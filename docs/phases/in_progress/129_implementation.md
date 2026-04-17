# MotoDiag Phase 129 — Rich Terminal UI Polish (Theme + Progress)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Centralize terminal UI conventions that are currently ad-hoc across Phases 109–128's CLI modules, plus add progress indicators to the long-running AI operations. No new commands, no migration, no new package — this phase is pure polish on the existing CLI surface. Three concrete deliverables:

1. **New `src/motodiag/cli/theme.py`** — one shared Console, one severity/status/tier color map, one icon map, and a `NO_COLOR` env-var respect helper. All existing CLI modules migrate from `Console()` local construction to `get_console()`.
2. **Progress spinners** on long-running AI calls: `with theme.status("Analyzing symptoms...")` wraps `diagnose quick` / `diagnose start` / `intake photo` / `code --explain` API invocations so the user sees something's happening during the 3-10 second AI wait.
3. **Consistent severity/status/tier colors** — every existing renderer that prints severity or tier gets its color from the shared map (not inline `style="red"`), so a future theme swap is one-line.

No textual TUI in this phase — `textual` full-TUI is a large effort and doesn't fit the "polish" scope. Noted in ROADMAP for a future phase if demand materializes.

CLI surface is UNCHANGED. Every test that passes today continues to pass; the only user-visible differences are:
- Spinners during AI calls (visible in real use, mostly transparent to test runs via CliRunner)
- Consistent color conventions across all existing tables/panels

Outputs: `src/motodiag/cli/theme.py` (~150 LoC), updates to `cli/code.py` / `cli/diagnose.py` / `cli/kb.py` / `cli/main.py` / `cli/subscription.py` (~20 LoC each to swap Console construction + adopt theme helpers), ~20 new tests. **No migration.**

## Logic

### 1. New `src/motodiag/cli/theme.py`

**Module-level public surface:**

- `get_console() -> Console` — returns a singleton Console. First call constructs with:
  - `force_terminal=False` (respect CliRunner's capture behavior in tests)
  - Respects `NO_COLOR` env var (per https://no-color.org/): if set to any value, construct Console with `no_color=True`
  - Default width from `COLUMNS` env var if set; otherwise Rich's auto-detection
- `reset_console() -> None` — clears the singleton (for tests that need a fresh console, analogous to `reset_settings()`)

**Color map constants:**

```python
SEVERITY_COLORS = {
    "critical": "red",
    "high":     "orange1",
    "medium":   "yellow",
    "low":      "green",
    "info":     "cyan",
    None:       "dim",
}
STATUS_COLORS = {
    "open":       "yellow",
    "diagnosed":  "cyan",
    "closed":     "green",
    "cancelled":  "dim",
}
TIER_COLORS = {
    "individual": "cyan",
    "shop":       "yellow",
    "company":    "magenta",
}
```

**Helper functions:**

- `severity_style(severity: str | None) -> str` — returns the rich style string for a severity; falls back to `"dim"` for unknown values.
- `status_style(status: str | None) -> str` — same for session status.
- `tier_style(tier: str | None) -> str` — same for subscription tier.
- `format_severity(severity: str | None) -> str` — returns `"[red]critical[/red]"` markup-string (for inline use in panels).
- `format_status(status)` / `format_tier(tier)` — parallel markup helpers.

**Icons:**

```python
ICON_OK      = "✓"
ICON_WARN    = "⚠"
ICON_FAIL    = "✗"
ICON_INFO    = "ℹ"
ICON_LOADING = "…"
```

Centralized so a future theme change is one file, and so Windows-console tests can override via monkeypatch if needed.

**Progress spinner helper:**

```python
def status(message: str, spinner: str = "dots"):
    """Context manager wrapping console.status().

    Usage:
        with theme.status("Analyzing symptoms..."):
            response, usage = diagnose_fn(...)
    """
    return get_console().status(message, spinner=spinner)
```

### 2. Integration into existing CLI modules

Each existing CLI module loses its `console = Console()` local construction and gains `from motodiag.cli.theme import get_console, status, severity_style, format_severity`. Call sites:

- **`cli/main.py`**: top-level `console = Console()` → `console = get_console()` (lazy). `_show_welcome` unchanged visually.
- **`cli/subscription.py`**: the `tier` command uses inline tier-color lookup. Replace with `tier_style(user_tier.value)` helper.
- **`cli/diagnose.py`**: 6 inline `console = Console()` in Click callbacks → all replaced with `get_console()`. `diagnose quick` and `diagnose start` wrap their `_run_quick` / `_run_interactive` calls with `theme.status("Analyzing symptoms...")`. The `_render_response` function uses `severity_style` for the Severity column instead of hardcoded `"red"`.
- **`cli/code.py`**: `console = Console()` → `get_console()`. `code --explain` wraps the `_run_explain` call with `theme.status("Interpreting fault code...")`.
- **`cli/kb.py`**: 3 inline `Console()` → `get_console()`. Issue tables use `severity_style` for the Severity column.
- **`cli/intake/...`** via `cli/main.py`'s garage commands: the `garage add-from-photo` and `intake photo` commands wrap their `VehicleIdentifier.identify()` calls with `theme.status("Identifying bike...")`.

### 3. `NO_COLOR` env var

Respected by `get_console()` — if `NO_COLOR` is set (to any truthy string), Console is constructed with `no_color=True`. Tests verify via `monkeypatch.setenv("NO_COLOR", "1")` + checking `get_console().no_color is True`.

### 4. Testing (~20 tests)

- **`TestConsole`** (5): `get_console()` returns singleton; `reset_console()` resets; `NO_COLOR` env var disables color; `COLUMNS` env var sets width; `force_terminal=False` keeps CliRunner happy.
- **`TestColorMaps`** (6): `severity_style("critical") == "red"`; unknown severity → `"dim"`; parallel tests for status and tier; `format_severity("critical")` returns `"[red]critical[/red]"` markup.
- **`TestIcons`** (2): all 5 icon constants exported; icons are single-character unicode strings.
- **`TestStatusSpinner`** (2): `theme.status(msg)` returns a context manager; entering/exiting doesn't crash.
- **`TestIntegration`** (5): existing CLI commands still render (happy-path smoke tests for diagnose quick, kb list, code P0115, intake quota, tier) — proves the Console swap didn't break anything.

All existing phase-specific test suites (Phases 109-128) should continue to pass without modification. If any test asserts on exact color strings (e.g., `"red"` in output), that assertion stays valid because the severity→color mapping preserves red for critical.

## Key Concepts
- **One Console, many call sites**: Rich's `Console` is threadsafe but heavy to construct. Singleton via `get_console()` matches how `get_settings()` works in `core/config.py` — same pattern the project already uses.
- **Color maps are data, not code**: storing severity→color in a dict means a future dark-mode or high-contrast theme is a 5-line patch. Contrast that with the current pattern where `"red"` is scattered across renderers.
- **Spinners on AI calls only**: DB-only operations (kb list, diagnose list) are instant. Only the calls that hit the Anthropic API get spinners. Rule: if it's >500ms typical, spin.
- **`NO_COLOR` compliance**: standard env var that mechanics running on dumb terminals (ssh'd shop servers) can set. Free-ish to add; nice to have.
- **No new commands**: the phase is pure polish. Discovery via `--help` is unchanged.
- **Testability**: spinners are invisible under CliRunner (Rich detects non-TTY and suppresses animation). The context manager still works as a context manager, so no test needs to mock it.
- **Forward-compat for Phase 175 (REST API)**: when we eventually add a JSON output mode across every command, the theme module becomes the place where "terminal mode on/off" is decided. Setting `get_console()` to write to a buffer is the hook Phase 175 will use.

## Verification Checklist
- [ ] `get_console()` returns the same Console instance across calls (singleton)
- [ ] `reset_console()` clears the singleton; next `get_console()` returns a new one
- [ ] `NO_COLOR=1` → `get_console().no_color is True`
- [ ] `COLUMNS=200` → Console width is 200
- [ ] `severity_style("critical")` == `"red"`; `"high"` → `"orange1"`; `"medium"` → `"yellow"`; `"low"` → `"green"`; None → `"dim"`
- [ ] `status_style("open")` → `"yellow"`; `"closed"` → `"green"`
- [ ] `tier_style("individual")` → `"cyan"`; `"shop"` → `"yellow"`; `"company"` → `"magenta"`
- [ ] `format_severity("critical")` returns `"[red]critical[/red]"` with square-bracket markup
- [ ] `format_status` and `format_tier` parallel behavior
- [ ] 5 icon constants defined (`ICON_OK`, `ICON_WARN`, `ICON_FAIL`, `ICON_INFO`, `ICON_LOADING`)
- [ ] `theme.status(msg)` returns a usable context manager
- [ ] `theme.status(msg)` context doesn't crash in non-TTY mode (CliRunner test)
- [ ] All existing CLI modules swap `Console()` construction for `get_console()` (no remaining inline `Console()` calls in `cli/`)
- [ ] `diagnose quick` still renders correctly (smoke test)
- [ ] `kb list` still renders correctly (smoke test)
- [ ] `code P0115` still renders correctly
- [ ] `intake quota` still renders correctly
- [ ] `tier` still renders correctly
- [ ] All 2233 existing tests still pass (zero regressions)
- [ ] Zero live API tokens burned

## Risks
- **Singleton reuse across tests** could leak state between tests (e.g., `NO_COLOR` set in one test bleeds into the next). Mitigated by `reset_console()` in the existing `cli_db` fixture pattern — any test that cares about Console config resets it.
- **Color constants may not be portable** across terminal emulators. Rich handles this automatically (falls back to 16-color on terminals without truecolor support). If a future test needs exact-color output, use Rich's `capture` mode.
- **Migrating 10+ inline `Console()` call sites** is a lot of mechanical editing. Risk of a missed site is low (grep is authoritative) but the patch touches 5 CLI files. Test coverage catches any callable break.
- **Spinners in CliRunner**: some tests that assert on exact stdout content may see the ephemeral spinner output. Mitigated — Rich auto-detects non-TTY and prints nothing animated in that mode. If a specific test breaks, the fix is to use `CliRunner(mix_stderr=False)` and assert on stdout only.
- **`Textual` TUI not implemented**: plan explicitly defers. Acceptable — the phase title was "Rich terminal UI (tables, colors, progress)" and we delivered that; full TUI is a different beast.
