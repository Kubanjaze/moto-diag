"""Media diagnostic intelligence — video/audio analysis for hands-free diagnostics.

Mechanic films a bike starting/running/dying → AI analyzes engine sound signature,
visual symptoms (smoke, leaks, vibration), and behavior → suggests diagnostic paths.

Key capabilities:
- Audio spectrogram analysis: identify knock, misfire, valve tick, exhaust leak
- Video frame analysis: smoke color, fluid leaks, gauge readings (via Claude Vision)
- Multimodal fusion: combine audio + video + text symptoms + DTCs
- Comparative analysis: "before vs after" audio baselines
- Real-time audio monitoring via phone microphone
- Photo annotation (Phase 119): coordinate-based shape overlays on static images
"""

from motodiag.media.photo_annotation import AnnotationShape, PhotoAnnotation
from motodiag.media.photo_annotation_repo import (
    add_annotation, get_annotation,
    list_annotations_for_image, list_annotations_for_failure_photo,
    count_annotations_for_image,
    update_annotation, delete_annotation, bulk_import_annotations,
)

__all__ = [
    "AnnotationShape", "PhotoAnnotation",
    "add_annotation", "get_annotation",
    "list_annotations_for_image", "list_annotations_for_failure_photo",
    "count_annotations_for_image",
    "update_annotation", "delete_annotation", "bulk_import_annotations",
]
