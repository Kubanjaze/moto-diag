# MotoDiag

AI-assisted motorcycle diagnostics and shop management. Describe a
symptom or read a fault code, work the diagnosis, then run the job:
intake, work order, parts, labour, invoice, and a share link the
customer can open without an account.

Two pieces ship from two repos:

| | |
|---|---|
| **`moto-diag`** (this repo) | Python CLI + FastAPI HTTP API + SQLite. The whole product works from a terminal. |
| **`moto-diag-mobile`** | React Native iOS app for the shop floor — camera, voice notes, work orders in your hand. |

## Requirements

- Python 3.11+ (developed on 3.14)
- macOS or Linux (the commands below are POSIX; this project is
  developed on macOS)
- An Anthropic API key, for the AI-assisted commands only. Everything
  else — fault-code lookup, the knowledge base, the shop workflow —
  runs entirely offline against local SQLite.

## Install

```bash
pipx install motodiag
motodiag db init
```

Or from source, to work on it:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
motodiag db init
```

Full instructions — extras, Docker, where your data lives — in the
[install guide](docs/guide/install.md).

`db init` creates the database and loads the starter data: DTC
definitions, symptom entries, and 660 curated known issues.

Verify:

```bash
motodiag --version
motodiag info
```

## Try it

```bash
motodiag code P0115
```

```
╭─────────────────────────────── DTC P0115 ────────────────────────────────╮
│ P0115 — Engine Coolant Temperature Circuit Malfunction                   │
│                                                                          │
│ Category: cooling                                                        │
│ Severity: MEDIUM                                                         │
│ Make: Generic (all makes)                                                │
╰──────────────────────────────────────────────────────────────────────────╯

Common causes:
  1. Faulty coolant temp sensor
  2. Wiring issue in coolant temp circuit
  3. Corroded connector

Fix: Check sensor connector, test sensor resistance vs temp chart, replace
if out of spec.
```

Then read **[docs/guide/quickstart.md](docs/guide/quickstart.md)** — a
bike from garage to finished diagnosis in about ten minutes.

## Guides

| Guide | For |
|---|---|
| [Quickstart](docs/guide/quickstart.md) | A mechanic diagnosing one bike |
| [Shop workflow](docs/guide/shop-workflow.md) | Intake → work order → parts → labour → invoice → customer link |
| [HTTP API](docs/guide/api.md) | Anyone integrating, or running the iOS app |
| [Install](docs/guide/install.md) | Getting it onto a machine |
| [Contributing](docs/contributing.md) | Working on MotoDiag itself |
| [Releasing](docs/releasing.md) | Cutting a release |
| [Launch checklist](docs/launch-checklist.md) | What's left before real users |

## What's in the box

The CLI has **255 commands** across 24 groups. `motodiag --help` lists
the groups; `motodiag <group> --help` lists each group's commands. The
ones you'll actually reach for:

```bash
motodiag code P0115                    # fault-code lookup
motodiag search "overheating"           # across DTCs, symptoms, known issues
motodiag kb list --make honda           # browse the knowledge base
motodiag garage add --make Honda --model CBR600F4i --year 2003
motodiag diagnose start                # interactive AI session with Q&A
motodiag quick "misfire at 4000rpm"     # one-shot, no Q&A
motodiag hardware scan                 # read DTCs off the ECU
motodiag shop work-order list          # the shop side
motodiag serve                         # the HTTP API
```

Shortcuts exist for the ones you type most: `d` for `diagnose`, `g` for
`garage`, `k` for `kb`, `q` for `quick`.

Shell completion:

```bash
motodiag completion zsh > ~/.motodiag-completion.zsh
echo 'source ~/.motodiag-completion.zsh' >> ~/.zshrc
```

## Talking to the bike

`motodiag hardware` speaks OBD-II over a Bluetooth or Wi-Fi adapter —
scan and clear DTCs, stream live PIDs, record a session and replay it,
and a live TUI dashboard. Adapter compatibility is its own knowledge
base (`motodiag hardware compat recommend`), because "OBD-II adapter"
covers a lot of ground that does not include most motorcycles.

No adapter? `motodiag hardware simulate run` drives the whole stack off
a scenario file, and the diagnostic side does not need hardware at all.

## The HTTP API

```bash
motodiag serve
```

Serves 80 routes on `127.0.0.1:8000` and applies any pending schema
migrations first. Interactive docs at `/docs`, and `/healthz` for a
liveness check. Authentication is an API key in an `X-API-Key` header:

```bash
motodiag apikey create --user 1 --name laptop
```

The key is shown **once**. See the [API guide](docs/guide/api.md) for
the auth model, tiers, error shape, and share links.

## Architecture

```
src/motodiag/
├── core/          config, database, migrations, session repo
├── cli/           the 255-command terminal interface
├── api/           FastAPI app, routes, auth deps, error mapping
├── auth/          API keys, tiers, permissions
├── engine/        AI diagnostic engine (Claude), prompt + cost control
├── knowledge/     DTCs, symptoms, known issues
├── vehicles/      vehicle registry and specs
├── hardware/      OBD-II adapters, live PIDs, recording, simulation
├── shop/          work orders, issues, triage, parts, labour, rules
├── crm/           customers and customer-bike relationships
├── accounting/    invoices and line items
├── scheduling/    bays, slots, calendar
├── inventory/     stock levels
├── advanced/      fleets, predictive maintenance, TSBs, recalls, drift
├── reporting/     report composition + HTML/PDF renderers
├── media/         photo and video processing (ffmpeg)
├── push/          APNs device tokens and notifications
├── billing/       Stripe + subscription lifecycle
├── intake/        photo-based bike identification
└── obd_reports/   field telemetry on adapter failures
```

Storage is a single SQLite file under sequential migrations. `motodiag
serve` applies pending migrations at startup; `motodiag db init` does
the same for CLI use.

## Fleet coverage

The curated knowledge base is deepest on:

- **Harley-Davidson** — Evo, Twin Cam, Milwaukee-Eight, Sportster
- **Honda** — CBR 900RR/929RR/954RR, CBR 600F4/F4i
- **Yamaha** — YZF-R1, YZF-R6, FZ/MT, VMAX
- **Kawasaki** — ZX-6R, ZX-7R, ZX-9R, ZX-10R
- **Suzuki** — GSX-R 600/750/1000

Generic DTC definitions apply to any OBD-II bike; make-specific entries
take precedence when one exists.

## Configuration

Settings come from environment variables (prefix `MOTODIAG_`) or a
gitignored `.env` in the repo root.

| Variable | Purpose |
|---|---|
| `MOTODIAG_DB_PATH` | SQLite file location |
| `ANTHROPIC_API_KEY` | Required for AI commands only |
| `MOTODIAG_ENV` | `dev` \| `test` \| `prod` |
| `MOTODIAG_API_HOST` / `_PORT` | Bind address for `serve` |
| `MOTODIAG_PUBLIC_BASE_URL` | Public origin, for customer share links |
| `MOTODIAG_BILLING_PROVIDER` | `fake` \| `stripe`; **must be `stripe` in prod** |

`motodiag config show` prints the resolved values; `motodiag config
paths` shows where data lands.

## Costs

AI commands call the Anthropic API and cost money. MotoDiag caches
responses, tracks spend, and will tell you:

```bash
motodiag cache stats     # hit count and approximate dollars saved
motodiag costs report    # the spend ledger
```

## License

See [LICENSE](LICENSE).
