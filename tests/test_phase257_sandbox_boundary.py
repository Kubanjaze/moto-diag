"""Phase 257 — the sandbox is the boundary, and this test is what proves it.

**A "stay in the worktree" instruction is not a boundary** (operator's hard
requirement). Every model stage of the source-transmission orchestrator
runs under `sandbox-exec` with the profile rendered from
`.claude/skills/source-transmission/sandbox.sb.tmpl`. This test renders that
same profile and runs planted attempts through it — no model, no network,
no cost — so a profile edit that opens a hole fails the suite.

**Why credentials are tested and not only writes.** Step 0 found that a
writes-only profile was not a boundary: a dry-run push to GitHub
authenticated through the macOS keychain helper and reported
`[new branch]`. The keychain case below is that same credential path, run
offline, with a control showing the credential is really there outside the
sandbox — a denial of something that does not exist proves nothing.

Planted targets are real paths (this repository, `~/.claude`). If the
sandbox ever leaks, the test removes what it created and fails.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "source-transmission"
sys.path.insert(0, str(SKILL))

from orchestrate import render_profile  # noqa: E402

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or not shutil.which("sandbox-exec"),
    reason="sandbox-exec is macOS-only; the orchestrator runs only there")

HOME = pathlib.Path.home()
PLANT = "PLANTED_257_TEST"
PLANTED_FILES = [ROOT / PLANT, ROOT / ".git" / PLANT, HOME / ".claude" / PLANT, HOME / PLANT]
CRED_HELPER = pathlib.Path(subprocess.run(
    ["git", "--exec-path"], capture_output=True, text=True).stdout.strip()) / "git-credential-osxkeychain"


@pytest.fixture(scope="module")
def box(tmp_path_factory):
    base = tmp_path_factory.mktemp("sbx")
    clone, runtmp = base / "clone", base / "tmp"
    runtmp.mkdir()
    subprocess.run(["git", "init", "-q", str(clone)], check=True)
    subprocess.run(["git", "-C", str(clone), "-c", "user.name=t", "-c", "user.email=t@l",
                    "commit", "-q", "--allow-empty", "-m", "seed"], check=True)
    profile = base / "sandbox.sb"
    profile.write_text(render_profile(clone, runtmp), encoding="utf-8")
    yield {"clone": clone, "tmp": runtmp, "profile": profile}
    for p in PLANTED_FILES:                      # a leak is cleaned, then fails below
        p.unlink(missing_ok=True)
    subprocess.run(["git", "-C", str(ROOT), "branch", "-D", "planted-257-test"],
                   capture_output=True)


def sandboxed(box, *argv, stdin=None):
    return subprocess.run(["sandbox-exec", "-f", str(box["profile"]), *argv],
                          cwd=box["clone"], input=stdin, capture_output=True, text=True,
                          env={**os.environ, "TMPDIR": str(box["tmp"]),
                               "GIT_TERMINAL_PROMPT": "0"}, timeout=120)


class TestPlantedAttemptsFail:
    @pytest.mark.parametrize("target", PLANTED_FILES, ids=["repo-tree", "repo-.git", "~/.claude", "~"])
    def test_a_write_outside_is_denied(self, box, target):
        r = sandboxed(box, "/usr/bin/touch", str(target))
        leaked = target.exists()
        target.unlink(missing_ok=True)
        assert r.returncode != 0 and not leaked, f"sandbox let a write through to {target}"
        assert "Operation not permitted" in r.stderr, r.stderr

    def test_a_python_write_outside_is_denied(self, box):
        r = sandboxed(box, sys.executable, "-c", f"open({str(HOME / PLANT)!r}, 'w').write('x')")
        leaked = (HOME / PLANT).exists()
        (HOME / PLANT).unlink(missing_ok=True)
        assert r.returncode != 0 and not leaked
        assert "Operation not permitted" in r.stderr

    def test_a_push_into_this_repository_is_denied(self, box):
        r = sandboxed(box, "git", "push", str(ROOT), "HEAD:refs/heads/planted-257-test")
        leaked = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q",
                                 "refs/heads/planted-257-test"], capture_output=True).returncode == 0
        assert r.returncode != 0 and not leaked, "a push from the sandbox landed in the repository"

    def test_the_token_file_cannot_be_read(self, box):
        target = HOME / ".config" / "motodiag" / "anthropic.env"
        if not target.exists():
            pytest.fail(f"control missing: {target} must exist to prove its read is denied")
        r = sandboxed(box, "/bin/cat", str(target))
        assert r.returncode != 0 and r.stdout == "" and "Operation not permitted" in r.stderr


class TestTheKeychainCredentialIsUnreachable:
    """The path that leaked in Step 0, run offline."""

    Q = "protocol=https\nhost=github.com\n\n"

    def test_control_the_credential_exists_outside(self):
        r = subprocess.run([str(CRED_HELPER), "get"], input=self.Q, capture_output=True, text=True)
        assert r.returncode == 0 and "\npassword=" in "\n" + r.stdout, (
            "control failed: no GitHub credential in the keychain, so denying it "
            "inside the sandbox would prove nothing")

    def test_the_credential_is_denied_inside(self, box):
        r = sandboxed(box, str(CRED_HELPER), "get", stdin=self.Q)
        assert "password=" not in r.stdout, "the sandbox reached a keychain credential"
        assert r.returncode != 0


class TestControlsInsideSucceed:
    def test_write_and_commit_inside_the_clone(self, box):
        r = sandboxed(box, "/bin/sh", "-c",
                      "echo ok > INSIDE.txt && git add INSIDE.txt && "
                      "git -c user.name=t -c user.email=t@l commit -qm inside")
        assert r.returncode == 0, r.stderr

    def test_sqlite_write_in_the_run_tmp(self, box):
        db = box["tmp"] / "snap.db"
        r = sandboxed(box, sys.executable, "-c",
                      f"import sqlite3; c=sqlite3.connect({str(db)!r}); c.execute('create table t(x)'); c.commit()")
        assert r.returncode == 0, r.stderr

    def test_reading_the_repository_is_allowed(self, box):
        r = sandboxed(box, "/bin/cat", str(ROOT / "CLAUDE.md"))
        assert r.returncode == 0 and "moto-diag" in r.stdout
