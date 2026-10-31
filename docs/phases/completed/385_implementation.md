# Phase 385 — The push token's own write

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-10-31 (v1.0 `7a29f36`)

---

## Goal

`device_tokens.last_seen_at` joins `SERVER_WRITES`, the set-aside list in
`.claude/skills/deploy/deploy.py` that Phase 383 built, as one more column
entry, on the operator's K39 ("add device_tokens.last_seen_at to the list as
its own phase"), scoped to that one column. The app's push registration
(`src/motodiag/push/registry.py` `register_token`, called from
`src/motodiag/api/routes/push.py`) is an upsert that refreshes that column on
every registration, with no user action, so since 2026-10-21 every comparison
of live with a backup after the phone has registered shows one changed row
nothing deployed (F212). After this phase a change confined to that column of
an existing token row is set aside, printed and named, wherever live is
compared with a backup: apply-live's drift check, its after-apply comparison
and verify-live. 383's three controls each still fail, and each is seen
failing once: another column of that row, an added token row, and the same
column name in another table. F212 is closed; F210's entry names what the
list still cannot cover. No migration and no change to live.

Two of the prompt's measured facts, taken 2026-10-21, have moved and were
re-verified on this branch's base (`ddcdfd6`):
- **The list** is at `deploy.py` line 177, not 171, and holds two entries:
  `api_keys.last_used_at` and, since K59 (2026-10-29, built on master before
  Phase 348), `audit_events` as a whole table (`WHOLE_TABLE`). The pin in
  `tests/test_phase383_server_writes.py` holds both. This phase makes three.
- **Live is past 384.** Phase 348's migration 088 was applied to live on
  2026-10-30 (`docs/phases/completed/348_live_diff.md`: the table
  `audit_events`, its index, two triggers and one `schema_version` row).
  `verify-live 384` compares live with 384's backup of 2026-10-20, so it
  reports those schema objects and exits 3 whatever this phase does. The
  row's words "`verify_phase.sh 384` passes again" cannot be made true by the
  list change alone; that is the fork under "Rule-1 stops anticipated", and
  the live proof this plan hands the operator is the newest deployed phase's
  check, 348's, beside 384's for the record.

## Logic

1. **`.claude/skills/deploy/deploy.py`** (the list only). `SERVER_WRITES`
   gains `"device_tokens": frozenset({"last_seen_at"})`. The comment above it
   gains F212 and K39: the writer (`push/registry.py` `register_token`, the
   upsert's `ON CONFLICT(token) DO UPDATE`, reached through `POST
   /v1/push/register`), and that the same upsert's rebind of `user_id` and
   `platform`, and a new token row, are not listed (F210). `server_masked`,
   `WHOLE_TABLE` and every refusal in the file are unchanged.
   Finish line: the pin equals the three entries; the fixture tests below
   pass with the entry and the set-aside tests go red without it.
2. **`tests/test_phase383_server_writes.py`.** `test_the_list_is_exactly_this`
   pins the three entries, and its docstring names this phase as the one
   that measured the column (384's check 8, F212). Nothing else in the file
   changes: 383's controls on `api_keys` still run as they are.
   Finish line: green on the branch, red on master's two-entry literal.
3. **`tests/test_phase385_server_writes.py`** (new), on 358's deploy
   contract `env` (fixture databases only, never live) and on a fresh
   database at the schema head through `tests/support/phase303.py`'s
   `new_db`, the way `tests/test_phase348_server_writes.py` drives the real
   code. Its cases are listed under Tests.
   Finish line: every case green; every control seen red under
   `385_mutate.py`.
4. **`docs/phases/in_progress/385_mutate.py` and `385_mutate.out`**, in
   383's harness form (exact strings, each occurring once, every file
   restored): the entry removed; the entry widened to `WHOLE_TABLE`; the
   entry widened to `{"last_seen_at", "platform"}`; `last_seen_at` listed
   under the control's second table instead; the pin's literal without the
   new entry. Each must turn its test red, and the three controls' red runs
   are the "each seen failing once" the row promises.
   Finish line: `385_mutate.out` records every mutation red, N/N.
5. **The deploy skill's documents.** `.claude/skills/deploy/SKILL.md`, the
   apply-live bullet that names `SERVER_WRITES`' columns, names the second
   column with F212 and K39, and says what stays outside the list.
   `.claude/skills/deploy/CHANGELOG.md` gains a dated entry at the top, in
   K59's form: the operator's words, the one line changed, the tests and
   mutations that hold it.
   Finish line: both files name the column; `wholetree.sh` passes.
6. **`docs/FOLLOWUPS.md`.** F212 gains a "Closed by Phase 385 (2026-10-30)"
   paragraph naming the entry, the pin and the three controls seen failing.
   F210 gains a paragraph, "What the list still cannot cover", naming: a new
   token row, when the phone's push token changes (an added row in
   `device_tokens`, which the added-row control keeps failing); a rebind,
   when the same token is registered by another user or platform (the
   upsert changes `user_id` or `platform`, which the other-column control
   keeps failing); and a shop's ordinary writes, F210's own case. No new
   finding is filed unless the Engineer finds something the record does
   not name; a new number is taken with the `finding` skill first.
   Finish line: every cited F-number resolves (`finding_check`).
7. **`docs/decisions.md`.** K39's "the check it became" cell changes from
   "None yet" to the entry in `deploy.py`, held by the pin in
   `tests/test_phase383_server_writes.py` and the controls in
   `tests/test_phase385_server_writes.py`, in K59's form.
   Finish line: the cell names paths that exist.
8. **The phase's own record**: `385_phase_log.md` (the re-verified facts
   above, the mutation record, the regression line), this document at v1.1, the ROADMAP row's status, the floor
   in `tests/test_phase255B_collected_test_floor.py` raised by a diff of
   collected ids, and the handoff `docs/handoffs/2026-10-31_385_closed.md` (dated the day
   of the close, for R6; see Deviations).
9. **The handoff's after-the-merge block**, for the operator, in rule 6's
   form: which computer (the Mac), which window (Terminal, in the
   repository folder), one paste block ending in ALL GOOD or SOMETHING IS
   OFF, no internal labels. Before pasting, the operator opens the MotoDiag
   app on their phone once, so the registration happens after 348's backup.
   The block: brings the Mac's `master` up to date; runs
   `verify_phase.sh 385 <regression hash> <merge>` (385 has no dry-run
   diff, so its check 8 reports no deploy to verify); runs
   `remote.py verify-live 348`, the live proof of record (K60), which must
   exit 0, and prints its "set
   aside" line, where the token row appears if the phone registered since
   348's backup; runs `remote.py verify-live 384` for the record and prints
   its lines, without judging it, since live is past 384. ALL GOOD rests on
   385's check and 348's verify-live; any `device_tokens` line outside "set
   aside" in either output is SOMETHING IS OFF. Every `gh` call in the
   block names `-R Kubanjaze/moto-diag` (R8).
   Finish line: the block is in the handoff before the merge, with
   `verify-live 348` exiting 0 from the Mac as the proof of record (K60);
   R6 and R8 pass.

Nothing under `src/` changes. The fleet's folder does not change.

## The change log's three newest entries

- **2026-10-29, rule 6: the code's counts only improve, and the weekly
  page (Phase 393, K54).** The check it became:
  `tests/test_phase393_quality_ratchet.py`. This phase's one changed line in
  `deploy.py` and its new test file are held by it; no pin moves.
- **2026-10-26, R8: an operator paste block's `gh` names its repository
  (before Phase 391, F222).** The check it became:
  `.claude/skills/closeout/roadmap_check.py` (R8), run by
  `tests/test_roadmap_continuity.py`. The handoff's after-the-merge block
  is held to it.
- **2026-10-22, `fleet` joins the procedure folders (after Phase 387).**
  No check: the entry says the row is text only and no check reads the
  table. This phase does not touch the fleet's folder.

## The plan of record

- 'Next, in order': 7. 385 (shop, built by fleet); needs the operator:
  nothing; from: 2026-10-21 · K53.
- The plan of record, 2026-10-21: "**2026-10-21: 385 goes before 345.** It
  is F212, the second column the API writes by itself,
  `device_tokens.last_seen_at`. **Why first:** every deploy's live check
  fails once the app re-registers for notifications, so this comes before
  the next phase with a deploy. **The operator's words:** "add
  device_tokens.last_seen_at to the list as its own phase". **What stays
  open:** F210's general rule is still needed before onboarding (330). **The
  prompt** is `docs/prompts/385_the_push_tokens_own_write.txt`."
- The plan of record, 2026-10-27: "**2026-10-27: 385 joins the list, before
  345 (K53).** The 2026-10-21 entry above put "385 goes before 345", but 385
  had no row, so K48's transcription left it out. **The operator's words:**
  "PR #15 closed under K9; put 385's row on master and 385 before 345 in
  Next, in order, as the 2026-10-21 entry says." **It needs nothing from
  the operator:** its prompt expects no migration and no change to live,
  and names no outside account or rule change beyond the one column the
  operator already approved (K39)."
- K39 (2026-10-21): "add device_tokens.last_seen_at to the list as its own
  phase"; the check it became: "None yet: Phase 385, prompt
  `docs/prompts/385_the_push_tokens_own_write.txt`, not built." This phase
  fills that cell.
- K53 (2026-10-27): "PR #15 closed under K9; put 385's row on master and 385
  before 345 in Next, in order, as the 2026-10-21 entry says."

This phase is not fleet-only: its kind in "Next, in order" is shop, and it
changes the deploy skill, not the fleet's folder, so K43's Unblocks line is
not required. What it clears is the live check of every later phase with a
deploy, 345 first, as the 2026-10-21 entry says.

## Rule-1 stops anticipated

- **A real fork, decided (A)** by the operator, 2026-10-31 (K60): "385's
  live proof is the newest deployed phase's check, verify-live 348 from the
  Mac, with verify-live 384 run for the record only; 384 can no longer pass
  since 348's migration 088." The fork as it was put: the row's live
  proof. The row and the prompt say "`verify_phase.sh 384` passes again from the Mac", but live has been past
  384 since 2026-10-30 (348's migration 088), so `verify-live 384` exits 3
  on 348's schema objects whatever the list holds, and no change in this
  phase can make 384's check 8 pass. Two plans would ship different things:
  (A) the row's live proof becomes the newest deployed phase's check,
  348's, run from the Mac through the way in, and the row's sentence is
  reworded by the operator (recommended: it is the same proof, on a backup
  that predates the phone's next registration); (B) the row keeps 384, and
  its exit 3 is recorded with its reason. Nothing the Engineer builds
  depends on the answer, so it builds everything else, names the fork in
  the phase log and the handoff, and the after-the-merge block prints both
  outputs for the operator's call. The Engineer does not reword the row.
- **A threshold or a rule's definition:** the list is a gate's definition,
  and K39 covers one column. The same upsert writes `user_id` and
  `platform` on a rebind, and a new registration adds a row; neither joins
  the list, both go to F210's entry, and the other-column and added-row
  controls keep failing on them. If the live check from the Mac shows any
  other column or table the running API writes, beyond the three entries,
  that is a stop for the operator, not an addition (the prompt's words).
- **A test that cannot be made green:** none expected; the mechanism is
  383's `server_masked`, unchanged.
- **A login or a credential:** none; the live check runs under the
  operator's own login on the Mac, through 384's way in.
- **A live-database change that alters or deletes rows:** none; no
  migration, and verify-live is read-only. Should the dry run of any later
  phase be needed here, it is out of scope.

## Tests

- **`tests/test_phase385_server_writes.py`**, on 358's `env` with a
  `device_tokens` table of 044's six columns holding row 31, and a second
  table with a `last_seen_at` column that the list does not cover:
  - a registration (the column refreshed on row 31) between the dry run and
    the apply no longer refuses; the live diff equals the approved exact
    diff and names `device_tokens 31 last_seen_at`;
  - a registration after the apply: verify-live exits 0 and prints the row
    among "set aside";
  - both listed columns written in one run, `api_keys 2 last_used_at` and
    `device_tokens 31 last_seen_at`, as 384's live showed on 2026-10-21:
    both set aside, nothing else;
  - the controls, before the apply (refuses, "changed since the dry run")
    and after it (verify-live exits 3): `platform` changed on row 31 (the
    rebind), a token row added, the same column name changed in the second
    table;
  - a migration whose approved diff names `device_tokens.last_seen_at` on
    row 31 shows it in the dry run, and a later registration on that field
    fails verify-live, as 383's test does for `api_keys`;
  - on a fresh database at the schema head (`new_db`, never live): a user
    registers a token twice through the real `register_token`; the diff
    against a backup taken between the two, through `server_masked`, is
    empty with one set-aside line; the control: a second user registering
    the same token (the rebind) leaves `device_tokens` in the diff.
- **`tests/test_phase383_server_writes.py`**: the pin equals the three
  entries, and `SCOPE`'s tables stay disjoint from the list.
- **Mutations** (`385_mutate.py`, `385_mutate.out`): the five under Logic 4,
  each red; the three controls' runs are the row's "each seen failing".
- **The floor** raised by a diff of collected ids against master, the
  reason in the commit message.
- **The whole tree**: `wholetree.sh` before every commit; `wholetree.sh
  --full` before the regression of record; the regression of record by
  `regression.sh`, its line in the phase log.

## Non-goals

F210's general rule (before row 330); `user_id`, `platform` or a new token
row joining the list; any change to `server_masked`, `WHOLE_TABLE` or any
refusal in `deploy.py`; any change under `src/`, including the push
registry and its route; the mobile app's registration code; any migration;
any change to live, any backup, and the retention of backups; 384's row,
documents or dry-run diff; rewording 385's row (the operator's); the fleet's
folder; F207, F209 and F211; a regression on the desktop outside the fence.

## Planned items

- [x] the entry in `deploy.py`, with its comment
- [x] the pin in `tests/test_phase383_server_writes.py`
- [x] `tests/test_phase385_server_writes.py`: the set-aside cases, the three controls before and after the apply, the migration case, the real `register_token` case
- [x] `385_mutate.py` and `385_mutate.out`, every mutation red
- [x] the deploy skill's `SKILL.md` and `CHANGELOG.md`
- [x] F212 closed; F210's paragraph on what the list still cannot cover; K39's cell in `docs/decisions.md`
- [x] the floor raised by a diff of collected ids
- [x] `wholetree.sh --full`, the regression of record, the close-out, this document at v1.1
- [x] the handoff with the Mac's after-the-merge block, and the fork named for the operator

## Deviations

What the build did that v1.0 does not say, each with its reason. The phase log has the dated detail.

- **Each control runs twice, beside a registration and alone** (12 control tests, not the 6 the Tests section implies). With the entry widened to `WHOLE_TABLE` (Logic 4's second mutation), an added-row control made only beside a registration stays green: the registration's changed row is itself drift under a whole-table entry, so the refusal fires anyway (measured: `-k "added_row and beside"`, 2 passed). Alone, the control goes red on that mutation, so the added-row control is seen failing as the row promises.
- **Each mutation runs against the test it must turn red**, by `-k`: E2 to E4 each select one control, so their red runs are the three controls seen failing, not a set-aside test the same mutation also breaks.
- **The second table is a fixture table, `phones`**, with a `last_seen_at` column; Logic 4's "listed under the control's second table instead" is that table.
- **`TestTheRealRegistration` fixes `register_token`'s clock** (`monkeypatch` of `registry._now`) for the second registration, so the refreshed `last_seen_at` differs from the first by construction, not by the clock's resolution. Both users are made before the backup, so the rebind control's diff is `device_tokens` alone.
- **The handoff is dated 2026-10-31**, not 2026-10-30 as Logic 8 names it: the close is on 2026-10-31, and R6 wants a handoff no earlier than the close. F212's closing paragraph carries the same date.
- **The after-the-merge block runs no `gh`**: it finds the merge as the Mac's `master` after a fast-forward, and checks that the regression's commit is in it.
- **One edit-guard block**: a Python script body writing v1.1 into this document was refused, since its text named `tests/`. The guard is unchanged; the Edit tool did the work.
- **No bug fixes**, no new finding.

## Results

- **Shipped.** `SERVER_WRITES["device_tokens"] = frozenset({"last_seen_at"})` in `.claude/skills/deploy/deploy.py`, with its comment; `server_masked`, `WHOLE_TABLE` and every refusal unchanged. The pin in `tests/test_phase383_server_writes.py` holds the three entries. Nothing under `src/` changed; no migration; no change to live.
- **Tests.** `tests/test_phase385_server_writes.py`, 19 tests: the registration set aside between the dry run and the apply and after it, and beside 383's request (both set aside, nothing else); the three controls (the rebind of `platform`, an added token row, `last_seen_at` in another table) before and after the apply, beside a registration and alone; a migration whose approved diff names the column; the real `register_token` on a fresh database at the schema head, with the rebind by another user as its control. `COLLECTED_TEST_FLOOR` 12133 → 12152 by a diff of collected ids against `d0c28cc` (+19 −0).
- **Mutations:** 5/5 red (`385_mutate.out`): the entry removed; widened to `WHOLE_TABLE` (the added-row control red); widened to `platform` (the rebind control red); moved to the other table (the other-table control red); the pin without the entry.
- **The record.** F212 closed; F210's "What the list still cannot cover"; K39's cell in `docs/decisions.md`; the deploy skill's `SKILL.md` and `CHANGELOG.md`.
- **`wholetree.sh --full`** on `4753b2d`: 4986 passed, 36 skipped, exit 0.
- **The regression of record**, as `regression.sh` printed it (the skip lines are in the phase log):

Regression of record: 12047 passed, 0 failed, 105 skipped, 0 errors at `4753b2d` (34 min 21 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)

  Line coverage of record: 87.71% at `4753b2d` (the pin is 87.50%).
- **Live.** Nothing applied. The live proof of record (K60) is the operator's step in the handoff, from the Mac after the merge: `verify-live 348` must exit 0, with the phone's registration among its "set aside" lines; `verify-live 384` is printed for the record only.

## Version history

| version | date | what |
|---|---|---|
| 1.0 | 2026-10-30 | `7a29f36`, approved by the Executive Officer on issue #41; the fork decided (A) by the operator as K60 (`d0c28cc`) |
| 1.1 | 2026-10-31 | built and closed: Deviations and Results |
