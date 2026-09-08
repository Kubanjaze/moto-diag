# Phase 222 — KTM Duke naked line

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Cover the Duke naked line — the small singles through the LC8c parallel
twins — as the second phase of the KTM block.

CLI: `motodiag kb list --make ktm`; guard is
`pytest tests/test_phase222_ktm_duke.py`.

Outputs:
- `known_issues_ktm_duke.json`
- `tests/test_phase222_ktm_duke.py`
- `tests/test_phase221_ktm_1290.py` corrected (a guard I wrote last
  phase breaks the moment the block grows — see below)
- Roadmap rows 222 and 224 corrected
- Documented known-issue count updated (751 → 756)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. A guard I wrote in Phase 221 fails as soon as this phase lands, and
that is my error, not a surprise.** `test_this_is_the_first_ktm_file`
asserts that no `known_issues_ktm_*.json` other than the 1290 file
exists. The intent was "this phase opens the KTM block" — a true and
worth-recording fact. The encoding was "no sibling KTM file may ever
exist", which is a different claim and a wrong one. A guard should
outlive the deliverable it was written for (Phase 220's finding); this
one was written so that it *cannot*. It is rewritten here to assert what
was actually meant: the 1290 file still holds its six entries and its
titles do not collide with a sibling's.

**2. Row 224 does not cover this phase's engine, because the LC8c is not
a V-twin.** Row 224 reads "KTM **LC8 V-twin** common issues". The 790 and
890 Duke use the **LC8c**, a parallel twin — a different engine
architecture that happens to share a family name. So the three topics
224 reserves (cam chain tensioner, electric start, valve clearance
intervals) are reserved *for the V-twin*, and as written row 224 leaves
the Duke twins' engine unowned. Row 224 is annotated rather than
silently assumed either way. This phase still avoids those three topics
on the LC8c, so that whichever way 224 is later scoped, nothing is
written twice.

**3. The 690 Duke falls between two rows.** Row 222's title is "KTM Duke
naked line" but its parenthetical lists only 125/390/790/890. Row 223
covers "enduro / adventure" and names the **690 Enduro R**. The 690 Duke
is a naked road bike, so by body style it belongs here and by
parenthetical it belongs nowhere. The adapter catalog already carries a
`690%` row labelled "690 Duke / Enduro", so the model is known to the
system while being absent from the content roadmap. Row 222 is corrected
to include it; row 223 is annotated to confirm it owns the Enduro R
only.

**4. The duplication picture is milder than Phase 221's but real.** 8
parallel-twin entries and roughly 25 small-displacement entries exist —
`kawasaki_ninja_small` alone holds 9. That is far short of the 19
rider-electronics entries that forced Phase 221 to cut five of eleven
candidates, but it is enough that "small bike needs its valves done" or
"parallel twin charging" would be re-tellings. The backwards genericness
test carries over.

**5. What the corpus cannot already say.** `LC8c`, `LC4`, `Bajaj`,
`crankpin` and `firing interval` are each **zero hits** across 751
entries. The strongest content is therefore architectural and
supply-chain: the LC8c being a parallel twin despite the name, its
offset crankpin being why riders describe V-twin character, the LC4
being shared between a road naked and an enduro, and the 125/390 being
built in India by Bajaj — which is a **parts-sourcing and spec-variation
fact, not a quality claim**, and must be written that way.

**6. "Super Duke" contains "Duke".** A naive `\bDuke\b` check matches
the entire Phase 221 file. Every model assertion in this phase's guard
is anchored to a number (`790 Duke`, `390 Duke`) or explicitly excludes
the `Super ` prefix.

## Logic

1. Draft Duke-line entries and cut any a mechanic could get from the
   existing parallel-twin or small-bike entries.
2. Anchor on what only a Duke entry can say: LC8c architecture, LC4
   sharing, Bajaj manufacture and its parts consequences, and the
   engine-shared/chassis-different pairs.
3. Validate mechanically: distinct-term specificity with a
   counter-assertion, deferral boundaries (221/223/224/225), the
   Super-Duke prefix trap, symptom format, provenance.

## Key Concepts

- **A guard that cannot survive its block growing is a bug.** Fixing
  221's is part of this phase's work, not a footnote.
- **LC8c is a parallel twin.** The name is the trap; the crankpin offset
  is why the trap is convincing.
- **Manufacturing origin is a supply-chain fact.** It is written as
  parts availability and spec variation, never as a quality judgement.
- Claim checks exempt negation in both directions (219) and reported
  speech (221).

## Verification Checklist

- [x] Phase 221's guard rewritten to assert what it meant, and 221's
      suite still passes
- [x] Every entry names Duke-line hardware — distinct terms, with a
      counter-assertion that an existing generic entry **fails** it
- [x] The LC8c is stated to be a parallel twin, and no entry asserts a
      V-twin for the 790/890
- [x] Manufacturing origin framed as sourcing and spec variation, with
      no quality claim — asserted
- [x] No 221 content (1290/Super Duke), no 223 content (EXC/enduro/
      450/500), none of 224's three reserved topics on the LC8c, no 225
      content (ECU/tuning/fault codes); `dtc_codes: []`
- [x] No `\bDuke\b` assertion that "Super Duke" satisfies
- [x] Rows 222 and 224 corrected, row 223 annotated
- [x] Symptom needles quoted from the shipped data
- [x] Regression green; F9 lint clean

## Risks

- **The Bajaj entry is the one that could go wrong.** Manufacturing
  origin is a legitimate diagnostic and sourcing fact and an
  illegitimate proxy for quality. It is written as the former and
  guarded against becoming the latter.
- **Scope creep via the 690.** Taking the 690 Duke is correct by body
  style; taking 690 *Enduro* content is not, and the two share an
  engine, which is exactly how the line gets crossed.
- **No independent reader**, as in 217–221.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 751 → 756 |
| Candidates drafted / shipped | 6 / 5 |
| KTM entries across two files | 11 |
| Roadmap rows corrected / annotated | 1 corrected (222), 2 annotated (223, 224) |
| Phase 221 guards repaired | 1 |
| Validator discrimination cases verified | 11 (4 claims flagged, 7 comparisons and quotations not) |
| Phase tests | 32 |
| Backend regression | 5229 passed / 0 failed |

**A guard I wrote last phase failed the moment this one landed.** Phase
221's `test_this_is_the_first_ktm_file` required that no sibling KTM file
exist. The fact behind it was true; the encoding was not the fact. Phase
220's finding — a guard should outlive the deliverable it was written for
— is exactly what this one violated, one phase after that finding was
recorded. It now asserts what was meant.

**The specificity bar was recalibrated, which is different from lowering
it.** Phase 221's three-distinct-terms rule suits a vocabulary with MSC,
Bosch and Super Adventure in it. The Duke line has none of those, so
entries score two to four on the same count, and dropping the threshold
to fit would have been precisely the failure 221 avoided. Instead the bar
changed shape: a **model or engine designation**, in the **title** as
well as the body. That is stronger against padding than a raw count, and
the corpus's existing parallel-twin entry still scores zero.

**The first draft had no diagnostic content.** Five entries, all
identification or sourcing — an honest reflection of what is
Duke-specific once 223, 224 and 225 take their topics, but a thin shape
for a known-issues file. One entry was cut for restating the others, and
the uneven-firing-beat entry added as the spine.

**Key finding: a validator over prose must exempt comparison, not just
negation and reported speech.** The check flagged "the throttle feel of a
V-twin" as claiming the LC8c is one — the sentence whose whole job is
explaining why an experienced rider gets it wrong. Similes before the
term and attributive uses after it are now exempt, joining negation
(216/219) and reported speech (221). Verified against eleven
discrimination cases rather than only against the shipped file, so the
exemption is known not to neuter the check: "The 790 Duke is a V-twin"
and "the LC8c V-twin makes its torque low down" are both still caught.
