# Follow-ups — backend

Findings about **backend** code: the corpus, retrieval, the CLI, the API,
migrations, the knowledge pipeline. Each entry records what was measured, why it
was not fixed where it was found, and what would close it.

## Where a finding lives

**A finding lives in the repo whose code it is about.** Backend findings here;
mobile findings in [`moto-diag-mobile/docs/FOLLOWUPS.md`](https://github.com/Kubanjaze/moto-diag-mobile/blob/main/docs/FOLLOWUPS.md).
A finding that spans both is filed once, in the repo where the fix lands, and
referenced from the other. This is stated in `ROADMAP_AUTHORITY.md`, which is
the binding contract — not in any one agent's memory.

## Numbering

**F-numbers are ONE global sequence across both files.** The next number is
`max(F across BOTH files) + 1`, never the max of one. Check both before
assigning. A number is never reused and never renumbered when a finding moves
repos.

At the time of writing the highest assigned is **F128** (this file); the mobile
file's highest is **F114**.

---

### F115

**A row is unreachable to the owners it was written for**

Phase 254's row 4605 explains that three unrelated components are all called a
drive belt, and that a Harley-Davidson final-drive belt is not a CVT belt. Its
`make` column reads `Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine`.

Measured: `Harley-Davidson Road King` reaches row 4605 → **False**.
`BMW R1200GS` → **False**. `Yamaha Bolt` → True. `Honda PCX 150` → True.

**The row that exists to stop a Harley owner confusing two belts cannot be
retrieved by a Harley owner.** The general half is the useful half and it is
scoped to the marques that need it least. Not fixed in 255 — the row ships
unscoped on the transmission axis, which is correct, but its `make` column is a
separate defect. Splitting the general half out belongs to 255B.

### F116

**`manual` is the fifth substring collision, and the worst ratio yet**

`SELECT * FROM known_issues WHERE description LIKE '%manual%'` returns **311
rows, of which 300 are the document** — service manual, owner's manual, workshop
manual. Exactly **2** use the word in the transmission sense.

The previous four: `grommet` (Phase 250C), `symptom`/`system`/`genuine part`
(253), `controller`/`kickstand` (250B), and now `manual`. Retrieval matching on
substrings is the common cause. Phase 255 routes around it — 255B selects rows
by the transmission axis rather than by searching for the word — but the
collision itself is untouched.

### F117

**The XS650 cooling over-reach predates Phase 254**

A Yamaha XS650 — an air-cooled parallel twin — retrieves **11 liquid-cooling
rows**. This is not 254's doing; it predates it. Measured across the corpus: 67
liquid-cooling rows, 11 of them naming more than one marque.

Cooling is the third axis. It needs the same treatment the transmission axis
just received, and the mechanism is now built.

### F118

**Final drive is a fourth axis, and must not be solved with `{manual}`**

Measured on the live database:

| machine | total rows | clutch | gearbox | **final-drive chain** |
|---|---|---|---|---|
| Honda PCX 150 | 165 | 3 | 1 | **8** |
| Yamaha Zuma 125 | 127 | 1 | 2 | **4** |
| Kymco Agility 50 | 16 | 0 | 1 | 0 |
| Genuine Buddy 125 | 15 | 0 | 1 | 0 |

A PCX has no chain. Neither does a belt-drive Harley-Davidson or a shaft-drive
Gold Wing, and **those two would not be helped by a `{manual}` declaration** —
they are manual-transmission machines that still must not receive chain content.
Final drive is its own axis: chain / belt / shaft.

Recorded on the general-applicability ticket as the fourth axis.

### F119

**~~Honda's US scooter owner's manuals name no transmission at all~~ — WRONG, and wrong in this project's signature way.**

**Filed 2026-09-21 (Phase 255). Retracted the same day.**

The original claim: the 2025 Ruckus owner's manual has zero occurrences of
"belt" in 107 pages and the 2025 Metropolitan none of "drive belt" or "weight
roller", so neither CVT machine could be classified from its own document.

**Both manuals state the transmission, in the Specifications table:**

> **"Primary reduction   V-matic (2.85:1 ~ 0.86:1)"**

— Ruckus 31GGA6300 (2012), 31GGA720 (2022), 31GJP600 (2024), 31GJP610 (2025);
Metropolitan 31GJB640 (2020) through 31GJB690 (2026). **V-matic is Honda's
trade name for its CVT**, and the *ratio range* is what settles it beyond the
name: a fixed primary reduction prints a single number, as the same tables do
two lines below — "Final reduction 13.708".

The same word appears in the PCX manuals ("V-Matic (2.52:1-0.81:1)") and the
SH125i/SH150i. Corroborated for the Metropolitan by the **CHF50 service
manual**, held on disk since Phase 254, whose specification table carries the
whole variator set — *Drive belt width*, *Movable drive face*, *Driven pulley*,
*Weight roller*, *Clutch outer I.D.*, *Lining thickness* — under a chapter
titled *KICKSTARTER/DRIVE PULLEY/DRIVEN PULLEY/CLUTCH*.

**Why it was wrong, which is the part worth keeping.** The search was for
`belt`, `drive belt`, `weight roller`, `CVT` and `transmission`. It was not for
**the maker's own word**. That is precisely what Phase 254's row 4604 exists to
warn about — *"what a scooter CVT is, in the makers' own words — and why
searching for the word 'variator' finds…"* — and the error was made one phase
later, by the author of the phase built on that row, while writing the
follow-up that asserted the absence.

A zero result is a fact about the query before it is a fact about the corpus.
The row says so; the search did not obey it.

**Fixed:** Ruckus and Metropolitan now carry sourced lookup entries. Re-running
the corrected vocabulary across every document on disk also settled **Piaggio
Fly 50** (workshop manual 633212, "MSS Fly 50 4T"), **Piaggio Beverly Tourer
125** (service station manual 665018) and **Vespa S 50 2T** (664787-664795) —
three more that the first sweep had left unsourced.

**The remaining eight were then classified rather than listed**, because
"unsourced" was hiding two different problems. Asked of each: no document, or
an alias gap?

**Five were alias gaps — the document was already on disk:**

| spelling | document | quote |
|---|---|---|
| SYM JET 50 / JET 100 | SYM service manual **7326249** | *"for the SANYANG JET 50/100 and JET Euro 50/100 series"*, spec table *"Primary Reduction **BELT**"* |
| SYM Joyride | SYM service manual **7429958** | *"for the Sanyang JOYRIDE 125/150/200"*, chapter 8 *"V-BELT DRIVING SYSTEM/FOOT STARTER"* |
| Vespa Sprint | Primavera owner's manual | cover: *"Vespa Primavera S - **Sprint S** 125-150 Ed. 01_05/2018 Cod. 1Q000662"* |
| Zuma 50 | Yamaha OMs **5PJ-F8199-13**, **1CD-F8199-10/-17**, **2DT-F8199-10** | *"V-belt"* scheduled beside *"Final transmission oil"*; covers give YW50T/FB/FK/FXE |

The Vespa Sprint is the sharpest of these: Phase 255 **removed** its aliases as
unsourced without reading the manual's own cover, which names it.

**Two are genuinely no-document:** **Piaggio Beverly 250** — zero mentions
across 227 readable PDFs — and **Vespa 946**, whose sixteen apparent hits are
all the phone number *"(888) 946-6329"* in Honda manuals. A textbook instance
of the substring collision this corpus keeps meeting.

**One is contested attribution, not a gap: Filly LX 50.** The Kymco Agility 50
service manual carries the CVT data (*"Type Non-stage transmission · Operation
Automatic centrifugal type"*) and prints `FILLY LX 50` as a header on 21 of its
183 pages — but Phase 254 established those pages alternate by odd/even folio,
the signature of a recycled template, with provenance genuinely unestablished
in two chapters. **No alias added:** the data is in the book, and whether it is
the Filly's data is exactly what 254 could not settle.

**Result: 50 of the 53 model spellings now resolve, up from 40.** Honda's web
spec pages remain **403** to this environment on every path tried
(`powersports.honda.com`, `automobiles.honda.com`), as throughout Phase 254 —
but no remaining gap depended on them.

**CLOSED-UNOBTAINABLE, operator's decision 2026-09-21: Piaggio Beverly 250 and
Vespa 946.** Both resolve to NULL and **NULL stays** — fail-closed is the
correct answer for a machine no document describes, and inventing one would be
the fabrication this axis exists to prevent. Re-open only if a document
arrives.

**And a vocabulary trap, recorded because it is the reason the search could
not have succeeded.** The download landing page for the Beverly workshop
manual spells the model **"bevely"**:

> *"**bevely** 125 e3 workshop manual.pdf download (16.7 MB)"*

A search for `beverly` cannot find `bevely`. This joins the corpus's standing
collection — *grommet* for Grom, *symptom*/*system* for SYM, *genuine part*
for Genuine, *controller* for roller, *kickstand* for kickstart, `manual` the
document versus `manual` the transmission, `946` the phone number, and
`V-matic` the word Honda actually uses. **Six of those nine are cases where
the search term was wrong, not the corpus.** `Filly LX 50` stays open
separately: its document exists and its attribution is what Phase 254 could
not settle.

### F120

**Piaggio uses "direct drive" to mean a CVT**

The Vespa Primavera/S 150 owner's manual states:

> "The vehicle is fitted with direct drive automatic transmission."

This is a twist-and-go CVT scooter. Piaggio's "direct drive" means there is no
intermediate gearbox — it does **not** mean the `direct_drive` value of the
Phase 255 transmission enum, which is defined as no gearbox *and no clutch*. The
same manual contains **zero** occurrences of "variator", which independently
corroborates Phase 254's vocabulary row.

A documentation hazard rather than a runtime one, because nothing in the code
reads document text to classify anything. Recorded in the ADR and in the lookup
entry itself so the next author does not resolve it the wrong way.

### F121

**Mobile has no transmission field, and the residual gap is user machines**

`NewVehicleScreen.tsx:121` posts `make, model, year, engine_cc, vin, protocol,
powertrain, engine_type, battery_chemistry, motor_kw, bms_present, mileage,
notes`. No transmission. Every mobile-created vehicle lands with the column NULL
and depends entirely on the backend resolver.

Mobile already sends `powertrain` as a first-class field, so the precedent for
adding one is in the same request body.

**Named as the phase immediately after 255B**, not "later": the live `vehicles`
table holds 10 machines and none of them is a CVT machine, so the exposure is
entirely future — whatever a user adds next.

### F122

**One corrupt applicability value stops diagnosis**

Phase 255's contract says an invalid `known_issues.applicability` is **rejected
loudly** at seed load and again at read. Implementing that and then exercising
it showed what "loudly" costs at read time.

`_declared_for` raises `ApplicabilityError`, which propagates through
`compose_prompt_rows` and out of `_load_known_issues` — the retrieval path for
`motodiag diagnose` (two call sites) and `motodiag code` (one). **A single row
with `{"transmision": ["cvt"]}` stops diagnosis for every machine, not just the
one the row would have reached.**

The trade was kept deliberately. Dropping the row silently would load a typo as
*unscoped*, which puts it back in front of every Gold Wing — the exact defect
Phase 255 exists to fix, reintroduced by one character. Treating it as "applies
to nothing" would be fail-closed and safe but silent, and a corpus in a state
nobody validated is not a corpus to answer from.

Two things were changed rather than left: the error now names the offending row
by id and title, and the behaviour is pinned by a test and two mutations.

**For the operator to decide, not for a later phase to assume:** whether a read
of a corrupt corpus should stop the product or degrade to withholding the row
with a logged error. Only reachable by writing to the column outside
`add_known_issue`, which validates — a JSON column has no CHECK constraint, so
that path exists.

### F123

**`predict_failures` is a third retrieval door and still carries the Phase 254 over-reach.**

Phase 255 fixed applicability on the two paths that hand corpus rows to a model
as context about one machine: `_load_known_issues` (`motodiag diagnose`,
`motodiag code`) and the video `/ask` endpoint. **`predict_failures` is a third
and was left.**

It does not use `known_issues_for_vehicle` at all. It runs its own four-pass
`search_known_issues` retrieval — the `LIKE`-based path — dedupes by issue id,
and scores fifty predictions with drift bonuses. Measured against the live
corpus:

| machine | Phase 254 rows behind its predictions |
|---|---|
| Yamaha MT07 | **5** — 4614, 4606, 4607, 4608, 4610 |
| Yamaha XS650 | **5** — same |
| Honda GL1800 Gold Wing | **2** — 4606, 4607 |

So a Gold Wing owner still receives maintenance predictions derived from
scooter variator-roller and clutch-lining rows.

**Why it was not fixed in Phase 255.** The filter itself is a one-line call and
the machinery exists. The pipeline is not: fifty scored predictions, a separate
retrieval with four passes and its own year-window handling, drift bonuses,
recall and TSB joins. Filtering its candidate pool changes what it predicts and
by how much, and that needs a plan, a measurement of the before/after
prediction set, and a refuter. **Changing a scored pipeline late in a phase,
without those, is exactly how the Phase 254 defect shipped** — so it is filed
rather than patched.

**The general lesson is bigger than this ticket.** Phase 254 never asked which
machines would receive its rows. Phase 255 asked it, and the answer was that
there are three doors and nobody had a list of them. **There is still no test
asserting that every retrieval path applies the applicability filter** — a new
fourth door would leak silently. That guard belongs with the general
applicability mechanism.

**CLOSED 2026-09-21 by Phase 256.** `predict_failures` routes through
`knowledge/retrieval.py::rows_for_machine(purpose="prediction")`, applied to
the **candidate pool before scoring**, so a row the machine cannot have
never earns a rank.

**No scoring change shipped**, and that is a diff rather than a claim: 421
predictions across 9 machines, **21 rows removed, all transmission-scoped,
zero non-scoped**, every scoring field identical for every survivor, and
relative order preserved on every machine. The MT07 drops 50 → 45 because
its pool ran out; the rest backfill from below the 50-cap.

This ticket also asked for "a test asserting that every retrieval path
applies the filter, so a fourth door cannot leak silently". That exists now:
`tests/test_phase256_chokepoint.py` fails the build if any module outside
the repo layer names `known_issues` in SQL, and plants a bypass against
itself on every run.

### F124

**Eleven schema pins shadow `SCHEMA_VERSION`, and the lint was suppressed eleven times.**

`SCHEMA_VERSION` is the single source of truth for the schema head. Eleven test
assertions duplicate its current value as a literal:

| file | line | form |
|---|---|---|
| `test_phase184_gate9.py` | 591 | `SCHEMA_VERSION == 63` |
| `test_phase205_gate11.py` | 643 | `SCHEMA_VERSION == 63` |
| `test_phase240_gate12.py` | 578 | `SCHEMA_VERSION == 63` |
| `test_phase244D_known_issues_dedup.py` | 187 | `SCHEMA_VERSION == 63` |
| `test_phase244F_marque_vocabulary.py` | 282 | `SCHEMA_VERSION == 63` |
| `test_phase244I_model_vocabulary.py` | 243 | `SCHEMA_VERSION == 63` |
| `test_phase244L_vision_costs.py` | 202 | `SCHEMA_VERSION == 63` |
| `test_phase244M_client_memory.py` | 801 | `SCHEMA_VERSION == 63` |
| `test_phase244N_passive_capture.py` | 572 | `SCHEMA_VERSION == 63` |
| `test_phase250_gate13.py` | 616 | `SCHEMA_VERSION == 63` |
| `test_phase191b_serve_migrations.py` | 100 | `get_current_version(db_path) == 63` |

**Every one carries an `f9-noqa: ssot-pin` suppression.** The SSOT lint
(`scripts/check_f9_patterns.py --check-ssot-constants`) flagged all eleven
correctly, and all eleven were waived — F9 subtype 4, suppressed at scale.

**They catch nothing.** The failure mode they claim to guard — the constant
bumped without a migration — is already caught by a single genuine pin,
`tests/test_phase240c_severity_ordering.py:257`:

```python
assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)
```

Verified: on a clean tree it passes; with `SCHEMA_VERSION` set to 64 and no
migration added it fails on its own, in 0.07s. It compares two independent
sources, which is what makes it a real pin rather than a copy.

**What they cost.** Every migration requires editing all eleven, and each
carries a hand-maintained "schema history" comment restating the migration
log — now 1–2 KB apiece. Phase 255 appended to eleven of them and needed
**five passes** to find them all: a subsystem blast radius found three, a
neighbour a fourth, a grep four more, a ninth only because `gate12` runs
`gate11` in a subprocess, and the last three only when the grep's hits were
counted rather than read off a `head`-truncated screen.

**Converting them to `== SCHEMA_VERSION` is not the fix** — that is `x == x`,
as their own comments say. They are deleted.

**Schema history has one canonical home:** each `Migration.description` in
`src/motodiag/core/migrations.py`, which already carries the full rationale for
every version, plus the per-phase `docs/phases/completed/NNN_implementation.md`
for narrative. The comment blobs were copies of it.

**CLOSED 2026-09-21.** All eleven deleted — ten whole test methods that held
nothing else, and one bare assertion in `191b` that sat beside an
`== SCHEMA_VERSION` line doing the same job. Nine unused `SCHEMA_VERSION`
imports removed with them. Guard added at
`tests/test_f124_schema_pin_discipline.py`: it fails on any equality against a
literal equal to the current head, on any NEW file taking an
`f9-noqa: ssot-pin` waiver on a schema-version line, and on any surviving
waiver that is not a `>=` floor — and it plants a head pin against its own
scanner to prove the scanner sees one.

**Proved, not asserted.** On a scratch branch, `SCHEMA_VERSION` was bumped to
64 with a no-op migration 064 — two source files touched, **zero test files
edited** — and the 735 tests that previously demanded eleven edits ran
**735 passed, 0 failed**. Branch discarded.

**Read of the instruction, stated because it is a judgement call:** "fail on
any literal equal to current SCHEMA_VERSION" is implemented as *equality*
comparisons only. Banning `>= 63` as well would forbid a phase from pinning
its own migration — the floor-pin pattern six phases use (194, 195, 195B,
235B, 244R, 255) — and a floor pin is written once and never edited again, so
it carries none of the cost this ticket is about. Say the word if the stricter
reading was meant.

Intermediate-state literals below the head (`== 38`, `== 51`) stay legal: they
assert a fixture mid-migration, not the head.

**The guard itself then failed Phase 244G, and that is worth recording here
rather than only in a commit message.** Its first version asserted a literal
string against the **raw** source of `test_phase240c_severity_ordering.py`:

```python
src = path.read_text(...)
assert "assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)" in src
```

244G forbids exactly this, for a reason that applies squarely: the assertion
would keep passing after the pin it protects was deleted, so long as the same
text survived anywhere in a comment — **including in this guard's own
docstring, which quotes it.** A guard that cannot fail is the thing F124 is
about, rebuilt in the act of fixing F124.

**How it got through:** 244G's scanner was run before the regression and
reported clean — **over the Phase 255 test file, not over this one.** The call
takes a directory; it was given one file. Scanning a subset and reporting it as
covering the change is the same error as reading a `head`-truncated grep, which
is what produced the eleven-pin hunt in the first place.

**Fixed in `65959c4`:** the invariant is now asserted directly from both
sources here, so this file fails on its own if the genuine pin is ever removed;
the existence check reads through `code_of()`, which blanks comments and
docstrings; and the scanner was re-run over the whole `tests/` tree — no
offenders.

### F125

**The ROADMAP_AUTHORITY contract drifted between its two copies, which is the drift class it exists to prevent.**

`ROADMAP_AUTHORITY.md` states: *"Identical copy committed to both repos… Do not
edit one copy without the other."* Found on 2026-09-21 while amending it:

| copy | bytes | has F54 amendment? |
|---|---|---|
| `moto-diag/ROADMAP_AUTHORITY.md` | 6,135 (pre-edit) | **yes** |
| `moto-diag-mobile/ROADMAP_AUTHORITY.md` | 5,138 (pre-edit) | **no** |

The **"Inventories are not status" amendment (added 2026-09-02 under F54)** was
committed to the backend copy only. The mobile repo carried a contract missing
one of its two amendments for **19 days**, and the mobile copy was the one a
reader in that repo would have consulted.

**Repaired** in the same commit that added the findings rule: the mobile copy
was replaced with the backend copy, and both are now byte-identical
(`md5 87f96432e7534ffd53f33b2a96f5eefa`).

**The structural point.** This contract's stated purpose is to remove a drift
class "structurally rather than relying on hand-sync discipline" — and it is
itself maintained by hand-sync discipline, which failed. The amendment
procedure requires a matched commit to both copies and nothing verifies it.

**What would close it:** a check that the two copies are byte-identical, run
where it cannot be skipped. A test in the backend suite can read the mobile
path only when both repos are checked out side by side, which is the normal
layout here but not guaranteed — so the check should skip loudly (naming why)
rather than pass when the sibling repo is absent, since a silent skip is how
this went unnoticed. **Not fixed here:** it needs a decision about where the
check runs, and a skip that is counted rather than invisible is exactly the
close-out gate discipline this project already learned once.

### F126

**The fourth retrieval door has been dead since it was written, and a bare `except` hid it.**

Found by the chokepoint phase's Step 0, asking the question directly: *which
code paths read `known_issues` for prompt, search or prediction purposes?*
Three were known. There is a fourth — `shop/priority_scorer.py`, which feeds
the AI work-order priority scorer — and it is not leaking. **It has never
returned a single row.**

```python
kb_rows = conn.execute(
    "SELECT id, title, severity, fix FROM known_issues "      # <-- no such column
    "WHERE LOWER(make) = ? AND (model IS NULL OR LOWER(model) LIKE ?) LIMIT 5",
    ...
).fetchall()
```

**There is no column `fix`.** It is `fix_procedure`, and `fix` has never
existed in the schema — not in `SCHEMA_SQL`, not in any migration. Every call
raises `sqlite3.OperationalError: no such column: fix`, and the enclosing
`except Exception: return []` converts it into an empty result.

**Measured against the live database**, running the same query with the column
name corrected:

| vehicle | returns today | would return |
|---|---|---|
| Harley-Davidson Road King | **0** | 5 |
| Yamaha YZF-R1 | **0** | 5 |
| Suzuki GSX-R1000 | **0** | 5 |
| Suzuki SV650 | **0** | 5 |
| KTM 390 | **0** | 5 |
| Kawasaki Ninja ZX-10R | **0** | 2 |
| Honda CB500 | **0** | 2 |
| Honda CBR954RR, cbrf4i, Yamaha MT07 | 0 | 0 |

**Seven of ten live vehicles lose real knowledge-base context**, and the
scorer is told the corpus has nothing to say about the machine. That is not a
missing feature the user can see — it is an AI prioritisation running on a
silently emptied input, which reads exactly like a legitimate "no known
issues".

**No test covers the function.** `grep` for `_find_kb_matches_safe` across
`tests/` returns nothing, so the docstring's promise — *"Try Phase 08
known_issues lookup; fall back to empty list on miss"* — was never exercised
against a real schema. The fallback was written for a **missing table**, and
it silently absorbed a **wrong column** instead.

**Three defects, one line apart:**

1. **Wrong column name**, never caught because nothing executed the query in a
   test.
2. **`except Exception` swallowing everything**, so a schema error is
   indistinguishable from an empty corpus — the F103 family: *a failure that
   reads as no results*.
3. **Substring model matching** (`LOWER(model) LIKE '%...%'`), the exact
   defect Phases 244C–244I removed from the main retrieval path. This door
   never got the fix because nobody knew it was a door.

**FIXED 2026-09-21 — this is a bug, not a finding to carry.** Two of the three
defects are closed on master in their own commit, ahead of Phase 256:

* **the wrong column** — `fix` → `fix_procedure`. The function now returns rows,
  and the counts match this ticket's table exactly: Road King 5, YZF-R1 5,
  GSX-R1000 5, SV650 5, KTM 390 5, ZX-10R 2, CB500 2.
* **the bare `except`** — narrowed to the one case it was written for, a
  missing `known_issues` table on an older install. Everything else raises. A
  schema error that reads as an empty corpus is the defect; the typo was only
  how it got in.

`tests/test_f126_priority_scorer_kb_lookup.py` covers both halves. The
negative control builds a database whose `known_issues` genuinely lacks
`fix_procedure` — a real schema mismatch, not a mocked driver — and asserts it
**raises**; a paired positive control proves the same database *with* the
column returns a row, so the raising test cannot pass by always failing. The
whole file was run against the restored defect: **4 of 8 fail**.

**The third defect stays open and belongs to Phase 256:** the model match is
still `LOWER(model) LIKE '%...%'`, the substring matching Phases 244C–244I
removed from the main retrieval path. It is deliberately unchanged here —
this commit exists to establish the **before** number, and changing the
retrieval shape in the same breath would make before and after
incomparable.

### F127

**Four real documents on disk cannot be read, and 32 more files are download debris.**

A census of every PDF in the research library, run while auditing Phase 255's
negative claims: **263 files, of which 36 could not be parsed.** They split
cleanly into two problems with two different remedies.

**(a) Four are genuine documents that a parser cannot open — these are worth
OCR.** Each is a real manufacturer document sitting in the library and
contributing nothing:

| file | size | pages | problem |
|---|---|---|---|
| `honda/grom_service.pdf` | — | **266** | image-only, zero extractable text |
| `pdfs/piaggio_primavera_om.pdf` | 5.9 MB | **53** | image-only, zero extractable text |
| `v2/sympdf/Fiddle_4_Owners_Manual.pdf` | 42.8 MB | — | `PdfReadError` |
| `v2/sympdf/Jet_14_Owners_Manual.pdf` | 42.4 MB | — | `PdfReadError` |

The Grom service manual is the sharpest loss: Phase 252 wanted Grom clutch and
gearbox data and could not read the one document that has it. Phase 254
established the OCR method — tesseract over rendered pages, with positive
controls on known-present terms — so the technique is in hand.

**Own phase, after 255B**, per the operator's decision of 2026-09-21. Not now.

**(b) 32 are not documents at all** — failed downloads saved with a `.pdf`
extension. Confirmed by reading their first bytes: `refute/beverly.pdf` and
`pdf/bev500.pdf` begin `<!DOC` (HTML landing pages), `pdf/bv500.pdf` is the
13-byte string `404 Not Found`, `pdfs/kymco_agility125_sm.pdf` is 103 bytes of
`<html`. Fourteen carry no marque in their filename at all. By marque: 14
unidentifiable, Honda 7, Lance 7, Roketa 2, SYM 2, Kymco 1, Piaggio 1,
Bintelli 1, GTR 1.

**Delete-or-refetch, on this same ticket, not now.** They are worse than
absent: they inflate every "searched N documents" denominator. **That is not
hypothetical — it is how the Beverly 250 "no document" verdict was reached**,
over 227 readable files while 36 were silently excluded, three of them
Beverly-related.

### F128

**Four rows name a machine their own applicability excludes — and one is a contradiction on disk.**

Found by a refuter attacking Phase 256's door-3 change. **No guard in that
phase could have found it**: they all ask whether a machine *receives* rows
it may not have. None asked whether a machine *misses* rows written for it.

| machine | row | cost |
|---|---|---|
| **Kymco Filly LX 50** | **4609** | **rank-1 prediction: critical, confidence 0.747, 3,000 miles overdue** |
| Piaggio Beverly 250 | 4613 | rank 5, high, confidence 0.593 |
| Vespa 946 | 4613 | rank 5 |
| SYM Symba | 4615 | rank 8 |

**No override rule was added, deliberately.** Letting an explicit model
match beat the axis filter would make a row's `model` string authoritative
over a sourced lookup — string-naming as authority, the pattern the
transmission axis exists to replace. **A row naming a machine is a claim;
the lookup is evidence.**

**4609 over-claimed.** It names the Filly because the Kymco Agility service
manual's **recycled page header** prints `FILLY LX 50` on 21 of 183 pages —
which Phase 254 examined and rejected as unestablished attribution. The row
asserted a machine its own document does not establish.

**4615 contradicts itself on disk**: it declares `{"transmission": ["cvt"]}`
while naming the Symba, which Phase 255's own lookup classifies
`semi_auto_centrifugal` from SYM's manual (*"Wet multi-plate type, auto
centrifugal clutch"*).

**Owed by 255B:** drop the Filly from 4609's model column; split 4615's
general half, which resolves the Symba naming. **Beverly 250 and Vespa 946
stay as they are** — closed-unobtainable per F119.

**Guarded permanently**, not phase-scoped:
`tests/test_phase256_chokepoint.py::TestNoRowExcludesAMachineItNames` pins
these four with their reasons and fails on a fifth.
