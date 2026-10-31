# Phase 385 — The push token's own write — phase log

**Status:** 🚧 In progress
**Branch:** `phase-385-the-push-token-s-own-write` (the Chief Engineer, in
the fleet's fence: a fresh clone, no push; the only writer)

---

### 2026-10-31 — Opened by the Chief Engineer, on v1.0

The plan is `385_implementation.md` v1.0 (`7a29f36`), approved by the
Executive Officer on issue #41; the operator's fork is decided as (A), K60
(`d0c28cc`). Row 385 was already 🚧 (`fee6428`). Read first: CLAUDE.md, the
plan, `385_step0.md`, `deploy.py`'s `SERVER_WRITES`,
`tests/test_phase383_server_writes.py`, `tests/test_phase348_server_writes.py`
and 348's mutation harness.

**The plan's re-verified facts hold on this branch** (`d0c28cc`):
- `SERVER_WRITES` is at `.claude/skills/deploy/deploy.py` line 177 and holds
  two entries, `api_keys.last_used_at` and `audit_events` (`WHOLE_TABLE`);
  `test_the_list_is_exactly_this` pins both.
- The writer: `src/motodiag/push/registry.py` `register_token`, an upsert
  whose `ON CONFLICT(token) DO UPDATE` sets `user_id`, `platform` and
  `last_seen_at`; migration 044 gives `device_tokens` six columns (`id`,
  `user_id`, `token`, `platform`, `created_at`, `last_seen_at`).
- The suite collects 12133 tests, equal to `COLLECTED_TEST_FLOOR`.

**Dates.** The plan names the handoff `2026-10-30_385_closed.md`; the
close-out is on 2026-10-31, and R6 wants a handoff dated no earlier than the
close, so it is `2026-10-31_385_closed.md`, and F212's closing paragraph
carries 2026-10-31.

**The fork (K60) is decided (A)**: the live proof of record is
`verify-live 348` from the Mac; `verify-live 384` runs for the record only.
The handoff's after-the-merge block follows it. The row's wording is the
operator's; it is not changed here beyond its status at close-out.

### 2026-10-31 — The entry, its tests, the mutations (`f1e14b3`)

- `deploy.py`: `SERVER_WRITES["device_tokens"] = frozenset({"last_seen_at"})`,
  and the comment naming the writer and what stays off the list (F210).
  `server_masked`, `WHOLE_TABLE` and every refusal are unchanged.
- The pin in `tests/test_phase383_server_writes.py` holds the three entries.
- `tests/test_phase385_server_writes.py`, 19 tests, fixture databases and a
  fresh database at the schema head only.
- **A decision, not in the plan:** each control runs twice, beside a
  registration and alone (12 control tests, not 6). Measured: with the
  entry widened to `WHOLE_TABLE`, the added-row control made only beside a
  registration stays green (`-k "added_row and beside"`: 2 passed), because
  the registration's changed row is itself drift under a whole-table entry
  and the refusal still fires. Alone, the control goes red on that
  mutation. Recorded in v1.1's Deviations.
- `385_mutate.py`: five mutations, each run against the test it must turn
  red; E2 to E4 each run one control, so their red runs are the controls
  seen failing. `385_mutate.out`: **5/5 red**.
- `COLLECTED_TEST_FLOOR` 12133 → 12152, a diff of collected ids against
  `d0c28cc`: +19 −0, all in the new file.

### 2026-10-31 — The documents

- `.claude/skills/deploy/SKILL.md`: the apply-live bullet names the second
  column, F212 and K39, and what stays off the list.
- `.claude/skills/deploy/CHANGELOG.md`: a dated entry at the top, in K59's
  form.
- `docs/FOLLOWUPS.md`: F212 closed, with its "Closed by Phase 385"
  paragraph; F210's "What the list still cannot cover". No new finding was
  filed: nothing found here is outside what the record names.
- `docs/decisions.md`: K39's "the check it became" cell names the entry,
  the pin and the controls.
