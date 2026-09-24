# Phase 354 — Scooter electrical (12V minimal)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-24 (close-out)

History: 1.0 the plan, after Step 0 (2026-09-24, `6c60740`); **1.1 the
close-out** — every section annotated *As built*, the checklist ticked with
its evidence, Deviations and Results added.

## Goal

Row 354: "Stator-to-battery, no FI on older carb scooters, simple wiring."
Write the scooter charging layer that Track M left empty, per machine and
per make, anchored to the makers' service manuals, so that a scooter query
finds its own charging system at tier 0 — and so that Gate 14 (258) has
electrical content to reach.

*As built:* seven rows shipped, one make per row, each reaching the machines
it names at tier 0 (tested for 13 machine spellings). Corpus 1,046 → 1,053.

## Step 0 — greenfield, extension or reshape?

**Extension: content only.** No code, no schema, no new axis. Measured on a
copy of the live database (schema unchanged since 257B, **1,046** rows) and
on the research library, 2026-09-24. Artefacts:
`~/research/motodiag/354_step0/` (scripts, page selection, raw sweep
output, `verified.json`).

| # | measured | how |
|---|---|---|
| S0-1 | **The scooter charging layer is empty.** Across the 50 rows of 251–254's four files, `stator` 0, `charging` 0, `rectifier` 0 | whole-word census, `census.py` |
| S0-2 | **Every `regulator` in those files is the US regulator** (NHTSA): 53 uses in 15 rows, none a voltage regulator. The fifth word collision in this track | matched strings printed, not counted blind |
| S0-3 | The census was itself wrong twice before this: `battery` read **0** (a regex missing its first letter) and `regulator` matched *regulatory*. Both fixed and re-run with the matches printed as the positive control; battery then read 225 corpus-wide | `census.py` |
| S0-4 | Charging content exists for motorcycles: 89 rows mention a stator, across 12 make groups (Honda 19, Suzuki 17, Kawasaki 16, Harley 12, Yamaha 11 …) | live copy |
| S0-5 | **Three Honda `model = All` rows reach every Honda scooter at tier 1 (`make_wide`)**: #263 "Regulator/rectifier failure — the universal Honda problem", #264 "Stator failure … all Honda models", #270 "Charging system preventive testing". All `unverified`. #263 tells the owner to replace the regulator with a MOSFET unit ("fits 90% of Hondas") | `known_issues_for_vehicle`, Ruckus / PCX150 / Metropolitan |
| S0-6 | A Ruckus is reached by 19 charging rows, a Zuma 125 by 12, **none about its own machine**; a Kymco Agility 50 by none | same |
| S0-7 | Every target machine resolves to a tier-0 spelling (`PCX 150`, `Metropolitan`, `Agility 50`, `People S 250`, `Zuma 125`, `LX 50`, `GTS 300`, `Fly 50`, `MP3 400`, `Beverly 125`, `Symply 125`, `Buddy 125`); a bare "SYM Fiddle" reaches nothing at tier 0 | resolver on the live copy |
| S0-8 | **Library:** 89 scooter-named PDFs; 79 extracted, 8 are saved HTML, 2 duplicates, 2 image-only (`grom_service.pdf`, `piaggio_primavera_om.pdf` — F127). 46 documents carry charging pages (678 pages) | `extract.py`, `select_pages.py` |
| S0-9 | **Sweep:** one Subconscious call per document, one turn, no tools. **1,227 facts returned, 1,115 verified** against the named page's text, **112 dropped (9%)** — most in the CHF50 mirror, whose OCR spaces letters apart. Four calls failed (two truncated or placeholder answers, two refused at zero tokens) and were re-run, not guessed past | `sweep.py`, `verify.py` |
| S0-10 | **Carburettor versus injection does not predict the charging design.** Three-phase: Honda PCX150 (FI) *and* CHF50 Metropolitan (carb); Piaggio Fly 125, Beverly 125, Vespa LX 125–150 (carb) and GTS 300, MP3 400 (FI); Kymco People S 250 (carb). Single-phase or split: Kymco Agility 50 (*"Single-phase half-wave SCR"*, separate lighting coil), Piaggio Fly 50 (*"Generator single-phase alternating current"*), SYM Fiddle 50 / Jet Euro / Symply 125 (charging coil + illumination coil, SCR). Yamaha's injected Zuma 125 prints *"AC magneto"* | verified quotes, the load-bearing pages re-read by hand |
| S0-11 | **The PCX150 2013–2017 service manual: *"The regulator/rectifier is built into the ECM."*** (p. 390 of the PDF) and *"Lighting system Battery"* (p. 12). S0-5's replace-the-regulator advice has no separate part to act on for this machine | read by hand |
| S0-12 | Owner's manuals do not state the generator type: Genuine's print *"Flywheel Magnet Stator"*; Honda's current PCX and Metropolitan owner's manuals give none | verified quotes |
| S0-13 | **Already written, not to be restated:** 252's Ruckus/Metropolitan row (carb vs FI, battery and fuse sizes) and 254's kickstart row (kickstart and injection never on the same machine, the flat-battery case) | seed files |

**The row's three claims, against the documents.** *Stator-to-battery* is
true on the three-phase machines and incomplete on the split ones, where
the headlight runs on AC from its own coil and never passes the battery.
*No FI on older carb scooters* is a tautology as written, its useful half
is already shipped (S0-13), and carb versus injection does not predict the
charging system (S0-10). *Simple wiring* is no document's claim and is not
written.

*As built:* every S0 row held through the build. S0-2's live count is
re-read at close-out (Results). One S0-10 clause narrowed under refute: the
CHF50 manual never prints "Metropolitan", so the rows say CHF50.

## Decisions

- **D1 — One make per row.** F142: a multi-make row pairs every model with
  every make in the junction. Each row names its own maker's machines, with
  the spellings S0-7 shows resolve.
  *As built:* as planned; `test_one_make_per_row` and a mutation pin it.
- **D2 — Unscoped on transmission.** These claims are about a machine's
  generator, not its transmission; under Phase 255's contract an absent key
  means the row makes no claim on that axis. The row's scope is its model
  column.
  *As built:* as planned; no row carries `applicability` (tested, and a
  `{cvt}` mutation is caught).
- **D3 — Anchored or not written** (254 D1). Every statement quotes a named
  document; a subject that yields no quote that survives refute ships
  nothing. Source label `service-manual` for every row.
  *As built:* as planned. Two subjects shipped nothing: R7 (Genuine) and the
  Symply 125 inside R3, each for want of a document tying a manual to a
  machine (Deviations).
- **D4 — The subjects, a ceiling not a promise.** Text is written at build
  time from the quotes.

  | # | make | machines | subject |
  |---|---|---|---|
  | R1 | Honda | PCX150 (2013–17), CHF50 Metropolitan | three-phase alternator/starter on both, carb and FI alike; on the PCX the regulator/rectifier is inside the ECM |
  | R2 | Kymco | Agility 50, People S 250 | one maker, opposite systems: single-phase half-wave SCR with an AC lighting coil, against a three-phase generator |
  | R3 | SYM | Fiddle 50, Jet Euro 50/100, Symply 125 | charging coil and illumination coil: the lighting side is AC and measured on the AC range |
  | R4 | Piaggio | Fly 50, Fly 125, Beverly 125, MP3 400 | single-phase on the 50, three-phase with a non-adjustable transistor regulator above it |
  | R5 | Vespa | LX 50, LX 125/150, GTS 300 | three-phase alternator, regulator wired to the battery with no key-switch connection |
  | R6 | Yamaha | Zuma 125 | AC magneto on an injected scooter; the published output and regulator ratings |
  | R7 | Genuine | Buddy 125 | the owner's manual names only a "flywheel magnet stator"; the PGO service manual's inspection |

  *As built:* R1 split into two rows (PCX150; CHF50), R3 without the
  Symply 125, R7 dropped: seven rows. Final machines per row are in
  Results.

- **D5 — The Honda make-wide rows are filed, not edited.** #263, #264 and
  #270 are identified by (make, model, title) (F129); correcting them needs
  a migration and a source they do not have. Filed as a finding with S0-5's
  measurement. R1 reaches the PCX and Metropolitan at tier 0, above them.
  *As built:* filed as **F149**. The PCX150 row outranks them (tested); the
  CHF50 row is modelled `CHF50`, so it reaches a CHF50 at tier 0 and a
  current Metropolitan only at tier 2.
- **D6 — Refute before commit.** Every drafted row goes through `/refute`
  on Opus, which opens each cited page itself; a row whose central sentence
  dies is rewritten once or dropped.
  *As built:* four refuters, 170 claims, 140 kept, 30 killed; every kill
  rewritten or dropped, none removing a row's central finding. The block is
  in the phase log and passes `refute_check.py`.
- **D7 — Not written here:** carb versus injection and kickstart (S0-13),
  carburettor service (353), wiring diagrams, any figure not printed on a
  fetched page.
  *As built:* held; `TestBoundaries` forbids carburettor-service terms, a
  kickstart claim and the Ruckus/NCW50 comparison.

## Scope

1. `known_issues_scooter_electrical.json`, at most seven rows (D4).
2. `tests/test_phase354_scooter_electrical_content.py` in 254's shape:
   every row anchored and labelled, one make per row, no restatement of
   S0-13's rows, every number on a cited page, and reachability — each
   named machine gets its row at tier 0 through `known_issues_for_vehicle`,
   and the rows survive `rows_for_machine`.
3. The "curated known issues" count moved in README and the launch
   checklist (Phase 208's guard).
4. A finding for S0-5.

*As built:* all four, plus F150 and one moved pin (Deviations).

## Non-goals

No schema change or migration; no new applicability axis; no edit to any
existing row; no carburettor service (353); no Gate 14 (258); no fix for
F142 or F127.

*As built:* held. No existing row was edited; F149 and F150 record the two
older defects this phase found.

## Verification checklist

- [x] every row anchored to a named document with verbatim quotes; every
      number on a cited page — quotes verified against page text by
      `verify.py`, load-bearing pages re-read by hand, then refuted
- [x] refute run over every row; its verdicts and what changed recorded —
      170 claims, 140 kept, 30 killed; block in the phase log, `refute_check`
      exit 0
- [x] one make per row; no row restates 252's or 254's rows —
      `TestWhatShipped`, `TestBoundaries`
- [x] each named machine reaches its row at tier 0; a Gold Wing does not
      get them above tier 2 — `TestReachable`, 13 machine spellings through
      `known_issues_for_vehicle` and `rows_for_machine`
- [x] new test file scanned by 244G; mutations N/N — 244G passes over the
      whole tree including the new file; break-it **12/12**
- [x] whole-tree gates on every pre-commit run; `COLLECTED_TEST_FLOOR`
      raised before the regression of record — 8999 → 9089 at `c79ddec`
- [x] live DB: backup, copy-first dry run, load, before/after printed — dry
      run on a fresh copy before the merge (1,046 → 1,053, the 1,046 hashed
      identical, a second load adds 0); the live load follows the merge
      per the closeout sequence and is recorded in the phase log
- [x] ROADMAP row closed, `implementation.md` history row and version

## Risks

- **A per-machine quote read as a make-wide rule.** 254 and 255B lost
  every tidy generalisation. Each row states its machines and does not
  generalise past them.
- **Recycled page templates.** 254 found FILLY page headers in the Agility
  50 manual; the sweep flagged two here (pp. 71, 174). Every quote's page is
  checked for its header.
- **Mirror provenance.** Most service manuals here are third-party copies;
  each row says so, as 251–254 did.

*As built:* the first risk was the live one, in a different shape — not a
make-wide rule but a **model identity** taken from a file name or an older
row (Symply, Metropolitan, Zuma). The header risk held: the Kymco figures
are from pages headed AGILITY 50 and the row says so. The provenance risk
inverted: "third-party mirror, the same copy Phase 254 cited" was false
for three manuals, so every row now says only what is known.

## Deviations

- **Seven rows, not the planned seven subjects.** R1 split into two rows
  (a row carries one year window, and the PCX150 and CHF50 need different
  ones); R7 (Genuine) was dropped because PGO's "PA 100 / 125" manual is
  not shown by any document to be a Buddy 125, leaving only an absence.
- **Symply 125 removed from R3**: its manual says only "MODEL ABA" (F150).
- **The PCX150 row got an end year (2015)** that v1.0 did not plan; a
  refuter found the 2018-on PCX150 is a different engine.
- **"Metropolitan" removed from the CHF50 row** — the manual never prints it.
- **Zuma 125 kept in the Yamaha row with its bridge stated**: the manual
  prints "YW125Y"; the link to the name is Phase 253's cover-code row.
- **Provenance rewritten on every row** from "the same copy Phase 254
  cited" to what is known.
- **A 255C pin moved**: the PCX tier table (11 → 12 at tier `model`,
  166 → 168 retrieved and kept), reason in the test.
- **`COLLECTED_TEST_FLOOR` rose by 90, not 85**: +5 from the F148 fix's
  closeout tests, never added to the floor.
- **A void deploy dry run** (zsh aborted a chain at an unmatched glob) was
  recorded and re-run under `bash` `set -euo pipefail`; the live file was
  checked untouched.
- **No bug fixes.** Nothing the phase shipped failed after it was
  committed; the census and sweep errors were caught in Step 0, before
  anything they produced was used.

## Results

| | before 354 | after 354 |
|---|---|---|
| scooter charging rows in Track M | 0 (`stator`, `charging`, `rectifier` 0 in 251–254's files) | **7** |
| corpus (seed files) | 1,046 | **1,053** |
| schema | 66 | 66 (no migration) |
| machines reaching an electrical row of their own at tier 0 | 0 | **13 spellings tested** (PCX150, CHF50, Agility 50, People S 250, Jet Euro 50, Joyride 125, Fiddle 50, Fly 50, MP3 400, LX 50, GTS 300, Zuma 125, YW125) |
| sweep | — | 46 documents, 1,227 facts, 1,115 verified |
| refute | — | 170 claims, 140 kept, 30 killed |
| 354 tests | 0 | **85** (`test_phase354_scooter_electrical_content.py`), mutations **12/12** |
| findings | — | **F149**, **F150** filed |
| `COLLECTED_TEST_FLOOR` | 8999 | **9089** |
| regression | 8999 at `d91c243` (257B) | **9089 passed, 0 failed, 0 skipped** at `c79ddec`, 52:16 |
| live DB | 1,046 rows, schema 66, 10 vehicles (fresh copy, 2026-09-24) | dry run 1,053; live load after merge (phase log) |

Carburettor versus injection does not predict how these scooters charge:
the carburetted CHF50 has a three-phase alternator/starter run by an ECM,
the injected YW125 prints "AC magneto", and one Kymco and one SYM manual
each hold both a split lighting-coil design and a single-generator one.
