# Phase 256 — The retrieval chokepoint

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-21

> **Step 0 below is unchanged from the committed draft** (`471f123`) and is
> not re-run. The plan begins at "Positive control on Step 0 itself".

---

## Why this phase exists

Phase 255 added an applicability filter and wired it into the retrieval path
it knew about. Asked late which *other* paths read `known_issues` for a
specific machine, it found a second (the video `/ask` endpoint, fixed in 255)
and a third (`predict_failures`, filed as F123). The operator's instruction:
**one chokepoint function applies the filter; every door calls it; a
structural guard fails if anything queries `known_issues` for those purposes
without going through it.**

## Step 0 — method

Stated first, because the conclusion is only as good as the sweep, and Phase
255 twice reported a subset as if it were a census.

**Three independent enumerations over `src/motodiag/` (263 files):**

1. **Raw SQL** — `grep -riE "(FROM|JOIN|INTO|UPDATE|DELETE FROM)[[:space:]]+known_issues"`.
   This is the one that finds a door nobody registered, because it does not
   depend on knowing which function to look for.
2. **AST call-sites** — parse every file, walk every `ast.Call`, match against
   the eight known repo/retrieval functions by name (`known_issues_for_vehicle`,
   `search_known_issues`, `search_known_issues_text`, `get_known_issue`,
   `count_known_issues`, `count_known_issues_matching`, `compose_prompt_rows`,
   `_load_known_issues`, `drop_inapplicable`).
3. **Every file naming the table at all** — 30 files — then each classified by
   hand as *retrieves* or *receives*.

**Honest limit on the method, stated because it matters:** the three known
doors were **not** rediscovered blind. I knew them from Phase 255 before
starting, so enumerations 2 and 3 were confirmations, not discoveries. **Only
enumeration 1 — the raw-SQL sweep — was capable of finding something nobody
had told it about, and it is the one that found door 4.** A future audit
should run the raw-SQL sweep first and treat the function list as derived
from it, not the reverse.


### Correction to Step 0, 2026-09-21 — "one dynamic query" was wrong; there are four

Step 0 reported **one** dynamic table-name query in the tree
(`capture/stats.py:19`) and treated the rest of its 11 hits as false
positives. **There are four.** The three it missed:

* `shop/intake_repo.py:90`
* `shop/issue_repo.py:173`
* `shop/work_order_repo.py:112`

each `f"SELECT * FROM {table} WHERE id = ?"`.

**Why the search could not have found them**, which is the part worth
keeping: it looked for `FROM` followed by `{`. In an f-string, `{table}` is
a **FormattedValue** — it is not in the literal text at all. The literal
simply ends with `"SELECT * FROM "`. So the search was scanning for a
character the target never contains, and its eleven "hits" were prose in
log messages; the one real find was luck.

This is another instance of the rule added to `CLAUDE.md` the same day: **a
search that cannot find is not a census.** The absence claim was about the
search, not the tree.

**All four are safe**, and that is verified rather than assumed: every
literal passed as the table argument was read from the call sites —
`intakes`, `customers`, `vehicles`, `shops`, `work_orders`,
`diagnostic_sessions`, `video_analyses`, `guidance_interactions` and the
rest. **`known_issues` is not among them in any of the four.**

The structural guard now pins all four and fails on a fifth, and its own
first version repeated Step 0's mistake exactly before over-correcting to
thirteen — twelve of them the same prose. It needs both halves: the
f-string must look like SQL **and** a literal must end where a table name
would go.

## Step 0 — the doors

| # | path | how it retrieves | applicability | status |
|---|---|---|---|---|
| 1 | `cli/diagnose.py:285` → `compose_prompt_rows:294`, via `_load_known_issues` (callers `diagnose:460`, `diagnose:536`, `code.py:160`) | resolver + junction, tiered | **filtered** | 255 |
| 2 | `api/routes/videos.py:528` → `drop_inapplicable:539` | resolver + junction, no composition | **filtered** | 255 bug fix #1 |
| 3 | `advanced/predictor.py:190,194,203,212` | `search_known_issues`, four passes, `LIKE` | **unfiltered** | **F123** |
| 4 | `shop/priority_scorer.py:255` | **raw SQL of its own** | **n/a — dead** | **F126** |

**Not doors**, verified rather than assumed: `api/routes/kb.py` and `cli/kb.py`
and `core/search.py` are catalogue **search** (user-initiated, not per-machine);
`pricing/repair_plan.py:293` fetches one issue **by id**;
`knowledge/marques.py` and `knowledge/models.py` rebuild the derived
junctions; `core/migrations.py` is one-time; `knowledge/loader.py` writes. The
other 14 files that name the table **receive** `known_issues` as a parameter
(`media/vision_analysis_pipeline.py`, `engine/prompts.py`, `engine/client.py`)
or mention it in prose. Zero raw SQL, zero repo calls.

## Step 0 — door 4 in detail (F126)

```sql
SELECT id, title, severity, fix FROM known_issues
 WHERE LOWER(make) = ? AND (model IS NULL OR LOWER(model) LIKE ?) LIMIT 5
```

**There is no column `fix`** — it is `fix_procedure`, and `fix` appears in no
version of `SCHEMA_SQL` and no migration. Every call raises
`sqlite3.OperationalError`, and the enclosing `except Exception: return []`
turns it into an empty result. The function has **never returned a row**.

Measured on the live database with the column corrected: **7 of 10 live
vehicles would return rows** (Road King 5, YZF-R1 5, GSX-R1000 5, SV650 5,
KTM 390 5, ZX-10R 2, CB500 2). All ten return zero today. The consumer is the
**AI work-order priority scorer**, so a shop's prioritisation has been running
on a silently emptied input that reads exactly like "no known issues".

**No test covers the function** — `grep -rn "_find_kb_matches_safe" tests/`
returns nothing.

Three defects one line apart: the wrong column; the bare `except` that makes a
schema error indistinguishable from an empty corpus; and `LOWER(model) LIKE
'%...%'`, the substring matching Phases 244C–244I removed from the main
retrieval path and which never reached here because nobody knew this was a
door. **Routing it through the chokepoint removes all three at once, which is
the argument for the chokepoint.**

## Step 0 — F122, and the option that was missed

Phase 255 made an invalid `applicability` value raise at read time, on the
reasoning that the only alternative was loading it as unscoped — which would
put a mistyped row back in front of every machine. **A third option was not
considered**, and it follows from this axis's own principle that *missing
beats misleading*:

> At read time the chokepoint **excludes** the corrupt row — never unscoped,
> never a crash — **logs an error naming the row id**, and **counts it in the
> persisted table**. Rejection stays loud at seed load and at every write
> path.

To evaluate in this phase's migration: whether
`CHECK (applicability IS NULL OR json_valid(applicability))` can be added, so
the column cannot hold unparseable JSON in the first place. Note that a CHECK
cannot validate the *schema* of the JSON — unknown axis keys and unknown
values still need the pydantic model — so this narrows the failure surface
rather than closing it.

## Step 0 — open, not yet answered

* **Piaggio Beverly 250 — no document *obtained*, not "no document exists".**
  Zero mentions across the 227 readable PDFs. **36 of 263 PDFs on disk are
  unreadable**, and three are Beverly-related: `refute/beverly.pdf` and
  `pdf/bev500.pdf` are HTML landing pages saved with a `.pdf` extension, and
  `pdf/bv500.pdf` is the 13-byte string `404 Not Found`. The landing pages
  name a *"bevely 125 e3 workshop manual"* and a *"beverly cruiser 500ie
  workshop manual"* — neither a 250. The earlier "no document" verdict was
  reached over a denominator that silently excluded 36 files.
* **Vespa 946 — not established.** All 16 apparent hits for `946` are the
  phone number `(888) 946-6329` in Honda manuals. **A search by Piaggio
  document code has not been run**, because no 946 document code is in hand,
  and no file on disk is named for it.
* **Unreadable inventory:** 36 of 263. Failed downloads (HTML or `404`)
  dominate; the genuinely-real-but-unparsed are
  `pdfs/piaggio_primavera_om.pdf` (5.9 MB, 53 pp, image-only),
  `v2/sympdf/Fiddle_4_Owners_Manual.pdf` and
  `v2/sympdf/Jet_14_Owners_Manual.pdf` (42 MB each, `PdfReadError`), plus
  `honda/grom_service.pdf` (266 pp, image-only). By marque: 14 unidentifiable,
  Honda 7, Lance 7, Roketa 2, SYM 2, Kymco 1, Piaggio 1, Bintelli 1, GTR 1.

## Positive control on Step 0 itself
> **Step 0's door count is UNCHANGED by the positive control.** The three
> blind spots it exposed were closed and re-run, and they surfaced **no fifth
> door**. The count stands at four. Recorded here explicitly because "the
> control found nothing new" and "the control was not run" look identical in
> a document that only reports findings.



Step 0's claim — *"there are exactly four doors"* — is a negative claim, so
under the rule added to `CLAUDE.md` on 2026-09-21 it needs its search
vocabulary stated and a positive control passed. Both were done before this
plan was written.

**Five bypass shapes were planted and the Step 0 grep run against them:**

| shape | caught by the Step 0 grep? |
|---|---|
| A — `FROM known_issues` on one line | caught |
| B — dynamic table name, `f"SELECT * FROM {TBL}"` | **MISSED** |
| C — split string literals, `"... FROM " "known_issues ..."` | **MISSED** |
| D — multi-line SQL, `FROM` and the table on different lines | **MISSED** |
| E — alias/join, `FROM known_issues AS k JOIN ...` | caught |

**So the Step 0 sweep had three blind spots.** They were closed by re-running
the enumeration with an **AST scan** that reads string constants — which
collapses C and D automatically, because Python joins adjacent literals — plus
a separate search for dynamic table names.

**Result: no fifth door.** The AST scan returns the same seven files as the
grep. The dynamic-name search returns 11 sites, of which **10 are false
positives** (docstrings and log messages containing the word *from*) and one
is real: `capture/stats.py:19`, `f"SELECT COUNT(*) FROM {table}{clause}"`. Its
`_count` helper is private, every caller passes a hard-coded literal, and
`known_issues` is not among them — `capture/stats.py` does not appear in the
30 files that name the table at all.

**Answer to "name any door the positive control found that I haven't listed":
none.** The four are all of them. That is now a controlled result rather than
an assertion, and the three blind spots are recorded because the *next* sweep
should start from the AST scan, not the grep.

---

# Plan (v1.0)

## Goal

One function decides whether a corpus row may reach a machine. Every path that
retrieves `known_issues` for prompt, search or prediction purposes calls it. A
structural guard fails the build if anything does not.

## D1. The chokepoint

```python
# knowledge/retrieval.py  (new module)
def rows_for_machine(
    rows, *, make, model, year=None, powertrain=None,
    transmission=None, purpose: Purpose, db_path=None,
) -> list[dict]
```

`Purpose` is a `Literal["prompt", "prediction", "search"]`. It is **required
and positional-by-keyword**, not defaulted, because a default is how door 4
would have been added without anyone deciding what it was.

It resolves the machine once, applies the applicability filter, records what it
withheld, and returns the surviving rows. It does **not** compose, rank or cap
— `compose_prompt_rows` keeps that job and calls this first.

**Why a new module rather than extending `prompt_rows.py`:** `prompt_rows` is
about *which twelve rows reach a prompt*. Three of the four doors do not build
a prompt. Putting the chokepoint there would mean `predict_failures` importing
a prompt-composition module, which is the kind of shape that makes the next
person write their own query instead.

## D2. What each door becomes

| door | today | after |
|---|---|---|
| 1 diagnose / code | `known_issues_for_vehicle` → `compose_prompt_rows` (filtered) | unchanged behaviour; the filter call moves inside `rows_for_machine` |
| 2 video `/ask` | `known_issues_for_vehicle` → `drop_inapplicable` | same, via the chokepoint |
| 3 `predict_failures` | four `search_known_issues` passes, unfiltered | passes through the chokepoint with `purpose="prediction"` |
| 4 `priority_scorer` | own raw SQL, **dead** (F126) | raw SQL deleted; uses the resolver via the chokepoint |

`drop_inapplicable` becomes internal to `retrieval.py`. Nothing outside calls
it directly.

## D3. Door 4 — what it does today, what changes, what proves it

**F126 was fixed on master before this phase opened** (`8e7db70`), because two
of its three defects were bugs rather than findings. So "today" below means
*after* that fix, and the before number this phase measures against is a real
one rather than a row of zeros.

**Today (master).** `_find_kb_matches_safe` returns rows again — the column is
`fix_procedure`, not the non-existent `fix` — and the bare `except Exception`
is narrowed to the one case it was written for, a missing `known_issues` table.
Everything else raises. Measured on the operator's database: **7 of 10
vehicles match** — Road King 5, YZF-R1 5, GSX-R1000 5, SV650 5, KTM 390 5,
ZX-10R 2, CB500 2. **That is the before number.**

**Still wrong, and this phase's to fix:** the match is
`LOWER(make) = ? AND (model IS NULL OR LOWER(model) LIKE '%...%')`. That
substring model matching is the 244C–244I defect, still live on this door
because nobody knew it was a door. It bypasses `known_issue_models`, so a row
whose model column *excludes* a model still matches it — the exact failure
244I's clause-scoped extraction was built to stop — and it applies no
applicability filter at all.

**After.** The raw SQL is deleted. The function calls
`rows_for_machine(purpose="prediction")`: the resolver and its junctions,
tiered matching, and the applicability filter.

**What proves it.** The before number above is already pinned by
`tests/test_f126_priority_scorer_kb_lookup.py` on master. This phase adds:

1. **The same seven vehicles still match** after the rewire — a count change
   here is a real behaviour change and must be explained, not absorbed.
2. **An exclusion case the substring path gets wrong today.** A vehicle whose
   model appears inside an *exclusion clause* of a row's model column
   (244I's `"390/790/890 Adventure — as distinct from 1290 Super Adventure"`
   shape) currently matches via `LIKE` and must not after. This is the
   assertion that proves the door actually moved rather than being wrapped.
3. **The negative**: no `{cvt}` row reaches a Gold Wing through this door, by
   name, per D8.

### D3a. Sequencing constraint — the filter lands in the same commit as the rewire

**Measured first, because the reason matters.** Door 4 does **not** leak
transmission-scoped rows today. Run against master `6298dfd`, the D8 machines
through door 4: Gold Wing, CBR1000RR, Grom, Africa Twin, YZF-R1, Road King,
GSX-R1000, Ninja 400 and CB500 all receive **zero** scoped rows; a Zuma 125
receives 4614, which is correct. Verified **without** the `LIMIT 5`, because
"5 rows returned" against a limit of 5 can hide a sixth — an R1 matches 33
rows unlimited, none scoped.

**But it is safe for the wrong reason, and that reason is about to be
removed.** Door 4 matches `LOWER(make) = ?`, exact string equality. Nine of
the eleven scoped rows carry
`make = "Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine"`, which is never
equal to `"yamaha"`. The 244C–244I defect on this door — the thing D3 exists
to fix — is currently acting as accidental protection.

**So the rewire is what creates the exposure.** The moment door 4 retrieves
through the resolver and its junctions, an R1 becomes eligible for all nine
multi-marque rows. A rewire that lands without the filter would take door 4
from *missing* to *misleading*, which is the one direction this axis forbids.

**The constraint:** the applicability filter lands in the **same commit** as
the door-4 rewire. Never after, not even by one commit.

**Enforced, not written.** The D8 door-4 negative fixtures — R1, Gold Wing and
CBR1000RR **must not receive a transmission-scoped row through door 4** — are
committed **before** the rewire commit. They pass today (door 4 matches
nothing scoped), and they pass after (the filter withholds it). **They fail in
between**, so a later split of rewire from filter fails the suite rather than
merely violating a paragraph.

**One caveat on that, stated because it is the shape of a test that passes for
the wrong reason:** a fixture green both before and after cannot, by itself,
tell the two reasons apart. So the rewire commit carries a **positive
control** — the filter call is removed, the fixture is shown to fail, and the
call is restored — exactly as the F124 and F126 guards did. Without it, these
fixtures would be three more assertions that have never been observed to fail.

## D4. `predict_failures` — the before number ships in the plan or nothing ships

**Measured before any change, on the live database** (the four-pass retrieval,
50 scored predictions):

| machine | Phase 254 rows behind its predictions |
|---|---|
| Yamaha MT07 | **5** — 4614, 4606, 4607, 4608, 4610 |
| Yamaha XS650 | **5** — same |
| Honda GL1800 Gold Wing | **2** — 4606, 4607 |

**The before/after that must be produced during the build, not asserted:** for
a fixed set of machines, the **full 50-prediction list** before and after —
ids, ranks and scores — with every difference attributed to the filter rather
than to a scoring change. **No scoring change ships in this phase.** If the
chokepoint changes the candidate pool enough to reorder predictions, that
reordering is reported as a number and reviewed before merge.

**Refuter.** An independent pass whose brief is to find a machine whose
predictions get *worse* — a case where a withheld row was the one carrying the
right answer. Its finding, or its failure to find one, goes in v1.1.

## D5. The structural guard

`tests/test_phase256_chokepoint.py`, in the orphan-guard style:

* **AST scan first**, not grep — Step 0's positive control showed the grep
  misses dynamic names, split literals and multi-line SQL.
* Fails if any module outside `knowledge/retrieval.py`,
  `knowledge/vehicle_resolver.py` and `knowledge/issues_repo.py` contains a
  `FROM/JOIN known_issues` string constant.
* Fails if `search_known_issues` or `known_issues_for_vehicle` is called
  outside those modules **and** outside the allowlisted search surfaces
  (`api/routes/kb.py`, `cli/kb.py`, `core/search.py`), which are catalogue
  search and take `purpose="search"`.
* **Allowlist entries carry a reason**, and the set is pinned, not the count —
  the F124 lesson.
* **Positive control, run by the test itself:** it plants a bypass module
  containing a raw query, asserts the scanner reports it, and removes it. The
  guard that cannot fail is the thing this phase exists to prevent.

## D6. The persisted withheld record

Migration **064** adds:

```sql
CREATE TABLE retrieval_withheld (
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    provenance TEXT NOT NULL CHECK (provenance IN (
        'explicit','model-sourced','powertrain-default','ambiguous','unknown')),
    purpose TEXT NOT NULL CHECK (purpose IN ('prompt','prediction','search')),
    rows_withheld INTEGER NOT NULL DEFAULT 0,
    retrievals INTEGER NOT NULL DEFAULT 0,
    corrupt_rows INTEGER NOT NULL DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    PRIMARY KEY (make, model, provenance, purpose)
);
```

Written at the chokepoint, upserted per retrieval. **This is the lookup's
to-do list**: every distinct machine resolving `unknown` or `ambiguous`, with
how often and how much it cost. The in-memory `withheld_snapshot` and
`reset_withheld` are **retired**, and their two entries come out of the 209B
orphan allowlist — which is what that allowlist entry asked for when it said
*"retire these or wire that route; do not let the entry sit."*

**Schema bump with zero test edits — proved here.** F124 deleted eleven literal
head-pins for exactly this moment. The build will bump 63 → 64 and run the full
regression; **any test requiring an edit is a defect in F124's work, not a
normal cost**, and will be reported as such.

## D7. F122 — corrupt rows are excluded, not fatal

At **read** time the chokepoint **excludes** a row whose `applicability` cannot
be parsed, logs an error naming the row id, and increments `corrupt_rows` for
that machine. Never unscoped — a typo must not put the row back in front of
every machine. Never a crash — one bad row must not stop diagnosis for
everyone, which is what ships today.

**Loud rejection stays** at seed load (`add_known_issue`) and at every write
path. The asymmetry is deliberate and is the phase's own principle: **at write
time nothing is lost by refusing; at read time refusing costs the technician
their answer.**

**The `CHECK` is viable, with a caveat that changes how it ships.**
`json_valid()` is available and `ALTER TABLE ... ADD CONSTRAINT` was verified
to both parse *and enforce* on SQLite 3.53.2 — checked with a positive control,
because an `ALTER` returning without raising is not evidence that it did
anything. **But the shipped product does not control the user's SQLite
version**, so migration 064 uses the **table-rebuild** path that migrations 051
and 052 already established for `known_issues`, which works on every version.
1,045 rows, three indexes, and **zero rows currently fail `json_valid`**, so
the rebuild is safe.

A `CHECK` cannot validate the JSON *schema* — unknown axis keys and unknown
values still need the pydantic model. It narrows the failure surface; it does
not close it.

## D8. Machine-level regression fixtures, per door, with negatives

Six machines × four doors, each asserting **must receive** and **must NOT
receive**, by row id:

| machine | why it is in the list | must NOT receive |
|---|---|---|
| Honda GL1800 Gold Wing | `ambiguous` (manual/DCT) | any `{cvt}` row |
| Honda CBR1000RR | `unknown`, six-speed | any `{cvt}` row |
| Honda Grom | `unknown`, the Step 0 poster child | any `{cvt}` row |
| Honda PCX 150 | `model-sourced cvt` — the control that must KEEP them | — must receive all 11 |
| Honda Africa Twin | `ambiguous`, column NULL | `{dct}`-only and lever-only rows |
| Kawasaki Ninja 400 | the isolating control | 0 before and 0 after, unchanged |

Every assertion names the machine, so deleting one is a visible edit. Each door
gets the full matrix — **24 assertions**, not one shared helper called four
times, because a shared helper is how door 2 went unfiltered for a phase.


---

## Deviations

### D-1. Four machines are denied a row that names them, by row id

Found by a refuter attacking the door-3 change, not by this phase's own
suite — which asked "does a machine receive rows it may not have" and never
"does a machine miss rows written **for** it".

| machine | row | what the row is | cost |
|---|---|---|---|
| **Kymco Filly LX 50** | **4609** | Kymco's self-contradicting CVT figures | **its rank-1 prediction: critical, confidence 0.747, 3,000 miles overdue** |
| Piaggio Beverly 250 | 4613 | Piaggio's belt limit, three different numbers | rank 5, high, confidence 0.593 |
| Vespa 946 | 4613 | same row | rank 5 |
| SYM Symba | 4615 | the regulator-index methodology | rank 8 |

**No "explicit model match overrides the axis filter" rule was added**, and
that is a decision rather than an omission. Such a rule would make a row's
`model` string authoritative over the sourced lookup — string-naming as
authority, which is the exact pattern this axis exists to replace. **A row
naming a machine is a claim. The lookup is evidence.**

**4609 over-claimed.** It names the Filly because the Kymco Agility service
manual's **recycled header** prints `FILLY LX 50` on 21 of its 183 pages —
which Phase 254 examined and the lookup rejected as unestablished
attribution. The row asserted a machine its own document does not
establish. **4609's model column drops the Filly in 255B.**

**4615's Symba naming is a contradiction on disk** — the row declares
`{"transmission": ["cvt"]}` and names a machine this phase's lookup
classifies `semi_auto_centrifugal` from SYM's own manual. **Resolved by the
255B split**, which Phase 255 already scheduled for that row's general half.

**Beverly 250 and Vespa 946 stay as they are** — closed-unobtainable
(F119), no document on disk.

**The Filly losing its rank-1 critical prediction is the fail-closed cost
made visible.** It is recorded here as a named machine and a named row
rather than as a count, because "some machines lose some rows" is the kind
of summary that lets a real loss pass review.

### D-2. The backfill is not neutral where a tie-break exists

Stated more precisely than the first write-up, which called it "the cap
refilling" and described the length rather than the list:

* Gold Wing, CBR1000RR and Africa Twin each replace a confidence **0.5400**
  row with **0.5333** (id 262) and **0.5000** (id 11).
* **YZF-R1 and XS650 lose id 4614 — critical, confidence 0.8600, at ranks 5
  and 2 — and backfill five mediums at ranks 45–49.**

The removal is correct: 4614 is a CVT recall and neither machine has a CVT.
But the machine trades a high-confidence prediction that was **wrong for
it** against lower-confidence ones that are **right for it**, and that is
the trade, not a neutral swap.

### D-3. `predict_failures` is no longer side-effect free

Its docstring said it was. The chokepoint upserts `retrieval_withheld` for
any machine resolving `unknown` or `ambiguous`. Documented at both ends as
**telemetry, not scoring** — no prediction, rank or score depends on it.

Verified rather than assumed: two calls in one process produce
`retrievals=2` and `rows_withheld=18` against `9` for one call, in **one**
table row, so it accumulates per retrieval and not per call site. On a
read-only database — which is what every rehearsal and close-out dry run
uses, per the operator's standing rule to test against copies — it returns
its 45 predictions and records nothing, silently, at debug level.

## Scope

1. `knowledge/retrieval.py` — the chokepoint.
2. Migration 064 — `retrieval_withheld`, plus the `known_issues` rebuild adding
   the `json_valid` CHECK. `SCHEMA_VERSION` 63 → 64.
3. Four doors rewired.
4. `priority_scorer` repaired first, then rewired (D3's order).
5. `tests/test_phase256_chokepoint.py` — structural guard with its positive
   control, plus the 24 machine-level assertions.
6. Retire `withheld_snapshot` / `reset_withheld`; remove their 209B allowlist
   entries; update the 244U running count.
7. ADR amendment recording the chokepoint and the F122 asymmetry.

## Non-goals

* **No scoring change** in `predict_failures`. Reordering caused by the filter
  is measured and reported, not tuned.
* **No new content rows**, no changes to the lookup beyond what a door needs.
* **No fix for Beverly 250 / Vespa 946 / Filly LX 50** — still open from 255.
* **No mobile transmission field** — that is the phase after 255B.
* **No third axis.** Cooling and final drive stay F117 and F118.
* **255B is still owed** and is not this phase.

## Risks

| risk | handling |
|---|---|
| The filter changes prediction output materially | D4's before/after, plus a refuter; no merge without the numbers |
| Table rebuild on `known_issues` loses data or an index | Copy-first on the live DB, integrity check, rollback tested, three indexes re-asserted by name |
| The guard's allowlist becomes a list of excuses | Pinned set with reasons, and 244U-style running count |
| `purpose="search"` becomes the way to bypass the filter | Search surfaces are allowlisted **by module**, and the guard fails on a new one |

## Verification checklist

- [ ] Positive control passes on the structural guard (planted bypass fires it)
- [ ] All four doors route through `rows_for_machine`
- [ ] `priority_scorer` before-number reproduced, then rewired
- [ ] `predict_failures` before/after produced, refuter reported
- [ ] 24 machine-level assertions, each naming its machine
- [ ] Schema 63 → 64 with **zero test edits** — or the exception reported
- [ ] Corrupt row excluded, logged, counted; loud at write paths
- [ ] `withheld_snapshot` / `reset_withheld` retired and de-allowlisted
- [ ] Regression green, **with commit hash and collected count**

---

## Results (v1.1)

### What shipped

| piece | where |
|---|---|
| The chokepoint, `purpose` required with no default | `knowledge/retrieval.py` |
| `retrieval_withheld` + `json_valid` CHECK on `known_issues` | migration 064 |
| Four doors routed through it | `cli/diagnose.py`, `api/routes/videos.py`, `advanced/predictor.py`, `shop/priority_scorer.py` |
| Structural guard + self-excluding-rows guard | `tests/test_phase256_chokepoint.py` |
| `motodiag kb withheld` — the lookup's to-do list | `cli/kb.py` |
| In-memory counter retired, de-allowlisted | `knowledge/transmission.py`, 209B, 244U |

`SCHEMA_VERSION` 63 → 64. **Regression `c8a0e16`: 7,964 collected, 7,964
passed, 0 failed, 0 skipped, 30:40.** F9 lint clean, 244G clean.

### One chokepoint, proved rather than asserted

A **single** mutation — the filter in `rows_for_machine` made a no-op —
fires **all fifteen** machine assertions, five machines across three doors.
Per-door controls: doors 1+2 ten failures, door 3 five (six when the call
is deleted, the extra being the wiring assertion), door 4 five.

### The doors

| door | before | after |
|---|---|---|
| 1 diagnose / code | filtered (255) | via chokepoint |
| 2 video `/ask` | filtered (255 bug fix #1) | via chokepoint, and now caps **after** filtering |
| 3 `predict_failures` | **unfiltered** — MT07 carried 5 scooter-CVT rows, Gold Wing 2 | via chokepoint, pre-scoring |
| 4 `priority_scorer` | **dead since written** (F126) | via chokepoint, raw SQL deleted |

### Door 3 — no scoring change, shown as a diff

421 predictions across 9 machines. **21 rows removed, all
transmission-scoped, zero non-scoped. Every scoring field identical for
every survivor. Relative order preserved on every machine.**

**The evidence is committed, not summarised**:
[`256_predictions_before.json`](256_predictions_before.json) and
[`256_predictions_after.json`](256_predictions_after.json) hold every
prediction — rank, issue id, title, severity, confidence, miles-to-onset
and match tier — so the claim above can be re-derived rather than trusted. The MT07 drops
50 → 45 because it ran out of candidates; the rest backfill from below the
50-cap. See Deviations D-2 for why that backfill is not neutral.

### F124's promise, collected

The 63 → 64 bump needed **zero test edits** — 747 tests across the eleven
files that used to require one each, `git diff tests/` empty. That bump
cost five discovery passes last time.

### Four variations of one error, in one day

Each was *a guard that cannot observe the thing it claims to guard*, and
**each was caught by a positive control, none by reading the code**:

1. The old `LIMIT 5` masking a door-4 leak — caught while checking whether
   F126's fix reopened it.
2. **My own door-4 tripwire, an hour later**, capping and filtering in one
   expression, so it read five rows while the scoped rows sat at positions
   56–115. It passed on leaking code.
3. `GUARD_FETCH = 400` — safe by arithmetic until the corpus grows.
   Measured: worst match 165 rows, unlimited costs 17.6 ms against 17.6 ms.
   The caps were doing no work.
4. My door-3 fixture rebuilding the candidate pool itself, so bypassing the
   filter *inside* `predict_failures` left all 60 assertions green.

### What the refuter found that no guard here could

All four verified before acting. The sharpest: **rows that name a machine
and are then withheld from it** — every guard in this file asks whether a
machine *receives* rows it may not have; none asked whether a machine
*misses* rows written for it. Four cases, recorded in Deviations D-1 by
machine and row id.

It also disproved a docstring written with some confidence — `rows_withheld`
is the cost of not knowing, **not** what sourcing recovers; sourcing a Grom
recovers zero — and caught that `predict_failures` had begun writing to the
database while its docstring called the pipeline side-effect free.

### Known limits carried forward

1. **Four rows name a machine they exclude.** Guard is permanent; 4609 and
   4615 resolve in 255B, the other two are closed-unobtainable.
2. **Alias matching is exact.** `Piaggio / Primavera 150` resolves
   `unknown` where `Vespa / Primavera 150` is sourced, and `PCX 150 ABS`
   misses `PCX 150`. The no-fuzzy-matching decision is Phase 255's and
   stands; the cost is now visible.
3. **A fully-withheld candidate pool returns `[]` before recalls are
   fetched.** Not reachable today — minimum survivors by make are SYM 5,
   Genuine 6, Kymco 6, Vespa 8, Piaggio 9 — but it becomes reachable if a
   marque's rows are ever all scoped.

### Non-goals held

No scoring change. No content rows. No lookup changes beyond what a door
needed. No third axis. **255B is still owed**, and now owes three specific
things: the 4609 model-column fix, the 4615 split, and the PCX generic-layer
question.
