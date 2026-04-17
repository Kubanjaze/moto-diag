# MotoDiag Phase 120 — Engine Sound Signature Library Expansion

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Extend the existing `src/motodiag/media/sound_signatures.py` library (Phase 98) with brand-specific and powertrain-specific variants that generic 7-type taxonomy cannot capture. Adds 4 new entries: **ELECTRIC_MOTOR** (Zero/LiveWire/Energica motor whine), **DUCATI_L_TWIN** (90° desmo with dry-clutch rattle), **KTM_LC8_V_TWIN** (75° V-twin), **TRIUMPH_TRIPLE** (Triumph-specific 120° triple, distinct from generic inline-3). Also updates 3 Phase 98 tests to forward-compat pattern so electric motors (which have no combustion firing frequency) don't fail combustion-specific assertions. No migration — pure data/code expansion.

CLI: `python -m pytest tests/test_phase120_sound_signatures_expansion.py -v`

Outputs: Extended `media/sound_signatures.py` (4 new enum members + 4 new SIGNATURES entries + 1 motor helper), updated `tests/test_phase98_sound_signatures.py` (3 forward-compat fixes), new `tests/test_phase120_sound_signatures_expansion.py` (38 tests)

## Logic
1. **4 new `EngineType` enum members** appended: ELECTRIC_MOTOR, DUCATI_L_TWIN, KTM_LC8_V_TWIN, TRIUMPH_TRIPLE. Enum now has 11 members total (7 original + 4 new).

2. **`_ENGINE_CYLINDERS` extended** with cylinder counts — Ducati/KTM = 2, Triumph = 3, electric = 0 (no cylinders, rotor + stator).

3. **New helper `motor_rpm_to_whine_frequency(motor_rpm, pole_pairs)`**: returns `motor_rpm * pole_pairs / 60.0`. Electric motor dominant spectral peak. Test-validated with Zero SR/F (4 pole pairs, 200 Hz @ 3000 RPM) and LiveWire One (8 pole pairs, 400 Hz @ 3000 RPM).

4. **4 new SIGNATURES entries** with physics-grounded frequencies + rich characteristic_sounds + diagnostic notes:
   - **ELECTRIC_MOTOR**: idle_rpm_range (0, 0) since no idle, firing_freq_* fields reinterpreted as whine frequency (200-600 Hz typical), harmonics [1, 2, 3, 6, 12] reflecting slot geometry. Characteristic sounds cover inverter IGBT switching, gear reduction whine, regen contactor clicks, tire/chain noise prominence without combustion masking. Notes document field reinterpretation and key diagnostic markers (inverter carrier tone = IGBT health, gear whine shift under load = reduction-gear bearing wear, continuous contactor click = stuck contactor).
   - **DUCATI_L_TWIN**: 90° V firing at 270°/450° intervals. Dry clutch rattle **explicitly documented as NORMAL** so mechanics unfamiliar with Ducatis don't misdiagnose. Desmo valve click at 2x firing frequency. Cam belt hum on pre-Panigale V2 engines. Covers Monster, Panigale V2, Scrambler 800/1100, Multistrada 950.
   - **KTM_LC8_V_TWIN**: 75° V firing at 285°/435° intervals — firing angle almost unique in motorcycles. Oval-bore throttle body intake "honk", balancer shaft, timing chain tensioner tick. Covers 1190/1290 Super Duke, Adventure, Super Adventure.
   - **TRIUMPH_TRIPLE**: 120° even-fire crank with Triumph-specific intake resonance producing the trademark "howl" above 8000 RPM. Covers Street Triple 675/765, Speed Triple 1050/1200, Daytona 675/765, Tiger 900/1200. Classifier should prefer this over generic INLINE_THREE when Triumph make hint present.

5. **3 forward-compat test updates** in `tests/test_phase98_sound_signatures.py`:
   - `test_all_engine_types_defined`: changed from exact-match set (`==`) to superset (`.issubset()`) — original 7 remain required, new additions don't break it.
   - `test_signature_fields_populated`: loops all SIGNATURES; electric motor has `continue` branch that skips combustion-specific assertions (idle_rpm_range ordering, cylinders > 0) but still validates whine fundamentals + characteristic sounds.
   - `test_estimate_rpm_roundtrip`: `continue` over ELECTRIC_MOTOR — electric motors have no combustion firing frequency, so `estimate_rpm` (combustion-specific) would round-trip to 0.

6. **No migration needed** — pure in-memory dict expansion, no DB changes, no SCHEMA_VERSION bump.

## Key Concepts
- **Brand-specific variants coexist with generic types**: `V_TWIN` (generic Harley-style) stays; new entries are peers, not replacements. Classifier code falls back to generic when a specific variant isn't identified.
- **Electric motor fields reinterpreted**: `firing_freq_*` carry motor whine fundamental = motor_RPM × pole_pairs / 60. Documented in each electric signature's `notes`. Trade-off: avoids a parallel signature model; pays the cost of one concept-overload per field.
- **Dry clutch rattle as diagnostic marker**: `DUCATI_L_TWIN` signature explicitly lists dry clutch rattle as *normal* characteristic — prevents false positives from spectral analyzers trained on non-dry-clutch V-twins.
- **Triumph-specific triple signature**: physics is identical to generic INLINE_THREE (120° crank × 3 cylinders × 4-stroke = same firing frequency), but characteristic_sounds and notes capture Triumph's intake-tuning signature ("melodic growl", 8k RPM howl). Classifier selection logic must prefer specific-brand match when make hint present.
- **Forward-compat test pattern extension**: the `>=` pattern established for schema versions now applies to enum-backed collections. When adding new members to an existing enum, prefer `issubset`/`in` over exact equality in existing tests.
- **No DB substrate change**: Phase 120 stays in the existing in-memory dict. Track Q phases (or later sound-focused phases) can migrate to a DB-backed table when the signature library grows past ~50 entries.

## Verification Checklist
- [x] 4 new EngineType enum members added (ELECTRIC_MOTOR, DUCATI_L_TWIN, KTM_LC8_V_TWIN, TRIUMPH_TRIPLE)
- [x] 4 new SIGNATURES dict entries with accurate firing/whine frequencies
- [x] Each new signature has ≥4 characteristic_sounds entries
- [x] Each new signature has accurate cylinder count (2 for Ducati/KTM, 3 for Triumph, 0 for electric)
- [x] motor_rpm_to_whine_frequency helper works: 3000 RPM × 4 pole pairs = 200 Hz, × 8 = 400 Hz, edge case 0 RPM = 0 Hz
- [x] ELECTRIC_MOTOR firing_freq fields populated with whine frequency (200-600 Hz range) not combustion
- [x] DUCATI_L_TWIN signature mentions dry clutch rattle as *normal*, not fault
- [x] KTM_LC8 signature mentions 75° V-twin firing interval and balancer shaft
- [x] TRIUMPH_TRIPLE signature mentions Triumph brand + specific models (Street Triple, Speed Triple, Daytona, Tiger)
- [x] Existing 7 generic signatures still present and unchanged (frequencies and cylinder counts stable)
- [x] SoundSignatureDB can load all 11 signatures (verified via `test_default_loads_all_11` + `test_get_signature_all_types`)
- [x] 3 forward-compat updates to Phase 98 tests (superset check + electric exemptions)
- [x] All 1954 existing tests still pass after Phase 98 test fixes — full suite 1992/1992 in 11:00

## Risks
- **Signature accuracy is opinion-based**: firing frequencies are physics, but "characteristic sounds" are subjective. Mitigated by conservative ranges based on dyno recordings and forum consensus. Future Track R phases can refine based on actual mechanic feedback.
- **Electric motor fields are reinterpreted**: `firing_freq_*` names don't match electric semantics. Trade-off accepted to avoid a parallel signature model. If a future phase needs motor-specific fields (pole_pairs, gear_ratio, inverter_carrier), extend SoundSignature with optional fields rather than creating a second class.
- **Dry clutch rattle detection is Ducati-specific**: if a Phase R learning system trains on generic V-twin audio, it may mis-flag Ducati dry clutch rattle as a fault. Signature explicitly documents this as normal — future learning phases must respect the `notes` field.
- **120° Triple signature supplements but doesn't replace INLINE_THREE**: classifier must prefer the specific variant when make hint is present. Default behavior without a hint still matches the generic. Documented in TRIUMPH_TRIPLE notes.
- **Initial regression surfaced 3 Phase 98 test failures**: resolved by forward-compat updates. Validates the zero-regression rule — electric motors broke hidden assumptions (cylinder > 0, idle range ordering, combustion roundtrip) that weren't caught until runtime.

## Deviations from Plan
- **3 Phase 98 test fixes not in original plan**: Required because existing tests made combustion-engine assumptions that electric motors broke. Applied the same forward-compat pattern already used for schema versions (`>=` + member exemption). Documented in Key Concepts so future phases know the pattern.
- **Test count 38 vs planned ~20**: More thorough than planned — added `TestSignatureLibraryIntegrity` suite ensuring all 11 signatures have populated characteristic_sounds, notes, and physics-sane frequencies; plus `TestOriginalSignaturesUnchanged` regression suite proving Phase 98 data stayed stable.

## Results
| Metric | Value |
|--------|-------|
| Modified files | 2 (`media/sound_signatures.py`, `tests/test_phase98_sound_signatures.py`) |
| New files | 1 (`tests/test_phase120_sound_signatures_expansion.py`) |
| New tests | 38 |
| Total tests | 1992 passing (was 1954) |
| New enum members | 4 (11 total) |
| New signatures | 4 (11 total) |
| New helper function | 1 (`motor_rpm_to_whine_frequency`) |
| Regression fixes | 3 (forward-compat updates in Phase 98 tests) |
| Schema version | No change (no migration) |
| Regression status | Zero regressions after forward-compat fixes — full suite 11:00 runtime |

Phase 120 expands the signature library from a generic 7-type taxonomy to 11 entries with brand/powertrain specificity. The **electric motor signature proves the library can handle non-combustion powertrains** without architectural changes — critical for Track L (electric motorcycle) phase work. The **Ducati dry-clutch-is-normal documentation** is the most operationally valuable entry: it will prevent any future learning system from flagging a healthy dry-clutch Ducati as faulty. **Forward-compat test pattern** now formally applies to enum membership, not just schema versions.
