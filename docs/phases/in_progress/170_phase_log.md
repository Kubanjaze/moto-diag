# MotoDiag Phase 170 — Phase Log

**Status:** 🟡 In Progress | **Started:** 2026-04-22
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
