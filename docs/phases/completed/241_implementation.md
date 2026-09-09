# Phase 241 — HV safety and lockout/tagout; Track L opens

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-09

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

- [x] Every entry reachable: a make/model-filtered lookup for an electric
      machine returns the HV safety content
- [x] No entry prints a voltage threshold, discharge wait or torque it cannot
      attribute; each such absence is stated explicitly
- [x] Provenance honest per entry, and no `model-generated` entry is phrased as
      a validated procedure
- [x] Forum-tip biconditional holds (Phase 240B rule 3)
- [x] Corpus count guard and Phase 208 doc-count guard stay green
- [x] The `SafetyChecker` integration gap is recorded, not silently filled
- [x] Every new guard mutation-tested
- [x] Full regression at or above 6007, 0 failed

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

---

## Deviations from Plan

**None to the shape of the phase** — the Step 0 findings held and the build
followed them. Three things are worth recording anyway.

**The `make` convention decided.** Every entry carries
`"Zero, Harley-Davidson, LiveWire, Energica, Damon"`, so `make LIKE '%X%'`
returns the whole file for each electric make — verified live for all five,
and for four electric models via the `model` field. The cost is that a
make-only `Harley-Davidson` query also returns HV safety content on a
Sportster. That was accepted deliberately: LiveWire *is* a Harley, the search
has no powertrain filter (the same gap that keeps `SafetyChecker` unwired), and
HV safety appearing for a Harley query is over-inclusion, not misinformation.
A prose make would have been unreachable from everything.

**My own guard fired twice on the entries, and both times the entry was
right.** The "certified procedure" guard matched *"the point the manual
specifies"* and *"the order the manual specifies"* — which is deferral, exactly
what a `model-generated` safety entry should do. Mention versus use, again.
Tightened so borrowed authority only counts when a figure follows in the same
clause. The second firing was a join artefact: `_claims()` joined fields with a
space, so a cause ending *"…the manual specifies"* ran into the next field's
*"1. Confirm"* and read as *"the manual specifies 1"*. The helper now joins on
newlines and every clause regex excludes them. Both fixes were mutation-tested
in both directions.

**Every entry is `model-generated`, and a test pins that.** No manufacturer HV
document was opened for this phase, so `service-manual` would have been a
false label on the one file where a false label is dangerous. The pin is
deliberate: the day a later phase opens a manual, this assertion is what it
changes, knowingly.

## Results

| Metric | Value |
|--------|-------|
| Entries | 10, all `model-generated`, in `known_issues_electric_hv_safety.json` |
| Corpus | 917 → **927**; four user docs moved with it |
| Severity mix | 5 critical, 4 high, 1 medium — not uniform, by guard |
| Machine-specific figures printed | **0** — no pack voltage, discharge wait or torque; every entry states the absence and routes to the manual |
| Reachable from | Zero, LiveWire, Energica, Damon, Harley-Davidson (make) and LiveWire, Ego, SR, HyperSport (model), verified live |
| Ordering | critical first through the real path — Phase 240C's fix, visible on a safety file |
| Guards | 24 |
| Mutation scenarios | 7, all caught |
| Corpus-globbing guards swept | 18 files, 635 passed, 0 objections to the new file |
| `SafetyChecker` gap | recorded as a two-part tripwire, not filled |
| Regression | **6031 passed / 0 failed** (baseline 6007; +24 guards) |

**Key finding: on a safety file, the deliberate absence is the content.** The
procedure — isolate, wait, prove the meter live-dead-live, measure, keep
custody of the disconnect, re-verify after every interruption — is
transferable and true. The figures are not, and a figure carried across from
another machine is the exact error the entries exist to prevent. Ten entries
that print no voltage, no wait and no torque, and say so in every one, are
worth more to a mechanic than ten that guess.
