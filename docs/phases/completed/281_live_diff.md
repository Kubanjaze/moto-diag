# Phase 281: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

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
- added rowid 77: (78, '2026-10-01 17:26:35')
## tax_jurisdictions: +1 added, 0 changed, 0 removed
- added rowid 1: (1, 'US-MA', 'Massachusetts')
## tax_line_rules: +3 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)
- added rowid 2: (2, 1, None)
- added rowid 3: (3, 1, None)
## tax_rates: +1 added, 0 changed, 0 removed
- added rowid 1: (1, 1, None)
