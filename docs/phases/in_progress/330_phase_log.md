# Phase 330 — phase log

**Status:** In progress

## 2026-11-21 — Step 0, re-measured by the Engineer

On this branch at `bc2f7bf` (v1.0, the Executive Officer's round 2).

- **`src/motodiag/cli/shop.py`,** as the plan reads: `_sole_shop_id_or_fail`
  217, `_resolve_shop_identifier` 258 (no identifier: `list_shops()`, owner
  1 by default; several shops: "Multiple shops exist (...); pass --shop NAME
  or --shop ID.", a `ClickException`, exit 1), `register_shop` 622, the
  `shop` group 633, `profile init` 644 (calls `create_shop` with no owner),
  `profile show` 692, `profile list` 707 (`list_shops(include_inactive=...)`),
  `customer add` 804, `customer link-bike` 992, `customer bikes` 1056,
  `member add` 4294, `member list` 4314, `register_inventory(shop_group)`
  4761.
- **The default owner:** `create_shop` 138 (`owner_user_id: int = 1` at
  148), `get_shop_by_name` 191 (`owner_user_id: int = 1`), `list_shops` 205
  (`owner_user_id: Optional[int] = 1`; `None` is every shop; ordered by
  `s.name, s.id`).
- **`src/motodiag/cli/main.py`:** `cli` 45, `garage` 441, `garage add` 506,
  `garage list` 546, `register_shop(cli)` 912, `register_user(cli)` 924,
  `register_workflow(cli)` 952.
- **`src/motodiag/cli/user.py`:** `_read_password` 43, `_hash_or_fail` 51,
  `register_user` 76, `user create` 83 (its function at 89);
  `MIN_PASSWORD_LENGTH = 8` (`auth/passwords.py` 31).
- **`src/motodiag/cli/workflow.py`:** `register_workflow` 57,
  `_template_or_refuse` 154, `POWERTRAINS` 169, `_walk` 173, `run` 199,
  `run_cmd` 207 (powertrain exit at 221 to 226), `start` 355 (its options
  `--bike`, `--vehicle-id`, `--work-order`, `--powertrain`).
  `template_repo.py`: `get_template_by_slug` 54, `list_templates` 63,
  `get_checklist_items` 168.
- **A fresh migrated database** holds 13 active templates (the first,
  `brake_service_v1`, covers `ice`, `electric`, `hybrid`, 7 items), one
  user (the system user, id 1), one customer (the seeded "Unassigned",
  id 1), and no row in `shops`, `shop_members`, `terms_acceptances`,
  `vehicles`, `customer_bikes` or `workflow_runs`.
- **The name:** `git grep -n -i onboard -- src/motodiag/cli` finds 4 lines,
  all in `payments.py` (31, 245, 251, 258), as the plan reads. No `onboard`
  group exists.
- **The `cli_db` fixture,** `tests/test_phase160_shop.py` 105 to 116, as
  the plan reads; `_make_cli` at 86 registers only `shop`.
- **Pins:** no test reads `cli.commands['shop'].commands` or counts the
  `shop` sub-groups or the root's commands (`grep -rn` over `tests/` for
  `commands['shop']`, `commands["shop"]`, `register_inventory(shop_group)`
  and `len(...commands)`: 0 lines). `docs/guide/shop-workflow.md` is read by
  `tests/test_phase208_docs.py`, which resolves every `motodiag` command in
  a `bash` block against the Click registry; the new paragraph's commands
  must therefore exist, which they do once the group is registered.
