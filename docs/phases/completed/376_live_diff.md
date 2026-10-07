# Phase 376: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

## schema added: index idx_accounting_export_settlements_claim

```sql
CREATE INDEX idx_accounting_export_settlements_claim
                ON accounting_export_settlements(claim_id)
```

## schema added: index idx_tax_settlement_rules_jurisdiction

```sql
CREATE INDEX idx_tax_settlement_rules_jurisdiction
                ON tax_settlement_rules(jurisdiction_id, settlement, effective_from)
```

## schema added: table accounting_export_files

```sql
CREATE TABLE accounting_export_files (
                export_id INTEGER NOT NULL,
                holds TEXT NOT NULL
                    CHECK (holds IN ('journal_entries', 'invoices', 'credit_notes')),
                file_name TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                row_count INTEGER NOT NULL CHECK (row_count >= 0),
                PRIMARY KEY (export_id, holds),
                FOREIGN KEY (export_id)
                    REFERENCES accounting_exports(id) ON DELETE CASCADE
            )
```

## schema added: table accounting_export_settlements

```sql
CREATE TABLE accounting_export_settlements (
                export_id INTEGER NOT NULL,
                claim_id INTEGER NOT NULL,
                PRIMARY KEY (export_id, claim_id),
                FOREIGN KEY (export_id)
                    REFERENCES accounting_exports(id) ON DELETE CASCADE,
                FOREIGN KEY (claim_id)
                    REFERENCES warranty_claims(id) ON DELETE CASCADE
            )
```

## schema added: table tax_settlement_rules

```sql
CREATE TABLE tax_settlement_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jurisdiction_id INTEGER NOT NULL,
                shop_id INTEGER,
                settlement TEXT NOT NULL CHECK (settlement IN ('absorb')),
                absorbed_tax TEXT NOT NULL CHECK (absorbed_tax IN ('stays_owed')),
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

## schema changed: table accounting_accounts

```sql
CREATE TABLE "accounting_accounts" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                target TEXT NOT NULL
                    CHECK (target IN ('quickbooks_online', 'xero')),
                kind TEXT NOT NULL
                    CHECK (kind IN ('labor', 'parts', 'diagnostic', 'misc',
                                    'tax', 'receivable', 'absorbed')),
                account TEXT NOT NULL CHECK (length(trim(account)) > 0),
                tax_type TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (shop_id, target, kind),
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE
            )
```

## schema changed: table accounting_exports

```sql
CREATE TABLE "accounting_exports" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id INTEGER NOT NULL,
                target TEXT NOT NULL
                    CHECK (target IN ('quickbooks_online', 'xero')),
                period_from TEXT NOT NULL,
                period_to TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                invoice_count INTEGER NOT NULL CHECK (invoice_count >= 0),
                exported_at TEXT NOT NULL,
                settlement_count INTEGER NOT NULL DEFAULT 0
                    CHECK (settlement_count >= 0),
                CHECK (invoice_count + settlement_count > 0),
                FOREIGN KEY (shop_id)
                    REFERENCES shops(id) ON DELETE CASCADE
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 82: (83, '2026-10-07 22:36:13')
## tax_settlement_rules: +1 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)
