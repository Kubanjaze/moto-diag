"""OpenAI Whisper cloud transcription — Phase 195B (Commit 0).

Wraps the OpenAI Whisper API (`whisper-1`) for the voice-symptom
feature half. Per Phase 195B plan v1.0 §1 + the Step 10 reframe:
cloud Whisper is **extraction-richness substrate**, not
canonicalization-priority — on-device STT held up under shop noise
(Step 10 PASS, worst-case 0.92), so Whisper's role is producing the
best-available canonical transcript for Claude-rich extraction to
work from, not rescuing bad on-device output.

Format: M4A is accepted natively by the Whisper API (verified at
Phase 195 Backend Commit 0.5) — no transcode step (F39 stays
deferred). WAV / Ogg also native.

Graceful degradation: when `MOTODIAG_OPENAI_API_KEY` is unset,
:func:`transcribe` raises :class:`WhisperUnavailableError` rather
than failing opaquely. The async extraction pipeline (Backend
Commit 1) catches it + falls back to the on-device `preview_text`
+ keyword extraction — the transcript still lands, just without the
Whisper-canonical text.

Cost: Whisper bills $0.006 / audio-minute. :func:`transcribe`
returns the computed `cost_usd_cents` so the caller records a
`cost_events` ledger row (Phase 195B §4 cost monitoring).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from motodiag.core.config import get_settings


_log = logging.getLogger(__name__)

# Whisper API pricing: USD 0.006 per audio-minute (2026-05 rate).
# Stored as a module constant so the cost math has a single source
# of truth; if OpenAI changes pricing, this is the one-line fix.
WHISPER_USD_CENTS_PER_MINUTE = 0.6


class WhisperUnavailableError(RuntimeError):
    """Raised when transcription is attempted without an API key.

    The async pipeline catches this + degrades to on-device
    preview_text + keyword extraction. Distinct from
    :class:`WhisperTranscriptionError` (the API was reachable but
    the call failed) so the caller can tell "not configured" from
    "configured but errored".
    """


class WhisperTranscriptionError(RuntimeError):
    """Raised when a Whisper API call fails (network, 4xx/5xx, or
    a malformed response). The async pipeline catches this + degrades
    the same way as :class:`WhisperUnavailableError`."""


@dataclass(frozen=True)
class WhisperSegment:
    """One time-coded segment of a Whisper transcript."""

    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class WhisperResult:
    """Result of a Whisper transcription.

    ``cost_usd_cents`` is the computed charge for the call — the
    caller records it as a ``cost_events`` ledger row + writes it to
    ``voice_transcripts.whisper_cost_usd_cents``.
    """

    text: str
    segments: list[WhisperSegment] = field(default_factory=list)
    model: str = "whisper-1"
    duration_ms: int = 0
    cost_usd_cents: int = 0


def whisper_available() -> bool:
    """Whether cloud transcription is configured at this boot."""
    return bool(get_settings().openai_api_key)


def estimate_cost_usd_cents(duration_ms: int) -> int:
    """Compute the Whisper charge for an audio clip of ``duration_ms``.

    Bills per audio-minute at :data:`WHISPER_USD_CENTS_PER_MINUTE`.
    Rounds UP to the next whole cent — under-billing the ledger would
    make the cost monitoring optimistic, which is the wrong direction
    for a budget guardrail.
    """
    minutes = duration_ms / 60_000.0
    return math.ceil(minutes * WHISPER_USD_CENTS_PER_MINUTE)


def transcribe(
    audio_path: str,
    *,
    duration_ms: int = 0,
    language: Optional[str] = None,
) -> WhisperResult:
    """Transcribe an audio file via the OpenAI Whisper API.

    ``audio_path`` is a filesystem path to the stored audio (M4A /
    WAV / Ogg — all Whisper-native). ``duration_ms`` is the
    mobile-reported clip duration, used for the cost estimate (the
    API response also carries a duration; we prefer the caller's
    value when given since it's the billable figure the mobile
    recorder authoritatively reports).

    Raises :class:`WhisperUnavailableError` when no API key is
    configured, :class:`WhisperTranscriptionError` on any API
    failure.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        raise WhisperUnavailableError(
            "OpenAI API key not configured (MOTODIAG_OPENAI_API_KEY); "
            "cloud transcription unavailable"
        )

    path = Path(audio_path)
    if not path.exists():
        raise WhisperTranscriptionError(
            f"audio file not found: {audio_path}"
        )

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover — install gate
        raise WhisperUnavailableError(
            "openai SDK not installed; install with: pip install "
            "'motodiag[ai]'"
        ) from exc

    client = OpenAI(api_key=settings.openai_api_key)
    model = settings.whisper_model

    try:
        with path.open("rb") as fh:
            resp = client.audio.transcriptions.create(
                model=model,
                file=fh,
                response_format="verbose_json",
                language=(language or "en")[:2],
            )
    except Exception as exc:  # noqa: BLE001 — surface as typed error
        raise WhisperTranscriptionError(
            f"Whisper API call failed: {exc!s}"
        ) from exc

    text = getattr(resp, "text", "") or ""
    # verbose_json carries `segments` (each with start/end in seconds)
    # + a top-level `duration` in seconds. Parse defensively — the
    # SDK response shape is dict-like or attr-like depending on
    # version.
    raw_segments = getattr(resp, "segments", None) or []
    segments: list[WhisperSegment] = []
    for seg in raw_segments:
        start_s = _seg_field(seg, "start", 0.0)
        end_s = _seg_field(seg, "end", 0.0)
        seg_text = str(_seg_field(seg, "text", "") or "").strip()
        segments.append(
            WhisperSegment(
                start_ms=int(round(start_s * 1000)),
                end_ms=int(round(end_s * 1000)),
                text=seg_text,
            )
        )

    api_duration_s = getattr(resp, "duration", 0.0) or 0.0
    effective_duration_ms = (
        duration_ms
        if duration_ms > 0
        else int(round(float(api_duration_s) * 1000))
    )
    cost = estimate_cost_usd_cents(effective_duration_ms)

    _log.info(
        "whisper transcribe ok: model=%s duration_ms=%d "
        "segments=%d cost_usd_cents=%d",
        model, effective_duration_ms, len(segments), cost,
    )
    return WhisperResult(
        text=text,
        segments=segments,
        model=model,
        duration_ms=effective_duration_ms,
        cost_usd_cents=cost,
    )


def _seg_field(seg: object, name: str, default: object) -> object:
    """Read a field from a Whisper segment that may be a dict or an
    attr-bearing object (SDK version variance)."""
    if isinstance(seg, dict):
        return seg.get(name, default)
    return getattr(seg, name, default)
