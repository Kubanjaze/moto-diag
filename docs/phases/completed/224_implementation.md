# Phase 224 — KTM engine families (LC8 / LC8c / LC4)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Be KTM's cross-engine file — the analogue of `honda_cross_model` and
`yamaha_crossmodel` — and settle the LC8c scope question Phase 222
raised.

CLI: `motodiag kb list --make ktm`; guard is
`pytest tests/test_phase224_ktm_engines.py`.

Outputs:
- `known_issues_ktm_engines.json`
- `tests/test_phase224_ktm_engines.py`
- Roadmap row 224 rescoped (decision recorded below)
- Documented known-issue count updated (762 → 766)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. The row's entire stated content is already written, and not
narrowly.** Row 224 reserves *cam chain tensioner*, *electric start
issues* and *valve clearance intervals*. Across 762 entries those topics
appear in **37**, **23** and **26** entries respectively — and the
procedures already exist in generic form: `cross_platform_starting` holds
starter relay, starter motor brush and **starter clutch (sprag/one-way
bearing)** entries, genuinely cross-platform; `honda_cross_model` and
`yamaha_crossmodel` hold cam chain tensioner and valve clearance entries
with `model: "All"` — make-scoped files, but the method in them is
engine-generic. A KTM cam chain tensioner entry would be the
thirty-eighth on that topic. **This phase does not write any of the
three.**

**2. But the row is structurally right, once read correctly.** Honda and
Yamaha each have a **cross-model file** that owns their make's universal
engine topics. Row 224 is KTM's, and KTM has something those makes do
not: **three engine architectures under two prefixes** — LC8 (75-degree
V-twin), LC8c (parallel twin) and LC4 (large single). That is the
content this file can carry that no cross-platform entry can.

**3. Decision on the LC8c scope question Phase 222 raised.** 222 found
that row 224 said "LC8 **V-twin**" while the 790/890 use the LC8c, a
parallel twin, leaving that engine unowned. **Decision: widen the row to
the KTM engine families** rather than keep it V-twin-only. Three reasons.
The three reserved topics are already covered thirty-odd times over, so a
V-twin-only phase would have almost nothing to write. The corpus's own
precedent is a per-make cross-engine file. And the block as numbered
(221–225) has no free row for an LC8c one, so V-twin-only leaves an
engine in four shipped models permanently unowned. Recorded on the row so
it is visible and reversible rather than inferred from a file name.

**4. What I do not know, and will not write.** Honda's cross-model entry
can say the inline-four cam chain tensioner is a documented make-wide
weakness because it is. I have no equivalent confident knowledge of an
LC8-specific tensioner, starter or valve failure pattern, and inventing
one would be fabrication wearing the costume of specificity — the exact
failure the `model-generated` provenance discipline exists to prevent.
The absence of those entries here is deliberate.

**5. So this is a small phase, and that is the honest outcome.** Four
entries: the engine family map, generation span within the LC8, cylinder
identification on a vee, and where the three universal topics actually
get diagnosed. Phase 220 shipped two surfaces instead of three for the
same kind of reason.

**6. Boundaries with 222 and 223.** 222 wrote "the LC8c is a parallel
twin, do not order V-twin parts" — an **architecture** point. This file's
nearest entry is about **generation** within the LC8, which 222 does not
touch. 223 wrote service counted in engine hours for competition
machines; this file does not restate schedules, only which family
determines which schedule.

## Logic

1. Write the family and generation content only a KTM cross-engine file
   can carry.
2. Route the three reserved topics to the cross-platform entries that
   already own them, and say what KTM actually changes about them.
3. Validate mechanically: no cam chain tensioner / starter / valve
   failure claims, every entry names an engine prefix, no restatement of
   222's architecture point, symptom format, provenance.

## Key Concepts

- **The row was right; its Notes were already written elsewhere.**
- **Three architectures, two prefixes.** LC8 and LC8c differ by a letter
  and by everything else; LC4 is a single.
- **Not knowing is a result.** No LC8-specific tensioner, starter or
  valve pattern is asserted, because I do not have one to assert.
- Claim checks exempt negation both ways (219), reported speech (221),
  comparison (222) and quotation (223).

## Verification Checklist

- [x] No entry claims an LC8-specific cam chain tensioner, starter or
      valve clearance failure pattern — asserted
- [x] The cross-platform entries that own those topics still exist —
      counter-assertion, so the routing is not pointing at nothing
- [x] Every entry names an engine prefix (LC8, LC8c, LC4) in title and
      body, with a counter-assertion that a cross-platform entry fails it
- [x] The LC8/LC8c architecture point is not restated from Phase 222
- [x] No cylinder numbering asserted that I cannot support — the entry
      directs to the manual instead
- [x] No 225 content (ECU/tuning/fault codes); `dtc_codes: []`
- [x] Row 224 rescoped with the decision recorded
- [x] KTM coexistence asserted as an invariant, not a constant (the
      Phase 223 lesson)
- [x] Regression green; F9 lint clean

## Risks

- **The temptation to fill the row as written** is the main hazard. Three
  named topics and an empty file invite writing them; they are already
  written thirty-odd times.
- **Overlap with Phase 222** on engine naming is close enough to need
  asserting, not just intending.
- **No independent reader**, as in 217–223.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 762 → 766 |
| KTM entries across four files | 21 |
| Reserved topics written here | **0 of 3** — already covered 37 / 23 / 26 times |
| KTM-specific failure claims about those topics | **0** — asserted |
| Scope decision | Row widened from LC8 V-twin to KTM engine families; recorded on the row |
| Corpus-claim corrected in content | 1 (cross-platform vs cross-model) |
| Phase tests | 25 |
| Backend regression | 5286 passed / 0 failed |

**The row was structurally right and its Notes were already written.**
Honda and Yamaha each have a cross-model file owning their universal
engine topics. Row 224 is KTM's — but the three topics its Notes named
were already told 37, 23 and 26 times, with the procedures in generic
form. So the file carries what only a KTM cross-engine file can:
architecture map, generation span, cylinder identification, routing.

**Not knowing is recorded as a result.** No LC8-specific tensioner,
starter or valve failure pattern is asserted, because I do not have one
to assert. The absence is a test, not an intention — `FAILURE_CLAIM`
fails on any sentence pairing a KTM prefix with one of the three topics
and a failure word.

**A factual claim about the corpus was wrong in the first draft, and the
check that caught it was a manual re-verification rather than a test.**
The routing entry said all three procedures were cross-platform. Only
the starter ones are; CCT and valve clearance live in Honda and Yamaha
cross-*model* files. The plan's Step 0 had made the same overstatement.
Both corrected, and a test now requires the entry to draw the
distinction. An entry that describes the corpus has to be checked
against the corpus, not against memory of the corpus.

**Key finding: a row can be structurally right while its stated content
is already written — and the honest deliverable is small.** Four entries.
Phase 220 shipped two surfaces instead of three; this ships four entries
where the row implied a dozen, for the same reason. The temptation was to
fill the row as written; the thirty-eighth cam chain tensioner entry
would have satisfied the roadmap and helped no one.
