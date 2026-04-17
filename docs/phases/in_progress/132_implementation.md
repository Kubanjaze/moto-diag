# MotoDiag Phase 132 — Export + Sharing (HTML + PDF)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal
Extend Phase 126's `diagnose show --format` mechanism with `html` and `pdf` output so mechanics can hand printed reports to customers or email PDFs to fleet managers. Also extend `kb show` (Phase 128) with the same formats so a known-issue entry can be shared as a customer-facing write-up. No new commands — both extensions reuse the existing `--format` / `--output` / `--yes` option pattern.

```
motodiag diagnose show 42 --format html --output report.html
motodiag diagnose show 42 --format pdf --output report.pdf
motodiag kb show 17 --format pdf --output known-issue-17.pdf
motodiag kb show 17 --format html                              # HTML to stdout (pipe to browser, etc.)
```

Implementation reuses Phase 126's `_format_session_md` / Phase 128's `_render_issue_detail` markdown as the pivot format. HTML is rendered via the `markdown` package (optional dep); PDF via `xhtml2pdf` (optional dep). Both fail gracefully with install hints when the dep is missing. No migration, no new package.

CLI parity with Phase 126:
| `--format` | `--output` | Behavior |
|-----------|-----------|----------|
| `terminal` (default) | — | existing rich.Panel output unchanged |
| `txt` / `json` / `md` | stdout or file | existing Phase 126 behavior |
| `html` / `pdf` | stdout or file | NEW — Phase 132 |

Outputs: extended `src/motodiag/cli/diagnose.py` (+~80 LoC), new formatter module `src/motodiag/cli/export.py` (~150 LoC), extended `src/motodiag/cli/kb.py` (+~80 LoC) to add `kb show --format/--output`, one new optional extras entry in `pyproject.toml`, ~25 new tests.

## Logic

### 1. New `src/motodiag/cli/export.py`
A small shared module that both `diagnose show` and `kb show` use for HTML/PDF rendering. Keeps the two CLI modules from duplicating formatter code.

- `_ensure_markdown_installed() -> ModuleType` — lazy-import the `markdown` package; on ImportError raise `ClickException("HTML/PDF export requires: pip install 'motodiag[export]'")`.
- `_ensure_pdf_installed() -> ModuleType` — same for `xhtml2pdf.pisa`.
- `_build_html_document(title: str, body_md: str) -> str` — wraps the markdown (converted to HTML via `markdown.markdown(body_md, extensions=["tables"])`) in a minimal, printable HTML5 document with inline CSS (page margins, table borders, header padding, readable font stack). Title goes in `<title>` and `<h1>`.
- `format_as_html(title: str, body_md: str) -> str` — public: converts markdown to a full HTML document. Wraps `_ensure_markdown_installed` + `_build_html_document`.
- `format_as_pdf(title: str, body_md: str) -> bytes` — public: converts markdown → HTML via the above, then HTML → PDF bytes via `xhtml2pdf.pisa.CreatePDF`. Returns the PDF bytes. On conversion error, raises `ClickException` with a clear message.
- `write_binary(path: Path, data: bytes, overwrite_confirmed: bool) -> None` — mirrors Phase 126's `_write_report_to_file` but for binary PDF bytes. Same overwrite/parent-dir/permission handling.

### 2. `diagnose show` HTML + PDF integration
- Extend the existing `--format` Choice to `[terminal|txt|json|md|html|pdf]`.
- New branches in the callback:
  - `html`: builds title from session dict, calls `format_as_html(title, _format_session_md(session))`. If `--output` given → writes via existing `_write_report_to_file` (text path). Otherwise → prints to stdout.
  - `pdf`: title + markdown same way, calls `format_as_pdf(...)`. `--output` required for PDF (a PDF file streamed to stdout is useless); CLI errors if not given. Writes via `write_binary`.

### 3. `kb show` HTML + PDF integration
Phase 128's `kb show` currently renders to terminal only. Phase 132 adds parity with Phase 126:
- Extract a `_format_issue_md(row: dict) -> str` from Phase 128's `_render_issue_detail` (or build fresh). Produces a `# {title}` heading + sections for make/model/year range, description, symptoms bulleted, DTCs, causes, fix procedure, parts, estimated hours.
- Add `--format [terminal|txt|md|html|pdf]` and `--output PATH` options to `kb show`. Terminal is default (Phase 128 behavior preserved). Text format is derived by stripping markdown (or just using the md output — acceptable for v1).
- Wires through the same `export.format_as_html` / `format_as_pdf` for html/pdf.

Scope note: `kb show --format json` is deferred to a future phase — the raw dict can already be inspected via SQL if needed, and no known customer demand.

### 4. Optional deps in `pyproject.toml`
- Add `[project.optional-dependencies] export = ["markdown>=3.5", "xhtml2pdf>=0.2.13"]`
- Add `export` to the `all` extras alias.

### 5. Testing (~25 tests)

- `TestExportHelpers` (6):
  - `format_as_html` produces valid HTML with `<title>`, `<h1>`, `<body>` structure.
  - `format_as_html` converts markdown tables (GFM) to `<table>` tags.
  - `format_as_html` raises ClickException with install hint when `markdown` is monkey-patched to raise ImportError.
  - `format_as_pdf` returns non-empty bytes starting with `%PDF` magic number.
  - `format_as_pdf` raises ClickException with install hint when `xhtml2pdf` monkey-patched to raise ImportError.
  - `write_binary` writes PDF bytes and confirmation is visible to caller.
- `TestDiagnoseShowHtml` (4):
  - `diagnose show N --format html` prints HTML to stdout; starts with `<!DOCTYPE` or similar.
  - `diagnose show N --format html --output report.html` writes file + confirmation.
  - HTML output contains the session diagnosis text.
  - HTML output contains the vehicle header info.
- `TestDiagnoseShowPdf` (4):
  - `diagnose show N --format pdf` without `--output` errors cleanly ("PDF output requires --output").
  - `diagnose show N --format pdf --output report.pdf` writes non-empty PDF bytes.
  - PDF file starts with `%PDF-` magic number.
  - Overwrite confirmation prompts unless `--yes`.
- `TestKbShowFormats` (5):
  - `kb show N --format terminal` (default) unchanged from Phase 128.
  - `kb show N --format md --output issue.md` writes markdown.
  - `kb show N --format html` prints HTML.
  - `kb show N --format pdf --output issue.pdf` writes PDF.
  - `kb show N --format pdf` without `--output` errors.
- `TestRegression` (3):
  - Phase 126 `diagnose show --format txt/json/md` still works.
  - Phase 128 `kb show` default still renders Panel.
  - Missing session/issue errors unchanged.
- `TestExtrasAvailable` (3):
  - `import markdown` succeeds in the test venv (sanity check the `export` extra is installed for the regression).
  - `import xhtml2pdf.pisa` succeeds.
  - `export` in `pyproject.toml` `[project.optional-dependencies]` (readable via `tomllib`).

All tests use cli_db fixture. No AI calls (pure formatting). Zero live tokens.

## Key Concepts
- **Markdown is the pivot format** — Phase 126's `_format_session_md` and the new `_format_issue_md` are the single source of truth. HTML is markdown + CSS; PDF is HTML + page layout. Any future format (DOCX, EPUB, …) hooks in at the same pivot.
- **Optional deps via extras**: `motodiag[export]` installs `markdown` + `xhtml2pdf`. A mechanic who doesn't need PDFs installs `motodiag` and everything works; a shop that wants customer-facing PDFs adds the extra. Install-hint messages on missing deps point to the exact `pip install` command.
- **PDF requires `--output`**: binary-to-stdout is useless. CLI errors with a clear message. Contrast with HTML which is human-pipeable (`... --format html | open -a Safari`).
- **`xhtml2pdf` chosen over `weasyprint`**: pure Python, cross-platform, no native deps. WeasyPrint is nicer typographically but needs Cairo/Pango on Windows — not worth the friction for a diagnostic-report use case. If customer feedback demands prettier PDFs, a future phase can add a `--engine weasyprint` flag.
- **Inline CSS in the HTML wrapper**: no external stylesheet — keeps the output self-contained for email attachments. Basic print-readable defaults: serif font, 1em margins, table borders, padded headers.
- **"Sharing" is file output, nothing fancier in v1**: mechanic emails the PDF themselves, or prints and hands over. Track I mobile can add native-share integration later. YAGNI on URL shorteners / upload services.
- **`kb show` gets parity with `diagnose show`** so the same mental model works across commands. Extracting `_format_issue_md` mirrors `_format_session_md` one-to-one.

## Verification Checklist
- [ ] `pyproject.toml` has `[project.optional-dependencies] export = [...]`
- [ ] `format_as_html(title, body_md)` returns a full `<!DOCTYPE html>…</html>` document
- [ ] `format_as_html` converts markdown tables to `<table>`
- [ ] `format_as_html` raises ClickException with install hint when markdown missing
- [ ] `format_as_pdf(title, body_md)` returns bytes starting with `%PDF-`
- [ ] `format_as_pdf` raises ClickException with install hint when xhtml2pdf missing
- [ ] `write_binary` handles overwrite + parent-dir + permission errors
- [ ] `diagnose show N --format html` prints HTML to stdout
- [ ] `diagnose show N --format html --output PATH` writes file
- [ ] `diagnose show N --format pdf` without `--output` exits 1 with clear error
- [ ] `diagnose show N --format pdf --output PATH` writes PDF bytes
- [ ] PDF output starts with `%PDF-` magic number
- [ ] HTML output contains vehicle + diagnosis text
- [ ] `kb show N --format html` prints HTML
- [ ] `kb show N --format md --output PATH` writes markdown
- [ ] `kb show N --format pdf --output PATH` writes PDF
- [ ] `kb show N --format pdf` without `--output` errors cleanly
- [ ] Phase 126 `diagnose show --format txt/json/md/terminal` still works (regression)
- [ ] Phase 128 `kb show` terminal-default still renders Rich Panel (regression)
- [ ] Missing session/issue errors unchanged
- [ ] All 2301 existing tests still pass (zero regressions)
- [ ] Zero live API tokens (pure formatting)

## Risks
- **`xhtml2pdf` HTML support is limited**: no flexbox, limited CSS3. Our CSS is deliberately simple (font, margins, table borders) so this is not a practical concern for diagnostic reports.
- **`markdown` package table extension**: requires explicit `extensions=["tables"]` enable. Easy to forget; test covers this.
- **Optional-dep install friction**: `motodiag[export]` isn't the default install. Mechanics who try `--format pdf` without installing the extra get a clear error with the exact `pip install` command.
- **PDF generation latency**: `xhtml2pdf` is slow on large documents (~1-2s for typical session reports). Acceptable for on-demand export; not a batch-generation tool.
- **Regression risk from Phase 126 `--format` Choice expansion**: adding `html` and `pdf` to the Click Choice could surprise existing tests if any assert on the valid-choices list. Regression tests cover the extant phase tests.
- **`kb show --format pdf` layout for issues with sparse data**: if `parts_needed` is empty, layout must not break. Markdown handles this gracefully (empty section just doesn't render); test covers sparse entries.
