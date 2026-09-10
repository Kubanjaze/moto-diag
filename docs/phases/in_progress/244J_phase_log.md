# Phase 244J — Wiring the guidance surface — phase log

**Status:** Planned
**Opened:** 2026-09-10

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
