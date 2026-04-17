# MotoDiag Phase 120 — Engine Sound Signature Library Expansion

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Extend the existing `src/motodiag/media/sound_signatures.py` library (Phase 98) with brand-specific and powertrain-specific variants that generic 7-type taxonomy cannot capture. Adds 4 new entries: **ELECTRIC_MOTOR** (Zero/LiveWire/Energica motor whine), **DUCATI_L_TWIN** (90° desmo with dry-clutch rattle), **KTM_LC8_V_TWIN** (75° V-twin with its own firing interval signature), **TRIUMPH_TRIPLE** (Triumph-specific 120° triple, distinct from generic inline-3). Ties into Phase 110's PowertrainType enum so electric motors aren't forced through combustion signature fields. No migrations — this is a pure data/code expansion.

CLI: `python -m pytest tests/test_phase120_sound_signatures_expansion.py -v`

Outputs: Extended `media/sound_signatures.py` (4 new enum members + 4 new signatures + 1 helper for electric), 1 new test file (~20 tests)

## Logic
1. **New `EngineType` enum members** — 4 additions:
   - `ELECTRIC_MOTOR` — any permanent-magnet synchronous electric motor (covers Zero SR/F, LiveWire One, Energica Eva Ribelle)
   - `DUCATI_L_TWIN` — Ducati 90° V-twin with desmodromic valves + dry-clutch rattle (Monster, Panigale V2, Scrambler)
   - `KTM_LC8_V_TWIN` — KTM 75° V-twin (1290 Super Duke, 1290 Adventure, 1290 Super Adventure)
   - `TRIUMPH_TRIPLE` — Triumph 120° crank inline-3 (Street Triple, Speed Triple, Tiger 900)

2. **Reinterpretation of `firing_freq_*` fields** for electric motors:
   - Existing semantic: combustion firing frequency = `(RPM/60) × (cylinders/strokes_per_cycle)`
   - For electric: same fields represent **motor whine fundamental** = `(motor_RPM/60) × pole_pairs`. Documented in the signature's `notes` field.
   - Adds `motor_rpm_to_whine_frequency(motor_rpm, pole_pairs)` helper function alongside existing `rpm_to_firing_frequency`

3. **4 new SIGNATURES entries**:
   - **ELECTRIC_MOTOR**: no firing pulse, dominant spectral content is motor whine (250-500 Hz at 3000 motor RPM assuming 4 pole pairs), inverter switching noise (~10-20 kHz), gear reduction whine (~1-3 kHz for Zero, ~500-800 Hz for LiveWire). characteristic_sounds: "smooth rising whine proportional to speed", "no idle — silent when stationary", "motor whine fundamental at 250-500 Hz low speed, scales linearly with motor RPM", "inverter IGBT switching produces audible carrier tone around 10-16 kHz", "regen braking produces whine shift and sometimes clicking from contactor"
   - **DUCATI_L_TWIN**: 90° V firing at 270°/450° intervals (more even than Harley 45° but still uneven), desmo valve system produces audible click at 2x firing frequency, dry clutch rattle (audible at idle, fades with engine RPM). characteristic_sounds: "pronounced dry clutch rattle at idle — '<rattle-rattle-rattle>' around 40-60 Hz separate from firing", "desmo valve click at 2x firing frequency — sharp tick-tick-tick layered on exhaust", "more even firing than Harley 45° but less than inline — 'lumpy' character", "exhaust note medium-low, not as deep as Harley but deeper than inline-4", "cam belt (pre-Panigale V2) produces hum in 300-600 Hz band"
   - **KTM_LC8_V_TWIN**: 75° V firing at 285°/435° intervals, "balanced V" character. characteristic_sounds: "distinct firing rhythm unlike 45°/90°/120° V-twins", "characteristic intake 'honk' from oval-bore throttle bodies", "balancer shaft smooths low-RPM vibration compared to unbalanced twins", "aggressive midrange growl — sits between Ducati L-twin smoothness and Harley V-twin rumble", "chain/sprocket noise prominent due to single-sided drive"
   - **TRIUMPH_TRIPLE**: 120° even-fire crank, Triumph-specific intake and exhaust tuning. characteristic_sounds: "signature 'melodic growl' — more musical than inline-4, less bass than twin", "strong third harmonic from 120° firing pattern", "Street Triple distinctive 'howl' above 8000 RPM from intake resonance", "680-765-765HC-900-1050-1200 displacement variants share the signature but scale frequency", "cam chain guides can produce rattle between 800-1500 Hz on high-mileage engines (>60k mi)"

4. **1 new helper function** `motor_rpm_to_whine_frequency(motor_rpm: float, pole_pairs: int) -> float`:
   ```python
   return motor_rpm * pole_pairs / 60.0
   ```

5. **No migration needed** — this is pure Python constants + code. No DB changes. No SCHEMA_VERSION bump.

## Key Concepts
- **Brand-specific variants coexist with generic types**: `V_TWIN` (generic Harley-style) stays; new entries are peers, not replacements. Classifier code can fall back to generic when a specific variant isn't identified.
- **Electric motor signature uses the same SoundSignature fields**: `firing_freq_*` reinterpreted as "dominant spectral peak frequency" — works for both combustion and motors. Documented in each electric signature's `notes`.
- **Dry clutch rattle as diagnostic marker**: `DUCATI_L_TWIN` signature explicitly lists dry clutch rattle as *normal* characteristic. Mechanics new to Ducatis misidentify it as a fault; the signature prevents false positives from spectral analyzers.
- **Gear whine for electric**: unlike ICE, electric motors transfer torque through a fixed-ratio gear reduction (no clutch slip). Gear mesh frequency is a key spectral feature — `GEAR_MESH_HZ = motor_rpm × teeth_count / 60`. Zero uses ~9:1, LiveWire ~5:1. Signature lists approximate gear whine ranges.
- **Motor pole pair assumption**: typical motorcycle traction motors have 4-8 pole pairs; default analysis assumes 4 (standard permanent-magnet synchronous). Edge-case motors (reluctance, induction) fall outside this signature.
- **No DB substrate change**: Phase 120 stays in the existing in-memory dict; Track Q phases (or later sound-focused phases) can migrate to a DB-backed table when the signature library grows past ~50 entries.

## Verification Checklist
- [ ] 4 new EngineType enum members added (ELECTRIC_MOTOR, DUCATI_L_TWIN, KTM_LC8_V_TWIN, TRIUMPH_TRIPLE)
- [ ] 4 new SIGNATURES dict entries with accurate firing/whine frequencies
- [ ] Each new signature has ≥4 characteristic_sounds entries
- [ ] Each new signature has accurate cylinder count (2 for Ducati/KTM, 3 for Triumph, 0 for electric)
- [ ] motor_rpm_to_whine_frequency helper function works: 3000 RPM × 4 pole pairs = 200 Hz
- [ ] ELECTRIC_MOTOR firing_freq fields populated with whine frequency (not combustion)
- [ ] DUCATI_L_TWIN signature mentions dry clutch rattle as *normal*, not fault
- [ ] KTM_LC8 signature mentions 75° V-twin firing intervals
- [ ] TRIUMPH_TRIPLE signature distinct from generic INLINE_THREE (Triumph-specific details)
- [ ] Existing 7 generic signatures still present and unchanged (regression test)
- [ ] SoundSignatureDB can load all 11 signatures (7 existing + 4 new)
- [ ] Existing Phase 98 signature tests still pass (zero regressions)
- [ ] All 1954 existing tests still pass

## Risks
- **Signature accuracy is opinion-based**: firing frequencies are physics, but "characteristic sounds" are subjective. Mitigated by conservative ranges based on dyno recordings and forum consensus. Future Track R phases can refine based on actual mechanic feedback.
- **Electric motor fields are reinterpreted**: `firing_freq_*` names don't match electric semantics. Trade-off accepted to avoid a parallel signature model. If a future phase needs motor-specific fields (pole_pairs, gear_ratio, inverter_carrier), extend SoundSignature with optional fields rather than creating a second class.
- **Dry clutch rattle detection is Ducati-specific**: if a Phase R learning system trains on generic V-twin audio, it may mis-flag Ducati dry clutch rattle as a fault. Signature explicitly documents this as normal.
- **120° Triple signature supplements but doesn't replace INLINE_THREE**: classifier must prefer the specific variant when make hint is present. Default behavior without a hint should still match the generic.
