# Phase 357: the dry-run diff for the live migration

- **Written:** `2026-09-28T14:47:54`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre357_20260928_144754.db`
- **Backup sha256:** `316eb0e0de0b4e035e0195a94fe73d326c7f8a3e189bfad9fc1e21f5e7c33c6c`
- **Scope sha256:** `6f7b716182c282e2243fecb3461c7e69a44a687e604acb8392b2a0798f44494c`
- **Migrations applied on the copy:** `[73]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema added: index idx_workflow_run_items_item

```sql
CREATE INDEX idx_workflow_run_items_item
                ON workflow_run_items(checklist_item_id)
```

## schema added: index idx_workflow_runs_vehicle

```sql
CREATE INDEX idx_workflow_runs_vehicle
                ON workflow_runs(vehicle_id, started_at)
```

## schema added: index idx_workflow_runs_work_order

```sql
CREATE INDEX idx_workflow_runs_work_order
                ON workflow_runs(work_order_id)
```

## schema added: table workflow_run_items

```sql
CREATE TABLE workflow_run_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                checklist_item_id INTEGER,
                sequence_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                required INTEGER NOT NULL,
                result TEXT CHECK (result IN ('pass', 'fail', 'skipped')),
                diagnosis TEXT,
                notes TEXT,
                answered_at TIMESTAMP,
                UNIQUE (run_id, sequence_number),
                CHECK ((result IS NULL) = (answered_at IS NULL)),
                CHECK (result IS NOT 'skipped' OR required = 0),
                CHECK (diagnosis IS NULL OR result = 'fail'),
                FOREIGN KEY (run_id)
                    REFERENCES workflow_runs(id) ON DELETE CASCADE,
                FOREIGN KEY (checklist_item_id)
                    REFERENCES checklist_items(id) ON DELETE SET NULL
            )
```

## schema added: table workflow_runs

```sql
CREATE TABLE workflow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                work_order_id INTEGER,
                powertrain TEXT NOT NULL
                    CHECK (powertrain IN ('ice', 'electric', 'hybrid')),
                status TEXT NOT NULL DEFAULT 'in_progress'
                    CHECK (status IN ('in_progress', 'complete')),
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                CHECK ((status = 'complete') = (finished_at IS NOT NULL)),
                FOREIGN KEY (template_id)
                    REFERENCES workflow_templates(id) ON DELETE RESTRICT,
                FOREIGN KEY (vehicle_id)
                    REFERENCES vehicles(id) ON DELETE RESTRICT,
                FOREIGN KEY (work_order_id)
                    REFERENCES work_orders(id) ON DELETE SET NULL
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 72: (73, '2026-09-28 18:47:54')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "72": {
     "applied_at": "<clock>",
     "version": 73
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_workflow_run_items_item",
   "index idx_workflow_runs_vehicle",
   "index idx_workflow_runs_work_order",
   "table workflow_run_items",
   "table workflow_runs"
  ],
  "changed": [],
  "removed": [],
  "sql": {
   "index idx_workflow_run_items_item": "CREATE INDEX idx_workflow_run_items_item\n                ON workflow_run_items(checklist_item_id)",
   "index idx_workflow_runs_vehicle": "CREATE INDEX idx_workflow_runs_vehicle\n                ON workflow_runs(vehicle_id, started_at)",
   "index idx_workflow_runs_work_order": "CREATE INDEX idx_workflow_runs_work_order\n                ON workflow_runs(work_order_id)",
   "table workflow_run_items": "CREATE TABLE workflow_run_items (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                run_id INTEGER NOT NULL,\n                checklist_item_id INTEGER,\n                sequence_number INTEGER NOT NULL,\n                title TEXT NOT NULL,\n                required INTEGER NOT NULL,\n                result TEXT CHECK (result IN ('pass', 'fail', 'skipped')),\n                diagnosis TEXT,\n                notes TEXT,\n                answered_at TIMESTAMP,\n                UNIQUE (run_id, sequence_number),\n                CHECK ((result IS NULL) = (answered_at IS NULL)),\n                CHECK (result IS NOT 'skipped' OR required = 0),\n                CHECK (diagnosis IS NULL OR result = 'fail'),\n                FOREIGN KEY (run_id)\n                    REFERENCES workflow_runs(id) ON DELETE CASCADE,\n                FOREIGN KEY (checklist_item_id)\n                    REFERENCES checklist_items(id) ON DELETE SET NULL\n            )",
   "table workflow_runs": "CREATE TABLE workflow_runs (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                template_id INTEGER NOT NULL,\n                vehicle_id INTEGER NOT NULL,\n                work_order_id INTEGER,\n                powertrain TEXT NOT NULL\n                    CHECK (powertrain IN ('ice', 'electric', 'hybrid')),\n                status TEXT NOT NULL DEFAULT 'in_progress'\n                    CHECK (status IN ('in_progress', 'complete')),\n                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n                finished_at TIMESTAMP,\n                CHECK ((status = 'complete') = (finished_at IS NOT NULL)),\n                FOREIGN KEY (template_id)\n                    REFERENCES workflow_templates(id) ON DELETE RESTRICT,\n                FOREIGN KEY (vehicle_id)\n                    REFERENCES vehicles(id) ON DELETE RESTRICT,\n                FOREIGN KEY (work_order_id)\n                    REFERENCES work_orders(id) ON DELETE SET NULL\n            )"
  }
 }
}
```
