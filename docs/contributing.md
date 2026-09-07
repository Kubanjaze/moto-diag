# Contributing to MotoDiag

For working on MotoDiag itself. If you just want to *use* it, the
[README](../README.md) and the [guides](guide/) are the place to start.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
motodiag db init
```

## Tests

```bash
pytest -q                       # full suite (~9 minutes)
pytest tests/test_phase207_security.py -q   # one file
pytest -q -k "customer or push"             # by keyword
```

The suite is organised by phase — `tests/test_phase<NN>_<topic>.py` —
and runs against temporary databases, never your working one.

## Pre-commit hooks

The repo runs F9 mock-vs-runtime-drift pattern checks before each
commit. One-time setup per machine:

```bash
pre-commit install
```

Run them by hand:

```bash
pre-commit run --all-files
# or directly
python scripts/check_f9_patterns.py --all
```

### The checks

- **`--check-ssot-constants`** — scans `tests/**` for literal pins of
  any constant declared in `f9_ssot_constants.toml`. Opt out per-line
  with `# f9-noqa: ssot-pin <reason>`, or
  `# f9-noqa: ssot-pin contract-pin: <reason>` when the two-source
  assertion is the deliberate design (a schema-version pin is the
  canonical case: importing the constant would make the assert `x == x`
  and it would never fail). File-level: `# f9-allow-ssot-constants:
  <reason>` (≥20 chars).
- **`--check-tag-catalog-coverage`** — diffs `APIRouter(tags=...)`
  strings in `src/motodiag/api/routes/**` against
  `motodiag.api.openapi.TAG_CATALOG`. A tag in a route but not the
  catalog is an error; a catalog entry no route uses is a warning.
- **`--check-deploy-path-init-db`** — flags Click commands under
  `src/motodiag/cli/` that call `uvicorn.run` without first calling
  `init_db()`. This exists because `motodiag serve` once didn't, and
  the backend quietly ran on a stale schema.
- **`--check-model-ids`** — **deprecated**; redirects to
  `--check-ssot-constants` filtered to `MODEL_ALIASES` + `MODEL_PRICING`.
  Call `--check-ssot-constants` directly in new code.

`docs/patterns/f9-mock-vs-runtime-drift.md` is the full pattern
catalogue: ten case studies of the same family of bug, which is
"something I believed about the system was true of my mental model and
not of the running code."

## Database changes

Schema changes are sequential migrations in
`src/motodiag/core/migrations.py`, appended to the `MIGRATIONS` list,
each with `upgrade_sql` and `rollback_sql`. Bump `SCHEMA_VERSION` in
`src/motodiag/core/database.py` in the same commit.

Three tests pin `SCHEMA_VERSION` deliberately and will fail until you
update them — that is their job, not an obstacle:

- `tests/test_phase184_gate9.py`
- `tests/test_phase191b_serve_migrations.py`
- `tests/test_phase205_gate11.py`

Apply and verify on a scratch database before committing. A migration
that references a column that does not exist will refuse to apply, and
finding that out in CI is slower than finding it out now.

## API contract changes

The mobile app's TypeScript types are generated from the backend's
OpenAPI schema. When you change a route or a model, refresh both or the
app will type-check against a contract the server no longer honours:

```bash
# in moto-diag, with the schema regenerated from the app object
python -c "import json; from motodiag.api.app import create_app; \
  json.dump(create_app().openapi(), open('/tmp/openapi.json','w'), indent=2)"

# in moto-diag-mobile
cp /tmp/openapi.json api-schema/openapi.json
npm run generate-api-types
npx tsc --noEmit
```

This has drifted twice. Both times the backend was correct and the
generated artefacts were stale, so the *types* were the thing that
lied.

## Documentation

`tests/test_phase208_docs.py` asserts that every `motodiag` command and
every `/v1/...` path named in the docs actually exists, reading the live
Click registry and the live OpenAPI schema. If you rename a command,
that test tells you which document to update.

It checks names, not truth. Nothing can assert that the sentence next
to a command is accurate — run the commands you document.

## Phase workflow

Development runs in numbered phases with plan-first discipline. See
`docs/ROADMAP.md` for the sequence and
`docs/phases/completed/` for the record. `ROADMAP_AUTHORITY.md` at the
repo root explains which document wins when two disagree.
