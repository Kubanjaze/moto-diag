# Phase 375: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

## schema added: index idx_tax_deductible_rules_jurisdiction

```sql
CREATE INDEX idx_tax_deductible_rules_jurisdiction
                ON tax_deductible_rules(jurisdiction_id, payer, effective_from)
```

## schema added: table tax_deductible_rules

```sql
CREATE TABLE tax_deductible_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jurisdiction_id INTEGER NOT NULL,
                shop_id INTEGER,
                payer TEXT NOT NULL
                    CHECK (payer IN ('maker_with_bike', 'other', 'shop_contract')),
                deductible_tax TEXT NOT NULL CHECK (deductible_tax IN ('taxable_share')),
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
                       OR repair_payer IN ('maker_with_bike', 'other', 'shop_contract')), deductible_cents INTEGER
                CHECK (deductible_cents IS NULL OR deductible_cents >= 0),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            )
```

## schema changed: table warranty_claim_lines

```sql
CREATE TABLE warranty_claim_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                line_type TEXT NOT NULL CHECK (line_type IN ('labor', 'parts')),
                work_order_part_id INTEGER,
                quantity REAL NOT NULL CHECK (quantity > 0),
                amount_cents INTEGER CHECK (amount_cents IS NULL OR amount_cents >= 0),
                description TEXT, deductible_cents INTEGER
                CHECK (deductible_cents IS NULL OR deductible_cents >= 0),
                CHECK ((line_type = 'labor') = (work_order_part_id IS NULL)),
                FOREIGN KEY (claim_id)
                    REFERENCES warranty_claims(id) ON DELETE CASCADE,
                FOREIGN KEY (work_order_part_id)
                    REFERENCES work_order_parts(id) ON DELETE RESTRICT
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
                CHECK (shortfall_cents IS NULL OR shortfall_cents >= 0), shortfall_invoice_id INTEGER, deductible_cents INTEGER
                CHECK (deductible_cents IS NULL OR deductible_cents >= 0), deductible_tax_cents INTEGER
                CHECK (deductible_tax_cents IS NULL OR deductible_tax_cents >= 0), deductible_tax_source TEXT,
                FOREIGN KEY (warranty_id)
                    REFERENCES warranties(id) ON DELETE CASCADE,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE SET NULL
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 83: (84, '2026-10-08 02:05:38')
## tax_deductible_rules: +3 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)
- added rowid 2: (2, 1, None)
- added rowid 3: (3, 1, None)
