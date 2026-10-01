"""No test reaches the network.

Phase 281 added the app's first calls to public data services (NHTSA's
recall service, NHTSA vPIC, the ECB's reference rates). The operator's rule
for them: tests use recorded fixtures, never a live endpoint. This guard
makes that a failure instead of a convention. `tests/conftest.py` calls
`install()` at import time, so it covers collection and every fixture.

Refused: a socket connection or a name lookup to anything that is not
loopback (127.0.0.0/8, ::1, "localhost") or a Unix socket. The refusal
raises `NetworkBlockedInTests`, naming the host, which fails the test.
"""

from __future__ import annotations

import ipaddress
import socket

_LOOPBACK_NAMES = frozenset({"localhost", "localhost.localdomain", "", None})

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_getaddrinfo = socket.getaddrinfo
_real_create_connection = socket.create_connection


class NetworkBlockedInTests(RuntimeError):
    """A test tried to reach a host that is not this machine."""


def _is_loopback(host) -> bool:
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if host in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def _refuse(host) -> None:
    raise NetworkBlockedInTests(
        f"network access refused in tests: {host!r}. Tests use recorded "
        f"fixtures, never a live endpoint (tests/support/network_guard.py)."
    )


def _check_address(sock, address) -> None:
    if getattr(socket, "AF_UNIX", None) is not None and sock.family == socket.AF_UNIX:
        return
    host = address[0] if isinstance(address, tuple) else address
    if not _is_loopback(host):
        _refuse(host)


def _guarded_connect(self, address):
    _check_address(self, address)
    return _real_connect(self, address)


def _guarded_connect_ex(self, address):
    _check_address(self, address)
    return _real_connect_ex(self, address)


def _guarded_getaddrinfo(host, *args, **kwargs):
    if not _is_loopback(host):
        _refuse(host)
    return _real_getaddrinfo(host, *args, **kwargs)


def _guarded_create_connection(address, *args, **kwargs):
    if not _is_loopback(address[0]):
        _refuse(address[0])
    return _real_create_connection(address, *args, **kwargs)


def install() -> None:
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    socket.getaddrinfo = _guarded_getaddrinfo
    socket.create_connection = _guarded_create_connection


def pytest_configure(config) -> None:
    """Lets `pytest -p support.network_guard` install the guard on its own."""
    install()
