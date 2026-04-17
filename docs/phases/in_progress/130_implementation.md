# MotoDiag Phase 130 — Shell Completions + Shortcuts

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Power-user polish: tab-completion for bash/zsh/fish, dynamic completion for runtime data (bike slugs, DTC codes, session IDs), and short command aliases for the highest-frequency paths. No migration, no new package — lives in a new `src/motodiag/cli/completion.py` orchestration module plus small alias registrations in `cli/main.py`.

```
motodiag completion bash                  # print bash setup script
motodiag completion zsh                   # print zsh setup script
motodiag completion fish                  # print fish setup script

# Dynamic tab-completion examples (once the user sources the script):
motodiag diagnose quick --bike <TAB>      # completes with garage slugs
motodiag code <TAB>                        # completes with seen DTC codes
motodiag diagnose show <TAB>              # completes with recent session IDs

# Baked-in short aliases:
motodiag d         # → diagnose
motodiag k         # → kb
motodiag q "..."   # → quick
motodiag g list    # → garage list
```

Outputs: new `src/motodiag/cli/completion.py` (~180 LoC), wire-up in `cli/main.py`, ~18 new tests. **No migration.**

## Logic

### 1. `motodiag completion <shell>` command

Uses Click's built-in completion infrastructure. Click 8+ provides the script-generation mechanism via the `_<PROG>_COMPLETE=<shell>_source <prog>` magic env var — which prints the setup script to stdout when set.

Our command wraps that mechanism with user-friendly output:

- `motodiag completion bash` — prints the bash completion script to stdout with a header comment and install instructions.
- `motodiag completion zsh` — same for zsh.
- `motodiag completion fish` — same for fish.

Implementation approach: invoke Click's `shell_completion.get_completion_class(shell).source()` directly (public API in Click 8.1+). Fall back to documenting manual install if Click's API changes in a future version.

Install hint in the header comment of each printed script:

```
# MotoDiag bash completion
# Install:
#   motodiag completion bash > ~/.local/share/bash-completion/completions/motodiag
#   # or for current session only:
#   eval "$(motodiag completion bash)"
```

### 2. Dynamic completion callbacks

Click supports dynamic completion via `shell_complete=callback` on options/arguments. The callback receives `(ctx, param, incomplete)` and returns a list of `CompletionItem` objects.

Three dynamic completers added in `cli/completion.py`:

- **`complete_bike_slug(ctx, param, incomplete)`** — queries `vehicles` table, builds slugs `{model-lowercased}-{year}` for each row, filters to those starting with `incomplete` (case-insensitive). Returns up to 20. Registered on `--bike` options in `diagnose quick` and `motodiag quick`.
- **`complete_dtc_code(ctx, param, incomplete)`** — queries distinct `code` values from `dtc_codes` table, filters by `incomplete` prefix. Registered on the `code` positional arg of `motodiag code`.
- **`complete_session_id(ctx, param, incomplete)`** — queries recent `diagnostic_sessions` IDs (last 20 by `created_at DESC`), filters by `incomplete` prefix-match on the stringified ID. Registered on session_id args for `diagnose show`, `diagnose reopen`, `diagnose annotate`.

Each completer must be defensive — if the DB doesn't exist yet (fresh install), it returns `[]` rather than crashing tab-completion.

### 3. Short command aliases

Click's `Group.add_command(cmd, name="alias")` can register a single command under multiple names. For a subgroup like `diagnose`, we want `d` to resolve to the whole group, not just one subcommand.

Approach: add aliases by registering the existing group/command objects under short names via `cli.add_command(diagnose_group, name="d")` etc.

Baked-in aliases (4 added):
- `motodiag d` → the `diagnose` group (so `motodiag d quick ...` works)
- `motodiag k` → the `kb` group (so `motodiag k list`, `motodiag k show 42`)
- `motodiag g` → the `garage` group
- `motodiag q` → the top-level `quick` command (the Phase 125 shortcut itself; now has a shorter alias)

Aliases MUST be hidden from `--help` output (otherwise the help text is cluttered with duplicates). Click's `hidden=True` on the command achieves this — registered aliases get `hidden=True` set at registration time.

### 4. `register_completion(cli_group)` in `cli/completion.py`

The function wires:
- The `completion` subcommand with `bash` / `zsh` / `fish` subcommands (nested group: `motodiag completion bash`).
- The three dynamic completers (as module-level functions that Phase 125's `--bike` options and Phase 124's `code` arg reference via `shell_complete=complete_bike_slug` etc.). The completers are defined in `completion.py`; existing CLI options in `cli/diagnose.py` and `cli/code.py` import and wire them.

Wait — adding `shell_complete=` to existing options requires editing `cli/diagnose.py` and `cli/code.py`. That's fine; small additive change.

The aliases registration happens in `cli/main.py` directly (simpler than a helper function).

### 5. Testing (~18 tests)

- **`TestCompletionCommand`** (5): `completion --help` lists 3 shells; `completion bash` prints non-empty script containing "_MOTODIAG_COMPLETE"; `completion zsh` similar; `completion fish` similar; unknown shell errors cleanly.
- **`TestDynamicCompleters`** (8): `complete_bike_slug` returns matching slugs from garage; returns empty on fresh DB; prefix-filters correctly; case-insensitive match. Same three patterns for `complete_dtc_code` and `complete_session_id`. One test per completer for the "empty DB doesn't crash" case.
- **`TestAliases`** (4): `motodiag d --help` works (diagnose group); `motodiag k list` works (kb); `motodiag g --help` works (garage); `motodiag --help` output does NOT list the short aliases (hidden=True verified).
- **`TestRegistration`** (1): `completion` command registered under `motodiag completion`.

All tests use `cli_db` fixture. Zero AI calls. Zero live tokens.

## Key Concepts
- **Click's completion infrastructure** is battle-tested — we just surface it with a friendlier wrapper and install hints. No reinventing the wheel.
- **Dynamic completers hit the DB** at tab-time. Must be fast (< 100ms typical) so tab-completion feels instant. All three completers are indexed queries — fine at any realistic DB size.
- **Aliases stay hidden from `--help`** so discovery flows through canonical names (`diagnose` / `kb` / `garage` / `quick`). Power users who know the aliases use them; newcomers aren't confused by duplicate help text.
- **Three shells is the 95% coverage set** — bash + zsh cover macOS/Linux defaults, fish covers the power-user crowd. PowerShell completion is a future-phase item if Windows mechanics need it.
- **Completion scripts are stateless** — once installed, they invoke `motodiag` with the magic env var to get completions. No daemon, no cache; each tab-press is a fresh subprocess. Rich's `get_console()` singleton doesn't interfere (completion mode returns raw strings, not Rich output).
- **Defensive DB access in completers**: if `motodiag.db` doesn't exist yet (fresh install, pre-`db init`), completers return `[]`. Tab-completion never crashes the user's shell.

## Verification Checklist
- [ ] `motodiag completion --help` lists 3 shells (bash, zsh, fish)
- [ ] `motodiag completion bash` prints a non-empty script
- [ ] `motodiag completion bash` output contains `_MOTODIAG_COMPLETE` (the magic env var)
- [ ] `motodiag completion zsh` prints a non-empty script
- [ ] `motodiag completion fish` prints a non-empty script
- [ ] `motodiag completion invalid_shell` errors cleanly
- [ ] `complete_bike_slug` returns slugs for seeded garage
- [ ] `complete_bike_slug` on fresh DB returns `[]` without crashing
- [ ] `complete_bike_slug` prefix-filters (input `sport` matches `sportster-2001` only)
- [ ] `complete_dtc_code` returns seeded DTCs
- [ ] `complete_dtc_code` on fresh DB returns `[]`
- [ ] `complete_dtc_code` prefix-filters (input `P0` matches `P0115`, `P0562`)
- [ ] `complete_session_id` returns recent session IDs
- [ ] `complete_session_id` on fresh DB returns `[]`
- [ ] `complete_session_id` prefix-filters (input `1` matches `1`, `10`, `11` etc.)
- [ ] `motodiag d --help` works (resolves to `diagnose`)
- [ ] `motodiag k list` works (resolves to `kb list`)
- [ ] `motodiag --help` does NOT list the short aliases (hidden)
- [ ] `completion` command registered
- [ ] All 2253 existing tests still pass (zero regressions)
- [ ] Zero live API tokens

## Risks
- **Click API drift**: `shell_completion.get_completion_class` is public in Click 8.1+. If Click 9 renames it, our wrapper breaks. Mitigation: the command tolerates `ImportError`/`AttributeError` and falls back to a documented manual-install path. Not in scope for v1 — we assume Click 8.x.
- **Dynamic completer DB latency**: if the DB is on a network mount or otherwise slow, tab-completion feels laggy. Mitigation: each completer has a `LIMIT 20` clause so the worst case is 20 rows fetched per tab-press.
- **Alias collision**: if a future phase adds a command named `d` or `k`, it would shadow the alias. Low risk but noted — aliases should stay stable across phases.
- **Completion scripts + shell quirks**: bash completion requires `bash-completion` package installed on some distros; zsh requires `compinit`; fish is usually fine out of the box. Install hints in the printed script header cover the common cases.
- **`motodiag q` alias vs `motodiag quick` — doubled shortcut**: intentional. `quick` is already a shortcut (Phase 125); `q` is a shortcut-of-a-shortcut for hardcore users. Cheap to add; no downside.
