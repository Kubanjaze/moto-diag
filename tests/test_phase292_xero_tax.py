"""Phase 292, bug fix #1 — the Xero file spreads an invoice's tax over its taxed lines only.

Since Phase 281 an invoice's tax falls on some line types only, and the
invoice records which (``taxed_line_types``). The Xero rows spread the tax
over every line, so on a Massachusetts invoice the untaxed labour row
carried most of the tax (Gate 16's Step 0, H1). An invoice made before 281
has no record and keeps the old spread over every line.
"""

from __future__ import annotations

import pytest

from motodiag.accounting import export as acct_export

MAPPING = {
    kind: {"account": code, "tax_type": "Tax on Sales (6.25%)"}
    for kind, code in (("labor", "200"), ("parts", "210"), ("diagnostic", "220"),
                       ("misc", "230"))
}


def _line(kind: str, cents: int, qty: float = 1.0) -> dict:
    return {"item_type": kind, "description": kind, "quantity": qty,
            "unit_price": cents / qty / 100, "line_total": cents / 100}


def _invoice(lines: list[dict], tax_cents: int, taxed) -> dict:
    return {"invoice_number": "INV-T", "customer_name": "Dana Rider",
            "customer_email": None, "issued_at": "2026-10-15T16:00:00+00:00",
            "due_at": None, "currency": "USD", "tax_amount": tax_cents / 100,
            "taxed_line_types": taxed, "lines": lines}


def _taxes(inv: dict) -> list[int]:
    rows = acct_export.xero_rows([inv], MAPPING, shop_id=1)
    return [int(r["TaxAmount"].replace(".", "")) for r in rows]


class TestTheTaxFollowsTheTaxedLines:
    def test_a_massachusetts_invoice_puts_no_tax_on_labour(self):
        """Labour 180.00 not taxed, parts 99.98 taxed at 6.25%: 6.25 of tax."""
        inv = _invoice([_line("labor", 18000, 1.5), _line("parts", 9998, 2.0)], 625,
                       "parts")
        assert _taxes(inv) == [0, 625]

    def test_several_taxed_lines_share_the_tax_and_the_untaxed_get_none(self):
        inv = _invoice([_line("labor", 18000), _line("parts", 4000),
                        _line("diagnostic", 5000), _line("parts", 6000)], 625, "parts")
        assert _taxes(inv) == [0, 250, 0, 375]

    def test_two_taxed_types_share_it_in_proportion(self):
        inv = _invoice([_line("labor", 10000), _line("parts", 10000),
                        _line("diagnostic", 5000)], 1250, "labor,parts")
        assert _taxes(inv) == [625, 625, 0]

    def test_an_invoice_made_before_the_record_keeps_the_spread_over_every_line(self):
        inv = _invoice([_line("labor", 10000), _line("parts", 10000)], 100, None)
        assert _taxes(inv) == [50, 50]

    def test_an_invoice_with_nothing_taxed_has_no_tax_on_any_line(self):
        inv = _invoice([_line("labor", 10000), _line("diagnostic", 5000)], 0, "none")
        assert _taxes(inv) == [0, 0]

    def test_tax_with_no_line_of_a_taxed_type_is_refused(self):
        inv = _invoice([_line("labor", 10000)], 625, "parts")
        with pytest.raises(acct_export.ExportError, match="no line of a taxed type"):
            acct_export.xero_rows([inv], MAPPING, shop_id=1)

    @pytest.mark.parametrize("taxed", [None, "parts", "labor,parts", "none"])
    def test_the_lines_always_carry_exactly_the_invoices_tax(self, taxed):
        tax = 0 if taxed == "none" else 777
        inv = _invoice([_line("labor", 12345), _line("parts", 6789),
                        _line("parts", 1)], tax, taxed)
        assert sum(_taxes(inv)) == tax
