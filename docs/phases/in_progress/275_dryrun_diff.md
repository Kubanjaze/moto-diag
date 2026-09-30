# Phase 275: the dry-run diff for the live migration

- **Written:** `2026-09-30T01:33:16`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre275_20260930_013316.db`
- **Backup sha256:** `6bf4ff642fd6baffba9d91d10718130e336a9d43bf53b713db3767c8f4899faa`
- **Scope sha256:** `447bfdcf08f2e56ee8c47c2ee4e2ac5c17dc1e957247998f69356b4cf2e8b22b`
- **Migrations applied on the copy:** `[77]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
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
- added rowid 76: (77, '2026-09-30 05:33:16')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "76": {
     "applied_at": "<clock>",
     "version": 77
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_accounting_export_invoices_invoice",
   "index idx_appointments_shop_start",
   "table accounting_accounts",
   "table accounting_export_invoices",
   "table accounting_exports"
  ],
  "changed": [
   "table appointments"
  ],
  "removed": [],
  "sql": {
   "index idx_accounting_export_invoices_invoice": "CREATE INDEX idx_accounting_export_invoices_invoice\n                ON accounting_export_invoices(invoice_id)",
   "index idx_appointments_shop_start": "CREATE INDEX idx_appointments_shop_start\n                ON appointments(shop_id, scheduled_start)",
   "table accounting_accounts": "CREATE TABLE accounting_accounts (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                shop_id INTEGER NOT NULL,\n                target TEXT NOT NULL\n                    CHECK (target IN ('quickbooks_online', 'xero')),\n                kind TEXT NOT NULL\n                    CHECK (kind IN ('labor', 'parts', 'diagnostic', 'misc',\n                                    'tax', 'receivable')),\n                account TEXT NOT NULL CHECK (length(trim(account)) > 0),\n                tax_type TEXT,\n                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                UNIQUE (shop_id, target, kind),\n                FOREIGN KEY (shop_id)\n                    REFERENCES shops(id) ON DELETE CASCADE\n            )",
   "table accounting_export_invoices": "CREATE TABLE accounting_export_invoices (\n                export_id INTEGER NOT NULL,\n                invoice_id INTEGER NOT NULL,\n                PRIMARY KEY (export_id, invoice_id),\n                FOREIGN KEY (export_id)\n                    REFERENCES accounting_exports(id) ON DELETE CASCADE,\n                FOREIGN KEY (invoice_id)\n                    REFERENCES invoices(id) ON DELETE CASCADE\n            )",
   "table accounting_exports": "CREATE TABLE accounting_exports (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                shop_id INTEGER NOT NULL,\n                target TEXT NOT NULL\n                    CHECK (target IN ('quickbooks_online', 'xero')),\n                period_from TEXT NOT NULL,\n                period_to TEXT NOT NULL,\n                file_name TEXT NOT NULL,\n                file_sha256 TEXT NOT NULL,\n                invoice_count INTEGER NOT NULL CHECK (invoice_count > 0),\n                exported_at TEXT NOT NULL,\n                FOREIGN KEY (shop_id)\n                    REFERENCES shops(id) ON DELETE CASCADE\n            )",
   "table appointments": "CREATE TABLE appointments (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                customer_id INTEGER NOT NULL,\n                vehicle_id INTEGER,\n                user_id INTEGER,\n                appointment_type TEXT NOT NULL DEFAULT 'service',\n                status TEXT NOT NULL DEFAULT 'scheduled',\n                scheduled_start TEXT NOT NULL,\n                scheduled_end TEXT NOT NULL,\n                actual_start TEXT,\n                actual_end TEXT,\n                notes TEXT,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                updated_at TIMESTAMP, shop_id INTEGER\n                REFERENCES shops(id) ON DELETE SET NULL, work_order_id INTEGER\n                REFERENCES work_orders(id) ON DELETE SET NULL,\n                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,\n                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL,\n                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL\n            )"
  }
 }
}
```
