# Phase 264 — Track N batch 2: winterization, de-winterization, engine break-in and valve adjustment — phase log

**Status:** 🚧 In progress
**Branch:** `phase-264` (Opus session, main checkout)

---

### 2026-09-26 — Opened: Track N batch 2

The operator's prompt, 2026-09-26: start Phase 264, Track N batch 2 of 3,
and run it to its finish line. Batch 2 is rows 264 (winterization), 265
(de-winterization), 266 (engine break-in) and 268 (valve adjustment).
Batch 3 is phase 262 (rows 262, 263, 267), then gate 272.

**Ledger convention, 261's, as the operator restated it.** 264 carries
the batch. Rows 265, 266 and 268 close ✅ "folded into 264" with no
CLOSED date. One history row (264) and one handoff.

**Two live-row changes, both in scope by the operator's words:**
1. `generic_winterization_v1`'s description says "Track N phase 264
   expands" (F158). Step 0 decides whether 264 extends that template or
   adds a new one. "Either way, the internal reference goes, and nothing a
   user sees names a phase."
2. F160: `ppi_chassis_v1` names the Yamaha YW125Y service manual "Zuma
   125". "Correct each one, in the same migration, to what the document's
   title page carries."

**The operator's stop, recorded as given:** "Both alter existing live
rows, which is a rule-1 stop. Back up to ~/backups/motodiag/ first and
keep 5. Dry-run on a copy, then show me the diff: every changed row, with
before and after text. Wait for my answer before the live apply." No
pre-approval of the live apply exists. This session asks for it and waits.

**Carried forward** (the operator's list): no literal head pin (F124); no
test reads `data/motodiag.db`; migration tests survive the next
migration; the rollback guard stays; the integration-gap allowlist and
its size pins are updated if a module is added; no internal references in
user-visible text (F158); a negative claim gets a whitespace-proof search
and a control on the cited page; each document is named from its title
page; the Edit tool for source edits; scratch files stay out of `/tmp`
(the session scratchpad is used). Subconscious is available again; bulk
reading goes through it (rule 2), with the fallback route recorded per
entry if it fails.

Read before acting: CLAUDE.md and the working-rules index; ROADMAP rows
258–272 and the status key; `ROADMAP_AUTHORITY.md`; the newest handoff
(`2026-09-25_261_closed.md`, named by `git log`); F158, F159, F160 in
`docs/FOLLOWUPS.md`; 261's implementation, phase log and Step 0;
migrations 007, 068 and 069 and the 114, 259, 260 and 261 test files.

Branch `phase-264` from `master` at `270fcad`. **Ledger step before Step
0:** rows 264, 265, 266 and 268 → 🚧, commit `ed70006`;
`roadmap_check.py` ok.

### 2026-09-26 — Step 0: an extension, four checklists, no fork

The measurements are in `264_step0.md`. In short:
- **The four categories already exist.** The batch is one content
  migration (070) plus tests, with no new module.
- **Every row has maker support.** One negative died inside Step 0: an
  electric traction battery's storage is in the Vespa Elettrica service
  station manual (p. 9). One was narrowed: no document says "heat cycle",
  but the Buddy 125 prescribes a cool-down. Seven negatives stand, each
  with a control on its page.
- **Decided, not asked:**
  - 264 adds `winterization_v1` rather than extending the generic. The
    generic's items carry unsupported figures and would be rewritten
    live; filed instead.
  - Valve adjustment is one template with optional per-engine-type
    items.

  Neither choice ships different things from the rows' subjects.
- **F160 re-measured:** 8 live mentions in 3 items, not 9. The ninth is
  migration 068's Python description, which no row carries.
- **Rule 2 ran on its primary route.** Subconscious answered all three
  calls in a sandbox proven by planted writes. It took 3–5 turns where 2
  is the measured norm, and one call looped. Its `machine` field
  reintroduced "Zuma". Nothing from the model is used unchecked.

### 2026-09-26 — Build: migration 070, four templates, two re-points, 31 tests

What shipped:
- **Migration 070 `seasonal_breakin_valve_workflows`** (schema 69 → 70):
  - `winterization_v1` (7 items, all powertrains);
  - `de_winterization_v1` (7, all powertrains);
  - `engine_break_in_v1` (6, ICE and hybrid);
  - `valve_adjustment_v1` (8, ICE and hybrid).

  Also the two live re-points: `generic_winterization_v1`'s description
  (keyed on its old text) and the F160 text in `ppi_chassis_v1`'s items.
  The rollback deletes the new rows and reverses both re-points in the
  opposite order.
- **Claims before text** (`s0/claims.py`, session scratchpad): 86 claims,
  257 verbatim anchors, all on their cited pages. The checker was seen to
  fail on a wrong page and a corrupted figure.
- **The cross-check** (`s0/xcheck.py`) maps every "PDF p." in the seeded
  text to a claim for the machine named before it: 221 cited pages, 0
  unclaimed. It found three real attribution gaps before any test ran:
  "The Yamaha grounds…" twice and "the Kymco keeps…" once, each after
  another machine had been named. All three now name the machine. Its
  control: withdrawing V13, the only claim on People S 250 SM p. 81,
  turned exactly that citation red.
- **31 tests** in `tests/test_phase264_seasonal_breakin_valve.py`. Two
  failed at first run, both test-authoring errors: a pin said "check"
  where the text says "checks", and `winterization_v1` is a substring of
  `de_winterization_v1`, so the other-slug check needed a boundary.
- **Two existing pins moved with the phase's own changes:**
  - `test_phase260_ppi_chassis.py::test_figures_name_their_machines`
    asserted "Zuma 125" on a fresh database. It now asserts "YW125Y",
    plus no "Zuma" in any chassis field.
  - `test_phase114_workflow_substrate.py::test_list_by_powertrain`
    asserted no winterization template for electric machines. That was a
    head-state assumption from the one generic template. The pin is now
    on the generic's slug, plus the positive that `winterization_v1` is
    offered for electric (S0-5, Vespa Elettrica p. 9).
- **Floor** 9415 → 9446 (+31, this file only; `--collect-only -q -p
  no:xdist` measured 9,446).

**Known-bad controls**, each planted with the Edit tool, run with
`__pycache__` cleared and `-B`, seen red, and reverted:

| # | plant | red tests |
|---|---|---|
| 1 | "start from 0.15 mm" in the no-figure valve item | `test_no_figure_item_carries_no_clearance` |
| 2 | 7,800 → 7,900 rpm in one field | `test_every_pinned_figure_is_in_its_field`, `test_figures_sit_beside_their_machine` |
| 3 | "(Phase 999)" in a template description | `test_all_four_templates_are_clean` |
| 4 | the bare-"Zuma" replace dropped from one field | the upgrade-scope test, both F160 tests, and 260's moved pin |
| 5 | `engine_break_in_v1` dropped from the rollback's template `DELETE` | both round-trip tests; the rollback guard stayed green, as in 261 |
| 6 | an extra `UPDATE` of an unrelated live item inside 070 | `test_upgrade_from_69_changes_exactly_the_scoped_rows`, the round trip |

After the reverts: `grep` finds none of the plants, 60 passed over the
264 and 260 files, and the cross-check still reads 0 unclaimed.

**Whole-tree gates before the build commit:**
- rule 3's four, plus the F124 guard, 240c, 209B, 244U, 244Y, 244V, 355,
  the floor, and the 114, 259, 260, 261 and 264 files: **514 passed**
  (`-n auto`);
- `finding_check` exit 0, and `check(phase_docs="docs/phases/in_progress")`
  returns [].

## Refuter pass

**Round 1 — 2026-09-26.** Four fresh-context Opus refuters, one per
template. The valve refuter also checked F160.
- Every cited page was opened. PDF rendering was unavailable (no
  poppler), so each refuter read the text layer with pypdf and rendered
  pages with `sips` where the text layer was poor.
- Every document's identity was read from its own title page.
- Full verdict files, with the item-text defects and the search counts
  behind each negative, are in the session scratchpad at
  `s0/refute/*_verdict.md`.
- The claim rows are as the refuters wrote them. The negative rows
  condense each refuter's search into its quoted control and page.

| claim | verdict | quote | source |
|---|---|---|---|
| W1 | kept | "Before storing the motorcycle, check all parts for function and wear. If service, repairs or replacements are necessary, you should do this during the storage period (less workshop overload)." | KTM 690 Enduro 2010 OM, p. 172 |
| W2 | kept | "Wash your motorcycle and wax all painted surfaces (except matte painted surfaces). Coat chrome pieces with rust-inhibiting oil. ● Lubricate the drive chain." | Honda CB500F/FA 2018 OM, p. 117 |
| W3 | kept | "Spray the brake and clutch lever pivots, the side stand pivots and the centre stand pivots … Coat bright metal and chrome-plated parts with an acid-free grease (e.g. Vaseline). Stand the motorcycle in a dry room in such a way that there is no load on either wheel. Before laying the vehicle up out of use, have the engine oil and the oil filter element changed by a specialist workshop" / "Remove the protective wax coating. Clean the motorcycle. Install a charged battery. Before starting: work through the checklist." | BMW F800R Rider's Manual, p. 124 |
| W4 | kept | "1. Make all necessary repairs … 3. Fill up the fuel tank, adding fuel stabilizer according to product instructions. Run the engine for 5 minutes … 4. For vehicles equipped with a fuel cock: Turn the fuel cock lever to the off position. 5. For vehicles with a carburetor … drain the fuel in the carburetor float chamber into a clean container … b. Pour a teaspoonful of engine oil into the spark plug bore … 7. Lubricate all control cables, pivots, levers and pedals … 9. Cover the muffler outlet with a plastic bag … 10. … attach a maintenance charger … Do not charge a VRLA battery with a conventional charger … If the battery will be removed, charge it once a month and store it … between 32-90 °F (0-30 °C)." | Yamaha XVS95CL/XVS95CLC OM, p. 81 |
| W5 | kept | "Storing the vehicle in a poorly ventilated room or covering it with a tarp, while it is still wet, will allow water and humidity to seep in and cause rust." / "avoid damp cellars, stables (because of the presence of ammonia) and areas where strong chemicals are stored." / "Before storing the vehicle long term (60 days or more):" / "If necessary, clean the brake discs and pads with brake cleaner or acetone. Before riding at higher speeds, test the vehicle's braking performance and cornering behavior." | Yamaha XVS95CL/XVS95CLC OM, p. 80 |
| W6 | kept | "When refueling for the last time before taking the motorcycle out of service, add fuel additive." / "Tip Fill the fuel tank completely as specified, using fuel with the lowest possible ethanol content." / "the water vapor produced during combustion condenses and causes valves and the exhaust system to rust." | KTM 1290 Super Duke R/RR 2023 OM, p. 157 |
| W7 | kept | "Make sure the tank is as empty as possible so that you can fill up with fresh fuel" / "Change the engine oil and filter, clean the oil screens." / "Storage temperature of battery without direct sunshine. 0… 35 °C" | KTM 690 Enduro 2010 OM, p. 172 |
| W8 | kept | "1. Change the engine oil and filter. 2. Drain the carburetor (if equipped) and empty the fuel tank into an approved gasoline container … Spray the inside of the tank with an aerosol rust-inhibiting oil." / "keep heat, sparks, and flame away. Refuel the scooter outdoors" / "Pour a tablespoon (15 - 20 cc) of clean engine oil into the cylinder and cover the spark plug hole with a piece of cloth." | Kymco People S 50/125/200 OM, p. 60 |
| W9 | kept | "Change the gear oil." / "add fuel additive." / "Add 2-stroke oil." / "Ideal charging and storage temperature of the lithium-ion battery 10 … 20 °C" / "Store the vehicle in a dry location that is not subject to large fluctuations in temperature." / "Raise the motorcycle with a lift stand." / "Cover the vehicle with a tarp or similar cover that is permeable to air." | KTM 2022 250/300 EXC TPI (and XC-W TPI) OM, p. 154 |
| W10 | kept | "Do not use non-porous materials since they prevent humidity from escaping, thus causing corrosion. Avoid running the engine for a short time only. Because the engine will not warm up sufficiently, the water vapor produced during combustion will condense, causing engine parts and the exhaust system to rust." | KTM 2022 EXC TPI OM, p. 155 |
| W11 | kept | "Drain the carburetor float chambers by loosening the drain bolts; this will prevent fuel deposits from building up. Pour the drained fuel into the fuel tank. 4. Fill up the fuel tank and add fuel stabilizer (if available) to prevent the fuel tank from rusting and the fuel from deteriorating." | Yamaha XV250T1/XV250T1C OM, p. 81 |
| W12 | kept | "Place your motorcycle on a maintenance stand and position a block so that both tires are off the ground. ● After rain, remove the body cover and allow the motorcycle to dry. ● Remove the battery … Fully charge the battery and then place it in a shaded, well-ventilated area. u If you leave the battery in place, disconnect the negative - terminal" | Honda CB500F/FA 2018 OM, p. 117 |
| W13 | kept | "For extended storage, remove the battery, give it a full charge, and store it in a cool, dry space. For maximum service life, charge the stored battery every two weeks." | Honda PCX150 2013–2017 SM, p. 390 |
| W14 | kept | "If the battery is not disconnected, the on-board electronics (clock, etc.) will discharge the battery. This can cause the battery to run flat. If this happens, warranty claims will not be accepted. Disconnect the ground (earth) lead from the battery prior to a lay-up." / "recharge it at regular intervals of approx. 4 months. If the battery is not disconnected from the motorcycle's systems, recharge it every 2 months at the latest" / "Always fully recharge the battery before restoring it to use" | BMW R 850 R / R 1150 R Maintenance Instructions, p. 49 |
| W15 | kept | "Use only electronically controlled battery chargers with a limit voltage of 14.4 V to charge the battery." | BMW R 850 R / R 1150 R MI, p. 48 |
| W16 | killed (page only; substance true) | p. 78: "These operations should be carried out before delivering the vehicle, and on a six-month basis while the vehicle is stored in open circuit." — the "sealed battery" condition is on p. 77: "Sealed battery If the vehicle is provided with a sealed battery, the only maintenance required is the check of its charge and recharging, if necessary." The 1-month / three-month sentences are on p. 78 as claimed. Fix: cite pp. 77–78. | Piaggio Beverly 125 SSM, pp. 77–78 |
| W17 | kept | "If the motorcycle is to be out of use for more than four weeks, disconnect the battery or connect a suitable trickle charger to the battery. BMW Motorrad has developed a float charger specially designed for compatibility with the electronics of your motorcycle." | BMW F800R Rider's Manual, p. 117 |
| W18 | kept | "IN THE EVENT OF PROLONGED PERIODS WITH THE VEHICLE NOT IN USE, CHARGE THE TRACTION BATTERY COMPLETELY AT LEAST ONCE EVERY THREE (3) MONTHS." / "EQUIPPED WITH AN EARTH CONNECTION AND A DIFFERENTIAL CIRCUIT BREAKER." / "TEMPERATURES BETWEEN 0°C AND -10°C, THE ON-BOARD ELECTRONICS WILL ONLY PERMIT A SLOW, PARTIAL TRACTION BATTERY CHARGING CYCLE, LASTING INDICATIVELY 6 HOURS AND TO A BATTERY STATE OF CHARGE OF 60%" (Pre-delivery section) | Vespa Elettrica SSM, p. 9 |
| W19 | kept | "Sealed battery If the vehicle is provided with a sealed battery … These operations should be carried out before delivering the vehicle, and on a six-month basis while the vehicle is stored in open circuit." | Vespa Elettrica SSM, p. 163 |
| W20 | kept | "8. Check and correct the tire air pressure, and then lift the vehicle so that all wheels are off the ground. Otherwise, turn the wheels a little once a month" | Yamaha XVS95CL OM, p. 81 |
| W21 | kept | "Do not use non-porous materials since they prevent humidity from escaping, thus causing corrosion." | KTM 2022 EXC TPI OM, p. 155 |
| W22 | kept | "Always store the vehicle in a cool, dry place. If necessary, protect it against dust with a porous cover." | Yamaha XVS95CL OM, p. 80 |
| W23 | kept | "Avoid running the engine for a short time only. Since the engine cannot warm up properly, the water vapor produced during combustion condenses and causes valves and exhaust system to rust." | KTM 690 Enduro 2010 OM, p. 173 |
| R1 | kept | "Restoring motorcycle to use … Remove the protective wax coating. … Clean the motorcycle. … Install a charged battery. … Before starting: work through the checklist." | Rider's Manual F 800 R, p.124 |
| R2 | kept | "Removal from storage 1. Uncover and clean the scooter. 2. Change the engine oil if more than 1 month has passed since the start of storage. 3. Charge the battery as required … Install the battery. 4. Drain any excess aerosol rust-inhibiting oil from the fuel tank. Fill the fuel tank with fresh gasoline. 5. Perform all the pre-ride inspection checks (see pages 23 - 33). Test ride the scooter at low speeds in a safe riding area, away from traffic." | Kymco People S 50 & 125 & 200 Owner's Manual, p.61 |
| R3 | kept | "20.2 Preparing for use after storage – Remove the motorcycle from the lift stand. – Install the 12-V battery. – Perform checks and maintenance measures when preparing for use. (p. 44) – Make a test ride." | KTM Owner's Manual 2022 250/300 EXC TPI (etc.), p.155 |
| R4 | kept | "Restoring to use • If necessary, remove protective wax coating • Clean the motorcycle • Install a charged battery • Perform safety checks (Rider's Manual 19-43) • Check the brakes (Rider's Manual 26-33) • Check/correct tyre pressures" | BMW Maintenance Instructions R 1150 R / R 850 R, p.59 |
| R5 | kept | "9. Cover the muffler outlet with a plastic bag to prevent moisture from entering it." | Yamaha XVS95CL/XVS95CLC Owner's Manual, p.81 |
| R6 | kept | "If voltage exceeds 12.60 V, the battery can be installed without any renewal recharge. - If voltage is below 12.60 V, a renewal recharge is required as explained in 2). … Constant voltage charge equal to 14.40 ÷ 14.70V … 10 to 12 h recommended Minimum 6 h Maximum 24 h … the terminals should be coated with Vaseline." | Piaggio Service Station Manual Beverly 125, p.78 |
| R7 | kept | "Restoring to use • If necessary, remove protective wax coating • Clean the motorcycle • Install a charged battery • Apply the correct grease to the battery terminals • Perform all safety checks • Check the brakes • Check/correct tyre pressures" | BMW Service and Technical Booklet R 1100 S, p.79 |
| R8 | kept | "Always fully recharge the battery before restoring it to use" | BMW MI R 1150 R / R 850 R, p.49 |
| R9 | kept | "Install the battery. … Info If the battery was removed, the time and date must be set." | KTM Owner's Manual 2016 1190 Adventure, p.206 |
| R10 | kept | "Do not attempt to jump-start the motorcycle if the battery is completely flat: recharge the battery instead. Risk of damaging the control units." | BMW MI R 1150 R / R 850 R, p.48 |
| R11 | kept | "This model comes with a maintenance free (MF) battery. … Even under normal use, the performance of the battery deteriorates after 2-3 years." | Honda 2013-2017 PCX150 Service Manual, p.390 |
| R12 | kept (context: this is the **Pre-delivery** section; see defect 7) | "- Charge the traction battery to 100% state of charge" / "AT BATTERY TEMPERATURES ABOVE 0°C, THE NORMAL CHARGE CYCLE TO 100% STATE OF CHARGE IS PERFORMED (NORMAL CHARGE), WHEREAS AT BATTERY TEMPERATURES BELOW 0°C, A SLOW, PARTIAL CHARGE CYCLE IS PERFORMED (SLOW CHARGE)." / "THE ANCILLARY BATTERY MAY STILL NOT BE FULLY CHARGED. THE ANCILLARY BATTERY IS, HOWEVER, ALWAYS CHARGED WHILE THE VEHICLE IS RUNNING." | Vespa Elettrica Service Station Manual, p.9 (footer "Pre-delivery PRE DE - 9") |
| R13 | kept (the page is headed "For motorcycle version 70 Km/h") | "Below 10% of traction battery charge state, the battery icon start flashing indicating the limitation of the current speed." | Vespa Elettrica SSM, p.90 |
| R14 | kept | "14.2 Putting into operation after storage … – Refuel. … – Make a test ride." | KTM Owner's Manual 2010 690 Enduro / Enduro R, p.173 |
| R15 | kept | "1. Engine oil level: Add engine oil if required (page 24). Check for leaks. 2. Tires … 3. Fuel level … 4. Front and rear brakes … 5. Steering … 6. Instruments … 7. Lights and horn … 8. Chassis" | Kymco People S OM, p.25 |
| R16 | kept (anchors present; the list is longer than the template gives it; see defect 10) | "Check the front brake fluid level. … Check that the brake system is functioning properly. … Check the settings of all controls and ensure that they can be operated smoothly. – Check all screws, nuts, and hose clamps regularly for tightness." | KTM 2022 EXC TPI OM, p.46 |
| R17 | kept | "After removing your motorcycle from storage, inspect all maintenance items required by the Maintenance Schedule." | Honda 2018 CB500F/FA Owner's Manual, p.117 |
| R18 | kept | "If the brake fluid level drops below the specified marking or the specified value, the brake system is leaking or the brake linings are worn down. – Check the brake system and do not continue riding until the problem is eliminated." | KTM 2022 EXC TPI OM, p.101 (13.5, front brake) |
| R19 | kept | "The tire air pressure must be checked and adjusted on cold tires (i.e., when the temperature of the tires equals the ambient temperature)." | Yamaha XVS95CL OM, p.58 |
| R20 | kept (context: the Care/cleaning section, not storage) | "Make sure there is no lubricant or wax on the brakes or tires. … If necessary, clean the brake discs and pads with brake cleaner or acetone. … Before riding at higher speeds, test the vehicle's braking performance and cornering behavior." | Yamaha XVS95CL OM, p.80 |
| E1 | kept | "When your engine is new or when you have installed new engine components, it is very important to follow this run-in procedure." / "0 - 100 miles Avoid opening the throttle beyond 1/2 throttle. Cool down the engine for 10 minutes, after every 30 minutes of operation." / "During the first 500 miles of operation, avoid wide-open throttle operation or any operation that may cause high engine temperatures." | Genuine Buddy 125 OM, PDF p. 25 |
| E2 | kept | "1. 0~95 MILES AVOID OVER 1/2 THROTTLING OPERATION.COOL DOWN THE ENGINE 5-10 MIN./PER HOUR." / "NOTE: CHANGE GEAR OIL AFTER 200 MILES" / "IF THERE IS ANY PROBLEM DURING THE INITIAL RUN-IN PREIOD, PLEASE CONTACT YOUR DEALERS." | Genuine Buddy 125 OM, PDF p. 27 |
| E3 | kept | "Since the engine is brand new, do not put an excessive load on it for the first 1600 km (1000 mi). The various parts in the engine wear and polish themselves to the correct operating clearances." / "0–1000 km (0–600 mi) Avoid prolonged operation above 3500 r/min." / "1000–1600 km (600–1000 mi) Avoid prolonged operation above 4200 r/min." / "Keep the engine speed out of the tachometer red zone." | Yamaha SR400 OM, PDF p. 39 |
| E4 | kept | "During the first: 1,000 km (621.4 mi) 6,000 rpm After the first: 1,000 km (621.4 mi) 7,800 rpm – Avoid fully opening the throttle!" | KTM 2010 690 Enduro / 690 Enduro R OM, PDF p. 46 |
| E5 | kept | "During the first: 1,000 km (620 mi) 6,500 rpm After the first: 1,000 km (620 mi) 10,250 rpm" | KTM 2016 1190 Adventure OM, PDF p. 86 |
| E6 | kept | "Until the running-in check, vary the throttle opening and engine-speed range frequently; avoid riding at constant engine rpm for prolonged periods. Try to do most of your riding during this initial period on twisting, fairly hilly roads." / "Running-in speeds <5000 min-1" / "Mileage until the running-in check 500...1200 km" | BMW R 1200 GS rider's manual, PDF p. 85 |
| E7 | kept | "0–1000 km (0–600 mi) Avoid prolonged operation above 1/3 throttle. NOTICE: After 1000 km (600 mi) of operation, the engine oil must be changed, and the oil filter cartridge or element replaced." / "1000–1600 km (600–1000 mi) Avoid prolonged operation above 1/2 throttle." | Yamaha XVS95CL/XVS95CLC OM, PDF p. 41 |
| E8 | kept | "Initial 300 miles (600 km): ........ Less than 1/2 throttle Up to 600 miles (1,000 km): ..... Less than 3/4 throttle" / "This allows the parts to be "loaded" with pressure, and then unloaded, allowing the parts to cool." / "It is essential that some stress be placed on these components during break-in" / "Do not, however, apply excessive load on the scooter's drive line." / "All fasteners will be tightened, and the contaminated engine oil will be replaced." | Kymco People S 50 & 125 & 200 OM, PDF p. 23 |
| E9 | kept | "Maximum engine performance During the first 3 operating hours < 70 % During the first 5 operating hours < 100 %" / "Idle speed 1,400 … 1,500 rpm Info The idle speed may change during the run-in time. » If the idle speed changes: – Adjust the idle speed." | KTM 2022 250/300 EXC TPI (and XC-W TPI) OM, PDF p. 40 |
| E10 | kept | "During the first 300 miles (500 km) of running, follow these guidelines … Avoid full-throttle starts and rapid acceleration. Avoid hard braking and rapid down-shifts. Ride conservatively." | Honda 2018 CB500F/FA OM, PDF p. 14 |
| E11 | kept | "Limit the maximum speed of your scooter during the first 600 miles (1,000 km) of operation. Keep the road speed below 25 MPH (40 KPH) during this break-in period." | Kymco People S OM, PDF p. 40 |
| E12 | kept | "avoiding high-speed main roads and highways if possible." / "Exceeding the specified engine speeds while running in will lead to increased engine wear." / "No full-load acceleration." | BMW F 800 R rider's manual, PDF p. 66 |
| E13 | kept | "Avoid low engine speeds at full load. Do not omit the first inspection after 500 - 1200 km." | BMW F 800 R rider's manual, PDF p. 67 |
| E14 | kept | "ENGINE OIL … INITIAL= 600 mi (1,000 km) or 1 month: R" (rendered page: "MAINTENANCE SCHEDULE (AFTER '13 MODEL)") | Honda PCX150 2013–2017 SM, PDF p. 77 (printed 3-5) |
| E15 | kept | "Performing the first scheduled maintenance is very important. It compensates for the initial wear that occurs during the break-in period." | Honda PCX150 2013–2017 SM, PDF p. 3 |
| E16 | kept | "After one month of use or 200 miles (300 km) of riding, which ever occurs first, contact your KYMCO dealer to perform an initial service on your scooter." / "This initial service is the most important service in the life of your scooter" | Kymco People S OM, PDF p. 25 |
| E17 | kept | "The BMW running-in check has to be performed when the motorcycle has covered between 500 km and 1200 km" | BMW F 800 R rider's manual, PDF p. 141 |
| E18 | kept | "If any engine trouble should occur during the engine break-in period, immediately have a Yamaha dealer check the vehicle." | Yamaha XVS95CL/XVS95CLC OM, PDF p. 42 |
| E19 | kept | "Operating the engine at constant low speed (light load) can cause parts to glaze and not seat in properly." | Kymco People S OM, PDF p. 23 |
| V1 | kept | "Inspect and adjust the valve clearance while the engine is cold (below 35°C/95°F)." / "align the cut out ("T" mark) [4] of the cooling fan with the index mark" / "This position can be confirmed by checking that there is slack in the rocker arm." / "Rotate the crankshaft one full turn counterclockwise slowly and match up again." / "inserting a feeler gauge [1] between the valve adjusting screw and valve stem." / "IN: 0.10 ± 0.02 mm" "EX: 0.24 ± 0.02 mm" | Honda PCX150 2013–2017 SM, p. 82 |
| V2 | kept | "while the engine is cold (below 35°C/95°F)" / "the lobe of the camshaft faces the cylinder side (TDC on the compression stroke)" / "turn the drive pulley (crankshaft) one revolution" / "inserting a feeler gauge between the valve lifter and shim." / rendered: "IN: 0.10 ± 0.03 mm" "EX: 0.19 ± 0.03 mm" (the text layer reads "+" for IN; the rendered page prints ±) | Honda CHF50/P/S Metropolitan 2002–2006 SM, p. 64 |
| V3 | kept | "Inspect and adjust valve clearance while the engine is cold (below 35Ċ)." [text layer] / "Valve Clearance: IN: 0.1mm EX: 0.1mm" / "Check the valve clearance again after the lock nut is tightened." The page gives °C only, no °F (see defect 1) | Kymco People/People S 250 SM, p. 59 |
| V4 | kept | "Valve clearance adjustment should be made on a cold engine, at room temperature." / "the piston must be at top dead center (TDC) on the compression stroke" / "Turn the crankshaft counterclockwise." / "align the punch mark a in the camshaft sprocket with the stationary b on the cylinder head" / "Intake valve 0.10 ~ 0.14mm" "Exhaust valve 0.16 ~ 0.20mm" | Yamaha YW125Y 2009 SM, p. 62 |
| V5 | kept | "2-cylinder 4-stroke Otto engine, 75° V arrangement, water-cooled" / "DOHC, 4 valves per cylinder, chain-driven" / "Exhaust at: 20 °C (68 °F) 0.25… 0.30 mm" / "Intake at: 20 °C (68 °F) 0.10… 0.15 mm" | KTM 2016 1190 Adventure OM, p. 209 |
| V6 | kept | "Unadjusted valves can result in improper air-fuel mixture, engine noise, and eventually engine damage." / "have your Yamaha dealer check and adjust the valve clearance at regular intervals." / "This service must be performed when the engine is cold." | Yamaha XVS95CL/XVS95CLC OM, p. 58 |
| V7 | kept | "Align the TDC mark c on the AC magneto rotor with the stationary pointer d on the crankcase." / "Loosen the locknut 1." / "between the end of the adjusting screw and the valve tip." / "Valve adjusting tool 90890-01311" / "Locknut 7Nm (0.7m kgf, 5.1ft lbf)" | Yamaha YW125Y 2009 SM, p. 63 |
| V8 | kept | "Measure the valve clearance again." / "repeat all of the valve clearance ad- justment steps until the specified clearance is obtained." / "breather 7Nm" "valve cover (intake and exhaust) 7Nm" "spark plug 13Nm" | Yamaha YW125Y 2009 SM, p. 64 |
| V9 | kept | "until there is a slight drag on the feeler gauge" / "Apply engine oil to the valve adjusting screw lock nut threads and seating surface." / "TORQUE: 10 N·m (1.0 kgf·m, 7 lbHt)" / "Recheck the valve clearance." / "Make sure the left crankcase cover duct rubber seal [1] is in good condition and replace it if necessary." | Honda PCX150 2013–2017 SM, p. 83 |
| V10 | kept | "Valve play, cold 0.07… 0.13 mm (0.0028… 0.0051 in)" (one figure; no intake/exhaust split) | KTM 2010 690 Enduro OM, p. 174 |
| V11 | kept | "valve clearance intake: 0.10 mm - discharge: 0.15 mm" (no temperature condition on the page or anywhere else in the manual) | Vespa GTS Super 300 ie (2008) SSM, p. 9 |
| V12 | kept | "If the compression is low, check for the following: … ‧Valve clearance to small" | Kymco People/People S 250 SM, p. 60 |
| V13 | kept | "Valve clearance adjusting nut 8.8N-m Apply engine oil to threads" | Kymco People/People S 250 SM, p. 81 |
| V14 | kept | "Tappet set screw lock nut 6 ÷ 8" (table headed "Name Torque in Nm") | Vespa GTS Super 300 ie (2008) SSM, p. 16 |
| V15 | kept | "Do not allow the shims to fall into the crankcase." / "Mark all shims to ensure correct reassembly in their original locations." / "The shims can be easily removed with tweezers or a magnet." / "Sixty-nine different shim thicknesses are available in increments of 0.025 mm (from 1.200 mm to 2.900 mm)." / "A = ( B - C) + D" / "Make sure of the correct shim thickness by measuring the shim with a micrometer." / "Reface the valve seat if carbon deposits result in a calculated dimension of over 2.900 mm." / "Rotate the camshaft by rotating the drive pulley (crankshaft) counterclockwise several times. Recheck the valve clearance." | Honda CHF50/P/S SM, p. 65 |
| V16 | kept | "* Valve clearance • Check and adjust valve clearance when engine is cold. • Adjust if necessary. Every 16000 mi (25000 km)" / "Items marked with an asterisk … have a Yamaha dealer perform the service." | Yamaha XVS95CL/XVS95CLC OM, p. 45 |
| V17 | kept | "Intake at: 20 °C (68 °F) 0.10 … 0.15 mm" / "Exhaust at: 20 °C (68 °F) 0.25 … 0.30 mm" | KTM 2023 1290 Super Duke R / RR OM, p. 161 |
| V18 | kept | "Cylinder arrangement: V-type" / "Number of cylinders: 2-cylinder" | Yamaha XVS95CL/XVS95CLC OM, p. 82 |
| V19 | kept | "Check the valve clearance. (air filter and spark plugs removed)" | KTM 2016 1190 Adventure OM, p. 103 |
| V20 | kept | "3 * Valve clearance • Check and adjust valve clearance when engine is cold. Every 26600 mi (42000 km)" | Yamaha YZFR6L/YZFR6LC OM, p. 60 |
| V21 | kept | "Water-cooled inline four-cylinder engine, longitudinal and horizontal installation, with 4 valves per cylinder, bucket-type tappets, two chain-driven overhead camshafts" | BMW K 1200 RS Maintenance Instructions, p. 63 |
| V22 | kept | "Air-cooled flat-twin ("Boxer") … operating 4 valves per cylinder by means of tappets and short pushrods" | BMW R 1100 S Service and Technical Booklet, p. 80 |
| V23 | kept | "Check/adjust valve clearances X X X" | BMW R 1100 S Service and Technical Booklet, p. 7 |
| F1 | kept, with one note | Rendered p. 1: "2009 / MOTORCYCLE / SERVICE MANUAL / Model : YW125Y_ / 32SF819770E0". "zuma" (whitespace-stripped, any case) is on 0 of 338 pages. Every re-pointed YW125Y citation says what its sentence says: p. 93 "Grasp the bottom of the front fork legs and gently rock the front fork. Binding/looseness → Adjust the steering head."; p. 94 "Lower ring nut (initial tightening torque) 38Nm" / "(final tightening torque) 14Nm"; p. 95 "Damage/scratches → Replace", "Oil leakage → Replace", "Push down hard on the handlebar several times and check if the front fork rebounds smoothly. Rough movement → Repair."; p. 34 "Free length 252.1mm … 247mm", "Inner tube bending limit … 0.2mm"; p. 55 "Wheel bearings • Check bearings for smooth operation. • Replace if necessary." Note (wording only, not a citation fault): "calls the same movement binding or looseness" misreads p. 93, where Binding/looseness is the fault the rocking check finds, not the name of the movement | Yamaha YW125Y 2009 SM pp. 1, 34, 55, 93, 94, 95 |
| N1 | kept | "valve clearance" appears in the library; no desmodromic valve train does (desmodrom / desmoservice / desmoquattro / desmosedici / ducati: 6 hits, every one a whitespace-joined false positive such as "des modifications"). Control: "VALVE CLEARANCE" | Honda CHF50 service manual, PDF p. 64 |
| N2 | killed (as first worded: "only Genuine prescribes a cool-down"); "no document names heat cycles" kept, 0 pages | "After every hour of operation, stop the engine, and then let it cool for five to ten minutes." | Yamaha XC50J owner's manual, PDF p. 34 (also XC50A p. 35, YW125Y OM p. 36, GQX125N p. 39) |
| N3 | kept for service manuals; killed as worded in item 1 ("the only maker ... is Genuine") | "It is better to drive in low speed after replacing the engine." | SYM T2 250i owner's manual, PDF p. 17 (also SYM Wolf Classic 150 p. 17) |
| N4 | kept | 17 inline-four documents, valve clearance / play / tappet / lash / shim within 150 characters of a mm or in figure: 0 pages; the words occur only as schedule lines, e.g. "Check and adjust valve clearance when engine is cold." Control hits "Valve play, cold 0.07… 0.13 mm" | Yamaha YZFR6L owner's manual, PDF p. 60; control KTM 690 Enduro 2010 OM p. 174 |
| N5 | kept | 5 boxer documents, the same search: 0 pages with a figure; the words occur as "Check/adjust valve clearances" | BMW R 1100 S Service and Technical Booklet, PDF p. 7 |
| N6 | kept | 211 storage-procedure pages, 0 with an oil-grade token; the 13 window hits are winter-riding oil tables, "synthetic wax", fogging oil and "SAE 12-VDC power socket". Control: "SAE viscosity grades: 10W-40" | Yamaha XVS95CL owner's manual, PDF p. 82 (a specification page, not storage) |
| N7 | kept | "exercise" near "brake" (27 pages), "operate the brake" (117), "pump" near brake (176), "several times / repeatedly" near brake (270): none in a storage or return-to-service context. Control: "Check the brakes" | BMW R 850 R / R 1150 R Maintenance Instructions, PDF p. 59 |

**Round 1 result: 93 rows.**
- 84 of 85 claims kept, and F1 kept. **W16 was killed on its page
  only:** the Beverly's sealed-battery condition is on p. 77, not p. 78.
- **Two negatives died as worded:**
  - N2's "only Genuine prescribes a cool-down": the Yamaha XC50J cools
    five to ten minutes after every hour, p. 34.
  - Item 1's "only Genuine speaks to a rebuild": SYM, "It is better to
    drive in low speed after replacing the engine", T2 250i p. 17.

  N3 survives for service manuals. N1, N4, N5, N6 and N7 survive
  widened searches.
- **About 50 item-text defects, all corrected.** The substantive ones:
  - the carburetor item cited the fuel-injected XVS95CL; the carbureted
    XV250T1 sets its fuel cock to "ON" (p. 80);
  - the template's own reconciliation of Yamaha's 5-minute run with
    KTM's short-run warning;
  - battery intervals stripped of their conditions;
  - the Elettrica's 100 % charge, which is its pre-delivery step;
  - a stand step and a cover step cited to a BMW page that says neither;
  - the muffler bag the Yamaha never removes;
  - KTM's before-use list presented as complete;
  - "cold" merged across makers, and the Vespa GTS given as cold with
    no temperature on its page;
  - the PCX150's crankcase duct seal read as a valve-cover seal;
  - the shim sentence reversed;
  - one machine's rule made universal, several times.

**Declined, with reasons:**
- "F800R" for the title page's "F 800 R", and "CB500F" for "CB500F/FA":
  spacing, and a base-model name for a manual that covers both. 261's
  live text uses the same forms.
- The CHF50's fuller name "CHF50/P/S": kept as 260 and 261 name it.
- In 260's live chassis text, the refuter noted a misreading ("calls the
  same movement binding or looseness"; p. 93 names binding or looseness
  as the fault found) and an ambiguous KTM EXC p. 76 citation. The
  operator's F160 scope is the "Zuma" name only, so these are recorded,
  not changed.

### Round 2 — 2026-09-26: the 10 claims round 1 added, and the corrected text

One fresh-context Opus refuter. Documents new in this round, named from
their title pages: the Yamaha XC50J owner's manual (p. 1 text, "1TS-F8199-15
XC50J ... OWNER'S MANUAL") and the SYM T2 250i owner's manual (rendered
cover, "T2 250i OWNER'S MANUAL").

| claim | verdict | quote | source |
|---|---|---|---|
| W24 | kept | "Long-term Before storing your motorcycle for several months: 1. Follow all the instructions in the "Care" section of this chapter. 2. Turn the fuel cock lever to "ON"." | Yamaha XV250T1/XV250T1C OM, PDF p. 80 |
| W25 | kept | "Sealed battery If the vehicle is provided with a sealed battery, the only maintenance required is the check of its charge and recharging, if necessary." | Piaggio Beverly 125 SSM, PDF p. 77 |
| R21 | kept | "BE CAREFUL NOT TO REVERSE THE CONNECTIONS" / "3) Constant current battery charge mode - Charge current equal to 1/10 of the nominal capacity of the battery - Charge time: 5 h" | Piaggio Beverly 125 SSM, PDF p. 78 |
| R22 | kept | "IN THE EVENT OF PROLONGED PERIODS WITH THE VEHICLE NOT IN USE, CHARGE THE TRACTION BATTERY COMPLETELY AT LEAST ONCE EVERY THREE (3) MONTHS." (the page's footer reads "Vespa Elettrica Pre-delivery PRE DE - 9") | Vespa Elettrica SSM, PDF p. 9 |
| E20 | kept | "0–150 km (0–90 mi) Avoid prolonged operation above 1/3 throttle. After every hour of operation, stop the engine, and then let it cool for five to ten minutes." | Yamaha XC50J OM, PDF p. 34 |
| E21 | kept (see defect 9 on how the item frames it) | "It is better to drive in low speed after replacing the engine." | SYM T2 250i OM, PDF p. 17 |
| E22 | kept | "During the first 5 operating hours < 100 %" / "– Check the idle speed regularly. Guideline Idle speed 1,400 … 1,500 rpm Info The idle speed may change during the run-in time." | KTM 2022 250/300 EXC TPI OM, PDF p. 40 |
| E23 | kept | "MILEAGE FROM 1 TO 620 MILES IS THE MOST IMPORTANT RERIOD … THE NEW ENGINE CAN'T AFFORD TOO MUCH LOADING DURING THE FIRST 620 MILES." / "4.ABOVE 620 MILES" | Genuine Buddy 125 OM, PDF p. 27 |
| V24 | kept | "A = ( B - C) + D A: New shim thickness B: Recorded valve clearance C: Specified valve clearance D: Old shim thickness" | Honda CHF50 SM, PDF p. 65 |
| V25 | kept | "5. Install: breather 7Nm (0.7m kgf, 5.1ft lbf) valve cover (intake and exhaust) 7Nm (0.7m kgf, 5.1ft lbf)" | Yamaha YW125Y 2009 SM, PDF p. 64 |

**Round 2 result: 10 kept, 0 killed.** It found 17 defects in the
corrected text, all fixed. Two were round-1 fixes only partly applied:
the XV250T1's "(if available)", and the Vespa exception in valve item 1.
One contradicted a cited maker: winterization's "now, not in the
spring" oil change, against the Kymco's change after storage (p. 61).

### Round 3 — 2026-09-26: the 9 claims round 2 added, and its 17 fixes

One fresh-context Opus refuter.

| claim | verdict | quote | source |
|---|---|---|---|
| W26 | kept | "Whenever possible, perform any necessary periodic maintenance or repairs before storage so the scooter will be in good condition for riding when it is removed from storage." | Kymco People S 50/125/200 OM, `pdf/PeopleS-50-125-200.pdf` p. 60 |
| W27 | kept | "Removal from storage … 2. Change the engine oil if more than 1 month has passed since the start of storage." | Kymco People S 50/125/200 OM, p. 61 |
| W28 | kept | "IF THE VEHICLE IS EXPOSED FOR A PROLONGED PERIOD OF TIME TO TEMPERATURES BETWEEN 0°C AND -10°C, THE ON-BOARD ELECTRONICS WILL ONLY PERMIT A SLOW, PARTIAL TRACTION BATTERY CHARGING CYCLE, LASTING INDICATIVELY 6 HOURS AND TO A BATTERY STATE OF CHARGE OF 60%" | Vespa Elettrica SSM, `elettrica_ws.pdf` p. 9 |
| W29 | kept | "5. For vehicles with a carburetor: To prevent fuel deposits from building up, drain the fuel in the carburetor float chamber into a clean container. Retighten the drain bolt and pour the fuel back into the fuel tank." | Yamaha XVS95CL OM, `…BP6-28199-13_02.pdf` p. 81 |
| R23 | kept | "3) Constant current battery charge mode - Charge current equal to 1/10 of the nominal capacity of the battery - Charge time: 5 h" / "WHEN THE BATTERY IS REALLY FLAT (WELL BELOW 12.6V) IT MIGHT OCCUR THAT 5 HOURS OF RECHARGING ARE NOT ENOUGH … IT IS HOWEVER ESSENTIAL NOT TO EXCEED 8 HOURS OF CONTINUOUS RECHARGING" | Piaggio Beverly 125 SSM, `pdf/beverly125.pdf` p. 78 |
| E24 | kept | "During the first 1,000km, it is better to drive in low speed for running the engine in good condition and long life. Change the engine oil and clean the oil filter element after first 300km." | SYM T2 250i OM, `v2/sympdf/T2_Owner_Manual.pdf` p. 17 |
| V26 | kept | "Loosen the lock nut and adjust by turning the adjusting nut" | Kymco People / People S 250 SM, `pdf/kymco_people_s250_sm.pdf` p. 59 |
| V27 | kept | "Rotate the camshaft by rotating the drive pulley (crankshaft) counterclockwise several times. Recheck the valve clearance." | Honda CHF50 SM, `honda/chf50_service_mirror.pdf` p. 65 |
| V28 | kept | "Valve play, cold 0.07… 0.13 mm (0.0028… 0.0051 in)" (the only valve-play line on the page) | KTM 690 Enduro 2010 OM, `acquired/KTM/10_3211511_en_OM.pdf` p. 174 |

**Round 3 result: 9 kept, 0 killed.** 15 of the 17 fixes had landed and
2 had landed partly; it also found 4 new defects. All are corrected:
- the Beverly's three months, given its condition;
- SYM filed under a replaced engine, not new parts;
- "whenever possible" and the oil filter restored;
- "on a KTM" narrowed to the three KTM manuals that carry the warning.

One finding was half wrong: it said the KTM 690 Enduro has no
short-run warning, but the warning is on its p. 173 (claim W23). The
cross-check's control, withdrawing W23, reddened exactly that citation.
**W30**, added from round 3's own quote, is checked mechanically on its
page but has had no fourth round.
