# Phase 244N — Stop discarding what already happens

**Version:** 1.0 | **Tier:** Large | **Date:** 2026-09-10

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

- [ ] A PATCH that changes an AI-authored diagnosis writes exactly one override
- [ ] The override carries the *prior* value in `ai_value`
- [ ] A PATCH with no change writes nothing
- [ ] A PATCH on a session with no `ai_model_used` writes nothing
- [ ] A failing override write does not fail the PATCH
- [ ] An `/ask` call writes exactly one `guidance_interactions` row
- [ ] The stored `response_json` round-trips to an equal `GuidanceResponse`
- [ ] `answers_the_question` is queryable as a column, not via JSON scan
- [ ] A failing interaction write does not fail the answer
- [ ] Re-analysis preserves the prior sweep in `video_analyses`
- [ ] `videos.analysis_findings` still holds the current sweep, unchanged shape
- [ ] Migration 059 backfills the four existing sweeps
- [ ] Migration 059 rolls back without destroying anything it did not create
- [ ] **No column named outcome / verdict / correct / score exists anywhere**
- [ ] `memory forget` erases a customer's guidance interactions
- [ ] Deleting a video cascades its analyses
- [ ] `capture stats` reports real counts
- [ ] Mutation: overwrite findings destructively again → a guard fails
- [ ] Mutation: make the override hook raise → a guard fails
- [ ] Mutation: drop the interaction write → a guard fails
- [ ] Full regression green

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
