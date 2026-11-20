# Phase 334: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **Set aside, written by the running API:** `0` (`none`)
- **F158 census on live:** `41`

## schema added: index idx_terms_acceptances_user_version

```sql
CREATE UNIQUE INDEX idx_terms_acceptances_user_version
                ON terms_acceptances(user_id, version)
```

## schema added: table terms_acceptances

```sql
CREATE TABLE terms_acceptances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                version TEXT NOT NULL,
                accepted_at TEXT NOT NULL
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 90: (91, '2026-11-20 05:22:25')
