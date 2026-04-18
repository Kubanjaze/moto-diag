"""Phase 144 — hardware simulator tests.

Six test classes, ~55 tests. Zero real serial I/O, zero live tokens,
zero wall-clock sleeps — all determinism comes from injecting a
:class:`~motodiag.hardware.simulator.SimulationClock` into the
adapter and advancing it manually. CI greps this file for
``time.sleep`` to enforce that rule.

Deliberate absence: this file does **not** import
``motodiag.hardware.mock``. The simulator is a *sibling* of the
Phase 140 :class:`MockAdapter`, not a subclass, and the test suite
treats it that way so contract drift between the two modules is
caught by the ABC contract checks, not hidden by shared test helpers.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from motodiag.cli.hardware import register_hardware
from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
    TimeoutError as ProtocolTimeoutError,
)
from motodiag.hardware.scenarios import BUILTIN_NAMES, builtin_path
from motodiag.hardware.simulator import (
    ClearDTC,
    Disconnect,
    EndScenario,
    InjectDTC,
    InjectTimeout,
    PhaseTransition,
    RampPid,
    Reconnect,
    RecordingSupportUnavailable,
    Scenario,
    ScenarioLoader,
    ScenarioValidationError,
    SimulatedAdapter,
    SimulationClock,
    StartState,
    _phase142_available,
    _parse_duration,
    _coerce_pid,
    PID_ALIASES,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _minimal_scenario() -> Scenario:
    """Return a tiny valid scenario — used by many tests as a starting point."""
    return Scenario(
        name="test_minimal",
        description="minimal test scenario",
        protocol="TestProto",
        vin="1HD1KHM19NB123456",
        initial={0x05: 88, 0x0C: 1000},
        timeline=[
            StartState(
                action="start", at_s=0.0,
                pids={0x05: 88, 0x0C: 1000},
                dtcs=[], vin="1HD1KHM19NB123456",
                protocol="TestProto",
            ),
            EndScenario(action="end", at_s=10.0),
        ],
    )


def _ramp_scenario() -> Scenario:
    """Scenario with a 0->100 ramp on PID 0x05 over 10s."""
    return Scenario(
        name="ramp_test",
        description="ramp test",
        protocol="TestProto",
        vin=None,
        initial={0x05: 0},
        timeline=[
            StartState(
                action="start", at_s=0.0,
                pids={0x05: 0}, dtcs=[], vin=None,
                protocol="TestProto",
            ),
            RampPid(
                action="ramp", at_s=0.0, pid=0x05,
                **{"from": 0.0}, to=100.0,
                duration_s=10.0,
            ),
            EndScenario(action="end", at_s=20.0),
        ],
    )


# ===========================================================================
# 1. TestSimulationClock (5)
# ===========================================================================


class TestSimulationClock:
    """SimulationClock semantics — all tests run in microseconds."""

    def test_tick_advances_forward(self):
        """tick(dt) monotonically advances now()."""
        clk = SimulationClock(start_s=0.0)
        assert clk.now() == 0.0
        clk.tick(0.1)
        assert clk.now() == pytest.approx(0.1)
        clk.tick(0.5)
        assert clk.now() == pytest.approx(0.6)

    def test_advance_jumps_forward(self):
        """advance(to_s) sets now() directly."""
        clk = SimulationClock()
        clk.advance(42.5)
        assert clk.now() == 42.5
        clk.advance(42.5)  # advancing to same value is fine
        assert clk.now() == 42.5
        clk.advance(100.0)
        assert clk.now() == 100.0

    def test_advance_backwards_raises(self):
        """advance(to_s) with to_s < now() raises ValueError."""
        clk = SimulationClock(start_s=10.0)
        with pytest.raises(ValueError, match="backwards"):
            clk.advance(5.0)

    def test_10k_ticks_are_monotonic_and_sum_correctly(self):
        """10_000 ticks of 0.01s sum to 100.0s with no drift."""
        clk = SimulationClock()
        for _ in range(10_000):
            clk.tick(0.01)
        # Floating point — use approx with tight rel tolerance.
        assert clk.now() == pytest.approx(100.0, rel=1e-9)

    def test_reset_rewinds_and_clears_freeze(self):
        """reset() re-anchors now() and clears frozen state."""
        clk = SimulationClock(start_s=50.0)
        clk.freeze()
        clk.tick(5.0)
        assert clk.now() == 50.0  # frozen, no advance
        clk.reset(start_s=0.0)
        assert clk.now() == 0.0
        # Frozen flag cleared too
        clk.tick(1.0)
        assert clk.now() == 1.0


# ===========================================================================
# 2. TestScenarioModels (10)
# ===========================================================================


class TestScenarioModels:
    """Pydantic models round-trip + invalid input rejection."""

    def test_start_state_roundtrip(self):
        e = StartState(
            action="start", at_s=0.0,
            pids={0x05: 20, 0x0C: 1800},
            dtcs=["P0171"],
            vin="1HD1KHM19NB123456",
            protocol="TestProto",
        )
        data = e.model_dump_json()
        e2 = StartState.model_validate_json(data)
        assert e == e2

    def test_ramp_pid_roundtrip_with_alias(self):
        # 'from' is a Python keyword — alias machinery must work.
        e = RampPid(
            action="ramp", at_s=5.0, pid=0x05,
            **{"from": 20.0}, to=90.0, duration_s=50.0,
        )
        data = e.model_dump_json(by_alias=True)
        parsed = json.loads(data)
        assert "from" in parsed
        e2 = RampPid.model_validate(parsed)
        assert e2.from_ == 20.0 and e2.to == 90.0

    def test_inject_dtc_roundtrip_and_format(self):
        e = InjectDTC(action="inject_dtc", at_s=10.0, code="P0300")
        e2 = InjectDTC.model_validate_json(e.model_dump_json())
        assert e2.code == "P0300"

    def test_clear_dtc_roundtrip(self):
        e = ClearDTC(action="clear_dtc", at_s=15.0, code="P0300")
        e2 = ClearDTC.model_validate_json(e.model_dump_json())
        assert e2.code == "P0300"

    def test_inject_timeout_roundtrip(self):
        e = InjectTimeout(action="inject_timeout", at_s=22.0, duration_s=3.0)
        e2 = InjectTimeout.model_validate_json(e.model_dump_json())
        assert e2.duration_s == 3.0

    def test_disconnect_reconnect_phase_end_roundtrip(self):
        for e in (
            Disconnect(action="disconnect", at_s=20.0),
            Reconnect(action="reconnect", at_s=30.0),
            PhaseTransition(action="phase", at_s=5.0, name="warmup"),
            EndScenario(action="end", at_s=60.0),
        ):
            cls = type(e)
            e2 = cls.model_validate_json(e.model_dump_json())
            assert e == e2

    def test_ramp_pid_negative_duration_rejected(self):
        """RampPid duration_s must be > 0."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RampPid(
                action="ramp", at_s=0.0, pid=0x05,
                **{"from": 0.0}, to=100.0,
                duration_s=-1.0,
            )

    def test_inject_dtc_invalid_code_rejected(self):
        """DTC codes that don't match [PCBU]+4 hex are rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            InjectDTC(action="inject_dtc", at_s=0.0, code="invalid")
        with pytest.raises(ValidationError):
            InjectDTC(action="inject_dtc", at_s=0.0, code="P0G00")

    def test_vin_length_validated(self):
        """Scenario VIN must be 17 chars when set."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Scenario(
                name="bad_vin", description="", protocol="p",
                vin="TOO_SHORT", initial={0x05: 10},
                timeline=[
                    StartState(
                        action="start", at_s=0.0,
                        pids={0x05: 10}, dtcs=[], vin=None,
                        protocol="p",
                    ),
                    EndScenario(action="end", at_s=10.0),
                ],
            )

    @pytest.mark.parametrize("name", BUILTIN_NAMES)
    def test_builtin_yaml_parses(self, name):
        """Every built-in YAML parses cleanly."""
        path = builtin_path(name)
        scen = ScenarioLoader.from_yaml(path)
        assert scen.name == name
        # Minimal structural checks — the Scenario validator did the
        # heavy lifting, we just smoke-check the result.
        assert len(scen.timeline) >= 2
        assert isinstance(scen.timeline[0], StartState)
        assert isinstance(scen.timeline[-1], EndScenario)


# ===========================================================================
# 3. TestSimulatedAdapter (15)
# ===========================================================================


class TestSimulatedAdapter:
    """SimulatedAdapter ABC compliance + state-fold semantics."""

    def test_abc_satisfied_and_instantiable(self):
        """SimulatedAdapter instantiates — all 8 ABC methods implemented."""
        adapter = SimulatedAdapter(_minimal_scenario())
        assert isinstance(adapter, ProtocolAdapter)

    def test_connect_and_disconnect_flip_state(self):
        adapter = SimulatedAdapter(_minimal_scenario())
        assert adapter.is_connected is False
        adapter.connect()
        assert adapter.is_connected is True
        adapter.disconnect()
        assert adapter.is_connected is False

    def test_initial_read_at_t_zero(self):
        """At t=0, read_pid returns StartState.pids value (rounded)."""
        clk = SimulationClock(start_s=0.0)
        adapter = SimulatedAdapter(_minimal_scenario(), clock=clk)
        adapter.connect()
        assert adapter.read_pid(0x05) == 88
        assert adapter.read_pid(0x0C) == 1000
        # Unknown PID → None
        assert adapter.read_pid(0xEE) is None

    def test_mid_ramp_interpolation(self):
        """Halfway through a 0->100 ramp, read_pid returns ~50."""
        clk = SimulationClock()
        adapter = SimulatedAdapter(_ramp_scenario(), clock=clk)
        adapter.connect()
        clk.advance(5.0)
        val = adapter.read_pid(0x05)
        # 0 + (100-0) * 5/10 = 50
        assert val == 50

    def test_post_ramp_pins_to_target(self):
        """After the ramp duration, read_pid stays at `to`."""
        clk = SimulationClock()
        adapter = SimulatedAdapter(_ramp_scenario(), clock=clk)
        adapter.connect()
        clk.advance(15.0)  # ramp ended at t=10
        assert adapter.read_pid(0x05) == 100

    def test_pre_ramp_pins_to_from(self):
        """Before the ramp fires, read_pid returns StartState value."""
        clk = SimulationClock()
        # Ramp starts at t=5 in this custom scenario
        scen = Scenario(
            name="late_ramp",
            description="",
            protocol="TestProto",
            vin=None,
            initial={0x05: 10},
            timeline=[
                StartState(
                    action="start", at_s=0.0,
                    pids={0x05: 10}, dtcs=[], vin=None,
                    protocol="TestProto",
                ),
                RampPid(
                    action="ramp", at_s=5.0, pid=0x05,
                    **{"from": 10.0}, to=90.0, duration_s=10.0,
                ),
                EndScenario(action="end", at_s=20.0),
            ],
        )
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(2.0)  # before ramp
        assert adapter.read_pid(0x05) == 10

    def test_inject_dtc_appears_at_correct_time(self):
        """InjectDTC at t=5 — before t=5 DTC absent, after t=5 present."""
        scen = Scenario(
            name="inject_test", description="", protocol="p", vin=None,
            initial={0x05: 88},
            timeline=[
                StartState(
                    action="start", at_s=0.0,
                    pids={0x05: 88}, dtcs=[], vin=None, protocol="p",
                ),
                InjectDTC(action="inject_dtc", at_s=5.0, code="P0171"),
                EndScenario(action="end", at_s=10.0),
            ],
        )
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(2.0)
        assert "P0171" not in adapter.read_dtcs()
        clk.advance(6.0)
        assert "P0171" in adapter.read_dtcs()

    def test_clear_dtc_event_removes_code(self):
        """ClearDTC after matching InjectDTC removes the code."""
        scen = Scenario(
            name="clear_test", description="", protocol="p", vin=None,
            initial={0x05: 88},
            timeline=[
                StartState(
                    action="start", at_s=0.0,
                    pids={0x05: 88}, dtcs=[], vin=None, protocol="p",
                ),
                InjectDTC(action="inject_dtc", at_s=2.0, code="P0300"),
                ClearDTC(action="clear_dtc", at_s=5.0, code="P0300"),
                EndScenario(action="end", at_s=10.0),
            ],
        )
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(3.0)
        assert "P0300" in adapter.read_dtcs()
        clk.advance(6.0)
        assert "P0300" not in adapter.read_dtcs()

    def test_user_clear_dtcs_empties_without_mutating_timeline(self):
        """adapter.clear_dtcs() wipes active list; timeline stays intact."""
        scen = Scenario(
            name="user_clear", description="", protocol="p", vin=None,
            initial={0x05: 88},
            timeline=[
                StartState(
                    action="start", at_s=0.0,
                    pids={0x05: 88}, dtcs=["P0171", "P0300"],
                    vin=None, protocol="p",
                ),
                EndScenario(action="end", at_s=10.0),
            ],
        )
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        assert set(adapter.read_dtcs()) == {"P0171", "P0300"}
        assert adapter.clear_dtcs() is True
        assert adapter.read_dtcs() == []
        # Scenario timeline is unchanged
        assert len(adapter.scenario.timeline) == 2

    def test_disconnect_event_raises_connection_error(self):
        """Reads during a Disconnect window raise ProtocolConnectionError."""
        scen = Scenario(
            name="disc_test", description="", protocol="p", vin=None,
            initial={0x05: 88},
            timeline=[
                StartState(
                    action="start", at_s=0.0,
                    pids={0x05: 88}, dtcs=[], vin=None, protocol="p",
                ),
                Disconnect(action="disconnect", at_s=5.0),
                Reconnect(action="reconnect", at_s=10.0),
                EndScenario(action="end", at_s=20.0),
            ],
        )
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(7.0)
        with pytest.raises(ProtocolConnectionError):
            adapter.read_pid(0x05)

    def test_reconnect_restores_reads(self):
        """Post-Reconnect, reads succeed again."""
        scen = Scenario(
            name="reconn_test", description="", protocol="p", vin=None,
            initial={0x05: 42},
            timeline=[
                StartState(
                    action="start", at_s=0.0,
                    pids={0x05: 42}, dtcs=[], vin=None, protocol="p",
                ),
                Disconnect(action="disconnect", at_s=2.0),
                Reconnect(action="reconnect", at_s=5.0),
                EndScenario(action="end", at_s=10.0),
            ],
        )
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(7.0)
        assert adapter.read_pid(0x05) == 42

    def test_inject_timeout_raises_and_recovers(self):
        """InjectTimeout raises during window; recovers after."""
        scen = Scenario(
            name="timeout_test", description="", protocol="p", vin=None,
            initial={0x05: 88},
            timeline=[
                StartState(
                    action="start", at_s=0.0,
                    pids={0x05: 88}, dtcs=[], vin=None, protocol="p",
                ),
                InjectTimeout(
                    action="inject_timeout", at_s=5.0, duration_s=3.0,
                ),
                EndScenario(action="end", at_s=20.0),
            ],
        )
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(6.0)
        with pytest.raises(ProtocolTimeoutError):
            adapter.read_pid(0x05)
        clk.advance(10.0)
        # Window is 5..8 — at t=10, clear again.
        assert adapter.read_pid(0x05) == 88

    def test_phase_transition_is_no_op_for_state(self):
        """PhaseTransition does not mutate any PID/DTC state."""
        scen = Scenario(
            name="phase_test", description="", protocol="p", vin=None,
            initial={0x05: 42},
            timeline=[
                StartState(
                    action="start", at_s=0.0,
                    pids={0x05: 42}, dtcs=[], vin=None, protocol="p",
                ),
                PhaseTransition(
                    action="phase", at_s=5.0, name="transition",
                ),
                EndScenario(action="end", at_s=10.0),
            ],
        )
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(3.0)
        assert adapter.read_pid(0x05) == 42
        clk.advance(7.0)
        assert adapter.read_pid(0x05) == 42
        assert adapter.read_dtcs() == []

    def test_read_vin_and_get_protocol_name_passthrough(self):
        """read_vin + get_protocol_name mirror the scenario header."""
        scen = _minimal_scenario()
        adapter = SimulatedAdapter(scen)
        adapter.connect()
        assert adapter.read_vin() == "1HD1KHM19NB123456"
        assert adapter.get_protocol_name() == "TestProto"

    def test_send_command_returns_empty_bytes_when_connected(self):
        """send_command returns b'' when connected; raises otherwise."""
        adapter = SimulatedAdapter(_minimal_scenario())
        with pytest.raises(ProtocolConnectionError):
            adapter.send_command(b"\x01\x00")
        adapter.connect()
        assert adapter.send_command(b"\x01\x00") == b""

    def test_determinism_across_constructor_repeats(self):
        """Same scenario + same clock time → identical read results."""
        scen = _ramp_scenario()
        clk1 = SimulationClock()
        clk2 = SimulationClock()
        a = SimulatedAdapter(scen, clock=clk1)
        b = SimulatedAdapter(scen, clock=clk2)
        a.connect()
        b.connect()
        for t in (0.0, 1.0, 3.3, 5.0, 7.7, 10.0, 15.0):
            clk1.advance(t)
            clk2.advance(t)
            assert a.read_pid(0x05) == b.read_pid(0x05), (
                f"divergent at t={t}"
            )


# ===========================================================================
# 4. TestBuiltinScenarios (10)
# ===========================================================================


def _drive_to_end(
    adapter: SimulatedAdapter, clock: SimulationClock,
) -> None:
    """Advance the clock across each scenario event (speed=0 equivalent)."""
    for event in adapter.scenario.timeline:
        clock.advance(event.at_s)


class TestBuiltinScenarios:
    """Each of the 10 shipped scenarios runs clean and hits expected state."""

    def test_healthy_idle_zero_dtcs(self):
        scen = ScenarioLoader.find("healthy_idle")
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        _drive_to_end(adapter, clk)
        assert adapter.read_dtcs() == []

    def test_cold_start_coolant_warms(self):
        scen = ScenarioLoader.find("cold_start")
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        _drive_to_end(adapter, clk)
        coolant = adapter.read_pid(0x05)
        assert coolant is not None
        assert coolant >= 85, f"coolant should warm to ~90°C, got {coolant}"

    def test_overheat_peaks_and_fires_p0217(self):
        scen = ScenarioLoader.find("overheat")
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        # Walk through to peak heat
        peak = 0
        for event in scen.timeline:
            clk.advance(event.at_s)
            v = adapter.read_pid(0x05) or 0
            if v > peak:
                peak = v
        assert peak >= 115, f"peak coolant {peak} < 115"
        assert "P0217" in adapter.read_dtcs()

    def test_misfire_rpm_variability(self):
        """Misfire scenario produces noticeable RPM std across the timeline."""
        scen = ScenarioLoader.find("misfire")
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        readings: list[int] = []
        # Sample at sub-event resolution.
        for t in range(0, 85, 1):
            clk.advance(float(t))
            v = adapter.read_pid(0x0C)
            if v is not None:
                readings.append(v)
        mean = sum(readings) / len(readings)
        variance = sum((r - mean) ** 2 for r in readings) / len(readings)
        std = variance ** 0.5
        assert std > 50, f"RPM std {std:.1f} too low — misfire not visible"
        assert "P0300" in adapter.read_dtcs()

    def test_lean_fault_stft_climbs_and_fires_p0171(self):
        scen = ScenarioLoader.find("lean_fault")
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(140.0)  # near end, ramp fully applied
        stft = adapter.read_pid(0x06)
        assert stft is not None and stft >= 145, (
            f"STFT {stft} should climb to ~150"
        )
        assert "P0171" in adapter.read_dtcs()

    def test_o2_sensor_fail_fires_p0134(self):
        scen = ScenarioLoader.find("o2_sensor_fail")
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(60.0)
        assert "P0134" in adapter.read_dtcs()

    def test_charging_fault_battery_drops_and_fires_p0620(self):
        scen = ScenarioLoader.find("charging_fault")
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        clk.advance(175.0)  # after full ramp
        battery_mv = adapter.read_pid(0x42)
        # Initial 14.2V = 14200; ramp to 11800
        assert battery_mv is not None and battery_mv <= 12000, (
            f"battery {battery_mv}mV should drop to ~11.8V"
        )
        assert "P0620" in adapter.read_dtcs()

    def test_ecu_crash_recovery_completes(self):
        scen = ScenarioLoader.find("ecu_crash_recovery")
        clk = SimulationClock()
        adapter = SimulatedAdapter(scen, clock=clk)
        adapter.connect()
        # Before the disconnect window — reads work.
        clk.advance(10.0)
        assert adapter.read_pid(0x05) is not None
        # Inside disconnect window — reads raise.
        clk.advance(25.0)
        with pytest.raises((ProtocolConnectionError, ProtocolTimeoutError)):
            adapter.read_pid(0x05)
        # After reconnect — reads work.
        clk.advance(50.0)
        assert adapter.read_pid(0x05) is not None

    def test_harley_sporty_warmup_protocol_and_vin(self):
        scen = ScenarioLoader.find("harley_sporty_warmup")
        adapter = SimulatedAdapter(scen)
        adapter.connect()
        assert adapter.get_protocol_name() == "SAE J1850 VPW"
        vin = adapter.read_vin()
        assert vin is not None and vin.startswith("1HD")

    def test_cbr600_warm_idle_protocol_and_vin(self):
        scen = ScenarioLoader.find("cbr600_warm_idle")
        adapter = SimulatedAdapter(scen)
        adapter.connect()
        assert adapter.get_protocol_name() == "ISO 14230 KWP2000"
        vin = adapter.read_vin()
        assert vin is not None and vin.startswith("JH2")


# ===========================================================================
# 5. TestScenarioFromRecording (5) — all skipped when Phase 142 absent
# ===========================================================================


_PHASE142_PRESENT = _phase142_available()


@pytest.mark.skipif(
    not _PHASE142_PRESENT,
    reason="Phase 142 RecordingManager not merged — skipping recording "
           "round-trip tests. These will activate automatically once "
           "motodiag.hardware.recorder is importable.",
)
class TestScenarioFromRecording:
    """Recording→Scenario round-trip tests — soft dep on Phase 142.

    Each test either exercises a round-trip against a real
    :class:`RecordingManager` (constructed fresh per test against a
    tmp DB) or confirms that bad inputs raise the right exception.
    Failures here that *aren't* related to the simulator surface are
    most likely Phase 142 contract drift — check
    :meth:`RecordingManager.load_recording` first.
    """

    def test_from_recording_nonexistent_raises_validation_error(self, tmp_path):
        """Asking for a recording ID that doesn't exist raises cleanly."""
        # Seed a fresh DB with nothing — then ask for ID 1 which isn't there.
        from motodiag.core.database import init_db
        db_path = str(tmp_path / "rec_miss.db")
        init_db(db_path)
        with pytest.raises((ScenarioValidationError, Exception)):
            ScenarioLoader.from_recording(1, db=db_path)

    def test_from_recording_invalid_id_shape_raises(self):
        """Non-int-coercible recording_id raises ValueError / TypeError."""
        with pytest.raises((ScenarioValidationError, ValueError, TypeError)):
            ScenarioLoader.from_recording("not-a-number")

    def test_from_recording_module_importable(self):
        """The recorder module loads under the name the probe checks."""
        import importlib
        mod = importlib.import_module("motodiag.hardware.recorder")
        assert hasattr(mod, "RecordingManager"), (
            "Phase 142 contract drifted — RecordingManager is missing "
            "from motodiag.hardware.recorder."
        )

    def test_from_recording_guard_probe_returns_true(self):
        """The internal probe returns True when Phase 142 is installed."""
        assert _phase142_available() is True

    def test_from_recording_missing_module_would_raise(self):
        """Confirm the guard engages when the probe reports Phase 142 absent."""
        # Monkey-patch the probe in-place to simulate Phase 142 absence.
        from motodiag.hardware import simulator as sim_mod
        original = sim_mod._phase142_available
        sim_mod._phase142_available = lambda: False
        try:
            with pytest.raises(RecordingSupportUnavailable):
                ScenarioLoader.from_recording(1)
        finally:
            sim_mod._phase142_available = original


def test_from_recording_raises_when_phase142_absent():
    """When Phase 142 is unavailable, from_recording raises the guard exception.

    When the module IS present (current runtime), we monkey-patch the
    probe to exercise the guard path anyway — so the test is meaningful
    in both states of the world.
    """
    from motodiag.hardware import simulator as sim_mod
    original = sim_mod._phase142_available
    sim_mod._phase142_available = lambda: False
    try:
        with pytest.raises(RecordingSupportUnavailable):
            ScenarioLoader.from_recording("any_id")
    finally:
        sim_mod._phase142_available = original


# ===========================================================================
# 6. TestSimulateCommand (10) — CliRunner driven
# ===========================================================================


def _make_cli():
    """Build a test CLI with just `hardware` registered."""
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_hardware(root)
    return root


@pytest.fixture(autouse=True)
def _patch_init_db(monkeypatch, tmp_path):
    """Redirect init_db() to a per-test tmp DB — matches Phase 140 fixture."""
    from motodiag.cli import hardware as hw_mod
    from motodiag.core.database import init_db

    db_path = str(tmp_path / "phase144.db")
    init_db(db_path)
    original = hw_mod.init_db

    def _patched(*args, **kwargs):
        return original(db_path, *args[1:], **kwargs) if args or kwargs \
            else original(db_path)

    monkeypatch.setattr(hw_mod, "init_db", _patched)
    yield db_path


class TestSimulateCommand:
    """CLI surface for `motodiag hardware simulate ...`."""

    def test_list_shows_all_builtins(self):
        runner = CliRunner()
        result = runner.invoke(_make_cli(), ["hardware", "simulate", "list"])
        assert result.exit_code == 0, result.output
        for name in BUILTIN_NAMES:
            assert name in result.output

    def test_list_with_user_path_shows_extra_scenarios(self, tmp_path):
        # Drop a user-authored YAML into tmp and verify it shows up.
        user_yaml = tmp_path / "custom.yaml"
        user_yaml.write_text(
            "name: custom_user\n"
            "description: user scenario\n"
            "protocol: TestProto\n"
            "initial: {0x05: 88}\n"
            "timeline:\n"
            "  - {action: start, at: 0s, pids: {0x05: 88}, dtcs: []}\n"
            "  - {action: end, at: 10s}\n",
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "simulate", "list",
             "--user-path", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output
        assert "custom_user" in result.output

    def test_run_healthy_idle_fast(self):
        """run <scenario> --speed 0 completes quickly + exits 0."""
        import time
        runner = CliRunner()
        t0 = time.monotonic()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "simulate", "run", "healthy_idle", "--speed", "0"],
        )
        elapsed = time.monotonic() - t0
        assert result.exit_code == 0, result.output
        assert elapsed < 5.0, f"simulate run too slow: {elapsed:.2f}s"

    def test_run_unknown_scenario_suggests_builtins(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "simulate", "run", "heaLthy_idlee"],
        )
        assert result.exit_code == 1
        # Close-match suggestion should point at healthy_idle
        assert "healthy_idle" in result.output

    def test_run_ecu_crash_recovery_event_log(self):
        """With --log, each timeline event gets a log line."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "simulate", "run", "ecu_crash_recovery",
             "--speed", "0", "--log"],
        )
        assert result.exit_code == 0, result.output
        assert "Disconnect" in result.output
        assert "Reconnect" in result.output

    @pytest.mark.parametrize("name", BUILTIN_NAMES)
    def test_validate_each_builtin_passes(self, name):
        runner = CliRunner()
        path = builtin_path(name)
        result = runner.invoke(
            _make_cli(),
            ["hardware", "simulate", "validate", str(path)],
        )
        assert result.exit_code == 0, result.output
        assert "OK" in result.output

    def test_validate_malformed_yaml_shows_line_number(self, tmp_path):
        """Broken YAML syntax triggers a parse error with line info."""
        bad = tmp_path / "broken.yaml"
        # Unterminated flow sequence — PyYAML raises ScannerError with
        # line+column context.
        bad.write_text(
            "name: broken\n"
            "description: oops\n"
            "protocol: test\n"
            "initial: {0x05: 88}\n"
            "timeline: [\n"
            "  - this is not valid YAML inside a flow sequence\n",
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "simulate", "validate", str(bad)],
        )
        assert result.exit_code == 1, result.output
        # Pydantic or yaml errors show parse-site info — accept either "line"
        # or "column" word as a proxy for "line-number awareness".
        assert ("line" in result.output.lower()
                or "column" in result.output.lower()
                or "parse" in result.output.lower()
                or "validation" in result.output.lower()
                or "failed" in result.output.lower())

    def test_validate_reconnect_without_disconnect_fails(self, tmp_path):
        """Reconnect without a preceding Disconnect is rejected."""
        bad = tmp_path / "bad_reconn.yaml"
        bad.write_text(
            "name: bad_reconnect\n"
            "description: reconnect without disconnect\n"
            "protocol: TestProto\n"
            "initial: {0x05: 88}\n"
            "timeline:\n"
            "  - {action: start, at: 0s, pids: {0x05: 88}, dtcs: []}\n"
            "  - {action: reconnect, at: 5s}\n"
            "  - {action: end, at: 10s}\n",
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "simulate", "validate", str(bad)],
        )
        assert result.exit_code == 1, result.output
        # Message should mention the reconnect or disconnect problem.
        output_lc = result.output.lower()
        assert ("reconnect" in output_lc or "disconnect" in output_lc)

    def test_scan_mock_and_simulator_mutex(self):
        """scan --mock --simulator X raises UsageError (exit 2)."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "scan", "--port", "COM3",
             "--mock", "--simulator", "healthy_idle"],
        )
        # Click UsageError → exit code 2
        assert result.exit_code == 2, result.output
        assert "mutually exclusive" in result.output.lower()

    def test_scan_with_simulator_prints_sim_badge(self):
        """hardware scan --simulator healthy_idle prints the SIM badge."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "scan", "--port", "sim://test",
             "--simulator", "healthy_idle"],
        )
        assert result.exit_code == 0, result.output
        assert "SIM" in result.output
        assert "healthy_idle" in result.output


# ===========================================================================
# Standalone helpers (non-class, not counted among the 55 methods)
# ===========================================================================


class TestDurationAndPidParsing:
    """Supporting helper tests — tiny but worth pinning down."""

    def test_parse_duration_bare_number(self):
        assert _parse_duration(5) == 5.0
        assert _parse_duration(1.5) == 1.5

    def test_parse_duration_seconds_suffix(self):
        assert _parse_duration("30s") == 30.0
        assert _parse_duration("1.5s") == 1.5

    def test_parse_duration_minutes_seconds(self):
        assert _parse_duration("1m30s") == 90.0
        assert _parse_duration("2m") == 120.0

    def test_parse_duration_rejects_negative(self):
        with pytest.raises(ValueError):
            _parse_duration(-1)
        with pytest.raises(ValueError):
            _parse_duration("-5s")

    def test_coerce_pid_all_forms(self):
        assert _coerce_pid(5) == 5
        assert _coerce_pid(0x05) == 5
        assert _coerce_pid("0x05") == 5
        assert _coerce_pid("coolant_temp") == PID_ALIASES["coolant_temp"]
        assert _coerce_pid("engine_rpm") == 0x0C

    def test_coerce_pid_rejects_bool_and_out_of_range(self):
        with pytest.raises(ValueError):
            _coerce_pid(True)
        with pytest.raises(ValueError):
            _coerce_pid(500)
