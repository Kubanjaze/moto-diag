"""Phase 361 — F178, part 1a: no stored powertrain value can hide a safety rule.

`SafetyChecker._applies` showed every rule only for `None`. Any other value
outside `("ice", "hybrid")` dropped the seven combustion rules, the fuel-leak
warning among them: measured at Step 0 (`361_step0.md`, S0-3) for
`hybrid_parallel` and `hybrid_series`, which the API's PATCH stored, and for
`""` and `ICE`. Now any value outside `PowertrainType` reads as unknown.

Every database is a fresh one under `tmp_path`, never `data/motodiag.db`.
The bike row is written with plain SQL, as an old API or a raw insert
would have left it.
"""

from __future__ import annotations

import io
import sqlite3
from types import SimpleNamespace

import pytest
from rich.console import Console

from motodiag.core.database import init_db
from motodiag.engine.safety import SAFETY_RULES, SafetyChecker
from motodiag.vehicles.registry import get_vehicle

LEAK = "fuel leak pooling under the tank"
FUEL = "Fuel leak detected"

#: Every value Step 0 saw hide the rules, plus two a raw insert could leave.
OUTSIDE_THE_ENUM = [None, "", "ICE", "Hybrid", "hybrid_parallel", "hybrid_series",
                    "petrol", " ice"]


def _titles(powertrain) -> list[str]:
    return [a.title for a in SafetyChecker(powertrain=powertrain).check_diagnosis(LEAK)]


class TestTheChecker:
    @pytest.mark.parametrize("value", OUTSIDE_THE_ENUM)
    def test_a_value_outside_the_enum_shows_every_rule(self, value):
        assert len(SafetyChecker(powertrain=value)._compiled_rules) == len(SAFETY_RULES)
        assert FUEL in _titles(value)

    @pytest.mark.parametrize("value", ["ice", "hybrid"])
    def test_combustion_powertrains_show_the_fuel_leak(self, value):
        assert FUEL in _titles(value)

    def test_electric_still_drops_the_combustion_rules(self):
        """Control: scoping still works for a stated value, so the tests above
        do not pass because scoping was switched off."""
        scoped = [r for r in SAFETY_RULES if r.get("applies_to")]
        assert len(scoped) == 7
        assert FUEL not in _titles("electric")
        assert len(SafetyChecker(powertrain="electric")._compiled_rules) == (
            len(SAFETY_RULES) - len(scoped))

    def test_an_enum_member_is_read_as_its_value(self):
        from motodiag.core.models import PowertrainType
        assert FUEL not in _titles(PowertrainType.ELECTRIC)
        assert FUEL in _titles(PowertrainType.HYBRID)


class TestTheDiagnosePanel:
    """The user's entry point: `motodiag diagnose` prints `_render_safety`,
    which builds the checker from the bike's stored powertrain."""

    @pytest.fixture
    def db(self, tmp_path):
        path = str(tmp_path / "phase361.db")
        init_db(path)
        return path

    def _bike(self, db, powertrain) -> dict:
        conn = sqlite3.connect(db)
        try:
            cur = conn.execute(
                "INSERT INTO vehicles (make, model, year, powertrain) VALUES (?, ?, ?, ?)",
                ("Honda", "CB500", 2020, powertrain))
            conn.commit()
            vid = cur.lastrowid
        finally:
            conn.close()
        return get_vehicle(vid, db_path=db)

    def _panel(self, vehicle) -> str:
        from motodiag.cli import diagnose

        out = io.StringIO()
        response = SimpleNamespace(notes=LEAK, diagnoses=[])
        diagnose._render_safety(Console(file=out, width=200), response,
                                vehicle=vehicle, symptoms=[])
        return out.getvalue()

    @pytest.mark.parametrize("value", ["hybrid_parallel", "hybrid_series", ""])
    def test_a_bike_stored_with_an_old_value_gets_the_fuel_leak_warning(self, db, value):
        vehicle = self._bike(db, value)
        assert vehicle["powertrain"] == value
        assert FUEL in self._panel(vehicle)

    def test_the_panel_can_tell_the_difference(self, db):
        """Control: the same text on a bike stored as electric shows no
        combustion warning."""
        assert FUEL not in self._panel(self._bike(db, "electric"))
