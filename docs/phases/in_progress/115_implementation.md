# MotoDiag Phase 115 — i18n Substrate

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Create the internationalization (i18n) substrate that Track Q phases 308-310 (Spanish/French/German localization) will consume. New `src/motodiag/i18n/` package with translations table, locale management, and a `t()` translator function. English-only content at this stage — Track Q phases populate the locale-specific strings. Adds migration 008 for the translations table.

CLI: `python -m pytest tests/test_phase115_i18n.py -v`

Outputs: `src/motodiag/i18n/` package, migration 008, tests

## Logic
1. **Migration 008**:
   - `CREATE TABLE translations` — locale (e.g., 'en', 'es', 'fr', 'de'), namespace (e.g., 'cli', 'diagnostics', 'ui'), key, value (translated text), context (optional plural form, usage hint)
   - Composite PK: (locale, namespace, key)
   - Seeds baseline English strings across 4 namespaces: cli, ui, diagnostics, workflow
   - ~40 seeded English strings (will be mirrored for each locale by Track Q)

2. **`src/motodiag/i18n/__init__.py`**: Public API
3. **`src/motodiag/i18n/models.py`**: `Locale` enum (en/es/fr/de/...), `Translation` model
4. **`src/motodiag/i18n/translator.py`**: `t(key, namespace='ui', locale=None, **kwargs)` function, locale fallback (es → en), string interpolation support
5. **`src/motodiag/i18n/translation_repo.py`**: CRUD for translations, bulk import from dict, locale completeness check

## Key Concepts
- Locale codes follow ISO 639-1 (en, es, fr, de, ja, it, pt)
- Namespace-scoped keys prevent collisions: `cli.welcome` vs `ui.welcome`
- Fallback chain: requested locale → English → key (if missing entirely)
- String interpolation with `{var}` placeholders
- Current locale: env var `MOTODIAG_LOCALE` or settings, defaults to `en`
- Track Q phases bulk-populate via `import_translations()` from JSON files

## Verification Checklist
- [ ] Migration 008 creates translations table
- [ ] Baseline English strings seeded
- [ ] Locale enum covers planned languages
- [ ] t() returns correct string for locale
- [ ] t() falls back to English if locale missing
- [ ] t() falls back to key if translation missing entirely
- [ ] String interpolation works
- [ ] Bulk import works
- [ ] All 1801 existing tests still pass
