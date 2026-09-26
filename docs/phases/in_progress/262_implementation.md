# Phase 262 — Track N batch 3: crash support, track-day preparation, and emissions compliance (California first)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-26

**Branch:** `phase-262` (Opus session, main checkout).

**Carries three ROADMAP rows** (the operator's batching): 262 crash and
insurance claim support, 263 track-day and race prep, 267 emissions and
smog compliance. One Step 0, one migration, one regression, one
close-out, one handoff. The ledger convention is 261's and 264's:
- row 262 closes with its CLOSED date and the regression line;
- rows 263 and 267 close ✅ "folded into 262" with no date of their own;
- one history row (262) and one handoff.

## Goal

Three shop protocols as workflow content on the Phase 114 substrate, one
template per row, reachable through `motodiag workflow list/show`, plus
three fixes to live rows in the same migration:

| row | slug | category | powertrains | items (optional) |
|---|---|---|---|---|
| 262 | `crash_support_v1` | `crash_support` | ice, electric, hybrid | 8 (the claim record; both California items) |
| 263 | `track_prep_v1` | `track_prep` | ice, hybrid | 6 (none) |
| 267 | `emissions_v1` | `emissions` | ice, hybrid | 7 (the evaporative system) |

Scope is the operator's answer to Step 0's fork (`262_step0.md`, S0-4):
- **262:** the makers' post-crash inspection, plus California's salvage
  and total-loss rules from the DMV's own text. Photo documentation,
  damage estimation and insurance claims are stated as unsourced (N9).
- **263:** the makers' track preparation. Safety wire, race coolant,
  tech inspection and number plates are stated as the sanctioning
  body's rules; no maker's document in the library gives them (N10–N12).
- **267:** the makers' emission pages plus the regulators' own text
  (BAR, CARB, DMV, EPA), acquired by script (S0-8).
- **Provenance:** named in the text ("California DMV, Vehicle Industry
  Registration Procedures Manual, 19.015"); the claims table records
  provenance `regulation` or `maker` per claim. No schema change.

Every figure an item states names its machine and cites that machine's
document and PDF page. Every rule from a regulator names the regulator
and the document (a web page is cited by its section title, as it has no
pages). Machines and documents are named from their title pages.

**Three live-row fixes, in the same migration** (the operator's scope):
1. **F161:** `generic_winterization_v1`'s unsupported figures go:
   - item 6's "Run engine 5 minutes to circulate", stated as universal,
     and its expected_fail;
   - item 7's "recommended winter weight (typically 10W-40)";
   - item 8's expected_pass "reading float voltage (13.2V-13.6V)".

   Each becomes a pointer to `winterization_v1`, which gives each maker's
   own figure with its page. The brand "Sta-Bil" in item 6's sentence goes
   with the figure (no maker's document names a product). Item 9 carries
   no figure and is not changed.
2. **F162:** `ppi_chassis_v1` item 18:
   - "the YW125Y service manual calls the same movement binding or
     looseness (PDF p. 93)" becomes "checks the same movement for binding
     or looseness";
   - "the KTM 250/300 EXC owner's manual (PDF p. 76)" in its description
     names the manual 260 cited: "the KTM 2022 250/300 EXC TPI owner's
     manual".
3. **W30:** `winterization_v1` item 56's Beverly sentence gets its first
   adversarial read in refute round 1. It is kept, fixed or dropped on
   the verdict.

CLI: none new.

Outputs:
- migration 071 `crash_track_emissions_workflows` in
  `src/motodiag/core/migrations.py` (schema 70 → 71);
- `SCHEMA_VERSION` 70 → 71 in `src/motodiag/core/database.py`;
- `tests/test_phase262_crash_track_emissions.py`;
- `tests/test_phase264_seasonal_breakin_valve.py`: its F162 head-state
  pin moves with the fix (and item 5's pins, if W30 changes);
- F161 and F162 closed at the live apply.

## Logic

1. **Migration 071**, inside the one-shot journal:
   - three `INSERT OR IGNORE` template rows (tier `individual`, system
     user 1), then 21 items keyed on the slug sub-select;
   - F161: three `UPDATE`s on `generic_winterization_v1`'s items, each
     keyed on the template's slug, the item's sequence number and the
     item's exact old text;
   - F162: one `UPDATE` on `ppi_chassis_v1`'s steering item, keyed on
     its exact old text;
   - W30: on the verdict.

   `rollback_sql` deletes the three templates' items and the templates,
   and restores every changed field verbatim, keyed on its new text.
2. **Data flow:** migration journal (existing DBs) / `db init` (new DBs) →
   `workflow_templates` + `checklist_items` → the existing accessors →
   the existing click commands → the terminal.

## Key Concepts

- **Content on a door that already opens** (259–264's shape).
- **Claims before text** (261): a claims list with verbatim anchors
  checked on their pages (`s0/claims262.py`, `s0/verify262.py`), then the
  text, then a cross-check that maps every "PDF p." and every regulator
  citation in the seeded text back to a claim (`s0/xcheck262.py`).
- **Regulator text is not a manual.** It is authoritative on what the
  law requires and says nothing about how a given machine behaves; the
  items keep the two apart and name which is which.
- **A negative is part of the content** where the row asks for something
  no document gives (photo standards, safety wire).
- **F158 and F124** as in 259–264.

## Decisions

- **D1: three templates, one per row**, each in its own existing enum
  category.
- **D2: one migration (071)** for the templates and the three fixes (the
  operator's scope).
- **D3: the regulators' text is acquired by script** (`acquire.py`'s
  Fetcher and `save()`), never by a model (F141), and only from hosts whose
  robots.txt permits it. leginfo and the eCFR API are excluded (S0-8).
- **D4: provenance in the text**, per the operator (S0-4).
- **D5: powertrains.** `crash_support_v1` all three. `track_prep_v1`
  and `emissions_v1` ICE and hybrid: every track document in the library
  is an ICE machine's, and an electric machine has no exhaust or
  evaporative emissions. S0-5 proposed all three for track prep. Measured
  against the documents, none speaks for an electric machine on a track.
- **D6: California first, and only California,** for the salvage and
  smog items. Other states' rules are not in the library.
- **D7: route.** Subconscious GLM-5.3 did the first-pass extraction in a
  proven sandbox (S0-7). Its quotes were checked on their pages: 250 of
  325 were there. Opus chooses every figure from the page itself.

## Non-goals

- No new tables, columns, repo functions, CLI commands, API routes or
  mobile screens.
- No state other than California for the salvage or smog items.
- No photo, estimating or insurance-claim standard is invented (N9).
- No race-organiser rules are invented (N10–N12).
- F158's `known_issues` references and F159 stay with their own work.

## Planned items

**`crash_support_v1`** — 1 safety, the law and the first look; 2 frame
(check, and change rather than repair); 3 handlebar and controls (replace,
never straighten); 4 front fork; 5 axles and wheels (runout against the
machine's limit); 6 hidden damage and the qualified check; 7 the claim
record (optional; N9); 8 California: total loss, salvage certificate, and
registering a repaired total loss (optional).

**`track_prep_v1`** — 1 intended use and warranty; 2 road equipment off
(mirrors, number-plate carrier, turn indicators) and back on for the
road; 3 suspension for the rider and the track; 4 rider aids on a closed
track; 5 service intervals when raced; 6 what the sanctioning body sets
(safety wire, coolant, tech inspection, number plates: N10–N12).

**`emissions_v1`** — 1 California Smog Check and motorcycles; 2 what
standard it was built to (the label, the California model, CARB's
Executive Order); 3 tampering: what counts and what the law says;
4 aftermarket parts and the CARB Executive Order label; 5 the catalytic
converter; 6 the evaporative system (optional); 7 emission maintenance,
records and the warranty.

## Claims for the refute pass

Filled at the build: every fact the seeded text states, with its library
path and PDF page (or regulator section), its verbatim anchors, and its
provenance.

## Verification Checklist

- [ ] Migration 071 applies on a fresh `init_db` database;
      `SCHEMA_VERSION >= 71`; 071 found by name
- [ ] Upgrade 070 → 071 on a self-built 070 database changes exactly the
      scoped item rows (F161's three, F162's one, W30's if it changes) and
      adds exactly the three templates and their items
- [ ] `rollback_to_version(70)` restores every changed row byte-identical,
      removes the new rows with no orphans, and re-applies
- [ ] Every migration keeps its rollback
- [ ] Each template: category, powertrains, tier, duration; titles and
      sequence; optional items exactly as planned
- [ ] Figures pinned per field; every machine-bound figure beside its
      machine; every regulator rule beside its regulator
- [ ] The negatives stated where the items rely on them
- [ ] F161: no "10W-40", "13.2", "5 minutes" or "Sta-Bil" in the generic
      items; F162: the two sentences as planned
- [ ] F158 pins over the three templates and the changed rows
- [ ] `workflow list --category <each>` and `workflow show <slug>` for
      all three
- [ ] Known-bad controls planted, seen red, reverted
- [ ] Rule 3's four whole-tree checks, plus the F124 guard and the related
      suites, before every commit that touches the migration
- [ ] Regression of record by `regression.sh`
- [ ] Refute pass over every claim and W30; after the last fix round,
      every claim whose text changed is re-read
- [ ] Backup, a dry run on a copy of live, the F158 census on the copy,
      and the diff with before and after text for every changed row, to
      the operator. The live apply and the merge wait for the operator's
      answer (rule 1)

## Risks

- **Regulator pages change.** A web page is not a fixed edition. Each is
  kept with its sha256 and fetch time; the text cites the page as fetched
  on 2026-09-26.
- **A rule read as a machine fact, or the reverse.** Mitigated by naming
  the regulator beside every rule and the machine beside every figure.
- **Figures read as universal.** Mitigated by `MACHINE_OF` pins.
- **Refute fixes introduce defects** (264's key finding). Mitigated by a
  final re-read of every claim whose text changed.
