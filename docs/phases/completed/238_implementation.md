# Phase 238 — European valve service intervals, compared across makes

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-08

## Goal

Job types and intervals side by side across the European makes, from
manufacturer documents only — and the two items earlier phases deferred here.

Guard: `pytest tests/test_phase238_european_intervals.py`.
Outputs: `known_issues_european_intervals.json`, its test, a correction to
one Phase 225B entry, roadmap row 238.

## Existing-code audit (Step 0)

**1. Per-make files already print some intervals.** BMW, Ducati, KTM, Triumph,
Aprilia and MV each have 1–3 files mentioning valves, and several print a
figure. This phase owns the comparison and the deferred items, and where it
prints a figure, the figure carries its document.

**2. Two deferrals name this phase.** Phase 234 could not establish the MV F4
shim diameter and refused to pick; Phase 225B deliberately printed no KTM
interval and deferred the Adventure-versus-Duke difference here.

**3. The corpus carries a false sibling claim, and it is mine.** Phase 225B's
entry says the 390 Adventure schedules its valve check at a shorter interval
than the 390 Duke. Its refuter had compared a 373cc Adventure against a 399cc
Duke. On one engine the two agree. This phase corrects the entry.

## Method

Paired capped 6-agent run with Phase 239. Both refuters refuted narrowly.
The source lens re-downloaded ten manufacturer PDFs, **MD5-matched** them to
the finding's copies and re-read every schedule table visually — every
interval survived. The contradiction lens found six MV maintenance manuals
already on disk that the finding had not opened, and in them the one
manufacturer-documented same-engine differing pair.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 904 → 917 (13 entries) |
| Provenance | 12 `service-manual`, 1 `model-generated` |
| Manufacturer documents read visually | 5 BMW Rider's Manuals + dealer sheet, 11 KTM manuals + service-times sheet, Ducati poster + Multistrada sheet + model pages, 7 Triumph handbooks + 2006 sheet, 6 MV maintenance manuals + workshop manual + TSB, Guzzi V85/V100 manuals |
| Refuter verdicts | 2 refuted, both narrowly |
| Shipped claim corrected in an earlier phase | 1 (Phase 225B) |
| Deferrals closed | 2 (234's F3 figure; 225B's sibling question) — 1 confirmed open (234's F4 shim diameter) |
| Phase tests | 24 |
| Backend regression | 5898 passed / 0 failed |

**This is the best-sourced phase in the block, and a refuter proved it.** The
source lens re-downloaded ten manufacturer PDFs, **MD5-matched** them to the
copies the finding had used, re-rendered every schedule table and read the
dot columns visually. Every BMW, KTM, Ducati, Triumph and Guzzi interval
survived. Every figure printed here carries its document by name, and a
test requires it.

**The sibling test has one documented exception, and the finding had said
there were none.** On KTM, Ducati and Triumph, siblings on one engine carry
one interval in the manufacturer's tables. The finding concluded no
same-engine pair differs anywhere. The contradiction lens found **six MV
Agusta maintenance manuals already on disk**, downloaded hours earlier by a
previous agent and never opened: the 798cc triple at **12,000 km** on the
Brutale 800, Dragster RR and Rivale, and **30,000 km** on the Turismo Veloce
and F3, in overlapping model years. The difference tracks MV's move from a
6,000 km coupon ladder to a 15,000 km one, applied model by model. That is
exactly the "primary source could not be obtained" claim the standing
warnings say will be checked — and it was on the machine the whole time.

**I shipped a false sibling claim at 225B, and this phase corrects it.**
225B's entry said the 390 Adventure schedules its valve check at a shorter
interval than the 390 Duke. Its refuter had compared a 373cc Adventure
against a 399cc Duke; on one engine the two agree, in eleven KTM manuals.
The corrected 225B entry keeps what was true — the dusty-conditions
qualifier, the Adventure-only rows, the generation change — states the
correction, and **prints no figures**, because 238 owns them. My first
correction put the figures in and 225B's own boundary test caught it.

**Two figures the research attributed to documents were misread.** MV's
coupon table has a merged first cell — coupon A spans both the running-in
and the annual column — and the finding had shifted every letter by one,
which sends a mechanic to the wrong coupon. Ducati's poster has three group
layouts and the finding quoted one group's oil-service column as a range
for all; Group 3 has no such column. Both are entries now, because both are
errors a shop makes at the bench.

**The two deferrals resolve asymmetrically.** Phase 234's F3 interval is
now confirmed at 30,000 km from the MY2020 maintenance manual. Phase 234's
F4 shim diameter is still in no manufacturer document — the workshop manual
gives the clearances and sends pad replacement to an engine manual not
obtained — so the measure-first rule stands, with the 7.48 mm owner figure
labelled as an owner report.

**Job types carry their provenance.** Desmo, cams-out shim, screw-and-locknut
and rocker-and-shim are named from manufacturer manuals where the manual
describes the method, and labelled "by owner report" where it does not —
the BMW boxers and KTM. The Ducati tool rows the research proposed are not
in the parts catalogue: only one number was confirmed and its fitment
exceeded the cited source.

**A sixth copy of the designation-bar guard, and the reason three sweeps
missed it.** Phase 237 found five copies and I called that the set. A sixth
fired here, in Phase 226, because my sweeps had matched on the test's *name*
— and this one is `test_no_other_makes_parallel_twin_entries_score`, not
`test_no_other_makes_entry_scores`. The sweep that found it matched on
**shape**: every test that globs the knowledge directory and skips by
filename. That search returns exactly six, and confirms Phase 221's
title-collision test is not one of them — it globs `known_issues_ktm_*`
only, so a European file never enters it. Same lesson as Phase 235's audit,
one turn later: an identifier-keyed search finds one phase's habits, and only
a shape-keyed one finds the invariant.

**Key finding: the primary source may already be on disk.** The finding's
one confident negative — no same-engine differing pair exists — was
overturned by documents a previous agent had downloaded to the same
scratchpad and no one had opened.
