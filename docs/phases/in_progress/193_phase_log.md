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
