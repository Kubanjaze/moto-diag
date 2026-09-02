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
