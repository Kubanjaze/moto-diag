# Phase 293: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **Set aside, written by the running API:** `0` (`none`)
- **Other differences, listed:** `1` (`stripe_event_cursors +0 ~1 -0`)
- **F158 census on live:** `41`

## schema added: index idx_manual_pages_manual_page

```sql
CREATE UNIQUE INDEX idx_manual_pages_manual_page
                ON manual_pages(manual_id, page_number)
```

## schema added: index idx_manuals_shop_sha

```sql
CREATE INDEX idx_manuals_shop_sha
                ON manual_references(shop_id, file_sha256)
```

## schema added: index idx_manuals_shop_status

```sql
CREATE INDEX idx_manuals_shop_status
                ON manual_references(shop_id, status)
```

## schema added: table manual_pages

```sql
CREATE TABLE manual_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manual_id INTEGER NOT NULL
                    REFERENCES manual_references(id) ON DELETE CASCADE,
                page_number INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                thumb_path TEXT NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
```

## schema added: table manual_pages_fts

```sql
CREATE VIRTUAL TABLE manual_pages_fts USING fts5(
                text,
                manual_id UNINDEXED,
                page_number UNINDEXED,
                content='manual_pages',
                content_rowid='id'
            )
```

## schema added: table manual_pages_fts_config

```sql
CREATE TABLE 'manual_pages_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID
```

## schema added: table manual_pages_fts_data

```sql
CREATE TABLE 'manual_pages_fts_data'(id INTEGER PRIMARY KEY, block BLOB)
```

## schema added: table manual_pages_fts_docsize

```sql
CREATE TABLE 'manual_pages_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB)
```

## schema added: table manual_pages_fts_idx

```sql
CREATE TABLE 'manual_pages_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID
```

## schema added: table manual_reviewers

```sql
CREATE TABLE manual_reviewers (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                granted_at TEXT NOT NULL,
                granted_by_user_id INTEGER REFERENCES users(id)
            )
```

## schema added: trigger manual_pages_ad

```sql
CREATE TRIGGER manual_pages_ad AFTER DELETE ON manual_pages BEGIN
                INSERT INTO manual_pages_fts(manual_pages_fts, rowid, text, manual_id, page_number)
                VALUES ('delete', old.id, old.text, old.manual_id, old.page_number);
            END
```

## schema added: trigger manual_pages_ai

```sql
CREATE TRIGGER manual_pages_ai AFTER INSERT ON manual_pages BEGIN
                INSERT INTO manual_pages_fts(rowid, text, manual_id, page_number)
                VALUES (new.id, new.text, new.manual_id, new.page_number);
            END
```

## schema added: trigger manual_pages_au

```sql
CREATE TRIGGER manual_pages_au AFTER UPDATE ON manual_pages BEGIN
                INSERT INTO manual_pages_fts(manual_pages_fts, rowid, text, manual_id, page_number)
                VALUES ('delete', old.id, old.text, old.manual_id, old.page_number);
                INSERT INTO manual_pages_fts(rowid, text, manual_id, page_number)
                VALUES (new.id, new.text, new.manual_id, new.page_number);
            END
```

## schema changed: table manual_references

```sql
CREATE TABLE manual_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                publisher TEXT,
                isbn TEXT,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                page_count INTEGER,
                section_titles TEXT NOT NULL DEFAULT '[]',
                url TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            , shop_id INTEGER REFERENCES shops(id), file_path TEXT, file_sha256 TEXT, file_size_bytes INTEGER, uploaded_by_user_id INTEGER
                REFERENCES users(id), kind TEXT
                CHECK (kind IS NULL
                       OR kind IN ('service_manual', 'parts_catalog', 'wiring', 'other')), status TEXT NOT NULL
                DEFAULT 'pending_review'
                CHECK (status IN ('pending_review', 'approved', 'rejected', 'taken_down')), reviewed_by_user_id INTEGER
                REFERENCES users(id), reviewed_at TEXT, review_reason TEXT, rendered_pages INTEGER NOT NULL DEFAULT 0, render_error TEXT)
```

## manual_pages_fts_config: +1 added, 0 changed, 0 removed
- added rowid version: ('version', 4)
## manual_pages_fts_data: +2 added, 0 changed, 0 removed
- added rowid 1: (1, b'')
- added rowid 10: (10, b'\x00\x00\x00\x00\x00\x00\x00')
## schema_version: +1 added, 0 changed, 0 removed
- added rowid 91: (92, '2026-11-24 03:06:00')
## stripe_event_cursors: +0 added, 1 changed, 0 removed

### stripe_event_cursors rowid 1

**polled_at**

- before: 2026-11-24T03:05:29.874+00:00
- after:  2026-11-24T03:05:50.124+00:00
