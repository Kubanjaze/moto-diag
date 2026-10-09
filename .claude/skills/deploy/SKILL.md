---
name: deploy
description: Apply a migration to the live moto-diag database — the dry run on a copy, the diff the operator approves (written into the phase folder and committed), and the live apply that refuses without it. Use when a phase's migration must reach data/motodiag.db, or when asked to deploy, dry-run or back up the live database.
---

# deploy — one script from backup to live

Built in Phase 358 (K3) from Phase 262's `deploy262.py`. Seven data phases
had each rewritten this step in a scratchpad under `/private/tmp`, and the
diff the operator approved for migration 071 survived there only by luck.

## The sequence

1. **Write the scope** as data:
   `docs/phases/in_progress/<phase>_deploy_scope.json`. Name every table
   the migration may touch, how many rows it adds or removes, and each
   existing row it may change. A row is found by a `where` clause that
   matches exactly one row before the migration, and it names the fields
   that may change. `fixtures/scope_262.json` is 262's scope in this form.
   An entry may also carry `"to": {field: value}`, the exact value the field
   must hold afterwards (Phase 359). Name every schema object the migration
   adds, removes or rewrites under `"schema"`, as
   `{"added": ["table workflow_runs", "index idx_wr_vehicle"]}`; any other
   schema change is a scope problem (Phase 357).
2. **`python .claude/skills/deploy/deploy.py dryrun <phase>`.** Live is
   only read. It then:
   - backs up to `~/backups/motodiag/` and keeps 5 (the operator, K27,
     2026-10-07: 5 now; 5 plus the first backup of each week once the
     first shop's real data is in);
   - migrates a copy in `data/deploy_scratch/` (gitignored, deleted after
     use) and diffs every table by rowid;
   - checks the scope and runs the F158 census on the copy;
   - **seed parity** (Phase 380, the operator's 2A): every `known_issues` row
     the migration adds or changes must equal the row with the same
     `row_key` in a fresh seed build at HEAD, every column but the id and
     the clocks, and a row it removes must be gone from that build (Phase
     381). A difference is a scope problem, so the seed and live cannot
     drift. `apply-live`'s own fresh run checks it again;
   - writes **`docs/phases/in_progress/<phase>_dryrun_diff.md`**, headed
     with the backup's path and sha256, the scope file's sha256, the
     census count and any scope problem. It ends with the **exact diff**
     as JSON: every field of every added or removed row, the before and
     after of every changed field, and the SQL of every schema object
     added or rewritten. A timestamp within a day of the run's own clock
     reads `<clock>`.
3. **Commit the diff and show it to the operator.** Changing an existing
   live row is a rule-1 stop. Wait for the operator's words.
4. **`deploy.py apply-live <phase>`, from the branch, after the regression
   of record** (Phase 378, K18: one order; the regression, the apply, the
   close-out commit, the merge). It refuses, before touching live, unless:
   - the phase log in `in_progress/` carries a regression line A5 can read,
     no code path changed between its commit and HEAD, and no code path is
     uncommitted (`fixtures/k18/` holds the known-bad logs);
   - the diff file exists, is committed and is unchanged;
   - the diff records no scope problem;
   - the backup still hashes as recorded, and the scope file is the one
     the diff was made with;
   - live still equals the backup;
   - a fresh dry run on a new copy stays in scope;
   - **that fresh run equals the committed exact diff, field for field**,
     clock values masked (F172, Phase 357). A diff file written before
     this check has no exact diff and is refused.

   It then migrates live, writes `<phase>_live_diff.md` and checks the
   scope and the equality again; the live diff says whether live equals
   the approved exact diff.
5. **`deploy.py verify-live <phase>`** (Phase 378, K25), read-only, any
   time after: it copies live and the phase's backup (opened immutable, so
   no `-shm` or `-wal` is left beside it) and prints the schema objects and
   tables that differ, whether that equals the approved exact diff, and
   live's integrity and foreign keys. It exits 3 when live does not equal
   the approved diff, and says when live's schema is past the phase's own
   migrations (F197, Phase 379); 1 on integrity or a foreign key; 2 with no
   deploy. verify_phase's check 8 calls it and fails on 1 or 3.
6. **At close-out**, the diff files move to `completed/` with the phase
   documents, and so does the scope file.

## What it holds, and what it cannot

`tests/test_phase358_deploy_contract.py` runs every refusal on fixture
databases. Each refusal was broken on purpose and seen red.

- **It cannot see whether the operator approved.** It sees only that the
  diff is committed and unchanged. The approval is the operator's words,
  quoted in the phase log.
- **The scope is as good as the person who writes it.** A `where` clause
  that matches the wrong single row passes.
- **The clock mask has a ceiling.** A migration edited to write a
  different timestamp that also falls within a day of the run is not told
  apart. A fixed date is compared (`tests/test_phase357_deploy_exact.py`).
