# Phase 244Q — The text diagnosis stops guessing at its own output

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10 (built 2026-09-11)

---

## Goal

`motodiag diagnose quick` now completes — the crash fixed earlier today — but
what it produces is useless. The response came back at **exactly 2048 output
tokens**, the configured `max_tokens`, truncated mid-JSON. `json.loads` failed,
and `_parse_diagnostic_response` fell back to storing the raw text as the
diagnosis with a hardcoded `confidence=0.5` and `severity=medium`.

So the command succeeds, the database gets a row, and the row contains a JSON
fragment presented as a diagnosis with a confidence nobody computed. **That is
worse than the crash**: a crash is visible, and this is a plausible-looking
record that quietly poisons the ground truth Phase 244N exists to collect.

Two changes, both requested by the operator: raise the cap, and get structured
output from the model instead of parsing free text out of it.

## Step 0 — three findings that change the shape of this

**S0-1. The codebase already predicted this exact change and left instructions.**
`diagnose()`'s cache-key comment:

> *"Only input data that affects the AI's answer is hashed, not the assembled
> prompt text — so if the prompt template changes but the semantic inputs
> don't, **stale cache entries still serve**. (Track R phase 321+ can
> version-prefix the cache key if a prompt change ever breaks response
> compatibility.)"*

This change breaks response compatibility. **The truncated blob currently in
`ai_response_cache` would serve forever** for that query — the same bad row,
immune to the fix, indistinguishable from a good one. Versioning the cache key
is not optional here; it is the difference between fixing this and appearing to.

**S0-2. `ask()` has five callers outside the diagnosis path** —
`shop/parts_sourcing.py`, `shop/labor_estimator.py` (×2), `shop/ai_client.py`,
`shop/priority_scorer.py` (×2). Changing `ask()` to force tool use would reach
all of them. The codebase already set the precedent for exactly this situation,
in `ask_with_images`'s own docstring: *"this method does not break the existing
`ask()` cache path — it's a sibling method, not a replacement."* So: a sibling.

**S0-3. The vision path's tool builders are the pattern to copy, and copying
them wholesale is fine here.** `DiagnosticResponse.model_json_schema()` exposes
exactly `vehicle_summary`, `symptoms_acknowledged`, `diagnoses`,
`additional_tests` and `notes` — five fields, all of them content the model
should author. Only `vehicle_summary` is required. It does carry
`$defs` (`DiagnosisItem`, `DiagnosticSeverity`), so the schema is self-
referential and must be passed whole rather than having `$defs` stripped.

> **Corrected during Step 0.** A first draft of this finding claimed the schema
> also carried `input_tokens`, `output_tokens`, `model`, `cost_estimate` and
> `latency_ms`, and argued at length that handing a model its own cost estimate
> invites a fabricated number. Those fields belong to **`TokenUsage`**, a
> different class further down the same file; a `sed` range had spilled past
> the class boundary and the fields were read off the wrong model. The argument
> was sound and the premise was false. Nothing needs stripping.

**S0-4. Truncation is currently undetectable.** `stop_reason` is never read
anywhere in `client.py`. The API says plainly when it ran out of room and the
code does not look, which is why a truncated response degraded silently instead
of failing loudly. Raising the cap makes truncation *rarer*; reading
`stop_reason` makes it *visible*, and only the second one is a fix.

## Folded in: the text path reaches the cost ledger

Added to this phase after the operator pointed out what the rest of it had been
missing: *"we are keeping track to regulate what would be most cost efficient,
however one needs to let it work to get enough data for that."*

**Everything above tunes a path that writes nothing to the cost ledger.**
`cost_events.kind` accepts `whisper`, `claude_extraction`, `vision_sweep` and
`vision_guidance` — Phase 244L widened it for vision and text diagnosis was
never in it. So `max_tokens` was raised, and the fallback restructured, against
spend that cannot be measured. The only trace of the one real call is an
`ai_response_cache` row, which is a cache artifact rather than a ledger entry,
and this phase's cache-kind bump has just orphaned it.

**Migration 060 widens the CHECK to add `text_diagnosis`, and nothing else.**
No new column. `cost_events` already carries `transcript_id`, `video_id` and
`shop_id`, and a `session_id` link would be a second table rebuild for
attribution nobody has asked for yet. Cost by kind, by model and by day is what
"what does a day cost" needs; if per-session attribution turns out to matter it
will be visible in use rather than guessed at now.

**`units_label='tokens'` / `units_value=output_tokens`.** The pair is already
kind-polymorphic — `('duration_ms', N)` for Whisper, `('tokens', N)` for Claude
— so recording output tokens per call costs nothing extra and **accumulates the
completion-length distribution as a side effect.** That distribution is what
sets `max_tokens` properly later, from a p95 rather than from doubling 2048.

**A truncated call is recorded too, and that is the point.** It is 100% waste:
paid in full, unusable output. If truncations are invisible in the ledger, the
most expensive failure mode in the system is the one nobody can see.
`ResponseTruncated` already carries its usage for exactly this.

**Cache hits are not recorded.** Zero spend, and `ai_response_cache.hit_count`
already counts the saving. A zero-cost row would only dilute the averages the
ledger exists to produce.

### What this phase deliberately does NOT now do

Tune anything on this data. There is one call in the ledger's history. The
operator's point stands: a value chosen from n=1 is a guess wearing a number,
and `max_tokens = 4096` is exactly that — defensible in direction, because a
truncated call is pure waste, and arbitrary in magnitude.

## Non-goals

- **Not touching `ask()`.** Five shop callers depend on its free-text contract.
- **Not touching the vision path.** It already does this correctly.
- **No tuning from this data.** The ledger starts empty; `max_tokens = 4096`
  stays a guess until a distribution exists to replace it.
- **No `session_id` column on `cost_events`.** A second table rebuild for
  attribution nobody has needed yet.
- **Not removing the free-text fallback.** It stays as the path for a model
  that refuses the tool — but it stops being reachable by silent truncation,
  and it stops being able to masquerade as a real diagnosis.
- **Not re-running the failed diagnosis on a paid call** until the guards pass
  offline.

## Logic

**`max_tokens` 2048 → 4096.** The existing validator already permits 100–8192,
so this needs no config surgery. 4096 rather than the ceiling because structured
output is schema-constrained and therefore less verbose than free prose, and
because a cap that is never approached teaches nothing about real usage.

**A new sibling: `ask_structured(prompt, tool, ...)`.** Builds the tool, forces
`tool_choice={"type": "tool", "name": ...}`, returns
`(tool_input: dict, usage, stop_reason)`. `ask()` is untouched.

**`_build_diagnosis_tool()`** returns `DiagnosticResponse.model_json_schema()`
with the five metadata fields stripped, so the model is asked for
`vehicle_summary`, `symptoms_acknowledged`, `diagnoses`, `additional_tests` and
`notes` — and not for its own token count.

**Truncation becomes loud.** If `stop_reason == "max_tokens"`, the result is not
quietly degraded into a fallback. It raises, and the CLI reports that the
response was cut off and what the cap is. A caller can then retry with a higher
cap deliberately. **No truncated response is ever written to the cache**, which
is how the current bad row got there.

**The cache kind becomes `diagnose-v2`.** Old rows keep their `diagnose` kind,
never match a v2 lookup, and remain readable for forensics. This is the S0-1
instruction, taken.

## Key Concepts

- **A silent degradation is worse than a crash.** The crash earlier today was
  found in one run. This produced a confident-looking record that would have
  been discovered months later, inside data that had already been reasoned over.
- **A confidence nobody computed is a lie with a number on it.** `0.5` was a
  placeholder in a fallback, and it lands in the same column a real confidence
  would.
- **Ask the model for what it authors, not for what you measure.** A tool schema
  containing `cost_estimate` is an invitation to fabricate one.
- **A cache outlives the bug that filled it.** Versioning the key is part of the
  fix, not hygiene after it.
- **Sibling, not replacement** — the rule this codebase already wrote down.

## Verification Checklist

- [x] `max_tokens` default is 4096 and still inside the validator's range
- [x] The tool schema carries exactly the five fields the model authors
- [x] The tool schema keeps its `$defs` — it is self-referential
- [x] `ask_structured` forces `tool_choice` to the named tool
- [x] A tool-use response parses into `DiagnosticResponse` with no text parsing
- [x] `stop_reason == "max_tokens"` raises rather than degrading
- [x] A truncated response is **never** written to the cache
- [x] `ask()` is unchanged — its five shop callers still pass
- [x] Cache kind is `diagnose-v2`; a `diagnose` row never serves a v2 lookup
- [x] The existing truncated cache row cannot be served after this change
- [x] A model that refuses the tool still falls back, reusing the response
      it already paid for
- [x] Mutation: strip the forced `tool_choice` → a guard fails
- [x] Mutation: strip `$defs` from the tool schema → a guard fails
- [x] Mutation: swallow `stop_reason` again → a guard fails
- [x] Mutation: revert the cache kind to `diagnose` → a guard fails
- [x] A completed diagnosis writes exactly one `text_diagnosis` ledger row
- [x] The row records `units_label='tokens'` and the real `output_tokens`
- [x] **A truncated call is recorded** — waste must be visible
- [x] A cache hit records nothing (zero spend, no dilution)
- [x] A failed ledger write never costs the caller their diagnosis
- [x] `motodiag costs report` renders the new kind with no code change
- [x] Migration 060 rolls back by rebuilding, never by dropping `cost_events`
- [x] Mutation: drop the ledger write → a guard fails
- [x] Mutation: skip recording truncations → a guard fails
- [x] **A refusal costs exactly one API call** (the defect the regression found)
- [x] Full regression green — **6,497 passed, 0 failed**, 28:06

## Risks

- **4096 may still be too low for a verbose model on a complex machine.** That
  is now a *loud* failure rather than a silent one, which is the point. If it
  proves common, the cap moves again with evidence instead of guesswork.
- **Doubling `max_tokens` roughly doubles the worst-case cost per diagnosis.**
  Haiku output is cheap and the ledger from Phase 244L will show the real number
  per call rather than an estimate. Stated because it is the operator's money.
- **Old cache rows become dead weight.** They stay readable and stop serving.
  Purging them is `motodiag cache` work and not this phase's call to make.
- **The schema carries `$defs` and must keep them.** `DiagnosisItem` and
  `DiagnosticSeverity` are referenced by `$ref`, so a stripped schema would be
  unresolvable. Worth noting that `_build_guidance_tool` in the vision path
  computes a `$defs`-stripped copy and then never uses it — harmless dead code,
  but it reads as though stripping were intended. Not this phase's to remove.

---

## Deviations from v1.0

**1. The fallback made a second paid API call, and the full regression found
it — not this phase's 22 guards.** `diagnose()` caught a tool refusal and
called `ask()` again, so every structured failure cost **two** calls. A silent
cost doubling on the failure path: the same shape of defect this phase exists
to remove.

It surfaced as `call_count == 2` in `test_phase131_cache.py::TestDiagnoseIntegration`
— a nine-phase-old test written by someone else for another purpose, which
counted actual SDK calls. This phase's own guards mocked `ask_structured`
itself and therefore could never see how many times the API was reached.
**The guards tested the layer just written rather than the boundary that costs
money.**

Fixed by adding `ToolRefused`, which carries the prose and usage from the call
that already happened, so the fallback parses what was paid for instead of
buying it twice.

**2. The same wrong-layer mistake, again, in the ledger guards.** Nine new
guards called `record_diagnosis_cost` directly. Deleting the call site in
`diagnose()` left all nine green. Caught by running the mutation rather than
assuming, and fixed with a guard that drives `diagnose()` and looks in the
table.

Twice in one phase, the same error: **verifying a function exists and works,
while never checking that anything calls it.** It is the integration-gap family
turned inward — the same defect this session found in `feedback/`,
`SafetyChecker` and `FeedbackReader`, now in the tests themselves.

**3. S0-3 was false and was corrected before any code depended on it.** The
plan claimed the tool schema carried `cost_estimate`, token counts and latency,
and argued that handing a model its own cost estimate invites a fabricated
number. Those fields belong to `TokenUsage`; a `sed` range had spilled past the
end of `DiagnosticResponse`. Sound argument, false premise — caught by printing
the schema instead of trusting the plan.

**4. A guard shipped vacuous.** `assert "falling back" in ... or True` passes
unconditionally. Replaced with behaviour, then replaced again when the behaviour
it asserted turned out to be the wrong invariant.

**5. A hardcoded model ID, in the same session that had already been caught for
it.** Phase 191C's f9 lint failed the regression on
`claude-haiku-4-5-20251001` in this phase's test file — the identical mistake
made at 244L four hours earlier, caught by the identical guard, fixed the
identical way. Now sourced from `MODEL_ALIASES`.

**6. Ledger coverage folded in mid-phase**, at the operator's direction, after
they pointed out that everything above tuned a path the cost ledger could not
hold. Migration 060 and `text_diagnosis`.

## Results

| | |
|---|---|
| Schema | v59 → **v60** (migration 060) |
| `max_tokens` | 2048 → **4096** — direction evidenced, magnitude a guess |
| Cache format | `diagnose` → **`diagnose-v2`** |
| New API surface | `ask_structured`, `ResponseTruncated`, `ToolRefused`, `record_diagnosis_cost` |
| `ask()` | **unchanged** — five shop callers untouched |
| Guards | **34** |
| Mutations run | **10**; 8 caught first time, 2 exposed wrong-layer guards |
| Schema pins bumped | 10 |
| Regression | **6,497 passed, 0 failed**, 28:06 |

**The finding worth the phase** is not the cap or the tool. It is that the
text-diagnosis path had been spending money since Phase 03 that the cost ledger
was structurally unable to hold, and nobody noticed because the two facts lived
in different files. Phase 244L widened the CHECK for vision and the text path
was simply never considered. This phase spent its first half tuning cost
behaviour that could not be measured — and only stopped because the operator
asked what the data actually said.
