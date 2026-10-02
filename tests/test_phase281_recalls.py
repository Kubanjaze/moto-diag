"""Phase 281, row 281: recalls refreshed from NHTSA, and what a lookup may say.

The recall service is never called: answers are the recorded fixtures (the
build's smoke response for PIAGGIO MP3 500 2020, NHTSA's HTTP 400
zero-result body, an Akamai block page). F103's rules are what these hold: a
failure is never an empty result; zero results are never an all-clear; a
refresh of every bike first asks for a campaign known to exist.
"""

from __future__ import annotations

import json

import pytest

from motodiag.advanced.recall_repo import list_open_for_bike
from support.phase281 import UNREACHABLE, fixture, new_db, ok, refused, seed_bike, serve, sql

MP3 = fixture("nhtsa_recalls_mp3_500_2020.json")
NONE_400 = fixture("nhtsa_recalls_none_400.json")
BLOCKED = fixture("nhtsa_blocked_403.html")
REFRESH_MP3 = ("advanced", "recall", "refresh", "--make", "PIAGGIO", "--model", "MP3 500",
               "--year", "2020")


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


def _flat(text: str) -> str:
    import re
    return re.sub(r"\s+", " ", re.sub(r"[│╭╮╰╯─]", " ", text))


def _mp3_ok(monkeypatch):
    return serve(monkeypatch, {"recallsByVehicle": (200, MP3)})


class TestRefresh:
    def test_campaigns_are_stored_with_their_fetch(self, db, monkeypatch):
        asked = _mp3_ok(monkeypatch)
        out = ok(db, *REFRESH_MP3)
        assert asked == ["https://api.nhtsa.gov/recalls/recallsByVehicle?make=PIAGGIO"
                         "&model=MP3%20500&modelYear=2020"]
        assert "NHTSA: 2 campaign(s) for 2020 PIAGGIO MP3 500, fetched" in out
        assert "20V524000" in out and "22V217000" in out
        assert "Whether this VIN is included is not in NHTSA's public data" in _flat(out)
        rows = sql(db, "SELECT campaign_number, nhtsa_id, make, model, year_start, source, "
                       "severity, notification_date, component FROM recalls ORDER BY 1")
        assert rows[0] == ("20V524000", "20V524000", "PIAGGIO", None, None, "nhtsa",
                           "unrated", "2020-08-28", "SERVICE BRAKES, HYDRAULIC")
        assert sql(db, "SELECT make, model, model_year FROM recall_vehicles") == [
            ("PIAGGIO", "MP3 500", 2020)] * 2
        assert sql(db, "SELECT outcome, http_status, result_count, error FROM "
                       "recall_fetches") == [("ok", 200, 2, None)]

    def test_nhtsas_park_flags_are_the_only_severity(self, db, monkeypatch):
        data = json.loads(MP3)
        data["results"][0]["parkIt"] = True             # built from the recorded answer
        data["results"][1]["parkOutSide"] = True
        serve(monkeypatch, {"recallsByVehicle": (200, json.dumps(data).encode())})
        ok(db, *REFRESH_MP3)
        assert {r[0] for r in sql(db, "SELECT severity FROM recalls")} == {"critical"}
        serve(monkeypatch, {"recallsByVehicle": (200, MP3)})
        ok(db, *REFRESH_MP3)
        assert {r[0] for r in sql(db, "SELECT severity FROM recalls")} == {"unrated"}
        assert "medium" not in {r[0] for r in sql(db, "SELECT severity FROM recalls")}

    def test_a_refresh_does_not_duplicate(self, db, monkeypatch):
        _mp3_ok(monkeypatch)
        ok(db, *REFRESH_MP3)
        ok(db, *REFRESH_MP3)
        assert sql(db, "SELECT COUNT(*) FROM recalls")[0][0] == 2
        assert sql(db, "SELECT COUNT(*) FROM recall_vehicles")[0][0] == 2
        assert sql(db, "SELECT COUNT(*) FROM recall_fetches")[0][0] == 2

    def test_one_of_the_ways_to_name_the_vehicle_is_required(self, db):
        refused(db, "advanced", "recall", "refresh")
        refused(db, "advanced", "recall", "refresh", "--make", "PIAGGIO", "--all-bikes")


class TestZeroIsNotAllClear:
    def test_nhtsas_400_zero_body_is_an_answer_of_none_as_named(self, db, monkeypatch):
        serve(monkeypatch, {"recallsByVehicle": (400, NONE_400)})
        out = _flat(ok(db, "advanced", "recall", "refresh", "--make", "Honda", "--model",
                       "Grom", "--year", "2016"))
        assert "0 campaign(s)" in out
        assert "NHTSA listed no recall for 2016 HONDA GROM as named" in out
        assert "this is not an all-clear" in out
        assert sql(db, "SELECT outcome, http_status, result_count FROM recall_fetches") == [
            ("ok", 400, 0)]
        out = _flat(ok(db, "advanced", "recall", "lookup", "--make", "Honda", "--model",
                       "Grom", "--year", "2016"))
        assert "NHTSA listed no recall" in out and "not an all-clear" in out
        assert "Clear" not in out.replace("all-clear", "")

    def test_a_400_with_campaigns_or_no_json_is_an_error(self, db, monkeypatch):
        serve(monkeypatch, {"recallsByVehicle": (400, MP3)})
        assert "answered with an error: HTTP 400" in refused(db, *REFRESH_MP3)
        serve(monkeypatch, {"recallsByVehicle": (400, b"Bad Request")})
        assert "could not be read" in refused(db, *REFRESH_MP3)

    def test_a_count_that_disagrees_with_the_results_is_refused(self, db, monkeypatch):
        data = json.loads(MP3)
        data["Count"] = 5
        serve(monkeypatch, {"recallsByVehicle": (200, json.dumps(data).encode())})
        assert "it gave Count 5 with 2 results" in refused(db, *REFRESH_MP3)
        assert sql(db, "SELECT COUNT(*) FROM recalls")[0][0] == 0

    def test_a_model_never_fetched_says_so(self, db, monkeypatch):
        _mp3_ok(monkeypatch)
        ok(db, *REFRESH_MP3)
        out = _flat(ok(db, "advanced", "recall", "lookup", "--make", "PIAGGIO", "--model",
                       "Beverly 350", "--year", "2020"))
        assert "No recall data is fetched for 2020 PIAGGIO Beverly 350" in out
        assert "NOT an all-clear" in out
        assert "20V524000" not in out, "a fetched campaign never covers a whole make"


class TestTheServiceDown:
    @pytest.mark.parametrize("answer, said", [
        ((403, BLOCKED), "NHTSA recalls refused the request: HTTP 403"),
        ((200, BLOCKED), "NHTSA recalls refused the request: HTTP 200 with a web page"),
        (UNREACHABLE, "NHTSA recalls could not be reached"),
        ((503, fixture("service_error_503_built.html")),
         "NHTSA recalls answered with an error: HTTP 503"),
    ])
    def test_a_failure_is_named_and_never_empty(self, db, monkeypatch, answer, said):
        serve(monkeypatch, {"recallsByVehicle": answer})
        out = _flat(refused(db, *REFRESH_MP3))
        assert said in out
        assert "Nothing is stored for this model." in out
        assert "0 campaign" not in out and "no recall" not in out.lower()
        assert sql(db, "SELECT outcome, result_count FROM recall_fetches") == [("failed", None)]

    def test_stored_data_survives_a_failed_refresh_and_is_shown(self, db, monkeypatch):
        _mp3_ok(monkeypatch)
        ok(db, *REFRESH_MP3)
        serve(monkeypatch, {"recallsByVehicle": (403, BLOCKED)})
        out = _flat(refused(db, *REFRESH_MP3))
        assert "Stored recalls for 2020 PIAGGIO MP3 500 (not refreshed)" in out
        assert "20V524000" in out
        assert sql(db, "SELECT COUNT(*) FROM recalls")[0][0] == 2
        out = _flat(ok(db, "advanced", "recall", "lookup", "--make", "PIAGGIO", "--model",
                       "MP3 500", "--year", "2020"))
        assert "20V524000" in out


class TestBikes:
    def test_a_bike_is_refreshed_listed_and_resolved(self, db, monkeypatch):
        seed_bike(db, make="Piaggio", model="MP3-500", year=2020)
        _mp3_ok(monkeypatch)
        ok(db, "advanced", "recall", "refresh", "--bike", "piaggio-2020")
        out = _flat(ok(db, "advanced", "recall", "list", "--bike", "piaggio-2020"))
        assert "Open recalls for bike 1" in out and "20V524000" in out
        assert "No recall is recorded as resolved" in out
        recall_id = sql(db, "SELECT id FROM recalls WHERE campaign_number = '20V524000'")[0][0]
        ok(db, "advanced", "recall", "mark-resolved", "--bike", "piaggio-2020",
           "--recall-id", recall_id)
        out = _flat(ok(db, "advanced", "recall", "list", "--bike", "piaggio-2020"))
        assert "Resolved recalls for bike 1" in out
        assert [r["campaign_number"] for r in list_open_for_bike(1, db_path=db)] == [
            "22V217000"]

    def test_the_predictors_feed_matches_by_model_not_by_make(self, db, monkeypatch):
        seed_bike(db, make="Piaggio", model="MP3 500", year=2020)
        seed_bike(db, make="Piaggio", model="Beverly 350", year=2020)
        seed_bike(db, make="Piaggio", model="MP3 500", year=2018)
        _mp3_ok(monkeypatch)
        ok(db, *REFRESH_MP3)
        assert len(list_open_for_bike(1, db_path=db)) == 2
        assert list_open_for_bike(2, db_path=db) == []
        assert list_open_for_bike(3, db_path=db) == []

    def test_all_bikes_asks_for_the_known_campaign_first(self, db, monkeypatch):
        seed_bike(db, make="Honda", model="Grom", year=2016)
        seed_bike(db, make="Honda", model="", year=2016)
        slept = []
        monkeypatch.setattr("time.sleep", lambda s: slept.append(s))
        asked = serve(monkeypatch, {"model=MP3": (200, MP3), "model=Grom": (400, NONE_400)})
        out = ok(db, "advanced", "recall", "refresh", "--all-bikes")
        assert "model=MP3%20500" in asked[0]
        assert "2016 Honda Grom: 0 campaign(s)" in out
        assert "Skipped bike 2: no make, model and year" in out
        assert slept == [1.0]

    def test_all_bikes_stops_when_the_known_campaign_is_missing(self, db, monkeypatch):
        seed_bike(db, make="Honda", model="Grom", year=2016)
        asked = serve(monkeypatch, {"recallsByVehicle": (400, NONE_400)})
        out = _flat(refused(db, "advanced", "recall", "refresh", "--all-bikes"))
        assert "Stopped before any bike: NHTSA did not return campaign 20V524000" in out
        assert len(asked) == 1, "no bike was asked about"

    def test_all_bikes_lists_failures_and_exits_1(self, db, monkeypatch):
        seed_bike(db, make="Honda", model="Grom", year=2016)
        monkeypatch.setattr("time.sleep", lambda s: None)
        serve(monkeypatch, {"model=MP3": (200, MP3), "model=Grom": UNREACHABLE})
        out = _flat(refused(db, "advanced", "recall", "refresh", "--all-bikes"))
        assert "Not refreshed: 2016 Honda Grom: NHTSA recalls could not be reached" in out
        assert "Its stored data is unchanged" in out


class TestCheckVin:
    def test_check_vin_refresh_decodes_then_asks_for_the_model_year(self, db, monkeypatch):
        asked = serve(monkeypatch, {"vpic.nhtsa.dot.gov": (200, fixture("vpic_clean_built.json")),
                                    "recallsByVehicle": (400, NONE_400)})
        out = _flat(ok(db, "advanced", "recall", "check-vin", "JH2RC5007LM200001",
                       "--refresh"))
        assert "modelyear=2020" in asked[0]
        assert "model=CBR1000RR&modelYear=2020" in asked[1]
        assert "2020 HONDA CBR1000RR" in out
        assert "NHTSA listed no recall for 2020 HONDA CBR1000RR as named" in out
        # Without --refresh, the stored decode and fetch are used; nothing is asked.
        asked.clear()
        out = _flat(ok(db, "advanced", "recall", "check-vin", "JH2RC5007LM200001"))
        assert asked == []
        assert "NHTSA listed no recall" in out

    def test_vpic_down_is_named(self, db, monkeypatch):
        serve(monkeypatch, {"vpic.nhtsa.dot.gov": UNREACHABLE})
        out = refused(db, "advanced", "recall", "check-vin", "JH2RC5007LM200001", "--refresh")
        assert "NHTSA vPIC could not be reached" in out
