# Phase 389A — Step 0: Phase 389A: 385's ROADMAP row

**Written 2026-10-25** by the Science Officer (`scout.py`, Haiku), from
mission issue #14, on this branch from `master` at `6adffc5`. The
counts are the script's; the judgement below them is the model's.

Classification: **extension.** The mission adds one new row for Phase 385 to docs/ROADMAP.md and touches no code. The census finds no row for Phase 385 anywhere in docs, while the committed prompt, the F212 finding and the operator's K39 decision all already exist, so the row is a new entry in an existing ledger that changes no behaviour.

## The overlap census

The census, no model: each count is `git grep -c -i -F -e <term> -- <area>` summed over files, run on this branch's clone (the mobile repository's from `git -C ../moto-diag-mobile grep … -- src`).

| term | src | tests | .claude | docs | mobile src |
|---|---|---|---|---|---|
| `push token` | 1 | 0 | 0 | 4 | 0 |
| `push_token` | 2 | 0 | 0 | 3 | 8 |
| `PUSH_TOKEN` | 2 | 0 | 0 | 3 | 8 |
| `push guard` | 0 | 11 | 11 | 94 | 0 |
| `git push` | 0 | 34 | 13 | 48 | 0 |
| `F212` | 0 | 0 | 0 | 15 | 0 |
| `385_the_push_tokens_own_write` | 0 | 0 | 0 | 3 | 0 |
| `the push token's own write` | 0 | 0 | 0 | 1 | 0 |
| `| 385 |` | 0 | 0 | 0 | 0 | 0 |
| `| 384 |` | 0 | 0 | 0 | 3 | 0 |
| `docs/ROADMAP.md` | 0 | 5 | 27 | 92 | 0 |
| `fleet-trial` | 0 | 0 | 0 | 0 | 0 |

The excerpts the judgement was given (`scout.candidates`): `.claude/skills/closeout/CHANGELOG.md:241`, `.claude/skills/closeout/CHANGELOG.md:251`, `.claude/skills/closeout/CHANGELOG.md:95`, `.claude/skills/closeout/SKILL.md:115`, `.claude/skills/closeout/SKILL.md:131`, `.claude/skills/closeout/SKILL.md:27`, `.claude/skills/closeout/_pre_push_guard.py:2`, `.claude/skills/closeout/_pre_push_guard.py:32`, `.claude/skills/closeout/_pre_push_guard.py:37`, `.claude/skills/closeout/_pre_push_guard.py:399`, `.claude/skills/closeout/_pre_push_guard.py:4`, `.claude/skills/closeout/fixtures/check2/good_paths.txt:3`, `.claude/skills/closeout/fixtures/roadmap_bad/ROADMAP_AUTHORITY.md:5`, `.claude/skills/closeout/fixtures/roadmap_bad/ROADMAP_AUTHORITY.md:6`, `.claude/skills/closeout/fixtures/roadmap_bad/ROADMAP_AUTHORITY.md:7`, `docs/FOLLOWUPS.md:3677`, `docs/ROADMAP.md:661`, `docs/decisions.md:30`, `docs/fleet/digests/2026-10-22.md:42`, `docs/handoffs/2026-10-21_384_closed.md:120`, `docs/handoffs/2026-10-22_386_closed.md:80`, `docs/handoffs/2026-10-22_387_closed.md:74`, `docs/phases/completed/204_phase_log.md:118`, `docs/phases/completed/261_implementation.md:215`, `docs/phases/completed/261_implementation.md:246`, `docs/phases/completed/388_phase_log.md:11`, `docs/prompts/385_the_push_tokens_own_write.txt:1`, `docs/prompts/385_the_push_tokens_own_write.txt:25`, `docs/reports/2026-10-12_plan_of_record.md:27`, `docs/reports/2026-10-22_fleet_proposal.md:23`, `src/motodiag/api/app.py:148`, `src/motodiag/api/routes/push.py:43`, `src/motodiag/api/routes/push.py:60`.

## What exists

docs/ROADMAP.md holds the rows around the gap: Phase 384 (closed), Phase 386, 387 and 388 (closed), and this branch's Phase 389A row (🚧). The census's `| 385 |` search finds nothing in docs, so the gap is real. docs/prompts/385_the_push_tokens_own_write.txt is committed, and its first line already says to add Phase 385 to the ROADMAP as 🚧. docs/FOLLOWUPS.md:3677 holds F212 (the API writes device_tokens.last_seen_at, which SERVER_WRITES does not name). docs/decisions.md:30 records K39 with "None yet", and docs/reports/2026-10-12_plan_of_record.md:27 names the same prompt. The push routes in src/motodiag/api/routes/push.py are the code Phase 385 concerns; this mission does not touch them. The `fleet-trial` marker is found nowhere in the census (no src, tests, .claude, docs or mobile hits), so no check reads it yet. The census did not search for the Captain, the Engineer, or the plan:approved label, so nothing below shows those exist beyond the Phase 388 handoff's description of the dispatcher.

## What the row promises

The mission promises three things. (1) Add a Phase 385 row to docs/ROADMAP.md, status not started, naming the prompt and F212: a reader reaches it by opening docs/ROADMAP.md, and the ROADMAP check (roadmap_check.py) holds it. (2) The dispatcher runs the mission from Step 0 to the Captain's merge recommendation: the Phase 388 handoff says the dispatcher and its label path exist on the desktop, and it is reached through a GitHub issue opened under the operator's login. The census does not confirm the Captain's stage exists on this branch; it is described as in progress here. (3) The operator merges by hand: nothing in the mission reaches the merge, so nothing in the repository does it automatically. Nothing reaches the Phase 385 work itself; the row only records that it is not started.

## Risks and stops

Status conflict, not a stop: the mission says the row is 🔲 (not started), but the Phase 385 prompt says to add it as 🚧 before Step 0. The ROADMAP status key defines 🚧 as in progress, and Phase 385 has not begun, so I recommend 🔲 and naming the conflict for the operator to see in the Captain's recommendation. Scope of F212's approval: the operator's 2026-10-21 approval covers the list change for Phase 385's own run, scoped to one column; this mission must not edit SERVER_WRITES or any file under src or tests. Any such edit is a rule-1 stop. Login: the GitHub issue and any comments run under the operator's login, pre-approved by Phase 389's scoped wording until the identity exists (F214); the trial may use it, applied literally, and no other writes go through it. Outward-facing: issue comments are public once posted, and the mission must not merge, close issues, or approve its own plan. Open issues from Phase 388 (#9 and #10) are the operator's to close. Gate risk, not a stop: whole-tree fast mode runs before the commit; if it needs Mac-only tools on the desktop, the commit blocks, which the push guard does by design (F216). Record it, never loosen the guard. The word limit on a ROADMAP row (roadmap_words.py) applies to the new row. No live change and no migration are in scope. Rule 1 stops for the row itself: None found.

## The calls

- scout: claude-haiku-5-5, session `8850ef48-4ede-4f1c-af00-1858031f51be`, input 2, cache write 0, cache read 16646, output 909, 2 turns, 5 s, $0.00 at list price (`claude -p … --output-format json`)
- scout: claude-haiku-5-5, session `03729412-88a7-4724-ae8f-09dc8637b661`, input 2, cache write 30087, cache read 3160, output 6086, 2 turns, 30 s, $0.01 at list price (`claude -p … --output-format json`)
