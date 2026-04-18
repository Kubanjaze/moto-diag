"""Mock OBD protocol adapter for the ``--mock`` CLI flag + Phase 140 tests.

Not for production — substrate for the ``motodiag hardware <cmd> --mock``
CLI flag and the Phase 144 hardware simulator that will extend this
class with scripted-fault scenarios, timing jitter, and protocol-layer
noise.

:class:`MockAdapter` is a **real concrete subclass** of
:class:`~motodiag.hardware.protocols.base.ProtocolAdapter`. Using a real
class (not a :class:`unittest.mock.MagicMock`) is a deliberate test
strategy: if the ABC contract ever grows a new abstract method, the
interpreter refuses to instantiate :class:`MockAdapter` and every test
that touches it fails loudly. A :class:`~unittest.mock.MagicMock` would
silently accept the call and mask the drift.

Typical usage
-------------

Default happy-path state — 2 stored DTCs, a realistic Harley VIN, and
Mode 01/03/04/09 support::

    adapter = MockAdapter()
    adapter.connect(port="COM3", baud=38400)
    assert adapter.read_dtcs() == ["P0115", "P0300"]
    adapter.disconnect()

Scripted scenarios for edge-case testing::

    # ECU that refuses to clear faults:
    MockAdapter(clear_returns=False)

    # Pre-OBD-II ECU that can't report VIN:
    MockAdapter(vin_unsupported=True)

    # Adapter whose connect() handshake fails:
    MockAdapter(fail_on_connect=True)

    # Empty DTC list (clean bike):
    MockAdapter(dtcs=[])

    # Phase 141 — scripted Mode 01 PID responses for the live sensor
    # streamer test suite. When ``pid_values`` is set, ``read_pid``
    # routes through the mapping instead of the legacy ``pid * 10``
    # path — an unknown key returns ``None`` so the streamer sees the
    # same "PID not supported" contract it would get from a real ECU.
    MockAdapter(pid_values={0x0C: 0x1AF8, 0x05: 0x5A})
"""

from __future__ import annotations

from typing import Dict, List, Optional

from motodiag.hardware.protocols.base import ProtocolAdapter
from motodiag.hardware.protocols.exceptions import (
    ConnectionError,
    UnsupportedCommandError,
)


# Default happy-path state. Chosen to mirror a realistic 2011+ Harley
# with a coolant-sensor fault (P0115) and a random misfire (P0300) —
# codes that already live in the Phase 7/111 seed DB so the scan CLI's
# enrichment pipeline can be exercised end-to-end by a ``--mock`` run
# without any special test-DB seeding.
_DEFAULT_DTCS: tuple[str, ...] = ("P0115", "P0300")
_DEFAULT_VIN: str = "1HD1KHM19NB123456"
_DEFAULT_ECU_PART: str = "HD-ECM-1234"
_DEFAULT_SW_VERSION: str = "1.0.5"
_DEFAULT_SUPPORTED_MODES: tuple[int, ...] = (1, 3, 4, 9)
_DEFAULT_PROTOCOL_NAME: str = "Mock Protocol"


class MockAdapter(ProtocolAdapter):
    """In-memory :class:`ProtocolAdapter` with fully scripted behavior.

    Parameters
    ----------
    dtcs:
        Initial list of stored DTCs. Defaults to a realistic pair
        (``["P0115", "P0300"]``). Pass ``[]`` for a clean bike.
    vin:
        VIN returned by :meth:`read_vin`. Defaults to a valid 17-char
        Harley-Davidson VIN. Pass ``None`` to simulate an ECU that
        doesn't report VIN.
    ecu_part:
        ECU part number / calibration ID. Defaults to ``"HD-ECM-1234"``.
    sw_version:
        ECU software version string. Defaults to ``"1.0.5"``.
    supported_modes:
        OBD-II modes this mock advertises as supported. Defaults to
        ``[1, 3, 4, 9]`` — the standard subset a Phase 140 ``info``
        command expects.
    clear_returns:
        Return value from :meth:`clear_dtcs`. ``True`` simulates an ECU
        that accepts the clear; ``False`` simulates an ECU that refuses
        (typically because ignition is on / engine running).
    protocol_name:
        String returned from :meth:`get_protocol_name`. Defaults to
        ``"Mock Protocol"`` — callers that want to mimic a specific
        real protocol can set this to e.g. ``"ISO 15765-4 (CAN 11/500)"``.
    fail_on_connect:
        When ``True``, :meth:`connect` raises :class:`ConnectionError`
        on the first attempt. Used to exercise the Phase 140 "no ECU
        detected" CLI error panel.
    vin_unsupported:
        When ``True``, :meth:`read_vin` raises
        :class:`UnsupportedCommandError` instead of returning the VIN.
        Used to exercise the Phase 140 "VIN: not available" CLI path.
    pid_values:
        **Phase 141 addition.** When provided, :meth:`read_pid`
        consults this mapping instead of the legacy Phase 140
        ``pid * 10`` / ``None`` rule: a hit returns the mapped raw
        integer (pre-assembled per the ABC contract), a miss returns
        ``None``. A defensive copy is stored at construction so the
        caller's dict is not shared with internal state. Pass ``None``
        (default) to preserve Phase 140 behavior exactly — every Phase
        140 test still passes because the new branch is gated on
        ``self._pid_values is not None``.
    """

    def __init__(
        self,
        dtcs: Optional[List[str]] = None,
        vin: Optional[str] = _DEFAULT_VIN,
        ecu_part: Optional[str] = _DEFAULT_ECU_PART,
        sw_version: Optional[str] = _DEFAULT_SW_VERSION,
        supported_modes: Optional[List[int]] = None,
        clear_returns: bool = True,
        protocol_name: str = _DEFAULT_PROTOCOL_NAME,
        fail_on_connect: bool = False,
        vin_unsupported: bool = False,
        pid_values: Optional[Dict[int, int]] = None,
    ) -> None:
        # Defensive copy of the DTC list so callers can't mutate our
        # state after construction by modifying their own list.
        self._dtcs: list[str] = (
            list(dtcs) if dtcs is not None else list(_DEFAULT_DTCS)
        )
        self._vin: Optional[str] = vin
        self._ecu_part: Optional[str] = ecu_part
        self._sw_version: Optional[str] = sw_version
        self._supported_modes: list[int] = (
            list(supported_modes)
            if supported_modes is not None
            else list(_DEFAULT_SUPPORTED_MODES)
        )
        self._clear_returns: bool = clear_returns
        self._protocol_name: str = protocol_name
        self._fail_on_connect: bool = fail_on_connect
        self._vin_unsupported: bool = vin_unsupported
        # Phase 141 — scripted Mode 01 PID table. Defensive copy so
        # callers can't mutate our state by editing their own dict
        # after construction. ``None`` preserves Phase 140 behavior.
        self._pid_values: Optional[Dict[int, int]] = (
            dict(pid_values) if pid_values is not None else None
        )
        # ``_is_connected`` is the backing attribute the base class's
        # ``is_connected`` property reads. Starts False; flipped by
        # connect()/disconnect().
        self._is_connected: bool = False

    # --- ProtocolAdapter contract --------------------------------------

    def connect(self, port: str = "", baud: int = 0) -> None:
        """Bring the mock to a ready state. Idempotent.

        Parameters are accepted for ABC-signature compatibility but
        ignored — the mock has no real transport.

        Raises
        ------
        ConnectionError
            When the adapter was constructed with
            ``fail_on_connect=True``. Used to exercise the CLI's
            "no ECU detected" path.
        """
        if self._fail_on_connect:
            raise ConnectionError("mock refused connect")
        # Idempotent — re-connecting an already-connected mock is a no-op,
        # matching the ABC contract.
        self._is_connected = True

    def disconnect(self) -> None:
        """Close the mock. Never raises. Idempotent."""
        # No real resource to release; we just flip the flag. Matches
        # the ABC's "must not raise" contract.
        self._is_connected = False

    def send_command(self, cmd: bytes) -> bytes:
        """Accept a raw command, return empty bytes.

        Raises
        ------
        ConnectionError
            If called on a disconnected adapter — mirrors the real
            wire-protocol contract so CLI paths that accidentally skip
            ``connect()`` fail the same way they would on hardware.
        """
        if not self._is_connected:
            raise ConnectionError("mock adapter not connected")
        # No wire protocol to simulate at this level. Phase 144 will
        # extend this to return scripted response bytes.
        return b""

    def read_dtcs(self) -> List[str]:
        """Return a copy of the stored DTC list.

        Copy (not reference) so a caller that clears the returned list
        in-place doesn't silently empty our internal state.
        """
        return list(self._dtcs)

    def clear_dtcs(self) -> bool:
        """Empty the stored DTC list, return the configured success flag."""
        self._dtcs = []
        return self._clear_returns

    def read_pid(self, pid: int) -> Optional[int]:
        """Return a deterministic fake PID value.

        Phase 141: when the mock was constructed with a ``pid_values``
        mapping, this method consults that table and returns the mapped
        value (or ``None`` on miss) — ignoring ``supported_modes``
        entirely. This lets the live-sensor streamer tests build
        fixtures like ``MockAdapter(pid_values={0x0C: 0x1AF8})`` that
        read as scripted wire captures.

        Otherwise (Phase 140 behavior, preserved unchanged): when
        ``pid`` is in the supported-modes list the mock returns
        ``pid * 10`` — arbitrary but reproducible across test runs —
        and returns ``None`` for anything outside that set. ``None``
        matches the ABC contract for "PID not supported".
        """
        if self._pid_values is not None:
            return self._pid_values.get(pid)
        if pid in self._supported_modes:
            return pid * 10
        return None

    def read_vin(self) -> Optional[str]:
        """Return the stored VIN, or raise if the mock is VIN-unsupported.

        Raises
        ------
        UnsupportedCommandError
            When the adapter was constructed with
            ``vin_unsupported=True``. Used to simulate protocols that
            physically cannot carry VIN data (early J1850 VPW).
        """
        if self._vin_unsupported:
            raise UnsupportedCommandError("read_vin")
        return self._vin

    def get_protocol_name(self) -> str:
        """Return the configured human-readable protocol label."""
        return self._protocol_name

    # --- Phase 140 helpers --------------------------------------------

    def identify_info(self) -> dict:
        """Best-effort snapshot of the mock's identity state.

        Matches the shape :class:`~motodiag.hardware.connection.HardwareSession`
        surfaces from its ``identify_ecu()`` helper — the ``--mock``
        path bypasses ``AutoDetector.identify_ecu`` entirely and reads
        this instead. VIN lookup is wrapped so a
        ``vin_unsupported=True`` mock yields ``None`` rather than
        raising out of an info-command.
        """
        try:
            vin_value = self.read_vin()
        except UnsupportedCommandError:
            vin_value = None
        return {
            "vin": vin_value,
            "ecu_part": self._ecu_part,
            "sw_version": self._sw_version,
            "supported_modes": list(self._supported_modes),
            "protocol_name": self._protocol_name,
        }


__all__ = ["MockAdapter"]
