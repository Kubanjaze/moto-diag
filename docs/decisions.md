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

Nothing checks yet that a cited K-id resolves here; the fleet proposal
plans that for the step that adds the Yeoman.

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
