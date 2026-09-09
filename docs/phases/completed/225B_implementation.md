# Phase 225B — KTM mid-size Adventure line (390 / 790 / 890 Adventure)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Close the open item the KTM block left behind at Phase 225 and has carried
through ten phases: the mid-size Adventure line has no roadmap row and no
content.

Guard: `pytest tests/test_phase225b_ktm_adventure.py`.
Outputs: `known_issues_ktm_adventure.json`, its test, roadmap row 225B,
implementation.md row.

## Existing-code audit (Step 0)

**1. The gap is real, and larger than "no roadmap row" suggested.** The string
`Super Adventure` appears 25 times across the seed — all of it the 1290, which
Phase 221 owns. `390 Adventure`, `790 Adventure` and `890 Adventure` appear
**zero times in 855 entries**. So this is not a tracking omission with content
behind it; there is no content.

**2. The engine is already covered, twice.** Phase 222 owns the 790/890 Duke
parallel twin and the 390 single; Phase 224 owns the LC8c engine family in the
abstract. Writing engine-internal content here would shadow both. The axis
that is genuinely uncovered is **everything around the engine** — the tank,
subframe, suspension, wheels and bodywork that make an Adventure a different
machine from the naked bike it shares an engine with.

**3. Two existing guards define the boundary from the other side.** Phase
221's `test_no_other_ktm_model_lines` forbids `125|390|690|790|890|450|500` in
the 1290 file, and Phase 222's `test_no_1290_specific_systems_or_models`
forbids `Super Duke|Super Adventure|MSC|MTC` in the Duke file. Neither
constrains this phase, but both establish the pattern this phase must follow:
assert the boundary from both sides.

**4. The naming trap is live and is the reason the gap persisted.** "Super
Adventure" (1290, Phase 221) and "Adventure" (390/790/890, uncovered) differ
by one word, and a corpus search for `Adventure` returns 25 confident hits
that are all the wrong machine. That is how this stayed open for ten phases,
and it is worth an entry in its own right.

## Method

One capped 6-agent run (2 questions × 2 refuter lenses), the cadence held
since 227. Questions ask explicitly for what is *not* shared with the Duke
siblings, and carry the standing warnings on phantom recall numbers,
cross-contamination and unconfirmable figures.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 855 → 865 |
| Entries | 10 — 9 `service-manual`, 1 `forum` |
| Research runs | 1 capped 6-agent run (6/6 returned) |
| Refuter verdicts | 3 refuted, 1 clean |
| Corrections forced by refutation | 5 |
| Phase tests | 31 |
| Backend regression | 5791 passed / 0 failed |

**A refutation turned "could not be determined" into a sourced fact.** The
research reported the 890 Adventure's assembly location as unresolvable and
graded its own confidence Low. A refuter opened the exact KTM page the finding
had cited as unhelpful and found all three 890 Adventure variants listed under
the Mattighofen production heading — and, on the same page, KTM's own
statement that the CFMoto partnership covers the 790 Duke and 790 Adventure.
So the two machines sitting side by side in the showroom come from different
plants, which is the part a parts counter needs.

**The opposite correction on the same topic.** The research cited a
manufacturer-partner press release for an assembly claim about the 2025 390
platform. The page contains no occurrence of the plant name, the models named,
or any production word at all — it is an unveiling and pre-booking
announcement. That entry now records the 2025 build location as **not
established**, and a test asserts that it stays that way. Two corrections in
opposite directions on one subject: one absence filled, one confident claim
withdrawn.

**The tyre campaign is narrower than it reads, and the difference is money.**
The manufacturer's own owner notification restricts it on these models to the
**front** tyre, and only to machines still wearing the originally fitted
tyres. Quoting a pair, or quoting it at all on a machine on its second set,
is wrong in a way the customer notices.

**A regulator declared unqueryable answered on the first attempt.** The
research recorded Canadian campaigns as unverifiable; a refuter queried
Transport Canada and returned both 790 brake campaigns. That is the third time
in this block regulator access has been the weak link rather than the data —
after the national index defect at 228 and the misspelled make at 231 — so the
entry routes the reader to check more than one national database and says
plainly that a clean result in one is not a clean result.

**The subframe entry exists to refuse a reputation.** KTM subframe cracking is
widely repeated and belongs to the earlier 950/990 generation; nothing found
supports it on these machines. What replaces the folklore is two things the
catalogue and manual do say: the subframe is a **bolt-on two-piece assembly**
with left, right and rear-reinforcement parts listed separately, so
single-sided crash damage is not a frame job; and the manual's **5 kg luggage
rack plate limit**, which most top-box installations exceed before anything
goes in the box.

**The gap survived ten phases because of one word.** `Super Adventure` appears
25 times in the corpus and is all 1290; `390/790/890 Adventure` appeared zero
times in 855 entries. A search for "Adventure" returns confident hits that are
all the wrong machine — which is why this is an entry in its own right rather
than only a fix.

**The phase deliberately prints no service-interval figures.** Phase 238 owns
European valve intervals across makes. This phase owns the narrower claim that
the Adventure and its Duke sibling do not share a schedule — including a
dusty-conditions qualifier on the Adventure air filter row that the Duke's
schedule lacks — and sends the reader to the machine's own manual for numbers.
A test enforces the boundary, scoped to mileages used *as* an interval so that
an owner reporting when a part failed is not caught by it.

**Key finding: a model line can be invisible because of its name.** This gap
was not an oversight of judgement; every search that would have revealed it
returned confident, plausible, wrong results. The corpus said "Adventure" 25
times and meant a different motorcycle every time.
