# Phase 209 — Packaging + distribution — Phase Log

**Status:** 🔨 In progress
**Started:** 2026-09-07
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
