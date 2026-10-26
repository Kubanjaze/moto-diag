"""Phase 390 — the resume's contract: what the skill's own records promise.

- Every stage the journal knows (`STAGE_RANK`), and the pause, has at least
  one kill point in `fixtures/resume/kill_points.json`, and every test the
  list names exists in `tests/test_phase390_resume.py`.
- Each known-bad journal in `fixtures/resume/bad/` is named by the search
  on start and kept by `prune_runs`.
- The journal is outside what the fence lets a model write: the fence binds
  `run/run` as `/fleet/run`, and the journal is `run/stage.json`.
- `SKILL.md` documents the journal and `recover --dry-run`; the CHANGELOG
  has the phase's entry; F219 is closed.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = SKILL / "fixtures" / "resume"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / "tests"))

import dispatcher as D  # noqa: E402
import journal as J  # noqa: E402
import test_phase390_resume as R  # noqa: E402
from test_phase390_resume import ledger, w  # noqa: E402

assert w and ledger  # the fixtures, imported for their names

POINTS = json.loads((FIX / "kill_points.json").read_text())
BAD = sorted((FIX / "bad").glob("*.json"))


def test_every_stage_and_the_pause_has_a_kill_point():
    assert set(POINTS) - {"_what"} == {*D.STAGE_RANK, "pause"}
    assert all(POINTS[s] for s in POINTS if s != "_what")


@pytest.mark.parametrize("name", sorted({t for s, pts in POINTS.items() if s != "_what"
                                         for t in pts.values()}))
def test_every_named_kill_point_has_its_test(name):
    assert callable(getattr(R, name, None)), f"no test {name}"


def test_the_list_names_every_kill_point_test():
    """A kill-point test cuts a stage (`_cut_` in its name), or is the pause's."""
    named = {t for s, pts in POINTS.items() if s != "_what" for t in pts.values()}
    cuts = {n for n in dir(R) if n.startswith("test_") and "_cut_" in n}
    assert cuts <= named, cuts - named
    assert named - cuts == {"test_a_pause_is_kept_until_its_resumed_stage_ends"}


def test_there_are_known_bad_journals():
    assert BAD


@pytest.mark.parametrize("bad", BAD, ids=lambda p: p.name)
def test_a_known_bad_journal_is_named_and_kept(w, bad, monkeypatch):
    run = w.fleet.runs / "20261025_150624_engineer_389A"
    (run / "run").mkdir(parents=True)
    shutil.copy(bad, run / J.FILE)
    assert J.Journal.load(run) is None and J.unfinished(w.fleet.runs) == []
    said = w.fleet.recover()
    assert said[0].startswith(f"leave {run.name}: its journal cannot be read")
    control = w.fleet.runs / "20261025_150000_finished"
    (control / "run").mkdir(parents=True)
    monkeypatch.setattr(D, "KEEP_RUNS", 1)
    (w.fleet.runs / "29991231_000000_newest").mkdir()        # the one KEEP_RUNS keeps
    w.fleet.prune_runs(set())
    assert run.is_dir(), "a run with an unreadable journal was pruned"
    assert not control.exists(), "the control: an older run with no journal is removed"


def test_the_journal_is_outside_the_fences_writable_run(w):
    run = w.fleet.new_run("x", {"stage": "digest", "day": "2026-10-21"})
    argv = D.FencedRunner(w.fleet, run / "clone", run / "run").fence_argv(["true"])
    bound = pathlib.Path(argv[argv.index("--run") + 1])
    journal_file = run / J.FILE
    assert journal_file.is_file() and bound == run / "run"
    assert bound not in journal_file.parents


def test_skill_md_documents_the_resume():
    text = (SKILL / "SKILL.md").read_text()
    for needle in ("journal.py", "recover --dry-run", "stage.json", "fleet-started"):
        assert needle in text, needle


def test_the_changelog_has_390():
    assert "(Phase 390)" in (SKILL / "CHANGELOG.md").read_text().split("\n## ", 2)[1]


def test_f219_is_closed():
    followups = (ROOT / "docs" / "FOLLOWUPS.md").read_text()
    head = next(ln for ln in followups.splitlines() if ln.startswith("### F219"))
    assert "CLOSED" in head and "390" in head
