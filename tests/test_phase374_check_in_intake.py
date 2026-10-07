"""Phase 374 — row 374: check-in with an intake (F189).

`shop appointment check-in` opens the work order from the visit's intake:
the one named with `--intake`, the one open intake taken within a day of
the appointment, or one it records itself. Driven through the commands
against a scratch database, on a fixed clock in New York (EDT, UTC-4).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from support.frozen_clock import frozen_datetime, set_zone
from support.phase275 import MONDAY, new_db, ok, refused, seed_booking_shop, sql

# Monday 2026-10-05, 10:00 in New York: an hour after the 09:00 booking.
NOW = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
ZONE = "America/New_York"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    import os

    from motodiag.scheduling import booking
    from motodiag.shop import intake_repo

    previous = os.environ.get("TZ")
    set_zone(ZONE)
    frozen = frozen_datetime(NOW)
    monkeypatch.setattr(booking, "datetime", frozen)
    monkeypatch.setattr(intake_repo, "datetime", frozen)
    yield
    set_zone(previous)


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    s = seed_booking_shop(path)
    ok(path, "shop", "appointment", "book", "--shop", s["shop"], "--customer", s["dana"],
       "--bike", s["bike1"], "--start", f"{MONDAY}T09:00", "--minutes", "60",
       "--mechanic", s["alex"], "--notes", "Hard start when cold")
    return path, s


def _flat(text: str) -> str:
    return " ".join(text.split())


def _intake(path, s, customer=None, mileage="31200", notes="Hard start when cold") -> int:
    ok(path, "shop", "intake", "create", "--shop", s["shop"], "--customer",
             customer or s["dana"], "--bike", s["bike1"], "--mileage", mileage,
             "--notes", notes)
    return sql(path, "SELECT MAX(id) FROM intake_visits")[0][0]


def _taken(path, intake_id, utc: str) -> None:
    sql(path, "UPDATE intake_visits SET intake_at = ? WHERE id = ?", (utc, intake_id))


def _unchanged(path) -> None:
    """A refused check-in leaves the appointment booked and adds nothing."""
    assert sql(path, "SELECT status, work_order_id FROM appointments") == [
        ("scheduled", None)]
    assert sql(path, "SELECT COUNT(*) FROM work_orders") == [(0,)]


def _wo_intake(path) -> int | None:
    return sql(path, "SELECT intake_visit_id FROM work_orders")[0][0]


class TestCheckInRecordsTheIntake:
    def test_with_no_intake_open_check_in_records_one_with_the_mileage_unknown(self, db):
        path, s = db
        out = _flat(ok(path, "shop", "appointment", "check-in", "1"))
        assert "Appointment #1 checked in; work order #1 opened." in out
        assert "Intake recorded: intake #1, taken 2026-10-05 10:00, mileage not recorded." in out
        assert "Record the mileage with: shop intake update 1 --mileage N" in out
        assert sql(path, "SELECT shop_id, customer_id, vehicle_id, mileage_at_intake, "
                         "reported_problems, intake_user_id, status FROM intake_visits") == [
            (s["shop"], s["dana"], s["bike1"], None, "Hard start when cold", 1, "open")]
        assert _wo_intake(path) == 1

    def test_the_mileage_and_problems_given_are_recorded(self, db):
        path, s = db
        out = _flat(ok(path, "shop", "appointment", "check-in", "1", "--mileage", "31200",
                       "--problems", "Stalls at idle"))
        assert "Intake recorded: intake #1, taken 2026-10-05 10:00, mileage 31,200 mi." in out
        assert "Record the mileage" not in out
        assert sql(path, "SELECT mileage_at_intake, reported_problems FROM intake_visits") == [
            (31200, "Stalls at idle")]

    def test_the_intake_is_stamped_in_utc_from_the_clock(self, db):
        path, s = db
        ok(path, "shop", "appointment", "check-in", "1")
        assert sql(path, "SELECT intake_at FROM intake_visits") == [("2026-10-05 14:00:00",)]

    def test_the_work_order_shows_its_intake_once_the_mileage_is_read(self, db):
        path, s = db
        ok(path, "shop", "appointment", "check-in", "1")
        ok(path, "shop", "intake", "update", "1", "--mileage", "31250")
        out = _flat(ok(path, "shop", "work-order", "show", "1"))
        assert "Intake: intake #1, taken 2026-10-05 10:00, mileage 31,250 mi" in out
        assert "Reported: Hard start when cold" in out

    def test_an_intake_for_another_customer_is_not_linked_and_is_named(self, db):
        path, s = db
        other = _intake(path, s, customer=s["sam"])
        out = _flat(ok(path, "shop", "appointment", "check-in", "1"))
        assert "Intake recorded: intake #2" in out
        assert f"this bike has 1 other open intake(s) (ids={other})" in out
        assert _wo_intake(path) == 2

    def test_a_closed_intake_is_not_linked(self, db):
        path, s = db
        ok(path, "shop", "intake", "close", str(_intake(path, s)))
        assert "Intake recorded: intake #2" in _flat(
            ok(path, "shop", "appointment", "check-in", "1"))

    def test_a_negative_mileage_is_refused_and_nothing_is_recorded(self, db):
        path, s = db
        refused(path, "shop", "appointment", "check-in", "1", "--mileage", "-5")
        _unchanged(path)
        assert sql(path, "SELECT COUNT(*) FROM intake_visits") == [(0,)]


class TestCheckInLinksTheIntake:
    def test_the_one_open_intake_taken_this_morning_is_linked(self, db):
        path, s = db
        intake = _intake(path, s)
        out = _flat(ok(path, "shop", "appointment", "check-in", "1"))
        assert (f"Intake linked: intake #{intake}, taken 2026-10-05 10:00, "
                "mileage 31,200 mi.") in out
        assert sql(path, "SELECT COUNT(*) FROM intake_visits") == [(1,)]
        assert _wo_intake(path) == intake

    # The booking is 09:00 EDT, 13:00 UTC; the intake's time is stored in UTC.
    @pytest.mark.parametrize("utc", ["2026-10-04 13:00:00", "2026-10-06 13:00:00"])
    def test_a_day_either_side_is_within_the_day(self, db, utc):
        path, s = db
        intake = _intake(path, s)
        _taken(path, intake, utc)
        ok(path, "shop", "appointment", "check-in", "1")
        assert _wo_intake(path) == intake

    @pytest.mark.parametrize("utc", ["2026-10-04 12:59:00", "2026-10-06 13:01:00"])
    def test_a_minute_beyond_the_day_asks_for_intake(self, db, utc):
        path, s = db
        intake = _intake(path, s)
        _taken(path, intake, utc)
        out = _flat(refused(path, "shop", "appointment", "check-in", "1"))
        assert "no single open intake for this customer and bike was taken within a day " \
               f"of appointment #1 ({MONDAY} 09:00)" in out
        assert f"intake #{intake}, taken" in out and "mileage 31,200 mi" in out
        assert "Give --intake ID" in out and "shop intake close ID" in out
        _unchanged(path)

    def test_two_open_intakes_ask_for_intake_and_name_both(self, db):
        path, s = db
        first, second = _intake(path, s), _intake(path, s, mileage="31210")
        out = _flat(refused(path, "shop", "appointment", "check-in", "1"))
        assert f"intake #{first}, taken 2026-10-05 10:00, mileage 31,200 mi" in out
        assert f"intake #{second}, taken 2026-10-05 10:00, mileage 31,210 mi" in out
        _unchanged(path)
        ok(path, "shop", "appointment", "check-in", "1", "--intake", str(second))
        assert _wo_intake(path) == second

    def test_intake_named_is_linked_whenever_it_was_taken(self, db):
        path, s = db
        intake = _intake(path, s)
        _taken(path, intake, "2026-09-28 13:00:00")
        out = _flat(ok(path, "shop", "appointment", "check-in", "1", "--intake",
                       str(intake)))
        assert f"Intake linked: intake #{intake}, taken 2026-09-28 09:00" in out
        assert _wo_intake(path) == intake

    def test_details_with_an_open_intake_are_refused_and_name_intake_update(self, db):
        path, s = db
        intake = _intake(path, s)
        out = _flat(refused(path, "shop", "appointment", "check-in", "1",
                            "--mileage", "31300"))
        assert f"is open for this visit; change its mileage or problems with: " \
               f"shop intake update {intake}" in out
        _unchanged(path)
        out = _flat(refused(path, "shop", "appointment", "check-in", "1", "--intake",
                            str(intake), "--problems", "Stalls"))
        assert f"shop intake update {intake}" in out
        _unchanged(path)

    @pytest.mark.parametrize("case", ["closed", "another customer", "missing"])
    def test_an_intake_named_that_is_not_this_visits_is_refused(self, db, case):
        path, s = db
        if case == "closed":
            intake = _intake(path, s)
            ok(path, "shop", "intake", "close", str(intake))
            expected = f"intake #{intake} is closed"
        elif case == "another customer":
            intake = _intake(path, s, customer=s["sam"])
            expected = f"intake #{intake} is for another customer"
        else:
            intake, expected = 99, "intake not found: id=99"
        out = _flat(refused(path, "shop", "appointment", "check-in", "1", "--intake",
                            str(intake)))
        assert expected in out
        _unchanged(path)


class TestCheckInWithAWorkOrder:
    def _work_order(self, path, s, intake=None) -> int:
        args = (["--intake", str(intake)] if intake else
                ["--shop", str(s["shop"]), "--customer", str(s["dana"]),
                 "--bike", str(s["bike1"])])
        ok(path, "shop", "work-order", "create", *args, "--title", "Hard start")
        return sql(path, "SELECT MAX(id) FROM work_orders")[0][0]

    def test_a_work_order_from_an_intake_prints_that_intake(self, db):
        path, s = db
        intake = _intake(path, s)
        wo = self._work_order(path, s, intake)
        out = _flat(ok(path, "shop", "appointment", "check-in", "1", "--wo", str(wo)))
        assert f"work order #{wo} linked" in out
        assert f"Intake linked: intake #{intake}, taken 2026-10-05 10:00, " \
               "mileage 31,200 mi." in out

    def test_a_work_order_without_one_says_so(self, db):
        path, s = db
        wo = self._work_order(path, s)
        out = _flat(ok(path, "shop", "appointment", "check-in", "1", "--wo", str(wo)))
        assert f"Work order #{wo} has no intake." in out
        assert sql(path, "SELECT COUNT(*) FROM intake_visits") == [(0,)]

    @pytest.mark.parametrize("extra", [["--intake", "1"], ["--mileage", "31200"],
                                       ["--problems", "Stalls"]])
    def test_intake_options_do_not_go_with_wo(self, db, extra):
        path, s = db
        _intake(path, s)
        wo = self._work_order(path, s)
        out = _flat(refused(path, "shop", "appointment", "check-in", "1", "--wo",
                            str(wo), *extra))
        assert "--wo links a work order with the intake it was opened with" in out
        assert sql(path, "SELECT status FROM appointments") == [("scheduled",)]


class TestThePacket:
    @pytest.fixture
    def claim(self, db):
        path, s = db
        sql(path, "UPDATE vehicles SET mileage = 52000 WHERE id = ?", (s["bike1"],))
        ok(path, "shop", "warranty", "add", "--bike", str(s["bike1"]), "--coverage",
           "extended", "--provider", "Honda Protection Plan", "--start", "2024-03-01",
           "--end", "2027-02-28", "--mileage-limit", "40000", "--payer", "other")
        return path, s

    def _open_claim(self, path) -> str:
        wo = sql(path, "SELECT MAX(id) FROM work_orders")[0][0]
        ok(path, "shop", "warranty", "claim", "open", "--warranty", "1", "--wo", str(wo),
           "--description", "Starter clutch")
        return _flat(ok(path, "shop", "warranty", "claim", "packet", "1"))

    def test_an_unknown_mileage_at_intake_is_not_recorded_not_the_bikes(self, claim):
        path, s = claim
        ok(path, "shop", "appointment", "check-in", "1")
        packet = self._open_claim(path)
        assert "Mileage on record: 52,000 mi" in packet
        assert "Mileage at intake: not recorded" in packet
        assert "Reported at intake: Hard start when cold" in packet
        # The bike's 52,000 would be over the limit; the intake's is unknown.
        assert ": cannot tell — the bike's mileage is not known (limit 40,000 mi)" in packet
        assert "over the 40,000 mi limit" not in packet

    def test_the_mileage_read_into_the_intake_reaches_the_packet(self, claim):
        path, s = claim
        ok(path, "shop", "appointment", "check-in", "1")
        ok(path, "shop", "intake", "update", "1", "--mileage", "31200")
        packet = self._open_claim(path)
        assert "Mileage at intake: 31,200 mi" in packet
        assert ": valid — 2024-03-01 to 2027-02-28; 31,200 of 40,000 mi" in packet

    def test_a_work_order_with_no_intake_keeps_the_bikes_mileage(self, claim):
        path, s = claim
        ok(path, "shop", "work-order", "create", "--shop", str(s["shop"]), "--customer",
           str(s["dana"]), "--bike", str(s["bike1"]), "--title", "Starter clutch")
        ok(path, "shop", "work-order", "start", "1")  # opened, so the packet has a date
        packet = self._open_claim(path)
        assert "Mileage at intake" not in packet
        assert "52,000 mi is over the 40,000 mi limit" in packet
