# Report document shape conventions

**Source of truth:** `motodiag.reporting.builders` + `motodiag.reporting.renderers`.
**Established by:** Phase 182 (initial shape + 3 builders + 2 renderers).
**Extended by:** Phase 192 (videos + Vision findings sections; this document).
**Filed at:** Phase 192 v1.0.1 architect-side deliverable, pre-Builder dispatch.

This document captures the existing dict-based `ReportDocument` shape conventions established by Phase 182 + the Phase 192 extension for Phase 191B videos + Vision findings. Future contributors extending the shape (Phase 193+) inherit conventions by reference rather than re-deriving from precedent. Audit-trail-preservation discipline per Phase 191C v1.0.1.

The existing shape is intentionally a freeform `dict[str, Any]` (typed as `ReportDocument = dict[str, Any]` in `builders.py`). Phase 192 v1.0.1 reshape preserved that choice (back-compat with Phase 182's three builders + two renderers) and deferred typed-Pydantic migration to **F32** with a measurable promotion trigger (third report-consuming surface).

## Top-level shape

Every `ReportDocument` is a dict with these top-level keys:

```python
{
    "title": str,                      # Required. e.g., "Diagnostic session report #N"
    "subtitle": Optional[str],         # Vehicle line, shop+customer, etc.; None when missing
    "issued_at": str (ISO 8601 UTC),   # Required. Generation timestamp; NOT session timestamp.
    "sections": list[dict],            # Required. Ordered list of section dicts; may be empty.
    "footer": str,                     # Required. One-line attribution; e.g., "Session N · MotoDiag".
}
```

**Required fields**: `title`, `issued_at`, `sections`, `footer`. Builders always populate these (even with placeholder values when source data is missing).

**Optional fields**: `subtitle`. When the resource lacks a natural subtitle (e.g., session with no vehicle metadata), set explicitly to `None` — don't omit the key. Renderers check `if doc.get("subtitle")`; missing key vs explicit `None` both render the same way, but explicit `None` documents intent.

**Naming**: snake_case throughout. No `camelCase`. Phase 182 established this convention; Phase 192 extension preserves it.

## Section shape variants

Each item in the top-level `sections` list is a dict with `heading: str` plus exactly one shape field. Phase 182 established four variants:

### Variant 1 — `rows` (labeled key-value list)

```python
{
    "heading": "Vehicle",
    "rows": [
        ("Make", "Honda"),
        ("Model", "CBR600RR"),
        ("Year", "2005"),
    ],
}
```

`rows` is a list of `(label, value)` tuples. Both elements are strings. Renderers project as a 2-column key-value grid (text renderer indents the label-value pairs; PDF renderer uses a borderless table).

When a value is missing, builders use the em-dash sentinel `"—"` (not "N/A", not empty string, not None). Phase 182 helper `_money(cents)` returns `"—"` on None input; the convention applies to all missing-value renderings.

### Variant 2 — `bullets` (unordered list)

```python
{
    "heading": "Reported symptoms",
    "bullets": ["Engine hesitates at idle", "Black smoke at full throttle"],
}
```

`bullets` is a list of strings. Renderers project as a bullet list.

### Variant 3 — `table` (multi-column table)

```python
{
    "heading": "Fault codes",
    "table": {
        "columns": ["Code", "Description", "Severity"],
        "rows": [
            ["P0171", "System Too Lean (Bank 1)", "medium"],
            ["P0420", "Catalyst System Efficiency Below Threshold", "low"],
        ],
    },
}
```

`table` is a dict with `columns: list[str]` and `rows: list[list[str]]`. Each row's length must equal `len(columns)`. Renderers project as a multi-column table with header row.

### Variant 4 — `body` (paragraph)

```python
{
    "heading": "Notes",
    "body": "Customer reports issue began after recent oil change at independent shop.",
}
```

`body` is a single string. Multi-line bodies use `\n` separators; renderers split paragraphs on `\n`.

### Variant 5 (Phase 192 NEW) — `videos` (per-video card list with nested findings)

```python
{
    "heading": "Videos",
    "videos": [
        {
            "video_id": 42,
            "filename": "recording-2026-05-05-1432.mp4",
            "captured_at": "2026-05-05T14:32:18+00:00",
            "duration_ms": 5200,
            "size_bytes": 1572864,
            "interrupted": False,
            "analysis_state": "analyzed",  # one of: pending, analyzing, analyzed, analysis_failed, unsupported
            "analyzing_started_at": "2026-05-05T14:32:30+00:00",  # ISO; None if never started
            "findings": {                  # only present when analysis_state == "analyzed"
                "overall_assessment": "Likely worn piston rings or valve seals.",
                "findings_list": [
                    {
                        "finding_type": "smoke",
                        "description": "Blue smoke from exhaust during throttle blip",
                        "confidence": 0.85,
                        "severity": "high",
                        "location_in_image": "lower right, exhaust pipe",
                    },
                    # ...
                ],
                "image_quality_note": "Frames are well-lit and in focus.",
                "frames_analyzed": 5,
                "model_used": "claude-sonnet-4-6",
                "cost_estimate_usd": 0.0354,
            },
        },
        # ... more video cards
    ],
}
```

**Why `videos` is a new section variant rather than a `table` or `body`**: tables don't support nested per-row sub-shapes; bodies don't structure per-video metadata. Phase 192 introduces `videos` because the per-video card with optional nested findings is genuinely a new structural shape, not a re-use of an existing one.

**The `findings` sub-shape mirrors Phase 191B's `VisualAnalysisResult` Pydantic model** verbatim (see `motodiag.media.vision_analysis.VisualAnalysisResult`). The nesting choice + design rationale is documented in the next section.

**Required fields per video card**: `video_id`, `filename`, `captured_at`, `duration_ms`, `size_bytes`, `interrupted`, `analysis_state`, `analyzing_started_at`. These are the metadata fields surfaced to viewers regardless of analysis status.

**Optional `findings`**: present only when `analysis_state == "analyzed"`. When `analysis_state` is `pending` / `analyzing` / `analysis_failed` / `unsupported`, the `findings` key is **absent from the dict** (not present-with-None). Renderers check `if "findings" in video` rather than `if video.get("findings") is not None`. The absent-vs-None distinction matches Phase 182's existing convention for the top-level `subtitle` field.

## Why videos+findings nest THIS WAY rather than as a peer top-level section

Phase 192 v1.0.1 architect deliverable Section 2: choose between two valid representations.

**Option (a): Vision findings as a TOP-LEVEL section, peer to Videos.**

```python
{"heading": "Videos", "videos": [...metadata only...]},
{"heading": "Vision findings", "bullets": [...cross-video summary...]},
```

Pro: maps cleanly to the PDF renderer's "Vision findings" cross-video summary block (which a print-format report would naturally have as its own section).
Con: requires the PDF renderer to walk the videos array AND know which findings belong to which video — the section-level shape doesn't encode the per-video relationship.

**Option (b): Vision findings nested under each video card.**

```python
{
    "heading": "Videos",
    "videos": [
        {..., "findings": {...}},
        {..., "findings": {...}},
        ...
    ],
}
```

Pro: maps cleanly to mobile viewer's per-video-expansion UX from Phase 191B (each video card expands to show its own findings inline). Single canonical representation; consumers project differently — mobile renders per-video-card-with-expandable-findings; PDF renderer aggregates findings across the videos array to produce the cross-video summary.
Con: PDF renderer needs aggregation logic to produce the cross-video summary view; can't just hand the section dict to a generic renderer.

**Decision: Option (b).**

Reasons:

1. **Single canonical representation; consumers project differently** is the right shape for substrate-extension work. Two parallel representations of the same logical data is the F9 family pattern (per `docs/patterns/f9-mock-vs-runtime-drift.md` subspecies (ii) generalized) — every Track-I phase since Phase 191B has been hardening against this drift class.
2. **Per-video-relationship is intrinsic to the data**, not an artifact of presentation. A finding without its video is contextless ("blue smoke" — from which recording?); a video with findings detached needs cross-referencing to reattach. Encoding the relationship structurally avoids the cross-reference re-derivation work at every consumer.
3. **PDF aggregation logic is a one-time renderer cost** (write once in `renderers.py`); Option (a)'s detached-findings-section would require composer work (build the aggregated section) PLUS consumer work (mobile would need to walk the aggregated section to re-attach findings to videos for the per-card UX). Composer + multiple consumers > single renderer.
4. **Future analysis types extend cleanly.** When Phase 195+ adds per-video audio analysis, OBD-time-series-correlated-with-video, or any other per-video derived analysis, those nest as sibling keys under each video card (`audio_analysis`, `obd_correlation`) — no new top-level section needed per analysis type. Option (a) would require a new top-level section per new analysis type, accumulating section sprawl.

The trade-off (PDF renderer needs aggregation logic vs composer needs to build the aggregated section) was decided in favor of Option (b)'s single canonical shape. PDF renderer extension is 192B's scope; the design choice doesn't block 192's substrate extension.

## Empty-state conventions

Phase 182 established two patterns:

### Pattern 1 — Omit-when-empty (most sections)

For `symptoms`, `fault_codes`, `repair_steps`, `notes`: the builder appends the section ONLY if the source data is non-empty.

```python
symptoms = row.get("symptoms") or []
if symptoms:
    sections.append({
        "heading": "Reported symptoms",
        "bullets": [str(s) for s in symptoms],
    })
```

Renderers iterate `doc.get("sections") or []`; absent sections render as nothing (not as a blank section with a heading-then-nothing).

### Pattern 2 — Always-present (vehicle, timeline, footer)

For `vehicle` and `timeline` sections (and the top-level `footer`): builders always append, even when source data is missing. Missing values within these sections use the `"—"` em-dash sentinel.

```python
sections.append({
    "heading": "Vehicle",
    "rows": [
        ("Make", vehicle_make or "—"),
        ("Model", vehicle_model or "—"),
        ("Year", str(vehicle_year) if vehicle_year else "—"),
    ],
})
```

The pattern signals: "vehicle metadata was checked; here's what we found" — even when nothing was found. Hidden vehicle section would imply absence of the check itself.

### Phase 192 extension: which pattern for `videos`?

**Decision: Pattern 1 (omit-when-empty).**

When a session has zero videos, the `videos` section is NOT appended to `sections`. The `if videos:` check at the composer mirrors Phase 182's existing `if symptoms:` pattern.

Rationale: videos are an OPTIONAL capture mechanism (per Phase 192 plan I3 decision). Most sessions don't capture videos; rendering a placeholder "No videos captured" section on every report would be structural noise. Phase 192's mobile viewer plan v1.0.1 + Section I3 explicitly decided "hide videos card entirely when zero videos" — composer omitting the section enforces this server-side; mobile renderer doesn't need explicit hide-logic.

This differs from Phase 192's mobile plan I1 + I2 + I8 which use **render-with-placeholder** for fault codes / diagnosis / symptoms. The asymmetry is correct: fault codes / symptoms / diagnosis are diagnostic-process steps where absence is meaningful ("checked, none found" vs "didn't check at all"). Videos are a capture mechanism where absence is not meaningful (most sessions don't capture).

## Renderers

Phase 182 ships two renderers in `motodiag.reporting.renderers`:

### `TextReportRenderer`

`content_type = "text/plain; charset=utf-8"`. Always available, no deps. Used as fallback when reportlab is unavailable. Produces plain-text output with markdown-like heading underlines.

### `PdfReportRenderer`

`content_type = "application/pdf"`. **Uses reportlab Platypus** (not WeasyPrint). PDF generation via `reportlab.platypus.SimpleDocTemplate` + `Paragraph` / `Table` / `Spacer` flowables.

**This is a significant correction to Phase 192 plan v1.0's locked decision** which specified WeasyPrint. The plan's framing ("WeasyPrint over wkhtmltopdf as the lib choice") was made without knowing Phase 182 had already chosen reportlab. Phase 192 v1.0.1 reshape preserves Phase 182's existing choice (back-compat with PDF rendering already in production). 192B's PDF template extension work uses reportlab Platypus shapes — no Jinja2 templates, no CSS, no `@page` rules.

The reportlab vs WeasyPrint decision is settled by Phase 182's existing investment (renderer is 326 lines of working code). Future PDF format work uses reportlab. WeasyPrint considerations from plan v1.0 are moot.

### Renderer shape contract

Both renderers consume the same `ReportDocument` dict. Renderer interface (per `class ReportRenderer` in `renderers.py`):

```python
class ReportRenderer:
    content_type: str = "application/octet-stream"
    file_extension: str = ""
    def render(self, doc: ReportDocument) -> bytes: ...
```

Phase 192 introduces the `videos` section variant. **Renderer extension is in scope for Phase 192's Builder dispatch** — both `TextReportRenderer` and `PdfReportRenderer` need to handle the new section variant. PDF renderer's per-video-card-with-nested-findings rendering is the bulk of the renderer-side Phase 192 work; text renderer needs minimal extension (per-video block with nested findings indentation).

The renderer-extension work belongs to Phase 192 (substrate) NOT Phase 192B (feature). Phase 192's report viewer doesn't directly use the PDF renderer, but the substrate principle says: the new section variant IS substrate; rendering it across both consumers (text fallback + PDF) is substrate-completion.

## Naming consistency notes

Phase 182's existing fields use these conventions; Phase 192 extension preserves:

- `id` / `_id` suffix for foreign keys (`session_id`, `video_id`).
- `_at` suffix for ISO timestamps (`captured_at`, `analyzing_started_at`, `issued_at`).
- `_ms` / `_bytes` / `_usd` suffixes for unit-bearing scalars (`duration_ms`, `size_bytes`, `cost_estimate_usd`).
- `_state` suffix for enum-typed status fields (`analysis_state`).
- Booleans without `is_` prefix where the field name is naturally a predicate (`interrupted`).
- `findings_list` (Phase 191B `VisualAnalysisResult` convention) NOT `findings` for the inner list-of-findings — `findings` is the container object.

When in doubt, look at the existing builder + Pydantic models first.

## Shape registry (current top-level fields + section variants)

For quick reference:

**Top-level keys:** `title`, `subtitle`, `issued_at`, `sections`, `footer`.

**Section shape variants:**
- `rows` (Phase 182): `list[(label, value)]`
- `bullets` (Phase 182): `list[str]`
- `table` (Phase 182): `{columns: list[str], rows: list[list[str]]}`
- `body` (Phase 182): `str`
- `videos` (Phase 192 NEW): `list[VideoCard]` where each `VideoCard` is a dict with required metadata fields + optional `findings` sub-shape

**Empty-state patterns:**
- Omit-when-empty: `symptoms`, `fault_codes`, `repair_steps`, `notes`, `videos` (Phase 192).
- Always-present (with `"—"` sentinel for missing values): `vehicle`, `timeline`.

## Maintenance

Update this doc when:

- A new section shape variant is introduced (e.g., a future `chart` variant for time-series data, an `image` variant for embedded annotated frames).
- Empty-state patterns change for an existing section.
- Naming conventions evolve (in which case the convention change should be applied repo-wide, not just documented as a divergence).
- A new builder is added to `motodiag.reporting.builders` (the "Phase Y builders" pattern; document the new builder's section list + any new section variants it introduces).

The doc is a working document, not a sealed-history record. Per Phase 191C v1.0.1's audit-trail-preservation principle: append updates to a "Revision history" section at the bottom rather than overwriting earlier content. Future contributors reading the doc see both the current shape and how it evolved.

## Related docs

- `docs/architecture/auth-policy.md` — F29 ADR; auth posture for the routes that consume these documents.
- `docs/patterns/f9-mock-vs-runtime-drift.md` — F9 family + the parallel-state-store anti-pattern that drove Option (b)'s single-canonical-representation choice.
- `motodiag.reporting.builders` source — Phase 182's three builders.
- `motodiag.reporting.renderers` source — Phase 182's two renderers.
- `motodiag.media.vision_analysis.VisualAnalysisResult` — Phase 191B Pydantic model whose shape mirrors the nested `findings` sub-object.
