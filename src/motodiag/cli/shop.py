"""Shop management CLI — ``motodiag shop {profile,customer,intake}``.

Phase 160. First Track G command surface. Opens shop management with
three subgroups:

- ``profile`` (3 subcommands) — register / show / update a shop's
  identity (name, address, contact, hours, tax ID).
- ``customer`` (9 subcommands) — CRUD + bike-link operations over the
  existing Phase 113 ``crm/`` substrate. This is the first CLI surface
  for customers (Phase 113 shipped the repo but never wired the CLI).
- ``intake`` (7 subcommands) — log bike arrivals as intake_visits rows
  with guarded status lifecycle (open / closed / cancelled / reopen).

Downstream Track G phases will append more subgroups (work orders in
161, issues in 162, parts in 165-166, scheduling in 168, invoicing in
169) via ``shop_group.group("...")`` — Click supports additive growth.
"""

from __future__ import annotations

import json as _json
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table

from motodiag.cli.theme import get_console
from motodiag.core.database import get_connection, init_db
from motodiag.crm import customer_bikes_repo, customer_repo
from motodiag.crm.models import Customer, CustomerRelationship
from motodiag.shop import (
    INTAKE_CLOSE_REASONS,
    INTAKE_STATUSES,
    ISSUE_CATEGORIES,
    ISSUE_SEVERITIES,
    ISSUE_STATUSES,
    IntakeAlreadyClosedError,
    IntakeNotFoundError,
    InvalidIssueTransition,
    InvalidWorkOrderTransition,
    IssueFKError,
    IssueNotFoundError,
    InvalidTierPreferenceError,
    InvoiceGenerationError,
    InvoiceNotFoundError,
    generate_invoice_for_wo,
    get_invoice_with_items,
    list_invoices_for_shop,
    mark_invoice_paid,
    revenue_rollup,
    void_invoice,
    EVENT_TRIGGERS,
    DuplicateRuleNameError,
    InvalidActionError,
    InvalidConditionError,
    InvalidEventError,
    RuleNotFoundError,
    build_wo_context,
    create_rule,
    delete_rule,
    disable_rule,
    enable_rule,
    evaluate_rule,
    fire_rule_for_wo,
    get_rule,
    list_rule_runs,
    list_rules,
    trigger_rules_for_event,
    update_rule,
    SHOP_ROLES,
    InvalidRoleError,
    MechanicNotInShopError,
    PermissionDenied,
    ShopMembershipNotFoundError,
    add_shop_member,
    current_assignment,
    deactivate_member,
    list_shop_mechanics,
    list_shop_members,
    list_work_order_assignments,
    mechanic_workload,
    reactivate_member,
    reassign_work_order,
    set_member_role,
    customer_repeat_rate,
    dashboard_snapshot,
    labor_accuracy,
    mechanic_performance,
    overrun_rate,
    throughput as analytics_throughput,
    top_issues as analytics_top_issues,
    top_parts as analytics_top_parts,
    turnaround,
    utilization_rollup,
    NOTIFICATION_EVENTS,
    NotificationContextError,
    NotificationNotFoundError,
    UnknownEventError,
    cancel_notification,
    get_notification,
    list_notifications,
    list_template_catalog,
    mark_notification_failed,
    mark_notification_sent,
    preview_notification,
    resend_notification,
    trigger_notification,
    BayNotFoundError,
    InvalidSlotTransition,
    LaborEstimatorError,
    LaborEstimateMathError,
    ReconcileMissingDataError,
    SlotNotFoundError,
    SlotOverlapError,
    PartNotFoundError,
    PartNotInCatalogError,
    PriorityBudgetExhausted,
    PriorityScorerError,
    ShopNameExistsError,
    ShopTriageError,
    ShopTriageWeights,
    WorkOrderPartNotFoundError,
    InvalidPartNeedTransition,
    add_part_to_work_order,
    build_requisition,
    cancel_part_need,
    get_requisition,
    list_parts_for_shop_open_wos,
    list_parts_for_wo,
    list_requisitions,
    mark_part_ordered,
    mark_part_received,
    get_recommendation,
    recommend_source,
    sourcing_budget,
    bulk_estimate_open_wos,
    estimate_labor,
    labor_budget,
    list_labor_estimates,
    reconcile_with_actual,
    BAY_TYPES,
    add_bay,
    cancel_slot,
    complete_slot,
    deactivate_bay,
    detect_conflicts,
    get_bay,
    get_slot,
    list_bays,
    list_slots,
    optimize_shop_day,
    reschedule_slot,
    schedule_wo as bay_schedule_wo,
    start_slot,
    utilization_for_day,
    ShopNotFoundError,
    WORK_ORDER_STATUSES,
    WorkOrderFKError,
    WorkOrderNotFoundError,
    assign_mechanic,
    cancel_intake,
    cancel_work_order,
    categorize_issue,
    close_intake,
    complete_work_order,
    create_intake,
    create_issue,
    create_shop,
    create_work_order,
    delete_shop,
    get_intake,
    get_issue,
    get_shop,
    get_shop_by_name,
    get_work_order,
    issue_stats,
    link_dtc,
    link_symptom,
    list_intakes,
    list_issues,
    list_open_for_bike,
    list_shops,
    list_work_orders,
    mark_duplicate_issue,
    mark_wontfix_issue,
    open_work_order,
    pause_work,
    priority_budget,
    rescore_all_open,
    score_work_order,
    build_triage_queue,
    clear_urgent,
    flag_urgent,
    load_triage_weights,
    reset_triage_weights,
    save_triage_weights,
    skip_work_order,
    reopen_intake,
    reopen_issue,
    reopen_work_order,
    resolve_issue,
    resume_work,
    start_work,
    unassign_mechanic,
    update_intake,
    update_issue,
    update_shop,
    update_work_order,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


UNASSIGNED_CUSTOMER_ID = 1


def _resolve_shop_identifier(
    identifier: Optional[str], *, require: bool = True,
) -> Optional[dict]:
    """Resolve a shop identifier (CLI-friendly): numeric id or name.

    When ``identifier`` is None and exactly one active shop exists,
    auto-select it (ambiguity remediation per Phase 125 style). When
    multiple active shops exist and no identifier is given, raise a
    ClickException with the list of choices.
    """
    if identifier is None:
        shops = list_shops()
        if not shops:
            if not require:
                return None
            raise click.ClickException(
                "No shop registered. Run `motodiag shop profile init` first."
            )
        if len(shops) == 1:
            return shops[0]
        names = ", ".join(s["name"] for s in shops)
        raise click.ClickException(
            f"Multiple shops exist ({names}); pass --shop NAME or --shop ID."
        )

    # Numeric first — fastest path.
    try:
        shop_id = int(identifier)
    except (TypeError, ValueError):
        row = get_shop_by_name(str(identifier))
    else:
        row = get_shop(shop_id)
        if row is None:
            # Might have been passed a numeric-looking name; fall back.
            row = get_shop_by_name(str(identifier))

    if row is None:
        raise click.ClickException(
            f"Shop not found: {identifier!r}. "
            "Run `motodiag shop profile list` to see registered shops."
        )
    return row


def _resolve_customer_identifier(identifier: str) -> dict:
    """Resolve a customer identifier (CLI-friendly): id, name, or email."""
    try:
        customer_id = int(identifier)
    except (TypeError, ValueError):
        results = customer_repo.search_customers(str(identifier))
        if not results:
            raise click.ClickException(
                f"Customer not found: {identifier!r}. "
                "Use `motodiag shop customer search QUERY` to look them up."
            )
        if len(results) > 1:
            names = ", ".join(
                f"{r['name']} (id={r['id']})" for r in results[:5]
            )
            raise click.ClickException(
                f"Ambiguous customer {identifier!r}; matches: {names}. "
                "Pass the customer id instead."
            )
        return results[0]
    row = customer_repo.get_customer(customer_id)
    if row is None:
        raise click.ClickException(
            f"Customer not found: id={customer_id}."
        )
    return row


def _resolve_bike_slug_or_id(identifier: str) -> dict:
    """Resolve a bike by integer id or LIKE-match on model/make.

    Narrower than diagnose.py's full slug parser (this phase does not
    need year-stripping). On miss, raises a Phase 125-style
    remediation ClickException pointing the mechanic at
    ``motodiag garage add`` (created by Phase 128) or ``motodiag
    vehicle list``.
    """
    try:
        vehicle_id = int(identifier)
    except (TypeError, ValueError):
        vehicle_id = None

    with get_connection() as conn:
        if vehicle_id is not None:
            row = conn.execute(
                "SELECT * FROM vehicles WHERE id = ?", (vehicle_id,),
            ).fetchone()
            if row is not None:
                return dict(row)
        pattern = f"%{str(identifier)}%"
        row = conn.execute(
            """SELECT * FROM vehicles
               WHERE LOWER(model) LIKE LOWER(?)
                  OR LOWER(make) LIKE LOWER(?)
               ORDER BY created_at, id
               LIMIT 1""",
            (pattern, pattern),
        ).fetchone()
    if row is None:
        raise click.ClickException(
            f"Bike not found: {identifier!r}. "
            "Run `motodiag vehicle list` to see your garage, or "
            "`motodiag vehicle add` to register one."
        )
    return dict(row)


def _parse_set_pairs(pairs: tuple[str, ...]) -> dict:
    """Parse repeated ``--set key=value`` pairs into a dict."""
    out: dict = {}
    for pair in pairs:
        if "=" not in pair:
            raise click.ClickException(
                f"--set expects KEY=VALUE (got {pair!r})"
            )
        key, _, value = pair.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            raise click.ClickException(
                f"--set key must not be empty (got {pair!r})"
            )
        out[key] = value if value != "" else None
    return out


def _render_shop_panel(console, shop: dict) -> None:
    """Render one shop as a Rich Panel."""
    lines: list[str] = []
    lines.append(f"[bold]{shop['name']}[/bold]  (id={shop['id']})")
    addr_bits = [
        shop.get("address"),
        ", ".join(
            b for b in (shop.get("city"), shop.get("state"), shop.get("zip"))
            if b
        ),
    ]
    addr = "  ".join(b for b in addr_bits if b)
    if addr:
        lines.append(f"Address: {addr}")
    if shop.get("phone"):
        lines.append(f"Phone:   {shop['phone']}")
    if shop.get("email"):
        lines.append(f"Email:   {shop['email']}")
    if shop.get("tax_id"):
        lines.append(f"Tax ID:  {shop['tax_id']}")
    if shop.get("hours_json"):
        lines.append(f"Hours:   {shop['hours_json']}")
    if not shop.get("is_active", 1):
        lines.append("[dim]INACTIVE[/dim]")
    console.print(Panel("\n".join(lines), title="Shop Profile"))


def _render_customer_panel(console, customer: dict) -> None:
    """Render one customer as a Rich Panel."""
    lines: list[str] = []
    lines.append(f"[bold]{customer['name']}[/bold]  (id={customer['id']})")
    if customer.get("email"):
        lines.append(f"Email: {customer['email']}")
    if customer.get("phone"):
        lines.append(f"Phone: {customer['phone']}")
    if customer.get("address"):
        lines.append(f"Address: {customer['address']}")
    if customer.get("notes"):
        lines.append(f"Notes: {customer['notes']}")
    if not customer.get("is_active", 1):
        lines.append("[dim]INACTIVE[/dim]")
    console.print(Panel("\n".join(lines), title="Customer"))


def _render_work_order_panel(console, wo: dict) -> None:
    """Render one work order as a Rich Panel."""
    status = wo.get("status", "draft")
    status_color = {
        "draft": "dim", "open": "green", "in_progress": "cyan",
        "on_hold": "yellow", "completed": "blue", "cancelled": "red",
    }.get(status, "white")
    priority = wo.get("priority", 3)
    prio_color = {1: "bold red", 2: "red", 3: "yellow", 4: "dim", 5: "dim"}
    prio_style = prio_color.get(priority, "white")
    lines: list[str] = []
    lines.append(
        f"[bold]WO id={wo['id']}:[/bold] {wo.get('title', '?')}  "
        f"[{status_color}]{status.upper().replace('_', ' ')}[/{status_color}]  "
        f"[{prio_style}]P{priority}[/{prio_style}]"
    )
    bike_label = " ".join(
        str(b) for b in (
            wo.get("vehicle_year"),
            wo.get("vehicle_make"),
            wo.get("vehicle_model"),
        ) if b
    )
    lines.append(
        f"Shop:     {wo.get('shop_name', '?')}  (id={wo['shop_id']})"
    )
    lines.append(
        f"Customer: {wo.get('customer_name', '?')}  (id={wo['customer_id']})"
    )
    lines.append(
        f"Bike:     {bike_label or '?'}  (id={wo['vehicle_id']})"
    )
    if wo.get("intake_visit_id"):
        lines.append(f"Intake:   id={wo['intake_visit_id']}")
    mech = wo.get("assigned_mechanic_name") or wo.get(
        "assigned_mechanic_user_id"
    )
    if mech:
        lines.append(f"Mechanic: {mech}")
    if wo.get("estimated_hours") is not None:
        lines.append(f"Est hrs:  {wo['estimated_hours']}")
    if wo.get("actual_hours") is not None:
        lines.append(f"Act hrs:  {wo['actual_hours']}")
    if wo.get("estimated_parts_cost_cents") is not None:
        cents = int(wo["estimated_parts_cost_cents"])
        lines.append(f"Parts $:  ${cents / 100:.2f}")
    if wo.get("description"):
        lines.append(f"\nDescription:\n  {wo['description']}")
    if wo.get("opened_at"):
        lines.append(f"\nOpened:    {wo['opened_at']}")
    if wo.get("started_at"):
        lines.append(f"Started:   {wo['started_at']}")
    if wo.get("completed_at"):
        lines.append(f"Completed: {wo['completed_at']}")
    if wo.get("closed_at") and status == "cancelled":
        lines.append(f"Cancelled: {wo['closed_at']}")
    if wo.get("on_hold_reason"):
        lines.append(f"\nHold reason: {wo['on_hold_reason']}")
    if wo.get("cancellation_reason"):
        lines.append(f"\nCancel reason: {wo['cancellation_reason']}")
    console.print(Panel("\n".join(lines), title="Work Order"))


def _render_intake_panel(console, intake: dict) -> None:
    """Render one intake as a Rich Panel."""
    status = intake.get("status", "open")
    status_color = {
        "open": "green", "closed": "blue", "cancelled": "red",
    }.get(status, "white")
    lines: list[str] = []
    lines.append(
        f"[bold]Intake id={intake['id']}[/bold]  "
        f"[{status_color}]{status.upper()}[/{status_color}]"
    )
    lines.append(
        f"Shop:     {intake.get('shop_name', '?')}  "
        f"(id={intake['shop_id']})"
    )
    lines.append(
        f"Customer: {intake.get('customer_name', '?')}  "
        f"(id={intake['customer_id']})"
    )
    bike_label = " ".join(
        str(b) for b in (
            intake.get("vehicle_year"),
            intake.get("vehicle_make"),
            intake.get("vehicle_model"),
        ) if b
    )
    lines.append(
        f"Bike:     {bike_label or '?'}  (id={intake['vehicle_id']})"
    )
    lines.append(f"Intake at: {intake.get('intake_at', '?')}")
    if intake.get("mileage_at_intake") is not None:
        lines.append(f"Mileage:  {intake['mileage_at_intake']}")
    if intake.get("reported_problems"):
        lines.append(f"\nReported problems:\n  {intake['reported_problems']}")
    if status != "open":
        lines.append(f"\nClosed at: {intake.get('closed_at', '?')}")
        if intake.get("close_reason"):
            lines.append(f"Reason:    {intake['close_reason']}")
    console.print(Panel("\n".join(lines), title="Intake Visit"))


def _render_notification_panel(console, notif) -> None:
    """Render a Notification or NotificationPreview as a Rich Panel."""
    status_color = {
        "pending": "yellow", "sent": "green",
        "failed": "red", "cancelled": "dim",
    }
    # Preview objects don't have id/status; guard with getattr
    notif_id = getattr(notif, "id", None)
    notif_status = getattr(notif, "status", "preview")
    color = status_color.get(notif_status, "white")
    header = (
        f"[bold]{notif.event}[/bold] / {notif.channel}  "
        f"[{color}]{notif_status}[/{color}]"
    )
    if notif_id is not None:
        header = f"[bold]Notification #{notif_id}[/bold]  " + header
    lines: list[str] = [header, "", f"To: {notif.recipient}"]
    if notif.subject:
        lines.append(f"Subject: {notif.subject}")
    lines.append("")
    lines.append(notif.body)
    title = (
        f"Notification #{notif_id}" if notif_id is not None
        else "Preview"
    )
    console.print(Panel("\n".join(lines), title=title))


def _render_invoice_panel(console, summary) -> None:
    """Render an InvoiceSummary as a Rich Panel."""
    status_color = {
        "draft": "white", "sent": "cyan", "paid": "green",
        "overdue": "red", "cancelled": "dim",
    }.get(summary.status, "white")
    lines: list[str] = [
        f"[bold]Invoice {summary.invoice_number}[/bold]  "
        f"[{status_color}]{summary.status.upper()}[/{status_color}]",
        f"ID:        {summary.id}",
        f"WO:        {summary.work_order_id or '—'}",
        f"Customer:  {summary.customer_name or '—'} "
        f"(id={summary.customer_id})",
        f"Issued:    {summary.issued_at or '—'}",
    ]
    if summary.paid_at:
        lines.append(f"Paid at:   {summary.paid_at}")
    lines.append("")
    lines.append("[bold]Line items[/bold]")
    for i in summary.items:
        lines.append(
            f"  {i.item_type:<10} qty={i.quantity:g} "
            f"@ ${i.unit_price_cents / 100:.2f} "
            f"→ ${i.line_total_cents / 100:.2f}   {i.description}"
        )
    lines.append("")
    lines.append(f"Subtotal:  ${summary.subtotal_cents / 100:.2f}")
    lines.append(f"Tax:       ${summary.tax_cents / 100:.2f}")
    lines.append(f"[bold]Total:     ${summary.total_cents / 100:.2f}[/bold]")
    if summary.notes:
        lines.append(f"\nNotes:     {summary.notes}")
    console.print(Panel("\n".join(lines), title="Invoice"))


# ---------------------------------------------------------------------------
# Register the top-level group
# ---------------------------------------------------------------------------


def register_shop(cli_group: click.Group) -> None:
    """Attach the ``shop`` subgroup to the top-level CLI.

    Phase 160 registers three nested subgroups (``profile``,
    ``customer``, ``intake``) and 19 subcommands. Subsequent Track G
    phases append new subgroups — e.g. ``shop work-order`` (161),
    ``shop issue`` (162), ``shop invoice`` (169) — without touching
    this function.
    """

    @cli_group.group("shop")
    def shop_group() -> None:
        """Shop management: profile, customers, intake."""

    # -----------------------------------------------------------------
    # shop profile {init, show, update, list, delete}
    # -----------------------------------------------------------------

    @shop_group.group("profile")
    def profile_group() -> None:
        """Register and manage shop profiles."""

    @profile_group.command("init")
    @click.option("--name", required=True, help="Shop name (must be unique per owner).")
    @click.option("--address", default=None)
    @click.option("--city", default=None)
    @click.option("--state", default=None)
    @click.option("--zip", "zip_code", default=None)
    @click.option("--phone", default=None)
    @click.option("--email", default=None)
    @click.option("--tax-id", "tax_id", default=None)
    @click.option(
        "--hours", "hours_json", default=None,
        help='Hours as JSON object, e.g. \'{"mon":"08:00-17:00"}\'.',
    )
    def profile_init(
        name: str,
        address: Optional[str],
        city: Optional[str],
        state: Optional[str],
        zip_code: Optional[str],
        phone: Optional[str],
        email: Optional[str],
        tax_id: Optional[str],
        hours_json: Optional[str],
    ) -> None:
        """Register a new shop. Idempotent on (owner, name)."""
        console = get_console()
        init_db()
        existing = get_shop_by_name(name)
        if existing is not None:
            console.print(
                f"[yellow]Shop {name!r} already exists "
                f"(id={existing['id']}).[/yellow]"
            )
            _render_shop_panel(console, existing)
            return
        try:
            shop_id = create_shop(
                name=name, address=address, city=city, state=state,
                zip=zip_code, phone=phone, email=email, tax_id=tax_id,
                hours_json=hours_json,
            )
        except (ShopNameExistsError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        row = get_shop(shop_id)
        assert row is not None
        console.print(f"[green]Registered shop id={shop_id}.[/green]")
        _render_shop_panel(console, row)

    @profile_group.command("show")
    @click.option("--shop", "shop_identifier", default=None,
                  help="Shop id or name (defaults to only active shop).")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def profile_show(shop_identifier: Optional[str], as_json: bool) -> None:
        """Show a shop profile."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        if as_json:
            click.echo(_json.dumps(shop, default=str, indent=2))
            return
        _render_shop_panel(console, shop)

    @profile_group.command("list")
    @click.option("--include-inactive", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def profile_list(include_inactive: bool, as_json: bool) -> None:
        """List registered shops."""
        console = get_console()
        init_db()
        shops = list_shops(include_inactive=include_inactive)
        if as_json:
            click.echo(_json.dumps(shops, default=str, indent=2))
            return
        if not shops:
            console.print("[dim]No shops registered.[/dim]")
            return
        table = Table(title="Shops", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("Name")
        table.add_column("Phone")
        table.add_column("Open intakes", justify="right")
        table.add_column("Total intakes", justify="right")
        for s in shops:
            label = s["name"]
            if not s.get("is_active", 1):
                label = f"[dim]{label} (inactive)[/dim]"
            table.add_row(
                str(s["id"]),
                label,
                s.get("phone") or "—",
                str(s.get("open_intake_count", 0)),
                str(s.get("total_intake_count", 0)),
            )
        console.print(table)

    @profile_group.command("update")
    @click.option("--shop", "shop_identifier", default=None,
                  help="Shop id or name (defaults to only active shop).")
    @click.option("--set", "set_pairs", multiple=True,
                  help="Repeated KEY=VALUE updates, e.g. --set phone=555-0101.")
    def profile_update(
        shop_identifier: Optional[str], set_pairs: tuple[str, ...],
    ) -> None:
        """Update fields on a shop profile."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        if not set_pairs:
            raise click.ClickException(
                "No updates specified. Pass one or more --set KEY=VALUE."
            )
        updates = _parse_set_pairs(set_pairs)
        try:
            changed = update_shop(shop["id"], updates)
        except (ShopNameExistsError, ShopNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        if not changed:
            console.print(
                "[yellow]No updatable fields recognized in --set payload.[/yellow]"
            )
            return
        row = get_shop(shop["id"])
        assert row is not None
        console.print(f"[green]Updated shop id={shop['id']}.[/green]")
        _render_shop_panel(console, row)

    @profile_group.command("delete")
    @click.option("--shop", "shop_identifier", required=True,
                  help="Shop id or name.")
    @click.option("--force", is_flag=True, default=False,
                  help="Skip confirmation prompt.")
    def profile_delete(shop_identifier: str, force: bool) -> None:
        """Hard-delete a shop (CASCADE drops intake history)."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        if not force:
            click.confirm(
                f"Really delete shop {shop['name']!r} (id={shop['id']})? "
                "This CASCADE-drops all intake history.",
                abort=True,
            )
        try:
            delete_shop(shop["id"])
        except ShopNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[green]Deleted shop id={shop['id']}.[/green]")

    # -----------------------------------------------------------------
    # shop customer {add, list, show, search, update, deactivate,
    #                link-bike, unlink-bike, bikes}
    # -----------------------------------------------------------------

    @shop_group.group("customer")
    def customer_group() -> None:
        """Manage customer records (wraps Phase 113 CRM layer)."""

    @customer_group.command("add")
    @click.option("--name", required=True)
    @click.option("--email", default=None)
    @click.option("--phone", default=None)
    @click.option("--address", default=None)
    @click.option("--notes", default=None)
    def customer_add(
        name: str,
        email: Optional[str],
        phone: Optional[str],
        address: Optional[str],
        notes: Optional[str],
    ) -> None:
        """Add a new customer."""
        console = get_console()
        init_db()
        try:
            customer = Customer(
                name=name, email=email, phone=phone,
                address=address, notes=notes,
            )
        except Exception as e:
            raise click.ClickException(f"Invalid customer data: {e}") from e
        customer_id = customer_repo.create_customer(customer)
        row = customer_repo.get_customer(customer_id)
        assert row is not None
        console.print(f"[green]Added customer id={customer_id}.[/green]")
        _render_customer_panel(console, row)

    @customer_group.command("list")
    @click.option("--inactive", is_flag=True, default=False,
                  help="Include deactivated customers.")
    @click.option("--limit", type=int, default=50)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def customer_list(
        inactive: bool, limit: int, as_json: bool,
    ) -> None:
        """List customers."""
        console = get_console()
        init_db()
        is_active = None if inactive else True
        rows = customer_repo.list_customers(is_active=is_active)
        rows = rows[: max(0, int(limit))] if limit else rows
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No customers.[/dim]")
            return
        table = Table(title="Customers", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("Name")
        table.add_column("Phone")
        table.add_column("Email")
        for r in rows:
            label = r["name"]
            if not r.get("is_active", 1):
                label = f"[dim]{label} (inactive)[/dim]"
            table.add_row(
                str(r["id"]), label,
                r.get("phone") or "—", r.get("email") or "—",
            )
        console.print(table)

    @customer_group.command("show")
    @click.argument("customer_identifier")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def customer_show(
        customer_identifier: str, as_json: bool,
    ) -> None:
        """Show a customer + their linked bikes."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        bikes = customer_bikes_repo.list_bikes_for_customer(customer["id"])
        payload = {"customer": customer, "bikes": bikes}
        if as_json:
            click.echo(_json.dumps(payload, default=str, indent=2))
            return
        _render_customer_panel(console, customer)
        if not bikes:
            console.print("[dim]No linked bikes.[/dim]")
            return
        table = Table(title="Linked bikes", show_lines=False)
        table.add_column("Vehicle ID", justify="right")
        table.add_column("Make")
        table.add_column("Model")
        table.add_column("Year", justify="right")
        table.add_column("Relationship")
        for b in bikes:
            table.add_row(
                str(b.get("vehicle_id", b.get("id", "?"))),
                str(b.get("make", "?")),
                str(b.get("model", "?")),
                str(b.get("year", "?")),
                str(b.get("relationship", "?")),
            )
        console.print(table)

    @customer_group.command("search")
    @click.argument("query")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def customer_search(query: str, as_json: bool) -> None:
        """Search customers by name, email, or phone."""
        console = get_console()
        init_db()
        rows = customer_repo.search_customers(query)
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print(f"[dim]No matches for {query!r}.[/dim]")
            return
        table = Table(title=f"Search: {query!r}", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("Name")
        table.add_column("Phone")
        table.add_column("Email")
        for r in rows:
            table.add_row(
                str(r["id"]), r["name"],
                r.get("phone") or "—", r.get("email") or "—",
            )
        console.print(table)

    @customer_group.command("update")
    @click.argument("customer_identifier")
    @click.option("--set", "set_pairs", multiple=True)
    def customer_update(
        customer_identifier: str, set_pairs: tuple[str, ...],
    ) -> None:
        """Update fields on a customer record."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        if not set_pairs:
            raise click.ClickException(
                "No updates specified. Pass one or more --set KEY=VALUE."
            )
        updates = _parse_set_pairs(set_pairs)
        ok = customer_repo.update_customer(customer["id"], updates)
        if not ok:
            console.print("[yellow]No fields updated.[/yellow]")
            return
        row = customer_repo.get_customer(customer["id"])
        assert row is not None
        console.print(
            f"[green]Updated customer id={customer['id']}.[/green]"
        )
        _render_customer_panel(console, row)

    @customer_group.command("deactivate")
    @click.argument("customer_identifier")
    def customer_deactivate(customer_identifier: str) -> None:
        """Soft-delete a customer (preserves history)."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        if customer["id"] == UNASSIGNED_CUSTOMER_ID:
            raise click.ClickException(
                "Cannot deactivate the Unassigned placeholder customer."
            )
        ok = customer_repo.deactivate_customer(customer["id"])
        if not ok:
            console.print(
                "[yellow]Customer already inactive or no change.[/yellow]"
            )
            return
        console.print(
            f"[green]Deactivated customer id={customer['id']}.[/green]"
        )

    @customer_group.command("link-bike")
    @click.argument("customer_identifier")
    @click.option("--bike", "bike_identifier", required=True,
                  help="Vehicle id or model/make substring.")
    @click.option(
        "--relationship",
        type=click.Choice(
            [r.value for r in CustomerRelationship], case_sensitive=False,
        ),
        default=CustomerRelationship.OWNER.value,
    )
    def customer_link_bike(
        customer_identifier: str,
        bike_identifier: str,
        relationship: str,
    ) -> None:
        """Link a bike to a customer with the given relationship."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        bike = _resolve_bike_slug_or_id(bike_identifier)
        customer_bikes_repo.link_customer_bike(
            customer["id"], bike["id"],
            relationship=CustomerRelationship(relationship),
        )
        console.print(
            f"[green]Linked bike id={bike['id']} to customer id={customer['id']} "
            f"as {relationship!r}.[/green]"
        )

    @customer_group.command("unlink-bike")
    @click.argument("customer_identifier")
    @click.option("--bike", "bike_identifier", required=True)
    @click.option(
        "--relationship",
        type=click.Choice(
            [r.value for r in CustomerRelationship], case_sensitive=False,
        ),
        default=CustomerRelationship.OWNER.value,
    )
    def customer_unlink_bike(
        customer_identifier: str,
        bike_identifier: str,
        relationship: str,
    ) -> None:
        """Unlink a bike from a customer."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        bike = _resolve_bike_slug_or_id(bike_identifier)
        ok = customer_bikes_repo.unlink_customer_bike(
            customer["id"], bike["id"],
            relationship=CustomerRelationship(relationship),
        )
        if not ok:
            raise click.ClickException(
                f"No {relationship!r} link found between customer "
                f"id={customer['id']} and bike id={bike['id']}."
            )
        console.print(
            f"[green]Unlinked bike id={bike['id']} from customer "
            f"id={customer['id']}.[/green]"
        )

    @customer_group.command("bikes")
    @click.argument("customer_identifier")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def customer_bikes(
        customer_identifier: str, as_json: bool,
    ) -> None:
        """List bikes linked to a customer."""
        console = get_console()
        init_db()
        customer = _resolve_customer_identifier(customer_identifier)
        bikes = customer_bikes_repo.list_bikes_for_customer(customer["id"])
        if as_json:
            click.echo(_json.dumps(bikes, default=str, indent=2))
            return
        if not bikes:
            console.print(
                f"[dim]No bikes linked to {customer['name']!r}.[/dim]"
            )
            return
        table = Table(
            title=f"Bikes for {customer['name']}", show_lines=False,
        )
        table.add_column("Vehicle ID", justify="right")
        table.add_column("Make")
        table.add_column("Model")
        table.add_column("Year", justify="right")
        table.add_column("Relationship")
        for b in bikes:
            table.add_row(
                str(b.get("vehicle_id", b.get("id", "?"))),
                str(b.get("make", "?")),
                str(b.get("model", "?")),
                str(b.get("year", "?")),
                str(b.get("relationship", "?")),
            )
        console.print(table)

    # -----------------------------------------------------------------
    # shop intake {create, list, show, update, close, reopen, open-for-bike}
    # -----------------------------------------------------------------

    @shop_group.group("intake")
    def intake_group() -> None:
        """Log and manage bike intake visits."""

    @intake_group.command("create")
    @click.option("--shop", "shop_identifier", default=None,
                  help="Shop id or name (defaults to only active shop).")
    @click.option("--customer", "customer_identifier", required=True,
                  help="Customer id, name, or email.")
    @click.option("--bike", "bike_identifier", required=True,
                  help="Vehicle id or model/make substring.")
    @click.option("--mileage", type=int, default=None,
                  help="Mileage at intake (optional).")
    @click.option("--notes", default=None,
                  help="Reported problems freetext.")
    def intake_create(
        shop_identifier: Optional[str],
        customer_identifier: str,
        bike_identifier: str,
        mileage: Optional[int],
        notes: Optional[str],
    ) -> None:
        """Log a new intake visit."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        customer = _resolve_customer_identifier(customer_identifier)
        bike = _resolve_bike_slug_or_id(bike_identifier)

        # UX guard: warn if this bike is already checked in.
        already_open = list_open_for_bike(bike["id"])
        if already_open:
            ids = ", ".join(str(x["id"]) for x in already_open)
            console.print(
                f"[yellow]Warning: bike id={bike['id']} already has "
                f"{len(already_open)} open intake(s) (ids={ids}).[/yellow]"
            )

        try:
            intake_id = create_intake(
                shop_id=shop["id"],
                customer_id=customer["id"],
                vehicle_id=bike["id"],
                reported_problems=notes,
                mileage_at_intake=mileage,
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        row = get_intake(intake_id)
        assert row is not None
        console.print(f"[green]Created intake id={intake_id}.[/green]")
        _render_intake_panel(console, row)

    @intake_group.command("list")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option(
        "--status",
        type=click.Choice(list(INTAKE_STATUSES) + ["all"], case_sensitive=False),
        default="open",
    )
    @click.option("--since", default=None,
                  help="Relative offset (7d/24h/30m) or ISO timestamp.")
    @click.option("--limit", type=int, default=50)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def intake_list(
        shop_identifier: Optional[str],
        status: str,
        since: Optional[str],
        limit: int,
        as_json: bool,
    ) -> None:
        """List intake visits (default: open queue)."""
        console = get_console()
        init_db()
        shop_id: Optional[int] = None
        if shop_identifier is not None:
            shop = _resolve_shop_identifier(shop_identifier)
            assert shop is not None
            shop_id = shop["id"]
        filter_status: Optional[str] = (
            None if status.lower() == "all" else status.lower()
        )
        rows = list_intakes(
            shop_id=shop_id, status=filter_status, since=since, limit=limit,
        )
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No intakes match filters.[/dim]")
            return
        table = Table(
            title=f"Intakes ({filter_status or 'all'})", show_lines=False,
        )
        table.add_column("ID", justify="right")
        table.add_column("Intake at")
        table.add_column("Shop")
        table.add_column("Customer")
        table.add_column("Bike")
        table.add_column("Status")
        for r in rows:
            bike_label = " ".join(
                str(b) for b in (
                    r.get("vehicle_year"),
                    r.get("vehicle_make"),
                    r.get("vehicle_model"),
                ) if b
            )
            table.add_row(
                str(r["id"]),
                str(r.get("intake_at", "?")),
                str(r.get("shop_name", "?")),
                str(r.get("customer_name", "?")),
                bike_label or "?",
                str(r.get("status", "?")),
            )
        console.print(table)

    @intake_group.command("show")
    @click.argument("intake_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def intake_show(intake_id: int, as_json: bool) -> None:
        """Show one intake visit."""
        console = get_console()
        init_db()
        row = get_intake(intake_id)
        if row is None:
            raise click.ClickException(f"intake not found: id={intake_id}")
        if as_json:
            click.echo(_json.dumps(row, default=str, indent=2))
            return
        _render_intake_panel(console, row)

    @intake_group.command("update")
    @click.argument("intake_id", type=int)
    @click.option("--mileage", type=int, default=None)
    @click.option("--notes", default=None)
    def intake_update_cmd(
        intake_id: int,
        mileage: Optional[int],
        notes: Optional[str],
    ) -> None:
        """Update mileage or reported_problems on an intake."""
        console = get_console()
        init_db()
        updates: dict = {}
        if mileage is not None:
            updates["mileage_at_intake"] = mileage
        if notes is not None:
            updates["reported_problems"] = notes
        if not updates:
            raise click.ClickException(
                "Nothing to update. Pass --mileage or --notes."
            )
        try:
            update_intake(intake_id, updates)
        except (IntakeNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        row = get_intake(intake_id)
        assert row is not None
        console.print(f"[green]Updated intake id={intake_id}.[/green]")
        _render_intake_panel(console, row)

    @intake_group.command("close")
    @click.argument("intake_id", type=int)
    @click.option(
        "--reason",
        type=click.Choice(INTAKE_CLOSE_REASONS, case_sensitive=False),
        default="completed",
    )
    def intake_close(intake_id: int, reason: str) -> None:
        """Close an intake visit (open → closed)."""
        console = get_console()
        init_db()
        try:
            close_intake(intake_id, close_reason=reason.lower())
        except (IntakeAlreadyClosedError, IntakeNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Closed intake id={intake_id} (reason={reason}).[/green]"
        )

    @intake_group.command("cancel")
    @click.argument("intake_id", type=int)
    @click.option(
        "--reason",
        type=click.Choice(INTAKE_CLOSE_REASONS, case_sensitive=False),
        default="customer-withdrew",
    )
    def intake_cancel(intake_id: int, reason: str) -> None:
        """Cancel an intake visit (open → cancelled)."""
        console = get_console()
        init_db()
        try:
            cancel_intake(intake_id, reason=reason.lower())
        except (IntakeAlreadyClosedError, IntakeNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Cancelled intake id={intake_id} (reason={reason}).[/green]"
        )

    @intake_group.command("reopen")
    @click.argument("intake_id", type=int)
    @click.option("--yes", is_flag=True, default=False,
                  help="Skip confirmation prompt.")
    def intake_reopen(intake_id: int, yes: bool) -> None:
        """Reopen a closed/cancelled intake visit."""
        console = get_console()
        init_db()
        row = get_intake(intake_id)
        if row is None:
            raise click.ClickException(f"intake not found: id={intake_id}")
        if row["status"] == "open":
            console.print("[yellow]Intake is already open.[/yellow]")
            return
        if not yes:
            click.confirm(
                f"Really reopen intake id={intake_id} (was {row['status']!r})?",
                abort=True,
            )
        try:
            reopen_intake(intake_id)
        except IntakeNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[green]Reopened intake id={intake_id}.[/green]")

    @intake_group.command("open-for-bike")
    @click.argument("bike_identifier")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def intake_open_for_bike(
        bike_identifier: str, as_json: bool,
    ) -> None:
        """Show open intakes currently logged for a given bike."""
        console = get_console()
        init_db()
        bike = _resolve_bike_slug_or_id(bike_identifier)
        rows = list_open_for_bike(bike["id"])
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print(
                f"[dim]No open intakes for bike id={bike['id']}.[/dim]"
            )
            return
        table = Table(
            title=f"Open intakes for bike id={bike['id']}", show_lines=False,
        )
        table.add_column("ID", justify="right")
        table.add_column("Intake at")
        table.add_column("Shop")
        table.add_column("Customer")
        for r in rows:
            table.add_row(
                str(r["id"]),
                str(r.get("intake_at", "?")),
                str(r.get("shop_name", "?")),
                str(r.get("customer_name", "?")),
            )
        console.print(table)

    # -----------------------------------------------------------------
    # shop work-order {create, list, show, update, start, pause, resume,
    #                  complete, cancel, reopen, assign, unassign}
    # -----------------------------------------------------------------

    @shop_group.group("work-order")
    def work_order_group() -> None:
        """Create and manage work orders (the mechanic's unit of work)."""

    @work_order_group.command("create")
    @click.option("--intake", "intake_identifier", default=None, type=int,
                  help="Existing intake visit id; auto-fills shop/customer/bike.")
    @click.option("--shop", "shop_identifier", default=None,
                  help="Required when --intake is not provided.")
    @click.option("--customer", "customer_identifier", default=None,
                  help="Required when --intake is not provided.")
    @click.option("--bike", "bike_identifier", default=None,
                  help="Required when --intake is not provided.")
    @click.option("--title", required=True)
    @click.option("--description", default=None)
    @click.option("--priority", type=click.IntRange(1, 5), default=3)
    @click.option("--estimated-hours", "estimated_hours",
                  type=float, default=None)
    @click.option("--parts-cost-cents", "estimated_parts_cost_cents",
                  type=int, default=None,
                  help="Estimated parts cost in cents (optional).")
    @click.option("--mechanic", "mechanic_user_id", type=int, default=None,
                  help="User id of the assigned mechanic (optional).")
    def wo_create(
        intake_identifier: Optional[int],
        shop_identifier: Optional[str],
        customer_identifier: Optional[str],
        bike_identifier: Optional[str],
        title: str,
        description: Optional[str],
        priority: int,
        estimated_hours: Optional[float],
        estimated_parts_cost_cents: Optional[int],
        mechanic_user_id: Optional[int],
    ) -> None:
        """Create a new work order (starts in draft status)."""
        console = get_console()
        init_db()

        if intake_identifier is not None:
            intake = get_intake(intake_identifier)
            if intake is None:
                raise click.ClickException(
                    f"Intake not found: id={intake_identifier}"
                )
            direct_args = any([
                shop_identifier, customer_identifier, bike_identifier,
            ])
            if direct_args:
                raise click.ClickException(
                    "--intake is mutually exclusive with "
                    "--shop/--customer/--bike."
                )
            shop_id = intake["shop_id"]
            customer_id = intake["customer_id"]
            vehicle_id = intake["vehicle_id"]
        else:
            if not (shop_identifier and customer_identifier and bike_identifier):
                raise click.ClickException(
                    "Without --intake, all of --shop, --customer, --bike "
                    "are required."
                )
            shop = _resolve_shop_identifier(shop_identifier)
            customer = _resolve_customer_identifier(customer_identifier)
            bike = _resolve_bike_slug_or_id(bike_identifier)
            shop_id = shop["id"]
            customer_id = customer["id"]
            vehicle_id = bike["id"]

        try:
            wo_id = create_work_order(
                shop_id=shop_id,
                vehicle_id=vehicle_id,
                customer_id=customer_id,
                title=title,
                description=description,
                priority=priority,
                estimated_hours=estimated_hours,
                estimated_parts_cost_cents=estimated_parts_cost_cents,
                intake_visit_id=intake_identifier,
                assigned_mechanic_user_id=mechanic_user_id,
            )
        except (ValueError, WorkOrderFKError) as e:
            raise click.ClickException(str(e)) from e
        row = get_work_order(wo_id)
        assert row is not None
        console.print(f"[green]Created work order id={wo_id}.[/green]")
        _render_work_order_panel(console, row)

    @work_order_group.command("list")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--bike", "bike_identifier", default=None)
    @click.option("--customer", "customer_identifier", default=None)
    @click.option("--mechanic", "mechanic_user_id", type=int, default=None)
    @click.option("--intake", "intake_visit_id", type=int, default=None)
    @click.option(
        "--status",
        type=click.Choice(list(WORK_ORDER_STATUSES) + ["all"],
                          case_sensitive=False),
        default=None,
        help="Single status filter; 'all' includes terminal.",
    )
    @click.option("--priority", type=click.IntRange(1, 5), default=None)
    @click.option("--since", default=None,
                  help="Relative offset (7d/24h/30m) or ISO timestamp.")
    @click.option("--limit", type=int, default=50)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def wo_list(
        shop_identifier: Optional[str],
        bike_identifier: Optional[str],
        customer_identifier: Optional[str],
        mechanic_user_id: Optional[int],
        intake_visit_id: Optional[int],
        status: Optional[str],
        priority: Optional[int],
        since: Optional[str],
        limit: int,
        as_json: bool,
    ) -> None:
        """List work orders (default: exclude terminal completed/cancelled)."""
        console = get_console()
        init_db()
        shop_id: Optional[int] = None
        vehicle_id: Optional[int] = None
        customer_id: Optional[int] = None
        if shop_identifier is not None:
            shop = _resolve_shop_identifier(shop_identifier)
            assert shop is not None
            shop_id = shop["id"]
        if bike_identifier is not None:
            vehicle_id = _resolve_bike_slug_or_id(bike_identifier)["id"]
        if customer_identifier is not None:
            customer_id = _resolve_customer_identifier(
                customer_identifier,
            )["id"]
        rows = list_work_orders(
            shop_id=shop_id,
            vehicle_id=vehicle_id,
            customer_id=customer_id,
            assigned_mechanic_user_id=mechanic_user_id,
            intake_visit_id=intake_visit_id,
            status=status.lower() if status else None,
            priority=priority,
            since=since,
            limit=limit,
        )
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No work orders match filters.[/dim]")
            return
        table = Table(
            title=f"Work orders ({status or 'active'})", show_lines=False,
        )
        table.add_column("ID", justify="right")
        table.add_column("P", justify="right")
        table.add_column("Status")
        table.add_column("Title")
        table.add_column("Shop")
        table.add_column("Customer")
        table.add_column("Bike")
        table.add_column("Mechanic")
        for r in rows:
            bike_label = " ".join(
                str(b) for b in (
                    r.get("vehicle_year"),
                    r.get("vehicle_make"),
                    r.get("vehicle_model"),
                ) if b
            )
            table.add_row(
                str(r["id"]),
                str(r.get("priority", "?")),
                str(r.get("status", "?")),
                str(r.get("title", "?")),
                str(r.get("shop_name", "?")),
                str(r.get("customer_name", "?")),
                bike_label or "?",
                str(r.get("assigned_mechanic_name") or "—"),
            )
        console.print(table)

    @work_order_group.command("show")
    @click.argument("wo_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def wo_show(wo_id: int, as_json: bool) -> None:
        """Show one work order."""
        console = get_console()
        init_db()
        row = get_work_order(wo_id)
        if row is None:
            raise click.ClickException(f"work order not found: id={wo_id}")
        if as_json:
            click.echo(_json.dumps(row, default=str, indent=2))
            return
        _render_work_order_panel(console, row)

    @work_order_group.command("update")
    @click.argument("wo_id", type=int)
    @click.option("--set", "set_pairs", multiple=True,
                  help="Repeated KEY=VALUE updates, e.g. --set priority=1.")
    def wo_update(wo_id: int, set_pairs: tuple[str, ...]) -> None:
        """Update whitelisted fields on a work order.

        Allowed keys: title, description, priority, estimated_hours,
        estimated_parts_cost_cents, actual_hours.
        """
        console = get_console()
        init_db()
        if not set_pairs:
            raise click.ClickException(
                "No updates specified. Pass one or more --set KEY=VALUE."
            )
        updates = _parse_set_pairs(set_pairs)
        try:
            changed = update_work_order(wo_id, updates)
        except (WorkOrderNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        if not changed:
            console.print(
                "[yellow]No updatable fields recognized in --set payload.[/yellow]"
            )
            return
        row = get_work_order(wo_id)
        assert row is not None
        console.print(f"[green]Updated work order id={wo_id}.[/green]")
        _render_work_order_panel(console, row)

    @work_order_group.command("start")
    @click.argument("wo_id", type=int)
    def wo_start(wo_id: int) -> None:
        """Transition a work order to in_progress.

        Works from both 'open' (initial start) and 'on_hold' (resume).
        For an 'on_hold' order you can also use `resume` for clarity.
        """
        console = get_console()
        init_db()
        row = get_work_order(wo_id)
        if row is None:
            raise click.ClickException(f"work order not found: id={wo_id}")
        if row["status"] == "draft":
            # Auto-open when starting a draft. Mechanic convenience —
            # one less click from intake to in-progress.
            try:
                open_work_order(wo_id)
            except (InvalidWorkOrderTransition, WorkOrderNotFoundError) as e:
                raise click.ClickException(str(e)) from e
        try:
            start_work(wo_id)
        except (InvalidWorkOrderTransition, WorkOrderNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[green]Started work order id={wo_id}.[/green]")

    @work_order_group.command("pause")
    @click.argument("wo_id", type=int)
    @click.option("--reason", default=None,
                  help="Why the work is paused (e.g. 'parts back-ordered').")
    def wo_pause(wo_id: int, reason: Optional[str]) -> None:
        """Transition in_progress → on_hold."""
        console = get_console()
        init_db()
        if reason is None:
            reason = click.prompt(
                "Reason (optional, press Enter to skip)",
                default="", show_default=False,
            ) or None
        try:
            pause_work(wo_id, reason=reason)
        except (InvalidWorkOrderTransition, WorkOrderNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[yellow]Paused work order id={wo_id}.[/yellow]")

    @work_order_group.command("resume")
    @click.argument("wo_id", type=int)
    def wo_resume(wo_id: int) -> None:
        """Transition on_hold → in_progress (alias for start on paused)."""
        console = get_console()
        init_db()
        try:
            resume_work(wo_id)
        except (InvalidWorkOrderTransition, WorkOrderNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[green]Resumed work order id={wo_id}.[/green]")

    @work_order_group.command("complete")
    @click.argument("wo_id", type=int)
    @click.option("--actual-hours", "actual_hours", type=float, default=None,
                  help="Actual hours worked (optional, persisted if given).")
    def wo_complete(
        wo_id: int, actual_hours: Optional[float],
    ) -> None:
        """Transition in_progress → completed."""
        console = get_console()
        init_db()
        try:
            complete_work_order(wo_id, actual_hours=actual_hours)
        except (InvalidWorkOrderTransition, WorkOrderNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[blue]Completed work order id={wo_id}.[/blue]"
        )

    @work_order_group.command("cancel")
    @click.argument("wo_id", type=int)
    @click.option("--reason", default="customer-withdrew",
                  help="Cancellation reason.")
    @click.option("--yes", is_flag=True, default=False,
                  help="Skip confirmation prompt.")
    def wo_cancel(wo_id: int, reason: str, yes: bool) -> None:
        """Transition any non-terminal status → cancelled."""
        console = get_console()
        init_db()
        row = get_work_order(wo_id)
        if row is None:
            raise click.ClickException(f"work order not found: id={wo_id}")
        if not yes:
            click.confirm(
                f"Really cancel work order id={wo_id} "
                f"(was {row['status']!r})?",
                abort=True,
            )
        try:
            cancel_work_order(wo_id, reason=reason)
        except (InvalidWorkOrderTransition, WorkOrderNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[red]Cancelled work order id={wo_id} (reason={reason}).[/red]"
        )

    @work_order_group.command("reopen")
    @click.argument("wo_id", type=int)
    @click.option("--yes", is_flag=True, default=False,
                  help="Skip confirmation prompt.")
    def wo_reopen(wo_id: int, yes: bool) -> None:
        """Transition completed|cancelled → open (clears terminal fields)."""
        console = get_console()
        init_db()
        row = get_work_order(wo_id)
        if row is None:
            raise click.ClickException(f"work order not found: id={wo_id}")
        if row["status"] == "open":
            console.print("[yellow]Work order is already open.[/yellow]")
            return
        if not yes:
            click.confirm(
                f"Really reopen work order id={wo_id} "
                f"(was {row['status']!r})? Terminal timestamps will be cleared.",
                abort=True,
            )
        try:
            reopen_work_order(wo_id)
        except (InvalidWorkOrderTransition, WorkOrderNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[green]Reopened work order id={wo_id}.[/green]")

    @work_order_group.command("assign")
    @click.argument("wo_id", type=int)
    @click.option("--mechanic", "mechanic_user_id", type=int, required=True,
                  help="User id of the mechanic to assign.")
    def wo_assign(wo_id: int, mechanic_user_id: int) -> None:
        """Assign a mechanic to a work order."""
        console = get_console()
        init_db()
        try:
            assign_mechanic(wo_id, mechanic_user_id)
        except (WorkOrderNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Assigned mechanic user_id={mechanic_user_id} to "
            f"work order id={wo_id}.[/green]"
        )

    @work_order_group.command("unassign")
    @click.argument("wo_id", type=int)
    def wo_unassign(wo_id: int) -> None:
        """Clear the assigned mechanic on a work order."""
        console = get_console()
        init_db()
        try:
            unassign_mechanic(wo_id)
        except WorkOrderNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Unassigned mechanic from work order id={wo_id}.[/green]"
        )

    @work_order_group.command("reassign")
    @click.argument("wo_id", type=int)
    @click.option("--to", "new_mechanic_id", type=int, default=None,
                  help="Target mechanic user id (omit to unassign).")
    @click.option("--by", "assigned_by_user_id", type=int, default=None)
    @click.option("--reason", default=None)
    def wo_reassign_cmd(
        wo_id, new_mechanic_id, assigned_by_user_id, reason,
    ):
        """Reassign a work order and log to the assignment history."""
        console = get_console()
        init_db()
        try:
            assignment_id = reassign_work_order(
                wo_id,
                new_mechanic_user_id=new_mechanic_id,
                assigned_by_user_id=assigned_by_user_id,
                reason=reason,
            )
        except (
            WorkOrderNotFoundError, InvalidWorkOrderTransition,
            MechanicNotInShopError,
        ) as e:
            raise click.ClickException(str(e)) from e
        target = (
            f"user id={new_mechanic_id}" if new_mechanic_id is not None
            else "(unassigned)"
        )
        console.print(
            f"[green]WO #{wo_id} reassigned to {target} "
            f"(assignment #{assignment_id}).[/green]"
        )

    @work_order_group.command("assignments")
    @click.argument("wo_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def wo_assignments_cmd(wo_id, as_json):
        """Show the full assignment history for a work order."""
        console = get_console()
        init_db()
        rows = list_work_order_assignments(wo_id)
        if as_json:
            click.echo(_json.dumps(
                [r.model_dump() for r in rows], default=str, indent=2,
            ))
            return
        if not rows:
            console.print(
                f"[dim]No assignment history for WO #{wo_id}.[/dim]"
            )
            return
        table = Table(
            title=f"Assignment history — WO #{wo_id}", show_lines=False,
        )
        table.add_column("ID", justify="right")
        table.add_column("Mechanic")
        table.add_column("Assigned")
        table.add_column("Unassigned")
        table.add_column("By")
        table.add_column("Reason")
        for r in rows:
            mech = (
                r.mechanic_username
                or (f"user#{r.mechanic_user_id}"
                    if r.mechanic_user_id is not None else "—")
            )
            table.add_row(
                str(r.id), mech,
                str(r.assigned_at),
                str(r.unassigned_at or "—"),
                str(r.assigned_by_user_id or "—"),
                str(r.reason or "—"),
            )
        console.print(table)

    # -----------------------------------------------------------------
    # shop issue {add, list, show, update, resolve, reopen, mark-duplicate,
    #             mark-wontfix, categorize, link-dtc, link-symptom, stats}
    # -----------------------------------------------------------------

    @shop_group.group("issue")
    def issue_group() -> None:
        """Structured issue logging: categorize, triage, resolve."""

    SEVERITY_COLORS = {
        "critical": "bold red", "high": "yellow",
        "medium": "white", "low": "dim",
    }

    def _render_issue_panel(console, issue: dict) -> None:
        sev = issue.get("severity", "medium")
        sev_style = SEVERITY_COLORS.get(sev, "white")
        status = issue.get("status", "open")
        status_color = {
            "open": "green", "resolved": "blue",
            "duplicate": "magenta", "wont_fix": "red",
        }.get(status, "white")
        lines: list[str] = []
        lines.append(
            f"[bold]Issue id={issue['id']}:[/bold] "
            f"{issue.get('title', '?')}  "
            f"[{status_color}]{status.upper()}[/{status_color}]  "
            f"[{sev_style}]{sev.upper()}[/{sev_style}]"
        )
        lines.append(f"Category: {issue.get('category', '?')}")
        lines.append(
            f"Work order: id={issue.get('work_order_id')} "
            f"({issue.get('work_order_title', '?')})"
        )
        bike_label = " ".join(
            str(b) for b in (
                issue.get("vehicle_year"),
                issue.get("vehicle_make"),
                issue.get("vehicle_model"),
            ) if b
        )
        if bike_label:
            lines.append(f"Bike: {bike_label}")
        if issue.get("customer_name"):
            lines.append(f"Customer: {issue['customer_name']}")
        if issue.get("shop_name"):
            lines.append(f"Shop: {issue['shop_name']}")
        if issue.get("linked_dtc_code"):
            dtc_desc = issue.get("linked_dtc_description")
            label = (
                f"{issue['linked_dtc_code']} — {dtc_desc}"
                if dtc_desc else f"{issue['linked_dtc_code']} (unknown code)"
            )
            lines.append(f"Linked DTC: {label}")
        if issue.get("linked_symptom_id"):
            sym_name = issue.get("linked_symptom_name") or "?"
            lines.append(
                f"Linked symptom: id={issue['linked_symptom_id']} ({sym_name})"
            )
        if issue.get("duplicate_of_issue_id"):
            dup_title = issue.get("duplicate_of_title") or "?"
            lines.append(
                f"Duplicate of: id={issue['duplicate_of_issue_id']} ({dup_title})"
            )
        if issue.get("description"):
            lines.append(f"\nDescription:\n  {issue['description']}")
        lines.append(f"\nReported: {issue.get('reported_at', '?')}")
        if issue.get("resolved_at"):
            lines.append(f"Resolved: {issue['resolved_at']}")
        if issue.get("resolution_notes"):
            lines.append(f"Resolution notes:\n  {issue['resolution_notes']}")
        console.print(Panel("\n".join(lines), title="Issue"))

    @issue_group.command("add")
    @click.option("--work-order", "work_order_id", type=int, required=True)
    @click.option("--title", required=True)
    @click.option("--description", default=None)
    @click.option(
        "--category",
        type=click.Choice(list(ISSUE_CATEGORIES), case_sensitive=False),
        default="other",
    )
    @click.option(
        "--severity",
        type=click.Choice(list(ISSUE_SEVERITIES), case_sensitive=False),
        default="medium",
    )
    @click.option("--dtc", "linked_dtc_code", default=None)
    @click.option("--symptom", "linked_symptom_id", type=int, default=None)
    @click.option("--session", "diagnostic_session_id", type=int, default=None)
    def issue_add(
        work_order_id, title, description, category, severity,
        linked_dtc_code, linked_symptom_id, diagnostic_session_id,
    ):
        """Add a new issue to a work order."""
        console = get_console()
        init_db()
        try:
            issue_id = create_issue(
                work_order_id=work_order_id,
                title=title,
                description=description,
                category=category.lower(),
                severity=severity.lower(),
                linked_dtc_code=linked_dtc_code,
                linked_symptom_id=linked_symptom_id,
                diagnostic_session_id=diagnostic_session_id,
            )
        except (ValueError, IssueFKError) as e:
            raise click.ClickException(str(e)) from e
        row = get_issue(issue_id)
        assert row is not None
        console.print(f"[green]Created issue id={issue_id}.[/green]")
        _render_issue_panel(console, row)

    @issue_group.command("list")
    @click.option("--work-order", "work_order_id", type=int, default=None)
    @click.option("--shop", "shop_id", type=int, default=None)
    @click.option(
        "--category",
        type=click.Choice(list(ISSUE_CATEGORIES), case_sensitive=False),
        default=None,
    )
    @click.option(
        "--severity",
        type=click.Choice(list(ISSUE_SEVERITIES), case_sensitive=False),
        default=None,
    )
    @click.option(
        "--status",
        type=click.Choice(list(ISSUE_STATUSES) + ["all"], case_sensitive=False),
        default=None,
    )
    @click.option("--vehicle", "vehicle_id", type=int, default=None)
    @click.option("--customer", "customer_id", type=int, default=None)
    @click.option("--since", default=None)
    @click.option("--limit", type=int, default=100)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def issue_list(
        work_order_id, shop_id, category, severity, status,
        vehicle_id, customer_id, since, limit, as_json,
    ):
        """List issues (default excludes terminal statuses)."""
        console = get_console()
        init_db()
        rows = list_issues(
            work_order_id=work_order_id,
            category=category.lower() if category else None,
            severity=severity.lower() if severity else None,
            status=status.lower() if status else None,
            shop_id=shop_id,
            vehicle_id=vehicle_id,
            customer_id=customer_id,
            since=since,
            limit=limit,
        )
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No issues match filters.[/dim]")
            return
        table = Table(title="Issues", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("Cat")
        table.add_column("Sev")
        table.add_column("Status")
        table.add_column("Title")
        table.add_column("WO")
        table.add_column("Reported")
        for r in rows:
            sev = r.get("severity", "medium")
            sev_style = SEVERITY_COLORS.get(sev, "white")
            table.add_row(
                str(r["id"]),
                str(r.get("category", "?")),
                f"[{sev_style}]{sev}[/{sev_style}]",
                str(r.get("status", "?")),
                str(r.get("title", "?")),
                str(r.get("work_order_id", "?")),
                str(r.get("reported_at", "?")),
            )
        console.print(table)

    @issue_group.command("show")
    @click.argument("issue_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def issue_show(issue_id, as_json):
        """Show one issue."""
        console = get_console()
        init_db()
        row = get_issue(issue_id)
        if row is None:
            raise click.ClickException(f"issue not found: id={issue_id}")
        if as_json:
            click.echo(_json.dumps(row, default=str, indent=2))
            return
        _render_issue_panel(console, row)

    @issue_group.command("update")
    @click.argument("issue_id", type=int)
    @click.option("--set", "set_pairs", multiple=True)
    def issue_update(issue_id, set_pairs):
        """Update whitelisted fields on an issue.

        Allowed: title, description, category, severity, linked_dtc_code,
        linked_symptom_id, diagnostic_session_id.
        """
        console = get_console()
        init_db()
        if not set_pairs:
            raise click.ClickException(
                "No updates specified. Pass one or more --set KEY=VALUE."
            )
        updates = _parse_set_pairs(set_pairs)
        # Coerce types for known integer fields
        for k in ("linked_symptom_id", "diagnostic_session_id"):
            if k in updates and updates[k] is not None:
                try:
                    updates[k] = int(updates[k])
                except (TypeError, ValueError) as e:
                    raise click.ClickException(
                        f"{k} must be an integer (got {updates[k]!r})"
                    ) from e
        try:
            changed = update_issue(issue_id, updates)
        except (IssueNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        if not changed:
            console.print(
                "[yellow]No updatable fields recognized in --set payload.[/yellow]"
            )
            return
        row = get_issue(issue_id)
        assert row is not None
        console.print(f"[green]Updated issue id={issue_id}.[/green]")
        _render_issue_panel(console, row)

    @issue_group.command("resolve")
    @click.argument("issue_id", type=int)
    @click.option("--notes", default=None)
    @click.option("--yes", is_flag=True, default=False)
    def issue_resolve(issue_id, notes, yes):
        """Mark an issue resolved (open → resolved)."""
        console = get_console()
        init_db()
        if not yes:
            click.confirm(
                f"Resolve issue id={issue_id}?", abort=True,
            )
        try:
            resolve_issue(issue_id, resolution_notes=notes)
        except (IssueNotFoundError, InvalidIssueTransition) as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[blue]Resolved issue id={issue_id}.[/blue]")

    @issue_group.command("reopen")
    @click.argument("issue_id", type=int)
    @click.option("--yes", is_flag=True, default=False)
    def issue_reopen(issue_id, yes):
        """Reopen a terminal issue (resolved/duplicate/wont_fix → open)."""
        console = get_console()
        init_db()
        row = get_issue(issue_id)
        if row is None:
            raise click.ClickException(f"issue not found: id={issue_id}")
        if row["status"] == "open":
            console.print("[yellow]Issue is already open.[/yellow]")
            return
        if not yes:
            click.confirm(
                f"Reopen issue id={issue_id} (was {row['status']!r})?",
                abort=True,
            )
        try:
            reopen_issue(issue_id)
        except (IssueNotFoundError, InvalidIssueTransition) as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[green]Reopened issue id={issue_id}.[/green]")

    @issue_group.command("mark-duplicate")
    @click.argument("issue_id", type=int)
    @click.option("--of", "duplicate_of_issue_id", type=int, required=True)
    @click.option("--notes", default=None)
    def issue_mark_duplicate(issue_id, duplicate_of_issue_id, notes):
        """Mark an issue as duplicate of another (open → duplicate)."""
        console = get_console()
        init_db()
        try:
            mark_duplicate_issue(
                issue_id, duplicate_of_issue_id,
                resolution_notes=notes,
            )
        except (IssueNotFoundError, InvalidIssueTransition, ValueError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[magenta]Marked issue id={issue_id} as duplicate of "
            f"id={duplicate_of_issue_id}.[/magenta]"
        )

    @issue_group.command("mark-wontfix")
    @click.argument("issue_id", type=int)
    @click.option("--notes", required=True,
                  help="REQUIRED audit-trail justification.")
    def issue_mark_wontfix(issue_id, notes):
        """Mark an issue won't-fix (open → wont_fix). Notes required."""
        console = get_console()
        init_db()
        if not notes or not notes.strip():
            raise click.ClickException(
                "--notes is required for mark-wontfix (audit-trail)."
            )
        try:
            mark_wontfix_issue(issue_id, resolution_notes=notes)
        except (IssueNotFoundError, InvalidIssueTransition, ValueError) as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[red]Marked issue id={issue_id} as wont_fix.[/red]")

    @issue_group.command("categorize")
    @click.argument("issue_id", type=int)
    @click.option(
        "--category",
        type=click.Choice(list(ISSUE_CATEGORIES), case_sensitive=False),
        required=True,
    )
    @click.option(
        "--severity",
        type=click.Choice(list(ISSUE_SEVERITIES), case_sensitive=False),
        default=None,
    )
    def issue_categorize(issue_id, category, severity):
        """Re-categorize an issue (convenience wrapper)."""
        console = get_console()
        init_db()
        sev = severity.lower() if severity else None
        try:
            categorize_issue(issue_id, category.lower(), severity=sev)
        except (IssueNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Categorized issue id={issue_id} as {category}"
            + (f"/{severity}" if severity else "") + ".[/green]"
        )

    @issue_group.command("link-dtc")
    @click.argument("issue_id", type=int)
    @click.option("--code", required=True)
    def issue_link_dtc(issue_id, code):
        """Link a DTC code to an issue (soft-validate; persist on miss)."""
        console = get_console()
        init_db()
        try:
            link_dtc(issue_id, code)
        except IssueNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Linked DTC {code} to issue id={issue_id}.[/green]"
        )

    @issue_group.command("link-symptom")
    @click.argument("issue_id", type=int)
    @click.option("--symptom", "symptom_id", type=int, required=True)
    def issue_link_symptom(issue_id, symptom_id):
        """Link a symptom to an issue (hard FK)."""
        console = get_console()
        init_db()
        try:
            link_symptom(issue_id, symptom_id)
        except (IssueNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Linked symptom id={symptom_id} to issue id={issue_id}.[/green]"
        )

    @issue_group.command("stats")
    @click.option("--work-order", "work_order_id", type=int, default=None)
    @click.option("--shop", "shop_id", type=int, default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def issue_stats_cmd(work_order_id, shop_id, as_json):
        """Show issue rollup stats."""
        console = get_console()
        init_db()
        stats = issue_stats(
            work_order_id=work_order_id, shop_id=shop_id,
        )
        if as_json:
            click.echo(_json.dumps(stats, default=str, indent=2))
            return
        console.print(Panel(
            f"Total: [bold]{stats['total']}[/bold]\n"
            f"Open: [green]{stats['open_count']}[/green]\n"
            f"[bold red]Critical open: {stats['critical_open_count']}[/bold red]",
            title="Issue stats",
        ))
        # by_status table
        t1 = Table(title="By status", show_header=True)
        t1.add_column("Status")
        t1.add_column("Count", justify="right")
        for status, n in stats["by_status"].items():
            t1.add_row(status, str(n))
        console.print(t1)
        # by_category table
        t2 = Table(title="By category", show_header=True)
        t2.add_column("Category")
        t2.add_column("Count", justify="right")
        for cat, n in stats["by_category"].items():
            t2.add_row(cat, str(n))
        console.print(t2)
        # by_severity table
        t3 = Table(title="By severity", show_header=True)
        t3.add_column("Severity")
        t3.add_column("Count", justify="right")
        for sev, n in stats["by_severity"].items():
            t3.add_row(sev, str(n))
        console.print(t3)

    # -----------------------------------------------------------------
    # shop priority {score, rescore-all, show, budget}
    # -----------------------------------------------------------------

    @shop_group.group("priority")
    def priority_group() -> None:
        """AI-ranked repair priority scoring (Phase 163)."""

    def _render_priority_score(console, ps) -> None:
        applied_color = "green" if ps.applied else "yellow"
        applied_label = (
            "[green]APPLIED[/green]" if ps.applied
            else "[yellow]LOGGED ONLY[/yellow]"
        )
        safety_label = (
            "[bold red]SAFETY-RISK[/bold red] " if ps.safety_risk else ""
        )
        cache_label = (
            "[dim](cache hit)[/dim]" if ps.cache_hit else ""
        )
        lines = [
            f"[bold]WO id={ps.wo_id}[/bold] {applied_label} {cache_label}",
            f"{safety_label}Priority: {ps.priority_before} → "
            f"[bold]{ps.priority_after}[/bold]",
            f"Confidence: {ps.confidence:.2f}",
            f"Ridability impact: {ps.ridability_impact}",
            f"\nRationale: {ps.rationale}",
            f"\nModel: {ps.ai_model}",
            f"Tokens: {ps.tokens_in} in / {ps.tokens_out} out",
            f"Cost: {ps.cost_cents}¢",
        ]
        console.print(Panel("\n".join(lines), title="Priority score"))

    @priority_group.command("score")
    @click.argument("wo_id", type=int)
    @click.option(
        "--model",
        type=click.Choice(["haiku", "sonnet"], case_sensitive=False),
        default="haiku",
    )
    @click.option(
        "--force", is_flag=True, default=False,
        help="Apply AI priority even on low confidence.",
    )
    @click.option(
        "--escalate-on-low-confidence", is_flag=True, default=False,
        help="Re-run with sonnet if first-pass confidence < 0.50.",
    )
    @click.option("--no-cache", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def priority_score_cmd(
        wo_id, model, force, escalate_on_low_confidence, no_cache, as_json,
    ):
        """Score one work order against the AI priority rubric."""
        console = get_console()
        init_db()
        try:
            ps = score_work_order(
                wo_id, model=model.lower(),
                use_cache=not no_cache,
                force=force,
                escalate_on_low_confidence=escalate_on_low_confidence,
            )
        except (PriorityScorerError, ShopNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(ps.model_dump(mode="json"), indent=2))
            return
        _render_priority_score(console, ps)

    @priority_group.command("rescore-all")
    @click.option("--shop", "shop_id", type=int, default=None)
    @click.option("--since", default=None,
                  help="Relative offset (24h/7d) or ISO timestamp.")
    @click.option("--limit", type=int, default=10)
    @click.option("--budget-cents", "budget_cents", type=int, default=50)
    @click.option(
        "--model",
        type=click.Choice(["haiku", "sonnet"], case_sensitive=False),
        default="haiku",
    )
    @click.option("--dry-run", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def priority_rescore_all_cmd(
        shop_id, since, limit, budget_cents, model, dry_run, as_json,
    ):
        """Re-score every open / in-progress / on-hold WO matching filters."""
        console = get_console()
        init_db()
        try:
            results = rescore_all_open(
                shop_id=shop_id, since=since, limit=limit,
                budget_cents=budget_cents, model=model.lower(),
                dry_run=dry_run,
            )
        except PriorityBudgetExhausted as e:
            console.print(f"[yellow]{e}[/yellow]")
            results = e.scored_so_far
        except PriorityScorerError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(
                [r.model_dump(mode="json") for r in results], indent=2,
            ))
            return
        if not results:
            console.print("[dim]No work orders matched filters.[/dim]")
            return
        table = Table(
            title=f"Priority scoring ({len(results)} WOs)",
            show_header=True,
        )
        table.add_column("WO", justify="right")
        table.add_column("P-before", justify="right")
        table.add_column("P-after", justify="right")
        table.add_column("Conf", justify="right")
        table.add_column("Safety")
        table.add_column("Applied")
        table.add_column("Cost¢", justify="right")
        for r in results:
            table.add_row(
                str(r.wo_id),
                str(r.priority_before),
                str(r.priority_after),
                f"{r.confidence:.2f}",
                "🚨" if r.safety_risk else "—",
                "✅" if r.applied else "—",
                str(r.cost_cents),
            )
        console.print(table)
        total_cost = sum(r.cost_cents for r in results)
        console.print(f"\nTotal cost: {total_cost}¢")

    @priority_group.command("show")
    @click.argument("wo_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def priority_show_cmd(wo_id, as_json):
        """Show the latest cached priority score for a WO."""
        from motodiag.shop import get_latest_priority_score
        console = get_console()
        init_db()
        row = get_latest_priority_score(wo_id)
        if row is None:
            raise click.ClickException(
                f"no priority score found for wo_id={wo_id}"
            )
        if as_json:
            click.echo(_json.dumps(row, default=str, indent=2))
            return
        lines = [
            f"[bold]WO id={wo_id}[/bold]",
            f"Priority: {row.get('priority')}",
            f"Confidence: {row.get('confidence')}",
            f"Safety risk: {row.get('safety_risk')}",
            f"Rationale: {row.get('rationale')}",
            f"Model: {row.get('ai_model')}",
            f"Tokens: {row.get('tokens_in')} in / {row.get('tokens_out')} out",
            f"Cost: {row.get('cost_cents')}¢",
            f"Generated: {row.get('generated_at')}",
        ]
        console.print(Panel("\n".join(lines), title="Cached priority score"))

    @priority_group.command("budget")
    @click.option("--from", "since", default=None,
                  help="ISO date or relative offset (e.g. '30d').")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def priority_budget_cmd(since, as_json):
        """Sum cumulative priority-scoring spend."""
        console = get_console()
        init_db()
        rollup = priority_budget(since=since)
        if as_json:
            click.echo(_json.dumps(rollup, indent=2))
            return
        console.print(Panel(
            f"Calls: {rollup['calls']}\n"
            f"Tokens in: {rollup['tokens_in']:,}\n"
            f"Tokens out: {rollup['tokens_out']:,}\n"
            f"Cost: {rollup['cost_cents']}¢ "
            f"(${rollup['cost_cents']/100:.2f})",
            title="Priority scoring budget"
            + (f" (since {since})" if since else ""),
        ))

    # -----------------------------------------------------------------
    # shop triage {queue, next, flag-urgent, skip, weights}
    # -----------------------------------------------------------------

    @shop_group.group("triage")
    def triage_group() -> None:
        """Automated triage queue — 'what to fix first' ranking."""

    def _render_triage_table(console, items, status_label: str) -> None:
        table = Table(
            title=f"Triage queue ({status_label}, {len(items)} WOs)",
            show_lines=False,
        )
        table.add_column("Rank", justify="right")
        table.add_column("WO", justify="right")
        table.add_column("Pri", justify="right")
        table.add_column("Title")
        table.add_column("Bike")
        table.add_column("Customer")
        table.add_column("Wait")
        table.add_column("Parts")
        table.add_column("Mech")
        table.add_column("Flag")
        for item in items:
            wo = item.work_order
            pri = wo.get("priority", 3)
            pri_color = {1: "bold red", 2: "red", 3: "yellow", 4: "dim", 5: "dim"}
            pri_style = pri_color.get(pri, "white")
            bike = " ".join(
                str(b) for b in (
                    wo.get("vehicle_year"),
                    wo.get("vehicle_make"),
                    wo.get("vehicle_model"),
                ) if b
            )
            wait_label = (
                f"{int(item.wait_hours / 24)}d"
                if item.wait_hours >= 24
                else f"{int(item.wait_hours)}h"
            )
            if item.parts_ready:
                parts_label = "[green]ready[/green]"
            else:
                parts_label = (
                    f"[yellow]{len(item.parts_missing_skus)} missing[/yellow]"
                )
            flag_label = ""
            if item.triage_flag == "urgent":
                flag_label = "[bold red]URGENT[/bold red]"
            elif item.triage_skip_reason:
                flag_label = f"[dim]skipped ({item.triage_skip_reason})[/dim]"
            from motodiag.shop.triage_queue import _parse_triage_markers
            clean = _parse_triage_markers(wo.get("description"))[
                "clean_description"
            ]
            title = wo.get("title", "?")
            if clean and clean != wo.get("description", ""):
                title = title  # display original WO title (markers strip from description, not title)
            table.add_row(
                str(item.rank),
                f"#{wo['id']}",
                f"[{pri_style}]{pri}[/{pri_style}]",
                str(title)[:40],
                bike,
                str(wo.get("customer_name", "?")),
                wait_label,
                parts_label,
                str(wo.get("assigned_mechanic_name") or "—"),
                flag_label,
            )
        console.print(table)

    @triage_group.command("queue")
    @click.option("--shop", "shop_id", type=int, default=None)
    @click.option("--mechanic", "assigned_mechanic_user_id", type=int, default=None)
    @click.option("--top", type=int, default=10)
    @click.option("--include-terminal", is_flag=True, default=False)
    @click.option(
        "--assume-parts-available/--require-parts",
        default=True,
        help="When Phase 165 absent, treat parts as ready (default).",
    )
    @click.option("--json", "as_json", is_flag=True, default=False)
    def triage_queue_cmd(
        shop_id, assigned_mechanic_user_id, top,
        include_terminal, assume_parts_available, as_json,
    ):
        """Print the ranked triage queue."""
        console = get_console()
        init_db()
        items = build_triage_queue(
            shop_id=shop_id,
            assigned_mechanic_user_id=assigned_mechanic_user_id,
            include_terminal=include_terminal,
            top=top,
            assumed_parts_available=assume_parts_available,
        )
        if as_json:
            payload = [item.model_dump(mode="json") for item in items]
            click.echo(_json.dumps(payload, default=str, indent=2))
            return
        if not items:
            console.print("[dim]No work orders match filters.[/dim]")
            return
        _render_triage_table(
            console, items, "open + in_progress + on_hold",
        )

    @triage_group.command("next")
    @click.option("--shop", "shop_id", type=int, default=None)
    def triage_next_cmd(shop_id):
        """Show the single highest-ranked WO."""
        console = get_console()
        init_db()
        items = build_triage_queue(shop_id=shop_id, top=1)
        if not items:
            console.print("[yellow]No open work orders.[/yellow]")
            raise click.exceptions.Exit(1)
        item = items[0]
        wo = item.work_order
        bike = " ".join(
            str(b) for b in (
                wo.get("vehicle_year"),
                wo.get("vehicle_make"),
                wo.get("vehicle_model"),
            ) if b
        )
        flag_line = ""
        if item.triage_flag == "urgent":
            flag_line = "\n[bold red]URGENT-FLAGGED[/bold red]"
        lines = [
            f"[bold]Pull this bike in next: WO #{wo['id']}[/bold]",
            f"Title: {wo.get('title', '?')}",
            f"Priority: {wo.get('priority', '?')}",
            f"Bike: {bike}",
            f"Customer: {wo.get('customer_name', '?')}",
            f"Wait: {item.wait_hours:.1f}h",
            f"Parts ready: {item.parts_ready}",
            f"Triage score: {item.triage_score:.1f}{flag_line}",
        ]
        console.print(Panel("\n".join(lines), title="Next up"))

    @triage_group.command("flag-urgent")
    @click.argument("wo_id", type=int)
    def triage_flag_urgent_cmd(wo_id):
        """Force a WO to the top — sets priority=1 + [TRIAGE_URGENT] marker."""
        console = get_console()
        init_db()
        try:
            flag_urgent(wo_id)
        except WorkOrderNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[bold red]Flagged WO id={wo_id} as URGENT.[/bold red] "
            "Priority set to 1."
        )

    @triage_group.command("skip")
    @click.argument("wo_id", type=int)
    @click.option("--reason", default="deferred",
                  help="Skip reason. Empty string clears the skip.")
    def triage_skip_cmd(wo_id, reason):
        """Soft-demote WO via [TRIAGE_SKIP: reason] marker."""
        console = get_console()
        init_db()
        try:
            skip_work_order(wo_id, reason)
        except WorkOrderNotFoundError as e:
            raise click.ClickException(str(e)) from e
        if not reason or not reason.strip():
            console.print(
                f"[green]Cleared skip on WO id={wo_id}.[/green]"
            )
        else:
            console.print(
                f"[yellow]Skipped WO id={wo_id} (reason={reason!r}).[/yellow]"
            )

    @triage_group.command("weights")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--set", "set_pairs", multiple=True,
                  help="Repeated KEY=VALUE updates (e.g. --set wait_weight=2.5).")
    @click.option("--reset", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def triage_weights_cmd(shop_id, set_pairs, reset, as_json):
        """Show or tune per-shop triage weights."""
        console = get_console()
        init_db()
        if reset:
            reset_triage_weights(shop_id)
            console.print(
                f"[green]Reset triage weights for shop id={shop_id} to defaults.[/green]"
            )
        if set_pairs:
            current = load_triage_weights(shop_id).model_dump()
            for pair in set_pairs:
                if "=" not in pair:
                    raise click.ClickException(
                        f"--set expects KEY=VALUE (got {pair!r})"
                    )
                key, _, value = pair.partition("=")
                key = key.strip()
                try:
                    current[key] = float(value)
                except ValueError as e:
                    raise click.ClickException(
                        f"weight value must be numeric (got {value!r})"
                    ) from e
            try:
                weights = ShopTriageWeights(**current)
            except Exception as e:
                raise click.ClickException(str(e)) from e
            save_triage_weights(shop_id, weights)
            console.print(
                f"[green]Updated triage weights for shop id={shop_id}.[/green]"
            )
        weights = load_triage_weights(shop_id)
        if as_json:
            click.echo(_json.dumps(weights.model_dump(), indent=2))
            return
        console.print(Panel(
            "\n".join(
                f"{k}: {v}" for k, v in weights.model_dump().items()
            ),
            title=f"Triage weights for shop id={shop_id}",
        ))

    # -----------------------------------------------------------------
    # shop parts-needs {add, list, consolidate, mark-ordered, mark-received,
    #                   requisition {create, list, show}}
    # -----------------------------------------------------------------

    @shop_group.group("parts-needs")
    def parts_needs_group() -> None:
        """Parts aggregation: link parts to WOs + roll up shopping lists."""

    @parts_needs_group.command("add")
    @click.argument("wo_id", type=int)
    @click.option("--part-id", "-p", required=True, type=int)
    @click.option("--qty", "-q", type=int, default=1, show_default=True)
    @click.option("--unit-cost", "unit_cost_override", type=int, default=None,
                  help="Override catalog unit cost in cents (nullable).")
    @click.option("--notes", default=None)
    def pn_add(wo_id, part_id, qty, unit_cost_override, notes):
        """Add a part line to a work order; recomputes parent WO cost."""
        console = get_console()
        init_db()
        try:
            wop_id = add_part_to_work_order(
                wo_id, part_id, quantity=qty,
                unit_cost_override=unit_cost_override, notes=notes,
            )
        except (PartNotInCatalogError, WorkOrderNotFoundError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Added work_order_part id={wop_id} "
            f"(wo={wo_id}, part={part_id}, qty={qty}).[/green]"
        )

    @parts_needs_group.command("list")
    @click.option("--wo", "wo_id", type=int, default=None)
    @click.option("--shop", "shop_id", type=int, default=None)
    @click.option("--include-cancelled", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def pn_list(wo_id, shop_id, include_cancelled, as_json):
        """List parts lines for a WO or aggregated across a shop."""
        console = get_console()
        init_db()
        if (wo_id is None) == (shop_id is None):
            raise click.ClickException(
                "Pass exactly one of --wo or --shop."
            )
        if wo_id is not None:
            rows = list_parts_for_wo(
                wo_id, include_cancelled=include_cancelled,
            )
            if as_json:
                click.echo(_json.dumps(rows, default=str, indent=2))
                return
            if not rows:
                console.print(
                    f"[dim]No parts on WO id={wo_id}.[/dim]"
                )
                return
            table = Table(
                title=f"Parts on WO id={wo_id}", show_lines=False,
            )
            table.add_column("WOP", justify="right")
            table.add_column("Part")
            table.add_column("Qty", justify="right")
            table.add_column("Unit ¢", justify="right")
            table.add_column("Subtotal ¢", justify="right")
            table.add_column("Status")
            for r in rows:
                table.add_row(
                    str(r["id"]),
                    f"{r.get('part_slug', '?')} (id={r['part_id']})",
                    str(r["quantity"]),
                    str(r["unit_cost_cents"]),
                    str(r["line_subtotal_cents"]),
                    r["status"],
                )
            console.print(table)
        else:
            consolidated = list_parts_for_shop_open_wos(shop_id)
            if as_json:
                payload = [c.model_dump() for c in consolidated]
                click.echo(_json.dumps(payload, default=str, indent=2))
                return
            if not consolidated:
                console.print(
                    f"[dim]No active parts needs for shop id={shop_id}.[/dim]"
                )
                return
            table = Table(
                title=f"Consolidated parts needs (shop id={shop_id})",
                show_lines=False,
            )
            table.add_column("Part")
            table.add_column("Qty", justify="right")
            table.add_column("WO ids")
            table.add_column("Est ¢", justify="right")
            table.add_column("OEM ¢", justify="right")
            table.add_column("Aftermarket ¢", justify="right")
            for c in consolidated:
                table.add_row(
                    f"{c.part_slug} (id={c.part_id})",
                    str(c.total_quantity),
                    ",".join(str(w) for w in c.wo_ids),
                    str(c.estimated_cost_cents),
                    str(c.oem_cost_cents) if c.oem_cost_cents is not None else "—",
                    str(c.aftermarket_cost_cents) if c.aftermarket_cost_cents is not None else "—",
                )
            console.print(table)

    @parts_needs_group.command("consolidate")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--top", "top_n", type=int, default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def pn_consolidate(shop_id, top_n, as_json):
        """Show cross-WO aggregated shopping list WITHOUT persisting."""
        console = get_console()
        init_db()
        consolidated = list_parts_for_shop_open_wos(shop_id)
        if top_n:
            consolidated = consolidated[:top_n]
        if as_json:
            payload = [c.model_dump() for c in consolidated]
            click.echo(_json.dumps(payload, default=str, indent=2))
            return
        if not consolidated:
            console.print("[dim]No active parts needs.[/dim]")
            return
        total = sum(c.estimated_cost_cents for c in consolidated)
        table = Table(
            title=f"Top parts needs (shop id={shop_id}) — total ¢{total}",
            show_lines=False,
        )
        table.add_column("Part")
        table.add_column("Qty", justify="right")
        table.add_column("WOs", justify="right")
        table.add_column("Est ¢", justify="right")
        for c in consolidated:
            table.add_row(
                f"{c.part_slug}",
                str(c.total_quantity),
                str(len(c.wo_ids)),
                str(c.estimated_cost_cents),
            )
        console.print(table)

    @parts_needs_group.command("mark-ordered")
    @click.argument("wop_id", type=int)
    def pn_mark_ordered(wop_id):
        """Advance a parts line from open → ordered."""
        console = get_console()
        init_db()
        try:
            mark_part_ordered(wop_id)
        except (WorkOrderPartNotFoundError, InvalidPartNeedTransition) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[yellow]Marked work_order_part id={wop_id} as ordered.[/yellow]"
        )

    @parts_needs_group.command("mark-received")
    @click.argument("wop_id", type=int)
    def pn_mark_received(wop_id):
        """Advance a parts line from ordered → received."""
        console = get_console()
        init_db()
        try:
            mark_part_received(wop_id)
        except (WorkOrderPartNotFoundError, InvalidPartNeedTransition) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Marked work_order_part id={wop_id} as received.[/green]"
        )

    # Nested requisition subgroup

    @parts_needs_group.group("requisition")
    def requisition_group() -> None:
        """Persisted consolidated shopping-list snapshots."""

    @requisition_group.command("create")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--wo", "wo_ids", multiple=True, type=int,
                  help="Limit to specific WOs (repeatable). Default: all active.")
    @click.option("--notes", default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def req_create(shop_id, wo_ids, notes, as_json):
        """Persist a new requisition snapshot."""
        console = get_console()
        init_db()
        try:
            req_id = build_requisition(
                shop_id,
                wo_ids=list(wo_ids) if wo_ids else None,
                notes=notes,
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        req = get_requisition(req_id)
        assert req is not None
        if as_json:
            click.echo(_json.dumps(req.model_dump(), default=str, indent=2))
            return
        console.print(Panel(
            f"Requisition id={req_id}\n"
            f"Shop: {shop_id}\n"
            f"Distinct parts: {req.total_distinct_parts}\n"
            f"Total quantity: {req.total_quantity}\n"
            f"Estimated cost: ¢{req.total_estimated_cost_cents} "
            f"(${req.total_estimated_cost_cents/100:.2f})",
            title="Requisition created",
        ))

    @requisition_group.command("list")
    @click.option("--shop", "shop_id", type=int, default=None)
    @click.option("--since", default=None)
    @click.option("--limit", type=int, default=20)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def req_list_cmd(shop_id, since, limit, as_json):
        """List recent requisitions (headers)."""
        console = get_console()
        init_db()
        rows = list_requisitions(
            shop_id=shop_id, since=since, limit=limit,
        )
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No requisitions found.[/dim]")
            return
        table = Table(title="Requisitions", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("Shop", justify="right")
        table.add_column("Generated")
        table.add_column("Parts", justify="right")
        table.add_column("Qty", justify="right")
        table.add_column("Est ¢", justify="right")
        for r in rows:
            table.add_row(
                str(r["id"]),
                str(r["shop_id"]),
                str(r["generated_at"]),
                str(r["total_distinct_parts"]),
                str(r["total_quantity"]),
                str(r["total_estimated_cost_cents"]),
            )
        console.print(table)

    @requisition_group.command("show")
    @click.argument("req_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def req_show(req_id, as_json):
        """Show a persisted requisition with its full item list."""
        console = get_console()
        init_db()
        req = get_requisition(req_id)
        if req is None:
            raise click.ClickException(f"requisition not found: id={req_id}")
        if as_json:
            click.echo(_json.dumps(req.model_dump(), default=str, indent=2))
            return
        console.print(Panel(
            f"Generated: {req.generated_at}\n"
            f"Distinct parts: {req.total_distinct_parts}\n"
            f"Total quantity: {req.total_quantity}\n"
            f"Estimated cost: ¢{req.total_estimated_cost_cents}",
            title=f"Requisition id={req_id} (shop {req.shop_id})",
        ))
        if not req.items:
            console.print("[dim]No items.[/dim]")
            return
        table = Table(title="Items", show_lines=False)
        table.add_column("Part")
        table.add_column("Qty", justify="right")
        table.add_column("Est ¢", justify="right")
        table.add_column("Contributing WOs")
        for item in req.items:
            table.add_row(
                f"{item.part_slug} (id={item.part_id})",
                str(item.total_quantity),
                str(item.estimated_cost_cents),
                ",".join(str(w) for w in item.wo_ids),
            )
        console.print(table)

    # -----------------------------------------------------------------
    # shop sourcing {recommend, show, budget}
    # -----------------------------------------------------------------

    @shop_group.group("sourcing")
    def sourcing_group() -> None:
        """AI parts sourcing + cost optimization (Phase 166)."""

    def _render_sourcing_panel(console, rec) -> None:
        cache_label = "[dim](cache hit)[/dim]" if rec.cache_hit else ""
        risk_block = (
            f"\nRisk notes: {rec.risk_notes}" if rec.risk_notes else ""
        )
        alts = (
            ", ".join(str(a) for a in rec.alternative_parts)
            if rec.alternative_parts else "—"
        )
        lines = [
            f"[bold]Part id={rec.part_id}[/bold] qty={rec.quantity} {cache_label}",
            f"Tier: [bold]{rec.source_tier.upper()}[/bold]  "
            f"confidence={rec.confidence:.2f}",
            f"Estimated cost: ¢{rec.estimated_cost_cents} "
            f"(${rec.estimated_cost_cents/100:.2f})",
            f"\nRationale: {rec.rationale}",
            f"\nAlternative parts: {alts}{risk_block}",
        ]
        if rec.vendor_suggestions:
            lines.append("\nVendor suggestions:")
            for v in rec.vendor_suggestions:
                url_line = (
                    f" — {v.url}" if v.url else " — URL unavailable"
                )
                lines.append(
                    f"  • {v.name} ({v.availability}) "
                    f"~¢{v.rough_price_cents}{url_line}"
                )
        lines.append(
            f"\nModel: {rec.ai_model}  tokens: {rec.tokens_in}→{rec.tokens_out}  "
            f"cost: {rec.cost_cents}¢"
        )
        console.print(Panel("\n".join(lines), title="Sourcing recommendation"))

    @sourcing_group.command("recommend")
    @click.option("--part-id", "part_id", type=int, required=True)
    @click.option("--qty", "quantity", type=int, default=1, show_default=True)
    @click.option("--vehicle-id", "vehicle_id", type=int, default=None)
    @click.option(
        "--tier",
        type=click.Choice(["oem", "aftermarket", "used", "balanced"],
                          case_sensitive=False),
        default="balanced",
    )
    @click.option(
        "--model",
        type=click.Choice(["haiku", "sonnet"], case_sensitive=False),
        default="haiku",
    )
    @click.option("--no-cache", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def sourcing_recommend(
        part_id, quantity, vehicle_id, tier, model, no_cache, as_json,
    ):
        """Ask Claude to pick the best source for a single part."""
        console = get_console()
        init_db()
        try:
            rec = recommend_source(
                part_id, quantity=quantity, vehicle_id=vehicle_id,
                tier_preference=tier.lower(), model=model.lower(),
                use_cache=not no_cache,
            )
        except (PartNotFoundError, InvalidTierPreferenceError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(rec.model_dump(mode="json"), default=str, indent=2))
            return
        _render_sourcing_panel(console, rec)

    @sourcing_group.command("show")
    @click.argument("rec_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def sourcing_show(rec_id, as_json):
        """Show one persisted sourcing recommendation."""
        console = get_console()
        init_db()
        row = get_recommendation(rec_id)
        if row is None:
            raise click.ClickException(f"recommendation not found: id={rec_id}")
        if as_json:
            click.echo(_json.dumps(row, default=str, indent=2))
            return
        rec = row.get("recommendation") or {}
        lines = [
            f"[bold]Recommendation id={rec_id}[/bold]",
            f"Part id={row['part_id']} qty={row['quantity']}",
            f"Tier: {row['source_tier']}",
            f"Confidence: {row['confidence']}",
            f"Estimated cost: ¢{row['estimated_cost_cents']}",
            f"Model: {row['ai_model']}  tokens: {row['tokens_in']}→{row['tokens_out']}  "
            f"cost: {row['cost_cents']}¢",
            f"Cache hit: {bool(row['cache_hit'])}",
            f"\nRationale: {rec.get('rationale', '?')}",
        ]
        console.print(Panel("\n".join(lines), title="Sourcing record"))

    @sourcing_group.command("budget")
    @click.option("--from", "since", default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def sourcing_budget_cmd(since, as_json):
        """Aggregate sourcing AI spend + tier distribution + cache-hit rate."""
        console = get_console()
        init_db()
        rollup = sourcing_budget(since=since)
        if as_json:
            click.echo(_json.dumps(rollup, indent=2))
            return
        tier_lines = "\n".join(
            f"  {t}: {n}" for t, n in rollup["tier_distribution"].items()
        ) or "  (no calls yet)"
        console.print(Panel(
            f"Calls: {rollup['calls']}\n"
            f"Tokens in: {rollup['tokens_in']:,}\n"
            f"Tokens out: {rollup['tokens_out']:,}\n"
            f"Cost: ¢{rollup['cost_cents']} "
            f"(${rollup['cost_cents']/100:.2f})\n"
            f"Cache hit rate: {rollup['cache_hit_rate']:.1%} "
            f"({rollup['cache_hit_count']}/{rollup['calls']})\n"
            f"\nTier distribution:\n{tier_lines}",
            title="Sourcing budget"
            + (f" (since {since})" if since else ""),
        ))

    # -----------------------------------------------------------------
    # shop labor {estimate, bulk, show, history, reconcile, budget}
    # -----------------------------------------------------------------

    @shop_group.group("labor")
    def labor_group() -> None:
        """AI labor time estimation (Phase 167)."""

    def _render_labor_estimate(console, est) -> None:
        cache_label = (
            "[dim](prompt cache)[/dim]" if est.prompt_cache_hit else ""
        )
        lines = [
            f"[bold]WO id={est.wo_id}[/bold] skill={est.skill_tier} {cache_label}",
            f"Base: {est.base_hours:.2f}h  →  "
            f"Adjusted: [bold]{est.adjusted_hours:.2f}h[/bold]",
            f"Skill adj: {est.skill_adjustment:+.2f}  "
            f"Mileage adj: {est.mileage_adjustment:+.2f}",
            f"Confidence: {est.confidence:.2f}",
            f"\nRationale: {est.rationale}",
        ]
        if est.breakdown:
            lines.append("\nBreakdown:")
            for step in est.breakdown:
                lines.append(
                    f"  • {step.step_name}: {step.step_hours:.2f}h"
                    + (
                        f"  ({', '.join(step.tools_needed)})"
                        if step.tools_needed else ""
                    )
                )
        if est.alternative_estimates:
            lines.append("\nAlternative scenarios:")
            for alt in est.alternative_estimates:
                lines.append(
                    f"  • {alt.scenario_name}: {alt.hours:.2f}h — {alt.notes}"
                )
        if est.environment_notes:
            lines.append(f"\nEnvironment: {est.environment_notes}")
        lines.append(
            f"\nModel: {est.ai_model}  tokens: {est.tokens_in}→{est.tokens_out}  "
            f"cost: {est.cost_cents}¢"
        )
        console.print(Panel("\n".join(lines), title="Labor estimate"))

    @labor_group.command("estimate")
    @click.argument("wo_id", type=int)
    @click.option(
        "--skill-tier",
        type=click.Choice(
            ["apprentice", "journeyman", "master"], case_sensitive=False,
        ),
        default="journeyman",
    )
    @click.option(
        "--model",
        type=click.Choice(["haiku", "sonnet"], case_sensitive=False),
        default="haiku",
    )
    @click.option("--environment", "environment_hint", default=None)
    @click.option("--no-write-back", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def labor_estimate_cmd(
        wo_id, skill_tier, model, environment_hint, no_write_back, as_json,
    ):
        """Estimate labor hours for a work order. Writes back to WO unless --no-write-back."""
        console = get_console()
        init_db()
        try:
            est = estimate_labor(
                wo_id, skill_tier=skill_tier.lower(), model=model.lower(),
                environment_hint=environment_hint,
                write_back=not no_write_back,
            )
        except (LaborEstimatorError, WorkOrderNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(est.model_dump(mode="json"), default=str, indent=2))
            return
        _render_labor_estimate(console, est)

    @labor_group.command("bulk")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option(
        "--skill-tier",
        type=click.Choice(
            ["apprentice", "journeyman", "master"], case_sensitive=False,
        ),
        default="journeyman",
    )
    @click.option(
        "--model",
        type=click.Choice(["haiku", "sonnet"], case_sensitive=False),
        default="haiku",
    )
    @click.option("--force", is_flag=True, default=False,
                  help="Re-estimate even if WO.estimated_hours already set.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def labor_bulk_cmd(shop_id, skill_tier, model, force, as_json):
        """Bulk-estimate all open/in-progress WOs for a shop."""
        console = get_console()
        init_db()
        results = bulk_estimate_open_wos(
            shop_id, model=model.lower(),
            skill_tier=skill_tier.lower(), force=force,
        )
        if as_json:
            click.echo(_json.dumps(
                [r.model_dump(mode="json") for r in results],
                default=str, indent=2,
            ))
            return
        if not results:
            console.print("[dim]No WOs estimated.[/dim]")
            return
        table = Table(
            title=f"Bulk labor estimate ({len(results)} WOs)",
            show_header=True,
        )
        table.add_column("WO", justify="right")
        table.add_column("Base h", justify="right")
        table.add_column("Adj h", justify="right")
        table.add_column("Skill")
        table.add_column("Conf", justify="right")
        table.add_column("Cost¢", justify="right")
        for r in results:
            table.add_row(
                str(r.wo_id), f"{r.base_hours:.2f}",
                f"{r.adjusted_hours:.2f}", r.skill_tier,
                f"{r.confidence:.2f}", str(r.cost_cents),
            )
        console.print(table)
        total_cost = sum(r.cost_cents for r in results)
        console.print(f"\nTotal cost: {total_cost}¢")

    @labor_group.command("show")
    @click.argument("est_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def labor_show_cmd(est_id, as_json):
        """Show a persisted labor estimate."""
        console = get_console()
        init_db()
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM labor_estimates WHERE id = ?", (est_id,),
            ).fetchone()
        if row is None:
            raise click.ClickException(f"labor estimate not found: id={est_id}")
        d = dict(row)
        if as_json:
            click.echo(_json.dumps(d, default=str, indent=2))
            return
        lines = [
            f"[bold]Labor estimate id={est_id}[/bold]",
            f"WO: {d['wo_id']}  skill={d['skill_tier']}",
            f"Base: {d['base_hours']}h  →  Adjusted: {d['adjusted_hours']}h",
            f"Confidence: {d['confidence']}",
            f"Model: {d['ai_model']}  tokens: {d['tokens_in']}→{d['tokens_out']}  "
            f"cost: {d['cost_cents']}¢",
            f"Generated: {d['generated_at']}",
            f"\nRationale: {d['rationale']}",
        ]
        console.print(Panel("\n".join(lines), title="Labor estimate record"))

    @labor_group.command("history")
    @click.argument("wo_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def labor_history_cmd(wo_id, as_json):
        """Show all labor estimates for a WO (newest first)."""
        console = get_console()
        init_db()
        rows = list_labor_estimates(wo_id=wo_id)
        wo_row = get_work_order(wo_id)
        actual = wo_row.get("actual_hours") if wo_row else None
        if as_json:
            click.echo(_json.dumps({
                "wo_id": wo_id, "actual_hours": actual, "estimates": rows,
            }, default=str, indent=2))
            return
        if not rows:
            console.print(f"[dim]No labor estimates for WO id={wo_id}.[/dim]")
            return
        table = Table(title=f"Labor history — WO {wo_id}", show_header=True)
        table.add_column("Est ID", justify="right")
        table.add_column("Adj h", justify="right")
        table.add_column("Skill")
        table.add_column("Confidence", justify="right")
        table.add_column("Generated")
        table.add_column("Delta", justify="right")
        for r in rows:
            delta_str = "—"
            if actual is not None:
                d = float(actual) - float(r["adjusted_hours"])
                delta_str = f"{d:+.2f}h"
            table.add_row(
                str(r["id"]), f"{r['adjusted_hours']:.2f}",
                r["skill_tier"], f"{r['confidence']:.2f}",
                str(r["generated_at"]), delta_str,
            )
        console.print(table)
        if actual is not None:
            console.print(f"Actual hours on WO: {actual:.2f}")

    @labor_group.command("reconcile")
    @click.argument("wo_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def labor_reconcile_cmd(wo_id, as_json):
        """Compare estimate vs actual for a completed WO (no AI call)."""
        console = get_console()
        init_db()
        try:
            report = reconcile_with_actual(wo_id)
        except (LaborEstimatorError, ReconcileMissingDataError,
                WorkOrderNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(
                report.model_dump(mode="json"), default=str, indent=2,
            ))
            return
        bucket_color = {
            "within": "green", "under": "yellow", "over": "red",
        }.get(report.bucket, "white")
        lines = [
            f"[bold]WO id={wo_id}[/bold]  "
            f"[{bucket_color}]{report.bucket.upper()}[/{bucket_color}]",
            f"Estimated: {report.estimated_hours:.2f}h  "
            f"Actual: {report.actual_hours:.2f}h",
            f"Delta: {report.delta_hours:+.2f}h"
            + (f" ({report.delta_pct:+.1f}%)" if report.delta_pct is not None else ""),
            f"\n{report.notes}",
        ]
        console.print(Panel("\n".join(lines), title="Reconciliation"))

    @labor_group.command("budget")
    @click.option("--shop", "shop_id", type=int, default=None)
    @click.option("--from", "since", default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def labor_budget_cmd(shop_id, since, as_json):
        """Aggregate labor-AI spend + cache-hit rate."""
        console = get_console()
        init_db()
        rollup = labor_budget(shop_id=shop_id, since=since)
        if as_json:
            click.echo(_json.dumps(rollup, indent=2))
            return
        console.print(Panel(
            f"Calls: {rollup['calls']}\n"
            f"Tokens in: {rollup['tokens_in']:,}\n"
            f"Tokens out: {rollup['tokens_out']:,}\n"
            f"Cost: ¢{rollup['cost_cents']} "
            f"(${rollup['cost_cents']/100:.2f})\n"
            f"Prompt cache hit rate: {rollup['cache_hit_rate']:.1%} "
            f"({rollup['cache_hit_count']}/{rollup['calls']})",
            title="Labor estimation budget"
            + (f" (since {since})" if since else ""),
        ))

    # -----------------------------------------------------------------
    # shop bay {add, list, show, deactivate, schedule, reschedule,
    #          conflicts, optimize, utilization, calendar}
    # -----------------------------------------------------------------

    @shop_group.group("bay")
    def bay_group() -> None:
        """Bay/lift scheduling (Phase 168, deterministic, stdlib-only)."""

    @bay_group.command("add")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--name", required=True)
    @click.option(
        "--type", "bay_type",
        type=click.Choice(list(BAY_TYPES), case_sensitive=False),
        default="lift",
    )
    @click.option("--max-weight-lbs", "max_bike_weight_lbs",
                  type=int, default=None)
    @click.option("--notes", default=None)
    def bay_add_cmd(shop_id, name, bay_type, max_bike_weight_lbs, notes):
        """Register a new physical bay/lift for a shop."""
        console = get_console()
        init_db()
        try:
            bay_id = add_bay(
                shop_id, name, bay_type=bay_type.lower(),
                max_bike_weight_lbs=max_bike_weight_lbs, notes=notes,
            )
        except Exception as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Registered bay id={bay_id} '{name}' ({bay_type}).[/green]"
        )

    @bay_group.command("list")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--include-inactive", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def bay_list_cmd(shop_id, include_inactive, as_json):
        """List bays for a shop."""
        console = get_console()
        init_db()
        rows = list_bays(shop_id, include_inactive=include_inactive)
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print(f"[dim]No bays registered for shop id={shop_id}.[/dim]")
            return
        table = Table(title=f"Bays (shop id={shop_id})", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Active")
        table.add_column("Max lbs", justify="right")
        for r in rows:
            table.add_row(
                str(r["id"]), r["name"], r["bay_type"],
                "yes" if r["is_active"] else "no",
                str(r["max_bike_weight_lbs"]) if r["max_bike_weight_lbs"] is not None else "—",
            )
        console.print(table)

    @bay_group.command("show")
    @click.argument("bay_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def bay_show_cmd(bay_id, as_json):
        """Show a bay + today's slot list."""
        console = get_console()
        init_db()
        bay = get_bay(bay_id)
        if bay is None:
            raise click.ClickException(f"bay not found: id={bay_id}")
        if as_json:
            click.echo(_json.dumps(bay, default=str, indent=2))
            return
        console.print(Panel(
            f"Name: {bay['name']}\n"
            f"Type: {bay['bay_type']}\n"
            f"Active: {'yes' if bay['is_active'] else 'no'}\n"
            f"Max weight: {bay['max_bike_weight_lbs']} lbs"
            if bay['max_bike_weight_lbs'] else "Max weight: —",
            title=f"Bay id={bay_id}",
        ))

    @bay_group.command("deactivate")
    @click.argument("bay_id", type=int)
    @click.option("--yes", is_flag=True, default=False)
    def bay_deactivate_cmd(bay_id, yes):
        """Soft-delete a bay (planned slots preserved but flagged in conflicts)."""
        console = get_console()
        init_db()
        if not yes:
            click.confirm(
                f"Deactivate bay id={bay_id}? (Planned slots remain but "
                "will surface as warnings in `bay conflicts`.)",
                abort=True,
            )
        try:
            deactivate_bay(bay_id)
        except BayNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[yellow]Deactivated bay id={bay_id}.[/yellow]")

    @bay_group.command("schedule")
    @click.argument("wo_id", type=int)
    @click.option("--bay", "bay_id", type=int, default=None)
    @click.option("--start", "scheduled_start", default=None,
                  help="ISO datetime; next-available if omitted.")
    @click.option("--duration-hours", "duration_hours", type=float, default=None,
                  help="Override WO.estimated_hours; defaults to 1.0.")
    @click.option("--notes", default=None)
    def bay_schedule_cmd(
        wo_id, bay_id, scheduled_start, duration_hours, notes,
    ):
        """Reserve a bay slot for a work order."""
        console = get_console()
        init_db()
        try:
            slot_id = bay_schedule_wo(
                wo_id, bay_id=bay_id, scheduled_start=scheduled_start,
                duration_hours=duration_hours,
            )
        except (WorkOrderNotFoundError, BayNotFoundError,
                SlotOverlapError, InvalidSlotTransition) as e:
            raise click.ClickException(str(e)) from e
        slot = get_slot(slot_id)
        console.print(Panel(
            f"Slot id: {slot_id}\n"
            f"Bay id: {slot['bay_id']}\n"
            f"Start: {slot['scheduled_start']}\n"
            f"End: {slot['scheduled_end']}\n"
            f"WO: {slot['work_order_id']}",
            title="Bay slot reserved",
        ))

    @bay_group.command("reschedule")
    @click.argument("slot_id", type=int)
    @click.option("--start", "new_start", default=None)
    @click.option("--bay", "new_bay_id", type=int, default=None)
    def bay_reschedule_cmd(slot_id, new_start, new_bay_id):
        """Move a planned slot (preserves duration)."""
        console = get_console()
        init_db()
        try:
            reschedule_slot(
                slot_id, new_start=new_start, new_bay_id=new_bay_id,
            )
        except (SlotNotFoundError, InvalidSlotTransition,
                SlotOverlapError, BayNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(f"[green]Rescheduled slot id={slot_id}.[/green]")

    @bay_group.command("conflicts")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--from", "from_date", default=None)
    @click.option("--to", "to_date", default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def bay_conflicts_cmd(shop_id, from_date, to_date, as_json):
        """Find overlapping slots in a date range."""
        console = get_console()
        init_db()
        date_range = None
        if from_date and to_date:
            date_range = (from_date, to_date)
        conflicts = detect_conflicts(shop_id, date_range=date_range)
        if as_json:
            click.echo(_json.dumps(
                [c.model_dump() for c in conflicts], default=str, indent=2,
            ))
            return
        if not conflicts:
            console.print(f"[green]No conflicts on shop id={shop_id}.[/green]")
            return
        table = Table(title=f"Conflicts (shop id={shop_id})", show_lines=False)
        table.add_column("Slots")
        table.add_column("Bay")
        table.add_column("Overlap (min)", justify="right")
        table.add_column("Severity")
        for c in conflicts:
            sev_color = "red" if c.severity == "error" else "yellow"
            table.add_row(
                f"{c.slot_a_id}↔{c.slot_b_id}",
                str(c.bay_id),
                f"{c.overlap_minutes:.1f}",
                f"[{sev_color}]{c.severity}[/{sev_color}]",
            )
        console.print(table)

    @bay_group.command("optimize")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--date", "date_str", required=True)
    @click.option("--iterations", type=int, default=500)
    @click.option("--seed", "random_seed", type=int, default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def bay_optimize_cmd(shop_id, date_str, iterations, random_seed, as_json):
        """Run greedy + annealing optimization (dry-run only; returns report)."""
        console = get_console()
        init_db()
        report = optimize_shop_day(
            shop_id, date_str,
            annealing_iterations=iterations,
            random_seed=random_seed,
        )
        if as_json:
            click.echo(_json.dumps(
                report.model_dump(), default=str, indent=2,
            ))
            return
        console.print(Panel(
            f"Utilization before: {report.utilization_before:.1%}\n"
            f"Utilization after:  {report.utilization_after:.1%}\n"
            f"Iterations run: {report.iterations_run}\n"
            f"Moves proposed: {len(report.moves)}\n"
            + (
                "[yellow]" + "\n".join(report.warnings) + "[/yellow]"
                if report.warnings else ""
            ),
            title=f"Optimization report (shop {shop_id}, {date_str})",
        ))

    @bay_group.command("utilization")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--date", "date_str", required=True)
    @click.option("--day-hours", "shop_day_hours", type=float, default=8.0)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def bay_utilization_cmd(shop_id, date_str, shop_day_hours, as_json):
        """Show utilization fraction for a shop-day."""
        console = get_console()
        init_db()
        result = utilization_for_day(
            shop_id, date_str, shop_day_hours=shop_day_hours,
        )
        if as_json:
            click.echo(_json.dumps(result, default=str, indent=2))
            return
        console.print(Panel(
            f"Utilization: [bold]{result['utilization']:.1%}[/bold]\n"
            f"Shop day: {result['shop_day_hours']:.1f}h\n"
            f"Date: {result['date']}",
            title=f"Shop {shop_id} utilization",
        ))

    @bay_group.command("calendar")
    @click.option("--shop", "shop_id", type=int, required=True)
    @click.option("--from", "from_date", required=True)
    @click.option("--to", "to_date", required=True)
    @click.option("--bay", "bay_filter", type=int, default=None)
    def bay_calendar_cmd(shop_id, from_date, to_date, bay_filter):
        """Render multi-day calendar (Rich table with hour-rows x bay-columns)."""
        console = get_console()
        init_db()
        slots = list_slots(
            shop_id=shop_id, bay_id=bay_filter,
            date_range=(from_date, to_date),
        )
        if not slots:
            console.print(
                f"[dim]No slots on shop id={shop_id} between "
                f"{from_date} and {to_date}.[/dim]"
            )
            return
        table = Table(
            title=f"Calendar: shop {shop_id} {from_date}..{to_date}",
            show_lines=False,
        )
        table.add_column("Slot", justify="right")
        table.add_column("Bay")
        table.add_column("Start")
        table.add_column("End")
        table.add_column("Status")
        table.add_column("WO")
        status_color = {
            "planned": "cyan", "active": "yellow",
            "completed": "green", "cancelled": "dim", "overrun": "red",
        }
        for s in slots:
            status = s.get("status", "?")
            color = status_color.get(status, "white")
            table.add_row(
                str(s["id"]), str(s.get("bay_name", s["bay_id"])),
                str(s["scheduled_start"]), str(s["scheduled_end"]),
                f"[{color}]{status}[/{color}]",
                str(s.get("work_order_id") or "—"),
            )
        console.print(table)

    # -----------------------------------------------------------------
    # shop invoice {generate, list, show, mark-paid, revenue, void}
    # Phase 169 — revenue tracking + invoicing
    # -----------------------------------------------------------------

    @shop_group.group("invoice")
    def invoice_group() -> None:
        """Invoices + revenue: generate from WOs, mark paid, roll up totals."""

    @invoice_group.command("generate")
    @click.argument("wo_id", type=int)
    @click.option("--tax-rate", type=float, default=0.0,
                  help="Sales tax rate 0-1 (e.g. 0.0825 for 8.25%).")
    @click.option("--supplies-pct", type=float, default=0.0,
                  help="Shop supplies percentage 0-1.")
    @click.option("--supplies-flat", "supplies_flat_cents", type=int, default=0,
                  help="Shop supplies flat fee (cents).")
    @click.option("--diagnostic-fee", "diagnostic_fee_cents", type=int, default=0,
                  help="Optional diagnostic fee line (cents).")
    @click.option("--hourly-rate", "hourly_rate_cents", type=int, default=None,
                  help="Labor hourly rate override (cents/hr).")
    @click.option("--notes", default=None, help="Invoice-level notes.")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def invoice_generate_cmd(
        wo_id, tax_rate, supplies_pct, supplies_flat_cents,
        diagnostic_fee_cents, hourly_rate_cents, notes, as_json,
    ):
        """Generate an invoice from a completed work order."""
        console = get_console()
        init_db()
        try:
            invoice_id = generate_invoice_for_wo(
                wo_id,
                tax_rate=tax_rate,
                shop_supplies_pct=supplies_pct,
                shop_supplies_flat_cents=supplies_flat_cents,
                diagnostic_fee_cents=diagnostic_fee_cents,
                labor_hourly_rate_cents=hourly_rate_cents,
                notes=notes,
            )
        except InvoiceGenerationError as e:
            raise click.ClickException(str(e)) from e
        except WorkOrderNotFoundError as e:
            raise click.ClickException(str(e)) from e
        summary = get_invoice_with_items(invoice_id)
        if as_json:
            click.echo(_json.dumps(
                summary.model_dump() if summary else {"id": invoice_id},
                default=str, indent=2,
            ))
            return
        assert summary is not None
        console.print(
            f"[green]Generated invoice id={invoice_id} "
            f"({summary.invoice_number}).[/green]"
        )
        _render_invoice_panel(console, summary)

    @invoice_group.command("list")
    @click.option("--shop", "shop_identifier", default=None,
                  help="Shop id or name (defaults to only active shop).")
    @click.option("--status", default=None,
                  help="Filter: draft|sent|paid|overdue|cancelled")
    @click.option("--since", default=None,
                  help="ISO timestamp or date (issued_at >= since).")
    @click.option("--limit", type=int, default=50)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def invoice_list_cmd(
        shop_identifier, status, since, limit, as_json,
    ):
        """List invoices for a shop."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        try:
            rows = list_invoices_for_shop(
                shop["id"], status=status, since=since, limit=limit,
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print(
                f"[dim]No invoices for shop {shop['name']!r}.[/dim]"
            )
            return
        table = Table(
            title=f"Invoices — {shop['name']}", show_lines=False,
        )
        table.add_column("ID", justify="right")
        table.add_column("Number")
        table.add_column("WO", justify="right")
        table.add_column("Status")
        table.add_column("Total", justify="right")
        table.add_column("Issued")
        status_color = {
            "draft": "white", "sent": "cyan", "paid": "green",
            "overdue": "red", "cancelled": "dim",
        }
        for r in rows:
            st = r.get("status", "?")
            color = status_color.get(st, "white")
            total_cents = int(r.get("total_cents") or 0)
            table.add_row(
                str(r["id"]), str(r.get("invoice_number") or ""),
                str(r.get("work_order_id") or "—"),
                f"[{color}]{st}[/{color}]",
                f"${total_cents / 100:.2f}",
                str(r.get("issued_at") or "—"),
            )
        console.print(table)

    @invoice_group.command("show")
    @click.argument("invoice_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def invoice_show_cmd(invoice_id, as_json):
        """Show an invoice with its line items."""
        console = get_console()
        init_db()
        summary = get_invoice_with_items(invoice_id)
        if summary is None:
            raise click.ClickException(f"invoice not found: id={invoice_id}")
        if as_json:
            click.echo(_json.dumps(summary.model_dump(), default=str, indent=2))
            return
        _render_invoice_panel(console, summary)

    @invoice_group.command("mark-paid")
    @click.argument("invoice_id", type=int)
    @click.option("--paid-at", default=None,
                  help="ISO timestamp (defaults to now UTC).")
    def invoice_mark_paid_cmd(invoice_id, paid_at):
        """Mark an invoice as paid."""
        console = get_console()
        init_db()
        try:
            mark_invoice_paid(invoice_id, paid_at=paid_at)
        except InvoiceNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Invoice id={invoice_id} marked paid.[/green]"
        )

    @invoice_group.command("void")
    @click.argument("invoice_id", type=int)
    @click.option("--reason", default=None, help="Reason (appended to notes).")
    def invoice_void_cmd(invoice_id, reason):
        """Void an invoice (sets status=cancelled, allows regeneration)."""
        console = get_console()
        init_db()
        try:
            void_invoice(invoice_id, reason=reason)
        except InvoiceNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[yellow]Invoice id={invoice_id} voided.[/yellow]"
        )

    @invoice_group.command("revenue")
    @click.option("--shop", "shop_identifier", default=None,
                  help="Shop id or name (omit for all-shops rollup).")
    @click.option("--since", default=None,
                  help="ISO timestamp or date (issued_at >= since).")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def invoice_revenue_cmd(shop_identifier, since, as_json):
        """Revenue rollup by status for the shop dashboard."""
        console = get_console()
        init_db()
        shop_id = None
        if shop_identifier is not None:
            shop = _resolve_shop_identifier(shop_identifier)
            assert shop is not None
            shop_id = shop["id"]
        rollup = revenue_rollup(shop_id=shop_id, since=since)
        if as_json:
            click.echo(_json.dumps(rollup.model_dump(), default=str, indent=2))
            return
        lines = [
            f"Shop:          {shop_id if shop_id is not None else '(all)'}",
            f"Since:         {since or '(all time)'}",
            f"Invoices:      {rollup.invoice_count}",
            f"Total invoiced: ${rollup.total_invoiced_cents / 100:.2f}",
            f"Total paid:    ${rollup.total_paid_cents / 100:.2f}",
            f"Pending:       ${rollup.total_pending_cents / 100:.2f}",
        ]
        if rollup.by_status:
            lines.append("")
            lines.append("By status:")
            for st, n in sorted(rollup.by_status.items()):
                lines.append(f"  {st:<10} {n}")
        console.print(Panel("\n".join(lines), title="Revenue Rollup"))

    # -----------------------------------------------------------------
    # shop notify {trigger, preview, list, mark-sent, mark-failed,
    #              cancel, templates, resend}
    # Phase 170 — customer communication
    # -----------------------------------------------------------------

    @shop_group.group("notify")
    def notify_group() -> None:
        """Customer communications — template-rendered audit-logged queue."""

    def _parse_extra(raw: Optional[str]) -> Optional[dict]:
        if not raw:
            return None
        try:
            parsed = _json.loads(raw)
        except ValueError as e:
            raise click.ClickException(
                f"--extra must be JSON object: {e}"
            ) from e
        if not isinstance(parsed, dict):
            raise click.ClickException(
                "--extra must be a JSON object, not a list/scalar"
            )
        return parsed

    @notify_group.command("trigger")
    @click.argument("event")
    @click.option("--wo", "wo_id", type=int, default=None)
    @click.option("--invoice", "invoice_id", type=int, default=None)
    @click.option("--customer", "customer_id", type=int, default=None)
    @click.option("--channel", type=click.Choice(
        ["email", "sms", "in_app"],
    ), default="email")
    @click.option("--extra", "extra_raw", default=None,
                  help='JSON object of template overrides, e.g. '
                       '\'{"approval_finding":"valves leaking"}\'')
    @click.option("--json", "as_json", is_flag=True, default=False)
    def notify_trigger_cmd(
        event, wo_id, invoice_id, customer_id, channel, extra_raw, as_json,
    ):
        """Render + queue a notification (status=pending)."""
        console = get_console()
        init_db()
        extra = _parse_extra(extra_raw)
        try:
            notif_id = trigger_notification(
                event,
                wo_id=wo_id, invoice_id=invoice_id,
                customer_id=customer_id, channel=channel,
                extra_context=extra,
            )
        except (UnknownEventError, NotificationContextError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        notif = get_notification(notif_id)
        if as_json:
            click.echo(_json.dumps(
                notif.model_dump() if notif else {"id": notif_id},
                default=str, indent=2,
            ))
            return
        assert notif is not None
        console.print(
            f"[green]Notification #{notif_id} queued "
            f"({event}/{channel}).[/green] "
            f"Mark sent with `shop notify mark-sent {notif_id}` "
            f"once delivered."
        )
        _render_notification_panel(console, notif)

    @notify_group.command("preview")
    @click.argument("event")
    @click.option("--wo", "wo_id", type=int, default=None)
    @click.option("--invoice", "invoice_id", type=int, default=None)
    @click.option("--customer", "customer_id", type=int, default=None)
    @click.option("--channel", type=click.Choice(
        ["email", "sms", "in_app"],
    ), default="email")
    @click.option("--extra", "extra_raw", default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def notify_preview_cmd(
        event, wo_id, invoice_id, customer_id, channel, extra_raw, as_json,
    ):
        """Render without persisting."""
        console = get_console()
        init_db()
        extra = _parse_extra(extra_raw)
        try:
            preview = preview_notification(
                event,
                wo_id=wo_id, invoice_id=invoice_id,
                customer_id=customer_id, channel=channel,
                extra_context=extra,
            )
        except (UnknownEventError, NotificationContextError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(
                preview.model_dump(), default=str, indent=2,
            ))
            return
        _render_notification_panel(console, preview)

    @notify_group.command("list")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--customer", "customer_id", type=int, default=None)
    @click.option("--wo", "wo_id", type=int, default=None)
    @click.option("--status", default=None,
                  type=click.Choice([
                      "pending", "sent", "failed", "cancelled",
                  ]))
    @click.option("--event", default=None)
    @click.option("--since", default=None)
    @click.option("--limit", type=int, default=50)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def notify_list_cmd(
        shop_identifier, customer_id, wo_id, status, event, since,
        limit, as_json,
    ):
        """List notifications with composable filters."""
        console = get_console()
        init_db()
        shop_id = None
        if shop_identifier is not None:
            shop = _resolve_shop_identifier(shop_identifier)
            assert shop is not None
            shop_id = shop["id"]
        try:
            rows = list_notifications(
                customer_id=customer_id, shop_id=shop_id, wo_id=wo_id,
                status=status, event=event, since=since, limit=limit,
            )
        except (UnknownEventError, ValueError) as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(rows, default=str, indent=2))
            return
        if not rows:
            console.print("[dim]No notifications match.[/dim]")
            return
        table = Table(title="Notifications", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("Event")
        table.add_column("Channel")
        table.add_column("Recipient")
        table.add_column("Status")
        table.add_column("Triggered")
        status_color = {
            "pending": "yellow", "sent": "green",
            "failed": "red", "cancelled": "dim",
        }
        for r in rows:
            st = r.get("status", "?")
            color = status_color.get(st, "white")
            table.add_row(
                str(r["id"]),
                str(r.get("event", "?")),
                str(r.get("channel", "?")),
                str(r.get("recipient") or "—"),
                f"[{color}]{st}[/{color}]",
                str(r.get("triggered_at") or "—"),
            )
        console.print(table)

    @notify_group.command("mark-sent")
    @click.argument("notification_id", type=int)
    @click.option("--sent-at", default=None,
                  help="ISO timestamp (defaults to now UTC).")
    def notify_mark_sent_cmd(notification_id, sent_at):
        """Transition pending → sent."""
        console = get_console()
        init_db()
        try:
            mark_notification_sent(notification_id, sent_at=sent_at)
        except NotificationNotFoundError as e:
            raise click.ClickException(str(e)) from e
        except Exception as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Notification #{notification_id} marked sent.[/green]"
        )

    @notify_group.command("mark-failed")
    @click.argument("notification_id", type=int)
    @click.option("--reason", required=True,
                  help="Why it failed (bounce, invalid number, etc).")
    def notify_mark_failed_cmd(notification_id, reason):
        """Transition pending → failed."""
        console = get_console()
        init_db()
        try:
            mark_notification_failed(
                notification_id, failure_reason=reason,
            )
        except NotificationNotFoundError as e:
            raise click.ClickException(str(e)) from e
        except Exception as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[red]Notification #{notification_id} marked failed: "
            f"{reason}[/red]"
        )

    @notify_group.command("cancel")
    @click.argument("notification_id", type=int)
    @click.option("--reason", default=None)
    def notify_cancel_cmd(notification_id, reason):
        """Transition pending → cancelled."""
        console = get_console()
        init_db()
        try:
            cancel_notification(notification_id, reason=reason)
        except NotificationNotFoundError as e:
            raise click.ClickException(str(e)) from e
        except Exception as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[yellow]Notification #{notification_id} cancelled.[/yellow]"
        )

    @notify_group.command("resend")
    @click.argument("notification_id", type=int)
    def notify_resend_cmd(notification_id):
        """Create a NEW pending notification duplicating a prior one."""
        console = get_console()
        init_db()
        try:
            new_id = resend_notification(notification_id)
        except NotificationNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Resent as notification #{new_id}.[/green] "
            f"(source #{notification_id} untouched for audit.)"
        )

    @notify_group.command("templates")
    @click.option("--json", "as_json", is_flag=True, default=False)
    def notify_templates_cmd(as_json):
        """Enumerate all registered templates."""
        console = get_console()
        catalog = list_template_catalog()
        if as_json:
            click.echo(_json.dumps(catalog, default=str, indent=2))
            return
        table = Table(title="Notification Templates", show_lines=False)
        table.add_column("Event")
        table.add_column("Channel")
        table.add_column("Has Subject")
        for row in catalog:
            table.add_row(
                row["event"], row["channel"],
                "yes" if row["has_subject"] else "—",
            )
        console.print(table)

    # -----------------------------------------------------------------
    # shop analytics {snapshot, throughput, turnaround, utilization,
    #                 overruns, labor-accuracy, top-issues, top-parts,
    #                 mechanic, customer-repeat}
    # Phase 171 — shop analytics dashboard
    # -----------------------------------------------------------------

    @shop_group.group("analytics")
    def analytics_group() -> None:
        """Read-only analytics over Track G state — no writes."""

    def _resolve_shop_id(identifier) -> int:
        shop = _resolve_shop_identifier(identifier)
        assert shop is not None
        return int(shop["id"])

    @analytics_group.command("snapshot")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--since", default="30d",
                  help="Rolling window: 30d, 7d, 24h, or ISO timestamp.")
    @click.option("--utilization-days", type=int, default=7)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def analytics_snapshot_cmd(
        shop_identifier, since, utilization_days, as_json,
    ):
        """All-in-one dashboard snapshot."""
        console = get_console()
        init_db()
        shop_id = _resolve_shop_id(shop_identifier)
        try:
            snap = dashboard_snapshot(
                shop_id, since=since,
                utilization_window_days=utilization_days,
            )
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(
                snap.model_dump(), default=str, indent=2,
            ))
            return
        lines = [
            f"Shop:       {shop_id}",
            f"Since:      {since}",
            f"Generated:  {snap.generated_at}",
            "",
            f"[bold]Throughput[/bold]",
            f"  Completed:         {snap.throughput.completed_total}",
            f"  By status:         "
            + ", ".join(
                f"{k}={v}" for k, v in snap.throughput.by_status.items()
            ),
            "",
            f"[bold]Turnaround (WO opened → completed)[/bold]",
            f"  Sample size:       {snap.turnaround.sample_size}",
            f"  Mean hours:        {snap.turnaround.mean_hours}",
            f"  Median hours:      {snap.turnaround.median_hours}",
            f"  p90 hours:         {snap.turnaround.p90_hours}",
            "",
            f"[bold]Utilization ({snap.utilization.from_date} → {snap.utilization.to_date})[/bold]",
            f"  Mean util:         {snap.utilization.mean_pct:.1%}",
            f"  Over-threshold days: {snap.utilization.over_threshold_days}",
            "",
            f"[bold]Overrun rate[/bold]",
            f"  Total slots:       {snap.overrun.total_slots}",
            f"  Overrun slots:     {snap.overrun.overrun_slots}",
            f"  Rate:              {snap.overrun.rate:.1%}",
            "",
            f"[bold]Labor accuracy (est vs actual, ±20%)[/bold]",
            f"  Sample:            {snap.labor_accuracy.sample_size}",
            f"  Within ±20%:       {snap.labor_accuracy.within_pct:.1%}",
            f"  Median delta pct:  {snap.labor_accuracy.median_delta_pct}",
            "",
            f"[bold]Customer repeat rate[/bold]",
            f"  Total WOs:         {snap.customer_repeat.total_wos}",
            f"  Repeat WOs:        {snap.customer_repeat.repeat_wos}",
            f"  Rate:              {snap.customer_repeat.repeat_rate:.1%}",
            "",
            f"[bold]Revenue (Phase 169)[/bold]",
            f"  Invoices:          {snap.revenue.invoice_count}",
            f"  Total invoiced:    ${snap.revenue.total_invoiced_cents / 100:.2f}",
            f"  Total paid:        ${snap.revenue.total_paid_cents / 100:.2f}",
            f"  Pending:           ${snap.revenue.total_pending_cents / 100:.2f}",
        ]
        if snap.top_issues:
            lines.append("")
            lines.append("[bold]Top issues[/bold]")
            for row in snap.top_issues[:5]:
                lines.append(
                    f"  {row.category:<20} {row.severity:<10} {row.count}"
                )
        if snap.top_parts:
            lines.append("")
            lines.append("[bold]Top parts by cost[/bold]")
            for row in snap.top_parts[:5]:
                lines.append(
                    f"  {row.slug:<35} qty={row.total_qty:<4} "
                    f"${row.total_cost_cents / 100:.2f}"
                )
        console.print(Panel("\n".join(lines), title="Dashboard"))

    def _simple_rollup_cmd(
        group, name: str, fn, as_model=True,
    ):
        @group.command(name)
        @click.option("--shop", "shop_identifier", default=None)
        @click.option("--since", default="30d")
        @click.option("--json", "as_json", is_flag=True, default=False)
        def _cmd(shop_identifier, since, as_json):
            console = get_console()
            init_db()
            shop_id = _resolve_shop_id(shop_identifier)
            try:
                result = fn(shop_id, since=since)
            except ValueError as e:
                raise click.ClickException(str(e)) from e
            if as_json or not as_model:
                payload = (
                    result.model_dump()
                    if hasattr(result, "model_dump") else result
                )
                click.echo(_json.dumps(payload, default=str, indent=2))
                return
            console.print(_json.dumps(
                result.model_dump() if hasattr(result, "model_dump") else result,
                default=str, indent=2,
            ))
        _cmd.__name__ = f"analytics_{name}_cmd"
        return _cmd

    _simple_rollup_cmd(analytics_group, "throughput", analytics_throughput)
    _simple_rollup_cmd(analytics_group, "turnaround", turnaround)
    _simple_rollup_cmd(analytics_group, "overruns", overrun_rate)
    _simple_rollup_cmd(analytics_group, "labor-accuracy", labor_accuracy)
    _simple_rollup_cmd(analytics_group, "mechanic", mechanic_performance)
    _simple_rollup_cmd(
        analytics_group, "customer-repeat", customer_repeat_rate,
    )

    @analytics_group.command("utilization")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--from", "from_date", required=True)
    @click.option("--to", "to_date", required=True)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def analytics_utilization_cmd(
        shop_identifier, from_date, to_date, as_json,
    ):
        """Per-day utilization across a window."""
        console = get_console()
        init_db()
        shop_id = _resolve_shop_id(shop_identifier)
        try:
            result = utilization_rollup(shop_id, from_date, to_date)
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(
                result.model_dump(), default=str, indent=2,
            ))
            return
        console.print(_json.dumps(
            result.model_dump(), default=str, indent=2,
        ))

    @analytics_group.command("top-issues")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--since", default="30d")
    @click.option("--limit", type=int, default=10)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def analytics_top_issues_cmd(shop_identifier, since, limit, as_json):
        """Top issue (category, severity) pairs."""
        console = get_console()
        init_db()
        shop_id = _resolve_shop_id(shop_identifier)
        try:
            rows = analytics_top_issues(shop_id, since=since, limit=limit)
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        payload = [r.model_dump() for r in rows]
        if as_json:
            click.echo(_json.dumps(payload, default=str, indent=2))
            return
        console.print(_json.dumps(payload, default=str, indent=2))

    @analytics_group.command("top-parts")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--since", default="30d")
    @click.option("--limit", type=int, default=10)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def analytics_top_parts_cmd(shop_identifier, since, limit, as_json):
        """Top parts by aggregate cost."""
        console = get_console()
        init_db()
        shop_id = _resolve_shop_id(shop_identifier)
        try:
            rows = analytics_top_parts(shop_id, since=since, limit=limit)
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        payload = [r.model_dump() for r in rows]
        if as_json:
            click.echo(_json.dumps(payload, default=str, indent=2))
            return
        console.print(_json.dumps(payload, default=str, indent=2))

    # -----------------------------------------------------------------
    # shop member {add, list, set-role, deactivate, reactivate}
    # Phase 172 — shop-scoped RBAC membership
    # -----------------------------------------------------------------

    @shop_group.group("member")
    def member_group() -> None:
        """Shop-scoped membership + role management."""

    @member_group.command("add")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--user", "user_id", type=int, required=True)
    @click.option("--role", type=click.Choice(list(SHOP_ROLES)),
                  default="tech")
    def member_add_cmd(shop_identifier, user_id, role):
        """Add (or reactivate) a shop member."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        try:
            add_shop_member(shop["id"], user_id, role)
        except InvalidRoleError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Added user id={user_id} as {role} of "
            f"shop {shop['name']!r}.[/green]"
        )

    @member_group.command("list")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--role", default=None,
                  type=click.Choice(list(SHOP_ROLES)))
    @click.option("--include-inactive", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def member_list_cmd(
        shop_identifier, role, include_inactive, as_json,
    ):
        """List members of a shop."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        rows = list_shop_members(
            shop["id"], role=role, active_only=not include_inactive,
        )
        if as_json:
            click.echo(_json.dumps(
                [r.model_dump() for r in rows], default=str, indent=2,
            ))
            return
        if not rows:
            console.print(
                f"[dim]No members in shop {shop['name']!r}.[/dim]"
            )
            return
        table = Table(
            title=f"Members — {shop['name']}", show_lines=False,
        )
        table.add_column("User", justify="right")
        table.add_column("Username")
        table.add_column("Role")
        table.add_column("Active")
        table.add_column("Joined")
        for r in rows:
            table.add_row(
                str(r.user_id),
                r.username or "—",
                r.role,
                "yes" if r.is_active else "no",
                str(r.joined_at),
            )
        console.print(table)

    @member_group.command("set-role")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--user", "user_id", type=int, required=True)
    @click.option("--role", type=click.Choice(list(SHOP_ROLES)),
                  required=True)
    def member_set_role_cmd(shop_identifier, user_id, role):
        """Change a member's role."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        try:
            set_member_role(shop["id"], user_id, role)
        except (InvalidRoleError, ShopMembershipNotFoundError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]User id={user_id} is now {role} at shop "
            f"{shop['name']!r}.[/green]"
        )

    @member_group.command("deactivate")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--user", "user_id", type=int, required=True)
    def member_deactivate_cmd(shop_identifier, user_id):
        """Deactivate a member (soft-delete — preserves audit trail)."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        try:
            deactivate_member(shop["id"], user_id)
        except ShopMembershipNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[yellow]User id={user_id} deactivated at shop "
            f"{shop['name']!r}.[/yellow]"
        )

    @member_group.command("reactivate")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--user", "user_id", type=int, required=True)
    def member_reactivate_cmd(shop_identifier, user_id):
        """Reactivate a deactivated member."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        try:
            reactivate_member(shop["id"], user_id)
        except ShopMembershipNotFoundError as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]User id={user_id} reactivated at shop "
            f"{shop['name']!r}.[/green]"
        )

    # -----------------------------------------------------------------
    # shop rule {add, list, show, update, enable, disable, delete,
    #            fire, test, history}
    # Phase 173 — workflow automation rules
    # -----------------------------------------------------------------

    @shop_group.group("rule")
    def rule_group() -> None:
        """Workflow automation: if-this-then-that rules."""

    def _parse_json_opt(raw, flag_name):
        if not raw:
            return []
        try:
            parsed = _json.loads(raw)
        except ValueError as e:
            raise click.ClickException(
                f"--{flag_name} must be valid JSON: {e}"
            ) from e
        if not isinstance(parsed, list):
            raise click.ClickException(
                f"--{flag_name} must be a JSON array"
            )
        return parsed

    @rule_group.command("add")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--name", required=True)
    @click.option("--event", "event_trigger",
                  type=click.Choice(list(EVENT_TRIGGERS)), required=True)
    @click.option("--conditions", "conditions_raw", default="[]",
                  help='JSON array of condition dicts, e.g. '
                       '\'[{"type":"priority_lte","value":2}]\'')
    @click.option("--actions", "actions_raw", required=True,
                  help='JSON array of action dicts, e.g. '
                       '\'[{"type":"flag_urgent"}]\'')
    @click.option("--priority", type=int, default=100)
    @click.option("--description", default=None)
    def rule_add_cmd(
        shop_identifier, name, event_trigger,
        conditions_raw, actions_raw, priority, description,
    ):
        """Create a new workflow rule."""
        console = get_console()
        init_db()
        shop = _resolve_shop_identifier(shop_identifier)
        assert shop is not None
        conditions = _parse_json_opt(conditions_raw, "conditions")
        actions = _parse_json_opt(actions_raw, "actions")
        try:
            rule_id = create_rule(
                shop_id=shop["id"], name=name,
                event_trigger=event_trigger,
                conditions=conditions, actions=actions,
                priority=priority, description=description,
            )
        except (
            DuplicateRuleNameError, InvalidEventError,
            InvalidConditionError, InvalidActionError,
        ) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Created rule #{rule_id} {name!r} "
            f"(event={event_trigger}).[/green]"
        )

    @rule_group.command("list")
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--event", "event_trigger", default=None,
                  type=click.Choice(list(EVENT_TRIGGERS)))
    @click.option("--include-inactive", is_flag=True, default=False)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def rule_list_cmd(
        shop_identifier, event_trigger, include_inactive, as_json,
    ):
        """List rules."""
        console = get_console()
        init_db()
        shop_id = None
        if shop_identifier is not None:
            shop = _resolve_shop_identifier(shop_identifier)
            assert shop is not None
            shop_id = shop["id"]
        rules = list_rules(
            shop_id=shop_id, event_trigger=event_trigger,
            active_only=not include_inactive,
        )
        if as_json:
            click.echo(_json.dumps(
                [r.model_dump() for r in rules], default=str, indent=2,
            ))
            return
        if not rules:
            console.print("[dim]No rules match.[/dim]")
            return
        table = Table(title="Workflow rules", show_lines=False)
        table.add_column("ID", justify="right")
        table.add_column("Shop")
        table.add_column("Name")
        table.add_column("Event")
        table.add_column("Priority", justify="right")
        table.add_column("Active")
        for r in rules:
            table.add_row(
                str(r.id), str(r.shop_id),
                r.name, r.event_trigger,
                str(r.priority),
                "yes" if r.is_active else "no",
            )
        console.print(table)

    @rule_group.command("show")
    @click.argument("rule_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def rule_show_cmd(rule_id, as_json):
        """Show one rule with conditions + actions."""
        console = get_console()
        init_db()
        rule = get_rule(rule_id)
        if rule is None:
            raise click.ClickException(f"rule not found: id={rule_id}")
        if as_json:
            click.echo(_json.dumps(
                rule.model_dump(), default=str, indent=2,
            ))
            return
        lines = [
            f"[bold]Rule #{rule.id}: {rule.name}[/bold]",
            f"Shop:       {rule.shop_id}",
            f"Event:      {rule.event_trigger}",
            f"Priority:   {rule.priority}",
            f"Active:     {'yes' if rule.is_active else 'no'}",
        ]
        if rule.description:
            lines.append(f"Description: {rule.description}")
        lines.append("")
        lines.append("[bold]Conditions (AND-composed)[/bold]")
        for c in rule.conditions:
            lines.append(f"  {_json.dumps(c)}")
        if not rule.conditions:
            lines.append("  (always)")
        lines.append("")
        lines.append("[bold]Actions (fire-in-order)[/bold]")
        for a in rule.actions:
            lines.append(f"  {_json.dumps(a)}")
        console.print(Panel("\n".join(lines), title="Rule"))

    @rule_group.command("update")
    @click.argument("rule_id", type=int)
    @click.option("--name", default=None)
    @click.option("--description", default=None)
    @click.option("--priority", type=int, default=None)
    @click.option("--conditions", "conditions_raw", default=None)
    @click.option("--actions", "actions_raw", default=None)
    def rule_update_cmd(
        rule_id, name, description, priority, conditions_raw, actions_raw,
    ):
        """Update an existing rule."""
        console = get_console()
        init_db()
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if priority is not None:
            updates["priority"] = priority
        if conditions_raw is not None:
            updates["conditions"] = _parse_json_opt(
                conditions_raw, "conditions",
            )
        if actions_raw is not None:
            updates["actions"] = _parse_json_opt(
                actions_raw, "actions",
            )
        if not updates:
            raise click.ClickException("no updates specified")
        try:
            update_rule(rule_id, **updates)
        except (InvalidConditionError, InvalidActionError) as e:
            raise click.ClickException(str(e)) from e
        console.print(
            f"[green]Rule #{rule_id} updated.[/green]"
        )

    @rule_group.command("enable")
    @click.argument("rule_id", type=int)
    def rule_enable_cmd(rule_id):
        """Activate a rule."""
        console = get_console()
        init_db()
        enable_rule(rule_id)
        console.print(f"[green]Rule #{rule_id} enabled.[/green]")

    @rule_group.command("disable")
    @click.argument("rule_id", type=int)
    def rule_disable_cmd(rule_id):
        """Deactivate a rule."""
        console = get_console()
        init_db()
        disable_rule(rule_id)
        console.print(f"[yellow]Rule #{rule_id} disabled.[/yellow]")

    @rule_group.command("delete")
    @click.argument("rule_id", type=int)
    @click.option("--yes", is_flag=True, default=False)
    def rule_delete_cmd(rule_id, yes):
        """Delete a rule (and cascades its run history)."""
        console = get_console()
        init_db()
        if not yes:
            if not click.confirm(
                f"Delete rule #{rule_id} and its run history?",
            ):
                raise click.ClickException("aborted")
        delete_rule(rule_id)
        console.print(f"[red]Rule #{rule_id} deleted.[/red]")

    @rule_group.command("fire")
    @click.argument("rule_id", type=int)
    @click.argument("wo_id", type=int)
    @click.option("--actor", "actor_user_id", type=int, default=None)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def rule_fire_cmd(rule_id, wo_id, actor_user_id, as_json):
        """Manually fire a rule against a WO."""
        console = get_console()
        init_db()
        try:
            result = fire_rule_for_wo(
                rule_id, wo_id,
                actor_user_id=actor_user_id,
                triggered_event="manual",
            )
        except RuleNotFoundError as e:
            raise click.ClickException(str(e)) from e
        if as_json:
            click.echo(_json.dumps(
                result.model_dump(), default=str, indent=2,
            ))
            return
        verdict = "MATCHED" if result.matched else "did not match"
        color = "green" if result.matched else "dim"
        console.print(
            f"[{color}]Rule #{rule_id} on WO #{wo_id}: {verdict}."
            f"[/{color}]"
        )
        for a in result.actions_log:
            ok = "[green]OK[/green]" if a.get("ok") else "[red]FAIL[/red]"
            console.print(f"  {ok}  {a}")
        if result.error:
            console.print(f"[red]Error: {result.error}[/red]")

    @rule_group.command("test")
    @click.argument("rule_id", type=int)
    @click.argument("wo_id", type=int)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def rule_test_cmd(rule_id, wo_id, as_json):
        """Dry-run: evaluate a rule against a WO without executing actions."""
        console = get_console()
        init_db()
        rule = get_rule(rule_id)
        if rule is None:
            raise click.ClickException(f"rule not found: id={rule_id}")
        ctx = build_wo_context(wo_id)
        matched = evaluate_rule(rule, ctx)
        payload = {
            "rule_id": rule_id, "rule_name": rule.name,
            "work_order_id": wo_id, "matched": matched,
            "would_fire_actions": rule.actions if matched else [],
        }
        if as_json:
            click.echo(_json.dumps(payload, default=str, indent=2))
            return
        color = "green" if matched else "dim"
        console.print(
            f"[{color}]Rule #{rule_id} on WO #{wo_id}: "
            f"{'MATCHED' if matched else 'did not match'}.[/{color}]"
        )
        if matched:
            console.print(f"Would fire {len(rule.actions)} action(s):")
            for a in rule.actions:
                console.print(f"  {_json.dumps(a)}")

    @rule_group.command("history")
    @click.option("--rule", "rule_id", type=int, default=None)
    @click.option("--wo", "wo_id", type=int, default=None)
    @click.option("--shop", "shop_identifier", default=None)
    @click.option("--matched-only", is_flag=True, default=False)
    @click.option("--since", default=None)
    @click.option("--limit", type=int, default=50)
    @click.option("--json", "as_json", is_flag=True, default=False)
    def rule_history_cmd(
        rule_id, wo_id, shop_identifier, matched_only,
        since, limit, as_json,
    ):
        """Show rule firing history."""
        console = get_console()
        init_db()
        shop_id = None
        if shop_identifier is not None:
            shop = _resolve_shop_identifier(shop_identifier)
            assert shop is not None
            shop_id = shop["id"]
        rows = list_rule_runs(
            rule_id=rule_id, wo_id=wo_id, shop_id=shop_id,
            matched_only=matched_only, since=since, limit=limit,
        )
        if as_json:
            click.echo(_json.dumps(
                [r.model_dump() for r in rows], default=str, indent=2,
            ))
            return
        if not rows:
            console.print("[dim]No rule runs match.[/dim]")
            return
        table = Table(title="Rule firing history", show_lines=False)
        table.add_column("Run", justify="right")
        table.add_column("Rule", justify="right")
        table.add_column("WO", justify="right")
        table.add_column("Event")
        table.add_column("Matched")
        table.add_column("Fired at")
        for r in rows:
            table.add_row(
                str(r.id), str(r.rule_id),
                str(r.work_order_id or "—"),
                str(r.triggered_event or "—"),
                "yes" if r.matched else "no",
                str(r.fired_at),
            )
        console.print(table)
