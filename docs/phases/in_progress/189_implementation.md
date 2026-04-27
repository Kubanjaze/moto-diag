# Phase 189 — Diagnostic Session UI (mobile)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-27

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

**New files (8):**
- `src/screens/SessionsListScreen.tsx` — list view. Pull-to-refresh. Empty state with "Start your first session" CTA. Tap row → SessionDetail. Footer shows tier + monthly quota ("individual tier · 47/50 sessions remaining this month").
- `src/screens/SessionDetailScreen.tsx` — single session view. Three sub-sections: **Vehicle** (make / model / year, optionally linked vehicle id), **Diagnosis state** (symptoms list + append + DTC list + append + diagnosis text + severity + confidence + cost estimate + edit-mode), **Lifecycle** (status badge + Close / Reopen buttons, gated by current status). Read-mode by default; tap "Edit diagnosis" to enter mutation mode.
- `src/screens/NewSessionScreen.tsx` — form. Required: vehicle make/model/year (or pick-from-garage). Optional initial symptoms[] + fault_codes[] (chip-style add-one inputs). Submit → POST → navigate to SessionDetail of the new session.
- `src/hooks/useSessions.ts` — `{sessions, listResponse, isLoading, error, refetch}` wrapping `api.GET('/v1/sessions')`. Refetches on focus. `listResponse` carries `{total_this_month, tier, monthly_quota_limit, monthly_quota_remaining}` for the footer.
- `src/hooks/useSession.ts` — `{session, isLoading, error, refetch}` single-session hook for `api.GET('/v1/sessions/{session_id}')`.
- `src/navigation/TabNavigator.tsx` — bottom-tab navigator (`@react-navigation/bottom-tabs`). Three tabs: Home / Garage (= Vehicles stack) / Sessions. Each tab is its own native-stack so back-navigation within a tab doesn't pop you to a different tab.
- `src/screens/SessionsListScreen.tsx` (and detail screen) — see above.

**Modified files (8):**
- `src/navigation/RootNavigator.tsx` — refactor: root becomes the `TabNavigator`; the existing flat stack is broken into per-tab stacks (`HomeStack`, `GarageStack`, `SessionsStack`). `RootStackParamList` is replaced by `RootTabParamList` + per-tab param-lists. Existing screens slot into the right per-tab stack with no behavior change.
- `src/screens/HomeScreen.tsx` — remove the "My garage" Section (its own tab now); keep Backend / Auth / Authed-smoke / BLE sections. Update subtitle "v0.0.4 · Phase 189".
- `src/screens/NewVehicleScreen.tsx` — battery_chemistry: `Field` → `SelectField<BatteryChemistryLiteral>` (F1 follow-up resolution).
- `src/screens/VehicleDetailScreen.tsx` — battery_chemistry: edit mode swaps `Field` for `SelectField`; view mode uses `labelFor()` for friendly label.
- `src/types/api.ts` — add `SessionResponse`, `SessionListResponse`, `SessionCreateRequest`, `SessionUpdateRequest`, `SymptomRequest`, `FaultCodeRequest`, `NoteRequest`, `SessionStatusLiteral` aliases. Add `BatteryChemistryLiteral` extracted via `NonNullable<>`.
- `src/types/vehicleEnums.ts` — add `BATTERY_CHEMISTRY_OPTIONS`, `BATTERY_CHEMISTRY_LABELS`. Extend `labelFor()` overload to accept `'battery_chemistry'` kind.
- `src/api/index.ts` — re-export new session-shaped type aliases for screen convenience.
- `package.json` + `package-lock.json` — add `@react-navigation/bottom-tabs` dep; bump `version` 0.0.3 → 0.0.4.
- `README.md` — update src/ tree for new screens / hooks / navigator, add Phase 189 entry to project structure.

**New tests (4 files, ~25-30 tests):**
- `__tests__/hooks/useSessions.test.ts` — mocks `api.GET('/v1/sessions')`; verifies loading/success/error states, listResponse passthrough, refetch referential stability. ~7 tests.
- `__tests__/hooks/useSession.test.ts` — same pattern for single-session fetch. ~5 tests.
- `__tests__/types/sessionEnums.test.ts` — `SESSION_STATUS_LABELS` / `SEVERITY_LABELS` rendering helpers (if extracted). ~4 tests.
- `__tests__/types/vehicleEnums.test.ts` (extend existing) — battery_chemistry options + labels + labelFor coverage. ~4 tests.
- `__tests__/api/client.test.ts` (extend existing) — add 2 new regression-guard tests asserting Content-Type preserved on `POST /v1/sessions/{id}/symptoms` + `POST /v1/sessions/{id}/close` (covers both body-bearing and empty-body POST paths added in Phase 189). ~2 tests.

Phase 188 contracted regression-guard pattern: every new code path that issues a body-bearing or empty-body POST/PATCH gets a transport guard.

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

- [ ] `npm test` → all prior 90 + ~25 new tests passing (target ~115 total).
- [ ] `npx tsc --noEmit` clean.
- [ ] Bottom-tab nav renders three tabs with labels Home / Garage / Sessions.
- [ ] Switching tabs preserves inner-stack position (e.g., open VehicleDetail in Garage tab, switch to Sessions, switch back → still on VehicleDetail).
- [ ] Sessions tab → SessionsListScreen → empty state ("No sessions yet · Start your first session" CTA).
- [ ] CTA → NewSessionScreen → form rendered with required + optional sections.
- [ ] Submit empty form → inline errors on make/model/year.
- [ ] Submit valid freehand form → POST → navigate to SessionDetail of new session (back-button goes to list, not form).
- [ ] Pick from garage flow: dropdown shows owned vehicles, selecting one auto-fills make/model/year + sends `vehicle_id`.
- [ ] SessionDetailScreen renders all sections (Vehicle / Diagnosis state / Lifecycle).
- [ ] Append symptom → input clears → list updates with new item.
- [ ] Append fault code → list updates.
- [ ] Append note → notes section reflects appended content.
- [ ] Edit diagnosis → change diagnosis text + severity + confidence + cost_estimate → Save → view mode reflects edits.
- [ ] Close session → status badge flips to "closed" → button changes to "Reopen session".
- [ ] Reopen session → status badge flips back to "open" → button changes back to "Close session".
- [ ] Pull-to-refresh on SessionsListScreen works.
- [ ] Quota footer shows "individual tier · X/50 sessions this month" with correct numbers.
- [ ] Quota exceeded (51st session this month on individual tier) → POST /v1/sessions returns 402 → readable message ("Session quota reached: 50/50 (individual tier this month) · upgrade or wait").
- [ ] Garage tab still works end-to-end (no Phase 188 regression).
- [ ] Battery chemistry is now a dropdown in NewVehicleScreen + VehicleDetailScreen edit mode (F1 fix verified); view mode shows friendly label.
- [ ] Home tab still shows Backend / Auth / Authed-smoke / BLE sections (no regression).
- [ ] Phase 187 auth persistence still works (cold relaunch keeps API key).
- [ ] Phase 186 BLE scan still works.

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

## Versioning targets at v1.1 finalize

- Mobile `package.json`: 0.0.3 → 0.0.4.
- Mobile `implementation.md`: 0.0.5 → 0.0.6.
- Backend `implementation.md`: 0.13.4 → 0.13.5 (Phase History row added; track phase progress).
- Backend `pyproject.toml`: unchanged (Track I is mobile-side; backend package only bumps at next backend gate / release milestone).
