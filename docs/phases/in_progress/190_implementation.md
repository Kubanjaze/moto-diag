# Phase 190 — DTC Code Lookup Screen (mobile)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-27

## Goal

Give the mechanic a real DTC reference inside the mobile app — a search-by-code-or-text surface plus a single-DTC detail view — over Phase 179's `/v1/kb/dtc/*` HTTP. Two user paths into the same DTCDetailScreen:

1. **General lookup from Home tab.** New "DTC lookup" Section on HomeScreen → DTCSearchScreen (search-as-you-type, debounced 300ms) → tap a result row → DTCDetailScreen.
2. **Contextual lookup from inside a session.** SessionDetail's fault-codes list rows become tappable → DTCDetailScreen with the code prefilled. Resolves the "raw code rendering" tradeoff Phase 189 explicitly carried as a known gap.

Phase 190 was originally "Interactive diagnostic session" + voice input; the swap at Phase 189 plan time put the canonical mechanic workflow first. Now Phase 190 picks up DTC lookup as a standalone screen + the cross-link integration into SessionDetail.

Voice input on the search input is **deferred to Phase 195** per ROADMAP.
Offline DTC database / persistent recent-searches / category browse are **deferred to Phase 198** (offline mode + local cache).
Filter chips by category / severity / make are **deferred** — backend supports them; UI ships search-on-text-only for the 80% mechanic flow ("type P0171, see if it shows up"). Fold filters into Phase 191 or as a standalone follow-up if smoke testing surfaces real demand.
"Add this DTC to current session" affordance is **NOT** in scope — would require global "current open session" state which ADR-003 deferred. The append flow stays inside SessionDetail's existing inline append input.

CLI — none (mobile has no CLI).

## Outputs

**New files (4):**

- `src/screens/DTCSearchScreen.tsx` — search input at top (autocapitalize=characters for direct DTC entry, keyboardType=default to allow text fallback), debounced 300ms, results FlatList rendering `DTCResponse` rows (code monospace + description + severity badge). Empty initial state with prompt copy. Loading / error / no-results states. Tap row → DTCDetail with the code as path param.
- `src/screens/DTCDetailScreen.tsx` — single-DTC view. Sections: **Header** (code monospace large + severity badge), **Description** (multiline body text), **Details** (category + make if make-specific), **Common causes** (bulleted list), **Fix summary** (multiline), **Source** (when reached via session-tap, tiny "from session #N" footer for context). Loading / 404 ("DTC code not found in database") / generic-error states. The screen is reachable from both `HomeStack` and `SessionsStack`; it doesn't care which path the user took.
- `src/hooks/useDTCSearch.ts` — `{results, total, query, setQuery, isLoading, error}` hook backed by `api.GET('/v1/kb/dtc', {params: {query: {q, limit}}})`. Debounce on `setQuery` (300ms via internal `setTimeout` + cleanup); empty query returns empty results without hitting the API. `total` exposed alongside `results` for "showing 50 of 127" copy if the page-cap kicks in.
- `src/hooks/useDTC.ts` — `{dtc, isLoading, error, refetch}` single-DTC hook for `api.GET('/v1/kb/dtc/{code}', {params: {path: {code}}})`. Mirrors `useVehicle`/`useSession` shape.

**Modified files (5):**

- `src/types/api.ts` — add `DTCResponse` (`components['schemas']['DTCResponse']`), `DTCListResponse` (`components['schemas']['DTCListResponse']`), `DTCCategoryResponse` (`components['schemas']['DTCCategoryResponse']`) aliases. The category alias ships even though Phase 190 doesn't render categories — small change, future-proofs the filter-chip work without a second `api.ts` edit later.
- `src/navigation/types.ts` — extend `HomeStackParamList` with `DTCSearch: undefined; DTCDetail: {code: string; sourceSessionId?: number}`. Extend `SessionsStackParamList` with `DTCDetail: {code: string; sourceSessionId?: number}` only (no `DTCSearch` — no real flow demands DTC search initiated from inside a session; user already has codes in front of them at session time).
- `src/navigation/HomeStack.tsx` — register `DTCSearch` + `DTCDetail` screens.
- `src/navigation/SessionsStack.tsx` — register `DTCDetail` (parallel registration for the tap-from-session path; `DTCSearch` deliberately omitted).
- `src/screens/HomeScreen.tsx` — add a new `Section title="DTC lookup"` between Backend and Auth (or wherever fits best — the auth-and-backend flow stays clean). Single Button "Look up a DTC" → `navigation.navigate('DTCSearch')`.
- `src/screens/SessionDetailScreen.tsx` — fault-code list rows become `<TouchableOpacity>` (currently plain `<View>`) → `navigation.navigate('DTCDetail', {code, sourceSessionId: session.id})`. Tiny visual affordance: chevron `›` on the right side of each fault-code row. Symptoms list stays a non-tappable read-only list (no DTC equivalent for symptoms).

**Imports (no module move, just reuse):**

- `src/types/sessionEnums.ts` keeps its current name. `SEVERITY_OPTIONS` + `SEVERITY_LABELS` + `renderSeverityForView` are reused by DTCDetailScreen + DTCSearchScreen for the severity badge rendering. Both backend `DTC.severity` and `Session.severity` are `Optional[str]`; both render with the same closed-set-prettify-or-verbatim helper. The slight file-name-vs-content drift (severity helpers in a session-named file) is tolerable; renaming is more disruptive than the inaccuracy. Documented at the top of `sessionEnums.ts` once Commit 1 lands.

**New tests (2 files, ~12-15 tests):**

- `__tests__/hooks/useDTC.test.ts` — 5 tests mirroring `useSession` pattern (path-param passthrough + loading→success + 404 ProblemDetail + refetch invocation + refetch referential stability).
- `__tests__/hooks/useDTCSearch.test.ts` — 7-9 tests covering the debounce contract: empty-query short-circuit (no API call), single setQuery → debounced API call after 300ms, rapid setQuery cancels prior debounce (only one API call lands), debounce-then-error surfaces via describeError, results pass-through, total pass-through, isLoading transitions during debounce-then-fetch.

**No new runtime deps.** No backend changes. No schema changes (backend still v38). No new ADR.

**Package version:** `0.0.4 → 0.0.5`.
**Project implementation.md version:** `0.0.6 → 0.0.7` on phase close.

## Logic

### Backend surfaces consumed

All from Phase 179, all gated by `require_api_key` only — **no `require_tier`** (KB is core product, not premium). No 402 quota path on either DTC endpoint.

| Method | Path                            | Purpose                              | Phase 190 caller |
|--------|---------------------------------|--------------------------------------|------------------|
| GET    | `/v1/kb/dtc?q=&limit=`          | Search DTCs by query string          | useDTCSearch     |
| GET    | `/v1/kb/dtc/{code}?make=`       | Single DTC fetch (404 if unknown)    | useDTC           |

`/v1/kb/dtc/categories` ships in the same router but Phase 190 doesn't render categories. Type alias added to `api.ts` for future use.

`/v1/kb/dtc` accepts `q` / `category` / `severity` / `make` query params; Phase 190 sends only `q` and `limit=50` (the backend's default page cap). Filter chips deferred.

`/v1/kb/dtc/{code}` accepts an optional `make` query param to disambiguate make-specific codes. Phase 190 doesn't pass `make` — the user is searching the generic catalog. Future: when reached via session-tap, pass `session.vehicle_make` to scope to the bike's make.

**Response shape** (`DTCResponse`):
```ts
{
  code: string
  description: string | null
  category: string | null
  severity: string | null   // free-text in backend; UI prettifies via SEVERITY_LABELS fall-through-to-raw
  make: string | null
  common_causes: string[]
  fix_summary: string | null
}
```

`DTCListResponse`: `{items: DTCResponse[], total: number}` — note `total` is the unfiltered match count; `items` is capped at the requested `limit`.

### Navigation placement

Per Q1 sign-off: option (a) — register the screens in both relevant stacks. To minimize boilerplate, only the screens each stack actually needs:

```
HomeStack
├── Home          ← unchanged
├── DTCSearch     ← new (general lookup)
└── DTCDetail     ← new (reached via DTCSearch row tap)

GarageStack       ← unchanged

SessionsStack
├── Sessions      ← unchanged (Phase 189)
├── SessionDetail ← unchanged (Phase 189)
├── NewSession    ← unchanged (Phase 189)
└── DTCDetail     ← new (reached via SessionDetail fault-code tap)
```

`DTCSearch` is **only** in HomeStack. From the user's mental model, "search the DTC catalog" is a launcher action (Home tab is the launcher), not a session-internal action. Inside a session the user already has codes in front of them; the cross-link path is fault-code → DTCDetail directly.

The `DTCDetail` route is registered identically in both stacks: `DTCDetail: {code: string; sourceSessionId?: number}`. The optional `sourceSessionId` is purely a render hint — when present, DTCDetailScreen shows a tiny "from session #N" footer so the user knows back-button takes them to the session, not to the search list. The screen itself doesn't care which stack it's in.

Cross-tab nav stays out of scope. Tapping a fault-code from SessionsStack pushes within SessionsStack (back goes to SessionDetail). Tapping a search result from HomeStack pushes within HomeStack (back goes to DTCSearch). If the user wants the same code surface from both contexts, they'll re-navigate. This avoids `navigation.getParent()` complexity and matches Phase 189's "defer cross-tab nav until a real flow demands it" decision.

### Data flow

```
useDTCSearch()              ← SearchScreen
  ├── debounced setQuery (300ms)
  ├── GET /v1/kb/dtc?q={query}&limit=50
  ├── returns {results, total, query, setQuery, isLoading, error}
  └── empty query → empty results, no API call

useDTC(code)                ← DetailScreen
  ├── GET /v1/kb/dtc/{code}
  ├── returns {dtc, isLoading, error, refetch}
  └── re-fetch on focus (in case of legacy off-route navigation)
```

### Debounce mechanics (useDTCSearch)

```ts
const [query, setQueryRaw] = useState('');
const [debouncedQuery, setDebouncedQuery] = useState('');
const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

const setQuery = useCallback((next: string) => {
  setQueryRaw(next);
  if (timerRef.current) clearTimeout(timerRef.current);
  timerRef.current = setTimeout(() => {
    setDebouncedQuery(next.trim());
  }, 300);
}, []);

useEffect(() => () => {
  if (timerRef.current) clearTimeout(timerRef.current);
}, []);

useEffect(() => {
  if (debouncedQuery.length === 0) {
    setResults([]);
    setTotal(0);
    return;
  }
  // fetch via api.GET — alive guard pattern from useVehicles / useSessions
  // ...
}, [debouncedQuery]);
```

Two pieces of state: `query` (immediate, drives the input element) and `debouncedQuery` (lagged, drives the API call). User types → `query` updates immediately → 300ms timer → `debouncedQuery` updates → effect fires → API call.

Cancellation: every keystroke clears the prior timer. So if the user types "P0171" character-by-character at typical speed, only the final "P0171" generates an API call.

Empty-query short-circuit: `debouncedQuery.length === 0` returns empty results without hitting the API. This handles the initial-render case + the user-clears-the-input case.

Test plan validates the contract: rapid `setQuery('P')` → `setQuery('P0')` → `setQuery('P01')` → ... within the 300ms window produces exactly one API call after the window settles.

### DTCSearchScreen states

| State           | Render                                                                          |
|-----------------|---------------------------------------------------------------------------------|
| Empty query     | Prompt copy: "Type a DTC code (e.g. P0171) or describe a symptom"               |
| Debouncing      | Input shows current text; results card shows muted "…" or stays prior          |
| Loading         | Spinner inside the results card                                                 |
| Success (≥1)    | FlatList of DTC rows (code · description · severity badge)                      |
| Success (0)     | "No DTCs match" + suggestion to broaden the query                               |
| Error           | Banner + Retry button (re-runs the current debouncedQuery)                      |

Header has a "Cancel" / back button (defaults from native-stack).

### DTCDetailScreen states

| State           | Render                                                                         |
|-----------------|--------------------------------------------------------------------------------|
| Loading         | Centered spinner                                                                |
| Error 404       | "DTC code 'XYZ' not found" + "Check the code or try the search" + Back button |
| Error generic   | "Couldn't load DTC" + Retry / Back                                              |
| Success         | Header card + Description + Details + Common causes + Fix summary + Source    |

When `route.params.sourceSessionId` is present, footer shows: "Opened from session #{sourceSessionId}". When absent (general lookup from Home), footer is omitted.

### SessionDetailScreen integration (the cross-link)

Phase 189 ships fault-code rows as plain `<View>` with monospace text. Phase 190 swaps to `<TouchableOpacity>`:

```tsx
<TouchableOpacity
  style={styles.faultCodeRow}
  onPress={() => navigation.navigate('DTCDetail', {
    code: code,
    sourceSessionId: session.id,
  })}
  accessibilityRole="button"
  testID={`session-fault-code-${idx}`}>
  <Text style={styles.listItemTextMono}>{code}</Text>
  <Text style={styles.faultCodeChevron}>›</Text>
</TouchableOpacity>
```

The chevron is the visual affordance — without it, mechanics won't know the row is tappable. Symptoms rows stay non-tappable (no DTC analog for natural-language symptoms).

### HomeScreen entry point

A new `Section title="DTC lookup"` lands between Backend and Auth. Helper text: "Look up DTC codes in the catalog. Search by code or description." Single Button "Look up a DTC" → `navigation.navigate('DTCSearch')`.

This is the same shape as Phase 188's pre-tab-nav "My garage" Section that got removed when Garage became its own tab. We're not adding a 4th tab for DTC because (a) it's contextual not primary, (b) tab clutter, (c) the cross-link from SessionDetail already covers the most-used path. Home becomes a launcher with one extra surface; that's the right place for it.

### Severity rendering — reuse `sessionEnums.ts`

Both backend `DTC.severity` and `Session.severity` are `Optional[str]`. DTCDetailScreen + DTCSearchScreen import `SEVERITY_LABELS` + `SEVERITY_OPTIONS` + `renderSeverityForView` from `src/types/sessionEnums.ts` and use the same closed-set-prettify-or-verbatim helper. The file name `sessionEnums.ts` is a slight inaccuracy (it now also serves DTC severity) but we accept the inaccuracy over the churn of renaming + updating every existing import. A 2-line comment at the top of the file documents the cross-use.

## Key Concepts

- **Debounced search input.** Two pieces of state (immediate `query` + lagged `debouncedQuery`); a `setTimeout` ref is reset on every keystroke so the timer always represents the latest input. Cleanup-on-unmount via `useEffect` return.
- **Search-as-you-type alive guard.** Same `alive` ref pattern from `useVehicles` / `useSessions` — but the in-flight request can race with the next debounced query. We use `alive.current` to drop stale responses after unmount, and an additional `requestId` counter to drop responses from prior queries that race the current one.
- **`openapi-fetch` query params.** `api.GET('/v1/kb/dtc', {params: {query: {q, limit}}})` — `params.query` for query-string args, distinct from `params.path` for path params. Both are type-checked against the spec.
- **`navigation.navigate` with cross-stack same-route name.** `'DTCDetail'` is registered identically in HomeStack and SessionsStack. Each stack has its own param-list type, but TypeScript narrows correctly because `useNavigation<NativeStackNavigationProp<HomeStackParamList | SessionsStackParamList>>()` isn't used — every screen is in exactly one stack and uses that stack's param list.
- **`accessibilityRole="button"` on tappable rows.** Already established in Phase 188/189. Confirms the row is interactive to screen readers + click-handler stack.
- **Empty-query short-circuit.** `debouncedQuery.length === 0 → empty results without API call`. Prevents the initial-render "search for empty string" wasted call.

## Verification Checklist

- [ ] `npm test` → all prior 162 + ~12-15 new tests passing (target ~175 total).
- [ ] `npx tsc --noEmit` clean every commit.
- [ ] HomeScreen has a "DTC lookup" Section between Backend and Auth.
- [ ] Tap "Look up a DTC" → DTCSearchScreen opens, input focused (or near-focused — keyboard up).
- [ ] Empty query state: prompt copy visible.
- [ ] Type "P0" → 300ms debounce → results render.
- [ ] Rapid typing "P0171" produces exactly one API call once typing settles.
- [ ] Tap a result row → DTCDetailScreen opens with code rendered + description / common causes / fix summary populated.
- [ ] DTCDetailScreen back-button returns to DTCSearchScreen with prior search state preserved.
- [ ] Type a known-bad code → search results show "No DTCs match" empty state.
- [ ] Type a known-bad code, navigate to DTCDetail (e.g., via deep-route construction in dev) → 404 state with code-specific message.
- [ ] Open a session from Sessions tab → SessionDetail with at least one fault code → tap a fault-code row → DTCDetailScreen opens with that code prefilled, "Opened from session #N" footer visible.
- [ ] DTCDetail back-button from session-tap path returns to SessionDetail (not to DTCSearch — different stack).
- [ ] Severity badge on DTCDetail renders prettified for closed values ("High" not "high"), verbatim for off-enum values.
- [ ] No regression: HomeScreen existing 4 sections (Backend / Auth / Authed-smoke / BLE) still render correctly.
- [ ] No regression: Garage tab end-to-end (Phase 188).
- [ ] No regression: Sessions tab end-to-end (Phase 189) — append symptom / append fault-code / diagnosis edit / lifecycle close-reopen all work.
- [ ] Severity helper file note: `sessionEnums.ts` top comment acknowledges DTC reuse.
- [ ] Phase 187 auth: cold relaunch keeps API key + DTC search works on first input.
- [ ] Phase 186 BLE scan: still works.

## Risks

- **Search-as-you-type races.** The `alive` guard alone isn't sufficient — between two debounced queries, an old request can complete after a new one was issued, overwriting fresh results with stale ones. Mitigation: `requestIdRef.current` counter incremented on every fetch start; only commit results if the response's requestId matches the current ref. Same pattern as TanStack Query's "query key" race protection. **Lock this in the test plan with a deterministic mock that resolves out-of-order.**
- **Initial empty-query render.** The user opens DTCSearch and the input is blank. Don't render a flash of "No DTCs match" — that'd only fire if the empty query hit the API and returned nothing. The empty-query short-circuit prevents this; the initial state shows the prompt copy.
- **404 messaging on DTCDetail.** Backend returns RFC 7807 ProblemDetail for 404 ("DTC code 'XYZ' not found"). The mobile screen renders the detail string verbatim; the `describeError` helper from Phase 187 covers this. Risk: if backend wording changes, mobile copy follows. Acceptable — sticking with backend's wording for now.
- **Cross-stack same-route-name TypeScript headaches.** `'DTCDetail'` is registered in both HomeStack and SessionsStack with identical param lists. TypeScript should infer correctly because each `useNavigation<...>()` callsite uses one specific stack's param list. If that goes sideways, a quick fix is to type-alias the shared shape: `type DTCDetailParams = {code: string; sourceSessionId?: number}` in `navigation/types.ts` and reference it from both list types.
- **Severity label drift.** If backend Phase 191+ changes DTC severity to a closed enum that doesn't match `low/medium/high/critical`, `renderSeverityForView` falls through to the raw value — visible to the user but not broken. Documented in `sessionEnums.ts` as a graceful fall-through.
- **Cross-stack navigation expectation.** Some users may expect tapping a fault-code in SessionDetail to push them to "DTC tab" (option (b) we rejected). Mitigation: there's no DTC tab; the DTCDetail screen visually looks the same regardless of stack. Footer text "Opened from session #N" gives the user the context. If feedback says "I want to search from inside a session", Phase 191+ adds DTCSearch to SessionsStack as an additive change.
- **Debounce timing.** 300ms is a standard. Too short (100ms) → API hammered + perceived jankiness. Too long (500ms+) → laggy feel. 300ms tested feels right; if smoke testing surfaces "feels slow," adjustable to 200ms via a single constant.
- **No-results state vs error state.** Backend returns 200 with `items: []` for a query that matches nothing — that's not an error. Mitigation: distinguish in the screen — `error` state on `apiError`, "no results" state on `data.items.length === 0`.

## Not in scope (firm)

- Voice input on the search field. → **Phase 195.**
- Offline DTC database / local-first fall-through. → **Phase 198.**
- Recent-searches persistence. → **Phase 198** (needs storage layer).
- Filter chips (category / severity / make). → **Phase 191 or follow-up.**
- "Add this DTC to current session" affordance. → **Out** (would need global "current session" state; ADR-003 deferred).
- Symptoms search (`/v1/kb/symptoms`). → **Out** (Phase 192+ if a use case emerges).
- Known-issues lookup (`/v1/kb/issues`). → **Out** (Phase 192+).
- Unified search (`/v1/kb/search`). → **Out** (Phase 192+).
- Make-scoped DTC lookup (passing `?make=` from session-tap). → **Phase 191** (small scope, but adds branch to `useDTC`).
- DTC-to-known-issue cross-link (`DTCResponse.dtc_codes` → known issue list). → **Phase 192+**.

## Smoke test (Kerwyn-side, post-build, pre-v1.1)

Prereqs: backend running with seeded DTC catalog (`.venv/Scripts/python.exe -m motodiag code load-seed` if not already loaded), API key in Keychain, at least one open session with at least one fault code (carry over from Phase 189 smoke, or create a new session).

1. **Cold relaunch.** Auth ✓ Authenticated; Home tab is initial. Phase 186 + 187 + 188 + 189 no-regression check.
2. **HomeScreen "DTC lookup" Section visible** between Backend and Auth.
3. **Tap "Look up a DTC".** DTCSearchScreen opens with empty input + prompt copy.
4. **Type "P0"** slowly (one char at a time, ~500ms apart). Each character triggers a 300ms debounced search → results render after each.
5. **Type "P0171"** rapidly (under 300ms total). Results render once with the final query.
6. **Backend logs (separate terminal)** show exactly one `GET /v1/kb/dtc?q=P0171&limit=50` from step 5 (not 5 calls).
7. **Tap a result row** (e.g., "P0171 — System Too Lean (Bank 1)"). DTCDetailScreen opens with code in monospace + description + severity badge + common causes list + fix summary.
8. **Back-button.** Returns to DTCSearchScreen with the prior search state intact (results still on screen, query still in input).
9. **Type a known-bad query** ("ZZZZZZ"). After debounce, "No DTCs match" empty state visible.
10. **Switch to Sessions tab.** Open a session with at least one fault code.
11. **Tap a fault-code row.** Visual chevron `›` confirms tappability. Navigation pushes DTCDetailScreen within SessionsStack.
12. **DTCDetailScreen footer** reads "Opened from session #N". Code data renders correctly.
13. **Back-button.** Returns to SessionDetailScreen (NOT to DTCSearchScreen — that's HomeStack).
14. **Switch tabs Home → Garage → Sessions.** Inner-stack state preserved per Phase 189 spec; DTCDetail still on top of SessionsStack.
15. **Tap a session fault-code that's a known-bad code** (e.g., manually create a session with code "BOGUS123" via the Phase 189 append flow first). Tap the code → DTCDetail 404 state ("DTC code 'BOGUS123' not found in database") with Back / Retry options.
16. **Append a fault code from inside the session via the existing Phase 189 flow** ("P0420"). Tap the new row → DTCDetail loads correctly.
17. **Cold relaunch.** DTCSearchScreen state is NOT preserved (no offline cache yet — Phase 198 territory). Other state intact.

If all pass → architect gate → v1.1 finalize.

## Commit plan (5 commits on `phase-190-dtc-code-lookup-screen` branch)

1. **DTC types + `useDTC` hook + DTCDetailScreen view-only + register on both stacks.** `src/types/api.ts` add 3 alias types; `src/hooks/useDTC.ts` 5-test mirror of `useSession`; `src/screens/DTCDetailScreen.tsx` with all states (loading / 404 / generic-error / success); navigation/types.ts extends both stack param lists; HomeStack + SessionsStack register `DTCDetail`. Severity badge reuses `sessionEnums.ts` helpers (top-comment update). Tests target ~167.
2. **SessionDetailScreen fault-code tap → DTCDetail integration.** Single screen edit: fault-code rows from `<View>` to `<TouchableOpacity>` with chevron + navigation.navigate. testID per row. No new tests (existing useSession tests cover the data; tap-handler is render-time wiring). Tests stay 167.
3. **`useDTCSearch` hook (debounced 300ms) + DTCSearchScreen list + empty + no-results + error states.** Hook with 7-9 tests including the rapid-type-collapses-to-one-call invariant + empty-query short-circuit + race-condition cancellation. Screen renders the 6 states. Register `DTCSearch` on HomeStack only. Tests target ~175.
4. **HomeScreen "DTC lookup" Section entry point.** Add the Section + Button → `navigation.navigate('DTCSearch')`. testID. No new tests (render-time wiring). Tests stay ~175.
5. **README + project structure + version bump 0.0.4 → 0.0.5.** README.md status / project-structure tree / testing section refreshed for the new screens + hooks; package.json + lockfile bump.

Each commit: `npm test` green + `npx tsc --noEmit` clean before push. Phase 188 8-commit pattern (5 build + 3 fix) is the precedent if architect gate finds bugs; Phase 189 1-round 7-commit clean is the better-case precedent. Pre-implementation sketch sign-off saved Phase 189 from fix-commit churn — Phase 190 has fewer state-machine surfaces than Phase 189 (no severity Other… equivalent), so a short pre-Commit-3 design check on the debounce-race contract should suffice if anything ambiguous emerges.

## Architect gate

After Commit 5, paste a build summary for Kerwyn-side smoke test (the 17-step list above). Once green, rebase-merge `phase-190-dtc-code-lookup-screen` → `main`, delete branch local + remote, finalize v1.1 docs, bump backend `implementation.md` 0.13.5 → 0.13.6, mark ROADMAP ✅, push.

## Versioning targets at v1.1 finalize

- Mobile `package.json`: 0.0.4 → 0.0.5.
- Mobile `implementation.md`: 0.0.6 → 0.0.7.
- Backend `implementation.md`: 0.13.5 → 0.13.6 (Phase History row added; Track I phase 6 of 20).
- Backend `pyproject.toml`: unchanged (Track I is mobile-side; backend package only bumps at backend-side gates).
