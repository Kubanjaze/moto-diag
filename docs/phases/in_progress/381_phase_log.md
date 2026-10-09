# Phase 381 — The content batch on the row key — phase log

**Status:** 🚧 In progress (2026-10-08)
**Branch:** `phase-381` (Opus session, main checkout)

---

### 2026-10-08 — Opened, Step 0, and the stop

The prompt is `docs/prompts/381_content_batch_on_the_row_key.txt`
(merged `dfc8184`). Row 381 went 🚧 before Step 0. Live was copied with
the backup API to the session scratchpad: schema 85, 1060 rows, all keyed.

`381_step0.md` re-measures each of the prompt's facts. All hold, with one
correction: F153's four SYM spellings sit on **8** CVT rows (7 scoped and
the unscoped 4605), not 11; the other 4 scoped rows pair no SYM model.

The prompt asked for a stop at Step 0 with four questions. As put to the
operator:

**Q1. F149** (rows 263, 264, 270). On disk: 27 distinct Honda PDFs, of
which 3 are service manuals (CHF50, PCX 2013–2017, Grom); no Honda
motorcycle service manual.
- **1A, retire the three (recommended).** Seed entries removed, the live
  rows deleted by key with their junction pairs. They cite nothing; the
  only Honda service manuals on disk contradict their procedure on the
  machines they reach. The VFR800, CB750, Shadow, Rebel, CB500F, XR650L
  and CBR family keep their own charging rows (all `unverified`). The
  parity check gains removed rows: a removed key must be absent from the
  fresh build.
- **1B, narrow `model` to what the rows' own text names** (263: VFR and
  "sport bikes"; 264: VFR, CBR), and delete their unsourced
  generalisations. The evidence is the rows' text, not a document. 270
  names no model and has nowhere to go. A scooter still sees 263 and 264
  at tier 2, labelled as another model.
- **1C, source them first.** This needs a Honda motorcycle service manual
  acquisition through Subconscious, so the phase pauses on F149.
- **Not offered:** a non-CVT applicability scope. It also withholds the
  rows from the VFR800, CB750, Shadow 750 and Rebel 500, which resolve
  `unknown`.

**Q2. F156.** The CHF50 rows 5338 and 6397 run from 2002 with no end
year, and the year filter is per row.
- **2A, a dated alias at resolution (recommended).** One sourced entry,
  Honda "Metropolitan" 2002–2006 → CHF50, citing the cover. It applies
  only when the door knows the year (diagnose does), and a row is tier 0
  when it pairs either name.
  - A 2005 Metropolitan gains 5338, 6397 and the 8 CVT rows paired with
    CHF50, and keeps 4577, 4588, 4615, 4616.
  - A 2018 Metropolitan, and any query with no year, is unchanged.
  - No row's content and no live row change for F156.
  - Remainder: 2007-on CHF50 Metropolitans. The cover says 2002–2006,
    while the tables reach "After ’07 model NVK00K".
- **2B, "Metropolitan" in 5338's and 6397's model column, with
  `year_end` 2006.** Two rows change. A 2007-on CHF50 loses both rows,
  which the same manual contradicts.
- **2C, the spelling with open years.** A 2018 injected NCW50 reaches the
  carburettor row. Rejected.
- **2D, year columns on the junction pairs.** A schema change, the tier
  SQL and every door; general, and larger than this phase.

**Q3. F158's wording.**
- **3A (recommended), a rule per word:**
  - "this project", "this file", "refut…" and "research pass" are build
    provenance. Delete the sentence when it narrates how the row was
    made; delete only the clause when the sentence also carries the fact.
    - Delete the sentence: 898 "The campaign is described without a
      reference number, per this project's standing decision."
    - Delete the clause: 904 "A refuter found the page **states that some
      compatible models are not shown**" → "The page **states that some
      compatible models are not shown**".
  - "corpus": where it states a scope the reader needs, it becomes
    "MotoDiag"; where it narrates, the sentence goes.
    - 855's title: "… and this corpus does not state what yours is" →
      "… and MotoDiag does not state what yours is".
    - 4605: "Measured on the corpus as it stands, a search for the phrase
      returns eight entries …" is deleted.
  - 672's title needs a replacement too: "… that this project's table
    does not decode" → "… that MotoDiag's table does not decode".
  - "census" stays. All 6 hits mean a complete count ("a sample and not a
    census", 4616), and banning it would catch the honest use.
  - The census is widened to the words removed: "this project", "this
    file", "refut", "corpus", "research pass".
- **3B, one fixed substitute per word** ("corpus" → "knowledge base",
  "refuter" → "a check"). This rewrites every sentence and adds claims.
- **3C, delete every sentence with a hit.** It cannot delete a title, and
  it loses scope statements the reader needs.
- **The data files.**
  - `parts.json` (10 hits) and `adapters.json` (3) are rendered by
    `advanced parts show` and `hardware compat show`. Live holds none of
    their rows. Decided: the same rule, as file edits with no migration,
    and the census reads both files.
  - `compat_matrix.json`'s one hit is "F650 Funduro", a BMW model.
    Nothing changes.
- **Also found:** "research library", 40 hits (22 checklist, 3 template,
  15 known issues). It is outside F158's list. Proposed: a new finding,
  not this phase.

**Q4. The live changes.**
- **One migration, 086, with one approval (recommended).** The dry-run
  diff shows every changed field, and a summary groups it by finding.
  Each finding's approval would otherwise need its own regression of
  record and its own dry-run and apply (K18).
- **One migration per finding.** The same rows, with 6 regressions of
  about 30 minutes each.

**Decided here, each with its reason:**
- **F152:** the sentence is replaced with the cover as rendered, and the
  test pins the modelling instead of the absence.
- **F153:** the 8 rows gain the SYM spellings 5340 uses (Jet Euro 50, Jet
  Euro 100, Fiddle 50, Joyride 125/150/200). The sources are SYM 7326249
  ("JET 50/100 series and JET EURO 50/100 series"), the Joyride manual
  4604 already quotes (LA12W, LA15W, LA18W), and the Fiddle 50 service
  manual (379). The old spellings stay, so no pair is lost.
- **F171:** the two deletions F171 names.
- **F164:** 262's last wording, completed, goes through this phase's
  refute. If it is killed, it does not ship, and F164 closes with that
  outcome.

Stopped for the operator's choices.

**The operator's choices, verbatim (2026-10-08), in this session:**

> 1A. 2A, with the alias window 2002–2007: the same manual's carburettor
> table names the '06–'07 model (NVK00J); later years stay open. 3A, and
> file the "research library" finding. 4A. One change: if F164's wording
> is killed in the refute, it doesn't ship and F164 stays open with the
> refute's reason, not closed.

So:
- F149's three rows are retired.
- The Metropolitan alias covers 2002–2007. It cites the carburettor
  table's "’06 – ’07 model NVK00J" beside the cover.
- F158 follows 3A, and "research library" gets its own finding.
- One migration, 086, with one approval.
- F164 closes only if its sentence survives the refute.

**Guard, recorded (rule 6):** the edit guard blocked a command that
appended to this log and ran `sed -i` on its status line. Nothing ran.
The edits were made with the Edit tool, and the guard is unchanged.

### 2026-10-08 — v1.0, and the build begins

**v1.0** committed as `10d074e` and pushed. The push guard blocked the
first attempt, because it ran `git commit` and `git push` in one command.
Nothing ran. They were then run as separate commands, and the guard is
unchanged (rule 6).

**Two notes from mapping the 51 rows to their seed files** (19 files):
- **"corpus" sits in five `model` columns as well.** Rows 4548–4552
  (`known_issues_inverter.json`) read "(2020+ Cypher III and 2014-2021
  Cypher II platforms, as this corpus names them)". `kb show` prints the
  model, so these five join 3A's wording pass, though they lie outside
  the six columns Step 0 counted. This is why "corpus" counts 36 over
  every text column but 30 over the six.
- **Row 855's frozen `row_key` contains "corpus":**
  `zero-hv-work-has-a-qualification-requirement-and-this-corpus-does`.
  A key is identity, never edited (F129), and no user reads it. So the
  widened census skips the `row_key` column. Otherwise it would count a
  hit that no edit can remove.

**An API error** cut a turn off while it was reading
`known_issues_honda_electrical.json`. Nothing had been written; the tree
was clean at `10d074e`.

**F149, seed:** the three entries are removed from
`known_issues_honda_electrical.json` (10 → 7 entries; 48 lines deleted,
none added; the file parses).

**F152, seed:** 5338's sentence "The manual prints the model only as CHF50,
and it names no end year." is now "The manual's cover reads 'CHF50/P/S',
'METROPOLITAN™' and '2002–2006', and its carburettor table also lists an
'After ’07 model' (p. 1-6)." The first draft cited p. 1-5. The text layer
put the table after page 9's "1-5" footer, and page 10's own footer reads
"1-6", so the citation was corrected before any refute read it.

**F153, F171, F158, seed and data files:** the edits are made, each with
the Edit tool. One replace-all was an exact string, counted first: the 8 CVT
rows' identical model text. 51 seed rows are changed or removed in 19 files
(the five `model` columns of 4548–4552 included). There are 22 sentences in
`parts.json` and `adapters.json`, more than Step 0's 10 and 3, which counted
only the census's old patterns.

**Step 0 corrected:** `compat_matrix.json`'s note said "1 hit, F650". That
grep required 60 characters before each match, so it missed two: "Phase 144
scenarios exercise compat flow via this slug" and "not in this corpus". The
phase's own data-file test found them. Both are fixed under 3A and refuted
(E, E2 below).

**Found while widening the census:**
- `dtc_codes` P0328 (MV Agusta) says "this project could open". This
  row ships from `dtc_codes/mv_agusta.json`, so 086 changes it on live
  and the seed carries the new text.
- `guidance_interactions.response_json` holds 5 "corpus" in 2 rows. These
  are the model's logged answers (2026-09-16), so the census counts them
  but treats them as operational, as it treats `shops` and
  `customer_notifications`.
- Row 855's frozen key holds "corpus". The census skips `row_key`.
- Two CLI messages say "this project" (`cli/advanced.py:206`,
  `cli/recall_nhtsa.py:46`). They are code strings, not content rows.
  F203 names them.

**Migration 086:** `381_gen086.py` diffs the live copy against a fresh seed
build by key. It writes `core/migration_086_rows.py`: 57 fields in 48 rows,
and 3 retired rows with their 3 make pairs.
- **Its post_apply `content_086`** changes each field through
  `update_known_issue_by_key`, only where the old text is still held, then
  syncs the junction.
- **The SQL** does the deletes, plus the checklist and DTC edits, each
  guarded on its old text.
- **Measured on a live copy:** the model junction gains exactly 48 pairs
  (6 SYM spellings × 8 rows) and loses none; the make junction loses 3.
  After 086, the generator finds 0 differences between the copy and the
  seed.
- **A defect in this new code, found before any commit.** The first
  rollback re-inserted the retired rows into any database, including one
  that never held them (`test_phase380_row_keys`, rolling a fresh build
  back to 84). The rollback now restores them only where a sibling row
  from their seed file is held. 85 → 86 → 85 on a live copy restores
  `known_issues`, both junctions, `checklist_items` and `dtc_codes`
  exactly. This was the phase's own uncommitted code, so it is not
  entered in the bug-fix register.

**F156:** `DATED_MODEL_ALIASES` and `dated_alias` are in `vehicle_resolver`.
`known_issues_for_vehicle(…, year=)` makes a row tier 0 when the junction
pairs it with either name. Diagnose, the video ask route and the priority
scorer pass the vehicle's year. Measured on a fresh build: a 2005 or 2007
Metropolitan has 17 tier-0 rows, the two CHF50 rows among them; 2008, 2018
and no year have 7.

**Parity:** `deploy.seed_parity` now refuses a removed row whose key is
still a seed entry. The deploy skill's text and changelog are updated.

**A consequence of F149 the gate measured.**
- The prompt's safety floor keeps three `critical` rows. Rows 263 and 264
  were critical, and they held two of those places in every Honda prompt.
- With them gone, the floor takes each machine's next critical make-wide
  rows, which displace tier-2 CVT rows:
  - Ruckus 4 → 2 CVT;
  - Grom 1 → 0 (the naming row).
- That is the composition working as designed. Gate 14's unscoped-row pin
  moved from the prompt to the chokepoint: both unscoped CVT rows still
  survive `rows_for_machine` for a manual Grom and a CBR, which is what a
  scoping decision would change.

**Tests:**
- `tests/test_phase381_content_batch.py`, 37 tests;
- Gate 14's F153 and F156 pins inverted, plus a 2018 Metropolitan, and its
  censuses re-measured;
- 354's F152 and F149 pins, and 262's F164 guard, inverted;
- the 1060 count moved to 1057 (the README and four tests);
- `SCHEMA_VERSION` 86;
- 14/14 mutations red (`381_mutate.out`);
- 244G 19 passed;
- the floor 10798 → 10839, by a diff of collected ids against `10d074e`
  in a worktree.

**F164 survived its refute**, with its DMV clause deleted in round 1. So
086 carries it, and F164 closes.

**The refute record is two tables.** `refute_check.py` C4 asks every row
for a document page. 33 claims rest on a document page, and they are the
`## Refuter pass` block, which passes C1–C7. The other 99 rows are wording
checks: each was checked against its own seed row or data file, with no
document to cite. A page for them would be false, so they are a second
table with the same columns, round and outcome rules. They pass C1–C3 and
C5–C7.

**After round 3:** no factual or citation defect is open. One wording
defect remains (the Grom row's opening), and it is F203, which also lists
the build wording the refuters found outside 3A's five words.

**The first `wholetree.sh --full`: 9 failed, 4147 passed.** Each was a pin
or a list that this phase's content moves, or a defect in its own
uncommitted code:
- 209B: `update_known_issue_by_key` left the orphan allowlist. Its entry
  said it would go stale "the day the first one lands", and 086 is that
  day. ORPHAN_COUNT 119 → 118.
- 208: three docs said 1060 known issues (`docs/guide/quickstart.md`,
  `docs/guide/install.md`, `docs/launch-checklist.md`). They now say 1057.
- 256: the rollback built a table name from a variable. The two junction
  tables are now written out literally.
- 255C: the PCX's tier table, 170 → 167 (F149's rows reached it at
  `make_wide`).
- 359, five tests:
  - They compared 072 with today's seed, which 086 has since moved on for
    4615, the F158 rows and item 18.
  - Their `seeded` fixture and the round-trip test now roll the head build
    back to 85, the seed as 072 knew it.
  - The F171 assertion takes the new item 18 text.
- **The rollback's ids, a second defect in this new code before any
  commit.** The rollback re-inserted the retired rows with live's ids, which
  a fresh build may already use, and `INSERT OR IGNORE` would drop them
  silently. They now come back under a new id, and their pairs are found by
  key.

After the fixes: the seven files 417 passed; the mutations re-run 14/14
red.

**The second `wholetree.sh --full`: 3 failed, 4152 passed.**
- **The floor, 2 tests:** 10838 collected against 10839. Removing the
  orphan entry also removed its parametrised id in 209B. The floor is now
  10838, with the reason beside it.
- **255B's migration-065 round trip:** a third defect in 086's rollback,
  before any commit. The sequence:
  - The test rolls a seeded build back to 64, which restores F149's rows.
  - It replays 65 → 86, and 085's post_apply keys those rows `auto-…`,
    because today's seed no longer holds them.
  - 086's forward delete is by key, so it leaves them.
  - The second rollback restored them again, and 085's rollback then
    failed on the prose identity index.

**A third defect in one build, so stop and find the shared cause (the
working rule).** All three are one cause. A SQL rollback has no record
of what its forward step deleted, so 086's rollback must infer whether
each retired row was there before, and each defect was an edge of that
inference:
- a database that never held the seed;
- a fresh build whose ids differ from live's;
- a row still present under a derived key.

The inference is now written as three guards:
- the row's seed file was held (a sibling row);
- its prose identity is absent (085's old unique index);
- it comes back under live's id where that id is free, else a new one.

On a copy of live, 85 → 86 → 85 restores `known_issues`, both junctions,
`checklist_items` and `dtc_codes` exactly, ids included. The alternative,
a table that keeps what 086 deleted, would add a schema object for a
rollback live is not expected to run, so the guards stand. Forward, live's
three rows carry their real keys from 380 (measured), so the delete by
key removes them.

**Build committed** as `33ef12e` and pushed, after `wholetree.sh --full`
on the staged tree passed (4155 passed). `regression.sh` then refused,
because it wants a `--full` record of the committed HEAD. So `--full` ran
on `33ef12e` (4155 passed, record written) before it.

**The first regression: 10836 passed, 2 failed, at `33ef12e`.** Both are
in `tests/test_phase33_honda_electrical.py`, which is outside the
whole-tree set:
- the Honda electrical file's count (10 → 7);
- its critical rows: the file's only two were F149's 263 and 264, so 0
  remain.

Both pins move, with the reason beside each. This is a pin the phase
missed, not a defect in shipped code, so it is not entered in the
bug-fix register. No other test reads the file. The regression of record
is re-run on the commit that carries the fix.

**Regression of record** (after `wholetree.sh --full` on `7dd69c9`, 4155
passed, record written):

Regression of record: 10838 passed, 0 failed, 0 skipped, 0 errors at `7dd69c9` (32 min 58 s wall, `python -m pytest -n auto --dist load`, exit 0)

## Refuter pass

Rounds 1–3 of the refute skill, run by Opus subagents, each reading its sources itself (renders where layout mattered). Files A, B, C1, C2, D are round 1; r2 round 2; r3 round 3; E and E2 the compat_matrix diffs' rounds 1 and 2. Only rows that rest on a document page are here; the wording checks follow.

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| F152, honda-honda-s-carburetted-chf50-charges-through-a-three-phase, description: cover reads 'CHF50/P/S', 'METROPOLITAN™', '2002–2006' | kept | "CHF50/P/S METROPOLITAN™ 2002–2006" | Honda CHF50/P/S service manual (chf50_service_mirror.pdf), cover, PDF p. 1 (image-only, rendered) | 1 · none · kept |
| F152, same sentence: carburettor table lists an 'After ’07 model' (p. 1-6) | kept | "Carburetor identification number ’06 – ’07 model NVK00J After ’07 model NVK00K" | CHF50 service manual, printed p. 1-6 (PDF p. 10), "FUEL SYSTEM SPECIFICATIONS (After ’05 model)" | 1 · none · kept |
| F152, rest of the row against the new sentence (no contradiction: row keeps year_start 2002, no year_end, and its earlier "'02 - '05 model and 'After '05' editions") | kept | "FUEL SYSTEM SPECIFICATIONS (’02 - ’05 model)" | CHF50 service manual, printed p. 1-6 (PDF p. 10) | 1 · none · kept |
| F153, piaggio-no-scooter-owner-s-manual-publishes-a-belt-width-or-wear, model | kept | "This service manual contains the technical data of each component inspection and repair for the SANYANG JET 50/100 and JET Euro 50/100 series motorcycle." | SYM manual 7326249, Forward, PDF p. 2 (cover rendered: "JET 50/100", "JET Euro 50/100", "SERVICE MANUAL") | 1 · none · kept |
| F149, PCX150: regulator/rectifier inside the ECM (p. 20-4) | kept | "• The regulator/rectifier is built into the ECM." | Honda PCX150 2013–2017 service manual, printed p. 20-4 (text-layer page 390) | 1 · none · kept |
| F149, PCX150: stator leads Red/yellow, Red/white, Red/blue (p. 6-6) | kept | "7. Stator Coil Circuit Inspection ... Disconnect the ECM 3P (Black) connector. ... CONNECTION: Red/yellow - Red/white Red/yellow - Red/blue Red/white - Red/blue" | PCX150 service manual, printed p. 6-6 (ELECTRIC STARTER, text-layer page 168) | 1 · none · kept |
| F149, PCX150: charging standard relative to battery voltage (p. 20-9) | kept | "With the headlight on high beam, restart the engine. Measure the voltage on the multimeter when the engine runs at 5,000 rpm. STANDARD: Measured BV < Measured CV < 15.5 V" | PCX150 service manual, printed p. 20-9 (text-layer page 395, between 20-8 and 20-10) | 1 · none · kept |
| F149, CHF50 tree ends at "Faulty ECM" (p. 15-5) | kept | "6. REGULATOR/RECTIFIER SYSTEM INSPECTION Inspect the regulator/rectifier system on the ECM side (page 15-9). Are the results of checked continuity and resistance correct? YES - Faulty ECM." | CHF50 service manual, printed p. 15-5 (PDF p. 253) | 1 · none · kept |
| F149, the retired rows' "3-pin yellow connector" contradicts both manuals | kept (retirement stands) | "Disconnect the alternator/starter 3P (Black) connec-tor." | CHF50 service manual, printed p. 15-8; PCX150 p. 6-6 likewise "ECM 3P (Black) connector" | 1 · none · kept |
| F149, the retired rows' fixed 13.5–14.5 V window contradicts both manuals | kept (retirement stands) | "Measured battery voltage < Measured charging voltage < 15.5 V" | CHF50 service manual, printed p. 15-5; PCX150 p. 20-9 "Measured BV < Measured CV < 15.5 V" | 1 · none · kept |
| F156, a 2007 Metropolitan is a CHF50 | kept | "’06 – ’07 model NVK00J" | CHF50/P/S METROPOLITAN™ service manual, printed p. 1-6 (PDF p. 10) | 1 · none · kept |
| F156, a 2018 Metropolitan is not a CHF50 | kept | "2018 OWNER'S MANUAL NCW50 Metropolitan" | 2018 Metropolitan owner's manual 31GJB620 (om_AHM_NCW50_2018_Metropolitan_31GJB620_0.pdf), cover, PDF p. 1 (rendered); text p. 592 line "PGM-FI (Programmed Fuel Injection) malfunction indicator" | 1 · none · kept |
| 18a: deleting "Rocking play is loose adjustment;" adds no claim, and it removes the F171 defect (the page names no cause) | kept | "» If there is detectable play: – Adjust the steering head bearing play. ( p. 74)" | KTM 2022 250/300 EXC TPI owner's manual (22_3214421_en_OM.pdf) PDF p. 76 (printed 74) | 1 · none · kept |
| 18b: "The KTM manual notes that running with play can damage the bearings and the bearing seats in the frame over time (PDF p. 76)" | kept | "If the vehicle is operated for a lengthy period with play in the steering head bearing, the bearings and the bearing seats in the frame can become damaged over time." | 22_3214421_en_OM.pdf PDF p. 76, in the "Info" box under 12.13 | 1 · none · kept |
| 18c: "The KTM manual" is the 2022 250/300 EXC TPI manual the item's description cites | kept | "OWNER'S MANUAL 2022 250 EXC TPI … 300 EXC TPI … Art. no. 3214421en" | 22_3214421_en_OM.pdf PDF p. 1 | 1 · none · kept |
| 18d: after the deletion, the next sentence's "the same manual" still resolves, and its detent claim holds | kept | "» If detent positions are detected: – Adjust the steering head bearing play. ( p. 74) – Check the steering head bearing and change if necessary." | 22_3214421_en_OM.pdf PDF p. 76 | 1 · none · kept |
| 86a: the KTM 2019 690 Duke owner's manual, PDF p. 54 | kept | "7.16 "TC/ABS" … Note Voiding of the government approval for road use and the insurance coverage If the ABS is switched off completely, the vehicle's approval for road use is invalidated." | KTM 2019 690 Duke OM (19_3213923_en_OM.pdf) PDF p. 54 (printed 52); title "OWNER'S MANUAL 2019 690 Duke Art. no. 3213923en", PDF p. 1 | 1 · none · kept |
| 86b: the KTM 2019 1090 Adventure R owner's manual, PDF p. 183 | kept | "Note Voiding of the government approval for road use and the insurance coverage If the ABS is switched off completely, the vehicle's approval for road use is invalidated." | KTM 2019 1090 Adventure R OM (19_3213917_en_OM.pdf) PDF p. 183 (printed 181); title "OWNER'S MANUAL 2019 1090 Adventure R Art. no. 3213917en", PDF p. 1 | 1 · none · kept |
| 86c: "in a note on switching the ABS off completely": a note, not a warning | kept | "Note" (the render shows a plain Note label; the grey "Warning" box below it, "Danger of accidents Driving aids can only prevent a rollover within the physical limitations.", does not mention insurance) | 19_3213917_en_OM.pdf PDF p. 183 (render); 19_3213923_en_OM.pdf PDF p. 54 (render, Note label) | 1 · none · kept |
| 86d: "headed "Voiding of the government approval for road use and the insurance coverage"" | kept | "Voiding of the government approval for road use and the insurance coverage" (the bold lead-in of the Note on both renders) | 19_3213917_en_OM.pdf PDF p. 183; 19_3213923_en_OM.pdf PDF p. 54 | 1 · none · kept |
| 86e: "EPA's fact sheet, under "WARRANTY ISSUES"" | kept | "WARRANTY ISSUES" (the heading on the render, right column); "FACT SHEET Defeat Device and Tampering March 2020". It is the only EPA fact sheet in `research/motodiag` by file name | EPA Fact Sheet, Defeat Devices and Tampering, March 2020 (system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf) PDF p. 2 | 1 · none · kept |
| 86f: the EPA quote, verbatim, at PDF p. 2 | kept | "Tampering can void manufacturer warranties and insurance agreements." | same EPA fact sheet, PDF p. 2 (of 2) | 1 · none · kept |
| 86g: "where cover can be lost" is true of the KTM notes | kept | "Voiding of the government approval for road use and the insurance coverage" (the body sentence names only road approval; "insurance" appears only in the heading, as 262 S1c recorded, and the clause attributes it to the heading) | 19_3213917_en_OM.pdf PDF p. 183; 19_3213923_en_OM.pdf PDF p. 54 | 1 · none · kept |
| 86h: "where cover can be lost" is true of EPA's line, which covers both warranties and insurance agreements | kept | "Tampering can void manufacturer warranties and insurance agreements." A voided insurance agreement is lost cover, and the clause quotes the warranty half in full rather than hiding it | EPA fact sheet PDF p. 2 | 1 · none · kept |
| 86i: "among them": the list is not exhaustive, and does not claim to be | kept | "Note Voiding of the government approval for road use and the insurance coverage If the ABS is switched off completely…" (a third KTM page that the clause does not name) | 19_3213923_en_OM.pdf PDF p. 110 (printed 108) | 1 · none · kept |
| 86j: "the California DMV's salvage pages, which give the insurance company's part in a total loss" (as a factual statement) | kept | "The insurance company or its designee (salvage pool or registration service) or the owner must apply for the salvage certificate within 10 days from the date the insurance company makes a total loss settlement with the owner."; "If you receive a settlement from your insurance company, then the insurance company is responsible for getting the certificate within 10 days from the date of the settlement." | California DMV VIRP manual 19.075 Salvage Certificate (HTML) p. 1; "Total Loss Salvage & Non-Repairable Vehicles" (HTML) p. 1; also 19.015 Definitions p. 1 ("the owner or insurance company considers it uneconomical to repair") and "Junk/Revived Salvage Vehicles" p. 1 ("previously reported to DMV as a total loss by the owner or insurance company") | 1 · none · kept |
| 86k: the DMV pages fall under "where cover can be lost" (a reading the sentence allows: "elsewhere it appears where cover can be lost — among them … — and in the California DMV's salvage pages") | killed | "If you receive a settlement from your insurance company, then the insurance company is responsible for getting the certificate within 10 days from the date of the settlement." The pages describe cover paying out as a total-loss settlement. No fetched DMV page says cover is lost | DMV "Total Loss Salvage & Non-Repairable Vehicles" (HTML) p. 1; VIRP 19.075 (HTML) p. 1 | 1 · wording · deleted |
| 86l: "elsewhere": the sentence's subject is "its owner's manuals", but two of the named sources (EPA, DMV) are not owner's manuals | kept | "FACT SHEET Defeat Device and Tampering March 2020" (a regulator document, not an owner's manual). Naming the documents resolves "elsewhere" to "elsewhere in the library", so no reader is misled about what EPA is | EPA fact sheet PDF p. 2 | 1 · none · kept |
| aprilia-and-mv-agusta-a-generic-scan-tool… fix_procedure: "this project's" to "MotoDiag's" Aprilia and MV tables | kept | "the codes shipped in MotoDiag's Aprilia and MV Agusta tables were chosen for exactly this divergence" | known_issues_aprilia_mv_electrical.json, aprilia-and-mv-agusta-a-generic-scan-tool-is-more-dangerous-on-an-aprilia-than-on; tables exist: knowledge/seed/dtc_codes/aprilia.json (P0510 "rear wheel radius"), dtc_codes/mv_agusta.json; seed row (no external document) | 1 · none · kept |
| MV DTC title: MotoDiag's table does not decode the MV manufacturer block | kept | "MV Agusta uses a genuine manufacturer fault-code block that MotoDiag's table does not decode" | known_issues_aprilia_mv_electrical.json, mv-agusta-mv-agusta-uses-a-genuine-manufacturer-fault-code-block-that; dtc_codes/mv_agusta.json holds 6 codes (P0328, P0208, P0638, P0639, P0561, P0501), none of them P1/U1 | 1 · none · kept |
| MV DTC: MotoDiag ships MV rows only for P0xxx codes | kept | "MotoDiag ships MV rows only for codes whose meaning could be established and explained, all of which are in the standard P0xxx range." | same row; dtc_codes/mv_agusta.json (all 6 are P0xxx) | 1 · none · kept |
| R2-10 item 86 (crash_support_v1 #7) diagnosis_if_fail, with the DMV tail deleted | kept | "Note Voiding of the government approval for road use and the insurance coverage If the ABS is switched off completely, the vehicle's approval for road use is invalidated." (690 Duke p. 54 and 1090 Adventure R p. 183, the same words); "WARRANTY ISSUES Tampering can void manufacturer warranties and insurance agreements." (EPA p. 2) | KTM 2019 690 Duke OM (19_3213923_en_OM.pdf) PDF p. 54; KTM 2019 1090 Adventure R OM (19_3213917_en_OM.pdf) PDF p. 183; EPA fact sheet (system_files_documents_2021-11_epafactsheetreaftermarketddsandtampering.pdf) PDF p. 2 | 2 · none · kept |
| R3-3 the sentence after the Cypher III lead: the 2025 owner's manual (8811984-AF), which covers the S, SR, SR/F and SR/S, sits in the Cypher III paragraph, so the 2025 S is implied to be Cypher III. Deleting "2024+ S" removed the only place the row said so outright | kept | "Zero S equipped with: Z-Force® ZF14.4 lithium ion power pack, 3.0 kW onboard charger, Cypher III operating system" | 2025 Zero owner's manual 8811984-AF, §1.2 "About This Manual" (PDF page 8), ~/Downloads/2025 25 FST Street NA - English- 8811984-AF.pdf | 3 · none · kept |

## Wording checks, against the seed row (no document page)

Each row checks a deletion or replacement against its own seed row or data file. The same columns and the same round rule as the Refuter pass; no page, because none exists.

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| F153, piaggio-every-maker-publishes-a-roller-wear-limit-in-a-service, model gains SYM Jet Euro 50/100, Fiddle 50, Joyride 125/150/200 | kept | "OD of weight roller 15.92~16.08 15.40" | SYM Fiddle 50 service manual (sym_fiddle50_sm.pdf; cover reads "Fiddle 50 SERVICE MANUAL"), ch. 7 maintenance information; same figures as the row's JET 50/100 manual (cover "JET 50/100 / JET Euro 50/100 SERVICE MANUAL") | 1 · none · kept |
| F153, piaggio-kickstart-backup-and-the-scooter-named-kick-that-has-none, model | kept | "Starting System Electrical & kick" | SYM Fiddle 50 service manual, specification page (Make SANYANG MODEL FA05 Series), ch. 1; carburetted (pilot screw), so consistent with the row's "kickstart on carburetted machines" | 1 · none · kept |
| F153, piaggio-no-maker-publishes-a-fault-code-for-a-cvt-the-transmission, model | kept | "Transmission C.V.T." | SYM JET 50/100 & JET Euro 50/100 service manual 7326249, specification pages "Make SANYANG MODEL JET 50 SERIES" / "JET 100 SERIES", ch. 1 | 1 · none · kept |
| F153, piaggio-the-clutch-side-one-maker-publishes-an-engagement-speed-one, model | kept | "Thickness of clutch weight 4.0~4.1 2.0" | SYM Fiddle 50 service manual, ch. 7 maintenance information (and identically in 7326249 ch. 7) | 1 · none · kept |
| F153, piaggio-three-unrelated-components-are-all-called-a-drive-belt-and-a, model | kept | "Primary Reduction BELT" | SYM Fiddle 50 service manual, specification page (FA05 Series), ch. 1 | 1 · none · kept |
| F153, piaggio-what-a-scooter-cvt-is-in-the-makers-own-words-and-why, model | kept | "Make SANYANG MODEL LA12W" … "Transmission C.V.T." (also LA15W, LA18W) | SYM Joyride service manual 7429958 (cover rendered: "Joyride SERVICE MANUAL"; Forward: "Sanyang JOYRIDE 125/150/200"), ch. 1 specification pages | 1 · none · kept |
| F153, piaggio-what-the-makers-themselves-say-a-cvt-symptom-means-quoted, model | kept | "1. Clutch ling spring broken" / "2. Clutch outer cover stuck with clutch balance weights" | SYM Fiddle 50 service manual, ch. 1 trouble diagnosis "CLUTCH, DRIVING AND DRIVING PULLEY" (same lines in 7326249 ch. 1) | 1 · none · kept |
| F171, yamaha-what-the-regulator-record-shows-for-scooter-cvts-one, fix_procedure: "conclude only that a sweep found one" | kept | "A sweep of 3,545 make, model and year combinations ... collected 1,125 distinct campaigns, of which exactly one touches a scooter CVT component" | the row's own description (known_issues_cvt.json) | 1 · none · kept |
| zero-controller-firmware-is-a-service-item-on-every-make-and-none, model: "as MotoDiag names them" | kept | "Zero, Cypher II platform (MotoDiag's name for the 2014-2021 S, SR, DS, DSR)" | known_issues_thermal/inverter seed rows (working tree), the one place the 2014-2021 range is defined | 1 · none · kept |
| zero-how-a-motor-controller-fault-reaches-the-rider-on-each-make, model | kept | "Zero, Cypher II platform (MotoDiag's name for the 2014-2021 S, SR, DS, DSR)" | same | 1 · none · kept |
| zero-no-electric-motorcycle-maker-publishes-an-overcurrent-phase, model | kept | "Zero, Cypher II platform (MotoDiag's name for the 2014-2021 S, SR, DS, DSR)" | same | 1 · none · kept |
| zero-what-reads-the-motor-controller-on-each-make-zero-s-dealer, model | kept | "Zero, Cypher II platform (MotoDiag's name for the 2014-2021 S, SR, DS, DSR)" | same | 1 · none · kept |
| zero-what-the-motor-controller-is-on-each-make-a-name-and-a, model | kept | "Zero, Cypher II platform (MotoDiag's name for the 2014-2021 S, SR, DS, DSR)" | same | 1 · none · kept |
| all-european-makes-five-valve-train… description: "for this project" to "for this entry"; "this corpus documents" to "MotoDiag documents" the 690 LC4 as rocker-arm | kept | "MotoDiag documents the single-cylinder 690 LC4 as a rocker-arm train — see the KTM 690 rocker-bearing entry in the European differentials file" | known_issues_european_intervals.json, all-european-makes-five-valve-train-job-types-across-the-european-makes-and-the; target exists: known_issues_european_differentials.json, ktm-ktm-690-lc4-valve-train-failure-is-the-roller-rocker-bearing; seed row (no external document) | 1 · none · kept |
| all-european-makes-five-valve-train… fix_procedure: "the corpus already holds" to "MotoDiag already holds" | kept | "MotoDiag already holds a contradicting engine in the 690 LC4's rocker-arm train" | known_issues_european_intervals.json, same key; known_issues_european_differentials.json, ktm-ktm-690-lc4-valve-train-failure-is-the-roller-rocker-bearing; seed row (no external document) | 1 · none · kept |
| aprilia-nineteen… description: "this project already documents" to "MotoDiag already documents" the torque-monitor case | kept | "MotoDiag already documents one such case on the ride-by-wire torque monitor" | known_issues_aprilia_mv_electrical.json, aprilia-nineteen-aprilia-fault-codes-never-reach-the-instrument; backed by known_issues_aprilia_dorsoduro.json, aprilia-the-shiver-s-ride-by-wire-self-learns-at-every-key-on-so-a: "a torque-monitor safety layer can shut the engine down and store a code the dashboard never displayed"; seed row (no external document) | 1 · none · kept |
| aprilia-the-sr-max… description: clause "nothing in this file about the ride-by-wire…" deleted | kept | "Nothing in the V-twin machines' documentation applies to it." | known_issues_aprilia_dorsoduro.json, aprilia-the-sr-max-is-a-scooter-not-a-motorcycle-it-shares-nothing; fix step 2 still carries it: "Do not carry anything from the Shiver or Dorsoduro documentation across"; seed row (no external document) | 1 · none · kept |
| bmw-bmw-supplies-the-hexhead… description: clause "and one an earlier research pass in this project produced" deleted | kept | "A widely repeated statement is that BMW will not supply hexhead final-drive internals and sells only the complete drive. No document stating it was found." | known_issues_european_parts.json, bmw-bmw-supplies-the-hexhead-final-drive-only-as-a-complete-unit; seed row (no external document) | 1 · none · kept |
| bmw-the-bmw-elast… description: research-pass and refuter sentences deleted, "the research had paired them the wrong way round" deleted | killed | title: "The BMW ELAST belt designation 'disagreement' has an explanation"; NEW description never states a disagreement; deleted fact clause: "sources disagree on which Contitech designation matches which BMW alternator belt" | known_issues_european_parts.json, bmw-the-bmw-elast-belt-designation-disagreement-has-an; seed row (no external document) | 1 · wording · fixed |
| ducati-desmo-service-intervals… fix_procedure: "read for this project" to "read for this entry" | kept | "On the manufacturer schedules read for this entry the valve row is marked under distance columns only" | known_issues_ducati_desmo.json, ducati-desmo-service-intervals-vary-by-generation-a-remembered; seed row (no external document) | 1 · none · kept |
| ducati-ducati-publishes-its-desmo-labour… description: "a detail a refuter corrected, because" deleted | kept | "Group 3 has no oil-service column at all — a shop reading one group's column into another misquotes." | known_issues_european_intervals.json, ducati-ducati-publishes-its-desmo-labour-in-six-minute-units-and; seed row (no external document) | 1 · none · kept |
| energica-energica-exposes-ev-live-data… description: "covered in this corpus" to "MotoDiag covers" | kept | "which is not true of the other electric marques MotoDiag covers" | known_issues_energica.json, energica-energica-exposes-ev-live-data-through-standard-obd-pids-not; backed by known_issues_zero.json "What a generic OBD-II scan tool does on a Zero is nothing" and known_issues_livewire.json "not a generic scan tool"; seed row (no external document) | 1 · none · kept |
| energica-energica-publishes-127… description: "in this corpus" to "MotoDiag covers" | kept | "This is the finding that most distinguishes Energica from the other electric marques MotoDiag covers." | known_issues_energica.json, energica-energica-publishes-127-fault-codes-in-standard-sae-format; same Zero and LiveWire rows; seed row (no external document) | 1 · none · kept |
| energica-energica-publishes-127… fix_procedure: "in this corpus" to "MotoDiag covers" | kept | "Unlike the other electric marques MotoDiag covers, Energica implements generic OBD services and Mode 3 returns stored codes." | known_issues_energica.json, same key; seed row (no external document) | 1 · none · kept |
| genuine-what-genuine-publishes-free… description: "the corpus can carry" to "MotoDiag can carry" | kept | "So for these machines MotoDiag can carry what an owner's manual states and no more" | known_issues_yamaha_kymco_sym_genuine.json, genuine-what-genuine-publishes-free-what-it-gates-and-a-warranty; seed row (no external document) | 1 · none · kept |
| honda-a-completed-grom-fuel-pump-recall… description: "in this corpus" to "in MotoDiag" | kept | "This is a different mechanism from the other repeat campaigns in MotoDiag" | known_issues_honda_small.json, honda-a-completed-grom-fuel-pump-recall-is-not-proof-of-a-repaired; other repeat campaigns exist, e.g. known_issues_triumph_triples.json, triumph-the-speed-triple-1200-s-second-radiator-fan-recall-exists; kept, unchanged claim; seed row (no external document) | 1 · none · kept |
| honda-honda-s-current-owner-s-manuals… description: "appears in this corpus" to "appears in MotoDiag" | kept | "no valve clearance, torque table or fault-code procedure for the Ruckus, Metropolitan or PCX appears in MotoDiag" | known_issues_honda_small.json, honda-honda-s-current-owner-s-manuals-stopped-carrying-torque; searched all seed rows for Ruckus/PCX/Metropolitan with valve clearance/torque/fault code: only Piaggio CVT rows quote a "PCX150 2013-2017 service manual", on the CVT, with no clearance, torque or code; kept, unchanged claim | 1 · none · kept |
| honda-what-honda-s-own-documents-say-about-modifying-a-grom… description: opening sentence deleted | kept | NEW opening: "What Honda does publish sits in the GROM125 service manual (Date of Issue August 2013) and is narrower than it first appears."; deleted fact clause: "almost nothing about it is documented by Honda" | known_issues_honda_small.json, honda-what-honda-s-own-documents-say-about-modifying-a-grom-four; seed row (no external document) | 1 · wording · open F203 |
| ktm-adventure-and-super-adventure… description: last sentence ("This project hit the same trap in its own corpus…") deleted | kept | "The engines are different, the frames are different, the fuel system architecture is different, and the service intervals are different." | known_issues_ktm_adventure.json, ktm-adventure-and-super-adventure-are-different-ktm-machines-and; seed row (no external document) | 1 · none · kept |
| ktm-cam-chain-starter-clutch… description: "This corpus already carries" to "MotoDiag already carries" | kept | "MotoDiag already carries the starter procedures as cross-platform entries (relay, motor, and the sprag or one-way starter clutch)" | known_issues_ktm_engines.json, ktm-cam-chain-starter-clutch-and-valve-clearance-faults-on-an; backed by known_issues_cross_platform_starting.json keys honda-starter-relay-contact-corrosion-clicking-but-no-crank-across, harley-davidson-starter-motor-brush-wear-and-commutator-degradation-slow-or, kawasaki-starter-clutch-sprag-one-way-bearing-failure-starter-spins; cam chain tensioner rows e.g. honda-cam-chain-tensioner-cct-rattle-all-f-series; seed row (no external document) | 1 · none · kept |
| ktm-cam-chain-starter-clutch… causes: "in this corpus" to "in MotoDiag" | kept | "Diagnostic procedures for all three already existing in MotoDiag" | known_issues_ktm_engines.json, same key; same backing rows; seed row (no external document) | 1 · none · kept |
| ktm-ktm-adventure-tubeless-rim-seal-bands… description: research-pass sentence deleted whole | killed | deleted fact: "the R variants, which take the 21-inch band; the catalogue rows here use exact model names for that reason"; catalogue: "Tubeless rim seal band, 21-inch front (R)" / "Tubeless rim seal band, 19-inch front (non-R)" | known_issues_european_parts.json, ktm-ktm-adventure-tubeless-rim-seal-bands-and-bead-gaskets-are; src/motodiag/advanced/data/parts.json lines 1296 and 1341; seed row (no external document) | 1 · factual · fixed |
| ktm-ktm-publishes-service-minutes… fix_procedure: "in this corpus" to "in MotoDiag" | kept | "The single-cylinder 690 LC4 is documented in MotoDiag as a rocker-arm train, not bucket-and-shim" | known_issues_european_intervals.json, ktm-ktm-publishes-service-minutes-and-the-valve-service-is-fifty; known_issues_european_differentials.json, ktm-ktm-690-lc4-valve-train-failure-is-the-roller-rocker-bearing; seed row (no external document) | 1 · none · kept |
| KTM LC8 fiche: the research-pass and refuter narration is deleted, and the page's truncation note is kept | killed | "The page **states that some compatible models are not shown** — the assignment list is truncated. So the absence of the later twins from that page is not evidence about them" | known_issues_european_parts.json, ktm-the-ktm-lc8-fiche-pages-for-the-balancer-seal-and-starter | 1 · wording · fixed |
| Kymco/SYM: "once in the corpus" removed; JASO appears in the Wolf CR300i | kept | "the oil standard JASO, for instance, appears in none of the seven Kymco manuals but does appear in SYM's Wolf CR300i, as 'SAE 10W-40, API SJ, JASO MA'" | known_issues_yamaha_kymco_sym_genuine.json, kymco-kymco-and-sym-do-show-fault-codes-on-the-dash-under-names-no | 1 · none · kept |
| MV coupon ladder: the "after a refuter caught a misread" clause is deleted | kept | "Drawn from the Turismo Veloce 800 user's manual MY2018–20, the coupon table read visually." | known_issues_european_intervals.json, mv-agusta-mv-agusta-s-coupon-ladder-starts-with-a-merged-cell-and | 1 · none · kept |
| MV DTC: the failure MotoDiag documents on the Aprilia side | kept | "Writing speculative meanings for those codes would produce exactly the failure MotoDiag documents on the Aprilia side — a confident, wrong answer" | same row; the counterpart is known_issues_aprilia_mv_electrical.json, aprilia-and-mv-agusta-a-generic-scan-tool-is-more-dangerous-on-an-aprilia-than-on ("Aprilia's codes look standard and are not") | 1 · none · kept |
| MV DTC causes: "for this project" removed | kept | "No MV Agusta primary fault-code document could be opened, so the block is named but not decoded" | same row, causes[3] | 1 · none · kept |
| MV triple: "when this file was written" becomes "when this entry was first written" | kept | "For the F3 675 the commonly quoted valve interval could not be confirmed when this entry was first written. **MV's own maintenance manuals resolve it**" | known_issues_mv_agusta_triple.json, mv-agusta-mv-triple-service-intervals-must-come-from-the-specific | 1 · none · kept |
| MV rim band: the "per this project's standing decision" sentence is deleted | kept | "So there is no consumable to order here; a spoked-wheel complaint on these machines is a frame-number question and then a wheel, not a band." | known_issues_european_parts.json, mv-agusta-no-mv-agusta-rim-band-part-could-be-established-the | 1 · none · kept |
| Piaggio belt limit: MotoDiag already carries the 125-class figures | kept | "MotoDiag already carries the 125-class figures against the manuals that publish them." | known_issues_cvt.json, piaggio-piaggio-s-belt-limit-is-three-different-numbers-and-one; supported by known_issues_vespa_piaggio.json ("The Beverly 125 service station manual … gives the drive belt a minimum width of 21.5 mm against a standard of 22.5 plus or minus 0.2 mm") | 1 · none · kept |
| Drive belt: "In this corpus" becomes "In MotoDiag" (unchanged claim) | kept | "In MotoDiag the phrase drive belt names three mechanically unrelated things, and nothing in a text search separates them." | known_issues_cvt.json, piaggio-three-unrelated-components-are-all-called-a-drive-belt-and-a; the named rows exist: harley_vrsc harley-davidson-drive-belt-tensioner-bearing-failure, livewire harley-davidson-single-speed-gearbox-no-clutch-and-a-belt-with-its-own, european_differentials bmw-bmw-boxer-alternator-belts-come-in-two-incompatible-types | 1 · none · kept |
| Drive belt: the "eight entries" measurement sentence is deleted | kept | "It carries all the drive and is replaced as a wear item on a published interval. The practical consequence is that a scooter owner's question and a cruiser owner's question have the same words in them" | same row | 1 · none · kept |
| Yamaha nameplate causes: "a corpus" becomes "a document" | kept | "Searching a document or a recall record for a marketing name the document never uses" | known_issues_yamaha_kymco_sym_genuine.json, yamaha-a-yamaha-scooter-names-itself-only-in-some-model-years-so | 1 · none · kept |
| Yamaha carbs: MotoDiag's row on the three Yamaha engines ties the YW50A to the Zuma 50 and carries the carburettor makers | kept | "MotoDiag's row on the three Yamaha engines ties the YW50A to the Zuma 50, and it already carries the carburettor makers and types" | known_issues_small_engine_carbs.json, yamaha-yamaha-s-carburetted-scooters-owner-s-manuals-leave; supported by yamaha-one-yamaha-scooter-nameplate-covers-three-different-engines ("The Zuma 50 through model year 2011 (cover code YW50A …) … a Teikei carburettor") | 1 · none · kept |
| Zero controller fault: "Cypher III platform (MotoDiag's name for the 2020+ SR/F, SR/S, DSR/X and 2024+ S, DS, DSR)" | killed | "Zero, Cypher III platform (MotoDiag's name for the 2020+ SR/F, SR/S, DSR/X and 2024+ S, DS, DSR)" | known_issues_inverter.json, zero-how-a-motor-controller-fault-reaches-the-rider-on-each-make; contradicted by known_issues_zero.json, zero-cypher-ii-or-cypher-iii-decides-which-procedures-and-which ("The dealer bulletin assigns the Cypher III platform to the SR/F and SR/S families") | 1 · factual · fixed |
| Zero controller fault: "Cypher II platform (MotoDiag's name for the 2014-2021 S, SR, DS, DSR)" | killed | "Zero, Cypher II platform (MotoDiag's name for the 2014-2021 S, SR, DS, DSR)" | known_issues_inverter.json, same row; contradicted by known_issues_zero.json, same row ("against the earlier Cypher II bikes, which take a different firmware lineage entirely") | 1 · factual · fixed |
| HV title: "this corpus" becomes "MotoDiag" | kept | "HV work has a qualification requirement, and MotoDiag does not state what yours is" | known_issues_electric_hv_safety.json, zero-hv-work-has-a-qualification-requirement-and-this-corpus-does | 1 · none · kept |
| HV description: MotoDiag states no qualification level for any territory (unchanged claim) | kept | "MotoDiag does not state a qualification level, a course, a certificate or a legal threshold for any territory" | same row; a seed grep for certified/certification/qualified/IMI/NFPA/OSHA/HV training found only "can only be preformed by a certified ELW dealer" (known_issues_inverter.json), a manufacturer authorisation, not a qualification level | 1 · none · kept |
| Zero temperature: "(the corpus's Cypher II)" becomes "(MotoDiag's Cypher II)" | kept | "On the 2014-2021 S, SR, DS and DSR (MotoDiag's Cypher II), the 2021 owner's manual (88-09447-01) says" | known_issues_thermal.json, zero-motor-and-controller-temperature-on-each-make-a-gauge-with | 1 · none · kept |
| Regen causes: "in this corpus" becomes "MotoDiag covers" | killed | "Expecting car-style one-pedal driving that no motorcycle maker MotoDiag covers offers" | known_issues_regen.json, zero-no-electric-motorcycle-maker-offers-a-one-pedal-stop-every | 1 · wording · deleted |
| Liquid-cooled battery: "the platform this corpus calls Cypher II" becomes "the platform MotoDiag calls Cypher II" | kept | "On the 2014-2021 S, SR, DS and DSR (the platform MotoDiag calls Cypher II), Zero's 2020 service manual" | known_issues_thermal.json, zero-nothing-on-any-make-is-documented-as-a-liquid-cooled-battery | 1 · none · kept |
| Liquid-cooled battery causes: "in this corpus" becomes "MotoDiag covers" | killed | "Assuming a liquid-cooled battery, which no maker MotoDiag covers documents" | same row, causes[0] | 1 · wording · deleted |
| Cooling loop: "(the corpus's Cypher II)" becomes "(MotoDiag's Cypher II)" | kept | "On the 2014-2021 S, SR, DS and DSR (MotoDiag's Cypher II), Zero's 2020 service manual (Version 1, archived dealer copy) requires thermal grease" | known_issues_thermal.json, zero-the-cooling-loop-s-own-faults-and-service-on-each-make-pump | 1 · none · kept |
| Zero recalls: "the platform name Cypher III is this corpus's" becomes "MotoDiag's" | killed | "the platform name Cypher III is MotoDiag's, not the filing's." | known_issues_inverter.json, zero-zero-s-two-2025-controller-recalls-a-motor-controller; contradicted by known_issues_zero.json, zero-cypher-ii-or-cypher-iii-decides-which-procedures-and-which ("Zero's machines split across two operating-system platforms … The dealer bulletin assigns the Cypher III platform") | 1 · factual · deleted |
| Deleting "Fiche-read this phase." leaves the fiche price attributed | kept | "Fiche GBP 576.23. Fiche prices are GBP/EUR inc. VAT and are left in notes, not converted." | parts.json aprilia-1a010574-stator; data file (no external document) | 1 · none · kept |
| Deleting the "Phase 237 flywheel-first differential" clause leaves the maker's statement whole | kept | "Maker states original flywheels used extremely strong magnets, burning stator windings and often the regulator." | parts.json rmstator-rms900-103848-stator; data file (no external document) | 1 · none · kept |
| Deleting the refuter's year_min correction loses no fitment fact | kept | "Hiflo's own catalogue lists RSV4 R 09-11, R Factory 10-12, ... RS 457 24-25. Not USD-priced" | parts.json hiflofiltro-hf138-oil-filter (year_min 2009 agrees with "09-11"); data file (no external document) | 1 · none · kept |
| Deleting "Fiche-read this phase." leaves the fiche price attributed | kept | "Fiche EUR 19.04. Fiche prices are GBP/EUR inc. VAT" | parts.json mv-8000b5425-oil-filter; data file (no external document) | 1 · none · kept |
| Deleting the "Phase 225B:" label does not misattribute the five-year claim | kept | "Fiche assignment. KTM ages the rim seal band out at five years regardless of wear." | parts.json ktm-60310177100-seal; data file (no external document) | 1 · none · kept |
| "was not fiche-read" without "this phase" is still true and still explains the missing cross-reference | kept | "the OEM pump number was not fiche-read, so no cross-reference row is made." | parts.json quantum-hfp-ppn17-krt-fuel-pump; data file (no external document) | 1 · none · kept |
| Deleting the "Phase 237:" label leaves the oily-intake note readable as a diagnostic note rather than as the fiche's | kept | "check those model diagrams directly. An oily FRONT intake on an LC8 is this seal, not fuelling." | parts.json ktm-0760122050-seal; data file (no external document) | 1 · none · kept |
| Deleting the "Phase 237:" label leaves the freewheel-bolt note standing | kept | "page truncated. Freewheel bolts backing out into the stator present as a charging fault." | parts.json ktm-60040020000-clutch; data file (no external document) | 1 · none · kept |
| Deleting "(Phase 237)" leaves the ELAST instruction whole | kept | "ELAST: fitted by length, never re-tensioned." | parts.json bmw-11318528385-alternator-belt; data file (no external document) | 1 · none · kept |
| "Per the owner-reproduced Continental table" stands without the deleted antecedent | kept | "Per the owner-reproduced Continental table, 4PK582 = 4PK592 (582)." | parts.json contitech-4pk592-582-elast-alternator-belt; data file (no external document) | 1 · none · kept |
| Deleting the "Phase 237:" label leaves the sealed/oil-fed note standing | kept | "Sealed and greased pre-2010, oil-fed and vented after." | parts.json bmw-33117722799-final-drive-bearing; data file (no external document) | 1 · none · kept |
| "No BMW number is assigned here" keeps its reason without the refuter clause | kept | "No BMW number is assigned here. No cross-reference row is made." | parts.json ina-f-237895-final-drive-bearing (description: "BMW part number NOT confirmed"); data file (no external document) | 1 · none · kept |
| Deleting the refuter's 73740242A correction loses no fitment fact | kept | "Fiche: Scrambler 800 Classic/Icon/Full Throttle 2015-17, ... 400 Sixty2 2016-19. Not USD-priced" | parts.json ducati-73740281a-timing-belt (year 2015–2018); data file (no external document) | 1 · none · kept |
| Deleting the "Phase 237:" label leaves the tensioner-bearing note standing | kept | "On desmo engines the tensioner bearing is a service item in its own right." | parts.json ducati-70240691a-cam-tensioner; data file (no external document) | 1 · none · kept |
| Deleting the "Phase 237:" label leaves the chrome-flaking note standing | kept | "Chrome flaking on these rockers is the 'glitter in the oil' differential." | parts.json ducati-20810018a-rocker-arm; data file (no external document) | 1 · none · kept |
| Deleting "A refuter added this fitment." leaves the fiche fitment | kept | "Fiche: ST4 S ABS 2003-05. Not USD-priced" | parts.json ducati-20810018a-rocker-arm--st4; data file (no external document) | 1 · none · kept |
| Deleting the "Phase 237:" label leaves the warm-high-idle note standing | kept | "Fiche VIN split 560476/560477. Warm high idle is usually the hoses and throttle-body gasket, not this valve." | parts.json triumph-t1242812-idle-valve; data file (no external document) | 1 · none · kept |
| Deleting "named in Phase 237" leaves "The IACV-to-intake-port rubber hoses" with a referent | kept | "The IACV-to-intake-port rubber hoses are NOT itemised separately on the fiche" | parts.json triumph-t1292075-vacuum-hose; data file (no external document) | 1 · none · kept |
| The mock adapter's known_issues still says what it is | kept | "Simulator / test only — not a real adapter." | adapters.json motodiag-mock (known_issues); data file (no external document) | 1 · none · kept |
| The mock adapter's notes still say what the slug is reserved for | kept | "Reserved slug for the MockAdapter / SimulatedAdapter bridge." | adapters.json motodiag-mock (notes); data file (no external document) | 1 · none · kept |
| Deleting "before Phase 230" leaves the Bonneville claim no broader than it was | kept | "The strongest single diagnostic answer for the injected air-cooled Bonneville family." | adapters.json dealertool-triumph (notes); data file (no external document) | 1 · none · kept |
| "MotoDiag could not verify" names the product correctly | kept | "MotoDiag could not verify that three-cylinder and four-cylinder MV families are covered equally" | adapters.json texa-idc5-bike (known_issues); data file (no external document) | 1 · none · kept |
| R2-1 BMW ELAST: the restored sentence "Sources disagree on which Contitech designation matches which BMW alternator belt." gives the title's 'disagreement' and the later "corrected pairing" something to refer to | kept | "Sources disagree on which Contitech designation matches which BMW alternator belt. **BMW marks the belt with its production length and Continental with its fitted length**" | known_issues_european_parts.json, bmw-the-bmw-elast-belt-designation-disagreement-has-an (seed row; the source is an owner thread, not on disk) | 2 · none · kept |
| R2-2 KTM rim seal: "The R variants take the 21-inch band; the catalogue rows here use exact model names for that reason." | kept | "Tubeless rim seal band, 21-inch front (R)" (model_pattern "1190 Adventure R%"); "exact model_pattern used because '1_90%Adventure%' would also match the R variants, which take a different band"; seed: "a Super Adventure S runs a 19-inch front and the R a 21-inch" | parts.json ktm-60309073100-seal and ktm-60309173100-seal (both "Fiche assignment"); known_issues_ktm_1290.json, ktm-which-1290-you-have-super-duke-r-super-duke-gt | 2 · none · kept |
| R2-3 KTM LC8: "So the absence of the 1190 and 1290 from that page is not evidence about them" | kept | "Fiche VISIBLE assignments: 990 Super Duke/R 2006-13, 950 Super Enduro R 2006-09; the page states some compatible models are not shown, so 1190/1290 fitment is unknown, not excluded" | parts.json ktm-0760122050-seal; known_issues_european_parts.json, ktm-the-ktm-lc8-fiche-pages-for-the-balancer-seal-and-starter | 2 · none · kept |
| R2-4 Zero controller fault: with "MotoDiag's name for" deleted, "(the 2020+ SR/F, SR/S, DSR/X and 2024+ S, DS, DSR)" and "(the 2014-2021 S, SR, DS, DSR)" now read as Zero's own membership of Cypher III and Cypher II | killed | "the firmware release notes page groups bikes as 2020-on Cypher III — listing the 2020-on SR/F and SR/S, the 2022-25 SR and the 2023-on adventure machines — against the earlier Cypher II bikes"; "the SR moves to Cypher III at 2022 while the SR/F and SR/S moved at 2020" | known_issues_zero.json, zero-cypher-ii-or-cypher-iii-decides-which-procedures-and-which (description, fix_procedure step 2), against known_issues_inverter.json, zero-how-a-motor-controller-fault-reaches-the-rider-on-each-make | 2 · factual · fixed |
| R2-5 the five inverter model columns: "(2020+ Cypher III and 2014-2021 Cypher II platforms)" | kept | "groups bikes as 2020-on Cypher III … against the earlier Cypher II bikes"; "the SR moves to Cypher III at 2022" (Cypher III starts 2020, and a Cypher II bike exists through 2021, so both year spans hold) | known_issues_zero.json, zero-cypher-ii-or-cypher-iii-decides-which-procedures-and-which; known_issues_inverter.json, the five rows' model field | 2 · none · kept |
| R2-6 Zero 2025 recalls: the clause naming Cypher III deleted; the sentence ends "…overcurrent, phase or IGBT." | kept | "The report does not say which other Zero models share this controller, and it never uses the words overcurrent, phase or IGBT. NHTSA campaign 25V587" (no other field of the row says "Cypher" or "platform", so nothing is left pointing at the deleted clause) | known_issues_inverter.json, zero-zero-s-two-2025-controller-recalls-a-motor-controller | 2 · none · kept |
| R2-7 regen causes: "Expecting car-style one-pedal driving" | kept | "Tell the rider plainly: none of the three makes documents a one-pedal stop; regen slows the motorcycle and the friction brakes stop it." | known_issues_regen.json, zero-no-electric-motorcycle-maker-offers-a-one-pedal-stop-every (causes, fix_procedure) | 2 · none · kept |
| R2-8 thermal causes: "Assuming a liquid-cooled battery" | kept | "Do not tell an owner whether the battery is cooled by liquid or by air; no document read says either for certain." | known_issues_thermal.json, zero-nothing-on-any-make-is-documented-as-a-liquid-cooled-battery (causes, fix_procedure step 2) | 2 · none · kept |
| R2-9 Ducati tensioner notes: "(fiche GBP 13.69; retailer USD 24.99 is the cost recorded)" | kept | "\"typical_cost_cents\": 2499" beside "fiche GBP 13.69; retailer USD 24.99 is the cost recorded" | parts.json ducati-70240691a-cam-tensioner (data file, no external document) | 2 · none · kept |
| R3-1 Cypher III paragraph's lead: the 2021 SR/F is a Cypher III machine | kept | "the firmware release notes page groups bikes as 2020-on Cypher III — listing the 2020-on SR/F and SR/S, the 2022-25 SR and the 2023-on adventure machines"; "the SR/F and SR/S moved at 2020" | known_issues_zero.json, zero-cypher-ii-or-cypher-iii-decides-which-procedures-and-which (description; fix_procedure step 2). The manual 88-09445-01 is not on disk (see notes) | 3 · none · kept |
| R3-2 Cypher II paragraph's lead: the 2021 S/SR/DS/DSR are Cypher II machines | kept | "the SR moves to Cypher III at 2022"; "against the earlier Cypher II bikes" (no 2021 S, SR, DS or DSR is in the Cypher III list: 2022-25 SR, 2023-on adventure machines) | known_issues_zero.json, zero-cypher-ii-or-cypher-iii-decides-which-procedures-and-which. The manual 88-09447-01 is not on disk | 3 · none · kept |
| R3-4 the sentence after the Cypher II lead: Zero's 2020 service manual (2020 S/SR/DS/DSR, per 247_implementation.md) cited in the Cypher II paragraph | kept | "the SR moves to Cypher III at 2022 while the SR/F and SR/S moved at 2020" (a 2020 S, SR, DS or DSR is not Cypher III) | known_issues_zero.json, zero-cypher-ii-or-cypher-iii-decides-which-procedures-and-which; docs/phases/completed/247_implementation.md, the Documents paragraph | 3 · none · kept |
| R3-5 the leads still read as sentences once the parentheticals are gone, and nothing points at the deleted text | kept | "Zero, Cypher III platform: the 2021 SR/F owner's manual (part 88-09445-01, dealer-hosted mirror copy) lists dash error code 9"; "Zero, Cypher II platform: the 2021 S/SR/DS/DSR owner's manual (part 88-09447-01, mirror copy) lists dash codes 4 and 5" | known_issues_inverter.json, this key, description | 3 · none · kept |
| R3-6 the model column, which is outside the diff: "(2020+ Cypher III and 2014-2021 Cypher II platforms)" still states the platforms by year | kept | "Zero S, SR, SR/F, SR/S, DS, DSR, DSR/X (2020+ Cypher III and 2014-2021 Cypher II platforms)" against "groups bikes as 2020-on Cypher III … against the earlier Cypher II bikes" | known_issues_inverter.json, this key, model; known_issues_zero.json, same key as R3-1 | 3 · none · kept |
| motodiag-mock (harley) note now reads only "Simulator harness — not a real adapter." with the Phase 144 sentence deleted | kept | "Simulator harness — not a real adapter." | src/motodiag/hardware/compat_data/compat_matrix.json, motodiag-mock / harley row (~l.469); data file (no external document) | 1 · none · kept |
| KTM EXC TuneECU note: the 250/350 SX-F "are not in MotoDiag" | killed | "the Super Duke 1290, the 1050/1090/1190/1290 Adventures, the 690 Duke 4, the 690 SMC and Enduro from the later model years, and the 250/350 SXF are all diagnostics-only" | src/motodiag/knowledge/seed/knowledge/known_issues_european_tooling.json, entry "TuneECU's capability degrades differently on KTM and Triumph…" (its `model` field also names "250/350 SXF"); data file (no external document) | 1 · factual · deleted |
| EXC TPI and TBI two-strokes are not on TuneECU's list | kept (still uncertain; PDF not re-fetched, outside round-2 scope) | "It does not cover any Bosch-managed bike (125–390, 790/890/990 Duke), any TPI or TBI two-stroke, or any Euro 5 model." | src/motodiag/knowledge/seed/knowledge/known_issues_ktm_electrical.json, entry `ktm-tuneecu-reaches-keihin-era-ktms-only-tuneboy-is-a-tune`, `description`; adapters.json `tuneecu-ktm-android` `known_issues` ("no EXC TPI/TBI two-strokes") | 2 · none · kept |
| TPI is Continental and TBI is Vitesco | kept | "The 2018–2023 TPI two-strokes run a **Continental** system … and the 2024-on TBI two-strokes pair a Keihin throttle body with a **Vitesco** ECU." | known_issues_ktm_electrical.json, entry 1 (engine-management supplier), `description` | 2 · none · kept |
| EXC-F four-strokes are not on TuneECU's list | kept (still uncertain) | "it covers the Keihin-managed 990 LC8 and 1190 RC8, the 690 family, the 1050 to 1290 Adventures and the 1290 Super Duke — every one of them marked as not Euro 5 — plus the 250/350 SX-F." (EXC-F absent from the enumerated list.) No seed row says EXC-F is listed. The same file's "TuneECU reaches Keihin-era bikes only" (entry 1 `fix_procedure` step 2) together with "Keihin manages … the EXC-F and SX-F four-strokes" states a necessary condition, not a sufficient one, so it does not contradict. | known_issues_ktm_electrical.json, entry `ktm-tuneecu-reaches-…`, `description`; entry 1, `description` and `fix_procedure` | 2 · none · kept |
| The 250/350 SX-F are on TuneECU's list | kept | "plus the 250/350 SX-F" / "the 250/350 SXF are all diagnostics-only" / "250/350 SX-F — diagnostics and tests only" | known_issues_ktm_electrical.json, entry `ktm-tuneecu-reaches-…`, `description`; known_issues_european_tooling.json, entry `ktm-tuneecu-s-capability-degrades-…`, `description`; adapters.json `tuneecu-ktm-android` `notes` | 2 · none · kept |
| "only the 250/350 SX-F … are" (scope of "only") | kept, with a wording observation | "only the 250/350 SX-F motocross models are." On its own, "only … are [on TuneECU's list]" could be read as "the only KTMs on the list". The sibling rows (990%, 1190 RC8%, 690%, 1190 Adventure%, 1050%, all with this adapter and status full/partial) contradict that reading. The sentence's context (EXC two-strokes and four-strokes set against "motocross models") limits it to KTM's off-road singles, and that is the natural reading. The word "only" was there in the same position before the fix, so the deletion added no claim. | compat_matrix.json l.1153–1211 (sibling tuneecu-ktm-android rows); the pre-fix text in `git diff` | 2 · wording · kept |
| The fix adds nothing and leaves nothing dangling | kept | before: "…only the 250/350 SX-F motocross models are, and those are not in this corpus."; after: "…only the 250/350 SX-F motocross models are." The diff is a pure deletion of the trailing clause. The sentence still parses and still ends on its own predicate. | `git diff -- src/motodiag/hardware/compat_data/compat_matrix.json`, hunk @@ -1281 | 2 · none · kept |
