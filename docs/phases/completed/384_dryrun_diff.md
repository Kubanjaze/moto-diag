# Phase 384: the dry-run diff for the live migration

- **Written:** `2026-10-20T22:55:30`
- **Backup:** `/home/lilcu/backups/motodiag/motodiag_pre384_20261020_225529.db`
- **Backup sha256:** `7858302e2ac895cf6530ce95f688ec0d970bdd18229cade71fdebf620b5a355f`
- **Scope sha256:** `ccc8c6f1897f4998c16a65c889550892bf9ff30ab7093a2b2dac39905698f26e`
- **Migrations applied on the copy:** `[]`
- **F158 census on the copy:** `41`
- **Scope problems:** `none`

The live apply refuses to run unless this file is committed and unchanged,
and unless a fresh dry run equals the exact diff at its end.

<!-- dry-run diff below; everything above is its header -->

<!-- the exact diff, clock values masked: apply-live compares a fresh dry run with it -->
```json
{
 "rows": {},
 "schema": {
  "added": [],
  "changed": [],
  "removed": [],
  "sql": {}
 }
}
```
