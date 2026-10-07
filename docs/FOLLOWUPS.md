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

At the time of writing the highest assigned is **F195**.

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

### F121 — CLOSED by Phase 257B (moto-diag `70c3f23`, mobile `0e1ed53`), 2026-09-24

**Closed:** the rider sets, changes or clears the transmission on the
vehicle screen, the API stores it, and every retrieval door uses it first
(provenance `explicit`). The create screen still posts none; that
remainder is F147 (mobile file).

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

### F141 — CLOSED by the no-tools source stage and E10 (excerpt binding), 2026-09-23; E9 alone did not close it

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

**Reopened 2026-09-23 — E9 did not close it.** The model writes the
sidecar, so the "original" it declares can be another file it wrote.
Three cases, each accepted by `check_one` with zero failures: (a) a
document in the clone root, outside `evidence/`, is read directly as an
original; (b) a sidecar whose `original` is a second model-written file
in `evidence/`; (c) a URL original whose `fetched_as` is model-written.
The sha256 pins only that the model's two files agree.

**What closed it:** the token redesign. The batch source stage is one
turn with `--tools ""` and writes nothing; its only inputs are the
library excerpts `candidates.py` cut. **E10** rejects a finding whose
document is not one of those excerpts or whose quote is not inside them,
and E3 matches the library original itself. Planted: a document not
handed over (the quote in it, the machine named — E3/E4 pass), and a
quote from the right file outside its excerpt; break-it seen to fail for
each. E9 stays for any path that still saves copies.

### F142

**Multi-make rows put every model under every make in the junction**

69 `known_issues` rows carry more than one make in `make` (`'Kymco, SYM'`,
`'Yamaha, Kymco, SYM, Genuine'`), and the junction `known_issue_models`
pairs each of their models with each of their makes: 1,129 junction rows,
192 distinct (make, model) pairs. Where a row names machines of several
makes, most of those pairs are wrong. Measured instances (Phase 257, while
classing census spellings): SYM's Jet 14, Fiddle 4 and Wolf CR300i filed
under Kymco (#4593, #4596); Kymco's X-Town 300 under SYM (same rows);
Yamaha's XC50 under Kymco, SYM and Genuine (#4603).

What it affects: a row filed under the wrong make is found by that make's
owners and may never reach the real make's owners — a Kymco query sees
SYM's Jet 14, and whether a SYM owner's retrieval reaches the row depends
on the make column, not on the machine. How many of the 192 pairs are
wrong is **not measured**; 192 is the ceiling.

Phase 257 only keeps these spellings out of the transmission census, by
named `other_make_model` entries in
`.claude/skills/source-transmission/census.py`. **Not fixed in 257.**
What would close it: the junction built per (machine, its own make) —
each model in a multi-make row assigned to the make that builds it — with
a whole-junction count of the pairs that move, and a test that a
multi-make row cannot produce a pair outside its models' own makes.


### F143

**Transmission coverage stopped where acquisition did: 528 census spellings still resolve unknown**

Phase 257 built the sourcing machine and ran it make by make until the
operator named KTM the last make (2026-09-23). At close the census
(`census.py`, whole junction) is **528** unknown (make, spelling) pairs,
**412** of them machine names; it was 605 when 257 opened.
`TRANSMISSION_LOOKUP` holds 121 entries, 71 of them written in 257. What
remains, by why it remains (machine-name counts from the census):

- **Maker site refuses a script (403), waits for the operator inbox**
  (`~/research/motodiag/inbox/<Make>/`, then `acquire.py ingest`; its
  smoke test has never run): Ducati 53, Aprilia 23, Piaggio 28, Vespa 22,
  Moto Guzzi 9. **Triumph 52**: its handbook list is reachable but the
  download returns 403 (downloads switched off); inbox too.
- **No measured route in `acquire.ROUTES`**: Harley-Davidson 16 (also
  inbox, operator), Energica 10, LiveWire 7, Damon 3.
- **A route exists, never batched**: MV Agusta 20, Zero 15, Genuine 4.
- **Batched, remainder unresolved**: BMW 32 (family pages write nothing),
  Kawasaki 29, Suzuki 25, Honda 20 (12 never sent; the E-Clutch CB650R
  and CB750 await a decision on an E-Clutch value), Yamaha 20, KTM 15,
  Kymco 6, SYM 3.
- **Held unknown by operator decision**: Yamaha MT-09 and MT-07 (whether a
  Y-AMT version is sold where a vehicle was bought; Yamaha's US pages name
  none, Europe's were never fetched). KTM "1290 Super Duke" and "Super
  Adventure S" (list matches only a longer name, the 4609 rule); KTM "EXC"
  and "Enduro R" (no manual of their own; not sent).
- **Sourced on the fallback route, to re-source when Subconscious is
  back**: 57 entries carry `source_route="claude-opus-5-5@medium"`
  (KTM 26, Yamaha 18, BMW 7, Honda 5, Suzuki 1); one filter on the field.
- **Seen, not fixed**: `toc_line` still drops BMW's prose cross-references
  printed with a "b" page glyph ("the auxiliary stand (b 24-27)").

What it affects: every unknown machine loses every transmission-scoped
row; 412 machine spellings do today. What would close it: the inbox run
for the 403 makes, routes for the four without one, batches for the three
with one, a re-source of the 57 fallback entries on Subconscious, and a
census back under a figure the operator sets.


### F144

**Video `/ask` never passes a vehicle's powertrain to retrieval**

`api/routes/videos.py` calls `rows_for_machine(...,
powertrain=getattr(context, "powertrain", None))`, and `VehicleContext`
has no `powertrain` field, so the value is `None` for every vehicle. The
resolver's third rung (`electric` ⇒ `direct_drive`, minus the listed
exceptions) is therefore unreachable from the API: an electric machine the
lookup does not name resolves `unknown` in `/ask` and `powertrain-default`
in `motodiag diagnose`. Found in Phase 257B Step 0, where the same shape
hid the vehicle's `transmission` (fixed there).

Not fixed in 257B on purpose: wiring it changes the answer for an unset
electric vehicle, and 257B's finish line requires unset to mean exactly
the previous behaviour. Exposure today: the live `vehicles` table holds 10
machines, all `ice`, so zero. What would close it: a `powertrain` field on
`VehicleContext` filled by `_build_vehicle_context`, and a test that an
unset electric vehicle resolves `powertrain-default` through `/ask`.

### F148 — CLOSED by `bac634d` (close-out tooling, not a phase), 2026-09-24

**Closed:** A7 now takes the newest phase as the history row with the
latest Date, with same-day rows ordered by the commit that first added
each row. Known-bad fixture `fixtures/a7_newest_bad` (A7 was silent on it on
master, and fires now) and `fixtures/a7_newest_good` (passes). Recorded in
the closeout skill's `CHANGELOG.md`.

**closeout_check A7's version-header half can only fire for Phase 244M**

`closeout_check.py` A7 takes the newest phase as the first `| **` row of
`implementation.md`'s history table (`rows[0]`) and checks the version
header only when the phase under check equals it. The table is not in
date order: its first bold row is **244M** (line 473 on 2026-09-24), and
257 sits at line 499. So for every phase but 244M the header half of A7 is
skipped, and a close-out that forgets the version bump passes it. Seen in
Phase 257B's close-out, reading A7 to learn what it needs. Not fixed there
(a change to the close-out's own checks is outside a transmission-field
phase). What would close it: take "newest" by the Date column (or by the
header's own phase), with a known-bad fixture where the newest row is not
first.

### F149

**Three unverified Honda `model = All` charging rows reach every Honda scooter at tier 1, and two of them prescribe a procedure the scooters' own manuals do not use**

Rows #263 ("Regulator/rectifier failure — the universal Honda problem"),
#264 ("Stator failure diagnosis and replacement — all Honda models") and
#270 ("Charging system preventive testing — annual check protocol") are
`source = unverified`, `model = All`, with no applicability. Measured in
Phase 354's Step 0 on a copy of the live database: they reach a Ruckus, a
PCX150 and a Metropolitan at `make_wide`, ranked above every other-model
row. #263 tests a "3-pin yellow connector" against a fixed 13.5-14.5 V
window and replaces the regulator with a separate MOSFET unit ("fits 90% of
Hondas"). Honda's PCX150 service manual puts the regulator/rectifier inside
the ECM (p. 20-4), names the stator leads Red/yellow, Red/white and
Red/blue (p. 6-6), and sets the standard relative to the battery's own
voltage (p. 20-9); the CHF50's manual ends its tree at "Faulty ECM"
(p. 15-5).

What it affects: every Honda scooter whose own row does not reach it at
tier 0. Phase 354's PCX150 and CHF50 rows outrank the three for those two
machines (tested); a Ruckus, a current Metropolitan and a PCX125 or PCX160
still see them first among charging rows.

Not fixed in 354: row identity is (make, model, title) (F129), so scoping
or rewording them needs a migration, and they cite no document to correct
against. What would close it: source the three against Honda motorcycle
service manuals and scope them to the machines those manuals cover, or
narrow their `model` from `All`, by migration, with a test that a Honda
scooter no longer receives them at `make_wide`.

### F150

**The manual the corpus calls the SYM Symply 125 never names a model beyond "MODEL ABA"**

`manuals/service/sym_symply125.pdf` in the research library says "SYM
series" and "MODEL ABA" (52.4 × 57.8 mm, about 125 cc); the string
"symply" appears 0 times in its extracted text, and the cover badge is not
legible. Only the file name says Symply. Measured by Phase 354's SYM
refuter. Phase 254's CVT rows nonetheless attribute a figure to it by
name — "SYM's Symply 125 gives a 19.0 mm limit" — and list "SYM Symply
125" in the model column of every row in `known_issues_cvt.json`, so a
Symply 125 owner reaches that figure at tier 0 on an identity no document
establishes.

Phase 354 kept the Symply out of its SYM row for this reason, and its
test forbids the name there. Not fixed in 354: the 254 rows are another
phase's content, and their titles are part of their identity (F129). What
would close it: a SYM document that ties model ABA to the Symply 125 (a
parts catalogue, a VIN decoder page, SYM's own spec sheet), or the name
removed from 254's rows by migration with the figure re-attributed to
"a SYM 125 cc service manual (model ABA)".

### F151

**The 80 `cross_platform_*` rows state general advice but are each filed under one make and one large model, so they reach no machine of another make and every other model of their make only at `make_other_model`**

The eight `known_issues_cross_platform_*.json` files (brakes, carbs,
charging, cooling, drivetrain, fi, ignition, starting) hold 10 rows each, all
`source` null. Each row's text is general — one is titled "CV carburetor
diaphragm failure — all makes and models" — but carries a single `make` and
`model` (Honda CB750, Yamaha V-Star 650, Kawasaki KZ1000, Suzuki GSX-R750 …)
and a 1969–2015 window. Measured in Phase 353's Step 0 on a copy of the live
database: a Kymco, SYM, Piaggio, Vespa or Genuine scooter receives none of the
ten carburettor rows; a Honda Ruckus or CHF50 receives 18–19 carburettor rows
at `make_other_model` and a Zuma 50 or Vino 22, headed by rows about a
CBR600F4i float bowl and a V-Star petcock. Eight of the 80 rows use universal
wording in their title or opening.

What it affects: the advice is either unreachable (other makes) or reaches a
machine as another model's row, beneath that machine's own rows; nothing is
anchored to a document.

Not fixed in 353: the rows are another phase's content and their identity is
(make, model, title) (F129). What would close it: decide per row whether it is
general (and then how a general row is represented — the transmission-axis
contract's "absent key means no claim" suggests an explicit all-makes scope,
not a borrowed model) or specific to the model it names; source it or label
it; migrate; and test that a row titled "all makes" either reaches other
makes or no longer says so.

### F152

**Phase 354's CHF50 charging row says the manual "prints the model only as CHF50, and it names no end year"; the manual's cover prints both a name and an end year**

The CHF50 service manual's cover (`honda/chf50_service_mirror.pdf`, PDF p. 1)
has no text layer. Rendered, it reads "2002–2006", "SERVICE MANUAL",
"CHF50/P/S" and "METROPOLITAN™". Phase 354 searched only the text layer, where
"metropolitan" occurs 0 times in 319 pages, and ran no positive control on the
image-only page. It then shipped the sentence "The manual prints the model
only as CHF50, and it names no end year" in the row "Honda's carburetted CHF50
charges through a three-phase alternator/starter that its ECM controls", and
`test_the_chf50_is_not_called_the_metropolitan` in
`tests/test_phase354_scooter_electrical_content.py`, whose docstring repeats
the 0-in-319 count as a fact about the document. Found by Phase 353's Honda
refuter, which rendered the cover; confirmed by rendering it again.

What it affects: one sentence of one row, and the reason a test gives. The
row's modelling is unaffected and still right. It is modelled `CHF50`, so a
current fuel-injected NCW50 Metropolitan does not reach it at tier 0. The
cover's 2002–2006 does not bound the manual either, because its
specification tables also cover "After '07 model NVK00K".

Not fixed in 353: the row is 354's content, and its title is part of its
identity (F129), although this sentence is in the description, not the title.
What would close it: reword the sentence to what the document shows (the
cover names the CHF50/P/S Metropolitan, 2002–2006; the tables reach after '07),
change the test to pin the modelling rather than the absence, and re-load.
Phase 353's own CHF50 row states the cover as rendered.

### F153

**The CVT rows pair SYM under spellings the track's other layers do not use, so no SYM scooter reaches a CVT row at tier 0**

Phase 254's multi-make CVT rows name SYM machines in their `model` columns
as `SYM JET 50`, `SYM JET 100`, `SYM Joyride`, `SYM Symply 125` and
`SYM Symba`; the junction (250C attribution, 255C canonical pairs) stores
those as `(SYM, Jet 50)`, `(SYM, Joyride)`, `(SYM, Symply 125)` — bare
spellings no query for the machines 353 and 354 cover would resolve to.
The electrical and carburettor layers pair the same machines under
`Jet Euro 50`, `Joyride 125`, `Fiddle 50`. Measured in Phase 258's Step 0
on a freshly seeded 1,060-row database: `(SYM, Jet Euro 50)`,
`(SYM, Joyride 125)` and `(SYM, Fiddle 50)` each hold exactly 2 tier-0
pairs (the electrical and carburettor rows), where `(Kymco, Agility 50)`
holds 11, 9 of them CVT. Every SYM machine reaches its CVT content at
tier 2 (`make_other_model`) only, and it reaches the 12-row prompt only
because rank order happens to admit tier-2 rows.

What it affects: a SYM owner's diagnosis presents the CVT layer — content
254 wrote for their machine — labelled as another model's rows, beneath
any tier-0 content that arrives later; and the day a SYM tier-0 row is
added, it will crowd the CVT layer out of the cap entirely (Gate 13's
mechanism, on the SYM half of the track).

Not fixed in 258: a gate writes no content, and the rows' identity is
(make, model, title) (F129). What would close it: a migration adding the
machines' own spellings (`Jet Euro 50`, `Joyride 125`, `Fiddle 50`) to
the CVT rows' model columns — or junction pairs for them — with a test
that a SYM query reaches a CVT row at tier 0. Pinned by
`tests/test_phase258_gate14.py`, whose SYM tests are written to fail
when this closes.

### F154

**"Fiddle 50" is missing from TRANSMISSION_LOOKUP, so the machine 354 and 353 name at tier 0 resolves transmission `unknown` and loses the scoped CVT layer entirely**

`knowledge/transmission.py`'s SYM Fiddle entry carries the spellings
`("fiddle", "fiddle iii", "fiddle 3", "fiddle3")` — the Fiddle III the
257 census sourced — but not `fiddle 50`, the spelling the corpus's own
rows use: `known_issues_scooter_electrical.json` and
`known_issues_small_engine_carbs.json` both list "Fiddle 50", and 354's
tier-0 test machines name it. Measured in Phase 258's Step 0: a
`(SYM, "Fiddle 50")` retrieval resolves provenance `unknown`; the
applicability filter (255, through the 256 chokepoint) then withholds
**8 rows** — every `{"transmission": ["cvt"]}` row in the corpus — and
the Fiddle 50's 12-row prompt holds none of 254's roller, belt or clutch
content, only the two unscoped naming/recall rows. The withheld count is
recorded in `retrieval_withheld`.

What it affects: the one machine the electrical and carburettor layers
both cover at tier 0 that cannot see the CVT layer at all; its owner's
belt-squeal diagnosis carries no CVT content, and the corpus row that
would explain the Fiddle's own belt-and-roller maintenance (257's
census source for the Fiddle III) never reaches them.

Not fixed in 258: a gate writes no production code. What would close it:
add `fiddle 50` to the Fiddle entry's spellings in `TRANSMISSION_LOOKUP`
— one line, evidenced by the same SYM Fiddle III owner's manual the
entry cites (a combined "Drive belt/roller I R" maintenance row) — with a
test that the machine resolves `model-sourced`/`cvt`. Pinned by
`tests/test_phase258_gate14.py`, written to fail when this closes.

### F155

**Symptom relevance does not stem plurals, and it can displace a machine's own tier-0 row for a tier-2 row that shares one symptom word**

`knowledge/prompt_rows.py::relevance_tokens` tokenises on whitespace and
punctuation with no plural handling, and `relevance_score` counts shared
raw tokens. Measured in Phase 258's Step 0: the symptom "scooter jerks
at low speed, belt squeal, won't pull away" tokenises to
`{away, belt, jerks, pull, scooter, speed, squeal}`; the Vespa LX 50's
tier-0 carburettor row — titled "Vespa's small carburetted **scooters**:
Dell'Orto on the two-stroke 50s…" — scores **0** ("scooter" ≠
"scooters"), while a tier-2 CVT row sharing the word "belt" scores 1 and
takes a reserved slot. With the symptom, the LX 50's prompt loses its
carburettor row (CVT 10, ELEC 1, CARB 0); without it, the prompt holds
all three layers.

What it affects: 250B's composition reserves four slots for what the
rider reported, and the ranking that fills them ranks a tier-2 row above
the machine's own tier-0 row whenever the symptom words miss by a
plural. Any corpus row whose title pluralises the machine class
("scooters", "twins", "singles") is invisible to a symptom that uses the
singular.

Not fixed in 258: a gate writes no production code, and 250B's choice to
let symptom relevance outrank tier is a design decision, not a defect —
the defect is the tokeniser's plural blindness making the ranking wrong
about what the rider reported. What would close it: stem plurals in
`relevance_tokens` (or score title+description, which for that row does
contain the singular), with the LX 50 displacement as the regression:
a belt-shaped symptom must not cost a machine its own tier-0 row.
Pinned by `tests/test_phase258_gate14.py`.

### F156

**A 2002–2006 Metropolitan is a CHF50, but the query "Metropolitan" reaches none of the CHF50 rows — and reaches the CVT recall rows at tier 0**

Phase 252 measured that the Metropolitan and the Ruckus are Honda's two
50 cm3 scooters and that the 2002–2006 Metropolitan is the CHF50 (F152's
cover: "CHF50/P/S METROPOLITAN™, 2002–2006"); 354 and 353 model their
CHF50 rows `CHF50` only. Measured in Phase 258's Step 0: `(Honda,
Metropolitan)` holds 0 junction pairs on the CHF50 carburettor and
electrical rows, while the CVT multi-make rows — which list "Honda
Metropolitan" — do pair it. A 2005 Metropolitan query therefore reaches
CVT regulator-record rows at tier 0, the three unverified F149 charging
rows at tier 1, and **none** of the carburettor or charging rows written
for the machine the owner has. The current fuel-injected NCW50
Metropolitan correctly reaches nothing (354's modelling, F152); the
2005 case is the gap.

What it affects: every owner who typed their scooter's name as Honda
printed it on the machine, for the four years the name and the model code
were the same bike.

Not fixed in 258: a gate writes no content, and bridging a name to a
model code is a content decision with a year dimension (the bridge must
not carry the injected NCW50 forward). What would close it: junction
pairs or model-column spellings for the 2002–2006 window, with a test
that a 2005 Metropolitan reaches the CHF50 carburettor row at tier 0
and a 2018 Metropolitan does not. Pinned by
`tests/test_phase258_gate14.py`.

### F157

**No adapter compatibility row exists for any scooter make; a Honda scooter's only answer is the make-level dev/test mock, while the corpus documents scooter diagnostic surfaces**

`compat_matrix.json` holds eleven makes — aprilia, bmw, ducati, harley,
honda, kawasaki, ktm, mv-agusta, suzuki, triumph, yamaha — and no row
names a scooter. Measured in Phase 258's Step 0 on a seeded catalogue
(the first pass measured against an unseeded store and said "none known"
for every machine; this corrects it): `hardware compat recommend` answers
"No compat entries known for this bike" for the Kymco Agility 50, SYM
Jet Euro 50, Piaggio Fly 50, Vespa LX 50, Yamaha Zuma 125 and Genuine
Buddy 125 — Yamaha's ten rows are model-scoped to its big bikes — while
a Honda scooter (Ruckus, CHF50) inherits the make-level **"Mock Adapter
(dev/test only)"**, because Honda's 13 rows carry no model. Track M's own
rows document diagnostic surfaces: 251's six-pin Piaggio connector row
("Piaggio calls it the OBD port, but it is a six-pin Piaggio connector"),
253's "Kymco and SYM do show fault codes on the dash — under names no
standard diagnostic…" — so the gate cannot assert an adapter per scooter
make the way Gate 12 could per European make.

What it affects: a scooter shop asking the product which scan tool reads
a customer's machine gets a dev/test mock (Honda) or "none known" (every
other make) for every machine Track M covered — honest, but it is also
the whole of the track's hardware answer.

Not fixed in 258: a gate writes no production code, and which adapters
actually read these machines is a sourcing question, not a guess to
write down. What would close it: compat rows sourced from adapter
vendors' coverage lists for at least the makes with documented diagnostic
surfaces (Piaggio/Vespa, Kymco, SYM), with the gate's honest-gap tests
failing the day they land. Pinned by `tests/test_phase258_gate14.py`, the
same shape as Gate 13's F99 for electric makes.

### F158 — fixed set CLOSED by migration 072 (Phase 359, live 2026-09-27); open for the wording its patterns do not match

**Text the product shows users carries internal build references: 34 "Phase N" / "Track N" mentions in 25 rendered rows, 23 of them known issues**

Measured on 2026-09-24 by the Opus session, on a copy of the live
database (schema 66, 1,060 `known_issues` rows). The census read every
text column of every table with the three patterns the operator gave:
`\bPhase \d+`, `\bTrack [A-Z]\b` and `\bF\d{2,3}\b`. The positive control
planted "Phase 999" in one `known_issues.description` on a second copy,
and the census found it exactly once, in that row.

| rendered column | pattern | hits | rows |
|---|---|---|---|
| `known_issues.description` and `.fix_procedure` | Phase N | 32 (23 + 9) | 23 |
| `workflow_templates.description` | Track N | 2 | 2 |
| **total** | | **34** | **25** |

- **The rows.** `known_issues` 252, 266, 713, 714, 859, 885, 892, 893,
  894, 898, 899, 901, 902, 903, 904, 905, 1284, 1288, 1332, 1475, 5339,
  5340 and 5343; `workflow_templates` 1 (`generic_ppi_v1`) and 2
  (`generic_winterization_v1`).
- **The tokens.** Phase 238 ×6; 237 ×5; 225/225B ×4; 234 ×3; 233, 236
  and 254 ×2; 212, 215, 231, 240, 247, 253, 31 and 33 ×1; Track N ×2.
- **Examples:**
  - "the reduced-magnet flywheel that Phase 237 names as the first
    suspect" (#899);
  - "Read blink code (see Phase 33 issue #1 for procedure)" (#266);
  - "Track N phase 264 expands." (the winterization template).
- **The F-number pattern finds no finding numbers in rendered text.** All
  7 of its rendered hits are BMW model names: F650, F700, F750, F800,
  F850 and F900.
- **Outside the rendered columns:** `customer_notifications.body` (4) and
  `shops.name` (1), both user data, and 24 BMW model names in the model
  columns.

**Where they come from:**
- 13 seed files in `src/motodiag/knowledge/seed/knowledge/`, led by
  `known_issues_european_parts.json` (9), `known_issues_european_intervals.json`
  (7), `known_issues_ktm_adventure.json` (4) and
  `known_issues_scooter_electrical.json` (3);
- the two templates' seed in `migrations.py`, the Phase 114 substrate.

**The census's limits, stated so its count is not over-read:**
- The patterns miss prose without a number. 9 `known_issues` rows say
  "this phase".
- Three data files the app may read without passing through the database
  also carry the patterns: `advanced/data/parts.json` (10),
  `hardware/compat_data/adapters.json` (3) and `compat_matrix.json` (1).
  Whether those fields are rendered was not checked.

**What it affects.** A rider or mechanic reading a description or a fix
procedure, in the CLI, the API or the app, meets "corrected at Phase
238" or "see Phase 33 issue #1". Those are references to this project's
build history that they cannot follow. Two procedures (#252, #266) point
at another entry by phase number instead of by name.

**Not fixed in 259**, by the operator's decision on 2026-09-24. 259's own
re-pointed description was written without phase numbers. The 34
existing references are left for a repair phase.

**Proposed guard test** (not written): `tests/test_rendered_text_has_no_build_references.py`.
- **What it reads.** A freshly initialised and seeded database, so it
  checks what ships rather than the live state. It reads every rendered
  column:
  - `known_issues`: title, description, symptoms, causes,
    fix_procedure, parts_needed;
  - `checklist_items`: all its text;
  - `workflow_templates`: name and description;
  - `dtc_codes`, `dtc_category_meta`, `symptoms`,
    `technical_service_bulletins`, `parts` and `translations`;
  - `permissions` and `roles` descriptions.

  It also reads the seed and data JSON for the same fields.
- **What fails it:** `\bPhase \d+` (any case), `\bTrack [A-Z]\b`, "this
  phase", and `\bF\d{2,3}\b` except for an explicit allowlist of the six
  BMW model names, each marked as a model.
- **Controls.** A planted "Phase 999" in a scratch copy must be caught,
  and a BMW F800 row must not be.
- **When it lands.** It is red on landing, with 34 known offenders. It
  can land with the repair phase, or land now as a ratchet: the 25 known
  rows go in a frozen list that may only shrink, so new content is
  guarded from the start.

**Re-measured after 259's deploy (2026-09-25, schema 67).** Still **34
hits in 25 rendered rows**, but not the same ones:
- **Gone:** `generic_ppi_v1`'s "Track N phase 259 expands", rewritten
  under the operator's option 1.
- **New:** "the chassis protocol is Phase 260", in 259's own new template
  (`ppi_engine_v1`'s description, `workflow_templates` #3). The Opus
  review missed it: option 1 was applied to the rewritten description,
  and the same phrase in the new template's text was not checked until
  `motodiag workflow show` printed it live.

The seven new checklist items carry none. This is the case the proposed
guard exists for: without the check, new content brings references in
at the same rate old ones are cleaned out.

**Fixed set closed 2026-09-27 by Phase 359's migration 072, applied live
under the operator's scoped approval.** Phase 358 had landed the guard as
a ratchet (`scripts/f158_census.py`, `F158_CEILING` 75).
- **The fixed set:** every "Phase N", "Track X" and "this phase" hit in a
  table the seed or a migration writes. That is 44 hits in 25 seed rows,
  and 43 in 24 live rows (`359_step0.md`, S0-5). The two starter
  templates' references went with their retirement.
- **All are removed, from the seed and from live.** A seed build's census
  is 75 → **31**, and each of the 31 is a BMW F-series model name
  (F650–F900 in a BMW row), which the exclusion rule
  (`f158_census.build_references`, with controls) keeps as content.
  `F158_CEILING` is 31. On live the census is 79 → **36**: the 31, plus 5
  hits in shop data (`shops.name` 1, `customer_notifications.body` 4),
  which are user data and were not edited.
- **Measured on live `known_issues` after 072,** over title, description,
  symptoms, causes, fix_procedure and parts_needed, against the pre-359
  backup: "Phase N" 32 → 0, "this phase" 11 → 0.

**Still open.** Internal wording the four patterns do not match, counted
on live `known_issues` in the same columns:
- "this project": 13 hits in 10 rows;
- "corpus": 30 in 23;
- "census": 6 in 4;
- "refut…": 4 in 4;
- "this file": 2 in 2.

One "corpus" hit is 4615's "corpus-wide", which is F171. The three data
files named above (`advanced/data/parts.json`,
`hardware/compat_data/adapters.json` and `compat_matrix.json`) were
outside 359's scope, and whether they are rendered is still not checked.
What would close the rest: a wording pass over those rows and a decision
on each data file. Each is refuted as its own diff, with the census
widened to the words it removes.

### F159 — CLOSED by migration 072 (Phase 359, live 2026-09-27), as retired

**`generic_ppi_v1`'s starter "Brake and tire condition" item carries uncited figures the library's documents contradict or do not support**

Migration 007's seed (the Phase 114 substrate) puts figures in
user-visible checklist text that no held document supports — the exact
defect class F149 documented for corpus rows, now on the workflow
screen, one `motodiag workflow show generic_ppi_v1` away from the
rider:

> "Measure pad thickness, rotor thickness, tire tread depth, DOT date."
> Pass: "Pads >3mm, rotors >min spec, tires <5 years old, adequate tread"

Measured in Phase 260's Step 0 against the library:

- **"Pads >3mm" is nobody's number.** The BMW F800R owner's manual
  (pp. 94–95) sets its pad wear limit at a minimum **1.0 mm** of
  friction pad only, without backing plate, with the wear-indicator
  grooves still visible; the CHF50 service manual gives its brake-shoe
  linings a **1.0 mm** service limit (p. 243). No document in the
  library states 3 mm for any pad.
- **"tires <5 years old" happens to match KTM's recommendation** —
  changed "after 5 years at the latest, regardless of the actual state of
  wear" (KTM 250/300 EXC TPI OM, p. 116) — but the item cites nothing,
  so the one right number it carries is right by coincidence, and
  presented as a universal when the library's figures are per-manual
  (CHF50 tread 0.8 mm service limit, KTM minimum 2 mm).
- The item's five siblings carry no figures; the other Phase-114
  workflow items are clean.

What it affects: a buyer or mechanic told "pads >3mm" fails healthy
brakes (the F800R's own grooves say 1.0 mm is fine) or, worse, accepts
pads a worn machine's manual would condemn, and the "5 years" line is
uncited where the same screen's new chassis protocol
(`ppi_chassis_v1`, 260) shows what a cited figure looks like.

Not fixed in 260: the item is the substrate's seed content, not the
phase's, and its row is the migration journal's — the fix is not a
content edit but a sourcing decision (whose figures, if anyone's, does a
*generic* PPI carry?) plus a migration keyed on the old text, per F129's
shape. What would close it: either source the starter item's figures to
documents and scope them per-machine, or replace the numbers with the
deferral pattern 260's items use (name the check, defer the figure to
the machine's own manual), by migration, with a pin that no uncited
figure returns.

**Closed 2026-09-27 by Phase 359's migration 072, applied live under the
operator's scoped approval, by retirement:**
- `generic_ppi_v1` is inactive, so `workflow list` does not print it.
- `workflow show generic_ppi_v1` prints only its retirement line, naming
  `ppi_chassis_v1` and `ppi_engine_v1`, and exits 1.
- No active template names it; Gate 15's link rule holds that.

The item's rows are kept, inactive, as history. The rollback restores
them. `tests/test_phase359_content_cleanup.py` pins the retirement.

### F160 — CLOSED by migration 070 (Phase 264, live 2026-09-26)

**`ppi_chassis_v1` names the Yamaha YW125Y service manual "Zuma 125", a name that document does not carry**

Migration 068's seeded text (the chassis pre-purchase protocol, live
since 2026-09-25) cites `pdf/yamaha_zuma125_2009_sm.pdf` as the "Yamaha
Zuma 125 2009 service manual" and "the Zuma 125" in 9 places across the
steering, fork and wheel items. The document's title page reads "2009
MOTORCYCLE SERVICE MANUAL Model : YW125Y", and a whitespace-proof search
finds "Zuma" on **0 of its 338 pages**. The market name comes from the
file name and outside knowledge, which is the failure the title-page rule
exists for (354's Symply/Zuma, 353's Fiddle III). The figures themselves
are the document's own and were kept by 260's refute pass. Found by
Phase 261's refute pass, whose new templates name the machine YW125Y and
carry a test that no "Zuma" appears in their text. Not fixed there: the
text is in live rows, and changing live rows is a rule-1 stop. What would
close it: a migration that re-points the nine mentions to the document's
own name, with the operator's approval for the live row change, and a
pin like `test_machines_are_named_as_their_documents_name_them` over
`ppi_chassis_v1`.

**Closed 2026-09-26 by Phase 264's migration 070, applied live under the
operator's scoped approval.** The live count was 8 mentions in 3 items
(ids 18, 19, 21). The ninth mention is in migration 068's Python
description, which is never seeded. All 8 now read "YW125Y", and
`test_no_zuma_in_any_workflow_row` and 260's moved pin keep the word
out. Two further defects the refuter found in the same item are F162.

### F161 — CLOSED by migration 071 (Phase 262, live 2026-09-26)

**`generic_winterization_v1`'s starter items carry storage figures the library's documents do not support**

Migration 007's seed (the Phase 114 substrate) puts three figures in
user-visible checklist text that no maker's document supports. It is
F159's defect class, on the winterization screen. Measured in Phase
264's Step 0 (`264_step0.md`, N6), whitespace-proof over the 260-PDF
library:

- **"Change engine oil and filter with recommended winter weight
  (typically 10W-40)."** No storage procedure in the library names an
  oil grade. Storage or laying-up within 300 characters of SAE, xW-y or
  viscosity finds 12 pages in 8 files, every one an under-seat "storage
  compartment". The control, `10w-40`, hits the Honda CHF50 service
  manual p. 58, a specification table.
- **"Battery on tender, reading float voltage (13.2V-13.6V)."** No
  document in the library gives a float-charge voltage. Of the 19 pages
  with 13.2–13.6 V, the figures are:
  - a fully charged battery's resting voltage at 20 °C, 13.0–13.2 V
    (Honda PCX150 (2013–2017) service manual p. 394, Kymco People /
    People S 250 service manual p. 213, the SYM service manuals);
  - a headlight control voltage, 12.6–13.6 V (SYM);
  - bulb ratings.

  A battery on a charger is not at its resting voltage. The makers'
  storage figures are different ones: BMW's gel battery on a charger limited to 14.4 V (R 850
  R / R 1150 R Maintenance Instructions p. 48), and Piaggio's 12.60 V
  open-circuit check before a stored battery is refitted (Beverly 125
  service station manual p. 78).
- **"Run engine 5 minutes to circulate", stated as universal.** It is
  Yamaha's step, with stabilized fuel, before long-term storage
  (XVS95CL owner's manual p. 81). The KTM 690 Enduro 2010 owner's manual
  stores with the tank as empty as possible (p. 172), and the Kymco People
  S owner's manual empties it (p. 60).

What it affects: `motodiag workflow show generic_winterization_v1`
shows those figures uncited, and they are presented as universal. The
same screen's `winterization_v1` (Phase 264) gives each maker's own
figure with its page.

Not fixed in 264: the operator scoped 264's live change to the
description's build reference, and rewriting the four items is a
live-row change of its own (rule 1). What would close it is the F159
shape: a migration keyed on the old text that either cites the figures
per machine or defers them to `winterization_v1`, with a pin that no
uncited figure returns.

### F162 — CLOSED by migration 071 (Phase 262, live 2026-09-26)

**`ppi_chassis_v1`'s steering item misreads the YW125Y service manual's p. 93, and one KTM citation cannot tell its manual apart**

Found by Phase 264's valve refuter while it checked F160's re-pointed
chassis text, and outside that change's scope, which was the name only:

- **Steering head bearings, instruction_text:** "the YW125Y service
  manual calls the same movement binding or looseness (PDF p. 93)". On
  p. 93, binding or looseness is the fault the check finds, not the name
  of the movement. The sentence should say that the manual checks for
  binding or looseness.
- **The "KTM 250/300 EXC owner's manual (PDF p. 76)" citation** in the
  same item: the library holds two KTM EXC owner's manuals, the 2022
  250/300 EXC TPI (`acquired/KTM/22_3214421_en_OM.pdf`) and the 2027 250
  XC-W / 300 EXC (`acquired/KTM/27_3240387_en_BA.pdf`), and the sentence
  is on p. 76 of both. The text should name the one it means, as 261's
  templates do ("KTM 2022 250/300 EXC TPI").

What it affects: one sentence of live text on the chassis pre-purchase
screen reads the Yamaha page loosely, and one citation is ambiguous.
Neither changes a figure. What would close it: a migration keyed on the
old text that rewords both, with the operator's approval for the
live-row change (rule 1).

### F163 — CLOSED by migration 072 (Phase 359, live 2026-09-27): the starter part retired, the chassis sentences deleted

**Live starter and chassis text keeps defects outside F161's and F162's scope: an unsourced title, two unsourced steps, a fail criterion one maker prescribes, and three unsupported steering-bearing sentences**

Found by Phase 262's round-1 refuters (`262_phase_log.md`, Refuter
pass) while they read F161's and F162's fixes. The operator scoped those
fixes to the unsupported figures (F161) and the two named defects (F162),
so these were recorded, not changed.

`generic_winterization_v1` (migration 007's starter), untouched by 262:
- **Item 1's title, "Add fuel stabilizer",** contradicts the makers who
  empty the tank: "Make sure the tank is as empty as possible" (KTM 2010
  690 Enduro OM p. 172); "empty the fuel tank into an approved gasoline
  container" (Kymco People S OM p. 60). The item's own instruction, since
  262, allows an empty tank.
- **Item 3's instruction, "Disconnect negative terminal, clean terminals,
  connect battery tender",** joins what the makers give as alternatives:
  "disconnect the battery or connect a suitable trickle charger" (BMW F
  800 R RM p. 117). No storage page checked says to clean the terminals.
- **Item 3's expected_fail, "Battery left disconnected with no
  maintenance",** is what the Honda CB500F/FA 2018 OM prescribes when the
  battery stays in: "If you leave the battery in place, disconnect the
  negative - terminal to prevent discharge" (p. 117). Since 262 the same
  item's expected_pass allows it.
- **Item 2's "Change engine oil and filter", stated as every machine's
  storage step, and its expected_pass "Fresh oil and filter":** the Honda
  CB500F/FA 2018 OM (p. 117) and Yamaha XVS95CL OM (p. 81) storage lists
  name no oil change, and the KTM 2022 250/300 EXC TPI, a two-stroke,
  changes the gear oil (p. 154). 262 removed the figure and points to
  `winterization_v1`, whose item 4 gives each maker's step; two attempts
  to list the makers in the starter text itself were each wrong once
  (262's refute rounds 1 and 2).
- **Item 4's "centerstand/jackstand to unload suspension":** every maker
  checked lifts the machine to take the load off both tires (Yamaha
  XVS95CL OM p. 81; BMW F 800 R RM p. 124; Honda CB500F/FA OM p. 117;
  Kymco People S OM p. 60). None mentions the suspension.

`ppi_chassis_v1`, "Steering head bearings" (live id 18), outside F162's
two sentences:
- "A notch at the straight-ahead position is dented bearing races",
  "freshly adjusted but unchanged bearings only hide the notch until the
  grease settles", and the diagnosis's "brinelled races from an impact
  or years of load in one position" have no support. "brinell" is on 0
  of the library's 26,228 pages, and the 16 notch/detent pages support
  none of them. The KTM 2022 250/300 EXC TPI OM adjusts first: "If detent
  positions are detected: – Adjust the steering head bearing play. –
  Check the steering head bearing and change if necessary" (p. 76). The
  nearest support names recessed seats or flattened balls only after
  adjustment fails, with no cause (Piaggio Beverly 125 SSM p. 56).

What it affects: `motodiag workflow show generic_winterization_v1` and
`… show ppi_chassis_v1` print these sentences uncited or contradicted.
A replacement for each is drafted, with its page quote, in
`262_phase_log.md` (Refuter pass, round 1, "Outside the scope: F163").
What would close it: a migration keyed on the old text, with the
operator's approval for the live-row change (rule 1).

**Closed 2026-09-27 by Phase 359's migration 072, applied live under the
operator's scoped approval.**
- **The starter part is closed by retirement.** `generic_winterization_v1`
  is inactive. `workflow show` prints only its retirement line, naming
  `winterization_v1`, and exits 1.
- **The chassis part is closed by deletion.** In `ppi_chassis_v1` item 2
  (live id 18), the notch sentence, "freshly adjusted … grease settles"
  and the "brinelled races" clause are gone. The diagnosis now follows the
  KTM 2022 250/300 EXC TPI OM p. 76: adjust the play, then check the
  bearing and change it if necessary.

The refute's remaining wording defect in that item, "Rocking play is loose
adjustment", is F171.

### F164

**`crash_support_v1` item 7 ships without the sentence on where "insurance" appears besides the papers: it was still unresolved after the operator's last refute round, and was dropped**

Phase 262 wrote, in item 7's diagnosis, where the library's
"insurance" pages point besides "where to keep the insurance papers":
KTM's note on switching the ABS off, EPA's warranty sentence, and the
California DMV's total-loss pages. The sentence was reworded in refute
rounds 1–4, and each rewrite was refuted. Round 5, the last under the
operator's stopping rule, killed "warnings": KTM prints the passage as a
"Note", which its own key defines apart from a "Warning", and on p. 183 a
separate Warning box follows it (KTM 2019 1090 Adventure R OM pp. 15,
183; the same note in the KTM 2019 690 Duke OM p. 54). EPA's line sits
under "WARRANTY ISSUES" (fact sheet, March 2020, p. 2). Under the
operator's rule the sentence was dropped from migration 071, not
shipped.

What ships in its place: "Where its owner's manuals say "insurance"
they mostly say where to keep the insurance papers" — kept by round 5,
25 of 28 owner's-manual pages.

The last proposed wording, which no refuter has read, is in
`262_phase_log.md` (Round 5). What would close it: that wording, or
another, through one adversarial read that kills nothing, then a
migration keyed on item 7's text. The live change of a shipped row
would be a rule-1 stop.

### F165 — CLOSED by Phase 357 (migration 073, live 2026-09-28): a run and its per-item results are saved and read back

**No workflow can be run: the workflow door only lists and shows templates, and nothing records a run or an item's result**

Found by Phase 272 (Gate 15) at Step 0 (`272_step0.md`, S0-1), measured
2026-09-26 at schema 71. ROADMAP row 272 read "Run PPI → tire service →
winterization → valve adjust → brake service end-to-end", and nothing in
the tree can do that:
- `motodiag workflow` has two commands: `list` (one option,
  `--category`) and `show <slug>`.
- No table stores a run or an item's result. Of 89 tables, the four
  whose names hold run, result, workflow, checklist, step or inspection
  are `workflow_templates`, `checklist_items`, `workflow_rules` and
  `workflow_rule_runs`; the last is Phase 173's shop rules (`rule_id`,
  `work_order_id`, `triggered_event`, `matched`), not a template run.
- Phase 82's step engine (`DiagnosticWorkflow`,
  `src/motodiag/engine/workflows.py`) is not connected to the templates.
  It imports nothing from `motodiag.workflows`; the 4 files that name
  the template tables are `core/migrations.py`, `workflows/__init__.py`,
  `workflows/template_repo.py` and `cli/workflow.py`.
- Powertrain applicability is per template (`applicable_powertrains`).
  `checklist_items` has no powertrain column, so a run would have to
  choose one.
- The CLI is the only door. The API's one "workflow" is Phase 173's shop
  rules (`api/errors.py` imports `shop.workflow_*`). In
  `../moto-diag-mobile/src`, 0 files mention workflow or checklist,
  against 34 that mention vehicle or garage.

What it affects: every one of the 15 seeded templates (100 items) can be
read, not worked through. A mechanic cannot record which items passed.
Gate 15's row was corrected to what the door does (walk through `list`
and `show`, per powertrain, with every template link resolving).

What would close it, as the operator scoped it on 2026-09-26: **row 356**,
an in-memory runner (`motodiag workflow run <slug>` over Phase 82's step
engine, pass or fail per item, a printed summary, nothing saved, no
schema change); then **row 357**, saved runs, with its own migration for
runs and per-item results tied to a bike or work order.

**Phase 356 (closed 2026-09-28) met the first half and not the second.**
`motodiag workflow run <slug>` works a template's checklist through the
step engine, one item at a time, with pass, fail or skip per item and a
printed summary. Nothing records the run or an item's result: the answers
end with the terminal session, by the row's scope. So F165 stays open
until row 357 saves a run and its per-item results.

**Closed by Phase 357 (2026-09-28).** Migration 073 adds
`workflow_runs` (tied to a bike always, and optionally a work order) and
`workflow_run_items` (one row per checklist item, with its result, notes
and the diagnosis printed at a fail). `motodiag workflow start`, `record`,
`resume`, `finish`, `runs` and `report` save a run as it is worked and
read it back. The proof is
`tests/test_phase357_saved_runs.py::TestF165::test_a_run_and_its_results_are_saved_and_read_back`:
a run started on a bike, every answer given, the rows read back with
plain SQL and through `report`. Live at schema 73; the live diff equals
the approved exact diff.

### F166 — CLOSED by migration 072 (Phase 359, live 2026-09-27), as retired

**`generic_ppi_v1` covers electric machines but requires an engine compression test, and asks every machine for its engine oil**

Found by Phase 272 (Gate 15) at Step 0 (`272_step0.md`, S0-4),
measured 2026-09-26 at schema 71. `generic_ppi_v1` (migration 007's
starter) prints "for ice, electric, hybrid". Its item 3, **"Engine
compression test"**, is required (`required = 1`): "Warm engine,
remove spark plug, crank and read compression gauge. Repeat all
cylinders." An electric machine has no engine, spark plug or cylinder,
so the electric pre-purchase walk prints a required step it cannot do.

Every other template that covers powertrains with and without an engine
carries its engine-only steps as optional: `winterization_v1` items 2, 3
and 4 and `de_winterization_v1` item 4, and, the other way round, the
traction-battery items (`winterization_v1` 6, `de_winterization_v1` 3).
Over every item title, with the engine and traction-battery vocabularies
in S0-4, this is the only required step whose title names work a
powertrain the template covers does not have.

Beside it, outside the title rule: item 4, "Fluid inspection" (also
required), says "Check oil color/level, coolant color/level" for every
machine. The gate's rule does not catch it, since its title names no
engine work.

What it affects: `motodiag workflow show generic_ppi_v1`, on the
electric walk of Gate 15. The gate pins item 3 as its rule's one
measured exception (`tests/test_phase272_gate15.py`), so the gate fails
the day it is fixed and must be updated with it. What would close it: a
migration making item 3 optional with an engine-only condition in its
text (or narrowing the template's powertrains), and item 4's oil check
conditioned the same way. The change to a live row is a rule-1 stop.

**Closed 2026-09-27 by Phase 359's migration 072, applied live under the
operator's scoped approval, by retirement.**
- `generic_ppi_v1` is inactive, and `workflow show` refuses it.
- Gate 15 no longer walks it, and W4's exception set is ∅, so the gate
  now allows no required engine step on an electric walk.
- The electric pre-purchase walk is `ppi_chassis_v1`, since
  `ppi_engine_v1` covers ICE and hybrid only.

### F167

**The whole-tree record's signing key is readable by every process the `lilquant` account runs, so an agent can sign a "passed" record without running the checks**

Found by Phase 358 (K1), measured 2026-09-27 (`358_phase_log.md`, "The
operator's question on the signing key, answered"). `wholetree.sh` signs
each record with HMAC-SHA256 under
`/Users/lilquant/.config/motodiag/wholetree.key` (owner `lilquant`, mode
600, 64 bytes). The key's mode stops other accounts. It does not stop
this one, and every Claude Code session, subagent, script and `claude -p`
run as `lilquant`. `test -r` succeeded from the building session. Whether
the GLM sandbox profile blocks reading `~/.config` was not measured.

What it affects: the push guard accepts any record whose signature
verifies. So a record forged *with* the key lets a push through with no
check run. Phase 358's hand-written-record control covered a forgery
*without* the key. The record proves "written by something holding the
key", not "written by `wholetree.sh` after a passing run". The operator
chose to state this as a known limit, not to fix it in 358. What would
close it: a key the agent's account cannot read. Examples: an OS keychain
item gated by user presence, a separate account that runs the command, or
recording the run somewhere the agent cannot write.

### F168

**The push guard sees only pushes made through Claude Code's Bash tool; a push from a terminal is never checked**

Found by Phase 358 (K1). The guard is a `PreToolUse` hook
(`.claude/settings.json` → `pre_push_guard.sh`), not a git hook. A
`git push` typed in a terminal, run by an IDE, or run by any tool other
than Claude Code's Bash tool reaches the remote with no whole-tree check,
no ROADMAP check and no close-out check.

What it affects: every guarantee the guard gives (358's whole-tree
record, R1–R7, the close-out contract on master) holds only for pushes an
agent makes through Bash. The contract tests still run with the suite, so
a red check surfaces at the next regression, but not at the push. What
would close it: a git `pre-push` hook (or a server-side check) calling
the same functions. It would need its own lockout-safety design, since a
git hook cannot be edited around with the Write tool the way
`settings.json` can.

### F169

**The push guard judges every `git push` against moto-diag's own checkout, whichever repository the push is in**

Found by Phase 358, seen live on 2026-09-27. The guard resolves the
pushed commits and records in the repository it lives in (`HERE.parents[2]`),
not in the directory the push runs in. The workspace-docs push of `4a5ca20`
(12:33) was logged as "push 63494b7ca4cb: accepted fast record", the
record of moto-diag's HEAD. That makes two errors possible:
- a push in another repository is **blocked** for moto-diag's state (a
  dirty moto-diag tree, or no record);
- it is **let through** on moto-diag's record, although nothing about the
  other repository was checked.

What it affects: pushes of workspace-docs and moto-diag-mobile made from a
session started at moto-diag's root. What would close it: resolve the
push's repository from the command (`cd`, `git -C`) and gate only
moto-diag's pushes, letting others through unjudged. That is a change to
what the guard guards, so the scope is the operator's call.

### F170

**Known issue 902 (Triumph idle-valve hoses) applies owner reports about the Sagem-managed T595 and 955i to the Street Triple 675, and nothing on disk says the 675 is Sagem-managed**

Found by Phase 359's refute round 2 (`359_phase_log.md`, Refuter pass),
2026-09-27. Row 902's model reads "Street Triple 675 2007–2016; the same
layout on other Sagem-era triples". Its title names the Street Triple.
Since 359 its description reads "Owner reports say warm high idle on the
Sagem-era triples is usually the rubber hoses from the idle air control
valve to the intake ports perishing, not the valve". 359 made that one
change: the claim had read as if the parts fiche said it, and it now names
its source.

That source is the entry "Triumph 955i warm high idle or stalling is
usually an air leak at the idle valve hoses, not the stepper" ("Drawn from
owner reports on Triumph forums"). It covers the T595 and 955i (Sagem,
1997–2010) and the 1050 Speed Triple, not the Street Triple 675.

A search of the seed data for "sagem" or "keihin" within reach of "675",
"Street Triple" or "Daytona" found only row 902 itself. So no document on
disk says which engine management the 675 uses. The refuter recalled,
without a source, that the 675 platform used Keihin management.

What it affects: `motodiag kb show` for row 902. A Street Triple 675 owner
is told a Sagem-era failure is "usually" theirs.

Not fixed in 359: the scope was build references and the lagging rows, and
the question needs a document. What would close it: a Triumph document for
the Street Triple 675's engine management, and then either narrowing row
902's model and wording to the machines the owner reports cover, or
sourcing the claim for the 675.

### F171

**Two wording defects left open by Phase 359's refute: "Rocking play is loose adjustment" (ppi_chassis_v1 item 2), and "a corpus-wide sweep" (known issue 4615)**

Phase 359's refute pass ran its three rounds (`359_phase_log.md`, Refuter
pass). Under the operator's rule (Phase 358, K9), a wording defect left
after round 3 goes to one finding, and this is that finding. Neither is a
factual or citation defect.

- **`ppi_chassis_v1` item 2's diagnosis**, killed as wording in round 3:
  it opens "Rocking play is loose adjustment; …". The page cited
  beside it, the KTM 2022 250/300 EXC TPI owner's manual, gives only the
  remedy: "If there is detectable play: – Adjust the steering head bearing
  play." (PDF p. 76). It names no cause. The fix is to delete "is loose
  adjustment", but a fourth round is not allowed. Round 2 had already
  deleted "or worn bearings" from the same sentence.
- **Known issue 4615's fix_procedure**, killed as wording in round 1:
  "conclude only that a corpus-wide sweep found one". "Corpus" is this
  project's word for its own knowledge base. The text is Phase 255B's seed,
  which 072 carries to live unchanged, because the operator's condition for
  4615 was that it change "only to its seed text". The fix is to delete
  "corpus-wide " in the seed and the live row together.

What it affects: `motodiag workflow show ppi_chassis_v1` and `motodiag kb
show` for the CVT regulator row. What would close it: the two deletions,
in the next content migration, refuted as their own diff.

### F172 — CLOSED by Phase 357 (2026-09-28): apply-live compares a fresh dry run with the approved exact diff

**`deploy.py apply-live` does not compare its fresh dry run with the committed diff the operator approved; it checks only that the fresh run stays inside the scope**

Named open by Phase 359's handoff (`docs/handoffs/2026-09-27_359_closed.md`,
"What is open"), filed by Phase 356 on 2026-09-27. In
`.claude/skills/deploy/deploy.py`, `preflight()` refuses when the diff file
is missing, uncommitted or changed, when it records a scope problem, when
the backup or scope file no longer hashes as recorded, and when live has
drifted from the backup. Its last check migrates a fresh copy and passes
it to `check_scope()`. Nothing compares that fresh diff with the rows and
fields in `<phase>_dryrun_diff.md`. A migration edited after the dry run,
whose new changes still fall inside the scope's tables, counts and named
fields, would be applied without a refusal.

What it affects: every live apply. The operator's approval of migration
072 asked for exactness ("stop if the fresh dry run differs in any row or
field"). 359 met that by hand, running the same computation with
`deploy.py`'s functions before live was touched and comparing it with the
committed diff: identical except for five clock values. The skill did not
enforce it.

**This is a gap to close before the next live apply, which is Phase 357's
migration.** What would close it: `apply-live` refuses unless the fresh dry
run's diff equals the committed one, with timestamp columns masked as 359
masked them, and a planted edit to a migration's row values is seen red.
Where the fix goes (a K-list item, its own phase, or 357's Step 0) is the
operator's call.

**Closed by Phase 357, before its live apply, as the operator placed it**
("Close F172 before this phase's live apply"). The dry-run file now ends
with the exact diff as JSON: every field of every added and removed row,
before and after of every changed field, and every schema object added or
rewritten. A timestamp within a day of the run's own clock is masked as
`<clock>`; a fixed date is compared. `apply-live` refuses when a fresh dry
run differs in any field, and names each one. The known-bad case, a fresh
run differing in one allowed field, is refused, and the same edit passes
the scope check alone; the good case, differing only in its clock, applies
(`tests/test_phase357_deploy_exact.py`). Six mutations red
(`357_mutate.py F172`). The deploy skill's `CHANGELOG.md` has the rest.

### F173

**`test_phase78_gate2_integration.py::TestGate2KnowledgeBaseIntegration::test_cross_platform_brakes` failed once in a parallel run and has not reproduced**

Recorded by Phase 359 (`docs/phases/completed/359_phase_log.md`, the
first `wholetree.sh --full`), filed by Phase 356 on 2026-09-27. The test
builds a database under `tmp_path`, loads every
`data/knowledge/known_issues_*.json` from `SEED_DATA_DIR`, and asserts that
`search_known_issues(query="brake fluid")` returns at least 5 rows; a seed
build returns 18. In 359's first `--full` (4 failed, 3859 passed) it was
one of the four failures. The other three were pins on text 359 removed.

What 359 recorded:
- its traceback was lost: `wholetree.py` keeps only the last 1500
  characters of pytest's output (`wholetree.py:259`), which cut two of the
  four FAILED lines;
- it passed alone, in a direct run over the same 80 member files, in the
  next two `--full` runs and in the regressions at `953c329`, `9e8e753`
  and `32d281a`;
- nothing in 359's diff touches brake-fluid text; every test that writes
  a known-issue JSON writes it under `tmp_path`; the search is plain SQL.

Phase 356 checked the tests that write near the seed directory (256,
255C, 358's F158 ratchet, 255B, 255): each writes under `tmp_path`. Not
excluded: a `--full` run while the working tree's seed JSON was being
edited. `wholetree.py` records only on a clean tree but will run on a
dirty one, and 359's log does not say whether the tree was clean or
still being edited at that run. If a seed file was rewritten during it,
the count would have been read from a file mid-edit. This is a
hypothesis, not a finding of cause.

Rule 3 says a test that fails only in parallel is a bug to fix. What would
reproduce it:
- run the test repeatedly under `-n auto --dist load` beside the rest of
  the `--full` member set at 359's first-run commit, keeping the junit
  whole (`--junitxml`), until it fails or a stated number of runs pass;
- rerun that set while a seed file is rewritten in place during the run,
  to test the dirty-tree hypothesis;
- `wholetree.py` keeping every FAILED line, so the next occurrence carries
  its traceback.

What would close it: a reproduction and its fix, or a stated run count
with no failure and the truncation fixed so a recurrence is not lost.

### F174 — CLOSED by Phase 360 (2026-09-29)

**Closed.** No path stores a powertrain nobody stated:
- migration 074 (live, schema 74) removed the column's `DEFAULT 'ice'`;
- `VehicleBase.powertrain` defaults to None;
- `garage add` and `garage add-from-photo` ask, and save nothing without
  an answer;
- a vision reply without the key is unknown;
- the API stores NULL when the field is absent;
- `workflow start` stores the stated value on a bike held as unknown.

Every reader's handling of an unknown powertrain is tested
(`tests/test_phase360_powertrain_unknown.py`); 21 mutations each turned a
test red. The app's twin, its `ice` preselect, closed as the mobile repo's
F179 (moto-diag-mobile `57c9e45`). The ten live bikes stay `ice`: all are
petrol models, and no live row changed. `engine_type`'s identical default
is F177.

**`motodiag garage add` stores a bike as `ice` when `--powertrain` is not given, so an electric bike added without the flag is recorded as an engine machine**

Measured by Phase 356's Step 0 (`356_step0.md`, S0-4, option B) and
filed at the operator's request on 2026-09-28. Not fixed in 356. The
default is set in three places, all of them `ice`:
- `garage add`'s `--powertrain` option, `default="ice"`
  (`src/motodiag/cli/main.py:442`);
- `VehicleBase.powertrain`, `Field(PowertrainType.ICE, …)`
  (`src/motodiag/core/models.py:149`);
- the `vehicles.powertrain` column, `TEXT DEFAULT 'ice'`
  (`src/motodiag/core/migrations.py:211`, Phase 110's migration, whose
  description says "Existing rows get ICE/4-stroke defaults"; a
  rollback's rebuilt `vehicles` table at `:2916` carries the same
  default).

So the stored value cannot tell "the mechanic said ice" from "nobody
said". The readers of that value (grep of `src/motodiag` for the
vehicle's `powertrain`):
- **diagnose** (`cli/diagnose.py:466`, `:542`) passes it to
  `_load_known_issues`. There, retrieval gives it to
  `resolve_transmission` (`knowledge/transmission.py`, rung 3: an
  electric machine with no gearbox defaults to `direct_drive`), and
  `prompt_rows` puts electric rows first only when it reads `electric`.
- **the predictor** (`advanced/predictor.py:243`) passes it to
  `rows_for_machine`, as above.
- **the priority scorer** (`shop/priority_scorer.py:321`) reads the same
  column.
- **the safety scoping** (`cli/diagnose.py:721` into `SafetyChecker`,
  `engine/safety.py:398–417`). `None` shows every rule, but `ice` is not
  `None`. Seven rules are scoped `("ice", "hybrid")`, so an electric bike
  stored as ice gets those alerts as well. No rule is hidden by the wrong
  value, since no rule is scoped to electric alone. The checker's
  docstring says "a blank or wrong value must not be able to hide a
  fuel-leak warning", and that still holds.

What it affects: an electric bike added with `garage add` and no
`--powertrain` loses rung 3's `direct_drive` default and the electric-first
ordering, and is scored and alerted as an engine machine. Phase 357's bike
link would inherit the value: a saved run tied to a bike would read `ice`.
The garage's photo path (`garage_add_from_photo`) stores a vision guess
instead and is not affected by this default.

Not measured: how many live garage rows are electric machines stored as
`ice`. That needs a read of the live database, which no phase has
scoped.

What would close it: the operator's choice between two fixes. One is to
require the powertrain at `garage add`, or ask for it when it is missing.
The other is to store unknown (`NULL`), which the readers above already
treat as "show everything". That second fix changes a column default,
which needs a migration. A census of live rows would come with either.

**Amended by Phase 357's Step 0 (2026-09-28): there is a fourth `ice`
default, and the CLI cannot correct a stored value.**
- The API's create request defaults it too:
  `VehicleCreateRequest.powertrain: PowertrainLiteral = "ice"`
  (`src/motodiag/api/routes/vehicles.py:83`). A bike added from the app
  without a powertrain is stored as `ice`.
- `garage update` takes `--mileage`, `--notes` and `--vin`, not
  `--powertrain` (`src/motodiag/cli/main.py:607`). Only the API's update
  (`vehicles.py:104`) can change a stored powertrain.

### F175 — CLOSED by Phase 357 (2026-09-28): a test pinning a whole-tree check's ledger joins `--full` by rule

**The whole-tree command's membership rule misses a test that pins a whole-tree check's ledger without enumerating anything, so `wholetree.sh` in either mode did not run `test_phase244Z_shelved_content.py`**

Found by Phase 356's bug fix #1 (`0130f1a`), filed by Phase 357 at the
operator's request on 2026-09-28. `.claude/skills/closeout/wholetree.py`
counts a test as whole-tree when it enumerates a repo directory, or
imports a helper that does. 244Z does neither. It pins `MODULE_ISLANDS`
and `MODULE_ISLAND_COUNT`, imported from `tests/support/integration_gaps_allowlist.py`
and `integration_gaps_counts.py`. Those two modules hold only data, and
209B keeps them equal to the tree. So 244Z's verdict moves when the tree
does. 356 wired `engine.workflows` and updated the gap tables; 244Z went
red, and only the full regression reached it.

Measured at `b0ff03a`: fast 31 files, `--full` 80. Neither holds 244Z or
`test_phase244Y_delete_pass.py`, the two tests in `tests/` that import
either gap-table module and are not members.

What it affected: a wiring change passed both modes of rule 3's command
and failed only at the regression of record, 23 minutes later.

**Closed by Phase 357.** A new class, `ledger`, `--full` only: a test that
imports a `tests/support` module whose body is only a docstring, imports
and assignments, where a code-class member imports that module too. The
data-only modules are `integration_gaps_allowlist`,
`integration_gaps_counts` and `model_gate_fixtures`. The ledger members
are 244Y and 244Z, found by the rule, not by name.
- Fast mode gains nothing from the rule: 31 files before and after.
- Control: a planted failure in 244Z turned `wholetree.sh --full` red,
  2026-09-28 12:51–12:57: 83 files, `1 failed, 3945 passed`, the failure
  the plant, exit 1. The plant was removed after and 244Z's diff is clean.
- Fixed in `wholetree.py`; `357_mutate.py F175`: 4/4 red.
- The fixture tests (`tests/test_phase357_wholetree_ledger.py`) hold the
  exclusions too: a support module with a function is not a ledger, and
  neither is a data module that no member imports.

### F176

**`motodiag garage remove` on a bike that a work order names ends in an `IntegrityError` traceback instead of a refusal**

Measured by Phase 357's Step 0 on a scratch database at schema 72
(`357_step0.md`, S0-3). `work_orders.vehicle_id` references `vehicles(id)
ON DELETE RESTRICT` (Phase 161's migration). `garage remove`
(`src/motodiag/cli/main.py:525`) calls `delete_vehicle`
(`src/motodiag/vehicles/registry.py:161`), which runs the `DELETE` with no
handling. With one work order on the bike, the delete raised
`sqlite3.IntegrityError: FOREIGN KEY constraint failed`.

What it affects: a mechanic removing a bike with shop history gets a
traceback, not a sentence saying why. The restriction itself is right:
the history is kept. Phase 357's `workflow_runs` references the vehicle
the same way, so a bike with a saved run behaves the same.

What would close it: `garage remove` refuses such a bike, names what
still refers to it (work orders, saved runs), and exits 1, with a test
for each.

### F177 — CLOSED by Phase 361 (2026-09-29)

**Closed**, by the operator's (c). No path stores an engine type nobody
stated:
- migration 075 (live, schema 75) removed the column's
  `DEFAULT 'four_stroke'`;
- `VehicleBase.engine_type` defaults to None;
- the API stores NULL when the field is absent;
- `garage add` and `garage add-from-photo` ask unless the powertrain is
  electric (which gives `electric_motor`), and save nothing without an
  answer; `unknown` stores NULL;
- `garage update --engine-type` corrects it.

Every reader's handling of an unknown engine type is tested
(`tests/test_phase361_contract_and_engine_type.py`): the diagnose prompt
leaves the line out, the cache key tells unknown from four-stroke, parts
sourcing prints `unknown` (it printed `None`), and the API read returns
null. `361_mutate.py`: 19/19 red. The app's side closed in moto-diag-mobile
`cd359e0` (its F181). Rotary and diesel are F180.

**A bike's `engine_type` is stored as `four_stroke` when nobody gave it, the same shape as F174's powertrain**

Found by Phase 360's Step 0 (`360_step0.md`, S0-3). The default is set in
four places, all `four_stroke`:
- the `vehicles.engine_type` column, `TEXT DEFAULT 'four_stroke'`
  (`src/motodiag/core/migrations.py:212`, Phase 110's migration; a
  rollback's rebuilt table at `:2917` carries it too);
- `VehicleBase.engine_type`, `Field(EngineType.FOUR_STROKE, …)`
  (`src/motodiag/core/models.py:153`);
- the API's `VehicleCreateRequest.engine_type: EngineTypeLiteral =
  "four_stroke"` (`src/motodiag/api/routes/vehicles.py:84`);
- `garage add` and `garage add-from-photo` derive `FOUR_STROKE` for
  anything not stated as electric (`src/motodiag/cli/main.py:467`,
  `:589`), so a two-stroke, and a bike whose powertrain is unknown, are
  stored as four-stroke.

What it affects: diagnose passes `engine_type` into the prompt as
"Engine: four_stroke" (`src/motodiag/engine/prompts.py:46–47`, via
`cli/diagnose.py:482`), and parts sourcing prints it
(`src/motodiag/shop/parts_sourcing.py:226`). A two-stroke scooter added
without the value is described to the model as a four-stroke. Not
measured: how many live rows are affected. The live census for Phase 360
showed ten bikes, all `four_stroke`, all petrol models.

Not fixed in Phase 360, whose scope is the powertrain. What would close
it: the same choice F174 was given, applied to `engine_type`, and a test
for each reader with the value unknown.

**The app's side (2026-09-29):** the app's add-bike form preselects
`engine_type` `'four_stroke'`
(`moto-diag-mobile/src/screens/NewVehicleScreen.tsx`). The mobile repo's
F179, which closed the form's `ice` preselect in `moto-diag-mobile`
`57c9e45`, records this and leaves it open under F177.

### F178 — CLOSED by Phase 361 (2026-09-29)

**Closed.** No stored powertrain value can hide a safety rule, and the
API accepts only the enum's values:
- **first, before any API change** (`663accc`): `SafetyChecker` reads any
  value outside `PowertrainType` as unknown and shows every rule. Step 0
  found an empty string and `ICE` also hid the seven rules;
- the API's powertrain values are `ice`, `electric`, `hybrid`: a hybrid
  bike can be created, and the variants are refused (422) on create and
  update;
- `update_vehicle` converts `powertrain` and `engine_type` through their
  enums, so no writer stores a value outside them.

Tests: `tests/test_phase361_safety_unknown_powertrain.py` (with the old
checker restored, 10 of its 16 fail) and
`tests/test_phase361_contract_and_engine_type.py`. The app's snapshot and
types were refreshed in moto-diag-mobile `cd359e0`. No live row held a
value outside the enum.

**The API's powertrain values are not the enum's: no API request can create a hybrid bike, and an update stores `hybrid_parallel` as it is, which hides seven safety rules**

Measured by Phase 360 on a scratch database, 2026-09-28. The API declares
`PowertrainLiteral = Literal["ice", "electric", "hybrid_parallel",
"hybrid_series"]` (`src/motodiag/api/routes/vehicles.py:57–59`). But
`PowertrainType` holds `ice`, `electric` and `hybrid`
(`src/motodiag/core/models.py:67–69`), and so do the CLI, the workflow
templates and the safety scoping. What happens to each value:
- `POST /v1/vehicles` with `"powertrain": "hybrid"`: **422**, refused by
  the literal.
- The same with `hybrid_parallel` or `hybrid_series`: **400**, from
  `PowertrainType(req.powertrain)`.
- `PATCH /v1/vehicles/{id}` with `hybrid_parallel`: **200**, and the row
  stores `hybrid_parallel`. The update path passes the string to
  `update_vehicle` with no enum conversion.
- `SafetyChecker(powertrain="hybrid_parallel")` on "fuel leak pooling under
  the tank" returns **no alert**. The seven rules scoped
  `("ice", "hybrid")` (`src/motodiag/engine/safety.py:83–247`) do not match
  the stored value, so a hybrid bike updated through the API loses the
  fuel-leak warning. The checker's docstring says "a blank or wrong value
  must not be able to hide a fuel-leak warning".

What it affects: only a bike updated through the API with a hybrid
variant. The live census for Phase 360 showed ten bikes, all `ice`, so no
live row holds such a value. The app's generated types
(`moto-diag-mobile/src/api-types.ts`) carry the same four values.

Not fixed in Phase 360: fixing it changes the API contract and the app's
generated types. What would close it:
- the API's literal made the enum's three values, or the variants mapped to
  `hybrid`, with the OpenAPI schema and the app's types regenerated;
- the update path converting through the enum;
- a test that a stored value outside the enum cannot suppress a safety
  rule.

### F180

**The engine-type enum has no value for a rotary or a diesel engine, so such a bike can only be stored as unknown**

Found by Phase 361's Step 0 (`361_step0.md`, S0-5), 2026-09-29. The API
offered `rotary`, `diesel` and `none`, and the app labelled them "Rotary",
"Diesel" and "N/A"; `EngineType` (`src/motodiag/core/models.py:114–118`)
holds `four_stroke`, `two_stroke`, `electric_motor`, `hybrid` and
`desmodromic`. Measured on a scratch database: a create with any of the
three was refused with 400, and an update stored it as given.

The operator (2026-09-29): "Keep the API's engine types aligned to the
code's five, and file rotary and diesel as a finding for a later phase
(until then such a bike is stored as unknown)." Phase 361 does that:
- the API accepts the five only;
- the CLI's `--engine-type unknown` and the app's "not listed" answer store
  NULL.

`none` needs no value: an electric bike's engine type is `electric_motor`.

What it affects: a rotary or diesel motorcycle is stored as unknown, so the diagnose prompt carries no engine line for it. The live
census on 2026-09-29 held no such bike: ten, all `four_stroke`.

Also noted, not part of the fix: the enum mixes a cycle (`four_stroke`,
`two_stroke`) with a valve train (`desmodromic`, which is four-stroke).

What would close it: `rotary` and `diesel` added to `EngineType` and to
the API's literal, the mobile snapshot and the app's options refreshed,
and a test for each reader with the new values.

### F182 — CLOSED by Phase 274 (2026-09-29)

**Closed.** The operator (2026-09-29): "F182's fix stays in this batch;
the estimate takes its rate from the same labor_rates lookup the invoice
uses, so the quote and the invoice agree."
- The estimate is the estimated hours at the rate
  `_lookup_labor_rate_cents` returns (the lookup `generate_invoice_for_wo`
  uses) plus the estimated parts cost. Measured: 2.0 h at $95.00 and
  $549.91 of parts renders $739.91, where it rendered $200.00.
- With no work order, no estimated hours or no labour rate, the
  notification is refused with the reason; nothing is invented. A caller's
  extra context may not replace the estimate's figures.
- `motodiag shop labor-rate set/list` records the rate: no command wrote
  `labor_rates` before, so the fixed estimate had no rate to find.
- Each queued estimate is recorded in `work_order_quotes` (hours, rate,
  parts, total, date), which `shop analytics variance` compares with the
  invoice.
- `tests/test_phase274_quotes_variance.py`; four mutations of the fix, each
  red (`274_mutate.py`, Q1–Q4).

The finding as filed:

**The estimate a customer is sent is the estimated hours times a hard-coded $100, with the parts left out**

Found by Phase 274's Step 0 (`274_step0.md`), 2026-09-29.
`src/motodiag/shop/notifications.py:399–406` builds the `estimate_ready`
total as `estimated_hours * 100.0` ("rough placeholder if no invoice"),
unless an invoice already exists, which for an estimate it normally does
not. The shop's labour rate is not read, and the work order's
`estimated_parts_cost_cents` is not added.

Measured on a scratch database: a work order estimated at 2.0 hours with
$549.91 of parts renders "Estimate for WO #1 (Valve check): $200.00."
through `motodiag shop notify preview estimate_ready --wo 1`. No test
covers the figure (no test names `estimate_total`).

What it affects: every estimate queued through `shop notify trigger
estimate_ready` or the API's notification route. Live holds no
`estimate_ready` notification (4 notifications, all `parts_arrived`).

What would close it: the estimate is the estimated hours at the shop's
labour rate plus the estimated parts cost; when no rate is known the
estimate is refused, never invented; a test pins the figure.

### F183 — CLOSED by Phase 369 (2026-10-01)

**A pytest-xdist worker died during `test_phase359_content_cleanup.py::TestTheMigration::test_the_round_trip_restores_the_workflow_tables` in one parallel regression, and the failure has not reproduced**

Recorded by Phase 274 (`docs/phases/completed/274_phase_log.md`,
"The regression, re-run on the close-out commit"), 2026-09-29.

The regression of record at `3b7528f` (`regression.sh`, `-n auto --dist
load`) reported 10108 passed and 1 failed. The failure was not an
assertion. The log
(`~/.cache/motodiag/regressions/3b7528f_parallel_20260929_211825.log`)
reads `[gw2] node down: Not properly terminated`, `replacing crashed worker
gw2`, and `worker 'gw2' crashed while running` that test. It gives no
traceback and no signal. No crash report was written to
`~/Library/Logs/DiagnosticReports/`.

The test seeds a database, rolls it back from the schema head to 071,
and re-applies 072. Since Phase 274, that rollback also peels migration
076, which includes `ALTER TABLE inventory_items DROP COLUMN
reorder_quantity`.

What was measured:
- the same test passed in the regression at `757b9f4` (10109 passed),
  whose source differs from `3b7528f` only in documents and
  `tests/test_roadmap_continuity.py`;
- the file alone: 18 passed;
- the file with `test_phase274_migration.py` and gate 15 under
  `-n auto --dist load`, five times: 64 passed each time;
- the regression re-run at `3b7528f`, same commit: 10109 passed, 0 failed
  (30 min 4 s).

Rule 3 says a test that fails only in parallel is a bug to fix, and this
one could not be made to fail again. Not excluded: memory pressure or an
external kill of the worker process, or a crash inside SQLite's
`DROP COLUMN` under load.

What would close it: the crash reproduced and its cause named, or a
stated number of `-n auto` runs of the migration round-trip tests that
all pass, with the worker's exit status captured (for example,
`faulthandler` enabled in the workers).

**Seen again, 2026-09-30 (Phase 281), on a different test.** A whole-suite
`-n auto --dist load` run on Phase 281's uncommitted work (not a
regression of record) lost worker gw6 with no traceback: `worker 'gw6'
crashed while running
'tests/test_phase78_gate2_integration.py::TestGate2KnowledgeBaseIntegration::test_noise_cross_make'`.
That test does no migration round-trip, so the crash is not tied to
`DROP COLUMN`. No crash report in `~/Library/Logs/DiagnosticReports/`.
The file alone: 22 passed, in 4 min 40 s. Recorded here as the prompt
directs; the regression of record is run in parallel afterwards, and a
second loss there stops the phase.

**Seen a third time, and an hour spent reproducing it (Phase 281,
2026-10-01).** The regression at `4faa46b` lost gw1 with no traceback in
`test_phase359_content_cleanup.py::TestTheMigration::test_the_round_trip_restores_the_workflow_tables`,
at the same point of the run as 274's crash (gw8 had just started gate
2's `test_yamaha_coverage`); the file alone passed 18. The operator
time-boxed a reproduction to one hour (`281_f183_repro.py`, its records
`281_f183_runs.jsonl` and `281_f183_hammer.jsonl`, all in Phase 281's
folder):
- the two files together under `-n 2 --dist load`, 4 runs: no lost worker;
- the two as plain processes side by side, 4 runs: every exit code 0, no
  signal;
- six plain processes at once over the round-trip test alone, 52 rounds
  (312 processes): every exit code 0, no signal.

Not reproduced. Ruled out: memory (no jetsam, per the operator), any
process-killing call in `src/` or `tests/`, pytest-timeout (not
installed), and the other project's one `pkill` (it matches no pytest).
All three losses came in the last ~2% of a full parallel run, which the
two files alone do not recreate. Phase 281's log has the details.

**Closed by Phase 369 (2026-10-01): the cause was a SIGALRM the push guard
left armed.** `_pre_push_guard.main()` armed `signal.alarm(FAST_LIMIT_S +
60)` (345 s), whose handler `_out_of_time` calls `os._exit(2)`, and
cancelled it inside its `try`; an exception from `wholetree_gate` skipped
the cancel. `test_phase358_wholetree_contract.py::TestTheWiring::test_an_error_in_the_whole_tree_gate_blocks`
runs `main()` in the worker with the gate raising, so 345 s later that
worker ended in whatever test it had reached: `os._exit` leaves no
traceback, faulthandler sees no fatal signal, and the handler's one line
went to pytest's captured stderr. The earlier searches for code that ends a
process looked for kill calls in `src/` and `tests/`; the handler is in
`.claude/skills/closeout/`.

The evidence (Phase 369's folder):
- in all three logged losses the dead worker is the one that ran that test
  (gw2 at `3b7528f`, gw1 at `4faa46b`, gw6 at `8ba118e`);
  `369_f183_timing.py` over all 19 parallel logs since Phase 358: the dead
  workers had 306.0, 311.8 and 327.6 s of completed tests after it and died
  in the next; the sixteen survivors ran out of tests at 63–343 s. 281's
  320 reproduction runs never ran the 358 test;
- R1, before the fix: that test and a 400 s sleeper in one worker lost the
  worker at 345.56 s, "node down: Not properly terminated", and the new
  plugin read its exit: "exited with status 2 (no signal)";
- R2, after the fix, the same command: 2 passed, no worker lost.

The fix: both guards cancel in a `finally`. What holds it:
`tests/test_phase369_worker_loss.py` (369_mutate.py 9/9 red), and
`tests/support/alarm_left_armed.py`, which fails any test that leaves
SIGALRM armed. `tests/support/worker_loss.py` stays: a lost worker now
writes its exit status or signal, its last test, any catchable signal and
a faulthandler dump into the run's output.

How it reached `master`: `master` failed gate 11 until 281 merged (the
mobile snapshot follows 281's API). So Phase 281 carried the fix
(`63fa5a8`) and merged first (`2806017`), at the operator's option 1.
Both regressions ran without a lost worker, and the teardown check found
no test leaving the alarm armed:
- 281's: 10279 passed, 0 failed at `63fa5a8`;
- 369's, of record: 10279 passed, 0 failed at `88dbbd1`.

### F184 — CLOSED by Phase 281 (2026-10-01)

**Closed.** The operator picked option A (2026-09-30): "1: A." The
invoice API's `tax_rate` and the CLI's `--tax-rate` are removed; an
invoice takes its tax only from the shop's tax jurisdiction on record.
- Rates and line rules are stored per jurisdiction, each with its
  effective date, valid-until date, source, check date and provenance
  (`regulation` or `shop`). Massachusetts ships from the Department of
  Revenue's text: 6.25% on separately stated parts; labour not taxable;
  a diagnostic fee not taxable as a reading of 830 CMR 64H.1.1(2)(a)1;
  no rule for shop supplies.
- An invoice for a shop with no jurisdiction, no rate valid on the
  invoice date, or no rule for a line type it carries is refused (the
  API answers 409); nothing is written.
- Each invoice records the rate, the rate's id and source, its recheck-by
  date and the taxed line types, and prints them. Tax falls on the
  taxable lines only.
- `shop tax status` fails once a rate or rule is past its validity.
- `tests/test_phase281_tax.py`; mutations T1–T11 in `281_mutate.py`, each
  red. The mobile snapshot was refreshed in moto-diag-mobile `e536e60`.
- Live: migration 078 at schema 78; the smoke shop has no jurisdiction,
  so an invoice there is refused until one is set.
- A tax-exempt sale is F185, open.

The finding as filed:

**An invoice's sales tax is zero unless someone types a rate, and nothing records that zero was assumed**

Found by Phase 281's Step 0 (`281_step0.md`), 2026-09-30, measured on
`master` at `5cde0c3`.
- `generate_invoice_for_wo(tax_rate=0.0)` in
  `src/motodiag/shop/invoicing.py:282` computes the tax as
  `subtotal × tax_rate` (line 448).
- `motodiag shop invoice generate --tax-rate` defaults to 0.0
  (`src/motodiag/cli/shop.py:3604`).
- The API's `InvoiceGenerateRequest.tax_rate` defaults to 0.0
  (`src/motodiag/api/routes/shop_mgmt.py:237`), for
  `POST /v1/shop/{shop_id}/invoices/generate`.
- An invoice stores one `tax_amount` and not the rate, so an invoice
  taxed at zero because nobody gave a rate looks the same as one for a
  shop that owes no tax.
- The shop records no location: the live `shops` table holds the smoke
  shop, with no address or state, so nothing could supply a rate.

It is an assumed value of the kind F174, F177 and F182 were. In
Massachusetts, the first shop's state, the 6.25% sales tax applies to
separately stated parts (830 CMR 64H.1.1(5)(a)); an invoice made with the
default charges none.

What it affects: every invoice generated without a rate. Live holds 0
invoices. The mobile app does not call invoice generation; only its
generated types name the request.

What would close it: the rate comes from a record of the shop's tax
jurisdiction, with its source, effective date and stated validity; an
invoice for a shop with no valid rate is refused; and each invoice records
the rate it used and that rate's source.

### F185

**A tax-exempt sale cannot be invoiced once the tax comes only from the shop's record**

Filed at the operator's request, 2026-09-30, with their pick of option A
for F184 in Phase 281 (`281_step0.md`, question 1). The operator's words:
"with the field gone, a tax-exempt sale (a resale or exempt-organization
certificate, for example a town's police bikes) can't be invoiced. It
waits until a real shop needs it."

With option A, invoice generation takes its rate and line rules only from
the shop's tax jurisdiction on record: the API's `tax_rate` and the CLI's
`--tax-rate` are removed. A sale the law exempts for this buyer, such as
one to a buyer holding a resale certificate or an exempt organization's
certificate (the DOR's guide names Form ST-4 for resale), would be taxed
at the shop's rate, with no way to record the exemption or its
certificate.

What it affects: no live shop today (live holds the smoke shop and 0
invoices). It waits until a real shop needs it.

What would close it: a customer (or a single invoice) can be marked
exempt, with the certificate's kind and number and who recorded it; the
invoice then records the exemption in place of the rate, and prints it.

### F186 — CLOSED by Phase 377 (2026-10-07)

**Work-order times are stamped in naive local time and compared with UTC windows**

**Closed:**
- **Writers:** the work-order, issue, intake, repair-plan, booking
  (`updated_at`) and other shop writers stamp UTC in Phase 370's format
  through `utc_now()`. That is 40 lines; the four appointment clock stamps
  keep 275's rule.
- **Comparisons:** `shop/analytics.py`'s 15 comparisons parse both sides,
  `datetime(col) >= ?` against `_parse_date_window`'s UTC cutoff. A typed
  date is the shop's day.
- **Days and months:** throughput's days, the P&L month and the accounting
  export use the shop's day (the server's zone, F192).
- **No silent drops:** turnaround and mechanic performance parse both times
  by one rule and raise, naming the work order, on a value that is not a
  time.
- **Readers:** the CLI and the work-order report show local time; the API
  sends 370's format, and the app formats it (moto-diag-mobile `0074eb9`).
- **Live:** migration 082 converted the 40 shop fields in the defect shape
  with the operator's approval; known_issues was left (2A).
- **Proof:** on the frozen clock in New York, a 30-day window at
  2026-10-15 12:00 EDT leaves out a 09:00 EDT completion on its first day
  (`tests/test_phase377_shop_utc.py`). 26/26 mutations red.

Found at Phase 370's Step 0 (2026-10-06), in the census of naive
`datetime.now()` calls that F10's fix started from. It is F10's family on
other tables, not a monthly counter.

- **Who stamps local:** `shop/work_order_repo.py` writes `opened_at`,
  `started_at`, `completed_at`, `closed_at` and `updated_at` with
  `datetime.now().isoformat()` (nine calls); `issue_repo.py` (5),
  `intake_repo.py` (4), `pricing/repair_plan.py` (5),
  `scheduling/booking.py` (4) and ten other modules do the same. In all,
  56 lines in `src/` call `datetime.now()` with no zone (counted by
  `grep -rn "datetime.now()"`, less lines naming `timezone`, `.year`,
  `strftime` or `date()`), 11 of them in `session_repo` (F10).
  `work_orders.created_at` is the column's `CURRENT_TIMESTAMP`, UTC.
- **Who compares them with UTC:** `shop/analytics.py`'s
  `_parse_date_window` returns a UTC cutoff as `YYYY-MM-DD HH:MM:SS`.
  `throughput`, `turnaround` and `labor_accuracy` compare it with
  `completed_at`. Two errors add: the clocks differ by the UTC offset
  (4 or 5 hours in a US Eastern shop), and on the cutoff's own date every
  `T` value sorts after the space value whatever its hour. So a 30-day
  window's first day is counted whole, plus up to the offset of the day
  before.
- **Live, 2026-10-06:** `work_orders` has 6 rows. `created_at`: 6 in the
  space shape (UTC). `opened_at` 5, `started_at` 4, `completed_at` 3 and
  `closed_at` 3, all naive local. `updated_at`: 5 local, 1 space.
  `issues` and `bay_schedule_slots` have no stamped rows.
- **Not a monthly quota.** The windows are rolling (`30d` by default), and
  the error is at the window's first edge. No test fails at a month's end
  because of it.

What would close it: every work-order, issue, intake, repair-plan and
booking time written in UTC, in Phase 370's format, with the analytics
cutoff in the same format; each reader that prints these times shows local
time; and a decision on the live rows like 370's.

### F187 — CLOSED by Phase 273 (2026-10-06)

**Closed.** Each defect below is fixed and, put back, turns a test red
(`273_mutate.py` F1–F6): checkout carries `user_id` and `tier` in
`subscription_data.metadata`; the period is read from the items; no tier
or status is invented (the tier from metadata, else the price id, else the
event is recorded with the reason); every subscription event re-reads the
subscription from Stripe; a failed read answers 503 and is not recorded.
Proved live in test mode: a `shop` checkout paid with a test card was
stored `shop active` with its period and price from the re-read, and its
payment recorded (200 cents) after bug fix #2. See
`docs/phases/completed/273_phase_log.md`.

**Phase 176's subscription webhook path would not change a tier against Stripe's current API**

Found at Phase 273's Step 0 (2026-10-06), by reading the code against
Stripe's documentation for API version `2026-09-30.endive`, the version
`stripe==16.0.0` pins (its `_api_version.py`). None of 176's Stripe code
has run against Stripe: the SDK is not installed, and its tests use the
fake provider with hand-built payloads.
- **The user is never found.** `StripeBillingProvider.create_checkout_session`
  puts `user_id` and `tier` in the Checkout Session's `metadata`. The
  subscription events read `metadata` on the Subscription object
  (`_resolve_user_id`). Stripe's metadata page: "An object's metadata
  doesn't automatically copy to related objects"; only
  `subscription_data.metadata` reaches the Subscription. A first
  `customer.subscription.created` then resolves no user (no subscription
  row holds the customer yet), is logged and skipped, and returns 200. The
  user has paid and their tier does not change.
- **The billing period is always empty.** `_sub_data_from_event` reads
  `current_period_start` and `current_period_end` from the Subscription.
  Since `2025-03-31.basil` they are on each subscription item
  (`items.data[].current_period_*`), so both are stored as null, and
  `GET /v1/billing/subscription` returns `current_period_end: null`.
- **Missing values are invented.** A payload with no tier is stored as
  `individual`, and one with no status as `active`.
- **Order is trusted.** Stripe: "doesn't guarantee the delivery of events
  in the order that they're generated". `upsert_from_stripe` writes each
  event's status, so a `customer.subscription.updated` delivered after
  `.deleted` makes a cancelled subscription active again.
- **A failed handler is final.** `dispatch_event` records the event,
  answers 200 when its handler raises, and skips the same event id on
  every retry. A transient failure (the database locked, for example) is
  never retried.

What would close it: user and tier carried in `subscription_data.metadata`
(and the session's), the tier read from the price id where metadata is
absent and refused if neither gives one; the period read from the items;
the subscription's state re-read from Stripe on each event rather than
taken from the payload; a handler failure answered with a status Stripe
retries, and not recorded as processed; each with a test, and the path run
once end to end against test mode.

### F188 — CLOSED by Phase 373 (2026-10-06)

**A warranty claim and the invoice for the same work order do not know about each other**

**Closed:** `shop warranty claim cover` records the lines a claim covers;
the invoice leaves them off what the customer owes and prices them for
the claim, so the amount claimed is derived in integer cents
(`--claimed-cents` is gone); the claim's tax follows who owes the repair
(`tax_warranty_rules`); the packet lists the covered lines and the
amount; the claim is exported as owed by its provider. Gate 16's pinned
test is inverted (`test_f188_covered_work_is_off_the_customers_invoice_and_on_the_claim`).
The measured case below, now: customer 6000 cents, claim 22623.
Migration 081. Settlements in the export are F190 (row 376).

Found at Phase 292's Step 0 (2026-10-06), in the dry walk of Gate 16 on a
scratch database (`docs/phases/in_progress/292_step0.md`, S0-4 H2).
- **The claim links the work order** (`shop warranty claim open --wo`,
  `inventory/warranty_claims.py:51`), and the invoice is built from the
  same work order (`shop invoice generate`, `shop/invoicing.py`). Neither
  reads the other: no query in `shop/invoicing.py` names
  `warranty_claims`, and none in `inventory/warranty_claims.py` names
  `invoices`.
- **Measured:** a bike with a valid comprehensive warranty (8,000 of
  12,000 mi, inside its dates), a draft claim open on the work order, and
  the repair (1.5 h at 12000 cents, 2 parts at 4599) invoiced to the
  customer in full: subtotal 27198, tax 575, total 27773 cents, paid by
  the customer's card.
- **The claimed amount is typed by hand** (`--claimed-cents`) and was "not
  recorded"; nothing derives it from the work order's labour and parts.

What it affects: every warranty repair. The shop can bill the customer and
the maker for the same work, and nothing in the app shows it.

What would close it (row 373): a rule for which lines a claim covers; the
claimed amount derived from those lines; claimed lines left off what the
customer owes; and Gate 16's pinned test of today's behaviour inverted.

### F189 — CLOSED by Phase 374 (2026-10-07)

**Check-in opens a work order with no intake, and no command can attach one afterwards**

**Closed:** `shop appointment check-in` opens the work order from the
visit's intake:
- the one named with `--intake`;
- or the one open intake for the shop, customer and bike, taken within a
  day of the appointment;
- or, with none open, one it records itself, with the mileage unknown
  unless given and the booking's notes as the problems.

Otherwise it refuses and lists them. It prints the intake's date and
mileage. The claim packet prints the mileage at intake and the reported
problems; an unknown mileage stays "not recorded", never the bike's. The
rule that a work order's intake cannot be changed afterwards stands.
Gate 16 walks both orders; its pinned test is inverted
(`test_f189_the_work_order_carries_its_intake_in_either_order`).

Found at Phase 292's Step 0 (2026-10-06) (`292_step0.md`, S0-4 H3).
- `shop appointment check-in` without `--wo` creates and opens a work
  order (`scheduling/booking.py:410`) and creates no intake.
- `intake_visit_id` is not in `update_work_order`'s whitelist, by design
  (`shop/work_order_repo.py:85`: "cancel the WO and recreate"). A
  checked-in appointment cannot be checked in again, so the recreated work
  order cannot be linked to the appointment.
- So book → intake → work order holds only in one order: `intake create`,
  then `work-order create --intake`, then `check-in --wo`. Gate 16 walks
  that order.

What it affects: the intake's mileage and reported problems never reach a
work order opened by check-in. The warranty claim packet then reads the
bike's recorded mileage instead of the mileage at intake
(`render_claim_packet`).

What would close it (row 374): check-in links or creates the intake, so
both orders end with the work order carrying it; Gate 16's pinned test of
the other order inverted.

### F190 — CLOSED by Phase 376 (2026-10-07)

**A warranty claim's settlement does not reach the accounting export**

**Closed:** `shop accounting export` books each settlement against the
claim's receivable, once per target, in the export whose range holds its
settlement day (the shop's day of `settled_at`, parsed). QuickBooks: a
`<claim number>-CR` journal crediting the provider's A/R for the
shortfall, against the income and tax the shortfall invoice re-bills (that
invoice's own journal follows) or the new `absorbed` account. Xero: a
tax-inclusive credit note to the provider in `<out>_credit_notes.csv`,
and the billed shortfall invoice in the invoices file. Revenue is not
counted twice; tax payable moves only by D11's cent. Proven for a denial
and a part approval, billed and absorbed, in both files
(`tests/test_phase376_settlement_export.py`); migration 083 live. The
text below is the finding as filed.

Found at Phase 373's Step 0 (2026-10-06), in the plan for the operator's
choices 2a and 5a (`docs/phases/completed/373_phase_log.md`).
- **Row 373 exports a claim as a receivable** from the warranty provider,
  at the amount claimed: in QuickBooks a journal entry debiting Accounts
  Receivable in the provider's name; in Xero a sales invoice to the
  provider.
- **When the claim is denied or approved for less,** `shop warranty claim
  settle` records the shop's decision: bill the customer for the shortfall
  (a second invoice on the work order, allowed only for this), or absorb
  it. **Neither is exported.** The export leaves shortfall invoices out
  and says how many; an absorbed shortfall changes no export row.
- So after a settlement the books still show the provider owing the full
  claimed amount, and a shortfall billed to the customer is not in them.
  Exporting the shortfall invoice as an ordinary invoice would count the
  covered work's revenue twice, which is why it is left out rather than
  exported.

What it affects: every claim settled for less than claimed. Live holds 0
claims (2026-10-06).

What would close it (row 376): each settlement in both files, against the
claim's receivable: in QuickBooks a journal moving the shortfall from the
provider to the customer or to a write-off account; in Xero a credit note
against the provider's invoice, which Xero imports from a file of its
own.

### F191 — CLOSED by Phase 377 (2026-10-07)

**`--since` compares a local-time cutoff with UTC stamps written in another format**

**Closed:** `_since_cutoff` is removed. `list_intakes`, `count_intakes`,
`list_work_orders` and `list_issues` compare `datetime(col) >= ?` against
`core/timestamps.utc_cutoff`, which is UTC in SQLite's canonical shape.
`datetime()` reads every stored shape and converts offsets. On the frozen
clock in New York, at 23:26 EDT and at 12:00 EDT, `--since 30m` includes
an intake, work order or issue from a minute ago and leaves out one from
three hours ago, through the repos and `shop intake list`
(`tests/test_phase377_shop_utc.py::TestSince30m`).

Found in Phase 374 (2026-10-06), reading `intake_at`'s clock.
`shop/intake_repo.py`'s `_since_cutoff` turns `7d`, `24h` or `30m` into
`datetime.now() - offset`, which is local time, formatted
`YYYY-MM-DDTHH:MM:SS`. It compares that cutoff, as text, with
`intake_visits.intake_at`. `intake_at` is UTC, `YYYY-MM-DD HH:MM:SS`:
SQLite's `CURRENT_TIMESTAMP` wrote it until 374, and Python's clock in the
same format since. `work_order_repo.list_work_orders` (`wo.created_at`)
and `issue_repo` reuse the same cutoff.

Measured on a scratch database, 2026-10-06 23:26 EDT:
- **In New York,** an intake stamped three hours earlier is listed by
  `list_intakes(since="30m")` and counted by `count_intakes`, along with
  two made that minute: 3 found, 2 expected.
- **On a machine set to UTC,** the separator alone decides:
  `'2026-10-07 03:26:39' >= '2026-10-07T02:56:39'` is False, so an
  intake made that minute is left out of `--since 30m`.

What it affects: `shop intake list --since`, the intake count, and the
work order and issue lists' `--since`. Live holds 0 intakes (2026-10-06).

What would close it: compute the cutoff in UTC in the column's own format
(or compare parsed times), for each table whose stamp it is compared with,
with a test at a fixed clock in a zone away from UTC.

### F192

**A shop has no time zone, so "the shop's day" is the server's zone**

Found at Phase 377's Step 0 (2026-10-07), in the operator's answer to its
first question. `shops` has no time-zone column (its columns: id,
owner_user_id, name, address, city, state, zip, phone, email, tax_id,
hours_json, is_active, created_at, updated_at, triage_weights), and no code
in `src/` uses `zoneinfo`. Phase 377 stores every shop time in UTC and
shows it, buckets it by day and reads a typed date in the machine's local
zone (`astimezone()`, SQLite's `'localtime'`). Phase 275's appointment
times are "the shop's clock time as entered" for the same reason.

What it affects: one server serving shops in more than one zone. A shop in
California on a server set to Eastern sees its times three hours ahead,
its `--since 2026-10-07` starts at 21:00 the day before, and an invoice
issued at 22:00 Pacific on the 31st falls in the next month's P&L and
accounting export. Today there is one shop, in Massachusetts, on a server
in its zone, so nothing is wrong in live. The product is meant for every
state.

What would close it: a time zone on each shop (an IANA name, such as
`America/Los_Angeles`), set when the shop is created, and every reader,
day bucket and typed-date cutoff of a shop's times converting in that
zone instead of the server's; appointment clock times read in it too.

Also seen in Phase 377's census: a bay slot's `scheduled_start` and
`scheduled_end` are the shop's clock time stored with `+00:00` (Phase
275's rule, `booking.py`), while its `actual_end` is real UTC. Analytics'
overrun window compares `COALESCE(actual_end, scheduled_end)` with a UTC
cutoff, so a slot with no `actual_end` sits at its window's edge off by
the shop's offset. A per-shop zone would let both be stored as one clock.

### F193

**Sensor-recording and drift filters compare a typed `--since` as text, in UTC**

Found in Phase 377's census (2026-10-07), left out of its fix by decision
(the phase log says why). `hardware/recorder.py`'s `list_recordings`
(`started_at >= ?`, `<= ?`), `advanced/drift.py` (`s.captured_at >= ?`,
`<= ?`) and `cli/advanced.py`'s drift chart (`s.captured_at >= ?`) put the
user's `--since` and `--until` straight into a text comparison. The
columns hold one aware shape, `YYYY-MM-DDTHH:MM:SS[.ffffff]+00:00`, so a
date or a value with an offset compares as a prefix; but a typed date is
read as the UTC day (a 2026-10-07 filter starts at 20:00 the evening
before in New York), and a typed value with another offset, or with a
space, compares wrong.

What it affects: `hardware` recording lists and the drift commands'
windows, by up to the UTC offset at the edges. Not the shop's tables.
`sensor_samples` can be large, which is why 377 did not wrap the column
in `datetime()` (it would stop the index being used).

What would close it: convert the typed value with `utc_cutoff` (Phase
377), then write it in the column's own shape, so the comparison stays
on the index; with a test at a fixed clock in a zone away from UTC.


### F194 — CLOSED by Phase 376 (2026-10-07)

**An invoice's number carries the UTC day, while its tax and the export use the shop's day**

**Closed:** `shop/invoicing.py`'s `_number_day` dates both numbers by the
shop's day of the same instant (`core/timestamps.local_day`). On the
frozen clock at 2026-10-31 21:00 EDT an invoice is `INV-1-1-20261031` and
a shortfall invoice `INV-1-1-20261031-S1`
(`tests/test_phase376_settlement_export.py`; mutation N1, the UTC day
again, goes red). The text below is the finding as filed.

Found at Phase 376's Step 0 (2026-10-07), from the operator's measurement
at `914adad`, re-verified on `phase-376` at `0897f14`.
`_format_invoice_number` (`shop/invoicing.py:210`) writes
`INV-<shop>-<work order>-<YYYYMMDD>` from the `now` it is given, and
`generate_invoice_for_wo` gives it `datetime.now(timezone.utc)` (`:598`).
The shortfall invoice's number takes its date the same way (`:764`). Tax
rules are resolved on `tax.today()` and the accounting export dates an
invoice by the shop's day (`_us_date`, Phase 377), both local. So after
20:00 EDT (19:00 EST) an invoice is numbered with tomorrow's date: at
2026-10-31 21:00 EDT the number reads `20261101` and the shop's day is
2026-10-31 (printed on the frozen-zone check in the 376 log), so an October
invoice can carry a November number.

What it affects: every invoice and shortfall invoice issued in the evening
hours, in the number printed to the customer and carried into QuickBooks'
Journal No. and Xero's InvoiceNumber. No amount or date column is wrong;
11 test files cite `INV-` numbers. Live holds 0 invoices (2026-10-07).

What would close it: date the number by the shop's day of the same
instant (`core/timestamps.local_day`), in both places, with a test on the
frozen clock at 21:00 EDT on a month's last day.

### F195

**Parts given away under an absorbed claim that carried no tax may owe tax on their cost, and nothing records it**

Found at Phase 376's Step 0 (2026-10-07), in its reading of the tax on an
absorbed shortfall (`docs/phases/completed/376_sources.md`, "What the
sources say together"). A claim whose warranty's payer is
`maker_with_bike` or `shop_contract` carries no tax (Phase 373's rules).
When its provider denies it or pays short and the shop absorbs the
shortfall, the parts were transferred for nothing. Massachusetts' LR 00-10
quotes G.L. c. 64H § 8(d): a use of property bought for resale "other than
retention, demonstration or display" is "deemed a retail sale", with "the
cost of the service or property to him" as the gross receipts. 830 CMR
64H.1.4 (promotional items) would bear on it and is blocked (403). Nothing
read in full rules on parts furnished under a denied warranty claim.

What it affects: any absorbed claim with covered parts and no tax on the
claim. The export (Phase 376) books the shortfall to the absorbed account
and no tax; the CLI names this finding when it does. The shop's cost of a
part is not on the invoice (`typical_cost_cents` is a price), so no tax
could be computed from what is stored. Live holds 0 claims (2026-10-07).

What would close it: the jurisdiction's own ruling on parts furnished
free under a denied warranty claim, recorded per jurisdiction as a rule
with its source; and, if it taxes their cost, a cost basis for the parts
and a line in the export.
