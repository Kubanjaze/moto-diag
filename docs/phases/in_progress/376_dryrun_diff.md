# Phase 376: the dry-run diff for the live migration

- **Written:** `2026-10-07T18:34:25`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre376_20261007_183425.db`
- **Backup sha256:** `5539d08e71206b49717c1ba86171a92f2b575172ea4e8b67a12c87382f658aa7`
- **Scope sha256:** `9db49dff1669fe912e5d4d8cf8db500f825375b25003a2b72b8ae3b760df535f`
- **Migrations applied on the copy:** `[83]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
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
- added rowid 82: (83, '2026-10-07 22:34:25')
## tax_settlement_rules: +1 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "82": {
     "applied_at": "<clock>",
     "version": 83
    }
   },
   "changed": {},
   "removed": {}
  },
  "tax_settlement_rules": {
   "added": {
    "1": {
     "absorbed_tax": "stays_owed",
     "basis": "reading",
     "checked_on": "2026-10-07",
     "created_at": "<clock>",
     "effective_from": "1999-01-01",
     "entered_by_user_id": null,
     "id": 1,
     "jurisdiction_id": 1,
     "notes": "A reading, to be confirmed by the shop's accountant: the tax charged on the claim stays owed when the shop absorbs a shortfall; any ST-BDR claim is the accountant's, not the export's. Not settled by the sources read: whether a part approval is a bad debt or a price reduction (830 CMR 64H.1.4, not readable), and tax on the cost of parts given away under a claim that carried no tax.",
     "provenance": "regulation",
     "settlement": "absorb",
     "shop_id": null,
     "source_clause": "\"Bad debt reimbursements may not be claimed on any other return and bad debts may not be subtracted from gross receipts on a vendor's sales or use tax return.\" Relief is a yearly claim on Form ST-BDR (G.L. c. 64H, s. 33) once the account is written off under IRC s. 166.",
     "source_title": "Massachusetts DOR, TIR 00-3: Claiming the Bad Debt Reimbursement",
     "source_url": "https://www.mass.gov/technical-information-release/tir-00-3-claiming-the-bad-debt-reimbursement",
     "valid_until": "2027-10-07"
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_accounting_export_settlements_claim",
   "index idx_tax_settlement_rules_jurisdiction",
   "table accounting_export_files",
   "table accounting_export_settlements",
   "table tax_settlement_rules"
  ],
  "changed": [
   "table accounting_accounts",
   "table accounting_exports"
  ],
  "removed": [],
  "sql": {
   "index idx_accounting_export_settlements_claim": "CREATE INDEX idx_accounting_export_settlements_claim\n                ON accounting_export_settlements(claim_id)",
   "index idx_tax_settlement_rules_jurisdiction": "CREATE INDEX idx_tax_settlement_rules_jurisdiction\n                ON tax_settlement_rules(jurisdiction_id, settlement, effective_from)",
   "table accounting_accounts": "CREATE TABLE \"accounting_accounts\" (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                shop_id INTEGER NOT NULL,\n                target TEXT NOT NULL\n                    CHECK (target IN ('quickbooks_online', 'xero')),\n                kind TEXT NOT NULL\n                    CHECK (kind IN ('labor', 'parts', 'diagnostic', 'misc',\n                                    'tax', 'receivable', 'absorbed')),\n                account TEXT NOT NULL CHECK (length(trim(account)) > 0),\n                tax_type TEXT,\n                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                UNIQUE (shop_id, target, kind),\n                FOREIGN KEY (shop_id)\n                    REFERENCES shops(id) ON DELETE CASCADE\n            )",
   "table accounting_export_files": "CREATE TABLE accounting_export_files (\n                export_id INTEGER NOT NULL,\n                holds TEXT NOT NULL\n                    CHECK (holds IN ('journal_entries', 'invoices', 'credit_notes')),\n                file_name TEXT NOT NULL,\n                file_sha256 TEXT NOT NULL,\n                row_count INTEGER NOT NULL CHECK (row_count >= 0),\n                PRIMARY KEY (export_id, holds),\n                FOREIGN KEY (export_id)\n                    REFERENCES accounting_exports(id) ON DELETE CASCADE\n            )",
   "table accounting_export_settlements": "CREATE TABLE accounting_export_settlements (\n                export_id INTEGER NOT NULL,\n                claim_id INTEGER NOT NULL,\n                PRIMARY KEY (export_id, claim_id),\n                FOREIGN KEY (export_id)\n                    REFERENCES accounting_exports(id) ON DELETE CASCADE,\n                FOREIGN KEY (claim_id)\n                    REFERENCES warranty_claims(id) ON DELETE CASCADE\n            )",
   "table accounting_exports": "CREATE TABLE \"accounting_exports\" (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                shop_id INTEGER NOT NULL,\n                target TEXT NOT NULL\n                    CHECK (target IN ('quickbooks_online', 'xero')),\n                period_from TEXT NOT NULL,\n                period_to TEXT NOT NULL,\n                file_name TEXT NOT NULL,\n                file_sha256 TEXT NOT NULL,\n                invoice_count INTEGER NOT NULL CHECK (invoice_count >= 0),\n                exported_at TEXT NOT NULL,\n                settlement_count INTEGER NOT NULL DEFAULT 0\n                    CHECK (settlement_count >= 0),\n                CHECK (invoice_count + settlement_count > 0),\n                FOREIGN KEY (shop_id)\n                    REFERENCES shops(id) ON DELETE CASCADE\n            )",
   "table tax_settlement_rules": "CREATE TABLE tax_settlement_rules (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                jurisdiction_id INTEGER NOT NULL,\n                shop_id INTEGER,\n                settlement TEXT NOT NULL CHECK (settlement IN ('absorb')),\n                absorbed_tax TEXT NOT NULL CHECK (absorbed_tax IN ('stays_owed')),\n                basis TEXT NOT NULL CHECK (basis IN ('stated', 'reading')),\n                effective_from TEXT NOT NULL,\n                valid_until TEXT NOT NULL CHECK (valid_until >= effective_from),\n                source_title TEXT NOT NULL CHECK (length(trim(source_title)) > 0),\n                source_url TEXT,\n                source_clause TEXT,\n                checked_on TEXT NOT NULL,\n                provenance TEXT NOT NULL CHECK (provenance IN ('regulation', 'shop')),\n                entered_by_user_id INTEGER,\n                notes TEXT,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                CHECK ((provenance = 'regulation') = (shop_id IS NULL)),\n                FOREIGN KEY (jurisdiction_id)\n                    REFERENCES tax_jurisdictions(id) ON DELETE CASCADE,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )"
  }
 }
}
```
