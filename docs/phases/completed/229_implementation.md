# Phase 229 — Triumph vintage (pre-Hinckley + early Hinckley)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Cover Triumph's pre-Hinckley Meriden machines and the early Hinckley
modular era — with the whole phase built on what is British-specific,
because the generic vintage topics are already told four times over.

CLI: `motodiag kb list --make triumph`; guard is
`pytest tests/test_phase229_triumph_vintage.py`.

Outputs:
- `known_issues_triumph_vintage.json`
- `tests/test_phase229_triumph_vintage.py`
- Roadmap row 229 corrected as the research dictates
- Documented known-issue count updated (806 → 819)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. This is the most saturated topic in the corpus, and the saturation
has a shape.** Four vintage files hold **40 entries** — Honda, Kawasaki,
Suzuki and Yamaha, ten each — plus `cross_platform_carbs` (10) and
`cross_platform_ignition` (10). Reading their titles together, every
make's vintage file covers the **same ten topics**: cam chain tensioner,
charging system, carburettor rebuild or sync, points ignition, petcock
and tank rust, fork seals, brakes, oil leaks, wiring harness, drive
chain. That is a template, and a Triumph file following it would be the
fifth telling of each.

Worse for a naive approach: `cross_platform_ignition` already owns
"Points ignition maintenance and electronic conversion — vintage bikes",
and its text already names Boyer Bransden **for British twins
specifically**. The single most obvious Triumph-vintage entry is
therefore already written, by another file, with the British case
called out.

**2. But every British-specific term returns zero.** `Whitworth`, `BSF`,
`BSCy`, `positive earth`, `oil-in-frame`, `Amal`, `modular`,
`project code`, `360-degree crank`, `dynamo` — **0 files each**. So the
gap is real and it is precisely the gap a Japanese-vintage corpus would
leave: the things that are different about a British bike rather than
the things that are the same about an old bike.

That gives the phase a hard rule. **Every entry must turn on something
that would make a mechanic trained on 1970s Japanese machines get it
wrong** — thread standards, earth polarity, oil-in-frame, Amal
carburettors, unit versus pre-unit, the 360-degree crank — or on the
Hinckley modular architecture. An entry that could sit in
`honda_vintage` with the badge swapped does not belong here.

**3. The row's own wording needs checking.** Row 229 reads "Classic
British triples, T509/T595, early Hinckley carbureted". Two things to
resolve by research rather than assumption. "Classic British triples"
is ambiguous between Meriden's Trident and Hinckley's modular triples.
And **T509 and T595 are factory project codes, not displacements** — the
T595 Daytona is not a 595. If the row's shorthand invites that reading,
it is the kind of error the last four phases each found.

**4. Boundaries.** 226 owns the Hinckley Bonneville twins from 2001, 227
the Tigers, 228 the Street/Speed Triple and Daytona, 230 electrical and
tooling. The early Hinckley bikes here are the 1991–2004 modular
machines, which is a distinct population from all of those. Phase 227's
Tiger entries already exclude the pre-Hinckley Tiger 900 (T400) by
naming it; this phase may claim it.

**5. Research is capped at 6 agents** — two questions, two adversarial
refuter lenses each — per the standing rule set after Phase 227 and
proven in 228, where the capped run cost 827K subagent tokens and 36
minutes, about half its predecessors, and still corrected two entries I
had written from memory. Progress is reported during the run.

## Logic

1. Research the Meriden-era service differences and the early Hinckley
   modular architecture; accept only what survives both refuters.
2. Write entries that each turn on a British-specific or
   Hinckley-modular fact, and cut any candidate that could be written
   about a Japanese bike of the same age.
3. Validate mechanically: a **genericness assertion** requiring every
   entry to name a British-specific term, with a counter-assertion that
   the existing vintage files score zero against it; deferral
   boundaries; provenance; symptom format.

## Key Concepts

- **The ten-topic template is the enemy.** Four files already follow it.
- **The gap is Britishness, not age.** Zero hits on every British term.
- **Project codes are not displacements** — the T595 trap.
- Claim checks exempt negation both ways (219), reported speech (221),
  comparison (222) and quotation (223), and distinguish mention from use
  in selectors, which has now caught me in ten phases.

## Verification Checklist

- [x] Every entry names a British-specific or Hinckley-modular term, with
      a counter-assertion that the four existing vintage files score zero
- [x] No entry restates one of the ten template topics as its subject
- [x] Project codes are stated as project codes, with actual
      displacements given, and no entry treats T595 as a capacity
- [x] Provenance per entry; `service-manual` entries say what they are
      drawn from, `model-generated` entries carry no sourced figure
- [x] No 226/227/228 content; no DTC or tooling content (230);
      `dtc_codes: []`
- [x] Adapter catalog Triumph rows unchanged at 5
- [x] Row 229 corrected if the research supports it
- [x] Symptom needles quoted from shipped data; no symptom resolves to
      two Triumph files; regression green; F9 clean

## Risks

- **Duplication is the sharpest hazard this phase has faced.** Sixty
  entries already cover old-motorcycle servicing, and the most natural
  Triumph entries are the ones already written.
- **Thread and polarity claims are safety- and damage-relevant** — a
  wrong thread standard rounds off a fastener, a wrong polarity destroys
  a regulator. Both are gated on research with sources.
- **No independent reader** of the final prose, as in 217–228.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 806 → 819 |
| Entries | 13, all `service-manual` |
| Research agents / refuters / died | 2 / 4 / **0** |
| Cost | 661K subagent tokens, 23 min — cheapest run of the block |
| Findings survived / refuted | 1 / 1 |
| Claims removed by refutation | **6** |
| Existing entries scoring on this file's specificity bar | **0 of 60** |
| Phase tests | 48 |
| Backend regression | 5515 passed / 0 failed |

**The audit's real finding was the shape of the saturation, not its
size.** Sixty entries already cover old-motorcycle servicing, but reading
the four vintage files' titles side by side showed they are not sixty
different entries — they are the *same ten topics* written four times.
That reframed the phase entirely. The question stopped being "what is
left to say about old Triumphs" and became "what axis do forty
Japanese-vintage entries not have", and the answer was Britishness:
Whitworth, BSF, Cycle thread, positive earth, oil-in-frame, Amal,
360-degree crank — every one of them zero hits across the corpus.

**The most useful entry is a deduction, not a fault.** On a 360-degree
twin both plugs fire every revolution, so if one cylinder has spark and
the other does not, the fault *cannot* be the ignition module or the
trigger — it must be local to that cylinder. That removes the expensive
part from the list before it is bought, and a shop trained on engines
with independent per-cylinder timing will not make the inference.

**Refutation removed six claims, and one of them was self-contradicting.**
The research asserted Whitworth disappeared after the last pre-units —
while its own cited source documented Whitworth nuts on 1963–67 unit
engines. A refuter that only checked whether sources existed would have
passed it; the one that read them caught it. The others: an inverted seat
height, valve and balancer specifications attributed to a source
containing neither, a recall year range narrower than the regulator's, a
polarity symptom set extrapolated past its source, and the five-speed
framed as retro-only when it also covers the 1994–95 Speed Triple — which
changes a gearbox quote.

**Key finding: when a topic is saturated, the phase's job is to find the
axis the corpus lacks.** Counting entries said the ground was covered.
Reading their titles said it was covered along one axis only.
