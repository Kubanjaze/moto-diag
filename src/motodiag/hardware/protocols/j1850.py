"""J1850 VPW protocol adapter for pre-2011 Harley-Davidson bikes (Phase 138).

Harleys built between roughly 1995 and 2010 (Sportster 883/1200, Dyna,
Softail, Touring with Evo / TC88 / TC96 engines) ride a **10.4 kbps SAE
J1850 VPW** bus — *variable pulse width*, not the 41.6 kbps PWM variant
Ford used. 2011+ Harleys migrated to CAN (Phase 136). Anyone grafting
Ford OBD tooling onto a Harley is in for a long Saturday.

Because affordable consumer ELM327 clones do a poor job of Harley's
proprietary J1850 dialect, real shop-floor workflows go through a
**hard-wired bridge device** (Daytona Twin Tec TCFI tuner, Scan Gauge
II, Dynojet Power Commander diagnostic mode, generic J1850 pass-through
adapters). The bridge speaks J1850 VPW to the bike and USB-serial to
our laptop. :class:`J1850Adapter` talks the bridge's serial protocol,
not raw J1850 frames — bus-level bit-banging is out of scope for
Python on a shop laptop.

Multi-module polling
--------------------

Harleys from the late-90s onward carry multiple modules on the same
J1850 physical layer:

- **ECM** at module address ``0x10`` — powertrain, ``P`` codes.
- **BCM** at ``0x40`` — body (security, lights, turn signals), ``B``
  codes. Present on 2004+ Dyna/Softail/Touring.
- **ABS** at ``0x28`` — chassis wheel-speed / valve solenoids, ``C``
  codes. Present on 2007+ Touring, 2008+ Dyna.

A real diagnostic workflow polls each module address separately because
they are independent ECUs with independent DTC tables. Digital Tech II
walks the module list in sequence; we mirror that behavior. Parallel
polling is **not** safe on J1850 VPW — the shared bus uses collision
arbitration and overlapping requests from the bridge cause frame
corruption.

Prefix override
---------------

Harley's proprietary ECM sometimes emits the wrong SAE high-nibble for
non-P codes. We know from the module address which prefix is correct
(ECM→P, BCM→B, ABS→C) and override the SAE nibble. This future-proofs
against ECM firmware variations.

Lazy pyserial import
--------------------

Mechanics who only use cloud / knowledge-base features should not need
``pyserial`` installed. :func:`_ensure_pyserial` mirrors the Phase 132
``_ensure_markdown_installed`` pattern — an install-hint
:class:`~click.ClickException` is raised on ``ImportError``, never at
module import time.

Dependency injection for tests
------------------------------

:class:`J1850Adapter` accepts an optional ``serial_factory`` constructor
kwarg. Tests inject a ``MockSerial`` class; production code leaves it
default and the adapter looks up ``pyserial.Serial`` lazily at
:meth:`~J1850Adapter.connect` time.

Scope (Phase 138)
-----------------

This module covers the *shape* of the Harley J1850 protocol plus four
well-documented bridges. Byte-perfect calibration against a real bike
is Phase 147 (Gate 6 hardware integration). :meth:`~J1850Adapter.read_pid`
and live-data reads are deliberately :class:`NotImplementedError` —
those land in Phase 141 once the per-bike PID map catalog exists.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
)
from motodiag.hardware.protocols.exceptions import (
    ProtocolError,
    TimeoutError as ProtocolTimeoutError,
    UnsupportedCommandError,
)


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

#: Variable Pulse Width baud rate for Harley J1850. Ford PWM uses 41600 —
#: we are *not* that protocol.
J1850_VPW_BAUD: int = 10400

#: Default per-operation timeout in seconds. J1850 frames are slow; cold-bus
#: cranking-on ECMs on pre-2007 Sportsters can take 2+ seconds to first
#: respond. 2.5s is a middle-ground — override via constructor when
#: troubleshooting a flaky bus. Phase 146 adds retry + cold-start tuning.
DEFAULT_READ_TIMEOUT_S: float = 2.5

#: Harley module addresses on the J1850 VPW bus.
MODULE_ADDRESS: dict[str, int] = {
    "ECM": 0x10,
    "BCM": 0x40,
    "ABS": 0x28,
}

#: SAE J2012 DTC prefix by Harley module. We override the SAE high-nibble
#: decoded from the raw frame because Harley's proprietary ECM sometimes
#: emits the wrong high-nibble for non-P codes — but we always know which
#: module we just polled, so we always know the correct prefix.
DTC_PREFIX_BY_MODULE: dict[str, str] = {
    "ECM": "P",
    "BCM": "B",
    "ABS": "C",
}

#: Stable order modules are polled in. Matches Digital Tech II behavior.
_MODULE_POLL_ORDER: tuple[str, ...] = ("ECM", "BCM", "ABS")

#: Protocol identifier returned by :meth:`J1850Adapter.get_protocol_name`.
PROTOCOL_NAME: str = "SAE J1850 VPW"


# ---------------------------------------------------------------------------
# Bridge command tables
# ---------------------------------------------------------------------------
#
# Each bridge device speaks a slightly different serial protocol to our
# host. Instead of subclassing per bridge, we keep a dict of dicts —
# adding a fifth bridge (say a Harley Digital Tech II clone) is a single
# dict entry, no class hierarchy.
#
# Every bridge dict must have the same key set. Missing keys will raise
# ``KeyError`` at :meth:`J1850Adapter.connect` / ``read_dtcs`` time, which
# is preferable to silent drift.
#
# The specific byte values are researched from published vendor
# documentation but are **not** shop-floor validated in this phase. Byte
# corrections land in Phase 147 or a dedicated tuning phase. This table
# is about *shape*, not byte-perfect compatibility.


_BRIDGE_COMMANDS: dict[str, dict[str, bytes]] = {
    "daytona": {
        "handshake": b"AT@1\r",
        "set_protocol_j1850_vpw": b"ATSP 2\r",
        "read_dtc_ecm": b"03\r",
        "read_dtc_bcm": b"1901\r",
        "read_dtc_abs": b"1902\r",
        "clear_dtc_ecm": b"04\r",
        "clear_dtc_bcm": b"1904\r",
        "clear_dtc_abs": b"1905\r",
        "prompt": b">",
    },
    "scangauge": {
        "handshake": b"ATI\r",
        "set_protocol_j1850_vpw": b"ATSP 2\r",
        "read_dtc_ecm": b"10 03\r",
        "read_dtc_bcm": b"40 19 01\r",
        "read_dtc_abs": b"28 19 02\r",
        "clear_dtc_ecm": b"10 04\r",
        "clear_dtc_bcm": b"40 19 04\r",
        "clear_dtc_abs": b"28 19 05\r",
        "prompt": b">",
    },
    "dynojet": {
        "handshake": b"DJI\r",
        "set_protocol_j1850_vpw": b"DJPROTO VPW\r",
        "read_dtc_ecm": b"DJDTC ECM\r",
        "read_dtc_bcm": b"DJDTC BCM\r",
        "read_dtc_abs": b"DJDTC ABS\r",
        "clear_dtc_ecm": b"DJCLR ECM\r",
        "clear_dtc_bcm": b"DJCLR BCM\r",
        "clear_dtc_abs": b"DJCLR ABS\r",
        "prompt": b">",
    },
    "generic": {
        "handshake": b"ATI\r",
        "set_protocol_j1850_vpw": b"ATSP 2\r",
        "read_dtc_ecm": b"01 03\r",
        "read_dtc_bcm": b"01 19 01\r",
        "read_dtc_abs": b"01 19 02\r",
        "clear_dtc_ecm": b"01 04\r",
        "clear_dtc_bcm": b"01 19 04\r",
        "clear_dtc_abs": b"01 19 05\r",
        "prompt": b">",
    },
}

#: Public read-only set of bridge identifiers the adapter recognizes.
SUPPORTED_BRIDGES: frozenset[str] = frozenset(_BRIDGE_COMMANDS.keys())


# Responses the bridge reports when the queried module does not answer.
# ABS is absent on non-Touring bikes; treat these as "no DTCs," not errors.
_EMPTY_RESPONSE_MARKERS: tuple[bytes, ...] = (
    b"NO DATA",
    b"NODATA",
    b"?",
    b"UNABLE TO CONNECT",
    b"UNABLETOCONNECT",
    b"CAN ERROR",
)


# ---------------------------------------------------------------------------
# Lazy pyserial import
# ---------------------------------------------------------------------------


def _ensure_pyserial() -> Any:
    """Import ``pyserial`` lazily, surface a friendly install hint on failure.

    Called from :meth:`J1850Adapter.connect`, never at module import time.
    Tests that inject a ``serial_factory`` kwarg bypass this entirely.

    Raises
    ------
    click.ClickException
        When ``pyserial`` is not installed. The message points users to
        the ``motodiag[hardware]`` extras install target.
    """

    try:
        import serial  # noqa: WPS433 — intentional lazy import
    except ImportError as exc:
        # Import click lazily too so users without click get a plain
        # ImportError instead of a confusing click import chain.
        try:
            from click import ClickException
        except ImportError:
            raise ImportError(
                "J1850 support requires pyserial. "
                "Install with: pip install 'motodiag[hardware]'"
            ) from exc
        raise ClickException(
            "J1850 support requires pyserial. "
            "Install with: pip install 'motodiag[hardware]'"
        ) from exc
    return serial


# ---------------------------------------------------------------------------
# Module-local exception subclasses
# ---------------------------------------------------------------------------


class J1850Error(ProtocolError):
    """Base class for every J1850-specific adapter error."""


class J1850ConnectionError(J1850Error):
    """Raised when the bridge handshake fails or the port will not open."""


class J1850ClearError(J1850Error):
    """Raised when a bridge reports a DTC-clear was rejected.

    Typical cause: ECU requires engine-off / ignition-on before it will
    accept Mode 04. Callers can retry after prompting the mechanic.
    """


class J1850ParseError(J1850Error):
    """Raised when a response frame is structurally unintelligible."""


# ---------------------------------------------------------------------------
# Response parser — deliberately lenient
# ---------------------------------------------------------------------------


def _parse_j1850_response(raw: bytes, expected_module: str) -> list[str]:
    """Decode a J1850 DTC response frame into a list of DTC code strings.

    The bridge has already stripped J1850 bit-level framing; what arrives
    here is ASCII hex (with variable whitespace) or one of the sentinel
    empty-response markers (``NO DATA``, ``?``, ``UNABLE TO CONNECT``).

    Frame shape, after bridge stripping, is typically::

        [header_byte] [count_byte] <2-byte DTC> <2-byte DTC> ... [checksum]

    Every bracket is optional:

    - ``daytona`` strips the header byte.
    - ``scangauge`` includes the module-ID echo.
    - Some bridges emit a count byte; some don't.
    - Some include a checksum byte; some don't.

    This parser is deliberately tolerant — shop-floor J1850 bridges are
    notoriously inconsistent. Phase 146 adds stricter frame validation
    behind a flag; Phase 138 covers the happy path.

    Parameters
    ----------
    raw:
        Raw bytes as received from the bridge (after ``read`` up to
        prompt).
    expected_module:
        One of ``"ECM"``, ``"BCM"``, ``"ABS"``. Drives prefix selection
        and header-stripping heuristics.

    Returns
    -------
    list[str]
        Zero or more DTC codes. Codes use the module-specific prefix
        (``P`` / ``B`` / ``C``), not the raw SAE high-nibble.

    Raises
    ------
    ValueError
        If ``expected_module`` is not one of the three supported module
        names. Frame-level garbage returns ``[]`` rather than raising —
        that's the lenient contract.
    """

    if expected_module not in DTC_PREFIX_BY_MODULE:
        raise ValueError(
            f"expected_module must be one of {sorted(DTC_PREFIX_BY_MODULE)}, "
            f"got {expected_module!r}"
        )

    if not raw:
        return []

    # Normalize: uppercase, strip prompt byte, strip whitespace.
    text = raw.upper()
    text = text.replace(b">", b"")

    # Empty-response sentinels.
    compact = b"".join(text.split())
    for marker in _EMPTY_RESPONSE_MARKERS:
        if marker in compact:
            return []

    # Tokenize. Each token should be a one- or two-character hex string.
    # ``bytes.split()`` splits on any ASCII whitespace run.
    tokens = text.split()
    if not tokens:
        return []

    # If any token came in as a 4+ char blob (no spaces from the bridge),
    # chop into 2-char chunks. Mixed whitespace + no whitespace frames are
    # both seen in the wild.
    flat: list[str] = []
    for tok in tokens:
        tok_str = tok.decode("ascii", errors="replace")
        if len(tok_str) % 2 != 0:
            # Odd-length token means corrupt hex — best-effort: skip.
            continue
        for i in range(0, len(tok_str), 2):
            flat.append(tok_str[i : i + 2])

    # Hex-decode each two-char pair into a byte value; silently drop
    # anything non-hex.
    byte_vals: list[int] = []
    for pair in flat:
        try:
            byte_vals.append(int(pair, 16))
        except ValueError:
            continue

    if not byte_vals:
        return []

    # Header-detection heuristic: if the first byte matches our expected
    # module address, strip it. This handles the scangauge echo case.
    if byte_vals and byte_vals[0] == MODULE_ADDRESS[expected_module]:
        byte_vals = byte_vals[1:]

    # Count-byte heuristic: if the next byte is small (< 16) AND the
    # remaining byte count is consistent with ``count * 2``, treat it as
    # a count byte and drop it. Otherwise assume no count byte and
    # consume all remaining bytes as DTC pairs.
    if len(byte_vals) >= 3 and byte_vals[0] <= 16:
        remaining = len(byte_vals) - 1
        count = byte_vals[0]
        # Accept the count byte if it plausibly equals (or is one less
        # than) the pair count — many bridges include a trailing checksum
        # byte that we want to strip.
        if count * 2 == remaining or count * 2 == remaining - 1:
            byte_vals = byte_vals[1:]
            if count * 2 == len(byte_vals) - 1:
                # Trailing checksum byte present — drop it.
                byte_vals = byte_vals[:-1]

    # Pair bytes → DTC codes. Ignore a trailing odd byte (treat as
    # checksum).
    if len(byte_vals) % 2 == 1:
        byte_vals = byte_vals[:-1]

    prefix = DTC_PREFIX_BY_MODULE[expected_module]
    codes: list[str] = []
    for i in range(0, len(byte_vals), 2):
        high_byte = byte_vals[i]
        low_byte = byte_vals[i + 1]

        # SAE J2012 nibble decode of the high byte:
        #   bits 7-6 → code type (P/C/B/U), bits 5-4 → first digit.
        # We *override* the SAE prefix with the module-specific prefix
        # because Harley's proprietary ECM sometimes emits the wrong
        # high-nibble for non-P codes — but we always know which module
        # we just polled.
        first_digit = (high_byte >> 4) & 0x03
        second_digit = high_byte & 0x0F
        third_digit = (low_byte >> 4) & 0x0F
        fourth_digit = low_byte & 0x0F

        code = (
            f"{prefix}"
            f"{first_digit:X}"
            f"{second_digit:X}"
            f"{third_digit:X}"
            f"{fourth_digit:X}"
        )
        codes.append(code)

    return codes


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class J1850Adapter(ProtocolAdapter):
    """Adapter for J1850 VPW buses via a USB-serial bridge device.

    Constructor
    -----------

    ``port``
        Serial device path (``"COM5"``, ``"/dev/ttyUSB0"``). The port
        passed here is the default used when :meth:`connect` is called
        without overriding. Phase 134's base-class signature takes
        ``port`` + ``baud`` at :meth:`connect` time, so we also honor
        those — constructor values are defaults that :meth:`connect`
        may override.

    ``baudrate``
        Serial baud. Defaults to :data:`J1850_VPW_BAUD` (10400).

    ``bridge``
        One of :data:`SUPPORTED_BRIDGES` (``"daytona"``, ``"scangauge"``,
        ``"dynojet"``, ``"generic"``). Controls which command bytes are
        emitted. Adding a bridge is a single :data:`_BRIDGE_COMMANDS`
        entry. Defaults to ``"generic"``.

    ``timeout_s``
        Per-operation read timeout. Defaults to
        :data:`DEFAULT_READ_TIMEOUT_S`.

    ``serial_factory``
        Callable used to construct the serial-port object. Defaults to
        the result of :func:`_ensure_pyserial` at :meth:`connect` time
        (``serial.Serial``). Tests pass a ``MockSerial`` class here to
        short-circuit the pyserial import entirely.

    Multi-module behavior
    ---------------------

    :meth:`read_dtcs` polls ECM → BCM → ABS **sequentially** and returns
    the merged ``list[str]``. Per-module detail is available via the
    additional :meth:`read_dtcs_by_module` method — Phase 140 uses that
    to label DTCs by source module in the diagnosis UI.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = J1850_VPW_BAUD,
        bridge: str = "generic",
        timeout_s: float = DEFAULT_READ_TIMEOUT_S,
        serial_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        if bridge not in _BRIDGE_COMMANDS:
            raise ValueError(
                f"Unknown bridge {bridge!r}. Supported bridges: "
                f"{sorted(SUPPORTED_BRIDGES)}"
            )

        self.port: str = port
        self.baudrate: int = baudrate
        self.bridge: str = bridge
        self.timeout_s: float = timeout_s
        self._serial_factory: Optional[Callable[..., Any]] = serial_factory

        self._commands: dict[str, bytes] = _BRIDGE_COMMANDS[bridge]
        self._serial: Any = None
        self._is_connected: bool = False

    # -- Connection lifecycle ----------------------------------------------

    def connect(
        self,
        port: Optional[str] = None,
        baud: Optional[int] = None,
    ) -> None:
        """Open the serial link and run the bridge handshake.

        Phase 134's :class:`ProtocolAdapter` signature is
        ``connect(port, baud)``; Phase 138 accepts both as optional so
        callers that configured everything at construction time can just
        call ``adapter.connect()`` without re-supplying values.

        Steps:

        1. Open the serial port (8N1, no flow control).
        2. Write the bridge handshake byte sequence.
        3. Read until the bridge prompt byte or timeout.
        4. Write the set-protocol-VPW command.
        5. Read until prompt or timeout.
        6. Flip ``_is_connected = True``.

        Idempotent: re-calling ``connect()`` on an already-connected
        adapter is a no-op, matching the Phase 134 contract.

        Raises
        ------
        J1850ConnectionError
            If the port cannot be opened or the handshake times out.
        """

        if self._is_connected:
            return

        effective_port = port if port is not None else self.port
        effective_baud = baud if baud is not None else self.baudrate

        factory = self._serial_factory
        if factory is None:
            serial_mod = _ensure_pyserial()
            factory = serial_mod.Serial

        try:
            self._serial = factory(
                port=effective_port,
                baudrate=effective_baud,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=self.timeout_s,
            )
        except Exception as exc:  # serial.SerialException, OSError, etc.
            raise J1850ConnectionError(
                f"Failed to open serial port {effective_port!r} at "
                f"{effective_baud} baud: {exc}"
            ) from exc

        # Handshake.
        try:
            handshake_reply = self._exchange(self._commands["handshake"])
        except ProtocolTimeoutError as exc:
            self._safe_close()
            raise J1850ConnectionError(
                f"Bridge handshake timed out on {effective_port!r}: {exc}"
            ) from exc

        if not handshake_reply:
            self._safe_close()
            raise J1850ConnectionError(
                f"Bridge handshake returned empty response on "
                f"{effective_port!r} (bridge={self.bridge}). "
                "Check cable, ignition-on, bridge power."
            )

        # Set protocol. A spurious empty reply here is tolerated — some
        # bridges just emit a prompt byte with no ``OK`` payload.
        try:
            self._exchange(self._commands["set_protocol_j1850_vpw"])
        except ProtocolTimeoutError as exc:
            self._safe_close()
            raise J1850ConnectionError(
                "Bridge set-protocol-VPW timed out: {0}".format(exc)
            ) from exc

        self._is_connected = True

    def disconnect(self) -> None:
        """Close the serial port and clear connection state.

        Never raises — cleanup failures are logged-and-swallowed so a
        disconnect error cannot mask an earlier exception. Idempotent.
        """

        self._safe_close()
        self._is_connected = False

    def _safe_close(self) -> None:
        """Best-effort close of the serial handle. Swallows exceptions."""

        if self._serial is None:
            return
        try:
            close = getattr(self._serial, "close", None)
            if close is not None:
                close()
        except Exception:
            # Intentionally swallowed — matches Phase 134 contract that
            # disconnect never raises.
            pass
        self._serial = None

    # -- Low-level I/O -----------------------------------------------------

    def send_command(self, cmd: bytes) -> bytes:
        """Send raw bytes to the bridge, return the raw reply.

        This is the Phase 134 escape hatch for commands the higher-level
        methods do not cover. Callers are responsible for the bridge's
        own framing (including the trailing ``\\r`` on AT-style commands).

        Raises
        ------
        ConnectionError
            If the adapter is not connected.
        TimeoutError
            If the read exceeds ``timeout_s`` without a prompt byte.
        """

        if not self._is_connected or self._serial is None:
            raise ProtocolConnectionError(
                "J1850Adapter.send_command called on a disconnected adapter"
            )
        return self._exchange(cmd)

    def _exchange(self, cmd: bytes) -> bytes:
        """Write ``cmd``, read until prompt byte or end-of-stream.

        Uses :attr:`_serial.write` and :attr:`_serial.read` — the latter
        is expected to return ``b""`` on timeout (standard pyserial
        behavior). A read that returns the configured prompt byte
        terminates the loop; a read that returns ``b""`` with nothing
        buffered raises :class:`TimeoutError`.
        """

        assert self._serial is not None  # noqa: S101 — guarded by callers
        try:
            self._serial.write(cmd)
        except Exception as exc:
            raise ProtocolConnectionError(
                f"Serial write failed: {exc}"
            ) from exc

        prompt = self._commands["prompt"]
        buffer = bytearray()
        # Read loop: accumulate until prompt byte arrives or the
        # underlying read times out (returns b"").
        while True:
            try:
                chunk = self._serial.read(128)
            except Exception as exc:
                raise ProtocolConnectionError(
                    f"Serial read failed: {exc}"
                ) from exc

            if not chunk:
                # Timeout / end-of-stream. If we already have data, return
                # it; if we have nothing, raise TimeoutError.
                if buffer:
                    return bytes(buffer)
                raise ProtocolTimeoutError(
                    f"No response from bridge within {self.timeout_s}s "
                    f"for command {cmd!r}"
                )

            buffer.extend(chunk)
            if prompt and prompt in buffer:
                # Trim at (and drop) the prompt byte so the caller gets
                # a clean payload.
                idx = buffer.index(prompt)
                return bytes(buffer[:idx])

    # -- High-level protocol operations ------------------------------------

    def read_dtcs(self) -> list[str]:
        """Poll ECM, BCM, ABS in order and return a merged DTC list.

        Returns
        -------
        list[str]
            DTC codes in ``P0171`` / ``B1121`` / ``C1014`` format,
            ordered ECM-first → BCM → ABS. Empty list means no stored
            faults across any of the three modules.

        Raises
        ------
        ConnectionError
            If the adapter is not connected.
        """

        by_module = self.read_dtcs_by_module()
        merged: list[str] = []
        for module in _MODULE_POLL_ORDER:
            merged.extend(by_module.get(module, []))
        return merged

    def read_dtcs_by_module(self) -> dict[str, list[str]]:
        """Return per-module DTC lists keyed by ECM / BCM / ABS.

        Phase 140 uses this to label DTCs by source module in the
        diagnosis UI. :meth:`read_dtcs` is the thin wrapper that flattens
        it to satisfy the Phase 134 base-class return type.

        Modules that reply ``NO DATA`` / ``?`` (common for ABS on
        non-Touring bikes) map to an empty list — not an error.
        """

        if not self._is_connected or self._serial is None:
            raise ProtocolConnectionError(
                "J1850Adapter.read_dtcs called on a disconnected adapter"
            )

        results: dict[str, list[str]] = {}
        for module in _MODULE_POLL_ORDER:
            cmd_key = f"read_dtc_{module.lower()}"
            cmd = self._commands[cmd_key]
            try:
                raw = self._exchange(cmd)
            except ProtocolTimeoutError:
                # A single module timing out (ABS absent on a Sportster,
                # BCM asleep on pre-2004 Dynas) should not poison the
                # whole read. Log by omission and continue.
                results[module] = []
                continue
            results[module] = _parse_j1850_response(raw, module)
        return results

    def clear_dtcs(self, module: Optional[str] = None) -> bool:
        """Send Mode-04 (clear) to one or all modules.

        Phase 134's base signature is ``clear_dtcs() -> bool`` — we
        preserve that (no-arg → clear all, bool result) and add an
        optional ``module`` kwarg that narrows the clear to a single
        module. Calling ``clear_dtcs("ECM")`` sends only the ECM clear
        command.

        Parameters
        ----------
        module:
            ``None`` (default) → clear ECM, BCM, ABS in order; returns
            ``True`` if every clear the bridge accepted was positive.
            ``"ECM"`` / ``"BCM"`` / ``"ABS"`` → clear just that module.

        Returns
        -------
        bool
            ``True`` when every sent clear was acknowledged. ``False``
            when any module replied with a non-empty rejection (some
            ECUs require ignition-on / engine-off).

        Raises
        ------
        ConnectionError
            If the adapter is not connected.
        J1850ClearError
            If the bridge itself rejected the clear command (not the
            ECU-said-no case — that returns ``False``).
        ValueError
            If ``module`` is not one of the three supported names.
        """

        if not self._is_connected or self._serial is None:
            raise ProtocolConnectionError(
                "J1850Adapter.clear_dtcs called on a disconnected adapter"
            )

        if module is None:
            modules = list(_MODULE_POLL_ORDER)
        else:
            if module not in DTC_PREFIX_BY_MODULE:
                raise ValueError(
                    f"module must be one of {sorted(DTC_PREFIX_BY_MODULE)} "
                    f"or None, got {module!r}"
                )
            modules = [module]

        all_ok = True
        for mod in modules:
            cmd_key = f"clear_dtc_{mod.lower()}"
            cmd = self._commands[cmd_key]
            try:
                reply = self._exchange(cmd)
            except ProtocolTimeoutError as exc:
                raise J1850ClearError(
                    f"Bridge did not acknowledge clear for {mod}: {exc}"
                ) from exc

            reply_upper = reply.upper()
            # Explicit rejection markers → ECU said no.
            if b"?" in reply_upper or b"ERROR" in reply_upper:
                all_ok = False

        return all_ok

    def read_pid(self, pid: int) -> Optional[int]:
        """Not implemented until Phase 141 delivers per-bike PID maps.

        Live data on J1850 requires a catalog of per-bike Mode 01 PIDs
        that Harley kept proprietary across model years — there is no
        universal SAE-style lookup. Phase 141 ships that catalog; this
        method raises :class:`NotImplementedError` with a pointer to
        the roadmap so callers know where to look.
        """

        raise NotImplementedError(
            "J1850Adapter.read_pid is delivered by Phase 141 "
            "(live data + per-bike PID map). Phase 138 ships the "
            "DTC read/clear surface only."
        )

    def read_vin(self) -> Optional[str]:
        """VIN read is not supported on pre-2008 Harley J1850 ECMs.

        Mode 09 PID 02 was not implemented on Harley ECMs before the
        2008 Delphi refresh, and even then it is inconsistent. Callers
        should fall back to the steering-neck VIN plate.
        """

        raise UnsupportedCommandError("read_vin")

    def get_protocol_name(self) -> str:
        """Stable protocol identifier: ``"SAE J1850 VPW"``."""

        return PROTOCOL_NAME

    # -- Convenience metadata ---------------------------------------------

    def adapter_info(self) -> dict[str, Any]:
        """Return a plain dict describing the adapter configuration.

        Useful for logs and the Phase 140 ``hardware diagnose`` CLI
        header line that tells the mechanic what we're connected to.
        """

        return {
            "protocol": PROTOCOL_NAME,
            "baud": self.baudrate,
            "bridge": self.bridge,
            "port": self.port,
            "timeout_s": self.timeout_s,
            "connected": self._is_connected,
        }
