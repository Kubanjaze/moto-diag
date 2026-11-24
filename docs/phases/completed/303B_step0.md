# Phase 303B — Step 0: what the app has for signing in

**Written 2026-11-20** by the advisor session on the Mac, from this
repository's master `2fb8f90` and the app's `main` at `2267ea5` (K99, row
303B, the prompt `docs/prompts/303B_the_apps_staff_sign_in_screen.txt`).
The app's code was read, never changed; the build is a session in
`moto-diag-mobile`, which writes nothing here.

Classification: **extension.** The app already has the one place a
credential lives (the Keychain slot behind `ApiKeyProvider`), the client
that sends it on every call, the home screen's auth block that sets and
clears it, and the push token's resync and deregister around both. What is
new is a second way to fill that slot (a username and password, through
the server's login), the sign-out that ends a sign-in on the server, and
the answer to a sign-in that has ended. No server change.

## S0-1 — the nouns, counted in the app's source

Each count below is `git grep -c -E '<term>' -- src ':!src/api-types.ts'`
in `moto-diag-mobile` at `2267ea5`, summed over files (the generated types
left out, since they name every route):

| term | lines | files | what it shows |
|---|---|---|---|
| `auth/login` | 0 | 0 | nothing calls the login route |
| `auth/logout` | 0 | 0 | nothing ends a sign-in |
| `auth/me` | 0 | 0 | nothing asks who the caller is |
| `mds_` | 0 | 0 | nothing knows a sign-in token |
| `useApiKey` | 13 | 6 | the credential's one hook, read by the home screen and `useTier` |
| `ApiKeyModal` | 6 | 3 | the paste box, opened only from the home screen |
| `\.use\(` | 1 | 1 | the client passes middleware through; none is installed |
| `session` | 384 | 45 | the word means a **diagnostic session** in the app |
| `Session` | 254 | 40 | the same: `SessionsStack`, `SessionDetailScreen`, `NewSessionScreen` |

The last two rows decide a name: in the app's code the new credential is
**a sign-in** (its token a sign-in token), never "a session", so that no
reader confuses it with the diagnostic sessions the app is built around.
The server's words (`/v1/auth/logout` "ends the calling session",
`credential.kind == "session"`) stay as the server says them, in the
places that call it.

## S0-2 — the code paths a sign-in goes through

- **The slot.** `src/contexts/ApiKeyProvider.tsx` gives `apiKey`,
  `isLoading`, `setApiKey` and `clearApiKey`; `src/api/auth.ts` keeps the
  value in the Keychain (service `moto-diag-mobile`) and sends it as the
  `X-API-Key` header. The server reads a sign-in token from that header as
  it reads a key (`src/motodiag/auth/deps.py`, `get_api_key`, then
  `resolve_credential`, dispatched on the `mds_` prefix). So a token can
  live in the same slot and go out the same way, with no change to the
  client's headers.
- **The client.** `src/api/client.ts` builds every call through
  `customFetch`, which reads the slot on each request, and exposes
  openapi-fetch's `use()`. A response hook installed there sees every
  401, which is where an ended sign-in is noticed once rather than in each
  screen's hook (the hooks keep their own messages: `shopAccessErrors.ts`,
  `pdfDownloadErrors.ts`, `useReportShareLink.ts`, `dtcErrors.ts` each map
  401 for their screen).
- **The home screen.** `src/screens/HomeScreen.tsx`'s "Auth" section is
  `AuthBlock` (line 421): with no credential, "Not authenticated." and a
  "Set API key" button; with one, a status line, `maskKey` (the first 13
  characters and "•••"), "Replace" and "Clear". `handleSubmitKey` stores a
  key and calls `resyncPushRegistration()`; `handleClearKey` asks, then
  `deregisterPushToken()` while the credential still works, then
  `clearApiKey()`.
- **The server.** `src/motodiag/api/routes/auth.py`: `POST /v1/auth/login`
  (`username`, `password`, optional `client` of at most 64 characters)
  answers `token`, `expires_at`, `user` (`id`, `username`, `full_name`,
  `email`) and `memberships`; a wrong password is 401 `login-failed`, with
  no lockout or throttle in the code. `GET /v1/auth/me` adds `credential`
  (`kind`, `id`, `prefix`) and `tier`. `POST /v1/auth/logout` is 204 for a
  sign-in and 400 `not-a-session` for a key. A sign-in lasts
  `session_lifetime_days` (30, `src/motodiag/core/config.py`); after that,
  or once ended, `verify_session` no longer resolves it and every route
  that needs a credential answers 401 `invalid-api-key`.

## S0-3 — the app's own copy of the server

`api-schema/openapi.json` names `/v1/auth/login`, `/v1/auth/me` and
`/v1/auth/logout` (`grep -c` gives 1 for each); the generated
`src/api-types.ts` came from that copy in the app's pull request 10
(`9a6972d`). So the types step finds nothing to do.

## S0-4 — the tests the build extends

- `__tests__/api/client.test.ts` (532 lines) stands in for the server with
  a mocked fetch; `__tests__/api/auth.test.ts` (166 lines) covers the
  Keychain slot. `jest.setup.js` mocks the native modules globally.
- The screens' tests are `*.smoke.test.tsx` and helper tests under
  `__tests__/screens/`; the home screen has `HomeNoServer.test.tsx`.

## S0-5 — the verbs

Every action the row promises has a way for a user to do it:

| the row says | the user's way |
|---|---|
| staff sign in by username and password | the sign-in box, from the home screen's auth block |
| the app keeps the token like today's key | nothing to do: the slot keeps it across restarts |
| signs out | "Sign out" in the same block |
| an expired or ended sign-in asks again | the sign-in box opens by itself, saying why |
| (kept) a pasted key | "Use an API key instead", the existing box |

## S0-6 — what bears on the plan

- **K99**, the operator's words, and **K98** (the app's screens on the list
  before 210, built in the app's repository). 334B, the terms screen,
  comes next and builds on this sign-in and sign-out; its prompt is read
  again once this merges.
- **The authority contract** (`ROADMAP_AUTHORITY.md`): row 303B and these
  files are this repository's; the app's `phase_log.md` covers 185 to 204.
- **The app's repository has no `CLAUDE.md`**, so the prompt carries the
  working rules.
- **No rule-1 stop is foreseen** (the plan's section says which would
  be one).
