# Phase 216 — Ducati Monster / Streetfighter (V-twin)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Open the Ducati block with the Monster line (1993→) and the V-twin
Streetfighters (1098/S 2009–13, 848 2012–15), drafted by independent
lenses and adversarially refuted before acceptance. The Ducati block
inherits the BMW block's deferral structure: **valve service belongs to
Phase 219, electrical/ECU/DDS to Phase 220**, so this phase writes
neither and its tests assert both.

The verification risk inverts *again*, and in the direction opposite to
Phase 214. Three BMW entries describe dry-clutch failures; a refuter
that learned "dry clutch is boxer hardware" would kill every correct
Ducati entry. Ducati's dry clutch is an exposed multi-plate stack behind
a vented cover with its own failure modes — basket-finger notching,
plate-ear hammering, slave-seal weep — and the famous idle rattle is
*normal*. The attribution refuter is briefed on that explicitly; the
duplication refuter polices the BMW seam.

CLI: `motodiag kb list --make ducati`; guard is
`pytest tests/test_phase216_ducati_monster.py`.

Outputs:
- `src/motodiag/knowledge/seed/knowledge/known_issues_ducati_monster.json`
- `tests/test_phase216_ducati_monster.py`
- Roadmap row 216 corrected at close-out; a note for row 217 that the
  Streetfighter V4 lands there
- Documented known-issue count updated (704 → 704 + N)

## Existing-code audit (Step 0, per CLAUDE.md)

Run as a four-agent workflow: overlap reader, two independent premise
checkers (confirm / refute), contract reader. 4 agents, 0 errors.

**1. The roadmap row is wrong, and both checkers agreed without seeing
each other.** Row 216 reads "…trellis frame, Testastretta evolution".
- **No trellis on the current Monster.** The 2021+ Monster (937) uses
  a cast-aluminium Panigale-style Front Frame bolted to the heads, and
  the 890 V2 Monster continues with aluminium — the first Monsters
  since 1993 without a trellis. Trellis is correct 1993–2020 only, in
  three sub-variants (classic 851-derived; hybrid with cast rear
  subframe on 696/796/1100; short trellis bolted to the Testastretta on
  821/1200).
- **"Testastretta evolution" does not cover the air-cooled line at
  all.** Every 2-valve Monster (M600/750/900, 620/695/800/1000/1100,
  696/796/797) is a Desmodue. And the liquid-cooled S4 (916) and early
  S4R (996) are **Desmoquattro**, not Testastretta — an entry saying
  "Monster Testastretta" before 2007 is wrong.
- **The Streetfighter V4 (2020+) is out of scope for this row.** It is
  a 1103 Desmosedici Stradale V4 on the Panigale V4's aluminium Front
  Frame with the Panigale's electronics; it shares nothing mechanical
  with a V-twin Monster. The refuting checker "failed on every axis" to
  place it here. **It belongs to Phase 217**, and the roadmap row is
  annotated so 217 picks it up.

**2. Completely greenfield for content.** No Ducati entry exists; the
only `ducati`/`desmo` grep hits are passing mentions in two Kawasaki
files. Eight Ducati adapter compat rows already exist (Monster and
Panigale CAN, plus the dealer DDS tool) — those belong to Phase 220's
surface and are untouched here.

**3. The dry-clutch seam with BMW is the duplication risk, and the
inverse of a foreign-hardware risk.** The overlap reader drew the line
precisely: the BMW entries are about a boxer *single-plate* dry clutch
contaminated by seal leaks, diagnosed at a bellhousing weep hole and
repaired via an 8–12 h engine/gearbox split, or about spline-sliding
hubs. The Ducati dry clutch is an *exposed multi-plate stack* in an
aluminium basket behind a vented cover, actuated by a hydraulic slave on
the left case: its failures are basket-finger and plate-ear wear, warped
steels, slave-seal weep (fluid, external, onto the sprocket cover), and
the plate stack comes out through the cover in under an hour. The idle
rattle that stops when the lever is pulled is **normal**, not a spline
symptom. A Ducati entry has to say those things, and must not re-tell
the BMW contamination story.

**4. Generation and clutch traps recorded** (from the checkers): S4R
(996 Desmoquattro, 2003–06) vs S4R Testastretta (998, 2007–08) vs S4RS;
695 vs 696 (different engines *and* frames); 796 vs 797 vs 795 (all
803 cc, three different bikes); 1100 dry clutch vs 1100 EVO **wet**
APTC clutch; Streetfighter 1098 dry vs 848 wet. Displacement badges lie
throughout (900 = 904 cc, 1000 = 992 cc, 796/797/800 = 803 cc). Every
entry must name a specific model and generation, and state dry or wet
where the clutch is involved.

**5. Deferrals, from the contract reader.** To **219**: desmo service
intervals and cost, opener/closer shims and clearances, closer-shim
wear symptoms, rocker chrome flaking, anything whose fix is "check
valve clearances". To **220**: Marelli ECU internals and mapping,
DDA+, Ducati CAN format, DDS tool and adapter rows, any Ducati fault
code (`dtc_codes` stays `[]`, exactly as 212–214 did for 215),
reg/rec and stator as an electrical category, TPS reset via tool.
**Cam belts are in scope here**: row 219 lists intervals, shims and
cost — not belts — and belt age, tensioner bearings and the
fixed-by-years replacement rule are a Monster-line failure mode. The
entry is written for belt-driven twins generally so Phase 218
(Multistrada) can reference rather than duplicate it.

**6. Contract** unchanged from 211–215 (`source: model-generated` in
the JSON, "general knowledge" in every description, symptoms as short
LIKE-searchable phrases, count guard), with `make == "Ducati"` and a
1993 year floor.

## Logic

1. **Draft** — seven lenses: air-cooled 2V Monsters 1993–2008
   (M900/600/750, 620/695/800/1000, S2R); liquid-cooled Desmoquattro
   S4/S4R/S4RS; 696/796/1100 hybrid-frame generation incl. 1100 EVO;
   821/1200 Testastretta 2014–21; Monster 937 (2021+) and 797;
   Streetfighter 1098/S/848; the dry clutch and hydraulic slave as a
   subject (briefed with the BMW seam explicitly).
2. **Dedup** — plain code against the 44 BMW titles and across drafts.
3. **Verify** — three refuters, each defaulting to refuted:
   - *attribution*: wrong generation (Desmoquattro vs Testastretta,
     695/696, 796/797, dry vs wet by year), Streetfighter V4 leakage,
     bare "Monster"; **told outright that dry clutches, desmo valve
     gear, cam belts and trellis frames are legitimate Ducati
     hardware**; generic naked-bike advice relabelled.
   - *duplication + deferral + figures*: restating the three BMW
     dry-clutch entries or the cross-platform wet-clutch/chain/charging
     entries; writing 219's valve service or 220's electrical/ECU
     content; invented figures or fault codes.
   - *safety and procedure*: cam-belt work (a snapped belt bends
     valves — engine must not be turned with belts off without locking
     tools), open dry-clutch covers (rotating exposed parts), hydraulic
     fluid on chain/brakes, hot rear cylinder, bike support.
4. **Synthesize** with fixable notes applied; cap 12; empty
   generations left absent and named.
5. **I write the files** and run the regression.

## Key Concepts

- **The guardrail inverts against the previous block, not the previous
  phase.** 214 relaxed "Paralever is an error" because the K has one.
  216 relaxes "dry clutch is BMW hardware" because Ducati's is
  different hardware with the same name — the seam is *mechanism*, and
  the duplication refuter is briefed on the exact distinguishing facts.
- **Deferral structure mirrors the BMW block**: 216–218 write model
  content with `dtc_codes: []`; 219 owns valve service; 220 owns
  electrical, ECU, DDS and codes — and the count guard, `undecided`
  state and symptom-in-schema rule all carry forward unchanged.
- **Precedence hazard carried from 215**: no DTC rows here, so no
  shadowing risk this phase; recorded so 220 remembers it.

## Verification Checklist

- [ ] Workflow ran 3 refuters per candidate; drafted / survived / kept
      and every drop reason recorded; zero undecided or all reported
- [ ] Every entry: `make == "Ducati"`, explicit model + generation,
      `source == "model-generated"`, "general knowledge" in description,
      `dtc_codes == []`
- [ ] No entry restates a BMW dry-clutch title; any Ducati dry-clutch
      entry describes the multi-plate exposed stack, not seal
      contamination or spline wear — asserted on title and text
- [ ] No Desmoquattro-era S4/S4R entry says "Testastretta"; no entry
      puts a trellis on a 2021+ Monster; no Streetfighter V4 — asserted
- [ ] No valve-service (219) or ECU/DDS/reg-rec (220) entry — asserted
      on titles
- [ ] Symptoms are short searchable phrases; real needles from the
      shipped data hit
- [ ] Roadmap row 216 corrected; row 217 annotated for the SF V4
- [ ] Count guard fires; four docs updated
- [ ] Backend regression green; F9 lint clean

## Risks

- **A refuter that over-learns the BMW seam will kill correct Ducati
  dry-clutch entries; one that under-learns it will pass a BMW retell
  with a Ducati badge.** Two lenses split the job — attribution permits
  the hardware, duplication polices the mechanism — and the tests
  assert both directions.
- **The Monster line is thirty years and a dozen distinct engines**;
  the naming traps are dense enough that a generic-but-true entry is
  the likeliest failure, as in 213. Expect drops; record empty
  generations rather than pad.
- **Three model-generated refuters are not a service manual.** Every
  entry stays tagged and the CLI warns on each.
