"""The network guard: no test reaches the network (Phase 281).

The guard is installed by tests/conftest.py. These tests prove it refuses a
public host, lets loopback through, and fails a planted test that makes a
real outbound request, run in a pytest subprocess with only the guard loaded.

Every host named here is reserved (`.invalid`, RFC 2606; 192.0.2.0/24,
RFC 5737), so a broken guard, as a mutation run makes it, still cannot
reach a real service.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import textwrap
import urllib.request
from pathlib import Path

import pytest

from support import network_guard
from support.network_guard import NetworkBlockedInTests

TESTS_DIR = Path(__file__).parent


def test_the_guard_is_installed_in_this_session():
    assert socket.getaddrinfo is network_guard._guarded_getaddrinfo
    assert socket.socket.connect is network_guard._guarded_connect


def test_a_public_name_lookup_is_refused():
    with pytest.raises(NetworkBlockedInTests, match="recall-service.invalid"):
        socket.getaddrinfo("recall-service.invalid", 443)


def test_a_connection_to_a_public_address_is_refused():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(NetworkBlockedInTests, match="192.0.2.1"):
            s.connect(("192.0.2.1", 443))
    finally:
        s.close()


def test_urlopen_of_a_public_host_fails_loudly():
    with pytest.raises(NetworkBlockedInTests):
        urllib.request.urlopen("https://rates-service.invalid/", timeout=1)


def test_loopback_is_allowed():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect(server.getsockname())
        conn, _ = server.accept()
        conn.close()
    finally:
        client.close()
        server.close()


PLANTED_BAD = textwrap.dedent('''
    import urllib.request

    def test_planted_reaches_a_live_endpoint():
        urllib.request.urlopen(
            "https://recall-service.invalid/recalls/recallsByVehicle"
            "?make=PIAGGIO&model=MP3%20500&modelYear=2020", timeout=5)
''')

PLANTED_LOOPBACK = textwrap.dedent('''
    import socket

    def test_planted_loopback_only():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(server.getsockname())
        client.close()
        server.close()
''')


def _run_planted(tmp_path: Path, body: str) -> subprocess.CompletedProcess:
    test_file = tmp_path / "test_planted.py"
    test_file.write_text(body)
    env = {"PYTHONPATH": str(TESTS_DIR), "PATH": "/usr/bin:/bin"}
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:xdist", "-p", "support.network_guard",
         "-p", "no:cacheprovider", "-o", "addopts=", str(test_file)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
    )


def test_the_planted_known_bad_test_is_caught(tmp_path):
    res = _run_planted(tmp_path, PLANTED_BAD)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "NetworkBlockedInTests" in res.stdout
    assert "recall-service.invalid" in res.stdout
    assert "1 failed" in res.stdout


def test_the_planted_loopback_control_passes(tmp_path):
    res = _run_planted(tmp_path, PLANTED_LOOPBACK)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "1 passed" in res.stdout
