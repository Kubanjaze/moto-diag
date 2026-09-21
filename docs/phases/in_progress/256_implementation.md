# Phase 256 — The retrieval chokepoint

**Version:** DRAFT (Step 0 only — NOT v1.0) | **Tier:** Standard | **Date:** 2026-09-21

> **This document is a draft.** It contains Step 0 findings and nothing else.
> No plan, no decisions, no scope. v1.0 is written only after the operator
> reviews Step 0. Committed at this stage so the findings live in the repo
> rather than in a chat transcript.

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

## Not decided here

Scope, the chokepoint's signature, the persisted table's schema, whether
`predict_failures` is refactored in this phase or after its before/after
measurement, and the migration number. **All of that is v1.0, and v1.0 is not
written until Step 0 is reviewed.**
