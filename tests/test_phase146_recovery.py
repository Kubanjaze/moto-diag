"""Phase 146 — Connection troubleshooting + recovery tests.

Seven test classes, ~50 tests, zero real serial I/O, zero real
``time.sleep`` (every retry path monkey-patches
``motodiag.hardware.connection.time.sleep`` to a no-op), zero live
tokens.

Test classes
------------

- :class:`TestRetryPolicy` (5) — model defaults, backoff, should_retry
  semantics, max_delay clamp, custom retry_on.
- :class:`TestHardwareSessionRetry` (10) — no-retry preserves Phase 140,
  retry wraps adapter, backoff timing, exhaustion, non-retryable
  immediate raise, auto_reconnect validation.
- :class:`TestResilientAdapter` (12) — wire methods retried, destructive
  methods passed through, UnsupportedCommandError / NoECUDetectedError
  never retried, exhaustion re-raises last.
- :class:`TestAutoReconnect` (8) — try_reconnect semantics.
- :class:`TestMockAdapterFlaky` (4) — flaky_rate clamping, determinism,
  default safety.
- :class:`TestAutoDetectorVerboseCallback` (4) — verbose flag +
  on_attempt callback hooks.
- :class:`TestDiagnoseCommand` (13) — CliRunner-driven paths through
  the 5-step troubleshooter.
"""

from __future__ import annotations

import logging

import pytest
from click.testing import CliRunner

from motodiag.cli.hardware import register_hardware
from motodiag.core.database import init_db
from motodiag.hardware.connection import (
    HardwareSession,
    ResilientAdapter,
    RetryPolicy,
)
from motodiag.hardware.ecu_detect import AutoDetector, NoECUDetectedError
from motodiag.hardware.mock import MockAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
    TimeoutError as ProtocolTimeoutError,
    UnsupportedCommandError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cli():
    """Build a fresh CLI root with just `hardware` registered."""
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_hardware(root)
    return root


@pytest.fixture(autouse=True)
def _patch_init_db(monkeypatch, tmp_path):
    """Redirect init_db() to a per-test tmp DB.

    Same pattern as Phase 140 — every hardware command calls init_db
    on top, we monkey-patch that to point at a scratch path so we
    don't touch the developer's real motodiag DB.
    """
    db_path = str(tmp_path / "phase146.db")
    init_db(db_path)
    from motodiag.cli import hardware as hw_mod

    original_init_db = hw_mod.init_db

    def _patched(*args, **kwargs):
        return (
            original_init_db(db_path, *args[1:], **kwargs)
            if args or kwargs
            else original_init_db(db_path)
        )

    monkeypatch.setattr(hw_mod, "init_db", _patched)
    yield db_path


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Neutralize ``time.sleep`` inside connection.py across every test.

    Retry-path tests that need to observe sleep durations can
    re-patch the module symbol explicitly; this blanket fixture just
    makes sure no test accidentally pays real wall-clock time.
    """
    import motodiag.hardware.connection as _conn_mod
    monkeypatch.setattr(_conn_mod.time, "sleep", lambda *_a, **_kw: None)


# ===========================================================================
# 1. RetryPolicy
# ===========================================================================


class TestRetryPolicy:
    """Pydantic model semantics — defaults, backoff, retry-eligibility."""

    def test_defaults(self):
        """Bare RetryPolicy() carries the documented defaults."""
        p = RetryPolicy()
        assert p.max_attempts == 3
        assert p.initial_delay_s == 0.5
        assert p.backoff_factor == 2.0
        assert p.max_delay_s == 5.0
        # retry_on default: exactly ProtocolConnectionError + ProtocolTimeoutError
        assert set(p.retry_on) == {
            ProtocolConnectionError, ProtocolTimeoutError,
        }

    def test_delay_for_attempt_exponential_with_clamp(self):
        """Backoff: 0.5 → 1.0 → 2.0 → 4.0 → clamped 5.0 on attempt 4."""
        p = RetryPolicy()  # defaults: 0.5, 2.0, 5.0
        assert p.delay_for_attempt(0) == pytest.approx(0.5)
        assert p.delay_for_attempt(1) == pytest.approx(1.0)
        assert p.delay_for_attempt(2) == pytest.approx(2.0)
        assert p.delay_for_attempt(3) == pytest.approx(4.0)
        # attempt 4 would be 8.0 — clamped to 5.0
        assert p.delay_for_attempt(4) == pytest.approx(5.0)
        # attempt 10 even more clamped
        assert p.delay_for_attempt(10) == pytest.approx(5.0)

    def test_should_retry_semantics(self):
        """ConnectionError + TimeoutError retried; others not."""
        p = RetryPolicy()
        assert p.should_retry(ProtocolConnectionError("boom")) is True
        assert p.should_retry(ProtocolTimeoutError("slow")) is True
        assert p.should_retry(UnsupportedCommandError("read_vin")) is False
        assert p.should_retry(
            NoECUDetectedError(port="COM3", make_hint=None, errors=[])
        ) is False
        # Arbitrary exception never retried unless the caller changed policy
        assert p.should_retry(RuntimeError("other")) is False

    def test_custom_retry_on(self):
        """retry_on can be overridden to cover custom exception types."""

        class MyErr(Exception):
            pass

        p = RetryPolicy(retry_on=[MyErr])
        assert p.should_retry(MyErr("boom")) is True
        # Defaults are NOT inherited — explicit list replaces default
        assert p.should_retry(ProtocolConnectionError("x")) is False

    def test_max_delay_clamp_honored(self):
        """A tight max_delay_s caps even the first backoff."""
        p = RetryPolicy(initial_delay_s=2.0, max_delay_s=0.5)
        # raw = 2.0 * 1.0 = 2.0, clamped to 0.5
        assert p.delay_for_attempt(0) == pytest.approx(0.5)


# ===========================================================================
# 2. HardwareSession — retry-free + retry-wrapped paths
# ===========================================================================


class _FlakyOnce(MockAdapter):
    """Helper — raises ProtocolConnectionError the first N times, then succeeds.

    Used to exercise the connect-retry loop without a real serial port.
    """

    def __init__(self, fail_times: int = 1, **kwargs):
        super().__init__(**kwargs)
        self._fail_times = fail_times
        self._attempts = 0

    def connect(self, port: str = "", baud: int = 0) -> None:
        self._attempts += 1
        if self._attempts <= self._fail_times:
            raise ProtocolConnectionError(
                f"fake transient failure #{self._attempts}"
            )
        super().connect(port, baud)


class TestHardwareSessionRetry:
    """Session-level retry semantics."""

    def test_no_retry_policy_preserves_phase_140(self):
        """retry_policy=None path returns raw adapter (NOT ResilientAdapter)."""
        with HardwareSession(port="COM3", mock=True) as adapter:
            assert isinstance(adapter, MockAdapter)
            assert not isinstance(adapter, ResilientAdapter)

    def test_retry_policy_wraps_adapter_in_resilient(self):
        """retry_policy=RetryPolicy() wraps the live adapter."""
        policy = RetryPolicy()
        with HardwareSession(
            port="COM3", mock=True, retry_policy=policy,
        ) as adapter:
            assert isinstance(adapter, ResilientAdapter)
            assert isinstance(adapter._inner, MockAdapter)

    def test_retry_exhausts_after_max_attempts(self):
        """3 consecutive connect failures raise the last exception."""
        inner = _FlakyOnce(fail_times=10)  # always fails
        policy = RetryPolicy(max_attempts=3)
        session = HardwareSession(
            port="COM3",
            adapter_override=inner,
            retry_policy=policy,
        )
        with pytest.raises(ProtocolConnectionError) as excinfo:
            with session:
                pytest.fail("should not reach body")
        assert "fake transient failure" in str(excinfo.value)
        assert inner._attempts == 3

    def test_retry_succeeds_after_two_failures(self):
        """Two transient failures then a success — session enters cleanly."""
        inner = _FlakyOnce(fail_times=2)
        policy = RetryPolicy(max_attempts=3)
        with HardwareSession(
            port="COM3",
            adapter_override=inner,
            retry_policy=policy,
        ) as adapter:
            assert isinstance(adapter, ResilientAdapter)
            assert inner._attempts == 3

    def test_backoff_sleeps_observed(self, monkeypatch):
        """Retry loop sleeps exactly max_attempts-1 times between attempts."""
        sleeps: list[float] = []
        import motodiag.hardware.connection as _conn_mod
        monkeypatch.setattr(
            _conn_mod.time, "sleep", lambda s: sleeps.append(s),
        )
        inner = _FlakyOnce(fail_times=2)
        policy = RetryPolicy(max_attempts=3, initial_delay_s=0.1,
                             backoff_factor=2.0, max_delay_s=10.0)
        with HardwareSession(
            port="COM3", adapter_override=inner, retry_policy=policy,
        ):
            pass
        # Attempts: 1 fails + sleep, 2 fails + sleep, 3 succeeds
        assert sleeps == [pytest.approx(0.1), pytest.approx(0.2)]

    def test_non_retryable_exception_raised_immediately(self):
        """RuntimeError (not in retry_on) raises on first attempt."""

        class BoomAdapter(MockAdapter):
            def connect(self, port: str = "", baud: int = 0) -> None:
                raise RuntimeError("not a retry class")

        inner = BoomAdapter()
        policy = RetryPolicy(max_attempts=5)
        with pytest.raises(RuntimeError, match="not a retry class"):
            with HardwareSession(
                port="COM3",
                adapter_override=inner,
                retry_policy=policy,
            ):
                pass

    def test_retry_policy_none_is_default(self):
        """Default constructor does NOT set retry_policy."""
        session = HardwareSession(port="COM3", mock=True)
        assert session.retry_policy is None
        assert session.auto_reconnect is False

    def test_auto_reconnect_without_retry_policy_raises(self):
        """auto_reconnect=True without a policy raises ValueError."""
        with pytest.raises(ValueError, match="auto_reconnect"):
            HardwareSession(
                port="COM3", mock=True, auto_reconnect=True,
            )

    def test_retry_preserves_exception_type_on_exhaustion(self):
        """The raised exception is the last caught, not wrapped."""
        inner = _FlakyOnce(fail_times=99)
        policy = RetryPolicy(max_attempts=2)
        with pytest.raises(ProtocolConnectionError) as excinfo:
            with HardwareSession(
                port="COM3", adapter_override=inner, retry_policy=policy,
            ):
                pass
        # Matches the most-recent failure message
        assert "#2" in str(excinfo.value)

    def test_mock_path_with_retry_wraps_mock(self):
        """mock=True with a policy wraps the default MockAdapter."""
        with HardwareSession(
            port="COM3", mock=True, retry_policy=RetryPolicy(),
        ) as adapter:
            # Inner adapter is a fresh MockAdapter — defaults apply
            assert isinstance(adapter, ResilientAdapter)
            assert adapter.read_dtcs() == ["P0115", "P0300"]


# ===========================================================================
# 3. ResilientAdapter
# ===========================================================================


class _ScriptableMock(MockAdapter):
    """MockAdapter variant — per-method scripted failure counts.

    Each wire-layer method takes a script of exceptions: a list
    indexed by attempt number. When the list element is ``None``,
    delegate to parent. Otherwise raise the scripted exception. An
    attempt index beyond the list's length defaults to success.
    """

    def __init__(self, scripts: dict[str, list], **kwargs):
        super().__init__(**kwargs)
        self._scripts = {k: list(v) for k, v in scripts.items()}
        self._call_counts: dict[str, int] = {}

    def _advance(self, name: str):
        idx = self._call_counts.get(name, 0)
        self._call_counts[name] = idx + 1
        script = self._scripts.get(name, [])
        if idx < len(script) and script[idx] is not None:
            raise script[idx]

    def send_command(self, cmd: bytes) -> bytes:
        self._advance("send_command")
        return super().send_command(cmd)

    def read_dtcs(self) -> list[str]:
        self._advance("read_dtcs")
        return super().read_dtcs()

    def read_pid(self, pid: int):
        self._advance("read_pid")
        return super().read_pid(pid)

    def read_vin(self):
        self._advance("read_vin")
        return super().read_vin()

    def clear_dtcs(self) -> bool:
        self._advance("clear_dtcs")
        return super().clear_dtcs()


class TestResilientAdapter:
    """Wrapper retry semantics — reads retried, destructive not."""

    def test_read_dtcs_retries_transient(self):
        """One TimeoutError then success — read_dtcs returns the list."""
        inner = _ScriptableMock(
            scripts={"read_dtcs": [ProtocolTimeoutError("t1")]},
        )
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=3))
        assert wrapped.read_dtcs() == ["P0115", "P0300"]
        assert inner._call_counts["read_dtcs"] == 2

    def test_read_pid_retries_connection_error(self):
        """ProtocolConnectionError is retry-eligible for reads too."""
        inner = _ScriptableMock(
            scripts={"read_pid": [ProtocolConnectionError("conn-drop")]},
            supported_modes=[1, 3, 4, 9],
        )
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=3))
        assert wrapped.read_pid(1) == 10

    def test_read_vin_retries_transient(self):
        """Transient VIN timeout recovers on second attempt."""
        inner = _ScriptableMock(
            scripts={"read_vin": [ProtocolTimeoutError("slow")]},
            vin="17CHARVINEXAMPLE1",
        )
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=3))
        assert wrapped.read_vin() == "17CHARVINEXAMPLE1"

    def test_send_command_retries_transient(self):
        """send_command is retry-eligible too."""
        inner = _ScriptableMock(
            scripts={"send_command": [ProtocolTimeoutError("t")]},
        )
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=3))
        assert wrapped.send_command(b"01 00") == b""

    def test_unsupported_command_never_retried(self):
        """UnsupportedCommandError bubbles on first attempt."""
        inner = MockAdapter(vin_unsupported=True)
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=5))
        with pytest.raises(UnsupportedCommandError):
            wrapped.read_vin()

    def test_no_ecu_detected_error_never_retried(self):
        """NoECUDetectedError raised mid-read propagates immediately."""

        class NoECUMock(MockAdapter):
            def read_dtcs(self):
                raise NoECUDetectedError(
                    port="COM3", make_hint=None, errors=[],
                )

        inner = NoECUMock()
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=5))
        with pytest.raises(NoECUDetectedError):
            wrapped.read_dtcs()

    def test_retry_exhaustion_raises_last_exception(self):
        """After max_attempts all fail, the last caught exception is raised."""
        exceptions = [
            ProtocolTimeoutError(f"t{i}") for i in range(5)
        ]
        inner = _ScriptableMock(
            scripts={"read_dtcs": exceptions},
        )
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=3))
        with pytest.raises(ProtocolTimeoutError) as excinfo:
            wrapped.read_dtcs()
        # Message matches the last (attempt 3 = index 2)
        assert "t2" in str(excinfo.value)
        assert inner._call_counts["read_dtcs"] == 3

    def test_retry_attempt_logged_at_info(self, caplog):
        """Each retry attempt is logged at INFO level."""
        inner = _ScriptableMock(
            scripts={"read_dtcs": [ProtocolTimeoutError("first")]},
        )
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=3))
        with caplog.at_level(
            logging.INFO, logger="motodiag.hardware.connection",
        ):
            wrapped.read_dtcs()
        assert any(
            "read_dtcs" in r.getMessage() for r in caplog.records
        )

    def test_clear_dtcs_not_retried(self):
        """Destructive clear_dtcs is NEVER retried — first failure raises."""
        inner = _ScriptableMock(
            scripts={
                "clear_dtcs": [
                    ProtocolTimeoutError("t1"),
                    ProtocolTimeoutError("t2"),
                ]
            }
        )
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy(max_attempts=5))
        with pytest.raises(ProtocolTimeoutError) as excinfo:
            wrapped.clear_dtcs()
        # First attempt raised — no retry happened
        assert "t1" in str(excinfo.value)
        assert inner._call_counts["clear_dtcs"] == 1

    def test_disconnect_passthrough_no_retry(self):
        """disconnect is ABC-contracted not to raise; wrapper passes through."""
        inner = MockAdapter()
        inner.connect("COM3", 0)
        wrapped = ResilientAdapter(inner, RetryPolicy())
        wrapped.disconnect()
        assert inner.is_connected is False

    def test_get_protocol_name_passthrough(self):
        """get_protocol_name returns the inner name — no retry logic."""
        inner = MockAdapter(protocol_name="TestProto")
        wrapped = ResilientAdapter(inner, RetryPolicy())
        assert wrapped.get_protocol_name() == "TestProto"

    def test_is_connected_mirrors_inner(self):
        """is_connected property reads through to the inner adapter."""
        inner = MockAdapter()
        wrapped = ResilientAdapter(inner, RetryPolicy())
        assert wrapped.is_connected is False
        inner.connect("COM3", 0)
        assert wrapped.is_connected is True
        inner.disconnect()
        assert wrapped.is_connected is False


# ===========================================================================
# 4. Auto-reconnect
# ===========================================================================


class TestAutoReconnect:
    """Session.try_reconnect helper for long-running streams/recordings."""

    def test_success_on_first_attempt_returns_true(self):
        inner = MockAdapter()
        session = HardwareSession(
            port="COM3",
            adapter_override=inner,
            retry_policy=RetryPolicy(max_attempts=3),
            auto_reconnect=True,
        )
        with session:
            assert session.try_reconnect() is True

    def test_exhausted_reconnect_returns_false(self):
        """After max_attempts consecutive connect failures, returns False."""
        inner = _FlakyOnce(fail_times=99)  # always fails
        session = HardwareSession(
            port="COM3",
            adapter_override=inner,
            retry_policy=RetryPolicy(max_attempts=3),
            auto_reconnect=True,
        )
        # __enter__ will also retry — bypass by manipulating state
        session._inner_adapter = inner
        session.retry_policy = RetryPolicy(max_attempts=3)
        assert session.try_reconnect() is False

    def test_second_attempt_success_returns_true(self, monkeypatch):
        """Reconnect at attempt 2 returns True (no exception propagation)."""
        inner = _FlakyOnce(fail_times=1)  # fails once then succeeds
        inner._attempts = 0  # reset counter from __init__
        session = HardwareSession(
            port="COM3",
            adapter_override=inner,
            retry_policy=RetryPolicy(max_attempts=3),
            auto_reconnect=True,
        )
        session._inner_adapter = inner
        session.retry_policy = RetryPolicy(max_attempts=3)
        assert session.try_reconnect() is True

    def test_requires_retry_policy_raises_valueerror(self):
        """auto_reconnect=True without a policy is a construction error."""
        with pytest.raises(ValueError):
            HardwareSession(
                port="COM3", mock=True, auto_reconnect=True,
            )

    def test_try_reconnect_without_policy_returns_false(self):
        """Calling try_reconnect on a no-policy session returns False."""
        session = HardwareSession(port="COM3", mock=True)
        # Enter to populate _inner_adapter
        session.__enter__()
        try:
            assert session.try_reconnect() is False
        finally:
            session.__exit__(None, None, None)

    def test_try_reconnect_before_enter_returns_false(self):
        """try_reconnect without an _inner_adapter returns False, not raise."""
        session = HardwareSession(
            port="COM3",
            mock=True,
            retry_policy=RetryPolicy(),
            auto_reconnect=True,
        )
        assert session.try_reconnect() is False

    def test_try_reconnect_respects_max_attempts(self):
        """Total connect attempts = retry_policy.max_attempts."""
        inner = _FlakyOnce(fail_times=99)
        inner._attempts = 0
        session = HardwareSession(
            port="COM3",
            adapter_override=inner,
            retry_policy=RetryPolicy(max_attempts=4),
            auto_reconnect=True,
        )
        session._inner_adapter = inner
        session.retry_policy = RetryPolicy(max_attempts=4)
        session.try_reconnect()
        assert inner._attempts == 4

    def test_reconnect_preserves_adapter_identity(self):
        """After a successful reconnect, the inner adapter reference is
        the same object — no wrapping happens inside try_reconnect."""
        inner = _FlakyOnce(fail_times=1)
        inner._attempts = 0
        session = HardwareSession(
            port="COM3",
            adapter_override=inner,
            retry_policy=RetryPolicy(max_attempts=3),
            auto_reconnect=True,
        )
        session._inner_adapter = inner
        session.retry_policy = RetryPolicy(max_attempts=3)
        assert session.try_reconnect() is True
        assert session._inner_adapter is inner


# ===========================================================================
# 5. MockAdapter.flaky_rate
# ===========================================================================


class TestMockAdapterFlaky:
    """Flaky-mock knobs — safe defaults + deterministic seeded behaviour."""

    def test_default_flaky_rate_never_raises(self):
        """flaky_rate=0.0 short-circuits every roll — 100 calls, 0 raises."""
        adapter = MockAdapter(flaky_rate=0.0)
        adapter.connect("COM3", 0)
        for _ in range(100):
            adapter.read_dtcs()
        # No exception raised — Phase 140 behavior fully preserved.

    def test_seeded_flaky_is_deterministic(self):
        """Two mocks with flaky_rate=0.5, flaky_seed=42 produce the same
        sequence of (raise, ok) outcomes."""

        def count_raises(seed: int, rate: float, n: int) -> int:
            adapter = MockAdapter(flaky_rate=rate, flaky_seed=seed)
            # connect() also rolls — consume it so the read_dtcs count
            # matches between two fresh adapters.
            try:
                adapter.connect("COM3", 0)
            except ProtocolTimeoutError:
                pass
            raises = 0
            for _ in range(n):
                try:
                    adapter.read_dtcs()
                except ProtocolTimeoutError:
                    raises += 1
            return raises

        a = count_raises(42, 0.5, 100)
        b = count_raises(42, 0.5, 100)
        assert a == b, (
            "Same seed + same rate must produce the same raise count"
        )
        # Sanity: with rate=0.5, somewhere between 25 and 75 of 100
        # should raise — far from 0 and far from 100.
        assert 25 <= a <= 75

    def test_different_seeds_diverge(self):
        """Two seeds with the same rate produce different outcomes."""

        def trace(seed: int) -> list[bool]:
            adapter = MockAdapter(flaky_rate=0.5, flaky_seed=seed)
            try:
                adapter.connect("COM3", 0)
            except ProtocolTimeoutError:
                pass
            results = []
            for _ in range(50):
                try:
                    adapter.read_dtcs()
                    results.append(False)
                except ProtocolTimeoutError:
                    results.append(True)
            return results

        t1 = trace(42)
        t2 = trace(7)
        assert t1 != t2

    def test_disconnect_and_protocol_name_immune_from_flaky(self):
        """disconnect() and get_protocol_name() never roll the RNG."""
        # Rate 1.0 would otherwise force a raise on EVERY call.
        adapter = MockAdapter(flaky_rate=1.0, flaky_seed=42)
        # Both of these ran zero wire traffic in Phase 140 — the flaky
        # layer must respect that.
        adapter.disconnect()
        adapter.get_protocol_name()


# ===========================================================================
# 6. AutoDetector verbose + on_attempt
# ===========================================================================


class TestAutoDetectorVerboseCallback:
    """verbose + on_attempt kwargs — additive to Phase 139."""

    def test_default_signature_preserves_phase_139(self):
        """AutoDetector with no new kwargs behaves exactly as Phase 139."""
        # Just constructing + confirming the defaults match.
        d = AutoDetector(port="COM3")
        assert d.verbose is False
        assert d.on_attempt is None

    def test_verbose_true_emits_info_log(self, caplog, monkeypatch):
        """verbose=True logs at INFO before each protocol attempt."""
        d = AutoDetector(port="NONEXISTENT", verbose=True)

        # Force every protocol to fail at build time so detect()
        # unambiguously exercises the per-protocol verbose log line.
        def always_fail(proto):
            raise RuntimeError(f"fake {proto} build fail")

        monkeypatch.setattr(d, "_build_adapter", always_fail)
        with caplog.at_level(
            logging.INFO, logger="motodiag.hardware.ecu_detect",
        ):
            try:
                d.detect()
            except NoECUDetectedError:
                pass
        messages = [r.getMessage() for r in caplog.records]
        # Expect at least one "AutoDetector trying <proto>" line
        assert any("trying" in m for m in messages)

    def test_on_attempt_callback_fires_per_protocol(self, monkeypatch):
        """on_attempt receives (name, exc) for each failed + successful try."""
        seen: list[tuple[str, object]] = []

        def cb(name: str, err):
            seen.append((name, err))

        # Force every protocol to fail via _build_adapter raising.
        d = AutoDetector(port="NONEXISTENT", on_attempt=cb)

        def always_fail(proto):
            raise RuntimeError(f"fake {proto} build fail")

        monkeypatch.setattr(d, "_build_adapter", always_fail)
        with pytest.raises(NoECUDetectedError):
            d.detect()
        # The default order tries 4 protocols
        assert len(seen) == 4
        # Each failure carried an exception object (not None)
        assert all(isinstance(err, RuntimeError) for _, err in seen)

    def test_on_attempt_callback_misbehavior_does_not_break_detect(
        self, monkeypatch,
    ):
        """A raising callback is swallowed — detect still completes."""

        def bad_cb(name: str, err):
            raise RuntimeError("callback boom")

        d = AutoDetector(port="NONEXISTENT", on_attempt=bad_cb)

        def always_fail(proto):
            raise RuntimeError(f"build fail {proto}")

        monkeypatch.setattr(d, "_build_adapter", always_fail)
        # The bad callback fires but detect still raises the real
        # terminal NoECUDetectedError — not the callback's RuntimeError.
        with pytest.raises(NoECUDetectedError):
            d.detect()


# ===========================================================================
# 7. diagnose command (CliRunner)
# ===========================================================================


class TestDiagnoseCommand:
    """CliRunner-driven tests of the 5-step troubleshooter."""

    def test_help_renders(self):
        """--help runs without error and mentions the 5 steps."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["hardware", "diagnose", "--help"],
        )
        assert result.exit_code == 0
        assert "diagnose" in result.output.lower() or "troubleshoot" in result.output.lower()

    def test_mock_all_green(self):
        """--mock runs all 5 steps and ends with 5/5 passed."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "diagnose", "--port", "COM3", "--mock"],
        )
        assert result.exit_code == 0, result.output
        # All 5 step titles appear in the output
        for token in ("Step 1", "Step 2", "Step 3", "Step 4", "Step 5"):
            assert token in result.output, (
                f"missing {token} in output:\n{result.output}"
            )
        # Summary mentions 5/5
        assert "5/5" in result.output

    def test_mock_mentions_all_steps(self):
        """Every step's title string appears in the output."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "diagnose", "--port", "COM3", "--mock"],
        )
        assert "Serial port open" in result.output
        assert "ATZ" in result.output
        assert "Negotiate protocol" in result.output
        assert "Read VIN" in result.output
        assert "DTC scan" in result.output

    def test_bad_port_short_circuits_step1(self):
        """Without --mock, a bad port fails step 1 and skips 2-5."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "diagnose", "--port", "DOES_NOT_EXIST_XYZ"],
        )
        # Exit code 1 because step 1 FAILed
        assert result.exit_code == 1, result.output
        assert "Step 1" in result.output
        # Step 2 and beyond should NOT have run.
        assert "Step 2" not in result.output
        # OS-specific remediation hint mentions at least one of the
        # common triggers
        hay = result.output
        assert any(
            hint in hay for hint in (
                "list_ports", "dialout", "CH340", "Bluetooth",
            )
        ), f"expected OS remediation hint in output:\n{hay}"

    def test_mock_step3_auto_detects_mock_protocol(self):
        """Step 3 under --mock negotiates the Mock Protocol."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "diagnose", "--port", "COM3", "--mock"],
        )
        assert "Mock Protocol" in result.output

    def test_mock_step4_reads_default_vin(self):
        """Step 4 under --mock reads the default MockAdapter VIN."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "diagnose", "--port", "COM3", "--mock"],
        )
        assert "1HD1KHM19NB123456" in result.output

    def test_mock_step5_reads_default_dtcs(self):
        """Step 5 under --mock lists the default DTCs."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "diagnose", "--port", "COM3", "--mock"],
        )
        assert "P0115" in result.output
        assert "P0300" in result.output

    def test_mock_with_make_hint_resolves(self):
        """--make does not collide with --mock and is accepted."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "diagnose", "--port", "COM3",
                "--make", "harley", "--mock",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_bike_and_make_mutex_raises_usage_error(self):
        """--bike and --make together are a usage error (exit 1)."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "diagnose", "--port", "COM3",
                "--bike", "anything", "--make", "harley", "--mock",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_verbose_flag_accepted(self):
        """--verbose runs cleanly on the mock path (no crash)."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "hardware", "diagnose", "--port", "COM3",
                "--mock", "--verbose",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_step3_failure_skips_steps_4_and_5(self, monkeypatch):
        """AutoDetector failure mid-step-3 short-circuits subsequent steps."""

        def raise_no_ecu(self):
            raise NoECUDetectedError(
                port=self.port,
                make_hint=self.make_hint,
                errors=[
                    ("CANAdapter", RuntimeError("bus off")),
                    ("KLineAdapter", RuntimeError("no response")),
                ],
            )

        monkeypatch.setattr(AutoDetector, "detect", raise_no_ecu)
        # Also stub out step 1 and 2 so they don't fail on a bogus port.
        # We patch the two helpers directly.
        from motodiag.cli import hardware as hw_mod
        monkeypatch.setattr(
            hw_mod, "_diagnose_step1_port",
            lambda c, p, m: ("OK", None),
        )
        monkeypatch.setattr(
            hw_mod, "_diagnose_step2_atz",
            lambda c, p, m: ("OK", None),
        )
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["hardware", "diagnose", "--port", "COM3"],
        )
        assert result.exit_code == 1, result.output
        # Step 3 FAILED
        assert "Step 3" in result.output
        # Step 4 and 5 did NOT run
        assert "Step 4" not in result.output
        assert "Step 5" not in result.output
        # AutoDetector failure mentioned in output
        hay = result.output.lower()
        assert "no ecu" in hay or "protocol" in hay

    def test_summary_panel_lists_pass_count(self):
        """Mock run's summary panel includes a pass count."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "diagnose", "--port", "COM3", "--mock"],
        )
        # Any of "5/5", "passed", "green"
        hay = result.output
        assert ("5/5" in hay) or ("passed" in hay.lower())

    def test_mock_exit_code_is_zero_on_all_green(self):
        """All-OK mock run exits 0."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            ["hardware", "diagnose", "--port", "COM3", "--mock"],
        )
        assert result.exit_code == 0
