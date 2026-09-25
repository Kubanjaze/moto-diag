# Phase 261 — Track N batch 1: tire, brake, suspension and drivetrain service

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-25

**Branch:** `phase-261` (Opus session, main checkout).

**Carries four ROADMAP rows** (the operator's batching, 2026-09-25): 261
tire service, 269 brake service, 270 suspension service, 271 chain / belt
/ shaft service. One Step 0, one migration, one regression, one
close-out, one handoff. The ledger convention is in the phase log.

## Goal

Give the shop four service protocols as workflow content on the Phase 114
substrate, one template per row, reachable through the `motodiag
workflow list/show` door 259 built:

| row | slug | category | subjects (the row's words) |
|---|---|---|---|
| 261 | `tire_service_v1` | `tire_service` | wear patterns, DOT date decoding, age cracking, balance, TPMS |
| 269 | `brake_service_v1` | `brake_service` | pad replacement, caliper rebuild, rotor thickness, fluid flush, bleed |
| 270 | `suspension_service_v1` | `suspension_service` | fork seals, fork oil, spring rate selection, rear shock rebuild, sag setup |
| 271 | `drivetrain_service_v1` | `drivetrain_service` | chain and sprockets, belt tension and alignment, shaft drive oil, u-joint inspection |

Every figure an item states cites a held document by name and PDF page,
in the item's own text, and names the machine it belongs to. Where no
document sets a figure (N1 wear-pattern names, N2 u-joint inspection, N3
belt alignment; `261_step0.md`), the item says where the figure belongs
and invents none.

CLI: none new. `motodiag workflow list [--category tire_service|
brake_service|suspension_service|drivetrain_service]` and `motodiag
workflow show <slug>`.

Outputs: migration 069 (`src/motodiag/core/migrations.py`, schema 68 →
69), `SCHEMA_VERSION` 68 → 69 in `src/motodiag/core/database.py`,
`tests/test_phase261_service_workflows.py`.

## Logic

1. **Migration 069, `chassis_drivetrain_service_workflows`.** Four
   `INSERT OR IGNORE` template rows (`applicable_powertrains`
   `["ice","electric","hybrid"]`, tier `individual`, system user 1), then
   each template's items keyed on its slug sub-select, inside the one-shot
   journal (S0-2). **Inserts only**: it alters and deletes no existing row.
   `rollback_sql` deletes the four templates' items, then the four
   templates.
2. **Items** (planned; titles may change in wording, not in subject):
   - `tire_service_v1` (7): read the old tire (wear, tread depth, the
     makers' causes of abnormal wear); damage and age cracking; the date
     code and the age limits; TPMS / RDC before and after the bead is
     broken (**optional**: machines with pressure sensors); fitting the
     replacement (approved tire, size, load and speed rating, tubeless,
     rotation arrow, rim runout while the wheel is off); balance; cold
     pressure and run-in.
   - `brake_service_v1` (7): pads; discs; caliper overhaul; master
     cylinder; fluid (type, interval, moisture, paint); bleeding;
     reassembly torques and bedding-in.
   - `suspension_service_v1` (7): record the settings and measure sag;
     spring rate for the rider; fork oil (quantity, level, air); fork
     seals and dust wipers (spring free length while apart); rear shock
     service or replacement (the makers disagree; both stated); damping
     and preload back to base; road check.
   - `drivetrain_service_v1` (7): chain slack; chain wear and sprockets;
     guides, cleaning and lubrication; chain adjustment, alignment and
     replacement; belt drive; shaft drive oil; universal joints and the
     swinging-arm bearings. The chain items are **optional**, and so are
     the belt and shaft items (a machine has one drive type; S0-4).
3. **Data flow.** Migration journal (existing DBs) / `db init` (new DBs)
   → `workflow_templates` + `checklist_items` → the existing accessors →
   the existing click commands → terminal. Nothing computes.

## Key Concepts

- **Content on a door that already opens.** 260's shape: one migration
  plus its pins, no new module, the integration-gap allowlist unmoved.
- **Makers' words, then negatives.** Every subject was searched in the
  maker's own vocabulary before a negative was allowed (`261_step0.md`
  S0-3). The belt negative died inside Step 0 to Yamaha's "drive belt
  slack".
- **Figures belong to machines.** A KTM EXC slack figure is the KTM EXC's.
  Items say "the CB500F owner's manual sets 35–45 mm", never "set the
  slack to 35–45 mm".
- **The makers disagree, and the item says so.** KTM services its shock
  (10 bar nitrogen, SAE 2.5 fluid); Honda forbids opening its damper.
  The item gives both and sends the shop to the machine's own manual.
- **F158 by construction.** No `Phase N`, `Track X`, finding number or
  "this phase" in any template or item text. The pin's pattern is seen to
  catch a planted "Phase 999".
- **F124.** No literal head pin. Migration tests apply migrations up to
  068 on a self-built database, apply 069 alone, and compare against
  `m.version`. Rollback tests use `rollback_to_version(68)`.

## Decisions

- **D1: four templates, one per row; not one "chassis service"
  template.** Each row is a distinct shop job with its own category in the
  enum.
- **D2: one migration (069) for all four**, the operator's batch shape.
- **D3: drivetrain is one template with optional per-drive items**
  (S0-4). Three templates would ship the same items under three slugs.
- **D4: all powertrains** (S0-5).
- **D5: scope stops at the rows' subjects.** The scooter CVT belt (a
  transmission part with its own `known_issues` content) and a scooter's
  final-reduction gear oil are not the row's "belt" and "shaft".
- **D6: the extraction route.** Subconscious returned 403 (account
  suspended; S0-7); rule 2's fallback route ran the one-turn extraction.
  Recorded, and the operator is told in the report.

## Non-goals

- No new tables, repo functions, CLI commands, API routes or mobile
  screens.
- No change to existing templates or items (F158's 33 references and
  F159's uncited starter figures stay with their own work).
- No CVT belt, winterization, break-in or valve content (batch 2 and
  other rows).

## Claims for the refute pass

Written with the content at build (v1.1), one row per fact as it
appears in the item text, with its library path and PDF page, so the
table matches what shipped (the 260 lesson). N1–N3 are the negatives,
with their controls, from `261_step0.md`.

## Verification Checklist

- [ ] Migration 069 applies on a fresh `init_db` database;
      `SCHEMA_VERSION >= 69`; 069 found by name
- [ ] Upgrade 068 → 069 on a self-built 068 database changes no existing
      template or item row and adds exactly the four templates and their
      items
- [ ] `rollback_to_version(68)` removes all four templates and their
      items; re-applying restores them
- [ ] Every migration keeps its rollback (260's guard still green with
      069 present)
- [ ] Each template: category, powertrains, tier, active, duration; item
      counts and contiguous sequence; every item has instruction, pass,
      fail; the optional items are exactly the planned ones
- [ ] Figures pinned per field for every item that states one
- [ ] The no-figure sentences (N1, N2, N3) present, and the u-joint and
      belt-alignment text carries no invented figure
- [ ] F158 pins over all four templates, with the pattern seen to catch a
      planted reference
- [ ] `workflow list` and `list --category <each>` show the new
      templates; `workflow show <slug>` prints every item title for all
      four
- [ ] Known-bad controls planted, seen red, reverted (phase log)
- [ ] Rule 3's four whole-tree checks, plus the F124 guard and 240c,
      before every commit that touches a migration
- [ ] Regression of record by `regression.sh`
- [ ] Refute pass over every claim, the `## Refuter pass` block in the
      phase log
- [ ] Dry run on a copy of the live database: inserts only, no existing
      row altered or deleted; then the live apply after a backup

## Risks

- **Figures quoted from one machine read as universal.** Mitigated by
  naming the machine beside every figure, and pinned by a test.
- **Item identity is prose** (F129's shape), as in 259/260: the content is
  pinned in tests and seeded only inside the journal.
- **The extraction ran on the fallback route.** Every quote was checked
  mechanically against its page, and the refute pass re-opens every
  citation.
