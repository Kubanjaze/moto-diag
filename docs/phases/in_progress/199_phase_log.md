# Phase 199 — Push Notifications (Mechanic-Facing, APNs) — Phase Log

**Status:** 📋 Planned
**Started:** 2026-09-02 | **Completed:** —
**Repos:** `Kubanjaze/moto-diag` + `Kubanjaze/moto-diag-mobile`, both on
branch `phase-199-push-notifications`

---

### 2026-09-02 15:35 — Plan written (Step 0 audit + v1.0)

- **Step 0 finding:** Phase 170's queue-only customer-notification system
  is the adjacent substrate ("expects a future transport layer") — but
  its audience is bike-owner customers (email/sms/in_app). User resolved
  the audience fork: **199 pushes to mechanics/app users** (the people
  with the app); the customer queue's future push channel is explicitly
  out of scope. Live producers wired: WO transitions (193) + analysis
  complete (191B/192). Mobile push = greenfield.
- **User decisions:** mechanic-facing MVP · **APNs direct** (.p8 JWT,
  httpx/h2) behind a `PushSender` seam (FCM later when Android ships) ·
  triggers = WO transitions + analysis-complete.
- **198 lessons pre-applied:** mobile dep spike gate must cover
  permission + token callback + foreground event (every surface used);
  `device_tokens` invariant decided up front (UNIQUE token, rebind on
  user switch).
- **User-side prerequisite:** APNs Auth Key (.p8) from the developer
  portal + Push Notifications capability in Xcode.
- **Next milestone:** plan commit + push → backend build (migration,
  register endpoint, sender + dry-run, hooks) → mobile spike → build →
  locked-phone smoke.
