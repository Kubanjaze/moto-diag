"""Phase 358, K1 — the whole-tree command, its record, and the guard that
runs it.

What this holds:

* the census finds the checks behind 257–260's five red regressions, and the
  fast/full split keeps them in fast mode;
* a record is accepted only for the exact commit, tree and script that
  `wholetree.sh` passed on, and only when it carries the command's signature;
* the guard blocks on a failure, on a missing record it cannot test in
  place, and when fast mode runs out of time — it fails closed;
* a commit that changes seed data or migrations.py needs a `--full` record;
* `regression.sh` refuses to start without a `--full` record for HEAD.

Every git repository here is a tmp one. Nothing writes into this checkout's
`.git` or the real record key.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLOSEOUT = ROOT / ".claude" / "skills" / "closeout"
sys.path.insert(0, str(CLOSEOUT))

import _pre_push_guard as guard  # noqa: E402
import wholetree as W  # noqa: E402

#: The four checks behind the five red regressions of 257–260, and rule 3's
#: test files. Every one must be in fast mode, or the guard misses it again.
_MUST_BE_FAST = {
    "tests/test_phase191c_f9_lint.py",             # 257: a literal model ID
    "tests/test_f124_schema_pin_discipline.py",    # 258, 260: a schema-head pin
    "tests/test_phase209B_integration_gaps.py",    # 259: the allowlist
    "tests/test_phase244U_gate_blind_spot.py",     # 259: a pinned count
    "tests/test_phase244G_guard_shapes.py",
    "tests/test_roadmap_continuity.py",
}


class TestTheCensus:
    def test_the_checks_behind_257_to_260_are_in_fast_mode(self):
        fast = set(W.members("fast"))
        assert _MUST_BE_FAST <= fast, sorted(_MUST_BE_FAST - fast)

    def test_full_is_every_member_and_contains_fast(self):
        c = W.census()
        full = set(W.members("full"))
        # Phase 357 (F175) added the ledger class, full-only.
        assert full == set(c["code"]) | set(c["seed"]) | set(c["outside"]) | set(c["ledger"])
        assert set(W.members("fast")) < full

    def test_the_split_excludes_by_its_stated_rule_and_nothing_else(self):
        """The exclusion's control: what fast mode drops from the code class
        is exactly the gates and the wheel build."""
        c = W.census()
        dropped = set(c["code"]) - set(W.members("fast"))
        assert dropped, "the control needs something excluded"
        for f in dropped:
            name = pathlib.Path(f).name
            assert W._GATE.search(name) or name == W._WHEEL_BUILD, f
        assert not set(c["seed"]) & set(W.members("fast"))
        assert not set(c["ledger"]) & set(W.members("fast"))

    @pytest.mark.parametrize("name,is_gate", [
        ("test_phase240_gate12.py", True), ("test_phase133_gate_5.py", True),
        ("test_phase121_gate_r.py", True), ("test_gate1_integration.py", True),
        ("test_phase244U_gate_blind_spot.py", False),
    ])
    def test_what_counts_as_a_gate(self, name, is_gate):
        assert bool(W._GATE.search(name)) is is_gate

    def test_a_new_whole_tree_test_joins_by_itself(self, tmp_path):
        """Membership by rule, not by list: a test that walks src/ is a
        member without anyone adding it, and a seed walker is full-only."""
        for d in ("tests", "tests/support", "scripts", ".claude/skills"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        (tmp_path / "tests" / "test_new_walker.py").write_text(
            "def test_x():\n    list(SRC.rglob('*.py'))\n")
        (tmp_path / "tests" / "test_new_seed.py").write_text(
            "def test_y():\n    list(K.glob('known_issues_*.json'))\n")
        (tmp_path / "tests" / "test_plain.py").write_text("def test_z():\n    assert 1\n")
        assert W.members("fast", tmp_path) == ["tests/test_new_walker.py"]
        assert W.members("full", tmp_path) == ["tests/test_new_seed.py",
                                               "tests/test_new_walker.py"]


def _repo(tmp_path: pathlib.Path) -> pathlib.Path:
    r = tmp_path / "repo"
    r.mkdir()
    g = ["git", "-C", str(r)]
    subprocess.run(g + ["init", "-q", "-b", "main"], check=True)
    subprocess.run(g + ["config", "user.email", "t@t"], check=True)
    subprocess.run(g + ["config", "user.name", "t"], check=True)
    (r / "src/motodiag/knowledge/seed").mkdir(parents=True)
    (r / "src/motodiag/knowledge/seed/known_issues_x.json").write_text("[]\n")
    (r / "README.md").write_text("x\n")
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-qm", "one"], check=True)
    return r


def _head(r):
    return (guard._rev(r, "HEAD"), guard._rev(r, "HEAD^{tree}"))


@pytest.fixture
def key(tmp_path, monkeypatch):
    k = tmp_path / "key"
    monkeypatch.setattr(W, "key_path", lambda: k)
    return k


class TestTheRecord:
    def test_a_record_the_command_wrote_is_accepted(self, tmp_path, key):
        r = _repo(tmp_path)
        c, t = _head(r)
        W.write_record("fast", c, t, "1 passed", 1.0, root=r)
        rec, why = W.valid_record(t, ("fast",), c, root=r)
        assert rec is not None, why
        assert oct(key.stat().st_mode & 0o777) == "0o600"

    def test_an_amended_commit_does_not_inherit_the_record(self, tmp_path, key):
        """The operator's control 1, in miniature: same tree, new commit."""
        r = _repo(tmp_path)
        c, t = _head(r)
        W.write_record("fast", c, t, "1 passed", 1.0, root=r)
        subprocess.run(["git", "-C", str(r), "commit", "-q", "--amend", "-m", "two"], check=True)
        c2, t2 = _head(r)
        assert t2 == t and c2 != c
        rec, why = W.valid_record(t2, ("fast",), c2, root=r)
        assert rec is None and "records commit" in why

    def test_another_tree_has_no_record(self, tmp_path, key):
        r = _repo(tmp_path)
        c, t = _head(r)
        W.write_record("fast", c, t, "1 passed", 1.0, root=r)
        (r / "README.md").write_text("y\n")
        subprocess.run(["git", "-C", str(r), "commit", "-qam", "change"], check=True)
        c2, t2 = _head(r)
        assert W.valid_record(t2, ("fast",), c2, root=r)[0] is None

    def test_a_changed_command_invalidates_the_record(self, tmp_path, key, monkeypatch):
        r = _repo(tmp_path)
        c, t = _head(r)
        W.write_record("fast", c, t, "1 passed", 1.0, root=r)
        monkeypatch.setattr(W, "script_hash", lambda *a: "0" * 64)
        rec, why = W.valid_record(t, ("fast",), c, root=r)
        assert rec is None and "different wholetree script" in why

    @pytest.mark.parametrize("forge", ["no mac", "wrong mac", "edited after signing"])
    def test_a_record_not_written_by_the_command_is_rejected(self, tmp_path, key, forge):
        """The operator's control 2, in miniature: a hand-written pass."""
        r = _repo(tmp_path)
        c, t = _head(r)
        path = W.write_record("fast", c, t, "1 passed", 1.0, root=r)
        rec = json.loads(path.read_text())
        if forge == "no mac":
            del rec["mac"]
        elif forge == "wrong mac":
            rec["mac"] = "0" * 64
        else:
            rec["summary"] = "9999 passed"
        path.write_text(json.dumps(rec))
        got, why = W.valid_record(t, ("fast",), c, root=r)
        assert got is None and "not written by wholetree.sh" in why

    def test_without_the_key_nothing_is_valid(self, tmp_path, key):
        r = _repo(tmp_path)
        c, t = _head(r)
        W.write_record("fast", c, t, "1 passed", 1.0, root=r)
        key.unlink()
        assert W.valid_record(t, ("fast",), c, root=r)[0] is None

    def test_no_record_is_written_for_a_tree_no_hash_names(self, tmp_path):
        r = _repo(tmp_path)
        assert W.tested_state(r) == _head(r)
        (r / "README.md").write_text("dirty\n")
        assert W.tested_state(r) is None
        subprocess.run(["git", "-C", str(r), "checkout", "--", "README.md"], check=True)
        (r / "untracked.py").write_text("x = 1\n")
        assert W.tested_state(r) is None


class TestThePushGate:
    def _never(self, *a):
        raise AssertionError("the guard ran fast mode although a record was valid")

    def test_a_valid_record_is_accepted_without_a_run(self, tmp_path, key):
        r = _repo(tmp_path)
        c, t = _head(r)
        W.write_record("fast", c, t, "1 passed", 1.0, root=r)
        assert guard.wholetree_gate("git push origin main", r, run=self._never) == []

    def test_a_full_record_also_serves(self, tmp_path, key):
        r = _repo(tmp_path)
        c, t = _head(r)
        W.write_record("full", c, t, "1 passed", 1.0, root=r)
        assert guard.wholetree_gate("git push", r, run=self._never) == []

    def test_a_timeout_blocks(self, tmp_path, key):
        r = _repo(tmp_path)
        fails = guard.wholetree_gate(
            "git push", r, run=lambda *a: W.Result(False, "x", 99.0, timed_out=True))
        assert fails and "ran out of time" in fails[0] and "fails closed" in fails[0]

    def test_a_failure_blocks(self, tmp_path, key):
        r = _repo(tmp_path)
        fails = guard.wholetree_gate("git push", r, run=lambda *a: W.Result(False, "1 failed", 5.0))
        assert fails and "failed" in fails[0]

    def test_a_pass_that_leaves_no_record_blocks(self, tmp_path, key):
        r = _repo(tmp_path)
        fails = guard.wholetree_gate("git push", r, run=lambda *a: W.Result(True, "ok", 5.0))
        assert fails and "no valid record" in fails[0]

    def test_a_commit_that_is_not_checked_out_is_not_run_but_blocked(self, tmp_path, key):
        r = _repo(tmp_path)
        subprocess.run(["git", "-C", str(r), "branch", "other"], check=True)
        (r / "README.md").write_text("z\n")
        subprocess.run(["git", "-C", str(r), "commit", "-qam", "ahead"], check=True)
        fails = guard.wholetree_gate("git push origin other", r, run=self._never)
        assert fails and "clean checkout" in fails[0]

    def test_a_dirty_tree_is_not_run_but_blocked(self, tmp_path, key):
        r = _repo(tmp_path)
        (r / "README.md").write_text("dirty\n")
        fails = guard.wholetree_gate("git push", r, run=self._never)
        assert fails and "clean checkout" in fails[0]

    @pytest.mark.parametrize("command", ["git push --all", "git push origin no-such-ref"])
    def test_a_push_it_cannot_resolve_is_blocked(self, tmp_path, key, command):
        assert guard.wholetree_gate(command, _repo(tmp_path), run=self._never)

    def test_a_deletion_sends_nothing(self, tmp_path, key):
        assert guard.wholetree_gate("git push origin :old", _repo(tmp_path), run=self._never) == []


class TestTheDeadline:
    def test_the_bounded_run_kills_the_command_and_reports_a_timeout(self, tmp_path, monkeypatch):
        """run_bounded against a stand-in command that sleeps: it must come
        back at the limit, report timed_out, and leave no process behind."""
        marker = tmp_path / "still_running"
        (tmp_path / "wholetree.sh").write_text(
            f"#!/bin/sh\nsleep 30\ntouch {marker}\n")
        (tmp_path / "wholetree.sh").chmod(0o755)
        monkeypatch.setattr(W, "HERE", tmp_path)
        t0 = time.monotonic()
        res = W.run_bounded("fast", 1.0, tmp_path)
        assert res.timed_out and not res.passed
        assert time.monotonic() - t0 < 10
        assert not marker.exists()

    def test_the_limit_sits_far_inside_the_hook_timeout(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text())
        timeout = settings["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"]
        assert W.FAST_LIMIT_S + 60 < timeout, (W.FAST_LIMIT_S, timeout)


class TestTheContentCommitGate:
    def _stage_seed(self, r):
        (r / "src/motodiag/knowledge/seed/known_issues_x.json").write_text('[{"a": 1}]\n')

    def test_a_staged_seed_change_needs_a_full_record(self, tmp_path, key):
        r = _repo(tmp_path)
        self._stage_seed(r)
        subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
        fails = guard.content_commit_gate("git commit -m x", r)
        assert fails and "wholetree.sh --full" in fails[0]
        tree = guard._tree_with(r)
        W.write_record("full", guard._rev(r, "HEAD"), tree, "1 passed", 1.0, root=r)
        assert guard.content_commit_gate("git commit -m x", r) == []

    def test_a_fast_record_does_not_serve_a_content_commit(self, tmp_path, key):
        r = _repo(tmp_path)
        self._stage_seed(r)
        subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
        W.write_record("fast", guard._rev(r, "HEAD"), guard._tree_with(r), "1 passed", 1.0, root=r)
        assert guard.content_commit_gate("git commit -m x", r)

    @pytest.mark.parametrize("command", [
        "git commit -am x",
        "git commit -m x -- src/motodiag/knowledge/seed/known_issues_x.json",
        "git commit -q -F - <<'M'\nmsg; with & and it's\nM",
    ])
    def test_every_shape_of_a_seed_commit_is_seen(self, tmp_path, key, command):
        r = _repo(tmp_path)
        self._stage_seed(r)                  # unstaged: -a and pathspec pick it up
        if "<<" in command:
            subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
        assert guard.content_commit_gate(command, r), command

    def test_a_docs_commit_passes(self, tmp_path, key):
        r = _repo(tmp_path)
        (r / "README.md").write_text("docs\n")
        subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
        assert guard.content_commit_gate("git commit -m docs", r) == []


class TestTheWiring:
    """Each gate is called from its one integration point."""

    def _main(self, monkeypatch, command):
        class _In:
            def read(self, *_):
                return json.dumps({"tool_input": {"command": command}})
        monkeypatch.setattr(sys, "stdin", _In())
        return guard.main()

    def test_a_push_goes_through_the_whole_tree_gate(self, monkeypatch, capsys):
        import roadmap_check
        monkeypatch.setattr(roadmap_check, "check_tree", lambda *a, **k: [])
        monkeypatch.setattr(guard, "wholetree_gate", lambda *a, **k: ["planted refusal"])
        assert self._main(monkeypatch, "git push origin some-branch") == 2
        assert "planted refusal" in capsys.readouterr().err

    def test_a_commit_goes_through_the_content_gate(self, monkeypatch, capsys):
        monkeypatch.setattr(guard, "content_commit_gate", lambda *a, **k: ["planted refusal"])
        assert self._main(monkeypatch, "git commit -m x") == 2
        assert "planted refusal" in capsys.readouterr().err

    @pytest.mark.parametrize("command,mover", [
        ("git commit -m x && git push", "commit"),
        ("git add -A; git commit -q -F - <<'M'\nmsg; it's\nM\ngit push origin b", "commit"),
        ("git rebase master && git push -f", "rebase"),
        ("git push", None),
        ("git push && git commit -m after", None),
        ("git log -1; git push", None),
    ])
    def test_a_push_after_a_head_move_in_one_command_is_seen(self, command, mover):
        """Found live in 358: the hook judges the whole command line before
        it runs, so a commit and a push together would push an unchecked
        commit on the strength of the old HEAD's record."""
        assert guard.moves_head_before_push(command) == mover

    def test_a_commit_and_push_together_are_blocked(self, monkeypatch, capsys):
        monkeypatch.setattr(guard, "wholetree_gate", lambda *a, **k: [])
        assert self._main(monkeypatch, "git commit -m x && git push") == 2
        assert "separate commands" in capsys.readouterr().err

    def test_an_error_in_the_whole_tree_gate_blocks(self, monkeypatch, capsys):
        import roadmap_check
        monkeypatch.setattr(roadmap_check, "check_tree", lambda *a, **k: [])

        def boom(*a, **k):
            raise RuntimeError("planted")
        monkeypatch.setattr(guard, "wholetree_gate", boom)
        assert self._main(monkeypatch, "git push") == 2

    def test_regression_sh_refuses_without_a_full_record(self, tmp_path):
        """Behaviour, not text: a clean repository holding the closeout
        scripts and no record. regression.sh must stop before any test runs."""
        r = tmp_path / "repo"
        shutil.copytree(CLOSEOUT, r / ".claude" / "skills" / "closeout",
                        ignore=shutil.ignore_patterns("__pycache__", "fixtures"))
        g = ["git", "-C", str(r)]
        subprocess.run(g + ["init", "-q"], check=True)
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
                       check=True)
        env = {**os.environ, "HOME": str(tmp_path)}      # no real key reachable
        p = subprocess.run([str(r / ".claude/skills/closeout/regression.sh")], cwd=r,
                           capture_output=True, text=True, env=env, timeout=60)
        assert p.returncode == 2, p.stdout + p.stderr
        assert "wholetree.sh --full" in p.stderr
        assert "Regression of record" not in p.stdout
