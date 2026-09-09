# Phase 241 — HV safety and lockout/tagout; Track L opens

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-09

## Goal

Give a mechanic the safety ground floor for working on a high-voltage
motorcycle: how the pack is isolated, how isolation is *verified* rather than
assumed, what tooling and PPE the job requires, and what qualification the work
demands. Track L's opener, and the phase every later electric phase stands on.

The distinguishing constraint is that **this is the first phase whose content
can kill someone if it is wrong**. Track K's provenance discipline was built for
quoting a valve interval. Here it is load-bearing: a `model-generated` entry
that reads like a verified discharge procedure is more dangerous than no entry,
because it looks like the thing a shop is entitled to act on.

CLI: no new commands. Content reaches mechanics through existing surfaces —
`kb search`, `kb symptom`, `diagnose`.

Outputs:
- `known_issues_electric_hv_safety.json` — HV safety and LOTO entries
- `tests/test_phase241_hv_safety.py`
- a recorded finding on `engine/safety.py` (see Logic, item 2)

## Logic

### Step 0 findings that set the scope

**1. This is extension, not greenfield.** The EV substrate shipped at Phases
110/111 and is already seeded and powertrain-scoped:

| substrate | state |
|---|---|
| `vehicles.powertrain`, `battery_chemistry`, `motor_kw`, `bms_present` | migration 110 |
| `EngineType.ELECTRIC_MOTOR` | `core/models.py:81` |
| `DTCCategory` — `HV_BATTERY`, `MOTOR`, `INVERTER`, `REGEN`, `CHARGING_PORT`, `THERMAL` | `core/models.py:180+` |
| `dtc_category_meta` rows, scoped `["electric","hybrid"]`, `hv_battery`/`motor`/`inverter` defaulting to **critical** | seeded |
| `workflow_templates.applicable_powertrains` | migration |

The plan is therefore written as extension from the start. This is the F33
discipline: Phase 192 was reshaped mid-flight for assuming greenfield, and the
audit step exists to stop that repeating.

**2. `SAFETY_RULES` exists — and nothing in production calls it.**
`engine/safety.py` holds a 19-rule engine with exactly the right shape
(`level`, `patterns`, `immediate_action`, and a `do_not` field). Two rules touch
anything electrical, both ICE wiring fires.

But an exhaustive sweep finds `SafetyChecker` referenced **only** in
`engine/__init__.py` (the export) and its own module. No API route, no CLI
command, no engine path constructs it. Only tests do.

**So HV rules must not go there in this phase.** Adding them would ship the
*appearance* of a safety system with no delivery path to a mechanic — the
integration-gap family CLAUDE.md documents at Phase 195 (`cleanupOldAudio`
implemented and tested, wiring never landed; function tests green, integration
absent). On high voltage that failure mode is not acceptable. The gap is
recorded as a finding for its own phase, which must wire the checker into a
real path *and* make it powertrain-aware — it has no vehicle context today, so
an HV rule would fire on a carburetted twin.

**3. The corpus is genuinely empty here, so the content work is real.**
`tagout`, `service plug`, `traction battery`, `insulated glove` and `regen`
appear in **zero** files; `high voltage` in one, `BMS` in one. All seven
`lockout` hits are false positives — heated-grip lockout, dealer-tool lockout, a
Baker Grudge compensator.

**4. A make-agnostic entry must not use a prose `make`.** Phase 240B's S2
established that `make LIKE '%X%'` never matches `'All European makes'`, and
three Track K entries are unreachable because of it. The existing
`known_issues_cross_platform_*.json` files avoid this by carrying real make
names. HV safety entries are cross-make by nature, so this phase must decide
the `make` convention deliberately rather than inherit the bug.

### What this phase ships

Knowledge entries covering: the service-disconnect/service-plug isolation
concept and why removal is not by itself proof of isolation; verification of
absence of voltage as a *measured* step with a meter proven live-dead-live;
the capacitor discharge interval and why the wait is not optional; insulated
tooling and PPE classes; single-person-working prohibitions; what qualification
the work requires and where the corpus must stop short of asserting a figure.

Every entry states what it rests on. Where no primary document was opened, the
entry says so and routes to the manufacturer's manual rather than printing a
number — the Phase 224/234 deliberate-absence discipline, applied where the
absence is a voltage or a wait time.

## Key Concepts

- **Provenance as a safety property.** `service-manual` means a primary
  document *states* the claim; `regulation` means legal or standards text.
  A procedure entry that cannot cite one of those must not read like a
  procedure.
- **Deliberate absence.** A withheld figure is a deliverable when the
  alternative is a plausible invention. Stating "this figure is not established
  here — read the manual for the machine" is the safe answer.
- **Reachability is part of correctness** (Phase 240B, S2). An entry a
  make-filtered lookup cannot return is not shipped, it is buried.
- **Integration gap.** A module with no production caller is not a feature.
- **Constant-for-invariant.** Guards assert the property, not the count.

## Verification Checklist

- [ ] Every entry reachable: a make/model-filtered lookup for an electric
      machine returns the HV safety content
- [ ] No entry prints a voltage threshold, discharge wait or torque it cannot
      attribute; each such absence is stated explicitly
- [ ] Provenance honest per entry, and no `model-generated` entry is phrased as
      a validated procedure
- [ ] Forum-tip biconditional holds (Phase 240B rule 3)
- [ ] Corpus count guard and Phase 208 doc-count guard stay green
- [ ] The `SafetyChecker` integration gap is recorded, not silently filled
- [ ] Every new guard mutation-tested
- [ ] Full regression at or above 6007, 0 failed

## Risks

- **The tempting scope error is wiring `SafetyChecker` in this phase.** It
  needs a production caller *and* powertrain awareness, and it touches the
  diagnostic path. That is its own phase; doing it here would bury HV content
  work inside an engine change.
- **Plausible-sounding invention is the failure mode that matters.** HV
  procedures are widely described online and easy to write fluently. The
  research must distinguish "the manual says" from "the internet says", and the
  entry must too.
- **A cross-make `make` value can silently bury the content** — the S2 defect.
  Decide the convention, then assert reachability in a test.
- **Severity inflation.** Everything about HV feels critical; if every entry is
  `critical` the ranking carries no information. Phase 240C made severity
  ordering real, so the values now decide what a mechanic sees first.
- **No electric bike exists in the corpus yet**, so a reachability test needs a
  seeded electric vehicle — the fixture is part of the work, not an aside.
