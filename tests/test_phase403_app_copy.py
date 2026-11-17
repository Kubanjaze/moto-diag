"""Phase 403 (c) — the phone app's copy, refreshed with no model (F276, K84).

What must hold (the 403 prompt, (c)): a result `app-copy`; on it the
dispatcher, with no model, regenerates `api-schema/openapi.json` from the
clone's HEAD the way that reproduces moto-diag-mobile `993fadc` from
`cbfa766` and `d292eef` from `76bdea5` byte for byte; refuses if any other
file would change; commits it on the app's branch of the phase branch's
name, never `main`; pushes it with the fleet's account; puts the fleet's own
copy of the app on that branch for the fence; runs Gate 11 with no model
against it; and resumes the Engineer from its held run. Known-bad: refused
on `main`, when a second file would change, when another check is also red.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
sys.path.insert(0, str(ROOT / "tests"))

import app_copy  # noqa: E402
import dispatcher as D  # noqa: E402
import engineer as E  # noqa: E402
import journal as J  # noqa: E402
from test_phase389_dispatcher import BRANCH, LINE, PHASE, FakeEngineer  # noqa: E402
from test_phase389_fleet_git import git  # noqa: E402
from test_phase390_resume import N, advance, labels, ledger, to_approved, w  # noqa: E402

assert w and ledger  # the fixtures, imported for their names

#: 403_step0.md, S0-3: the generated file's sha-256, equal to the app's.
PAIRS = [("cbfa766", "993fadc", "0aa24a3f922b67c64744dd86fef55365540dc9421b0f52572686eda0b01ee873"),
         ("76bdea5", "d292eef", "d43910b075ae21875aadd69eb5efca5bea0dc406792c7264c4570024080283a6")]
OLD = '{\n  "openapi": "3.1.0",\n  "paths": {}\n}\n'
NEW = '{\n  "openapi": "3.1.0",\n  "paths": {\n    "/v1/new": {}\n  }\n}\n'


@pytest.mark.parametrize("backend, app, sha", PAIRS, ids=[f"{b}->{a}" for b, a, _ in PAIRS])
def test_the_generator_reproduces_the_apps_copy_byte_for_byte(tmp_path, backend, app, sha):
    """Red on the old code: there is no generator."""
    src = tmp_path / "x"
    src.mkdir()
    tar = subprocess.run(["git", "-C", str(ROOT), "archive", backend, "src"], capture_output=True,
                         check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(src)], input=tar, check=True)
    out = tmp_path / "openapi.json"
    subprocess.run([sys.executable, "-I", "-c", app_copy.GENERATOR, str(out), str(src / "src")],
                   cwd=src, check=True, capture_output=True,
                   env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(tmp_path)})
    assert hashlib.sha256(out.read_bytes()).hexdigest() == sha, f"not moto-diag-mobile {app}"


# ----------------------------------------------------- a stand-in phone app
def mobile_repo(tmp: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """(the app on "GitHub", a bare repository; the fleet's own copy)."""
    seed = tmp / "app-seed"
    (seed / "api-schema").mkdir(parents=True)
    (seed / app_copy.SCHEMA).write_text(OLD)
    (seed / "src").mkdir()
    (seed / "src" / "App.tsx").write_text("export {}\n")
    git("init", "-q", "-b", "main", cwd=seed)
    git("add", "-A", cwd=seed)
    git("-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "the app", cwd=seed)
    bare = tmp / "app.git"
    git("clone", "-q", "--bare", str(seed), str(bare), cwd=tmp)
    copy = tmp / "state-mobile"
    git("clone", "-q", str(bare), str(copy), cwd=tmp)
    return bare, copy


class AppCopyEngineer(FakeEngineer):
    """First session: a commit, then `app-copy`. Later: `pr-ready`."""

    def __call__(self, cmd, stdout, stderr, **kw):
        if self.runs == 0:
            self.result = {"outcome": E.APP_COPY,
                           "summary": "The payments list now names its fixed values."}
        else:
            self.result = {"outcome": "pr-ready", "summary": "Done.", "regression_line": LINE}
        return super().__call__(cmd, stdout, stderr, **kw)


@pytest.fixture
def app(w, tmp_path):
    bare, copy = mobile_repo(tmp_path)
    ident = tmp_path / "fleet-github.env"
    ident.write_text("FLEET_GITHUB_USER=motodiag-fleet-bot\nFLEET_GITHUB_TOKEN=ghp_"
                     + "a" * 36 + "\n")
    ident.chmod(0o600)
    w.engineer = AppCopyEngineer()
    w.make()
    w.fleet.identity_file, w.fleet.mobile, w.fleet.mobile_url = ident, copy, str(bare)
    w.gate11 = [False, True]          # red before the copy, green after
    w.fast_ok = True
    base = w.fleet.check

    def check(clone, commit, *, full, command=None):
        cmd = command or []
        if cmd and cmd[-1] == app_copy.GATE11:
            w.checks.append((commit, full, command))
            # The fence mounts the fleet's copy: Gate 11 reads it.
            ok = (copy / app_copy.SCHEMA).read_text() == NEW if w.gate11 is None else \
                w.gate11.pop(0)
            return D.Check(ok, commit, why="21 passed" if ok else "1 failed: the snapshot")
        if cmd[:3] == [".venv/bin/python", "-I", "-c"]:
            run = w.fleet.new_run("check")
            (run / "run" / app_copy.OUT_NAME).write_text(NEW)
            w.checks.append((commit, full, command))
            return D.Check(True, commit, out="", run=str(run))
        if not full and command is None and not w.fast_ok:
            return D.Check(False, commit, why="1 failed in tests/test_phase372_routes.py")
        return base(clone, commit, full=full, command=command)
    w.fleet.check = check
    w.bare, w.copy = bare, copy
    return w


def app_log(w, ref: str) -> list[str]:
    return git("log", "--format=%s", ref, cwd=w.bare).stdout.splitlines()


def test_app_copy_refreshes_one_file_on_the_phase_branch_and_resumes(app):
    """Red on the old code: `app-copy` is no outcome it reads."""
    w = app
    to_approved(w)
    advance(w)
    assert len(app_log(w, "main")) == 1, "main was written"
    names = git("diff", "--name-only", f"main..{BRANCH}", cwd=w.bare).stdout.split()
    assert names == [app_copy.SCHEMA]
    assert git("show", f"{BRANCH}:{app_copy.SCHEMA}", cwd=w.bare).stdout == NEW
    said = w.host.comments(N)[-1]
    assert said.startswith(D.APP_M) and f"`{BRANCH}`" in said
    (held,) = J.held_runs(w.fleet.runs, N)
    info = J.held(held)
    assert info["why"] == E.APP_COPY and info["app"]["BRANCH"] == BRANCH
    assert w.engineer.runs == 1 and "needs-admiral" not in labels(w)
    advance(w)                                     # the next cycle: the Engineer goes on
    assert w.engineer.runs == 2
    assert "The phone app's copy of the API's description is refreshed" in w.session_briefs[-1]
    assert labels(w) == ["mission", "review:open"] and BRANCH in w.host.prs
    assert J.held(held) is None


def test_the_fleet_copy_is_mounted_on_the_phase_branch(app):
    w = app
    to_approved(w)
    advance(w)
    head = git("rev-parse", "HEAD", cwd=w.copy).stdout.strip()
    assert head == git("rev-parse", BRANCH, cwd=w.bare).stdout.strip()
    w.fleet.sync_mobile("phase-999-none")
    assert git("rev-parse", "HEAD", cwd=w.copy).stdout == git("rev-parse", "main",
                                                              cwd=w.bare).stdout


def test_another_red_check_refuses_and_stops(app):
    """Known-bad: the whole-tree run is red too, so it is not only the copy."""
    w = app
    to_approved(w)
    w.fast_ok = False
    advance(w)
    assert len(app_log(w, "--all")) == 1, "the app was written"
    assert "needs-admiral" in labels(w)
    note = w.host.comments(N)[-1]
    assert note.startswith(f"{D.MARKER} needs-admiral rank=engineer stop={E.APP_COPY}")
    assert "another check is also red" in note
    (held,) = J.held_runs(w.fleet.runs, N)
    assert J.held(held)["why"] == D.STOPPED, "the work was not kept"


def test_gate11_still_red_against_the_new_copy_stops(app):
    """Known-bad: the refreshed copy does not turn Gate 11 green: the build
    does not go on as if it had."""
    w = app
    w.gate11 = [False, False]
    to_approved(w)
    advance(w)
    note = w.host.comments(N)[-1]
    assert "still fails against" in note and "needs-admiral" in labels(w)
    assert w.engineer.runs == 1


def test_gate11_already_green_refuses(app):
    w = app
    w.gate11 = [True]
    to_approved(w)
    advance(w)
    assert "already passes" in w.host.comments(N)[-1] and len(app_log(w, "--all")) == 1


def test_without_the_fleets_account_it_refuses(app):
    w = app
    w.fleet.identity_file = w.tmp / "no-identity.env"
    to_approved(w)
    advance(w)
    assert "only with the fleet's own GitHub account" in w.host.comments(N)[-1]
    assert len(app_log(w, "--all")) == 1


@pytest.mark.parametrize("branch", ["main", "master", f"phase-{PHASE}-stopped-x", "phase-1-x"])
def test_the_step_refuses_any_branch_but_the_phases(tmp_path, branch):
    _, copy = mobile_repo(tmp_path)
    with pytest.raises(D.Stop, match="goes only on the app's branch"):
        app_copy.commit_copy(copy, branch, PHASE, NEW.encode(), "c" * 40, ("t", "t@l"))
    assert git("rev-parse", "--abbrev-ref", "HEAD", cwd=copy).stdout.strip() == "main"


def test_a_second_file_changing_is_refused(tmp_path, monkeypatch):
    """Known-bad: the copy's checkout leaves another file changed (here a
    planted change git cannot discard: a file the step does not own,
    written after the checkout)."""
    _, copy = mobile_repo(tmp_path)
    real = app_copy._git

    def plant(repo, *args):
        r = real(repo, *args)
        if args[:1] == ("status",):
            (repo / "src" / "App.tsx").write_text("export const x = 1\n")
            r = real(repo, *args)
        return r
    monkeypatch.setattr(app_copy, "_git", plant)
    with pytest.raises(D.Stop, match="more than the one file would change"):
        app_copy.commit_copy(copy, BRANCH, PHASE, NEW.encode(), "c" * 40, ("t", "t@l"))


def test_the_same_description_is_nothing_to_commit(tmp_path):
    _, copy = mobile_repo(tmp_path)
    with pytest.raises(D.Stop, match="nothing to commit"):
        app_copy.commit_copy(copy, BRANCH, PHASE, OLD.encode(), "c" * 40, ("t", "t@l"))


def test_the_brief_offers_app_copy_and_asks_nothing_of_the_desktop():
    brief = " ".join(E.session_brief(PHASE, N).split())
    assert '"outcome": "app-copy"' in brief
    assert ("Never ask the operator, in a stop, a log or a handoff, to refresh the app's copy"
            in brief)


def test_an_app_copy_result_needs_its_summary(tmp_path):
    (tmp_path / E.RESULT).write_text(json.dumps({"outcome": E.APP_COPY}))
    with pytest.raises(D.Stop, match="does not say what changed"):
        E.read_result(tmp_path)
    (tmp_path / E.RESULT).write_text(json.dumps({"outcome": E.APP_COPY, "summary": "x"}))
    assert E.read_result(tmp_path)["outcome"] == E.APP_COPY


def test_the_fence_mounts_the_fleets_copy_never_the_operators(monkeypatch):
    """The default copy is the fleet's, under its state folder; the
    operator's ~/Projects/moto-diag-mobile is never it."""
    import importlib

    import fleet_git
    monkeypatch.delenv("FLEET_MOBILE", raising=False)
    monkeypatch.delenv("FLEET_STATE", raising=False)
    fresh = importlib.reload(fleet_git)
    try:
        assert fresh.MOBILE == (pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet"
                                / "moto-diag-mobile")
    finally:
        monkeypatch.undo()
        importlib.reload(fleet_git)
