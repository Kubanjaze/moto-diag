"""Phase 395 — the Engineer's `deploy` outcome, believed only as a `pr-ready` is.

The prompt: "A deploy is believed only as a pr-ready is: the clone clean,
the model-free run counting what the Engineer's line counts", and, for the
round after the apply, "No code changes after the apply". Each refusal has
a hand-written known-bad case in `.claude/skills/fleet/fixtures/deploy/`,
applied to a good tree that passes (the control).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = SKILL / "fixtures" / "deploy"
sys.path.insert(0, str(SKILL))

import engineer as E  # noqa: E402
from rank_call import Stop  # noqa: E402

PHASE = "990"
RESULT = json.loads((FIX / "deploy_result.json").read_text())
LINE = RESULT["regression_line"]
PLAN = (f"# Phase {PHASE}\n\n## Goal\n\nOne empty table.\n\n{E.DATABASE_STEP}\n\n"
        "It adds trial_empty.\n")


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def write(repo: pathlib.Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


def good_tree(tmp: pathlib.Path) -> pathlib.Path:
    """A clone at the Engineer's `deploy` point: master, and the phase branch
    with a migration, its scope file, the plan naming the database step and
    the regression of record."""
    repo = tmp / "clone"
    git(tmp, "init", "-q", "-b", "master", str(repo))
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    write(repo, {E.MIGRATIONS: "MIGRATIONS = [87]\n", "README.md": "master\n"})
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "master")
    git(repo, "switch", "-q", "-c", f"phase-{PHASE}-one-empty-table")
    inp = "docs/phases/in_progress"
    write(repo, {E.MIGRATIONS: "MIGRATIONS = [87, 88]\n",
                 f"{inp}/{PHASE}_implementation.md": PLAN,
                 f"{inp}/{PHASE}_deploy_scope.json": json.dumps(
                     {"tables": {"schema_version": {"added": 1}},
                      "schema": {"added": ["table trial_empty"]}})})
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the migration")
    short = git(repo, "rev-parse", "--short", "HEAD")
    write(repo, {f"{inp}/{PHASE}_phase_log.md":
                 f"# log\n\nRegression of record: 1234 passed, 0 failed, 0 skipped, 0 errors at "
                 f"`{short}` (12 min 0 s wall, `python -m pytest -n auto --dist load`, exit 0)\n"})
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the regression of record")
    return repo


def apply_case(repo: pathlib.Path, case: dict) -> None:
    write(repo, case.get("write", {}))
    for rel in case.get("remove", []):
        git(repo, "rm", "-q", rel)
    if case.get("commit"):
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", f"the known-bad case: {case['what'][:40]}")


def applied(repo: pathlib.Path, answer: str = "yes") -> str:
    """The operator's block, as its commits land in the clone: the dry-run
    diff and the answer, then the live diff."""
    inp = "docs/phases/in_progress"
    write(repo, {f"{inp}/{PHASE}_dryrun_diff.md": "# dry run\n",
                 f"{inp}/{PHASE}_deploy_answer.md":
                 f"# answer\n\nThe operator typed, verbatim:\n\n> {answer}\n"})
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the dry-run diff, and the operator's yes")
    write(repo, {f"{inp}/{PHASE}_live_diff.md":
                 "# live\n\n- **Scope problems:** `none`\n"
                 "- **Equals the approved exact diff:** `yes`\n"})
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "the live diff")
    return git(repo, "rev-parse", "HEAD")


def close_out(repo: pathlib.Path, quote: str = "> yes") -> None:
    """The close-out round's own commit: the answer quoted, documents only."""
    log = repo / "docs" / "phases" / "in_progress" / f"{PHASE}_phase_log.md"
    log.write_text(log.read_text() + f"\n## The database step\n\n{quote}\n")
    git(repo, "commit", "-qam", "the close-out")


def bad(name: str) -> dict:
    return json.loads((FIX / "known_bad" / f"{name}.json").read_text())


# ------------------------------------------------------------- read_result
def test_a_deploy_result_reads(tmp_path):
    (tmp_path / E.RESULT).write_text(json.dumps(RESULT))
    assert E.read_result(tmp_path)["outcome"] == "deploy"


@pytest.mark.parametrize("drop", ["summary", "regression_line", "live_change"])
def test_a_deploy_result_missing_a_part_is_a_stop(tmp_path, drop):
    (tmp_path / E.RESULT).write_text(json.dumps({k: v for k, v in RESULT.items() if k != drop}))
    with pytest.raises(Stop):
        E.read_result(tmp_path)


# ------------------------------------------------------------- verify_deploy
def test_the_good_tree_is_believed(tmp_path):
    assert E.verify_deploy(good_tree(tmp_path), PHASE, RESULT, LINE) == []


@pytest.mark.parametrize("name", ["deploy_dirty_clone", "deploy_no_scope_file"])
def test_a_known_bad_deploy_is_refused(tmp_path, name):
    repo = good_tree(tmp_path)
    case = bad(name)
    apply_case(repo, case)
    fails = E.verify_deploy(repo, PHASE, RESULT, LINE)
    assert any(case["refusal"] in f for f in fails), fails


def test_counts_that_differ_from_the_model_free_run_are_refused(tmp_path):
    other = LINE.replace("1234 passed", "1233 passed")
    fails = E.verify_deploy(good_tree(tmp_path), PHASE, RESULT, other)
    assert any("the model-free run counts" in f for f in fails), fails


def test_no_model_free_line_is_refused(tmp_path):
    assert E.verify_deploy(good_tree(tmp_path), PHASE, RESULT, None)


def test_a_plan_that_does_not_name_the_database_step_is_refused(tmp_path):
    repo = good_tree(tmp_path)
    apply_case(repo, {"write": {f"docs/phases/in_progress/{PHASE}_implementation.md": "# plan\n"},
                      "commit": True, "what": "no step"})
    assert any("not in scope" in f for f in E.verify_deploy(repo, PHASE, RESULT, LINE))


def test_a_branch_with_no_migration_is_refused(tmp_path):
    repo = good_tree(tmp_path)
    git(repo, "checkout", "-q", "master", "--", E.MIGRATIONS)
    git(repo, "commit", "-qm", "no migration")
    assert any("no migration" in f for f in E.verify_deploy(repo, PHASE, RESULT, LINE))


def test_a_branch_that_changes_the_deploy_tools_is_refused(tmp_path):
    repo = good_tree(tmp_path)
    apply_case(repo, {"write": {".claude/skills/deploy/deploy.py": "# loosened\n"},
                      "commit": True, "what": "a tool"})
    assert any("master's tools" in f for f in E.verify_deploy(repo, PHASE, RESULT, LINE))


def test_a_branch_that_already_carries_a_diff_is_refused(tmp_path):
    repo = good_tree(tmp_path)
    apply_case(repo, {"write": {f"docs/phases/in_progress/{PHASE}_dryrun_diff.md": "x\n"},
                      "commit": True, "what": "a diff"})
    assert any("only the operator's block" in f for f in E.verify_deploy(repo, PHASE, RESULT, LINE))


def test_documents_already_closed_out_are_refused(tmp_path):
    repo = good_tree(tmp_path)
    git(repo, "mv", f"docs/phases/in_progress/{PHASE}_phase_log.md",
        f"docs/phases/{PHASE}_phase_log.md")
    git(repo, "commit", "-qm", "moved")
    assert any("before the close-out" in f for f in E.verify_deploy(repo, PHASE, RESULT, LINE))


# ------------------------------------------------------- after the apply
def test_a_documents_only_close_out_passes(tmp_path):
    repo = good_tree(tmp_path)
    at = applied(repo)
    close_out(repo)
    assert E.applied_at(repo, PHASE) == at
    assert E.verify_after_apply(repo, PHASE, at) == []


def test_a_code_change_after_the_apply_is_refused(tmp_path):
    repo = good_tree(tmp_path)
    at = applied(repo)
    close_out(repo)
    case = bad("code_after_apply")
    apply_case(repo, case)
    fails = E.verify_after_apply(repo, PHASE, at)
    assert any(case["refusal"] in f for f in fails), fails


def test_an_answer_not_quoted_is_refused(tmp_path):
    repo = good_tree(tmp_path)
    at = applied(repo, answer="yes, go")
    close_out(repo, quote="> yes")
    assert any("does not quote" in f for f in E.verify_after_apply(repo, PHASE, at))


def test_a_migration_with_no_database_step_does_not_open_a_pr(tmp_path):
    repo = good_tree(tmp_path)
    assert any("database step has not run" in f for f in E.migration_changes(repo, PHASE))


def test_a_migration_changed_after_the_apply_does_not_open_a_pr(tmp_path):
    """A Red Team finding that would change an applied migration is the
    operator's (the prompt: a rule-1 stop), never a fix round's."""
    repo = good_tree(tmp_path)
    applied(repo)
    assert E.migration_changes(repo, PHASE) == []
    apply_case(repo, {"write": {E.MIGRATIONS: "MIGRATIONS = [87, 88, 89]\n"}, "commit": True,
                      "what": "changed"})
    assert any("changed after it was applied" in f for f in E.migration_changes(repo, PHASE))


# ------------------------------------------------------------- the briefs
def test_the_brief_names_the_database_step_and_its_outcome():
    brief = E.session_brief(PHASE, 36)
    assert E.DATABASE_STEP.lstrip("# ") in brief and '"outcome": "deploy"' in brief
    assert "Then do NOT close out" in brief and "live_change" in brief
    assert "never a deploy" in brief


def test_the_close_out_brief_changes_no_code():
    brief = E.session_brief(PHASE, 36, closeout=True)
    assert "The database step is done" in brief and "change no code" in brief
    assert f"{PHASE}_deploy_answer.md" in brief
    assert "The database step is done" not in E.session_brief(PHASE, 36)


def test_the_fix_round_holds_an_applied_migration():
    brief = E.session_brief(PHASE, 36, findings="- a finding", rnd=1)
    assert f"docs/phases/completed/{PHASE}_live_diff.md" in brief
    assert "never a fix" in brief
