
## 2026-10-28: The operator's answers to the Chief Engineer's stop

> My answers to the Chief Engineer's stop: go with your picks, plus K55. (a) Sessions live in the API-key table, mds_ for sessions and mdk_ for keys, no migration. (b) Gate only the new login path; existing commands behave as today. (c) A logged-in staff member uses their own subscription, else the highest active subscription of an owner-role active member of a shop they are an active member of. (d) A session lives 30 days; a password is at least 8 characters.

## 2026-10-28: The Chief Engineer's build session reads the answers

The heading above is on the branch, so this session does not stop again (Logic item 1) and builds from item 2, applying the operator's words literally:

- **(a)** Sessions are rows of `api_keys`: `mds_` for a session, `mdk_` for a key. No migration, so no dry run, live apply or deploy order.
- **(b)** The only new gate is `manage_users` on the owner's password reset. Every existing command and route behaves as it does today.
- **(c)** A session caller's tier is their own active subscription, else the highest active subscription of an owner-role active member of any shop where the caller is an active member. A key caller is resolved as today.
- **(d)** `session_lifetime_days = 30`; `MIN_PASSWORD_LENGTH = 8`.
- **K55** governs where it differs from the plan text: the reset refuses an owner at any shop and a member of any other shop where the caller lacks `manage_users`; `authenticate` runs the check against a fixed dummy hash on both failing paths; the socket takes a session only through the bearer subprotocol, and serve installs a redaction filter on uvicorn's two loggers; expiry is compared as UTC times.

Baseline: 11738 collected ids on `5313a5e`, kept at `/fleet/run/ids_before.txt` for the floor diff.

**Decision (Logic item 2): passwords use `hashlib.scrypt` from the standard library.** n 2**14, r 8, p 1, 32-byte key, 16-byte salt from `secrets`, stored as `scrypt$<n>$<r>$<p>$<salt>$<hash>` and compared with `hmac.compare_digest`. Why: the desktop's service installs nothing new, and the stored string carries its parameters, so a later change still verifies old hashes.

## 2026-10-28: Items 2 to 10 built, with their tests

- `auth/passwords.py`, `auth/sessions_repo.py`, `ApiKey.kind`; `auth/deps.py` (`resolve_credential`, `resolve_tier`, `Caller`, `AuthedUser.credential_kind`); `api/routes/live.py` (one credential function and one tier function, `_resolve_tier` removed, a session in the query string refused 4401); `api/middleware.py`; `api/routes/auth.py`, mounted in `app.py`, with `openapi.py` and `errors.py`; `shop/rbac.list_member_permissions`; `cli/user.py` and the two `apikey` filters; `core/config.session_lifetime_days`; the uvicorn redaction filter in `cli/serve.py`.
- `tests/test_phase176_auth_billing.py`, `tests/test_phase180_shop_api.py`, `tests/test_phase181_live_ws.py` and `tests/test_phase183_openapi.py` pass with no edit: 147 passed.
- **Decision: the reset's K55 checks read memberships active or not.** "Owner at any shop" and "belongs to any other shop" count a deactivated membership too, so a former owner, or a member set aside at another shop who could be brought back, is still refused. That refuses more than the operator's words require, never less; the control (a plain tech of the caller's shop, no other membership) is still reset. Tested by `test_a_member_set_aside_at_another_shop_is_still_refused`.
- **Decision: `authenticate` treats a hash not of the module's form as no password** and checks against the dummy hash, so a foreign-shaped hash does not return early either.
- **Decision: `request.state.caller` is set in `get_api_key` as well as `get_current_user`,** so a route that needs only a key (the eight kb routes) leaves the caller too, which is what the Goal's sentence for Phase 348 asks.
- **Decision: two exceptions beyond the plan's two,** `LoginFailedError` (401 `login-failed`, every login failure and a wrong current password) and `LoginSessionNotFoundError` (404 `login-session-not-found`; `session-not-found` is a diagnostic session's). Deviations in v1.1.
- **Allowlists the wiring moved:** `motodiag user` now calls `create_user`, `deactivate_user` and `list_users`, so their entries left `tests/support/integration_gaps_allowlist.py`; `ORPHAN_COUNT` 118 → 115 (`tests/support/integration_gaps_counts.py`); 244X's pin of its own entries 50 → 47, and its known-callerless control drops `create_user`. Found by `wholetree.sh` (3 failed), grepped for every pin before the change.
- `tests/test_phase303_wiring.py` first read raw source; 244G's meta-guard refused it, and it now reads `code_of`. My own new test before any commit, so not a bug fix.
- Floor: +141 −7 by a diff of collected ids, 11738 → 11872.
- `wholetree.sh` passed, exit 0 (2336 passed, 10 skipped).

## 2026-10-28: Mutations, the guides, the findings

- `303_mutate.py`, 24 mutations after 392's harness: **24/24 red** (`303_mutate.out`). Afterwards `git status` showed `src/` and `tests/` exactly as committed. The edit guard did not block the script: it writes `src/` from a script file, not from a shell redirect.
- **Decision: the mutations reach past the plan's ten.** The plan's ten guards are P1, P2, S1–S3, S4 (the one-reason login), S5, D1, D2 (the tier rule, which breaks one function) and R1. The four K55 requirements are K1–K4 (K4 compares the date text, as K55 asks) and L1–L3. Ten more cover the other promises (S6, D3, D4, R2–R4, C1, and L1–L3's filter and socket).
- `docs/guide/api.md`: "A staff login" and "An API key" under Authentication; the 401 text, the 401 table row and the tier sentence follow the code. The opening count is corrected to 88 routes over 111 operations (a deviation).
- `docs/guide/shop-workflow.md` section 0 gains `motodiag user create` before `shop member add`, as run against a fresh database. Without a terminal, getpass printed "Can not control echo" warnings; the guide shows the prompts as a terminal prints them. Everything else is the output verbatim. `tests/test_phase208_docs.py`: 20 passed.
- **Findings F229 and F230** filed with the `finding` skill (`next_f_number.sh`: F228 here, F181 in the mobile repo, next F229) before any document cited them. `finding_check.py` exit 0.

## 2026-10-28: Stopped before the regression of record: a test this session cannot make green

`wholetree.sh --full` on `0b61578`, a clean tree: **4 failed, 4777 passed, 36 skipped** (997 s wall), exit 1. Fast mode had passed; these files are only in the full set.

- All four are one cause. `tests/test_phase205_gate11.py`'s two contract-snapshot tests, `test_every_live_path_is_in_the_committed_snapshot` and `test_every_live_schema_is_in_the_committed_snapshot`, fail, and Gates 12, 13 and 14 each re-run Gate 11 (`test_phase240_gate12.py`, `test_phase250_gate13.py` twice, `test_phase258_gate14.py`).
- The gate reads the mobile repository's committed snapshot, `../moto-diag-mobile/api-schema/openapi.json`. That snapshot lacks this phase's seven `/v1/auth/*` operations and three request schemas (`LoginRequest`, `PasswordChangeRequest`, `PasswordResetRequest`). The remedy the test prints is a mobile-repository commit, `npm run refresh-api-schema` (with a backend running) and then `npm run generate-api-types`. That is how 281 (`e536e60`), 361 (`cd359e0`) and 360 (`57c9e45`) met it.
- This session cannot do that: the mobile checkout is read-only in the fence ("Read-only file system", measured), there is no network for npm, and phases 185–204 are the mobile repository's. Loosening the gate (a list of paths the backend may add ahead of the app) would change a check's rule, a rule-1 stop of its own, and is not done.
- So this is rule 1's "a test it cannot make green". No regression of record was run, and nothing was closed out. The build, the guides, the findings and the mutations (24/24 red) are committed at `0b61578` and before. The handoff's draft, which waits on the regression line, is kept at `/fleet/run/handoff_draft.md`, outside the repository.

## 2026-10-28: The operator's answers to the Chief Engineer's stop (second stop, test-cannot-be-green)

Copied verbatim from the comment by Kubanjaze on issue #31:

> My answer to the second stop (a test that cannot be green): option 1, and do not change the standing test. I pushed your three commits through 7cd219c to the branch. I refreshed the phone app's API snapshot (api-schema/openapi.json) from this branch: moto-diag-mobile commit 7489fd5, committed on the PC and not pushed; its generated types are regenerated on the Mac when it is pushed. Put in the handoff's after-the-merge step: push that app commit, then regenerate and push src/api-types.ts, only after 303 merges, because master's server does not serve the login addresses until then. Before the final run: master took F229 and F230 (c608169), so merge master into the branch and renumber your two findings to the next free numbers with the finding skill (the next two free numbers after F230), everywhere they are cited. Then run the final full check and close out.
