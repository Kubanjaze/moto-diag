# Plan of record: the order from here, 2026-10-12

Written 2026-10-12 by the advisor session that verified Phases 373–381. This copy in the repository is the canonical one.

## Next, in order

The fleet reads this table exactly (`.claude/skills/fleet/plan_order.py`): the first row whose ROADMAP row is not ✅ is the next mission. A row built by a builder session is waited for. A row that needs the operator is asked first, in plain English. Otherwise the fleet opens the mission's issue and a one-row pull request that marks its row 🚧, and the operator merges it by hand (K49). The list changes only by a dated entry under "Changes to the order" with a K-id, written on the operator's word (K48).

As of 2026-11-27, K153.

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
| 10 | 397 | fleet | builder | nothing | 2026-10-31, later · K63 |
| 11 | 343 | shop | fleet | an outside account: crash reports (Sentry), which the operator opens | Wave 1, item 2 · K48 |
| 12 | 398 | fleet | builder | nothing | 2026-11-05 · K67 |
| 13 | 371 | shop | fleet | a fork: Stripe's production webhooks need an endpoint Stripe can reach, and the backend is tailnet-only (the operator's decision 3 of 2026-09-28); and an outside account, Stripe's live account ("Stripe: the live account, for 371 and 372") | Wave 1, item 4 · K48, K52 |
| 14 | 372 | shop | fleet | an outside account: Stripe's live account | Wave 1, item 4 · K48 |
| 15 | 403 | fleet | builder | nothing | 2026-11-15 · K84 |
| 16 | 404 | shop | fleet | nothing | 2026-11-15 · K84 |
| 17 | 334 | shop | fleet | nothing | Wave 1, item 5 · K48, K84 |
| 18 | 405 | shop | fleet | nothing | 2026-11-19 · K91 |
| 19 | 330 | shop | fleet | a rule change: F210's general rule comes first ("F210's general rule is still needed before onboarding (330)", 2026-10-21); it changes the set-aside list's definition, which is the operator's call | Wave 1, item 5 · K48, K52 |
| 20 | 293 | shop | fleet | a rule change: the operator decided on 2026-11-21 what each plan may store in manuals (Individual 2 GB, Shop 20 GB, Company 50 GB shared by its shops, at most 300 MB a file) and that every upload is checked by the server, then approved by a person at Mekno before anyone can open it, with the terms saying so; and on 2026-11-22 the other three: manual files go in the nightly backup, the upload terms ship before a lawyer's read, and a limit counts only the files a shop uploads | 2026-11-20 · K94, K119, K121, K122, K123 |
| 21 | 303B | shop | builder | nothing | 2026-11-20, evening, later · K99 |
| 22 | 334B | shop | builder | nothing | 2026-11-20, evening · K98 |
| 23 | 372B | shop | builder | nothing | 2026-11-20, evening · K98 |
| 24 | 210 | shop | fleet | nothing | Wave 1, item 6 · K48 |
| 25 | 409 | shop | builder | a fork: how the internet reaches the server (a tunnel, a rented server in front, or another way; the record's rule is never the LAN and never Funnel, unless the operator asks) and its name; and an outside account for the way in and for the name's DNS | 2026-11-25 · K140, K137; 2026-11-26 · K149 |
| 26 | 329 | shop | builder | a fork: K101 keeps the support email for the first 10 shops and sign-ups off the Mekno server, where self-serve sign-up has to make the account; and where the sign-up form lives; and an outside account: the email service that sends the address check and the password reset | 2026-11-25 · K140, K137, K101; 2026-11-27 · K152, K153 |
| 27 | 410 | shop | builder | an outside account: Apple's developer account and App Store Connect, the operator's own (K136); and a fork: the review account, and how Mekno answers Apple's rules on deleting an account in the app and on plans bought outside it | 2026-11-25 · K140, K137, K136 |
| 28 | 344 | shop | fleet | nothing | Wave 1, item 5 · K48, K128 |

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
- **2026-10-31, later: 397 goes after 345 and before 343 (K63).** The independent check of master on the Mac (`docs/reports/2026-10-31_independent_check.md`) failed one test of 12,184 in its full parallel run at `ce97159`: `tests/test_phase392_check_limit.py::test_run_group_kills_the_whole_group_and_says_what_it_printed`, which gives its planted command one second to print (F241). The same test's `alive()` reads `/proc`, which macOS does not have, so on the Mac its check that the planted command's child was killed passes whether or not it was.
  - **The operator's words:** "give me the prompt for the builder chat to fix that test".
  - **It unblocks a clean full run on the Mac** (K43 rule 4): the independent check that follows 345, and every first-shop phase after it. A failed run is not of record.
  - **It is built by a builder session, and the fleet waits for it.** 345 stays ahead of it: the fleet's Chief Engineer is building 345 in the fence, and 397 leaves it alone.
  - **Its prompt** is `docs/prompts/397_the_one_second_window.txt`, and its row is on master, 🔲.
- **2026-11-05: 398 goes after 343 and before 371 (K67).** The two stalls in F251 and F252 held 345 for 2 h 8 min and 343 for 9 h 13 min, each needing a hand push, and 371 would meet both at its Red Team stage.
  - **The operator's words:** "yes, fix the two stalls now as phase 398".
  - **It unblocks 371** (K43 rule 4).
  - **It is built by a builder session, and the fleet waits for it.** It changes `.claude/skills/closeout/` and `.claude/skills/fleet/`, which the push gate keeps from the fleet.
  - **371 stays held until it is in.** 371's fork is answered (K65) and it may start before the live account (K66), but the hold on issue #54 stays on until 398 is merged and the fleet's copy has moved. Taking it off is the operator's step.
  - **Its prompt** is `docs/prompts/398_the_two_stalls.txt`, and its row is on master, 🔲.
- **2026-11-07: the cost ledger (399) and the Bosun watching only (400) run beside this list, not in it (K69).** Neither unblocks a first-shop phase, so each goes ahead only by the operator's exception to K43.
  - **The operator's words:** "the cost ledger and Bosun’s watch-only phase may go ahead as fleet-only phases, one at a time while a shop phase runs; anything after comes back to me".
  - **For these two only.** K43 holds for every later fleet-only phase: a board, earlier document checks, hooks and anything else come back to the operator one at a time.
  - **Built by builder sessions, one at a time, while a shop phase from this list runs.** Both change `.claude/skills/fleet/`, which the push gate keeps from the fleet. If shop work stalls, they stop too.
  - **Not in the list, so the fleet never waits for them.** A builder's row in the list is waited for; these run beside the shop phase instead. 399 starts once the next shop phase has started, and 400 after 399 closes.
  - **Prompts:** `docs/prompts/399_the_cost_ledger.txt`; 400's is written after 399 closes. Rows 399 and 400 are on master, 🔲. The rank's name is K68's.
- **2026-11-15: 403, 404 and 334 go after 372 and before 330 (K84).** Phase 372 lost more than two days to stops that left its commits behind and to two refreshes of the phone app's copy by hand (F266, F231, F276). The pricing report asks for its step 2 before the first shop pays (F270, F271, F272, F274). And Mekno shows a user no terms yet.
  - **The operator's words:** "yes go with templates, and approve both drafts".
  - **403, the fleet's stops, unblocks 404, 334 and 330** (K43 rule 4), and every later shop phase that changes what the server tells the phone app. It is a fleet-only phase, which K69 says comes back to the operator: K84 is that answer. It is built by a builder session, and the fleet waits for it: it changes `.claude/skills/fleet/`, which the push gate keeps from the fleet. 400, the Bosun, stays as K69 sets it and is not built while 403 is.
  - **404, what the plans limit, is built by the fleet.** Its four plan decisions, and that they change limits, are in K84 and in its prompt.
  - **334 needs no outside person now.** Its terms and privacy policy come from templates, and a lawyer's review comes later, as a new version. It goes before 330, so that 330's onboarding can include the step.
  - **Prompts:** `docs/prompts/403_the_fleets_stops.txt`, `docs/prompts/404_the_plans_limits_and_the_feed_status.txt` and `docs/prompts/334_the_terms_from_templates.txt`. Rows 403 and 404 are on master, 🔲, and row 334 says templates.
- **2026-11-19: 405 goes after 334 and before 330 (K91).** The deploy check asks whether the change did what was approved, not whether live stood still since the backup. Then the payments feed's writes (F259), and later a shop's own (F210), stop refusing database steps and failing the checks after them.
  - **Why now:** 404's first database step refused on the feed's writes, and every check after it failed once the feed ran again (`docs/handoffs/2026-11-18_404_closed.md`, "After the merge"). 334 adds a table through a database step too.
  - **The operator's words:** "C as recommended, with 334's database step done the 404 way. Add C's row right after 334 so the fleet opens it when 334 merges."
  - **Until 405 lands,** 334's database step stops the payments feed from before the dry run until the dispatcher's own check has passed, as 404's did.
  - **330 keeps its need as written:** F210's general rule comes first, and 405 is that rule.
  - **The prompt** is `docs/prompts/405_the_deploy_check_asks_what_the_change_did.txt`. Row 405 is on master, 🔲.
- **2026-11-19, later: 406 runs beside this list, not in it (K93).** The Mac reaches the rest of the home desktop's steps through 384's fixed list, so the operator need not be at both computers.
  - **The operator's words:** "Yes. Set it up as phase 406 and build it on the Mac now, alongside 334."
  - **Built by the advisor session on the Mac,** as a pull request the operator merges after review. The fleet does not wait for it, and it does not wait for the fleet.
  - **The order does not change:** after 334 comes 405, then 330.
  - **The prompt** is `docs/prompts/406_the_mac_runs_the_rest.txt`. Row 406 is on master, 🚧.
- **2026-11-20: 293, the shop manual library, goes after 330 (K94).** A shop uploads the PDF manuals it owns, private to that shop, and the app finds the page for the bike, searches it, zooms it and keeps it offline. Licensed diagrams come later, into the same screens.
  - **Why:** the brief of 2026-11-20 (`docs/reports/2026-11-20_manuals_and_parts_breakdowns_brief.md`) found that the diagrams shops want are publishers' licensed data with no price yet, and that a library of a shop's own manuals needs no licence and is the screen licensed data would plug into.
  - **The operator's words:** "Decision: build the shop manual library (shops upload their own PDF manuals, per-shop, pages by bike, search, zoom, offline) as planned row 293, after 330. Licensed diagrams come later into the same screens. Priority is getting to market: 405, then 330, then 293."
  - **293 comes straight after 330,** so 344 and 210 move down one place, to 21 and 22. Row 293 is reshaped from "Factory service manual references"; the rest of Track P stays in Wave 2.
  - **What 293 needs from the operator,** asked before it starts: what each plan may store in manuals, and the terms' clause on uploads.
  - **No prompt yet:** one is written before 330 closes, from the brief's plan outline. Row 293 is on master, 🔲.
- **2026-11-20, later: 407 runs beside this list, not in it (K96).** When the fleet's first step calls a phase a reshape, the dispatcher asks the operator at once and labels the issue `needs-admiral`, instead of two plan-writer calls and a stop with no label (F285).
  - **The operator's words:** "do that and let me know where issues stand", answering the advisor's proposal.
  - **Built by the advisor session on the Mac,** as a pull request the operator merges after review, as 406 was. The fleet does not wait for it, and it does not wait for the fleet.
  - **The order does not change:** after 405 comes 330, then 293.
  - **The prompt** is `docs/prompts/407_the_operators_decision_asked_first.txt`. Row 407 is on master, 🚧.
- **2026-11-20, evening: 334B and 372B, the app's terms and payment screens, join the list before 210 (K98).** Without them a shop cannot accept the terms or take card payments in the app. They were split from 334 and 372 into rows of their own (K84, K81) and were on no list.
  - **The operator's words:** "yes add both app screens to the list", answering the advisor's proposal that they be built in a session on the app's repository while the fleet works through the server-side phases.
  - **Built by a builder session on the app's repository** (moto-diag-mobile), so the fleet waits for them only when it reaches them, after 344 and before 210. Meanwhile it goes on through 405, 330, 293 and 344.
  - **210 moves down two places, to 24.**
  - **The prompts were written when the rows were split:** `docs/prompts/334B_the_apps_terms_screen.txt` and `docs/prompts/372_the_apps_payment_screens.txt`. Each is read again against master before its session starts. Rows 334B and 372B are on master, 🔲.
- **2026-11-20, evening, later: 303B, the app's staff sign-in screen, joins the list first of the app's three screens (K99).** The server has had staff logins since 303, but the app's only way in is a pasted API key, so each staff member needs a key made by hand.
  - **The operator's words:** "yes add the staff sign-in screen to the list too", answering the advisor's question after 334B's prompt was checked against the app's code.
  - **Built by a builder session on the app's repository** (moto-diag-mobile), like 334B and 372B. It comes first of the three: the terms screen follows signing in, and the payment screens need a signed-in member.
  - **334B, 372B and 210 move down one place,** to 23, 24 and 25.
  - **The prompt** is `docs/prompts/303B_the_apps_staff_sign_in_screen.txt`, written the same evening against both repositories' code. Row 303B is on master, 🔲.
- **2026-11-21: 408 runs beside this list, not in it (K109, K117, K118).** getmekno.com's basics and trust, with the terms and privacy 1.0 published, from the marketing thread's phase request; the operator answered its questions in K114.
  - **The operator's words:** "build 408 on the Mac" (K117), undone the same day: "Undo K117 so the record says the thread built 408" (K118).
  - **Built by the home desktop's main-chat thread,** on `phase-408-thread-build`, with the operator's approved wording, founder block and photo, as a pull request the operator merges. The advisor's branch stops at `6c52577`. The fleet does not wait for 408, and 408 does not wait for the fleet.
  - **The order does not change:** 330 is in progress (K116), then 293.
  - **The prompt** is `docs/prompts/408_the_sites_basics_and_trust.txt`. Row 408 is on master, 🚧.
- **2026-11-21, later: 293's storage limits and its upload review are decided (K119).** They are the two things this plan said 293 needs from the operator before it starts: what each plan may store in manuals, and the terms' clause on uploads.
  - **The operator's words:** "Review PR 83 on moto-diag: the manual storage limits and the upload-review rule for row 293 (Individual 2 GB, Shop 20 GB, Company 50 GB shared, 300 MB per file; every upload gets a server check, then a person at Mekno approves it before anyone can open it, and the terms say so, so the review step ships in the same release as uploads). It is a document only. If it is sound, merge it and record the limits and the review rule as my decision."
  - **The draft** is `docs/reports/2026-11-21_293_storage_and_uploads_draft.md`, merged as pull request 83 (fad7927) after the advisor's review. Its limits replace the brief's examples of 500 MB and 10 GB.
  - **Three more are the operator's, best answered when 293 starts** (#20 says so):
    - where manual files are backed up: the brief put them in the nightly backup, and the draft recommends a weekly backup of their own, once Step 0 has measured the home desktop's free disk;
    - whether the terms wait for a lawyer's read: the draft sends its wording to one, and `docs/legal/README.md` says only that a lawyer's review comes later;
    - whether a limit counts only the files a shop sends, or also the page images made from them: the draft's "about 10 manuals" in 2 GB counts both.
  - **For 293's plan, from the advisor's review:**
    - The reviewer is the first account that can open any shop's files. Every role on the server is a shop's own (`src/motodiag/auth/models.py`) and none is Mekno's staff, so 293 adds one, with a test that no one else can open a file waiting for review.
    - A new version of the terms asks every user to accept it before anything else: while the terms are required, a user who has not accepted the current version can only read and accept them, see who they are, or sign out (`src/motodiag/auth/terms_acceptance.py`). Asking only on the manuals screens, as the draft suggests, would be new code.
    - The privacy policy needs more than the draft's one sentence. Its list of what is kept names photos, videos and voice notes, not manuals; its Backblaze line says every upload is copied each night, which changes if manuals get a weekly backup; and the sentence's "looks at it once" is not quite right, since a flagged file goes back to the reviewer.
    - A company's shops are not linked in the data (Company's three locations are only shown, since 404), so until they are, a Company account's 50 GB is one shop's.
  - **The order does not change:** 330 is in progress (K116), then 293. #20 still asks the operator before 293 starts: a limit is a threshold, a rule-1 stop, which the record never answers (K50).
  - **The prompt,** written before 330 closes, carries K119 and the draft, and for Step 0's log one guard block met in this review: the edit guard refused a redirect to a file path held in a variable, and the command was run again with the path written out.
- **2026-11-22: 293's last three questions are answered, and its prompt is written (K121, K122, K123).** The order does not change: 330 is finished, and 293 is next.
  - **The operator's words:** "Manual files go in the nightly backup (345), no separate weekly one." (K121) "Upload terms ship now as a version; a lawyer's read becomes a later version, as K84 did." (K122) "The storage limit counts the uploaded files only, not the page images made from them." (K123) They came with "Decisions for 293, record them in decisions.md and write 293's prompt in docs/prompts/ from the brief's section 4, K119 and your four storage notes".
  - **What they settle:**
    - the draft's weekly backup is not used, so the privacy policy's Backblaze line ("every upload, each night") stays true;
    - the upload clause ships in 293 as the next version of the terms, and a lawyer's read becomes a later one, as K84 did for 334;
    - a plan's manual storage is the bytes of the files a shop sends.
  - **The prompt** is `docs/prompts/293_shop_manual_library.txt`. It is written from the brief's section 4, K119, the draft, K121 to K123 and the advisor's four notes above, and it carries the guard block for Step 0's log. The plan writer reads it from the phase's branch.
  - **Row 293** is on master, 🔲, and #20 still asks the operator: the operator takes `needs-admiral` off issue 86 once the prompt is on master.
  - **Decided the same day, outside the order:**
    - the test shop on live is marked inactive, not deleted, as a live step of its own, not yet run (K124);
    - no app screen for onboarding (K125);
    - a bike two shops share is linked to the second shop's customer too (K126, F291);
    - the coverage pin goes to 88.0 (K127).
- **2026-11-22, later: the advisor's recommendations from the day's status are taken (K128), and 344 moves after 210.**
  - **The operator's words:** "im taking all your recommendations, log it all, prompt me when its time to continue and you give me the next prompt for main", after the advisor's read-only status of what is left before launch (the first paying shop using the app day to day).
  - **293 is an extension, built by the fleet.** A new version of the terms is accepted by everyone through the sign-in gate as it is (`src/motodiag/auth/deps.py`), not on the manuals screens only. This answers the fleet's question on issue 86, and 293's Step 0 report carries it beside its Classification line.
  - **344, the in-app support channel, waits until after launch.** It moves from #21 to #25, after 210: the support email covers the first shops (K101). 303B, 334B, 372B and 210 move up one place.
  - **334B, the app's terms screen, comes next for the app.** The advisor reads its prompt again against master and the app's `main`, writes its Step 0 and plan here, and the operator's own session (the home desktop's main chat) builds it, beside 293.
  - **372B gets a fresh prompt from the advisor,** after 334B: `docs/prompts/372_the_apps_payment_screens.txt` was written for 372's old branch.
  - **The terms switch goes on after 334B and after 293's new terms version,** so every user accepts once.
  - **The test shop is marked inactive before the onboarding day,** with a block the advisor writes when the operator asks (K124's hold stands).
  - **210, launch readiness, gets a written scope** before the fleet reaches it.
  - **The advisor's estimate, a guess:** 7 to 10 working days to launch at the current pace. The likeliest to slip is 372B with the Stripe side, which waits on Stripe support for the terms links.
- **2026-11-25: three phases come between 210 and 344, in the operator's order (K140).** They are K137's phase after 210, split in three.
  - **The operator's words:** "Three, in this order: 1 public web address for the server, 2 self-serve sign-up (row 329), 3 TestFlight then App Store. 344 after all three. Write the list change and the three one-page scopes, documents only, no building, and give me one block to merge them." They answer the advisor's question, once 210's plan was approved and its build had started, whether K137's phase is one phase or three.
  - **409, a public web address for the server, is #25,** a new row. Sign-up and the App Store both need the server reachable off the tailnet: K136's answer 2 says "App Store once a public API exists".
  - **329, self-serve sign-up, is #26:** the existing row, retitled from "Self-service signup flow (web)", since where the form lives is a question for its Step 0.
  - **410, TestFlight then the App Store, is #27,** a new row. A builder session on the app's repository builds it, as 303B, 334B and 372B were built.
  - **344 moves down three places, to 28.** It still waits until after launch (K128).
  - **Each of the three asks the operator before it starts,** and its row says what: how the internet reaches the server, for 409; K101's rule for the first 10 shops, where the form lives and the email service, for 329; Apple's account and its review rules, for 410.
  - **The prompts,** one page each, are `docs/prompts/409_a_public_web_address_for_the_server.txt`, `docs/prompts/329_self_serve_sign_up.txt` and `docs/prompts/410_testflight_then_the_app_store.txt`. They are written before the fleet reaches them, as 210's was (K128). Rows 409, 329 and 410 are on master, 🔲.
- **2026-11-26: 409 is built by a builder session, not the fleet (K149).** The fleet's Step 0 for 409 (issue 104) classified it a reshape and asked the operator whether the fleet builds it as an extension or a builder session does.
  - **The operator's words:** "409: B".
  - **Row 25's builder is now `builder`.** The home desktop's main chat builds 409 from its draft pull request 98, with the operator's six answers of 2026-11-25, which stand; the advisor reviews it, and the operator merges. The fleet waits for it, and issue 104 keeps needs-hands until the session's close-out closes it.
  - **The order does not change:** 409, then 329, then 410, then 344.
- **2026-11-27: 329 is built by a builder session, not the fleet (K153), and the operator's answers of 2026-11-25 are on master (K152).** After 409's merge the fleet opened issue 112 for 329 and asked what the plan says it needs.
  - **The operator's words:**
    - "go with your picks" (K153);
    - the answers of 2026-11-25 to Step 0's questions 1, 3 and 4 (K152): the form on getmekno.com/signup, Resend as the email service, and pay first with a 14-day refund by hand.

    K141 and K150 had already settled K101's part.
  - **Row 26's builder is now `builder`.** The home desktop's main chat builds 329 from its draft pull request 99, the advisor reviews it, and the operator merges. The fleet waits for it, and issue 112 keeps needs-hands until the session's close-out closes it.
  - **The order does not change:** 329, then 410, then 344.

## Where the ledger stands

On `master` at `ebefa84`, 2026-11-22, rows numbered 100 and up, counted by their status cell (`grep -c -E '^\| *[0-9]{3}[A-Z]? .*\| *<status> *\|' docs/ROADMAP.md`):

| Status | Rows |
|---|---|
| ✅ | 257 |
| 🔲 | 58 |
| ⏸️ | 16 |
| 🚧 | 2 |

The two in progress are 303B, the app's staff sign-in screen, and 389A, the fleet's first trial. First counted on `60bb480`, 2026-10-12: 222, 61, 17 and 0.

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
- **A lawyer,** for 334's terms: since K84 (2026-11-15), later, as a review of the template terms that becomes a new version.
- **The shop's accountant** confirms the Massachusetts warranty readings (373–375) before a real warranty job.
- **Accounts** for offsite backup (345) and crash reports (343).
- **K11:** decide the Subconscious plan before it cancels on 2026-10-23.
