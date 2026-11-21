# Phase 330 — phase log

**Status:** Complete

## 2026-11-21 — Step 0, re-measured by the Engineer

On this branch at `bc2f7bf` (v1.0, the Executive Officer's round 2).

- **`src/motodiag/cli/shop.py`,** as the plan reads: `_sole_shop_id_or_fail`
  217, `_resolve_shop_identifier` 258 (no identifier: `list_shops()`, owner
  1 by default; several shops: "Multiple shops exist (...); pass --shop NAME
  or --shop ID.", a `ClickException`, exit 1), `register_shop` 622, the
  `shop` group 633, `profile init` 644 (calls `create_shop` with no owner),
  `profile show` 692, `profile list` 707 (`list_shops(include_inactive=...)`),
  `customer add` 804, `customer link-bike` 992, `customer bikes` 1056,
  `member add` 4294, `member list` 4314, `register_inventory(shop_group)`
  4761.
- **The default owner:** `create_shop` 138 (`owner_user_id: int = 1` at
  148), `get_shop_by_name` 191 (`owner_user_id: int = 1`), `list_shops` 205
  (`owner_user_id: Optional[int] = 1`; `None` is every shop; ordered by
  `s.name, s.id`).
- **`src/motodiag/cli/main.py`:** `cli` 45, `garage` 441, `garage add` 506,
  `garage list` 546, `register_shop(cli)` 912, `register_user(cli)` 924,
  `register_workflow(cli)` 952.
- **`src/motodiag/cli/user.py`:** `_read_password` 43, `_hash_or_fail` 51,
  `register_user` 76, `user create` 83 (its function at 89);
  `MIN_PASSWORD_LENGTH = 8` (`auth/passwords.py` 31).
- **`src/motodiag/cli/workflow.py`:** `register_workflow` 57,
  `_template_or_refuse` 154, `POWERTRAINS` 169, `_walk` 173, `run` 199,
  `run_cmd` 207 (powertrain exit at 221 to 226), `start` 355 (its options
  `--bike`, `--vehicle-id`, `--work-order`, `--powertrain`).
  `template_repo.py`: `get_template_by_slug` 54, `list_templates` 63,
  `get_checklist_items` 168.
- **A fresh migrated database** holds 13 active templates (the first,
  `brake_service_v1`, covers `ice`, `electric`, `hybrid`, 7 items), one
  user (the system user, id 1), one customer (the seeded "Unassigned",
  id 1), and no row in `shops`, `shop_members`, `terms_acceptances`,
  `vehicles`, `customer_bikes` or `workflow_runs`.
- **The name:** `git grep -n -i onboard -- src/motodiag/cli` finds 4 lines,
  all in `payments.py` (31, 245, 251, 258), as the plan reads. No `onboard`
  group exists.
- **The `cli_db` fixture,** `tests/test_phase160_shop.py` 105 to 116, as
  the plan reads; `_make_cli` at 86 registers only `shop`.
- **Pins:** no test reads `cli.commands['shop'].commands` or counts the
  `shop` sub-groups or the root's commands (`grep -rn` over `tests/` for
  `commands['shop']`, `commands["shop"]`, `register_inventory(shop_group)`
  and `len(...commands)`: 0 lines). `docs/guide/shop-workflow.md` is read by
  `tests/test_phase208_docs.py`, which resolves every `motodiag` command in
  a `bash` block against the Click registry; the new paragraph's commands
  must therefore exist, which they do once the group is registered.

## 2026-11-21 — the build

- **`src/motodiag/crm/bike_import.py`** (new): `BikeRow`, `ImportReport`,
  `parse_row` (one row's values through `VehicleBase`), `read_bike_rows`
  (header checked first; every row checked; a duplicate VIN names both
  lines) and `import_bikes`. `import_bikes` takes the problems as a keyword
  (`problems=`) and a `dry_run` keyword: the plan's signature is
  `import_bikes(rows, shop_id, db_path)`, and both the "nothing is written
  when problems is not empty" rule and `--dry-run` need the function to
  know them. A dry run walks the same code and writes nothing; a customer
  it would make is kept in memory so a later row of the same file matches
  it, as the write does.
- **`src/motodiag/cli/shop_onboard.py`** (new): `register_onboard`, the
  `onboard` group with `status`, `run` and `import-bikes`; one function per
  row (`step_shop`, `step_owner`, `step_staff`, `step_terms`,
  `step_bikes`), each `(done, detail)`, shared by `status` and `run`.
  `status` with no `--shop` reads `list_shops()` (owner 1, active, the
  order `profile list` uses: by name, then id), and with no shop prints one
  block of `not yet` rows; it never calls `_resolve_shop_identifier(None)`.
  `run` and `import-bikes` resolve one shop through
  `_resolve_shop_identifier` (several shops and no `--shop`: its own
  "Multiple shops exist" refusal, exit 1). The walk is
  `ctx.invoke(run_cmd, slug=..., powertrain=...)`, with the slug a Choice
  over the active slugs and the powertrain a Choice over that template's
  `applicable_powertrains`.
- **`src/motodiag/cli/shop.py`:** the import line and
  `register_onboard(shop_group)` beside `register_inventory(shop_group)`;
  nothing else.
- **Choices the plan left open,** each shipping the same behaviour:
  - The four steps after the shop ask "Do this step now?" even when no shop
    exists, so the declined input string has its five answers; a `y` there
    with no shop says the step needs the shop first and writes nothing.
  - The terms step, when the shop has no owner, says the owner's login step
    comes first and asks nothing more.
  - The hand-typed bike asks whether to add one ("Add one bike by hand?
    [y/N]") after `n` to the CSV question; its powertrain is a Choice of
    `ice`, `electric`, `hybrid` and `unknown` (the default, stored as
    none).
  - The walkthrough's default powertrain reads the shop's newest linked
    bike (the highest vehicle id linked to one of its customers), so it is
    the last imported bike whether it came in on this run or an earlier
    one.
- **The five readings, recorded** (also for the pull request's text):
  1. The wizard is the server's command line, not an app screen or an API
     route; an app screen is a row of the operator's own making.
  2. "Bike inventory" is the shop's customers' bikes (`vehicles`,
     `customers`, `customer_bikes`), not parts stock, which stays with
     `shop inventory add`, named on the closing screen.
  3. The shop's `owner_user_id` stays the default 1, as `profile init`
     leaves it; ownership is the `owner` role in `shop_members`. Held by
     the happy-path test (`profile show` with no `--shop` finds the shop;
     `shops.owner_user_id` is 1) and mutation M12.
  4. The terms are accepted only by the one owner who says they are at the
     keyboard, for themselves; never for staff, never for an absent owner.
  5. A bike is identified only by its VIN; a row without one is added
     again on every import, and the report counts it.
  None of the five needed an existing command's behaviour to change.
- **Tests,** `tests/test_phase330_onboarding.py`: 31 functions, 35 ids, on
  `motodiag.cli.main.cli`, every database a fresh migrated one under
  `tmp_path`. The run's "declined" case checks that every one of the eight
  tables holds exactly what a fresh database holds: a fresh database is
  not empty (the system user and the "Unassigned" customer are seeded by
  their migrations), so "empty afterwards" is read as "unchanged", and
  `shops` is checked to be 0.
- **Old code:** the new file, copied into a worktree at `bc2f7bf` and run
  with that tree's `src` first on the path, fails at collection
  (`ModuleNotFoundError: No module named 'motodiag.crm.bike_import'`); the
  controls on the same tree, 197 passed: `test_phase160_shop.py`,
  `test_phase172_rbac.py`, `test_phase303_user_cli.py`,
  `test_phase334_terms_routes.py`, `test_phase356_workflow_run.py`,
  `test_phase357_saved_runs.py`.
- **Controls on this branch,** 389 passed: those six files, every other
  `test_phase303_*`, `test_phase334_*`, `test_phase357_*` file,
  `test_phase208_docs.py` (the guide's commands resolve) and the new file.
- **Mutations,** `330_mutate.py`, 388's harness: 17/17 red
  (`330_mutate.out`). Two differ from the plan's list:
  - M10 (the terms row's owner-exists condition removed) stayed green on
    the first run against the fresh-database `status` test: with no shop
    at all, the terms row is `not yet` through the no-shop branch before
    the owner check is reached. The case the condition holds is a shop
    with no owner member, and M10 now runs
    `test_a_shop_with_no_owner_leaves_terms_not_yet_whatever_acceptances_hold`,
    red. A harness target, not a code defect.
  - The plan's "customer match widened to a LIKE on the phone (the
    other-shop case red)": the other-shop case is held by
    `search_customers(..., shop_id=...)`, not by the exact comparison, so
    a LIKE inside the shop leaves it green. Two mutations hold the two
    halves: M16 (the exact comparison dropped) turns
    `test_a_phone_that_contains_another_customers_phone_is_not_a_match`
    red, a test added for it; M17 (the shop scope dropped) turns the
    other-shop test red.
- **Quality counts** (`scripts/code_quality.py counts`): ruff 1108, mypy
  202, complex 25, big 5, helpers 19, swallowed 22, every one at its pin.
  The first measure read mypy 204: two errors in the new code (a
  `str | None` assigned to a `str` in the customer match, and
  `create_shop(**fields)`), fixed before the first commit by a
  `_customer_key` helper and named arguments.
- **`COLLECTED_TEST_FLOOR`** 13031 to 13066, by a diff of collected ids
  against `bc2f7bf`: +35 -0, all in the new file.
- **The guide,** `docs/guide/shop-workflow.md` section 0: a paragraph on
  `onboard run`, `status` and `import-bikes` with the CSV columns; the two
  outputs were run against a fresh database at `/fleet/run/s330/g.db`.

## 2026-11-21 — the regression of record

`wholetree.sh --full` on `3d6bc4d` first: 5357 passed, 36 skipped, exit 0
(record `b2483c5a…_full.json`). Then `regression.sh` on the clean tree at
`3d6bc4d`, inside the fleet's fence; its record, as it printed it:


Regression of record: 12961 passed, 0 failed, 105 skipped, 0 errors at `3d6bc4d` (41 min 19 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:104: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:121: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:137: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:145: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:153: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:162: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:175: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:185: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:218: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:223: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:248: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:259: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:272: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:292: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:306: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:321: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:333: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:340: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: inside the fleet's fence: its boundary is proven from the host, not from inside
Line coverage of record: 88.42% at `3d6bc4d` (the pin is 87.50%): 0.92 points above it; raise COVERAGE_PERCENT to lock it in

The quality counts at `3d6bc4d` are those of the build entry, every one at
its pin. `COVERAGE_PERCENT` is left at 87.50%: raising it is a change under
`tests/` after the regression of record, and no rule asks this phase for
it. The handoff names it.

## 2026-11-21 — the close-out

- **The live step and `init_db`.** `status`, like every existing `shop`
  command, opens the database through `init_db()`, which applies any
  migration the code has and the database lacks. The server runs with
  `--skip-migrations` because a migration reaches live only through the
  deploy skill. This phase has no migration, so on live at the code's
  schema `init_db` applies nothing. The handoff's live block therefore
  reads live's schema version (read-only) and the server code's
  `SCHEMA_VERSION`, and stops, having run nothing on live, unless they are
  equal. No code changed for it: `status` keeps the existing commands'
  form, and the plan's pass condition (exit 0) is unchanged.
- **Documents:** v1.1 of `330_implementation.md`; the ROADMAP row ✅; the
  root `implementation.md` (0.13.141, its row) and `phase_log.md` pointer;
  the handoff `docs/handoffs/2026-11-21_330_closed.md`; the phase's files
  moved to `docs/phases/completed/`.

## 2026-11-21 — fix round 1: the Red Team's two findings

### Bug fix #1 — 2026-11-21 — `status` with no `--shop` printed shops in name order, not id order

**Issue.** Item 2's finish line and the Tests section say that with two
shops and no `--shop`, two blocks print in id order. `status` printed them
in `list_shops()`'s order, `ORDER BY s.name, s.id`
(`src/motodiag/shop/shop_repo.py` line 232). The test named its shops
"Alpha Moto" (id 1) and "Bravo Cycles" (id 2), so name order and id order
were the same and it passed either way.

**Root cause.** The build reused `profile list`'s order, as the build entry
above records ("by name, then id"), and the test's fixture could not tell
the two orders apart.

**Fix.** `status` sorts `list_shops()` by id. The test's shops are now
"Zulu Cycles" (id 1) and "Alpha Moto" (id 2), so name order is the
reverse of id order. `330_mutate.py` gains M18 (the sort removed, name
order back), red; M15's target string follows the new line.

**Files.** `src/motodiag/cli/shop_onboard.py`,
`tests/test_phase330_onboarding.py`, `docs/phases/completed/330_mutate.py`,
`docs/phases/completed/330_mutate.out`.

**Verified.** The changed test failed on the old line and passes on the
new; the file's 35 tests pass; `330_mutate.py` 18/18 red. The first form
of the fix (`sorted(...)` assigned straight to the `Optional` list) read
mypy 203 against its pin 202 in `wholetree.sh`; a typed local brought it
back to 202 before the commit. No test was added or removed, so
`COLLECTED_TEST_FLOOR` is unchanged.

**Commit.** `ef2cfff`.

### The handoff did not run `verify_phase.sh` — 2026-11-21

v1.1's Deviation 6 said `verify_phase.sh` runs after the merge from the
handoff, and the planned item was ticked, but no paste block in the
handoff called it. Step 1's block now does, on the Mac, after the server
moves onto the merge: it brings the Mac's copy to the merge (stopping
unless the Mac's master is at it, with nothing changed by hand, as 405's
block does), takes the phase's last commit from the merged pull request,
and runs `verify_phase.sh 330` with the regression's commit and that one.
Deviation 6 now names step 1.
