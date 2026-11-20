# Phase 334: the dry-run diff for the live migration

- **Written:** `2026-11-20T00:22:21`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre334_20261120_002219.db`
- **Backup sha256:** `a610be36fe58a78b1e9a9578ff6b692e364cd3083319808112dd808c54a00db1`
- **Scope sha256:** `0cfb039d6d321eac4c551f697c287123b5a70ac3efe4f974f6bc4232c56170e0`
- **Migrations applied on the copy:** `[91]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
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
- added rowid 90: (91, '2026-11-20 05:22:20')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "90": {
     "applied_at": "<clock>",
     "version": 91
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_terms_acceptances_user_version",
   "table terms_acceptances"
  ],
  "changed": [],
  "removed": [],
  "sql": {
   "index idx_terms_acceptances_user_version": "CREATE UNIQUE INDEX idx_terms_acceptances_user_version\n                ON terms_acceptances(user_id, version)",
   "table terms_acceptances": "CREATE TABLE terms_acceptances (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                user_id INTEGER NOT NULL REFERENCES users(id),\n                version TEXT NOT NULL,\n                accepted_at TEXT NOT NULL\n            )"
  }
 }
}
```
