# Phase 273: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

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
- added rowid 79: (80, '2026-10-06 21:36:01')
