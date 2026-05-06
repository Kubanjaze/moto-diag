"""Phase 192B Commit 1 — deterministic PDF rendering regression guard.

Rendering the same ``ReportDocument`` twice should produce
byte-identical PDFs. This is the load-bearing property for:
- regression detection (we can byte-compare PDF goldens in tests)
- caching (CDN / proxy can cache `/pdf` responses by session id)
- audit trail (the same session always renders the same PDF for
  posterity, regardless of when it was rendered)

If reportlab embeds non-deterministic metadata (creation
timestamp, file ID, etc.) by default, this test FAILS on first
run. The failure tells us exactly what's non-deterministic. Per
the Phase 192B plan v1.0 Risks section + commit-discipline
discussion: do NOT expand Commit 1's scope to fix it. Let the
test fail; the failure documents F34's first concrete
reproduction; the fix lands in a follow-up commit.

Either outcome is information; neither is a Commit 1 blocker.

If the test passes on first run, that's a free architectural
property — substrate produces deterministic bytes, F34 doesn't get
filed, share-flow correctness has a regression-protected guarantee
from this commit forward.
"""

from __future__ import annotations

import pytest

from motodiag.reporting.renderers import (
    PDF_AVAILABLE,
    PdfReportRenderer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_doc(title: str = "Diagnostic session report #42") -> dict:
    """A representative ReportDocument with all 5 section variants
    populated. Covers the surface area an actual session render
    exercises so the determinism check holds for the real shape, not
    just a degenerate case."""
    return {
        "title": title,
        "subtitle": "2005 Honda CBR600",
        "issued_at": "2026-05-05T17:42:00+00:00",
        "sections": [
            {
                "heading": "Vehicle",
                "rows": [
                    ("Make", "Honda"),
                    ("Model", "CBR600"),
                    ("Year", "2005"),
                ],
            },
            {
                "heading": "Reported symptoms",
                "bullets": ["Engine hesitates at idle", "Black smoke at full throttle"],
            },
            {
                "heading": "Fault codes",
                "table": {
                    "columns": ["Code", "Description", "Severity"],
                    "rows": [
                        ["P0171", "System Too Lean (Bank 1)", "medium"],
                    ],
                },
            },
            {
                "heading": "Notes",
                "body": "Customer reports issue began after recent oil change.",
            },
            {
                "heading": "Videos",
                "videos": [
                    {
                        "video_id": 42,
                        "filename": "recording.mp4",
                        "captured_at": "2026-05-05T14:32:18+00:00",
                        "duration_ms": 5200,
                        "size_bytes": 1572864,
                        "interrupted": False,
                        "analysis_state": "analyzed",
                        "analyzing_started_at": "2026-05-05T14:32:30+00:00",
                        "findings": {
                            "overall_assessment": "Likely worn rings.",
                            "findings": [
                                {
                                    "finding_type": "smoke",
                                    "description": "Blue smoke from exhaust",
                                    "confidence": 0.85,
                                    "severity": "high",
                                    "location_in_image": "lower right",
                                },
                            ],
                            "image_quality_note": "Frames well-lit.",
                            "frames_analyzed": 5,
                            "model_used": "claude-sonnet-4-6",
                            "cost_estimate_usd": 0.0354,
                        },
                    },
                ],
            },
        ],
        "footer": "MotoDiag — Session 42",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# F34 closed at Commit 1.5 (un-xfailed)
# ---------------------------------------------------------------------------
#
# First-run finding (Phase 192B Commit 1, 2026-05-05): reportlab's
# default render embeds non-deterministic metadata — `CreationDate`,
# `ModDate`, and a random PDF trailer `/ID` pair. Concrete diff
# captured at index ~2310 of a representative session render.
#
# F34 fix landed at Commit 1.5: ``PdfReportRenderer`` gains opt-in
# ``deterministic=True`` constructor parameter that propagates
# ``invariant=True`` through SimpleDocTemplate → Canvas →
# PDFDocument, zeroing the wall-clock timestamps + seeding the
# trailer ``/ID`` deterministically. POST route (preset-filtered
# share-flow callers) opts in; GET route preserves the default
# non-deterministic behavior for revision-tracking callers.
#
# These tests now pass ``deterministic=True`` explicitly and serve
# as the regression guard for the new opt-in mode. The xfail
# markers were removed at Commit 1.5 per the un-xfailing pattern
# Phase 191C 5b established for clean-baseline gate tests.


@pytest.mark.skipif(not PDF_AVAILABLE, reason="reportlab not installed")
class TestDeterministicPdfRender:
    """Pin the deterministic-mode contract for share-flow callers.

    Every test in this class uses ``PdfReportRenderer(deterministic=True)``
    — the share-flow consumer's choice. Default-mode rendering
    (``deterministic=False``, the GET-route consumer's choice) is
    spec-compliant non-deterministic and intentionally NOT covered
    here; ``TestDefaultModeStillNonDeterministic`` below verifies
    the default-mode contract stays preserved.
    """

    def test_same_doc_same_renderer_produces_identical_bytes(self):
        """Two renders of the same document via the same
        deterministic renderer instance produce byte-identical PDFs."""
        renderer = PdfReportRenderer(deterministic=True)
        doc = _sample_doc()

        bytes_a = renderer.render(doc)
        bytes_b = renderer.render(doc)

        assert bytes_a == bytes_b, (
            f"PDF render is non-deterministic with deterministic=True "
            f"+ same renderer instance. Diff at first byte: "
            f"{_first_diff_byte(bytes_a, bytes_b)}."
        )

    def test_same_doc_fresh_renderer_each_call_produces_identical_bytes(self):
        """Two renders of the same document via FRESH deterministic
        renderer instances produce byte-identical PDFs. Guards against
        renderer-instance state mattering for output."""
        doc = _sample_doc()

        bytes_a = PdfReportRenderer(deterministic=True).render(doc)
        bytes_b = PdfReportRenderer(deterministic=True).render(doc)

        assert bytes_a == bytes_b, (
            f"PDF render is non-deterministic with deterministic=True "
            f"+ across renderer instances. Diff at first byte: "
            f"{_first_diff_byte(bytes_a, bytes_b)}."
        )

    def test_different_titles_produce_different_bytes(self):
        """Sanity check: deterministic mode still respects content
        differences. If this fails, the determinism contract has
        collapsed to "always emit identical bytes" which is wrong."""
        renderer = PdfReportRenderer(deterministic=True)
        bytes_a = renderer.render(_sample_doc(title="Report A"))
        bytes_b = renderer.render(_sample_doc(title="Report B"))

        assert bytes_a != bytes_b, (
            "Deterministic renderer produced identical bytes for "
            "documents with different titles. Content-sensitivity "
            "is independent of time-sensitivity; this MUST hold "
            "even in deterministic mode."
        )

    def test_get_renderer_factory_passes_deterministic_through(self):
        """Pin the factory contract: ``get_renderer('pdf',
        deterministic=True)`` returns a renderer that produces the
        same byte-identical output as ``PdfReportRenderer(
        deterministic=True)`` directly. Guards against the factory
        forgetting to plumb the kwarg."""
        from motodiag.reporting.renderers import get_renderer

        doc = _sample_doc()
        bytes_via_factory = get_renderer(
            "pdf", deterministic=True,
        ).render(doc)
        bytes_via_constructor = PdfReportRenderer(
            deterministic=True,
        ).render(doc)

        assert bytes_via_factory == bytes_via_constructor


@pytest.mark.skipif(not PDF_AVAILABLE, reason="reportlab not installed")
class TestDefaultModeStillNonDeterministic:
    """Pin the contract that ``deterministic=False`` (the default)
    preserves reportlab's spec-compliant non-deterministic
    behavior. Revision-tracking callers (existing GET ``/pdf``
    consumers, future audit-log consumers) rely on each render
    producing a unique trailer ``/ID`` per the PDF spec's "assist
    in identifying revisions" intent.

    If a future change accidentally flips the default to
    deterministic, this test catches it.
    """

    def test_default_mode_two_renders_diverge(self):
        """Two renders via the default-mode renderer should NOT be
        byte-identical. If they are, the default has drifted from
        spec-compliant non-determinism."""
        renderer = PdfReportRenderer()  # default: deterministic=False
        doc = _sample_doc()
        bytes_a = renderer.render(doc)
        bytes_b = renderer.render(doc)
        assert bytes_a != bytes_b, (
            "Default-mode PdfReportRenderer produced byte-identical "
            "output. If this is intentional (default flipped to "
            "deterministic=True), update this test + audit GET "
            "/pdf consumers for revision-tracking impact."
        )


def _first_diff_byte(a: bytes, b: bytes) -> str:
    """Return a human-readable description of the first byte where
    two byte strings diverge. Useful for diagnosing PDF non-
    determinism — typically the first diff is in the metadata
    creation-time or trailer-ID region near the file start or end."""
    if len(a) != len(b):
        return f"length mismatch: a={len(a)} b={len(b)}"
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            # Show a 32-byte window around the divergence point so
            # the failure message is actionable.
            start = max(0, i - 16)
            end = min(len(a), i + 16)
            return (
                f"index {i}: a={a[start:end]!r} vs b={b[start:end]!r}"
            )
    return "no diff found despite assertion (byte arrays must be equal)"
