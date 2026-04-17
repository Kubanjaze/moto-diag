"""Translator — the t() function.

Phase 115: main public API for retrieving localized strings. Implements
fallback chain: requested locale → English → key. Supports string
interpolation via {placeholder} syntax.
"""

import os
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.i18n.models import Locale


DEFAULT_LOCALE = Locale.EN


def current_locale() -> Locale:
    """Get the current locale.

    Priority: MOTODIAG_LOCALE env var → DEFAULT_LOCALE (en).
    """
    env = os.environ.get("MOTODIAG_LOCALE", "").lower()
    if env:
        try:
            return Locale(env)
        except ValueError:
            pass
    return DEFAULT_LOCALE


def set_locale(locale: Locale | str) -> None:
    """Set the current locale by updating env var.

    Primarily used for testing — production code typically relies on the
    MOTODIAG_LOCALE env var being set before the app starts.
    """
    val = locale.value if isinstance(locale, Locale) else locale
    os.environ["MOTODIAG_LOCALE"] = val


def t(
    key: str,
    namespace: str = "ui",
    locale: Optional[Locale | str] = None,
    db_path: str | None = None,
    **kwargs,
) -> str:
    """Translate a key to the current locale with fallback to English.

    Args:
        key: Translation key within the namespace.
        namespace: Namespace (cli/ui/diagnostics/workflow/...).
        locale: Optional locale override. Defaults to current_locale().
        db_path: Optional DB path override.
        **kwargs: String interpolation values for {placeholders}.

    Returns:
        Translated string. If no translation exists in the requested locale
        or English, returns the key itself as a last resort.
    """
    target_locale = locale if locale is not None else current_locale()
    if isinstance(target_locale, Locale):
        target_locale = target_locale.value

    with get_connection(db_path) as conn:
        # Try requested locale first
        cursor = conn.execute(
            "SELECT value FROM translations WHERE locale = ? AND namespace = ? AND key = ?",
            (target_locale, namespace, key),
        )
        row = cursor.fetchone()

        if row is None and target_locale != DEFAULT_LOCALE.value:
            # Fall back to English
            cursor = conn.execute(
                "SELECT value FROM translations WHERE locale = ? AND namespace = ? AND key = ?",
                (DEFAULT_LOCALE.value, namespace, key),
            )
            row = cursor.fetchone()

    if row is None:
        # Last resort: return the key
        value = f"[{namespace}.{key}]"
    else:
        value = row[0]

    # String interpolation
    if kwargs:
        try:
            value = value.format(**kwargs)
        except (KeyError, IndexError):
            # Missing placeholder — return un-interpolated to avoid breaking
            pass

    return value
