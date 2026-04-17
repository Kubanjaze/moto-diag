"""Translation repository — CRUD for the translations table.

Phase 115: CRUD + bulk import + locale completeness check. Track Q phases
use import_translations() to load JSON files of locale-specific strings.
"""

from typing import Optional

from motodiag.core.database import get_connection
from motodiag.i18n.models import Locale, Translation


def get_translation(
    locale: Locale | str,
    namespace: str,
    key: str,
    db_path: str | None = None,
) -> Optional[str]:
    """Return a single translation value, or None if not found."""
    loc_val = locale.value if isinstance(locale, Locale) else locale
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT value FROM translations WHERE locale = ? AND namespace = ? AND key = ?",
            (loc_val, namespace, key),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def set_translation(translation: Translation, db_path: str | None = None) -> None:
    """Upsert a single translation (replaces if (locale, namespace, key) exists)."""
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO translations
               (locale, namespace, key, value, context)
               VALUES (?, ?, ?, ?, ?)""",
            (
                translation.locale.value, translation.namespace,
                translation.key, translation.value, translation.context,
            ),
        )


def delete_translation(
    locale: Locale | str,
    namespace: str,
    key: str,
    db_path: str | None = None,
) -> bool:
    """Delete a translation. Returns True if anything was deleted."""
    loc_val = locale.value if isinstance(locale, Locale) else locale
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM translations WHERE locale = ? AND namespace = ? AND key = ?",
            (loc_val, namespace, key),
        )
        return cursor.rowcount > 0


def list_translations(
    locale: Locale | str | None = None,
    namespace: Optional[str] = None,
    db_path: str | None = None,
) -> list[dict]:
    """List translations with optional locale/namespace filters."""
    query = "SELECT locale, namespace, key, value, context FROM translations WHERE 1=1"
    params: list = []
    if locale is not None:
        loc_val = locale.value if isinstance(locale, Locale) else locale
        query += " AND locale = ?"
        params.append(loc_val)
    if namespace is not None:
        query += " AND namespace = ?"
        params.append(namespace)
    query += " ORDER BY namespace, key, locale"

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def import_translations(
    translations: list[dict] | list[Translation],
    db_path: str | None = None,
) -> int:
    """Bulk import translations. Returns count imported.

    Accepts either a list of dicts with keys {locale, namespace, key, value, context}
    or a list of Translation Pydantic models. Uses INSERT OR REPLACE semantics.
    """
    count = 0
    with get_connection(db_path) as conn:
        for t in translations:
            if isinstance(t, Translation):
                values = (
                    t.locale.value, t.namespace, t.key, t.value, t.context,
                )
            else:
                loc = t["locale"]
                if isinstance(loc, Locale):
                    loc = loc.value
                values = (
                    loc, t["namespace"], t["key"], t["value"], t.get("context"),
                )
            conn.execute(
                """INSERT OR REPLACE INTO translations
                   (locale, namespace, key, value, context)
                   VALUES (?, ?, ?, ?, ?)""",
                values,
            )
            count += 1
    return count


def list_locales(db_path: str | None = None) -> list[str]:
    """Return all locales that have at least one translation entry."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "SELECT DISTINCT locale FROM translations ORDER BY locale"
        )
        return [row[0] for row in cursor.fetchall()]


def count_translations(
    db_path: str | None = None,
    locale: Locale | str | None = None,
    namespace: Optional[str] = None,
) -> int:
    query = "SELECT COUNT(*) FROM translations WHERE 1=1"
    params: list = []
    if locale is not None:
        loc_val = locale.value if isinstance(locale, Locale) else locale
        query += " AND locale = ?"
        params.append(loc_val)
    if namespace is not None:
        query += " AND namespace = ?"
        params.append(namespace)
    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]


def locale_completeness(locale: Locale | str, db_path: str | None = None) -> dict:
    """Report how complete a locale's translations are vs. English.

    Returns a dict with:
        - locale: the queried locale
        - english_count: total English translations
        - locale_count: translations in this locale
        - missing_keys: list of (namespace, key) tuples missing in this locale
        - completeness_ratio: 0.0 to 1.0
    """
    loc_val = locale.value if isinstance(locale, Locale) else locale

    with get_connection(db_path) as conn:
        english_count = conn.execute(
            "SELECT COUNT(*) FROM translations WHERE locale = 'en'"
        ).fetchone()[0]

        locale_count = conn.execute(
            "SELECT COUNT(*) FROM translations WHERE locale = ?", (loc_val,),
        ).fetchone()[0]

        # Missing keys = English keys not present in target locale
        missing = conn.execute(
            """SELECT e.namespace, e.key FROM translations e
               WHERE e.locale = 'en'
               AND NOT EXISTS (
                   SELECT 1 FROM translations t
                   WHERE t.locale = ? AND t.namespace = e.namespace AND t.key = e.key
               )
               ORDER BY e.namespace, e.key""",
            (loc_val,),
        ).fetchall()

    missing_keys = [(row[0], row[1]) for row in missing]
    completeness_ratio = (
        locale_count / english_count if english_count > 0 else 0.0
    )

    return {
        "locale": loc_val,
        "english_count": english_count,
        "locale_count": locale_count,
        "missing_keys": missing_keys,
        "completeness_ratio": round(completeness_ratio, 4),
    }
