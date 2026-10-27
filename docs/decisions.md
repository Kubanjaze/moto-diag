# Decisions — the operator's words, by K-id

One line per decision: the K-id, the date, the operator's words verbatim,
and the check it became. A decision that became a document and no check
says so; none is invented.

K-ids are one sequence. K1–K31 are recorded in
`docs/reports/2026-09-27_process_kinks_triage.md` and
`docs/reports/2026-10-07_process_kinks_triage.md`. This file starts at K32,
seeded in Phase 386 (2026-10-22) from the operator's quoted words in
`docs/reports/2026-10-12_plan_of_record.md`, one line per quotation. A
quotation's date is the one the plan of record gives it, or the date of
the change it is quoted under.

Since Phase 387, rows are added with
`.claude/skills/fleet/yeoman.py decide`, which takes the next K-id and
refuses a row citing a K-id that does not resolve (in the two triage
reports or in this file). Nothing yet checks K-ids cited elsewhere, in
phase documents or handoffs, the way `finding_check` B2 checks F-numbers.

| K-id | Date | The operator's words | The check it became |
|---|---|---|---|
| K32 | 2026-10-08 | "i care about doing it in the order that makes the most sense, with context in mind feel free to adjust what that looks like" | No check. The order is `docs/reports/2026-10-12_plan_of_record.md`, whose changes are dated there. |
| K33 | 2026-10-08 | "i previously said thats where my server would live. I think it's time . we can roll that into the plan" | Phase 382: live on the home desktop. Each machine's `~/.config/motodiag/live.json` says where live is, and every tool that reads live refuses (exit 4) on a machine that does not hold it: `tests/test_phase382_live_location.py`. |
| K34 | 2026-10-12 | "give me the prompt to give my claude code on my windows server desktop" | No check. The prompts are `docs/prompts/382_desktop_setup.txt` and `docs/prompts/382_live_on_the_home_desktop.txt`. |
| K35 | 2026-10-19 | "write 383" | No check. The prompt is `docs/prompts/383_follow_ups_from_382.txt`. |
| K36 | 2026-10-20 | "this workflow is only getting more intricate and complicated" | No check by itself; it led to K37 and Phase 384. |
| K37 | 2026-10-20 | "cant everything i do on the mac just automatically get done on the pc?" | Phase 384: the Mac runs the desktop's deploy steps through a fixed list over the tailnet: `tests/test_phase384_remote_dispatcher.py`, `tests/test_phase384_remote_client.py`, `tests/test_phase384_install_remote.py`. |
| K38 | 2026-10-20 | "way 1" | The same as K37: 384's way 1, a builder on the Mac doing the desktop's steps, the operator only approving. |
| K39 | 2026-10-21 | "add device_tokens.last_seen_at to the list as its own phase" | None yet: Phase 385, prompt `docs/prompts/385_the_push_tokens_own_write.txt`, not built. |
| K40 | 2026-10-22 | "The labels on GitHub, created with gh from this Mac under my login, since no rank pushes code yet" | The eleven labels made by `.claude/skills/fleet/labels.py` under the operator's own gh login, a stand-in until the identity phase (F214); `tests/test_phase387_fleet_contract.py` holds the names and that an existing label is never overwritten. |
| K41 | 2026-10-22 | "Pin them (Recommended)" | `.claude/skills/fleet/plan_check.py`'s WRITTEN_BEFORE: 384 and 386's v1.0 are not held to the classification, change-log and stop items they predate; `tests/test_phase387_fleet_contract.py` holds the pin to equality. |
| K42 | 2026-10-25 | "K11, 2026-10-25: I let Subconscious lapse. The Science Officer runs on Haiku through --source-route anthropic until the 600-machine sourcing backlog is scheduled; re-subscribe the week it is." | Answers K11 (the Subconscious plan). No check yet: CLAUDE.md rule 2 already names `--source-route anthropic` as the fallback while Subconscious is down; the Science Officer (Haiku) is built in Phase 389, and the re-subscription is the operator's, the week the 600-machine sourcing backlog is scheduled. |
| K43 | 2026-10-26 | "yes write it into the plan" | No check. docs/reports/2026-10-12_plan_of_record.md, 2026-10-26: 391 is the last fleet-only phase; after it and the trial (389A, issue #14), the next phase is first-shop work through the fleet, 303 and 348, as the fleet's end-to-end run; a later fleet-only phase must name the first-shop phase it unblocks. |
| K44 | 2026-10-26 | "its supposed to replace what ive been doing. so bridge that gap however it must, thats priority, so we can continue on track" | None yet: Phase 392, prompt docs/prompts/392_the_fleet_follows_the_plan.txt (every planning rank reads the plan of record and docs/decisions.md and cites them; a plan_check item holds it; the next mission comes from the plan; F223); the plan of record's 2026-10-26 entry puts it between 391 and 303/348. |
