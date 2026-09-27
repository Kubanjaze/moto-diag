# deploy — changelog

## 2026-09-27 — created (Phase 358, K3)

The operator: "deploy script in the repo. it writes the approved dry-run
diff into the phase folder, and the live apply refuses to run without that
file. no more temp copies." And, accepted at v1.0: "live apply refuses
unless the diff file is committed and unchanged."

- **Where it came from:** Phase 262's `deploy262.py`, kept verbatim with
  its sha256 in `358_step0.md`. What changed from it:
  - the scope is JSON in the phase folder, no longer Python constants;
  - the diff goes to the phase folder, no longer the scratchpad;
  - copies go to the gitignored `data/deploy_scratch/` and are deleted;
  - the census is `scripts/f158_census.py`;
  - the paths are arguments;
  - the apply refuses without a committed, unchanged diff, and when the
    diff records a scope problem, the backup's hash moved, or the scope
    file changed.
- **Controls, in the contract test, on fixture databases:**
  - each refusal: no file, uncommitted, edited after commit, an
    out-of-scope dry run, live changed, a fresh dry run out of scope, the
    scope changed, the backup gone;
  - a clean apply;
  - retain-5;
  - an ambiguous scope entry refused.
- **Four mutations were each seen red and reverted:** the committed check,
  the unchanged check, live-equals-backup, and the fresh scope check.
  Under each, the fixture's "live" was migrated.
- **358 never ran it against live.** Its first real use is the content
  phase.
