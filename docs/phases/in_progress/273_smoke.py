"""Phase 273 — the smoke calls, through the app's own commands.

Run by ``273_smoke.sh``, which loads the operator's test-mode keys into
this process's environment from ``~/.config/motodiag/stripe-test.env``;
nothing here reads, prints or writes a key or a webhook secret.

Every Stripe request is answered by Stripe's own HTTP client, wrapped so
each response is kept under ``273_smoke/responses/`` (the one-use
onboarding URL and e-mail addresses removed) to become a recorded
fixture. The product's own call log (``MOTODIAG_STRIPE_CALL_LOG``) writes
``273_smoke/calls.jsonl``.

The database is a scratch copy of live, never live:
``~/.cache/motodiag/phase273/smoke.db``.

Stages: prepare, connect, status, setup, paylink, checkout, terminal,
portal, summary.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = HERE / "273_smoke"
SCRATCH = Path.home() / ".cache" / "motodiag" / "phase273"
DB = SCRATCH / "smoke.db"
LIVE = ROOT / "data" / "motodiag.db"
IDS = RUN / "ids.json"

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _guard() -> None:
    if Path(os.environ.get("MOTODIAG_DB_PATH", "")).resolve() != DB.resolve():
        sys.exit(f"MOTODIAG_DB_PATH must be the scratch copy {DB}")
    if DB.resolve() == LIVE.resolve():
        sys.exit("refusing to run against the live database")
    key = os.environ.get("MOTODIAG_STRIPE_API_KEY", "")
    if not key.startswith(("sk_test_", "rk_test_")):
        sys.exit("the key loaded is not a test-mode key; nothing was called")


def _record_responses() -> None:
    """Keep each response body for the fixtures, with the onboarding link
    and e-mail addresses removed."""
    import stripe

    from motodiag.payments import stripe_api

    inner = stripe.new_default_http_client()
    out = RUN / "responses"
    out.mkdir(parents=True, exist_ok=True)

    class Keep(stripe.HTTPClient):
        name = "phase273-smoke"

        def request(self, method, url, headers, post_data=None, **kwargs):
            body, status, resp_headers = inner.request(method, url, headers, post_data)
            n = len(list(out.glob("*.json"))) + 1
            path = url.split("api.stripe.com", 1)[-1].split("?")[0]
            text = body.decode() if isinstance(body, bytes) else body
            try:
                data = json.loads(text)
            except ValueError:
                data = {"_unparsed": len(text)}
            if isinstance(data, dict) and data.get("object") == "v2.core.account_link":
                data["url"] = "[one-use onboarding link, not kept]"
            kept = json.loads(EMAIL.sub("owner@example.com", json.dumps(data)))
            name = f"{n:02d}_{method.lower()}{re.sub(r'[^a-z0-9]+', '_', path.lower())}.json"
            (out / name).write_text(json.dumps({
                "_fixture": {"kind": "recorded",
                             "source": f"Stripe test mode, {method.upper()} {path}, "
                                       "via 273_smoke.py",
                             "request_id": (resp_headers or {}).get("Request-Id")},
                "status": status, "body": kept}, indent=2) + "\n")
            return body, status, resp_headers

        def close(self):
            inner.close()

    stripe_api._test_http_client = Keep()


def _motodiag(*args: str) -> int:
    from motodiag.cli.main import cli

    print(f"\n$ motodiag {' '.join(args)}", flush=True)
    try:
        rv = cli.main(list(args), prog_name="motodiag", standalone_mode=False)
        return int(rv or 0)
    except SystemExit as e:
        return int(e.code or 0)
    except Exception as e:  # the command's own refusal, shown as it is
        code = getattr(e, "exit_code", 1)
        print(f"[exit {code}] {e}")
        return code


def _ids() -> dict:
    return json.loads(IDS.read_text())


def prepare() -> None:
    """A scratch copy of live (read-only backup API), migrated, with a smoke
    shop in Massachusetts, two sent invoices and a user to subscribe."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        Path(str(DB) + suffix).unlink(missing_ok=True)
    src = sqlite3.connect(f"file:{LIVE}?mode=ro", uri=True)
    dst = sqlite3.connect(DB)
    src.backup(dst)
    src.close()
    dst.close()
    from motodiag.accounting import tax
    from motodiag.core.database import get_connection, init_db

    init_db(str(DB))
    with get_connection(str(DB)) as conn:
        shop = conn.execute(
            "INSERT INTO shops (name, address, city, state, zip) VALUES "
            "('Phase 273 Smoke Shop', '1 Test Street', 'Boston', 'MA', '02110')"
        ).lastrowid
        cust = conn.execute("INSERT INTO customers (name) VALUES "
                            "('Phase 273 smoke customer')").lastrowid
        bike = conn.execute(
            "INSERT INTO vehicles (make, model, year, powertrain, engine_type) "
            "VALUES ('Honda', 'CB500F', 2020, 'ice', 'four_stroke')").lastrowid
        invoices = []
        for n, total in ((1, 12.34), (2, 56.78)):
            wo = conn.execute(
                "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title) "
                "VALUES (?, ?, ?, ?)", (shop, bike, cust, f"Phase 273 smoke {n}"),
            ).lastrowid
            invoices.append(conn.execute(
                "INSERT INTO invoices (customer_id, invoice_number, status, subtotal, "
                "tax_amount, total, currency, work_order_id) VALUES (?, ?, 'sent', ?, 0, "
                "?, 'USD', ?)", (cust, f"INV-273-SMOKE-{n}", total, total, wo),
            ).lastrowid)
        user = conn.execute("INSERT INTO users (username, email) VALUES "
                            "('phase273smoke', 'owner@example.com')").lastrowid
    tax.set_shop_jurisdiction(shop, "US-MA", db_path=str(DB))
    IDS.write_text(json.dumps({"shop": shop, "checkout_invoice": invoices[0],
                               "terminal_invoice": invoices[1], "user": user},
                              indent=2) + "\n")
    print(f"scratch copy ready: {DB} (schema migrated); ids in {IDS.name}")


def main(stage: str) -> int:
    if stage == "prepare":
        prepare()
        return 0
    _guard()
    _record_responses()
    ids = _ids()
    if stage == "check":
        return _motodiag("payments", "check")
    if stage == "connect":
        return _motodiag("shop", "payments", "connect", "--shop", str(ids["shop"]),
                         "--email", os.environ["PHASE273_OWNER_EMAIL"])
    if stage == "status":
        return _motodiag("shop", "payments", "status", "--shop", str(ids["shop"]))
    if stage == "setup":
        return _motodiag("shop", "terminal", "setup", "--shop", str(ids["shop"]),
                         "--simulated")
    if stage == "paylink":
        return _motodiag("shop", "invoice", "pay-link", str(ids["checkout_invoice"]))
    if stage == "checkout":
        return _motodiag("subscription", "checkout-url", "--user", str(ids["user"]),
                         "--tier", "shop")
    if stage == "terminal":
        return _motodiag("shop", "terminal", "pay", str(ids["terminal_invoice"]))
    if stage == "portal":
        return _motodiag("subscription", "portal-url", "--user", str(ids["user"]))
    if stage == "summary":
        return summary(ids)
    sys.exit(f"unknown stage {stage!r}")


def summary(ids: dict) -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    out = []
    for inv in (ids["checkout_invoice"], ids["terminal_invoice"]):
        r = conn.execute("SELECT invoice_number, status, paid_at FROM invoices "
                         "WHERE id = ?", (inv,)).fetchone()
        out.append(f"invoice {r['invoice_number']}: {r['status']} (paid_at {r['paid_at']})")
    for r in conn.execute("SELECT id, channel, amount_cents, status, outcome, "
                          "outcome_reason FROM invoice_payments ORDER BY id"):
        out.append(f"payment {r['id']}: {r['channel']} {r['amount_cents']} cents, "
                   f"{r['status']}, {r['outcome']} {r['outcome_reason'] or ''}".rstrip())
    for r in conn.execute("SELECT tier, status, current_period_end, stripe_price_id "
                          "FROM subscriptions WHERE user_id = ?", (ids["user"],)):
        out.append(f"subscription: {r['tier']} {r['status']}, period ends "
                   f"{r['current_period_end']}, price {r['stripe_price_id']}")
    for r in conn.execute("SELECT status, amount_paid_cents, currency FROM "
                          "subscription_payments WHERE user_id = ?", (ids["user"],)):
        out.append(f"subscription payment: {r['status']} {r['amount_paid_cents']} "
                   f"{r['currency']}")
    for r in conn.execute("SELECT type, COUNT(*) n, SUM(error IS NOT NULL) errors, "
                          "SUM(account IS NOT NULL) connect FROM stripe_webhook_events "
                          "GROUP BY type ORDER BY type"):
        out.append(f"event {r['type']}: {r['n']} received, {r['errors']} with an "
                   f"error, {r['connect']} from a connected account")
    for r in conn.execute("SELECT type, error FROM stripe_webhook_events "
                          "WHERE error IS NOT NULL"):
        out.append(f"  error on {r['type']}: {r['error']}")
    text = "\n".join(out)
    print(text)
    (RUN / "summary.txt").write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
