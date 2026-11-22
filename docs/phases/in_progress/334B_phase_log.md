# Phase 334B — phase log

**Status:** In progress

## 2026-11-22 — Step 0 and v1.0

The operator, 2026-11-22 (K128): "im taking all your recommendations, log
it all, prompt me when its time to continue and you give me the next prompt
for main". Among them: 334B is next for the app, its prompt read again
first. Then: "334B: finish the plan and hand me the prompt. Do not build it
yourself. I run app phases as a separate session that opens the PR in
moto-diag-mobile only; you keep the moto-diag record, same split as 303B.
Include in the prompt the small wording fix from 303B: the sign-in
screen's "Set an API key first." line."

Step 0 (`334B_step0.md`) read the app at `2f6739c` and this repository at
`b95f3d0`:
- nothing in the app calls the terms routes yet, and no web link is opened
  anywhere;
- 303B left the host, the client hook, the events module and the sign-out
  sequence to build on;
- the wording line is the home screen's "Authed smoke" block, line 574.
Classification: extension.

v1.0 (`334B_implementation.md`): the terms box rendered by `SignInHost`;
the 403 hook in `customFetch`, once per burst; agreeing, with the stale 422
read again; one sign-out shared with the home screen; the wording line;
and their tests. Row 334B is marked 🚧 in the same commit.

**Two changes from the prompt as first written,** made when it was read
again, with the reasons:
- **The box opens only when the server asks** (its 403), not at start-up.
  K128 turns the switch on after 334B and after 293's new terms version so
  that every user accepts once, and a start-up box while the switch is off
  would ask each user twice.
- **The 403 hook sits in `customFetch`,** not in `use()` middleware, as
  303B found: the middleware runs before the credential is added.

**Who builds and who records.** The build is the operator's own session in
`moto-diag-mobile` on `phase-334B-the-apps-terms-screen`. It opens its pull
request there only, and writes nothing in this repository. The advisor
keeps this log, the row and the close-out here, from the app's pull
request, as for 303B.

**Where these files live until the close-out.** On this repository's branch
of the same name, as 303B's did: the push guard refuses a phase's files on
master before its close-out (303B's log, 2026-11-20). Row 334B is marked 🚧
on master in its own commit, with its pin in
`tests/test_phase334_legal_texts.py`.
