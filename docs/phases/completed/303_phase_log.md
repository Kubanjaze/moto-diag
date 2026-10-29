# Phase 303 — phase log: multi-user auth with roles

**Status:** Complete
**Branch:** `phase-303-multi-user-auth-with-roles`
**Prompt:** `docs/prompts/303_multi_user_auth_with_roles.txt`

## 2026-10-28: The operator's answers to the Chief Engineer's stop

> My answers to the Chief Engineer's stop: go with your picks, plus K56. (a) Sessions live in the API-key table, mds_ for sessions and mdk_ for keys, no migration. (b) Gate only the new login path; existing commands behave as today. (c) A logged-in staff member uses their own subscription, else the highest active subscription of an owner-role active member of a shop they are an active member of. (d) A session lives 30 days; a password is at least 8 characters.

## 2026-10-28: The Chief Engineer's build session reads the answers

The heading above is on the branch, so this session does not stop again (Logic item 1) and builds from item 2, applying the operator's words literally:

- **(a)** Sessions are rows of `api_keys`: `mds_` for a session, `mdk_` for a key. No migration, so no dry run, live apply or deploy order.
- **(b)** The only new gate is `manage_users` on the owner's password reset. Every existing command and route behaves as it does today.
- **(c)** A session caller's tier is their own active subscription, else the highest active subscription of an owner-role active member of any shop where the caller is an active member. A key caller is resolved as today.
- **(d)** `session_lifetime_days = 30`; `MIN_PASSWORD_LENGTH = 8`.
- **K56** governs where it differs from the plan text: the reset refuses an owner at any shop and a member of any other shop where the caller lacks `manage_users`; `authenticate` runs the check against a fixed dummy hash on both failing paths; the socket takes a session only through the bearer subprotocol, and serve installs a redaction filter on uvicorn's two loggers; expiry is compared as UTC times.

Baseline: 11738 collected ids on `5313a5e`, kept at `/fleet/run/ids_before.txt` for the floor diff.

**Decision (Logic item 2): passwords use `hashlib.scrypt` from the standard library.** n 2**14, r 8, p 1, 32-byte key, 16-byte salt from `secrets`, stored as `scrypt$<n>$<r>$<p>$<salt>$<hash>` and compared with `hmac.compare_digest`. Why: the desktop's service installs nothing new, and the stored string carries its parameters, so a later change still verifies old hashes.

## 2026-10-28: Items 2 to 10 built, with their tests

- `auth/passwords.py`, `auth/sessions_repo.py`, `ApiKey.kind`; `auth/deps.py` (`resolve_credential`, `resolve_tier`, `Caller`, `AuthedUser.credential_kind`); `api/routes/live.py` (one credential function and one tier function, `_resolve_tier` removed, a session in the query string refused 4401); `api/middleware.py`; `api/routes/auth.py`, mounted in `app.py`, with `openapi.py` and `errors.py`; `shop/rbac.list_member_permissions`; `cli/user.py` and the two `apikey` filters; `core/config.session_lifetime_days`; the uvicorn redaction filter in `cli/serve.py`.
- `tests/test_phase176_auth_billing.py`, `tests/test_phase180_shop_api.py`, `tests/test_phase181_live_ws.py` and `tests/test_phase183_openapi.py` pass with no edit: 147 passed.
- **Decision: the reset's K56 checks read memberships active or not.** "Owner at any shop" and "belongs to any other shop" count a deactivated membership too, so a former owner, or a member set aside at another shop who could be brought back, is still refused. That refuses more than the operator's words require, never less; the control (a plain tech of the caller's shop, no other membership) is still reset. Tested by `test_a_member_set_aside_at_another_shop_is_still_refused`.
- **Decision: `authenticate` treats a hash not of the module's form as no password** and checks against the dummy hash, so a foreign-shaped hash does not return early either.
- **Decision: `request.state.caller` is set in `get_api_key` as well as `get_current_user`,** so a route that needs only a key (the eight kb routes) leaves the caller too, which is what the Goal's sentence for Phase 348 asks.
- **Decision: two exceptions beyond the plan's two,** `LoginFailedError` (401 `login-failed`, every login failure and a wrong current password) and `LoginSessionNotFoundError` (404 `login-session-not-found`; `session-not-found` is a diagnostic session's). Deviations in v1.1.
- **Allowlists the wiring moved:** `motodiag user` now calls `create_user`, `deactivate_user` and `list_users`, so their entries left `tests/support/integration_gaps_allowlist.py`; `ORPHAN_COUNT` 118 → 115 (`tests/support/integration_gaps_counts.py`); 244X's pin of its own entries 50 → 47, and its known-callerless control drops `create_user`. Found by `wholetree.sh` (3 failed), grepped for every pin before the change.
- `tests/test_phase303_wiring.py` first read raw source; 244G's meta-guard refused it, and it now reads `code_of`. My own new test before any commit, so not a bug fix.
- Floor: +141 −7 by a diff of collected ids, 11738 → 11872.
- `wholetree.sh` passed, exit 0 (2336 passed, 10 skipped).

## 2026-10-28: Mutations, the guides, the findings

- `303_mutate.py`, 24 mutations after 392's harness: **24/24 red** (`303_mutate.out`). Afterwards `git status` showed `src/` and `tests/` exactly as committed. The edit guard did not block the script: it writes `src/` from a script file, not from a shell redirect.
- **Decision: the mutations reach past the plan's ten.** The plan's ten guards are P1, P2, S1–S3, S4 (the one-reason login), S5, D1, D2 (the tier rule, which breaks one function) and R1. The four K56 requirements are K1–K4 (K4 compares the date text, as K56 asks) and L1–L3. Ten more cover the other promises (S6, D3, D4, R2–R4, C1, and L1–L3's filter and socket).
- `docs/guide/api.md`: "A staff login" and "An API key" under Authentication; the 401 text, the 401 table row and the tier sentence follow the code. The opening count is corrected to 88 routes over 111 operations (a deviation).
- `docs/guide/shop-workflow.md` section 0 gains `motodiag user create` before `shop member add`, as run against a fresh database. Without a terminal, getpass printed "Can not control echo" warnings; the guide shows the prompts as a terminal prints them. Everything else is the output verbatim. `tests/test_phase208_docs.py`: 20 passed.
- **Findings F229 and F230** filed with the `finding` skill (`next_f_number.sh`: F228 here, F181 in the mobile repo, next F229) before any document cited them. `finding_check.py` exit 0. (Renumbered F231 and F232 on 2026-10-28 after master took F229 and F230; see the last entry.)

## 2026-10-28: Stopped before the regression of record: a test this session cannot make green

`wholetree.sh --full` on `0b61578`, a clean tree: **4 failed, 4777 passed, 36 skipped** (997 s wall), exit 1. Fast mode had passed; these files are only in the full set.

- All four are one cause. `tests/test_phase205_gate11.py`'s two contract-snapshot tests, `test_every_live_path_is_in_the_committed_snapshot` and `test_every_live_schema_is_in_the_committed_snapshot`, fail, and Gates 12, 13 and 14 each re-run Gate 11 (`test_phase240_gate12.py`, `test_phase250_gate13.py` twice, `test_phase258_gate14.py`).
- The gate reads the mobile repository's committed snapshot, `../moto-diag-mobile/api-schema/openapi.json`. That snapshot lacks this phase's seven `/v1/auth/*` operations and three request schemas (`LoginRequest`, `PasswordChangeRequest`, `PasswordResetRequest`). The remedy the test prints is a mobile-repository commit, `npm run refresh-api-schema` (with a backend running) and then `npm run generate-api-types`. That is how 281 (`e536e60`), 361 (`cd359e0`) and 360 (`57c9e45`) met it.
- This session cannot do that: the mobile checkout is read-only in the fence ("Read-only file system", measured), there is no network for npm, and phases 185–204 are the mobile repository's. Loosening the gate (a list of paths the backend may add ahead of the app) would change a check's rule, a rule-1 stop of its own, and is not done.
- So this is rule 1's "a test it cannot make green". No regression of record was run, and nothing was closed out. The build, the guides, the findings and the mutations (24/24 red) are committed at `0b61578` and before. The handoff's draft, which waits on the regression line, is kept at `/fleet/run/handoff_draft.md`, outside the repository.

## 2026-10-28: The operator's answers to the Chief Engineer's stop (second stop, test-cannot-be-green)

Copied verbatim from the comment by Kubanjaze on issue #31:

> My answer to the second stop (a test that cannot be green): option 1, and do not change the standing test. I pushed your three commits through 7cd219c to the branch. I refreshed the phone app's API snapshot (api-schema/openapi.json) from this branch: moto-diag-mobile commit 7489fd5, committed on the PC and not pushed; its generated types are regenerated on the Mac when it is pushed. Put in the handoff's after-the-merge step: push that app commit, then regenerate and push src/api-types.ts, only after 303 merges, because master's server does not serve the login addresses until then. Before the final run: master took F229 and F230 (c608169), so merge master into the branch and renumber your two findings to the next free numbers with the finding skill (the next two free numbers after F230), everywhere they are cited. Then run the final full check and close out.

## 2026-10-28: Master merged; the two findings renumbered F231 and F232

- `git merge origin/master` (`c608169`): one conflict, in `docs/FOLLOWUPS.md`, where master's F229 (reserved, closed) and F230 met this branch's two entries. Master's two are kept as they are.
- With the `finding` skill's rule (both repositories' files, master's copy for this repository): highest F230 here, F181 in the mobile repository, next free F231. This branch's "no way back from an Engineer's rule-1 stop" is now **F231** and "a migration has no path through the fleet" **F232**; the header reads F232.
- Cited elsewhere only in `303_implementation.md` (item 11's "Built:" line and the Results' Findings bullet), now F231 and F232. The operator's words above, which name master's F229 and F230, are kept verbatim, as is the earlier entry with a note.

## 2026-10-28: The regression of record

`wholetree.sh --full` on `d0f31ca`, a clean tree, exit 0: 4781 passed, 36 skipped (1026.5 s wall). The mobile snapshot the operator refreshed (moto-diag-mobile `7489fd5`) carries this phase's operations, so Gate 11 and the three gates that re-run it pass with no change to any test (`tests/test_phase205_gate11.py` alone first: 21 passed).

Then `regression.sh` on the same clean tree, as printed:

Regression of record: 11767 passed, 0 failed, 105 skipped, 0 errors at `d0f31ca` (34 min 32 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)
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
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
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

No bug fixes in this phase.

## Refuter pass

The fleet's Red Team, three rounds on PR #34 (K9): round 1 at 08:37 on
2026-10-29, reading `1428785`; round 2 at 09:46, reading `ea04f16`;
round 3 at 10:58, reading `f5d54ff`. Each page is the line number in the
commit that round read. Every finding was paperwork in the documents; none
was in the code.
- **Round 1:** six findings, five factual and one wording. All six were
  corrected in `ea04f16`: the handoff's operator blocks are four, not one;
  the filtered commands are `apikey list` and `apikey show`; "No other stop
  was met" deleted; Step 2's one variable recorded as a deviation; v1.0's
  five commits named in the v1.1 header; the mutation breakdown no longer
  counts L1 to L3 twice.
- **Round 2:** one citation finding and one wording finding, both handled
  in `f5d54ff`. The renumbering entry's pointer was corrected, and the
  "my own tests" sentence was deleted.
- **Round 3:** one factual finding and two wording findings. The two
  wording findings went to F233 (`5995cd4`). The factual one was the
  handoff's unrecorded fence-run sentence. Under K9 the operator decided
  it (K57), and the sentence was deleted (`441ef96`).

Rows refuted in more than one round carry the last round. The claims that
cite K55 cite 303's own requirements, K56 since the merge (`c079c24`).

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| The handoff's one operator block has no gh call | killed | "### Step 4: regenerate the phone app's types" | docs/handoffs/2026-10-28_303_closed.md p. 163 | 1 · factual · fixed |
| Handoff: apikey list and apikey revoke leave sessions alone | killed | "changed = revoke_api_key(key_id)" | src/motodiag/cli/apikey.py p. 122 | 1 · factual · fixed |
| No other stop was met | killed | "Stopped before the regression of record: a test this session cannot make green" | docs/phases/completed/303_phase_log.md p. 46 | 1 · factual · deleted |
| The first user is created under MOTODIAG_DB_PATH and MOTODIAG_DATA_DIR as the service sets them | killed | "export MOTODIAG_DB_PATH=~/motodiag/live/motodiag.db" | docs/handoffs/2026-10-28_303_closed.md p. 112 | 1 · factual · fixed |
| Built as planned against v1.0 0e5f614; Deviations lists what the plan did not say | killed | "(v1.0 `0e5f614`, 2026-10-27)" | docs/phases/completed/303_implementation.md p. 3 | 1 · factual · fixed |
| Mutations: the plan's ten, the four K55 requirements, and ten more | killed | "the four K55 requirements, and ten more" | docs/phases/completed/303_implementation.md p. 141 | 1 · wording · fixed |
| The F-numbers were cited only in "Results of item 10" | killed | "Cited elsewhere only in `303_implementation.md` (Results of item 10), now F231 and F232." | docs/phases/completed/303_phase_log.md p. 65 | 2 · citation · fixed |
| "Two of my own tests were corrected" (the 244G guard; the allowlists) | killed | "Two of my own tests were corrected before their first commit (the 244G raw-source guard; the allowlists), as logged." | docs/phases/completed/303_implementation.md p. 201 | 2 · wording · deleted |
| Steps 1 and 2's blocks were run in the fence, with a wrong login answering 401 | killed | "The blocks in steps 1 and 2 were run against a scratch database and a server on loopback in the fence" | docs/handoffs/2026-10-28_303_closed.md p. 45 | 3 · factual · deleted |
| The handoff lists what the user command shipped | killed | "`motodiag user create / list / set-password /" | docs/handoffs/2026-10-28_303_closed.md p. 14 | 3 · wording · open F233 |
| The first stop was the fork at Step 0 | killed | "The fork at Step 0" | docs/phases/completed/303_implementation.md p. 208 | 3 · wording · open F233 |
| 141 tests in nine files (v1.1 Tests, Results) | kept | "+141 -7. Added: test_phase303_auth_api.py (44)," | tests/test_phase255B_collected_test_floor.py p. 417 | 3 · none · kept |
| The floor rose 11738 → 11872 | kept | "COLLECTED_TEST_FLOOR = 11872" | tests/test_phase255B_collected_test_floor.py p. 428 | 3 · none · kept |
| Regression of record 11767 passed, 105 skipped at d0f31ca (11767 + 105 = 11872, the floor) | kept | "Regression of record: 11767 passed, 0 failed, 105 skipped, 0 errors at `d0f31ca`" | docs/phases/completed/303_phase_log.md p. 73 | 3 · none · kept |
| wholetree.sh --full 4781 passed before the regression | kept | "`wholetree.sh --full` on `d0f31ca`, a clean tree, exit 0: 4781 passed, 36 skipped" | docs/phases/completed/303_phase_log.md p. 69 | 3 · none · kept |
| Mutations 24/24 red; the plan's ten + K1–K4 + ten more = 24 | kept | "24/24 red" | docs/phases/completed/303_mutate.out p. 25 | 3 · none · kept |
| F231 is the rule-1 stop with no way back into the fleet | kept | "A rule-1 stop raised by the Chief Engineer has no way back into the fleet" | docs/FOLLOWUPS.md p. 4460 | 3 · none · kept |
| F232 is a migration with no path through the fleet | kept | "A phase with a migration has no path through the fleet" | docs/FOLLOWUPS.md p. 4481 | 3 · none · kept |
| The FOLLOWUPS header reads F232 after the renumbering | kept | "At the time of writing the highest assigned is **F232**" | docs/FOLLOWUPS.md p. 22 | 3 · none · kept |
| ORPHAN_COUNT 118 → 115 | kept | "ORPHAN_COUNT = 115" | tests/support/integration_gaps_counts.py p. 66 | 3 · none · kept |
| 244X's own pin 50 → 47 | kept | "→ 47 (Phase 303 wired create_user, deactivate_user, list_users)" | tests/test_phase244X_multiline_reexports.py p. 138 | 3 · none · kept |
| docs/guide/api.md's count is now 88 routes over 111 operations | kept | "88 routes over 111 operations." | docs/guide/api.md p. 3 | 3 · none · kept |
| uvicorn 0.49 writes a WebSocket handshake's path with its query string on its error logger | kept | "'%s - \"WebSocket %s\" [accepted]'," | .venv/lib/python3.14/site-packages/uvicorn/protocols/websockets/websockets_impl.py p. 263 | 3 · none · kept |
| The redaction filter is attached to uvicorn.access and uvicorn.error through log_config | kept | "for name in (\"uvicorn.access\", \"uvicorn.error\"):" | src/motodiag/cli/serve.py p. 72 | 3 · none · kept |
| "Confined to mds_" is substr, because _ is a LIKE wildcard | kept | "# SQL for \"this row is a session\". Not LIKE 'mds_%': '_' is a LIKE wildcard." | src/motodiag/auth/sessions_repo.py p. 67 | 3 · none · kept |
| authenticate runs the check against the dummy hash on an unknown or passwordless name (K55 req. 2) | kept | "matched = verify_password(password, stored if has_password else DUMMY_HASH)" | src/motodiag/auth/sessions_repo.py p. 226 | 3 · none · kept |
| scrypt n 2**14, r 8, p 1, 32-byte key; maxmem 64 MiB | kept | "MAX_MEMORY = 64 * 1024 * 1024" | src/motodiag/auth/passwords.py p. 30 | 3 · none · kept |
| A query-string session is refused 4401 with today's "missing API key" reason, even beside a good subprotocol | kept | "if not plaintext or _session_in_query(websocket):" | src/motodiag/api/routes/live.py p. 321 | 3 · none · kept |
| The live socket's tier comes from resolve_tier; _resolve_tier removed | kept | "sub_tier = resolve_tier(api_key, db_path=db_path)" | src/motodiag/api/routes/live.py p. 334 | 3 · none · kept |
| request.state.caller is set in get_api_key as well (Deviations) | kept | "request.state.caller = Caller(key.user_id, key.kind, key.id)" | src/motodiag/auth/deps.py p. 212 | 3 · none · kept |
| The limiter key stays key:<id>; a credentialed caller with no tier stays 'individual' | kept | "return f\"key:{key.id}\", tier or \"individual\"" | src/motodiag/api/middleware.py p. 159 | 3 · none · kept |
| The reset's K55 checks read memberships active or not (Deviations) | kept | "others = list_shops_for_user(user_id, active_only=False, db_path=db_path)" | src/motodiag/api/routes/auth.py p. 247 | 3 · none · kept |
| LoginFailedError 401 login-failed and LoginSessionNotFoundError 404 login-session-not-found are mapped | kept | "(LoginFailedError, 401, \"login-failed\", \"Login failed\")," | src/motodiag/api/errors.py p. 226 | 3 · none · kept |
| apikey list and apikey show skip session rows | kept | "if k.kind == \"api_key\"]" | src/motodiag/cli/apikey.py p. 85 | 3 · none · kept |
| The operator's four requirements are recorded in docs/decisions.md (K55 then, K56 now) | kept | "1. The owner's password reset must refuse when the person being reset is an owner at any shop" | docs/decisions.md p. 54 | 3 · none · kept |
| The plan of record's "Next, in order" row 2 puts 303 in order | kept | "2026-10-26 · K43" | docs/reports/2026-10-12_plan_of_record.md p. 14 | 3 · none · kept |
| 303 and 348 are two missions, 303 first (K48) | kept | "**303 and 348 are two missions, 303 first.**" | docs/reports/2026-10-12_plan_of_record.md p. 82 | 3 · none · kept |
| The ROADMAP row is closed with its date and regression line | kept | "**CLOSED 2026-10-28.**" | docs/ROADMAP.md p. 559 | 3 · none · kept |
| The handoff's operator blocks carry no gh call (R8) | kept | "could not push the app" | docs/handoffs/2026-10-28_303_closed.md p. 158 | 3 · none · kept |

## 2026-10-28: Close-out

v1.1 (Results added), this log Complete, the files moved to `docs/phases/completed/`, the ROADMAP row ✅, `implementation.md`'s version and history row, the root `phase_log.md`'s pointer, and the handoff `docs/handoffs/2026-10-28_303_closed.md` with the operator's four steps after the merge (the server, the first login, the app commit pushed from the desktop, the app's types regenerated on the Mac). No migration, so no live outcome; the merge is the operator's.

## 2026-10-29: The Red Team's round 1, six document corrections

No code changed, so no bug fix and no new regression of record; the line above stands.

- **The handoff's operator blocks are four, not one.** `303_implementation.md` item 11's "Built:" line and the change-log section now say four, each with no `gh` call and each ending in ALL GOOD or SOMETHING IS OFF.
- **`apikey revoke` was not changed.** The handoff now names the two filtered commands, `apikey list` and `apikey show`.
- **The stops were two.** The Rule-1 section's "No other stop was met" is deleted and points to Results, which names the second (Gate 11's mobile snapshot).
- **Step 2's block sets only `MOTODIAG_DB_PATH`**, where item 11 also named `MOTODIAG_DATA_DIR`. Its four commands read the database path, not the data directory (`grep` of `cli/user.py`, `cli/shop.py`, `auth/` and `shop/rbac.py` finds no `data_dir`). Recorded as a deviation; the block, run as written in the fence, is unchanged.
- **The plan the build is measured against is named.** v1.0 was committed five times without a version bump: `f3f7859`, `b4abb65`, `461b381`, `a0688a8`, `0e5f614`. The first planned migration 088 with a `user_sessions` table; the Executive Officer's round-1 revision, `b4abb65`, moved sessions into `api_keys` and left the table as part (a)'s alternative; `0e5f614` is the text approved on issue #31. The v1.1 header now says so.
- **The mutation count no longer labels L1 to L3 twice.** The 2026-10-28 entry above called K1–K4 and L1–L3 "the four K56 requirements" and counted L1–L3 in the ten more as well. Correctly: the plan's ten; K1 and K2 (requirement 1), K3 (2) and K4 (4); and ten more, L1–L3 (requirement 3) among them. 10 + 4 + 10 = 24, as `303_mutate.out` lists. v1.1's Tests line says so.

## 2026-10-29: The Red Team's round 2, two document corrections

No code changed, so no bug fix and no new regression of record; the line above stands.

- **The renumbering entry pointed at the wrong section.** It said the findings are cited in "Results of item 10"; item 10 is `core/config.py`, and the citations are in item 11's "Built:" line and the Results' Findings bullet. The pointer now names those two.
- **v1.1's "No bug fixes" bullet called the allowlists "my own tests".** Only the wiring test was this phase's own; the allowlist and count pins were existing tests moved by the wiring, as the 2026-10-28 entry says. The sentence is deleted (K9); "nothing committed was found wrong" stands.

## 2026-10-29: The operator decides (K57): the sentence deleted, master merged, K55 renumbered K56

The Red Team's round 3 of 3 left #31 on needs-admiral (K9). The operator,
recorded as K57 with `yeoman.py decide` (covers: no stop): "303: delete the
unrecorded fence-run sentence, merge master, renumber 303's K55 to K56, and
send it to the Captain; the Red Team's rounds are spent." Done in the
planter's session, under the operator's login:

- **The handoff's unrecorded claim deleted** (`441ef96`): the Regression
  section's sentence beginning "The blocks in steps 1 and 2 were run against
  a scratch database". Nothing else the Red Team did not name was changed;
  its wording findings stay filed as F233.
- **Master merged** (`c079c24`, master at `f856439`, Phase 394). Master's
  K55 (394, the brief on stdin) stays K55; this phase's K55 (the operator's
  four security requirements) is K56: its decisions row, this log,
  `303_implementation.md`, `303_mutate.py`, the handoff, ROADMAP row 303,
  implementation.md's 303 row, and the comments and three test class names
  in `src/` and `tests/` that cite it. The operator's words quoted here as
  "plus K55" now read "plus K56", as the operator asked for every 303
  citation. Master's K55 citations are untouched.
- **The floor** 11756 → 11890: master's 11756 plus this phase's +141 −7,
  by a diff of collected ids against master at `f856439`.
- **K57** recorded (`42f8651`).

`pgrep -x bwrap` before each run: exit 1; `dispatcher.log`'s last line was
10:58's "issue 31: back, rounds exhausted", no stage running (F220).
`wholetree.sh` (fast) before each commit, exit 0; `wholetree.sh --full` on
`42f8651`, exit 0: 4820 passed, 15 skipped (437.5 s wall).

`regression.sh` on `42f8651` in this checkout, outside the fence: not of
record, 11853 passed, 4 failed, 33 skipped, 0 errors (10 min 55 s wall,
exit 1). The four are the desktop's four the fleet skill names, none in
this phase's code: `test_phase257_orchestrator_guards.py`'s two
`osacompile` checks (macOS only), its `subc` profile control (no
`subc login` on this machine), and `test_phase204_gate10.py`'s installed
ffmpeg (none on the home desktop).

So the regression of record ran as this phase's earlier one and 394's did:
the fleet's `Fleet.check_run` on `42f8651`, a fresh clone in the fence, no
model, no token, with the fleet's virtualenv, in its own state folder
(`~/motodiag/p303/state/runs/20261029_124944_check`), with the mobile
repository beside it at `7489fd5` (the snapshot that carries this phase's
operations). The skips are the same 81 lines as `d0f31ca`'s, in another order.

    wholetree full: PASSED — 4799 passed, 36 skipped, 32 warnings in 1028.61s (0:17:08) (1031.6 s wall)

Regression of record: 11785 passed, 0 failed, 105 skipped, 0 errors at `42f8651` (35 min 1 s wall, `python -m pytest -n auto --dist load`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
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
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
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
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
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
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
