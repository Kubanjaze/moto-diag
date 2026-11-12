# Phase 372 — phase log: Payment API routes and the app's payment screens

**Status:** In progress

Built by the Chief Engineer in the fleet's fence, on `phase-372-payment-api-routes-and-the-app`; the plan is `372_implementation.md` v1.0, approved by the Executive Officer on issue #59.

## 2026-11-12: How the record answers Step 0's stops

The Science Officer's Step 0 (`372_step0.md`) listed five stops, (a) to (e). Four are answered by the record; (d) stays a fork.

- **(a) Stripe's live account.** It exists and is in use: live payments went on at 21:10 EST on 2026-11-11 (`docs/handoffs/2026-11-10_402_closed.md`, "Live payments went on"). K66 did not cover this phase, so it did not start early; it starts with the account in use.
- **(b) Which issue holds the phase.** Issue #59, the mission issue this phase was opened from. K76 names it ("issue #59 (372) keeps its hold"). K66's issue #54 is Phase 371's (K65, K70 and K73 all name #54 for 371), so the two do not conflict. The hold on #59 is lifted when the operator marks the plan approved; the Executive Officer's approval of v1.0 is on #59.
- **(c) The sequencing.** Every row before #14 in "Next, in order" is ✅, which is why `plan_order.py` picked 372; the 2026-10-22 to 2026-10-25 entry's first-shop rows 303 and 348 have closed.
- **(d) The app half.** A real fork, left to the operator: (A) one phase, both repositories; (B) the routes now and the screens as a letter follow-on. The plan's recommendation is (A). The operator picks at the Gate 11 stop at the latest.
- **(e) The live key.** No step of the build or the tests reads it: the tests use the test-only key in `tests/support/stripe_fixtures.py` and Stripe's recorded answers.

The decisions, character for character from `docs/decisions.md`:

- K48 (2026-10-27): "1: The plan of record stays the single source; add a short "Next, in order" list at its top that the fleet reads exactly; it changes only by a dated entry with a K-id, written on my word."
- K66 (2026-11-05): "yes, the fleet can start before the live account"
- K76 (2026-11-09): "402: start it now, the fleet builds it."

## 2026-11-12: Items 1 and 2 built (the routes, the error map, the document)

- **`src/motodiag/api/routes/payments.py`**, new: the five routes, each on `Depends(require_tier("shop"))` (which wraps `get_current_user`) and `require_shop_access` imported from `shop_mgmt.py`: the account read for any active member, connect on `manage_billing`, the two starts and the payments list on `manage_shop`. Registered in `app.py` beside `shop_mgmt_router`.
- **Decided here:** the responses are pydantic models, so the document carries the fields by name for the app's generated types; an invoice not at the shop raises `InvoiceNotFoundError`, whose row in the chain already answers 404 `invoice-not-found`, so the 404 is a problem document like its neighbours; the account read's "no account" is an `HTTPException(404)` with the plan's sentence, before any Stripe call; connect sends `contact_email or ""`, so a missing email is `connect_shop`'s own refusal (409). Besides `_invoice_shop_id`, three small private helpers: `_require_invoice_at_shop` (the check the three invoice routes share), `_account` and `_started_fields` (the answer's fields). None writes.
- **`src/motodiag/api/errors.py`**: four rows in `_exc_class_chain`, `ConnectError` 409 `payment-refused`, `StripeNotConfigured` and `LiveKeyRefused` 503 `payments-not-configured`, `StripeUnavailable` 503 `stripe-unavailable`. `StripeLibraryMissing` is a `StripeNotConfigured` and answers through its row.
- **`src/motodiag/api/openapi.py`**: `payments` in `TAG_CATALOG` and in `_ALWAYS_TIER_GATED_TAGS`. Each route declares 403 as `{"$ref": "#/components/responses/Forbidden"}` and 409 and 503 with the `ProblemDetail` schema. FastAPI adds a `description` beside the `$ref`, which OpenAPI 3.1 allows on a reference.
- `create_app().openapi()`: each of the five operations carries `security` and 401, 402, 403, 404, 409 and 503.

## 2026-11-12: Item 4, the tests

- `tests/test_phase372_payment_routes.py`, 26 tests, all green on the first run. Only the writer, who logs in for the audit test, gets a password hash; the other callers use API keys (a hash per user made the file 76 s).
- `tests/test_phase372_wiring.py`, 18 tests, read with `code_of`.
- **Against master's code.** A scratch worktree at `62c9f3c` (master's code) with the new route module and the two test files copied in, so only `app.py`, `errors.py` and `openapi.py` were master's, run with that worktree's `src/` on `PYTHONPATH`: route tests 1 passed / 25 failed, wiring 10 passed / 8 failed, `tests/test_phase273_connect.py` 12 passed / 0 failed, `tests/test_phase273_invoice_payments.py` 35 passed / 0 failed. The ten wiring tests that passed read the route module's own text, which the control kept. The one route test that passed was "an invoice that does not exist is 404": a path nobody serves is a 404 too, so it could not fail. It now also requires the problem type `invoice-not-found`, and re-run on master's code it is red (1 failed); on the branch its class is 4 passed. So all 26 route tests are red on master's code.
- **Mutations.** `372_mutate.py`, the plan's thirteen, on 348's harness; its output is `372_mutate.out`: **13/13 red**, every file restored. The route mutations run the route tests alone, so each is caught by an answer, not by the wiring file's reading of the text.
- **The OpenAPI suites unchanged:** `tests/test_phase372_wiring.py`, `test_phase183_openapi.py`, `test_phase184_gate9.py`, `test_phase204_gate10.py` and `test_phase205_gate11.py` together: 91 passed, 1 skipped, 2 failed, the two failures Gate 11's `TestContractSnapshot` (below).
- **`COLLECTED_TEST_FLOOR`** 12576 → 12620, by a diff of collected ids against `62c9f3c`, each side with its own `src/`: +44 −0 (26 and 18).
- The quality counts (`scripts/code_quality.py counts`) equal their pins: ruff 1108, mypy 202, complex 25, big 5, helpers 19, swallowed 22. The test file's import order was put right for ruff before the commit.
- `wholetree.sh`: exit 0, 2634 passed, 10 skipped. Commit `2106fc7`.

## 2026-11-12: Item 5, the guide; item 6, the app's prompt

- `docs/guide/api.md`: the `payments` row (five operations) and the sentence on `manage_billing` and `manage_shop` under "Tiers and limits". `docs/guide/payments.md`: "From the app".
- **`README.md`'s route count** said "Serves 80 routes", from Phase 208 (`e79ad0f`) and already wrong: master's code serves 112 operations, by `create_app().openapi()`. The plan says the count "moves with it"; moving 80 by five would print another wrong number, so it now says 117, the measured count on this branch.
- `docs/prompts/372_the_apps_payment_screens.txt`, for the session in `moto-diag-mobile` under option A; `docs/prompts/README.md` lists it in a new section, "Written for a session in the mobile repository", since its table lists only the prompts moved in on 2026-09-27.

## 2026-11-12: Gate 11 is red, as the plan says

`tests/test_phase205_gate11.py`, `TestContractSnapshot`:

- `test_every_live_path_is_in_the_committed_snapshot`: missing the five operations of this phase, and nothing else.
- `test_every_live_schema_is_in_the_committed_snapshot`: missing `CheckoutStarted`, `ConnectAnswer`, `ConnectRequest`, `InvoicePayment`, `InvoicePayments`, `PaymentAccount` and `TerminalStarted`, this phase's seven models, and nothing else.

The phone app's copy at `../moto-diag-mobile` is read-only inside the fence and stands at `04be61c` on `main` (348's refresh). No gate is loosened. As for 303 and 348, the Engineer commits what is built and stops with kind `test-cannot-be-green`; the operator refreshes the app's snapshot on the mobile branch `phase-372-payment-api-routes-and-the-app` and picks between the plan's options (A) and (B). The regression of record and the close-out wait for that.
