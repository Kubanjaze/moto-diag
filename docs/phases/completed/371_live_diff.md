# Phase 371: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **Set aside, written by the running API:** `0` (`none`)
- **F158 census on live:** `41`

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
- added rowid 88: (89, '2026-11-08 23:58:27')
