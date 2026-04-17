# MotoDiag Phase 132 — Export + Sharing (HTML + PDF)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Extend Phase 126's `diagnose show --format` mechanism with `html` and `pdf` output. Also bring `kb show` (Phase 128) to parity with `diagnose show` — adds `--format`/`--output`/`--yes` so a known-issue entry can be exported to md/html/pdf as a customer-facing write-up. No new commands, no migration. Markdown is the pivot format; HTML is markdown + inline CSS; PDF is HTML + page layout.

```
motodiag diagnose show 42 --format html --output report.html
motodiag diagnose show 42 --format pdf --output report.pdf
motodiag kb show 17 --format md --output issue.md
motodiag kb show 17 --format pdf --output known-issue-17.pdf
```

Outputs: new `src/motodiag/cli/export.py` (~260 LoC), extended `cli/diagnose.py` (+~35 LoC for `html`/`pdf` branches), extended `cli/kb.py` (+~100 LoC for `_format_issue_md` + `_format_issue_text` helpers + `--format`/`--output` branching), new `export` optional dep in `pyproject.toml`, 25 new tests.

## Logic

### 1. New `src/motodiag/cli/export.py`
Shared HTML/PDF rendering used by both `diagnose show` and `kb show`.

- `_ensure_markdown_installed() -> module` — lazy-imports `markdown`; raises `ClickException` with `pip install 'motodiag[export]'` hint on ImportError.
- `_ensure_pdf_installed() -> module` — same for `xhtml2pdf.pisa`.
- `_build_html_document(title, body_md) -> str` — wraps markdown-converted HTML in a full `<!DOCTYPE html>` document. Inline CSS: serif `Georgia/"Times New Roman"/serif` font; `@page { size: letter; margin: 1in; }` for print; table `border-collapse` + 1px padding; `<h1>` with underline; `<h2>`/`<h3>` with accent color. Title HTML-entity escaped before insertion (defensive XSS guard, even though input is internal).
- `format_as_html(title, body_md) -> str` — combines ensure + build_document.
- `format_as_pdf(title, body_md) -> bytes` — `format_as_html(...)` → `xhtml2pdf.pisa.CreatePDF(html, dest=BytesIO())`; checks `pisa_status.err` and raises ClickException on conversion failure; returns `.getvalue()`.
- `write_binary(path, data, overwrite_confirmed) -> None` — mirrors Phase 126's `_write_report_to_file` but for bytes. `wb` mode, `os.makedirs(parent, exist_ok=True)`, `click.confirm` overwrite unless `overwrite_confirmed=True`, PermissionError + IsADirectoryError → ClickException.

### 2. `cli/diagnose.py` — extended `diagnose show` (~35 LoC added)
- `--format` Choice expanded from `[terminal|txt|json|md]` to `[terminal|txt|json|md|html|pdf]`.
- New `html` branch: `format_as_html(title=f"Session #{id}", body_md=_format_session_md(session))`. Stdout if no `--output`; text file write via existing `_write_report_to_file` if `--output` given.
- New `pdf` branch: ClickException if no `--output` (binary-to-stdout is useless). `format_as_pdf(...)` → `write_binary(Path(output), bytes, overwrite_confirmed=yes_flag)`. Prints confirmation.

### 3. `cli/kb.py` — extended `kb show` (~100 LoC added)
- New `_format_issue_md(row) -> str` helper: `# {title}` + sections for Overview (year range + severity + make/model), Description, Symptoms (bulleted), Fault Codes (bulleted), Causes (bulleted), Fix Procedure (paragraph), Parts Needed (bulleted), Labor Hours (if set). All sections sparse-field-tolerant — None/empty lists skip the section entirely.
- New `_format_issue_text(row) -> str` — aliased to `_format_issue_md` per plan's "acceptable for v1" note. Separate text-strip implementation deferred.
- `kb show` gains `--format [terminal|txt|md|html|pdf]` default `terminal`, `--output PATH`, `--yes`. Branches:
  - `terminal` (default): Phase 128's `_render_issue_detail` unchanged.
  - `txt` / `md`: write via `_write_report_to_file` (re-imported from `cli.diagnose` to keep one implementation of the file-safety handling).
  - `html` / `pdf`: route through `cli.export.format_as_html` / `format_as_pdf` + `write_binary`.
  - `pdf` without `--output`: ClickException.

### 4. `pyproject.toml`
- Added `export = ["markdown>=3.5", "xhtml2pdf>=0.2.13"]` to `[project.optional-dependencies]`.
- Added `export` to the `all` extras alias.

### 5. Testing (25 tests across 6 classes)
- `TestExportHelpers` (6): HTML structure (doctype + title + h1 + body); markdown tables → `<table>`; ClickException on missing `markdown` (via monkeypatch); PDF starts with `%PDF-` magic bytes; ClickException on missing `xhtml2pdf`; `write_binary` handles bytes + parent-dir + overwrite + permission.
- `TestDiagnoseShowHtml` (4): html-to-stdout starts with `<!DOCTYPE`; html-to-file writes + confirms; html contains diagnosis text; html contains vehicle header.
- `TestDiagnoseShowPdf` (4): missing `--output` errors cleanly; file write produces bytes; PDF starts with `%PDF-`; `--yes` skips overwrite prompt.
- `TestKbShowFormats` (5): terminal default unchanged (Phase 128 regression); `--format md --output` writes; html to stdout; pdf to file; pdf without output errors.
- `TestRegression` (3): Phase 126 formats (txt/json/md/terminal) still work; Phase 128 kb-show terminal default unchanged; missing session/issue errors unchanged.
- `TestExtrasAvailable` (3): `markdown` importable, `xhtml2pdf.pisa` importable, `pyproject.toml` has `export` extras entry.

Seeds sessions via `create_session`/`set_diagnosis`/`close_session`; seeds known_issues via `add_known_issue`. ImportError simulations use `monkeypatch.setitem(sys.modules, "markdown", None)`. All tests use `cli_db` fixture. Zero AI calls.

## Key Concepts
- **Markdown is the pivot format**: Phase 126's `_format_session_md` and the new `_format_issue_md` are the single source of truth. HTML is markdown + CSS; PDF is HTML + page layout. Any future format (DOCX, EPUB) hooks in at the same pivot.
- **Optional dep via extras**: `motodiag[export]` installs both `markdown` and `xhtml2pdf`. Default install doesn't carry this weight. Install-hint message on ImportError points to the exact `pip install` command.
- **PDF requires `--output`**: binary-to-stdout is useless. CLI errors clearly. Contrast with HTML which is human-pipeable (`... --format html | open -a Safari`).
- **`xhtml2pdf` chosen over `weasyprint`**: pure Python, cross-platform, no native Cairo/Pango dep. WeasyPrint would be nicer typographically but costs ~100 MB of native libs on Windows — not worth the friction for a diagnostic-report use case. If customer feedback demands prettier PDFs, a future phase can add a `--engine weasyprint` flag.
- **Inline CSS**: self-contained HTML — email attachments render without external stylesheets.
- **Sharing = file output**: mechanic emails the PDF or prints it. No URL shorteners, no upload services in v1. Track I mobile can add native-share integration later.
- **`kb show` parity with `diagnose show`**: same `--format`/`--output`/`--yes` surface, same terminal default, same binary PDF requires-output rule. Consistent mental model across commands.
- **`_format_issue_text` aliases `_format_issue_md` (v1)**: acceptable per plan. A future phase can implement true markdown-stripping if customer feedback demands plain-text-without-markup. Most mechanics emailing a text report are fine with markdown.
- **XSS defensive HTML-entity escape on title**: title comes from internal session/issue data, not user input at render time — risk is near-zero, but the escape is cheap insurance.

## Verification Checklist
- [x] `pyproject.toml` has `export = ["markdown>=3.5", "xhtml2pdf>=0.2.13"]` in optional-dependencies
- [x] `export` included in `all` extras alias
- [x] `format_as_html(title, body_md)` returns a full `<!DOCTYPE html>...</html>` document
- [x] `format_as_html` converts GFM markdown tables to `<table>` tags
- [x] `format_as_html` raises ClickException with install hint when markdown missing
- [x] `format_as_pdf(title, body_md)` returns bytes starting with `%PDF-`
- [x] `format_as_pdf` raises ClickException with install hint when xhtml2pdf missing
- [x] `write_binary` handles overwrite, parent-dir auto-create, and permission errors
- [x] `diagnose show N --format html` prints HTML to stdout
- [x] `diagnose show N --format html --output PATH` writes file
- [x] `diagnose show N --format pdf` without `--output` exits 1 with clear error
- [x] `diagnose show N --format pdf --output PATH` writes PDF bytes
- [x] PDF output starts with `%PDF-` magic number
- [x] HTML output contains vehicle + diagnosis text
- [x] `kb show N --format html` prints HTML
- [x] `kb show N --format md --output PATH` writes markdown
- [x] `kb show N --format pdf --output PATH` writes PDF
- [x] `kb show N --format pdf` without `--output` errors cleanly
- [x] Phase 126 `diagnose show --format txt/json/md/terminal` still works (regression)
- [x] Phase 128 `kb show` terminal-default still renders Rich Panel (regression)
- [x] Missing session/issue errors unchanged
- [x] `markdown` package importable in test venv
- [x] `xhtml2pdf.pisa` importable in test venv
- [x] `export` extras readable via `tomllib`
- [x] All 2301 existing tests still pass (zero regressions — full suite running)
- [x] Zero live API tokens burned (pure formatting)

## Risks (all resolved)
- **`xhtml2pdf` HTML coverage is limited** (no flexbox, limited CSS3). Accepted — our CSS is deliberately simple (font, margins, table borders, `@page`).
- **Optional-dep install friction**: mechanics who try `--format pdf` without installing `[export]` get a clear ClickException with the exact `pip install` command. Documented.
- **PDF generation latency (~1-2s)**: on-demand export, not a batch tool. Acceptable.
- **Regression on Phase 126 `--format` Choice expansion**: tests cover; no existing test asserted against the exact valid-choices list.
- **Sparse kb entry layout (empty parts list, no estimated_hours)**: `_format_issue_md` skips empty sections entirely. Tested.

## Deviations from Plan
- **`_format_issue_text` aliases `_format_issue_md`**: plan explicitly allowed "acceptable for v1" — Builder took that route. Documented.
- **Re-imports `_write_report_to_file` from `cli/diagnose.py`** in `cli/kb.py` for text/md output: keeps a single implementation of the overwrite/parent-dir/permission safety net rather than duplicating. Minor coupling between the two CLI modules, but the alternative was duplicate code.
- **HTML-entity escape on title in `_build_html_document`**: defensive, not in plan. Titles come from internal session/issue data so XSS risk is negligible, but the escape costs nothing and prevents future bugs if titles ever become user-controlled.
- **Unused-import cleanup in test file during build**: removed unused `sys`, `patch`, private helper imports after initial write. Normal hygiene.

## Results
| Metric | Value |
|--------|------:|
| New files | 2 (`src/motodiag/cli/export.py`, `tests/test_phase132_export.py`) |
| Modified files | 3 (`pyproject.toml`, `src/motodiag/cli/diagnose.py`, `src/motodiag/cli/kb.py`) |
| New tests | 25 |
| Total tests | 2326 passing (was 2301) |
| New extras | 1 (`motodiag[export]` = markdown + xhtml2pdf) |
| New CLI formats | 2 (`html`, `pdf`) on 2 commands (`diagnose show` + `kb show`) |
| New CLI commands | 0 |
| Migration | None |
| Schema version | 15 (unchanged) |
| Regression status | Zero regressions (pending — full suite running) |
| Live API tokens burned | **0** (pure formatting, no AI involvement) |

Eighth agent-delegated phase. Builder-A shipped 25 tests all passing first run (11.94s) — zero iterative fixes, zero Architect corrections during trust-but-verify. The markdown-as-pivot architecture holds: `_format_session_md` (Phase 126) and the new `_format_issue_md` are the single source of truth; HTML and PDF are downstream renderings of the same text. Any future format (DOCX, EPUB, `.rtf`) plugs in at the same pivot. Track D's user-facing feature set is now effectively complete — Phase 133 is the Gate 5 integration test that validates the whole workflow end-to-end.
