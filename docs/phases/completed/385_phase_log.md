# Phase 385 — The push token's own write — phase log

**Status:** ✅ Complete (2026-10-31)
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

### 2026-10-31 — The regression of record

`wholetree.sh --full` on `4753b2d`: 4986 passed, 36 skipped, exit 0 (record
`e91e21caf0861e6d83d4a08d1f74cfa8a0d2c71b_full.json`). Then
`regression.sh` on the clean tree, as printed:

Regression of record: 12047 passed, 0 failed, 105 skipped, 0 errors at `4753b2d` (34 min 21 s wall, `python -m pytest -n auto --dist load --cov=motodiag`, exit 0) (run inside the fleet's fence)
Skipped in the regression of record: [1] tests/test_phase204_gate10.py:47: inside the fleet's fence: no ffmpeg on the home desktop
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:137: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:145: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:153: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:162: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:175: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:185: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:218: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:223: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:248: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:259: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:272: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:292: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:306: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:321: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:333: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:340: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:438: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:445: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:464: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:249: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:264: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:269: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:277: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [1] tests/test_phase191b_ffmpeg.py:283: real ffmpeg binary or fixture mp4 not available
Skipped in the regression of record: [4] tests/test_phase257_sandbox_boundary.py:72: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:80: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:87: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:93: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:106: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:112: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:119: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:125: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [1] tests/test_phase257_sandbox_boundary.py:131: sandbox-exec is macOS-only; the orchestrator runs only there
Skipped in the regression of record: [7] tests/test_phase257_source_checks.py:211: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/Yamaha/library_om_contents_pdf_10_5YR-F8199-15_02.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:476: acquired/KTM/24_3214961_en_OM.pdf is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase257_source_checks.py:527: the KTM manual is not in this machine's library
Skipped in the regression of record: [1] tests/test_phase244H_test_db_isolation.py:79: no production database on this machine
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:147: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:352: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:358: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:364: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_manual_route_excerpts.py:367: needs the on-disk library
Skipped in the regression of record: [1] tests/test_phase257_orchestrator_guards.py:85: inside the fleet's fence: no Subconscious login there (K42)
Skipped in the regression of record: [2] tests/test_phase257_orchestrator_guards.py:149: inside the fleet's fence: osacompile is macOS-only
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:104: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase209_packaging.py:121: inside the fleet's fence: no network to build a wheel
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:61: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [4] tests/test_phase388_fence_boundary.py:96: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [3] tests/test_phase388_fence_boundary.py:105: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:113: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:120: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:125: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:131: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:139: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:148: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:159: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:164: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:170: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:177: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:186: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:198: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:210: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:216: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [7] tests/test_phase388_fence_boundary.py:221: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:235: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:244: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:280: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:287: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:291: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:295: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:303: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [2] tests/test_phase388_fence_boundary.py:316: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:325: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:330: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:338: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:344: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:350: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:354: inside the fleet's fence: its boundary is proven from the host, not from inside
Skipped in the regression of record: [1] tests/test_phase388_fence_boundary.py:360: inside the fleet's fence: its boundary is proven from the host, not from inside
Line coverage of record: 87.71% at `4753b2d` (the pin is 87.50%)

12047 passed + 105 skipped = 12152, the new `COLLECTED_TEST_FLOOR`.


No bug fixes: no defect was found in the phase's own committed code, so
there is no bug-fix register.

### 2026-10-31 — Close-out

**A guard blocked a command:** a Python script body (`python3 - <<'EOF'`)
writing v1.1 into `385_implementation.md` was refused by the edit guard,
because its text named `tests/` paths and the guard blocks a write it
cannot resolve. Made with the Edit tool instead; the guard is unchanged.

v1.1 written (Deviations, Results, the version history); the phase's files
moved to `docs/phases/completed/` with `git mv`; row 385 ✅ with its CLOSED
date and the regression line; the root `phase_log.md`'s pointer; the
handoff `docs/handoffs/2026-10-31_385_closed.md`, with the Mac's
after-the-merge block (no `gh` in it), K60's live proof (`verify-live 348`
must exit 0) and `verify-live 384` printed for the record only.

## Refuter pass

| claim | verdict | quote | source | round · kind · outcome |
|---|---|---|---|---|
| SERVER_WRITES gains the device_tokens entry, server_masked/WHOLE_TABLE unchanged | kept | "\"device_tokens\": frozenset({\"last_seen_at\"})}" | .claude/skills/deploy/deploy.py p. 186 | 1 · none · kept |
| The list was at deploy.py line 177 on the base (7 comment lines added since; now 184) | kept | "SERVER_WRITES: dict[str, frozenset[str]] = {\"api_keys\": frozenset({\"last_used_at\"})," | .claude/skills/deploy/deploy.py p. 184 | 1 · none · kept |
| The writer is register_token's upsert ON CONFLICT(token) DO UPDATE setting user_id, platform, last_seen_at | kept | "ON CONFLICT(token) DO UPDATE SET" | src/motodiag/push/registry.py p. 32 | 1 · none · kept |
| Migration 044 gives device_tokens six columns | kept | "last_seen_at TEXT NOT NULL" | src/motodiag/core/migrations.py p. 3576 | 1 · none · kept |
| The pin holds the three entries | kept | "\"device_tokens\": frozenset({\"last_seen_at\"})}" | tests/test_phase383_server_writes.py p. 168 | 1 · none · kept |
| tests/test_phase385_server_writes.py has 19 tests (3 + 12 controls + 2 + 2) | kept | "TestTheControlsStillFail 12, TestAMigrationThatWritesTheColumn 2," | tests/test_phase255B_collected_test_floor.py p. 462 | 1 · none · kept |
| COLLECTED_TEST_FLOOR 12133 → 12152 | kept | "COLLECTED_TEST_FLOOR = 12152" | tests/test_phase255B_collected_test_floor.py p. 465 | 1 · none · kept |
| 12047 passed + 105 skipped = 12152 | kept | "12047 passed + 105 skipped = 12152, the new `COLLECTED_TEST_FLOOR`." | docs/phases/completed/385_phase_log.md p. 161 | 1 · none · kept |
| TestTheRealRegistration monkeypatches registry._now after the backup | kept | "monkeypatch.setattr(registry, \"_now\", lambda: REGISTERED)" | tests/test_phase385_server_writes.py p. 197 | 1 · none · kept |
| Each control runs beside a registration and alone | kept | "@pytest.mark.parametrize(\"beside\", [True, False], ids=[\"beside\", \"alone\"])" | tests/test_phase385_server_writes.py p. 122 | 1 · none · kept |
| E2–E4 each run one control by -k | kept | "T_ADDED = pytest(T385, \"-k\", \"TestTheControlsStillFail and added_row\")" | docs/phases/completed/385_mutate.py p. 36 | 1 · none · kept |
| Mutations 5/5 red | kept | "5/5 red" | docs/phases/completed/385_mutate.out p. 6 | 1 · none · kept |
| F212 closed by Phase 385 on 2026-10-31 with the three controls | kept | "**Closed by Phase 385 (2026-10-31).** The operator chose the first (K39," | docs/FOLLOWUPS.md p. 3718 | 1 · none · kept |
| F210 gains "What the list still cannot cover" naming new token row, rebind, shop writes | kept | "**What the list still cannot cover** (Phase 385, 2026-10-31, after" | docs/FOLLOWUPS.md p. 3654 | 1 · none · kept |
| K39's cell names the entry, pin and controls | kept | "held by the pin in tests/test_phase383_server_writes.py and the controls in tests/test_phase385_server_writes.py; built in Phase 385." | docs/decisions.md p. 38 | 1 · none · kept |
| K60 decides (A): verify-live 348 is the proof of record, 384 for the record only | kept | "385's live proof is the newest deployed phase's check, verify-live 348 from the Mac, with verify-live 384 run for the record only" | docs/decisions.md p. 59 | 1 · none · kept |
| SKILL.md names the second column with F212 and K39 and what stays off | kept | "Since Phase 385 (F212, the operator's K39)," | .claude/skills/deploy/SKILL.md p. 137 | 1 · none · kept |
| CHANGELOG gains a dated entry at the top | kept | "## 2026-10-31 — device_tokens.last_seen_at joins SERVER_WRITES (Phase 385, K39, F212)" | .claude/skills/deploy/CHANGELOG.md p. 3 | 1 · none · kept |
| Handoff block's grep -v "set aside" works because set-aside names print on the same line | kept | "print(f\"  set aside: {len(aside)} change(s) the running API writes \"" | .claude/skills/deploy/deploy.py p. 811 | 1 · none · kept |
| The after-the-merge block runs no gh and ends ALL GOOD / SOMETHING IS OFF | kept | "echo \"ALL GOOD\"" | docs/handoffs/2026-10-31_385_closed.md p. 112 | 1 · none · kept |
| ROADMAP row closed with CLOSED date, regression line and K60's live proof | kept | "**CLOSED 2026-10-31.** `device_tokens.last_seen_at` joins `SERVER_WRITES`" | docs/ROADMAP.md p. 662 | 1 · none · kept |
| 385 is row 7 of Next, in order (K53), 345 next | kept | "| 7 | 385 | shop | fleet | nothing | 2026-10-21 · K53 |" | docs/reports/2026-10-12_plan_of_record.md p. 19 | 1 · none · kept |
| No refute pass ran, no bug fixes | kept | "No refute pass ran." | docs/phases/completed/385_phase_log.md p. 163 | 1 · none · kept |
