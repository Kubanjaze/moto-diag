# Phase 354 — Scooter electrical (12V minimal) — phase log

**Status:** ✅ Complete (2026-09-24)
**Opened:** 2026-09-24

---

### 2026-09-24 — Opened after 257, 257B and the F148 fix

Taken before 258 by the operator: Gate 14 queries a scooter for CVT,
electrical and carb content, and electrical (354) and carb (353) are not
built. Read before acting: ROADMAP (354, 353, 258 and the Track M rows),
`ROADMAP_AUTHORITY.md` (354 is backend, 205+), `257_implementation.md`
and `257B_implementation.md` in place of the newest handoff (operator: the
2026-09-23 handoff predates 257's close, 257B and F148), FOLLOWUPS (F115,
F127, F129, F142 bear on this), and 251–255B's implementation docs for the
content rules this track built.

ROADMAP row to 🚧 before Step 0: `572664b`, pushed on `phase-354`.
`roadmap_check.py` exit 0 before that commit.

**Decision (logged, not asked):** bulk reading goes through Subconscious
(`subc claude`, `subconscious/glm-5.3-marathon`), one document per call,
one turn, tools disabled with 257's flags. Every quote it returns is
checked against the page text by a script before it is used; its
`value` field is a map, not evidence, because a verbatim quote can sit
beside a value that says more than the quote does.

### 2026-09-24 — Step 0: extension, content only, no fork

Measurements S0-1..S0-13 are in the implementation doc. In short: the
scooter charging layer is empty (the only `regulator` in 251–254's files
is the US regulator), three unverified Honda `model = All` charging rows
reach every Honda scooter at tier 1, and the service manuals show that
carburettor versus injection does not predict the charging design (the
carburetted CHF50 Metropolitan is three-phase; the injected Zuma 125
prints "AC magneto"). The PCX150 manual puts the regulator/rectifier
inside the ECM.

**Decision (logged, not asked): no fork.** Each question had a default
this track already set: one make per row (F142), content written from
quotes and a subject dropped when its quote dies (254, 255B), and a defect
in an older row filed rather than patched mid-phase (254's F111). The
row's three phrases are tested, not written: *simple wiring* is no
document's claim, and *no FI on older carb scooters* is already shipped
by 252 and 254.

**Decision:** Honda rows #263, #264, #270 are filed, not edited (D5).

**The census was wrong twice before it was right** (S0-3): `battery`
read 0 through a regex missing its first letter, and `regulator` matched
*regulatory*. Caught because 0 batteries in 1,046 rows is impossible and
16 regulator rows beside 0 stator rows was implausible; both re-run with
the matched strings printed.

**Sweep:** 46 documents, 1,227 facts, 1,115 verified, 9% dropped. Four
calls failed and were re-run: Symply 125 (output overran its limit, only
the tail returned), Vespa LX 50 (a literal `[...]` placeholder), Fiddle
III and Fly 50 (refused at zero tokens). The prompt now caps an answer at
40 facts and forbids placeholders.

**Housekeeping, stated because it cannot be proved either way:** copying
the Step 0 scripts to `~/research/motodiag/354_step0/` briefly wrote five
files (`census.py`, `extract.py`, `select_pages.py`, `sweep.py`,
`verify.py`) into the research root and then deleted them. That tree is
not under git. Nothing in it references root-level files of those names,
so none is believed to have existed; if one did, it was overwritten.

### 2026-09-24 — Build: seven rows, four refuters, 30 claims killed

v1.0 committed and pushed at `6c60740` before any content was written.

Rows drafted from the verified quotes, every load-bearing page re-read by
hand first, then refuted on Opus by four agents (one per maker group),
each opening every cited page itself. 170 claims tested: 140 kept, 30
killed. None of the kills removed a row's central finding; they were
scope, conditions, attribution and provenance, which is what the test's
`TestWhatTheRefutersCorrected` now pins.

**Decisions (logged, not asked):**

- **Honda split into two rows** (PCX150; CHF50). A row has one year window,
  and 255B's F132 rule allows only a window a cited document supports.
  v1.0's D4 had them as one subject.
- **PCX150 window 2013–2015.** The service manual prints only "'13 model"
  and "After '13"; the refuter found the 2020 PCX150 is a different engine
  (149 cm3, 57.3 mm bore). 2015 is the last year a document ties to this
  manual (the 2015 owner's manual's KF18, 153 cm3); the PDF's file name
  says 2017, which is not a document.
- **"Metropolitan" out of the CHF50 row.** The CHF50 manual prints it 0
  times in 319 pages, and no document on disk ties the two names. The row
  is modelled `CHF50` so a current NCW50 Metropolitan cannot reach it at
  tier 0 (tested).
- **Genuine row (R7) dropped before refute.** Its service-manual half was
  PGO's "SERIVCE MANUAL 2004 PA 100 / 125", and no document establishes
  that the PA125 is a Buddy 125. What remained was one absence ("Flywheel
  Magnet Stator"), too thin to ship.
- **Symply 125 out of the SYM row.** The manual filed as the Symply says
  only "MODEL ABA". Phase 254 attributes figures to the Symply by name on
  the same file: filed as **F150**.
- **Zuma 125 kept in the Yamaha row, attributed.** The manual never prints
  "Zuma" (0 of 338 pages); it prints `YW125Y`. The bridge is Phase 253's
  cover-code row, and the row says so. One outside lookup was tried
  (NHTSA campaign 13V035's PDF): a 10-page scan with no text layer, so the
  search stopped there.
- **Provenance rewritten on every row.** "The same copy Phase 254 cited"
  was false for the SYM Jet, the Beverly (254 cited 665018/618162, this is
  664603) and the Vespa S 50. Each row now says only what is known: copies
  in the research library, not fetched from the maker by this entry. A
  refuter-supplied S 50 manual number (664788) appears nowhere in that
  manual and was not used.
- **Honda make-wide rows #263/#264/#270 filed as F149**, not edited (D5).

**The first draft's worst sentence** was Vespa's "a lights-off reading on
a 50 cc Vespa is allowed to run higher than on a 125": the 16 V figure is
a burnt-bulb regulation check with no measuring point, the 15.2 V a
battery-pole reading with a charged battery. Different tests; the
sentence compared nothing. And the Yamaha fix step had its logic
backwards: 0.42–0.56 ohm fails *both* of the manual's ranges, it does not
fall "between" them.

**Tests:** `tests/test_phase354_scooter_electrical_content.py`, 85
collected. Break-it **12/12**: each mutation re-plants one defect this
phase found or excluded (open PCX window, "Metropolitan" in the CHF50
model, a multi-make row, a `{cvt}` scope, the backwards Zuma band, Symply
back, the 254 provenance line, the Vespa comparison, a loose model
spelling, a wrong Honda standard, an `unverified` label, a kickstart
claim); the seed file byte-identical after. The tier-0 test was seen red
for a real reason during the build: removing the Symply dropped it to
`make_other_model`.

**Counts:** corpus 1,046 → **1,053**. The Phase 208 guard named four
documents holding 1046 (README, quickstart, install guide, launch
checklist); an earlier grep had found two.

**A 255C pin moved, with its reason.** The whole-tree run before the first
commit (1,941 passed, 1 failed, 13:09) failed
`test_phase255C_junction_identity::test_the_tier_table`: the PCX reached
12 rows at tier `model`, not 11. Measured on a fresh seed: 12 at `model`,
168 retrieved and 168 kept, not 166 — +1 is 354's PCX150 row at tier 0,
+1 its CHF50 row at `make_other_model`. The pin records 255C's result and
was moved with that reason in the test, as 252–254 moved 250C's. Not a
bug fix: the rows did what they were written to do.

### 2026-09-24 — Deploy dry run on a copy of the live database

**First attempt was void, and is recorded because it looked like a
result.** zsh aborted an `&&` chain at an unmatched `rm -f copy.db*` glob,
so the backup copy was never taken and the before-mtime never set; the
commands after `;` still ran, `sqlite3` created an empty scratch file and
`motodiag db init` initialised that empty file, and the final comparison
against an unset variable printed "live mtime unchanged: NO". Checked
directly: the live `data/motodiag.db` was untouched — mtime 2026-09-22
16:25:43, 1,046 rows, max id 4616, an empty WAL. Re-run as a
`set -euo pipefail` bash script.

**Dry run** (fresh `.backup` copy, `MOTODIAG_DB_PATH=<copy> motodiag db
init`, the deploy's own entry point):

| | before | after | second load |
|---|---|---|---|
| `known_issues` | 1,046 (max id 4616) | **1,053** (ids 5337–5343, the seven rows) | 1,053 (`Loaded 0`) |
| schema | 66 | 66 | 66 |
| vehicles | 10 | 10 | 10 |
| hash of the 1,046 existing rows | `0c2d160326e766f4` | `0c2d160326e766f4` | `0c2d160326e766f4` |

Live file's mtime unchanged by the dry run. The live load follows the
merge, per the closeout sequence, with a backup to `~/backups/motodiag/`.

### 2026-09-24 — Close-out

Regression of record: **9089 passed, 0 failed, 0 skipped** at `c79ddec`
(52:16; 8 warnings, all `utcnow` deprecations in Phase 171's tests). The
collected count equals the floor raised at that commit. No bug fixes in
this phase: the census and sweep errors were caught in Step 0 before
anything they produced was used, and nothing committed later failed.

v1.1 written; ROADMAP row closed ✅ (104 words by `roadmap_words.py`);
`implementation.md` history row added and version 0.13.77 → 0.13.78; both
documents moved to `completed/`. The live load follows the merge.

### 2026-09-24 — Merged and deployed

Merged `8d1e29a`, pushed; the push guard's close-out check passed.

**Live load**, on `master` at `8d1e29a`, `bash` `set -euo pipefail`:

| | before | after |
|---|---|---|
| `known_issues` | 1,046 (max id 4616) | **1,053** (ids 5337–5343) |
| schema / vehicles | 66 / 10 | 66 / 10 |
| hash of the 1,046 existing rows | `0c2d160326e766f4` | `0c2d160326e766f4` |

Backup `~/backups/motodiag/motodiag_pre354_20260924_163732.db`, md5
`2169f020e84919b86c4af0b1302ba04f` equal to the live file before the load.
The script's `integrity_check` did not run — `sqlite3 -readonly` cannot
create the `-shm` a WAL-mode file needs (error 14), and a failure inside a
command substitution does not trip `set -e` — so it was run on a scratch
copy of the backup: `ok`, 1,046 rows, md5 unchanged. `cp -p` had kept the
live file's 2026-09-22 mtime on the backup, which would make retention
(by mtime) prune the newest backup first; touched to its creation time,
md5 unchanged. Retention to five removed `motodiag_pre255_143025.db`
(2026-09-21), the oldest.

**Smoke, on the live database:** PCX150, Agility 50 and Zuma 125 each get
their row at tier `model`; a Gold Wing sees the two Honda rows only at
`make_other_model`.

`verify_phase.sh 354 c79ddec 8d1e29a`: checks 2–13 clean; check 1's only
open item was this handoff, committed with this entry; check 4's three
hits are prose about the sweep's placeholder answers, not stubs.

## Refuter pass

Four refuters on Opus, one per maker group, each opening every cited page itself (text and, where
OCR was weak, rendered page images). Reports: `~/research/motodiag/354_step0/refute_*.md`.
`uncertain` claims are recorded as killed as written: each was rewritten or dropped.

SYM refuter's scope note: Every page below was read in full as extracted text: Jet pp. 59, 136-148; Fiddle pp. 1-3, 55, 128-138; Symply pp. 1-3, 14, 158-170; Joyride p. 2, pp. 170-182. The Symply cover (p. 1) was also viewed as an image. Searches were run across all extracted pages of the Joyride and Jet manuals for `illumination | lighting coil | light coil | charging coil Y – Y` (Joyride: 3 hits, all p. 178, and no illumination or lighting coil; Jet: 9 hits on pp. 143-144, which shows the search finds a lighting coil where one is printed) and across all Symply pages for `symply` (0 hits).

| claim | verdict | quote | source |
|---|---|---|---|
| [Honda] PCX: the manual is for the PCX150 | kept | "This manual describes the service procedures for the PCX150." | PCX SM, How to use this manual, PDF p.3 |
| [Honda] PCX: PGM-FI | kept | "FUEL Type PGM-FI (Programmed Fuel Injection)" | PCX SM 1-6 (PDF p.12), same on PDF p.13 |
| [Honda] PCX: covers "'13 model" and "After '13 model" | kept | "Current leakage '13 model 0.1 mA max. / After '13 model 0.4 mA max." | PCX SM 1-11 (PDF p.17); also 20-8 (PDF p.394) |
| [Honda] PCX: `year_start` 2013 with no `year_end` (row applies to every PCX150 from 2013 on) | killed (rewritten) | "Displacement *2 9.1 cu-in (149 cm3)" / "Bore x stroke 2.26 x 2.28 in (57.3 x 57.9 mm)" / "Final reduction 9.854" (2020 PCX150) vs SM "Displacement 153 cm3 (9.3 cu-in)" / "Bore and stroke 58.0 x 57.9 mm" / "Final reduction 10. 751 (54/17 X 44/13)" | 2020_PCX150.pdf owner's manual p.127 (PDF p.129) vs PCX SM 1-7 (PDF p.13). 2015 OM ("Type KF18", 153 cm3, final 10.751, GTZ8V) matches the SM's After '13 edition. The SM prints no date of issue and no model-year range beyond "After '13". |
| [Honda] PCX: "Charging system Triple phase output alternator" | kept | "Charging system Triple phase output alternator" | PCX SM 1-6 (PDF p.12); also After '13 page PDF p.13 |
| [Honda] PCX: "Lighting system Battery" | kept | "Lighting system Battery" | PCX SM 1-6 (PDF p.12) |
| [Honda] PCX: "The scooter has alternator/starter. The alternator/starter has alternator and starter functions." | kept | "The scooter has alternator/starter. The alternator/starter has alternator and starter functions." | PCX SM 20-4 (PDF p.390) |
| [Honda] PCX: "The regulator/rectifier is built into the ECM." | kept | "• The regulator/rectifier is built into the ECM." | PCX SM 20-4 (PDF p.390) |
| [Honda] PCX: no separate regulator to unplug or replace (manual shows no separate reg/rec part) | kept | "3. Current Leakage Test Without Regulator/rectifier built in ECM" | PCX SM 20-6 (PDF p.392). Search: "regulator" (case-insens.) over all 436 page texts = 4 pages: p.390, p.392 (charging), p.105/106 ("Faulty pressure regulator (fuel pump)"). Positive control: the search finds the 20-4 line. No separate reg/rec anywhere. |
| [Honda] PCX: tree disconnects "ECM 3P (Black) and ECM 5P connectors" | kept | "- ECM 3P (Black) connector (page 4-49). / - ECM 5P connector (page 4-49)." | PCX SM 20-6 (PDF p.392) |
| [Honda] PCX: the tree "ends 'YES - Faulty regulator/rectifier in ECM.'" | killed (uncertain as written; rewritten) | "YES - Faulty regulator/rectifier in ECM." | PCX SM 20-6 (PDF p.392). Quote verbatim, but it is the YES branch of step 3; the tree continues to steps 4-6 ending "YES - Replace the ECM with a new one and recheck." |
| [Honda] PCX: leakage threshold "below 0.1 mA" (fix step 2) | killed (rewritten) | "SPECIFIED CURRENT LEAKAGE: '13 model: 0.1 mA max. After '13 model: 0.4 mA max." | PCX SM 20-8 (PDF p.394); 1-11 (PDF p.17). The flow chart on 20-6 (PDF p.392) does say "Is the current leakage below 0.1 mA?" for both, so the row copies the chart but states a spec that is wrong for After '13 machines. |
| [Honda] PCX: "if it falls, the regulator/rectifier in the ECM is faulty" (fix step 3) | kept | "Recheck the battery current leakage. Is the current leakage below 0.1 mA? YES - Faulty regulator/rectifier in ECM." | PCX SM 20-6 (PDF p.392) |
| [Honda] PCX: standard "Measured BV < Measured CV < 15.5 V" (p. 20-9) | kept | "STANDARD: Measured BV < Measured CV < 15.5 V" | PCX SM 20-9 (PDF p.395; label lost in OCR, placed by 20-8 on PDF p.394, 20-10 on PDF p.396, and 20-6's "Measure the charging voltage (page 20-9)") |
| [Honda] PCX: at 5,000 rpm with headlight on high beam | kept | "With the headlight on high beam, restart the engine. Measure the voltage on the multimeter when the engine runs at 5,000 rpm." | PCX SM 20-9 (PDF p.395) |
| [Honda] PCX: standard is relative to battery voltage "rather than a fixed window" | kept | "STANDARD:Measured BV < Measured CV< 15.5 V • BV = Battery Voltage" | PCX SM 20-6 (PDF p.392). Search for any fixed charging voltage (`1[45].[0-9] V`) over the whole PCX text: 2 hits, both this 15.5 V line. Upper bound is fixed, lower bound is the battery. |
| [Honda] PCX: stator at ECM 3P (Black), Red/yellow-Red/white, Red/yellow-Red/blue, Red/white-Red/blue, 0.03-0.20 ohm at 20 C | kept | "Is the resistance within 0.03 - 0.20 .Q (20 °C/68 °F)?" | PCX SM 6-6 (PDF p.168) |
| [Honda] PCX: failure means "Replace the alternator/starter with a new one" | kept | "NO - Replace the alternator/starter with a new one and recheck." | PCX SM 6-6 (PDF p.168) |
| [Honda] PCX: stator check as a charging-diagnosis step (fix step 5) | killed (uncertain as written; rewritten) | "Alternator/starter does not turn" … "7. Stator Coil Circuit Inspection" | PCX SM 6-5/6-6 (PDF p.167-168). The check is in the ELECTRIC STARTER tree; the charging tree (20-6) has no stator step (steps: battery, leakage, leakage w/o ECM, charging voltage, starter/charging relay, relay line). |
| [Honda] PCX: "Alternator Capacity 0.343 kW/5,000 rpm" | kept | "Alternator Capacity 0.343 kW/5,000 rpm" | PCX SM 1-11 (PDF p.17); 20-5 (PDF p.391). One value for both editions. |
| [Honda] PCX: warning "The alternator/starter could suddenly start when the ignition switch is turned ON, causing serious injury." | kept | "The alternator/starter could suddenly start when the ignition switch is turned ON, causing serious injury." | PCX SM ALTERNATOR/STARTER general (PDF p.293; label OCR'd as "1", chapter 14) |
| [Honda] PCX: "Honda's procedure ends at the ECM or the starter/charging relay" (fix step 6) | killed (uncertain as written; rewritten) | "YES - Faulty battery." / "NO - • Shorted wire harness • Faulty ignition switch" | PCX SM 20-6 (PDF p.392). Tree also terminates at battery, harness, ignition switch and wiring. |
| [Honda] PCX: causes list (reg/rec in ECM, alternator/starter, starter/charging relay, battery) | kept | "NO - Faulty starter/charging relay" | PCX SM 20-6 (PDF p.392) |
| [Honda] PCX: page headers name another model | kept | "BATTERY/CHARGING SYSTEM" | PCX SM PDF p.390-396; no other model names anywhere ("PCX150" is the only model string) |
| [Honda] CHF50: manual is for the CHF50 | kept | "This service manual describes the service procedures for the CHF50." | CHF50 SM, How to use, PDF p.3 (Date of Issue: July, 2007) |
| [Honda] CHF50: "'02 - '05 model" and "After '05" editions | kept | "Curb weight ( ' 0 2 - '05 model) (After'0 5 model)" | CHF50 SM 1-5 (PDF p.9); TOC "FUEL SYSTEM SPECIFICATIONS {'02 - '05 model) … (After '05 model)" PDF p.5 |
| [Honda] CHF50: it is "the Metropolitan" | killed (uncertain as written; dropped) | "This service manual describes the service procedures for the CHF50." ("metropolitan": 0 hits in 319 pages) | CHF50 SM, PDF p. 3 |
| [Honda] CHF50: carburetted, CV carburettor | kept | "CV (Constant Velocity) type , with flat valve" | CHF50 SM 1-5 (PDF p.9). Search "PGM-FI / fuel inject / injector" = 0 pages; "carburetor" = 32 pages. It has an electric fuel pump ("FUEL PUMP FLOW CAPACITY", 1-9) but that does not contradict carburetted. |
| [Honda] CHF50: "Starter ACG" | kept | "Starter ACG" | CHF50 SM 1-5 (PDF p.9), Starting system value |
| [Honda] CHF50: "Triple phase output alternator" | kept | "Triple phase output alternato r" | CHF50 SM 1-5 (PDF p.9) |
| [Honda] CHF50: lighting system on the battery | kept | "Lighting system … Battery" | CHF50 SM 1-5 (PDF p.9), columns split by OCR; 4th ELECTRICAL row |
| [Honda] CHF50: "combined alternator/starter" | kept | "This scooter u s es a combined alternator/starter." | CHF50 SM 20-3 (PDF p.310) |
| [Honda] CHF50: "The alternator operates as a 3-phase AC generator" | kept | "T he alternator o p e r a t es as a 3-phase AC generator." | CHF50 SM 20-3 (PDF p.310) |
| [Honda] CHF50: ECM adjusts stator current to start and "to increase charging current under 3,500 rpm to enhance charging capability" | kept | "The ECM adjusts current to the stator coil to turn the flywheel when starting , and to increase charging current under 3,500 rpm to enhance charging capability." | CHF50 SM 20-3 (PDF p.310) |
| [Honda] CHF50: the carburetted machine has an ECM (and reg/rec is in it) | kept | "• T he regulator/rectifier is located in the ECM." | CHF50 SM 15-3 (PDF p.251); also PDF p.257 |
| [Honda] CHF50: charging coil 0.05-0.5 ohm at 20 C | kept | "Is the alternator charging coil resistance within 0.05 - 0.5 Q (20°C/68°F)?" | CHF50 SM 15-5 (PDF p.253); 15-4 (PDF p.252); 15-8 (PDF p.256) |
| [Honda] CHF50: correct reg/rec system inspection on ECM side → "Faulty ECM" | kept | "Are the results of checked continuity and resistance correct? YES - F a u l ty ECM." | CHF50 SM 15-5 (PDF p.253) |
| [Honda] CHF50: "Measured battery voltage < Measured charging voltage < 15.5 V" | kept | "Measured battery voltage < Measured charging voltage < 15.5 V" | CHF50 SM 15-5 (PDF p.253) |
| [Honda] CHF50: 5,000 rpm, headlight high beam | kept | "With the headlight on high beam, restart the engine. Measure t he v o l t a ge o n t he m u l t i m e t er w h en t he engine runs at 5,000 rpm." | CHF50 SM 15-8 (PDF p.256) |
| [Honda] CHF50: 190 W at 5,000 rpm | kept | "190W/5,000 r pm" | CHF50 SM 15-4 (PDF p.252); also 1-9 (PDF p.13) |
| [Honda] CHF50: leakage below 0.1 mA; disconnect ECM 6P; fall → faulty ECM | kept | "Disconnec t th e 6P connecto r o f the E CM … Is the current leakage below 0.1 mA? … YES - F a u l ty ECM." | CHF50 SM 15-5 (PDF p.253); one value "0.1 mA m a x." on 15-4 for both editions |
| [Honda] CHF50: cause "Faulty main relay or wiring" | kept | "NO - • F a u l ty mai n rela y or relate d circui t (pag e 1 5 - 1 1 )." | CHF50 SM 15-5 (PDF p.253) |
| [Honda] CHF50: "Turn the ignition OFF before servicing the alternator/starter" | kept | "• A l w a ys turn off the ignition switch before disconnecting any electrical component." | CHF50 SM 15-3 (PDF p.251). (The PCX's "could suddenly start" warning is not claimed for the CHF50; fine.) |
| [Honda] CHF50: "The standard matches the injected PCX150's" | kept | CHF50 "Measured BV < Measured CV < 15.5 V" = PCX "Measured BV < Measured CV < 15.5 V" | CHF50 SM 15-8 (PDF p.256); PCX SM 20-9 (PDF p.395) |
| [Honda] NCW50: "none of its owner's manuals read for this entry states its charging system" | kept | "Your vehicle has a maintenance-free type battery." (battery only; regulat/alternator/charging system/ACG/stator/generator give 0 relevant hits in the 2018, 2020 and 2023-2026 manuals; the same grep finds "regulator" in the PCX SM) | NCW50 2020 owner's manual 31GJB640, p. 56 |
| [Honda] CHF50: page headers name another model | kept | "BATTERY/CHARGING S Y S T EM" | CHF50 SM PDF p.251-256; "TECHNICAL FEATURES" PDF p.310 |
| [Kymco/Yamaha] Kymco: Agility regulator/rectifier type is "Single-phase half-wave SCR" | kept | "Type Single-phase half-wave SCR" | Agility 50 SM, 14-2, PDF p.153 (header AGILITY 50) |
| [Kymco/Yamaha] Kymco: Agility has two outputs, "Lighting 13.1±0.5V" and "Charging 14.5±0.5V/5000rpm" | kept | "Lighting 13.1±0.5V" / "Charging 14.5±0.5V/5000rpm"; the Lighting cell also holds "13.1～13.9V/5000rpm (Electric tester, tachometer)" | Agility 50 SM, 14-2, PDF p.153 (image) |
| [Kymco/Yamaha] Kymco: lighting coil "Yellow～Green 0.1～1.0" ohm at 20 C | kept | "Lighting coil resistance (20℃) Yellow～Green 0.1～1.0Ω" | Agility 50 SM, 14-2, PDF p.153 |
| [Kymco/Yamaha] Kymco: charging coil "White～Green 0.2～1.2" ohm | kept | "Charging coil resistance (20℃) White～Green 0.2～1.2Ω" | Agility 50 SM, 14-2, PDF p.153 |
| [Kymco/Yamaha] Kymco: capacity 0.144 kW at 5,000 rpm | kept | "Capacity 0.144KW/5000rpm" | Agility 50 SM, 14-2, PDF p.153 |
| [Kymco/Yamaha] Kymco: Agility battery 12V-4Ah | kept | "Capacity/Model 12V−4AH" | Agility 50 SM, 14-2, PDF p.153 |
| [Kymco/Yamaha] Kymco: lighting side measured on AC range at headlight wire coupler | kept | "Measure the voltage with the electric tester in the AC range." (figure label "Headlight Wire Coupler") | Agility 50 SM, 14-4, PDF p.155 (header AGILITY 50) |
| [Kymco/Yamaha] Kymco: "so a DC reading there says nothing about the lighting coil" | killed (uncertain as written; rewritten) | the row's own inference; the manual only prescribes the AC range and does not discuss DC readings | Agility 50 SM, 14-4, PDF p.155 |
| [Kymco/Yamaha] Kymco: Agility's yellow wire is its lighting coil | kept | "Between lighting wire (yellow) and engine ground" ; "Measure the resistance between the A.C. generator yellow wire and engine ground ... Replace the A.C. generator lighting coil" | Agility 50 SM, 14-5 PDF p.156 (header AGIKITY 50), 14-6 PDF p.157 (AGILITY 50) |
| [Kymco/Yamaha] Kymco fix step 2: lighting output on AC range at headlight coupler is 13.1 +/- 0.5 V | killed (rewritten) | the test at the headlight coupler gives its own figure: "LIGHTING SYSTEM LIMIT VOLTAGE INSPECTION ... Limit Voltage:1 2 ～14V/ (5000rpm max.)"; the spec table's lighting cell gives two figures, "13.1～13.9V/5000rpm" and "13.1±0.5V" | Agility 50 SM, 14-4 PDF p.155; 14-2 PDF p.153 |
| [Kymco/Yamaha] Kymco fix step 2: charging output 14.5 +/- 0.5 V at 5,000 rpm | kept | "Charging 14.5±0.5V/5000rpm"; 14-4 current test "Limit Voltage/Current:1 4～15V/0.5A max. (5000rpm max.)" | Agility 50 SM, 14-2 p.153; 14-4 p.155 |
| [Kymco/Yamaha] Kymco: People S 250 has no lighting coil in its specification | kept | the 16-2 spec lists only "A.C. Generator Charging coil resistance (20℃) Yellow ～Yellow 1.6 ～2.5Ω". A search of all 243 pages for "lighting coil", "single-phase", "half-wave" and "three-phase" found 0 hits. Positive control: the same search finds "Single-phase half-wave" in the Agility text. | People S 250 SM, 16-2, PDF p.211; whole book |
| [Kymco/Yamaha] Kymco: People fault list names "Open circuit between AC generator 3 yellow wires" | kept | "Open circuit between AC generator 3 yellow wires" (split across a line) | People S 250 SM, 1-30, PDF p.33 (header PEOPLE/PEOPLE S 250) |
| [Kymco/Yamaha] Kymco: People "Charging coil resistance (20C) Yellow ~Yellow 1.6 ~2.5" ohm | kept | "Charging coil resistance (20℃) Yellow ～Yellow 1.6 ～2.5Ω" | People S 250 SM, 16-2, PDF p.211 |
| [Kymco/Yamaha] Kymco: People "Capacity 180W/5000rpm" | kept | "Capacity 180W/5000rpm" | People S 250 SM, 16-2, PDF p.211 |
| [Kymco/Yamaha] Kymco: People "Regulator/Rectifier Limit voltage 14.5±0.5V" | kept | "Regulator/Rectifier Limit voltage 14.5±0.5V" | People S 250 SM, 16-2, PDF p.211 |
| [Kymco/Yamaha] Kymco: People battery 12V10AH | kept | "Capacity 12V10AH" | People S 250 SM, 16-2, PDF p.211 |
| [Kymco/Yamaha] Kymco: People's three yellow wires are its generator (three-phase) | kept | charging circuit drawn "Y Y Y" from a three-winding "A.C.G." to "REG REC"; the rectifier diagram on 16-6 shows three inputs into a six-diode bridge | People S 250 SM, 16-1 PDF p.210 (image), 16-6 PDF p.215 (image) |
| [Kymco/Yamaha] Kymco: the two books "share a maker and a carburettor" | kept | People: "Fuel System Carburetor", "Type CVK", "Venturi dia. 30 equivalent"; Agility: "Type CVK", "Venturi dia.(mm) φ17equivalent". Both are carburetted, but the carburettors are different. | People S 250 SM 1-2 PDF p.5; Agility 50 SM 1-2 PDF p.3 |
| [Kymco/Yamaha] Kymco: every figure is from pages headed AGILITY 50 | kept | 14-2 and 14-4 read "AGILITY 50". No figure is taken from 14-5 or 14-6 (those carry the yellow-wire identity, and 14-5 reads "AGIKITY 50"). | Agility 50 SM, PDF pp.153, 155 |
| [Kymco/Yamaha] Yamaha: the manual is for a fuel-injected machine | kept | "this model has adopted an electronically controlled fuel injection(FI)" | YW125Y SM, PDF p.9 |
| [Kymco/Yamaha] Yamaha: the machine is the "Zuma 125" | killed (uncertain as written; rewritten) | the manual names it only as "Model : YW125Y_" and "YW125Y 2009 SERVICE MANUAL"; "Zuma" appears on 0 of 338 pages | YW125Y SM, PDF pp.1-2 |
| [Kymco/Yamaha] Yamaha: wiring diagram labelled 'YW125Y' | kept | "YW125Y WIRING DIAGRAM" | YW125Y SM, PDF p.337 |
| [Kymco/Yamaha] Yamaha: "System type AC magneto", model 5S9 (T-MORIC), "Nominal output 14V 170W/5000r/min" | kept | "System type AC magneto"; "Model (manufacturer) 5S9 (T-MORIC)"; "Nominal output 14V 170W/5000r/min" | YW125Y SM, 2-15, PDF p.35 (image) |
| [Kymco/Yamaha] Yamaha: rectifier/regulator SH640E-11 (TAIGENE), "No load regulated voltage 14.1 ~ 14.9V", "Rectifier capacity 25A" | kept | "SH640E-11 (TAIGENE)"; "No load regulated voltage 14.1 ~ 14.9V"; "Rectifier capacity 25A" | YW125Y SM, 2-15, PDF p.35 |
| [Kymco/Yamaha] Yamaha: YT7B-BS battery, 12V 6.5AH | kept | "YT7B-BS (YUASA)"; "Battery voltage capacity 12V 6.5AH" | YW125Y SM, 2-15, PDF p.35 |
| [Kymco/Yamaha] Yamaha: "Stator coil resistance/color 0.56 ~ 0.84" ohm, white-white | kept | "Stator coil resistance/color 0.56 ~ 0.84Ω at 20°C (68°F) /white - white" (Charging system block, Standard column) | YW125Y SM, 2-15, PDF p.35 (image) |
| [Kymco/Yamaha] Yamaha: troubleshooting measures three white pairs, "Stator coil resistance 0.28 ~ 0.42" ohm | kept | "Positive tester probe → white ① Negative tester probe → white ②" (and ①-③, ②-③); "Stator coil resistance 0.28 ~ 0.42 Ω at 20°C (68°F)" | YW125Y SM, 7-28, PDF p.316 (image) |
| [Kymco/Yamaha] Yamaha: the two figures conflict (same basis, not per-coil vs per-pair) | kept | both pages measure between two white leads ("/white - white" on 2-15; white-to-white pairs on 7-28). The manual gives no other stator figure (a search for "stator" finds only 2-15 and 7-28 with values), names one model/year ("YW125Y 2009") and one stator (5S9). Note: 0.28-0.42 is exactly half of 0.56-0.84, the ratio of a star winding's per-phase to line-to-line resistance, which may explain the error, but neither page says "per coil". | YW125Y SM, PDF pp.35, 316 |
| [Kymco/Yamaha] Yamaha: a failed reading means "Replace the crankshaft position sensor/stator coil assembly" | kept | "Replace the crank-shaft position sensor/ stator coil assembly." | YW125Y SM, 7-28, PDF p.316 |
| [Kymco/Yamaha] Yamaha: 0.6 ohm passes 2-15 and fails 7-28 | kept | "0.56 ~ 0.84Ω" and "0.28 ~ 0.42 Ω" | YW125Y SM p. 2-15 (PDF p. 35), p. 7-28 (PDF p. 316) |
| [Kymco/Yamaha] Yamaha: order main fuse, battery, charging voltage, stator coil resistance, wiring (p. 7-27) | kept | "1. main fuse 2. battery 3. charging voltage 4. stator coil resistance 5. wiring connections (of the entire charging system)" | YW125Y SM, 7-27, PDF p.315 |
| [Kymco/Yamaha] Yamaha: the flow "ends in 'Replace the rectifier/regulator.'" (cited p. 7-27) | kept | "Replace the rectifier/ regulator." is on 7-28, not 7-27 | YW125Y SM, 7-28, PDF p.316 |
| [Kymco/Yamaha] Yamaha fix step 3: "A reading between 0.42 and 0.56 ohm falls between the manual's two figures ... do not condemn ... on one page's figure alone" | killed (rewritten) | a reading in 0.42-0.56 is outside BOTH "0.28 ~ 0.42 Ω" and "0.56 ~ 0.84Ω", so it fails both pages. The readings that one page passes and the other fails are 0.28-0.42 and 0.56-0.84. | YW125Y SM, 2-15 p.35; 7-28 p.316 |
| [Kymco/Yamaha] Yamaha fix step 4: no-load regulated voltage 14.1-14.9 V | kept | "No load regulated voltage 14.1 ~ 14.9V"; the troubleshooting check on 7-27 uses a different figure, "Charging voltage 14 V at 5000r/min" | YW125Y SM, 2-15 p.35; 7-27 p.315 |
| [SYM] The Jet manual covers the JET 50/100 series and the JET EURO 50/100 series | kept | "JET 50/100 and JET Euro 50/100 series" | Jet, front matter, PDF p. 2-3 (grep hit) |
| [SYM] Jet 15-2 prints "Control voltage in headlight 12.6 - 13.6 V / 5000 rpm (JET 50/100)" | kept | "Control voltage in headlight 12.6 - 13.6 V / 5000 rpm (JET 50/100)" | Jet 15-2, PDF p. 137 |
| [SYM] Jet 15-2: "Control voltage in charging 14.0 - 15.0 V / 5000 rpm" | kept | "Control voltage in charging 14.0 - 15.0 V / 5000 rpm" | Jet 15-2, PDF p. 137 |
| [SYM] Jet battery 12V3Ah (15-2) | kept | "Capacity 12V3Ah" | Jet 15-2, PDF p. 137 |
| [SYM] (implied) 12.6-13.6 V is *the* Jet 50/100 headlight spec | killed (uncertain as written; rewritten) | 15-7 prints a different figure for the same test: "JET 50/100 series ... Control voltage: 12.0~14.0 V / 5000 rpm" (AC, blue + / green -) | Jet 15-7, PDF p. 142 |
| [SYM] Jet 15-8: "Charging coil (white - green): 0.2~1.0" ohm, for JET 50/100 | kept | "Voltage Regulator Inspection – JET 50/100 ... Charging coil (white - green): 0.2~1.0Ω" | Jet 15-8, PDF p. 143 |
| [SYM] Jet 15-8: "Illumination coil (yellow - green): 0.1~0.8" ohm, for JET 50/100 | kept | "Illumination coil (yellow - green): 0.1~0.8Ω"; the table above it on the same page gives: "Check charging /illumination coil (yellow to ground) if its resistance is within 0.2~0.8Ω"; the 6-2 table gives: "JET 50/100 series ... Y ... 0.2~0.8 Ω" | Jet 15-8, PDF p. 143; Jet 6-2, PDF p. 59 |
| [SYM] The white-green/yellow-green coil pair on 15-8 is Jet 50/100, not Jet Euro | kept | Section heading "Voltage Regulator Inspection – JET 50/100"; the Jet Euro has its own section "Inspection on SCR – JET EURO 50/100" on 15-9; 6-2 gives JET EURO only "Y/L" and "Y ... 0.4~0.8 Ω" | Jet 15-8/15-9, PDF pp. 143-144; 6-2, PDF p. 59 |
| [SYM] Jet Euro: "Inspection on SCR - JET EURO 50/100", "Charging coil Y - Y 0.4~0.8" ohm | kept | "Inspection on SCR – JET EURO 50/100 ... Charging coil Y – Y 0.4~0.8Ω" | Jet 15-9, PDF p. 144 |
| [SYM] Measured "between each yellow wire of the SCR" | kept | "Measure the resistance between each yellow wire of the SCR." | Jet 15-9, PDF p. 144 |
| [SYM] The manual lists a "Head Light Control Unit (Jet Euro only)" | kept | "Head Light Control Unit (Jet Euro only)" | Jet 15-1, PDF p. 136 |
| [SYM] The Jet Euro has no lighting coil | kept | 6-2 JET EURO table has only "Y/L ... 50~200Ω" and "Y ... 0.4~0.8 Ω"; the 15-7 Jet Euro headlight test is DC ("Measure direct current voltage") | Jet 6-2, PDF p. 59; 15-7, PDF p. 142 |
| [SYM] The Fiddle 50 manual is for the Fiddle 50 only | kept | "for the SANGANG Fiddle 50 series scooter"; "Sanyang Fiddle 50 scooters". It names no other model | Fiddle front matter, PDF pp. 2-3 |
| [SYM] Fiddle repeats the same coil pair (15-8) | kept | "Charging coil (white - green): 0.2~1.0Ω / Illumination coil (yellow - green): 0.1~0.8Ω"; same internal conflict: "charging /illumination coil (yellow to ground) ... 0.2~0.8Ω" | Fiddle 15-8, PDF p. 135 (6-2 PDF p. 55: "Y ... 0.2~0.8 Ω") |
| [SYM] Fiddle prints the same 12.6 ~ 13.6 V headlight control voltage (15-2) | kept | "Control voltage in headlight 12.6 ~ 13.6 V / 5000 rpm" (no model qualifier) | Fiddle 15-2, PDF p. 129 |
| [SYM] (fix step 2) Fiddle charging control voltage 14.0-15.0 V / 5000 rpm | kept | 15-2: "Control voltage in charging 14.0 ~ 15.0 V / 5000 rpm"; 15-6: "Control Charging Voltage: 14.5 V / 5000 rpm"; 15-7 headlight: "Control voltage: 12.0~14.0 V / 5000 rpm" | Fiddle 15-2/15-6/15-7, PDF pp. 129/133/134 |
| [SYM] Symply 16-3: "Lighting coil resistance (20C) Between yellow-green: 0.8 ±0.1" ohm | kept | "Lighting coil resistance (20℃) Between yellow-green: 0.8 ±0.1Ω" | Symply 16-3, PDF p. 159 |
| [SYM] Symply 16-3: "Charging coil resistance (20C) Between white-green: 0.6 ±0.1" ohm | kept | "Charging coil resistance (20℃) Between white-green: 0.6 ±0.1Ω" | Symply 16-3, PDF p. 159 |
| [SYM] The manual at sym_symply125.pdf is a Symply 125 manual | killed (uncertain as written; dropped) | The text never names the model: "for the SYM series motorcycle"; spec page: "MAKER SANYANG MODEL ABA", bore 52.4 x stroke 57.8 mm (≈125 cc). The cover shows a scooter whose badge cannot be read. 0 text hits for "symply" | Symply PDF pp. 2, 14; cover p. 1 |
| [SYM] Joyride manual covers Joyride 125/150/200 | kept | "for the Sanyang JOYRIDE 125/150/200 motorcycle" | Joyride Forward, PDF p. 2 |
| [SYM] Joyride: "Charging coil Y - Y 0.4 - 0.8" ohm | kept | "Inspection on SCR ... Charging coil Y – Y 0.4 – 0.8Ω" | Joyride 17-7, PDF p. 178 |
| [SYM] Joyride: "Control Charging Voltage: 15.0 + 0.5 V / 2000 rpm" | kept | "Control Charging Voltage: 15.0 + 0.5 V / 2000 rpm" | Joyride 17-6, PDF p. 177 (also 17-2, p. 173: "Control voltage in charging 15.0 + 0.5 V") |
| [SYM] The Joyride has no illumination/lighting coil | kept | The 17-5 charging circuit shows only "Yellow" x4 between the generator and the regulator rectifier; the only coil test is "Inspection on the Charging Coil" | Joyride 17-5/17-7, PDF pp. 176/178 |
| [SYM] "which yellow wire is which depends on the model, sometimes within one book" | kept | The Jet book gives JET 50/100 yellow as "Illumination coil (yellow - green)" (15-8) and JET EURO yellow-yellow as "Charging coil Y – Y" (15-9) | Jet 15-8/15-9, PDF pp. 143-144 |
| [SYM] "on a Jet 50/100, Fiddle 50 ... yellow is the illumination coil" | killed (uncertain as written; rewritten) | The same page names that winding two ways: "Check charging /illumination coil (yellow to ground) ... 0.2~0.8Ω" and "illumination coil (the yellow to ground) ... 0.1~0.8Ω". The ignition page also prints "Exciting (yellow - ground): 400~800Ω", although its CDI table puts the exciter on "Black/Red-Green" and 6-2 puts 400~800 on R/B | Jet 15-8, p. 143; 15-12, p. 147; Fiddle 15-8, p. 135; 15-11, p. 138 |
| [SYM] "on a ... Symply 125 yellow is the illumination coil" | kept | "Measure the resistance between the yellow wire on the alternator and frame ground ... Replace the alternator lighting coil"; 16-9: "Check illumination wire (yellow) to ground" | Symply 16-10/16-9, PDF pp. 166/165 |
| [SYM] "on a Jet Euro or Joyride it is the charging coil" | kept | Jet: "Charging coil Y – Y 0.4~0.8Ω"; Joyride: "Charging coil Y – Y 0.4 – 0.8Ω" | Jet 15-9, p. 144; Joyride 17-7, p. 178 |
| [SYM] (fix step 4) Y-Y 0.4-0.8 is measured "at the SCR or regulator connector" | kept | "between each yellow wire of the SCR"; the Joyride figure is labelled "Regulator rectifier" | Jet 15-9, p. 144; Joyride 17-7, p. 178 |
| [SYM] (fix step 5) "If parts and wiring are normal on a Jet Euro, the manual says replace the SCR" | kept | "If there is nothing wrong with parts and wiring, replace the SCR." (Joyride 17-7 prints the same sentence) | Jet 15-9, PDF p. 144 |
| [SYM] "the same copy Phase 254 cited" | killed (uncertain as written; rewritten) | "JET EURO 50/100 series" (the manual's own name; 254_implementation.md has 0 hits for 7326249, 7429958, Jet or Joyride, and 255_implementation.md line 693 is where it is cited) | SYM 7326249, PDF p. 59 |
| [SYM] Model list: Jet 50, Jet 100, Jet Euro 50, Jet Euro 100, Fiddle 50, Joyride 125/150/200 | kept | "JET 50/100 series", "JET EURO 50/100 series"; "Sanyang JOYRIDE 125/150/200" | SYM 7326249 PDF p. 59; SYM 7429958 PDF p. 2 |
| [SYM] Model list: Symply 125 | killed (uncertain as written; dropped) | "MAKER SANYANG MODEL ABA" ("symply": 0 hits) | manual filed as Symply 125, PDF p. 14 |
| [Piaggio/Vespa] Fly 50 4T manual lists a single-phase generator | kept | "Generator single-phase alternating current" | Fly 50 4T WM 633212, PDF p10 |
| [Piaggio/Vespa] Fly 50 battery 12V-9Ah | kept | "Battery 12V-9Ah" | Fly 50 4T, p10 |
| [Piaggio/Vespa] Stator Black-earth ~ 1 ohm | kept | "Stator : Black-earth ~ 1 Ω (Stator)" | Fly 50 4T, p54 |
| [Piaggio/Vespa] Open output approx. 25 - 35 V at 2,000 rpm | kept | "The voltage output at 2,000 rpm must be approx. 25 - 35V" (AC, Gray-Blue wire to earth, regulator connector detached) | Fly 50 4T, p55 |
| [Piaggio/Vespa] At least 13 V at idle with 1.5 - 2 A (charged battery) | kept | "Check the voltage at idle is at least 13V (charged battery) and the recharge current is 1.5 - 2A with the lighting system and the choke device excluded" (the row leaves out the condition that lights and choke are excluded) | Fly 50 4T, p56 |
| [Piaggio/Vespa] 14 - 14.5 V regulator threshold | kept | "current values of ≥ 5A may be found, with voltage readings of 14 - 14.5V (regulator threshold voltage)" (measured with lights, choke, stop light and horn on) | Fly 50 4T, p57 |
| [Piaggio/Vespa] Fly 125-150 three-phase alternator, same words | kept | "The recharge system is provided with a three phase alternator with permanent flywheel." | Fly 125-150 4T WM 633225, p73 |
| [Piaggio/Vespa] Beverly 125 has the same wording | kept | "The recharge system is provided with a three phase alternator with permanent flywheel." | Beverly 125 SSM 664602/664603, p73 |
| [Piaggio/Vespa] "The alternator is directly connected to the voltage regulator." (both manuals) | kept | "The alternator is directly connected to the voltage regulator." | Fly 125 p73; Beverly 125 p73 |
| [Piaggio/Vespa] 15A fuse to earth and battery positive (both) | kept | Fly: "directly connected to earth and to the battery positive passing through the 15A safety fuse"; Beverly: "directly connected to the ground lead and to the battery positive terminal passing through the 15A protection fuse (No. 7)" | Fly 125 p73; Beverly 125 p73 |
| [Piaggio/Vespa] "This system therefore requires no connection to the key switch." (in both manuals) | kept | "This system therefore requires no connection to the key switch." (on both pages) | Fly 125 p73; Beverly 125 p73 |
| [Piaggio/Vespa] Stator 0.7 - 0.9 ohm between yellow cables, insulated from ground | kept | "Ohm value: 0.7 ÷ 0.9 Ohm" / "Also check that all yellow cables are insulated from the ground connection." | Fly 125 p73; Beverly 125 p72 |
| [Piaggio/Vespa] Charged battery, lights off: "should not exceed 15.2 Volt." | kept | "With a perfectly charged battery and lights off, measure voltage at the battery poles with a high running engine. The voltage should not exceed 15.2 Volt." | Fly 125 p74; Beverly 125 p72 |
| [Piaggio/Vespa] Beverly figures belong to the 125 | kept | Figures from the manual titled "Beverly 125". The charging pages 72-73 carry no version split. The only "Version 250" text in the text layer is on the time-schedule pages (p241, p271), not on the charging pages. | Beverly 125, p72-73, p241 |
| [Piaggio/Vespa] Fly 125 vs 150 | kept | The charging pages are headed "Fly 125 - 150 4T" and give no per-displacement figure | Fly 125, p73-74 |
| [Piaggio/Vespa] The MP3 400 is injected | kept | "Ignition Electronic, inductive, high efficiency ignition, integrated with the injection system"; wiring key "1. Injection ECU" | MP3 400 i.e. SSM 664502, p11, p50 |
| [Piaggio/Vespa] MP3 "a three-phase generator with permanent magneto flywheel" | kept | "The recharge circuit is provided with a three-phase generator with permanent magneto flywheel." | MP3 400, p76 |
| [Piaggio/Vespa] MP3 regulator "Non-adjustable three-phase transistor" | kept | "Type Non-adjustable three-phase transistor" | MP3 400, p78 |
| [Piaggio/Vespa] MP3 14 - 15 V at 5,000 rpm | kept | "Voltage ranging between 14.0 and 15.0V at 5000 rpm." / "Voltage 14 ÷ 15V at 5000 rpm with lights off" | MP3 400, p77, p78 |
| [Piaggio/Vespa] MP3 stator 0.2 - 1 ohm between each yellow terminal and the other two | kept | "Measure the resistance between each of the yellow terminals and the other two. ... Resistance: 0.2 - 1 Ω" | MP3 400, p76-77 |
| [Piaggio/Vespa] MP3 fuse 30A | kept | "passing through the 30A protective fuse." | MP3 400, p76 |
| [Piaggio/Vespa] MP3 figures apply to both the i.e. and the RL | kept | "Voltage 14 ÷ 15V at 5000 rpm with lights off" (no i.e./RL split in the charging section) | MP3 400, p. 78 |
| [Piaggio/Vespa] "The manuals also say ... 'a good compromise ... idle stability. For this reason, it is very important that the idle speed is adjusted as prescribed.'" (this sentence follows the MP3 text) | killed (rewritten) | The full quote appears only in Fly 125 p73 and Beverly 125 p73. MP3 p76 stops at "a good compromise is achieved between generated power and idle stability." and carries no "For this reason..." sentence. The Fly 50 has no such text. | Fly 125 p73; Beverly p73; MP3 p76 |
| [Piaggio/Vespa] Fix step 5: "Set idle to specification before judging a three-phase system" (applied to the MP3 too) | killed (uncertain as written; rewritten) | "The recharge circuit is provided with a three-phase generator with permanent magneto flywheel." (no idle instruction follows in the MP3 section) | MP3 400, p. 76 |
| [Piaggio/Vespa] "Piaggio's workshop manuals print no chapter page numbers" | killed (rewritten) | "ELE SYS - 73" | Fly 125 p. 73 (also Fly 50 p. 55, Beverly p. 73, MP3 p. 77) |
| [Piaggio/Vespa] "Read from a third-party mirror copy ..., the same copy Phase 254 cited." | killed (rewritten) | Phase 254 cited "the Beverly Tourer 125 service station manual 665018" and "workshop manual 618162". This Beverly PDF is "SERVICE STATION MANUAL 664602 IT-664603 EN ... Beverly 125", a different document (known_issues_cvt.json row "Piaggio's belt limit..."; Beverly p1). Fly 50 633212 and Fly 125 633225 match the numbers 254 cites. The copy's identity (sha) was not checked. | Beverly 125 p1; known_issues_cvt.json |
| [Piaggio/Vespa] Model "Fly 50" | killed (uncertain as written; rewritten) | The manual is "MSS Fly 50 4T". A 2T Fly 50 exists and is not covered. | Fly 50 p1, p10 |
| [Piaggio/Vespa] Model "Fly 150" | kept | "Fly 125 - 150 4T"; "Chassis prefix (150) ZAPM42200" | Fly 125-150, p1, p8 |
| [Piaggio/Vespa] LX 50 generator "In alternate current with three output sections" | kept | "Generator In alternate current with three output sections". The same family's S 50 2T regulator connector has two separate magneto inputs, "2. Magneto flywheel (Grey-Blue)" and "8. Magneto flywheel (Yellow)", plus a separate ignition "RECHARGING COIL" (Red–Green 800 ÷ 1100 Ohm). So "three output sections" means three separate windings, not three-phase. The row implies nothing wrong here, but a reader could misread it. | LX 50 WM 633416 p10; S 50 2T p53, p61 |
| [Piaggio/Vespa] LX 50 battery 12V-4Ah | kept | "Battery 12V-4Ah" | LX 50 p10 |
| [Piaggio/Vespa] Lights on 13 - 14.5 V at 5000 rpm | kept | "Make sure that at 5000 rpm with the lights on that the regulation voltage is between 13V and 14.5V." | LX 50 p52 |
| [Piaggio/Vespa] Lights off at most 16 V | kept | "Make sure that at 5000 rpm with the lights off the regulation voltage is ï£ 16V." The rendered page image also prints "ï£". The ≤ reading rests on the next line: "If the regulation voltage is greater than >16V replace the regulator." | LX 50 p52 (image checked) |
| [Piaggio/Vespa] 1.5 - 2 A and 13 V at 3,000 rpm | kept | "Following the replacement, measure the current and the recharging voltage on the battery ends (FIG. B). The values detected must be 1.5 ÷ 2 A and 13 V at 3000 rpm." (a check after replacing the regulator under FAULT 3) | LX 50 p52 |
| [Piaggio/Vespa] S 50 pair, lights on | kept | "Check that the control voltage is between 13V and 14.5V at 5000 rpm with the lights on." | S 50 2T SSM 664787-95, p54 (image checked) |
| [Piaggio/Vespa] S 50 pair, lights off | kept | "Check that the control voltage is 16V at 5000 rpm with the lights off." | S 50 2T p54 |
| [Piaggio/Vespa] S 50 replace-above-16 V sentence | kept | "Replace the voltage regulator if control voltages are over >16V." | S 50 2T, p. 54 |
| [Piaggio/Vespa] Title and description: the lights-on/off test is "Vespa's 50 cc charging" | killed (uncertain as written; rewritten) | The pair sits under "FAULT 1", which answers fault "1) Blow out of the lighting system bulbs" (LX) / "1) Lighting system bulbs burn out" (S 50). It is a lighting-regulation check. The battery-charging check is FAULT 3 or 4 (13 V, 1.5 - 2 A at 3000 rpm, measured at the battery). | LX 50 p51-52; S 50 p54-55 |
| [Piaggio/Vespa] LX 125-150 and GTS: three-phase alternator sentence | kept | "The recharge system is provided with a three phase alternator with permanent flywheel" | LX 125-150 4T Euro 3 WM 633976, p. 73; GTS Super 300 ie (2008), p. 90 |
| [Piaggio/Vespa] LX 125-150 and GTS: alternator wired straight to the regulator | kept | "The alternator is directly connected to the voltage regulator." | 633976 p. 73; GTS p. 90 |
| [Piaggio/Vespa] Fuse 15A (LX) / 30A (GTS) | kept | LX: "passing through the 15A safety fuse"; GTS: "passing through the 30A protective fuse." | 633976 p73; GTS p90 |
| [Piaggio/Vespa] "on the LX 'This system therefore requires no connection to the key switch.'" | kept | Present on 633976 p73. Absent from GTS p90, and a grep of every GTS page for "key switch" finds no such sentence. The row scopes it correctly. | 633976 p73; GTS p90 |
| [Piaggio/Vespa] Title: "the LX 125-150 and GTS 300 use a three-phase alternator with no key-switch connection" | killed (rewritten) | "This system therefore requires no connection to the key switch." (in 633976 only; absent from the GTS section) | 633976 p. 73; GTS p. 90 |
| [Piaggio/Vespa] LX 125-150 stator 0.7 - 0.9 ohm, yellow cables insulated | kept | "Ohm value: 0.7 ÷ 0.9 Ohm" / "Also check that all yellow cables are insulated from the ground connection." | 633976 p74 |
| [Piaggio/Vespa] LX 125-150 ≤ 15.2 V with a charged battery and lights off | kept | "With a perfectly charged battery and lights off, measure voltage at the battery poles with a high running engine. The voltage should not exceed 15.2 Volt." | 633976 p74 |
| [Piaggio/Vespa] GTS regulator "Non-adjustable three-phase transistor" | kept | "Type Non-adjustable three-phase transistor" | GTS p92 |
| [Piaggio/Vespa] GTS stator 0.2 - 1 ohm | kept | "Resistance: 0.2 - 1 Ω"; "Resistance between terminals: 0.2 ÷ 1 Ohm" | GTS p91, p14 |
| [Piaggio/Vespa] GTS 450 W | kept | "STATOR Power: 450 W" | GTS p14 |
| [Piaggio/Vespa] GTS 14 - 15 V at 5,000 rpm with lights off | kept | "Voltage 14 ÷ 15V at 5000 rpm with lights off"; "ensure that the lights are all out ... Voltage ranging between 14.0 and 15.0V at 5000 rpm." | GTS p92, p91 |
| [Piaggio/Vespa] **"A lights-off reading on a 50 cc Vespa is allowed to run higher than on a 125; comparing it with the larger machines' ceiling would condemn a good regulator."** | killed (rewritten) | The two figures are not the same measurement. The 15.2 V figure is "measure voltage at the battery poles" with "a perfectly charged battery" and "a high running engine" (633976 p74). The 16 V figure is the FAULT 1 "regulation voltage" at 5000 rpm (LX 50 p52). FAULT 1 is the lighting-bulb fault, and the page names no measuring point and no battery state. The 50's own battery-side figure is "13 V at 3000 rpm" at "the battery ends" (p52). No page supports reading 16 V at the battery of a 50 as normal. | 633976 p74; LX 50 p51-52; S 50 p54-55 |
| [Piaggio/Vespa] Fix step 1: "replace the regulator only above 16 V" | killed (rewritten) | Both manuals also order regulator replacement in other cases. S 50 FAULT 4: "If the values detected are lower than those specified, replace the regulator." LX 50 FAULT 3: "replace the regulator because it is certainly inefficient, and replace the protection fuse." LX 50 FAULT 2 b: "If the tests do not reveal any anomalies, replace the regulator." | S 50 p55; LX 50 p52 |
| [Piaggio/Vespa] Fix step 4: "Do not judge a 50 cc Vespa against the larger machines' ceiling." | killed (rewritten) | "The voltage should not exceed 15.2 Volt." (battery poles, charged battery; the 50s' 16 V is a burnt-bulb regulation check) | 633976 p. 74; LX 50 633416 p. 52 |
| [Piaggio/Vespa] "Piaggio's workshop manuals print no chapter page numbers" | killed (rewritten) | "ELE SYS - 73" | Fly 125 p. 73 (also Fly 50 p. 55, Beverly p. 73, MP3 p. 77) |
| [Piaggio/Vespa] "the same copy Phase 254 cited" | killed (uncertain as written; rewritten) | "SERVICE STATION MANUAL Vespa S 50 2T" (reached after 254, per FOLLOWUPS lines 155-158; 254 cited Beverly 665018/618162, not this 664603) | S 50 2T, PDF p. 1 |
| [Piaggio/Vespa] Model "LX 50" | killed (uncertain as written; rewritten) | Manual 633416 is for the two-stroke: "Engine type Two-stroke, single cylinder Piaggio Hi-PER2". The LX 50 4T is not covered. | LX 50 p9 |
| [Piaggio/Vespa] Model "S 50" | killed (uncertain as written; rewritten) | The manual is "Vespa S 50 2T" only | S 50 p1 |
| [Piaggio/Vespa] Model "LX 150" | kept | "Vespa LX 125 - 150 4T Euro 3" | 633976 p8 footer |
| [Piaggio/Vespa] Model "GTS 300" | killed (uncertain as written; rewritten) | The manual is "Vespa GTS Super 300 ie (2008)" | GTS p7 |
