"""The Captain: a phase's v1.0, and the merge recommendation.

Phase 389. Fable, fresh `claude -p` per call, with 387's read-only tools:
the model reads the repository and returns text; this script writes the one
file the Captain may change (`fleet_git.may_touch`), so it never touches
`src/`.

- `write_plan`: the v1.0 from the Step 0 report, the ROADMAP row and the
  phase's prompt (or, on a revision, also the XO's items). `plan_check`
  runs on what came back; a failure gets one more call with the failed
  items, and a second failure is a stop: nothing is written.
- `recommend`: after the Red Team's clear, three lines for the operator,
  merge or hold.

**The plan of record** (Phase 392, K44): both briefs carry what the record
says on the phase (`plan_order.brief_block`). The v1.0 must cite the dated
entry or K-id that puts the phase in order (P9) and, for a fleet-only
phase, name the first-shop phase it unblocks (P10); the recommendation's
comment ends with the script's cite line.

Measured at Step 0 (S0-3), the brief below as drafted: one call, 30 turns,
312 s, 237K tokens read, 20K written; its plan for 388 passed P1–P8.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_check  # noqa: E402
import plan_order  # noqa: E402
import rank_call  # noqa: E402
from rank_call import FABLE, Runner, Stop  # noqa: E402

PLAN_SCHEMA = {
    "type": "object",
    "properties": {"implementation_md": {"type": "string"}},
    "required": ["implementation_md"], "additionalProperties": False,
}
RECOMMEND_SCHEMA = {
    "type": "object",
    "properties": {"decision": {"enum": ["merge", "hold"]},
                   "lines": {"type": "array", "items": {"type": "string"},
                             "minItems": 3, "maxItems": 3}},
    "required": ["decision", "lines"], "additionalProperties": False,
}

BRIEF = """\
You are the Captain of the MotoDiag fleet. You write one phase plan:
docs/phases/in_progress/{N}_implementation.md, version 1.0, from the phase's
Step 0 report, its ROADMAP row and the prompt that opened it (all below).
You are read-only: you may Read, Grep and Glob the repository to check
what you write against what is there. You do not edit any file; you return
the whole document as `implementation_md`, and a script writes it.

The plan is the contract the Chief Engineer builds to, and the Executive
Officer checks it before any code is written. Follow the repository's own
form: read the newest docs/phases/completed/*_implementation.md for its
shape (do not copy its content). The document must have, as ## sections:
- Goal; Logic (what ships, file by file, each with its finish line);
- "The change log's three newest entries": each of the three newest
  entries under "## Change log" in CLAUDE.md, by its date, with the check
  it became as a backticked path that exists, or "no check" when the
  entry itself says it is text only;
- "The plan of record": the dated entry under "Changes to the order" (by
  its date) or the K-id from docs/decisions.md that puts this phase in
  order, quoted from the record below, never from memory. If the phase is
  fleet-only (its "Next, in order" kind is fleet, or it changes only the
  fleet's own folder), a line beginning "Unblocks:" naming the first-shop
  phase it unblocks, by number (K43). If nothing in the record puts the
  phase in order, say so: that is a stop, not something to invent;
- "Rule-1 stops anticipated": bullets, each one of CLAUDE.md rule 1's five
  kinds (a real fork, a threshold or rule's definition, a test that
  cannot be made green, a login or credential, a live-database change that
  alters or deletes rows), or "None expected";
- Tests; Non-goals; Planned items (unticked checkboxes).
No section may be empty, and no line may start with TBD, TODO, "to be
written", "placeholder" or an ellipsis. Name no path under data/, no seed
data, no split and no eval protocol outside Non-goals.

Decide nothing that CLAUDE.md rule 1 reserves for the operator: if the
Step 0 report leaves such a choice open, list it as a stop. Never plan a
change under src/ that the Step 0 report does not support. Write plainly.
"""

RECOMMEND_BRIEF = """\
You are the Captain of the MotoDiag fleet. A phase's pull request has been
built by the Chief Engineer, checked by a run no model touched, and cleared
by the Red Team. The operator merges by hand. Write the recommendation the
operator reads first: exactly three lines, plain English, no internal
labels.
1. What the phase ships, in one sentence.
2. What was checked and what it showed (the regression line's counts, the
   Red Team's clear).
3. Merge or hold, and the one reason.
Return "decision": "merge" only if nothing below gives a reason to hold.
Read the plan of record's words on this phase below: a phase the record
does not put in order, or a pull request that ships something the record
reserves for the operator, is a reason to hold.
"""


def plan_prompt(phase: str, row: str, prompt_text: str, step0: str,
                items: list[str] | None = None, plan_now: str | None = None,
                record: str = "") -> str:
    text = (BRIEF.replace("{N}", phase) + f"\n=== the ROADMAP row ===\n{row}\n\n"
            f"=== the phase's prompt ===\n{prompt_text or '(none committed)'}\n\n"
            f"=== docs/phases/in_progress/{phase}_step0.md ===\n{step0}\n\n{record}")
    if items:
        text += ("\n\n=== the plan as it stands ===\n" + (plan_now or "")
                 + "\n\n=== what must change (the Executive Officer's items, or the checklist's"
                 " failures) ===\n" + "\n".join(f"- {i}" for i in items))
    return text


def write_plan(phase: str, row: str, prompt_text: str, step0: str, *, clone: pathlib.Path,
               run: Runner, items: list[str] | None = None, model: str = FABLE
               ) -> list[rank_call.Call]:
    """Write a v1.0 that passes plan_check into the clone, or raise Stop."""
    impl, _ = plan_check.plan_paths(phase)
    path = clone / impl
    plan_now = path.read_text(encoding="utf-8") if path.exists() else None
    calls: list[rank_call.Call] = []
    for attempt in range(2):
        c = rank_call.call("captain", plan_prompt(phase, row, prompt_text, step0, items, plan_now,
                                                  plan_order.brief_block(clone, phase)),
                           model, PLAN_SCHEMA, cwd=clone, run=run, timeout=3600)
        calls.append(c)
        text = c.structured.get("implementation_md")
        if not isinstance(text, str) or not text.strip():
            raise Stop("the plan came back empty")
        previous = path.read_text(encoding="utf-8") if path.exists() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")
        report = plan_check.check(phase, clone)
        if report.ok:
            return calls
        failed = [ln for ln in report.lines() if " FAIL " in ln or ln.startswith("CANNOT")]
        if previous is None:
            path.unlink()
        else:
            path.write_text(previous, encoding="utf-8")
        items, plan_now = failed, text
    raise Stop("the plan still fails the checklist after one more call: " + "; ".join(failed)[:400])


def recommend(phase: str, summary: str, *, clone: pathlib.Path, run: Runner, model: str = FABLE
              ) -> tuple[dict, rank_call.Call]:
    c = rank_call.call("captain", f"{RECOMMEND_BRIEF}\n=== phase {phase} ===\n{summary}\n\n"
                                  f"{plan_order.brief_block(clone, phase)}", model,
                       RECOMMEND_SCHEMA, cwd=clone, run=run)
    v = c.structured
    lines = v.get("lines")
    if v.get("decision") not in ("merge", "hold"):
        raise Stop("the recommendation has no decision")
    if not (isinstance(lines, list) and len(lines) == 3
            and all(isinstance(x, str) and x.strip() and "\n" not in x for x in lines)):
        raise Stop("the recommendation is not three single lines")
    return v, c
