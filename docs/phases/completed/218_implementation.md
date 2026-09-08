# Phase 218 — Ducati Multistrada

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Cover the Multistrada line — 1200 (2010–14), 1200 DVT (2015–17), 1260
(2018–20), V2 (2022+) and V4 (2021+) — hand-drafted in lean mode, with
the same mechanical validation the draft-and-refute pipeline used to
provide.

Two Step 0 findings shape the whole phase, and both are inversions of
rules written in the two phases immediately before it.

CLI: `motodiag kb list --make ducati`; guard is
`pytest tests/test_phase218_ducati_multistrada.py`.

Outputs:
- `known_issues_ducati_multistrada.json`
- `tests/test_phase218_ducati_multistrada.py`
- Roadmap row 219 annotated for the Granturismo exclusion
- Documented known-issue count updated (726 → 726 + N)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. The Multistrada V4 has no desmodromic valves — and that breaks
Phase 219's premise for this bike.** The 2021+ V4 uses the **Granturismo**
engine with conventional **spring valve return**, giving a 60,000 km
(≈37,000 mile) valve interval against roughly 15,000 miles for the
desmo Desmosedici Stradale. Verified by search, not assumed.

Consequences:
- Phase 219 is titled "Ducati desmodromic valve service". **It does not
  apply to the Multistrada V4**, and row 219 is annotated to say so.
- The fact is legitimately *this* phase's content, framed as the
  expectation problem it actually causes — a shop quoting a Ducati
  major service from desmo habit, on a bike that has neither desmo nor
  that interval. Writing the desmo *procedure* remains 219's job; the
  point here is that it is absent.

**2. The cam drive is not uniform within one model line.** The
Multistrada 1200, 1260 and V2 are belt-driven Testastretta engines; the
V4 Granturismo is chain driven. So **neither Phase 216's rule ("Monster
line is belt driven, deny cam chain") nor Phase 217's ("Panigale is
chain driven, deny cam belt") holds across the Multistrada** — both are
true, of different bikes wearing the same model name. The tests here
assert per-generation rather than per-file: a belt claim is only valid
on a 1200/1260/V2 entry, a chain claim only on a V4 entry.

That is the third inversion in three phases and the first where the
correct rule is *conditional* rather than flipped.

**3. Semi-active suspension is saturated — Skyhook would be the
sixth.** Existing: BMW first-generation ESA and ESA II (K-series), DDC
(S1000), Öhlins Smart EC (Panigale, written last phase by me), and the
ZX-10R KECS entry. Every one of them is some version of "the electronic
unit failed or a mode was not set". A sixth telling of that story adds
nothing. A Skyhook entry is only justified if it is about something the
others cannot cover — the *adventure-touring* interaction, where an
electronically preloaded bike must be told it is carrying luggage and a
passenger, which is a Multistrada problem and not a superbike one.

**4. Adventure-touring generics are saturated too**: Honda dualsport,
V-Strom and Yamaha dualsport files already cover loaded-suspension sag,
pannier-rack cracking, screen buffeting, crash protection and chain
wear under touring loads. Nothing generic about riding a big ADV bike
belongs here.

**5. Greenfield for Multistrada content** — no occurrence anywhere in
the knowledge base. Deferrals unchanged: **219** desmo valve service
(where it applies), **220** Marelli ECU, DDA+, Ducati CAN, DDS and all
fault codes (`dtc_codes == []`).

## Logic

1. Hand-draft entries that are Multistrada-specific by construction:
   the Granturismo spring-valve exception; the split cam drive within
   one model name; DVT variable valve timing on the 2015–17 1200; the
   V4's radar hardware; Skyhook only in its load-carrying aspect.
2. Apply the refuters' checks mechanically: could this sentence appear
   unchanged on a V-Strom or an Africa Twin? On another Ducati? On one
   of the five existing electronic-suspension entries? If yes, cut it.
3. Validate: fields, vocabulary, deferrals, **conditional** cam-drive
   claims by generation, symptom format, no title collision with the 22
   existing Ducati entries.

## Key Concepts

- **Conditional guardrails.** 216 and 217 each had a single correct
  rule per file. Here the rule depends on the generation inside the
  file, so the test resolves belt-versus-chain from the entry's own
  model string before judging its claims.
- **Granturismo is the exception that redefines the block**: the first
  Ducati road engine without desmodromic valves, and the reason Phase
  219's title cannot be taken as covering every Ducati.
- **DVT** (Desmodromic Variable Timing, 1200 DVT 2015–17) is desmo
  *plus* variable timing — a third state between the plain desmo of the
  1200 and the spring valves of the V4.
- Symptom strings remain reports, not claims — the Phase 217 lesson;
  claim checks never run on `symptoms`.

## Verification Checklist

- [x] 8 entries; every one `make == "Ducati"`, explicit Multistrada
      model + generation, `source == "model-generated"`, "general
      knowledge" in the description, `dtc_codes == []`
- [x] Cam-drive claims **conditional and correct**: no belt claimed on
      a V4-only entry, no chain on a 1200/1260/V2 entry — resolved per
      entry from its own model string, with a counter-assertion that
      216 and 217 still hold their own rules
- [x] The Granturismo spring-valve exception is stated without writing
      219's desmo procedure
- [x] The Skyhook entry is about load carrying, asserted — not a sixth
      "the electronic unit failed"
- [x] No title collision across the three Ducati files; all load to 30
- [x] Symptom needles quoted from the shipped data
- [x] Row 219 annotated for the Granturismo exclusion
- [x] 22 phase tests; F9 lint clean; regression **5123 / 0**

## Risks

- **No independent reader again.** Lean mode means the adversarial pass
  is replaced by my own checks, which have now been wrong in three
  consecutive phases — always by flagging correct content, never by
  passing something false, but the asymmetry is not a guarantee.
- **Skyhook is the likeliest entry to fail the specificity bar**, and
  should be dropped rather than padded if the load-carrying angle does
  not hold up.
- **Every entry stays tagged `model-generated`**; the CLI warns on each.


## Deviations from Plan

**A latent gate tripped, and the honest fix was not the obvious one.**
The first regression failed `test_phase78_gate2_integration.py::
test_forum_tips_present` — a Gate 2 assertion that ≥90% of known issues
carry a "Forum tip" in their fix procedure. The count was 660/734, or
89.9%.

The obvious fix — add "Forum tip" text to the Track K entries — would
have been **fabricating provenance**. These entries are model-generated;
claiming a forum source is precisely what `known_issues.source` exists
to prevent, and it would have made the corpus dishonest to pass a test.

Measured instead: the forum-sourced population is at **660/660, 100%**,
and the model-generated population at **0/74**. The gate's intent was
never violated; only its denominator changed when Phase 211 introduced
a second provenance class. So the assertion was scoped to the
population it was written about, and a **complementary assertion added**
that model-generated entries must *not* claim forum tips — turning a
weakened test into a stronger, two-sided guarantee.

This has been drifting since Phase 211 and would have tripped on
whichever phase happened to cross 90%. It caught 218 by arithmetic, not
by fault.

**Skyhook survived the specificity bar, narrowly.** With five
electronic-suspension entries already in the corpus — BMW ESA and ESA
II, DDC, Öhlins Smart EC, ZX-10R KECS — a sixth "the unit failed" was
not defensible. The entry that was written is about the *load selection*
on an electronically preloaded adventure bike, which none of the five
can cover, and the test asserts that framing rather than trusting it.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 726 → 734 |
| Multistrada entries | 8 |
| Guardrail form | **conditional** — first in the project |
| Gate corrections | 1 (Gate 2 forum tips, scoped by provenance) |
| Phase tests | 22 |
| Backend regression | 5123 passed / 0 failed |

**Key finding: a guardrail can be conditional rather than global, and a
gate can decay by addition rather than by fault.** Phases 216 and 217
each had one correct cam-drive rule per file; the Multistrada needed one
rule *per entry*, resolved from the bike. And Gate 2 did not break
because anything got worse — it broke because a second, honestly
labelled population of content diluted a ratio that had only ever
described the first. The fix in both cases was to make the rule aware of
what it is actually measuring.
