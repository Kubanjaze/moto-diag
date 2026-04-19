# MotoDiag Phase 154 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

### 2026-04-18 18:55 — Plan written, v1.0

Seventh Track F phase. TSB database — OEM-issued Technical Service Bulletins. Distinct from Phase 08 known_issues (forum-consensus) and Phase 155 recalls (federal/safety).

**Scope:** Migration 022 + `advanced/tsb_repo.py` (200 LoC) + `tsbs.json` (40 real TSBs cited to public archives) + `cli/advanced.py` +220 LoC `tsb` subgroup + Phase 148 `FailurePrediction.applicable_tsbs` additive field + `~30 tests`.

**Non-negotiables:** Three independent provenance layers (TSB ≠ recall ≠ known_issue). UNIQUE tsb_number. Real numbers with public source_urls. Seed-on-init guarded. Phase 148 integration non-breaking (default_factory=list). Single TSB query per predict (no N+1). Zero AI, zero network.

**Test plan ~30:** TestMigration022 (4), TestTSBRepo (10), TestTSBLoader (4), TestTSBCLI (10), TestPhase148TSBIntegration (2).

**Dependencies:** Phase 148 `advanced_group` hard (shipped). Phases 149-153 migrations 018-021 sequential. No hardware dep.

**Next:** Builder-154 agent-delegated after Phase 153 merges. Architect trust-but-verify + 10-URL spot-check.
