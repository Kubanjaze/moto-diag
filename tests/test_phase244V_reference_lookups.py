"""Phase 244V — the reference data a technician asks for mid-job.

Phases 92 and 93 shipped four reference tables — 20 torque specs, 8 valve
clearances, 14 service intervals, 5 wiring circuits — each with lookups, each
tested in isolation, and **no command or route reached any of it**. The 209B
reachability gate could not see that: ``engine/__init__`` re-exported the
names, and until 244U a re-export counted as a use.

Every test here goes through the CLI, because that is the claim being made:
not that `get_torque_spec` returns a value, which was already true and already
tested, but that a person can get one.

Two things are pinned harder than the rendering:

* **provenance on every screen.** These are generic authored values. The
  modules said so in a docstring, which is not where anyone reads a number.
  F86 is the cautionary case in this repo: a fixture whose fabricated federal
  campaign numbers read as real for five months because nothing at the point
  of use said otherwise.
* **a miss says what exists.** 244R fixed the same silence for
  ``code --category``. A lookup that finds nothing is the moment the user most
  needs the vocabulary.
"""

from __future__ import annotations

import re

import pytest
from click.testing import CliRunner

from motodiag.cli.reference import PROVENANCE
from motodiag.engine.service_data import (
    COMMON_SERVICE_INTERVALS,
    COMMON_TORQUE_SPECS,
    COMMON_VALVE_CLEARANCES,
)
from motodiag.engine.wiring import CIRCUIT_REFERENCES


@pytest.fixture(autouse=True)
def wide_console(monkeypatch):
    """Rich folds a long cell across lines, and flattening the output then
    interleaves the columns — "Inline-4 intake valve (typical)" arrives as
    "Inline-4 intake valve ... (typical)" with two other cells in between.
    Widening the virtual terminal is the convention this repo already uses
    (`test_phase128_kb.py:61`); the console is a singleton, so it is reset on
    both sides."""
    from motodiag.cli.theme import reset_console

    reset_console()
    monkeypatch.setenv("COLUMNS", "220")
    yield
    reset_console()


def _run(*args):
    from motodiag.cli.main import cli

    return CliRunner().invoke(cli, list(args))


def _flat(text: str) -> str:
    """Rich wraps inside table cells and panel borders; compare on words."""
    stripped = re.sub(r"[│╭╮╰╯─━┃┏┓┗┛┡┩╇┳┻╋┼]", " ", text)
    return re.sub(r"\s+", " ", stripped).strip()


ALL_COMMANDS = ["torque", "valve", "interval", "circuit"]


# ---------------------------------------------------------------------------
# 1. It is reachable at all
# ---------------------------------------------------------------------------


class TestTheDataIsReachable:
    @pytest.mark.parametrize("command", ALL_COMMANDS)
    def test_the_command_exists(self, command):
        result = _run("ref", command, "--help")
        assert result.exit_code == 0, result.output

    def test_the_group_is_on_the_root_cli(self):
        assert "ref" in _flat(_run("--help").output)

    def test_a_torque_spec_reaches_the_screen(self):
        out = _flat(_run("ref", "torque", "drain plug").output)
        assert "Oil drain plug (M12)" in out
        assert "20" in out

    def test_a_valve_clearance_reaches_the_screen(self):
        out = _flat(_run("ref", "valve", "inline-4 intake").output)
        assert "0.1" in out and "0.2" in out

    def test_a_service_interval_reaches_the_screen(self):
        out = _flat(_run("ref", "interval", "brake fluid").output)
        assert "Brake fluid flush" in out
        assert "24" in out

    def test_a_circuit_reaches_the_screen(self):
        out = _flat(_run("ref", "circuit", "charging").output)
        assert "Yellow (3 wires)" in out
        assert "50-80V AC at 5000 RPM" in out

    def test_the_whole_torque_table_lists(self):
        out = _flat(_run("ref", "torque").output)
        for spec in COMMON_TORQUE_SPECS:
            assert spec["fastener"] in out, f"missing from the table: {spec['fastener']}"

    def test_the_whole_interval_table_lists(self):
        out = _flat(_run("ref", "interval").output)
        for interval in COMMON_SERVICE_INTERVALS:
            assert interval["service_item"] in out

    def test_the_whole_clearance_table_lists(self):
        out = _flat(_run("ref", "valve").output)
        for clearance in COMMON_VALVE_CLEARANCES:
            assert clearance["component"] in out

    def test_every_circuit_is_listed_by_name(self):
        out = _flat(_run("ref", "circuit").output)
        for circuit in CIRCUIT_REFERENCES:
            assert circuit["circuit_name"] in out


# ---------------------------------------------------------------------------
# 2. Provenance, on every screen
# ---------------------------------------------------------------------------


class TestProvenanceIsOnEveryScreen:
    @pytest.mark.parametrize("args", [
        ["torque"], ["torque", "drain plug"],
        ["valve"], ["valve", "inline-4 intake"],
        ["interval"], ["interval", "brake fluid"],
        ["circuit"], ["circuit", "charging"], ["circuit", "--system", "electrical"],
    ])
    def test_a_result_carries_its_provenance(self, args):
        """Every successful screen, not a representative sample: the one that
        forgets is the one someone torques a caliper bolt from."""
        out = _flat(_run("ref", *args).output)
        assert "not manufacturer data" in out
        assert "service manual" in out

    def test_the_wording_is_the_module_constant(self):
        """Rendered from one string, so it cannot drift per command."""
        out = _flat(_run("ref", "torque", "drain plug").output)
        assert _flat(PROVENANCE) in out

    @pytest.mark.parametrize("claim", [
        "official", "oem ", "factory spec", "manufacturer spec",
        "manufacturer-specified", "per the manufacturer",
    ])
    def test_it_does_not_claim_a_manufacturer(self, claim):
        """The inverse of the provenance line: it must not only say the right
        thing, it must not say the wrong one. "not manufacturer data" is the
        only occurrence of the word that should survive here."""
        assert claim not in _flat(_run("ref", "torque").output).lower(), (
            f"the reference screen must not imply {claim!r}"
        )

    def test_torque_warns_before_the_numbers_not_after(self):
        """A torque figure is acted on the moment it is read. The warning
        above the table is read; a footer under 20 rows is not."""
        out = _flat(_run("ref", "torque").output)
        warning = out.index("check the manual for THIS bike")
        first_number = out.index("Oil drain plug (M12)")
        assert warning < first_number

    def test_the_torque_warning_says_what_goes_wrong_both_ways(self):
        out = _flat(_run("ref", "torque").output).lower()
        assert "brake failure" in out, "under-torque"
        assert "strips an aluminium case" in out, "over-torque"

    def test_the_clearances_say_they_are_cold(self):
        """True of all 8 rows and stated in none of them — obvious to whoever
        wrote the table, invisible to whoever reads one row."""
        assert "COLD" in _flat(_run("ref", "valve", "harley twin cam intake").output)


# ---------------------------------------------------------------------------
# 3. A miss says what exists
# ---------------------------------------------------------------------------


class TestAMissIsUseful:
    @pytest.mark.parametrize("command,query", [
        ("torque", "flux capacitor bolt"),
        ("valve", "wankel rotor tip seal"),
        ("interval", "warp coil realignment"),
        ("circuit", "hyperdrive"),
    ])
    def test_a_miss_exits_nonzero(self, command, query):
        assert _run("ref", command, query).exit_code == 1

    @pytest.mark.parametrize("command,query,expected", [
        ("torque", "flux capacitor bolt", "Oil drain plug (M12)"),
        ("valve", "wankel rotor tip seal", "Harley Twin Cam intake"),
        ("interval", "warp coil realignment", "Chain adjustment and lube"),
        ("circuit", "hyperdrive", "ABS wheel speed sensor circuit"),
    ])
    def test_a_miss_lists_what_is_available(self, command, query, expected):
        out = _flat(_run("ref", command, query).output)
        assert "Nothing matches" in out
        assert expected in out, "the user needs the vocabulary, not an empty screen"

    def test_an_unknown_system_lists_the_real_systems(self):
        out = _flat(_run("ref", "circuit", "--system", "hydraulics").output)
        assert "electrical" in out and "braking" in out
        assert "Charging circuit" not in out, (
            "the systems are the vocabulary here, not the circuit names"
        )

    def test_a_miss_does_not_print_an_empty_table(self):
        """Printing headers with no rows reads as 'there is nothing for this
        bike' rather than 'that is not a name I know'."""
        out = _flat(_run("ref", "torque", "flux capacitor bolt").output)
        assert "Torque specifications" not in out


# ---------------------------------------------------------------------------
# 4. The query itself
# ---------------------------------------------------------------------------


class TestTheLookup:
    def test_the_match_is_case_insensitive(self):
        assert "Oil drain plug (M12)" in _flat(_run("ref", "torque", "DRAIN PLUG").output)

    def test_a_partial_match_returns_the_first_of_several(self):
        """Both M12 and M14 drain plugs match 'drain plug'. The repo's lookup
        returns one; pinned so the CLI is not blamed for the ambiguity, and so
        that a later fix to return all of them shows up here."""
        out = _flat(_run("ref", "torque", "drain plug").output)
        assert "Oil drain plug (M12)" in out
        assert "Oil drain plug (M14)" not in out

    def test_a_system_filter_returns_every_circuit_in_it(self):
        out = _flat(_run("ref", "circuit", "--system", "electrical").output)
        assert "Charging circuit" in out
        assert "Starting circuit" in out
        assert "Fuel injection" not in out

    def test_the_system_label_survives_rendering(self):
        """`[electrical]` in a panel title is markup to rich, which silently
        drops it. Caught in the smoke test, not by a reviewer."""
        assert "(electrical)" in _flat(_run("ref", "circuit", "charging").output)

    def test_a_zero_interval_renders_as_absent_not_as_zero(self):
        """Brake fluid is time-based: 0 miles means 'not measured in miles',
        and '0' next to a mileage column means 'change it now'."""
        out = _flat(_run("ref", "interval", "brake fluid").output)
        assert "Brake fluid flush — 0" not in out
        assert re.search(r"Brake fluid flush\s+—\s+—\s+24", out), out


# ---------------------------------------------------------------------------
# 5. The diagnostic content, which is the reason to wire the wiring
# ---------------------------------------------------------------------------


class TestACircuitRendersWhatTheJobNeeds:
    def test_the_test_points_are_shown(self):
        out = _flat(_run("ref", "circuit", "charging").output)
        assert "Test points" in out
        assert "AC voltage across all 3 pairs at 5000 RPM" in out

    def test_the_common_failures_are_shown(self):
        out = _flat(_run("ref", "circuit", "charging").output)
        assert "Common failures" in out
        assert "Stator winding shorted to ground" in out

    def test_the_diagnostic_tips_are_shown(self):
        out = _flat(_run("ref", "circuit", "starting").output)
        assert "Diagnostic tips" in out

    def test_the_expected_readings_are_shown(self):
        """A wire colour without a number is a picture; the number is the test."""
        out = _flat(_run("ref", "circuit", "ignition").output)
        assert "ohm" in out.lower() or "V" in out

    def test_the_applicable_makes_are_shown(self):
        out = _flat(_run("ref", "circuit", "abs").output)
        assert "Honda" in out and "Harley-Davidson" in out


# ---------------------------------------------------------------------------
# 6. What this phase does not claim
# ---------------------------------------------------------------------------


class TestWhatIsStillUnwired:
    def test_the_prompt_builders_are_deliberately_not_wired(self):
        """`build_service_data_context` and `build_wiring_context` render
        generic numbers into prompt text. Feeding "typical Japanese rear axle
        nut: 100 Nm" to a model asked about a specific bike invites it to
        state that figure as the bike's own. They stay on the shelf, and the
        allowlist still carries them.

        This is a documenting test: delete it when a phase wires them WITH a
        way for the answer to say which numbers are generic."""
        from support.integration_gaps_allowlist import ORPHANS

        assert "engine/service_data.py::build_service_data_context" in ORPHANS
        assert "engine/wiring.py::build_wiring_context" in ORPHANS

    def test_no_new_reference_data_was_authored(self):
        """244V wires what Phases 92/93 wrote. Authoring torque figures for a
        bike I cannot measure is how fabricated data gets in — see F86."""
        assert len(COMMON_TORQUE_SPECS) == 20
        assert len(COMMON_VALVE_CLEARANCES) == 8
        assert len(COMMON_SERVICE_INTERVALS) == 14
        assert len(CIRCUIT_REFERENCES) == 5

    def test_there_is_no_api_or_app_surface(self):
        """Explicit non-goal. Gate 11 pins the mobile app's OpenAPI snapshot
        against the running API, so a route here would need a snapshot refresh
        and regenerated types — a separate phase, not a rider on this one."""
        from pathlib import Path

        routes = Path("src/motodiag/api")
        hits = [
            f"{p}:{i}"
            for p in routes.rglob("*.py")
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if "service_data" in line or "engine.wiring" in line
        ]
        assert hits == [], f"the API now reaches the reference data: {hits}"
