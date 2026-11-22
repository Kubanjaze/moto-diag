# Phase 334B — The app's terms screen

**Version 1.1, 2026-11-22.** Closed. v1.0 (the same day) was the plan by
the advisor session on the Mac (K98, K128), from this repository's master
`b95f3d0` and the app's `main` `2f6739c`. Built by the operator's own
session in `moto-diag-mobile`, on the branch
`phase-334B-the-apps-terms-screen`, from
`docs/prompts/334B_the_apps_terms_screen.txt`: pull request #12, head
`e71fd74`, merged by the operator as `58142e4` on 2026-11-22.
Classification: **extension** (`334B_step0.md`). The plan was committed
before any code; this version records what was built, from the pull
request's description and the advisor's review of it.

## Goal

When the server asks a user to accept the Terms of Service, the app shows
them the version and its date, opens the terms and the privacy policy in
the phone's browser, and records their "I agree" with the version shown, or
lets them sign out instead. It then returns them to where they were. No
server change.

Met in code and tests. The check on a phone waits for a server with the
terms switch on (Rule-1 stops, and the handoff).

## The plan of record

'Next, in order' #22 (K98; K128 moved 344 after 210), the second of the
app's three screens: sign-in (303B, closed), the terms (this phase,
closed), then payments (372B, whose prompt the advisor writes fresh). Built
by the operator's own session in the app's repository, beside the fleet's
293; the operator merged the app's pull request after the advisor's
review.

## Logic

The app's name rule stands: a credential from the sign-in box is **a
sign-in**, never "a session" (`334B_step0.md`, S0-4). Built that way.

### 1. The terms box

As planned. `src/screens/TermsModal.tsx`, rendered once by `SignInHost`
beside the sign-in and key boxes. It reads `GET /v1/terms` each time it
opens and shows "Version <version>, <date>". "Read the terms" and "Read the
privacy policy" open `terms_url` and `privacy_url` with `Linking.openURL`,
the app's first links to a web page. "I agree" posts the version shown.
"Sign out" signs out (item 4). No Cancel, and Android's back button leaves
it up. Added in the build: when `GET /v1/terms` itself fails, the box shows
the error and a "Try again" link (Deviations, 1).

### 2. When it opens: when the server asks

As planned. In `customFetch` (`src/api/client.ts`), beside 303B's
ended-sign-in hook: a 403 whose problem type ends `/terms-not-accepted`,
read from a clone, calls `notifyTermsRequired()` in
`src/api/termsEvents.ts`. It fires once until the box closes
(`termsBoxClosed()`); `SignInHost` listens and opens the box. Nothing at
start-up (K128). `src/api/errors.ts` gains `TermsProblemSlug`
(`'terms-not-accepted' | 'terms-version-stale'`) beside `AuthProblemSlug`.

### 3. Agreeing

As planned. On 200 the box closes and the refused call is not repeated. On
422 `terms-version-stale` the box reads `GET /v1/terms` again and shows
"The terms changed while this was open. This is the new version." Any other
failure shows `describeError`'s text.

### 4. Signing out from the box

As planned. `signOut(credential, clearCredential)` in `src/api/signIn.ts`,
moved out of `HomeScreen.tsx`. For a sign-in it marks the token, deregisters
the push token, logs out and clears. For a pasted key it deregisters and
clears, and never calls logout. The home screen's two confirmations call
it, and so does the terms box, through `SignInHost`. Signing out from the
box closes it and opens nothing else (Deviations, 2).

### 5. The wording line

As planned. The home screen's "Authed smoke" block says "Sign in first."
with nothing stored (`src/screens/HomeScreen.tsx`, line 565 after item 4's
move). No existing test named the old words.

### 6. The record

As planned. This repository keeps `334B_step0.md`, this plan,
`334B_phase_log.md`, row 334B and the handoff, written by the advisor from
the app's pull request. The app's session wrote nothing here. The phase's
files stayed on this repository's branch of the same name until the
close-out.

## Rule-1 stops

None met in the build.
- **A real fork:** none. K128 settled when the box opens.
- **A threshold or a rule's definition:** none. No server change.
- **A test that cannot be made green:** none. No existing test changed.
- **A login or a credential:** none; the tests use made-up values. The
  check on a phone needs a server with the terms switch on: the live
  server once the operator turns it on (after 293, K128), or a test server,
  at the operator's choice. It has not run.
- **A live-database change:** none.

## Tests

In the app, 23 new tests, each in a new file, so 303B's files are
unchanged:
- `__tests__/api/signOut.test.ts` (4): the shared sign-out for a sign-in
  and for a key.
- `__tests__/api/termsEvents.test.ts` (6): a 403 `terms-not-accepted`
  fires once and the caller still gets its error; a burst of three fires
  once; a 403 of another type, a 401 and a 200 do nothing; after the box
  closes, a later 403 fires again.
- `__tests__/screens/TermsModal.smoke.test.tsx` (7): the version and date,
  the two links, "I agree", the stale 422, other errors, no Cancel.
- `__tests__/screens/SignInHost.terms.test.tsx` (5): closed at start, with
  nothing asked of the server; a terms-required event opens the box;
  agreeing closes it and a later refusal opens it again; signing out from
  the box for a sign-in (deregister, logout, clear) and for a key (no
  logout).
- `__tests__/screens/HomeSmokeWording.test.tsx` (1): "Sign in first."
- **Each seen red first,** as the pull request records: against missing
  modules, a stub box that renders nothing, a host without the box, the
  hook not yet in `customFetch`, and the old words.

## Non-goals

The text of the terms; any server change; a start-up check (K128);
repeating a refused call by itself; the live WebSocket route; turning the
switch on; Stripe Checkout's terms consent; the store listings' privacy
links; a build for the phones. None of them was built.

## Deviations

1. **"Try again" in the box,** not in the plan: when `GET /v1/terms` fails
   as the box opens, it shows the error and a link to read the terms again.
   Without it the user's only way out would be "Sign out".
2. **Signing out from the box closes it and opens nothing else.** The plan
   did not say; the home screen's "Sign in" is there.
3. **The new tests are in new files,** not added to 303B's, so those files
   stay unchanged.
4. **The wording line moved to line 565,** after item 4 took the sign-out
   sequences out of `HomeScreen.tsx`.
5. **Not run: the check on a phone,** which needs a server with the terms
   switch on (Rule-1 stops). It is open in the handoff.

## Results

| | before (`main` `2f6739c`) | after (`e71fd74`) |
|---|---|---|
| `npx jest` | 104 suites, 1248 passed | 109 suites, 1271 passed (+23) |
| `npx tsc --noEmit` | clean | clean |
| `npx eslint .` | 0 errors, 143 warnings | 0 errors, 143 warnings |
| `npm run generate-api-types` | changes nothing | — |

- **The advisor's re-run on the Mac,** 2026-11-22, in a scratchpad clone at
  `e71fd74`, with the same lockfile as the app checkout: tsc exit 0; eslint
  exit 0, 0 errors and 143 warnings; jest 109 suites and 1271 tests passed.
  The pull request adds test files only and removes no line of a test.
- **Merged** by the operator as `58142e4` (moto-diag-mobile `main`),
  2026-11-22 at 20:30 UTC.
- **This repository:** no code changed. Its regression of record, on the
  close-out's merge of master (`445e000`), is in the log.

## Planned items

- [x] The terms box, rendered by `SignInHost`
- [x] The 403 hook in `customFetch`, once per burst, through `termsEvents.ts`
- [x] "I agree", and the stale 422 read again
- [x] One sign-out, shared by the home screen and the box
- [x] The wording line: "Sign in first."
- [x] The tests, each seen red; tsc, eslint and jest clean
- [x] The app's pull request, merged by the operator after review (#12,
  `58142e4`)
- [x] The close-out here: v1.1, the log, row 334B ✅, the handoff

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-22 | The plan, from Step 0 (K98, K128). |
| 1.1 | 2026-11-22 | Closed: what was built (pull request #12, `e71fd74`, merged as `58142e4`), five deviations, the results. |
