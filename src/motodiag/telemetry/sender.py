"""The sender: a bounded queue and one thread that posts envelopes
(Phase 343).

A capture never blocks and never raises: a full queue, or a pause after a
429, drops the event and counts it. A failed send is logged at WARNING at
most once a minute, naming the status and the host, never the key. The
numbers are the operator's (2026-11-01): a queue of 100 events, a
5-second transport timeout, a 2-second flush at process exit.
"""

from __future__ import annotations

import atexit
import functools
import logging
import queue
import random
import socket
import threading
import time
import urllib.error
import urllib.request
from typing import Callable, Mapping, Optional

from motodiag import __version__
from motodiag.core.timestamps import utc_now
from motodiag.telemetry.dsn import Dsn, DsnError, parse_dsn
from motodiag.telemetry.envelope import envelope

logger = logging.getLogger("motodiag.telemetry")

QUEUE_SIZE = 100
TIMEOUT_S = 5.0
EXIT_FLUSH_S = 2.0
WARN_EVERY_S = 60.0
MAX_PAUSE_S = 60.0
CONTENT_TYPE = "application/x-sentry-envelope"

#: ``(url, headers, body) -> (status, reason, response headers)``.
Transport = Callable[[str, dict[str, str], bytes],
                     tuple[int, str, Mapping[str, str]]]


def urllib_transport(url: str, headers: dict[str, str], body: bytes, *,
                     timeout: float = TIMEOUT_S) -> tuple[int, str, dict[str, str]]:
    """POST ``body`` to ``url``; an HTTP error status is an answer, not a raise."""
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            response.read()
            return response.status, str(response.reason), dict(response.headers)
    except urllib.error.HTTPError as err:
        return err.code, str(err.reason), dict(err.headers or {})


class NullSender:
    """No DSN: sends nothing, starts no thread."""

    enabled = False
    dsn: Optional[Dsn] = None
    release = __version__
    environment = ""
    server_name = ""
    dropped = 0

    def capture(self, event: dict) -> bool:
        return False

    def sampled(self) -> bool:
        return False

    def flush(self, timeout_s: float = EXIT_FLUSH_S) -> bool:
        return True

    def close(self) -> None:
        return None


class Sender:
    """Posts each captured event to the DSN's project from one thread."""

    enabled = True

    def __init__(self, dsn: Dsn, *, transport: Optional[Transport] = None,
                 queue_size: int = QUEUE_SIZE, timeout_s: float = TIMEOUT_S,
                 traces_sample_rate: float = 0.1,
                 clock: Optional[Callable[[], float]] = None,
                 rng: Optional[Callable[[], float]] = None,
                 release: str = __version__, environment: str = "",
                 server_name: str = "",
                 exit_flush_s: float = EXIT_FLUSH_S) -> None:
        self.dsn = dsn
        self.traces_sample_rate = traces_sample_rate
        self.release, self.environment = release, environment
        self.server_name = server_name
        self.exit_flush_s = exit_flush_s
        self._transport: Transport = transport or functools.partial(
            urllib_transport, timeout=timeout_s)
        self._clock = clock or time.monotonic
        self._rng = rng or random.random
        self._queue: queue.Queue[dict] = queue.Queue(maxsize=queue_size)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._paused_until = 0.0
        self._last_warning: Optional[float] = None
        self.dropped = 0
        self.sent = 0
        self.failed = 0
        self.last_status: Optional[int] = None
        self.last_error: Optional[str] = None
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="motodiag-telemetry")
        self._thread.start()
        atexit.register(self.close)

    # --- the caller's side ---------------------------------------------

    def sampled(self) -> bool:
        """Whether this request is timed. The one place it is decided."""
        return self._rng() < self.traces_sample_rate

    def capture(self, event: dict) -> bool:
        """Queue ``event``; False, and counted, when it is dropped."""
        if self._stop.is_set() or self._paused():
            self._drop()
            return False
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            self._drop()
            return False
        return True

    def flush(self, timeout_s: float = EXIT_FLUSH_S) -> bool:
        """True when every queued event was handled within ``timeout_s``."""
        deadline = time.monotonic() + timeout_s
        with self._queue.all_tasks_done:
            while self._queue.unfinished_tasks:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._queue.all_tasks_done.wait(remaining)
        return True

    def close(self) -> None:
        """Flush for the exit's 2 seconds, then stop the thread."""
        if self._stop.is_set():
            return
        self.flush(self.exit_flush_s)
        self._stop.set()
        self._thread.join(timeout=1.0)
        atexit.unregister(self.close)

    # --- the thread's side ---------------------------------------------

    def _paused(self) -> bool:
        return self._clock() < self._paused_until

    def _drop(self) -> None:
        with self._lock:
            self.dropped += 1

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                event = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                if self._paused():
                    self._drop()
                else:
                    self._post(event)
            finally:
                self._queue.task_done()

    def _post(self, event: dict) -> None:
        body = envelope(event, self.dsn, utc_now())
        headers = {"Content-Type": CONTENT_TYPE,
                   "X-Sentry-Auth": self.dsn.auth_header}
        try:
            status, reason, answer = self._transport(
                self.dsn.envelope_url, headers, body)
        except Exception as exc:  # the product comes before the report
            self.failed += 1
            self.last_error = type(exc).__name__
            self._warn("telemetry: sending to %s failed: %s: %s",
                       self.dsn, type(exc).__name__, exc)
            return
        self.last_status = status
        if 200 <= status < 300:
            self.sent += 1
            return
        self.failed += 1
        if status == 429:
            self._pause(answer)
        self._warn("telemetry: %s answered %s %s", self.dsn, status, reason)

    def _pause(self, answer: Mapping[str, str]) -> None:
        lowered = {k.lower(): v for k, v in answer.items()}
        try:
            seconds = float(lowered.get("retry-after", MAX_PAUSE_S))
        except ValueError:
            seconds = MAX_PAUSE_S
        self._paused_until = self._clock() + min(max(seconds, 0.0), MAX_PAUSE_S)

    def _warn(self, message: str, *args: object) -> None:
        now = self._clock()
        if self._last_warning is None or now - self._last_warning >= WARN_EVERY_S:
            self._last_warning = now
            logger.warning(message, *args)
        else:
            logger.debug(message, *args)


def make_sender(settings, *, transport: Optional[Transport] = None):
    """A :class:`Sender` when the DSN is set and usable, else a
    :class:`NullSender`. A bad DSN is logged once and never stops the API."""
    text = (settings.sentry_dsn or "").strip()
    if not text:
        return NullSender()
    try:
        dsn = parse_dsn(text)
    except DsnError as exc:
        logger.error("telemetry is off: MOTODIAG_SENTRY_DSN cannot be used (%s)", exc)
        return NullSender()
    return Sender(dsn, transport=transport,
                  traces_sample_rate=settings.telemetry_traces_sample_rate,
                  environment=settings.telemetry_environment_name,
                  server_name=socket.gethostname())
