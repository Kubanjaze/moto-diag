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
# F34 xfail marker
# ---------------------------------------------------------------------------
#
# First-run finding (Phase 192B Commit 1, 2026-05-05): reportlab's
# default render embeds non-deterministic metadata — `CreationDate`,
# `ModDate`, and a random PDF trailer `/ID` pair. Concrete diff
# captured at index ~2310 of a representative session render: the
# `/ID` hex pair varies per render even for byte-identical inputs.
# F34 filed in mobile FOLLOWUPS with reproduction.
#
# Per Phase 192B plan v1.0 + commit-discipline: do NOT expand
# Commit 1's scope to fix the non-determinism. The test is the
# load-bearing addition; the fix lands as a separate atomic commit
# (Commit 1.5 or similar) before mobile work continues — share-flow
# correctness depends on this property, so the fix is a hard
# prerequisite for Commit 2.
#
# `strict=True`: when F34 fix lands and these tests start passing,
# pytest will FAIL the suite to signal "remove this xfail marker"
# — exactly the un-xfailing pattern Phase 191C 5b used for clean-
# baseline gate tests.

_F34_XFAIL = pytest.mark.xfail(
    strict=True,
    reason=(
        "F34: reportlab embeds non-deterministic CreationDate / "
        "ModDate / trailer-/ID by default. Fix lands in Phase 192B "
        "Commit 1.5 (follow-up, before mobile Commit 2) — likely "
        "via SimpleDocTemplate(invariant=True) or explicit "
        "canvas.setCreator()/setProducer() + zeroed metadata. "
        "When fix lands, this test un-xfails to PASS and the "
        "marker should be removed."
    ),
)


@pytest.mark.skipif(not PDF_AVAILABLE, reason="reportlab not installed")
class TestDeterministicPdfRender:
    """If any of these tests fail, file F34 with the failure message.
    Expected fix paths (in order of preference):
    1. ``SimpleDocTemplate(invariant=True)`` — reportlab's documented
       deterministic-output flag (verify it exists in the installed
       version).
    2. Override creation timestamp via ``canvas.setProducer()`` /
       ``canvas.setCreator()`` + zeroing the creation-date metadata.
    3. Seed PDF trailer ID deterministically.
    """

    @_F34_XFAIL
    def test_same_doc_same_renderer_produces_identical_bytes(self):
        """Two renders of the same document via the same renderer
        instance produce byte-identical PDFs."""
        renderer = PdfReportRenderer()
        doc = _sample_doc()

        bytes_a = renderer.render(doc)
        bytes_b = renderer.render(doc)

        assert bytes_a == bytes_b, (
            f"PDF render is non-deterministic with same renderer "
            f"instance. Diff at first byte: "
            f"{_first_diff_byte(bytes_a, bytes_b)}. "
            f"File F34 if this is the first failure."
        )

    @_F34_XFAIL
    def test_same_doc_fresh_renderer_each_call_produces_identical_bytes(self):
        """Two renders of the same document via FRESH renderer
        instances produce byte-identical PDFs. Guards against
        renderer-instance state mattering for output (it shouldn't)."""
        doc = _sample_doc()

        bytes_a = PdfReportRenderer().render(doc)
        bytes_b = PdfReportRenderer().render(doc)

        assert bytes_a == bytes_b, (
            f"PDF render is non-deterministic across renderer "
            f"instances. Diff at first byte: "
            f"{_first_diff_byte(bytes_a, bytes_b)}. "
            f"File F34 if this is the first failure."
        )

    def test_different_titles_produce_different_bytes(self):
        """Sanity check: actual content differences DO produce
        different bytes. If this fails, the determinism guarantee
        is meaningless (renderer ignored the input change). NOT
        marked xfail — this MUST pass even with non-determinism
        because content-sensitivity is a separate property from
        time-sensitivity."""
        renderer = PdfReportRenderer()
        bytes_a = renderer.render(_sample_doc(title="Report A"))
        bytes_b = renderer.render(_sample_doc(title="Report B"))

        assert bytes_a != bytes_b, (
            "Renderer produced identical bytes for documents with "
            "different titles. The determinism check is meaningless "
            "without input-sensitivity verification."
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
