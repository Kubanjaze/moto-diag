"""Photo annotation model — shapes overlaid on static images.

Phase 119 (Retrofit): coordinate-based shape annotations (circles,
rectangles, arrows, text labels). Coords normalized 0.0–1.0 so
annotations survive image resize or display-device pixel density
differences. Distinct from Phase 105's video annotation (timestamp-based).
Track Q phase 307 builds the canvas overlay renderer.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


class AnnotationShape(str, Enum):
    """Shape of a photo annotation."""
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    ARROW = "arrow"
    TEXT = "text"


class PhotoAnnotation(BaseModel):
    """A single shape annotation on a static image.

    Coordinate conventions:
    - circle/rectangle: (x, y) = top-left corner, width/height = extent, all [0.0, 1.0]
    - arrow: (x, y) = tail, (x+width, y+height) = head; width/height may be negative
    - text: (x, y) = baseline-left anchor; width/height ignored
    """
    id: Optional[int] = None
    image_ref: str = Field(..., description="Opaque image identifier (path/URL/URI)")
    failure_photo_id: Optional[int] = Field(
        None, description="Optional FK to failure_photos.id (CASCADE on delete)"
    )
    shape: AnnotationShape
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    width: Optional[float] = None
    height: Optional[float] = None
    text: Optional[str] = None
    color: str = Field(default="#FF0000", description="Hex color #RRGGBB")
    stroke_width: int = Field(default=2, ge=1, le=32)
    label: Optional[str] = None
    created_by_user_id: int = Field(default=1, description="FK users.id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("color")
    @classmethod
    def _valid_hex_color(cls, v: str) -> str:
        if not HEX_COLOR_RE.match(v):
            raise ValueError(f"color must match #RRGGBB hex format, got {v!r}")
        return v.upper()

    @field_validator("width", "height")
    @classmethod
    def _size_bounds(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        # Arrows can have negative deltas (pointing up/left); circle/rect use absolute bounds
        if abs(v) > 1.0:
            raise ValueError(f"width/height must be in [-1.0, 1.0], got {v}")
        return v
