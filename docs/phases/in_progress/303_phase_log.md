
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
