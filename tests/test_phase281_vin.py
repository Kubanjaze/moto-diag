"""Phase 281, row 287: VIN decoding by NHTSA vPIC.

A decode is stored per VIN with its date and asked again only on request. A
partial decode says so, with vPIC's own error text. With vPIC down, the
command names it and shows the offline decode labelled as maker and year
only. `--save` writes a VIN to a bike that has none and never changes its
make, model or year. vPIC is never called: answers are the recorded smoke
response (a made-up VIN, decoded partially) and a clean decode built from its
format.
"""

from __future__ import annotations

import pytest

from support.phase281 import UNREACHABLE, fixture, new_db, ok, refused, seed_bike, serve, sql

PARTIAL = fixture("vpic_partial_1HD1FRW177Y600001.json")
CLEAN = fixture("vpic_clean_built.json")


@pytest.fixture
def db(tmp_path):
    return new_db(tmp_path)


class TestDecode:
    def test_a_partial_decode_is_labelled_with_vpics_own_text(self, db, monkeypatch):
        asked = serve(monkeypatch, {"vpic.nhtsa.dot.gov": (200, PARTIAL)})
        out = ok(db, "advanced", "vin", "decode", "1hd1frw177y600001")
        assert asked == ["https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/"
                         "1HD1FRW177Y600001?format=json&modelyear=2007"]
        assert "Manufacturer: HARLEY-DAVIDSON MOTOR COMPANY" in out
        assert "Model year: 2007" in out
        assert "Make: not given" in out
        assert "Partial decode. vPIC error 3,14: 3 - VIN corrected" in out
        row = sql(db, "SELECT vin, make, model, model_year, vehicle_type, error_code "
                      "FROM vin_decodes")
        assert row == [("1HD1FRW177Y600001", None, None, 2007, "MOTORCYCLE", "3,14")]

    def test_a_stored_decode_is_not_asked_for_again_unless_refreshed(self, db, monkeypatch):
        asked = serve(monkeypatch, {"vpic.nhtsa.dot.gov": (200, CLEAN)})
        ok(db, "advanced", "vin", "decode", "JH2RC5007LM200001")
        out = ok(db, "advanced", "vin", "decode", "JH2RC5007LM200001")
        assert len(asked) == 1
        assert "Model: CBR1000RR" in out and "Partial decode" not in out
        ok(db, "advanced", "vin", "decode", "JH2RC5007LM200001", "--refresh")
        assert len(asked) == 2
        assert sql(db, "SELECT COUNT(*) FROM vin_decodes")[0][0] == 1

    def test_an_invalid_vin_is_refused_before_any_request(self, db, monkeypatch):
        asked = serve(monkeypatch, {})
        assert "forbidden character" in refused(db, "advanced", "vin", "decode",
                                                "1HD1FRW17OY600001")
        assert asked == []

    @pytest.mark.parametrize("answer, said", [
        (UNREACHABLE, "NHTSA vPIC could not be reached"),
        ((503, fixture("service_error_503_built.html")),
         "NHTSA vPIC answered with an error: HTTP 503"),
        ((200, b'{"Count":0,"Results":[]}'), "expected one decoded result"),
    ])
    def test_vpic_down_shows_the_offline_decode_labelled(self, db, monkeypatch, answer, said):
        serve(monkeypatch, {"vpic.nhtsa.dot.gov": answer})
        out = refused(db, "advanced", "vin", "decode", "1HD1FRW177Y600001")
        assert said in out
        assert "Offline: maker and year only" in out
        assert "Make: Harley-Davidson" in out and "Year: 2007" in out
        assert sql(db, "SELECT COUNT(*) FROM vin_decodes")[0][0] == 0


class TestSave:
    def test_save_writes_the_vin_and_keeps_the_bikes_own_details(self, db, monkeypatch):
        seed_bike(db, make="Honda", model="Fireblade", year=2020)
        serve(monkeypatch, {"vpic.nhtsa.dot.gov": (200, CLEAN)})
        out = ok(db, "advanced", "vin", "decode", "JH2RC5007LM200001", "--bike", "honda-2020",
                 "--save")
        assert "The bike's model is 'Fireblade'; vPIC gives 'CBR1000RR'. The bike's is kept." \
            in out
        assert "VIN saved to bike 1" in out
        assert sql(db, "SELECT make, model, year, vin FROM vehicles") == [
            ("Honda", "Fireblade", 2020, "JH2RC5007LM200001")]

    def test_a_bike_with_another_vin_is_not_changed(self, db, monkeypatch):
        seed_bike(db, make="Honda", model="CBR1000RR", year=2020, vin="JH2SC5900LM000001")
        serve(monkeypatch, {"vpic.nhtsa.dot.gov": (200, CLEAN)})
        out = refused(db, "advanced", "vin", "decode", "JH2RC5007LM200001", "--bike",
                      "honda-2020", "--save")
        assert "already has VIN JH2SC5900LM000001; it is not replaced" in out
        assert sql(db, "SELECT vin FROM vehicles")[0][0] == "JH2SC5900LM000001"

    def test_save_needs_a_bike(self, db):
        refused(db, "advanced", "vin", "decode", "JH2RC5007LM200001", "--save")


class TestRecallRefreshByVin:
    def test_a_partial_decode_cannot_ask_nhtsa(self, db, monkeypatch):
        asked = serve(monkeypatch, {"vpic.nhtsa.dot.gov": (200, PARTIAL)})
        out = refused(db, "advanced", "recall", "refresh", "--vin", "1HD1FRW177Y600001")
        assert "vPIC did not give a make, model and year" in out
        assert len(asked) == 1, "NHTSA's recall service was not asked"

    def test_a_clean_decode_asks_for_its_model_year(self, db, monkeypatch):
        asked = serve(monkeypatch, {
            "vpic.nhtsa.dot.gov": (200, CLEAN),
            "recallsByVehicle": (400, fixture("nhtsa_recalls_none_400.json"))})
        out = ok(db, "advanced", "recall", "refresh", "--vin", "JH2RC5007LM200001")
        assert "vPIC: 2020 HONDA CBR1000RR" in out
        assert "make=HONDA&model=CBR1000RR&modelYear=2020" in asked[1]
