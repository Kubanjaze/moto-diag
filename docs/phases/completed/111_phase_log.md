# MotoDiag Phase 111 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-17
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 13:05 — Plan written, v1.0
Knowledge base schema expansion. Migration 004 adds DTC categories column + dtc_category_meta table. New DTCCategory enum covering HV/battery/motor/regen/TPMS/emissions alongside existing engine/fuel/ignition/ABS etc. OEM-specific DTC format classifiers for BMW/Ducati/KTM/Triumph/Aprilia. All 1651 existing tests must still pass.

### 2026-04-17 13:25 — Classifier ordering issue discovered
Initial implementation put Aprilia's `DTC-NNNN` classifier AFTER Ducati's `DTC-` check, causing Aprilia codes to be misclassified as Ducati DDS. Fixed by:
1. Placing Aprilia check first when `make="Aprilia"` hint provided
2. Tightening Ducati regex to require letter prefix `DTC-[PA]NNNN` (not just `DTC-*`)
3. Order: Aprilia → Ducati → KTM → Triumph

### 2026-04-17 13:40 — Build complete, v1.1
- Created migration 004: dtc_category column + dtc_category_meta table with 20 pre-seeded categories
- Added DTCCategory enum with 20 members (7 ICE + 7 chassis/safety + 6 electric + unknown)
- Extended DTCCode model with optional dtc_category field (default UNKNOWN), backward compat preserved
- Added 6 OEM classifiers to fault_codes.py: BMW_ISTA, DUCATI_DDS, KTM_KDS, TRIUMPH_TUNEECU, APRILIA_DIAG, ELECTRIC_HV
- Added 3 repo functions: get_dtcs_by_category(), get_category_meta(), list_all_categories()
- Bumped SCHEMA_VERSION 3 → 4
- 43 new tests in test_phase111_kb_schema_expansion.py (all passing in 1.31s)
- Full regression: 1694/1694 passing in 3m 14s — zero regressions
- Rollback of migration 004 verified (removes column + meta table cleanly)
