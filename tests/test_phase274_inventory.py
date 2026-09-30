"""Phase 274 — row 279, parts inventory with reorder points and local POs.

Everything through `motodiag shop inventory …` on a scratch database.
Nothing is sent anywhere: a PO is drafted, printed, and its status is what
the user records.
"""

from __future__ import annotations

import json

import pytest

from support.phase274 import new_db, ok, refused, seed_shop, sql


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    seed_shop(path, "Reyes Moto")
    ok(path, "shop", "inventory", "vendor", "add", "--name", "Acme Parts",
       "--email", "orders@acme.example", "--terms", "Net 30")
    ok(path, "shop", "inventory", "vendor", "add", "--name", "Moto Supply")
    return path


def _item(db, sku, qty, point, reorder_qty=0, vendor=None, cost=0):
    args = ["shop", "inventory", "add", "--sku", sku, "--name", f"Part {sku}",
            "--qty", qty, "--reorder-point", point, "--reorder-qty", reorder_qty,
            "--unit-cost-cents", cost]
    if vendor:
        args += ["--vendor", vendor]
    ok(db, *args)


def _stock(db, sku):
    return sql(db, "SELECT quantity_on_hand FROM inventory_items WHERE sku = ?", (sku,))[0][0]


class TestStock:
    def test_add_list_show_and_adjust(self, db):
        _item(db, "OF-1", 6, 4, 10, "Acme Parts", 425)
        assert "OF-1" in ok(db, "shop", "inventory", "list")
        shown = json.loads(ok(db, "shop", "inventory", "show", "OF-1", "--json"))
        assert (shown["quantity_on_hand"], shown["reorder_point"],
                shown["reorder_quantity"], shown["unit_cost"]) == (6, 4, 10, 4.25)
        out = ok(db, "shop", "inventory", "adjust", "OF-1", "--by", "-2")
        assert "OF-1: 4 on hand" in out and "at or below its reorder point" in out
        assert _stock(db, "OF-1") == 4

    def test_stock_cannot_go_below_zero(self, db):
        _item(db, "OF-1", 1, 0)
        assert "cannot go down by 2" in refused(db, "shop", "inventory", "adjust",
                                                "OF-1", "--by", "-2")
        assert _stock(db, "OF-1") == 1

    def test_low_lists_only_items_at_or_below_their_point(self, db):
        _item(db, "A", 4, 4)      # at the point
        _item(db, "B", 5, 4)      # above
        _item(db, "C", 0, 0)      # no point: never due
        low = json.loads(ok(db, "shop", "inventory", "list", "--low", "--json"))
        assert [r["sku"] for r in low] == ["A"]

    def test_set_changes_the_reorder_fields(self, db):
        _item(db, "A", 4, 4)
        ok(db, "shop", "inventory", "set", "A", "--reorder-qty", "12",
           "--vendor", "Moto Supply")
        assert sql(db, "SELECT reorder_quantity, vendor_id FROM inventory_items") == [(12, 2)]
        assert "Nothing to change" in refused(db, "shop", "inventory", "set", "A")

    def test_a_duplicate_sku_is_refused(self, db):
        _item(db, "A", 1, 0)
        refused(db, "shop", "inventory", "add", "--sku", "A", "--name", "again")

    def test_an_unknown_vendor_is_refused(self, db):
        out = refused(db, "shop", "inventory", "add", "--sku", "A", "--name", "a",
                      "--vendor", "Nobody")
        assert "No vendor 'Nobody'" in out


class TestPurchaseOrders:
    def _setup(self, db):
        _item(db, "OF-1", 2, 4, 10, "Acme Parts", 425)    # due, orderable
        _item(db, "BP-1", 0, 2, 4, "Acme Parts", 3100)    # due, orderable
        _item(db, "SP-1", 1, 3, 6, "Moto Supply", 899)    # due, other vendor
        _item(db, "NQ-1", 0, 5, 0, "Acme Parts")          # due, no reorder quantity
        _item(db, "NV-1", 0, 5, 3)                        # due, no vendor
        _item(db, "OK-1", 9, 2, 5, "Acme Parts")          # not due

    def test_reorder_shows_what_would_be_ordered_and_why_not(self, db):
        self._setup(db)
        plan = {p["sku"]: p for p in json.loads(
            ok(db, "shop", "inventory", "reorder", "--json"))}
        assert set(plan) == {"OF-1", "BP-1", "SP-1", "NQ-1", "NV-1"}
        assert plan["OF-1"]["order_quantity"] == 10
        assert plan["NQ-1"]["skip_reason"] == "no reorder quantity set"
        assert plan["NV-1"]["skip_reason"] == "no vendor set"
        assert "not ordered: no vendor set" in ok(db, "shop", "inventory", "reorder")

    def test_generate_drafts_one_po_per_vendor_and_names_what_it_skipped(self, db):
        self._setup(db)
        out = ok(db, "shop", "inventory", "po", "generate")
        assert "Not ordered: NQ-1" in out and "no reorder quantity set" in out
        assert "Not ordered: NV-1" in out and "no vendor set" in out
        pos = sql(db, "SELECT vendor_id, status FROM purchase_orders ORDER BY vendor_id")
        assert pos == [(1, "draft"), (2, "draft")]
        lines = sql(db, "SELECT i.sku, l.quantity, l.unit_cost_cents "
                        "FROM purchase_order_lines l "
                        "JOIN inventory_items i ON i.id = l.item_id ORDER BY i.sku")
        assert lines == [("BP-1", 4, 3100), ("OF-1", 10, 425), ("SP-1", 6, 899)]

    def test_an_item_on_an_open_po_is_not_ordered_twice(self, db):
        self._setup(db)
        ok(db, "shop", "inventory", "po", "generate")
        out = ok(db, "shop", "inventory", "po", "generate")
        assert "already on an open purchase order" in out
        assert sql(db, "SELECT COUNT(*) FROM purchase_orders") == [(2,)]

    def test_the_printable_po(self, db, tmp_path):
        self._setup(db)
        ok(db, "shop", "inventory", "po", "generate")
        path = tmp_path / "po.txt"
        ok(db, "shop", "inventory", "po", "show", "1", "--out", str(path))
        text = path.read_text()
        assert "PURCHASE ORDER PO-" in text
        assert "From: Reyes Moto" in text
        assert "To:   Acme Parts" in text and "Terms: Net 30" in text
        assert "OF-1" in text and "BP-1" in text and "SP-1" not in text
        assert "166.50" in text          # 10 x 4.25 + 4 x 31.00
        assert "Phase" not in text and "Track" not in text

    def test_receive_adds_the_quantities_to_stock(self, db):
        self._setup(db)
        ok(db, "shop", "inventory", "po", "generate")
        ok(db, "shop", "inventory", "po", "mark-sent", "1")
        out = ok(db, "shop", "inventory", "po", "receive", "1")
        assert "+10 OF-1" in out
        assert (_stock(db, "OF-1"), _stock(db, "BP-1"), _stock(db, "SP-1")) == (12, 4, 1)
        assert sql(db, "SELECT status FROM purchase_orders WHERE id = 1") == [("received",)]

    @pytest.mark.parametrize("steps", [
        ["receive"],                          # a draft is not received
        ["mark-sent", "mark-sent"],
        ["cancel", "mark-sent"],
        ["mark-sent", "receive", "cancel"],
    ])
    def test_a_move_out_of_order_is_refused(self, db, steps):
        self._setup(db)
        ok(db, "shop", "inventory", "po", "generate")
        for step in steps[:-1]:
            ok(db, "shop", "inventory", "po", step, "1")
        before = _stock(db, "OF-1")
        refused(db, "shop", "inventory", "po", steps[-1], "1")
        assert _stock(db, "OF-1") == before

    def test_a_cancelled_po_frees_its_items_for_the_next_one(self, db):
        self._setup(db)
        ok(db, "shop", "inventory", "po", "generate")
        ok(db, "shop", "inventory", "po", "cancel", "1")
        ok(db, "shop", "inventory", "po", "generate")
        rows = json.loads(ok(db, "shop", "inventory", "po", "list", "--json"))
        assert sorted((r["vendor_name"], r["status"]) for r in rows) == [
            ("Acme Parts", "cancelled"), ("Acme Parts", "draft"), ("Moto Supply", "draft")]
