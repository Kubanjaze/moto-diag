"""Phase 273's mutations: each breaks one thing the phase promises, and the
tests named beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/completed/273_mutate.py`
(moved from in_progress/ at close-out). 281's form: each mutation replaces
one exact string (which must occur once), runs its tests with `-B` after
clearing `__pycache__`, and restores the file whatever happens. Prints one
line per mutation and exits 1 if any stayed green. An argument runs only
the mutations whose name starts with it: `K` the gateway and keys, `S` the
test session's secrets, `C` Connect, `P` invoice payments, `W` the
webhook, `F` F187, `M` migration 080, `Y` bug fixes #1 and #2.

No mutation can reach Stripe: every test answers from fixtures through the
SDK's http_client, and 281's network guard holds.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
T_GATE = ["tests/test_phase273_gateway.py"]
T_SECRETS = ["tests/test_phase273_secrets.py"]
T_CONNECT = ["tests/test_phase273_connect.py"]
T_INV = ["tests/test_phase273_invoice_payments.py"]
T_SUB = ["tests/test_phase273_subscriptions.py"]
T_MIG = ["tests/test_phase273_migration.py"]

API = "src/motodiag/payments/stripe_api.py"
CONNECT = "src/motodiag/payments/connect.py"
PAY = "src/motodiag/payments/invoice_payments.py"
HOOKS = "src/motodiag/billing/webhook_handlers.py"
PROVIDERS = "src/motodiag/billing/providers.py"
ROUTE = "src/motodiag/api/routes/billing.py"
CLI_PAY = "src/motodiag/cli/payments.py"
CLI_BILL = "src/motodiag/cli/billing.py"
MIGRATIONS = "src/motodiag/core/migrations.py"
CONFTEST = "tests/conftest.py"

MUTATIONS = [
    # ------------------------------------------------------------ the gateway
    ("K1 a live key is allowed outside prod", API,
     "    if key.startswith(LIVE_KEY_PREFIXES) and env != Environment.PROD:",
     "    if False:", T_GATE),
    ("K2 a restricted live key is not refused", API,
     'LIVE_KEY_PREFIXES = ("sk_live_", "rk_live_")', 'LIVE_KEY_PREFIXES = ("sk_live_",)',
     T_GATE),
    ("K3 the API version is the account's older one", API,
     'API_VERSION = "2026-09-30.endive"', 'API_VERSION = "2026-08-26.dahlia"', T_GATE),
    ("K4 Stripe's key-quoting error is not scrubbed", API,
     '    return _SECRET_SHAPED.sub("[redacted]", text)', "    return text", T_GATE),
    ("K5 the call log names the connected account", API,
     '"connected_account": bool((req_headers or {}).get("Stripe-Account")),',
     '"connected_account": (req_headers or {}).get("Stripe-Account"),', T_GATE),
    ("K6 every key counts as test mode", API,
     "    return key.startswith(TEST_KEY_PREFIXES)", "    return True", T_GATE),
    ("K7 176's provider skips the live-key check", PROVIDERS,
     "            stripe_api.refuse_live_key(api_key, self._settings.env)",
     "            pass", T_GATE),
    # ------------------------------------------------------------ the test session's secrets
    ("S1 Stripe settings are not blanked (a .env value is read)", CONFTEST,
     'for _name in STRIPE_SETTINGS_BLANKED:\n    os.environ[_name] = ""\n', "", T_SECRETS),
    ("S2 exported Stripe variables are not removed", CONFTEST,
     '    if _name.startswith(("MOTODIAG_STRIPE_", "STRIPE_")):\n        del os.environ[_name]',
     "    pass", T_SECRETS),
    ("S3 the provider is not forced to fake", CONFTEST,
     'os.environ["MOTODIAG_BILLING_PROVIDER"] = "fake"\n', "", T_SECRETS),
    # ------------------------------------------------------------ Connect
    ("C1 the platform carries the shop's losses", CONNECT,
     'LOSSES_COLLECTOR = "stripe"', 'LOSSES_COLLECTOR = "application"', T_CONNECT),
    ("C2 the shop gets the Express dashboard", CONNECT,
     'DASHBOARD = "full"', 'DASHBOARD = "express"', T_CONNECT),
    ("C3 a shop can be paid before card_payments is active", CONNECT,
     '        return self.card_payments_status == "active"', "        return True", T_CONNECT),
    ("C4 eventually-due requirements count as due now", CONNECT,
     'in ("currently_due", "past_due"))', 'in ("currently_due", "past_due", "eventually_due"))',
     T_CONNECT),
    # ------------------------------------------------------------ invoice payments
    ("P1 an event from another account pays the invoice", PAY,
     '    if event.get("account") != row["stripe_account_id"]:\n        raise PaymentEventRejected(\n'
     "            f\"payment {row['id']} belongs to",
     "    if False:\n        raise PaymentEventRejected(\n"
     "            f\"payment {row['id']} belongs to", T_INV),
    ("P2 a short amount pays the invoice", PAY,
     '    if received != row["amount_cents"] or received != owed:', "    if False:", T_INV),
    ("P3 another currency pays the invoice", PAY,
     '    if currency != inv["currency"].lower():', "    if False:", T_INV),
    ("P4 starting a Checkout payment marks the invoice paid", PAY,
     '"UPDATE invoice_payments SET checkout_session_id = ?, livemode = ? WHERE id = ?",',
     "\"UPDATE invoices SET status = 'paid' WHERE ? IS NOT NULL AND ? IS NOT NULL AND id = ?\",",
     T_INV),
    ("P5 a success is not final", PAY,
     '        if row["status"] == "succeeded":\n            return "unchanged',
     '        if False:\n            return "unchanged', T_INV),
    ("P6 paid twice is not reported", PAY,
     '    if inv["status"] == "paid":', "    if False:", T_INV),
    ("P7 a draft or cancelled invoice can be paid", PAY,
     'PAYABLE_STATUSES = ("sent", "overdue")',
     'PAYABLE_STATUSES = ("sent", "overdue", "draft", "paid", "cancelled")', T_INV),
    ("P8 a late, older refund lowers the refunded amount", PAY,
     "SET refunded_cents = MAX(refunded_cents, ?) WHERE id = ?",
     "SET refunded_cents = ? WHERE id = ?", T_INV),
    ("P9 the Checkout Session is made on the platform", PAY,
     '                "stripe_account": acct.stripe_account_id,\n                "idempotency_key"',
     '                "idempotency_key"', T_INV),
    ("P10 the card-present intent carries no metadata", PAY,
     '                "metadata": meta,\n            }, {**opts,', "            }, {**opts,", T_INV),
    # ------------------------------------------------------------ the webhook
    ("W1 a live event is applied outside prod", HOOKS,
     '    if event.get("livemode") and s.env != Environment.PROD:', "    if False:", T_INV),
    ("W2 a repeated event runs its handler again", HOOKS,
     "        if cur.rowcount == 0:", "        if False:", T_SUB),
    ("W3 a retryable failure is recorded, so never retried", HOOKS,
     "        _forget_event(event_id, db_path)\n",
     '        _mark_processed(event_id, error="x", db_path=db_path)\n', T_SUB),
    ("W4 the route answers 200 when the event must be retried", ROUTE,
     "    if result.retry:", "    if False:", T_SUB),
    # ------------------------------------------------------------ F187
    ("F1 checkout's metadata does not reach the subscription", PROVIDERS,
     '            "subscription_data": {"metadata": meta},\n', "", T_SUB),
    ("F2 the period is read from the subscription, as before Basil", HOOKS,
     '        "current_period_start": _iso_ts(item.get("current_period_start")),',
     '        "current_period_start": _iso_ts(sub.get("current_period_start")),', T_SUB),
    ("F3 a missing tier is invented", HOOKS,
     "    if tier is None:\n        raise SubscriptionEventError(",
     '    if tier is None:\n        tier = "individual"\n    if False:\n'
     "        raise SubscriptionEventError(", T_SUB),
    ("F4 a missing status is invented", HOOKS,
     '    if not sub.get("status"):\n',
     '    if not sub.get("status"):\n        sub["status"] = "active"\n    if False:\n', T_SUB),
    ("F5 the payload is trusted, not re-read", HOOKS,
     "    sub = provider.retrieve_subscription(sub_id)\n",
     "    sub = provider.retrieve_subscription(sub_id)\n"
     '    sub = {**sub, "status": "active"}\n', T_SUB),
    ("F6 a late failure overwrites a tier payment", HOOKS,
     "status = CASE WHEN subscription_payments.status = 'paid'\n"
     "                               THEN 'paid' ELSE excluded.status END,",
     "status = excluded.status,", T_SUB),
    # ------------------------------------------------------------ migration 080
    ("M1 the rollback keeps subscription_payments", MIGRATIONS,
     "            DROP TABLE IF EXISTS subscription_payments;\n", "", T_MIG),
    ("M2 the rollback keeps stripe_webhook_events.livemode", MIGRATIONS,
     "            ALTER TABLE stripe_webhook_events DROP COLUMN livemode;\n", "", T_MIG),
    ("M3 deleting an invoice deletes its Stripe payments", MIGRATIONS,
     "                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT,",
     "                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,", T_MIG),
    ("M4 a payment of 0 cents is accepted", MIGRATIONS,
     "                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),",
     "                amount_cents INTEGER NOT NULL,", T_MIG),
    # ------------------------------------------------------------ bug fix #1
    ("Y1 pay-link prints its URL through rich again", CLI_PAY,
     "        click.echo(started.checkout_url)  # never through rich (bug fix #1)",
     '        console.print(f"    {started.checkout_url}")', T_INV),
    ("Y1b checkout-url prints its URL through rich again", CLI_BILL,
     "        click.echo(result.checkout_url)", '        console.print(f"    {result.checkout_url}")',
     T_SUB),
    # ------------------------------------------------------------ bug fix #2
    ("Y2 an invoice before its subscription waits for a retry again", HOOKS,
     "        _store_from_stripe(sub_id, db_path, provider, settings)\n"
     "        existing = get_subscription_by_stripe_id(sub_id, db_path=db_path)",
     '        raise BillingProviderError("not stored yet; retry")', T_SUB),
]


def run_tests(tests: list[str]) -> int:
    for base in (ROOT / "src", ROOT / "tests"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
         "-o", "addopts=", *tests],
        cwd=ROOT, capture_output=True, text=True,
    ).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    every = sorted({t for m in chosen for t in m[4]})
    assert run_tests(every) == 0, "the tests are not green before mutating"
    survivors = []
    for name, rel, old, new, tests in chosen:
        path = ROOT / rel
        original = path.read_text()
        assert original.count(old) == 1, f"{name}: the text occurs {original.count(old)} times"
        try:
            path.write_text(original.replace(old, new))
            code = run_tests(tests)
        finally:
            path.write_text(original)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    assert run_tests(every) == 0, "the tests are not green after restoring"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
