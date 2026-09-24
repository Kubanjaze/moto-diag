# Phase 353 — Small-engine carb service (single/twin-barrel) — phase log

**Status:** ✅ Complete (2026-09-24)
**Opened:** 2026-09-24

---

### 2026-09-24 — Opened after 354

Taken before 258 per `docs/handoffs/2026-09-24_354_closed.md`: Gate 14
queries a scooter for CVT, electrical and carb content, and carb (353) is
the last of the three not built. Read before acting: the handoff, ROADMAP
rows 353, 354 and 258, `ROADMAP_AUTHORITY.md` (353 is backend, 205+),
`354_implementation.md` (v1.1) and its phase log, FOLLOWUPS F149, F150,
F142, F127, F129.

Branch `phase-353` from `master` at `0b0ac2c`, in sync with `origin`.
`roadmap_check.py` exit 0; ROADMAP row to 🚧 before Step 0 at `ee4a979`,
pushed.

**Standing rules for this phase (operator, same as 354):** stop once after
Step 0 only for a real fork, otherwise log each decision here and carry
on; bulk reading through Subconscious, refute on Opus; the whole-tree
gates (191C F9 lint, 244G, finding_check B2) on every pre-commit run;
close-out through merge and push; a new dated handoff naming 258 next.

**Decision (logged, not asked):** 354's reading pipeline is reused with
the field list swapped (`~/research/motodiag/353_step0/`). Two changes,
each for a measured reason:

- **Every library PDF is extracted, not a name-filtered set.** 354's file
  name filter missed `honda/ruck_*.pdf` (the four Ruckus owner's manuals
  Phase 252 read), the budget `Lance_*` manuals and the Dio. Documents are
  then selected by carburettor vocabulary, and a document outside the
  class is excluded by what its own title page prints (KTM 950 Super
  Enduro R, YZF600RW, XR650L, Bonneville; the MP3 500 as injected).
- **354's extracted page text was not kept** (`354_step0/` holds the
  index and sweep output, not the page files), so extraction re-ran:
  271 PDFs, 264 unique, 246 extracted, 18 unreadable by pypdf, 14 with
  no text layer.

### 2026-09-24 — Step 0: extension, content only, no fork

Measurements S0-1..S0-13 are in the implementation doc. In short: Track M
holds no carburettor service. The corpus's only carburettor-service rows
are ten unsourced big-bike rows filed under one make and model each, so no
carburetted scooter reaches a row about its own carburettor. The row's
"Keihin/Mikuni" is true for the Piaggio four-strokes and the Vino, and
false for the two-strokes (Dell'Orto, Teikei). The Kymco, SYM and CHF50
service manuals name no maker.

**Decision (logged, not asked): no fork.** Every question had a default
354 set: one make per row, written from verified quotes, an older defect
filed rather than patched (D5), title-page identity. One apparent fork,
how to label owner's-manual-only rows, already has an answer: 252 and
253 label them `service-manual` and say in the text which document it
is. 353 follows that.

**Decision:** the XV250 stays out (D7). It is the class's only twin, its
owner's manual prints "BDS26 × 1" and then "float chambers" in the
plural, and one manual is not enough to settle that.

**Decision:** R8 (Genuine) is a ceiling item only. The one Genuine service
manual is PGO's "PA 100 / 125" and never names the Buddy (S0-12, 354's
R7).

**Sweep:** 41 documents, 1,300 facts, 1,207 verified, 7% dropped, every
call parsed first time.

### 2026-09-24 — Build: seven rows, four refuters, 32 claims killed

v1.0 committed and pushed at `7cb9a75` before any content was written.

Rows were drafted from the verified quotes, with every load-bearing page
re-read by hand first. They were then refuted on Opus by four agents (Honda,
Kymco + SYM, Piaggio + Vespa, Yamaha), each opening every cited page itself
and rendering pages where the text layer was doubtful. 178 claims tested:
146 kept, 32 killed ("uncertain" recorded as killed, since each was
rewritten). As in 354, no kill removed a row's subject. They were edition
scope, dropped steps, attribution and one identity. After the rewrite,
`check_quotes.py` (in `353_step0/`) found all 98 single-quoted passages in
their make's documents, compared on letters and digits because of the
CHF50's spaced text layer. A planted fake quote was reported missing.

**Two Step 0 statements were corrected by hand-reading, before refute:**
S0-9's SYM quote was cut short. The star note prohibits adjustment "by
unauthorized people", not outright. And Piaggio's "TAMPERPROOF SCREWS ARE
SUPPLIED WITH 125 CC MODELS" is printed on the intake-manifold page, not
the mixture-screw page. Both are recorded in v1.1's Deviations.

**Decisions (logged, not asked):**

- **R8 (Genuine) dropped.** Its one source, the Urbano 125 owner's manual's
  storage paragraph, is word for word the same as the Chicago Scooter
  Company's Bella Classic 50 manual (PDF p. 40 / p. 39). It is a generic
  paragraph, and too thin to ship.
- **The CHF50 row states its cover.** The Honda refuter rendered the
  image-only cover: "2002–2006", "CHF50/P/S METROPOLITAN™". Confirmed by
  rendering it again. The row stays modelled `CHF50`, so an injected
  NCW50 Metropolitan does not reach it at tier 0 (tested; a mutation that
  adds "Metropolitan" to the model column is caught). **Phase 354's CHF50
  charging row says the manual "prints the model only as CHF50, and it
  names no end year"**: filed as **F152**, not edited (354's content,
  F129).
- **The CHF50 row covers both editions' resets.** v1.0's draft gave only
  the after-'05 idle drop and left a replaced screw with no starting
  position. The '02–'05 highest-idle method and the after-'05 idle drop are
  both written out, and so is the asymmetric return from altitude (1/2 turn
  in going up, 1/4 turn out coming down, as printed on pp. 5-20 and 5-21).
- **Ruckus: "idle is the owner's only adjustment" narrowed.** Only the 2012
  edition gives an owner idle procedure (the search for "Adjusting the
  Engine Idle" finds it in 2012 alone). The later editions' emission
  sentence limits adjustment; it does not hand idle to the owner. The
  methanol change is dated "2022 or earlier" (2013–2021 not read).
- **The B 125-250 manual's Walbro columns removed from the Piaggio row.**
  Its 125 chassis prefix (ZAPM 28400) is not the Beverly 125 manual's
  (ZAPM 28900), and the Beverly frame number on its thermal-switch page
  matches its 250. So no model in the row's column is tied to it.
- **The Fly 50's automatic starter is its own**: "6 Ω ± 5 %", "max. time
  15 min" (ENG - 121), not the Fly 125–150's 20 Ω and 5 min. v1.0's draft
  applied the second to both.
- **"Fiddle III" removed from the SYM model column.** That manual prints
  only "MODEL XA05W-6", and the name came from its file name. This is 354's
  lesson (F150) found again, and the row names the manual by its model code.
- **Kymco: "factory pre-set" is the Agility 50 manual's claim only.** The
  People S 250 manual says to record the turns and says nothing of a preset.
- **Yamaha: methanol is "not recommended", not forbidden**, and "add fuel
  stabilizer (if available)" keeps its condition.

**Found and filed:** **F151**, the 80 `cross_platform_*` rows (Step 0,
D5). **F152**, 354's CHF50 sentence (above).

**Tests:** `tests/test_phase353_small_engine_carb_content.py`, 99 tests.
Break-it **14/14** (each mutation run with `__pycache__` cleared and
`-B`, the seed restored byte-identical after). 244G scanner over the
whole `tests/` tree: 0 hits. **A 255C pin moved**: the PCX tier table
168 → 170 retrieved and kept. The CHF50 and Ruckus carburettor rows reach
a PCX at `make_other_model`; tier `model` is unchanged at 12. Related
suites plus the four whole-tree gates: 946 passed and that one pin failed
before the move; 255C then passed 92/92.

### 2026-09-24 — Deploy dry run on a copy of the live database

`bash` with `set -euo pipefail` (354's lesson): a fresh `.backup` copy, then
`MOTODIAG_DB_PATH=<copy> motodiag db init`, the deploy's own entry point.

| | before | after | second load |
|---|---|---|---|
| `known_issues` | 1,053 (max id 5343) | **1,060** (ids 6397–6403, the seven rows) | 1,060 |
| schema / vehicles | 66 / 10 | 66 / 10 | 66 / 10 |
| hash of the 1,053 existing rows | `4ee85e6eb1af3e06` | `4ee85e6eb1af3e06` | — |

The live file's mtime was unchanged by the dry run.

### 2026-09-24 — Close-out

Regression of record: **9188 passed, 0 failed, 0 skipped** at `fb4a76d`
(52:35; 8 warnings, all `utcnow` deprecations in Phase 171's tests). The
collected count equals the floor raised at that commit. No bug fixes in
this phase: the Step 0 and draft errors were caught before commit, and
nothing committed later failed.

v1.1 written; ROADMAP row closed ✅; `implementation.md` history row added
and version 0.13.78 → 0.13.79; both documents moved to `completed/`. The
live load follows the merge.

### 2026-09-24 — Merged and deployed

Merged `78fbc67`, pushed; the push guard's close-out check passed. (The
first attempt, `git merge -F -`, is not supported by git and did nothing;
master stayed at `0b0ac2c` and the merge was re-run with a message file.)

**Live load**, on `master` at `78fbc67`, `bash` with `set -euo pipefail`:

| | before | after |
|---|---|---|
| `known_issues` | 1,053 (max id 5343) | **1,060** (ids 6397–6403) |
| schema / vehicles | 66 / 10 | 66 / 10 |
| hash of the 1,053 existing rows | `4ee85e6eb1af3e06` | `4ee85e6eb1af3e06` |

Backup `~/backups/motodiag/motodiag_pre353_20260924_183635.db`, taken by
`sqlite3 .backup` and touched to its creation time (354's retention
lesson). `integrity_check` was run on a scratch copy of it (354's WAL
lesson) and read `ok`. Retention to five removed
`motodiag_pre256_20260921_195822.db`, the oldest.

**Smoke, on the live database:** Ruckus, Agility 50, Fly 50 and Zuma 50
each get their row at tier `model`; a Gold Wing sees the two Honda rows
only at `make_other_model`.

`verify_phase.sh 353 fb4a76d 78fbc67`: checks 1–13 clean (check 2: no
code after the regression hash).

## Refuter pass

Four refuters on Opus, one per maker group, each opening every cited page itself (text, and rendered page images where the text layer was doubtful). Reports: `~/research/motodiag/353_step0/refute_*.md`. `uncertain` claims are recorded as killed as written: each was rewritten or dropped.

| claim | verdict | quote | source |
|---|---|---|---|
| [Honda] CHF50 row: the document names the machine CHF50 | kept | "This service manual describes the service procedures for the CHF50." | chf50_service_mirror.pdf PDF p. 3 |
| [Honda] CHF50 row: year_start 2002 | kept | "2002–2006 … SERVICE MANUAL … CHF50/P/S METROPOLITAN" (cover, image only) | chf50_service_mirror.pdf PDF p. 1 (no printed number) |
| [Honda] CHF50: p. 1-6 prints two fuel-system tables, '02-'05 and after '05 | kept | "FUEL SYSTEM SPECIFICATIONS (’02 - ’05 model)" / "FUEL SYSTEM SPECIFICATIONS (After ’05 model)" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50 '02-'05: carburettor NVK00E ([P type] NVK00F) | kept | "Carburetor identification number NVK00E [P type] NVK00F" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50: main jet #72 (both tables) | kept | "Main jet #72" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50: slow jet #35 | kept | "Slow jet #35 X #35" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50 '02-'05: pilot screw initial opening 2-3/4 out, [P type] 2-1/8 | kept | "Pilot screw initial opening 2-3/4 turns out [P type] 2-1/8 turns out" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50: float level 13 mm | kept | "Float level 13 mm (0.5 in)" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50: idle 2,000 ± 100 rpm | kept | "Idle speed 2,000 ± 100 rpm" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50: SE valve resistance quote | kept | "Starting enrichment (SE) valve resistance (20° C/68° F) 2.8 – 5.2 Ω" | chf50 PDF p. 10, printed 1-6; also PDF p. 107, printed 5-21 |
| [Honda] CHF50 after '05: same table except NVK00J ('06-'07) / NVK00K (after '07) and pilot 2-1/4 | kept | "Carburetor identification number ’06 – ’07 model NVK00J After ’07 model NVK00K … Pilot screw initial opening 2-1/4 turns out" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50: the manual names no carburettor maker | kept (text layer only) | "CV (Constant Velocity) type , with flat valve" (carburettor type, no maker; "keihin"/"mikuni" 0 hits in 319 pages) | chf50 PDF p. 9, printed 1-5 |
| [Honda] CHF50: "factory pre-set … unless the pilot screw is replaced" is an after-'05 statement (the row introduces it with "On the after '05 model") | killed | "PILOT SCREW ADJUSTMENT: ('02 - '05 model) • The pilot screw is factory pre-set and no adjustment is necessary unless the pilot screw is replaced." | chf50 PDF p. 104, printed 5-18 (the after-'05 copy is PDF p. 105, printed 5-19) |
| [Honda] CHF50 title: the pilot screw is "set by an idle drop" (unqualified, whole model) | killed | '02-'05 procedure: "6. Turn the pilot screw in or out slowly to obtain the highest engine speed. 7. Readjust the idle speed with the throttle stop screw." (no idle drop); "IDLE DROP PROCEDURE" appears only under "(After '05 model)" | chf50 PDF pp. 104–105, printed 5-18/5-19 |
| [Honda] CHF50 after '05: warm-up is ten minutes of stop-and-go riding | kept | "Stop and go riding for 10 minutes is sufficient." | chf50 PDF p. 105, printed 5-19 |
| [Honda] CHF50 after '05: find highest idle, turn in "until the engine speed drops by 50 rpm" | kept | "8. Turn the pilot screw in until the engine speed drops by 50 rpm." | chf50 PDF p. 106, printed 5-20 |
| [Honda] CHF50 after '05: "FINAL OPENING: 1/4 turns out" | kept | "9. Turn the pilot screw counterclockwise to final opening from the position obtained in step 8. FINAL OPENING: 1/4 turns out" | chf50 PDF p. 106, printed 5-20 |
| [Honda] CHF50: tachometer graduated in 50 rpm or finer | kept | "Use a tachometer with graduations of 50 rpm or smaller that will accurately indicate a 50 rpm change." | chf50 PDF p. 105, printed 5-19 (same on 5-18) |
| [Honda] CHF50: pilot-screw text cited to pp. 5-19, 5-20 | kept | "PILOT SCREW ADJUSTMENT : (After '05 model) IDLE DROP PROCEDURE" | chf50 PDF pp. 105–106, printed 5-19/5-20 |
| [Honda] CHF50: high-altitude quote "above 2,000 m (6,500 feet), the carburetor must be readjusted" | kept (quote truncated; continues "as described below to improve driveability and decrease exhaust emissions.") | "When the vehicle is to be operated continuously above 2,000 m (6,500 feet), the carburetor must be readjusted" | chf50 PDF p. 106, printed 5-20 |
| [Honda] CHF50: high-altitude text is after '05 only | kept | "HIGH ALTITUDE ADJUSTMENT (After '05 model)" (whole-document `altitude` hits: pp. 87 TOC, 106, 107 only) | chf50 PDF p. 106, printed 5-20; TOC PDF p. 87, printed 5-1 |
| [Honda] CHF50: HIGH ALTITUDE MAIN JET #70 | kept | "HIGH ALTITUDE MAIN JET: #70" | chf50 PDF p. 106, printed 5-20 |
| [Honda] CHF50: high-altitude pilot 1/2 turn in from factory preset | kept | "HIGH ALTITUDE PILOT SCREW OPENING: 1/2 turn in from the factory preset position" | chf50 PDF p. 106, printed 5-20 |
| [Honda] CHF50: pilot seat damage quote and "seats lightly" count before removal (p. 5-12) | kept | "Damage to the pilot screw seat will occur if the pilot screw is tightened against the seat." / "Turn the pilot screw in and record the number of turns it takes before it seats lightly." | chf50 PDF p. 98, printed 5-12 |
| [Honda] CHF50: compressed air, "a piece of wire will damage the carburetor body" (p. 5-13) | kept | "Cleaning the air and fuel passages with a piece of wire will damage the carburetor body." / "Blow open all air and fuel passages in the carburetor body with compressed air." | chf50 PDF p. 99, printed 5-13 |
| [Honda] CHF50 cause: "Jets or passages damaged by wire during cleaning" | killed (uncertain as written; rewritten) | "a piece of wire will damage the carburetor body" (the manual names the body, not the jets; jets are separately "easily … scored or scratched") | chf50 PDF pp. 98–99, printed 5-12/5-13 |
| [Honda] CHF50 cause: SE valve out of its 2.8–5.2 ohm range | kept | "STANDARD: 2.8 - 5.2 Ω (at 20°C/68°F) If the resistance is abnormal, replace the SE valve." | chf50 PDF p. 107, printed 5-21 |
| [Honda] CHF50 symptom: hard (cold) start linked to SE valve | kept | "Engine stall, hard to start, rough idling … Faulty starting enrichment (SE) valve" | chf50 PDF p. 91, printed 5-5 |
| [Honda] CHF50 cause: standard jetting used continuously above 2,000 m | kept | "When the vehicle is to be operated continuously above 2,000 m (6,500 feet), the carburetor must be readjusted" | chf50 PDF p. 106, printed 5-20 |
| [Honda] CHF50 fix 1: the two tables differ in carburettor number and pilot opening | kept | (see the two tables) "Pilot screw initial opening 2-3/4 turns out" vs "Pilot screw initial opening 2-1/4 turns out" | chf50 PDF p. 10, printed 1-6 |
| [Honda] CHF50 fix 2: SE valve 2.8–5.2 ohm at 20 C | kept | "STANDARD: 2.8 - 5.2 Ω (at 20°C/68°F)" | chf50 PDF p. 107, printed 5-21 |
| [Honda] CHF50 fix 3: seat lightly, record turns, never tighten | kept | "record the number of turns it takes before it seats lightly" | chf50 PDF p. 98, printed 5-12 |
| [Honda] CHF50 fix 4: compressed air, never wire | kept | "Blow open all air and fuel passages in the carburetor body with compressed air." | chf50 PDF p. 99, printed 5-13 |
| [Honda] CHF50 fix 5: after '05 replaced screw = warm up, set idle, highest idle, drop 50, out 1/4, reset idle | killed (a condition dropped) | "1. Turn the pilot screw clockwise until it seats lightly, and then back it out to the specification given. … INITIAL OPENING: 2-1/4 turns out" and "7. Lightly open the throttle 2 or 3 times, then adjust the idle speed"; the first idle is "TENTATIVE IDLE SPEED: 2,000 ± 100 rpm" | chf50 PDF pp. 105–106, printed 5-19/5-20 |
| [Honda] CHF50 fix 6: above 2,000 m, #70 and 1/2 turn in | kept (incomplete: omits the return below 1,500 m, see below) | "HIGH ALTITUDE MAIN JET: #70" / "1/2 turn in from the factory preset position" | chf50 PDF p. 106, printed 5-20 |
| [Honda] Ruckus row: four manuals read, 31GGA6300 (2012), 31GGA720 (2022), 31GJP600 (2024), 31GJP610 (2025) | kept | "31GGA630 2012 NPS50 Owner’s Manual" (2012); "20222022 NPS50 Owner’s Manual" (2022 cover); "2024 RUCKUS"; "2025 RUCKUS" | 2012 PDF p. 101 (printed 99); 2022/2024/2025 PDF p. 1 |
| [Honda] Ruckus row: model "Ruckus, NPS50" | kept | "2024 Ruckus Owner’s Manual" / "2022 NPS50 Owner’s Manual" (2012 text says only "NPS50"; "Ruckus" is in its PDF metadata title "2012 Ruckus (NPS50) Owner's Manual") | 2024 PDF p. 94; 2022 PDF p. 94 (printed 90); 2012 PDF metadata |
| [Honda] Ruckus: year window 2012–2025 | kept (bounded by the editions read; 2013–2021 unread) | "2025 RUCKUS" | 2025 PDF p. 1 |
| [Honda] Ruckus: 2022–2025 say the emission system allows no adjustment except idle with the throttle stop screw | kept (all three editions) | "The exhaust emission control system consists of appropriate carburetor settings, and no adjustment should be made except idle speed adjustment with the throttle stop screw." | 2022 PDF p. 88 (printed 84); 2024 PDF p. 88 (printed 84); 2025 PDF p. 89 (printed 85) |
| [Honda] Ruckus: 2012 does not carry that sentence (implied by "2022 to 2025 editions say") | kept | 2012 instead: "The exhaust emission control system includes the following components that should not need adjustment, although periodic inspection by your Honda dealer is recommended." | 2012 PDF p. 95, printed 93 |
| [Honda] Ruckus title: "idle is the owner's only carburettor adjustment" | killed | 2025 schedule: "Engine Idle Speed" marked Intermediate with "Refer to page –", legend "Intermediate. We recommend service by your dealer, unless you have the necessary tools and are mechanically skilled. Procedures are provided in an official Honda Service Manual" (no owner idle procedure in 2022/2024/2025: `Adjusting the Engine Idle` 0 hits; 2012 has one) | 2025 PDF p. 42, printed 38 (rendered image) |
| [Honda] Ruckus: idle 2,000 ± 100 rpm (2012 p. 66; 2025 p. 104) | kept | "Idle speed: 2,000 ± 100 rpm" / "Idle speed 2,000 ± 100 rpm" | 2012 PDF p. 66 (printed 64); 2025 PDF p. 104 (printed 100) |
| [Honda] Ruckus: warm-up and "Do not attempt to compensate …" (2012 p. 66) | kept (2012 only; 0 hits in 2022–2025) | "The engine must be at normal operating temperature foe accurate idle speed adjustment. 10 minutes of stop-and-go riding is sufficient. Do not attempt to compensate for faults in other systems by adjusting idle speed." | 2012 PDF p. 66, printed 64 |
| [Honda] Ruckus: high altitude "in the same words in 2012 and 2025" | killed | 2012: "Above 6,500 feet (2,000 m) … (below 5,000 feet, 1,500 m). See your Honda dealer." vs 2025: "Above 6,500 ft (2,000 m) … (below 5,000 ft (1,500 m)). See your dealer." | 2012 PDF p. 99 (printed 97); 2025 PDF p. 93 (printed 89) |
| [Honda] Ruckus: high-altitude substance (rich above 2,000 m, dealer adjusts, return below 1,500 m, lean setting at low altitude risks rough idle/stall/overheating) in every edition | kept (2012, 2022, 2024, 2025 all carry it; 2022/2024/2025 word-identical) | "Sustained riding at lower altitudes with the lean high-altitude setting may cause rough idling, stalling, or engine damage from overheating." | 2012 PDF p. 99; 2022 PDF p. 92 (printed 88); 2024 PDF p. 92 (printed 88); 2025 PDF p. 93 (printed 89) |
| [Honda] Ruckus: 2012 allows ethanol 10%, MTBE 15%, methanol 5% with cosolvents (PDF p. 100) | kept | "Methanol (methyl alcohol) 5% by volume (max) that contain cosolvents and corrosion inhibitors to protect the fuel system. Never use a blend containing more than 5%." | 2012 PDF p. 100, printed 98 |
| [Honda] Ruckus: 2022, 2024 and 2025 keep ethanol up to 10% and forbid methanol | kept (all three) | "Ethanol (ethyl alcohol) up to 10% by volume. … Do not use gasoline containing methanol (methyl alcohol)." | 2022 PDF p. 93 (printed 89); 2024 PDF p. 93 (printed 89); 2025 PDF p. 94 (printed 90) |
| [Honda] Ruckus title: "methanol was dropped after 2012" | killed (uncertain as written; rewritten) | the change is bounded only by the 2012 and 2022 editions read; the row itself says "Editions between 2012 and 2022 were not read" | 2012 PDF p. 100; 2022 PDF p. 93 |
| [Honda] Ruckus fix 1: warm 10 minutes stop-and-go, then set idle, as a procedure for all editions | killed (uncertain as written; rewritten) | the warm-up sentence is 2012-only ("10 minutes of stop-and-go riding is sufficient"); 2022–2025 give no procedure and refer to the service manual | 2012 PDF p. 66; 2025 PDF p. 42 |
| [Honda] Ruckus fix 1: idle is "the only adjustment the 2022 - 2025 manuals leave to the owner" | killed | "Intermediate. We recommend service by your dealer, unless you have the necessary tools and are mechanically skilled." (applied to "Engine Idle Speed", "Refer to page –"); the emission sentence restricts all adjustment, it does not assign idle to the owner | 2025 PDF p. 42, printed 38; 2025 PDF p. 89 |
| [Honda] Ruckus fix 2: dealer adjusts above 6,500 ft; return to factory spec before riding below 5,000 ft | kept | "the carburetor must be returned to standard factory specifications before riding again at lower altitudes (below 5,000 ft (1,500 m)). See your dealer." | 2025 PDF p. 93, printed 89 |
| [Honda] Ruckus fix 3: ethanol up to 10%; no methanol 2022–2025; 2012 allowed 5% with cosolvents | kept | "Do not use gasoline containing methanol (methyl alcohol)." | 2022/2024 PDF p. 93; 2025 PDF p. 94 |
| [Honda] Ruckus cause: idle adjusted to mask a fault elsewhere | kept (2012 text only) | "Do not attempt to compensate for faults in other systems by adjusting idle speed." | 2012 PDF p. 66, printed 64 |
| [Honda] Ruckus cause: high-altitude setting left in below 1,500 m | kept | "Sustained riding at lower altitudes with the lean high-altitude setting may cause rough idling, stalling, or engine damage from overheating." | ruck_2025_31GJP610.pdf PDF p. 93; ruck_2012_31GGA6300.pdf PDF p. 99 (printed 97) |
| [Kymco] The Agility 50 manual's pages are headed AGILITY 50 | kept | "AGILITY 50" | kymco_agility50_sm.pdf: header on every cited page (p3/1-2, p55/5-2, p57/5-4, p58/5-5, p65/5-12). Note: 21 other pages carry "FILLY LX 50" headers, none of them cited |
| [Kymco] The Agility 50 carburettor type is CVK | kept | "Type CVK" | kymco_agility50_sm.pdf p55 / 5-2; also p3 / 1-2 |
| [Kymco] The People S 250 carburettor type is CVK | kept | "Type CVK CVK" | kymco_people_s250_sm.pdf p164 / 13-5 |
| [Kymco] Neither Kymco manual names the carburettor's maker | kept | "KEIHIN CVEK26" (the positive control, fly125.pdf p9); 0 hits in either Kymco manual | search of kymco_agility50_sm.pdf (183 pp.) and kymco_people_s250_sm.pdf (243 pp.); control fly125.pdf PDF p. 9 |
| [Kymco] Agility 50: main jet #85, slow jet #35, float level 17 mm | kept | "Float level (mm) 17 Main jet #85 Slow jet #35" | kymco_agility50_sm.pdf p55 / 5-2 |
| [Kymco] Agility 50 pilot screw opening is 2 ±1/2 turns | kept | "Pilot screw opening 2 ±1/2" | kymco_agility50_sm.pdf p55 / 5-2; also p65 / 5-12 "Standard Opening: 2±1/2 turns" |
| [Kymco] Agility 50 idle is 1900 rpm (pp. 5-2 and 5-12) | kept | "Idle speed 1900rpm"; "Idle Speed: 1900Ô100rpm" | kymco_agility50_sm.pdf p55 / 5-2 and p65 / 5-12. It also appears on AGILITY 50-headed p34 / 3-0 and p39 / 3-5 |
| [Kymco] The Agility 50 opening specification page gives 1700 ±100 rpm | kept | "Idle speed (rpm) 1700 Ô100rpm" | kymco_agility50_sm.pdf p3 / 1-2, headed AGILITY 50 (so not a template header from another model) |
| [Kymco] Agility 50 venturi figures: 20 mm on p. 5-2 and "phi17 equivalent" on the opening page | kept | "Venturi dia. (mm) 20"; "Venturi dia.(mm) φ17equivalent" | p55 / 5-2; p3 / 1-2. The word "equivalent" suggests a different measure from the bore, so these are two figures, not necessarily a contradiction |
| [Kymco] People S 250 column: 104#, pilot screw opening 1-1/4 ±3/4, idle 1600 | kept | "PEOPLE 250 PEOPLE S 250 … Main jet NO 108# 104# Pilot screw opening 2½ ± ½ 1¼± ¾ … Idle speed 1700 1600" | kymco_people_s250_sm.pdf p164 / 13-5 |
| [Kymco] People 250 column: 108#, 2-1/2 ±1/2, idle 1700 (p. 13-5) | kept | "PEOPLE 250 PEOPLE S 250" / "Main jet NO 108# 104#" | p164 / 13-5; p5 (People 250, BC50AA) "Idle speed (rpm) 1700±100rpm" |
| [Kymco] **Both** manuals say "The pilot screw is factory pre-set and no adjustment is necessary…" | killed (uncertain as written; rewritten) | Agility 50 only: "The pilot screw is factory pre-set and no adjustment is necessary. During carburetor disassembly, note the number of turns of the pilot screw and use as a reference when reinstalling it." The People S 250 manual says instead: "Before removing the pilot screw, turn the pilot screw clockwise until it seats lightly and record the rotating turns." | kymco_agility50_sm.pdf p65 / 5-12; kymco_people_s250_sm.pdf p169 / 13-10. Search `pre-? ?set\ | factory`: People S 250 0 hits; control 2 hits on Agility 50 p65 |
| [Kymco] Agility 50 bystarter: "10 ohm max.", 10 minutes minimum after stopping | kept | "Resistance: 10Ω max. (10 minutes minimum after stopping the engine)" (checked on the rendered page; the text layer reads "1 0Ω") | kymco_agility50_sm.pdf p57 / 5-4 |
| [Kymco] Bystarter resistance "14 - 20 ohm" on the People S 250 (p. 13-11) | kept | "Resistance: 14-20Ω (10 minutes minimum after stopping the engine)" | kymco_people_s250_sm.pdf p170 / 13-11 (rendered). The page is headed "PEOPLE/PEOPLE S 250", so the figure covers the People 250 too; the row leaves that out |
| [Kymco] Agility 50 test: battery, wait 5 minutes, blocked = normal; disconnect, wait 30 minutes, air passes = normal | kept | "Wait 5 minutes and blow the hose with mouth or vacuum pump. If the passage is blocked, the auto bystarter is normal. … Wait 30 minutes and blow the hose with mouth or vacuum pump. If air can be blown into the hose, the auto bystarter is normal." | kymco_agility50_sm.pdf p58 / 5-5 |
| [Kymco] The same two-step test is in the People S 250 manual | kept | "Wait 5 minutes and blow the hose with mouth. If the passage is blocked, the auto bystarter is normal. … Wait 30 minutes and blow the hose with mouth.. If air can be blown into the hose, the auto bystarter is normal." | kymco_people_s250_sm.pdf p170 / 13-11 |
| [Kymco] The People S 250 manual says "Do not try to disassemble the auto bystarter" (p. 13-5) | kept | "Do not try to disassemble the auto bystarter." | kymco_people_s250_sm.pdf p164 / 13-5 |
| [Kymco] Storage quote from the Agility 50 manual, p. 5-2 | kept | "When the motorcycle is not used for over one month, drain the residual gasoline from the float chamber to avoid erratic idling and clogged slow jet due to deteriorated fuel." | kymco_agility50_sm.pdf p55 / 5-2. The People S 250 has no equivalent: the `month` search has 1 hit, and it is about the battery |
| [Kymco] Owner's manual: "Drain the carburetor (if equipped) and empty the fuel tank" (PDF p. 49) | kept | "2. Drain the carburetor (if equipped) and empty the fuel tank into an approved gasoline container…" | kymco_agility50-125.pdf p49 / printed 47. The manual covers "Specifications (Agility 50)" and "(Agility 125)" (p3) |
| [Kymco] The model column's Agility 50, People S 250 and People 250 are each covered by a document | kept | "Motorcycle Name & Type AGILITY 50"; "PEOPLE 250" (BC50AA); "PEOPLE S 250" (BA50AA) | agility50_sm p3 / 1-2; people_s250_sm p5, p6 |
| [Kymco] Fix 1: drain the float chamber through its drain screw after a month unused | kept | "Before float chamber disassembly, loosen the drain screw to drain the residual gasoline" | kymco_agility50_sm.pdf p55 / 5-2 |
| [Kymco] Fix 1: "clean the slow jet if idle stays erratic" | killed (uncertain as written; rewritten) | "drain the residual gasoline from the float chamber to avoid erratic idling and clogged slow jet due to deteriorated fuel" (no sentence instructs cleaning it) | kymco_agility50_sm.pdf p55 / 5-2 |
| [Kymco] Fix 2: resistance figures (Agility 50 10 ohm max; People S 250 14 - 20 ohm) | kept | "Resistance:1 0Ω max." / "Resistance:1 4 - 2 0 Ω" | p57 / 5-4; p170 / 13-11 |
| [Kymco] Fix 3: powered 5 minutes, passage blocked; disconnected 30 minutes, air passes; replace if either fails; do not disassemble | kept | as above; "Do not try to disassemble the auto bystarter." | agility p58 / 5-5; people p170 / 13-11, p164 / 13-5 |
| [Kymco] Fix 4: seat the pilot screw lightly, record the turns, reinstall to the same count | kept | "turn the pilot screw clockwise until it seats lightly and record the rotating turns"; "Be sure to record the rotating turns when it is removed." | kymco_people_s250_sm.pdf p169 / 13-10, p174 |
| [Kymco] Fix 5: the Agility 50 manual prints two idle speeds (1900 and 1700 ±100) | kept | "Idle speed (rpm) 1700 Ô100rpm" vs "Idle Speed: 1900Ô100rpm" | p3 / 1-2 vs p65 / 5-12. Both pages are headed AGILITY 50 |
| [SYM] The Jet manual covers Jet 50/100 and Jet Euro 50/100 | kept | "the SANYANG JET 50/100 and JET Euro 50/100 series motorcycle" | sym_7326249.pdf p2 |
| [SYM] The Jet is two-stroke | kept | "Cycle/Cooling 2-stroke/forced air cooled" | sym_7326249.pdf p12 / 1-5 (JET 50 SERIES), p13 / 1-6 (JET 100 SERIES). No spec page is headed Jet Euro; it is two-stroke only by sharing the manual's engine chapters |
| [SYM] Fiddle 50 is model FA05U, two-stroke | kept | "MODEL ILLUSTRATION FA05U"; "MODEL FA05 Series … Cycle/Cooling 2-stroke/forced air cooled" | sym_fiddle50_sm.pdf p5; p10 / 1-5 |
| [SYM] Fiddle III is model XA05W-6, four-stroke | kept | "MODEL XA05W-6 … Cycle/Cooling 4-stroke/forced air cooled" | sym_fiddle3_sm.pdf p14 / 1-9 |
| [SYM] The document read is a **Fiddle III** manual (the model column) | killed (uncertain as written; rewritten) | The text never says "Fiddle" (1 hit for `f.?i.?d.?d.?l.?e\ | XA05\ | FA05\ | fiddle`, and that hit is "MODEL XA05W-6"). The cover (p1) says only "SERVICE MANUAL" over a photo; p2 says "the SYM series motorcycle"; the PDF title is "Microsoft Word - a COVER.doc" | sym_fiddle3_sm.pdf p1, p2, p14 / 1-9. The identity rests on the file name and the photo, not the document's text |
| [SYM] Joyride 125/150/200 = LA12W, LA15W, LA18W | kept | "Sanyang JOYRIDE 125/150/200"; "MODEL LA12W" / "LA15W" / "LA18W" | sym_7429958.pdf p2; p10-12 / 1-5 to 1-7 |
| [SYM] Joyride carburettor IDs "CVK039 CVK034 CVK066" (p. 4-2) | kept | "I.D. number CVK039 CVK034 CVK066" | sym_7429958.pdf p43 / 4-2 |
| [SYM] Fiddle 50 carburettor ID "PB2BE" (p. 10-2) | kept | "I.D. number PB2BE" | sym_fiddle50_sm.pdf p85 / 10-2 |
| [SYM] None of the four SYM manuals names the carburettor's maker | kept | 0 hits in 161 + 149 + 187 + 203 pages; control "KEIHIN CVEK26" found in fly125.pdf p9 | search of sym_7326249.pdf, sym_fiddle50_sm.pdf, sym_fiddle3_sm.pdf, sym_7429958.pdf; control fly125.pdf PDF p. 9 |
| [SYM] By-starter quote "Resistance value: Max. 10 ohm (Measured after engine stopped for more than 10 minutes)" | kept | "Resistance value: Max. 10ΩΩΩΩ (Measured after engine stopped for more than 10 minutes)" | sym_7429958.pdf p46 / 4-5; also sym_fiddle3_sm.pdf p49 / 4-7. The Jet and Fiddle 50 instead say "Resistance value: Max. 10Ω(at cold engine)" (Jet p91 / 10-4; Fiddle 50 p87 / 10-4) |
| [SYM] Joyride: "Replace the auto starter with a new one if resistance value exceeds standard" (p. 4-5) | kept | "Replace the auto starter with a new one if resistance value exceeds standard." | sym_7429958.pdf p46 / 4-5 |
| [SYM] Jet: "If the resistance value exceeds the standard a little bit…" (p. 10-4) | kept | "If the resistance value exceeds the standard a little bit, the auto by-starter may still in normal. However, it is necessary to check other relative components for damage." | sym_7326249.pdf p91 / 10-4. The same sentence is in sym_fiddle50_sm.pdf p87 / 10-4 |
| [SYM] Joyride circuit test: cold (30 minutes after removal) air must pass; 12 V for 5 minutes, "If air flows through the circuit, then, replace the starter" | kept | "Remove carburetor, allow it to cool off for 30 minutes. … Replace the auto by-starter if the circuit clogged. Connect battery posts (12V) to starter's connectors. After 5 minutes, test the by-starter circuit with compressed air. If air flows through the circuit, then, replace the starter." | sym_7429958.pdf p46 / 4-5 |
| [SYM] Pilot screw quote "Pilot screw was set at factory…" (Joyride, p. 4-10) | kept | "Pilot screw was set at factory, so no adjustment is needed. Note the number of turns it takes to screw it all the way in for ease of installation." | sym_7429958.pdf p51 / 4-10. Fiddle III has the same sentence for its "Fuel amount adjust screw" (p51 / 4-9); Jet and Fiddle 50 have 0 `factory` hits |
| [SYM] Joyride: CO 1.0~1.5 % at 1600 ±100 rpm on an exhaust analyser (p. 4-10) | kept | "Idle speed rpm: 1600 ± 100 rpm Connect the hose of exhaust analyzer … Adjust the pilot screw and read CO reading on the analyzer CO standard value: 1.0~1.5 %" | sym_7429958.pdf p51 / 4-10 |
| [SYM] CO 1.0~1.5 % is a Joyride figure, set against the two-stroke 1.8-2.6 % | killed (uncertain as written; rewritten) | Fiddle III also gives "CO standard value: 1.0~1.5 %" at "Idle speed rpm: 2100±100 rpm", set with the "air volume adjustment screw" | sym_fiddle3_sm.pdf p51 / 4-9 |
| [SYM] Jet: "CO: 1.8-2.6%" (p. 2-13) | kept | "Adjust the idle speed screw to let engine speed in 2000±100 rpm. … Adjust the idling emission value to standard range. (CO: 1.8-2.6%)" | sym_7326249.pdf p38 / 2-13. The procedure's 2000±100 rpm is the Jet 50 idle; the same page gives "Idle speed: 2100±100 rpm (JET 100)" |
| [SYM] Fiddle 50: "CO: 1.8-2.6%" (p. 2-11) | kept | "(CO: 1.8-2.6%)" | sym_fiddle50_sm.pdf p32 / 2-11 |
| [SYM] The EPA star-note wording (Joyride, p. 2-2) | kept | "These marks "☆☆☆☆" in the schedule are emission control items. According to EPA regulations, these items must be performed normally periodical maintenance following the use r manual instructions. They are prohibited to be adjusted or repaired by unauthorized people. Otherwise, SYM is no responsible for the charge." | sym_7429958.pdf p23 / 2-2; the same note is in sym_fiddle3_sm.pdf p23 / 2-2 |
| [SYM] "**The maintenance schedules** mark emission items with a star: 'According to EPA regulations…'" (implied for all four manuals) | killed (uncertain as written; rewritten) | The Jet and Fiddle 50 schedules carry ☆ marks but no EPA note. Their "Remarks: 1." is "Clean or replace the air cleaner element more often for pro-long engine life-span…" | sym_7326249.pdf p27; sym_fiddle50_sm.pdf p23. `\bEPA\b`: 0 hits in Jet and Fiddle 50; controls 2 in Joyride and 3 in Fiddle III |
| [SYM] Every manual notes a drain screw in the float chamber (Joyride, p. 4-2) | kept | "There is a drain screw in the float chamber for draining residual gasoline." (Joyride, Fiddle III); "Loosen draining screw and then drain out fuel inside the carburetor." (Jet, Fiddle 50) | joy p43 / 4-2; fiddle3 p44 / 4-2; jet p91 / 10-4; fiddle50 p87 / 10-4 |
| [SYM] Fiddle III has an "ECS (Electronically controlled carburetor system)" chapter that no other manual here has | kept | "ECS(Electronically controlled carburetor system) Vehicle Configuration" | sym_fiddle3_sm.pdf p55 / 4-2. `electronically controlled carburet\ | \bECS\b`: 22 hits in Fiddle III, 0 in each of the other five |
| [SYM] The ECU reads an "O2 Sensor" among its inputs (chapter 4) | kept | "…Output Crankshafthrotatehspeed ThrottlehPositionhSensor O2 Sensor Enginehtemperaturehsensor Batteryhvoltage…" | sym_fiddle3_sm.pdf p56 / 4-3. Two chapters are numbered 4: FUEL SYSTEM (p43-53, 4-1 to 4-11) and ECS (p54-66, 4-1 to 4-13) |
| [SYM] Fix 1: engine stopped over 10 minutes, 10 ohm max.; the Jet allows a little over | kept | "If the resistance value exceeds the standard a little bit, the auto by-starter may still in normal." | joy p46 / 4-5; jet p91 / 10-4 |
| [SYM] Fix 2: "powered from 12 V for 5 minutes, it must not" (for all listed models) | killed (uncertain as written; rewritten) | The Jet and Fiddle 50 give neither 12 V nor 5 minutes: "Connect battery to starter's connectors and wait for several minutes. Pump compressed air into the fuel rich circuit. Air should not flow into the circuit." | sym_7326249.pdf p92 / 10-5; sym_fiddle50_sm.pdf p88 / 10-5. The 12 V / 5 minutes figures are from Joyride p46 / 4-5 and Fiddle III p49 / 4-7 |
| [SYM] Fix 3: count the turns to seat the pilot screw and reinstall to that count | kept | "Note the number of turns it takes to screw it all the way in for ease of installation." | joy p51 / 4-10; fiddle3 p51 / 4-9 |
| [SYM] Fix 4: CO 1.0-1.5 % (Joyride) or 1.8-2.6 % (Jet, Fiddle 50) | killed (uncertain as written; rewritten) | Fiddle III: "CO standard value: 1.0~1.5 %" at 2100±100 rpm | sym_fiddle3_sm.pdf p51 / 4-9 |
| [SYM] Fix 5: "Star-marked schedule items are emission items" (all models) | killed (uncertain as written; rewritten) | "These marks “☆☆☆☆” in the schedule are emission control items." (Joyride and XA05W-6 only; the Jet and Fiddle 50 schedules print ☆ with no definition) | jet p27; fiddle50 p23 |
| [SYM] Fix 5: "**SYM** prohibits adjustment or repair by unauthorized people" | killed (uncertain as written; rewritten) | "According to EPA regulations, … They are prohibited to be adjusted or repaired by unauthorized people. Otherwise, SYM is no responsible for the charge." The prohibition is attributed to EPA regulations; SYM only disclaims responsibility | sym_7429958.pdf p23 / 2-2 |
| [SYM] Cause: "Auto by-starter PTC element failed (resistance above 10 ohm cold)" | kept | "If the resistance value exceeds specification too much, it means that the PTC in the auto by-starter is malfunction." | sym_7326249.pdf p91 / 10-4 |
| [Kymco] "Both manuals" also covers the by-starter test's normal states (blocked when heated, open when cold) | kept | "If the passage is blocked, the auto bystarter is normal." (both manuals) | agility p58 / 5-5; people p170 / 13-11 |
| [Piaggio] Fly 50 4T carburettor is a Keihin CVK 18, printed "KEHIN" | kept | "Kehin KEHIN CARBURETTOR Specification Desc./Quantity Type CVK 18" | fly50.pdf p12, CHAR - 12 (also "KEIHN CVK 18" at p9, CHAR - 9) |
| [Piaggio] Fly 50 idle mixture screw initial opening 1-3/4 (CHAR - 12) | kept | "Initial opening - idle mixture screw: 1 3/4" | fly50.pdf p12, CHAR - 12 |
| [Piaggio] Fly 125 - 150 4T: Keihin CVEK26 (CHAR - 12) | kept | "Kehin CARBURETTOR SETTING Specification Desc./Quantity Type CVEK26" | fly125.pdf p12, CHAR - 12 (also "KEIHIN CVEK26", p9, CHAR - 9) |
| [Piaggio] Beverly 125: Keihin CVEK 30 (CHAR - 9) | kept | "Fuel supply KEIHIN CVEK 30 carburettor and electrical fuel pump." | beverly125.pdf p9, CHAR - 9 |
| [Piaggio] Typhoon 50 is a two-stroke with "DELL'ORTO PHVA 17.5" (CHAR - 8) | kept | "Engine type Two-stroke, single cylinder Piaggio Hi-PER2 ... Carburettor DELL'ORTO PHVA 17.5" | typhoon50.pdf p8, CHAR - 8 |
| [Piaggio] Typhoon 50 belongs under make Piaggio, not Gilera | kept | "Engine type Two-stroke, single cylinder Piaggio Hi-PER2" | typhoon50.pdf p8, CHAR - 8; "Gilera" occurs only in "Piaggio-Gilera dealers" boilerplate, p2/p3 (no folio) |
| [Piaggio] 618162 is "the manual for the B 125-250 engine" | killed (uncertain as written; rewritten) | "Chassis prefix (125) ZAPM 28400 ÷ 1001 Engine prefix (125) M284M ... Chassis prefix (250) ZAPM 28500 ÷ 1001" | bev_b.pdf p8, CHAR - 8: it is a whole-vehicle workshop manual (chassis prefixes, weights, top speed), not an engine manual |
| [Piaggio] Its thermal-switch page lists X9, X8 and Beverly frame numbers (ELE SYS - 83) | kept | "ZAPM2300003507739 (X9) ZAPM3620000003383 (X8) ZAPM2850000001025 (Beverly)" | bev_b.pdf p83, ELE SYS - 83 |
| [Piaggio] B 125-250 lists two carburettors for the 125, a Keihin CVEK30 and a "WALBRO CARBURETTOR" WVF-7G | kept | "Keihin Carburettor (125 - 250) CVEK-30 Walbro Carburettor (125) WVF 7G* Ø 29"; "WALBRO CARBURETTOR ... Type to depression WVF-7G*" | bev_b.pdf p8, CHAR - 8; p13, CHAR - 13 |
| [Piaggio] B 125-250 starter device resistance about 20 Ω on the Keihin, about 40 Ω on the Walbro (CHAR - 13, 14) | kept | "Starter device resistance ~ 20 Ω" (Keihin 125); "Starter device resistance ~ 40 Ω" (Walbro 125) | bev_b.pdf p13, CHAR - 13; p14, CHAR - 14 |
| [Piaggio] The Walbro starter has one resistance figure, about 40 Ω (fix step 2) | killed (uncertain as written; rewritten) | "Check the auto starter: Protrusion Value for Walbro 12.5 ÷ 13 mm ... Check the automatic starter: Resistance around 30 Ω" | bev_b.pdf p212-213, ENG - 212/213, against "Walbro Resistance approx. 40 Ω", p215, ENG - 215 |
| [Piaggio] The Keihin/Walbro choice (causes, fix step 1) applies to a model in the model column, the Beverly 125 | killed (uncertain as written; rewritten) | "Chassis prefix ZAPM 28900 ÷ 1001 Engine prefix M28FM" | beverly125.pdf p8, CHAR - 8; `walbro` 0 hits in 664603 (control: 17 in bev_b); the B 125-250's 125 is ZAPM 28400 / M284M (bev_b p8, CHAR - 8), and its Beverly frame number ZAPM285… matches the **250** prefix |
| [Piaggio] "The screw final position should be determined by an exhaust fume analysis" (Fly 125, ENG - 149) | kept | "The screw final position should be determined by an exhaust fume analysis." | fly125.pdf p149, ENG - 149 |
| [Piaggio] Same sentence in the Beverly 125 (ENG - 162) | kept | "The screw final position should be determined by an exhaust fume analysis." | beverly125.pdf p162, ENG - 162 |
| [Piaggio] Fly 50: oil at 70 - 80 °C, idle "about 1900/2000 rpm" (ENG - 123) | kept | "make sure that the oil temperature is be- tween 70÷80 °C" … "Idle speed about 1900/2000 rpm" | fly50.pdf p123, ENG - 123 |
| [Piaggio] Fly 50 loosening/tightening quote (ENG - 123) | kept | "When the screw is loosened the CO value rises (rich mix). Tightening the screw decreases the CO (lean mix)." | fly50.pdf p123, ENG - 123 |
| [Piaggio] Fly 50 target "CO adjustment 3,2% +/- 0,5" | kept | "CO adjustment 3,2% ± 0,5" | fly50.pdf p123, ENG - 123; p9, CHAR - 9 |
| [Piaggio] Fly 125 - 150: "Starter resistance 20 Ohm (at 24 deg)", "Starter pin travel 10 mm (at 24 deg)" (CHAR - 12) | kept | "Starter pin travel 10 mm (at 24°) Starter resistance 20 Ohm (at 24°)" | fly125.pdf p12, CHAR - 12 (125 column; the 150 column's resistance line is on p13, CHAR - 13) |
| [Piaggio] Fly 125 - 150: powered from 12 V the piston must protrude fully (cited ENG - 154) | kept | "With a 12V battery power the automatic starter and check that the piston protrudes as much as possible." | fly125.pdf p153, **ENG - 153** (not 154) |
| [Piaggio] "Check the automatic starter: Keihin maximum time 5 min" (Fly 125, ENG - 154) | kept | "Check the automatic starter: Keihin maximum time 5 min" | fly125.pdf p154, ENG - 154 |
| [Piaggio] Fly 125 - 150 prints protrusion as "XX / XX mm at approx. 20 C" and "XXX / XXX mm", blanks never filled in | kept | "Kehin: Protrusion value XX ÷ XX mm at approx. 20°C ... Kehin maximum protrusion XXX ÷ XXX mm" | fly125.pdf p154, ENG - 154 (rendered image confirms; `protrusion` finds no other value in the manual) |
| [Piaggio] B 125-250 gives 12.5 - 13 mm at 20 °C and 18.5 - 19 mm maximum "for Walbro" (ENG - 212) | kept | "Protrusion Value for Walbro 12.5 ÷ 13 mm at approx. 20°C Check the automatic starter: maximum protru- sion 18.5 ÷ 19 mm" | bev_b.pdf p212, ENG - 212 (repeated with "Walbro maximum protrusion", p215, ENG - 215) |
| [Piaggio] Beverly 125: "TAMPERPROOF SCREWS ARE SUPPLIED WITH 125 CC MODELS" on the intake manifold (ENG - 111) | kept | "Removing the intake manifold ... Loosen the 3 crews and remove the intake mani- fold. N.B. TAMPERPROOF SCREWS ARE SUPPLIED WITH 125 CC MODELS." | beverly125.pdf p111, ENG - 111 |
| [Piaggio] Model column: each of Fly 50, Fly 125, Fly 150, Beverly 125, Typhoon 50 is covered by a document | kept | "MSS Fly 50 4T"; "Fly 125 - 150 4T"; "Beverly 125"; "Typhoon 50" | title pages p1 of fly50 (633212), fly125 (633225), beverly125 (664603 EN), typhoon50 |
| [Piaggio] Fix step 2: the automatic starter on a Keihin is about 20 Ω at 24 °C and extends fully within 5 minutes (a rule for all Keihin models in the row, including the Fly 50's CVK 18) | killed (uncertain as written; rewritten) | "Automatic starter resistance 6 Ω ± 5 % ... Battery 12V-9Ah max. protrusion 15 mm max. time 15 min" | fly50.pdf p121, ENG - 121 (protrusion "11 mm" at "24° C", p120, ENG - 120) |
| [Piaggio] Cause: "Automatic starter outside its resistance, travel or 5-minute time" (for every model in the row) | killed (uncertain as written; rewritten) | "max. time 15 min" | fly50.pdf p121, ENG - 121 |
| [Piaggio] Fix step 2: the 5 minutes is the time within which the piston must extend fully | killed (uncertain as written; rewritten) | "The correct warm up time depends on the ambi- ent temperature." … "Check the automatic starter: Keihin maximum time 5 min" | fly125.pdf p153-154, ENG - 153/154: the manual never says what the 5 minutes times |
| [Piaggio] Fix step 3 (oil at 70 - 80 °C, then the flow screw on an analyser) applies to the Typhoon 50 | killed (uncertain as written; rewritten) | "Lubrication With blend and variable oil ... by means of a pump"; "CO adjustment 3.5% ± 0.5 Engine idle speed 1800 to 2000 r.p.m." | typhoon50.pdf p8, CHAR - 8: a two-stroke with no sump; the manual has no oil-temperature CO procedure |
| [Piaggio] Title: the mixture screw is set on an exhaust analyser; the starter is checked by resistance, travel and time | kept | "If protrusion, resistance or timing values are dif- ferent from the ones prescribed, replace the start- er." | fly125.pdf p153, ENG - 153; fly50.pdf p121, ENG - 121 |
| [Vespa] LX 50 prints "DELL'ORTO PHVA 17.5" (CHAR - 9) | kept | "Carburettor DELL'ORTO PHVA 17.5" | vespa_lx50_633416.pdf p9, CHAR - 9 |
| [Vespa] S 50 prints "DELL'ORTO PHVA 17.5" (CHAR - 9) | kept | "Fuel supply Carburettor: DELL'ORTO PHVA 17.5 RD" | vespa_s50_2t.pdf p9, CHAR - 9 |
| [Vespa] LX 50 and S 50 are two-strokes | kept | "Engine type Two-stroke, single cylinder Piaggio Hi-PER2"; "Type single-cylinder, two-stroke" | lx50 p9, CHAR - 9; s50 p9, CHAR - 9 |
| [Vespa] Same settings: max nozzle 53, A22 in notch 1, min nozzle 32, "Initial minimum mix screw opening: 1 1/2", starter jet 50, "Stroke of starter pin: 11 mm" | kept | "Maximum nozzle: 53 ... Tapered pin stamped code: A22 Pin position (notches from above): 1 ... Minimum nozzle: 32 ... Initial minimum mix screw opening: 1 1/2 Starter jet 50 ... Stroke of starter pin: 11 mm" | lx50 p12, CHAR - 12; s50 p11-12, CHAR - 11/12 (the two tables are line-for-line identical) |
| [Vespa] LX 125 - 150 4T prints "KEIHIN CVEK26" (CHAR - 4) | kept | "Carburettor KEIHIN CVEK26" | piaggio_633976_vespaLX.pdf p10, CHAR - 4 |
| [Vespa] 125 and 150 columns differ: stamping 270C/271B, max jet 82/80, min jet 42/35, idle screw 2-1/2 / 1-3/4 | kept | "Setting stamping 270C Maximum jet 82 ... Minimum jet 42 ... initial opening 2 ½" / "Setting stamping 271B Maximum jet 80 ... Minimum jet 35 ... initial opening 1 ¾" | 633976 p12, CHAR - 6; p13, CHAR - 7 |
| [Vespa] LX 125 - 150 "Starter resistance 20 Ohm (at 24 deg)" (CHAR - 6; ENG - 72) | kept | "Starter resistance 20 Ohm (at 24°)" | 633976 p12, CHAR - 6; p156, ENG - 72 |
| [Vespa] "Keihin maximum time 5 min" is an LX 125 - 150 Keihin figure (ENG - 72) | kept | "Check the automatic starter: Keihin maximum time 5 min" | 633976 p156, ENG - 72 |
| [Vespa] LX 50 characteristics: idle "1800 to 2000 r.p.m.", "CO adjustment 3.5% +/- 0.5" (CHAR - 9) | kept | "CO adjustment 3.5% ± 0.5 Engine idle speed 1800 to 2000 r.p.m." | lx50 p9, CHAR - 9 |
| [Vespa] LX 50 CO check: "adjust the idle speed to 1,700 +/- 100 rpm and check the CO value is equal 3.5 +/- 1%" (MAIN - 36) | kept | "Start the engine, adjust the idle speed to 1,700 ± 100 rpm and check the CO value is equal 3.5 ± 1%" | lx50 p36, MAIN - 36 |
| [Vespa] Gas probe sealed to the secondary air manifold "in order to guarantee accurate CO readings" | kept | "Attach the exhaust gas collection tube to the sec- ondary air rubber manifold. Such joint must be sealed in order to guarantee accurate CO read- ings." | lx50 p36, MAIN - 36 |
| [Vespa] The LX 50 gives "two idle figures for two procedures" | killed (uncertain as written; rewritten) | "CO check ... adjust the idle speed to 1,700 ± 100 rpm" (the only procedure); CHAR - 9 is a characteristics table | lx50 p9, CHAR - 9 and p36-37, MAIN - 36/37; «Adjusting the idle speed» is only referenced (MAIN - 28 to 30), with no section body in the manual |
| [Vespa] Intake manifold clamping screws come off with "an anti-tampering TORX spanner" (LX 50 ENG - 78; S 50 ENG - 84) | kept | "Use an anti-tampering TORX spanner to remove the two clamping screws of the intake manifold" | lx50 p78, ENG - 78; s50 p84, ENG - 84 |
| [Vespa] The LX 50 copy is marked as downloaded from Manualslib | kept | "Downloaded from www.Manualslib.com manuals search engine" | lx50 p1 and every page footer |
| [Vespa] Fix step 2: CO 3.5 % at idle on an analyser, probe sealed, applies to the "two-stroke 50" including the S 50 | killed (uncertain as written; rewritten) | "Engine idle speed 1,800 ± 100 rpm" | s50 p9, CHAR - 9: the S 50 manual has 0 hits for CO, analyser or carbon monoxide (LX 50 control: 9) |
| [Vespa] Fix step 3: LX 125 - 150 starter "fully extended within 5 minutes" | killed (uncertain as written; rewritten) | "Check the automatic starter: Keihin maximum time 5 min" | 633976 p156, ENG - 72: the manual does not say what the 5 minutes times |
| [Vespa] Model column LX 50, S 50, LX 125, LX 150 each covered by a document | kept | "Vespa LX 50"; "Vespa S 50 2T"; "Vespa LX 125 - 150 4T Euro 3" | title pages p1 of 633416, 664787-664795, 633976 |
| [Yamaha] YW50T manual says "all carburetor adjustments should be left to a Yamaha dealer, who has the necessary professional knowledge and experience" (5PJ-F8199-13, PDF p. 48) | kept | "Therefore, all carburetor adjustments should be left to a Yamaha dealer, who has the necessary professional knowledge and experience." | 5PJ-F8199-13 (YW50T), PDF p. 48, printed 6-10 |
| [Yamaha] Title and fix step 3: the owner's manuals leave carburettor adjustment to the dealer (as a statement about all seven editions) | kept | "Therefore, carburetor adjustments should be left to Yamaha dealer, who has the necessary professional knowledge and experience." | Wording found in the other six: 3D1-F8199-10 PDF p. 47 (6-13); 3D1-F8199-11 PDF p. 47 (6-13); 3D1-F8199-15 PDF p. 50 (6-14); 5PJ-F8199-17 PDF p. 47 (6-11); 5YR-F8199-10 PDF p. 53 (6-19); 5YR-F8199-15 PDF p. 50 (6-13). The word "all" and the article "a" appear only in YW50T |
| [Yamaha] The owner checks idle and has it "corrected by a Yamaha dealer" if needed | kept (for the two editions it cites) | "Check the engine idling speed and, if necessary, have it corrected by a Yamaha dealer." | 5PJ-F8199-17 PDF p. 47 (6-11); 3D1-F8199-15 PDF p. 50 (6-14). YJ125Y has "adjusted by", not "corrected by", on PDF p. 51 (6-14). XC50V, XC50W, YW50T and YJ125S have no idle-check section and no idle figure |
| [Yamaha] Idle 1800 - 1900 r/min on the YW50A (5PJ-F8199-17, PDF p. 47) | kept | "Engine idling speed: 1800 - 1900 r/min" | 5PJ-F8199-17 (YW50A), PDF p. 47, printed 6-11 |
| [Yamaha] Idle 2000 - 2200 r/min on the XC50A (3D1-F8199-15, PDF p. 50) | kept | "Engine idling speed: 2000 - 2200 r/min" | 3D1-F8199-15 (XC50A), PDF p. 50, printed 6-14 |
| [Yamaha] Storage lead-in "Before storing your scooter for several months" | kept | "Before storing your scooter for several months:" | 5YR-F8199-10 (YJ125S), PDF p. 64, printed 7-3 |
| [Yamaha] Storage quote "Drain the carburetor float chamber ... Pour the drained fuel into the fuel tank" (YJ125S, 5YR-F8199-10, PDF p. 64) | kept | "Drain the carburetor float chamber by loosening the drain bolt; this will prevent fuel deposits from building up. Pour the drained fuel into the fuel tank." | 5YR-F8199-10, PDF p. 64, printed 7-3 |
| [Yamaha] Storage quote "Fill up the fuel tank and add fuel stabilizer (if available) ..." (same page) | kept | "Fill up the fuel tank and add fuel stabilizer (if available) to prevent the fuel tank from rusting and the fuel from deteriorating." | 5YR-F8199-10, PDF p. 64, printed 7-3 |
| [Yamaha] "the same words in the XC50 and YW50A manuals" | kept (and holds in all seven) | "2. Drain the carburetor float chamber by loosening the drain bolt; this will prevent fuel deposits from building up. Pour the drained fuel into the fuel tank." | Also found in: 3D1-F8199-10 PDF p. 63 (7-3); 3D1-F8199-11 PDF p. 63 (7-3); 3D1-F8199-15 PDF pp. 67-68 (7-3/7-4); 5PJ-F8199-17 PDF pp. 63-64 (7-3/7-4); 5PJ-F8199-13 PDF p. 65 (7-4); 5YR-F8199-15 PDF pp. 69-70 (7-3/7-4) |
| [Yamaha] E10 quote "Gasohol containing ethanol can be used if the ethanol content does not exceed 10% (E10)" (YW50A PDF p. 25; XC50A PDF p. 25) | kept | "Gasohol containing ethanol can be used if the ethanol content does not exceed 10% (E10)." | 5PJ-F8199-17 PDF p. 25 (3-7); 3D1-F8199-15 PDF p. 25 (3-7); also 5YR-F8199-15 PDF p. 24 (3-6) |
| [Yamaha] "E10" as the manuals' own term (title "allow E10"), across editions | kept, with a caveat | "Gasohol containing ethanol can be used if ethanol content does not exceed 10%." | 5YR-F8199-10 PDF p. 21 (3-4). The "(E10)" label appears in only 3 of 7 editions (XC50A, YW50A, YJ125Y). XC50V (p. 23, 3-7), XC50W (p. 23, 3-7), YW50T (p. 27, 3-7) and YJ125S say "10%" without it. The limit itself is the same in all seven |
| [Yamaha] Methanol quote "not recommended by Yamaha because it can cause damage to the fuel system or vehicle performance problems" | kept (7/7) | "Gasohol containing methanol is not recommended by Yamaha because it can cause damage to the fuel system or vehicle performance problems." | 5PJ-F8199-17 PDF p. 25 (3-7); 3D1-F8199-15 PDF p. 25 (3-7); and every older edition (3D1-10/-11 p. 23, 5PJ-13 p. 27, 5YR-10 p. 21, 5YR-15 p. 24) |
| [Yamaha] Title: the manuals "allow E10 but not methanol" | killed | "Gasohol containing methanol is not recommended by Yamaha" | All seven manuals, fuel page (e.g. 5PJ-F8199-17 PDF p. 25, 3-7). The manuals say methanol blends are *not recommended*; no edition says they are not allowed. Fix step 2 words this correctly, but the title makes it a prohibition |
| [Yamaha] Fix step 1: "fill the tank and add stabiliser" | killed (minor) | "add fuel stabilizer (if available)" | All seven, storage step 3 (e.g. 5YR-F8199-10 PDF p. 64, 7-3). The manuals make stabiliser conditional, and the fix step drops "(if available)" |
| [Yamaha] Fix step 1: drain through the drain bolt and pour the fuel back into the tank before storing for several months | kept | "Drain the carburetor float chamber by loosening the drain bolt ... Pour the drained fuel into the fuel tank." | 5YR-F8199-10 PDF p. 64 (7-3), and all seven as above |
| [Yamaha] Fix step 2: "Use unleaded fuel; E10 is acceptable, methanol blends are not recommended" | kept | "Recommended fuel: UNLEADED GASOLINE ONLY" | 5PJ-F8199-17 PDF p. 25 (3-7); same in all seven |
| [Yamaha] Fix step 3: idle figures (YW50A 1800 - 1900, XC50A 2000 - 2200) and dealer correction of idle or "any other carburettor setting" | kept, but incomplete | "Engine idling speed: 1600 ~ 1700 r/min" | 5YR-F8199-15 (YJ125Y), PDF p. 51, printed 6-14. The Vino 125 (YJ125Y) prints an idle figure the row leaves out, although its model column lists "Vino 125" |
| [Yamaha] "The carburettor makers and types they print are already in the corpus's row on the three Yamaha engines" | kept, with a caveat | "Manufacturer TEIKEI Type × quantity Y14P × 1" | 5PJ-F8199-13 (YW50T), PDF p. 68, printed 8-1. The Phase 253 row 1 carries TEIKEI "Y14P-13E ( 5PJ5 ) x 1" (YW50A, matching 5PJ-17 PDF p. 65), KEIHIN "NCV18 x 1" (XC50; matching 3D1-10/-11 p. 65 and 3D1-15 p. 69) and Mikuni "BS26 x 1" (YJ125Y; also YJ125S p. 66). All three makers and base types are present. The YW50T's shorter "Y14P × 1" designation is not |
| [Yamaha] "the cover codes are tied to the Vino and Zuma names by the corpus's Yamaha scooter rows" | killed (uncertain as written; rewritten) | "Congratulations on your purchase of the Y amaha VINO." | 3D1-F8199-10 and -11, PDF p. 3; "VINO125" in 5YR-F8199-10 PDF p. 3; "VINO OWNER'S MANUAL" on PDF p. 5 of 3D1-10/-11. For three editions the manuals themselves carry the Vino name, so the row understates its own evidence. The Phase 253 rows tie YW50A to "Zuma 50 through model year 2011", XC50A to the Vino 50, YJ125Y to the Vino 125, and XC50V/XC50W to the Vino 50 (row 3). No Phase 253 row ties YW50T to "Zuma 50" in a sentence: YW50T appears only in row 4's model list, beside "Zuma, Zuma 125, YW125, Riva". "Zuma" occurs 0 times in all seven manuals |
| [Yamaha] Model column "Vino 50, Vino 125, Zuma 50, XC50" | killed (uncertain as written; rewritten) | "Congratulations on your purchase of the Yamaha YW50T." | 5PJ-F8199-13 PDF p. 3. "Vino 50", "Vino 125" and "XC50" are supported by the documents. "Zuma 50" rests on the corpus's YW50A bridge, and the documents never name it (0 hits in 7). The column names one base code (XC50) but not YJ125 or YW50, although Phase 253 row 3 says a Yamaha scooter should be identified by code |
| [Yamaha] Description: seven editions read (3D1-10, -11, -15; 5YR-10, -15; 5PJ-13, -17) and their models (XC50 = Vino, YJ125 = Vino 125, YW50 = Zuma 50) | kept | "3D1-F8199-15XC50A OWNER'S MANUAL" | Cover pages (PDF p. 1) of all seven: XC50V, XC50W, XC50A, YW50T, YW50A, YJ125S, YJ125Y |
