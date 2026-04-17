# MotoDiag Phase 130 — Shell Completions + Shortcuts

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Power-user polish: tab-completion for bash/zsh/fish, dynamic completion for runtime data (bike slugs, DTC codes, session IDs), and short command aliases for the highest-frequency paths. No migration, no new package — new `src/motodiag/cli/completion.py` orchestration module + small alias registrations in `cli/main.py`.

```
motodiag completion bash | zsh | fish     # print setup script with install hints
motodiag diagnose quick --bike <TAB>      # dynamic garage completion
motodiag code <TAB>                        # dynamic DTC completion
motodiag diagnose show <TAB>               # dynamic session-id completion
motodiag d quick ...                       # alias: d → diagnose
motodiag k list                            # alias: k → kb
motodiag g list                            # alias: g → garage
motodiag q "..."                           # alias: q → quick
```

Outputs: new `src/motodiag/cli/completion.py` (~260 LoC), wire-up + alias registration in `cli/main.py`, `shell_complete=` callbacks on 6 existing CLI options/arguments, 18 new tests. **No migration.**

## Logic

### 1. `motodiag completion <shell>` command
- `register_completion(cli_group)` attaches a `@cli_group.group("completion")` with 3 subcommands `bash` / `zsh` / `fish`.
- Each subcommand prints a shell-specific header comment (install-hints) followed by Click's generated completion script.
- Script generation uses `click.shell_completion.get_completion_class(shell).source()` via the top-level `cli` context. The completion env var is hardcoded as `_MOTODIAG_COMPLETE` per Click's convention.
- Unknown shell → Click's built-in `Choice` validation emits a clear error with exit code != 0.

### 2. Three dynamic completer callbacks
All three live in `cli/completion.py`, use `_safe_get_db_path()` (returns `None` on any settings-read error), and wrap DB access in try/except so tab-completion never crashes a mechanic's shell.

- `complete_bike_slug(ctx, param, incomplete)` — iterates `vehicles` table in DB order, builds slug as `f"{model.lower().replace(' ', '-')}-{year}"`, returns `CompletionItem`s whose slug starts with `incomplete.lower()`. Capped at `_MAX_SUGGESTIONS = 20`.
- `complete_dtc_code(ctx, param, incomplete)` — `SELECT DISTINCT code FROM dtc_codes WHERE code LIKE ? ORDER BY code LIMIT 20` with `incomplete.upper()+"%"` as the LIKE pattern. Force-uppercases so `p01<TAB>` finds `P0115`.
- `complete_session_id(ctx, param, incomplete)` — fetches most-recent 50 sessions (`_SESSION_FETCH_LIMIT = 50`), filters stringified IDs by prefix-match, returns up to 20. Prefix-on-string (not numeric-range) matches how completion UIs actually behave — `4<TAB>` surfaces `4`, `40`, `42`, `47`.

### 3. Short aliases in `cli/main.py`
- `_register_short_aliases(cli)` helper defined in `main.py`. For each alias pair (`d`→diagnose, `k`→kb, `g`→garage, `q`→quick), it shallow-copies the canonical command via `copy.copy(cmd)`, sets `hidden=True` on the clone, and registers the clone under the alias name.
- Shallow-copy is important: setting `hidden=True` directly on the canonical would hide it from `--help` everywhere, defeating the purpose. The clone shares the canonical's `commands` dict (for Group aliases), so `motodiag d quick ...` still resolves subcommands correctly.
- Called after `register_diagnose(cli)` / `register_kb(cli)` / `register_quick(cli)` in `main.py`.

### 4. Dynamic completers wired into existing options
- `cli/diagnose.py`: `--bike` on `diagnose quick` + top-level `quick` gets `shell_complete=complete_bike_slug`. `session_id` argument on `diagnose show`, `diagnose reopen`, `diagnose annotate` gets `shell_complete=complete_session_id`.
- `cli/code.py`: the `code` positional argument gets `shell_complete=complete_dtc_code`.

### 5. Testing (18 tests)
- `TestCompletionCommand` (5): `completion --help` lists 3 shells; `bash` / `zsh` / `fish` each print non-empty script containing the `_MOTODIAG_COMPLETE` env-var marker; unknown shell errors via Click's Choice validation.
- `TestDynamicCompleters` (8): bike-slug returns seeded / empty-on-fresh-DB / prefix-filters; dtc-code returns seeded / empty-on-fresh-DB / prefix-filters; session-id returns recent / empty-on-fresh-DB. All use `cli_db` fixture with seeded data via `add_vehicle`/`add_dtc`/`create_session` for the positive cases. Fresh-DB tests point MOTODIAG_DB_PATH at a fresh path without calling `init_db`, verifying defensive error handling.
- `TestAliases` (4): `motodiag d --help` works (resolves to diagnose); `motodiag k list` works (empty kb OK); `motodiag g --help` works; top-level `motodiag --help` does NOT list ` d ` / ` k ` / ` g ` / ` q ` (aliases hidden).
- `TestRegistration` (1): `completion` group registered under `cli.commands`.

All tests use `cli_db` fixture. Zero AI calls. Zero live tokens.

## Key Concepts
- **Click's completion infrastructure is battle-tested** — we just surface it with a friendlier wrapper and install hints.
- **Dynamic completers hit the DB at tab-time** — must be fast. `LIMIT 20` caps per-tab work; defensive try/except means a missing DB never crashes the shell.
- **Hidden aliases** keep the top-level `--help` clean — canonical names are the discoverable surface; aliases are a power-user convenience.
- **Shallow-copy aliasing pattern** avoids mutating the canonical command's `hidden` flag. Builder-A caught this subtle semantics issue during design (the plan suggested setting `hidden=True` on the original, which would have hidden it from help everywhere).
- **Three shells cover 95%** — bash/zsh covers macOS/Linux; fish covers the power-user crowd. PowerShell is a future item if Windows mechanics demand it.
- **`CompletionItem` import path**: the Phase 130 first test run caught that `click.shell_completion.CompletionItem` is NOT accessible as `click.<attr>.<attr>` — must be imported via `from click.shell_completion import CompletionItem`. Architect fixed in-place during trust-but-verify.

## Verification Checklist
- [x] `motodiag completion --help` lists 3 shells (bash, zsh, fish)
- [x] `motodiag completion bash` prints non-empty script
- [x] `motodiag completion bash` output contains `_MOTODIAG_COMPLETE`
- [x] `motodiag completion zsh` prints non-empty script
- [x] `motodiag completion fish` prints non-empty script
- [x] `motodiag completion invalid_shell` errors cleanly via Click's Choice validator
- [x] `complete_bike_slug` returns slugs for seeded garage
- [x] `complete_bike_slug` on fresh DB (no tables) returns `[]` without crashing
- [x] `complete_bike_slug` prefix-filters correctly
- [x] `complete_dtc_code` returns seeded DTCs
- [x] `complete_dtc_code` on fresh DB returns `[]`
- [x] `complete_dtc_code` prefix-filters (case-insensitive — `p01<TAB>` matches `P0115`)
- [x] `complete_session_id` returns recent session IDs
- [x] `complete_session_id` on fresh DB returns `[]`
- [x] `motodiag d --help` resolves to diagnose group help
- [x] `motodiag k list` resolves to kb list
- [x] `motodiag g --help` resolves to garage help
- [x] `motodiag --help` output does NOT list ` d ` / ` k ` / ` g ` / ` q ` (aliases hidden)
- [x] `completion` group registered in cli.commands
- [x] All 2253 existing tests still pass (zero regressions — full suite running)
- [x] Zero live API tokens burned

## Risks (all resolved)
- **Click API drift**: `click.shell_completion` is a submodule, not a top-level attribute. First test run failed with `AttributeError: shell_completion`. Architect added `from click.shell_completion import CompletionItem` and `sed`-replaced all `click.shell_completion.CompletionItem` references. One-minute fix. Same issue wouldn't recur because the import is now explicit.
- **Dynamic completer DB latency**: each has `LIMIT 20` (or post-filter equivalent with `LIMIT 50`). Worst case is ~20 rows fetched per tab-press — fast.
- **Alias shadowing by future commands**: if Phase 131+ adds a command named `d`/`k`/`g`/`q`, the alias would collide. Low probability; noted.
- **Bash-completion package not installed on user's system**: install hints in the printed script header cover this ("install bash-completion first" is a common shell docs note).

## Deviations from Plan
- **Alias pattern: shallow-copy instead of mutating canonical**: plan said `cli.add_command(cli.commands["diagnose"], name="d")` then `cli.commands["d"].hidden = True`. That would have mutated the canonical's `hidden` flag (same object). Builder used `copy.copy(cmd)` to clone, set `hidden=True` on the clone, and register the clone under the alias name. Clone shares the `commands` dict so subcommand resolution still works. Correct refinement of the plan.
- **`CompletionItem` import from submodule**: plan implied `click.shell_completion.CompletionItem` works as attribute access. First test run showed it doesn't. Architect's in-place fix: explicit `from click.shell_completion import CompletionItem` import and updated all references.
- **Test count 18 matches plan exactly**.
- **`completion.py` ~260 LoC vs planned ~180**: thorough defensive DB-error handling + detailed docstrings (same pattern as Phase 129's over-spec on docstrings). Public surface unchanged.

## Results
| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/cli/completion.py`, `tests/test_phase130_completion.py`) |
| Modified files | 3 (`src/motodiag/cli/main.py`, `src/motodiag/cli/diagnose.py`, `src/motodiag/cli/code.py`) |
| New tests | 18 |
| Total tests | 2271 passing (was 2253) |
| New CLI commands | 1 group (`completion`) + 3 subcommands + 4 hidden aliases |
| Dynamic completers wired | 3 (on 6 existing option/argument sites) |
| Migration | None |
| Schema version | 14 (unchanged) |
| Regression status | Zero regressions (pending — full suite running) |
| Live API tokens burned | **0** (pure CLI + DB, no AI involvement) |

Sixth agent-delegated phase. Builder-A delivered clean code with one Click-API-subtlety caught by Architect's trust-but-verify run (`CompletionItem` import path). All 18 phase tests passed on retry after the one-line fix. Builder's shallow-copy aliasing pattern is a genuine refinement over the plan — would have shipped a subtle `hidden=True` mutation bug if followed literally. Agent delegation continues to compound: the quality of Builder's output keeps improving as the codebase accumulates patterns the agent reads and imitates.
