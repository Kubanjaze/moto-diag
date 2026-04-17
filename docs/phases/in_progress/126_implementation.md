# MotoDiag Phase 126 — Diagnostic Report Output (Export to File)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Add file export to the existing `motodiag diagnose show` command (Phase 123) so mechanics can save a diagnosis report to disk for customer handoff, recordkeeping, or sharing. Supports three formats:

- `txt` — plain-text report suitable for email / printing (no Rich markup)
- `json` — structured JSON (full session row + all fields) for programmatic use or API upload
- `md` — GitHub-flavored markdown with tables for humans + machines

No separate `export` command — extending `diagnose show` keeps the UX tight:

```
motodiag diagnose show 42                      # current behavior — render to terminal
motodiag diagnose show 42 --format json        # print JSON to stdout
motodiag diagnose show 42 --format md --output report.md
motodiag diagnose show 42 --format txt --output /tmp/session-42.txt
```

Pure formatting. No new substrate, no migration, no new package. Extends `cli/diagnose.py`.

## Logic

### 1. New helpers in `cli/diagnose.py`

- `_format_session_text(session: dict) -> str` — plain-text report. Header block (session ID, status, date), vehicle block, symptoms + fault codes list, diagnosis block with confidence/severity, bulleted repair steps. No Rich markup, no ANSI codes. Lines wrapped at 80 cols.
- `_format_session_json(session: dict) -> str` — JSON-serialized session dict. Handles the `symptoms`, `fault_codes`, `repair_steps` JSON-array fields (already deserialized by session_repo); outputs pretty-printed JSON with 2-space indent. Include a top-level `"format_version": "1"` key for future schema evolution.
- `_format_session_md(session: dict) -> str` — GitHub-flavored markdown. Heading for session, vehicle info as key-value list, symptoms/fault codes as bulleted lists, diagnosis as paragraph + metadata table (confidence | severity | model | tokens), repair steps as numbered list, footer with created/closed timestamps.

Each formatter is pure: `dict in → str out`. Testable without file I/O.

### 2. Extended `diagnose show` command

Add two new options:
- `--format [terminal|txt|json|md]` default `terminal` (preserves Phase 123 behavior)
- `--output PATH` optional; if given with a non-`terminal` format, write to file instead of stdout

Decision matrix:
| `--format` | `--output` | Behavior |
|-----------|-----------|----------|
| `terminal` (default) | — | existing Rich Panel output (Phase 123 unchanged) |
| `terminal` | (ignored with warning) | write the Rich rendering using `console.record` + `console.export_text` |
| `txt` / `json` / `md` | absent | print formatted string to stdout |
| `txt` / `json` / `md` | PATH | write to file; print `"Saved to PATH"` confirmation |

### 3. File writing

- `--output` accepts a path string. If the file exists, confirm overwrite with `click.confirm` (unless `--yes` flag — added).
- Parent dir created with `os.makedirs(parent, exist_ok=True)` if needed.
- UTF-8 encoding, `newline=""` on open to avoid Windows CRLF doubling.
- Error handling: `PermissionError` → ClickException with clear message; `IsADirectoryError` → ClickException.

### 4. Testing (~20 tests)

- **`TestFormatters`** (9 tests): each formatter (`txt`, `json`, `md`) with full/minimal session dicts; `json` round-trips through `json.loads`; `md` contains expected section headers; `txt` has no Rich markup characters; empty fields handled gracefully (no crash on missing `repair_steps`).
- **`TestDiagnoseShowExport`** (6 tests): `--format txt` to stdout, `--format json --output PATH`, `--format md --output PATH`, existing terminal behavior unchanged, overwrite confirmation with `--yes`, unknown session ID errors cleanly.
- **`TestFileWriteErrors`** (3 tests): PermissionError surfaced as ClickException, directory-as-path error, parent directory auto-created.
- **`TestRegression`** (2 tests): `diagnose show N` default still terminal, Phase 123 rendering unchanged.

All tests in `tests/test_phase126_report.py`. No AI calls needed — pure formatting. Zero live tokens (none would be burned anyway).

## Key Concepts
- **Three text formats cover the use cases**: `txt` for email/print, `json` for API/integration, `md` for GitHub issues / shop wiki. No PDF yet — that's Track I mobile app + Phase 132's job (export + sharing).
- **Pure formatters over imperative rendering**: each `_format_*` function returns a string. The Click command's only job is pick-format + stdout-or-file. Makes unit testing trivial and sets up Phase 132 to reuse formatters for customer-facing PDF via a markdown → PDF pipeline.
- **`--output` is opt-in**: default (no `--output`) prints to stdout for all non-terminal formats. Means `motodiag diagnose show 42 --format json | jq .diagnosis` works out of the box for shell piping.
- **Format version in JSON**: `"format_version": "1"` at the top. Future formatter changes bump this; consumers can reject unknown versions.
- **No new `export` command**: extending `show` keeps the command tree shallow and the semantic is clear ("show the session, optionally to a file").

## Verification Checklist
- [ ] `_format_session_text(full_session)` produces plain-text report with no Rich markup
- [ ] `_format_session_json(full_session)` round-trips through json.loads with all fields preserved
- [ ] `_format_session_json(session)` includes `"format_version": "1"` at top level
- [ ] `_format_session_md(full_session)` includes expected GFM headings (`# Session #N`, `## Vehicle`, `## Diagnosis`, `## Repair Steps`)
- [ ] Formatters handle missing/empty fields without crashing (empty `repair_steps`, None confidence, missing `fault_codes`)
- [ ] `diagnose show N` (no flags) renders terminal Panel as before (Phase 123 regression)
- [ ] `diagnose show N --format txt` prints text to stdout
- [ ] `diagnose show N --format json` prints JSON to stdout
- [ ] `diagnose show N --format md --output report.md` writes file, prints confirmation
- [ ] `diagnose show MISSING --format json` exits nonzero with clear error
- [ ] Overwrite existing file: prompts for confirmation (or `--yes` skips)
- [ ] Parent directory auto-created for `--output /tmp/newdir/report.txt`
- [ ] `PermissionError` surfaces as ClickException with clear message
- [ ] Directory-as-output path errors cleanly
- [ ] All 2157 existing tests still pass (zero regressions)
- [ ] Zero live API tokens (none involved)

## Risks
- **Markdown table alignment quirks**: GFM tables require consistent column widths or some renderers choke. Mitigated by using simple key-value lists + one metadata table; formatter uses `rich.table` for terminal but hand-rolled markdown for the `md` export.
- **Text wrapping at 80 cols**: Python's `textwrap.fill` handles this fine. Risk: long repair-step bullets may wrap weirdly. Acceptable; mechanics can read it.
- **JSON schema stability**: once consumers depend on the shape, we can't change it freely. `format_version` gives us an escape hatch; we just don't publicly document the schema until Phase 175 (REST API) stabilizes it.
- **Windows line endings**: `newline=""` on `open()` prevents CRLF doubling. Tested via CI on Windows (the project's primary dev platform).
