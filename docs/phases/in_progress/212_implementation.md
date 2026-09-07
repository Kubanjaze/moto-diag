# Phase 212 — BMW GS adventure line (F-series)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Cover the chain-driven BMW adventure line — F650GS single and twin,
F700GS, F800GS, F750GS, F850GS, F900GS — plus the ADV-accessory
failures specific to BMW's CAN-bus electrics. Every entry is authored
as model-generated, tagged so in the JSON and in its own description,
and — new for this phase — **drafted by independent authors and
adversarially refuted before it is accepted**. Content that will carry a
"needs mechanic review" label deserves more than one pass before it is
written down.

CLI: `motodiag kb list --make bmw`, `motodiag kb show <id>`; the guard
is `pytest tests/test_phase212_bmw_gs_adventure.py`.

Outputs:
- `src/motodiag/knowledge/seed/knowledge/known_issues_bmw_f_series_gs.json`
  — ~12 entries, each `source: "model-generated"`
- A widened Phase 211 fuel-strip entry (see audit item 3)
- `tests/test_phase212_bmw_gs_adventure.py`
- Corrected roadmap row text (see audit item 1)
- Documented known-issue count updated (672 → 672 + N)

## Existing-code audit (Step 0, per CLAUDE.md)

Run as a four-agent workflow: one overlap reader across the whole seed,
two **independent** premise checkers (one asked to confirm the roadmap
row, one asked to refute the opposite claim), and one contract reader
over the Phase 211 tests. Findings:

**1. The roadmap row is factually wrong, and both checkers agreed
without seeing each other.** Row 212 reads "…paralever final drive".
Every F-series GS — F650GS single (2000–2007), F650GS twin (2008–2012),
F700GS, F800GS (2008–2018 and 2024+), F750GS, F850GS, F900GS — is
**chain-driven** with a conventional double-sided swingarm. Paralever is
the shaft-drive torque-reaction swingarm on the boxer R-series and the
K-series; it has never been fitted to an F. The claim is cross-
contamination from the R-series GS row. Consequence: the twelve Phase
211 entries are almost entirely boxer/shaft/dry-clutch hardware with
**no F-series analogue** — final drive bearing, Paralever pivots,
input-shaft splines, dry-clutch seal contamination, belt alternator,
Hall sensor plate, servo Integral ABS, diode board, brushed rotor. None
of it ports. The row text is corrected at close-out.

**2. Naming traps that would put an entry on the wrong bike.**
"F650GS" is two unrelated machines: a 652 cc Rotax single (2000–2007,
chain on the *right* side, continued as the G650GS to 2016) and a
798 cc parallel twin (2008–2012, a detuned F800GS). "F800GS" is likewise
two: 798 cc (2008–2018) and 895 cc (2024+). No twin's displacement
matches its name. Belt-driven F800S/ST/GT are not GS models. Every
entry in this phase carries an explicit model string and year range;
none says bare "GS".

**3. One genuine overlap, to be widened rather than duplicated.**
Phase 211's fuel-level strip-sensor entry is scoped to `R1200GS
2007–2012`, but the same resistive strip and the same erratic-gauge
failure apply to the F800GS / F650GS-twin family. Rather than a second
entry, this phase widens the 211 entry's model and description. The
211 test asserts on `make="BMW"` and titles, not model strings, so it
survives.

**4. What the F-series may legitimately add** over existing cross-
platform coverage: the Rotax 652 water-pump seal *and shaft* failure
with its right-side-cover access (weep-hole diagnosis is already
covered twice and must not be restated); the Rotax starter sprag as a
model-specific parts/access entry (the mechanism is already covered);
F-specific surging/hesitation citing the BMS-C/BMS-K ECU and its
idle-actuator, **not** the generic lean-map story that four other
entries already tell; and the BMW CAN-bus accessory problem — no fuse
box, non-CAN accessories rejected — which is distinct from the generic
charging-budget entries.

**5. Reserved.** Dealer/diagnostic mode, fault-code reading and GS-911
belong to Phase 215 and are not written here.

**6. Contract** (from the 211 tests): fourteen fields including
`source`; severity ∈ {critical, high, medium, low}; `source ==
"model-generated"` on every record and in the JSON itself; the phrase
"general knowledge" in every description; `make == "BMW"` on every
record; the file named `known_issues_*.json` under the seed dir; and
the count guard, which will fail four docs the moment N entries land
until each says `672 + N`.

## Logic

1. **Draft** — six independent author agents, one per lens (F650GS
   single/Rotax; 798 cc twins F650GS/F700GS/F800GS; 853 cc F750/F850GS;
   895 cc F900GS/new F800GS; ADV accessories & CAN-bus; chassis/wheels/
   ABS across the line), each given the avoid-list and the contract,
   each returning candidate entries as structured output with a
   self-assessed confidence and a list of any numeric figures it used.
2. **Dedup** — plain code, by normalised title, against the 211 titles
   and across drafts.
3. **Verify** — every candidate faces three refuters with distinct
   lenses: *attribution* (wrong model, wrong years, R-series hardware
   ported to an F, F650GS single/twin confusion); *invented figures*
   (any specific voltage, torque, interval or price that a mechanic
   would treat as a spec — the rule is omit, not guess); *safety and
   procedure* (would following it damage the bike or hurt someone;
   is the fix ordered sensibly). Each refuter is told to default to
   refuted when uncertain. An entry survives only if at most one
   refuter refutes it **and** the safety refuter does not.
4. **Synthesize** — one agent assembles survivors into the final JSON,
   enforcing the contract mechanically (fields, severity vocabulary,
   `source`, the admission phrase, explicit model strings) and capping
   at the strongest ~12.
5. **I write the files** — the JSON, the widened 211 entry, the test,
   the doc-count update — and run the regression. Agents return data;
   nothing in the workflow touches the working tree.

## Key Concepts

- **Adversarial verify, perspective-diverse**: three refuters with
  different lenses rather than three identical ones, because an entry
  can be wrong in three different ways and redundancy catches only one.
- **Default-to-refuted**: refuters are instructed that uncertainty is a
  refutation. The cost of dropping a true entry is a thinner file; the
  cost of keeping a false one is a mechanic following it.
- **Figures are omitted, not guessed**: the invented-figures refuter
  exists because "50–70 VAC per leg" reads as authority whether or not
  it is right.
- `pipeline()` over candidates so verification of one entry does not
  wait on the drafting of another; a single barrier before dedup,
  because dedup genuinely needs the full set.
- The same test shape as Phase 211, plus one assertion the workflow
  makes possible: every entry's `model` string names a specific F/G
  model — none is bare "GS".

## Verification Checklist

- [x] The content workflow ran 3 refuters per candidate under the
      survival rule: **17 drafted → 17 after dedup → 14 survived → 12
      kept** (synthesizer cap), **0 undecided**
- [x] The three drops are recorded with reasons below, not silently lost
- [x] Every entry: `make == "BMW"`, an explicit F/G model string, a
      generation marker on the ambiguous F650GS/F800GS badges,
      `source == "model-generated"`, "general knowledge" in the
      description, no bare "GS" — all asserted
- [x] No R-series-only component (Paralever, crown wheel, dry clutch,
      diode board, slip ring, alternator belt, cardan, Telelever,
      input-shaft spline, final drive housing) appears anywhere in the
      F-series file — asserted per term, with a counter-assertion that
      the term *does* still exist in the R-series file so the check is
      meaningful
- [x] No entry restates a topic on the avoid-list; the widened
      fuel-strip entry is not duplicated (asserted)
- [x] The 211 fuel-strip entry is widened to the F800 family — a
      four-line diff, and Phase 211's tests still pass
- [x] Symptoms normalised from sentences to short phrases, since
      `find_issues_by_symptom` is a SQL LIKE match and a sentence never
      matches a mechanic's query; four real queries asserted to hit
- [x] Both BMW files load together to 24 entries
- [x] The count guard fired on 672 → 684 and all four docs updated
- [x] Roadmap row 212 corrected at close-out: chain, not Paralever
- [x] 34 phase tests; F9 lint clean; backend regression green

## Risks

- **The refuters are also models.** Three model-generated opinions
  about a model-generated entry are not a service manual. What the
  process buys is consistency and the removal of the obviously wrong;
  it does not make the survivors true. The tag stays.
- **Default-to-refuted will drop some real failures.** That is the
  intended direction of error. The phase log lists what was dropped so
  a mechanic can reinstate anything they know to be real.
- **Widening the 211 entry edits Phase 211 content after close.** It is
  a scope correction to an existing model string, not a rewrite, and
  the 211 tests are re-run to prove nothing else moved.


## Deviations from Plan

**The first content run reported 0 survivors, and it was meaningless.**
45 of 57 agents died on a session limit, and my aggregation treated a
`null` verdict as `{refuted: true, problem: 'fatal'}` — so an outage
masqueraded as unanimous adversarial refutation and killed every
candidate. That is a real defect in the harness, not the content. Fixed
before the retry: a dead refuter is retried once, then **excluded from
the vote**; fewer than two real verdicts yields `undecided`, reported
rather than dropped. The resumed run replayed the six drafters from
cache and returned 58/58 agents with **0 undecided**.

**The refuters earned their keep.** Three drops, each for a distinct
reason the lens was built to catch:

1. **Fuel pump controller (FPC) on the 798cc twins — fatal, two lenses.**
   Attribution: a discrete potted FPC module is Hexhead R1200 and
   K1200/K1300 hardware; the 798cc F-twins run BMS-K/KP driving the
   in-tank pump through an ECU-controlled relay. The entry sent a
   mechanic hunting a part the bike does not have, and cited a recall
   campaign never run against those VINs — *exactly* the R-series-onto-F
   port this phase existed to prevent, and it slipped past a drafter
   that had the avoid-list in front of it. Safety independently rated it
   fatal: step 5 applied a heat gun beside an under-seat fuel tank whose
   flange the entry itself described as prone to weeping.
2. **Rotax 652 water-pump seal — dropped on figures and safety.**
   `figures_used` was empty while the text carried an unsourced 3.5-hour
   estimate; safety flagged draining coolant with no cold-engine
   instruction on a pressurised system.
3. **F800GS fork seals — dropped on figures and safety**, same shape:
   undeclared specification-grade figures.

**Two more cut at synthesis** to fit the cap of 12: a near-duplicate
rear-wheel-bearing entry (the weaker of two), and an accessory-socket
entry that documented normal ZFE behaviour rather than a fault.

**Symptom normalisation was not in the plan.** The drafters returned
symptoms as full sentences (mean 85 characters). `find_issues_by_symptom`
is a SQL `LIKE '%needle%'` match, so a sentence is unsearchable — a
mechanic typing "chain slap" would never reach the entry. Rewritten to
the short phrases the rest of the corpus uses (mean 22 characters), with
a safety caution that had been misfiled in a symptoms array moved into
the fix procedure. This is a format correction; no substance changed.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 672 → 684 |
| F-series entries | 12 (2 single-cylinder, 7 F800GS, 3 F750/F850GS) |
| Drafted → deduped → survived → kept | 17 → 17 → 14 → 12 |
| Undecided (harness failures) | 0, after the fix |
| Refuter verdicts collected | 51 |
| Phase tests | 34 |
| Backend regression | 4964 passed / 0 failed |
| Roadmap row corrected | "paralever final drive" → chain |

**Key finding: the adversarial pass caught a factual error the
avoid-list did not prevent.** The FPC entry was drafted by an agent
holding an explicit instruction not to port R-series hardware onto an F,
and it did so anyway — convincingly, with correct model strings and
years, which is precisely what makes that class of error dangerous. One
drafting pass would have shipped it. What killed it was a second agent
whose only job was to disbelieve the first.

The second finding is about the harness rather than the bikes: a
verification rule that cannot distinguish "the refuter disagreed" from
"the refuter died" will report a confident zero. Any survival rule needs
an explicit undecided state.
