# Phase 272 — Gate 15: Track N's five workflows walked end-to-end through the workflow door — phase log

**Status:** 🚧 In progress
**Branch:** `phase-272` (Opus session, main checkout)

---

### 2026-09-26 — Opened: Gate 15, test-only

The operator's prompt, 2026-09-26: start Phase 272, Gate 15, the Track N
integration test, and run it to its finish line. The last session's
state is `docs/handoffs/2026-09-26_262_closed.md`. Tests and documents
only: no production code, no migration, no change to the live database.

**The operator's decision, recorded verbatim:**

> option 1, test-only gate, with three conditions:
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

**The operator's stop condition:** "If Step 0 finds the walk cannot be
written without production code, or anything else that needs a
decision, stop and give me the options."

**Carried forward** (the operator's list): no test reads
`data/motodiag.db`; no literal pin of the schema head (F124); the
whole-tree gates before every commit, including the 244G scanner over
the new test file; the Edit tool for source edits; scratch files out of
`/tmp`; commit messages through a quoted heredoc. Regression by
`.claude/skills/closeout/regression.sh`.

Row 272 went 🚧 before Step 0, with its text corrected per condition 1.

### 2026-09-26 — Step 0

`272_step0.md`. The operator's five measured points all re-verify
(S0-1). The walk needs no production code (S0-2). The link census finds
22 slug references (16 distinct links, 22 resolving), 1 slug-with-item
reference and 12 same-template item references, and 0 references in any
other form (S0-3).

**One decision, taken here and not a stop** (S0-4, v1.0 D1): the
title-vocabulary rule for wrong-powertrain steps finds one live
violation, `generic_ppi_v1` item 3, a required "Engine compression test"
in a template that covers electric. Fixing it is a migration, which the
operator excluded. Recorded as the rule's exact, measured exception and
filed (F166), as Gates 13 and 14 did with every gap they measured. Why
this is not a stop under rule 1: no second plan ships different code;
the operator's rule, controls and conditions are unchanged; the
alternative (the migration) is outside the scope the operator set.

### 2026-09-26 — v1.0 committed and pushed

`17284af`: Step 0, v1.0, row 272 🚧 with its corrected text, rows 356
and 357 (🔲, after 355), F165 and F166. Four whole-tree checks green
before the commit (58 passed; `finding_check.py` exit 0). Pushed as
`phase-272`.

### 2026-09-26 — Build: `tests/test_phase272_gate15.py`

**One defect in the new file before its first commit, not a bug-fix
entry** (the file had never been committed): the first run gave 10
failed and 10 errors, all `OperationalError('no such table:
workflow_templates')`. The helper passed the database through
`CliRunner(env=…)`, but `reset_settings()` rebuilds the settings at
once, before CliRunner applies its env, so the CLI read conftest's
default database. Fix: the helper sets `MOTODIAG_DB_PATH` and `COLUMNS`
through a scoped `pytest.MonkeyPatch`, then resets, and resets again
after. Then 29 passed.

**What the walk read**, all from printed text, schema 71:

| powertrain | walked (in the row's order) | skipped |
|---|---|---|
| ice | all nine: `generic_ppi_v1`, `ppi_engine_v1`, `ppi_chassis_v1`, `tire_service_v1`, `generic_winterization_v1`, `winterization_v1`, `de_winterization_v1`, `valve_adjustment_v1`, `brake_service_v1` | none |
| electric | six: `generic_ppi_v1`, `ppi_chassis_v1`, `tire_service_v1`, `winterization_v1`, `de_winterization_v1`, `brake_service_v1` | `ppi_engine_v1`, `generic_winterization_v1`, `valve_adjustment_v1` (the valve-adjustment stage is empty) |
| hybrid | all nine, as ice | none |

W4 finds exactly `('electric', 'generic_ppi_v1', 3)`, the F166 step.
The link census from the printed `show` output equals Step 0's from the
rows: 15 listed templates, 22 slug references, 16 distinct links, 8
source templates; 13 item-reference matches (29 item numbers once
ranges are expanded), 1 of them cross-template
(`de_winterization_v1` → `winterization_v1` item 7); **0 broken**. The
walks print 57 outputs, 318,015 characters, with 0 build references.

Two tightenings before the commit: W3 now also checks each parsed
title and required flag against the repository's row, since W4 reads
both from the print; and a weak `>= 1` item-reference assertion became
the specific cross-template reference.

`c7ba345`: 29 passed (12.3 s). Four whole-tree checks green (58
passed; finding exit 0); 244G's scanner over `tests/` found 0; the F124
guard, 9 passed.

### 2026-09-26 — The operator's planted controls, in the gate's own fixture

Each plant was one line added to the module fixture `gate_db` after
`init_db(path)`, then the whole file run with `python -B -m pytest -q
-p no:cacheprovider tests/test_phase272_gate15.py`, then the line
removed with the Edit tool. After each removal `git diff` against
`c7ba345` was 0 lines. Outputs saved in the session scratchpad
(`plant1.txt`, `plant2a.txt`, `plant2b.txt`, `plant3.txt`).

**Plant 1: a broken template link.**
`UPDATE checklist_items SET diagnosis_if_fail = replace(diagnosis_if_fail,
'brake_service_v1', 'brake_servce_v1') WHERE sequence_number = 6 AND
template_id = (… 'de_winterization_v1')`. Red, **2 failed, 27 passed**:

```
E   AssertionError: assert [('de_winteri...e_servce_v1')] == []
E     Left contains one more item: ('de_winterization_v1', 'brake_servce_v1')
FAILED tests/test_phase272_gate15.py::TestTheLinks::test_the_check_finds_the_known_links
FAILED tests/test_phase272_gate15.py::TestTheLinks::test_every_link_resolves
```

The known-links test failed too, because `de_winterization_v1` now
named six templates, not five. Removed; diff 0 lines.

**Plant 2a: a valve-adjustment step on an electric walk.**
`INSERT INTO checklist_items (…) SELECT id, 8, 'Valve clearance — check
and adjust', 'Measure each valve with a feeler gauge.', 'Within spec',
'Out of spec', 1 FROM workflow_templates WHERE slug =
'brake_service_v1'` (brake service covers electric). Red, **1 failed,
28 passed**:

```
E     Extra items in the left set:
E     ('electric', 'brake_service_v1', 8)
FAILED tests/test_phase272_gate15.py::TestTheWalk::test_no_required_step_names_work_its_powertrain_lacks
```

Removed; diff 0 lines.

**Plant 2b: valve adjustment made to cover electric.**
`UPDATE workflow_templates SET applicable_powertrains =
'["ice","electric","hybrid"]' WHERE slug = 'valve_adjustment_v1'`. Red,
**1 failed, 28 passed**:

```
E     Extra items in the left set:
E     ('electric', 'valve_adjustment_v1', 1)
E     ('electric', 'valve_adjustment_v1', 2)
FAILED tests/test_phase272_gate15.py::TestTheWalk::test_no_required_step_names_work_its_powertrain_lacks
```

W2 stayed green, as it should: it reads applicability from the print,
and the print now named electric. Only items 1 and 2 are caught: the
other six titles name the method (feeler gauge, screw and lock nut,
shims) and not the engine. The gate fails either way, but the
vocabulary's reach is the title (v1.0 Risks). Removed; diff 0 lines.

**Plant 3: a build reference in a walked template** (F158's control).
`UPDATE checklist_items SET instruction_text = instruction_text || '
See F166.' WHERE sequence_number = 2 AND template_id = (…
'tire_service_v1')`. Red, **1 failed, 28 passed**:

```
E   AssertionError: assert ['F166', 'F166', 'F166'] == []
FAILED tests/test_phase272_gate15.py::TestNoBuildReferences::test_the_walks_print_none
```

Once per powertrain's walk, since tire service is on all three.
Removed; diff 0 lines. The file then ran 29 passed (11.9 s).

The same plants stay in the file as permanent checker tests on their
own fresh databases: `test_a_misspelt_slug_is_caught`,
`test_a_link_to_an_inactive_template_is_caught`,
`test_an_item_that_does_not_exist_is_caught`,
`test_a_valve_adjustment_step_on_an_electric_walk_is_caught`,
`test_valve_adjustment_made_to_cover_electric_is_caught`,
`test_a_planted_reference_is_caught`, and
`test_a_motorcycle_model_is_not_a_finding` (BMW F800R, 95 °F).

### 2026-09-26 — Mutations: 7/7 red

Run from a scratch script that imports the committed test module and
mutates in memory, never the file; each restored and re-run green.

| # | mutation | check | result |
|---|---|---|---|
| M1 | migration 070's `rollback_sql` set to `SELECT 1;` | peel to 69 | red |
| M2 | 071's rollback keeps its two DELETEs, drops its five UPDATEs restoring the F161/F162/W30 rows | peel to 70 | red (row content is compared, not presence) |
| M3 | one item title differs between two databases | fresh-database equality | red |
| M4 | the powertrain parser drops one value | W1 | red (`generic_ppi_v1`) |
| M5 | the `show` parser ignores "(optional)" | W3 | red (`tire_service_v1 item 4`) |
| M5 | the same | W4 | red |
| M6 | the walk skips nothing | W2 | red |

A first M2 attempt split the SQL on `;` and broke a string literal
(`OperationalError: near "%"`); it was cut at the first `UPDATE` instead.

### 2026-09-26 — Floor

`--collect-only -q`: 9,507. `COLLECTED_TEST_FLOOR` 9478 → 9507 (+29,
this file). The floor test, the four whole-tree checks and B2 over
`in_progress/` were green (60 passed; finding exit 0; 244G 0; B2 `[]`).
