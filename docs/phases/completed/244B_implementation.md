# Phase 244B — Guidance mode: answering the question the technician actually asked

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10

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

## Scope amendment (v1.0.1, 2026-09-10)

**Narrowed to the media path.** v1.0 left open whether to build the
question-carrying substrate across vision, audio and text at once, or to do one
path first. Decision: **vision/media only** in this phase.

Rationale: it is the path the failure was actually observed on, so acceptance
criteria can be anchored to a real case rather than an imagined one; it is the
path where all three structural blocks compound (`_build_user_prompt`,
`VISION_ANALYSIS_PROMPT`, and the forced `tool_choice`); and proving the shape
on one path before generalising avoids designing a shared abstraction against a
single example.

**Consequences for this phase.** The text path's fourth cause — the required
`DiagnosisItem.diagnosis` root-cause field — is **out of scope** and is recorded
as debt. `engine/models.py` and `DiagnosticResponse` are not touched. The
`diagnose --interactive` clarifying loop is not touched. A later phase
generalises whatever contract proves out here to the text and audio paths.

**What must be true anyway**: the guidance contract designed here has to be
plausible to generalise. Making it vision-specific in a way that cannot extend
would just move the problem.

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

- [x] A technician question is carried end-to-end and is present in the model
      input on every path it is offered
- [x] Asking a narrow question returns an answer to it — **met empirically at
      v1.2**: the user's original recording was re-run and the answer named
      three ordered leak candidates. See Addendum.
- [x] A guidance answer can decline to name a root cause
- [x] Every candidate carries its grounding class; ungrounded reasoning is
      labelled as such
- [x] "Not established for this machine" is reachable and tested
- [x] The existing sweep path still works unchanged, with its tests green
- [~] Session persistence carries the question and the exchange — **not done**,
      deferred with the multi-turn surface. See Deviations.
- [x] Every new guard mutation-tested
- [x] Full regression at or above 6087, 0 failed

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

### Resolution notes (v1.1)

- **Shipped contract — RESOLVED, by not changing it.** `tool_choice` was neither
  relaxed nor made conditional. `provide_guidance` was added as a second tool and
  `answer_question_about_frames()` as a second method, leaving
  `analyze_video_frames` byte-identical. A guard pins its `tool_choice` line and
  signature; its own 20 tests pass unchanged. `DiagnosticResponse` was not touched
  at all — v1.0.1 scoped the text path out.
- **Fluent ungrounded reasoning — MITIGATED, not eliminated.** `Grounding` is a
  required field on every candidate and `NOT_ESTABLISHED` is a first-class value,
  so an invented candidate must label itself as reasoning rather than machine
  knowledge. This makes an ungrounded answer *visible*; it does not make it
  impossible. Live evaluation remains the only real check.
- **Relevance — NOT RESOLVED, and recorded as such.** The recorded exchange was
  requested and not available, so the phase asserts structure only and the two
  affected checklist items are marked `[~]`. The alternative — inventing reference
  cases and asserting against them — would have produced guards that prove my
  guess about a good answer, not a good answer. Left honestly unasserted.
- **Guidance becoming instruction — RESOLVED by contract shape.** No
  `repair_steps` field exists to hold a procedure, and `GUIDANCE_PROMPT` routes to
  the manual for anything HV or brake related, per Phase 241.
- **Chatbot creep — RESOLVED by scope.** Single-turn, media path only. Session
  persistence of the question was deliberately not built; it belongs with the
  multi-turn surface if that is ever opened.

---

## Deviations from Plan

**A fourth cause was found during the build, reported by the user, and it was
not a prompt problem at all.** The user observed that the analysis *"guessed
make and model instead of pulling details already provided by the bike in the
session"*. `analysis_worker._build_vehicle_context()` was a stub returning an
empty `VehicleContext()`, with a docstring stating that "Commit 3 + 4 will JOIN
against sessions/vehicles for richer context". **That never landed.**

The consequence was worse than a missing enrichment.
`VehicleContext.to_context_string()` renders an empty context as the literal
string `"No vehicle context provided."` — so on every video analysis since
Phase 191B the model was *told* nothing was known about the machine, and then
shown pixels. Guessing was the only move available to it. The session held the
answer the whole time: the video row carries `session_id`, and sessions store
`vehicle_make`, `vehicle_model`, `vehicle_year` and `vehicle_id`.

Now wired, with symptoms JSON-decoded because sessions store them as text and a
raw string would have reached the prompt as a list of characters. Best-effort
preserved and tested: a missing session or a failing lookup returns an empty
context rather than blocking the analysis.

**This is the third instance of one family in this session.** `SafetyChecker`
(241) — implemented, tested, never wired. The `HV_` code format (244) —
asserted in a comment, never sourced. And now this — stubbed, deferred to a
commit that never came. In all three the code looked finished and nothing
failed loudly. **A stub whose docstring promises a later commit is a checkable
shape**, and a guard sweep for it is recorded as follow-up debt.

**Guidance was built as a separate path, not a flag on the sweep.** v1.0 left
open whether to relax `tool_choice` or add a second tool. Decision: a second
tool. Forcing a structured answer is what makes the sweep reliable, and the
failure was applying that shape to a question, not the forcing itself. So
`provide_guidance` sits beside `report_video_findings`, `analyze_video_frames`
is untouched, and a guard asserts its `tool_choice` line and signature are
unchanged.

**Two checklist items are not met, and are marked `[~]` rather than ticked.**

*Relevance is asserted structurally, not empirically.* The guards prove the
question reaches the model, that the contract cannot express a diagnosis, and
that grounding is mandatory. They do **not** prove the answer is relevant —
"answered the question" is not a regex, and I asked for the recording and its
response to anchor acceptance criteria to a real exchange. Without it, what
this phase can honestly claim is that **the four structural causes of drift are
closed**, not that drift is gone. That distinction is the phase's main
limitation and it should be re-tested against the original case before anyone
concludes the problem is solved.

*Session persistence is not done.* Storing the question and the exchange
belongs with the multi-turn surface, which v1.0.1 scoped out. `create_session`
still has no free-text question field.

**Scope held to the media path** per v1.0.1. The text path's required
`DiagnosticResponse.diagnosis` root-cause field is untouched and remains debt:
`diagnose --interactive` still cannot answer a narrow question narrowly.

## Addendum (v1.2) — two more fields the session already held

Re-running the user's actual recording found the stub fix was necessary but not
sufficient. Two further pieces of the session never reached the model:

**The `notes` field was read by nothing.** In the reported case it was the only
place the complaint was written down — *"Leaking oil on left side"* — while
`symptoms` was empty. The analysis was shown a bike and asked to find a fault
while the fault report sat one column away. Now carried into the context.

**The session's make/model is a stale snapshot.** `diagnostic_sessions`
denormalizes make/model/year at creation *and* keeps a `vehicle_id`; nothing
re-syncs them. The user corrected "Homda" to "Honda" in the garage and the
session kept reporting the typo — so the context builder, reading the session
copy, would have gone on naming the wrong marque forever after the data was
fixed. The live vehicle row is now preferred, with the snapshot as fallback and
a guard that a blank garage field cannot erase a populated session.

Guards 30 → 35.

## A tripwire fired on documentation, not on code

The full regression came back red on one test — Phase 241's own tripwire,
`test_safety_checker_has_no_production_caller_today`, reporting that
`SafetyChecker` was "now constructed in production" in
`media/analysis_worker.py`.

It was not. The file names it in a docstring, as a cross-reference: *"same
integration-gap family as `SafetyChecker` at Phase 241"*. The tripwire matched
the bare identifier anywhere in the file, so **it fired on the sentence that
exists to make the gap findable** — a mention-versus-use failure, the third
this session.

The perverse incentive is worth naming: as written, the tripwire punished
documenting the very pattern it guards. Anyone hitting it would have been
nudged to delete the reference rather than examine the wiring.

Repaired structurally rather than by pattern. The check now parses with `ast`,
so string literals and comments are not in the tree at all and only a real
reference counts — a `Name`, an `Attribute`, or an `ImportFrom`. Verified in
both directions, because relaxing a safety tripwire demands proof it still
catches what it exists for:

| mutation in a production file | fires |
|---|---|
| `from motodiag.engine.safety import SafetyChecker` | yes |
| `SafetyChecker()` construction | yes |
| `safety.SafetyChecker()` attribute access | yes |
| the identifier in a docstring | **no** |
| the identifier in a comment | **no** |

`SafetyChecker` remains unwired. The gap this pins is unchanged; only the
detector's ability to tell a caller from a citation is.

## Results

| Metric | Value |
|--------|-------|
| Structural causes of drift found | **4** — three in Step 0, one reported mid-build |
| Causes closed on the media path | 4 of 4, plus 2 found by re-running the real recording |
| Source files changed | 3 — `vision_types.py`, `vision_analysis_pipeline.py`, `analysis_worker.py` |
| New contract | `GuidanceResponse` / `GuidanceCandidate` / `Grounding` — no diagnosis, no repair steps, no parts, no cost |
| Sweep path | untouched, asserted by guard; its own 20 tests green |
| Guards | 35 |
| Relevance asserted | **structurally, then empirically** — original recording re-run at v1.2 |
| Regression | **6140 passed / 0 failed** (baseline 6087; +53 guards). First run was **red** — 1 failed, 6139 passed — on Phase 241's SafetyChecker tripwire firing on a docstring; see the tripwire section. **This single run validates 244B and 244C together**, since 244C was built before 244B was committed; no separate green run exists for 244B alone |

**Key finding: the answer drifted because four separate contracts each made a
narrow answer impossible, and none of them was the prompt.** The question was
not a parameter; the system prompt commanded a six-category sweep; `tool_choice`
forced the sweep's shape; and the vehicle context was a stub that actively told
the model nothing was known. Each is individually defensible — a sweep tool
should be forced, a stub should degrade gracefully — and together they made a
specific question unanswerable. **Asking "why did the model drift" was the
wrong question; the model was never given the opportunity not to.**
