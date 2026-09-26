# Phase 264 — Track N batch 2: winterization, de-winterization, engine break-in and valve adjustment

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-26

**Branch:** `phase-264` (Opus session, main checkout).

**Carries four ROADMAP rows** (the operator's batching): 264
winterization, 265 de-winterization, 266 engine break-in, 268 valve
adjustment. One Step 0, one migration, one regression, one close-out,
one handoff. The ledger convention is 261's:
- row 264 closes with its CLOSED date and the regression line;
- rows 265, 266 and 268 close ✅ "folded into 264" with no date of their
  own;
- one history row (264) and one handoff.

## Goal

Four shop protocols as workflow content on the Phase 114 substrate, one
template per row, reachable through `motodiag workflow list/show`:

| row | slug | category | powertrains | items (optional) |
|---|---|---|---|---|
| 264 | `winterization_v1` | `winterization` | ice, electric, hybrid | 7 (fuel, carburetor, oil and cylinders, traction battery) |
| 265 | `de_winterization_v1` | `de_winterization` | ice, electric, hybrid | 7 (traction battery, fuel and oil) |
| 266 | `engine_break_in_v1` | `break_in` | ice, hybrid | 6 (cool-down) |
| 268 | `valve_adjustment_v1` | `valve_service` | ice, hybrid | 8 (screw and lock nut, shims, V-twin, the engine types with no figure) |

Every figure an item states names its machine and cites that machine's
document and PDF page, in the item's own text. Machines are named as
their documents' title pages name them. Where the makers disagree
(fuel before storage, cylinder oil, battery intervals, break-in limits,
"cold") the item gives each maker's position beside its machine and says
they cannot be merged. Where no document sets a figure (N1–N7 in
`264_step0.md`) the item says so and invents none. Steps no document
states are marked as the template's own.

**Two live-row changes, in the same migration** (the operator's scope):
1. **F158:** `generic_winterization_v1`'s description loses "Track N
   phase 264 expands." and names `winterization_v1` by slug. Its four
   items are untouched.
2. **F160:** the 8 "Zuma" mentions in 3 live `ppi_chassis_v1` items (ids
   18, 19, 21) become the title page's model code, "YW125Y". F160 says
   nine; the ninth is in migration 068's Python description, which is
   never seeded (S0-6).

CLI: none new.

Outputs:
- migration 070 `seasonal_breakin_valve_workflows` in
  `src/motodiag/core/migrations.py` (schema 69 → 70);
- `SCHEMA_VERSION` 69 → 70 in `src/motodiag/core/database.py`;
- `tests/test_phase264_seasonal_breakin_valve.py`;
- `tests/test_phase260_ppi_chassis.py`: its "Zuma 125" head-state pin
  moves to "YW125Y" with the fix;
- a new finding for the generic winterization items' unsupported figures;
- F160 closed.

## Logic

1. **Migration 070**, inside the one-shot journal:
   - four `INSERT OR IGNORE` template rows (tier `individual`, system user
     1), then 28 items keyed on the slug sub-select;
   - one `UPDATE` of `generic_winterization_v1.description`, keyed on its
     slug and on the old text;
   - one `UPDATE` of `ppi_chassis_v1`'s items: the one unique phrase "The
     Zuma manual's adjustment" first, then "Zuma 125" → "YW125Y", across
     the six text fields.

   `rollback_sql` deletes the four templates' items and the templates,
   reverses the F160 text in the opposite order, and restores the
   generic description verbatim.
2. **Data flow:** migration journal (existing DBs) / `db init` (new DBs) →
   `workflow_templates` + `checklist_items` → the existing accessors →
   the existing click commands → the terminal.

## Key Concepts

- **Content on a door that already opens** (259–261's shape): one
  migration plus its pins.
- **Claims before text** (261): a claims list with verbatim anchors
  checked on their pages, then the text, then a cross-check mapping every
  "PDF p." in the seeded text back to a claim for the machine named
  before it.
- **A figure travels with its method.** "Cold" is three definitions:
  below 35 °C (Honda, Kymco), room temperature (Yamaha), and 20 °C (KTM's
  V-twins). Break-in is limited by engine speed, by throttle opening, or
  by engine performance. Each figure keeps its measure.
- **F158 and F124** as in 259–261.

## Decisions

- **D1: four templates, one per row**, each its own enum category, which
  already exists.
- **D2: one migration (070)** for the four templates and both live
  re-points (the operator's scope).
- **D3: 264 adds `winterization_v1`; the generic stays the quick starter**
  (S0-4). The generic's unsupported figures are filed, not fixed.
- **D4: valve adjustment is one template with optional per-engine-type
  items** (S0-4). Inline-four, boxer and desmodromic engines share one
  item, whose content is the negatives.
- **D5: powertrains** as S0-5.
- **D6: the F160 text is "YW125Y"**, the title page's model code, matching
  069's text. The document is "the Yamaha YW125Y 2009 service manual".
- **D7: route.** Subconscious GLM-5.3 did the first-pass extraction, in
  a proven sandbox (S0-7). Opus chose every figure from its page.

## Non-goals

- No new tables, repo functions, CLI commands, API routes or mobile
  screens.
- The generic winterization items, F158's `known_issues` references and
  F159 stay with their own work.
- No crash, track-day or emissions content (batch 3).

## Claims for the refute pass

Written at build, before the item text, in the phase log and in v1.1.

## Verification Checklist

- [ ] Migration 070 applies on a fresh `init_db` database;
      `SCHEMA_VERSION >= 70`; 070 found by name
- [ ] Upgrade 069 → 070 on a self-built 069 database changes exactly the 1
      template description and 3 chassis items named here, and adds exactly
      the four templates and their items
- [ ] `rollback_to_version(69)` restores every changed row byte-identical
      (except `updated_at`) and removes the new rows with no orphans;
      re-applying restores them
- [ ] Every migration keeps its rollback
- [ ] Each template: category, powertrains, tier, duration; item titles
      and sequence; the optional items exactly the planned ones
- [ ] Figures pinned per field; every machine-bound figure beside its
      machine; machines named as their documents name them, with no
      "Zuma" anywhere in the workflow tables
- [ ] N1–N5 stated where the items rely on them; the no-figure engine-type
      item carries no clearance figure
- [ ] F158 pins over the four templates and the re-pointed generic
      description
- [ ] `workflow list --category <each>` and `workflow show <slug>` for
      all four
- [ ] Known-bad controls planted, seen red, reverted
- [ ] Rule 3's four whole-tree checks, plus the F124 guard and the
      related suites, before every commit that touches the migration
- [ ] Regression of record by `regression.sh`
- [ ] Refute pass over every claim, with the phase log's `## Refuter pass`
- [ ] Backup, a dry run on a copy of live, the diff shown to the
      operator, and the live apply only on the operator's answer
