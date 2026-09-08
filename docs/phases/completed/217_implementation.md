# Phase 217 — Ducati Panigale superbike line

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Cover the Panigale line — 899/959/1199/1299 Superquadro V-twins and the
V4 Desmosedici Stradale — plus the **Streetfighter V4/V2**, which the
Phase 216 audit moved here because they are Panigale-derived and share
nothing mechanical with a V-twin Monster.

Written by hand this phase, sequentially. The previous five content
phases used multi-agent draft-and-refute; that is being set aside for
cost, so the same discipline is applied directly: specificity over
genericness, figures deferred to the manual, honest tagging, and the
deferral boundaries enforced by test.

CLI: `motodiag kb list --make ducati`; guard is
`pytest tests/test_phase217_ducati_panigale.py`.

Outputs:
- `src/motodiag/knowledge/seed/knowledge/known_issues_ducati_panigale.json`
- `tests/test_phase217_ducati_panigale.py`
- Corrected comment in `tests/test_phase216_ducati_monster.py` (below)
- Documented known-issue count updated (716 → 716 + N)

## Existing-code audit (Step 0, per CLAUDE.md)

Run inline. Nouns: `panigale`, `superquadro`, `desmosedici`,
`streetfighter`, `monocoque`, `ohlins`, plus the 216 titles.

**1. A guardrail I wrote one phase ago is wrong, and this phase is
where it breaks.** Phase 216's test file carried the comment *"Ducatis
are belt driven"* and denies `cam chain` on every Monster entry. That
is true of the Desmodue, Desmoquattro and Testastretta engines in that
file — and **false of the Panigale**. The Superquadro drives its cams
by a chain running to a gear train between the camshafts, explicitly to
remove belt service; the V4 Desmosedici Stradale is likewise
chain-driven. Verified by search rather than assumed.

The Phase 216 assertion is scoped to the Monster file, so nothing
breaks behaviourally — but the *comment* stated a false generalisation
about Ducati, and has been corrected in place to say the rule covers
the Monster-line engines only. **Phase 217 must not inherit it**: an
entry claiming cam belts on a Panigale would be wrong, and a "no belt
service" note is a legitimate Panigale diagnostic point.

This is the third guardrail inversion in six phases (214 Paralever, 216
dry clutch, 217 cam drive) and the first that inverts *within* a block.

**2. Greenfield for content.** No `panigale` or `superquadro` string
exists anywhere in the knowledge base. Eight Ducati adapter compat rows
mention Panigale, but those are Phase 220's surface and are untouched.

**3. The genericness risk is the highest of any phase so far.** The
corpus already holds **six** litre-class superbikes — CBR1000RR,
ZX-10R, GSX-R1000, YZF-R1, GSX-R1100 and BMW S1000RR — and Phase 213
lost 12 of 18 candidates to exactly this. A Panigale entry must name
Panigale hardware or it is a seventh copy of a story already told.

**4. Deferrals, unchanged from the block.** To **219**: desmodromic
valve service — intervals, opener/closer shims, clearances, cost.
(Search surfaced the 1199's 15,000 mi / 24,000 km desmo interval; that
figure belongs to 219 and is deliberately not written here.) To **220**:
Marelli ECU, DDA+, Ducati CAN, the DDS tool, any fault code —
`dtc_codes` stays `[]`. Cam belts were in scope for 216 but are
**irrelevant here**, which is itself the point.

**5. Contract** unchanged: `make == "Ducati"`, `source:
model-generated` in the JSON, "general knowledge" in every description,
symptoms as short LIKE-searchable phrases, no title collision with the
12 Monster entries, 2012 year floor (the 1199 is MY2012).

## Logic

1. Draft entries by hand across: Superquadro V-twins (1199/1299,
   899/959), the V4 (Panigale V4 2018+, V4 R, V4 SP), the
   Streetfighter V4/V2, and the chassis/electronics that are
   structurally Ducati (monocoque airbox-frame, Öhlins Smart EC).
2. Every entry must pass the test I would have given a refuter: could
   this sentence appear unchanged on a ZX-10R? If yes, cut it.
3. No figure stated as a specification unless deferred to the manual.
4. Validate mechanically (fields, vocabulary, deferrals, generation
   claims, symptom length), write, test, regress.

## Key Concepts

- **Chain-and-gear cam drive** is the Panigale's defining service
  difference from every earlier Ducati: no belt interval, a different
  noise signature, and cam timing adjustable at the gears.
- **Monocoque construction**: the 1199+ uses the airbox as the
  structural member bolted to the heads — there is no conventional
  frame to inspect, which changes crash assessment exactly as the
  Monster 937's Front Frame did.
- **The V4 is a different engine family** from the Superquadro:
  counter-rotating crankshaft, twin-pulse firing, and a rear-bank
  deactivation strategy at idle that owners misread as a misfire.
- **Streetfighter V4/V2 arrive here by audit**, not by the roadmap row.

## Verification Checklist

- [x] 10 entries, hand-drafted; every one `make == "Ducati"`, explicit
      model + generation, `source == "model-generated"`, "general
      knowledge" in the description, `dtc_codes == []`
- [x] No entry **claims** a cam belt on a Panigale — asserted on
      title/description/causes/fix_procedure, with a counter-assertion
      that the Monster file still owns belts
- [x] A symptom may still *report* a mistaken belt quote — asserted,
      because that is the complaint this phase exists to answer
- [x] Every entry names Panigale hardware (Superquadro, Desmosedici
      Stradale, monocoque, Smart EC, counter-rotating crank, rear-bank)
- [x] No Monster title collision; both Ducati files load to 22
- [x] No Phase 219 valve-service or Phase 220 ECU/tool content
- [x] Symptom needles quoted from the shipped data
- [x] Phase 216's false "Ducatis are belt driven" comment corrected in
      place; its 24 tests still pass
- [x] 20 phase tests; F9 lint clean; regression **5100 / 0**

## Risks

- **Hand-drafting removes the adversarial check that caught real errors
  in 212–216.** The mitigation is that the mechanical validator and the
  test file encode what the refuters were checking — attribution,
  deferral, genericness, figures — but a human-written entry that is
  confidently wrong has no second reader this phase. Stated plainly so
  the record is honest.
- **The V4 is recent and electronics-dense**, and most of its
  electronics belong to Phase 220. Expect a small file rather than a
  padded one.
- **Every entry stays tagged `model-generated`** and the CLI warns on
  each; nothing here is a service manual.


## Deviations from Plan

**Hand-drafted, no workflow.** The user asked for lean running, so the
draft-and-refute pipeline used in 212–216 was set aside. The validation
it provided was reproduced mechanically: a claim-level checker for the
inverted belt rule, deferral checks, generation and specificity checks,
and symptom-format checks. What was *not* reproduced is an independent
reader — stated in the Risks section before drafting and worth
repeating here.

**The audit found a guardrail I had written one phase earlier was
wrong.** Phase 216's test file said "Ducatis are belt driven". Verified
by search: the Superquadro drives its cams by a chain to a gear train
between the camshafts, specifically to remove belt service, and the V4
is chain driven too. The Phase 216 assertion was scoped to the Monster
file so nothing broke behaviourally, but the comment was a false
generalisation and has been corrected in place.

**My validator was wrong a third consecutive time.** It flagged the
symptom "quoted for cam belts on a panigale" as claiming the bike has
belts. It does not — it records the mistaken quote a shop gives, which
is precisely the complaint the entry answers. The rule now runs on
title, description, causes and fix_procedure and deliberately not on
`symptoms`, because a symptom is a *report*, which may include a
mistaken belief. That distinction is now written into the test file.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 716 → 726 |
| Panigale entries | 10 (Superquadro, V4, Streetfighter V4, 899/959) |
| Guardrail inversions in the block so far | 2 (dry clutch, cam drive) |
| Phase tests | 20 |
| Backend regression | 5100 passed / 0 failed |

**Key finding: a guardrail can be wrong against the phase that follows
it in the same block, by the same manufacturer.** Phase 216 correctly
denied cam chains on the Monster line and generalised that to "Ducati".
One phase later the same make's flagship contradicts it. Rules learned
from a platform have to be re-derived against the next platform even
when the badge does not change — and the check that enforces a rule
needs the same scepticism as the content it polices, which is now the
third phase running where my own validator, not the content, was at
fault.
