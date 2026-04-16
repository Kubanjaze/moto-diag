"""Phase 04 — vehicle registry CRUD tests."""

import pytest
from motodiag.core.database import init_db
from motodiag.core.models import VehicleBase, ProtocolType
from motodiag.vehicles.registry import (
    add_vehicle, get_vehicle, list_vehicles, update_vehicle,
    delete_vehicle, count_vehicles,
)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def sportster(db_path):
    v = VehicleBase(
        make="Harley-Davidson", model="Sportster 1200",
        year=2001, engine_cc=1200, protocol=ProtocolType.J1850,
    )
    vid = add_vehicle(v, db_path)
    return vid


@pytest.fixture
def cbr(db_path):
    v = VehicleBase(
        make="Honda", model="CBR929RR",
        year=2001, engine_cc=929, protocol=ProtocolType.K_LINE,
    )
    return add_vehicle(v, db_path)


class TestAddVehicle:
    def test_returns_id(self, sportster):
        assert sportster > 0

    def test_multiple(self, sportster, cbr):
        assert sportster != cbr


class TestGetVehicle:
    def test_found(self, db_path, sportster):
        v = get_vehicle(sportster, db_path)
        assert v["make"] == "Harley-Davidson"
        assert v["year"] == 2001

    def test_not_found(self, db_path):
        assert get_vehicle(999, db_path) is None


class TestListVehicles:
    def test_all(self, db_path, sportster, cbr):
        results = list_vehicles(db_path=db_path)
        assert len(results) == 2

    def test_filter_make(self, db_path, sportster, cbr):
        results = list_vehicles(make="Honda", db_path=db_path)
        assert len(results) == 1
        assert results[0]["model"] == "CBR929RR"

    def test_filter_year(self, db_path, sportster, cbr):
        results = list_vehicles(year=2001, db_path=db_path)
        assert len(results) == 2

    def test_empty(self, db_path):
        assert list_vehicles(db_path=db_path) == []


class TestUpdateVehicle:
    def test_update(self, db_path, sportster):
        assert update_vehicle(sportster, {"notes": "Needs new stator"}, db_path)
        v = get_vehicle(sportster, db_path)
        assert v["notes"] == "Needs new stator"

    def test_invalid_field_ignored(self, db_path, sportster):
        assert not update_vehicle(sportster, {"hacker": "drop table"}, db_path)


class TestDeleteVehicle:
    def test_delete(self, db_path, sportster):
        assert delete_vehicle(sportster, db_path)
        assert get_vehicle(sportster, db_path) is None

    def test_delete_nonexistent(self, db_path):
        assert not delete_vehicle(999, db_path)


class TestCount:
    def test_count(self, db_path, sportster, cbr):
        assert count_vehicles(db_path) == 2

    def test_empty(self, db_path):
        assert count_vehicles(db_path) == 0
