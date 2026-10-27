#!/usr/bin/env python3
"""The Executive Officer: one verdict on a phase plan, the label set by script.

    xo.py review <phase> --issue N [--no-label] [--repo PATH]

1. `plan_check` runs first (the same function). A failed checklist is a
   back-to-captain verdict with the failed items, and no model is called.
2. On a pass, one read-only call (`rank_call`, Fable) with the plan, the
   step-0 report and the checklist's result, and a fixed verdict schema:
   approve; back-to-captain with items; recommend-to-admiral with a reason.
3. The script, not the model, sets the label from the parsed verdict:
   approve → plan:approved; back-to-captain → plan:needs-review;
   recommend-to-admiral → needs-admiral. A third back-to-captain on one
   plan becomes needs-admiral: two rounds at most.
4. The verdict is a comment on the mission issue, opening with a marker
   line, and ending with what the plan of record says on the phase (the
   script's `plan_order.cite_line`; Phase 392). The call's brief carries
   the record's words on the phase (`plan_order.brief_block`). The rounds
   are counted from those markers, so the state lives on GitHub beside the
   label, not in a file on one machine.

**A stage that cannot finish leaves the label where it found it** and
comments why (the fleet proposal's one new rule). Exit 0 a verdict applied,
2 the plan cannot be read, 3 a stop (a call with no usage, the wrong model,
no verdict, a label gh would not set).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fleet_git  # noqa: E402
import plan_check  # noqa: E402
import plan_order  # noqa: E402
import rank_call  # noqa: E402
from rank_call import FABLE, Runner, Stop, gh  # noqa: E402

APPROVE, BACK, ADMIRAL = "approve", "back-to-captain", "recommend-to-admiral"
LABEL = {APPROVE: "plan:approved", BACK: "plan:needs-review", ADMIRAL: "needs-admiral"}
#: The labels this rank moves; setting one removes the others.
PLAN_LABELS = ("plan:needs-review", "plan:approved", "needs-admiral")
MAX_ROUNDS = 2
MARKER = "<!-- xo-verdict:"
_MARKER = re.compile(r"^<!-- xo-verdict: (\S+) round=(\d+)", re.M)

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"enum": [APPROVE, BACK, ADMIRAL]},
        "items": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "items", "reason"],
    "additionalProperties": False,
}

BRIEF = """\
You are the Executive Officer of the MotoDiag fleet. You review one phase
plan (implementation.md v1.0) and its step-0 report before any code is
written. You are read-only: you may Read, Grep and Glob the repository to
check what the plan says against what is there. You do not edit anything.

The written checklist (plan_check.py) has already passed; its result is
below. Your job is what the checklist cannot see. Return exactly one of:
- "approve": the plan is buildable as written, its claims match the
  repository, its Step 0 supports its choices, and nothing in it needs the
  operator. "items" may be empty.
- "back-to-captain": the plan has defects its author can fix: a claim the
  repository contradicts, an item with no finish line, a step that cannot
  be done as written, a contradiction. List each as one item that says what
  to change. Do not list matters of taste.
- "recommend-to-admiral": the plan passes, but carries a risk no checklist
  item covers and that only the operator can weigh. Give the reason in at
  most three lines.

The operator alone decides CLAUDE.md rule 1's stops: a real fork, a
threshold or rule's definition, a test that cannot be made green, a login
or credential, a live-database change that alters or deletes rows. If the
plan quietly decides one of those itself, that is back-to-captain, or
recommend-to-admiral when the plan cannot be fixed without the operator.

The plan of record's words on this phase are below, with docs/decisions.md's
(Read both files too). A plan that contradicts them, or decides what a
K-id already decided differently, is back-to-captain; cite the dated entry
or the K-id in the item.
"""


def build_prompt(phase: str, plan: str, step0: str, report: plan_check.Report,
                 record: str = "") -> str:
    return (f"{BRIEF}\n=== the checklist: plan_check {phase} ===\n" + "\n".join(report.lines())
            + f"\n\n=== {phase}_implementation.md ===\n{plan}\n=== {phase}_step0.md ===\n{step0}"
            + (f"\n\n{record}" if record else ""))


def check_verdict(v: dict) -> dict:
    """The schema's own rules, re-checked: the model's JSON is never trusted."""
    if v.get("verdict") not in LABEL:
        raise Stop(f"no verdict in {sorted(v)}")
    items, reason = v.get("items"), v.get("reason")
    if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
        raise Stop("the verdict's items are not a list of strings")
    if not isinstance(reason, str):
        raise Stop("the verdict has no reason")
    if v["verdict"] == BACK and not items:
        raise Stop("back-to-captain with no items")
    if v["verdict"] == ADMIRAL and not reason.strip():
        raise Stop("recommend-to-admiral with no reason")
    return v


def prior_rounds(issue: int | None, run: Runner,
                 identity_file: pathlib.Path = fleet_git.IDENTITY_FILE) -> int:
    """How many back-to-captain verdicts this rank has already given here,
    read from the fleet's own comments only (Phase 392, F223)."""
    if issue is None:
        return 0
    r = gh(["issue", "view", str(issue), "--json", "comments,body"], run=run)
    if r.returncode != 0:
        raise Stop(f"gh could not read issue {issue}: {r.stderr.strip()[:200]}")
    data = json.loads(r.stdout)
    bodies = [c.get("body", "") for c in fleet_git.from_trusted(
        data.get("comments", []), fleet_git.trusted_authors(data.get("body", ""), identity_file))]
    return sum(1 for b in bodies for v, _ in _MARKER.findall(b) if v == BACK)


def current_labels(issue: int, run: Runner) -> list[str]:
    r = gh(["issue", "view", str(issue), "--json", "labels"], run=run)
    if r.returncode != 0:
        raise Stop(f"gh could not read issue {issue}'s labels: {r.stderr.strip()[:200]}")
    return [lab["name"] for lab in json.loads(r.stdout).get("labels", [])]


def decide(verdict: dict, rounds_before: int) -> tuple[str, str, int]:
    """(the verdict as applied, its label, this round's number)."""
    v = verdict["verdict"]
    if v != BACK:
        return v, LABEL[v], rounds_before
    n = rounds_before + 1
    if n > MAX_ROUNDS:
        return ADMIRAL, LABEL[ADMIRAL], n
    return BACK, LABEL[BACK], n


def comment_body(phase: str, applied: str, given: str, rnd: int, verdict: dict,
                 call: rank_call.Call | None, cite: str = "") -> str:
    lines = [f"{MARKER} {given} round={rnd} applied={applied} phase={phase} -->",
             f"**Executive Officer, phase {phase}: {applied}** (label `{LABEL[applied]}`)", ""]
    if applied != given:
        lines += [f"The verdict given was {given}, round {rnd}; two rounds is the most, so it "
                  "goes to the Admiral.", ""]
    if verdict.get("reason"):
        lines += [verdict["reason"], ""]
    lines += [f"- {i}" for i in verdict.get("items", [])]
    lines += ["", call.line() if call else "No model call: the written checklist failed."]
    if cite:
        lines += ["", cite]
    return "\n".join(lines)


def set_label(issue: int, label: str, run: Runner) -> None:
    have = current_labels(issue, run)
    args = ["issue", "edit", str(issue), "--add-label", label]
    for old in PLAN_LABELS:
        if old != label and old in have:
            args += ["--remove-label", old]
    r = gh(args, run=run)
    if r.returncode != 0:
        raise Stop(f"gh would not set {label}: {r.stderr.strip()[:200]}")


def review(phase: str, issue: int | None, *, repo: pathlib.Path = plan_check.ROOT,
           label: bool = True, run: Runner = subprocess.run, model: str = FABLE,
           out=print, identity_file: pathlib.Path = fleet_git.IDENTITY_FILE) -> int:
    def stop(why: str) -> int:
        out(f"STOP: {why}. The label is left where it was.")
        if label and issue is not None:
            gh(["issue", "comment", str(issue), "--body",
                f"Executive Officer, phase {phase}: stopped, label unchanged. {why}"], run=run)
        return 3

    report = plan_check.check(phase, repo)
    if report.unreadable:
        out("\n".join(report.lines()))
        stop("the plan cannot be read")
        return 2
    try:
        before = prior_rounds(issue, run, identity_file)
        call = None
        if not report.ok:
            verdict = {"verdict": BACK, "reason": "The written checklist failed.",
                       "items": [ln for ln in report.lines() if " FAIL " in ln]}
        else:
            impl, step0 = plan_check.plan_paths(phase)
            src = plan_check.Source(repo)
            call = rank_call.call("xo", build_prompt(phase, src.read(impl), src.read(step0) or "",
                                                     report, plan_order.brief_block(repo, phase)),
                                  model, SCHEMA, cwd=repo, run=run)
            verdict = check_verdict(call.structured)
        applied, lab, rnd = decide(verdict, before)
        body = comment_body(phase, applied, verdict["verdict"], rnd, verdict, call,
                            plan_order.cite_line(repo, phase))
        out(body)
        if label and issue is not None:
            r = gh(["issue", "comment", str(issue), "--body", body], run=run)
            if r.returncode != 0:
                raise Stop(f"gh would not comment: {r.stderr.strip()[:200]}")
            set_label(issue, lab, run)
            out(f"label set: {lab} on issue {issue}")
        else:
            out(f"label not set (--no-label): would be {lab}")
        return 0
    except Stop as e:
        return stop(str(e))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("review")
    r.add_argument("phase")
    r.add_argument("--issue", type=int)
    r.add_argument("--no-label", action="store_true")
    r.add_argument("--repo", type=pathlib.Path, default=plan_check.ROOT)
    a = ap.parse_args(argv)
    if not a.no_label and a.issue is None:
        ap.error("--issue is required unless --no-label")
    return review(a.phase, a.issue, repo=a.repo, label=not a.no_label)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
