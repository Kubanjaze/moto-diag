"""Real ffmpeg subprocess wrapper for Phase 191B video diagnostic pipeline.

Phase 100's ``media/video_frames.py`` provides the metadata-only contract
(VideoMetadata + VideoFrame + FrameExtractionConfig + VideoFrameExtractor
class with placeholder descriptions). This module is the real backend
that fulfills the contract — actual ffmpeg subprocess calls for frame
extraction + audio sidecar extraction + video validation.

Per Phase 191B v1.0 plan B2 sign-off: ``subprocess.run`` only — no
Python wrapper library (ffmpeg-python, imageio, etc.). The subprocess
boundary keeps the binary dependency explicit and the failure modes
honest (FFmpegMissing surfaces at module load AND at call time;
FFmpegFailed bubbles stderr verbatim for debugging).

Module-load detection: at import, we resolve the ffmpeg binary via
``shutil.which`` (or the ``FFMPEG_BIN_OVERRIDE`` env var when present
for tests). The resolved path is logged at INFO; absence is logged at
WARNING. The upload endpoint translates ``FFMPEG_BIN is None`` into a
503 ProblemDetail at request time so the operator sees a real error
instead of a generic 500.

Defaults per Phase 191B v1.0 plan B3:
    - 2 fps for the first 30s, 1 fps after that
    - capped at 60 frames total
    - 120s subprocess timeout (well over the 30s expected runtime for
      typical 30s-2min clips; soft-failure if a pathological video
      pegs the encoder)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-load detection
# ---------------------------------------------------------------------------


def _detect_ffmpeg() -> Optional[str]:
    """Resolve the ffmpeg binary path or return None if absent.

    Order of resolution:
        1. ``FFMPEG_BIN_OVERRIDE`` env var — used by tests to force
           absent ("" → None) or to point at a stub binary path. If set
           and the path exists, returns the path; if set to "" (empty),
           treats ffmpeg as absent; if set to a non-empty path that
           doesn't exist, returns None.
        2. ``shutil.which("ffmpeg")`` — system PATH lookup.
    """
    override = os.environ.get("FFMPEG_BIN_OVERRIDE")
    if override == "":
        return None
    if override is not None:
        return override if Path(override).exists() else None
    return shutil.which("ffmpeg")


FFMPEG_BIN: Optional[str] = _detect_ffmpeg()

if FFMPEG_BIN is None:
    _log.warning(
        "ffmpeg not found on PATH; video analysis pipeline will return "
        "503 until ffmpeg is installed. Set FFMPEG_BIN_OVERRIDE for "
        "testing.",
    )
else:
    _log.info("ffmpeg detected at: %s", FFMPEG_BIN)


# ---------------------------------------------------------------------------
# Defaults (per Phase 191B v1.0 plan B3)
# ---------------------------------------------------------------------------

#: Maximum frames extracted from any single video.
MAX_FRAMES = 60

#: ffmpeg ``-vf`` filter expression that yields ~2 fps for the first 30s
#: and ~1 fps after that. The expression assumes the source is 30 fps;
#: ``-vsync vfr`` lets the timing be variable so we don't force-pad.
#: Specifically: ``not(mod(n,15))`` keeps every 15th frame in the first
#: 30s window (≈2 fps at 30 fps source); ``not(mod(n,30))`` keeps every
#: 30th frame after (≈1 fps at 30 fps source). The ``+`` is logical OR
#: between the two windows.
FRAME_FILTER = (
    "select='lt(t\\,30)*not(mod(n\\,15))"
    "+gte(t\\,30)*not(mod(n\\,30))'"
)

#: subprocess timeout in seconds. 120s is well over the 30s expected
#: runtime for typical 30s-2min clips; tighter than the route handler's
#: own timeout (which is request-level, not subprocess-level).
SUBPROCESS_TIMEOUT_SEC = 120


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FFmpegMissing(RuntimeError):
    """Raised when the ffmpeg binary is not available on the system.

    Routes translate this into HTTP 503 with a ProblemDetail envelope
    explaining the install steps. Mobile sees an `unsupported` analysis
    state when the failure mode is detected post-upload.
    """


class FFmpegFailed(RuntimeError):
    """Raised when the ffmpeg subprocess returned non-zero or timed out.

    The original stderr is preserved on ``self.stderr`` for debugging.
    Routes translate this into ``analysis_state='unsupported'`` for
    the persistent video-is-malformed case.
    """

    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_frames(
    video_path: Path,
    output_dir: Path,
    max_frames: int = MAX_FRAMES,
) -> list[Path]:
    """Extract frames per the default Phase 191B sampling policy.

    Yields up to ``max_frames`` JPEG frames into ``output_dir`` named
    ``frame_001.jpg`` ... ``frame_NNN.jpg`` (zero-padded for sort
    stability). Returns the sorted list of generated paths. ``output_dir``
    is created if it doesn't exist.

    Args:
        video_path: Source video file (mp4 or any ffmpeg-readable format).
        output_dir: Directory for extracted JPEG frames. Created if
                    missing. Existing files with the same name pattern
                    will be overwritten by ``-y``.
        max_frames: Hard cap on number of frames extracted (default 60).

    Raises:
        FFmpegMissing: when the ffmpeg binary is not on PATH.
        FFmpegFailed: when ffmpeg exits non-zero or times out.
    """
    if FFMPEG_BIN is None:
        raise FFmpegMissing("ffmpeg binary not on PATH")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", str(video_path),
        "-vf", FRAME_FILTER,
        "-vframes", str(max_frames),
        "-vsync", "vfr",
        str(output_dir / "frame_%03d.jpg"),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as e:
        raise FFmpegFailed(
            f"ffmpeg timeout after {SUBPROCESS_TIMEOUT_SEC}s",
            stderr=str(e),
        ) from e

    if proc.returncode != 0:
        raise FFmpegFailed(
            f"ffmpeg exited {proc.returncode}",
            stderr=proc.stderr,
        )

    return sorted(output_dir.glob("frame_*.jpg"))


def extract_audio(
    video_path: Path,
    output_path: Path,
) -> Path:
    """Extract the audio track as an mp3 sidecar (mono, 44.1 kHz, 128 kbps).

    Per B4 sign-off the sidecar is created on every upload but the
    audio analysis path is deferred to Track G (audio-aware
    diagnostics). Storing the sidecar now keeps re-analysis cheap when
    Track G ships — no need to re-process the source video.

    Args:
        video_path: Source video file.
        output_path: Destination mp3 path. Parent directory is created
                     if missing. Overwritten by ``-y`` if present.

    Returns:
        The same ``output_path`` on success.

    Raises:
        FFmpegMissing: when the ffmpeg binary is not on PATH.
        FFmpegFailed: when ffmpeg exits non-zero or times out.
    """
    if FFMPEG_BIN is None:
        raise FFmpegMissing("ffmpeg binary not on PATH")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i", str(video_path),
        "-vn",            # no video
        "-ac", "1",       # mono
        "-ar", "44100",   # 44.1 kHz
        "-b:a", "128k",   # 128 kbps mp3
        str(output_path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as e:
        raise FFmpegFailed(
            f"ffmpeg audio extraction timeout after "
            f"{SUBPROCESS_TIMEOUT_SEC}s",
            stderr=str(e),
        ) from e

    if proc.returncode != 0:
        raise FFmpegFailed(
            f"ffmpeg audio extraction exited {proc.returncode}",
            stderr=proc.stderr,
        )

    return output_path


def validate_video(video_path: Path) -> dict:
    """Probe basic video metadata via ``ffmpeg -i``.

    ffmpeg writes container metadata to stderr (yes, stderr — that's
    what ``-i`` does without an output target). We parse the relevant
    fields out of the stderr text rather than shelling out to ffprobe;
    this keeps the ffmpeg-only dependency surface honest (some minimal
    builds ship ffmpeg without ffprobe).

    Returns a dict with the best-effort-parsed fields:
        {
            "width": int,
            "height": int,
            "duration_seconds": float,
            "codec": str,
            "fps": float,
        }

    Raises:
        FFmpegMissing: when the ffmpeg binary is not on PATH.
        FFmpegFailed: when ffmpeg cannot probe the file at all (e.g.,
            truncated, not a video, unreadable).
    """
    if FFMPEG_BIN is None:
        raise FFmpegMissing("ffmpeg binary not on PATH")

    # Run ffmpeg -i with no output target. Returncode is non-zero
    # because ffmpeg complains about no output, but stderr still
    # contains the parsed metadata block. We handle this by parsing
    # stderr regardless of exit code, then sanity-checking the parse.
    cmd = [FFMPEG_BIN, "-i", str(video_path)]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as e:
        raise FFmpegFailed(
            f"ffmpeg probe timeout after {SUBPROCESS_TIMEOUT_SEC}s",
            stderr=str(e),
        ) from e

    stderr = proc.stderr or ""

    # If stderr contains "Invalid data" or "could not find codec"
    # then the file is genuinely malformed.
    lowered = stderr.lower()
    if (
        "invalid data" in lowered
        or "could not find codec" in lowered
        or "moov atom not found" in lowered
        or "no such file or directory" in lowered
    ):
        raise FFmpegFailed(
            "ffmpeg could not probe the video (malformed or missing)",
            stderr=stderr,
        )

    return _parse_probe_stderr(stderr)


def _parse_probe_stderr(stderr: str) -> dict:
    """Extract width / height / duration / codec / fps from ffmpeg -i stderr.

    Best-effort regex parsing — fields default to sensible empties if
    the line shape isn't recognized. The route handler doesn't crash
    on missing fields; downstream code that needs a specific field
    must handle the default explicitly.
    """
    import re

    width = 0
    height = 0
    duration = 0.0
    codec = ""
    fps = 0.0

    # Duration line: "  Duration: 00:00:03.00, start: ..."
    m = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
        stderr,
    )
    if m:
        h, mn, s = m.groups()
        duration = int(h) * 3600 + int(mn) * 60 + float(s)

    # Video stream line:
    #   "Stream #0:0: Video: h264 (Constrained Baseline) ..., 320x240, ..., 30 fps, 30 tbr, ..."
    m = re.search(
        r"Stream\s*#\d+[:\.]\d+[^:]*:\s*Video:\s*([^\s,]+).*?(\d+)x(\d+)",
        stderr,
    )
    if m:
        codec = m.group(1)
        width = int(m.group(2))
        height = int(m.group(3))

    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", stderr)
    if m:
        fps = float(m.group(1))

    return {
        "width": width,
        "height": height,
        "duration_seconds": duration,
        "codec": codec,
        "fps": fps,
    }
