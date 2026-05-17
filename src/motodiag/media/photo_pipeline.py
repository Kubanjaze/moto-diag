"""Photo normalization pipeline — Phase 194 (Commit 0) Section K.

Single canonical storage format for ``work_order_photos`` uploads:

1. Decode raw bytes (HEIC via pillow-heif when registered; otherwise
   PIL handles JPEG/PNG natively).
2. Read EXIF orientation tag, rotate pixels to upright, strip EXIF.
3. Resize to 2048px long-edge bound while preserving aspect ratio
   (no upscaling — small inputs pass through).
4. Encode JPEG quality 85.

Trade-off accepted (per Phase 194 v1.0 Section K): lossy transformation.
Original capture is not preserved; what's stored is the canonical form.
Phase 194B's AI analysis can re-litigate IF original-pixel access matters
(edge detection tasks where JPEG compression artifacts could confuse the
model). Default for 194: store the canonical form.

Why this is substrate-time work, not retrofit: each consumer that has to
honor EXIF orientation independently is drift risk (the canonical "why
are all my photos sideways" smoke-gate finding). Phase 194 has 1 consumer
today (mobile WorkOrderPhotosSection); Phase 194B will add a 2nd (AI
analysis); a future PDF integration may add a 3rd. Building once at the
write boundary is much smaller than retrofitting after 3 consumers exist.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageOps


_log = logging.getLogger(__name__)

# Canonical pipeline parameters (per Section K).
LONG_EDGE_BOUND_PX = 2048
JPEG_QUALITY = 85
JPEG_FORMAT = "JPEG"


# pillow-heif registers itself as a PIL plugin; the import side-effect
# is required for ``Image.open()`` to recognize HEIC/HEIF inputs. Guard
# the import so a missing optional dep degrades gracefully — JPEG/PNG
# inputs still work; HEIC inputs raise ``UnsupportedImageFormatError``.
try:
    import pillow_heif  # type: ignore[import-untyped]

    pillow_heif.register_heif_opener()
    _HEIF_AVAILABLE = True
except ImportError:  # pragma: no cover — install gate verified at boot
    _HEIF_AVAILABLE = False
    _log.warning(
        "pillow-heif not installed; HEIC photo uploads will fail. "
        "Install with: pip install pillow-heif",
    )


class UnsupportedImageFormatError(ValueError):
    """Raised when the uploader sent a format the pipeline can't decode.

    Distinct from ``ImageDecodeError`` — this is "format recognized but
    backend lacks the codec" (e.g., HEIC without pillow-heif). Routes
    map to HTTP 415 Unsupported Media Type.
    """


class ImageDecodeError(ValueError):
    """Raised when the uploaded bytes are corrupt or not an image.

    Routes map to HTTP 422 Unprocessable Entity.
    """


@dataclass(frozen=True)
class NormalizedPhoto:
    """Result of ``normalize_photo``: the canonical JPEG + dimensions."""

    jpeg_bytes: bytes
    width: int
    height: int


def normalize_photo(raw_bytes: bytes) -> NormalizedPhoto:
    """Decode → orient → resize → encode → return ``NormalizedPhoto``.

    Pure function — testable without route harness. Raises
    ``ImageDecodeError`` (corrupt/non-image input) or
    ``UnsupportedImageFormatError`` (HEIC without pillow-heif).
    """
    if not raw_bytes:
        raise ImageDecodeError("empty payload")

    try:
        img = Image.open(io.BytesIO(raw_bytes))
        # Force-load before any operation so the codec actually runs
        # (PIL is lazy by default; ``.load()`` surfaces decode errors
        # eagerly rather than at unpredictable later access).
        img.load()
    except Image.UnidentifiedImageError as exc:
        raise ImageDecodeError(
            f"unrecognized image format: {exc!s}"
        ) from exc
    except OSError as exc:
        # PIL raises OSError for HEIF inputs when the plugin isn't
        # registered. Detect and re-raise as the typed format error
        # so the route layer can translate to 415.
        msg = str(exc).lower()
        if "heif" in msg or "heic" in msg:
            raise UnsupportedImageFormatError(
                "HEIC/HEIF input but pillow-heif is not installed"
            ) from exc
        raise ImageDecodeError(f"image decode failed: {exc!s}") from exc

    # Step 2: EXIF orientation → upright pixels + strip EXIF.
    # ``ImageOps.exif_transpose`` is the canonical way to honor
    # orientation; it returns a new image with pixels rotated and
    # the EXIF orientation tag removed.
    img = ImageOps.exif_transpose(img)

    # Step 3: Convert mode if needed (JPEG can't encode RGBA / palette).
    # P-mode (palette) GIFs and RGBA PNGs both lose alpha at this step;
    # acceptable trade-off for the canonical format choice.
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Step 4: Resize to long-edge bound, preserving aspect ratio.
    # No upscaling — small inputs pass through unchanged.
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > LONG_EDGE_BOUND_PX:
        scale = LONG_EDGE_BOUND_PX / float(long_edge)
        new_w = int(round(w * scale))
        new_h = int(round(h * scale))
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        w, h = new_w, new_h

    # Step 5: Encode JPEG quality 85; ``optimize=True`` for smaller
    # files at no quality cost.
    buf = io.BytesIO()
    img.save(
        buf,
        format=JPEG_FORMAT,
        quality=JPEG_QUALITY,
        optimize=True,
    )
    return NormalizedPhoto(
        jpeg_bytes=buf.getvalue(), width=w, height=h,
    )


def heif_available() -> bool:
    """Whether HEIC/HEIF decoding is wired up at this boot.

    Routes can use this to short-circuit on HEIC uploads with a clearer
    error message than the lazy decode path produces.
    """
    return _HEIF_AVAILABLE
