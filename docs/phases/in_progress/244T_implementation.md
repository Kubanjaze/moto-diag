# Phase 244T — A hazard is told to the person holding the wrench

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-17

---

## Goal

`engine/safety.py` has 19 rules that read a diagnosis and raise "brake system
failure — do NOT ride", "fuel leak — do not start the engine". **No product
path calls it.** Phase 241 recorded that as its own open finding; four phases
later it is still true, and `media/analysis_worker.py:223` names
`SafetyChecker` as the canonical example of the family.

It is invisible to the 209B reachability gate because `engine/__init__.py`
re-exports the name, which the scanner counts as a reference — the blind spot
244U exists to close.

## Step 0 — findings

Ran as a design plus an adversarial check inside 244R's sweep. **The checker
broke the design's central item**, and it is the one that decides whether this
phase makes the product safer or less safe.

**S0-1. Do not infer "electric" from the make.** The design proposed deriving
it from the corpus marque vocabulary or a hardcoded list. Both fail, in
opposite directions and on the same manufacturer: the corpus-derived route
classifies **Harley-Davidson as an electric marque**, so high-voltage rules
would fire on the operator's own carburetted Road King; the hardcoded list
misses **LiveWire, which is sold as a Harley-Davidson model**.

**S0-2. A second writer already sets powertrain from a guess.**
`cli/main.py:579` sets `PowertrainType(guess.powertrain_guess)` inside
`garage_add_from_photo` — a vision model's opinion, with no confidence floor.
So "the garage record" is not a wholly human-entered field.

**S0-3. There are no high-voltage rules.** All 19 rules are
internal-combustion or universal: fuel, brakes, chain, tyres, valve clearance,
spark plugs. Phase 241's HV safety knowledge lives in `known_issues`, not
here. So scoping by powertrain can only ever *suppress* engine-specific rules
on an electric bike; it cannot add the rules that bike would need.

**S0-4. What the rules actually fire on.** Measured against all 970 corpus
entries (title + description + symptoms, the closest available stand-in for
diagnosis text — the database holds exactly one real AI diagnosis):

| | |
|---|---|
| Entries firing any alert | **291 / 970 (30.0%)** |
| Entries firing a CRITICAL | **96 (9.9%)** |
| Alerts by level | caution 185 · critical 98 · info 72 · warning 37 |

Rendering all four levels would put a notice on about a third of jobs, most
of it caution-grade ("oil leak"). **Operator's decision, 2026-09-17: show
CRITICAL and WARNING only.**

## Scope

1. **Rules carry `applies_to`.** Each of the 19 declares the powertrains it
   makes sense for; absent means all. Only the unambiguous engine-specific
   ones are narrowed (fuel leak, fuel odour, spark plugs, valve clearance,
   air filter, head gasket, exhaust leak). Brakes, steering, tyres, chain,
   wheel bearings and electrical shorts stay universal.
2. **`SafetyChecker(powertrain=...)` filters by it**, and **unknown means
   show everything**. Suppressing a fuel-leak warning because a garage row is
   blank is the wrong direction to fail in.
3. **The powertrain comes from the garage record only** — never inferred from
   make or model (S0-1). Recorded with it: that field can itself come from a
   photo guess (S0-2), which is a reason to prefer showing an ICE rule over
   hiding it, not a reason to guess differently.
4. **`diagnose quick` and `diagnose start` render the alerts**, above the
   ranked diagnoses, at CRITICAL and WARNING only. The check reads the
   model's diagnosis text and the technician's own symptom text.
5. **Tests through the commands**, including the two inverse cases: a
   caution-grade phrase produces no panel, and an engine-only rule does not
   fire on an electric bike.

## Non-goals

- **Writing high-voltage rules** (S0-3). That is content work with a real
  sourcing burden, and inventing it is what 245 was rejected for. Filed.
- **`check_repair_procedure`**, the second entry point, stays unwired.
- **The API and the mobile app.** Neither renders safety alerts; this phase
  does not pretend otherwise.
- **Any new database field.**

## Verification Checklist

- [ ] A critical-grade diagnosis shows the alert in `diagnose quick`
- [ ] A warning-grade diagnosis shows it too
- [ ] A caution-grade diagnosis shows nothing — the operator's threshold
- [ ] The technician's typed symptoms are checked, not only the model's text
- [ ] An engine-only rule does not fire on an electric bike
- [ ] A universal rule still fires on an electric bike
- [ ] An unknown powertrain shows everything, rather than suppressing
- [ ] Nothing infers electric from the make: a Harley stays ICE, a LiveWire is not special-cased
- [ ] `diagnose start` renders the same way
- [ ] A safety failure never takes down the diagnosis
- [ ] Mutations: unwire the caller; drop the threshold; drop the scoping; invert unknown-powertrain; infer from make — each caught
- [ ] Full regression green
