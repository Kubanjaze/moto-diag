# Phase 383: the dry-run diff for the live migration

- **Written:** `2026-10-19T21:25:35`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre383_20261019_212534.db`
- **Backup sha256:** `a18a2f9378c934d8dd1ffc94fc7d9f1af3cb241720e9142eb77db487d3a8c577`
- **Scope sha256:** `de7f0eb5b38ff0abfefccc3bf0630dd846543b8e17acae8ce791c23fa35ef5a5`
- **Migrations applied on the copy:** `[87]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## schema_version: +1 added, 0 changed, 0 removed
- added rowid 86: (87, '2026-10-20 01:25:35')
## videos: +0 added, 6 changed, 0 removed

### videos rowid 1

**file_path**

- before: /home/lilcu/motodiag/live/videos/shop_1/session_1/1.mp4
- after:  videos/shop_1/session_1/1.mp4

### videos rowid 2

**file_path**

- before: /home/lilcu/motodiag/live/videos/shop_1/session_4/2.mp4
- after:  videos/shop_1/session_4/2.mp4

### videos rowid 3

**file_path**

- before: /home/lilcu/motodiag/live/videos/shop_1/session_4/3.mp4
- after:  videos/shop_1/session_4/3.mp4

### videos rowid 4

**file_path**

- before: /home/lilcu/motodiag/live/videos/shop_1/session_1/4.mp4
- after:  videos/shop_1/session_1/4.mp4

### videos rowid 5

**file_path**

- before: /home/lilcu/motodiag/live/videos/shop_1/session_6/5.mp4
- after:  videos/shop_1/session_6/5.mp4

### videos rowid 6

**file_path**

- before: /home/lilcu/motodiag/live/videos/shop_1/session_6/6.mp4
- after:  videos/shop_1/session_6/6.mp4

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "schema_version": {
   "added": {
    "86": {
     "applied_at": "<clock>",
     "version": 87
    }
   },
   "changed": {},
   "removed": {}
  },
  "videos": {
   "added": {},
   "changed": {
    "1": {
     "file_path": [
      "/home/lilcu/motodiag/live/videos/shop_1/session_1/1.mp4",
      "videos/shop_1/session_1/1.mp4"
     ]
    },
    "2": {
     "file_path": [
      "/home/lilcu/motodiag/live/videos/shop_1/session_4/2.mp4",
      "videos/shop_1/session_4/2.mp4"
     ]
    },
    "3": {
     "file_path": [
      "/home/lilcu/motodiag/live/videos/shop_1/session_4/3.mp4",
      "videos/shop_1/session_4/3.mp4"
     ]
    },
    "4": {
     "file_path": [
      "/home/lilcu/motodiag/live/videos/shop_1/session_1/4.mp4",
      "videos/shop_1/session_1/4.mp4"
     ]
    },
    "5": {
     "file_path": [
      "/home/lilcu/motodiag/live/videos/shop_1/session_6/5.mp4",
      "videos/shop_1/session_6/5.mp4"
     ]
    },
    "6": {
     "file_path": [
      "/home/lilcu/motodiag/live/videos/shop_1/session_6/6.mp4",
      "videos/shop_1/session_6/6.mp4"
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
