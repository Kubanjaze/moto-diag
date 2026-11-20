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
   approved. Other differences are listed, not counted as failures.
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
operator's database step run the new rule; then, from the Mac,
`verify_phase.sh` for 404 (`404 29e21a3 d797d8e`) and for this phase, with
check 8 passing and the payments feed's writes listed.

## Logic

Causes and measurements: `405_step0.md`. The Engineer re-measures each line
below before changing it (CLAUDE.md, Step 0) and records the census in the
phase log. What this plan's own reading found, at `9707177`:
`SERVER_WRITES` at `deploy.py` line 184, `server_masked` 189, `exact_gaps`
291, `shape_gaps` 748, `preflight` 567 with the drift refusal at 598,
`apply_live` 626, `verify_live` 762; the callers: `through_fleet.py` calls
`apply_live` at line 450 and `verify_live` at 340 and 473 and reads only
their exit codes; the dispatcher's `verify_live_here`
(`.claude/skills/fleet/dispatcher.py` line 701) runs the fleet's own copy of
`deploy.py` and `stage_deployed` (line 2109) stops on any exit but 0; the
Quartermaster's `database_step` (`.claude/skills/fleet/quartermaster.py`
line 153) reads the live diff's header lines `Scope problems` and `Equals
the approved exact diff` and the exit code; `verify_phase.sh` check 8 (line
69) fails on any exit but 0 and 2; the Mac's way in runs the same check from
`live_check` (`ops/desktop/motodiag_remote.py` line 247, not 183 as the
prompt says). None of those callers needs a code change: they read exit
codes and two header lines, and both keep their meaning.

1. **What a change touches** (`.claude/skills/deploy/deploy.py`, one new
   function beside `server_masked`).
   - `touched(scope, approved, schema_of)` returns the set of tables the
     change touches, as the ROADMAP row defines it: "the tables its approved
     diff and its scope name". That is: every key of the scope's `tables`;
     every table under the approved exact diff's `rows`; every object under
     the scope's `schema` and the approved diff's `schema` that is a
     `table`, by its name; and for an `index`, `trigger` or `view` named
     there, the table SQLite records it on (`tbl_name` in `sqlite_master`,
     read from the backup, or from live after the apply when the object is
     new). `schema_version` is in every real scope, so it is always touched.
     The set is printed once per run, so the operator can read what the
     check protected.
   - Finish line: on the deploy contract's fixture scope the set is
     `{workflow_templates, checklist_items, schema_version}`; a scope whose
     `schema` adds `index idx_x` on `known_issues` puts `known_issues` in the
     set; a table only the approved diff names (none in the scope) is in
     the set; a table in neither is not.
2. **Before the apply: refuse only a touched table** (`preflight`, the
   drift refusal at line 598).
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
     dry run and the apply is listed, not refused.
3. **After the apply, and in `verify-live`: the approved changes hold,
   the rest is listed** (`apply_live`, `verify_live`, and one new comparison
   beside `exact_gaps` and `shape_gaps`).
   - `approved_holds(approved, now, clock_rule)` returns two lists: `gaps`,
     every leaf of the approved exact diff that is absent from live's diff
     or holds a different value (rows added, removed or changed, their
     fields, and every schema object with its SQL), and `listed`, what
     live's diff holds that the approved diff does not, grouped as
     `table +a ~c -r` for rows the approved diff does not name, `table rowid
     column` for a field that moved in a row it names, and `schema added:
     name` for an object it does not name. An approved value masked as
     `<clock>` matches any timestamp-shaped value, as `shape_gaps` already
     does. `exact_gaps` keeps its job on the fresh dry run in `preflight`,
     where the copy must equal the approved diff both ways; `shape_gaps` is
     replaced by the new comparison in `verify_live` or kept as its gaps
     half, the Engineer's choice, said in the log.
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
     backup. It prints the schema lines and the `rows:` lines as today, the
     set-aside line, then the listed differences, then `equals the approved
     exact diff: yes` when `gaps` is empty, `no` with the gaps when not.
     Exit 3 only on gaps; the F197 lines stay with them: when live's schema
     head is past the phase's own, "later migrations explain the
     difference", else "the difference is not a later migration's". A later
     phase's own additions with every approved change still holding are
     listed, and the exit is 0. Integrity and foreign keys are unchanged
     and still exit 1. Exit 2 with no deploy is unchanged.
   - Finish line: on the fixture database, after a clean apply, a row added
     to `known_issues` or to a stand-in `stripe_event_cursors` is listed and
     `verify-live` exits 0; a migration that creates `stripe_feed_checkins`
     and rows written to it afterwards, as 404's check-ins, are listed and
     the exit is 0; an approved added row deleted from live exits 3; an
     approved changed field written again exits 3 (383's
     `test_a_later_request_on_that_field_fails_verify_live` stays as it
     is); an approved schema object dropped exits 3; a migration that
     writes one value on the copy and another on live makes `apply_live`
     return 1 and the live diff say `no`.
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
   id and the reason; the controls on a touched table keep failing. Each
   control that changed an untouched table is kept in two forms: on a
   touched table (the scope names it) it still refuses before the apply
   and still exits 3 after; on an untouched table it is listed and passes.
   - Finish line: every changed assertion is in the phase log's list, each
     with the K91 sentence that changes it; no test outside that list
     changes.
6. **The deploy skill's record** (`.claude/skills/deploy/SKILL.md`,
   `.claude/skills/deploy/CHANGELOG.md`, `deploy.py`'s module docstring).
   - `SKILL.md`: step 4's bullet "live still equals the backup, but for
     the columns the running API writes" becomes the rule above, dated,
     with K91; step 5 says what `verify-live` now asks and what exit 3 now
     means; the line under "From the Mac" that reads "Before Phase 405
     lands, a database step stops the payments feed and stays at the
     desktop (K91)" is replaced by what holds after it: a database step no
     longer needs the feed stopped; "What it holds, and what it cannot"
     gains the new rule's limit: after the apply, a row the migration wrote
     on live but not on the copy cannot be told from a row the running code
     wrote, and is listed, not failed; the comparison before the apply (the
     fresh dry run must equal the approved diff) is where a migration's own
     surprise is caught.
   - `CHANGELOG.md`: a dated entry at the top, "2026-11-2x — the check
     asks what the change did (Phase 405, K91, F210, F259)", naming the
     functions, the tests and the mutation count.
   - `deploy.py`'s docstring (lines 18 to 34) says the same in its `apply-live`
     and `verify-live` lines.
   - Finish line: `git grep -n -F 'live equals the backup' -- .claude/skills/deploy`
     finds no line that still states the old rule as current.
7. **Documents.** `docs/FOLLOWUPS.md` gains, at close-out, the closing lines
   for F259 and F210 in the form F270's has, each saying "once merged and
   live" until the handoff records the live step; if Step 0 or the build
   finds a case the rule does not cover, the Engineer files a finding with
   the `finding` skill before any document cites its number. The ROADMAP
   row moves with the work. The handoff carries the live step as paste
   blocks, each saying which computer and which window, ending in ALL GOOD
   or SOMETHING IS OFF, every `gh` call naming `-R Kubanjaze/moto-diag`
   (R8). `docs/decisions.md` on this branch ends at K94; K95's row is the
   Yeoman's, on master, and this plan cites it from the Step 0 report.
8. **Finish line for the phase:** every test under Tests green and the new
   file seen red on master's `deploy.py`; the mutations red;
   `COLLECTED_TEST_FLOOR` raised by a diff of collected ids; the quality
   counts at their pins (no function in `deploy.py` crosses McCabe 20: the
   new comparison and the touched set are their own functions; coverage
   does not fall); the regression of record inside the fence after
   `wholetree.sh`; `verify_phase.sh`; the handoff.

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
  the listed lines, whether `shape_gaps` is kept as the gaps half or
  replaced, the names of the new functions), either choice ships the same
  behaviour.
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
  **Three readings, recorded, told to the operator with the pull
  request:** (1) an index, trigger or view the scope or the approved diff
  names counts its table as touched, by `tbl_name` in `sqlite_master`;
  (2) the after-apply scope check over the whole live diff is replaced by
  the approved-holds comparison, because K91 says a difference the running
  code made is listed, and the scope stays checked twice before the apply;
  (3) `verify-live` for an older phase passes when every approved change
  still holds and later migrations only added other objects, and still
  fails, naming the later migration, when one altered or removed an
  approved change. If the Engineer finds a case where any of the three
  could go two ways on live, that is a stop.
- **A test that cannot be made green: none known.** The existing controls
  that change are named under Tests, each with the reason in the commit
  message. If a test outside that list (357's exact comparison, 358's other
  refusals, 395's and 406's caller tests, 379's check 8 tests) cannot be
  made green inside K91's words, the Engineer stops.
- **A login or a credential: none.** Every test runs on fixture databases
  in a temporary git repository, through 358's deploy contract; nothing
  reads live, the backups folder or the network.
- **A live-database change that alters or deletes rows: none.** The phase
  has no migration and changes no live row. The live step after the merge
  moves the fleet's code copy and runs read-only checks. Any live write,
  or any stop or start of the payments feed or the server, is a stop.

## Tests

- `tests/test_phase405_what_the_change_did.py`, on 358's `env` fixture
  and its scope (touched: `workflow_templates`, `checklist_items`,
  `schema_version`; untouched: `known_issues`, and stand-in tables
  `stripe_event_cursors`, `stripe_feed_checkins` and `work_orders` the
  fixture adds, named for the writers F259 and F210 describe):
  - **the touched set:** the fixture scope's three tables; a scope whose
    `schema` adds an index on `known_issues` adds that table; a table only
    the approved diff names is in; a table in neither is out;
  - **before the apply, listed and applied:** a `stripe_event_cursors` row
    rewritten between the dry run and the apply; a `work_orders` row added
    (a shop's own write, F210); a `known_issues` row added (358's old
    control, now listed); in each, `apply_live` returns 0, live holds the
    approved change, the output names the table under "outside the tables
    this change touches", and the live diff's header reads `Equals the
    approved exact diff: yes` with the table under `Other differences,
    listed`;
  - **before the apply, refused:** a row added to, changed in and removed
    from `checklist_items`; a row added to `workflow_templates`; a change
    to a table that is touched only through an index the scope names; each
    exits 2 with "changed since the dry run", and live is untouched (358's
    `_refusal`);
  - **after the apply, listed and passing:** a new `known_issues` row; a
    `stripe_event_cursors` row rewritten; a migration that creates
    `stripe_feed_checkins` (the scope's `schema` names it) and three rows
    written to it afterwards, as 404's check-ins; a later phase's
    `schema_version` row and a new row in a touched table (379's old
    case); each `verify_live` exits 0 and prints the table in the listed
    lines;
  - **after the apply, failing:** an approved added row deleted from live;
    an approved changed field written back to its old value; an approved
    added row's other field changed; an approved index dropped; each
    `verify_live` exits 3 and says `no`, with the F197 line naming whether
    a later migration explains it; and the apply's own check: a migration
    that writes one value on the copy and another on live makes
    `apply_live` return 1, the live diff say `no`, and `verify_live` exit 3;
  - **the other gates unchanged, run again here as controls:** a fresh dry
    run differing in one field refuses (357's case); a scope file changed
    refuses; the backup gone refuses; a foreign-key break exits 1;
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
  - `tests/test_phase379_verify_live_fails.py`
    `test_an_approved_diff_missing_a_live_row_fails`: becomes "an approved
    row missing on live" (the row deleted from live), exit 3; its old
    shape, live holding a row the approved diff does not, becomes a listed
    case; `test_a_later_migration_is_named_as_the_cause_and_still_fails`:
    the later migration alters an approved row, exit 3 with the F197 line;
    its old shape (a later row added) becomes a listed case;
  - `tests/test_phase383_server_writes.py` `TestTheControlsStillFail` and
    `TestAWholeTableKeepsItsControls`: each control kept on a touched
    table under a scope that names it (383's `_scoped` form), and its
    untouched form moved to the listed cases; `test_the_list_is_exactly_this`
    and `TestAMigrationThatWritesTheColumn` unchanged;
  - `tests/test_phase385_server_writes.py` `TestTheControlsStillFail`: the
    same, under a scope naming `device_tokens`; `other_table` becomes a
    listed case in both positions;
  - `tests/test_phase348_server_writes.py`: unchanged (it tests
    `server_masked` alone);
  - `tests/test_phase357_deploy_exact.py`: unchanged.
- Old code: the new file run against master's `deploy.py`, red, with the
  controls green.
- Mutations, `405_mutate.py`, each a string in `deploy.py` replaced and the
  named tests run, every file restored: the touched set returned as every
  table of the backup (the old rule; the listed-and-applied cases go red);
  the touched set returned empty (the refused cases go red); the gaps half
  of the comparison returning `[]` (the failing cases go red); the listed
  half counted as gaps (the listed-and-passing cases go red); an index's
  table left out of the touched set (the index case goes red); the clock
  rule dropped from the comparison (the clean read-back goes red).
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
stays true. The desktop's installed dispatcher and sudoers (406's, installed
once; nothing here changes the fixed list). A shop's own traffic and
onboarding (330). The engineer gate's deploy-folder refusal
(`engineer.verify_deploy`), which K95 says does not apply here and which is
not changed. The K95 row in `docs/decisions.md` (the Yeoman's, on master).
No seed data, no split and no eval protocol: this phase has none, and it
names no path under `data/`.

## Planned items

- [ ] Step 0 re-measured: the line numbers above, the four callers and what each reads, the `SERVER_WRITES` finding (still used in a touched table before the apply) and the census in the phase log
- [ ] `touched`: the set as the row defines it, printed once per run, with its tests
- [ ] Before the apply: the drift split by the touched set; a touched table refuses with "changed since the dry run"; the rest is listed and the apply goes on
- [ ] After the apply and in `verify-live`: `approved_holds`; the live diff's header keeps its two lines and gains `Other differences, listed`; exit 3 only on gaps, the F197 lines kept
- [ ] The existing controls moved where K91 moves the rule, each named in the phase log with its reason; the controls on a touched table still red on their mutations
- [ ] `SKILL.md`, `CHANGELOG.md` and the module docstring say what the check now asks, dated, with K91
- [ ] New tests red on master's `deploy.py`; the callers' tests green unchanged; `405_mutate.py` red; `COLLECTED_TEST_FLOOR` raised by a diff of collected ids; the quality counts at their pins
- [ ] The regression of record inside the fence; `verify_phase.sh`
- [ ] The close-out: FOLLOWUPS closing lines for F259 and F210 "once merged and live"; any uncovered case filed as a finding; the ROADMAP row ✅ with CLOSED date and regression line; the handoff with the live step (the fleet's code copy onto the merge and the fleet restarted; from the Mac, `verify_phase.sh 404 29e21a3 d797d8e` and for 405, check 8 passing with the feed's writes listed) as paste blocks ending in ALL GOOD or SOMETHING IS OFF
