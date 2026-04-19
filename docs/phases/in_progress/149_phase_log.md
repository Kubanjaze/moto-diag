# MotoDiag Phase 149 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 18:30 — Plan written, v1.0

Second Track F phase. Appends `wear` subcommand to the `advanced` Click group Phase 148 created. Distinct problem space: "mechanic reports symptoms → rank worn components" vs Phase 148's "miles/age forecast". Zero AI, zero migration, zero tokens. File-based seed of 30 curated wear patterns with forum citations + overlap-ratio scoring.

**Scope:**
- `advanced/wear.py` (~250 LoC) — WearPattern + WearMatch Pydantic v2 models + analyze_wear + lru-cached loader + tokenizer + bike-match tierer + overlap scorer.
- `advanced/wear_patterns.json` — 30 real patterns with mechanic vocabulary (`tick of death`, `chain slap on decel`, `dim headlight <1500 rpm`), inspection_steps, forum/service-manual citations.
- `cli/advanced.py` +~150 LoC — `wear_cmd` appended to Phase-148 `advanced_group`.
- `advanced/__init__.py` +3 LoC exports.
- `tests/test_phase149_wear.py` ~30 tests (TestWearPatternModel×4, TestAnalyzer×12, TestWearCommand×10, TestRegression×3).

**Design non-negotiables:**
1. **File-seeded, not DB-backed.** Editorial curated content; DB-backing is roadmap Phase 155+.
2. **No `--current-miles`** — symptom set is the signal.
3. **Scoring:** `overlap*0.7 + bike_bonus*0.3` floored by `overlap * confidence_hint`.
4. **Substring-either-direction** symptom matching for vocabulary drift.
5. **Append-to-existing-group**, not new registration — Phase 148 owns `register_advanced`.
6. **Helper reuse** (`_render_bike_not_found`, `_format_confidence`).
7. **Zero migration.** known_issues schema untouched.

**Test plan (~30):**
- TestWearPatternModel (4): round-trip, frozen, validation, tuple stability.
- TestAnalyzer (12): tokenizer, substring match, bike-match ladder, dropped patterns, generic cross-make, min_confidence boundaries, confidence_hint floor, empty symptoms, missing file, sort determinism.
- TestWearCommand (10, CliRunner): bike happy, direct-args, json, unknown-bike remediation, mutex, missing symptoms, invalid min_confidence, empty-matches panel, --help, Phase 148 predict still registered.
- TestRegression (3): Phase 148 predict, Phase 140 hardware scan, Phase 08 known_issues.

**Dependencies:** Phase 148 complete (required). No Track E migration dependency. No hardware dependency.

**Next:** Build — agent-delegated Builder-149. Architect trust-but-verify reproduces 30-test run.
