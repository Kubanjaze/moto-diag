# MotoDiag — Project Implementation

**Version:** 0.1.1 | **Date:** 2026-04-15
**Repo:** https://github.com/Kubanjaze/moto-diag
**Local:** `C:\Users\Kerwyn\PycharmProjects\moto-diag\`
**Roadmap:** `phases/ROADMAP_MOTODIAG_100.md` (local) | 100 phases across 8 tracks

---

## Overview

MotoDiag is an AI-powered motorcycle diagnostic tool designed for mechanics. It combines symptom-based troubleshooting with an AI reasoning engine and optional hardware OBD adapter integration for live ECU data.

**Target fleet:**
- Harley-Davidson — all eras (Evo 1984+, Twin Cam 1999+, Milwaukee-Eight 2017+, Sportster 1986+)
- Honda — CBR 900RR/929RR/954RR, CBR 600F4/F4i
- Yamaha — YZF-R1, YZF-R6
- Kawasaki — ZX-6R, ZX-7R, ZX-9R, ZX-10R
- Suzuki — GSX-R 600/750/1000

**Target users:** Motorcycle mechanics helping fellow mechanics

---

## Architecture

```
moto-diag/
├── pyproject.toml              ← project config, deps, entry points
├── implementation.md           ← THIS FILE (project-level overview)
├── phase_log.md                ← project-level change log
├── main.py                     ← CLI fallback entry point
├── src/motodiag/
│   ├── __init__.py             ← v0.1.0
│   ├── core/                   ← config, database, base models (Track A)
│   ├── vehicles/               ← vehicle registry, specs (Track A/B)
│   ├── knowledge/              ← DTC codes, symptoms, known issues (Track B)
│   ├── engine/                 ← AI diagnostic engine (Track C)
│   ├── cli/                    ← terminal interface (Track D)
│   ├── hardware/               ← OBD adapter interface (Track E)
│   ├── advanced/               ← fleet, maintenance, prediction (Track F)
│   └── api/                    ← REST API (Track G)
├── data/
│   ├── dtc_codes/              ← fault code databases
│   ├── vehicles/               ← make/model specs
│   └── knowledge/              ← known issues, repair procedures
├── tests/
├── output/
└── docs/
    └── phases/                 ← per-phase implementation + log docs
```

## Package Inventory

| Package | Track | Status | Description |
|---------|-------|--------|-------------|
| `core` | A | Scaffold | Config (pydantic-settings), base models (VehicleBase, DTCCode, DiagnosticSessionBase) |
| `vehicles` | A/B | Scaffold | Vehicle registry — empty, awaiting Phase 04 |
| `knowledge` | B | Scaffold | Knowledge base — empty, awaiting Phase 08 |
| `engine` | C | Scaffold | AI diagnostic engine — empty, awaiting Phase 29 |
| `cli` | D | Scaffold | Click CLI with 5 subcommands (placeholder stubs) |
| `hardware` | E | Scaffold | OBD adapter interface — empty, awaiting Phase 59 |
| `advanced` | F | Scaffold | Fleet management — empty, awaiting Phase 73 |
| `api` | G | Scaffold | REST API — empty, awaiting Phase 85 |

## Database Tables

_None yet — SQLite setup in Phase 03._

## CLI Commands

| Command | Status | Phase |
|---------|--------|-------|
| `motodiag --version` | ✅ Working | 01 |
| `motodiag --help` | ✅ Working | 01 |
| `motodiag info` | ✅ Working | 01 |
| `motodiag diagnose` | Stub | 29+ |
| `motodiag code <DTC>` | Stub | 05 |
| `motodiag garage` | Stub | 04 |
| `motodiag history` | Stub | 07 |

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Build style | Monorepo with subpackages | Single repo, shared models, one .venv |
| CLI framework | Click + Rich | Subcommand architecture, formatted terminal output |
| Config | pydantic-settings | .env support, typed settings, validation |
| Data models | Pydantic v2 | Validation, serialization, type safety |
| Database | SQLite (planned) | Local-first, no server, same as COS |
| AI Engine | Claude API (planned) | Haiku for cost, Sonnet for complex diagnostics |
| Hardware | Optional OBD adapters | CAN (Harley 2011+), K-line (Japanese 90s/2000s), J1850 (older Harley) |

## Dependencies

**Base:** click, rich, pydantic, pydantic-settings
**Dev:** pytest, pytest-cov, ruff
**AI (optional):** anthropic
**API (optional):** fastapi, uvicorn
**Hardware (optional):** pyserial

## Phase History

| Phase | Title | Date | Key Changes |
|-------|-------|------|-------------|
| 01 | Project scaffold + monorepo setup | 2026-04-15 | Initial monorepo, 8 subpackages, CLI, base models, 24 tests |

## Completion Gates

| Gate | Target Phase | Status | Criteria |
|------|-------------|--------|----------|
| Gate 1 | ~12 | 🔲 | Create vehicle → add symptoms → store → retrieve |
| Gate 2 | ~45 | 🔲 | Full symptom-to-repair flow with confidence + cost |
| Gate 3 | ~58 | 🔲 | Full mechanic workflow through CLI |
| Gate 4 | ~72 | 🔲 | Simulated ECU → adapter → read codes → AI diagnosis |
| Gate 5 | ~84 | 🔲 | Fleet + history + prediction end-to-end |
| Gate 6 | ~94 | 🔲 | Full API workflow: auth → vehicle → diagnose → report |
