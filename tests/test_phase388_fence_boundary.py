"""Phase 388 — the fleet's fence on Linux, and this test is what proves it.

The Mac twin is `tests/test_phase257_sandbox_boundary.py` (macOS
`sandbox-exec`); this file is skipped on macOS, and on Linux it fails rather
than skips when `bwrap` is missing. It runs planted attempts through
`.claude/skills/fleet/fence.sh` itself, no model, no cost, so an edit that
opens a hole fails the suite.

257's eight planted attempts, each with a control showing the target or
credential is really there outside (a denial of something absent proves
nothing): writes to this repository's tree, its `.git`, `~/.claude` and `~`;
a Python write to `~`; a push into this repository; a read of the operator's
login file; a read of `gh`'s credential (Linux's stand-in for 257's
keychain). Then the cases the 388 prompt adds: a push to `master` rejected,
the `workspace-docs` import resolving, F215's planted read of `~/.config`
refused, and the same commands outside the fence succeeding.

Planted targets are real paths. If the fence ever leaks, the test removes
what it created and fails.
"""
from __future__ import annotations

import os
import pathlib
import secrets
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLEET = ROOT / ".claude" / "skills" / "fleet"
FENCE = FLEET / "fence.sh"
WORKSPACE_DOCS = ROOT.parent / "workspace-docs"
sys.path.insert(0, str(FLEET))

from fence_net import allowed  # noqa: E402

@pytest.fixture(scope="module", autouse=True)
def linux_only():
    """Skipped on the Mac, in the form EXPECTED_SKIPS pins (the operator's
    "Mac runs it (Recommended)", Phase 388): the Mac's fence is 257's."""
    if sys.platform == "darwin":
        pytest.skip("macOS: the fence there is sandbox-exec, proven by test_phase257_sandbox_boundary.py")


HOME = pathlib.Path.home()
PLANT = "PLANTED_388_TEST"
PLANTED_FILES = [ROOT / PLANT, ROOT / ".git" / PLANT, HOME / ".claude" / PLANT, HOME / PLANT]
LOGIN_FILE = HOME / ".claude" / ".credentials.json"
GH_CREDENTIAL = HOME / ".config" / "gh" / "hosts.yml"
BRANCH = "planted-388-test"


def test_bwrap_is_installed():
    assert shutil.which("bwrap"), "bwrap is missing: the fleet's fence cannot run on this machine"


@pytest.fixture(scope="module")
def box(tmp_path_factory):
    if not (WORKSPACE_DOCS / "claude" / "working-rules.md").is_file():
        pytest.fail(f"control missing: {WORKSPACE_DOCS} must exist beside the repository")
    base = tmp_path_factory.mktemp("fence")
    clone, run = base / "clone", base / "run"
    run.mkdir()
    subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(ROOT), str(clone)], check=True)
    yield {"base": base, "clone": clone, "run": run}
    for p in PLANTED_FILES:                      # a leak is cleaned, then fails below
        p.unlink(missing_ok=True)
    subprocess.run(["git", "-C", str(ROOT), "branch", "-D", BRANCH], capture_output=True)


def fenced(box, *argv, net="model", env=None, wsdocs=WORKSPACE_DOCS, clone=None):
    return subprocess.run(
        [str(FENCE), "--clone", str(clone or box["clone"]), "--run", str(box["run"]),
         "--workspace-docs", str(wsdocs), "--net", net, "--", *argv],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, **(env or {})})


def branch_exists(name: str) -> bool:
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--verify", "-q",
                           f"refs/heads/{name}"], capture_output=True).returncode == 0


class TestPlantedAttemptsFail:
    """257's eight, on Linux."""

    @pytest.mark.parametrize("target", PLANTED_FILES, ids=["repo-tree", "repo-.git", "~/.claude", "~"])
    def test_a_write_outside_is_refused(self, box, target):
        assert target.parent.is_dir(), f"control: {target.parent} must exist outside the fence"
        r = fenced(box, "/usr/bin/touch", str(target))
        leaked = target.exists()
        target.unlink(missing_ok=True)
        assert r.returncode != 0 and not leaked, f"the fence let a write through to {target}"
        assert "No such file or directory" in r.stderr or "Read-only file system" in r.stderr, r.stderr

    @pytest.mark.parametrize("argv", [("/usr/bin/touch", "/PLANTED_388"),
                                      ("/usr/bin/touch", "/fleet/PLANTED_388"),
                                      ("/usr/bin/mkdir", "-p", "/home/lilcu")],
                             ids=["/", "/fleet", "a /home made inside"])
    def test_the_fences_own_root_is_read_only(self, box, argv):
        r = fenced(box, *argv)
        assert r.returncode != 0 and "Read-only file system" in r.stderr, r.stderr

    def test_a_python_write_outside_is_refused(self, box):
        r = fenced(box, "/usr/bin/python3", "-c", f"open({str(HOME / PLANT)!r}, 'w').write('x')")
        leaked = (HOME / PLANT).exists()
        (HOME / PLANT).unlink(missing_ok=True)
        assert r.returncode != 0 and not leaked
        assert "FileNotFoundError" in r.stderr or "Read-only" in r.stderr, r.stderr

    def test_a_push_into_this_repository_is_refused(self, box):
        r = fenced(box, "git", "push", str(ROOT), f"HEAD:refs/heads/{BRANCH}")
        assert r.returncode != 0 and not branch_exists(BRANCH), \
            "a push from the fence landed in the repository"

    def test_the_login_file_cannot_be_read(self, box):
        if not (LOGIN_FILE.is_file() and os.access(LOGIN_FILE, os.R_OK)):
            pytest.fail(f"control missing: {LOGIN_FILE} must exist to prove its read is refused")
        r = fenced(box, "/usr/bin/cat", str(LOGIN_FILE))
        assert r.returncode != 0 and r.stdout == "" and "No such file" in r.stderr

    def test_the_gh_credential_cannot_be_read(self, box):
        if not (GH_CREDENTIAL.is_file() and os.access(GH_CREDENTIAL, os.R_OK)):
            pytest.fail(f"control missing: {GH_CREDENTIAL} must exist to prove its read is refused")
        r = fenced(box, "/usr/bin/cat", str(GH_CREDENTIAL))
        assert r.returncode != 0 and r.stdout == "" and "No such file" in r.stderr


class TestPushToMaster:
    def test_a_push_to_master_through_origin_is_rejected(self, box):
        before = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "master"],
                                capture_output=True, text=True).stdout
        r = fenced(box, "/bin/sh", "-c", "git -c user.name=t -c user.email=t@l commit -q "
                   "--allow-empty -m planted && git push origin HEAD:master")
        after = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "master"],
                               capture_output=True, text=True).stdout
        assert r.returncode != 0 and before == after, "master moved from inside the fence"

    def test_a_push_to_github_is_refused_by_the_gate(self, box):
        r = fenced(box, "git", "push", "https://github.com/Kubanjaze/moto-diag.git",
                   f"HEAD:refs/heads/{BRANCH}")
        assert r.returncode != 0 and "403" in r.stderr, r.stderr
        assert "DENY CONNECT github.com:443" in (box["run"] / "net.log").read_text()


class TestTheWorkspaceDocsImport:
    """The ninth case: a fence that cannot see workspace-docs passes every
    write test and runs with no workspace rules (388_step0.md S0-2)."""

    def test_the_import_path_resolves_inside(self, box):
        r = fenced(box, "/usr/bin/head", "-1", "../workspace-docs/claude/working-rules.md")
        first = (WORKSPACE_DOCS / "claude" / "working-rules.md").read_text().splitlines()[0]
        assert r.returncode == 0 and r.stdout.strip() == first, r.stderr

    def test_workspace_docs_is_read_only(self, box):
        r = fenced(box, "/usr/bin/touch", f"../workspace-docs/{PLANT}")
        leaked = (WORKSPACE_DOCS / PLANT).exists()
        (WORKSPACE_DOCS / PLANT).unlink(missing_ok=True)
        assert r.returncode != 0 and not leaked and "Read-only file system" in r.stderr

    def test_the_approval_is_seeded_for_the_fences_clone_path(self, box):
        fenced(box, "true")
        import json
        config = json.loads((box["run"] / "claude" / ".claude.json").read_text())
        project = config["projects"]["/fleet/moto-diag"]
        assert project["hasClaudeMdExternalIncludesApproved"] is True

    def test_a_fence_without_workspace_docs_is_refused(self, box, tmp_path):
        r = fenced(box, "true", wsdocs=tmp_path)
        assert r.returncode == 2 and "working-rules.md" in r.stderr


class TestF215ReadsAreConfined:
    """F215: on the Mac the read-only ranks could read anything a denylist
    missed. Here the operator's home is not in the fence at all."""

    def test_a_planted_canary_under_config_is_refused(self, box):
        folder = HOME / ".config" / "motodiag-fence-canary-388"
        folder.mkdir(exist_ok=True)
        token = "CANARY-" + secrets.token_hex(8)
        (folder / "secret.txt").write_text(token + "\n")
        try:
            assert (folder / "secret.txt").read_text().strip() == token   # control: readable outside
            r = fenced(box, "/bin/sh", "-c", f"cat {folder}/secret.txt; ls {folder}; grep -r CANARY {folder}")
        finally:
            shutil.rmtree(folder, ignore_errors=True)
        assert token not in r.stdout + r.stderr and r.returncode != 0

    def test_a_canary_elsewhere_in_the_home_is_refused_too(self, box):
        canary = HOME / f".fence-canary-388-{secrets.token_hex(4)}"
        token = "CANARY-" + secrets.token_hex(8)
        canary.write_text(token)
        try:
            r = fenced(box, "/usr/bin/cat", str(canary))
        finally:
            canary.unlink(missing_ok=True)
        assert token not in r.stdout and r.returncode != 0, "a home path outside any list was read"


class TestTheNetwork:
    @pytest.mark.parametrize("net", ["model", "none"])
    def test_a_direct_connection_is_unreachable(self, box, net):
        r = fenced(box, "/usr/bin/python3", "-c",
                   "import socket; socket.create_connection(('140.82.112.3', 443), 3)", net=net)
        assert r.returncode != 0 and "Network is unreachable" in r.stderr, r.stderr

    def test_the_gate_answers_403_to_a_host_not_allowed(self, box):
        r = fenced(box, "/usr/bin/curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                   "https://example.com/")
        assert r.returncode != 0 and "DENY CONNECT example.com:443" in (box["run"] / "net.log").read_text()

    @pytest.mark.parametrize("line,expected", [
        ("CONNECT api.anthropic.com:443 HTTP/1.1", ("api.anthropic.com", 443)),
        ("CONNECT API.Anthropic.com:443 HTTP/1.1", ("api.anthropic.com", 443)),
        ("CONNECT github.com:443 HTTP/1.1", None),
        ("CONNECT api.anthropic.com:80 HTTP/1.1", None),
        ("CONNECT api.anthropic.com.evil.example:443 HTTP/1.1", None),
        ("GET http://api.anthropic.com/ HTTP/1.1", None),
        ("CONNECT api.anthropic.com HTTP/1.1", None),
    ])
    def test_the_gate_allows_the_model_api_only(self, line, expected):
        assert allowed(line) == expected


class TestTheEnvironment:
    def test_only_the_token_crosses(self, box):
        r = fenced(box, "/usr/bin/env", env={"CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat-test",
                                             "ANTHROPIC_API_KEY": "sk-ant-api-test",
                                             "PLANTED_388_VAR": "x"})
        names = {ln.split("=", 1)[0] for ln in r.stdout.splitlines()}
        assert "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat-test" in r.stdout
        assert "ANTHROPIC_API_KEY" not in names and "PLANTED_388_VAR" not in names
        assert "HOME=/fleet/run/home" in r.stdout and "CLAUDE_CONFIG_DIR=/fleet/run/claude" in r.stdout

    def test_the_token_is_never_on_a_command_line(self):
        assert "--setenv CLAUDE_CODE_OAUTH_TOKEN" not in FENCE.read_text()


class TestControlsSucceed:
    """The same commands outside the fence, and the ones it must allow."""

    def test_the_planted_write_succeeds_outside_the_fence(self, box, tmp_path):
        target = tmp_path / PLANT
        assert fenced(box, "/usr/bin/touch", str(target)).returncode != 0 and not target.exists()
        assert subprocess.run(["/usr/bin/touch", str(target)]).returncode == 0 and target.exists()

    def test_the_planted_push_succeeds_outside_the_fence(self, box, tmp_path):
        bare = tmp_path / "bare.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        assert fenced(box, "git", "push", str(bare), "HEAD:refs/heads/x").returncode != 0
        r = subprocess.run(["git", "-C", str(box["clone"]), "push", "-q", str(bare), "HEAD:refs/heads/x"],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

    def test_write_and_commit_inside_the_clone(self, box):
        r = fenced(box, "/bin/sh", "-c", "echo ok > INSIDE.txt && git add INSIDE.txt && "
                   "git -c user.name=t -c user.email=t@l commit -qm inside")
        assert r.returncode == 0, r.stderr
        assert (box["clone"] / "INSIDE.txt").read_text() == "ok\n"

    def test_write_in_the_run_directory(self, box):
        r = fenced(box, "/bin/sh", "-c", "echo ok > /fleet/run/inside.txt")
        assert r.returncode == 0 and (box["run"] / "inside.txt").exists()


class TestRefusals:
    def test_the_operators_checkout_is_refused_as_the_clone(self, box):
        r = fenced(box, "true", clone=ROOT)
        assert r.returncode == 2 and "runs from" in r.stderr

    def test_no_run_directory_is_refused(self, box, tmp_path):
        r = subprocess.run([str(FENCE), "--clone", str(box["clone"]), "--run", str(tmp_path / "no"),
                            "--workspace-docs", str(WORKSPACE_DOCS), "--", "true"],
                           capture_output=True, text=True)
        assert r.returncode == 2 and "no run directory" in r.stderr

    def test_no_bwrap_is_refused(self, box, tmp_path):
        (tmp_path / "dirname").symlink_to(shutil.which("dirname"))
        r = subprocess.run(["/bin/bash", str(FENCE), "--clone", str(box["clone"]), "--run",
                            str(box["run"]), "--workspace-docs", str(WORKSPACE_DOCS), "--", "true"],
                           capture_output=True, text=True, env={"PATH": str(tmp_path)})
        assert r.returncode == 2 and "bwrap is not installed" in r.stderr
