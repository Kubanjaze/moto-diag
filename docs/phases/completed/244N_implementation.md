# Phase 244N — Stop discarding what already happens

**Version:** 1.1 | **Tier:** Large | **Date:** 2026-09-10 (built 2026-09-10)

---

## Goal

The operator's framing: *"it needs more data to be built but it needs to start
acquiring said data passively."*

Right, and the obstacle is not that the data is hard to collect. Three streams
of exactly the right data pass through this product every day and are thrown
away at the end of the request. This phase stops throwing them away. It adds no
work for a technician, asks no question, and changes nothing a user sees.

**Passive** is the whole constraint. Anything that requires someone to fill in
a form is a different phase with a different success condition, and it is the
phase that has already failed once here — see S0-1.

## Step 0 — the feedback subsystem exists and has zero callers

**S0-1. An entire package is wired to nothing.** `motodiag/feedback/` contains
`feedback_repo.py` with **nine public functions** — `submit_feedback`,
`record_override`, `get_overrides_for_session`, `count_overrides_for_field` and
five more — plus `FeedbackReader` in `learning_hook.py`, plus models, plus two
tables, plus tests. Outside the `feedback/` package itself: **zero callers.**
There is no API route (`api/routes/` has no `feedback.py`) and no CLI command.

So `diagnostic_feedback` and `session_overrides` sit at 0 rows for the simplest
possible reason: **there is no way to put a row in them.** This is the largest
integration gap found this session — larger than the `SafetyChecker` at 241 or
the `VehicleContext` stub at 244C, because those were single functions and this
is a subsystem built at Phase 116 and never connected.

It also explains Phase 244M's dead compile path. 244M wired
`diagnostic_feedback` into the memory compile and noted the table was empty;
the reason is one layer further down than "nobody has used it yet".

**S0-2. `session_overrides` is a passive capture surface, and the hook already
exists.** Its columns are `(session_id, field_name, ai_value, override_value,
overridden_by_user_id, reason, overridden_at)` — precisely *"the AI said X, a
mechanic changed it to Y."* And `PATCH /v1/sessions/{id}` already accepts
`diagnosis`, `confidence` and `severity`. The update overwrites them and
**records nothing about the prior value.**

> This is the finding that makes the phase cheap. An override is not a form —
> it is a **byproduct of work the technician was already doing.** They correct
> the diagnosis because they need it correct on the work order; capturing that
> they changed it costs them nothing. The most valuable ground-truth signal in
> the product is a side effect of normal use, and the table for it was built
> nine phases ago and left unconnected.

**S0-3. `/ask` persists nothing.** `GuidanceResponse` carries
`question_understood_as`, `answers_the_question`, ranked `candidates` (each with
`why_plausible`, `how_to_discriminate` and a `Grounding` label),
`what_would_narrow_it`, `not_established` and `observation_basis`. All of it is
serialised to the client and discarded. Since 244L a `vision_guidance` cost row
survives the request — **so the product records what the question cost and not
what it was.**

**S0-4. Re-analysis destroys the previous sweep.** `set_analysis_findings` runs
`UPDATE videos SET analysis_findings = ?`. There is one blob per video and no
history. This has already cost real data: commit `d2c23f8` — *"Preserve session
6's pre-244B sweep before overwriting it"* — exists because the sweep had to be
rescued into git by hand before a re-run.

**S0-5. The project already has an interaction-log pattern; don't invent one.**
`intake_usage_log` is `(user_id, kind, model_used, confidence, image_hash,
tokens_input, tokens_output, cost_cents, created_at)` — append-only, one row per
interaction, written by `intake/vehicle_identifier.py`. Follow it.

**S0-6. `ai_response_cache` is a cache, not a log, and conflating them would be
a mistake.** It has a UNIQUE `cache_key`, `hit_count` and `last_used_at`: keyed
by input, for reuse, one row per distinct input. An interaction log is keyed by
time, append-only, one row per event — two identical questions asked a week
apart are one cache row and two interactions. They answer different questions
and this phase does not touch the cache.

## What this phase records, and what it refuses to record

Three streams, all additive, none destructive:

| stream | today | after |
|---|---|---|
| Mechanic corrections | discarded by `PATCH` | `session_overrides` row |
| Guidance Q&A | discarded at response | `guidance_interactions` row |
| Superseded sweeps | overwritten in place | `video_analyses` row kept |

**The rule that protects the eventual dataset: record, never label.** A finding
nobody acted on is `unresolved`, not `wrong` — it may have been correct and
deprioritised, or correct and fixed without a work order. If absence of evidence
is allowed to become a negative label, the calibration computed on this data in
a year is built on invented negatives and nothing downstream can tell. So this
phase stores observations and timestamps and **writes no outcome column at
all** — not even a nullable one, because a nullable column invites a default.
Interpretation is Phase 244P's problem, on data this phase keeps honest.

## Non-goals

- **No linkage or inference.** Not connecting a work order to the finding that
  preceded it. That is 244P, and it is unbuildable until this phase's rows exist.
- **No per-finding stable ids.** A sweep is addressable as a `video_analyses`
  row; individual findings get durable identity in 244P.
- **No outcome, verdict, correct/incorrect or score column anywhere.**
- **No new technician-facing surface.** No form, no prompt, no "was this
  helpful?". If it needs a click it is not passive and it belongs elsewhere.
- **No hive mind** (244O), **no vision answer reuse** (244P+).
- **No retention policy.** These rows are subject to the same erase path 244M
  built, and extending `memory forget` to cover them is in scope; deciding how
  long they live is not.

## CLI

```
motodiag capture stats                    # what is accumulating, per stream
motodiag capture interactions [--vehicle N] [--limit N]
motodiag capture overrides [--session N]
motodiag capture analyses --video N       # sweep history, newest first
```

Read-only by design. There is no `capture record` command — if a human has to
run something, the capture was not passive.

## Outputs

- `session_overrides` rows written as a side effect of existing PATCH traffic.
- `guidance_interactions` rows, one per `/ask`, carrying the full
  `GuidanceResponse` and the question.
- `video_analyses` rows, one per sweep run, with prior sweeps preserved.
- `motodiag capture stats` — the honest count of how much ground truth exists,
  so "we don't have enough data yet" is a number rather than a feeling.

## Logic

**Migration 059** adds two tables and touches no existing data.

`guidance_interactions`: `(id, video_id FK ON DELETE SET NULL, vehicle_id FK ON
DELETE SET NULL, session_id, question TEXT NOT NULL, question_understood_as,
answers_the_question INTEGER, response_json TEXT NOT NULL, candidate_count,
model_used, cost_event_id FK, asked_by_user_id, created_at)`. The full response
is kept as JSON **and** the fields worth querying are promoted to columns —
`answers_the_question` is the single most interesting bit in the product (how
often can it not answer?) and must not require a JSON scan.

`video_analyses`: `(id, video_id FK ON DELETE CASCADE, findings_json NOT NULL,
model_used, cost_usd_cents, frames_analyzed, analyzed_at, superseded_at)`.
`set_analysis_findings` gains an insert here before its existing UPDATE, so the
`videos.analysis_findings` column keeps working exactly as it does today — it
becomes a pointer to the current sweep rather than the only copy. **Nothing
downstream changes**, which is the point: 244M's compile, the API and the
reports all keep reading the column.

Existing blobs are backfilled into `video_analyses` by the migration, because
four sweeps already exist and dropping them on the floor while adding a table
whose purpose is to stop dropping sweeps would be its own joke.

**The override hook.** In the session PATCH path, before applying an update:
for each of `diagnosis`, `confidence`, `severity` present in the request and
differing from the stored value, if the stored value was AI-authored
(`ai_model_used` is set on the session), record a `SessionOverride` via the
existing `feedback_repo.record_override`. Then apply the update as now.

Three constraints on that hook:

1. **It cannot fail the request.** A capture write that 500s a technician's
   edit has traded the thing that matters for the thing that might matter later.
   Wrapped, logged, swallowed — the same contract 244L set for cost recording.
2. **It records only human edits of AI values.** A session the AI never touched
   has no `ai_value` to contrast, and recording `(NULL → "x")` as an override
   would dilute the signal with ordinary data entry.
3. **No-op PATCHes record nothing.** Sending the same value is not a correction.

**Erasure.** `memory forget` is extended to cover `guidance_interactions` for a
customer's vehicles. `video_analyses` cascades from `videos`. A guidance
question is a person's words about their machine and is as deletable as a
compiled fact.

## Key Concepts

- **Passive means byproduct.** The capture that works is the one attached to
  work someone already had a reason to do. The feedback subsystem failed for
  nine phases not because the schema was wrong — it is right — but because
  every path into it required someone to go out of their way.
- **Record, never label.** Storing "a work order closed four days after this
  finding" is a fact. Storing "this finding was correct" is a guess wearing a
  column name, and it is unfalsifiable once written.
- **Absence must stay distinguishable from negative.** Forever, not by
  convention.
- **A cache and a log are not the same table.** Keyed by input vs keyed by time.
- **The most valuable signal in the product is the one it currently deletes.**
  A real technician, on a real machine, mid-repair, asking what they actually
  need to know — and the answer evaporates at the end of the HTTP response.

## Verification Checklist

- [x] A PATCH that changes an AI-authored diagnosis writes exactly one override
- [x] The override carries the *prior* value in `ai_value`
- [x] A PATCH with no change writes nothing
- [x] A PATCH on a session with no `ai_model_used` writes nothing
- [x] A failing override write does not fail the PATCH
- [x] An `/ask` call writes exactly one `guidance_interactions` row
- [x] The stored `response_json` round-trips to an equal `GuidanceResponse`
- [x] `answers_the_question` is queryable as a column, not via JSON scan
- [x] A failing interaction write does not fail the answer
- [x] Re-analysis preserves the prior sweep in `video_analyses`
- [x] `videos.analysis_findings` still holds the current sweep, unchanged shape
- [x] Migration 059 backfills the four existing sweeps
- [x] Migration 059 rolls back without destroying anything it did not create
- [x] **No column named outcome / verdict / correct / score exists anywhere**
- [x] `memory forget` erases a customer's guidance interactions
- [x] Deleting a video cascades its analyses
- [x] `capture stats` reports real counts
- [x] Mutation: overwrite findings destructively again → a guard fails
- [x] Mutation: make the override hook raise → a guard fails
- [x] Mutation: drop the interaction write → a guard fails
- [x] Mutation: add an `outcome` column → the record-never-label guards fail
- [x] Mutation: record no-op PATCHes as corrections → a guard fails
- [x] Mutation: capture overrides with no AI author → a guard fails
- [x] A numeric no-op (`0.8` vs `'0.8'`) records nothing
- [x] The `/ask` capture resolves `vehicle_id` from the **session**, not the video
- [x] `capture` exposes no `record` command — recording is a byproduct
- [x] Full regression green — **6,463 passed, 0 failed**, 23:36

## Risks

- **The override hook sits on a live write path.** Mitigated by the
  cannot-fail-the-request contract and by a guard that asserts the PATCH still
  succeeds when capture raises. The same shape 244L used, which worked.
- **`video_analyses` grows without bound.** One row per sweep per video, each
  holding a findings blob. At current volume this is nothing; at scale it needs
  a retention answer, which this phase deliberately does not invent. Recorded
  as debt rather than solved speculatively.
- **Capturing a technician's edits is monitoring-adjacent.** `session_overrides`
  carries `overridden_by_user_id`. 244M's research flagged technician monitoring
  as *wholly unresearched* — consent, works councils, two-party-consent wiretap
  law — and this phase does not resolve it. What it does is narrow: the column
  already exists, the data is a correction to a machine's record rather than a
  measure of a person, and nothing in this phase aggregates, ranks or reports
  per-technician. **Building any per-mechanic accuracy view is out of scope and
  should not be added without that research.** Stated here so the constraint
  travels with the data.
- **Guidance questions are free text and will eventually contain personal
  information** — a customer's name, a phone number, whatever the technician
  typed. They are covered by the erase path for that reason, and the CJEU
  en-bloc concern from 244M's research applies: redaction at ingest is the
  better answer and is not attempted here.
- **This phase produces no visible improvement.** Nothing gets smarter, no
  answer gets better, and the value is entirely in what becomes possible later.
  That is the correct trade and it is worth saying plainly, because a phase
  whose success looks identical to doing nothing is easy to skip and expensive
  to skip late.

---

## Deviations from v1.0

**1. The "never raises" contract was in the wrong place, and the tests caught
it.** Every capture function was written to swallow its own exceptions, and
that felt like enough. It is not. Two guards — `a_failing_override_capture_does
_not_fail_the_patch` and `a_failing_analysis_history_write_does_not_fail_the
_analysis` — patched the capture callable itself to raise, and **both failed**:
the promise lived inside the callee, while the call sites invoked it bare. A
failed import, or one refactor that lets a capture function raise, and a
technician's edit 500s for a logging concern.

Both call sites are now guarded as well. The contract is "capture never costs
the request", and **the boundary is where a promise like that has to hold** —
not one frame further in, where the next person to edit the callee can silently
revoke it.

**2. `video_repo.py` had no logger, so the fix I wrote raised `NameError` from
inside its own `except` block.** The guard stayed red after the "fix" and said
so. A handler that throws is worse than no handler, because it converts a
swallowed failure into an unhandled one at exactly the moment things are
already going wrong.

**3. The `/ask` capture would have written `vehicle_id = NULL` on every row.**
The first draft read `row["vehicle_id"]` off the video. **`videos` carries
`session_id` and has no `vehicle_id` column**, so the lookup would have been
`None` forever — and that is not cosmetic: erasure resolves customer →
vehicles → interactions, so a permanently NULL `vehicle_id` means a deletion
request silently matches nothing *and reports success*. Caught by checking the
column list rather than assuming it. Now resolved through the session, with a
guard.

**4. `cost_estimate` added to the captured fields.** v1.0 named diagnosis,
confidence and severity. `OverrideField` also has `cost_estimate`, and
`SessionUpdateRequest` accepts it — the captured set is the intersection of
what the model authors and what a PATCH can carry, and leaving a member out
would silently drop a real correction.

**5. Erasure's dry-run had to change too.** `erase_plan` counted only
`memory_facts` while `erase_customer` now also deletes interactions. A preview
that undercounts is a lie in precisely the situation it exists to prevent, so
the count covers both.

**6. Nine schema pins, and the note left at 244M did its job.** 244M was caught
by the regression because one pin is spelled `get_current_version(db_path) ==
N` rather than `SCHEMA_VERSION == N`. This time the search covered both forms
and found all nine before the regression ran — eight of one spelling, one of
the other. The note in that pin's reason string is why.

**7. The backfill guard was wrong on its first write.** It deleted the
`schema_version` row for 059 and re-ran `init_db`, which failed with "table
guidance_interactions already exists" — the migration machinery correctly
objecting to being told something had been un-applied when it had not. Replaced
with a real `rollback_to_version(58)`.

**8. The test fixture needed `reset_settings()`.** `get_settings` is an
`lru_cache(maxsize=1)`, so `create_app()` kept a path cached by an earlier test
and the API read a different database than the fixture wrote. It surfaced as
`no such table: api_keys` from inside auth middleware, several layers from the
cause.

## Results

| | |
|---|---|
| Schema | v58 → **v59** (migration 059) |
| New tables | `guidance_interactions`, `video_analyses` |
| Backfill | **4 sweeps, 20 findings** preserved from the existing column |
| Capture streams wired | 3 (overrides, guidance, sweep history) |
| Feedback subsystem callers | **0 → 1** (nine phases after it was built) |
| Guards | **46** |
| Mutations run | **6**, all caught |
| Schema pins bumped | 9 (8 of one spelling, 1 of the other) |
| Regression | **6,463 passed, 0 failed**, 23:36 |
| New source | 614 lines across 6 modules |

**The finding worth the phase.** Step 0 went looking for where to put captured
data and found that the place already existed — `session_overrides`, correct in
every column, with `feedback_repo.record_override` sitting beside it. The
subsystem had **zero callers outside its own package**, no API route and no CLI
command, since Phase 116. The tables were empty because **nothing could write
to them**, and the one-line fix was a call at a hook point that had been
overwriting the exact values the table wanted to store.

That reframes 244M's dead compile path too: 244M recorded "`diagnostic_feedback`
is empty" as an observation about usage. It was an observation about wiring.
