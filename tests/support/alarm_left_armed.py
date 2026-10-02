"""Phase 369 — no test leaves SIGALRM armed (F183's cause).

The push guard's ``main()`` armed a 345 s alarm whose handler calls
``os._exit(2)``, and an exception from the whole-tree gate skipped the
cancel. A test that ran ``main()`` inside an xdist worker left it armed; 345
s later it ended whichever test that worker had reached, with no traceback,
and xdist reported only "node down: Not properly terminated".

So every test, serial or parallel, fails in teardown if it leaves the
real-time timer armed, and the timer is cancelled there, before it can end
a later test.
"""

from __future__ import annotations

import signal

import pytest


@pytest.hookimpl(wrapper=True)       # after the test's own teardown, never before it
def pytest_runtest_teardown(item: pytest.Item):
    try:
        return (yield)
    finally:
        left, _ = signal.setitimer(signal.ITIMER_REAL, 0)
        if left:
            pytest.fail(f"{item.nodeid} left SIGALRM armed ({left:.0f} s to go). It "
                        "would have fired in a later test in this process; it is "
                        "cancelled now. Cancel an alarm in a `finally` (F183).",
                        pytrace=False)
