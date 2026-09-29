"""Phase 274 — row 274, Customer CRM: the communication log and bike ownership.

Everything is driven through `motodiag shop customer …` against a scratch
database.
"""

from __future__ import annotations

import json

import pytest

from support.phase274 import (
    new_db, ok, refused, seed_bike, seed_customer, seed_shop, sql,
)


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    shop = seed_shop(path)
    seed_customer(path, shop, "Dana Reyes", "dana@example.com")   # id 2
    seed_customer(path, shop, "Sam Ortiz", "sam@example.com")     # id 3
    seed_bike(path)                                                 # id 1
    return path


def _history(db_path, who="2"):
    return json.loads(ok(db_path, "shop", "customer", "history", who, "--json"))


class TestCommunicationLog:
    def test_a_logged_call_is_stored_and_shown(self, db):
        out = ok(db, "shop", "customer", "log-contact", "2", "--channel", "phone",
                 "--direction", "inbound", "--summary", "Asked when the bike is ready",
                 "--at", "2026-09-20T10:00:00")
        assert "Logged contact #1 with Dana Reyes (inbound, phone)" in out
        assert sql(db, "SELECT customer_id, shop_id, direction, channel, summary, "
                       "occurred_at FROM customer_communications") == [
            (2, 1, "inbound", "phone", "Asked when the bike is ready", "2026-09-20T10:00:00")]
        table = ok(db, "shop", "customer", "history", "2")
        assert "Asked when the bike is ready" in table
        assert "inbound" in table and "phone" in table

    def test_the_history_merges_contacts_and_notifications_newest_first(self, db):
        ok(db, "shop", "customer", "log-contact", "2", "--channel", "in_person",
           "--direction", "outbound", "--summary", "Explained the valve job",
           "--at", "2026-09-10T09:00:00")
        sql(db, "INSERT INTO customer_notifications (customer_id, shop_id, event, channel, "
                "recipient, subject, body, triggered_at) VALUES (2, 1, 'wo_completed', "
                "'email', 'dana@example.com', 'Your bike is ready', 'body', "
                "'2026-09-15T12:00:00')")
        ok(db, "shop", "customer", "log-contact", "2", "--channel", "sms",
           "--direction", "inbound", "--summary", "Will pick up Friday",
           "--at", "2026-09-16T08:00:00")
        got = [(e["source"], e["text"]) for e in _history(db)]
        assert got == [
            ("contact", "Will pick up Friday"),
            ("notification", "Your bike is ready"),
            ("contact", "Explained the valve job"),
        ]

    def test_another_customers_entries_are_not_shown(self, db):
        ok(db, "shop", "customer", "log-contact", "3", "--channel", "phone",
           "--direction", "inbound", "--summary", "Sam called")
        assert _history(db, "2") == []
        assert "Nothing logged for Dana Reyes" in ok(db, "shop", "customer", "history", "2")

    def test_a_work_order_of_another_customer_is_refused(self, db):
        sql(db, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title) "
                "VALUES (1, 1, 3, 'Sam job')")
        out = refused(db, "shop", "customer", "log-contact", "2", "--channel", "phone",
                      "--direction", "outbound", "--summary", "x", "--wo", "1")
        assert "belongs to another customer" in out
        assert sql(db, "SELECT COUNT(*) FROM customer_communications") == [(0,)]

    def test_an_empty_summary_is_refused(self, db):
        out = refused(db, "shop", "customer", "log-contact", "2", "--channel", "phone",
                      "--direction", "outbound", "--summary", "   ")
        assert "summary" in out

    def test_an_unknown_channel_is_not_a_choice(self, db):
        refused(db, "shop", "customer", "log-contact", "2", "--channel", "pigeon",
                "--direction", "outbound", "--summary", "x")


class TestOwnership:
    def test_a_transfer_records_the_previous_owner(self, db):
        ok(db, "shop", "customer", "link-bike", "2", "--bike", "1")
        out = ok(db, "shop", "customer", "transfer-bike", "--bike", "1",
                 "--from", "2", "--to", "3", "--notes", "sold privately")
        assert "now belongs to Sam Ortiz" in out
        rows = json.loads(ok(db, "shop", "customer", "bike-owners", "1", "--json"))
        assert [(r["name"], r["cb_relationship"]) for r in rows] == [
            ("Sam Ortiz", "owner"), ("Dana Reyes", "previous_owner")]
        table = ok(db, "shop", "customer", "bike-owners", "1")
        assert "previous_owner" in table and "Sam Ortiz" in table

    def test_a_transfer_from_a_non_owner_is_refused(self, db):
        ok(db, "shop", "customer", "link-bike", "2", "--bike", "1")
        out = refused(db, "shop", "customer", "transfer-bike", "--bike", "1",
                      "--from", "3", "--to", "2")
        assert "not the recorded owner" in out
        assert sql(db, "SELECT customer_id, relationship FROM customer_bikes") == [
            (2, "owner")]

    def test_a_bike_sold_back_to_a_previous_owner_and_on_again(self, db):
        """Dana → Sam → Dana → Sam: one owner, and each earlier owner keeps one
        previous link (Sam owned it before, so he is both)."""
        ok(db, "shop", "customer", "link-bike", "2", "--bike", "1")
        for a, b in (("2", "3"), ("3", "2"), ("2", "3")):
            ok(db, "shop", "customer", "transfer-bike", "--bike", "1", "--from", a, "--to", b)
        assert sorted(sql(db, "SELECT customer_id, relationship FROM customer_bikes")) == [
            (2, "previous_owner"), (3, "owner"), (3, "previous_owner")]

    def test_a_bike_with_no_links_says_so(self, db):
        assert "No customer is linked" in ok(db, "shop", "customer", "bike-owners", "1")
