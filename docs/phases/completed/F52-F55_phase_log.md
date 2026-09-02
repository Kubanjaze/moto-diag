# F52 · F54 · F55 — Pre-Gate-10 Cleanup — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-02 | **Completed:** 2026-09-02
**Repos:** `Kubanjaze/moto-diag` + `Kubanjaze/moto-diag-mobile`, branch
`cleanup-f52-f55-pre-gate10`

---

### 2026-09-02 17:55 — Cleanup pass: three tickets + one stale phase status

Requested after a review of the pace through Phases 196B-200: five
same-day phases had left five follow-ups and one phase stuck at 🔄. The
brief was to close them before Gate 10 rather than carry them into it.

- **F55 (backend):** migration 046 adds nullable
  `diagnostic_sessions.customer_id`, backfilled from
  `vehicles.customer_id` **skipping the id-1 "Unassigned" sentinel** —
  the trap the ticket itself flagged. `resolve_session_customer_name`
  prefers the session column then falls back through the vehicle, which
  is the path that actually carries traffic since nothing writes the new
  column yet. Builder emits `prepared_for`; the Phase 200 HTML renderer
  shows "Prepared for <name>". Shape doc updated. SCHEMA_VERSION 45→46,
  both designed pins advanced.
- **F52 (both repos):** `AppDelegate` adopts
  `UNUserNotificationCenterDelegate`; JS gains a `notification`
  listener that always calls `finish()`; backend logs successful sends.
- **F52 caught a second bug on device — the important part.** The first
  build did the textbook thing (adopt the delegate, return presentation
  options) and the foreground JS event went SILENT. Root cause: once a
  notification-center delegate exists, iOS routes a foreground alert
  with no `content-available` to `willPresent` and stops calling
  `application(_:didReceiveRemoteNotification:fetchCompletionHandler:)`,
  which is the only place the library emits its JS event from. Fixed by
  forwarding the payload from `willPresent`. **Verified on device:**
  `[199 push] foreground notification` now appears with the app open,
  and because that log comes from the forward, it also proves the
  presentation options were returned.
- **F54 (backend):** `implementation.md` described `api` as "empty,
  awaiting Phase 175" and had no rows for `reporting`, `push`,
  `work_order_photos`, `voice_transcripts`, `cost_events`,
  `device_tokens` or `report_shares`; the `schema_version` row still
  said v38. All rewritten from the code. `ROADMAP_AUTHORITY.md` gains
  an **"Inventories are not status"** rule so the same correct reasoning
  ("Track I status lives in the mobile repo") stops taking the
  architecture sections down with it.
- **Phase 196 closed.** Ten days at 🔄 with finished code and tests. The
  outstanding item — BLE connect/handshake — needs a BLE-class adapter,
  because the reference dongle is classic Bluetooth. Re-scoped to
  **F56**; 196B already covers the product need. Docs → `completed/`.
  `docs/phases/in_progress/` is now empty.
- **Left open on purpose:** F51 (deep-link on tap) is phase-shaped work
  needing a navigation ref, though its native half now exists; F53
  (customer-queue push channel) cannot be built without a customer
  client.
