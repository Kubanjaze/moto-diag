# Phase 359 — Content clean-up: starter templates and build references — phase log

**Status:** 🚧 In progress
**Branch:** `phase-359` (Opus session, main checkout, the only writer)

---

### 2026-09-27 — Opened

The prompt is `docs/prompts/359_content_cleanup.txt` (committed in
`30ac15f`, merged `bb3ef02`).

**The operator's order and condition, verbatim (2026-09-27):**

> order after: content phase (F159/F163/F166 templates + F158's 27 rows) → 356 → 357 → Track O.
> content phase: decide "retire vs repair" for the two old starter templates at its step 0, with a count of every template and row that references them. not before.

**Row 359 🚧:** `dc69e50`. 359 is the next free number: the highest row
was 358, the mobile ROADMAP has no 359, and `ROADMAP_AUTHORITY.md` gives
205+ to this repo.

### 2026-09-27 — Bug fix #1: A5 judged the first regression line, not the last

- **Issue:** 358's close-out check A5 read a log's first regression line
  that parsed. When a regression is re-run, that is the superseded run.
  358 recorded two: 9636 at `8a205ee`, then 9639 at `d93d8de` after its
  bug fix #2. A log whose first line parsed and whose re-run line did not
  would have passed. Reported in 358's handoff
  (`docs/handoffs/2026-09-27_358_closed.md`, "What is open").
- **Root cause:** `regression_line` ran `_REGRESSION.search` over the
  whole log, which returns the first match.
- **Fix:** it takes the last line carrying "Regression of record:" and
  parses that one. This fixes 358's check; the rule (count + hash +
  command) is unchanged.
- **Files:** `.claude/skills/closeout/closeout_check.py`; fixtures
  `k6_k7/a5_bad_last_line_superseded.md` and `k6_k7/a5_good_last_line.md`;
  `tests/test_phase359_a5_last_line.py` (4 tests); the skill's
  `CHANGELOG.md`.
- **Verified:** with the old `regression_line` restored, 3 of the 4 new
  tests failed, including the `check()` wiring test; with the fix, 67
  passed across the new file, `test_phase358_closeout_k6_k7.py` and
  `test_phase255D_closeout_contract.py`. 358's exemption controls still
  recompute to 10 and 40. Fast whole-tree: 1472 passed.

**Commit.** `5bc40c8`.

### 2026-09-27 — Step 0, stopped for the operator's pick

Recorded in `359_step0.md`. It ends at the fork the prompt names, retire
or repair, plus one scope question: live row 4615 lags its seed just as
row 31 does.

Decided without a stop, with the reason:
- **F158's fixed set** is every "Phase N", "Track X" and "this phase" hit
  in seed- or migration-written tables: 44 hits in 25 seed rows. The 31
  F-number hits are all BMW F-series model names and stay. Reason: the
  prompt's own exclusion ("a model name … stays").
- **The `known_issue_models` difference is not a finding.** Live equals
  a rebuild of its own content. The gap is in 358's ratchet fixture, which
  omits `db init`'s last step. It is fixed at the build as a bug fix to
  358's check.

### 2026-09-27 — The operator's pick, verbatim

> B, with the show change. Add the VIN step to ppi_chassis_v1 item 1 from a primary document named from its title page; if it doesn't survive the refute, that change doesn't ship and the loss is recorded. Yes to 4615 in 072, on one condition: the dry-run diff shows 4615 changing only to its seed text, field for field, and nothing else.

How it is applied, literally:
- The starters are retired (`is_active = 0`), and `workflow show` on a
  retired slug prints that it is retired, with no items.
- The VIN step is its own change, and it ships only if it survives the
  refute. If it does not, 072 ships without it, and the loss is recorded
  as a finding.
- Row 4615: the dry run compares the copy's row, field by field, with
  the row a seed build produces. Any other change to 4615 stops the
  deploy.

**v1.0:** `8c88d00`.

### 2026-09-27 — Bug fix #2: the F158 ratchet did not build its database as `db init` does

- **Issue:** 358's ratchet fixture (`tests/test_phase358_f158_ratchet.py`,
  `built`) says it builds "the way `motodiag db init` builds one", but it
  skipped `db init`'s last step, `rebuild_model_index_at`. Its
  `known_issue_models` junction differed from live's by 116 and 327 rows
  (Step 0, S0-6). Live equals a rebuild of its own content, 2833 = 2833.
- **Root cause:** the fixture copied `db init`'s loaders but not its final
  model rebuild; `rebuild_make_index_at` was there, the model rebuild was
  not.
- **Fix:** the fixture calls `rebuild_model_index_at` last. The census count
  was 75 either way, so the ceiling did not move for this.
- **Files:** `tests/test_phase358_f158_ratchet.py`.
- **Verified:** the new test `test_the_build_is_db_inits_build` (a second
  rebuild of the built database changes nothing) failed before the fix and
  passed after; 11 passed.

**Commit.** `2973d1a`.

### 2026-09-27 — The VIN source (rule 2)

- **The library, parsed** into the session scratchpad (`s0/parse.py`,
  pypdf): 262 files, 244 opened, **26,220 pages**, 14 image-only; the 18
  unopened files are the same class 262 saw (truncated streams, one empty
  file). 262's census read 260 files and 26,228 pages.
- **Census** (whitespace stripped, lower-cased, `s0/libcensus.py`): "vehicle
  identification number" or "VIN" on 330 pages in 121 files; a frame,
  chassis or serial number on 100 pages in 65; the number within 200
  characters of registration, title, ownership, licence or documents on 71
  pages in 57 files.
- **Sandbox proven first** (`s0/extract359.py prove`, the source-transmission
  orchestrator's profile): planted writes into the repository, the library
  and the session scratchpad each failed with `Operation not permitted`;
  the control write inside the run's clone succeeded. Run directory
  `~/.cache/motodiag/source-runs/359_step0/content_cleanup_vin_20260927_145927/`.
- **Extraction, one no-tools turn each, JSON schema:**

| run | route | pages | facts | quotes on their page | turns | tokens | time |
|---|---|---|---|---|---|---|---|
| every VIN/frame-number page | `subconscious/glm-5.3-marathon@default` | 304 | 20 | 19 | 5 | 670,696 | 278 s |
| the number near registration, title, ownership, documents, insurance, dealer, record | `subconscious/glm-5.3-marathon@default` | 149 | 0 (`is_error`) | — | 8 | 913,461 | 517 s |
| the number near registration, title, ownership, theft, stolen | `subconscious/glm-5.3-marathon@default` | 117 | 14 | 14 | 3 | 212,177 | 147 s |

  - The first run returned only BMW location and index lines, although the
    census had put the registration pages mostly in Yamaha, Honda and
    Piaggio files. So it was not taken as the answer.
  - The second errored (193k output tokens, no structured result). The
    third, narrower, was the one retry.
- **Chosen,** each quote read on its page by Opus, and each document named
  from its rendered page 1 (`qlmanage`):
  - `gts300_abs_om.pdf`: page 1 reads "Vespa GTS 300 i.e. ABS", "Ed.
    04_04/2018". PDF p. 34 (printed 34): "We recommend checking that the
    chassis registration number stamped on the vehicle corresponds with
    that on the vehicle documentation."
  - `acquired/Honda/om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf`: its
    cover has no text layer; rendered, it reads "2018 OWNER'S MANUAL
    CB500F/FA", HONDA. PDF p. 119: "The VIN and engine serial number
    uniquely identify your motorcycle and are required in order to register
    your motorcycle."

### 2026-09-27 — The build

- **Seed edits:** 33 Edit-tool edits in 12 `known_issues_*.json` files,
  then round 1's four fixes (below). A seed build's census is **31**, every
  hit a BMW F-series model name.
- **`migration_072_live_rows.py`** is generated (`gen072.py`, in the
  session scratchpad; its logic is in the module's docstring). It compares a
  live copy with the edited seed's build: **26 rows, 35 fields**, exactly
  S0-5's 24 plus rows 31 and 4615. No row exists on one side only.
- **Migration 072:** the workflow half is written in `migrations.py`, and the
  known-issue half is turned into SQL from that data. Every statement is
  keyed on the exact old text.
- **On a copy of the live copy, 072 makes every seed-borne table equal a
  fresh seed build:** `known_issues`, both junctions, both workflow tables,
  `dtc_codes` and `symptoms`. It changes 26 known-issue rows, 4 templates
  and 2 items, and adds a `schema_version` row. Live's census goes 79 → 36:
  31 BMW names plus 5 hits in shop data.
- **`workflow show` on a retired slug** prints `<slug>: <description>` and
  exits 1. The description is the retirement line naming the replacements.
- **The F158 exclusion rule is code** (`f158_census.build_references`), with
  controls:
  - a planted "See F158" in a BMW row is kept;
  - "F800" in a BMW row is excluded, while "F800" in a non-BMW row is kept;
  - a planted "Phase 199" shop name is counted by the census but left out as
    content;
  - on the seed, build references are 0.

  One control first proved nothing. It planted "F800GS", which the census
  pattern never matches (no word boundary before the G). It now plants a
  token the census does catch.
- **`F158_CEILING`:** 75 → **31**.
- **The deploy skill's `to`:** a scope entry may name the value a field must
  hold after the migration. This holds the operator's 4615 condition,
  "changing only to its seed text". `tests/test_phase359_deploy_to.py` has
  the known-bad case (the allowed field changes, but to other text).
- **Tests changed:**
  - Gate 15: the walk, ∅ W4 exceptions, 4 links fewer, and the slug floor
    22 → 15, measured. It also gained a retired-slug check and its control;
  - 259, 260 ×3, 261 and 264: each was pinning the starters' pre-359 state.
- **Mutations, 8 of 8 red** (`mutate.py`: one exact replacement, the file
  restored and sha256-checked, `-B` with `__pycache__` cleared):
  1. `show` prints a retired template;
  2. the exclusion ignores the make;
  3. operational rows are counted as content;
  4. deploy ignores `to`;
  5. the known-issue SQL is not keyed on old text;
  6. the starters are not retired;
  7. the VIN step is not applied;
  8. A5 reads the first line.
- The 244G scanner over `tests/`: 0 findings.

### 2026-09-27 — The refute, three rounds

Four fresh-context Opus refuters; their verdicts are kept in
`359_refute_verdicts.md`, and each round's input is generated from the data
(`359_refute_input.md`: 51 blocks; `_r2`: 8; `_r3`: 1).

- **Round 1, workflow text (9 blocks, 20 rows): 0 killed.** Both VIN quotes
  are verbatim on their pages, and both title pages were checked. The
  steering deletions are right: neither the KTM nor the YW125Y page names a
  cause for a notch. Outside the blocks the refuter found five things, and
  four were acted on:
  - "full" in ppi_engine_v1 contrasted with the retired quick check:
    **deleted**;
  - the retirement line sent an electric machine to the ICE-only
    ppi_engine_v1: **fixed**;
  - after the deletions, the notch had no diagnosis: KTM p. 76's own
    detent step was added;
  - the fail line did not name an altered number: Vespa p. 34's caution
    supports adding it;
  - the retired slug was a docstring example in `workflows/models.py`:
    changed.
- **Round 1, known-issue text (42 blocks): 5 killed.**
  - C28: the flywheel was left dangling; the companion entry is now named
    by its title.
  - C32: an owner-report claim read as if the fiche said it; it is now
    attributed to owner reports.
  - C40: "This" was ambiguous; it now reads "This entry".
  - C42: "the European intervals file" was **deleted**.
  - C48: row 4615's "corpus-wide" was **left open, F171**. It is 255B's
    seed text, and the operator's condition is that 4615 change only to
    its seed text.
- **Round 2 (the diff and its neighbours, 12 rows): 1 killed.** The KTM
  sentence is from p. 76's Info box, not its Warning box, so "warns" became
  "notes". Two flags:
  - "or worn bearings" is not on p. 76 for play: **deleted**;
  - row 902's model scope: **F170**, older content that needs a document.
- **Round 3 (1 block, 6 rows): 1 killed, as wording.** "Rocking play is
  loose adjustment" states a cause the page does not; it gives only the
  remedy. Round 3 is the last, so this goes to **F171**, the one finding,
  with C48.

## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| The Vespa GTS 300 i.e. ABS manual recommends checking the stamped chassis number against the vehicle documentation | kept | "We recommend checking that the chassis registration number stamped on the vehicle corresponds with that on the vehicle documentation." | Vespa GTS 300 i.e. ABS manual (Ed. 04_04/2018), `gts300_abs_om.pdf` p. 34 | 1 · none · kept |
| The Honda 2018 CB500F/FA owner's manual says the VIN is required to register the motorcycle | kept | "The VIN and engine serial number uniquely identify your motorcycle and are required in order to register your motorcycle." | Honda 2018 CB500F/FA owner's manual, `om_AHM_CB500F-FA_2018_CB500F.FA_31MJWB20_0.pdf` p. 119 | 1 · none · kept |
| The number to compare is stamped on the frame ("stamped identification number") | kept | "a number stamped on both the chassis « A» and the engine « B»" | Vespa GTS 300 i.e. ABS manual p. 34 | 1 · none · kept |
| An altered frame number is a fail | kept | "ALTERING IDENTIFICATION REGISTRATION NUMBERS CAN LEAD TO SERIOUS PENAL SANCTIONS (IMPOUNDING OF THE VEHICLE, ETC.)" | Vespa GTS 300 i.e. ABS manual p. 34 | 2 · none · kept |
| A notch at straight-ahead is dented bearing races; adjustment only hides it; brinelled races | killed | "If detent positions are detected: – Adjust the steering head bearing play. – Check the steering head bearing and change if necessary." | KTM 2022 250/300 EXC TPI owner's manual, `22_3214421_en_OM.pdf` p. 76 | 1 · factual · deleted |
| The YW125Y's adjustment: lower ring nut, 38 N·m then 14 N·m | kept | "Lower ring nut (initial tightening torque) 38Nm" … "Lower ring nut (final tightening torque) 14Nm" | Yamaha YW125Y service manual (title page "Model : YW125Y"), `yamaha_zuma125_2009_sm.pdf` p. 94 | 1 · none · kept |
| For a detent, adjust the play, then check the bearing and change it if necessary | kept | "If detent positions are detected: – Adjust the steering head bearing play. – Check the steering head bearing and change if necessary." | KTM 2022 250/300 EXC TPI owner's manual p. 76 | 3 · none · kept |
| Running with play can damage the bearings and their seats in the frame over time ("notes") | kept | "If the vehicle is operated for a lengthy period with play in the steering head bearing, the bearings and the bearing seats in the frame can become damaged over time." | KTM 2022 250/300 EXC TPI owner's manual p. 76 (Info box) | 3 · none · kept |
| The same sentence as a "warning" that play "damages" the seats | killed | "the bearings and the bearing seats in the frame can become damaged over time" | KTM 2022 250/300 EXC TPI owner's manual p. 76 (Info, not Warning) | 2 · wording · fixed |
| Rocking play is loose adjustment or worn bearings | killed | "If there is detectable play: – Adjust the steering head bearing play." | KTM 2022 250/300 EXC TPI owner's manual p. 76 | 2 · wording · deleted |
| Rocking play "is loose adjustment" | killed | "If there is detectable play: – Adjust the steering head bearing play." | KTM 2022 250/300 EXC TPI owner's manual p. 76 | 3 · wording · open F171 |

## Refute of the known-issue edits: text against text

These 42 verdicts judge old text against new, and no document, so they have
no page to cite. They sit outside the checklist, which requires one. The full table is in
`359_refute_verdicts.md`.

| block | row | verdict | round · kind · outcome |
|---|---|---|---|
| C10 | 31 thermostat (one sentence rewritten, the rest is 243's seed) | kept | 1 · none · kept |
| C11–C27, C29–C31, C33–C39, C41, C43–C47, C49–C51 | the other 20 F158 rows and 4615's other blocks | kept | 1 · none · kept |
| C28 | 899 Aprilia V4 charging: "the reduced-magnet flywheel" dangling | killed | 1 · wording · fixed (named by title), 2 · none · kept |
| C32 | 902 Triumph idle hoses: owner-report claim unattributed | killed | 1 · citation · fixed (attributed), 2 · none · kept |
| C40 | 1288 KTM Duke: "This covers" ambiguous | killed | 1 · wording · fixed, 2 · none · kept |
| C42 | 1332 MV triple: "the European intervals file" | killed | 1 · wording · deleted, 2 · none · kept |
| C48 | 4615 CVT regulator: "a corpus-wide sweep" | killed | 1 · wording · open F171 |
