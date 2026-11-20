# Phase 303B — The app's staff sign-in screen

**Version 1.0, 2026-11-20.** Plan by the advisor session on the Mac (K99),
from this repository's master `2fb8f90` and the app's `main` `2267ea5`.
Built by a session in `moto-diag-mobile`, on the branch
`phase-303B-the-apps-staff-sign-in-screen`, from
`docs/prompts/303B_the_apps_staff_sign_in_screen.txt`. Classification:
**extension** (`303B_step0.md`). This plan is committed before any code.

## Goal

A shop's staff sign in to the app with the username and password the
server has had since Phase 303, instead of each needing an API key made for
them by hand. The app keeps the sign-in like today's key, says who is
signed in, signs out properly, and asks again when a sign-in has ended. The
pasted key stays as a second way in. No server change.

## The plan of record

'Next, in order' #22 (K99), first of the app's three screens (sign-in, then
the terms, then payments), after 344 and before 210. Built by a builder
session in the app's repository, which the fleet waits for only when it
reaches it. The operator merges the app's pull request after the advisor's
review.

## Logic

In the app's code the new credential is **a sign-in** and its token **a
sign-in token**, never "a session": the app uses "session" for a diagnostic
session on 384 lines in 45 files (`303B_step0.md`, S0-1). The server's own
words stay where the server is quoted.

### 1. A sign-in token lives in the existing slot

The token is stored with `ApiKeyProvider.setApiKey` and sent by the client
exactly as a key is (`X-API-Key`), which the server accepts for both. The
slot holds one credential at a time. One helper in `src/api/auth.ts`,
`isSignInToken(value)`, is true for a value that starts `mds_`; nothing
else changes in the slot, the Keychain service or the client's headers.

### 2. The sign-in box

`src/screens/SignInModal.tsx`, new, beside `ApiKeyModal`, rendered once
near the root (`App.tsx`, inside `ApiKeyProvider`, beside the navigation
container) so it can open over any screen, by the home screen's button or
by an ended sign-in (item 5), through the same small module.
`ApiKeyModal` may move there with it, so that "Use an API key instead"
works wherever the box opened:
- username and password fields (the password hidden; neither field
  autocorrects or capitalises), a "Sign in" button, and "Use an API key
  instead", which closes it and opens `ApiKeyModal` as the home screen
  does today;
- "Sign in" posts `POST /v1/auth/login` through the shared client with
  `client` set to the app's name and platform, cut to 64 characters;
- on 200: `setApiKey(token)`, then `resyncPushRegistration()`, as
  `handleSubmitKey` does, then close;
- on 401 `login-failed`: "That username or password is wrong." and the
  password field emptied. Any other failure shows the client's existing
  error text (`src/api/errors.ts`, `describeError`).
- The password lives only in the box's own state while it is open, and is
  never logged.

### 3. The home screen's auth block

`AuthBlock` in `src/screens/HomeScreen.tsx`:
- **No credential:** "Not signed in.", a "Sign in" button (opens the box)
  and "Use an API key instead" (opens `ApiKeyModal`).
- **A sign-in token:** "Signed in as" the user's `full_name`, or else
  `username`, from `GET /v1/auth/me` (read when the block shows a sign-in
  token; on failure it says "Signed in" with no name), and "Sign out". The
  token itself is never shown, masked or not.
- **A pasted key:** today's view, unchanged (status line, `maskKey`,
  "Replace", "Clear").

### 4. Signing out

`handleSignOut`, beside `handleClearKey`, behind the same kind of
confirmation: `deregisterPushToken()` while the token still works, then
`POST /v1/auth/logout` (204), then `clearApiKey()`. A failed logout is
logged and signing out goes on, so a dead network never leaves a user stuck
signed in. A pasted key's "Clear" stays as it is and never calls logout
(the server answers 400 `not-a-session` for a key).

### 5. A sign-in that has ended

One response hook on the shared client (`src/api/client.ts`, through
`use()`, or in `customFetch`, whichever the build finds smaller): a 401
whose problem type ends `invalid-api-key`, on a request that carried a
sign-in token, means the sign-in expired (30 days by default) or was ended.
It fires once per token through a small listener module
(`src/api/signInEvents.ts`); `ApiKeyProvider` listens and clears the slot
through its own `clearApiKey`, so its state follows, and the sign-in box
opens saying "Your sign-in has ended. Please sign in again." A pasted key's
401 is left to each screen's own message, as today; a 401 `login-failed`
from the box itself never fires it.

### 6. The record

This repository keeps `303B_step0.md`, this plan, `303B_phase_log.md`, row
303B and, at the close-out, the handoff. The advisor writes them, from the
app's pull request: its description carries the build's notes, decisions
and test results. The app's session writes nothing here, and the app's
`phase_log.md` (185 to 204) is not touched.

## Rule-1 stops anticipated

- **A real fork: none known.** K99 and the prompt fix the scope. Where the
  box is rendered and whether the 401 hook is middleware or part of
  `customFetch` are build choices that ship the same behaviour.
- **A threshold or a rule's definition: none.** No server change, no
  change to what the server refuses.
- **A test that cannot be made green: none known.** If existing tests break
  on the auth block's new words, the session updates them and names each in
  the pull request; if one cannot be made green, it stops.
- **A login or a credential: none for the build.** Tests use made-up
  values. A check on a phone with a real staff account is the operator's,
  after the merge.
- **A live-database change: none.**

## Tests

In the app, in its own style (`__tests__/api/client.test.ts`'s mocked
fetch; `*.smoke.test.tsx` for screens):
1. `isSignInToken`: true for an `mds_` value, false for a key and for an
   empty value.
2. The box: a 200 stores the token and resyncs the push token (both
   mocked), then closes; a 401 `login-failed` shows the message and empties
   the password; "Use an API key instead" opens the key box; `client` is
   sent and is at most 64 characters.
3. The auth block: with a sign-in token it shows the name from
   `GET /v1/auth/me` and never the token; with a key it is unchanged; with
   nothing it offers both ways in.
4. Signing out: the calls come in the order deregister, logout, clear; a
   failed logout still clears; a key's "Clear" never calls logout.
5. An ended sign-in: a 401 `invalid-api-key` on a sign-in token clears the
   slot once and opens the box with its message; the same 401 on a pasted
   key does neither; a 401 `login-failed` from the login call does neither.
6. Each new test is seen red before its code (the pull request says how).

`npx tsc --noEmit` and `npx eslint .` clean; `npx jest` green, with the
count before and after in the pull request.

## Non-goals

Changing a password; an owner resetting a member's password; the list of
open sign-ins; showing or editing roles; adding staff; the terms screen
(334B, next); any server change; the store listings; a build for the
phones (a release step after the merge).

## Deviations

To be written at v1.1.

## Results

To be written at v1.1.

## Planned items

- [ ] `isSignInToken`, the sign-in box, and the auth block's three views
- [ ] Signing out, with logout only for a sign-in
- [ ] An ended sign-in noticed once, the slot cleared, the box opened
- [ ] The tests, each seen red; tsc, eslint and jest clean
- [ ] The app's pull request, merged by the operator after review
- [ ] The close-out here: v1.1, the log, row 303B ✅, the handoff

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-20 | The plan, from Step 0 (K99). |
