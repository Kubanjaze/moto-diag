# Phase 241 — HV safety and lockout/tagout — phase log

**Status:** Planned
**Opened:** 2026-09-09

---

## 2026-09-09 — Plan v1.0 written; Track L opens

Track L (241–250) is electric. This phase is its opener and the safety floor
every later electric phase stands on.

**Step 0 — existing-code audit.** Four findings, two of which changed the
phase's shape.

**1. Extension, not greenfield.** The EV substrate shipped at Phases 110/111
and is already seeded *and* powertrain-scoped: `vehicles.powertrain`,
`battery_chemistry`, `motor_kw`, `bms_present`; `EngineType.ELECTRIC_MOTOR`;
six EV `DTCCategory` members; and `dtc_category_meta` rows scoped
`["electric","hybrid"]` with `hv_battery`, `motor` and `inverter` already
defaulting to **critical**. Plan v1.0 is written as extension from the start
rather than as greenfield with a v1.0.1 reshape to follow — the F33 discipline
added after Phase 192 was reshaped mid-flight for exactly this.

**2. `SAFETY_RULES` exists, and nothing in production calls it.** This is the
finding that set the phase's boundary. `engine/safety.py` holds a 19-rule
engine with precisely the right shape for HV work — `level`, `patterns`,
`immediate_action`, and a `do_not` field for the critical warning. Only two
rules touch anything electrical, both ICE wiring fires.

But an exhaustive sweep for `SafetyChecker`, `check_diagnosis`,
`check_symptoms`, `check_repair_procedure` and `format_alerts` across `src/`
returns only `engine/__init__.py` (the export line) and `safety.py` itself. No
API route, no CLI command, no engine path constructs it. **Only tests do.**

So HV rules are deliberately **not** going into `SAFETY_RULES` in this phase.
Adding them would ship the appearance of a safety system with no path to a
mechanic — the integration-gap family CLAUDE.md records at Phase 195, where
`cleanupOldAudio` was implemented and tested in isolation and the wiring was
never landed: function tests green, integration absent. On high voltage that
is not an acceptable failure mode. The gap is recorded for its own phase, which
must both wire the checker into a real path and make it powertrain-aware —
`SafetyChecker` takes no vehicle context today, so an HV rule added now would
fire on a carburetted twin.

**3. The content ground is genuinely empty.** `tagout`, `service plug`,
`traction battery`, `insulated glove` and `regen` appear in **zero** knowledge
files; `high voltage` in one and `BMS` in one. All seven `lockout` hits are
false positives — a heated-grip engine-running lockout, the Ducati/MV
dealer-tool lockout, and a Baker Grudge compensator. So the entries are real
new work, not a re-cut of existing material.

**4. A cross-make entry must not carry a prose `make`.** Phase 240B's S2
established that `make LIKE '%X%'` can never match `'All European makes'`, and
three Track K entries are unreachable today because of it. The existing
`known_issues_cross_platform_*.json` files sidestep this by carrying real make
names (Honda, Kawasaki, Suzuki, Yamaha, Harley-Davidson). HV safety content is
cross-make by nature, so this phase decides the convention deliberately and
asserts reachability in a test rather than inheriting the defect.

**A note on why the provenance discipline matters more here.** Track K built it
to keep a valve interval honest. This is the first phase whose content can kill
someone if it is wrong: a `model-generated` entry phrased as a verified
discharge procedure is worse than no entry, because it looks like something a
shop is entitled to act on. Where no primary document is opened, the entry will
say so and route to the manufacturer's manual rather than print a figure — the
Phase 224/234 deliberate-absence rule, applied to voltages and wait times.

Baseline before any work: **6007 passed / 0 failed** (Phase 240C).

Plan v1.0 written to `docs/phases/in_progress/241_implementation.md`.
