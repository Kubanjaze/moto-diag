# Phase 387 — The XO and the Yeoman

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-22 (v1.0 the same day, `ea6fed8`)

---

## Goal

Steps 2 and 3 of `docs/reports/2026-10-22_fleet_proposal.md` in one
phase: the Executive Officer, who reviews a plan, and the Yeoman, who keeps
the decisions file and writes a daily digest. Both are read-only: nothing
here pushes code or merges. The prompt is
`docs/prompts/387_xo_and_yeoman.txt`; Step 0 is `387_step0.md`
(classification: extension).

What shipped is a new skill folder, `.claude/skills/fleet/`, in the shape of
`closeout` and `finding`: `SKILL.md`, `CHANGELOG.md`, five scripts and a
shared call module, hand-written known-bad fixtures, and three test files.
Plus the eleven GitHub labels, made with `gh` under the operator's login.

The operator's pick at Step 0 (verbatim in the log, K41): **"Pin them
(Recommended)"**. The checklist's three items that 384 and 386 predate
are not applied to those two plans; every plan from 387 on faces every
item.

## Logic

### 1. `plan_check.py`: the checklist, no model

`plan_check.py <phase> [--repo PATH] [--rev COMMIT] [--no-pin]` reads,
from the working tree or from one commit (`git show <rev>:<path>`), four
files: the ROADMAP, `CLAUDE.md`, and the phase's `implementation.md` and
`step0.md` under `docs/phases/in_progress/`. `--rev` is how 384's and
386's v1.0 are checked as they were committed (`b6ffcb6`, `5d0a687`).
Exit 0 pass; 1 fail, each failed item printed by its id; 2 when the
ROADMAP, `CLAUDE.md` or the implementation document cannot be read.
`--self-test` builds every known-bad case and shows each fires alone.

| id | the item | how |
|---|---|---|
| P1 | the phase has a ROADMAP row and it is 🚧 | `roadmap_check.rows()` and `ACTIVE`, imported |
| P2 | `<N>_step0.md` exists | a file read; when it is missing, P3 and P4 are reported as not judged |
| P3 | every count in the step-0 report shows the query that produced it | the count rule (below) |
| P4 | the step-0 classification is greenfield or extension; reshape fails, and so does none | a `Classification:` line, its first word |
| P5 | the plan names none of the four content kinds the prompt lists | patterns in `SKILL.md`; the knowledge path from `wholetree.CONTENT_PATHS`, imported; the Non-goals section is not read |
| P6 | every section is filled, no stubs; Goal and Logic present | a heading with nothing under it before the next heading at its level or above; a line that starts with a stub word |
| P7 | the plan cites the three newest `CLAUDE.md` change-log entries and the check each became | a block holding the entry's date and either a backticked path that exists (at `--rev`, in that commit) or "no check", accepted only when the entry itself says "text only" or "no check" |
| P8 | the rule-1 stops the plan anticipates are listed | a heading naming stops, holding bullets; each one of rule 1's five kinds, or "none" |

**The count rule (P3).** A block is a paragraph, a bullet item with its
continuation lines, or one table row with the block just before its table.
A count is a number followed within two words by a counted noun (a plural,
or passed, failed, skipped), with no preposition, article or verb between.
Not counts: numbers in arithmetic, after "step", "item", "phase", "row",
"line", "port", "schema", "migration" and the like, and four-digit years.
A count is shown when its block, or its table's lead, holds a backticked
command or script.

**The stub rule (P6)** matches a line that *starts* with a stub word,
after any list marker: matching anywhere would fail the plan that names
the stub words to describe this check.

**The pin.** `WRITTEN_BEFORE = {"384": {P4, P7, P8}, "386": {P7, P8}}`.
The report names each skipped item and what it would have failed on.

### 2. `xo.py` and `rank_call.py`

`xo.py review <phase> --issue <n>` (or `--no-label`):
1. `plan_check` (the same function). A failure is back-to-captain with the
   failed items; no model call.
2. On a pass, one call through `rank_call.call`: the brief, the
   checklist's result, the plan and the step-0 report; from the repository
   root; `--model claude-fable-5-1`; `rank_call.FENCE`: `--tools
   Read,Grep,Glob`, `--allowedTools Read,Grep,Glob`, `--disallowedTools`
   Bash plus Read, Grep and Glob on `SECRET_HOMES` (bug fix #1),
   `--permission-mode dontAsk`, `--strict-mcp-config`; `--output-format
   json`; `--json-schema` with the fixed verdict.
3. **A stop** (exit 3, no label moved, a comment saying why): claude
   exits non-zero, prints no JSON or reports an error; the model asked for
   is not served; no token usage or no session id; no `structured_output`;
   a verdict outside the schema, a back-to-captain with no items, a
   recommend-to-admiral with no reason; `gh` refusing the comment or the
   label.
4. The label from the parsed verdict: approve → `plan:approved`;
   back-to-captain → `plan:needs-review`; recommend-to-admiral →
   `needs-admiral`. Setting one removes the other two. The comment opens
   with `<!-- xo-verdict: <given> round=<n> applied=<applied> … -->`; the
   rounds are counted from those markers; a third back-to-captain is
   applied as needs-admiral.
5. Every call is recorded (session id, served model, the four token
   counts, list cost, turns, wall time) in the comment and in
   `~/.local/state/motodiag/fleet/calls.jsonl` (`$FLEET_LEDGER`).

### 3. `yeoman.py`: `decide` and `digest`

**`decide`** appends one row to `docs/decisions.md`: the next K-id, the
date, the words verbatim in quotes (`|` escaped for the table), the
check. It refuses a `--kid` that is not the next, a cited K-id that does
not resolve (`### K<n>.` headings and `- **K<n>` bullets in the two
triage reports; `| K<n> |` rows in the file), a backticked path that does
not exist, a newline, an empty field, a malformed date. No model.

**`digest`** writes `docs/fleet/digests/<date>.md` for one local day. The
two ends of the window are the last commits before 00:00 and before the
next 00:00 (`git rev-list -1 --before`). From those two commits and `gh`:
the ROADMAP rows added or changed (status or text) and every 🚧 row at the
end; the newest handoff by the end, with its "What is open" and "What is
next" sections quoted; findings open at the end (a heading without CLOSED
or FOLDED INTO; the title from the heading or the line under it), filed and
closed in the window; `needs-admiral` and `needs-hands` issues open, or
updated in the window. One Haiku call, through `rank_call` with the same
fence, writes a summary of at most 120 words from the facts only, under
its own heading. Every date, F- or K-id and number of two digits or more in
it must be in the facts, or it is set aside with what it invented named
(bug fix #2). A stop writes no file.

### 4. `labels.py`

`gh label list` first; an existing label reused untouched; a missing one
made with `gh label create` (never `--force`); before and after printed;
`--check` lists only.

### 5. `fence_probe.py`

Three model calls on the machine it runs on: the planted Bash call under
`FENCE` must make no file; the control, Bash allowed, must make it; a
canary under `~/.config` must not reach the session through Read, Grep or
Glob while a repository file is read. Exit 0 only when all three hold.

## The change log's three newest entries

- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." The one question this phase
  put to the operator was asked in plain words.
- **2026-10-19, live is on the home desktop.** The check it became:
  `tests/test_phase382_live_location.py`. Nothing here reads live.
- **2026-10-07, rule 6 standing practice; the deploy order.** The check
  for the deploy order: `tests/test_phase378_deploy_order.py`. No
  migration here. The standing lines followed: the whole-tree command run
  on its own before every commit; `COLLECTED_TEST_FLOOR` raised by a diff
  of collected ids; each guard block recorded, the guards unchanged.

## Rule-1 stops anticipated

- A real fork in the checklist's design: met at Step 0 and answered, "Pin
  them (Recommended)".
- A test that cannot be made green: none met.
- A login or a credential: none asked for.
- None from a live-database change or a threshold: nothing touched live.

## Tests

- `tests/test_phase387_fleet_contract.py` (53): every known-bad case on its
  own item and no other; every item has a case; a case that edits nothing
  is refused; the good tree passes; 384, 386 and 387 pass at their v1.0
  commits with exactly their pinned items skipped, 387 with none; the
  pin's equality; exit codes 0, 1, 2 and the self-test; the reuse of
  `roadmap_check` and `wholetree`; the labels' names and their reuse; the
  count rule's planted count, its query, and five things that name rather
  than count.
- `tests/test_phase387_xo.py` (18): with stand-ins for `claude` and `gh`,
  each verdict's label and only that; the marker and the recorded call;
  rounds two and three; a failed checklist calls no model; an unreadable
  plan; seven stops that move no label; `--no-label`; the fence flags,
  including the credential homes.
- `tests/test_phase387_yeoman.py` (21): `decide`'s K-id sources, one row
  verbatim, seven refusals that write nothing, K1–K39 on the real file;
  `digest` on a git history with dated commits (the day and not the day
  after, the day before not seeing the day, findings by heading, the
  handoff by the window's end, issues by state and window), the file
  written, the invented date set aside, a summary from the facts kept,
  three stops.
- `fence_probe.py`, by hand (it calls the model).
- `387_mutate.py`: 52/52 red.

## Non-goals

- The dispatcher, the Linux fence, the Captain, the Engineer, the Red
  Team, the Quartermaster: later rollout steps.
- The fleet's own GitHub identity and the master ruleset (F214).
- The activity log on the Mac as a digest input: a later phase, named in
  the handoff.
- Mobile's `FOLLOWUPS.md` in the digest: its headings do not mark closure.
- Any path under `data/`, seed data, a train/test split or an eval
  protocol: none is touched.
- Widening `finding_check.py` B2 (F213): the operator's call.

## Planned items

- [x] `plan_check.py`, the good and known-bad fixtures, the contract test
- [x] the count rule tightened and its rate over the 34 reports
- [x] `xo.py` and its tests
- [x] `yeoman.py` (`decide`, `digest`) and its tests
- [x] `labels.py`; the eleven labels made; the stand-in row in `decisions.md` (K40)
- [x] `SKILL.md`, `CHANGELOG.md`; the fence probe in the skill
- [x] the mutation run
- [x] the proofs in the log; the real XO run on this plan; one digest
- [x] `COLLECTED_TEST_FLOOR` raised
- [x] close-out: `wholetree.sh --full`, `regression.sh`, the handoff,
      `verify_phase.sh`, row 387 to ✅

## Deviations

- **Two bug fixes, both from the proofs.** The XO's first real verdict
  named a gap its own fence left: reads reach anywhere. Bug fix #1 denies
  the credential homes, and F215 carries real confinement to the fence
  phase. The first real digest invented a year; bug fix #2 checks a
  summary's dates, ids and numbers against the facts.
- **`rank_call.py` is a sixth file the plan did not name.** The XO and the
  digest make the same fenced call with the same stops; two callers, one
  implementation.
- **`fence_probe.py` gained a read case** with bug fix #1.
- **A mission issue was opened**, #9, for the XO's label to sit on. The
  plan said "the mission issue" and did not say who opens it; this run
  opened it with `mission` and `plan:needs-review`, under the operator's
  login.
- **K41 was recorded too.** The plan named one `decide` row (K40); the
  operator's Step 0 answer is a decision of the same kind.
- **`docs/decisions.md`'s header** no longer says nothing checks K-ids:
  `decide` checks its own row; K-ids cited elsewhere are still unchecked.
- **The count rule's rate barely moved:** 32 of 34 reports before and
  after, 198 blocks to 197. The tightenings removed false hits in this
  phase's own report; the older reports' hits are mostly real.
- **The root `phase_log.md` gained 386's pointer** with 387's: 386's own
  close-out did not add one.
- **Two guard blocks of my own making** (commit and push in one command)
  and one edit-guard block (a redirect to a variable path), each in the
  log; no guard changed.

## Results

### Step 0's measurements

- `claude -p` on this login serves `claude-fable-5-1`, `claude-opus-5-5`
  and `claude-haiku-5-5`, by full id and by alias (S0-1). Pre-approval (a)
  was not needed.
- The fence (S0-2, then `fence_probe.py` twice): a planted Bash call made
  nothing; the control made its file; after bug fix #1, a canary under
  `~/.config` was denied to all three read tools.
- `gh`: the operator's admin login; 9 labels before, 20 after.
- One XO call on 386's v1.0 (dry run): 148,263 tokens read, 7,347 written,
  11 turns, 100 s, $1.22 at list price. On 387's v1.0 (the real run):
  242,198 read (162 input, 38,802 cache write, 203,234 cache read), 7,699
  written, 20 turns, 99 s, $1.21.
- One digest summary on Haiku: under 25,000 tokens read, under 3,600
  written, 2 turns, 8–14 s, about $0.01.

### The proofs

All five are in the log: 384 and 386 PASS at their commits with their
pinned items named; the 21 known-bad cases each fail on their own item;
the planted Bash call refused; the XO approved 387 and set
`plan:approved` on issue #9; the digest for 2026-10-22.

### The regression of record

Regression of record: 11092 passed, 0 failed, 1 skipped, 0 errors at `c64e055` (20 min 44 s wall, `python -m pytest -n auto --dist load`, exit 0)
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine

The one skip is the expected one (244H). `wholetree.sh --full` on the same
commit: 4318 passed, 104 files. 92 tests added; `COLLECTED_TEST_FLOOR`
11093.
