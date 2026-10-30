# Phase 348: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **Set aside, written by the running API:** `0` (`none`)
- **F158 census on live:** `41`

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
- added rowid 87: (88, '2026-10-30 16:12:25')
