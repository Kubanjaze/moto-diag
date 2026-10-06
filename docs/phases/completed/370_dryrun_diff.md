# Phase 370: the dry-run diff for the live migration

- **Written:** `2026-10-06T11:04:34`
- **Backup:** `/Users/lilquant/backups/motodiag/motodiag_pre370_20261006_110434.db`
- **Backup sha256:** `dbc4aaf913044788c1a5671ec69a969ca7ce93b5cdbb36400011ab226e3a4e0e`
- **Scope sha256:** `44bbd6430eb64376fede19840d54da340dace6d8c7a3556ae26de04018580354`
- **Migrations applied on the copy:** `[79]`
- **F158 census on the copy:** `36`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->
## diagnostic_sessions: +0 added, 7 changed, 0 removed

### diagnostic_sessions rowid 1

**created_at**

- before: 2026-06-13T00:04:48.958638
- after:  2026-06-13T04:04:48.958+00:00

### diagnostic_sessions rowid 2

**created_at**

- before: 2026-09-02T14:49:39.104923
- after:  2026-09-02T18:49:39.104+00:00

### diagnostic_sessions rowid 3

**created_at**

- before: 2026-09-02T14:56:57.713399
- after:  2026-09-02T18:56:57.713+00:00

### diagnostic_sessions rowid 4

**created_at**

- before: 2026-09-07T09:09:00.130231
- after:  2026-09-07T13:09:00.130+00:00

### diagnostic_sessions rowid 5

**created_at**

- before: 2026-09-07 17:27:55
- after:  2026-09-07T17:27:55.000+00:00

### diagnostic_sessions rowid 6

**created_at**

- before: 2026-09-09T19:50:41.005067
- after:  2026-09-09T23:50:41.005+00:00

**updated_at**

- before: 2026-09-09T19:54:06.795174
- after:  2026-09-09T23:54:06.795+00:00

### diagnostic_sessions rowid 11

**created_at**

- before: 2026-09-17T15:22:14.228127
- after:  2026-09-17T19:22:14.228+00:00

**updated_at**

- before: 2026-09-17T15:22:35.263866
- after:  2026-09-17T19:22:35.263+00:00

**closed_at**

- before: 2026-09-17T15:22:35.263866
- after:  2026-09-17T19:22:35.263+00:00
## schema_version: +1 added, 0 changed, 0 removed
- added rowid 78: (79, '2026-10-06 15:04:34')

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {
  "diagnostic_sessions": {
   "added": {},
   "changed": {
    "1": {
     "created_at": [
      "2026-06-13T00:04:48.958638",
      "2026-06-13T04:04:48.958+00:00"
     ]
    },
    "11": {
     "closed_at": [
      "2026-09-17T15:22:35.263866",
      "2026-09-17T19:22:35.263+00:00"
     ],
     "created_at": [
      "2026-09-17T15:22:14.228127",
      "2026-09-17T19:22:14.228+00:00"
     ],
     "updated_at": [
      "2026-09-17T15:22:35.263866",
      "2026-09-17T19:22:35.263+00:00"
     ]
    },
    "2": {
     "created_at": [
      "2026-09-02T14:49:39.104923",
      "2026-09-02T18:49:39.104+00:00"
     ]
    },
    "3": {
     "created_at": [
      "2026-09-02T14:56:57.713399",
      "2026-09-02T18:56:57.713+00:00"
     ]
    },
    "4": {
     "created_at": [
      "2026-09-07T09:09:00.130231",
      "2026-09-07T13:09:00.130+00:00"
     ]
    },
    "5": {
     "created_at": [
      "2026-09-07 17:27:55",
      "2026-09-07T17:27:55.000+00:00"
     ]
    },
    "6": {
     "created_at": [
      "2026-09-09T19:50:41.005067",
      "2026-09-09T23:50:41.005+00:00"
     ],
     "updated_at": [
      "2026-09-09T19:54:06.795174",
      "2026-09-09T23:54:06.795+00:00"
     ]
    }
   },
   "removed": {}
  },
  "schema_version": {
   "added": {
    "78": {
     "applied_at": "<clock>",
     "version": 79
    }
   },
   "changed": {},
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
