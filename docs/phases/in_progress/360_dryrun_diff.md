# Phase 360: the dry-run diff for the live migration

- **Written:** `2026-09-29T11:16:43`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre360_20260929_111643.db`
- **Backup sha256:** `887c2aff4cb19554e1bd7be46bebf8dc128a11ef827b44881d23bd6d7f498691`
- **Scope sha256:** `f0cd58bb20a73f8faf7a26e1ef6e0213f2c8849f62ba4675dcb8221b5ae4cfaf`
- **Migrations applied on the copy:** `[74]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema changed: table vehicles

```sql
CREATE TABLE "vehicles" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER NOT NULL,
                engine_cc INTEGER,
                vin TEXT,
                protocol TEXT NOT NULL DEFAULT 'none',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                powertrain TEXT,
                engine_type TEXT DEFAULT 'four_stroke',
                battery_chemistry TEXT,
                motor_kw REAL,
                bms_present INTEGER DEFAULT 0,
                customer_id INTEGER DEFAULT 1,
                mileage INTEGER,
                owner_user_id INTEGER NOT NULL DEFAULT 1,
                transmission TEXT
                CHECK (transmission IS NULL OR transmission IN (
                    'manual', 'cvt', 'dct', 'semi_auto_centrifugal',
                    'semi_auto_actuated', 'direct_drive'
                ))
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 73: (74, '2026-09-29 15:16:43')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "73": {
     "applied_at": "<clock>",
     "version": 74
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [],
  "changed": [
   "table vehicles"
  ],
  "removed": [],
  "sql": {
   "table vehicles": "CREATE TABLE \"vehicles\" (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                make TEXT NOT NULL,\n                model TEXT NOT NULL,\n                year INTEGER NOT NULL,\n                engine_cc INTEGER,\n                vin TEXT,\n                protocol TEXT NOT NULL DEFAULT 'none',\n                notes TEXT,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                updated_at TIMESTAMP,\n                powertrain TEXT,\n                engine_type TEXT DEFAULT 'four_stroke',\n                battery_chemistry TEXT,\n                motor_kw REAL,\n                bms_present INTEGER DEFAULT 0,\n                customer_id INTEGER DEFAULT 1,\n                mileage INTEGER,\n                owner_user_id INTEGER NOT NULL DEFAULT 1,\n                transmission TEXT\n                CHECK (transmission IS NULL OR transmission IN (\n                    'manual', 'cvt', 'dct', 'semi_auto_centrifugal',\n                    'semi_auto_actuated', 'direct_drive'\n                ))\n            )"
  }
 }
}
```
