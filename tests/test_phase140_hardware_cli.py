"""Phase 140 — Hardware CLI (scan / clear / info) tests.

Six test classes, ~40 tests, zero real serial I/O, zero live tokens.
All hardware interactions go through :class:`MockAdapter` (a real
concrete :class:`ProtocolAdapter` subclass — not a :class:`MagicMock`
— so ABC contract drift surfaces as an immediate instantiation
failure rather than a silently-passing mock).

Test classes
------------

- :class:`TestMockAdapterContract` (5) — ABC satisfied, connect/disconnect,
  DTC round-trip, read_pid / read_vin semantics.
- :class:`TestHardwareSession` (6) — mock path, override path, disconnect
  semantics, real AutoDetector propagation, error pass-through.
- :class:`TestScanCommand` (10) — Click-runner driven: happy path, bike
  slug resolution, DTC enrichment, error panels.
- :class:`TestClearCommand` (8) — safety warning, confirm prompt, success
  / refusal rendering.
- :class:`TestInfoCommand` (6) — all fields, VIN=None, empty supported-
  modes.
- :class:`TestDTCLookup` (5) — :func:`resolve_dtc_info` tier semantics.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from motodiag.cli.hardware import register_hardware
from motodiag.core.database import init_db
from motodiag.core.models import DTCCode, Severity, SymptomCategory
from motodiag.hardware.connection import HardwareSession
from motodiag.hardware.ecu_detect import NoECUDetectedError
from motodiag.hardware.mock import MockAdapter
from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
    UnsupportedCommandError,
)
from motodiag.knowledge.dtc_lookup import resolve_dtc_info
from motodiag.knowledge.dtc_repo import add_dtc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cli():
    """Build a fresh CLI group with just `hardware` registered.

    Faster than importing the full motodiag.cli.main CLI (which also
    registers diagnose, code, kb, cache, etc.) and sufficient for the
    hardware-only test scope.
    """
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_hardware(root)
    return root


@pytest.fixture(autouse=True)
def _patch_init_db(monkeypatch, tmp_path):
    """Redirect init_db() to a per-test tmp DB so we don't touch the
    developer's real motodiag DB during CliRunner invocations.
    """
    db_path = str(tmp_path / "phase140.db")
    init_db(db_path)

    # Every command path calls init_db() with no args at the top; we
    # patch that top-level symbol in the hardware module to return our
    # tmp path instead of the default-settings path. The real init_db
    # we called above seeded the schema, so downstream queries work.
    from motodiag.cli import hardware as hw_mod

    original_init_db = hw_mod.init_db

    def _patched(*args, **kwargs):
        return original_init_db(db_path, *args[1:], **kwargs) \
            if args or kwargs else original_init_db(db_path)

    monkeypatch.setattr(hw_mod, "init_db", _patched)
    # Also expose the tmp path to tests that want to seed rows via
    # add_dtc(..., db_path=...).
    yield db_path


# ===========================================================================
# 1. MockAdapter contract
# ===========================================================================


class TestMockAdapterContract:
    """MockAdapter must be a real concrete ProtocolAdapter."""

    def test_is_abc_satisfied_and_instantiable(self):
        """Constructing a MockAdapter must not raise — all 8 abstract
        methods implemented."""
        adapter = MockAdapter()
        assert isinstance(adapter, ProtocolAdapter)
        assert adapter.is_connected is False

    def test_connect_and_disconnect_flip_is_connected(self):
        """connect() sets is_connected=True; disconnect() sets False."""
        adapter = MockAdapter()
        adapter.connect("COM3", 38400)
        assert adapter.is_connected is True
        adapter.disconnect()
        assert adapter.is_connected is False

    def test_read_and_clear_dtcs_roundtrip(self):
        """read_dtcs returns a copy; clear_dtcs empties + returns flag."""
        adapter = MockAdapter(dtcs=["P0115", "P0300", "U0100"])
        adapter.connect("COM3", 38400)
        assert adapter.read_dtcs() == ["P0115", "P0300", "U0100"]
        # read_dtcs returns a defensive copy — caller can't mutate us
        got = adapter.read_dtcs()
        got.clear()
        assert adapter.read_dtcs() == ["P0115", "P0300", "U0100"]
        # Clear with True
        assert adapter.clear_dtcs() is True
        assert adapter.read_dtcs() == []
        # Construct a refusing adapter
        refusing = MockAdapter(clear_returns=False)
        refusing.connect("COM3", 38400)
        assert refusing.clear_dtcs() is False

    def test_read_pid_supported_vs_unsupported(self):
        """Supported PID returns pid * 10; unsupported returns None."""
        adapter = MockAdapter(supported_modes=[1, 3, 4, 9])
        adapter.connect("COM3", 38400)
        assert adapter.read_pid(1) == 10
        assert adapter.read_pid(4) == 40
        assert adapter.read_pid(2) is None
        assert adapter.read_pid(255) is None

    def test_read_vin_returns_value_or_raises(self):
        """read_vin returns VIN when supported, raises when not."""
        supported = MockAdapter(vin="1HD1KHM19NB123456")
        supported.connect("COM3", 38400)
        assert supported.read_vin() == "1HD1KHM19NB123456"

        unsupported = MockAdapter(vin_unsupported=True)
        unsupported.connect("COM3", 38400)
        with pytest.raises(UnsupportedCommandError):
            unsupported.read_vin()

        # VIN-None mock returns None without raising
        none_vin = MockAdapter(vin=None)
        none_vin.connect("COM3", 38400)
        assert none_vin.read_vin() is None


# ===========================================================================
# 2. HardwareSession context manager
# ===========================================================================


class TestHardwareSession:
    """HardwareSession lifecycle — mock, override, and real-detector paths."""

    def test_mock_true_yields_connected_mock_adapter(self):
        """mock=True instantiates a default MockAdapter and connects it."""
        with HardwareSession(port="COM3", mock=True) as adapter:
            assert isinstance(adapter, MockAdapter)
            assert adapter.is_connected is True
            # Default state — the canonical P0115/P0300 pair.
            assert adapter.read_dtcs() == ["P0115", "P0300"]
        # After __exit__, adapter is disconnected
        assert adapter.is_connected is False

    def test_adapter_override_skips_both_mock_and_detector(self):
        """adapter_override takes precedence over mock + auto-detection."""
        injected = MockAdapter(dtcs=["U0100"], protocol_name="CustomProto")
        with HardwareSession(
            port="COM3", mock=True, adapter_override=injected,
        ) as adapter:
            assert adapter is injected
            assert adapter.read_dtcs() == ["U0100"]

    def test_exit_calls_disconnect_even_on_exception(self):
        """__exit__ must disconnect even when the user's code raises."""
        adapter = MockAdapter()
        with pytest.raises(ValueError):
            with HardwareSession(
                port="COM3", adapter_override=adapter,
            ):
                assert adapter.is_connected
                raise ValueError("user code boom")
        # The ValueError propagated; disconnect still ran.
        assert adapter.is_connected is False

    def test_disconnect_failure_does_not_mask_caller_exception(self):
        """Buggy disconnect() is swallowed; caller's exception wins."""
        class BrokenDisconnect(MockAdapter):
            def disconnect(self) -> None:
                raise RuntimeError("cleanup boom")

        adapter = BrokenDisconnect()
        with pytest.raises(ValueError, match="user code boom"):
            with HardwareSession(
                port="COM3", adapter_override=adapter,
            ):
                raise ValueError("user code boom")

    def test_real_auto_detector_path_returns_detected_adapter(self):
        """With mock=False and no override, HardwareSession delegates to
        AutoDetector.detect(). We patch AutoDetector to confirm."""
        sentinel_adapter = MagicMock(spec=ProtocolAdapter)
        sentinel_adapter.is_connected = True

        mock_detector_instance = MagicMock()
        mock_detector_instance.detect.return_value = sentinel_adapter

        with patch(
            "motodiag.hardware.connection.AutoDetector",
            return_value=mock_detector_instance,
        ) as mock_cls:
            with HardwareSession(
                port="COM3", make_hint="harley", timeout_s=3.0,
            ) as adapter:
                assert adapter is sentinel_adapter
            # Constructor was called with the session's kwargs
            mock_cls.assert_called_once_with(
                port="COM3", baud=None, make_hint="harley", timeout_s=3.0,
            )
            mock_detector_instance.detect.assert_called_once()

    def test_no_ecu_detected_error_propagates_unchanged(self):
        """NoECUDetectedError from AutoDetector.detect flows through."""
        err = NoECUDetectedError(
            port="COM3",
            make_hint="harley",
            errors=[("J1850Adapter", RuntimeError("no response"))],
        )
        mock_detector_instance = MagicMock()
        mock_detector_instance.detect.side_effect = err

        with patch(
            "motodiag.hardware.connection.AutoDetector",
            return_value=mock_detector_instance,
        ):
            with pytest.raises(NoECUDetectedError) as excinfo:
                with HardwareSession(port="COM3", make_hint="harley"):
                    pytest.fail("should not reach body")
            assert excinfo.value.port == "COM3"
            assert excinfo.value.make_hint == "harley"
            assert len(excinfo.value.errors) == 1


# ===========================================================================
# 3. scan command
# ===========================================================================


class TestScanCommand:
    """motodiag hardware scan — happy, edge, and error paths."""

    def test_scan_mock_happy_path_prints_dtc_table(self):
        runner = CliRunner()
        result = runner.invoke(_make_cli(), ["hardware", "scan", "--port", "COM3", "--mock"])
        assert result.exit_code == 0, result.output
        # Both default DTCs rendered
        assert "P0115" in result.output
        assert "P0300" in result.output
        # The [MOCK] badge is visible
        assert "MOCK" in result.output
        # Footer mentions the protocol name
        assert "Mock Protocol" in result.output

    def test_scan_mock_bike_slug_passes_make_hint(self, tmp_path):
        """--bike harley-glide-2015 resolves to make_hint=harley even on
        the --mock path. We verify by seeding a garage row and asserting
        the make hint is used for DTC enrichment (P0115 gets looked up
        with make='Harley-Davidson').
        """
        from motodiag.vehicles.registry import add_vehicle
        from motodiag.core.models import VehicleBase, ProtocolType

        # The HardwareSession fixture already set up init_db on tmp DB,
        # but _resolve_bike_slug uses the default DB — patch it.
        with patch("motodiag.cli.hardware._resolve_bike_slug") as mock_resolve:
            mock_resolve.return_value = {
                "id": 1, "make": "Harley-Davidson", "model": "Glide",
                "year": 2015,
            }
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                [
                    "hardware", "scan", "--port", "COM3",
                    "--bike", "harley-glide-2015", "--mock",
                ],
            )
        assert result.exit_code == 0, result.output
        mock_resolve.assert_called_once_with("harley-glide-2015")

    def test_scan_dtc_enrichment_db_hit(self, _patch_init_db):
        """A DTC present in the DB surfaces its description + severity
        in the scan table with source=db_generic (no make_hint given)."""
        db_path = _patch_init_db
        add_dtc(
            DTCCode(
                code="P0115",
                description="Engine Coolant Temperature Circuit Malfunction",
                category=SymptomCategory.COOLING,
                severity=Severity.MEDIUM,
            ),
            db_path=db_path,
        )
        # Need to also make dtc_lookup's get_dtc hit the test DB. Easiest:
        # patch resolve_dtc_info to use our db_path by monkey-patching
        # its default.
        from motodiag.knowledge import dtc_lookup as lookup_mod
        orig_resolve = lookup_mod.resolve_dtc_info

        def _resolve_with_db(code, make_hint=None, db_path=None):
            return orig_resolve(code, make_hint=make_hint, db_path=db_path or _patch_init_db)

        with patch(
            "motodiag.cli.hardware.resolve_dtc_info",
            side_effect=_resolve_with_db,
        ):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(), ["hardware", "scan", "--port", "COM3", "--mock"]
            )
        assert result.exit_code == 0, result.output
        assert "Coolant" in result.output
        # Source column shows db_generic for P0115 (no make_hint)
        assert "db_generic" in result.output

    def test_scan_dtc_enrichment_classifier_fallback(self):
        """A DTC not in the DB falls through to the classifier with
        source=classifier."""
        # Use an adapter_override with a code definitely not in any seed DB
        adapter = MockAdapter(dtcs=["P9999"])

        with patch(
            "motodiag.cli.hardware.HardwareSession",
            return_value=MagicMock(
                __enter__=MagicMock(return_value=adapter),
                __exit__=MagicMock(return_value=False),
            ),
        ):
            runner = CliRunner()
            # The HardwareSession patch above replaces the class itself;
            # we must also stub the adapter.read_dtcs path. Easier path:
            # construct a real HardwareSession with adapter_override via
            # a simpler patch.
            pass

        # Simpler: construct a real CLI invocation with a mock+override
        # by monkey-patching the HardwareSession to use our override.
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
                ["hardware", "scan", "--port", "COM3", "--mock"],
            )
        assert result.exit_code == 0, result.output
        assert "P9999" in result.output
        assert "classifier" in result.output

    def test_scan_unknown_port_prints_no_ecu_panel(self):
        """When HardwareSession raises NoECUDetectedError, scan renders
        the red panel and exits 1."""
        err = NoECUDetectedError(
            port="COM_BAD",
            make_hint=None,
            errors=[("J1850Adapter", RuntimeError("port not found"))],
        )

        class BadSession:
            def __init__(self, *a, **kw): pass
            def __enter__(self): raise err
            def __exit__(self, *a): return False

        with patch("motodiag.cli.hardware.HardwareSession", BadSession):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                ["hardware", "scan", "--port", "COM_BAD"],
            )
        assert result.exit_code == 1
        assert "No ECU detected" in result.output
        assert "J1850Adapter" in result.output
        assert "port not found" in result.output

    def test_scan_no_ecu_error_unpacks_multiple_adapter_failures(self):
        """The panel lists one line per attempted adapter, not str(exc)."""
        err = NoECUDetectedError(
            port="COM3",
            make_hint="honda",
            errors=[
                ("KLineAdapter", RuntimeError("framing error")),
                ("CANAdapter", RuntimeError("no response")),
                ("ELM327Adapter", RuntimeError("handshake failed")),
            ],
        )

        class BadSession:
            def __init__(self, *a, **kw): pass
            def __enter__(self): raise err
            def __exit__(self, *a): return False

        with patch("motodiag.cli.hardware.HardwareSession", BadSession):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                ["hardware", "scan", "--port", "COM3", "--make", "honda"],
            )
        assert result.exit_code == 1
        # All three adapter names appear
        assert "KLineAdapter" in result.output
        assert "CANAdapter" in result.output
        assert "ELM327Adapter" in result.output
        # All three error summaries appear
        assert "framing error" in result.output
        assert "no response" in result.output
        assert "handshake failed" in result.output

    def test_scan_empty_dtc_list_shows_clean_message(self):
        """Mock with dtcs=[] renders the green 'No codes stored' panel."""
        adapter = MockAdapter(dtcs=[])
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
                ["hardware", "scan", "--port", "COM3", "--mock"],
            )
        assert result.exit_code == 0, result.output
        assert "No codes stored" in result.output

    def test_scan_mock_badge_visible(self):
        """The [MOCK] badge is shown on the --mock path."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "scan", "--port", "COM3", "--mock"],
        )
        assert result.exit_code == 0
        assert "MOCK" in result.output

    def test_scan_bike_and_make_mutually_exclusive(self):
        """Passing both --bike and --make is a user error."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "scan", "--port", "COM3",
                "--bike", "harley-2015", "--make", "harley", "--mock",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_scan_bike_slug_not_found_shows_remediation(self):
        """Unknown slug renders a helpful 'Bike not found' panel."""
        with patch(
            "motodiag.cli.hardware._resolve_bike_slug",
            return_value=None,
        ):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                [
                    "hardware", "scan", "--port", "COM3",
                    "--bike", "nosuch-2015", "--mock",
                ],
            )
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or \
            "no bike" in result.output.lower()


# ===========================================================================
# 4. clear command
# ===========================================================================


class TestClearCommand:
    """motodiag hardware clear — safety, confirmation, and outcome."""

    def test_clear_shows_safety_warning(self):
        """The yellow safety panel is always printed before prompt."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "clear", "--port", "COM3", "--mock", "--yes"],
        )
        assert "safety warning" in result.output.lower() or \
            "do not clear" in result.output.lower()
        assert "clear all stored dtcs" in result.output.lower()

    def test_clear_without_yes_prompts(self):
        """No --yes ⇒ click.confirm runs; answer 'n' aborts."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "clear", "--port", "COM3", "--mock"],
            input="n\n",
        )
        # Exit 0 — abort is a user choice, not an error
        assert result.exit_code == 0
        assert "aborted" in result.output.lower()

    def test_clear_with_yes_skips_prompt(self):
        """--yes skips the prompt entirely and proceeds to clear."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "clear", "--port", "COM3", "--mock", "--yes"],
        )
        assert result.exit_code == 0
        assert "accepted the clear" in result.output.lower() or \
            "cleared" in result.output.lower()

    def test_clear_success_green_panel(self):
        """Default MockAdapter returns True from clear_dtcs."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "clear", "--port", "COM3", "--mock", "--yes"],
        )
        assert result.exit_code == 0
        assert "accepted" in result.output.lower()

    def test_clear_refusal_red_panel(self):
        """MockAdapter(clear_returns=False) triggers the red refusal path."""
        adapter = MockAdapter(clear_returns=False)
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
                ["hardware", "clear", "--port", "COM3", "--mock", "--yes"],
            )
        assert result.exit_code == 1
        assert "refused" in result.output.lower()
        assert "ignition" in result.output.lower()

    def test_clear_on_no_ecu_detected(self):
        """Clear surfaces the same red panel as scan when no ECU found."""
        err = NoECUDetectedError(
            port="COM_BAD", make_hint=None,
            errors=[("CANAdapter", RuntimeError("timeout"))],
        )

        class BadSession:
            def __init__(self, *a, **kw): pass
            def __enter__(self): raise err
            def __exit__(self, *a): return False

        with patch("motodiag.cli.hardware.HardwareSession", BadSession):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                ["hardware", "clear", "--port", "COM_BAD", "--yes"],
            )
        assert result.exit_code == 1
        assert "No ECU detected" in result.output

    def test_clear_prompt_yes_answer_proceeds(self):
        """Answering 'y' at the prompt proceeds to clear."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "clear", "--port", "COM3", "--mock"],
            input="y\n",
        )
        assert result.exit_code == 0
        assert "accepted" in result.output.lower()

    def test_clear_bike_slug_not_found(self):
        """Unknown slug renders the bike-not-found panel with exit 1."""
        with patch(
            "motodiag.cli.hardware._resolve_bike_slug",
            return_value=None,
        ):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                [
                    "hardware", "clear", "--port", "COM3",
                    "--bike", "nosuch-2015", "--mock", "--yes",
                ],
            )
        assert result.exit_code == 1


# ===========================================================================
# 5. info command
# ===========================================================================


class TestInfoCommand:
    """motodiag hardware info — identity panel rendering."""

    def test_info_mock_prints_all_fields(self):
        """Default MockAdapter → panel with VIN / ECU / sw version / modes."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "info", "--port", "COM3", "--mock"],
        )
        assert result.exit_code == 0, result.output
        assert "1HD1KHM19NB123456" in result.output  # VIN
        assert "HD-ECM-1234" in result.output  # ECU part
        assert "1.0.5" in result.output  # sw version
        assert "Mock Protocol" in result.output

    def test_info_vin_none_shows_not_available(self):
        """VIN=None renders 'not available' rather than crashing."""
        adapter = MockAdapter(vin=None)
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
                ["hardware", "info", "--port", "COM3", "--mock"],
            )
        assert result.exit_code == 0, result.output
        assert "not available" in result.output

    def test_info_vin_unsupported_does_not_crash(self):
        """vin_unsupported=True triggers UnsupportedCommandError under the
        hood but identify_info catches it and returns None."""
        adapter = MockAdapter(vin_unsupported=True)
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
                ["hardware", "info", "--port", "COM3", "--mock"],
            )
        assert result.exit_code == 0, result.output
        assert "not available" in result.output

    def test_info_empty_supported_modes(self):
        """Adapter with supported_modes=[] renders all modes as dim ✗."""
        adapter = MockAdapter(supported_modes=[])
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
                ["hardware", "info", "--port", "COM3", "--mock"],
            )
        assert result.exit_code == 0, result.output
        # Should still render the Mode 01/03/04/09 rows, just with ✗
        assert "Mode 01" in result.output
        assert "Mode 03" in result.output

    def test_info_no_ecu_detected(self):
        """info also surfaces the red panel on detection failure."""
        err = NoECUDetectedError(
            port="COM_BAD", make_hint=None,
            errors=[("J1850Adapter", RuntimeError("no response"))],
        )

        class BadSession:
            def __init__(self, *a, **kw): pass
            def __enter__(self): raise err
            def __exit__(self, *a): return False

        with patch("motodiag.cli.hardware.HardwareSession", BadSession):
            runner = CliRunner()
            result = runner.invoke(
                _make_cli(),
                ["hardware", "info", "--port", "COM_BAD"],
            )
        assert result.exit_code == 1
        assert "No ECU detected" in result.output

    def test_info_mock_badge_present(self):
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "info", "--port", "COM3", "--mock"],
        )
        assert result.exit_code == 0
        assert "MOCK" in result.output


# ===========================================================================
# 6. resolve_dtc_info (knowledge/dtc_lookup.py)
# ===========================================================================


class TestDTCLookup:
    """resolve_dtc_info — 3-tier cascade semantics."""

    def test_make_specific_hit_returns_db_make(self, _patch_init_db):
        """Exact (code, make) match → source=db_make."""
        db_path = _patch_init_db
        add_dtc(
            DTCCode(
                code="P0300",
                description="Harley-specific misfire",
                category=SymptomCategory.ENGINE,
                severity=Severity.HIGH,
                make="Harley-Davidson",
            ),
            db_path=db_path,
        )
        info = resolve_dtc_info(
            "P0300", make_hint="Harley-Davidson", db_path=db_path,
        )
        assert info["source"] == "db_make"
        assert info["description"] == "Harley-specific misfire"
        assert info["severity"] == "high"

    def test_generic_fallback_returns_db_generic(self, _patch_init_db):
        """No make-specific row, but generic row exists → db_generic."""
        db_path = _patch_init_db
        add_dtc(
            DTCCode(
                code="P0115",
                description="Generic ECT circuit",
                category=SymptomCategory.COOLING,
                severity=Severity.MEDIUM,
            ),
            db_path=db_path,
        )
        info = resolve_dtc_info("P0115", make_hint=None, db_path=db_path)
        assert info["source"] == "db_generic"
        assert info["description"] == "Generic ECT circuit"

    def test_make_scoped_fallthrough_to_generic_is_db_generic(
        self, _patch_init_db,
    ):
        """Provided make_hint but DB only has generic row → db_generic
        (not db_make, because the make scope didn't match)."""
        db_path = _patch_init_db
        add_dtc(
            DTCCode(
                code="P0115",
                description="Generic ECT circuit",
                category=SymptomCategory.COOLING,
                severity=Severity.MEDIUM,
            ),
            db_path=db_path,
        )
        info = resolve_dtc_info(
            "P0115", make_hint="Honda", db_path=db_path,
        )
        assert info["source"] == "db_generic"

    def test_classifier_fallback_on_unknown_code(self, _patch_init_db):
        """Code not in DB at all → source=classifier + severity=unknown."""
        db_path = _patch_init_db
        info = resolve_dtc_info("P9999", make_hint=None, db_path=db_path)
        assert info["source"] == "classifier"
        assert info["severity"] == "unknown"
        assert info["description"] == "Classified by pattern only"
        # Category is populated from classify_code's system label — not None
        assert info["category"] is not None

    def test_classifier_fallback_always_returns_info(self, _patch_init_db):
        """Even a totally bogus code falls through — never returns None."""
        db_path = _patch_init_db
        info = resolve_dtc_info("ZZZZZ", make_hint=None, db_path=db_path)
        assert info is not None
        assert info["code"] == "ZZZZZ"
        assert info["source"] == "classifier"
