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
   must hold afterwards (Phase 359).
2. **`python .claude/skills/deploy/deploy.py dryrun <phase>`.** Live is
   only read. It then:
   - backs up to `~/backups/motodiag/` and keeps 5;
   - migrates a copy in `data/deploy_scratch/` (gitignored, deleted after
     use) and diffs every table by rowid;
   - checks the scope and runs the F158 census on the copy;
   - writes **`docs/phases/in_progress/<phase>_dryrun_diff.md`**, headed
     with the backup's path and sha256, the scope file's sha256, the
     census count and any scope problem.
3. **Commit the diff and show it to the operator.** Changing an existing
   live row is a rule-1 stop. Wait for the operator's words.
4. **`deploy.py apply-live <phase>`.** It refuses, before touching live,
   unless:
   - the diff file exists, is committed and is unchanged;
   - the diff records no scope problem;
   - the backup still hashes as recorded, and the scope file is the one
     the diff was made with;
   - live still equals the backup;
   - a fresh dry run on a new copy stays in scope.

   It then migrates live, writes `<phase>_live_diff.md` and checks the
   scope again.
5. **At close-out**, the diff files move to `completed/` with the phase
   documents, and so does the scope file.

## What it holds, and what it cannot

`tests/test_phase358_deploy_contract.py` runs every refusal on fixture
databases. Each refusal was broken on purpose and seen red.

- **It cannot see whether the operator approved.** It sees only that the
  diff is committed and unchanged. The approval is the operator's words,
  quoted in the phase log.
- **The scope is as good as the person who writes it.** A `where` clause
  that matches the wrong single row passes.
