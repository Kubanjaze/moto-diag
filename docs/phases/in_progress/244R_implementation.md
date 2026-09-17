# Phase 244R — The DTC taxonomy can hold content

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-17

---

## Goal

`motodiag code --category engine` answers **"No DTCs found in category 'engine'."**
There are 29 engine codes in the table. Nineteen of the twenty categories
behave this way; the twentieth, `unknown`, returns all 99 rows, because that
is where every row actually sits.

One omitted keyword argument does it. `knowledge/loader.py:65-72` builds
`DTCCode(...)` without `dtc_category`, the field defaults to
`DTCCategory.UNKNOWN` (`core/models.py:201-204`), and `dtc_repo.add_dtc`
faithfully persists it. `load_dtc_file` is the only production writer of
`dtc_codes`, so the defect is one choke point and 99 rows.

This phase makes the taxonomy able to hold content, which is the precondition
for roadmap row 247 (motor controller / inverter faults) — six EV categories
have been seeded and advertised since Phase 111, and a phase that authored EV
codes today would ship them into a column nothing can query.

Numbered **244R**: the 244-letter series is this project's corrective series,
and this is corrective work found by the Track L readiness audit. It lands
before 245.

## Step 0 — findings

Run as eight agents: four designs, each adversarially checked. Three of the
four designs were broken by their checker; this one survived with six
corrections, all folded in below. The other three subjects became the
follow-on phases in **Non-goals**.

**S0-1. The defect, and why 6,692 tests missed it.** Three test modules do
load the real seed corpus through the real loader
(`tests/test_phase05_dtc.py:117-147`, `tests/test_phase240_gate12.py:63`),
but none asserts anything about `dtc_category`. Every test of `--category`
and of `get_dtcs_by_category` builds synthetic `DTCCode` objects with
`dtc_category` passed by hand (`tests/test_phase124_code.py:66-110`,
`395-420`; `tests/test_phase111_kb_schema_expansion.py:179-196`). The seam
between authored data and the filter was never crossed by a test.

**S0-2. `unknown` is a category too.** `dtc_category_meta` holds 20 rows and
one of them is `unknown` (migration 004, `core/migrations.py:124`), so
`--category unknown` returns the whole table today. A typo
(`--category nonsense`) and a correct query on an empty category are
byte-identical: both print the same "No DTCs found" line. **The plan's
success is not only "categories return rows" but "a wrong category says so".**

**S0-3. 🚨 The taxonomy contradicts itself, on exactly the rows a
demonstration would use.** The shipped `dtc_category_meta` describes
`exhaust` as covering O2 sensors, catalyst and secondary air; the
`DTCCategory` enum comment (`core/models.py:166` vs `:169`) assigns O2, PAIR
and catalyst to `emissions`. Two authorities in this repo give opposite
answers for P0420/P0430/P0131/P0132/P0444. **This must be resolved before a
single row is authored** — see Scope 1.

**S0-4. Neither mechanical source of values works.** Measured, not guessed:
- Copying the legacy `category` column classifies 76/99. The other 23 —
  `electrical` (18) and `idle` (5) — are `SymptomCategory` members that do
  not exist in `DTCCategory` and have no `dtc_category_meta` row. Nothing in
  `src/` ever constructs a `DTCCategory` from a row (`dtc_repo.py:282-292`
  returns `dict(row)`), so those values would not fail loudly; they would sit
  in the column joining to nothing. It is also lossy: all 20 legacy `exhaust`
  rows mix real exhaust faults with EVAP, catalyst and O2.
- Deriving from the code prefix puts **0 rows** in `engine` and **0** in
  `cooling`, pushes the whole P03xx misfire family into `ignition`, and
  leaves 8 Harley P1xxx codes as "manufacturer_specific"
  (`engine/fault_codes.py:55-63`, `:135-136`). The EV prefixes cannot help
  either: Phase 244 already recorded that `HV_`/`MC_`/`BMS_` is an internal
  namespace no manufacturer emits (`fault_codes.py:196-219`).

So the values are **authored per row in the seed JSON**, which is the only
source that can be reviewed.

**S0-5. The loader's writes are not atomic, per file.** `load_dtc_file`
pre-deletes inside one committed transaction (`loader.py:48-61`) and then
inserts row by row (`:63-75`). A bad enum value raises out of the constructor
*after* the deletes have committed, leaving that make's codes deleted and not
re-inserted. Adding a value that can raise makes this reachable, so the fix
has to make the load parse-then-write.

**S0-6. The CLI contradicts itself in two directions, and a partial fix only
changes the shape of it.** `motodiag code P0440` prints "Category: exhaust"
from the legacy column (`cli/code.py:195`) while `--category` narrows on
`dtc_category` (`:362-364`). Fixing only the filter means the panel and the
list disagree about the same row.

**S0-7. The API filters the other column, and cannot see this fix at all.**
`GET /v1/kb/dtc?category=` narrows on legacy `category`
(`dtc_repo.py:144-146`), and `DTCResponse` has no `dtc_category` field
(`api/routes/kb.py:188`), so the mobile client holds 20 advertised categories
and DTC rows carrying a different vocabulary. Converging them changes the
`/v1/kb/export` content hash (`kb.py:290`) and the OpenAPI contract that
Gate 11 pins against the app's committed snapshot. **Out of scope here** —
see Non-goals.

**S0-8. A schema bump is a ten-pin job here, plus Gate 9.** Phase 209D's
close-out found ten `SCHEMA_VERSION == N` pins spelled two ways; Gate 9's
(`tests/test_phase184_gate9.py:591`) is one of them and its own comment
requires the reason to be appended when bumped.

**S0-9. A data-writing migration needs Phase 244H's warning attached.**
`tests/test_phase244H_test_db_isolation.py:1-11` records a regression run
applying migrations to the operator's real database twice in one day: *"Both
were correct, which is why nobody noticed."* Migration 062 writes data, so
the plan states its blast radius and its idempotence explicitly.

## Scope

1. **Declare the authority, then author 99 values.**
   `dtc_category_meta` wins: it is what the CLI joins against, what
   `/v1/kb/dtc/categories` and `/v1/kb/export` serve to the app, and what a
   reader can inspect at runtime. The `DTCCategory` enum comment is corrected
   to match it in the same commit, so the two stop disagreeing. Every one of
   the 99 entries across the 8 files in `seed/dtc_codes/` gains an authored
   `dtc_category`, with the mapping rationale recorded in the phase log —
   including the 23 rows the legacy column could not answer.
2. **The loader reads it, tolerantly, and writes atomically.**
   `dtc_category=DTCCategory(item.get("dtc_category", "unknown"))`, matching
   the tolerant style of every neighbouring field so the four existing
   fixture-based tests keep passing. `load_dtc_file` builds and validates
   every `DTCCode` for a file **before** deleting anything (S0-5).
3. **Migration 062 backfills the operator's rows**, via a `post_apply` hook
   that reads the seed files and issues one `UPDATE ... SET dtc_category`
   per code, matching on `(code, make)`. Ids are untouched, which is why this
   is safer than telling the operator to re-seed. Rollback returns every row
   to `unknown`. `SCHEMA_VERSION` 61 → 62, and all ten pins plus Gate 9's are
   updated with the reason.
4. **The CLI stops contradicting itself and stops lying about typos.**
   - `motodiag code <CODE>` shows the DTC category, with the symptom
     category labelled as what it is.
   - `--category` validates its argument against `dtc_category_meta`: an
     unknown value says so and lists the valid ones, instead of reporting an
     empty category. This is what makes S0-2's silence impossible.
5. **Tests, through the command a user runs**, not through synthetic rows:
   - a corpus guard: every seed entry carries a `dtc_category` that
     constructs, and the count is pinned at 99 so a new file cannot arrive
     uncategorised;
   - the real corpus through the real loader: zero rows left `unknown`;
   - parametrised over every category the corpus claims: `motodiag code
     --category X` returns rows;
   - the negative, written as intent: the six EV categories return nothing
     **because no EV DTC data exists** — 244R does not invent any;
   - a referential guard: every distinct `dtc_category` value is a
     `dtc_category_meta` primary key;
   - migration 062 forward and back, asserting id stability;
   - a typo prints the valid list;
   - the panel and the list agree about the same code.

## Non-goals

Each is a follow-on phase or ticket, recorded so the next one starts from
here rather than rediscovering it.

- **The API's filter column and `DTCResponse.dtc_category`** (S0-7). It
  changes the mobile contract Gate 11 pins and the `/kb/export` hash; it
  deserves its own phase with the app's refresh in the same commit.
- **244S — retrieval convergence.** `kb list` and `diagnose` bypass the
  vehicle resolver. Its Step 0 already found the blocker: the two paths
  return different row shapes, and the resolver returns an identity tuple.
- **244T — safety at the moment it matters.** `SafetyChecker` has no caller.
  Its Step 0 broke the obvious electric-detection design in both directions
  (Harley classified electric; LiveWire missed as a Harley model), and the
  alert-rate measurements need an operator decision.
- **244U — the reachability gate's blind spot.** 117 definitions across 42
  modules are hidden from the 209B gate by re-exports and `__all__`. The
  obvious half of that fix is a measured no-op.
- **Recalls.** `motodiag recalls` queries a table nothing ever seeds — a
  safety lookup that reports "no recalls" for every bike. Filed, not fixed
  here.
- **No new DTC content**, EV or otherwise. This phase classifies what exists.

## Verification Checklist

- [ ] `dtc_category_meta` is named as the authority, and the enum comment no longer disagrees with it
- [ ] All 99 seed entries carry an authored `dtc_category`; the 23 the legacy column could not answer are listed in the phase log with reasons
- [ ] The loader reads the key tolerantly — the four existing fixture tests still pass untouched
- [ ] A bad value in one seed file deletes nothing (parse-then-write)
- [ ] After `motodiag db init`, zero rows read `unknown`
- [ ] `motodiag code --category engine` returns the engine codes; parametrised over every populated category
- [ ] The six EV categories return nothing, and a test says why
- [ ] `motodiag code --category nonsense` reports an invalid category and lists the valid ones
- [ ] `motodiag code P0440` and `--category <its category>` agree
- [ ] Every `dtc_category` value present in the table is a `dtc_category_meta` key
- [ ] Migration 062 forward: all rows classified, `dtc_codes.id` unchanged
- [ ] Migration 062 rollback: every row reads `unknown` again
- [ ] Ten `SCHEMA_VERSION` pins plus Gate 9's updated with the 61→62 reason
- [ ] Applied to a copy of production: 99 rows classified, integrity ok, no other table touched
- [ ] Mutations: drop the loader kwarg; make the key required; copy the legacy column instead; skip the backfill; remove the category validation; break the parse-then-write ordering — each caught
- [ ] 209B reachability gate still passes; f9 lint clean; full regression green

## Risks

- **Authoring 99 values is judgement, not mechanism.** Mitigated by naming
  one authority (S0-3), recording the rationale per group, and a referential
  guard that fails if a value does not exist in the meta table.
- **A data-writing migration on the operator's live database** (S0-9). It
  updates one column, keyed by `(code, make)`, is idempotent, and is verified
  on a copy of production before it goes near the original.
- **The migration pins the seed data as of apply time.** A later edit to a
  seed file does not re-run 062; only `motodiag db init` picks it up. Stated
  here so nobody later assumes the column stays in sync by itself.
- **The CLI and API will still disagree** until the API phase lands. The
  plan says so rather than leaving it to be discovered.
