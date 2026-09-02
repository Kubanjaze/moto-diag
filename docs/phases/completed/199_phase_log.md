# Phase 199 — Push Notifications (Mechanic-Facing, APNs) — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-02 | **Completed:** 2026-09-02
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

---

### 2026-09-02 16:10 — Session handoff: backend DONE, mobile spike gate IN PROGRESS

**Done this session:**
- **Backend build (`98008f7`, pushed):** migration 044 `device_tokens`
  (SCHEMA_VERSION 44) · `push/` package (registry, PushSender seam w/
  DryRunSender + lazy ApnsSender, events glue w/ self-suppression +
  410-prune) · POST/DELETE `/v1/push/register` · hooks in shop_mgmt
  transition+assign + analysis worker · TAG_CATALOG "push" · `[push]`
  extra (httpx[http2], PyJWT, cryptography). 12 new tests; full
  regression 4622 passed with only the two DESIGNED SCHEMA_VERSION
  tripwires firing — both pins advanced 43→44 per their own contract
  comments; pins+199 rerun 30 passed (canonical interpreter).
- **Apple-side DONE:** APNs Auth Key at `~/Projects/apns/AuthKey_5F2J49F8UT.p8`
  (OUTSIDE both repos, never commit). **Key ID `5F2J49F8UT` · Team
  `B6QK49DPRZ` · topic `com.bandithero.motodiag`.** Downloads copy
  deleted. Push Notifications capability added in Xcode (entitlements
  committed).
- **Mobile spike (WIP commit `9ea2538`):** dep
  `@react-native-community/push-notification-ios` compiles under New
  Arch (pod links; first Run). Spike probe (App.tsx cold mount,
  DELETE-BEFORE-BUILD): permission surface PASS
  (`authorizationStatus:2`, lockScreen/sound/alert true) — but the
  `register` token event was SILENT. **Root cause found: AppDelegate
  had no remote-notification delegate methods** (the lib's documented
  native wiring). Swift bridge added (didRegister/didFail/didReceive →
  `RNCPushNotificationIOS`), committed, NOT yet rebuilt/verified.

**RESUME CHECKLIST (next session):**
1. Repos: both on `phase-199-push-notifications`; fetch + confirm tips
   (backend `98008f7`+ledger commit, mobile `9ea2538`).
2. **Xcode → Run** (Swift change needs rebuild) → console filter `199`
   → expect `register event: token(64 chars)`. If STILL silent: next
   suspect is the Swift `import RNCPushNotificationIOS` module
   resolution (bridging-header/modulemap territory) — check the build
   log for import errors first.
3. Token seen → spike gate CLOSED → build the real layer:
   `src/services/pushRegistration.ts` (permission → token →
   POST /v1/push/register on app start; deregister on sign-out),
   wire at cold mount beside offlineBoot + extend the cold-start guard,
   DELETE spike file + App.tsx block, tests (service vs fake module/api
   + guard), tsc + jest, build commit.
4. **Device smoke (locked phone):** serve with env
   `MOTODIAG_APNS_DRY_RUN=0 MOTODIAG_APNS_KEY_PATH=$HOME/Projects/apns/AuthKey_5F2J49F8UT.p8
   MOTODIAG_APNS_KEY_ID=5F2J49F8UT MOTODIAG_APNS_TEAM_ID=B6QK49DPRZ
   MOTODIAG_APNS_TOPIC=com.bandithero.motodiag` (sandbox default on) +
   `pip install -e ".[push]"` once for the live deps. App runs once to
   register the token, then lock the phone; trigger a WO transition
   (second user via curl per test_phase184 bootstrap idiom, or
   assign-to-self-then-transition-by-other) → **push lights the locked
   screen.** Also smoke analysis-complete if a video is handy.
5. Record smoke in this log + impl doc v1.1, docs → completed/, ROADMAP
   ✅, mobile project docs (implementation.md 0.2.0→0.2.1 + Phase
   History row, root phase_log entry), F-followups (deep-link-on-tap;
   customer-queue push channel), merge branches → main/master,
   regression on merged, push.
6. Watch-items: lint-staged/stash shuffle (198 note) — check
   `git stash list` after any failed commit; the video-task stash must
   stay at stash@{0}.

---

### 2026-09-02 16:35 — Spike gate CLOSED + mobile build committed

- **Resume verified:** both repos at their pushed tips (backend
  `4c4e56e`, mobile `9ea2538`); phone connected; Metro + serve restarted
  on this Mac (serve now on the 199 code with the live APNs env — the
  previous process predated `98008f7` and had no push routes).
- **Token silence had THREE stacked causes, not one:**
  1. Missing AppDelegate delegate methods (fixed in `9ea2538`).
  2. Swift `import RNCPushNotificationIOS` → *no such module*: the pod's
     podspec defines no module map (plain static lib), so the
     handoff's "next suspect" was right. Fix: `MotoDiag-Bridging-Header.h`
     with the ObjC `#import`, `SWIFT_OBJC_BRIDGING_HEADER` on both
     configs, Swift import line removed.
  3. **Debug config had no `CODE_SIGN_ENTITLEMENTS`** — only Release
     pointed at `MotoDiagRelease.entitlements`, so this morning's spike
     build was signed WITHOUT `aps-environment` (verified with
     `codesign -d --entitlements`). iOS would have called
     `didFailToRegister…` ("no valid aps-environment") — which was
     ALSO silent because of cause 1. Added the entitlements file to
     Debug; rebuilt binary shows `aps-environment=development`.
- **Dev-loop note (RN 0.85):** Metro no longer prints app `console.log`
  lines. Read them through Metro's CDP inspector endpoint instead
  (`~/Projects/p199_cdp_console.cjs`: `GET :8081/json` → websocket
  with `Origin: http://localhost:8081` → `Runtime.enable` replays
  Hermes' cached console). `xcodebuild … build` + `xcrun devicectl
  device install app` / `process launch` replaced the Xcode Run button.
- **Spike gate verdict (device, 16:21):** `requestPermissions` →
  `authorizationStatus:2`, lockScreen/alert/sound true; `register
  event: token(64 chars)`; **token surface PASS under New Arch.**
- **Mobile build (committed):** `src/services/pushRegistration.ts`
  (listeners → permission → token → AsyncStorage → POST; sign-in
  resync; sign-out deregister-before-clear; injectable deps; iOS-only
  no-op elsewhere), App.tsx cold-mount wiring + `stop()` on unmount,
  HomeScreen key-handler wiring, spike file + block DELETED,
  `__tests__/services/pushRegistration.test.ts` (11) + cold-start guard
  extended, jest global mock for the native lib, `api-schema` +
  `api-types` refreshed (`/v1/push/register` the only new path).
  **Suite 69 suites / 864 tests green (+11); tsc clean; eslint 0
  errors.**
- **Device registration PASS (16:33):** relaunch → `[199 push] token
  received (64 chars)` → `registered with backend` → serve log `POST
  /v1/push/register 200` → `device_tokens` row present.
- **Next:** locked-phone smoke (WO transition by a second user →
  APNs sandbox → lock screen), then close per CLAUDE.md.

---

### 2026-09-02 16:50 — DEVICE SMOKE: APNs-accepted — Phase 199 ✅ Complete

- **Setup:** serve on this Mac with the live env (`APNS_DRY_RUN=0`, key
  path/id/team/topic; sandbox default) after `pip install -e ".[push]"`;
  app registered → `device_tokens` user 1. App TERMINATED via
  `devicectl` so iOS renders banners. Second user `smoke_owner_199`
  (shop-tier sub + API key) bootstrapped via the repo helpers; shop
  "Phase 199 Smoke Shop" (`POST /v1/shop/profile` 201) with user 1 as
  `tech`; WO #1 "Push smoke: GSX-R1000 valve check" (draft).
- **Push #1 — assign** `POST /v1/shop/1/work-orders/1/assign
  {mechanic_user_id: 1}` as user 2 → 200, `assigned_mechanic_user_id=1`
  → `notify_wo_assigned` ("Work order #1 assigned to you").
- **Push #2 — transition** `{action: "open"}` as user 2 → 200,
  `status=open` → `notify_wo_transition` ("Work order #1 was opened").
  Serve log: **zero** `APNs send failed` warnings on either call
  (failures warn; successes are silent at INFO — noted in F52).
- **Push #3 — direct gateway evidence:** `get_sender()` →
  `ApnsSender` on `https://api.sandbox.push.apple.com`;
  `send(token, "MotoDiag smoke (Phase 199)", …)` →
  **`PushResult(ok=True, unregistered=False)`** — the .p8 JWT, key id,
  team id, topic and the phone's token are all accepted by Apple.
- **Visual confirmation:** left to the user — this session has no
  remote view of the physical iPhone (no `devicectl` screenshot; iPhone
  Mirroring parked). The three notifications persist in Notification
  Center. Analysis-complete not device-smoked (no video handy; events
  test covers it). Smoke rows (user 2, shop 1, WO 1) remain in the dev
  DB.

### 2026-09-02 17:00 — Documentation update + close

- `199_implementation.md` → v1.1 (as-built outputs, three-cause root
  cause, RN 0.85 dev-loop notes, checklist, deviations — foreground
  presentation scoped out to F52 —, results, key finding).
- Docs → `completed/`; mobile project docs (`implementation.md` 0.2.0 →
  0.2.1 + Phase History row, root `phase_log.md`, ROADMAP 199 ✅);
  F51 (deep-link on tap), F52 (foreground presentation + success log),
  F53 (customer-queue push channel), F54 (backend inventory drift for
  Track I substrate tables/packages) filed in mobile FOLLOWUPS.
- Branches fast-forwarded into `master` / `main`, regression on merged,
  pushed.
