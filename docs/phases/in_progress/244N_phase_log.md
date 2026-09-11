# Phase 244N — Stop discarding what already happens — phase log

**Status:** Planned
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
