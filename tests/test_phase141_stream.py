"""Phase 141 — Live Sensor Streaming tests.

Five test classes, ~40+ tests, zero real serial I/O, zero live tokens.
Every streamer interaction goes through :class:`MockAdapter` with the
new ``pid_values`` kwarg — a real concrete
:class:`~motodiag.hardware.protocols.base.ProtocolAdapter` so any ABC
drift surfaces as an instantiation failure (same discipline as Phase
140's tests).

Test classes
------------

- :class:`TestSensorCatalog` — SAE J1979 canonical decode vectors
  (RPM / coolant / IAT / throttle / battery / O2 voltage / VSS /
  runtime) plus unknown-PID rejection.
- :class:`TestSensorReading` — Pydantic v2 model: ISO UTC timestamp,
  lowercase ``pid_hex`` rejection, ``value`` / ``status`` coherence.
- :class:`TestSensorStreamer` — happy path, unsupported PIDs, timeout
  recovery, ConnectionError propagation, hz throttle via mock
  :func:`sleep`, custom clock, one-shot guard, non-catalog PIDs.
- :class:`TestStreamCommand` — CliRunner-driven: ``--mock --duration``,
  custom ``--pids``, validation errors, clamping, CSV output, appending,
  unsupported rendering, ECU silence, Ctrl+C cleanup, ``--help``.
- :class:`TestMockAdapterExtension` — Phase 141 ``pid_values`` kwarg:
  happy path, unknown key, legacy override, None preserves Phase 140,
  defensive copy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from motodiag.cli.hardware import register_hardware
from motodiag.core.database import init_db
from motodiag.hardware.connection import HardwareSession
from motodiag.hardware.mock import MockAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
    TimeoutError as ProtocolTimeoutError,
)
from motodiag.hardware.sensors import (
    SENSOR_CATALOG,
    SensorReading,
    SensorStreamer,
    decode_pid,
    parse_pid_list,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


_FIXED_UTC = datetime(2026, 4, 18, 12, 0, 0, tzinfo=timezone.utc)


def _fixed_clock() -> datetime:
    """Clock factory that always returns the same UTC instant."""
    return _FIXED_UTC


def _make_cli():
    """Build a minimal Click group with only ``hardware`` attached."""

    @click.group()
    def root() -> None:
        """test root"""

    register_hardware(root)
    return root


@pytest.fixture(autouse=True)
def _patch_init_db(monkeypatch, tmp_path):
    """Redirect init_db() to a per-test tmp DB (mirrors Phase 140)."""
    db_path = str(tmp_path / "phase141.db")
    init_db(db_path)

    from motodiag.cli import hardware as hw_mod

    original_init_db = hw_mod.init_db

    def _patched(*args, **kwargs):
        return original_init_db(db_path, *args[1:], **kwargs) \
            if args or kwargs else original_init_db(db_path)

    monkeypatch.setattr(hw_mod, "init_db", _patched)
    yield db_path


# ===========================================================================
# 1. SENSOR_CATALOG — SAE J1979 canonical vectors
# ===========================================================================


class TestSensorCatalog:
    """SAE J1979 decoders must return canonical values."""

    def test_rpm_canonical_vector(self):
        """``0x1AF8`` (=6904) divided by 4 = 1726 rpm."""
        # Pre-assembled int per the Phase 134 ABC — adapter handles
        # (A << 8) | B; decoder is a pure int->float.
        assert decode_pid(0x0C, 0x1AF8) == pytest.approx(1726.0)

    def test_coolant_temp_canonical_vector(self):
        """Coolant 0x5A (90) - 40 = 50 °C."""
        assert decode_pid(0x05, 0x5A) == pytest.approx(50.0)

    def test_iat_canonical_vector(self):
        """Intake air temp 0x0F raw 0x41 (65) - 40 = 25 °C."""
        # PID 0x0F uses the same offset-40 decoder as coolant.
        assert decode_pid(0x0F, 0x41) == pytest.approx(25.0)

    def test_throttle_canonical_vector(self):
        """Throttle 0xFF (255) * 100 / 255 = 100%."""
        assert decode_pid(0x11, 0xFF) == pytest.approx(100.0)

    def test_battery_voltage_canonical_vector(self):
        """Control-module voltage 0x3600 (13824) / 1000 = 13.824 V."""
        assert decode_pid(0x42, 0x3600) == pytest.approx(13.824)

    def test_o2_voltage_canonical_vector(self):
        """O2 sensor voltage: 0x5AB0 upper byte 0x5A (90) / 200 = 0.45 V.

        Lower byte 0xB0 is short-term fuel trim — Phase 141 ignores it.
        """
        assert decode_pid(0x14, 0x5AB0) == pytest.approx(0.45)

    def test_vss_and_runtime_canonical_vectors(self):
        """Vehicle speed 0x64 (100) → 100 km/h; runtime 0x0A28 → 2600 s."""
        assert decode_pid(0x0D, 0x64) == pytest.approx(100.0)
        assert decode_pid(0x1F, 0x0A28) == pytest.approx(2600.0)

    def test_unknown_pid_raises_value_error(self):
        """decode_pid on a PID outside the catalog raises ValueError."""
        with pytest.raises(ValueError, match="Unknown PID"):
            decode_pid(0xFE, 0)

    def test_catalog_covers_expected_pids(self):
        """Spec mandates at least these PIDs — sanity check."""
        required = {
            0x04, 0x05, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11,
            0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B,
            0x1F, 0x2F, 0x42, 0x46, 0x5C,
        }
        missing = required - set(SENSOR_CATALOG.keys())
        assert not missing, f"Missing PIDs in catalog: {missing}"


# ===========================================================================
# 2. SensorReading — Pydantic v2 model
# ===========================================================================


class TestSensorReading:
    """SensorReading enforces uppercase hex + value/status coherence."""

    def test_happy_path_round_trip(self):
        """A valid ok-status reading survives model_dump + revalidation."""
        r = SensorReading(
            pid=0x0C,
            pid_hex="0x0C",
            name="Engine RPM",
            value=1726.0,
            unit="rpm",
            raw=0x1AF8,
            captured_at=_FIXED_UTC,
            status="ok",
        )
        dumped = r.model_dump()
        r2 = SensorReading(**dumped)
        assert r2.pid == 0x0C
        assert r2.value == pytest.approx(1726.0)

    def test_captured_at_isoformat_is_utc(self):
        """ISO timestamp string includes ``T`` separator + UTC offset."""
        r = SensorReading(
            pid=0x05,
            pid_hex="0x05",
            name="Engine coolant temperature",
            value=50.0,
            unit="°C",
            raw=0x5A,
            captured_at=_FIXED_UTC,
            status="ok",
        )
        iso = r.captured_at.isoformat()
        assert "T" in iso
        assert "+00:00" in iso

    def test_lowercase_pid_hex_rejected(self):
        """pid_hex regex requires uppercase hex digits."""
        with pytest.raises(ValidationError):
            SensorReading(
                pid=0x0C,
                pid_hex="0x0c",  # lowercase — must be rejected
                name="Engine RPM",
                value=1726.0,
                unit="rpm",
                raw=0x1AF8,
                captured_at=_FIXED_UTC,
                status="ok",
            )

    def test_unsupported_with_nonnull_value_rejected(self):
        """Unsupported/timeout status must have value=None."""
        with pytest.raises(ValidationError):
            SensorReading(
                pid=0x0C,
                pid_hex="0x0C",
                name="Engine RPM",
                value=2.0,  # BOGUS — unsupported requires None
                unit="rpm",
                raw=None,
                captured_at=_FIXED_UTC,
                status="unsupported",
            )


# ===========================================================================
# 3. SensorStreamer — one-shot polling generator
# ===========================================================================


class TestSensorStreamer:
    """SensorStreamer drives the adapter + translates errors per spec."""

    def test_happy_path_yields_decoded_readings(self):
        """Scripted pid_values produce ok readings with decoded values."""
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8, 0x05: 0x5A})
        adapter.connect("COM3", 38400)
        sleep_mock = MagicMock()
        streamer = SensorStreamer(
            adapter, [0x0C, 0x05], hz=2.0,
            sleep=sleep_mock, clock=_fixed_clock,
        )
        gen = streamer.iter_readings()
        tick = next(gen)
        assert len(tick) == 2
        rpm, coolant = tick
        assert rpm.pid == 0x0C
        assert rpm.status == "ok"
        assert rpm.value == pytest.approx(1726.0)
        assert coolant.pid == 0x05
        assert coolant.status == "ok"
        assert coolant.value == pytest.approx(50.0)

    def test_unsupported_pid_returns_none_reading(self):
        """pid_values miss → adapter returns None → status=unsupported."""
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8})
        adapter.connect("COM3", 38400)
        streamer = SensorStreamer(
            adapter, [0x0C, 0x05], hz=5.0,
            sleep=MagicMock(), clock=_fixed_clock,
        )
        tick = next(streamer.iter_readings())
        assert tick[0].status == "ok"
        assert tick[1].status == "unsupported"
        assert tick[1].value is None
        assert tick[1].raw is None

    def test_timeout_error_caught_and_retries_next_tick(self):
        """TimeoutError → status=timeout, next call recovers."""
        adapter = MagicMock()
        # Sequence: first read_pid raises, second returns a value
        adapter.read_pid.side_effect = [
            ProtocolTimeoutError("ecu timeout"),
            0x1AF8,
        ]
        streamer = SensorStreamer(
            adapter, [0x0C], hz=5.0,
            sleep=MagicMock(), clock=_fixed_clock,
        )
        gen = streamer.iter_readings()
        tick1 = next(gen)
        assert tick1[0].status == "timeout"
        assert tick1[0].value is None
        tick2 = next(gen)
        assert tick2[0].status == "ok"
        assert tick2[0].value == pytest.approx(1726.0)

    def test_connection_error_propagates(self):
        """ConnectionError is re-raised immediately — loop stops."""
        adapter = MagicMock()
        adapter.read_pid.side_effect = ProtocolConnectionError("serial broke")
        streamer = SensorStreamer(
            adapter, [0x0C], hz=5.0,
            sleep=MagicMock(), clock=_fixed_clock,
        )
        gen = streamer.iter_readings()
        with pytest.raises(ProtocolConnectionError, match="serial broke"):
            next(gen)

    def test_hz_throttle_calls_sleep_with_reciprocal(self):
        """Streamer calls sleep(1/hz) exactly once per tick."""
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8})
        adapter.connect("COM3", 38400)
        sleep_mock = MagicMock()
        streamer = SensorStreamer(
            adapter, [0x0C], hz=4.0,
            sleep=sleep_mock, clock=_fixed_clock,
        )
        gen = streamer.iter_readings()
        next(gen)  # tick 1 yielded; sleep(0.25) fires after yield
        next(gen)  # tick 2 yielded; second sleep(0.25) fires
        next(gen)  # tick 3 yielded; triggers return of tick 2's post-yield sleep
        assert sleep_mock.call_count == 2
        for call in sleep_mock.call_args_list:
            args, _ = call
            assert args[0] == pytest.approx(0.25)

    def test_custom_clock_used_for_captured_at(self):
        """Injected clock pins timestamps deterministically."""
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8})
        adapter.connect("COM3", 38400)

        def clock_fn() -> datetime:
            return _FIXED_UTC

        streamer = SensorStreamer(
            adapter, [0x0C], hz=5.0,
            sleep=MagicMock(), clock=clock_fn,
        )
        tick = next(streamer.iter_readings())
        assert tick[0].captured_at == _FIXED_UTC

    def test_iter_readings_is_one_shot(self):
        """Second call to iter_readings raises RuntimeError."""
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8})
        adapter.connect("COM3", 38400)
        streamer = SensorStreamer(
            adapter, [0x0C], hz=5.0,
            sleep=MagicMock(), clock=_fixed_clock,
        )
        next(streamer.iter_readings())
        with pytest.raises(RuntimeError, match="one-shot"):
            next(streamer.iter_readings())

    def test_non_catalog_pid_yields_unsupported_with_synthetic_name(self):
        """An out-of-catalog PID gets status=unsupported + 'PID 0x..' name."""
        adapter = MockAdapter(pid_values={0xFD: 12345})
        adapter.connect("COM3", 38400)
        streamer = SensorStreamer(
            adapter, [0xFD], hz=5.0,
            sleep=MagicMock(), clock=_fixed_clock,
        )
        tick = next(streamer.iter_readings())
        assert tick[0].status == "unsupported"
        assert tick[0].name == "PID 0xFD"
        assert tick[0].unit == ""


# ===========================================================================
# 4. parse_pid_list — CLI input validation
# ===========================================================================


class TestParsePidList:
    """parse_pid_list accepts hex/dec, rejects bad tokens."""

    def test_mixed_hex_and_decimal(self):
        """Accepts 0xNN and decimal, preserving order + dedup."""
        result = parse_pid_list("0x0C, 0x05, 17, 0x42")
        # 17 decimal = 0x11 = throttle
        assert result == [0x0C, 0x05, 0x11, 0x42]

    def test_dedupe_preserves_first_seen_order(self):
        """0x0C,0x05,0x0C → [0x0C, 0x05]."""
        result = parse_pid_list("0x0C,0x05,0x0C")
        assert result == [0x0C, 0x05]

    def test_empty_spec_rejected(self):
        """Empty or whitespace-only input raises ClickException."""
        with pytest.raises(click.ClickException):
            parse_pid_list("")
        with pytest.raises(click.ClickException):
            parse_pid_list("   ")

    def test_garbage_token_rejected(self):
        """Non-parsable token raises with token name in message."""
        with pytest.raises(click.ClickException, match="potato"):
            parse_pid_list("0x0C,potato")

    def test_out_of_range_rejected(self):
        """Values >255 raise regardless of base."""
        with pytest.raises(click.ClickException, match="out of range"):
            parse_pid_list("0x100")
        with pytest.raises(click.ClickException, match="out of range"):
            parse_pid_list("300")


# ===========================================================================
# 5. motodiag hardware stream — CLI
# ===========================================================================


class TestStreamCommand:
    """CliRunner-driven tests for the stream subcommand."""

    def test_mock_happy_path_default_pids_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3",
                "--mock", "--duration", "0.5", "--hz", "2",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "MOCK" in result.output
        # Six default PID rows — RPM, coolant, IAT, throttle, battery,
        # O2. Each appears at least as a PID hex label.
        for expected in ("0x0C", "0x05", "0x0F", "0x11", "0x42", "0x14"):
            assert expected in result.output, (
                f"Expected {expected} in output: {result.output}"
            )
        assert "Polled" in result.output

    def test_mock_custom_pids_renders_only_those_rows(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3",
                "--mock", "--duration", "0.5", "--hz", "2",
                "--pids", "0x0C,0x42",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "0x0C" in result.output
        assert "0x42" in result.output
        # 0x05 coolant should NOT appear — we didn't request it
        assert "0x05" not in result.output

    def test_empty_pids_rejected(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--pids", "",
            ],
        )
        assert result.exit_code != 0
        assert "pids" in result.output.lower()

    def test_out_of_range_pid_rejected(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--pids", "0x100",
            ],
        )
        assert result.exit_code != 0
        assert "out of range" in result.output.lower()

    def test_garbage_pid_token_rejected(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--pids", "potato",
            ],
        )
        assert result.exit_code != 0
        assert "potato" in result.output

    def test_hz_zero_rejected(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--hz", "0",
            ],
        )
        assert result.exit_code != 0
        assert "hz" in result.output.lower()

    def test_hz_over_ceiling_clamped_with_warning(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--hz", "20", "--duration", "0.3",
            ],
        )
        assert result.exit_code == 0, result.output
        # Yellow warning panel printed before the stream started
        assert "clamped" in result.output.lower()

    def test_output_csv_writes_header_and_rows(self, tmp_path):
        out = tmp_path / "stream.csv"
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--pids", "0x0C,0x42",
                "--duration", "0.5", "--hz", "4",
                "--output", str(out),
            ],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()
        content = out.read_text(encoding="utf-8").splitlines()
        # Header + at least one data row
        assert len(content) >= 2
        header = content[0]
        assert "timestamp_utc_iso" in header
        assert "elapsed_s" in header
        # Column labels use "Name (unit)" for catalog entries
        assert "Engine RPM (rpm)" in header
        assert "Control module voltage (V)" in header

    def test_output_csv_rerun_appends_without_duplicate_header(self, tmp_path):
        out = tmp_path / "stream.csv"
        runner = CliRunner()
        # First run
        result1 = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--pids", "0x0C",
                "--duration", "0.3", "--hz", "4",
                "--output", str(out),
            ],
        )
        assert result1.exit_code == 0, result1.output
        # Second run — same path
        result2 = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--pids", "0x0C",
                "--duration", "0.3", "--hz", "4",
                "--output", str(out),
            ],
        )
        assert result2.exit_code == 0, result2.output
        lines = out.read_text(encoding="utf-8").splitlines()
        # Only one header line ("timestamp_utc_iso")
        header_lines = [ln for ln in lines if ln.startswith("timestamp_utc_iso")]
        assert len(header_lines) == 1

    def test_unsupported_pid_rendered_as_em_dash(self):
        """A PID not in pid_values renders as em-dash cell."""
        # Override HardwareSession to yield a MockAdapter with only one
        # pid_values key — the other default PID reads return None.
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8})
        real_session = HardwareSession(
            port="COM3", adapter_override=adapter,
        )
        with patch(
            "motodiag.cli.hardware.HardwareSession",
            return_value=real_session,
        ):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                [
                    "hardware", "stream", "--port", "COM3", "--mock",
                    "--pids", "0x0C,0x05",
                    "--duration", "0.5", "--hz", "4",
                ],
            )
        assert result.exit_code == 0, result.output
        # Em-dash (U+2014) appears for the unsupported coolant reading
        assert "—" in result.output

    def test_ecu_silence_renders_red_panel_and_exits_one(self):
        """ProtocolError mid-stream surfaces as red panel + exit 1."""
        broken_adapter = MagicMock()
        broken_adapter.is_connected = True
        broken_adapter.get_protocol_name.return_value = "Mock Protocol"
        broken_adapter.read_pid.side_effect = ProtocolConnectionError(
            "ecu silent"
        )

        class _SilentSession:
            def __init__(self, *a, **kw):
                pass

            def __enter__(self):
                return broken_adapter

            def __exit__(self, *a):
                return False

        with patch("motodiag.cli.hardware.HardwareSession", _SilentSession):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                [
                    "hardware", "stream", "--port", "COM3", "--mock",
                    "--pids", "0x0C",
                    "--duration", "1", "--hz", "4",
                ],
            )
        assert result.exit_code == 1
        assert "ECU went silent" in result.output

    def test_keyboard_interrupt_exits_zero_and_calls_disconnect(self):
        """Ctrl+C mid-stream → exit 0 + HardwareSession.__exit__ runs."""
        real_adapter = MockAdapter(pid_values={0x0C: 0x1AF8})
        disconnect_spy = MagicMock(wraps=real_adapter.disconnect)
        real_adapter.disconnect = disconnect_spy  # type: ignore[assignment]

        # Build a streamer whose first next() raises KeyboardInterrupt.
        class _KbiStreamer:
            def __init__(self, *a, **kw):
                pass

            def iter_readings(self):
                raise KeyboardInterrupt()

        with patch(
            "motodiag.cli.hardware.SensorStreamer", _KbiStreamer,
        ):
            real_session = HardwareSession(
                port="COM3", adapter_override=real_adapter,
            )
            with patch(
                "motodiag.cli.hardware.HardwareSession",
                return_value=real_session,
            ):
                runner = CliRunner()
                result = runner.invoke(
                    _make_cli(),
                    [
                        "hardware", "stream", "--port", "COM3", "--mock",
                        "--pids", "0x0C",
                        "--duration", "0", "--hz", "4",
                    ],
                )
        assert result.exit_code == 0, result.output
        disconnect_spy.assert_called()

    def test_help_mentions_all_flags(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["hardware", "stream", "--help"],
        )
        assert result.exit_code == 0
        for flag in (
            "--port", "--bike", "--make", "--baud", "--timeout",
            "--mock", "--pids", "--hz", "--duration", "--output",
        ):
            assert flag in result.output, f"--help missing {flag}"

    def test_bike_and_make_mutually_exclusive(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "stream", "--port", "COM3", "--mock",
                "--bike", "x", "--make", "harley",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output


# ===========================================================================
# 6. MockAdapter pid_values extension
# ===========================================================================


class TestMockAdapterExtension:
    """Phase 141 ``pid_values`` kwarg — additive to Phase 140."""

    def test_pid_values_returns_mapped_value(self):
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8, 0x05: 0x5A})
        adapter.connect("COM3", 38400)
        assert adapter.read_pid(0x0C) == 0x1AF8
        assert adapter.read_pid(0x05) == 0x5A

    def test_pid_values_missing_key_returns_none(self):
        adapter = MockAdapter(pid_values={0x0C: 0x1AF8})
        adapter.connect("COM3", 38400)
        assert adapter.read_pid(0x42) is None

    def test_pid_values_overrides_legacy_supported_modes(self):
        """When pid_values is set, supported_modes is ignored."""
        adapter = MockAdapter(
            pid_values={0x0C: 0x1AF8},
            supported_modes=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        )
        adapter.connect("COM3", 38400)
        # Legacy path would have returned 10*10=100 for pid=10, but
        # pid_values is authoritative now.
        assert adapter.read_pid(10) is None
        assert adapter.read_pid(0x0C) == 0x1AF8

    def test_pid_values_none_preserves_phase_140_behavior(self):
        """Default MockAdapter still returns pid*10 or None."""
        adapter = MockAdapter(supported_modes=[1, 3, 4, 9])
        adapter.connect("COM3", 38400)
        assert adapter.read_pid(1) == 10
        assert adapter.read_pid(4) == 40
        assert adapter.read_pid(2) is None
        assert adapter.read_pid(255) is None

    def test_pid_values_defensive_copy_on_construction(self):
        """Mutating the caller's dict after construction must not leak."""
        src: dict[int, int] = {0x0C: 0x1AF8}
        adapter = MockAdapter(pid_values=src)
        src[0x42] = 0x3600  # caller mutates their own dict
        adapter.connect("COM3", 38400)
        assert adapter.read_pid(0x42) is None, (
            "Mutating the source dict leaked into MockAdapter — defensive "
            "copy missing"
        )
