# Phase 293: the dry-run diff for the live migration

- **Written:** `2026-11-23T22:05:45`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre293_20261123_220543.db`
- **Backup sha256:** `38d9866a56259c77f1f9b32b7892f6ae61652f77121b30e37616a022a0e3c391`
- **Scope sha256:** `9a849ebbcffa7b0746a984cdcc347d845650c6c9c4029359efb959ef5bca4827`
- **Migrations applied on the copy:** `[92]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
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
- added rowid 91: (92, '2026-11-24 03:05:44')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "manual_pages_fts_config": {
   "added": {
    "version": {
     "k": "version",
     "v": 4
    }
   },
   "changed": {},
   "removed": {}
  },
  "manual_pages_fts_data": {
   "added": {
    "1": {
     "block": "x''",
     "id": 1
    },
    "10": {
     "block": "x'00000000000000'",
     "id": 10
    }
   },
   "changed": {},
   "removed": {}
  },
  "schema_version": {
   "added": {
    "91": {
     "applied_at": "<clock>",
     "version": 92
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_manual_pages_manual_page",
   "index idx_manuals_shop_sha",
   "index idx_manuals_shop_status",
   "table manual_pages",
   "table manual_pages_fts",
   "table manual_pages_fts_config",
   "table manual_pages_fts_data",
   "table manual_pages_fts_docsize",
   "table manual_pages_fts_idx",
   "table manual_reviewers",
   "trigger manual_pages_ad",
   "trigger manual_pages_ai",
   "trigger manual_pages_au"
  ],
  "changed": [
   "table manual_references"
  ],
  "removed": [],
  "sql": {
   "index idx_manual_pages_manual_page": "CREATE UNIQUE INDEX idx_manual_pages_manual_page\n                ON manual_pages(manual_id, page_number)",
   "index idx_manuals_shop_sha": "CREATE INDEX idx_manuals_shop_sha\n                ON manual_references(shop_id, file_sha256)",
   "index idx_manuals_shop_status": "CREATE INDEX idx_manuals_shop_status\n                ON manual_references(shop_id, status)",
   "table manual_pages": "CREATE TABLE manual_pages (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                manual_id INTEGER NOT NULL\n                    REFERENCES manual_references(id) ON DELETE CASCADE,\n                page_number INTEGER NOT NULL,\n                image_path TEXT NOT NULL,\n                thumb_path TEXT NOT NULL,\n                text TEXT NOT NULL DEFAULT '',\n                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP\n            )",
   "table manual_pages_fts": "CREATE VIRTUAL TABLE manual_pages_fts USING fts5(\n                text,\n                manual_id UNINDEXED,\n                page_number UNINDEXED,\n                content='manual_pages',\n                content_rowid='id'\n            )",
   "table manual_pages_fts_config": "CREATE TABLE 'manual_pages_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID",
   "table manual_pages_fts_data": "CREATE TABLE 'manual_pages_fts_data'(id INTEGER PRIMARY KEY, block BLOB)",
   "table manual_pages_fts_docsize": "CREATE TABLE 'manual_pages_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB)",
   "table manual_pages_fts_idx": "CREATE TABLE 'manual_pages_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID",
   "table manual_references": "CREATE TABLE manual_references (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                source TEXT NOT NULL,\n                title TEXT NOT NULL,\n                publisher TEXT,\n                isbn TEXT,\n                make TEXT,\n                model TEXT,\n                year_start INTEGER,\n                year_end INTEGER,\n                page_count INTEGER,\n                section_titles TEXT NOT NULL DEFAULT '[]',\n                url TEXT,\n                notes TEXT,\n                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n            , shop_id INTEGER REFERENCES shops(id), file_path TEXT, file_sha256 TEXT, file_size_bytes INTEGER, uploaded_by_user_id INTEGER\n                REFERENCES users(id), kind TEXT\n                CHECK (kind IS NULL\n                       OR kind IN ('service_manual', 'parts_catalog', 'wiring', 'other')), status TEXT NOT NULL\n                DEFAULT 'pending_review'\n                CHECK (status IN ('pending_review', 'approved', 'rejected', 'taken_down')), reviewed_by_user_id INTEGER\n                REFERENCES users(id), reviewed_at TEXT, review_reason TEXT, rendered_pages INTEGER NOT NULL DEFAULT 0, render_error TEXT)",
   "table manual_reviewers": "CREATE TABLE manual_reviewers (\n                user_id INTEGER PRIMARY KEY REFERENCES users(id),\n                granted_at TEXT NOT NULL,\n                granted_by_user_id INTEGER REFERENCES users(id)\n            )",
   "trigger manual_pages_ad": "CREATE TRIGGER manual_pages_ad AFTER DELETE ON manual_pages BEGIN\n                INSERT INTO manual_pages_fts(manual_pages_fts, rowid, text, manual_id, page_number)\n                VALUES ('delete', old.id, old.text, old.manual_id, old.page_number);\n            END",
   "trigger manual_pages_ai": "CREATE TRIGGER manual_pages_ai AFTER INSERT ON manual_pages BEGIN\n                INSERT INTO manual_pages_fts(rowid, text, manual_id, page_number)\n                VALUES (new.id, new.text, new.manual_id, new.page_number);\n            END",
   "trigger manual_pages_au": "CREATE TRIGGER manual_pages_au AFTER UPDATE ON manual_pages BEGIN\n                INSERT INTO manual_pages_fts(manual_pages_fts, rowid, text, manual_id, page_number)\n                VALUES ('delete', old.id, old.text, old.manual_id, old.page_number);\n                INSERT INTO manual_pages_fts(rowid, text, manual_id, page_number)\n                VALUES (new.id, new.text, new.manual_id, new.page_number);\n            END"
  }
 }
}
```
