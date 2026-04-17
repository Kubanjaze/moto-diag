"""AI audio coaching for optimal engine audio capture.

Phase 107: Guides mechanics through standardized audio capture protocols
to ensure recordings are usable for diagnostic analysis. Provides step-by-step
instructions, evaluates capture quality, and selects the appropriate protocol
based on the reported symptom or engine type.

Designed for the mobile app workflow: mechanic opens a diagnostic session,
the app walks them through the protocol, and evaluates each recording before
proceeding. Works entirely offline — no API calls needed for coaching.
"""

import math
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.media.audio_capture import AudioSample


class CaptureQuality(str, Enum):
    """Quality assessment of a captured audio sample."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    UNUSABLE = "unusable"


class EngineType(str, Enum):
    """Engine configurations for protocol selection."""
    SINGLE_CYLINDER = "single_cylinder"
    V_TWIN = "v_twin"
    PARALLEL_TWIN = "parallel_twin"
    INLINE_FOUR = "inline_four"
    V_FOUR = "v_four"
    FLAT_TWIN = "flat_twin"
    UNKNOWN = "unknown"


class CoachingStep(BaseModel):
    """A single step in an audio capture protocol."""
    step_number: int = Field(description="Sequential step number (1-based).")
    instruction: str = Field(description="What the mechanic should do.")
    expected_condition: str = Field(
        description="What the engine/bike should be doing at this step.",
    )
    duration_seconds: int = Field(
        description="How long to hold this step (seconds).",
    )
    rpm_target: Optional[int] = Field(
        default=None,
        description="Target RPM for this step, if applicable.",
    )
    mic_position: str = Field(
        default="near exhaust",
        description="Where the phone/mic should be positioned.",
    )
    notes: str = Field(
        default="",
        description="Additional tips or warnings for this step.",
    )


class CaptureProtocol(BaseModel):
    """A complete audio capture protocol with ordered steps."""
    name: str = Field(description="Protocol identifier (e.g., 'idle_baseline').")
    description: str = Field(description="What this protocol captures and why.")
    steps: list[CoachingStep] = Field(
        default_factory=list,
        description="Ordered steps to follow.",
    )
    total_duration: int = Field(
        default=0,
        description="Total expected duration in seconds.",
    )
    engine_types_applicable: list[EngineType] = Field(
        default_factory=lambda: [e for e in EngineType if e != EngineType.UNKNOWN],
        description="Engine types this protocol works for.",
    )
    symptoms_applicable: list[str] = Field(
        default_factory=list,
        description="Symptoms this protocol is designed to investigate.",
    )
    min_quality_required: CaptureQuality = Field(
        default=CaptureQuality.ACCEPTABLE,
        description="Minimum quality for a usable capture.",
    )

    model_config = {"arbitrary_types_allowed": True}

    @property
    def step_count(self) -> int:
        return len(self.steps)


class QualityAssessment(BaseModel):
    """Result of evaluating an audio capture's quality."""
    quality: CaptureQuality = Field(description="Overall quality rating.")
    score: float = Field(description="Numeric quality score (0.0-1.0).")
    issues: list[str] = Field(
        default_factory=list,
        description="List of quality issues found.",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions to improve capture quality.",
    )
    meets_minimum: bool = Field(
        default=True,
        description="Whether the capture meets minimum quality for analysis.",
    )
    metrics: dict = Field(
        default_factory=dict,
        description="Detailed quality metrics.",
    )


# --- Predefined capture protocols ---

CAPTURE_PROTOCOLS: dict[str, CaptureProtocol] = {
    "idle_baseline": CaptureProtocol(
        name="idle_baseline",
        description=(
            "Capture engine idle sound as a baseline. Start cold, let the engine "
            "warm up, then record steady idle for 30 seconds. This establishes the "
            "normal sound signature for the engine."
        ),
        steps=[
            CoachingStep(
                step_number=1,
                instruction="Start the engine cold. Do not touch the throttle.",
                expected_condition="Engine cranking then catching — cold idle (may be high idle if choke/enrichener is on).",
                duration_seconds=10,
                rpm_target=1500,
                mic_position="12 inches from exhaust pipe opening",
                notes="Cold start sound is important — captures enrichener and cold clearances.",
            ),
            CoachingStep(
                step_number=2,
                instruction="Let the engine stabilize. Keep recording without touching anything.",
                expected_condition="Engine settling to stable idle. RPM should drop as engine warms.",
                duration_seconds=30,
                rpm_target=1000,
                mic_position="12 inches from exhaust pipe opening",
                notes="Listen for any ticking, knocking, or irregular rhythm.",
            ),
            CoachingStep(
                step_number=3,
                instruction="Note the final stable idle RPM. Stop recording.",
                expected_condition="Steady idle at operating temperature.",
                duration_seconds=10,
                rpm_target=900,
                mic_position="12 inches from exhaust pipe opening",
                notes="Record the RPM shown on tachometer for comparison with audio estimate.",
            ),
        ],
        total_duration=50,
        symptoms_applicable=["rough idle", "high idle", "stalling", "hunting idle", "ticking at idle"],
    ),

    "rev_sweep": CaptureProtocol(
        name="rev_sweep",
        description=(
            "Slowly sweep through the RPM range to capture the engine's sound at "
            "all speeds. Reveals issues that only appear at specific RPM bands — "
            "like exhaust resonance, valve float, or cam chain noise."
        ),
        steps=[
            CoachingStep(
                step_number=1,
                instruction="Start from stable idle. Begin recording.",
                expected_condition="Engine at stable warm idle.",
                duration_seconds=5,
                rpm_target=1000,
                mic_position="near exhaust",
                notes="Ensure engine is fully warmed up before starting.",
            ),
            CoachingStep(
                step_number=2,
                instruction="Slowly roll the throttle open over 15 seconds to reach 5000 RPM.",
                expected_condition="Smooth, gradual RPM increase. Listen for flat spots or surging.",
                duration_seconds=15,
                rpm_target=5000,
                mic_position="near exhaust",
                notes="Go SLOWLY. We need sound at every RPM, not just idle and redline.",
            ),
            CoachingStep(
                step_number=3,
                instruction="Hold at 5000 RPM for 5 seconds.",
                expected_condition="Steady RPM at 5000. Engine should sound smooth and consistent.",
                duration_seconds=5,
                rpm_target=5000,
                mic_position="near exhaust",
                notes="Any vibration or roughness here suggests upper-range issues.",
            ),
            CoachingStep(
                step_number=4,
                instruction="Slowly roll off the throttle back to idle over 10 seconds.",
                expected_condition="Smooth deceleration. Listen for popping, backfiring, or hanging RPM.",
                duration_seconds=10,
                rpm_target=1000,
                mic_position="near exhaust",
                notes="Decel popping suggests lean exhaust or exhaust leak.",
            ),
            CoachingStep(
                step_number=5,
                instruction="Hold at idle for 5 seconds, then stop recording.",
                expected_condition="Back to stable idle. Compare with initial idle sound.",
                duration_seconds=5,
                rpm_target=1000,
                mic_position="near exhaust",
                notes="If idle quality changed, that indicates a potential issue revealed by the sweep.",
            ),
        ],
        total_duration=40,
        symptoms_applicable=[
            "flat spot", "surging", "vibration at speed", "power loss",
            "decel popping", "exhaust noise", "valve noise",
        ],
    ),

    "load_test": CaptureProtocol(
        name="load_test",
        description=(
            "Quick throttle blips to test transient response and acceleration sound. "
            "Reveals carburetor/fuel injection issues, ignition problems, and "
            "mechanical noises that only appear under load changes."
        ),
        steps=[
            CoachingStep(
                step_number=1,
                instruction="Start from stable idle. Begin recording.",
                expected_condition="Engine at stable warm idle.",
                duration_seconds=5,
                rpm_target=1000,
                mic_position="near exhaust",
            ),
            CoachingStep(
                step_number=2,
                instruction="Quickly blip the throttle to 3000 RPM and release. Repeat 3 times with 3-second gaps.",
                expected_condition="Crisp acceleration, clean return to idle. No stumble or hesitation.",
                duration_seconds=15,
                rpm_target=3000,
                mic_position="near exhaust",
                notes="Hesitation on blip = possible accelerator pump or fuel delivery issue.",
            ),
            CoachingStep(
                step_number=3,
                instruction="Hold steady at 3000 RPM for 10 seconds.",
                expected_condition="Smooth, even exhaust note at 3000 RPM.",
                duration_seconds=10,
                rpm_target=3000,
                mic_position="near exhaust",
                notes="Listen for rhythmic misfire or uneven exhaust pulses.",
            ),
            CoachingStep(
                step_number=4,
                instruction="Release throttle to idle. Stop recording after 5 seconds.",
                expected_condition="Clean return to idle without hanging or stumble.",
                duration_seconds=5,
                rpm_target=1000,
                mic_position="near exhaust",
            ),
        ],
        total_duration=35,
        symptoms_applicable=[
            "hesitation", "stumble", "bog", "misfire", "poor throttle response",
            "knocking under load", "pinging",
        ],
    ),

    "cold_start": CaptureProtocol(
        name="cold_start",
        description=(
            "Capture the entire cold start sequence from first crank to stable idle. "
            "Cold starts reveal starter motor issues, compression problems, "
            "enrichener/choke behavior, and cold valve train noise."
        ),
        steps=[
            CoachingStep(
                step_number=1,
                instruction="Engine must be fully cold (sitting 4+ hours). Position phone and start recording BEFORE hitting the starter.",
                expected_condition="Silence, then cranking sound.",
                duration_seconds=5,
                mic_position="near cylinder head (for valve train) or near exhaust",
                notes="The cranking sound itself is diagnostic — slow cranking = weak battery or compression issues.",
            ),
            CoachingStep(
                step_number=2,
                instruction="Hit the starter. Let the engine crank and catch. Do NOT touch throttle.",
                expected_condition="Cranking (2-5 seconds), then engine catches and runs rough initially.",
                duration_seconds=10,
                rpm_target=1500,
                mic_position="near cylinder head or exhaust",
                notes="If it takes more than 5 seconds to start, note that — possible fuel or ignition issue.",
            ),
            CoachingStep(
                step_number=3,
                instruction="Let the engine warm up without touching anything. Keep recording.",
                expected_condition="RPM gradually dropping from cold-start high idle to normal idle.",
                duration_seconds=60,
                rpm_target=1000,
                mic_position="near exhaust",
                notes="Listen for valve ticking that fades as oil warms up vs ticking that persists.",
            ),
            CoachingStep(
                step_number=4,
                instruction="Once RPM is stable, record 10 more seconds of warm idle. Stop recording.",
                expected_condition="Stable warm idle. Compare with cold start sound.",
                duration_seconds=10,
                rpm_target=900,
                mic_position="near exhaust",
            ),
        ],
        total_duration=85,
        symptoms_applicable=[
            "hard starting", "slow crank", "cold start rattle", "valve tick",
            "cold stalling", "high idle", "smoke on startup",
        ],
    ),

    "decel_pop": CaptureProtocol(
        name="decel_pop",
        description=(
            "Rev to 5000 RPM and snap the throttle closed to capture deceleration "
            "popping and backfiring. Indicates lean exhaust conditions, exhaust leaks, "
            "or air injection system issues."
        ),
        steps=[
            CoachingStep(
                step_number=1,
                instruction="Start from stable warm idle. Begin recording.",
                expected_condition="Engine at stable warm idle.",
                duration_seconds=5,
                rpm_target=1000,
                mic_position="behind exhaust exit, 12 inches back",
                notes="Position mic behind the exhaust to capture pops clearly.",
            ),
            CoachingStep(
                step_number=2,
                instruction="Smoothly rev to 5000 RPM and hold for 3 seconds.",
                expected_condition="Engine at steady 5000 RPM.",
                duration_seconds=8,
                rpm_target=5000,
                mic_position="behind exhaust exit",
            ),
            CoachingStep(
                step_number=3,
                instruction="SNAP the throttle fully closed. Do not feather it — quick and complete.",
                expected_condition="Engine decelerating rapidly. Listen for popping, crackling, or backfire.",
                duration_seconds=5,
                mic_position="behind exhaust exit",
                notes="Occasional light popping is normal on many bikes. Heavy or persistent popping = lean exhaust.",
            ),
            CoachingStep(
                step_number=4,
                instruction="Repeat steps 2-3 two more times.",
                expected_condition="Same decel pattern. Consistency confirms the issue is real, not random.",
                duration_seconds=25,
                rpm_target=5000,
                mic_position="behind exhaust exit",
                notes="If pops are inconsistent, may be intermittent exhaust leak rather than fuel mixture.",
            ),
            CoachingStep(
                step_number=5,
                instruction="Return to idle. Stop recording.",
                expected_condition="Stable idle.",
                duration_seconds=5,
                rpm_target=1000,
                mic_position="behind exhaust exit",
            ),
        ],
        total_duration=48,
        symptoms_applicable=[
            "decel popping", "backfire", "exhaust pop", "afterfire",
            "crackling on decel", "lean exhaust",
        ],
    ),
}


# Mapping from symptoms to recommended protocols
SYMPTOM_PROTOCOL_MAP: dict[str, list[str]] = {
    "rough idle": ["idle_baseline", "cold_start"],
    "high idle": ["idle_baseline", "cold_start"],
    "stalling": ["idle_baseline", "load_test"],
    "hunting idle": ["idle_baseline"],
    "ticking": ["cold_start", "idle_baseline"],
    "knocking": ["load_test", "rev_sweep"],
    "misfire": ["load_test", "rev_sweep", "idle_baseline"],
    "hesitation": ["load_test", "rev_sweep"],
    "stumble": ["load_test"],
    "bog": ["load_test", "rev_sweep"],
    "decel popping": ["decel_pop"],
    "backfire": ["decel_pop", "rev_sweep"],
    "exhaust pop": ["decel_pop"],
    "power loss": ["rev_sweep", "load_test"],
    "vibration": ["rev_sweep"],
    "hard starting": ["cold_start"],
    "slow crank": ["cold_start"],
    "smoke": ["cold_start", "rev_sweep"],
    "valve noise": ["cold_start", "idle_baseline", "rev_sweep"],
    "flat spot": ["rev_sweep", "load_test"],
    "surging": ["rev_sweep", "idle_baseline"],
}


# Quality thresholds for capture evaluation
QUALITY_THRESHOLDS = {
    CaptureQuality.EXCELLENT: 0.85,
    CaptureQuality.GOOD: 0.70,
    CaptureQuality.ACCEPTABLE: 0.50,
    CaptureQuality.POOR: 0.30,
    # Below 0.30 = UNUSABLE
}


class AudioCoach:
    """Guides mechanics through optimal audio capture procedures.

    Manages protocol selection, step-by-step coaching, and capture quality
    evaluation. Designed for integration with the mobile app UI.

    Usage:
        coach = AudioCoach()
        protocol = coach.get_protocol("idle_baseline")
        coach.start_protocol(protocol)
        step = coach.get_current_step()
        # ... mechanic records audio ...
        assessment = coach.evaluate_capture(audio_sample, protocol)
        coach.advance_step()
    """

    def __init__(self):
        self._current_protocol: Optional[CaptureProtocol] = None
        self._current_step_index: int = 0
        self._is_active: bool = False
        self._step_captures: dict[int, QualityAssessment] = {}

    @property
    def is_active(self) -> bool:
        """Whether a coaching session is currently in progress."""
        return self._is_active

    @property
    def current_protocol(self) -> Optional[CaptureProtocol]:
        return self._current_protocol

    @property
    def progress(self) -> float:
        """Completion progress as a fraction (0.0 to 1.0)."""
        if not self._current_protocol or not self._current_protocol.steps:
            return 0.0
        return self._current_step_index / len(self._current_protocol.steps)

    def get_protocol(
        self,
        name: Optional[str] = None,
        symptom: Optional[str] = None,
        engine_type: Optional[str] = None,
    ) -> CaptureProtocol:
        """Select a capture protocol by name, symptom, or engine type.

        Args:
            name: Protocol name (e.g., 'idle_baseline').
            symptom: Reported symptom to match protocols against.
            engine_type: Engine type to filter applicable protocols.

        Returns:
            The matched CaptureProtocol.

        Raises:
            ValueError: If no matching protocol found.
        """
        if name is not None:
            if name in CAPTURE_PROTOCOLS:
                return CAPTURE_PROTOCOLS[name]
            raise ValueError(
                f"Unknown protocol '{name}'. Available: {list(CAPTURE_PROTOCOLS.keys())}"
            )

        if symptom is not None:
            symptom_lower = symptom.lower()
            # Direct match in symptom map
            if symptom_lower in SYMPTOM_PROTOCOL_MAP:
                proto_name = SYMPTOM_PROTOCOL_MAP[symptom_lower][0]
                return CAPTURE_PROTOCOLS[proto_name]
            # Fuzzy match: check if symptom appears in any protocol's applicable symptoms
            for proto in CAPTURE_PROTOCOLS.values():
                for applicable in proto.symptoms_applicable:
                    if symptom_lower in applicable.lower() or applicable.lower() in symptom_lower:
                        return proto
            # Default to idle_baseline
            return CAPTURE_PROTOCOLS["idle_baseline"]

        if engine_type is not None:
            try:
                et = EngineType(engine_type)
            except ValueError:
                et = EngineType.UNKNOWN

            for proto in CAPTURE_PROTOCOLS.values():
                if et in proto.engine_types_applicable:
                    return proto

        # Default
        return CAPTURE_PROTOCOLS["idle_baseline"]

    def get_protocols_for_symptom(self, symptom: str) -> list[CaptureProtocol]:
        """Get all protocols applicable to a symptom, ranked by relevance.

        Args:
            symptom: The reported symptom.

        Returns:
            List of applicable protocols, most relevant first.
        """
        symptom_lower = symptom.lower()
        if symptom_lower in SYMPTOM_PROTOCOL_MAP:
            return [CAPTURE_PROTOCOLS[n] for n in SYMPTOM_PROTOCOL_MAP[symptom_lower]]

        # Fuzzy match
        matched: list[CaptureProtocol] = []
        for proto in CAPTURE_PROTOCOLS.values():
            for applicable in proto.symptoms_applicable:
                if symptom_lower in applicable.lower() or applicable.lower() in symptom_lower:
                    if proto not in matched:
                        matched.append(proto)
        return matched or [CAPTURE_PROTOCOLS["idle_baseline"]]

    def list_protocols(self) -> list[dict]:
        """List all available protocols with basic info.

        Returns:
            List of dicts with protocol name, description, duration, and step count.
        """
        return [
            {
                "name": p.name,
                "description": p.description[:100] + "..." if len(p.description) > 100 else p.description,
                "total_duration": p.total_duration,
                "steps": p.step_count,
            }
            for p in CAPTURE_PROTOCOLS.values()
        ]

    def start_protocol(self, protocol: CaptureProtocol) -> CoachingStep:
        """Begin a coaching session with the given protocol.

        Args:
            protocol: The protocol to follow.

        Returns:
            The first coaching step.

        Raises:
            RuntimeError: If a session is already active.
            ValueError: If the protocol has no steps.
        """
        if self._is_active:
            raise RuntimeError("A coaching session is already active. Call finish_protocol() first.")
        if not protocol.steps:
            raise ValueError("Protocol has no steps.")

        self._current_protocol = protocol
        self._current_step_index = 0
        self._is_active = True
        self._step_captures = {}

        return protocol.steps[0]

    def get_current_step(self) -> Optional[CoachingStep]:
        """Return the current coaching instruction.

        Returns:
            The current CoachingStep, or None if no active session or all steps completed.
        """
        if not self._is_active or self._current_protocol is None:
            return None
        if self._current_step_index >= len(self._current_protocol.steps):
            return None
        return self._current_protocol.steps[self._current_step_index]

    def advance_step(self) -> Optional[CoachingStep]:
        """Move to the next step in the protocol.

        Returns:
            The next CoachingStep, or None if the protocol is complete.

        Raises:
            RuntimeError: If no active session.
        """
        if not self._is_active or self._current_protocol is None:
            raise RuntimeError("No active coaching session.")

        self._current_step_index += 1

        if self._current_step_index >= len(self._current_protocol.steps):
            return None

        return self._current_protocol.steps[self._current_step_index]

    def finish_protocol(self) -> dict:
        """End the coaching session and return a summary.

        Returns:
            Summary dict with steps completed, quality assessments, and overall rating.
        """
        if not self._is_active:
            raise RuntimeError("No active coaching session to finish.")

        protocol_name = self._current_protocol.name if self._current_protocol else "unknown"
        total_steps = self._current_protocol.step_count if self._current_protocol else 0
        steps_completed = min(self._current_step_index, total_steps)

        # Compute overall quality from step captures
        if self._step_captures:
            avg_score = sum(a.score for a in self._step_captures.values()) / len(self._step_captures)
            overall_quality = _score_to_quality(avg_score)
        else:
            avg_score = 0.0
            overall_quality = CaptureQuality.UNUSABLE

        summary = {
            "protocol": protocol_name,
            "steps_total": total_steps,
            "steps_completed": steps_completed,
            "steps_evaluated": len(self._step_captures),
            "overall_quality": overall_quality.value,
            "average_quality_score": round(avg_score, 4),
            "step_assessments": {
                step: {
                    "quality": assessment.quality.value,
                    "score": assessment.score,
                    "issues": assessment.issues,
                }
                for step, assessment in self._step_captures.items()
            },
        }

        self._is_active = False
        self._current_protocol = None
        self._current_step_index = 0
        self._step_captures = {}

        return summary

    def evaluate_capture(
        self,
        sample: AudioSample,
        protocol: Optional[CaptureProtocol] = None,
    ) -> QualityAssessment:
        """Evaluate whether an audio capture is sufficient for analysis.

        Checks:
        - Duration: is it long enough for the protocol step?
        - Signal level: is there actual audio content (not just silence)?
        - Clipping: is the audio distorted from being too loud?
        - Noise floor: is the signal-to-noise ratio acceptable?

        Args:
            sample: The AudioSample to evaluate.
            protocol: Optional protocol context for duration requirements.

        Returns:
            QualityAssessment with rating, score, issues, and suggestions.
        """
        issues: list[str] = []
        suggestions: list[str] = []
        score = 1.0
        metrics: dict = {}

        # --- Duration check ---
        min_duration = 1.0  # Default minimum
        if protocol and protocol.steps and self._current_step_index < len(protocol.steps):
            step = protocol.steps[self._current_step_index]
            min_duration = step.duration_seconds * 0.5  # Allow 50% of target

        metrics["duration_seconds"] = sample.duration_seconds
        metrics["min_duration_required"] = min_duration

        if sample.duration_seconds < min_duration:
            deficit = min_duration - sample.duration_seconds
            issues.append(f"Recording too short ({sample.duration_seconds:.1f}s, need {min_duration:.1f}s)")
            suggestions.append(f"Record at least {deficit:.1f} more seconds.")
            score -= 0.3

        # --- Signal level check ---
        peak = sample.get_peak_amplitude()
        rms = sample.get_rms_amplitude()
        metrics["peak_amplitude"] = round(peak, 4)
        metrics["rms_amplitude"] = round(rms, 4)

        if rms < 0.01:
            issues.append("No audio signal detected — recording appears silent.")
            suggestions.append("Ensure the engine is running and the microphone is not muted.")
            score -= 0.5
        elif rms < 0.05:
            issues.append(f"Very low signal level (RMS={rms:.4f}).")
            suggestions.append("Move the phone closer to the exhaust or engine.")
            score -= 0.2

        # --- Clipping check ---
        if sample.samples:
            clip_count = sum(1 for s in sample.samples if abs(s) >= 0.99)
            clip_ratio = clip_count / len(sample.samples)
            metrics["clip_ratio"] = round(clip_ratio, 6)

            if clip_ratio > 0.05:
                issues.append(f"Severe clipping ({clip_ratio:.1%} of samples). Audio is distorted.")
                suggestions.append("Move the phone further from the exhaust to reduce volume.")
                score -= 0.3
            elif clip_ratio > 0.01:
                issues.append(f"Mild clipping ({clip_ratio:.1%} of samples).")
                suggestions.append("Slightly increase distance from the exhaust.")
                score -= 0.1
        else:
            metrics["clip_ratio"] = 0.0

        # --- Signal-to-noise estimate ---
        # Compare loudest 10% vs quietest 10% of windows
        if sample.samples and len(sample.samples) >= 1000:
            window_size = len(sample.samples) // 20
            window_rms: list[float] = []
            for i in range(0, len(sample.samples) - window_size + 1, window_size):
                w = sample.samples[i:i + window_size]
                w_rms = math.sqrt(sum(s * s for s in w) / len(w))
                window_rms.append(w_rms)

            if window_rms:
                sorted_rms = sorted(window_rms)
                n = max(1, len(sorted_rms) // 10)
                noise_floor = sum(sorted_rms[:n]) / n if n > 0 else 0.0
                signal_peak = sum(sorted_rms[-n:]) / n if n > 0 else 0.0

                if noise_floor > 0:
                    snr = signal_peak / noise_floor
                else:
                    snr = 100.0  # Very clean

                metrics["estimated_snr"] = round(snr, 2)

                if snr < 2.0:
                    issues.append(f"Poor signal-to-noise ratio ({snr:.1f}x).")
                    suggestions.append(
                        "Reduce background noise — turn off compressors, close bay doors, "
                        "or move closer to the engine."
                    )
                    score -= 0.2
                elif snr < 4.0:
                    issues.append(f"Marginal signal-to-noise ratio ({snr:.1f}x).")
                    suggestions.append("Try to reduce background noise if possible.")
                    score -= 0.1

        # Clamp score
        score = max(0.0, min(1.0, score))
        quality = _score_to_quality(score)

        # Determine if it meets minimum
        min_quality = CaptureQuality.ACCEPTABLE
        if protocol:
            min_quality = protocol.min_quality_required
        quality_order = [
            CaptureQuality.EXCELLENT,
            CaptureQuality.GOOD,
            CaptureQuality.ACCEPTABLE,
            CaptureQuality.POOR,
            CaptureQuality.UNUSABLE,
        ]
        meets_minimum = quality_order.index(quality) <= quality_order.index(min_quality)

        assessment = QualityAssessment(
            quality=quality,
            score=round(score, 4),
            issues=issues,
            suggestions=suggestions,
            meets_minimum=meets_minimum,
            metrics=metrics,
        )

        # Store for the current step if in an active session
        if self._is_active:
            self._step_captures[self._current_step_index] = assessment

        return assessment


def _score_to_quality(score: float) -> CaptureQuality:
    """Convert a numeric score to a CaptureQuality enum."""
    if score >= QUALITY_THRESHOLDS[CaptureQuality.EXCELLENT]:
        return CaptureQuality.EXCELLENT
    elif score >= QUALITY_THRESHOLDS[CaptureQuality.GOOD]:
        return CaptureQuality.GOOD
    elif score >= QUALITY_THRESHOLDS[CaptureQuality.ACCEPTABLE]:
        return CaptureQuality.ACCEPTABLE
    elif score >= QUALITY_THRESHOLDS[CaptureQuality.POOR]:
        return CaptureQuality.POOR
    else:
        return CaptureQuality.UNUSABLE
