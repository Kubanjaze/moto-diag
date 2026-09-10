# Phase 244J — The guidance surface has no caller

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-10

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

- [ ] Asking a question about an owned video returns a `GuidanceResponse`
- [ ] A video belonging to another user is refused, before any frame work
- [ ] A video id from a different session in the same account is refused
- [ ] An empty or whitespace question is rejected with 422
- [ ] Individual tier is refused with 402
- [ ] The corpus reaches the call through the resolver, tiered
- [ ] The sweep path and its queued worker are untouched
- [ ] The inverse tripwire fails if the production caller is removed
- [ ] Mutation: drop the ownership check → a guard fails
- [ ] Mutation: remove the route → the tripwire fails
- [ ] Full regression green

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
