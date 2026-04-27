# Phase 189 — Diagnostic Session UI (mobile)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-27 | **Status:** ✅ Complete

## Goal

Give the mechanic a real "sessions" surface on mobile — start / view / append-to / close diagnostic sessions over Phase 178 `/v1/sessions/*` HTTP, backed by the Phase 187 typed client. This is the **canonical mechanic workflow** for MotoDiag (a session is the unit of work that holds symptoms, fault codes, diagnosis text, severity, confidence, cost estimate, and a status lifecycle), so it gets the first tab next to "My garage" and is the headline addition of Track I post-188.

Three new screens (Sessions list, NewSession, SessionDetail) + 2 hooks (`useSessions`, `useSession(id)`) + the **first bottom-tab navigation** in the app (Home / Garage / Sessions) + form validation for the create flow + targeted append/lifecycle/diagnosis-edit mutations on the detail screen.

Roadmap was swapped at plan time: **Phase 189 was originally "DTC code lookup screen"** and Phase 190 was "Interactive diagnostic session." We swapped because (a) the session UI is the load-bearing workflow — DTC lookup is a sub-surface that's most useful *inside* a session — and (b) it's the screen that proves the bottom-tab nav, the session-quota footer, the lifecycle buttons, and the FastAPI 402-quota / 422-validation error paths from a body-bearing route. DTC lookup as a standalone screen + tap-from-SessionDetail integration becomes Phase 190.

DTC tap-to-resolve (`GET /v1/kb/dtc/{code}`) is **deferred to Phase 190**. Phase 189's DTC list shows raw codes only.
Voice input for symptoms / notes is **deferred to Phase 195** per ROADMAP.
Freeze-frame display is **deferred** entirely (Phase 197 live-data screen has the better surface).
F1 follow-up from Phase 188 (battery_chemistry should be a `SelectField` not free-text) is **folded in as Commit 1** — small, demonstrates the vehicleEnums.ts pattern works for closed-set Pydantic Literals, and ships the post-merge follow-up before it rots.

CLI — none (mobile has no CLI).

## Outputs

**New files (12 — plan said 8; 4 extras emerged for testability + nav modularity):**
- `src/screens/SessionsListScreen.tsx` — list view. Pull-to-refresh. Empty state with "Start your first session" CTA. Tap row → SessionDetail. Footer shows tier + monthly quota ("individual tier · 49/50 sessions remaining this month") using session-shaped keys (`total_this_month` / `monthly_quota_limit` / `monthly_quota_remaining`). Per-row `StatusBadge` (open / in_progress / closed).
- `src/screens/SessionDetailScreen.tsx` — single session view. Six cards: **Vehicle** (read-only) → **Symptoms** (read-only list + always-visible inline append input) → **Fault codes** (same shape, monospace + auto-uppercase on append) → **Diagnosis** (view-mode read-only with prettified severity via `renderSeverityForView`; edit-mode toggles a full form with diagnosis text + severity SelectField + custom-severity Field + confidence 0-1 + cost estimate ≥ 0) → **Notes** (read-only string + multiline append input) → **Lifecycle** (status badge + Created/Closed timestamps + Close/Reopen button per current status).
- `src/screens/NewSessionScreen.tsx` — form. Required: vehicle make / model / year, both freehand AND tap-to-fill from `useVehicles`-backed garage list. Optional initial symptoms (multiline, newline-separated to allow commas inside symptoms) + fault codes (comma-separated, uppercased on submit). Submit → POST `/v1/sessions` → `navigation.replace` to SessionDetail of the new session (back-button skips the form).
- `src/screens/sessionFormHelpers.ts` — pure helpers `packSymptoms` + `packFaultCodes` for input parsing. Lives outside the screen so unit tests can import without pulling the api/keychain/openapi-fetch graph through the screen entry point.
- `src/hooks/useSessions.ts` — `{sessions, listResponse, isLoading, error, refetch}` wrapping `api.GET('/v1/sessions')`. Refetches on focus.
- `src/hooks/useSession.ts` — `{session, isLoading, error, refetch}` single-session hook for `api.GET('/v1/sessions/{session_id}')`.
- `src/navigation/RootNavigator.tsx` (rewritten) — bottom-tab navigator (`@react-navigation/bottom-tabs` v7.15.10). Three tabs: HomeTab / GarageTab / SessionsTab.
- `src/navigation/HomeStack.tsx` — single-screen native-stack for the Home tab.
- `src/navigation/GarageStack.tsx` — native-stack for the Garage tab (Vehicles / VehicleDetail / NewVehicle, Phase 188 surface unchanged).
- `src/navigation/SessionsStack.tsx` — native-stack for the Sessions tab (Sessions / SessionDetail / NewSession).
- `src/navigation/types.ts` — `RootTabParamList` + per-tab param-lists.
- `src/types/sessionEnums.ts` — `SeverityLiteral` (`'low' | 'medium' | 'high' | 'critical'`) + `SEVERITY_OPTIONS` + `SEVERITY_LABELS` + 3 helpers per the Commit 6 sign-off sketch: `deriveSeverityState` (decompose backend value → screen state), `packSeverityForSubmit` (pack screen state → PATCH body), `renderSeverityForView` (pretty closed labels + verbatim custom values).

**Modified files (10):**
- `src/components/SelectField.tsx` — discriminated-union props with `nullable` discriminator. Existing closed-required call sites (protocol/powertrain/engine_type) unchanged. New nullable variant adds opt-in `allowNull` (renders "—" clear row) + `allowCustom` (renders "Other…" row + supports customValue round-trip-display via the trigger). Pure helpers `buildSelectRows` + `getTriggerDisplay` exported for unit tests.
- `src/components/Field.tsx` — converted to `forwardRef<TextInput, Props>` so callers can imperatively focus the underlying TextInput (used by the severity custom-value Field on Other… selection).
- `src/screens/HomeScreen.tsx` — dropped the "My garage" Section (Garage is its own tab now); dropped `useNavigation` / `NativeStackNavigationProp` / `Button` imports (unused after removal); subtitle "v0.0.3 · Phase 188 scaffold" → "v{appVersion} · Phase 189".
- `src/screens/NewVehicleScreen.tsx` — battery_chemistry: `Field` → `SelectField<BatteryChemistryLiteral>` with `nullable allowNull` (F1 follow-up resolution). Param-list type swap `RootStackParamList` → `GarageStackParamList`.
- `src/screens/VehicleDetailScreen.tsx` — battery_chemistry: edit mode swaps `Field` for `SelectField`; view mode uses `labelFor()` for friendly label. Param-list type swap.
- `src/screens/VehiclesScreen.tsx` — param-list type swap `RootStackParamList` → `GarageStackParamList`.
- `src/types/api.ts` — added `SessionListResponse` / `SessionResponse` / `SessionCreateRequest` / `SessionUpdateRequest` / `SymptomRequest` / `FaultCodeRequest` / `NoteRequest` / `SessionStatusLiteral` aliases pulled from generated api-types. Added `BatteryChemistryLiteral` (manually defined — backend exposes the field as bare `Optional[str]` even though the route handler enforces a closed enum at the boundary).
- `src/types/vehicleEnums.ts` — added `BATTERY_CHEMISTRY_OPTIONS` (5 values: `li_ion` / `lfp` / `nmc` / `nca` / `lead_acid`) + `BATTERY_CHEMISTRY_LABELS`. Extended `labelFor()` switch to include `'battery_chemistry'` kind.
- `package.json` + `package-lock.json` — added `@react-navigation/bottom-tabs@^7.15.10`; bumped `version` 0.0.3 → 0.0.4.
- `README.md` — Status updated to Phase 189; tech-stack entry expanded for bottom-tabs; project-structure tree refreshed; testing section bumped to "162 tests as of Phase 189 commit 6" + explicit list of helper-test coverage + transport-regression guards.

**Plan dropped:** `src/api/index.ts` re-export of session-shaped aliases. Not needed in practice — screens import from `../types/api` directly without ergonomic friction.

**New tests (5 files, 72 new tests vs ~25-30 planned — overshot for completeness):**
- `__tests__/components/SelectField.test.ts` — 18 tests covering `buildSelectRows` (closed-set / allowNull / allowCustom / both) and `getTriggerDisplay` (selected label / null label / placeholder / "Other: customValue" round-trip / defensive cases).
- `__tests__/types/vehicleEnums.test.ts` — 10 tests covering battery_chemistry options + labels completeness, `labelFor` battery_chemistry round-trip, legacy off-enum fall-through, regression spot-checks for protocol/powertrain/engine_type.
- `__tests__/hooks/useSessions.test.ts` — 8 tests mirroring `useVehicles` patterns + one explicit guard test asserting session-shaped quota keys (`total_this_month` / `monthly_quota_*`) are present and vehicle-shape keys are absent.
- `__tests__/hooks/useSession.test.ts` — 5 tests (path-param passthrough, loading→success, 404 ProblemDetail, refetch invocation + state update, refetch referential stability).
- `__tests__/screens/NewSessionScreen.test.ts` — 9 tests on `packSymptoms` + `packFaultCodes` (empty handling, newline + CRLF splits, comma-preservation in symptoms, DTC uppercasing + dropping empties).
- `__tests__/types/sessionEnums.test.ts` — 20 tests on SEVERITY_OPTIONS shape + label-map completeness + `deriveSeverityState` (null / closed / off-enum / case-sensitive) + `packSeverityForSubmit` (choice / custom / both-empty / whitespace / invariant defense) + `renderSeverityForView` (closed prettified vs custom verbatim) + a 3-test round-trip integration block proving `derive → pack` survives all three logical states unchanged.
- `__tests__/api/client.test.ts` — extended with 2 new regression-guard tests asserting Content-Type + X-API-Key preserved on `POST /v1/sessions/{id}/symptoms` (body-bearing) and X-API-Key + Accept + correct path-param URL on `POST /v1/sessions/{id}/close` (empty-body).

Phase 188 contracted regression-guard pattern held: every new HTTP verb code path is implicitly a Phase 187 transport-regression check; the 2 explicit guards in `client.test.ts` are belt-and-suspenders.

**New runtime dep:** `@react-navigation/bottom-tabs` (latest 7.x — same major as `@react-navigation/native` 7.2.2 already present). No new native modules — relies on `react-native-screens` + `react-native-safe-area-context` already installed for native-stack.

**No backend changes.** No schema changes (backend still v38). No new ADR (the bottom-tab decision is small enough that the ADR-001 React Navigation choice covers it; if Track I bring more nav surface, ADR may be revisited).

**Package version:** `0.0.3 → 0.0.4`.
**Project implementation.md version:** `0.0.5 → 0.0.6` on phase close.

## Logic

### Backend surfaces consumed

All from Phase 178, all gated by `Depends(get_current_user)` + monthly session quota (`TIER_SESSION_MONTHLY_LIMITS`: individual=50 / shop=500 / company=unlimited per month).

| Method | Path                                  | Purpose                                                 | Phase 189 caller |
|--------|---------------------------------------|---------------------------------------------------------|------------------|
| GET    | `/v1/sessions`                        | List sessions + monthly quota metadata                  | useSessions      |
| POST   | `/v1/sessions`                        | Create new session (quota-checked)                      | NewSessionScreen |
| GET    | `/v1/sessions/{session_id}`           | Single session fetch                                    | useSession       |
| PATCH  | `/v1/sessions/{session_id}`           | Update diagnosis/severity/confidence/cost_estimate      | SessionDetailScreen edit-mode |
| POST   | `/v1/sessions/{session_id}/symptoms`  | Append a symptom string                                 | SessionDetailScreen |
| POST   | `/v1/sessions/{session_id}/fault-codes` | Append a fault code string                            | SessionDetailScreen |
| POST   | `/v1/sessions/{session_id}/notes`     | Append a note string (concatenates to `notes` field)    | SessionDetailScreen |
| POST   | `/v1/sessions/{session_id}/close`     | Close session (status → closed)                         | SessionDetailScreen |
| POST   | `/v1/sessions/{session_id}/reopen`    | Reopen a closed session                                 | SessionDetailScreen |

**8 distinct POSTs across the phase.** Each is implicitly a Phase 187 transport-regression check (Phase 188 lesson). Two new POST guards in `client.test.ts` belt-and-suspender this.

**One critical schema difference vs Phase 188:**

Vehicles list uses `{items, total, tier, quota_limit, quota_remaining}`.
Sessions list uses `{items, total_this_month, tier, monthly_quota_limit, monthly_quota_remaining}`.

These are NOT parity. The hook + footer must use the session-shaped keys. TypeScript catches the difference at compile time (the generated `api-types.ts` has both shapes), but the convention is worth calling out so a copy-paste from the vehicles hook doesn't silently render `undefined`.

Sessions quota is **monthly** (resets each calendar month) vs vehicles' **active count**. UI copy reflects this: "47 / 50 sessions this month" not "47 / 50 sessions".

### Navigation refactor (the biggest single change in this phase)

Phase 188's nav is a flat native-stack: Home → Vehicles → {VehicleDetail | NewVehicle}. Phase 189 introduces three top-level tabs, each its own native-stack so back-nav within a tab is independent.

```
RootNavigator (TabNavigator: bottom-tabs)
├── Home tab           (HomeStack: native-stack)
│   └── Home          ← scaffold / status / BLE / smoke
├── Garage tab         (GarageStack: native-stack)
│   ├── Vehicles      ← list (was top-level Vehicles)
│   ├── VehicleDetail ← was top-level
│   └── NewVehicle    ← was top-level
└── Sessions tab       (SessionsStack: native-stack)
    ├── Sessions      ← new SessionsListScreen
    ├── SessionDetail ← new
    └── NewSession    ← new
```

Type-level changes:
```ts
export type RootTabParamList = {
  HomeTab: undefined;
  GarageTab: undefined;
  SessionsTab: undefined;
};

export type HomeStackParamList = { Home: undefined };
export type GarageStackParamList = {
  Vehicles: undefined;
  VehicleDetail: {vehicleId: number};
  NewVehicle: undefined;
};
export type SessionsStackParamList = {
  Sessions: undefined;
  SessionDetail: {sessionId: number};
  NewSession: undefined;
};
```

`useNavigation<NativeStackNavigationProp<...>>()` callsites in existing screens (HomeScreen, VehicleDetailScreen, VehiclesScreen) must use the new per-tab stack param list — straightforward find-and-replace, TypeScript catches anything missed.

Tab bar UI: bottom-tabs default look + per-tab `tabBarLabel` ("Home" / "Garage" / "Sessions"). Tab icons deferred — Phase 188 didn't pull in an icon library and Phase 189 doesn't need one yet (label-only is readable + tappable). 48dp minimum tap area is met by bottom-tabs default.

Cross-tab nav (e.g., "from SessionDetail jump to the linked Vehicle") **not implemented in Phase 189** — adds nesting complexity and isn't a confirmed user need. If wanted later, `navigation.getParent()` + `navigate('GarageTab', {screen: 'VehicleDetail', params: {vehicleId}})`.

### Data flow

Same hook pattern as Phase 188:

```
useSessions()                       ← list, in SessionsListScreen
  ├── api.GET('/v1/sessions')       ← typed via openapi-fetch
  ├── returns {sessions, listResponse, isLoading, error, refetch}
  └── re-fetches on focus           ← React Navigation's useFocusEffect

useSession(sessionId)               ← single, in SessionDetailScreen
  ├── api.GET('/v1/sessions/{session_id}')
  ├── returns {session, isLoading, error, refetch}
  └── re-fetches on focus           ← in case mutations happened off-screen
```

**Mutations stay inline (no `useMutation` abstraction yet)** — Phase 188 made the same call and it held up. Pattern:

```ts
const onAppendSymptom = async () => {
  setSubmitting(true);
  try {
    const {data, error} = await api.POST('/v1/sessions/{session_id}/symptoms', {
      params: {path: {session_id: sessionId}},
      body: {symptom: input.trim()},
    });
    if (error) {
      Alert.alert('Add symptom failed', describeError(error));
      return;
    }
    setInput('');
    await refetch(); // refresh local view immediately
  } finally {
    setSubmitting(false);
  }
};
```

Each mutation refetches the parent `useSession` hook on success (cheap — single-row fetch) instead of doing optimistic local updates. Optimistic-update layer is deferred until per-mutation latency becomes user-visible.

### NewSessionScreen form

Two paths: **freehand** (type vehicle make/model/year) and **from-garage** (pick a vehicle the user owns; auto-populates make/model/year + sets `vehicle_id`).

```
[ Pick from garage ▼ ]   (loads useVehicles in-screen; falls through to freehand if none)
or
Make:  [             ]   ← required
Model: [             ]   ← required
Year:  [             ]   ← required, numeric

(optional)
Initial symptoms (chips, comma-separated input → array on submit)
Initial fault codes (chips, comma-separated input → array on submit)

[ Start session ]
```

Minimal client-side validation (backend Phase 178 Pydantic owns truth):
- `vehicle_make` / `vehicle_model`: required, 1-100 chars.
- `vehicle_year`: required, integer 1900-2100.
- Optional `symptoms` / `fault_codes`: pass through; backend constraints (each item 1-500 / 1-50 chars) surface as HVE 422 if violated.

If a vehicle is picked from garage, `vehicle_id` is sent; otherwise omitted. Backend stores both `vehicle_id` (FK) and the denormalized `vehicle_make/model/year` (so historical sessions are intact even if the bike is later deleted).

### SessionDetailScreen layout

Three sections, top to bottom:

**1. Vehicle** (read-only): "Honda CBR600 (2005)" + "Linked: garage #3" or "Linked: none" if `vehicle_id == null`.

**2. Diagnosis state** (mostly read-only, edit-toggle-able):
- **Symptoms** (list of strings, with bullet rendering). Append input + button at bottom of list.
- **Fault codes** (list of strings). Append input + button. Codes shown as raw strings ("P0171") — Phase 190 will add a tap-to-lookup that resolves via `GET /v1/kb/dtc/{code}` and links to the DTC screen.
- **Diagnosis text** (long string). Edit-mode = TextInput multiline.
- **Severity** (free-text in backend; UI offers SelectField with `low | medium | high | critical` options + "other" → free-text fallback). Backend `severity: Optional[str]` accepts anything; the SelectField is a UI nudge, not a constraint.
- **Confidence** (0.0–1.0 float). Edit-mode = numeric Field with parser `parseFloat` + range validation 0–1. Display: percentage ("78%").
- **Cost estimate** (≥ 0.0 float). Edit-mode = numeric Field. Display: dollar formatted ("$320.00").
- **Notes** (concatenated string built by repeated `/notes` POSTs — backend appends with newline separator). Display read-only; append-only via append-input pattern (cannot edit historic notes; matches backend semantics).

Edit-mode toggle: "Edit diagnosis" button enters edit-mode for the diagnosis-state section's PATCH-able fields (diagnosis text, severity, confidence, cost_estimate). "Save" → PATCH `/v1/sessions/{id}` with delta object. "Cancel" → discard local edits, refetch.

**Append paths use POST sub-routes, not PATCH** — backend keeps symptoms/fault_codes/notes as append-only journals for audit clarity. The UI mirrors this: each list has its own append input that's always visible (read-mode included), so the mechanic can capture observations while reviewing without an extra mode-switch.

**3. Lifecycle**: status badge (`open` blue / `in_progress` amber / `closed` gray) + lifecycle button:
- status `open` or `in_progress` → "Close session" (POST `/close`).
- status `closed` → "Reopen session" (POST `/reopen`).

Status transitions don't ask for confirmation — the inverse action is one tap away on the same screen.

### Error + quota surfacing

Phase 187 `describeError` already handles ProblemDetail + (Phase 188 commit 7) HTTPValidationError. Phase 189-specific surfaces:

- **402 SubscriptionRequiredError / monthly quota** on POST /v1/sessions: "Session quota reached: 50/50 (individual tier this month). Upgrade to shop tier (500/month) or wait until next month." Tier-aware copy mirrors Phase 188 vehicles 402.
- **404 on session detail** ("session id=X not found"): "Session not found. It may have been deleted." → navigate back to list.
- **422 HTTPValidationError** on PATCH (e.g., severity too long, confidence > 1.0): formatted via Phase 188 commit 7's `formatHTTPValidationError`.
- **404 on append/close/reopen**: generally only happens if the session was deleted between detail-fetch and mutation. Surface as "Session is no longer available" + navigate back.

### Pull-to-refresh + focus refetch

`SessionsListScreen` uses `<FlatList>` with `RefreshControl`. `useFocusEffect(refetch)` handles return-from-detail.
`SessionDetailScreen` has focus-refetch (cheap single-row).

### F1 cleanup (Commit 1)

Phase 188 logged a follow-up: battery_chemistry should be a `SelectField`, not free-text. Implementation:

```ts
// src/types/vehicleEnums.ts (add)
import type {components} from '../api-types';

type VehicleCreate = components['schemas']['VehicleCreateRequest'];
export type BatteryChemistryLiteral = NonNullable<VehicleCreate['battery_chemistry']>;

export const BATTERY_CHEMISTRY_OPTIONS: ReadonlyArray<BatteryChemistryLiteral> = [
  // pulled from generated api-types — exact set determined at build time
];

export const BATTERY_CHEMISTRY_LABELS: Record<BatteryChemistryLiteral, string> = {
  // friendly labels (e.g., 'lithium_ion' → 'Lithium-ion')
};

// labelFor() overload extended to include 'battery_chemistry' kind.
```

`NewVehicleScreen.tsx` + `VehicleDetailScreen.tsx`: replace battery_chemistry `Field` with `SelectField<BatteryChemistryLiteral>`. View mode in detail uses `labelFor(value, 'battery_chemistry')`.

This commit lands first because (a) it's the smallest scoped change, (b) it validates the F1 fix before adding any session-screen complexity, (c) it demonstrates that the vehicleEnums.ts pattern from Phase 188 commit 8 generalizes to any closed-set Pydantic Literal — useful pattern documentation for the rest of Track I.

## Key Concepts

- **`@react-navigation/bottom-tabs` v7** — pairs with `@react-navigation/native` 7.x. `createBottomTabNavigator()`. Per-tab native-stack via `<Tab.Screen>` whose `component` is the per-tab stack navigator.
- **Per-tab navigation isolation** — each tab has independent back-stack state. Switching tabs preserves where you were; switching back doesn't reset the inner stack.
- **`useFocusEffect`** — already used in Phase 188; behavior carries over inside per-tab stacks.
- **`navigation.replace`** vs `navigate` — for "create then go to detail" (NewSession submit), `replace` removes NewSession from the stack so back-button goes to list, not back to the form.
- **openapi-fetch path params** — `api.POST('/v1/sessions/{session_id}/symptoms', {params: {path: {session_id: id}}, body: {...}})`. The `params.path` object is type-checked against the URL template at compile time.
- **Discriminated `{data, error}` union from openapi-fetch** — same pattern as Phase 188; check `error` first, then `data` is non-null.
- **Pydantic `Literal` extraction** — `NonNullable<components['schemas']['SessionUpdateRequest']['status']>` gives the `'open' | 'in_progress' | 'closed'` union directly from the spec.
- **Append-only journals** — symptoms/fault_codes/notes endpoints return the *full* updated session, not just the appended item. The hook's `refetch` after a mutation is logically equivalent to using the response — but `refetch` keeps the data flow uniform and trivially correct under racing mutations.

## Verification Checklist

- [x] `npm test` → **162 / 162 green** (90 baseline + 72 new — well over the ~25-30 plan target). Suites: 12 passed, 12 total. Time: ~3.5–4.5s per run.
- [x] `npx tsc --noEmit` clean (exit 0) every commit.
- [x] Bottom-tab nav renders three tabs with labels Home / Garage / Sessions. **Verified at architect gate Step 19.**
- [x] Switching tabs preserves inner-stack position. **Verified at gate Step 19 — open SessionDetail in Sessions, switch to Garage (still on vehicle detail), switch back to Sessions (still on SessionDetail). No popping to root, no stack corruption.**
- [x] Sessions tab → SessionsListScreen → empty state ("No sessions yet · Start your first session" CTA). **Gate Step 3.**
- [x] CTA → NewSessionScreen → form rendered with required + optional sections. **Gate Step 4.**
- [x] Submit empty form → inline errors on make/model/year. **Gate Step 5.**
- [x] Submit valid freehand form → POST → navigate to SessionDetail of new session (back-button goes to list, not form). **Gate Step 7 — 201 Created, `navigation.replace` skipped the form on back.**
- [x] Pick from garage flow: dropdown shows owned vehicles, selecting one auto-fills make/model/year + sends `vehicle_id`. **Gate Step 6 — "Linked to garage #5" banner visible with Unlink escape hatch.**
- [x] SessionDetailScreen renders all sections (Vehicle / Symptoms / Fault codes / Diagnosis / Notes / Lifecycle). **Gate Step 9 — all six cards rendered, status "open".**
- [x] Append symptom → input clears → list updates with new item. **Gate Steps 10–11 — two distinct symptom appends verified, multi-item list growth confirmed.**
- [x] Append fault code → list updates. **Gate Step 11 — client-side lowercase→uppercase normalization on submit verified ("p0171" → "P0171").**
- [x] Append note → notes section reflects appended content. **Gate Step 12 — backend appended with auto-timestamp prefix.**
- [x] Edit diagnosis → change diagnosis text + severity + confidence + cost_estimate → Save → view mode reflects edits. **Gate Steps 13–16 — three saves verified across closed-pick (Medium → 'medium'), Other… (custom = 'investigating'), and closed-after-custom (High → 'high'). Round-trip render proof verified at Step 16: re-entering edit-mode pre-selected "Other…" with the custom Field pre-populated with "investigating", exactly as sketched.**
- [x] Close session → status badge flips to "closed" → button changes to "Reopen session". **Gate Step 17 — Closed timestamp populates from server response.**
- [x] Reopen session → status badge flips back to "open" → button changes back to "Close session". **Gate Step 18 — Closed timestamp vanishes (logged as Nit 2 for Phase 191 — pure-state vs audit-history is a product call, not a bug).**
- [x] Pull-to-refresh on SessionsListScreen works. **Verified during gate.**
- [x] Quota footer shows "individual tier · X/50 sessions this month" with correct numbers. **Gate Step 8 — "individual tier · 49/50 sessions remaining this month" using session-shaped keys (`total_this_month` / `monthly_quota_limit` / `monthly_quota_remaining`); the planning-time shape-difference flag is fully de-risked.**
- [-] Quota exceeded (51st session this month on individual tier) → 402. **Skipped (would burn through quota); copy + handler exists in `handleApiError`. Architect cleared without exercising it. Re-test if a real user hits the quota.**
- [x] Garage tab still works end-to-end (no Phase 188 regression). **Gate Step 2 — battery chemistry edit mode shows closed dropdown (5 options + null clear, no Other…), view mode renders prettified "Lithium-ion".**
- [x] Battery chemistry is now a dropdown in NewVehicleScreen + VehicleDetailScreen edit mode (F1 fix verified); view mode shows friendly label. **Gate Step 2.**
- [x] Home tab still shows Backend / Auth / Authed-smoke / BLE sections (no regression). **Gate Step 1.**
- [x] Phase 187 auth persistence still works (cold relaunch keeps API key). **Gate Step 1 + Step 20 — keychain restored auth across cold relaunch; full session state hydrated from backend (vehicle link, 2 symptoms, 1 fault code, full diagnosis with severity = High, 1 note, lifecycle, status pill).**
- [x] Phase 186 BLE scan still works. **Verified — no regressions.**

## Risks

- **Bottom-tab dep install + Android gradle.** `@react-navigation/bottom-tabs` is pure JS but pulls react-native-screens + react-native-safe-area-context (both already installed). Risk is near-zero, but Phase 186/187/188 all surfaced ble-plx-style gradle bugs from packages that *should* have installed cleanly. Mitigation: install in Commit 2, run `npm run android` in the same commit, patch-package if needed.
- **Nav refactor breaks existing tests.** Tests that import `RootStackParamList` or use `NativeStackNavigationProp<RootStackParamList, 'X'>` will fail to type-check after the refactor. Mitigation: Commit 2 includes the type-rename pass; tsc clean is a hard gate before continuing.
- **Quota schema-key drift from vehicles.** `total_this_month` not `total`; `monthly_quota_limit` not `quota_limit`. If a copy-paste from `useVehicles` lands without renaming, the quota footer renders blank. Mitigation: TypeScript guard via the generated types + a hook-level test that asserts the listResponse keys.
- **Severity field is free-text in backend, dropdown in UI.** Backend accepts arbitrary strings; UI nudges to `low|medium|high|critical`. If a server-stored severity is "moderate" (existing data), the SelectField shows blank/no-match. Mitigation: SelectField with "Other..." option that reveals a Field for free-text input; gracefully renders unknown values in view mode.
- **Confidence parsing.** `parseFloat('0.5')` works; `parseFloat('.5')` works; `parseFloat('1.0e0')` works. Edge case: empty string → NaN → submit caught as "must be a number 0-1". Mitigation: explicit `Number.isNaN` check + range guard before submit.
- **Cost estimate parsing — currency symbols.** User types "$300" → `parseFloat('$300')` = NaN. Strip non-numeric (except decimal point) before parse. Or just refuse with a hint.
- **Append button race.** User taps "Add symptom" twice fast → two POSTs, two appends. `submitting` state guard prevents this — same pattern as Phase 188 form submit.
- **Append-while-stale.** Detail screen shows session v1; user appends symptom; backend returns full session v2 with the new symptom; refetch returns v2; UI updates. But if a *different* user (multi-mechanic shop) is also editing (Phase 196 shop scope), the detail might race. Out of scope for Phase 189 — single-user flow only. If multi-mechanic mutations diverge, last-writer-wins (backend semantics, no transactional locking).
- **Close-then-reopen latency.** Two sequential POSTs feel slow if backend is on a different network. Mitigation: optimistic local status update on lifecycle button tap (revert on error). Decision: defer optimistic updates; current refetch-after-mutation is correct + understandable, and the smoke test will tell us if perceived latency is a real problem (likely <500ms on local backend).
- **Tab nav — initial route on launch.** Phase 188 launches on Home. Phase 189 keeps Home as the default initial tab so the auth/version status remains the first thing the user sees on cold launch. Switching default to Sessions tab once auth is stable could come later (Phase 199 push notifications might be the natural moment).
- **DTC list bare codes (no description) might surprise users.** Phase 189 ships raw "P0171" rendering. The Phase 190 ROADMAP entry now explicitly notes the integration cross-link, so this is a known tradeoff with a 1-phase follow-up.

## Not in scope (firm)

- DTC tap-to-lookup integration (`GET /v1/kb/dtc/{code}` or `/v1/kb/search?q=`). → **Phase 190.**
- Standalone DTC search screen (search by code or text, offline DB). → **Phase 190.**
- Voice input for symptoms / notes. → **Phase 195.**
- Freeze-frame data display. → **Phase 197.**
- Camera attach to session (photo/video evidence). → **Phase 191/194.**
- Offline session caching. → **Phase 198.**
- Optimistic UI updates on mutations. (Possible future polish; not until perceived latency becomes a real problem.)
- Multi-mechanic shop UI (assignment, per-tech filters on session list). → **Phase 193.**
- Tab icons (label-only is fine for Phase 189; icon library decision deferred).
- Cross-tab nav helpers (jump from SessionDetail to its Vehicle).
- AI-driven diagnosis suggestion endpoints (those exist on backend Phase 162.5 family but aren't part of `/v1/sessions/*`).

## Smoke test (Kerwyn-side, post-build, pre-v1.1)

Prereqs: backend running on emulator-host port 8080, dev API key present in Keychain (Phase 187 persistence), at least one vehicle in garage from Phase 188 (or use freehand path).

1. **Cold relaunch.** Auth ✓ Authenticated; Home tab is initial. Phase 187 + 186 no-regression check.
2. **Tap "Garage" tab.** Vehicles list still works. Open a vehicle. Verify battery chemistry shows as a friendly label in view mode (F1 fix), and as a dropdown in edit mode.
3. **Tap "Sessions" tab.** Empty state ("No sessions yet" + CTA).
4. **Tap "Start your first session" CTA.** NewSessionScreen opens.
5. **Submit empty form.** Inline errors on make/model/year.
6. **Pick a bike from garage dropdown.** Make/model/year auto-fill.
7. **Submit.** POST /v1/sessions, navigate to SessionDetail. Back-button goes to list (not form).
8. **List shows the new session** with status "open", quota footer "individual tier · 1/50 sessions this month".
9. **Tap row → SessionDetail.** All three sections render, status "open".
10. **Append symptom** "engine bog at 4500 RPM" → list updates.
11. **Append fault code** "P0171" → list updates with raw code.
12. **Append note** "Owner reports started after fuel filter swap" → notes section reflects.
13. **Tap "Edit diagnosis."** Diagnosis text / severity dropdown / confidence / cost_estimate become editable. Set diagnosis = "Lean fuel mixture, possible vacuum leak", severity = "medium", confidence = 0.65, cost = $180. Save. View mode reflects.
14. **Tap "Close session."** Status flips to "closed", button becomes "Reopen session".
15. **Tap "Reopen session."** Status flips back, button becomes "Close session".
16. **Quota stress (optional, only if curious — burns through quota):** Create 50 sessions on individual tier, attempt 51st → 402 with readable message.
17. **Switch tabs Home → Garage → Sessions** in any order. Inner-stack state preserved.
18. **Cold relaunch.** Sessions tab → list still shows what was there. Detail still openable.

If all pass → architect gate → v1.1 finalize.

## Commit plan (7 commits on `phase-189-diagnostic-session-ui` branch)

1. **F1 cleanup: battery_chemistry → SelectField.** Adds `BatteryChemistryLiteral` + `BATTERY_CHEMISTRY_OPTIONS` + `BATTERY_CHEMISTRY_LABELS` to `vehicleEnums.ts`; extends `labelFor()` overload; switches NewVehicleScreen + VehicleDetailScreen edit mode from Field to SelectField; view mode uses `labelFor`. ~4 new vehicleEnums tests. Total tests target ~94. **Verifies Phase 188 vehicleEnums pattern generalizes; ships F1 follow-up.**
2. **Bottom-tab nav refactor + screen stubs.** Install `@react-navigation/bottom-tabs`; refactor `RootNavigator.tsx` into `TabNavigator` + per-tab stacks; rename param-list types; type-rename pass at all `useNavigation<...>()` callsites; HomeScreen drops "My garage" Section; subtitle update; placeholder SessionsListScreen / NewSessionScreen / SessionDetailScreen with TODO bodies. `npm run android` smoke check. tsc clean. tests still 94 green.
3. **`useSessions` hook + SessionsListScreen list rendering.** Hook with 7 tests (loading/success/error/refetch-stability/listResponse-passthrough/empty-array/quota-keys-shape). FlatList + RefreshControl + empty state + quota footer + error banner + header "+ Start session" button. Tests target ~101.
4. **`useSession(id)` hook + SessionDetailScreen view mode.** Hook with ~5 tests. Read-only layout: Vehicle section + Diagnosis state section (lists + read-only display) + Lifecycle section (status badge + close/reopen buttons calling POST /close + /reopen with confirm-via-tap-only). Append paths NOT yet wired (placeholder buttons disabled + "TODO: append in commit 6"). Tests target ~106.
5. **NewSessionScreen form + create.** Both freehand + pick-from-garage paths. `useVehicles` reused for the picker. Submit POST → `replace` to SessionDetail. 422 surfacing via existing describeError. Tier-aware 402 quota copy. Tests: minimal (form is mostly UI, not validators) — target ~108.
6. **SessionDetail mutations: append symptom/fault-code/note + diagnosis edit + close/reopen wiring.** Inline append inputs that POST and refetch. Edit-mode toggle for diagnosis text / severity / confidence / cost_estimate via PATCH. SelectField for severity. Numeric Field with parsers for confidence (0-1 range) + cost_estimate (≥0). Lifecycle buttons fully wired. Tests: 2 new client.test regression-guards (Content-Type on POST /symptoms + POST /close — body-bearing + empty-body POST paths). Target ~110.
7. **README + project structure update + version bump 0.0.4.** README.md src/ tree updated; package.json version 0.0.3 → 0.0.4 (lockfile too); HomeScreen subtitle "v0.0.4 · Phase 189".

Each commit: `npm test` green + `npx tsc --noEmit` clean before push. Commit-2 also passes `npm run android` (gradle smoke). If Phase 188's pattern repeats (architect gate finds bugs), follow-up fix commits 8-10 land between commit 7 and rebase-merge.

## Architect gate

After commit 7, paste a build summary for Kerwyn-side smoke test (the 18-step list above). If round 1 finds issues, fix commits land before rebase-merge — Phase 188 8-commit pattern (5 build + 3 fix) is the precedent. Once green, rebase-merge `phase-189-diagnostic-session-ui` → `main`, delete branch local + remote.

**Outcome:** GATE PASSED on round 1. Zero fix commits required. 7-commit feature branch rebase-merged to `main` at finalize.

## Deviations from Plan

1. **Navigation file structure split into 5 files instead of 1 `TabNavigator.tsx`.** Plan called for one `src/navigation/TabNavigator.tsx`. Actual: `RootNavigator.tsx` (rewritten as the bottom-tab root) + `HomeStack.tsx` + `GarageStack.tsx` + `SessionsStack.tsx` + `types.ts`. Each per-tab stack is self-contained ~30 LoC; types live in one shared module. Cleaner ownership for the rest of Track I — Phase 190+ adds DTC screens to `SessionsStack.tsx` without touching the tab root.

2. **Symptoms input switched from comma-separated to newline-separated.** Plan v1.0 sketched chips/comma input; actual ships multiline with one symptom per line because natural-language symptoms commonly contain commas ("idle bog at 4500 rpm, started after fuel-filter swap" is one symptom, not two). Fault codes stay comma-separated since DTCs don't contain commas. Test `packSymptoms preserves commas inside symptoms (intentional)` documents the choice.

3. **`src/screens/sessionFormHelpers.ts` emerged as a separate module.** Plan didn't anticipate it. Test for `NewSessionScreen` initially imported helpers from the screen file directly, which transitively pulled `../api` (keychain / openapi-fetch graph) and broke the test loader. Fix: extract pack helpers to a sibling module that's testable in isolation. Same separation pattern as `Field.tsx`'s exported `validate*` / `parse*` helpers. Same pattern then re-applied for severity helpers in Commit 6 via `src/types/sessionEnums.ts`.

4. **`src/components/Field.tsx` converted to `forwardRef`.** Plan v1.0 didn't call this out; it emerged in Commit 6 to support the severity custom-input auto-focus per the sketch sign-off. Small, contained — backward-compatible for existing call sites. Worth flagging as a load-bearing change because every existing Field caller now sees the new ref-forwarding behavior even if they don't use it.

5. **Severity Other… UX clarification at smoke-flow review.** During the Commit 6 sketch posting, the Step 5 wording promised "trigger shows Other immediately on tap" which would have required Option 2 (a SelectField change). The sign-off resolution agreed with Option 1 — trigger reads "—" until first keystroke; the custom Field appears focused below. The sketch was updated; the implementation is honest about state. **Visually verified at Gate Step 14.**

6. **`src/api/index.ts` re-export of session types — dropped.** Plan said "re-export new session-shaped type aliases for screen convenience"; not needed in practice. Screens import `SessionResponse` etc. directly from `../types/api`. Less duplication; one source of truth.

7. **Test count overshot by ~3×.** Plan: ~25-30 new tests. Actual: 72 new (162 total = 90 baseline + 72). Driven by helper extraction yielding more pure-test surface (SelectField buildSelectRows + getTriggerDisplay; sessionEnums derive/pack/render trio; sessionFormHelpers pack functions) and explicit guards (the session-shape-vs-vehicles-shape guard test, the 2 transport-regression guards, the regression-guard for legacy off-enum battery_chemistry fall-through). Net positive — every test guards a real failure mode.

8. **Architect gate round 1 PASSED with zero fix commits.** Phase 188 set the precedent of "round 1 BLOCKED, 3 fix commits, round 2 GREEN." Phase 189 inverted it: round 1 GREEN, no fix commits. Two factors: (1) Phase 188 commits 6/7/8 fixed transport bugs that would have re-surfaced here; their guard tests covered the new POST surfaces in advance. (2) The pre-Commit-5 sketch sign-off for severity Other… caught the design ambiguity (Option 1 vs 2) before code; Phase 188 had no such gate.

## Results

| Metric                              | Value                                                                                |
|-------------------------------------|--------------------------------------------------------------------------------------|
| Branch                              | `phase-189-diagnostic-session-ui` (7 commits, rebase-merged to `main` at finalize)   |
| Tests passing                       | 162 / 162 (12 suites)                                                                |
| Tests added this phase              | 72 (90 baseline → 162)                                                               |
| Test runtime                        | ~3.5–4.5s                                                                            |
| Typecheck                           | clean (`tsc --noEmit`, exit 0 every commit)                                          |
| New runtime deps                    | 1 (`@react-navigation/bottom-tabs@7.15.10`)                                          |
| New native modules                  | 0 (bottom-tabs is pure JS; relies on already-installed `react-native-screens` + `react-native-safe-area-context`) |
| Gradle smoke (cold rebuild)         | clean (cd android && ./gradlew clean && cd .. && npm run android)                    |
| Architect gate                      | PASSED round 1 (zero fix commits)                                                    |
| Phase 186 BLE regressions           | none                                                                                 |
| Phase 187 auth regressions          | none                                                                                 |
| Phase 188 garage CRUD regressions   | none                                                                                 |
| New HTTP verb code paths            | 8 distinct POSTs + 1 PATCH + 2 GETs (against Phase 178 `/v1/sessions/*`)             |
| Transport-regression guards added   | 2 (`POST /v1/sessions/{id}/symptoms` body-bearing; `POST /v1/sessions/{id}/close` empty-body) |
| Bug 1 (customFetch Content-Type)    | held across 7 distinct POST/PATCH calls in the gate (both body-bearing and empty-body branches) |
| Mobile package version              | 0.0.3 → 0.0.4                                                                        |
| Mobile project `implementation.md`  | 0.0.5 → 0.0.6 (this finalize)                                                        |
| Backend project `implementation.md` | 0.13.4 → 0.13.5 (this finalize)                                                      |
| Backend `pyproject.toml`            | unchanged (Track I is mobile-side; backend package only bumps at backend-side gates) |
| Backend code change                 | zero (pure mobile phase)                                                             |
| Backend schema change               | none (still v38)                                                                     |

**Commits, in order on the feature branch:**

| # | Hash      | Title |
|--:|-----------|-------|
| 1 | `c6f5683` | battery_chemistry → SelectField (F1 fix) |
| 2 | `e572292` | bottom-tab nav refactor + session screen stubs |
| 3 | `e4c35a9` | useSessions hook + SessionsListScreen real impl |
| 4 | `dd9c0cf` | useSession(id) + SessionDetailScreen view + lifecycle |
| 5 | `77dfa8b` | NewSessionScreen form + POST /v1/sessions |
| 6 | `ba5a93c` | SessionDetail mutations + severity edit + guards |
| 7 | `cc8929b` | README + project structure update + version 0.0.4 |

**Key finding: when an architect-gate sketch sign-off lands BEFORE the implementation, round 1 holds.** Phase 188 had no pre-implementation review for vehicle CRUD and the gate caught 2 transport bugs + 1 cosmetic nit. Phase 189 paused before Commit 5 to sketch the severity Other… round-trip UX in writing — the State A/B/C model, the `deriveSeverityState` / `packSeverityForSubmit` / `renderSeverityForView` trio, the Option 1 vs Option 2 trigger-display question, the agreed customLabel: 'Other'. The user spotted a real inconsistency in Step 5 wording before any code existed; resolution was a 1-line update to the smoke-flow doc. Round 1 then passed clean. Two takeaways for the rest of Track I: (1) every commit that introduces a non-obvious state machine (severity round-trip, optimistic update layer, offline op-queue) gets a pre-implementation sketch posted for sign-off, not just an implementation.md plan section; (2) the architect-gate's round 1 GREEN result this phase is repeatable — pre-implementation sketches let the user catch design issues at sketch-cost (~30 min) instead of implementation-cost (~3-4 fix commits).

## Versioning landed at v1.1 finalize

- Mobile `package.json`: 0.0.3 → 0.0.4 ✅
- Mobile `implementation.md`: 0.0.5 → 0.0.6 ✅
- Backend `implementation.md`: 0.13.4 → 0.13.5 ✅
- Backend `pyproject.toml`: unchanged (Track I is mobile-side)

## Post-merge follow-ups (NOT blocking, logged in `moto-diag-mobile/docs/FOLLOWUPS.md`)

1. **F2 — Per-entry edit/delete on open sessions.** Smoke testing surfaced the demand: a typo committed to the symptoms list with no way to correct it. Defensible middle ground: open sessions → entries can be edited/deleted; closed sessions → immutable (or edits tracked as new entries with `[edited at X]`). Backend likely needs a `deleted_at` soft-delete column. Matches the dev team's "defer until a real flow demands it" pattern — the real flow has now demanded it. **Recommended target: Phase 191.**

2. **F3 — Lifecycle audit history.** Closed timestamp vanishes from the Lifecycle card on Reopen, reflecting pure current state rather than audit history. For forensic-style diagnostic logs, persisting close/reopen events as a timeline ("Closed 12:22 PM, Reopened 12:24 PM") is generally more useful than pure-state. **Product call, not a bug. Recommended target: Phase 191 follow-up.**
