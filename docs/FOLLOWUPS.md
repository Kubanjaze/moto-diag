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

At the time of writing the highest assigned is **F141** (this file); the mobile
file's highest is **F115**.

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

**Addendum, 2026-09-22 (Phase 255B) — the census, with a count.**
F118 was filed from one machine's retrieval. The corpus-side number is worse
than the retrieval-side number suggested.

Vocabulary `drive chain` / `chain slack` / `chain tension`, case-insensitive,
over `title || description || fix_procedure || symptoms`, scope every
`known_issues_*.json` in `src/motodiag/knowledge/seed/knowledge` (107 files):
**80 rows carry drive-chain content, across 52 files. Exactly 1 declares any
applicability** — and that one is Phase 255B's own, which may not survive its
refuter pass. The other **79 are unscoped**, so they pass the transmission
gate for any machine the lookup resolves as `cvt`.

Phase 255B's refuter pass reached the same conclusion from the retrieval side
with a different vocabulary and got 89 rows — the two counts differ by search
terms, not by substance, and both say the same thing: **almost every
chain row in the corpus is unscoped.** Named live examples it verified:
`known_issues_honda_cross_model.json` "Chain and sprocket maintenance" and
`known_issues_cross_platform_drivetrain.json` "Chain stretch measurement …
all chain-driven motorcycles" both reach a Honda PCX 150;
`known_issues_yamaha_crossmodel.json` reaches a Yamaha Zuma 125.

This is why F118 says the fix is a **final-drive axis** and not a `{manual}`
set: scoping 79 rows by transmission would be inferring final drive from
gearbox type, which is wrong for a belt-drive Harley in the other direction.

---

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

---

### F129

**A row has no identity independent of its title text, so editing a title, make or model on a seeded database duplicates the row instead of updating it.**

`known_issues` carries

```sql
CREATE UNIQUE INDEX idx_known_issues_identity
    ON known_issues(COALESCE(make, ''), COALESCE(model, ''), title);
```

and `issues_repo.add_known_issue` inserts with `ON CONFLICT DO NOTHING`. Those
three columns are therefore the row's identity, and all three are **content**
that a phase may legitimately need to correct.

**Measured, not argued.** Seeding `known_issues_cvt.json` into a fresh database
gave 12 rows. Dropping `Filly LX 50` from 4609's `model` column and re-seeding
the same database gave **13**, with both rows present:

```
id=6   model=Agility 50, Agility 125, People S 250, People 250, Filly LX 50
id=18  model=Agility 50, Agility 125, People S 250, People 250
```

The over-claiming row survives its own correction, and nothing reports it.

**The second keyed reader.** `loader.backfill_row_applicability` matches on
`(title, make)` and applies an `UPDATE`. A title change re-points that matcher
too, so a renamed row silently stops receiving its applicability backfill —
failing open, as an unscoped row.

**Why this bites content work specifically.** Phase 255B had to change a model
column (4609, withdrawing an over-claim), a make column (4605, F115) and would
have liked to trim a title (4615, whose trailing clause moved to another row).
The first two were done through a migration hook that `UPDATE`s matched on the
row's OLD identity; the title trim was **abandoned** — the operator's decision
of 2026-09-21 was to leave 4615's title verbatim rather than risk the
duplicate. So this defect is already shaping content decisions.

**Not fixed in 255B.** A fix means giving rows a stable key that is not their
prose — a slug, a source-file-plus-ordinal, or a UUID written at seed time —
and re-pointing the identity index, the upsert and the backfill matcher at it.
That is a corpus-wide schema and loader change, not a content phase's work.

**What 255B did instead**, and what a fix would let it stop doing:
`knowledge/loader.py::reconcile_255B_rows` and migration 065 carry the old and
new column values as literal pairs so the `UPDATE` can find the row. Every such
pair is a workaround for this finding.

---

### F130

**Two corpora the predictor reads have no applicability field at all, and 24 of 30 patterns in one of them apply to every machine ever made.**

Phase 255 added the transmission axis to `known_issues` and Phase 256 made one
chokepoint apply it. Neither reached these two files, which
`advanced/wear.py` and `advanced/schedule_repo.py` read directly — outside the
chokepoint by construction, because they are not `known_issues`.

| file | shape |
|---|---|
| `src/motodiag/advanced/wear_patterns.json` | **24 of 30** patterns at `make: null`, `model_pattern: "%"` |
| `src/motodiag/advanced/data/service_interval_templates.json` | `chain-clean-lube` at `make: "*"`, described *"Universal chain maintenance"* |

**Demonstrated, not inferred.** Feeding each pattern its own symptom strings and
resolving against two machines that cannot have the part:

| pattern | Honda PCX 150 (CVT, no clutch cable, no chain) | Harley Road King (belt final drive) |
|---|---|---|
| `clutch-cable-stretch` | **matches** | **matches** |
| `chain-stretch-sprocket` | **matches** | **matches** |
| `clutch-basket-judder` | **matches** | **matches** |
| `final-drive-splines` | **matches** | **matches** |

The symptom vocabulary leans the same way: of 40 symptoms, `Clutch slipping` and
`Hard shifting` are manual-machine symptoms, and **none** of belt, creep or
kickstart appears at all.

**This is the exact distinction Phase 255B's content rows document.** 255B ships
a row saying a machine in this class has no drive chain and that a chain
interval is meaningless on it, while `chain-clean-lube` offers that machine a
universal chain-maintenance interval from a different code path in the same
product.

**Not fixed in 255B** — operator's decision of 2026-09-21, filed rather than
scoped. A fix means an applicability field on both files, a reader that applies
it, and guards, which is a mechanism phase like 255 rather than a content phase.

---

### F131

**Six transmission-lookup entries have a canonical name that does not resolve to their own entry, and one of them is a name a rider would actually type.**

`TRANSMISSION_LOOKUP` holds 50 entries. Resolving each entry's own `canonical`
string against its own `make` returns a different entry, or `unknown`, for six:

| canonical | resolves as | aliases it does have |
|---|---|---|
| `SH125i/SH150i` | unknown | `sh125i`, `sh150i`, `sh 125i`, `sh 150i`, `sh125`, `sh150` |
| `XC155 / SMAX` | unknown | `xc155`, `xc 155`, `xc155f`, `smax`, `s max`, `s-max` |
| `Jet 50/100` | unknown | `jet 50`, `jet50`, `jet 100`, `jet100`, … |
| `LX 125/150` | unknown | `lx`, `lx 125`, `lx125`, `lx 150`, `lx150` |
| `GTS 300/310` | unknown | `gts`, `gts 300`, `gts300`, `gts 310`, … |
| **`CT125 Hunter Cub`** | **unknown** | `ct125`, `ct 125`, `trail 125`, `ct125a`, `hunter cub` |

**Five of the six are harmless.** They are compound display labels covering two
models — nobody types `LX 125/150` as a model name, and every real spelling is
in the alias tuple.

**The sixth is not.** `CT125 Hunter Cub` is Honda's own name for the machine. A
rider or a technician who enters it gets `provenance='unknown'`, every
transmission candidate open, and therefore — under the fail-closed filter Phase
255 built — **every transmission-scoped row withheld**. Entering `CT125`,
`Trail 125` or `Hunter Cub` instead works correctly. The failure is silent and
looks like a machine with no known issues.

```
resolve_transmission("Honda", "CT125 Hunter Cub") -> unknown, entry=None
resolve_transmission("Honda", "CT125")            -> model-sourced, semi_auto_centrifugal
```

**Same family as the Phase 255B Step 0 finding** that the junction stores
marque-prefixed model strings (`Honda PCX150`) the tier query cannot match
against the resolved `PCX 150` — 469 of 2,424 junction rows, 19%. Both are
string-matching gaps between how a name is stored and how it is looked up.

**Not fixed in 255B**, whose non-goals forbid adding lookup entries. Pinned
instead: `tests/test_phase255B_twist_and_go.py::test_the_canonical_name_gap_is_recorded_not_silently_worked_around`
asserts the set of six, so a seventh fails the suite.

**A related coverage gap, recorded here rather than as its own finding:** the
Kymco `Like 150i` entry's aliases are `like 150i`, `like150i`, `like`. `Like
50i` and `Like 125` resolve `unknown`. This cost 255B real coverage — the row
about the Kymco Like owner's manual's clutch-lever defect applies to the
combined Like 50i/150i edition too, and had to be declared for the `Like 150i`
alone rather than name a machine the lookup cannot place.

---

### F132 — CLOSED by migration 065 (Phase 255B, 2026-09-22)

**An unevidenced year window silently gated retrieval on shipped rows.**

Filed as a follow-up and reclassified the same day as a live defect, because
`cli/diagnose.py::_covers_year` applies `year_start`/`year_end` **before**
retrieval. The Phase 254 CVT rows carried a 25-year window, 2002–2026, cited
to nothing at either end. `estimated_hours` was set on all thirteen rows in
the file and **none of them describes a repair** — checked, not assumed: no
`fix_procedure` in the file contains a repair action.

**Scope rule applied:** only windows no cited document supports; a row whose
description names a model-year range keeps it. Two did — *"It covers 4,262
units across model years 2015 to 2020"* and *"model years 2003 to 2026"*.
Eleven did not.

**The evidence it shipped on.** Nulling a bound removes a gate, so this can
only widen, which is the direction the phase had otherwise been tightening.
Measured over 11 machines × 8 model years, rows entering / leaving:

```
machine                      class        2001   2003   2005   2013   2019   2022   2026   2027
------------------------------------------------------------------------------------------------
Honda PCX 150                cvt            +9   same   same   same   same   same   same     +9
Kymco Agility 50             cvt           +10     +1   same     +1     +1     +1     +1    +10
Vespa LX 50                  cvt           +10     +1   same   same   same     +1     +1    +10
Yamaha Zuma 125              cvt            +9   same   same   same   same   same   same     +9
Genuine Buddy 125            cvt            +9   same   same   same   same   same   same     +9
Kymco People S 250           cvt           +10     +1   same     +1     +1     +1     +1    +10
Honda GL1800 Gold Wing       NOT cvt        +2   same   same   same   same   same   same     +2
Yamaha YZF-R1                NOT cvt        +2   same   same   same   same   same   same     +2
Honda Grom                   NOT cvt        +2   same   same   same   same   same   same     +2
Kawasaki Ninja 400           NOT cvt      same   same   same   same   same   same   same   same
SYM Symba 100                semi-auto      +2   same   same   same   same   same   same     +2
------------------------------------------------------------------------------------------------
TOTAL entering: 143    TOTAL leaving: 0
```

**Nothing leaves.** Non-CVT machines gain two rows, and both are unscoped by
design — 4605, the drive-belt vocabulary row, and 4615's general half about
the regulator record. No scoped CVT content reaches a machine the filter
excludes, which is what the guard asserts.

**The first version of this table was wrong** — 123 entering, one row for
non-CVT machines. It was measured against a database in which migration
065's hook had seeded rows on an empty database, because an anchor guard had
been deleted. Corrected from a correctly seeded database. Recorded because a
measurement taken on a broken fixture reads exactly like a correct one.

**Also settled here rather than row by row:** `source: service-manual` means
a **manufacturer document**, not literally a service manual. Measured across
all 107 seed files — 192 rows carry the label and **75 of them (39%) cite an
owner's manual** in their own description. That is the label's meaning, not
an error repeated 75 times. Stated in
[`docs/architecture/applicability-axes.md`](architecture/applicability-axes.md);
no new enum value, no rows mislabeled.

**Closed by migration 065.** Live database round trip verified: rows with a
year window 12 → 2, rows with `estimated_hours` 12 → 0. Guarded by
`tests/test_phase255B_twist_and_go.py::TestF132UnevidencedMetadata`, three
tests, each broken on purpose and seen to fail.

---

### F133 — FOLDED INTO F118 (Phase 255B, 2026-09-22)

**Reserved, not independently filed.** The finding — that almost every
drive-chain row in the corpus is unscoped, so it passes the transmission
gate for any CVT machine — is the corpus-side measurement F118 was missing,
not a separate defect. Operator's decision, 2026-09-22: attach to F118
rather than open a number.

The census lives in **F118's addendum** above: vocabulary `drive chain` /
`chain slack` / `chain tension` over `title || description || fix_procedure
|| symptoms`, scope all 107 seed files, **80 rows across 52 files, exactly
one declaring applicability, 79 unscoped.**

The number is recorded here so it is not reused, and so a reader who meets
"F133" in a commit message or transcript finds where it went.

---

### F134 — CLOSED by the deduplication commit (Phase 255B, 2026-09-22)

**Counting file paths as documents inflated every "N manuals say X" claim.**

The evidence library held **263 `.pdf` files and 172 distinct documents**.
The Genuine Buddy Kick owner's manual existed under **five** paths, the
Kymco Agility owner's manual under four, the Honda CHF50 service manual
under three.

**Two claims were already wrong because of it**, both inside Phase 255B:

* a Kymco Like owner's manual was cited as appearing in *"two editions"* —
  three paths held **one byte-identical file**, md5 `de2df98e…`, 3,163,921
  bytes, 61 pages. That sentence was the row's entire reason for existing,
  promoting it from a typo in one book to a document-integrity defect.
* a SYM count treated `pdf/sym_fiddle3.pdf` and
  `v2/sympdf/Fiddle_III_Owners_Manual.pdf` as two machines. Byte-identical,
  md5 `9d8814f3…`.

**Closed by deduplicating on content hash**: 75 redundant copies removed,
533.8 MB, every one byte-identical by md5 to the copy kept.
`~/research/motodiag/DEDUP_MANIFEST.md` maps each removed path to its
replacement. The **16 download-debris files were deliberately not
deduplicated** — they are F127's evidence and two repo documents cite
`pdf/bv500.pdf` by path.

**The rule that replaces the practice:** a claim about how many manuals say
something cites **distinct documents, not paths**, and a count taken by
globbing the library is wrong by construction until it is hashed. Recorded
in `ROADMAP_AUTHORITY.md`, matched in both repos.

**One more instance of the same census error, for the record:** this phase
wrote *"247 readable PDFs"* into `ROADMAP_AUTHORITY.md` — a **file** count
quoted as a **document** count. The real figure is **172**, wrong by 75.

---

### F135

**What the corpus means by a "model" — group (B) is a 244I semantics question, not a spelling one**

Filed by Phase 255C, which explicitly left it undecided. 255C's positive
extraction gate closes **group (A)** — fragments with no code token and a
bare lowercase word — with a whole-corpus negative control that rejects
exactly 55 strings. **Group (B) it does not touch, and cannot.**

Group (B) is **28 strings that carry a code token but read as prose**, and
**no shape rule separates them.** The pair that shows why:

| string | verdict | why it is hard |
|---|---|---|
| `R1200 hexhead` | a real engine-family designation 244I's vocabulary is built to carry | number plus lowercase words |
| `2020 service manual` | debris | number plus lowercase words |

Phase 255C's bug fix #5 added a third specimen from the other direction:
`KTM LC8 75-degree V-twin` is now indexed as a model for KTM, and it is an
**engine**, not a machine. It reached the junction through the same
ambiguity — it carries a code token, so no gate rejects it.

Telling these apart requires deciding **what the corpus means by a model**:
whether an engine family, a generation nickname, or a service-document title
is a thing a caller can own. That is 244I semantics, and it belongs with the
general-applicability axes (F117 cooling, F118 final drive) rather than with
identity normalisation.

**Group (B) strings stay exactly as they are today.** They are not debris and
removing them would lose real designations; they are simply not decidable by
shape.

**Correction recorded with this entry:** Phase 255C's plan states this was
"filed on the general-applicability ticket". It was not — the claim was
written and the entry never created. Found at close-out by checking
`FOLLOWUPS.md` for the ticket the plan cited. **A document saying a thing was
filed is not the filing**, which is the same class as every census error this
week: the claim was checked against what it sat next to rather than against
what produced it.

### F136

**"Every consumer" was enumerated over `src/` and missed a canonical pinned in a test**

Phase 255C's decision 5 required that the resolver change reach every
consumer of canonical strings, with a positive control, **before v1.0**. D4
did that: an AST-based enumeration, sixteen pinned literals named, a positive
control proving the enumeration found what it looked for.

The full regression found a **seventeenth**.
`tests/test_phase245_damon_absence.py` asserts
`identity.model.resolved == "Damon HyperSport"` — a canonical string, pinned
in a test, asserting a resolver return value. D4 enumerated consumers in
`src/`, so it could not have seen it.

**The positive control proved the enumeration found what it looked for. It
did not prove the enumeration looked in the right places.** That is the
distinction between validation and verification, applied to a census rather
than to a test, and it is the third time this week the same shape has landed.

**What to change:** an enumeration whose subject is "every consumer of X"
scopes over `src/` **and** `tests/`, because a pinned literal in a test is a
consumer — it is the one that fails the build. Cheap to do: the sixteen were
found by AST; the seventeenth would have been found by the same pass with
`tests/` in its roots.

### F137 — CLOSED by Phase 255D fix #8, `b934926` (2026-09-22)

**`verify_phase.sh` check 2 scoped "code" to `src/` and `tests/`, and could not see `.claude/`**

Check 2 asks whether any code changed between the regression hash and the
tip — whether the green run describes the tree that shipped. It was
`git diff REG..TIP -- src/ tests/`. Phase 255D's bug fixes #5 and #6 changed
`.claude/skills/closeout/closeout_check.py` and
`.claude/skills/finding/finding_check.py` **after** the closing regression
at `b0ae748`, and check 2 printed only the floor-test bump.

Measured over the tracked tree: code lives outside those two directories in
`.claude/` (six scripts, the hook settings, the fixtures the checks read),
`scripts/`, `data/pricing/`, `main.py`, `pyproject.toml`, the Docker files
and `.pre-commit-config.yaml`. **The two-directory scope was an exclusion
nobody had written down as one** — everything else was silently treated as
documentation. It is F136's shape again: a census scoped to where the author
expected the thing to be.

**Closed by** `code_after_regression.py`, which inverts the rule: a path is
code unless it is positively documentation (`docs/`, `.md` outside the code
directories, `LICENSE`, `.gitignore`, `.gitkeep`). Controls: a hand-written
path-list fixture; the real `b0ae748..3dfc78a` range, which must report both
skill scripts; and a census asserting every tracked script classifies as
code. With the old scope restored, all three fail.

### F138

**The workspace `CLAUDE.md` is 926 lines, and shrinking it further is a decision about what stops being shared, not a tidy-up**

Phase 255D split the workspace `CLAUDE.md` (in `workspace-docs`) from
1,337 lines to 889, moving every project-specific line out. It has since
grown to **926** with that phase's own additions. The phase's Deviations
section records why 889 was not the ~174 estimated: 174 measured the rules
*cited in a working session*, not what is legitimately cross-project.

What remains is cross-project by content — the phase template, versioning,
Lean API usage, Python standards, architecture, the failure-family taxonomy,
prompt templates and a 149-line change log. Moving more means
deciding that some of those stop being shared rules for every project, which
is the operator's judgement and not a mechanical split.

**What would close it:** a decision, per section, on whether it stays
shared, moves to a project `CLAUDE.md` or a skill folder, or is archived —
and for the change log, whether it moves to its own file. Filed as a
follow-up by instruction; deliberately not done in 255D.

### F139

**A parallel session's manual-coverage Step 0 was directionally right and numerically loose**

Before Phase 257, another session drafted a Step 0 for sourced
manual-transmission coverage. Cross-checked read-only on 2026-09-22 against
the live database (schema 66, 1,046 issues, junction 2,795). **The
cross-check's figures are the numbers of record:**

| claim | other session | of record | why they differ |
|---|---|---|---|
| spellings resolving `unknown` | 605 | **605** | agree (689 junction pairs; 38 are EV marques that resolve `powertrain-default` once `powertrain='electric'` is passed) |
| unknowns with no on-disk manual naming the transmission | 427 | **~600** | spelling-match noise: junction strings such as `'1000'`, `'One'`, `'Bolt'`, `'20'`, `'Gilera'` occur as ordinary words in scooter manuals. Only **5** unknown spellings have a maker manual on disk stating a manual gearbox (SYM Wolf Classic 150, Wolf CR300i, Kymco K-Pipe, Honda Grom, Grom 125) |
| unscoped manual-side rows | 70 | **78** (75 without EV regen rows 4557/4560/4562) | vocabulary; 206 is the positive control in both. A keyword count is not a verdict count — read in context, about half of the hits reaching scooters are shaft-drive, DCT or scooter rows |
| manual-side rows a PCX 150 retrieves | 13 | **13** | agree |
| why 255B saw "3 clutch + 2 shifting" | the pre-256 25-row cap | **a narrower vocabulary** | under a 25-row cap the PCX keeps **1** such row (4605); 255B's own S0-4 records 165 rows retrieved, so the cap was not in play |
| cost of declaring `{manual}` | 517 machines / 2,959 losses | **531 / 3,186** | universe (694 = junction ∪ vehicles) and row set; the 79 CVT scooters' 337 losses are the intended effect, not cost, so only `unknown` machines count |

**Shape of the error:** every loose figure came from counting what a search
matched rather than what the matched thing was — the "measure what produced
the number" rule, and the reason 257's SOP forbids spelling-match counting.

**What closes it:** Phase 257's census and cost table are built on the
figures of record, with the method stated. Note for readers: 255D's own
documents mention F138–F140 as the `finding` fixture's fabricated numbers;
those mentions describe the fixture and do not cite this entry or F140.

### F140

**The no-`{manual}` sequencing rule is enforced on seed JSON only; nothing checks the live table**

Phase 255's A1 forbids any row declaring a transmission set containing
`manual` until manual coverage is sourced — a `{manual}` row is withheld
from every machine resolving `unknown` (531 of 694 machines today). The rule
is enforced by exactly two tests, both of which read seed files:
`tests/test_phase255_transmission_axis.py::test_no_shipped_row_declares_manual`
(every `known_issues_*.json`) and
`tests/test_phase255B_twist_and_go.py::test_no_row_in_the_file_declares_a_set_containing_manual`
(the CVT seed). `knowledge/applicability.py` lists `manual` as a valid value,
so the loader accepts it, and a migration hook, `post_apply` backfill or
direct write would put one in the live table with no test failing.

Measured: the live table holds **11** scoped rows, all
`{"transmission": ["cvt"]}`. **Clean by content, not by enforcement.**

**What closes it:** an assertion over the database the loader and the
migrations actually build, with a positive control that plants a `{manual}`
row in a fixture database and sees the check fail. Or, if Phase 257 lifts
the rule, retire both seed tests in the same commit that lifts it, with the
reason — a rule enforced in one place and lifted in another is how the two
drift.

### F141 — CLOSED by the entry_check provenance rule (E9), 2026-09-22

**entry_check E3 verified quotes against the model's own saved copies, not against the originals they claim to come from**

Phase 257's Honda batch cited `./evidence/grom2025.txt` and
`./evidence/grom2020.txt` — text files the sandboxed source stage itself
rendered from the on-disk HTML — and `entry_check.py`'s E3 string-matched
the quotes against those saved copies. A model that edits its own copy
(fabricates a quote, changes "4 speeds" to "5") passes E3 today, because
the check and the copy are both under the model's control. The same
shape was true of every document under `evidence/`: SYM's runs saved both
the fetched PDF and a `.txt` extraction, and E3 read the `.txt`.

Refute opens the cited document independently, so tranche 1's entries
are not affected — the gap is in the gate, not in what it let through
this time. Measured: `check_one` read `f["document"]` and nothing else;
no check anywhere read an original behind a copy, and no field recorded
which original a copy came from.

**What closes it:** a document under `evidence/` must declare its
original in a `<file>.provenance.json` sidecar — an on-disk library path
or a URL, plus the original's sha256 (and, for a URL, the pinned fetch
entry_check can read offline). E9 rejects a copy with no sidecar, an
unreadable original, or a hash that no longer matches; E3 extracts the
text from the ORIGINAL itself — HTML→text in entry_check's own code,
`.txt` raw, PDF via pypdf — and matches the quote against that, never
against the saved copy. Known-bad fixtures plant a doctored copy (quote
in the copy, absent from its declared original), a missing sidecar and a
stale hash; break-it tests verified each fires and that disabling the
original-matching makes the doctored-copy test fail. The source-stage
prompt now instructs the model to write the sidecars. Filed and closed
by the same commit (Phase 257, branch `phase-257-orchestrator`).

