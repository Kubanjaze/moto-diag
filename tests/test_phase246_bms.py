"""Phase 246 — BMS diagnostics: the generic layer, anchored per make.

Two halves. The first is the rule the operator set for this row: **a
forum-cited numeric threshold is allowed only if the provenance label is
surfaced wherever the number is displayed.** Step 0 found every display
surface but one already showed `source` — `kb list`, `kb search`,
`kb by-symptom`, `kb show`, the API — and the one that did not was the prompt:
`build_knowledge_context` carried title, severity, scope, symptoms, causes
and a fix preview, and no source, so a forum threshold reached the model
looking exactly like manufacturer data. `diagnose` renders no KB entries
itself; the model's answer is where a technician reads the number. These
tests walk every surface.

The second half is the content: five generic entries — cell balancing,
state of health, the voltage curve, thermal derating, cycle counting — each
anchored to a manufacturer page for at least one make, or not written. Those
tests are added when the research record is in; the rule tests come first
because the rule is what makes the content safe to write.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from motodiag.core.database import get_connection, init_db
from motodiag.engine.prompts import DIAGNOSTIC_SYSTEM_PROMPT, build_knowledge_context


def _issue(conn, *, source, title="Cell imbalance above 100 mV at rest", make="Zero", model="SR/S"):
    return conn.execute(
        "INSERT INTO known_issues (make, model, title, description, symptoms, causes, "
        "severity, source, fix_procedure) VALUES (?, ?, ?, ?, ?, ?, 'medium', ?, ?)",
        (make, model, title, "An owner-community threshold, for the display tests.",
         json.dumps(["reduced range"]), json.dumps(["a weak brick"]), source,
         "Balance-charge overnight; if the app still shows >100 mV, see a dealer."),
    ).lastrowid


@pytest.fixture
def garage(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    db = str(tmp_path / "phase246.db")
    init_db(db)
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    monkeypatch.setenv("COLUMNS", "220")
    reset_settings()
    with get_connection(db) as conn:
        issue_id = _issue(conn, source="forum")
    from motodiag.knowledge.marques import rebuild_make_index_at
    from motodiag.knowledge.models import rebuild_model_index_at

    rebuild_make_index_at(db)
    rebuild_model_index_at(db)
    yield db, issue_id
    reset_settings()


def _run(*args):
    from motodiag.cli.main import cli

    return CliRunner().invoke(cli, list(args))


# ---------------------------------------------------------------------------
# 1. The label is surfaced wherever the number is displayed
# ---------------------------------------------------------------------------


class TestEveryDisplaySurfaceShowsTheSource:
    """The operator's rule, walked surface by surface. A forum threshold
    ("100 mV") is seeded once; each surface must show `forum` beside it."""

    def test_kb_list(self, garage):
        out = _run("kb", "list", "--make", "Zero").output
        assert "100 mV" in out and "forum" in out, out

    def test_kb_search(self, garage):
        out = _run("kb", "search", "imbalance").output
        assert "100 mV" in out and "forum" in out, out

    def test_kb_symptom(self, garage):
        out = _run("kb", "by-symptom", "reduced range").output
        assert "100 mV" in out and "forum" in out, out

    def test_kb_show(self, garage):
        _db, issue_id = garage
        out = _run("kb", "show", str(issue_id)).output
        assert "100 mV" in out
        assert "Source:" in out and "forum" in out, out

    def test_the_prompt(self, garage):
        """The surface Step 0 found bare. `diagnose` renders no KB entries;
        the model's answer is the display, so the label goes in the prompt."""
        context = build_knowledge_context([{
            "title": "Cell imbalance above 100 mV at rest", "severity": "medium",
            "symptoms": ["reduced range"], "causes": [], "fix_procedure": "", "source": "forum",
        }])
        assert "source: forum" in context

    def test_the_prompt_carries_service_manual_too(self):
        context = build_knowledge_context([{
            "title": "Balancing runs during the CV taper", "severity": "low",
            "symptoms": [], "causes": [], "source": "service-manual",
        }])
        assert "source: service-manual" in context

    def test_a_legacy_row_renders_as_before(self):
        """244S pins `--- Issue 1: Legacy (severity: low) ---` for a dict with no
        source. The label is appended only when there is one."""
        context = build_knowledge_context([
            {"title": "Legacy", "severity": "low", "symptoms": [], "causes": []},
        ])
        assert "--- Issue 1: Legacy (severity: low) ---" in context
        assert "source:" not in context


class TestTheModelIsToldWhatTheLabelMeans:
    def test_the_system_prompt_names_the_label(self):
        assert "`source:` label" in DIAGNOSTIC_SYSTEM_PROMPT

    def test_forum_figures_are_never_a_specification(self):
        assert "never present it as a specification" in DIAGNOSTIC_SYSTEM_PROMPT
        assert "service-manual" in DIAGNOSTIC_SYSTEM_PROMPT
