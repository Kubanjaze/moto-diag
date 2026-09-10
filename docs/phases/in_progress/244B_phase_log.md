# Phase 244B — Guidance mode — phase log

**Status:** Planned
**Opened:** 2026-09-09

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
