# Phase 264 — Track N batch 2: winterization, de-winterization, engine break-in and valve adjustment — phase log

**Status:** 🚧 In progress
**Branch:** `phase-264` (Opus session, main checkout)

---

### 2026-09-26 — Opened: Track N batch 2

The operator's prompt, 2026-09-26: start Phase 264, Track N batch 2 of 3,
and run it to its finish line. Batch 2 is rows 264 (winterization), 265
(de-winterization), 266 (engine break-in) and 268 (valve adjustment).
Batch 3 is phase 262 (rows 262, 263, 267), then gate 272.

**Ledger convention, 261's, as the operator restated it.** 264 carries
the batch. Rows 265, 266 and 268 close ✅ "folded into 264" with no
CLOSED date. One history row (264) and one handoff.

**Two live-row changes, both in scope by the operator's words:**
1. `generic_winterization_v1`'s description says "Track N phase 264
   expands" (F158). Step 0 decides whether 264 extends that template or
   adds a new one. "Either way, the internal reference goes, and nothing a
   user sees names a phase."
2. F160: `ppi_chassis_v1` names the Yamaha YW125Y service manual "Zuma
   125". "Correct each one, in the same migration, to what the document's
   title page carries."

**The operator's stop, recorded as given:** "Both alter existing live
rows, which is a rule-1 stop. Back up to ~/backups/motodiag/ first and
keep 5. Dry-run on a copy, then show me the diff: every changed row, with
before and after text. Wait for my answer before the live apply." No
pre-approval of the live apply exists. This session asks for it and waits.

**Carried forward** (the operator's list): no literal head pin (F124); no
test reads `data/motodiag.db`; migration tests survive the next
migration; the rollback guard stays; the integration-gap allowlist and
its size pins are updated if a module is added; no internal references in
user-visible text (F158); a negative claim gets a whitespace-proof search
and a control on the cited page; each document is named from its title
page; the Edit tool for source edits; scratch files stay out of `/tmp`
(the session scratchpad is used). Subconscious is available again; bulk
reading goes through it (rule 2), with the fallback route recorded per
entry if it fails.

Read before acting: CLAUDE.md and the working-rules index; ROADMAP rows
258–272 and the status key; `ROADMAP_AUTHORITY.md`; the newest handoff
(`2026-09-25_261_closed.md`, named by `git log`); F158, F159, F160 in
`docs/FOLLOWUPS.md`; 261's implementation, phase log and Step 0;
migrations 007, 068 and 069 and the 114, 259, 260 and 261 test files.

Branch `phase-264` from `master` at `270fcad`. **Ledger step before Step
0:** rows 264, 265, 266 and 268 → 🚧, commit `ed70006`;
`roadmap_check.py` ok.

### 2026-09-26 — Step 0: an extension, four checklists, no fork

The measurements are in `264_step0.md`. In short:
- **The four categories already exist.** The batch is one content
  migration (070) plus tests, with no new module.
- **Every row has maker support.** One negative died inside Step 0: an
  electric traction battery's storage is in the Vespa Elettrica service
  station manual (p. 9). One was narrowed: no document says "heat cycle",
  but the Buddy 125 prescribes a cool-down. Seven negatives stand, each
  with a control on its page.
- **Decided, not asked:**
  - 264 adds `winterization_v1` rather than extending the generic. The
    generic's items carry unsupported figures and would be rewritten
    live; filed instead.
  - Valve adjustment is one template with optional per-engine-type
    items.

  Neither choice ships different things from the rows' subjects.
- **F160 re-measured:** 8 live mentions in 3 items, not 9. The ninth is
  migration 068's Python description, which no row carries.
- **Rule 2 ran on its primary route.** Subconscious answered all three
  calls in a sandbox proven by planted writes. It took 3–5 turns where 2
  is the measured norm, and one call looped. Its `machine` field
  reintroduced "Zuma". Nothing from the model is used unchecked.

### 2026-09-26 — Build: migration 070, four templates, two re-points, 31 tests

What shipped:
- **Migration 070 `seasonal_breakin_valve_workflows`** (schema 69 → 70):
  - `winterization_v1` (7 items, all powertrains);
  - `de_winterization_v1` (7, all powertrains);
  - `engine_break_in_v1` (6, ICE and hybrid);
  - `valve_adjustment_v1` (8, ICE and hybrid).

  Also the two live re-points: `generic_winterization_v1`'s description
  (keyed on its old text) and the F160 text in `ppi_chassis_v1`'s items.
  The rollback deletes the new rows and reverses both re-points in the
  opposite order.
- **Claims before text** (`s0/claims.py`, session scratchpad): 86 claims,
  257 verbatim anchors, all on their cited pages. The checker was seen to
  fail on a wrong page and a corrupted figure.
- **The cross-check** (`s0/xcheck.py`) maps every "PDF p." in the seeded
  text to a claim for the machine named before it: 221 cited pages, 0
  unclaimed. It found three real attribution gaps before any test ran:
  "The Yamaha grounds…" twice and "the Kymco keeps…" once, each after
  another machine had been named. All three now name the machine. Its
  control: withdrawing V13, the only claim on People S 250 SM p. 81,
  turned exactly that citation red.
- **31 tests** in `tests/test_phase264_seasonal_breakin_valve.py`. Two
  failed at first run, both test-authoring errors: a pin said "check"
  where the text says "checks", and `winterization_v1` is a substring of
  `de_winterization_v1`, so the other-slug check needed a boundary.
- **Two existing pins moved with the phase's own changes:**
  - `test_phase260_ppi_chassis.py::test_figures_name_their_machines`
    asserted "Zuma 125" on a fresh database. It now asserts "YW125Y",
    plus no "Zuma" in any chassis field.
  - `test_phase114_workflow_substrate.py::test_list_by_powertrain`
    asserted no winterization template for electric machines. That was a
    head-state assumption from the one generic template. The pin is now
    on the generic's slug, plus the positive that `winterization_v1` is
    offered for electric (S0-5, Vespa Elettrica p. 9).
- **Floor** 9415 → 9446 (+31, this file only; `--collect-only -q -p
  no:xdist` measured 9,446).

**Known-bad controls**, each planted with the Edit tool, run with
`__pycache__` cleared and `-B`, seen red, and reverted:

| # | plant | red tests |
|---|---|---|
| 1 | "start from 0.15 mm" in the no-figure valve item | `test_no_figure_item_carries_no_clearance` |
| 2 | 7,800 → 7,900 rpm in one field | `test_every_pinned_figure_is_in_its_field`, `test_figures_sit_beside_their_machine` |
| 3 | "(Phase 999)" in a template description | `test_all_four_templates_are_clean` |
| 4 | the bare-"Zuma" replace dropped from one field | the upgrade-scope test, both F160 tests, and 260's moved pin |
| 5 | `engine_break_in_v1` dropped from the rollback's template `DELETE` | both round-trip tests; the rollback guard stayed green, as in 261 |
| 6 | an extra `UPDATE` of an unrelated live item inside 070 | `test_upgrade_from_69_changes_exactly_the_scoped_rows`, the round trip |

After the reverts: `grep` finds none of the plants, 60 passed over the
264 and 260 files, and the cross-check still reads 0 unclaimed.

**Whole-tree gates before the build commit:**
- rule 3's four, plus the F124 guard, 240c, 209B, 244U, 244Y, 244V, 355,
  the floor, and the 114, 259, 260, 261 and 264 files: **514 passed**
  (`-n auto`);
- `finding_check` exit 0, and `check(phase_docs="docs/phases/in_progress")`
  returns [].
