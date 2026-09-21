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

At the time of writing the highest assigned is **F125** (this file); the mobile
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

**Still unsourced**, and now a much shorter list: Filly LX 50, Piaggio Beverly
250, SYM JET 50, SYM JET 100, SYM Joyride, Vespa 946, Vespa Sprint, Zuma 50.
Honda's own web spec pages return **403** to this environment on every path
tried (`powersports.honda.com`, `automobiles.honda.com`), as they did
throughout Phase 254, so the remaining eight need either a document or a route
in.

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
