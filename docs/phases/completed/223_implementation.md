# Phase 223 — KTM enduro (EXC / EXC-F / 690 Enduro R)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Cover KTM's off-road singles: the two-stroke EXC line, the four-stroke
EXC-F line, and the road-legal 690 Enduro R.

CLI: `motodiag kb list --make ktm`; guard is
`pytest tests/test_phase223_ktm_enduro.py`.

Outputs:
- `known_issues_ktm_enduro.json`
- `tests/test_phase223_ktm_enduro.py`
- Roadmap row 223 corrected (EXC vs EXC-F) and the adventure gap recorded
- Documented known-issue count updated (756 → 762)

## Existing-code audit (Step 0, per CLAUDE.md)

**1. This is the first phase in the KTM block whose gaps are large
rather than narrow.** 221 and 222 both fought duplication. Here the
searches come back empty: `TPI` **0 files**, `transfer port` **0**,
`engine hour` **0**, `hour meter` **0**, `competition` **0**,
`piston replacement` **0**. Across 756 entries the only genuine
two-stroke service content is three RD350/400 entries in
`yamaha_vintage` — oil injection, expansion chambers, reed valves, all
1970s road bikes. **Modern competition two-stroke content does not exist
in this corpus.**

**2. But the off-road *topic* is well covered, so the backwards
genericness test still applies.** Four dual-sport files hold **40
entries** — Honda, Kawasaki, Suzuki, Yamaha, ten each. Those are trail
and dual-sport machines: DR650, KLR, XR, WR. An entry about chain wear
off-road or air filter service would be a re-telling. What those 40
entries cannot describe is a **competition** machine, and that is the
distinction this file is built on.

**3. The row names the four-strokes wrongly.** Row 223 reads
"450/500 EXC". KTM's four-stroke enduros are **EXC-F** — 250, 350, 450
and 500 EXC-F — while plain **EXC** denotes the two-strokes, 250 and 300.
So "450 EXC" and "300 EXC" name engines with different numbers of
strokes, and the row's own shorthand collapses the distinction the
customer-facing naming exists to make. Third naming correction in the
KTM block, after the Super Adventure GT (221) and the LC8c (222).

**4. The adventure half of the row has no content and no home.** Row 223
is titled "KTM enduro / **adventure**", but every model it names is an
enduro single. The **390, 790 and 890 Adventure** appear in no row: 221
took the 1290 Super Adventure, 222 the Duke nakeds, and 224/225 are
engine and electrical rows. Putting a parallel-twin adventure tourer in
the same phase as competition two-strokes would be incoherent, so **this
phase does not take them**. The gap is recorded on the row rather than
silently absorbed or silently left; where it should go is a call worth
making deliberately, and the KTM block as numbered (221–225) has no free
row for it.

**5. What 222 deferred here.** Row 222 wrote only the cross-reference
discipline for the LC4 — cross-reference the engine, not the bike — and
left LC4 content here. Row 224 reserves cam chain tensioner, electric
start and valve clearance for the **LC8 V-twin**; the LC4 is a single
and neither an LC8 nor an LC8c, so those topics are not reserved away
from this phase. They are still approached carefully, because 224's own
scope is an open question.

**6. Interval figures are deferred by test, as in Phase 219.** This is
the phase where that matters most. Competition service intervals vary by
model, by year and above all by how the machine is used, and a
remembered number becomes a wrong quote or, worse, a missed rebuild. No
entry states an hours or mileage figure as fact.

## Logic

1. Build the file on what makes a competition machine different from the
   40 trail-bike entries: service measured in engine hours, top-end work
   as maintenance rather than failure, and a fuel-injected two-stroke.
2. Correct the EXC/EXC-F naming in content as well as in the row.
3. Validate mechanically: designation specificity with a
   counter-assertion against a dual-sport entry, no interval figures, no
   premix claim for TPI bikes, deferral boundaries, symptom format.

## Key Concepts

- **Competition, not trail.** The 40 existing off-road entries describe
  machines meant to last; these describe machines meant to be rebuilt.
- **A TPI two-stroke does not take premix.** It carries an oil tank and
  a pump, and both halves of that — mixing fuel that should not be
  mixed, and never filling the tank that must be — are expensive.
- **EXC is a two-stroke; EXC-F is a four-stroke.** One letter.
- Claim checks exempt negation both ways (219), reported speech (221)
  and comparison (222).

## Verification Checklist

- [x] Every entry names an enduro designation (EXC, EXC-F, TPI, LC4,
      690 Enduro R) in title and body, with a counter-assertion that an
      existing dual-sport entry **fails** it
- [x] No entry states a service interval figure as fact — regex asserted
- [x] No entry says a TPI model takes premix; the oil pump is stated
- [x] EXC and EXC-F are distinguished, and no four-stroke model is
      called a plain EXC
- [x] No 221 content (1290/Super Adventure/MSC), no 222 content
      (Duke nakeds, Bajaj, LC8c), no 224 content on the V-twin, no 225
      content (ECU/tuning); `dtc_codes: []`
- [x] No mid-size Adventure content — the gap is recorded, not taken
- [x] Symptom needles quoted from the shipped data
- [x] Regression green; F9 lint clean

## Risks

- **Interval figures are the sharpest hazard here**, sharper than in
  219, because a missed top-end on a competition two-stroke is an engine
  rather than a wrong quote. Deferred by test.
- **Two-stroke content is new ground for this corpus**, so there is no
  existing entry to check tone or depth against.
- **No independent reader**, as in 217–222.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 756 → 762 |
| KTM entries across three files | 17 |
| Corpus hits before this phase: TPI / transfer port / engine hour / hour meter / competition / piston replacement | **0 each** |
| Existing off-road entries the file must not restate | 40 |
| Dual-sport entries scoring an enduro designation | **0** (counter-assertion runs over two whole files) |
| Roadmap: corrected / flagged open | 1 corrected (EXC-F), 1 gap flagged (mid-size Adventure) |
| Validator discrimination cases verified | 6 |
| Phase tests | 32 |
| Backend regression | 5261 passed / 0 failed |

**The gaps were real for once.** Every phase since 213 has spent its
Step 0 discovering that the topic was already told. Here six searches
returned zero and the only two-stroke service content in the corpus was
three entries about 1970s Yamahas. That does not relax the genericness
test — 40 dual-sport entries still exist — but it changes what the test
is for: not proving an entry is not a re-telling, but proving it
describes a **competition** machine rather than a trail bike.

**The counter-assertion got stronger.** Phases 221 and 222 ran theirs
against one hand-picked entry. This one runs over two entire dual-sport
files, every entry, and requires all of them to score zero. A
counter-assertion that only checks the example you had in mind is
checking your memory rather than the corpus.

**A test caught a content gap rather than a false positive.** The rule
requiring any entry that mentions intervals to point at the manual
failed on the EXC/EXC-F naming entry, which said the two engines want
different intervals without saying where to get them. The content was
fixed rather than the rule loosened — the opposite of the temptation, and
worth recording because six of the last seven validator failures went the
other way.

**A guard with the same defect I had just fixed broke in the same
phase.** Phase 222 repaired a Phase 221 guard that could not survive the
KTM block growing — then wrote `test_they_load_together`, which globs the
KTM files but hardcoded their total at 11. Phase 223 added a third file
and the full regression caught it. Both were the same mistake: a
constant standing in for an invariant. Both KTM coexistence tests now
assert the invariant — loading every KTM file yields exactly the sum of
their entries, with none lost to a collision — plus each file's own
count. Worth recording plainly: fixing an instance of a bug is not the
same as fixing the habit that produces it, and I demonstrated that
within a single phase.

**Key finding: a validator over prose must exempt quotation.** The check
flagged `a request for a top end on a "450 EXC"` — a sentence whose whole
job is naming the error, already marked as a citation by the writer.
After seven phases the exemptions have a shape: negation, reported
speech, comparison and quotation are all ways of **mentioning** a term
rather than **using** it. A check that cannot tell mention from use will
keep failing on exactly the sentences that do the teaching.
