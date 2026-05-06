# Phase 193 — Shop Dashboard (mobile, consumer-side)

**Version:** 1.0 (plan) + 1.0.1 (Step-0 surfacing: URL-prefix correction) + 1.0.2 (Commit-0.5 surfacing: assign endpoint gap + RBAC role-name correction) + 1.1 (final: as-built Results + Verification Checklist marked + Deviations) | **Tier:** Standard | **Date:** 2026-05-06

## Plan v1.1 — Final: as-built Results + Verification Checklist marked

Phase 193 closed at Mobile Commit 3 finalize on 2026-05-06. Mobile-only consumer-side build on Phase 161/162/164/180 backend substrate, plus two architectural-blocker substrate additions (Commit 0 + Commit 0.5) that surfaced via Step-0 audits before mobile work proceeded.

### Results

| Metric | Value |
|--------|-------|
| Total commits | 6 (1 backend Commit 0 + 1 backend Commit 0.5 + 3 mobile Commits 1/2/3 + 1 finalize) |
| Backend tests added | 19 (9 sort_param + 10 assign_endpoint) |
| Backend pyproject | 0.3.4 → 0.3.6 (Commit 0 + Commit 0.5 each minor patch) |
| Mobile tests added | 137 (73 Commit 1 hooks + 54 Commit 2 helpers/screens/mutations + 10 Commit 3 smoke gate) |
| Mobile suite at finalize | 572/572 across 45 suites (435 → 572 across the phase, +137) |
| Mobile package | 0.1.4 → 0.1.7 (Commit 1 + Commit 2 + Commit 3 each minor patch) |
| F-tickets touched | F33 closed (promoted to CLAUDE.md Step 0 ahead of plan v1.0); F36 NEW filed (member workload counts deferred); F37 NEW filed (enum-value verification process refinement, deferred until 3rd instance); F28 + F29 + F30 reaffirmed deferred (orthogonal to 193 scope) |
| Plan amendments | 2 (v1.0.1 URL-prefix correction; v1.0.2 assign endpoint gap + RBAC role-name correction) |

**Key finding**: Step-0 audits caught architectural-blocker gaps **twice** in this phase (Commit 0 triage HTTP exposure + Commit 0.5 assign HTTP exposure), each time before mobile work proceeded against the missing substrate. Both followed the same shape: tiny additive backend route + tests + version bump + atomic commit, dispatched ahead of mobile work to avoid mobile-side rework. The pre-dispatch decision tree at Commit 1 dispatch (and the implicit one at Commit 2 dispatch) functioned as designed.

**Secondary finding**: F33's existing-code overlap audit catches *structural* overlaps via name-level greps but does NOT catch *value-level* enum mismatches (Phase 193's RBAC role enum was named intuitively but mismatched backend's actual choices). F37 candidate captures the gap; defer filing as a phase-sized intervention until a third instance surfaces (Phase 191B's `analysis_state` near-miss + Phase 193's role enum mismatch are data points 1 + 2).

**Tertiary finding**: opt-in tier-reactive nav design (`useTier` with 4 reactivity sources — mount + apiKey-change + AppState 'active' + explicit refetch) preserved offline behavior + handled the canonical Stripe-portal-upgrade flow without app restart. Smoke-gate Step 10 (concrete test) verified the load-bearing reactive-add property: tier flips `individual → shop` mid-session → ShopTab appears in the tab list without remount. Same shape Phase 192B used for share-flow byte-determinism: convert plan-doc claim into smoke-tested property.

### Verification Checklist (final)

- [x] `useShops` / `useWorkOrders` / `useWorkOrder` / `useShopMembers` hooks return `{data, error: ShopAccessError | null, isLoading, refetch}` shape (typed-error-at-hook-boundary).
- [x] `ShopAccessError` 5-kind discriminated union covers all observed failure modes; classifier mirrors Phase 190 + 192B logic.
- [x] 402 copy is generic-informational (no upgrade-action affordance per subscription audit).
- [x] `ShopTab` registered as 4th bottom tab; tier-reactive (visible without app restart on upgrade per smoke-gate Step 10).
- [x] `ShopPickerScreen` shown on first navigate when multi-shop; auto-skipped when single-membership (via `useFocusEffect` redirect chain).
- [x] Sticky session picker persists via AsyncStorage; cleared on cold-relaunch via App.tsx useEffect.
- [x] `WorkOrderListScreen` renders FlatList with sort toggle (Newest / Priority / Triage) + status filter row.
- [x] Pull-to-refresh + focus-effect refresh both fire correctly.
- [x] `WorkOrderDetailScreen` reads `sections: WorkOrderSection[]`; renders via discriminated-union type guards.
- [x] Unknown section variant renders as "(Unknown section variant)" not crash (smoke-gate Step 9 verified).
- [x] State-transition buttons (`Mark in_progress`, `Mark on_hold`, `Mark completed`) fire `POST /transition` correctly + UI reflects new status.
- [x] `Mark on_hold` requires reason field (TextInput in transition modal).
- [x] Reassign button opens `MemberPickerModal`; default filter = mechanic-eligible roles (`tech | apprentice` per v1.0.2 correction) + "Show all" toggle.
- [x] Member-picker rows do NOT show workload column (F36 filed; backend doesn't expose).
- [x] 402 / 403 / 401 errors surface distinct copy via `shopAccessErrorCopy` helper.
- [x] All 10 architect-smoke steps documented; Steps 9 + 10 concretely smoke-tested (load-bearing architectural commitments converted to verified properties); Steps 1-8 covered by hook + helper + classifier unit tests.
- [x] All doc + package version bumps recorded.
- [x] F-ticket dispositions captured at finalize (F33 closed; F36 NEW; F37 NEW; F28/F29/F30 reaffirmed deferred).

### Risks (final — resolution notes)

- **Tier-reactive nav implementation friction** (predicted in plan v1.0): did NOT materialize as friction. `useTier` 4-source reactivity (mount + apiKey-change + AppState 'active' + explicit refetch) shipped cleanly in Commit 1; smoke-gate Step 10 concretely verified the reactive-add + reactive-remove paths.
- **Triage-sort backend endpoint may not exist** (predicted): did materialize. Resolved at backend Commit 0 (`93af90e`) via single-endpoint-with-`sort`-query-param design; chose option (b) per the pre-dispatch decision tree's "lean" recommendation. Single endpoint maps cleaner to plan v1.0 Section C's "three lenses on one mental model" framing.
- **Member workload counts** (predicted): backend doesn't expose. F36 filed at finalize; picker ships without column. Backend audit confirmed `ShopMember` Pydantic model lacks the field; separate `MechanicWorkload` model exists but isn't joined into `/members` response.
- **`AsyncStorage` not yet wired** (predicted): did materialize. 5-min compat audit on `@react-native-async-storage/async-storage` 3.0.2 (released 2026-03-26) confirmed zero RN 0.85 / iOS 17 / Android 14 / scoped-storage open issues. Installed cleanly.
- **Multi-shop deep-link handling** (predicted): handled via `WorkOrderListScreen`'s `useFocusEffect` reading `getActiveShopId()` on focus + redirecting to `ShopPicker` if mismatch. NOT extensively smoke-tested in unit-tests — device smoke-gate is the verification surface.
- **`WorkOrderSection` future-variant lock-in risk** (predicted): mitigated. Smoke-gate Step 9 verified the defensive "(Unknown section variant)" trailer holds. Future phases (194 photos, 195 voice_transcripts, 196 obd_snapshots) extend the union additively.
- **No backend `/assign` HTTP exposure** (NOT predicted in plan v1.0; surfaced at Step-0 round 2): resolved at backend Commit 0.5 (`fcc1181`) via new `POST /assign` endpoint + `WorkOrderAssignRequest{mechanic_user_id: int | null}` body. Documented in plan v1.0.2 amendment.
- **RBAC role enum mismatch** (NOT predicted; surfaced at Step-0 round 2): plan v1.0 + Commit 1's `useShopMembers.ts` declared `'owner' | 'manager' | 'mechanic' | 'apprentice' | 'viewer'`; backend's actual enum is `('owner', 'tech', 'service_writer', 'apprentice')`. Documented in plan v1.0.2 amendment + propagated to mobile in commit `6c93904`. F37 candidate filed for process refinement.

### Deviations from Plan

- **Commit 0 added as a substrate-blocker fix** between plan v1.0 and Mobile Commit 1: Step-0 audit at Mobile Commit 1 dispatch surfaced missing triage HTTP exposure. Resolved at backend Commit 0 (`93af90e`) via single-endpoint sort-param design. Plan v1.0 anticipated this as a possible follow-up; it became necessary on Commit 1's first dispatch.
- **Commit 0.5 added as a second substrate-blocker fix** between Mobile Commit 1 and Mobile Commit 2: Step-0 audit at Mobile Commit 2 dispatch surfaced missing assign HTTP exposure + RBAC role-name mismatch. Plan v1.0.2 amendment captured both surfacings + propagated the role-name correction to mobile. Commit 0.5 (`fcc1181`) shipped the assign endpoint; mobile commit `6c93904` shipped the role enum correction.
- **Plan v1.0.1 amendment** for URL-prefix typo (`/v1/shops/` → `/v1/shop/`) landed BEFORE Mobile Commit 1 to keep plan-of-record consistent with Commit 1's hooks. Mirrors Phase 192B's v1.0.1 timing pattern.
- **Plan v1.0.2 amendment** for assign endpoint gap + RBAC role-name correction landed BEFORE Mobile Commit 2 for the same reason.
- **F36 fires at finalize** (member workload counts) per plan v1.0 risks + Section E refinement. Backend audit confirmed `ShopMember` lacks the field; picker ships without column.
- **F37 candidate filed** (process refinement: extend F33 audit to include enum-value verification). Deferred until 3rd instance of plan-vs-reality enum mismatch surfaces.

---

## Plan v1.0.2 — Commit-0.5 surfacing: assign endpoint gap + RBAC role-name correction

This amendment lands BEFORE Mobile Commit 2 begins, mirroring the v1.0.1 timing decision: surface corrections that affect downstream commits ship as their own amendment.

### Surfacing source

Phase 193 Commit 0.5 build cycle (2026-05-06). Two architectural assumptions in plan v1.0 + Commit 1 surfaced as wrong when the assign-endpoint test fixtures hit the real backend:

**(A) No assign HTTP endpoint existed.** Plan v1.0 Section E + Commit 1's `useShopMembers` hook assumed a reassign endpoint existed for the MemberPickerModal flow. Audit found `assign_mechanic()` + `unassign_mechanic()` repo functions in `src/motodiag/shop/work_order_repo.py:516+538` (Phase 161) but ZERO HTTP route called them. Same Step-0 pattern as Commit 0's triage HTTP gap. Resolved at Commit 0.5: new `POST /v1/shop/{shop_id}/work-orders/{wo_id}/assign` endpoint with `WorkOrderAssignRequest{mechanic_user_id: int | None}` body. Same auth posture as transition endpoint (basic membership check). RBAC tightening (manager/owner-only reassign of others' WOs) deferred as F-ticket candidate.

**(B) RBAC role enum was wrong.** Plan v1.0 Section E + Commit 1's `useShopMembers.ts` declared `ShopMember.role` as `'owner' | 'manager' | 'mechanic' | 'apprentice' | 'viewer'`. **Backend's actual role enum is `('owner', 'tech', 'service_writer', 'apprentice')`** per `src/motodiag/shop/rbac.py:111` `_validate_role`. Test fixture `add_shop_member(role="mechanic")` raised `InvalidRoleError`. Mobile-side hook's typed role union must mirror the real enum or TypeScript narrowing breaks for any consumer that switches on role.

### Why the Commit 1 audit didn't catch (B)

Commit 1's audit greps were on functionality keywords (`dashboard / work_order / triage / assign`) not on role names. Role enum was an architectural assumption from plan v1.0's mental model of "shop UI → mechanics get assigned" — the word "mechanic" is intuitive for the role but doesn't match backend's actual choice of "tech" + "service_writer" + "apprentice". F33's process refinement caught the structural overlaps; this miss is a per-symbol grep that was never run.

**F-ticket candidate (F37)**: extend the F33 audit step to include enum-value verification when the plan references specific enum names. Trigger: third instance where plan v1.0's enum-naming assumption mismatches backend reality (Phase 191B's analysis_state name was a near-miss; Phase 193's role enum is data point 1 explicitly catching a mismatch). Defer filing until a third instance surfaces.

### What changes

**(B)** is the load-bearing correction for downstream Commit 2:
- `src/hooks/useShopMembers.ts` `ShopMember.role` updated to backend enum `'owner' | 'tech' | 'service_writer' | 'apprentice'`. Comment block expanded with the role-mapping rationale ("tech + apprentice are mechanic-eligible for assignment picker's default filter; owner + service_writer are admin-eligible"). Existing `useShopMembers` tests' fixtures updated `mechanic` → `tech`, `manager` → `service_writer`.
- Plan v1.0 Section E's "RBAC-aware filtering" still holds — just with the corrected role names. Commit 2's `MemberPickerModal` default filter targets `tech | apprentice`; "show all" affordance unchanged.

**(A)** is fully resolved at Commit 0.5 — the new assign endpoint + 10 tests land in commit `<TBD>`. Mobile Commit 2 consumes it via `useTransitionWorkOrder` (transitions) + `useReassignWorkOrder` (assignment). No further plan changes for (A).

### Backward compatibility

- No mobile-API contract change: `useShopMembers` was Commit 1's only consumer; the hook isn't exported beyond the package + Commit 1 didn't export `ShopMember.role` outside the hook file. Type narrowing for `role` works as soon as `useShopMembers.ts` is updated; no other call sites need updating.
- 8 existing `useShopMembers` tests' fixtures updated alongside the role enum change. No assertion changes.

### Architectural commitments unchanged

- Tier-reactive `ShopTab` (Section A)
- Read + light mutation scope (Section B locked transitions: `start | resume | pause | complete`)
- Sort toggle on WO list (Section C)
- Sticky session shop picker (Section D)
- Member-picker default filter (Section E — semantics preserved, role names corrected)
- Pull + focus refresh (Section F)
- Source-agnostic UI (Section G)
- 5-kind `ShopAccessError` (Section H)
- 10 architect-smoke steps (Section I)
- 3-commit cadence (Section J — plus Commit 0 + 0.5 backend additives)

---

## Plan v1.0.1 — URL-prefix correction (singular `/v1/shop/`, not plural `/v1/shops/`)

This amendment lands BEFORE Mobile Commit 1 begins. Every Commit 1 hook references the URL prefix; plan-doc drift between v1.0 and the Commit 1 implementation would create "which is canonical?" friction for anyone reviewing Commit 1 against plan-of-record.

### Surfacing source

Phase 193 Commit 0's Step 0 audit (`93af90e`, 2026-05-06 03:48). The grep on `triage / priority_scorer / sort` in `src/motodiag/api/routes/` surfaced (a) the missing triage HTTP exposure (handled in Commit 0) and (b) a bonus discovery of the URL-prefix typo:

```python
# src/motodiag/api/routes/shop_mgmt.py:66
router = APIRouter(prefix="/shop", tags=["shop-management"])
```

Plan v1.0 Goal section + Logic section + multiple inline references all cited `/v1/shops/{shop_id}/...` (plural). Actual prefix is **singular** `/v1/shop/{shop_id}/...`. Phase 180's existing `test_phase180_shop_api.py` consistently uses `/v1/shop/...` (singular), and Phase 193 Commit 0's `test_phase193_commit0_sort_param.py` follows the same singular convention.

### Why this amendment lands NOW (not bundled at finalize)

The bundle-amendments-at-finalize discipline applies to corrections that aren't load-bearing for downstream commits. This correction IS load-bearing:

- Mobile Commit 1's hooks (`useShops` / `useWorkOrders` / `useWorkOrder` / `useShopMembers`) all hit URLs that the openapi-fetch client resolves via `api-types.ts`. After Commit 1's OpenAPI regen, the typed paths will be singular (matching the running app's actual routes).
- A reviewer comparing Commit 1's hook URL targets against plan v1.0 would find apparent drift (plan says `/v1/shops/`, code says `/v1/shop/`) and have to dig to learn the plan was wrong, not the code.
- Mid-flight surface corrections that affect downstream commits ship as their own amendment — same posture as Phase 191D's v1.0.1 corrections that surfaced during execution. Cheaper to land the one-line correction now than create plan-vs-code reading friction across all of Commit 1's review surface.

### What changes in plan v1.0 prose

All occurrences of `/v1/shops/` → `/v1/shop/`. Inline corrections applied below in the "Goal" + "Logic" + "Outputs" sections of the original v1.0 prose. Documented here at the v1.0.1 amendment for the audit-trail-preservation discipline; the inline corrections in the v1.0 sections below are NOT silent rewrites.

**No other v1.0.1 scope changes** — this amendment is purely the URL-prefix correction. Phase 193's architectural commitments (uniform display, source-agnostic UI; data-driven `WorkOrderSection` discriminated union; tier-reactive `ShopTab`; etc.) all hold unchanged.

---

## Goal

Ship the **shop-tier mechanic's primary mobile surface**: a 4th bottom-tab `ShopTab` that surfaces the existing Phase 161/162/164/180 backend substrate (work orders + issues + triage queue + RBAC) as native UI. Mechanics get a viewable, sortable, lightly-mutable list of work orders with detail screens for state transitions + reassignment.

Consumer-side phase. **Backend untouched** in default scope (Phase 180 already shipped 25 endpoints under `/v1/shop/{shop_id}/*` — singular per plan v1.0.1 amendment correction; Phase 193 Commit 0 `93af90e` extended `GET /work-orders` with the sort param). Mobile-side is greenfield: no shop screens exist, no shop hooks exist, only typed routes via openapi-typescript codegen.

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
- `src/motodiag/api/routes/shop_mgmt.py` (804 LoC, Phase 180; extended at Phase 193 Commit 0): 25 HTTP endpoints under `/v1/shop/{shop_id}/*` (singular — corrected at v1.0.1; `APIRouter(prefix="/shop")` per `shop_mgmt.py:66`) covering profile/members/customers/intakes/work-orders/issues/invoices/notifications/analytics. Phase 193 Commit 0 added `sort` query param to `GET /work-orders` per Section C's `Newest/Priority/Triage` toggle. **All required routes for 193 now exist**.

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
   - `useShops()` — calls `GET /v1/shop/profile/list` (existing endpoint). Returns shop-membership list for the picker.
   - `useWorkOrders(shopId, sortBy)` — calls `GET /v1/shop/{shop_id}/work-orders?sort={sortBy}`. `sortBy: 'newest' | 'priority' | 'triage'`. Pinned at Phase 193 Commit 0 (`93af90e`) — single endpoint with query-param dispatch (NOT separate route) per Section C's "three lenses on one mental model" framing. Backend strips triage rank/score from the response; mobile gets a uniform `{items, total}` shape regardless of sort.
   - `useWorkOrder(shopId, woId)` — calls `GET /v1/shop/{shop_id}/work-orders/{wo_id}`.
   - `useShopMembers(shopId)` — calls `GET /v1/shop/{shop_id}/members`. Used by the assignment picker.
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
- **Triage-sort backend surface unclear** (RESOLVED at Commit 0): backend `triage_queue.py` exposed `build_triage_queue()` Python function but no HTTP route called it. Step 0 audit at Commit 1 dispatch confirmed the gap. Resolved at Commit 0 (`93af90e`) via single-endpoint-with-query-param: `sort=triage` on existing `GET /v1/shop/{shop_id}/work-orders` calls `build_triage_queue` and unwraps `TriageItem` to plain WO dicts. Response shape uniform across all sort modes (option (b) of plan v1.0 considered + rejected — single-endpoint design maps cleaner to Section C's "three lenses on one mental model").
- **Member workload counts**: per Section E refinement, picker should show workload counts. Backend `useShopMembers` payload shape unverified. Mitigation: F-ticket if absent (F36) + ship without column for 193.
- **`AsyncStorage` not yet wired**: mobile codebase may or may not have `AsyncStorage` set up. Mitigation: verify at Commit 2 build time; install `@react-native-async-storage/async-storage` if needed, with 5-min compat audit per F33-style discipline.
- **Multi-shop deep-link handling**: if user has shop A active but receives a deep-link to a shop B WO, mid-session shop-switch must work without breaking nav state. Mitigation: handle in `useFocusEffect` of `WorkOrderListScreen` — if active shop differs from URL-param shop, prompt user to switch.
- **`WorkOrderSection` future-variant lock-in risk**: choosing the discriminated-union shape now commits future phases (194/195/196) to slot variants in cleanly. If a future phase needs a fundamentally different shape (e.g., embedded video player surface), the discriminated-union pattern stretches awkwardly. Mitigation: documented forward-look in plan v1.0 (this section) sets the expectation; if a phase needs structurally different shape, that phase opens a v1.0.1-amendment-style architectural-extension discussion. Phase 192's `ReportSection` precedent suggests this concern hasn't materialized yet — Variant 5 (videos with nested findings) was structurally novel and slotted in cleanly.
