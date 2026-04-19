# MotoDiag Phase 155 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

### 2026-04-18 19:00 — Plan written, v1.0

Eighth Track F phase. NHTSA safety recall lookup. EXTENDS Phase 118 `recalls` (first Track F phase to touch retrofit-era table). ALTER TABLE ADD COLUMN (SQLite-safe) — `nhtsa_id` UNIQUE via partial index, `vin_range` JSON-or-NULL sentinel, `open` default 1. New `recall_resolutions` child table FK CASCADE (vehicle+recall) SET NULL (user).

**Scope:** Migration 023 + `advanced/recall_repo.py` (200 LoC) + `recalls.json` (30 real NHTSA campaigns from last 5 yrs) + `cli/advanced.py` +220 LoC `recall` subgroup (4 cmds) + Phase 148 `FailurePrediction.applicable_recalls` + severity-floor-raise on critical match + 30 tests.

**Non-negotiables:** EXTEND Phase 118, never duplicate. Partial UNIQUE INDEX (SQLite idiom). Zero network, bundled seed. Phase 148 integration additive. UNIQUE(vehicle_id, recall_id) idempotent mark-resolved.

**Test plan ~30:** TestMigration023 (4), TestRecallRepo (10), TestRecallLoader (4), TestRecallCLI (10), TestPhase148RecallIntegration (2).

**Dependencies:** Phase 118 `recalls` shipped. Phase 148 `advanced` group shipped. Phases 149-154 migrations sequential.

**Next:** Builder-155 agent-delegated. Architect trust-but-verify + 10-URL NHTSA spot-check.
