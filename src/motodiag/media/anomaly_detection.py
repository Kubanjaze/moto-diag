"""Audio anomaly detection for motorcycle engine diagnostics.

Phase 99: Identifies specific mechanical problems from engine sound by
comparing spectral characteristics against known anomaly signatures.

Each anomaly type has a spectral fingerprint — knock produces sharp broadband
spikes periodic with engine rotation, valve tick is a consistent high-frequency
click at valve-train frequencies, exhaust leaks create broadband noise that
scales with RPM. The detector checks a SpectrogramResult against all known
anomaly patterns and returns ranked findings with confidence, severity,
likely causes, and repair guidance.

Designed to work with synthetic test audio — no real engine recordings or
audio hardware required for testing.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.media.spectrogram import SpectrogramResult


class AnomalyType(str, Enum):
    """Categories of mechanical anomalies detectable by audio analysis.

    Each type has a distinct spectral signature that differentiates it
    from normal engine operation and from other anomaly types.
    """
    KNOCK = "knock"
    MISFIRE = "misfire"
    VALVE_TICK = "valve_tick"
    EXHAUST_LEAK = "exhaust_leak"
    BEARING_WHINE = "bearing_whine"
    CAM_CHAIN_RATTLE = "cam_chain_rattle"
    STARTER_GRIND = "starter_grind"
    CLUTCH_RATTLE = "clutch_rattle"
    DETONATION = "detonation"
    NORMAL = "normal"


class Severity(str, Enum):
    """Severity levels for detected anomalies.

    Maps to shop urgency: CRITICAL means stop riding immediately,
    HIGH means schedule service soon, MODERATE means monitor,
    LOW means note at next service, NONE means healthy.
    """
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    NONE = "none"


class AnomalySignature(BaseModel):
    """Spectral pattern definition for a specific anomaly type.

    Defines the frequency range, energy threshold, and characteristics
    that distinguish this anomaly from normal operation.
    """
    anomaly_type: AnomalyType = Field(description="The mechanical problem this signature identifies")
    freq_low: float = Field(description="Lower bound of primary frequency range in Hz")
    freq_high: float = Field(description="Upper bound of primary frequency range in Hz")
    energy_threshold: float = Field(
        description="Minimum fraction of total energy in this band to trigger detection (0-1)"
    )
    severity: Severity = Field(description="Default severity when detected")
    description: str = Field(default="", description="What this anomaly sounds like")
    likely_causes: list[str] = Field(default_factory=list, description="Mechanical causes of this sound")
    secondary_bands: list[str] = Field(
        default_factory=list,
        description="Other frequency band names that may show elevated energy with this anomaly",
    )


class AudioAnomaly(BaseModel):
    """A detected anomaly from audio analysis."""
    anomaly_type: AnomalyType = Field(description="Type of mechanical problem detected")
    confidence: float = Field(description="Detection confidence 0.0 to 1.0")
    frequency_range: tuple[float, float] = Field(description="Frequency range where anomaly was detected (Hz)")
    description: str = Field(default="", description="Human-readable description of the finding")
    likely_causes: list[str] = Field(default_factory=list, description="Possible mechanical causes")
    severity: Severity = Field(default=Severity.NONE, description="Urgency of the finding")
    energy_fraction: float = Field(default=0.0, description="Fraction of total spectral energy in anomaly band")
    recommendation: str = Field(default="", description="What the mechanic should do next")


# --- Anomaly signature definitions ---
# Each signature defines the spectral fingerprint of a specific mechanical problem.
# The energy_threshold is calibrated so that normal engine sounds don't trigger
# false positives — only genuinely elevated energy in the anomaly band triggers detection.

ANOMALY_SIGNATURES: list[AnomalySignature] = [
    AnomalySignature(
        anomaly_type=AnomalyType.KNOCK,
        freq_low=1000.0,
        freq_high=4000.0,
        energy_threshold=0.15,
        severity=Severity.CRITICAL,
        description="Sharp metallic impact periodic with engine rotation. Rod knock is a "
                    "deep thud at 1-2 kHz; piston slap is a lighter tap at 2-4 kHz. Both "
                    "are loudest when cold and under load.",
        likely_causes=[
            "Rod bearing wear — excessive clearance allows connecting rod to impact crankshaft journal",
            "Piston slap — worn piston or cylinder wall allows piston to rock at BDC/TDC",
            "Wrist pin wear — loose fit between piston pin and connecting rod small end",
            "Main bearing wear — crankshaft main journals have excessive play",
        ],
        secondary_bands=["exhaust_note", "valve_train"],
    ),
    AnomalySignature(
        anomaly_type=AnomalyType.MISFIRE,
        freq_low=50.0,
        freq_high=250.0,
        energy_threshold=0.10,
        severity=Severity.HIGH,
        description="Missing or irregular exhaust pulse at the expected firing frequency. "
                    "The spectral energy at the fundamental drops while broadband noise increases. "
                    "Sounds like a stumble, pop, or hesitation in the exhaust note.",
        likely_causes=[
            "Fouled or worn spark plug — carbon deposits prevent reliable spark",
            "Weak ignition coil — intermittent spark delivery to one cylinder",
            "Vacuum leak — lean mixture causes inconsistent combustion",
            "Fuel injector partially clogged — insufficient fuel delivery to affected cylinder",
            "Low compression — worn rings or leaking valve prevents proper combustion",
        ],
        secondary_bands=["low_rumble", "exhaust_note"],
    ),
    AnomalySignature(
        anomaly_type=AnomalyType.VALVE_TICK,
        freq_low=500.0,
        freq_high=2000.0,
        energy_threshold=0.12,
        severity=Severity.MODERATE,
        description="Consistent metallic tick synchronized with camshaft rotation (half engine speed). "
                    "Loudest at idle, often diminishes at higher RPM as oil pressure increases. "
                    "Sounds like a sewing machine running inside the engine.",
        likely_causes=[
            "Excessive valve clearance — shim-under-bucket or screw-adjust has drifted out of spec",
            "Worn cam follower — rocker arm or bucket surface is pitted or galled",
            "Collapsed hydraulic lifter — internal check valve or plunger stuck (Harley, some Honda)",
            "Worn cam lobe — reduced lift causes sloppier valve motion with audible impact",
        ],
        secondary_bands=["knock"],
    ),
    AnomalySignature(
        anomaly_type=AnomalyType.EXHAUST_LEAK,
        freq_low=200.0,
        freq_high=4000.0,
        energy_threshold=0.20,
        severity=Severity.MODERATE,
        description="Broadband hissing or ticking that increases with RPM. Loudest near exhaust "
                    "port or gasket junction. Sounds like a sharp 'tss-tss-tss' timed with exhaust "
                    "pulses, often described as a 'header leak tick'.",
        likely_causes=[
            "Exhaust gasket failure — crush gasket between header and cylinder head has blown out",
            "Cracked exhaust header — thermal fatigue crack at weld or bend point",
            "Loose exhaust clamp — slip joint at collector or muffler inlet has loosened",
            "Warped exhaust flange — repeated heat cycles have distorted the mounting surface",
        ],
        secondary_bands=["exhaust_note", "valve_train"],
    ),
    AnomalySignature(
        anomaly_type=AnomalyType.BEARING_WHINE,
        freq_low=2000.0,
        freq_high=8000.0,
        energy_threshold=0.10,
        severity=Severity.HIGH,
        description="Continuous high-frequency tone that rises in pitch linearly with RPM. "
                    "Distinguishable from valve tick by its steady, non-impulsive character. "
                    "Sounds like a distant siren or singing noise.",
        likely_causes=[
            "Worn crankshaft main bearing — reduced oil film allows metal-to-metal contact",
            "Rod bearing wear — especially under load, the bearing surfaces whine before they knock",
            "Transmission bearing wear — input or output shaft bearing failing",
            "Cam bearing wear — camshaft journal running dry or with excessive clearance",
            "Wheel bearing (if speed-dependent rather than RPM-dependent) — rule out by testing in neutral",
        ],
        secondary_bands=["knock"],
    ),
    AnomalySignature(
        anomaly_type=AnomalyType.CAM_CHAIN_RATTLE,
        freq_low=800.0,
        freq_high=3000.0,
        energy_threshold=0.12,
        severity=Severity.MODERATE,
        description="Rattling or slapping sound loudest at idle and light throttle, often diminishing "
                    "under load. The cam chain (or timing chain) slaps against its guide when the "
                    "tensioner can no longer take up slack. Sounds like marbles in a tin can.",
        likely_causes=[
            "Cam chain tensioner failure — hydraulic plunger worn out or ratchet mechanism broken",
            "Stretched cam chain — high-mileage chain has elongated beyond tensioner range",
            "Worn cam chain guide — plastic guide rail has worn through, chain contacts engine case",
            "Incorrect cam chain tension — manual tensioner not properly adjusted",
        ],
        secondary_bands=["valve_train", "knock"],
    ),
    AnomalySignature(
        anomaly_type=AnomalyType.STARTER_GRIND,
        freq_low=500.0,
        freq_high=3000.0,
        energy_threshold=0.15,
        severity=Severity.MODERATE,
        description="Harsh grinding or clashing sound only during cranking. The starter motor gear "
                    "fails to fully engage the ring gear on the flywheel before spinning. "
                    "Sounds like metal gears clashing.",
        likely_causes=[
            "Worn starter clutch — one-way clutch (sprag clutch) slipping or not fully engaging",
            "Starter motor gear wear — bendix or reduction gear teeth worn or chipped",
            "Weak starter relay — insufficient voltage causes slow engagement before motor spins",
            "Ring gear damage — chipped or missing teeth on flywheel ring gear",
        ],
        secondary_bands=["knock", "bearing_whine"],
    ),
    AnomalySignature(
        anomaly_type=AnomalyType.CLUTCH_RATTLE,
        freq_low=300.0,
        freq_high=1500.0,
        energy_threshold=0.10,
        severity=Severity.LOW,
        description="Light rattling at idle that disappears when the clutch lever is pulled in. "
                    "Caused by backlash in the clutch basket, hub, or primary drive. "
                    "Common on high-mileage bikes and usually not harmful.",
        likely_causes=[
            "Clutch basket notching — friction plates have worn grooves in the basket fingers",
            "Primary drive gear backlash — excessive play between engine sprocket and clutch gear",
            "Clutch hub damper wear — rubber dampers in the clutch hub have deteriorated",
            "Loose clutch basket nut — rare but dangerous if the basket comes loose",
        ],
        secondary_bands=["low_rumble", "valve_train"],
    ),
    AnomalySignature(
        anomaly_type=AnomalyType.DETONATION,
        freq_low=2000.0,
        freq_high=6000.0,
        energy_threshold=0.12,
        severity=Severity.CRITICAL,
        description="Sharp, metallic pinging under load, especially during acceleration. "
                    "Caused by abnormal combustion — the air-fuel mixture ignites spontaneously "
                    "from compression heat before the spark plug fires. Sounds like shaking a "
                    "can of ball bearings. Destroys pistons and rings if sustained.",
        likely_causes=[
            "Low octane fuel — pump gas octane too low for the engine's compression ratio",
            "Excessive carbon buildup — deposits raise effective compression ratio",
            "Lean air-fuel mixture — insufficient fuel causes higher combustion temperatures",
            "Ignition timing too advanced — spark fires too early in the compression stroke",
            "Overheating — elevated coolant/oil temperature lowers the detonation threshold",
        ],
        secondary_bands=["knock", "bearing_whine"],
    ),
]

# Build lookup dict by anomaly type
_ANOMALY_LOOKUP: dict[AnomalyType, AnomalySignature] = {
    sig.anomaly_type: sig for sig in ANOMALY_SIGNATURES
}


class AudioAnomalyDetector:
    """Detects mechanical anomalies from engine audio spectrograms.

    Compares spectral energy distribution against known anomaly signatures.
    Each anomaly type has a characteristic frequency range and energy threshold.
    When energy in that range exceeds the threshold, the anomaly is flagged
    with a confidence proportional to how far above threshold the energy is.

    Typical usage:
        detector = AudioAnomalyDetector()
        anomalies = detector.detect(spectrogram_result)
        if not detector.is_normal(spectrogram_result):
            print(f"Issues found: {[a.anomaly_type for a in anomalies]}")
            print(f"Severity: {detector.get_severity(spectrogram_result)}")
    """

    def __init__(
        self,
        signatures: Optional[list[AnomalySignature]] = None,
        confidence_threshold: float = 0.3,
    ):
        """Initialize the detector.

        Args:
            signatures: Custom anomaly signatures. Defaults to ANOMALY_SIGNATURES.
            confidence_threshold: Minimum confidence to include in results (0-1).
                Lower values catch more marginal anomalies but increase false positives.
        """
        self.signatures = signatures if signatures is not None else ANOMALY_SIGNATURES
        self.confidence_threshold = confidence_threshold

    def detect(self, spectrogram: SpectrogramResult) -> list[AudioAnomaly]:
        """Analyze a spectrogram for mechanical anomalies.

        For each known anomaly signature, computes the fraction of total
        spectral energy that falls within the anomaly's frequency range.
        If this fraction exceeds the signature's threshold, the anomaly
        is reported with confidence proportional to the excess.

        Args:
            spectrogram: SpectrogramResult from SpectrogramAnalyzer.

        Returns:
            List of AudioAnomaly sorted by confidence (highest first).
            Empty list if no anomalies detected above confidence_threshold.
        """
        if not spectrogram.frequency_bins or not spectrogram.magnitude_bins:
            return []

        # Compute total spectral energy (sum of squared magnitudes)
        total_energy = sum(m * m for m in spectrogram.magnitude_bins)
        if total_energy == 0:
            return []

        anomalies: list[AudioAnomaly] = []

        for sig in self.signatures:
            # Compute energy in this anomaly's frequency range
            band_energy = 0.0
            for freq, mag in zip(spectrogram.frequency_bins, spectrogram.magnitude_bins):
                if sig.freq_low <= freq <= sig.freq_high:
                    band_energy += mag * mag

            energy_fraction = band_energy / total_energy

            # Check if energy exceeds threshold
            if energy_fraction >= sig.energy_threshold:
                # Confidence scales from threshold (0.3) to 2x threshold (1.0)
                # The further above threshold, the more confident the detection
                excess_ratio = energy_fraction / sig.energy_threshold
                confidence = min(1.0, 0.3 + 0.7 * (excess_ratio - 1.0))

                if confidence >= self.confidence_threshold:
                    recommendation = self._get_recommendation(sig.anomaly_type, sig.severity)

                    anomalies.append(AudioAnomaly(
                        anomaly_type=sig.anomaly_type,
                        confidence=round(confidence, 3),
                        frequency_range=(sig.freq_low, sig.freq_high),
                        description=sig.description,
                        likely_causes=sig.likely_causes,
                        severity=sig.severity,
                        energy_fraction=round(energy_fraction, 4),
                        recommendation=recommendation,
                    ))

        # Sort by confidence descending
        anomalies.sort(key=lambda a: a.confidence, reverse=True)
        return anomalies

    def is_normal(self, spectrogram: SpectrogramResult) -> bool:
        """Check if the audio sounds normal (no anomalies above threshold).

        Args:
            spectrogram: SpectrogramResult to evaluate.

        Returns:
            True if no anomalies detected, False if any mechanical issues found.
        """
        anomalies = self.detect(spectrogram)
        return len(anomalies) == 0

    def get_severity(self, spectrogram: SpectrogramResult) -> Severity:
        """Return the highest severity among all detected anomalies.

        Args:
            spectrogram: SpectrogramResult to evaluate.

        Returns:
            Highest Severity found, or Severity.NONE if engine sounds normal.
        """
        anomalies = self.detect(spectrogram)
        if not anomalies:
            return Severity.NONE

        # Severity ordering: CRITICAL > HIGH > MODERATE > LOW > NONE
        severity_order = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MODERATE: 2,
            Severity.LOW: 1,
            Severity.NONE: 0,
        }

        highest = max(anomalies, key=lambda a: severity_order.get(a.severity, 0))
        return highest.severity

    def _get_recommendation(self, anomaly_type: AnomalyType, severity: Severity) -> str:
        """Generate a shop-appropriate recommendation for a detected anomaly.

        Args:
            anomaly_type: The type of anomaly detected.
            severity: The severity of the detection.

        Returns:
            Recommendation string for the mechanic.
        """
        recommendations: dict[AnomalyType, str] = {
            AnomalyType.KNOCK: (
                "Stop riding immediately. Rod or main bearing knock causes catastrophic "
                "engine failure if ignored. Perform oil pressure test and inspect bearings. "
                "If confirmed, engine teardown is required."
            ),
            AnomalyType.MISFIRE: (
                "Check spark plugs, ignition coils, and fuel injectors. Perform compression "
                "test to rule out mechanical cause. Check for vacuum leaks with carb cleaner "
                "spray test. Address before sustained riding — unburnt fuel damages catalytic "
                "converter and washes cylinder walls."
            ),
            AnomalyType.VALVE_TICK: (
                "Check valve clearances against service manual spec. On hydraulic lifter "
                "engines, check oil level and condition first — dirty oil clogs lifters. "
                "Shim-under-bucket engines need shim replacement. Monitor — moderate tick "
                "is acceptable on some engines, but increasing tick indicates wear."
            ),
            AnomalyType.EXHAUST_LEAK: (
                "Inspect exhaust gaskets at head-to-header junction and all clamp points. "
                "Use a shop rag near suspected leak area — exhaust pulses will push it away. "
                "Replace crush gaskets and torque to spec. An exhaust leak affects AFR readings "
                "and can mislead O2 sensor-based fuel injection."
            ),
            AnomalyType.BEARING_WHINE: (
                "Drain oil and inspect for metallic particles. Perform oil pressure test at "
                "idle and 3000 RPM. If oil pressure is low, bearing replacement is required "
                "before catastrophic failure. A whine that changes with RPM (not road speed) "
                "is an engine bearing; speed-dependent is a wheel bearing."
            ),
            AnomalyType.CAM_CHAIN_RATTLE: (
                "Inspect cam chain tensioner — hydraulic tensioners can be tested by checking "
                "if the pushrod extends and holds when compressed. Manual tensioners need "
                "adjustment per service manual. On high-mileage engines, replace chain and "
                "guides as a set. A broken chain guide can drop debris into the oil system."
            ),
            AnomalyType.STARTER_GRIND: (
                "Check starter clutch (sprag clutch) operation. Inspect starter motor gear "
                "and ring gear teeth for damage. Test battery voltage under cranking load — "
                "low voltage causes slow engagement. On Harley primary-drive starters, check "
                "compensator sprocket condition."
            ),
            AnomalyType.CLUTCH_RATTLE: (
                "Pull the clutch lever — if rattle stops, it is clutch basket backlash. "
                "Inspect basket fingers for notching. Light rattle is normal on many bikes "
                "and not harmful. Replace basket only if friction plates are binding in the "
                "notches and causing hard shifting or clutch drag."
            ),
            AnomalyType.DETONATION: (
                "Stop riding under load immediately — sustained detonation melts pistons. "
                "Switch to higher octane fuel. Check ignition timing. Inspect for carbon "
                "buildup (use a borescope through spark plug hole). On fuel-injected bikes, "
                "check for ECU fault codes that may indicate sensor failure causing lean condition."
            ),
        }

        return recommendations.get(anomaly_type, "Inspect further — anomaly detected but no specific guidance available.")
