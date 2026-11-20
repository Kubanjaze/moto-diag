# Phase 405 — The deploy check asks what the change did (F210, F259)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-11-20

---

## Goal

A live database step today compares live with the backup taken at its dry
run and refuses, or fails, on anything that changed in between, apart from
the three entries of `SERVER_WRITES`. The payments feed writes live all the
time (F259), so 404's first database step refused before touching live, the
second ran only with the feed stopped, and every later check failed once the
feed ran again: the Quartermaster's Q1 and `verify_phase.sh` check 8
(`docs/handoffs/2026-11-18_404_closed.md`, "After the merge"). A shop's own
use will do the same (F210), and F210 is to be settled before onboarding
(330).

Built by the fleet, after 334 and before 330 (K91). The operator's words:
"C as recommended, with 334's database step done the 404 way. Add C's row
right after 334 so the fleet opens it when 334 merges." (K91), and on the
classification, "A. Let the fleet build 405 as I decided in K91. Relabel the
Step 0 report as an extension and note the deploy-folder rule does not apply
because 405 has no database change. Condition: 405 must still show the full
dry-run list before it asks for yes, and nothing it changes in the deploy
check lands on the live server before your review and my merge." (K95,
quoted in `405_step0.md`).

Revised for the Executive Officer's round 3 by the advisor session, at the
operator's word on that verdict ("A, do it up", 2026-11-20; K97, the
Yeoman's row on master, like K95's): item 1's views, item 3's entries,
item 6's `SERVER_WRITES` block, and the tests and mutations they need.
Nothing else in the plan changed.

After this phase, the deploy check stops asking whether live stood still
since the backup and asks whether the change did what was approved:

1. **Before the apply,** `apply-live` refuses only a change since the dry
   run in a table the change touches: the tables its approved diff and its
   scope name. A change anywhere else, the payments feed's, the server's or
   a shop's, is listed in the output and the apply goes ahead.
2. **After the apply, and in every later check** (apply-live's own check,
   `verify-live`, the dispatcher's re-check, the Quartermaster's Q1 and
   `verify_phase.sh` check 8, from the desktop or through the Mac's way
   in), the check passes when everything approved is on live exactly as
   approved. Other differences are listed, not counted as failures. After
   the apply the touched set decides nothing: a row the running code adds
   to a table the change created, or a field it moves in a row the
   approved diff names, is a listed difference, because the approved leaf
   still holds.
3. **Still refused or failed:** an approved change missing on live or
   different from what was approved, and a change since the dry run to a
   table the change touches. Every gate that is not this comparison stays
   as it is: the regression of record, the committed and unchanged diff,
   the fresh dry run that must equal the approved diff field for field,
   scope problems on the approved and the fresh dry run, the backup's
   hash, the scope file's hash, integrity and foreign keys.

One implementation in `deploy.py`, which every caller already uses. No
migration, no change to live, and the payments feed and the server are not
stopped or started.

The live step, in the handoff: the fleet's own copy of the code moves onto
the merge and the fleet restarts, so the dispatcher's re-check and the
operator's database step run the new rule. Then, from the Mac, the Mac's
own checkout is first put on master at 405's merge, clean, because
`remote.py` sends the Mac's HEAD as the commit the desktop checks out and
runs `deploy.py` from; only then `verify_phase.sh` for 404
(`404 29e21a3 d797d8e`), whose check 8 passes with the payments feed's
writes listed, and `verify_phase.sh` for this phase with its own two
commits, whose check 8 prints the live line and "has no dry-run diff: no
deploy to verify" and passes. Phase 405 has no dry-run diff, so its own run
lists nothing; only 404's run shows the listed writes. Run with the Mac
still on an older commit, 404's check 8 would run the old `deploy.py` and
fail, so the handoff's block refuses to go on unless the Mac's HEAD is the
merge commit.

## Logic

Causes and measurements: `405_step0.md`. The Engineer re-measures each line
below before changing it (CLAUDE.md, Step 0) and records the census in the
phase log. What this plan's own reading found, at `bd19285`:
`SERVER_WRITES` at `deploy.py` line 184, `server_masked` 189, `schema` 229,
`exact` 260, `exact_gaps` 291, `check_scope` 358 (its schema names at 362),
`shape_gaps` 748 (called once, at line 804 in `verify_live`), `preflight`
567 with the drift read at 593, the drift refusal at 598 and the fresh copy
migrated at 609, `apply_live` 626, `verify_live` 762; the callers:
`through_fleet.py` calls `apply_live` at line 450 and `verify_live` at 340
and 473 and reads only their exit codes; the dispatcher's
`verify_live_here` (`.claude/skills/fleet/dispatcher.py` line 701) runs the
fleet's own copy of `deploy.py` and `stage_deployed` (line 2109) stops on
any exit but 0; the Quartermaster's `database_step`
(`.claude/skills/fleet/quartermaster.py` line 153) reads the live diff's
header lines `Scope problems` and `Equals the approved exact diff` and the
exit code; `verify_phase.sh` check 8 (line 69) runs `verify-live` only when
a dry-run diff exists (line 90) and fails on any exit but 0 and 2; where
live is elsewhere it runs `remote.py live-check` (line 83), and `remote.py`
adds the Mac's own pushed HEAD as the commit (`AT_COMMIT` line 44,
`pushed_head` line 78, used at line 189); the desktop's `live_check`
(`ops/desktop/motodiag_remote.py` line 247, not 183 as the prompt says)
checks that commit out, detached and clean, in the development checkout
(`at`, line 209) and runs that checkout's `deploy.py verify-live`, or
prints "has no dry-run diff: no deploy to verify" with exit 0 when the
phase has none (lines 259 to 263). None of those callers needs a code
change: they read exit codes and two header lines, and both keep their
meaning. What the Mac sends decides which `deploy.py` the desktop runs, and
item 7 says what the handoff does about it.

1. **What a change touches** (`.claude/skills/deploy/deploy.py`, one new
   function beside `server_masked`, and one small reader beside `schema`).
   - `tbl_names(path)` reads `{"index i": "t", "trigger g": "t", "table t":
     "t"}` from a database's `sqlite_master` (`type`, `name`, `tbl_name`),
     the same rows `schema` reads. A view is left out: SQLite stores a
     view's own name as its `tbl_name` (measured: `create view v as select
     a from t` reads back as `('view', 'v', 'v')`), so a view names no
     table. No migration creates one today (`git grep -n -i -E 'create
     +(temp(orary)? +)?view' -- src/motodiag/core/migrations.py` finds no
     line), so a view named in a scope or the approved diff contributes no
     table to the touched set until a phase that creates one says what it
     touches.
   - `touched(scope, approved, names)` returns the set of tables the change
     touches, as the ROADMAP row defines it: "the tables its approved diff
     and its scope name". That is: every key of the scope's `tables`; every
     table under the approved exact diff's `rows`; every object under the
     scope's `schema` and the approved diff's `schema` (`added`, `removed`,
     `changed`) that is a `table`, by its name; and for an `index` or
     `trigger` named there, the table `names` maps it to (a `view` adds
     none, above).
     `schema_version` is in every real scope, so it is always touched.
   - **Where `names` comes from.** The set is computed once, in
     `preflight`, and its source is the fresh pre-apply copy's
     `sqlite_master` read after `migrate(fresh)` has run on it and before
     `_drop(fresh)`. That copy holds every object the change adds (the
     backup predates them) and every object it keeps (a dropped object's
     table comes from the backup's `sqlite_master`, read the same way and
     merged under the fresh copy's entries). So the drift read and split
     (today lines 593 to 599) move to after the fresh dry run's two gates,
     the scope check and the exact comparison, which are unchanged. The
     drift is then read from live later than today, a narrower window
     before the apply, not a wider one. An object the scope or the approved
     diff names that the fresh copy and the backup both lack contributes no
     table; the fresh dry run's scope gate (`check_scope`, line 362) refuses
     such a run before the split is reached, and the Engineer confirms that
     at Step 0 with a planted scope naming an index the migration never
     creates. If that gate lets it through, the case is a stop, not a
     fallback the Engineer invents.
   - The set is printed once per run, `tables this change touches: …`, so
     the operator can read what the check protected. After the apply and
     in `verify-live` the set decides nothing and is not computed: the
     comparison there is item 3's.
   - Finish line: on the deploy contract's fixture scope the set is
     `{workflow_templates, checklist_items, schema_version}`; a scope whose
     `schema` adds `index idx_x` and a migration that creates it on
     `known_issues` put `known_issues` in the set, read from the migrated
     copy; a table only the approved diff names (none in the scope) is in
     the set; a table in neither is not; the planted scope naming an index
     the migration never creates is refused by the scope gate before the
     split runs.
2. **Before the apply: refuse only a touched table** (`preflight`, the
   drift refusal, moved as item 1 says).
   - `drift, aside = server_masked(diff(dump(bk), dump(db)), approved)` stays
     as it is, so a listed server write in a touched table is still set
     aside, and a field the approved diff names never is. The drift is then
     split by `touched`. A table in the set that differs refuses, with a
     message that still contains the words "changed since the dry run" and
     names the tables and their counts (`table +added ~changed -removed`),
     and ends "Stop and ask." Tables outside the set that differ are printed
     as one list, "changed since the dry run, outside the tables this change
     touches: …", with the same counts, and the apply goes on. The set-aside
     line stays as printed today.
   - `SERVER_WRITES` stays. Under the new rule it still decides a verdict in
     one place: a listed column written by the server in a touched table
     between the dry run and the apply, which is set aside rather than
     refused. The phase log says so, with the case that shows it (383's
     `TestAMigrationThatWritesTheColumn` scope, which touches `api_keys`).
     Nothing is added to the list: that was K91's option A, not chosen.
   - Finish line: on the fixture database, a row written to `known_issues`
     (untouched) between the dry run and the apply is listed and the apply
     returns 0; a row added to, changed in or removed from `checklist_items`
     or `workflow_templates` (touched) refuses with exit 2 and live is
     untouched; a stand-in `stripe_event_cursors` row rewritten between the
     dry run and the apply is listed, not refused; a `known_issues` row
     changed when the scope's `schema` adds an index on `known_issues`
     refuses.
3. **After the apply, and in `verify-live`: the approved changes hold,
   the rest is listed** (`apply_live`, `verify_live`, `shape_gaps` kept as
   the gaps half, and one new function beside it for the listed half).
   - `approved_holds(approved, now)` returns two lists: `gaps`, every entry
     of the approved exact diff (an entry as the next bullet defines it)
     that is absent from live's diff or holds a different value (rows
     added, removed or changed, their fields, and every schema object with
     its SQL), and `listed`, the entries live's diff holds that the approved
     diff does not, grouped as `table +a ~c -r` for rows the approved diff
     does not name, `table rowid column` for a field that moved in a row it
     names, and `schema added: name` (or `removed:`, `changed:`) for an
     object it does not name, with that object's `sql` entry. An approved
     value masked as `<clock>` matches any timestamp-shaped value, as today.
   - **An entry, defined here: `entries(d)`,** one new function beside
     `_leaves`, called only by `approved_holds`. `_leaves` (line 282) makes
     one leaf of an empty dict and one leaf of a whole list, and `exact`
     (line 260) writes `"added": {}`, `"removed": {}` and `"changed": {}`
     for every table it lists, the schema's `added`, `removed` and `changed`
     as lists of names, and each changed field as one `[before, after]`
     list. Walked that way, an approved empty dict is a value live lacks
     once live has a row there, and a later migration's object makes live's
     list of names differ from the approved one: both gaps, the old rule
     again. So `entries(d)` is the diff with three changes, made on both
     sides:
     - every empty dict dropped, at any depth, with a dict left empty by
       that: an approved table with nothing added, removed or changed holds
       nothing, so a row live adds to or removes from it is listed;
     - each of `schema.added`, `schema.removed` and `schema.changed` made
       one key per name (`{"table t": true}`): each approved name is its own
       entry, a gap when live's same list lacks it, and a name only live's
       list holds is listed;
     - each changed field's `[before, after]` made two entries,
       `{"before": old, "after": new}`, so the `<clock>` rule, which
       matches one value, reads the after-value. No test asserts a gap
       message on a changed field's list (`git grep -n -E "approved
       \[|live \[" -- tests` finds no line), and
       383's and 385's column-writing migrations write
       `2020-01-01T00:00:00Z`, which is never masked, so their "written
       again" controls still exit 3.
     `exact` writes no other list. `docs/phases/in_progress/405_entries_census.py`
     reads every approved diff committed under `docs/phases/completed/`: 21
     hold an exact diff, the 20 that list a table all hold empty dicts, and
     none holds `<clock>` inside a changed field's list. The Engineer re-runs
     it at Step 0 and records its output in the phase log. A side with no
     entries left is `{}`, which holds none: an approved diff with no
     entries (384's, which changed nothing) has no gaps, and a live diff
     with none lists nothing. `_leaves` reads `{}` as one leaf, so
     `approved_holds` passes neither side to `shape_gaps` or
     `listed_differences` as `{}`; it answers those cases itself. `_leaves` is
     unchanged, so `exact_gaps` still compares the fresh dry run with the
     approved diff exactly, both ways, empty dicts and whole lists included.
   - **`shape_gaps` is kept, as the gaps half, with its signature and its
     messages.** `shape_gaps(approved, now) -> list[str]` keeps producing
     `"{path}: approved {va!r}, live {vb!r}"`, and the `<clock>` rule
     stays. One change to its body: it walks the approved diff's leaves
     (`sorted(a)`), not the union of both sides (`sorted(set(a) | set(b))`,
     line 754 today), so a leaf only live holds is no longer a gap. That is
     the whole of the rule change on this function, and
     `tests/test_phase378_verify_live.py::test_a_masked_clock_matches_any_timestamp_and_nothing_else`
     (lines 122 to 138) stays as it is and stays green: each of its five
     assertions puts the same leaves on both sides or fewer on live's, so
     the narrowed walk returns what it returned before, in the same words.
     The Engineer runs that test unchanged as the control that the
     signature and messages held, and `approved_holds` calls
     `shape_gaps(entries(approved), entries(now))` for its first list. The
     second list comes from a new function, `listed_differences(approved,
     now)`, walking the leaves of `entries(now)` that `entries(approved)`
     lacks and grouping them as above (a changed field's two entries are one
     field there). `exact_gaps` keeps its job on the
     fresh dry run in `preflight`, where the copy must equal the approved
     diff both ways.
   - **What is a gap and what is listed, settled here.** A gap is only an
     approved entry absent or different: an approved added row gone, an
     approved changed field holding neither its approved after-value nor
     `<clock>` where that was approved, an approved added row's field
     changed, an approved schema name missing from live's same list or its
     SQL different. Everything else is listed, whatever table it is in: a
     field the approved diff does not name moved in a row it does name
     (383's `api_keys` row 2 `is_active` after a `last_used_at` migration),
     a row added to or removed from a table the change touches or created
     (404's check-ins, 379's later row; an approved `{}` holds nothing), a
     schema object a later migration added (334's two, on live past 404's
     backup), and any change in a table the change does not touch.
     This is the row's "other differences are listed", and the tests under
     item 5 follow it.
   - **`apply_live`, after the migration:** `gaps` are the scope problems
     recorded, as `live differs from the approved diff: …` is today, and
     the exit is 1 when any exists, else 0. The after-apply `check_scope`
     call no longer runs over the whole live diff: a row the running code
     wrote since the dry run would read as a count mismatch or a table not
     in scope, which is what K91 says to list. The scope was checked twice
     before the apply, on the approved dry run and on the fresh copy
     moments earlier, and those gates are unchanged. The live diff's header
     keeps `Scope problems` (the gaps, or `none`), `Equals the approved
     exact diff` (`yes` when `gaps` is empty: every approved change holds),
     `Set aside, written by the running API` and `F158 census on live`, and
     gains one line, `Other differences, listed`, with the count and the
     first entries or `none`. The Quartermaster's Q1 and the 395 and 406
     tests read the first two lines and keep working.
   - **`verify_live`:** the same comparison on live read now against the
     backup, at the one call site (line 804). It prints the schema lines
     and the `rows:` lines as today, the set-aside line, then the listed
     differences, then `equals the approved exact diff: yes` when `gaps` is
     empty, `no` with the gaps when not. Exit 3 only on gaps; the F197
     lines stay with them: when live's schema head is past the phase's own,
     "later migrations explain the difference", else "the difference is not
     a later migration's". A later phase's own additions with every
     approved change still holding are listed, and the exit is 0. Integrity
     and foreign keys are unchanged and still exit 1. Exit 2 with no deploy
     is unchanged.
   - Finish line: on the fixture database, after a clean apply, a row added
     to `known_issues` or to a stand-in `stripe_event_cursors` is listed and
     `verify-live` exits 0; a migration that creates `stripe_feed_checkins`
     and rows written to it afterwards, as 404's check-ins, are listed and
     the exit is 0; a later migration that adds a schema object the
     approved diff does not name is listed as `schema added: …` and the
     exit is 0 (404's check 8 needs exactly this: live holds 334's two
     objects past 404's backup); a row removed from a touched table whose
     approved `removed` is `{}` is listed, exit 0; an approved diff with no
     entries lists every difference, exit 0; an approved changed field
     masked `<clock>`, read back as a later timestamp, holds, exit 0; an
     approved added row deleted from live exits 3; an
     approved changed field written again exits 3 (383's
     `test_a_later_request_on_that_field_fails_verify_live` stays as it
     is); an approved schema object dropped exits 3; a migration that
     writes one value on the copy and another on live makes `apply_live`
     return 1 and the live diff say `no`; the 378 `shape_gaps` test passes
     without an edit.
4. **The callers, unchanged and shown to be so** (`through_fleet.py`,
   `remote.py`, `ops/desktop/motodiag_remote.py`, the dispatcher, the
   Quartermaster, `verify_phase.sh`).
   - No code change in any of them. `through_fleet.py` still shows the full
     dry-run list before it asks for yes (K95's condition), which
     `tests/test_phase395_through_fleet.py` and
     `tests/test_phase406_through_fleet_split.py` already pin; those tests
     stay green without edits. The dispatcher's re-check and Q1 read the
     exit code and the two header lines whose meaning is kept.
   - Finish line: the 395, 406, 379 (check 8) and 395 Q1 tests pass on the
     new `deploy.py` without a change to their assertions; `git diff
     --stat master -- .claude/skills/fleet .claude/skills/closeout
     .claude/skills/deploy/through_fleet.py .claude/skills/deploy/remote.py
     ops/` is empty.
5. **The existing controls, moved where K91 moves the rule** (the tests
   named under Tests). A control that holds the old rule changes only
   where K91 changes it, each change named in the phase log with the test
   id and the reason. The two positions differ, and the plan says which is
   which:
   - **Before the apply,** a control that changed a table the fixture
     scope does not touch is kept in two forms: under a scope that names
     the table (383's and 385's `_scoped` form) it still refuses with
     "changed since the dry run"; under the fixture scope it is listed and
     the apply returns 0. The touched-table form is the control, and its
     mutation (the touched set returned empty) turns it red.
   - **After the apply,** every existing control changes a field or row
     the approved diff does not name (383's `api_keys` row 2 `is_active`
     and `devices`, its `audit_events` row removed and `devices` row added;
     385's `rebind`, `added_row` and `other_table`, beside and alone). By
     item 3 those are the listed shape and exit 0, so they move to the
     listed cases, each asserting exit 0 and its change in the listed
     lines. The after-apply control that still fails is an approved leaf
     altered or missing: each file keeps its existing `_scoped` test (the
     approved field written again, exit 3) and gains one more under
     `_scoped`, the approved `schema_version` row deleted from live after
     the apply, exit 3. Item 3's "still exits 3" after the apply means
     those shapes and no other.
   - Finish line: every changed assertion is in the phase log's list, each
     with the K91 sentence that changes it; no test outside that list
     changes; each class docstring says which shape it holds.
6. **The deploy skill's record** (`.claude/skills/deploy/SKILL.md`,
   `.claude/skills/deploy/CHANGELOG.md`, `deploy.py`'s module docstring and
   its `SERVER_WRITES` comment block).
   - `SKILL.md`: step 4's bullet "live still equals the backup, but for
     the columns the running API writes" (line 129) becomes the rule above,
     dated, with K91; step 5 says what `verify-live` now asks and what exit
     3 now means; the line under "From the Mac" that reads "Before Phase
     405 lands, a database step stops the payments feed and stays at the
     desktop (K91)" is replaced by what holds after it: a database step no
     longer needs the feed stopped; "What it holds, and what it cannot"
     gains the new rule's limit: after the apply, a row the migration wrote
     on live but not on the copy cannot be told from a row the running code
     wrote, and is listed, not failed; the comparison before the apply (the
     fresh dry run must equal the approved diff) is where a migration's own
     surprise is caught.
   - `CHANGELOG.md`: a dated entry at the top, "2026-11-2x — the check
     asks what the change did (Phase 405, K91, F210, F259)", naming the
     functions, the moved drift split, the tests and the mutation count.
   - `deploy.py`'s docstring (lines 18 to 34) says the same in its
     `apply-live` and `verify-live` lines; today its `apply-live` line
     reads "live / equals the backup" across lines 25 and 26.
   - `deploy.py`'s `SERVER_WRITES` comment block (lines 172 to 182): its
     two sentences ending "so either one is drift" (K59: an `audit_events`
     row changed or removed; F212: a token row rebound, or a new one)
     describe the old rule after the apply. Each gains what holds after
     405: before the apply, such a change in a table the change touches
     refuses; after the apply, it is listed unless it alters an approved
     entry. The rest of the block, and K59's and F212's words, are kept.
   - Finish line: `git grep -n -F 'equals the backup' -- .claude/skills/deploy`
     finds exactly two lines before the work, `SKILL.md:129` and
     `deploy.py:26`, measured on this branch at `bd19285`, and finds none
     after it. The phase log records both runs. A historical mention of
     the old rule, if one is wanted in `CHANGELOG.md`'s new entry, is
     worded without that phrase, so the grep stays a clean zero.
7. **Documents.** `docs/FOLLOWUPS.md` gains, at close-out, the closing lines
   for F259 and F210 in the form F270's has, each saying "once merged and
   live" until the handoff records the live step; if Step 0 or the build
   finds a case the rule does not cover, the Engineer files a finding with
   the `finding` skill before any document cites its number. The ROADMAP
   row moves with the work. The handoff carries the live step as paste
   blocks, each saying which computer and which window, ending in ALL GOOD
   or SOMETHING IS OFF, every `gh` call naming `-R Kubanjaze/moto-diag`
   (R8).
   - **The Mac's block puts the Mac on the merge first.** `remote.py`
     sends the Mac's own HEAD as the commit for `live-check`, and the
     desktop checks that commit out in its development checkout and runs
     that checkout's `deploy.py`. So the Mac's block, before either
     `verify_phase.sh` run, does `git fetch origin`, `git checkout master`
     and `git pull --ff-only`, confirms the tree is clean, and prints
     SOMETHING IS OFF and stops unless `git rev-parse HEAD` equals 405's
     merge commit on master (written into the block after the merge). The
     block says in plain words why: with the Mac on an older commit, 404's
     check 8 would run the old deploy check and fail. If the desktop's
     development checkout is not clean, `live_check` refuses and the block
     prints SOMETHING IS OFF; the handoff says that the desktop's checkout
     is then tidied at the desktop, not from the Mac.
   - The Mac's blocks expect what each run can print: 404's run shows
     check 8 passing with the feed's writes in the listed lines; 405's run
     shows check 8 printing "has no dry-run diff: no deploy to verify" and
     passing, and lists nothing.
   - `docs/decisions.md` on this branch ends at K94; K95's row is the
     Yeoman's, on master, and this plan cites it from the Step 0 report.
8. **Finish line for the phase:** every test under Tests green and the new
   file seen red on master's `deploy.py`; the mutations red;
   `COLLECTED_TEST_FLOOR` raised by a diff of collected ids; the quality
   counts at their pins (no function in `deploy.py` crosses McCabe 20: the
   new comparison, the touched set and the drift split are their own
   functions; coverage does not fall); the regression of record inside the
   fence after `wholetree.sh`; `verify_phase.sh`; the handoff.

## The change log's three newest entries

- **2026-10-29 — rule 6: the code's counts only improve, and the weekly page (Phase 393, K54).** Became `tests/test_phase393_quality_ratchet.py`: the six measured counts against their pins both ways, and the coverage gate wired into `.claude/skills/closeout/regression.sh`. This phase adds no ruff or mypy finding, no `except Exception: pass`, and keeps `preflight`, `apply_live` and `verify_live` under McCabe 20 by putting the new logic in functions of their own.
- **2026-10-26 — R8: an operator paste block's `gh` names its repository (before Phase 391, F222).** Became R8 in `.claude/skills/closeout/roadmap_check.py`, run with every suite and on every push. The handoff's live-step blocks carry `-R Kubanjaze/moto-diag` on every `gh` call or make none.
- **2026-10-22 — `fleet` joins the procedure folders (after Phase 387).** No check: the entry says the row is text only and no check reads the table. This phase changes nothing under `.claude/skills/fleet/`.

## The plan of record

'Next, in order' #18 of `docs/reports/2026-10-12_plan_of_record.md`:
"18. 405 (shop, built by fleet); needs the operator: nothing; from:
2026-11-19 · K91".

The dated entry under "Changes to the order", 2026-11-19: "**2026-11-19:
405 goes after 334 and before 330 (K91).** The deploy check asks whether the
change did what was approved, not whether live stood still since the
backup. Then the payments feed's writes (F259), and later a shop's own
(F210), stop refusing database steps and failing the checks after them."
Its lines: "**Why now:** 404's first database step refused on the feed's
writes, and every check after it failed once the feed ran again
(`docs/handoffs/2026-11-18_404_closed.md`, "After the merge"). 334 adds a
table through a database step too." "**Until 405 lands,** 334's database
step stops the payments feed from before the dry run until the dispatcher's
own check has passed, as 404's did." "**330 keeps its need as written:**
F210's general rule comes first, and 405 is that rule."

K91 (2026-11-19), the operator's words "C as recommended, with 334's
database step done the 404 way. Add C's row right after 334 so the fleet
opens it when 334 merges."; the part on this phase: "Option C, the advisor's
recommendation: the deploy check asks whether the change did exactly what
was approved, and whether anything else touched what it changes; before the
apply it refuses only a change since the dry run in a table the change
touches; after the apply, and in every later check, the approved changes
must hold, and other differences are listed, not failed. Not chosen: A, the
feed's tables on the set-aside list, and B, the feed stopped for every
database step. It becomes Phase 405, built by the fleet after 334 and before
330".

Phase 334 is closed (`docs/handoffs/2026-11-20_334_closed.md`; its ROADMAP
row reads CLOSED 2026-11-20), so the order holds and 405 is next.

The phase is a shop phase in the plan of record's list ("shop, built by
fleet"): it changes `.claude/skills/deploy/`, `tests/` and `docs/`, and
nothing under `.claude/skills/fleet/`. No "Unblocks:" line under K43
applies; the plan of record itself says 330 keeps its need and 405 is the
rule it needs.

## Rule-1 stops anticipated

- **A real fork: none known.** K91 chose option C over A and B, and the
  Step 0 report leaves no second plan that would ship something different.
  Where this plan leaves a build choice (the wording of the refusal and of
  the listed lines, the name of the new listing function), either choice
  ships the same behaviour. `shape_gaps` is kept, as item 3 fixes; that is
  no longer a choice left to the build.
- **A threshold or a rule's definition: one change, approved; anything
  else is a stop.** K91 is the operator's approval of exactly the
  comparison above, and K95 of the fleet building it. The Engineer applies
  it literally. Foreseeable stops, each with kind `threshold-or-rule`: a
  touched set derived in any way other than the row's words ("the tables
  its approved diff and its scope name") where the two readings would give
  different verdicts on a real case; any new refusal; any change to a gate
  that is not this comparison (the fresh dry run's equality, the scope
  checks before the apply, the backup's hash, the scope file's hash,
  integrity, foreign keys, the regression gate, the committed diff); any
  entry added to or removed from `SERVER_WRITES`; stopping or starting the
  payments feed or the server inside a database step.
  **Four readings, recorded, told to the operator with the pull
  request:** (1) an index or trigger the scope or the approved diff names
  counts its table as touched (a view names none: item 1), by `tbl_name`
  in the fresh pre-apply copy's `sqlite_master` after the migration has
  run on it, merged with
  the backup's for a dropped object, and the drift split moves after the
  fresh dry run's gates to read it; (2) the after-apply scope check over
  the whole live diff is replaced by the approved-holds comparison,
  because K91 says a difference the running code made is listed, and the
  scope stays checked twice before the apply; (3) after the apply, a
  field the approved diff does not name, moved in a row it does name, and
  a row added to or removed from a touched table, are listed, because the
  approved entry still holds, and only an approved entry (item 3's
  `entries`) absent or different fails; (4) `verify-live` for an older
  phase passes when every
  approved change still holds and later migrations only added other
  objects, and still fails, naming the later migration, when one altered
  or removed an approved change. If the Engineer finds a case where any of
  the four could go two ways on live, or a scope naming an object the
  migration never creates reaches the drift split, that is a stop.
- **A test that cannot be made green: none known.** The existing controls
  that change are named under Tests, each with the reason in the commit
  message. If a test outside that list (357's exact comparison, 358's other
  refusals, 378's `shape_gaps` test, 395's and 406's caller tests, 379's
  check 8 tests) cannot be made green inside K91's words, the Engineer
  stops.
- **A login or a credential: none.** Every test runs on fixture databases
  in a temporary git repository, through 358's deploy contract; nothing
  reads live, the backups folder or the network.
- **A live-database change that alters or deletes rows: none.** The phase
  has no migration and changes no live row. The live step after the merge
  moves the fleet's code copy, moves the Mac's checkout to the merge, and
  runs read-only checks. Any live write, or any stop or start of the
  payments feed or the server, is a stop.

## Tests

- `tests/test_phase405_what_the_change_did.py`, on 358's `env` fixture
  and its scope (touched: `workflow_templates`, `checklist_items`,
  `schema_version`; untouched: `known_issues`, and stand-in tables
  `stripe_event_cursors`, `stripe_feed_checkins` and `work_orders` the
  fixture adds, named for the writers F259 and F210 describe):
  - **the touched set:** the fixture scope's three tables; a scope whose
    `schema` adds an index on `known_issues`, with a migration that
    creates it, adds that table, read from the migrated copy; a table only
    the approved diff names is in; a table in neither is out; a scope
    naming an index the migration never creates is refused by the fresh
    dry run's scope gate, and the split is not reached;
  - **before the apply, listed and applied:** a `stripe_event_cursors` row
    rewritten between the dry run and the apply; a `work_orders` row added
    (a shop's own write, F210); a `known_issues` row added (358's old
    control, now listed); in each, `apply_live` returns 0, live holds the
    approved change, the output names the table under "outside the tables
    this change touches", and the live diff's header reads `Equals the
    approved exact diff: yes` with the table under `Other differences,
    listed`;
  - **before the apply, refused:** a row added to, changed in and removed
    from `checklist_items`; a row added to `workflow_templates`; a
    `known_issues` row changed when the table is touched only through an
    index the scope names and the migration creates; each exits 2 with
    "changed since the dry run", and live is untouched (358's `_refusal`);
  - **after the apply, listed and passing:** a new `known_issues` row; a
    `stripe_event_cursors` row rewritten; a migration that creates
    `stripe_feed_checkins` (the scope's `schema` names it) and three rows
    written to it afterwards, as 404's check-ins; a later phase's
    `schema_version` row and a new row in a touched table (379's old
    case); a field the approved diff does not name moved in a row it
    names; a later migration that adds a schema object (`table later_t`)
    the approved diff does not name, listed as `schema added: table
    later_t` (the handoff's 404 run depends on this case); a row removed
    from a touched table whose approved `removed` is `{}`; an approved diff
    with no entries (384's shape), every difference listed; an approved
    changed field masked `<clock>` by a migration that writes the run's
    time, read back with a timestamp outside the masking day; each
    `verify_live` exits 0 and prints the table or object in the listed
    lines;
  - **after the apply, failing:** an approved added row deleted from live;
    an approved changed field written back to its old value; an approved
    added row's other field changed; an approved index dropped; each
    `verify_live` exits 3 and says `no`, with the F197 line naming whether
    a later migration explains it; and the apply's own check: a migration
    that writes one value on the copy and another on live makes
    `apply_live` return 1, the live diff say `no`, and `verify_live` exit 3;
  - **the two halves, alone:** `shape_gaps` on an approved diff and a live
    diff holding one extra leaf returns `[]`, and `listed_differences`
    returns that leaf grouped; on an approved leaf absent, `shape_gaps`
    returns the one message in the 378 format and `listed_differences`
    returns `[]`; `entries` alone: an empty dict dropped at any depth,
    each schema name its own key, a changed field's list split into
    `before` and `after`, and the input not modified; and `exact_gaps`
    still reporting an approved `{}` that a fresh diff lacks, which shows
    `_leaves` was not the one changed;
  - **the other gates unchanged, run again here as controls:** a fresh dry
    run differing in one field refuses (357's case); a scope file changed
    refuses; the backup gone refuses; a foreign-key break exits 1; a
    touched-table drift and a fresh-dry-run gap together refuse on the
    gap first, showing the split now runs after the fresh dry run's gates;
  - **the callers:** `verify_phase.sh` check 8 on a stand-in `deploy.py`
    exiting 0 with listed lines passes, and on 3 fails (379's harness);
    the Quartermaster's `database_step` passes on exit 0 with `yes` and
    refuses on 3 (395's harness); `through_fleet.py` still prints the dry
    run's list before the question (406's split test, unchanged, named in
    the log as K95's condition).
- Existing tests updated with the reason in the commit message, each
  named in the phase log:
  - `tests/test_phase358_deploy_contract.py`
    `test_when_live_changed_since_the_backup` (a `known_issues` row,
    untouched): becomes the listed case, and a new sibling on
    `checklist_items` keeps the refusal;
  - `tests/test_phase378_verify_live.py`
    `test_a_row_outside_the_approved_diff_is_reported`: exit 0, the row
    listed and still printed as `rows: known_issues +0 ~1 -0`;
    `test_a_masked_clock_matches_any_timestamp_and_nothing_else` is
    **unchanged**, and is the control that `shape_gaps` kept its signature
    and messages;
  - `tests/test_phase379_verify_live_fails.py`
    `test_an_approved_diff_missing_a_live_row_fails`: becomes "an approved
    row missing on live" (the row deleted from live), exit 3; its old
    shape, live holding a row the approved diff does not, becomes a listed
    case; `test_a_later_migration_is_named_as_the_cause_and_still_fails`:
    the later migration alters an approved row, exit 3 with the F197 line;
    its old shape (a later row added) becomes a listed case;
  - `tests/test_phase383_server_writes.py`: in `TestTheControlsStillFail`,
    the three before-the-apply controls are each kept under a scope that
    names their table (the `_scoped` form, `api_keys` for the first two;
    a scope naming `devices` for the third), still refusing, and their
    fixture-scope forms become listed cases with exit 0;
    `test_another_column_after_the_apply` and
    `test_another_table_after_the_apply` move to the listed cases, exit 0
    with the change in the listed lines; `TestAWholeTableKeepsItsControls`:
    `test_a_changed_row_before_the_apply` kept under a scope naming
    `audit_events`, refusing, and its fixture-scope form listed;
    `test_a_removed_row_after_the_apply` and
    `test_another_table_s_added_row_after_the_apply` move to the listed
    cases; `TestAMigrationThatWritesTheColumn` unchanged and gains
    `test_the_approved_row_removed_after_the_apply` (the approved
    `schema_version` row 71 deleted from live, exit 3);
    `test_the_list_is_exactly_this` unchanged;
  - `tests/test_phase385_server_writes.py` `TestTheControlsStillFail`:
    `test_before_the_apply` runs `rebind` and `added_row` under a scope
    naming `device_tokens` (the `_scoped` form), still refusing, beside
    and alone, and under the fixture scope as listed cases; `other_table`
    (`phones`) is a listed case in both scopes; `test_after_the_apply`
    becomes the listed case for all six parametrizations, exit 0;
    `TestAMigrationThatWritesTheColumn` unchanged and gains
    `test_the_approved_row_removed_after_the_apply`, exit 3;
  - `tests/test_phase348_server_writes.py`: unchanged (it tests
    `server_masked` alone);
  - `tests/test_phase357_deploy_exact.py`: unchanged.
- Old code: the new file run against master's `deploy.py`, red, with the
  controls green.
- Mutations, `405_mutate.py`, each a string in `deploy.py` replaced and the
  named tests run, every file restored: the touched set returned as every
  table of the backup (the old rule; the listed-and-applied cases go red);
  the touched set returned empty (the refused cases go red); `shape_gaps`
  returning `[]` (the failing cases go red); `shape_gaps` walking the
  union of both sides again (the listed-and-passing cases go red, and the
  378 test stays green, which shows that test alone does not hold the new
  rule); an index's table left out of the touched set (the index case goes
  red); the clock rule dropped from `shape_gaps` (the clean read-back and
  the 378 test go red); the `tbl_names` map read from the backup instead
  of the migrated copy (the index case goes red); `entries` keeping the
  schema's lists whole (the later-schema-object case goes red); `entries`
  keeping empty dicts (the removed-row case and 379's old shape go red);
  `entries` keeping a changed field's list whole (the masked-clock field
  case goes red); `approved_holds` calling `shape_gaps` on an approved
  diff with no entries (the 384-shape case goes red).
- `COLLECTED_TEST_FLOOR` raised by a diff of collected ids; the floor test
  and the quality ratchet both green.
- The regression of record through `regression.sh` inside the fence, with
  `wholetree.sh` first. This phase touches neither the knowledge content
  paths nor `migrations.py`, so fast mode suffices before each commit, and
  `--full` runs once before the regression of record.

## Non-goals

A migration, or any change to live. Stopping or starting the payments feed
or the server, in this phase or inside a database step. Adding
`stripe_event_cursors`, `stripe_feed_checkins`, `stripe_feed_notices`,
`stripe_webhook_events`, `invoice_payments`, `invoices` or
`terms_acceptances` to `SERVER_WRITES` (K91's option A, not chosen; 334's
open item on `terms_acceptances` needs no entry under the new rule, and the
handoff says so). The feed stopped for every database step (option B). Any
code change to `through_fleet.py`, `remote.py`,
`ops/desktop/motodiag_remote.py`, `verify_phase.sh`, `quartermaster.py` or
`dispatcher.py`: they read exit codes and two header lines whose meaning is
kept; `verify_phase.sh`'s comment "3 live differs from the approved diff"
stays true, and its "no dry-run diff" skip, which makes 405's own check 8
print nothing listed, is not changed. Changing which commit `remote.py`
sends for `live-check`: it stays the Mac's pushed HEAD, and the handoff
puts the Mac on the merge instead. Renaming `shape_gaps` or changing its
signature or message format. The desktop's installed dispatcher and
sudoers (406's, installed once; nothing here changes the fixed list). A
shop's own traffic and onboarding (330). The engineer gate's deploy-folder
refusal (`engineer.verify_deploy`), which K95 says does not apply here and
which is not changed. The K95 row in `docs/decisions.md` (the Yeoman's, on
master). A touched set computed after the apply or in `verify-live`: it
decides nothing there. No seed data, no split and no eval protocol: this
phase has none, and it names no path under `data/`.

## Planned items

- [ ] Step 0 re-measured: the line numbers above, the four callers and what each reads, which commit `remote.py` sends for `live-check` and what the desktop does with it, the `SERVER_WRITES` finding (still used in a touched table before the apply), the scope gate's refusal of an object the migration never creates, the two lines `git grep -n -F 'equals the backup' -- .claude/skills/deploy` finds, and the census in the phase log
- [ ] `tbl_names` and `touched`: the set as the row defines it, read from the migrated pre-apply copy, printed once per run, with its tests
- [ ] Before the apply: the drift read and split moved after the fresh dry run's gates; a touched table refuses with "changed since the dry run"; the rest is listed and the apply goes on
- [ ] After the apply and in `verify-live`: `shape_gaps` kept as the gaps half, walking the approved leaves only, its signature and messages unchanged and the 378 test green without an edit; `entries` (empty dicts dropped, each schema name and each changed field's `before` and `after` its own entry), `listed_differences` and `approved_holds`; the census re-run and recorded; the live diff's header keeps its two lines and gains `Other differences, listed`; exit 3 only on an approved entry absent or different, the F197 lines kept
- [ ] The existing controls moved where K91 moves the rule: before the apply, kept on a touched table and listed on an untouched one; after the apply, moved to the listed cases, with the approved-row-removed control added under each `_scoped` form; each named in the phase log with its reason; the kept controls still red on their mutations
- [ ] `SKILL.md`, `CHANGELOG.md`, the module docstring and the `SERVER_WRITES` comment block say what the check now asks, dated, with K91; the grep for `equals the backup` under the deploy folder finds nothing after, both runs in the log
- [ ] New tests red on master's `deploy.py`; the callers' tests green unchanged; `405_mutate.py` red; `COLLECTED_TEST_FLOOR` raised by a diff of collected ids; the quality counts at their pins
- [ ] The regression of record inside the fence; `verify_phase.sh`
- [ ] The close-out: FOLLOWUPS closing lines for F259 and F210 "once merged and live"; any uncovered case filed as a finding; the ROADMAP row ✅ with CLOSED date and regression line; the handoff with the live step as paste blocks ending in ALL GOOD or SOMETHING IS OFF: the fleet's code copy onto the merge and the fleet restarted; from the Mac, first fetch, checkout master, pull fast-forward only, and stop unless HEAD is 405's merge commit, then `verify_phase.sh 404 29e21a3 d797d8e` with check 8 passing and the feed's writes listed, and `verify_phase.sh` for 405 with check 8 printing "no deploy to verify" and passing
