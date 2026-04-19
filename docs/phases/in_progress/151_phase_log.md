# MotoDiag Phase 151 — Phase Log

**Status:** 🟡 Planned | **Started:** 2026-04-18 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 18:40 — Plan written, v1.0

Fourth Track F phase. Dual-axis (miles OR months) service-interval scheduling. Migration 019 creates `service_intervals` (per-bike) + `service_interval_templates` (global seed). ~44 canonical JSON rows. `motodiag advanced schedule {init, list, due, overdue, complete, history}` — 6 subcommands.

**Scope:**
- Migration 019 (v18→v19): two tables + 3 indexes, CHECK constraint requiring at least one interval axis.
- `advanced/data/service_interval_templates.json` — 44 rows (Harley 10, Japanese big-4 22, European 7, universal 5).
- `advanced/models.py` +~40 LoC ServiceInterval.
- `advanced/schedule_repo.py` (~220 LoC) CRUD + load + seed_from_template + match_templates_for_vehicle.
- `advanced/scheduler.py` (~150 LoC) next_due_calc + due_items + overdue_items + record_completion.
- `cli/advanced.py` +~300 LoC nested schedule subgroup.
- `tests/test_phase151_schedule.py` ~35 tests (TestMigration019×4, TestScheduleRepo×10, TestScheduler×10, TestScheduleCLI×11).

**Design non-negotiables:**
1. Pure SW + SQL + static JSON. Zero AI, zero tokens.
2. Template → instance pattern (Phase 145 mirror).
3. Phase 152 soft-dep via try/except (graceful degradation).
4. Dual-axis due arithmetic with month-end day-clamp via `calendar.monthrange`.
5. Rich Table + `--json` dual output.
6. Zero cli/main.py delta.
7. Builder claims next-available migration integer at build time.

**Dependencies:** Phase 148 hard (uses `register_advanced` group). Phase 149, 150 unrelated (different commands). Phase 152 soft (vehicles.mileage + service_history — graceful degradation).

**Open questions:** 018/019 slot, JSON template path config, month-arith library (manual chosen), schedule history panel when 152 absent, first-run re-seed policy (no, destroys last_done), parts-cost integration (Phase 154).

**Next:** Builder-151 agent-delegated. Architect trust-but-verify.
