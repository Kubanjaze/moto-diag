# Phase 329: the dry-run diff for the live migration

- **Written:** `2026-11-27T16:30:25`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre329_20261127_163023.db`
- **Backup sha256:** `c9f40438a23cda7cd2a13a8cd3cbc156ba6a78f77bfdfb6ea449067a677e936f`
- **Scope sha256:** `a89feb689d4557cc3bec968641beb3a9bfc01f832d74a1d2023eb936a5804677`
- **Migrations applied on the copy:** `[93]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema added: index idx_one_time_codes_hash

```sql
CREATE UNIQUE INDEX idx_one_time_codes_hash
                ON one_time_codes(code_hash)
```

## schema added: index idx_one_time_codes_subject

```sql
CREATE INDEX idx_one_time_codes_subject
                ON one_time_codes(purpose, subject)
```

## schema added: index idx_signups_username

```sql
CREATE INDEX idx_signups_username ON signups(username)
```

## schema added: table one_time_codes

```sql
CREATE TABLE one_time_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purpose TEXT NOT NULL
                    CHECK (purpose IN ('verify_email', 'reset_password')),
                subject TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                issued_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                used_at REAL
            )
```

## schema added: table signups

```sql
CREATE TABLE signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                shop_name TEXT,
                tier TEXT NOT NULL CHECK (tier IN ('individual', 'shop', 'company')),
                terms_version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending_email'
                    CHECK (status IN ('pending_email', 'email_verified', 'completed')),
                created_at TEXT NOT NULL,
                verified_at TEXT,
                completed_at TEXT,
                stripe_subscription_id TEXT,
                stripe_checkout_session_id TEXT,
                user_id INTEGER REFERENCES users(id),
                shop_id INTEGER REFERENCES shops(id),
                CHECK ((tier = 'individual') = (shop_name IS NULL))
            )
```

## schema_version: +1 added, 0 changed, 0 removed
- added rowid 92: (93, '2026-11-27 21:30:24')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "92": {
     "applied_at": "<clock>",
     "version": 93
    }
   },
   "changed": {},
   "removed": {}
  }
 },
 "schema": {
  "added": [
   "index idx_one_time_codes_hash",
   "index idx_one_time_codes_subject",
   "index idx_signups_username",
   "table one_time_codes",
   "table signups"
  ],
  "changed": [],
  "removed": [],
  "sql": {
   "index idx_one_time_codes_hash": "CREATE UNIQUE INDEX idx_one_time_codes_hash\n                ON one_time_codes(code_hash)",
   "index idx_one_time_codes_subject": "CREATE INDEX idx_one_time_codes_subject\n                ON one_time_codes(purpose, subject)",
   "index idx_signups_username": "CREATE INDEX idx_signups_username ON signups(username)",
   "table one_time_codes": "CREATE TABLE one_time_codes (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                purpose TEXT NOT NULL\n                    CHECK (purpose IN ('verify_email', 'reset_password')),\n                subject TEXT NOT NULL,\n                code_hash TEXT NOT NULL,\n                issued_at REAL NOT NULL,\n                expires_at REAL NOT NULL,\n                used_at REAL\n            )",
   "table signups": "CREATE TABLE signups (\n                id INTEGER PRIMARY KEY AUTOINCREMENT,\n                email TEXT NOT NULL,\n                owner_name TEXT NOT NULL,\n                username TEXT NOT NULL,\n                password_hash TEXT NOT NULL,\n                shop_name TEXT,\n                tier TEXT NOT NULL CHECK (tier IN ('individual', 'shop', 'company')),\n                terms_version TEXT NOT NULL,\n                status TEXT NOT NULL DEFAULT 'pending_email'\n                    CHECK (status IN ('pending_email', 'email_verified', 'completed')),\n                created_at TEXT NOT NULL,\n                verified_at TEXT,\n                completed_at TEXT,\n                stripe_subscription_id TEXT,\n                stripe_checkout_session_id TEXT,\n                user_id INTEGER REFERENCES users(id),\n                shop_id INTEGER REFERENCES shops(id),\n                CHECK ((tier = 'individual') = (shop_name IS NULL))\n            )"
  }
 }
}
```
