# Phase 244J — The guidance surface has no caller

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

Phase 244B built `answer_question_about_frames`, a contract that cannot express
a diagnosis, grounding labels that force a model to say what it is reasoning
from, and thirty-five guards. **Nothing calls it.** A technician cannot ask the
product a question, because the only way in is a Python import.

This session found the same shape three times before this one:

| thing | state when found |
|---|---|
| `SafetyChecker` (241) | implemented, tested, no production caller |
| the `HV_` DTC format (244) | asserted in a comment, sourced by nothing |
| `_build_vehicle_context` (244B) | a stub deferring the join to a commit that never landed |

Each looked finished. Each failed silently for months. **This is the fourth, and
it is the one this session created** — which makes shipping it without a caller
the least defensible of the four.

## Non-goals

- **Not a chat surface.** One question, one answer, against one video. Multi-turn
  memory was scoped out at 244B v1.0.1 and stays out.
- **Not changing the guidance contract.** `GuidanceResponse`, `GUIDANCE_PROMPT`
  and the grounding rules are unchanged. This phase is wiring, and a wiring
  phase that quietly edits the thing it wires is how regressions arrive.
- **Not touching the sweep path.** `analyze_video_frames` and its queued worker
  are untouched, as at 244B.

## Logic

**`POST /v1/sessions/{session_id}/videos/{video_id}/ask`**, body
`{"question": "..."}`, returning `GuidanceResponse`.

**Synchronous, unlike the analysis upload.** The sweep is queued because nobody
is waiting for it; a question has someone waiting, and an answer delivered to
nowhere is not an answer. The cost is a request that runs as long as the model
takes — stated in the route's docstring rather than discovered.

**Ownership before anything expensive.** `get_video_for_owner` plus the
`session_id` cross-check, matching the file-streaming route exactly, and before
frames are extracted or any API call is made.

**Tier `shop`, matching upload.** The endpoint spends a vision API call, and
gating a paid operation at the same level as the operation that produced its
input is the least surprising choice.

**The corpus reaches it through the resolver.** `known_issues_for_vehicle`, so
the endpoint inherits every fix from 244C through 244I: a typo resolves, prose
models are indexed, excluded models are not, and rows arrive tiered.

**An inverse tripwire.** Phase 241's guard asserts `SafetyChecker` has *no*
production caller, recording a known gap. This phase's asserts the opposite —
that `answer_question_about_frames` **does** have one — so the integration gap
cannot silently reopen. The two guards are the same idea pointed in opposite
directions, and both fail loudly when reality moves.

## Key Concepts

- **An untested integration gap is a feature that does not exist.** Thirty-five
  guards on an uncallable method prove the method works, not that anyone can use
  it.
- **Queue what nobody waits for; answer what someone asked.** The sweep and the
  question have different shapes because they have different readers.
- **Check ownership before spending money.** Authorisation ordering is a cost
  property as well as a security one.
- **Assert the caller exists.** The cheapest guard against this family.

## Verification Checklist

- [x] Asking a question about an owned video returns a `GuidanceResponse`
- [x] A video belonging to another user is refused, before any frame work
- [x] A video id from a different session in the same account is refused
- [x] An empty or whitespace question is rejected with 422
- [x] Individual tier is refused with 402
- [x] The corpus reaches the call through the resolver, tiered
- [x] The sweep path and its queued worker are untouched
- [x] The inverse tripwire fails if the production caller is removed
- [x] Mutation: drop the ownership check → a guard fails
- [x] Mutation: remove the route → the tripwire fails
- [x] Full regression green

## Risks

- **A long synchronous request is a real cost**, and the wrong answer to it is a
  queue plus polling, which is a bigger surface than this phase should open. The
  latency is documented at the route; if it becomes a problem the fix is a
  streaming or job-backed variant, not a silent timeout.
- **Ownership checks are the security boundary here** and they are easy to get
  subtly wrong — a video id from another session in the same account must fail
  too, which is why that is a guard rather than an assumption.
- **The endpoint spends money per call.** No rate limiting beyond the existing
  tier middleware is added; that is the platform's concern and is recorded
  rather than half-solved here.
- **Wiring phases invite scope creep** toward the chat surface the user
  originally described. One question, one answer, one video.

---

## Deviations from Plan

**Adding a route reached into another repository, and found it stale.** Gate 11
compares the backend's live paths against a committed OpenAPI snapshot in
`moto-diag-mobile/api-schema/openapi.json`, so the new endpoint failed it
immediately — which is the guard doing exactly its job.

Regenerating with the mobile repo's own tooling added one path and changed no
existing one. It also revealed something this phase did not cause:
**`KnownIssueResponse.source` had been missing `"regulation"` since Phase 235B.**
The snapshot was last regenerated on 2026-09-07 at Phase 211 — **85 backend
commits earlier** — so the mobile app's generated types did not know that
provenance value existed, and a knowledge-base entry carrying it violated the
type that app compiles against.

**The gate could not have caught that**, because it compares paths only.
Component-schema drift is invisible to it. Recorded as Phase 244K rather than
folded in here: this is a wiring phase, and widening it mid-flight to rewrite a
gate is how a small change becomes an unreviewable one.

The regeneration ran against a throwaway backend on a spare port with a
temporary database — Phase 244H's lesson applied to tooling as well as tests. A
pre-existing backend of the operator's on port 8000 was left untouched, and was
briefly mistaken for the new one until the missing route made the confusion
obvious.

**The mobile repo was committed but not pushed**, at the operator's direction,
and `npm run generate-api-types` was run alongside the schema refresh so the
commit is coherent — the tracked `src/api-types.ts` is derived from the snapshot,
and committing one without the other would leave that repo internally
inconsistent.

## Results

| Metric | Value |
|--------|-------|
| Endpoint | `POST /v1/sessions/{session_id}/videos/{video_id}/ask` |
| Integration gaps closed | the fourth this session, and the only one it created |
| Guards | 20 |
| Mutations run / caught | 7 / 7 |
| Cross-repo | 1 path added, **0 existing paths changed**; 85 commits of schema drift repaired |
| Regression | **6300 passed / 0 failed** (baseline 6280; +20 guards). First run red on Gate 11's cross-repo OpenAPI snapshot — see Deviations |

**Key finding: guards that prove a component works say nothing about whether
anyone can reach it.** Phase 244B shipped thirty-five passing guards on a method
with no caller, verified its behaviour against a real recording, and wrote the
result up as working. Every one of those claims was true. The product still could
not answer a technician's question, and nothing in the suite noticed — because
nothing was asking that question.

The inverse tripwire is the cheap fix: Phase 241's asserts `SafetyChecker` has
**no** production caller, recording a known gap; this one asserts the guidance
method **does** have one. Same mechanism, opposite polarity, and between them
they make both states loud instead of silent.
