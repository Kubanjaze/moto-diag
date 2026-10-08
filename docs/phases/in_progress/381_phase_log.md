# Phase 381 — The content batch on the row key — phase log

**Status:** 🚧 Step 0, stopped for the operator (2026-10-08)
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
