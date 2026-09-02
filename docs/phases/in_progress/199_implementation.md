# Phase 199 — Push Notifications (Mechanic-Facing, APNs)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-02

## Existing-code audit (Step 0 — run 2026-09-02, before this plan)

- **Backend substrate:** Phase 170 shipped a queue-only CUSTOMER
  notification system (`shop/notifications.py` — "expects a future
  transport layer"; channels email/sms/in_app; 10 events in
  `NOTIFICATION_EVENTS`). **Audience fork resolved by user decision:**
  199 pushes go to MECHANICS/app users (they have the app installed);
  the customer queue keeps its channels — a future customer `push`
  channel is explicitly out of scope (follow-up noted below).
- **Live event producers:** WO transitions (Phase 193 endpoints in
  `shop_mgmt.py`, RBAC'd, assigned-member model) + video analysis
  completion (Phase 191B/192 worker's atomic `analysis_state` update).
  `parts_arrived`/estimates/approvals have no producers yet (Phase 201+)
  — not wired (no dead wiring).
- **Mobile:** no push code anywhere (greenfield). Paid Apple Developer
  account signed in (2026-06-13 provisioning entry) — APNs keys
  available.
- **User decisions (2026-09-02):** mechanic-facing MVP · APNs direct
  (token/.p8 JWT auth) behind a `PushSender` seam (196 transport-seam
  precedent; FCM slots in when Android ships) · triggers = WO
  transitions + analysis-complete.
- **198 process lessons applied:** the mobile push dep gets a SPIKE GATE
  covering EVERY surface used (permission request + token callback, not
  just import); Step 0 data-invariant probe: `device_tokens` uniqueness
  = token string (one row per token; user rebinds on login switch).

## Goal

When a work order they're assigned to changes state, or a diagnostic
video analysis finishes, the mechanic's iPhone gets a push — locked
screen included. Backend registers device tokens, sends via APNs
directly (HTTP/2 + .p8 JWT), prunes dead tokens; mobile asks permission,
registers its token, and renders foreground notifications sanely.
Deep-linking from a tapped push into the WO/session is OUT of scope
(follow-up) — MVP lands the notification itself.

Run:
- Backend: `pytest tests/ -k phase199`; sender dry-run via
  `MOTODIAG_APNS_DRY_RUN=1` (logs instead of sending).
- Device smoke: transition a WO (curl/second session) → push arrives on
  the locked phone.

Outputs:
- **Backend (branch `phase-199-push-notifications`):**
  - migration: `device_tokens` (id, user_id FK, token UNIQUE, platform,
    created_at, last_seen_at) + SCHEMA_VERSION bump
  - `POST /v1/push/register` (authed; upsert token→user rebind) +
    `DELETE /v1/push/register` (sign-out hygiene)
  - `push/sender.py`: `PushSender` seam + `ApnsSender` (httpx[http2],
    PyJWT ES256 over the .p8; env: `MOTODIAG_APNS_KEY_PATH`, `_KEY_ID`,
    `_TEAM_ID`, `_TOPIC` (bundle id), `_SANDBOX`, `_DRY_RUN`) —
    verified LOCALLY first (inspect.signature/dry-run) per API frugality
  - hooks: WO transition endpoints + analysis-complete worker path →
    resolve recipient user(s) → send; APNs 410/Unregistered → prune token
  - tests: register/rebind/delete, sender payload shape vs a fake
    transport, hook wiring guards (transition fires exactly one send),
    prune-on-410
- **Mobile (branch `phase-199-push-notifications`):**
  - dep (SPIKE-GATED): `@react-native-community/push-notification-ios`
    — spike must exercise permission request + token callback +
    foreground-notification event under New Arch; FALLBACK (196B
    pattern): small Swift module wrapping
    `registerForRemoteNotifications` + delegate callbacks
  - `src/services/pushRegistration.ts`: permission → token →
    `POST /v1/push/register`; re-register on app start (token rotation);
    deregister on sign-out
  - wiring at the offlineBoot-style single integration point + cold-start
    guard extension
  - Xcode: Push Notifications capability (`aps-environment` entitlement)
  - tests: registration service vs fake module + api, guard extension
- **Apple-side (USER, one-time):** create an APNs Auth Key (.p8) in the
  developer portal (Keys → +, check APNs), note Key ID + Team ID, drop
  the .p8 at the env-configured path on the serve host.

## Logic

- Registration: app start → permission (first run prompts) → APNs token
  → upsert to backend keyed by token (token may move between users on
  shared devices — rebind, never duplicate).
- Sending: event → recipient user ids (WO: assigned member; analysis:
  session owner) → all their live tokens → APNs `alert` payload
  (title/body from compact mechanic-facing copy — NOT the Phase 170
  customer templates; those stay customer-voiced) + `thread-id` per WO.
- Failure: 410/`Unregistered` deletes the token row; transient errors
  log-and-continue (no retry queue in MVP — pushes are best-effort by
  nature; noted in Risks).
- Foreground: notification arrives while app open → dep's event → simple
  in-app banner/alert (MVP: system default presentation options).

## Key Concepts

- `PushSender` seam + `MOTODIAG_APNS_DRY_RUN` make every backend test
  and the first live run cheap (API-frugality: one clean live send).
- APNs sandbox vs production topic: Debug builds use the sandbox
  gateway (`_SANDBOX=1` default in dev).
- SSOT: event names reuse `NOTIFICATION_EVENTS` strings where they
  overlap (wo_* states) — no parallel vocabulary.
- 198 lesson applied: spike gate covers permission + token + foreground
  event — all three surfaces the build touches.

## Verification Checklist

- [ ] Apple-side key created; env configured on the serve host
- [ ] Backend: migration + register/rebind/delete + sender (fake
      transport + dry-run) + hook guards green on canonical interpreter
- [ ] Mobile spike gate: permission prompt + token callback (+ foreground
      event) verified on-device under New Arch — PASS recorded
- [ ] Mobile: registration service green; cold-start guard extended;
      entitlement present
- [ ] Full suites green both repos; tsc clean
- [ ] Device smoke: WO transition (curl/second actor) → push on LOCKED
      phone; analysis-complete → push; 410-prune observed or covered by
      test; recorded here + phase log

## Risks

- **APNs setup friction** (key, entitlement, sandbox-vs-prod topic
  mismatches) — dry-run + sandbox default; the smoke uses Debug/sandbox.
- **Best-effort delivery** (no retry queue in MVP): acceptable for
  notifications; revisit only if the shop workflow starts DEPENDING on
  them (would pair with the 170 queue's status discipline).
- **Dep New-Arch risk** (community push lib ages): spike-gated with a
  scoped native-module fallback, per 196B/198 precedent.
- **Recipient resolution edge cases** (unassigned WOs, self-transitions
  — don't push a mechanic about their own tap): self-suppression rule in
  the hooks, tested.
- Deep-linking from tap deferred (follow-up filed at close).
