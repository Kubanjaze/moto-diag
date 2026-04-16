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
