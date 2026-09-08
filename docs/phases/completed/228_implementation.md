# Phase 228 — Triumph Street Triple / Speed Triple

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Cover Triumph's triple-cylinder sport line — the Street Triple and Speed
Triple nakeds — and settle where the faired Daytona belongs.

CLI: `motodiag kb list --make triumph`; guard is
`pytest tests/test_phase228_triumph_triples.py`.

Outputs:
- `known_issues_triumph_triples.json`
- `tests/test_phase228_triumph_triples.py`
- Roadmap row 228 corrected (the Daytona omission)
- Documented known-issue count updated (795 → 806)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. Zero triple-sport content.** Searching Street Triple, Speed Triple,
Daytona, 675 and 765 across 795 entries returns exactly one hit, and it
is my own boundary sentence in the Tiger file excluding the Speed Triple
1200 from the T-plane claim. So the make-specific ground is empty.

**2. The naked-sport topic is not empty, so the genericness test
stands.** "naked" matches 13 files, MT-09 9, Z900/Z1000 8, GSX-S 7,
Monster 2. The Street and Speed Triple sit squarely in that segment, so
an entry that could have been written about an MT-09 does not belong
here. Designation bar with a corpus-wide counter-assertion, as in 227.

**3. The Daytona has no row, and the adapter catalog already knows
about it.** Row 228's detail reads "Triple naked sport", and the Daytona
675 is a faired supersport — so by the row's own scope it is excluded.
It appears in no other row either: 226 is the Bonneville twins, 227 the
Tigers, 229 the pre-Hinckley and early Hinckley bikes, 230 electrical.
Yet two compat rows already name it ("Daytona 675 + Street Triple 675",
"Street Triple / Daytona 675 CAN"). That is the **fourth consecutive
block-opening row omission** — after the 690 Duke (222), the 790
Bonneville (226) and the Tiger 1050 (227) — and the pattern is now worth
naming in its own right: the roadmap's model lists were written from
model *names*, and every make has a machine whose name does not announce
which list it belongs to.

**4. Boundaries inherited from 227.** Phase 227 established that row
228's "1050" is the Speed Triple 1050, not the Tiger 1050, and that the
Speed Triple 1200 shares the Tiger 1200's 1160cc architecture but **not**
its T-plane crank. Both are load-bearing here and are asserted rather
than assumed.

**5. Row 230 still owns the electrical surface**, including the P0315
crankshaft-position adaption that Phase 227 handed it. The adapter
catalog stays guarded at 5 rows.

**6. Research is capped this phase, after being dropped and
reinstated mid-phase.** The user raised that long unsupervised fan-out is
a real concern — measured at 1.83M subagent tokens (225), 2.07M (226) and
1.55M (227) — chose a ~6-agent cap, then dropped workflows entirely, and
the capped run was stopped mid-flight. Writing began without sources, and
the consequence was immediate and concrete: phases 226 and 227 could
carry **recall campaign numbers, manufacturer publication numbers and
cited service intervals** only because agents opened regulator databases
and handbook PDFs, and an unsourced phase must not invent them. On that
basis workflows were reinstated, capped.

So this file has **mixed provenance, honestly recorded**. Five entries
written before the reinstatement are general-knowledge identification and
cross-reference content and stay `model-generated`; anything the research
establishes ships as `service-manual`. The cap is two research questions
instead of four, keeping two adversarial refuter lenses each, because
refutation is where the value has been — across 226 and 227 it removed
eight claims that would otherwise have shipped, three of which would have
sent a shop to the wrong part or interval.

## Logic

1. Write the general-knowledge layer first — engine sharing between the
   Daytona and Street Triple, model names reused over different engines,
   trim suffixes, and the cross-file boundary with the Tiger 1200 — and
   mark it `model-generated`, which is what it is.
2. Add what the research establishes as `service-manual`, accepting only
   findings that survive both refuters, and let refutation remove claims
   as readily as it adds them.
3. Assert the provenance split holds: no `model-generated` entry may
   carry a recall campaign number, publication number or interval
   figure, because those are exactly what an unsourced entry would be
   tempted to invent.
4. Validate mechanically: designation bar with a corpus-wide
   counter-assertion, deferral boundaries, catalog guarded at 5, symptom
   format.

## Key Concepts

- **Fourth row omission running.** The Daytona's absence is the same
  failure as the 690 Duke's, the 790 Bonneville's and the Tiger 1050's.
- **The naked segment is crowded**; a Triumph entry must name a Triumph.
- **Provenance is per-entry, not per-file.** The split between what was
  known and what was sourced is asserted rather than described.
- Claim checks exempt negation both ways (219), reported speech (221),
  comparison (222) and quotation (223), and distinguish mention from use
  in selectors, which has caught me in eight phases.

## Verification Checklist

- [x] Every entry names a triple-sport designation in title and body,
      with a counter-assertion swept over every non-Triumph file
- [x] Provenance is per-entry and honest: `model-generated` entries open
      with the general-knowledge convention, `service-manual` entries say
      what they are drawn from
- [x] **No `model-generated` entry carries a recall number, publication
      number or interval figure** — asserted by regex, since those are
      what an unsourced entry would be tempted to invent
- [x] The Daytona's scope is stated explicitly, whichever way it lands
- [x] The Speed Triple 1200 is not described as T-plane (the 227
      boundary), and no Tiger or Bonneville content appears
- [x] No DTC or tooling content (230); `dtc_codes: []`
- [x] Adapter catalog Triumph rows unchanged at 5
- [x] Row 228 corrected; the four-omission pattern recorded
- [x] Symptom needles quoted from shipped data; no symptom resolves to
      two Triumph files; regression green; F9 clean

## Risks

- **Duplication with the crowded naked segment** is the sharpest hazard.
- **Fabrication in the unsourced half is the sharpest hazard.** A file
  whose neighbours carry recall numbers is precisely where an invented
  campaign number would look natural in the entries that have no sources
  behind them. A regex asserts none appears there.
- **No independent reader** of the final prose, as in 217–227.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 795 → 806 |
| Entries | 11 — 8 `service-manual`, 3 `model-generated` |
| Research agents / refuters / died | 2 / 4 / **0** |
| Cost after the cap | 827K subagent tokens, 36 min — about half of 225–227 |
| Findings survived / refuted | 1 / 1 |
| **My own entries corrected by research** | **2** |
| Roadmap corrections | 1 (the Daytona had no row) |
| Phase tests | 46 |
| Backend regression | 5467 passed / 0 failed |

**The cap worked and the answer to "do we need this" was settled by
evidence rather than argument.** Research was capped to six agents,
dropped entirely, and reinstated mid-phase. In the gap I wrote five
entries from general knowledge — and when research ran, it contradicted
**two of them**. The Daytona 675 and Street Triple 675 share an engine
only to 2012; from 2013 the Daytona took a bigger bore and shorter
stroke with higher compression while the Street Triple kept the
original, so they are different engines rather than different tunes.
And trim suffixes are not reliably engine-neutral: the 2017–2022 Street
Triple **S** is a 660, not a 765. Both errors would have sent someone to
order the wrong parts, and both were written confidently.

**The provenance split is asserted, not described.** Three entries stay
`model-generated` because that is what they are; eight are
`service-manual`. A test forbids any `model-generated` entry from
carrying a recall campaign number, a manufacturer publication number or
an interval figure — precisely the things an unsourced entry would
invent to look as authoritative as its neighbours.

**Both refuters caught the same misreading, and what survived was more
useful than what was claimed.** The research read a recall form's
*candidate* model list as the affected population; the form's own unit
table shows one model affected and the rest at zero. But the underlying
oddity is real and worse than a wide scope: the regulator's structured
model index for that campaign lists models with **zero** units while
omitting the one that is affected, so a query by model name never
returns it. The entry teaches the frame-number habit rather than the
campaign.

**Key finding: the value of research is in the claims it corrects and
removes, not the ones it adds.** Across 226–228 refutation has removed
ten claims that would otherwise have shipped and corrected two I had
already written. On this phase the corrections came from a run costing
half what its predecessors did.
