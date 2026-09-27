# Phase 272 — Gate 15: Track N's five workflows walked end-to-end through the workflow door

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-27 (v1.0 2026-09-26)

---

## Goal

Row 272, as it read before this phase: "Gate 15 — Specialized workflows
integration test. Run PPI → tire service → winterization → valve adjust
→ brake service end-to-end". Track N's closing gate.

**No workflow can be run** (`272_step0.md`, S0-1): `motodiag workflow`
has `list` and `show`; no table holds a run or an item's result; Phase
82's step engine is not connected to the templates; the CLI is the only
door. The operator chose a test-only gate, with three conditions, given
verbatim:

> 1. correct gate 15's roadmap row: it verifies the five workflows walk
>    through end-to-end via workflow list/show, per powertrain, with every
>    template link resolving — it does not claim they "run". the row
>    can't say something nothing does.
> 2. positive control on the walk: plant a broken template link and a
>    wrong-powertrain step (valve adjustment on an electric), show the
>    gate fails on each, then remove them.
> 3. "a workflow can't be run" is filed as a finding AND named as a
>    specific phase on the roadmap (the in-memory runner, option 2's
>    scope), not left as "future". saved runs (option 3) come after that,
>    as their own phase with the migration.

Tests and documents only: no production code, no migration, no change to
the live database.

## Logic

One test file, `tests/test_phase272_gate15.py`, over one freshly
migrated database per module (never `data/motodiag.db`):

1. **The walk.** For each powertrain (ice, electric, hybrid), one pass
   through the row's order with `CliRunner` against the real CLI root:

   | stage | templates, in order |
   |---|---|
   | PPI | `generic_ppi_v1` → `ppi_engine_v1` → `ppi_chassis_v1` |
   | tire service | `tire_service_v1` |
   | winterization | `generic_winterization_v1` → `winterization_v1` → `de_winterization_v1` |
   | valve adjustment | `valve_adjustment_v1` |
   | brake service | `brake_service_v1` |

   For each stage, `workflow list --category <c>` (the category is read
   from `show`) and, for each template, `workflow show <slug>`.
   Applicability is read from the printed text only: `list`'s
   Powertrains cell (wrapped lines joined) and `show`'s "for …" header.
2. **The per-powertrain rule**, asserted as a rule:
   - *W1:* `list` and `show` print the same powertrains for a template.
   - *W2:* powertrain P's walk visits, in the row's order, exactly the
     row's templates whose printed powertrains name P; the rest are
     listed but not walked.
   - *W3:* every walked template's `show` exits 0 and prints its items
     numbered 1…n without a gap, each with a Pass and a Fail line.
   - *W4:* on P's walk, no **required** step's title names work P does
     not have: engine work on an electric walk, traction-battery work on
     an ICE walk (vocabularies in S0-4). A template covering powertrains
     with and without that work carries the step as optional.
   - *W4's measured exception:* the violations are exactly
     `generic_ppi_v1` item 3 (F166, S0-4), so the check fails on any new
     one and again the day that one is fixed.
3. **The links.** Every reference in every live template's printed
   `show` output, in the forms S0-3 censused (slug; slug with item; item
   within the same template), resolves: a slug to a template `workflow
   list` prints, an item number to an item `show` prints. The check
   first finds the known links (de_winterization_v1's five, the PPI and
   winterization chains, the census counts) before it is trusted to find
   none broken.
4. **Breadth.** The union of `list --category c` over every category the
   `--category` option offers equals `workflow list`, equals the active
   templates the repository returns, and every one of them `show`s.
5. **No build reference in the walk's output** (F158), with the four
   patterns 262 used, and a planted control.
6. **Migrations from 067 on.** Two fresh databases are identical in
   `workflow_templates` and `checklist_items` (schema and rows, the
   timestamp columns aside). For every version *v* from 66 to the head
   minus one, rolling a fresh head database back to *v* gives the same
   workflow tables as a database built only up to *v*. Neither check
   names 71: both take the head from `SCHEMA_VERSION`, so the next
   migration joins them.

## Key Concepts

- **The front door is the evidence.** Applicability, links and item
  numbers are read from what the CLI prints, not from the repository
  layer, as Gates 12–14 did. The repository is used only as the
  independent count for breadth.
- **Titles carry the powertrain rule.** Items have no powertrain; a
  step's title names its work. The body text names engine words
  incidentally (master cylinder, fork compression damping), so a
  body-text rule would need an exception list; the title rule needs
  one measured exception.
- **An exclusion needs a control.** The walk skips templates that do not
  name P; W4's exception excludes one step. Both have planted cases they
  must not hide.

## Decisions

**D1. The gate reports; it does not repair.** `generic_ppi_v1` item 3 is
a required engine compression test in a template that covers electric.
Fixing it is a migration; this gate has none. Pinned as W4's exact
exception and filed (F166), as Gates 13 and 14 did with their gaps
(258's D1).

**D2. Cross-powertrain links resolve and are recorded, not failed.**
`generic_ppi_v1` and `ppi_chassis_v1` point at `ppi_engine_v1` on the
electric walk; it resolves and prints "for ice, hybrid". The operator's
condition is that every link resolves.

**D3. The planted controls are temporary edits to the gate's own
fixture**, run, captured red, and reverted, recorded in the phase log
with the failing output. Each also has a permanent unit test that feeds
the checker a planted input, so the checkers stay proven after the
plants are gone.

**D4. Rows 356 and 357 go in before the finding is filed**, so the
finding's row numbers resolve.

## Non-goals

- Running a workflow, saving a run, or any `--powertrain` option: rows
  356 and 357.
- Fixing `generic_ppi_v1` item 3 or item 4 (F166), or anything in F163.
- An API route or a mobile screen for workflows.

## Planned items

1. Row 272 🚧, corrected per condition 1, saying what it read before.
2. Rows 356 (in-memory workflow runner) and 357 (saved workflow runs,
   its own migration, after 356), both 🔲, after 355.
3. F165 (a workflow can't be run; names 356 and 357) and F166 (the
   required engine step on the electric walk).
4. `tests/test_phase272_gate15.py`, sections 1–6 of Logic.
5. Planted controls, each red then removed: a broken template link; a
   wrong-powertrain step (a valve adjustment step on an
   electric-covering template, and `valve_adjustment_v1` made to cover
   electric); a build reference in a walked template.
6. `COLLECTED_TEST_FLOOR` raised to the new count.
7. Close-out: v1.1, row 272 ✅, history row, handoff.

## Verification Checklist

- [x] Row 272 🚧 before Step 0; corrected text within 120 words (56 at v1.0)
- [x] Rows 356 and 357 added; `roadmap_check.py` green
- [x] F165 and F166 filed; `finding_check.py` green, B2 over `in_progress/` `[]`
- [x] Each powertrain's walk green, with its visited and skipped templates recorded (phase log, Build)
- [x] The link check finds the 16 known links, de_winterization_v1's five among them, before finding none broken
- [x] Broken-link plant red (2 failed), removed
- [x] Wrong-powertrain plant red in both shapes (W4), removed
- [x] Build-reference plant red, removed
- [x] Migrations: fresh databases identical; every rollback from 66 to the head peels its successors, equal to a database built to it; no literal 71
- [x] 244G scanner over `tests/` (0); the four whole-tree checks green; F124 guard green
- [x] Mutations 7/7 red
- [x] Regression of record by `regression.sh`: 9507 passed at `5750985`
- [x] Handoff written

## Deviations from Plan

- **Planned item 6 (floor) and the planted controls ran as planned.** No
  production code, no migration, no live change.
- **The CLI helper sets the environment before resetting settings**, not
  through `CliRunner(env=…)`: `reset_settings()` rebuilds the settings at
  once, so the first draft read conftest's default database (10 failed,
  10 errors, before the file's first commit). Not a bug-fix entry: the
  file had never been committed.
- **W3 grew two assertions** not in v1.0: each parsed title and required
  flag equals the repository's row, because W4 reads both from the
  print. Mutation M5 shows why: with "(optional)" ignored, W4 alone
  would report a false violation set.
- **The walk runs at a wide console** (`COLUMNS=10000`, the documented
  test hook in `theme.get_console`) so item titles do not wrap; one test
  reads `list` at 80 columns and proves the wrapped table parses to the
  same powertrains. v1.0 said the parser joins wrapped lines; it does,
  and that is now the 80-column test.
- **Mutations were added** (7, v1.0 listed only the plants): M1–M6 in
  the phase log.
- **Plant 2b catches `valve_adjustment_v1` items 1 and 2 only**: the
  other six titles name the method, not the engine. The gate still
  fails; the title vocabulary's reach was a v1.0 risk, now measured.

## Results

| | |
|---|---|
| Test file | `tests/test_phase272_gate15.py`, 29 tests |
| Walks | ice 9 of 9; electric 6 of 9 (skips `ppi_engine_v1`, `generic_winterization_v1`, `valve_adjustment_v1`); hybrid 9 of 9 |
| W4 | exactly `('electric', 'generic_ppi_v1', 3)`, F166 |
| Links | 22 slug references, 16 distinct links, 8 source templates; 13 item references, 1 cross-template; 0 broken |
| Breadth | 15 live templates = the union of `list --category` over 13 categories = `list` = the repository |
| F158 | 57 outputs, 318,015 characters, 0 build references |
| Migrations | fresh databases identical; rollbacks to 66–70 each equal a database built to that version |
| Planted controls | 4 runs, each red, each removed (`git diff` 0 lines) |
| Mutations | 7/7 red |
| Findings | F165 (a workflow can't be run; rows 356, 357), F166 (`generic_ppi_v1`'s engine steps on electric) |
| Floor | 9478 → 9507 |
| Regression of record | **9507 passed, 0 failed, 0 skipped, 0 errors** at `5750985` (11 min 15 s wall, `python -m pytest -n auto --dist load`, exit 0) |

Key finding: **the row asked for a run, and the door only reads.** The
walk proves every Track N protocol on the row's path can be read in
order, per powertrain, with its links intact; it cannot prove a
mechanic can work one through. And reading per powertrain found the one
step no earlier phase had looked at from the electric side: the starter
PPI's required compression test.

## Risks

- **Parsing a Rich table.** A layout change in `list` would break the
  parser, not the product. Mitigated: the parser is checked against the
  repository's powertrains for every template (W1 plus breadth), so a
  mis-parse fails loudly rather than passing an empty walk.
- **A title vocabulary misses a wrong step whose title names no engine
  work** (`generic_ppi_v1` item 4, "Fluid inspection", S0-4). Stated in
  F166, not claimed covered.
