# Phase 334B — Step 0: what the app has for the terms

**Written 2026-11-22** by the advisor session on the Mac, from this
repository's master `b95f3d0` and the app's `main` at `2f6739c` (303B's
merge), at the operator's word (K98, K128; row 334B, the prompt
`docs/prompts/334B_the_apps_terms_screen.txt`). The app's code was read,
never changed; the build is the operator's own session in
`moto-diag-mobile`, which writes nothing here.

Classification: **extension.** The server has had the terms, their two
routes and the switch since Phase 334. Since 303B the app has the places a
terms box plugs into: the one host near the root that renders the sign-in
and key boxes (`SignInHost`), the client hook that sees an ended sign-in in
`customFetch`, the small events module those two talk through, and the
sign-out sequence. What is new is the terms box itself, the client's answer
to 403 `terms-not-accepted`, the accept call, and the app's first link to a
web page.

## S0-1 — the nouns, counted in the app's source

Each count below is `git grep -c -F -e '<term>' -- src App.tsx ':!src/api-types.ts'`
in `moto-diag-mobile` at `2f6739c`, summed over files (the generated types
left out, since they name every route):

| term | lines | files | what it shows |
|---|---|---|---|
| `v1/terms` | 0 | 0 | nothing calls the terms routes |
| `terms-not-accepted` | 0 | 0 | nothing answers the switch's 403 |
| `terms-version-stale` | 0 | 0 | nothing answers the stale 422 |
| `Linking` | 8 | 5 | only `Linking.openSettings()`, for camera and microphone permissions: no web link is opened anywhere yet |
| `SignInHost` | 8 | 5 | 303B's host near the root, which renders the boxes |
| `onSignInUiRequest` | 3 | 2 | the host's channel for "open a box" |
| `notifySignInEnded` | 5 | 2 | the client hook's channel for an ended sign-in |
| `handleSignOut` | 2 | 1 | the sign-out sequence lives in the home screen only |
| `endSignIn` | 4 | 2 | the logout call, in `src/api/signIn.ts` |
| `useApiKey` | 16 | 8 | the credential's one hook |
| `Set an API key first` | 1 | 1 | the line the operator asked to change: `src/screens/HomeScreen.tsx`, line 574 |

The generated types name both routes: `git grep -c -F -e '"/v1/terms"' -e '"/v1/terms/accept"' -- src/api-types.ts api-schema/openapi.json`
counts 2 in each file. Unlike 303B's three routes, these answer typed
models (`TermsInfo`, `Acceptance`), so no narrowing at the boundary is
needed.

## S0-2 — the server, on master `b95f3d0`

Read in `src/motodiag/api/routes/terms.py`, `src/motodiag/auth/terms_acceptance.py`,
`src/motodiag/auth/deps.py` and `src/motodiag/api/errors.py`:
- `GET /v1/terms` answers `TermsInfo`: `version`, `date`, `terms_url`,
  `privacy_url`, and, with a credential, `accepted` and `accepted_at`
  (both null for an anonymous caller).
- `POST /v1/terms/accept` with `{"version": ...}` answers `Acceptance`
  (`version`, `accepted_at`). A version that is not the current one is 422
  with the problem type ending `terms-version-stale`.
- With `MOTODIAG_TERMS_REQUIRED` on, every credentialed route answers 403
  with the type ending `terms-not-accepted` until the caller accepts,
  except `TERMS_EXEMPT_PATHS`: read the terms, accept them, see who they
  are, or sign out. The switch is off on live (334's handoff).
- The live WebSocket route resolves its credential itself and is the one
  credentialed route the switch does not hold (334's handoff).

## S0-3 — what changed since the prompt was first written

The prompt was written on 2026-11-19 and corrected on 2026-11-20, before
303B. Read again now:
- **The app has staff sign-in** (303B, `2f6739c`). The prompt's "sign out
  means clearApiKey" is now two sequences: a sign-in signs out with
  deregister, `POST /v1/auth/logout` and clear (after marking the token so
  its own 401s open nothing); a pasted key's "Clear" deregisters and
  clears, and never calls logout.
- **The hook's place:** 303B found that `use()` middleware runs before
  `customFetch` adds the credential, so its hook went into `customFetch`.
  The 403 hook goes beside it.
- **The pages show version 1.0** (published with 408, 2026-11-21): the
  prompt's note that they showed an older text is past.
- **When the switch goes on:** after 334B and after 293's new terms
  version, so every user accepts once (K128). A box shown at start-up while
  the switch is off would ask each user twice, for 1.0 now and for 293's
  version later. So the box opens only when the server asks, by its 403.
- **The wording line** is the home screen's "Authed smoke" block, not a
  sign-in screen: with nothing stored it says "Set an API key first."

## S0-4 — the name rule, kept

In the app's code a credential from the sign-in box is **a sign-in**, never
"a session" (303B's S0-1: "session" means a diagnostic session on 384 lines
in 45 files). The terms box follows it.
