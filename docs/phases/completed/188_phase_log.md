# Phase 188 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-24 | **Completed:** 2026-04-26
**Repo:** https://github.com/Kubanjaze/moto-diag-mobile
**Branch:** `phase-188-vehicle-garage` (8 commits; rebase-merged to `main` at v1.1 finalize)

---

### 2026-04-24 — Plan v1.0 written, committed

Plan committed as `22158f3` on `main`. Scope: 3 screens (Vehicles list, VehicleDetail, NewVehicle) + 2 hooks (useVehicles, useVehicle) + 3 extracted components (Button, Field, SelectField) + navigation wiring + form-level validation over Phase 177's `/v1/vehicles` CRUD endpoints. Tier-aware 402 quota error surfacing. ~25 unit tests planned.

**Scope cut:** VIN scanner deferred to its own phase (camera + ML OCR is significant work; mixing into 188 would triple the surface).

**Commit plan:** 5 commits on feature branch.

---

### 2026-04-24 — Commit 1 (`2a9bd0d`): nav + screen stubs + Button

- src/components/Button.tsx (3 variants: primary/secondary/danger).
- src/screens/{VehiclesScreen, VehicleDetailScreen, NewVehicleScreen}.tsx (placeholder content).
- src/navigation/RootNavigator.tsx — RootStackParamList extended; 3 new Stack.Screen entries.
- src/screens/HomeScreen.tsx — "Open garage" button via new `Section` at top.
- 41 / 41 prior tests still green.

### 2026-04-24 — Commit 2 (`91e887c`): useVehicles + VehiclesScreen list

- src/hooks/useVehicles.ts — fetches /v1/vehicles, exposes {vehicles, listResponse, isLoading, error, refetch}; refetch is referentially stable.
- src/screens/VehiclesScreen.tsx — full FlatList with pull-to-refresh, empty state, error banner, quota footer ("individual tier · 4/5 slots remaining"), header "+ Add" button.
- src/types/api.ts — added VehicleResponse, VehicleCreateRequest, VehicleUpdateRequest aliases + Literal unions extracted via NonNullable<>.
- 7 new tests; 48 / 48 green.

### 2026-04-24 — Commit 3 (`10bfa35`): useVehicle(id) + VehicleDetailScreen view + delete

- src/hooks/useVehicle.ts — single-vehicle fetch with type-enforced path params.
- src/screens/VehicleDetailScreen.tsx — view mode with two detail cards + delete-with-confirm via api.DELETE.
- 4 new tests; 52 / 52 green.

### 2026-04-24 — Commit 4 (`9651a7f`): NewVehicleScreen form + Field/SelectField + create

- src/components/Field.tsx — labeled TextInput + 4 validation helpers (validateRequired/Year/OptionalInt/OptionalFloat) + 2 parsers.
- src/components/SelectField.tsx — Literal-enum dropdown (modal-style; no @react-native-picker dep).
- src/screens/NewVehicleScreen.tsx — full form with 3 section groups (Bike / OBD+powertrain / Notes), required-field validation, POST submit with 402 quota copy.
- 17 new tests (Field validators); 71 / 71 green.
- Build deviation: my first guess at the protocol enum was wrong (5 values vs the actual 13). TypeScript flagged it via the generated api-types — fixed with the canonical enum pulled from `src/api-types.ts`. Generated types are load-bearing; this would have been a runtime 422 caught at the gate.

### 2026-04-24 — Commit 5 (`9947615`): VehicleDetailScreen edit mode + README + version 0.0.3

- src/screens/VehicleDetailScreen.tsx — edit-mode toggle reusing Field + SelectField (~60 LoC of inline enum lists duplicated from NewVehicleScreen — to be extracted in commit 8).
- package.json + package-lock.json: 0.0.2 → 0.0.3.
- README.md: src/components/, src/hooks/, src/screens/ entries updated for new files.
- 71 / 71 green; tsc clean.

### 2026-04-26 — Architect gate ROUND 1: BLOCKED with detailed report

Kerwyn ran the 11-step smoke test on emulator. **7 / 11 steps green**:

✅ Auth persistence + cold-launch / Open garage + empty state / NewVehicle form opens / Read paths (list, pull-to-refresh, quota footer, detail view) / Edit-mode form opens with required asterisks / Delete works end-to-end / Phase 187 + Phase 186 no-regression.

❌ Step 5 partially blocked / Steps 6, 7 (real save → list) / Step 9 (edit save) / Step 11 (5+ bikes for quota test) — all blocked by 2 bugs:

**BUG 1 (BLOCKER):** Save fails with 422 on POST + PATCH for any payload. Backend logs: 5 × `POST /v1/vehicles HTTP/1.1 422 Unprocessable Content`. Kerwyn confirmed via curl that minimal `{"make":"Honda","model":"CBR600","year":2005}` POST works → vehicle id=1 created. Bug is mobile-app-side, not backend validation.

**BUG 2 (BLOCKER):** Error UX shows `[object Object]` instead of unwrapped 422 detail. User had no way to understand the failure without curl-debugging.

**NIT 1 (cosmetic):** VehicleDetailScreen view mode shows raw enum values (`ice`, `four_stroke`) — dropdowns in edit/create show friendly labels ("Internal combustion", "4-stroke"), so labels exist but view mode wasn't using them.

Architect recommendation: hold merge, fix Bug 1 + Bug 2 as blockers, Nit 1 as cleanup, re-smoke steps 5/6/7/9/11.

### 2026-04-26 — Diagnosis

**BUG 1 root cause traced to Phase 187 customFetch.** openapi-fetch wraps body + Content-Type into a Request object passed as `input`; `init` is undefined. Phase 187's customFetch read only `init?.headers` (always undefined for body-bearing methods), then passed `{headers: finalHeaders}` as init. Per fetch spec, init.headers REPLACES the Request's headers entirely. So Content-Type was stripped on POST/PATCH. Backend got body bytes with no Content-Type → couldn't parse → 422 HTTPValidationError. GET worked (no body), DELETE worked (no body in our DELETE calls), POST + PATCH broke.

**BUG 2 root cause:** describeError only knew RFC 7807 ProblemDetail (`{title, status, detail?}`). FastAPI's 422 response uses HTTPValidationError shape (`{detail: [{loc, msg, type, ...}]}`) — not wrapped in the Phase 175 envelope. isProblemDetail returned false → describeError fell through to String(err) → "[object Object]".

**NIT 1 root cause:** PROTOCOL_OPTIONS / PROTOCOL_LABELS / POWERTRAIN_* / ENGINE_TYPE_* duplicated inline in NewVehicleScreen and VehicleDetailScreen edit pane (~120 LoC). View mode had no labels because the labels lived in private screen modules.

### 2026-04-26 — Commit 6 (`7f3fc88`) FIX: customFetch preserves Request headers

src/api/client.ts customFetch rewritten:
- Read Request's headers FIRST (capturing Content-Type) when input is a Request instance.
- Overlay caller-supplied init.headers next.
- Add Accept + auth on top.
- Preserves Content-Type on body-bearing methods; harmless for GET.

__tests__/api/client.test.ts: 2 regression-guard tests (`'preserves Content-Type from Request on POST (commit-6 regression)'` + `'preserves Content-Type from Request on PATCH (commit-6 regression)'`) asserting init.headers passed downstream contains content-type: application/json. 73 / 73 tests green.

### 2026-04-26 — Commit 7 (`eb42c21`) FIX: describeError handles HTTPValidationError

src/api/errors.ts:
- Added HTTPValidationError + ValidationError types from generated api-types.
- isHTTPValidationError(x) narrowing predicate (detects `detail: array of {loc, msg, type, ...}` shape; rejects empty `detail: []` to avoid false positives).
- formatHTTPValidationError(e) renders one line per field error as "field: msg"; strips body/query/path/header/cookie loc prefixes.
- describeError() now checks HVE BEFORE ProblemDetail.

__tests__/api/errors.test.ts: 17 new tests covering HVE narrowing (7), formatting (7), describeError integration (3 — including a regression guard explicitly asserting no `[object Object]`). 90 / 90 tests green.

### 2026-04-26 — Commit 8 (`1ae92b6`) FIX: extract vehicleEnums + apply view-mode labels

src/types/vehicleEnums.ts (new):
- PROTOCOL_OPTIONS / PROTOCOL_LABELS (full Record, not Partial — TypeScript flags missing options if backend adds enum value).
- POWERTRAIN_* / ENGINE_TYPE_* (same pattern).
- labelFor(value, kind) helper for view-mode rendering. Falls back to raw value when unrecognized.

src/screens/NewVehicleScreen.tsx + VehicleDetailScreen.tsx: replace inline option lists + label maps with imports from vehicleEnums (60-line reduction each).

src/screens/VehicleDetailScreen.tsx view mode: Protocol / Powertrain / Engine type rows now use labelFor().

90 / 90 tests still green; tsc clean.

### 2026-04-26 — Architect gate ROUND 2: GATE PASSED

Kerwyn re-ran the 5 previously-blocked steps + bonus regression checks. All green:

- ✅ Step 5: required-field validation, no submit, helpful placeholders.
- ✅ Step 6: real save, no [object Object], auto-nav to list. **Commit-6 customFetch verified on POST.**
- ✅ Step 7: list render + quota footer (4/5 remaining).
- ✅ Step 9A: enum labels readable in detail view (None (no OBD), Internal combustion, 4-stroke, BMS = No). **Commit-8 nit fix verified.**
- ✅ Step 9B: edit save via PATCH, Protocol None → OBD-II, no error. **Commit-6 customFetch verified on PATCH.**
- ✅ Step 11: 6th-bike attempt at 5/5 produced readable 402 alert ("Upgrade needed / Vehicle quota exceeded for current subscription tier / vehicle quota exceeded: 5/5 (individual tier)"). **Commit-7 describeError verified on 402.**

**Bonus regression-guard verification:** During fill-to-5/5, a free-text "lithium-ion" entry in the battery_chemistry field triggered a backend BatteryChemistry enum validation HVE. Alert rendered cleanly as "Validation error: 'lithium-ion' is not a valid BatteryChemistry" — second independent confirmation of Commit 7's HVE unwrap on a different code path.

No Phase 186 BLE or Phase 187 auth regressions.

**Filed as post-merge follow-up (NOT blocking):** Battery chemistry should be a SelectField, not a free-text Field. Logged in `docs/FOLLOWUPS.md`.

**Architect cleared for v1.1 finalize.**

### 2026-04-26 — v1.1 finalize (this commit)

- Plan → v1.1: all Verification Checklist items `[x]`, Deviations section captures the 2 latent Phase 187 bugs found + 3-fix-commit response + the round-1/round-2 gate process, Results table with final numbers + commit hash chain, Key finding documenting the "transport bugs hide in GET-only test surfaces" lesson for the rest of Track I.
- Phase log → this file (timestamped milestones from plan v1.0 through finalize).
- Move both files from `docs/phases/in_progress/` → `docs/phases/completed/`.
- New `docs/FOLLOWUPS.md` capturing Nit 2 (battery_chemistry dropdown).
- Project `implementation.md` version bump 0.0.4 → 0.0.5; Phase 188 row added to Phase History.
- Project `phase_log.md` Phase 188 closure entry.
- Mobile `docs/ROADMAP.md` Phase 188 marked ✅.
- Backend `moto-diag/docs/ROADMAP.md` Phase 188 marked ✅.
- Rebase-merge `phase-188-vehicle-garage` → `main` (8 commits, fast-forward).
- Delete feature branch local + remote.

**Phase 188 closes green. Track I scorecard: 4 of 20 phases complete (185 / 186 / 187 / 188).** Next: **Phase 189 — DTC code lookup screen** (search by code or text, voice input deferred to its own phase, offline DTC database from Phase 198).
