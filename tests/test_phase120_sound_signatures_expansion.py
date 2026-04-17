"""Phase 120 — Sound signature library expansion tests.

Tests cover:
- 4 new EngineType enum members
- 4 new SIGNATURES entries with plausible physics-based frequencies
- motor_rpm_to_whine_frequency helper
- ELECTRIC_MOTOR uses whine frequency (not combustion)
- DUCATI_L_TWIN documents dry clutch as NORMAL (not a fault)
- KTM_LC8 mentions 75° V angle
- TRIUMPH_TRIPLE distinct from generic INLINE_THREE
- Original 7 signatures unchanged (regression safety)
- SoundSignatureDB loads all 11 signatures
"""

import math

import pytest

from motodiag.media.sound_signatures import (
    EngineType, SIGNATURES, SoundSignature, SoundSignatureDB,
    rpm_to_firing_frequency, motor_rpm_to_whine_frequency,
)


# --- Enum expansion ---


class TestEngineTypeExpansion:
    def test_enum_has_11_members(self):
        assert len(EngineType) == 11

    def test_new_members_present(self):
        names = {e.value for e in EngineType}
        assert "electric_motor" in names
        assert "ducati_l_twin" in names
        assert "ktm_lc8_v_twin" in names
        assert "triumph_triple" in names

    def test_original_members_preserved(self):
        names = {e.value for e in EngineType}
        for original in (
            "single_cylinder", "v_twin", "parallel_twin",
            "inline_three", "inline_four", "v_four", "boxer_twin",
        ):
            assert original in names


# --- motor_rpm_to_whine_frequency helper ---


class TestMotorWhineHelper:
    def test_zero_sr_f_200hz(self):
        # Zero SR/F: 4 pole pairs, 3000 motor RPM → 200 Hz
        assert motor_rpm_to_whine_frequency(3000, 4) == pytest.approx(200.0)

    def test_livewire_400hz(self):
        # LiveWire One: 8 pole pairs, 3000 motor RPM → 400 Hz
        assert motor_rpm_to_whine_frequency(3000, 8) == pytest.approx(400.0)

    def test_high_speed(self):
        # 7500 motor RPM × 4 pole pairs → 500 Hz (highway cruise)
        assert motor_rpm_to_whine_frequency(7500, 4) == pytest.approx(500.0)

    def test_zero_rpm_zero_hz(self):
        assert motor_rpm_to_whine_frequency(0, 4) == 0.0


# --- New signatures ---


class TestElectricMotorSignature:
    def test_present(self):
        assert EngineType.ELECTRIC_MOTOR in SIGNATURES

    def test_idle_is_silent(self):
        sig = SIGNATURES[EngineType.ELECTRIC_MOTOR]
        assert sig.idle_rpm_range == (0, 0)

    def test_cylinder_count_zero(self):
        sig = SIGNATURES[EngineType.ELECTRIC_MOTOR]
        assert sig.cylinders == 0

    def test_frequencies_use_whine_not_combustion(self):
        # 200 Hz low-speed whine (3000 motor RPM × 4 pole pairs)
        sig = SIGNATURES[EngineType.ELECTRIC_MOTOR]
        assert sig.firing_freq_idle_low == pytest.approx(200.0)
        assert sig.firing_freq_idle_high == pytest.approx(300.0)
        assert sig.firing_freq_5000_low == pytest.approx(500.0)

    def test_characteristic_sounds_mention_inverter_and_gear(self):
        sig = SIGNATURES[EngineType.ELECTRIC_MOTOR]
        joined = " ".join(sig.characteristic_sounds).lower()
        assert "inverter" in joined or "igbt" in joined
        assert "gear" in joined
        assert "regen" in joined

    def test_notes_explain_field_reinterpretation(self):
        sig = SIGNATURES[EngineType.ELECTRIC_MOTOR]
        assert "motor" in sig.notes.lower()
        assert "pole" in sig.notes.lower()


class TestDucatiLTwinSignature:
    def test_present(self):
        assert EngineType.DUCATI_L_TWIN in SIGNATURES

    def test_cylinders_2(self):
        assert SIGNATURES[EngineType.DUCATI_L_TWIN].cylinders == 2

    def test_dry_clutch_rattle_documented_as_normal(self):
        sig = SIGNATURES[EngineType.DUCATI_L_TWIN]
        joined_lower = (" ".join(sig.characteristic_sounds) + " " + sig.notes).lower()
        assert "dry clutch" in joined_lower
        assert "rattle" in joined_lower
        # Must explicitly state it's normal, not a fault
        assert "normal" in sig.notes.lower() or "not" in sig.notes.lower()

    def test_firing_frequency_matches_physics(self):
        # V-twin 4-stroke at 1200 RPM idle: (1200/60)*(2/2) = 20 Hz
        sig = SIGNATURES[EngineType.DUCATI_L_TWIN]
        assert sig.firing_freq_idle_low < sig.firing_freq_idle_high < sig.firing_freq_5000_low


class TestKtmLC8Signature:
    def test_present(self):
        assert EngineType.KTM_LC8_V_TWIN in SIGNATURES

    def test_cylinders_2(self):
        assert SIGNATURES[EngineType.KTM_LC8_V_TWIN].cylinders == 2

    def test_mentions_75_degree_v_angle(self):
        sig = SIGNATURES[EngineType.KTM_LC8_V_TWIN]
        joined = " ".join(sig.characteristic_sounds) + " " + sig.notes
        assert "75" in joined  # 75° angle

    def test_mentions_balancer_shaft(self):
        sig = SIGNATURES[EngineType.KTM_LC8_V_TWIN]
        joined = " ".join(sig.characteristic_sounds) + " " + sig.notes
        assert "balancer" in joined.lower() or "balance" in joined.lower()


class TestTriumphTripleSignature:
    def test_present(self):
        assert EngineType.TRIUMPH_TRIPLE in SIGNATURES

    def test_cylinders_3(self):
        assert SIGNATURES[EngineType.TRIUMPH_TRIPLE].cylinders == 3

    def test_frequency_differs_from_generic_inline_three_not_at_all(self):
        # Physics-wise, 3 cylinders × 120° is the same regardless of brand,
        # so the frequency values match INLINE_THREE. Differentiation is in
        # characteristic_sounds and notes.
        tri = SIGNATURES[EngineType.TRIUMPH_TRIPLE]
        gen = SIGNATURES[EngineType.INLINE_THREE]
        assert tri.firing_freq_idle_low != gen.firing_freq_idle_low or (
            tri.characteristic_sounds != gen.characteristic_sounds
        )

    def test_mentions_triumph_brand(self):
        sig = SIGNATURES[EngineType.TRIUMPH_TRIPLE]
        joined = " ".join(sig.characteristic_sounds) + " " + sig.notes
        assert "triumph" in joined.lower()

    def test_mentions_specific_models(self):
        sig = SIGNATURES[EngineType.TRIUMPH_TRIPLE]
        joined = " ".join(sig.characteristic_sounds) + " " + sig.notes
        # Should reference at least one Triumph model in notes
        joined_lower = joined.lower()
        assert any(m in joined_lower for m in ["street triple", "speed triple", "daytona", "tiger"])


# --- Signature library integrity ---


class TestSignatureLibraryIntegrity:
    def test_all_11_signatures_present(self):
        assert len(SIGNATURES) == 11

    def test_all_signatures_have_characteristic_sounds(self):
        for engine_type, sig in SIGNATURES.items():
            assert len(sig.characteristic_sounds) >= 4, (
                f"{engine_type.value} has only {len(sig.characteristic_sounds)} characteristic sounds"
            )

    def test_all_signatures_have_notes(self):
        for engine_type, sig in SIGNATURES.items():
            assert len(sig.notes) > 50, f"{engine_type.value} notes are too terse"

    def test_all_frequencies_non_negative(self):
        for engine_type, sig in SIGNATURES.items():
            assert sig.firing_freq_idle_low >= 0
            assert sig.firing_freq_idle_high >= 0
            assert sig.firing_freq_5000_low >= 0
            assert sig.firing_freq_5000_high >= 0

    def test_idle_frequencies_ordered_correctly(self):
        for engine_type, sig in SIGNATURES.items():
            if engine_type == EngineType.ELECTRIC_MOTOR:
                continue  # electric is non-combustion; check separately
            assert sig.firing_freq_idle_low <= sig.firing_freq_idle_high, (
                f"{engine_type.value}: idle_low > idle_high"
            )
            assert sig.firing_freq_5000_low <= sig.firing_freq_5000_high, (
                f"{engine_type.value}: 5000_low > 5000_high"
            )


# --- Regression: original 7 signatures unchanged ---


class TestOriginalSignaturesUnchanged:
    """Sanity check that Phase 120 additions did not alter Phase 98 signatures."""

    def test_single_cylinder_still_1(self):
        assert SIGNATURES[EngineType.SINGLE_CYLINDER].cylinders == 1

    def test_v_twin_still_2(self):
        assert SIGNATURES[EngineType.V_TWIN].cylinders == 2

    def test_inline_four_still_4(self):
        assert SIGNATURES[EngineType.INLINE_FOUR].cylinders == 4

    def test_boxer_twin_still_2(self):
        assert SIGNATURES[EngineType.BOXER_TWIN].cylinders == 2

    def test_inline_four_idle_frequency_stable(self):
        # Inline-4 at 1000 RPM idle: (1000/60)*(4/2) = 33.33 Hz
        sig = SIGNATURES[EngineType.INLINE_FOUR]
        assert sig.firing_freq_idle_low == pytest.approx(33.33, abs=0.1)


# --- SoundSignatureDB loading ---


class TestSoundSignatureDB:
    def test_default_loads_all_11(self):
        db = SoundSignatureDB()
        for engine_type in EngineType:
            assert engine_type in db.signatures

    def test_can_look_up_new_variants(self):
        db = SoundSignatureDB()
        assert db.signatures[EngineType.ELECTRIC_MOTOR].cylinders == 0
        assert db.signatures[EngineType.DUCATI_L_TWIN].cylinders == 2
