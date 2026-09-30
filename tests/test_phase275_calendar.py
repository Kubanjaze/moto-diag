"""Phase 275 — row 276: one calendar of appointments and bay slots, and its iCal file.

Driven through `motodiag shop calendar …`. The `.ics` is read back by a
small RFC 5545 reader in this file (unfold, split properties), not by the
code that wrote it.
"""

from __future__ import annotations

import pytest

from support.phase275 import (
    MONDAY, TUESDAY, new_db, ok, refused, seed_bay_slot, seed_booking_shop, sql,
)


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    s = seed_booking_shop(path)
    ok(path, "shop", "appointment", "book", "--shop", s["shop"], "--customer", s["dana"],
       "--bike", s["bike1"], "--start", f"{MONDAY}T09:00", "--minutes", "60",
       "--mechanic", s["alex"], "--notes", "Hard start; stalls, then dies\nsecond line")
    ok(path, "shop", "appointment", "book", "--shop", s["shop"], "--customer", s["sam"],
       "--bike", s["bike2"], "--start", f"{TUESDAY}T14:00", "--minutes", "30",
       "--mechanic", s["jo"])
    s["slot"] = seed_bay_slot(path, s["shop"], s["alex"], s["sam"], s["bike2"],
                              f"{MONDAY}T11:00:00+00:00", f"{MONDAY}T13:00:00+00:00")
    return path, s


def _export(path, s, tmp_path, *extra, name="cal.ics"):
    out = tmp_path / name
    ok(path, "shop", "calendar", "export", "--shop", s["shop"], "--from", MONDAY,
       "--to", TUESDAY, "--out", str(out), *extra)
    return out.read_bytes()


def _unfold(raw: bytes) -> list[str]:
    text = raw.decode("utf-8")
    assert text.endswith("\r\n")
    physical = text[:-2].split("\r\n")
    assert all("\n" not in line and "\r" not in line for line in physical)
    logical: list[str] = []
    for line in physical:
        if line.startswith(" "):
            logical[-1] += line[1:]
        else:
            logical.append(line)
    return logical


def _events(raw: bytes) -> list[dict]:
    events, current = [], None
    for line in _unfold(raw):
        name, _, value = line.partition(":")
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            events.append(current)
            current = None
        elif current is not None:
            current[name] = value
    return events


class TestCalendarView:
    def test_both_kinds_are_shown_in_time_order(self, db):
        path, s = db
        out = ok(path, "shop", "calendar", "show", "--shop", s["shop"],
                 "--from", MONDAY, "--to", TUESDAY)
        a = out.index("Service: Dana Reyes (2020 Honda CB500F)")
        b = out.index(f"Bay Lift A: work order #{s['slot']['wo']}: Valve adjust")
        c = out.index("Service: Sam Ortiz (2021 Yamaha MT-07)")
        assert a < b < c

    def test_a_mechanic_sees_their_appointments_and_their_bay_work(self, db):
        path, s = db
        out = ok(path, "shop", "calendar", "show", "--shop", s["shop"], "--from", MONDAY,
                 "--to", TUESDAY, "--mechanic", s["alex"])
        assert "Dana Reyes" in out and "Bay Lift A" in out and "Sam Ortiz" not in out
        out = ok(path, "shop", "calendar", "show", "--shop", s["shop"], "--from", MONDAY,
                 "--to", TUESDAY, "--mechanic", s["jo"])
        assert "Sam Ortiz" in out and "Bay Lift A" not in out

    def test_a_bay_shows_only_its_slots(self, db):
        path, s = db
        out = ok(path, "shop", "calendar", "show", "--shop", s["shop"], "--from", MONDAY,
                 "--to", TUESDAY, "--bay", s["slot"]["bay"])
        assert "Bay Lift A" in out and "Dana Reyes" not in out

    def test_a_day_outside_the_range_is_left_out(self, db):
        path, s = db
        out = ok(path, "shop", "calendar", "show", "--shop", s["shop"],
                 "--from", TUESDAY, "--to", TUESDAY)
        assert "Sam Ortiz" in out and "Dana Reyes" not in out and "Lift A" not in out


class TestIcal:
    def test_the_file_is_a_valid_calendar_with_one_event_per_row(self, db, tmp_path):
        path, s = db
        raw = _export(path, s, tmp_path)
        lines = _unfold(raw)
        assert lines[0] == "BEGIN:VCALENDAR" and lines[-1] == "END:VCALENDAR"
        assert "VERSION:2.0" in lines and "METHOD:PUBLISH" in lines
        assert any(line.startswith("PRODID:") for line in lines)
        assert all(len(p.encode("utf-8")) <= 75 for p in raw.decode("utf-8").split("\r\n"))
        events = _events(raw)
        assert sorted(e["UID"] for e in events) == sorted([
            f"appointment-1@motodiag-shop-{s['shop']}",
            f"appointment-2@motodiag-shop-{s['shop']}",
            f"bay-slot-{s['slot']['slot']}@motodiag-shop-{s['shop']}",
        ])
        for e in events:
            assert e["DTSTAMP"].endswith("Z") and len(e["DTSTAMP"]) == 16

    def test_times_are_the_shops_clock_time(self, db, tmp_path):
        path, s = db
        by_uid = {e["UID"].split("@")[0]: e for e in _events(_export(path, s, tmp_path))}
        assert by_uid["appointment-1"]["DTSTART"] == "20261005T090000"
        assert by_uid["appointment-1"]["DTEND"] == "20261005T100000"
        slot = by_uid[f"bay-slot-{s['slot']['slot']}"]
        assert (slot["DTSTART"], slot["DTEND"]) == ("20261005T110000", "20261005T130000")

    def test_a_slot_stored_in_another_zone_is_written_in_utc(self, db, tmp_path):
        path, s = db
        sql(path, "UPDATE bay_schedule_slots SET scheduled_start = ?, scheduled_end = ?",
            (f"{MONDAY}T11:00:00-04:00", f"{MONDAY}T13:00:00-04:00"))
        by_uid = {e["UID"].split("@")[0]: e for e in _events(_export(path, s, tmp_path))}
        slot = by_uid[f"bay-slot-{s['slot']['slot']}"]
        assert (slot["DTSTART"], slot["DTEND"]) == ("20261005T150000Z", "20261005T170000Z")

    def test_text_is_escaped(self, db, tmp_path):
        path, s = db
        by_uid = {e["UID"].split("@")[0]: e for e in _events(_export(path, s, tmp_path))}
        description = by_uid["appointment-1"]["DESCRIPTION"]
        assert "Notes: Hard start\\; stalls\\, then dies\\nsecond line" in description
        assert "Customer: Dana Reyes\\nBike: 2020 Honda CB500F" in description

    def test_a_long_line_folds_without_splitting_a_character(self, db, tmp_path):
        path, s = db
        sql(path, "UPDATE appointments SET notes = ? WHERE id = 1", ("Zündkerze ölig " * 12,))
        raw = _export(path, s, tmp_path)
        raw.decode("utf-8")  # every physical line is whole UTF-8
        physical = raw.decode("utf-8").split("\r\n")
        assert any(line.startswith(" ") for line in physical)
        assert all(len(p.encode("utf-8")) <= 75 for p in physical)
        by_uid = {e["UID"].split("@")[0]: e for e in _events(raw)}
        assert ("Notes: " + "Zündkerze ölig " * 12).rstrip() in by_uid["appointment-1"]["DESCRIPTION"]

    def test_status_follows_the_row(self, db, tmp_path):
        path, s = db
        ok(path, "shop", "appointment", "confirm", "1", "--channel", "phone")
        ok(path, "shop", "appointment", "cancel", "2")
        by_uid = {e["UID"].split("@")[0]: e for e in _events(_export(path, s, tmp_path))}
        assert by_uid["appointment-1"]["STATUS"] == "CONFIRMED"
        assert by_uid["appointment-2"]["STATUS"] == "CANCELLED"
        assert by_uid[f"bay-slot-{s['slot']['slot']}"]["STATUS"] == "TENTATIVE"

    def test_a_checked_in_appointment_names_its_work_order(self, db, tmp_path):
        path, s = db
        ok(path, "shop", "appointment", "check-in", "1")
        wo = sql(path, "SELECT work_order_id FROM appointments WHERE id = 1")[0][0]
        by_uid = {e["UID"].split("@")[0]: e for e in _events(_export(path, s, tmp_path))}
        assert f"Work order: #{wo}" in by_uid["appointment-1"]["DESCRIPTION"]

    def test_an_existing_file_is_not_overwritten(self, db, tmp_path):
        path, s = db
        target = tmp_path / "keep.ics"
        target.write_text("mine")
        out = refused(path, "shop", "calendar", "export", "--shop", s["shop"],
                      "--from", MONDAY, "--to", TUESDAY, "--out", str(target))
        assert "already exists" in out
        assert target.read_text() == "mine"

    def test_mechanic_and_bay_together_are_refused(self, db, tmp_path):
        path, s = db
        refused(path, "shop", "calendar", "export", "--shop", s["shop"], "--from", MONDAY,
                "--to", TUESDAY, "--mechanic", s["alex"], "--bay", s["slot"]["bay"],
                "--out", str(tmp_path / "x.ics"))
