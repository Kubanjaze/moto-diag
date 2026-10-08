"""Sales tax by jurisdiction (Phase 281, row 288).

A shop is in one tax jurisdiction. For each jurisdiction the database holds
its rate and, for each invoice line type, whether that type is taxable.
Every rate and rule carries the date it takes effect, the date it is valid
until, its source and when the source was checked, and its provenance:

- ``regulation``: shipped, read from the regulator's own text (Massachusetts,
  from the Department of Revenue; ``docs/phases/completed/281_sources.md``);
- ``shop``: entered by one shop for itself, which applies to that shop only.

A rule's ``basis`` says whether the source states it (``stated``) or it is
this build's reading of the source (``reading``).

Tax is never assumed. `resolve_tax` answers for an invoice date or raises
`TaxNotOnRecord`, naming what is missing and the command that records it.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Optional

from motodiag.core.database import get_connection

LINE_TYPES: tuple[str, ...] = ("labor", "parts", "diagnostic", "misc")

LINE_LABELS: dict[str, str] = {
    "labor": "labour", "parts": "parts", "diagnostic": "diagnostic fee",
    "misc": "shop supplies",
}

# Phase 373: who owes a warranty repair, which decides whether the tax on
# covered work goes on the claim (``tax_warranty_rules``).
PAYERS: tuple[str, ...] = ("maker_with_bike", "other", "shop_contract")

PAYER_LABELS: dict[str, str] = {
    "maker_with_bike": "a maker's warranty included in the bike's price",
    "other": "someone else's plan or contract",
    "shop_contract": "a service contract this shop sold",
}

# Phase 376: what happens to the tax charged on a claim whose shortfall the
# shop absorbs (``tax_settlement_rules``). The one treatment on record is
# that it stays owed; a jurisdiction read otherwise needs its own phase.
SETTLEMENT_RULE = "absorb"
SETTLEMENT_LABEL = "a warranty shortfall the shop absorbs"

# Phase 375: the tax on a warranty deductible charged to the customer, by
# payer (``tax_deductible_rules``). The one treatment on record taxes its
# taxable share, the lines of the types the shop's rules tax.
DEDUCTIBLE_TAX = "taxable_share"

# The operator, 2026-09-30: a regulation rate or rule is valid for 12 months
# from the date its source was last checked.
REGULATION_RECHECK_MONTHS = 12

_CODE_RE = re.compile(r"^[A-Z]{2}(-[A-Z0-9]{1,3})?$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class TaxRecordError(ValueError):
    """A tax record could not be written as given."""


class TaxNotOnRecord(ValueError):
    """An invoice cannot be taxed from what is on record."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Tax is not on record for this invoice: " + "; ".join(problems))


@dataclass(frozen=True)
class TaxItem:
    """One stored rate (``item == "rate"``) or line rule (``item`` a line type)."""

    item: str
    row_id: int
    value: float
    effective_from: str
    valid_until: str
    source_title: str
    source_url: Optional[str]
    source_clause: Optional[str]
    checked_on: str
    provenance: str
    basis: str

    @property
    def source_text(self) -> str:
        text = self.source_title
        if self.source_clause:
            text += f", {self.source_clause}"
        if self.source_url:
            text += f" ({self.source_url})"
        return text


@dataclass
class TaxDecision:
    jurisdiction_code: str
    jurisdiction_name: str
    currency: str
    rate: TaxItem
    rules: dict[str, TaxItem] = field(default_factory=dict)

    @property
    def taxable_types(self) -> list[str]:
        return [t for t in LINE_TYPES if t in self.rules and self.rules[t].value]

    @property
    def recheck_by(self) -> str:
        return min([self.rate.valid_until] + [r.valid_until for r in self.rules.values()])

    @property
    def source_text(self) -> str:
        return (f"{self.jurisdiction_code} {self.rate.value * 100:g}%: "
                f"{self.rate.source_text}, checked {self.rate.checked_on} ({self.rate.provenance})")


# ---------------------------------------------------------------------------
# Dates and checks
# ---------------------------------------------------------------------------


def today() -> date:
    """Today's date: the one clock every validity check reads."""
    return date.today()


def parse_day(value: str, what: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise TaxRecordError(f"{what} must be a date as YYYY-MM-DD (got {value!r})") from exc


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def _check_period(effective_from: str, valid_until: str) -> tuple[str, str]:
    start = parse_day(effective_from, "the effective date")
    end = parse_day(valid_until, "the valid-until date")
    if end < start:
        raise TaxRecordError(
            f"the valid-until date {end} is before the effective date {start}"
        )
    return start.isoformat(), end.isoformat()


def _require_text(value: Optional[str], what: str) -> str:
    if value is None or not str(value).strip():
        raise TaxRecordError(f"{what} is required")
    return str(value).strip()


# ---------------------------------------------------------------------------
# Jurisdictions
# ---------------------------------------------------------------------------


def add_jurisdiction(code: str, name: str, currency: str,
                     db_path: Optional[str] = None) -> int:
    code = str(code).strip().upper()
    currency = str(currency).strip().upper()
    if not _CODE_RE.match(code):
        raise TaxRecordError(
            f"a jurisdiction code is a country code, optionally with a region "
            f"(US-MA, CA-ON, GB); got {code!r}"
        )
    if not _CURRENCY_RE.match(currency):
        raise TaxRecordError(f"a currency is three letters (USD, CAD, EUR); got {currency!r}")
    name = _require_text(name, "a name")
    with get_connection(db_path) as conn:
        if conn.execute("SELECT 1 FROM tax_jurisdictions WHERE code = ?", (code,)).fetchone():
            raise TaxRecordError(f"jurisdiction {code} is already on record")
        return conn.execute(
            "INSERT INTO tax_jurisdictions (code, name, currency) VALUES (?, ?, ?)",
            (code, name, currency),
        ).lastrowid


def list_jurisdictions(db_path: Optional[str] = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, code, name, currency FROM tax_jurisdictions ORDER BY code"
        ).fetchall()
        return [dict(r) for r in rows]


def get_jurisdiction(code: str, db_path: Optional[str] = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT id, code, name, currency FROM tax_jurisdictions WHERE code = ?",
            (str(code).strip().upper(),),
        ).fetchone()
        return dict(row) if row else None


def set_shop_jurisdiction(shop_id: int, code: str, user_id: Optional[int] = None,
                          db_path: Optional[str] = None) -> dict:
    jur = get_jurisdiction(code, db_path=db_path)
    if jur is None:
        raise TaxRecordError(
            f"no jurisdiction {str(code).upper()!r} on record; add it with "
            f"`motodiag shop tax jurisdiction add`"
        )
    with get_connection(db_path) as conn:
        if not conn.execute("SELECT 1 FROM shops WHERE id = ?", (shop_id,)).fetchone():
            raise TaxRecordError(f"no shop with id {shop_id}")
        conn.execute(
            "INSERT INTO shop_tax_jurisdictions (shop_id, jurisdiction_id, set_by_user_id) "
            "VALUES (?, ?, ?) ON CONFLICT(shop_id) DO UPDATE SET "
            "jurisdiction_id = excluded.jurisdiction_id, "
            "set_by_user_id = excluded.set_by_user_id, set_at = CURRENT_TIMESTAMP",
            (shop_id, jur["id"], user_id),
        )
    return jur


def shop_jurisdiction(shop_id: int, db_path: Optional[str] = None) -> Optional[dict]:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT j.id, j.code, j.name, j.currency FROM shop_tax_jurisdictions s "
            "JOIN tax_jurisdictions j ON j.id = s.jurisdiction_id WHERE s.shop_id = ?",
            (shop_id,),
        ).fetchone()
        return dict(row) if row else None


def _require_shop_jurisdiction(shop_id: int, db_path: Optional[str]) -> dict:
    jur = shop_jurisdiction(shop_id, db_path=db_path)
    if jur is None:
        raise TaxRecordError(
            f"shop {shop_id} has no tax jurisdiction; set it with "
            f"`motodiag shop tax jurisdiction set --shop {shop_id} --code CODE`"
        )
    return jur


# ---------------------------------------------------------------------------
# A shop's own rate and rules
# ---------------------------------------------------------------------------


def set_shop_rate(shop_id: int, rate: float, effective_from: str, valid_until: str,
                  source_title: str, checked_on: str, source_url: Optional[str] = None,
                  user_id: Optional[int] = None, db_path: Optional[str] = None) -> int:
    """Record a shop's own rate (a fraction: 0.0625 is 6.25%)."""
    rate = float(rate)
    if not (0.0 <= rate < 1.0):
        raise TaxRecordError(f"a rate is from 0 up to 100% (got {rate * 100:g}%)")
    start, end = _check_period(effective_from, valid_until)
    checked = parse_day(checked_on, "the date the source was checked").isoformat()
    jur = _require_shop_jurisdiction(shop_id, db_path)
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO tax_rates (jurisdiction_id, shop_id, rate, effective_from, "
            "valid_until, source_title, source_url, checked_on, provenance, "
            "entered_by_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'shop', ?)",
            (jur["id"], shop_id, rate, start, end,
             _require_text(source_title, "a source"), source_url, checked, user_id),
        ).lastrowid


def set_shop_rule(shop_id: int, line_type: str, taxable: bool, effective_from: str,
                  valid_until: str, source_title: str, checked_on: str,
                  source_url: Optional[str] = None, source_clause: Optional[str] = None,
                  basis: str = "stated", user_id: Optional[int] = None,
                  db_path: Optional[str] = None) -> int:
    if line_type not in LINE_TYPES:
        raise TaxRecordError(f"a line type is one of {', '.join(LINE_TYPES)}; got {line_type!r}")
    if basis not in ("stated", "reading"):
        raise TaxRecordError(f"basis is stated or reading; got {basis!r}")
    start, end = _check_period(effective_from, valid_until)
    checked = parse_day(checked_on, "the date the source was checked").isoformat()
    jur = _require_shop_jurisdiction(shop_id, db_path)
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO tax_line_rules (jurisdiction_id, shop_id, line_type, taxable, "
            "basis, effective_from, valid_until, source_title, source_url, "
            "source_clause, checked_on, provenance, entered_by_user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'shop', ?)",
            (jur["id"], shop_id, line_type, 1 if taxable else 0, basis, start, end,
             _require_text(source_title, "a source"), source_url, source_clause,
             checked, user_id),
        ).lastrowid


def confirm_regulation(code: str, checked_on: str, source_url: str,
                       db_path: Optional[str] = None) -> dict:
    """Record a new check of a regulation's source.

    Copies the jurisdiction's latest regulation rate and rules as new rows,
    checked on ``checked_on`` and valid 12 months from it. The old rows stay.
    """
    checked = parse_day(checked_on, "the check date")
    url = _require_text(source_url, "the page checked")
    until = add_months(checked, REGULATION_RECHECK_MONTHS).isoformat()
    jur = get_jurisdiction(code, db_path=db_path)
    if jur is None:
        raise TaxRecordError(f"no jurisdiction {str(code).upper()!r} on record")
    with get_connection(db_path) as conn:
        rate = conn.execute(
            "SELECT * FROM tax_rates WHERE jurisdiction_id = ? AND provenance = 'regulation' "
            "ORDER BY checked_on DESC, id DESC LIMIT 1", (jur["id"],),
        ).fetchone()
        if rate is None:
            raise TaxRecordError(
                f"{jur['code']} has no regulation rate to confirm; its rates are its "
                f"shops' own"
            )
        conn.execute(
            "INSERT INTO tax_rates (jurisdiction_id, shop_id, rate, effective_from, "
            "valid_until, source_title, source_url, checked_on, provenance, notes) "
            "VALUES (?, NULL, ?, ?, ?, ?, ?, ?, 'regulation', ?)",
            (jur["id"], rate["rate"], rate["effective_from"], until, rate["source_title"],
             rate["source_url"], checked.isoformat(), f"re-checked at {url}"),
        )
        rules = conn.execute(
            "SELECT * FROM tax_line_rules r WHERE jurisdiction_id = ? "
            "AND provenance = 'regulation' AND id = (SELECT id FROM tax_line_rules x "
            "WHERE x.jurisdiction_id = r.jurisdiction_id AND x.line_type = r.line_type "
            "AND x.provenance = 'regulation' ORDER BY checked_on DESC, id DESC LIMIT 1)",
            (jur["id"],),
        ).fetchall()
        for rule in rules:
            conn.execute(
                "INSERT INTO tax_line_rules (jurisdiction_id, shop_id, line_type, taxable, "
                "basis, effective_from, valid_until, source_title, source_url, "
                "source_clause, checked_on, provenance, notes) "
                "VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'regulation', ?)",
                (jur["id"], rule["line_type"], rule["taxable"], rule["basis"],
                 rule["effective_from"], until, rule["source_title"], rule["source_url"],
                 rule["source_clause"], checked.isoformat(), f"re-checked at {url}"),
            )
        # Phase 373: the warranty rules are re-checked with the rest.
        warranty_rules = conn.execute(
            "SELECT * FROM tax_warranty_rules r WHERE jurisdiction_id = ? "
            "AND provenance = 'regulation' AND id = (SELECT id FROM tax_warranty_rules x "
            "WHERE x.jurisdiction_id = r.jurisdiction_id AND x.payer = r.payer "
            "AND x.provenance = 'regulation' ORDER BY checked_on DESC, id DESC LIMIT 1)",
            (jur["id"],),
        ).fetchall()
        for rule in warranty_rules:
            conn.execute(
                "INSERT INTO tax_warranty_rules (jurisdiction_id, shop_id, payer, "
                "taxed_on_claim, basis, effective_from, valid_until, source_title, "
                "source_url, source_clause, checked_on, provenance, notes) "
                "VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'regulation', ?)",
                (jur["id"], rule["payer"], rule["taxed_on_claim"], rule["basis"],
                 rule["effective_from"], until, rule["source_title"], rule["source_url"],
                 rule["source_clause"], checked.isoformat(), f"re-checked at {url}"),
            )
        # Phase 376: and the settlement rules.
        settlement_rules = conn.execute(
            "SELECT * FROM tax_settlement_rules r WHERE jurisdiction_id = ? "
            "AND provenance = 'regulation' AND id = (SELECT id FROM tax_settlement_rules x "
            "WHERE x.jurisdiction_id = r.jurisdiction_id AND x.settlement = r.settlement "
            "AND x.provenance = 'regulation' ORDER BY checked_on DESC, id DESC LIMIT 1)",
            (jur["id"],),
        ).fetchall()
        for rule in settlement_rules:
            conn.execute(
                "INSERT INTO tax_settlement_rules (jurisdiction_id, shop_id, settlement, "
                "absorbed_tax, basis, effective_from, valid_until, source_title, "
                "source_url, source_clause, checked_on, provenance, notes) "
                "VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'regulation', ?)",
                (jur["id"], rule["settlement"], rule["absorbed_tax"], rule["basis"],
                 rule["effective_from"], until, rule["source_title"], rule["source_url"],
                 rule["source_clause"], checked.isoformat(), f"re-checked at {url}"),
            )
        # Phase 375: and the deductible rules.
        deductible_rules = conn.execute(
            "SELECT * FROM tax_deductible_rules r WHERE jurisdiction_id = ? "
            "AND provenance = 'regulation' AND id = (SELECT id FROM tax_deductible_rules x "
            "WHERE x.jurisdiction_id = r.jurisdiction_id AND x.payer = r.payer "
            "AND x.provenance = 'regulation' ORDER BY checked_on DESC, id DESC LIMIT 1)",
            (jur["id"],),
        ).fetchall()
        for rule in deductible_rules:
            conn.execute(
                "INSERT INTO tax_deductible_rules (jurisdiction_id, shop_id, payer, "
                "deductible_tax, basis, effective_from, valid_until, source_title, "
                "source_url, source_clause, checked_on, provenance, notes) "
                "VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'regulation', ?)",
                (jur["id"], rule["payer"], rule["deductible_tax"], rule["basis"],
                 rule["effective_from"], until, rule["source_title"], rule["source_url"],
                 rule["source_clause"], checked.isoformat(),
                 f"re-checked at {url}. {rule['notes'] or ''}".strip()),
            )
    return {"code": jur["code"], "checked_on": checked.isoformat(), "valid_until": until,
            "rules": len(rules), "warranty_rules": len(warranty_rules),
            "settlement_rules": len(settlement_rules),
            "deductible_rules": len(deductible_rules)}


def set_shop_warranty_rule(shop_id: int, payer: str, taxed_on_claim: bool,
                           effective_from: str, valid_until: str, source_title: str,
                           checked_on: str, source_url: Optional[str] = None,
                           source_clause: Optional[str] = None, basis: str = "stated",
                           user_id: Optional[int] = None,
                           db_path: Optional[str] = None) -> int:
    """Record a shop's own rule for whether covered work's tax goes on the claim."""
    if payer not in PAYERS:
        raise TaxRecordError(f"a payer is one of {', '.join(PAYERS)}; got {payer!r}")
    if basis not in ("stated", "reading"):
        raise TaxRecordError(f"basis is stated or reading; got {basis!r}")
    start, end = _check_period(effective_from, valid_until)
    checked = parse_day(checked_on, "the date the source was checked").isoformat()
    jur = _require_shop_jurisdiction(shop_id, db_path)
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO tax_warranty_rules (jurisdiction_id, shop_id, payer, "
            "taxed_on_claim, basis, effective_from, valid_until, source_title, "
            "source_url, source_clause, checked_on, provenance, entered_by_user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'shop', ?)",
            (jur["id"], shop_id, payer, 1 if taxed_on_claim else 0, basis, start, end,
             _require_text(source_title, "a source"), source_url, source_clause,
             checked, user_id),
        ).lastrowid


def set_shop_settlement_rule(shop_id: int, effective_from: str, valid_until: str,
                             source_title: str, checked_on: str,
                             source_url: Optional[str] = None,
                             source_clause: Optional[str] = None, basis: str = "stated",
                             user_id: Optional[int] = None,
                             db_path: Optional[str] = None) -> int:
    """Record a shop's own reading that the tax charged on a claim stays owed
    when the shop absorbs the claim's shortfall (Phase 376)."""
    if basis not in ("stated", "reading"):
        raise TaxRecordError(f"basis is stated or reading; got {basis!r}")
    start, end = _check_period(effective_from, valid_until)
    checked = parse_day(checked_on, "the date the source was checked").isoformat()
    jur = _require_shop_jurisdiction(shop_id, db_path)
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO tax_settlement_rules (jurisdiction_id, shop_id, settlement, "
            "absorbed_tax, basis, effective_from, valid_until, source_title, "
            "source_url, source_clause, checked_on, provenance, entered_by_user_id) "
            "VALUES (?, ?, 'absorb', 'stays_owed', ?, ?, ?, ?, ?, ?, ?, 'shop', ?)",
            (jur["id"], shop_id, basis, start, end,
             _require_text(source_title, "a source"), source_url, source_clause,
             checked, user_id),
        ).lastrowid


def set_shop_deductible_rule(shop_id: int, payer: str, effective_from: str,
                             valid_until: str, source_title: str, checked_on: str,
                             source_url: Optional[str] = None,
                             source_clause: Optional[str] = None, basis: str = "stated",
                             user_id: Optional[int] = None,
                             db_path: Optional[str] = None) -> int:
    """Record a shop's own reading that a warranty deductible's taxable share
    is taxed to the customer, for a repair owed by ``payer`` (Phase 375)."""
    if payer not in PAYERS:
        raise TaxRecordError(f"a payer is one of {', '.join(PAYERS)}; got {payer!r}")
    if basis not in ("stated", "reading"):
        raise TaxRecordError(f"basis is stated or reading; got {basis!r}")
    start, end = _check_period(effective_from, valid_until)
    checked = parse_day(checked_on, "the date the source was checked").isoformat()
    jur = _require_shop_jurisdiction(shop_id, db_path)
    with get_connection(db_path) as conn:
        return conn.execute(
            "INSERT INTO tax_deductible_rules (jurisdiction_id, shop_id, payer, "
            "deductible_tax, basis, effective_from, valid_until, source_title, "
            "source_url, source_clause, checked_on, provenance, entered_by_user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'shop', ?)",
            (jur["id"], shop_id, payer, DEDUCTIBLE_TAX, basis, start, end,
             _require_text(source_title, "a source"), source_url, source_clause,
             checked, user_id),
        ).lastrowid


# ---------------------------------------------------------------------------
# Resolving and checking
# ---------------------------------------------------------------------------


def _item(row, item: str, value: float) -> TaxItem:
    keys = row.keys()
    return TaxItem(
        item=item, row_id=int(row["id"]), value=value,
        effective_from=row["effective_from"], valid_until=row["valid_until"],
        source_title=row["source_title"], source_url=row["source_url"],
        source_clause=row["source_clause"] if "source_clause" in keys else None,
        checked_on=row["checked_on"], provenance=row["provenance"],
        basis=row["basis"] if "basis" in keys else "stated",
    )


# The two tables `_pick` reads, written out so every query's table is visible
# in the source (the chokepoint gate refuses a table name held in a variable).
_PICK_FROM = {
    "tax_rates": "SELECT * FROM tax_rates WHERE ",
    "tax_line_rules": "SELECT * FROM tax_line_rules WHERE ",
    "tax_warranty_rules": "SELECT * FROM tax_warranty_rules WHERE ",
    "tax_settlement_rules": "SELECT * FROM tax_settlement_rules WHERE ",
    "tax_deductible_rules": "SELECT * FROM tax_deductible_rules WHERE ",
}


def _pick(conn, table: str, jur_id: int, shop_id: int, on: str,
          line_type: Optional[str] = None, valid_only: bool = True,
          payer: Optional[str] = None, settlement: Optional[str] = None):
    """The shop's own row if one applies, else the regulation row."""
    select = _PICK_FROM[table]
    where = "jurisdiction_id = ?"
    params: list = [jur_id]
    if line_type is not None:
        where += " AND line_type = ?"
        params.append(line_type)
    if payer is not None:
        where += " AND payer = ?"
        params.append(payer)
    if settlement is not None:
        where += " AND settlement = ?"
        params.append(settlement)
    if valid_only:
        where += " AND effective_from <= ? AND valid_until >= ?"
        params += [on, on]
    else:
        where += " AND effective_from <= ?"
        params.append(on)
    order = "ORDER BY effective_from DESC, checked_on DESC, id DESC LIMIT 1"
    own = conn.execute(
        select + where + " AND shop_id = ? " + order, params + [shop_id],
    ).fetchone()
    if own is not None:
        return own
    return conn.execute(
        select + where + " AND shop_id IS NULL " + order, params,
    ).fetchone()


def resolve_tax(shop_id: int, on_date: date, line_types: Iterable[str],
                db_path: Optional[str] = None) -> TaxDecision:
    """The rate and rules an invoice dated ``on_date`` uses, or TaxNotOnRecord."""
    on = on_date.isoformat()
    wanted = [t for t in LINE_TYPES if t in set(line_types)]
    jur = shop_jurisdiction(shop_id, db_path=db_path)
    if jur is None:
        raise TaxNotOnRecord([
            f"shop {shop_id} has no tax jurisdiction (set it with `motodiag shop tax "
            f"jurisdiction set --shop {shop_id} --code CODE`)"
        ])
    problems: list[str] = []
    with get_connection(db_path) as conn:
        rate_row = _pick(conn, "tax_rates", jur["id"], shop_id, on)
        if rate_row is None:
            problems.append(_missing_rate(conn, jur, shop_id, on))
        rules: dict[str, TaxItem] = {}
        for line_type in wanted:
            row = _pick(conn, "tax_line_rules", jur["id"], shop_id, on, line_type)
            if row is None:
                problems.append(_missing_rule(conn, jur, shop_id, on, line_type))
            else:
                rules[line_type] = _item(row, line_type, float(row["taxable"]))
    if problems:
        raise TaxNotOnRecord(problems)
    return TaxDecision(
        jurisdiction_code=jur["code"], jurisdiction_name=jur["name"],
        currency=jur["currency"], rate=_item(rate_row, "rate", float(rate_row["rate"])),
        rules=rules,
    )


def resolve_warranty_rule(shop_id: int, on_date: date, payer: str,
                          db_path: Optional[str] = None) -> TaxItem:
    """Whether covered work's tax goes on the claim, for a repair owed by
    ``payer``, on ``on_date``: the rule (``value`` 1.0 or 0.0) or
    TaxNotOnRecord."""
    on = on_date.isoformat()
    jur = shop_jurisdiction(shop_id, db_path=db_path)
    if jur is None:
        raise TaxNotOnRecord([
            f"shop {shop_id} has no tax jurisdiction (set it with `motodiag shop tax "
            f"jurisdiction set --shop {shop_id} --code CODE`)"
        ])
    with get_connection(db_path) as conn:
        row = _pick(conn, "tax_warranty_rules", jur["id"], shop_id, on, payer=payer)
        if row is None:
            raise TaxNotOnRecord([_missing_warranty_rule(conn, jur, shop_id, on, payer)])
    return _item(row, payer, float(row["taxed_on_claim"]))


def _missing_warranty_rule(conn, jur: dict, shop_id: int, on: str, payer: str) -> str:
    label = PAYER_LABELS[payer]
    stale = _pick(conn, "tax_warranty_rules", jur["id"], shop_id, on, payer=payer,
                  valid_only=False)
    if stale is not None:
        return (f"the {jur['code']} rule for warranty work owed by {label} was valid "
                f"until {stale['valid_until']} and must be re-checked")
    return (f"no {jur['code']} rule on record for the tax on warranty work owed by "
            f"{label} (record it with `motodiag shop tax warranty-rule set --shop "
            f"{shop_id} --payer {payer}`)")


def resolve_settlement_rule(shop_id: int, on_date: date,
                            db_path: Optional[str] = None) -> TaxItem:
    """The reading that the tax charged on a claim stays owed when the shop
    absorbs its shortfall, valid on ``on_date``, or TaxNotOnRecord (Phase 376)."""
    on = on_date.isoformat()
    jur = shop_jurisdiction(shop_id, db_path=db_path)
    if jur is None:
        raise TaxNotOnRecord([
            f"shop {shop_id} has no tax jurisdiction (set it with `motodiag shop tax "
            f"jurisdiction set --shop {shop_id} --code CODE`)"
        ])
    with get_connection(db_path) as conn:
        row = _pick(conn, "tax_settlement_rules", jur["id"], shop_id, on,
                    settlement=SETTLEMENT_RULE)
        if row is None:
            raise TaxNotOnRecord([_missing_settlement_rule(conn, jur, shop_id, on)])
    return _item(row, SETTLEMENT_RULE, 1.0)


def _missing_settlement_rule(conn, jur: dict, shop_id: int, on: str) -> str:
    stale = _pick(conn, "tax_settlement_rules", jur["id"], shop_id, on,
                  settlement=SETTLEMENT_RULE, valid_only=False)
    if stale is not None:
        return (f"the {jur['code']} rule for the tax on {SETTLEMENT_LABEL} was valid "
                f"until {stale['valid_until']} and must be re-checked")
    return (f"no {jur['code']} rule on record for the tax on {SETTLEMENT_LABEL} "
            f"(record the shop's reading with `motodiag shop tax settlement-rule set "
            f"--shop {shop_id}`)")


def resolve_deductible_rule(shop_id: int, on_date: date, payer: str,
                            db_path: Optional[str] = None) -> TaxItem:
    """The reading that a warranty deductible's taxable share is taxed to the
    customer, for a repair owed by ``payer``, valid on ``on_date``, or
    TaxNotOnRecord (Phase 375)."""
    on = on_date.isoformat()
    jur = shop_jurisdiction(shop_id, db_path=db_path)
    if jur is None:
        raise TaxNotOnRecord([
            f"shop {shop_id} has no tax jurisdiction (set it with `motodiag shop tax "
            f"jurisdiction set --shop {shop_id} --code CODE`)"
        ])
    with get_connection(db_path) as conn:
        row = _pick(conn, "tax_deductible_rules", jur["id"], shop_id, on, payer=payer)
        if row is None:
            raise TaxNotOnRecord([_missing_deductible_rule(conn, jur, shop_id, on, payer)])
    return _item(row, payer, 1.0)


def _missing_deductible_rule(conn, jur: dict, shop_id: int, on: str, payer: str) -> str:
    label = PAYER_LABELS[payer]
    stale = _pick(conn, "tax_deductible_rules", jur["id"], shop_id, on, payer=payer,
                  valid_only=False)
    if stale is not None:
        return (f"the {jur['code']} rule for the tax on a deductible under {label} was "
                f"valid until {stale['valid_until']} and must be re-checked")
    return (f"no {jur['code']} rule on record for the tax on a deductible under {label} "
            f"(record the shop's reading with `motodiag shop tax deductible-rule set "
            f"--shop {shop_id} --payer {payer}`)")


def _missing_rate(conn, jur: dict, shop_id: int, on: str) -> str:
    stale = _pick(conn, "tax_rates", jur["id"], shop_id, on, valid_only=False)
    if stale is not None:
        return (f"the {jur['code']} rate was valid until {stale['valid_until']} and must "
                f"be re-checked (`motodiag shop tax confirm` for a regulation rate, "
                f"`motodiag shop tax rate set --shop {shop_id}` for the shop's own)")
    return (f"no {jur['code']} rate on record for {on} (record the shop's own with "
            f"`motodiag shop tax rate set --shop {shop_id}`)")


def _missing_rule(conn, jur: dict, shop_id: int, on: str, line_type: str) -> str:
    label = LINE_LABELS[line_type]
    stale = _pick(conn, "tax_line_rules", jur["id"], shop_id, on, line_type,
                  valid_only=False)
    if stale is not None:
        return (f"the {jur['code']} rule for {label} was valid until "
                f"{stale['valid_until']} and must be re-checked")
    return (f"no {jur['code']} rule on record for whether {label} is taxable (record "
            f"it with `motodiag shop tax rule set --shop {shop_id} --line-type "
            f"{line_type}`)")


@dataclass
class TaxStatus:
    shop_id: int
    jurisdiction: Optional[dict]
    rate: Optional[TaxItem]
    rules: dict[str, TaxItem]
    failures: list[str]
    not_on_record: list[str]
    # Phase 373: whether covered warranty work's tax goes on the claim, by payer.
    warranty_rules: dict[str, TaxItem] = field(default_factory=dict)
    warranty_not_on_record: list[str] = field(default_factory=list)
    # Phase 376: the tax on an absorbed shortfall; None when none is valid,
    # and ``settlement_not_on_record`` when none was ever recorded.
    settlement_rule: Optional[TaxItem] = None
    settlement_not_on_record: bool = False
    # Phase 375: the tax on a warranty deductible, by payer.
    deductible_rules: dict[str, TaxItem] = field(default_factory=dict)
    deductible_not_on_record: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def recheck_by(self) -> Optional[str]:
        dates = [i.valid_until for i in ([self.rate] if self.rate else [])]
        dates += [r.valid_until for r in self.rules.values()]
        dates += [r.valid_until for r in self.warranty_rules.values()]
        dates += [self.settlement_rule.valid_until] if self.settlement_rule else []
        dates += [r.valid_until for r in self.deductible_rules.values()]
        return min(dates) if dates else None


def tax_status(shop_id: int, today: date, db_path: Optional[str] = None) -> TaxStatus:
    """What is on record for a shop today, and what fails the check.

    Fails: no jurisdiction; no rate valid today; a rule whose latest row is
    past its validity. A line type with no rule at all is listed as not on
    record: an invoice carrying it is refused, but a shop that never charges
    it is not failing.
    """
    on = today.isoformat()
    jur = shop_jurisdiction(shop_id, db_path=db_path)
    if jur is None:
        return TaxStatus(shop_id, None, None, {}, [
            f"no tax jurisdiction (set it with `motodiag shop tax jurisdiction set "
            f"--shop {shop_id} --code CODE`)"
        ], [])
    failures: list[str] = []
    not_on_record: list[str] = []
    rules: dict[str, TaxItem] = {}
    rate: Optional[TaxItem] = None
    with get_connection(db_path) as conn:
        rate_row = _pick(conn, "tax_rates", jur["id"], shop_id, on)
        if rate_row is None:
            failures.append(_missing_rate(conn, jur, shop_id, on))
        else:
            rate = _item(rate_row, "rate", float(rate_row["rate"]))
        for line_type in LINE_TYPES:
            row = _pick(conn, "tax_line_rules", jur["id"], shop_id, on, line_type)
            if row is not None:
                rules[line_type] = _item(row, line_type, float(row["taxable"]))
                continue
            stale = _pick(conn, "tax_line_rules", jur["id"], shop_id, on, line_type,
                          valid_only=False)
            if stale is not None:
                failures.append(_missing_rule(conn, jur, shop_id, on, line_type))
            else:
                not_on_record.append(line_type)
        warranty_rules: dict[str, TaxItem] = {}
        warranty_not_on_record: list[str] = []
        for payer in PAYERS:
            row = _pick(conn, "tax_warranty_rules", jur["id"], shop_id, on, payer=payer)
            if row is not None:
                warranty_rules[payer] = _item(row, payer, float(row["taxed_on_claim"]))
            elif _pick(conn, "tax_warranty_rules", jur["id"], shop_id, on, payer=payer,
                       valid_only=False) is not None:
                failures.append(_missing_warranty_rule(conn, jur, shop_id, on, payer))
            else:
                warranty_not_on_record.append(payer)
        settlement_rule: Optional[TaxItem] = None
        settlement_not_on_record = False
        row = _pick(conn, "tax_settlement_rules", jur["id"], shop_id, on,
                    settlement=SETTLEMENT_RULE)
        if row is not None:
            settlement_rule = _item(row, SETTLEMENT_RULE, 1.0)
        elif _pick(conn, "tax_settlement_rules", jur["id"], shop_id, on,
                   settlement=SETTLEMENT_RULE, valid_only=False) is not None:
            failures.append(_missing_settlement_rule(conn, jur, shop_id, on))
        else:
            settlement_not_on_record = True
        deductible_rules: dict[str, TaxItem] = {}
        deductible_not_on_record: list[str] = []
        for payer in PAYERS:
            row = _pick(conn, "tax_deductible_rules", jur["id"], shop_id, on, payer=payer)
            if row is not None:
                deductible_rules[payer] = _item(row, payer, 1.0)
            elif _pick(conn, "tax_deductible_rules", jur["id"], shop_id, on, payer=payer,
                       valid_only=False) is not None:
                failures.append(_missing_deductible_rule(conn, jur, shop_id, on, payer))
            else:
                deductible_not_on_record.append(payer)
    return TaxStatus(shop_id, jur, rate, rules, failures, not_on_record, warranty_rules,
                     warranty_not_on_record, settlement_rule, settlement_not_on_record,
                     deductible_rules, deductible_not_on_record)
