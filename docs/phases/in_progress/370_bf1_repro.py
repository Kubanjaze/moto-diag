"""Phase 370 bug fix #1: the 429 test fails when a minute ticks over mid-test.

The regression of record at 7ed0159 failed one test:
test_phase176_auth_billing.py::TestRateLimitMiddleware::test_anon_over_limit_returns_429,
at line 786, a 404 where a 429 was expected. The limiter counts per
wall-clock minute (auth/rate_limiter.py: ``minute_start = int(now // 60) * 60``)
and ``create_app`` builds it on the real clock. The test sends three
requests; if a minute starts between the second and the third, the count
resets and the third is not limited.

This puts the limiter's default clock (``time.time``, bound when the limiter
is built) on a minute boundary: the first two requests at :59.0 and :59.5,
every later call at :00.5 of the next minute. It runs the test under that
clock and prints pytest's summary line.

Run: .venv/bin/python docs/phases/in_progress/370_bf1_repro.py
Before the fix it must fail; after it, pass.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TEST = ("tests/test_phase176_auth_billing.py::TestRateLimitMiddleware::"
        "test_anon_over_limit_returns_429")
BOUNDARY = 1_700_000_040.0          # divisible by 60: a minute starts here


class _MinuteRollover:
    """time.time() at :59.0, :59.5, then :00.5 of the next minute, held."""

    def __init__(self) -> None:
        self._values = [BOUNDARY - 1.0, BOUNDARY - 0.5]

    def time(self) -> float:
        return self._values.pop(0) if self._values else BOUNDARY + 0.5

    def __getattr__(self, name):  # anything else the module asks of `time`
        import time
        return getattr(time, name)


def pytest_configure(config) -> None:
    import motodiag.auth.rate_limiter as rate_limiter

    rate_limiter.time = _MinuteRollover()


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "pytest", TEST, "-q", "-p", "no:cacheprovider",
         "-p", "no:xdist", "-p", "370_bf1_repro"],
        cwd=ROOT, capture_output=True, text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(pathlib.Path(__file__).parent)},
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    for line in lines:
        if line.startswith(("E ", "tests/", "FAILED")) or "passed" in line or "failed" in line:
            print(line)
    print(f"exit {result.returncode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
