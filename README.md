# MotoDiag

AI-powered motorcycle diagnostic tool. Symptom analysis, fault code interpretation, and guided troubleshooting — built for mechanics.

## Target Fleet
- **Harley-Davidson** — all eras (Evo, Twin Cam, Milwaukee-Eight, Sportster)
- **Honda** — CBR 900RR/929RR/954RR, CBR 600F4/F4i
- **Yamaha** — YZF-R1, YZF-R6
- **Kawasaki** — ZX-6R, ZX-7R, ZX-9R, ZX-10R
- **Suzuki** — GSX-R 600/750/1000

## Quick Start

```bash
# Create venv and install
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -e ".[dev]"

# Run
motodiag --version
motodiag info
motodiag --help
```

## Architecture

```
src/motodiag/
├── core/       — config, database, base models
├── vehicles/   — vehicle registry, specs
├── knowledge/  — DTC codes, symptoms, known issues
├── engine/     — AI diagnostic engine (Claude API)
├── cli/        — terminal interface
├── hardware/   — OBD adapter interface
├── advanced/   — fleet, maintenance, prediction
└── api/        — REST API
```

## Hybrid Design

**Phase 1 (Software):** AI troubleshooting agent — describe symptoms or enter fault codes, get guided diagnosis.

**Phase 2 (Hardware):** Bluetooth OBD adapter reads live sensor data and fault codes directly from the ECU. AI interprets real data alongside symptom reports.

## Pre-commit hooks

This repo uses [pre-commit](https://pre-commit.com) to run F9 mock-vs-runtime-drift pattern checks before each commit. Architect-side opt-in (one-time per machine):

```bash
.venv\Scripts\python.exe -m pip install -e ".[dev]"  # installs pre-commit
.venv\Scripts\pre-commit install                      # wires up .git/hooks/pre-commit
```

After install, every `git commit` runs `scripts/check_f9_patterns.py --all`. To run manually:

```bash
.venv\Scripts\pre-commit run --all-files
# OR
.venv\Scripts\python.exe scripts/check_f9_patterns.py --all
```

The checks are:

- `--check-ssot-constants` (Phase 191D, F20 mitigation) — TOML-driven scan of `tests/**` for literal pins of any constant declared in `f9_ssot_constants.toml`. Generalizes the original narrow model-ID rule. Opt out per-line with `# f9-noqa: ssot-pin <reason>` or `# f9-noqa: ssot-pin contract-pin: <reason>` (intentional two-source assertion design); file-level with `# f9-allow-ssot-constants: <reason>` (>=20 chars).
- `--check-tag-catalog-coverage` (Phase 191D, F21 mitigation) — diffs `src/motodiag/api/routes/**/*.py` `APIRouter(tags=...)` strings against `motodiag.api.openapi.TAG_CATALOG`; flags tags-in-routes-not-in-catalog (error) / tags-in-catalog-not-in-routes (warn).
- `--check-deploy-path-init-db` (subspecies iv) — flags Click commands under `src/motodiag/cli/` that call `uvicorn.run` (or similar serve patterns) without first calling `init_db()`. Opt out per-call with `# f9-noqa: deploy-path-init-db <reason>`.
- `--check-model-ids` (subspecies ii narrow) — **DEPRECATED at Phase 191D**; stub-redirects to `--check-ssot-constants` filtered to `MODEL_ALIASES` + `MODEL_PRICING`. Removal targeted Phase 200+. New code should call `--check-ssot-constants` directly.

See `docs/patterns/f9-mock-vs-runtime-drift.md` for the pattern catalog + per-subspecies mitigation strategy (the "Subspecies (ii) generalized" subsection covers the F20/F21 scope extension).

Real CI integration is deferred to Phase 204 / Gate 10 per the existing CI-deferred posture.
