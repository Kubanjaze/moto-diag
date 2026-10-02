"""Phase 369 — a lost xdist worker explains itself.

F183: four regressions lost a worker with only "[gwN] node down: Not
properly terminated". xdist sees the channel close; it never says how the
process ended or what it was doing. This plugin records, per worker:

- its PID, and the last test it started (``<gw>.last``, rewritten at each
  test's start);
- a traceback for any catchable signal it receives (``<gw>.<SIGNAME>``,
  written by ``faulthandler.register`` with ``chain=True``, so the signal's
  own behaviour is unchanged);
- a fatal-error dump (``<gw>.faulthandler``) in a file instead of stderr,
  which pytest's capture can swallow.

On the controller, ``pytest_testnodedown`` reads the worker's exit status
from its process and writes one block into the run's output, so the
regression log itself names the cause. The files live in a temporary
directory the controller makes, outside pytest's basetemp: the suite's
nested pytest runs prune numbered basetemp directories.

Only an xdist run uses it; a serial run has no worker to lose. The cause
it was built to find has its own check, ``support.alarm_left_armed``.
"""

from __future__ import annotations

import faulthandler
import os
import signal
import tempfile
from pathlib import Path

import pytest

DIR_KEY = "motodiag_worker_loss_dir"
SIGNALS = ("SIGTERM", "SIGHUP", "SIGPIPE", "SIGXCPU", "SIGXFSZ", "SIGUSR1", "SIGUSR2")

_folder_key = pytest.StashKey[str]()
_last: Path | None = None             # this worker's ``<gw>.last``
_open_files: list = []                # kept open for faulthandler's lifetime


@pytest.hookimpl(trylast=True)        # after pytest's own faulthandler setup
def pytest_configure(config: pytest.Config) -> None:
    global _last
    workerinput = getattr(config, "workerinput", None)
    if workerinput is None:
        # xdist's option, set before any configure hook; its "dsession"
        # plugin is registered in xdist's own configure, which may run later.
        if getattr(config.option, "dist", "no") != "no":
            config.stash[_folder_key] = tempfile.mkdtemp(prefix="motodiag_worker_loss_")
        return
    folder = workerinput.get(DIR_KEY)
    if not folder:
        return
    base = Path(folder) / workerinput["workerid"]
    fatal = open(f"{base}.faulthandler", "w")
    _open_files.append(fatal)
    faulthandler.enable(file=fatal, all_threads=True)
    for name in SIGNALS:
        f = open(f"{base}.{name}", "w")
        _open_files.append(f)
        faulthandler.register(getattr(signal, name), file=f, all_threads=True, chain=True)
    _last = Path(f"{base}.last")
    _last.write_text(f"pid {os.getpid()}\n")


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node) -> None:
    folder = node.config.stash.get(_folder_key, None)
    if folder:
        node.workerinput[DIR_KEY] = folder


def pytest_runtest_logstart(nodeid: str, location) -> None:
    if _last is not None:
        _last.write_text(f"pid {os.getpid()}\nstarted {nodeid}\n")


def exit_status(returncode: int | None) -> str:
    """How a process ended, from Popen's returncode."""
    if returncode is None:
        return "exit status not read"
    if returncode < 0:
        try:
            return f"killed by signal {signal.Signals(-returncode).name} ({-returncode})"
        except ValueError:
            return f"killed by signal {-returncode}"
    return f"exited with status {returncode} (no signal)"


def _indent(text: str) -> list[str]:
    """A dump's lines, prefixed so one grep for "worker-loss:" keeps them."""
    return [f"worker-loss:   {ln}" for ln in text.splitlines()]


def describe(folder: str, workerid: str, returncode: int | None, pid: int | None) -> list[str]:
    """The lines written into the run's output for one lost worker."""
    base = Path(folder) / workerid
    lines = [f"worker-loss: {workerid} pid {pid}: {exit_status(returncode)}"]
    last = Path(f"{base}.last")
    lines.append("worker-loss: " + (last.read_text().strip().replace("\n", "; ")
                                    if last.exists() else "no record of a started test"))
    received = []
    for name in SIGNALS:
        p = Path(f"{base}.{name}")
        if p.exists() and p.stat().st_size:
            received.append(name)
            lines += [f"worker-loss: {name} received:"] + _indent(p.read_text())
    if not received:
        lines.append(f"worker-loss: no catchable signal received ({', '.join(SIGNALS)})")
    fatal = Path(f"{base}.faulthandler")
    if fatal.exists() and fatal.stat().st_size:
        lines += ["worker-loss: faulthandler dump:"] + _indent(fatal.read_text())
    else:
        lines.append("worker-loss: faulthandler dump empty (no fatal error)")
    lines.append(f"worker-loss: files in {folder}")
    return lines


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node, error) -> None:
    folder = node.config.stash.get(_folder_key, None)
    if not error or not folder:
        return
    popen = getattr(node.gateway._io, "popen", None)   # execnet's popen gateway
    pid = returncode = None
    note = []
    if popen is not None:
        pid = popen.pid
        try:
            returncode = popen.wait(timeout=10)
        except Exception as e:        # the report says so; nothing is hidden
            note = [f"worker-loss: reading its exit status failed: {e!r}"]
    workerid = node.gateway.id
    lines = describe(folder, workerid, returncode, pid) + note
    Path(folder, f"{workerid}.down").write_text("\n".join(lines) + "\n")
    tr = node.config.pluginmanager.get_plugin("terminalreporter")
    for ln in lines:
        tr.write_line(ln)
