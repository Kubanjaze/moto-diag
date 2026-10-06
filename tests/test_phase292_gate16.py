"""Gate 16 — one job walked from booking to the accounting export (Phase 292).

Track O's closing gate. On a freshly migrated database, through the real
commands, in the row's order: staff book the customer's appointment; the
intake; the work order; the warranty check, with a claim on the covered
case; the repair; the invoice; the payment; the export. Every row the walk
needs comes from a command a user can run.

- **Two card walks.** An invoice is paid once, so the walk runs twice: paid
  through `shop invoice pay-link` and through `shop terminal pay`. Each is
  paid only when Stripe's signed `payment_intent.succeeded` reaches
  `/v1/billing/webhooks/stripe`.
- **A cash job in each.** A second job, whose warranty has expired, paid
  by `shop invoice mark-paid`. Both invoices go in one export per target.
- **Stripe answers from Phase 273's fixtures.** No key, no network.
- **The clock** is 2026-10-15 12:00 in New York, so no day or month edge
  moves the walk (F186's edges are not this gate's).

What the gate found is in `docs/phases/*/292_step0.md`: the Xero tax
spread (fixed here), and F188 and F189, pinned below as they are.
"""

from __future__ import annotations

import csv
import inspect
import json
import os
import re
import socket
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.api.deps import get_settings as api_settings
from motodiag.payments import stripe_api
from support import network_guard
from support.frozen_clock import set_zone
from support.phase273 import STRIPE_ENV, cli
from support.stripe_fixtures import (
    SHOP_ACCOUNT, TEST_KEY, TERMINAL_PI, FixtureHTTP, event, freeze_webhook_clock,
    load, signed, stripe_settings,
)

PRODUCTION_DB = (Path(__file__).resolve().parent.parent / "data" / "motodiag.db").resolve()

# --- The clock: a Thursday, midday, mid-month ---

ZONE = "America/New_York"
NOON = datetime(2026, 10, 15, 16, 0, tzinfo=timezone.utc)  # 12:00 EDT
DAY = "2026-10-15"
NOON_TS = int(NOON.timestamp())

# Modules the walk's commands import inside a function, loaded before the
# freeze so the freeze reaches them. The walk's own check (Logic 8) names
# any module that escaped, so this list cannot go stale silently.
PRELOAD = (
    "motodiag.cli.main",
    "motodiag.api",
    "motodiag.advanced.parts_loader",
    "motodiag.advanced.parts_repo",
    "motodiag.vehicles.registry",
    "motodiag.billing.webhook_handlers",
)

_CLOCK_CALL = re.compile(r"\b(?:datetime|date)\.(?:now|today|utcnow)\(")

# --- The two jobs ---

JOB_A = {  # the card job: covered by its warranty, a claim opened
    "customer": ("Dana Rider", "dana@example.com"),
    "bike": ("Honda", "CBR600RR", "2005"),
    "warranty": ("extended", "Honda Protection Plan", "2024-03-01", "2027-02-28", "40000"),
    "mileage": "31200",
    "start": f"{DAY}T09:00", "minutes": "120",
    "problem": "Front brake squeals and pulls left",
    "part": ("brake pads", "honda", "honda-06455-mee-000-brake-pads"),
    "qty": "2", "unit_cost": None, "estimate": "1.0", "hours": "1.5",
}
JOB_B = {  # the cash job: its warranty ended before the visit
    "customer": ("Sam Okafor", "sam@example.com"),
    "bike": ("Yamaha", "YZF-R1", "2005"),
    "warranty": ("extended", "Yamaha Extended Service", "2021-04-01", "2026-03-31", "30000"),
    "mileage": "22400",
    "start": f"{DAY}T13:00", "minutes": "60",
    "problem": "Front caliper sticking",
    "part": ("caliper", "yamaha", "all-balls-18-3019-brake-caliper-kit"),
    "qty": "1", "unit_cost": "3150", "estimate": "1.0", "hours": "1.25",
}

# The cents, worked by hand from the jobs above and Massachusetts' rules
# (parts taxable at 6.25%, labour not), at 12000 cents an hour.
KNOWN = {
    "A": {"labor": 18000, "parts": 9998, "subtotal": 27998, "tax": 625, "total": 28623},
    "B": {"labor": 15000, "parts": 3150, "subtotal": 18150, "tax": 197, "total": 18347},
}
LABOUR_RATE_CENTS = 12000

CONNECT = [("POST", r"/v2/core/accounts", "v2_account_created"),
           ("POST", r"/v2/core/account_links", "v2_account_link")]
STATUS = [("GET", rf"/v2/core/accounts/{SHOP_ACCOUNT}", "v2_account_active")]
SHOP_NAME = "Harbor Moto Works"
# Stripe returns the reader with the label it was sent. The recorded reader
# carries the smoke run's shop name, so it is answered with this shop's.
READER_LABEL = f"{SHOP_NAME} simulated reader"
TERMINAL_SETUP = [("POST", r"/v1/terminal/locations", "terminal_location"),
                  ("POST", r"/v1/terminal/readers",
                   (200, {**load("terminal_reader")["body"], "label": READER_LABEL}))]
PAY = {
    "checkout": [("POST", r"/v1/checkout/sessions", "checkout_session_invoice")],
    "terminal": [("POST", r"/v1/payment_intents", "payment_intent_card_present"),
                 ("POST", r".*/process_payment_intent", "reader_processing"),
                 ("POST", r".*/present_payment_method", "reader_presented")],
}
CHECKOUT_PI = "pi_gate16_checkout"

BUILD_REFERENCES = (
    r"\bPhase \d+\b",
    r"\bTrack [A-Z]\b",
    r"this phase",
    r"\bF\d{2,3}\b",
)


# --- Helpers ---


def _cents(dollars) -> int:
    return int(round(float(dollars) * 100))


def _half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), ROUND_HALF_UP))


def _rows(db: str, query: str, params=()) -> list[dict]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def _one(db: str, query: str, params=()) -> dict:
    rows = _rows(db, query, params)
    assert len(rows) == 1, (query, rows)
    return rows[0]


def _printed_id(output: str, pattern: str) -> int:
    m = re.search(pattern, output)
    assert m, f"no id matching {pattern!r} in:\n{output}"
    return int(m.group(1))


def build_references(outputs: list[str]) -> list[str]:
    text = " ".join(" ".join(o.split()) for o in outputs)
    return [m.group() for pattern in BUILD_REFERENCES
            for m in re.finditer(pattern, text, re.IGNORECASE)]


def _frozen_classes():
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return NOON.astimezone().replace(tzinfo=None)
            return NOON.astimezone(tz)

        @classmethod
        def utcnow(cls):
            return NOON.replace(tzinfo=None)

        @classmethod
        def today(cls):
            return cls.now()

    class FrozenDate(date):
        @classmethod
        def today(cls):
            return NOON.astimezone().date()

    return FrozenDatetime, FrozenDate


@contextmanager
def frozen_clock(mp: pytest.MonkeyPatch):
    """Every loaded ``motodiag`` module's ``datetime`` and ``date`` read NOON,
    in New York; so does the Stripe SDK's signature clock. Yields the ids of
    the modules frozen."""
    previous_zone = os.environ.get("TZ")
    for name in PRELOAD:
        __import__(name)
    set_zone(ZONE)
    frozen_dt, frozen_date = _frozen_classes()
    frozen: set[int] = set()
    try:
        for name, mod in list(sys.modules.items()):
            if not name.startswith("motodiag") or mod is None:
                continue
            if getattr(mod, "datetime", None) is datetime:
                mp.setattr(mod, "datetime", frozen_dt)
                frozen.add(id(mod))
            if getattr(mod, "date", None) is date:
                mp.setattr(mod, "date", frozen_date)
                frozen.add(id(mod))
        freeze_webhook_clock(mp, at=NOON_TS)
        yield frozen
    finally:
        set_zone(previous_zone)


def escaped_the_freeze(frozen: set[int]) -> list[str]:
    """``motodiag`` modules loaded during the walk that hold the real clock
    and call it."""
    escaped = []
    for name, mod in list(sys.modules.items()):
        if not name.startswith("motodiag") or mod is None or id(mod) in frozen:
            continue
        if getattr(mod, "datetime", None) is datetime or getattr(mod, "date", None) is date:
            try:
                source = inspect.getsource(mod)
            except (OSError, TypeError):
                continue
            if _CLOCK_CALL.search(source):
                escaped.append(name)
    return sorted(escaped)


# --- The walk ---


class Walker:
    """Runs commands against one database and keeps what each printed, and
    every Stripe request."""

    def __init__(self, db: str, mp: pytest.MonkeyPatch):
        self.db = db
        self.mp = mp
        self.steps: list[dict] = []
        self.requests: list = []
        self.unanswered: list = []
        self.job: str | None = None

    def run(self, label: str, *args, stripe=None, expect: int | None = 0) -> str:
        http = FixtureHTTP(list(stripe or []))
        self.mp.setattr(stripe_api, "_test_http_client", http)
        out = cli(self.db, *args)
        self.requests.extend((label, r) for r in http.requests)
        self.unanswered.extend((label, e) for e in http.expected)
        self.steps.append({"label": label, "job": self.job, "argv": [str(a) for a in args],
                           "exit": out.exit_code, "output": out.output})
        if expect is not None:
            assert out.exit_code == expect, (
                f"{label}: motodiag {' '.join(map(str, args))} exited "
                f"{out.exit_code}\n{out.output}\n{out.exception!r}")
        return out.output

    def outputs(self) -> list[str]:
        return [s["output"] for s in self.steps]


def _set_up_shop(w: Walker, rec: dict) -> None:
    out = w.run("shop", "shop", "profile", "init", "--name", SHOP_NAME,
                "--address", "12 Wharf Street", "--city", "Boston", "--state", "MA",
                "--zip", "02110", "--phone", "617-555-0142",
                "--hours", json.dumps({d: "08:00-17:00" for d in
                                       ("mon", "tue", "wed", "thu", "fri")}))
    rec["shop"] = shop = _printed_id(out, r"Registered shop id=(\d+)")
    w.run("mechanic", "shop", "member", "add", "--shop", shop, "--user", 1, "--role", "tech")
    w.run("tax", "shop", "tax", "jurisdiction", "set", "--shop", shop, "--code", "US-MA")
    rec["tax_status"] = json.loads(
        w.run("tax status", "shop", "tax", "status", "--shop", shop, "--json"))
    w.run("labour rate", "shop", "labor-rate", "set", "--hourly-cents", LABOUR_RATE_CENTS,
          "--state", "MA", "--source", "Shop's posted rate")
    rates = json.loads(w.run("labour rates", "shop", "labor-rate", "list", "--json"))
    rec["labour_rate_cents"] = _cents(next(r["hourly_rate"] for r in rates
                                           if r["state"] == "MA"))
    w.run("parts catalogue", "advanced", "parts", "seed", "--yes")
    w.run("stripe account", "shop", "payments", "connect", "--shop", shop, "--email",
          "owner@harbormoto.example", stripe=CONNECT)
    w.run("stripe status", "shop", "payments", "status", "--shop", shop, stripe=STATUS)
    w.run("reader", "shop", "terminal", "setup", "--shop", shop, "--simulated",
          stripe=TERMINAL_SETUP)
    for kind, account in (("receivable", "Accounts Receivable (A/R)"),
                          ("labor", "Labor Income"), ("parts", "Parts Sales"),
                          ("tax", "Sales Tax Payable")):
        w.run("qbo map", "shop", "accounting", "map", "set", "--shop", shop, "--target",
              "quickbooks-online", "--kind", kind, "--account", account)
    for kind, code, tax_type in (("labor", "200", "Tax Exempt"),
                                 ("parts", "210", "Tax on Sales (6.25%)")):
        w.run("xero map", "shop", "accounting", "map", "set", "--shop", shop, "--target",
              "xero", "--kind", kind, "--account", code, "--tax-type", tax_type)


def _walk_job(w: Walker, rec: dict, key: str, job: dict) -> dict:
    """One job, book → repair → invoice, in the row's order. Returns its ids
    and what each step left behind."""
    shop = rec["shop"]
    j: dict = {"key": key}
    name, email = job["customer"]
    out = w.run("customer", "shop", "customer", "add", "--name", name, "--email", email,
                "--shop-id", shop)
    j["customer"] = cust = _printed_id(out, r"Added customer id=(\d+)")
    make, model, year = job["bike"]
    out = w.run("bike", "garage", "add", "--make", make, "--model", model, "--year", year,
                "--powertrain", "ice", "--engine-type", "four_stroke")
    j["bike"] = bike = _printed_id(out, r"Added vehicle #(\d+)")
    w.run("owner", "shop", "customer", "link-bike", cust, "--bike", bike)
    coverage, provider, start, end, limit = job["warranty"]
    out = w.run("coverage", "shop", "warranty", "add", "--bike", bike, "--coverage",
                coverage, "--provider", provider, "--start", start, "--end", end,
                "--mileage-limit", limit)
    j["warranty"] = _printed_id(out, r"Recorded warranty #(\d+)")

    # Customer books: staff book it for them (self-booking is row 363).
    slot = job["start"][-5:]
    j["slots"] = w.run("slots", "shop", "appointment", "slots", "--shop", shop,
                       "--date", DAY, "--minutes", job["minutes"])
    out = w.run("book", "shop", "appointment", "book", "--shop", shop, "--customer", cust,
                "--bike", bike, "--start", job["start"], "--minutes", job["minutes"],
                "--mechanic", 1, "--notes", job["problem"])
    j["appointment"] = appt = _printed_id(out, r"Booked appointment #(\d+)")
    j["slot"] = slot
    j["confirmation"] = w.run("confirm", "shop", "appointment", "confirm", appt,
                              "--channel", "phone", "--by", 1)

    # Intake, then the work order from it, then check-in linking that order
    # (the order that holds; F189).
    out = w.run("intake", "shop", "intake", "create", "--shop", shop, "--customer", cust,
                "--bike", bike, "--mileage", job["mileage"], "--notes", job["problem"])
    j["intake"] = intake = _printed_id(out, r"Created intake id=(\d+)")
    out = w.run("work order", "shop", "work-order", "create", "--intake", intake,
                "--title", job["problem"], "--estimated-hours", job["estimate"],
                "--mechanic", 1)
    j["wo"] = wo = _printed_id(out, r"Created work order id=(\d+)")
    w.run("check-in", "shop", "appointment", "check-in", appt, "--wo", wo)

    # Warranty check on the visit's day, at the intake's mileage.
    j["warranty_check"] = json.loads(w.run(
        "warranty check", "shop", "warranty", "check", "--bike", bike, "--on", DAY,
        "--mileage", job["mileage"], "--json"))
    verdicts = {c["warranty_id"]: c["verdict"] for c in j["warranty_check"]["coverage"]}
    if verdicts.get(j["warranty"]) == "valid":
        out = w.run("claim", "shop", "warranty", "claim", "open", "--warranty",
                    j["warranty"], "--wo", wo, "--description",
                    f"{job['problem']}: pads replaced under the extended plan")
        j["claim"] = _printed_id(out, r"Opened claim #(\d+)")

    # Repair.
    w.run("start", "shop", "work-order", "start", wo)
    query, part_make, slug = job["part"]
    found = json.loads(w.run("part search", "advanced", "parts", "search", query,
                             "--make", part_make, "--json"))["parts"]
    j["part"] = part = next(p for p in found if p["slug"] == slug)
    add = ["parts-needs", "add", wo, "--part-id", part["id"], "--qty", job["qty"]]
    if job["unit_cost"]:
        add += ["--unit-cost", job["unit_cost"]]
    out = w.run("part on the order", "shop", *add)
    wop = _printed_id(out, r"Added work_order_part id=(\d+)")
    w.run("ordered", "shop", "parts-needs", "mark-ordered", wop)
    w.run("received", "shop", "parts-needs", "mark-received", wop)
    w.run("complete", "shop", "work-order", "complete", wo, "--actual-hours", job["hours"])
    w.run("appointment done", "shop", "appointment", "complete", appt)
    j["wo_row"] = json.loads(w.run("work order shown", "shop", "work-order", "show", wo,
                                   "--json"))
    j["wo_parts"] = json.loads(w.run("parts shown", "shop", "parts-needs", "list",
                                     "--wo", wo, "--json"))

    # Invoice.
    out = w.run("invoice", "shop", "invoice", "generate", wo)
    j["invoice"] = _printed_id(out, r"Generated invoice id=(\d+)")
    j["invoice_shown"] = json.loads(w.run("invoice shown", "shop", "invoice", "show",
                                          j["invoice"], "--json"))
    return j


def _pay_by_card(w: Walker, rec: dict, j: dict, channel: str, plants: dict) -> None:
    inv = j["invoice"]
    if channel == "checkout":
        j["pay_output"] = w.run("pay-link", "shop", "invoice", "pay-link", inv,
                                stripe=PAY["checkout"])
        asked = w.requests[-1][1].params["line_items[0][price_data][unit_amount]"]
        pi_id = CHECKOUT_PI
    else:
        j["pay_output"] = w.run("reader pay", "shop", "terminal", "pay", inv,
                                stripe=PAY["terminal"])
        asked = next(r for label, r in w.requests
                     if label == "reader pay" and r.path == "/v1/payment_intents").params["amount"]
        pi_id = TERMINAL_PI
    j["stripe_asked_cents"] = int(asked)
    if plants.get("paid_without_event"):
        w.run("PLANT mark-paid", "shop", "invoice", "mark-paid", inv)
    j["before_event"] = {
        "invoice": _one(w.db, "SELECT status, paid_at FROM invoices WHERE id = ?", (inv,)),
        "payment": _one(w.db, "SELECT * FROM invoice_payments WHERE invoice_id = ?", (inv,)),
    }
    pay = j["before_event"]["payment"]
    received = j["stripe_asked_cents"] + plants.get("event_amount_off", 0)
    evt = event("payment_intent.succeeded", {
        "id": pi_id, "object": "payment_intent", "amount": received,
        "amount_received": received, "currency": "usd", "status": "succeeded",
        "metadata": {"motodiag_payment_id": str(pay["id"]),
                     "motodiag_invoice_id": str(inv)},
    }, event_id=f"evt_gate16_{channel}", account=SHOP_ACCOUNT)
    evt["created"] = NOON_TS
    j["event"] = evt
    payload, sig = signed(evt, timestamp=NOON_TS)
    app = create_app(db_path_override=w.db)
    app.dependency_overrides[api_settings] = lambda: stripe_settings(db_path=w.db)
    resp = TestClient(app, raise_server_exceptions=False).post(
        "/v1/billing/webhooks/stripe", content=payload,
        headers={"Stripe-Signature": sig})
    j["webhook"] = (resp.status_code, resp.text)
    j["after_event"] = {
        "invoice": _one(w.db, "SELECT status, paid_at FROM invoices WHERE id = ?", (inv,)),
        "payment": _one(w.db, "SELECT * FROM invoice_payments WHERE invoice_id = ?", (inv,)),
    }
    j["payments_shown"] = w.run("payments shown", "shop", "invoice", "payments", inv)


def _export(w: Walker, rec: dict, out_dir: Path) -> None:
    shop = rec["shop"]
    for target in ("quickbooks-online", "xero"):
        path = out_dir / f"{target}.csv"
        rec[f"export_{target}_output"] = w.run(
            f"export {target}", "shop", "accounting", "export", "--shop", shop,
            "--target", target, "--from", DAY, "--to", DAY, "--out", path)
        with path.open(newline="", encoding="utf-8") as f:
            rec[f"export_{target}"] = list(csv.DictReader(f))
    again = out_dir / "quickbooks-online-again.csv"
    w.run("export again", "shop", "accounting", "export", "--shop", shop, "--target",
          "quickbooks-online", "--from", DAY, "--to", DAY, "--out", again, expect=None)
    rec["export_again"] = w.steps[-1]
    rec["export_again_written"] = again.exists()
    rec["exported_ids"] = {
        t: sorted(r["invoice_id"] for r in _rows(
            w.db, "SELECT aei.invoice_id FROM accounting_export_invoices aei "
                  "JOIN accounting_exports ae ON ae.id = aei.export_id "
                  "WHERE ae.target = ?", (t,)))
        for t in ("quickbooks_online", "xero")}


def walk(tmp: Path, channel: str, plants: dict | None = None) -> dict:
    """The gate's walk: the shop, job A paid by card through `channel`,
    job B paid in cash, and the exports."""
    plants = plants or {}
    db = str(tmp / "gate16.db")
    rec: dict = {"db": db, "channel": channel}
    mp = pytest.MonkeyPatch()
    try:
        from motodiag.core.database import init_db
        init_db(db)
        create_app(db_path_override=db)  # loads the routes' modules before the freeze
        with frozen_clock(mp) as frozen:
            for patch in plants.get("patches", ()):
                patch(mp)
            w = Walker(db, mp)
            _set_up_shop(w, rec)
            w.job = "A"
            rec["A"] = _walk_job(w, rec, "A", JOB_A)
            _pay_by_card(w, rec, rec["A"], channel, plants)
            w.job = "B"
            rec["B"] = _walk_job(w, rec, "B", JOB_B)
            rec["B"]["cash_output"] = w.run("cash", "shop", "invoice", "mark-paid",
                                            rec["B"]["invoice"])
            w.job = None
            _export(w, rec, tmp)
            rec["escaped"] = escaped_the_freeze(frozen)
        rec["steps"], rec["requests"], rec["unanswered"] = w.steps, w.requests, w.unanswered
        rec["invoices"] = {k: _one(db, "SELECT * FROM invoices WHERE id = ?",
                                   (rec[k]["invoice"],)) for k in ("A", "B")}
        rec["lines"] = {k: _rows(db, "SELECT * FROM invoice_line_items WHERE invoice_id = ? "
                                     "ORDER BY sort_order, id", (rec[k]["invoice"],))
                        for k in ("A", "B")}
        rec["network_guarded"] = socket.getaddrinfo is network_guard._guarded_getaddrinfo
    finally:
        mp.undo()
    return rec


def _xero_tax_over_every_line(mp):
    from motodiag.accounting import export as acct_export

    mp.setattr(acct_export, "_line_taxes", lambda inv: acct_export.spread_tax(
        [_cents(line["line_total"]) for line in inv["lines"]], _cents(inv["tax_amount"])))


def _exports_forget_what_they_carried(mp):
    from motodiag.accounting import export as acct_export

    real = acct_export.invoices_in_range

    def every_time(shop_id, from_day, to_day, key, include_exported=False, db_path=None):
        return real(shop_id, from_day, to_day, key, True, db_path=db_path)

    mp.setattr(acct_export, "invoices_in_range", every_time)


def _every_warranty_valid(mp):
    from motodiag.inventory import warranty_repo

    mp.setattr(warranty_repo, "coverage_status", lambda w, on, miles: ("valid", ["planted"]))


# The operator's five planted controls, and F158's. Each walk must turn the
# named check of the gate red; the phase log records each run.
PLANTS = {
    "an invoice marked paid with no event": {"paid_without_event": True},
    "an event whose amount differs from the invoice's total": {"event_amount_off": 1},
    "an expired warranty reported as covered": {"patches": [_every_warranty_valid]},
    "the export's tax line differing from the invoice's tax":
        {"patches": [_xero_tax_over_every_line]},
    "an invoice exported twice to the same target":
        {"patches": [_exports_forget_what_they_carried]},
    "a build reference in what the walk prints":
        {"patches": [lambda mp: mp.setitem(JOB_A, "problem", JOB_A["problem"] + " (F188)")]},
}


@pytest.fixture(scope="module", params=["checkout", "terminal"])
def walked(request, tmp_path_factory):
    return walk(tmp_path_factory.mktemp(f"gate16_{request.param}"), request.param)


# --- 1. The walk ran, in the row's order, on the frozen clock ---


ROW_ORDER = ("book", "intake", "work order", "warranty check", "start", "invoice")


class TestTheWalk:
    def test_every_step_ran_through_a_command(self, walked):
        assert all(s["exit"] == 0 for s in walked["steps"]
                   if s["label"] != "export again"), [
            (s["label"], s["exit"]) for s in walked["steps"] if s["exit"]]
        assert len(walked["steps"]) >= 60

    @pytest.mark.parametrize("k", ["A", "B"])
    def test_each_job_ran_in_the_rows_order(self, walked, k):
        labels = [s["label"] for s in walked["steps"] if s["job"] == k]
        pay = {"A": "pay-link" if walked["channel"] == "checkout" else "reader pay",
               "B": "cash"}[k]
        order = [labels.index(step) for step in (*ROW_ORDER, pay)]
        assert order == sorted(order), labels
        everything = [s["label"] for s in walked["steps"]]
        assert everything.index("export quickbooks-online") > max(
            i for i, s in enumerate(walked["steps"]) if s["job"] in ("A", "B"))

    def test_the_walk_ran_on_the_frozen_day(self, walked):
        for k in ("A", "B"):
            inv = walked["invoices"][k]
            assert inv["issued_at"].startswith(f"{DAY}T16:00:00"), inv["issued_at"]
            assert inv["invoice_number"].endswith(DAY.replace("-", ""))
            assert walked[k]["wo_row"]["completed_at"].startswith(f"{DAY}T12:00")

    def test_no_module_escaped_the_freeze(self, walked):
        assert walked["escaped"] == []

    def test_no_key_and_no_network(self, walked):
        assert walked["network_guarded"]
        assert STRIPE_ENV["MOTODIAG_STRIPE_API_KEY"] == TEST_KEY
        assert walked["requests"], "the walk made no Stripe request"
        assert {r.headers.get("Authorization") for _, r in walked["requests"]} == {
            f"Bearer {TEST_KEY}"}
        assert walked["unanswered"] == []
        assert Path(walked["db"]).resolve() != PRODUCTION_DB

    def test_the_reader_was_registered_with_the_label_it_was_answered_with(self, walked):
        sent = [r for label, r in walked["requests"]
                if label == "reader" and r.path == "/v1/terminal/readers"]
        assert [r.params["label"] for r in sent] == [READER_LABEL]


# --- 2. Each hand-off, checked where it happens ---


class TestTheHandOffs:
    @pytest.mark.parametrize("k", ["A", "B"])
    def test_staff_book_a_free_slot_and_confirm_it(self, walked, k):
        j = walked[k]
        assert j["slot"] in j["slots"]
        appt = _one(walked["db"], "SELECT * FROM appointments WHERE id = ?",
                    (j["appointment"],))
        assert (appt["shop_id"], appt["customer_id"], appt["vehicle_id"]) == (
            walked["shop"], j["customer"], j["bike"])
        assert appt["scheduled_start"].startswith(f"{DAY}T{j['slot']}")
        assert "is confirmed for Thursday 15 October 2026" in j["confirmation"]

    @pytest.mark.parametrize("k", ["A", "B"])
    def test_the_work_order_comes_from_the_intake_and_the_appointment_links_it(self, walked, k):
        j, db = walked[k], walked["db"]
        intake = _one(db, "SELECT * FROM intake_visits WHERE id = ?", (j["intake"],))
        wo = j["wo_row"]
        appt = _one(db, "SELECT * FROM appointments WHERE id = ?", (j["appointment"],))
        assert wo["intake_visit_id"] == j["intake"]
        assert (wo["shop_id"], wo["customer_id"], wo["vehicle_id"]) == (
            intake["shop_id"], intake["customer_id"], intake["vehicle_id"]) == (
            appt["shop_id"], appt["customer_id"], appt["vehicle_id"])
        assert intake["mileage_at_intake"] == int(JOB_A["mileage"] if k == "A"
                                                  else JOB_B["mileage"])
        assert appt["work_order_id"] == j["wo"]
        assert appt["status"] == "completed"

    def test_the_covered_job_is_valid_and_its_claim_is_on_the_work_order(self, walked):
        j = walked["A"]
        cover = {c["warranty_id"]: c for c in j["warranty_check"]["coverage"]}
        assert cover[j["warranty"]]["verdict"] == "valid"
        assert j["warranty_check"]["on"] == DAY
        claim = _one(walked["db"],
                     "SELECT c.*, w.vehicle_id FROM warranty_claims c "
                     "JOIN warranties w ON w.id = c.warranty_id WHERE c.id = ?",
                     (j["claim"],))
        assert (claim["work_order_id"], claim["vehicle_id"], claim["status"]) == (
            j["wo"], j["bike"], "draft")

    def test_the_expired_job_is_not_valid_and_has_no_claim(self, walked):
        j = walked["B"]
        cover = {c["warranty_id"]: c for c in j["warranty_check"]["coverage"]}
        assert cover[j["warranty"]]["verdict"] == "not valid"
        assert any("2026-03-31" in r for r in cover[j["warranty"]]["reasons"])
        assert "claim" not in j
        assert _rows(walked["db"], "SELECT id FROM warranty_claims WHERE work_order_id = ?",
                     (j["wo"],)) == []

    @pytest.mark.parametrize("k", ["A", "B"])
    def test_the_repair_completes_the_work_order_with_its_part_received(self, walked, k):
        j = walked[k]
        assert j["wo_row"]["status"] == "completed"
        assert j["wo_row"]["started_at"] and j["wo_row"]["completed_at"]
        assert [(p["part_id"], p["status"]) for p in j["wo_parts"]] == [
            (j["part"]["id"], "received")]

    @pytest.mark.parametrize("k", ["A", "B"])
    def test_the_invoice_is_issued_for_the_work_order(self, walked, k):
        j, inv = walked[k], walked["invoices"][k]
        assert (inv["work_order_id"], inv["customer_id"]) == (j["wo"], j["customer"])
        assert inv["taxed_line_types"] == "parts"
        assert inv["tax_rate"] == walked["tax_status"]["rate"]["value"]

    def test_the_payment_is_for_the_invoice_on_the_shops_account(self, walked):
        j = walked["A"]
        pay = j["after_event"]["payment"]
        assert (pay["invoice_id"], pay["shop_id"], pay["stripe_account_id"]) == (
            j["invoice"], walked["shop"], SHOP_ACCOUNT)
        assert pay["channel"] == walked["channel"]

    def test_the_export_carries_exactly_the_two_invoices(self, walked):
        ids = sorted(walked[k]["invoice"] for k in ("A", "B"))
        assert walked["exported_ids"] == {"quickbooks_online": ids, "xero": ids}
        numbers = {walked["invoices"][k]["invoice_number"] for k in ("A", "B")}
        for target in ("quickbooks-online", "xero"):
            assert "Wrote 2 invoice(s)" in walked[f"export_{target}_output"]
        assert {r["Journal No."] for r in walked["export_quickbooks-online"]} == numbers
        assert {r["InvoiceNumber"] for r in walked["export_xero"]} == numbers

    def test_an_invoice_is_exported_once_per_target(self, walked):
        again = walked["export_again"]
        assert again["exit"] == 1, again["output"]
        assert "were exported before" in again["output"]
        assert not walked["export_again_written"]


# --- 3. The money, in integer cents, link by link ---


def _work_order_cents(walked, k) -> dict:
    j = walked[k]
    labour = _half_up(Decimal(str(j["wo_row"]["actual_hours"]))
                      * walked["labour_rate_cents"])
    parts = sum(p["quantity"] * p["unit_cost_cents"] for p in j["wo_parts"])
    assert parts == sum(p["line_subtotal_cents"] for p in j["wo_parts"])
    return {"labor": labour, "parts": parts}


def _invoice_cents(walked, k) -> dict:
    by_type: dict = {}
    for line in walked["lines"][k]:
        by_type[line["item_type"]] = by_type.get(line["item_type"], 0) + _cents(
            line["line_total"])
    inv = walked["invoices"][k]
    return {**by_type, "subtotal": _cents(inv["subtotal"]), "tax": _cents(inv["tax_amount"]),
            "total": _cents(inv["total"])}


class TestTheMoney:
    @pytest.mark.parametrize("k", ["A", "B"])
    def test_the_work_order_gives_the_invoices_lines(self, walked, k):
        assert walked["labour_rate_cents"] == LABOUR_RATE_CENTS
        wo, inv = _work_order_cents(walked, k), _invoice_cents(walked, k)
        assert (inv["labor"], inv["parts"]) == (wo["labor"], wo["parts"])
        assert (wo["labor"], wo["parts"]) == (KNOWN[k]["labor"], KNOWN[k]["parts"])

    @pytest.mark.parametrize("k", ["A", "B"])
    def test_the_invoice_adds_up_and_taxes_only_what_the_rules_tax(self, walked, k):
        inv = _invoice_cents(walked, k)
        status = walked["tax_status"]
        taxable = sum(inv[t] for t in ("labor", "parts")
                      if status["rules"][t]["value"])
        assert inv["subtotal"] == inv["labor"] + inv["parts"]
        assert inv["tax"] == _half_up(Decimal(taxable) * Decimal(str(status["rate"]["value"])))
        assert inv["total"] == inv["subtotal"] + inv["tax"]
        assert {key: inv[key] for key in KNOWN[k]} == KNOWN[k]

    def test_the_card_payment_is_the_invoice_total(self, walked):
        j, total = walked["A"], _invoice_cents(walked, "A")["total"]
        assert j["stripe_asked_cents"] == total
        assert j["before_event"]["payment"]["amount_cents"] == total
        assert j["event"]["data"]["object"]["amount_received"] == total
        assert f"{total / 100:.2f} USD" in j["pay_output"]

    @pytest.mark.parametrize("k", ["A", "B"])
    def test_quickbooks_carries_the_invoice_line_by_line(self, walked, k):
        inv, number = _invoice_cents(walked, k), walked["invoices"][k]["invoice_number"]
        rows = [r for r in walked["export_quickbooks-online"] if r["Journal No."] == number]
        by_account = {r["Account Name"]: (r["Debits"], r["Credits"]) for r in rows}
        money = lambda c: f"{c // 100}.{c % 100:02d}"  # noqa: E731
        assert by_account == {
            "Accounts Receivable (A/R)": (money(inv["total"]), ""),
            "Labor Income": ("", money(inv["labor"])),
            "Parts Sales": ("", money(inv["parts"])),
            "Sales Tax Payable": ("", money(inv["tax"])),
        }

    @pytest.mark.parametrize("k", ["A", "B"])
    def test_xero_carries_each_line_and_the_tax_on_the_taxed_lines_only(self, walked, k):
        inv, number = _invoice_cents(walked, k), walked["invoices"][k]["invoice_number"]
        rows = [r for r in walked["export_xero"] if r["InvoiceNumber"] == number]
        status = walked["tax_status"]
        got = {}
        for r in rows:
            kind = "labor" if r["AccountCode"] == "200" else "parts"
            amount = _half_up(Decimal(r["Quantity"]) * Decimal(r["UnitAmount"]) * 100)
            got[kind] = (amount, _cents(r["TaxAmount"]))
        want_tax = {t: (inv["tax"] if status["rules"][t]["value"] else 0)
                    for t in ("labor", "parts")}
        assert got == {t: (inv[t], want_tax[t]) for t in ("labor", "parts")}
        assert sum(tax for _, tax in got.values()) == inv["tax"]


# --- 4. Paid only through the webhook ---


class TestPaidOnlyThroughTheWebhook:
    def test_starting_the_payment_does_not_pay_the_invoice(self, walked):
        j = walked["A"]
        assert "The invoice is not paid yet" in j["pay_output"]
        assert j["before_event"]["invoice"] == {"status": "sent", "paid_at": None}
        assert j["before_event"]["payment"]["status"] == "started"

    def test_the_signed_event_pays_it(self, walked):
        j = walked["A"]
        assert j["webhook"][0] == 200, j["webhook"][1]
        assert j["after_event"]["invoice"] == {
            "status": "paid", "paid_at": "2026-10-15T16:00:00.000+00:00"}
        pay = j["after_event"]["payment"]
        assert (pay["status"], pay["outcome"], pay["outcome_reason"]) == (
            "succeeded", "paid_invoice", None)
        assert "paid_invoice" in j["payments_shown"]

    def test_the_event_was_recorded_once_from_the_shops_account(self, walked):
        rows = _rows(walked["db"], "SELECT event_id, account, livemode, error "
                                   "FROM stripe_webhook_events")
        assert rows == [{"event_id": f"evt_gate16_{walked['channel']}",
                         "account": SHOP_ACCOUNT, "livemode": 0, "error": None}]

    def test_cash_is_marked_paid_by_hand_and_exported_the_same_way(self, walked):
        j = walked["B"]
        assert walked["invoices"]["B"]["status"] == "paid"
        assert walked["invoices"]["B"]["paid_at"] == "2026-10-15T16:00:00+00:00"
        assert _rows(walked["db"], "SELECT id FROM invoice_payments WHERE invoice_id = ?",
                     (j["invoice"],)) == []
        assert walked["invoices"]["B"]["id"] in walked["exported_ids"]["xero"]


# --- 5. What the walk prints names no phase, track or finding (F158) ---


class TestNoBuildReferences:
    def test_the_walk_prints_none(self, walked):
        outputs = [s["output"] for s in walked["steps"]]
        assert sum(len(o) for o in outputs) > 10000
        assert build_references(outputs) == []

    def test_a_planted_reference_is_caught(self):
        assert build_references(["Front brake squeals (see F188)"]) == ["F188"]

    def test_a_motorcycle_model_is_not_a_finding(self):
        assert build_references(["the BMW F800R rider's manual, below 95 °F"]) == []


# --- 6. F188 and F189, pinned as they are today ---


class TestWhatTheGateFound:
    def test_f188_covered_work_is_invoiced_to_the_customer_in_full(self, walked):
        """Passes today, and fails the day row 373 lets a claim reach the
        invoice: then invert it."""
        j = walked["A"]
        claim = _one(walked["db"], "SELECT * FROM warranty_claims WHERE id = ?",
                     (j["claim"],))
        assert claim["amount_claimed_cents"] is None
        assert _invoice_cents(walked, "A")["total"] == KNOWN["A"]["total"]
        assert walked["invoices"]["A"]["status"] == "paid"

    def test_f189_check_in_without_a_work_order_opens_one_with_no_intake(self, tmp_path):
        """Passes today, and fails the day row 374 gives check-in the intake."""
        db = str(tmp_path / "f189.db")
        from motodiag.core.database import init_db
        init_db(db)

        def run(*args):
            out = cli(db, *args)
            assert out.exit_code == 0, out.output
            return out.output

        shop = _printed_id(run("shop", "profile", "init", "--name", "Check-in Shop"),
                           r"Registered shop id=(\d+)")
        cust = _printed_id(run("shop", "customer", "add", "--name", "Dana Rider",
                               "--shop-id", shop), r"Added customer id=(\d+)")
        bike = _printed_id(run("garage", "add", "--make", "Honda", "--model", "CBR600RR",
                               "--year", "2005", "--powertrain", "ice", "--engine-type",
                               "four_stroke"), r"Added vehicle #(\d+)")
        run("shop", "customer", "link-bike", cust, "--bike", bike)
        appt = _printed_id(run("shop", "appointment", "book", "--shop", shop, "--customer",
                               cust, "--bike", bike, "--start", f"{DAY}T09:00",
                               "--minutes", "60"), r"Booked appointment #(\d+)")
        run("shop", "intake", "create", "--shop", shop, "--customer", cust, "--bike", bike,
            "--mileage", "31200")
        out = run("shop", "appointment", "check-in", appt)
        wo = _printed_id(out, r"work order #(\d+) opened")
        assert _one(db, "SELECT intake_visit_id FROM work_orders WHERE id = ?",
                    (wo,))["intake_visit_id"] is None
        assert "--intake" not in run("shop", "appointment", "check-in", "--help")


# --- 7. The planted controls stay proven ---

# Each plant, walked on its own database, turns the gate's own check red.
CAUGHT_BY = {
    "an invoice marked paid with no event": lambda r: (
        TestPaidOnlyThroughTheWebhook().test_starting_the_payment_does_not_pay_the_invoice(r)),
    "an event whose amount differs from the invoice's total": lambda r: (
        TestPaidOnlyThroughTheWebhook().test_the_signed_event_pays_it(r)),
    "an expired warranty reported as covered": lambda r: (
        TestTheHandOffs().test_the_expired_job_is_not_valid_and_has_no_claim(r)),
    "the export's tax line differing from the invoice's tax": lambda r: (
        TestTheMoney().test_xero_carries_each_line_and_the_tax_on_the_taxed_lines_only(r, "A")),
    "an invoice exported twice to the same target": lambda r: (
        TestTheHandOffs().test_an_invoice_is_exported_once_per_target(r)),
    "a build reference in what the walk prints": lambda r: (
        TestNoBuildReferences().test_the_walk_prints_none(r)),
}


class TestThePlantsTurnTheGateRed:
    def test_every_plant_has_its_check(self):
        assert set(CAUGHT_BY) == set(PLANTS)

    @pytest.mark.parametrize("plant", list(PLANTS))
    def test_the_plant_is_caught(self, tmp_path, plant):
        planted = walk(tmp_path, "checkout", PLANTS[plant])
        with pytest.raises(AssertionError):
            CAUGHT_BY[plant](planted)
