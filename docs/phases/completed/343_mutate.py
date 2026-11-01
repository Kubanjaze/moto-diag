"""Phase 343's mutations: each breaks one promise, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/343_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 345's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__` under `src/`, every file restored whatever happens. A run
that outlives its limit counts as red (a blocking `put` hangs the queue
test rather than failing it). Exits 1 if any mutation stays green. An
argument runs only the mutations whose name starts with it.

No mutation reads live or opens a socket beyond loopback.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

T = "src/motodiag/telemetry/"
DSN, EVENTS, ENVELOPE, SENDER = (T + "dsn.py", T + "events.py", T + "envelope.py",
                                 T + "sender.py")
API, ERRORS, MAIN = ("src/motodiag/api/telemetry.py", "src/motodiag/api/errors.py",
                     "src/motodiag/cli/main.py")
LIMIT_S = 180


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_DSN = pytest("tests/test_phase343_dsn.py")
T_EVENTS = pytest("tests/test_phase343_events.py")
T_SENDER = pytest("tests/test_phase343_sender.py")
T_API = pytest("tests/test_phase343_api.py")

MUTATIONS = [
    ("M1 redact made the identity",
     [(EVENTS, "    out = SESSION_TOKEN_RE.sub(TOKEN_REDACTED, text)\n",
       "    return text\n    out = text\n")], T_EVENTS),
    ("M2 the actual path sent in place of the route template",
     [(API, '    return getattr(route, "path_format", None) or UNMATCHED',
       "    return request.url.path")], T_API),
    ("M3 the comparison in sampled() inverted",
     [(SENDER, "return self._rng() < self.traces_sample_rate",
       "return self._rng() >= self.traces_sample_rate")], T_SENDER),
    ("M4 put_nowait replaced by a blocking put",
     [(SENDER, "self._queue.put_nowait(event)", "self._queue.put(event)")], T_SENDER),
    ("M5 the capture removed from _unhandled_handler",
     [(ERRORS, "    capture_crash(request, exc)\n", "    pass\n")], T_API),
    ("M6 the mapped-error handler (the 404) capturing",
     [(ERRORS, "    async def handler(request: Request, exc: Exception):\n"
               "        return _problem_response(",
       "    async def handler(request: Request, exc: Exception):\n"
       "        from motodiag.api.telemetry import capture_crash\n"
       "        capture_crash(request, exc)\n"
       "        return _problem_response(")], T_API),
    ("M7 the key printed by Dsn.__repr__",
     [(DSN, 'return f"Dsn(host={self.netloc!r}, project_id={self.project_id!r})"',
       'return f"Dsn(host={self.netloc!r}, key={self.public_key!r})"')], T_DSN),
    ("M8 the item header's length off by one",
     [(ENVELOPE, '"length": len(payload)}', '"length": len(payload) + 1}')], T_SENDER),
    ("M9 /healthz no longer skipped",
     [(API, 'SKIPPED_PATHS = frozenset({"/healthz"})',
       "SKIPPED_PATHS: frozenset[str] = frozenset()")], T_API),
    ("M10 OPTIONS no longer skipped",
     [(API, 'return request.method == "OPTIONS" or request.url.path in SKIPPED_PATHS',
       "return request.url.path in SKIPPED_PATHS")], T_API),
    ("M11 the catch-and-re-raise removed from TelemetryMiddleware",
     [(API, "        try:\n"
            "            response: Response = await call_next(request)\n"
            "        except Exception:\n"
            "            _time(request, sender, 500, wall, start)\n"
            "            raise\n",
       "        response: Response = await call_next(request)\n")], T_API),
    ("M12 the middleware closing over the sender at install",
     [(API, "        sender = _sender(request)\n        if sender is None or skipped(request):",
       "        sender = self.installed if self.installed.enabled else None\n"
       "        if sender is None or skipped(request):"),
      (API, "    app.add_middleware(TelemetryMiddleware)\n",
       "    app.add_middleware(TelemetryMiddleware)\n"
       "    TelemetryMiddleware.installed = sender\n")], T_API),
    ("M13 sentry_dsn dropped from the config show mask",
     [(MAIN, 'SECRET_SETTING_NAMES = ("api_key", "sentry_dsn")',
       'SECRET_SETTING_NAMES = ("api_key",)')], T_DSN),
]


def clear_caches() -> None:
    for d in (ROOT / "src").rglob("__pycache__"):
        for f in d.glob("*.pyc"):
            f.unlink()


def run(command: list[str]) -> int:
    clear_caches()
    try:
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                              timeout=LIMIT_S).returncode
    except subprocess.TimeoutExpired:
        return 124


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals: dict[str, str] = {}
        try:
            for rel, old, new in edits:
                path = ROOT / rel
                originals.setdefault(rel, path.read_text())
                current = path.read_text()
                assert current.count(old) == 1, \
                    f"{name}: the text occurs {current.count(old)} times in {rel}"
                path.write_text(current.replace(old, new))
            code = run(command)
        finally:
            for rel, text in originals.items():
                (ROOT / rel).write_text(text)
        verdict = ("red (timed out)" if code == 124 else "red") if code != 0 \
            else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
