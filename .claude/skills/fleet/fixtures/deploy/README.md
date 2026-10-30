# The database step's fixtures (Phase 395, K58)

Hand-written. `known_bad/` holds one case per refusal the prompt names;
each must be refused, and the good tree it changes must pass (the control).
The tests are `tests/test_phase395_engineer_deploy.py` (the first two and
the fourth), `tests/test_phase395_dispatcher_deploy.py` (the third) and
`tests/test_phase395_q1.py` (the fifth).

| file | the refusal |
|---|---|
| `known_bad/deploy_dirty_clone.json` | a `deploy` with an uncommitted file in the clone |
| `known_bad/deploy_no_scope_file.json` | a `deploy` whose branch has no scope file |
| `known_bad/resume_live_not_equal.json` | the resume, with `verify-live` saying live is not the approved diff (exit 3) |
| `known_bad/code_after_apply.json` | the close-out round after the apply changes code |
| `known_bad/q1_migration_no_live_diff.json` | Q1 on a migration with a dry-run diff and no live diff |

`deploy_result.json` is a `deploy` the Engineer may write. `trial/` is the
trial's output (Phase 395), kept as the prompt asks.
