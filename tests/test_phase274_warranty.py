"""Phase 274 — row 280, warranty validity and claim records.

Through `motodiag shop warranty …` on a scratch database. The validity
lookup never reads a figure that was not recorded as a pass.
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
    shop = seed_shop(path, "Reyes Moto")
    seed_customer(path, shop, "Dana Reyes")                                  # 2
    seed_bike(path, "Honda", "CB500F", 2024, vin="MLHPC6400R5000001",
              mileage=8200)                                                  # 1
    seed_bike(path, "Yamaha", "MT-07", 2021)                                 # 2
    ok(path, "shop", "customer", "link-bike", "2", "--bike", "1")
    return path


def _check(db, *args):
    return {c["warranty_id"]: (c["verdict"], c["reasons"]) for c in json.loads(
        ok(db, "shop", "warranty", "check", "--bike", "1", "--json", *args))["coverage"]}


def _add(db, *args):
    ok(db, "shop", "warranty", "add", "--bike", "1", *args)


class TestValidity:
    def test_valid_within_dates_and_mileage(self, db):
        _add(db, "--coverage", "powertrain", "--provider", "Honda", "--start",
             "2024-03-01", "--end", "2027-03-01", "--mileage-limit", "24000")
        assert _check(db, "--on", "2026-09-29") == {
            1: ("valid", ["2024-03-01 to 2027-03-01", "8,200 of 24,000 mi"])}
        assert "valid" in ok(db, "shop", "warranty", "check", "--bike", "1",
                             "--on", "2026-09-29")

    @pytest.mark.parametrize("args, reason", [
        (("--on", "2027-03-02"), "ended 2027-03-01"),
        (("--on", "2024-02-01"), "starts 2024-03-01"),
        (("--on", "2026-09-29", "--mileage", "24001"),
         "24,001 mi is over the 24,000 mi limit"),
    ])
    def test_not_valid_names_the_reason(self, db, args, reason):
        _add(db, "--coverage", "powertrain", "--start", "2024-03-01", "--end",
             "2027-03-01", "--mileage-limit", "24000")
        assert _check(db, *args) == {1: ("not valid", [reason])}

    def test_an_unrecorded_limit_is_never_a_pass(self, db):
        _add(db, "--coverage", "comprehensive", "--start", "2024-03-01")
        assert _check(db, "--on", "2026-09-29")[1] == (
            "cannot tell", ["no end date recorded", "no mileage limit recorded"])

    def test_an_unknown_mileage_is_never_a_pass(self, db):
        ok(db, "shop", "warranty", "add", "--bike", "2", "--coverage", "extended",
           "--start", "2021-01-01", "--end", "2030-01-01", "--mileage-limit", "50000")
        got = json.loads(ok(db, "shop", "warranty", "check", "--bike", "2", "--on",
                            "2026-09-29", "--json"))["coverage"][0]
        assert (got["verdict"], got["reasons"]) == (
            "cannot tell", ["the bike's mileage is not known (limit 50,000 mi)"])

    def test_a_failure_outranks_a_missing_figure(self, db):
        _add(db, "--coverage", "extended", "--end", "2025-01-01")
        assert _check(db, "--on", "2026-09-29")[1][0] == "not valid"

    def test_the_mileage_option_overrides_the_recorded_one(self, db):
        _add(db, "--coverage", "powertrain", "--start", "2024-03-01", "--end",
             "2027-03-01", "--mileage-limit", "10000")
        assert _check(db, "--on", "2026-09-29")[1][0] == "valid"
        assert _check(db, "--on", "2026-09-29", "--mileage", "12000")[1][0] == "not valid"

    def test_no_warranty_is_not_shown_as_cover(self, db):
        assert "No warranty is recorded" in ok(db, "shop", "warranty", "check",
                                               "--bike", "1")

    def test_an_end_before_the_start_is_refused(self, db):
        refused(db, "shop", "warranty", "add", "--bike", "1", "--coverage", "powertrain",
                "--start", "2027-01-01", "--end", "2026-01-01")
        assert sql(db, "SELECT COUNT(*) FROM warranties") == [(0,)]

    def test_the_list_shows_the_coverage(self, db):
        _add(db, "--coverage", "powertrain", "--provider", "Honda", "--mileage-limit",
             "24000")
        out = ok(db, "shop", "warranty", "list", "--bike", "1")
        assert "powertrain" in out and "Honda" in out and "24,000" in out


class TestClaims:
    def _wo(self, db, vehicle=1):
        sql(db, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title, status, "
                "actual_hours, opened_at, completed_at) VALUES (1, ?, 2, 'Replace stator', "
                "'completed', 2.5, '2026-09-20T09:00:00', '2026-09-21T16:00:00')", (vehicle,))
        wo = sql(db, "SELECT MAX(id) FROM work_orders")[0][0]
        sql(db, "INSERT INTO issues (work_order_id, title, category, severity, description, "
                "resolution_notes) VALUES (?, 'No charge at idle', 'electrical', 'high', "
                "'Battery flat after 20 min ride', 'Stator windings open; replaced')", (wo,))
        sql(db, "INSERT INTO parts (slug, oem_part_number, brand, description, category, "
                "make, model_pattern, typical_cost_cents) VALUES (?, "
                "'31120-MJW-J01', 'Honda', 'Stator assembly', 'electrical', 'Honda', "
                "'CB500%', 28900)", (f"stator-{wo}",))
        part = sql(db, "SELECT MAX(id) FROM parts")[0][0]
        sql(db, "INSERT INTO work_order_parts (work_order_id, part_id, quantity, status) "
                "VALUES (?, ?, 1, 'installed')", (wo, part))
        sql(db, "INSERT INTO work_order_time_entries (work_order_id, user_id, started_at, "
                "ended_at, duration_seconds, created_at, updated_at) VALUES (?, 1, "
                "'2026-09-21T09:00:00', '2026-09-21T11:30:00', 9000, 'x', 'x')", (wo,))
        return wo

    def _warranty(self, db):
        _add(db, "--coverage", "powertrain", "--provider", "Honda", "--start",
             "2024-03-01", "--end", "2027-03-01", "--mileage-limit", "24000")

    def test_a_claim_moves_through_its_statuses(self, db):
        self._warranty(db)
        wo = self._wo(db)
        # Phase 373: the amount claimed is derived by the invoice, never typed.
        ok(db, "shop", "warranty", "claim", "open", "--warranty", "1", "--wo", wo,
           "--description", "Stator failed at 8,200 mi")
        assert sql(db, "SELECT claim_count FROM warranties") == [(1,)]
        ok(db, "shop", "warranty", "claim", "status", "1", "--to", "submitted",
           "--claim-number", "HN-2026-0042")
        ok(db, "shop", "warranty", "claim", "status", "1", "--to", "approved",
           "--approved-cents", "38900")
        ok(db, "shop", "warranty", "claim", "status", "1", "--to", "paid")
        row = sql(db, "SELECT status, claim_number, amount_claimed_cents, "
                      "amount_approved_cents, submitted_at IS NOT NULL, "
                      "decided_at IS NOT NULL, paid_at IS NOT NULL FROM warranty_claims")
        assert row == [("paid", "HN-2026-0042", None, 38900, 1, 1, 1)]
        listed = json.loads(ok(db, "shop", "warranty", "claim", "list", "--bike", "1",
                               "--json"))
        assert [c["status"] for c in listed] == ["paid"]
        assert "HN-2026-0042" in ok(db, "shop", "warranty", "claim", "show", "1")

    @pytest.mark.parametrize("steps", [
        ["approved"], ["paid"], ["submitted", "paid"],
        ["submitted", "denied", "approved"],
    ])
    def test_a_move_out_of_order_is_refused(self, db, steps):
        self._warranty(db)
        ok(db, "shop", "warranty", "claim", "open", "--warranty", "1", "--description", "x")
        for s in steps[:-1]:
            ok(db, "shop", "warranty", "claim", "status", "1", "--to", s)
        refused(db, "shop", "warranty", "claim", "status", "1", "--to", steps[-1])

    def test_a_work_order_on_another_bike_is_refused(self, db):
        self._warranty(db)
        wo = self._wo(db, vehicle=2)
        out = refused(db, "shop", "warranty", "claim", "open", "--warranty", "1",
                      "--wo", wo, "--description", "x")
        assert "another bike" in out
        assert sql(db, "SELECT (SELECT COUNT(*) FROM warranty_claims), "
                       "(SELECT claim_count FROM warranties)") == [(0, 0)]

    def test_the_packet_holds_the_claims_documentation(self, db, tmp_path):
        self._warranty(db)
        wo = self._wo(db)
        ok(db, "shop", "warranty", "claim", "open", "--warranty", "1", "--wo", wo,
           "--description", "Stator failed at 8,200 mi")
        path = tmp_path / "claim.txt"
        ok(db, "shop", "warranty", "claim", "packet", "1", "--out", str(path))
        text = path.read_text()
        for expected in (
            "WARRANTY CLAIM #1", "Shop: Reyes Moto", "Customer: Dana Reyes",
            "Bike: 2024 Honda CB500F", "VIN: MLHPC6400R5000001", "8,200 mi",
            "Coverage: powertrain (Honda)", "Term: 2024-03-01 to 2027-03-01",
            "On the repair date (2026-09-21): valid",
            "Stator failed at 8,200 mi", "Covered lines:\n    not recorded yet",
            "Amount claimed: not recorded", "Amount approved: not recorded",
            "No charge at idle [electrical, high]",
            "Resolution: Stator windings open",
            "1 x Honda Stator assembly (part no. 31120-MJW-J01) [installed]",
            "Labour: 2.50 h logged in 1 time entry; billed hours 2.5",
        ):
            assert expected in text, expected
        assert "Phase" not in text and "Track" not in text

    def test_the_packet_says_what_is_not_recorded(self, db):
        ok(db, "shop", "warranty", "add", "--bike", "2", "--coverage", "extended")
        ok(db, "shop", "warranty", "claim", "open", "--warranty", "1", "--description", "x")
        text = ok(db, "shop", "warranty", "claim", "packet", "1")
        for expected in ("VIN: not recorded", "Mileage limit: not recorded",
                         "Work order: none linked", "Customer: not recorded"):
            assert expected in text, expected
