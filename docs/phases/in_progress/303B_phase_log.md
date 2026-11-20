# Phase 303B — phase log

**Status:** In progress

## 2026-11-20 — Step 0 and v1.0

The operator, 2026-11-20, evening (K99): "yes add the staff sign-in screen
to the list too", then "yes write the sign-in screen instructions" and
"yes write the sign-in screen plan".

Master `45c26d9` holds K99, row 303B and its place in 'Next, in order'
(#22, before 334B, 372B and 210); `2fb8f90` holds the prompt,
`docs/prompts/303B_the_apps_staff_sign_in_screen.txt`, written against
both repositories' code.

Step 0 (`303B_step0.md`) read the app at `2267ea5` and this repository at
`2fb8f90`: nothing in the app calls the login, me or logout routes; the
Keychain slot, the client and the push token's resync and deregister are
there to build on; "session" already means a diagnostic session in the
app, so the new credential is called a sign-in. Classification: extension.

v1.0 (`303B_implementation.md`): the token in the existing slot, the
sign-in box, the auth block's three views, signing out with logout only for
a sign-in, an ended sign-in noticed once by the client, and their tests.
Row 303B is marked 🚧 in the same commit.

**Who builds and who records.** The build is a session in
`moto-diag-mobile` on `phase-303B-the-apps-staff-sign-in-screen`; it writes
nothing in this repository. The advisor keeps this log, the row and the
close-out here, from the app's pull request.
