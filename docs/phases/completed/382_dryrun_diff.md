# Phase 382: the dry-run diff for the live migration

- **Written:** `2026-10-19T14:56:02`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre382_20261019_145601.db`
- **Backup sha256:** `07e8fcc7cd4c8b91653f9f8e459d752a05dd566cac425b548640f06be77c19db`
- **Scope sha256:** `75f88f449f0ceac9e3ce329f77d8871e79b22b9bec400ba35629a4d2dac45ddb`
- **Migrations applied on the copy:** `[]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## videos: +0 added, 6 changed, 0 removed

### videos rowid 1

**file_path**

- before: /Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_1/1.mp4
- after:  /home/lilcu/motodiag/live/videos/shop_1/session_1/1.mp4

### videos rowid 2

**file_path**

- before: /Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_4/2.mp4
- after:  /home/lilcu/motodiag/live/videos/shop_1/session_4/2.mp4

### videos rowid 3

**file_path**

- before: /Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_4/3.mp4
- after:  /home/lilcu/motodiag/live/videos/shop_1/session_4/3.mp4

### videos rowid 4

**file_path**

- before: /Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_1/4.mp4
- after:  /home/lilcu/motodiag/live/videos/shop_1/session_1/4.mp4

### videos rowid 5

**file_path**

- before: /Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_6/5.mp4
- after:  /home/lilcu/motodiag/live/videos/shop_1/session_6/5.mp4

### videos rowid 6

**file_path**

- before: /Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_6/6.mp4
- after:  /home/lilcu/motodiag/live/videos/shop_1/session_6/6.mp4

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "videos": {
   "added": {},
   "changed": {
    "1": {
     "file_path": [
      "/Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_1/1.mp4",
      "/home/lilcu/motodiag/live/videos/shop_1/session_1/1.mp4"
     ]
    },
    "2": {
     "file_path": [
      "/Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_4/2.mp4",
      "/home/lilcu/motodiag/live/videos/shop_1/session_4/2.mp4"
     ]
    },
    "3": {
     "file_path": [
      "/Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_4/3.mp4",
      "/home/lilcu/motodiag/live/videos/shop_1/session_4/3.mp4"
     ]
    },
    "4": {
     "file_path": [
      "/Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_1/4.mp4",
      "/home/lilcu/motodiag/live/videos/shop_1/session_1/4.mp4"
     ]
    },
    "5": {
     "file_path": [
      "/Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_6/5.mp4",
      "/home/lilcu/motodiag/live/videos/shop_1/session_6/5.mp4"
     ]
    },
    "6": {
     "file_path": [
      "/Users/lilquant/Projects/moto-diag/data/videos/shop_1/session_6/6.mp4",
      "/home/lilcu/motodiag/live/videos/shop_1/session_6/6.mp4"
     ]
    }
   },
   "removed": {}
  }
 },
 "schema": {
  "added": [],
  "changed": [],
  "removed": [],
  "sql": {}
 }
}
```
