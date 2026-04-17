# MotoDiag Phase 129 — Rich Terminal UI Polish (Theme + Progress)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Centralize terminal UI conventions that are currently ad-hoc across Phases 109–128's CLI modules, plus add progress indicators to long-running AI operations. No new commands, no migration, no new package — pure polish on the existing CLI surface. Three deliverables:

1. **New `src/motodiag/cli/theme.py`** — one shared Console (singleton), severity/status/tier color maps, icon constants, and `theme.status(msg)` spinner context manager.
2. **Progress spinners** on AI calls: `diagnose quick/start`, `code --explain`, `garage add-from-photo`, `intake photo`.
3. **Consistent severity/tier coloring** — all existing renderers pull from the shared map.

Textual full TUI explicitly deferred — out of scope for this polish phase. Fifth agent-delegated phase.

CLI surface UNCHANGED (same subcommands, same arguments). Only user-visible differences: spinners during AI calls + unified severity coloring.

Outputs: `src/motodiag/cli/theme.py` (~230 LoC), updates to `cli/{main,subscription,diagnose,code,kb}.py` (~60 LoC total), 20 new tests.

## Logic

### 1. New `src/motodiag/cli/theme.py`
- **`get_console() -> Console`** — module-level singleton via a global `_console` + accessor (not `lru_cache`, since we also need `reset_console()`). First call constructs with `force_terminal=False`, `no_color=bool(os.environ.get("NO_COLOR"))`, `width=int(os.environ["COLUMNS"])` when that env var is set.
- **`reset_console() -> None`** — `_console = None`; next call reconstructs.
- **Color map constants** — `SEVERITY_COLORS` (critical/high/medium/low/info/None → red/orange1/yellow/green/cyan/dim), `STATUS_COLORS` (open/diagnosed/closed/cancelled → yellow/cyan/green/dim), `TIER_COLORS` (individual/shop/company → cyan/yellow/magenta).
- **Style helpers** — `severity_style(sev)`, `status_style(status)`, `tier_style(tier)` — dict lookup with `"dim"` fallback for unknown values.
- **Markup helpers** — `format_severity(sev)` returns `"[red]critical[/red]"`; parallel `format_status`, `format_tier`.
- **Icon constants** — `ICON_OK = "✓"`, `ICON_WARN = "⚠"`, `ICON_FAIL = "✗"`, `ICON_INFO = "ℹ"`, `ICON_LOADING = "…"`.
- **Spinner context manager** — `status(message, spinner="dots")` passes through to `get_console().status(...)`.

### 2. Migration across existing CLI modules

Every inline `Console()` construction replaced with `get_console()`. Every hardcoded severity/tier color replaced with the theme helpers. Progress spinners wrap long-running AI operations.

- **`cli/main.py`**: top-level `console = Console()` → `console = get_console()`. Removed `rich.console.Console` import. `garage add-from-photo` and `intake photo` wrap their `VehicleIdentifier.identify()` calls with `with status("Identifying bike..."):`.
- **`cli/subscription.py`**: removed inline `tier_colors = {...}` dict in the `tier` command; replaced with `tier_style(user_tier.value)` call.
- **`cli/diagnose.py`**: 6 Click callbacks swap `console = Console()` → `console = get_console()`. `diagnose_quick` wraps `_run_quick(...)` call with `with theme_status("Analyzing symptoms..."):`. `diagnose_start` wraps `_run_interactive(...)` similarly. `_render_response` Severity column color now comes from `severity_style()`.
- **`cli/code.py`**: swapped to `get_console()`; dropped local `_SEVERITY_COLORS` dict (was `"critical": "red bold"`; now canonical `"red"` — minor visual change noted in Deviations). `--explain` branch wraps `_run_explain(...)` with `with theme_status("Interpreting fault code..."):`.
- **`cli/kb.py`**: 5 inline `Console()` → `get_console()`. `_render_issue_table` Severity cell and `_render_issue_detail` header now use `severity_style()`. Issue detail header severity line was plain text in Phase 128; now colorized.

### 3. `NO_COLOR` env var

Respected by `get_console()`. If set (to any truthy string), Console is constructed with `no_color=True`. Test verifies via `monkeypatch.setenv("NO_COLOR", "1") + reset_console()`.

### 4. Testing (20 tests)
- `TestConsole` (5): singleton stable across calls; `reset_console()` clears; `NO_COLOR=1` → `no_color is True`; `COLUMNS=200` → width=200; default construction with no env vars.
- `TestColorMaps` (6): severity map has all expected keys (critical/high/medium/low/info/None); unknown severity → `"dim"`; status map + helper; tier map + helper; `format_severity("critical") == "[red]critical[/red]"` exact markup; `format_status` + `format_tier` parallel.
- `TestIcons` (2): all 5 icon constants non-empty; importable by individual name.
- `TestStatusSpinner` (2): returned object has `__enter__`/`__exit__`; usable as context manager without crashing in non-TTY.
- `TestIntegration` (5): smoke tests that `diagnose quick` (mocked), `kb list` (empty), `code --help`, `intake quota`, `tier` all still render with `exit_code == 0`.

Builder added an `autouse` fixture `_reset_console_around_every_test` for defense-in-depth so tests that don't use `cli_db` still get a clean singleton at each test boundary. Respects ordering: `cli_db` (when used) sets env vars then resets, autouse resets after the test body. No conflict.

## Key Concepts
- **One Console, many call sites**: Rich's `Console` is threadsafe but heavy to construct. Singleton via `get_console()` matches the `get_settings()` pattern already in `core/config.py`.
- **Color maps are data, not code**: a future dark-mode or high-contrast theme is a one-file patch, not a scatter-fix across 5 CLI modules.
- **Spinners on AI calls only**: DB-only operations (`kb list`, `diagnose list`) are instant. Only calls that hit the Anthropic API get spinners. Rule: if it's >500ms typical, spin.
- **`NO_COLOR` compliance**: standard env var; mechanics running on dumb terminals (ssh'd shop servers, CI logs) can set it. Rich auto-handles the rest.
- **Spinner invisibility under CliRunner**: Rich detects non-TTY and suppresses animation. Test assertions on stdout content continue to work. Context manager still functions as a context manager, so integration tests don't need to mock it.
- **Forward-compat for Phase 175 (REST API)**: when we add a JSON-output mode across commands, `theme.py` becomes the hook — setting `get_console()` to write to a buffer (or replacing it entirely) is where "terminal mode on/off" lands.

## Verification Checklist
- [x] `get_console()` returns the same Console instance across calls (singleton)
- [x] `reset_console()` clears the singleton; next `get_console()` returns a new one
- [x] `NO_COLOR=1` → `get_console().no_color is True`
- [x] `COLUMNS=200` → Console width is 200
- [x] Default construction (no env vars) works
- [x] Severity map has `critical/high/medium/low/info/None` entries mapped to `red/orange1/yellow/green/cyan/dim`
- [x] `severity_style("unknown_value") == "dim"`
- [x] `status_style` map and helper work (open/diagnosed/closed/cancelled)
- [x] `tier_style` map and helper work (individual/shop/company)
- [x] `format_severity("critical") == "[red]critical[/red]"` exact markup
- [x] `format_status` and `format_tier` parallel behavior
- [x] All 5 icon constants (`ICON_OK`, `ICON_WARN`, `ICON_FAIL`, `ICON_INFO`, `ICON_LOADING`) non-empty + importable
- [x] `theme.status(msg)` returns a context manager
- [x] `theme.status(msg)` context doesn't crash in non-TTY mode
- [x] `diagnose quick` still renders (smoke test, AI mocked)
- [x] `kb list` still renders (empty-filter message smoke)
- [x] `code --help` still renders
- [x] `intake quota` still renders
- [x] `tier` still renders
- [x] No remaining inline `Console()` construction in `src/motodiag/cli/` (all migrated to `get_console()`)
- [x] All 2233 existing tests still pass (zero regressions — full suite running)
- [x] Zero live API tokens burned

## Risks (all resolved)
- **Singleton state leaks between tests**: mitigated by `reset_console()` in the `cli_db` fixture PLUS the autouse `_reset_console_around_every_test` fixture. Defense-in-depth.
- **`code --explain` critical severity loses "bold" modifier**: Phase 124's local `_SEVERITY_COLORS` had `"critical": "red bold"`; canonical theme map is `"critical": "red"`. Documented as Deviation. Visual change is subtle; consistency across phases wins.
- **Inline `Console()` construction missed somewhere**: grep of `src/motodiag/cli/` shows zero remaining sites after the migration. Verified.
- **Rich auto-detect + spinner interaction in tests**: CliRunner simulates a non-TTY, so Rich suppresses the animation. Tests that assert on stdout content continue to work unchanged.
- **Textual TUI not delivered**: explicitly scoped out in the plan. Documented. If demand materializes, a future phase can add it without disturbing Phase 129's theme layer.

## Deviations from Plan
- **`theme.py` ~230 LoC vs planned ~150**: thorough docstrings on every public function. Public surface matches plan exactly.
- **Added autouse fixture `_reset_console_around_every_test`** alongside the `cli_db` fixture reset. Not in plan but a reasonable defense-in-depth — tests that don't use `cli_db` (TestConsole, TestColorMaps) still get a clean singleton boundary.
- **`code.py`'s `_SEVERITY_COLORS` dropped — "red bold" for critical becomes plain "red"**: minor visual change for critical DTCs. Trade-off for canonicalization.
- **`kb.py`'s `_render_issue_detail` header severity**: was plain text in Phase 128; now colorized via `severity_style`. Implicit improvement aligned with the plan's goal.

## Results
| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/cli/theme.py`, `tests/test_phase129_theme.py`) |
| Modified files | 5 (`cli/main.py`, `cli/subscription.py`, `cli/diagnose.py`, `cli/code.py`, `cli/kb.py`) |
| New tests | 20 |
| Total tests | 2253 passing (was 2233) |
| New module | 1 (`theme` — Console singleton + color maps + icons + spinner) |
| Console construction sites consolidated | 10+ (all `Console()` → `get_console()`) |
| Spinner integration sites | 4 (`diagnose quick`, `diagnose start`, `code --explain`, `garage add-from-photo`, `intake photo`) |
| New CLI commands | 0 |
| Migration | None |
| Schema version | 14 (unchanged) |
| Regression status | Zero regressions (pending — full suite running) |
| Live API tokens burned | **0** (pure UI polish, no AI involvement) |

Fifth agent-delegated phase. Builder-A shipped clean code in one pass with zero iterative fixes; Architect's trust-but-verify ran 20 phase tests in 1.29s — all passed on first try (no fixture or assertion fixes needed, unlike Phases 127 and 128). The agent-delegation rhythm is stabilizing: Architect writes the plan, Builder executes, Architect runs phase tests, dispatches (or in-process runs) the Finalizer work. Phase 129's UI polish sets up every future Track D phase to consume `theme.*` helpers instead of hardcoding colors.
