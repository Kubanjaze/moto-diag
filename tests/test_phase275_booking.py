"""Phase 275 — row 275: booking by shop staff.

Everything is driven through `motodiag shop appointment …` against a
scratch database.
"""

from __future__ import annotations

import json

import pytest

from support.phase275 import (
    MONDAY, TUESDAY, WEDNESDAY, new_db, ok, refused, seed_bay_slot,
    seed_booking_shop, sql,
)


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    return path, seed_booking_shop(path)


def _book(db_path, s, start, minutes=60, mechanic=None, customer=None, bike=None,
          extra=()):
    args = ["shop", "appointment", "book", "--shop", s["shop"],
            "--customer", customer or s["dana"], "--bike", bike or s["bike1"],
            "--start", start, "--minutes", minutes]
    if mechanic is not None:
        args += ["--mechanic", mechanic]
    return list(args) + list(extra)


def _appt(db_path, appt_id=1):
    return json.loads(ok(db_path, "shop", "appointment", "show", appt_id, "--json"))


class TestBooking:
    def test_a_booking_stores_the_shop_the_times_and_the_mechanic(self, db):
        path, s = db
        out = ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"],
                              extra=["--type", "diagnostic", "--notes", "Hard start"]))
        assert f"Booked appointment #1 for Dana Reyes, {MONDAY}T09:00 to {MONDAY}T10:00" in out
        assert sql(path, "SELECT shop_id, customer_id, vehicle_id, user_id, "
                         "appointment_type, status, scheduled_start, scheduled_end, "
                         "work_order_id FROM appointments") == [
            (s["shop"], s["dana"], s["bike1"], s["alex"], "diagnostic", "scheduled",
             f"{MONDAY}T09:00", f"{MONDAY}T10:00", None)]

    def test_an_end_time_books_the_same_as_a_length(self, db):
        path, s = db
        ok(path, "shop", "appointment", "book", "--shop", s["shop"], "--customer",
           s["dana"], "--bike", s["bike1"], "--start", f"{MONDAY}T09:00",
           "--end", f"{MONDAY}T10:30")
        assert sql(path, "SELECT scheduled_end FROM appointments") == [(f"{MONDAY}T10:30",)]

    def test_an_end_before_the_start_is_refused(self, db):
        path, s = db
        out = refused(path, "shop", "appointment", "book", "--shop", s["shop"],
                      "--customer", s["dana"], "--bike", s["bike1"],
                      "--start", f"{MONDAY}T10:00", "--end", f"{MONDAY}T09:00")
        assert "must end after it starts" in out
        assert sql(path, "SELECT COUNT(*) FROM appointments") == [(0,)]

    def test_a_time_with_a_zone_is_refused(self, db):
        path, s = db
        out = refused(path, *_book(path, s, f"{MONDAY}T09:00+02:00"))
        assert "without a time zone" in out

    def test_a_bike_not_linked_to_the_customer_is_refused(self, db):
        path, s = db
        out = refused(path, *_book(path, s, f"{MONDAY}T09:00", bike=s["bike2"]))
        assert "is not linked to Dana Reyes" in out and "link-bike" in out

    def test_a_mechanic_who_is_not_a_member_is_refused(self, db):
        path, s = db
        sql(path, "UPDATE shop_members SET is_active = 0 WHERE user_id = ?", (s["jo"],))
        out = refused(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["jo"]))
        assert "not an active member" in out


class TestDoubleBooking:
    def test_the_same_mechanic_cannot_be_booked_twice_at_once(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"]))
        out = refused(path, *_book(path, s, f"{MONDAY}T09:30", mechanic=s["alex"],
                                   customer=s["sam"], bike=s["bike2"]))
        assert "already has appointment #1" in out
        assert sql(path, "SELECT COUNT(*) FROM appointments") == [(1,)]

    def test_another_mechanic_or_an_adjacent_time_is_free(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"]))
        ok(path, *_book(path, s, f"{MONDAY}T09:30", mechanic=s["jo"],
                        customer=s["sam"], bike=s["bike2"]))
        ok(path, *_book(path, s, f"{MONDAY}T10:00", mechanic=s["alex"],
                        customer=s["sam"], bike=s["bike2"]))
        assert sql(path, "SELECT COUNT(*) FROM appointments") == [(3,)]

    def test_a_cancelled_appointment_does_not_block_the_time(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"]))
        ok(path, "shop", "appointment", "cancel", "1", "--reason", "Customer away")
        ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"],
                        customer=s["sam"], bike=s["bike2"]))
        assert "Cancelled: Customer away" in _appt(path, 1)["notes"]

    def test_an_overlap_with_the_mechanics_bay_work_is_booked_with_a_warning(self, db):
        path, s = db
        slot = seed_bay_slot(path, s["shop"], s["alex"], s["sam"], s["bike2"],
                             f"{MONDAY}T08:00:00+00:00", f"{MONDAY}T12:00:00+00:00")
        out = ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"]))
        assert "Booked appointment #1" in out
        assert f"Warning: The mechanic has work order #{slot['wo']} in bay Lift A" in out
        assert "Warning" not in ok(path, *_book(path, s, f"{MONDAY}T13:00",
                                                mechanic=s["alex"]))

    def test_a_move_onto_the_mechanics_other_appointment_is_refused(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"]))
        ok(path, *_book(path, s, f"{MONDAY}T11:00", mechanic=s["alex"],
                        customer=s["sam"], bike=s["bike2"]))
        out = refused(path, "shop", "appointment", "reschedule", "2",
                      "--start", f"{MONDAY}T09:30", "--minutes", "30")
        assert "already has appointment #1" in out
        ok(path, "shop", "appointment", "reschedule", "2",
           "--start", f"{TUESDAY}T09:30", "--minutes", "30")
        assert _appt(path, 2)["scheduled_start"] == f"{TUESDAY}T09:30"


class TestSlots:
    def test_free_times_step_by_fifteen_minutes_around_bookings(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"]))
        out = ok(path, "shop", "appointment", "slots", "--shop", s["shop"],
                 "--date", MONDAY, "--minutes", "60", "--mechanic", s["alex"])
        times = out.split(": ", 1)[1].strip().split(", ")
        assert times[:1] == ["08:00"]
        assert "08:15" not in times and "09:45" not in times
        assert "10:00" in times
        assert times[-1] == "16:00"
        assert out.startswith("Alex Kim")

    def test_without_a_mechanic_every_active_member_is_listed(self, db):
        path, s = db
        out = ok(path, "shop", "appointment", "slots", "--shop", s["shop"],
                 "--date", MONDAY, "--minutes", "480")
        assert "Alex Kim (user" in out and "Jo Park (user" in out
        assert out.count("08:00") == 2

    def test_a_day_the_shop_is_closed_is_refused(self, db):
        path, s = db
        out = refused(path, "shop", "appointment", "slots", "--shop", s["shop"],
                      "--date", WEDNESDAY, "--minutes", "60")
        assert "closed on Wednesdays" in out

    def test_no_recorded_hours_are_never_assumed(self, db):
        path, s = db
        sql(path, "UPDATE shops SET hours_json = NULL")
        out = refused(path, "shop", "appointment", "slots", "--shop", s["shop"],
                      "--date", MONDAY, "--minutes", "60")
        assert "no opening hours recorded" in out and "--open" in out
        given = ok(path, "shop", "appointment", "slots", "--shop", s["shop"],
                   "--date", MONDAY, "--minutes", "60", "--mechanic", s["jo"],
                   "--open", "10:00", "--close", "12:00")
        assert "10:00, 10:15, 10:30, 10:45, 11:00" in given
        assert "09:45" not in given and "11:15" not in given


class TestConfirmation:
    def test_confirming_prints_the_text_logs_a_contact_and_queues_nothing(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"]))
        out = ok(path, "shop", "appointment", "confirm", "1", "--channel", "sms")
        assert "your appointment at Twin Peaks Moto is confirmed for Monday 05 October 2026" in out
        assert "09:00 to 10:00" in out
        assert "Bike: 2020 Honda CB500F." in out
        assert "Mechanic: Alex Kim." in out
        assert "Address: 12 Mill Rd, Lowell, MA 01852." in out
        assert "call 555-0101" in out
        assert "Nothing was sent" in out
        assert _appt(path)["status"] == "confirmed"
        contacts = sql(path, "SELECT customer_id, shop_id, direction, channel, summary "
                             "FROM customer_communications")
        assert len(contacts) == 1
        assert contacts[0][:4] == (s["dana"], s["shop"], "outbound", "sms")
        assert "Appointment #1 confirmed." in contacts[0][4]
        assert sql(path, "SELECT COUNT(*) FROM customer_notifications") == [(0,)]

    def test_the_confirmation_leaves_out_what_is_not_recorded(self, db):
        path, s = db
        sql(path, "UPDATE shops SET address = NULL, city = NULL, state = NULL, "
                  "zip = NULL, phone = NULL")
        ok(path, *_book(path, s, f"{MONDAY}T09:00"))
        out = ok(path, "shop", "appointment", "confirm", "1", "--channel", "phone")
        assert "Address" not in out and "call" not in out and "Mechanic:" not in out

    def test_a_cancelled_appointment_cannot_be_confirmed(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00"))
        ok(path, "shop", "appointment", "cancel", "1")
        out = refused(path, "shop", "appointment", "confirm", "1", "--channel", "phone")
        assert "is cancelled; it cannot be confirmed" in out
        assert sql(path, "SELECT COUNT(*) FROM customer_communications") == [(0,)]


class TestCheckIn:
    def test_check_in_opens_a_work_order_assigned_to_the_mechanic(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00", mechanic=s["alex"],
                        extra=["--notes", "Hard start"]))
        out = ok(path, "shop", "appointment", "check-in", "1")
        assert "work order #1 opened" in out
        assert sql(path, "SELECT shop_id, vehicle_id, customer_id, title, status, "
                         "assigned_mechanic_user_id FROM work_orders") == [
            (s["shop"], s["bike1"], s["dana"], "Service: Hard start", "open", s["alex"])]
        appt = _appt(path)
        assert (appt["status"], appt["work_order_id"]) == ("in_progress", 1)
        assert appt["actual_start"]
        ok(path, "shop", "appointment", "complete", "1")
        assert _appt(path)["status"] == "completed"

    def test_check_in_links_a_matching_work_order(self, db):
        path, s = db
        sql(path, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title) "
                  "VALUES (?, ?, ?, 'Existing job')", (s["shop"], s["bike1"], s["dana"]))
        ok(path, *_book(path, s, f"{MONDAY}T09:00"))
        assert "work order #1 linked" in ok(path, "shop", "appointment", "check-in", "1",
                                            "--wo", "1")
        assert sql(path, "SELECT COUNT(*) FROM work_orders") == [(1,)]

    def test_check_in_refuses_another_customers_work_order(self, db):
        path, s = db
        sql(path, "INSERT INTO work_orders (shop_id, vehicle_id, customer_id, title) "
                  "VALUES (?, ?, ?, 'Sam job')", (s["shop"], s["bike2"], s["sam"]))
        ok(path, *_book(path, s, f"{MONDAY}T09:00"))
        out = refused(path, "shop", "appointment", "check-in", "1", "--wo", "1")
        assert "is for another customer, bike" in out
        assert _appt(path)["status"] == "scheduled"


class TestStatusMoves:
    @pytest.mark.parametrize("command", [["complete"], ["check-in"]])
    def test_a_closed_appointment_cannot_move(self, db, command):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00"))
        ok(path, "shop", "appointment", "no-show", "1")
        out = refused(path, "shop", "appointment", *command, "1")
        assert "is no_show" in out

    def test_a_scheduled_appointment_cannot_be_completed(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00"))
        assert "cannot become completed" in refused(path, "shop", "appointment",
                                                    "complete", "1")

    def test_a_cancelled_appointment_cannot_be_moved(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00"))
        ok(path, "shop", "appointment", "cancel", "1")
        out = refused(path, "shop", "appointment", "reschedule", "1",
                      "--start", f"{TUESDAY}T09:00", "--minutes", "60")
        assert "only a scheduled or confirmed appointment can be moved" in out

    def test_the_list_filters_by_day_and_status(self, db):
        path, s = db
        ok(path, *_book(path, s, f"{MONDAY}T09:00"))
        ok(path, *_book(path, s, f"{TUESDAY}T09:00", customer=s["sam"], bike=s["bike2"]))
        ok(path, "shop", "appointment", "cancel", "2")
        rows = json.loads(ok(path, "shop", "appointment", "list", "--shop", s["shop"],
                             "--from", TUESDAY, "--to", TUESDAY, "--json"))
        assert [r["id"] for r in rows] == [2]
        rows = json.loads(ok(path, "shop", "appointment", "list", "--shop", s["shop"],
                             "--status", "scheduled", "--json"))
        assert [r["id"] for r in rows] == [1]
        assert "Dana Reyes" in ok(path, "shop", "appointment", "list", "--shop", s["shop"])
