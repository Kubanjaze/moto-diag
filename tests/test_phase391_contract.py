"""Phase 391 — the Quartermaster's contract: what the skill's records promise.

- In shadow it merges nothing and moves no label: neither its stage nor
  its module holds a merge, a label write or a push.
- `SKILL.md` documents the rank and its checks; the CHANGELOG's newest
  entry is this phase's; the Step 0 dry run's real artefacts are kept.
- Every check id the brief lists is one the module can return.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))

sys.path.insert(0, str(ROOT / "tests"))
import dispatcher as D  # noqa: E402
import quartermaster as Q  # noqa: E402
from support.source_guards import code_of  # noqa: E402


def test_the_stage_merges_nothing_and_moves_no_label():
    src = code_of(D.Fleet.stage_quartermaster)
    for forbidden in ('"merge",', "pr merge", "--add-label", "--remove-label", "set_state",
                      "label_once", "reapply", "push_once", "push_rank", "commit_once"):
        assert forbidden not in src, forbidden


def test_the_module_calls_no_github_and_no_git_write():
    src = code_of(SKILL / "quartermaster.py")
    assert "rank_call.gh" not in src and '"gh"' not in src
    writes = re.findall(r'_git\(clone, "(\w+(?:-\w+)?)"', src)
    assert set(writes) <= {"diff", "merge-base", "cat-file", "status", "merge-tree"}, writes


def test_merge_tree_writes_no_ref():
    """`git merge-tree --write-tree` writes objects, never a ref or the work tree."""
    assert '"merge-tree", "--write-tree"' in code_of(SKILL / "quartermaster.py")


def test_every_listed_check_has_its_reader():
    src = code_of(SKILL / "quartermaster.py")
    for k in Q.CHECKS:
        if k.startswith("Q"):
            assert f'"{k}"' in src.split("CHECKS = {", 1)[1].split("BRIEF", 1)[1] \
                or f'Finding("{k}"' in src, k
    assert set(Q.NOT_READ) <= set(Q.CHECKS)


def test_skill_md_documents_the_quartermaster():
    text = (SKILL / "SKILL.md").read_text()
    for needle in ("quartermaster.py", "In shadow it merges nothing", "quartermaster_since",
                   "| Q1 |", "| Q9 |", "quartermaster.jsonl"):
        assert needle in text, needle


def test_the_changelogs_newest_entry_is_391():
    """391's entry is there; since Phase 392 it is no longer the newest."""
    heads = [ln for ln in (SKILL / "CHANGELOG.md").read_text().splitlines()
             if ln.startswith("## ")]
    assert any("(Phase 391)" in h for h in heads)


def test_the_dry_runs_artefacts_are_kept():
    d = SKILL / "fixtures" / "quartermaster" / "pr20"
    for name in ("verify.txt", "context.txt", "verdict.json", "brief_as_drafted.txt"):
        assert (d / name).is_file(), name
    assert json.loads((d / "verdict.json").read_text())["verdict"] == "refuse"
    assert "=== 14. the regression line names its command ===" in (d / "verify.txt").read_text()


def test_the_stage_is_known_to_the_resume_and_the_sweep():
    assert D.STAGE_RANK["quartermaster"] == "quartermaster"
    assert D.QM_M in D.RANK_PREFIXES
    assert "stage_quartermaster" in code_of(D.Fleet.resume)
