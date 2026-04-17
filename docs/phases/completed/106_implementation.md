# MotoDiag Phase 106 — Media-Enhanced Diagnostic Reports

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-16

## Goal
Build a ReportGenerator class that assembles comprehensive diagnostic reports combining AI analysis with media evidence (audio clips, video frames, spectrograms, photos). Produces detailed text reports for CLI display, brief one-paragraph summaries for quick review, and supports merging multiple reports for the same vehicle. Reports are the final output artifact of a diagnostic session.

CLI: `python -m pytest tests/test_phase106_reports.py -v`

Outputs: `src/motodiag/media/reports.py` (ReportGenerator + DiagnosticReport + MediaAttachment), 26 tests

## Logic
- MediaAttachment model: attachment_id, media_type (audio_clip/video_frame/spectrogram/photo), filename, timestamp, description, analysis_summary, tags, created_at
- DiagnosticReport model: report_id, vehicle_context dict, symptoms list, diagnosis, diagnosis_details list, confidence (high/medium/low/uncertain), confidence_score (0.0-1.0), attachments list, recommendations list, notes, generated_at, session_id
- DiagnosticReport properties: attachment_count, has_media_evidence, get_attachments_by_type()
- ReportGenerator.generate_report(): assembles DiagnosticReport from all parameters, validates confidence enum
- ReportGenerator.add_attachment(): adds MediaAttachment to existing report, validates media_type enum
- ReportGenerator.format_text_report(): produces multi-line CLI output with sections: Header (ID, date, session), Vehicle, Symptoms, Diagnosis (with confidence), Findings, Media Evidence (with timestamps), Recommendations, Notes
- ReportGenerator.format_summary(): one-paragraph summary: "[Vehicle] presented with [symptoms]. Diagnosis ([confidence]): [diagnosis]. Evidence: [media counts]."
- ReportGenerator.merge_reports(): combines symptoms, details, attachments, recommendations from multiple reports; deduplicates symptoms and recommendations; uses highest confidence from any report

## Key Concepts
- MediaType enum: audio_clip, video_frame, spectrogram, photo — covers all diagnostic media sources
- ConfidenceLevel enum: high, medium, low, uncertain — qualitative confidence ratings
- Text report format designed for CLI display with section headers and numbered lists
- Summary format designed for quick review — single paragraph with vehicle, symptoms, diagnosis, confidence, evidence counts
- Report merging deduplicates symptoms and recommendations while preserving all attachments
- Confidence escalation on merge: uses the highest confidence from any input report
- Vehicle context is a free-form dict — no rigid schema, adapts to whatever vehicle info is available
- Reports are the bridge between the AI diagnostic engine (Track C) and the user-facing interface (Tracks D, F, H, I)

## Verification Checklist
- [x] MediaAttachment: creation, all media types, with tags (3 tests)
- [x] DiagnosticReport: creation, has_media_evidence, get_attachments_by_type (3 tests)
- [x] generate_report: basic, all fields, invalid confidence raises, empty report (4 tests)
- [x] add_attachment: single, multiple, invalid media_type raises (3 tests)
- [x] format_text_report: full sections, minimal, with session_id (3 tests)
- [x] format_summary: basic, no vehicle, with evidence, no evidence, many symptoms truncated (5 tests)
- [x] merge_reports: two reports, empty raises, preserves attachments, single report (4 tests)

## Risks
- Reports are in-memory only — no persistence to database or file export yet. Will connect to session storage in later phases.
- Text report format is fixed-width oriented for CLI. HTML/PDF export for web/mobile is Track H/I concern.

## Results
| Metric | Value |
|--------|-------|
| Files created | 1 (reports.py) |
| Tests | 26 |
| Models | 2 (DiagnosticReport, MediaAttachment) |
| Enums | 2 (MediaType, ConfidenceLevel) |
| Generator methods | 5 (generate_report, add_attachment, format_text_report, format_summary, merge_reports) |
| Report sections | 7 (Vehicle, Symptoms, Diagnosis, Findings, Media Evidence, Recommendations, Notes) |
| External deps | 0 (pure Python + Pydantic) |

Key finding: The report model is intentionally flexible — vehicle_context is a dict, not a rigid schema, so it works for any motorcycle make/model without requiring a complete vehicle database entry. The merge functionality enables building comprehensive reports from multiple diagnostic sessions on the same bike, which is common in real shop workflows.
