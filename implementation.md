# MotoDiag Phase 01 — Project Scaffold + Monorepo Setup

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-15

## Goal
Establish the moto-diag monorepo foundation: Python package structure, pyproject.toml with dependencies, CLI entry point, and the directory skeleton for all 8 tracks. This phase produces a runnable `motodiag` CLI that prints version info and verifies the package structure is importable.

CLI: `python main.py --version` / `python main.py --help`

Outputs:
- Working monorepo with all package directories
- `pyproject.toml` with base dependencies
- `main.py` CLI entry point
- All `__init__.py` files with package metadata
- `.gitignore`, `.env.example`, `README.md`

## Logic
1. Create `moto-diag/` project directory at `C:\Users\Kerwyn\PycharmProjects\moto-diag\`
2. Create `pyproject.toml` with:
   - Project metadata (name, version, description, author)
   - Base dependencies: `click`, `rich`, `pydantic`, `pydantic-settings`
   - Optional dependency groups: `[dev]` (pytest, ruff), `[api]` (fastapi, uvicorn), `[hardware]` (pyserial)
   - Entry point: `motodiag = "motodiag.cli.main:cli"`
3. Create package structure under `src/motodiag/`:
   - `core/` — config, database, base models
   - `vehicles/` — vehicle registry
   - `knowledge/` — DTC codes, symptoms, known issues
   - `engine/` — AI diagnostic engine
   - `cli/` — terminal interface
   - `hardware/` — OBD adapter interface (stubbed)
   - `advanced/` — fleet, maintenance, prediction (stubbed)
   - `api/` — REST API (stubbed)
4. Create `main.py` with Windows UTF-8 fix, argparse fallback, package import verification
5. Create `data/` subdirectories: `dtc_codes/`, `vehicles/`, `knowledge/`
6. Create `tests/` with `conftest.py`
7. Create `.gitignore`, `.env.example`, `README.md`
8. Create `.venv`, install in editable mode, verify imports

## Key Concepts
- Python monorepo with `src/` layout (PEP 621 / pyproject.toml)
- `click` for CLI framework (subcommand architecture)
- `rich` for terminal formatting (tables, panels, colors)
- `pydantic` for data models, `pydantic-settings` for config
- Editable install: `pip install -e ".[dev]"`
- Package `__init__.py` exports `__version__`

## Verification Checklist
- [ ] `python main.py --help` shows usage info
- [ ] `python main.py --version` shows version 0.1.0
- [ ] `python -c "import motodiag; print(motodiag.__version__)"` works
- [ ] `python -c "from motodiag.core import config"` works
- [ ] `python -c "from motodiag.cli import main"` works
- [ ] All 8 subpackage directories importable
- [ ] pytest discovers and runs (even if no tests yet)
- [ ] `motodiag` CLI entry point works after pip install -e

## Risks
- Windows path issues with `src/` layout — mitigate with proper pyproject.toml config
- Click + argparse conflict in main.py — use Click as primary, argparse only as fallback
- Python 3.13 compatibility with all dependencies — verify during install
