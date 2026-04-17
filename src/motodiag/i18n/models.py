"""i18n Pydantic models.

Phase 115: Locale enum and Translation model.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Locale(str, Enum):
    """Supported locales (ISO 639-1 codes).

    Phase 115 (Retrofit): plumbing only — English is the only populated
    locale. Track Q phases 308-310 add Spanish (es), French (fr), German (de).
    Additional locales (Japanese, Italian, Portuguese) reserved for future.
    """
    EN = "en"  # English (default)
    ES = "es"  # Spanish (Track Q phase 308)
    FR = "fr"  # French (Track Q phase 309)
    DE = "de"  # German (Track Q phase 310)
    JA = "ja"  # Japanese (reserved)
    IT = "it"  # Italian (reserved)
    PT = "pt"  # Portuguese (reserved)


class Translation(BaseModel):
    """A single translation entry."""
    locale: Locale = Field(..., description="Target locale")
    namespace: str = Field(..., description="Namespace (e.g., 'cli', 'ui', 'diagnostics')")
    key: str = Field(..., description="Translation key within the namespace")
    value: str = Field(..., description="Translated string")
    context: Optional[str] = Field(
        None,
        description="Optional context hint for translators (plural forms, usage)",
    )
