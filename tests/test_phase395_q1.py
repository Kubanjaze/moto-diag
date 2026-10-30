"""Phase 395 — the Quartermaster's Q1 and the database step.

The prompt: "Q1 passes a phase whose migration was applied this way: its
dry-run and live diffs are committed, and verify-live agrees. A migration
with no live apply still refuses." `verify-live` reads live, so the
dispatcher runs it outside the fence and hands Q1 its result
(`live_check`); in the fence there is none, and a migration refuses.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / "tests"))

import quartermaster as Q  # noqa: E402
from test_phase395_engineer_deploy import (  # noqa: E402
    FIX,
    PHASE,
    applied,
    apply_case,
    close_out,
    git,
    good_tree,
    write,
)


def closed(tmp: pathlib.Path) -> pathlib.Path:
    """A pull request's head after the database step and the close-out:
    every phase file in `completed/`."""
    repo = good_tree(tmp)
    write(repo, {f"docs/phases/in_progress/{PHASE}_step0.md":
                 "# Step 0\n\nClassification: **extension.**\n"})
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "step 0")
    applied(repo)
    close_out(repo)
    (repo / "docs" / "phases" / "completed").mkdir()
    for p in sorted((repo / "docs" / "phases" / "in_progress").iterdir()):
        git(repo, "mv", str(p.relative_to(repo)), f"docs/phases/completed/{p.name}")
    git(repo, "commit", "-qm", "moved")
    return repo


def agrees():
    return 0, "  equals the approved exact diff: yes\n"


def test_a_migration_applied_through_the_database_step_passes(tmp_path):
    f = Q.scope(closed(tmp_path), PHASE, live_check=agrees)
    assert f.ok, f.why


def test_the_known_bad_migration_with_no_live_diff_refuses(tmp_path):
    repo = closed(tmp_path)
    case = json.loads((FIX / "known_bad" / "q1_migration_no_live_diff.json").read_text())
    apply_case(repo, case)
    f = Q.scope(repo, PHASE, live_check=agrees)
    assert not f.ok and case["refusal"] in f.why, f.why
    assert f"no committed {PHASE}_live_diff.md" in f.why


def test_in_the_fence_with_no_live_check_a_migration_still_refuses(tmp_path):
    f = Q.scope(closed(tmp_path), PHASE)
    assert not f.ok and "no live in the fence" in f.why


def test_verify_live_disagreeing_refuses(tmp_path):
    f = Q.scope(closed(tmp_path), PHASE,
                live_check=lambda: (3, "  equals the approved exact diff: no\n"))
    assert not f.ok and "verify-live exits 3" in f.why


def test_a_live_diff_that_records_a_problem_refuses_without_asking_live(tmp_path):
    repo = closed(tmp_path)
    p = repo / "docs" / "phases" / "completed" / f"{PHASE}_live_diff.md"
    p.write_text(p.read_text().replace("`yes`", "`no`"))
    git(repo, "commit", "-qam", "live is not the approved diff")
    asked = []
    f = Q.scope(repo, PHASE, live_check=lambda: asked.append(1) or (0, ""))
    assert not f.ok and "not the approved diff" in f.why and asked == []


def test_a_migration_with_no_step_at_all_refuses(tmp_path):
    repo = good_tree(tmp_path)
    write(repo, {f"docs/phases/in_progress/{PHASE}_step0.md": "Classification: **extension.**\n"})
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "step 0")
    f = Q.scope(repo, PHASE, live_check=agrees)
    assert not f.ok and "a migration with no database step" in f.why


@pytest.mark.parametrize("kind", ["dryrun_diff", "deploy_answer"])
def test_each_of_the_steps_files_is_needed(tmp_path, kind):
    repo = closed(tmp_path)
    git(repo, "rm", "-q", f"docs/phases/completed/{PHASE}_{kind}.md")
    git(repo, "commit", "-qm", f"no {kind}")
    f = Q.scope(repo, PHASE, live_check=agrees)
    assert not f.ok and f"no committed {PHASE}_{kind}.md" in f.why


def test_v8_says_why_it_is_not_read():
    assert "verify-live outside it" in Q.NOT_READ["V8"]
