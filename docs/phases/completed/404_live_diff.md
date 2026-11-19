# Phase 404: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **Set aside, written by the running API:** `0` (`none`)
- **F158 census on live:** `41`

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
- added rowid 89: (90, '2026-11-19 03:10:02')
