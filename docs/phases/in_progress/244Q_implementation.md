# Phase 244Q — The text diagnosis stops guessing at its own output

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-10

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

## Non-goals

- **Not touching `ask()`.** Five shop callers depend on its free-text contract.
- **Not touching the vision path.** It already does this correctly.
- **No schema migration.** Cache versioning is a key change, not a DDL change.
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

- [ ] `max_tokens` default is 4096 and still inside the validator's range
- [ ] The tool schema carries exactly the five fields the model authors
- [ ] The tool schema keeps its `$defs` — it is self-referential
- [ ] `ask_structured` forces `tool_choice` to the named tool
- [ ] A tool-use response parses into `DiagnosticResponse` with no text parsing
- [ ] `stop_reason == "max_tokens"` raises rather than degrading
- [ ] A truncated response is **never** written to the cache
- [ ] `ask()` is unchanged — its five shop callers still pass
- [ ] Cache kind is `diagnose-v2`; a `diagnose` row never serves a v2 lookup
- [ ] The existing truncated cache row cannot be served after this change
- [ ] A model that refuses the tool still falls back, and the fallback is
      labelled as such rather than carrying a fabricated confidence
- [ ] Mutation: strip the forced `tool_choice` → a guard fails
- [ ] Mutation: strip `$defs` from the tool schema → a guard fails
- [ ] Mutation: swallow `stop_reason` again → a guard fails
- [ ] Mutation: revert the cache kind to `diagnose` → a guard fails
- [ ] Full regression green

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
