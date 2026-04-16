# MotoDiag Phase 01 — Project Scaffold + Monorepo Setup

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-15

## Goal
Establish the moto-diag monorepo foundation: Python package structure, pyproject.toml with dependencies, CLI entry point, and the directory skeleton for all 8 tracks. This phase produces a runnable `motodiag` CLI that prints version info and verifies the package structure is importable.

CLI: `python main.py --version` / `python main.py --help` / `motodiag --help` / `motodiag info`

Outputs:
- Working monorepo with all 8 subpackage directories
- `pyproject.toml` with base + optional dependencies
- `main.py` CLI entry point (argparse fallback with Windows UTF-8 fix)
- `motodiag` Click CLI with subcommands (diagnose, code, garage, history, info)
- Base data models: VehicleBase, DiagnosticSessionBase, DTCCode, enums
- Config system with pydantic-settings (.env support)
- 24 tests covering imports, config, models, and CLI

## Logic
1. Created `moto-diag/` project directory with `src/motodiag/` package layout
2. Created `pyproject.toml` with setuptools build backend, base deps (click, rich, pydantic, pydantic-settings), optional dep groups (dev, ai, api, hardware, all), and `motodiag` CLI entry point
3. Created 8 subpackages under `src/motodiag/`: core, vehicles, knowledge, engine, cli, hardware, advanced, api — each with `__init__.py`
4. Built `core/config.py` with `Settings` class (pydantic-settings) loading from `.env` with `MOTODIAG_` prefix
5. Built `core/models.py` with base Pydantic models: VehicleBase, DiagnosticSessionBase, DTCCode, and enums (DiagnosticStatus, Severity, SymptomCategory, ProtocolType)
6. Built `cli/main.py` with Click group: welcome screen (rich Panel + Table), subcommands (diagnose, code, garage, history, info) — placeholder stubs pointing to future phases
7. Built `main.py` fallback with argparse, Windows UTF-8 fix, `--version` and `--info` flags
8. Created `.venv` with Python 3.13, installed editable with `[dev]` extras
9. All 24 tests pass: package imports, version, config defaults, model creation, CLI help/version/info

## Key Concepts
- **PEP 621 pyproject.toml** with `setuptools.build_meta` backend and `src/` layout
- **Click CLI framework** with `@click.group(invoke_without_command=True)` for subcommand architecture
- **Rich** for terminal formatting (Panel, Table, Console)
- **Pydantic v2** models with Field validators, enums, type hints
- **pydantic-settings** for config from `.env` files with prefix
- **Editable install**: `pip install -e ".[dev]"` for development workflow
- **ProtocolType enum**: CAN, K_LINE, J1850, PROPRIETARY, NONE — covers all target bikes

## Verification Checklist
- [x] `python main.py --help` shows usage info
- [x] `python main.py --version` shows version 0.1.0
- [x] `python -c "import motodiag; print(motodiag.__version__)"` works
- [x] `python -c "from motodiag.core import config"` works
- [x] `python -c "from motodiag.cli import main"` works
- [x] All 8 subpackage directories importable (12 import tests pass)
- [x] pytest discovers and runs — 24/24 tests pass in 0.29s
- [x] `motodiag` CLI entry point works after pip install -e

## Risks
- ~~Windows path issues with `src/` layout~~ — resolved, pyproject.toml `[tool.setuptools.packages.find]` with `where = ["src"]` works correctly
- ~~Click + argparse conflict in main.py~~ — resolved, main.py uses argparse as fallback, Click is primary via `motodiag` entry point
- ~~Python 3.13 compatibility~~ — all deps install and work on 3.13.5
- Initial build-backend was wrong (`setuptools.backends._legacy`) — fixed to `setuptools.build_meta`

## Deviations from Plan
- Build backend changed from `setuptools.backends._legacy:_Backend` to `setuptools.build_meta` — the legacy backend doesn't support editable installs in newer pip versions

## Results
| Metric | Value |
|--------|-------|
| Subpackages | 8 (core, vehicles, knowledge, engine, cli, hardware, advanced, api) |
| Source files | 13 Python files |
| Test count | 24 |
| Test pass rate | 100% (24/24) |
| Test time | 0.29s |
| Dependencies | click, rich, pydantic, pydantic-settings (base); pytest, pytest-cov, ruff (dev) |

Foundation is solid. All 8 track directories are importable, base models cover the core domain (vehicles, DTCs, diagnostic sessions, protocols), and the CLI is ready for subcommand expansion in subsequent phases.
