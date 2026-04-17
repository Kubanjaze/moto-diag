"""Phase 115 — i18n translations substrate tests.

Tests cover:
- Migration 008 creates translations table with composite PK
- ~40 seeded English strings across 4 namespaces (cli, ui, diagnostics, workflow)
- Locale enum has 7 members (en, es, fr, de, ja, it, pt)
- Translation CRUD
- Bulk import (dicts + Pydantic models)
- t() fallback chain: requested locale -> en -> [namespace.key]
- String interpolation via {placeholder} syntax
- locale_completeness reporter
- Schema version >= 8 (forward-compat for later phases)
"""

import os

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import (
    get_migration_by_version, rollback_migration, rollback_to_version,
)
from motodiag.i18n import (
    Locale, Translation,
    t, current_locale, set_locale,
    get_translation, set_translation, delete_translation,
    list_translations, import_translations, list_locales,
    count_translations, locale_completeness,
)


# --- Migration 008 ---


class TestMigration008:
    def test_migration_008_exists(self):
        m = get_migration_by_version(8)
        assert m is not None
        assert "translations" in m.upgrade_sql.lower()

    def test_translations_table_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='translations'"
            )
            assert cursor.fetchone() is not None

    def test_composite_pk(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute("PRAGMA table_info(translations)")
            cols = {row[1]: row for row in cursor.fetchall()}
        assert "locale" in cols and cols["locale"][5] > 0
        assert "namespace" in cols and cols["namespace"][5] > 0
        assert "key" in cols and cols["key"][5] > 0
        assert "value" in cols
        assert "context" in cols

    def test_indexes_created(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' "
                "AND name LIKE 'idx_translations%'"
            )
            indexes = {row[0] for row in cursor.fetchall()}
        assert "idx_translations_locale" in indexes
        assert "idx_translations_ns_key" in indexes

    def test_rollback_drops_translations(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # Rolling back 008 alone is safe — no later migrations depend on it
        m = get_migration_by_version(8)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='translations'"
            )
            assert cursor.fetchone() is None


# --- Seeded English strings ---


class TestSeededEnglishStrings:
    def test_cli_namespace_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_translation("en", "cli", "welcome", db) == "Welcome to MotoDiag"
        assert get_translation("en", "cli", "exit_goodbye", db) == "Goodbye!"

    def test_ui_namespace_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_translation("en", "ui", "button_save", db) == "Save"
        assert get_translation("en", "ui", "button_cancel", db) == "Cancel"
        assert get_translation("en", "ui", "loading", db) == "Loading..."

    def test_diagnostics_namespace_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_translation("en", "diagnostics", "severity_critical", db) == "Critical"
        assert get_translation("en", "diagnostics", "severity_low", db) == "Low"
        assert get_translation("en", "diagnostics", "confidence_high", db) == "High confidence"

    def test_workflow_namespace_seeded(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_translation("en", "workflow", "step_pass", db) == "Pass"
        assert get_translation("en", "workflow", "step_fail", db) == "Fail"
        assert get_translation("en", "workflow", "template_ppi", db) == "Pre-Purchase Inspection"

    def test_approx_40_english_strings_total(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        total = count_translations(db, locale="en")
        # 11 cli + 12 ui + 11 diagnostics + 11 workflow = 45
        assert 40 <= total <= 50, f"Expected ~40 baseline strings, got {total}"

    def test_all_4_namespaces_present(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT DISTINCT namespace FROM translations WHERE locale='en' ORDER BY namespace"
            )
            namespaces = {row[0] for row in cursor.fetchall()}
        assert namespaces == {"cli", "ui", "diagnostics", "workflow"}


# --- Locale enum ---


class TestLocaleEnum:
    def test_locale_has_7_members(self):
        assert len(Locale) == 7

    def test_locale_iso_codes(self):
        assert Locale.EN.value == "en"
        assert Locale.ES.value == "es"
        assert Locale.FR.value == "fr"
        assert Locale.DE.value == "de"
        assert Locale.JA.value == "ja"
        assert Locale.IT.value == "it"
        assert Locale.PT.value == "pt"


# --- CRUD ---


class TestTranslationCRUD:
    def test_set_and_get(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t_obj = Translation(
            locale=Locale.ES, namespace="cli", key="welcome",
            value="Bienvenido a MotoDiag",
        )
        set_translation(t_obj, db)
        assert get_translation(Locale.ES, "cli", "welcome", db) == "Bienvenido a MotoDiag"

    def test_get_missing_returns_none(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_translation("en", "cli", "nonexistent_key", db) is None

    def test_set_is_upsert(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t1 = Translation(locale=Locale.ES, namespace="ui", key="button_save", value="Guardar")
        t2 = Translation(locale=Locale.ES, namespace="ui", key="button_save", value="Guardar (v2)")
        set_translation(t1, db)
        set_translation(t2, db)
        assert get_translation("es", "ui", "button_save", db) == "Guardar (v2)"

    def test_delete(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        t_obj = Translation(locale=Locale.FR, namespace="cli", key="welcome", value="Bienvenue")
        set_translation(t_obj, db)
        assert delete_translation(Locale.FR, "cli", "welcome", db) is True
        assert get_translation("fr", "cli", "welcome", db) is None

    def test_delete_nonexistent_returns_false(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert delete_translation("fr", "cli", "nonexistent", db) is False

    def test_list_by_locale(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        en_rows = list_translations(locale="en", db_path=db)
        assert len(en_rows) >= 40
        assert all(r["locale"] == "en" for r in en_rows)

    def test_list_by_namespace(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        ui_rows = list_translations(namespace="ui", db_path=db)
        assert all(r["namespace"] == "ui" for r in ui_rows)
        assert len(ui_rows) >= 10


# --- Bulk import ---


class TestBulkImport:
    def test_import_dicts(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        rows = [
            {"locale": "es", "namespace": "cli", "key": "welcome", "value": "Bienvenido"},
            {"locale": "es", "namespace": "cli", "key": "exit_goodbye", "value": "Adiós"},
        ]
        count = import_translations(rows, db)
        assert count == 2
        assert get_translation("es", "cli", "welcome", db) == "Bienvenido"

    def test_import_pydantic_models(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        rows = [
            Translation(locale=Locale.DE, namespace="ui", key="button_save", value="Speichern"),
            Translation(locale=Locale.DE, namespace="ui", key="button_cancel", value="Abbrechen"),
        ]
        count = import_translations(rows, db)
        assert count == 2
        assert get_translation("de", "ui", "button_save", db) == "Speichern"

    def test_import_mixed(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        rows = [
            {"locale": "fr", "namespace": "cli", "key": "welcome", "value": "Bienvenue"},
            Translation(locale=Locale.FR, namespace="ui", key="button_save", value="Enregistrer"),
        ]
        count = import_translations(rows, db)
        assert count == 2


# --- t() translator and fallback chain ---


class TestTranslator:
    def test_t_returns_english_by_default(self, tmp_path, monkeypatch):
        db = str(tmp_path / "t.db")
        init_db(db)
        monkeypatch.delenv("MOTODIAG_LOCALE", raising=False)
        assert t("welcome", namespace="cli", db_path=db) == "Welcome to MotoDiag"

    def test_t_with_explicit_locale(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        set_translation(
            Translation(locale=Locale.ES, namespace="cli", key="welcome", value="Bienvenido"),
            db,
        )
        assert t("welcome", namespace="cli", locale="es", db_path=db) == "Bienvenido"

    def test_t_fallback_to_english(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # No Spanish translation seeded — should fall back to English
        result = t("welcome", namespace="cli", locale="es", db_path=db)
        assert result == "Welcome to MotoDiag"

    def test_t_fallback_to_key_as_last_resort(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # No translation in any locale
        result = t("nonexistent_key", namespace="cli", locale="es", db_path=db)
        assert result == "[cli.nonexistent_key]"

    def test_t_with_string_interpolation(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        result = t("version_info", namespace="cli", db_path=db, version="1.2.3")
        assert result == "MotoDiag v1.2.3"

    def test_t_with_missing_placeholder_returns_raw(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # version_info expects {version} but we pass nothing
        result = t("version_info", namespace="cli", db_path=db)
        assert "{version}" in result

    def test_t_locale_enum_accepted(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        result = t("welcome", namespace="cli", locale=Locale.EN, db_path=db)
        assert result == "Welcome to MotoDiag"


# --- Environment locale ---


class TestCurrentLocale:
    def test_default_is_en(self, monkeypatch):
        monkeypatch.delenv("MOTODIAG_LOCALE", raising=False)
        assert current_locale() == Locale.EN

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("MOTODIAG_LOCALE", "es")
        assert current_locale() == Locale.ES

    def test_env_invalid_falls_back_to_en(self, monkeypatch):
        monkeypatch.setenv("MOTODIAG_LOCALE", "klingon")
        assert current_locale() == Locale.EN

    def test_set_locale(self, monkeypatch):
        monkeypatch.delenv("MOTODIAG_LOCALE", raising=False)
        set_locale(Locale.FR)
        assert current_locale() == Locale.FR


# --- Locale completeness ---


class TestLocaleCompleteness:
    def test_completeness_en_is_100pct(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        report = locale_completeness("en", db)
        assert report["completeness_ratio"] == 1.0
        assert report["missing_keys"] == []

    def test_completeness_empty_locale_is_0(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        report = locale_completeness("es", db)
        assert report["completeness_ratio"] == 0.0
        assert len(report["missing_keys"]) >= 40

    def test_completeness_partial(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        # Translate 2 strings to Spanish
        import_translations([
            {"locale": "es", "namespace": "cli", "key": "welcome", "value": "Bienvenido"},
            {"locale": "es", "namespace": "ui", "key": "button_save", "value": "Guardar"},
        ], db)
        report = locale_completeness("es", db)
        assert 0 < report["completeness_ratio"] < 1.0
        assert report["locale_count"] == 2

    def test_list_locales(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert list_locales(db) == ["en"]
        set_translation(
            Translation(locale=Locale.ES, namespace="cli", key="welcome", value="Bienvenido"),
            db,
        )
        locales = list_locales(db)
        assert set(locales) == {"en", "es"}


# --- Forward compat: schema version >= 8 ---


class TestSchemaVersionForwardCompat:
    def test_schema_version_at_least_8(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_schema_version(db) >= 8

    def test_schema_version_constant_at_least_8(self):
        assert SCHEMA_VERSION >= 8
