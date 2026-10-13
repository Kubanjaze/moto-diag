# Plan of record: the order from here, 2026-10-12

Written 2026-10-12 by the advisor session that verified Phases 373–381. This copy in the repository is the canonical one.

The ROADMAP stays the ledger: this file records the order of the open rows, and why. A Step 0 that measures something new can change the order. Any change is recorded here, dated.

The operator's words:
- 2026-10-08: "i care about doing it in the order that makes the most sense, with context in mind feel free to adjust what that looks like"
- 2026-10-08, on the home desktop: "i previously said thats where my server would live. I think it's time . we can roll that into the plan"
- 2026-10-12: "give me the prompt to give my claude code on my windows server desktop"

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
