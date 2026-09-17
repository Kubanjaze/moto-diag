# Phase 209B — What the launch checklist doesn't know

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-17

---

## Goal

Launch readiness was recommended next on 2026-09-17, on the reasoning that
Gate 10 had closed and so Phase 210 was unblocked. **That reasoning was wrong.**
`docs/launch-checklist.md`, written 2026-09-09, says so directly:

> *Phase 210 (launch readiness) is deliberately unstarted — it depends on steps
> 1–6 below.*

Steps 1–6 cover standing up a host, building the Docker image, a privacy
policy, a demo instance, screenshots and TestFlight. Every one of them needs
the operator, and none can be done from a coding session. Phase 210 stays
where it is.

What *can* be done now is make sure that, when the operator works through
those steps, they succeed. The checklist was written the day before the whole
244 series began. Since then the product has gained vision questions, a cost
ledger, per-machine memory and passive capture, and the checklist knows
nothing about any of them. This phase closes that gap, and it runs the audit
that the 244 series kept doing by accident: finding code that was built and
tested but never connected to anything.

Numbered **209B** — an insertion after 209 (packaging) and before 210 (launch),
which is where this work belongs.

## Step 0 — findings

**S0-1. 210 is gated on the operator, not on code.** Stated above. This phase
does not start 210 and does not claim to.

**S0-2. The container can't do the headline feature.** The Dockerfile builds
on `python:3.13-slim` and never installs ffmpeg. `media/ffmpeg.py` resolves
the binary at import and turns its absence into a **503 on every video
upload**. So in a container, the sweep and Ask are both dead on arrival. It
works on the laptop only because Homebrew installed ffmpeg. Docker is still
not installed on this machine, so, like the rest of the Dockerfile (F76),
any fix here can't be verified from this session.

**S0-2b. The server install recipe is missing half the server — in all
three places it's written down.** The Dockerfile installs
`motodiag[api,vision,push]`. The checklist's step 1 says `pip install
"motodiag[api,vision,push]"`. `docs/guide/install.md` line 93, the
production path, says the same. Two things are missing from all three:

- **The `ai` extra.** `anthropic` and `openai` are declared only in `ai`. A
  server built from any of the three recipes has neither SDK, so diagnosis,
  vision, Ask and Whisper **all fail even with the keys set**. `ai` shows up
  only on install.md line 63, the *CLI* line.
- **`reportlab`, which is declared nowhere.** The API's PDF report routes
  (`/v1/reports/{session,work-order,invoice}/{id}/pdf`) render with
  `reportlab` directly. It reaches the dev venv only as a transitive
  dependency of `xhtml2pdf`, from the unrelated `export` extra, and
  `reporting/renderers.py` says so in as many words: *"reportlab is already
  a transitive dep (installed in the project venv)"*. On a server installed
  from any of the three recipes, **every PDF report raises**.

Phase 209's clean-install test checks a venv with no extras and one with
`[api]`, and never the recipe a server is actually installed with. It would
have caught both.

**S0-2c. The image can't be built at all.** The runtime stage runs
`pip install /tmp/*.whl[api,vision,push]`. To `/bin/sh`, `[api,vision,push]`
is a **glob character class**, so `*.whl[…]` matches nothing and is passed
through literally. pip then gets a path containing a real `*` and rejects it:
`ERROR: Invalid wheel filename (wrong number of parts): '*'`. I reproduced
this without Docker: a dummy wheel in a temp directory, the exact line under
`/bin/sh`, and `pip install --dry-run` on what came out. Debian's `dash`
leaves unmatched globs literal the same way. This one would at least fail
**loudly**, at the first `docker build` — which nobody has ever run (F76).
The fix resolves the wheel path first:
`whl="$(ls /tmp/*.whl)"; pip install "${whl}[server]"`.

**S0-3. The deployment env block has no AI keys.** Step 1's env block lists
`MOTODIAG_ENV`, `PUBLIC_BASE_URL`, `BILLING_PROVIDER`, `STRIPE_WEBHOOK_SECRET`
and `API_CORS_ORIGINS`. It doesn't list `ANTHROPIC_API_KEY` (diagnosis,
vision, Ask) or `OPENAI_API_KEY` (Whisper). A server configured from the
checklist would have **every AI feature failing**. `docs/guide/install.md`
mentions ffmpeg zero times.

**S0-4. The privacy wording is now false.** Step 3 says the policy must state
*"that data goes only to the operator's own backend."* The backend sends video
frames and technicians' questions to **Anthropic**, and voice audio to
**OpenAI**. The policy has to say so. Whether the App Store privacy label
changes as a result is the operator's decision, possibly with counsel; this
phase doesn't answer it.

**S0-5. The server address is compiled into the app.** `api/client.ts` takes
the base URL from the caller (tests), then from `Config.API_BASE_URL` (read
from `.env` **at build time**), then falls back to `10.0.2.2:8000`. The user
has no way to change it at runtime. Two consequences:

- A TestFlight build made today points at
  `kerwyns-macbook-air.taila45995.ts.net`, which only the operator's own
  tailnet can reach. Step 4 tells the operator to *"put the server URL and key
  in the App Review notes"*, but there is nowhere in the app for a reviewer to
  enter a URL.
- Step 3 says *"every deployment is the shop's own"*, but an App Store binary
  can only ever talk to **one** server. Self-hosted backends and a single
  published binary don't fit together. That is a product decision, not
  something to settle in code here.

**S0-6. 38 of 256 modules can't be reached — about 15% of the codebase.**
Walking the import graph from the real entry points (`motodiag.cli.main:cli`
from `pyproject.toml`, the `motodiag.api` app factory, and the package root)
reaches **218 of 256 modules**. The other 38 are imported only by each other,
or by nothing:

| package | unreachable | what it is |
|---|---:|---|
| `media` | 13 | most of **Track C2 — Media Diagnostic Intelligence** (96–108): annotation, anomaly detection, coaching, comparative, fusion, realtime, reports, sound signatures, plus spectrogram and audio capture, which only those modules import |
| `reference` | 6 | a reference-data package |
| `i18n` | 4 | translator and repo; the `translations` table has **45 rows** nothing can read |
| `pricing` | 4 | repair plans, estimates, labor rates |
| `knowledge.seed` | 3 | seed modules; seeding actually happens elsewhere |
| `scheduling` | 3 | appointments |
| `workflows` | 3 | workflow templates |
| `cli.registry`, `core.logging` | 2 | command registry; `setup_logging` |

The live media pipeline (vision, photos, ffmpeg, Whisper) *is* reachable.
Next to it sits an audio-intelligence layer that the roadmap marks ✅ across
13 phases and that no entry point can reach.

Dynamic imports were checked, since they are the blind spot of static
reachability. `cli/main.py` `__import__`s top-level packages for a status
table, all of them already reachable. `migrations.py` loads
`knowledge.marques` and `knowledge.models` through `post_apply` strings.
`hardware/simulator.py` loads `hardware.recorder`. **None of these touch the
38.** The instrument still has to treat literal `import_module("…")`,
`__import__("…")` and `post_apply="module:func"` as edges, or it will one day
report a dynamically loaded module as dead.

**S0-6b. Built, tested, never called — inside reachable modules.** Of the
1,267 public top-level definitions in `src/motodiag`, **78 are referenced by
no code anywhere else in `src/`**. Counted without blanking comments and
docstrings the figure is 59; the other 19 names appear elsewhere only in prose.
Some of the 78 are legitimate — test infrastructure, and public API kept on
purpose. Some are this session's recurring defect:

| candidate | why it matters |
|---|---|
| `core/logging.py::setup_logging` | One test file, **zero production callers**. The shipped app never configures its own logging. |
| `media/ffmpeg.py::validate_video` | One test file, zero callers. Uploads *are* checked for size, quota and metadata schema, but the **file is never probed**: width, height, duration and codec come from the client's own metadata, not the bytes. |
| `pricing/repair_plan.py` (8 functions) | Full repair-plan CRUD with no caller. |
| `engine/workflows.py` (4 functions) | Guided no-start, charging and overheating workflows with no caller. |
| `pricing/estimate.py::estimate_issue_cost` | Cost estimation with no caller. |

**S0-7. Memory goes stale.** Phase 244M's compile runs only from
`motodiag memory compile`, and nothing calls it automatically. Unless someone
runs it, the memory that feeds the vision prompt holds whatever was true the
last time someone remembered to.

**S0-8. Nothing caps spend.** `cost_cap_monthly_usd_cents` exists and nothing
reads it (a 244L non-goal). The first real prices are now known: 1¢ for a text
diagnosis, 13¢ for a vision question, 5¢ for a sweep. A deployed shop has no
ceiling.

**S0-9. The corrections stream can't be fed from the phone.** No API route
sets `ai_model_used` (recorded debt, `f697576`). Phase 244N only captures
overrides of AI-authored sessions, so a mobile-only shop produces none.

**S0-10. The checklist's numbers are stale.** It says 4,902 tests (now
6,500+), schema v50 (now 60) and 80 routes (now 81), and its step 0 ("push
three phases") was done long ago.

## Scope

**A. Refresh `docs/launch-checklist.md`.** Correct the stale facts. Add
S0-2 through S0-9 as items, each with an owner and a *done when*. Rewrite
step 4 honestly: the reviewer path it describes doesn't exist yet.

**B. Give the server recipe one name, and make it complete.**
- A new **`server` extra** = `api` + `ai` + `vision` + `push`. The Dockerfile,
  the checklist and install.md all point at `motodiag[server]`. Three
  hand-maintained copies drifted identically, and one name can't.
- **Declare `reportlab` in `api`**, next to the routes that import it. Relying
  on `export` → `xhtml2pdf` → `reportlab` means the API breaks the day the
  CLI switches PDF libraries.
- **Extend Phase 209's clean-install test** with a venv built from
  `motodiag[server]` that imports `anthropic`, `openai` and `reportlab` and
  renders a PDF. This part *is* verifiable here, unlike the container.
- **Install ffmpeg in the Dockerfile's runtime stage**, labelled
  **unverified** next to the existing "never built" warning. Step 2's
  verification gains an explicit `ffmpeg -version` check.

**C. Add the AI keys and ffmpeg to the deployment docs**: the env block and
`docs/guide/install.md`.

**D. Make the integration-gap audit a permanent instrument.**
- Commit the scanner under `tests/support/`. **Module reachability from the
  entry points is the primary check.** It finds dead code at any size, from a
  single module to a 13-module layer, which counting names can't: a name-based
  pass found `scheduling` only by luck and missed the Track C2 layer entirely,
  because `media/` as a whole is reachable. The name-based orphan scan stays
  as the second check, for unused functions *inside* reachable modules, with
  references counted in code only (78 candidates once comments and docstrings
  are blanked, against 59 without, because 19 names appeared only in prose).
- A gate test fails when a **new** unreferenced public definition appears.
  Every known one must sit in an allowlist with a **classification** and a
  **reason** of at least 20 characters, the same discipline as `f9-noqa`.
- Classify all 59 candidates plus the islands as `test-infra`, `public-api`,
  `unwired-feature` or `dead`.

The 244 series found six of these by accident. With the gate, the next one
gets found on purpose.

## Non-goals

Each of these is a decision, not a defect. Each is recorded in the checklist
with its options, and none is settled here.

- **No runtime server-URL setting** (S0-5). It collides with the
  one-binary / self-hosted question, and that is product architecture.
- **No wiring** of repair plans, workflows, scheduling, `setup_logging` or
  `validate_video`. Some of these should obviously be connected, but each is
  its own change with its own risk, and this phase is the survey.
- **No deletions**, not even of anything classified `dead`. Classifying is
  cheap and reversible; deleting isn't.
- **No cost-cap enforcement** (S0-8). What happens to a shop mid-shift when
  it hits the cap is a product call. It is also tuning, and there are four
  cost samples.
- **No automatic memory compile** (S0-7). When it runs, and what it costs to
  run it, need real usage first.
- **No privacy-label decision** (S0-4).

## Verification Checklist

- [ ] The checklist no longer says 4,902 tests, schema v50 or "push three phases"
- [ ] The checklist names ffmpeg, both AI keys, the third-party data flow and the baked server URL
- [ ] Step 4 no longer tells a reviewer to enter a URL the app can't accept
- [ ] A `server` extra exists and is the only server recipe in the docs
- [ ] `reportlab` is declared, in `api`
- [ ] A clean `[server]` venv imports anthropic, openai and reportlab
- [ ] A clean `[server]` venv renders a PDF report
- [ ] Mutation: drop `ai` from `server` → the packaging test fails
- [ ] Mutation: drop `reportlab` from `api` → the packaging test fails
- [ ] The Dockerfile installs `[server]` and ffmpeg, labelled unverified
- [ ] The Dockerfile resolves the wheel path before appending extras (shell-glob bug)
- [ ] That form is proven under `/bin/sh` against a real wheel filename
- [ ] The install guide mentions ffmpeg and both AI keys
- [ ] Reachability from the declared entry points is the primary check
- [ ] Literal `import_module` / `__import__` / `post_apply` strings count as edges
- [ ] The scanner reports unreachable modules and orphaned functions separately
- [ ] All 38 unreachable modules and all 78 orphans are classified, each with a reason of at least 20 characters
- [ ] The gate fails on a newly added unreferenced public function
- [ ] The gate passes on a newly added function that something calls
- [ ] Route handlers and CLI commands are never flagged
- [ ] Mutation: add an orphan → the gate fails
- [ ] Mutation: empty a reason → the gate fails
- [ ] Mutation: remove an unreachable module from the allowlist → the gate fails
- [ ] Mutation: import a dead module from a reachable one → the gate fails (stale entry)
- [ ] Full regression green

## Risks

- **A name-based scanner can be fooled.** A function reached only through
  `getattr`, a string entry point or a plugin registry looks orphaned when it
  isn't. False positives go in the allowlist with the reason. The more
  dangerous case is a false negative: a name that appears in prose (a comment
  or docstring) looks referenced when it isn't. That is the mention-vs-use
  family this project has hit five times, so the scanner matches against code
  with comments and docstrings blanked, using `tests/support/source_guards`.
- **The allowlist can rot into a list of excuses.** Mitigated by requiring a
  classification plus a reason, and by keeping `unwired-feature` entries
  visible in the checklist rather than only in a test.
- **The ffmpeg change stays unverified** until someone builds the image, and
  saying so in the checklist is the most that can be done here.
- **This phase fixes almost nothing directly.** Its value is that launch-day
  surprises get found now and are written down where the operator will read
  them.
