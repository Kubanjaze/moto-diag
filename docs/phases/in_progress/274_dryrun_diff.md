# Phase 274: the dry-run diff for the live migration

- **Written:** `2026-09-29T21:01:36`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre274_20260929_210135.db`
- **Backup sha256:** `0aa3d589b52a96e26a283f3c2f80884e1bf6188776bb8993636425fa4d5f604b`
- **Scope sha256:** `173e1d2b3f8b0322bfe1855afaa829a0cd9eae347c3c4819e66aa6d912f50178`
- **Migrations applied on the copy:** `[76]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema added: index idx_customer_comms_customer

```sql
CREATE INDEX idx_customer_comms_customer
                ON customer_communications(customer_id, occurred_at)
```

## schema added: index idx_po_lines_item

```sql
CREATE INDEX idx_po_lines_item
                ON purchase_order_lines(item_id)
```

## schema added: index idx_purchase_orders_vendor

```sql
CREATE INDEX idx_purchase_orders_vendor
                ON purchase_orders(vendor_id, status)
```

## schema added: index idx_shop_expenses_month

```sql
CREATE INDEX idx_shop_expenses_month
                ON shop_expenses(shop_id, month)
```

## schema added: index idx_warranty_claims_warranty

```sql
CREATE INDEX idx_warranty_claims_warranty
                ON warranty_claims(warranty_id)
```

## schema added: index idx_work_order_quotes_wo

```sql
CREATE INDEX idx_work_order_quotes_wo
                ON work_order_quotes(work_order_id, quoted_at)
```

## schema added: table customer_communications

```sql
CREATE TABLE customer_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                shop_id INTEGER,
                work_order_id INTEGER,
                direction TEXT NOT NULL
                    CHECK (direction IN ('inbound', 'outbound')),
                channel TEXT NOT NULL
                    CHECK (channel IN ('phone', 'in_person', 'email',
                                       'sms', 'other')),
                summary TEXT NOT NULL CHECK (length(trim(summary)) > 0),
                logged_by_user_id INTEGER,
                occurred_at TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id)
                    REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE SET NULL,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE SET NULL,
                FOREIGN KEY (logged_by_user_id)
                    REFERENCES users(id) ON DELETE SET NULL
            )
```

## schema added: table mechanic_cost_rates

```sql
CREATE TABLE mechanic_cost_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                cost_cents_per_hour INTEGER NOT NULL
                    CHECK (cost_cents_per_hour >= 0),
                effective_from TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (shop_id, user_id, effective_from),
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id)
                    REFERENCES users(id) ON DELETE CASCADE
            )
```

## schema added: table purchase_order_lines

```sql
CREATE TABLE purchase_order_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_cost_cents INTEGER NOT NULL DEFAULT 0
                    CHECK (unit_cost_cents >= 0),
                UNIQUE (po_id, item_id),
                FOREIGN KEY (po_id)
                    REFERENCES purchase_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (item_id)
                    REFERENCES inventory_items(id) ON DELETE RESTRICT
            )
```

## schema added: table purchase_orders

```sql
CREATE TABLE purchase_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                po_number TEXT NOT NULL UNIQUE,
                vendor_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'sent', 'received',
                                      'cancelled')),
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                sent_at TEXT,
                received_at TEXT,
                cancelled_at TEXT,
                FOREIGN KEY (vendor_id)
                    REFERENCES vendors(id) ON DELETE RESTRICT
            )
```

## schema added: table shop_expenses

```sql
CREATE TABLE shop_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                month TEXT NOT NULL
                    CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),
                category TEXT NOT NULL CHECK (length(trim(category)) > 0),
                amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
                description TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE
            )
```

## schema added: table warranty_claims

```sql
CREATE TABLE warranty_claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                warranty_id INTEGER NOT NULL,
                work_order_id INTEGER,
                status TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'submitted', 'approved',
                                      'denied', 'paid')),
                claim_number TEXT,
                description TEXT NOT NULL
                    CHECK (length(trim(description)) > 0),
                amount_claimed_cents INTEGER
                    CHECK (amount_claimed_cents IS NULL
                           OR amount_claimed_cents >= 0),
                amount_approved_cents INTEGER
                    CHECK (amount_approved_cents IS NULL
                           OR amount_approved_cents >= 0),
                opened_at TEXT NOT NULL,
                submitted_at TEXT,
                decided_at TEXT,
                paid_at TEXT,
                notes TEXT,
                FOREIGN KEY (warranty_id)
                    REFERENCES warranties(id) ON DELETE CASCADE,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE SET NULL
            )
```

## schema added: table work_order_part_costs

```sql
CREATE TABLE work_order_part_costs (
                work_order_part_id INTEGER PRIMARY KEY,
                purchase_cost_cents_each INTEGER NOT NULL
                    CHECK (purchase_cost_cents_each >= 0),
                recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_order_part_id)
                    REFERENCES work_order_parts(id) ON DELETE CASCADE
            )
```

## schema added: table work_order_quotes

```sql
CREATE TABLE work_order_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                notification_id INTEGER,
                estimated_hours REAL NOT NULL CHECK (estimated_hours > 0),
                labor_rate_cents INTEGER NOT NULL
                    CHECK (labor_rate_cents >= 0),
                parts_cents INTEGER NOT NULL CHECK (parts_cents >= 0),
                total_cents INTEGER NOT NULL CHECK (total_cents >= 0),
                quoted_at TEXT NOT NULL,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (notification_id)
                    REFERENCES customer_notifications(id) ON DELETE SET NULL
            )
```

## schema changed: table inventory_items

```sql
CREATE TABLE inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                make TEXT,
                model_applicable TEXT NOT NULL DEFAULT '[]',
                quantity_on_hand INTEGER NOT NULL DEFAULT 0,
                reorder_point INTEGER NOT NULL DEFAULT 0,
                unit_cost REAL DEFAULT 0.0,
                unit_price REAL DEFAULT 0.0,
                vendor_id INTEGER,
                location TEXT,
                last_counted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP, reorder_quantity INTEGER NOT NULL DEFAULT 0
                CHECK (reorder_quantity >= 0),
                FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 75: (76, '2026-09-30 01:01:36')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "75": {
     "applied_at": "<clock>",
     "version": 76
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_customer_comms_customer",
   "index idx_po_lines_item",
   "index idx_purchase_orders_vendor",
   "index idx_shop_expenses_month",
   "index idx_warranty_claims_warranty",
   "index idx_work_order_quotes_wo",
   "table customer_communications",
   "table mechanic_cost_rates",
   "table purchase_order_lines",
   "table purchase_orders",
   "table shop_expenses",
   "table warranty_claims",
   "table work_order_part_costs",
   "table work_order_quotes"
  ],
  "changed": [
   "table inventory_items"
  ],
  "removed": [],
  "sql": {
   "index idx_customer_comms_customer": "CREATE INDEX idx_customer_comms_customer\n                ON customer_communications(customer_id, occurred_at)",
   "index idx_po_lines_item": "CREATE INDEX idx_po_lines_item\n                ON purchase_order_lines(item_id)",
   "index idx_purchase_orders_vendor": "CREATE INDEX idx_purchase_orders_vendor\n                ON purchase_orders(vendor_id, status)",
   "index idx_shop_expenses_month": "CREATE INDEX idx_shop_expenses_month\n                ON shop_expenses(shop_id, month)",
   "index idx_warranty_claims_warranty": "CREATE INDEX idx_warranty_claims_warranty\n                ON warranty_claims(warranty_id)",
   "index idx_work_order_quotes_wo": "CREATE INDEX idx_work_order_quotes_wo\n                ON work_order_quotes(work_order_id, quoted_at)",
   "table customer_communications": "CREATE TABLE customer_communications (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                customer_id INTEGER NOT NULL,\n                shop_id INTEGER,\n                work_order_id INTEGER,\n                direction TEXT NOT NULL\n                    CHECK (direction IN ('inbound', 'outbound')),\n                channel TEXT NOT NULL\n                    CHECK (channel IN ('phone', 'in_person', 'email',\n                                       'sms', 'other')),\n                summary TEXT NOT NULL CHECK (length(trim(summary)) > 0),\n                logged_by_user_id INTEGER,\n                occurred_at TEXT NOT NULL,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                FOREIGN KEY (customer_id)\n                    REFERENCES customers(id) ON DELETE CASCADE,\n                FOREIGN KEY (shop_id)\n                    REFERENCES shops(id) ON DELETE SET NULL,\n                FOREIGN KEY (work_order_id)\n                    REFERENCES work_orders(id) ON DELETE SET NULL,\n                FOREIGN KEY (logged_by_user_id)\n                    REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table inventory_items": "CREATE TABLE inventory_items (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                sku TEXT NOT NULL UNIQUE,\n                name TEXT NOT NULL,\n                description TEXT,\n                category TEXT,\n                make TEXT,\n                model_applicable TEXT NOT NULL DEFAULT '[]',\n                quantity_on_hand INTEGER NOT NULL DEFAULT 0,\n                reorder_point INTEGER NOT NULL DEFAULT 0,\n                unit_cost REAL DEFAULT 0.0,\n                unit_price REAL DEFAULT 0.0,\n                vendor_id INTEGER,\n                location TEXT,\n                last_counted_at TIMESTAMP,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                updated_at TIMESTAMP, reorder_quantity INTEGER NOT NULL DEFAULT 0\n                CHECK (reorder_quantity >= 0),\n                FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL\n            )",
   "table mechanic_cost_rates": "CREATE TABLE mechanic_cost_rates (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                shop_id INTEGER NOT NULL,\n                user_id INTEGER NOT NULL,\n                cost_cents_per_hour INTEGER NOT NULL\n                    CHECK (cost_cents_per_hour >= 0),\n                effective_from TEXT NOT NULL,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                UNIQUE (shop_id, user_id, effective_from),\n                FOREIGN KEY (shop_id)\n                    REFERENCES shops(id) ON DELETE CASCADE,\n                FOREIGN KEY (user_id)\n                    REFERENCES users(id) ON DELETE CASCADE\n            )",
   "table purchase_order_lines": "CREATE TABLE purchase_order_lines (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                po_id INTEGER NOT NULL,\n                item_id INTEGER NOT NULL,\n                quantity INTEGER NOT NULL CHECK (quantity > 0),\n                unit_cost_cents INTEGER NOT NULL DEFAULT 0\n                    CHECK (unit_cost_cents >= 0),\n                UNIQUE (po_id, item_id),\n                FOREIGN KEY (po_id)\n                    REFERENCES purchase_orders(id) ON DELETE CASCADE,\n                FOREIGN KEY (item_id)\n                    REFERENCES inventory_items(id) ON DELETE RESTRICT\n            )",
   "table purchase_orders": "CREATE TABLE purchase_orders (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                po_number TEXT NOT NULL UNIQUE,\n                vendor_id INTEGER NOT NULL,\n                status TEXT NOT NULL DEFAULT 'draft'\n                    CHECK (status IN ('draft', 'sent', 'received',\n                                      'cancelled')),\n                notes TEXT,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                sent_at TEXT,\n                received_at TEXT,\n                cancelled_at TEXT,\n                FOREIGN KEY (vendor_id)\n                    REFERENCES vendors(id) ON DELETE RESTRICT\n            )",
   "table shop_expenses": "CREATE TABLE shop_expenses (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                shop_id INTEGER NOT NULL,\n                month TEXT NOT NULL\n                    CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),\n                category TEXT NOT NULL CHECK (length(trim(category)) > 0),\n                amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),\n                description TEXT,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                FOREIGN KEY (shop_id)\n                    REFERENCES shops(id) ON DELETE CASCADE\n            )",
   "table warranty_claims": "CREATE TABLE warranty_claims (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                warranty_id INTEGER NOT NULL,\n                work_order_id INTEGER,\n                status TEXT NOT NULL DEFAULT 'draft'\n                    CHECK (status IN ('draft', 'submitted', 'approved',\n                                      'denied', 'paid')),\n                claim_number TEXT,\n                description TEXT NOT NULL\n                    CHECK (length(trim(description)) > 0),\n                amount_claimed_cents INTEGER\n                    CHECK (amount_claimed_cents IS NULL\n                           OR amount_claimed_cents >= 0),\n                amount_approved_cents INTEGER\n                    CHECK (amount_approved_cents IS NULL\n                           OR amount_approved_cents >= 0),\n                opened_at TEXT NOT NULL,\n                submitted_at TEXT,\n                decided_at TEXT,\n                paid_at TEXT,\n                notes TEXT,\n                FOREIGN KEY (warranty_id)\n                    REFERENCES warranties(id) ON DELETE CASCADE,\n                FOREIGN KEY (work_order_id)\n                    REFERENCES work_orders(id) ON DELETE SET NULL\n            )",
   "table work_order_part_costs": "CREATE TABLE work_order_part_costs (\n                work_order_part_id INTEGER PRIMARY KEY,\n                purchase_cost_cents_each INTEGER NOT NULL\n                    CHECK (purchase_cost_cents_each >= 0),\n                recorded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                FOREIGN KEY (work_order_part_id)\n                    REFERENCES work_order_parts(id) ON DELETE CASCADE\n            )",
   "table work_order_quotes": "CREATE TABLE work_order_quotes (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                work_order_id INTEGER NOT NULL,\n                notification_id INTEGER,\n                estimated_hours REAL NOT NULL CHECK (estimated_hours > 0),\n                labor_rate_cents INTEGER NOT NULL\n                    CHECK (labor_rate_cents >= 0),\n                parts_cents INTEGER NOT NULL CHECK (parts_cents >= 0),\n                total_cents INTEGER NOT NULL CHECK (total_cents >= 0),\n                quoted_at TEXT NOT NULL,\n                FOREIGN KEY (work_order_id)\n                    REFERENCES work_orders(id) ON DELETE CASCADE,\n                FOREIGN KEY (notification_id)\n                    REFERENCES customer_notifications(id) ON DELETE SET NULL\n            )"
  }
 }
}
```
