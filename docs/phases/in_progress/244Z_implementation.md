# Phase 244Z — What the shelved modules would say if anyone wired them

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-18

---

## Goal

Six engine modules stay on the shelf after 244Y — `repair`, `parts`,
`workflows`, `intermittent`, `correlation`, `confidence`, 2,140 lines — because
the audit's word for them was *keep shelved*: they are the only path to content
the knowledge base does not carry. Shelved is not the same as harmless. The
audit named four things in them that would put a wrong number or a wrong
diagnosis in front of a technician the day any of them is wired, and every
one is a content defect, not a wiring defect. This phase fixes the content so
that the wire-or-delete decision, when the operator takes it, is not also a
"but first fix the prompt" decision.

It is the last letter. After this the 244 series — built-but-unreachable as
a thing the tree can see — is done, and the roadmap resumes at 245.

## Step 0 — findings

Every line verified on the tree as 244Y left it.

**S0-1. `repair.py:106` instructs the model to invent torque specs, and the
module labels nothing.** Verbatim: *`2. **Include torque specs** where
applicable (e.g., "Torque drain plug to 14-16 ft-lbs").`* `grep -c
'PROVENANCE\|generic\|verify against\|not manufacturer'` on the module
returns 0. The exemplar anchors low: `service_data.py` has the M12 drain plug
at 20 Nm (14.8 ft-lb, inside the range) and the M14 at 25 Nm (18.4 ft-lb,
~20% above it) — and low is the direction that leaks. The audit called this
its single highest risk, worse than F86: a fabricated NHTSA id was a
greppable literal; a per-call hallucinated torque leaves no literal to grep,
no fixture to correct, and no record of what was printed to whom.

**S0-2. CORR-001 is incoherent on its face, and it is the only one.**
`correlation.py:71-82`: `symptom_set` includes `"coolant smell"`, the
explanation says *"compression leak into coolant jacket"* and then *"Common
on air-cooled twins"*, `common_vehicles` is Twin Cam and Evolution. Air-cooled
engines have no coolant jacket. Severity `critical`, confidence `0.85`, and it
is the module's own docstring example. A mechanical scan of all 18 rules —
liquid-cooling symptoms (`coolant`, `radiator`, `thermostat`, `water pump`,
`cooling fan`) against air-cooled `common_vehicles` or an explanation that
says air-cooled — flags **only CORR-001**. The audit's "then the other
seventeen have not been read either" is a content-read claim this scan does
not settle, but it bounds the phase: one rule is wrong in a way a grep can
see.

**S0-3. Three charging floors at three RPMs, one of them shipping.**
`intermittent.py:243`: *"Measure charging voltage at idle with all
accessories on — should be >13V"*; `:329-330`: *"13.5-14.5V at 3000RPM;
below 13V = charging problem"*. `wiring.py:45`, which `motodiag ref circuit
charging` prints today: *"13.8-14.5V DC at 5000 RPM"*; `:56`: reg/rec failure
is *"<13.5V or >15V"*; `:49`: *"DC voltage at idle and 5000 RPM"*. The
shipped reference and the shelved one disagree on where to measure and what
passes. If `intermittent` is ever wired, one CLI prints two answers for one
part.

**S0-4. `parts.py:37` solicits part *equivalence* claims.** The
`cross_references` field's description is *"Equivalent parts from other brands
(e.g., 'Denso IU27 = NGK CR9EIA-9')"*. An invented part number fails safe —
the counter says no such number exists. An invented equivalence fails unsafe:
both numbers resolve, the wrong part ships, and it physically installs.

**S0-5. None of this reaches a user today.** All six modules are on
`MODULE_ISLANDS`. This is fix-before-wiring, and the plan says so rather
than dressing it as a live defect.

**S0-6. The wire-or-delete decision is not this phase's.** The audit scored
all six below 4.3/10 as-is, and its recommendation for four of them was
"keep shelved" because they are the only route to content the corpus lacks.
That is a product decision with a cost line (two of them spend money per
call). 244Z leaves the six exactly as reachable as it found them — not at
all — and makes the content honest so the decision is clean.

## Scope

1. **`repair.py`'s prompt stops asking for invented numbers.** Line 106
   becomes: state a torque figure only when the caller supplied one;
   otherwise say *"torque to the manufacturer's specification — see the
   service manual"*. The low-anchoring exemplar goes. `RepairProcedure`
   gains nothing; the prompt is the change. A test pins that the prompt
   contains no numeric torque example and does contain the manual referral.
2. **CORR-001 is deleted, and the scan that found it becomes a test.**
   Making the rule true would mean authoring head-gasket symptoms for
   air-cooled Harleys — which the plan's own non-goal forbids and F86 is the
   reason for. The module's docstring example points at a rule the scan finds
   consistent. The S0-2 scan runs over every rule as a test, so the next
   authored rule that puts coolant on an air-cooled twin fails there, and a
   reconstruction of the original proves the guard can fail.
3. **`intermittent.py` defers to the shipped reference for charging
   numbers.** Lines 243 and 329-330 lose their own thresholds and point at
   the charging circuit reference (`wiring.py`), which is the one source
   `motodiag ref circuit charging` prints. A test asserts no voltage or RPM
   literal in `intermittent.py` contradicts `wiring.py`'s charging entry —
   computed from both modules, not hardcoded.
4. **`parts.py` stops soliciting equivalences.** The `cross_references`
   description asks for *"alternative part numbers the technician should
   verify — never stated as equivalent"*, and the prompt text is aligned.
   A test pins the word "equivalent" out of the field description and the
   prompt.
5. **Tests through the modules**, on the content: the four changes above,
   plus the six modules still import and their existing suites still pass.

## Non-goals

- **No wiring, no deletion, no cost.** All six stay on `MODULE_ISLANDS`
  with their entries unchanged. Nothing new spends money.
- **No content authoring beyond the four items.** The other seventeen
  correlation rules, the twelve intermittent patterns and the three
  workflow scripts are not re-read here; the scan in S0-2 is a floor.
- **No API or CLI surface.**

## Verification Checklist

- [ ] `REPAIR_PROMPT` contains no numeric torque example and refers the reader to the manual
- [ ] CORR-001 no longer pairs a liquid-cooling symptom with an air-cooled vehicle; the scan passes over all rules
- [ ] No voltage/RPM literal in `intermittent.py` contradicts `wiring.py`'s charging circuit
- [ ] "equivalent" does not appear in `parts.py`'s field description or prompt
- [ ] All six modules import; `test_phase84_repair`, `test_phase153_parts`, `test_phase82_workflows`, `test_phase91_intermittent`, `test_phase90_correlation`, `test_phase83_confidence` pass
- [ ] `MODULE_ISLANDS` unchanged: 14 entries, zero stale, zero new
- [ ] Mutations: restore the torque exemplar; put "coolant" back in CORR-001; restore the 13V idle floor; restore "Equivalent" — each caught
- [ ] Full regression green
