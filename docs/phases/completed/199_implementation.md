# Phase 199 — Push Notifications (Mechanic-Facing, APNs)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-02 (v1.0 plan 15:35 → v1.1 as-built 17:00)

## Existing-code audit (Step 0 — run 2026-09-02, before this plan)

- **Backend substrate:** Phase 170 shipped a queue-only CUSTOMER
  notification system (`shop/notifications.py` — "expects a future
  transport layer"; channels email/sms/in_app; 10 events in
  `NOTIFICATION_EVENTS`). **Audience fork resolved by user decision:**
  199 pushes go to MECHANICS/app users (they have the app installed);
  the customer queue keeps its channels — a future customer `push`
  channel is explicitly out of scope (follow-up F53).
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
- **As-built audit note (v1.1):** the "Xcode: Push Notifications
  capability" prerequisite was SATISFIED IN NAME ONLY at spike time —
  Xcode had attached the entitlements file to the Release configuration
  only, so the Debug build the spike ran on carried no `aps-environment`.
  Verifying the SIGNED binary (`codesign -d --entitlements`) — not the
  project settings — is the audit step that would have caught it.

## Goal

When a work order they're assigned to changes state, or a diagnostic
video analysis finishes, the mechanic's iPhone gets a push — locked
screen included. Backend registers device tokens, sends via APNs
directly (HTTP/2 + .p8 JWT), prunes dead tokens; mobile asks permission,
registers its token on every cold start, re-syncs after sign-in and
deregisters on sign-out. Deep-linking from a tapped push (F51) and
in-app presentation while the app is foregrounded (F52) are follow-ups —
MVP lands the notification itself, and it did.

Run:
- Backend: `pytest tests/test_phase199_push.py`; sender dry-run via
  `MOTODIAG_APNS_DRY_RUN=1` (default; logs instead of sending). Live:
  `pip install -e ".[push]"` once, then serve with
  `MOTODIAG_APNS_DRY_RUN=0 MOTODIAG_APNS_KEY_PATH=<.p8> MOTODIAG_APNS_KEY_ID=…
  MOTODIAG_APNS_TEAM_ID=… MOTODIAG_APNS_TOPIC=com.bandithero.motodiag`
  (`MOTODIAG_APNS_SANDBOX=1` default → Debug builds).
- Device smoke: assign/transition a WO as a SECOND user (curl) → push on
  the phone (app terminated or backgrounded so iOS renders the banner).
- Reading the app's console on RN 0.85: Metro no longer prints
  `console.log`; attach to Metro's CDP inspector instead (see Key
  Concepts).

Outputs (as built):
- **Backend (`98008f7` on `phase-199-push-notifications`):**
  - migration 044 `device_tokens` (id, user_id FK, token UNIQUE,
    platform, created_at, last_seen_at); SCHEMA_VERSION 43 → 44 (the two
    designed pin tests advanced per their contract comments)
  - `src/motodiag/push/` package: `registry.py` (register/rebind/delete/
    tokens_for_user), `sender.py` (`PushSender` Protocol seam,
    `DryRunSender`, lazy-import `ApnsSender` — httpx HTTP/2 + PyJWT ES256
    over the .p8, 45-min JWT reuse, sandbox/prod host switch, 410 →
    `unregistered`), `events.py` (recipient resolution + mechanic-voiced
    copy + self-suppression + 410-prune; every entry best-effort)
  - `api/routes/push.py`: `POST /v1/push/register` (upsert/rebind) +
    `DELETE /v1/push/register`; TAG_CATALOG `push` entry
  - hooks: `shop_mgmt.py` transition + assign endpoints → `notify_wo_*`;
    analysis worker → `notify_analysis_complete`
  - `pyproject.toml` `[push]` extra (httpx[http2], PyJWT, cryptography)
  - `tests/test_phase199_push.py` (12): registry register/rebind/delete,
    endpoint auth/roundtrip/deregister, events copy + self-suppression +
    410-prune + analysis-complete, hook wiring guards
- **Mobile (`9ea2538` spike WIP → `bb6758c` build):**
  - dep `@react-native-community/push-notification-ios` (spike-gated;
    the Swift-module fallback was NOT needed once the bridging header
    resolved the import)
  - native: `AppDelegate.swift` remote-notification delegate methods →
    `RNCPushNotificationIOS`; `MotoDiag-Bridging-Header.h` (the pod
    defines no Swift module) wired via `SWIFT_OBJC_BRIDGING_HEADER` on
    both configs; `CODE_SIGN_ENTITLEMENTS` added to the **Debug** config
    (was Release-only) → `aps-environment=development` in the signed
    Debug binary
  - `src/services/pushRegistration.ts`: `startPushRegistration()`
    (listeners → `requestPermissions` → token → AsyncStorage → POST),
    `resyncPushRegistration()` (after sign-in), `deregisterPushToken()`
    (DELETE before the key is cleared), `registerPushToken()`; injectable
    deps (push module / api adapter / token store / platform); iOS-only
    no-op elsewhere; best-effort with loud `[199 push]` logging
  - `App.tsx` cold-mount wiring beside `startOfflineBoot()` + `stop()` on
    unmount; `HomeScreen` resync-after-`setApiKey` / deregister-before-
    `clearApiKey`; spike file + block deleted
  - `api-schema/openapi.json` + `src/api-types.ts` refreshed
  - tests: `__tests__/services/pushRegistration.test.ts` (11) +
    `App.coldStart.smoke.test.tsx` guard extended + `jest.setup.js`
    global mock for the native lib
- **Apple-side (user, done):** APNs Auth Key `.p8` at
  `~/Projects/apns/` (outside both repos); Key ID / Team ID / topic in
  the ledger; Push Notifications capability in Xcode.

## Logic

- Registration: cold mount → listeners attached FIRST → permission
  request (prompts on first run; already-authorized installs get the
  token immediately) → APNs token → persisted locally → upsert to the
  backend keyed by token (rebind on user switch, never duplicate). First
  launch: the token lands before an API key exists → the POST 401s →
  `resyncPushRegistration()` re-POSTs the stored token once a key is
  set. Sign-out: DELETE while still authed, then clear the key.
- Sending: event → recipient user id (WO: assigned member; analysis:
  session owner) → all their live tokens → APNs `alert` payload
  (mechanic-voiced title/body — NOT the Phase 170 customer templates) +
  `thread-id` per WO/session, `apns-priority` 10, sound default.
- Failure: 410/`Unregistered` deletes the token row; transient errors
  `logger.warning` and continue (no retry queue in MVP). Misconfigured
  APNs env degrades to the dry-run sender with a warning — never a
  crash in the request path.
- Self-suppression: no push to a user about an action they performed.
- Foreground: NOT delivered in MVP (deviation, see below) — iOS shows
  nothing for a foregrounded app without a `willPresent` delegate; F52.

## Key Concepts

- `PushSender` seam + `MOTODIAG_APNS_DRY_RUN` make every backend test
  and the first live run cheap (API-frugality: one clean live send).
- APNs sandbox vs production gateway: Debug builds (development
  `aps-environment`) MUST hit `api.sandbox.push.apple.com`
  (`MOTODIAG_APNS_SANDBOX=1` default).
- **Three native prerequisites, all silent when missing:** (1) the
  AppDelegate delegate methods (the lib's documented wiring), (2) a way
  for Swift to see the pod's ObjC class — the podspec defines no module,
  so `import RNCPushNotificationIOS` fails with *no such module*; use a
  bridging header with `#import <RNCPushNotificationIOS/
  RNCPushNotificationIOS.h>`, (3) `aps-environment` on the build config
  actually being run — verify on the signed binary with `codesign -d
  --entitlements :- <app>`.
- **RN 0.85 dev loop:** Metro stopped forwarding app `console.log`.
  `GET http://localhost:8081/json` lists the Hermes target; open its
  `webSocketDebuggerUrl` with header `Origin: http://localhost:8081`
  (the inspector proxy rejects other origins with 401), send
  `Runtime.enable` → Hermes replays its cached console, so a late attach
  still shows cold-start lines. Script kept at
  `~/Projects/p199_cdp_console.cjs`. Build/install without the Xcode
  Run button: `xcodebuild -workspace … -destination id=<udid>
  -allowProvisioningUpdates build` → `xcrun devicectl device install
  app` → `xcrun devicectl device process launch --terminate-existing`.
- SSOT: WO action verbs map from the Phase 193 transition actions; no
  parallel event vocabulary.
- 198 lesson applied: the spike gate covered permission + token +
  error surfaces on-device before the service was written.

## Verification Checklist

- [x] Apple-side key created; env configured on the serve host
      (`~/Projects/apns/AuthKey_5F2J49F8UT.p8`; serve restarted with the
      live env on this Mac)
- [x] Backend: migration + register/rebind/delete + sender (fake
      transport + dry-run) + hook guards green — 12 tests; full
      regression 4622 passed; pins + 199 rerun 30 passed
- [x] Mobile spike gate: permission prompt + token callback +
      registrationError surface verified on-device under New Arch —
      PASS 16:21 (`register event: token(64 chars)`). Foreground
      `notification` listener attached without throwing (spike); actual
      foreground presentation deferred (F52)
- [x] Mobile: registration service green (11 tests); cold-start guard
      extended; entitlement present on the SIGNED Debug binary
- [x] Full suites green both repos; tsc clean (mobile 69 suites / 864
      tests; eslint 0 errors)
- [x] Device smoke: app → `POST /v1/push/register 200` → `device_tokens`
      row; WO **assign** + **open transition** by a second user (curl,
      self-suppression not triggered) → hook path completed with zero
      APNs failure warnings; direct `ApnsSender.send` to the phone's
      token → `PushResult(ok=True)` from `api.sandbox.push.apple.com`;
      app terminated before sending so iOS renders the banners.
      **On-screen/lock-screen visual confirmation is the user's** (no
      remote screenshot path for a physical iPhone from this session;
      the three notifications persist in Notification Center).
      410-prune covered by test (no dead token available to observe).
      Analysis-complete NOT device-smoked (no video handy) — covered by
      the events test.

## Risks

- **APNs setup friction** — MATERIALIZED, three ways at once: missing
  delegate methods, Swift module resolution, Debug-config entitlement.
  All resolved in `bb6758c`; the "verify the signed binary" audit step
  is the durable lesson.
- **Best-effort delivery** (no retry queue in MVP): acceptable for
  notifications; revisit only if the shop workflow starts DEPENDING on
  them (would pair with the 170 queue's status discipline). Sends that
  fail log a warning; successes are silent at INFO — a success log line
  would help future smokes (folded into F52's scope).
- **Dep New-Arch risk** (community push lib ages): the lib itself worked
  under New Arch; the risk that bit was the missing Swift module map,
  not the runtime. Fallback native module NOT needed.
- **Recipient resolution edge cases** (unassigned WOs, self-transitions):
  self-suppression rule in the hooks, tested.
- **Foreground presentation gap** (new): with the app open, iOS renders
  no banner unless the app implements
  `UNUserNotificationCenterDelegate.willPresent` — mechanics tapping
  around the app during a transition see nothing until they background
  it. Filed F52.
- Deep-linking from tap deferred — F51.

## Deviations from Plan

- **Foreground notification handling not delivered.** Plan v1.0 listed
  "renders foreground notifications sanely" and a foreground-event
  spike surface. The spike only verified the listener attaches; the
  build ships no `notification` listener and no `willPresent` delegate.
  Scoped out consciously at close (MVP = the push itself) and filed as
  F52 rather than rushed in after the smoke.
- **Native fixes beyond the plan's "capability + delegate" list:**
  bridging header (Swift module resolution) and Debug-config
  entitlements — see Key Concepts.
- **Dev-loop tooling change:** Xcode Run + console filter replaced by
  `xcodebuild` + `devicectl` + a CDP console reader (RN 0.85 Metro
  behaviour), recorded in the ledger for future smokes.
- **Smoke evidence shape:** APNs-accepted (sandbox 200) + hook path
  clean, with visual lock-screen confirmation left to the user — the
  session had no remote view of the physical phone.

## Results

| Metric | Value |
|--------|-------|
| Backend new tests | 12 (`test_phase199_push.py`) |
| Backend full regression | 4622 passed (2 designed SCHEMA_VERSION pins advanced 43→44) |
| Mobile new tests | +11 → 69 suites / 864 tests green |
| Mobile static checks | tsc clean · eslint 0 errors |
| Spike gate | PASS — token(64 chars), authorizationStatus 2, lockScreen/alert/sound true |
| Device registration | `POST /v1/push/register` 200 → `device_tokens` row (user 1, ios) |
| Smoke sends | 3 (assign, open transition, direct check); APNs sandbox `ok=True`; 0 failure warnings |
| Root causes behind the silent token | 3 (delegate methods · Swift module map · Debug entitlement) |
| Commits | backend `42cd51f` plan · `98008f7` build · `4c4e56e` ledger · close docs; mobile `9ea2538` spike · `bb6758c` build · close docs |

**Key finding:** a silent native callback usually has more than one
cause stacked behind it — fixing the first (delegate methods) exposed
the second (module resolution) and only the signed-binary check exposed
the third (Debug entitlement). Spike gates for native surfaces should
verify the *artifact* (signed entitlements, build log) as well as the
*behaviour*, because iOS reports each of these failures to a callback
that is itself missing.
