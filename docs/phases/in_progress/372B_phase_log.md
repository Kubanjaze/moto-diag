# Phase 372B — phase log

**Status:** In progress

## 2026-11-22 — Step 0 and v1.0

The operator, 2026-11-22 (K128): "im taking all your recommendations", one
of which was that 372B gets a fresh prompt from the advisor after 334B.
Then, after 334B closed: "give me the prompt from main to continue through
it", and "i mean continue through whats to be accomplished right now. we
are running a strict schedule here".

Step 0 (`372B_step0.md`) read the app at `58142e4` and this repository at
`618bc73`:
- the app's types name all seven routes, and nothing in the app calls
  them yet;
- the stacks, the settings screen, the shop-access errors, the share sheet
  and the tier hook are there to build on.
Classification: extension.

v1.0 (`372B_implementation.md`) is 372's item 7, re-read against today's
code:
- one hook for the payment routes;
- card payments setup;
- an invoice's payment at the reader or by pay-link, with its outcome;
- the plan screen;
- and their tests.
Row 372B is marked 🚧 in the same commit.

**Who builds and who records.** As for 303B and 334B: the operator's own
session in `moto-diag-mobile` on `phase-372B-the-apps-payment-screens`
opens its pull request there only and writes nothing here. The advisor
keeps this log, the row and the close-out. These files stay on this
repository's branch of the same name until the close-out; row 372B is
marked 🚧 on master in its own commit.
