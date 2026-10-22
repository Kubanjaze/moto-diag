# Phase 386 — Fleet records: the debts, the measurements, the accounts

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-22

---

## Goal

Step 1 of the rollout in `docs/reports/2026-10-22_fleet_proposal.md`: a
records phase. It closes the parts of the proposal's debt table that
Step 0 confirmed, writes down what Step 0 measured (one phase's token
cost, how this Mac is logged in, the usage baseline), seeds the fleet's
decisions file, and records how a dispatcher is logged in on the
subscription and how to check the billing went there.

The prompt is `docs/prompts/386_fleet_records.txt`. Its scope, in the
operator's words: "It is a records phase: documentation, measurements and
the fleet's accounts. No change under src/ or tests/. The dispatcher,
plan_check.py, the Linux fence and every later rollout step are their own
phases later, each with its own row; do not start them here."

Step 0 is `386_step0.md`. What it decided for this plan:
- **Confirmed, fixed here:** the root `phase_log.md` stops at 255B;
  `implementation.md` line 6's Windows path (and line 7's count);
  `docs/contributing.md`'s "~9 minutes".
- **Confirmed, not this phase's:** `CLAUDE.md`'s `../workspace-docs`
  import (the fence phase's ninth case; a `CLAUDE.md` edit is the
  operator's).
- **Refuted, no change:** the version split, `README.md`, F132–F134, 072.
- **Found:** `finding_check.py` B2 reads only completed phase documents,
  so it cannot see a lost F133 or F134.

The operator's answers to Step 0 (2026-10-22, verbatim in the log): the
desktop is ALL GOOD; the usage figures are "a baseline only"; K11 comes on
10/23; GitHub accounts and master protection are "for a later phase", with
one finding carrying two facts.

## Logic

Each item is its own commit, `wholetree.sh` run on its own before each,
its exit code read.

### 1. The root `phase_log.md` catch-up

`ROADMAP_AUTHORITY.md` names the backend `phase_log.md` an authoritative
surface for 205+. Its last entry is 255B (2026-09-22). Measured at plan
time: of the phases from 255 on with documents in `completed/`, 41 have no
heading in the root log naming them (255, 256, 255C, 255D, 257 … 384).

One dated section, "Catch-up, written 2026-10-22 (Phase 386)", then one
pointer entry per phase in close order, in the shape 255B's entry uses:
`## Phase N — <ROADMAP title> — CLOSED <date>`, and the links to its
`phase_log.md` and `implementation.md` in `completed/`. The title and date
come from the ROADMAP row, by a script that reads the row and stops on any
phase with no CLOSED date or no documents. No summary is written: the row
and the phase's own log carry it, and a summary written now would be a
second account of each phase.

Also measured: 205–240 (Tracks J and K, less 210) are missing from the
root log as well, an older gap the proposal did not name. They are
recorded in the log and the handoff, not backfilled here: the debt
confirmed was the tail after 255B.

### 2. `implementation.md` lines 6 and 7

- Line 6: `**Local:** \`~/Projects/moto-diag\``, as `CLAUDE.md` has it.
- Line 7: "352 phases across 21 tracks (A-T)" becomes a pointer that does
  not go stale: the ROADMAP is the count, 21 tracks (A–T and C2), with the
  count measured today (403 rows, 365 numbered and 38 letter follow-ons,
  by `grep -cE '^\| *[0-9]{2,3}[A-Z]? *\|' docs/ROADMAP.md`).

### 3. `docs/contributing.md`

Line 18's `pytest -q  # full suite (~9 minutes)` becomes the command of
record and its last measured time: `.claude/skills/closeout/regression.sh`
(`python -m pytest -n auto --dist load`, 27 min 52 s at 384), with plain
`pytest -q` kept as the serial way and no time claimed for it.

### 4. Two findings, by the `finding` skill

The numbers come from `next_f_number.sh` when each is filed, and no
document cites a number before its entry exists.
- **B2's scope:** a lost entry cited only by the ROADMAP, a report or
  `FOLLOWUPS.md` itself passes; Step 0's planted control is the evidence.
  To close: a later phase widens what B2 reads. Changing the check is not
  done here (a rule's definition, rule 1).
- **GitHub, the two facts** the operator named: rulesets are free on a
  public repo and moto-diag is public today, so if it goes private,
  master protection becomes a GitHub Pro purchase, not a click; and the
  fleet's own GitHub identity (an App, or a machine user with write) is
  created in the phase where a rank first pushes. Step 0's read-only
  queries are the evidence that nothing is protected today.

### 5. `docs/decisions.md`

A new file. K-ids continue the existing sequence (the proposal: "not a
third numbering scheme"). K1–K31 are in the two process-kinks triage
reports; the highest in use is K31
(`grep -rhoE '\bK[0-9]{1,3}\b' docs CLAUDE.md .claude`, outliers checked:
K46, K67, K75 and K100 are BMW model and chassis codes, K73 is in a Honda
part number, K0 a Honda generation). So the seed starts at **K32**.

One line per quoted operator sentence in
`docs/reports/2026-10-12_plan_of_record.md`, eight in all: id, date, the
words verbatim, the check it became. The date is the one the plan of
record gives the words, or the date of the change they sit under. Where
the words became a document and no check, the line says "no check" and
names the document; it does not invent one.

### 6. The setup-token and Haiku billing procedure

A dated entry in `.claude/skills/deploy/CHANGELOG.md` (the deploy skill
already holds the desktop and the door; the dispatcher will run there).
Text only, no code. It covers:
- logging a dispatcher in with `claude setup-token` as the user it runs
  as, the token kept in a mode-600 env file, never printed;
- proving no `ANTHROPIC_API_KEY` is in its environment, the same places
  Step 0 searched on the Mac, plus the service's own environment;
- an environment built from nothing for each call, carrying only
  `CLAUDE_CODE_OAUTH_TOKEN`, the way `orchestrate.py`'s `run_stage` and
  `check_route` already do;
- the Haiku billing check: one `claude -p` call on Haiku in that
  environment, the served model read from its JSON, then the operator
  confirms claude.ai Settings > Usage moved and Console billing did not.

### 7. Results

The measured numbers from Step 0 items 2, 3 and 6, in this document's
Results at v1.1.

## Non-goals

- Anything under `src/` or `tests/`; the dispatcher, `plan_check.py`, the
  Linux fence, the Yeoman and every later rollout step.
- GitHub accounts and the master ruleset: the operator, 2026-10-22, "leave
  both for a later phase".
- Running the setup-token login or the Haiku call: a login is the
  operator's (rule 1), and the dispatcher's machine is set up in its own
  phase. This phase writes the procedure.
- The Subconscious account (K11): recorded in the log when the operator
  confirms it, nothing done to the account.
- Changing `finding_check.py` B2, or `CLAUDE.md`'s import.
- Backfilling the root log for 205–240.

## Planned items

- [ ] 1. Root `phase_log.md` catch-up, 255 → 384
- [ ] 2. `implementation.md` lines 6 and 7
- [ ] 3. `docs/contributing.md` suite command and time
- [ ] 4a. Finding: B2's scope
- [ ] 4b. Finding: GitHub's two facts
- [ ] 5. `docs/decisions.md`, K32 on
- [ ] 6. The setup-token and Haiku billing procedure
- [ ] 7. Results: Step 0 items 2, 3, 6
- [ ] K11 in the phase log, in the operator's words (10/23)
- [ ] Close-out: `wholetree.sh --full`, `regression.sh`, the handoff,
      `verify_phase.sh`, row 386 to ✅

## Deviations

None yet (v1.0).

## Results

Written at v1.1.
