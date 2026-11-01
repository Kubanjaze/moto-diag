"""Crash reports and request timings sent to Sentry (Phase 343).

Off unless ``MOTODIAG_SENTRY_DSN`` is set. A small client of Sentry's
envelope protocol in the standard library: ``dsn`` reads the DSN,
``events`` builds what an event may carry, ``envelope`` writes the wire
format and ``sender`` posts it from one background thread per process.
"""

from motodiag.telemetry.dsn import Dsn, DsnError, parse_dsn

__all__ = ["Dsn", "DsnError", "parse_dsn"]
