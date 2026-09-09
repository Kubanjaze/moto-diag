# Track K — the contradictions dimension, re-run uncapped

Produced at Phase 240B, 2026-09-09, in answer to the warning
`TRACK_K_AUDIT_DEBT.md` records against itself:

> The contradictions auditor reported finding **16** cross-phase
> contradictions. The workflow submitted only the first **8** for
> verification — the script capped each dimension at `findings.slice(0, 8)`
> — and 6 of those 8 were confirmed. **Eight contradictions were therefore
> never verified and are not listed below.** Section A is the confirmed
> subset, not the full set.

**The corpus is not clean.** The uncapped re-run returns **27 contradictions
and 13 uncertain findings**, against the original run's 6 confirmed. The cap
did not trim a tail; it hid the majority of the dimension.

## Method

The original audit script lived in the workflow journal, not the repo, so it
could not be re-executed. The dimension was re-run as a fresh adversarial
sweep over the same corpus — 30 Track K knowledge files (257 entries), the 8
DTC files, the adapter and parts catalogues — partitioned six ways so that no
slice hit a cap:

| slice | scope |
|---|---|
| 1 | BMW cluster vs the four cross-make files |
| 2 | Ducati cluster vs the four cross-make files |
| 3 | KTM cluster vs the four cross-make files |
| 4 | Triumph cluster vs the four cross-make files |
| 5 | Aprilia + MV Agusta cluster vs the four cross-make files |
| 6 | the four cross-make files against each other and the catalogues |

Every finding was required to carry verbatim quotes from both sides, a
same-subject argument, the operative cost, a reachability trace through the
real retrieval predicate, and a recorded kill attempt. The already-adjudicated
findings — the six confirmed and the two rejected — were excluded by name.

## Verification status — read this before acting on anything below

The failure that produced this debt was reporting 16 findings and verifying 8.
This document does not repeat it silently. Findings are marked:

- **[VERIFIED]** — reproduced independently against the tree during this
  phase, quote by quote.
- **[REPORTED]** — surfaced by the sweep with evidence and a kill attempt, but
  **not** independently re-verified. Roughly 60% of the original audit's
  findings did not survive verification. Treat these as candidates, not facts.

**Nothing in Part 2 or Part 3 was fixed at Phase 240B.** That phase fixed the
six section A contradictions, the guard defects B1–B5 and the section C rule.
Widening it to a corpus-wide content rewrite would have meant abbreviating the
care each entry gets, which the working agreement forbids.

---

# Part 1 — The structural findings: why this keeps happening

The original audit diagnosed the cause as a documentation habit — "the
correction was recorded only in the new file". That is true but shallow. Three
retrieval defects mean the corrective cross-make files are systematically
outranked or unreachable relative to the per-make entries they were written to
correct. **All six sweep slices found S1 independently.**

### S1 [VERIFIED] — severity sorts backwards; `critical` comes back last

`src/motodiag/knowledge/issues_repo.py` orders by `severity DESC` on a TEXT
column. SQLite sorts that lexicographically:

```
ORDER BY severity DESC -> ['medium', 'low', 'high', 'critical']
```

`medium` outranks `critical` on every knowledge-search path — line 119
(`search_known_issues`), line 154 (`find_issues_by_symptom`), line 164
(`find_issues_by_dtc`).

It is a defect, not a design choice: three other modules in the same repo map
severity to a rank correctly.

| module | pattern |
|---|---|
| `shop/issue_repo.py:440` | `ORDER BY CASE i.severity WHEN 'critical' THEN 4 …` |
| `engine/correlation.py:436` | `severity_order = {"critical": 4, "high": 3, …}` |
| `advanced/predictor.py:821` | `severity_rank = {…}` |

`knowledge/issues_repo.py` is the lone outlier. **Blast radius: 73 test files
assert on `results[0]`.** Fixing it reorders every knowledge search result
corpus-wide and needs its own phase and its own regression.

### S2 [VERIFIED] — three entries are unreachable from any make-filtered lookup

`issues_repo.py:84-86` builds `AND make LIKE ?` with `f"%{make}%"` against the
verbatim `make` string, so an entry whose make reads "All European makes"
matches nothing. Exactly three of 257 Track K entries:

| entry | `make` |
|---|---|
| `known_issues_european_intervals.json[4]` | `'All European makes'` |
| `known_issues_european_tooling.json[5]` | `'All European makes'` |
| `known_issues_european_tooling.json[12]` | `'All makes'` |

**This changed the Phase 240B fix for contradiction A5.** `intervals[4]` is the
entry that wrongly places KTM in the shim-under-bucket column — and it is one
of the three. Correcting its text does nothing for a `make="KTM"` lookup. The
A5 fix is only effective because it also edits `intervals[6]` (make `'KTM'`,
reachable). The verifier had recommended the second site for consistency; the
real reason is stronger.

Recommended repair: enumerate the makes in those three `make` fields. Cheap and
count-neutral, but it changes make-filtered result sets and must land with a
check of every pinned make-count.

### S3 [VERIFIED] — corrections filed under a make that cannot reach them

`known_issues_european_tooling.json[2]` is titled *"TuneECU's capability
degrades differently on KTM and Triumph"* and carries `make: 'KTM'`. Its
Triumph half — that the tool can write a map but not read one, so a
calibration cannot be backed up before a remap — is invisible to every
Triumph query. Its KTM half **was** back-propagated, into
`known_issues_ktm_electrical.json[1]`; the Triumph half was carried nowhere.
`tooling[1]`, which makes a claim about "every other marque", carries
`make: 'Ducati'`.

### S4 [VERIFIED] — the same entry is the only answer past its evidence

`european_tooling[2]` runs to `year_end` **2026** while every corroborating
row stops at 2020. For MY2021+ it is the **only** TuneECU entry a KTM query
returns:

```
make=KTM year=2016 term='TuneECU'  -> 4 rows
make=KTM year=2021 term='TuneECU'  -> 1 row  (european_tooling[2])
make=KTM year=2023 term='TuneECU'  -> 1 row  (european_tooling[2])
```

It tells a shop the tool diagnoses these machines. `ktm_electrical[1]` — out of
range — says TuneECU covers "no Euro 5 model" at all.

### S5 [VERIFIED] — two machine-readable service intervals are wrong

`src/motodiag/advanced/data/service_interval_templates.json`. `scheduler.next_due`
reads `every_miles` and `every_months` only — it never reads `notes`, so the
caveats in these rows are unreachable by the code that schedules the work.

```json
{"make": "ducati", "model_pattern": "%", "item_slug": "valve-check",
 "description": "Desmodromic valve service", "every_miles": 7500, ...}
{"make": "ktm", "model_pattern": "690%", "item_slug": "valve-check",
 "every_miles": 15000, ...}
```

The Ducati row is `model_pattern: "%"` with no year bound — every Ducati,
including the spring-valve V4 Granturismo (60,000 km) and 890 V2 (45,000 km),
booked for a "Desmodromic valve service" five times more often than Ducati
requires. The KTM row stores 15,000 **miles** where every KTM valve figure in
the corpus is in kilometres; the sibling rows in the same file convert
correctly, which is what makes this look like an unconverted figure.

These sit in `advanced/data/`, outside Track K — the same boundary section D
of the first debt document draws around `recalls.json`.

---

# Part 2 — New contradictions (27)

## BMW slice

| # | contradiction | files | status |
|---|---|---|---|
| N1 | Eight 16-pin-only adapters rated as covering 2013+ R1200GS and F-series, on bikes that kept the round 10-pin connector until 2016–17. The GS-911 rows in the same file carry the caveat; the generic-adapter rows do not, and `status: "full"` is the machine-readable field. | `bmw_electrical[2]` vs `compat_matrix.json` (8 rows) | [REPORTED] |
| N2 | Which hexhead final-drive bearing fails, and whether one can be ordered. The per-make entry names the crown-wheel bearing in title, causes and parts list; the corrected entry and the catalogue both point at the outer wheel-side bearing, and the catalogue records that **no BMW number is confirmed** for the crown-wheel one. Distinct from the adjudicated A2 pairing, which is about lubrication generation. | `bmw_r_series[0]` vs `european_parts[3]`, `parts.json` | [REPORTED] |

## Ducati slice

| # | contradiction | files | status |
|---|---|---|---|
| N3 | Multistrada V2 asserted desmodromic through 2026 against the 2025 890 V2 spring-valve engine. Overlapping years; the wrong entry is `medium` and therefore the top hit under S1. | `ducati_multistrada[0]` vs `european_intervals[11]` | **[VERIFIED]** |
| N4 | Multistrada V2 asserted belt-driven through 2026 against the chain-drive 890 V2 — and `parts_needed` names "Cam belts and tensioner/idler bearings on 1200/1260/V2", an orderable part that does not exist for that engine. | `ducati_multistrada[1]` vs `european_intervals[11]`, `[4]` | **[VERIFIED]** |
| N5 | `ducati_desmo[0]` names the Granturismo as the sole non-desmo Ducati road engine; the 890 V2 is a second. This gates the whole desmo procedure set. | `ducati_desmo[0]` vs `european_intervals[11]` | [REPORTED] |
| N6 | A legislated OBD-II layer assumed from 2001, on machines the tooling file says carry a proprietary 3-pin plug. Survives either reading of the Euro 4/5 dispute — 2001 is 15–20 years early on both. | `ducati_electrical[0]` vs `european_tooling[10]` | [REPORTED] |
| N7 | The Panigale V4's structural member is the airbox monocoque in one entry and an aluminium front-frame in another. `parts_needed` names "Monocoque airbox/frame assembly". | `ducati_panigale[1]` vs `[7]` | [REPORTED] |

## KTM slice

| # | contradiction | files | status |
|---|---|---|---|
| N8 | TuneECU needs two different KTM 6-pin adaptors (C for K-Line, D for CAN); the KTM file sells it as one universal adaptor plus a choice of interface cable. `compat_matrix` rows 115–122 record the split by protocol. | `european_tooling[10]` vs `ktm_electrical[1]` | [REPORTED] |
| N9 | For MY2021–2026 the only reachable TuneECU answer says the tool diagnoses these machines; the corpus elsewhere says Euro 5 KTMs are not supported at all. See S4. | `european_tooling[2]` vs `ktm_electrical[1]` | **[VERIFIED]** |
| N10 | Clearance drift on a 690 LC4: one entry says diagnose generically and adjust, the other says adjusting is the wrong repair because the rocker bearing is wearing. Distinct from the adjudicated A5, which is about valve-train *type*. | `ktm_engines[3]` vs `european_differentials[7]` | [REPORTED] |
| N11 | The LC8 starter clutch has a bulletin-backed KTM-specific failure; `ktm_engines[3]` tells the shop no such make-specific mechanism exists. The `critical` correction sorts last under S1. | `ktm_engines[3]` vs `european_differentials[4]` | [REPORTED] |

## Triumph slice

| # | contradiction | files | status |
|---|---|---|---|
| N12 | Air-cooled T100/Thruxton valve interval: 12,000 vs 20,000 miles — and the entry carrying the correct split names no model, so it is **not returned at all** for `model='Thruxton'` or `'T100'`. The entry's own prose agrees; its `model` field, `causes[1]` and `year_start` are what assert the wrong thing, and those are the fields retrieval keys on. | `european_intervals[7]` vs `triumph_bonneville[7]` | **[VERIFIED]** |
| N13 | TuneECU on newer CAN-bus Triumphs: "no read" vs "map read and write". The correction is filed under `make: 'KTM'`. See S3. | `european_tooling[2]` vs `triumph_electrical[3]` | **[VERIFIED]** |
| N14 | Daytona 660 valve interval: the top hit says 12,000 miles "across the line", the second says 20,000. | `triumph_triples[8]` vs `european_intervals[7]` | [REPORTED] |
| N15 | Street Triple trim letters "describe suspension, brakes and equipment" vs "the trim letter does change the displacement" — the 2017–2022 S is a 660, and the general rule orders 765 parts for it. | `triumph_triples[2]` vs `[4]` | [REPORTED] |

## Aprilia / MV slice

| # | contradiction | files | status |
|---|---|---|---|
| N16 | Aprilia's pre-Euro-5 6-pin plug erased by the cross-make "one lead, three makes" purchasing instruction. `compat_matrix` rows 157–158 record the 6-pin from the same vendor source. | `european_tooling[10]` vs `aprilia_mv_electrical[4]` | [REPORTED] |
| N17 | The regulation-sourced entry's one non-regulation clause — "still require the make's own tooling" — is refuted twice in the corpus, including four entries later in its own file. Everything in that entry that *is* a law claim stands. | `aprilia_mv_electrical[3]` vs `european_tooling[8]`, `aprilia_mv_electrical[7]` | [REPORTED] |
| N18 | Rear-wheel-radius acquisition: dealer tool in the DTC table, rider-performed calibration ride in the knowledge base. Different tables, so neither suppresses the other — both are live for the same machine on the same day. | `dtc_codes/aprilia.json` P0510 vs `aprilia_rsv4[4]` | [REPORTED] |

## Cross-make slice

| # | contradiction | files | status |
|---|---|---|---|
| N19 | Ducati dealer-tool lockout: the tooling file says there is none, the hardware catalogue prices a dealer-only tool at $2,499 and tells independents to buy something else. | `european_tooling[3]` vs `adapters.json`, `compat_matrix.json` | [REPORTED] |
| N20 | TuneECU CAN-era Triumph rated `full` in the compat matrix against "no read" in the tooling file — **from the same cited source**. The KTM half of the same claim is encoded correctly as `partial`, proving the schema can express it. | `european_tooling[2]` vs `compat_matrix.json` | [REPORTED] |
| N21 | "Stock the Italian 3-pin lead once… one purchase, not three" against catalogue rows recording 6-pin Aprilias inside the same window. | `european_tooling[10]` vs `compat_matrix.json` | [REPORTED] |
| N22 | "The crown-wheel bearing carries an individual BMW part number" against a catalogue row that exists specifically to record that it does not. | `european_parts[3]` vs `parts.json` | [REPORTED] |
| N23 | The early Mitsubishi charging family is assigned to the Tuono V4 R 2011 in the row's own notes, while the row's `model_pattern` is `RSV4%` and cannot match a Tuono. The Kokusan sibling *did* get a dedicated Tuono row. | `european_parts[2]` vs `parts.json` | [REPORTED] |
| N24 | Desmoquattro rockers: prose covers the "916–998 family", the catalogue's `model_pattern` `9_6%` with `year_max: 2002` excludes the 998, 748, 888 and 851 — so those machines return no rocker row at all. | `european_parts[4]` vs `parts.json` | [REPORTED] |
| N25 | One blanket 7,500-mile "Desmodromic valve service" for every Ducati including the two spring-valve engines. See S5. | `service_interval_templates.json` vs `european_intervals[11]`, `[2]` | **[VERIFIED]** |
| N26 | KTM 690 valve check stored as 15,000 **miles**, a figure matching no KTM interval in the corpus. See S5. | `service_interval_templates.json` vs `european_intervals[6]`, `[1]` | **[VERIFIED]** |
| N27 | Moto Guzzi has zero rows in the hardware compatibility data while the tooling file says its answer is identical to Aprilia's; PADS, a Piaggio Group platform, is scoped in the catalogue as "Aprilia's factory tool". | `european_tooling[7]` vs `compat_matrix.json`, `adapters.json` | [REPORTED] |

---

# Part 3 — Uncertain (13)

Recorded so nobody re-litigates them from scratch, and explicitly **not**
asserted. Each survived a kill attempt only partially.

1. The 998 listed as Desmoquattro in the differentials file and Testastretta in the Monster file — taxonomy, with a real catalogue consequence.
2. Shims listed as a valve-adjustment part for the R1100/R1150 oilhead, which the intervals file classes screw-and-locknut. The entry hedges "shims **or** feeler gauges".
3. Coding described as dealer-only on BMW while the compat matrix rates an independent kit "full … coding" — may be a bundling difference (coding vs programming vs software updates).
4. The Street Triple 675 labelled "Sagem-era" and inheriting an idle-hose finding written for a different management generation; already propagated into three catalogue rows.
5. TuneECU coverage said to be keyed by frame-number breaks where the vendor's table is keyed by model year. Thin operative cost.
6. The EFI changeover stated as a year range in one entry and denied as a year question in another — the entries agree on procedure, differ on the printed range.
7. The parts catalogue converts the IACV VIN split into a model-year split; both rows carry the VIN numbers in `notes`.
8. `european_intervals[6]` prints a closed set of kilometre valve intervals in an entry whose `model` field names the 450/500 EXC-F, which is serviced by engine hours. A scoping defect in a retrieval surface.
9. The "1190/1290 fitment unknown, not excluded" correction is year-capped at 2013, so no 1190 or 1290 lookup can reach it.
10. `ktm_engines[0]` enumerates LC8c as "the 790 and 890 models" only; three other places name the 2024-on 990 Duke as LC8c. Nearly killed — the entry's fix is a physical count-the-cylinders test.
11. Whether the Aprilia V4 generator family can be resolved from documentation or only by pulling the cover. Both entries converge on "establish it from the machine".
12. MV triple crank direction: the entry determines the direction and then disclaims it in the next sentence. A documentation defect more than a both-answers contradiction.
13. Moto Guzzi V100 valve job: "rocker shaft out" in the job-type entry, "camshafts out" in the model entry — same file. Demoted to uncertain by S2: the job-type entry is unreachable from a Guzzi make filter, so the correct entry is the only one returned.

---

# Part 4 — What the sweep cleared

Reported as data, because a clean result on a dimension that has been wrong
before is worth recording.

**The DTC shadow discipline holds.** Every make-specific row that shadows a
generic code was compared field by field. Overlaps: BMW 7, Ducati 6, KTM 6,
Triumph 4, Harley 1; Aprilia and MV Agusta shadow nothing. **All 24 European
overlaps differ substantially in both `common_causes` and `fix_summary`** —
highest similarity ratio 0.18 on causes, 0.16 on fixes, no field identical
anywhere. No make row hides a generic row.

Two adjacent observations offered as data, not findings: six make rows
silently change the severity a code triages at (KTM P0130/P0150/P0420
`medium→low`, KTM and Triumph P0120 `high→medium`, Ducati P0230
`critical→high`), and KTM P0120 moves `category` from `fuel` to `engine`.
Each is individually defensible.

Also cleared: the Phase 238 back-propagation into `ktm_adventure[7]` is clean;
the Phase 236 Triumph connector correction did reach `triumph_electrical[1]`;
the BMW ELAST belt pairing in the catalogue is correct; the Moto Guzzi
small-block filter cross-reference is correct; the KTM adaptor C/D split is
consistent row by row; and no Triumph same-engine sibling pair differs on
interval.

---

# Recommended scheduling

1. **S1 first, and alone.** It changes the answer to every knowledge query in
   the product. One phase, its own regression, and a decision about the 73
   test files that assert on `results[0]`.
2. **S2, S3, S4 together** — they are all "the correction cannot be reached
   from where the error is". Count-neutral data edits plus a guard asserting
   that every Track K entry is reachable from at least one make filter.
3. **S5 with the catalogue contradictions** (N19–N27) — one pass over
   `advanced/data/`, which no Track K test reads today.
4. **The per-make content contradictions** (N1–N18) in make-sized batches,
   each following the Phase 240B pattern: read the verifier note first, check
   the count guards before editing, and mutation-test every new guard.

Before fixing any [REPORTED] finding, verify it. That is the whole lesson of
the document this one extends.
