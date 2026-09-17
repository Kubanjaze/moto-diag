# Phase 209B — What the launch checklist doesn't know — phase log

**Status:** ✅ Complete
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

## 2026-09-17 — Built

**The gate.** Walking the import graph from the declared entry points and
the API factory finds **38 unreachable modules**. Counting references in code
only finds **47 orphaned public definitions** inside the reachable ones. All
85 are classified in `tests/support/integration_gaps_allowlist.py`, and the
gate fails in both directions: something new becomes unreachable, or something
listed gets wired up and its entry goes stale. The second direction is what
stops the list turning into a set of excuses.

The first version took **52 seconds**: a regex compiled per definition and run
over every file, roughly 300,000 scans. Counting identifiers once per file
brought it to **3.3 seconds** and produced the identical 47. Five mutations,
five caught.

**Checking my own reasons turned out to matter as much as the scan.** Several
allowlist reasons were drafted as plausible explanations and then checked
before commit. Three were simply false: `require_intake` isn't a guard; the
theme formatters were *added* in the Rich phase, not left behind by it; fleet
roles *are* set, just never changed afterwards. A fourth I couldn't support.
Earlier the same day, "uploads are never validated" had gone the same way:
the route checks size, quota and schema, and what it never does is probe the
file. **An allowlist exists to be believed**, so every sentence in it had to
be checked, not just the counts.

**Packaging.** A `server` extra now names the whole server, `reportlab` is
declared where it's imported, and the Dockerfile resolves its wheel path
before appending extras. That last one was a separate bug found while doing
the ffmpeg change: the image had never been buildable, because
`*.whl[api,vision,push]` is a shell glob class and pip rejects a literal `*`.
Reproduced and fixed under `/bin/sh`. ffmpeg itself is added but unverified,
since there's still no Docker here.

**The two mutations that justify the phase.** Remove `reportlab` from `api`,
or `ai` from `server`, and a clean venv built from the real wheel **genuinely
fails**: the PDF won't render, and the SDKs won't import. The Phase 209 test
already in the repo installed no extras and `[api]` alone, which were never
the recipe a server uses. This test builds that recipe.

**One of my own tests was named for more than it did.**
`test_a_pdf_report_renders` built the renderer and never rendered anything,
and it would have passed P1 anyway. Caught while writing the mutation plan,
before any mutation ran. It now renders a document and checks the `%PDF-`
header.

**Docs.** The launch checklist grew from 257 to 377 lines. It now opens with
the four silent-failure blockers and has a new **Decisions** section: one
binary or one server per shop, a spending ceiling, when memory refreshes,
captured-data privacy, and the 33 unreachable features. The install guide's
"verified end to end" claim is corrected; the route it described couldn't run
any AI feature.

## 2026-09-17 — Regression red: my reportlab placement broke Phase 209's contract

**First full run: 2 failed, 6,622 passed.** Both failures were in Phase 209's
`[api]`-only packaging tests. I had declared `reportlab` in `api`, next to the
routes that import it, and `reportlab` requires Pillow. Phase 209 had made
`[api]` Pillow-free on purpose, so photo processing degrades with a message
instead of the whole API needing imaging libraries. My change pulled Pillow
into every `[api]` install, and the tests that exist to protect that contract
caught it immediately.

The fix is `reportlab` in its own `reports` extra, which `server` includes.
The PDF renderer now fails the way photos do, naming the extra to install. A
new mutation (P6) puts `reportlab` back in `api` and is caught twice.

Widening the recipe guard to scan `src/` found **two more recipes for an API
with no AI**, both in error messages. `motodiag serve` told a missing-uvicorn
operator to install `motodiag[api]`, and the photo pipeline recommended
`motodiag[api,vision]`. Those are the messages someone reads while setting up
a server, and both would have led them to exactly the broken install this
phase exists to remove. A docs-only guard could never have seen them.

**Second run: 6,626 passed, 0 failed, 25:18.**
