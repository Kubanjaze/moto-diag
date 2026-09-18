# Phase 244V — The reference data a technician asks for mid-job — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-17

---

## 2026-09-17 — Plan v1.0 written

Opened straight off 244U's finding. The gate could finally see the layer, and
the largest coherent piece of it was reference data: four tables, complete
since Phases 92/93, reachable from nothing.

Step 0's hardest question was whether to wire it at all. The data came from
the same commit wave as the recall fixture whose "NHTSA campaign numbers"
turned out to sit on a synthetic grid (F86, assessed earlier today). The
answer is that these are different in kind — a generic torque for an M12 drain
plug is a real category, and nothing here impersonates an official identifier
— but only if every screen says which kind of number it is. That became the
phase's second requirement, ahead of the rendering.

## 2026-09-17 — Built

Four commands, one provenance constant, 55 tests, all of them through the CLI.
Testing `get_torque_spec` was never the gap; that was already done and already
passing while no human could reach the function.

The provenance test is parametrised over all nine successful screens rather
than a sample, and six negative assertions were added beside it: the screen
must not say "official", "OEM", "factory spec" or "per the manufacturer"
anywhere. Torque leads with its warning instead of trailing it, and a test
pins the ordering — the figure is acted on the moment it is read, and a
footer under twenty rows is not.

Two things the build changed from the plan. Building the full tables *through*
`list_all_torque_specs` and friends, rather than iterating the raw dicts, gave
those accessors real callers too — eight allowlist entries removed instead of
five. And `[{circuit.system}]` in a panel title renders as nothing at all,
because rich reads it as a markup tag; the system label was silently vanishing
from every circuit screen. The smoke run caught it, not review.

One of my own test assertions was vacuous: `claim not in claim.join([""])` is
`claim not in ""`, always true, so the whole check never ran. Rewritten as a
parametrised negative.

244U's two scale pins moved down and were rewritten rather than deleted. The
orphan count is now recorded as a running trend (46 → 66 → 58), and the
engine-layer assertion became a ceiling rather than a floor, so wiring more of
the layer passes and adding unreachable capability fails.

`build_service_data_context` and `build_wiring_context` stay on the shelf on
purpose, with a test naming them and saying why: generic numbers in a prompt
about a specific bike come back out as that bike's numbers.

11/11 mutations killed.

## 2026-09-17 — Complete

Regression **6,961 passed, 0 failed, 27:37**. No schema change.

Eight allowlist entries removed; the gate agreed in the stale direction, which is the half of it that only works if someone actually wires something.
