# Phase 281: the dry-run diff for the live migration

- **Written:** `2026-10-01T13:24:46`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre281_20261001_132445.db`
- **Backup sha256:** `8b27328912949761dafe8dcb49cf87fe454775799ea9d07214d19bdab976f92a`
- **Scope sha256:** `5251a1d3b9a749c1a681a9772ae773ab3eef192c9fedba80acb7d0d728c70e47`
- **Migrations applied on the copy:** `[78]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema added: index idx_exchange_rates_ecb_day

```sql
CREATE UNIQUE INDEX idx_exchange_rates_ecb_day
                ON exchange_rates(base, quote, rate_date) WHERE source = 'ecb'
```

## schema added: index idx_exchange_rates_pair

```sql
CREATE INDEX idx_exchange_rates_pair
                ON exchange_rates(base, quote, rate_date)
```

## schema added: index idx_recall_fetches_vehicle

```sql
CREATE INDEX idx_recall_fetches_vehicle
                ON recall_fetches(make, model_year, fetched_at)
```

## schema added: index idx_recall_vehicles_lookup

```sql
CREATE INDEX idx_recall_vehicles_lookup
                ON recall_vehicles(make, model_year)
```

## schema added: index idx_tax_line_rules_jurisdiction

```sql
CREATE INDEX idx_tax_line_rules_jurisdiction
                ON tax_line_rules(jurisdiction_id, line_type, shop_id)
```

## schema added: index idx_tax_rates_jurisdiction

```sql
CREATE INDEX idx_tax_rates_jurisdiction
                ON tax_rates(jurisdiction_id, shop_id, effective_from)
```

## schema added: table exchange_rates

```sql
CREATE TABLE exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base TEXT NOT NULL CHECK (length(base) = 3),
                quote TEXT NOT NULL CHECK (length(quote) = 3 AND quote <> base),
                rate TEXT NOT NULL CHECK (CAST(rate AS REAL) > 0),
                rate_date TEXT NOT NULL,
                valid_until TEXT NOT NULL CHECK (valid_until >= rate_date),
                source TEXT NOT NULL CHECK (source IN ('ecb', 'shop')),
                shop_id INTEGER,
                source_url TEXT,
                source_note TEXT,
                entered_by_user_id INTEGER,
                fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK ((source = 'ecb') = (shop_id IS NULL)),
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
```

## schema added: table recall_fetches

```sql
CREATE TABLE recall_fetches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                model_year INTEGER NOT NULL,
                fetched_at TEXT NOT NULL,
                url TEXT NOT NULL,
                http_status INTEGER,
                result_count INTEGER,
                outcome TEXT NOT NULL CHECK (outcome IN ('ok', 'failed')),
                error TEXT,
                CHECK ((outcome = 'ok') = (result_count IS NOT NULL AND error IS NULL))
            )
```

## schema added: table recall_vehicles

```sql
CREATE TABLE recall_vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recall_id INTEGER NOT NULL,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                model_year INTEGER,
                UNIQUE (recall_id, make, model, model_year),
                FOREIGN KEY (recall_id) REFERENCES recalls(id) ON DELETE CASCADE
            )
```

## schema added: table shop_tax_jurisdictions

```sql
CREATE TABLE shop_tax_jurisdictions (
                shop_id INTEGER PRIMARY KEY,
                jurisdiction_id INTEGER NOT NULL,
                set_by_user_id INTEGER,
                set_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,
                FOREIGN KEY (jurisdiction_id)
                    REFERENCES tax_jurisdictions(id) ON DELETE RESTRICT,
                FOREIGN KEY (set_by_user_id) REFERENCES users(id) ON DELETE SET NULL
            )
```

## schema added: table tax_jurisdictions

```sql
CREATE TABLE tax_jurisdictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                currency TEXT NOT NULL CHECK (length(currency) = 3),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
```

## schema added: table tax_line_rules

```sql
CREATE TABLE tax_line_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jurisdiction_id INTEGER NOT NULL,
                shop_id INTEGER,
                line_type TEXT NOT NULL
                    CHECK (line_type IN ('labor', 'parts', 'diagnostic', 'misc')),
                taxable INTEGER NOT NULL CHECK (taxable IN (0, 1)),
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

## schema added: table tax_rates

```sql
CREATE TABLE tax_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jurisdiction_id INTEGER NOT NULL,
                shop_id INTEGER,
                rate REAL NOT NULL CHECK (rate >= 0 AND rate < 1),
                effective_from TEXT NOT NULL,
                valid_until TEXT NOT NULL CHECK (valid_until >= effective_from),
                source_title TEXT NOT NULL CHECK (length(trim(source_title)) > 0),
                source_url TEXT,
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

## schema added: table vin_decodes

```sql
CREATE TABLE vin_decodes (
                vin TEXT PRIMARY KEY,
                make TEXT,
                model TEXT,
                model_year INTEGER,
                manufacturer TEXT,
                vehicle_type TEXT,
                error_code TEXT,
                error_text TEXT,
                response_json TEXT NOT NULL,
                url TEXT NOT NULL,
                fetched_at TEXT NOT NULL
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
                updated_at TIMESTAMP, work_order_id INTEGER, tax_rate REAL, tax_rate_id INTEGER, tax_source TEXT, tax_recheck_by TEXT, taxed_line_types TEXT, fx_from_currency TEXT, fx_rate TEXT, fx_rate_id INTEGER, fx_rate_date TEXT, fx_source TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,
                FOREIGN KEY (repair_plan_id) REFERENCES repair_plans(id) ON DELETE SET NULL
            )
```

## schema changed: table recalls

```sql
CREATE TABLE recalls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_number TEXT NOT NULL UNIQUE,
                make TEXT NOT NULL,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                description TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium',
                remedy TEXT,
                notification_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            , nhtsa_id TEXT, vin_range TEXT, open INTEGER NOT NULL DEFAULT 1, source TEXT
                CHECK (source IS NULL OR source = 'nhtsa'), fetched_at TEXT, component TEXT, consequence TEXT)
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 77: (78, '2026-10-01 17:24:45')
## tax_jurisdictions: +1 added, 0 changed, 0 removed
- added rowid 1: (1, 'US-MA', 'Massachusetts')
## tax_line_rules: +3 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)
- added rowid 2: (2, 1, None)
- added rowid 3: (3, 1, None)
## tax_rates: +1 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "77": {
     "applied_at": "<clock>",
     "version": 78
    }
   },
   "changed": {},
   "removed": {}
  },
  "tax_jurisdictions": {
   "added": {
    "1": {
     "code": "US-MA",
     "created_at": "<clock>",
     "currency": "USD",
     "id": 1,
     "name": "Massachusetts"
    }
   },
   "changed": {},
   "removed": {}
  },
  "tax_line_rules": {
   "added": {
    "1": {
     "basis": "stated",
     "checked_on": "2026-09-30",
     "created_at": "<clock>",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 1,
     "jurisdiction_id": 1,
     "line_type": "parts",
     "notes": null,
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "830 CMR 64H.1.1(2)(b)1 and (5)(a): separately stated parts are taxable",
     "source_title": "Massachusetts DOR, 830 CMR 64H.1.1 Services Enterprises",
     "source_url": "https://www.mass.gov/regulations/830-CMR-64h11-service-enterprises",
     "taxable": 1,
     "valid_until": "2027-09-30"
    },
    "2": {
     "basis": "stated",
     "checked_on": "2026-09-30",
     "created_at": "<clock>",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 2,
     "jurisdiction_id": 1,
     "line_type": "labor",
     "notes": null,
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "830 CMR 64H.1.1(2)(a)1 and (5)(a), and the DOR guide's \"Car repairs\": separately stated labour is not taxable",
     "source_title": "Massachusetts DOR, 830 CMR 64H.1.1 Services Enterprises",
     "source_url": "https://www.mass.gov/regulations/830-CMR-64h11-service-enterprises",
     "taxable": 0,
     "valid_until": "2027-09-30"
    },
    "3": {
     "basis": "reading",
     "checked_on": "2026-09-30",
     "created_at": "<clock>",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 3,
     "jurisdiction_id": 1,
     "line_type": "diagnostic",
     "notes": null,
     "provenance": "regulation",
     "shop_id": null,
     "source_clause": "a reading of 830 CMR 64H.1.1(2)(a)1: a service with no transfer of property; the regulation does not name a diagnostic fee",
     "source_title": "Massachusetts DOR, 830 CMR 64H.1.1 Services Enterprises",
     "source_url": "https://www.mass.gov/regulations/830-CMR-64h11-service-enterprises",
     "taxable": 0,
     "valid_until": "2027-09-30"
    }
   },
   "changed": {},
   "removed": {}
  },
  "tax_rates": {
   "added": {
    "1": {
     "checked_on": "2026-09-30",
     "created_at": "<clock>",
     "effective_from": "2009-08-01",
     "entered_by_user_id": null,
     "id": 1,
     "jurisdiction_id": 1,
     "notes": "Effective date from TIR 09-11: https://www.mass.gov/technical-information-release/tir-09-11-change-in-rate-scope-and-computation-of-salesuse-taxes",
     "provenance": "regulation",
     "rate": 0.0625,
     "shop_id": null,
     "source_title": "Massachusetts DOR, Sales and Use Tax guide; TIR 09-11",
     "source_url": "https://www.mass.gov/guides/sales-and-use-tax",
     "valid_until": "2027-09-30"
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_exchange_rates_ecb_day",
   "index idx_exchange_rates_pair",
   "index idx_recall_fetches_vehicle",
   "index idx_recall_vehicles_lookup",
   "index idx_tax_line_rules_jurisdiction",
   "index idx_tax_rates_jurisdiction",
   "table exchange_rates",
   "table recall_fetches",
   "table recall_vehicles",
   "table shop_tax_jurisdictions",
   "table tax_jurisdictions",
   "table tax_line_rules",
   "table tax_rates",
   "table vin_decodes"
  ],
  "changed": [
   "table invoices",
   "table recalls"
  ],
  "removed": [],
  "sql": {
   "index idx_exchange_rates_ecb_day": "CREATE UNIQUE INDEX idx_exchange_rates_ecb_day\n                ON exchange_rates(base, quote, rate_date) WHERE source = 'ecb'",
   "index idx_exchange_rates_pair": "CREATE INDEX idx_exchange_rates_pair\n                ON exchange_rates(base, quote, rate_date)",
   "index idx_recall_fetches_vehicle": "CREATE INDEX idx_recall_fetches_vehicle\n                ON recall_fetches(make, model_year, fetched_at)",
   "index idx_recall_vehicles_lookup": "CREATE INDEX idx_recall_vehicles_lookup\n                ON recall_vehicles(make, model_year)",
   "index idx_tax_line_rules_jurisdiction": "CREATE INDEX idx_tax_line_rules_jurisdiction\n                ON tax_line_rules(jurisdiction_id, line_type, shop_id)",
   "index idx_tax_rates_jurisdiction": "CREATE INDEX idx_tax_rates_jurisdiction\n                ON tax_rates(jurisdiction_id, shop_id, effective_from)",
   "table exchange_rates": "CREATE TABLE exchange_rates (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                base TEXT NOT NULL CHECK (length(base) = 3),\n                quote TEXT NOT NULL CHECK (length(quote) = 3 AND quote <> base),\n                rate TEXT NOT NULL CHECK (CAST(rate AS REAL) > 0),\n                rate_date TEXT NOT NULL,\n                valid_until TEXT NOT NULL CHECK (valid_until >= rate_date),\n                source TEXT NOT NULL CHECK (source IN ('ecb', 'shop')),\n                shop_id INTEGER,\n                source_url TEXT,\n                source_note TEXT,\n                entered_by_user_id INTEGER,\n                fetched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                CHECK ((source = 'ecb') = (shop_id IS NULL)),\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table invoices": "CREATE TABLE invoices (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                customer_id INTEGER NOT NULL,\n                repair_plan_id INTEGER,\n                invoice_number TEXT NOT NULL UNIQUE,\n                status TEXT NOT NULL DEFAULT 'draft',\n                subtotal REAL NOT NULL DEFAULT 0.0,\n                tax_amount REAL NOT NULL DEFAULT 0.0,\n                total REAL NOT NULL DEFAULT 0.0,\n                currency TEXT NOT NULL DEFAULT 'USD',\n                issued_at TIMESTAMP,\n                due_at TIMESTAMP,\n                paid_at TIMESTAMP,\n                notes TEXT,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                updated_at TIMESTAMP, work_order_id INTEGER, tax_rate REAL, tax_rate_id INTEGER, tax_source TEXT, tax_recheck_by TEXT, taxed_line_types TEXT, fx_from_currency TEXT, fx_rate TEXT, fx_rate_id INTEGER, fx_rate_date TEXT, fx_source TEXT,\n                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE,\n                FOREIGN KEY (repair_plan_id) REFERENCES repair_plans(id) ON DELETE SET NULL\n            )",
   "table recall_fetches": "CREATE TABLE recall_fetches (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                make TEXT NOT NULL,\n                model TEXT NOT NULL,\n                model_year INTEGER NOT NULL,\n                fetched_at TEXT NOT NULL,\n                url TEXT NOT NULL,\n                http_status INTEGER,\n                result_count INTEGER,\n                outcome TEXT NOT NULL CHECK (outcome IN ('ok', 'failed')),\n                error TEXT,\n                CHECK ((outcome = 'ok') = (result_count IS NOT NULL AND error IS NULL))\n            )",
   "table recall_vehicles": "CREATE TABLE recall_vehicles (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                recall_id INTEGER NOT NULL,\n                make TEXT NOT NULL,\n                model TEXT NOT NULL,\n                model_year INTEGER,\n                UNIQUE (recall_id, make, model, model_year),\n                FOREIGN KEY (recall_id) REFERENCES recalls(id) ON DELETE CASCADE\n            )",
   "table recalls": "CREATE TABLE recalls (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                campaign_number TEXT NOT NULL UNIQUE,\n                make TEXT NOT NULL,\n                model TEXT,\n                year_start INTEGER,\n                year_end INTEGER,\n                description TEXT NOT NULL,\n                severity TEXT NOT NULL DEFAULT 'medium',\n                remedy TEXT,\n                notification_date TEXT,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            , nhtsa_id TEXT, vin_range TEXT, open INTEGER NOT NULL DEFAULT 1, source TEXT\n                CHECK (source IS NULL OR source = 'nhtsa'), fetched_at TEXT, component TEXT, consequence TEXT)",
   "table shop_tax_jurisdictions": "CREATE TABLE shop_tax_jurisdictions (\n                shop_id INTEGER PRIMARY KEY,\n                jurisdiction_id INTEGER NOT NULL,\n                set_by_user_id INTEGER,\n                set_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n                FOREIGN KEY (jurisdiction_id)\n                    REFERENCES tax_jurisdictions(id) ON DELETE RESTRICT,\n                FOREIGN KEY (set_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table tax_jurisdictions": "CREATE TABLE tax_jurisdictions (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                code TEXT NOT NULL UNIQUE,\n                name TEXT NOT NULL CHECK (length(trim(name)) > 0),\n                currency TEXT NOT NULL CHECK (length(currency) = 3),\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP\n            )",
   "table tax_line_rules": "CREATE TABLE tax_line_rules (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                jurisdiction_id INTEGER NOT NULL,\n                shop_id INTEGER,\n                line_type TEXT NOT NULL\n                    CHECK (line_type IN ('labor', 'parts', 'diagnostic', 'misc')),\n                taxable INTEGER NOT NULL CHECK (taxable IN (0, 1)),\n                basis TEXT NOT NULL CHECK (basis IN ('stated', 'reading')),\n                effective_from TEXT NOT NULL,\n                valid_until TEXT NOT NULL CHECK (valid_until >= effective_from),\n                source_title TEXT NOT NULL CHECK (length(trim(source_title)) > 0),\n                source_url TEXT,\n                source_clause TEXT,\n                checked_on TEXT NOT NULL,\n                provenance TEXT NOT NULL CHECK (provenance IN ('regulation', 'shop')),\n                entered_by_user_id INTEGER,\n                notes TEXT,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                CHECK ((provenance = 'regulation') = (shop_id IS NULL)),\n                FOREIGN KEY (jurisdiction_id)\n                    REFERENCES tax_jurisdictions(id) ON DELETE CASCADE,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table tax_rates": "CREATE TABLE tax_rates (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                jurisdiction_id INTEGER NOT NULL,\n                shop_id INTEGER,\n                rate REAL NOT NULL CHECK (rate >= 0 AND rate < 1),\n                effective_from TEXT NOT NULL,\n                valid_until TEXT NOT NULL CHECK (valid_until >= effective_from),\n                source_title TEXT NOT NULL CHECK (length(trim(source_title)) > 0),\n                source_url TEXT,\n                checked_on TEXT NOT NULL,\n                provenance TEXT NOT NULL CHECK (provenance IN ('regulation', 'shop')),\n                entered_by_user_id INTEGER,\n                notes TEXT,\n                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                CHECK ((provenance = 'regulation') = (shop_id IS NULL)),\n                FOREIGN KEY (jurisdiction_id)\n                    REFERENCES tax_jurisdictions(id) ON DELETE CASCADE,\n                FOREIGN KEY (shop_id) REFERENCES shops(id) ON DELETE CASCADE,\n                FOREIGN KEY (entered_by_user_id) REFERENCES users(id) ON DELETE SET NULL\n            )",
   "table vin_decodes": "CREATE TABLE vin_decodes (\n                vin TEXT PRIMARY KEY,\n                make TEXT,\n                model TEXT,\n                model_year INTEGER,\n                manufacturer TEXT,\n                vehicle_type TEXT,\n                error_code TEXT,\n                error_text TEXT,\n                response_json TEXT NOT NULL,\n                url TEXT NOT NULL,\n                fetched_at TEXT NOT NULL\n            )"
  }
 }
}
```
