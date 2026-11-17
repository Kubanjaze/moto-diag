#!/usr/bin/env python3
"""Phase 403's trial, once, in the real place, before 404 starts (the
prompt's after-merge step 3).

Run on the home desktop from the fleet's copy of the code, after the merge,
after the fleet's account has write access to moto-diag-mobile (step 1) and
the fleet's copy is on master (step 2), with no fleet job running:

    ~/.local/state/motodiag/fleet/venv/bin/python docs/phases/completed/403_trial.py

What is real: GitHub (both repositories, the fleet's account, the
operator's own `gh` sign-in for the answer), the dispatcher's own methods
(`stop_engineer`, `keep_stop`, `push_side`, `engineer_stop`,
`operator_comments`, `engineer_clone`, `carry_answer`), the push gate's
side mode, the fence (the generator and Gate 11 run in it with no network
and no model), and `app_copy.commit_copy`.

What stands in: the Engineer (a planted commit and a planted stop: no model
is called), and the description pushed to the app's throwaway branch (the
generator's own output with one key added, `x-fleet-trial`, because
master's description already equals the app's `main` and an equal copy is
refused as nothing to commit).

Everything it makes is the trial's own and is removed at the end: the
issue `Phase 403: the fleet's stops, trial <stamp>` (carrying
`<!-- fleet-trial -->`; closed), the branch `phase-403-trial-<stamp>` in
both repositories and the side branch `phase-403-stopped-<run>` (deleted),
and its state folder `~/motodiag/p403/trial-<stamp>` (kept, for the
record). Row 403 is ✅ on master by then, so the running fleet works none
of it. The last line is ALL GOOD or SOMETHING IS OFF.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / ".claude" / "skills" / "fleet"))
import app_copy  # noqa: E402
import dispatcher as D  # noqa: E402
import fleet_git  # noqa: E402
import journal  # noqa: E402

PHASE = "403"
STAMP = dt.datetime.now().strftime("%Y%m%d%H%M")
BRANCH = f"phase-{PHASE}-trial-{STAMP}"
STATE = pathlib.Path.home() / "motodiag" / "p403" / f"trial-{STAMP}"
FLEET_VENV = pathlib.Path.home() / ".local" / "state" / "motodiag" / "fleet" / "venv"
ANSWER = (f"Trial answer ({STAMP}): go on from the kept commit. This line is the "
          "operator's own, posted by the trial from this computer's gh sign-in.")
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, said: str = "") -> bool:
    results.append((name, ok, said))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f": {said}" if said else ""), flush=True)
    return ok


def operator_gh(*args: str) -> str:
    """`gh` as the operator: this computer's own sign-in, no fleet token."""
    env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN")}
    r = subprocess.run(["gh", *args, "-R", D.REPO], capture_output=True, text=True, env=env,
                       stdin=subprocess.DEVNULL, timeout=120)
    if r.returncode != 0:
        raise SystemExit(f"SOMETHING IS OFF: gh {' '.join(args[:2])} failed: {r.stderr.strip()}")
    return r.stdout


def git(*args: str, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def main() -> int:
    STATE.mkdir(parents=True, exist_ok=False)
    fleet = D.Fleet(state=STATE, token="", venv=FLEET_VENV, mobile=STATE / "moto-diag-mobile",
                    mobile_url=fleet_git.MOBILE_URL)
    ident = fleet.fleet_identity()
    if not check("the fleet's own GitHub account is set up", bool(ident and ident.is_fleet)):
        return finish(fleet, None, None, None)
    fleet.update_mirror()
    fleet.ensure_mobile()
    url = operator_gh("issue", "create", "--title", f"Phase {PHASE}: the fleet's stops, trial "
                      f"{STAMP}", "--body", f"Phase 403's trial ({STAMP}): a planted stop, an "
                      f"answer, the app's copy. Nothing from it merges.\n\n{fleet_git.TRIAL_MARKER}")
    n = int(url.strip().rsplit("/", 1)[1])
    print(f"the trial's issue: #{n}")

    # 1. the throwaway phase branch, at master
    setup = STATE / "setup"
    git("clone", "-q", "--branch", "master", str(fleet.mirror), str(setup))
    r = fleet_git.push(setup, BRANCH, ident, url=fleet.push_url)
    fleet.update_mirror()
    master = fleet.ref("master")
    if not check(f"the throwaway branch {BRANCH} is on GitHub", r.returncode == 0
                 and fleet.ref(BRANCH) == master, r.stderr.strip()[:200]):
        return finish(fleet, n, None, None)

    # 2. a planted stop after a commit: kept, on its side branch
    run = fleet.new_run(f"engineer_{PHASE}", {"stage": "engineer", "issue": n, "phase": PHASE,
                                              "body": "", "branch": BRANCH, "rnd": 0})
    fleet.journal = journal.Journal.load(run)
    clone = fleet.stage_clone(run, BRANCH)
    fleet.author(clone, "engineer", ident)
    (clone / "docs" / f"{PHASE}_trial_{STAMP}.md").write_text(
        f"# Phase 403's trial, {STAMP}\n\nA planted commit before a planted stop.\n")
    git("add", "-A", cwd=clone)
    git("commit", "-qm", f"Phase {PHASE} trial: a planted commit before a planted stop", cwd=clone)
    head = git("rev-parse", "HEAD", cwd=clone).stdout.strip()
    out = fleet.stop_engineer(n, PHASE, BRANCH, run, ident, 0, "test-cannot-be-green",
                              f"Chief Engineer, phase {PHASE} (trial): stopped "
                              "(test-cannot-be-green). A planted stop after a commit.")
    fleet.finish(out)
    side = fleet_git.side_branch(PHASE, run.name)
    fleet.update_mirror()
    check("the stopped run is held", (journal.held(run) or {}).get("why") == D.STOPPED)
    check(f"its commit is on the side branch {side}", fleet.ref(side) == head)
    check("the phase branch did not move", fleet.ref(BRANCH) == master)
    note = json.loads(operator_gh("issue", "view", str(n), "--json", "comments"))["comments"][-1]
    check("the stop note names the commit and the side branch",
          f"`{head[:12]}`" in note["body"] and f"`{side}`" in note["body"])

    # 3. the operator's answer, quoted into the log; the next round from the kept run
    fleet.say(n, "<!-- fleet-trial: not an answer -->", "The fleet's own comment, not an answer.")
    operator_gh("issue", "comment", str(n), "--body", ANSWER)
    operator_gh("issue", "edit", str(n), "--remove-label", "needs-admiral")
    stopped = fleet.engineer_stop(n)
    check("the stop is read from its marker", bool(stopped) and stopped[1] == "test-cannot-be-green")
    said = fleet.operator_comments(n, stopped[0]) if stopped else []
    check("only the operator's own comment is the answer",
          [c["body"] for c in said] == [ANSWER], f"{len(said)} comment(s)")
    run2 = fleet.new_run(f"engineer_{PHASE}", {"stage": "engineer", "issue": n, "phase": PHASE,
                                               "body": "", "branch": BRANCH, "rnd": 0})
    fleet.journal = journal.Journal.load(run2)
    clone2 = fleet.engineer_clone(run2, n, BRANCH)
    check("the next round's clone has the kept commit",
          git("merge-base", "--is-ancestor", head, "HEAD", cwd=clone2).returncode == 0)
    check("the hold is let go", journal.held(run) is None)
    fleet.author(clone2, "engineer", ident)
    brief = fleet.carry_answer(n, PHASE, clone2, {"at": stopped[0].isoformat(),
                                                  "kind": stopped[1]}) if stopped else {}
    log = (clone2 / brief.get("LOG", "missing")).read_text(encoding="utf-8") \
        if brief else ""
    check("the answer is quoted verbatim in a dated phase-log entry",
          f"> {ANSWER}" in log and brief.get("HEADING", "?") in log)
    fleet.finish("the trial's second round")
    head2 = git("rev-parse", "HEAD", cwd=clone2).stdout.strip()

    # 4. the app's copy, on a throwaway branch in the app's repository
    gen = fleet.check(clone2, head2, full=False, command=app_copy.generate_cmd())
    made = pathlib.Path(gen.run) / "run" / app_copy.OUT_NAME if gen.run else None
    if not check("the generator ran in the fence, no model, no network",
                 gen.ok and made is not None and made.is_file(), gen.why[-200:]):
        return finish(fleet, n, side, ident)
    data = json.loads(made.read_text(encoding="utf-8"))
    data["x-fleet-trial"] = STAMP
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    try:
        app_copy.commit_copy(fleet.mobile, "main", PHASE, text.encode(), head2, ("t", "t@t"))
        check("the step refuses main", False)
    except D.Stop as e:
        check("the step refuses main", "never on 'main'" in str(e))
    try:
        sha = app_copy.commit_copy(fleet.mobile, BRANCH, PHASE, text.encode(), head2,
                                   ident.author("app-copy"))
    except D.Stop as e:
        check("the copy is committed on the app's throwaway branch", False, str(e))
        return finish(fleet, n, side, ident)
    r = fleet_git.push(fleet.mobile, BRANCH, ident, url=fleet_git.MOBILE_URL)
    if not check("the fleet's account pushed it to moto-diag-mobile", r.returncode == 0,
                 r.stderr.strip()[:300]):
        return finish(fleet, n, side, ident)
    git("fetch", "-q", "origin", cwd=fleet.mobile)
    names = git("diff", "--name-only", f"origin/main..origin/{BRANCH}",
                cwd=fleet.mobile).stdout.split()
    check("only api-schema/openapi.json differs from the app's main", names == [app_copy.SCHEMA],
          f"{names[:5]}")
    check("the app's main did not move", git("rev-parse", "origin/main", cwd=fleet.mobile)
          .stdout.strip() != sha)
    gate = fleet.check(clone2, head2, full=False, command=app_copy.GATE11_CMD)
    check("Gate 11 passes against the fleet's copy on that branch", gate.ok, gate.why[-200:])
    return finish(fleet, n, side, ident)


def finish(fleet: D.Fleet, n: int | None, side: str | None, ident) -> int:
    """The trial's own things removed, then the verdict."""
    if ident is not None:
        for repo, url in ((STATE / "setup", fleet.push_url),
                          (fleet.mobile, fleet_git.MOBILE_URL)):
            for b in ([BRANCH, side] if repo.name == "setup" else [BRANCH]):
                if b and (repo / ".git").exists():
                    env = {**os.environ, "FLEET_PUSH_TOKEN": ident.token}
                    git_argv = fleet_git.push_argv(repo, b, ident, url)
                    argv = [*git_argv[:-1], f":refs/heads/{b}"]
                    subprocess.run(argv, capture_output=True, text=True, env=env, timeout=300)
    for p in journal.held_runs(fleet.runs, n or -1):
        journal.release(p)
    if n is not None:
        operator_gh("issue", "close", str(n), "--comment", "Phase 403's trial is over: its "
                    "branches are deleted.")
    bad = [name for name, ok, _ in results if not ok]
    print()
    print(f"{len(results) - len(bad)} of {len(results)} checks passed. The trial's folder: {STATE}")
    print("ALL GOOD" if results and not bad else "SOMETHING IS OFF: " + "; ".join(bad))
    return 0 if results and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
