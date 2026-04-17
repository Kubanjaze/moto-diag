"""Reference package — manual citations, parts diagrams, failure photos, video tutorials.

Phase 117 (Retrofit): 4 empty tables + CRUD. Track P phases 293-302
populate actual content: Clymer/Haynes citations (293), per-model torque
specs (294), failure photo library (295), video tutorial index (296-302).
"""

from motodiag.reference.models import (
    ManualSource, DiagramType, FailureCategory, SkillLevel,
    ManualReference, PartsDiagram, FailurePhoto, VideoTutorial,
)
from motodiag.reference.manual_repo import (
    add_manual, get_manual, list_manuals, update_manual, delete_manual,
)
from motodiag.reference.diagram_repo import (
    add_diagram, get_diagram, list_diagrams, update_diagram, delete_diagram,
)
from motodiag.reference.photo_repo import (
    add_photo, get_photo, list_photos, update_photo, delete_photo,
)
from motodiag.reference.video_repo import (
    add_video, get_video, list_videos, update_video, delete_video,
)

__all__ = [
    "ManualSource", "DiagramType", "FailureCategory", "SkillLevel",
    "ManualReference", "PartsDiagram", "FailurePhoto", "VideoTutorial",
    "add_manual", "get_manual", "list_manuals", "update_manual", "delete_manual",
    "add_diagram", "get_diagram", "list_diagrams", "update_diagram", "delete_diagram",
    "add_photo", "get_photo", "list_photos", "update_photo", "delete_photo",
    "add_video", "get_video", "list_videos", "update_video", "delete_video",
]
