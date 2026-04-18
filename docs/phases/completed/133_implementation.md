# MotoDiag Phase 133 — Gate 5: CLI Integration Test

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Results
| Metric | Value |
|--------|------:|
| New files | 1 (`tests/test_phase133_gate_5.py`) |
| Modified files | 0 — test-only phase |
| New tests | 7 (1 workflow + 4 surface-breadth + 2 Gate R regression) |
| Total tests | 2333 passing (was 2326) |
| Workflow CLI invocations | 19 commands in one shared-DB test |
| AI mocks | 3 (`_default_diagnose_fn`, `_default_interpret_fn`, `_default_vision_call`) |
| Gate 5 status | ✅ **PASSED** |
| Schema version | 15 (unchanged) |
| Live API tokens burned | **0** |

**GATE 5 PASSED** — Track D's user-facing CLI feature set works end-to-end. Ninth agent-delegated phase; Builder shipped clean code, 7 tests passed first run (6.04s) on Architect's trust-but-verify. Consolidated 19 CLI invocations into one cohesive workflow test (mirroring Gate R's Part A pattern over 20 siloed tests — one workflow proves cross-command state transitions that siloed per-command tests cannot).

## Deviations from Plan
- Test count 7 vs planned 15-20: Builder consolidated. One 19-step workflow covers more ground than 19 separate tests.
- `test_phase121_gate_r_still_passes` subprocess test dropped in favor of schema-version assertion + per-module-import diagnostic. Gate R already runs in the regular suite.
- Build fix: initial draft used non-existent `DTCCategory.SENSOR`; changed to `DTCCategory.ENGINE` (P0115 is ECT).

---

## Goal (v1.0)
Gate 5 is the integration checkpoint that closes Track D (mechanic CLI, phases 109-132). Prove the full mechanic workflow works end-to-end across every Track D command — from `garage add` through `diagnose quick` through report export and knowledge-base lookup — wired together on one shared DB fixture via Click's `CliRunner`. Pattern mirrors Phase 121's Gate R: **one big integration test file with ~15-20 tests**, zero new production code, pure observation over the existing CLI surface. If this test passes, Track D is closed and Phase 134 opens the next track.

CLI: `python -m pytest tests/test_phase133_gate_5.py -v` — **test-only phase, no new CLI commands, no new modules, no new migrations.**

Outputs:
- `tests/test_phase133_gate_5.py` — ONE new test file with ~15-20 integration tests across 3 classes (Part A workflow, Part B CLI surface, Part C regression)
- Zero production code changes (`src/motodiag/**` untouched)
- Zero schema changes (stays at v15 from Phase 131)
- Documentation: `docs/phases/in_progress/133_implementation.md` + `133_phase_log.md`, promoted to `completed/` on finish

## Logic

### Part A — End-to-end mechanic workflow (`TestMechanicEndToEnd` — 1 big test, ~180 LoC)

Single test `test_full_mechanic_flow` builds a realistic shop scenario on one shared DB fixture, using Click's `CliRunner` to invoke the real `motodiag.cli.main:cli` group. Each step depends on the previous step's DB state — catches cross-command integration bugs siloed unit tests miss. Mirrors Phase 121's `TestEndToEndShopWorkflow::test_full_workflow` structure.

**Setup:**
- `tmp_path` DB fixture (`cli_db` pattern from Phase 123 — monkeypatch `MOTODIAG_DB_PATH` + `reset_settings()`).
- Three mocks active for the whole test (nested `with` blocks):
  1. `patch("motodiag.cli.diagnose._default_diagnose_fn", fake_diagnose)` — returns a canned `DiagnosticResponse` with 90% confidence "Stator failure" diagnosis (reuses Phase 123's `make_response` helper).
  2. `patch("motodiag.cli.code._default_interpret_fn", fake_interpret)` — returns a canned fault-code explanation dict.
  3. `patch("motodiag.intake.vehicle_identifier._default_vision_call", fake_vision)` — not invoked in this workflow (no `garage add-from-photo` step) but patched defensively so any accidental camera path fails closed rather than hitting the API.
- Helper `run(args, input_=None)` — wraps `runner.invoke(cli, args, input=input_, catch_exceptions=False)`.

**Workflow steps (18 CLI invocations, each asserted):**

1. **`garage add`** — `motodiag garage add --make Harley-Davidson --model "Sportster 883" --year 2005 --engine-cc 883 --vin 1HD1CZ3115K123456 --protocol j1850 --powertrain ice`. Assert `result.exit_code == 0`, `"Added vehicle #1"` in output. Capture vehicle ID.
2. **`garage list`** — assert exit 0 + `"Sportster 883"` + `"2005"` in output.
3. **`motodiag quick "won't start, no spark"`** — Phase 125 top-level shortcut. Assert exit 0, session created (query `list_sessions(vehicle_id=1)` → 1 row), diagnosis text in output. Capture session ID.
4. **`diagnose list`** — assert exit 0 + the session ID + `"Sportster"` in output.
5. **`diagnose show <sid>`** — assert exit 0 + `"Stator failure"` + `"won't start"` in output.
6. **`diagnose show <sid> --format md --output <tmp>/report.md`** — assert exit 0, file exists, content starts with `# Session` and contains the diagnosis.
7. **`diagnose show <sid> --format html --output <tmp>/report.html`** (Phase 132) — assert exit 0, file exists, content starts with `<!DOCTYPE` and contains the diagnosis text.
8. **`diagnose show <sid> --format pdf --output <tmp>/report.pdf`** (Phase 132) — assert exit 0, file exists, bytes start with `%PDF-` magic.
9. **`diagnose annotate <sid> "Follow-up: stator AC output was 12V low — confirmed failure"`** (Phase 127) — assert exit 0, success message. Verify via `get_session(sid)` that the notes column now contains the annotation + timestamp.
10. **`diagnose reopen <sid>`** (Phase 127) — session was closed by `quick` in step 3. Assert exit 0, status flipped from `closed` → `open`.
11. **`code P0115`** (Phase 124) — local DTC lookup (no AI). Assert exit 0, description text present. Note: P0115 is a generic OBD-II coolant sensor code — seed via `add_dtc` before this step OR pre-load DTCs via `db init`. Plan: pre-seed in fixture to keep test hermetic.
12. **`code P0115 --explain --vehicle-id 1`** (Phase 124, AI path) — uses mocked `_default_interpret_fn`. Assert exit 0, canned explanation text present, zero real API hits.
13. **`kb list`** (Phase 128) — assert exit 0. If the fixture seeds a known issue, assert its title appears; otherwise assert the "no entries" fallback message.
14. **`kb search "stator"`** (Phase 128) — seed one `add_known_issue` with title "Twin-Cam stator failure" in the fixture. Assert exit 0 + title in output.
15. **`kb show <kbid> --format md --output <tmp>/kb.md`** (Phase 132) — assert exit 0, file exists, content starts with `# ` and contains the issue title.
16. **`cache stats`** (Phase 131) — assert exit 0, output contains cache count (may be 0 since diagnose/interpret are mocked — that's fine, the command itself must work).
17. **`intake quota`** (Phase 122) — assert exit 0, quota output (tier + used/limit or unlimited message).
18. **`tier --compare`** — assert exit 0, output contains all three tier names (`individual`, `shop`, `company`) — proves Phase 129 theme + Phase 118 subscription features wire into CLI.
19. **`completion bash`** (Phase 130) — assert exit 0, output contains bash completion snippet (`_MOTODIAG_COMPLETE`).

Total: 18 real CLI invocations plus 1 intentional-error check (`diagnose show 99999` → exit != 0 with clear error, proves CLI error paths aren't swallowed).

**Final integrity assertions (end of `test_full_mechanic_flow`):**
- `get_schema_version()` >= 15 (Phase 131's cache table migration).
- DB contains exactly 1 vehicle, 1 session (reopened, so status='open'), 1 DTC entry (P0115), 1 known-issue entry.
- Session has non-null `notes` column from step 9.
- 3 report files exist on disk (md + html + pdf) and are non-empty.

### Part B — CLI surface breadth (`TestCliSurface` — 4 tests)

Fast tests that don't require a DB — they inspect the Click command tree at import time.

1. **`test_all_toplevel_commands_registered`** — import `motodiag.cli.main:cli`; assert every expected command name is in `cli.commands`: `diagnose`, `code`, `kb`, `garage`, `intake`, `cache`, `completion`, `tier`, `config`, `info`, `history`, `quick`, `db`, `search`. Assert short aliases `d`, `k`, `g`, `q` are ALSO in `cli.commands` but have `hidden=True`.
2. **`test_hidden_aliases_not_in_help`** — invoke `cli --help` via `CliRunner`; assert `"\n  d "` and `"\n  k "` and `"\n  g "` and `"\n  q "` do NOT appear as leading command-list entries (they may appear in text, but not as command rows). Assert `"diagnose"`, `"kb"`, `"garage"`, `"quick"` DO appear.
3. **`test_expected_subcommands_present`** — for each subgroup, assert its expected subcommand names:
   - `diagnose`: `start`, `quick`, `list`, `show`, `reopen`, `annotate`
   - `garage`: `add`, `list`, `remove`, `add-from-photo`
   - `intake`: `photo`, `quota`
   - `kb`: `list`, `search`, `show`
   - `cache`: `stats`, `purge`, `clear`
   - `completion`: `bash`, `zsh`, `fish`
   - `config`: `show`, `paths`, `init`
   - `db`: `init`
4. **`test_cli_help_exits_zero_via_subprocess`** — `subprocess.run([sys.executable, "-m", "motodiag.cli.main", "--help"], ...)` exits 0 in under 30 seconds and output contains `"MotoDiag"` + `"diagnose"` + `"garage"`. Mirrors Phase 121's `test_motodiag_cli_help_works` — catches any circular import or module-level side effect introduced during Track D.

### Part C — Regression + schema compat (`TestRegression` — 3 tests)

1. **`test_phase121_gate_r_still_passes`** — collect and run `tests/test_phase121_gate_r.py::TestEndToEndShopWorkflow::test_full_workflow` via `pytest.main([...])` in a subprocess, assert exit 0. Proves Track D phases 122-132 did not break the retrofit integration.

   _Alternative if subprocess-pytest is flaky: import the Gate R test function directly and invoke with a fresh fixture. Decision during build._

2. **`test_schema_version_is_at_least_15`** — fresh `init_db(tmp_path_db)`; `get_schema_version() >= 15`. Covers Phase 131's migration 015 forward-compat for Track E phases that will bump schema further.

3. **`test_all_track_d_cli_modules_import_cleanly`** — direct in-process import of every `motodiag.cli.*` submodule (`diagnose`, `code`, `kb`, `cache`, `completion`, `theme`, `export`, `subscription`, `registry`). Belt-and-suspenders companion to Part B's subprocess test — if the subprocess `--help` fails, this gives a precise per-module diagnostic.

### Fixture design

```python
@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Phase 123 fixture pattern: point settings at a temp DB."""
    from motodiag.core.config import reset_settings
    from motodiag.core.database import init_db
    from motodiag.knowledge.dtc_repo import add_dtc
    from motodiag.core.models import DTCCode
    # ... seed P0115, seed one known_issue for kb tests
    db_path = str(tmp_path / "phase133.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    reset_settings()
    init_db(db_path)
    # seed DTC + known issue here so workflow steps 11/14 have data
    yield db_path
    reset_settings()
```

Mocks (reused from Phase 123/124/125 test helpers where possible):
- `make_diagnose_fn` / `make_response` from `tests/test_phase123_diagnose.py` — import directly.
- `fake_interpret` — local helper returning a canned `FaultCodeExplanation`-shaped SimpleNamespace.
- `fake_vision` — local helper returning a canned `VehicleGuess` — unused in this test but patched defensively.

## Key Concepts
- **Gate 5 is a checkpoint, not a feature.** Same contract as Gate R (Phase 121): no new production code, no new packages, no migrations. Only: one test file that integrates the whole CLI surface via `CliRunner`.
- **One cohesive scenario, not 18 disconnected tests.** The workflow test shares state across steps because that's how real mechanics use the tool — diagnose writes a session, `show` reads it, `annotate` mutates it, `reopen` mutates it again. Siloed per-command unit tests (which already exist in phases 122-132) would NOT catch an annotation-then-reopen-then-export bug. This gate test will.
- **CliRunner over subprocess for the workflow.** `CliRunner.invoke()` runs Click commands in-process, captures stdout/stderr, returns a `Result`. Much faster than subprocess (10-100x), exposes exceptions cleanly, and shares the monkeypatched `MOTODIAG_DB_PATH` env var. Subprocess is reserved for the import-graph smoke test where in-process isn't representative.
- **Three mocks, zero live tokens.** Every AI-bearing path is patched at the boundary (`_default_diagnose_fn`, `_default_interpret_fn`, `_default_vision_call`). These are the same patch points Phase 123/124/122 use in their own unit tests — we're composing, not inventing.
- **Hidden-alias assertion pattern.** Phase 130's short aliases (`d`/`k`/`g`/`q`) are tested for both registration (exist in `cli.commands`) AND help suppression (don't appear as rows in `--help` output). This catches the specific failure mode where a refactor re-registers the alias without the `hidden=True` clone — users would suddenly see `d` cluttering their help screen.
- **Phase 121 Gate R stays green.** Part C explicitly re-runs Gate R's end-to-end workflow to prove Track D (phases 122-132, ~500 new tests, 6 new CLI commands) did not regress the retrofit integration. If Gate R fails, Track D did something that broke the substrate — stop and fix.
- **Schema v15 as a floor, not a ceiling.** The `>=` comparison (Phase 121 convention) keeps this test compatible with future migrations. Phase 134+ can bump to v16 without editing this test.
- **This is a Click-surface test, not a logic test.** We don't re-test the diagnosis algorithm, the PDF renderer, the cache hash function, etc. — those are covered in their own phases. Gate 5 only verifies that the CLI wires these pieces together correctly when a real mechanic drives them from a terminal.

## Verification Checklist
- [ ] `tests/test_phase133_gate_5.py` exists with exactly 3 test classes: `TestMechanicEndToEnd`, `TestCliSurface`, `TestRegression`
- [ ] Part A: `test_full_mechanic_flow` runs 18+ CLI invocations on one shared DB via `CliRunner`
- [ ] Part A: all 3 AI boundaries mocked (`_default_diagnose_fn`, `_default_interpret_fn`, `_default_vision_call`)
- [ ] Part A: `garage add` + `garage list` happy path passes
- [ ] Part A: `motodiag quick "<symptoms>" --bike <slug>` creates a session and persists a diagnosis
- [ ] Part A: `diagnose list` + `diagnose show <id>` happy paths pass
- [ ] Part A: `diagnose show --format md/html/pdf --output <path>` all three formats produce non-empty files with correct magic/prefix
- [ ] Part A: `diagnose annotate <id> "note"` writes to session.notes; verified via direct DB read
- [ ] Part A: `diagnose reopen <id>` flips status from closed → open; verified via DB read
- [ ] Part A: `code P0115` (local lookup) returns description; pre-seeded in fixture
- [ ] Part A: `code P0115 --explain --vehicle-id 1` uses mocked interpreter, returns canned explanation, zero API hits
- [ ] Part A: `kb list` + `kb search "stator"` find the seeded known-issue entry
- [ ] Part A: `kb show <id> --format md --output <path>` writes markdown file
- [ ] Part A: `cache stats`, `intake quota`, `tier --compare`, `completion bash` all exit 0 with expected keywords
- [ ] Part A: final integrity asserts schema >= 15, 1 vehicle, 1 session (status=open), session.notes populated, 3 report files on disk
- [ ] Part B: `test_all_toplevel_commands_registered` — 14 canonical commands + 4 hidden aliases all present
- [ ] Part B: `test_hidden_aliases_not_in_help` — `d`/`k`/`g`/`q` absent from `--help` command rows
- [ ] Part B: `test_expected_subcommands_present` — all 8 subgroups have expected subcommands
- [ ] Part B: `test_cli_help_exits_zero_via_subprocess` — `python -m motodiag.cli.main --help` exits 0 in <30s
- [ ] Part C: `test_phase121_gate_r_still_passes` — Gate R's workflow test still green
- [ ] Part C: `test_schema_version_is_at_least_15` — forward-compat floor
- [ ] Part C: `test_all_track_d_cli_modules_import_cleanly` — every `motodiag.cli.*` submodule imports
- [ ] Zero live API tokens burned during the full test run
- [ ] Full regression suite still passes (2326 existing + ~15-20 new Gate 5 tests)
- [ ] No production code modified (`git diff src/` empty)

## Risks
- **Risk: Gate 5 failure = Track D is not done.** If any of the 18 workflow steps fail, Track D has an integration bug that siloed unit tests missed. Fix in-place before declaring Track D closed — do not paper over with `pytest.skip`.
- **Risk: mock drift.** If Phase 123's `_default_diagnose_fn` or Phase 124's `_default_interpret_fn` get renamed/moved in a later refactor, this test breaks. Mitigation: pin the exact patch paths in this file's docstring and reference them by the phase that introduced them. Any future renamer must update Gate 5.
- **Risk: subprocess CLI test flakiness.** Windows path issues + `sys.executable` + 30s timeout are Phase 121-proven robust. Low risk. If it flakes, fall back to direct import-graph test (Part C #3).
- **Risk: CliRunner state leakage between steps.** `CliRunner.invoke` creates a fresh context each call, but the underlying DB via env-var monkeypatch persists — that's intentional. Watch for Click's `standalone_mode=True` default swallowing exceptions: use `catch_exceptions=False` on every `.invoke()`.
- **Risk: xhtml2pdf native lag.** PDF step (A.8) can take ~1-2s on slow runners. Acceptable; Phase 132 already absorbs this cost in CI.
- **Risk: seeded fixture gets reused across tests unintentionally.** Each test that needs fresh state should request the `cli_db` fixture afresh (pytest gives each test a fresh `tmp_path`). Workflow test is the only stateful one; Parts B+C are stateless or use their own isolated DBs.
- **Risk: Phase 121 Gate R regression test re-runs become a maintenance drag.** If Gate R is already in the regular suite, running it twice is redundant but cheap (~4s). Keep it explicit here as a documented "Track D did not break the substrate" claim — future devs read Gate 5, see Gate R invoked, understand the contract.
- **Risk: hidden-alias test too strict.** Click's help output format may change across versions. Mitigation: assert on structural substrings (`"\n  d "` as a command row), not the whole help text. If Click changes format, update the assertion — it's intentionally tight.
- **Risk: `completion bash` output changes when Click regenerates the completion snippet.** Assert only on a stable marker like `_MOTODIAG_COMPLETE`, not on byte-exact output.
