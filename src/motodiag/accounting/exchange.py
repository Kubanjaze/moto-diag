"""Exchange rates (Phase 281, row 289).

Two sources, both stored with the rate's own date, a valid-until date and
their source:

- the ECB's euro reference rates, fetched on request from the ECB's daily
  feed. The ECB says they are "published for information purposes only.
  Using the rates for transaction purposes is strongly discouraged." So they
  convert amounts shown to the user, and never an invoice (the operator's
  3A, 2026-09-30);
- a shop's own rate (its bank's, say), entered with its source and
  valid-until date. Only these convert an invoice.

The ECB states no validity. The operator (2026-09-30) set it: a rate is
usable through the 5th calendar day after its own date, which covers the
Easter closure (Thursday's rate until Tuesday's is published).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.core.outbound import ServiceUnavailable, fetch

ECB_SERVICE = "ECB reference rates"
ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
ECB_VALID_DAYS = 5
ECB_CAVEAT = "ECB reference rate, published for information purposes only."

_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_ECB_NS = "{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}"


class ExchangeRateError(ValueError):
    """A rate could not be recorded, or no valid rate converts the amount."""


@dataclass(frozen=True)
class Conversion:
    amount: Decimal
    result: Decimal
    from_currency: str
    to_currency: str
    rate: Decimal
    rate_date: str
    valid_until: str
    source: str
    source_note: str
    method: str  # direct, inverse, cross (through the euro), same
    rate_id: Optional[int]

    @property
    def is_ecb(self) -> bool:
        return self.source == "ecb"


def _currency(value: str) -> str:
    code = str(value).strip().upper()
    if not _CURRENCY_RE.match(code):
        raise ExchangeRateError(f"a currency is three letters (USD, CAD, EUR); got {value!r}")
    return code


def _day(value: str, what: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise ExchangeRateError(f"{what} must be a date as YYYY-MM-DD (got {value!r})") from exc


def parse_ecb_daily(body: bytes) -> tuple[str, dict[str, Decimal]]:
    """The rate date and EUR→currency rates from the ECB's daily XML."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ServiceUnavailable(ECB_SERVICE, "malformed", f"not XML ({exc})") from exc
    dated = [c for c in root.iter(f"{_ECB_NS}Cube") if c.get("time")]
    if len(dated) != 1:
        raise ServiceUnavailable(ECB_SERVICE, "malformed",
                                 f"expected one dated set of rates, found {len(dated)}")
    rate_date = dated[0].get("time")
    rates: dict[str, Decimal] = {}
    for cube in dated[0]:
        currency, rate = cube.get("currency"), cube.get("rate")
        if not currency or not rate:
            continue
        rates[currency] = Decimal(rate)
    if not rates:
        raise ServiceUnavailable(ECB_SERVICE, "malformed", "the feed held no rates")
    _day(rate_date, "the ECB's rate date")
    return rate_date, rates


def refresh_ecb(db_path: Optional[str] = None) -> dict:
    """Fetch the ECB's daily rates and store them. Raises ServiceUnavailable."""
    response = fetch(ECB_SERVICE, ECB_DAILY_URL, expect="xml")
    rate_date, rates = parse_ecb_daily(response.body)
    valid_until = (date.fromisoformat(rate_date) + timedelta(days=ECB_VALID_DAYS)).isoformat()
    added = 0
    with get_connection(db_path) as conn:
        for currency, rate in sorted(rates.items()):
            cur = conn.execute(
                "INSERT OR IGNORE INTO exchange_rates (base, quote, rate, rate_date, "
                "valid_until, source, source_url, fetched_at) "
                "VALUES ('EUR', ?, ?, ?, ?, 'ecb', ?, ?)",
                (currency, str(rate), rate_date, valid_until, ECB_DAILY_URL,
                 response.fetched_at),
            )
            added += cur.rowcount
    return {"rate_date": rate_date, "valid_until": valid_until, "currencies": len(rates),
            "added": added, "status": response.status, "bytes": len(response.body),
            "fetched_at": response.fetched_at, "url": response.url}


def set_shop_rate(shop_id: int, from_currency: str, to_currency: str, rate: str,
                  rate_date: str, valid_until: str, source_note: str,
                  user_id: Optional[int] = None, db_path: Optional[str] = None) -> int:
    """Record a shop's own rate: 1 ``from_currency`` = ``rate`` ``to_currency``."""
    base, quote = _currency(from_currency), _currency(to_currency)
    if base == quote:
        raise ExchangeRateError("a rate converts between two different currencies")
    try:
        value = Decimal(str(rate))
    except ArithmeticError as exc:
        raise ExchangeRateError(f"a rate is a number (got {rate!r})") from exc
    if not value > 0:
        raise ExchangeRateError(f"a rate is greater than zero (got {rate})")
    start, end = _day(rate_date, "the rate's date"), _day(valid_until, "the valid-until date")
    if end < start:
        raise ExchangeRateError(f"the valid-until date {end} is before the rate's date {start}")
    if not source_note or not str(source_note).strip():
        raise ExchangeRateError("a source is required (for example, the bank that quoted it)")
    with get_connection(db_path) as conn:
        if not conn.execute("SELECT 1 FROM shops WHERE id = ?", (shop_id,)).fetchone():
            raise ExchangeRateError(f"no shop with id {shop_id}")
        return conn.execute(
            "INSERT INTO exchange_rates (base, quote, rate, rate_date, valid_until, source, "
            "shop_id, source_note, entered_by_user_id) VALUES (?, ?, ?, ?, ?, 'shop', ?, ?, ?)",
            (base, quote, str(value), start.isoformat(), end.isoformat(), shop_id,
             str(source_note).strip(), user_id),
        ).lastrowid


def list_rates(db_path: Optional[str] = None, shop_id: Optional[int] = None) -> list[dict]:
    with get_connection(db_path) as conn:
        query = "SELECT * FROM exchange_rates WHERE source = 'ecb'"
        params: list = []
        if shop_id is not None:
            query = "SELECT * FROM exchange_rates WHERE source = 'ecb' OR shop_id = ?"
            params = [shop_id]
        query += " ORDER BY rate_date DESC, source, base, quote"
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def _round(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def shop_rate(shop_id: int, from_currency: str, to_currency: str, on_date: date,
              db_path: Optional[str] = None) -> Optional[dict]:
    """The shop's own rate for this pair, valid on ``on_date``."""
    on = on_date.isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM exchange_rates WHERE source = 'shop' AND shop_id = ? "
            "AND base = ? AND quote = ? AND rate_date <= ? AND valid_until >= ? "
            "ORDER BY rate_date DESC, id DESC LIMIT 1",
            (shop_id, from_currency, to_currency, on, on),
        ).fetchone()
        return dict(row) if row else None


def _ecb_rows(conn, on: str) -> dict[str, dict]:
    """The newest ECB rates valid on ``on``, all of one rate date."""
    latest = conn.execute(
        "SELECT MAX(rate_date) FROM exchange_rates WHERE source = 'ecb' "
        "AND rate_date <= ? AND valid_until >= ?", (on, on),
    ).fetchone()[0]
    if latest is None:
        return {}
    rows = conn.execute(
        "SELECT * FROM exchange_rates WHERE source = 'ecb' AND rate_date = ?", (latest,),
    ).fetchall()
    return {r["quote"]: dict(r) for r in rows}


def convert(amount: str, from_currency: str, to_currency: str, on_date: date,
            shop_id: Optional[int] = None, db_path: Optional[str] = None) -> Conversion:
    """Convert with the shop's own valid rate if asked and present, else the ECB's."""
    base, quote = _currency(from_currency), _currency(to_currency)
    try:
        value = Decimal(str(amount))
    except ArithmeticError as exc:
        raise ExchangeRateError(f"an amount is a number (got {amount!r})") from exc
    on = on_date.isoformat()
    if base == quote:
        return Conversion(value, value, base, quote, Decimal(1), on, on, "same", "", "same", None)
    if shop_id is not None:
        own = shop_rate(shop_id, base, quote, on_date, db_path=db_path)
        if own is not None:
            rate = Decimal(own["rate"])
            return Conversion(value, _round(value * rate), base, quote, rate,
                              own["rate_date"], own["valid_until"], "shop",
                              own["source_note"] or "", "direct", int(own["id"]))
    with get_connection(db_path) as conn:
        ecb = _ecb_rows(conn, on)
    missing = [c for c in (base, quote) if c != "EUR" and c not in ecb]
    if not ecb or missing:
        stored = "no ECB rates valid on this date" if not ecb else \
            f"the ECB rates valid on this date have no {', '.join(missing)}"
        raise ExchangeRateError(
            f"no valid rate converts {base} to {quote} on {on}: {stored}. Fetch the ECB's "
            f"rates with `motodiag shop currency refresh`"
            + (f", or record the shop's own with `motodiag shop currency set --shop "
               f"{shop_id}`" if shop_id is not None else "")
        )
    if base == "EUR":
        row = ecb[quote]
        rate, method, rate_id = Decimal(row["rate"]), "direct", int(row["id"])
    elif quote == "EUR":
        row = ecb[base]
        rate, method, rate_id = Decimal(1) / Decimal(row["rate"]), "inverse", int(row["id"])
    else:
        row = ecb[quote]
        rate = Decimal(ecb[quote]["rate"]) / Decimal(ecb[base]["rate"])
        method, rate_id = "cross", None
    return Conversion(value, _round(value * rate), base, quote, rate, row["rate_date"],
                      row["valid_until"], "ecb", ECB_DAILY_URL, method, rate_id)
