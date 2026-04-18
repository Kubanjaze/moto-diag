"""Hardware session context manager (Phase 140, extended Phase 146).

:class:`HardwareSession` is the lifecycle wrapper around Phase 139's
:class:`~motodiag.hardware.ecu_detect.AutoDetector`. It gives CLI
commands a single ``with`` block that:

1. Picks the right path — real auto-detection, a :class:`MockAdapter`
   for ``--mock`` / CI, or a caller-supplied ``adapter_override`` for
   scripted scenarios.
2. Connects the adapter (or lets :class:`NoECUDetectedError` propagate
   unchanged so the CLI surface can render a per-adapter failure panel).
3. Guarantees :meth:`ProtocolAdapter.disconnect` fires on ``__exit__``,
   even on exception paths, and **never** masks the caller's exception
   if disconnect itself misbehaves.

Design notes
------------

- The ``adapter_override`` kwarg exists specifically for tests that want
  to inject a pre-configured :class:`MockAdapter` with specific scripted
  state (e.g. ``MockAdapter(dtcs=["U0100"])``) without having to monkey-
  patch :class:`AutoDetector`. The override skips both auto-detection
  and the default ``mock=True`` path.
- ``mock=True`` with no override produces a default-state
  :class:`MockAdapter` — the standard ``motodiag hardware scan --mock``
  code path.
- :meth:`identify_ecu` is a convenience so CLI commands don't have to
  branch on "am I running on a real detector or a mock?" — the session
  knows.

Phase 146 additions
-------------------

- :class:`RetryPolicy` — Pydantic model governing how many times a
  transient connect/read failure is retried, the exponential backoff
  between attempts, and which exception classes are eligible for retry.
  When a session is constructed with ``retry_policy=None`` (the
  default), the Phase 140 code paths run byte-for-byte unchanged —
  zero Phase 140 tests need to know this phase happened.
- :class:`ResilientAdapter` — transparent :class:`ProtocolAdapter`
  decorator that wraps the live adapter once a retry-enabled session
  enters its ``with`` block. Read methods go through a retry loop;
  destructive operations (``clear_dtcs``) and lifecycle operations
  (``connect`` / ``disconnect``) do NOT retry — duplicating a Mode 04
  on a Harley is a mechanic-surprise hazard, and ABC-contract
  idempotency covers the lifecycle calls already.
- :meth:`HardwareSession.try_reconnect` — helper for long-running
  streams / recordings (Phases 141/142) that want to survive a
  mid-session ECU silence without the caller writing its own retry
  loop.
"""

from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field

from motodiag.hardware.ecu_detect import AutoDetector, NoECUDetectedError
from motodiag.hardware.mock import MockAdapter
from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
    TimeoutError as ProtocolTimeoutError,
    UnsupportedCommandError,
)


logger = logging.getLogger(__name__)


# Default serial baud rate used when the caller doesn't specify one.
# 38400 is the ELM327 factory default and a reasonable middle ground
# across K-line and J1850 adapters too. The real :class:`AutoDetector`
# path overrides this per-protocol anyway; this constant only applies
# to the ``mock=True`` and ``adapter_override`` paths.
_DEFAULT_BAUD: int = 38400


# ---------------------------------------------------------------------------
# Phase 146 — Retry policy model
# ---------------------------------------------------------------------------


class RetryPolicy(BaseModel):
    """Governs retry-with-backoff behaviour for transient hardware failures.

    An instance of this model is passed to :class:`HardwareSession` (via
    the ``retry_policy`` kwarg) to enable retry semantics. When
    ``retry_policy is None`` (the default), :class:`HardwareSession`
    runs its Phase 140 code paths unchanged.

    Parameters
    ----------
    max_attempts:
        Total number of attempts, including the first. Default 3 — two
        retries after the initial attempt. Must be >= 1 in practice;
        the model does not enforce a minimum because a caller
        deliberately constructing ``max_attempts=1`` for a
        compat-testing shim is a legal use case.
    initial_delay_s:
        Base delay before the first retry, in seconds. Default 0.5s.
    backoff_factor:
        Multiplier applied to the delay between attempts. Default 2.0
        (doubling). Combined with ``max_delay_s`` this gives the AWS-SDK
        exponential-with-clamp pattern.
    max_delay_s:
        Upper clamp on any single inter-attempt sleep. Default 5.0s.
        A three-attempt run with defaults sleeps 0.5s then 1.0s — well
        under this clamp; the clamp matters only for callers who bump
        ``max_attempts`` and want to cap their worst-case wait.
    retry_on:
        List of exception classes that trigger a retry when raised.
        Defaults to ``[ProtocolConnectionError, ProtocolTimeoutError]``
        — the two domain-layer exceptions from
        :mod:`motodiag.hardware.protocols.exceptions` aliased out of
        the Python built-in shadows. All other exceptions (including
        :class:`UnsupportedCommandError` and ``NoECUDetectedError``)
        propagate immediately regardless of policy.

    Notes
    -----
    - No jitter. Single mechanic, single bike — deterministic backoff
      is easier to reason about and easier to test.
    - ``arbitrary_types_allowed=True`` is required because Pydantic v2
      can't validate ``type[Exception]`` out of the box.
    """

    max_attempts: int = 3
    initial_delay_s: float = 0.5
    backoff_factor: float = 2.0
    max_delay_s: float = 5.0
    retry_on: List[type] = Field(
        default_factory=lambda: [
            ProtocolConnectionError,
            ProtocolTimeoutError,
        ]
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def delay_for_attempt(self, attempt_idx: int) -> float:
        """Return the sleep duration before attempt ``attempt_idx + 1``.

        ``attempt_idx`` is the zero-based index of the attempt that
        just failed — so ``delay_for_attempt(0)`` is the sleep between
        attempt 1 (which just failed) and attempt 2.

        Formula: ``min(initial_delay_s * backoff_factor ** attempt_idx,
        max_delay_s)`` — clamped exponential.
        """
        raw = self.initial_delay_s * (self.backoff_factor ** attempt_idx)
        return min(raw, self.max_delay_s)

    def should_retry(self, exc: BaseException) -> bool:
        """Return whether ``exc`` is eligible for a retry under this policy.

        True iff ``exc`` is an instance of any class in :attr:`retry_on`.
        :class:`UnsupportedCommandError` and ``NoECUDetectedError`` are
        deliberately not in the default list — the former is a
        semantic NACK (retrying cannot change the protocol's
        capabilities), the latter is terminal (retrying against a
        fundamentally unreachable ECU just burns wall-clock time).
        """
        return any(isinstance(exc, cls) for cls in self.retry_on)


# ---------------------------------------------------------------------------
# Phase 146 — Resilient adapter wrapper
# ---------------------------------------------------------------------------


class ResilientAdapter(ProtocolAdapter):
    """Transparent :class:`ProtocolAdapter` decorator with retry semantics.

    Wraps an already-connected inner adapter plus a :class:`RetryPolicy`.
    Read methods (``send_command``, ``read_dtcs``, ``read_pid``,
    ``read_vin``) retry transient failures per the policy. Destructive
    methods (``clear_dtcs``) and lifecycle methods (``connect``,
    ``disconnect``, ``get_protocol_name``, ``is_connected``) pass
    through to the inner adapter without retry — duplicating a Mode 04
    on a Harley ECU is a mechanic-surprise hazard, and lifecycle calls
    are already idempotent per the Phase 134 ABC contract.

    The decorator is itself a concrete :class:`ProtocolAdapter`
    subclass, so anything that accepts a ``ProtocolAdapter`` will
    accept a ``ResilientAdapter`` transparently — no downstream code
    changes needed.

    Parameters
    ----------
    inner:
        The live (already connected) :class:`ProtocolAdapter` to wrap.
        Ownership transfers to the wrapper: callers should only
        interact with the wrapped interface after construction.
    policy:
        The :class:`RetryPolicy` governing retry behaviour. Typically
        supplied by :class:`HardwareSession.__enter__` when
        ``retry_policy`` was passed to the session.
    """

    def __init__(
        self,
        inner: ProtocolAdapter,
        policy: RetryPolicy,
    ) -> None:
        self._inner: ProtocolAdapter = inner
        self._policy: RetryPolicy = policy
        # The ABC's ``is_connected`` property reads ``_is_connected``
        # off ``self``; we want it to mirror the inner adapter's state
        # without drifting. The property override below does the
        # forwarding, so this backing attribute is never actually read.
        self._is_connected = False  # pragma: no cover — shadowed by property

    # --- Lifecycle — pass-through, NO retry ----------------------------

    def connect(self, port: str = "", baud: int = 0) -> None:
        """Pass ``connect`` straight to the inner adapter. Never retries.

        Connection establishment is handled by the session's own retry
        loop in :meth:`HardwareSession.__enter__`; by the time a
        ResilientAdapter exists, the inner adapter is already
        connected. This override exists for ABC compliance plus the
        edge case where a caller wants to reconnect an already-torn-
        down wrapper explicitly.
        """
        self._inner.connect(port, baud)

    def disconnect(self) -> None:
        """Pass ``disconnect`` to the inner adapter. Never retries.

        The ABC contract says ``disconnect`` must not raise — wrapping
        it in a retry loop would just mask bugs.
        """
        self._inner.disconnect()

    def get_protocol_name(self) -> str:
        """Return the inner adapter's protocol name. No retry."""
        return self._inner.get_protocol_name()

    @property
    def is_connected(self) -> bool:  # type: ignore[override]
        """Mirror the inner adapter's connection state."""
        return self._inner.is_connected

    # --- Destructive — pass-through, NO retry --------------------------

    def clear_dtcs(self) -> bool:
        """Pass ``clear_dtcs`` to the inner adapter. Never retries.

        Mode 04 (clear DTCs) is destructive: on a successful execute
        the ECU erases stored codes and freeze-frame data. Retrying a
        clear that appeared to time out could duplicate the operation
        after the first one actually landed — a mechanic-surprise
        hazard. The CLI's ``clear`` command defaults ``--no-retry`` and
        does not wrap the adapter in a ResilientAdapter for that flow;
        this pass-through exists only so the wrapper remains a fully
        compliant :class:`ProtocolAdapter`.
        """
        return self._inner.clear_dtcs()

    # --- Reads — retried per policy ------------------------------------

    def send_command(self, cmd: bytes) -> bytes:
        """Send a raw command, retrying transient failures."""
        return self._with_retry(
            "send_command", lambda: self._inner.send_command(cmd),
        )

    def read_dtcs(self) -> list[str]:
        """Read stored DTCs, retrying transient failures."""
        return self._with_retry("read_dtcs", self._inner.read_dtcs)

    def read_pid(self, pid: int) -> Optional[int]:
        """Read a single PID, retrying transient failures."""
        return self._with_retry(
            "read_pid", lambda: self._inner.read_pid(pid),
        )

    def read_vin(self) -> Optional[str]:
        """Read the VIN, retrying transient failures.

        :class:`UnsupportedCommandError` is NOT retried — a protocol
        that can't carry VIN won't develop the capability on a retry.
        """
        return self._with_retry("read_vin", self._inner.read_vin)

    # --- Retry core ----------------------------------------------------

    def _with_retry(self, op_name: str, fn):
        """Execute ``fn`` with retry semantics per :attr:`_policy`.

        :class:`UnsupportedCommandError` and ``NoECUDetectedError`` are
        re-raised immediately regardless of the policy — retrying them
        is either semantically meaningless (unsupported) or a waste of
        time (ECU unreachable).

        Other exceptions are checked against
        :meth:`RetryPolicy.should_retry`. On a retry-eligible failure,
        the method logs at INFO and sleeps
        :meth:`RetryPolicy.delay_for_attempt`. After
        ``max_attempts`` the last exception is re-raised.
        """
        last_exc: Optional[BaseException] = None
        max_attempts = max(1, int(self._policy.max_attempts))
        for attempt in range(max_attempts):
            try:
                return fn()
            except UnsupportedCommandError:
                raise
            except NoECUDetectedError:
                raise
            except Exception as exc:  # noqa: BLE001
                if not self._policy.should_retry(exc):
                    raise
                last_exc = exc
                logger.info(
                    "ResilientAdapter.%s attempt %d/%d failed: %s",
                    op_name, attempt + 1, max_attempts, exc,
                )
                if attempt + 1 < max_attempts:
                    time.sleep(self._policy.delay_for_attempt(attempt))
                continue
        # Exhausted retries — re-raise the last caught exception. If
        # last_exc is somehow still None (defensive — would only happen
        # with max_attempts=0, which max() above prevents), raise a
        # RuntimeError to surface the misconfig loudly rather than
        # silently returning None.
        if last_exc is None:  # pragma: no cover — guarded by max(1,...)
            raise RuntimeError(
                f"ResilientAdapter.{op_name} exhausted retries with no "
                "recorded exception — policy misconfigured?"
            )
        raise last_exc


# ---------------------------------------------------------------------------
# HardwareSession
# ---------------------------------------------------------------------------


class HardwareSession:
    """Context manager wrapping :class:`AutoDetector` and adapter lifecycle.

    Parameters
    ----------
    port:
        Serial port string (``"COM3"``, ``"/dev/ttyUSB0"``, etc.).
        Passed through to :class:`AutoDetector` on the real path; used
        only as the documented target on the mock / override paths.
    make_hint:
        Optional manufacturer hint (``"harley"``, ``"honda"``, …) that
        steers :class:`AutoDetector`'s protocol priority order. Ignored
        on the mock / override paths.
    baud:
        Optional serial baud-rate override. ``None`` lets
        :class:`AutoDetector` pick the per-protocol default; on the
        mock / override paths, ``None`` degrades to ``_DEFAULT_BAUD``
        (38400) when calling ``connect()``.
    timeout_s:
        Per-adapter connect-attempt timeout in seconds. Default 2.0
        seconds matches the Phase 134 ABC default; the real detector
        uses 5.0 as its own default but the CLI layer wants a snappier
        2.0 so mechanics don't wait 20s on unreachable hardware.
    mock:
        When ``True`` (and no ``adapter_override`` supplied), instantiate
        a default-state :class:`MockAdapter` and skip auto-detection.
        This is the ``--mock`` CLI flag path.
    adapter_override:
        Escape hatch for tests: a pre-built :class:`ProtocolAdapter`
        (typically a :class:`MockAdapter` with specific scripted state)
        that the session should use verbatim. Takes precedence over
        both ``mock`` and the auto-detector path.
    retry_policy:
        **Phase 146 addition.** When supplied, the session wraps the
        negotiated adapter in a :class:`ResilientAdapter` and retries
        transient connect failures with exponential backoff per the
        policy. When ``None`` (default), the Phase 140 code paths run
        byte-for-byte unchanged — zero Phase 140 tests change.
    auto_reconnect:
        **Phase 146 addition.** When ``True``, long-running callers
        (streams, recordings) can invoke :meth:`try_reconnect` to
        recover from a mid-session ECU silence. Requires
        ``retry_policy`` to be supplied (``ValueError`` otherwise) —
        the policy defines the reconnect cadence.

    Attributes
    ----------
    adapter:
        The live :class:`ProtocolAdapter`. Populated by
        :meth:`__enter__`; reading it outside a ``with`` block raises
        :class:`RuntimeError`.
    """

    def __init__(
        self,
        port: str,
        make_hint: Optional[str] = None,
        baud: Optional[int] = None,
        timeout_s: float = 2.0,
        mock: bool = False,
        adapter_override: Optional[ProtocolAdapter] = None,
        retry_policy: Optional[RetryPolicy] = None,
        auto_reconnect: bool = False,
    ) -> None:
        if auto_reconnect and retry_policy is None:
            raise ValueError(
                "auto_reconnect=True requires a retry_policy — the "
                "policy defines the reconnect cadence."
            )
        self.port: str = port
        self.make_hint: Optional[str] = make_hint
        self.baud: Optional[int] = baud
        self.timeout_s: float = timeout_s
        self.mock: bool = mock
        self._adapter_override: Optional[ProtocolAdapter] = adapter_override
        self._adapter: Optional[ProtocolAdapter] = None
        # Inner adapter — for retry-wrapped sessions this is the raw
        # pre-decoration adapter, used by :meth:`try_reconnect` to
        # re-establish the underlying transport. For non-retry
        # sessions, stays None (try_reconnect is a no-op without a
        # policy anyway).
        self._inner_adapter: Optional[ProtocolAdapter] = None
        self.retry_policy: Optional[RetryPolicy] = retry_policy
        self.auto_reconnect: bool = auto_reconnect

    # --- Public accessor -----------------------------------------------

    @property
    def adapter(self) -> ProtocolAdapter:
        """The live adapter. Only valid between ``__enter__`` and ``__exit__``.

        Raises
        ------
        RuntimeError
            If accessed before :meth:`__enter__` has run.
        """
        if self._adapter is None:
            raise RuntimeError(
                "HardwareSession.adapter accessed outside a 'with' block"
            )
        return self._adapter

    # --- Context manager -----------------------------------------------

    def _enter_once(self) -> ProtocolAdapter:
        """Run one lifecycle pass of the Phase 140 __enter__ logic.

        Refactored out of :meth:`__enter__` so the Phase 146 retry loop
        can call it repeatedly. When the session has no retry policy,
        :meth:`__enter__` calls this exactly once and the Phase 140
        behavior is byte-identical.

        Returns the raw (non-wrapped) :class:`ProtocolAdapter`.
        """
        if self._adapter_override is not None:
            adapter: ProtocolAdapter = self._adapter_override
            # Respect an override that's already connected — idempotent
            # per the ABC, but skipping the call is faster and keeps the
            # test log clean.
            if not adapter.is_connected:
                adapter.connect(self.port, self.baud or _DEFAULT_BAUD)
            return adapter

        if self.mock:
            adapter = MockAdapter()
            adapter.connect(self.port, self.baud or _DEFAULT_BAUD)
            return adapter

        # Real auto-detection. :class:`AutoDetector`'s constructor
        # signature is ``(port, baud, make_hint, timeout_s, compat_repo,
        # verbose, on_attempt)`` — keyword arguments are the safe form.
        detector = AutoDetector(
            port=self.port,
            baud=self.baud,
            make_hint=self.make_hint,
            timeout_s=self.timeout_s,
        )
        return detector.detect()

    def __enter__(self) -> ProtocolAdapter:
        """Connect the chosen adapter and return it.

        Precedence:

        1. ``adapter_override`` — use it verbatim; call ``connect()`` if
           the override isn't already connected.
        2. ``mock=True`` — instantiate a default :class:`MockAdapter`
           and connect it.
        3. Otherwise — delegate to :class:`AutoDetector`, which returns
           an already-connected adapter.

        Phase 146: when ``retry_policy`` was supplied, the connect pass
        above runs inside a retry-with-backoff loop governed by the
        policy. The first success wins; retry-eligible exceptions are
        logged and slept through; non-retry exceptions bubble
        immediately. A successful connect wraps the live adapter in a
        :class:`ResilientAdapter` so subsequent reads are also
        retry-covered.

        Raises
        ------
        NoECUDetectedError
            Propagated unchanged from :meth:`AutoDetector.detect` so the
            CLI layer can render its per-adapter failure panel.
        ConnectionError
            From the mock / override path if ``connect()`` fails
            (typically a :class:`MockAdapter` constructed with
            ``fail_on_connect=True``).
        """
        if self.retry_policy is None:
            # Phase 140 path — byte-identical.
            raw = self._enter_once()
            self._inner_adapter = raw
            self._adapter = raw
            return raw

        # Phase 146 path — retry loop around _enter_once.
        last_exc: Optional[BaseException] = None
        max_attempts = max(1, int(self.retry_policy.max_attempts))
        for attempt in range(max_attempts):
            try:
                raw = self._enter_once()
            except Exception as exc:  # noqa: BLE001
                if not self.retry_policy.should_retry(exc):
                    raise
                last_exc = exc
                logger.info(
                    "HardwareSession connect attempt %d/%d failed: %s",
                    attempt + 1, max_attempts, exc,
                )
                if attempt + 1 < max_attempts:
                    time.sleep(
                        self.retry_policy.delay_for_attempt(attempt)
                    )
                continue
            # Success — wrap in ResilientAdapter and return.
            self._inner_adapter = raw
            wrapped = ResilientAdapter(raw, self.retry_policy)
            self._adapter = wrapped
            return wrapped
        # Exhausted retries.
        if last_exc is None:  # pragma: no cover — guarded above
            raise RuntimeError(
                "HardwareSession connect exhausted retries with no "
                "recorded exception"
            )
        raise last_exc

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        """Disconnect the adapter. Never masks the caller's exception.

        The ABC's ``disconnect()`` contract promises not to raise, but
        a buggy subclass might. If one does and we're already
        propagating a caller exception, we swallow the cleanup error
        (and log it at DEBUG) so the original exception reaches the
        caller unchanged. If no exception is in flight, a cleanup
        failure is still swallowed rather than raised — hardware
        cleanup errors should never kill a user's workflow.
        """
        if self._adapter is not None:
            try:
                self._adapter.disconnect()
            except Exception as cleanup_exc:  # noqa: BLE001
                logger.debug(
                    "HardwareSession disconnect raised %s: %s",
                    type(cleanup_exc).__name__,
                    cleanup_exc,
                )
        # Return False so any in-flight exception propagates unchanged.
        return False

    # --- Phase 146: mid-session reconnect ------------------------------

    def try_reconnect(self) -> bool:
        """Attempt to reconnect the inner adapter in place.

        For long-running streams / recordings that want to survive a
        mid-session ECU silence. Uses the same exponential-backoff
        cadence as the session's connect-time retry loop (driven by
        :attr:`retry_policy`).

        Returns
        -------
        bool
            ``True`` on a successful reconnect (the inner adapter is
            live and the outer wrapper continues to route through it).
            ``False`` after ``max_attempts`` consecutive failures —
            callers decide whether to abort or continue.

        Notes
        -----
        - Calling ``try_reconnect`` on a session that was constructed
          without a retry_policy returns ``False`` immediately (no
          reconnect cadence to honour).
        - The inner adapter's ``connect()`` is idempotent per the ABC
          contract, so re-issuing it on an already-connected adapter
          is safe.
        - Logs each attempt at INFO so the CLI layer (and mechanics
          reading the log) can see the reconnect happening.
        """
        if self.retry_policy is None:
            logger.debug(
                "try_reconnect called on a session with no retry_policy"
            )
            return False
        if self._inner_adapter is None:
            logger.debug(
                "try_reconnect called before __enter__ / after __exit__"
            )
            return False
        max_attempts = max(1, int(self.retry_policy.max_attempts))
        for attempt in range(max_attempts):
            try:
                logger.info(
                    "HardwareSession reconnect attempt %d/%d on %s",
                    attempt + 1, max_attempts, self.port,
                )
                self._inner_adapter.connect(
                    self.port, self.baud or _DEFAULT_BAUD,
                )
            except Exception as exc:  # noqa: BLE001
                logger.info(
                    "HardwareSession reconnect attempt %d/%d failed: %s",
                    attempt + 1, max_attempts, exc,
                )
                if attempt + 1 < max_attempts:
                    time.sleep(
                        self.retry_policy.delay_for_attempt(attempt)
                    )
                continue
            return True
        return False

    # --- ECU identification helper -------------------------------------

    def identify_ecu(self) -> dict:
        """Return a VIN / ECU / sw-version / supported-modes snapshot.

        On the mock / override paths (where the adapter is a
        :class:`MockAdapter`), reads directly from the mock's
        :meth:`~MockAdapter.identify_info` helper — bypassing
        :class:`AutoDetector.identify_ecu` entirely because the mock
        doesn't implement ``send_command`` in a way that would yield
        real-looking Mode 09 responses.

        On the real-detector path, delegates to
        :meth:`AutoDetector.identify_ecu`, then massages the returned
        dict into the same ``{vin, ecu_part, sw_version, supported_modes,
        protocol_name}`` shape the CLI's ``info`` command expects.
        """
        adapter = self.adapter
        # Mock / override shortcut — if the adapter knows how to answer
        # the identify question itself, ask it directly. When a
        # ResilientAdapter is wrapping a MockAdapter, the wrapper does
        # NOT expose ``identify_info`` — so we also check the inner
        # adapter for the shortcut.
        identify_self = getattr(adapter, "identify_info", None)
        if not callable(identify_self) and self._inner_adapter is not None:
            identify_self = getattr(
                self._inner_adapter, "identify_info", None,
            )
        if callable(identify_self):
            info = identify_self()
            # Ensure protocol_name is always populated — some future
            # mock subclass might forget to set it.
            info.setdefault("protocol_name", adapter.get_protocol_name())
            return info

        # Real detector path. We re-use AutoDetector's identify logic
        # but re-shape its dict onto the CLI's field names so the info
        # command has one surface to render.
        detector = AutoDetector(
            port=self.port,
            baud=self.baud,
            make_hint=self.make_hint,
            timeout_s=self.timeout_s,
        )
        raw = detector.identify_ecu(adapter)
        return {
            "vin": raw.get("vin"),
            "ecu_part": raw.get("ecu_part_number"),
            "sw_version": raw.get("software_version"),
            "supported_modes": raw.get("supported_modes", []),
            "protocol_name": adapter.get_protocol_name(),
        }


__all__ = [
    "HardwareSession",
    "RetryPolicy",
    "ResilientAdapter",
]
