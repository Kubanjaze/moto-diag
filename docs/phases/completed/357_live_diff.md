# Phase 357: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

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
- added rowid 72: (73, '2026-09-28 18:49:34')
