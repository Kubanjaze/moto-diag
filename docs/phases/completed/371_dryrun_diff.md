# Phase 371: the dry-run diff for the live migration

- **Written:** `2026-11-08T18:58:08`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre371_20261108_185806.db`
- **Backup sha256:** `fdb96525b4a3bcfc5bca9516701965a45e92c30eb1effa209178682dbd6d7520`
- **Scope sha256:** `a09d4575e6613ffeec9a2ca4ed51840033f84aceb738a4668d10fab1c723843e`
- **Migrations applied on the copy:** `[89]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema added: index idx_stripe_feed_notices_line

```sql
CREATE INDEX idx_stripe_feed_notices_line
                ON stripe_feed_notices(line, sent_at)
```

## schema added: table stripe_event_cursors

```sql
CREATE TABLE stripe_event_cursors (
                account TEXT PRIMARY KEY,
                last_created INTEGER NOT NULL,
                last_event_id TEXT,
                polled_at TEXT NOT NULL,
                last_error TEXT,
                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1))
            )
```

## schema added: table stripe_feed_notices

```sql
CREATE TABLE stripe_feed_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                line TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                detail TEXT,
                delivered INTEGER NOT NULL CHECK (delivered IN (0, 1))
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 88: (89, '2026-11-08 23:58:08')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "88": {
     "applied_at": "<clock>",
     "version": 89
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_stripe_feed_notices_line",
   "table stripe_event_cursors",
   "table stripe_feed_notices"
  ],
  "changed": [],
  "removed": [],
  "sql": {
   "index idx_stripe_feed_notices_line": "CREATE INDEX idx_stripe_feed_notices_line\n                ON stripe_feed_notices(line, sent_at)",
   "table stripe_event_cursors": "CREATE TABLE stripe_event_cursors (\n                account TEXT PRIMARY KEY,\n                last_created INTEGER NOT NULL,\n                last_event_id TEXT,\n                polled_at TEXT NOT NULL,\n                last_error TEXT,\n                livemode INTEGER NOT NULL DEFAULT 0 CHECK (livemode IN (0, 1))\n            )",
   "table stripe_feed_notices": "CREATE TABLE stripe_feed_notices (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                line TEXT NOT NULL,\n                sent_at TEXT NOT NULL,\n                detail TEXT,\n                delivered INTEGER NOT NULL CHECK (delivered IN (0, 1))\n            )"
  }
 }
}
```
