# Plan of record: the order from here, 2026-10-12

Written 2026-10-12 by the advisor session that verified Phases 373–381. This copy in the repository is the canonical one.

## Next, in order

The fleet reads this table exactly (`.claude/skills/fleet/plan_order.py`): the first row whose ROADMAP row is not ✅ is the next mission. A row built by a builder session is waited for. A row that needs the operator is asked first, in plain English. Otherwise the fleet opens the mission's issue and a one-row pull request that marks its row 🚧, and the operator merges it by hand (K49). The list changes only by a dated entry under "Changes to the order" with a K-id, written on the operator's word (K48).

As of 2026-10-31, K61.

| # | phase | kind | built by | needs the operator | entry |
|---|---|---|---|---|---|
| 1 | 392 | fleet | builder | nothing | 2026-10-26, later · K44 |
| 2 | 303 | shop | fleet | nothing | 2026-10-26 · K43 |
| 3 | 394 | fleet | builder | nothing | 2026-10-28 · K55 |
| 4 | 393 | fleet | builder | nothing | 2026-10-27 · K54 |
| 5 | 395 | fleet | builder | nothing | 2026-10-29 · K58 |
| 6 | 348 | shop | fleet | nothing | 2026-10-26 · K43 |
| 7 | 385 | shop | fleet | nothing | 2026-10-21 · K53 |
| 8 | 396 | fleet | builder | nothing | 2026-10-31 · K61 |
| 9 | 345 | shop | fleet | an outside account: the offsite backup's service account, which the operator opens | Wave 1, item 2 · K48 |
| 10 | 343 | shop | fleet | an outside account: crash reports (Sentry), which the operator opens | Wave 1, item 2 · K48 |
| 11 | 371 | shop | fleet | a fork: Stripe's production webhooks need an endpoint Stripe can reach, and the backend is tailnet-only (the operator's decision 3 of 2026-09-28); and an outside account, Stripe's live account ("Stripe: the live account, for 371 and 372") | Wave 1, item 4 · K48, K52 |
| 12 | 372 | shop | fleet | an outside account: Stripe's live account | Wave 1, item 4 · K48 |
| 13 | 330 | shop | fleet | a rule change: F210's general rule comes first ("F210's general rule is still needed before onboarding (330)", 2026-10-21); it changes the set-aside list's definition, which is the operator's call | Wave 1, item 5 · K48, K52 |
| 14 | 334 | shop | fleet | an outside person: a lawyer, for the terms a shop signs | Wave 1, item 5 · K48 |
| 15 | 344 | shop | fleet | nothing | Wave 1, item 5 · K48 |
| 16 | 210 | shop | fleet | nothing | Wave 1, item 6 · K48 |

The ROADMAP stays the ledger: this file records the order of the open rows, and why. A Step 0 that measures something new can change the order. Any change is recorded here, dated.

The operator's words:
- 2026-10-08: "i care about doing it in the order that makes the most sense, with context in mind feel free to adjust what that looks like"
- 2026-10-08, on the home desktop: "i previously said thats where my server would live. I think it's time . we can roll that into the plan"
- 2026-10-12: "give me the prompt to give my claude code on my windows server desktop"

## Changes to the order

- **2026-10-19: 383 goes before 345.** Phase 382 closed on 2026-10-19 and filed F205, F206 and F208. Phase 383 takes them in this order: F206, F208, then F205.
  - **F206 and F208 are the gates every later live apply rests on.** Under F206, a failing regression line passes A5 and K18. Under F208, a live the API is writing blocks apply-live and fails check 8.
  - **F205's relative media paths** are what a restore from 345's offsite backups needs.
  - **The prompt** is `docs/prompts/383_follow_ups_from_382.txt`, written at the operator's "write 383".
- **2026-10-20: 384 goes before 345.** In 384, a builder on the Mac does the PC's steps itself over the tailnet, and the operator only approves.
  - **The reason:** since 382, every deploy step runs on the PC by hand, and in 383 the operator carried each one between the two computers.
  - **The operator's words:** first "this workflow is only getting more intricate and complicated", then "cant everything i do on the mac just automatically get done on the pc?" Offered two ways, they answered "way 1".
  - **A plan to move whole phases to the PC was written first and set aside, unpublished, at the operator's word.**
  - **The prompt** is `docs/prompts/384_the_mac_runs_the_pcs_steps.txt`.
- **2026-10-21: 385 goes before 345.** It is F212, the second column the API writes by itself, `device_tokens.last_seen_at`.
  - **Why first:** every deploy's live check fails once the app re-registers for notifications, so this comes before the next phase with a deploy.
  - **The operator's words:** "add device_tokens.last_seen_at to the list as its own phase".
  - **What stays open:** F210's general rule is still needed before onboarding (330).
  - **The prompt** is `docs/prompts/385_the_push_tokens_own_write.txt`.
- **2026-10-22 to 2026-10-25: the fleet went before the first shop.** Phases 386 to 389 closed, and 390 is open, under `docs/reports/2026-10-22_fleet_proposal.md`.
  - **None of the ten first-shop rows has started:** 345, 343, 303, 348, 371, 372, 330, 334, 344 and 210.
  - **385 has no row.** It is the fleet's trial job (issue #14).
  - **The operator, 2026-10-25:** "how far are we from getting back on track. I feel sidetracked as hell getting this to work", then "yes add the line to the plan of record".
  - **When shop work resumes:** after 390 closes and the trial's last steps are done.
  - **The advisor's recommendation, for the operator to confirm:**
    - The next phase is a first-shop row, run through the fleet: staff logins with roles and the activity log (303 and 348), which need no outside account. That was the proposal's own step 6.
    - The proposal's last two steps, the Quartermaster in shadow and the end-to-end run, ride along inside those phases rather than taking phases of their own.
    - New fleet work waits, unless it blocks a first-shop phase.
- **2026-10-26: shop work comes next, after 391.** The operator's decision is K43 in `docs/decisions.md`. Asked "Want me to write that rule into the plan of record, so the fleet and every builder sees it?", they answered "yes write it into the plan". The rule they approved:
  1. **391 is the last fleet-only phase.** 391 is the Quartermaster, in shadow, already under way. It finishes.
  2. **The trial is wrapped** when its builder asks: 389A, 385's row, issue #14.
  3. **The next phase is first-shop work, run through the fleet:** staff logins with roles and the activity log (303 and 348). It is also the fleet's end-to-end run, the proposal's step 9, done on real work.
  4. **No new fleet-only phase** unless it unblocks a first-shop phase, which its row names.
  - **Where things stood:** 390 and 390A closed. None of the ten first-shop rows had started.
  - **This confirms the 2026-10-25 recommendation with one change:** the Quartermaster took a phase of its own (391), which was already under way.
- **2026-10-26, later: 392 goes between 391 and 303/348.** In 392 the fleet follows the plan of record. The operator's decision is K44.
  - **What was found:** no rank reads the plan of record or docs/decisions.md. A mission starts only when someone opens its issue by hand. The ranks trust a marker comment from any author (F223, on a public repository).
  - **The operator's words:** "well the fleet should be reading the plan of record, how tf is that missed!?", "isnt that the whole point!?", "its supposed to replace what ive been doing. so bridge that gap however it must, thats priority, so we can continue on track".
  - **What it unblocks:** 303 and 348, which its row names (K43).
  - **Its proof:** the fleet starts 303 and 348 from this plan by itself.
  - **The prompt** is `docs/prompts/392_the_fleet_follows_the_plan.txt`.
  - **F226 rides along (K45).** A finished fleet run's temporary files are deleted. That replaces the shrink the disk image no longer gives: it has not been sparse since 2026-10-26.
    - **The operator's words:** "go with your pick, delete each run's temp files".
    - **Why in 392:** 392 already changes the dispatcher.
  - **F225 and F227 ride along too (K46).** A fleet check that runs past its time limit stops and says so, instead of silently starting over. The fleet service's open-file limit is measured, then set. Either could trip 392's own proof.
    - **The operator's words:** "yes add both to 392".
    - **The two numbers are the operator's,** asked at 392's Step 0.
  - **F228 rides along too (K47).** A Red Team round that leaves a small wording issue open always stops, because nothing tells the rank that the issue needs a finding number, and it cannot file one. #14 stopped on it and is parked until 392 merges. Then its label is re-applied once, and that run is the fix's proof.
    - **The operator's words:** "yes go ahead".
- **2026-10-27: the order is a list the fleet reads exactly (K48).** At 392's Step 0 the operator answered: "The plan of record stays the single source; add a short "Next, in order" list at its top that the fleet reads exactly; it changes only by a dated entry with a K-id, written on my word."
  - **The list is "Next, in order", at the top of this file.** It transcribes the order already here: 392, then 303 and 348 (K43), then Wave 1's own numbering. No row's place changed.
  - **303 and 348 are two missions, 303 first.** The ledger has two rows and a mission is one row; 348's log records which staff login did what, which 303 makes (392's Step 0, S0-5).
  - **What each row needs from the operator** is taken from Wave 1 and "The operator's steps outside the code" below.
  - **How a row reaches master (K49):** "The fleet opens a one-row PR (the 🚧 row and the issue) and I merge it by hand; the fleet never pushes to master."
  - **Corrected the same day, before the list merged (K52),** from the advisor at the operator's word: row 6 (371) needs Stripe's live account as well as the webhook fork; row 8 (330) needs F210's general rule first, which changes the set-aside list's definition, the operator's call. The list's needs gained "a rule change" for that.
- **2026-10-27: 385 joins the list, before 345 (K53).** The 2026-10-21 entry above put "385 goes before 345", but 385 had no row, so K48's transcription left it out.
  - **The operator's words:** "PR #15 closed under K9; put 385's row on master and 385 before 345 in Next, in order, as the 2026-10-21 entry says."
  - **Its row** is on master now, 🔲, with the text from PR #15 (389A, the trial).
  - **It needs nothing from the operator:** its prompt, `docs/prompts/385_the_push_tokens_own_write.txt`, expects no migration and no change to live, and names no outside account or rule change beyond the one column the operator already approved (K39).
- **2026-10-27: 393 goes after 303 and before 348 (K54).** Nothing checks how the code itself is written: the linter is configured and never run, the type hints are never checked, and coverage is never measured.
  - **The operator's words:** "Approved: Phase 393 as drafted, after 303 and before 348, built by a builder session; its numbers are mine."
  - **It is built by a builder session, and the fleet waits for it:** it changes `.claude/skills/fleet/`, which the push gate keeps from the fleet. 348 and every first-shop phase after it are built under its checks.
  - **Its prompt** is `docs/prompts/393_the_code_itself_gets_checked.txt`, and its row is on master, 🔲. The numbers in it (85% changed-line coverage, McCabe 20, 100 KB per file, the ratchet) are the operator's.
- **2026-10-28: 394 goes right after 303 (K55).** PR #34, 303's build, made the Red Team's brief larger than Linux's 128 KiB limit on a single command-line argument. The brief went on the command line, so the Red Team's stage could not start: the dispatcher's log says "cycle failed" every 5 minutes from 16:38, and each retry said "Red Team started" again on #31.
  - **The operator's words:** "New small phase, on my word: the fleet passes a rank's brief on standard input. Next free ROADMAP number, row 🚧 first, kind fleet, built by a builder; its row names 303 as what it unblocks (K43 rule 4); add it to "Next, in order" right after 303 with a dated entry and the next K-id (yeoman.py decide)".
  - **It unblocks 303,** whose Red Team cannot run without it. #31 is held with `needs-admiral` until it merges.
  - **It is built by a builder session, and the fleet waits for it:** it changes `.claude/skills/fleet/`, which the push gate keeps from the fleet.
  - **Its prompt** is `docs/prompts/394_the_brief_on_stdin.txt`, and its row is 🚧.
- **2026-10-29: 395 goes after 393 and before 348 (K58).** 348, the audit log, needs a new table: its Step 0 (`abbafd4`, on its branch) finds no event store to extend. A phase with a migration has no path through the fleet (F232): the Engineer cannot dry-run, apply live or pause between the regression and the close-out. 303 avoided a migration by keeping its sessions in the API-key table.
  - **The operator's words:** "add it altogether to throw at it", then "yes go ahead" to the advisor's reading of it: a builder session gives the fleet the database step, then the fleet builds all of 348, its new table included.
  - **It unblocks 348** (K43 rule 4), and every later first-shop phase with a migration. The fleet had already opened 348 by itself (#36; its row PR merged at 20:05). #36 is held with `needs-admiral` from 20:24 until 395 merges and the fleet runs its code. 348's Step 0 and the Captain's v1.0 stay on its branch.
  - **It is built by a builder session, and the fleet waits for it:** it changes `.claude/skills/fleet/`, which the push gate keeps from the fleet.
  - **Its prompt** is `docs/prompts/395_the_database_step.txt`, and its row is on master, 🔲.
- **2026-10-31: 396 goes after 385 and before 345 (K61).** The fleet got four things wrong on 348 and 385, measured on the real phases: the Quartermaster's fenced code check (Q10, Q12) gave no result on PR #40 and PR #43; the close-out wrote "No refute pass ran" while its own log recorded the Red Team's rounds (303, 348, 385); the dispatcher opened duplicate issue #44 for 385 from an order read before a 53-minute stage, during which 385 merged; and 348's Red Team was handed the Captain's first draft as "the approved v1.0".
  - **The operator's words:** "fix the four things the fleet got wrong on 348 and 385 before the next phase."
  - **It unblocks 345** (K43 rule 4), and every first-shop phase after it, whose Quartermaster verdicts are not trustworthy until the code check runs in the fence.
  - **It is built by a builder session, and the fleet waits for it:** it changes `.claude/skills/fleet/`, which the push gate keeps from the fleet.
  - **Its prompt** is `docs/prompts/396_the_fleets_four_slips.txt`, and its row is on master, 🔲.

## Where the ledger stands

On `master` at `60bb480`, rows numbered 100 and up, counted by their status cell (`grep -c -E '^\| *[0-9]{3}[A-Z]? .*\| *<status> *\|' docs/ROADMAP.md`):

| Status | Rows |
|---|---|
| ✅ | 222 |
| 🔲 | 61 |
| ⏸️ | 17 |
| 🚧 | 0 |

Track O is complete. Phases 373–381 closed between 2026-10-06 and 2026-10-09.

## The principle

The first real shop, in Massachusetts, comes first, and safely. That means:
- an always-on server;
- backups that leave the building, and crash reports;
- a record of who did what;
- payments;
- the terms a shop signs.

Reference data and the AI work come after a shop is using the product. The second shop comes after the first.

## Wave 1: the first shop, safely

1. **382, live and the backend on the home desktop.**
   - It comes first because everything else in this wave attaches to wherever the server runs, and the Mac sleeps. It hibernated mid-phase on 2026-10-08.
   - Prompts: `docs/prompts/382_desktop_setup.txt` (part 1, the machine) and `docs/prompts/382_live_on_the_home_desktop.txt` (part 2, the move).
2. **345, Cloud backup + sync; 343, Telemetry + crash reporting (Sentry).** Both need the host settled, and each needs a service account the operator opens.
3. **303, Multi-user auth with roles; 348, Audit log (who did what, when).**
   - Role code exists in `src/motodiag/auth/`.
   - A shop's staff need their own logins, and a record of who changed what.
   - Neither depends on the host, so a Mac builder can run them.
4. **371, Live Stripe payments and production webhooks; 372, Payment API routes and the app's payment screens.** Both are ⏸️.
   - Row 371 records why it waits: Stripe's production webhooks need an endpoint Stripe can reach, and the operator's decision 3 of 2026-09-28 keeps the backend tailnet-only. That is the operator's call, at 371's Step 0.
   - F185 goes with them: a tax-exempt sale cannot be invoiced once the tax comes only from the shop's record.
5. **330, Onboarding wizard for new shops; 334, Terms of Service + liability framework; 344, In-app support channel.**
6. **210, Launch readiness + full integration.**

## Wave 2: reference data and the shop floor

- Track P, the Reference Data Library (293–302), with the open sourcing findings.
- 305 Print + label support, 306 Barcode / QR scanning, 307 Photo annotation.

## Wave 3: the second shop

Whatever the first shop's use shows, before a second one starts.

## Wave 4: Track R, Advanced AI Capabilities (318–327)

## Wave 5: the rest

The remaining rows of Tracks Q, S and T.

## Open findings

A finding joins the wave whose code it touches.
- **F204** is the nearest: the prompt's safety floor and row 231's scope, a consequence of 381.
- **F202 and F203** are wording passes like 381's.

## The operator's steps outside the code

- **Stripe:** the live account, for 371 and 372.
- **A lawyer,** for 334's terms.
- **The shop's accountant** confirms the Massachusetts warranty readings (373–375) before a real warranty job.
- **Accounts** for offsite backup (345) and crash reports (343).
- **K11:** decide the Subconscious plan before it cancels on 2026-10-23.
