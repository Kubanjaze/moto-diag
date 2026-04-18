"""ECU auto-detection + handshake (Phase 139).

Glue layer over Phases 134-138's protocol adapters. Given a serial port
and (optionally) a bike make hint, :class:`AutoDetector` tries each
candidate adapter in a priority order chosen from the hint, negotiates
a live session with the first one that responds, and returns the
connected :class:`ProtocolAdapter` ready for Phase 140's DTC read/clear
operations.

Design notes
------------

- **Detection is a glue layer, not a protocol.** Phases 134-138 each
  own one wire protocol; this phase owns the decision of which protocol
  to try first for a given bike. Keeping the heuristic in one place
  lets us tweak the make→protocol mapping without touching adapter
  internals.

- **Make-hint is advisory.** With no hint, detection still works — it
  just tries more candidates. A good hint can connect in <2s on a
  Harley; a bad or missing hint might take 10-15s on the same bike.

- **Japanese bikes don't use J1850; Harleys don't use K-line.**
  Hardcoding these exclusions in the priority table is cheaper than
  trying and failing — each failed ``connect()`` attempt costs real
  wall-clock time (5s typical timeout).

- **First-connect-wins returns a live adapter.** The caller owns the
  lifecycle and is responsible for ``adapter.disconnect()`` when done.
  :meth:`AutoDetector.detect` does NOT close the returned adapter.

- **Non-ProtocolError exceptions are caught and recorded.** A buggy
  adapter raising ``OSError`` or ``ValueError`` must not prevent the
  other three from being tried. The full failure list surfaces in the
  :class:`NoECUDetectedError` message so debugging is still possible.

- **``identify_ecu`` is best-effort.** Any OBD read can fail on a
  non-compliant ECU — Harley VINs aren't always on Mode 09 PID 02,
  older Japanese ECUs may return garbage for calibration ID. Returning
  ``None`` for individual fields instead of raising lets the UI show
  partial info ("VIN: 1HD...; ECU: unknown") rather than failing.

- **Adapter constructors are NOT uniform.** Phases 134-138 each settled
  on protocol-specific constructor kwargs (CAN uses ``channel`` +
  ``bitrate``, K-line uses ``port`` + ``baud`` + ``ecu_address``,
  J1850 uses ``port`` + ``baudrate`` + ``bridge``, ELM327 uses
  ``port`` + ``baud`` + ``timeout``). :meth:`_build_adapter` contains
  per-protocol wiring that maps the generic ``(port, baud, timeout_s)``
  inputs onto each adapter's real signature.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional, Tuple

from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import ProtocolError


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Make-hint → protocol priority table
# ---------------------------------------------------------------------------

#: Canonical protocol-label strings used in priority lists. Mapped to
#: concrete adapter classes inside :meth:`AutoDetector._build_adapter`.
#: Using strings here (not adapter classes directly) keeps the priority
#: table declarative and lets tests patch the build step cleanly.
PROTOCOL_CAN: str = "CAN"
PROTOCOL_KLINE: str = "KLINE"
PROTOCOL_J1850: str = "J1850"
PROTOCOL_ELM327: str = "ELM327"


#: Make-hint to ordered protocol list. Unknown / None → ``_DEFAULT_ORDER``.
#:
#: Rationales:
#:
#: - ``harley`` → J1850 → CAN → ELM327. Pre-2011 Harleys use J1850 VPW;
#:   2011+ use CAN. ELM327 is the universal fallback for generic OBD
#:   dongles paired with Harley-to-J1962 adapter cables. **K-line
#:   excluded** — Harley never used it.
#:
#: - ``honda`` / ``yamaha`` / ``kawasaki`` / ``suzuki`` → K-line → CAN →
#:   ELM327. 90s-2010 Japanese bikes are predominantly K-line /
#:   KWP2000. 2010+ moved to CAN. ELM327 fallback. **J1850 excluded**
#:   — not used on Japanese bikes.
#:
#: - ``ducati`` / ``bmw`` / ``ktm`` / ``triumph`` → CAN → K-line →
#:   ELM327. Modern European bikes are CAN-first. Older models fall
#:   back to K-line. **J1850 excluded**.
_MAKE_HINT_ORDER: dict[str, tuple[str, ...]] = {
    "harley": (PROTOCOL_J1850, PROTOCOL_CAN, PROTOCOL_ELM327),
    "honda": (PROTOCOL_KLINE, PROTOCOL_CAN, PROTOCOL_ELM327),
    "yamaha": (PROTOCOL_KLINE, PROTOCOL_CAN, PROTOCOL_ELM327),
    "kawasaki": (PROTOCOL_KLINE, PROTOCOL_CAN, PROTOCOL_ELM327),
    "suzuki": (PROTOCOL_KLINE, PROTOCOL_CAN, PROTOCOL_ELM327),
    "ducati": (PROTOCOL_CAN, PROTOCOL_KLINE, PROTOCOL_ELM327),
    "bmw": (PROTOCOL_CAN, PROTOCOL_KLINE, PROTOCOL_ELM327),
    "ktm": (PROTOCOL_CAN, PROTOCOL_KLINE, PROTOCOL_ELM327),
    "triumph": (PROTOCOL_CAN, PROTOCOL_KLINE, PROTOCOL_ELM327),
}

#: No hint / unknown make: try modern CAN first (covers most 2011+ bikes),
#: then the pre-CAN protocols, then the universal ELM327 fallback.
_DEFAULT_ORDER: tuple[str, ...] = (
    PROTOCOL_CAN,
    PROTOCOL_KLINE,
    PROTOCOL_J1850,
    PROTOCOL_ELM327,
)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class NoECUDetectedError(ProtocolError):
    """Raised by :meth:`AutoDetector.detect` when every candidate failed.

    Subclass of :class:`ProtocolError` so existing catch-all handlers
    in ``cli/`` already cover it without needing import changes.

    Attributes
    ----------
    port:
        The serial port that was probed.
    make_hint:
        The normalized make hint used to select the priority list, or
        ``None`` if no hint was provided.
    errors:
        List of ``(adapter_name, exception)`` tuples — one per attempted
        adapter, preserving the order they were tried.
    """

    def __init__(
        self,
        port: str,
        make_hint: Optional[str],
        errors: List[Tuple[str, BaseException]],
    ) -> None:
        self.port: str = port
        self.make_hint: Optional[str] = make_hint
        self.errors: List[Tuple[str, BaseException]] = list(errors)
        summary = _format_error_summary(port, make_hint, self.errors)
        super().__init__(summary)


def _format_error_summary(
    port: str,
    make_hint: Optional[str],
    errors: List[Tuple[str, BaseException]],
) -> str:
    """Render a human-readable one-line-ish summary of a detect failure."""
    hint_part = f"make_hint={make_hint}" if make_hint else "make_hint=None"
    if not errors:
        return f"No ECU detected on {port} ({hint_part}). No adapters tried."
    parts = []
    for name, err in errors:
        # Keep each error terse — one line each, truncate ultra-long messages.
        err_str = str(err).strip() or type(err).__name__
        if len(err_str) > 120:
            err_str = err_str[:117] + "..."
        parts.append(f"{name} ({err_str})")
    joined = "; ".join(parts)
    return f"No ECU detected on {port} ({hint_part}). Tried: {joined}."


# ---------------------------------------------------------------------------
# AutoDetector
# ---------------------------------------------------------------------------


class AutoDetector:
    """Try a prioritized list of protocol adapters and return the first connection.

    Parameters
    ----------
    port:
        Serial port string (``"COM3"``, ``"/dev/ttyUSB0"``, or a
        Bluetooth port). Passed to adapters that accept a serial port;
        also used as the ``channel`` argument to the CAN adapter.
    baud:
        Optional baud-rate override. ``None`` means each adapter uses
        its own default (CAN=500k, K-line=10400, J1850=10400,
        ELM327=38400). A non-None value is passed through unchanged.
    make_hint:
        Normalized (lowercase, stripped) before dispatch. Accepted
        values: ``"harley"``, ``"honda"``, ``"yamaha"``, ``"kawasaki"``,
        ``"suzuki"``, ``"ducati"``, ``"bmw"``, ``"ktm"``, ``"triumph"``,
        or ``None``. Unknown values fall to the default order silently.
    timeout_s:
        Applied per-adapter ``connect()`` attempt. Adapters that accept
        a timeout kwarg receive it; adapters that don't get ignored.
        Default: 5.0 seconds.
    compat_repo:
        Optional compatibility-knowledge module exposing
        ``protocols_to_skip_for_make(make) -> set[str]`` (Phase 145).
        When supplied AND a make_hint is given, :meth:`detect` filters
        the priority order to skip protocols that no known-compatible
        adapter for this make actually supports. When ``None``
        (default), behavior is identical to Phase 139 — zero Phase 139
        tests change. Duck-typed (any object with the named method
        works), so the caller passes
        :mod:`motodiag.hardware.compat_repo` directly or a custom
        shim for tests.
    """

    def __init__(
        self,
        port: str,
        baud: Optional[int] = None,
        make_hint: Optional[str] = None,
        timeout_s: float = 5.0,
        compat_repo: Optional[Any] = None,
    ) -> None:
        self.port: str = port
        self.baud: Optional[int] = baud
        self.make_hint: Optional[str] = self._normalize_hint(make_hint)
        self.timeout_s: float = timeout_s
        self._compat_repo: Optional[Any] = compat_repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self) -> ProtocolAdapter:
        """Try each candidate adapter; return the first connected one.

        Returns
        -------
        ProtocolAdapter
            A live, connected adapter. The caller owns the lifecycle
            and must call ``adapter.disconnect()`` when finished.

        Raises
        ------
        NoECUDetectedError
            When every candidate adapter failed to connect. The raised
            exception carries the port, make hint, and per-adapter error
            list.
        """
        protocol_names = self._protocol_order_for_hint(self.make_hint)
        errors: List[Tuple[str, BaseException]] = []

        for protocol in protocol_names:
            try:
                adapter = self._build_adapter(protocol)
            except Exception as err:  # noqa: BLE001
                # Constructor / import failure — record and continue.
                # An ImportError from a missing optional dep (pyserial,
                # python-can) shouldn't kill detection for the protocols
                # that don't need that dep.
                errors.append((protocol, err))
                logger.debug(
                    "build_adapter(%s) failed: %s", protocol, err
                )
                continue

            try:
                adapter.connect()
            except ProtocolError as err:
                errors.append((type(adapter).__name__, err))
                logger.debug(
                    "%s.connect() raised ProtocolError: %s",
                    type(adapter).__name__,
                    err,
                )
                continue
            except Exception as err:  # noqa: BLE001
                # Unexpected failure (OSError from a buggy driver,
                # ValueError from a mis-wired constructor, etc.) — record
                # and continue rather than propagate.
                errors.append((type(adapter).__name__, err))
                logger.debug(
                    "%s.connect() raised non-ProtocolError: %s (%s)",
                    type(adapter).__name__,
                    type(err).__name__,
                    err,
                )
                continue

            # First successful connect wins. Adapter is live and owned
            # by the caller.
            logger.info(
                "AutoDetector connected on %s via %s",
                self.port,
                type(adapter).__name__,
            )
            return adapter

        raise NoECUDetectedError(
            port=self.port,
            make_hint=self.make_hint,
            errors=errors,
        )

    def identify_ecu(self, adapter: ProtocolAdapter) -> dict:
        """Probe a connected adapter for VIN + ECU identity info.

        Issues OBD-style Mode 09 reads (PID 02 = VIN, PID 0A = ECU name,
        PID 04 = calibration ID, PID 08 = software version) plus a
        mode-support probe. Every read is individually wrapped in a
        ``try/except ProtocolError`` so a partial-compliance ECU never
        raises from this method — missing fields return ``None``.

        Parameters
        ----------
        adapter:
            A live :class:`ProtocolAdapter`. Must be connected — reads
            on a disconnected adapter will raise, which this method
            catches and turns into ``None`` fields.

        Returns
        -------
        dict
            Keys: ``vin``, ``ecu_id``, ``ecu_part_number``,
            ``software_version``, ``supported_modes``. Values are
            ``str | None`` except ``supported_modes`` which is a
            ``list[int]``.
        """
        result: dict = {
            "vin": None,
            "ecu_id": None,
            "ecu_part_number": None,
            "software_version": None,
            "supported_modes": [],
        }

        # VIN — Mode 09 PID 02 (standard OBD-II).
        vin_bytes = self._safe_mode9_read(adapter, 0x02)
        if vin_bytes is not None:
            result["vin"] = self._decode_vin(vin_bytes)

        # ECU name — Mode 09 PID 0A.
        ecu_name_bytes = self._safe_mode9_read(adapter, 0x0A)
        if ecu_name_bytes is not None:
            result["ecu_id"] = self._decode_ascii(ecu_name_bytes)

        # Calibration ID (ECU part number) — Mode 09 PID 04.
        cal_id_bytes = self._safe_mode9_read(adapter, 0x04)
        if cal_id_bytes is not None:
            result["ecu_part_number"] = self._decode_ascii(cal_id_bytes)

        # Software version — Mode 09 PID 08.
        sw_ver_bytes = self._safe_mode9_read(adapter, 0x08)
        if sw_ver_bytes is not None:
            result["software_version"] = self._decode_ascii(sw_ver_bytes)

        # Mode-support probe (Mode 01/02/03/04/09 each with PID 0x00).
        result["supported_modes"] = self._probe_supported_modes(adapter)

        return result

    # ------------------------------------------------------------------
    # Internals — make-hint dispatch
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_hint(make_hint: Optional[str]) -> Optional[str]:
        """Normalize a make hint to lowercase + stripped, or ``None``."""
        if make_hint is None:
            return None
        normalized = make_hint.strip().lower()
        if not normalized:
            return None
        return normalized

    def _protocol_order_for_hint(
        self, make_hint: Optional[str]
    ) -> tuple[str, ...]:
        """Return the ordered list of protocol-label strings for a hint.

        Unknown values fall to :data:`_DEFAULT_ORDER`. The returned
        tuple is consumed by :meth:`_build_adapter` which maps each
        label to a concrete adapter class + protocol-specific
        constructor kwargs.

        Phase 145: when a :attr:`_compat_repo` is attached AND a
        ``make_hint`` is available, protocols that no known adapter
        for this make supports are filtered out of the order. Falls
        back to the unfiltered order if the filter would leave an
        empty list (never brick detection because the knowledge base
        happens to be sparse for a new make).
        """
        if make_hint is None:
            order = _DEFAULT_ORDER
        else:
            order = _MAKE_HINT_ORDER.get(make_hint, _DEFAULT_ORDER)

        if self._compat_repo is None or make_hint is None:
            return order

        try:
            skip = self._compat_repo.protocols_to_skip_for_make(make_hint)
        except Exception:  # noqa: BLE001
            # A buggy compat_repo must not break detection — silently
            # fall back to the unfiltered order.
            return order

        if not skip:
            return order
        filtered = tuple(p for p in order if p not in skip)
        return filtered or order  # safety: never empty

    # ------------------------------------------------------------------
    # Internals — adapter construction (non-uniform signatures)
    # ------------------------------------------------------------------

    def _build_adapter(self, protocol: str) -> ProtocolAdapter:
        """Construct the concrete adapter for a protocol label.

        Adapter constructors are **not uniform** across Phases 135-138
        (see module docstring). This method contains the per-protocol
        wiring that translates the generic ``(port, baud, timeout_s)``
        inputs onto each adapter's real kwarg names:

        - CAN: ``channel`` (not ``port``), ``bitrate`` (not ``baud``).
        - K-line: ``port``, ``baud``, ``read_timeout`` (not ``timeout``).
        - J1850: ``port``, ``baudrate`` (not ``baud``), ``timeout_s``.
        - ELM327: ``port``, ``baud``, ``timeout`` (not ``timeout_s``).

        Imports are done lazily so a missing optional dep (e.g.
        ``python-can`` for the CAN adapter) only surfaces as an
        :class:`ImportError` when that adapter is actually tried —
        other protocols can still be attempted.
        """
        if protocol == PROTOCOL_CAN:
            from motodiag.hardware.protocols.can import CANAdapter

            kwargs: dict[str, Any] = {
                "channel": self.port,
                "request_timeout": self.timeout_s,
                "multiframe_timeout": max(self.timeout_s, 1.0),
            }
            if self.baud is not None:
                kwargs["bitrate"] = self.baud
            return CANAdapter(**kwargs)

        if protocol == PROTOCOL_KLINE:
            from motodiag.hardware.protocols.kline import KLineAdapter

            kwargs = {
                "port": self.port,
                "read_timeout": self.timeout_s,
            }
            if self.baud is not None:
                kwargs["baud"] = self.baud
            return KLineAdapter(**kwargs)

        if protocol == PROTOCOL_J1850:
            from motodiag.hardware.protocols.j1850 import J1850Adapter

            kwargs = {
                "port": self.port,
                "timeout_s": self.timeout_s,
            }
            if self.baud is not None:
                kwargs["baudrate"] = self.baud
            return J1850Adapter(**kwargs)

        if protocol == PROTOCOL_ELM327:
            from motodiag.hardware.protocols.elm327 import ELM327Adapter

            kwargs = {
                "port": self.port,
                "timeout": self.timeout_s,
            }
            if self.baud is not None:
                kwargs["baud"] = self.baud
            return ELM327Adapter(**kwargs)

        # Never expected in practice — the priority table only yields
        # the four known labels — but defensive for future expansion.
        raise ValueError(f"Unknown protocol label: {protocol!r}")

    # ------------------------------------------------------------------
    # Internals — identify_ecu helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_mode9_read(
        adapter: ProtocolAdapter, pid: int
    ) -> Optional[bytes]:
        """Issue a Mode 09 PID read; return bytes or ``None`` on failure.

        Tries ``adapter.send_request(mode=0x09, pid=pid)`` if available
        (the plan's canonical method); otherwise falls back to
        ``adapter.send_command(bytes([0x09, pid]))``. This two-method
        fallback tolerates adapter heterogeneity in Phases 134-138 —
        the :class:`ProtocolAdapter` ABC defines ``send_command`` as the
        low-level escape hatch and some concrete subclasses also expose
        a higher-level ``send_request(mode, pid)`` convenience.

        Any :class:`ProtocolError` subclass is caught and converted to
        ``None``. Non-protocol exceptions are also caught so a buggy
        adapter (e.g. AttributeError from a mocked method) doesn't
        abort the entire identify pass — the individual field simply
        stays ``None``.
        """
        try:
            send_request = getattr(adapter, "send_request", None)
            if callable(send_request):
                reply = send_request(mode=0x09, pid=pid)
            else:
                reply = adapter.send_command(bytes([0x09, pid]))
        except ProtocolError:
            return None
        except Exception:  # noqa: BLE001
            # Non-protocol failure (mocked adapter misbehaving, stray
            # AttributeError, etc.) — treat as a soft failure.
            return None
        if reply is None:
            return None
        if isinstance(reply, (bytes, bytearray)):
            return bytes(reply)
        # Some adapters may return a str — encode defensively.
        if isinstance(reply, str):
            return reply.encode("ascii", errors="replace")
        # Unknown return type — reject rather than guess.
        return None

    @staticmethod
    def _decode_vin(data: bytes) -> Optional[str]:
        """Decode a VIN from a Mode 09 PID 02 response.

        Strips OBD padding (0x00, 0xFF) and non-printable bytes. Also
        strips any leading OBD mode/PID echo bytes (``0x49 0x02 0x01``)
        that adapter implementations sometimes leave in the raw reply.
        Validates the final decoded string is exactly 17 ASCII chars;
        otherwise returns ``None``.
        """
        if not data:
            return None

        # Strip leading echo bytes: some adapter implementations return
        # the full OBD response including the "49 02 01" (service-echo,
        # PID-echo, item-count) prefix. We handle both "stripped" and
        # "with echo" inputs.
        stripped = bytes(data)
        # Peel off any number of leading "49 02 [01]" echo groups.
        while len(stripped) >= 2 and stripped[0] == 0x49 and stripped[1] == 0x02:
            # Skip '49 02'; if the next byte looks like a 1-byte item
            # count (0x01), skip it too.
            if len(stripped) >= 3 and stripped[2] == 0x01:
                stripped = stripped[3:]
            else:
                stripped = stripped[2:]

        # Filter: keep only printable ASCII, drop padding (0x00, 0xFF).
        chars: list[str] = []
        for b in stripped:
            if b in (0x00, 0xFF):
                continue
            if 0x20 <= b < 0x7F:
                chars.append(chr(b))

        vin = "".join(chars).strip().upper()
        if len(vin) != 17:
            return None
        return vin

    @staticmethod
    def _decode_ascii(data: bytes) -> Optional[str]:
        """Decode a generic Mode 09 ASCII response.

        Strips OBD padding (0x00, 0xFF) and non-printable bytes.
        Returns ``None`` if the result is empty after stripping.
        """
        if not data:
            return None

        chars: list[str] = []
        for b in bytes(data):
            if b in (0x00, 0xFF):
                continue
            if 0x20 <= b < 0x7F:
                chars.append(chr(b))

        decoded = "".join(chars).strip()
        if not decoded:
            return None
        return decoded

    @staticmethod
    def _probe_supported_modes(adapter: ProtocolAdapter) -> list[int]:
        """Probe standard OBD-II modes for support.

        Issues a PID 0x00 read on each of modes 0x01, 0x02, 0x03, 0x04,
        0x09. Any mode whose probe returns without raising a
        :class:`ProtocolError` is added to the list. This is a
        capability advertisement — Phase 140 uses it to decide whether
        to even attempt Mode 03 on ECUs that don't implement it
        (avoids a wall-clock timeout on a known-unsupported command).

        Both ``send_request(mode, pid)`` and the fallback
        ``send_command(bytes([mode, 0x00]))`` are tried in that order
        — the :class:`ProtocolAdapter` ABC only guarantees
        ``send_command``, but most concrete adapters also expose the
        higher-level ``send_request`` convenience.
        """
        supported: list[int] = []
        for mode in (0x01, 0x02, 0x03, 0x04, 0x09):
            try:
                send_request = getattr(adapter, "send_request", None)
                if callable(send_request):
                    send_request(mode=mode, pid=0x00)
                else:
                    adapter.send_command(bytes([mode, 0x00]))
            except ProtocolError:
                continue
            except Exception:  # noqa: BLE001
                continue
            supported.append(mode)
        return supported


__all__ = [
    "AutoDetector",
    "NoECUDetectedError",
    "PROTOCOL_CAN",
    "PROTOCOL_KLINE",
    "PROTOCOL_J1850",
    "PROTOCOL_ELM327",
]
