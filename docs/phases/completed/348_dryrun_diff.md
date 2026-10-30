# Phase 348: the dry-run diff for the live migration

- **Written:** `2026-10-30T12:12:19`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre348_20261030_121217.db`
- **Backup sha256:** `bf1cfa66f1743113339a3fd9a68b989fa446d9a0a081bd8f42ce45f35b4667d2`
- **Scope sha256:** `629e2ff485da2a8f9806825ade5883c3e076bfc7f0b3e00c422cbf4acf2bf439`
- **Migrations applied on the copy:** `[88]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema added: index idx_audit_events_shop

```sql
CREATE INDEX idx_audit_events_shop
                ON audit_events(shop_id, id)
```

## schema added: table audit_events

```sql
CREATE TABLE audit_events (
                id INTEGER PRIMARY KEY,
                occurred_at TEXT NOT NULL,
                request_id TEXT,
                actor_user_id INTEGER,
                actor_username TEXT,
                credential_kind TEXT,
                credential_id INTEGER,
                client_address TEXT,
                forwarded_for TEXT,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                endpoint TEXT,
                path_params TEXT,
                shop_id INTEGER,
                status INTEGER NOT NULL,
                prev_hash TEXT NOT NULL,
                row_hash TEXT NOT NULL
            )
```

## schema added: trigger audit_events_no_delete

```sql
CREATE TRIGGER audit_events_no_delete
                BEFORE DELETE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END
```

## schema added: trigger audit_events_no_update

```sql
CREATE TRIGGER audit_events_no_update
                BEFORE UPDATE ON audit_events
                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 87: (88, '2026-10-30 16:12:19')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "87": {
     "applied_at": "<clock>",
     "version": 88
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_audit_events_shop",
   "table audit_events",
   "trigger audit_events_no_delete",
   "trigger audit_events_no_update"
  ],
  "changed": [],
  "removed": [],
  "sql": {
   "index idx_audit_events_shop": "CREATE INDEX idx_audit_events_shop\n                ON audit_events(shop_id, id)",
   "table audit_events": "CREATE TABLE audit_events (\n                id INTEGER PRIMARY KEY,\n                occurred_at TEXT NOT NULL,\n                request_id TEXT,\n                actor_user_id INTEGER,\n                actor_username TEXT,\n                credential_kind TEXT,\n                credential_id INTEGER,\n                client_address TEXT,\n                forwarded_for TEXT,\n                method TEXT NOT NULL,\n                path TEXT NOT NULL,\n                endpoint TEXT,\n                path_params TEXT,\n                shop_id INTEGER,\n                status INTEGER NOT NULL,\n                prev_hash TEXT NOT NULL,\n                row_hash TEXT NOT NULL\n            )",
   "trigger audit_events_no_delete": "CREATE TRIGGER audit_events_no_delete\n                BEFORE DELETE ON audit_events\n                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END",
   "trigger audit_events_no_update": "CREATE TRIGGER audit_events_no_update\n                BEFORE UPDATE ON audit_events\n                BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END"
  }
 }
}
```
