# Phase 353 — Small-engine carb service (single/twin-barrel)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-24 (close-out)

History: 1.0 the plan, after Step 0 (2026-09-24, `7cb9a75`); **1.1 the
close-out**: every section annotated *As built*, the checklist ticked with
its evidence, Deviations and Results added.

## Goal

Row 353: "Keihin/Mikuni small-bore carbs, seasonal cleaning, emission
restrictions." Write the carburettor-service layer that Track M left to
this row, one make per row, anchored to the makers' own documents, so a
carburetted scooter's query finds its own carburettor at tier 0. Gate 14
(258) also needs carb content to reach.

*As built:* seven rows, one make per row. Each reaches the machines it names
at tier 0, tested for 19 machine spellings. Corpus 1,053 → 1,060.

## Step 0 — greenfield, extension or reshape?

**Extension: content only.** No code, no schema, no new axis. Measured on a
`.backup` copy of the live database (1,053 rows, max id 5343) and on the
research library, 2026-09-24. Artefacts: `~/research/motodiag/353_step0/`
(`census.py`, `reach.py`, `extract.py`, `select_pages.py`, `sweep.py`,
`verify.py`, `fields.txt`, `pages/verified.json`).

| # | measured | how |
|---|---|---|
| S0-1 | **Track M has no carburettor service.** Across the 57 rows of 251–254's and 354's five files: `float bowl` 0, `pilot screw` 0, `main jet` 0, `slow/pilot jet` 0, `jetting` 0, `ethanol` 0, `storage` 0. The only carburettor words there say that a machine *is* carburetted (`carburetted` 12, `carburettor` 7, `carburetor` 5, printed) | `census.py`, matched strings printed |
| S0-2 | **The corpus's carburettor service is ten unsourced big-bike rows.** `known_issues_cross_platform_carbs.json`: each row's title or text is general (one is titled "CV carburetor diaphragm failure — all makes and models"), but each is filed under one make and one large model (CB750, V-Star 650, KZ1000, GSX-R750 …), window 1969–2015, `source` null. The same holds for all 80 rows of the eight `cross_platform_*` files | seed files |
| S0-3 | **No carburetted scooter reaches a carburettor row about its own carburettor.** Kymco Agility 50 / People S 250, SYM Fiddle 50 / Jet Euro 50, Piaggio Fly 50 / Fly 125 / Beverly 125, Vespa LX 50 / LX 150 / S 50 and Genuine Buddy 125 get no carburettor-service row at all. A Ruckus or CHF50 gets 18–19 at `make_other_model`, the first being "Float bowl overflow and fuel leak" (CBR600F4i); a Zuma 50 / Vino gets 22, the first "V-Star 650/1100 vacuum petcock failure" | `reach.py`, `known_issues_for_vehicle` + `rows_for_machine` |
| S0-4 | **Library:** every PDF extracted this time (354's name filter missed `honda/ruck_*.pdf`, the Lance manuals and the Dio): 271 files, 264 unique, 246 extracted, 18 unreadable by pypdf, 14 with no text layer. 46 with `carburet` ≥ 3; five excluded by their own title page (KTM 950 Super Enduro R, YZF600RW, XR650L, Bonneville) or as injected (MP3 500). **41 documents, 947 selected pages** | `extract.py`, `select_pages.py` |
| S0-5 | **Sweep:** one Subconscious call per document, one turn, no tools. **1,300 facts, 1,207 verified** against the named page's text, **93 dropped (7%)**; 41 of 41 calls parsed, none re-run | `sweep.py`, `verify.py` |
| S0-6 | **"Keihin/Mikuni" is true for part of the class.** Printed makers: **Keihin** on the Piaggio four-strokes (Fly 50 "CVK 18", Fly 125–150 and Vespa LX 125–150 "CVEK26", Beverly 125 "CVEK 30"), the Vino 50 (XC50, "NCV18 x 1") and Kymco's Super 8 ("Keihin 16.5 mm"); **Mikuni** on the Vino 125 (YJ125, "BS26"); **Dell'Orto** on the two-stroke Vespa LX 50, S 50 and Piaggio Typhoon 50 ("PHVA 17.5"); **Teikei** on the two-stroke Zuma 50 (YW50, "Y14P"). The Kymco, SYM and Honda CHF50 **service manuals print a type (CVK, PB2BE, NVK00E) and no maker** | verified quotes |
| S0-7 | **"Single/twin-barrel": every carburettor in the class is printed "× 1"**; no document prints a twin-barrel carburettor. The one twin-cylinder machine read (Yamaha XV250) prints "BDS26 × 1" | verified quotes |
| S0-8 | **Seasonal storage: the makers disagree on when and how.** Kymco's Agility 50 service manual drains the float chamber when the machine "is not used for over one month"; Yamaha's owner's manuals drain it "before storing your scooter for several months" and **pour the drained fuel back into the tank** with stabiliser; Kymco's owner's manuals drain the carburettor **and empty the tank**; a Bintelli manual says two weeks | verified quotes |
| S0-9 | **Emission restrictions take three forms.** Honda's Ruckus: "no adjustment should be made except idle speed adjustment with the throttle stop screw"; SYM: schedule items marked ☆ are emission items "prohibited to be adjusted" under EPA rules, and the pilot screw is "set at factory"; Piaggio: the mixture screw's "final position should be determined by an exhaust fume analysis" (CO 3.8 ± 0.7 % on the Beverly 125), and "TAMPERPROOF SCREWS ARE SUPPLIED WITH 125 CC MODELS". *Corrected at build (Deviations):* SYM's note ends "by unauthorized people" and is in two of the four manuals; the tamperproof screws are the intake manifold's | verified quotes |
| S0-10 | **Cold-start enrichment differs by maker and so does its test.** Honda CHF50 "Starting enrichment (SE) valve resistance 2.8 – 5.2 Ω"; SYM auto by-starter "Max. 10 Ω"; Kymco Agility 50 10 Ω max and People S 250 14–20 Ω, with a blow-through test (blocked after 5 min powered, open after 30 min cold); Piaggio "Starter resistance 20 Ohm (at 24°)", pin travel 10 mm, "maximum time 5 min" | verified quotes |
| S0-11 | **Honda's Ruckus fuel rule changed between editions.** 2012 (31GGA6300): methanol "5% by volume (max)" with cosolvents, MTBE 15 %; 2022, 2024, 2025: "Do not use gasoline containing methanol". High altitude: above 6,500 ft (2,000 m) the carburettor may be adjusted by the dealer and "must be returned to standard factory specifications" below 5,000 ft (1,500 m). The CHF50 service manual gives the altitude settings (main jet #70, pilot screw 1/2 turn in) | verified quotes |
| S0-12 | **Identities checked on the title page** (354's lesson). The "Buddy 125" service manual is PGO's "PA 100 / 125" and never prints Buddy (0 pages); the Symply manual is "MODEL ABA" (F150); the Grand Tourer 150 manual is Royal Alloy's; the Bella Classic 50 is the Chicago Scooter Company's | page 1 text |
| S0-13 | **Already written, not to be restated:** 252's Ruckus/Metropolitan row (the Ruckus is carburetted and the Metropolitan injected; it notes the altitude section exists and the idle-only sentence), 253's Zuma/Vino row (the three carburettor codes as evidence of three engines), 254's kickstart row and 354's charging rows | seed files |

**The row's three claims, against the documents.** *Keihin/Mikuni
small-bore carbs* is true for the Piaggio four-strokes and the Vino and
false for the two-strokes (Dell'Orto, Teikei); for Kymco, SYM and the
CHF50 the service manual does not say. *Seasonal cleaning* has no common
rule: the makers disagree on when to drain and what to do with the fuel
(S0-8). *Emission restrictions* are real and take three different forms
(S0-9).

*As built:* S0-1..S0-8 and S0-10..S0-13 held. Two corrections came from
reading pages by hand (S0-9) and one from refute (S0-12: the CHF50 cover,
which has no text layer, prints "CHF50/P/S METROPOLITAN" and "2002–2006";
filed against 354 as F152).

## Decisions

- **D1 — One make per row** (F142), as 354. Piaggio and Vespa are separate
  makes in the corpus and get separate rows.
  *As built:* as planned; `test_one_make_per_row` and a mutation pin it.
- **D2 — Unscoped on transmission** (Phase 255's contract); the model
  column scopes the row.
  *As built:* no row carries `applicability` (tested; a `{cvt}` mutation is
  caught). Two rows carry a year window from their documents: CHF50 from
  2002, Ruckus 2012–2025.
- **D3 — Anchored or not written.** Every statement quotes a named
  document; a subject whose quote dies under refute ships nothing. Label
  `service-manual` for every row. Owner's-manual-anchored rows carry that
  label as 252's and 253's did: it names the maker's own document, and the
  text says which document it is.
  *As built:* as planned. R8 shipped nothing (Deviations).
- **D4 — The subjects, a ceiling not a promise.** Text is written at build
  time from the quotes.

  | # | make | machines | subject |
  |---|---|---|---|
  | R1 | Honda | CHF50 | the service manual's settings, SE valve test, high-altitude settings, pilot screw handling |
  | R2 | Honda | Ruckus (NPS50) | idle is the only owner adjustment; altitude up and back; the methanol rule that changed after 2012 |
  | R3 | Kymco | Agility 50, People S 250 | pilot screw factory-set, count the turns; the bystarter's two-temperature test; drain after a month unused; the carburettor's maker is not printed |
  | R4 | SYM | Jet / Jet Euro 50–100, Fiddle 50, Fiddle III, Joyride 125–200 | auto by-starter test; ☆ emission items not to be adjusted; pilot screw set at factory |
  | R5 | Piaggio | Fly 50, Fly 125/150, Beverly 125, Typhoon 50 | Keihin on the four-strokes, Dell'Orto on the two-stroke; mixture set by CO analysis; tamperproof screws on 125s; auto-starter figures |
  | R6 | Vespa | LX 50, S 50, LX 125/150 | Dell'Orto PHVA on the two-stroke 50s, Keihin CVEK26 on the LX 125–150; CO adjustment |
  | R7 | Yamaha | Vino 50 (XC50), Vino 125 (YJ125), Zuma 50 | three carburettor makers across one scooter family; adjustments left to the dealer; storage drains the float chamber back into the tank; E10 yes, methanol no |
  | R8 | Genuine | Urbano 125 | owner's-manual storage (stabiliser, run, drain) — thin; dropped if nothing else survives |

- **D5 — The cross-platform rows are filed, not edited.** S0-2's 80 rows
  are another phase's content and their identity is (make, model, title)
  (F129). Filed as a finding with the S0-2/S0-3 measurement.
  *As built:* filed as **F151**. Every named machine's own row now outranks
  them (the Ruckus row above the CBR600F4i float-bowl row, tested).
- **D6 — Refute before commit** on Opus, each refuter opening every cited
  page itself; a row whose central sentence dies is rewritten once or
  dropped.
  *As built:* four refuters, 178 claims, 146 kept, 32 killed; every kill
  rewritten, none removing a row's subject. The block is in the phase log
  and passes `refute_check.py`.
- **D7 — Not written here:** carb versus injection (252), the three
  engines behind the Zuma/Vino names (253), kickstart (254), charging
  (354), the XV250 (one small twin, one owner's manual: not a class), any
  figure not printed on a read page, and no "Keihin/Mikuni" generalisation.
  *As built:* held; `TestBoundaries` pins each.

## Scope

1. `known_issues_small_engine_carbs.json`, at most eight rows (D4).
2. `tests/test_phase353_small_engine_carb_content.py` in 354's shape:
   anchored and labelled, one make per row, the boundaries of S0-13, every
   figure on a cited page, and reachability — each named machine gets its
   row at tier 0 through `known_issues_for_vehicle`, and the rows survive
   `rows_for_machine`.
3. The "curated known issues" count moved in README, quickstart, install
   guide and launch checklist (Phase 208's guard).
4. A finding for S0-2.

*As built:* all four, plus F152 and one moved pin (Deviations).

## Non-goals

No schema change or migration; no edit to any existing row; no Gate 14
(258); no fix for F142, F127, F149, F150 or the S0-2 finding.

*As built:* held. No existing row was edited.

## Verification checklist

- [x] every row anchored to a named document with verbatim quotes; every
      number on a cited page. Quotes verified against page text by
      `verify.py`; load-bearing pages re-read by hand; after the rewrite,
      `check_quotes.py` found all 98 quotes (a planted fake was caught)
- [x] refute run over every row; verdicts and changes recorded:
      178 claims, 146 kept, 32 killed; block in the phase log,
      `refute_check` exit 0
- [x] one make per row; no row restates 252's, 253's, 254's or 354's rows:
      `TestWhatShipped`, `TestBoundaries`
- [x] each named machine reaches its row at tier 0; a Gold Wing does not
      get them above tier 2: `TestReachable`, 19 machine spellings
      through `known_issues_for_vehicle` and `rows_for_machine`
- [x] 244G over the whole tree (0 hits); break-it **14/14**
- [x] whole-tree gates on every pre-commit run; `COLLECTED_TEST_FLOOR`
      raised before the regression of record: 9089 → 9188 at `fb4a76d`
- [x] live DB: backup, copy-first dry run, load, before/after printed.
      Dry run on a fresh copy before the merge (1,053 → 1,060, the 1,053
      hashed identical, a second load adds 0); the live load follows the
      merge and is recorded in the phase log
- [x] ROADMAP row closed, `implementation.md` history row and version

## Risks

- **A figure from the wrong edition or variant.** The service manuals
  print two to four columns per table (Joyride LA12W/LA15W/LA18W, People
  S 250 against People 250, Beverly 125 against 250). Each figure is
  attributed to its column.
- **Model identity** (354): each machine named only as its document prints
  it, with the bridge stated where a cover code is involved (YW50 → Zuma
  50, XC50 → Vino 50, YJ125 → Vino 125).
- **Mirror provenance.** Each row says only what is known of its copy.

*As built:* the first risk was live twice, as a column taken for a whole
manual (the Fly 50 given the Fly 125's automatic starter, the B 125
engine's Walbro given to the Beverly 125). The identity risk was live
once: "Fiddle III" came from a file name. The provenance risk held.

## Deviations

- **Seven rows, not eight.** R8 (Genuine) was dropped. Its one source, the
  Urbano 125 owner's manual's storage paragraph, is word for word the
  Chicago Scooter Company's Bella Classic 50 paragraph.
- **S0-9 corrected by hand-reading, before refute.** SYM's star note ends
  "by unauthorized people", and only the Joyride and XA05W-6 manuals carry
  it. Piaggio's tamperproof screws are the intake manifold's, not the
  mixture screw's.
- **S0-12 extended by refute.** The CHF50 cover, image-only, prints
  "CHF50/P/S METROPOLITAN" and "2002–2006". 353's row states it; 354's
  row says the opposite, filed as **F152**.
- **"Fiddle III" out of the SYM model column.** That manual prints only
  "MODEL XA05W-6"; the row names it by that code.
- **The Walbro columns out of the Piaggio row.** The B 125-250 manual
  (618162) is tied to no model the row names.
- **The Fly 50's automatic starter written as its own** (6 Ω ± 5 %,
  15 min), after a draft applied the Fly 125–150's (20 Ω, 5 min) to both.
- **The CHF50 reset written per edition**, with the replaced screw's
  initial opening and the asymmetric return from altitude.
- **The Ruckus row narrowed**: only the 2012 edition gives the owner an
  idle procedure, and the methanol change is dated "2022 or earlier".
- **A 255C pin moved**: the PCX tier table 168 → 170 retrieved and kept;
  the reason is in the test.
- **No bug fixes.** Nothing the phase shipped failed after it was
  committed. The Step 0 and draft errors were caught before commit.

## Results

| | before 353 | after 353 |
|---|---|---|
| carburettor-service rows about a small scooter's own carburettor | 0 | **7** |
| corpus (seed files) | 1,053 | **1,060** |
| schema | 66 | 66 (no migration) |
| machines reaching a carburettor row of their own at tier 0 | 0 | **19 spellings tested** |
| sweep | — | 41 documents, 1,300 facts, 1,207 verified |
| refute | — | 178 claims, 146 kept, 32 killed |
| 353 tests | 0 | **99**, break-it **14/14** |
| findings | — | **F151**, **F152** filed |
| `COLLECTED_TEST_FLOOR` | 9089 | **9188** |
| regression | 9089 at `c79ddec` (354) | **9188 passed, 0 failed, 0 skipped** at `fb4a76d`, 52:35 |
| live DB | 1,053 rows, schema 66, 10 vehicles | dry run 1,060; live load after merge (phase log) |

"Keihin/Mikuni" is true for part of the class: the Piaggio and Vespa
four-strokes and the Vino. The two-stroke Vespas and
the Typhoon carry Dell'Orto, the two-stroke Zuma 50 Teikei, and the Kymco,
SYM and Honda CHF50 service manuals name no carburettor maker at all.
