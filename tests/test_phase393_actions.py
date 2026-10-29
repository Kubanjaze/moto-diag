"""Phase 393 — the GitHub Actions workflow's shape.

On every pull request: the lint and type ratchet and `roadmap_check.py`.
No secret, no write permission, no live-data path, and the tools it
installs are the pinned dev extra (so its counts are the desktop's).
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows" / "quality.yml"
TEXT = WF.read_text(encoding="utf-8")
CODE = "\n".join(ln for ln in TEXT.splitlines() if not ln.lstrip().startswith("#"))


def test_it_runs_on_every_pull_request():
    assert re.search(r"^on:\n  pull_request:\s*$", CODE, re.M)


def test_it_holds_no_secret_and_cannot_write():
    assert "secrets." not in CODE
    assert re.search(r"^permissions:\n  contents: read\s*$", CODE, re.M)
    assert "write" not in CODE


def test_it_reads_no_live_data():
    for word in ("live.json", "motodiag.db", "MOTODIAG_DB_PATH", ".config/motodiag"):
        assert word not in CODE


def test_it_runs_the_ratchet_and_the_ledger():
    assert "tests/test_phase393_quality_ratchet.py" in CODE
    assert "python .claude/skills/closeout/roadmap_check.py" in CODE


def test_it_installs_the_pinned_tools():
    assert 'pip install -e ".[dev]"' in CODE
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for pin in ('"ruff==0.16.9"', '"mypy==2.3.1"', '"pytest-cov==7.1.0"', '"coverage==7.14.1"'):
        assert pin in pyproject
