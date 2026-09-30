# Phase 281 — Track O batch 3: recalls, VIN decoding, tax rates and exchange rates — phase log

**Status:** 🚧 In progress
**Branch:** `phase-281` (Opus session, main checkout, the only writer)

---

### 2026-09-30 — Opened: Track O batch 3

The prompt is `docs/prompts/281_track_o_batch3.txt` (merged in
`5cde0c3`). The operator's words it carries, verbatim:

> 1, 2, 3, 5 as recommended.

> 4: check row 288 — which jurisdiction does it name, and where is the first real shop? tax follows the shop. if it's MA (flat statewide), start there, not CA. either way: every rate stored with its effective date and source, and a check that fails when a rate is past its stated validity.

> note for the batch 3 prompt when you write it: first outbound calls in the app. tests use recorded fixtures, never live endpoints; the app degrades cleanly when a service is down (shown to the user, never silently empty); no live API call during the build except one smoke call per service, logged.

> i will be in MA and i mean, i intend to be in all 50 states or wherever they can download it , idk how that would work

> we will just wait until it reports and then go with whats recommended based on that

Batch 3 is rows 281 (NHTSA recall refresh), 287 (VIN decoder), 288 (tax
rates) and 289 (exchange rates). The tax plan the operator accepted: a
model not tied to one state or country; Massachusetts shipped verified
from the Department of Revenue's own text; every other shop enters its
own rate with its source and effective date; a check fails once a rate is
past its stated validity; automatic rates for every address paused.

Read first: the 275 handoff (`docs/handoffs/2026-09-30_275_closed.md`),
the triage report (`docs/reports/2026-09-28_track_o_triage.md`), rows
281, 287, 288 and 289, and 275's documents in `docs/phases/completed/`.

The first commit: **row 281 🚧**, carrying the batch.
