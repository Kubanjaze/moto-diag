"""Engine sound signature database for motorcycle diagnostics.

Phase 98: Known-good baseline sound profiles for each engine configuration.
Maps engine type to expected firing frequency ranges, harmonic patterns,
and characteristic sounds. Enables comparing a recorded spectrogram against
the expected profile to identify the engine type and detect deviations.

Firing frequency calculation:
    firing_freq = (RPM / 60) * (cylinders / strokes_per_cycle)
    For 4-stroke: firing_freq = RPM * cylinders / 120

V-twins with uneven firing intervals produce a distinctive "potato-potato"
sound because the power pulses are not evenly spaced. Inline-4s produce
a smooth, even exhaust note. These spectral fingerprints let us identify
engine type from audio alone.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from motodiag.media.spectrogram import SpectrogramResult


class EngineType(str, Enum):
    """Motorcycle engine configurations encountered in the shop.

    Each type has a distinct sound signature due to cylinder count,
    arrangement, firing order, and crankshaft design.
    """
    SINGLE_CYLINDER = "single_cylinder"
    V_TWIN = "v_twin"
    PARALLEL_TWIN = "parallel_twin"
    INLINE_THREE = "inline_three"
    INLINE_FOUR = "inline_four"
    V_FOUR = "v_four"
    BOXER_TWIN = "boxer_twin"


class SoundSignature(BaseModel):
    """Expected spectral profile for a specific engine type.

    Describes what a healthy engine of this type should sound like
    at idle and at higher RPM. Used as the reference for comparison
    when diagnosing an unknown engine recording.
    """
    engine_type: EngineType = Field(description="Engine configuration")
    idle_rpm_range: tuple[int, int] = Field(description="Typical idle RPM range (low, high)")
    firing_freq_idle_low: float = Field(description="Firing frequency at low end of idle RPM range (Hz)")
    firing_freq_idle_high: float = Field(description="Firing frequency at high end of idle RPM range (Hz)")
    firing_freq_5000_low: float = Field(description="Firing frequency at 5000 RPM (Hz) — low estimate")
    firing_freq_5000_high: float = Field(description="Firing frequency at 5000 RPM (Hz) — high estimate")
    expected_harmonics: list[float] = Field(
        default_factory=list,
        description="Harmonic multipliers relative to fundamental. [1, 2, 3] = fundamental + 2nd + 3rd harmonic.",
    )
    characteristic_sounds: list[str] = Field(
        default_factory=list,
        description="Human-readable descriptions of the engine's sound character.",
    )
    cylinders: int = Field(description="Number of cylinders")
    strokes: int = Field(default=4, description="Stroke count (virtually all modern motorcycles are 4-stroke)")
    notes: str = Field(default="", description="Additional diagnostic notes about this engine type")


def rpm_to_firing_frequency(rpm: float, engine_type: EngineType) -> float:
    """Calculate the fundamental firing (combustion) frequency from RPM and engine type.

    For a 4-stroke engine: each cylinder fires once every 2 crankshaft revolutions.
        firing_freq = (RPM / 60) * (cylinders / 2)

    This is the fundamental frequency that appears as the dominant spectral peak
    in a healthy engine's audio. Harmonics appear at 2x, 3x, 4x, etc.

    Args:
        rpm: Engine speed in revolutions per minute.
        engine_type: The engine configuration (determines cylinder count).

    Returns:
        Firing frequency in Hz.

    Examples:
        Single cylinder at 1000 RPM: (1000/60) * (1/2) = 8.33 Hz
        V-twin at 1000 RPM: (1000/60) * (2/2) = 16.67 Hz
        Inline-4 at 6000 RPM: (6000/60) * (4/2) = 200 Hz
    """
    cylinder_count = _ENGINE_CYLINDERS[engine_type]
    # 4-stroke: each cylinder fires once per 2 revolutions
    return (rpm / 60.0) * (cylinder_count / 2.0)


# Cylinder count lookup for each engine type
_ENGINE_CYLINDERS: dict[EngineType, int] = {
    EngineType.SINGLE_CYLINDER: 1,
    EngineType.V_TWIN: 2,
    EngineType.PARALLEL_TWIN: 2,
    EngineType.INLINE_THREE: 3,
    EngineType.INLINE_FOUR: 4,
    EngineType.V_FOUR: 4,
    EngineType.BOXER_TWIN: 2,
}


# --- Known-good sound signatures for each engine type ---
# These are the spectral fingerprints of healthy engines. Deviations from
# these patterns indicate mechanical problems.

SIGNATURES: dict[EngineType, SoundSignature] = {
    EngineType.SINGLE_CYLINDER: SoundSignature(
        engine_type=EngineType.SINGLE_CYLINDER,
        idle_rpm_range=(1000, 1300),
        firing_freq_idle_low=rpm_to_firing_frequency(1000, EngineType.SINGLE_CYLINDER),   # 8.33 Hz
        firing_freq_idle_high=rpm_to_firing_frequency(1300, EngineType.SINGLE_CYLINDER),  # 10.83 Hz
        firing_freq_5000_low=rpm_to_firing_frequency(4800, EngineType.SINGLE_CYLINDER),   # 40.0 Hz
        firing_freq_5000_high=rpm_to_firing_frequency(5200, EngineType.SINGLE_CYLINDER),  # 43.33 Hz
        expected_harmonics=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        characteristic_sounds=[
            "strong single exhaust pulse — pronounced 'thump' per firing",
            "long gap between pulses at idle — audible silence between thumps",
            "heavy vibration at low RPM — big single thumper shake",
            "exhaust note deepens significantly with large bore singles (>500cc)",
            "prominent first and second harmonics, weak higher harmonics",
        ],
        cylinders=1,
        notes="Singles produce the most vibration per power stroke. Common in dirt bikes, "
              "dual sports (DR650, KLR650), and some standards (SR400). The long inter-pulse "
              "gap makes misfires very obvious by ear.",
    ),
    EngineType.V_TWIN: SoundSignature(
        engine_type=EngineType.V_TWIN,
        idle_rpm_range=(800, 1100),
        firing_freq_idle_low=rpm_to_firing_frequency(800, EngineType.V_TWIN),     # 13.33 Hz
        firing_freq_idle_high=rpm_to_firing_frequency(1100, EngineType.V_TWIN),   # 18.33 Hz
        firing_freq_5000_low=rpm_to_firing_frequency(4800, EngineType.V_TWIN),    # 80.0 Hz
        firing_freq_5000_high=rpm_to_firing_frequency(5200, EngineType.V_TWIN),   # 86.67 Hz
        expected_harmonics=[1.0, 1.5, 2.0, 3.0, 4.0],
        characteristic_sounds=[
            "uneven exhaust pulse — 'potato-potato' cadence from unequal firing intervals",
            "45-degree V-twins (Harley) fire at 315/405 degree intervals, creating the signature lope",
            "90-degree V-twins (Ducati, SV650) fire more evenly but still have audible unevenness",
            "strong low-frequency rumble — the bass note that carries through walls",
            "sub-harmonics from uneven firing create spectral energy below fundamental",
        ],
        cylinders=2,
        notes="The V-twin's unequal firing interval is its defining spectral feature. Harley "
              "45-degree twins have the most pronounced unevenness. Misfires disrupt the "
              "characteristic rhythm and are easily detected. Cam chain tensioner wear "
              "adds a rattle in the 800-1500 Hz range.",
    ),
    EngineType.PARALLEL_TWIN: SoundSignature(
        engine_type=EngineType.PARALLEL_TWIN,
        idle_rpm_range=(900, 1200),
        firing_freq_idle_low=rpm_to_firing_frequency(900, EngineType.PARALLEL_TWIN),    # 15.0 Hz
        firing_freq_idle_high=rpm_to_firing_frequency(1200, EngineType.PARALLEL_TWIN),  # 20.0 Hz
        firing_freq_5000_low=rpm_to_firing_frequency(4800, EngineType.PARALLEL_TWIN),   # 80.0 Hz
        firing_freq_5000_high=rpm_to_firing_frequency(5200, EngineType.PARALLEL_TWIN),  # 86.67 Hz
        expected_harmonics=[1.0, 2.0, 3.0, 4.0],
        characteristic_sounds=[
            "360-degree crank: even firing pulses, smooth buzz similar to inline-4 but lower",
            "270-degree crank: uneven pulses resembling a V-twin character (modern Yamaha MT-07, Kawasaki Z650)",
            "180-degree crank: alternating pulses, classic British twin sound",
            "less bass than V-twin, more midrange — 'buzzy' character at high RPM",
            "mechanical noise concentrated in valve train band (500-2000 Hz)",
        ],
        cylinders=2,
        notes="The crank angle determines the sound character. 270-degree cranks (MT-07, "
              "Rebel 500) are designed to sound like V-twins. 360-degree cranks (older Honda "
              "CB twins) are smoother. Balancer shaft noise may appear at 2x RPM.",
    ),
    EngineType.INLINE_THREE: SoundSignature(
        engine_type=EngineType.INLINE_THREE,
        idle_rpm_range=(900, 1200),
        firing_freq_idle_low=rpm_to_firing_frequency(900, EngineType.INLINE_THREE),    # 22.5 Hz
        firing_freq_idle_high=rpm_to_firing_frequency(1200, EngineType.INLINE_THREE),  # 30.0 Hz
        firing_freq_5000_low=rpm_to_firing_frequency(4800, EngineType.INLINE_THREE),   # 120.0 Hz
        firing_freq_5000_high=rpm_to_firing_frequency(5200, EngineType.INLINE_THREE),  # 130.0 Hz
        expected_harmonics=[1.0, 2.0, 3.0, 4.0, 5.0],
        characteristic_sounds=[
            "evenly spaced 240-degree firing intervals — smooth but with audible burble",
            "distinctive 'growl' that sits between V-twin rumble and inline-4 scream",
            "strong third harmonic from the 3-cylinder firing pattern",
            "rich midrange — less bass than twin, less top-end than four",
            "Triumph triple signature: musical exhaust note described as 'melodic growl'",
        ],
        cylinders=3,
        notes="The 120-degree firing intervals (Triumph triples) produce a unique sound. "
              "The third harmonic (3x fundamental) is characteristically strong. Valve "
              "clearances on 3-cylinder engines are critical — uneven tick patterns are "
              "more audible than on 4-cylinder engines.",
    ),
    EngineType.INLINE_FOUR: SoundSignature(
        engine_type=EngineType.INLINE_FOUR,
        idle_rpm_range=(1000, 1400),
        firing_freq_idle_low=rpm_to_firing_frequency(1000, EngineType.INLINE_FOUR),    # 33.33 Hz
        firing_freq_idle_high=rpm_to_firing_frequency(1400, EngineType.INLINE_FOUR),   # 46.67 Hz
        firing_freq_5000_low=rpm_to_firing_frequency(4800, EngineType.INLINE_FOUR),    # 160.0 Hz
        firing_freq_5000_high=rpm_to_firing_frequency(5200, EngineType.INLINE_FOUR),   # 173.33 Hz
        expected_harmonics=[1.0, 2.0, 4.0, 6.0, 8.0],
        characteristic_sounds=[
            "smooth even exhaust pulse — four evenly-spaced firings per 720 degrees",
            "signature inline-4 'scream' above 8000 RPM — high-frequency harmonic content increases",
            "cam chain whine prominent in the 2-4 kHz range on high-RPM fours",
            "mechanical noise spreads across frequency bands — harder to isolate single faults",
            "even-order harmonics (2nd, 4th) dominate — odd harmonics suppressed by symmetric firing",
        ],
        cylinders=4,
        notes="Japanese inline-fours (CBR, ZX, GSX-R, R1/R6) are the most common sportbike "
              "configuration. The even firing pattern makes individual misfires harder to "
              "detect by ear than on twins. Cam chain noise is the most common mechanical "
              "concern — produces a high-frequency rattle that increases with mileage.",
    ),
    EngineType.V_FOUR: SoundSignature(
        engine_type=EngineType.V_FOUR,
        idle_rpm_range=(1000, 1300),
        firing_freq_idle_low=rpm_to_firing_frequency(1000, EngineType.V_FOUR),    # 33.33 Hz
        firing_freq_idle_high=rpm_to_firing_frequency(1300, EngineType.V_FOUR),   # 43.33 Hz
        firing_freq_5000_low=rpm_to_firing_frequency(4800, EngineType.V_FOUR),    # 160.0 Hz
        firing_freq_5000_high=rpm_to_firing_frequency(5200, EngineType.V_FOUR),   # 173.33 Hz
        expected_harmonics=[1.0, 1.5, 2.0, 3.0, 4.0, 6.0],
        characteristic_sounds=[
            "uneven firing intervals create a 'gear-driven' mechanical sound unlike inline-4",
            "deeper exhaust note than inline-4 with more bass content",
            "Honda VFR 'gear whine' from cam gear drive is normal — not a fault",
            "Aprilia/Ducati V4 has more pronounced unevenness than Honda V4",
            "sub-harmonics present from unequal firing order",
        ],
        cylinders=4,
        notes="V-fours combine twin-like character with four-cylinder power. Honda VFR's "
              "gear-driven cams produce a distinctive whine that customers mistake for a "
              "fault — it's normal. The V4R (Aprilia RSV4, Ducati Panigale V4) fires with "
              "a 'big bang' order that sounds dramatically different from a traditional V4.",
    ),
    EngineType.BOXER_TWIN: SoundSignature(
        engine_type=EngineType.BOXER_TWIN,
        idle_rpm_range=(900, 1100),
        firing_freq_idle_low=rpm_to_firing_frequency(900, EngineType.BOXER_TWIN),    # 15.0 Hz
        firing_freq_idle_high=rpm_to_firing_frequency(1100, EngineType.BOXER_TWIN),  # 18.33 Hz
        firing_freq_5000_low=rpm_to_firing_frequency(4800, EngineType.BOXER_TWIN),   # 80.0 Hz
        firing_freq_5000_high=rpm_to_firing_frequency(5200, EngineType.BOXER_TWIN),  # 86.67 Hz
        expected_harmonics=[1.0, 2.0, 3.0, 4.0],
        characteristic_sounds=[
            "180-degree opposed firing — even pulses like a parallel twin 360-degree crank",
            "distinctive lateral rocking due to horizontally opposed cylinders",
            "low exhaust note with less 'rumble' than V-twin — smoother character",
            "valve train noise prominent — BMW boxer valve adjustments are a common service item",
            "air-cooled boxers (pre-2013 BMW) have more mechanical noise than liquid-cooled",
        ],
        cylinders=2,
        notes="BMW boxer twins fire at even 360-degree intervals but the horizontal cylinder "
              "arrangement produces a unique lateral rocking vibration. The mechanical valve "
              "train on older air-cooled boxers is louder than DOHC engines. Loose valve "
              "clearances produce a characteristic tick that's very audible with the exposed cylinders.",
    ),
}


class SignatureMatch(BaseModel):
    """Result of comparing a spectrogram against an engine signature."""
    engine_type: EngineType = Field(description="Matched engine type")
    confidence: float = Field(description="Match confidence 0.0 to 1.0")
    firing_freq_match: bool = Field(default=False, description="Peak freq falls in expected firing range")
    harmonic_score: float = Field(default=0.0, description="How well harmonics match expected pattern (0-1)")
    notes: str = Field(default="", description="Diagnostic notes about the match")


class SoundSignatureDB:
    """Database of known engine sound signatures.

    Compares recorded spectrograms against the signature library to
    identify engine type and detect deviations from expected profiles.
    """

    def __init__(self, signatures: Optional[dict[EngineType, SoundSignature]] = None):
        """Initialize with signature library.

        Args:
            signatures: Custom signatures dict. Defaults to built-in SIGNATURES.
        """
        self.signatures = signatures if signatures is not None else SIGNATURES

    def get_signature(self, engine_type: EngineType) -> Optional[SoundSignature]:
        """Look up the sound signature for a specific engine type.

        Args:
            engine_type: The engine configuration to look up.

        Returns:
            SoundSignature if found, None otherwise.
        """
        return self.signatures.get(engine_type)

    def estimate_rpm(self, firing_frequency: float, engine_type: EngineType) -> float:
        """Estimate engine RPM from the observed firing frequency and engine type.

        Inverse of rpm_to_firing_frequency():
            RPM = firing_freq * 120 / cylinders

        Args:
            firing_frequency: Observed firing frequency in Hz.
            engine_type: Engine configuration (determines cylinder count).

        Returns:
            Estimated RPM.
        """
        cylinders = _ENGINE_CYLINDERS[engine_type]
        if cylinders == 0:
            return 0.0
        return (firing_frequency * 120.0) / cylinders

    def match_profile(
        self,
        spectrogram: SpectrogramResult,
        top_n: int = 3,
    ) -> list[SignatureMatch]:
        """Compare a spectrogram against all known engine signatures.

        Scoring considers:
        1. Whether the peak frequency falls in the expected firing frequency range
           (at idle or 5000 RPM — we check both)
        2. How well the observed harmonics match the expected harmonic pattern
        3. Energy distribution across frequency bands

        Args:
            spectrogram: SpectrogramResult from SpectrogramAnalyzer.
            top_n: Number of top matches to return.

        Returns:
            List of SignatureMatch sorted by confidence (highest first).
        """
        if not spectrogram.frequency_bins or not spectrogram.magnitude_bins:
            return []

        peak_freq = spectrogram.peak_frequency
        matches: list[SignatureMatch] = []

        for engine_type, sig in self.signatures.items():
            score = 0.0
            freq_match = False
            notes_parts: list[str] = []

            # --- Criterion 1: Peak frequency in expected firing range (0-50 points) ---
            # Check idle range
            if sig.firing_freq_idle_low <= peak_freq <= sig.firing_freq_idle_high:
                score += 50.0
                freq_match = True
                est_rpm = self.estimate_rpm(peak_freq, engine_type)
                notes_parts.append(f"Peak {peak_freq:.1f} Hz matches idle range, est. {est_rpm:.0f} RPM")
            # Check 5000 RPM range
            elif sig.firing_freq_5000_low <= peak_freq <= sig.firing_freq_5000_high:
                score += 45.0
                freq_match = True
                est_rpm = self.estimate_rpm(peak_freq, engine_type)
                notes_parts.append(f"Peak {peak_freq:.1f} Hz matches 5000 RPM range, est. {est_rpm:.0f} RPM")
            else:
                # Partial credit for being close (within 2x the range width)
                idle_center = (sig.firing_freq_idle_low + sig.firing_freq_idle_high) / 2
                idle_width = sig.firing_freq_idle_high - sig.firing_freq_idle_low
                if idle_width > 0:
                    distance = abs(peak_freq - idle_center) / idle_width
                    if distance < 2.0:
                        partial = max(0, 25.0 * (1.0 - distance / 2.0))
                        score += partial
                        notes_parts.append(f"Peak {peak_freq:.1f} Hz near idle range (distance={distance:.1f})")

                rev_center = (sig.firing_freq_5000_low + sig.firing_freq_5000_high) / 2
                rev_width = sig.firing_freq_5000_high - sig.firing_freq_5000_low
                if rev_width > 0:
                    distance = abs(peak_freq - rev_center) / rev_width
                    if distance < 2.0:
                        partial = max(0, 20.0 * (1.0 - distance / 2.0))
                        score += partial

            # --- Criterion 2: Harmonic pattern match (0-30 points) ---
            harmonic_score = self._score_harmonics(spectrogram, peak_freq, sig.expected_harmonics)
            score += harmonic_score * 30.0
            if harmonic_score > 0.5:
                notes_parts.append(f"Harmonic pattern match: {harmonic_score:.0%}")

            # --- Criterion 3: Band energy distribution (0-20 points) ---
            band_score = self._score_band_distribution(spectrogram, engine_type)
            score += band_score * 20.0

            confidence = min(1.0, score / 100.0)

            matches.append(SignatureMatch(
                engine_type=engine_type,
                confidence=round(confidence, 3),
                firing_freq_match=freq_match,
                harmonic_score=round(harmonic_score, 3),
                notes="; ".join(notes_parts) if notes_parts else "No strong spectral match",
            ))

        # Sort by confidence descending
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches[:top_n]

    def _score_harmonics(
        self,
        spectrogram: SpectrogramResult,
        fundamental_freq: float,
        expected_harmonics: list[float],
    ) -> float:
        """Score how well the observed harmonics match expected pattern.

        For each expected harmonic multiplier, check if there's significant
        energy at that frequency (within a tolerance window).

        Returns:
            Score from 0.0 to 1.0.
        """
        if fundamental_freq <= 0 or not expected_harmonics:
            return 0.0
        if not spectrogram.frequency_bins or not spectrogram.magnitude_bins:
            return 0.0

        # Frequency resolution determines our tolerance window
        if len(spectrogram.frequency_bins) >= 2:
            freq_res = spectrogram.frequency_bins[1] - spectrogram.frequency_bins[0]
        else:
            return 0.0

        tolerance = max(freq_res * 1.5, 10.0)  # At least 10 Hz tolerance

        # Find overall max magnitude for normalization
        max_mag = max(spectrogram.magnitude_bins[1:]) if len(spectrogram.magnitude_bins) > 1 else 1.0
        if max_mag == 0:
            return 0.0

        hits = 0
        for harmonic_mult in expected_harmonics:
            target_freq = fundamental_freq * harmonic_mult
            # Find magnitude at target frequency
            best_mag = 0.0
            for freq, mag in zip(spectrogram.frequency_bins, spectrogram.magnitude_bins):
                if abs(freq - target_freq) <= tolerance:
                    best_mag = max(best_mag, mag)

            # Count as a hit if magnitude is above 10% of peak
            if best_mag > max_mag * 0.10:
                hits += 1

        return hits / len(expected_harmonics)

    def _score_band_distribution(
        self,
        spectrogram: SpectrogramResult,
        engine_type: EngineType,
    ) -> float:
        """Score energy distribution across bands for a given engine type.

        Different engine types concentrate energy in different bands.
        V-twins have more low_rumble; inline-4s have more valve_train.

        Returns:
            Score from 0.0 to 1.0.
        """
        if not spectrogram.band_energies:
            return 0.0

        total_energy = sum(spectrogram.band_energies.values())
        if total_energy == 0:
            return 0.0

        # Expected dominant bands per engine type
        expected_dominant: dict[EngineType, list[str]] = {
            EngineType.SINGLE_CYLINDER: ["firing_frequency", "low_rumble", "exhaust_note"],
            EngineType.V_TWIN: ["low_rumble", "firing_frequency", "exhaust_note"],
            EngineType.PARALLEL_TWIN: ["firing_frequency", "exhaust_note", "valve_train"],
            EngineType.INLINE_THREE: ["firing_frequency", "exhaust_note", "valve_train"],
            EngineType.INLINE_FOUR: ["firing_frequency", "valve_train", "exhaust_note"],
            EngineType.V_FOUR: ["firing_frequency", "exhaust_note", "low_rumble"],
            EngineType.BOXER_TWIN: ["firing_frequency", "exhaust_note", "valve_train"],
        }

        expected = expected_dominant.get(engine_type, ["firing_frequency"])
        expected_energy = sum(spectrogram.band_energies.get(b, 0.0) for b in expected)
        fraction_in_expected = expected_energy / total_energy

        return min(1.0, fraction_in_expected)
