# Phase 244T — A hazard is told to the person holding the wrench

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-17 (built 2026-09-17)

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

- [x] A critical-grade diagnosis shows the alert in `diagnose quick`
- [x] A warning-grade diagnosis shows it too
- [x] A caution-grade diagnosis shows nothing — the operator's threshold
- [x] The technician's typed symptoms are checked, not only the model's text
- [x] An engine-only rule does not fire on an electric bike
- [x] A universal rule still fires on an electric bike
- [x] An unknown powertrain shows everything, rather than suppressing
- [x] Nothing infers electric from the make: a Harley stays ICE, a LiveWire is not special-cased
- [x] `diagnose start` renders the same way
- [x] A safety failure never takes down the diagnosis
- [x] Mutations: unwire the caller; drop the threshold; drop the scoping; invert unknown-powertrain; infer from make — each caught
- [x] Full regression green

## Deviations from v1.0

**1. 🚨 Wiring it up found two critical false alarms.** Nothing had pressed
these patterns against real diagnosis text in four phases. `gas(oline)?`
matched the "gas" inside **"gasket"**, so *"valve cover gasket weeping; no
other leak found"* printed **CRITICAL: FUEL LEAK — do not start the engine**.
`oil` matched the "oil" inside **"coil"**. Together they account for **22 of
the 98 critical alerts** the corpus produced. Fixed here rather than deferred,
because the threshold this phase chose renders exactly those.

**2. The first fix silenced the rules it was guarding.** Word boundaries went
in as plain Python strings, where `\b` is a backspace character, not a regex
boundary — so "fuel leaking from the petcock" stopped alerting. Raw strings,
and tests in both directions now.

**3. The measured rates changed, and the plan's numbers with them.** After the
pattern fix: 29.7% of corpus entries fire something and **10.8% fire a
critical or warning** — what a technician now sees. The plan's 9.9% critical
was partly the bug.

**4. Phase 241's tripwire fired, exactly as designed.** Its failure message
carried three instructions for the day someone wired the checker: give it
powertrain context (done), add the withheld HV rules (**not** done — no
sourceable content, filed as **F88**), delete the tripwire (done, replaced by
its inverse so the surface cannot quietly go dark).

## Results

| | |
|---|---|
| The gap | 19 rules, no caller since Phase 241 — now rendered by `diagnose quick` and `diagnose start` |
| Threshold | CRITICAL + WARNING, the operator's decision from measurement: **10.8%** of corpus entries reach it |
| Electric detection | the garage record only. Inferring from the make calls Harley-Davidson electric and misses LiveWire |
| Unknown powertrain | shows everything — the field can hold a photo model's guess |
| False alarms removed | **22 of 98 criticals**, from two substring matches (Deviation 1) |
| Input | the model's diagnosis AND the technician's typed symptoms |
| Failure behaviour | a safety failure is logged and swallowed; the diagnosis always renders |
| HV rules | none exist, so an electric bike gets fewer alerts rather than the right ones — **F88**, not invented |
| Tests added | **26** |
| Mutations | **9 of 9 caught** (the run also exposed a weak assertion of mine) |
| Regression | **6,914 passed, 0 failed, 30:07** |
