"""Audio metadata + format detection — Phase 195 (Commit 0).

**Architectural choice (Section 5 + Section K — verbatim storage with
explicit format tracking)**: Phase 195 stores mobile-uploaded audio
bytes VERBATIM and tracks the source format in
``voice_transcripts.audio_format`` (DB column from migration 042).
True 16 kHz mono PCM normalization is NOT shipped in Phase 195. This
is path (c) from Backend Commit 0.5's architect-side review: verbatim
+ format-tracking, NOT path (a) "verify-and-F-ticket" or path (b)
"reverse + ship pydub normalization."

**Why verbatim is the architecturally correct choice (not a workaround)**:

1. **Whisper accepts mobile output natively.** OpenAI Whisper API
   officially supports {mp3, mp4, mpeg, mpga, m4a, wav, webm}. iOS +
   Android (via ``react-native-audio-recorder-player`` defaults)
   produce M4A/AAC, which Whisper consumes directly. Phase 195B's
   cloud transcription does NOT need a transcoding step.
2. **Verbatim M4A is ~4× SMALLER than 16 kHz PCM.** A 90-second voice
   memo at 64 kbps M4A/AAC is ~720 KB; the same clip in normalized
   16 kHz mono 16-bit PCM is ~2.88 MB. Storing verbatim REDUCES
   storage cost vs the original plan-v1.0 projection, not increases
   it. Section 5's 60-day retention projection at 100-mechanic scale
   redoes to ~130 GB peak (was ~520 GB on PCM assumption) — bounded.
3. **Format heterogeneity tracked at the schema level.**
   ``voice_transcripts.audio_format`` (TEXT NOT NULL DEFAULT 'm4a',
   CHECK-equivalent enforcement at the Pydantic
   :class:`AudioFormat` Literal layer) means every consumer
   (mechanic-replay UI, 195B Whisper integration, Phase 96 acoustic-
   analysis cross-pollination) can dispatch on format. No silent
   assumptions baked in.
4. **The one consumer that genuinely needs PCM is speculative.** Phase
   96 acoustic-analysis cross-pollination (sound-signature analysis
   on the same recording) wants 16 kHz PCM input. That integration
   does not exist today. F39 NEW filed at Backend Commit 0.5: install
   ffmpeg + ship pydub transcoding when that integration's plan opens
   — NOT before.

**Phase 195's ``inspect_audio`` returns**:

- ``audio_format``: detected format (``'wav' | 'm4a' | 'ogg' | 'unknown'``).
  WAV / M4A / Ogg are recognized via magic-byte header detection;
  ``'unknown'`` raises :class:`UnsupportedAudioFormatError` (HTTP 415).
- ``size_bytes``: raw byte length.
- ``sha256``: content hash for dedup.
- ``duration_ms``: parsed from WAV header via stdlib :mod:`wave`;
  M4A / Ogg fall back to mobile-supplied ``duration_ms`` from the
  multipart metadata (``react-native-audio-recorder-player`` reports
  it authoritatively from its own framing).
- ``sample_rate_hz``: parsed from WAV header; 16000 default for M4A
  (matches what mobile is configured to capture at) / 48000 default
  for Ogg.

The route layer trusts mobile-supplied ``duration_ms`` when header
parsing returns ``None``, which is the M4A and Ogg case.
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
