# Phase 209D — Whose spend is it — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-17

---

## 2026-09-17 14:25 EDT — Plan v1.0 written

Opened because the operator asked what the cap was actually for. The honest
answer was in the ledger: **32¢ across 4 calls**. At measured prices $25 is
about 500 sweeps or 190 video questions a month, so it is a brake on a
runaway rather than a budget, and four samples cannot set it. The decision:
build the instrument, leave the number for later. The block gets built and
defaults to off.

Step 0 also corrected the ticket twice. `cost_cap_monthly_usd_cents` is a
**server setting defaulting to 0**, not a per-shop column, and
`shop_cost_this_month` was written for a soft warning that does not block.
And the reason the cap would have been a no-op is unchanged and now
first-class: every `cost_events` row has `shop_id = NULL`.

Two of the four kinds already attribute (voice, through the shop-scoped
work-order route). The vision pipeline already takes `shop_id` and nobody
passes it. Text diagnosis is CLI-only — there is no diagnosis route in the
API at all — so its shop has to come from the CLI's own session.

## 2026-09-17 — Built

Migration 061 adds `diagnostic_sessions.shop_id`; sessions are stamped at
creation; the sweep, the ask route and the CLI diagnosis all record who pays;
`shop/cost_cap.py` refuses before the money when a number is configured, and
does nothing when it isn't.

Three things worth keeping:

- **The 209B gate earned its keep.** `shop_cost_this_month` was orphan #28,
  listed as *"Nothing reads it, which is half of why
  cost_cap_monthly_usd_cents is never enforced."* Wiring it made the entry
  stale and the gate failed in the direction that usually rots silently.
  The entry is gone.
- **Ten schema pins, spelled two ways.** The 244L pin's own note warns that
  `test_phase191b_serve_migrations.py` writes `get_current_version(db_path)
  == N`, which a `SCHEMA_VERSION` grep misses. A scan of every test file
  found ten pins across suites 184–244N.
- **A test double that had stopped testing the real call.** The media wiring
  guard's fake `analyze_video_frames` did not take `shop_id`, so passing it
  broke the double rather than the product. It now takes it and records it.

Two of my own first drafts were wrong and the tests said so: the ask route
needs a shop-tier subscription, and a fake call of 400/500 tokens costs less
than a cent, which `record_diagnosis_cost` skips by design — so the ledger
assertion failed against an empty table until the fake call was made to cost
something.

16 of 16 mutations caught. On a copy of production the migration applies
clean: schema 61, integrity ok, the 6 existing sessions stay unstamped
(no backfill, deliberately) and the 4 old cost rows stay unattributed.

## 2026-09-17 15:09 EDT — Complete

Regression **6,687 passed, 0 failed, 26:19**. Schema 60 → 61.
