"""Phase 133 — Gate 5: CLI Integration Test.

Pass/fail checkpoint for Track D (mechanic CLI, phases 122-132).

Proves the full mechanic workflow wires together end-to-end on a single
shared DB via Click's ``CliRunner``: garage add → diagnose quick →
annotate → reopen → code lookup → kb search → export in three formats
→ cache/tier/intake/completion introspection.

Pattern mirrors Phase 121's Gate R — one big integration test file, zero
new production code, pure observation over the existing CLI surface.

Every AI-bearing boundary is patched:

- ``motodiag.cli.diagnose._default_diagnose_fn`` (Phase 123)
- ``motodiag.cli.code._default_interpret_fn`` (Phase 124)
- ``motodiag.intake.vehicle_identifier._default_vision_call`` (Phase 122)

Three test classes:

- ``TestEndToEndCliWorkflow``: the 18-step mechanic scenario.
- ``TestCliSurfaceBreadth``: command-tree structural assertions.
- ``TestRegressionAgainstGateR``: schema/import-graph sanity.

Zero live AI tokens.
"""

from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.core.database import (
    SCHEMA_VERSION,
    get_schema_version,
    init_db,
)
from motodiag.core.migrations import get_applied_migrations
from motodiag.core.models import (
    DTCCategory,
    DTCCode,
    Severity,
    SymptomCategory,
)
from motodiag.core.session_repo import get_session, list_sessions
from motodiag.engine.models import TokenUsage
from motodiag.knowledge.dtc_repo import add_dtc
from motodiag.knowledge.issues_repo import add_known_issue


# -----------------------------------------------------------------------------
# Fixtures + shared helpers
# -----------------------------------------------------------------------------


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + env at a temp DB; seed one DTC + one known-issue.

    Pattern: Phase 123/128 — env var + reset_settings around the test so
    get_settings() returns a Settings pointing at the temp DB. COLUMNS=200
    widens the virtual terminal so Rich tables don't word-wrap long titles
    mid-row (which breaks substring asserts on titles).
    """
    from motodiag.core.config import reset_settings

    db_path = str(tmp_path / "phase133.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    monkeypatch.setenv("COLUMNS", "200")
    reset_settings()
    init_db(db_path)

    # Seed P0115 — generic OBD-II ECT sensor code. Pre-seeding keeps the
    # workflow's `code P0115` step hermetic (doesn't depend on whatever
    # dtc_codes/*.json is on disk).
    add_dtc(
        DTCCode(
            code="P0115",
            description="Engine Coolant Temperature sensor circuit",
            category=SymptomCategory.ENGINE,
            dtc_category=DTCCategory.ENGINE,
            severity=Severity.MEDIUM,
            make=None,  # generic
            common_causes=[
                "ECT sensor open / shorted",
                "Harness chafe near header",
                "ECU connector corrosion",
            ],
            fix_summary=(
                "Ohm-check ECT sensor cold (~2kΩ) and warm (~200Ω); "
                "replace if reading is flat."
            ),
        ),
        db_path=db_path,
    )

    # Seed one known-issue referencing "stator" so `kb search "stator"`
    # always finds something regardless of loader data shape.
    add_known_issue(
        title="Twin-Cam stator failure — low AC output under load",
        description=(
            "Twin-Cam 88/96 stators lose insulation under heat; AC "
            "output drops below spec, battery discharges on long rides."
        ),
        make="Harley-Davidson",
        model="Sportster 883",
        year_start=1999,
        year_end=2016,
        severity="high",
        symptoms=[
            "battery not charging",
            "headlight dim at idle",
            "no spark after warmup",
        ],
        dtc_codes=["P0562"],
        causes=["Stator winding insulation breakdown", "Rotor magnet loss"],
        fix_procedure=(
            "Measure AC output stator-to-stator at 2000 rpm; "
            "replace assembly if <16V AC per 1000 rpm."
        ),
        parts_needed=["OEM stator", "Primary gasket", "Primary fluid"],
        estimated_hours=3.5,
        db_path=db_path,
    )

    yield db_path
    reset_settings()


# ----- Canned AI responses (NO network calls anywhere) -----


class _DiagItem:
    """Minimal DiagnosisItem shim matching engine.models shape."""

    def __init__(self, diagnosis, confidence, severity, rationale, actions=None):
        self.diagnosis = diagnosis
        self.confidence = confidence
        self.severity = severity
        self.rationale = rationale
        self.recommended_actions = actions or []


def _make_canned_diagnose_response():
    """Build a DiagnosticResponse-shaped SimpleNamespace at 0.90 confidence.

    Phase 123 test pattern — confidence >= CONFIDENCE_ACCEPT_THRESHOLD
    terminates the interactive loop on round 1 so quick-path tests
    don't hang waiting for mechanic input.
    """
    return SimpleNamespace(
        vehicle_summary="2005 Harley-Davidson Sportster 883",
        symptoms_acknowledged=["won't start, no spark"],
        diagnoses=[
            _DiagItem(
                diagnosis="Stator failure",
                confidence=0.90,
                severity="high",
                rationale=(
                    "Classic Sportster 883 failure mode — stator windings "
                    "break down with age and heat, killing charging output."
                ),
                actions=[
                    "Measure stator AC output (2-pin connector)",
                    "Replace stator assembly if <16V AC per 1000 rpm",
                    "Inspect regulator/rectifier for secondary damage",
                ],
            )
        ],
        additional_tests=[],
        notes=None,
    )


def _make_canned_usage():
    """TokenUsage shim — same shape Phase 123 tests use."""
    return TokenUsage(
        input_tokens=500,
        output_tokens=150,
        model="haiku",
        cost_estimate=0.001,
        latency_ms=1200,
    )


def _make_canned_interpret_result():
    """FaultCodeResult-shaped SimpleNamespace for --explain path (Phase 124)."""
    return SimpleNamespace(
        code="P0115",
        code_format="obd2_generic",
        description="fuel_and_air_metering",
        system="fuel_and_air_metering",
        possible_causes=[
            "ECT sensor open / failing",
            "Harness chafe near header",
            "ECU connector corrosion",
        ],
        tests_to_confirm=[
            "Ohm-check ECT sensor cold (~2kΩ) and warm (~200Ω)",
            "Back-probe ECU pin for 5V reference",
        ],
        related_symptoms=["Hard cold start", "Rich mixture until warm"],
        repair_steps=[
            "Confirm reading with OEM service tool",
            "Replace ECT sensor (OEM spec)",
            "Clear codes and verify",
        ],
        estimated_hours=0.8,
        estimated_cost="$45-$120",
        safety_critical=False,
        notes=None,
    )


def _fake_diagnose(**kwargs):
    """Drop-in for ``_default_diagnose_fn`` — ignores args, returns canned."""
    return _make_canned_diagnose_response(), _make_canned_usage()


def _fake_interpret(**kwargs):
    """Drop-in for ``_default_interpret_fn`` — ignores args, returns canned."""
    return _make_canned_interpret_result(), _make_canned_usage()


def _fake_vision(image_bytes, hints, model_id):
    """Drop-in for ``_default_vision_call`` — defensive only.

    This workflow never invokes ``garage add-from-photo`` but the patch is
    active throughout so that any accidental intake.VehicleIdentifier call
    fails fast (returns a canned response rather than reaching the live
    Anthropic API).
    """
    # Return a minimal JSON object matching the identifier's expected output.
    canned = (
        '{"make":"Harley-Davidson","model":"Sportster 883",'
        '"year_range":[2004,2006],"engine_cc_range":[883,883],'
        '"powertrain_guess":"ice","confidence":0.85,'
        '"reasoning":"(mocked for gate 5)","alert":null}'
    )
    return canned, 100, 50


# -----------------------------------------------------------------------------
# Part A — End-to-end mechanic workflow
# -----------------------------------------------------------------------------


class TestEndToEndCliWorkflow:
    """One cohesive scenario — 18 CLI invocations on a shared DB.

    Each step depends on state from the previous step. Catches cross-command
    integration bugs siloed unit tests (phases 122-132) cannot surface.
    """

    def test_full_mechanic_flow(self, cli_db, tmp_path):
        # Import inside the test so the cli_db env patching is in effect
        # before the subscription module's env read and the CLI module
        # evaluates its command registrations.
        from motodiag.cli.main import cli

        runner = CliRunner()

        def run(args, input_=None):
            """Invoke cli with catch_exceptions=False so failures surface loud."""
            result = runner.invoke(
                cli, args, input=input_, catch_exceptions=False,
            )
            return result

        # Three AI-bearing boundaries patched for the entire workflow.
        # If any live code path slipped past a mock it would hit network,
        # fail fast on credentials, and be visible in test output.
        with patch(
            "motodiag.cli.diagnose._default_diagnose_fn", _fake_diagnose,
        ), patch(
            "motodiag.cli.code._default_interpret_fn", _fake_interpret,
        ), patch(
            "motodiag.intake.vehicle_identifier._default_vision_call",
            _fake_vision,
        ):
            # --- Step 1: garage add ---------------------------------------
            r = run([
                "garage", "add",
                "--make", "Harley-Davidson",
                "--model", "Sportster 883",
                "--year", "2005",
                "--engine-cc", "883",
                "--vin", "1HD1CZ3115K123456",
                "--protocol", "j1850",
                "--powertrain", "ice",
            ])
            assert r.exit_code == 0, r.output
            assert "Added vehicle #1" in r.output
            assert "Sportster 883" in r.output

            # --- Step 2: garage list --------------------------------------
            r = run(["garage", "list"])
            assert r.exit_code == 0, r.output
            assert "Sportster 883" in r.output
            assert "2005" in r.output

            # --- Step 3: motodiag quick "symptoms" --bike -----------------
            # Top-level shortcut (Phase 125) delegates to `diagnose quick`.
            r = run([
                "quick",
                "won't start, no spark",
                "--bike", "sportster-2005",
            ])
            assert r.exit_code == 0, r.output
            assert "Session #" in r.output
            assert "Stator failure" in r.output

            # Pull the session ID back from the DB (the quick output says
            # "Session #1 created and diagnosed." but we query to be robust
            # to future output format tweaks).
            sessions = list_sessions(vehicle_id=1, db_path=cli_db)
            assert len(sessions) == 1, (
                f"Expected exactly 1 session after quick; got {len(sessions)}"
            )
            sid = sessions[0]["id"]
            assert sessions[0]["status"] == "closed", (
                "quick should close the session on success"
            )

            # --- Step 4: diagnose list ------------------------------------
            r = run(["diagnose", "list"])
            assert r.exit_code == 0, r.output
            assert str(sid) in r.output
            assert "Sportster" in r.output

            # --- Step 5: diagnose show <sid> (terminal) -------------------
            r = run(["diagnose", "show", str(sid)])
            assert r.exit_code == 0, r.output
            assert "Stator failure" in r.output
            assert "won't start" in r.output

            # --- Step 6: diagnose show --format md --output ---------------
            md_path = tmp_path / "report.md"
            r = run([
                "diagnose", "show", str(sid),
                "--format", "md",
                "--output", str(md_path),
            ])
            assert r.exit_code == 0, r.output
            assert md_path.exists(), "md report not written"
            md_content = md_path.read_text(encoding="utf-8")
            assert md_content.startswith("# Session"), (
                f"md should start with heading; got {md_content[:60]!r}"
            )
            assert "Stator failure" in md_content

            # --- Step 7: diagnose show --format html --output -------------
            html_path = tmp_path / "report.html"
            r = run([
                "diagnose", "show", str(sid),
                "--format", "html",
                "--output", str(html_path),
            ])
            assert r.exit_code == 0, r.output
            assert html_path.exists(), "html report not written"
            html_content = html_path.read_text(encoding="utf-8")
            # xhtml2pdf output starts with standard DOCTYPE preamble.
            assert html_content.lstrip().lower().startswith("<!doctype"), (
                f"html should start with <!DOCTYPE; got {html_content[:80]!r}"
            )
            assert "Stator failure" in html_content

            # --- Step 8: diagnose show --format pdf --output --------------
            pdf_path = tmp_path / "report.pdf"
            r = run([
                "diagnose", "show", str(sid),
                "--format", "pdf",
                "--output", str(pdf_path),
            ])
            assert r.exit_code == 0, r.output
            assert pdf_path.exists(), "pdf not written"
            # PDF magic number — catches "someone wrote HTML with .pdf ext".
            pdf_bytes = pdf_path.read_bytes()
            assert pdf_bytes.startswith(b"%PDF-"), (
                f"pdf magic missing; got first 8 bytes = {pdf_bytes[:8]!r}"
            )
            assert len(pdf_bytes) > 500, "pdf is suspiciously small"

            # --- Step 9: diagnose annotate <sid> "note" -------------------
            annotation = (
                "Follow-up: stator AC output 12V low at 2000 rpm — "
                "confirmed failure, ordering OEM replacement."
            )
            r = run(["diagnose", "annotate", str(sid), annotation])
            assert r.exit_code == 0, r.output
            assert "Note added" in r.output

            # Verify via direct DB read — notes column must contain the text.
            row = get_session(sid, db_path=cli_db)
            assert row is not None
            assert row.get("notes") is not None, (
                "annotate did not write to notes column"
            )
            assert annotation in row["notes"]

            # --- Step 10: diagnose reopen <sid> ---------------------------
            # Session was closed by quick in step 3 — reopen flips it back.
            r = run(["diagnose", "reopen", str(sid)])
            assert r.exit_code == 0, r.output
            assert "reopened" in r.output.lower()

            row = get_session(sid, db_path=cli_db)
            assert row["status"] == "open", (
                f"reopen should flip status to open; got {row['status']!r}"
            )

            # --- Step 11: code P0115 (local, no AI) -----------------------
            r = run(["code", "P0115"])
            assert r.exit_code == 0, r.output
            # Description comes from the seeded DTC row.
            assert "Coolant Temperature" in r.output
            # Common causes section surfaces at least one seeded cause.
            assert "sensor" in r.output.lower()

            # --- Step 12: code P0115 --explain --vehicle-id 1 -------------
            # Hits mocked _default_interpret_fn; zero live tokens.
            r = run([
                "code", "P0115",
                "--explain",
                "--vehicle-id", "1",
            ])
            assert r.exit_code == 0, r.output
            # Canned causes + repair steps surface in the explain panel.
            assert "ECT sensor" in r.output
            # Repair-step text from the canned result.
            assert "Replace ECT sensor" in r.output

            # --- Step 13: kb list -----------------------------------------
            r = run(["kb", "list"])
            assert r.exit_code == 0, r.output
            assert "stator" in r.output.lower(), (
                "seeded Twin-Cam stator issue should surface in kb list"
            )

            # --- Step 14: kb search "stator" ------------------------------
            r = run(["kb", "search", "stator"])
            assert r.exit_code == 0, r.output
            assert "Twin-Cam stator failure" in r.output

            # Pull the known-issue ID back for the next step. (We only
            # seeded one row so this is deterministic.)
            from motodiag.knowledge.issues_repo import search_known_issues_text

            rows = search_known_issues_text("stator", db_path=cli_db)
            assert rows, "seeded known-issue should match"
            kb_id = rows[0]["id"]

            # --- Step 15: kb show <kbid> --format md --output -------------
            kb_md_path = tmp_path / "kb.md"
            r = run([
                "kb", "show", str(kb_id),
                "--format", "md",
                "--output", str(kb_md_path),
            ])
            assert r.exit_code == 0, r.output
            assert kb_md_path.exists(), "kb md report not written"
            kb_content = kb_md_path.read_text(encoding="utf-8")
            assert kb_content.startswith("# "), (
                f"kb md should start with heading; got {kb_content[:60]!r}"
            )
            assert "Twin-Cam stator failure" in kb_content

            # --- Step 16: cache stats -------------------------------------
            # With diagnose/interpret mocked the cache may be empty — the
            # command itself must still exit 0 and render.
            r = run(["cache", "stats"])
            assert r.exit_code == 0, r.output
            # Either the empty-state panel or the stats panel is fine.
            lower = r.output.lower()
            assert "cache" in lower

            # --- Step 17: intake quota ------------------------------------
            r = run(["intake", "quota"])
            assert r.exit_code == 0, r.output
            # Unlimited OR count-format. Both are valid output shapes.
            lower = r.output.lower()
            assert ("tier:" in lower) or ("unlimited" in lower) or (
                "used" in lower
            )

            # --- Step 18: tier --compare ----------------------------------
            r = run(["tier", "--compare"])
            assert r.exit_code == 0, r.output
            lower = r.output.lower()
            assert "individual" in lower
            assert "shop" in lower
            assert "company" in lower

            # --- Step 19: completion bash ---------------------------------
            r = run(["completion", "bash"])
            assert r.exit_code == 0, r.output
            # Click's bash completion uses the _MOTODIAG_COMPLETE env hook.
            assert "_MOTODIAG_COMPLETE" in r.output

            # --- Intentional-error check: diagnose show <nonexistent> -----
            # Proves CLI error paths aren't silently swallowed. We let
            # Click's runner catch exceptions here — Abort() + exit_code!=0
            # is the contract the show command documents.
            r = runner.invoke(
                cli, ["diagnose", "show", "99999"],
                catch_exceptions=True,
            )
            assert r.exit_code != 0, (
                "showing a nonexistent session should error out"
            )
            assert "not found" in r.output.lower()

        # -----------------------------------------------------------------
        # Final integrity assertions — all mocks now out of scope
        # -----------------------------------------------------------------
        assert get_schema_version(cli_db) >= 15, (
            "schema should be >= Phase 131 floor (v15)"
        )

        sessions_final = list_sessions(db_path=cli_db)
        assert len(sessions_final) == 1, (
            f"Expected exactly 1 session at end of workflow; "
            f"got {len(sessions_final)}"
        )
        final = sessions_final[0]
        assert final["status"] == "open", (
            "session should be left in 'open' state after reopen"
        )
        assert final.get("notes") is not None, (
            "session should have notes from annotate step"
        )

        # Three report files written and readable.
        assert md_path.exists() and md_path.stat().st_size > 0
        assert html_path.exists() and html_path.stat().st_size > 0
        assert pdf_path.exists() and pdf_path.stat().st_size > 0


# -----------------------------------------------------------------------------
# Part B — CLI surface breadth
# -----------------------------------------------------------------------------


class TestCliSurfaceBreadth:
    """Fast structural tests over the Click command tree. No DB needed."""

    def test_all_toplevel_commands_registered(self):
        """Every expected canonical command + every hidden alias is present."""
        from motodiag.cli.main import cli

        canonical = {
            "diagnose", "code", "kb", "garage", "intake", "cache",
            "completion", "tier", "config", "info", "history", "quick",
            "db", "search",
        }
        missing = canonical - set(cli.commands)
        assert not missing, (
            f"Missing canonical top-level commands: {sorted(missing)}. "
            f"Present: {sorted(cli.commands)}"
        )

        # Phase 130 hidden single-letter aliases.
        aliases = {"d", "k", "g", "q"}
        missing_aliases = aliases - set(cli.commands)
        assert not missing_aliases, (
            f"Missing hidden aliases: {sorted(missing_aliases)}. "
            f"Present: {sorted(cli.commands)}"
        )
        # Hidden flag must be set so --help filters them out.
        for alias in aliases:
            cmd = cli.commands[alias]
            assert getattr(cmd, "hidden", False) is True, (
                f"Alias {alias!r} is not hidden; would clutter --help"
            )

    def test_hidden_aliases_not_in_help(self):
        """Aliases are registered but MUST NOT show up as --help rows.

        We assert on structural substrings (``"\\n  d "`` as a
        command-row prefix) rather than the whole help string so format
        changes across Click versions don't spuriously fail the test.
        """
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(cli, ["--help"], catch_exceptions=False)
        assert r.exit_code == 0, r.output

        # Canonical commands DO appear.
        for name in ("diagnose", "kb", "garage", "quick"):
            assert name in r.output, (
                f"canonical command {name!r} missing from --help:\n{r.output}"
            )

        # Aliases DO NOT appear as command rows. Click renders rows with
        # at least two leading spaces followed by the command name and
        # more whitespace. Matching "\n  d " catches a row without
        # matching substrings in description text.
        for alias in ("d", "k", "g", "q"):
            row_marker = f"\n  {alias} "
            assert row_marker not in r.output, (
                f"hidden alias {alias!r} leaked into --help:\n{r.output}"
            )

    def test_expected_subcommands_present(self):
        """Each subgroup has its expected subcommand set."""
        from motodiag.cli.main import cli

        expected: dict[str, set[str]] = {
            "diagnose": {"start", "quick", "list", "show", "reopen", "annotate"},
            "garage": {"add", "list", "remove", "add-from-photo"},
            "intake": {"photo", "quota"},
            "kb": {"list", "show", "search", "by-symptom", "by-code"},
            "cache": {"stats", "purge", "clear"},
            "completion": {"bash", "zsh", "fish"},
            "config": {"show", "paths", "init"},
            "db": {"init"},
        }

        for group_name, expected_subcmds in expected.items():
            assert group_name in cli.commands, (
                f"subgroup {group_name!r} not registered"
            )
            group = cli.commands[group_name]
            assert isinstance(group, click.Group), (
                f"{group_name!r} registered but is not a click.Group "
                f"(got {type(group).__name__})"
            )
            actual = set(group.commands)
            missing = expected_subcmds - actual
            assert not missing, (
                f"{group_name!r} missing subcommands: {sorted(missing)}. "
                f"Present: {sorted(actual)}"
            )

    def test_cli_help_exits_zero_via_subprocess(self):
        """``python -m motodiag.cli.main --help`` exits 0 in the real python.

        CliRunner invokes in-process; this test catches module-level side
        effects and import-graph breakage that only manifest on a cold
        Python start — mirrors Phase 121's ``test_motodiag_cli_help_works``.
        """
        result = subprocess.run(
            [sys.executable, "-m", "motodiag.cli.main", "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"--help exited {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
        combined = (result.stdout + result.stderr)
        lower = combined.lower()
        assert "motodiag" in lower
        assert "diagnose" in lower
        assert "garage" in lower


# -----------------------------------------------------------------------------
# Part C — Regression + forward-compat
# -----------------------------------------------------------------------------


class TestRegressionAgainstGateR:
    """Proves Track D (phases 122-132) did not break the Phase 121 substrate."""

    def test_schema_version_is_at_least_15(self, tmp_path):
        """Forward-compat floor for Phase 131's migration 015 (cache table).

        Uses ``>=`` so Phase 134+ can bump without editing this test — same
        convention Phase 121 set with its ``>= 12`` check.
        """
        db = str(tmp_path / "schema.db")
        init_db(db)
        assert get_schema_version(db) >= 15, (
            f"expected schema >= 15 (Phase 131 floor); got {get_schema_version(db)}"
        )
        assert SCHEMA_VERSION >= 15, (
            f"SCHEMA_VERSION constant should be >= 15; got {SCHEMA_VERSION}"
        )

        applied = get_applied_migrations(db)
        # Retrofit floor + Track D's cache migration (015).
        for v in (3, 12, 15):
            assert v in applied, (
                f"missing migration version {v} on fresh init; "
                f"applied = {sorted(applied)}"
            )

    def test_all_track_d_cli_modules_import_cleanly(self):
        """Every Track D CLI submodule imports without side effects.

        Belt-and-suspenders companion to the subprocess --help test — if
        that fails, this gives a per-module diagnostic rather than a
        single "exit code 1" from the subprocess.
        """
        import motodiag.cli.diagnose  # noqa: F401  (Phase 123/127/132)
        import motodiag.cli.code  # noqa: F401  (Phase 124)
        import motodiag.cli.kb  # noqa: F401  (Phase 128)
        import motodiag.cli.cache  # noqa: F401  (Phase 131)
        import motodiag.cli.completion  # noqa: F401  (Phase 130)
        import motodiag.cli.theme  # noqa: F401  (Phase 129)
        import motodiag.cli.export  # noqa: F401  (Phase 132)
        import motodiag.cli.subscription  # noqa: F401  (Phase 118 helper)
        import motodiag.cli.registry  # noqa: F401  (Phase 109)
        import motodiag.cli.main  # noqa: F401  (top-level glue)
