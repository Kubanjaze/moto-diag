#!/usr/bin/env python3
"""The fence's network: the model API and nothing else.

    fence_net.py proxy SOCKET LOG             outside the fence
    fence_net.py inside PORT SOCKET -- CMD…   inside the fence

The fence runs with no network of its own (`bwrap --unshare-all`). Outside
it, `proxy` listens on a unix socket and answers HTTP `CONNECT` for the
hosts in `ALLOW` only; anything else, including a plain request, gets 403.
One line per request goes to LOG, `ALLOW` or `DENY` and the request line.

Inside it, `inside` binds `127.0.0.1:PORT` before anything else, forwards
each connection there to the socket (bound into the fence by `fence.sh`),
then runs CMD and exits with its code. `HTTPS_PROXY` points CMD at the port.
Claude Code honours it (Phase 388 Step 0, S0-5: a call through the gate
reached the real API; `curl` and `git` to GitHub were refused 403).

Standard library only: it runs under `/usr/bin/python3` inside the fence,
where nothing of the operator's home is mounted.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading

#: The hosts a fenced stage may reach, as (host, port). The model API only.
ALLOW = frozenset({("api.anthropic.com", 443)})


def allowed(request_line: str) -> tuple[str, int] | None:
    """The (host, port) a request line asks to CONNECT to, when allowed."""
    parts = request_line.split()
    if len(parts) != 3 or parts[0] != "CONNECT":
        return None
    host, _, port = parts[1].rpartition(":")
    if not port.isdigit():
        return None
    target = (host.lower(), int(port))
    return target if target in ALLOW else None


def pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while data := src.recv(65536):
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


def splice(a: socket.socket, b: socket.socket) -> None:
    threading.Thread(target=pipe, args=(a, b), daemon=True).start()
    pipe(b, a)


def serve_one(client: socket.socket, log, lock: threading.Lock) -> None:
    with client:
        head = b""
        while b"\r\n\r\n" not in head:
            data = client.recv(4096)
            if not data or len(head) > 16384:
                return
            head += data
        line = head.split(b"\r\n", 1)[0].decode("latin-1")
        target = allowed(line)
        with lock:
            print(f"{'ALLOW' if target else 'DENY'} {line}", file=log, flush=True)
        if target is None:
            client.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            return
        try:
            upstream = socket.create_connection(target, timeout=30)
        except OSError:
            client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            return
        upstream.settimeout(None)
        with upstream:
            client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
            splice(client, upstream)


def proxy(sock_path: str, log_path: str) -> None:
    server = socket.socket(socket.AF_UNIX)
    server.bind(sock_path)
    server.listen(32)
    lock = threading.Lock()
    with open(log_path, "a", encoding="utf-8") as log:
        while True:
            client, _ = server.accept()
            threading.Thread(target=serve_one, args=(client, log, lock), daemon=True).start()


def bridge(listener: socket.socket, sock_path: str) -> None:
    while True:
        client, _ = listener.accept()
        upstream = socket.socket(socket.AF_UNIX)
        try:
            upstream.connect(sock_path)
        except OSError:
            client.close()
            continue
        threading.Thread(target=splice, args=(client, upstream), daemon=True).start()


def inside(port: int, sock_path: str, cmd: list[str]) -> int:
    listener = socket.socket()
    listener.bind(("127.0.0.1", port))
    listener.listen(32)
    threading.Thread(target=bridge, args=(listener, sock_path), daemon=True).start()
    # The token's pipe (Phase 389): handed on to claude, which reads it once.
    fd = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR")
    return subprocess.run(cmd, pass_fds=(int(fd),) if fd else ()).returncode


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[0] == "proxy":
        proxy(argv[1], argv[2])
        return 0
    if len(argv) >= 5 and argv[0] == "inside" and argv[3] == "--":
        return inside(int(argv[1]), argv[2], argv[4:])
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
