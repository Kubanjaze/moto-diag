# Phase 380: live after the apply, against the backup

- **Scope problems:** `none`
- **Equals the approved exact diff:** `yes`
- **F158 census on live:** `36`

## schema added: index idx_known_issues_row_key

```sql
CREATE UNIQUE INDEX idx_known_issues_row_key ON known_issues(row_key)
```

## schema removed: index idx_known_issues_identity

## schema changed: table known_issues

```sql
CREATE TABLE "known_issues" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year_start INTEGER,
                year_end INTEGER,
                severity TEXT NOT NULL DEFAULT 'medium',
                symptoms TEXT,
                dtc_codes TEXT,
                causes TEXT,
                fix_procedure TEXT,
                parts_needed TEXT,
                estimated_hours REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_user_id INTEGER DEFAULT 1,
                source TEXT NOT NULL DEFAULT 'unverified'
                    CHECK (source IN (
                        'unverified', 'model-generated', 'forum',
                        'service-manual', 'mechanic-verified', 'regulation'
                    )),
                applicability TEXT
                    CHECK (applicability IS NULL OR json_valid(applicability))
            , row_key TEXT)
```

## known_issue_models: +0 added, 0 changed, 109 removed
- removed rowid 1069: (4593, 'Kymco', 'Wolf CR300i')
- removed rowid 1085: (4596, 'Kymco', 'Wolf CR300i')
- removed rowid 1219: (4604, 'Piaggio', 'LX50')
- removed rowid 1249: (4606, 'Piaggio', 'LX50')
- removed rowid 1279: (4607, 'Piaggio', 'LX50')
- removed rowid 1309: (4608, 'Piaggio', 'LX50')
- removed rowid 1339: (4610, 'Piaggio', 'LX50')
- removed rowid 1369: (4611, 'Piaggio', 'LX50')
- removed rowid 1399: (4612, 'Piaggio', 'LX50')
- removed rowid 1429: (4605, 'Piaggio', 'LX50')
- removed rowid 1788: (4574, 'Piaggio', 'LX50')
- removed rowid 1792: (4574, 'Piaggio', 'Primavera 150')
- removed rowid 1795: (4574, 'Piaggio', 'S50')
- removed rowid 1809: (4574, 'Vespa', 'MP3 250')
- removed rowid 1815: (4569, 'Piaggio', 'GTS 310')
- removed rowid 1828: (4576, 'Piaggio', 'GTS 310')
- removed rowid 1834: (4576, 'Piaggio', 'Primavera 150')
- removed rowid 1835: (4576, 'Piaggio', 'Sprint 125')
- removed rowid 1836: (4576, 'Piaggio', 'Sprint 150')
- removed rowid 2169: (4563, 'Harley-Davidson', 'Ego')
- removed rowid 2175: (4563, 'LiveWire', 'Ego')
- removed rowid 2183: (4563, 'Zero', 'Ego')
- removed rowid 2198: (4564, 'Harley-Davidson', 'Ego')
- removed rowid 2204: (4564, 'LiveWire', 'Ego')
- removed rowid 2212: (4564, 'Zero', 'Ego')
- removed rowid 2227: (4565, 'Harley-Davidson', 'Ego')
- removed rowid 2233: (4565, 'LiveWire', 'Ego')
- removed rowid 2241: (4565, 'Zero', 'Ego')
- removed rowid 2256: (4566, 'Harley-Davidson', 'Ego')
- removed rowid 2262: (4566, 'LiveWire', 'Ego')
- removed rowid 2270: (4566, 'Zero', 'Ego')
- removed rowid 2285: (4556, 'Harley-Davidson', 'Ego')
- removed rowid 2291: (4556, 'LiveWire', 'Ego')
- removed rowid 2299: (4556, 'Zero', 'Ego')
- removed rowid 2314: (4557, 'Harley-Davidson', 'Ego')
- removed rowid 2320: (4557, 'LiveWire', 'Ego')
- removed rowid 2328: (4557, 'Zero', 'Ego')
- removed rowid 2343: (4558, 'Harley-Davidson', 'Ego')
- removed rowid 2349: (4558, 'LiveWire', 'Ego')
- removed rowid 2357: (4558, 'Zero', 'Ego')
- removed rowid 2372: (4559, 'Harley-Davidson', 'Ego')
- removed rowid 2378: (4559, 'LiveWire', 'Ego')
- removed rowid 2386: (4559, 'Zero', 'Ego')
- removed rowid 2401: (4560, 'Harley-Davidson', 'Ego')
- removed rowid 2407: (4560, 'LiveWire', 'Ego')
- removed rowid 2415: (4560, 'Zero', 'Ego')
- removed rowid 2430: (4561, 'Harley-Davidson', 'Ego')
- removed rowid 2436: (4561, 'LiveWire', 'Ego')
- removed rowid 2444: (4561, 'Zero', 'Ego')
- removed rowid 2457: (4548, 'Harley-Davidson', 'Ego')
- removed rowid 2462: (4548, 'LiveWire', 'Ego')
- removed rowid 2470: (4548, 'Zero', 'Ego')
- removed rowid 2483: (4549, 'Harley-Davidson', 'Ego')
- removed rowid 2488: (4549, 'LiveWire', 'Ego')
- removed rowid 2496: (4549, 'Zero', 'Ego')
- removed rowid 2509: (4550, 'Harley-Davidson', 'Ego')
- removed rowid 2514: (4550, 'LiveWire', 'Ego')
- removed rowid 2522: (4550, 'Zero', 'Ego')
- removed rowid 2535: (4551, 'Harley-Davidson', 'Ego')
- removed rowid 2540: (4551, 'LiveWire', 'Ego')
- removed rowid 2548: (4551, 'Zero', 'Ego')
- removed rowid 2561: (4552, 'Harley-Davidson', 'Ego')
- removed rowid 2566: (4552, 'LiveWire', 'Ego')
- removed rowid 2574: (4552, 'Zero', 'Ego')
- removed rowid 2582: (4541, 'Harley-Davidson', 'Ego')
- removed rowid 2584: (4541, 'LiveWire', 'Ego')
- removed rowid 2586: (4541, 'Zero', 'Ego')
- removed rowid 2593: (4545, 'Harley-Davidson', 'Ego')
- removed rowid 2595: (4545, 'LiveWire', 'Ego')
- removed rowid 2597: (4545, 'Zero', 'Ego')
- removed rowid 2604: (4546, 'Harley-Davidson', 'Ego')
- removed rowid 2606: (4546, 'LiveWire', 'Ego')
- removed rowid 2608: (4546, 'Zero', 'Ego')
- removed rowid 2615: (4547, 'Harley-Davidson', 'Ego')
- removed rowid 2617: (4547, 'LiveWire', 'Ego')
- removed rowid 2619: (4547, 'Zero', 'Ego')
- removed rowid 2629: (4543, 'Harley-Davidson', 'Ego')
- removed rowid 2634: (4543, 'LiveWire', 'Ego')
- removed rowid 2639: (4543, 'Zero', 'Ego')
- removed rowid 2652: (847, 'Harley-Davidson', 'Ego')
- removed rowid 2656: (847, 'LiveWire', 'Ego')
- removed rowid 2660: (847, 'Zero', 'Ego')
- removed rowid 2671: (848, 'Harley-Davidson', 'Ego')
- removed rowid 2675: (848, 'LiveWire', 'Ego')
- removed rowid 2679: (848, 'Zero', 'Ego')
- removed rowid 2690: (849, 'Harley-Davidson', 'Ego')
- removed rowid 2694: (849, 'LiveWire', 'Ego')
- removed rowid 2698: (849, 'Zero', 'Ego')
- removed rowid 2709: (850, 'Harley-Davidson', 'Ego')
- removed rowid 2713: (850, 'LiveWire', 'Ego')
- removed rowid 2717: (850, 'Zero', 'Ego')
- removed rowid 2728: (851, 'Harley-Davidson', 'Ego')
- removed rowid 2732: (851, 'LiveWire', 'Ego')
- removed rowid 2736: (851, 'Zero', 'Ego')
- removed rowid 2747: (852, 'Harley-Davidson', 'Ego')
- removed rowid 2751: (852, 'LiveWire', 'Ego')
- removed rowid 2755: (852, 'Zero', 'Ego')
- removed rowid 2766: (853, 'Harley-Davidson', 'Ego')
- removed rowid 2770: (853, 'LiveWire', 'Ego')
- removed rowid 2774: (853, 'Zero', 'Ego')
- removed rowid 2785: (854, 'Harley-Davidson', 'Ego')
- removed rowid 2789: (854, 'LiveWire', 'Ego')
- removed rowid 2793: (854, 'Zero', 'Ego')
- removed rowid 2804: (855, 'Harley-Davidson', 'Ego')
- removed rowid 2808: (855, 'LiveWire', 'Ego')
- removed rowid 2812: (855, 'Zero', 'Ego')
- removed rowid 2823: (856, 'Harley-Davidson', 'Ego')
- removed rowid 2827: (856, 'LiveWire', 'Ego')
- removed rowid 2831: (856, 'Zero', 'Ego')
## known_issues: +0 added, 1060 changed, 0 removed

### known_issues rowid 1

**row_key**

- before: None
- after:  honda-brake-fluid-contamination-dot-4-hygroscopic-water-absorption

### known_issues rowid 2

**row_key**

- before: None
- after:  kawasaki-caliper-piston-seizure-rebuild-procedure-and-when-to-replace

### known_issues rowid 3

**row_key**

- before: None
- after:  suzuki-brake-pad-selection-sintered-vs-organic-vs-semi-metallic-for

### known_issues rowid 4

**row_key**

- before: None
- after:  kawasaki-brake-rotor-warping-minimum-thickness-measurement-runout

### known_issues rowid 5

**row_key**

- before: None
- after:  honda-master-cylinder-failure-internal-seal-wear-lever-feel

### known_issues rowid 6

**row_key**

- before: None
- after:  yamaha-stainless-steel-braided-brake-line-upgrade-benefits-fitment

### known_issues rowid 7

**row_key**

- before: None
- after:  suzuki-abs-wheel-speed-sensor-contamination-cleaning-gap-setting

### known_issues rowid 8

**row_key**

- before: None
- after:  honda-abs-modulator-bleeding-specialized-procedure-vs-standard

### known_issues rowid 9

**row_key**

- before: None
- after:  yamaha-rear-drum-brake-maintenance-adjustment-shoe-replacement

### known_issues rowid 10

**row_key**

- before: None
- after:  harley-davidson-brake-caliper-mounting-bolt-torque-thread-lock-application

### known_issues rowid 11

**row_key**

- before: None
- after:  honda-cv-carburetor-diaphragm-failure-all-makes-and-models

### known_issues rowid 12

**row_key**

- before: None
- after:  yamaha-pilot-jet-clogging-from-ethanol-fuel-seasonal-storage

### known_issues rowid 13

**row_key**

- before: None
- after:  kawasaki-float-height-maladjustment-fuel-level-too-high-or-too-low

### known_issues rowid 14

**row_key**

- before: None
- after:  suzuki-carburetor-synchronization-uneven-cylinder-fueling

### known_issues rowid 15

**row_key**

- before: None
- after:  honda-enrichment-circuit-choke-failure-cold-start-problems

### known_issues rowid 16

**row_key**

- before: None
- after:  kawasaki-intake-manifold-vacuum-leaks-false-air-causing-lean

### known_issues rowid 17

**row_key**

- before: None
- after:  suzuki-pilot-screw-adjustment-idle-mixture-fine-tuning

### known_issues rowid 18

**row_key**

- before: None
- after:  honda-float-bowl-overflow-and-fuel-leak-fire-hazard

### known_issues rowid 19

**row_key**

- before: None
- after:  kawasaki-main-jet-sizing-for-aftermarket-exhaust-and-intake-rejetting

### known_issues rowid 20

**row_key**

- before: None
- after:  honda-carb-to-throttle-body-conversion-considerations-efi-retrofit

### known_issues rowid 21

**row_key**

- before: None
- after:  honda-stator-winding-failure-insulation-breakdown-causing-shorted

### known_issues rowid 22

**row_key**

- before: None
- after:  kawasaki-regulator-rectifier-failure-shunt-type-vs-mosfet-comparison

### known_issues rowid 23

**row_key**

- before: None
- after:  honda-stator-connector-melting-fire-risk-and-solder-bypass

### known_issues rowid 24

**row_key**

- before: None
- after:  suzuki-rotor-flywheel-magnet-degradation-loss-of-charging-output

### known_issues rowid 25

**row_key**

- before: None
- after:  kawasaki-battery-selection-and-compatibility-agm-vs-lithium-vs

### known_issues rowid 26

**row_key**

- before: None
- after:  suzuki-parasitic-draw-testing-systematic-fuse-pull-diagnosis-for

### known_issues rowid 27

**row_key**

- before: None
- after:  honda-charging-system-voltage-test-the-universal-3-step-diagnostic

### known_issues rowid 28

**row_key**

- before: None
- after:  kawasaki-ground-circuit-resistance-voltage-drop-testing-for-corroded

### known_issues rowid 29

**row_key**

- before: None
- after:  suzuki-accessory-load-management-calculating-electrical-draw-vs

### known_issues rowid 30

**row_key**

- before: None
- after:  harley-davidson-alternator-belt-harley-and-direct-drive-charging

### known_issues rowid 31

**row_key**

- before: None
- after:  honda-thermostat-failure-stuck-closed-causing-overheating-vs-stuck

### known_issues rowid 32

**row_key**

- before: None
- after:  suzuki-radiator-fan-switch-and-relay-failure-fan-not-activating-in

### known_issues rowid 33

**row_key**

- before: None
- after:  kawasaki-coolant-degradation-acidic-coolant-corroding-water-pump

### known_issues rowid 34

**row_key**

- before: None
- after:  honda-water-pump-seal-failure-weep-hole-diagnosis-and-bearing

### known_issues rowid 35

**row_key**

- before: None
- after:  suzuki-radiator-core-blockage-external-debris-and-internal

### known_issues rowid 36

**row_key**

- before: None
- after:  harley-davidson-air-cooled-engine-heat-management-oil-selection-oil-cooler

### known_issues rowid 37

**row_key**

- before: None
- after:  kawasaki-coolant-hose-failure-hardening-cracking-and-silicone-hose

### known_issues rowid 38

**row_key**

- before: None
- after:  yamaha-head-gasket-failure-coolant-in-oil-diagnosis-and-combustion

### known_issues rowid 39

**row_key**

- before: None
- after:  kawasaki-radiator-cap-pressure-rating-failure-boil-over-prevention

### known_issues rowid 40

**row_key**

- before: None
- after:  yamaha-track-and-racing-coolant-requirements-engine-ice-water

### known_issues rowid 41

**row_key**

- before: None
- after:  honda-chain-stretch-measurement-and-replacement-criteria-all-chain

### known_issues rowid 42

**row_key**

- before: None
- after:  kawasaki-sprocket-wear-patterns-hooked-teeth-countershaft-vs-rear

### known_issues rowid 43

**row_key**

- before: None
- after:  suzuki-chain-lubrication-comparison-wax-wet-and-auto-oiler-systems

### known_issues rowid 44

**row_key**

- before: None
- after:  harley-davidson-belt-drive-maintenance-tension-inspection-and-replacement-on

### known_issues rowid 45

**row_key**

- before: None
- after:  honda-shaft-drive-service-hypoid-gear-oil-seal-inspection-and

### known_issues rowid 46

**row_key**

- before: None
- after:  kawasaki-clutch-drag-and-basket-notching-wet-clutch-diagnosis-across

### known_issues rowid 47

**row_key**

- before: None
- after:  suzuki-clutch-cable-adjustment-and-hydraulic-clutch-bleeding

### known_issues rowid 48

**row_key**

- before: None
- after:  yamaha-transmission-shifting-issues-false-neutral-hard-shifting-and

### known_issues rowid 49

**row_key**

- before: None
- after:  honda-countershaft-seal-replacement-the-forgotten-maintenance-item

### known_issues rowid 50

**row_key**

- before: None
- after:  yamaha-final-drive-alignment-chain-belt-and-shaft-drive-alignment

### known_issues rowid 51

**row_key**

- before: None
- after:  honda-fuel-pump-failure-and-testing-all-efi-motorcycles

### known_issues rowid 52

**row_key**

- before: None
- after:  kawasaki-throttle-position-sensor-tps-calibration-and-failure-erratic

### known_issues rowid 53

**row_key**

- before: None
- after:  suzuki-intake-air-pressure-iap-map-sensor-failure-incorrect-fuel

### known_issues rowid 54

**row_key**

- before: None
- after:  yamaha-o2-sensor-failure-and-elimination-closed-loop-fueling-issues

### known_issues rowid 55

**row_key**

- before: None
- after:  honda-engine-coolant-temperature-ect-sensor-failure-cold-start

### known_issues rowid 56

**row_key**

- before: None
- after:  kawasaki-fuel-injector-clogging-and-cleaning-spray-pattern

### known_issues rowid 57

**row_key**

- before: None
- after:  yamaha-idle-speed-control-isc-iacv-valve-carbon-buildup-erratic-or

### known_issues rowid 58

**row_key**

- before: None
- after:  suzuki-throttle-body-cleaning-and-synchronization-multi-cylinder

### known_issues rowid 59

**row_key**

- before: None
- after:  harley-davidson-fuel-pressure-regulator-failure-fuel-rail-pressure-out-of

### known_issues rowid 60

**row_key**

- before: None
- after:  harley-davidson-ecu-ecm-reset-and-adaptation-relearn-post-service-idle-and

### known_issues rowid 61

**row_key**

- before: None
- after:  honda-spark-plug-fouling-and-heat-range-selection-all-makes-and

### known_issues rowid 62

**row_key**

- before: None
- after:  kawasaki-ignition-coil-failure-primary-and-secondary-winding-testing

### known_issues rowid 63

**row_key**

- before: None
- after:  suzuki-cdi-ecu-ignition-module-failure-testing-without-an

### known_issues rowid 64

**row_key**

- before: None
- after:  honda-pickup-coil-ckp-sensor-resistance-testing-and-air-gap

### known_issues rowid 65

**row_key**

- before: None
- after:  kawasaki-spark-plug-wire-and-cap-resistance-ngk-standards-and-testing

### known_issues rowid 66

**row_key**

- before: None
- after:  yamaha-points-ignition-maintenance-and-electronic-conversion

### known_issues rowid 67

**row_key**

- before: None
- after:  harley-davidson-ignition-timing-static-and-dynamic-verification-across-all

### known_issues rowid 68

**row_key**

- before: None
- after:  suzuki-kill-switch-circuit-intermittent-open-creating-random-no

### known_issues rowid 69

**row_key**

- before: None
- after:  kawasaki-misfires-under-load-lean-condition-versus-ignition-failure

### known_issues rowid 70

**row_key**

- before: None
- after:  suzuki-coil-on-plug-cop-system-diagnostics-modern-motorcycle

### known_issues rowid 71

**row_key**

- before: None
- after:  honda-starter-relay-contact-corrosion-clicking-but-no-crank-across

### known_issues rowid 72

**row_key**

- before: None
- after:  harley-davidson-starter-motor-brush-wear-and-commutator-degradation-slow-or

### known_issues rowid 73

**row_key**

- before: None
- after:  kawasaki-starter-clutch-sprag-one-way-bearing-failure-starter-spins

### known_issues rowid 74

**row_key**

- before: None
- after:  suzuki-clutch-safety-switch-failure-bike-won-t-start-even-with

### known_issues rowid 75

**row_key**

- before: None
- after:  yamaha-kickstand-safety-switch-corrosion-no-start-from-weather

### known_issues rowid 76

**row_key**

- before: None
- after:  honda-kill-switch-and-handlebar-control-switch-failure-no-power-to

### known_issues rowid 77

**row_key**

- before: None
- after:  kawasaki-battery-cable-voltage-drop-terminal-corrosion-causing-slow

### known_issues rowid 78

**row_key**

- before: None
- after:  suzuki-tip-over-sensor-bank-angle-sensor-preventing-start-after-a

### known_issues rowid 79

**row_key**

- before: None
- after:  honda-neutral-switch-failure-false-neutral-detection-preventing-in

### known_issues rowid 80

**row_key**

- before: None
- after:  harley-davidson-compression-release-and-high-compression-starting-issues-big

### known_issues rowid 81

**row_key**

- before: None
- after:  harley-davidson-stator-failure-chronic-undercharging

### known_issues rowid 82

**row_key**

- before: None
- after:  harley-davidson-cam-chain-tensioner-failure-twin-cam-tick-of-death

### known_issues rowid 83

**row_key**

- before: None
- after:  harley-davidson-compensator-sprocket-noise-primary-clunk-on-startup

### known_issues rowid 84

**row_key**

- before: None
- after:  harley-davidson-intake-manifold-air-leak-lean-running-and-backfire

### known_issues rowid 85

**row_key**

- before: None
- after:  harley-davidson-voltage-regulator-failure-overcharging-or-no-charge

### known_issues rowid 86

**row_key**

- before: None
- after:  harley-davidson-sportster-primary-chain-tensioner-wear

### known_issues rowid 87

**row_key**

- before: None
- after:  harley-davidson-turn-signal-module-failure-erratic-blinkers

### known_issues rowid 88

**row_key**

- before: None
- after:  harley-davidson-exhaust-header-leak-ticking-when-cold

### known_issues rowid 89

**row_key**

- before: None
- after:  harley-davidson-fuel-injector-clogging-lean-stumble-off-idle

### known_issues rowid 90

**row_key**

- before: None
- after:  harley-davidson-rear-brake-switch-failure-brake-light-always-on-or-never-on

### known_issues rowid 91

**row_key**

- before: None
- after:  harley-davidson-compensator-sprocket-noise-and-failure-twin-cam-and

### known_issues rowid 92

**row_key**

- before: None
- after:  harley-davidson-intake-manifold-seal-leak-all-v-twins-with-shared-manifold

### known_issues rowid 93

**row_key**

- before: None
- after:  harley-davidson-heat-soak-and-hot-restart-issues-air-cooled-v-twins

### known_issues rowid 94

**row_key**

- before: None
- after:  harley-davidson-primary-oil-fluid-leak-derby-cover-and-primary-gasket

### known_issues rowid 95

**row_key**

- before: None
- after:  harley-davidson-clutch-adjustment-and-clutch-pack-wear-cable-and-hydraulic

### known_issues rowid 96

**row_key**

- before: None
- after:  harley-davidson-rear-suspension-sag-and-shock-degradation

### known_issues rowid 97

**row_key**

- before: None
- after:  harley-davidson-wheel-bearing-failure-front-and-rear

### known_issues rowid 98

**row_key**

- before: None
- after:  harley-davidson-exhaust-leak-at-head-pipe-flange-all-models

### known_issues rowid 99

**row_key**

- before: None
- after:  harley-davidson-tire-wear-pattern-diagnosis-cupping-feathering-flat-spotting

### known_issues rowid 100

**row_key**

- before: None
- after:  harley-davidson-fuel-quality-and-ethanol-damage-carb-and-efi-eras

### known_issues rowid 101

**row_key**

- before: None
- after:  harley-davidson-voltage-regulator-rectifier-failure-all-eras

### known_issues rowid 102

**row_key**

- before: None
- after:  harley-davidson-stator-failure-burn-and-short

### known_issues rowid 103

**row_key**

- before: None
- after:  harley-davidson-starter-solenoid-failure-clicks-but-won-t-crank

### known_issues rowid 104

**row_key**

- before: None
- after:  harley-davidson-ground-cable-corrosion-mysterious-electrical-gremlins

### known_issues rowid 105

**row_key**

- before: None
- after:  harley-davidson-can-bus-communication-fault-2011-models

### known_issues rowid 106

**row_key**

- before: None
- after:  harley-davidson-ignition-switch-failure-intermittent-power-loss

### known_issues rowid 107

**row_key**

- before: None
- after:  harley-davidson-turn-signal-module-tsm-tssm-malfunction

### known_issues rowid 108

**row_key**

- before: None
- after:  harley-davidson-wiring-harness-chafing-heat-and-vibration-damage

### known_issues rowid 109

**row_key**

- before: None
- after:  harley-davidson-battery-type-mismatch-wrong-charger-or-wrong-battery

### known_issues rowid 110

**row_key**

- before: None
- after:  harley-davidson-headlight-and-lighting-circuit-overload

### known_issues rowid 111

**row_key**

- before: None
- after:  harley-davidson-base-gasket-oil-leak-chronic-weeping

### known_issues rowid 112

**row_key**

- before: None
- after:  harley-davidson-starter-clutch-failure-grinding-on-start

### known_issues rowid 113

**row_key**

- before: None
- after:  harley-davidson-rocker-box-oil-leak-dripping-on-jugs

### known_issues rowid 114

**row_key**

- before: None
- after:  harley-davidson-cam-cover-leak-oil-pooling-behind-cylinders

### known_issues rowid 115

**row_key**

- before: None
- after:  harley-davidson-cv-carburetor-slide-diaphragm-tear-hesitation-and-bog

### known_issues rowid 116

**row_key**

- before: None
- after:  harley-davidson-weak-charging-old-style-stator-and-regulator

### known_issues rowid 117

**row_key**

- before: None
- after:  harley-davidson-ignition-module-failure-intermittent-no-start-or-misfire

### known_issues rowid 118

**row_key**

- before: None
- after:  harley-davidson-oil-pump-check-valve-failure-wet-sumping

### known_issues rowid 119

**row_key**

- before: None
- after:  harley-davidson-pushrod-tube-o-ring-leaks-oil-at-the-head-cylinder-junction

### known_issues rowid 120

**row_key**

- before: None
- after:  harley-davidson-voltage-regulator-overheating-melted-connector

### known_issues rowid 121

**row_key**

- before: None
- after:  harley-davidson-oil-sumping-at-oil-cooler-m8-touring-models

### known_issues rowid 122

**row_key**

- before: None
- after:  harley-davidson-exhaust-header-heat-discoloration-and-warping

### known_issues rowid 123

**row_key**

- before: None
- after:  harley-davidson-compensator-noise-still-present-on-early-m8

### known_issues rowid 124

**row_key**

- before: None
- after:  harley-davidson-infotainment-system-freezing-rebooting-boom-box-gts

### known_issues rowid 125

**row_key**

- before: None
- after:  harley-davidson-intake-runner-valve-carbon-buildup-causing-rough-idle

### known_issues rowid 126

**row_key**

- before: None
- after:  harley-davidson-primary-chain-adjuster-shoe-premature-wear-on-softail

### known_issues rowid 127

**row_key**

- before: None
- after:  harley-davidson-throttle-by-wire-calibration-cruise-control-surge

### known_issues rowid 128

**row_key**

- before: None
- after:  harley-davidson-rear-suspension-preload-adjustment-failure-touring

### known_issues rowid 129

**row_key**

- before: None
- after:  harley-davidson-oil-pressure-sensor-failure-false-low-oil-pressure-warning

### known_issues rowid 130

**row_key**

- before: None
- after:  harley-davidson-rider-passenger-floorboard-vibration-m8-touring

### known_issues rowid 131

**row_key**

- before: None
- after:  harley-davidson-tft-instrument-cluster-freezing-and-rebooting

### known_issues rowid 132

**row_key**

- before: None
- after:  harley-davidson-ride-by-wire-throttle-hesitation-and-surging

### known_issues rowid 133

**row_key**

- before: None
- after:  harley-davidson-coolant-leak-at-water-pump-gasket

### known_issues rowid 134

**row_key**

- before: None
- after:  harley-davidson-oil-consumption-higher-than-expected-break-in-and-beyond

### known_issues rowid 135

**row_key**

- before: None
- after:  harley-davidson-side-stand-sensor-intermittent-bike-won-t-start-or-stalls

### known_issues rowid 136

**row_key**

- before: None
- after:  harley-davidson-cornering-abs-traction-control-false-intervention

### known_issues rowid 137

**row_key**

- before: None
- after:  harley-davidson-exhaust-heat-shield-rattle-and-discoloration

### known_issues rowid 138

**row_key**

- before: None
- after:  harley-davidson-chain-final-drive-maintenance-not-a-harley-tradition

### known_issues rowid 139

**row_key**

- before: None
- after:  harley-davidson-battery-drain-parasitic-draw-from-electronics

### known_issues rowid 140

**row_key**

- before: None
- after:  harley-davidson-mid-mount-controls-ergonomic-issues-sportster-s-specific

### known_issues rowid 141

**row_key**

- before: None
- after:  harley-davidson-shared-oil-system-engine-transmission-primary-use-same-oil

### known_issues rowid 142

**row_key**

- before: None
- after:  harley-davidson-clutch-cable-adjustment-heavy-pull-and-poor-engagement

### known_issues rowid 143

**row_key**

- before: None
- after:  harley-davidson-starter-motor-brushes-worn-slow-no-crank

### known_issues rowid 144

**row_key**

- before: None
- after:  harley-davidson-carb-enrichener-choke-circuit-plugged-hard-cold-start

### known_issues rowid 145

**row_key**

- before: None
- after:  harley-davidson-regulator-rectifier-failure-under-seat-heat-trap

### known_issues rowid 146

**row_key**

- before: None
- after:  harley-davidson-speedometer-drive-gear-failure-no-speedo-reading

### known_issues rowid 147

**row_key**

- before: None
- after:  harley-davidson-rear-axle-adjustment-chain-alignment-and-tire-wear

### known_issues rowid 148

**row_key**

- before: None
- after:  harley-davidson-rocker-box-oil-leak-dripping-on-883-and-1200

### known_issues rowid 149

**row_key**

- before: None
- after:  harley-davidson-kickstand-switch-bike-dies-when-put-in-gear

### known_issues rowid 150

**row_key**

- before: None
- after:  harley-davidson-exhaust-crossover-pipe-crack-2-into-1-systems

### known_issues rowid 151

**row_key**

- before: None
- after:  harley-davidson-fuel-pump-failure-in-tank-design

### known_issues rowid 152

**row_key**

- before: None
- after:  harley-davidson-engine-mount-rubber-isolator-deterioration

### known_issues rowid 153

**row_key**

- before: None
- after:  harley-davidson-ecm-efi-lean-stumble-decel-pop-and-off-idle-hesitation

### known_issues rowid 154

**row_key**

- before: None
- after:  harley-davidson-stator-connector-melt-sportster-specific

### known_issues rowid 155

**row_key**

- before: None
- after:  harley-davidson-intake-manifold-leak-lean-codes-and-surging

### known_issues rowid 156

**row_key**

- before: None
- after:  harley-davidson-rear-brake-caliper-piston-seizure

### known_issues rowid 157

**row_key**

- before: None
- after:  harley-davidson-turn-signal-auto-cancel-not-working-tssm-issue

### known_issues rowid 158

**row_key**

- before: None
- after:  harley-davidson-primary-chain-noise-shared-oil-makes-it-worse

### known_issues rowid 159

**row_key**

- before: None
- after:  harley-davidson-handlebar-switch-housing-failure-intermittent-controls

### known_issues rowid 160

**row_key**

- before: None
- after:  harley-davidson-fork-seal-leak-oil-on-fork-tubes

### known_issues rowid 161

**row_key**

- before: None
- after:  harley-davidson-cam-chain-tensioner-shoe-failure-tick-of-death

### known_issues rowid 162

**row_key**

- before: None
- after:  harley-davidson-compensator-sprocket-rattle-primary-clunk

### known_issues rowid 163

**row_key**

- before: None
- after:  harley-davidson-oil-sumping-crankcase-oil-accumulation

### known_issues rowid 164

**row_key**

- before: None
- after:  harley-davidson-intake-manifold-leak-lean-surge-at-idle

### known_issues rowid 165

**row_key**

- before: None
- after:  harley-davidson-stator-failure-charging-system-breakdown

### known_issues rowid 166

**row_key**

- before: None
- after:  harley-davidson-inner-cam-bearing-failure-catastrophic-if-ignored

### known_issues rowid 167

**row_key**

- before: None
- after:  harley-davidson-efi-tps-calibration-drift-surging-and-poor-throttle-response

### known_issues rowid 168

**row_key**

- before: None
- after:  harley-davidson-primary-chain-tensioner-wear-chain-slap-at-idle

### known_issues rowid 169

**row_key**

- before: None
- after:  harley-davidson-exhaust-header-bolt-seizure-broken-bolt-in-head

### known_issues rowid 170

**row_key**

- before: None
- after:  harley-davidson-rear-cylinder-overheating-heat-management-issues

### known_issues rowid 171

**row_key**

- before: None
- after:  harley-davidson-twin-cam-96-cam-chain-tensioner-improved-but-not-eliminated

### known_issues rowid 172

**row_key**

- before: None
- after:  harley-davidson-abs-module-failure-abs-light-on-intermittent-abs-activation

### known_issues rowid 173

**row_key**

- before: None
- after:  harley-davidson-ecm-tuning-factory-lean-condition-and-decel-popping

### known_issues rowid 174

**row_key**

- before: None
- after:  harley-davidson-6-speed-transmission-hard-shift-into-5th-or-false-neutral

### known_issues rowid 175

**row_key**

- before: None
- after:  harley-davidson-stator-failure-same-harley-story-different-decade

### known_issues rowid 176

**row_key**

- before: None
- after:  harley-davidson-throttle-by-wire-tbw-throttle-body-failure-2008-models

### known_issues rowid 177

**row_key**

- before: None
- after:  harley-davidson-compensator-noise-worse-on-103-110-cvo-models

### known_issues rowid 178

**row_key**

- before: None
- after:  harley-davidson-oil-cooler-lines-leaking-touring-models

### known_issues rowid 179

**row_key**

- before: None
- after:  harley-davidson-wheel-bearing-failure-touring-and-dyna

### known_issues rowid 180

**row_key**

- before: None
- after:  harley-davidson-fuel-pump-failure-no-start-no-prime-sound

### known_issues rowid 181

**row_key**

- before: None
- after:  harley-davidson-coolant-system-failure-radiator-fan-relay-and-thermostat

### known_issues rowid 182

**row_key**

- before: None
- after:  harley-davidson-hydraulic-clutch-master-cylinder-failure

### known_issues rowid 183

**row_key**

- before: None
- after:  harley-davidson-underseat-fuel-cell-delamination

### known_issues rowid 184

**row_key**

- before: None
- after:  harley-davidson-exhaust-header-cracking-heat-stress-on-front-cylinder

### known_issues rowid 185

**row_key**

- before: None
- after:  harley-davidson-alternator-rotor-nut-backing-off-charging-failure

### known_issues rowid 186

**row_key**

- before: None
- after:  harley-davidson-perimeter-frame-stress-cracks-headstock-and-swingarm-pivot

### known_issues rowid 187

**row_key**

- before: None
- after:  harley-davidson-ecu-mapping-runs-rich-from-factory-o2-sensor-fouling

### known_issues rowid 188

**row_key**

- before: None
- after:  harley-davidson-drive-belt-tensioner-bearing-failure

### known_issues rowid 189

**row_key**

- before: None
- after:  harley-davidson-starter-motor-and-starter-clutch-failure-high-compression

### known_issues rowid 190

**row_key**

- before: None
- after:  harley-davidson-rear-shock-preload-adjuster-seizure-and-linkage-wear

### known_issues rowid 191

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-high-output-stator-variant

### known_issues rowid 192

**row_key**

- before: None
- after:  honda-hstc-honda-selectable-torque-control-false-intervention

### known_issues rowid 193

**row_key**

- before: None
- after:  honda-cam-chain-tensioner-liter-bike-version

### known_issues rowid 194

**row_key**

- before: None
- after:  honda-hesd-failure-same-as-cbr600rr-but-higher-forces

### known_issues rowid 195

**row_key**

- before: None
- after:  honda-quickshifter-malfunction-2017-sp-models

### known_issues rowid 196

**row_key**

- before: None
- after:  honda-exhaust-valve-servo-pair-system-failure

### known_issues rowid 197

**row_key**

- before: None
- after:  honda-coolant-leak-at-thermostat-housing-and-water-pump-high-heat

### known_issues rowid 198

**row_key**

- before: None
- after:  honda-rear-shock-linkage-and-shock-absorber-degradation

### known_issues rowid 199

**row_key**

- before: None
- after:  honda-brake-master-cylinder-and-caliper-piston-sticking

### known_issues rowid 200

**row_key**

- before: None
- after:  honda-rr-r-2020-wing-damage-and-aero-part-availability

### known_issues rowid 201

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-same-honda-disease

### known_issues rowid 202

**row_key**

- before: None
- after:  honda-carburetor-issues-f2-f3-f4-specific

### known_issues rowid 203

**row_key**

- before: None
- after:  honda-cam-chain-tensioner-cct-rattle-all-f-series

### known_issues rowid 204

**row_key**

- before: None
- after:  honda-f4i-fuel-injector-clogging-and-lean-stumble

### known_issues rowid 205

**row_key**

- before: None
- after:  honda-ignition-coil-and-spark-plug-cap-failure

### known_issues rowid 206

**row_key**

- before: None
- after:  honda-clutch-cable-fraying-and-sudden-failure-cable-clutch-models

### known_issues rowid 207

**row_key**

- before: None
- after:  honda-radiator-fan-failure-and-overheating-in-traffic

### known_issues rowid 208

**row_key**

- before: None
- after:  honda-chain-and-sprocket-wear-high-mileage-commuters

### known_issues rowid 209

**row_key**

- before: None
- after:  honda-speedometer-cable-and-gear-failure-f2-f3

### known_issues rowid 210

**row_key**

- before: None
- after:  honda-exhaust-header-rust-and-collector-gasket-leak

### known_issues rowid 211

**row_key**

- before: None
- after:  honda-hesd-honda-electronic-steering-damper-failure-2007

### known_issues rowid 212

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-improved-but-still-happens

### known_issues rowid 213

**row_key**

- before: None
- after:  honda-c-abs-unit-failure-2009-abs-models

### known_issues rowid 214

**row_key**

- before: None
- after:  honda-cam-chain-tensioner-noise-all-years

### known_issues rowid 215

**row_key**

- before: None
- after:  honda-fuel-pump-failure-low-fuel-overheating

### known_issues rowid 216

**row_key**

- before: None
- after:  honda-valve-clearance-tightening-high-mileage-engines

### known_issues rowid 217

**row_key**

- before: None
- after:  honda-instrument-cluster-lcd-fade-and-pixel-loss

### known_issues rowid 218

**row_key**

- before: None
- after:  honda-fork-cartridge-degradation-and-oil-breakdown

### known_issues rowid 219

**row_key**

- before: None
- after:  honda-stator-failure-on-high-rpm-track-use

### known_issues rowid 220

**row_key**

- before: None
- after:  honda-subframe-cracking-crash-damage-and-rear-stand-use

### known_issues rowid 221

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-overcharging-or-dead-battery

### known_issues rowid 222

**row_key**

- before: None
- after:  honda-cam-chain-tensioner-cct-failure-top-end-rattle

### known_issues rowid 223

**row_key**

- before: None
- after:  honda-hiss-immobilizer-lockout-929rr-and-954rr

### known_issues rowid 224

**row_key**

- before: None
- after:  honda-carburetor-synchronization-and-vacuum-leak-900rr-1992-1999

### known_issues rowid 225

**row_key**

- before: None
- after:  honda-fork-seal-leak-and-suspension-sag-age-related

### known_issues rowid 226

**row_key**

- before: None
- after:  honda-starter-clutch-sprag-clutch-failure

### known_issues rowid 227

**row_key**

- before: None
- after:  honda-coolant-leak-at-water-pump-and-thermostat-housing

### known_issues rowid 228

**row_key**

- before: None
- after:  honda-pgm-fi-fuel-injection-issues-929rr-and-954rr

### known_issues rowid 229

**row_key**

- before: None
- after:  honda-rear-shock-linkage-bearing-wear-rising-rate-suspension

### known_issues rowid 230

**row_key**

- before: None
- after:  honda-fairing-bolt-corrosion-and-cracked-fairings

### known_issues rowid 231

**row_key**

- before: None
- after:  honda-cam-chain-tensioner-cct-the-honda-inline-4-universal

### known_issues rowid 232

**row_key**

- before: None
- after:  honda-starter-clutch-sprag-one-way-clutch-failure-all-honda

### known_issues rowid 233

**row_key**

- before: None
- after:  honda-coolant-hose-deterioration-and-clamp-failure-all-liquid

### known_issues rowid 234

**row_key**

- before: None
- after:  honda-valve-clearance-tightening-all-honda-4-stroke-engines

### known_issues rowid 235

**row_key**

- before: None
- after:  honda-chain-and-sprocket-maintenance-the-overlooked-service

### known_issues rowid 236

**row_key**

- before: None
- after:  honda-brake-fluid-degradation-universal-honda-concern

### known_issues rowid 237

**row_key**

- before: None
- after:  honda-throttle-cable-and-throttle-body-maintenance

### known_issues rowid 238

**row_key**

- before: None
- after:  honda-fork-seal-and-suspension-service-neglect

### known_issues rowid 239

**row_key**

- before: None
- after:  honda-air-filter-neglect-and-airbox-service

### known_issues rowid 240

**row_key**

- before: None
- after:  honda-tire-age-and-dry-rot-time-based-replacement

### known_issues rowid 241

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-shadow-and-vtx

### known_issues rowid 242

**row_key**

- before: None
- after:  honda-shaft-drive-final-gear-oil-leak-shaft-drive-models

### known_issues rowid 243

**row_key**

- before: None
- after:  honda-carburetor-pilot-circuit-clogging-shadow-600-750-1100

### known_issues rowid 244

**row_key**

- before: None
- after:  honda-vtx-1800-starter-motor-and-starter-clutch-failure

### known_issues rowid 245

**row_key**

- before: None
- after:  honda-fuel-pump-failure-efi-shadow-and-vtx-models

### known_issues rowid 246

**row_key**

- before: None
- after:  honda-hydraulic-valve-lifter-noise-vtx-1300

### known_issues rowid 247

**row_key**

- before: None
- after:  honda-clutch-drag-and-hard-neutral-finding

### known_issues rowid 248

**row_key**

- before: None
- after:  honda-exhaust-crossover-pipe-rust-through

### known_issues rowid 249

**row_key**

- before: None
- after:  honda-seat-height-and-ergonomic-issues-shorter-riders

### known_issues rowid 250

**row_key**

- before: None
- after:  honda-speedometer-and-tachometer-cable-failure-older-shadow-models

### known_issues rowid 251

**row_key**

- before: None
- after:  honda-xr650l-carburetor-jetting-lean-from-factory

### known_issues rowid 252

**row_key**

- before: None
- after:  honda-xr650l-oil-consumption-and-valve-adjustment

### known_issues rowid 253

**row_key**

- before: None
- after:  honda-crf250l-300l-lack-of-power-designed-limitations

### known_issues rowid 254

**row_key**

- before: None
- after:  honda-africa-twin-dct-off-road-behavior-same-honda-dct-issues

### known_issues rowid 255

**row_key**

- before: None
- after:  honda-africa-twin-coolant-system-and-radiator-protection

### known_issues rowid 256

**row_key**

- before: None
- after:  honda-off-road-electrical-damage-water-fording-and-mud

### known_issues rowid 257

**row_key**

- before: None
- after:  honda-chain-and-sprocket-accelerated-wear-off-road-dirt-and-mud

### known_issues rowid 258

**row_key**

- before: None
- after:  honda-crf250l-300l-clutch-basket-rattle-and-chatter

### known_issues rowid 259

**row_key**

- before: None
- after:  honda-africa-twin-crash-protection-and-adventure-prep

### known_issues rowid 260

**row_key**

- before: None
- after:  honda-xr650l-stator-and-charging-system-weakness

### known_issues rowid 261

**row_key**

- before: None
- after:  honda-pgm-fi-self-diagnostic-blink-codes-reading-without-a-dealer

### known_issues rowid 262

**row_key**

- before: None
- after:  honda-hiss-immobilizer-system-all-efi-honda-models

### known_issues rowid 263

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-the-universal-honda-problem

### known_issues rowid 264

**row_key**

- before: None
- after:  honda-stator-failure-diagnosis-and-replacement-all-honda-models

### known_issues rowid 265

**row_key**

- before: None
- after:  honda-starter-relay-and-starter-motor-diagnosis

### known_issues rowid 266

**row_key**

- before: None
- after:  honda-fi-fuel-injection-light-on-sensor-and-actuator-faults

### known_issues rowid 267

**row_key**

- before: None
- after:  honda-ground-connection-corrosion-hidden-electrical-gremlin

### known_issues rowid 268

**row_key**

- before: None
- after:  honda-headlight-and-turn-signal-bulb-replacement-sealed-beam-vs-h4

### known_issues rowid 269

**row_key**

- before: None
- after:  honda-fuse-diagnosis-and-fuse-box-corrosion

### known_issues rowid 270

**row_key**

- before: None
- after:  honda-charging-system-preventive-testing-annual-check-protocol

### known_issues rowid 271

**row_key**

- before: None
- after:  honda-carburetor-issues-rebel-250-1985-2016

### known_issues rowid 272

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-rebel-250-and-300-500

### known_issues rowid 273

**row_key**

- before: None
- after:  honda-rebel-1100-dct-transmission-jerky-low-speed-behavior

### known_issues rowid 274

**row_key**

- before: None
- after:  honda-rebel-300-500-chain-tension-and-adjustment-beginner-neglect

### known_issues rowid 275

**row_key**

- before: None
- after:  honda-battery-drain-from-sitting-rebel-250-garage-queens

### known_issues rowid 276

**row_key**

- before: None
- after:  honda-turn-signal-relay-and-led-conversion-issues

### known_issues rowid 277

**row_key**

- before: None
- after:  honda-rebel-1100-oil-cooler-and-cooling-system-africa-twin-engine

### known_issues rowid 278

**row_key**

- before: None
- after:  honda-rear-drum-brake-adjustment-rebel-250

### known_issues rowid 279

**row_key**

- before: None
- after:  honda-headlight-bulb-burnout-and-dim-lighting-rebel-250

### known_issues rowid 280

**row_key**

- before: None
- after:  honda-throttle-cable-and-throttle-body-icing-rebel-300-500-cold

### known_issues rowid 281

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-shared-sport-bike-weakness

### known_issues rowid 282

**row_key**

- before: None
- after:  honda-cam-chain-tensioner-noise-inline-4-models

### known_issues rowid 283

**row_key**

- before: None
- after:  honda-cb1000r-throttle-by-wire-hesitation-and-surge

### known_issues rowid 284

**row_key**

- before: None
- after:  honda-carburetor-issues-cb750-nighthawk-1991-2003

### known_issues rowid 285

**row_key**

- before: None
- after:  honda-chain-and-sprocket-wear-commuter-use-pattern

### known_issues rowid 286

**row_key**

- before: None
- after:  honda-handlebar-vibration-engine-to-chassis-transfer

### known_issues rowid 287

**row_key**

- before: None
- after:  honda-fuel-tank-rust-older-cb750-and-hornet-models

### known_issues rowid 288

**row_key**

- before: None
- after:  honda-headlight-aim-and-visibility-naked-bike-riding-position

### known_issues rowid 289

**row_key**

- before: None
- after:  honda-rear-shock-degradation-standard-bike-loads

### known_issues rowid 290

**row_key**

- before: None
- after:  honda-mirror-vibration-and-blind-spots-naked-bike-aerodynamics

### known_issues rowid 291

**row_key**

- before: None
- after:  honda-vtec-crossover-surge-vfr800-2002-2017

### known_issues rowid 292

**row_key**

- before: None
- after:  honda-regulator-rectifier-failure-v4-heat-generation

### known_issues rowid 293

**row_key**

- before: None
- after:  honda-rc51-fuel-injection-synchronization-and-tps-calibration

### known_issues rowid 294

**row_key**

- before: None
- after:  honda-gear-driven-cam-noise-v4-characteristic-sound

### known_issues rowid 295

**row_key**

- before: None
- after:  honda-vfr800-linked-braking-system-cbs-c-abs-issues

### known_issues rowid 296

**row_key**

- before: None
- after:  honda-rc51-rear-cylinder-overheating-in-traffic

### known_issues rowid 297

**row_key**

- before: None
- after:  honda-vfr1200f-shaft-drive-maintenance-and-dct-specifics

### known_issues rowid 298

**row_key**

- before: None
- after:  honda-fuel-pump-relay-failure-vfr-and-rc51

### known_issues rowid 299

**row_key**

- before: None
- after:  honda-exhaust-header-collector-gasket-leak-v4-thermal-stress

### known_issues rowid 300

**row_key**

- before: None
- after:  honda-windscreen-vibration-and-fairing-buzz-sport-touring-miles

### known_issues rowid 301

**row_key**

- before: None
- after:  honda-points-ignition-failure-and-conversion-pre-1980-models

### known_issues rowid 302

**row_key**

- before: None
- after:  honda-carburetor-bank-rebuild-4-carb-inline-4-service

### known_issues rowid 303

**row_key**

- before: None
- after:  honda-charging-system-failure-early-honda-generators-and-stators

### known_issues rowid 304

**row_key**

- before: None
- after:  honda-cam-chain-and-tensioner-wear-high-mileage-sohc-engines

### known_issues rowid 305

**row_key**

- before: None
- after:  honda-fuel-petcock-vacuum-diaphragm-failure

### known_issues rowid 306

**row_key**

- before: None
- after:  honda-brake-master-cylinder-and-caliper-rebuild-aging-hydraulics

### known_issues rowid 307

**row_key**

- before: None
- after:  honda-exhaust-rust-through-and-header-replacement

### known_issues rowid 308

**row_key**

- before: None
- after:  honda-fork-seal-leak-and-fork-tube-pitting

### known_issues rowid 309

**row_key**

- before: None
- after:  honda-wiring-harness-deterioration-brittle-insulation-and-corroded

### known_issues rowid 310

**row_key**

- before: None
- after:  honda-engine-gasket-weeping-and-oil-leak-top-end-and-covers

### known_issues rowid 311

**row_key**

- before: None
- after:  kawasaki-klr650-doohickey-failure-balancer-chain-tensioner

### known_issues rowid 312

**row_key**

- before: None
- after:  kawasaki-klr650-thermosyphon-oil-cooler-and-overheating

### known_issues rowid 313

**row_key**

- before: None
- after:  kawasaki-klr650-gen-2-2008-fuel-injection-lean-surge

### known_issues rowid 314

**row_key**

- before: None
- after:  kawasaki-klx250-300-valve-clearance-tightening

### known_issues rowid 315

**row_key**

- before: None
- after:  kawasaki-versys-650-suspension-inadequacy-stock-fork-and-shock

### known_issues rowid 316

**row_key**

- before: None
- after:  kawasaki-versys-1000-throttle-by-wire-hunting-at-low-speed

### known_issues rowid 317

**row_key**

- before: None
- after:  kawasaki-klr650-subframe-and-luggage-rack-cracking

### known_issues rowid 318

**row_key**

- before: None
- after:  kawasaki-klx250-300-carburetor-jetting-factory-lean-for-emissions

### known_issues rowid 319

**row_key**

- before: None
- after:  kawasaki-versys-650-chain-and-sprocket-accelerated-wear

### known_issues rowid 320

**row_key**

- before: None
- after:  kawasaki-klr650-stator-and-charging-system-failure

### known_issues rowid 321

**row_key**

- before: None
- after:  kawasaki-kawasaki-fi-self-diagnostic-mode-dealer-mode-dtc-readout

### known_issues rowid 322

**row_key**

- before: None
- after:  kawasaki-kawasaki-stator-and-regulator-rectifier-failure-all-models

### known_issues rowid 323

**row_key**

- before: None
- after:  kawasaki-kleen-pair-air-injection-system-exhaust-popping-and-removal

### known_issues rowid 324

**row_key**

- before: None
- after:  kawasaki-kawasaki-immobilizer-kipass-system-issues

### known_issues rowid 325

**row_key**

- before: None
- after:  kawasaki-kawasaki-led-lighting-upgrades-and-compatibility-issues

### known_issues rowid 326

**row_key**

- before: None
- after:  kawasaki-kawasaki-ground-connection-corrosion-intermittent-electrical

### known_issues rowid 327

**row_key**

- before: None
- after:  kawasaki-kawasaki-starter-system-relay-motor-and-clutch-switch

### known_issues rowid 328

**row_key**

- before: None
- after:  kawasaki-kawasaki-battery-drain-parasitic-draw-on-modern-models

### known_issues rowid 329

**row_key**

- before: None
- after:  kawasaki-kawasaki-ktrc-klcm-kibs-electronic-system-sensor-calibration

### known_issues rowid 330

**row_key**

- before: None
- after:  kawasaki-kawasaki-wiring-harness-connector-corrosion-multi-pin

### known_issues rowid 331

**row_key**

- before: None
- after:  kawasaki-supercharger-system-understanding-the-centrifugal-compressor

### known_issues rowid 332

**row_key**

- before: None
- after:  kawasaki-h2-extreme-cooling-demands-dual-radiator-system

### known_issues rowid 333

**row_key**

- before: None
- after:  kawasaki-h2-electronics-suite-ktrc-kibs-klcm-kebc-complexity

### known_issues rowid 334

**row_key**

- before: None
- after:  kawasaki-h2-paint-and-finish-self-healing-paint-and-mirror-chrome

### known_issues rowid 335

**row_key**

- before: None
- after:  kawasaki-h2-chain-and-sprocket-supercharged-torque-stress

### known_issues rowid 336

**row_key**

- before: None
- after:  kawasaki-h2-oil-consumption-and-quality-supercharger-lubrication

### known_issues rowid 337

**row_key**

- before: None
- after:  kawasaki-h2-fuel-system-high-flow-demands-under-boost

### known_issues rowid 338

**row_key**

- before: None
- after:  kawasaki-h2-sx-sport-touring-specific-luggage-wind-protection-cruise

### known_issues rowid 339

**row_key**

- before: None
- after:  kawasaki-h2-brake-system-stopping-500-lbs-of-supercharged-speed

### known_issues rowid 340

**row_key**

- before: None
- after:  kawasaki-h2-valve-clearance-supercharged-engine-increases-service

### known_issues rowid 341

**row_key**

- before: None
- after:  kawasaki-zx-12r-ram-air-system-pressurized-airbox-maintenance

### known_issues rowid 342

**row_key**

- before: None
- after:  kawasaki-zx-12r-charging-system-same-era-same-weakness

### known_issues rowid 343

**row_key**

- before: None
- after:  kawasaki-zx-12r-and-zx-14r-weight-related-brake-and-tire-wear

### known_issues rowid 344

**row_key**

- before: None
- after:  kawasaki-zx-14r-fuel-injection-and-throttle-response-ride-by-wire

### known_issues rowid 345

**row_key**

- before: None
- after:  kawasaki-zx-14r-abs-and-ktrc-sport-touring-electronics

### known_issues rowid 346

**row_key**

- before: None
- after:  kawasaki-zx-14r-shaft-drive-discussion-chain-drive-maintenance

### known_issues rowid 347

**row_key**

- before: None
- after:  kawasaki-zx-12r-and-zx-14r-cct-high-torque-inline-4

### known_issues rowid 348

**row_key**

- before: None
- after:  kawasaki-zx-14r-cooling-system-sport-touring-thermal-management

### known_issues rowid 349

**row_key**

- before: None
- after:  kawasaki-zx-12r-suspension-sag-heavy-bike-needs-proper-setup

### known_issues rowid 350

**row_key**

- before: None
- after:  kawasaki-zx-14r-valve-clearance-high-mileage-sport-tourer

### known_issues rowid 351

**row_key**

- before: None
- after:  kawasaki-ninja-250r-carburetor-issues-pilot-jets-and-choke-enrichment

### known_issues rowid 352

**row_key**

- before: None
- after:  kawasaki-ninja-250r-300-400-dropped-bike-damage-first-bike-reality

### known_issues rowid 353

**row_key**

- before: None
- after:  kawasaki-ninja-250r-300-charging-system-small-stator-big-demands

### known_issues rowid 354

**row_key**

- before: None
- after:  kawasaki-ninja-300-400-fuel-pump-and-fi-system-efi-beginner-bike

### known_issues rowid 355

**row_key**

- before: None
- after:  kawasaki-ninja-250-300-400-chain-maintenance-neglect-new-rider

### known_issues rowid 356

**row_key**

- before: None
- after:  kawasaki-ninja-250r-300-valve-clearance-parallel-twin-needs-regular

### known_issues rowid 357

**row_key**

- before: None
- after:  kawasaki-ninja-400-abs-sensor-and-modulator-issues

### known_issues rowid 358

**row_key**

- before: None
- after:  kawasaki-ninja-250r-coolant-system-air-cooled-vs-liquid-cooled

### known_issues rowid 359

**row_key**

- before: None
- after:  kawasaki-ninja-400-exhaust-header-cracking-known-factory-issue

### known_issues rowid 360

**row_key**

- before: None
- after:  kawasaki-all-ninja-250-300-400-oil-change-neglect-and-first-service

### known_issues rowid 361

**row_key**

- before: None
- after:  kawasaki-kz1000-1100-cam-chain-tensioner-failure-manual-vs-automatic

### known_issues rowid 362

**row_key**

- before: None
- after:  kawasaki-kz650-750-charging-system-stator-and-regulator-rectifier

### known_issues rowid 363

**row_key**

- before: None
- after:  kawasaki-kz-gpz-inline-4-carburetor-synchronization-and-rebuild

### known_issues rowid 364

**row_key**

- before: None
- after:  kawasaki-gpz900r-1000rx-fuel-system-petcock-and-tank-rust

### known_issues rowid 365

**row_key**

- before: None
- after:  kawasaki-kz550-650-ignition-system-points-vs-electronic-conversion

### known_issues rowid 366

**row_key**

- before: None
- after:  kawasaki-kz1000-1100-fork-seal-and-suspension-wear

### known_issues rowid 367

**row_key**

- before: None
- after:  kawasaki-all-kz-gpz-models-engine-oil-and-gasket-leaks

### known_issues rowid 368

**row_key**

- before: None
- after:  kawasaki-gpz550-750-brake-system-aging-calipers-and-master-cylinder

### known_issues rowid 369

**row_key**

- before: None
- after:  kawasaki-kz-gpz-electrical-wiring-brittle-harness-and-connector

### known_issues rowid 370

**row_key**

- before: None
- after:  kawasaki-kz-gpz-drive-chain-and-sprocket-original-equipment-long-gone

### known_issues rowid 371

**row_key**

- before: None
- after:  kawasaki-vulcan-800-900-carburetor-issues-pilot-jet-and-idle-circuit

### known_issues rowid 372

**row_key**

- before: None
- after:  kawasaki-vulcan-900-1700-fuel-injection-idle-surge-isc-valve-carbon

### known_issues rowid 373

**row_key**

- before: None
- after:  kawasaki-vulcan-1500-1600-shaft-drive-service-neglect

### known_issues rowid 374

**row_key**

- before: None
- after:  kawasaki-vulcan-750-starter-system-starter-clutch-and-relay-issues

### known_issues rowid 375

**row_key**

- before: None
- after:  kawasaki-vulcan-2000-massive-v-twin-unique-issues

### known_issues rowid 376

**row_key**

- before: None
- after:  kawasaki-vulcan-900-belt-drive-maintenance-tension-and-inspection

### known_issues rowid 377

**row_key**

- before: None
- after:  kawasaki-all-vulcan-models-air-cooled-v-twin-heat-soak-in-traffic

### known_issues rowid 378

**row_key**

- before: None
- after:  kawasaki-vulcan-1700-efi-and-abs-modern-cruiser-electronics

### known_issues rowid 379

**row_key**

- before: None
- after:  kawasaki-vulcan-500-ninja-500-engine-in-cruiser-chassis

### known_issues rowid 380

**row_key**

- before: None
- after:  kawasaki-all-vulcan-models-exhaust-and-intake-modifications-for-sound

### known_issues rowid 381

**row_key**

- before: None
- after:  kawasaki-z900-z1000-exposed-radiator-vulnerability-naked-bike-tax

### known_issues rowid 382

**row_key**

- before: None
- after:  kawasaki-z1000-throttle-response-aggressive-ride-by-wire-mapping

### known_issues rowid 383

**row_key**

- before: None
- after:  kawasaki-z650-z400-shared-ninja-platform-issues-in-naked-chassis

### known_issues rowid 384

**row_key**

- before: None
- after:  kawasaki-z750-z800-stator-and-charging-mid-displacement-kawasaki

### known_issues rowid 385

**row_key**

- before: None
- after:  kawasaki-z-h2-supercharged-naked-unique-cooling-and-boost-challenges

### known_issues rowid 386

**row_key**

- before: None
- after:  kawasaki-all-z-models-chain-maintenance-on-commuter-nakeds

### known_issues rowid 387

**row_key**

- before: None
- after:  kawasaki-z900-ktrc-traction-control-naked-bike-sensor-exposure

### known_issues rowid 388

**row_key**

- before: None
- after:  kawasaki-z1000-cct-high-revving-naked-inline-4

### known_issues rowid 389

**row_key**

- before: None
- after:  kawasaki-z400-z650-beginner-friendly-issues-drops-and-maintenance

### known_issues rowid 390

**row_key**

- before: None
- after:  kawasaki-all-z-models-headlight-and-visibility-upgrades-on-naked

### known_issues rowid 391

**row_key**

- before: None
- after:  kawasaki-2004-2005-zx-10r-headshake-and-stability-raw-first

### known_issues rowid 392

**row_key**

- before: None
- after:  kawasaki-zx-10r-stator-and-charging-system-literbike-heat-and-current

### known_issues rowid 393

**row_key**

- before: None
- after:  kawasaki-2016-zx-10r-imu-and-electronics-suite-ktrc-kibs-kecs

### known_issues rowid 394

**row_key**

- before: None
- after:  kawasaki-zx-10r-cct-failure-high-output-literbike-engine

### known_issues rowid 395

**row_key**

- before: None
- after:  kawasaki-zx-10r-fuel-pump-and-fuel-system-high-flow-demands

### known_issues rowid 396

**row_key**

- before: None
- after:  kawasaki-zx-10r-valve-clearance-literbike-service-interval

### known_issues rowid 397

**row_key**

- before: None
- after:  kawasaki-zx-10r-kleen-system-literbike-decel-popping

### known_issues rowid 398

**row_key**

- before: None
- after:  kawasaki-zx-10r-track-crash-damage-patterns-literbike-specific

### known_issues rowid 399

**row_key**

- before: None
- after:  kawasaki-zx-10r-quick-shifter-and-auto-blipper-shift-quality-tuning

### known_issues rowid 400

**row_key**

- before: None
- after:  kawasaki-zx-10r-cooling-system-high-output-engine-thermal-management

### known_issues rowid 401

**row_key**

- before: None
- after:  kawasaki-636cc-vs-599cc-displacement-confusion-racing-class-and-parts

### known_issues rowid 402

**row_key**

- before: None
- after:  kawasaki-zx-6r-stator-and-charging-system-failure-sport-bike

### known_issues rowid 403

**row_key**

- before: None
- after:  kawasaki-zx-6r-cam-chain-tensioner-high-revving-inline-4

### known_issues rowid 404

**row_key**

- before: None
- after:  kawasaki-kleen-system-decel-popping-kawasaki-s-emission-air-injection

### known_issues rowid 405

**row_key**

- before: None
- after:  kawasaki-zx-6r-valve-clearance-shim-under-bucket-on-high-revving-600

### known_issues rowid 406

**row_key**

- before: None
- after:  kawasaki-zx-6r-fuel-pump-failure-ethanol-and-heat-damage

### known_issues rowid 407

**row_key**

- before: None
- after:  kawasaki-zx-6r-cooling-system-radiator-fan-and-thermostat-issues

### known_issues rowid 408

**row_key**

- before: None
- after:  kawasaki-2009-zx-6r-ktrc-traction-control-sensor-and-calibration

### known_issues rowid 409

**row_key**

- before: None
- after:  kawasaki-zx-6r-fork-seal-leaks-aggressive-riding-accelerates-wear

### known_issues rowid 410

**row_key**

- before: None
- after:  kawasaki-zx-6r-quick-shifter-and-shift-quality-transmission-concerns

### known_issues rowid 411

**row_key**

- before: None
- after:  kawasaki-zx-7r-carburetor-sync-and-idle-issues-4-cv-carbs-on-aging

### known_issues rowid 412

**row_key**

- before: None
- after:  kawasaki-zx-7r-fuel-system-aging-petcock-fuel-lines-and-tank

### known_issues rowid 413

**row_key**

- before: None
- after:  kawasaki-zx-7r-charging-system-stator-and-regulator-on-aging-sport

### known_issues rowid 414

**row_key**

- before: None
- after:  kawasaki-zx-7rr-flat-slide-fcr-carburetor-maintenance-homologation

### known_issues rowid 415

**row_key**

- before: None
- after:  kawasaki-zx-7r-cam-chain-tensioner-750cc-inline-4-stress

### known_issues rowid 416

**row_key**

- before: None
- after:  kawasaki-zx-7r-wiring-harness-and-connector-degradation-20-year-old

### known_issues rowid 417

**row_key**

- before: None
- after:  kawasaki-zx-7r-rubber-component-degradation-hoses-seals-and-boots

### known_issues rowid 418

**row_key**

- before: None
- after:  kawasaki-zx-7r-suspension-fork-oil-and-shock-rebuild-on-aging-dampers

### known_issues rowid 419

**row_key**

- before: None
- after:  kawasaki-zx-7r-brake-system-caliper-rebuild-and-fluid-flush-on-aging

### known_issues rowid 420

**row_key**

- before: None
- after:  kawasaki-zx-7r-ignition-system-coils-plug-wires-and-spark-plugs-on

### known_issues rowid 421

**row_key**

- before: None
- after:  kawasaki-zx-9r-carburetor-issues-1998-1999-cv-carbs-on-open-class

### known_issues rowid 422

**row_key**

- before: None
- after:  kawasaki-zx-9r-early-fuel-injection-2000-2003-kawasaki-s-first-gen-fi

### known_issues rowid 423

**row_key**

- before: None
- after:  kawasaki-zx-9r-charging-system-failure-universal-kawasaki-sport-bike

### known_issues rowid 424

**row_key**

- before: None
- after:  kawasaki-zx-9r-cam-chain-tensioner-900cc-inline-4

### known_issues rowid 425

**row_key**

- before: None
- after:  kawasaki-zx-9r-cooling-system-thermostat-and-fan-relay-failures

### known_issues rowid 426

**row_key**

- before: None
- after:  kawasaki-zx-9r-fuel-pump-aging-2000-2003-fi-models

### known_issues rowid 427

**row_key**

- before: None
- after:  kawasaki-zx-9r-front-fork-seal-leaks-and-aging-suspension

### known_issues rowid 428

**row_key**

- before: None
- after:  kawasaki-zx-9r-brake-system-aging-same-urgency-as-zx-7r

### known_issues rowid 429

**row_key**

- before: None
- after:  kawasaki-zx-9r-valve-clearance-inline-4-at-20-years

### known_issues rowid 430

**row_key**

- before: None
- after:  kawasaki-zx-9r-ground-wire-and-ignition-switch-corrosion

### known_issues rowid 431

**row_key**

- before: None
- after:  suzuki-bandit-600-1200-air-oil-cooled-engine-overheating-in-traffic

### known_issues rowid 432

**row_key**

- before: None
- after:  suzuki-bandit-carburetor-bank-600-1200-sync-and-rebuild

### known_issues rowid 433

**row_key**

- before: None
- after:  suzuki-bandit-1250-2007-2012-fuel-injection-issues

### known_issues rowid 434

**row_key**

- before: None
- after:  suzuki-bandit-charging-system-stator-and-reg-rec-failure

### known_issues rowid 435

**row_key**

- before: None
- after:  suzuki-bandit-600-cam-chain-tensioner-rattle

### known_issues rowid 436

**row_key**

- before: None
- after:  suzuki-bandit-fork-and-suspension-budget-upgrades-for-naked-bike

### known_issues rowid 437

**row_key**

- before: None
- after:  suzuki-bandit-fuel-petcock-vacuum-diaphragm-failure-carb-models

### known_issues rowid 438

**row_key**

- before: None
- after:  suzuki-bandit-brake-system-aging-calipers-and-spongy-lever

### known_issues rowid 439

**row_key**

- before: None
- after:  suzuki-bandit-chain-and-sprocket-commuter-wear

### known_issues rowid 440

**row_key**

- before: None
- after:  suzuki-bandit-wiring-and-electrical-ground-corrosion-on-naked-bikes

### known_issues rowid 441

**row_key**

- before: None
- after:  suzuki-suzuki-universal-stator-connector-melting-fire-risk

### known_issues rowid 442

**row_key**

- before: None
- after:  suzuki-suzuki-cam-chain-tensioner-cross-model-failure-pattern

### known_issues rowid 443

**row_key**

- before: None
- after:  suzuki-suzuki-fuel-pump-relay-universal-15-failure

### known_issues rowid 444

**row_key**

- before: None
- after:  suzuki-suzuki-pair-system-removal-universal-procedure

### known_issues rowid 445

**row_key**

- before: None
- after:  suzuki-suzuki-coolant-system-universal-flush-and-thermostat-service

### known_issues rowid 446

**row_key**

- before: None
- after:  suzuki-suzuki-valve-clearance-cross-model-service-intervals

### known_issues rowid 447

**row_key**

- before: None
- after:  suzuki-suzuki-chain-and-sprocket-universal-maintenance

### known_issues rowid 448

**row_key**

- before: None
- after:  suzuki-suzuki-brake-fluid-contamination-all-hydraulic-brake-models

### known_issues rowid 449

**row_key**

- before: None
- after:  suzuki-suzuki-fork-seal-and-oil-cross-model-service

### known_issues rowid 450

**row_key**

- before: None
- after:  suzuki-suzuki-exhaust-modifications-universal-fueling-requirements

### known_issues rowid 451

**row_key**

- before: None
- after:  suzuki-boulevard-intruder-800-carburetor-issues-pilot-jet-and

### known_issues rowid 452

**row_key**

- before: None
- after:  suzuki-boulevard-c50-m50-fuel-injection-lean-surge

### known_issues rowid 453

**row_key**

- before: None
- after:  suzuki-boulevard-c90-m109r-shaft-drive-service

### known_issues rowid 454

**row_key**

- before: None
- after:  suzuki-boulevard-m109r-clutch-drag-and-creep

### known_issues rowid 455

**row_key**

- before: None
- after:  suzuki-intruder-boulevard-1500-starter-clutch-failure

### known_issues rowid 456

**row_key**

- before: None
- after:  suzuki-boulevard-intruder-charging-system-stator-and-reg-rec

### known_issues rowid 457

**row_key**

- before: None
- after:  suzuki-boulevard-intruder-air-cooled-v-twin-heat-management

### known_issues rowid 458

**row_key**

- before: None
- after:  suzuki-m109r-fuel-pump-and-fi-relay

### known_issues rowid 459

**row_key**

- before: None
- after:  suzuki-boulevard-exhaust-modification-and-fueling-popping-and-lean

### known_issues rowid 460

**row_key**

- before: None
- after:  suzuki-boulevard-brake-system-rear-drum-and-front-caliper

### known_issues rowid 461

**row_key**

- before: None
- after:  suzuki-dr-z400s-sm-carburetor-jetting-factory-lean-for-emissions

### known_issues rowid 462

**row_key**

- before: None
- after:  suzuki-dr-z400-valve-clearance-tightening-kick-start-getting-harder

### known_issues rowid 463

**row_key**

- before: None
- after:  suzuki-dr-z400sm-supermoto-brake-and-wheel-maintenance

### known_issues rowid 464

**row_key**

- before: None
- after:  suzuki-dr650se-carburetor-and-jetting-altitude-sensitive-thumper

### known_issues rowid 465

**row_key**

- before: None
- after:  suzuki-dr650se-oil-consumption-piston-rings-and-valve-seals

### known_issues rowid 466

**row_key**

- before: None
- after:  suzuki-dr-z400-dr650-chain-and-sprocket-off-road-accelerated-wear

### known_issues rowid 467

**row_key**

- before: None
- after:  suzuki-dr-z400-electrical-system-weak-charging-and-battery-drain

### known_issues rowid 468

**row_key**

- before: None
- after:  suzuki-dr650se-suspension-stock-fork-and-shock-inadequacy

### known_issues rowid 469

**row_key**

- before: None
- after:  suzuki-dr-z400-dr650-kick-start-mechanism-lever-and-shaft

### known_issues rowid 470

**row_key**

- before: None
- after:  suzuki-dr650se-starter-system-relay-and-motor-issues

### known_issues rowid 471

**row_key**

- before: None
- after:  suzuki-suzuki-c-mode-self-diagnostic-fi-light-blink-codes

### known_issues rowid 472

**row_key**

- before: None
- after:  suzuki-suzuki-stator-and-reg-rec-universal-diagnosis-procedure

### known_issues rowid 473

**row_key**

- before: None
- after:  suzuki-suzuki-pair-system-function-and-removal-across-models

### known_issues rowid 474

**row_key**

- before: None
- after:  suzuki-suzuki-ground-connection-corrosion-all-models

### known_issues rowid 475

**row_key**

- before: None
- after:  suzuki-suzuki-starter-system-relay-switches-and-motor-diagnosis

### known_issues rowid 476

**row_key**

- before: None
- after:  suzuki-suzuki-battery-and-parasitic-draw-modern-model-storage

### known_issues rowid 477

**row_key**

- before: None
- after:  suzuki-suzuki-s-dms-tc-abs-sensor-calibration-sport-models

### known_issues rowid 478

**row_key**

- before: None
- after:  suzuki-suzuki-led-conversion-and-electrical-load-management

### known_issues rowid 479

**row_key**

- before: None
- after:  suzuki-suzuki-wiring-connector-corrosion-multi-pin-failure-points

### known_issues rowid 480

**row_key**

- before: None
- after:  suzuki-suzuki-fi-relay-and-fuse-box-common-failure-across-models

### known_issues rowid 481

**row_key**

- before: None
- after:  suzuki-gsx-r1000-k5-k8-2005-2008-engine-cases-cracking-at-oil-drain

### known_issues rowid 482

**row_key**

- before: None
- after:  suzuki-gsx-r1000-stator-and-charging-failure

### known_issues rowid 483

**row_key**

- before: None
- after:  suzuki-gsx-r1000-s-dms-motion-track-tcs-imu-issues-2012

### known_issues rowid 484

**row_key**

- before: None
- after:  suzuki-gsx-r1000-cam-chain-tensioner-failure

### known_issues rowid 485

**row_key**

- before: None
- after:  suzuki-gsx-r1000-exhaust-valve-servo-set-suzuki-exhaust-tuning

### known_issues rowid 486

**row_key**

- before: None
- after:  suzuki-gsx-r1000-fuel-pump-relay-and-priming-failure

### known_issues rowid 487

**row_key**

- before: None
- after:  suzuki-gsx-r1000-valve-clearance-track-bike-accelerated-schedule

### known_issues rowid 488

**row_key**

- before: None
- after:  suzuki-gsx-r1000-quickshifter-issues-2017

### known_issues rowid 489

**row_key**

- before: None
- after:  suzuki-gsx-r1000-cooling-system-track-overheating

### known_issues rowid 490

**row_key**

- before: None
- after:  suzuki-gsx-r1000-rear-wheel-bearing-failure

### known_issues rowid 491

**row_key**

- before: None
- after:  suzuki-gsx-r1100-oil-air-cooled-engine-overheating-in-traffic

### known_issues rowid 492

**row_key**

- before: None
- after:  suzuki-gsx-r1100-carburetor-bank-4x-mikuni-bst36-40-rebuild-and

### known_issues rowid 493

**row_key**

- before: None
- after:  suzuki-gsx-r1100-charging-system-stator-and-regulator-failure

### known_issues rowid 494

**row_key**

- before: None
- after:  suzuki-gsx-r1100-cam-chain-tensioner-age-related-failure

### known_issues rowid 495

**row_key**

- before: None
- after:  suzuki-gsx-r1100-fork-and-suspension-period-correct-upgrades

### known_issues rowid 496

**row_key**

- before: None
- after:  suzuki-gsx-r1100-ignition-system-pickup-coil-and-cdi

### known_issues rowid 497

**row_key**

- before: None
- after:  suzuki-gsx-r1100-fuel-petcock-and-tank-rust

### known_issues rowid 498

**row_key**

- before: None
- after:  suzuki-gsx-r1100-brake-system-complete-refresh-needed

### known_issues rowid 499

**row_key**

- before: None
- after:  suzuki-gsx-r1100-wiring-harness-deterioration

### known_issues rowid 500

**row_key**

- before: None
- after:  suzuki-gsx-r1100-drive-chain-530-heavy-duty-requirements

### known_issues rowid 501

**row_key**

- before: None
- after:  suzuki-gsx-r600-stator-and-regulator-rectifier-failure-all-years

### known_issues rowid 502

**row_key**

- before: None
- after:  suzuki-gsx-r600-cam-chain-tensioner-cct-failure

### known_issues rowid 503

**row_key**

- before: None
- after:  suzuki-gsx-r600-pair-system-decel-popping-with-aftermarket-exhaust

### known_issues rowid 504

**row_key**

- before: None
- after:  suzuki-gsx-r600-fuel-pump-failure-and-fuel-filter-clogging

### known_issues rowid 505

**row_key**

- before: None
- after:  suzuki-gsx-r600-fork-seal-and-suspension-maintenance

### known_issues rowid 506

**row_key**

- before: None
- after:  suzuki-gsx-r600-valve-clearance-shim-under-bucket-inspection

### known_issues rowid 507

**row_key**

- before: None
- after:  suzuki-gsx-r600-coolant-system-thermostat-and-radiator-fan

### known_issues rowid 508

**row_key**

- before: None
- after:  suzuki-gsx-r600-s-dms-and-tc-system-issues-2011

### known_issues rowid 509

**row_key**

- before: None
- after:  suzuki-gsx-r600-brake-caliper-sticking-and-pad-glazing

### known_issues rowid 510

**row_key**

- before: None
- after:  suzuki-gsx-r600-clutch-drag-and-basket-notching

### known_issues rowid 511

**row_key**

- before: None
- after:  suzuki-gsx-r750-second-gear-failure-transmission-weakness

### known_issues rowid 512

**row_key**

- before: None
- after:  suzuki-gsx-r750-stator-and-charging-system-failure

### known_issues rowid 513

**row_key**

- before: None
- after:  suzuki-gsx-r750-cam-chain-tensioner-rattle

### known_issues rowid 514

**row_key**

- before: None
- after:  suzuki-gsx-r750-fuel-pump-and-fi-relay-2004

### known_issues rowid 515

**row_key**

- before: None
- after:  suzuki-gsx-r750-srad-1996-1999-coolant-leak-water-pump-and-hoses

### known_issues rowid 516

**row_key**

- before: None
- after:  suzuki-gsx-r750-rear-shock-linkage-wear

### known_issues rowid 517

**row_key**

- before: None
- after:  suzuki-gsx-r750-throttle-position-sensor-tps-calibration-drift

### known_issues rowid 518

**row_key**

- before: None
- after:  suzuki-gsx-r750-chain-and-sprocket-heavy-torque-wear

### known_issues rowid 519

**row_key**

- before: None
- after:  suzuki-gsx-r750-brake-master-cylinder-spongy-lever-and-fluid

### known_issues rowid 520

**row_key**

- before: None
- after:  suzuki-gsx-r750-headstock-bearing-wear-and-head-shake

### known_issues rowid 521

**row_key**

- before: None
- after:  suzuki-gsx-s750-1000-throttle-by-wire-jerkiness-at-low-speed

### known_issues rowid 522

**row_key**

- before: None
- after:  suzuki-gsx-s1000-cam-chain-tensioner-from-gsx-r-engine

### known_issues rowid 523

**row_key**

- before: None
- after:  suzuki-katana-2019-heat-management-gsx-s-engine-in-sport-touring

### known_issues rowid 524

**row_key**

- before: None
- after:  suzuki-gsx-s-katana-stator-and-charging-system

### known_issues rowid 525

**row_key**

- before: None
- after:  suzuki-gsx-s-katana-fuel-pump-relay-failure

### known_issues rowid 526

**row_key**

- before: None
- after:  suzuki-gsx-s750-chain-and-sprocket-maintenance

### known_issues rowid 527

**row_key**

- before: None
- after:  suzuki-katana-stock-mirror-vibration-rider-comfort-issue

### known_issues rowid 528

**row_key**

- before: None
- after:  suzuki-gsx-s-katana-valve-clearance-maintenance

### known_issues rowid 529

**row_key**

- before: None
- after:  suzuki-gsx-s1000-abs-and-tc-sensor-maintenance

### known_issues rowid 530

**row_key**

- before: None
- after:  suzuki-gsx-s-katana-fork-seal-and-oil-service

### known_issues rowid 531

**row_key**

- before: None
- after:  suzuki-sv650-regulator-rectifier-failure-all-generations

### known_issues rowid 532

**row_key**

- before: None
- after:  suzuki-sv650-carbureted-1999-2002-cv-carb-tuning-and-cold-start

### known_issues rowid 533

**row_key**

- before: None
- after:  suzuki-sv650-cam-chain-tensioner-noise-both-engines

### known_issues rowid 534

**row_key**

- before: None
- after:  suzuki-sv650-clutch-spring-and-basket-issues

### known_issues rowid 535

**row_key**

- before: None
- after:  suzuki-sv650-fuel-pump-failure-2003-fuel-injected

### known_issues rowid 536

**row_key**

- before: None
- after:  suzuki-sv650-suspension-stock-inadequacy-and-budget-upgrades

### known_issues rowid 537

**row_key**

- before: None
- after:  suzuki-sv1000-fuel-injection-surging-tps-and-secondary-throttle

### known_issues rowid 538

**row_key**

- before: None
- after:  suzuki-sv650-gladius-2009-2015-specific-generation-issues

### known_issues rowid 539

**row_key**

- before: None
- after:  suzuki-sv650-fork-seal-and-stanchion-maintenance

### known_issues rowid 540

**row_key**

- before: None
- after:  suzuki-sv650-exhaust-and-intake-modifications-fueling-requirements

### known_issues rowid 541

**row_key**

- before: None
- after:  suzuki-gs1000-1100-cam-chain-tensioner-automatic-unit-failure

### known_issues rowid 542

**row_key**

- before: None
- after:  suzuki-gs550-750-850-charging-system-stator-and-regulator

### known_issues rowid 543

**row_key**

- before: None
- after:  suzuki-gs-katana-1100-carburetor-bank-4x-mikuni-rebuild-and-sync

### known_issues rowid 544

**row_key**

- before: None
- after:  suzuki-gs-katana-ignition-system-points-electronic-and-cdi

### known_issues rowid 545

**row_key**

- before: None
- after:  suzuki-gsx1100-katana-1982-1984-fuel-system-petcock-and-tank-rust

### known_issues rowid 546

**row_key**

- before: None
- after:  suzuki-gs-katana-fork-and-suspension-modernization-needed

### known_issues rowid 547

**row_key**

- before: None
- after:  suzuki-gs-katana-brake-system-complete-refresh-required

### known_issues rowid 548

**row_key**

- before: None
- after:  suzuki-gs-katana-engine-oil-leaks-gasket-age

### known_issues rowid 549

**row_key**

- before: None
- after:  suzuki-gs-katana-wiring-harness-brittle-insulation-and-corroded

### known_issues rowid 550

**row_key**

- before: None
- after:  suzuki-gs-katana-drive-chain-530-maintenance-and-conversion

### known_issues rowid 551

**row_key**

- before: None
- after:  suzuki-v-strom-650-fuel-injection-lean-surge-at-cruise

### known_issues rowid 552

**row_key**

- before: None
- after:  suzuki-v-strom-1000-cam-chain-tensioner-noise

### known_issues rowid 553

**row_key**

- before: None
- after:  suzuki-v-strom-650-1000-windscreen-buffeting-and-wind-noise

### known_issues rowid 554

**row_key**

- before: None
- after:  suzuki-v-strom-650-1000-suspension-sag-for-adventure-loading

### known_issues rowid 555

**row_key**

- before: None
- after:  suzuki-v-strom-1050-2020-electronic-throttle-and-ride-mode-issues

### known_issues rowid 556

**row_key**

- before: None
- after:  suzuki-v-strom-charging-system-stator-and-reg-rec

### known_issues rowid 557

**row_key**

- before: None
- after:  suzuki-v-strom-chain-and-sprocket-loaded-touring-wear

### known_issues rowid 558

**row_key**

- before: None
- after:  suzuki-v-strom-650-valve-clearance-tightening

### known_issues rowid 559

**row_key**

- before: None
- after:  suzuki-v-strom-side-stand-switch-intermittent-starting-prevention

### known_issues rowid 560

**row_key**

- before: None
- after:  suzuki-v-strom-abs-system-maintenance-sensor-and-modulator

### known_issues rowid 561

**row_key**

- before: None
- after:  yamaha-cam-chain-tensioner-failure-cross-model-pattern-on-all

### known_issues rowid 562

**row_key**

- before: None
- after:  yamaha-ethanol-fuel-damage-storage-and-fuel-system-degradation

### known_issues rowid 563

**row_key**

- before: None
- after:  yamaha-valve-clearance-tightening-universal-yamaha-pattern-across

### known_issues rowid 564

**row_key**

- before: None
- after:  yamaha-exup-valve-system-cross-model-exhaust-valve-diagnostic

### known_issues rowid 565

**row_key**

- before: None
- after:  yamaha-brake-fluid-neglect-and-abs-modulator-corrosion-all-yamaha

### known_issues rowid 566

**row_key**

- before: None
- after:  yamaha-chain-and-sprocket-wear-patterns-sport-vs-cruiser-vs

### known_issues rowid 567

**row_key**

- before: None
- after:  yamaha-coolant-hose-degradation-and-clamp-loosening-all-liquid

### known_issues rowid 568

**row_key**

- before: None
- after:  yamaha-tire-selection-and-pressure-management-riding-style-matters

### known_issues rowid 569

**row_key**

- before: None
- after:  yamaha-winterization-and-seasonal-storage-protecting-your-yamaha

### known_issues rowid 570

**row_key**

- before: None
- after:  yamaha-aftermarket-exhaust-and-fueling-the-universal-mod-that

### known_issues rowid 571

**row_key**

- before: None
- after:  yamaha-v-star-650-carburetor-issues-pilot-jet-clogging-and-idle

### known_issues rowid 572

**row_key**

- before: None
- after:  yamaha-v-star-650-1100-vacuum-petcock-failure-fuel-in-oil

### known_issues rowid 573

**row_key**

- before: None
- after:  yamaha-v-star-1100-stator-and-charging-system-failure

### known_issues rowid 574

**row_key**

- before: None
- after:  yamaha-v-star-1300-950-shaft-drive-final-drive-service-neglect

### known_issues rowid 575

**row_key**

- before: None
- after:  yamaha-v-star-250-beginner-bike-valve-adjustment-single-cylinder

### known_issues rowid 576

**row_key**

- before: None
- after:  yamaha-bolt-r-spec-air-cooled-heat-management-in-traffic

### known_issues rowid 577

**row_key**

- before: None
- after:  yamaha-v-star-650-starter-clutch-and-starting-difficulty

### known_issues rowid 578

**row_key**

- before: None
- after:  yamaha-v-star-1300-fuel-injection-idle-surge-isc-valve

### known_issues rowid 579

**row_key**

- before: None
- after:  yamaha-bolt-drive-belt-tension-and-inspection-belt-drive-cruiser

### known_issues rowid 580

**row_key**

- before: None
- after:  yamaha-v-star-650-1100-exhaust-and-intake-decel-popping-air

### known_issues rowid 581

**row_key**

- before: None
- after:  yamaha-wr250r-stator-and-charging-small-engine-high-demand

### known_issues rowid 582

**row_key**

- before: None
- after:  yamaha-wr250r-suspension-service-high-quality-components-need

### known_issues rowid 583

**row_key**

- before: None
- after:  yamaha-wr250r-fuel-injection-cold-start-issues-small-single

### known_issues rowid 584

**row_key**

- before: None
- after:  yamaha-xt250-carburetor-and-fuel-system-ethanol-and-storage-issues

### known_issues rowid 585

**row_key**

- before: None
- after:  yamaha-xt250-chain-stretch-and-sprocket-wear-trail-riding

### known_issues rowid 586

**row_key**

- before: None
- after:  yamaha-xt250-valve-adjustment-screw-type-easy-and-critical

### known_issues rowid 587

**row_key**

- before: None
- after:  yamaha-tenere-700-wind-protection-and-ergonomic-fatigue

### known_issues rowid 588

**row_key**

- before: None
- after:  yamaha-tenere-700-off-road-crash-protection-essential-guards-and

### known_issues rowid 589

**row_key**

- before: None
- after:  yamaha-tenere-700-cp2-engine-fueling-lean-spot-same-as-mt-07-r7

### known_issues rowid 590

**row_key**

- before: None
- after:  yamaha-tenere-700-rear-shock-inadequacy-for-loaded-adventure-riding

### known_issues rowid 591

**row_key**

- before: None
- after:  yamaha-yamaha-self-diagnostic-mode-fi-light-blink-code-reading

### known_issues rowid 592

**row_key**

- before: None
- after:  yamaha-universal-stator-connector-failure-every-yamaha-from-the

### known_issues rowid 593

**row_key**

- before: None
- after:  yamaha-mosfet-regulator-upgrade-universal-recommendation-for-all

### known_issues rowid 594

**row_key**

- before: None
- after:  yamaha-ground-wire-corrosion-the-most-misdiagnosed-yamaha

### known_issues rowid 595

**row_key**

- before: None
- after:  yamaha-yamaha-wiring-harness-degradation-heat-and-age

### known_issues rowid 596

**row_key**

- before: None
- after:  yamaha-yamaha-fuse-and-relay-diagnostics-systematic-troubleshooting

### known_issues rowid 597

**row_key**

- before: None
- after:  yamaha-yamaha-immobilizer-system-ydis-key-chip-and-antenna

### known_issues rowid 598

**row_key**

- before: None
- after:  yamaha-yamaha-led-and-lighting-upgrades-electrical-load

### known_issues rowid 599

**row_key**

- before: None
- after:  yamaha-yamaha-battery-selection-agm-vs-lithium-considerations

### known_issues rowid 600

**row_key**

- before: None
- after:  yamaha-woolich-racing-diagnostic-tool-the-aftermarket-yamaha

### known_issues rowid 601

**row_key**

- before: None
- after:  yamaha-mt-09-fz-09-snatchy-throttle-response-ride-by-wire

### known_issues rowid 602

**row_key**

- before: None
- after:  yamaha-mt-09-fz-09-cp3-engine-valve-clearance-tightening

### known_issues rowid 603

**row_key**

- before: None
- after:  yamaha-mt-07-fz-07-stator-connector-and-charging-cp2-platform

### known_issues rowid 604

**row_key**

- before: None
- after:  yamaha-fz6-fz6r-overheating-in-traffic-detuned-r6-engine-in-naked

### known_issues rowid 605

**row_key**

- before: None
- after:  yamaha-mt-10-fz-10-electronics-complexity-r1-crossplane-in-a-naked

### known_issues rowid 606

**row_key**

- before: None
- after:  yamaha-mt-03-beginner-bike-dropped-in-parking-lot-damage-pattern

### known_issues rowid 607

**row_key**

- before: None
- after:  yamaha-fz8-throttle-bodies-and-idle-issues-fazer-engine-platform

### known_issues rowid 608

**row_key**

- before: None
- after:  yamaha-mt-09-fz-09-fuel-pump-and-fuel-system-ethanol-sensitivity

### known_issues rowid 609

**row_key**

- before: None
- after:  yamaha-mt-07-fz-07-chain-and-sprocket-high-torque-twin-wears

### known_issues rowid 610

**row_key**

- before: None
- after:  yamaha-all-fz-mt-models-exposed-radiator-vulnerability-on-naked

### known_issues rowid 611

**row_key**

- before: None
- after:  yamaha-exup-valve-servo-failure-all-generations

### known_issues rowid 612

**row_key**

- before: None
- after:  yamaha-stator-and-charging-system-failure-1998-2008-models

### known_issues rowid 613

**row_key**

- before: None
- after:  yamaha-crossplane-crank-engine-noise-2009-r1-characteristic-sound

### known_issues rowid 614

**row_key**

- before: None
- after:  yamaha-ycc-t-yamaha-chip-controlled-throttle-issues-2004

### known_issues rowid 615

**row_key**

- before: None
- after:  yamaha-ycc-i-yamaha-chip-controlled-intake-variable-intake

### known_issues rowid 616

**row_key**

- before: None
- after:  yamaha-fuel-pump-failure-and-tank-corrosion

### known_issues rowid 617

**row_key**

- before: None
- after:  yamaha-cam-chain-tensioner-yamaha-version

### known_issues rowid 618

**row_key**

- before: None
- after:  yamaha-fork-and-shock-degradation-track-use-accelerates-wear

### known_issues rowid 619

**row_key**

- before: None
- after:  yamaha-r1m-r1s-electronics-complexity-2015-specific

### known_issues rowid 620

**row_key**

- before: None
- after:  yamaha-subframe-and-bodywork-damage-from-track-crashes

### known_issues rowid 621

**row_key**

- before: None
- after:  yamaha-cam-chain-tensioner-failure-2003-2005-r6-notorious

### known_issues rowid 622

**row_key**

- before: None
- after:  yamaha-stator-and-charging-system-failure-all-fuel-injected-models

### known_issues rowid 623

**row_key**

- before: None
- after:  yamaha-valve-clearance-tightening-shim-under-bucket-requires

### known_issues rowid 624

**row_key**

- before: None
- after:  yamaha-exup-valve-servo-failure-same-system-as-r1

### known_issues rowid 625

**row_key**

- before: None
- after:  yamaha-2006-2007-underseat-exhaust-heat-damage

### known_issues rowid 626

**row_key**

- before: None
- after:  yamaha-fuel-pump-failure-ethanol-and-low-fuel-damage

### known_issues rowid 627

**row_key**

- before: None
- after:  yamaha-throttle-body-sync-carbureted-gen-1-and-fuel-injected-models

### known_issues rowid 628

**row_key**

- before: None
- after:  yamaha-coolant-leak-from-water-pump-mechanical-seal

### known_issues rowid 629

**row_key**

- before: None
- after:  yamaha-immobilizer-key-chip-recognition-failure

### known_issues rowid 630

**row_key**

- before: None
- after:  yamaha-2017-r6-electronics-suite-shared-r1-platform-issues

### known_issues rowid 631

**row_key**

- before: None
- after:  yamaha-yzf600r-thundercat-carburetor-sync-and-idle-issues

### known_issues rowid 632

**row_key**

- before: None
- after:  yamaha-yzf600r-thundercat-vacuum-petcock-failure

### known_issues rowid 633

**row_key**

- before: None
- after:  yamaha-yzf600r-thundercat-charging-system-and-regulator-failure

### known_issues rowid 634

**row_key**

- before: None
- after:  yamaha-yzf600r-thundercat-chain-and-sprocket-wear-sport-touring

### known_issues rowid 635

**row_key**

- before: None
- after:  yamaha-yzf600r-thundercat-fork-seal-leaks-and-suspension-sag

### known_issues rowid 636

**row_key**

- before: None
- after:  yamaha-r7-clutch-chatter-and-engagement-harshness-cp2-twin

### known_issues rowid 637

**row_key**

- before: None
- after:  yamaha-r7-suspension-inadequacy-for-track-use-budget-components

### known_issues rowid 638

**row_key**

- before: None
- after:  yamaha-r7-quick-shifter-inconsistency-and-false-neutrals

### known_issues rowid 639

**row_key**

- before: None
- after:  yamaha-r7-overheating-in-slow-traffic-cp2-heat-management

### known_issues rowid 640

**row_key**

- before: None
- after:  yamaha-r7-ecu-fueling-lean-spot-at-3000-4500-rpm-emissions-mapping

### known_issues rowid 641

**row_key**

- before: None
- after:  yamaha-xs650-points-ignition-timing-and-condenser-failure

### known_issues rowid 642

**row_key**

- before: None
- after:  yamaha-xs650-charging-system-rotor-and-stator-failure

### known_issues rowid 643

**row_key**

- before: None
- after:  yamaha-xs650-oil-leaks-engine-case-pushrod-seals-and-gaskets

### known_issues rowid 644

**row_key**

- before: None
- after:  yamaha-xs650-cam-chain-and-tensioner-40-year-old-engines

### known_issues rowid 645

**row_key**

- before: None
- after:  yamaha-rd350-400-oil-injection-system-failure-autolube

### known_issues rowid 646

**row_key**

- before: None
- after:  yamaha-rd350-400-expansion-chamber-and-exhaust-condition

### known_issues rowid 647

**row_key**

- before: None
- after:  yamaha-rd350-400-reed-valve-inspection-and-replacement

### known_issues rowid 648

**row_key**

- before: None
- after:  yamaha-sr400-500-kickstart-only-starting-technique-and

### known_issues rowid 649

**row_key**

- before: None
- after:  yamaha-sr400-500-carburetor-and-jetting-single-mikuni-vm-bs-carb

### known_issues rowid 650

**row_key**

- before: None
- after:  yamaha-sr400-500-valve-adjustment-screw-type-frequent-interval

### known_issues rowid 651

**row_key**

- before: None
- after:  yamaha-gen-1-v-boost-system-malfunction-butterfly-valve-and-servo

### known_issues rowid 652

**row_key**

- before: None
- after:  yamaha-gen-1-vmax-carburetor-sync-and-jetting-4-mikuni-carbs

### known_issues rowid 653

**row_key**

- before: None
- after:  yamaha-gen-1-vmax-charging-system-failure-stator-and-regulator

### known_issues rowid 654

**row_key**

- before: None
- after:  yamaha-gen-1-vmax-shaft-drive-and-final-drive-service

### known_issues rowid 655

**row_key**

- before: None
- after:  yamaha-gen-1-vmax-fuel-system-tank-corrosion-and-petcock-issues

### known_issues rowid 656

**row_key**

- before: None
- after:  yamaha-gen-2-vmax-fuel-injection-and-throttle-body-issues

### known_issues rowid 657

**row_key**

- before: None
- after:  yamaha-gen-2-vmax-cooling-system-radiator-and-coolant-management

### known_issues rowid 658

**row_key**

- before: None
- after:  yamaha-gen-2-vmax-weight-related-brake-and-tire-wear

### known_issues rowid 659

**row_key**

- before: None
- after:  yamaha-gen-2-vmax-electronics-abs-tc-and-cruise-control

### known_issues rowid 660

**row_key**

- before: None
- after:  yamaha-all-vmax-exhaust-system-heat-and-header-bluing

### known_issues rowid 661

**row_key**

- before: None
- after:  aprilia-the-shiver-and-dorsoduro-share-a-90-degree-longitudinal-v

### known_issues rowid 662

**row_key**

- before: None
- after:  aprilia-the-shiver-s-ride-by-wire-self-learns-at-every-key-on-so-a

### known_issues rowid 663

**row_key**

- before: None
- after:  aprilia-an-aprilia-throttle-body-is-a-non-serviceable-assembly-and

### known_issues rowid 664

**row_key**

- before: None
- after:  aprilia-the-chronic-shiver-and-dorsoduro-fuel-pump-and-charging

### known_issues rowid 665

**row_key**

- before: None
- after:  aprilia-the-sr-max-is-a-scooter-not-a-motorcycle-it-shares-nothing

### known_issues rowid 666

**row_key**

- before: None
- after:  aprilia-and-mv-agusta-a-generic-scan-tool-is-more-dangerous-on-an-aprilia-than-on

### known_issues rowid 667

**row_key**

- before: None
- after:  aprilia-nineteen-aprilia-fault-codes-never-reach-the-instrument

### known_issues rowid 668

**row_key**

- before: None
- after:  aprilia-aprilia-s-hidden-service-code-menu-reports-dashboard-faults

### known_issues rowid 669

**row_key**

- before: None
- after:  aprilia-and-mv-agusta-a-euro-4-aprilia-or-mv-agusta-is-not-a-locked-door-the

### known_issues rowid 670

**row_key**

- before: None
- after:  aprilia-and-mv-agusta-both-makes-changed-diagnostic-connectors-more-than-once-and

### known_issues rowid 671

**row_key**

- before: None
- after:  mv-agusta-mv-agusta-has-no-diagnostic-software-of-its-own-the-official

### known_issues rowid 672

**row_key**

- before: None
- after:  mv-agusta-mv-agusta-uses-a-genuine-manufacturer-fault-code-block-that

### known_issues rowid 673

**row_key**

- before: None
- after:  aprilia-tuneecu-covers-aprilia-but-not-mv-agusta-and-it-is-a-mapping

### known_issues rowid 674

**row_key**

- before: None
- after:  aprilia-no-aprilia-v4-has-ever-displaced-1100cc-and-the-same-model

### known_issues rowid 675

**row_key**

- before: None
- after:  aprilia-cylinder-1-on-an-aprilia-v4-is-the-left-rear-the-banks

### known_issues rowid 676

**row_key**

- before: None
- after:  aprilia-the-aprilia-v4-cam-drive-is-chain-to-intake-and-gear-to

### known_issues rowid 677

**row_key**

- before: None
- after:  aprilia-three-normal-aprc-behaviours-look-like-faults-a-lit-rider

### known_issues rowid 678

**row_key**

- before: None
- after:  aprilia-aprc-must-be-recalibrated-after-wheel-tyre-or-sprocket-work

### known_issues rowid 679

**row_key**

- before: None
- after:  aprilia-an-aprilia-engine-recall-is-filed-under-a-misspelled-make-a

### known_issues rowid 680

**row_key**

- before: None
- after:  aprilia-the-aprilia-front-brake-master-cylinder-is-a-repeat-offender

### known_issues rowid 681

**row_key**

- before: None
- after:  aprilia-charging-failures-on-an-aprilia-v4-are-owner-consensus-not-a

### known_issues rowid 682

**row_key**

- before: None
- after:  bmw-bmw-proprietary-fault-codes-are-invisible-to-a-generic

### known_issues rowid 683

**row_key**

- before: None
- after:  bmw-zfe-central-vehicle-electronics-as-the-failed-module

### known_issues rowid 684

**row_key**

- before: None
- after:  bmw-bmw-motorcycle-diagnostic-connectors-round-10-pin

### known_issues rowid 685

**row_key**

- before: None
- after:  bmw-dry-sump-oil-overfill-oil-in-airbox-from-wrong-level-check

### known_issues rowid 686

**row_key**

- before: None
- after:  bmw-starter-freewheel-sprag-replacement-on-the-rotax-652-single

### known_issues rowid 687

**row_key**

- before: None
- after:  bmw-notchy-indexed-steering-head-bearings-on-the-21-inch-f800gs

### known_issues rowid 688

**row_key**

- before: None
- after:  bmw-rapid-rear-brake-pad-wear-and-dragging-rear-brake-on-the

### known_issues rowid 689

**row_key**

- before: None
- after:  bmw-gear-shift-assist-pro-stops-working-shift-lever-sensor

### known_issues rowid 690

**row_key**

- before: None
- after:  bmw-steering-head-clunk-over-bumps-bearing-adjuster-loose-from

### known_issues rowid 691

**row_key**

- before: None
- after:  bmw-accessory-spliced-into-a-zfe-switched-circuit-trips-the

### known_issues rowid 692

**row_key**

- before: None
- after:  bmw-heated-grips-inoperative-engine-running-lockout-zfe-low

### known_issues rowid 693

**row_key**

- before: None
- after:  bmw-non-can-accessories-on-the-f750gs-f850gs-zfe-platform

### known_issues rowid 694

**row_key**

- before: None
- after:  bmw-f800gs-21-inch-tubed-spoked-front-wheel-spoke-loosening

### known_issues rowid 695

**row_key**

- before: None
- after:  bmw-f800gs-rear-wheel-and-cush-drive-sprocket-carrier-bearing

### known_issues rowid 696

**row_key**

- before: None
- after:  bmw-f800gs-swingarm-chain-slider-wear-allowing-the-chain-to-cut

### known_issues rowid 697

**row_key**

- before: None
- after:  bmw-dry-single-plate-clutch-contaminated-by-oil-slip-and-judder

### known_issues rowid 698

**row_key**

- before: None
- after:  bmw-telelever-a-arm-ball-joint-wear-knock-under-braking

### known_issues rowid 699

**row_key**

- before: None
- after:  bmw-telelever-front-spring-strut-worn-or-leaking-mistaken-for-a

### known_issues rowid 700

**row_key**

- before: None
- after:  bmw-driveshaft-spline-wear-at-gearbox-output-and-final-drive

### known_issues rowid 701

**row_key**

- before: None
- after:  bmw-duolever-front-end-ball-joint-and-wishbone-wear-transverse

### known_issues rowid 702

**row_key**

- before: None
- after:  bmw-first-generation-esa-electronic-suspension-actuator-failure

### known_issues rowid 703

**row_key**

- before: None
- after:  bmw-duolever-ball-joint-and-wishbone-wear-k1300-front-end-play

### known_issues rowid 704

**row_key**

- before: None
- after:  bmw-esa-ii-on-the-k1300-telling-a-dead-adjuster-from-a-worn-out

### known_issues rowid 705

**row_key**

- before: None
- after:  bmw-reverse-assist-inoperative-or-drops-out-k1600-models-with

### known_issues rowid 706

**row_key**

- before: None
- after:  bmw-duolever-wishbone-ball-joint-wear-k1600-front-end-knock-with

### known_issues rowid 707

**row_key**

- before: None
- after:  bmw-duolever-steering-link-and-steering-pivot-play-vague

### known_issues rowid 708

**row_key**

- before: None
- after:  bmw-final-drive-crown-wheel-bearing-failure-hexhead-r1200gs-rt-r

### known_issues rowid 709

**row_key**

- before: None
- after:  bmw-surging-at-steady-throttle-oilhead-r1100-r1150-motronic-ma2

### known_issues rowid 710

**row_key**

- before: None
- after:  bmw-rear-main-gearbox-input-seal-leak-contaminating-the-dry

### known_issues rowid 711

**row_key**

- before: None
- after:  bmw-gearbox-input-shaft-spline-wear-dry-clutch-hub

### known_issues rowid 712

**row_key**

- before: None
- after:  bmw-hall-effect-sensor-wiring-breakdown-oilhead-r1100-r1150

### known_issues rowid 713

**row_key**

- before: None
- after:  bmw-integral-abs-servo-assisted-pump-failure-20012006-oilhead

### known_issues rowid 714

**row_key**

- before: None
- after:  bmw-fuel-level-strip-sensor-failure-hexhead-r1200-and-f800

### known_issues rowid 715

**row_key**

- before: None
- after:  bmw-alternator-drive-belt-wear-belt-driven-alternator-oilhead

### known_issues rowid 716

**row_key**

- before: None
- after:  bmw-water-pump-seal-weep-wethead-r1200-r1250-liquid-cooled-2013

### known_issues rowid 717

**row_key**

- before: None
- after:  bmw-diode-board-failure-airhead-5-6-7-and-r-series-19701995

### known_issues rowid 718

**row_key**

- before: None
- after:  bmw-alternator-rotor-open-circuit-and-brush-wear-airhead

### known_issues rowid 719

**row_key**

- before: None
- after:  bmw-paralever-pivot-bearing-wear-oilhead-and-hexhead-swingarm

### known_issues rowid 720

**row_key**

- before: None
- after:  bmw-cold-start-timing-chain-rattle-on-s1000rr-k46-tensioner

### known_issues rowid 721

**row_key**

- before: None
- after:  bmw-race-abs-partly-integral-braking-on-s1000rr-k46-mistaken-for

### known_issues rowid 722

**row_key**

- before: None
- after:  bmw-shiftcam-cold-start-rattle-on-2019-s1000rr-separating-normal

### known_issues rowid 723

**row_key**

- before: None
- after:  bmw-shiftcam-fails-to-switch-to-the-full-load-cam-profile

### known_issues rowid 724

**row_key**

- before: None
- after:  bmw-s1000xr-2015-2019-first-generation-high-frequency-vibration

### known_issues rowid 725

**row_key**

- before: None
- after:  bmw-ddc-dynamic-esa-rear-shock-fails-to-a-fixed-damping-state-on

### known_issues rowid 806

**row_key**

- before: None
- after:  ducati-desmodromic-valve-gear-is-two-rockers-and-two-shims-per

### known_issues rowid 807

**row_key**

- before: None
- after:  ducati-both-desmo-clearances-must-be-measured-the-closing-clearance

### known_issues rowid 808

**row_key**

- before: None
- after:  ducati-closing-shim-collets-and-half-rings-the-step-where-a-desmo

### known_issues rowid 809

**row_key**

- before: None
- after:  ducati-shim-availability-not-shim-price-is-what-strands-a-ducati

### known_issues rowid 810

**row_key**

- before: None
- after:  ducati-desmo-service-intervals-vary-by-generation-a-remembered

### known_issues rowid 811

**row_key**

- before: None
- after:  ducati-two-valve-and-four-valve-desmo-services-are-different-jobs

### known_issues rowid 812

**row_key**

- before: None
- after:  ducati-ducati-proprietary-fault-codes-are-invisible-to-a-generic

### known_issues rowid 813

**row_key**

- before: None
- after:  ducati-throttle-position-reset-after-throttle-body-work-is-a

### known_issues rowid 814

**row_key**

- before: None
- after:  ducati-the-dda-is-a-data-logger-not-a-fault-reader-owners-and-shops

### known_issues rowid 815

**row_key**

- before: None
- after:  ducati-ducati-immobiliser-and-the-coded-key-a-no-start-that-is

### known_issues rowid 816

**row_key**

- before: None
- after:  ducati-aftermarket-exhaust-and-ecu-mapping-on-a-ducati-what-a

### known_issues rowid 817

**row_key**

- before: None
- after:  ducati-cam-belt-degradation-by-age-on-air-cooled-2v-desmodue

### known_issues rowid 818

**row_key**

- before: None
- after:  ducati-cam-belt-age-out-and-tensioner-idler-bearing-failure-on-the

### known_issues rowid 819

**row_key**

- before: None
- after:  ducati-single-sided-swingarm-eccentric-chain-adjuster-seized-or

### known_issues rowid 820

**row_key**

- before: None
- after:  ducati-nylon-fuel-tank-swelling-and-distortion-on-ethanol-blended

### known_issues rowid 821

**row_key**

- before: None
- after:  ducati-fuel-weep-and-erratic-fuel-gauge-at-the-in-tank-pump-flange

### known_issues rowid 822

**row_key**

- before: None
- after:  ducati-cam-belt-age-based-replacement-and-tensioner-idler-bearing

### known_issues rowid 823

**row_key**

- before: None
- after:  ducati-cam-belt-age-out-and-condition-inspection-on-the-liquid

### known_issues rowid 824

**row_key**

- before: None
- after:  ducati-trellis-frame-bolted-to-the-cylinder-heads-fastener

### known_issues rowid 825

**row_key**

- before: None
- after:  ducati-monster-937-crash-damage-assessment-cast-aluminium-front

### known_issues rowid 826

**row_key**

- before: None
- after:  ducati-dry-slipper-clutch-plate-ear-and-basket-finger-hammering

### known_issues rowid 827

**row_key**

- before: None
- after:  ducati-external-hydraulic-clutch-slave-cylinder-weeping-dot4-onto

### known_issues rowid 828

**row_key**

- before: None
- after:  ducati-normal-dry-clutch-idle-rattle-mistaken-for-a-fault-triage

### known_issues rowid 829

**row_key**

- before: None
- after:  ducati-multistrada-v4-has-no-desmodromic-valves-desmo-era-service

### known_issues rowid 830

**row_key**

- before: None
- after:  ducati-multistrada-cam-drive-splits-by-generation-belts-on-the-1200

### known_issues rowid 831

**row_key**

- before: None
- after:  ducati-multistrada-1200-dvt-variable-valve-timing-noise-and

### known_issues rowid 832

**row_key**

- before: None
- after:  ducati-multistrada-v4-radar-sensors-contamination-and-alignment-not

### known_issues rowid 833

**row_key**

- before: None
- after:  ducati-skyhook-electronic-preload-not-told-about-the-load-sag-and

### known_issues rowid 834

**row_key**

- before: None
- after:  ducati-multistrada-v4-rear-cylinder-deactivation-at-a-standstill

### known_issues rowid 835

**row_key**

- before: None
- after:  ducati-multistrada-1200-and-1260-are-not-the-same-bike-for-parts-or

### known_issues rowid 836

**row_key**

- before: None
- after:  ducati-multistrada-v4-rally-and-loaded-touring-bikes-checking-what

### known_issues rowid 837

**row_key**

- before: None
- after:  ducati-superquadro-cam-drive-is-chain-and-gear-no-belt-service-and

### known_issues rowid 838

**row_key**

- before: None
- after:  ducati-panigale-monocoque-construction-there-is-no-frame-to

### known_issues rowid 839

**row_key**

- before: None
- after:  ducati-panigale-v4-rear-bank-deactivation-at-idle-mistaken-for-a

### known_issues rowid 840

**row_key**

- before: None
- after:  ducati-panigale-v4-counter-rotating-crank-changes-how-the-bike

### known_issues rowid 841

**row_key**

- before: None
- after:  ducati-superquadro-heat-at-a-standstill-rear-cylinder-coolant-and

### known_issues rowid 842

**row_key**

- before: None
- after:  ducati-ohlins-smart-ec-semi-active-suspension-on-the-panigale-s

### known_issues rowid 843

**row_key**

- before: None
- after:  ducati-panigale-side-mounted-radiators-and-exposed-coolers-take

### known_issues rowid 844

**row_key**

- before: None
- after:  ducati-streetfighter-v4-is-a-panigale-underneath-do-not-apply

### known_issues rowid 845

**row_key**

- before: None
- after:  ducati-panigale-wet-slipper-clutch-judder-and-drag-not-the-dry

### known_issues rowid 846

**row_key**

- before: None
- after:  ducati-panigale-899-and-959-are-not-small-1199s-subframe-exhaust

### known_issues rowid 847

**row_key**

- before: None
- after:  zero-removing-the-service-disconnect-isolates-the-pack-it-does

### known_issues rowid 848

**row_key**

- before: None
- after:  zero-verify-absence-of-voltage-with-a-meter-you-prove-live-dead

### known_issues rowid 849

**row_key**

- before: None
- after:  zero-the-capacitor-discharge-wait-is-a-specified-interval-not-a

### known_issues rowid 850

**row_key**

- before: None
- after:  zero-keep-the-removed-service-disconnect-on-your-person-lockout

### known_issues rowid 851

**row_key**

- before: None
- after:  zero-insulated-gloves-are-rated-dated-and-inspected-an

### known_issues rowid 852

**row_key**

- before: None
- after:  zero-do-not-work-alone-on-a-live-hv-system-and-know-the-rescue

### known_issues rowid 853

**row_key**

- before: None
- after:  zero-orange-cable-is-a-convention-not-a-guarantee-identify-hv

### known_issues rowid 854

**row_key**

- before: None
- after:  zero-a-damaged-deformed-or-submerged-pack-is-a-different-job-do

### known_issues rowid 855

**row_key**

- before: None
- after:  zero-hv-work-has-a-qualification-requirement-and-this-corpus-does

### known_issues rowid 856

**row_key**

- before: None
- after:  zero-isolation-expires-re-verify-after-any-interruption-and

### known_issues rowid 857

**row_key**

- before: None
- after:  energica-energica-is-not-one-motor-pmac-hsm-and-pmasynrm-across-three

### known_issues rowid 858

**row_key**

- before: None
- after:  energica-no-energica-document-states-a-pole-or-pole-pair-count-do-not

### known_issues rowid 859

**row_key**

- before: None
- after:  energica-energica-publishes-127-fault-codes-in-standard-sae-format

### known_issues rowid 860

**row_key**

- before: None
- after:  energica-the-rider-can-read-energica-codes-with-no-tool-at-all-and

### known_issues rowid 861

**row_key**

- before: None
- after:  energica-energica-exposes-ev-live-data-through-standard-obd-pids-not

### known_issues rowid 862

**row_key**

- before: None
- after:  energica-energica-s-service-intervals-exist-but-are-generation

### known_issues rowid 863

**row_key**

- before: None
- after:  energica-energica-pack-capacity-grew-across-generations-and-cycle

### known_issues rowid 864

**row_key**

- before: None
- after:  energica-energica-drives-through-a-chain-and-the-ratio-differs-by

### known_issues rowid 865

**row_key**

- before: None
- after:  energica-dc-fast-charging-is-standard-on-an-energica-and-the-ac

### known_issues rowid 866

**row_key**

- before: None
- after:  energica-energica-s-documentation-and-dealer-network-have-both

### known_issues rowid 867

**row_key**

- before: None
- after:  energica-energica-exposes-two-independent-data-paths-and-owners-have

### known_issues rowid 868

**row_key**

- before: None
- after:  energica-an-energica-can-become-an-orphaned-machine-mid-repair-record

### known_issues rowid 869

**row_key**

- before: None
- after:  bmw-bmw-oilhead-charging-fault-the-first-suspect-is-the-brush

### known_issues rowid 870

**row_key**

- before: None
- after:  bmw-bmw-boxer-alternator-belts-come-in-two-incompatible-types

### known_issues rowid 871

**row_key**

- before: None
- after:  bmw-bmw-liquid-cooled-boxer-charging-the-alternator-is-inside

### known_issues rowid 872

**row_key**

- before: None
- after:  ktm-ktm-950-super-enduro-r-the-regulator-fails-by-overcharging

### known_issues rowid 873

**row_key**

- before: None
- after:  ktm-ktm-lc8-charging-fault-with-a-metallic-noise-from-the

### known_issues rowid 874

**row_key**

- before: None
- after:  aprilia-aprilia-v4-charging-failure-the-flywheel-is-the-first

### known_issues rowid 875

**row_key**

- before: None
- after:  bmw-bmw-boxer-startup-clack-is-normal-the-opposite-call-to-the

### known_issues rowid 876

**row_key**

- before: None
- after:  ktm-ktm-690-lc4-valve-train-failure-is-the-roller-rocker-bearing

### known_issues rowid 877

**row_key**

- before: None
- after:  moto-guzzi-moto-guzzi-1200-8v-whether-an-engine-has-flat-or-roller

### known_issues rowid 878

**row_key**

- before: None
- after:  triumph-triumph-955i-warm-high-idle-or-stalling-is-usually-an-air

### known_issues rowid 879

**row_key**

- before: None
- after:  bmw-bmw-can-bus-with-the-zfe-module-has-no-fuses-to-pull-and-an

### known_issues rowid 880

**row_key**

- before: None
- after:  bmw-bmw-hexhead-final-drive-crown-bearing-sealed-and-greased

### known_issues rowid 881

**row_key**

- before: None
- after:  ducati-ducati-desmoquattro-glitter-in-the-oil-means-look-at-the

### known_issues rowid 882

**row_key**

- before: None
- after:  ktm-ktm-lc8-water-pump-seal-is-a-scheduled-part-with-casting

### known_issues rowid 883

**row_key**

- before: None
- after:  ktm-ktm-lc8-with-an-oily-front-intake-and-a-rich-front-cylinder

### known_issues rowid 884

**row_key**

- before: None
- after:  mv-agusta-on-most-european-makes-the-same-engine-gets-the-same-valve

### known_issues rowid 885

**row_key**

- before: None
- after:  ktm-ktm-s-390-valve-interval-difference-is-373cc-versus-399cc

### known_issues rowid 886

**row_key**

- before: None
- after:  bmw-european-valve-intervals-move-by-engine-generation-not-by

### known_issues rowid 887

**row_key**

- before: None
- after:  bmw-no-european-valve-row-opened-carries-a-time-trigger-due-by

### known_issues rowid 888

**row_key**

- before: None
- after:  all-european-makes-five-valve-train-job-types-across-the-european-makes-and-the

### known_issues rowid 889

**row_key**

- before: None
- after:  ducati-ducati-publishes-its-desmo-labour-in-six-minute-units-and

### known_issues rowid 890

**row_key**

- before: None
- after:  ktm-ktm-publishes-service-minutes-and-the-valve-service-is-fifty

### known_issues rowid 891

**row_key**

- before: None
- after:  triumph-triumph-s-own-check-sheet-bills-the-valve-check-and-the

### known_issues rowid 892

**row_key**

- before: None
- after:  aprilia-aprilia-s-trust-aprilia-maintenance-sheets-omit-the-valve

### known_issues rowid 893

**row_key**

- before: None
- after:  mv-agusta-mv-agusta-s-coupon-ladder-starts-with-a-merged-cell-and

### known_issues rowid 894

**row_key**

- before: None
- after:  mv-agusta-the-mv-agusta-f4-shim-diameter-is-still-in-no-manufacturer

### known_issues rowid 895

**row_key**

- before: None
- after:  ducati-ducati-s-60-000-and-45-000-km-intervals-belong-to-spring

### known_issues rowid 896

**row_key**

- before: None
- after:  moto-guzzi-moto-guzzi-s-two-current-engines-take-opposite-valve-jobs

### known_issues rowid 897

**row_key**

- before: None
- after:  moto-guzzi-moto-guzzi-1200-8v-roller-tappet-kits-are-released-only

### known_issues rowid 898

**row_key**

- before: None
- after:  mv-agusta-no-mv-agusta-rim-band-part-could-be-established-the

### known_issues rowid 899

**row_key**

- before: None
- after:  aprilia-the-aprilia-v4-charging-system-exists-in-two-families-and

### known_issues rowid 900

**row_key**

- before: None
- after:  bmw-bmw-supplies-the-hexhead-final-drive-only-as-a-complete-unit

### known_issues rowid 901

**row_key**

- before: None
- after:  ducati-the-ducati-desmoquattro-opening-rocker-arm-is-discontinued

### known_issues rowid 902

**row_key**

- before: None
- after:  triumph-triumph-s-fiche-does-not-itemise-the-street-triple-idle

### known_issues rowid 903

**row_key**

- before: None
- after:  ktm-ktm-adventure-tubeless-rim-seal-bands-and-bead-gaskets-are

### known_issues rowid 904

**row_key**

- before: None
- after:  ktm-the-ktm-lc8-fiche-pages-for-the-balancer-seal-and-starter

### known_issues rowid 905

**row_key**

- before: None
- after:  aprilia-aprilia-and-moto-guzzi-share-one-parts-catalogue-one

### known_issues rowid 906

**row_key**

- before: None
- after:  bmw-the-bmw-elast-belt-designation-disagreement-has-an

### known_issues rowid 907

**row_key**

- before: None
- after:  moto-guzzi-the-moto-guzzi-small-block-oil-filter-has-no-hiflo-cross

### known_issues rowid 908

**row_key**

- before: None
- after:  bmw-supports-bmw-in-tuneecu-means-one-449cc-enduro-single-and

### known_issues rowid 909

**row_key**

- before: None
- after:  ducati-tuneecu-scopes-ducati-by-ecu-part-number-rather-than-by

### known_issues rowid 910

**row_key**

- before: None
- after:  ktm-tuneecu-s-capability-degrades-differently-on-ktm-and-triumph

### known_issues rowid 911

**row_key**

- before: None
- after:  ducati-and-mv-agusta-ducati-and-mv-agusta-have-no-dealer-tool-lockout-texa

### known_issues rowid 912

**row_key**

- before: None
- after:  bmw-and-ducati-have-texa-lists-coding-and-adaptation-functions-for-two-european

### known_issues rowid 913

**row_key**

- before: None
- after:  all-european-makes-texa-s-entry-tier-idc5-basic-licence-contains-no-european

### known_issues rowid 914

**row_key**

- before: None
- after:  bmw-bmw-s-gs-911-is-unavoidable-and-its-enthusiast-tier-is

### known_issues rowid 915

**row_key**

- before: None
- after:  aprilia-and-moto-guzzi-aprilia-and-moto-guzzi-share-one-dealer-tool-pads-and-one

### known_issues rowid 916

**row_key**

- before: None
- after:  aprilia-and-moto-guzzi-diagcode-covers-only-the-piaggio-group-but-exceeds-the

### known_issues rowid 917

**row_key**

- before: None
- after:  ducati-obdstar-s-iscan-catalogue-looks-multi-brand-but-the-hardware

### known_issues rowid 918

**row_key**

- before: None
- after:  bmw-ducati-aprilia-and-moto-guzzi-share-one-3-pin-plug-while-ktm

### known_issues rowid 919

**row_key**

- before: None
- after:  triumph-triumph-is-the-european-connector-outlier-it-had-the-16-pin

### known_issues rowid 920

**row_key**

- before: None
- after:  all-makes-a-vendor-s-own-if-it-is-not-listed-it-is-not-compatible-line

### known_issues rowid 1271

**row_key**

- before: None
- after:  ktm-which-1290-you-have-super-duke-r-super-duke-gt-super

### known_issues rowid 1272

**row_key**

- before: None
- after:  ktm-msc-on-a-1290-is-a-bosch-supplier-system-not-a-ktm-in-house

### known_issues rowid 1273

**row_key**

- before: None
- after:  ktm-abs-and-ride-mode-returning-to-default-at-every-key-cycle-on

### known_issues rowid 1274

**row_key**

- before: None
- after:  ktm-offroad-abs-on-a-super-adventure-r-is-reduced-intervention

### known_issues rowid 1275

**row_key**

- before: None
- after:  ktm-after-a-drop-a-1290-can-ride-normally-while-the-lean

### known_issues rowid 1276

**row_key**

- before: None
- after:  ktm-wheel-speed-sensing-on-a-super-adventure-r-s-21-inch-spoked

### known_issues rowid 1277

**row_key**

- before: None
- after:  ktm-adventure-and-super-adventure-are-different-ktm-machines-and

### known_issues rowid 1278

**row_key**

- before: None
- after:  ktm-the-mid-size-adventure-runs-dry-with-fuel-still-showing-and

### known_issues rowid 1279

**row_key**

- before: None
- after:  ktm-the-ktm-adventure-fuel-gauge-reading-full-for-the-first-half

### known_issues rowid 1280

**row_key**

- before: None
- after:  ktm-the-abs-module-on-the-mid-size-ktm-adventure-sits-under-the

### known_issues rowid 1281

**row_key**

- before: None
- after:  ktm-the-mid-size-adventure-fuel-pump-sits-low-and-exposed-and

### known_issues rowid 1282

**row_key**

- before: None
- after:  ktm-the-ktm-950-990-subframe-cracking-reputation-does-not-belong

### known_issues rowid 1283

**row_key**

- before: None
- after:  ktm-the-adventure-s-tubeless-spoked-wheels-seal-on-a-rim-band

### known_issues rowid 1284

**row_key**

- before: None
- after:  ktm-the-adventure-and-its-duke-sibling-share-an-engine-and-its

### known_issues rowid 1285

**row_key**

- before: None
- after:  ktm-the-mid-size-adventure-recalls-are-brakes-and-one-tyre

### known_issues rowid 1286

**row_key**

- before: None
- after:  ktm-where-a-mid-size-ktm-adventure-was-built-depends-on-model

### known_issues rowid 1287

**row_key**

- before: None
- after:  ktm-the-lc8c-in-a-790-or-890-duke-is-a-parallel-twin-not-a-v

### known_issues rowid 1288

**row_key**

- before: None
- after:  ktm-the-125-and-390-duke-are-built-in-india-by-bajaj-what-that

### known_issues rowid 1289

**row_key**

- before: None
- after:  ktm-a-390-duke-and-an-rc-390-share-an-engine-but-not-a-chassis

### known_issues rowid 1290

**row_key**

- before: None
- after:  ktm-a-690-duke-is-the-road-naked-sharing-the-lc4-big-single-with

### known_issues rowid 1291

**row_key**

- before: None
- after:  ktm-an-lc8c-idles-and-pulls-with-an-uneven-beat-by-design

### known_issues rowid 1292

**row_key**

- before: None
- after:  ktm-which-engine-management-supplier-your-ktm-has-decides-which

### known_issues rowid 1293

**row_key**

- before: None
- after:  ktm-tuneecu-reaches-keihin-era-ktms-only-tuneboy-is-a-tune

### known_issues rowid 1294

**row_key**

- before: None
- after:  ktm-a-ktm-dash-never-shows-a-numeric-fault-code-pre-tft-bikes

### known_issues rowid 1295

**row_key**

- before: None
- after:  ktm-a-generic-scanner-s-label-for-a-p1xxx-code-on-a-ktm-is-not

### known_issues rowid 1296

**row_key**

- before: None
- after:  ktm-immobiliser-no-start-on-a-ktm-shows-as-dash-text-not-a-p

### known_issues rowid 1297

**row_key**

- before: None
- after:  ktm-throttle-adaptation-on-a-ktm-a-documented-post-map-load

### known_issues rowid 1298

**row_key**

- before: None
- after:  ktm-ktm-powerparts-exhaust-maps-are-dealer-installed-and-exhaust

### known_issues rowid 1299

**row_key**

- before: None
- after:  ktm-a-tpi-two-stroke-runs-an-oil-pump-not-premix-and-both-halves

### known_issues rowid 1300

**row_key**

- before: None
- after:  ktm-exc-is-a-two-stroke-and-exc-f-is-a-four-stroke-one-letter

### known_issues rowid 1301

**row_key**

- before: None
- after:  ktm-exc-and-exc-f-service-is-counted-in-engine-hours-not-miles-a

### known_issues rowid 1302

**row_key**

- before: None
- after:  ktm-a-top-end-on-a-250-or-300-exc-is-maintenance-not-a-failure

### known_issues rowid 1303

**row_key**

- before: None
- after:  ktm-the-exhaust-power-valve-on-a-250-or-300-exc-carbons-up-and

### known_issues rowid 1304

**row_key**

- before: None
- after:  ktm-a-690-enduro-r-is-a-road-legal-enduro-not-a-competition-bike

### known_issues rowid 1305

**row_key**

- before: None
- after:  ktm-ktm-s-engine-prefixes-name-three-architectures-not-one

### known_issues rowid 1306

**row_key**

- before: None
- after:  ktm-within-the-lc8-the-generation-matters-as-much-as-the-family

### known_issues rowid 1307

**row_key**

- before: None
- after:  ktm-on-an-lc8-the-cylinders-are-front-and-rear-not-left-and

### known_issues rowid 1308

**row_key**

- before: None
- after:  ktm-cam-chain-starter-clutch-and-valve-clearance-faults-on-an

### known_issues rowid 1309

**row_key**

- before: None
- after:  harley-davidson-the-livewire-has-no-thermostat-as-a-service-item-its-one

### known_issues rowid 1310

**row_key**

- before: None
- after:  harley-davidson-livewire-coolant-is-replaced-once-at-50-000-mi-by-a-dealer

### known_issues rowid 1311

**row_key**

- before: None
- after:  harley-davidson-a-livewire-service-is-inspections-and-torque-checks-there-is

### known_issues rowid 1312

**row_key**

- before: None
- after:  harley-davidson-single-speed-gearbox-no-clutch-and-a-belt-with-its-own

### known_issues rowid 1313

**row_key**

- before: None
- after:  harley-davidson-a-livewire-one-on-a-level-2-charger-charges-at-the-level-1

### known_issues rowid 1314

**row_key**

- before: None
- after:  harley-davidson-livewire-publishes-its-own-charging-best-practice-and-a-20

### known_issues rowid 1315

**row_key**

- before: None
- after:  harley-davidson-the-2020-livewire-onboard-charger-software-campaign-can-shut

### known_issues rowid 1316

**row_key**

- before: None
- after:  harley-davidson-no-regulator-record-could-be-established-for-the-livewire

### known_issues rowid 1317

**row_key**

- before: None
- after:  harley-davidson-the-badge-changes-at-2021-and-so-does-the-dealer-the

### known_issues rowid 1318

**row_key**

- before: None
- after:  harley-davidson-the-livewire-diagnostic-connector-is-a-6-pin-can-link-and

### known_issues rowid 1319

**row_key**

- before: None
- after:  harley-davidson-livewire-connect-telematics-was-discontinued-in-december

### known_issues rowid 1320

**row_key**

- before: None
- after:  harley-davidson-the-livewire-onboard-charger-fails-as-a-unit-and-its-failure

### known_issues rowid 1321

**row_key**

- before: None
- after:  harley-davidson-owner-reported-livewire-trouble-spots-cluster-delamination

### known_issues rowid 1322

**row_key**

- before: None
- after:  harley-davidson-the-livewire-shows-its-own-trouble-codes-without-a-dealer

### known_issues rowid 1323

**row_key**

- before: None
- after:  mv-agusta-radial-valve-on-an-mv-agusta-f4-describes-where-the-valves

### known_issues rowid 1324

**row_key**

- before: None
- after:  mv-agusta-measure-an-mv-agusta-f4-shim-before-ordering-a-kit-the

### known_issues rowid 1325

**row_key**

- before: None
- after:  mv-agusta-mv-four-cylinder-model-numbers-are-wrong-in-both-directions

### known_issues rowid 1326

**row_key**

- before: None
- after:  mv-agusta-an-mv-agusta-f4-valve-interval-is-short-by-superbike

### known_issues rowid 1327

**row_key**

- before: None
- after:  mv-agusta-what-an-independent-shop-can-and-cannot-do-on-an-mv-agusta

### known_issues rowid 1328

**row_key**

- before: None
- after:  mv-agusta-the-mv-triple-s-crankshaft-turns-backwards-so-turn-it-in-the

### known_issues rowid 1329

**row_key**

- before: None
- after:  mv-agusta-the-mv-triple-s-starter-clutch-is-handed-for-reverse

### known_issues rowid 1330

**row_key**

- before: None
- after:  mv-agusta-two-mv-triple-recalls-are-do-not-ride-and-one-of-them-cannot

### known_issues rowid 1331

**row_key**

- before: None
- after:  mv-agusta-the-us-scope-of-the-mv-agusta-fork-recall-understates-the

### known_issues rowid 1332

**row_key**

- before: None
- after:  mv-agusta-mv-triple-service-intervals-must-come-from-the-specific

### known_issues rowid 1463

**row_key**

- before: None
- after:  triumph-alternator-to-harness-connector-overheating-on-the-t100-t120

### known_issues rowid 1464

**row_key**

- before: None
- after:  triumph-clutch-cable-chafing-the-main-harness-at-the-headstock-on

### known_issues rowid 1465

**row_key**

- before: None
- after:  triumph-starter-cable-against-the-oil-cooler-return-pipe-on-early

### known_issues rowid 1466

**row_key**

- before: None
- after:  triumph-a-bonneville-model-name-spans-up-to-three-different-engines

### known_issues rowid 1467

**row_key**

- before: None
- after:  triumph-an-air-cooled-efi-bonneville-still-looks-carburetted-the

### known_issues rowid 1468

**row_key**

- before: None
- after:  triumph-telling-a-790-from-an-865-by-engine-number-works-on-the-t100

### known_issues rowid 1469

**row_key**

- before: None
- after:  triumph-crank-angle-on-the-bonneville-family-is-not-the-air-cooled

### known_issues rowid 1470

**row_key**

- before: None
- after:  triumph-the-bonneville-valve-job-changed-completely-in-2016-cams-out

### known_issues rowid 1471

**row_key**

- before: None
- after:  triumph-liquid-cooled-1200-throttles-cannot-be-balanced-with-vacuum

### known_issues rowid 1472

**row_key**

- before: None
- after:  triumph-the-t120-and-street-twin-cooling-system-hides-in-plain-sight

### known_issues rowid 1473

**row_key**

- before: None
- after:  triumph-air-cooled-bonneville-starter-and-wheel-faults-that-never

### known_issues rowid 1474

**row_key**

- before: None
- after:  triumph-a-flashing-triumph-warning-lamp-means-an-identity-or

### known_issues rowid 1475

**row_key**

- before: None
- after:  triumph-the-triumph-diagnostic-socket-looks-like-obd-ii-but-does-not

### known_issues rowid 1476

**row_key**

- before: None
- after:  triumph-a-carburetted-air-cooled-bonneville-has-no-diagnostic

### known_issues rowid 1477

**row_key**

- before: None
- after:  triumph-tuneecu-tuneboy-and-dealertool-all-cover-triumph-and

### known_issues rowid 1478

**row_key**

- before: None
- after:  triumph-triumph-documents-no-dash-diagnostic-mode-the-button

### known_issues rowid 1479

**row_key**

- before: None
- after:  triumph-the-tiger-900-and-2022-on-tiger-1200-fire-unevenly-by-design

### known_issues rowid 1480

**row_key**

- before: None
- after:  triumph-tiger-900-names-two-unrelated-motorcycles-thirty-years-apart

### known_issues rowid 1481

**row_key**

- before: None
- after:  triumph-only-the-tiger-1200s-are-shaft-drive-and-the-shaft-layout

### known_issues rowid 1482

**row_key**

- before: None
- after:  triumph-tiger-valve-intervals-split-12-000-versus-20-000-miles-by

### known_issues rowid 1483

**row_key**

- before: None
- after:  triumph-tiger-first-service-mileages-are-not-all-the-same-500-miles

### known_issues rowid 1484

**row_key**

- before: None
- after:  triumph-tiger-1200-front-brake-pads-recalled-for-corrosion-the

### known_issues rowid 1485

**row_key**

- before: None
- after:  triumph-early-tiger-800-recalls-include-a-deceleration-stall-from

### known_issues rowid 1486

**row_key**

- before: None
- after:  triumph-tiger-explorer-recalls-a-throttle-butterfly-that-can-deviate

### known_issues rowid 1487

**row_key**

- before: None
- after:  triumph-the-manifold-pressure-hose-stall-recall-is-a-tiger-sport-660

### known_issues rowid 1488

**row_key**

- before: None
- after:  triumph-tiger-cylinder-head-bolts-must-be-oil-lubricated-on-the

### known_issues rowid 1489

**row_key**

- before: None
- after:  triumph-xr-and-xc-gt-and-rally-describe-wheels-and-suspension-not

### known_issues rowid 1490

**row_key**

- before: None
- after:  triumph-the-daytona-675-and-street-triple-675-shared-an-engine-only

### known_issues rowid 1491

**row_key**

- before: None
- after:  triumph-the-daytona-is-a-faired-supersport-not-a-naked-it-sits

### known_issues rowid 1492

**row_key**

- before: None
- after:  triumph-street-triple-names-a-675-and-a-765-the-engine-changed-in

### known_issues rowid 1493

**row_key**

- before: None
- after:  triumph-the-speed-triple-went-from-1050-to-1200-and-the-name-carried

### known_issues rowid 1494

**row_key**

- before: None
- after:  triumph-s-r-and-rs-mostly-describe-chassis-and-equipment-but-the

### known_issues rowid 1495

**row_key**

- before: None
- after:  triumph-two-separate-2013-speed-triple-transmission-recalls-and-the

### known_issues rowid 1496

**row_key**

- before: None
- after:  triumph-the-speed-triple-1200-s-second-radiator-fan-recall-exists

### known_issues rowid 1497

**row_key**

- before: None
- after:  triumph-there-is-no-cam-or-valve-gear-recall-on-the-675-what-gets

### known_issues rowid 1498

**row_key**

- before: None
- after:  triumph-triple-sport-valve-intervals-are-12-000-miles-across-the

### known_issues rowid 1499

**row_key**

- before: None
- after:  triumph-a-street-triple-can-lose-anti-lock-braking-without-lighting

### known_issues rowid 1500

**row_key**

- before: None
- after:  triumph-daytona-675-charging-failures-a-regulator-rectifier-recall

### known_issues rowid 1501

**row_key**

- before: None
- after:  triumph-a-meriden-triumph-carries-several-unrelated-british-thread

### known_issues rowid 1502

**row_key**

- before: None
- after:  triumph-meriden-triumphs-are-positive-earth-through-1978-assuming

### known_issues rowid 1503

**row_key**

- before: None
- after:  triumph-on-an-oil-in-frame-triumph-the-frame-is-the-oil-tank-so-a

### known_issues rowid 1504

**row_key**

- before: None
- after:  triumph-there-is-no-oil-filter-to-change-on-a-meriden-twin

### known_issues rowid 1505

**row_key**

- before: None
- after:  triumph-a-360-degree-meriden-twin-runs-wasted-spark-so-a-dead

### known_issues rowid 1506

**row_key**

- before: None
- after:  triumph-on-an-amal-carburettor-the-pilot-screw-is-an-air-screw

### known_issues rowid 1507

**row_key**

- before: None
- after:  triumph-vibration-on-a-360-degree-twin-is-designed-in-and-it-is-the

### known_issues rowid 1508

**row_key**

- before: None
- after:  triumph-on-an-early-hinckley-triumph-the-badge-is-not-the-capacity

### known_issues rowid 1509

**row_key**

- before: None
- after:  triumph-t595-is-a-project-code-not-a-capacity-the-t595-daytona-is-a

### known_issues rowid 1510

**row_key**

- before: None
- after:  triumph-carburetted-and-injected-early-hinckley-triumphs-share-model

### known_issues rowid 1511

**row_key**

- before: None
- after:  triumph-a-mid-nineties-hinckley-speed-triple-t309-may-be-a-five

### known_issues rowid 1512

**row_key**

- before: None
- after:  triumph-early-hinckley-recalls-include-a-frame-headstock-weld-and-a

### known_issues rowid 1513

**row_key**

- before: None
- after:  triumph-hinckley-fasteners-are-metric-throughout-the-clean-break

### known_issues rowid 1614

**row_key**

- before: None
- after:  zero-identify-the-zero-platform-before-quoting-anything-pack

### known_issues rowid 1615

**row_key**

- before: None
- after:  zero-cypher-ii-or-cypher-iii-decides-which-procedures-and-which

### known_issues rowid 1616

**row_key**

- before: None
- after:  zero-zero-belt-tension-is-specified-by-frequency-and-the-window

### known_issues rowid 1617

**row_key**

- before: None
- after:  zero-zero-belt-care-is-a-cleaning-and-inspection-routine-not-an

### known_issues rowid 1618

**row_key**

- before: None
- after:  zero-zero-s-published-service-schedule-is-short-and-front-loaded

### known_issues rowid 1619

**row_key**

- before: None
- after:  zero-a-zero-left-standing-needs-a-charging-regime-and-a-fully

### known_issues rowid 1620

**row_key**

- before: None
- after:  zero-zero-warrants-the-motorcycle-and-the-power-pack-on-different

### known_issues rowid 1621

**row_key**

- before: None
- after:  zero-a-zero-is-not-an-obd-ii-vehicle-the-codes-are-on-the-dash

### known_issues rowid 1622

**row_key**

- before: None
- after:  zero-the-zero-app-is-the-owner-s-diagnostic-surface-and-what-it

### known_issues rowid 1623

**row_key**

- before: None
- after:  zero-zero-firmware-is-a-service-item-with-published-release-notes

### known_issues rowid 1624

**row_key**

- before: None
- after:  zero-zero-s-charging-accessories-are-dealer-installed-and-change

### known_issues rowid 1625

**row_key**

- before: None
- after:  zero-two-zero-campaigns-are-stop-riding-campaigns-the-2012-pack

### known_issues rowid 1626

**row_key**

- before: None
- after:  zero-zero-battery-campaigns-split-by-model-and-the-remedies-are

### known_issues rowid 1627

**row_key**

- before: None
- after:  zero-the-2014-zero-motor-campaign-is-screened-per-model-the-build

### known_issues rowid 1628

**row_key**

- before: None
- after:  zero-two-zero-brake-campaigns-and-neither-presents-the-way-a

### known_issues rowid 1629

**row_key**

- before: None
- after:  zero-the-zero-key-switch-wiring-campaign-is-fixed-by-firmware-not

### known_issues rowid 1630

**row_key**

- before: None
- after:  zero-the-zero-s-16-pin-socket-is-not-an-obd-ii-port-and-the

### known_issues rowid 4541

**row_key**

- before: None
- after:  zero-cell-balancing-is-automatic-on-every-make-what-the-bms-shows

### known_issues rowid 4542

**row_key**

- before: None
- after:  zero-reading-cell-spread-from-a-zero-bms-log-the-community-bands

### known_issues rowid 4543

**row_key**

- before: None
- after:  zero-state-of-health-is-a-dealer-tool-number-on-every-make-what

### known_issues rowid 4544

**row_key**

- before: None
- after:  zero-estimating-a-zero-pack-s-usable-capacity-from-its-own-logs

### known_issues rowid 4545

**row_key**

- before: None
- after:  zero-no-electric-motorcycle-maker-publishes-a-voltage-to-state-of

### known_issues rowid 4546

**row_key**

- before: None
- after:  zero-thermal-derating-is-the-bms-refusing-charge-or-discharge-at

### known_issues rowid 4547

**row_key**

- before: None
- after:  zero-no-electric-motorcycle-maker-exposes-a-cycle-counter-what

### known_issues rowid 4548

**row_key**

- before: None
- after:  zero-what-the-motor-controller-is-on-each-make-a-name-and-a

### known_issues rowid 4549

**row_key**

- before: None
- after:  zero-how-a-motor-controller-fault-reaches-the-rider-on-each-make

### known_issues rowid 4550

**row_key**

- before: None
- after:  zero-no-electric-motorcycle-maker-publishes-an-overcurrent-phase

### known_issues rowid 4551

**row_key**

- before: None
- after:  zero-controller-firmware-is-a-service-item-on-every-make-and-none

### known_issues rowid 4552

**row_key**

- before: None
- after:  zero-what-reads-the-motor-controller-on-each-make-zero-s-dealer

### known_issues rowid 4553

**row_key**

- before: None
- after:  zero-zero-s-two-2025-controller-recalls-a-motor-controller

### known_issues rowid 4554

**row_key**

- before: None
- after:  harley-davidson-livewire-s-powertrain-shutdown-recalls-are-software-in-the

### known_issues rowid 4555

**row_key**

- before: None
- after:  zero-what-a-zero-s-own-logs-hold-about-the-motor-controller-per

### known_issues rowid 4556

**row_key**

- before: None
- after:  zero-what-the-rider-can-set-for-regen-on-each-make-named-modes

### known_issues rowid 4557

**row_key**

- before: None
- after:  zero-off-throttle-regen-and-coasting-on-each-make-a-drag-on-a

### known_issues rowid 4558

**row_key**

- before: None
- after:  zero-does-regen-light-the-brake-lamp-yes-above-an-unpublished

### known_issues rowid 4559

**row_key**

- before: None
- after:  zero-no-electric-motorcycle-maker-offers-a-one-pedal-stop-every

### known_issues rowid 4560

**row_key**

- before: None
- after:  zero-when-regen-is-limited-or-cut-on-each-make-a-full-pack-a-cold

### known_issues rowid 4561

**row_key**

- before: None
- after:  zero-where-regen-is-set-and-read-on-each-make-the-dash-the-app

### known_issues rowid 4562

**row_key**

- before: None
- after:  zero-what-a-zero-does-with-regen-on-a-full-pack-per-the-community

### known_issues rowid 4563

**row_key**

- before: None
- after:  zero-nothing-on-any-make-is-documented-as-a-liquid-cooled-battery

### known_issues rowid 4564

**row_key**

- before: None
- after:  zero-motor-and-controller-temperature-on-each-make-a-gauge-with

### known_issues rowid 4565

**row_key**

- before: None
- after:  zero-the-cooling-loop-s-own-faults-and-service-on-each-make-pump

### known_issues rowid 4566

**row_key**

- before: None
- after:  zero-ambient-heat-and-cold-on-each-make-what-the-manuals-say

### known_issues rowid 4567

**row_key**

- before: None
- after:  vespa-the-hpe-engine-moved-the-drive-belt-interval-from-15-000-km

### known_issues rowid 4568

**row_key**

- before: None
- after:  vespa-vespa-and-piaggio-manuals-are-vin-gated-or-dealer-only-what

### known_issues rowid 4569

**row_key**

- before: None
- after:  vespa-piaggio-calls-it-the-obd-port-but-it-is-a-six-pin-piaggio

### known_issues rowid 4570

**row_key**

- before: None
- after:  piaggio-the-mp3-roll-lock-engages-only-on-four-conditions-at-once

### known_issues rowid 4571

**row_key**

- before: None
- after:  piaggio-servicing-the-mp3-roll-lock-a-three-step-reset-four-test

### known_issues rowid 4572

**row_key**

- before: None
- after:  vespa-four-brake-campaigns-one-supplier-and-two-different-platings

### known_issues rowid 4573

**row_key**

- before: None
- after:  vespa-a-vespa-recall-caused-by-servicing-reusing-the-exhaust

### known_issues rowid 4574

**row_key**

- before: None
- after:  vespa-what-the-us-regulator-record-covers-for-these-machines-and

### known_issues rowid 4575

**row_key**

- before: None
- after:  piaggio-the-cvt-wear-limits-piaggio-publishes-for-its-scooters-and

### known_issues rowid 4576

**row_key**

- before: None
- after:  vespa-engine-family-names-as-piaggio-writes-them-i-get-hpe-and-hi

### known_issues rowid 4577

**row_key**

- before: None
- after:  honda-honda-s-two-50-cm3-scooters-are-opposite-machines-the-ruckus

### known_issues rowid 4578

**row_key**

- before: None
- after:  honda-what-changed-between-ruckus-editions-two-separate-oil-spec

### known_issues rowid 4579

**row_key**

- before: None
- after:  honda-a-grom-fault-above-1800-rpm-shows-as-a-steady-lamp-not-a

### known_issues rowid 4580

**row_key**

- before: None
- after:  honda-the-eleven-codes-a-grom125-can-show-and-the-one-pair-honda

### known_issues rowid 4581

**row_key**

- before: None
- after:  honda-in-model-year-2022-the-grom-and-the-trail-125-ran-different

### known_issues rowid 4582

**row_key**

- before: None
- after:  honda-grom-service-data-that-belongs-only-to-the-pre-2022-four

### known_issues rowid 4583

**row_key**

- before: None
- after:  honda-the-pcx-changed-displacement-three-times-in-five-years-and-a

### known_issues rowid 4584

**row_key**

- before: None
- after:  honda-honda-s-current-owner-s-manuals-stopped-carrying-torque

### known_issues rowid 4585

**row_key**

- before: None
- after:  honda-a-completed-grom-fuel-pump-recall-is-not-proof-of-a-repaired

### known_issues rowid 4586

**row_key**

- before: None
- after:  honda-the-metropolitan-transmission-campaign-covers-ten-model

### known_issues rowid 4587

**row_key**

- before: None
- after:  honda-two-minimoto-campaigns-that-are-easy-to-misread-one-is-a

### known_issues rowid 4588

**row_key**

- before: None
- after:  honda-what-the-us-regulator-record-shows-for-honda-s-small

### known_issues rowid 4589

**row_key**

- before: None
- after:  honda-what-honda-s-own-documents-say-about-modifying-a-grom-four

### known_issues rowid 4590

**row_key**

- before: None
- after:  yamaha-one-yamaha-scooter-nameplate-covers-three-different-engines

### known_issues rowid 4591

**row_key**

- before: None
- after:  yamaha-yamaha-prints-the-same-v-belt-interval-three-different-ways

### known_issues rowid 4592

**row_key**

- before: None
- after:  yamaha-a-yamaha-scooter-names-itself-only-in-some-model-years-so

### known_issues rowid 4593

**row_key**

- before: None
- after:  kymco-kymco-and-sym-publish-owner-s-manuals-and-outsource

### known_issues rowid 4594

**row_key**

- before: None
- after:  kymco-kymco-s-own-product-page-serves-a-2009-carburetted-manual

### known_issues rowid 4595

**row_key**

- before: None
- after:  sym-a-sym-manual-tells-you-to-change-the-oil-three-times-more

### known_issues rowid 4596

**row_key**

- before: None
- after:  kymco-kymco-and-sym-do-show-fault-codes-on-the-dash-under-names-no

### known_issues rowid 4597

**row_key**

- before: None
- after:  genuine-who-builds-a-genuine-scooter-is-answerable-as-a-chain-of

### known_issues rowid 4598

**row_key**

- before: None
- after:  genuine-a-genuine-vin-may-not-decode-at-all-and-one-of-its-manuals

### known_issues rowid 4599

**row_key**

- before: None
- after:  genuine-what-genuine-publishes-free-what-it-gates-and-a-warranty

### known_issues rowid 4600

**row_key**

- before: None
- after:  kymco-kymco-s-us-campaigns-include-an-engine-replaced-whole-two

### known_issues rowid 4601

**row_key**

- before: None
- after:  genuine-genuine-s-electric-scooter-carries-two-campaigns-at-once

### known_issues rowid 4602

**row_key**

- before: None
- after:  yamaha-yamaha-s-scooter-campaigns-include-a-drain-bolt-that-can

### known_issues rowid 4603

**row_key**

- before: None
- after:  yamaha-the-regulator-s-own-index-under-lists-these-machines-against

### known_issues rowid 4604

**row_key**

- before: None
- after:  piaggio-what-a-scooter-cvt-is-in-the-makers-own-words-and-why

### known_issues rowid 4605

**row_key**

- before: None
- after:  piaggio-three-unrelated-components-are-all-called-a-drive-belt-and-a

### known_issues rowid 4606

**row_key**

- before: None
- after:  piaggio-every-maker-publishes-a-roller-wear-limit-in-a-service

### known_issues rowid 4607

**row_key**

- before: None
- after:  piaggio-the-clutch-side-one-maker-publishes-an-engagement-speed-one

### known_issues rowid 4608

**row_key**

- before: None
- after:  piaggio-no-scooter-owner-s-manual-publishes-a-belt-width-or-wear

### known_issues rowid 4609

**row_key**

- before: None
- after:  kymco-a-kymco-service-manual-gives-four-cvt-figures-twice-with

### known_issues rowid 4610

**row_key**

- before: None
- after:  piaggio-what-the-makers-themselves-say-a-cvt-symptom-means-quoted

### known_issues rowid 4611

**row_key**

- before: None
- after:  piaggio-kickstart-backup-and-the-scooter-named-kick-that-has-none

### known_issues rowid 4612

**row_key**

- before: None
- after:  piaggio-no-maker-publishes-a-fault-code-for-a-cvt-the-transmission

### known_issues rowid 4613

**row_key**

- before: None
- after:  piaggio-piaggio-s-belt-limit-is-three-different-numbers-and-one

### known_issues rowid 4614

**row_key**

- before: None
- after:  yamaha-a-cvt-recall-exists-that-no-belt-pulley-or-variator-search

### known_issues rowid 4615

**row_key**

- before: None
- after:  yamaha-what-the-regulator-record-shows-for-scooter-cvts-one

### known_issues rowid 4616

**row_key**

- before: None
- after:  yamaha-the-regulator-s-two-indexes-contradict-each-other-and-an

### known_issues rowid 5337

**row_key**

- before: None
- after:  honda-on-a-honda-pcx150-the-alternator-is-also-the-starter-and-the

### known_issues rowid 5338

**row_key**

- before: None
- after:  honda-honda-s-carburetted-chf50-charges-through-a-three-phase

### known_issues rowid 5339

**row_key**

- before: None
- after:  kymco-two-kymco-service-manuals-two-opposite-charging-systems-the

### known_issues rowid 5340

**row_key**

- before: None
- after:  sym-one-sym-manual-gives-the-jet-50-100-an-illumination-coil-and

### known_issues rowid 5341

**row_key**

- before: None
- after:  piaggio-piaggio-s-fly-50-is-single-phase-while-the-fly-125-beverly

### known_issues rowid 5342

**row_key**

- before: None
- after:  vespa-vespa-s-50-cc-regulator-is-tested-with-the-lights-on-and-off

### known_issues rowid 5343

**row_key**

- before: None
- after:  yamaha-yamaha-s-yw125-service-manual-gives-two-stator-resistances-a

### known_issues rowid 6397

**row_key**

- before: None
- after:  honda-honda-s-chf50-carburettor-a-factory-pre-set-pilot-screw

### known_issues rowid 6398

**row_key**

- before: None
- after:  honda-honda-ruckus-owner-s-manuals-idle-speed-is-the-only

### known_issues rowid 6399

**row_key**

- before: None
- after:  kymco-kymco-agility-50-and-people-s-250-carburettors-record-the

### known_issues rowid 6400

**row_key**

- before: None
- after:  sym-sym-carburetted-scooters-the-auto-by-starter-is-checked-by

### known_issues rowid 6401

**row_key**

- before: None
- after:  piaggio-piaggio-s-small-carburetted-scooters-the-mixture-screw-is

### known_issues rowid 6402

**row_key**

- before: None
- after:  vespa-vespa-s-small-carburetted-scooters-dell-orto-on-the-two

### known_issues rowid 6403

**row_key**

- before: None
- after:  yamaha-yamaha-s-carburetted-scooters-owner-s-manuals-leave
## schema_version: +1 added, 0 changed, 0 removed
- added rowid 84: (85, '2026-10-08 19:32:26')
