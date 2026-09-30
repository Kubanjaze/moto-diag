# Phase 274: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

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
- added rowid 75: (76, '2026-09-30 01:03:05')
