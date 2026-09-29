# Phase 360: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

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
- added rowid 73: (74, '2026-09-29 15:19:32')
