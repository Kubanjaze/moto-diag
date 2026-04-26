# Track G Research Brief: Parts/Labor Pricing & Sourcing

Research for Phases 166 (AI parts sourcing) + 167 (AI labor estimation) + 171 (shop analytics — future).
Source: Domain-Researcher-Pricing agent. Cross-referenced against RevZilla/AMCA/MIC/Motorcycle.com 2025-2026 pricing data.

---

## 1. OEM vs Aftermarket vs Used — Decision Rubric (Phase 166)

### Decision tree

```
Part request
├── Safety-critical path-of-force (brake hydraulics, steering bearings,
│   wheel bearings, control cables, fuel lines, throttle cables, hydraulic clutch lines)
│   └── OEM or tier-1 aftermarket (EBC/Galfer/HEL/Goodridge) ONLY — never used, never AliExpress
├── Safety-adjacent friction surface (brake pads, brake rotors, tires, chain+sprockets)
│   └── Reputable aftermarket EQUAL or BETTER than OEM on most applications
│       EBC HH > OEM on most sport bikes; Vesrah RJL > OEM on sport-touring
│       DID 520VX3 / EK ZVX3 > stock OEM chains
├── Engine internals (pistons, rings, valves, cams, bearings)
│   ├── Bike ≥ 2005 with OEM in production → OEM
│   ├── Bike 1990-2004 or OEM discontinued → Wiseco/JE/Wossner pistons, Kibblewhite valves
│   └── Pre-1990 Japanese → aftermarket is often ONLY path; used-OEM last resort
├── Electrical charging system (stator, regulator/rectifier, CDI, ignition coils)
│   └── AFTERMARKET WINS on older Japanese bikes (counter-intuitive — must encode in AI)
│       Ricks Motorsports MOSFET R/R > OEM shunt R/R on 80s-00s Honda/Yamaha/Kawasaki
│       Ricks stators run cooler than OEM on CBR/VFR/FZR
│       ElectroSport, Compu-Fire (HD) also solid
├── Consumables (oil filter, air filter, spark plugs, levers, mirrors, grips, bar-ends,
│   turn signal bulbs, brake fluid, coolant, gaskets EXCEPT head gaskets)
│   └── Quality aftermarket always fine (K&N, HiFlo, NGK, Denso, Pro Taper)
│       OEM oil filter is a waste of money on 99% of applications
├── Body/cosmetic (fairings, tank, seat, fender, mirrors)
│   ├── Insurance/color-match → OEM or OEM-paint-code aftermarket
│   ├── Budget customer → used-OEM from Boneyard / eBay Motors
│   └── Race/track bike → aftermarket fiberglass (Hotbodies, Armour Bodies)
└── Discontinued OEM
    └── Used-OEM (eBay, Boneyard Cycle Parts, MotoProz, CMSNL) → aftermarket reproduction
        (Partzilla, CheapCycleParts carry NOS) → last resort: China-direct with verified reviews
```

### Concrete examples (seed data for Phase 166 AI prompt)

| Scenario | Recommendation | Why |
|---|---|---|
| 2019 Harley M8 Touring brake pads | EBC Double-H or OEM | Both safe; EBC ~30% cheaper, better bite |
| 1998 Honda CBR900RR stator | Ricks Motorsports aftermarket | Runs cooler than OEM which famously cooks itself |
| 2007 Yamaha R1 valve shim kit | OEM Yamaha or Pro-X | Both identical spec; OEM lead time can be weeks |
| 1995 Kawasaki ZX-7 carb rebuild kit | K&L or All Balls | OEM discontinued; K&L is factory supplier |
| 2021 Ducati Panigale V4 brake rotor | OEM Brembo only | Factory Brembo is already best, no uplift from aftermarket |
| 1982 Honda CB750 piston set | Wiseco or JE | OEM NLA; forged aftermarket is UPGRADE over stock cast |
| 2015 HD Sportster clutch pack | Barnett or OEM | Barnett equal or better; $40 cheaper |
| 2003 Suzuki GSX-R750 fairing panel | Used-OEM from eBay | Aftermarket ABS repro is usable but fitment suffers |
| 2018 KTM 690 Duke oil filter | HiFlo HF650 | OEM is literally a rebadged HiFlo; save $8 |
| 1996 Yamaha YZF600R R/R | Shindengen MOSFET kit (FH020AA) | OEM shunt will cook the stator AGAIN; aftermarket fix is standard |

---

## 2. Vendor Tier Taxonomy (Phase 166)

| Tier | Examples | Discount off MSRP | Lead time | When to pick |
|---|---|---|---|---|
| **T1: OEM dealer counter** | HD dealer, Honda Powerhouse, Yamaha/Kaw/Suz authorized | 0% or 10-15% shop wholesale | Same-day to 3 days | Warranty-documented repair, insurance claim, urgent same-day |
| **T2: OEM wholesale / online OEM discount** | Partzilla, BikeBandit, CheapCycleParts, RevZilla-OEM, Tucker, Parts Unlimited, Drag Specialties, WPS | 20-35% off MSRP | 2-5 business days | **Default for most OEM line items.** |
| **T3: Aftermarket brand direct or reseller** | EBC, Galfer, Vesrah, K&N, HiFlo, Ricks Motorsports, Wiseco, JE, Barnett, DID, EK, Pro Taper, Renthal, Shindengen, ElectroSport, Dynojet, S&S, Andrews, Screamin' Eagle | 15-50% off equivalent OEM | 2-7 days | Consumables, wear items, electrical upgrades, performance parts |
| **T4: Online mega-retailers** | RevZilla, J&P Cycles, Dennis Kirk, ChapMoto, MotoSport, Cyclegear, BikeBandit | Pricing blends T2+T3 | 2-5 days (RevZilla often next-day) | One-stop convenience; mixed orders; price-match available |
| **T5: Used-OEM / secondary market** | eBay Motors, Boneyard Cycle Parts (MI), MotoProz, CMSNL (EU), Facebook Marketplace, local salvage yards, PartsGiant, SRC Powersports | 40-80% off new OEM | Variable: 3-10 days shipped, same-day local | Discontinued parts, cosmetic body panels, non-wear mechanical |
| **T6 (avoid for safety-critical)** | AliExpress, Temu, generic Amazon listings | 60-90% off | 2-6 weeks | Cosmetic only (bar-ends, grips, LED bulbs, decorative). NEVER brakes, tires, bearings, fasteners, charging. |

Phase 166 ranking logic: default T2/T3, T1 for warranty/urgent, T5 for NLA, flag T6 with warning.

---

## 3. Labor Time Norms (Phase 167) — Baseline Table

Journeyman mechanic, well-equipped shop, no seized fasteners.

| Job | HD TC/M8 | Honda CBR600/1000RR | Yamaha R1/R6 | Suzuki GSX-R | Kawasaki ZX-6/10 | Dual-sport (KLR/DR/XR) | Cruiser (mid-size Japanese) |
|---|---|---|---|---|---|---|---|
| Oil + filter change | 0.5 hr | 0.4 hr | 0.4 hr | 0.4 hr | 0.4 hr | 0.3 hr | 0.5 hr |
| Chain + sprocket set | n/a (belt) | 1.2 hr | 1.2 hr | 1.2 hr | 1.2 hr | 1.0 hr | 1.3 hr |
| Brake pads (per wheel) | 0.4 hr | 0.4 hr | 0.4 hr | 0.4 hr | 0.4 hr | 0.4 hr | 0.5 hr |
| Brake rotor (per wheel) | 0.8 hr | 0.7 hr | 0.7 hr | 0.7 hr | 0.7 hr | 0.6 hr | 0.9 hr |
| Tire mount + balance (per wheel, R&R included) | 0.8 hr | 0.9 hr | 0.9 hr | 0.9 hr | 0.9 hr | 0.7 hr | 1.0 hr |
| Valve CHECK only | 1.5 hr | 3.0 hr | 3.5 hr | 3.0 hr | 3.0 hr | 1.0 hr | 2.0 hr |
| Valve ADJUST (shim-under-bucket) | n/a (pushrod) | 5.0 hr | 6.0 hr | 5.5 hr | 5.5 hr | 2.0 hr | 3.5 hr |
| Carb sync (2-cyl) | 0.8 hr | — | — | — | — | 0.8 hr | 1.0 hr |
| Carb sync (4-cyl) | — | 1.2 hr | 1.2 hr | 1.2 hr | 1.2 hr | — | 1.5 hr |
| Full carb rebuild (4-cyl, off bike) | — | 4.5 hr | 4.5 hr | 4.5 hr | 4.5 hr | 2.5 hr (1-cyl) | 3.5 hr (2-cyl) |
| Throttle body clean + sync (FI) | 1.0 hr | 1.5 hr | 1.5 hr | 1.5 hr | 1.5 hr | 1.0 hr | 1.5 hr |
| Fork seal replacement (pair) | 2.5 hr | 2.5 hr | 2.5 hr | 2.5 hr | 2.5 hr | 2.0 hr | 3.0 hr |
| Stator replacement | 2.0 hr (primary side) | 3.0 hr (case-split or side-cover) | 3.0 hr | 3.0 hr | 3.0 hr | 2.5 hr | 2.5 hr |
| R/R replacement | 0.4 hr | 0.5 hr | 0.5 hr | 0.5 hr | 0.5 hr | 0.5 hr | 0.5 hr |
| Clutch pack replacement | 1.5 hr (dry primary) | 2.0 hr (wet) | 2.0 hr | 2.0 hr | 2.0 hr | 1.5 hr | 2.5 hr |
| Top-end rebuild (head off, piston/rings) | 12 hr (M8) / 10 hr (TC) | 14 hr (I4) | 14 hr | 14 hr | 14 hr | 8 hr (single) | 10 hr (twin) |
| State inspection | 0.5 hr | 0.5 hr | 0.5 hr | 0.5 hr | 0.5 hr | 0.5 hr | 0.5 hr |

### Skill tier adjustments (multiplicative)

| Tier | Multiplier | Reasoning |
|---|---|---|
| Apprentice (0-2 yr) | **1.35x** | First-time jobs, tool-hunting, manual reading, slower fastener intuition |
| Journeyman (3-8 yr) | **1.00x** (baseline) | Book time = real time on familiar platforms |
| Master (8+ yr, platform specialist) | **0.80x** | Knows shortcuts, pre-stages tools, parallel diagnosis |

Apprentice uplift compresses on simple jobs (oil changes both hit 0.5 hr) but expands on complex (master rebuilds Keihin FCR bank in 3 hr; apprentice takes 6).

### Mileage / condition adjustments

| Condition | Multiplier | Applies to |
|---|---|---|
| <20k mi, garaged, no rust | 0.95x | Everything disassembly-heavy |
| 20-50k mi, normal wear | 1.00x | Baseline |
| >50k mi | **1.15x** | Exhaust flanges, axle nuts, fork pinch bolts, engine mounts |
| >50k AND coastal/rust-belt | **1.30x** | Everything with external fastener; penetrating oil soak + bolt extraction |
| Prior owner-mechanic signs (stripped Phillips, JB Weld, mismatched fasteners) | **1.25x** | On top of mileage factor |

### Phase 167 rubric (for AI system prompt)

```
1. Start with base hours from lookup table for job × platform
2. Apply skill multiplier (default journeyman 1.00x)
3. Apply mileage multiplier
4. Apply corrosion-belt multiplier if bike in coastal or rust-belt state
5. Apply prior-bad-work multiplier if diagnostic flags stripped fasteners
6. Add diagnostic time SEPARATELY (do NOT bundle into repair — Phase 171)
7. Round UP to nearest 0.1 hr; never bill below 0.3 hr minimum
```

---

## 4. Regional Labor Rate Norms (Phase 171 reference — future)

US motorcycle shop labor rates, 2025-2026:

| Shop type | Hourly rate range | Diagnostic fee | Shop supplies fee | Disposal fee |
|---|---|---|---|---|
| Independent mechanic (solo / 2-bay) | $85-125/hr | $50-95 flat or waived if work authorized | 3-5% of labor, $15 min | $5-10 |
| Franchise dealership (HD, metric) | $120-180/hr | $95-150 flat or first 30 min free | 5-7% of labor, $25 min | $10-20 |
| Premium / specialty / euro | $175-250/hr | $125-200 flat, non-refundable | 7-10%, $35 min | $15-25 |
| Mobile mechanic | $95-140/hr + trip charge | $75-125 diagnosis + $1-2/mi trip | Often bundled | Customer disposal |

### Regional multipliers

| Region | Multiplier | Examples |
|---|---|---|
| NYC metro, SF Bay, LA, Seattle, Boston, DC | **1.25-1.40x** | Independent in Brooklyn = $140-165/hr |
| Secondary coastal (San Diego, Portland OR, Miami, Denver) | **1.10-1.20x** | |
| Midwest metros (Chicago, Minneapolis, Detroit, Columbus) | **1.00x** baseline | |
| South/Southeast (Atlanta, Nashville, Dallas, Phoenix) | **0.90-1.00x** | |
| Rural Midwest/South/Mountain West | **0.75-0.90x** | Rural IA independent at $75/hr still common |

### Line-item conventions Phase 171 should model

- Diagnostic billed separately; often waived if customer authorizes recommended repair (dealership standard; independents split)
- Shop supplies line near-universal; % more modern than flat
- Environmental/disposal usually separate and regulated (CA, NY, WA require)
- **Accessory install labor** (user-flagged in memory): flat-rate from per-shop menu, not hourly — exhaust install $150, bar-end mirrors $40, heated grips $175-250, windshield swap $50, luggage rack $85, crash bar $120-175. Each shop builds its own menu.

---

## Key findings for Phase 166/167 system prompts

1. **Biggest Phase 166 win: know when aftermarket is BETTER than OEM** (older Japanese charging systems, sintered brake pads, forged pistons). This is the knowledge gap most shop-management tools miss.
2. **Phase 167 multipliers are where accuracy lives.** Zip code + mileage + prior-work signals move real labor 30-50% off book time. Book-only estimates consistently underbill.
3. **Diagnostic time MUST be separate line.** Bundling into repair = shops lose money when customers decline the work.
