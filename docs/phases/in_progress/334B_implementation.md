# Phase 334B — The app's terms screen

**Version 1.0, 2026-11-22.** Plan by the advisor session on the Mac (K98,
K128), from this repository's master `b95f3d0` and the app's `main`
`2f6739c`. Built by the operator's own session in `moto-diag-mobile`, on the
branch `phase-334B-the-apps-terms-screen`, from
`docs/prompts/334B_the_apps_terms_screen.txt`. Classification:
**extension** (`334B_step0.md`). This plan is committed before any code.

## Goal

When the server asks a user to accept the Terms of Service, the app shows
them the version and its date, opens the terms and the privacy policy in
the phone's browser, and records their "I agree" with the version shown, or
lets them sign out instead. It then returns them to where they were. No
server change.

## The plan of record

'Next, in order' #22 (K98; K128 moved 344 after 210), the second of the
app's three screens: sign-in (303B, closed), then the terms, then payments
(372B). Built by the operator's own session in the app's repository (the
home desktop's main chat), beside the fleet's 293. The operator merges the
app's pull request after the advisor's review.

## Logic

The app's name rule stands: a credential from the sign-in box is **a
sign-in**, never "a session" (`334B_step0.md`, S0-4).

### 1. The terms box

`src/screens/TermsModal.tsx`, new, rendered once by `SignInHost` beside the
sign-in and key boxes, so it opens over any screen:
- the version and its date, read from `GET /v1/terms` each time the box
  opens;
- "Read the terms" and "Read the privacy policy", which open `terms_url`
  and `privacy_url` in the phone's browser with `Linking.openURL`;
- "I agree", which posts `POST /v1/terms/accept` with the version shown;
- "Sign out", which signs the stored credential out (item 4);
- no Cancel: while the server asks, every other call is refused, so the
  box stays until the user agrees or signs out.

### 2. When it opens: when the server asks

In `customFetch` (`src/api/client.ts`), beside 303B's ended-sign-in hook: a
403 whose problem type ends `/terms-not-accepted`, read from a clone so the
screen still gets its own error, calls `notifyTermsRequired()` in a small
module, `src/api/termsEvents.ts`, shaped like `signInEvents.ts`. It fires
once, however many calls were refused, until the box closes. `SignInHost`
listens and opens the box.

Not at start-up. The terms switch goes on after this phase and after 293's
new terms version, so every user accepts once (K128). A box shown at
start-up while the switch is off would ask each user twice. While the
switch is off, the box never opens.

### 3. Agreeing

On 200 the box closes and the user is where they were. The call that was
refused is not repeated by itself; the user tries it again. On 422 whose
type ends `/terms-version-stale`, the text changed while the box was open:
read `GET /v1/terms` again and show the new version in the same box, saying
so. Any other failure shows `describeError`'s text in the box.

### 4. Signing out from the box

One sign-out, shared by the home screen and the terms box. The sequences
move out of `HomeScreen.tsx` into one function, for example `signOut()` in
`src/api/signIn.ts`, and both call it:
- **a sign-in:** mark the token (`suppressSignInEnded`), deregister the
  push token, `POST /v1/auth/logout`, clear;
- **a pasted key:** deregister the push token, clear, and never logout.

The home screen's two confirmations stay where they are. 303B's home-screen
tests pass unchanged.

### 5. The wording line

`src/screens/HomeScreen.tsx`, line 574: with nothing stored, the "Authed
smoke" block says "Set an API key first.". It becomes "Sign in first.", at
the operator's word (2026-11-22). Any test naming the old words is updated
and named in the pull request.

### 6. The record

This repository keeps `334B_step0.md`, this plan, `334B_phase_log.md`, row
334B and, at the close-out, the handoff. The advisor writes them, from the
app's pull request: its description carries the build's notes, decisions
and test results. The app's session writes nothing here, and the app's
`phase_log.md` (185 to 204) is not touched.

## Rule-1 stops anticipated

- **A real fork: none known.** K128 settles when the box opens. Where the
  sign-out function lives, and the events module's exact shape, are build
  choices that ship the same behaviour.
- **A threshold or a rule's definition: none.** No server change.
- **A test that cannot be made green: none known.** If existing tests break
  on the moved sign-out or the new words, the session updates them and
  names each in the pull request; if one cannot be made green, it stops.
- **A login or a credential: none for the build.** Tests use made-up
  values. A check on a phone needs a server with the switch on: the
  operator's live server once the switch goes on (after 293, K128), or a
  test server, at the operator's choice after the merge.
- **A live-database change: none.**

## Tests

In the app, in its own style (`__tests__/api/client.test.ts`'s mocked
fetch; `*.smoke.test.tsx` for screens):
1. The client hook: a 403 `terms-not-accepted` fires once, and a burst of
   three fires once; a 403 of another type, a 401 and a 200 do not; after
   the box closes, a later 403 fires again.
2. The box: it shows the version and date from `GET /v1/terms` (mocked);
   the two links call `Linking.openURL` with the two addresses; "I agree"
   posts the version shown and closes; a 422 `terms-version-stale` reads
   again and shows the new version; another error shows its text; there is
   no Cancel.
3. Signing out from the box: for a sign-in, deregister, logout and clear,
   in that order; for a key, deregister and clear, with no logout.
4. The host: a terms-required event opens the box over any screen, and
   agreeing closes it.
5. The wording: with nothing stored, the "Authed smoke" block says "Sign in
   first."
6. Each new test is seen red before its code (the pull request says how);
   303B's tests pass unchanged.

`npx tsc --noEmit` and `npx eslint .` with no errors; `npx jest` green, with
the count before and after in the pull request.

## Non-goals

The text of the terms (two pages on getmekno.com, whose addresses
`GET /v1/terms` gives); any server change; a start-up check (K128); repeating
a refused call by itself; the live WebSocket route, which the switch does
not hold (334's handoff: the box opens from the REST calls around it);
turning the switch on; Stripe Checkout's terms consent (parked on Stripe
support); the store listings' privacy links; a build for the phones.

## Deviations

To be written at v1.1.

## Results

To be written at v1.1.

## Planned items

- [ ] The terms box, rendered by `SignInHost`
- [ ] The 403 hook in `customFetch`, once per burst, through `termsEvents.ts`
- [ ] "I agree", and the stale 422 read again
- [ ] One sign-out, shared by the home screen and the box
- [ ] The wording line: "Sign in first."
- [ ] The tests, each seen red; tsc, eslint and jest clean
- [ ] The app's pull request, merged by the operator after review
- [ ] The close-out here: v1.1, the log, row 334B ✅, the handoff

## Version history

| version | date | change |
|---|---|---|
| 1.0 | 2026-11-22 | The plan, from Step 0 (K98, K128). |
