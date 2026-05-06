# Phase 193 — Shop Dashboard (mobile, consumer-side)

**Version:** 1.0 (plan) | **Tier:** Standard | **Date:** 2026-05-06

## Goal

Ship the **shop-tier mechanic's primary mobile surface**: a 4th bottom-tab `ShopTab` that surfaces the existing Phase 161/162/164/180 backend substrate (work orders + issues + triage queue + RBAC) as native UI. Mechanics get a viewable, sortable, lightly-mutable list of work orders with detail screens for state transitions + reassignment.

Consumer-side phase. **Backend untouched** (Phase 180 already shipped 25 endpoints under `/v1/shops/{shop_id}/*`). Mobile-side is greenfield: no shop screens exist, no shop hooks exist, only typed routes via openapi-typescript codegen.

CLI: no new CLI surface (mobile-only feature).

Outputs:
- Mobile hooks: `useShops` (membership list for picker), `useWorkOrders(shopId)`, `useWorkOrder(woId)`, `useShopMembers(shopId)`. All return `{data, error: ShopAccessError | undefined, isLoading, refetch}` per Section J's typed-error-from-hook-boundary commitment.
- Mobile typed-error: `src/hooks/shopAccessErrors.ts` — `ShopAccessError` discriminated union with three kinds (`unauthorized` 401 / `subscription_required` 402 / `not_member` 403). Mirrors `pdfDownloadErrors.ts` + `dtcErrors.ts` patterns.
- Mobile screens: `ShopTabRoot` (modal shop-picker on first navigate when multi-shop) → `WorkOrderListScreen` (sort toggle Newest/Priority/Triage) → `WorkOrderDetailScreen` (data-driven section composition + state-transition + reassign).
- Mobile data-driven section composition for WO detail: `WorkOrderSection` discriminated union (today: `vehicle | customer | issues | notes | lifecycle`; future-ready for Phase 194 `photos`, Phase 195 `voice_transcripts`, Phase 196 `obd_snapshots`).
- Mobile nav: `ShopTab` added to `RootTabParamList`; tier-reactive visibility (free-tier user upgrades mid-session → tab appears without app restart).
- Mobile copy: 5-kind error-copy register for `ShopAccessError` + tier-aware tab visibility copy.

## Architectural commitment — uniform display, source-agnostic UI

**Phase 193 displays fault codes, symptoms, and (eventually) photos uniformly regardless of input source.** Each future phase (194 camera/photo, 195 voice → structured symptoms, 196 Bluetooth OBD → fault codes/sensor snapshots) gets to argue whether source-tracking is load-bearing; if yes, that phase adds source via migration + extends rendering. Substrate-anticipates-feature means **leaving the data shape open to provenance, not pre-implementing provenance UI**.

The load-bearing piece: **WO detail's section list is data-driven**. `WorkOrderSection` is a discriminated union with explicit variants. Today's variants cover the existing data (vehicle / customer / issues / notes / lifecycle). Future phases ADD variants without rewriting the screen. Same architectural shape as Phase 192's `ReportSection` discriminated union — proven pattern, deliberate reuse.

Concrete forward-looks:
- **Phase 194 (photos)**: when photos attach to WOs/issues, a new `WorkOrderSection` variant `photos` slots in alongside existing variants. Backend will need an attachments table or column; that's 194's concern, not 193's. Phase 193's discriminated-union shape means 194's UI work is purely additive.
- **Phase 195 (voice)**: voice extraction produces structured symptoms attached to sessions/intakes. Phase 193 displays linked symptoms (via `linked_symptom_id` in `issues`) uniformly; whether they came from voice transcription or mechanic typing is invisible. If 195 decides source-tracking matters, it adds a `source` column + 193's display extends.
- **Phase 196 (OBD)**: OBD scans produce DTCs that flow into `linked_dtc_code`. Phase 193 displays DTCs uniformly. If 196 wants "(OBD-scanned)" badges, that's a 196 follow-up on top of an additive `source` column.

**Cross-cutting forward-look discipline**: Phase 193 dashboard treats input data as uniform. No source-aware UI. No "manual vs auto" distinctions. Substrate anticipates by leaving shape open, NOT by pre-implementing provenance.

## Logic

### F33-style existing-code overlap audit (per CLAUDE.md Step 0)

Audit ran 2026-05-06 BEFORE plan v1.0 was written. Greps across `src/motodiag/` (backend) + `src/` (mobile) for: `dashboard`, `work_order|WorkOrder`, `triage|Triage`, `assign|Assign`, `shop|Shop`. Findings:

**Backend substrate (massive — Phase 193 is consumer-side, like 192B):**
- `src/motodiag/shop/work_order_repo.py` (748 LoC, Phase 161 + migration 026): full CRUD + 6-state lifecycle (`draft/open/in_progress/on_hold/completed/cancelled`), priority 1–5, `assigned_mechanic_user_id`.
- `src/motodiag/shop/issue_repo.py` (Phase 162 + migration 027): issues attached to WOs, 13 categories, 4 severities, 4 statuses, optional `linked_dtc_code` + `linked_symptom_id` + `diagnostic_session_id` (already source-agnostic per the architectural commitment above).
- `src/motodiag/shop/triage_queue.py` (416 LoC, Phase 164 + migration 028): `build_triage_queue()` deterministic-scoring layer + urgent/skip flags.
- `src/motodiag/shop/priority_scorer.py` (539 LoC, Phase 163): AI-driven priority override.
- `src/motodiag/shop/bay_scheduler.py` (779 LoC, Phase 165): bay assignment + scheduling. NOT in 193 scope.
- `src/motodiag/shop/analytics.py` (644 LoC, Phase 167): snapshot/revenue/top-issues. NOT in 193 scope.
- `src/motodiag/api/routes/shop_mgmt.py` (804 LoC, Phase 180): 25 HTTP endpoints under `/v1/shops/{shop_id}/*` covering profile/members/customers/intakes/work-orders/issues/invoices/notifications/analytics. **All required routes for 193 already exist**.

**Mobile substrate**: greenfield. `src/api-types.ts` has the 25 endpoints typed via openapi-typescript codegen (122 hits). Zero shop screens, zero shop hooks. Three false-positive matches in `NewSessionScreen.tsx` / `Button.tsx` / `ApiKeyModal.tsx` (the word "shop" appears in tier names + "shop-glove touch target" comments — not actual shop UI).

**Subscription/upgrade flow audit** (for Section H 402 copy decision): mobile UI has NO upgrade screen. `NewSessionScreen.tsx:331` and `NewVehicleScreen.tsx:317` have informational 402 copy ("Upgrade your subscription tier...") WITHOUT action affordance. Phase 193's 402 copy must follow this precedent — generic, no action pointer until upgrade flow ships in a future phase.

**F33 verdict**: Phase 193 is mobile-only consumer-side build on top of existing Phase 161/162/164/180 backend substrate. NO backend additions in 193's default scope.

### Mobile Commit 1 — hooks + typed errors + nav scaffolding

1. **Typed `ShopAccessError`** in `src/hooks/shopAccessErrors.ts`. Discriminated union mirroring `pdfDownloadErrors.ts`:
   - `unauthorized` (401) — "Your API key is no longer valid. Re-enter via Home → API key card."
   - `subscription_required` (402) — "Shop tier required to access this surface." (NO action pointer per subscription-audit precedent — informational only until upgrade flow ships.)
   - `not_member` (403) — "You're not a member of this shop. Ask the owner to add you."
   - Plus the standard `network` + `unknown` kinds for completeness.
   - `classifyShopAccessError({apiError, response, thrown, shopId?})` reads HTTP status from openapi-fetch response + body shape from apiError. Mirrors Phase 190 + 192B pattern.

2. **Hooks** under `src/hooks/`:
   - `useShops()` — calls `GET /v1/shops/profile/list` (existing endpoint). Returns shop-membership list for the picker.
   - `useWorkOrders(shopId, sortBy)` — calls `GET /v1/shops/{shop_id}/work-orders`. `sortBy: 'newest' | 'priority' | 'triage'`. The triage variant fetches from a separate endpoint OR uses client-side sort over the WO list with the priority field; will pin in Q&A-follow-up at Builder dispatch.
   - `useWorkOrder(shopId, woId)` — calls `GET /v1/shops/{shop_id}/work-orders/{wo_id}`.
   - `useShopMembers(shopId)` — calls `GET /v1/shops/{shop_id}/members`. Used by the assignment picker.
   - All hooks return `{data, error: ShopAccessError | null, isLoading, refetch}` shape. Typed-error-at-hook-boundary commitment per Section J.

3. **Nav scaffolding**:
   - `RootTabParamList` extended with `ShopTab: undefined`.
   - `ShopStackParamList` introduced with screens `WorkOrderList`, `WorkOrderDetail`, `ShopPicker` (modal).
   - `RootNavigator` adds `ShopTab` conditionally based on tier (read from `useApiKeyState` or equivalent — to verify against existing tier-state plumbing during build). **Tier-reactive**: when free-tier user upgrades mid-session, `ShopTab` appears without app restart. Implementation: `RootNavigator` reads tier state reactively + re-renders the tab list on tier change.

4. **Tests**: 4 new test files (1 per hook) + 1 typed-error test file = 5 new test files. Estimated 35-50 tests covering happy paths, error classification, refetch stability, multi-shop list shape.

### Mobile Commit 2 — screens (ShopPicker + WorkOrderList + WorkOrderDetail)

1. **`ShopPickerScreen`** (modal): sticky session picker. Shown on first navigate to `ShopTab` IFF user has multiple memberships. Single-membership users skip the picker (auto-select). Selection persists for the session — stored in `AsyncStorage` keyed by `shop:active:{userId}`. Cleared on cold-relaunch OR via explicit "Switch shop" affordance in settings (settings UI deferred to a follow-up phase if no settings surface exists yet).

2. **`WorkOrderListScreen`**: FlatList of WO rows.
   - Sort toggle pill: `Newest | Priority | Triage`.
   - Filter row: status (`open | in_progress | on_hold | completed`).
   - Per-row: title, vehicle, status badge, priority chip, assigned mechanic.
   - Pull-to-refresh + `useFocusEffect` refresh (Section F (b) pattern, matches `VehicleDetailScreen`).
   - Tap → `WorkOrderDetailScreen`.
   - Empty state: "No open work orders. Tap + to create." (create-button surface deferred — see Section J commit cadence note).

3. **`WorkOrderDetailScreen`**: data-driven section composition.
   - Reads `sections: WorkOrderSection[]` derived from the WO + linked issues + lifecycle data.
   - **`WorkOrderSection` discriminated union** (the load-bearing forward-look architecture):
     - `{kind: 'vehicle', rows: Array<[string, string]>}`
     - `{kind: 'customer', rows: Array<[string, string]>}`
     - `{kind: 'issues', issues: Issue[]}` — list of linked issues; each renders title + severity + status + linked DTC/symptom IDs
     - `{kind: 'notes', body: string}`
     - `{kind: 'lifecycle', rows: Array<[string, string]>}` — opened/started/completed/closed timestamps + transitions
   - Section list is built in a pure helper (`buildWorkOrderSections(wo, issues)`) that's testable without an RN renderer — same convention as Phase 192's `reportPresets.ts` / `reportStuckDetection.ts`.
   - Default rendering branches via type guards (`isVehicleSection`, `isCustomerSection`, etc.). Unknown variant → graceful "(Unknown section)" trailer (matches Phase 192's `ReportSectionCard` defensive pattern).

4. **State-transition buttons** on `WorkOrderDetailScreen`:
   - Three exposed: `Mark in_progress`, `Mark on_hold` (with reason field), `Mark completed`.
   - Two NOT exposed in 193: `draft → open` (intake-flow concern, lives in a different surface; deferred); `→ cancelled` (needs confirmation modal + reason + irreversibility-warning UX; deferred to a follow-up phase).
   - Buttons disabled when transition isn't valid for current status (read from existing backend `valid_transitions` shape; if not exposed, hardcode the transition matrix mirroring `work_order_repo.py`).

5. **Reassignment UI**: `MemberPickerModal` triggered from `WorkOrderDetailScreen` "Reassign" button.
   - Modal lists shop members from `useShopMembers(shopId)`.
   - **Default filter**: mechanic-eligible roles (mechanic / manager / owner). "Show all" affordance for the rare case the assignment shouldn't be a mechanic.
   - **Workload column**: each member row shows "Jose — 4 active WOs" if `useShopMembers` payload already includes workload counts. **F-ticket if backend doesn't surface this** — file `F36 (NEW)` and ship without workload column for 193. Verify at build time.

6. **Tests**: pure-helper tests for `buildWorkOrderSections` + section-discriminator type guards; light render tests deferred per Phase 192/192B convention (no RN component renderer in this codebase). Estimated 25-35 tests.

### Mobile Commit 3 + finalize — smoke gate + finalize docs

1. Architect-gate smoke 10 steps (~45-60 min single session, no live API costs):
   1. Shop-tier user with single membership: tap `ShopTab` → WO list renders (no picker).
   2. Tap WO → detail screen renders with all 5 default section variants.
   3. Sort toggle `Newest / Priority / Triage` cycles correctly.
   4. State transition button (`Mark in_progress`) fires + UI updates.
   5. Reassign via member-list picker → assignment changes + reflected on WO detail.
   6. Multi-shop user: shop picker shown on first `ShopTab` navigate; switching shops swaps WO list.
   7. Free-tier user attempting `ShopTab` access → 402 surfaces with correct copy (no upgrade-action affordance per audit).
   8. Member-of-other-shop attempting cross-shop deep-link → 403 surfaces.
   9. **Data-driven section rendering**: mock unknown discriminator type into the `sections` array, verify graceful "(Unknown section)" rendering. Pins the forward-looking architecture as smoke-tested.
   10. **Tier-reactive nav**: simulate free → shop tier upgrade mid-session, verify `ShopTab` appears without app restart.

2. Doc finalize:
   - `docs/phases/in_progress/193_*.md` → `docs/phases/completed/193_*.md`.
   - implementation.md v1.0 → v1.1 with as-built Results + Verification Checklist.
   - Backend `implementation.md` Phase History row (zero-LoC Phase 193 row noting "consumer-side; backend substrate untouched").
   - Mobile `implementation.md` Phase History row.
   - Both ROADMAPs mark Phase 193 ✅.

3. F-ticket dispositions at finalize:
   - F35 (NEW — triage explainability surface "why is this WO triaged here?") filed as candidate. Trigger: priority_scorer factors expand beyond current set OR mechanics ask explainability as user-pull signal.
   - F36 candidate filed if backend doesn't expose member workload counts at Commit 2.
   - F28 + F29 + F30 reaffirmed deferred (orthogonal to 193 scope).

## Key Concepts

- **`WorkOrderSection` discriminated union** — load-bearing forward-look architecture. Mirrors Phase 192's `ReportSection` shape exactly. Future phases (194 / 195 / 196) add variants without screen-rewrite.
- **Tier-reactive `ShopTab` visibility** — `RootNavigator` reads tier state reactively. Free-tier user upgrades mid-session → tab appears without restart. Smoke-tested at Step 10.
- **Sticky-session shop picker with cold-relaunch reset** — `AsyncStorage` keyed by `shop:active:{userId}`. Cleared on cold-relaunch (mechanics background constantly; "session" must NOT mean OS-level process death).
- **Single-shop optimization** — picker skipped entirely if user has one membership; auto-select.
- **`ShopAccessError` discriminated union** — 5 kinds (`unauthorized` / `subscription_required` / `not_member` / `network` / `unknown`). Subscription-required copy is generic-informational per audit (no upgrade-flow exists in mobile UI yet).
- **Sort toggle (Newest/Priority/Triage)** — same WO list, three lenses. Triage IS WO-list-by-scoring-function, not a separate screen. F35 candidate filed for explainability.
- **State-transition scope locked**: `Mark in_progress`, `Mark on_hold` (with reason), `Mark completed`. `→ cancelled` deferred (confirmation-modal-design surface). `draft → open` deferred (intake-flow surface).
- **Member-picker default filter**: mechanic-eligible roles + "show all" affordance for manager assignment.

## Verification Checklist

- [ ] `useShops` / `useWorkOrders` / `useWorkOrder` / `useShopMembers` hooks return `{data, error: ShopAccessError | null, isLoading, refetch}` shape.
- [ ] `ShopAccessError` 5-kind discriminated union covers all observed failure modes.
- [ ] `classifyShopAccessError` mirrors Phase 190 / 192B classification logic.
- [ ] 402 copy is generic-informational (no upgrade-action affordance per subscription audit).
- [ ] `ShopTab` registered as 4th bottom tab.
- [ ] `ShopTab` visible only for shop-tier users; tier-reactive (visible without app restart on upgrade).
- [ ] `ShopPickerScreen` shown on first navigate when multi-shop; auto-skipped when single-membership.
- [ ] Sticky session picker persists via `AsyncStorage`; cleared on cold-relaunch.
- [ ] `WorkOrderListScreen` renders FlatList with sort toggle (Newest / Priority / Triage) + status filter row.
- [ ] Pull-to-refresh + focus-effect refresh both fire correctly.
- [ ] `WorkOrderDetailScreen` reads `sections: WorkOrderSection[]`; renders via discriminated-union type guards.
- [ ] Unknown section variant renders as "(Unknown section)" not crash.
- [ ] State-transition buttons (`Mark in_progress`, `Mark on_hold`, `Mark completed`) fire `POST /transition` correctly + UI reflects new status.
- [ ] `Mark on_hold` requires reason field (TextInput in transition modal).
- [ ] Reassign button opens `MemberPickerModal`; default filter = mechanic-eligible roles + "show all" toggle.
- [ ] Member-picker rows show workload count if backend exposes it (F36 ticket if not).
- [ ] 402 / 403 / 401 errors surface distinct copy via `shareErrorCopy`-style helper.
- [ ] All 10 architect-smoke steps pass.
- [ ] All doc + package version bumps recorded.
- [ ] F-ticket dispositions captured at finalize (F35 NEW; F36 conditional).

## Risks

- **Tier-reactive nav implementation friction**: `RootNavigator`'s tab-list re-render on tier change requires reading tier state reactively. Existing `ApiKeyProvider` may or may not surface tier; verify at Commit 1 build time. Mitigation: if tier state isn't reactive today, file mini-F-ticket + implement minimal reactive subscription (likely 1–2 hours of work absorbed into Commit 1 scope).
- **Triage-sort backend surface unclear**: backend `triage_queue.py` exposes `build_triage_queue()` Python function but the corresponding HTTP endpoint may not exist in Phase 180's surface. Mitigation: verify at Commit 1 build time. If endpoint doesn't exist, two options: (a) client-side sort over the WO list using priority field (lossy approximation of triage); (b) add `GET /v1/shops/{shop_id}/triage` backend endpoint as a small additive Commit 0 (matches the substrate-then-feature discipline). Lean (b) if endpoint genuinely missing.
- **Member workload counts**: per Section E refinement, picker should show workload counts. Backend `useShopMembers` payload shape unverified. Mitigation: F-ticket if absent (F36) + ship without column for 193.
- **`AsyncStorage` not yet wired**: mobile codebase may or may not have `AsyncStorage` set up. Mitigation: verify at Commit 2 build time; install `@react-native-async-storage/async-storage` if needed, with 5-min compat audit per F33-style discipline.
- **Multi-shop deep-link handling**: if user has shop A active but receives a deep-link to a shop B WO, mid-session shop-switch must work without breaking nav state. Mitigation: handle in `useFocusEffect` of `WorkOrderListScreen` — if active shop differs from URL-param shop, prompt user to switch.
- **`WorkOrderSection` future-variant lock-in risk**: choosing the discriminated-union shape now commits future phases (194/195/196) to slot variants in cleanly. If a future phase needs a fundamentally different shape (e.g., embedded video player surface), the discriminated-union pattern stretches awkwardly. Mitigation: documented forward-look in plan v1.0 (this section) sets the expectation; if a phase needs structurally different shape, that phase opens a v1.0.1-amendment-style architectural-extension discussion. Phase 192's `ReportSection` precedent suggests this concern hasn't materialized yet — Variant 5 (videos with nested findings) was structurally novel and slotted in cleanly.
