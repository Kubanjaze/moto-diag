# Phase 209D — Whose spend is it — phase log

**Status:** Planned
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
