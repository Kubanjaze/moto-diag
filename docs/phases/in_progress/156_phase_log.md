# MotoDiag Phase 156 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

### 2026-04-18 19:05 — Plan written, v1.0

Ninth Track F phase. Peer-cohort anomaly detection. No AI, no migration, no tokens. Pure SQL on Phase 142 `sensor_recordings`+`sensor_samples` + `statistics` stdlib.

**Scope:** `advanced/comparative.py` (~300 LoC) with `find_peer_recordings`/`compute_peer_stats`/`compare_against_peers` + PeerStats/PeerComparison frozen dataclasses. `cli/advanced.py` +~250 LoC `compare` subgroup (3 subcommands: bike/recording/fleet). 28 tests, 4 classes.

**Non-negotiables:** Zero migration. Two-stage reduction (per-recording summary → percentile across recordings). `--peers-min 5` default noisy-stats guard. Target always excluded. `--cohort` ±1 yr default bandwidth. 200-row cohort cap. Phase 150 graceful feature-detect absence. Forum-idiom output.

**Test plan ~28:** TestFindPeers (6), TestComputePeerStats (8), TestCompareAgainstPeers (8), TestCompareCLI (10).

**Dependencies:** Phase 148 + Phase 142 hard. Phase 150 soft (feature-detect).

**Next:** Builder-156 agent-delegated. Architect trust-but-verify + 3-CLI-transcript spot-check.
