# Track O triage: business infrastructure (rows 273–292)

2026-09-28. This is a read-only analysis for the operator's decision; no code or ROADMAP row changes. It was measured on `master` at `f27be0b`.

**Method:**
- the row text comes from `docs/ROADMAP.md`;
- code overlap comes from a keyword search of the 263 Python files under `src/motodiag`, and from the closed ROADMAP rows that built each package;
- outside dependencies come from the row text and from what the code calls today.

A keyword hit is not proof of a feature. Each batch's Step 0 re-verifies against the code, and proves each outside service with one real request.

---

## The recommendation

1. **Track O mostly extends code that already exists.** The substrates are already in place:
   - 113: customers, bikes and ownership history;
   - 118: the billing, accounting, inventory and scheduling packages;
   - 155: NHTSA recalls;
   - 160, 168 and 169: the shop, bay scheduling and invoicing;
   - 176: a billing provider switch with a Stripe implementation;
   - 182: reporting.
2. **The limits are outside the code:**
   - accounts and keys only the operator can create (Stripe, Google, Intuit, Xero);
   - public endpoints that the tailnet-only rule forbids (Stripe webhooks, customer self-booking);
   - dealer or partner agreements that may not be obtainable (the five parts suppliers, OEM warranty portals).
3. **Proposed: four batches and the gate,** ordered so that nothing waits on the operator until batch 4. The supplier and OEM-portal parts are paused with their reason, unless the operator wants file-based versions.

## Row by row

| row | title | already built | outside dependency | proposed |
|---|---|---|---|---|
| 273 | Payment processing (Stripe) | 176: `billing/providers.py`, a `FakeBillingProvider` and a `StripeBillingProvider`, switched by `MOTODIAG_BILLING_PROVIDER`; checkout sessions, subscriptions, `billing/webhook_handlers.py`. 118 and 169: invoices. | The operator's Stripe account in test mode, for Connect and Terminal (Stripe's simulated reader). Webhooks need an endpoint Stripe can reach, which conflicts with tailnet-only. | Batch 4 |
| 274 | Customer CRM | 113: `crm/` customers, `customer_bikes`, ownership history, `transfer_ownership()`. Notes exist on customers and on bikes. Shop notifications (`customer_notifications`). | none | Batch 1: the communication log is what is missing. Step 0 checks whether `customer_notifications` already serves as one |
| 275 | Appointment booking | 118: `scheduling/` appointments, schema and CRUD. 168: bay scheduling. | "Online booking" by customers needs an endpoint customers can reach, which conflicts with tailnet-only. | Batch 2: booking by shop staff. Customer self-booking paused |
| 276 | Calendar sync (iCal / Google) | none; the scheduling docstring defers it | iCal: none. Google two-way sync: the operator's Google OAuth client. | Batch 2: iCal. Google sync paused, or batch 4 |
| 277 | Accounting export (QuickBooks) | 118 and 169: invoices and line items; the accounting docstring defers export | A file export needs nothing. API sync needs an Intuit developer account. | Batch 2: file export |
| 278 | Accounting export (Xero) | as 277 | A file export needs nothing. API sync needs a Xero developer account. | Batch 2: file export |
| 279 | Parts inventory with reorder points | 118: `inventory/item_repo.py`, low-stock alerts | none for reorder points and local purchase orders. Sending a PO to a supplier is a supplier integration. | Batch 1 |
| 280 | OEM warranty claims | 118: `inventory/warranty_repo.py`, warranty coverage per vehicle (powertrain, comprehensive, extended, aftermarket) with its provider. That is the basis for the row's validity lookup. | "OEM-specific submission flows" are OEM dealer portals, which need dealer access | Batch 1: the validity lookup, local claim records and a printable claim packet. OEM submission paused |
| 281 | NHTSA recall processing | 155: `advanced/recall_repo.py` (603 lines): VIN validation, range check, WMI decode, `recall_resolutions`. Its data is local, and nothing in `src` calls NHTSA. | NHTSA's public recall data (no key) for refresh. "OEM reimbursement" is for dealers only. | Batch 3: live refresh. Reimbursement paused |
| 282–286 | Supplier integrations (Parts Unlimited, NAPA, Drag Specialties, Dennis Kirk, tire distributors) | `shop/parts_sourcing.py`: an AI supplier taxonomy that names Parts Unlimited and Drag Specialties as "T2 OEM wholesale online". It has no API. | Dealer or B2B accounts with each supplier; no public API is known. NAPA TRACS is NAPA's own shop system. | Paused, unless you want file-based price-list imports |
| 287 | VIN decoder (vPIC) | 155: WMI decode, which gives the manufacturer only | NHTSA vPIC, public, no key | Batch 3 |
| 288 | Tax rate lookup | `shop/invoicing.py` takes a manual `tax_rate` from 0 to 1 | Rate data: a state's published tables (California's CDTFA first, like 267), or a commercial API that needs an account | Batch 3, California first |
| 289 | Multi-currency | invoices and payments already carry `currency` (default `'USD'`) | Exchange rates: the ECB's daily reference rates (public, no key), or entered by hand | Batch 3 |
| 290 | Financial reporting | `shop/analytics.py`; 182: the `reporting/` package | none | Batch 1 |
| 291 | Estimate vs actual variance | `shop/work_order_repo.py` (estimated and actual hours), `shop/labor_estimator.py`, analytics | none | Batch 1 |
| 292 | Gate 16: integration test | — | Whatever the batches ship. Payment goes through the fake provider, so tests need no Stripe keys. | Last: tests only. K8 rewrites its verbs for anything paused |

**A stale reference found on the way.** Two package docstrings name old Track O numbers:
- `scheduling/__init__.py` says "Track O phases 288-289" for calendar sync and booking, which are now 275 and 276;
- `accounting/__init__.py` says "Track O phases 278-281" for QuickBooks and Xero, which are now 277 and 278.

The phase that next touches each package should correct its docstring.

## Proposed batches

1. **Local shop data, with no outside dependency:** 274 CRM, 279 reorder points and local POs, 280 local warranty claims, 290 financial reporting, 291 variance.
2. **Booking, calendar and accounting files:** 275 staff booking, 276 iCal, 277 QuickBooks export file, 278 Xero export file.
3. **Public data services:** 287 vPIC, 281 NHTSA recall refresh, 288 California tax rates, 289 exchange rates. These make outbound calls with no accounts. Tests use recorded fixtures; no test calls the network.
4. **Payments:** 273 Stripe Connect, Terminal (simulated reader) and invoice payment, built on 176's provider switch. Most of it is built and tested against the fake provider; the live test-mode check needs the operator's keys.

Then **Gate 16 (292)**.

**Paused, each with its reason on the row (⏸️):**
- 282–286, the supplier integrations;
- OEM submission (280) and OEM reimbursement (281);
- Google Calendar two-way sync (276);
- customer self-booking (275).

## Decisions for the operator

1. **The batches and their order.** Recommended: 1 → 2 → 3 → 4 → gate. Batches 1–3 need nothing from you.
2. **The supplier rows (282–286) and the OEM parts of 280 and 281:** pause them with the reason, reduce them to file-based imports, or drop them from the ledger.
3. **Public exposure.** Either keep tailnet-only, or plan an exposed endpoint (your call; never without asking). Keeping tailnet-only means:
   - Stripe webhooks through `stripe listen` in development;
   - no customer self-booking;
   - Google sync by polling, if it is ever built.
4. **Tax data:** California first, from the regulator's published rates (provenance `regulation`), or a commercial API on your account.
5. **F174** (`garage add` and the API store `ice` by default; diagnose, the predictor and the safety scoping read it): a small phase before batch 1, or after Track O.

## What you would need to supply

- **Batches 1–3:** nothing; no accounts and no keys.
- **Batch 4:** a Stripe account in test mode. You enter the keys yourself, because builders never type credentials. Also the Connect settings, and decision 3.
- **Google Calendar sync, if wanted:** a Google Cloud OAuth client.
- **QuickBooks or Xero API sync, if wanted:** developer accounts.
- **Supplier integrations:** dealer agreements.
