# Phase 209 — Packaging + distribution

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

`pip install motodiag` currently produces a CLI that **cannot start** —
not one broken command, all of them, on the first line of output. The
Step 0 audit built a wheel, installed it into a clean venv, and ran
`motodiag --version`: `ModuleNotFoundError: No module named 'fastapi'`.
This phase makes the distributed artefact work, adds the container and
release paths, and lands a test that installs the built wheel into a
throwaway environment and runs it — because every defect below was
invisible to 4,879 passing tests, which all run against the source tree.

CLI: `python -m build` then `pip install dist/*.whl` in a clean venv;
the guard is `pytest tests/test_phase209_packaging.py`.

Outputs:
- Fixed `pyproject.toml` packaging metadata + `MANIFEST.in`
- Lazy FastAPI boundary so the CLI installs without the `api` extra
- Platform-correct user data directory
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`
- `docs/guide/install.md` — install paths for each kind of user
- `docs/releasing.md` — the release runbook
- `tests/test_phase209_packaging.py` — the clean-install guard

## Existing-code audit (Step 0, per CLAUDE.md)

Nouns audited: `Dockerfile`, `docker-compose`, `MANIFEST.in`,
`setup.py`, `.github/workflows`, `*.spec`, `package-data`,
`build-system`, `PROJECT_ROOT`, `DATA_DIR`.

**Greenfield for artefacts, but the existing metadata is wrong.**
Nothing exists: no `Dockerfile`, no `.dockerignore`, no
`docker-compose.yml`, no `MANIFEST.in`, no `setup.py`, no CI workflows,
no PyInstaller spec. `[build-system]` is present and correct
(setuptools ≥ 68). What the audit found instead is that the package
metadata that *does* exist is broken in three ways, each verified by
building and installing rather than by reading:

**1. The CLI cannot start on a base install — every command, immediately.**
`src/motodiag/cli/main.py` imports `cli.apikey`, which imports
`motodiag.auth.api_key_repo`. Importing that submodule executes
`motodiag/auth/__init__.py`, whose line 50 imports `motodiag.auth.deps`,
which imports `fastapi` at module level. `fastapi` is in the `api`
extra, not the base dependencies — deliberately, since the design
clearly intends a light CLI-only install (`api`, `ai`, `push`,
`hardware`, `vision` are all extras). So the one eager import at
`auth/__init__.py:50` makes the entire product depend on an optional
extra. Only `fastapi` (and `PIL`, in `media/photo_pipeline.py`) are
imported eagerly; `anthropic`, `openai`, `httpx`, `jwt`, `cryptography`
and `uvicorn` are already lazy, so this is a narrow miss rather than a
pattern.

**2. The default database lands inside the virtualenv's library
directory.** `core/config.py:14` computes
`PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent`,
which is correct for a source checkout (`src/motodiag/core/` → repo
root) and wrong for an installed package, where four parents up from
`site-packages/motodiag/core/config.py` is `<venv>/lib/python3.14`.
Confirmed on the clean install: `db_path` resolved to
`<venv>/lib/python3.14/data/motodiag.db`. A user's shop data would live
inside their virtualenv — deleted by a rebuild, absent after an
upgrade, and in a system-wide install, not writable at all.

**3. Three data files never reach the wheel.**
`[tool.setuptools.package-data]` declares `hardware.scenarios`,
`advanced` and `advanced.data` but not `hardware.compat_data`. The
source tree has 19 non-`.py` files; the built wheel contains 16. The
missing three are `adapters.json`, `compat_matrix.json` and
`compat_notes.json` — the entire adapter-compatibility knowledge base,
so `motodiag hardware compat seed` and `compat recommend` fail on any
installed copy. This is the same class as (1): a hand-maintained list
that nothing checks against reality.

**Why the tests did not catch any of this:** every one of the 4,879
tests runs against the source tree, where `PROJECT_ROOT` is right, the
data files are on disk, and the dev venv has every extra installed. The
tests answer "does the code work"; none of them asks "does the artefact
we hand people work."

## Logic

1. **Fix the FastAPI boundary.** Give `motodiag/auth/__init__.py` a
   PEP 562 module-level `__getattr__` so the `deps` names resolve
   lazily. The CLI then imports the repo layer without dragging in the
   web framework, and `from motodiag.auth import get_current_user`
   still works for the API. Same treatment for `PIL` if the clean-venv
   run shows it on a CLI path.
2. **Fix the data directory.** Resolve the user data dir by platform —
   `~/Library/Application Support/motodiag` on macOS,
   `$XDG_DATA_HOME`/`~/.local/share/motodiag` on Linux — when the
   package is installed, while keeping the repo-root `data/` when
   running from a source checkout, so existing development databases do
   not move underfoot. `MOTODIAG_DB_PATH` continues to override.
3. **Fix package data, then stop hand-maintaining it.** Add
   `hardware.compat_data`, and add a test that walks every non-`.py`
   file under `src/motodiag/` and asserts it appears in a built wheel.
   Declaring data files is exactly the kind of list that drifts.
4. **Docker.** A multi-stage image that installs the wheel with the
   `api` extra and runs `motodiag serve`, a `.dockerignore` that keeps
   the build context off the 275 KB history docs and the local
   database, and a compose file with the data volume and environment
   a real deployment needs — including the `MOTODIAG_BILLING_PROVIDER`
   Phase 207 made a startup requirement in prod.
5. **Install documentation** for the three kinds of reader: a mechanic
   who wants the CLI (`pipx`), someone running the API (Docker), and a
   developer (source checkout). Written per Phase 208's rule that
   documented commands get executed.
6. **Release runbook** — version bump in one place, build, verify,
   publish, tag; plus the mobile half's real state.
7. **The guard.** `tests/test_phase209_packaging.py` builds the wheel,
   installs it into a fresh venv with **no extras**, and runs the CLI.
   Marked slow and skippable, but run in this phase's regression.

## Key Concepts

- **PEP 562** — module-level `__getattr__(name)` for lazy submodule
  attribute resolution; the mechanism that lets `motodiag.auth` expose
  FastAPI-dependent names without importing FastAPI to do it.
- `importlib.metadata.version()` / `PackageNotFoundError` — already the
  version source since Phase 208; also the cleanest signal for
  "installed vs source checkout", though the direct test is whether
  `PROJECT_ROOT/pyproject.toml` exists.
- `python -m build` → `dist/*.whl` + `dist/*.tar.gz`; `zipfile` to
  introspect the wheel's `RECORD` for the data-file assertion.
- `venv.EnvBuilder` / `subprocess` for the clean-install test — the
  install must happen outside the dev environment or it proves nothing.
- Docker multi-stage: build the wheel in a builder layer, `pip install`
  the wheel into a slim runtime layer, so no build toolchain ships.
- **`pipx` over PyInstaller** for the "standalone binary" roadmap item.
  A frozen binary for a Click app with 24 command groups, optional
  extras and SQLite data means a fragile ~100 MB artefact per platform
  and a code-signing requirement on macOS. `pipx install motodiag`
  already delivers what the roadmap item wants — an isolated CLI on the
  PATH without touching system Python. Recommended as the answer, with
  the reasoning recorded rather than silently skipping the row.

## Verification Checklist

- [ ] `pip install dist/*.whl` into a venv with **no extras**, then
      `motodiag --version`, `motodiag --help`, `motodiag db init`,
      `motodiag code P0115` all succeed
- [ ] `motodiag hardware compat list` works on the installed copy
      (the missing-data-files case)
- [ ] Default `db_path` on an installed copy is a user data directory,
      not inside the venv
- [ ] A source checkout still uses the repo-root `data/` — no existing
      development database moves
- [ ] Every non-`.py` file under `src/motodiag/` appears in the wheel —
      asserted, not counted by hand
- [ ] The guard fails when the fix is reverted
- [ ] `docker build` succeeds and the container answers `/healthz`
- [ ] The image does not contain the local database or the phase docs
- [ ] Backend regression green; F9 lint clean

## Risks

- **The clean-install test is slow and network-dependent.** Building a
  wheel and creating a venv takes tens of seconds; installing extras
  would hit PyPI. It installs the wheel with no extras and no other
  network dependency, and is marked so it can be deselected — but a
  guard that is routinely skipped is a guard that is not running, which
  is the failure mode to watch.
- **Changing the default data directory moves people's data.** The
  source-checkout path is deliberately unchanged for exactly this
  reason, but anyone who has already `pip install`-ed and accumulated a
  database inside their venv would see a new empty one. Given the
  install is currently incapable of starting, nobody can be in that
  position — worth stating plainly rather than assuming.
- **Docker is written and built here, not deployed.** It answers
  `/healthz` locally. Whether it survives a real host, TLS termination
  and a proxy is F64's question and is not settled by this phase.
- **Play Store is not addressed.** Android has not been built since iOS
  became the shipped target and is documented as unverified. Claiming a
  Play Store path would be inventing one; the roadmap row is answered
  honestly instead.
