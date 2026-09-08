# Phase 230 — Triumph electrical + tooling

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Close the Triumph block: the fault-code surface that 226–229 deferred
here, the adapter-catalog gap 226 left, the TuneBoy/TuneECU naming
question, and the P0315 finding Phase 227 handed over.

Direct analogue of 215 (BMW), 220 (Ducati) and 225 (KTM). Inherits their
governing constraint — **a wrong fault code is worse than a missing
one**, and a make-specific row that restates the generic row **hides**
it.

CLI: `motodiag code <dtc>`, `motodiag kb list --make triumph`; guard is
`pytest tests/test_phase230_triumph_electrical.py`.

Outputs (three surfaces, as in 225):
- `src/motodiag/knowledge/seed/dtc_codes/triumph.json`
- `known_issues_triumph_electrical.json`
- `adapters.json` + `compat_matrix.json`, if the research establishes a
  Triumph-capable tool with real provenance
- `tests/test_phase230_triumph_electrical.py`
- Roadmap row 230 corrected; Triumph block summary
- Documented known-issue count updated (819 → 824)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. This row carries three explicit inheritances, all recorded on it by
earlier phases.** That is new — no previous closing phase arrived with a
written brief from its predecessors.

- **The adapter gap (from 226).** Five Triumph compat rows, none
  `full`, and the only Bonneville row is `obdlink-lx` on `bonneville%`
  **2016–2025** — so the air-cooled 2001–2015 Bonneville, the subject of
  eleven entries in this corpus, has **no adapter row at all**. 226
  guarded the count at 5 and left it here.
- **The naming question (from 225 via 226).** This row's title says
  *TuneBoy* while its own notes say *TuneECU*. Phase 225 established
  these are different products, and that for KTM only TuneECU does
  diagnostics. For Triumph the answer may differ — TuneBoy's own site
  lists Triumph — so it is being researched rather than carried across.
- **P0315 (from 227).** A refuter surfaced *Crankshaft Position System
  Variation Not Learned*: a Euro 5 adaption that stores a code and
  lights the MIL if never performed, and which reportedly **cannot be
  cleared with the normal Erase DTCs function**. 227 declined to write
  it because it was out of scope there. It is verified here before
  being written, not carried on trust.

**2. There is no Triumph DTC file.** The seed holds generic, BMW,
Ducati, Harley and KTM. Every Triumph row written here shadows a generic
row and must earn it — the finding that made 215 drop P0135 and shaped
220 and 225.

**3. What 226–229 deferred, by test.** All four forbid
`P0xxx | P1xxx | C1xxx | TuneECU | TuneBoy | dealer mode` and keep
`dtc_codes: []`. That is this phase's entire inbound scope, and those
four test files are the fence: nothing written here may make them fail.

**4. What already exists in Triumph terms and must not be restated.**
The block holds **46 entries** across four files. 227 already says the
liquid-cooled 1200 throttle balance requires the dealer tool; 229 already
covers Meriden-era electrical polarity. So the read-access entry here
cannot be the generic point — it has to be the Triumph tool landscape
and the code format.

**5. Cylinder numbering is the sharpest DTC question, and the block has
a precedent for refusing it.** 220's strongest content was Ducati L-twin
cylinder identity, settled from KTM's own manual in 225; 224 declined to
assert KTM numbering because it could not be supported. A Triumph
misfire row naming the physical cylinder on an inline triple is worth
having **only if research settles it with a source** — otherwise the row
is not written.

**6. Research is capped at 6 agents** — two questions, two refuter
lenses each — per the standing rule, which in 228 and 229 cost 827K and
661K subagent tokens against 1.5–2.1M before it. Progress is reported
during the run.

## Logic

1. Research the tool landscape and the code format; accept only findings
   that survive both refuters, and verify P0315 rather than inheriting
   it on trust.
2. Write DTC rows only where a Triumph-specific cause or fix is
   established, each against the generic row it shadows.
3. Write knowledge entries on the tool landscape, the code format and
   dash behaviour, and the adaptation requirements.
4. Fill the adapter gap only with real provenance in `verified_by`; the
   226–229 guards at 5 rows are then updated deliberately, as 225 did
   for KTM.
5. Validate against 215/220/225's checks plus the 226–229 fence.

## Key Concepts

- **A closing phase with a written brief.** Three inheritances, each
  verified rather than assumed.
- **Earning the shadow** — from 215, 220 and 225.
- **Refuse the cylinder numbering unless sourced** — the 224 precedent.
- Claim checks exempt negation both ways (219), reported speech (221),
  comparison (222) and quotation (223), and distinguish mention from use
  in selectors, which has caught me in ten phases.

## Verification Checklist

- [x] Every DTC row standard format; no invented P1xxx; no Triumph
      proprietary number transcribed
- [x] Every shadowing row differs from the generic row in causes **and**
      fix, with a counter-assertion that at least one genuinely shadows
- [x] `motodiag code` resolves the Triumph row for a Triumph and generic
      for another make — verified live
- [x] P0315 written only as research verified it, including whether the
      erase-function claim holds; if unverified, said so or omitted
- [x] No cylinder numbering asserted unless sourced; if asserted,
      guarded against self-contradiction (the 220 regex)
- [x] TuneBoy/TuneECU resolved from research for **Triumph
      specifically**, not carried across from the KTM answer
- [x] Adapter records match a peer's schema; compat rows Triumph-only;
      `verified_by` real; the air-cooled Bonneville gap addressed or its
      absence explained; 226–229 row-count guards updated deliberately
- [x] Nothing here makes tests 226–229 fail
- [x] Symptom needles quoted from shipped data; no symptom resolves to
      two Triumph files; regression green; F9 clean; block summary written

## Risks

- **Fabricated codes and a fabricated adapter record** are the sharpest
  hazards. Both are gated on research with sources.
- **Inherited claims are the subtler hazard.** P0315 arrives with a
  provenance chain one refuter long, and a claim that has been written
  down twice can feel established without being verified. It is checked
  here.
- **No independent reader** of the final prose, as in 217–229.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 819 → 824 |
| DTC rows | 7 (4 shadowing, all differing) |
| Adapters / compat rows added | 2 / 17 — Triumph rows 5 → 22 |
| Inheritances discharged | 3 of 3 (adapter gap, naming question, P0315) |
| Research agents / refuters / died | 2 / 4 / **0** |
| Cost | 760K subagent tokens, 25 min |
| Earlier-phase guards inverted | 4 (226–229 row counts) |
| Phase tests | 42 |
| Backend regression | 5558 passed / 0 failed |

**A closing phase with a written brief, and all three inheritances
changed on contact.** The adapter gap turned out to need *two* answers,
not one: the injected air-cooled Bonneville gets coverage, and the
carburetted machines get an explicit `incompatible` row because they
have no engine control module at all. That distinction is the whole
value — an absent row implies missing tooling, and the truth is that no
tool can exist. The naming question inverted the KTM answer rather than
inheriting it: TuneBoy is only an editor on KTM and is not only that on
Triumph. And P0315 held completely, verified verbatim in Triumph's own
bulletins by a refuter who re-downloaded them.

**The cylinder numbering came with an exception, which is why it was
worth researching rather than assuming.** Triumph's specification tables
give "Left to Right" for the transverse triples — but the Rocket 3's
longitudinal triple is "Front to back, 1 at front". A misfire row written
from the first fact alone is actively wrong on that model, and Phase 224
had already established the discipline of refusing a numbering that
cannot be supported.

**The best knowledge entry is one nobody would look for.** Triumph's
workshop manual specifies lamp behaviour per code, and the pattern is
consistent: flashing for identity and security mismatches, steady for
ordinary faults. So the lamp itself narrows the search before a tool is
connected, and a flashing lamp is a provenance conversation rather than
a sensor one.

**Key finding: an inherited claim is not a verified one.** P0315 arrived
recorded on the roadmap by a previous phase, on one refuter's word. It
would have been easy to write it as established — it had, after all,
already been written down twice. It was checked again, and it held; the
point is that holding was the outcome rather than the assumption.
