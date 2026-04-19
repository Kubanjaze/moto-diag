# MotoDiag Phase 153 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

### 2026-04-18 18:50 — Plan written, v1.0

Sixth Track F phase. OEM↔aftermarket parts cross-reference. Migration 021 (next-available slot). `advanced/parts_repo.py` 250 LoC + `parts_loader.py` 100 LoC + 60 parts + 80 xrefs. `motodiag advanced parts {search, xref, show, seed}` 4 subcommands. Phase 148 `parts_cost_cents` opportunistically populated via `_lookup_parts_cost` (import-delayed, None-on-miss, Phase 148 regression safe).

**Non-negotiables:** Real OEM+aftermarket from public catalogs. Equivalence rating 1-5 curated. Cascade delete. Self-xref CHECK. Phase 145 loader pattern. Zero AI.

**Test plan ~30:** TestMigration021 (4), TestPartsRepo (10), TestPartsLoader (6), TestPartsCLI (10).

**Dependencies:** Phase 148 hard (FailurePrediction.parts_cost_cents Optional[int]), Phase 145 loader pattern reference, users.id FK Phase 112 safe.

**Next:** Builder-153 agent-delegated after Phase 148 GREEN (shipped). Architect trust-but-verify.
