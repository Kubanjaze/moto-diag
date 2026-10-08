"""Phase 378, K18 — one deploy order, enforced.

The order: the regression of record, then `deploy.py apply-live` from the
branch (it reads the scope and the approved diff from `in_progress/`), then
the close-out commit that moves the deploy files, then the merge. 376 applied
083 before its regression; nothing stopped it. Now `apply-live` refuses unless
the phase log carries a regression line A5 can read, no code path changed
between its commit and HEAD, and no code path is uncommitted.

Every case runs on 358's fixture repository and databases.
"""

from __future__ import annotations

import pathlib
import shutil

from test_phase358_deploy_contract import (  # noqa: F401  (env is a fixture)
    D, PHASE, ROOT, _commit_diff, _dryrun, _git, _refusal, env, migrate_in_scope,
    record_regression,
)

FIXTURES = ROOT / ".claude" / "skills" / "deploy" / "fixtures" / "k18"


def _log(env) -> pathlib.Path:
    return env["repo"] / "docs" / "phases" / "in_progress" / f"{PHASE}_phase_log.md"


def _ready(env):
    assert _dryrun(env) == 0
    _commit_diff(env)


def _code_change(env, path="src/motodiag/core/migrations.py"):
    f = env["repo"] / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("# changed after the regression\n")
    _git(env["repo"], "add", str(f))
    _git(env["repo"], "commit", "-qm", "a code change")


class TestTheRefusals:
    def test_no_phase_log(self, env, capsys):
        _ready(env)
        _log(env).unlink()
        _git(env["repo"], "commit", "-qam", "the log removed")
        assert "no phase log" in _refusal(env, capsys)

    def test_a_log_with_no_regression_line(self, env, capsys):
        _ready(env)
        shutil.copy(FIXTURES / "no_regression_line.md", _log(env))
        _git(env["repo"], "commit", "-qam", "the known-bad log")
        assert "has no regression of record that A5 can read" in _refusal(env, capsys)

    def test_a_regression_line_a5_cannot_read(self, env, capsys):
        _ready(env)
        shutil.copy(FIXTURES / "unparsable_regression_line.md", _log(env))
        _git(env["repo"], "commit", "-qam", "the known-bad log")
        assert "has no regression of record that A5 can read" in _refusal(env, capsys)

    def test_code_changed_after_the_regression(self, env, capsys):
        _ready(env)
        _code_change(env)
        err = _refusal(env, capsys)
        assert "code changed after the regression of record" in err
        assert "src/motodiag/core/migrations.py" in err

    def test_a_skill_script_is_code_too(self, env, capsys):
        """verify_phase's check 2 scope (F137): `.claude/` is code."""
        _ready(env)
        _code_change(env, ".claude/skills/deploy/deploy.py")
        assert "code changed after the regression of record" in _refusal(env, capsys)

    def test_uncommitted_code(self, env, capsys):
        _ready(env)
        f = env["repo"] / "src" / "motodiag" / "core" / "new_migration.py"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("# not committed\n")
        assert "uncommitted code in the working tree" in _refusal(env, capsys)

    def test_a_regression_commit_that_does_not_resolve(self, env, capsys):
        _ready(env)
        text = _log(env).read_text()
        commit = text.split("at `", 1)[1].split("`", 1)[0]
        _log(env).write_text(text.replace(commit, "deadbee"))
        _git(env["repo"], "commit", "-qam", "a log naming no commit")
        assert "which is not a commit here" in _refusal(env, capsys)


class TestWhatItAllows:
    def test_documents_after_the_regression_are_allowed(self, env):
        """The dry-run diff and the log are committed after the regression;
        they are documents, so the apply goes ahead."""
        _ready(env)
        notes = env["repo"] / "docs" / "phases" / "in_progress" / f"{PHASE}_step0.md"
        notes.write_text("notes\n")
        _git(env["repo"], "add", str(notes))
        _git(env["repo"], "commit", "-qm", "docs only")
        assert D.apply_live(PHASE, db=env["live"], repo=env["repo"],
                            migrate=migrate_in_scope) == 0

    def test_a_rerun_after_a_code_change_clears_it(self, env):
        """The last regression line counts (A5's rule), so a re-run recorded
        after the change lets the apply go ahead."""
        _ready(env)
        _code_change(env)
        record_regression(env["repo"])
        assert D.regression_problem(env["repo"], PHASE) is None


class TestTheSkillStatesTheOrder:
    def test_the_close_out_sequence_names_one_order(self):
        skill = (ROOT / ".claude" / "skills" / "closeout" / "SKILL.md").read_text()
        assert ("the regression of record, then `deploy.py apply-live` from the branch, "
                "then the close-out commit, then the merge") in " ".join(skill.split())
        assert "Merge, then deploy" not in skill
