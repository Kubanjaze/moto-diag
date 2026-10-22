---
name: fleet
description: The fleet's read-only ranks — the Executive Officer's plan checklist and verdict (plan_check.py, xo.py), the Yeoman's decisions file and daily digest (yeoman.py), and the GitHub labels that carry a phase's state (labels.py). Use when reviewing a phase's v1.0 before the build, recording an operator decision as a K-id, writing the day's digest, or checking the fleet's labels.
---

# fleet — the ranks that read and never write code

## Why this folder exists

The operator was the message bus between sessions: approving plans that
already passed the written rules, answering questions already answered in
the plan of record, carrying state between windows by hand
(`docs/reports/2026-10-22_fleet_proposal.md`, "What the record shows").
This folder holds the first two ranks that take that work, both read-only:
the **Executive Officer** (approves a plan by checklist) and the
**Yeoman** (keeps the decisions file, writes the digest). Neither pushes
code or merges.

**A GitHub label on the mission issue is the state word.** The script sets
it from a parsed result; a model never does.

## The plan checklist — `plan_check.py`

```
python3 .claude/skills/fleet/plan_check.py <phase> [--rev COMMIT] [--no-pin]
python3 .claude/skills/fleet/plan_check.py --self-test
```

Pure checks, no model. Exit 0 pass, 1 fail (each failed item named), 2
cannot read the ROADMAP, `CLAUDE.md` or the plan.

| id | the item |
|---|---|
| P1 | a ROADMAP row, 🚧 (`roadmap_check.rows`, reused) |
| P2 | `<N>_step0.md` exists |
| P3 | every count in the step-0 report shows the query that produced it |
| P4 | `Classification:` greenfield or extension; reshape or none fails |
| P5 | no path under `data/`, the knowledge content path (`wholetree.CONTENT_PATHS`, reused), seed data, a split or an eval protocol named outside the Non-goals |
| P6 | every section filled, no stub line; Goal and Logic present |
| P7 | the three newest `CLAUDE.md` change-log entries cited, each with a backticked path that exists, or "no check" for an entry that says it is text only |
| P8 | a section listing the rule-1 stops, each one of the five kinds, or "none" |

**P3, the count rule, is strict on purpose.** A count is a number
followed within two words (no preposition, article or verb between) by a
counted noun. It is shown when its paragraph or bullet, or for a table
row its row or the block just before the table, holds a backticked
command or script. Over the 34 step-0 reports written before it, 32 have
at least one count without its query (197 blocks, measured in Phase 387).
Most are real (a live count with only its source named); some are not
(a number in prose arithmetic). A false hit costs a round back to the
Captain, never a wrong approval. Counts written as words ("three nodes")
are not read.

**The pin.** `WRITTEN_BEFORE`: 384 and 386's v1.0 predate P4, P7 and P8
(the operator, 2026-10-22, K41: "Pin them (Recommended)"). Equality-tested.

## The Executive Officer — `xo.py`

```
python3 .claude/skills/fleet/xo.py review <phase> --issue N
python3 .claude/skills/fleet/xo.py review <phase> --no-label
```

1. `plan_check`; a failure is back-to-captain with no model call.
2. One read-only call on Fable (`claude-fable-5-1`) with `--json-schema`:
   approve; back-to-captain with items; recommend-to-admiral with a reason.
3. The label from the parsed verdict: `plan:approved`, `plan:needs-review`,
   `needs-admiral`. The third back-to-captain becomes `needs-admiral`;
   rounds are counted from the rank's own marker comments on the issue.
4. **A stop leaves the label where it was** and comments why: exit 3 for
   a call with no usage, the wrong model served, no or a malformed
   verdict, a label `gh` refuses.

## The Yeoman — `yeoman.py`

```
python3 .claude/skills/fleet/yeoman.py decide --words "…" --check "…" [--kid K42]
python3 .claude/skills/fleet/yeoman.py digest [--date YYYY-MM-DD]
```

- **decide**: one row in `docs/decisions.md`, the next K-id, the words
  verbatim. Refuses an unresolved K-id (defined only by the two triage
  reports and the file itself: K75 is a BMW), a wrong `--kid`, a path
  that does not exist, a newline. No model.
- **digest**: `docs/fleet/digests/<date>.md`, one local day by time window:
  ROADMAP rows changed and in progress, the newest handoff's open and next
  sections, findings open, filed and closed (this repository's
  `FOLLOWUPS.md` only: mobile's headings do not mark closure), and the open
  `needs-admiral` / `needs-hands` issues. A Haiku summary on top, read-only;
  a stop writes no file.

## The read-only fence — `rank_call.py`, `fence_probe.py`

Every model call goes through `rank_call.call`: `--tools Read,Grep,Glob`
(which tools exist), `--allowedTools Read,Grep,Glob`, `--disallowedTools
Bash`, `--permission-mode dontAsk`, `--strict-mcp-config`. Full model ids,
never aliases; the served model is checked; session id and token usage are
recorded per call in `~/.local/state/motodiag/fleet/calls.jsonl` (or
`$FLEET_LEDGER`). Not `--bare`: it reads only an API key, never the
subscription login.

`fence_probe.py` proves the fence on the machine it runs on: a planted
Bash call under the fence makes no file; the control, with Bash allowed,
does. It calls the model, so it is run by hand and its output logged.

## The labels — `labels.py`

The eleven, in the order a phase passes through them: `mission`,
`step0:done`, `plan:needs-review`, `plan:approved`, `build:open`,
`review:open`, `review:clear`, `merge:needs-review`, `needs-admiral`,
`needs-hands`, `merged`. An existing label is reused, never `--force`d.
Made under the operator's login (K40), a stand-in until the fleet's own
identity (F214).

## What is held by a test

`tests/test_phase387_fleet_contract.py` (the checklist, every known-bad
case on its own item, the pin's equality, 384/386/387 at their v1.0, the
reuse, the labels), `tests/test_phase387_xo.py`, `tests/test_phase387_yeoman.py`.
