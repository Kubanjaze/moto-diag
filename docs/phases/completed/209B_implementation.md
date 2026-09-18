# Phase 209B — What the launch checklist doesn't know

**Version:** 1.2 | **Tier:** Standard | **Date:** 2026-09-17 (built 2026-09-17; decisions recorded 2026-09-17)

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
- **Declare `reportlab`** in its own `reports` extra, pulled in by `server`.
  Relying on `export` → `xhtml2pdf` → `reportlab` means the API breaks the day
  the CLI switches PDF libraries. *(v1.0 said "in `api`"; see Deviation 7.)*
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

- [x] The checklist no longer says 4,902 tests, schema v50 or "push three phases"
- [x] The checklist names ffmpeg, both AI keys, the third-party data flow and the baked server URL
- [x] Step 4 no longer tells a reviewer to enter a URL the app can't accept
- [x] A `server` extra exists and is the only server recipe in the docs
- [x] `reportlab` is declared, in `reports`, and `server` includes it
- [x] `[api]` alone stays Pillow-free (Phase 209's contract)
- [x] An `[api]`-only PDF request names the missing extra
- [x] A clean `[server]` venv imports anthropic, openai and reportlab
- [x] A clean `[server]` venv renders a PDF report
- [x] Mutation: drop `ai` from `server` → the packaging test fails
- [x] Mutation: drop `reportlab` from `reports` → the packaging test fails
- [x] The Dockerfile installs `[server]` and ffmpeg, labelled unverified
- [x] The Dockerfile resolves the wheel path before appending extras (shell-glob bug)
- [x] That form is proven under `/bin/sh` against a real wheel filename
- [x] The install guide mentions ffmpeg and both AI keys
- [x] Reachability from the declared entry points is the primary check
- [x] Literal `import_module` / `__import__` / `post_apply` strings count as edges
- [x] The scanner reports unreachable modules and orphaned functions separately
- [x] All 38 unreachable modules and all 78 orphans are classified, each with a reason of at least 20 characters
- [x] The gate fails on a newly added unreferenced public function
- [x] The gate passes on a newly added function that something calls
- [x] Route handlers and CLI commands are never flagged
- [x] Mutation: add an orphan → the gate fails
- [x] Mutation: empty a reason → the gate fails
- [x] Mutation: remove an unreachable module from the allowlist → the gate fails
- [x] Mutation: import a dead module from a reachable one → the gate fails (stale entry)
- [x] Full regression green — **6,626 passed, 0 failed**, 25:18 (first run: 2 failed — Deviation 7)

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

---

## Deviations from v1.0

**1. The first orphan scanner made the gate take 52 seconds.** It compiled a
regex per public definition and searched every file with it, roughly 300,000
scans over this tree. It now counts identifiers once per file, and the gate
runs in **3.3 seconds**. The two are equivalent: the gate's "no new orphan"
and "no stale entry" tests pass against the identical allowlist of 47, which
the fast version could only do by finding exactly the same set.

**2. Four allowlist reasons were plausible stories, and three of them were
false.** They were drafted before being checked, then checked one by one:

- `require_intake` was described as "an intake guard never applied". It's
  `get_intake` that raises on a miss.
- The theme formatters were "left unused after the CLI moved to Rich". They
  were *added* in Phase 129, the Rich polish phase.
- `set_bike_role` was said to mean fleet roles "can't be set by any user
  path". They're set when a bike joins a fleet; what nothing does is change
  them afterwards.
- The HEIF probe was said to leave "a failure rather than a clear message".
  I couldn't support that, so it now just says what the probe is.

The ones that held (`_manager` at module level, a second insert path,
`deactivate_shop` exists, per-issue pairing exists) stayed. An allowlist full
of confident fiction is worse than none, because its whole purpose is to be
believed.

**3. "Uploads are never validated" was an overstatement, caught before the
plan was committed.** The upload route checks the size cap (413), the quota
(402) and the metadata schema (422). What it never does is probe the file,
so width, height, duration and codec come from the client's own claims.
Corrected in the plan, the log and the allowlist.

**4. The first PDF test was named for more than it checked.**
`test_a_pdf_report_renders` built the renderer and never rendered anything.
It now renders a document in the clean `[server]` venv and asserts the output
starts with `%PDF-`. That's why mutation M1 below means something.

**5. Two edit scripts wrote nothing, and said so.** One anchored on a
comment-stripped view of `pyproject.toml`; the other was an unquoted heredoc
that mangled backslashes. Both asserted their anchor before writing, so both
stopped instead of guessing. Redone against the exact text.

**6. The Dockerfile fix grew by one bug.** Scope B said "install ffmpeg".
Reading the install line to do that showed the image could never have been
built at all: `/tmp/*.whl[api,vision,push]` is a shell glob class, and pip
rejects the literal `*`. Reproduced under `/bin/sh` and fixed the same way.

**7. The first place I declared `reportlab` broke a Phase 209 contract, and
Phase 209's tests caught it.** I first put `reportlab` in `api`, next to the
routes that import it. The full regression came back with **2 failures**,
both in Phase 209's `[api]`-only tests. `reportlab` requires Pillow, and
Phase 209 had made `[api]` deliberately Pillow-free, so that photo processing
degrades with a message rather than requiring imaging libraries across the
whole API. Declaring it there pulled Pillow into every `[api]` install.

The fix is a dedicated **`reports`** extra, which `server` includes. The PDF
renderer now degrades the same way photos do: its error names the `reports`
extra and `motodiag[server]`. A new `[api]`-only test pins that behaviour, and
a new static test fails if `reportlab` or Pillow is ever declared directly in
`api` (mutation P6).

Scanning `src/` for recipes, which the first version didn't do, then found
**two more places recommending an API with no AI**. Both were error messages:
`motodiag serve` said *"run `pip install 'motodiag[api]'`"*, and the photo
pipeline said `motodiag[api,vision]`. Both now point at `[server]`. The
recipe guard covers every `.py` file under `src/motodiag`, because these were
sitting exactly where a docs-only scan couldn't see them.

**8. v1.2, decisions recorded after close, and one result corrected.** After
the phase closed, the operator decided every open item in the checklist's
Decisions section; they're recorded below under **Decisions**. The
decisions triage also found that one of the 33 `unwired-feature` entries,
`create_extracted_symptom`, had been wired in by Phase 195 Commit 0 and
replaced by Phase 195B Commit 1. That makes it superseded, not unreachable.
It's reclassified in the allowlist, and the Results count below now reads 32.

## Results

| | |
|---|---|
| Modules reachable from entry points | **218 / 256** |
| Unreachable modules | **38** (~15%), every one classified |
| Orphans inside live modules | **47** (78 in total; 31 sit inside unreachable modules and aren't double-counted) *— corrected by Phase 244U: the scanner could not see a name whose only references were a package re-export, because an `__init__` writes it twice (the import alias and `__all__`). With that fixed the live count is 66. `SafetyChecker` is the name that proved it: Phase 241 recorded it had no caller and this gate never listed it.* |
| Classification | `unwired-feature` **32** · `public-api` 21 · `substrate` 16 · `test-infra` 9 · `superseded` **7** *(33 / 6 at close; #30 reclassified in v1.2)* |
| Largest unwired block | Track C2 audio intelligence — 10 modules, marked ✅ on the roadmap |
| Gate tests | **107**, in 3.3s (from 52s) |
| Recipes corrected in source | 2 error messages (`serve`, photo pipeline) that recommended an API without AI |
| Packaging tests added | 10 — 6 static, 4 in clean venvs (`[server]` ×3, `[api]` ×1) |
| Mutations | **11 of 11 caught** (5 gate, 6 packaging) |
| `server` extra | added; self-reference proven to resolve from a local wheel |
| `reportlab` | declared in its own `reports` extra, included by `server` (**not** `api` — see Deviation 7) |
| Dockerfile | glob bug fixed (**verified** under `/bin/sh`); ffmpeg added (**unverified** — no Docker) |
| Regression | **6,626 passed, 0 failed**, 25:18 |
| Launch checklist | 257 → 377 lines; four silent-failure blockers and five decisions added |
| Install guide | server recipe, AI keys and ffmpeg; a false "verified end to end" claim corrected |

**Mutations**

| | mutation | caught by |
|---|---|---|
| G1 | a new orphan in live code | `test_no_new_orphan` |
| G2 | a reason emptied to "tbd" | `test_classification_and_reason` |
| G3 | an unreachable module dropped from the list | `test_no_new_unreachable_module` + scale pin |
| G4 | a dead module wired up | `test_no_stale_unreachable_entry` + scale pin |
| G5 | a substrate that stops naming its phase | `test_a_substrate_names_the_phase_it_waits_for` |
| P1 | `reportlab` removed from `reports` | the static check **and a real PDF render failing in a clean venv** |
| P2 | `ai` removed from `server` | the static check **and a real SDK import failing in a clean venv** |
| P3 | a doc recipe back to `[api,vision,push]` | `test_no_recipe_installs_the_api_without_ai` |
| P4 | ffmpeg dropped from the Dockerfile | `test_the_dockerfile_installs_ffmpeg` |
| P5 | a recipe names an extra that doesn't exist | `test_every_recipe_names_only_real_extras` |
| P6 | `reportlab` put back in `api` — **my own first mistake** | the static Pillow-free check **and Phase 209's real `[api]` venv** |

P1 and P2 are the ones that justify the phase. Each defect gets reproduced
in a real, clean install, and the test fails on it. The Phase 209 test that
already existed covered no extras and `[api]` alone, so the only combination
it never tried was the one every server actually uses.

**Key finding.** About 15% of the backend can't be reached from anything a
user can run, and most of it sits under roadmap rows marked complete. The
roadmap was recording *built and tested*; nothing was recording *reachable*.
The same blind spot showed up one level down in packaging. Every server
recipe was missing the extra that makes it an AI product, and the PDF
dependency existed only because a development environment happened to have
it. Each problem stayed invisible for the same reason: every check looked at
its own piece and never at the path a user actually takes. The gate added
here checks exactly that path, and the clean-install test does the same for
the thing that actually gets shipped.

---

## Decisions — recorded 2026-09-17

The operator decided every open question in the launch checklist's
**Decisions** section on 2026-09-17. This section is the record. The
checklist marks each one resolved and points here.

| # | Decision | Status | Tracked in |
|---|---|---|---|
| 1 | Runtime server-URL setting in the app | Decided; implementation in progress | moto-diag-mobile |
| 2 | Hosting: Fly.io + SQLite volume + Litestream; site on Vercel | Decided — **domain TBD** | F64 (deploy), F81 (Postgres) |
| 3 | Which server is down, and what "no backups" covers | Answered; `data/` backed up | — |
| 4 | Test sessions 8 and 9 | **Done** — deleted | this record |
| 5 | Spending cap: $25/month per shop | Decided | F78 |
| 6 | Memory refresh on session close | Decided | F79 |
| 7 | Privacy policy reflects collected data | Decided — owner **Kerwyn** | F80 |
| 8 | Unreachable features: don't build; fix the gate | Decided; gate change **done** | F82, F83; CLAUDE.md gate item 6 |

### 1. Server address — runtime setting (blocked launch)

- Add a runtime server-URL setting to the app. **Rejected alternatives:**
  - *One hosted service for all shops* — we become the host forever, with
    every shop's data on our box.
  - *A separate build per shop* — a rebuild and a store resubmission for
    every customer.
- **Default:** `https://api.<domain>`, read from config (`API_BASE_URL` at
  build time), **never a string literal in source** (SSOT rule). The domain
  is TBD until it's bought this week; `.env.example` stays
  `api.<your-domain>`.
- **Override:** a field on the Settings screen. On save, a **live health
  check** runs against the entered URL: `GET /healthz` must return 200 with
  `status: "ok"` and a `schema_version`.
- **Plain http is rejected** except for a dev allowlist — `localhost`,
  `127.0.0.1` and `10.0.2.2` (the Android emulator's route to the host) — kept
  in **one constant**, not spread across checks.
- **No server set** → *"No server set — go to Settings."* Production builds
  must have `API_BASE_URL` set at build time, enforced by a **build-time
  assertion**, so a normal user never sees that screen.
- **Regression guard (required):** a test proving the API client reads the
  stored setting, not the compiled constant.
- Until the domain exists, the operator sets the Tailscale address on their
  phone by hand.

### 2. Hosting

- **Site + waitlist:** Vercel, at the bare domain.
- **Backend:** **Fly.io**, at `api.<domain>`. Vercel isn't the backend host:
  it has serverless timeouts, cold starts and no persistent process, and the
  API runs video analysis, Whisper and uploads, and holds a database.
- **Database:** **SQLite on a Fly persistent volume, replicated continuously
  by Litestream to object storage from day one.**
- **Revised from "managed Postgres with automatic backups".** This backend
  has no Postgres support: 81 direct `sqlite3` uses, 58 migrations written as
  SQLite DDL (including table-rebuild patterns), and no Postgres driver or
  ORM. Moving to Postgres is a port, not a hosting setting, and not a launch
  task. It's filed as **F81, "Postgres port — revisit when concurrent shops
  > 1"**.
- **F64 is now the deploy ticket.** The checklist's step 1 was written for
  the home-desktop plan, and that plan is superseded.
- **Domain:** TBD.

### 3. Server down / backups — answered before any other work

- **Down:** the development API on the operator's laptop (`motodiag serve`
  on `127.0.0.1:8000`) and its Tailscale exposure, shut down on 2026-09-16
  at 11:31 on request. **No deployed server has ever existed.**
- **"No leftover backups"** meant only the temporary database copies taken
  before table-rebuilding migrations. At that point **nothing backed the
  machine up**: no Time Machine destination, and `data/` is gitignored. The
  real bike videos, the first real cost events and the first Q&A existed in
  one place.
- **Resolved:** the operator zipped `data/` to iCloud Drive
  (`motodiag-data-2026-09-17.zip`). Before item 4 ran, the archive was
  checked: `motodiag.db` plus all six videos, sizes matching the live files,
  zip integrity OK. For launch, the answer is Litestream (decision 2).

### 4. Test sessions 8 and 9 — deleted

- Both were created by Claude running `motodiag diagnose quick` on
  2026-09-10 and 2026-09-11, using symptoms paraphrased from session 6's
  real complaint. As a result, vehicle 10's memory held that complaint
  three times.
- The argument that session 9 held "the only structured AI diagnosis in the
  database" was **rejected**: a diagnosis can be regenerated in minutes.
- **Done:** both sessions printed in full (see the 209B phase log), then
  deleted, together with the **5 memory facts** compiled from them.
  `memory_facts` has no foreign key to sessions, so those facts would
  otherwise have gone stale. Memory was then rebuilt from scratch and came to
  **37 facts**, the same as the targeted delete. Only `diagnostic_sessions`
  (8 → 6) and `memory_facts` (42 → 37) changed. **The text-diagnosis cost row
  was kept** because it records real spend and isn't linked to a session.
- Vehicle 10's prompt history is now its one real complaint.

### 5. Spending cap — F78

- **$25/month per shop**, enforced through `shop_cost_this_month`, which is
  #28 in the triage below and currently has no caller at all. Not a launch
  blocker.
- Known per-call costs: about **1¢** per text diagnosis, **13¢** per video
  question, and **5¢** per automatic sweep.

### 6. Memory refresh — F79

- Recompile a machine's memory **when its session closes**. Not a launch
  blocker.

### 7. Privacy policy — F80 (owner: Kerwyn)

- Collected data must be reflected in the policy before store submission:
  technicians' questions and answers, corrections and who made them, and the
  frames and audio sent to Anthropic and OpenAI.

### 8. Unreachable features — triaged, not built

- **Nothing on the list gets built now.**
- **#30 dropped.** `create_extracted_symptom` was wired in and later
  replaced, so it's now `superseded`. That leaves **32** genuinely unwired
  features.
- **The real fix is the gate.** The phase completion checklist in
  `CLAUDE.md` gained item 6: *a user-reachable entry point (CLI command or
  API route) exists and is exercised by a test* (workspace-docs `1c21fe0`,
  with a dated Change Log entry).
- **F82:** the 22 cause-A items (media, pricing and workflow islands) —
  wire or delete, decided per phase.
- **F83:** the 10 cause-B items (dead repo methods) — delete unless a caller
  is planned. #28 has one: F78.

**Cause A — built before any way to use it existed, and no later phase came
back for it (22).** All of these date from 2026-04-15/16. Phases 97–107
landed as a single 9,552-line commit that day, and the API didn't exist
until 2026-04-22. The checklists for those phases have no item requiring a
user entry point; "done" meant "N tests pass".

| # | Feature | File |
|---|---|---|
| 1 | Engine-sound spectrogram | `media/spectrogram.py` |
| 2 | Audio anomaly detection | `media/anomaly_detection.py` |
| 3 | Audio capture / preprocessing | `media/audio_capture.py` |
| 4 | Audio-capture coaching | `media/coaching.py` |
| 5 | Before/after audio comparison | `media/comparative.py` |
| 6 | Multimodal evidence fusion | `media/fusion.py` |
| 7 | Real-time audio monitor | `media/realtime.py` |
| 8 | Media-enhanced reports | `media/reports.py` |
| 9 | Engine sound-signature database | `media/sound_signatures.py` |
| 10 | Video annotation | `media/annotation.py` |
| 11 | Structured logging + audit trail | `core/logging.py` |
| 12–15 | Guided no-start / charging / overheating workflows + step engine | `engine/workflows.py` |
| 16–19 | Pricing package, estimates, labor rates, repair plans | `pricing/*` |
| 20–22 | Pricing models (`LaborRateType`, `PlanItemType`, `RepairPlanStatus`) | `core/models.py` |

**Cause B — the repo or helper layer was written wider than the wired
feature that used it (10).** The features themselves are live. These
individual methods from their "Commit 0" or CRUD layers never got a caller.

| # | Method | File | Planned caller |
|---|---|---|---|
| 23 | `validate_video` — probe an uploaded file | `media/ffmpeg.py` | — |
| 24 | `extract_audio` | `media/ffmpeg.py` | — (feeds the cause-A audio layer) |
| 25 | `heif_available` | `media/photo_pipeline.py` | — |
| 26 | `list_issue_photos` | `shop/wo_photo_repo.py` | — |
| 27 | `whisper_available` | `media/whisper_client.py` | — |
| 28 | `shop_cost_this_month` | `shop/cost_repo.py` | **F78 (spending cap)** |
| 29 | `soft_delete_extracted_symptom` | `shop/extracted_symptom_repo.py` | — |
| 31 | `reactivate_shop` | `shop/shop_repo.py` | — |
| 32 | `set_bike_role` | `advanced/fleet_repo.py` | — |
| 33 | `update_fleet_description` | `advanced/fleet_repo.py` | — |

Numbering is kept from the original triage, so #30 is absent here.

**The common thread: the phase completion gate checked *tested and
documented*, never *reachable*,** and both causes passed it. Gate item 6 now
checks for it.
