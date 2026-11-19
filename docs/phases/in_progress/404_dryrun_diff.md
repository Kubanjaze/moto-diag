# Phase 404: the dry-run diff for the live migration

- **Written:** `2026-11-18T22:09:57`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre404_20261118_220955.db`
- **Backup sha256:** `8354a42edb398b15d5a52b0eb9664a973d5e0164b239d9b3afda7be4c1950a6a`
- **Scope sha256:** `6bca455ef683c4d8f8143c6cbd765ae3421dfc19c0871f7f87ba5205cadb63c7`
- **Migrations applied on the copy:** `[90]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema added: index idx_stripe_feed_checkins_sent_at

```sql
CREATE INDEX idx_stripe_feed_checkins_sent_at
                ON stripe_feed_checkins(sent_at)
```

## schema added: table stripe_feed_checkins

```sql
CREATE TABLE stripe_feed_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_at TEXT NOT NULL,
                ok INTEGER NOT NULL CHECK (ok IN (0, 1)),
                answer TEXT NOT NULL,
                slug TEXT NOT NULL
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 89: (90, '2026-11-19 03:09:56')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "89": {
     "applied_at": "<clock>",
     "version": 90
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_stripe_feed_checkins_sent_at",
   "table stripe_feed_checkins"
  ],
  "changed": [],
  "removed": [],
  "sql": {
   "index idx_stripe_feed_checkins_sent_at": "CREATE INDEX idx_stripe_feed_checkins_sent_at\n                ON stripe_feed_checkins(sent_at)",
   "table stripe_feed_checkins": "CREATE TABLE stripe_feed_checkins (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                sent_at TEXT NOT NULL,\n                ok INTEGER NOT NULL CHECK (ok IN (0, 1)),\n                answer TEXT NOT NULL,\n                slug TEXT NOT NULL\n            )"
  }
 }
}
```
