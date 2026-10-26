"""Phase 391 Step 0: one Quartermaster call on a real PR, to measure its cost.

Not shipped code. PR #20 (phase 390A, fleet-built; the operator closed it
unmerged). verify_phase.sh runs model-free in the fence (no net, no token);
then one fenced Opus call, read-only tools, with the drafted brief.
    python3 qm_dry_run.py verify     # the model-free part
    python3 qm_dry_run.py call       # the model call
"""
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path("/home/lilcu/Projects/moto-diag")
FLEET = REPO / ".claude/skills/fleet"
sys.path.insert(0, str(FLEET))
import dispatcher as D  # noqa: E402
import red_team  # noqa: E402
import rank_call  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent / "qm_dry"
CLONE, RUN = HERE / "clone", HERE / "run"
TIP, REG, PHASE = "f987bf3130874e806153d0784ecce246b971cbcb", "44f846d", "390A"


def git(*a, cwd=None):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=cwd)


def setup():
    if not CLONE.is_dir():
        RUN.mkdir(parents=True, exist_ok=True)
        git("clone", "-q", "--no-hardlinks", str(REPO), str(CLONE))
        git("-C", str(CLONE), "checkout", "-q", "--detach", TIP)
    return D.Fleet(state=HERE / "state", token="", out=print,
                   venv=pathlib.Path.home() / ".local/state/motodiag/fleet/venv")


def verify():
    fleet = setup()
    runner = D.FencedRunner(fleet, CLONE, RUN)
    argv = runner.fence_argv(["/bin/bash", "-c",
                              f".claude/skills/closeout/verify_phase.sh {PHASE} {REG} {TIP}"],
                             net="none", token=False)
    r = subprocess.run(argv, capture_output=True, text=True, cwd=CLONE,
                       env={"PATH": "/usr/bin:/bin"}, stdin=subprocess.DEVNULL, timeout=3600)
    (HERE / "verify.txt").write_text(r.stdout + r.stderr)
    print("exit", r.returncode)
    print(r.stdout[-3000:])


BRIEF = open(pathlib.Path(__file__).with_name("qm_brief.txt")).read()
SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"enum": ["merge", "refuse"]},
        "failed": {"type": "array", "items": {
            "type": "object", "properties": {"check": {"type": "string"},
                                             "why": {"type": "string"}},
            "required": ["check", "why"], "additionalProperties": False}},
        "summary": {"type": "string"},
    },
    "required": ["verdict", "failed", "summary"], "additionalProperties": False,
}


def gh(*a):
    return subprocess.run(["gh", *a, "-R", "Kubanjaze/moto-diag"], capture_output=True,
                          text=True).stdout


def call():
    fleet = setup()
    fleet.token = D.load_token()
    pc = red_team.plan_commit(CLONE, PHASE)
    plan_diff = git("-C", str(CLONE), "diff", pc, "HEAD", "-M", "--",
                    f"docs/phases/in_progress/{PHASE}_implementation.md",
                    f"docs/phases/completed/{PHASE}_implementation.md").stdout
    pr = json.loads(gh("pr", "view", "20", "--json", "body,comments"))
    captain = [c["body"] for c in pr["comments"] if "fleet-captain-pr" in c["body"]]
    red = [c["body"] for c in pr["comments"] if "fleet-red-team-pr" in c["body"]]
    context = (f"=== the checks run by script (the dry run's stand-in table) ===\n"
               f"(the full run and the scripted checks are not part of this dry run)\n\n"
               f"=== verify_phase.sh {PHASE} {REG} {TIP[:12]}, run with no model ===\n"
               f"{(HERE / 'verify.txt').read_text()}\n\n"
               f"=== the Captain's recommendation ===\n{captain[-1] if captain else '(none)'}\n\n"
               f"=== the Red Team's last word ===\n{red[-1] if red else '(none)'}\n\n"
               f"=== the pull request's body ===\n{pr['body']}\n\n"
               f"=== the diff of v1.0 ({pc[:12]}) to v1.1 ===\n{plan_diff}")
    (HERE / "context.txt").write_text(context)
    runner = D.FencedRunner(fleet, CLONE, RUN)
    c = rank_call.call("quartermaster", BRIEF.replace("{N}", PHASE) + "\n" + context,
                       rank_call.OPUS, SCHEMA, cwd=CLONE, run=runner, timeout=3600,
                       ledger=HERE / "calls.jsonl")
    (HERE / "verdict.json").write_text(json.dumps(c.structured, indent=2))
    print(c.line())
    print(json.dumps(c.structured, indent=2))
    print("context chars", len(context))


if __name__ == "__main__":
    {"verify": verify, "call": call}[sys.argv[1]]()
