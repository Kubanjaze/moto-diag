"""Phase 281, row 289: exchange rates and conversion.

The ECB's daily reference rates, fetched on request and stored with their
date, are usable through the 5th calendar day after it (the operator,
2026-09-30); a shop's own rates carry the validity it enters. Every conversion
prints its rate, date and source; the ECB's say they are for information
only. The ECB is never called: its feed is the recorded smoke response.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from motodiag.accounting import exchange
from support.phase281 import UNREACHABLE, fixture, new_db, ok, on_day, refused, seed_shop, \
    serve, sql

ECB_OK = {"eurofxref-daily.xml": (200, fixture("ecb_daily_2026-09-30.xml"))}


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    seed_shop(path, "Reyes Moto")
    return path


class TestTheFeed:
    def test_the_recorded_feed_parses_to_29_rates_of_one_date(self):
        rate_date, rates = exchange.parse_ecb_daily(fixture("ecb_daily_2026-09-30.xml"))
        assert rate_date == "2026-09-30"
        assert len(rates) == 29
        assert rates["USD"] == Decimal("1.1355")
        assert rates["CAD"] == Decimal("1.6105")
        assert rates["GBP"] == Decimal("0.85463")

    def test_refresh_stores_them_valid_through_the_5th_day(self, db, monkeypatch):
        asked = serve(monkeypatch, ECB_OK)
        out = ok(db, "shop", "currency", "refresh")
        assert asked == [exchange.ECB_DAILY_URL]
        assert "ECB reference rates for 2026-09-30: 29 currencies (29 new)" in out
        assert "usable until 2026-10-05" in out
        assert "published for information purposes only" in out
        assert "not used on invoices" in out
        rows = sql(db, "SELECT base, quote, rate, rate_date, valid_until, source FROM "
                       "exchange_rates WHERE quote = 'USD'")
        assert rows == [("EUR", "USD", "1.1355", "2026-09-30", "2026-10-05", "ecb")]

    def test_a_second_refresh_of_the_same_date_adds_nothing(self, db, monkeypatch):
        serve(monkeypatch, ECB_OK)
        ok(db, "shop", "currency", "refresh")
        assert "(0 new)" in ok(db, "shop", "currency", "refresh")
        assert sql(db, "SELECT COUNT(*) FROM exchange_rates")[0][0] == 29


class TestTheServiceDown:
    @pytest.mark.parametrize("answer, said", [
        (UNREACHABLE, "ECB reference rates could not be reached"),
        ((503, fixture("service_error_503_built.html")),
         "ECB reference rates answered with an error: HTTP 503"),
        ((200, fixture("service_error_503_built.html")),
         "ECB reference rates refused the request: HTTP 200 with a web page"),
        ((500, b"oops"), "ECB reference rates answered with an error: HTTP 500"),
        ((200, b"<gesmes:Envelope"), "ECB reference rates sent an answer that could not be read"),
    ])
    def test_it_says_so_naming_the_service_and_exits_1(self, db, monkeypatch, answer, said):
        serve(monkeypatch, {"eurofxref": answer})
        out = refused(db, "shop", "currency", "refresh")
        assert said in out
        assert "No ECB rates are stored." in out
        assert "currencies" not in out

    def test_what_is_stored_is_shown_with_its_date(self, db, monkeypatch):
        serve(monkeypatch, ECB_OK)
        ok(db, "shop", "currency", "refresh")
        serve(monkeypatch, {"eurofxref": UNREACHABLE})
        out = refused(db, "shop", "currency", "refresh")
        assert "could not be reached" in out
        assert "Stored ECB rates, newest dated 2026-09-30, valid until 2026-10-05" in out


class TestConversion:
    @pytest.fixture
    def rates(self, db, monkeypatch):
        serve(monkeypatch, ECB_OK)
        ok(db, "shop", "currency", "refresh")
        return db

    def test_a_cross_rate_through_the_euro_is_labelled(self, rates, monkeypatch):
        on_day(monkeypatch, "2026-10-01")
        out = ok(rates, "shop", "currency", "convert", "100", "USD", "CAD")
        assert "100 USD = 141.83 CAD" in out      # 100 x 1.6105 / 1.1355
        assert "a cross rate through the euro, from two ECB rates" in out
        assert "dated 2026-09-30, valid until 2026-10-05; source: ECB" in out
        assert "published for information purposes only" in out

    def test_direct_and_inverse(self, rates, monkeypatch):
        on_day(monkeypatch, "2026-10-01")
        assert "100 EUR = 113.55 USD" in ok(rates, "shop", "currency", "convert", "100",
                                            "EUR", "USD")
        out = ok(rates, "shop", "currency", "convert", "113.55", "USD", "EUR")
        assert "113.55 USD = 100.00 EUR" in out
        assert "the inverse of the euro rate" in out

    def test_valid_through_the_5th_day_and_refused_on_the_6th(self, rates, monkeypatch):
        on_day(monkeypatch, "2026-10-05")
        ok(rates, "shop", "currency", "convert", "100", "USD", "GBP")
        on_day(monkeypatch, "2026-10-06")
        out = refused(rates, "shop", "currency", "convert", "100", "USD", "GBP")
        assert "no ECB rates valid on this date" in out
        assert "motodiag shop currency refresh" in out

    def test_a_rate_is_not_used_before_its_own_date(self, rates, monkeypatch):
        on_day(monkeypatch, "2026-09-29")
        refused(rates, "shop", "currency", "convert", "100", "USD", "GBP")

    def test_a_currency_the_ecb_does_not_quote_is_refused(self, rates, monkeypatch):
        on_day(monkeypatch, "2026-10-01")
        out = refused(rates, "shop", "currency", "convert", "100", "USD", "XAU")
        assert "have no XAU" in out

    def test_the_shops_own_rate_wins_when_asked_for(self, rates, monkeypatch):
        on_day(monkeypatch, "2026-10-01")
        ok(rates, "shop", "currency", "set", "--shop", "1", "--from", "USD", "--to", "CAD",
           "--rate", "1.40", "--rate-date", "2026-09-30", "--valid-until", "2026-10-02",
           "--source", "Eastern Bank quote")
        out = ok(rates, "shop", "currency", "convert", "100", "USD", "CAD", "--shop", "1")
        assert "100 USD = 140.00 CAD" in out
        assert "the shop's own rate (Eastern Bank quote)" in out
        assert "information purposes" not in out
        on_day(monkeypatch, "2026-10-03")
        out = ok(rates, "shop", "currency", "convert", "100", "USD", "CAD", "--shop", "1")
        assert "source: ECB" in out, "past its validity the shop's rate is not used"

    def test_a_shops_rate_needs_its_source_and_a_sane_period(self, db):
        out = refused(db, "shop", "currency", "set", "--shop", "1", "--from", "USD", "--to",
                      "CAD", "--rate", "0", "--rate-date", "2026-09-30", "--valid-until",
                      "2026-10-02", "--source", "bank")
        assert "greater than zero" in out
        out = refused(db, "shop", "currency", "set", "--shop", "1", "--from", "USD", "--to",
                      "CAD", "--rate", "1.4", "--rate-date", "2026-09-30", "--valid-until",
                      "2026-09-01", "--source", "bank")
        assert "is before the rate's date" in out

    def test_rates_lists_what_is_stored(self, rates):
        out = ok(rates, "shop", "currency", "rates")
        assert "2026-10-05" in out and "ECB" in out
