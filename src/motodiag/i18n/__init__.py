"""i18n package — internationalization substrate for localized strings.

Phase 115 (Retrofit): introduces translations table + t() translator function
that Track Q phases 308-310 will populate with Spanish/French/German strings.
English-only content at this stage.
"""

from motodiag.i18n.models import Locale, Translation
from motodiag.i18n.translation_repo import (
    count_translations,
    delete_translation,
    get_translation,
    import_translations,
    list_locales,
    list_translations,
    locale_completeness,
    set_translation,
)
from motodiag.i18n.translator import current_locale, set_locale, t

__all__ = [
    "Locale", "Translation",
    "t", "current_locale", "set_locale",
    "get_translation", "set_translation", "list_translations",
    "delete_translation", "import_translations", "locale_completeness",
    "list_locales", "count_translations",
]
