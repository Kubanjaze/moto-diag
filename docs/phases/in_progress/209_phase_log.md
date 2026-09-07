# Phase 209 — Packaging + distribution — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-07 | **Completed:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag` + mobile, branch `phase-209-packaging`

---

### 2026-09-07 — Plan v1.0 + Step 0 audit

- **Step 0 was done by building the artefact, not by reading about it.**
  Built a wheel, made a clean venv, installed, ran `motodiag --version`.
  It crashed on the first line: `ModuleNotFoundError: No module named
  'fastapi'`. Not one broken command — the CLI cannot start at all on a
  `pip install motodiag`.
- **Three defects, all in metadata that nothing checks:**
  1. `auth/__init__.py:50` imports `deps`, which imports `fastapi` at
     module level. `fastapi` is an `api` extra, deliberately — the
     design clearly intends a light CLI-only install. One eager import
     makes the whole product require an optional extra. Narrow, not
     systemic: `anthropic`, `openai`, `httpx`, `jwt`, `cryptography`
     and `uvicorn` are all already lazy.
  2. `PROJECT_ROOT` is four parents up from `core/config.py`, which is
     the repo root in a checkout and `<venv>/lib/python3.14` in an
     install. Confirmed: `db_path` resolved to
     `<venv>/lib/python3.14/data/motodiag.db`. A shop's data would live
     inside their virtualenv.
  3. `package-data` declares three of the four data directories. The
     source tree has 19 non-`.py` files; the wheel has 16. The missing
     three are the entire adapter-compatibility knowledge base.
- **Why 4,879 passing tests caught none of it:** every test runs against
  the source tree, where `PROJECT_ROOT` is right, the data files are on
  disk, and the dev venv has every extra. The suite answers "does the
  code work". Nothing asked "does the thing we hand people work."
  That is the same shape as Phase 208's finding one phase later — the
  tests cover the halves, not the seam between the product and its
  distribution.
- **Roadmap row "standalone binary" — recommending `pipx`, not
  PyInstaller.** Freezing a Click app with 24 command groups, five
  optional extras and SQLite data means a fragile ~100 MB per-platform
  artefact plus macOS code signing. `pipx install motodiag` already
  gives an isolated CLI on the PATH without touching system Python.
  Recorded as a decision with reasoning rather than a silently skipped
  row.
- **Play Store will be answered honestly, not invented.** Android has
  not been built since iOS became the shipped target and Phase 208
  documented it as unverified.

### 2026-09-07 — Built. Five defects, not three, and the worst one shipped silently.

- **`pip install motodiag` produced a product that could not start.**
  Fixed by deferring `motodiag.auth.deps` behind a PEP 562
  `__getattr__`, so the CLI imports the repo layer without dragging in
  a web framework that lives in an optional extra.
- **The seed knowledge base was never in the package** — the defect the
  audit's three findings would have left in place. `db init` loads DTCs,
  symptoms and ~6,600 known issues from the repo's `data/` directory,
  which no wheel has ever contained; on an installed copy every load
  guard silently found nothing and the command printed **"Database
  ready."** The knowledge base is the product. 69 JSON files (1.5 MB)
  moved into `src/motodiag/knowledge/seed/`, and `db init` now exits
  non-zero saying the build is incomplete rather than claiming success
  over an empty database.
- **`motodiag serve` could not start on an `[api]` install** either:
  `media/photo_pipeline.py` imported Pillow at module level and both
  `api/errors.py` and `routes/photos.py` import it at load time, so the
  API died before binding a port. Pillow is in `vision`. Now resolved at
  call time behind `PillowUnavailableError`, which names the extra — the
  API serves everything else and fails only where photos are processed.
- **The database was going to live inside the user's virtualenv.**
  `PROJECT_ROOT` is four parents up from `core/config.py`: the repo root
  in a checkout, `<venv>/lib/python3.14` in an install. Now a real user
  data directory per platform, with the source-checkout path deliberately
  unchanged so no development database moved.
- **`package-data` had drifted** — `hardware.compat_data` was never
  declared, so the adapter knowledge base was missing from every
  installed copy. Rather than just adding the line, a test now walks
  every non-`.py` file under `src/` and asserts it reaches the wheel.
  16 data files → 88.
- **The guard was proven before it was trusted.** Restoring the eager
  `auth.deps` import broke `test_version_runs_without_any_extra` and
  `test_help_lists_the_command_groups`. 23 packaging tests: build a
  wheel, install into a throwaway venv with **no extras**, run the
  product, and separately confirm FastAPI and Pillow are genuinely
  absent so nothing passes by accident.
- **One of my own tests was wrong in a useful way.** It asserted
  `len(app.routes) > 50` and read 21 on the clean install — which looked
  like catastrophic router loss and was not. FastAPI 0.141 stopped
  flattening included routers into `app.routes`; `openapi()["paths"]`
  still returned all 80. The dev venv pins 0.136, a fresh install
  resolves 0.141, because `pyproject.toml` says `fastapi>=0.110`. The
  assertion now tests the OpenAPI contract; the version spread is F77.
- **Collateral, caught and fixed:** moving the seed data meant rewriting
  71 test files. The mechanical pass missed `tests/test_pricing.py`,
  which also used `DATA_DIR / "pricing"` (test fixtures, not shipped
  data), leaving a `NameError` in 24 tests. Caught by regression, fixed,
  and every touched file scanned for the same shape.
- **Docker: written, never built.** Docker is not installed here, so
  `docker build` has never run. Everything the image *does* was verified
  outside a container — wheel plus `api` extra installs, `motodiag
  serve` starts, `/healthz` and `/v1/version` answer 200. The Dockerfile,
  compose file and install guide each say so in their own text, and it
  is filed as **F76** rather than left as an implied claim.
- **Roadmap rows answered honestly:** "standalone binary" is `pipx`, not
  PyInstaller, with the reasoning in the install guide — a frozen Click
  app with 24 groups, five extras and 1.5 MB of data buys a fragile
  ~100 MB per-platform artefact plus notarisation to deliver what pipx
  already does. Play Store is unscoped: Android has not been built since
  iOS became the shipped target.
- **Regression 4902 / 0. F9 lint clean.**
- **Key finding: the suite proved the code worked and said nothing about
  the product.** 4,879 tests passed against a distribution that could
  not start, could not find its own knowledge base, and would have
  written a shop's database inside a virtualenv — because every one of
  them ran in an environment no user will ever have. Same lesson as
  Phase 208 one phase later, and now nameable: **the tests cover the
  code, not the boundary between the code and the world.** Docs crossed
  one boundary, packaging crossed another, and each found what the other
  could not. The uncrossed one is deployment — F64 and F76.
