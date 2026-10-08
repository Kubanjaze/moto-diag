# Phase 375: the dry-run diff for the live migration

- **Written:** `2026-10-07T22:03:25`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre375_20261007_220325.db`
- **Backup sha256:** `b4f23ab1e7e7295253619a4706a944be797db74b886dcd634c49aab31e2b5a87`
- **Scope sha256:** `323839311f2739fbcc701345f4a7971eaaeb10dffc16130b19facebc54086ce1`
- **Migrations applied on the copy:** `[84]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
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
- added rowid 83: (84, '2026-10-08 02:03:25')
## tax_deductible_rules: +3 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)
- added rowid 2: (2, 1, None)
- added rowid 3: (3, 1, None)

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "83": {
     "applied_at": "<clock>",
     "version": 84
    }
   },
   "changed": {},
   "removed": {}
  },
  "tax_deductible_rules": {
   "added": {
    "1": {
     "basis": "reading",
     "checked_on": "2026-10-07",
     "created_at": "<clock>",
     "deductible_tax": "taxable_share",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 1,
     "jurisdiction_id": 1,
     "notes": "A reading, to be confirmed by the shop's accountant before a real warranty job. The deductible is split over the covered lines and stated by kind (LR 85-8: https://www.mass.gov/letter-ruling/letter-ruling-85-8-auto-repairs); its taxable share is taxed to the customer, and the claim carries the rest of the tax on the covered parts, so together they are the tax on the entire parts charge. Left open by the sources: none names a deductible, or says whether the plan's deductible includes tax.",
     "payer": "other",
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "LR 79-19, on a plan whose customer pays \"a $25.00 deductible amount for any single covered repair\": \"the entire amount charged by the dealer for parts is taxable under the Massachusetts sales tax whether or not the charges are partially or fully covered by the Plan.\" LR 85-8: when the parts and labor charges are not separately stated, \"the entire value of the charge is subject to the sales tax\" if the parts are ten percent or more of it.",
     "source_title": "Massachusetts DOR, Letter Rulings 79-19 and 85-8",
     "source_url": "https://www.mass.gov/letter-ruling/letter-ruling-79-19-motor-vehicle-buyer-protection-plan",
     "valid_until": "2027-10-07"
    },
    "2": {
     "basis": "reading",
     "checked_on": "2026-10-07",
     "created_at": "<clock>",
     "deductible_tax": "taxable_share",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 2,
     "jurisdiction_id": 1,
     "notes": "A reading, to be confirmed by the shop's accountant before a real warranty job. Left open by the sources: LR 03-8 states no tax only for a repair with no additional consideration from the retail customer; a deductible is consideration paid by the customer, and LR 03-8 does not rule on that case. This reading taxes the deductible's taxable share to the customer; the claim carries no tax.",
     "payer": "maker_with_bike",
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "LR 03-8: a repair or exchange under a warranty included in the price \"with no additional consideration from the retail customer\" is \"neither a rescission of the retail sale nor an additional sale\". LR 85-8: a charge whose parts are not separately stated is taxable whole when the parts are ten percent or more of it.",
     "source_title": "Massachusetts DOR, Letter Rulings 03-8 and 85-8",
     "source_url": "https://www.mass.gov/letter-ruling/letter-ruling-03-8-sales-tax-consequences-of-certain-merchandise-exchanges",
     "valid_until": "2027-10-07"
    },
    "3": {
     "basis": "reading",
     "checked_on": "2026-10-07",
     "created_at": "<clock>",
     "deductible_tax": "taxable_share",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 3,
     "jurisdiction_id": 1,
     "notes": "A reading, to be confirmed by the shop's accountant before a real warranty job. Left open by the sources: whether a deductible is a \"separate charge\" for property the original contract price does not include under 830 CMR 64H.1.1(5)(g); this reading collects tax on its taxable share. Where the shop already paid tax buying those parts, LR 80-17 (https://www.mass.gov/letter-ruling/letter-ruling-80-17-optional-maintenance-and-consulting-contracts-name) lets it deduct their cost from gross sales on its next return: the accountant's adjustment, not the export's.",
     "payer": "shop_contract",
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "830 CMR 64H.1.1(5)(g): \"A service enterprise shall collect the sales tax on any tangible personal property which the original contract price does not include and for which the service enterprise makes a separate charge.\" LR 80-17: the same, and \"it may deduct the cost of the property to it from gross sales as an adjustment on its next sales tax return.\"",
     "source_title": "Massachusetts DOR, 830 CMR 64H.1.1, Letter Rulings 80-17 and 85-8",
     "source_url": "https://www.mass.gov/regulations/830-CMR-64h11-service-enterprises",
     "valid_until": "2027-10-07"
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_tax_deductible_rules_jurisdiction",
   "table tax_deductible_rules"
  ],
  "changed": [
   "table warranties",
   "table warranty_claim_lines",
   "table warranty_claims"
  ],
  "removed": [],
  "sql": {
   "index idx_tax_deductible_rules_jurisdiction": "CREATE INDEX idx_tax_deductible_rules_jurisdiction\n                ON tax_deductible_rules(jurisdiction_id, payer, effective_from)",
   "table tax_deductible_rules": "CREATE TABLE tax_deductible_rules (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                jurisdiction_id INTEGER NOT NULL,\n                shop_id INTEGER,\n                payer TEXT NOT NULL\n                    CHECK (payer IN ('maker_with_bike', 'other', 'shop_contract')),\n                deductible_tax TEXT NOT NULL CHECK (deductible_tax IN ('taxable_share')),\n                basis TEXT NOT NULL CHECK (basis IN ('stated', 'reading')),\n                effective_from TEXT NOT NULL,\n                valid_until TEXT NOT NULL CHECK (valid_until >= effective_from),\n                source_title TEXT NOT NULL CHECK (length(trim(source_title)) > 0),\n                source_url TEXT,\n                source_clause TEXT,\n                checked_on TEXT NOT NULL,\n                provenance TEXT NOT NULL CHECK (provenance IN ('regulation', 'shop')),\n                entered_by_user_id INTEGER,\n                notes TEXT,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                CHECK ((provenance = 'regulation') = (shop_id IS NULL)),\n                FOREIGN KEY (jurisdiction_id)\n                    REFERENCES tax_jurisdictions(id) ON DELETE CASCADE,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table warranties": "CREATE TABLE warranties (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                vehicle_id INTEGER NOT NULL,\n                coverage_type TEXT NOT NULL,\n                provider TEXT,\n                start_date TEXT,\n                end_date TEXT,\n                mileage_limit INTEGER,\n                terms TEXT,\n                claim_count INTEGER NOT NULL DEFAULT 0,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, repair_payer TEXT\n                CHECK (repair_payer IS NULL\n                       OR repair_payer IN ('maker_with_bike', 'other', 'shop_contract')), deductible_cents INTEGER\n                CHECK (deductible_cents IS NULL OR deductible_cents >= 0),\n                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE\n            )",
   "table warranty_claim_lines": "CREATE TABLE warranty_claim_lines (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                claim_id INTEGER NOT NULL,\n                line_type TEXT NOT NULL CHECK (line_type IN ('labor', 'parts')),\n                work_order_part_id INTEGER,\n                quantity REAL NOT NULL CHECK (quantity > 0),\n                amount_cents INTEGER CHECK (amount_cents IS NULL OR amount_cents >= 0),\n                description TEXT, deductible_cents INTEGER\n                CHECK (deductible_cents IS NULL OR deductible_cents >= 0),\n                CHECK ((line_type = 'labor') = (work_order_part_id IS NULL)),\n                FOREIGN KEY (claim_id)\n                    REFERENCES warranty_claims(id) ON DELETE CASCADE,\n                FOREIGN KEY (work_order_part_id)\n                    REFERENCES work_order_parts(id) ON DELETE RESTRICT\n            )",
   "table warranty_claims": "CREATE TABLE warranty_claims (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                warranty_id INTEGER NOT NULL,\n                work_order_id INTEGER,\n                status TEXT NOT NULL DEFAULT 'draft'\n                    CHECK (status IN ('draft', 'submitted', 'approved',\n                                      'denied', 'paid')),\n                claim_number TEXT,\n                description TEXT NOT NULL\n                    CHECK (length(trim(description)) > 0),\n                amount_claimed_cents INTEGER\n                    CHECK (amount_claimed_cents IS NULL\n                           OR amount_claimed_cents >= 0),\n                amount_approved_cents INTEGER\n                    CHECK (amount_approved_cents IS NULL\n                           OR amount_approved_cents >= 0),\n                opened_at TEXT NOT NULL,\n                submitted_at TEXT,\n                decided_at TEXT,\n                paid_at TEXT,\n                notes TEXT, coverage_recorded_at TEXT, invoice_id INTEGER, covered_cents INTEGER\n                CHECK (covered_cents IS NULL OR covered_cents >= 0), tax_cents INTEGER\n                CHECK (tax_cents IS NULL OR tax_cents >= 0), tax_source TEXT, settlement TEXT\n                CHECK (settlement IS NULL\n                       OR settlement IN ('bill_customer', 'absorb')), settled_at TEXT, shortfall_cents INTEGER\n                CHECK (shortfall_cents IS NULL OR shortfall_cents >= 0), shortfall_invoice_id INTEGER, deductible_cents INTEGER\n                CHECK (deductible_cents IS NULL OR deductible_cents >= 0), deductible_tax_cents INTEGER\n                CHECK (deductible_tax_cents IS NULL OR deductible_tax_cents >= 0), deductible_tax_source TEXT,\n                FOREIGN KEY (warranty_id)\n                    REFERENCES warranties(id) ON DELETE CASCADE,\n                FOREIGN KEY (work_order_id)\n                    REFERENCES work_orders(id) ON DELETE SET NULL\n            )"
  }
 }
}
```
