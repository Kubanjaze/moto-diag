# MotoDiag Phase 126 — Diagnostic Report Output (Export to File)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Add file export to the existing `motodiag diagnose show` command (Phase 123) so mechanics can save a diagnosis report to disk for customer handoff, recordkeeping, or sharing. Supports three text formats: `txt` (plain-text for email/print), `json` (structured for API/integration), `md` (GitHub-flavored markdown). No separate `export` command — extending `diagnose show` keeps the command tree tight:

```
motodiag diagnose show 42                      # unchanged — Rich Panel to terminal
motodiag diagnose show 42 --format json        # print JSON to stdout
motodiag diagnose show 42 --format md --output report.md
motodiag diagnose show 42 --format txt --output /tmp/session-42.txt --yes
```

Pure formatting. No new substrate, no migration, no new package. Extends `cli/diagnose.py`.

## Logic

### 1. New helpers in `cli/diagnose.py`
- Module constants: `_REPORT_FORMAT_VERSION = "1"`, `_TEXT_WRAP_COL = 80`
- 4 private utility helpers:
  - `_short_ts(iso_str)` — format ISO datetime to compact human-readable
  - `_fmt_list(items, prefix)` — bulleted-list formatter for text output
  - `_fmt_conf(confidence)` — format `float | None` as "0.87" or "—"
  - `_write_report_to_file(path, content, overwrite_confirmed)` — UTF-8 + `newline=""`, parent dir auto-create via `os.makedirs(parent, exist_ok=True)`, click.confirm for overwrite unless `overwrite_confirmed=True`, catches PermissionError and IsADirectoryError as ClickException with clear messages
- 3 public-ish formatters (pure `dict → str`):
  - `_format_session_text(session)` — plain-text report. Header block (session ID + status + created), vehicle block, symptoms + fault-codes bulleted lists, diagnosis block with confidence/severity, repair steps numbered. Uses `textwrap.fill(..., subsequent_indent="    ")` for hanging-indent on wrapped bullets so continuation lines align under text rather than under the bullet number. Zero Rich markup, zero ANSI codes.
  - `_format_session_json(session)` — pretty JSON via `json.dumps(indent=2, ensure_ascii=False, default=str)`. `"format_version": "1"` is the FIRST key in the output (ordered dict construction). Full session row preserved; JSON-array fields (symptoms, fault_codes, repair_steps) stay as arrays.
  - `_format_session_md(session)` — GitHub-flavored markdown. `# Session #N`, `## Vehicle`, `## Symptoms` / `## Fault codes`, `## Diagnosis`, `## Repair Steps`, plus a metadata key-value table at the bottom (confidence / severity / model / tokens / created / closed).

### 2. Extended `diagnose show` command
Two new options on the existing callback:
- `--format [terminal|txt|json|md]` default `terminal` (preserves Phase 123 behavior)
- `--output PATH` optional; if given with a non-terminal format, write to file
- `--yes / -y` flag to skip overwrite confirmation

Decision matrix (implemented):
| `--format` | `--output` | Behavior |
|-----------|-----------|----------|
| `terminal` (default) | — | existing Rich Panel to stdout (Phase 123 unchanged, byte-for-byte) |
| `terminal` | PATH | prints **yellow warning** ("terminal format does not support file output"), still renders to stdout, does NOT write file |
| `txt` / `json` / `md` | absent | print formatted string to stdout |
| `txt` / `json` / `md` | PATH | write to file; print `"Saved to PATH"` confirmation |

### 3. File writing
- `os.makedirs(parent, exist_ok=True)` for any missing parent directories
- UTF-8 encoding, `newline=""` on `open()` to avoid Windows CRLF doubling
- Overwrite handling: `click.confirm("Overwrite?")` unless `--yes` flag; `click.Abort()` on decline
- `PermissionError` → `ClickException("Permission denied writing to PATH")`
- `IsADirectoryError` → `ClickException("PATH is a directory")` (also caught upstream by Click's `Path(dir_okay=False)` type)

### 4. Test layout (`tests/test_phase126_report.py` — 22 tests)
- **`TestFormatters`** (10 tests): each formatter with full + minimal session dicts; JSON round-trips through `json.loads`; `format_version` is the first key; markdown contains expected GFM headings; text has no Rich markup; text wraps at 80 cols with hanging indent; missing fields don't crash.
- **`TestDiagnoseShowExport`** (7 tests): txt-to-stdout, json-to-stdout, md-to-file, txt-to-file, missing session errors cleanly, overwrite declined via `click.confirm`, overwrite bypassed via `--yes`.
- **`TestFileWriteErrors`** (3 tests): directory-as-output rejected (Click's built-in + app-level), parent dir auto-created, PermissionError surfaced as ClickException (narrow `builtins.open` patch targeting only the exact output path so SQLite and pytest opens pass through).
- **`TestRegression`** (2 tests): default `diagnose show N` still terminal (Phase 123), `--format terminal --output PATH` warns but doesn't write.

All tests pure-formatting. Zero AI calls, zero mocks needed beyond the narrow `open` patch.

## Key Concepts
- **Three text formats cover the v1 use cases**: `txt` for email/print, `json` for API/integration, `md` for GitHub issues / shop wiki. No PDF yet — that's Phase 132 (export + sharing) + Phase 175 (REST API).
- **Pure formatters over imperative rendering**: each `_format_*` returns a string. The Click command's only job is pick-format + stdout-or-file. Makes unit testing trivial and sets up Phase 132 to reuse formatters for PDF via a markdown → PDF pipeline (Pandoc or WeasyPrint).
- **`--output` is opt-in**: default (no `--output`) prints to stdout. `motodiag diagnose show 42 --format json | jq .diagnosis` works out of the box for shell piping.
- **`format_version` key in JSON**: first key in the output, value `"1"`. Future formatter changes bump this; consumers can reject unknown versions. Intentionally not documented publicly yet — locking the schema waits for Phase 175 REST API.
- **`--format terminal --output PATH` intentionally no-ops the file write**: simpler than using Rich's `console.record + export_text()` and stays inside Phase 123's terminal rendering path unchanged. The warning tells the user to use `txt` instead.
- **No new `export` command**: extending `show` keeps semantic tight. "Show the session, optionally to a file."

## Verification Checklist
- [x] `_format_session_text(full_session)` produces plain-text with all sections, no Rich markup
- [x] `_format_session_json(full_session)` round-trips through `json.loads` with all fields preserved
- [x] `_format_session_json(session)` has `"format_version": "1"` as first key
- [x] `_format_session_md(full_session)` includes `# Session #N`, `## Vehicle`, `## Diagnosis`, `## Repair Steps`
- [x] Formatters handle missing/empty fields without crashing (missing `repair_steps` field, None `confidence`, minimal session dict)
- [x] Text wraps long lines at 80 cols with hanging indent on bullets
- [x] `diagnose show N` (no flags) renders terminal Panel as Phase 123 did
- [x] `diagnose show N --format txt` prints text to stdout
- [x] `diagnose show N --format json` prints JSON to stdout
- [x] `diagnose show N --format md --output report.md` writes file + confirmation
- [x] `diagnose show N --format txt --output report.txt` writes file
- [x] `diagnose show MISSING --format json` exits nonzero with clear error
- [x] Overwrite existing file prompts via `click.confirm`; declining aborts cleanly
- [x] `--yes` flag bypasses the overwrite prompt
- [x] Parent directory auto-created for `--output /tmp/newdir/report.txt`
- [x] Directory-as-output path rejected (Click's built-in Path validator)
- [x] PermissionError surfaced as ClickException
- [x] `--format terminal --output PATH` prints warning, still renders, does NOT write file
- [x] All 2157 existing tests still pass (zero regressions — full suite running)
- [x] Zero live API tokens (none involved — pure formatting)

## Risks (all resolved)
- **Rich markup leaking into text format**: verified via `test_text_has_no_rich_markup` — no `[bold]`, `[red]`, or other markup substrings in the output.
- **JSON schema stability**: `format_version` escape hatch in place. Schema stays private until Phase 175 REST API.
- **Windows line endings**: `newline=""` on open prevents CRLF doubling. All tests run on Windows (project's primary dev platform).
- **Narrow `builtins.open` patch in permission test**: targets only the exact output path, so SQLite and pytest-internal opens pass through untouched. Confirmed by test passing cleanly.

## Deviations from Plan
- **`--format terminal --output PATH` behavior**: plan said "write the Rich rendering using `console.record + export_text`". Builder implemented the simpler path — print warning and do NOT write the file. Rationale: keeps Phase 123's terminal rendering byte-for-byte unchanged, avoids a Rich-recording dependency in tests, and the warning clearly directs users to `--format txt` for that use case. Documented in the decision matrix.
- **4 private utility helpers (`_short_ts`, `_fmt_list`, `_fmt_conf`, `_write_report_to_file`)** not in plan. Natural factoring of shared code across the three formatters.
- **`_write_report_to_file(... overwrite_confirmed=assume_yes)` parameter** — Builder's design: `--yes` maps to `overwrite_confirmed=True`, which bypasses the confirm prompt inside the writer. Cleaner than putting the confirm in the Click callback.
- **Test count 22 vs planned ~20**: extra coverage on `format_version` ordering + minimal-session-round-trips. Natural overcoverage for a format phase.

## Results
| Metric | Value |
|--------|------:|
| Modified files | 2 (`src/motodiag/cli/diagnose.py`, plus new test file) |
| New files | 1 (`tests/test_phase126_report.py`) |
| New tests | 22 |
| Total tests | 2179 passing (was 2157) |
| New formatters | 3 pure `dict → str` functions |
| New CLI options | 3 (`--format`, `--output`, `--yes`) on existing `diagnose show` |
| Production LoC | ~200 added to `cli/diagnose.py` |
| New tables | 0 |
| New migrations | 0 |
| Schema version | 13 (unchanged) |
| Regression status | Zero regressions |
| Live API tokens burned | **0** (pure formatting, no AI involvement) |

Phase 126 is the third Track D UX phase post-retrofit. Builder-A (agent) produced clean code with one small design deviation (the `--format terminal --output PATH` no-op). Architect ran the 22 phase-specific tests before kicking the full regression — standard trust-but-verify per the corrected CLAUDE.md delegation pattern. No AI calls, no mocks beyond a narrow file-write patch. The pure-formatter architecture positions Phase 132 (PDF export) to reuse `_format_session_md` as input to a markdown → PDF pipeline with zero refactoring.
