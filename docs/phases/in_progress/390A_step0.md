# Phase 390A — Step 0: Phase 390A: the Quartermaster's ROADMAP row (the Science Officer's proof)

**Written 2026-10-25** by the Science Officer (`scout.py`, Haiku), from
mission issue #16, on this branch from `master` at `9f0bd7b`. The
counts are the script's; the judgement below them is the model's.

Classification: **greenfield.** Nothing of the Quartermaster exists in code. Its name appears only in the fleet's routing table in `.claude/skills/fleet/dispatcher.py` and in label text in `.claude/skills/fleet/labels.py`, and the dispatcher's own entry says the Quartermaster is not built yet. The mission is a docs-only ledger row, so it changes no existing behaviour.

## The overlap census

The census, no model: each count is `git grep -c -i -F -e <term> -- <area>` summed over files, run on this branch's clone (the mobile repository's from `git -C ../moto-diag-mobile grep … -- src`).

| term | src | tests | .claude | docs | mobile src |
|---|---|---|---|---|---|
| `Quartermaster` | 0 | 0 | 2 | 25 | 0 |
| `fleet_proposal` | 0 | 0 | 4 | 16 | 0 |
| `ROADMAP.md` | 0 | 14 | 39 | 109 | 0 |
| `ROADMAP_AUTHORITY` | 0 | 3 | 10 | 34 | 0 |
| `390A` | 0 | 0 | 0 | 1 | 0 |
| `391` | 1 | 0 | 0 | 20 | 2 |
| `in shadow` | 1 | 3 | 0 | 5 | 0 |
| `fleet-trial` | 0 | 1 | 2 | 1 | 0 |
| `restart` | 56 | 10 | 9 | 223 | 4 |
| `resume` | 41 | 29 | 64 | 141 | 8 |
| `Yeoman` | 0 | 28 | 19 | 53 | 0 |
| `🔲` | 0 | 4 | 8 | 91 | 0 |

The excerpts the judgement was given (`scout.candidates`): `.claude/skills/closeout/_pre_push_guard.py:399`, `.claude/skills/closeout/closeout_check.py:268`, `.claude/skills/closeout/fixtures/check2/good_paths.txt:3`, `.claude/skills/closeout/fixtures/roadmap_bad/ROADMAP_AUTHORITY.md:5`, `.claude/skills/closeout/fixtures/roadmap_bad/ROADMAP_AUTHORITY.md:6`, `.claude/skills/closeout/fixtures/roadmap_bad/docs/ROADMAP.md:10`, `.claude/skills/closeout/roadmap_check.py:12`, `.claude/skills/closeout/roadmap_check.py:14`, `.claude/skills/closeout/roadmap_check.py:159`, `.claude/skills/closeout/roadmap_check.py:9`, `.claude/skills/deploy/CHANGELOG.md:104`, `.claude/skills/fleet/CHANGELOG.md:33`, `.claude/skills/fleet/CHANGELOG.md:5`, `.claude/skills/fleet/CHANGELOG.md:60`, `.claude/skills/fleet/SKILL.md:17`, `.claude/skills/fleet/SKILL.md:262`, `.claude/skills/fleet/dispatcher.py:114`, `.claude/skills/fleet/fleet_git.py:46`, `.claude/skills/fleet/labels.py:30`, `docs/ROADMAP.md:662`, `docs/ROADMAP.md:667`, `docs/ROADMAP.md:668`, `docs/handoffs/2026-10-25_389_closed.md:114`, `docs/phases/completed/134_phase_log.md:9`, `docs/phases/completed/256_predictions_after.json:2872`, `docs/phases/completed/256_predictions_before.json:2917`, `docs/phases/completed/257_phase_log.md:2763`, `docs/phases/completed/262_implementation.md:344`, `docs/phases/completed/389_implementation.md:96`, `docs/phases/completed/TRACK_K_AUDIT_VERIFIER_NOTES.md:1197`, `docs/phases/completed/TRACK_K_AUDIT_VERIFIER_NOTES.md:1231`, `docs/reports/2026-10-22_fleet_proposal.md:222`, `tests/test_phase389_scout.py:33`.

## What exists

`.claude/skills/fleet/dispatcher.py` names the Quartermaster in its merge routing, with the note that it is not built yet. `.claude/skills/fleet/labels.py` carries a label described as waiting for the Quartermaster's checks and merge. `docs/reports/2026-10-22_fleet_proposal.md` describes the Quartermaster as its step 8, in shadow. `docs/ROADMAP.md` has the rows up to Phase 390A, and the excerpts show no row for Phase 391. The `391` hit in `src` was not in the excerpts, so it was not read and needs checking before the row is written.

## What the row promises

Phase 391's row promises a Quartermaster that runs `verify_phase.sh`, writes its merge verdict to the digest while the operator still merges, refuses a planted bad PR, and, once promoted, merges and closes the mission issue. Nothing reaches any of this yet. The row itself is status 🔲, so the only way to reach it is to read `docs/ROADMAP.md`. The reach for each verb belongs to the later phase that builds it, not to this docs row.

## Risks and stops

None found for the operator's reserved stops: this is an ordinary docs row with the next free number, it changes no threshold or rule definition, and it needs no login beyond the planted-trial identity already granted by Phase 390's pre-approval. Watch items: check the `src` hit for `391` before writing the row; keep the row under the ROADMAP word cap; and do not add documents or an in-progress status, so the status check stays consistent.

## The calls

- scout: claude-haiku-5-5, session `c0e71e03-445f-4fa1-b586-fd4a501f4d50`, input 2, cache write 16677, cache read 0, output 1064, 2 turns, 6 s, $0.00 at list price (`claude -p … --output-format json`)
- scout: claude-haiku-5-5, session `99b6d566-c5ea-4686-b990-4dae1efa9985`, input 4, cache write 37457, cache read 34501, output 4183, 3 turns, 21 s, $0.01 at list price (`claude -p … --output-format json`)
