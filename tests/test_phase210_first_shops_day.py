"""Phase 210: the first shop's working day, end to end, through the API.

One fresh database at the code's schema, the terms switch on as it will be
at launch, and the billing provider ``stripe`` throughout (the payment
routes and the feed refuse any other), with the stand-in Stripe answering
from the recorded fixtures under ``tests/fixtures/phase273/``. No step
reaches a network or a model: the network guard's refusals are recorded,
and the last test asserts there were none.

The day is one ordered story. The module-scoped ``day`` fixture runs every
step in order, inside one ``MonkeyPatch`` context that is undone before the
first test reads anything, and records each step's outcome. Each test names
one step: it passes when the step passed, re-raises the step's own failure,
or says at which earlier step the shop's day stopped. Under ``-n auto`` a
worker that has not seen the day builds it from the start; the last test
builds it a second time and holds the ids equal.
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import pytest
import support.network_guard as network_guard
from click.testing import CliRunner
from fastapi.testclient import TestClient
from support.phase273 import STRIPE_ENV, answer
from support.phase293 import pdf_bytes, stub_scanner, use_path
from support.phase303 import auth, login, make_shop, make_sub, make_user, new_db, sql
from support.phase345 import FAKE_VALUES, MemoryStore, cheap_crypto
from support.phase371 import ask, succeeded
from support.stripe_fixtures import (
    FROZEN_AT,
    SHOP_ACCOUNT,
    body,
    event,
    freeze_webhook_clock,
    signed,
)

from motodiag.advanced.parts_repo import add_part
from motodiag.api.app import create_app
from motodiag.auth.terms_acceptance import TERMS_DATE, TERMS_VERSION, record_acceptance
from motodiag.backup.restore import _rows, list_snapshots, restore
from motodiag.backup.settings import BackupSettings
from motodiag.backup.snapshot import take_snapshot
from motodiag.cli.main import cli as main_cli
from motodiag.cli.theme import reset_console
from motodiag.core.config import reset_settings
from motodiag.payments import event_feed

OWNER, OWNER_PW = "tess", "ownerpass1"
MECHANIC, MECHANIC_PW = "mo", "techpass12"
SECOND_MECHANIC, SECOND_MECHANIC_PW = "sam", "techpass13"
REVIEWER = "mekno_reviewer"
SHOP_NAME = "Bandit Hero Cycles"

#: 330's wizard on a fresh database, every step taken: the shop (step 1 runs
#: because there is no shop), the owner's login, two mechanics as ``tech``,
#: the owner accepting the terms at the keyboard, and one bike by hand for
#: one customer; then no walkthrough.
WIZARD_INPUT = (
    f"y\n{SHOP_NAME}\n\nAustin\nTX\n\n\n\n"
    f"y\n{OWNER}\nTess Ramirez\n\n{OWNER_PW}\n{OWNER_PW}\n"
    "y\n"
    f"y\n{MECHANIC}\nMo Diaz\n\ntech\n{MECHANIC_PW}\n{MECHANIC_PW}\n"
    f"y\n{SECOND_MECHANIC}\nSam Lee\n\ntech\n{SECOND_MECHANIC_PW}\n{SECOND_MECHANIC_PW}\n"
    "n\n"
    f"y\n{OWNER}\ny\n"
    "y\nn\ny\nHonda\nCBR600RR\n2009\n\nice\nMarcus Webb\n512-555-0188\n"
    "n\n"
)
ONBOARD_STEPS = ("shop", "owner", "staff", "terms", "bikes")

LABOUR_CENTS = 9500
PART_CENTS = 4500
TAX_PERCENT = 8.25

CHECKOUT_SUB = ("POST", r"/v1/checkout/sessions", "checkout_session_subscription")
CHECKOUT_INVOICE = ("POST", r"/v1/checkout/sessions", "checkout_session_invoice")
CREATE = ("POST", r"/v2/core/accounts", "v2_account_created")
LINK = ("POST", r"/v2/core/account_links", "v2_account_link")
READ_ACTIVE = ("GET", rf"/v2/core/accounts/{SHOP_ACCOUNT}", "v2_account_active")


# ---------------------------------------------------------------- the day's state
@dataclass
class Day:
    folder: Path
    mp: Any = None
    db: str = ""
    c: Optional[TestClient] = None
    ids: dict[str, int] = field(default_factory=dict)
    tokens: dict[str, str] = field(default_factory=dict)
    #: Every write to the shop's routes by the owner or the mechanic:
    #: (method, path, username, status), for the audit step.
    writes: list[tuple[str, str, str, int]] = field(default_factory=list)
    refused_hosts: list[str] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    failed: dict[str, BaseException] = field(default_factory=dict)
    invoice: dict = field(default_factory=dict)
    pdf: bytes = b""
    rows_at_backup: dict[str, int] = field(default_factory=dict)

    @property
    def shop(self) -> int:
        return self.ids["shop"]

    def call(self, who: Optional[str], method: str, path: str, *,
             expect: Optional[int] = None, **kw):
        headers = {**(auth(self.tokens[who]) if who else {}), **kw.pop("headers", {})}
        assert self.c is not None
        r = self.c.request(method, path, headers=headers, **kw)
        if (method != "GET" and who in (OWNER, MECHANIC)
                and path.startswith(f"/v1/shop/{self.ids.get('shop')}/")):
            self.writes.append((method, path, who, r.status_code))
        if expect is not None:
            assert r.status_code == expect, f"{method} {path}: {r.status_code} {r.text}"
        return r

    def cli(self, *args, input: Optional[str] = None):
        reset_console()
        out = CliRunner().invoke(main_cli, [str(a) for a in args], input=input)
        assert out.exit_code == 0, f"motodiag {' '.join(map(str, args))}:\n{out.output}"
        return out

    def scalar(self, query: str, params: tuple = ()):
        return sql(self.db, query, params)[0][0]


def _problem(r) -> str:
    return r.json()["type"].rsplit("/", 1)[-1]


# ---------------------------------------------------------------- the steps
def the_shop_made_with_the_wizard(d: Day) -> None:
    out = d.cli("shop", "onboard", "run", input=WIZARD_INPUT)
    assert "Registered shop id=" in out.output
    assert f"Recorded: {OWNER} accepted version {TERMS_VERSION}." in out.output
    assert OWNER_PW not in out.output and MECHANIC_PW not in out.output
    [status] = json.loads(d.cli("shop", "onboard", "status", "--json").output)
    assert status["shop_name"] == SHOP_NAME
    assert {k: status[k]["status"] for k in ONBOARD_STEPS} == dict.fromkeys(ONBOARD_STEPS, "done")
    d.ids["shop"] = int(status["shop_id"])
    for name in (OWNER, MECHANIC, SECOND_MECHANIC):
        d.ids[name] = d.scalar("SELECT id FROM users WHERE username = ?", (name,))
    roles = sql(d.db, "SELECT u.username, m.role FROM shop_members m JOIN users u "
                      "ON u.id = m.user_id WHERE m.shop_id = ? ORDER BY u.username", (d.shop,))
    assert roles == [(MECHANIC, "tech"), (SECOND_MECHANIC, "tech"), (OWNER, "owner")]
    assert sql(d.db, "SELECT user_id, version FROM terms_acceptances") == [
        (d.ids[OWNER], TERMS_VERSION)]
    [(customer, bike)] = sql(d.db, "SELECT c.id, cb.vehicle_id FROM customers c JOIN "
                                   "customer_bikes cb ON cb.customer_id = c.id "
                                   "WHERE c.name = 'Marcus Webb' AND c.shop_id = ?", (d.shop,))
    d.ids["customer1"], d.ids["bike1"] = customer, bike
    # The wizard writes no plan: every shop route answers 402 until one is on record.
    assert d.scalar("SELECT COUNT(*) FROM subscriptions") == 0


def the_shop_plan_before_the_first_shop_route(d: Day) -> None:
    d.tokens[OWNER] = login(d.c, OWNER, OWNER_PW)
    d.ids["riley"] = make_user(d.db, "riley", None)
    fourth = {"user_id": d.ids["riley"], "role": "service_writer"}
    r = d.call(OWNER, "POST", f"/v1/shop/{d.shop}/members", json=fourth, expect=402)
    assert _problem(r) == "subscription-required"

    http = answer(d.mp, [CHECKOUT_SUB])
    r = d.call(OWNER, "POST", "/v1/billing/checkout-session", json={"tier": "shop"}, expect=200)
    assert r.json()["checkout_url"].startswith("https://checkout.stripe.com/")
    asked = http.requests[0].params
    assert asked["subscription_data[metadata][user_id]"] == str(d.ids[OWNER])
    assert asked["subscription_data[metadata][tier]"] == "shop"
    assert asked["line_items[0][price]"] == "price_test_shop"

    sub = body("subscription_active")
    sub["metadata"]["user_id"] = str(d.ids[OWNER])
    reread = answer(d.mp, [("GET", rf"/v1/subscriptions/{sub['id']}", (200, sub))])
    evt = event("customer.subscription.created", {
        "id": sub["id"], "object": "subscription", "status": "active",
        "customer": sub["customer"],
        "metadata": {"user_id": str(d.ids[OWNER]), "tier": "shop"},
    }, event_id="evt_210_the_shop_plan")
    payload, signature = signed(evt)
    r = d.call(None, "POST", "/v1/billing/webhooks/stripe", content=payload,
               headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
               expect=200)
    assert r.json()["processed"] is True
    assert [q.path for q in reread.requests] == [f"/v1/subscriptions/{sub['id']}"]
    r = d.call(OWNER, "GET", "/v1/billing/subscription", expect=200)
    assert (r.json()["tier"], r.json()["status"]) == ("shop", "active")

    r = d.call(OWNER, "POST", f"/v1/shop/{d.shop}/members", json=fourth, expect=201)
    assert r.json() == {"shop_id": d.shop, **fourth}
    r = d.call(OWNER, "GET", f"/v1/shop/{d.shop}/members", expect=200)
    assert r.json()["total"] == 4


def signing_in(d: Day) -> None:
    sessions = d.scalar("SELECT COUNT(*) FROM api_keys")
    r = d.call(None, "POST", "/v1/auth/login",
               json={"username": MECHANIC, "password": "not the password"}, expect=401)
    assert _problem(r) == "login-failed" and "token" not in r.json()
    assert d.scalar("SELECT COUNT(*) FROM api_keys") == sessions
    d.tokens[MECHANIC] = login(d.c, MECHANIC, MECHANIC_PW)
    for who, role in ((OWNER, "owner"), (MECHANIC, "tech")):
        me = d.call(who, "GET", "/v1/auth/me", expect=200).json()
        assert me["user"]["username"] == who
        assert [(m["shop_id"], m["shop_name"], m["role"]) for m in me["memberships"]] == [
            (d.shop, SHOP_NAME, role)]


def the_terms(d: Day) -> None:
    orders = f"/v1/shop/{d.shop}/work-orders"
    r = d.call(MECHANIC, "GET", orders, expect=403)
    assert _problem(r) == "terms-not-accepted"
    terms = d.call(MECHANIC, "GET", "/v1/terms", expect=200).json()
    assert (terms["version"], terms["date"], terms["accepted"]) == (
        TERMS_VERSION, TERMS_DATE, False)
    assert terms["version"] == "1.1" and terms["date"] == "2026-11-23"
    d.call(MECHANIC, "GET", "/v1/auth/me", expect=200)
    second = login(d.c, MECHANIC, MECHANIC_PW)
    assert d.c.post("/v1/auth/logout", headers=auth(second)).status_code == 204
    r = d.call(MECHANIC, "POST", "/v1/terms/accept", json={"version": "1.0"}, expect=422)
    assert _problem(r) == "terms-version-stale"
    assert _problem(d.call(MECHANIC, "GET", orders, expect=403)) == "terms-not-accepted"
    r = d.call(MECHANIC, "POST", "/v1/terms/accept", json={"version": TERMS_VERSION},
               expect=200)
    assert r.json()["version"] == TERMS_VERSION
    assert d.call(MECHANIC, "GET", "/v1/terms", expect=200).json()["accepted"] is True
    # The owner accepted at the wizard: the same table, 330 and 334 agreeing.
    d.call(OWNER, "GET", orders, expect=200)


def each_limited_to_their_role(d: Day) -> None:
    d.ids["jordan"] = make_user(d.db, "jordan", None)
    r = d.call(MECHANIC, "POST", f"/v1/shop/{d.shop}/members",
               json={"user_id": d.ids["jordan"], "role": "tech"}, expect=403)
    assert _problem(r) == "permission-denied"
    assert d.scalar("SELECT COUNT(*) FROM shop_members WHERE user_id = ?",
                    (d.ids["jordan"],)) == 0
    # Admitted through the owner's plan: the mechanic has none of their own.
    r = d.call(MECHANIC, "GET", f"/v1/shop/{d.shop}/work-orders", expect=200)
    assert r.json()["items"] == []
    assert d.scalar("SELECT COUNT(*) FROM subscriptions WHERE user_id = ?",
                    (d.ids[MECHANIC],)) == 0


def a_customer_and_a_bike(d: Day) -> None:
    r = d.call(OWNER, "POST", f"/v1/shop/{d.shop}/customers",
               json={"name": "Dana Cole", "phone": "512-555-0199"}, expect=201)
    assert (r.json()["name"], r.json()["shop_id"]) == ("Dana Cole", d.shop)
    d.ids["customer2"] = r.json()["id"]
    # Another shop's member, on a Shop plan of their own, is refused.
    stranger = make_user(d.db, "stranger")
    make_sub(d.db, stranger)
    d.ids["other_shop"] = make_shop(d.db, "Another Shop", stranger)
    record_acceptance(stranger, TERMS_VERSION, d.db)
    d.tokens["stranger"] = login(d.c, "stranger")
    d.call("stranger", "POST", f"/v1/shop/{d.shop}/customers", json={"name": "Not yours"},
           expect=403)
    r = d.call(OWNER, "POST", "/v1/vehicles", expect=201, json={
        "make": "Yamaha", "model": "MT-07", "year": 2021, "powertrain": "ice"})
    assert (r.json()["make"], r.json()["model"]) == ("Yamaha", "MT-07")
    d.ids["bike2"] = r.json()["id"]
    r = d.call(OWNER, "POST", f"/v1/shop/{d.shop}/intakes", expect=201, json={
        "customer_id": d.ids["customer2"], "vehicle_id": d.ids["bike2"],
        "reported_problems": "Misfires under load", "mileage_at_intake": 8120})
    assert (r.json()["customer_id"], r.json()["vehicle_id"]) == (
        d.ids["customer2"], d.ids["bike2"])
    d.ids["intake"] = r.json()["id"]
    names = [c["name"] for c in d.call(OWNER, "GET", f"/v1/shop/{d.shop}/customers",
                                       expect=200).json()["items"]]
    assert sorted(names) == ["Dana Cole", "Marcus Webb"]


def a_diagnosis(d: Day) -> None:
    r = d.call(OWNER, "POST", "/v1/sessions", expect=201, json={
        "vehicle_make": "Yamaha", "vehicle_model": "MT-07", "vehicle_year": 2021,
        "vehicle_id": d.ids["bike2"]})
    sid = r.json()["id"]
    d.ids["session"] = sid
    d.call(OWNER, "POST", f"/v1/sessions/{sid}/symptoms",
           json={"symptom": "misfire under load"}, expect=200)
    d.call(OWNER, "POST", f"/v1/sessions/{sid}/fault-codes", json={"code": "P0301"},
           expect=200)
    r = d.call(OWNER, "POST", f"/v1/sessions/{sid}/close", expect=200)
    assert r.json()["status"] == "closed"
    assert "misfire under load" in r.json()["symptoms"]
    assert "P0301" in r.json()["fault_codes"]
    assert d.refused_hosts == []


def a_work_order_with_parts_and_labour(d: Day) -> None:
    base = f"/v1/shop/{d.shop}/work-orders"
    r = d.call(OWNER, "POST", base, expect=201, json={
        "vehicle_id": d.ids["bike2"], "customer_id": d.ids["customer2"],
        "title": "Misfire on cylinder 1; front brake pads", "intake_visit_id": d.ids["intake"]})
    assert r.json()["status"] == "draft"
    wo = r.json()["id"]
    d.ids["wo"] = wo
    r = d.call(OWNER, "POST", f"{base}/{wo}/transition", json={"action": "start"}, expect=409)
    assert _problem(r) == "invalid-transition"
    r = d.call(OWNER, "POST", f"{base}/{wo}/transition", json={"action": "open"}, expect=200)
    assert r.json()["status"] == "open"
    r = d.call(OWNER, "POST", f"{base}/{wo}/assign",
               json={"mechanic_user_id": d.ids[MECHANIC]}, expect=200)
    assert r.json()["assigned_mechanic_user_id"] == d.ids[MECHANIC]
    r = d.call(MECHANIC, "POST", f"{base}/{wo}/transition", json={"action": "start"},
               expect=200)
    assert r.json()["status"] == "in_progress"

    # The part: the catalogue has no route that creates one.
    d.ids["part"] = add_part("ebc-fa252hh", "FA252HH", "EBC", "Sintered front brake pads",
                             "brakes", "yamaha", "MT-07%", typical_cost_cents=PART_CENTS,
                             db_path=d.db)
    parts = f"{base}/{wo}/parts"
    r = d.call(OWNER, "POST", parts, json={"part_id": d.ids["part"], "quantity": 1},
               expect=201)
    assert r.json()["status"] == "open"
    wop = r.json()["id"]
    d.ids["wop"] = wop
    r = d.call(OWNER, "POST", f"{parts}/order", expect=200)
    assert r.json()["ordered"] == 1
    assert [line["status"] for line in r.json()["lines"]] == ["ordered"]
    for action in ("received", "installed"):
        r = d.call(OWNER, "POST", f"{parts}/{wop}/transition", json={"action": action},
                   expect=200)
        assert r.json()["status"] == action
    r = d.call(OWNER, "POST", f"{parts}/{wop}/transition", json={"action": "ordered"},
               expect=409)
    assert _problem(r) == "invalid-transition"

    # The hour: clocked, then corrected through the adjust route.
    r = d.call(MECHANIC, "POST", f"{base}/{wo}/clock-in", expect=201)
    entry = r.json()["entry"]["id"]
    d.ids["time_entry"] = entry
    r = d.call(MECHANIC, "POST", f"{base}/{wo}/clock-out", expect=200)
    assert r.json()["duration_seconds"] == 0
    r = d.call(MECHANIC, "PATCH", f"/v1/shop/{d.shop}/time-entries/{entry}", expect=200,
               json={"started_at": "2026-11-25T09:00:00+00:00",
                     "ended_at": "2026-11-25T10:00:00+00:00"})
    assert r.json()["duration_seconds"] == 3600

    r = d.call(MECHANIC, "POST", f"{base}/{wo}/transition", json={"action": "complete"},
               expect=200)
    assert r.json()["status"] == "completed"
    assert r.json()["actual_hours"] == 1.0


#: The invoice is dated by the real clock (``tax.today()``), so the records
#: span every day this test can run on, and the test reads no clock itself.
TAX_DATES = ["--effective", "2026-01-01", "--valid-until", "2099-12-31",
             "--source-title", "Texas Comptroller, sales tax rate locator",
             "--checked-on", "2026-11-25"]


def an_invoice_at_the_shops_own_tax_rate(d: Day) -> None:
    generate = f"/v1/shop/{d.shop}/invoices/generate"
    wo = {"work_order_id": d.ids["wo"]}
    r = d.call(OWNER, "POST", generate, json=wo, expect=422)
    assert "no labor rate available" in r.json()["detail"]
    d.cli("shop", "labor-rate", "set", "--hourly-cents", LABOUR_CENTS, "--state", "TX")

    r = d.call(OWNER, "POST", generate, json=wo, expect=409)
    assert _problem(r) == "tax-not-on-record"
    assert f"shop {d.shop} has no tax jurisdiction" in r.json()["detail"]
    d.cli("shop", "tax", "jurisdiction", "add", "--code", "US-TX", "--name", "Texas",
          "--currency", "USD")
    d.cli("shop", "tax", "jurisdiction", "set", "--shop", d.shop, "--code", "US-TX")
    d.cli("shop", "tax", "rate", "set", "--shop", d.shop, "--rate", TAX_PERCENT, *TAX_DATES)
    d.cli("shop", "tax", "rule", "set", "--shop", d.shop, "--line-type", "labor",
          "--taxable", *TAX_DATES)
    r = d.call(OWNER, "POST", generate, json=wo, expect=409)
    assert "--line-type parts" in r.json()["detail"]  # the installed part reached the invoice
    assert "--line-type labor" not in r.json()["detail"]
    d.cli("shop", "tax", "rule", "set", "--shop", d.shop, "--line-type", "parts",
          "--taxable", *TAX_DATES)

    r = d.call(OWNER, "POST", generate, json=wo, expect=201)
    inv = r.json()
    d.invoice = inv
    d.ids["invoice"] = inv["id"]
    lines = sorted((i["item_type"], i["quantity"], i["unit_price_cents"], i["line_total_cents"])
                   for i in inv["items"])
    assert lines == [("labor", 1.0, LABOUR_CENTS, LABOUR_CENTS),
                     ("parts", 1.0, PART_CENTS, PART_CENTS)], inv["items"]
    taxable = LABOUR_CENTS + PART_CENTS
    assert (inv["subtotal_cents"], inv["tax_rate"]) == (taxable, TAX_PERCENT / 100)
    assert inv["tax_cents"] == round(taxable * TAX_PERCENT / 100) == 1155
    assert inv["total_cents"] == taxable + inv["tax_cents"] == 15155
    assert (inv["status"], inv["currency"]) == ("sent", "USD")


def paid_by_card_through_the_feed(d: Day) -> None:
    pay = f"/v1/shop/{d.shop}/payments"
    answer(d.mp, [CREATE, LINK])
    r = d.call(OWNER, "POST", f"{pay}/connect", expect=201, json={
        "contact_email": "tess@example.com", "country": "US", "currency": "USD"})
    assert (r.json()["stripe_account_id"], r.json()["card_payments_status"]) == (
        SHOP_ACCOUNT, "restricted")
    answer(d.mp, [READ_ACTIVE])
    r = d.call(OWNER, "GET", f"{pay}/account", params={"refresh": "true"}, expect=200)
    assert (r.json()["card_payments_status"], r.json()["can_take_payments"]) == ("active", True)

    invoice = f"/v1/shop/{d.shop}/invoices/{d.ids['invoice']}/payments"
    answer(d.mp, [])
    r = d.call(MECHANIC, "POST", f"{invoice}/checkout", expect=403)
    assert _problem(r) == "permission-denied"
    answer(d.mp, [CHECKOUT_INVOICE])
    r = d.call(OWNER, "POST", f"{invoice}/checkout", expect=201)
    payment_id = r.json()["payment_id"]
    d.ids["payment"] = payment_id
    cents = d.invoice["total_cents"]
    assert r.json()["amount_cents"] == cents
    before = d.call(OWNER, "GET", invoice, expect=200).json()
    assert [i["status"] for i in before["items"]] == ["started"]
    assert d.scalar("SELECT status FROM invoices WHERE id = ?", (d.ids["invoice"],)) == "sent"

    evt = succeeded(payment_id, d.ids["invoice"], event_id="evt_210_paid")
    evt["data"]["object"]["amount"] = evt["data"]["object"]["amount_received"] = cents
    http = answer(d.mp, [ask(), ask([evt])])
    from motodiag.core.config import get_settings
    results = event_feed.poll_once(get_settings(), d.db, lambda: float(FROZEN_AT + 10))
    assert [(x.account, x.error) for x in results] == [("platform", None), (SHOP_ACCOUNT, None)]
    assert [q.headers.get("Stripe-Account") for q in http.requests] == [None, SHOP_ACCOUNT]
    after = d.call(OWNER, "GET", invoice, expect=200).json()
    assert [(i["status"], i["outcome"]) for i in after["items"]] == [
        ("succeeded", "paid_invoice")]
    assert d.scalar("SELECT status FROM invoices WHERE id = ?", (d.ids["invoice"],)) == "paid"


def a_manual_uploaded_reviewed_and_opened(d: Day) -> None:
    manuals = f"/v1/shop/{d.shop}/manuals"
    meta = json.dumps({"title": "Yamaha MT-07 service manual", "kind": "service_manual",
                       "make": "Yamaha", "model": "MT-07", "year_start": 2018,
                       "year_end": 2024})

    def upload(who: str):
        return d.call(who, "POST", manuals, data={"metadata": meta},
                      files={"file": ("mt07.pdf", d.pdf, "application/pdf")})

    assert upload(MECHANIC).status_code == 403
    r = upload(OWNER)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "pending_review"
    mid = r.json()["id"]
    d.ids["manual"] = mid
    d.call(MECHANIC, "GET", f"{manuals}/{mid}/pages/1", expect=404)

    d.ids[REVIEWER] = make_user(d.db, REVIEWER)
    d.cli("manuals", "reviewer", "grant", REVIEWER)
    d.tokens[REVIEWER] = login(d.c, REVIEWER)
    d.call(REVIEWER, "POST", "/v1/terms/accept", json={"version": TERMS_VERSION}, expect=200)
    queue = d.call(REVIEWER, "GET", "/v1/review/manuals", expect=200).json()
    assert [(m["id"], m["shop_name"], m["uploader_username"]) for m in queue] == [
        (mid, SHOP_NAME, OWNER)]
    r = d.call(REVIEWER, "POST", f"/v1/review/manuals/{mid}/decision",
               json={"decision": "approved"}, expect=200)
    assert r.json()["status"] == "approved"

    r = d.call(MECHANIC, "GET", f"{manuals}/{mid}/pages/1", expect=200)
    assert r.headers["content-type"] == "image/jpeg"
    hits = d.call(MECHANIC, "GET", f"{manuals}/search", params={"q": "caliper"},
                  expect=200).json()
    assert [(h["manual_id"], h["page_number"]) for h in hits] == [(mid, 1)]
    assert "caliper" in hits[0]["snippet"].lower()


def the_plans_limits(d: Day) -> None:
    usage = d.call(OWNER, "GET", f"/v1/shop/{d.shop}/manuals/usage", expect=200).json()
    assert usage["limit_bytes"] == 20 * 1024**3  # the Shop plan's 20 GB, in GiB
    have = d.call(OWNER, "GET", "/v1/vehicles", expect=200).json()["total"]
    for n in range(have, 50):
        d.call(OWNER, "POST", "/v1/vehicles", expect=201,
               json={"make": "Honda", "model": f"Grom {n}", "year": 2022})
    r = d.call(OWNER, "POST", "/v1/vehicles", expect=201,
               json={"make": "Honda", "model": "Grom 51", "year": 2022})
    listed = d.call(OWNER, "GET", "/v1/vehicles", params={"limit": 200}, expect=200).json()
    assert (listed["total"], listed["tier"], listed["quota_limit"]) == (51, "shop", None)
    assert r.json()["model"] == "Grom 51"


def the_audit_log_names_who_did_each_step(d: Day) -> None:
    items = d.call(OWNER, "GET", f"/v1/shop/{d.shop}/audit", params={"limit": 500},
                   expect=200).json()["items"]
    stamps = [i["id"] for i in items]
    assert stamps == sorted(stamps, reverse=True)  # newest first
    logged = {(i["method"], i["path"], i["actor"]["username"], i["status"]) for i in items}
    missing = [w for w in d.writes if w not in logged]
    assert missing == [], missing
    refused = ("POST", f"/v1/shop/{d.shop}/members", MECHANIC, 403)
    assert refused in logged
    assert {w[2] for w in d.writes} == {OWNER, MECHANIC}


def the_nights_backup(d: Day) -> None:
    data_dir = d.folder / "data"
    work = d.folder / "backup_work"
    work.mkdir(mode=0o700)
    store = MemoryStore()
    settings = BackupSettings(d.folder / "backup.env", *FAKE_VALUES.values())
    d.rows_at_backup = _rows(Path(d.db))
    result = take_snapshot(Path(d.db), data_dir, settings, store, work,
                           lambda: "2026-11-26T03:00:00+00:00", label="nightly")
    file_path = d.scalar("SELECT file_path FROM manual_references WHERE id = ?",
                         (d.ids["manual"],))
    assert file_path.startswith("manuals/")
    assert file_path in [e.path for e in result.manifest.media]
    assert result.manifest.label == "nightly" and result.manifest.db_sha256

    [ref] = list_snapshots(store)
    target = d.folder / "restored"
    report = restore(ref, store, settings, target)
    assert report.rows == d.rows_at_backup
    for table in ("shops", "users", "subscriptions", "shop_members", "terms_acceptances",
                  "customers", "customer_bikes", "vehicles", "intake_visits",
                  "diagnostic_sessions", "work_orders", "work_order_parts",
                  "work_order_time_entries", "parts", "labor_rates", "invoices",
                  "invoice_line_items", "invoice_payments", "shop_payment_accounts",
                  "stripe_event_cursors", "tax_jurisdictions", "shop_tax_jurisdictions",
                  "tax_rates", "tax_line_rules", "manual_references", "manual_pages",
                  "manual_reviewers", "audit_events"):
        assert report.rows[table] > 0, table
    assert (target / file_path).read_bytes() == d.pdf
    runs = (work / "runs.log").read_text().splitlines()
    assert len(runs) == 1 and json.loads(runs[0])["outcome"] == "ok"


STEPS: list[tuple[str, Callable[[Day], None]]] = [
    ("the shop, made with the wizard", the_shop_made_with_the_wizard),
    ("the Shop plan, before the first shop route", the_shop_plan_before_the_first_shop_route),
    ("signing in", signing_in),
    ("the terms", the_terms),
    ("each limited to their role", each_limited_to_their_role),
    ("a customer and a bike", a_customer_and_a_bike),
    ("a diagnosis", a_diagnosis),
    ("a work order with parts and labour", a_work_order_with_parts_and_labour),
    ("an invoice at the shop's own tax rate", an_invoice_at_the_shops_own_tax_rate),
    ("paid by card through the payments feed", paid_by_card_through_the_feed),
    ("a manual uploaded, reviewed and opened", a_manual_uploaded_reviewed_and_opened),
    ("the plan's limits", the_plans_limits),
    ("the audit log names who did each step", the_audit_log_names_who_did_each_step),
    ("the night's backup", the_nights_backup),
]


# ---------------------------------------------------------------- running the day
def run_day(folder: Path) -> Day:
    d = Day(folder, pdf=pdf_bytes(1))
    with pytest.MonkeyPatch.context() as mp:
        d.mp = mp
        for k, v in {**STRIPE_ENV, "MOTODIAG_TERMS_REQUIRED": "true", "MOTODIAG_ENV": "dev",
                     "MOTODIAG_DATA_DIR": str(folder / "data"), "COLUMNS": "240"}.items():
            mp.setenv(k, v)
        use_path(mp, stub_scanner(folder / "bin", "eicar"))
        real_refuse = network_guard._refuse

        def record(host):
            d.refused_hosts.append(str(host))
            real_refuse(host)

        mp.setattr(network_guard, "_refuse", record)
        freeze_webhook_clock(mp)
        cheap_crypto(mp)
        d.db = new_db(folder, mp)
        d.c = TestClient(create_app(db_path_override=d.db), raise_server_exceptions=False)
        try:
            for name, step in STEPS:
                try:
                    step(d)
                except Exception as e:  # recorded; the step's test re-raises it
                    e.add_note(f"the shop's day stopped at: {name}")
                    d.failed[name] = e
                    break
                d.done.append(name)
        finally:
            d.c.close()
            d.mp = None
    reset_settings()
    reset_console()
    return d


@pytest.fixture(scope="module")
def day(tmp_path_factory) -> Day:
    return run_day(tmp_path_factory.mktemp("phase210_day"))


def _step(day: Day, name: str) -> None:
    if name in day.done:
        return
    if name in day.failed:
        raise day.failed[name]
    stopped = next(iter(day.failed), "an unknown step")
    pytest.fail(f"the shop's day stopped before this step, at: {stopped}\n"
                + "".join(traceback.format_exception(day.failed[stopped]))
                if day.failed else f"the shop's day never reached: {name}")


def test_the_shop_made_with_the_wizard(day):
    _step(day, "the shop, made with the wizard")


def test_the_shop_plan_before_the_first_shop_route(day):
    _step(day, "the Shop plan, before the first shop route")


def test_signing_in(day):
    _step(day, "signing in")


def test_the_terms(day):
    _step(day, "the terms")


def test_each_limited_to_their_role(day):
    _step(day, "each limited to their role")


def test_a_customer_and_a_bike(day):
    _step(day, "a customer and a bike")


def test_a_diagnosis(day):
    _step(day, "a diagnosis")


def test_a_work_order_with_parts_and_labour(day):
    _step(day, "a work order with parts and labour")


def test_an_invoice_at_the_shops_own_tax_rate(day):
    _step(day, "an invoice at the shop's own tax rate")


def test_paid_by_card_through_the_payments_feed(day):
    _step(day, "paid by card through the payments feed")


def test_a_manual_uploaded_reviewed_and_opened(day):
    _step(day, "a manual uploaded, reviewed and opened")


def test_the_plans_limits(day):
    _step(day, "the plan's limits")


def test_the_audit_log_names_who_did_each_step(day):
    _step(day, "the audit log names who did each step")


def test_the_nights_backup(day):
    _step(day, "the night's backup")


def test_every_step_ran_and_none_reached_a_network(day):
    assert day.done == [name for name, _ in STEPS], day.failed
    assert day.refused_hosts == []


def test_a_rebuild_of_the_day_gives_the_same_ids(day, tmp_path):
    again = run_day(tmp_path / "again")
    assert again.done == day.done
    assert again.ids == day.ids
