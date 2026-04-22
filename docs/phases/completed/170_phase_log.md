# MotoDiag Phase 170 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-22 | **Completed:** 2026-04-22
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-22 — Plan written

Plan v1.0 authored in-session (serial per-phase discipline). Scope:
template-rendered audit-logged customer notifications for shop-workflow
events. **This phase owns templates + persistence + CLI only; actual
email/SMS delivery is deferred to Track J transport infrastructure.**
Notifications persist as `status='pending'` in a new
`customer_notifications` table; mechanic (or Phase 173 automation)
transitions to `sent`/`failed`/`cancelled` explicitly.

Key design decisions:
- `string.Template` placeholders (safer than f-strings with user content).
- Guarded status lifecycle mirroring Phase 161 work-order pattern —
  `sent` is terminal; `resend` creates a new pending row rather than
  mutating the failed one.
- 10 built-in event templates × 2-3 channels each (email + sms + in_app).
- Content principles baked from motorcycle-mechanic feedback: first-name
  recipient, WO # + shop phone in every message, plain language, prominent
  totals, shop hours in completed/pickup messages.
- `_load_event_context` pulls WO + customer + vehicle + shop + optional
  invoice + optional parts into a single template-context dict;
  `extra_context` kwarg overrides for Phase 173 automation edge cases.
- Zero AI, zero network, zero tokens. Pure templating + SQL.

### 2026-04-22 — Build complete

Files shipped:

1. **Migration 034** (schema v33→v34) — `customer_notifications` table
   with 4 FKs (customer/shop CASCADE, work_order_id + invoice_id SET
   NULL), 2 CHECK constraints (event + channel whitelists), 3 indexes
   (customer+triggered_at, shop+status, wo).

2. **`shop/notification_templates.py`** (~265 LoC) — `NotificationTemplate`
   class + 23 registered templates across 10 events × email/sms/in_app
   channels. `get_template(event, channel)` + `list_templates()` +
   `UnknownEventError` + `TemplateNotFoundError`.

3. **`shop/notifications.py`** (~510 LoC) — 2 Pydantic models
   (`Notification` + `NotificationPreview`), 3 exceptions, 8 public
   functions (`trigger_notification`, `preview_notification`,
   `mark_notification_sent`, `mark_notification_failed`,
   `cancel_notification`, `resend_notification`, `list_notifications`,
   `get_notification`), 7 private helpers (event-context assembler,
   shop-hours formatter, money formatter, recipient picker, etc.),
   `_VALID_TRANSITIONS` dict driving the guarded lifecycle.

4. **`shop/__init__.py`** +26 re-exports.

5. **`cli/shop.py`** +292 LoC — `notify` subgroup with **8 subcommands**
   (`trigger`, `preview`, `list`, `mark-sent`, `mark-failed`, `cancel`,
   `resend`, `templates`) + `_render_notification_panel` helper. Total
   `cli/shop.py` now ~4640 LoC across 13 subgroups and 96 subcommands.

6. **`tests/test_phase170_notifications.py`** (32 tests across 6 classes):
   - `TestMigration034` (5): schema version, table, indexes, CHECK
     enforcement, rollback.
   - `TestTemplates` (5): catalog covers all 10 events, ≥2 channels per
     event, email subjects present, unknown event raises, render
     substitutes placeholders.
   - `TestTriggerAndPreview` (9): preview doesn't persist, trigger
     persists pending, SMS/email channel requires phone/email, unknown
     event raises, wo_completed includes invoice total, shop hours
     render, extra_context overrides, channel-specific recipient.
   - `TestLifecycle` (5): mark-sent, mark-failed + reason required,
     cancel, resend creates new pending, illegal transition raises.
   - `TestListing` (3): composable filters, bogus status/event rejected.
   - `TestNotifyCLI` (5): preview / trigger / mark-sent / list / resend
     CLI round-trip.

**Key build discoveries:**
- `string.Template` dollar-sign escape: `$$$identifier` (not
  `\$$identifier`) to render `$<value>`. Caught + fixed via template
  render spot-check before tests ran.
- `_format_hours_line` fallback uses `"call $shop_phone"` so the outer
  render substitutes shop_phone, giving `"Pickup hours: call 555-1212"`
  without hardcoding an "(unknown)" string.
- Event-context assembler resolves from any of `wo_id`/`invoice_id`/
  `customer_id`; the last mode requires the customer to have at least
  one prior WO so shop can be inferred.

**Tests:** 32 GREEN in 20.35s. Single pass — zero test fixes needed.

**Targeted regression: 543 GREEN in 341.61s (5m 42s)** covering Phase
113 (CRM) + Phase 118 (accounting) + Phase 131 + 153 + Track G 160-170
+ Phase 162.5. Zero regressions.

Build deviations vs plan:
- Dollar-escape in templates discovered + fixed during build.
- `_format_hours_line` fallback strategy (inline `$shop_phone`
  directive) chosen over hardcoded "(call for hours)".
- 32 tests vs ~30 planned (+2 coverage on channel-recipient + extra-
  context paths).

### 2026-04-22 — Documentation finalization

`implementation.md` promoted to v1.1. Verification Checklist all `[x]`.
Deviations + Results sections appended. Key finding captures customer-
comms plumbing design: decouple content rendering (this phase) from
delivery (Phase 181+ transport). Template catalog covers every Track G
lifecycle event Phase 173 automation rules might want to fire.

Project-level updates:
- `implementation.md` schema_version footnote v33 → v34
- `implementation.md` Database Tables: append `customer_notifications`
- `implementation.md` Phase History: append Phase 170 row
- `implementation.md` Shop CLI Commands: 88 → 96 subcommands; added
  `motodiag shop notify` row (13th subgroup)
- `phase_log.md` project-level: Phase 170 closure entry
- `docs/ROADMAP.md`: Phase 170 row → ✅
- Project version 0.10.1 → **0.10.2** (Track G comms plumbing landed)

**Key finding:** Phase 170 validates the "plumbing before transport"
pattern. By writing rendered, audit-logged notifications to a queue
(status='pending') with an explicit transition to sent/failed/cancelled,
the actual delivery integration becomes a pluggable worker rather than
module-internal logic. Any operator can wire Twilio or SendGrid today
by polling `SELECT * FROM customer_notifications WHERE status='pending'`
and calling `mark_notification_sent(id)` or `mark_notification_failed(id,
reason=...)`. Phase 181+ will add a supervised worker process; Phase
173 will wire `trigger_notification(...)` as the action side of
workflow-automation rules. The `string.Template` choice (vs f-strings)
paid off — caught the one placeholder-drift bug at render time with a
clean `NotificationContextError` rather than leaking a half-rendered
"$customer_name" to a live customer.
