# Phase 244U — The gate can see what a re-export hides

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-17 (built 2026-09-17)

---

## Goal

Phase 209B built a reachability gate that fails in both directions and has
held for five phases. It has a blind spot: **a name re-exported from a
package `__init__` looks referenced**, because the scanner counts identifiers
and a re-export writes the name twice — once in the `from … import` alias
list, once in `__all__`.

`SafetyChecker` is how this was found. Phase 241 recorded that it had no
caller; 209B's gate never listed it, because `engine/__init__.py` re-exports
it. Four phases later 244T wired it up, and the gate had been silent
throughout.

## Step 0 — findings

All numbers measured on this tree, not carried over from the sweep that
raised the issue.

**S0-1. 🚨 The sweep's headline number does not reproduce.** It reported
"117 names across 42 modules" hidden from the gate. Measured against the
gate's own live-orphan definition — public defs with no reference, excluding
those inside already-unreachable modules — the answer is **20**. The larger
figure appears to count names inside modules the allowlist already carries as
unreachable, which the gate deliberately does not double-count.

**S0-2. The two halves are genuinely conjunctive, and the sweep was right
about that.** A re-exported name appears twice, so blanking one occurrence
leaves the other:

| what is blanked | live orphans | newly visible |
|---|---|---|
| nothing (today) | 46 | — |
| `from … import` alias lists, in `__init__.py` only | 46 | **+0** |
| `__all__` string literals, everywhere | 49 | +3 |
| **both** | **66** | **+20** |

**Seventeen of the twenty appear only when both are applied.** An
implementer who ships the `__init__` half first sees a green gate and
concludes there was nothing to find — which is exactly what the sweep warned
about, and the only part of its analysis that survived measurement.

**S0-3. What the blind spot was hiding is a layer, not a scattering.** The 20
are:

| area | names |
|---|---|
| `engine/service_data.py` | `build_service_data_context`, `get_service_interval`, `get_torque_spec`, `get_valve_clearance` |
| `engine/wiring.py` | `build_wiring_context`, `get_circuit_reference`, `get_circuits_by_system` |
| `engine/confidence.py` | `rank_diagnoses`, `score_diagnosis_from_evidence` |
| `engine/cost.py` | `CostEstimator`, `format_estimate` |
| one class each | `SymptomCorrelator`, `EvaluationTracker`, `IntermittentAnalyzer`, `PartsRecommender`, `RepairProcedureGenerator`, `SymptomAnalyzer` |
| elsewhere | `hardware/compat_repo.remove_adapter`, `hardware/scenarios.builtin_path`, `hardware/sensors.decode_pid`, `i18n/translator.set_locale` |

Torque specs, valve clearances, wiring references, cost estimates, parts
recommendations and repair-procedure generation: capability a technician
would want, that no command or route can reach.

**S0-4. `SafetyChecker` is no longer among them**, because 244T gave it a
caller the day before this phase. That is the gate working as intended, one
phase late.

## Scope

1. **`blank_exports` in `tests/support/integration_gaps.py`**, applied to the
   code view alongside `blank_comments_and_docstrings`:
   - the alias list of `from … import …`, in `__init__.py` files only — a
     package re-export is not a use;
   - string literals inside an `__all__` assignment, in **every** file.
   The module path in a `from` statement is left alone, so import-graph
   reachability is unaffected.
2. **Classify all 20** in the allowlist, each with a reason that has been
   checked rather than inferred — 209B shipped three reasons that turned out
   false, and that is the failure this phase must not repeat.
3. **Update the pinned scale** (46 → 66) and 209B's recorded orphan count,
   with a note saying why the number moved.
4. **Scanner self-tests**, in the shape 209B established: a re-exported dead
   name is visible; a name listed only in `__all__` is visible; a genuinely
   used name stays invisible; blanking does not disturb module reachability;
   and — the one that matters — **each half alone leaves the 17 hidden**.

## Non-goals

- **Wiring any of the 20.** This phase makes them visible and classified.
  What to do about an unreachable `get_torque_spec` is a product decision,
  and the operator's standing instruction from 209B is to fix the gate rather
  than build the backlog.
- **Deleting anything.** Classifying is cheap and reversible.
- **Widening the gate to private names or to `import x as y` aliases.**

## Verification Checklist

- [x] A dead name re-exported from a package `__init__` is reported
- [x] A dead name listed in a non-`__init__` module's `__all__` is reported
- [x] A name with a real caller is still not reported
- [x] Each half alone leaves 17 of the 20 hidden — the conjunctive proof
- [x] Module reachability is unchanged by the blanking
- [x] All 20 classified, every reason checked against the code
- [x] The scale pin moves 46 → 66 and says why
- [x] 209B's implementation doc records the corrected count
- [x] The gate still fails in both directions (new orphan, stale entry)
- [x] Mutations: drop each half; blank the module path too; classify with an empty reason — each caught
- [x] Full regression green

## Deviations from v1.0

**1. A test expectation of mine was wrong, and the correction is worth
keeping.** I assumed a re-exported module would show as unreachable once the
name stopped counting. It does not, and should not: `demo/__init__` importing
`demo.shelf` is a real import edge, so the MODULE is reachable while the NAME
is an orphan inside it. A capability can be importable and still be something
no user can reach. That distinction is now a test.

**2. The mutation run found the scope untested.** Nothing pinned *where* alias
blanking applies, so scoping it to package inits survived a mutation that
applied it everywhere. Pinned now, with the note that widening it is a
decision to take on purpose rather than by accident.

## Results

| | |
|---|---|
| The blind spot | a package re-export writes a name twice, so every exported name looked referenced |
| How it was found | `SafetyChecker` — Phase 241 recorded it had no caller, the gate never listed it, 244T wired it four phases later |
| Newly visible | **20** (the sweep claimed 117; measured against the gate's own live-orphan definition it is 20) |
| Conjunctive proof | alias lists alone **+0** · `__all__` alone +3 · **both +20**, 17 of which appear only together |
| What was hidden | a layer: torque specs, valve clearances, wiring circuit references, cost estimation, parts recommendation, repair-procedure generation |
| Classification | 4 readers, 4 challengers; 19 stood, 1 reason corrected |
| Allowlist | 46 → **66** entries, scale pinned, 209B's Results line corrected |
| Reachability | unchanged at 38 unreachable modules — the module path is never blanked |
| Tests added | **12** |
| Mutations | **4 of 4 caught** |
| Regression | **6,914 passed, 0 failed, 30:07** |

**What this does not do:** wire any of the 20. The operator's standing
instruction from 209B is to fix the gate rather than build the backlog, and
what to do about an unreachable `get_torque_spec` is a product decision.
