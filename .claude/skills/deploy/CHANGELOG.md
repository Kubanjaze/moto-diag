# deploy — changelog

## 2026-10-31 — device_tokens.last_seen_at joins SERVER_WRITES (Phase 385, K39, F212)

The operator, 2026-10-21: "add device_tokens.last_seen_at to the list as its
own phase" (K39), scoped to that one column. The app's push registration
(`POST /v1/push/register`, `push/registry.py` `register_token`) refreshes
the column on every registration, so 384's check 8 failed on one changed
row nothing deployed (F212).

`deploy.py`: one line, `SERVER_WRITES["device_tokens"] =
frozenset({"last_seen_at"})`, and its comment. `server_masked`,
`WHOLE_TABLE` and every refusal are unchanged. The upsert's rebind of
`user_id` and `platform`, and a new token row, are not listed (F210).
Held by the pin in `tests/test_phase383_server_writes.py` and by
`tests/test_phase385_server_writes.py` (19 tests: the registration set
aside, the three controls before and after the apply, beside a
registration and alone, the migration that names the column, the real
`register_token` on a fresh database). `385_mutate.py`: 5/5 red, each of the
three controls seen failing on its own mutation.

## 2026-10-29 — audit_events joins SERVER_WRITES as a whole table (K59, before Phase 348)

The operator, 2026-10-29: "audit_events joins SERVER_WRITES as a whole
table: it is append-only and only the server writes it." That changes a
gate's definition (F212), so it is the operator's (K59). It is built here, on
master, before 348: 395's database step runs only master's deploy tools, and
`engineer.verify_deploy` refuses a phase branch that changes
`.claude/skills/deploy/` (the operator chose "on master first").

`deploy.py`: `WHOLE_TABLE`, and `SERVER_WRITES["audit_events"]` set to it.
For such a table `server_masked` sets aside each row the running API adds
(`audit_events <rowid> added`), except one the approved exact diff names as
added; a changed or removed row stays in the diff and refuses the apply or
fails verify-live, as before. Until 348's migration makes the table, the
entry matches nothing. Held by `tests/test_phase383_server_writes.py`
(the pin, and six tests: three that set aside, three controls), each class
seen to go red on a planted break.

## 2026-10-29 — through the fleet (Phase 395, K58, F232)

`through_fleet.py`, new: the work of the paste block the fleet hands the
operator for a phase with a migration (the dry run on a copy, the change
in plain words, the operator's yes, `apply-live`, `verify-live`), run with
master's code against the branch's `src/`. No refusal in `deploy.py`
changed; `deploy.py` is unchanged. "Through the fleet" in `SKILL.md`.
Bug fix #1 (the trial): the question opens `/dev/tty` twice, once to write
and once to read.

## 2026-10-22 — a dispatcher logs in on the subscription, and the Haiku billing check (Phase 386)

A procedure, not code. It is here because the fleet's dispatcher will run
on the desktop, which this skill already reaches; the phase that builds
the dispatcher runs it. The operator's decision of 2026-10-22: the fleet
runs on the Max subscription, not on an API key (the fleet proposal,
"Decisions taken"). Phase 386's Step 0 found this Mac already that way:
no `ANTHROPIC_API_KEY` anywhere, and `orchestrate.py`'s Anthropic stages
carry only `CLAUDE_CODE_OAUTH_TOKEN`.

**Logging the dispatcher in.** On the machine, as the user the dispatcher
runs as:
1. **No API key in its environment.** Print only whether each is set,
   never a value: the shell (`printenv ANTHROPIC_API_KEY >/dev/null &&
   echo SET || echo unset`); the shell profiles and `/etc/environment`
   (`grep -l ANTHROPIC_API_KEY …`); the service manager
   (`systemctl --user show-environment`, and the dispatcher unit's
   `Environment=` and `EnvironmentFile=`); Claude Code's `settings.json`
   files (`env`, `apiKeyHelper`). Every one says unset or names nothing.
2. **The login is the operator's** (rule 1). In that user's terminal the
   operator runs `claude setup-token` (its help: "Set up a long-lived
   authentication token (requires Claude subscription)"), signs in with
   the Max account, and puts the token it prints into
   `~/.config/motodiag/anthropic.env` as one line,
   `CLAUDE_CODE_OAUTH_TOKEN=…`, then `chmod 600` the file. The token is
   never pasted into a chat, a commit, a log or a prompt.
3. **The token's class, without printing it:**
   `grep -c '^CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat' ~/.config/motodiag/anthropic.env`
   prints 1 and `grep -c 'sk-ant-api' ~/.config/motodiag/anthropic.env`
   prints 0 (an OAuth token, not a Console key).
4. **Every call gets an environment built from nothing** carrying that one
   variable, as `orchestrate.py`'s `run_stage` does, and refuses if any
   other credential is present, as its `check_route` does. Which
   credential Claude Code would prefer if a key were also present is not
   relied on: the environment cannot hold one.

**The Haiku billing check,** the dispatcher's first unattended stage:
1. **Before:** the operator notes claude.ai Settings > Usage (the session
   and weekly figures) and the Console's billing page for the
   organisation.
2. **One call**, nothing else running on the account:
   ```
   TOKEN=$(sed -n 's/^CLAUDE_CODE_OAUTH_TOKEN=//p' ~/.config/motodiag/anthropic.env)
   env -i HOME="$HOME" PATH="$PATH" TERM=dumb CLAUDE_CODE_OAUTH_TOKEN="$TOKEN" \
     claude -p "Reply with the single word OK." --model claude-haiku-5-5 \
     --tools "" --output-format json --no-session-persistence \
     | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sorted(d.get("modelUsage") or {}), d.get("is_error"), d.get("result"))'
   ```
   It passes when `modelUsage` names only the Haiku model asked for,
   `is_error` is false and the reply is OK.
3. **After:** the operator confirms claude.ai Settings > Usage moved and
   the Console's billing did not. One short call may not move a figure
   shown in whole percent; no movement is not a pass. Then the check is
   repeated after a known larger use, never concluded from silence.
4. **If the Console moved,** the dispatcher is billing a key: nothing
   unattended runs until the key is found and removed, and step 1 of the
   login is done again.

## 2026-10-20 — the Mac drives the desktop's steps (Phase 384)

The operator: "1A, 2A (i), 3A".
- **`remote.py`** on the Mac sends one operation from a fixed list to the
  desktop, over SSH to `motodiag-ops` on the tailnet, with the operator's
  key; exit 4 with no way in. An operation that runs code names HEAD, clean
  and pushed.
- **`ops/desktop/motodiag_remote.py`**, the key's forced command, runs only
  the list, each argument held by a pattern, every request logged; the
  checkout detached at the Mac's commit; written diffs to the outbox.
- **`fetch`**: the Mac writes a desktop file only on an equal sha256, and
  commits it under its own guards; the desktop never commits.
- **`media_check.py`**: every video through the file route on a read-only
  copy of live, each body equal to the sha256 its row recorded at upload.
- **verify_phase.sh** checks 8 and 9 go through the way in where live is
  elsewhere.
- `tests/test_phase384_*.py`.

## 2026-10-19 — the gates on a live the API writes; a passing regression (Phase 383, F208, F206)

The operator: "2A with apply-live following it, check 8 unchanged".
- **`SERVER_WRITES`** = `{"api_keys": {"last_used_at"}}`, the one column
  the running API writes by itself. apply-live's "changed since the dry
  run", its after-apply comparison and verify-live set aside a change
  confined to it, print each, and the live diff names them. Anything else
  still refuses or exits 3; a field the approved diff names is compared
  exactly; the dry runs are not masked.
  `tests/test_phase383_server_writes.py`. F210: the list cannot hold once
  a shop's traffic reaches live.
- **K18** refuses a regression line that records a failure, an error, a
  nonzero exit or an unpinned skip (F206), with the reason.

## 2026-10-19 — live moved to the home desktop; live.json, `backup`, exit 4 (Phase 382)

- **Where live is.** The `LIVE` constant (`data/motodiag.db` in the
  checkout) is gone. `live.py` reads `~/.config/motodiag/live.json` on each
  machine; `dryrun`, `apply-live`, `verify-live` and `backup` take live from
  it, and refuse with exit 4 before touching anything when it is missing,
  `null` (the Mac) or names no file. `verify_phase.sh` check 8 and the
  source-transmission tools read it too.
- **Backups** refuse a Windows drive or a cloud-synced folder.
- **`backup [label]`** is a new mode: a backup-API copy, retain-5, its sha256.
- **The deploy runs on the desktop** (the operator's 1A); after the merge,
  the server's checkout pulls master and the unit restarts. SKILL.md has the
  commands.
- **A change with no migration** passes its own `migrate` to `dryrun` and
  `apply_live` from a phase script (382's 6 video paths).
- Held by `tests/test_phase382_live_location.py` (30 tests, 21/21 mutations
  red in `382_mutate.py`); every mode exiting 4 on the Mac's file is among them.

## 2026-10-08 — seed parity covers removed rows (Phase 381)

- **The gap.** `seed_parity` compared only added and changed rows. A
  migration that removes a row whose key is still a seed entry passed, and
  the next fresh build would bring the row back. Phase 381's migration 086
  removes three (F149).
- **The change.** A removed row's `row_key` that a fresh seed build still
  holds is a scope problem: "seed parity: removed row_key … is still a seed
  entry". `tests/test_phase381_content_batch.py::TestParityForRemovedRows`
  holds it, and the mutation that drops the check goes red (`381_mutate.py`
  P1).

## 2026-10-08 — the diff sees a column a migration adds (Phase 380, bug fix #1)

- **The defect.** `diff()` kept only the old table's columns. For a migration
  adding a column, a scope `to` on it crashed (085's dry run), the exact diff
  dropped its values, and a change in it was not a moved field.
- **The change.** Both sides are lined up on the union of the two column
  lists. `tests/test_phase380_deploy_new_column.py` gives 3 failed before
  the fix and 3 passed after.

## 2026-10-08 — seed parity for content migrations (Phase 380, the operator's 2A)

The operator: "With 2A, each content migration's dry run shows the changed
rows equal a fresh seed build, by key, so the seed and live can't drift."
- `seed_parity` builds the seed at HEAD on a scratch database (`init_db` and
  every known-issue seed file), then compares every `known_issues` row the
  migration adds or changes, by `row_key`, every column but the id and the
  clocks.
- A difference, or a key no seed entry holds, is a scope problem. The dry run
  records it, and `apply-live` refuses, both on the recorded problem and on
  its own fresh run.
- It runs only when the copy has `row_key` (migration 085 on).
- The build is injectable (`parity_build`), so
  `tests/test_phase380_seed_parity.py` never builds the real seed. It covers
  a clean case, a drifting migration, a seed edited after the approval, and
  a key no seed holds.
- Its first real run read the backup's columns, which have no `row_key`, and
  checked nothing in 0.0 s. It now reads the copy's columns.

## 2026-10-08 — verify-live fails on a mismatch (Phase 379, F197)

The operator: "379 = the nine small fixes."
- `verify-live` exits 3 when live does not equal the approved exact diff.
  Before, it printed "no" and exited 0, which is how the advisor found it
  on 376.
- It says whether live's schema version is above the phase's own (read
  from the dry run's "Migrations applied on the copy"), in which case a
  later migration explains the difference.
- `tests/test_phase379_verify_live_fails.py`: the known-bad case is an
  approved diff missing one live row.

## 2026-10-07 — apply-live after the regression of record; verify-live (Phase 378, K18, K25, K27)

The operator: "approved: 378 = K18–K25." "K27: (a) now, (b) once the
first shop's real data is in."

- **K18.** `apply-live` refuses unless:
  - the phase log in `in_progress/` carries a regression line A5 can read
    (`closeout_check.regression_line`);
  - no code path changed between its commit and HEAD
    (`code_after_regression.is_code`, verify_phase's check 2 scope);
  - no code path is uncommitted.

  376 applied 083 before its regression, and nothing stopped it. The
  known-bad logs are `fixtures/k18/`. 358's fixture repository now records
  a regression line, so the older apply tests pass for their own reason.
  `tests/test_phase378_deploy_order.py`.
- **K25.** `verify-live <phase>` is new, read-only. It copies live and the
  phase's backup, the backup opened `immutable=1`; the WAL control shows a
  plain read-only open leaves `-shm`. It prints:
  - the schema and row differences;
  - whether they equal the approved exact diff (`<clock>` matched by
    shape);
  - integrity and foreign keys.

  `tests/test_phase378_verify_live.py`.
- **K27.** The skill records the operator's call: 5 backups now, 5 plus the
  first of each week once the first shop's real data is in. `KEEP` is
  unchanged.

## 2026-09-28 — apply-live compares the fresh dry run with the approved diff (Phase 357, F172)

The operator: "Make `deploy.py apply-live` refuse unless its fresh dry
run's diff equals the committed diff field for field, with timestamps
masked." Phase 359 made this comparison by hand.
- **The dry-run file ends with the exact diff**, as JSON after a second
  marker: every field of every added and removed row, before and after of
  every changed field. The markdown report shows only three fields of an
  added row, so it could not be the thing compared.
- **Clock values are masked** as `<clock>`: a timestamp-shaped value
  within one day of the run's own UTC clock. That is what 359 masked by
  hand (the new `applied_at`, four `updated_at`). A fixed date is compared.
- **apply-live refuses** when a fresh run differs in any field, naming
  each by its path, and refuses a diff file written before this change.
  After the live apply, the live diff says whether live equals the
  approved exact diff; a difference there is a scope problem, exit 1.
- **Schema objects are diffed and scoped** too: tables, indexes, triggers
  and views added, removed or rewritten, with their SQL. Phase 357's
  migration adds tables and no rows but one `schema_version` row, so a
  rows-only diff would not have shown what the operator approves. A
  scope names them under `"schema"`.
- **Controls:** `tests/test_phase357_deploy_exact.py` — one field differs
  (refused; the same edit passes the scope check alone), only the clock
  differs (applies), a fixed date differs (refused), an old diff file
  (refused), an unnamed new table (scope problem), a named table whose
  SQL differs (refused). `357_mutate.py F172`: 6/6 red.

## 2026-09-27 — a scope entry's `to` (Phase 359)

The operator's condition on live row 4615: "the dry-run diff shows 4615
changing only to its seed text, field for field, and nothing else." A
scope entry's `fields` already hold "nothing else". A new optional `to`
(`{field: value}`) holds "only to": after the migration the field must
equal that value. Otherwise it is a scope problem, so the dry run records
it and apply-live refuses.
- **Checked** in the dry run, the pre-apply fresh run, and after the live
  apply (`expected()`, and `check_scope`'s new argument).
- **The problem message has no backticks:** the diff header's parser reads
  a value between them, and a backtick in the message broke it (found by
  the new test).
- `tests/test_phase359_deploy_to.py` holds the known-bad case: the allowed
  field changes, but to other text. Ignoring `to` turned it red (Phase 359
  mutation M4).
- First real use: Phase 359's scope gives every changed field its value:
  26 known-issue rows, 4 templates, 2 items.

## 2026-09-27 — created (Phase 358, K3)

The operator: "deploy script in the repo. it writes the approved dry-run
diff into the phase folder, and the live apply refuses to run without that
file. no more temp copies." And, accepted at v1.0: "live apply refuses
unless the diff file is committed and unchanged."

- **Where it came from:** Phase 262's `deploy262.py`, kept verbatim with
  its sha256 in `358_step0.md`. What changed from it:
  - the scope is JSON in the phase folder, no longer Python constants;
  - the diff goes to the phase folder, no longer the scratchpad;
  - copies go to the gitignored `data/deploy_scratch/` and are deleted;
  - the census is `scripts/f158_census.py`;
  - the paths are arguments;
  - the apply refuses without a committed, unchanged diff, and when the
    diff records a scope problem, the backup's hash moved, or the scope
    file changed.
- **Controls, in the contract test, on fixture databases:**
  - each refusal: no file, uncommitted, edited after commit, an
    out-of-scope dry run, live changed, a fresh dry run out of scope, the
    scope changed, the backup gone;
  - a clean apply;
  - retain-5;
  - an ambiguous scope entry refused.
- **Four mutations were each seen red and reverted:** the committed check,
  the unchanged check, live-equals-backup, and the fresh scope check.
  Under each, the fixture's "live" was migrated.
- **358 never ran it against live.** Its first real use is the content
  phase.
