# Phase 219 — Ducati desmodromic valve service

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Write the desmodromic valve service that Phases 216, 217 and 218 all
deferred here. This is a **procedure phase** rather than a failure
phase: the subject is a service most shops quote wrong, price wrong, or
approach with spring-valve assumptions that do not transfer.

CLI: `motodiag kb list --make ducati`; guard is
`pytest tests/test_phase219_ducati_desmo.py`.

Outputs:
- `known_issues_ducati_desmo.json`
- `tests/test_phase219_ducati_desmo.py`
- Roadmap row 219 corrected (terminology — see below)
- Documented known-issue count updated (734 → 734 + N)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. The roadmap row uses the wrong mechanism, and it is the fourth row
error in this block.** Row 219 reads "shim-over-bucket opener/closer".
Verified by search: desmodromic valve gear has **two rocker arms per
valve** — an opening rocker and a closing rocker — and **two shims per
valve**: a small shim on top of the valve stem setting the opening
clearance, and a large shim wrapped around the stem retaining the
collets, setting the closing clearance. **There are no buckets.**
"Shim-over-bucket" describes a spring-valve arrangement, which is what
the *other* 22 valve entries in this corpus cover. The row is corrected
at close-out to "opening and closing rockers, opening and closing shims,
retaining collets".

**2. This phase's justification is the contrast, and it is strong.**
The corpus holds **22 valve-clearance entries** across Honda, Kawasaki,
Suzuki and Yamaha — every one of them a spring-valve engine, several
explicitly "shim-under-bucket". None describes a desmodromic system.
Twice the rockers, twice the shims, no springs and a closing clearance
that has no analogue is not a variation on those entries; it is a
different mechanism. The genericness risk that killed Phase 213
therefore runs the other way here: the danger is writing a *generic
valve-clearance* entry, not a Ducati one.

**3. Scope, inherited from three phases.** In scope: Desmodue (2V
air-cooled), Desmoquattro, Testastretta including the 11° and DVT
variants, Superquadro, and Desmosedici Stradale. **Out of scope: the
Multistrada V4's Granturismo**, which uses conventional spring valve
return — established in Phase 218 and already annotated on the row.
That exclusion is asserted by test here.

**4. What the earlier phases explicitly left.** 216 deferred desmo
intervals, opener/closer shims, closer wear symptoms and rocker
condition. 217 deferred the same plus the Panigale's interval figure
surfaced during its audit. 218 established the Granturismo exclusion.
Cam belts stayed in 216/218 and are **not** re-written here — a desmo
service and a belt service often coincide in the workshop, and saying
so is legitimate, but the belt procedure itself is already written.

**5. Deferral out.** Phase **220** still owns Marelli ECU, DDA+, Ducati
CAN, DDS and every fault code; `dtc_codes` stays `[]`.

## Logic

1. Hand-draft entries covering: what the mechanism actually is and why
   spring-valve assumptions fail; the two clearances and why both are
   measured; collet and closing-shim handling, where the real risk sits;
   shim sizing and parts lead time, which is what strands a bike
   mid-service; the cost and interval question that drives most customer
   conversations; and the 2V-versus-4V differences in access and effort.
2. Every entry must fail the reverse test: could this appear unchanged
   in one of the 22 spring-valve entries? If yes, cut it.
3. Figures deferred to the manual throughout. Interval figures vary by
   generation by a factor of two or more, and quoting a remembered
   number is exactly the error the phase is about.

## Key Concepts

- **Two rockers, two shims, no springs, no buckets.** The opening shim
  sits on the valve stem; the closing shim wraps the stem and retains
  the collets.
- **The closing clearance has no analogue** in a spring-valve engine,
  which is why a competent shim-under-bucket mechanic can still get a
  desmo service wrong.
- **The service is labour-dominated**, and shim availability rather
  than shim cost is what determines whether the bike moves this week.
- Symptom strings remain reports, not claims (Phase 217 lesson); claim
  checks never run on `symptoms`.

## Verification Checklist

- [x] 6 entries; every one `make == "Ducati"`, `source ==
      "model-generated"`, "general knowledge" in the description,
      `dtc_codes == []`
- [x] **No entry claims a bucket** — asserted with bidirectional
      negation and a named-system exemption, plus a counter-assertion
      that the spring-valve files still use the term
- [x] The Granturismo exclusion is stated and asserted
- [x] Every entry names desmodromic hardware (opening/closing rocker,
      opening/closing shim, collet, half-ring) — the reverse of Phase
      213's genericness test
- [x] **No interval figure stated as fact** — asserted by regex; the
      interval entry defers to the manual
- [x] No cam-belt procedure re-written; the collet entry is rated
      `critical`
- [x] All four Ducati files load to 36, no title collision
- [x] Row 219 terminology corrected
- [x] 22 phase tests; F9 lint clean; regression **5145 / 0**

## Risks

- **No independent reader**, as in 217 and 218. The mechanical checks
  encode what the refuters looked for, and my own checks have been
  wrong in three consecutive phases — always by flagging correct
  content, never by passing something false, but that asymmetry is
  observed rather than guaranteed.
- **Interval figures are the sharpest hazard in this phase**, because a
  wrong number becomes a wrong quote. Every interval is deferred to the
  manual, and the entries say why a remembered figure is unsafe.
- **Every entry stays tagged `model-generated`**; the CLI warns on each.


## Deviations from Plan

**The roadmap named a mechanism this engine does not have, and that is
the fourth row correction in the Ducati block.** Row 219 read
"shim-over-bucket opener/closer". Verified: desmodromic valve gear uses
two rocker arms per valve and two shims — a small opening shim on the
stem, a large closing shim retaining the collets — and **no buckets at
all**. "Shim-over-bucket" is a spring-valve arrangement, which is what
the corpus's other 22 valve entries describe. Corrected at close-out.

**The genericness test runs backwards in this phase.** Phase 213 lost
12 of 18 candidates because litre-bike content was already told six
times. Here the corpus's 22 valve-clearance entries are *all*
spring-valve, several explicitly "shim-under-bucket", so the risk is
writing one of those with a Ducati badge. The test therefore requires
every entry to **name desmodromic hardware** rather than forbidding a
shared topic.

**My validator was wrong for the fourth consecutive phase**, and this
time in two new ways. It flagged "shim-under-bucket" — a *proper name*
for the contrasting design, not a claim this engine has a bucket — and
it flagged "the Multistrada V4's Granturismo **is not** [desmodromic]",
because the negation *follows* the term and the check only looked
backwards. Both are now handled: negation is checked in both
directions, and named-system compounds are exempt. The pattern across
216–219 is consistent: every false positive has been the sentence that
proves the content correct.

**Intervals are deferred by test, not just by intention.** A regex
assertion fails any entry stating a mileage figure as fact, because a
wrong interval becomes a wrong quote — the specific harm this phase
exists to prevent.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 734 → 740 |
| Desmo entries | 6 |
| Roadmap corrections in the Ducati block | 4 |
| Consecutive phases where my validator produced false positives | 4 |
| Phase tests | 22 |
| Backend regression | 5145 passed / 0 failed |

**Key finding: the check needs to model how language actually works, not
just which words appear.** Four phases of false positives have all been
the same mistake in different clothes — a term negated before it, a term
negated after it, a term inside a compound proper noun, a term in a
symptom that reports someone else's error. Each time the content was
right and the rule was too literal. A validator over prose has to
distinguish assertion from reference, and negation can arrive from
either side.
