"""Reference package Pydantic models.

Phase 117: 4 enums (source/type/category/level) + 4 models. All models
support optional year range via year_start/year_end (NULL = universal).
"""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

# --- Enums ---

#: Phase 293: a shop's uploaded manual, through its review (K119).
ManualStatus = Literal["pending_review", "approved", "rejected", "taken_down"]
ManualKind = Literal["service_manual", "parts_catalog", "wiring", "other"]
ReviewDecision = Literal["approved", "rejected", "taken_down"]


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
    # Phase 293: a shop's own uploaded file, and its review.
    shop_id: Optional[int] = None
    file_path: Optional[str] = None
    file_sha256: Optional[str] = None
    file_size_bytes: Optional[int] = None
    uploaded_by_user_id: Optional[int] = None
    kind: Optional[ManualKind] = None
    status: ManualStatus = "pending_review"
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[str] = None
    review_reason: Optional[str] = None
    rendered_pages: int = 0
    render_error: Optional[str] = None


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
