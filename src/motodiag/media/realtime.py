"""Real-time audio monitoring for live engine diagnostics.

Phase 104: Processes AudioSample chunks as they arrive, tracks engine RPM
estimates, detects anomalies, and generates alerts. Simulated monitoring —
does not capture from microphone hardware, but processes chunks fed to it
by the caller (CLI, API, or mobile app).

Designed for live diagnostic sessions where a mechanic holds a phone near
a running engine and watches for anomalies in real time.
"""

import math
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.media.audio_capture import AudioSample, AudioConfig, AudioPreprocessor


class DisplayMode(str, Enum):
    """How monitoring results are displayed to the mechanic."""
    COMPACT = "compact"       # Single-line status updates
    DETAILED = "detailed"     # Full analysis per chunk
    ALERTS_ONLY = "alerts_only"  # Only show when something is wrong


class EventType(str, Enum):
    """Types of events generated during monitoring."""
    ANALYSIS_RESULT = "analysis_result"
    ALERT = "alert"
    STATUS = "status"
    SESSION_START = "session_start"
    SESSION_STOP = "session_stop"


class AlertSeverity(str, Enum):
    """Severity levels for monitoring alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MonitorConfig(BaseModel):
    """Configuration for real-time audio monitoring."""
    analysis_interval_sec: float = Field(
        default=2.0,
        description="How often to run analysis on incoming audio (seconds).",
    )
    alert_threshold: float = Field(
        default=0.15,
        description="Anomaly score above this triggers an alert (0.0-1.0).",
    )
    display_mode: DisplayMode = Field(
        default=DisplayMode.DETAILED,
        description="How monitoring output is displayed.",
    )
    rpm_smoothing_window: int = Field(
        default=3,
        description="Number of recent RPM estimates to average for smoothing.",
    )
    audio_config: AudioConfig = Field(
        default_factory=AudioConfig,
        description="Audio preprocessing configuration.",
    )


class MonitorEvent(BaseModel):
    """A single event during a monitoring session."""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the event occurred.",
    )
    event_type: EventType = Field(description="Type of event.")
    severity: AlertSeverity = Field(
        default=AlertSeverity.INFO,
        description="Severity level of the event.",
    )
    data: dict = Field(
        default_factory=dict,
        description="Event-specific data payload.",
    )
    message: str = Field(
        default="",
        description="Human-readable event description.",
    )


class MonitorSession(BaseModel):
    """State of an active or completed monitoring session."""
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier.",
    )
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the session started.",
    )
    ended_at: Optional[datetime] = Field(
        default=None,
        description="When the session ended (None if still active).",
    )
    events: list[MonitorEvent] = Field(
        default_factory=list,
        description="All events generated during the session.",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the session is currently running.",
    )
    current_rpm_estimate: Optional[float] = Field(
        default=None,
        description="Latest smoothed RPM estimate.",
    )
    chunks_processed: int = Field(
        default=0,
        description="Number of audio chunks processed so far.",
    )
    total_audio_seconds: float = Field(
        default=0.0,
        description="Total audio duration processed.",
    )
    rpm_history: list[float] = Field(
        default_factory=list,
        description="Recent RPM estimates for smoothing.",
    )
    anomaly_count: int = Field(
        default=0,
        description="Number of anomalies detected.",
    )

    model_config = {"arbitrary_types_allowed": True}

    @property
    def duration_seconds(self) -> float:
        """Session wall-clock duration in seconds."""
        end = self.ended_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()

    @property
    def alert_events(self) -> list[MonitorEvent]:
        """Return only alert events."""
        return [e for e in self.events if e.event_type == EventType.ALERT]

    @property
    def analysis_events(self) -> list[MonitorEvent]:
        """Return only analysis result events."""
        return [e for e in self.events if e.event_type == EventType.ANALYSIS_RESULT]


def estimate_rpm_from_samples(samples: list[float], sample_rate: int) -> Optional[float]:
    """Estimate engine RPM from audio samples using zero-crossing rate.

    The dominant frequency of an engine's exhaust note corresponds to its
    firing frequency. For a single-cylinder 4-stroke, firing_freq = RPM / 120.
    For a twin, firing_freq = RPM / 60. We use a conservative single-cylinder
    assumption and let the caller adjust.

    Zero-crossing rate gives a rough fundamental frequency estimate:
    frequency ~= zero_crossings / (2 * duration)

    Args:
        samples: Audio sample values (-1.0 to 1.0).
        sample_rate: Sample rate in Hz.

    Returns:
        Estimated RPM, or None if insufficient data.
    """
    if len(samples) < sample_rate * 0.05:  # Need at least 50ms of audio
        return None

    # Count zero crossings
    crossings = 0
    for i in range(1, len(samples)):
        if (samples[i - 1] >= 0 and samples[i] < 0) or \
           (samples[i - 1] < 0 and samples[i] >= 0):
            crossings += 1

    duration = len(samples) / sample_rate
    if duration <= 0:
        return None

    # Fundamental frequency estimate from zero-crossing rate
    frequency = crossings / (2.0 * duration)

    # Convert to RPM assuming single-cylinder 4-stroke: RPM = freq * 120
    # Typical motorcycle idle: 800-1200 RPM = 6.7-10 Hz fundamental
    # Rev range: 800-14000 RPM = 6.7-116.7 Hz
    rpm = frequency * 120.0

    # Clamp to reasonable motorcycle RPM range
    if rpm < 200 or rpm > 18000:
        return None

    return round(rpm, 1)


def compute_anomaly_score(sample: AudioSample) -> float:
    """Compute a simple anomaly score for an audio chunk.

    Uses a combination of:
    - Amplitude irregularity (high variance in peak-to-peak within sub-windows)
    - Sudden transients (spikes that exceed 3x the RMS)

    Returns a score from 0.0 (normal) to 1.0 (highly anomalous).
    """
    if not sample.samples or len(sample.samples) < 100:
        return 0.0

    rms = sample.get_rms_amplitude()
    if rms == 0.0:
        return 0.0

    # Count transient spikes (samples exceeding 3x RMS)
    spike_threshold = 3.0 * rms
    spike_count = sum(1 for s in sample.samples if abs(s) > spike_threshold)
    spike_ratio = spike_count / len(sample.samples)

    # Compute amplitude variance across sub-windows
    window_size = len(sample.samples) // 10
    if window_size < 10:
        window_size = len(sample.samples)

    window_rms_values = []
    for i in range(0, len(sample.samples) - window_size + 1, window_size):
        window = sample.samples[i:i + window_size]
        w_rms = math.sqrt(sum(s * s for s in window) / len(window))
        window_rms_values.append(w_rms)

    if len(window_rms_values) > 1:
        mean_rms = sum(window_rms_values) / len(window_rms_values)
        variance = sum((r - mean_rms) ** 2 for r in window_rms_values) / len(window_rms_values)
        cv = math.sqrt(variance) / mean_rms if mean_rms > 0 else 0.0  # Coefficient of variation
    else:
        cv = 0.0

    # Combine: spike_ratio contributes 60%, amplitude variability 40%
    score = min(1.0, (spike_ratio * 10.0) * 0.6 + min(1.0, cv * 2.0) * 0.4)

    return round(score, 4)


class RealtimeMonitor:
    """Monitors engine audio in real time, processing chunks as they arrive.

    Usage:
        monitor = RealtimeMonitor(config)
        session = monitor.start_session()
        while recording:
            alerts = monitor.process_chunk(audio_chunk)
            if alerts:
                display_alerts(alerts)
        summary = monitor.stop_session()
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.preprocessor = AudioPreprocessor(self.config.audio_config)
        self._session: Optional[MonitorSession] = None

    @property
    def session(self) -> Optional[MonitorSession]:
        """Current monitoring session, or None if not started."""
        return self._session

    def start_session(self) -> MonitorSession:
        """Create and start a new monitoring session.

        Returns:
            The new MonitorSession.

        Raises:
            RuntimeError: If a session is already active.
        """
        if self._session is not None and self._session.is_active:
            raise RuntimeError("A monitoring session is already active. Stop it first.")

        self._session = MonitorSession()

        start_event = MonitorEvent(
            event_type=EventType.SESSION_START,
            severity=AlertSeverity.INFO,
            message="Monitoring session started.",
            data={"config": self.config.model_dump()},
        )
        self._session.events.append(start_event)

        return self._session

    def process_chunk(self, chunk: AudioSample) -> list[MonitorEvent]:
        """Process an incoming audio chunk and return any generated alerts.

        Steps:
        1. Preprocess the chunk (normalize, noise gate)
        2. Estimate RPM from the audio
        3. Compute anomaly score
        4. Generate events (always an analysis_result; alert if anomaly > threshold)

        Args:
            chunk: An AudioSample containing raw audio data.

        Returns:
            List of alert events (empty if nothing anomalous).

        Raises:
            RuntimeError: If no session is active.
        """
        if self._session is None or not self._session.is_active:
            raise RuntimeError("No active monitoring session. Call start_session() first.")

        # Preprocess: normalize and apply noise gate (skip segment — chunk is already sized)
        normalized = self.preprocessor.normalize_amplitude(chunk)
        gated = self.preprocessor.apply_noise_gate(normalized)

        # Estimate RPM
        rpm_estimate = estimate_rpm_from_samples(gated.samples, gated.sample_rate)
        if rpm_estimate is not None:
            self._session.rpm_history.append(rpm_estimate)
            # Keep only the smoothing window
            window = self.config.rpm_smoothing_window
            if len(self._session.rpm_history) > window:
                self._session.rpm_history = self._session.rpm_history[-window:]
            # Smoothed average
            self._session.current_rpm_estimate = round(
                sum(self._session.rpm_history) / len(self._session.rpm_history), 1
            )

        # Compute anomaly score
        anomaly_score = compute_anomaly_score(gated)

        # Update session stats
        self._session.chunks_processed += 1
        self._session.total_audio_seconds += chunk.duration_seconds

        # Generate analysis result event
        analysis_data = {
            "chunk_index": self._session.chunks_processed,
            "rpm_estimate": rpm_estimate,
            "rpm_smoothed": self._session.current_rpm_estimate,
            "anomaly_score": anomaly_score,
            "peak_amplitude": gated.get_peak_amplitude(),
            "rms_amplitude": gated.get_rms_amplitude(),
            "duration_seconds": chunk.duration_seconds,
        }

        analysis_event = MonitorEvent(
            event_type=EventType.ANALYSIS_RESULT,
            severity=AlertSeverity.INFO,
            message=f"Chunk {self._session.chunks_processed}: "
                    f"RPM={self._session.current_rpm_estimate or 'N/A'}, "
                    f"anomaly={anomaly_score:.4f}",
            data=analysis_data,
        )
        self._session.events.append(analysis_event)

        # Check for alerts
        alerts: list[MonitorEvent] = []

        if anomaly_score >= self.config.alert_threshold:
            self._session.anomaly_count += 1

            if anomaly_score >= 0.7:
                severity = AlertSeverity.CRITICAL
                msg = f"CRITICAL anomaly detected (score={anomaly_score:.3f}). Possible misfire or mechanical issue."
            elif anomaly_score >= 0.4:
                severity = AlertSeverity.WARNING
                msg = f"Warning: elevated anomaly score ({anomaly_score:.3f}). Monitor closely."
            else:
                severity = AlertSeverity.INFO
                msg = f"Mild anomaly detected (score={anomaly_score:.3f})."

            alert_event = MonitorEvent(
                event_type=EventType.ALERT,
                severity=severity,
                message=msg,
                data={
                    "anomaly_score": anomaly_score,
                    "rpm_estimate": self._session.current_rpm_estimate,
                    "chunk_index": self._session.chunks_processed,
                },
            )
            self._session.events.append(alert_event)
            alerts.append(alert_event)

        # RPM deviation alert (sudden change > 500 RPM between estimates)
        if len(self._session.rpm_history) >= 2:
            rpm_delta = abs(self._session.rpm_history[-1] - self._session.rpm_history[-2])
            if rpm_delta > 500:
                rpm_alert = MonitorEvent(
                    event_type=EventType.ALERT,
                    severity=AlertSeverity.WARNING,
                    message=f"Sudden RPM change: {rpm_delta:.0f} RPM delta detected.",
                    data={
                        "rpm_delta": rpm_delta,
                        "rpm_previous": self._session.rpm_history[-2],
                        "rpm_current": self._session.rpm_history[-1],
                    },
                )
                self._session.events.append(rpm_alert)
                alerts.append(rpm_alert)

        return alerts

    def get_status(self) -> dict:
        """Return current session status.

        Returns:
            Dict with session state: RPM, anomalies, duration, chunk count.

        Raises:
            RuntimeError: If no session exists.
        """
        if self._session is None:
            raise RuntimeError("No monitoring session exists. Call start_session() first.")

        return {
            "session_id": self._session.session_id,
            "is_active": self._session.is_active,
            "duration_seconds": round(self._session.duration_seconds, 2),
            "chunks_processed": self._session.chunks_processed,
            "total_audio_seconds": round(self._session.total_audio_seconds, 2),
            "current_rpm_estimate": self._session.current_rpm_estimate,
            "anomaly_count": self._session.anomaly_count,
            "active_alerts": [
                e.message for e in self._session.alert_events[-5:]
            ],
        }

    def stop_session(self) -> dict:
        """Stop the active monitoring session and return a summary.

        Returns:
            Summary dict with session stats and findings.

        Raises:
            RuntimeError: If no active session exists.
        """
        if self._session is None or not self._session.is_active:
            raise RuntimeError("No active session to stop.")

        self._session.is_active = False
        self._session.ended_at = datetime.now(timezone.utc)

        stop_event = MonitorEvent(
            event_type=EventType.SESSION_STOP,
            severity=AlertSeverity.INFO,
            message="Monitoring session stopped.",
            data={
                "total_chunks": self._session.chunks_processed,
                "total_anomalies": self._session.anomaly_count,
                "total_audio_seconds": self._session.total_audio_seconds,
            },
        )
        self._session.events.append(stop_event)

        # Build summary
        analysis_events = self._session.analysis_events
        anomaly_scores = [
            e.data.get("anomaly_score", 0.0) for e in analysis_events
        ]
        rpm_estimates = [
            e.data.get("rpm_estimate") for e in analysis_events
            if e.data.get("rpm_estimate") is not None
        ]

        summary = {
            "session_id": self._session.session_id,
            "duration_seconds": round(self._session.duration_seconds, 2),
            "chunks_processed": self._session.chunks_processed,
            "total_audio_seconds": round(self._session.total_audio_seconds, 2),
            "anomaly_count": self._session.anomaly_count,
            "avg_anomaly_score": round(
                sum(anomaly_scores) / len(anomaly_scores), 4
            ) if anomaly_scores else 0.0,
            "max_anomaly_score": round(max(anomaly_scores), 4) if anomaly_scores else 0.0,
            "rpm_range": {
                "min": round(min(rpm_estimates), 1) if rpm_estimates else None,
                "max": round(max(rpm_estimates), 1) if rpm_estimates else None,
                "final": self._session.current_rpm_estimate,
            },
            "alert_count": len(self._session.alert_events),
            "alerts": [
                {"severity": e.severity.value, "message": e.message}
                for e in self._session.alert_events
            ],
        }

        return summary
