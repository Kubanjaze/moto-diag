"""``motodiag telemetry`` — is crash reporting on, and does the wire work
(Phase 343).

``status`` reads the settings and prints the project, never the key.
``check`` sends one test event to the project and prints its id, so the
operator can find it in Sentry. Nothing else in the repository sends a
test event.
"""

from __future__ import annotations

import socket
from typing import Optional

import click

from motodiag import __version__
from motodiag.core.config import Settings, get_settings
from motodiag.core.timestamps import utc_now
from motodiag.telemetry.dsn import Dsn, DsnError, parse_dsn
from motodiag.telemetry.events import message_event
from motodiag.telemetry.sender import TIMEOUT_S, Sender, Transport

#: The seam a test sets to an in-process transport; None is the real wire.
TRANSPORT: Optional[Transport] = None


def _dsn_or_exit(settings: Settings) -> Dsn:
    """The parsed DSN, or exit 1 when unset and 2 when malformed."""
    text = settings.sentry_dsn.strip()
    if not text:
        click.echo("telemetry: off (MOTODIAG_SENTRY_DSN is not set)")
        raise SystemExit(1)
    try:
        return parse_dsn(text)
    except DsnError as exc:
        click.echo(f"telemetry: off, MOTODIAG_SENTRY_DSN cannot be used: {exc}")
        raise SystemExit(2) from None


def register_telemetry(cli: click.Group) -> None:
    @cli.group("telemetry")
    def telemetry_group() -> None:
        """Crash reports to Sentry: whether they are on, and a test send."""

    @telemetry_group.command("status")
    def status_cmd() -> None:
        """Say whether crash reporting is on, and to which project."""
        settings = get_settings()
        dsn = _dsn_or_exit(settings)
        click.echo("telemetry: on")
        click.echo(f"  project:     {dsn}")
        click.echo(f"  environment: {settings.telemetry_environment_name}")
        click.echo(f"  release:     {__version__}")
        click.echo(f"  sample rate: {settings.telemetry_traces_sample_rate}")

    @telemetry_group.command("check")
    def check_cmd() -> None:
        """Send one test event to the Sentry project and print its id."""
        settings = get_settings()
        try:
            dsn = _dsn_or_exit(settings)
        except SystemExit as stop:
            raise SystemExit(2) from stop
        host = socket.gethostname()
        text = f"telemetry check from {host} at {utc_now()}"
        event = message_event(text, release=__version__,
                              environment=settings.telemetry_environment_name,
                              server_name=host)
        click.echo(f"sending one test event to {dsn}: {text!r}")
        click.echo(f"  event id: {event['event_id']}")
        sender = Sender(dsn, transport=TRANSPORT,
                        environment=settings.telemetry_environment_name,
                        server_name=host)
        sender.capture(event)
        sender.flush(TIMEOUT_S + 1)
        sender.close()
        status = sender.last_status
        if status is not None and 200 <= status < 300:
            click.echo(f"sent: {dsn} accepted event {event['event_id']} "
                       f"(status {status})")
            return
        if status is not None:
            click.echo(f"not sent: {dsn} answered status {status}")
        else:
            click.echo(f"not sent: {sender.last_error or 'no answer'}")
        raise SystemExit(1)
