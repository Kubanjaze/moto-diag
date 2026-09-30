"""Accounting export files: QuickBooks Online journal entries and Xero sales invoices.

Both are built from ``invoices`` and ``invoice_line_items`` (which
``shop/invoicing.py`` writes) and the shop's own account names
(``accounting_accounts``). Each format follows its vendor's import page as
read on 2026-09-29; the pages are quoted in
``docs/phases/completed/275_format_sources.md``. Neither file has been
tried in a real QuickBooks or Xero company.

The files are written locally. Nothing is uploaded.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from motodiag.core.database import get_connection

# The command-line name of each target, and the name stored.
TARGETS: dict[str, str] = {"quickbooks-online": "quickbooks_online", "xero": "xero"}

LINE_KINDS: tuple[str, ...] = ("labor", "parts", "diagnostic", "misc")
KINDS: tuple[str, ...] = LINE_KINDS + ("tax", "receivable")

KIND_LABELS = {
    "labor": "labour", "parts": "parts", "diagnostic": "diagnostic",
    "misc": "shop supplies", "tax": "sales tax", "receivable": "accounts receivable",
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


def _us_date(value: Optional[str]) -> str:
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


def invoices_in_range(
    shop_id: int, from_day: str, to_day: str, key: str,
    include_exported: bool = False, db_path: Optional[str] = None,
) -> tuple[list[dict], list[str]]:
    """The shop's invoices issued in the range, not cancelled, with their lines.

    A shop's invoice is one whose work order is at the shop. Returns the
    invoices, and the numbers of those left out because an earlier export to
    the same target carried them (unless ``include_exported``).
    """
    _check_range(from_day, to_day)
    with get_connection(db_path) as conn:
        rows = [dict(r) for r in conn.execute(
            """SELECT i.*, c.name AS customer_name, c.email AS customer_email
                 FROM invoices i
                 JOIN work_orders wo ON wo.id = i.work_order_id
                 JOIN customers c ON c.id = i.customer_id
                WHERE wo.shop_id = ? AND i.status != 'cancelled'
                  AND i.issued_at IS NOT NULL
                  AND substr(i.issued_at, 1, 10) BETWEEN ? AND ?
                ORDER BY i.issued_at, i.id""",
            (shop_id, from_day, to_day),
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
            kept.append(inv)
    return kept, skipped


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
                            shop_id: int) -> list[dict]:
    """One balanced journal entry per invoice.

    Debit the receivable for the invoice total, naming the customer; credit
    each line kind's total to its income account; credit the tax to the tax
    account. Refused when an entry would not balance to the cent.
    """
    key = "quickbooks_online"
    needed = {"receivable"}
    for inv in invoices:
        needed |= {line["item_type"] for line in inv["lines"]}
        if _cents(inv["tax_amount"]):
            needed.add("tax")
    unknown = needed - set(KINDS)
    if unknown:
        raise ExportError(f"unknown line type(s): {', '.join(sorted(unknown))}")
    _require_mapping(mapping, [k for k in KINDS if k in needed], key, shop_id)

    rows: list[dict] = []
    for inv in invoices:
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
    return rows


# ---------------------------------------------------------------------------
# Xero: sales invoices
# ---------------------------------------------------------------------------


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


def _quantity(value) -> str:
    q = float(value)
    return f"{q:.4f}".rstrip("0").rstrip(".")


def xero_rows(invoices: list[dict], mapping: dict[str, dict],
              shop_id: int) -> list[dict]:
    """One row per invoice line, tax-exclusive, with its share of the tax."""
    key = "xero"
    needed = sorted({line["item_type"] for inv in invoices for line in inv["lines"]},
                    key=lambda k: KINDS.index(k) if k in KINDS else 99)
    unknown = [k for k in needed if k not in KINDS]
    if unknown:
        raise ExportError(f"unknown line type(s): {', '.join(unknown)}")
    _require_mapping(mapping, needed, key, shop_id, need_tax_type=True)

    rows: list[dict] = []
    for inv in invoices:
        if not inv["lines"]:
            raise ExportError(f"invoice {inv['invoice_number']} has no lines")
        amounts = [_cents(line["line_total"]) for line in inv["lines"]]
        taxes = spread_tax(amounts, _cents(inv["tax_amount"]))
        for line, tax in zip(inv["lines"], taxes):
            account = mapping[line["item_type"]]
            row = {c: "" for c in XERO_COLUMNS}
            row.update({
                "ContactName": inv["customer_name"],
                "EmailAddress": inv["customer_email"] or "",
                "InvoiceNumber": inv["invoice_number"],
                "InvoiceDate": _us_date(inv["issued_at"]),
                "DueDate": _us_date(inv["due_at"]),
                "Description": line["description"],
                "Quantity": _quantity(line["quantity"]),
                "UnitAmount": _money(_cents(line["unit_price"])),
                "AccountCode": account["account"],
                "TaxType": account["tax_type"],
                "TaxAmount": _money(tax),
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


def export_file(
    shop_id: int, target: str, from_day: str, to_day: str, out_path: str,
    include_exported: bool = False, db_path: Optional[str] = None,
) -> ExportResult:
    """Write the export file and record it. Refuses to overwrite a file."""
    key = target_key(target)
    path = Path(out_path)
    if path.exists():
        raise ExportError(f"{path} already exists; choose another name")
    invoices, skipped = invoices_in_range(shop_id, from_day, to_day, key,
                                          include_exported, db_path=db_path)
    if not invoices:
        why = (f"; {len(skipped)} were exported before (add --include-exported "
               "to write them again)") if skipped else ""
        raise ExportError(
            f"no invoices to export for shop id={shop_id} from {from_day} to "
            f"{to_day}{why}")
    mapping = _mapping(shop_id, key, db_path)
    if key == "quickbooks_online":
        columns = QBO_JOURNAL_COLUMNS
        rows = quickbooks_journal_rows(invoices, mapping, shop_id)
        notes = [
            QBO_STATEMENT,
            "Dates are written MM/DD/YYYY; choose that format when QuickBooks asks.",
            "Import it in QuickBooks Online under Settings, Import data, Journal entries.",
        ]
    else:
        columns = XERO_COLUMNS
        rows = xero_rows(invoices, mapping, shop_id)
        notes = [
            "Prices are tax exclusive; choose that when Xero asks. Each line "
            "carries its share of the invoice's tax in TaxAmount.",
            "Xero imports these as draft invoices, to approve there.",
        ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(columns), lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    data = buffer.getvalue().encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    with get_connection(db_path) as conn:
        export_id = conn.execute(
            """INSERT INTO accounting_exports
               (shop_id, target, period_from, period_to, file_name, file_sha256,
                invoice_count, exported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (shop_id, key, from_day, to_day, str(path), digest, len(invoices),
             datetime.now(timezone.utc).isoformat(timespec="seconds")),
        ).lastrowid
        conn.executemany(
            "INSERT OR IGNORE INTO accounting_export_invoices (export_id, invoice_id) "
            "VALUES (?, ?)",
            [(export_id, inv["id"]) for inv in invoices],
        )
    return ExportResult(path, key, len(invoices), len(rows), digest, skipped, notes)


def list_exports(shop_id: int, db_path: Optional[str] = None) -> list[dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM accounting_exports WHERE shop_id = ? ORDER BY id DESC",
            (shop_id,),
        ).fetchall()
    return [dict(r) for r in rows]
