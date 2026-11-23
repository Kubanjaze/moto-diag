# Phase 303B — The app's staff sign-in screen

**Version 1.1, 2026-11-22.** Closed. v1.0 (2026-11-20) was the plan by the
advisor session on the Mac (K99), from this repository's master `2fb8f90`
and the app's `main` `2267ea5`. Built by the operator's own session in
`moto-diag-mobile`, on the branch
`phase-303B-the-apps-staff-sign-in-screen`, from
`docs/prompts/303B_the_apps_staff_sign_in_screen.txt`: pull request #11,
head `b7ad88f`, merged by the operator as `2f6739c` on 2026-11-22.
Classification: **extension** (`303B_step0.md`). The plan was committed
before any code; this version records what was built, from the pull
request's description and the advisor's review of it.

## Goal

A shop's staff sign in to the app with the username and password the
server has had since Phase 303, instead of each needing an API key made for
them by hand. The app keeps the sign-in like today's key, says who is
signed in, signs out properly, and asks again when a sign-in has ended. The
pasted key stays as a second way in. No server change.

Met, as planned: the four checks on a real iPhone passed (Results).

## The plan of record

'Next, in order' #22 (K99), first of the app's three screens (sign-in, then
the terms, then payments), after 344 and before 210. Built by a builder
session in the app's repository; the operator merged the app's pull request
after the advisor's review. The app's next screen is 334B, the terms.

## Logic

In the app's code the new credential is **a sign-in** and its token **a
sign-in token**, never "a session": the app uses "session" for a diagnostic
session on 384 lines in 45 files (`303B_step0.md`, S0-1). The server's own
words stay where the server is quoted. Built that way: in the new code the
word appears only in the server's own words (`credential.kind`'s
`'session'`, in `CredentialKind`, and the problem type `not-a-session`) and
in the comment that states this rule.

### 1. A sign-in token lives in the existing slot

As planned. `isSignInToken(value)` and `SIGN_IN_TOKEN_PREFIX = 'mds_'` in
`src/api/auth.ts`. The token is stored with `setApiKey` and sent as
`X-API-Key`, like a key (the server's own test, `key_prefix.startswith("mds_")`
in `src/motodiag/auth/api_key_repo.py`, tells the two apart). Nothing else
changes in the slot, the Keychain service or the client's headers.

### 2. The sign-in box

`src/screens/SignInModal.tsx`, rendered once by `src/screens/SignInHost.tsx`,
which `App.tsx` mounts inside `ApiKeyProvider`, beside the navigation
container. `ApiKeyModal` moved there with it, so "Use an API key instead"
works wherever the box opened; any screen opens either box through
`openSignIn()` and `openApiKeyEntry()` in `src/api/signInEvents.ts`.
- The username and password fields (the password hidden; neither
  autocorrects or capitalises), "Sign in", and "Use an API key instead".
- "Sign in" posts `POST /v1/auth/login` through `signIn()` in
  `src/api/signIn.ts`, with `client` set to "MotoDiag <platform>
  <version>", cut to 64 characters (the server's `LoginRequest.client`
  limit).
- On 200, `SignInHost` stores the token, then resyncs the push token, then
  closes the box, as `handleSubmitKey` did.
- On 401 `login-failed`: "That username or password is wrong." and the
  password emptied. Any other failure shows `describeError`'s text.
- The password lives only in the box's state while it is open, is emptied
  each time the box opens, and is never logged.

### 3. The home screen's auth block

`AuthBlock` in `src/screens/HomeScreen.tsx`, as planned:
- **No credential:** "Not signed in.", "Sign in" and "Use an API key
  instead".
- **A sign-in token:** "Signed in as" the user's `full_name`, or else
  `username`, from `GET /v1/auth/me` ("Signed in" if that fails), and
  "Sign out". The token itself is never shown.
- **A pasted key:** today's view, unchanged.

### 4. Signing out

`handleSignOut`, behind a confirmation: `deregisterPushToken()`, then
`POST /v1/auth/logout` (`endSignIn()`), then `clearApiKey()`. A failed
logout is logged and signing out goes on; the push step catches its own
failures too. A pasted key's "Clear" never calls logout. Added in the
build: the token is marked first (`suppressSignInEnded`), so a 401 from
sign-out's own calls does not pop the "has ended" box (Deviations, 1).

### 5. A sign-in that has ended

In `customFetch` (`src/api/client.ts`), not `use()` middleware: the
middleware runs before `customFetch` adds `X-API-Key`, so only
`customFetch` knows whether the request carried a sign-in token. A 401
whose problem type ends `/invalid-api-key`, on a request that carried a
sign-in token, calls `notifySignInEnded(token)`, once per token, reading
the body from a clone so each screen still gets its own error.
`ApiKeyProvider` clears the slot, only if the Keychain still holds that
token, and `SignInHost` opens the box saying "Your sign-in has ended.
Please sign in again." A pasted key's 401, and a `login-failed`, never fire
it. `hasProblemSlug()` and the union `AuthProblemSlug` are in
`src/api/errors.ts`, shared by the client and `signIn.ts`.

### 6. The record

As planned. This repository keeps `303B_step0.md`, this plan,
`303B_phase_log.md`, row 303B and the handoff, written by the advisor from
the app's pull request. The app's session wrote nothing here, and the app's
`phase_log.md` (185 to 204) is not touched. The phase's files stayed on
this repository's branch of the same name until the close-out: the push
guard refused them on master on 2026-11-20 (the log says so).

## Rule-1 stops

None met in the build.
- **A real fork:** none. Where the box is rendered and where the 401 hook
  lives were build choices, and both ship the planned behaviour.
- **A threshold or a rule's definition:** none. No server change.
- **A test that cannot be made green:** none. No existing test had to
  change.
- **A login or a credential:** none for the build; the tests use made-up
  values. For the phone check the operator signed in with their own
  login on live, after resetting its password there themselves (the
  log).
- **A live-database change:** none by the phase. The operator's own
  password reset changed one existing row on live, after a backup (the
  log, and the handoff's live outcome).

## Tests

In the app, in its own style, 51 new tests:
- `__tests__/api/signIn.test.ts` (23): `isSignInToken`, the client label
  at most 64 characters, login 200, `login-failed`, other failures, no
  token and a thrown call, `/me`, logout 204 and failure,
  `hasProblemSlug`, the events (once per token, the mark, unsubscribing),
  and the client hook (a sign-in token's 401 fires once; a pasted key's
  401, a `login-failed` and a 200 do not).
- `__tests__/screens/SignInModal.smoke.test.tsx` (7),
  `__tests__/screens/SignInHost.test.tsx` (8),
  `__tests__/contexts/ApiKeyProvider.signInEnded.test.tsx` (2) and
  `__tests__/screens/HomeAuth.test.tsx` (10): the box, the host, the
  provider's clear, and the auth block's three views and sign-out
  (deregister, logout, clear, in that order; a failed logout still
  clears; a key's "Clear" calls no logout).
- A wiring guard in `__tests__/App.coldStart.smoke.test.tsx` (1): `App`
  mounts `SignInHost`.
- **Each seen red first,** as the pull request says: `signIn.test.ts`
  before its modules existed, and its hook test again with the notify call
  removed; for the rest, each code path removed or reordered until its test
  went red, then restored.

## Non-goals

Changing a password; an owner resetting a member's password; the list of
open sign-ins; showing or editing roles; adding staff; the terms screen
(334B, next); any server change; the store listings; a build for the
phones (a release step after the merge). None of them was built.

## Deviations

1. **The mark on sign-out, `suppressSignInEnded(token)`,** was not in the
   plan. Without it, signing out of a sign-in the server had already ended
   would open "Your sign-in has ended" at someone who is leaving. Tested.
2. **The home screen's test result resets on any change of credential**
   (an effect on the stored value), not inside the key box's handlers,
   because storing a credential moved to `SignInHost`. The same behaviour.
3. **The client label carries the app's version** ("MotoDiag <platform>
   <version>"), where the plan named the app's name and platform. Still cut
   to 64 characters.
4. **`ApiKeyModal` moved to `SignInHost`,** which the plan allowed; the
   home screen's "Set" and "Replace" open it through `openApiKeyEntry()`.
5. **Lint:** 0 errors, and 143 warnings where `main` has 140. The three new
   ones are `no-void` on `void promise` calls, the style `App.tsx` and
   `HomeScreen.tsx` already use. The plan's "eslint clean" is read as no
   errors.
6. **The phone check ran before the merge,** at the pull request's own
   suggestion, where the plan put it after; the operator ran it, with the
   advisor's added tap (the key box opened from inside the sign-in box).
7. **Left as it was:** the "Authed smoke" block's hint "Set an API key
   first." still says that. It is outside what the plan names; a one-line
   wording change for a later app session.
8. **One pull request, in the app's repository only,** as the prompt says.
   This record is the advisor's, from that pull request.

## Results

| | before (`main` `2267ea5`) | after (`b7ad88f`) |
|---|---|---|
| `npx jest` | 99 suites, 1197 passed | 104 suites, 1248 passed (+51) |
| `npx tsc --noEmit` | clean | clean |
| `npx eslint .` | 0 errors, 140 warnings | 0 errors, 143 warnings |
| `npm run generate-api-types` | changes nothing | — |

- **The advisor's re-run on the Mac,** 2026-11-22, in a scratchpad clone at
  `b7ad88f` (the app's repository runs no checks on a pull request): tsc
  exit 0; eslint exit 0, 0 errors and 143 warnings; jest 104 suites and
  1248 tests passed. No line of an existing test was removed.
- **The phone check,** by the operator on a real iPhone, 2026-11-22, all
  four passed: a wrong password is refused; signing in with a real login
  works; signing out is clean; and "Use an API key instead" opens the key
  box, whose Cancel returns to the home screen.
- **Merged** by the operator as `2f6739c` (moto-diag-mobile `main`),
  2026-11-22 at 16:47 UTC.
- **This repository:** no code changed. Its regression of record, on the
  close-out's merge of master (`2225ec3`), is in the log.

## Planned items

- [x] `isSignInToken`, the sign-in box, and the auth block's three views
- [x] Signing out, with logout only for a sign-in
- [x] An ended sign-in noticed once, the slot cleared, the box opened
- [x] The tests, each seen red; tsc, eslint and jest clean (eslint: no
  errors, Deviations 5)
- [x] The app's pull request, merged by the operator after review (#11,
  `2f6739c`)
- [x] The close-out here: v1.1, the log, row 303B ✅, the handoff

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-20 | The plan, from Step 0 (K99). |
| 1.1 | 2026-11-22 | Closed: what was built (pull request #11, `b7ad88f`, merged as `2f6739c`), eight deviations, the results, the phone check. |
