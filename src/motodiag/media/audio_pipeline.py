"""Audio metadata + format detection — Phase 195 (Commit 0).

**Risk #10 deviation from plan v1.0**: pydub + ffmpeg are not present in the
Phase 195 dev environment, and the canonical 16 kHz mono 16-bit PCM
normalization pipeline is only valuable when feeding cloud Whisper —
which is Phase 195B's job. Phase 195 stores audio bytes verbatim; the
"normalization" reduces to format detection + metadata extraction, which
is sufficient for Phase 195's use cases:

1. Backend stores audio at canonical disk path (format-agnostic).
2. Backend serves audio back via the file-stream endpoint
   (pass-through; the mobile player handles playback whatever the
   format is).
3. Backend keyword extraction (Section 2 γ) operates on
   ``preview_text`` from on-device STT, NOT on the audio bytes.

True normalization (resample to 16 kHz, transcode to PCM) is deferred
to Phase 195B, which will install ``pydub>=0.25`` + ``ffmpeg>=4`` as
required deps and use them to normalize audio for Whisper input.

Phase 195's ``inspect_audio`` returns:
- ``audio_format``: detected format (`'wav' | 'm4a' | 'ogg' | 'unknown'`).
- ``size_bytes``: raw byte length.
- ``sha256``: content hash for dedup.
- ``duration_ms``: parsed from format header when possible (WAV via
  ``wave`` module; M4A/Ogg fall back to mobile-supplied metadata).
- ``sample_rate_hz``: parsed from WAV header; 16000 default for M4A
  (Whisper canonical, what mobile is configured to capture at) /
  48000 default for Ogg.

The route layer trusts mobile-supplied ``duration_ms`` if header parsing
returns None, since the mobile audio recorder library reports it
authoritatively from its own framing.
"""

from __future__ import annotations

import hashlib
import io
import logging
import struct
import wave
from dataclasses import dataclass
from typing import Optional


_log = logging.getLogger(__name__)


# Canonical sample rate Phase 195 records at (matches Whisper input
# requirement so 195B's normalization is a transcode, not a resample).
DEFAULT_SAMPLE_RATE_HZ = 16000
# Common iOS / Android default sample rates we surface as fallbacks.
M4A_DEFAULT_SAMPLE_RATE_HZ = 16000
OGG_DEFAULT_SAMPLE_RATE_HZ = 48000


class UnsupportedAudioFormatError(ValueError):
    """Raised when the upload format isn't one of the recognized headers.

    Routes map to HTTP 415 Unsupported Media Type. Distinct from
    ``AudioDecodeError``: this is "we don't know what this is" vs
    "we recognized it but it's broken."
    """


class AudioDecodeError(ValueError):
    """Raised when format-detection succeeds but parsing fails.

    Routes map to HTTP 422 Unprocessable Entity.
    """


@dataclass(frozen=True)
class InspectedAudio:
    """Result of ``inspect_audio``: detected format + parsed metadata.

    ``duration_ms`` is None when the format header doesn't expose
    duration (e.g., M4A without parsing the moov atom). The route
    layer falls back to ``metadata.duration_ms`` from the mobile
    multipart payload in that case.
    """
    audio_format: str
    size_bytes: int
    sha256: str
    duration_ms: Optional[int]
    sample_rate_hz: int


def inspect_audio(raw_bytes: bytes) -> InspectedAudio:
    """Detect format + extract metadata from a raw audio upload.

    Phase 195 substrate: format-detection only. True normalization
    (resample, transcode) is deferred to Phase 195B per Risk #10.

    Recognized formats (header-magic-byte detection):
    - WAV: ``RIFF....WAVE``. Parsed via ``wave`` module for canonical
      duration + sample rate.
    - M4A / MP4: ``ftypM4A`` / ``ftypisom`` / ``ftypmp42`` at byte
      offset 4. Common iOS AVAudioRecorder default. Header detection
      only; duration falls back to mobile metadata.
    - Ogg: ``OggS`` at byte 0. Common Android default. Header
      detection only.

    Anything else raises ``UnsupportedAudioFormatError``.
    """
    if not raw_bytes:
        raise AudioDecodeError("empty audio payload")

    size_bytes = len(raw_bytes)
    sha256 = hashlib.sha256(raw_bytes).hexdigest()

    audio_format = _detect_format(raw_bytes)
    if audio_format == "wav":
        try:
            with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
                duration_ms = int(
                    1000 * wf.getnframes() / wf.getframerate(),
                )
                sample_rate_hz = wf.getframerate()
        except (wave.Error, EOFError, struct.error) as exc:
            raise AudioDecodeError(
                f"WAV header detected but parsing failed: {exc!s}",
            ) from exc
    elif audio_format == "m4a":
        # M4A duration parsing requires walking the moov atom (mp4
        # box format); not worth the implementation cost for Phase
        # 195. Mobile metadata is authoritative.
        duration_ms = None
        sample_rate_hz = M4A_DEFAULT_SAMPLE_RATE_HZ
    elif audio_format == "ogg":
        duration_ms = None
        sample_rate_hz = OGG_DEFAULT_SAMPLE_RATE_HZ
    else:
        raise UnsupportedAudioFormatError(
            f"unrecognized audio format (header bytes: "
            f"{raw_bytes[:16].hex()})",
        )

    return InspectedAudio(
        audio_format=audio_format,
        size_bytes=size_bytes,
        sha256=sha256,
        duration_ms=duration_ms,
        sample_rate_hz=sample_rate_hz,
    )


def _detect_format(raw_bytes: bytes) -> str:
    """Classify raw bytes by magic-number header. Returns 'wav' /
    'm4a' / 'ogg' / 'unknown'."""
    if len(raw_bytes) < 12:
        return "unknown"
    head = raw_bytes[:12]
    # WAV: 'RIFF' at 0 + 'WAVE' at 8.
    if head[0:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    # MP4 / M4A family: 'ftyp' at byte 4 + brand at byte 8.
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand in (b"M4A ", b"isom", b"mp42", b"mp41", b"M4B "):
            return "m4a"
    # Ogg: 'OggS' at byte 0.
    if head[0:4] == b"OggS":
        return "ogg"
    return "unknown"
