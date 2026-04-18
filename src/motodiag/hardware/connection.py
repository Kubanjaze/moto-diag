"""Hardware session context manager (Phase 140).

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
"""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Optional, Type

from motodiag.hardware.ecu_detect import AutoDetector
from motodiag.hardware.mock import MockAdapter
from motodiag.hardware.protocols.base import ProtocolAdapter


logger = logging.getLogger(__name__)


# Default serial baud rate used when the caller doesn't specify one.
# 38400 is the ELM327 factory default and a reasonable middle ground
# across K-line and J1850 adapters too. The real :class:`AutoDetector`
# path overrides this per-protocol anyway; this constant only applies
# to the ``mock=True`` and ``adapter_override`` paths.
_DEFAULT_BAUD: int = 38400


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
    ) -> None:
        self.port: str = port
        self.make_hint: Optional[str] = make_hint
        self.baud: Optional[int] = baud
        self.timeout_s: float = timeout_s
        self.mock: bool = mock
        self._adapter_override: Optional[ProtocolAdapter] = adapter_override
        self._adapter: Optional[ProtocolAdapter] = None

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

    def __enter__(self) -> ProtocolAdapter:
        """Connect the chosen adapter and return it.

        Precedence:

        1. ``adapter_override`` — use it verbatim; call ``connect()`` if
           the override isn't already connected.
        2. ``mock=True`` — instantiate a default :class:`MockAdapter`
           and connect it.
        3. Otherwise — delegate to :class:`AutoDetector`, which returns
           an already-connected adapter.

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
        if self._adapter_override is not None:
            self._adapter = self._adapter_override
            # Respect an override that's already connected — idempotent
            # per the ABC, but skipping the call is faster and keeps the
            # test log clean.
            if not self._adapter.is_connected:
                self._adapter.connect(self.port, self.baud or _DEFAULT_BAUD)
            return self._adapter

        if self.mock:
            adapter: ProtocolAdapter = MockAdapter()
            adapter.connect(self.port, self.baud or _DEFAULT_BAUD)
            self._adapter = adapter
            return adapter

        # Real auto-detection. Note :class:`AutoDetector`'s own
        # constructor signature is ``(port, baud, make_hint, timeout_s)``
        # — keyword arguments are the safe form.
        detector = AutoDetector(
            port=self.port,
            baud=self.baud,
            make_hint=self.make_hint,
            timeout_s=self.timeout_s,
        )
        self._adapter = detector.detect()
        return self._adapter

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
        # the identify question itself, ask it directly.
        identify_self = getattr(adapter, "identify_info", None)
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


__all__ = ["HardwareSession"]
