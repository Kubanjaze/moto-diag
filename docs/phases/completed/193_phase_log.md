# Phase 193 — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-05-06
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile)
**Branch:** `phase-193-shop-dashboard` (created BOTH repos at F33 promotion commit; plan v1.0 follows)

---

### 2026-05-06 03:08 — F33 promoted to CLAUDE.md (pre-plan, separate commit)

Per Kerwyn's pre-dispatch reminder ("F33 promote-to-CLAUDE.md timing: land as separate doc commit BEFORE plan v1.0, not alongside") — atomic-per-concern git hygiene. F33 promotion is the process refinement governing how Phase 193 plan v1.0 itself gets written, so landing it FIRST means plan v1.0 can reference CLAUDE.md as canonical source rather than self-referentially documenting its own process.

**Workspace-root `CLAUDE.md` edit**: existing-code overlap audit step inserted as **Step 0** of the Phase build workflow, BEFORE Step 1 (Implementation plan). Five sub-steps (identify nouns; grep both repos; classify greenfield/extension/reshape; reshape plan if mismatch; document findings). Includes precedent cases (Phase 191B fix-cycle-3 + Phase 192 v1.0→v1.0.1 reshape) + Phase 192B validation note.

**Mobile FOLLOWUPS commit `55c34e0`**: F33 entry status flipped to CLOSED with full resolution path + historical surfacing context preserved. First commit on `phase-193-shop-dashboard` branch (mobile).

**Backend branch**: `phase-193-shop-dashboard` created from `phase-192B-pdf-export-share-sheet` HEAD. No commits yet beyond the branch-point.

---

### 2026-05-06 03:24 — Plan v1.0 written

Phase 193 opens as **mobile-only consumer-side build** on top of existing Phase 161/162/164/180 backend substrate. Same shape as Phase 192B (consumer-side after substrate audit caught Phase 182's PDF route).

**F33 audit ran BEFORE plan write** (per CLAUDE.md Step 0 — first official application of the canonical-process step):
- Backend greps for `dashboard|work_order|triage|assign|shop` → massive substrate exists. 7 Phase-161-through-167 modules totaling ~3,400 LoC under `src/motodiag/shop/` + 25-endpoint HTTP surface in `api/routes/shop_mgmt.py` (Phase 180). All routes Phase 193 needs already exist.
- Mobile greps → greenfield. `src/api-types.ts` has the routes typed (122 hits via openapi-typescript codegen). Zero shop screens / hooks / nav registration. Three false-positive matches in `NewSessionScreen.tsx` / `Button.tsx` / `ApiKeyModal.tsx` (the word "shop" appears in tier names + "shop-glove touch target" comments, not actual UI).
- Subscription/upgrade audit (for Section H 402 copy decision) → mobile UI has NO upgrade screen. Existing 402 copy in `NewSessionScreen.tsx:331` + `NewVehicleScreen.tsx:317` is informational only ("Upgrade your subscription tier...") with NO action affordance. Phase 193's 402 copy must follow this precedent — generic, no upgrade pointer until upgrade flow ships.

**F33 verdict**: Phase 193 is mobile-only consumer-side build. NO backend additions in default scope. Same posture as Phase 192B's consumer-side framing.

**Pre-plan Q&A architect-side** (no Plan agent dispatched per Kerwyn's discipline): 10 sections worked through. All 10 returned with picks + refinements:

- **A**: (a) 4th bottom tab `ShopTab`. **Refinement**: tier-reactive — free-tier user upgrades mid-session → tab appears without app restart. Smoke-tested at Step 10.
- **B**: (β) read + light mutation. **Locked transition scope**: `Mark in_progress`, `Mark on_hold` (with reason), `Mark completed` exposed. `draft → open` (intake-flow surface) + `→ cancelled` (confirmation-modal-design surface) deferred.
- **C**: (II) sort toggle on WO list (Newest / Priority / Triage). **F35 (NEW) filed**: triage explainability surface ("why is this WO triaged here?"). Trigger: priority_scorer factors expand OR mechanics ask explainability.
- **D**: (i) sticky session picker. **Refinements**: skip picker if single-membership (auto-select); "sticky for session" = until cold-relaunch OR explicit settings shop-switch (NOT until OS process death — mechanics background constantly).
- **E**: (p) member-list picker with RBAC-aware filtering. **Refinements**: default filter = mechanic-eligible roles + "show all" affordance; show workload column ("Jose — 4 active WOs") IF `useShopMembers` payload includes it (F36 ticket if backend doesn't expose; ship without column for 193).
- **F**: (b) pull + focus refresh. **Forward-looking note**: Phase 199 push notifications will handle real-time; pull/focus handles catch-up. 193's choice doesn't preclude 199's design.
- **G**: confirmed "uniform display, source-agnostic UI" posture. **Plan v1.0 documents this as the architectural commitment** (see "Architectural commitment" section in implementation.md, intro-prominent). Load-bearing piece: WO detail's section list is data-driven via `WorkOrderSection` discriminated union — same shape as Phase 192's `ReportSection`.
- **H**: `ShopAccessError` 5-kind discriminated union (unauthorized / subscription_required / not_member / network / unknown). **Refinement on 402 copy per subscription audit**: generic-informational, no action pointer until upgrade flow ships (matches `NewSessionScreen.tsx` precedent).
- **I**: 8 base steps + 2 additions = **10 architect-smoke steps**. Step 9 = data-driven section rendering (mock unknown discriminator, verify graceful handling — pins forward-looking architecture as smoke-tested). Step 10 = tier-reactive nav (simulate free→shop tier upgrade mid-session, verify ShopTab appears without restart).
- **J**: 3-commit cadence accepted. **Note**: hooks bake in typed-error union from day one — `useWorkOrders` / `useWorkOrder` / `useShopMembers` all return `{data, error: ShopAccessError | null, isLoading, refetch}`. Discriminated union surfaces at hook boundary; screens consume typed errors. Same pattern as `usePdfDownload` + `useDTC`.

**Phase 193 explicitly NOT taking on**:
- Phase 165 bay scheduling UI (deferred to its own phase or a follow-up)
- Phase 167 analytics UI (deferred)
- Phase 162 issue creation flow (Phase 193 only DISPLAYS issues — creation is a separate surface)
- Photos / voice / OBD UIs (Phases 194/195/196 — substrate left open via discriminated-union for future variants)
- Subscription upgrade flow (no audit-confirmed UI exists; not 193's concern)

**Risks at plan-write time** (full set in implementation.md):
1. Tier-reactive nav implementation friction (verify at Commit 1)
2. Triage-sort backend endpoint may not exist (verify; (b) add tiny backend Commit 0 if missing)
3. Member workload counts (F36 if backend doesn't expose)
4. `AsyncStorage` may need install + 5-min compat audit
5. Multi-shop deep-link handling
6. `WorkOrderSection` future-variant lock-in risk (mitigated by documented forward-look)

**Next step**: push plan v1.0 commit on both repos. Then begin Mobile Commit 1 (hooks + typed errors + nav scaffolding).

---

### 2026-05-06 03:48 — Step 0 (literal first step of Mobile Commit 1) surfaced missing triage HTTP exposure → Commit 0 dispatched

Per Kerwyn's pre-dispatch instruction ("Step 0 (literal first step, before any implementation): verify triage-sort backend endpoint exists. ... If no triage HTTP exposure exists at all: halt Commit 1, dispatch tiny Commit 0 backend addition first").

**5-min grep on triage / priority_scorer / sort in src/motodiag/api/routes/**:
- `GET /v1/shop/{shop_id}/work-orders` accepts `status` + `limit` only. NO `sort` param. NO `?sort=triage` surface.
- `triage_queue.py` module's `build_triage_queue()` function exists (Phase 164, 416 LoC) but is NEVER called from any HTTP route.
- Zero triage HTTP exposure across the entire shop_mgmt route file.

**Verdict**: third branch of the user's pre-dispatch decision tree. Halt Commit 1. Dispatch tiny Commit 0 backend addition first. Resume Commit 1 against the new substrate.

**Bonus discovery**: plan v1.0 incorrectly cited the URL prefix as `/v1/shops/...` (plural). Actual prefix is `/v1/shop/...` (singular — `APIRouter(prefix="/shop")` at `shop_mgmt.py:66`). To be corrected at finalize.

**Commit 0 design**:
- Add `sort: Literal["newest", "priority", "triage"] | None = None` query param to existing `GET /v1/shop/{shop_id}/work-orders`.
- `None` (omitted) or `"priority"` → existing behavior (priority ASC, created_at DESC) — backward compatible.
- `"newest"` → re-sort by `created_at DESC, id DESC` in route handler (`list_work_orders` result re-sorted in Python; no `list_work_orders` repo function changes).
- `"triage"` → call `build_triage_queue(shop_id, db_path)` and unwrap each `TriageItem` to its plain `work_order` dict. Triage rank/score/parts_ready stay server-side this phase per F35 candidate (mobile explainability deferred). Honor `status` filter post-triage. Honor `limit` post-triage.
- Response shape `{items, total}` UNIFORM across all sort modes (clients get plain WO dicts regardless of sort — no polymorphic shape).

**Why this design** (over the alternative dedicated `GET /v1/shop/{shop_id}/triage` route):
- Plan v1.0 Section C locked `Sort toggle Newest/Priority/Triage` as the UX shape — three lenses on one mental model. Single-endpoint-with-query-param maps directly. Two-endpoint-swap-hooks would require the mobile UI to swap hook calls when the toggle changes, breaking the "one list, three lenses" abstraction.
- F35 (triage explainability) is the natural follow-up that exposes rank/score; that's its own phase, not 193's concern. Stripping the rich `TriageItem` shape this phase keeps the wire surface minimal — what F35 wants is additive (new fields + maybe a separate detail endpoint), not a redesign.

**Code changes** (3 files):
- `src/motodiag/api/routes/shop_mgmt.py`: `build_triage_queue` import + extended `list_work_orders_endpoint` with `sort` query param + dispatch logic. ~50 LoC.
- `tests/test_phase193_commit0_sort_param.py`: NEW. 9 tests across 5 classes — backward-compat regression (omit sort = priority default), explicit priority matches default, newest re-sorts by created_at DESC, response shape uniform across sort modes, triage unwraps to plain WO dicts (rank/score absent), triage excludes terminal states, invalid sort = 422, sort + status filter compose correctly.
- `pyproject.toml`: 0.3.4 → 0.3.5 (additive feature minor patch).

**Verification**:
- 9/9 new tests pass.
- 54/54 in cross-phase regression sample (`test_phase180_shop_api.py` 49 tests + `test_phase164_triage_queue.py` 5 tests). Zero ripple from the route extension.

**Next step**: commit + push Commit 0. Then regenerate mobile OpenAPI types from the running app (per Phase 192B Commit 1 precedent), and resume Mobile Commit 1 (hooks + typed errors + nav scaffolding) against the new sort-aware substrate.

---

### 2026-05-06 04:14 — Mobile Commit 1 build complete

Three logical paragraphs per pre-dispatch commit-message-structure.

**Hooks + typed-error union (data layer)**. Five new hooks all return `{data, error: ShopAccessError | null, isLoading, refetch}` shape per Section J's typed-error-at-hook-boundary commitment:
- `useTier()` — fetches `/v1/billing/subscription`. Reactive across (1) mount, (2) apiKey changes (Context-driven via `useApiKey()`), (3) AppState 'active' transitions (covers external-Stripe-portal-upgrade path), (4) explicit `refetch()` for caller-driven re-fetch. Narrows `string | null` from api-types to `SubscriptionTier` union (`anonymous | individual | shop | company`). `hasShopAccess()` predicate exported for `RootNavigator` + future shop-scope-gating screens. 402 + 404 from billing endpoint resolve to `'individual'` baseline (free-tier user with no Stripe sub on file) rather than surfacing as error.
- `useShops()` — fetches `/v1/shop/profile/list`. Returns `ShopMembership[]`. Powers `ShopPickerScreen` (Commit 2) + auto-skip-when-single-membership behavior.
- `useWorkOrders(shopId, options)` — fetches `/v1/shop/{shop_id}/work-orders?sort={sortBy}&status={filter}&limit={N}`. Single endpoint, query-param dispatch (Section C lock). Phase 193 Commit 0's `sort` param consumed via the `sortBy` option.
- `useWorkOrder(shopId, woId)` — fetches `/v1/shop/{shop_id}/work-orders/{wo_id}`. Powers `WorkOrderDetailScreen` (Commit 2).
- `useShopMembers(shopId)` — fetches `/v1/shop/{shop_id}/members`. Powers `MemberPickerModal` (Commit 2). Pure helper `formatMemberName()` exported for picker-row rendering: prefers `display_name` → `username` → `User #{user_id}`.

**ShopAccessError + copy helper (error semantics)**. `src/hooks/shopAccessErrors.ts` ships the discriminated union with 5 kinds (per plan v1.0 Section H): `unauthorized` (401) / `subscription_required` (402, generic-informational copy per subscription-audit precedent — NO upgrade-action affordance until upgrade flow ships) / `not_member` (403, with `shopId` preserved for screen copy) / `network` (transport failure) / `unknown` (5xx + other 4xx). `classifyShopAccessError()` mirrors Phase 190 + 192B classification logic. `src/screens/shopAccessErrorCopy.ts` ships `shopAccessErrorCopy()` mapping each kind to `{title, message, retryable}` triples. Copy register voice/tone: informative > apologetic, action-oriented when recovery exists, terminology-consistent ("API key" / "Home" / "shop" / "member"). Commit 2's screens consume the helper for Alert + inline-error surfaces.

**ShopTab nav scaffolding + tier-reactivity (nav layer)**. `RootTabParamList.ShopTab` added to `src/navigation/types.ts`. `ShopStackParamList` introduced with three routes (`ShopPicker` modal / `WorkOrderList` / `WorkOrderDetail` with `shopId + woId` params). `src/navigation/ShopStack.tsx` ships the stack scaffold + a placeholder root screen ("Shop dashboard — Phase 193 Commit 2 lands work orders, triage, and reassign here") so Step 10 of architect-gate can verify tab visibility WITHOUT waiting for Commit 2's screens. `RootNavigator` reads `useTier()` reactively + conditionally renders `ShopTab` via `hasShopAccess(tier)`. Free-tier user upgrading mid-session → AppState 'active' on app foreground → `useTier` refetches → tier flips → `RootNavigator` re-renders → `ShopTab` appears. Smoke-gate Step 10 verifies the no-restart property.

**Verification**:
- 73 new tests across 7 test files (16 typed-error + 16 copy register + 8 useShops + 8 useWorkOrders + 4 useWorkOrder + 8 useShopMembers + formatMemberName + 13 useTier + hasShopAccess).
- 508/508 mobile suite green across 38 suites (435 → 508, +73 across this commit).
- TypeScript: `tsc --noEmit` clean.
- ESLint: 6 new `no-void` warnings (parity-preserved with `useSession.ts:67` / `useReport.ts:81` / `useSessionVideos.ts` / etc.). Zero errors.
- OpenAPI types regenerated. Diff bounded to Commit 0's `sort` param surface (api-schema/openapi.json +24 lines, src/api-types.ts +17/-1). Spot-check confirmed zero unrelated drift.

**Section E Builder-flag (workload counts)**: `useShopMembers` accepts `active_wo_count` field on `ShopMember` shape but doesn't yet verify backend exposes it. Will verify at Commit 2 build time when MemberPickerModal renders the picker rows; if absent, F36 ticket fires + ship without the workload column for 193.

**Mobile package.json**: 0.1.4 → 0.1.5.

**Next step**: commit + push Mobile Commit 1. Then begin Mobile Commit 2 (screens).

---

### 2026-05-06 04:42 — Commit 0.5 + plan v1.0.2 (Step-0 pattern fired again)

Mobile Commit 2's first step (verify reassign endpoint surface BEFORE writing the MemberPickerModal hook) surfaced two more substrate gaps:

**(A) No `/assign` HTTP endpoint existed.** `assign_mechanic()` + `unassign_mechanic()` repo functions in `work_order_repo.py:516+538` (Phase 161) had ZERO HTTP route calling them. Same Step-0 pattern as Commit 0's triage HTTP gap.

**(B) RBAC role enum was wrong in plan v1.0 + Commit 1.** Plan v1.0 Section E + `useShopMembers.ts` declared roles as `'owner' | 'manager' | 'mechanic' | 'apprentice' | 'viewer'`. Backend's actual enum is `('owner', 'tech', 'service_writer', 'apprentice')` per `rbac.py:111`. Surfaced when test fixture's `add_shop_member(role="mechanic")` raised `InvalidRoleError`.

**Why Commit 1's F33 audit didn't catch (B)**: audit greps were on functionality keywords (`dashboard / work_order / triage / assign`), not enum-value verification. F37 candidate filed (extend F33 to include enum-name checks when plan references specific values; trigger = third instance).

**Commit 0.5 backend addition**:
- `POST /v1/shop/{shop_id}/work-orders/{wo_id}/assign` endpoint added.
- `WorkOrderAssignRequest{mechanic_user_id: int | None}` Pydantic body model. `null` (explicit) unassigns; required field (omitting → 422).
- Same auth posture as transition endpoint (`require_shop_access` basic membership check). Cross-shop WOs return 404. RBAC tightening deferred.
- Imports: `assign_mechanic` + `unassign_mechanic` from `motodiag.shop`.
- Tests: `tests/test_phase193_commit0_5_assign_endpoint.py` — 10 tests across 3 classes (happy: assign / reassign / unassign-via-null; validation: omitting required field 422; auth: 401 unauth + 402 individual-tier + 403 non-member + 404 cross-shop + 404 nonexistent-WO).
- 10/10 tests pass. 41/41 in regression sample (Commit 0 9 + Commit 0.5 10 + Phase 180 22).

**Plan v1.0.2 amendment** (lands BEFORE Mobile Commit 2 begins, mirroring v1.0.1 timing): documents both surfacings + the RBAC role-correction propagation to `useShopMembers.ts`. Backward compatibility: `ShopMember.role` was Commit 1-only; type-narrowing fix is local to the hook + 8 test fixtures.

**Mobile-side correction** (rides Commit 0.5 commit since it's tightly coupled):
- `src/hooks/useShopMembers.ts` `ShopMember.role` enum updated `'owner' | 'manager' | 'mechanic' | 'apprentice' | 'viewer'` → `'owner' | 'tech' | 'service_writer' | 'apprentice'`.
- `__tests__/hooks/useShopMembers.test.ts` fixtures `mechanic` → `tech`, `manager` → `service_writer`.
- Mobile suite re-verified post-correction.

**pyproject.toml**: 0.3.5 → 0.3.6.

**Next step** (resumed after the Commit 0.5 detour): regen mobile OpenAPI types to pick up the new `/assign` endpoint, then begin Mobile Commit 2 (screens + activeShop service + AsyncStorage install + mutation hooks).

---

### 2026-05-06 05:32 — Mobile Commit 2 build complete

Substantial UI commit: 3 screens + 2 components + 2 mutation hooks + 1 service + 1 type module + 1 helper + AsyncStorage install + App.tsx wiring. Built atop Commit 1's hooks + Commit 0/0.5's backend substrate.

**5-min compat audit on `@react-native-async-storage/async-storage`** (per F33-style discipline for new dep installs): latest `3.0.2` (released 2026-03-26). Zero RN 0.85 / iOS 17 / Android 14 / scoped-storage open issues. Two open issues are v3 migration Q&As + Mac Catalyst feature request — irrelevant to our greenfield install. Decision: install `3.0.2`.

**Section E backend audit verified F36 fires.** `ShopMember` Pydantic model in `rbac.py:72` exposes `user_id / shop_id / role / joined_at / is_active / username / full_name`. NO `active_wo_count` field. Separate `MechanicWorkload` model exists (`rbac.py:95`) with `total_open` but isn't joined into the `/members` endpoint response. F36 fires at finalize per plan v1.0 risks; MemberPickerModal ships without workload column.

**Pure-logic + service modules** (5 files, 54 tests):
- `src/types/workOrder.ts` — `WorkOrderSection` discriminated union with 5 variants + 5 type guards. Mirrors Phase 192's `ReportSection` shape exactly.
- `src/screens/buildWorkOrderSections.ts` — pure helper builds `WorkOrderSection[]` from `(WorkOrderListRow, WorkOrderIssue[], joined?)`. Section order: vehicle → customer → issues → notes (omit-when-empty) → lifecycle. Always-present semantics for vehicle/customer/issues/lifecycle (matches Phase 182 convention; em-dash sentinel for missing fields).
- `src/services/activeShopStorage.ts` — sticky-shop persistence via AsyncStorage. Single key `motodiag:shop:active`. `get/set/clear` helpers + defensive null on parse errors / missing keys / invalid values. Cold-relaunch reset wired into App.tsx via `clearActiveShopId()` in the cold-mount useEffect.
- `src/hooks/useTransitionWorkOrder.ts` — POST to `/transition` with `{action, reason?, actual_hours?}`. Returns `{transition, isTransitioning, error}`. Action-agnostic (caller derives from current status — "Mark in_progress" → start when open, resume when on_hold).
- `src/hooks/useReassignWorkOrder.ts` — POST to `/assign` (Commit 0.5 substrate). Returns `{reassign, isReassigning, error}`. Pass `null` mechanicUserId for explicit unassign.

**Components** (2 files, no render tests per codebase convention; smoke-gated at Commit 3):
- `src/components/WorkOrderSectionCard.tsx` — discriminated-union renderer. Branches via type guards (5 variants today; defensive "(Unknown section variant)" trailer for forward-look). Issue rendering includes severity chip + linked DTC code + category/status meta line. Mirrors Phase 192's `ReportSectionCard` architecture.
- `src/components/MemberPickerModal.tsx` — RBAC-aware picker with default filter on `tech | apprentice` (corrected role enum per plan v1.0.2) + "Show all" toggle. Empty state copy adapts to filter mode. Workload column deferred (F36).

**Screens** (3 files):
- `src/screens/ShopPickerScreen.tsx` — modal shop picker. `onShopPicked` callback prop; ShopStack wraps to navigation.goBack() after pick (WorkOrderList re-reads activeShopId on focus).
- `src/screens/WorkOrderListScreen.tsx` — sort toggle (Newest/Priority/Triage) + status filter row + FlatList with pull-to-refresh + focus-effect refresh. Reads activeShopId on focus; redirects to ShopPicker if null.
- `src/screens/WorkOrderDetailScreen.tsx` — data-driven section rendering via `buildWorkOrderSections` + `WorkOrderSectionCard`. State-transition buttons (Mark in_progress / Mark on_hold with reason modal / Mark completed). Reassign opens MemberPickerModal. Action-availability gated by current status.

**Nav wiring**:
- `src/navigation/ShopStack.tsx` — registers WorkOrderList (initial), WorkOrderDetail, ShopPicker (modal). Render-prop-style children for ShopPicker to inject the goBack callback.
- `App.tsx` — `clearActiveShopId()` added to cold-mount useEffect. Belt-and-suspenders: shareTempCleanup sweep + activeShop reset both fire on cold-mount.

**Tests added at Commit 2** (5 files, 54 tests):
- `__tests__/types/workOrder.test.ts` (10): type-guard discrimination + union-narrowing exercise.
- `__tests__/screens/buildWorkOrderSections.test.ts` (14): section order + omit-when-empty + always-present semantics + missing-value em-dash + lifecycle timestamp surfacing + issues passthrough.
- `__tests__/services/activeShopStorage.test.ts` (15): get/set/clear cycle + defensive null handling for parse errors / 0 / negative / non-numeric / read failures + cold-relaunch round-trip.
- `__tests__/hooks/useTransitionWorkOrder.test.ts` (8): hit POST endpoint + path params + body shape (action / reason / actual_hours) + 4xx/5xx error classification + isTransitioning lifecycle.
- `__tests__/hooks/useReassignWorkOrder.test.ts` (7): hit POST assign endpoint + null-for-unassign body + 400-nonexistent-mechanic + 404-cross-shop + isReassigning lifecycle.

**Mid-build tooling fix**: useTier tests had cross-test bleed (renderHook didn't unmount, AppState listeners + fetchTier closures persisted). Added `trackedRenderHook` helper + `afterEach` cleanup pattern; "narrows known tier strings" test loop got per-iteration `unmount()` calls. Fix backfills cleanly into existing 12 useTier tests; all pass.

**Verification**:
- 54 new tests across 5 files.
- 562/562 mobile suite green across 43 suites (508 → 562, +54).
- TypeScript: `tsc --noEmit` clean.
- ESLint: 13 warnings (9 no-void parity-preserved with useSession.ts:67 pattern; 4 react/no-unstable-nested-components parity-preserved with VehiclesScreen.tsx:37 since Phase 188). Zero errors.

**F36 fires at finalize** (per Section E plan v1.0 + audit verified): backend `ShopMember` doesn't expose workload counts; MemberPickerModal ships without the column for 193.

**Mobile package.json**: 0.1.5 → 0.1.6.

**Next step**: commit + push Mobile Commit 2. Then Mobile Commit 3 (10-step smoke gate + plan v1.1 finalize + F36 ticket file + ROADMAP marks ✅).

---

### 2026-05-06 06:18 — Mobile Commit 3 + finalize (PHASE 193 COMPLETE)

10-step smoke gate executed per plan v1.0 Section I. Steps 9 + 10 are the load-bearing concrete tests per Kerwyn's pre-dispatch reminder ("convert plan-doc claims into smoke-tested properties"); Steps 1-8 are covered by hook + helper + classifier unit tests already in place from Commits 1-2.

**Smoke gate Step 9 — data-driven section rendering** (load-bearing): file `__tests__/components/WorkOrderSectionCard.smoke.test.tsx`. 4 tests. Pinned: known variants render without crashing; unknown discriminator renders "(Unknown section variant)" trailer; bare `{kind}` with no payload renders gracefully; defensive fallback heading-derivation switch doesn't render stale headings for unknown variants. **4/4 PASS.** Forward-look architecture commitment from plan v1.0 intro is now smoke-tested. Future variants (194 photos, 195 voice_transcripts, 196 obd_snapshots) extend additively; if a future phase ships a section variant the mobile build hasn't picked up yet, the screen renders the defensive trailer rather than crashing.

**Smoke gate Step 10 — tier-reactive ShopTab visibility** (load-bearing): file `__tests__/navigation/RootNavigator.smoke.test.tsx`. 6 tests. Pinned: ShopTab hidden for `individual` + null tier; visible for `shop` + `company`; **REACTIVELY adds ShopTab when tier flips `individual → shop` without remount** (the canonical Stripe-portal-upgrade flow); REACTIVELY removes when flips `shop → individual` (subscription expired/cancelled). **6/6 PASS.** Plan v1.0 Section A's tier-reactive commitment now smoke-tested. Test required mocking `@react-navigation/bottom-tabs` (Jest preset doesn't transform its ESM); mock replaces `Navigator` + `Screen` with View-based stubs that expose `tabBarLabel` props as Text nodes for scraping. Bounded mock — doesn't escape the test file.

**Smoke gate Steps 1-8 coverage map** (already verified via prior commits' tests, no new test files needed):
- Step 1 (single-membership → WO list): `useShops` + `useWorkOrders` tests pin fetch shape. Auto-skip orchestration deferred to device smoke.
- Step 2 (WO detail 5 sections): `buildWorkOrderSections.test.ts` pins section order + presence; component-render verified via Step 9.
- Step 3 (sort toggle cycles): `useWorkOrders.test.ts` pins `sortBy` query param dispatch for all 3 modes.
- Step 4 (state transition fires): `useTransitionWorkOrder.test.ts` pins POST + body shape + error classification.
- Step 5 (reassign reflected): `useReassignWorkOrder.test.ts` pins POST assign + null-for-unassign + 400-nonexistent-mechanic + 404-cross-shop.
- Step 6 (multi-shop swap): `useShops` + `activeShopStorage.test.ts` pin fetch + persistence; orchestration deferred to device smoke.
- Step 7 (free-tier 402 copy): `shopAccessErrors.test.ts` + `shopAccessErrorCopy.test.ts` pin generic-informational copy without upgrade-action affordance.
- Step 8 (cross-shop 403): `shopAccessErrors.test.ts` pins 403 → `not_member` classification with shopId preserved.

**Device smoke-gate** (per Phase 192/192B precedent): deferred until next available device session. Unit-test coverage for the load-bearing logic is in place; visual verification of the full nav + screen flows happens on hardware.

**F-ticket dispositions at finalize**:
- F33 closed (promoted to CLAUDE.md Step 0 ahead of plan v1.0; no further action).
- F36 NEW filed: backend `ShopMember` workload counts + member-picker workload column. Backend audit confirmed `ShopMember` Pydantic model in `rbac.py:72` lacks `active_wo_count`. Picker ships without column for 193. Recommended target: Phase 193+ follow-up.
- F37 NEW filed: extend F33 audit step to include enum-value verification. Phase 191B's `analysis_state` near-miss + Phase 193's role enum mismatch = data points 1 + 2; defer filing as phase-sized intervention until 3rd instance.
- F28 + F29 + F30 reaffirmed deferred (orthogonal to 193 scope).

**Doc finalize**:
- `docs/phases/in_progress/193_*.md` → `docs/phases/completed/193_*.md`.
- Implementation.md v1.0.2 → v1.1 with as-built Results + Verification Checklist + Deviations.
- Backend `implementation.md`: Phase 193 row added to Phase History. Doc/pkg version split note updated for pyproject 0.3.4 → 0.3.6. Doc version 0.13.12 → 0.13.13.
- ROADMAP marks ✅ on both repos.
- Mobile package + impl.md: 0.1.4 → 0.1.7 across the phase (Commits 1, 2, 3 each minor patch).

**Phase 193 status**: ✅ Complete. Mobile shop dashboard surface on top of Phase 161/162/164/180 backend substrate. End-to-end flow: shop-tier user taps `ShopTab` → optionally picks shop (if multi-membership) → sees WO list with sort toggle + status filter → taps WO → sees data-driven section detail → marks transitions OR reassigns mechanic via picker → list refreshes on focus. Forward-look held: `WorkOrderSection` discriminated union mirrors Phase 192's `ReportSection` shape exactly; Phases 194/195/196 will extend additively.
