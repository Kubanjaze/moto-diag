"""`motodiag shop appointment` and `motodiag shop calendar`: booking by staff, and iCal.

Attached to the ``shop`` group by :func:`register_booking`, which
``register_shop`` calls.
"""

from __future__ import annotations

import json as _json
from datetime import timedelta
from pathlib import Path
from typing import Optional

import click
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import init_db
from motodiag.scheduling import booking, calendar
from motodiag.scheduling.models import AppointmentStatus, AppointmentType


def _end_from(start: str, end: Optional[str], minutes: Optional[int]) -> str:
    if (end is None) == (minutes is None):
        raise click.UsageError("give either --end or --minutes")
    if end is not None:
        return end
    return (booking.parse_entered_time(start)
            + timedelta(minutes=minutes)).isoformat(timespec="minutes")


def _show_warnings(console, warnings: list[str]) -> None:
    for w in warnings:
        console.print(f"[yellow]Warning: {w}[/yellow]")


def register_booking(shop_group: click.Group) -> None:
    from motodiag.cli.shop import (
        _resolve_bike_slug_or_id,
        _resolve_customer_identifier,
    )

    @shop_group.group("appointment")
    def appointment_group() -> None:
        """Book, move, confirm and check in customer appointments."""

    @appointment_group.command("book")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--customer", "customer_identifier", required=True,
                  help="Customer id, name or email.")
    @click.option("--bike", "bike_identifier", required=True,
                  help="Bike id, make or model; it must be linked to the customer.")
    @click.option("--start", required=True,
                  help="The shop's clock time, YYYY-MM-DDTHH:MM.")
    @click.option("--end", default=None, help="End time, YYYY-MM-DDTHH:MM.")
    @click.option("--minutes", type=int, default=None, help="Length instead of --end.")
    @click.option("--type", "appointment_type", default="service",
                  type=click.Choice([t.value for t in AppointmentType]))
    @click.option("--mechanic", "mechanic_user_id", type=int, default=None,
                  help="User id of the mechanic who will see the customer.")
    @click.option("--notes", default=None)
    def appointment_book(shop_id, customer_identifier, bike_identifier, start, end,
                         minutes, appointment_type, mechanic_user_id, notes) -> None:
        """Book an appointment for a customer and their bike."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        bike = _resolve_bike_slug_or_id(bike_identifier)
        try:
            appt_id, warnings = booking.book(
                shop_id, customer["id"], bike["id"], start,
                _end_from(start, end, minutes), appointment_type=appointment_type,
                mechanic_user_id=mechanic_user_id, notes=notes,
            )
        except booking.BookingError as e:
            raise click.ClickException(str(e)) from e
        appt = booking.require_appointment(appt_id)
        console.print(
            f"[green]Booked appointment #{appt_id} for {customer['name']}, "
            f"{appt['scheduled_start']} to {appt['scheduled_end']}.[/green]"
        )
        _show_warnings(console, warnings)

    @appointment_group.command("list")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--from", "from_day", default=None, help="First day, YYYY-MM-DD.")
    @click.option("--to", "to_day", default=None, help="Last day, YYYY-MM-DD.")
    @click.option("--mechanic", "mechanic_user_id", type=int, default=None)
    @click.option("--status", default=None,
                  type=click.Choice([s.value for s in AppointmentStatus]))
    @click.option("--json", "as_json", is_flag=True, default=False)
    def appointment_list(shop_id, from_day, to_day, mechanic_user_id, status,
                         as_json) -> None:
        """A shop's appointments, earliest first."""
        console = get_console()
        init_db()
        rows = booking.list_for_shop(shop_id, from_day, to_day,
                                     mechanic_user_id=mechanic_user_id, status=status)
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No appointments match.[/dim]")
            return
        table = Table(title=f"Appointments at shop {shop_id}", show_lines=False)
        for col in ("ID", "Start", "End", "Customer", "Bike", "Type", "Mechanic",
                    "Status", "WO"):
            table.add_column(col)
        for r in rows:
            table.add_row(
                str(r["id"]), r["scheduled_start"], r["scheduled_end"],
                r["customer_name"], calendar.bike_label(r), r["appointment_type"],
                booking.user_label(r["user_id"]), r["status"],
                str(r["work_order_id"] or "—"),
            )
        console.print(table)

    @appointment_group.command("show")
    @click.argument("appt_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def appointment_show(appt_id: int, as_json: bool) -> None:
        """One appointment."""
        console = get_console()
        init_db()
        try:
            appt = booking.require_appointment(appt_id)
        except booking.BookingError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(appt, default=str, indent=2))
            return
        for key in ("id", "shop_id", "customer_id", "vehicle_id", "appointment_type",
                    "status", "scheduled_start", "scheduled_end", "actual_start",
                    "actual_end", "work_order_id", "notes"):
            console.print(f"{key}: {appt[key] if appt[key] is not None else '—'}")
        console.print(f"mechanic: {booking.user_label(appt['user_id'])}")

    @appointment_group.command("slots")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--date", "day", required=True, help="YYYY-MM-DD.")
    @click.option("--minutes", type=int, required=True, help="Length of the appointment.")
    @click.option("--mechanic", "mechanic_user_id", type=int, default=None)
    @click.option("--open", "open_at", default=None,
                  help="Opening time, HH:MM, when the shop has none recorded.")
    @click.option("--close", "close_at", default=None, help="Closing time, HH:MM.")
    def appointment_slots(shop_id, day, minutes, mechanic_user_id, open_at,
                          close_at) -> None:
        """Free start times on a day, per mechanic, within the shop's hours."""
        console = get_console()
        init_db()
        try:
            free = booking.free_slots(shop_id, day, minutes, mechanic_user_id,
                                      open_at, close_at)
        except booking.BookingError as e:
            raise click.ClickException(str(e)) from e
        for user_id, times in free.items():
            who = booking.user_label(user_id)
            if times:
                console.print(f"{who} (user {user_id}): {', '.join(times)}")
            else:
                console.print(f"{who} (user {user_id}): no free {minutes}-minute slot")

    @appointment_group.command("reschedule")
    @click.argument("appt_id", type=int)
    @click.option("--start", required=True)
    @click.option("--end", default=None)
    @click.option("--minutes", type=int, default=None)
    def appointment_reschedule(appt_id, start, end, minutes) -> None:
        """Move an appointment to another time."""
        console = get_console()
        init_db()
        try:
            warnings = booking.reschedule(appt_id, start, _end_from(start, end, minutes))
        except booking.BookingError as e:
            raise click.ClickException(str(e)) from e
        appt = booking.require_appointment(appt_id)
        console.print(
            f"[green]Appointment #{appt_id} moved to {appt['scheduled_start']} "
            f"to {appt['scheduled_end']}.[/green]"
        )
        _show_warnings(console, warnings)

    @appointment_group.command("confirm")
    @click.argument("appt_id", type=int)
    @click.option("--channel", required=True,
                  type=click.Choice(booking.CONFIRM_CHANNELS),
                  help="How the shop will send or give the confirmation.")
    @click.option("--by", "by_user_id", type=int, default=None,
                  help="User id of the person confirming.")
    def appointment_confirm(appt_id: int, channel: str,
                            by_user_id: Optional[int]) -> None:
        """Mark confirmed, print the confirmation, and log it as a contact.

        Nothing is sent from here: send or read out the printed text yourself.
        """
        console = get_console()
        init_db()
        try:
            text, contact_id = booking.confirm(appt_id, channel, by_user_id)
        except (booking.BookingError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        click.echo(text)
        console.print(
            f"[green]Appointment #{appt_id} confirmed; logged as contact "
            f"#{contact_id} ({channel}). Nothing was sent: send the text above "
            "yourself.[/green]"
        )

    @appointment_group.command("check-in")
    @click.argument("appt_id", type=int)
    @click.option("--wo", "work_order_id", type=int, default=None,
                  help="Link this work order instead of opening a new one.")
    def appointment_check_in(appt_id: int, work_order_id: Optional[int]) -> None:
        """The customer has arrived: open (or link) the work order."""
        console = get_console()
        init_db()
        try:
            wo_id, created = booking.check_in(appt_id, work_order_id)
        except (booking.BookingError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        verb = "opened" if created else "linked"
        console.print(
            f"[green]Appointment #{appt_id} checked in; work order #{wo_id} "
            f"{verb}.[/green]"
        )

    @appointment_group.command("cancel")
    @click.argument("appt_id", type=int)
    @click.option("--reason", default=None)
    def appointment_cancel(appt_id: int, reason: Optional[str]) -> None:
        """Cancel an appointment."""
        _simple(lambda: booking.cancel(appt_id, reason), f"Appointment #{appt_id} cancelled.")

    @appointment_group.command("no-show")
    @click.argument("appt_id", type=int)
    def appointment_no_show(appt_id: int) -> None:
        """The customer did not come."""
        _simple(lambda: booking.mark_no_show(appt_id),
                f"Appointment #{appt_id} marked as a no-show.")

    @appointment_group.command("complete")
    @click.argument("appt_id", type=int)
    def appointment_complete(appt_id: int) -> None:
        """Close a checked-in appointment."""
        _simple(lambda: booking.complete(appt_id), f"Appointment #{appt_id} completed.")

    def _simple(action, message: str) -> None:
        console = get_console()
        init_db()
        try:
            action()
        except booking.BookingError as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[green]{message}[/green]")

    # -----------------------------------------------------------------
    # calendar
    # -----------------------------------------------------------------

    @shop_group.group("calendar")
    def calendar_group() -> None:
        """One calendar of appointments and bay work, and an iCal file of it."""

    def _entries(shop_id, from_day, to_day, mechanic_user_id, bay_id) -> list[dict]:
        if mechanic_user_id is not None and bay_id is not None:
            raise click.UsageError("give --mechanic or --bay, not both")
        try:
            return calendar.calendar_entries(shop_id, from_day, to_day,
                                             mechanic_user_id, bay_id)
        except ValueError as e:
            raise click.ClickException(str(e)) from e

    _range_options = [
        click.option("--shop", "shop_id", type=int, required=True),
        click.option("--from", "from_day", required=True, help="First day, YYYY-MM-DD."),
        click.option("--to", "to_day", required=True, help="Last day, YYYY-MM-DD."),
        click.option("--mechanic", "mechanic_user_id", type=int, default=None,
                     help="Only this mechanic's appointments and bay work."),
        click.option("--bay", "bay_id", type=int, default=None,
                     help="Only this bay's slots."),
    ]

    def _with_range(f):
        for option in reversed(_range_options):
            f = option(f)
        return f

    @calendar_group.command("show")
    @_with_range
    def calendar_show(shop_id, from_day, to_day, mechanic_user_id, bay_id) -> None:
        """Appointments and bay slots in a date range, in time order."""
        console = get_console()
        init_db()
        entries = _entries(shop_id, from_day, to_day, mechanic_user_id, bay_id)
        if not entries:
            console.print(f"[dim]Nothing booked from {from_day} to {to_day}.[/dim]")
            return
        table = Table(title=f"Calendar {from_day} to {to_day}", show_lines=False)
        for col in ("Start", "End", "What", "Status"):
            table.add_column(col)
        for e in entries:
            zone = " UTC" if e["in_utc"] else ""
            table.add_row(
                e["start"].strftime("%Y-%m-%d %H:%M") + zone,
                e["end"].strftime("%Y-%m-%d %H:%M") + zone,
                e["summary"], e["status"].replace("_", " "),
            )
        console.print(table)

    @calendar_group.command("export")
    @_with_range
    @click.option("--out", "out_path", required=True, type=click.Path(dir_okay=False),
                  help="The .ics file to write.")
    def calendar_export(shop_id, from_day, to_day, mechanic_user_id, bay_id,
                        out_path) -> None:
        """Write the calendar as an iCal (.ics) file to import into a calendar app.

        One-way: re-export after changes and import again. Events keep their
        identity between exports, and cancelled ones are marked cancelled.
        """
        console = get_console()
        init_db()
        path = Path(out_path)
        if path.exists():
            raise click.ClickException(f"{path} already exists; choose another name")
        entries = _entries(shop_id, from_day, to_day, mechanic_user_id, bay_id)
        name = f"Shop {shop_id} {from_day} to {to_day}"
        path.write_bytes(calendar.to_ics(entries, name).encode("utf-8"))
        console.print(
            f"[green]Wrote {len(entries)} event(s) to {path}.[/green] Import it into "
            "your calendar app; it does not update by itself."
        )
