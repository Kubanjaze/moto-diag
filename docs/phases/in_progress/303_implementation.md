# Phase 303 — Multi-user auth with roles

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-10-27

---

## Goal

A shop's staff get their own logins. Today a person reaches the API only by pasting an API key that the operator mints by hand on the server (`motodiag apikey create --user N`, Phase 176), and the CLI has no command that creates a staff user at all. The roles the row names already exist: Phase 112 seeded owner, tech, service_writer and apprentice with their permissions, and Phase 172 gave each shop member a role that `has_shop_permission` in `src/motodiag/shop/rbac.py` walks. Phase 180's shop routes already refuse a non-member and check the member's permission on every write. What does not exist is the front door: no password is ever set or checked, no session token is issued, nothing logs out.

This phase ships that front door and nothing behind it:

- **Owner, tech, service writer and apprentice:** a user is created with a password from the CLI, then given a role at a shop with the existing `shop member add`. Login returns the user's memberships and roles, so a client knows what the person may do.
- **Permission gating** on the new path, with the existing tables: the owner's password reset for a member needs `manage_users` at that shop, through `require_shop_permission`. No existing command or route gains a gate it does not have today (Step 0's classification, extension, holds only on that).
- **Session management:** a login makes a session token, shown once and stored hashed like an API key; a session expires, is revoked by logout, by a password change, by the owner's reset, by the CLI, or when the user is deactivated. Every route that takes an API key today also takes a session token, so a logged-in tech reaches the shop console, the knowledge base and the live socket the same way a key does.

The Science Officer asked for the `authenticate` and `password` hits in src to be read before the build. Read for this plan: they are the users table's nullable `password_hash` column and its model and repository field (Phase 112, `src/motodiag/auth/models.py`, `src/motodiag/auth/users_repo.py`), the API-key layer (Phase 176, `src/motodiag/auth/deps.py`, `src/motodiag/auth/api_key_repo.py`) and docstrings that say the CLI has no authenticated user (`src/motodiag/shop/attribution.py`, `src/motodiag/cli/diagnose.py`). No password or session code exists. Phase 112's note that real authentication would arrive with Track H is half answered: Track H's Phase 176 shipped API keys and left passwords unwritten. That is a plan note, not a stop, and this phase writes the other half.

What this makes for Phase 348: every request resolved from a session or a key leaves the resolved caller (user id, credential kind, session id) on the request, so 348's log can record which staff login did what (the plan of record, 2026-10-27: "348's log records which staff login did what, which 303 makes").

## Logic

1. **Migration 088, `user_sessions`** (`src/motodiag/core/migrations.py`; `SCHEMA_VERSION` 87 → 88 in `src/motodiag/core/database.py`). One table: `id`, `user_id` (references `users`, on delete cascade), `token_hash` (unique), `token_prefix`, `client` (free text the login sends, or null), `created_at`, `expires_at`, `revoked_at`; one index on `(user_id, revoked_at)`. Timestamps in the stored UTC form (`motodiag.core.timestamps.utc_now`). Rollback drops the index and the table. No column is added to `users`; the existing nullable `password_hash` is used. No existing row of any table is touched.
   Finish line: a fresh database has the table; upgrade then rollback leaves schema 87 with no trace; `deploy.py dryrun 303` against a copy of live reports schema added only, zero rows added, changed or removed, and no scope problem. The scope file `docs/phases/in_progress/303_deploy_scope.json` names the table and the index under `schema.added` and nothing else.

2. **`src/motodiag/auth/passwords.py`** (new): `hash_password(plain) -> str` and `verify_password(plain, stored) -> bool`. The stored form is one string, `scrypt$<n>$<r>$<p>$<salt>$<hash>`, from `hashlib.scrypt` with a fresh 16-byte salt from `secrets`, compared with `hmac.compare_digest`. `MIN_PASSWORD_LENGTH = 8`; shorter raises `PasswordTooShort`. A stored value that is null, empty or not in this form verifies false, so the seeded system user and every pre-existing user can never log in until a password is set.
   Finish line: a password verifies against its own hash; a wrong password, a null hash and a hash of a different shape all fail; two hashes of one password differ; the parameters are constants named in the module and the stored string carries them, so a later change verifies old hashes.
   (The library is the operator's pick at stop 1c below; the module's two functions keep their names whichever is picked.)

3. **`src/motodiag/auth/sessions_repo.py`** (new): `UserSession` (pydantic, never the plaintext), `create_session(user_id, client, lifetime_days, db_path) -> (UserSession, plaintext)`, `verify_session(plaintext, db_path) -> Optional[UserSession]`, `revoke_session(session_id, db_path)`, `revoke_user_sessions(user_id, keep_session_id=None, db_path)`, `list_user_sessions(user_id, include_revoked=False, db_path)`, and `authenticate(username, password, db_path) -> Optional[dict]`. A token is `mds_` and 32 random bytes url-safe from `secrets`, stored as its sha256 with the first 12 characters as the prefix, the same shape as `api_key_repo`. `verify_session` returns a session only when it is unrevoked, unexpired and its user is active, **and it writes nothing**: no last-seen column exists and none is refreshed, because the deploy gates refuse any column the running API writes by itself that `deploy.SERVER_WRITES` does not name (F208, F210, F212), and adding to that list is the operator's call. `authenticate` returns the user row on a match and `None` for an unknown name, a wrong password, a user with no password and an inactive user alike, with one reason string, so the login route cannot tell a caller which it was.
   Finish line: each function's tests; a request authenticated by a session leaves every byte of `user_sessions` as it was (the F210 control); an expired, a revoked and a deactivated user's session each verify to `None`.

4. **`src/motodiag/auth/deps.py`**: a session is a second credential. `get_api_key` resolves a bearer or `X-API-Key` value that starts with `mdk_` through `verify_api_key` as today, and one that starts with `mds_` through `verify_session`; its return is `Optional[Credential]`, where `Credential = Union[ApiKey, UserSession]`, and it stashes the session on `request.state.session` as it stashes a key. `require_api_key` returns a `Credential` and keeps its 401 message, extended to name a session token. `AuthedUser` gains `credential_kind` (`"api_key"` or `"session"`) and `session_id`; `api_key_id` and `api_key_prefix` become optional. `get_current_user` builds the same `AuthedUser` from either, resolves the tier as stop 1b's answer says (the plan's default reading: a session caller's own active subscription, else the highest active subscription of the owners of the shops the caller is an active member of; an API-key caller's tier is resolved exactly as today), and stashes the result on `request.state.caller` for Phase 348. `require_tier` is unchanged. The eight `kb.py` routes and `live.py`, whose dependency is annotated `ApiKey`, change only that annotation to `Credential` (`live.py` reads `.user_id`, which both carry).
   Finish line: `tests/test_phase176_auth_billing.py` and `tests/test_phase180_shop_api.py` pass with no edit; a session token reaches `/v1/shop/profile/list` with the same 401, 402 and 403 semantics a key gets; a revoked or expired session is 401; a tech's session with no subscription of their own reaches a shop route under the default reading and gets 402 under the other; the kb routes answer a session.

5. **`src/motodiag/api/middleware.py`**: `_try_resolve_api_key` resolves an `mds_` token through `verify_session`, keys the limiter `session:<id>` and finds the tier the way item 4 does, so a logged-in caller is limited at their tier and not as an anonymous address. Login itself stays rate-limited as anonymous by the existing settings; nothing is added to `_RATE_LIMIT_EXEMPT_PATHS`.
   Finish line: a session caller's `X-RateLimit-Limit` is their tier's; an unauthenticated login attempt counts against the address's anonymous budget.

6. **`src/motodiag/api/routes/auth.py`** (new), included in `src/motodiag/api/app.py` under `/v1` beside the others; `src/motodiag/api/openapi.py` gains an `auth` tag, `/v1/auth/login` in `PUBLIC_PATH_PREFIXES`, and the `bearerAuth` scheme's text says a session token is accepted too.
   - `POST /v1/auth/login` `{username, password, client?}` → 200 `{token, expires_at, user: {id, username, full_name, email}, memberships: [{shop_id, shop_name, role, permissions}]}`; 401 with one problem type for every failure (no 404 for an unknown name). No key or session needed.
   - `GET /v1/auth/me` → the same user and memberships block plus `credential: {kind, id}` and `tier`; any credential.
   - `POST /v1/auth/logout` → 204, revokes the calling session; a key caller gets 400 (`not-a-session`).
   - `GET /v1/auth/sessions` → the caller's unrevoked sessions (prefix, client, created, expires, which one is current); `DELETE /v1/auth/sessions/{id}` → 204 for one of the caller's own, 404 for anyone else's.
   - `POST /v1/auth/password` `{current_password, new_password}` → 204; wrong current is 401; too short is 422; every other session of the user is revoked, the calling one kept.
   - `POST /v1/auth/shops/{shop_id}/members/{user_id}/password` `{new_password}` → 204; `require_tier("shop")`, then `require_shop_permission(shop_id, caller, "manage_users")`, then the target must be an active member of that shop (404 otherwise); all the target's sessions are revoked. This is the row's permission gate on the new path: an owner may, an apprentice may not, a member of another shop may not.
   Finish line: each status above has a test; a token appears in exactly one response body ever; the problem-detail envelope and request id match the existing routes (`src/motodiag/api/errors.py` maps the new `NotASessionError`).

7. **`src/motodiag/shop/rbac.py`**: one addition, `list_member_permissions(shop_id, user_id, db_path) -> list[str]`, the permission names the member's role grants, by the same join `has_shop_permission` walks. Nothing else in the module changes.
   Finish line: an owner lists all twelve seeded permissions, an apprentice its read-mostly set, a non-member and an inactive member an empty list; `has_shop_permission` agrees with the list for every name.

8. **`src/motodiag/cli/user.py`** (new), registered from `src/motodiag/cli/main.py` as the top-level group `user`, the way `apikey` is (the builder first confirms no command or short alias already takes the name):
   - `user create --username U --full-name N [--email E] [--password-stdin]`: without the flag, prompts twice with hidden input; prints the new id and reminds that a role comes from `shop member add`.
   - `user list [--include-inactive] [--json]`: id, username, full name, active, whether a password is set (never the hash), open sessions.
   - `user set-password USER [--password-stdin]` (USER an id or a username): sets the hash and revokes the user's sessions.
   - `user deactivate USER`: `deactivate_user` (which already refuses the system user) and revokes sessions.
   - `user sessions USER [--json]` and `user logout USER`: list and revoke.
   Finish line: each subcommand round-trips under `CliRunner`; a password never reaches stdout, the log or `--json`; `user create` with a 7-character password exits non-zero naming the minimum; `shop-workflow.md` step 0 shows `user create` before `shop member add`, as run.

9. **`src/motodiag/core/config.py`**: `session_lifetime_days: int = 30`, read by the login route; the number is stop 2's.
   Finish line: a session made under a one-day setting expires after a day; the setting reads from the environment like the rate limits do.

10. **Documents.** `docs/guide/api.md` "Authentication" gains the login and a session example beside the key; `docs/guide/shop-workflow.md` step 0 gains the staff user; the ROADMAP row closes within 120 words; `docs/phases/in_progress/303_deploy_scope.json` and the committed `303_dryrun_diff.md`; the handoff with the operator's steps in plain English (which computer, which window, one paste block ending ALL GOOD or SOMETHING IS OFF): restart the API service on the desktop after the merge, then create their own user and log in once with curl.
    Finish line: `verify_phase.sh` reads right; the handoff's `gh` calls carry `-R Kubanjaze/moto-diag` (R8).

The order of the deploy is rule 4's: the regression of record, `deploy.py apply-live 303` from the branch on the desktop, the close-out commit, the merge. The operator's first password and first login come after the close-out's `verify-live`, because a login writes a session row and a password writes a users row, and verify-live would report them as outside the approved diff (F210's general case, which row 330 settles). The Quartermaster, in shadow, refuses a pull request with a migration as out of scope; that is its rule, not a failure of this phase, and the operator merges by hand (K49).

## The change log's three newest entries

- **2026-10-26, R8: an operator paste block's `gh` names its repository.** The check it became: `.claude/skills/closeout/roadmap_check.py` R8, run by `tests/test_roadmap_continuity.py` and on every push. This phase's handoff blocks carry `-R Kubanjaze/moto-diag`.
- **2026-10-22, `fleet` joins the procedure folders.** The entry says the row is text only and no check reads the table; the folder's own tests hold the folder, `tests/test_phase387_fleet_contract.py`. This phase is the first first-shop phase the fleet runs end to end (K43).
- **2026-10-20, rule 6: plain English to the operator.** No check: the entry says "Text only; no check holds it." The handoff's steps, the stop questions on the mission issue and the row pull request are written to it.

## The plan of record

- **The entry that puts 303 in order:** the plan of record's "Next, in order" row 2, "303 | shop | fleet | nothing | 2026-10-26 · K43", and its dated entry of **2026-10-26**: "shop work comes next, after 391. The operator's decision is K43 in `docs/decisions.md`. Asked "Want me to write that rule into the plan of record, so the fleet and every builder sees it?", they answered "yes write it into the plan"", whose rule 3 reads: "**The next phase is first-shop work, run through the fleet:** staff logins with roles and the activity log (303 and 348). It is also the fleet's end-to-end run, the proposal's step 9, done on real work."
- **K43** (2026-10-26), the operator's words "yes write it into the plan"; the check it became: "No check. docs/reports/2026-10-12_plan_of_record.md, 2026-10-26: 391 is the last fleet-only phase; after it and the trial (389A, issue #14), the next phase is first-shop work through the fleet, 303 and 348, as the fleet's end-to-end run; a later fleet-only phase must name the first-shop phase it unblocks."
- **The order within the pair,** the plan of record, 2026-10-27 (K48): "**303 and 348 are two missions, 303 first.** The ledger has two rows and a mission is one row; 348's log records which staff login did what, which 303 makes (392's Step 0, S0-5)."
- **What opened it:** the plan of record, 2026-10-26, later (K44): "**What it unblocks:** 303 and 348, which its row names (K43)." and "**Its proof:** the fleet starts 303 and 348 from this plan by itself."
- **What the row needs from the operator:** "nothing" (the list). The stops below are rule-1 stops met in the work, not needs the list records.
- This phase's kind is shop, not fleet-only, so it names nothing it unblocks; 348 follows it by the same list.

## Rule-1 stops anticipated

- **A real fork, 1a (Step 0's):** gate only the new login path, or gate the existing CLI and the diagnostic commands too. This plan takes the first: every existing command and route behaves exactly as today for the callers it has today, and the only new gate is `manage_users` on the owner's reset. The second reading changes what current commands do, is a reshape by Step 0's own words, and goes back to Step 0 for the Admiral. The operator confirms the first reading on the mission issue before the build starts.
- **A real fork, 1b (not in Step 0):** how a staff member who logs in meets `require_tier("shop")`, which reads a subscription per user (`get_active_subscription(user_id)`). A tech has no subscription of their own, so without a rule every shop route answers their session 402. Two plans: (i) a session caller's tier is their own subscription, else the owner's of a shop they are an active member of, and an API-key caller is resolved exactly as today; (ii) the tier rule changes for every caller, keys included, which changes today's behaviour and is a reshape. The Captain recommends (i); item 4 is built only after the operator's words.
- **A real fork, 1c (Step 0's second stop, read as what ships):** how passwords are stored and tokens issued. The Captain recommends the standard library: `hashlib.scrypt` for passwords and `secrets` for an opaque session token hashed with sha256, the shape API keys already have; nothing new to install on the desktop's service. The other plan is a new dependency (argon2-cffi or bcrypt), a wheel the desktop installs and the service unit carries. Item 2 is built only after the operator's words. Step 0 called this a credential decision; the operator's answer is recorded either way.
- **A threshold or a rule's definition:** two numbers this phase sets and the operator confirms at the build's start: a session lives 30 days from login (`session_lifetime_days`), and a password is at least 8 characters. No lockout count, no idle timeout and no change to `deploy.SERVER_WRITES` (a gate's definition, F212) are planned; if the Red Team asks for any, it is a stop, not a change the builder makes.
- **A test it cannot make green:** none expected. If `tests/test_phase176_auth_billing.py` or `tests/test_phase180_shop_api.py` go red under item 4, that is the signal item 4 changed today's behaviour, and the builder stops rather than editing them.
- **A login or a credential:** none needed from the operator. `apply-live` runs on the desktop, where live is, under the fleet's own account. The operator's own password is set by the operator's hand after the merge and is never typed into an issue, a log or a paste block.
- **A live-database change:** migration 088 adds a table and an index and alters or deletes no row, so by rule 1's words it is not a stop; the dry-run diff is still committed and shown before the apply, as the deploy skill asks. A backfill of any `users` row, a password for an existing user by the agent, or a column on `users` would be a stop; this plan has none.

## Tests

- `tests/test_phase303_passwords.py`: hash and verify, the salt, the shape, null and foreign hashes fail closed, the minimum length, the system user never verifies.
- `tests/test_phase303_sessions_repo.py`: create, verify, expiry, revoke one, revoke all but one, list, `authenticate`'s one reason for four failures, the F210 control (a verified request changes no byte of `user_sessions`, compared row for row before and after).
- `tests/test_phase303_migration.py`: 088 up, rollback, `SCHEMA_VERSION >= 88` (F124: no head pinned), the index present, no other table's schema changed.
- `tests/test_phase303_auth_api.py`: every route of item 6 at every status it names; a token in exactly one response; the problem envelope; a session on a shop route, a kb route and the live route; expired and revoked sessions 401; the owner's reset allowed for `manage_users`, refused for an apprentice and for a member of another shop; the rate limiter's key and tier for a session; login limited as anonymous. The fixtures follow `test_phase180_shop_api.py`'s (`init_db` on a temp path, `create_app(db_path_override=...)`, `TestClient`).
- `tests/test_phase303_tier_for_session.py`: the stop 1b reading the operator picks, with the other reading's test kept as the control that the two differ.
- `tests/test_phase303_user_cli.py`: each `user` subcommand under `CliRunner`, hidden prompt and `--password-stdin`, no password in output or `--json`, the short password refused, deactivate revokes.
- `tests/test_phase303_caller_on_request.py`: `request.state.caller` carries user id, credential kind and session id for a key and for a session, the seam 348 reads.
- A wiring test that `/v1/auth/login` is routed by `create_app` and that `user` is registered on the CLI (the working rules: a module called from one integration point ships with a test that the point calls it).
- `docs/phases/in_progress/303_mutate.py`, after 392's harness: each mutation breaks one guard (the constant-time compare, the expiry check, the revoked check, the active-user check, the `manage_users` gate, the one-reason login, the no-write rule, the session's tier rule, the minimum length, the prefix dispatch in `get_api_key`) and a test goes red; N/N recorded in `303_mutate.out`.
- `COLLECTED_TEST_FLOOR` rises by a diff of collected ids against master, the reason in the commit message. `wholetree.sh` before every commit, run on its own; `wholetree.sh --full` before the commit that touches `migrations.py` (the guard refuses it otherwise) and before the regression of record; `regression.sh` for the line of record.

## Non-goals

- The app's login screen. Phases 185–204 are the mobile repository's (`ROADMAP_AUTHORITY.md`); until a mobile phase adds the screen, the app keeps its API key, and the API this phase ships is what that screen will call.
- Gating the CLI, the diagnostic commands or any existing route beyond what it checks today (fork 1a's second reading).
- A lockout after failed logins, an idle timeout, a last-seen column on sessions, or any addition to `deploy.SERVER_WRITES`.
- Password reset by email, single sign-on, two-factor, or retiring API keys.
- Phase 348's audit log itself; this phase only leaves the caller on the request for it.
- Any migration that changes an existing row; anything under `data/`; seed data; a split or an eval protocol.
- F210's general rule (row 330's need, K52).

## Planned items

- [ ] Stops 1a, 1b, 1c and the two numbers asked on the mission issue in plain English, and answered in the operator's own words before items 2 and 4 are built
- [ ] Migration 088 and `SCHEMA_VERSION` 88, with the scope file and the dry run on a copy of live
- [ ] `auth/passwords.py`
- [ ] `auth/sessions_repo.py`, with the F210 control
- [ ] `auth/deps.py`: the second credential, `AuthedUser`'s new fields, `request.state.caller`; the kb and live annotations
- [ ] `api/middleware.py`: the limiter knows a session
- [ ] `api/routes/auth.py`, `app.py`, `openapi.py`, `errors.py`
- [ ] `shop/rbac.py`: `list_member_permissions`
- [ ] `cli/user.py` and its registration
- [ ] `core/config.py`: `session_lifetime_days`
- [ ] Tests, the wiring tests, the mutation script, the floor
- [ ] `docs/guide/api.md`, `docs/guide/shop-workflow.md`
- [ ] Regression of record, `apply-live` on the desktop, `verify-live`, the close-out commit, the handoff with the operator's steps, the merge by the operator's hand, `verify_phase.sh`
