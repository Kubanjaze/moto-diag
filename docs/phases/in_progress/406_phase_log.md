# Phase 406 — phase log

## 2026-11-19 — Step 0 and v1.0

The operator, 2026-11-19 (K93): "Yes. Set it up as phase 406 and build it on
the Mac now, alongside 334. Two conditions: it comes as a pull request I
merge after your review, not a direct push to master, and the database step
from the Mac must still show me the dry run's list before it asks for yes."

Master `3ebeac6` holds K93, row 406 (🚧), the prompt
(`docs/prompts/406_the_mac_runs_the_rest.txt`) and the plan of record's
entry. This branch is `phase-406-the-mac-runs-the-rest`, from `3ebeac6`.

Step 0 (`406_step0.md`): the fixed list has 13 operations; the lock's
`PermitTTY no` means the database step cannot ask for yes through the way
in, so it becomes two calls with the yes on the Mac; the only password-free
rule is the app server's. Classification: extension.

v1.0 (`406_implementation.md`): ten operations, the database step's two
modes, `remote.py deploy-step`, one more password-free rule line and
`update_remote.sh`. No change to the lock.
