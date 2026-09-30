# Phase 275: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

## schema added: index idx_accounting_export_invoices_invoice

```sql
CREATE INDEX idx_accounting_export_invoices_invoice
                ON accounting_export_invoices(invoice_id)
```

## schema added: index idx_appointments_shop_start

```sql
CREATE INDEX idx_appointments_shop_start
                ON appointments(shop_id, scheduled_start)
```

## schema added: table accounting_accounts

```sql
CREATE TABLE accounting_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                target TEXT NOT NULL
                    CHECK (target IN ('quickbooks_online', 'xero')),
                kind TEXT NOT NULL
                    CHECK (kind IN ('labor', 'parts', 'diagnostic', 'misc',
                                    'tax', 'receivable')),
                account TEXT NOT NULL CHECK (length(trim(account)) > 0),
                tax_type TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (shop_id, target, kind),
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE
            )
```

## schema added: table accounting_export_invoices

```sql
CREATE TABLE accounting_export_invoices (
                export_id INTEGER NOT NULL,
                invoice_id INTEGER NOT NULL,
                PRIMARY KEY (export_id, invoice_id),
                FOREIGN KEY (export_id)
                    REFERENCES accounting_exports(id) ON DELETE CASCADE,
                FOREIGN KEY (invoice_id)
                    REFERENCES invoices(id) ON DELETE CASCADE
            )
```

## schema added: table accounting_exports

```sql
CREATE TABLE accounting_exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                target TEXT NOT NULL
                    CHECK (target IN ('quickbooks_online', 'xero')),
                period_from TEXT NOT NULL,
                period_to TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                invoice_count INTEGER NOT NULL CHECK (invoice_count > 0),
                exported_at TEXT NOT NULL,
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE
            )
```

## schema changed: table appointments

```sql
CREATE TABLE appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                vehicle_id INTEGER,
                user_id INTEGER,
                appointment_type TEXT NOT NULL DEFAULT 'service',
                status TEXT NOT NULL DEFAULT 'scheduled',
                scheduled_start TEXT NOT NULL,
                scheduled_end TEXT NOT NULL,
                actual_start TEXT,
                actual_end TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP, shop_id INTEGER
                REFERENCES shops(id) ON DELETE SET NULL, work_order_id INTEGER
                REFERENCES work_orders(id) ON DELETE SET NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 76: (77, '2026-09-30 05:35:17')
