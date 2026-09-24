# Phase 257B — The per-vehicle transmission field

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-24 (close-out)

History: 1.0 the plan, after Step 0 (2026-09-24, `f4889a9`); **1.1 the
close-out** — every section annotated *As built*, the checklist ticked with
its evidence, Deviations and Results added.

## Goal

A rider can set, change or clear their vehicle's transmission in the mobile
app, and that vehicle's diagnoses use it. The resolver already has an
`explicit` rung above the lookup (121 entries); nothing a rider can reach
writes to it, so every user machine the lookup does not name fails closed
(528 census spellings, F143). The rider's own answer wins, with provenance
`explicit`. Closes F121.

*As built:* all five finish-line items are met (Results). F121 is closed;
its remaining part, the create screen, is F147.

## Step 0 — greenfield, extension or reshape?

**Extension, smaller than the plan feared.** Grepped the plan's nouns in
`src/` and the mobile `src/`; read the live database on a copy.

| # | measured | where |
|---|---|---|
| S0-1 | `vehicles.transmission` **already exists**: nullable TEXT, CHECK over the six values, no default | migration 063 (Phase 255), `core/migrations.py:4383` |
| S0-2 | live `data/motodiag.db` is schema **66**; **10** vehicles, **0** with a transmission | copy in the scratchpad, `sqlite3` |
| S0-3 | `VehicleBase.transmission: Optional[VehicleTransmission] = None` exists | `core/models.py:169` |
| S0-4 | `resolve_transmission(..., explicit=)` exists and answers `explicit` first; an unrecognised value logs and falls through | `knowledge/transmission.py:972` |
| S0-5 | all four doors pass `transmission` to `rows_for_machine`: CLI diagnose (`vehicle.get("transmission")`), predictor, priority_scorer, video `/ask` | `grep rows_for_machine(` = 4 callers |
| S0-6 | **but** `add_vehicle` / `add_vehicle_for_owner` never INSERT it, and `update_vehicle`'s whitelist omits it: nothing can write the column | `vehicles/registry.py:60, 201, 127` |
| S0-7 | the vehicle API's create, update and response schemas have no `transmission` | `api/routes/vehicles.py:66, 84, 104` |
| S0-8 | PATCH drops every `None` (`if v is not None`), so a clear cannot be expressed today | `api/routes/vehicles.py:299` |
| S0-9 | **`/ask`, the API's only retrieval door, passes `getattr(context, "transmission", None)` on a `VehicleContext` that has no such field: it is `None` for every vehicle, always.** Same for `powertrain` | `api/routes/videos.py:548`, `media/vision_types.py:262` |
| S0-10 | no session endpoint runs a diagnosis; the app's diagnosis surface over the API is video `/ask` | `api/routes/sessions.py` |
| S0-11 | mobile: `VehicleDetailScreen.tsx` has a view and an edit pane; enum options and labels live in `src/types/vehicleEnums.ts`; types come from `npm run refresh-api-schema` + `generate-api-types` | mobile repo |

No fork: the field lives where Phase 255 put it, and the backend change is
smaller than one nullable column — no migration at all.

*As built:* S0-2 re-checked at close-out, below (Results). Every other row
held.

## Decisions

- **D1 — No migration.** The column, its CHECK and the model field exist.
  Existing vehicles are untouched because nothing writes to them; the live
  database is not migrated, so no backup is taken for this phase's code.
  (The close-out deploy still backs up, per the skill.)
  *As built:* no migration. The close-out took **no** backup either, for
  257's reason: nothing in 257B writes the live database (phase log,
  "Deploy").
- **D2 — API field.** `transmission: Optional[TransmissionLiteral]` on
  `VehicleCreateRequest` (default `None`), `VehicleUpdateRequest` and
  `VehicleResponse`. The literal is the six `VehicleTransmission` values, so
  OpenAPI carries an enum and the app's types are generated, not hand-typed.
  *As built:* as planned; `test_openapi_carries_the_six_values` pins the
  enum on all three schemas.
- **D3 — Clear is an explicit `null`.** PATCH `{"transmission": null}`
  clears; omitting the key leaves it alone. The existing "`None` means not
  sent" behaviour is kept for every other field.
  *As built:* as planned, and stated in the field's OpenAPI description so
  the app's author sees it. A test pins that `notes: null` still means "not
  sent".
- **D4 — Registry writes it.** Both inserts carry `vehicle.transmission`;
  the update whitelist gains `transmission`.
  *As built:* the enum-to-value conversion planned alongside was **dropped**
  (Deviations).
- **D5 — `/ask` receives the vehicle's value.** `VehicleContext` gains a
  `transmission` field, filled from the live vehicle row in
  `_build_vehicle_context`. The prompt text is not changed. **`powertrain`
  is not wired into `/ask`**: doing so would move every unset electric
  vehicle from `unknown` to `powertrain-default`, which breaks finish-line
  item 2. Filed.
  *As built:* as planned, with the read in its **own** query (bug fix #1).
  `powertrain` is F144.
- **D6 — CLI diagnose already honours it** once the column is written; a
  test proves the wiring rather than a code change.
  *As built:* `TestTheCliDoorReadsIt` drives `_run_quick` on a stored
  `manual` PCX150: provenance `explicit`, the manual row in, the CVT row out.
- **D7 — Mobile.** The vehicle detail screen shows the field and offers the
  six choices plus "Not sure", which sends `null`. The create screen is not
  changed.
  *As built:* as planned; the create screen is F147.
- **D8 — Labels say mechanism, in a rider's words.**
  *As built:* Manual (clutch lever, you shift) · Automatic CVT
  (twist-and-go) · Dual-clutch (DCT) · Semi-auto, no clutch lever (Super
  Cub style) · Semi-auto, electronic clutch (Y-AMT style) · Direct drive
  (no gearbox); unset reads "Not sure" in both panes.

## Non-goals

Showing the lookup's value as a suggestion in the app; bulk editing; any
change to the transmission lookup; the create screen; `powertrain` in
`/ask` (D5). Each is a follow-up, filed.

*As built:* filed as F145 (suggestion), F146 (bulk editing), F147 (create
screen) in the mobile file, and F144 (`powertrain`) here. The lookup is
untouched: `knowledge/transmission.py` has no diff.

## Verification checklist

- [x] POST with and without `transmission`; GET returns it; PATCH sets,
      changes, clears with `null`, and omitting the key leaves it alone —
      `TestTheApiStoresIt`, incl. all six values round-tripped
- [x] an off-enum value is a 422 (POST and PATCH, four spellings), and the
      database CHECK still holds (`IntegrityError` on `'automatic'`)
- [x] existing vehicles read back `transmission: null` and are unchanged —
      a row inserted the pre-257B way compares byte-equal before and after a
      neighbour is set; live DB re-read at close-out (Results)
- [x] resolver: explicit wins over the lookup; unset equals the lookup's
      answer (`TestTheResolverOrder`)
- [x] **E2E through the real API**: set → `/ask` retrieves with provenance
      `explicit` → clear → `/ask` back to `model-sourced`, rows follow
      (`TestEndToEnd::test_set_ask_clear_ask`; only frame extraction and the
      vision call are stubbed)
- [x] CLI diagnose door reads the stored value (`TestTheCliDoorReadsIt`)
- [x] mobile: types regenerated from a backend on 127.0.0.1 (the schema diff
      is the field only); the detail screen renders the value, offers seven
      choices, "Not sure" sends `null`; jest 1174 / tsc 0 / eslint 0 errors
- [x] break-it: backend **10/10** mutations, mobile **6/6**; both bug
      fixes' guards seen red without their fix
- [x] whole-tree gates on every pre-commit run; regression of record in
      both repos (Results)

## Risks

- A mock of `VisionAnalyzer` that stops tracking the real signature would
  stop testing the call (244L); the E2E reuses 244J's mock shape.
  *As built:* same signature as 244J's.
- The API's PATCH null semantics differ between `transmission` and the
  rest (D3). Documented on the schema.

## Deviations

- **The enum conversion in `update_vehicle` was dropped.** Planned under D4
  for symmetry with the four enums beside it. Measured: sqlite binds a
  `str` enum member as its value unaided, so the line did nothing and no
  mutation of it could fail a test (S9). The existing four are untouched.
- **Two bug fixes the plan did not foresee.** #1: widening
  `_build_vehicle_context`'s live-row SELECT made it all-or-nothing on a
  table without the column (caught by 244B's test). #2: the finding
  contract pinned which FOLLOWUPS file leads, and filing 257B's app
  findings where their code is flipped it. #2 changed a test outside this
  phase's subject; its reasoning and the skill's changelog entry are in the
  register.
- **`COLLECTED_TEST_FLOOR` rose by 40, not 26.** 14 are
  `test_roadmap_continuity.py`, added by `76edc69` (the rule change between
  257 and 257B) and never added to the floor.
- **F148 filed from reading the close-out's own check**: A7's
  version-header half is keyed to the first history row, which is 244M, so
  it cannot fire for any other phase. Not fixed here.

## Results

| | before 257B | after 257B |
|---|---|---|
| a rider can set / change / clear the transmission | no (no writer anywhere) | **yes**: API create + PATCH (null clears); app vehicle screen |
| provenance a rider's machine can reach | model-sourced / ambiguous / powertrain-default / unknown | **+ explicit**, first |
| `/ask` sees the vehicle's value | never (getattr on a missing field) | **yes** (E2E) |
| schema | 66 | 66 (no migration) |
| live DB at close-out (fresh copy) | 10 vehicles, 0 transmissions | **unchanged**: 10 / 0, 1,046 `known_issues`, main file mtime 2026-09-22 16:25 |
| 257B tests | 0 | backend **25** (`test_phase257B_transmission_field.py`), mobile **10** (7 screen + 3 enum) |
| mutations | — | backend **10/10**, mobile **6/6** |
| bug fixes | — | 2 (`8e039e7`, `df82a21`) |
| findings | — | F144, F145, F146, F147, F148 filed; F121 closed |
| `COLLECTED_TEST_FLOOR` | 8959 | **8999** |
| backend regression | 8959 at `b8382b5` (257) | **8999 passed, 0 failed, 0 skipped** at `d91c243`, 48:31 |
| mobile regression | — | **1174 passed / 96 suites**, tsc 0, at `0e1ed53` (code) / `0a339d1` (branch tip) |

The E2E runs through HTTP end to end: a Honda PCX150 (lookup `cvt`) asks
with the CVT row and without the manual one; set to `manual`, the same
question resolves `explicit` and the rows swap; cleared, it is back to
`model-sourced` and the CVT row.
