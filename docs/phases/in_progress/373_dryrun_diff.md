# Phase 373: the dry-run diff for the live migration

- **Written:** `2026-10-06T21:05:40`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre373_20261006_210540.db`
- **Backup sha256:** `4aef54846d724be236e670512223c850d48373868f46d59c83afddf46cb7de31`
- **Scope sha256:** `c66f8d3e8c861309df43892e241017e151a602f81cabc1c1fd14f8298ae21568`
- **Migrations applied on the copy:** `[81]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
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
- added rowid 80: (81, '2026-10-07 01:05:40')
## tax_warranty_rules: +3 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)
- added rowid 2: (2, 1, None)
- added rowid 3: (3, 1, None)

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "80": {
     "applied_at": "<clock>",
     "version": 81
    }
   },
   "changed": {},
   "removed": {}
  },
  "tax_warranty_rules": {
   "added": {
    "1": {
     "basis": "stated",
     "checked_on": "2026-10-06",
     "created_at": "<clock>",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 1,
     "jurisdiction_id": 1,
     "notes": "A reading, to be confirmed by the shop's accountant before a real warranty job.",
     "payer": "maker_with_bike",
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "quoting Sales Tax Information Letter #3: a dealer replaces a defective part under the warranty and bills the maker; \"No sales tax is to be collected. The sales price of the new automobile included the warranty.\"",
     "source_title": "Massachusetts DOR, Letter Ruling 03-8",
     "source_url": "https://www.mass.gov/letter-ruling/letter-ruling-03-8-sales-tax-consequences-of-certain-merchandise-exchanges",
     "taxed_on_claim": 0,
     "valid_until": "2027-10-06"
    },
    "2": {
     "basis": "reading",
     "checked_on": "2026-10-06",
     "created_at": "<clock>",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 2,
     "jurisdiction_id": 1,
     "notes": "A reading, to be confirmed by the shop's accountant before a real warranty job. LR 85-1: https://www.mass.gov/letter-ruling/letter-ruling-85-1-vinyl-repair-service",
     "payer": "other",
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "LR 79-19: separately stated parts are taxable \"whether or not the charges are partially or fully covered by the Plan\"; LR 85-1: \"Whether an automobile upon which work is performed is under warranty is irrelevant for sales tax purposes.\" The tax is added to the claim: a reading.",
     "source_title": "Massachusetts DOR, Letter Rulings 79-19 and 85-1",
     "source_url": "https://www.mass.gov/letter-ruling/letter-ruling-79-19-motor-vehicle-buyer-protection-plan",
     "taxed_on_claim": 1,
     "valid_until": "2027-10-06"
    },
    "3": {
     "basis": "stated",
     "checked_on": "2026-10-06",
     "created_at": "<clock>",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 3,
     "jurisdiction_id": 1,
     "notes": "A reading, to be confirmed by the shop's accountant before a real warranty job.",
     "payer": "shop_contract",
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "830 CMR 64H.1.1(5)(g): the service enterprise \"is the consumer of parts\" it uses under a service contract, pays the tax when it buys them, and \"does not collect the sales tax from its customer\"",
     "source_title": "Massachusetts DOR, 830 CMR 64H.1.1 Services Enterprises",
     "source_url": "https://www.mass.gov/regulations/830-CMR-64h11-service-enterprises",
     "taxed_on_claim": 0,
     "valid_until": "2027-10-06"
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_tax_warranty_rules_jurisdiction",
   "index idx_warranty_claim_lines_claim",
   "table accounting_export_claims",
   "table tax_warranty_rules",
   "table warranty_claim_lines"
  ],
  "changed": [
   "table invoices",
   "table warranties",
   "table warranty_claims"
  ],
  "removed": [],
  "sql": {
   "index idx_tax_warranty_rules_jurisdiction": "CREATE INDEX idx_tax_warranty_rules_jurisdiction\n                ON tax_warranty_rules(jurisdiction_id, payer, effective_from)",
   "index idx_warranty_claim_lines_claim": "CREATE INDEX idx_warranty_claim_lines_claim\n                ON warranty_claim_lines(claim_id)",
   "table accounting_export_claims": "CREATE TABLE accounting_export_claims (\n                export_id INTEGER NOT NULL,\n                claim_id INTEGER NOT NULL,\n                PRIMARY KEY (export_id, claim_id),\n                FOREIGN KEY (export_id)\n                    REFERENCES accounting_exports(id) ON DELETE CASCADE,\n                FOREIGN KEY (claim_id)\n                    REFERENCES warranty_claims(id) ON DELETE CASCADE\n            )",
   "table invoices": "CREATE TABLE invoices (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                customer_id INTEGER NOT NULL,\n                repair_plan_id INTEGER,\n                invoice_number TEXT NOT NULL UNIQUE,\n                status TEXT NOT NULL DEFAULT 'draft',\n                subtotal REAL NOT NULL DEFAULT 0.0,\n                tax_amount REAL NOT NULL DEFAULT 0.0,\n                total REAL NOT NULL DEFAULT 0.0,\n                currency TEXT NOT NULL DEFAULT 'USD',\n                issued_at TIMESTAMP,\n                due_at TIMESTAMP,\n                paid_at TIMESTAMP,\n                notes TEXT,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                updated_at TIMESTAMP, work_order_id INTEGER, tax_rate REAL, tax_rate_id INTEGER, tax_source TEXT, tax_recheck_by TEXT, taxed_line_types TEXT, fx_from_currency TEXT, fx_rate TEXT, fx_rate_id INTEGER, fx_rate_date TEXT, fx_source TEXT, shortfall_claim_id INTEGER,\n                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,\n                FOREIGN KEY (repair_plan_id) REFERENCES repair_plans(id) ON DELETE SET NULL\n            )",
   "table tax_warranty_rules": "CREATE TABLE tax_warranty_rules (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                jurisdiction_id INTEGER NOT NULL,\n                shop_id INTEGER,\n                payer TEXT NOT NULL\n                    CHECK (payer IN ('maker_with_bike', 'other', 'shop_contract')),\n                taxed_on_claim INTEGER NOT NULL CHECK (taxed_on_claim IN (0, 1)),\n                basis TEXT NOT NULL CHECK (basis IN ('stated', 'reading')),\n                effective_from TEXT NOT NULL,\n                valid_until TEXT NOT NULL CHECK (valid_until >= effective_from),\n                source_title TEXT NOT NULL CHECK (length(trim(source_title)) > 0),\n                source_url TEXT,\n                source_clause TEXT,\n                checked_on TEXT NOT NULL,\n                provenance TEXT NOT NULL CHECK (provenance IN ('regulation', 'shop')),\n                entered_by_user_id INTEGER,\n                notes TEXT,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                CHECK ((provenance = 'regulation') = (shop_id IS NULL)),\n                FOREIGN KEY (jurisdiction_id)\n                    REFERENCES tax_jurisdictions(id) ON DELETE CASCADE,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table warranties": "CREATE TABLE warranties (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                vehicle_id INTEGER NOT NULL,\n                coverage_type TEXT NOT NULL,\n                provider TEXT,\n                start_date TEXT,\n                end_date TEXT,\n                mileage_limit INTEGER,\n                terms TEXT,\n                claim_count INTEGER NOT NULL DEFAULT 0,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, repair_payer TEXT\n                CHECK (repair_payer IS NULL\n                       OR repair_payer IN ('maker_with_bike', 'other', 'shop_contract')),\n                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE\n            )",
   "table warranty_claim_lines": "CREATE TABLE warranty_claim_lines (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                claim_id INTEGER NOT NULL,\n                line_type TEXT NOT NULL CHECK (line_type IN ('labor', 'parts')),\n                work_order_part_id INTEGER,\n                quantity REAL NOT NULL CHECK (quantity > 0),\n                amount_cents INTEGER CHECK (amount_cents IS NULL OR amount_cents >= 0),\n                description TEXT,\n                CHECK ((line_type = 'labor') = (work_order_part_id IS NULL)),\n                FOREIGN KEY (claim_id)\n                    REFERENCES warranty_claims(id) ON DELETE CASCADE,\n                FOREIGN KEY (work_order_part_id)\n                    REFERENCES work_order_parts(id) ON DELETE RESTRICT\n            )",
   "table warranty_claims": "CREATE TABLE warranty_claims (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                warranty_id INTEGER NOT NULL,\n                work_order_id INTEGER,\n                status TEXT NOT NULL DEFAULT 'draft'\n                    CHECK (status IN ('draft', 'submitted', 'approved',\n                                      'denied', 'paid')),\n                claim_number TEXT,\n                description TEXT NOT NULL\n                    CHECK (length(trim(description)) > 0),\n                amount_claimed_cents INTEGER\n                    CHECK (amount_claimed_cents IS NULL\n                           OR amount_claimed_cents >= 0),\n                amount_approved_cents INTEGER\n                    CHECK (amount_approved_cents IS NULL\n                           OR amount_approved_cents >= 0),\n                opened_at TEXT NOT NULL,\n                submitted_at TEXT,\n                decided_at TEXT,\n                paid_at TEXT,\n                notes TEXT, coverage_recorded_at TEXT, invoice_id INTEGER, covered_cents INTEGER\n                CHECK (covered_cents IS NULL OR covered_cents >= 0), tax_cents INTEGER\n                CHECK (tax_cents IS NULL OR tax_cents >= 0), tax_source TEXT, settlement TEXT\n                CHECK (settlement IS NULL\n                       OR settlement IN ('bill_customer', 'absorb')), settled_at TEXT, shortfall_cents INTEGER\n                CHECK (shortfall_cents IS NULL OR shortfall_cents >= 0), shortfall_invoice_id INTEGER,\n                FOREIGN KEY (warranty_id)\n                    REFERENCES warranties(id) ON DELETE CASCADE,\n                FOREIGN KEY (work_order_id)\n                    REFERENCES work_orders(id) ON DELETE SET NULL\n            )"
  }
 }
}
```
