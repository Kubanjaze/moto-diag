# Phase 259 — Pre-purchase inspection (PPI) — engine

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-24

**Branch:** `phase-259` (GLM builder session in the sandbox clone; finish
line "ready to merge" — the regression of record, the refute pass, the
merge and the deploy are the Opus session's).

## Goal

Give the shop a pre-purchase **engine** inspection protocol as persistent
workflow content on the Phase 114 substrate — one template,
`ppi_engine_v1`, covering the six subjects the ROADMAP row names
(compression, leak-down, oil sample, fuel quality, starter/charging
health, visual inspection) — and give the workflow substrate its first
user-reachable front door, `motodiag workflow list/show`, because
nothing in the CLI or API can reach a single template today. Every
figure in the item text cites the document it came from; where no
document sets a figure the item says where the figure belongs and no
number is invented.

CLI: `motodiag workflow list`, `motodiag workflow show ppi_engine_v1`

Outputs: migration 067 (`src/motodiag/core/migrations.py`, schema 66 →
67), `src/motodiag/cli/workflow.py`, one line in
`src/motodiag/cli/main.py` registering it,
`tests/test_phase259_ppi_engine.py`

## Logic

1. **Migration 067 — `ppi_engine_workflow`.** One `INSERT` for the
   template (slug `ppi_engine_v1`, category `ppi`,
   `applicable_powertrains = ["ice","hybrid"]` — **not** `electric`: the
   six subjects are ICE subjects; the substrate's default would offer
   this to a Zero), `estimated_duration_minutes` 70, tier `individual`,
   system user 1. Seven `INSERT`s for the checklist items
   (`sequence_number` 1–7, keyed on the slug sub-select, inside the
   one-shot migration journal — `checklist_items` has no unique
   constraint, so a re-runnable seed path would duplicate rows; S0-2).
   One `UPDATE` re-pointing `generic_ppi_v1`'s now-stale description
   ("Track N phase 259 expands with engine-specific content") at the new
   slug. `rollback_sql` peels exactly what 067 added: delete the new
   template's items (cascade), the template, and restore the old
   description.
2. **CLI — `src/motodiag/cli/workflow.py`.** A `workflow` click group,
   `register_workflow(cli)` wired in `main.py` beside the other
   registrars, in the 244V pattern (`ref` was built for exactly this
   unreachable-reference shape):
   - `motodiag workflow list [--category <cat>]` — active templates via
     `list_templates`, a table of slug / category / name / minutes.
   - `motodiag workflow show <slug>` — the template header (name,
     description, category, powertrains, duration) then every item in
     sequence with its full text: instruction, expected pass, expected
     fail, diagnosis if fail, tools, minutes. The description and
     instruction fields carry their citations inline, so the screen the
     mechanic reads states the provenance where 244V taught this project
     to put it.
   - an unknown slug or an empty category prints an honest message and
     exits non-zero.
3. **Data flow.** migration journal (existing DBs) / `db init` (new DBs)
   → `workflow_templates` + `checklist_items` → `template_repo`'s
   existing accessors → click commands → terminal. No new tables, no new
   repo functions, no API, no model changes. Nothing computes; this is
   content plus a reader.

## Key Concepts

- **Extension, not greenfield** (S0-1): Phase 114's substrate already has
  every field the six subjects need; the phase adds content and one
  reader. `WorkflowCategory.PPI`, `create_template`/`add_checklist_item`
  are not used by 259's seed (the journal is), only by 114's tests.
- **Provenance on screen** (244V's rule): an item's figures belong to
  named documents with pages, in the text itself. General procedure
  (how to hold a throttle, where air escapes) is authored knowledge;
  every *figure* is either cited or explicitly deferred to the machine's
  own manual. The leak-down item carries **no** percentage — S0-3's
  census found none in 260 PDFs (control: "compression" finds 178), and
  an invented threshold is exactly what F149 documented for corpus rows.
- **The floor-pin pattern** (F124): schema assertions in 259's tests use
  `SCHEMA_VERSION >= 67`, never `== 67`; the genuine head pin lives
  where it already lives, `tests/test_phase240c_severity_ordering.py`.
- **Applicability by powertrain** (S0-4): `["ice","hybrid"]` excludes
  electric machines through `list_templates`' documented JSON-substring
  filter — the substrate's own mechanism, not a new one.
- **Migration seeding shape** (114 precedent): `INSERT OR IGNORE` +
  slug sub-selects inside `Migration.upgrade_sql`, `rollback_sql`
  peeling only what this migration added.

## Decisions

- **D1 — new template, not an edit of `generic_ppi_v1`.** The generic
  PPI stays the quick 5-item check it is; `ppi_engine_v1` is the
  engine-side protocol; Phase 260 adds the chassis protocol. Editing a
  seeded template's content in place would also collide with the item
  identity problem (S0-2): there is no update path keyed on anything but
  prose.
- **D2 — powertrains `["ice","hybrid"]`**, per S0-4.
- **D3 — CLI, not API, for the front door.** No workflow API route
  exists and the CLI is the door every integration gate to date has
  walked (`gate14` through `motodiag` and the HTTP API; Gate 15 will
  need this command). The API surface stays out of scope.
- **D4 — seven items**, mapping to the row's six subjects: static visual
  (1), battery/charging (2), starter/cold start/running (3) — together
  the starter/charging-health and visual subjects — compression (4),
  leak-down (5), oil (6), fuel (7). Spark-plug reading, coolant flushes
  and service-history forensics are folded into the running/visual items
  or left out (S7: the row names six subjects).
- **D5 — `generic_ppi_v1`'s stale forward pointer is re-pointed** by the
  same migration, because after this phase it would promise a "Track N
  phase 259" expansion inside the generic template that this phase
  deliberately did not do there (D1).

## Non-goals

- No chassis content (260), no tire/winterization/valve content (261+).
- No new tables, repo functions, API routes, or models.
- No migration of the live database in this session: migration 067 runs
  as a dry run against a copy of the snapshot; the real load, after a
  backup, is the Opus session's.
- No leak-down figure anywhere in the content (S0-3's negative claim).
- Mobile: untouched.

## Claims for the Opus refute pass

Every fact below is taken from a document in `~/research/motodiag`
(cited by library-relative path and PDF page, the F152 convention) and
appears in the seeded item text. The refute pass opens each document at
the page and checks the claim against it.

| # | claim as it appears in the content | document | PDF page |
|---|---|---|---|
| C1 | Honda CHF50 cylinder compression is 1,393 kPa (14.2 kgf/cm², 202 psi) at 1,500 rpm; the service-limit column for compression is blank | `honda/chf50_service_mirror.pdf` | 11 |
| C2 | CHF50 battery 12V-6Ah; current leakage 0.1 mA max; voltage 13.0-13.2 V fully charged at 20 °C/68 °F; below 12.3 V needs charging; charging current 0.6 A/5-10 h normal, 3 A/1 h quick | `honda/chf50_service_mirror.pdf` | 13 |
| C3 | CHF50 alternator capacity 190 W at 5,000 rpm; charging coil resistance 0.05-0.5 Ω at 20 °C/68 °F | `honda/chf50_service_mirror.pdf` | 13 |
| C4 | The CHF50 troubleshooting table lists, as causes of oil consumption: external oil leak; worn piston ring or incorrect piston ring installation; worn cylinder; worn valve guide or seal — and, as causes of oil contamination: oil not changed often enough; faulty cylinder head gasket; worn piston ring | `honda/chf50_service_mirror.pdf` | 79 (printed 4-3) |
| C5 | "Engine oil consumption varies and oil quality deteriorates according to riding conditions and time elapsed. Check the engine oil level regularly, and add the recommended engine oil if necessary. Dirty oil or old oil should be changed as soon as possible." (paraphrased in the item text as cited guidance) | `honda/metro_2025_31GJB680.pdf` | 62 (printed 58) |
| C6 | Fuel guidelines: "Use only unleaded gasoline. Use the recommended octane number… Do not use stale or contaminated gasoline or an oil/gasoline mixture. Avoid getting dirt or water in the fuel tank." | `honda/metro_2025_31GJB680.pdf` | 17 (printed 13) |
| C7 | **Negative:** no document in the library describes a leak-down test or sets a leak-down figure — vocabulary `leak[- ]?down`, scope every `*.pdf` under `~/research/motodiag` minus the two venvs (260 files, 16 unparseable = F127's debris), count 0; control: "compression" finds 178 files including C1's exact page | whole library (`census_leakdown.py`, in the builder session's tmp) | — |

Measurements of this repo the refute pass reproduces (not document
claims): the substrate has no CLI/API consumer (grep over `cli/`, `api/`
= 0 imports); the snapshot is at schema 66 with 1,060 `known_issues`, 2
templates, 9 items; migration 067 raises a fresh `db init` database to
67 with `ppi_engine_v1` + 7 items.

## Verification Checklist

- [ ] Migration 067 applies on a copy of the snapshot (66 → 67) and on a
      fresh `db init` database; `SCHEMA_VERSION >= 67`
- [ ] 067's rollback peels it: no `ppi_engine_v1`, items gone via
      cascade, `generic_ppi_v1`'s description restored; schema back at 66
- [ ] Template: category `ppi`, powertrains exactly `["ice","hybrid"]`,
      active, tier `individual`; not offered under
      `list_templates(powertrain="electric")`
- [ ] Seven items, `sequence_number` 1–7 contiguous, every item has
      instruction / expected pass / expected fail; figures pinned: C1's
      figures in the compression item, C2/C3's in the battery item, C5's
      in the oil item, C6's in the fuel item
- [ ] The leak-down item contains **no** percentage figure (a regex any
      number+`%` must miss) and names where the threshold belongs
- [ ] `motodiag workflow list` shows both PPI templates;
      `--category ppi` hides winterization; `motodiag workflow show
      ppi_engine_v1` prints all seven item titles and the template
      description; unknown slug exits non-zero
- [ ] `generic_ppi_v1` still holds its 5 items, still active,
      description now points at `ppi_engine_v1`
- [ ] Wiring: the click group is registered from `main.py` (the tests
      drive the real registered group, not a private import)
- [ ] The four whole-tree checks (191C F9 lint, 244G, roadmap continuity,
      `finding_check`) plus the sandbox list's whole-tree tests all pass

## Risks

- **Item identity is prose** (S0-2/F129's shape): a later phase that
  rewrites a seeded item on a live database will duplicate it. Mitigated
  by pinning the content in this phase's tests and by the same
  migration-keyed-on-old-text rule the corpus uses.
- **The 12.3 V / 13.0-13.2 V figures are CHF50's, not universal.** The
  item text says so twice (worked example, machine's manual deferred);
  the refute pass should attack whether any sentence implies the numbers
  apply beyond the cited machine.
- **`list_templates`' substring powertrain filter** is 114's documented
  limitation; 259 relies on it for the electric exclusion (D2), and the
  test pins that reliance so a future JSON-query upgrade cannot silently
  drop it.
- **Migration 067's seed is not idempotent outside the journal**
  (no unique constraint on items). It never runs outside the journal;
  recorded here so nobody "fixes" the loader later by re-running it.
