"""Record a shop's sales tax for tests that generate invoices (Phase 281).

Since F184 closed, an invoice takes its tax only from the shop's tax
jurisdiction on record and is refused without it. Tests written before that,
which relied on a tax rate of zero by default, now state the rate: a test
jurisdiction, entered as the shop's own, valid 2000-01-01 to 2099-12-31 so no
test depends on today's date, with every line type taxable (the old
behaviour: the rate applied to the whole subtotal).
"""

from __future__ import annotations

from motodiag.accounting import tax

TEST_CODE = "ZZ-T"


def record_tax_for_wo(db_path: str, wo_id: int, rate: float = 0.0) -> None:
    """`record_tax` for the shop a work order belongs to."""
    from motodiag.core.database import get_connection

    with get_connection(db_path) as conn:
        shop_id = conn.execute("SELECT shop_id FROM work_orders WHERE id = ?",
                               (wo_id,)).fetchone()[0]
    record_tax(db_path, int(shop_id), rate=rate)


def record_tax(db_path: str, shop_id: int, rate: float = 0.0,
               taxable: tuple[str, ...] = tax.LINE_TYPES) -> None:
    if tax.get_jurisdiction(TEST_CODE, db_path=db_path) is None:
        tax.add_jurisdiction(TEST_CODE, "Test jurisdiction", "USD", db_path=db_path)
    tax.set_shop_jurisdiction(shop_id, TEST_CODE, db_path=db_path)
    tax.set_shop_rate(shop_id, rate, "2000-01-01", "2099-12-31",
                      "Test fixture, not a real rate", "2026-09-30", db_path=db_path)
    for line_type in tax.LINE_TYPES:
        tax.set_shop_rule(shop_id, line_type, line_type in taxable, "2000-01-01",
                          "2099-12-31", "Test fixture, not a real rule", "2026-09-30",
                          db_path=db_path)
