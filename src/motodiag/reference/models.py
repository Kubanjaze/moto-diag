"""Reference package Pydantic models.

Phase 117: 4 enums (source/type/category/level) + 4 models. All models
support optional year range via year_start/year_end (NULL = universal).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums ---


class ManualSource(str, Enum):
    """Publisher/origin of a service manual reference."""
    CLYMER = "clymer"
    HAYNES = "haynes"
    OEM = "oem"  # Factory service manual
    FORUM = "forum"  # Forum compilation (e.g., Harley Davidson Forums wiki)
    OTHER = "other"


class DiagramType(str, Enum):
    """Type of technical diagram."""
    EXPLODED_VIEW = "exploded_view"
    SCHEMATIC = "schematic"
    WIRING = "wiring"
    ASSEMBLY = "assembly"


class FailureCategory(str, Enum):
    """High-level category of failure depicted in a photo."""
    MECHANICAL_WEAR = "mechanical_wear"
    ELECTRICAL_FAILURE = "electrical_failure"
    CORROSION = "corrosion"
    COSMETIC_DAMAGE = "cosmetic_damage"
    CRASH_DAMAGE = "crash_damage"
    FLUID_LEAK = "fluid_leak"
    OTHER = "other"


class SkillLevel(str, Enum):
    """Skill level required to follow a video tutorial."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# --- Models ---


class ManualReference(BaseModel):
    """A service manual citation."""
    id: Optional[int] = None
    source: ManualSource
    title: str
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    page_count: Optional[int] = None
    section_titles: list[str] = Field(default_factory=list)
    url: Optional[str] = None
    notes: Optional[str] = None


class PartsDiagram(BaseModel):
    """An exploded view, schematic, wiring, or assembly diagram."""
    id: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    diagram_type: DiagramType
    section: Optional[str] = Field(None, description="Chapter/section label (e.g., 'Engine', 'Transmission')")
    title: str
    image_ref: str = Field(..., description="Path, URL, or URI to the image")
    source_manual_id: Optional[int] = Field(None, description="FK manual_references.id")
    notes: Optional[str] = None


class FailurePhoto(BaseModel):
    """A photo depicting a specific failure mode."""
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    failure_category: FailureCategory
    make: Optional[str] = None
    model: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    part_affected: Optional[str] = None
    image_ref: str = Field(..., description="Path, URL, or URI to the image")
    submitted_by_user_id: int = Field(default=1, description="FK users.id")


class VideoTutorial(BaseModel):
    """A tutorial video (YouTube, Vimeo, or internal)."""
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    source: str = Field(..., description="youtube, vimeo, internal, or other")
    source_video_id: Optional[str] = Field(None, description="Native video id (e.g., YouTube ID)")
    url: Optional[str] = None
    duration_seconds: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None
    skill_level: SkillLevel = SkillLevel.INTERMEDIATE
    topic_tags: list[str] = Field(default_factory=list)
