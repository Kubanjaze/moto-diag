# Phase 244Q — The text diagnosis stops guessing at its own output — phase log

**Status:** Planned
**Opened:** 2026-09-10

---

## 2026-09-10 — Plan v1.0 written

Opened directly from the operator's instruction — *"raise max_tokens and use
structured output"* — after running `motodiag diagnose quick` to give Phase
244N's override capture something to fire on. The crash was fixed in a hotfix;
what the command produced afterwards was worse than the crash.

The response came back at **exactly 2048 output tokens**, the configured cap,
truncated mid-JSON. Parsing failed and the fallback stored the raw text as the
diagnosis with a hardcoded `confidence=0.5` and `severity=medium`. The command
reported success. **A crash is found in one run; this produces a
plausible-looking record that would surface months later, inside data already
reasoned over** — and it lands in the exact column Phase 244N exists to collect
honest ground truth in.

**Step 0 found that the codebase had already predicted this change and left the
instruction for it.** `diagnose()`'s cache-key comment says only semantic inputs
are hashed, not the prompt text, so *"if the prompt template changes but the
semantic inputs don't, stale cache entries still serve"* — and names
version-prefixing the key as the remedy if a change ever breaks response
compatibility. This change breaks response compatibility. Without versioning,
**the truncated blob now sitting in `ai_response_cache` would serve forever**
for that query: the same bad row, immune to the fix, indistinguishable from a
good one. That turns a fix into the appearance of one.

**Step 0 also set the shape.** `ask()` has five callers outside the diagnosis
path — parts sourcing, labor estimation twice, the shop AI client, priority
scoring twice — so forcing tool use on `ask()` itself would reach all of them.
The codebase already wrote down the answer, in `ask_with_images`'s docstring:
*"a sibling method, not a replacement."* So `ask_structured` is a sibling.

**And one correction to the pattern being copied.** The vision path builds its
tool from `VisualAnalysisResult.model_json_schema()` wholesale. Doing that with
`DiagnosticResponse` would hand the model a schema containing `cost_estimate`,
`input_tokens`, `output_tokens`, `model` and `latency_ms` — metadata the system
stamps after the call. **Asking a model for its own cost estimate invites it to
invent a number that then sits in a field meant to hold a measured one.** The
tool schema describes what the model authors and nothing else.

**The real fix is not the cap.** `stop_reason` is never read anywhere in
`client.py`. The API said plainly that it had run out of room and the code did
not look. Raising the cap makes truncation rarer; reading `stop_reason` makes it
visible, and only the second one is a fix. A truncated response will raise, and
will never be written to the cache — which is how the current bad row got there.

## 2026-09-10 — Step 0 correction, before any code was written

S0-3 as first written was wrong. It claimed `DiagnosticResponse` carries
`input_tokens`, `output_tokens`, `model`, `cost_estimate` and `latency_ms`, and
built an argument about not asking a model to estimate its own cost.

Those fields belong to **`TokenUsage`**, declared further down the same file. A
`sed` range used while reading the models spilled past the end of
`DiagnosticResponse` and I read the next class's fields as its own. Checking
`model_json_schema()` directly — rather than reading the source and inferring —
showed five properties, all of them content the model should author, and
nothing to strip.

The reasoning was sound and the premise was false, which is the more dangerous
combination: a well-argued finding is harder to doubt. Caught because the build
step began by printing the actual schema instead of trusting the plan. Second
time today that a `sed`/`grep` range produced a confident claim about the wrong
text — the earlier one was a `LIMIT 1` sample that became "every finding carries
0.99".

What survived: the schema does carry `$defs` for `DiagnosisItem` and
`DiagnosticSeverity`, so it is self-referential and must be passed whole.
