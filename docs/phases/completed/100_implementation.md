# MotoDiag Phase 100 — Video Frame Extraction

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a simulated video frame extraction module for media diagnostics. Models video metadata (filename, duration, resolution, fps, file size, format), generates frame extraction plans based on configurable time intervals or keyframe detection at scene changes, and returns structured VideoFrame objects with placeholder descriptions and tags. No actual video processing — operates on metadata models to define the extraction contract that Claude Vision (Phase 101) will consume.

CLI: `python -m pytest tests/test_phase100_video_frames.py -v`

Outputs: `src/motodiag/media/video_frames.py` (VideoFrameExtractor + models), 34 tests

## Logic
- VideoResolution model: width/height in pixels, computed aspect_ratio and human-readable label (480p, 720p, 1080p, 4K)
- VideoMetadata model: filename, duration_seconds, resolution, fps, file_size_bytes, format (MP4/MOV/AVI/MKV/WEBM enum). Computed total_frames, file_size_mb, bitrate_kbps.
- VideoFrame model: frame_number (0-based), timestamp_sec, description (text), tags (list[str]). Computed timestamp_display (MM:SS.mmm format).
- FrameExtractionConfig: interval_seconds, max_frames, start_time_sec, end_time_sec. effective_end_time() clamps to video duration.
- SceneChangeMarker: timestamp_sec, change_score (0.0-1.0), change_type (cut/dissolve/motion_spike/visual).
- VideoFrameExtractor.extract_frames(): generates timestamps at config.interval_seconds, capped by max_frames, returns VideoFrame list with placeholder descriptions via deterministic template rotation.
- VideoFrameExtractor.extract_keyframes(): filters SceneChangeMarkers by change_threshold, generates frames at significant scene change points. Falls back to simulated markers at ~5s intervals if none provided.
- VideoFrameExtractor.get_frame_at_timestamp(): returns a single frame at any valid timestamp. Validates bounds.
- VideoFrameExtractor.get_extraction_plan(): returns metadata about the plan (frame_count, timestamps, coverage_percent) without extracting.
- Placeholder generators: _generate_placeholder_description() and _generate_placeholder_tags() use deterministic rotation over motorcycle-relevant templates (angles, components, lighting conditions).

## Key Concepts
- Pydantic models with computed properties (aspect_ratio, total_frames, bitrate_kbps, timestamp_display)
- VideoFormat enum for supported container formats
- Simulated extraction — no OpenCV, no actual video files, no external deps
- FrameExtractionConfig with start/end time windowing and max_frames cap
- SceneChangeMarker with threshold-based keyframe filtering
- Deterministic placeholder generation via index-based template rotation
- Extraction plan preview via get_extraction_plan() (metadata only, no frame objects)

## Verification Checklist
- [x] VideoResolution: aspect ratio, label for 4K/1440p/1080p/720p/480p/small, str (8 tests)
- [x] VideoMetadata: basic fields, total_frames, file_size_mb, bitrate, format enum (5 tests)
- [x] VideoFrame: basic fields, timestamp_display MM:SS.mmm, defaults (4 tests)
- [x] FrameExtractionConfig: defaults, effective_end_time with None/clamped/within (4 tests)
- [x] SceneChangeMarker: basic fields (1 test)
- [x] extract_frames: count, max_frames cap, increasing frame numbers, interval timestamps, placeholder descriptions/tags, start offset, end boundary, start=end raises ValueError (9 tests)
- [x] extract_keyframes: with markers, keyframe tag, simulated fallback, max_frames cap, all below threshold (5 tests)
- [x] get_frame_at_timestamp: valid, negative raises, beyond duration raises, zero (4 tests)
- [x] get_extraction_plan: frame count, coverage percent, empty plan, timestamps list (4 tests)

## Risks
- Placeholder descriptions are static templates — in production, Claude Vision fills real content
- SceneChangeMarker simulation is simplistic (fixed intervals) — real implementation needs pixel-level analysis
- No frame image data — this module produces metadata only; actual image bytes come from a video backend

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (video_frames.py) |
| Tests | 34 |
| Models | 6 (VideoFormat, VideoResolution, VideoMetadata, VideoFrame, FrameExtractionConfig, SceneChangeMarker) |
| Extractor methods | 4 (extract_frames, extract_keyframes, get_frame_at_timestamp, get_extraction_plan) |
| External deps | 0 (pure Pydantic) |

Key finding: The simulated extraction approach cleanly separates the "what frames to extract" logic from actual video processing. The VideoFrameExtractor defines the full contract (configs, timestamps, frame numbering) that a real video backend would implement, while producing testable output with zero external dependencies.
