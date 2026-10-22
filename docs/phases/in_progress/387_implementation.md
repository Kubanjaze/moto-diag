# Phase 387 — The XO and the Yeoman

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-22

---

## Goal

Steps 2 and 3 of `docs/reports/2026-10-22_fleet_proposal.md` in one
phase: the Executive Officer, who reviews a plan, and the Yeoman, who keeps
the decisions file and writes a daily digest. Both are read-only: nothing
here pushes code or merges. The prompt is
`docs/prompts/387_xo_and_yeoman.txt`; Step 0 is `387_step0.md`
(classification: extension).

What ships is a new skill folder, `.claude/skills/fleet/`, in the shape of
`closeout` and `finding`: `SKILL.md`, `CHANGELOG.md`, three scripts,
hand-written known-bad fixtures, and a contract test. Plus the eleven
GitHub labels, made with `gh` under the operator's login.

The operator's pick at Step 0 (verbatim in the log): **"Pin them
(Recommended)"**. The checklist's three items that 384 and 386 predate
are not applied to those two plans; every plan from 387 on faces every
item.

## Logic

### 1. `plan_check.py`: the checklist, no model

`plan_check.py <phase> [--repo PATH] [--rev COMMIT]` reads, from the
working tree or from one commit (`git show <rev>:<path>`), four files: the
ROADMAP, `CLAUDE.md`, and the phase's `implementation.md` and `step0.md`
under `docs/phases/in_progress/`. `--rev` is how 384's and 386's v1.0 are
checked as they were committed (`b6ffcb6`, `5d0a687`). Exit 0 pass; 1 fail,
each failed item printed by its id; 2 when the ROADMAP, `CLAUDE.md` or the
implementation document cannot be read.

| id | the item | how |
|---|---|---|
| P1 | the phase has a ROADMAP row and it is 🚧 | `roadmap_check.rows()` and `ACTIVE`, imported |
| P2 | `<N>_step0.md` exists | a file read |
| P3 | every count in the step-0 report shows the query that produced it | Step 0's count rule, tightened (below) |
| P4 | the step-0 classification is greenfield or extension; reshape fails, and so does none | a `Classification:` line, its first word |
| P5 | the plan names none of the four content kinds the prompt lists | patterns in `SKILL.md`; the knowledge path comes from `wholetree.CONTENT_PATHS`, imported; the Non-goals section is not read, so a plan may say what it leaves alone |
| P6 | every section is filled, no stubs; Goal and Logic present | a heading with nothing under it before the next heading at its level or above; stub words (TBD, TODO, placeholder, "to be written", a lone ellipsis) |
| P7 | the plan cites the three newest `CLAUDE.md` change-log entries and the check each became | the three newest `### YYYY-MM-DD —` headings under "Change log"; a block of the plan holds the date and either a backticked path that exists in the repo (at `--rev`, in that commit) or "no check", accepted only when the entry itself says "text only" or "no check" |
| P8 | the rule-1 stops the plan anticipates are listed | a heading naming stops, holding bullets; each names one of rule 1's five kinds, or says none is expected |

**The count rule (P3).** A block is a paragraph, a bullet item with its
continuation lines, or one table row with its table's lead paragraph. A
count is a number followed within two words by a counted noun (a plural,
or passed, failed, skipped). It is shown when its block holds a backticked
command or script. The tightening, each measured over the 34 step-0
reports before and after: numbers inside arithmetic, after "step",
"item", "phase", "row", "line", "port", "schema" or "migration", and
four-digit years are not counts. The rate on the 34 is recorded in
Results; a hit on an honest report means back to the Captain, which costs a
round, never a wrong approval.

**The pin.** `WRITTEN_BEFORE = {"384": {"P4", "P7", "P8"}, "386": {"P7",
"P8"}}`: those items are not applied to those plans, and the report says
which were skipped. A test holds it to equality: without the pin, each
pinned plan fails on exactly its pinned items, so the pin can neither grow
nor keep an item that is no longer needed.

### 2. `xo.py`: one read-only call, the label set by the script

`xo.py review <phase> --issue <n>`:
1. Runs `plan_check` (the same function, imported). A failure is
   back-to-captain with the failed items; no model call.
2. On a pass, one `claude -p` call: the plan, the step-0 report and the
   checklist's result in the prompt, from the repository root, `--model
   claude-fable-5-1`, `--tools Read,Grep,Glob`, `--allowedTools
   Read,Grep,Glob`, `--disallowedTools Bash`, `--permission-mode dontAsk`,
   `--strict-mcp-config`, `--output-format json`, and `--json-schema` with
   the fixed verdict: `approve`; `back-to-captain` with `items`;
   `recommend-to-admiral` with a `reason`.
3. A **stop** (exit 3, no label moved, a comment saying why) when the call
   fails, the served model is not the one asked for, `structured_output`
   does not match the schema, or the JSON carries no usage. A call with no
   recorded usage is a stop.
4. The label, from the parsed verdict: approve → `plan:approved`;
   back-to-captain → `plan:needs-review`; recommend-to-admiral →
   `needs-admiral`. Each verdict is a comment on the mission issue with a
   machine-readable marker line. The rounds are counted from those
   markers: a third back-to-captain becomes `needs-admiral`.
5. Every call is recorded: session id, served model, the four token counts,
   list cost, turns, wall time. It goes in the issue comment and in a ledger
   outside the repository (`~/.local/state/motodiag/fleet/calls.jsonl`).

`--no-label` prints the label it would set and touches nothing on GitHub.
`gh` and `claude` are run through one injectable runner, so the tests
drive both with stand-ins.

### 3. `yeoman.py`: `decide` and `digest`

**`decide --words "…" --check "…" [--date] [--kid]`** appends one row to
`docs/decisions.md`: the next K-id, the date, the words verbatim (a `|`
escaped for the table, a newline refused), and the check it became. It
refuses when `--kid` is not the next free K-id, when any K-id cited in the
words or the check does not resolve (Step 0's S0-8: the two triage reports'
headings and bullets, and this file's rows), or when a backticked path in
the check does not exist. No model: the words are the operator's, and a
model in that path could only change them.

**`digest [--date YYYY-MM-DD]`** writes `docs/fleet/digests/<date>.md` for
one local day, by time window, from four inputs and nothing else:
- ROADMAP rows added or changed between the window's two ends (the file
  at the last commit before each), and every 🚧 row at the end;
- the newest handoff at the window's end, with its "What is open" and
  "What is next" sections quoted;
- open findings in `docs/FOLLOWUPS.md` at the end (a heading without
  CLOSED or FOLDED INTO), and those filed or closed inside the window;
- open GitHub issues labelled `needs-admiral` or `needs-hands`, and those
  updated inside the window.

The facts are the script's. Then one Haiku call (`claude-haiku-5-5`, the
same read-only flags as the XO) writes a plain-English summary of at most
120 words from those facts, placed under its own heading and marked as the
model's. The same stop rule as the XO: a call with no usage, or the wrong
model served, writes no file.

### 4. The labels

`labels.py` (in the skill): for each of the eleven names, `gh label list`
first; an existing label is reused untouched (pre-approval (b)); a missing
one is made with `gh label create` (no `--force`). Before and after lists
are printed. `docs/decisions.md` gets a row through `decide` saying that the
operator's login is a stand-in until the identity phase (F214).

### 5. The proofs, in the phase log

- `plan_check` on 384's and 386's v1.0 at their commits: pass, with the
  pinned items named;
- `plan_check` on every known-bad case: each fails on its own item, by id;
- a planted Bash call from the XO's tool set: refused (Step 0's probe, now
  a script in the skill with its control);
- one real `xo.py` run on this plan: the verdict and the label it set;
- one `yeoman.py digest`.

## The change log's three newest entries

- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." This phase hands the
  operator nothing to run; a stop's question follows the rule.
- **2026-10-19, live is on the home desktop.** The check it became:
  `tests/test_phase382_live_location.py` (every tool that reads live
  refuses, exit 4, off the desktop). Nothing here reads live.
- **2026-10-07, rule 6 standing practice; the deploy order.** The check
  for the deploy order: `tests/test_phase378_deploy_order.py`. No
  migration here. The standing lines this phase follows: the whole-tree
  command run on its own before every commit; `COLLECTED_TEST_FLOOR`
  raised by a diff of collected ids (pre-approval (c)); a blocked guard
  recorded, never loosened.

## Rule-1 stops anticipated

- A real fork in the checklist's design: met at Step 0 and answered, "Pin
  them (Recommended)".
- A test that cannot be made green: the regression of record, the
  whole-tree command, and the new contract test.
- A login or a credential: if `gh` or `claude` asks for one mid-run.
- None expected from a live-database change or a threshold: nothing here
  touches live, and the checklist's items are the operator's words.

## Tests

- `tests/test_phase387_fleet_contract.py`: every known-bad case fails on
  its own item and on no other; the good fixture passes; 384 and 386 pass
  at their commits with exactly their pinned items skipped; the pin's
  equality; exit 2 on an unreadable plan; the reuse (P1 calls
  `roadmap_check.rows`, P5 reads `wholetree.CONTENT_PATHS`).
- `tests/test_phase387_xo.py`: with a stand-in `claude` and `gh`: each
  verdict sets its label and only that; a failed checklist calls no
  model; the third back-to-captain becomes `needs-admiral`; each stop (no
  usage, wrong model, bad schema, exit ≠ 0) moves no label; the command
  line carries the fence flags and never `Bash`.
- `tests/test_phase387_yeoman.py`: `decide` writes one row with the next
  K-id and refuses an unresolved K-id, a wrong `--kid`, a missing path, a
  newline; the K-id resolver reads the two reports and the file, and not a
  BMW K75 elsewhere; `digest` reads a fixture repository by its window:
  a row changed the day before is out, one changed that day is in; the
  findings rule; the issue lists; the stop rule.
- The fence probe as a script with its control, run by hand for the proof
  (it calls the model, so no test runs it).
- Mutations over the checks and the label map, each seen to turn a test
  red.

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

- [ ] `plan_check.py`, the good and known-bad fixtures, the contract test
- [ ] the count rule tightened and its rate over the 34 reports
- [ ] `xo.py` and its tests
- [ ] `yeoman.py` (`decide`, `digest`) and its tests
- [ ] `labels.py`; the eleven labels made; the stand-in row in `decisions.md`
- [ ] `SKILL.md`, `CHANGELOG.md`; the fence probe in the skill
- [ ] the mutation run
- [ ] the proofs in the log; the real XO run on this plan; one digest
- [ ] `COLLECTED_TEST_FLOOR` raised
- [ ] close-out: `wholetree.sh --full`, `regression.sh`, the handoff,
      `verify_phase.sh`, row 387 to ✅
