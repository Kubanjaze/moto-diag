"""Accounting export files: QuickBooks Online journal entries, Xero sales
invoices and (Phase 376) Xero credit notes.

Both are built from ``invoices`` and ``invoice_line_items`` (which
``shop/invoicing.py`` writes) and the shop's own account names
(``accounting_accounts``), and from warranty claims' settlements. Each
format follows its vendor's import page as read on 2026-09-29 (quoted in
``docs/phases/completed/275_format_sources.md``) and, for credit notes and
settlements, on 2026-10-07 (``376_sources.md``). No file has been tried in
a real QuickBooks or Xero company.

The files are written locally. Nothing is uploaded.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from motodiag.accounting import tax as tax_mod
from motodiag.core.database import get_connection
from motodiag.core.timestamps import local_day, local_day_start

# The command-line name of each target, and the name stored.
TARGETS: dict[str, str] = {"quickbooks-online": "quickbooks_online", "xero": "xero"}

LINE_KINDS: tuple[str, ...] = ("labor", "parts", "diagnostic", "misc")
# Phase 376: ``absorbed``, where a warranty shortfall the shop absorbs goes.
KINDS: tuple[str, ...] = LINE_KINDS + ("tax", "receivable", "absorbed")

KIND_LABELS = {
    "labor": "labour", "parts": "parts", "diagnostic": "diagnostic",
    "misc": "shop supplies", "tax": "sales tax", "receivable": "accounts receivable",
    "absorbed": "warranty shortfall absorbed",
}

# Intuit, "Import journal entries" (QuickBooks Online): the six columns the
# page lists as required, and Name, which it asks for on an Accounts
# Receivable line.
QBO_JOURNAL_COLUMNS: tuple[str, ...] = (
    "Journal No.", "Journal Date", "Account Name", "Debits", "Credits",
    "Journal/Description", "Name",
)

# Xero, "Import customer invoices": every column name the page gives, plus
# Description and Quantity, which the page does not name and a line needs.
XERO_COLUMNS_FROM_PAGE: tuple[str, ...] = (
    "ContactName", "EmailAddress", "InvoiceNumber", "InvoiceDate", "DueDate",
    "InventoryItemCode", "UnitAmount", "Discount", "AccountCode", "TaxType",
    "TaxAmount", "TrackingName", "TrackingOption", "Currency", "BrandingTheme",
)
XERO_COLUMNS_NOT_ON_PAGE: tuple[str, ...] = ("Description", "Quantity")
XERO_COLUMNS: tuple[str, ...] = (
    "ContactName", "EmailAddress", "InvoiceNumber", "InvoiceDate", "DueDate",
    "InventoryItemCode", "Description", "Quantity", "UnitAmount", "Discount",
    "AccountCode", "TaxType", "TaxAmount", "TrackingName", "TrackingOption",
    "Currency", "BrandingTheme",
)

# Xero, "Import customer credit notes" (US), read 2026-10-07: the column
# names the page gives (376_sources.md X1), less the postal-address group,
# which the page names only as "POAddressLine1, etc". No TaxAmount: the file
# is tax-inclusive (the operator's choice 5A), because the page does not say
# what sign a credit note's tax amount takes.
XERO_CREDIT_NOTE_COLUMNS: tuple[str, ...] = (
    "ContactName", "EmailAddress", "InvoiceNumber", "Reference", "InvoiceDate",
    "DueDate", "InventoryItemCode", "Description", "Quantity", "UnitAmount",
    "Discount", "AccountCode", "TaxType", "TrackingName1", "TrackingOption1",
    "TrackingName2", "TrackingOption2", "Currency", "BrandingTheme",
)

QBO_STATEMENT = (
    "These are journal entries, not invoices: they carry no line items, and "
    "they do not reach QuickBooks' sales-tax reports."
)


class ExportError(ValueError):
    """An export that is refused, with the reason."""


def target_key(name: str) -> str:
    if name in TARGETS:
        return TARGETS[name]
    if name in TARGETS.values():
        return name
    raise ExportError(f"unknown target {name!r}; use {' or '.join(TARGETS)}")


def _target_name(key: str) -> str:
    return next(k for k, v in TARGETS.items() if v == key)


# ---------------------------------------------------------------------------
# The account mapping
# ---------------------------------------------------------------------------


def set_account(shop_id: int, target: str, kind: str, account: str,
                tax_type: Optional[str] = None,
                db_path: Optional[str] = None) -> None:
    """Map one kind to the shop's own account (and, for Xero, tax rate name)."""
    key = target_key(target)
    if kind not in KINDS:
        raise ExportError(f"kind must be one of {', '.join(KINDS)}")
    if not account or not account.strip():
        raise ExportError("the account name must not be empty")
    if tax_type is not None and not tax_type.strip():
        tax_type = None
    with get_connection(db_path) as conn:
        if conn.execute("SELECT 1 FROM shops WHERE id = ?", (shop_id,)).fetchone() is None:
            raise ExportError(f"shop not found: id={shop_id}")
        conn.execute(
            """INSERT INTO accounting_accounts (shop_id, target, kind, account, tax_type)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (shop_id, target, kind) DO UPDATE SET
                   account = excluded.account, tax_type = excluded.tax_type,
                   updated_at = CURRENT_TIMESTAMP""",
            (shop_id, key, kind, account.strip(),
             tax_type.strip() if tax_type else None),
        )


def list_accounts(shop_id: int, target: Optional[str] = None,
                  db_path: Optional[str] = None) -> list[dict]:
    q = "SELECT * FROM accounting_accounts WHERE shop_id = ?"
    params: list = [shop_id]
    if target is not None:
        q += " AND target = ?"
        params.append(target_key(target))
    with get_connection(db_path) as conn:
        rows = conn.execute(q + " ORDER BY target, kind", params).fetchall()
    return [dict(r) for r in rows]


def _mapping(shop_id: int, key: str, db_path: Optional[str]) -> dict[str, dict]:
    return {r["kind"]: r for r in list_accounts(shop_id, key, db_path=db_path)}


# ---------------------------------------------------------------------------
# The invoices
# ---------------------------------------------------------------------------


def _cents(amount) -> int:
    return int(round(float(amount or 0) * 100))


def _money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


money = _money  # the CLI prints amounts as the files write them


def _us_date(value: Optional[str]) -> str:
    """The shop's day of a stored time, such as ``issued_at`` (a bare date
    as written), MM/DD/YYYY."""
    if not value:
        return ""
    text = str(value)
    day = text if len(text) == 10 else local_day(text)
    return datetime.fromisoformat(day).strftime("%m/%d/%Y")


def _us_due_date(value: Optional[str]) -> str:
    """A due date, MM/DD/YYYY: a calendar date, so its own date as written."""
    if not value:
        return ""
    return datetime.fromisoformat(str(value)[:10]).strftime("%m/%d/%Y")


def _check_range(from_day: str, to_day: str) -> None:
    try:
        lo, hi = date.fromisoformat(from_day), date.fromisoformat(to_day)
    except ValueError as e:
        raise ExportError("dates must be YYYY-MM-DD") from e
    if hi < lo:
        raise ExportError("the range must end on or after its first day")


def _day_window(from_day: str, to_day: str) -> tuple[str, str]:
    """``[start, end)`` in UTC for the shop's days ``from_day..to_day``,
    for ``datetime(issued_at) >= ? AND datetime(issued_at) < ?``."""
    after = date.fromisoformat(to_day) + timedelta(days=1)
    return local_day_start(from_day), local_day_start(after)


def invoices_in_range(
    shop_id: int, from_day: str, to_day: str, key: str,
    include_exported: bool = False, db_path: Optional[str] = None,
) -> tuple[list[dict], list[str]]:
    """The shop's invoices issued in the range, not cancelled, with their lines.

    A shop's invoice is one whose work order is at the shop. Returns the
    invoices, and the numbers of those left out because an earlier export to
    the same target carried them (unless ``include_exported``). Each invoice
    carries its warranty claims with an amount (Phase 373) as ``claims``. A
    settled claim's shortfall invoice is not selected here: it is exported
    with its settlement (Phase 376, ``settlements_in_range``).
    """
    _check_range(from_day, to_day)
    with get_connection(db_path) as conn:
        rows = [dict(r) for r in conn.execute(
            """SELECT i.*, c.name AS customer_name, c.email AS customer_email
                 FROM invoices i
                 JOIN work_orders wo ON wo.id = i.work_order_id
                 JOIN customers c ON c.id = i.customer_id
                WHERE wo.shop_id = ? AND i.status != 'cancelled'
                  AND i.shortfall_claim_id IS NULL
                  AND i.issued_at IS NOT NULL
                  AND datetime(i.issued_at) >= ? AND datetime(i.issued_at) < ?
                ORDER BY datetime(i.issued_at), i.id""",
            (shop_id, *_day_window(from_day, to_day)),
        ).fetchall()]
        exported = {r[0] for r in conn.execute(
            """SELECT aei.invoice_id FROM accounting_export_invoices aei
                 JOIN accounting_exports ae ON ae.id = aei.export_id
                WHERE ae.target = ?""",
            (key,),
        ).fetchall()}
        kept: list[dict] = []
        skipped: list[str] = []
        for inv in rows:
            if inv["id"] in exported and not include_exported:
                skipped.append(inv["invoice_number"])
                continue
            inv["lines"] = [dict(r) for r in conn.execute(
                "SELECT * FROM invoice_line_items WHERE invoice_id = ? "
                "ORDER BY sort_order, id",
                (inv["id"],),
            ).fetchall()]
            inv["claims"] = [dict(r) for r in conn.execute(
                "SELECT c.*, w.provider FROM warranty_claims c "
                "JOIN warranties w ON w.id = c.warranty_id "
                "WHERE c.invoice_id = ? AND c.amount_claimed_cents > 0 ORDER BY c.id",
                (inv["id"],),
            ).fetchall()]
            for claim in inv["claims"]:
                claim["lines"] = [dict(r) for r in conn.execute(
                    "SELECT * FROM warranty_claim_lines WHERE claim_id = ? ORDER BY id",
                    (claim["id"],),
                ).fetchall()]
            kept.append(inv)
    return kept, skipped


def settlements_in_range(
    shop_id: int, from_day: str, to_day: str, key: str,
    include_exported: bool = False, db_path: Optional[str] = None,
) -> tuple[list[dict], list[str]]:
    """The shop's claims settled on a shop's day in the range (Phase 376).

    Each carries its provider, its claim number's invoice, its lines, whether
    an earlier export to the same target carried the claim
    (``claim_exported``) and, when billed to the customer, the shortfall
    invoice with its lines (``shortfall_invoice``). Returns them, and labels
    for those an earlier export to the target carried (unless
    ``include_exported``).
    """
    _check_range(from_day, to_day)
    with get_connection(db_path) as conn:
        rows = [dict(r) for r in conn.execute(
            """SELECT c.*, w.provider,
                      i.invoice_number AS claim_invoice_number,
                      i.issued_at AS claim_issued_at,
                      i.currency AS currency,
                      i.taxed_line_types AS taxed_line_types
                 FROM warranty_claims c
                 JOIN warranties w ON w.id = c.warranty_id
                 JOIN work_orders wo ON wo.id = c.work_order_id
                 JOIN invoices i ON i.id = c.invoice_id
                WHERE wo.shop_id = ? AND c.settlement IS NOT NULL
                  AND datetime(c.settled_at) >= ? AND datetime(c.settled_at) < ?
                ORDER BY datetime(c.settled_at), c.id""",
            (shop_id, *_day_window(from_day, to_day)),
        ).fetchall()]
        settled = {r[0] for r in conn.execute(
            """SELECT aes.claim_id FROM accounting_export_settlements aes
                 JOIN accounting_exports ae ON ae.id = aes.export_id
                WHERE ae.target = ?""",
            (key,),
        ).fetchall()}
        claims_in_books = {r[0] for r in conn.execute(
            """SELECT aec.claim_id FROM accounting_export_claims aec
                 JOIN accounting_exports ae ON ae.id = aec.export_id
                WHERE ae.target = ?""",
            (key,),
        ).fetchall()}
        kept: list[dict] = []
        skipped: list[str] = []
        for s in rows:
            if s["id"] in settled and not include_exported:
                skipped.append(f"claim #{s['id']}'s settlement")
                continue
            s["claim_exported"] = s["id"] in claims_in_books
            s["lines"] = [dict(r) for r in conn.execute(
                "SELECT * FROM warranty_claim_lines WHERE claim_id = ? ORDER BY id",
                (s["id"],),
            ).fetchall()]
            s["shortfall_invoice"] = None
            if s["shortfall_invoice_id"] is not None:
                inv = dict(conn.execute(
                    """SELECT i.*, c.name AS customer_name, c.email AS customer_email
                         FROM invoices i JOIN customers c ON c.id = i.customer_id
                        WHERE i.id = ?""",
                    (s["shortfall_invoice_id"],),
                ).fetchone())
                inv["lines"] = [dict(r) for r in conn.execute(
                    "SELECT * FROM invoice_line_items WHERE invoice_id = ? "
                    "ORDER BY sort_order, id",
                    (inv["id"],),
                ).fetchall()]
                inv["claims"] = []
                s["shortfall_invoice"] = inv
            kept.append(s)
    return kept, skipped


def _claim_number(inv: dict, claim: dict) -> str:
    return f"{inv['invoice_number']}-W{claim['id']}"


def _require_provider(inv: dict, claim: dict) -> str:
    provider = (claim.get("provider") or "").strip()
    if not provider:
        raise ExportError(
            f"warranty claim #{claim['id']} on invoice {inv['invoice_number']} has no "
            f"provider on record, so its receivable has no one to name; record it with "
            f"`motodiag shop warranty update {claim['warranty_id']} --provider NAME`"
        )
    return provider


def _claim_by_kind(claim: dict) -> dict[str, int]:
    by_kind: dict[str, int] = {}
    for line in claim["lines"]:
        by_kind[line["line_type"]] = by_kind.get(line["line_type"], 0) + int(
            line["amount_cents"])
    return by_kind


def _require_mapping(mapping: dict[str, dict], needed: list[str], key: str,
                     shop_id: int, need_tax_type: bool = False) -> None:
    missing = [k for k in needed if k not in mapping]
    if missing:
        first = missing[0]
        raise ExportError(
            f"no {_target_name(key)} account is mapped for "
            f"{', '.join(KIND_LABELS[k] for k in missing)}; run `motodiag shop "
            f"accounting map set --shop {shop_id} --target {_target_name(key)} "
            f"--kind {first} --account NAME"
            + (" --tax-type NAME" if need_tax_type else "") + "`"
        )
    if need_tax_type:
        untaxed = [k for k in needed if not mapping[k]["tax_type"]]
        if untaxed:
            raise ExportError(
                "Xero needs a tax rate name on every mapped kind; none is set for "
                f"{', '.join(KIND_LABELS[k] for k in untaxed)} (add --tax-type, "
                "for example --tax-type \"Tax Exempt\")"
            )


# ---------------------------------------------------------------------------
# QuickBooks Online: journal entries
# ---------------------------------------------------------------------------


def quickbooks_journal_rows(invoices: list[dict], mapping: dict[str, dict],
                            shop_id: int, settlements: tuple = ()) -> list[dict]:
    """One balanced journal entry per invoice, then each settlement's.

    Debit the receivable for the invoice total, naming the customer; credit
    each line kind's total to its income account; credit the tax to the tax
    account. Refused when an entry would not balance to the cent. A
    settlement (Phase 376) credits the provider's receivable for the
    shortfall: billed, against the income and tax it re-bills to the
    customer, followed by the shortfall invoice's own entry; absorbed,
    against the absorbed account.
    """
    key = "quickbooks_online"
    needed = {"receivable"}
    billed = [s["shortfall_invoice"] for s in settlements if s["shortfall_invoice"]]
    for inv in list(invoices) + billed:
        needed |= {line["item_type"] for line in inv["lines"]}
        if _cents(inv["tax_amount"]):
            needed.add("tax")
        for claim in inv.get("claims", []):
            needed |= {line["line_type"] for line in claim["lines"]}
            if claim["tax_cents"]:
                needed.add("tax")
    if any(s["settlement"] == "absorb" for s in settlements):
        needed.add("absorbed")
    unknown = needed - set(KINDS)
    if unknown:
        raise ExportError(f"unknown line type(s): {', '.join(sorted(unknown))}")
    _require_mapping(mapping, [k for k in KINDS if k in needed], key, shop_id)

    rows: list[dict] = []
    for inv in invoices:
        rows += _quickbooks_invoice_rows(inv, mapping)
    for settlement in settlements:
        rows += _quickbooks_settlement_rows(settlement, mapping)
    return rows


def _quickbooks_invoice_rows(inv: dict, mapping: dict[str, dict]) -> list[dict]:
    """An invoice's journal entry, then its claims' (Phase 373)."""
    rows: list[dict] = []
    claim_rows = _quickbooks_claim_rows(inv, mapping)
    if not inv["lines"] and _cents(inv["total"]) == 0:
        return claim_rows  # Phase 373: every line covered; the customer owes nothing
    number, when = inv["invoice_number"], _us_date(inv["issued_at"])
    total = _cents(inv["total"])
    tax = _cents(inv["tax_amount"])
    by_kind: dict[str, int] = {}
    for line in inv["lines"]:
        by_kind[line["item_type"]] = by_kind.get(line["item_type"], 0) + _cents(
            line["line_total"])
    credits = sum(by_kind.values()) + tax
    if credits != total:
        raise ExportError(
            f"invoice {number} does not balance: its lines and tax come to "
            f"{_money(credits)}, its total is {_money(total)}"
        )
    rows.append({
        "Journal No.": number, "Journal Date": when,
        "Account Name": mapping["receivable"]["account"],
        "Debits": _money(total), "Credits": "",
        "Journal/Description": f"Invoice {number}",
        "Name": inv["customer_name"],
    })
    for kind in LINE_KINDS:
        if kind in by_kind:
            rows.append({
                "Journal No.": number, "Journal Date": when,
                "Account Name": mapping[kind]["account"],
                "Debits": "", "Credits": _money(by_kind[kind]),
                "Journal/Description": f"Invoice {number}: {KIND_LABELS[kind]}",
                "Name": "",
            })
    if tax:
        rows.append({
            "Journal No.": number, "Journal Date": when,
            "Account Name": mapping["tax"]["account"],
            "Debits": "", "Credits": _money(tax),
            "Journal/Description": f"Invoice {number}: sales tax",
            "Name": "",
        })
    return rows + claim_rows


def _settlement_number(s: dict) -> str:
    """The credit's number: the claim's own number (373), then ``-CR``."""
    return f"{s['claim_invoice_number']}-W{s['id']}-CR"


def _settlement_shares(s: dict) -> tuple[list[dict], list[int], int]:
    """A billed settlement's shortfall lines, each line's amount in cents, and
    the claim's tax inside the shortfall: the shortfall less the shortfall
    invoice's subtotal (373 split the pre-tax share over the lines)."""
    inv = s["shortfall_invoice"]
    if inv["status"] == "cancelled":
        raise ExportError(
            f"claim #{s['id']}'s shortfall invoice {inv['invoice_number']} is void, so "
            f"its settlement cannot be booked against the customer"
        )
    amounts = [_cents(line["line_total"]) for line in inv["lines"]]
    tax_share = int(s["shortfall_cents"]) - sum(amounts)
    if tax_share < 0 or tax_share > int(s["tax_cents"] or 0):
        raise ExportError(
            f"claim #{s['id']}'s settlement does not balance: its shortfall is "
            f"{_money(int(s['shortfall_cents']))} and its shortfall invoice's lines "
            f"{_money(sum(amounts))}"
        )
    return inv["lines"], amounts, tax_share


def _quickbooks_settlement_rows(s: dict, mapping: dict[str, dict]) -> list[dict]:
    """A settlement's journal entry (Phase 376), and for a billed one the
    shortfall invoice's own entry after it."""
    provider = _require_provider({"invoice_number": s["claim_invoice_number"]}, s)
    number, when = _settlement_number(s), _us_date(s["settled_at"])
    shortfall = int(s["shortfall_cents"])
    claim = f"Warranty claim #{s['id']} on invoice {s['claim_invoice_number']}"
    rows: list[dict] = []
    if s["settlement"] == "absorb":
        rows.append({
            "Journal No.": number, "Journal Date": when,
            "Account Name": mapping["absorbed"]["account"],
            "Debits": _money(shortfall), "Credits": "",
            "Journal/Description": f"{claim}: shortfall absorbed by the shop", "Name": "",
        })
    else:
        lines, amounts, tax_share = _settlement_shares(s)
        by_kind: dict[str, int] = {}
        for line, amount in zip(lines, amounts):
            by_kind[line["item_type"]] = by_kind.get(line["item_type"], 0) + amount
        billed = s["shortfall_invoice"]["invoice_number"]
        for kind in LINE_KINDS:
            if kind in by_kind:
                rows.append({
                    "Journal No.": number, "Journal Date": when,
                    "Account Name": mapping[kind]["account"],
                    "Debits": _money(by_kind[kind]), "Credits": "",
                    "Journal/Description": f"{claim}: {KIND_LABELS[kind]} re-billed to "
                                           f"the customer on {billed}",
                    "Name": "",
                })
        if tax_share:
            rows.append({
                "Journal No.": number, "Journal Date": when,
                "Account Name": mapping["tax"]["account"],
                "Debits": _money(tax_share), "Credits": "",
                "Journal/Description": f"{claim}: the claim's sales tax on the shortfall",
                "Name": "",
            })
    rows.append({
        "Journal No.": number, "Journal Date": when,
        "Account Name": mapping["receivable"]["account"],
        "Debits": "", "Credits": _money(shortfall),
        "Journal/Description": f"{claim}: shortfall, not paid by {provider}",
        "Name": provider,
    })
    if s["shortfall_invoice"] is not None:
        rows += _quickbooks_invoice_rows(s["shortfall_invoice"], mapping)
    return rows


# ---------------------------------------------------------------------------
# Xero: sales invoices
# ---------------------------------------------------------------------------


def _quickbooks_claim_rows(inv: dict, mapping: dict[str, dict]) -> list[dict]:
    """A journal entry per warranty claim on the invoice (Phase 373): debit
    the receivable for the amount claimed, in the provider's name; credit the
    covered work's income and the claim's tax."""
    rows: list[dict] = []
    when = _us_date(inv["issued_at"])
    for claim in inv.get("claims", []):
        number = _claim_number(inv, claim)
        provider = _require_provider(inv, claim)
        by_kind = _claim_by_kind(claim)
        total, tax = int(claim["amount_claimed_cents"]), int(claim["tax_cents"])
        if sum(by_kind.values()) + tax != total:
            raise ExportError(
                f"warranty claim {number} does not balance: its lines and tax come "
                f"to {_money(sum(by_kind.values()) + tax)}, it claims {_money(total)}"
            )
        description = f"Warranty claim #{claim['id']} on invoice {inv['invoice_number']}"
        rows.append({
            "Journal No.": number, "Journal Date": when,
            "Account Name": mapping["receivable"]["account"],
            "Debits": _money(total), "Credits": "",
            "Journal/Description": description, "Name": provider,
        })
        for kind in LINE_KINDS:
            if kind in by_kind:
                rows.append({
                    "Journal No.": number, "Journal Date": when,
                    "Account Name": mapping[kind]["account"],
                    "Debits": "", "Credits": _money(by_kind[kind]),
                    "Journal/Description": f"{description}: {KIND_LABELS[kind]}",
                    "Name": "",
                })
        if tax:
            rows.append({
                "Journal No.": number, "Journal Date": when,
                "Account Name": mapping["tax"]["account"],
                "Debits": "", "Credits": _money(tax),
                "Journal/Description": f"{description}: sales tax", "Name": "",
            })
    return rows


def spread_tax(line_cents: list[int], tax_cents: int) -> list[int]:
    """The invoice's tax over its lines in proportion to their amounts.

    Each share is rounded down, and the remainder goes on the last line, so
    the shares sum to ``tax_cents`` exactly.
    """
    total = sum(line_cents)
    if not line_cents:
        return []
    if total == 0:
        return [0] * (len(line_cents) - 1) + [tax_cents]
    shares = [tax_cents * c // total for c in line_cents]
    shares[-1] += tax_cents - sum(shares)
    return shares


def _taxed_types(inv: dict) -> Optional[set[str]]:
    """The line types the invoice's tax fell on, as it recorded them (Phase
    281), or None for an invoice made before that record, whose tax fell on
    every line."""
    recorded = inv.get("taxed_line_types")
    if recorded is None:
        return None
    return {t for t in recorded.split(",") if t and t != "none"}


def _line_taxes(inv: dict) -> list[int]:
    """Each line's share of the invoice's tax: only lines of a taxed type
    share it, in proportion to their amounts."""
    lines = inv["lines"]
    tax = _cents(inv["tax_amount"])
    taxed = _taxed_types(inv)
    on = [i for i, line in enumerate(lines)
          if taxed is None or line["item_type"] in taxed]
    if tax and not on:
        raise ExportError(
            f"invoice {inv['invoice_number']} carries tax but no line of a taxed "
            f"type ({', '.join(sorted(taxed or ())) or 'none'})"
        )
    shares = [0] * len(lines)
    for i, share in zip(on, spread_tax([_cents(lines[i]["line_total"]) for i in on], tax)):
        shares[i] = share
    return shares


def _quantity(value) -> str:
    q = float(value)
    return f"{q:.4f}".rstrip("0").rstrip(".")


def xero_rows(invoices: list[dict], mapping: dict[str, dict],
              shop_id: int, settlements: tuple = ()) -> list[dict]:
    """One row per invoice line, tax-exclusive, with its share of the tax.
    A billed settlement's shortfall invoice (Phase 376) follows the invoices,
    as an ordinary invoice to the customer."""
    key = "xero"
    billed = [s["shortfall_invoice"] for s in settlements if s["shortfall_invoice"]]
    kinds = {line["item_type"] for inv in list(invoices) + billed for line in inv["lines"]}
    kinds |= {line["line_type"] for inv in invoices for claim in inv.get("claims", [])
              for line in claim["lines"]}
    needed = sorted(kinds, key=lambda k: KINDS.index(k) if k in KINDS else 99)
    unknown = [k for k in needed if k not in KINDS]
    if unknown:
        raise ExportError(f"unknown line type(s): {', '.join(unknown)}")
    _require_mapping(mapping, needed, key, shop_id, need_tax_type=True)

    rows: list[dict] = []
    for inv in list(invoices) + billed:
        rows += _xero_invoice_rows(inv, mapping)
    return rows


def _xero_invoice_rows(inv: dict, mapping: dict[str, dict]) -> list[dict]:
    """An invoice's rows, then its claims' (Phase 373)."""
    claim_rows = _xero_claim_rows(inv, mapping)
    if not inv["lines"] and _cents(inv["total"]) == 0:
        return claim_rows  # Phase 373: every line covered; the customer owes nothing
    if not inv["lines"]:
        raise ExportError(f"invoice {inv['invoice_number']} has no lines")
    rows: list[dict] = []
    for line, tax in zip(inv["lines"], _line_taxes(inv)):
        account = mapping[line["item_type"]]
        row = {c: "" for c in XERO_COLUMNS}
        row.update({
            "ContactName": inv["customer_name"],
            "EmailAddress": inv["customer_email"] or "",
            "InvoiceNumber": inv["invoice_number"],
            "InvoiceDate": _us_date(inv["issued_at"]),
            "DueDate": _us_due_date(inv["due_at"]),
            "Description": line["description"],
            "Quantity": _quantity(line["quantity"]),
            "UnitAmount": _money(_cents(line["unit_price"])),
            "AccountCode": account["account"],
            "TaxType": account["tax_type"],
            "TaxAmount": _money(tax),
            "Currency": inv["currency"] or "",
        })
        rows.append(row)
    return rows + claim_rows


@dataclass
class CreditNote:
    """What one credit note should show in Xero, for the CLI to print."""
    number: str
    credit_cents: int
    expected_tax_cents: int
    absorbed: bool


def xero_credit_note_rows(settlements: list[dict], mapping: dict[str, dict],
                          shop_id: int) -> tuple[list[dict], list[CreditNote]]:
    """A credit note to the provider per settlement (Phase 376), tax-inclusive.

    Billed: a line per shortfall line, each the negative of its amount plus
    its share of the claim's tax inside the shortfall, spread over the lines
    of the types the claim's invoice taxed. Absorbed: one line, the whole
    shortfall to the absorbed account, whose mapped rate should carry no tax
    (2A: the tax charged stays owed). Every credit note's lines sum to minus
    its shortfall.
    """
    needed = set()
    for s in settlements:
        if s["settlement"] == "absorb":
            needed.add("absorbed")
        else:
            needed |= {line["item_type"] for line in s["shortfall_invoice"]["lines"]}
    _require_mapping(mapping, [k for k in KINDS if k in needed], "xero", shop_id,
                     need_tax_type=True)
    rows: list[dict] = []
    notes: list[CreditNote] = []
    for s in settlements:
        provider = _require_provider({"invoice_number": s["claim_invoice_number"]}, s)
        number, shortfall = _settlement_number(s), int(s["shortfall_cents"])
        if s["settlement"] == "absorb":
            parts = [("absorbed", f"Warranty claim #{s['id']}: shortfall absorbed by the "
                                  f"shop", shortfall)]
            tax_share = 0
        else:
            lines, amounts, tax_share = _settlement_shares(s)
            taxed = _taxed_types({"taxed_line_types": s["taxed_line_types"]})
            on = [i for i, line in enumerate(lines)
                  if taxed is None or line["item_type"] in taxed]
            if tax_share and not on:
                raise ExportError(f"credit note {number} carries tax but no line of a "
                                  f"taxed type")
            shares = [0] * len(lines)
            for i, share in zip(on, spread_tax([amounts[i] for i in on], tax_share)):
                shares[i] = share
            parts = [(line["item_type"], line["description"], amount + share)
                     for line, amount, share in zip(lines, amounts, shares)]
        for kind, description, amount in parts:
            row = {c: "" for c in XERO_CREDIT_NOTE_COLUMNS}
            row.update({
                "ContactName": provider,
                "InvoiceNumber": number,
                "Reference": f"{s['claim_invoice_number']}-W{s['id']}",
                "InvoiceDate": _us_date(s["settled_at"]),
                "DueDate": _us_date(s["settled_at"]),
                "Description": description,
                "Quantity": "1",
                "UnitAmount": _money(-amount),
                "AccountCode": mapping[kind]["account"],
                "TaxType": mapping[kind]["tax_type"],
                "Currency": s["currency"] or "",
            })
            rows.append(row)
        notes.append(CreditNote(number, shortfall, tax_share, s["settlement"] == "absorb"))
    return rows, notes


def _xero_claim_rows(inv: dict, mapping: dict[str, dict]) -> list[dict]:
    """A sales invoice to the provider per warranty claim on the invoice
    (Phase 373): a row per covered line, the claim's tax on the lines of the
    types the invoice taxed."""
    rows: list[dict] = []
    taxed = _taxed_types(inv)
    for claim in inv.get("claims", []):
        provider = _require_provider(inv, claim)
        lines, tax = claim["lines"], int(claim["tax_cents"])
        on = [i for i, line in enumerate(lines)
              if taxed is None or line["line_type"] in taxed]
        if tax and not on:
            raise ExportError(f"warranty claim {_claim_number(inv, claim)} carries tax "
                              f"but no line of a taxed type")
        shares = [0] * len(lines)
        for i, share in zip(on, spread_tax([int(lines[i]["amount_cents"]) for i in on],
                                           tax)):
            shares[i] = share
        for line, share in zip(lines, shares):
            account = mapping[line["line_type"]]
            row = {c: "" for c in XERO_COLUMNS}
            row.update({
                "ContactName": provider,
                "InvoiceNumber": _claim_number(inv, claim),
                "InvoiceDate": _us_date(inv["issued_at"]),
                "DueDate": _us_due_date(inv["due_at"]),
                "Description": f"Warranty claim #{claim['id']}: {line['description']}",
                "Quantity": "1",
                "UnitAmount": _money(int(line["amount_cents"])),
                "AccountCode": account["account"],
                "TaxType": account["tax_type"],
                "TaxAmount": _money(share),
                "Currency": inv["currency"] or "",
            })
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Writing the file
# ---------------------------------------------------------------------------


@dataclass
class ExportResult:
    path: Path
    target: str
    invoice_count: int
    row_count: int
    sha256: str
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    claim_count: int = 0
    # Phase 376: settlements, every file written, and what each credit note
    # should show in Xero.
    settlement_count: int = 0
    files: list["ExportedFile"] = field(default_factory=list)
    credit_notes: list[CreditNote] = field(default_factory=list)
    settlement_notes: list[str] = field(default_factory=list)


@dataclass
class ExportedFile:
    path: Path
    holds: str  # journal_entries, invoices or credit_notes
    row_count: int
    sha256: str


FILE_LABELS = {"journal_entries": "journal entries", "invoices": "sales invoices",
               "credit_notes": "credit notes"}


def credit_notes_path(path: Path) -> Path:
    """Where a Xero export's credit notes go, beside its invoices file."""
    return path.with_name(f"{path.stem}_credit_notes{path.suffix or '.csv'}")


def _csv_bytes(columns: tuple[str, ...], rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(columns), lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _require_claims_in_books(settlements: list[dict], claim_ids: set[int],
                             target_key_: str) -> None:
    """D1 (Step 0): a settlement is booked only against a claim the target's
    books hold: exported to it before, or in this run."""
    for s in settlements:
        if not s["claim_exported"] and s["id"] not in claim_ids:
            raise ExportError(
                f"warranty claim #{s['id']} was settled on {local_day(s['settled_at'])}, "
                f"but the claim was never exported to {_target_name(target_key_)}; export "
                f"its invoice {s['claim_invoice_number']} first (issued "
                f"{local_day(s['claim_issued_at'])})"
            )


def _settlement_tax_notes(shop_id: int, settlements: list[dict],
                          db_path: Optional[str]) -> list[str]:
    """What an absorbed shortfall means for tax (2A), refusing one whose claim
    carried tax when the shop's jurisdiction has no reading on record."""
    notes: list[str] = []
    for s in settlements:
        if s["settlement"] != "absorb":
            continue
        tax = int(s["tax_cents"] or 0)
        if tax:
            day = date.fromisoformat(local_day(s["settled_at"]))
            try:
                rule = tax_mod.resolve_settlement_rule(shop_id, day, db_path=db_path)
            except tax_mod.TaxNotOnRecord as exc:
                raise ExportError("; ".join(exc.problems)) from exc
            notes.append(
                f"Claim #{s['id']}'s shortfall is absorbed: the {_money(tax)} of tax "
                f"charged on the claim stays owed ({rule.source_title}; a reading for "
                f"your accountant to confirm). It is written off with the shortfall.")
        elif any(line["line_type"] == "parts" for line in s["lines"]):
            notes.append(
                f"Claim #{s['id']}'s shortfall is absorbed and the claim carried no tax: "
                f"tax on the parts' cost may be due (finding F195); ask your accountant.")
    return notes


def export_file(
    shop_id: int, target: str, from_day: str, to_day: str, out_path: str,
    include_exported: bool = False, db_path: Optional[str] = None,
) -> ExportResult:
    """Write the export file(s) and record them. Refuses to overwrite a file.

    QuickBooks: one file of journal entries. Xero: the sales invoices at
    ``out_path`` and, when settlements credit a provider (Phase 376), the
    credit notes beside it (``credit_notes_path``); a file with no rows is
    not written.
    """
    key = target_key(target)
    path = Path(out_path)
    invoices, skipped = invoices_in_range(shop_id, from_day, to_day, key,
                                          include_exported, db_path=db_path)
    settlements, skipped_settlements = settlements_in_range(
        shop_id, from_day, to_day, key, include_exported, db_path=db_path)
    skipped += skipped_settlements
    if not invoices and not settlements:
        why = (f"; {len(skipped)} were exported before (add --include-exported "
               "to write them again)") if skipped else ""
        raise ExportError(
            f"no invoices to export for shop id={shop_id} from {from_day} to "
            f"{to_day}{why}")
    claim_ids = [c["id"] for inv in invoices for c in inv.get("claims", [])]
    _require_claims_in_books(settlements, set(claim_ids), key)
    settlement_notes = _settlement_tax_notes(shop_id, settlements, db_path)
    billed = [s["shortfall_invoice"] for s in settlements if s["shortfall_invoice"]]
    mapping = _mapping(shop_id, key, db_path)
    credit_notes: list[CreditNote] = []
    if key == "quickbooks_online":
        files = [("journal_entries", path, QBO_JOURNAL_COLUMNS,
                  quickbooks_journal_rows(invoices, mapping, shop_id, tuple(settlements)))]
        notes = [
            QBO_STATEMENT,
            "Dates are written MM/DD/YYYY; choose that format when QuickBooks asks.",
            "Import it in QuickBooks Online under Settings, Import data, Journal entries.",
        ]
        if settlements:
            notes.append(
                "Each warranty settlement's -CR journal credits the provider's "
                "receivable: apply it to the claim's journal in QuickBooks, under "
                "+ Create, Receive payment, the provider, the claim's journal under "
                "Outstanding Transactions and the -CR journal under Credits.")
    else:
        invoice_rows = xero_rows(invoices, mapping, shop_id, tuple(settlements))
        note_rows, credit_notes = xero_credit_note_rows(settlements, mapping, shop_id)
        files = []
        if invoices or billed:
            files.append(("invoices", path, XERO_COLUMNS, invoice_rows))
        if note_rows:
            files.append(("credit_notes", credit_notes_path(path),
                          XERO_CREDIT_NOTE_COLUMNS, note_rows))
        notes = [
            "Prices are tax exclusive; choose that when Xero asks. Each line "
            "carries its share of the invoice's tax in TaxAmount.",
            "Xero imports these as draft invoices, to approve there.",
        ] if invoices or billed else []
        if note_rows:
            notes.append(
                "The credit notes file is tax inclusive: choose that when Xero asks. "
                "Import it under Sales overview, the import icon. Xero imports them as "
                "drafts: check each one's tax against the line below, approve it, then "
                "allocate it to the provider's invoice named in its Reference.")
    for _, file_path, _, _ in files:
        if file_path.exists():
            raise ExportError(f"{file_path} already exists; choose another name")
    written: list[ExportedFile] = []
    for holds, file_path, columns, rows in files:
        data = _csv_bytes(columns, rows)
        file_path.write_bytes(data)
        written.append(ExportedFile(file_path, holds, len(rows),
                                    hashlib.sha256(data).hexdigest()))
    first = written[0]
    invoice_ids = [inv["id"] for inv in invoices] + [inv["id"] for inv in billed]
    with get_connection(db_path) as conn:
        export_id = conn.execute(
            """INSERT INTO accounting_exports
               (shop_id, target, period_from, period_to, file_name, file_sha256,
                invoice_count, exported_at, settlement_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (shop_id, key, from_day, to_day, str(first.path), first.sha256,
             len(invoice_ids), datetime.now(timezone.utc).isoformat(timespec="seconds"),
             len(settlements)),
        ).lastrowid
        conn.executemany(
            "INSERT INTO accounting_export_files (export_id, holds, file_name, "
            "file_sha256, row_count) VALUES (?, ?, ?, ?, ?)",
            [(export_id, f.holds, str(f.path), f.sha256, f.row_count) for f in written],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO accounting_export_invoices (export_id, invoice_id) "
            "VALUES (?, ?)",
            [(export_id, invoice_id) for invoice_id in invoice_ids],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO accounting_export_claims (export_id, claim_id) "
            "VALUES (?, ?)",
            [(export_id, claim_id) for claim_id in claim_ids],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO accounting_export_settlements (export_id, claim_id) "
            "VALUES (?, ?)",
            [(export_id, s["id"]) for s in settlements],
        )
    return ExportResult(first.path, key, len(invoice_ids), first.row_count, first.sha256,
                        skipped, notes, len(claim_ids), len(settlements), written,
                        credit_notes, settlement_notes)


def list_exports(shop_id: int, db_path: Optional[str] = None) -> list[dict]:
    """The shop's exports, newest first, each with its ``files`` (Phase 376)."""
    with get_connection(db_path) as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM accounting_exports WHERE shop_id = ? ORDER BY id DESC",
            (shop_id,),
        ).fetchall()]
        for r in rows:
            r["files"] = [dict(f) for f in conn.execute(
                "SELECT * FROM accounting_export_files WHERE export_id = ? ORDER BY rowid",
                (r["id"],),
            ).fetchall()]
    return rows
