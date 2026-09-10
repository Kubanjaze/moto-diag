# Phase 244B — Guidance mode: answering the question the technician actually asked

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-09

## Goal

Let a technician ask the product an open question about a machine in front of
them — *"where is this leak most likely coming from?"*, *"what would make it
do this only when hot?"* — and get an answer **to that question**: the
candidate origins, how they present differently, and what to check first to
tell them apart.

**The goal is explicitly not to solve the problem.** It is to guide the
technician's own reasoning. They remain the diagnostician; the product's job is
to widen and then order their search space, and to say what it is resting on
while doing it.

This phase exists because that was tested and it did not work. The user showed
the product a bike, asked where the leak was most likely coming from, and got
"plenty of information" that "drifted from the purpose/question posed".

CLI: a guidance surface on the existing diagnostic entry points. No new
top-level command unless Step 0's substrate makes one unavoidable.

Outputs:
- a question carried as a first-class input through the analysis paths
- a response contract that can answer narrowly
- grounding so a candidate says what it rests on
- `tests/test_phase244B_guidance.py`

## Logic

### Step 0 — why it drifted. Three independent causes, all confirmed in source.

The drift is not a prompt-quality problem. The system is **structurally unable**
to answer a narrow question, in three separate places.

**1. The question is never passed.** `media/vision_analysis_pipeline.py`
builds its user prompt with `_build_user_prompt(vehicle_context, frame_count)`
— two parameters, neither of them the technician's question. The text it
produces says *"Examine each frame for the diagnostic symptoms in the system
prompt"*. The question was not drifted from; **it was never an input.**

**2. The system prompt is a fixed sweep.** `VISION_ANALYSIS_PROMPT` instructs a
six-category examination — smoke, fluid leaks, physical damage, gauge readings,
wear indicators, corrosion — and requires every finding to be typed from an
eight-value enum with a confidence and a severity. A complete sweep is the only
product that instruction can yield.

**3. The answer shape is forced.** The call sets
`tool_choice = {"type": "tool", "name": "report_video_findings"}`. Even if the
question reached the model, it **could not answer in prose or in any other
shape**. This is the decisive one: the model did not choose to drift, it was
prevented from answering narrowly.

There is a fourth, on the text path. `engine/models.py` makes
`DiagnosisItem.diagnosis` a **required** field described as *"What is wrong —
specific root cause"*, alongside required-by-convention `repair_steps`,
`parts_needed` and `estimated_cost`. So a narrow question still returns a full
diagnostic dump, and a system with no evidence for a root cause must still name
one. **The current product cannot say "I don't know, but here is how to narrow
it."**

Note also what a leak question actually hits today: `LEAK` is one of eight enum
values, and the prompt's leak guidance is about identifying the *fluid* by
colour — green is coolant, brown is oil. That is "what is this fluid", not
"where is it coming from". The system holds no representation of candidate
sources and discriminating observations, which is the question that was asked.

### What exists to build on

`diagnose --interactive` already runs a clarifying loop with
`MAX_CLARIFYING_ROUNDS = 3`, but it is the inverse shape: engine-led, converging
on a verdict, terminating. `engine/retrieval.py` and the corpus provide
grounding. `create_session` stores `symptoms` as a list and has no field for a
free-text question or a multi-turn exchange.

So this is extension across existing substrate, not greenfield — and the
substrate's contracts are the thing in the way.

### What this phase must decide, not assume

- **Whether to relax `tool_choice` or add a second tool.** Forcing a structured
  answer is what makes the current sweep reliable; removing it wholesale risks
  the opposite failure. A second tool shaped for guidance is the likelier
  answer, with the sweep tool retained for sweep requests.
- **Whether guidance is a mode or a separate path.** A question-shaped request
  and a sweep request want different prompts, different tools and different
  response contracts.
- **How a candidate cites itself.** This is the phase's central risk (below).

### Grounding — the central design risk

Track K spent thirty phases making static content honest about its sources.
Every knowledge entry says what it rests on; a figure carries its document or
is withheld; a phase records what it could not establish.

**This is the first surface where the product reasons out loud, and it has no
provenance discipline at all.** A guidance answer that says "check the
countershaft seal first" is worthless — worse, actively dangerous to a
technician's time — if there is no way to tell whether that came from the
corpus, from the machine's own recorded history, or from nowhere.

So a guidance answer must distinguish, per candidate:
- grounded in a corpus entry for **this** make, model and year — cite it;
- grounded in a cross-platform entry that applies generally — say so;
- general mechanical reasoning with no corpus support — say **that**;
- and it must be able to answer "not established for this machine" rather than
  inventing a candidate to fill the list.

An ungrounded guidance surface would undo, in one feature, the discipline the
corpus phases built.

## Key Concepts

- **Answer the question asked.** Relevance is the acceptance criterion, not
  completeness. More information is the failure mode here, not the goal.
- **Guidance, not verdict.** The output is candidates and discriminators, and
  the technician decides. A required root-cause field forces a guess.
- **Provenance per candidate**, in the Track K tradition, applied to generated
  reasoning rather than static content.
- **A deliberate absence is a deliverable** (Phase 224/234/241). "No corpus
  entry covers this for your machine" is a real answer.
- **Reachability is correctness** (240B S2) and **ordering is real** (240C):
  what the corpus retrieves and in what order shapes what guidance can ground on.

## Verification Checklist

- [ ] A technician question is carried end-to-end and is present in the model
      input on every path it is offered
- [ ] Asking a narrow question returns an answer to it — asserted against a
      recorded real exchange, not a synthetic one
- [ ] A guidance answer can decline to name a root cause
- [ ] Every candidate carries its grounding class; ungrounded reasoning is
      labelled as such
- [ ] "Not established for this machine" is reachable and tested
- [ ] The existing sweep path still works unchanged, with its tests green
- [ ] Session persistence carries the question and the exchange
- [ ] Every new guard mutation-tested
- [ ] Full regression at or above 6087, 0 failed

## Risks

- **This phase changes a shipped contract.** Relaxing or supplementing
  `tool_choice`, and touching `DiagnosticResponse`, affects the working sweep
  path. The sweep must keep working; its tests are the guard.
- **Fluent ungrounded reasoning is the failure mode**, and it is the one that
  looks most like success. A confident, well-organised, entirely invented list
  of leak candidates reads better than an honest short one. The grounding
  labels are the whole defence.
- **Relevance is hard to assert in a test.** "Answered the question" is not a
  regex. The acceptance criteria need a recorded exchange to anchor them —
  requested from the user, and if unavailable the phase must construct and
  record its own reference cases rather than assert nothing.
- **Guidance can become instruction.** On a machine with HV or brakes involved,
  "check X first" shades into a procedure. The Phase 241 discipline applies:
  route to the manual, do not invent a step.
- **Scope creep toward a chatbot.** The deliverable is a question-answering
  guidance surface on the diagnostic path, not a general assistant. Multi-turn
  memory beyond the session is out of scope for this phase.
