"""ELM327 OBD-II adapter (Phase 135).

Concrete :class:`ProtocolAdapter` implementation for the ELM327 AT
command protocol. The ELM327 is the de-facto interface chip for ~80 %
of aftermarket OBD-II dongles on the market — Bluetooth OBDLink MX+,
Vgate iCar, OBDLink SX, and every $5 eBay "ELM327 v1.5" clone all speak
this wire protocol. Shipping this adapter unlocks real-world motorcycle
scan support for every platform reachable via a CAN-to-ELM bridge
(ISO 15765-4, ISO 9141-2, KWP2000, J1850).

Design notes
------------

* **Lazy pyserial import.** :mod:`serial` is only imported the first
  time :meth:`ELM327Adapter.connect` is called, via the small
  :func:`_get_serial_module` indirection. Three wins: (1) importing
  this module on a machine without ``pyserial`` never crashes; (2)
  the install hint lives at ``connect()`` time, where it's useful;
  (3) tests monkeypatch :func:`_get_serial_module` — no
  ``sys.modules`` gymnastics, no fragile import-order plumbing.

* **Prompt-terminated I/O.** The ELM327 sends ``>`` whenever it is
  ready for the next command. Read-until-prompt is the only framing
  we need — no length prefix, no escape bytes.

* **Two timeout regimes.** Most AT commands reply in < 100 ms. ``ATZ``
  (reset) and ``ATSP0`` (auto protocol) can take 4-5 s on cold start
  as the chip probes buses, so we use :data:`SLOW_CMD_TIMEOUT_S` for
  those and :data:`DEFAULT_TIMEOUT_S` for everything else.

* **SAE J2012 DTC decoder.** Pure function (:func:`_parse_dtc_hex`),
  no I/O — unit-testable in isolation. Top 2 bits of the first byte
  select the letter (00=P, 01=C, 10=B, 11=U), the remaining 14 bits
  render as 4 hex digits.

* **ELM error tokens.** ``NO DATA``, ``UNABLE TO CONNECT``, ``CAN
  ERROR``, ``BUS ERROR``, ``?``, ``STOPPED``, ``BUFFER FULL`` all
  raise :class:`ProtocolError`. ``SEARCHING...`` is informational
  (the chip is auto-detecting a protocol) and is stripped as noise.
  ``NO DATA`` specifically on :meth:`read_dtcs` is benign — it means
  "no stored codes" and the method returns ``[]`` instead of raising.

* **Multi-frame CAN reassembly.** ISO 15765-2 transport splits
  responses > 7 payload bytes across multiple frames; the ELM327
  prefixes them with ``0:``, ``1:``, ``2:`` on separate lines. We
  strip those prefixes and concatenate the payload hex.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError as ProtocolConnectionError,
    ProtocolError,
    TimeoutError as ProtocolTimeoutError,
)

logger = logging.getLogger(__name__)


# -- Protocol constants -----------------------------------------------------

ELM_PROMPT: bytes = b">"  # ELM327 always terminates a reply with '>'
ELM_LINE_END: bytes = b"\r"  # AT commands terminated with CR

DEFAULT_BAUD: int = 38400  # ELM327 v1.5 factory default
DEFAULT_TIMEOUT_S: float = 2.0  # Most AT commands reply in < 100 ms
SLOW_CMD_TIMEOUT_S: float = 5.0  # ATZ reset + ATSP0 auto-detect on cold start

# ELM error tokens that indicate a real failure (not noise).
# Ordered longest-first so substring checks don't false-match a
# shorter token that is a prefix of a longer one.
_ELM_ERROR_TOKENS: tuple[str, ...] = (
    "UNABLE TO CONNECT",
    "BUFFER FULL",
    "CAN ERROR",
    "BUS ERROR",
    "NO DATA",
    "STOPPED",
    "?",
)

# Informational messages the chip emits while auto-detecting a protocol;
# we strip these rather than treat them as errors.
_ELM_NOISE_TOKENS: tuple[str, ...] = (
    "SEARCHING...",
    "BUS INIT",
    "BUS INIT: OK",
    "BUS INIT:...OK",
)


def _get_serial_module():  # pragma: no cover - trivial indirection
    """Return the :mod:`serial` module, raising ``ImportError`` if absent.

    This one-line indirection is the single testability seam: tests
    monkey-patch ``motodiag.hardware.protocols.elm327._get_serial_module``
    to return a fake module, eliminating ``sys.modules`` trickery and
    import-order fragility. The smell of "a function that only exists
    for tests" is strictly cheaper than the alternatives.
    """

    import serial  # noqa: I001 — intentional lazy import

    return serial


# -- Pure parsers (unit-testable, no I/O) -----------------------------------


def _parse_dtc_hex(hex_pairs: list[tuple[str, str]]) -> list[str]:
    """Decode SAE J2012 diagnostic-trouble-code hex pairs.

    Parameters
    ----------
    hex_pairs:
        A list of ``(byte1_hex, byte2_hex)`` tuples. Each tuple encodes
        one DTC. The pair ``("00", "00")`` is padding and is filtered
        out (ELM327 zero-pads responses to a consistent frame length).

    Returns
    -------
    list[str]
        Decoded codes in canonical ``[PCBU]XXXX`` format. Order is
        preserved from the input so callers can dedupe / sort if they
        need to.

    Examples
    --------
    >>> _parse_dtc_hex([("01", "33")])
    ['P0133']
    >>> _parse_dtc_hex([("41", "23")])  # 0x41 >> 6 == 1 → 'C'
    ['C0123']
    >>> _parse_dtc_hex([("81", "56")])  # 0x81 >> 6 == 2 → 'B'
    ['B0156']
    >>> _parse_dtc_hex([("C1", "89")])  # 0xC1 >> 6 == 3 → 'U'
    ['U0189']
    >>> _parse_dtc_hex([("00", "00")])  # padding
    []
    """

    letter_table = ("P", "C", "B", "U")
    decoded: list[str] = []
    for raw1, raw2 in hex_pairs:
        b1 = int(raw1, 16)
        b2 = int(raw2, 16)
        if b1 == 0 and b2 == 0:
            # Zero-padding byte pair — skip.
            continue
        letter = letter_table[(b1 >> 6) & 0b11]
        # Lower 14 bits: top 6 come from bits 0-5 of byte1; bottom 8
        # come from byte2. We render the 14 bits as 4 hex digits by
        # taking the low nibble of byte1 (top 4) + all of byte2 (low 8),
        # then prefixing with the middle nibble (bits 4-5 of byte1).
        top_two_bits = (b1 >> 4) & 0b11  # middle 2 bits of the 14
        remaining = ((b1 & 0x0F) << 8) | b2  # lower 12 bits
        code = f"{letter}{top_two_bits:X}{remaining:03X}"
        decoded.append(code)
    return decoded


def _is_elm_error(response: str) -> Optional[str]:
    """Return the matching ELM error token, or ``None`` if clean.

    Matching is case-insensitive and substring-based because the chip
    occasionally prefixes error lines with stray CR/LF or the original
    command echo. ``?`` is only matched as a standalone word (not as
    a random question mark inside a hex response, which shouldn't
    occur — hex responses are [0-9A-F ] only — but we're defensive).
    """

    upper = response.upper().strip()
    if not upper:
        return None
    for token in _ELM_ERROR_TOKENS:
        if token == "?":
            # '?' means "don't understand that command" — appears alone.
            if upper == "?" or upper.endswith("\r?") or upper.endswith(" ?"):
                return token
            continue
        if token in upper:
            return token
    return None


def _strip_noise(response: str) -> str:
    """Remove ELM327 informational tokens (``SEARCHING...`` et al)."""

    cleaned = response
    for token in _ELM_NOISE_TOKENS:
        cleaned = cleaned.replace(token, "")
    # Collapse any multi-blank-line artefacts from the removal.
    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    return "\n".join(lines)


def _strip_multiframe_prefixes(response: str) -> str:
    """Join ISO 15765-2 multi-frame lines into one hex blob.

    Lines that look like ``0:``, ``1:``, ..., ``9:`` are CAN multi-
    frame continuation markers. We drop the marker and concatenate
    the payload.
    """

    out_parts: list[str] = []
    for line in response.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Look for a leading "<digit>:" marker.
        if len(stripped) >= 2 and stripped[0].isdigit() and stripped[1] == ":":
            out_parts.append(stripped[2:].strip())
        else:
            out_parts.append(stripped)
    return " ".join(out_parts)


# -- Adapter ----------------------------------------------------------------


class ELM327Adapter(ProtocolAdapter):
    """ELM327 AT-command adapter over a serial/Bluetooth transport.

    Construct with the port string and (optionally) a custom baud rate
    or timeout. Call :meth:`connect` to run the init sequence, then
    use the high-level reads (:meth:`read_dtcs`, :meth:`clear_dtcs`,
    :meth:`read_pid`, :meth:`read_vin`) or the low-level
    :meth:`send_command` escape hatch.

    Parameters
    ----------
    port:
        Serial device path. Windows: ``"COM5"``. Linux USB:
        ``"/dev/ttyUSB0"``. Linux Bluetooth-SPP: ``"/dev/rfcomm0"``.
    baud:
        Initial baud rate. 38400 matches ELM327 v1.5 factory default.
    timeout:
        Per-read timeout in seconds for normal commands.
    protocol:
        ``ATSP`` protocol number. ``"0"`` = auto (recommended — ELM
        probes every supported bus). ``"6"`` = ISO 15765-4 CAN 11/500
        (fastest direct-lock for modern motorcycles).
    """

    def __init__(
        self,
        port: str,
        baud: int = DEFAULT_BAUD,
        timeout: float = DEFAULT_TIMEOUT_S,
        protocol: str = "0",
    ) -> None:
        self._port = port
        self._baud = baud
        self._timeout = timeout
        self._protocol = protocol
        # Populated by connect(); typed loosely to avoid a hard
        # dependency on pyserial at import time.
        self._serial = None  # type: ignore[assignment]
        self._is_connected = False
        self._device_description: Optional[str] = None

    # -- ProtocolAdapter contract ------------------------------------------

    def connect(
        self, port: Optional[str] = None, baud: Optional[int] = None
    ) -> None:
        """Open the serial port and run the ELM327 init sequence.

        The base ABC signature is ``connect(port, baud)``, but
        ELM327Adapter is almost always constructed with the port
        already baked in (Bluetooth dongles bind to a specific COM),
        so both params are optional overrides here. Supplied values
        replace the constructor defaults.

        Idempotent — calling on an already-connected adapter is a
        no-op. Raises :class:`ProtocolConnectionError` on handshake
        failure and leaves the adapter disconnected.
        """

        if self._is_connected:
            return

        if port is not None:
            self._port = port
        if baud is not None:
            self._baud = baud

        try:
            serial_mod = _get_serial_module()
        except ImportError as exc:
            raise ProtocolError(
                "pyserial is not installed. Install with: "
                "pip install 'motodiag[hardware]'"
            ) from exc

        serial_exc = getattr(serial_mod, "SerialException", Exception)

        try:
            self._serial = serial_mod.Serial(
                self._port, self._baud, timeout=self._timeout
            )
        except serial_exc as exc:
            raise ProtocolConnectionError(
                f"Failed to open serial port {self._port!r}: {exc}"
            ) from exc

        # Run the init sequence. If anything fails, close the port
        # before re-raising so we don't leak an open handle.
        try:
            # Use the internal _send (returns str) for the handshake;
            # send_command's bytes contract is for external callers.
            banner = self._send("ATZ", timeout=SLOW_CMD_TIMEOUT_S)
            self._device_description = banner.strip() or "ELM327"

            for at_cmd in ("ATE0", "ATL0", "ATS0", "ATH0"):
                self._expect_ok(at_cmd)

            # ATSP can take longer if the chip probes buses.
            self._expect_ok(f"ATSP{self._protocol}", timeout=SLOW_CMD_TIMEOUT_S)
        except Exception:
            # Clean up the half-open port and rethrow.
            try:
                self._serial.close()
            except Exception:  # pragma: no cover — defensive
                pass
            self._serial = None
            self._is_connected = False
            raise

        self._is_connected = True
        logger.info(
            "ELM327 connected on %s (%s)",
            self._port,
            self._device_description,
        )

    def disconnect(self) -> None:
        """Close the serial port. Must not raise."""

        if self._serial is not None:
            # Best-effort protocol close so we don't strand the ECU.
            try:
                if getattr(self._serial, "is_open", True):
                    self._serial.write(b"ATPC" + ELM_LINE_END)
            except Exception:  # pragma: no cover — best-effort
                pass
            try:
                self._serial.close()
            except Exception:  # pragma: no cover — best-effort
                pass
        self._serial = None
        self._is_connected = False

    def send_command(
        self,
        cmd,  # bytes | str — accept either for ergonomics
        timeout: Optional[float] = None,
    ) -> bytes:
        """Send a single AT/OBD command and return the cleaned reply.

        The base ABC declares ``send_command(cmd: bytes) -> bytes``.
        We accept ``str`` too so the ELM327-internal init sequence
        can use readable literals (``"ATZ"`` is far easier on the eye
        than ``b"ATZ"``). The return type remains ``bytes`` per the
        contract, but most internal callers immediately decode it —
        the :meth:`_send` helper returns ``str`` for that reason.
        """

        reply = self._send(cmd, timeout=timeout)
        return reply.encode("ascii", errors="replace")

    def read_dtcs(self) -> list[str]:
        """Execute Mode 03 and return stored DTC codes.

        Returns an empty list on ``NO DATA`` (= no stored faults).
        Caller-visible ``NO DATA`` is suppressed specifically for
        this method because it's a benign status, not an error.
        """

        try:
            reply = self._send("03")
        except ProtocolError as exc:
            # Only 'NO DATA' is benign on a DTC read.
            if "NO DATA" in str(exc).upper():
                return []
            raise

        flattened = _strip_multiframe_prefixes(reply)
        tokens = [t.upper() for t in flattened.split()]

        # ISO-TP multi-frame responses can carry a leading payload-size
        # header token (e.g. '009' meaning 9 payload bytes) before the
        # ``43`` service echo. Scan forward until we hit the service
        # echo so we tolerate both framings.
        try:
            start = tokens.index("43")
        except ValueError:
            raise ProtocolError(
                f"Unexpected Mode 03 response (missing 0x43 prefix): {reply!r}"
            ) from None

        # Drop the service echo. Some ECUs insert a count byte next; we
        # don't rely on it — we just decode every 2-byte pair we see.
        payload = tokens[start + 1 :]
        if len(payload) % 2 != 0:
            # Odd byte count — treat the first payload byte as a count
            # field and skip it.
            payload = payload[1:]
        pairs = [(payload[i], payload[i + 1]) for i in range(0, len(payload), 2)]
        codes = _parse_dtc_hex(pairs)
        return sorted(set(codes))

    def clear_dtcs(self) -> bool:
        """Execute Mode 04 to clear stored DTCs. Returns True on ACK."""

        try:
            reply = self._send("04")
        except ProtocolError:
            # Any error on a clear is a hard failure — we re-raise
            # rather than return False, because the caller's signal
            # for "ECU refused the clear" is the 7F NACK below, not a
            # serial-level error.
            raise

        upper = reply.upper().strip()
        flattened = _strip_multiframe_prefixes(upper)
        tokens = flattened.split()
        if not tokens:
            raise ProtocolError(f"Empty response to Mode 04 clear: {reply!r}")
        if tokens[0] == "44":
            return True
        # 7F 04 XX is a negative response (ECU refused — e.g. ignition
        # wrong, engine running). Surface as False, not an exception.
        if tokens[0] == "7F" and len(tokens) >= 2 and tokens[1] == "04":
            return False
        raise ProtocolError(
            f"Unexpected Mode 04 response (want '44' or '7F 04'): {reply!r}"
        )

    def read_pid(self, pid: int, mode: int = 1) -> Optional[int]:
        """Execute a Mode 01 (or 02) PID read, return the integer value.

        The base ABC signature is ``read_pid(pid)`` with an implicit
        Mode 01. We add an optional ``mode`` kwarg for freeze-frame
        (Mode 02) reads without breaking the contract. Multi-byte
        payloads are combined big-endian.

        Returns ``None`` if the ECU replies that the PID is not
        supported (``NO DATA`` or ``7F 01 12`` NACK).
        """

        if mode not in (1, 2):
            raise ValueError(f"read_pid: mode must be 1 or 2 (got {mode})")
        if not 0 <= pid <= 0xFF:
            raise ValueError(f"read_pid: pid out of range 0-0xFF (got {pid})")

        cmd = f"{mode:02X}{pid:02X}"
        try:
            reply = self._send(cmd)
        except ProtocolError as exc:
            if "NO DATA" in str(exc).upper():
                return None
            raise

        flattened = _strip_multiframe_prefixes(reply)
        tokens = [t.upper() for t in flattened.split()]
        expected_prefix = f"{mode + 0x40:02X}"
        expected_pid = f"{pid:02X}"

        # 7F {mode} XX is a negative response → unsupported PID.
        # Scan for it rather than anchoring at index 0 so a leading
        # multi-frame size header doesn't mask the NACK.
        if "7F" in tokens:
            nack_start = tokens.index("7F")
            if tokens[nack_start : nack_start + 2] == ["7F", f"{mode:02X}"]:
                return None

        # Scan for the service-echo prefix — tolerates a leading size
        # header from ISO-TP multi-frame responses.
        start = -1
        for i in range(len(tokens) - 1):
            if tokens[i] == expected_prefix and tokens[i + 1] == expected_pid:
                start = i
                break
        if start == -1:
            raise ProtocolError(
                f"Unexpected PID read response (want {expected_prefix} "
                f"{expected_pid}): {reply!r}"
            )

        payload_hex = tokens[start + 2 :]
        if not payload_hex:
            return None
        value = 0
        for hx in payload_hex:
            value = (value << 8) | int(hx, 16)
        return value

    def read_vin(self) -> Optional[str]:
        """Execute Mode 09 PID 02 and return the 17-char VIN.

        Decodes the ISO 15765-2 multi-frame response by stripping the
        ``49 02 01`` service/PID/message-count prefix from each frame,
        concatenating the remaining payload bytes, and ASCII-decoding.
        VIN must be exactly 17 printable-ASCII characters after the
        decode — anything shorter raises :class:`ProtocolError`.
        """

        try:
            reply = self._send("0902")
        except ProtocolError as exc:
            if "NO DATA" in str(exc).upper():
                return None
            raise

        flattened = _strip_multiframe_prefixes(reply)
        tokens = [t.upper() for t in flattened.split()]

        # Peel off every occurrence of the 49 02 01 prefix. Real ELM
        # responses interleave the prefix once per frame for multi-
        # frame VIN replies, so we walk the token stream.
        payload: list[str] = []
        i = 0
        while i < len(tokens):
            if (
                i + 2 < len(tokens)
                and tokens[i] == "49"
                and tokens[i + 1] == "02"
                and tokens[i + 2] == "01"
            ):
                i += 3
                continue
            payload.append(tokens[i])
            i += 1

        # Decode hex bytes to ASCII, dropping zero-padding.
        chars: list[str] = []
        for hx in payload:
            try:
                b = int(hx, 16)
            except ValueError:
                # Non-hex garbage line — skip silently.
                continue
            if b == 0:
                continue
            # Keep only printable ASCII.
            if 0x20 <= b < 0x7F:
                chars.append(chr(b))

        vin = "".join(chars).strip().upper()
        if len(vin) < 17:
            raise ProtocolError(
                f"VIN response shorter than 17 chars (got {len(vin)}): {vin!r}"
            )
        return vin[:17]

    def get_protocol_name(self) -> str:
        """Return a stable, human-readable protocol identifier."""

        # Protocol number → ELM327 datasheet label. Kept here (not in
        # a module-level dict) because it's only used by this method
        # and clarity-at-point-of-use > DRY for a 9-entry lookup.
        names = {
            "0": "ELM327 (auto)",
            "1": "SAE J1850 PWM",
            "2": "SAE J1850 VPW",
            "3": "ISO 9141-2",
            "4": "ISO 14230-4 KWP (5-baud init)",
            "5": "ISO 14230-4 KWP (fast init)",
            "6": "ISO 15765-4 CAN 11/500",
            "7": "ISO 15765-4 CAN 29/500",
            "8": "ISO 15765-4 CAN 11/250",
            "9": "ISO 15765-4 CAN 29/250",
            "A": "SAE J1939 CAN",
        }
        return names.get(self._protocol.upper(), f"ELM327 protocol {self._protocol}")

    # -- Internals ---------------------------------------------------------

    def _send(self, cmd, timeout: Optional[float] = None) -> str:
        """Low-level command dispatch returning a ``str`` reply.

        Centralises four concerns:

        1. Guarding "must be connected" (except for the init sequence,
           which sets ``_serial`` before ``_is_connected`` flips).
        2. Writing the command + CR to the wire.
        3. Reading until the ``>`` prompt or the time budget expires.
        4. Stripping command echo / noise / error tokens.
        """

        if self._serial is None:
            raise ProtocolConnectionError(
                "ELM327 adapter is not connected — call connect() first"
            )

        if isinstance(cmd, bytes):
            cmd_str = cmd.decode("ascii", errors="replace")
        else:
            cmd_str = cmd

        budget = timeout if timeout is not None else self._timeout

        # Drain any stale bytes left over from a prior aborted read.
        try:
            if hasattr(self._serial, "reset_input_buffer"):
                self._serial.reset_input_buffer()
        except Exception:  # pragma: no cover — best effort
            pass

        to_write = cmd_str.encode("ascii", errors="replace") + ELM_LINE_END
        self._serial.write(to_write)

        raw = self._read_until_prompt(budget)
        text = raw.decode("ascii", errors="replace")

        # Strip the trailing prompt + CRs, drop the command echo
        # (defensive — ATE0 should suppress it but clones sometimes
        # disagree).
        text = text.replace("\r", "\n")
        # Remove the leading echoed command if present.
        if text.lstrip().upper().startswith(cmd_str.upper()):
            first_nl = text.find("\n")
            if first_nl != -1:
                text = text[first_nl + 1 :]
        # Drop the trailing '>' prompt.
        text = text.rstrip(">").rstrip()
        text = _strip_noise(text)

        # Raise on real error tokens.
        err = _is_elm_error(text)
        if err is not None:
            raise ProtocolError(f"ELM returned {err!r} in response to {cmd_str!r}")

        return text

    def _read_until_prompt(self, timeout: float) -> bytes:
        """Read bytes one at a time until ``>`` or the budget expires."""

        deadline = time.monotonic() + timeout
        buf = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProtocolTimeoutError(
                    f"Timed out after {timeout:.2f}s waiting for ELM prompt"
                )
            chunk = self._serial.read(1)
            if not chunk:
                # Empty read — either serial-level timeout or the
                # mock's "nothing queued" signal. Loop and let the
                # wall-clock budget decide.
                if time.monotonic() >= deadline:
                    raise ProtocolTimeoutError(
                        f"Timed out after {timeout:.2f}s waiting for ELM prompt"
                    )
                continue
            buf.extend(chunk)
            if chunk == ELM_PROMPT:
                return bytes(buf)

    def _expect_ok(self, at_cmd: str, timeout: Optional[float] = None) -> None:
        """Send an AT command and assert the reply is ``OK``."""

        reply = self._send(at_cmd, timeout=timeout)
        if "OK" not in reply.upper():
            raise ProtocolConnectionError(
                f"ELM327 init: {at_cmd} returned {reply!r} (expected 'OK')"
            )
