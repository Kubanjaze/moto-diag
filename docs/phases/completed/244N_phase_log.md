# Phase 244N — Stop discarding what already happens — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10

---

## 2026-09-10 — Plan v1.0 written

Opened from the operator's framing: *"it needs more data to be built but it
needs to start acquiring said data passively."* That is the correct read of
where 244M left things — the memory works, the compile path for mechanic
corrections is wired, and `diagnostic_feedback` has zero rows, so the most
valuable input has nothing in it.

**Step 0 found the reason, and it is one layer below where I had been looking.**
244M recorded that `FeedbackReader` had no callers. The truth is larger: the
**entire `feedback/` package** has no callers. Nine public repo functions, a
reader, models, two tables and tests, built at Phase 116 — and outside the
package itself, nothing calls any of it. No API route. No CLI command.

So `diagnostic_feedback` and `session_overrides` are empty for the simplest
possible reason: **there is no way to put a row in them.** Not "nobody has
bothered" — there is no path. That reframes the whole problem. The capture
system does not need designing; it needs connecting.

**And the connection point already exists.** `session_overrides` stores
`(field_name, ai_value, override_value, reason)` — *the AI said X, a mechanic
changed it to Y*. `PATCH /v1/sessions/{id}` already accepts `diagnosis`,
`confidence` and `severity`, and overwrites them without recording what was
there.

That is the finding that makes this phase cheap, and it is the principle the
phase turns on: **passive means byproduct.** An override is not a form. The
technician corrects the diagnosis because they need it correct on the work
order; recording that they changed it costs them nothing. The feedback
subsystem did not fail for nine phases because its schema was wrong — the
schema is right — but because every path into it required someone to go out of
their way, and nobody ever does.

**Two other streams evaporate the same way.** `/ask` returns a full
`GuidanceResponse` — restated question, ranked candidates each with a
discriminating check and a `Grounding` label, what would narrow it, what could
not be established — and persists none of it. Since 244L the product records
what that question *cost* and not what it *was*. And `set_analysis_findings`
runs `UPDATE videos SET analysis_findings = ?`, so every re-analysis destroys
the prior sweep; commit `d2c23f8` exists because one had to be rescued into git
by hand before a re-run.

**The design rule: record, never label.** A finding nobody acted on is
unresolved, not wrong — it may have been right and deprioritised, or right and
fixed without paperwork. If absence of evidence is allowed to become a negative,
the calibration computed on this data in a year rests on invented negatives and
nothing downstream can detect it. So this phase writes no outcome column at
all, not even a nullable one, because a nullable column invites a default.
Interpretation is 244P's job, on data this phase keeps honest.

**Two things Step 0 stopped me from building.** `ai_response_cache` looked like
somewhere to put interactions until its columns said otherwise — UNIQUE
`cache_key`, `hit_count`, `last_used_at` is a cache keyed by input, and a log is
keyed by time; two identical questions a week apart are one cache row and two
interactions. And `intake_usage_log` already establishes this project's
append-only interaction-log pattern, so the new table follows it rather than
inventing a shape. Fifth and sixth time this session that reading for what
exists beat building something.

**One constraint carried forward rather than resolved.** `session_overrides`
records `overridden_by_user_id`, which makes this monitoring-adjacent. 244M's
research flagged technician monitoring as wholly unresearched — consent, works
councils, two-party-consent wiretap law. This phase stays narrow: the column
already exists, the row is a correction to a machine's record rather than a
measure of a person, and nothing here aggregates or ranks per technician.
Building a per-mechanic accuracy view is explicitly out of scope and should not
be added without that research. Written into the plan's Risks so the constraint
travels with the data rather than living in one person's head.

**This phase will produce no visible improvement.** Nothing gets smarter and no
answer gets better; the entire value is in what becomes possible once the rows
exist. Worth saying plainly, because a phase whose success looks identical to
doing nothing is easy to skip and expensive to skip late.

## 2026-09-10 — Built

**The tests found a hole in the phase's own headline promise.** Every capture
function was written to swallow its exceptions, and that felt like enough. Two
guards patched the capture callable itself to raise and **both failed**: the
promise lived inside the callee while the call sites invoked it bare. So the
guarantee held only as long as nobody refactored the callee and no import
failed. Both call sites are guarded now. *The boundary is where a promise like
"this never costs the request" has to hold* — one frame further in, the next
person to edit the callee can silently revoke it.

Then the fix itself was broken: `video_repo.py` has no logger, so the `except`
block I wrote raised `NameError` from inside itself. The guard stayed red and
said so. A handler that throws is worse than no handler — it converts a
swallowed failure into an unhandled one at exactly the moment things are
already going wrong.

**A silent erasure bug, caught by reading the column list instead of assuming
it.** The first draft of the `/ask` capture read `row["vehicle_id"]` off the
video. `videos` carries `session_id` and **has no `vehicle_id` column**, so
every interaction would have stored NULL. That is not cosmetic: erasure
resolves customer → vehicles → interactions, so a permanently NULL
`vehicle_id` means a deletion request matches nothing **and reports success** —
a compliance failure that looks exactly like compliance.

**The note left at 244M paid for itself.** 244M was caught red by the
regression over one schema pin spelled `get_current_version(db_path) == N`
instead of `SCHEMA_VERSION == N`. The note left in that pin's reason string
said the obvious grep would miss it. This time the search covered both
spellings up front and found all nine pins before the regression ran.

**Six mutations, all caught:** destroy sweep history again; add an `outcome`
column; drop the interaction write; stop reading the prior value before a
PATCH; record no-op PATCHes as corrections; capture overrides with no AI
author.

**What the phase actually cost to build, versus what it unlocked.** Step 0 went
looking for somewhere to put captured data and found the place already built —
`session_overrides`, correct in every column, with `record_override` beside it,
unused since Phase 116. The tables were empty because nothing could write to
them. One call, at a hook point that had been overwriting the exact values the
table wanted to store.

That also corrects 244M's reading of its own dead compile path. 244M recorded
"`diagnostic_feedback` is empty" as a fact about usage. It was a fact about
wiring.

**Regression: 6,463 passed, 0 failed, 23:36.** Green first time, which is the first phase this session to manage it — the nine schema pins were found before the run rather than by it.
