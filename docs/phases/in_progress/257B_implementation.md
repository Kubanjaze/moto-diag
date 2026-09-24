# Phase 257B — The per-vehicle transmission field

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-24

History: 1.0 the plan, after Step 0 (2026-09-24).

## Goal

A rider can set, change or clear their vehicle's transmission in the mobile
app, and that vehicle's diagnoses use it. The resolver already has an
`explicit` rung above the lookup (121 entries); nothing a rider can reach
writes to it, so every user machine the lookup does not name fails closed
(528 census spellings, F143). The rider's own answer wins, with provenance
`explicit`. Closes F121.

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

## Decisions

- **D1 — No migration.** The column, its CHECK and the model field exist.
  Existing vehicles are untouched because nothing writes to them; the live
  database is not migrated, so no backup is taken for this phase's code.
  (The close-out deploy still backs up, per the skill.)
- **D2 — API field.** `transmission: Optional[TransmissionLiteral]` on
  `VehicleCreateRequest` (default `None`), `VehicleUpdateRequest` and
  `VehicleResponse`. The literal is the six `VehicleTransmission` values, so
  OpenAPI carries an enum and the app's types are generated, not hand-typed.
- **D3 — Clear is an explicit `null`.** PATCH `{"transmission": null}`
  clears; omitting the key leaves it alone. The existing "`None` means not
  sent" behaviour is kept for every other field (none of them is clearable
  today, and changing that is out of scope).
- **D4 — Registry writes it.** Both inserts carry `vehicle.transmission`;
  the update whitelist gains `transmission`, with enum-to-value conversion
  like the others.
- **D5 — `/ask` receives the vehicle's value.** `VehicleContext` gains a
  `transmission` field, filled from the live vehicle row in
  `_build_vehicle_context` (the same row it already reads for make, model,
  year, mileage). The prompt text (`to_context_string`) is not changed.
  **`powertrain` is not wired into `/ask`**: doing so would move every
  electric vehicle with no transmission from `unknown` to the
  `powertrain-default` rung, which breaks finish-line item 2 ("unset means
  exactly today's behaviour"). Filed as a finding instead.
- **D6 — CLI diagnose already honours it** once the column is written
  (S0-5); a test proves the wiring rather than a code change.
- **D7 — Mobile.** The vehicle detail screen shows the field in view mode
  and offers the six choices plus "Not sure" in edit mode; "Not sure" sends
  `null`. The create screen is not changed: the goal names the vehicle
  screen, and a rider sets it there after adding the bike.
- **D8 — Labels say mechanism, in a rider's words**, from the enum's own
  definitions: Manual; Automatic (CVT, twist-and-go); Dual-clutch (DCT);
  Semi-auto, centrifugal clutch (Super Cub style); Semi-auto, actuated
  clutch (Y-AMT style); Direct drive (no gearbox).

## Non-goals

Showing the lookup's value as a suggestion in the app; bulk editing; any
change to the transmission lookup; the create screen; `powertrain` in
`/ask` (D5). Each is a follow-up, filed.

## Verification checklist

- [ ] POST with and without `transmission`; GET returns it; PATCH sets,
      changes, clears with `null`, and omitting the key leaves it alone
- [ ] an off-enum value is a 422, and the database CHECK still holds
- [ ] existing vehicles read back `transmission: null` and are unchanged
- [ ] resolver: explicit wins over the lookup; unset is byte-for-byte the
      lookup's answer (provenance and candidates)
- [ ] **E2E through the real API**: set → `/ask` retrieves with provenance
      `explicit` → clear → `/ask` back to `model-sourced`, rows follow
- [ ] CLI diagnose door reads the stored value (wiring test)
- [ ] mobile: types regenerated from a backend on 127.0.0.1; the detail
      screen renders the value, offers seven choices, "Not sure" sends
      `null`; jest, tsc and lint green
- [ ] break-it: each new test seen red with its line of code removed
- [ ] whole-tree gates on every pre-commit run; regression of record in
      both repos

## Risks

- A mock of `VisionAnalyzer` that stops tracking the real signature would
  stop testing the call (244L); the E2E reuses 244J's mock shape.
- The API's PATCH null semantics differ between `transmission` and the
  rest (D3). Documented on the schema so the app's author sees it.
