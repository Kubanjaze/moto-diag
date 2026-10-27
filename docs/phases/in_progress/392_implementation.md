# Phase 392 — The fleet follows the plan of record

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-27

---

## Goal

The fleet was built to take the operator's place as the message bus
(`docs/reports/2026-10-22_fleet_proposal.md`): answering what the plan of
record already answers, approving what already passes the written rules,
and carrying state between windows. It never reads the plan of record
(Step 0, S0-1). This phase makes it:

- every rank that plans or judges reads `docs/reports/2026-10-12_plan_of_record.md`
  and `docs/decisions.md`, and what it writes cites the dated entry or the
  K-id that bears on the phase; `plan_check` holds the v1.0 to it;
- the next mission comes from the plan's "Next, in order" list (K48),
  through a one-row pull request the operator merges by hand (K49);
- a stop the record already answers is answered from it, by lookup (K50);
- and four findings that could trip its own proof close: F223, F226
  (K45), F225 and F227 (K46, K51), F228 (K47).

Unblocks: 303 and 348, the next first-shop phase in the plan (K43).

## The plan of record

- **The entry that puts 392 in order:** the plan of record's "2026-10-26,
  later: 392 goes between 391 and 303/348", the operator's decision K44
  ("its supposed to replace what ive been doing. so bridge that gap
  however it must, thats priority, so we can continue on track").
- **What it unblocks:** 303 and 348 (K43: "a later fleet-only phase must
  name the first-shop phase it unblocks").
- **Riding along:** K45 (F226), K46 (F225, F227), K47 (F228); the Step 0
  answers K48–K51.

## Logic

1. **`.claude/skills/fleet/plan_order.py`** (new), the one reader of the
   record, pure functions, no model:
   - `order(root)`: the "Next, in order" table at the top of the plan of
     record, parsed exactly: `| # | phase | kind | built by | needs the
     operator | entry |`; `kind` is `shop` or `fleet`, `built by` is
     `fleet` or `builder`, `needs` is `nothing` or one of `an outside
     account`, `an outside person`, `a fork`, `a credential`, `a live
     change`, each with its words. Its "As of <date>, <K-id>" line names
     a dated entry under "Changes to the order" and a K-id that resolves.
   - `check(root)`: what is wrong with the list (unparsed row, a phase with
     no ROADMAP row, a phase twice, an unknown kind or need, an "As of"
     whose date has no dated entry or whose K-id does not resolve).
   - `next_entry(root, rows)`: the first entry whose row is not ✅.
   - `decisions(root)`: `docs/decisions.md`'s rows, with a fifth column,
     `Covers`: `stop=<kind> subject=<phase>[,<phase>]`, or `no stop`.
   - `bearing(root, phase)`: the order entry, each dated change that names
     the phase, each K-id row that names it; `brief_block(…)` the text a
     rank's prompt gets; `cite_line(…)` the one line a rank's comment
     ends with ("The plan of record: …; K43, K44").
   - `answer(root, kind, phase)`: the one K-id whose `Covers` names this
     stop kind and this phase, or None; never for a rule-1 kind (K50), and
     None when two match.
   - `first_shop(root)`: the phases of the plan's "Wave 1".
   Finish line: `tests/test_phase392_plan_order.py`, the real plan of
   record and decisions file parsed, and one known-bad copy per refusal.
2. **The plan of record and `docs/decisions.md`.** The "Next, in order"
   list at the plan's top, with its dated entry (2026-10-27, K48) under
   "Changes to the order". `docs/decisions.md` gains the `Covers` column
   for every row (K32–K51 all `no stop`: none answers a non-rule-1 stop);
   `yeoman.py decide` takes `--covers`, refuses a rule-1 kind and a
   malformed line.
3. **The ranks read and cite** (`scout.py`, `captain.py`, `xo.py`,
   `red_team.py`, `quartermaster.py`, and the dispatcher that calls them):
   each brief gets `brief_block` and a sentence to cite from it; each
   comment a rank posts ends with `cite_line`, written by script. The
   Science Officer's report gets a scripted "## The plan of record"
   section. The Captain's brief asks for a "## The plan of record" section
   and, for a fleet-only phase, an "Unblocks:" line.
4. **`plan_check.py` P9 and P10.** P9: the v1.0 names a K-id whose row
   names the phase, or a dated "Changes to the order" entry that names it,
   or the phase is in the order list and the v1.0 cites that entry's K-id.
   P10: for a fleet-only phase (the list's kind `fleet`; or, not listed,
   a plan naming `.claude/skills/fleet/` and no `src/`), a line naming
   "unblocks" and a Wave 1 phase whose row is not ✅. 384–391's v1.0 are
   pinned for both (`WRITTEN_BEFORE`), equality-tested. A known-bad case
   for each in `fixtures/bad/cases.json`, seen red; the good tree gains a
   plan of record and a decisions file.
5. **The next mission** (`dispatcher.py`, a `next` stage, journaled): each
   cycle, `next_entry`. Built by a builder: wait, logged once. Built by
   the fleet, no open issue for it (opened by the fleet or the operator):
   open `Phase <N>: <title>` with `mission`, its body naming the work
   branch and quoting the entry. If the entry needs the operator: one
   plain-English comment quoting the entry and `needs-hands` (an account,
   a person, a credential) or `needs-admiral` (a fork, a live change); no
   pull request until the label is off. Otherwise, the row not 🚧 on
   `master` and no open row PR: branch `phase-<N>-row` from `master`, the
   row's status alone changed to 🚧, pushed through the gate as a new
   rank `row` (G3: `docs/ROADMAP.md` only, one row, its status alone), a
   PR whose body tells the operator, plainly, that merging starts the
   phase. The fleet never pushes to `master` (G1, unchanged). Once merged,
   the cycle's existing rule (row 🚧, `mission`) starts the Science
   Officer.
6. **Answered stops** (`dispatcher.py`): an Engineer stop of kind
   `third-bug-fix` or `guard-blocked-twice` asks `answer()` first. A match:
   a `<!-- fleet-answered: kid=… stop=… -->` comment quoting the K-id's
   words verbatim, and the Engineer runs again with them in its brief. One
   answer per K-id and stop per issue: the same stop again goes to the
   operator. Every other stop is unchanged.
7. **F223** (`dispatcher.py`, `xo.py`, `quartermaster.py`): `comments()`
   keeps only comments whose author is the fleet's login, or the
   operator's on an issue whose body carries `<!-- fleet-trial -->`; the
   cycle and `recover` act only on issues opened by those two. Every
   due rule, round count, marker search and model brief reads through it.
   Known-bad: a planted Red Team clear, Captain merge and XO verdict from
   a third login, each ignored.
8. **F226** (`dispatcher.py`): `clean_tmp(run)` removes `run/tmp` but the
   `motodiag_worker_loss_*` folders. Called when a stage's journal ends
   (not a pause, not a held run), when a check run returns, and when a
   held run is released; `prune_runs` also cleans every ended, unheld,
   unpaused run's `tmp` it keeps. The reclaim line adds "nothing came back
   to Windows (the disk image is not sparse)" when C: did not move. The
   fleet skill's "Free space" and F221's method say what replaced the
   shrink. Known-bad: a held, a paused and an unfinished run each keep
   their `tmp`; the worker-loss files survive.
9. **F225** (`dispatcher.py`): `CHECK_TIMEOUT_S = 5400` (K51); a run past
   it returns a failed `Check` naming the limit, and the fence's process
   group is killed. The stage stops the usual way. Known-bad: a planted
   over-limit command.
10. **F227** (`ops/desktop/motodiag-fleet.service`): `LimitNOFILE=1048576`
    (K51); the service contract's known-bad case, a unit without it. One
    worker's peak open files measured in the fence
    (`392_fd_probe.py`), the leak looked for at the peak; a planted run
    under a small limit seen to fail. Installing the unit is the
    operator's paste block (sudo).
11. **F228** (`red_team.py`, `dispatcher.py`): the brief states C7 in its
    own words; on a back before round 3 C7 is set aside as C6 is; on a
    clear, or a back in round 3, the dispatcher files the one finding
    (the next number over both repositories) and writes it into each open
    wording row, committed with the table. Known-bad: #14's round-3 table
    (`fixtures/red_team/14_round3.json`).
12. **The skill, its CHANGELOG, the findings** F223, F225–F228 closed.

## The change log's three newest entries

- **2026-10-26, R8: an operator paste block's `gh` names its repository.**
  The check it became: `tests/test_roadmap_continuity.py`
  (`.claude/skills/closeout/roadmap_check.py` R8). This phase's operator
  blocks carry `-R Kubanjaze/moto-diag`.
- **2026-10-22, `fleet` joins the procedure folders.** The folder's own
  tests hold it (`tests/test_phase387_fleet_contract.py`); the row is
  text. This phase extends the folder.
- **2026-10-20, rule 6: plain English to the operator.** No check: the
  entry says "Text only; no check holds it." The next-mission comments,
  the row PR's body and the handoff's blocks are written to it.

## Rule-1 stops anticipated

- **A real fork:** none open; the four Step 0 questions are answered
  (K48–K51).
- **A threshold or a rule's definition:** the open-file limit and the
  check's time limit, set by the operator (K51). Nothing else changes.
- **A test that cannot be made green:** none expected.
- **A login or a credential:** the unit's install needs the operator's
  sudo: one paste block.
- **A live-database change:** none expected; nothing here reads live.

## Tests

- `tests/test_phase392_plan_order.py`: the real list and decisions parse;
  `check` on each known-bad copy; `bearing` for 392, 303 and 348;
  `answer` matches one K-id, refuses a rule-1 kind and two matches.
- `tests/test_phase392_next_mission.py`: on stand-ins, builder waits; a
  fleet entry opens its issue and its row PR once; an entry needing the
  operator asks once and waits for the label; a resumed `next` stage
  makes nothing twice; the `row` rank's gate refuses another row, a
  second file and a change past the status.
- `tests/test_phase392_answers.py`: an Engineer stop answered from a
  covering K-id (quoted verbatim), a rule-1 kind never, the same stop
  twice goes to the operator.
- `tests/test_phase392_authors.py`: F223's planted third-login markers and
  issue.
- `tests/test_phase392_tmp.py`: F226's deletion and its four known-bad
  cases; the reclaim line.
- `tests/test_phase392_check_limit.py`: F225's planted over-limit command,
  through a stage to one stop.
- `tests/test_phase392_red_team_c7.py`: F228 on #14's table.
- `tests/test_phase388_service_contract.py`: the unit's limit and its
  known-bad case. `tests/test_phase387_fleet_contract.py`: P9 and P10's
  cases, the pin.
- `docs/phases/in_progress/392_mutate.py`: each new rule broken, every
  mutation red.
- `COLLECTED_TEST_FLOOR` raised by the diff of collected ids;
  `wholetree.sh` before each commit; the regression of record inside the
  fence.

## Non-goals

- Promoting the Quartermaster; merging anything; the operator's master
  ruleset.
- Running 303 or 348 here: after the merge, the fleet starts them.
- Any migration, anything under `data/`, seed data, a split or an eval
  protocol, or live.
- Changing the order of any row, or what any entry needs.

## Planned items

- [ ] `plan_order.py`, the list, the `Covers` column, `decide --covers`
- [ ] the ranks read and cite
- [ ] P9, P10, their cases, the pin
- [ ] the next mission and the `row` rank
- [ ] answered stops
- [ ] F223
- [ ] F226, with the disk measured before and after two stages
- [ ] F225, F227 (the probe, the unit)
- [ ] F228
- [ ] skill, CHANGELOG, findings; mutations; regression; close-out; handoff
