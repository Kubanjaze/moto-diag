# Phase 273: the dry-run diff for the live migration

- **Written:** `2026-10-06T17:34:55`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre273_20261006_173455.db`
- **Backup sha256:** `57a951fd4da6357bf312d6722099a74c009a122c3ce0434b76a6f8dea54c991b`
- **Scope sha256:** `528a8ec8d2f0668c639207dca67fce86494bef3519cf1379b9ed415fb34ebcb0`
- **Migrations applied on the copy:** `[80]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema added: index idx_invoice_payments_invoice

```sql
CREATE INDEX idx_invoice_payments_invoice
                ON invoice_payments(invoice_id)
```

## schema added: table invoice_payments

```sql
CREATE TABLE invoice_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                shop_id INTEGER NOT NULL,
                stripe_account_id TEXT NOT NULL,
                channel TEXT NOT NULL CHECK (channel IN ('checkout', 'terminal')),
                checkout_session_id TEXT UNIQUE,
                payment_intent_id TEXT UNIQUE,
                terminal_reader_id TEXT,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                currency TEXT NOT NULL CHECK (length(currency) = 3),
                status TEXT NOT NULL DEFAULT 'started'
                    CHECK (status IN ('started', 'failed', 'succeeded')),
                outcome TEXT CHECK (outcome IS NULL
                    OR outcome IN ('paid_invoice', 'paid_twice', 'rejected')),
                outcome_reason TEXT,
                failure_message TEXT,
                refunded_cents INTEGER NOT NULL DEFAULT 0 CHECK (refunded_cents >= 0),
                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),
                started_by_user_id INTEGER,
                started_at TEXT NOT NULL,
                settled_at TEXT,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE RESTRICT,
                FOREIGN KEY (started_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
```

## schema added: table shop_payment_accounts

```sql
CREATE TABLE shop_payment_accounts (
                shop_id INTEGER PRIMARY KEY,
                stripe_account_id TEXT NOT NULL UNIQUE,
                dashboard TEXT NOT NULL,
                fees_collector TEXT NOT NULL,
                losses_collector TEXT NOT NULL,
                country TEXT NOT NULL CHECK (length(country) = 2),
                currency TEXT NOT NULL CHECK (length(currency) = 3),
                card_payments_status TEXT,
                requirements_due INTEGER,
                status_checked_at TEXT,
                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),
                created_by_user_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE RESTRICT,
                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
```

## schema added: table subscription_payments

```sql
CREATE TABLE subscription_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subscription_id INTEGER,
                stripe_invoice_id TEXT NOT NULL UNIQUE,
                stripe_subscription_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('paid', 'failed')),
                amount_due_cents INTEGER NOT NULL CHECK (amount_due_cents >= 0),
                amount_paid_cents INTEGER NOT NULL CHECK (amount_paid_cents >= 0),
                currency TEXT NOT NULL CHECK (length(currency) = 3),
                period_start TEXT,
                period_end TEXT,
                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),
                recorded_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY (subscription_id)
                    REFERENCES subscriptions(id) ON DELETE SET NULL
            )
```

## schema added: table terminal_locations

```sql
CREATE TABLE terminal_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                stripe_account_id TEXT NOT NULL,
                stripe_location_id TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                address_json TEXT NOT NULL,
                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE RESTRICT
            )
```

## schema added: table terminal_readers

```sql
CREATE TABLE terminal_readers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                location_id INTEGER NOT NULL,
                stripe_reader_id TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                device_type TEXT,
                simulated INTEGER NOT NULL CHECK (simulated IN (0, 1)),
                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE RESTRICT,
                FOREIGN KEY (location_id)
                    REFERENCES terminal_locations(id) ON DELETE RESTRICT
            )
```

## schema changed: table stripe_webhook_events

```sql
CREATE TABLE stripe_webhook_events (
                event_id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                error TEXT
            , account TEXT, livemode INTEGER)
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 79: (80, '2026-10-06 21:34:55')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "79": {
     "applied_at": "<clock>",
     "version": 80
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_invoice_payments_invoice",
   "table invoice_payments",
   "table shop_payment_accounts",
   "table subscription_payments",
   "table terminal_locations",
   "table terminal_readers"
  ],
  "changed": [
   "table stripe_webhook_events"
  ],
  "removed": [],
  "sql": {
   "index idx_invoice_payments_invoice": "CREATE INDEX idx_invoice_payments_invoice\n                ON invoice_payments(invoice_id)",
   "table invoice_payments": "CREATE TABLE invoice_payments (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                invoice_id INTEGER NOT NULL,\n                shop_id INTEGER NOT NULL,\n                stripe_account_id TEXT NOT NULL,\n                channel TEXT NOT NULL CHECK (channel IN ('checkout', 'terminal')),\n                checkout_session_id TEXT UNIQUE,\n                payment_intent_id TEXT UNIQUE,\n                terminal_reader_id TEXT,\n                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),\n                currency TEXT NOT NULL CHECK (length(currency) = 3),\n                status TEXT NOT NULL DEFAULT 'started'\n                    CHECK (status IN ('started', 'failed', 'succeeded')),\n                outcome TEXT CHECK (outcome IS NULL\n                    OR outcome IN ('paid_invoice', 'paid_twice', 'rejected')),\n                outcome_reason TEXT,\n                failure_message TEXT,\n                refunded_cents INTEGER NOT NULL DEFAULT 0 CHECK (refunded_cents >= 0),\n                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),\n                started_by_user_id INTEGER,\n                started_at TEXT NOT NULL,\n                settled_at TEXT,\n                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE RESTRICT,\n                FOREIGN KEY (started_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table shop_payment_accounts": "CREATE TABLE shop_payment_accounts (\n                shop_id INTEGER PRIMARY KEY,\n                stripe_account_id TEXT NOT NULL UNIQUE,\n                dashboard TEXT NOT NULL,\n                fees_collector TEXT NOT NULL,\n                losses_collector TEXT NOT NULL,\n                country TEXT NOT NULL CHECK (length(country) = 2),\n                currency TEXT NOT NULL CHECK (length(currency) = 3),\n                card_payments_status TEXT,\n                requirements_due INTEGER,\n                status_checked_at TEXT,\n                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),\n                created_by_user_id INTEGER,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE RESTRICT,\n                FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table stripe_webhook_events": "CREATE TABLE stripe_webhook_events (\n                event_id TEXT PRIMARY KEY,\n                type TEXT NOT NULL,\n                payload_json TEXT NOT NULL,\n                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                processed_at TIMESTAMP,\n                error TEXT\n            , account TEXT, livemode INTEGER)",
   "table subscription_payments": "CREATE TABLE subscription_payments (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                user_id INTEGER NOT NULL,\n                subscription_id INTEGER,\n                stripe_invoice_id TEXT NOT NULL UNIQUE,\n                stripe_subscription_id TEXT NOT NULL,\n                status TEXT NOT NULL CHECK (status IN ('paid', 'failed')),\n                amount_due_cents INTEGER NOT NULL CHECK (amount_due_cents >= 0),\n                amount_paid_cents INTEGER NOT NULL CHECK (amount_paid_cents >= 0),\n                currency TEXT NOT NULL CHECK (length(currency) = 3),\n                period_start TEXT,\n                period_end TEXT,\n                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),\n                recorded_at TEXT NOT NULL,\n                updated_at TEXT NOT NULL,\n                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,\n                FOREIGN KEY (subscription_id)\n                    REFERENCES subscriptions(id) ON DELETE SET NULL\n            )",
   "table terminal_locations": "CREATE TABLE terminal_locations (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                shop_id INTEGER NOT NULL,\n                stripe_account_id TEXT NOT NULL,\n                stripe_location_id TEXT NOT NULL UNIQUE,\n                display_name TEXT NOT NULL,\n                address_json TEXT NOT NULL,\n                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE RESTRICT\n            )",
   "table terminal_readers": "CREATE TABLE terminal_readers (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                shop_id INTEGER NOT NULL,\n                location_id INTEGER NOT NULL,\n                stripe_reader_id TEXT NOT NULL UNIQUE,\n                label TEXT NOT NULL,\n                device_type TEXT,\n                simulated INTEGER NOT NULL CHECK (simulated IN (0, 1)),\n                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1)),\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE RESTRICT,\n                FOREIGN KEY (location_id)\n                    REFERENCES terminal_locations(id) ON DELETE RESTRICT\n            )"
  }
 }
}
```
