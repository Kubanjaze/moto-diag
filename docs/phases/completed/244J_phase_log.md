# Phase 244J — Wiring the guidance surface — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-10 — Plan v1.0 written

Phase 244B built a guidance contract that cannot express a diagnosis, grounding
labels that force the model to say what it is reasoning from, and thirty-five
guards. **Nothing calls it.** The only way to ask the product a question is a
Python import.

This session found the same shape three times before noticing it had created a
fourth. `SafetyChecker` at Phase 241: implemented, tested, no production caller.
The `HV_` DTC format at 244: asserted in a comment, sourced by nothing.
`_build_vehicle_context` at 244B: a stub deferring the real join to a commit
that never landed. Each looked finished, and each failed silently for months.

**This one is the least defensible of the four, because it is mine and it is
recent.** I wrote the guards, verified the behaviour against a real recording,
documented the result — and shipped a method a technician cannot reach.

So the phase is deliberately small: one endpoint, one question, one answer,
against one video. The guidance contract itself is not touched, because a wiring
phase that edits the thing it wires is how regressions arrive dressed as
progress.

The one guard worth naming ahead of the build is the **inverse tripwire**. Phase
241's guard asserts that `SafetyChecker` has *no* production caller, recording a
gap so the day someone wires it, the test fails and explains what else that
wiring needs. This phase's asserts the opposite: that
`answer_question_about_frames` *does* have one. Same idea pointed in opposite
directions, and both fail loudly when reality moves away from what the docs
claim.


---

## 2026-09-10 — Built

`POST /v1/sessions/{session_id}/videos/{video_id}/ask`. Synchronous rather than
queued: the sweep is queued because nobody waits for it, and a question has
someone waiting. Ownership is verified before frames are extracted or any paid
call is made, and a guard asserts zero frames for a refused request — the
authorisation ordering is a cost property here, not only a security one.

The corpus arrives through `known_issues_for_vehicle`, so the endpoint inherits
Phases 244C-244I rather than re-querying: a typo in the make still resolves,
prose model values are indexed, models an entry excludes are not, and rows come
back tiered.

**The inverse tripwire.** Phase 241's guard asserts `SafetyChecker` has *no*
production caller, recording a known gap. This one asserts
`answer_question_about_frames` *does* have one, and says in its failure message
that removing the route deliberately means deleting the tripwire and explaining
why. Removing the route fails twelve tests.

**Adding a route reached into the mobile repository and found it stale.** Gate 11
compares live paths against a committed OpenAPI snapshot there, so the endpoint
failed it at once — the guard working. Regenerating added one path, changed no
existing one, and surfaced a defect this phase did not cause:
`KnownIssueResponse.source` had been missing `"regulation"` since Phase 235B,
because that snapshot was last regenerated at Phase 211 — **85 backend commits
earlier**. The mobile app's types did not know the value existed.

The gate could not have caught it: it compares paths only, so schema drift is
invisible. Phase 244K will extend it. Not folded in here, because a wiring phase
that grows to rewrite a gate is how a reviewable change stops being one.

Regeneration ran against a throwaway backend on a spare port with a temporary
database — Phase 244H's lesson applied to tooling. The operator's own backend on
port 8000 was left untouched, and briefly mistaken for the new one until the
missing route made the confusion obvious. The mobile repo was committed, not
pushed, with `generate-api-types` run alongside so the tracked types match the
snapshot.

20 guards, 7/7 mutations caught, F9 lint clean.

**What this phase is really about.** Phase 244B shipped thirty-five passing
guards on a method nothing could call, verified against a real recording, written
up as working. Every claim was true and the product still could not answer a
technician's question. **Guards that prove a component works say nothing about
whether anyone can reach it.**
