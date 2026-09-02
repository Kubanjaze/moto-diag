# F52 · F54 · F55 — Pre-Gate-10 Cleanup

**Version:** 1.1 | **Tier:** Micro (three F-tickets, one pass) | **Date:** 2026-09-02

## Goal

Close the debt Track I accumulated while running five phases in one day,
before Gate 10 (Phase 204) tries to exercise all of it end to end. Three
filed tickets plus one stale phase status, chosen because each was a
thing the record claimed but the system did not do.

CLI: none. Run: `pytest tests/test_f52_f55_cleanup.py`.

## Scope (and what was deliberately left)

Done here:

- **F52 — foreground push presentation.** A push arriving while the app
  was open rendered nothing at all. Both halves fixed: the native
  delegate, and a backend log line so a successful send leaves a trace.
- **F54 — backend inventory drift.** `implementation.md` still described
  the `api` package as "empty, awaiting Phase 175" and had no rows at
  all for `reporting`, `push`, or five Track-I-era tables.
- **F55 — sessions could not name their customer.** Migration 046 plus a
  resolver, so the Phase 200 customer page can say who it is for.
- **Phase 196 status.** Ten days at 🔄 with finished code; closed with
  the hardware-dependent half re-scoped to F56.

Deliberately NOT done, with reasons:

- **F51 (deep-link on tap)** — needs a navigation-ref singleton and
  route wiring in `RootNavigator`, which is phase-shaped work, not
  cleanup. The native half it depends on now exists (the
  `didReceive` forward landed with F52), so it is cheaper than it was.
- **F53 (customer-queue push channel)** — cannot be built. It needs a
  customer-side client that does not exist; Phase 200's share view is a
  browser page with no device token. Blocked on product, not effort.

## Logic

- **F52 native:** `AppDelegate` adopts `UNUserNotificationCenterDelegate`
  and sets itself as the delegate at launch. `willPresent` returns
  `[.banner, .list, .sound, .badge]` **and** forwards the payload to
  `RNCPushNotificationIOS.didReceiveRemoteNotification`; `didReceive`
  (a tap) forwards to the library and completes.
- **F52 JS:** `startPushRegistration` attaches a `notification` listener
  that logs and always calls `finish()`, and `stop()` detaches it.
- **F52 backend:** `push/events._send_to_user` logs one INFO line per
  successful send.
- **F55:** migration 046 adds nullable `diagnostic_sessions.customer_id`
  and backfills from `vehicles.customer_id`, skipping the id-1
  "Unassigned" sentinel. `resolve_session_customer_name` reads the
  session column first, then falls back through the vehicle — the
  fallback carries live traffic, because nothing writes the new column
  yet. The builder emits `prepared_for`; `HtmlReportRenderer` renders it.
- **F54:** inventory rows rewritten from the code, and
  `ROADMAP_AUTHORITY.md` gains a rule saying inventories are not status.

## Key Concepts

- **The willPresent routing detail is the whole of F52.** Once an app
  sets a `UNUserNotificationCenterDelegate`, iOS delivers a foreground
  alert with no `content-available` through `willPresent` and NOT
  through `application(_:didReceiveRemoteNotification:fetchCompletionHandler:)`
  — which is the only place the community library emits its JS
  `notification` event from. Adopting the delegate to get a banner
  therefore silently removes the JS event unless you forward. The first
  build here did exactly that and was caught on device.
- **A sentinel is not a value.** The Phase 006 retrofit gave
  `vehicles.customer_id` a `DEFAULT 1` pointing at "Unassigned". Any
  backfill reading that column must skip it or it manufactures false
  customer relationships at scale.
- **Inventories are not status.** `ROADMAP_AUTHORITY` correctly told
  Track I close-outs to skip the backend's status surfaces; five
  close-outs then skipped its architecture surfaces by the same
  reasoning. The rule now distinguishes them explicitly.

## Verification Checklist

- [x] Migration 046 applies; column + index present; SCHEMA_VERSION 46;
      both designed pins advanced 45→46
- [x] Backfill takes the vehicle's customer AND skips the id-1 sentinel
      — tested by rolling back to 45 and re-applying over seeded rows
- [x] Resolver: session column wins, vehicle fallback works, sentinel
      and missing both yield None, no-vehicle yields None
- [x] `prepared_for` reaches the customer page, and an injected
      `<script>` customer name renders escaped
- [x] A successful push logs at INFO (asserted, not assumed)
- [x] **Foreground banner verified on device**: push sent to the
      foregrounded app → `[199 push] foreground notification` in the app
      console. Because that log is emitted from the `willPresent`
      forward, its presence also proves the presentation options were
      returned, i.e. the banner was shown.
- [x] Backend regression green on the canonical interpreter
- [x] Mobile suite green; tsc clean; eslint 0 errors
- [x] `docs/phases/in_progress/` is empty — no phase left mid-flight

## Risks

- **Double-emit of the JS notification event** if a future payload adds
  `content-available`, since the fetch-handler path would then fire too.
  Harmless today (the listener only logs and finishes) but worth knowing
  before anyone makes that listener do real work.
- **`prepared_for` is HTML-only.** PDF and text renderers ignore it, so
  the same report names the customer on the web and not in the PDF. A
  deliberate call: adding the line to the PDF moves bytes that Phase
  192B's deterministic-render tests pin, and that belongs in a commit
  that updates those goldens.
- **Nothing writes `diagnostic_sessions.customer_id` yet.** New sessions
  resolve their customer through the vehicle. Fine, and the column is
  there for whichever phase adds customer selection to session creation.
- **F56 depends on a purchase**, so it can sit open indefinitely without
  anyone being wrong.

## Results

| Metric | Value |
|--------|-------|
| Tickets closed | F52, F54, F55 (+ Phase 196 status) |
| Tickets left open, with reasons | F51 (phase-shaped), F53 (blocked on a customer client), F56 (new, needs hardware) |
| New backend tests | 12 (`test_f52_f55_cleanup.py`) |
| Backend full regression | 4662 passed, 0 failed, 5 skipped (8:07) |
| Mobile tests | +2 → 70 suites / 876 (both into the existing push-registration suite) |
| Schema | 45 → 46 (migration 046) |
| Device verification | foreground banner + JS event confirmed |
| Phases left in `in_progress/` | 0 |

**Key finding:** the fix for F52 introduced the bug F52 was about. Adopting
the notification-center delegate is what makes a foreground banner
possible, and it is also what stops the library's JS event from firing —
so the "obvious" implementation produces a visible banner and a silent
app, which is a worse and more confusing state than before. It only
surfaced because the change was tested on the device rather than trusted
from the diff. That is the same lesson Phase 199 wrote down about
verifying the artifact instead of the settings, arriving a second time by
a different route.
