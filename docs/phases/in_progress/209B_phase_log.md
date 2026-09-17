# Phase 209B — What the launch checklist doesn't know — phase log

**Status:** Planned
**Opened:** 2026-09-17

---

## 2026-09-17 — Plan v1.0 written

This phase exists because of a recommendation I got wrong.

While reorienting, I recommended **Phase 210, launch readiness**, as the next
move. The reasoning was that Gate 10 had closed and so 210 was unblocked. Step 0
found `docs/launch-checklist.md`, written 2026-09-09, which says *"Phase 210 is
deliberately unstarted — it depends on steps 1–6"*: host, Docker, privacy
policy, demo instance, screenshots and TestFlight. All of those are the
operator's to do. Gate 10 was never the gate that mattered. I stopped and said
so before building anything under the wrong label.

The substance the operator approved still stands: a systematic hunt for code
that was built but never connected. It goes here, as an insertion before 210,
together with bringing the checklist up to date with the product it's supposed
to launch.

**The checklist was written the day before the 244 series began, and the gaps
are not cosmetic:**

- **The Docker image can't run the headline feature.** No ffmpeg in
  `python:3.13-slim`, so every video upload returns 503 in a container. It only
  works on the laptop because Homebrew installed ffmpeg.
- **The deployment env block has no AI keys.** A server configured by following
  the checklist would have every AI feature failing.
- **The privacy wording is false.** *"Data goes only to the operator's own
  backend"*: the backend sends frames and questions to Anthropic and audio to
  OpenAI.
- **The app's server address is compiled in**, with no runtime setting. A
  TestFlight build today would point at a tailnet no reviewer can reach, and
  step 4's instruction to give the reviewer a server URL has nowhere in the app
  to go. It also contradicts the premise that "every deployment is the shop's
  own": a single App Store binary can only talk to one server. That is a
  product question and is recorded as one.

**The unwired-code scan, done properly this time.** An earlier package-level
pass in this session was broken — zsh mangled a glob and every package reported
zero references, which was plainly false. I discarded those numbers. The
function-level scan finds **59 of 1,267** public definitions that nothing else
in `src/` refers to. Two of them I verified by hand before citing:
`setup_logging` and `validate_video` each have one test file and **zero
production callers**. So the shipped app never configures its own logging, and
the server never probes an uploaded file. It does check size, quota and
metadata schema, but it takes width, height, duration and codec from the
client's own claims. My first draft said "uploads are never validated";
checking the route showed that was an overstatement. That is the same integration-gap family as
`feedback/`, `SafetyChecker` and `FeedbackReader`.

The name-based scan also misses a second shape: `scheduling` is an *island*.
Its functions reference each other, so none of them looks orphaned, and
nothing outside the package touches any of it. The audit reports both shapes.

**Deliberately a survey, not a repair.** No wiring, no deletions, no runtime
URL setting, no cost-cap enforcement, no automatic memory compile. Each of
those is a product decision or a tuning decision. That follows the operator's
standing instruction to instrument first and tune on data, and the other
decisions are theirs to make.

**Context from the same morning, before this plan.** Compiling memory on
production for the first time exposed a 244M provenance defect: every session
diagnosis was being labelled `mechanic-verified`. The compile was rolled back
before anything read it, and the fix is in regression as a separate change.
It also surfaced test data on production: two overrides and a fabricated
*"confirmed on the bench"* diagnosis, all written by my Sept 11 verification
script. With the operator's approval, those were deleted, along with their
three test edits on session 9, which they confirmed were logging tests. The
corrections table now holds no rows, and every row it gains from here will be
a real correction.

## 2026-09-17 — Step 0, second pass: the scale is larger than the plan said

The first draft sized the problem by counting names: 59 orphaned public
definitions, plus `scheduling` as a package-level island. **Both methods were
too weak**, and the second pass changed the phase's primary instrument.

Blanking comments and docstrings before counting references raised the
orphan count **from 59 to 78**. Nineteen names had only ever been *described*
elsewhere, never called. The naive count was a false-negative generator, and
false negatives are the direction that hides defects.

Then I checked whether the modules containing those names were imported at
all. **Eight media modules are imported by nothing**, and two more are
imported only by those eight. The package-level island check could never have
seen this, because `media/` as a whole is reachable through the vision
pipeline.

So I walked the import graph from the real entry points instead. **218 of 256
modules are reachable. 38 are not.** That includes most of Track C2 (13
modules), a `reference` package, `i18n` (whose table holds 45 rows nothing can
read), `pricing`, `scheduling`, `workflows` and `core.logging`. About 15% of
the codebase can't be reached from anywhere a user can get to. Most of it sits
under roadmap rows marked ✅.

The one blind spot of static reachability, dynamic imports, was checked
before believing the number. There are three sites (`cli/main.py`,
`migrations.py` `post_apply`, `hardware/simulator.py`), and none of them
reaches the 38.

This is the finding the phase exists for, and it's much bigger than the
evidence that motivated it.

## 2026-09-17 — Step 0, third pass: the server recipe is missing half the server

Looking at the Dockerfile to add ffmpeg, I checked which extras it installs:
`[api,vision,push]`. The AI SDKs are declared only in `ai`, so **a container
built from this file can't call Claude or Whisper at all**, keys or no keys.
The checklist's pip recipe and install.md's production line say exactly the
same thing. Three hand-written copies of the server recipe, all missing the
same extra.

Then, checking whether the API's PDF reports needed `export`: they render with
`reportlab` directly, and **`reportlab` isn't declared anywhere**. It reaches
the dev venv as a dependency of `xhtml2pdf`, from the `export` extra, and the
renderer's own docstring says so: *"reportlab is already a transitive dep
(installed in the project venv)"*. It works in development and fails on any
server.

Phase 209 built a clean-install test for exactly this class of problem, then
tested a venv with no extras and one with `[api]`, and never the combination
a server is actually installed with.

So scope B grew from "add ffmpeg" to "make the server recipe one name and make
it complete". It's the one part of this phase that *can* be verified from
here, because the packaging test installs from a real wheel.
