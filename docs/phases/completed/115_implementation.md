# MotoDiag Phase 115 — i18n Substrate

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the internationalization (i18n) substrate that Track Q phases 308-310 (Spanish/French/German localization) will consume. New `src/motodiag/i18n/` package with translations table, `Locale` enum, and a `t()` translator function implementing the fallback chain locale → English → `[namespace.key]`. English-only content at this stage — Track Q phases populate the locale-specific strings. Adds migration 008 for the translations table with 45 seeded English strings across 4 namespaces (cli/ui/diagnostics/workflow).

CLI: `python -m pytest tests/test_phase115_i18n.py -v`

Outputs: `src/motodiag/i18n/` package (4 files), migration 008, 40 tests

## Logic
1. **Migration 008**:
   - `CREATE TABLE translations` — locale, namespace, key, value (NOT NULL), context (optional plural form / usage hint)
   - Composite PK: `(locale, namespace, key)`
   - 2 indexes: `idx_translations_locale`, `idx_translations_ns_key`
   - Seeds 45 baseline English strings across 4 namespaces: cli (11), ui (12), diagnostics (11), workflow (11)
   - Rollback drops the translations table

2. **`src/motodiag/i18n/__init__.py`** — re-exports the public API (Locale, Translation, t, current_locale, set_locale, CRUD functions, import_translations, locale_completeness, list_locales, count_translations).

3. **`src/motodiag/i18n/models.py`**:
   - `Locale` enum: 7 members — EN, ES, FR, DE, JA, IT, PT (ISO 639-1 codes)
   - `Translation` Pydantic model — locale, namespace, key, value, optional context

4. **`src/motodiag/i18n/translator.py`**:
   - `t(key, namespace='ui', locale=None, db_path=None, **kwargs)` — main public API
   - Fallback chain: requested locale → English (if different) → `[namespace.key]`
   - String interpolation via `value.format(**kwargs)`, swallows KeyError/IndexError to return un-interpolated on missing placeholders (never break the UI)
   - `current_locale()` reads `MOTODIAG_LOCALE` env var, falls back to `Locale.EN`; invalid values also fall back
   - `set_locale()` updates the env var (primarily for tests)

5. **`src/motodiag/i18n/translation_repo.py`**:
   - CRUD: `get_translation`, `set_translation` (upsert), `delete_translation`, `list_translations` (locale/namespace filters)
   - Bulk: `import_translations` accepts both dicts and Pydantic models (INSERT OR REPLACE)
   - Reporting: `list_locales`, `count_translations`, `locale_completeness` — returns `{locale, english_count, locale_count, missing_keys, completeness_ratio}`

6. **`database.py`**: `SCHEMA_VERSION` 7 → 8.

## Key Concepts
- Locale codes follow ISO 639-1 (en, es, fr, de, ja, it, pt)
- Namespace-scoped keys prevent collisions: `cli.welcome` vs `ui.welcome` coexist
- Fallback chain never returns empty string — always returns something renderable
- Composite PK `(locale, namespace, key)` enables INSERT OR REPLACE upsert semantics
- `t()` accepts both `Locale` enum and raw string locale codes
- `import_translations()` is idempotent — reruns overwrite, never duplicate
- `locale_completeness()` computes missing keys by SQL `NOT EXISTS` anti-join against English
- Pattern for Track Q phases 308-310: JSON file per locale → `import_translations()` → verify with `locale_completeness()`

## Verification Checklist
- [x] Migration 008 creates translations table with composite PK and indexes
- [x] 45 baseline English strings seeded (11 cli + 12 ui + 11 diagnostics + 11 workflow)
- [x] Locale enum has 7 members covering planned languages + reserves
- [x] t() returns correct string for requested locale
- [x] t() falls back to English if locale missing
- [x] t() falls back to `[namespace.key]` if translation missing entirely
- [x] String interpolation with `{placeholder}` syntax works
- [x] Missing placeholder returns un-interpolated string (no exception)
- [x] Bulk import works for both dicts and Pydantic models
- [x] locale_completeness reports missing keys and ratio correctly
- [x] MOTODIAG_LOCALE env var respected; invalid values fall back to en
- [x] Schema version assertions use `>=` (forward-compat)
- [x] Migration 008 rollback drops translations table cleanly
- [x] All 1801 existing tests still pass (zero regressions)

## Risks
- **Bundle size if every locale loaded at once**: resolved — translations table is SQLite-backed and queried per-key, not bulk-loaded into memory. Adding locales scales linearly in DB size only.
- **Key proliferation across the codebase**: mitigated by namespace convention (cli/ui/diagnostics/workflow) — call sites self-document their context.
- **Placeholder typos silently return raw string**: intentional trade-off — preferable to crashing the UI. Track Q's completeness report catches missing keys; placeholder mismatches will need a separate lint pass in a future phase.
- **SCHEMA_VERSION forward-compat tests**: all new tests use `>= 8` per established pattern.

## Deviations from Plan
- Plan said "~40 seeded English strings" — actual count is 45 (11+12+11+11). The test asserts `40 <= total <= 50` to accept the range without forcing a specific count.
- Migration 008's upgrade_sql carries both the DDL and the seeds in one script — simpler than a two-phase seed step, and `INSERT OR IGNORE` makes the migration idempotent if re-run.

## Results
| Metric | Value |
|--------|-------|
| New files | 5 (i18n/__init__.py, models.py, translator.py, translation_repo.py, test_phase115_i18n.py) |
| New tests | 40 |
| Total tests | 1841 passing (was 1801) |
| Seeded English strings | 45 across 4 namespaces |
| Locale enum members | 7 (en/es/fr/de/ja/it/pt) |
| Schema version | 7 → 8 |
| Regression status | Zero regressions — full suite 7:21 runtime |

Phase 115 establishes the translation substrate Track Q will populate. The `t()` fallback chain (locale → en → `[namespace.key]`) guarantees the UI never shows empty strings, and the `locale_completeness` reporter gives Track Q phases a direct measure of translation progress per locale.
