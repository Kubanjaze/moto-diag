"""Phase 389 — the dispatcher's push gate and the identity it pushes in.

What must hold (the 389 prompt and Step 0, S0-4): nothing a rank wrote is
pushed unchecked, because the push guard is a hook that fires only inside a
Claude session; the push identity never enters the fence, and the
operator's own login is used only for a planted trial until the fleet's
machine user exists (pre-approval (b)).

Each hand-written case in `fixtures/push_gate/cases.json` is applied to a
real git clone of a repository built from 387's good fixture tree and must
fail on exactly its own G-id; the good cases must pass.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
sys.path.insert(0, str(SKILL))

import fleet_git as G  # noqa: E402
from plan_check import GOOD  # noqa: E402

CASES = json.loads((SKILL / "fixtures" / "push_gate" / "cases.json").read_text())
BRANCH = "phase-900-fixture"
FLEET_TOKEN = "ghp_" + "Ab3d" * 9


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def make_origin(base: pathlib.Path) -> pathlib.Path:
    """387's good tree, made to pass the ledger check: the real authority
    contract and the handoff its closed row 898 needs (R6)."""
    src = base / "origin"
    shutil.copytree(GOOD, src)
    shutil.copy(ROOT / "ROADMAP_AUTHORITY.md", src / "ROADMAP_AUTHORITY.md")
    (src / "docs" / "handoffs").mkdir(parents=True)
    (src / "docs" / "handoffs" / "2026-10-03_898_closed.md").write_text("# 898\n\nNext: 900.\n")
    git("init", "-q", "-b", "master", cwd=src)
    git("add", "-A", cwd=src)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "good", cwd=src)
    git("branch", BRANCH, cwd=src)
    return src


@pytest.fixture(scope="module")
def origin(tmp_path_factory):
    return make_origin(tmp_path_factory.mktemp("gate"))


def clone_with(origin: pathlib.Path, dest: pathlib.Path, branch: str, edits: list[dict]) -> str:
    """A clone on `branch` with the edits committed; returns the base commit."""
    git("clone", "-q", str(origin), str(dest), cwd=dest.parent)
    start = BRANCH if branch.startswith("phase-900") else "master"
    git("switch", "-q", "-C", branch, f"origin/{start}", cwd=dest)
    base = git("rev-parse", "HEAD", cwd=dest).stdout.strip()
    for e in edits:
        p = dest / e["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        if "write" in e:
            p.write_text(e["write"])
        elif "append" in e:
            p.write_text(p.read_text().rstrip("\n") + "\n" + e["append"] + "\n")
        else:
            old, new = e["replace"]
            text = p.read_text()
            assert text.count(old) == 1, f"{e['path']}: {old!r} occurs {text.count(old)} times"
            p.write_text(text.replace(old, new))
    git("add", "-A", cwd=dest)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "the case", cwd=dest)
    return base


def passed(_commit):
    return True, ""


@pytest.mark.parametrize("case", CASES["good"], ids=[c["id"] for c in CASES["good"]])
def test_each_good_push_passes(origin, tmp_path, case):
    base = clone_with(origin, tmp_path / "c", case["branch"], case["edits"])
    assert G.gate(tmp_path / "c", rank=case["rank"], phase="900", branch=case["branch"], base=base,
                  tested=passed, mobile=None) == []


@pytest.mark.parametrize("case", CASES["bad"], ids=[c["id"] for c in CASES["bad"]])
def test_each_known_bad_push_fails_on_its_own_item(origin, tmp_path, case):
    base = clone_with(origin, tmp_path / "c", case["branch"], case["edits"])
    fails = G.gate(tmp_path / "c", rank=case["rank"], phase="900", branch=case["branch"],
                   base=base, tested=passed, mobile=None)
    assert fails and {f.split()[0] for f in fails} == {case["item"]}, fails


def test_a_push_that_is_not_a_fast_forward(origin, tmp_path):
    """GitHub's branch has a commit the clone's HEAD lacks: a push would
    rewrite history."""
    clone = tmp_path / "c"
    base = clone_with(origin, clone, BRANCH, [{"path": "a.txt", "write": "a\n"}])
    git("switch", "-q", "-c", "elsewhere", base, cwd=clone)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-q", "--allow-empty", "-m", "z",
        cwd=clone)
    github_has = git("rev-parse", "HEAD", cwd=clone).stdout.strip()
    git("switch", "-q", BRANCH, cwd=clone)
    fails = G.gate(clone, rank="engineer", phase="900", branch=BRANCH, base=github_has,
                   tested=passed, mobile=None)
    assert [f.split()[0] for f in fails] == ["G2"], fails


def test_a_commit_no_model_free_run_passed(origin, tmp_path):
    base = clone_with(origin, tmp_path / "c", BRANCH, [{"path": "src/motodiag/x.py", "write": "X = 1\n"}])
    fails = G.gate(tmp_path / "c", rank="engineer", phase="900", branch=BRANCH, base=base,
                   tested=lambda c: (False, "3 failed"), mobile=None)
    assert [f.split()[0] for f in fails] == ["G6"] and "3 failed" in fails[0]


def test_the_untested_check_runs_only_when_everything_else_passed(origin, tmp_path):
    seen = []
    base = clone_with(origin, tmp_path / "c", "master", [{"path": "a.txt", "write": "a\n"}])
    G.gate(tmp_path / "c", rank="engineer", phase="900", branch="master", base=base,
           tested=lambda c: seen.append(c) or (True, ""), mobile=None)
    assert seen == [], "a model-free run was spent on a push that was refused anyway"


class TestThePaths:
    @pytest.mark.parametrize("rank,path,ok", [
        ("scout", "docs/phases/in_progress/900_step0.md", True),
        ("scout", "docs/prompts/900_the_mission.txt", True),
        ("scout", "docs/prompts/901_other.txt", False),
        ("scout", "docs/phases/in_progress/900_implementation.md", False),
        ("captain", "docs/phases/in_progress/900_implementation.md", True),
        ("captain", "src/motodiag/x.py", False),
        ("red-team-record", "docs/phases/completed/900_phase_log.md", True),
        ("red-team-record", "docs/phases/completed/900_implementation.md", False),
        ("engineer", "src/motodiag/x.py", True),
        ("engineer", "CLAUDE.md", False),
        ("engineer", ".claude/skills/fleet/scout.py", False),
        ("engineer", ".claude/skills/closeout/pre_push_guard.sh", False),
        ("engineer", ".claude/skills/closeout/closeout_check.py", True),
        ("nobody", "README.md", False),
    ])
    def test_may_touch(self, rank, path, ok):
        assert G.may_touch(rank, "900", path) is ok


class TestTheSecretPattern:
    @pytest.mark.parametrize("line", [
        "sk-ant-oat01-test-token",                       # 388's test token
        "sk-ant-oat01-FAKETOKEN389-Ab9_-Ab9_-Ab9_-",      # 388's fence test
        "ghp_short", "github_pat_short",
    ])
    def test_a_tests_fake_token_is_not_a_credential(self, line):
        assert not G.SECRET.search(line)

    @pytest.mark.parametrize("line", [
        "sk-ant-oat01-" + "A" * 95, "sk-ant-api03-" + "B" * 93, "ghp_" + "C" * 36,
        "github_pat_" + "D" * 82, "sk-gw-" + "E" * 40,
    ])
    def test_a_real_shaped_credential_is(self, line):
        assert G.SECRET.search(line)


class TestTheIdentity:
    def write(self, tmp_path, text, mode=0o600):
        p = tmp_path / "fleet-github.env"
        p.write_text(text)
        p.chmod(mode)
        return p

    def test_the_fleets_account(self, tmp_path):
        p = self.write(tmp_path, f"FLEET_GITHUB_USER=motodiag-fleet\nFLEET_GITHUB_TOKEN={FLEET_TOKEN}\n")
        ident = G.identity("any issue", p)
        assert ident == G.Identity("motodiag-fleet", FLEET_TOKEN) and ident.is_fleet
        assert ident.author("engineer") == ("MotoDiag fleet (engineer)",
                                            "motodiag-fleet@users.noreply.github.com")
        assert ident.env() == {"GH_TOKEN": FLEET_TOKEN}

    def test_without_the_account_only_a_trial_uses_the_operators_login(self, tmp_path):
        missing = tmp_path / "none.env"
        ident = G.identity(f"Planted. {G.TRIAL_MARKER}", missing)
        assert ident.token is None and ident.env() == {}
        assert ident.author("captain") == ("MotoDiag fleet (captain)", "fleet@motodiag.invalid")
        with pytest.raises(G.NeedsHands, match="not a planted trial"):
            G.identity("A real mission.", missing)

    @pytest.mark.parametrize("text,mode,why", [
        (f"FLEET_GITHUB_USER=motodiag-fleet\nFLEET_GITHUB_TOKEN={FLEET_TOKEN}\n", 0o644, "mode 600"),
        ("FLEET_GITHUB_USER=motodiag-fleet\nFLEET_GITHUB_TOKEN=sk-ant-oat01-x\n", 0o600, "one FLEET_GITHUB_TOKEN"),
        (f"FLEET_GITHUB_TOKEN={FLEET_TOKEN}\n", 0o600, "FLEET_GITHUB_USER"),
        (f"FLEET_GITHUB_USER=Kubanjaze\nFLEET_GITHUB_TOKEN={FLEET_TOKEN}\n", 0o600, "operator's own"),
    ])
    def test_a_wrong_file_is_refused_not_ignored(self, tmp_path, text, mode, why):
        p = self.write(tmp_path, text, mode)
        with pytest.raises(G.NeedsHands, match=why):
            G.identity(f"a trial {G.TRIAL_MARKER}", p)

    def test_the_token_never_reaches_the_command_line(self, tmp_path):
        argv = G.push_argv(tmp_path, BRANCH, G.Identity("motodiag-fleet", FLEET_TOKEN))
        assert FLEET_TOKEN not in " ".join(argv)
        assert argv[3:5] == ["-c", "credential.helper="], "the operator's gh helper is not reset"
        assert "$FLEET_PUSH_TOKEN" in argv[6] and argv[-1] == f"HEAD:refs/heads/{BRANCH}"

    def test_the_operators_push_names_no_helper(self, tmp_path):
        argv = G.push_argv(tmp_path, BRANCH, G.Identity("operator", None))
        assert "credential.helper=" not in " ".join(argv)

    def test_the_token_goes_in_the_push_processs_environment_only(self, tmp_path):
        seen = {}

        def run(cmd, **kw):
            seen.update(cmd=cmd, env=kw["env"])
            return subprocess.CompletedProcess(cmd, 0, "", "")

        G.push(tmp_path, BRANCH, G.Identity("motodiag-fleet", FLEET_TOKEN), run=run)
        assert seen["env"]["FLEET_PUSH_TOKEN"] == FLEET_TOKEN and FLEET_TOKEN not in seen["cmd"]
        assert "FLEET_PUSH_TOKEN" not in os.environ

    def test_a_real_push_with_the_helper(self, origin, tmp_path):
        """The helper line is what git runs: a push to a local bare repository
        with it set succeeds, and the bare repository gets the branch."""
        bare = tmp_path / "bare.git"
        git("init", "-q", "--bare", str(bare), cwd=tmp_path)
        clone_with(origin, tmp_path / "c", BRANCH, [{"path": "a.txt", "write": "a\n"}])
        r = G.push(tmp_path / "c", BRANCH, G.Identity("motodiag-fleet", FLEET_TOKEN), url=str(bare))
        assert r.returncode == 0, r.stderr
        assert git("rev-parse", "--verify", f"refs/heads/{BRANCH}", cwd=bare).stdout.strip()


def test_the_identity_file_is_not_in_the_repository():
    assert not str(G.IDENTITY_FILE).startswith(str(ROOT))
