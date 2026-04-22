# MotoDiag Phase 170 — Customer Communication

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-22

## Goal

Template-rendered, audit-logged customer notifications for shop-workflow
events — status transitions (opened / in-progress / on-hold / completed /
cancelled), invoice milestones (issued / paid), parts milestones (parts
arrived), and explicit estimate-ready / approval-requested messages.
**This phase owns the templating + persistence + rendering + CLI.** It
does NOT send email/SMS — actual delivery is out of scope (deferred to
infrastructure in Track J). Every notification persists to
`customer_notifications` with a status lifecycle of
`pending → sent|failed|cancelled`; the mechanic (or Phase 173 automation)
transitions status explicitly. This lets the shop's existing email/SMS
workflow (or a later Phase 181+ transport) consume the queue.

CLI — `motodiag shop notify {trigger, preview, list, mark-sent,
mark-failed, cancel, templates, resend}` — 8 subcommands.

**Design rule:** zero AI, zero tokens, zero network. Pure templating +
SQL. Pydantic models at the module boundary; `string.Template` for
placeholders (safer than f-strings for user-supplied content).
Forward-compat: Phase 181+ transport will add a worker that picks up
`status='pending'` rows and does the actual send, flipping them to
`sent` or `failed`.

Outputs:
- Migration 034 (~40 LoC): creates `customer_notifications` table +
  3 indexes. No existing-table ALTERs.
- `src/motodiag/shop/notifications.py` (~550 LoC) — trigger / preview /
  render / mark-sent / mark-failed / cancel / resend / list /
  _load_event_context / 3 Pydantic / 3 exceptions.
- `src/motodiag/shop/notification_templates.py` (~150 LoC) — 10
  built-in templates + `get_template(event, channel)` + dispatch map.
- `src/motodiag/shop/__init__.py` +20 LoC re-exports.
- `src/motodiag/cli/shop.py` +260 LoC — `notify` subgroup with 8
  subcommands + `_render_notification_panel` helper.
- `src/motodiag/core/database.py` SCHEMA_VERSION 33 → 34.
- `tests/test_phase170_notifications.py` (~30 tests across 6 classes).

## Logic

### Migration 034

```sql
CREATE TABLE IF NOT EXISTS customer_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    shop_id INTEGER NOT NULL,
    work_order_id INTEGER,       -- nullable for generic customer messages
    invoice_id INTEGER,           -- nullable
    event TEXT NOT NULL CHECK(event IN (
        'wo_opened', 'wo_in_progress', 'wo_on_hold', 'wo_completed',
        'wo_cancelled', 'invoice_issued', 'invoice_paid',
        'parts_arrived', 'estimate_ready', 'approval_requested'
    )),
    channel TEXT NOT NULL CHECK(channel IN ('email', 'sms', 'in_app')),
    recipient TEXT NOT NULL,      -- rendered at trigger-time from customer
    subject TEXT,                 -- nullable (SMS has no subject)
    body TEXT NOT NULL,           -- rendered template body
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN (
        'pending', 'sent', 'failed', 'cancelled'
    )),
    failure_reason TEXT,          -- populated on status='failed'
    triggered_by_user_id INTEGER, -- FK soft-reference to users.id
    triggered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
    FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
    FOREIGN KEY (work_order_id) REFERENCES work_orders(id) ON DELETE SET NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL
);
CREATE INDEX idx_notif_customer ON customer_notifications(customer_id, triggered_at DESC);
CREATE INDEX idx_notif_shop_status ON customer_notifications(shop_id, status);
CREATE INDEX idx_notif_wo ON customer_notifications(work_order_id);
```

Rollback drops indexes + table cleanly.

### `shop/notifications.py` — function inventory

```python
def trigger_notification(
    event: NotificationEvent,
    *,
    wo_id: Optional[int] = None,
    invoice_id: Optional[int] = None,
    customer_id: Optional[int] = None,  # required if wo_id + invoice_id both None
    channel: NotificationChannel = "email",
    extra_context: Optional[dict] = None,  # arbitrary template overrides
    db_path: Optional[str] = None,
) -> int:
    """Render template for event + persist as status='pending'. Returns
    notification_id. Resolves customer from WO, invoice, or explicit id.
    Raises NotificationContextError if context cannot be assembled.
    """

def preview_notification(
    event: NotificationEvent,
    *, wo_id=None, invoice_id=None, customer_id=None,
    channel="email", extra_context=None, db_path=None,
) -> NotificationPreview:
    """Render without persisting. For --dry-run."""

def mark_notification_sent(
    notification_id: int,
    sent_at: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Transition pending → sent."""

def mark_notification_failed(
    notification_id: int,
    failure_reason: str,
    db_path: Optional[str] = None,
) -> bool:
    """Transition pending → failed."""

def cancel_notification(
    notification_id: int, reason: Optional[str] = None,
    db_path: Optional[str] = None,
) -> bool:
    """Transition pending → cancelled (explicit mechanic action)."""

def resend_notification(
    notification_id: int, db_path: Optional[str] = None,
) -> int:
    """Create a new 'pending' row duplicating a prior sent/failed one.
    Returns new notification_id. Source row is untouched (audit trail)."""

def list_notifications(
    *, customer_id=None, shop_id=None, wo_id=None,
    status=None, event=None, since=None, limit=100,
    db_path=None,
) -> list[dict]:
    """Composable filter query."""

def get_notification(
    notification_id: int, db_path: Optional[str] = None,
) -> Optional[Notification]:
    """Single-row fetch."""
```

**Guarded status lifecycle** (mirrors Phase 161 work-order pattern):

| From       | → pending | → sent | → failed | → cancelled |
|------------|-----------|--------|----------|-------------|
| pending    |           | ✓      | ✓        | ✓           |
| sent       |           |        |          |             |
| failed     |           | ✓\*    |          |             |
| cancelled  |           |        |          |             |

\* Only via `resend_notification` which creates a NEW pending row rather
than mutating the failed one — preserves the failure audit trail.

Pydantic models: `Notification` (full row), `NotificationPreview`
(rendered subject/body/recipient without id), `NotificationContext`
(assembled template context).

Exceptions: `NotificationContextError` (can't resolve WO/customer/shop),
`UnknownEventError` (event not in CHECK list), `NotificationNotFoundError`.

### `shop/notification_templates.py` — content

10 built-in templates, one per event × channel where both email and SMS
make sense. Email templates have subject + body; SMS are body-only (160
char target); in_app templates are body-only + short-form.

Template placeholders use `string.Template` syntax (`$customer_name`,
`$shop_name`, `$wo_id`, `$wo_title`, `$wo_status`, `$invoice_number`,
`$invoice_total`, `$parts_list`, `$estimate_total`). Unresolved
placeholders raise `NotificationContextError` — better than emitting
"Hello $customer_name" to a customer.

Content principles (from motorcycle-mechanic feedback):
- First-name recipient; no "Dear Sir/Madam"
- Include WO number + shop phone in every message so the customer can
  reply/call with context
- Plain language — no service-writer jargon ("bike" not "motorcycle
  vehicle"; "done" not "completed and ready for pickup retrieval")
- Approval-requested and estimate-ready messages include the total cost
  prominently; no fine print
- Completed message includes pickup hours if shop has `hours_json` set
- Parts-arrived message says which WO + which parts so mechanic and
  customer can confirm before install

Example templates (excerpt):

```
wo_completed (email):
  Subject: Your $bike_label is ready — WO #$wo_id
  Body: Hey $customer_first, good news — your $bike_label is done.
        Final total: $$invoice_total. $shop_hours_line
        Questions? Call $shop_phone.
        — $mechanic_first at $shop_name

wo_completed (sms):
  Your $bike_label is done (WO #$wo_id). Total $$invoice_total.
  Pickup: $shop_hours_short. $shop_phone.

invoice_issued (email):
  Subject: Invoice $invoice_number — $$invoice_total
  Body: Hey $customer_first — attached is invoice $invoice_number for
        the work on your $bike_label. $$invoice_total total. Pay when
        convenient; we can take cash, card, or bank transfer.
        — $shop_name

parts_arrived (sms):
  WO #$wo_id: parts came in ($parts_list). Scheduling install; we'll
  text when ready. — $shop_name
```

### `_load_event_context` (private helper)

Assembles template context by pulling:
- WO row (Phase 161 `get_work_order`) → title/status/priority/estimated_hours
- Customer row → first-name extraction (`.split()[0]`)
- Vehicle → `year make model` → `bike_label`
- Shop → name/phone/hours_json → `shop_hours_line` ("Pickup hours: M-F 8-5, Sat 9-3") and `shop_hours_short` ("M-F 8-5")
- Invoice (if invoice_id OR if event in {invoice_*, wo_completed}) → number/total/status
- Parts (for parts_arrived) → comma-joined `description` from installed rows

`extra_context` kwarg merges on top (override for edge cases — e.g.,
Phase 173 automation might inject a custom `next_step` placeholder).

### CLI subgroup

```
notify trigger EVENT [--wo WO_ID | --invoice INVOICE_ID | --customer CUSTOMER_ID]
                     [--channel email|sms|in_app] [--extra JSON] [--json]
notify preview EVENT [--wo WO_ID | --invoice INVOICE_ID | --customer CUSTOMER_ID]
                     [--channel email|sms|in_app] [--extra JSON] [--json]
notify list [--shop X] [--customer X] [--wo X] [--status pending|sent|failed|cancelled]
            [--event EVT] [--since 30d] [--limit 50] [--json]
notify mark-sent NOTIFICATION_ID [--sent-at ISO]
notify mark-failed NOTIFICATION_ID --reason "bounce: invalid email"
notify cancel NOTIFICATION_ID [--reason X]
notify templates [--json]          # list all 10 events × 2-3 channels
notify resend NOTIFICATION_ID      # new pending row dup of source
```

## Key Concepts

- **Queue, not transport.** Phase 170 writes to `customer_notifications`
  with status='pending' and expects a future transport layer (Phase 181+
  or operator's own integration) to pick up, send, and flip the status.
  This decouples content rendering from delivery mechanics.
- **`string.Template`, not f-strings.** Safer with user-derived content
  (customer names, notes) — no arbitrary code execution risk, and
  `Template.substitute` raises cleanly on unresolved placeholders.
- **Audit-log-only lifecycle.** Notifications are never updated in place
  except for status transitions. Resend creates a new row so the failure
  audit survives. This matches Phase 162's issues-lifecycle pattern.
- **Template channel matrix**: most events have email + sms variants;
  `in_app` is a subset (only wo_opened / wo_completed / approval_requested
  make sense as in-shop mechanic dashboard blips).
- **Shop hours rendering**: Phase 160 stores `shop.hours_json` as a JSON
  object like `{"mon": "08:00-17:00", ...}` — this phase formats it to
  human-readable `"M-F 8am-5pm, Sat 9am-3pm"` via `_format_hours_line`
  (pure function; tested).
- **No write-back to WO/invoice.** Phase 170 reads those tables but
  never writes to them. Notifications are downstream state.

## Verification Checklist

- [ ] Migration 034 creates `customer_notifications` with all CHECK
      constraints + 3 indexes.
- [ ] SCHEMA_VERSION 33 → 34.
- [ ] Rollback to 33 drops table + indexes cleanly.
- [ ] `trigger_notification` for each event renders the correct template
      and persists pending row.
- [ ] Missing placeholder raises `NotificationContextError` (no partial
      "Hello $customer_name" leaks).
- [ ] Unknown event rejected at CHECK constraint.
- [ ] `preview_notification` returns rendered content without persisting
      (DB row count unchanged).
- [ ] Lifecycle: pending → sent / failed / cancelled works; sent →
      anything raises; resend of sent creates NEW pending row.
- [ ] Template dispatch: `(event, channel)` pair resolves correctly;
      missing channel raises clean error.
- [ ] Shop hours rendering: empty → "(call for hours)", full week →
      "M-F 8am-5pm, Sat 9am-3pm", custom schedule rendered correctly.
- [ ] `list_notifications` composable filters (by customer, shop, WO,
      status, event, since).
- [ ] CLI `notify {trigger,preview,list,mark-sent,mark-failed,cancel,
      templates,resend}` round-trip.
- [ ] Phase 113/118/131/153/160-169 tests still GREEN.
- [ ] Zero AI calls.

## Risks

- **Template placeholder drift.** If a template references `$next_step`
  but `_load_event_context` doesn't populate it, every trigger fails
  with `NotificationContextError`. Mitigation: test each template
  renders against a populated fixture; placeholder presence asserted
  per-event. `extra_context` kwarg provides an explicit escape hatch
  for Phase 173 automation rules that want to inject custom fields.
- **Shop hours formatting edge cases.** Customers in different
  timezones, 24-hour shops, holiday hours — this phase formats whatever
  the shop entered in `hours_json` literally. Mitigation: format helper
  has fallback "(call for hours)" when input is empty/invalid; tests
  cover the common case (Mon-Fri + Sat) and the empty case.
- **Queue-without-transport confusion.** Mechanics might expect
  `trigger_notification` to actually send the email. Mitigation: CLI
  `notify trigger` output explicitly says "Notification #NN queued;
  mark sent with `notify mark-sent NN` once delivered" to avoid the
  "I triggered it but nothing happened" support case. Template
  examples include the expected mechanic flow.
- **Invoice total formatting.** Invoice table stores dollar floats;
  template needs `$invoice_total` as "1,234.56". Mitigation:
  `_format_money_cents` helper (cents → "1,234.56") reused from Phase
  169 convention; test rendering at $0, $9.99, $12345.67.
- **Channel-specific character limits.** SMS at 160 chars is tight —
  templates use abbreviations (WO #, pickup hours short-form). Test
  asserts SMS bodies for all events stay under 320 chars (double-part
  SMS is acceptable; triple-part is not).
