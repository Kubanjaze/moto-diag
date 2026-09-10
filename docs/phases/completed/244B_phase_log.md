# Phase 244B — Guidance mode — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-09 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-09 — Plan v1.0 written

Opened at the user's request after a real test failed: they showed the product
a bike, asked where the leak was most likely coming from, and got "plenty of
information" that "drifted from the purpose/question posed during the
recording". The goal they described is guidance rather than resolution — help
the technician work out where to look, not hand them a verdict.

**Step 0 found three independent structural causes, all in source, none of them
a prompt-quality problem.**

1. **The question is never passed.** `_build_user_prompt(vehicle_context,
   frame_count)` in `media/vision_analysis_pipeline.py` takes two parameters,
   neither the technician's question, and produces text telling the model to
   *"examine each frame for the diagnostic symptoms in the system prompt"*. The
   question was not drifted from — it was never an input.
2. **The system prompt is a fixed six-category sweep** — smoke, fluid leaks,
   damage, gauge readings, wear, corrosion — with every finding typed from an
   eight-value enum. A complete sweep is the only thing that instruction can
   produce.
3. **The answer shape is forced.** The call sets
   `tool_choice = {"type": "tool", "name": "report_video_findings"}`. Even had
   the question arrived, the model **could not** answer in any other shape.
   The model did not choose to drift; it was prevented from answering narrowly.

**A fourth cause sits on the text path.** `DiagnosisItem.diagnosis` is a
required field described as "What is wrong — specific root cause". So a narrow
question still returns a full diagnostic dump, and a system with no evidence
must still name a cause. **The product currently cannot say "I don't know, but
here is how to narrow it."**

Worth recording precisely what a leak question hits today: `LEAK` is one of
eight enum values, and the prompt's leak guidance is about identifying the
*fluid* by colour — green coolant, brown oil. That is "what is this fluid", not
"where is it coming from". The system holds no representation of candidate
sources and discriminating observations, which is the question that was asked.

**The central risk is grounding, and it is a Track K risk.** Thirty phases went
into making static content honest about its sources. This is the first surface
where the product reasons out loud, and it has no provenance discipline at all.
A guidance answer saying "check the countershaft seal first" is worse than
useless if a technician cannot tell whether that came from a corpus entry for
their machine, from a cross-platform entry, or from nowhere. So the phase
requires a grounding class per candidate and an answer that can say "not
established for this machine" instead of inventing a candidate to fill a list.
An ungrounded guidance surface would undo the corpus discipline in one feature.

**What the phase must decide rather than assume**, and has recorded as open:
whether to relax `tool_choice` or add a second guidance-shaped tool alongside
the working sweep tool; whether guidance is a mode or a separate path; and how
a candidate cites itself.

**Two things were asked of the user and are not blocking.** The recording and
its actual response, so acceptance criteria anchor to a real exchange rather
than a synthetic one — relevance is not a regex and "answered the question"
needs a reference case. And whether to scope this to the media path first or to
the shared question-carrying substrate across all three input paths at once.

Baseline before any work: **6087 passed / 0 failed** (Phase 244).

Plan v1.0 written to `docs/phases/in_progress/244B_implementation.md`.

---

## 2026-09-10 — Built

**A fourth cause, and it was the one the user actually noticed.** Mid-build they
reported that the analysis *"guessed make and model instead of pulling details
already provided by the bike in the session"*. That is not a prompt problem
either. `analysis_worker._build_vehicle_context()` was a stub — it returned an
empty `VehicleContext()` under a docstring saying "Commit 3 + 4 will JOIN
against sessions/vehicles for richer context". Those commits never landed.

The empty context was worse than absent. `VehicleContext.to_context_string()`
renders empty as the literal `"No vehicle context provided."` — so every video
analysis since Phase 191B has opened by **telling the model nothing is known
about the machine**, then showing it pixels. Guessing was the only move left.
The data was there the whole time: the video row carries `session_id`, and
sessions store make, model, year and `vehicle_id`.

Now joined, with symptoms JSON-decoded — sessions store them as text, and a raw
string would have reached the prompt as a list of individual characters.
Best-effort behaviour is preserved and tested: a missing session or a failing
lookup yields an empty context rather than failing the analysis.

**Third instance of one family in this session.** `SafetyChecker` (241) —
built, tested, never wired. The `HV_` code format (244) — asserted, never
sourced. This — stubbed, deferred to a commit that never came. Each looked
finished; none failed loudly. **A stub whose docstring promises a later commit
is a checkable shape**, and sweeping for it is recorded as debt.

**Guidance is a second path, not a flag.** `provide_guidance` sits beside
`report_video_findings`; `analyze_video_frames` is untouched and a guard pins
its `tool_choice` line and signature. Forcing a structured answer is *why* the
sweep is reliable — the bug was applying the sweep's shape to a question, not
the forcing.

**What the contract cannot say.** `GuidanceResponse` has no `diagnosis`, no
`repair_steps`, no `parts_needed`, no `estimated_cost`. Every candidate carries
a `Grounding` value, `NOT_ESTABLISHED` included, so "this project does not
establish that for this machine" is expressible rather than something the model
must route around. That is the phase's whole thesis: the earlier answer drifted
partly because **no available output shape let it answer narrowly and admit a
gap.**

30 guards. Sweep path's own 20 tests green. F9 lint clean.

**The limitation, stated plainly.** These guards prove the question reaches the
model, that a diagnosis is inexpressible, and that grounding is mandatory. They
do **not** prove the answer is relevant — that is not a regex. The four
structural causes of drift are closed; whether drift is gone needs the original
recording re-run against this build.


---

## 2026-09-10 — Re-run against the original recording

The user supplied the session rather than the file: *"just use the video saved
in this session, its the exact same one."* Session 6, video 5, 22 frames.

**The before, measured rather than remembered.** The stored analysis held 15
findings — tank grip pads, brake lever, windscreen, frame sliders, respray,
seat wear. **Not one concerned a leak.** The word appears once, at position 10
of 11 in `suggested_diagnostics`. The overall assessment opens "likely a
Kawasaki ZX-series, Suzuki GSX-R, or similar" for a bike the session records as
a Honda.

**Two more defects, both the same shape as the stub.** The session's `notes`
field held "Leaking oil on left side" and was read by nothing. And the session's
make/model is a denormalized snapshot that never re-syncs with the garage — the
user corrected "Homda" to "Honda" and the session kept the typo. Both fixed,
guards 30 → 35.

**The after.** Three leak candidates ordered by what to check first, each with a
discriminator, plus what would narrow it and an explicit statement of what the
frames cannot resolve. The contract's grounding labels proved non-vacuous under
a real test: handed 20 corpus rows, the model reported that none of them
addressed an oil leak and marked every candidate `general_reasoning` rather than
laundering corpus presence into machine-specific confidence.

**The relevance checklist item, previously `[~]`, is now met empirically** — not
by a regex, but by the run the user asked for.


---

## 2026-09-10 — Regression red, then fixed: a tripwire that fired on prose

First full regression: **1 failed, 6139 passed**. The failure was Phase 241's
`test_safety_checker_has_no_production_caller_today`, claiming `SafetyChecker`
was now constructed in `media/analysis_worker.py`.

It is not constructed there. It is *named* there, in a docstring, as a
cross-reference to the integration-gap family. The tripwire matched the bare
string anywhere in the file, so it fired on the documentation written to make
the gap findable — and would have nudged whoever hit it to delete the sentence
rather than look at the wiring.

Rewritten to parse with `ast`, where string literals and comments simply are
not part of the tree. Mutation-verified both ways: a real import, a real
construction and an attribute access each fire; the identifier in a docstring
or a comment does not. **Relaxing a safety tripwire without proving it still
catches its target would have been the worse defect**, so both directions were
tested before the change was kept.

Third mention-versus-use failure in this session, after Phase 244's attribution
guard and its repair. The pattern is stable enough to state: **a guard that
matches an identifier as text will eventually fire on the prose that explains
it.**
