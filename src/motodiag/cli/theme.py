"""Shared Rich terminal UI conventions for the MotoDiag CLI.

Phase 129: centralize what had been ad-hoc across Phases 109-128 —
one ``Console`` singleton, one canonical severity / status / tier
color map, one icon set, and a ``status()`` context manager that
wraps ``Console.status`` so long-running AI calls show a spinner.

Public surface:

- :func:`get_console` — lazy singleton accessor. Honors ``NO_COLOR``
  (per https://no-color.org/) and ``COLUMNS`` env vars. First call
  constructs; subsequent calls return the same instance until
  :func:`reset_console` is invoked.
- :func:`reset_console` — clears the singleton for tests that
  need a fresh Console (e.g. after monkey-patching ``NO_COLOR``).
- :data:`SEVERITY_COLORS`, :data:`STATUS_COLORS`, :data:`TIER_COLORS`
  — canonical color maps. Future theme changes (dark mode,
  high-contrast) are a one-dict-edit away.
- :func:`severity_style`, :func:`status_style`, :func:`tier_style`
  — return the Rich style string for a severity / status / tier,
  falling back to ``"dim"`` for unknown values.
- :func:`format_severity`, :func:`format_status`, :func:`format_tier`
  — return a ready-to-print Rich markup string like
  ``"[red]critical[/red]"``.
- :func:`status` — context manager wrapping
  ``get_console().status(msg, spinner=...)``. In non-TTY mode Rich
  suppresses the animation, so CliRunner tests do not capture stray
  spinner frames.
- ``ICON_OK``, ``ICON_WARN``, ``ICON_FAIL``, ``ICON_INFO``,
  ``ICON_LOADING`` — centralized unicode glyphs so a future theme
  swap (ASCII fallback for dumb terminals) is a single file edit.

Rationale:
    Rich's :class:`~rich.console.Console` is safe to share across
    threads but heavy to construct, so we use a process-wide
    singleton the same way :func:`motodiag.core.config.get_settings`
    does. A simple module-level variable is used (instead of
    ``functools.lru_cache``) because we also need the ability to
    reset — the settings module does the same with its
    ``cache_clear`` helper, but a plain global is simpler when no
    arguments are involved.

    Forward-compat: when Phase 175 introduces a JSON output mode
    across every command, swapping the Console implementation
    (or pointing it at a buffer) will be a single change here.
"""

from __future__ import annotations

import os
from typing import Optional

from rich.console import Console


# --- Icons --------------------------------------------------------------------
#
# Centralized so a future theme change (e.g. ASCII fallback for dumb
# terminals, or a test that wants to monkey-patch them to specific
# sentinels) is a single file edit. Keep these as module constants —
# they are compile-time stable and cheap to import.

ICON_OK: str = "✓"
ICON_WARN: str = "⚠"
ICON_FAIL: str = "✗"
ICON_INFO: str = "ℹ"
ICON_LOADING: str = "…"


# --- Color maps ---------------------------------------------------------------
#
# Canonical severity / status / tier → Rich style strings. Stored as
# dicts so a future theme swap (dark mode, high-contrast) is a single
# edit. The ``None`` key on SEVERITY_COLORS is used when a DB row has
# no severity recorded — the renderer can still look up a style without
# branching.

SEVERITY_COLORS: dict[Optional[str], str] = {
    "critical": "red",
    "high":     "orange1",
    "medium":   "yellow",
    "low":      "green",
    "info":     "cyan",
    None:       "dim",
}

STATUS_COLORS: dict[Optional[str], str] = {
    "open":       "yellow",
    "diagnosed":  "cyan",
    "closed":     "green",
    "cancelled":  "dim",
    None:         "dim",
}

TIER_COLORS: dict[Optional[str], str] = {
    "individual": "cyan",
    "shop":       "yellow",
    "company":    "magenta",
    None:         "dim",
}


# --- Console singleton --------------------------------------------------------

_console: Optional[Console] = None


def get_console() -> Console:
    """Return the process-wide Rich Console singleton.

    The Console is constructed lazily on first access. Subsequent
    calls return the same instance until :func:`reset_console` is
    invoked (typically in a test teardown).

    Env-var handling:

    - ``NO_COLOR`` (any non-empty value) → ``no_color=True``.
      Matches the https://no-color.org/ convention that mechanics
      running on dumb terminals (SSH'd shop servers, minimal CI
      runners) can use to disable ANSI color globally.
    - ``COLUMNS`` (integer) → Console width is forced to that value.
      Used by tests to widen the virtual terminal so Rich does not
      word-wrap long table titles across multiple lines.
    - ``force_terminal=False`` is always passed — we want CliRunner
      (which hooks into the non-TTY code path) to capture output
      cleanly without us forcing ANSI codes into the stream.
    """
    global _console
    if _console is None:
        kwargs: dict = {"force_terminal": False}

        # NO_COLOR: per the spec, any non-empty value disables color.
        # We do not inspect the contents — presence alone is enough.
        if os.environ.get("NO_COLOR"):
            kwargs["no_color"] = True

        # COLUMNS: a test or user explicitly sets the virtual-terminal
        # width. We only honor it if it parses as a positive integer;
        # otherwise fall back to Rich's own auto-detection.
        cols_raw = os.environ.get("COLUMNS")
        if cols_raw:
            try:
                cols = int(cols_raw)
                if cols > 0:
                    kwargs["width"] = cols
            except (TypeError, ValueError):
                # Malformed COLUMNS — ignore and let Rich auto-detect.
                pass

        _console = Console(**kwargs)
    return _console


def reset_console() -> None:
    """Clear the Console singleton so the next :func:`get_console`
    call constructs a fresh instance.

    Used by tests that mutate ``NO_COLOR`` / ``COLUMNS`` via
    ``monkeypatch.setenv`` and need the Console to pick up the new
    env. Parallel to :func:`motodiag.core.config.reset_settings`.
    """
    global _console
    _console = None


# --- Style helpers ------------------------------------------------------------


def severity_style(severity: Optional[str]) -> str:
    """Return the Rich style string for a severity value.

    Unknown severities (including empty string) fall back to ``"dim"``
    rather than raising — the CLI should never crash on an unexpected
    knowledge-base entry. Case-insensitive on input.
    """
    if severity is None:
        return SEVERITY_COLORS[None]
    key = str(severity).strip().lower()
    # Empty string after strip → treat as unknown (dim).
    if not key:
        return "dim"
    return SEVERITY_COLORS.get(key, "dim")


def status_style(status: Optional[str]) -> str:
    """Return the Rich style string for a session status value.

    Unknown statuses fall back to ``"dim"``. Case-insensitive.
    """
    if status is None:
        return STATUS_COLORS[None]
    key = str(status).strip().lower()
    if not key:
        return "dim"
    return STATUS_COLORS.get(key, "dim")


def tier_style(tier: Optional[str]) -> str:
    """Return the Rich style string for a subscription tier value.

    Unknown tiers fall back to ``"dim"``. Case-insensitive.
    """
    if tier is None:
        return TIER_COLORS[None]
    key = str(tier).strip().lower()
    if not key:
        return "dim"
    return TIER_COLORS.get(key, "dim")


# --- Markup helpers -----------------------------------------------------------
#
# Each ``format_*`` returns a Rich markup string like
# ``"[red]critical[/red]"`` that is ready to drop into a Panel body
# or a Table cell via ``console.print``. The text content is the
# ORIGINAL input (not the lowercased key) so the renderer can
# preserve casing — e.g. a table might want "CRITICAL" in uppercase
# while still using the "red" style.


def format_severity(severity: Optional[str]) -> str:
    """Return a Rich markup string wrapping the severity in its style.

    Example: ``format_severity("critical")`` → ``"[red]critical[/red]"``.
    ``None`` or empty input → ``"[dim]-[/dim]"`` as a safe placeholder.
    """
    style = severity_style(severity)
    text = severity if severity else "-"
    return f"[{style}]{text}[/{style}]"


def format_status(status: Optional[str]) -> str:
    """Return a Rich markup string wrapping the session status in its style."""
    style = status_style(status)
    text = status if status else "-"
    return f"[{style}]{text}[/{style}]"


def format_tier(tier: Optional[str]) -> str:
    """Return a Rich markup string wrapping the subscription tier in its style."""
    style = tier_style(tier)
    text = tier if tier else "-"
    return f"[{style}]{text}[/{style}]"


# --- Progress spinner ---------------------------------------------------------


def status(message: str, spinner: str = "dots"):
    """Context manager wrapping :meth:`Console.status` on the singleton.

    Usage::

        with theme.status("Analyzing symptoms..."):
            response, usage = diagnose_fn(...)

    In a real terminal this shows an animated spinner with the given
    message. Under CliRunner (non-TTY), Rich auto-detects the lack of
    a terminal and suppresses the animation — so this is safe to leave
    in place across tests without adding mocks.
    """
    return get_console().status(message, spinner=spinner)
