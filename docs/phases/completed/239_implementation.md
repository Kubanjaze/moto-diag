# Phase 239 — European parts sourcing and pricing

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Turn "European parts sourcing + pricing" into things a catalogue can hold:
fiche-verified rows for the makes that had none, cross-references with an
honest rating, and constraints that rest on a document.

Guard: `pytest tests/test_phase239_european_parts.py`.
Outputs: rows in `parts.json` and `parts_xref.json`,
`known_issues_european_parts.json`, its test, roadmap row 239.

## Existing-code audit (Step 0)

**1. The substrate is real and was thin.** `parts.json` (Phase 153) held 62
rows — Honda 14, Harley 11, BMW 6, Triumph 6, Ducati 4, KTM 4 — and **zero**
for Aprilia, MV Agusta and Moto Guzzi. `parts_xref.json` held 83 OEM-to-
aftermarket rows. `parts_sourcing.py` (Phase 166) ranks by rating then cost.
This is the adapter-gap shape Phase 235 filled, on a different table.

**2. "Pricing" was already refuted as generic.** The Phase 237 research's
pricing prose came back "no sourceable per-make pricing structure", so the
question was rewritten to ask only for rows and documented constraints.

**3. Three substrate rules shape every row.** `equivalence_rating` is an
integer 1–5 under a CHECK, not the research's exact/functional/approximate;
every xref must resolve both slugs to existing parts or the loader raises;
and `typical_cost_cents` must be an int — `0` is `add_part`'s own default and
every cost query filters `> 0`, so it is the repo's unpriced sentinel rather
than "free".

## Method

Paired capped 6-agent run with Phase 238. Both refuters refuted this question
on **fitment**: the majority of part numbers checked out against the fiche,
and thirteen corrections were concrete — a pattern that matched the wrong
variant, a cross-reference paired backwards, a belt assigned to the wrong
Scrambler years. Each is pinned individually in the test.

## Results

| Metric | Value |
|--------|-------|
| Parts rows | 62 → 125 (aprilia 0 → 11, mv-agusta 0 → 4, moto-guzzi 0 → 9; bmw 6 → 16, ducati 4 → 17, ktm 4 → 17, triumph 6 → 9) |
| Cross-references | 83 → 100 |
| New categories | 8 — alternator-belt, final-drive-bearing, flywheel, idle-valve, rocker-arm, tappet, timing-belt, vacuum-hose |
| Known issues | 893 → 904 (11 entries) |
| Fitment corrections from refutation | 13, each pinned in the test |
| Structural entries dropped as generic | 3 (MV distribution corporate news) |
| Phase tests | 26 |
| Backend regression | 5872 passed / 0 failed |

**Both refuters refuted on fitment, and fitment is where a catalogue hurts.**
The majority of part numbers checked out against the fiche — the refuters
re-read Aprilia's, MV's, Guzzi's, KTM's, Ducati's and Triumph's pages and
confirmed the numbers, supersessions and VIN splits. What they found wrong
was the kind of error that puts a wrong part on a bike: a KTM rim-band
pattern `1_90%Adventure%` that would have matched the R variants, which take
a different band; a BMW belt cross-reference paired the wrong way round; a
Ducati belt assigned to Scrambler years that are on a different number; a
Hiflo filter given a start year six years late. Each correction is a named
test.

**The BMW belt "disagreement" turned out to have an explanation.** The
research recorded that sources disagree on which Continental designation
matches which BMW belt and declined to pick. A refuter found the answer in
the same owner thread: BMW prints production length, Continental prints
fitted length, so 4PK582 is Continental's 4PK592 (582) and 4PK592 is 4PK611
(592). Two belt generations, overlapping for 2005–07, so the fiche by
production month decides — and the catalogue carries the corrected pairing
at an approximate rating because the source is owner-reproduced.

**Three substrate rules shaped the rows, and one nearly lost fourteen of
them silently.** `equivalence_rating` is an integer under a CHECK; every
xref must resolve both slugs; and cost must be an int. The first loader run
took 111 of 125 rows without error, because the slug was brand+number+category
and several parts have more than one fitment row — `INSERT OR IGNORE` dropped
the rest. Slugs now carry a pattern token on repeat fitments, and the test
loads the file end-to-end and compares counts.

**Cost zero is the repo's own sentinel, and it is used honestly.** `add_part`
defaults to 0 and every cost query filters `> 0`, so an unpriced row is
excluded from ranking rather than read as free. Forty-three rows carry the
fiche's GBP or EUR price in notes and a stated 0. One row had my own
currency error — a fiche GBP figure recorded as cents — caught by the phase's
own no-conversion test.

**A pre-existing duplicate in the seed surfaced.** The original Phase 153
cross-reference file carries one duplicated pair, silently swallowed by the
loader since. It is left as data and detected by the test rather than
papered over; the count assertion now expects exactly that one.

**Eleven constraints, each resting on a document.** The Guzzi tappet kits are
released only against a documented wear claim — the bulletin says "no
preventive operations" — and out-of-warranty supply ran through a help-desk
ticket; the Aprilia V4 has two charging families and the engine-number split
in circulation is an aftermarket claim with no Aprilia document; BMW's
"final drive supplied complete only" is **not established**, bearings carry
their own numbers; no MV rim band could be established and the documented
spoked-wheel remedy is a whole wheel; Triumph's fiche does not itemise the
hoses that fail; KTM's LC8 fiche pages are truncated, so "not listed" is
unknown rather than no-fit. Three MV distribution entries — corporate news —
were flagged generic by both refuters and dropped.

**Key finding: a catalogue row fails at the fitment pattern, not the part
number.** Every part number survived refutation; what needed correcting was
which bikes each row claimed.
