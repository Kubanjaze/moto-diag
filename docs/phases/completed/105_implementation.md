# MotoDiag Phase 105 — Video Annotation + Timestamps

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a VideoAnnotator class for marking moments in diagnostic video with timestamped annotations. Supports both AI-generated and mechanic-added annotations with severity levels (info/warning/critical). Produces text timelines for CLI display, filters by time range and severity, and auto-generates annotations from analysis results. No actual video processing — manages annotation metadata that overlays on video.

CLI: `python -m pytest tests/test_phase105_annotation.py -v`

Outputs: `src/motodiag/media/annotation.py` (VideoAnnotator + Annotation + AnnotatedVideo), 27 tests

## Logic
- Annotation model: annotation_id, timestamp_sec, label, description, severity (info/warning/critical), annotator (ai/mechanic), tags list, confidence (float for AI), created_at
- AnnotatedVideo model: video_id, video_metadata dict, annotations list (sorted by timestamp), created_at
- VideoAnnotator.create_video(): creates AnnotatedVideo with metadata
- VideoAnnotator.add_annotation(): validates timestamp (non-negative, within duration), validates severity/annotator enums, inserts annotation and re-sorts by timestamp
- VideoAnnotator.get_annotations_in_range(): filters by start_sec <= timestamp <= end_sec (inclusive)
- VideoAnnotator.get_critical_moments(): returns warning+critical or critical-only annotations
- VideoAnnotator.generate_timeline(): produces formatted text timeline with [MM:SS] [SEVERITY] label -- description [annotator] format, header with filename and duration, footer with counts
- VideoAnnotator.auto_annotate(): converts analysis result dicts to AI annotations, skips incomplete results (missing timestamp_sec or label)
- VideoAnnotator.get_annotations_by_label(): case-insensitive label search
- VideoAnnotator.remove_annotation(): removes by annotation_id, returns bool

## Key Concepts
- Annotations sorted by timestamp on every insertion — ensures timeline order is always correct
- Severity enum: info (observations), warning (potential issues), critical (action needed)
- Annotator enum: ai (auto-generated from analysis) vs mechanic (human-added)
- AI annotations include confidence scores (0.0-1.0); mechanic annotations leave confidence as None
- Timeline format designed for CLI display with fixed-width timestamp column
- Auto-annotate accepts generic dicts — decoupled from any specific analysis engine output format
- Validation: negative timestamps rejected, timestamps beyond video duration rejected, invalid severity/annotator values rejected

## Verification Checklist
- [x] Annotation model: creation, defaults, AI with confidence (3 tests)
- [x] AnnotatedVideo model: creation with metadata, no metadata (2 tests)
- [x] add_annotation: single, multiple sorted, with severity, negative timestamp raises, exceeds duration raises, invalid severity raises, invalid annotator raises (7 tests)
- [x] Filtering: get_annotations_in_range (basic, inclusive boundaries, no results, invalid range raises), get_critical_moments (with/without warnings) (6 tests)
- [x] Timeline: full output, empty video, without descriptions (3 tests)
- [x] Auto-annotate: from results, skips incomplete, empty results (3 tests)
- [x] Label search case-insensitive, remove annotation, remove nonexistent (3 tests)

## Risks
- No actual video file handling — this module is metadata-only. Video rendering/playback is Track I (mobile app).
- Annotations are in-memory only. Persistence to database will be added when the annotation system connects to the diagnostic session storage.

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (annotation.py) |
| Tests | 27 |
| Models | 2 (Annotation, AnnotatedVideo) |
| Enums | 2 (AnnotationSeverity, AnnotatorType) |
| Annotator methods | 7 (create_video, add_annotation, get_annotations_in_range, get_critical_moments, generate_timeline, auto_annotate, get_annotations_by_label, remove_annotation) |
| External deps | 0 (pure Python + Pydantic) |

Key finding: The annotation system is completely decoupled from video file format or playback — it manages timestamped metadata that can overlay on any video source. The auto_annotate method accepts generic dicts, making it easy to connect to any analysis engine output without tight coupling.
