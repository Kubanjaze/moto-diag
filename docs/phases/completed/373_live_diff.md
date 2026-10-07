# Phase 373: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

## schema added: index idx_tax_warranty_rules_jurisdiction

```sql
CREATE INDEX idx_tax_warranty_rules_jurisdiction
                ON tax_warranty_rules(jurisdiction_id, payer, effective_from)
```

## schema added: index idx_warranty_claim_lines_claim

```sql
CREATE INDEX idx_warranty_claim_lines_claim
                ON warranty_claim_lines(claim_id)
```

## schema added: table accounting_export_claims

```sql
CREATE TABLE accounting_export_claims (
                export_id INTEGER NOT NULL,
                claim_id INTEGER NOT NULL,
                PRIMARY KEY (export_id, claim_id),
                FOREIGN KEY (export_id)
                    REFERENCES accounting_exports(id) ON DELETE CASCADE,
                FOREIGN KEY (claim_id)
                    REFERENCES warranty_claims(id) ON DELETE CASCADE
            )
```

## schema added: table tax_warranty_rules

```sql
CREATE TABLE tax_warranty_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jurisdiction_id INTEGER NOT NULL,
                shop_id INTEGER,
                payer TEXT NOT NULL
                    CHECK (payer IN ('maker_with_bike', 'other', 'shop_contract')),
                taxed_on_claim INTEGER NOT NULL CHECK (taxed_on_claim IN (0, 1)),
                basis TEXT NOT NULL CHECK (basis IN ('stated', 'reading')),
                effective_from TEXT NOT NULL,
                valid_until TEXT NOT NULL CHECK (valid_until >= effective_from),
                source_title TEXT NOT NULL CHECK (length(trim(source_title)) > 0),
                source_url TEXT,
                source_clause TEXT,
                checked_on TEXT NOT NULL,
                provenance TEXT NOT NULL CHECK (provenance IN ('regulation', 'shop')),
                entered_by_user_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK ((provenance = 'regulation') = (shop_id IS NULL)),
                FOREIGN KEY (jurisdiction_id)
                    REFERENCES tax_jurisdictions(id) ON DELETE CASCADE,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
```

## schema added: table warranty_claim_lines

```sql
CREATE TABLE warranty_claim_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                line_type TEXT NOT NULL CHECK (line_type IN ('labor', 'parts')),
                work_order_part_id INTEGER,
                quantity REAL NOT NULL CHECK (quantity > 0),
                amount_cents INTEGER CHECK (amount_cents IS NULL OR amount_cents >= 0),
                description TEXT,
                CHECK ((line_type = 'labor') = (work_order_part_id IS NULL)),
                FOREIGN KEY (claim_id)
                    REFERENCES warranty_claims(id) ON DELETE CASCADE,
                FOREIGN KEY (work_order_part_id)
                    REFERENCES work_order_parts(id) ON DELETE RESTRICT
            )
```

## schema changed: table invoices

```sql
CREATE TABLE invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                repair_plan_id INTEGER,
                invoice_number TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'draft',
                subtotal REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                total REAL NOT NULL DEFAULT 0.0,
                currency TEXT NOT NULL DEFAULT 'USD',
                issued_at TIMESTAMP,
                due_at TIMESTAMP,
                paid_at TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP, work_order_id INTEGER, tax_rate REAL, tax_rate_id INTEGER, tax_source TEXT, tax_recheck_by TEXT, taxed_line_types TEXT, fx_from_currency TEXT, fx_rate TEXT, fx_rate_id INTEGER, fx_rate_date TEXT, fx_source TEXT, shortfall_claim_id INTEGER,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (repair_plan_id) REFERENCES repair_plans(id) ON DELETE SET NULL
            )
```

## schema changed: table warranties

```sql
CREATE TABLE warranties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                coverage_type TEXT NOT NULL,
                provider TEXT,
                start_date TEXT,
                end_date TEXT,
                mileage_limit INTEGER,
                terms TEXT,
                claim_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, repair_payer TEXT
                CHECK (repair_payer IS NULL
                       OR repair_payer IN ('maker_with_bike', 'other', 'shop_contract')),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            )
```

## schema changed: table warranty_claims

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
                notes TEXT, coverage_recorded_at TEXT, invoice_id INTEGER, covered_cents INTEGER
                CHECK (covered_cents IS NULL OR covered_cents >= 0), tax_cents INTEGER
                CHECK (tax_cents IS NULL OR tax_cents >= 0), tax_source TEXT, settlement TEXT
                CHECK (settlement IS NULL
                       OR settlement IN ('bill_customer', 'absorb')), settled_at TEXT, shortfall_cents INTEGER
                CHECK (shortfall_cents IS NULL OR shortfall_cents >= 0), shortfall_invoice_id INTEGER,
                FOREIGN KEY (warranty_id)
                    REFERENCES warranties(id) ON DELETE CASCADE,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE SET NULL
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 80: (81, '2026-10-07 01:55:29')
## tax_warranty_rules: +3 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)
- added rowid 2: (2, 1, None)
- added rowid 3: (3, 1, None)
