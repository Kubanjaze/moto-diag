# Phase 359 — the round-1 refute input: every sentence 072 changes, with its neighbours

Generated from `migration_072_live_rows.py` and from the workflow rows of a live copy before and after 072. `-` is live's sentence, `+` what ships; `  ` lines are the unchanged neighbours.

## Workflow text

### C1. `generic_ppi_v1` description

  - Quick pre-purchase inspection covering engine, chassis, fluids, electrical.
  - For the full engine-side protocol see ppi_engine_v1.
  + Retired.
  + For a pre-purchase inspection use ppi_engine_v1 and ppi_chassis_v1.

### C2. `generic_winterization_v1` description

  - Seasonal storage: fuel stabilization, battery tender, oil change, storage position.
  - For the full protocol, with each maker's own figures cited, see winterization_v1.
  + Retired.
  + For seasonal storage use winterization_v1.

### C3. `ppi_engine_v1` description

    Engine-side protocol for buying a used ICE motorcycle: compression, leak-down, oil, fuel, starter/charging health and the visual checks.
  - Companion to generic_ppi_v1 (the quick check); for the full chassis-side protocol see ppi_chassis_v1.
  + For the full chassis-side protocol see ppi_chassis_v1.
    Figures in the item text cite the document they come from; where no document sets a figure the item says where the figure belongs — nothing here is invented.

### C4. `ppi_chassis_v1` description

    Chassis-side protocol for buying a used motorcycle: frame and crash evidence, steering head bearings, front fork, swingarm, wheel bearings, brakes and tires.
  - Companion to generic_ppi_v1 (the quick check) and ppi_engine_v1 (the engine-side protocol).
  + Companion to ppi_engine_v1 (the engine-side protocol).
    Figures in the item text cite the document they come from; where no document sets a figure the item says where the figure belongs — nothing here is invented.

### C5. `ppi_chassis_v1` item 1 instruction_text

    Ask for the service records, any crash story and the title status, and read the machine against them — new OEM plastics on a "never dropped" seller story is a question, not an answer.
  + Find the frame's stamped identification number and compare it with the number on the title or registration: the Vespa GTS 300 i.e. ABS manual recommends "checking that the chassis registration number stamped on the vehicle corresponds with that on the vehicle documentation" (PDF p. 34), and the Honda 2018 CB500F/FA owner's manual says the VIN is "required in order to register your motorcycle" (PDF p. 119).
  + Take the number's position from the machine's own manual.
    No document in the research library sets a frame-alignment measurement or a straightening tolerance, so none is invented here: a frame suspected of bending goes to the machine's own service manual or a specialist jig, and the KTM manual's position on repairs to its own frames is that they are not permitted — a damaged frame is a replaced frame (PDF p. 94).

### C6. `ppi_chassis_v1` item 1 expected_pass

  - Seams and paint consistent throughout, no welded repair outside factory joints, no bent mounts, history and title clean.
  + Seams and paint consistent throughout, no welded repair outside factory joints, no bent mounts, history and title clean, and the stamped frame number matching the title or registration.

### C7. `ppi_chassis_v1` item 1 expected_fail

  - Cracks, non-factory welds, repainted sections hiding damage, bent peg or lever mounts, a crash story that does not match the machine.
  + Cracks, non-factory welds, repainted sections hiding damage, bent peg or lever mounts, a crash story that does not match the machine, a stamped frame number that does not match the title or registration.

### C8. `ppi_chassis_v1` item 2 instruction_text

    Then turn the bars slowly lock to lock — they must move easily over the entire range with no detent position.
  - A notch at the straight-ahead position is dented bearing races.
  - The YW125Y manual's adjustment is made on the lower ring nut, 38 N·m initial tightening torque and 14 N·m final (PDF p. 94) — freshly adjusted but unchanged bearings only hide the notch until the grease settles.
  + The YW125Y manual's adjustment is made on the lower ring nut, 38 N·m initial tightening torque and 14 N·m final (PDF p. 94).

### C9. `ppi_chassis_v1` item 2 diagnosis_if_fail

  - Rocking play is loose adjustment or worn bearings; a notch at straight-ahead is brinelled races from an impact or years of load in one position — and the KTM manual warns that running with play damages the bearing seats in the frame as well (PDF p. 76).
  - Adjustment is cheap; dented races mean a steering-stem strip, and seats damaged at the frame belong to the frame item's walk-away.
  + Rocking play is loose adjustment or worn bearings; the KTM manual warns that running with play damages the bearing seats in the frame as well (PDF p. 76).
  + Adjustment is cheap; seats damaged at the frame belong to the frame item's walk-away.

## Known-issue text (live id, make, title, field)

### C10. known_issues 31 (Honda) “Thermostat failure — stuck closed causing overheating vs stuck open ca” — description

    A stuck-open thermostat is insidious — the engine runs cold, fuel economy drops 10-15%, oil doesn't reach temperature to boil off moisture and fuel contamination, and cold-running causes accelerated cylinder wear.
  - This affects all liquid-cooled motorcycles: Honda CBR600RR/1000RR, Kawasaki ZX-6R/ZX-10R and Ninja 650, Suzuki GSX-R600/750/1000 and V-Strom 650/1000, Yamaha YZF-R1/R6 and MT-09, and Harley-Davidson liquid-cooled models including Street 750, Pan America, and LiveWire.
  + This affects all liquid-cooled motorcycles: Honda CBR600RR/1000RR, Kawasaki ZX-6R/ZX-10R and Ninja 650, Suzuki GSX-R600/750/1000 and V-Strom 650/1000, Yamaha YZF-R1/R6 and MT-09, and Harley-Davidson liquid-cooled combustion models including Street 750 and Pan America.
  + The LiveWire is deliberately excluded from this list: the word thermostat does not appear once in the 108 sections of the LiveWire owner's manual, neither the 2020 nor the 2021 service-interval table carries a thermostat row, and the manual's own cooling-system troubleshooting topic does not list one among the causes of overheating.
  + Its coolant circuit exists to carry heat out of the motor and inverter, holds approximately 0.8 qt (0.72 L), and its only scheduled fluid event is a coolant replacement at 80,000 km (50,000 mi) by a dealer.
  + This entry makes no claim either way about a thermostat on the Street 750 or Pan America, which were not examined.
    The thermostat is a $15-30 part that should be replaced every 40,000-50,000 miles or whenever the cooling system is serviced.

### C11. known_issues 252 (Honda) “XR650L oil consumption and valve adjustment” — fix_procedure

    The intake valve tightens faster than exhaust because the lean factory jetting makes the combustion hotter, which accelerates seat wear.
  - After you uncork and rejet (Phase 31 issue #1), the valves tighten slower because the engine runs cooler.
  + After you uncork and rejet, the valves tighten slower because the engine runs cooler.
    Check oil every ride and carry 500ml in your pack on long rides.

### C12. known_issues 266 (Honda) “FI (Fuel Injection) light on — sensor and actuator faults” — fix_procedure

    1.
  - Read blink code (see Phase 33 issue #1 for procedure).
  + Read blink code.
    2.

### C13. known_issues 713 (BMW) “Integral ABS (servo-assisted) pump failure — 2001–2006 oilhead/hexhead” — fix_procedure

    3.
  - Read stored faults with a BMW-capable tool (see the Phase 215 dealer-mode entry) to distinguish a pressure fault from an electrical one.
  + Read stored faults with a BMW-capable tool to distinguish a pressure fault from an electrical one.
    4.

### C14. known_issues 714 (BMW) “Fuel-level strip sensor failure — hexhead R1200 and F800-family (2007–” — description

    It does not affect running; it just makes the gauge untrustworthy.
  - Phase 212 widened this entry from R1200GS-only after an audit found the same part fails the same way on the F800 family — on the F800GS the tank is under the seat and the sensor is reached from the pump plate above.
  + The same part fails the same way on the F800 family — on the F800GS the tank is under the seat and the sensor is reached from the pump plate above.
    Written from general knowledge — verify against the manual.

### C15. known_issues 859 (Energica) “Energica publishes 127 fault codes in standard SAE format — and a gene” — description

    This is the finding that most distinguishes Energica from the other electric marques in this corpus.
  - The manual carries a section headed 'Diagnostic codes' whose table columns read Label (DTC), Description, MIL, listing 127 distinct codes across 129 rows with plain-English descriptions (one label, U0182, appears twice, and one row carries two codes, P2158 + P0500; an earlier version of this entry said 110 codes and 65 powertrain — the count was corrected in Phase 247 from a row-by-row read of the rendered pages).
  + The manual carries a section headed 'Diagnostic codes' whose table columns read Label (DTC), Description, MIL, listing 127 distinct codes across 129 rows with plain-English descriptions (one label, U0182, appears twice, and one row carries two codes, P2158 + P0500).
    The format is standard SAE J2012: a single letter P, B, C or U followed by four alphanumeric characters, with no underscore, word prefix or separator — 82 powertrain, 17 chassis, 15 body, 13 network.

### C16. known_issues 885 (KTM) “KTM's 390 valve interval difference is 373cc versus 399cc, not Duke ve” — description

    Drawn from eleven KTM owner's manuals, the schedule tables read visually and confirmed by two independent passes.
  - Phase 225B recorded that the 390 Adventure and 390 Duke carry different valve intervals; the figures it saw are real, but the difference is between **engines**, not between the naked bike and the adventure bike.
  + Where the 390 Adventure and 390 Duke carry different valve intervals, the difference is between **engines**, not between the naked bike and the adventure bike.
    The 373cc engine — 390 Duke MY2022 and 390 Adventure MY2021 and MY2023 — schedules the valve check with a spark-plug change every **15,000 km**.

### C17. known_issues 885 (KTM) “KTM's 390 valve interval difference is 373cc versus 399cc, not Duke ve” — description

    On each engine the Duke and the Adventure agree.
  - What genuinely differs between siblings is the row's contents — the Adventure R row is the valve check alone, the Duke row bundles the plug — and the dusty-conditions qualifier on the Adventure air filter, both of which Phase 225B also recorded and which stand.
  - Its 'shorter interval than the Duke' sentence does not, and is corrected here.
  + What genuinely differs between siblings is the row's contents — the Adventure R row is the valve check alone, the Duke row bundles the plug — and the dusty-conditions qualifier on the Adventure air filter.

### C18. known_issues 885 (KTM) “KTM's 390 valve interval difference is 373cc versus 399cc, not Duke ve” — fix_procedure

    Do not schedule the valve check by age on any KTM: none of the eleven manuals marks the valve row in a month column.
  - Keep the Adventure-specific items Phase 225B records — the dusty-conditions air-filter qualifier and the Adventure-only rows — which are where the schedules genuinely differ.
  + Keep the Adventure-specific items — the dusty-conditions air-filter qualifier and the Adventure-only rows — which are where the schedules genuinely differ.

### C19. known_issues 892 (Aprilia) “Aprilia's 'Trust Aprilia Maintenance' sheets omit the valve check, and” — description

    They are a consumables list, not the schedule, and a shop that treats one as the schedule drops the valve check from the machine's service life entirely.
  - The valve interval itself could not be opened from an Aprilia schedule page in this phase; the figure this project carries — 20,000 and 40,000 km, halved for track, wet or dust — rests on the service manual cited at Phase 231 and on index snippets, and is recorded as unconfirmed here rather than restated as verified.
  + The valve interval itself could not be opened from an Aprilia schedule page; the figure of 20,000 and 40,000 km, halved for track, wet or dust, rests on a service manual and on index snippets, and is recorded as unconfirmed here rather than restated as verified.

### C20. known_issues 892 (Aprilia) “Aprilia's 'Trust Aprilia Maintenance' sheets omit the valve check, and” — causes

  - ["The official maintenance sheets are consumables lists with no valve row", "Their column structure looks like a schedule, so they are read as one", "The valve interval sits in the use-and-maintenance manual, which was not openable this phase", "Aggregator figures for the 660 family have no Aprilia document behind them"]
  + ["The official maintenance sheets are consumables lists with no valve row", "Their column structure looks like a schedule, so they are read as one", "The valve interval sits in the use-and-maintenance manual, which could not be opened", "Aggregator figures for the 660 family have no Aprilia document behind them"]

### C21. known_issues 893 (MV Agusta) “MV Agusta's coupon ladder starts with a merged cell, and reading it sh” — description

    On this ladder the valve check falls at C, E and G — every 30,000 km.
  - The F3 675/800 MY2020 maintenance manual carries the same 30,000 km valve figure, which resolves the interval Phase 234 could not confirm.
  + The F3 675/800 MY2020 maintenance manual carries the same 30,000 km valve figure.

### C22. known_issues 894 (MV Agusta) “The MV Agusta F4 shim diameter is still in no manufacturer document — ” — description

    Drawn from the MV Agusta Brutale ORO/S workshop manual and the maintenance manuals on disk, plus owner reports labelled as such.
  - Phase 234 deliberately did not print a shim diameter because sources disagreed.
  - This phase opened the workshop manual for the early four: it gives the clearances, names the part an adjustment pad under the valve cup, sends pad replacement to the F4 engine manual — and prints **no diameter**.
  + The workshop manual for the early four gives the clearances, names the part an adjustment pad under the valve cup, sends pad replacement to the F4 engine manual — and prints **no diameter**.
    Owner reports give 7.48 mm, the small Japanese size, with a thickness range; that is an owner report, and other sizes circulate.

### C23. known_issues 894 (MV Agusta) “The MV Agusta F4 shim diameter is still in no manufacturer document — ” — description

    Owner reports give 7.48 mm, the small Japanese size, with a thickness range; that is an owner report, and other sizes circulate.
  - The instruction from Phase 234 is therefore confirmed rather than replaced: measure a shim already in the engine before ordering, and do it before the camshafts are out.
  + So measure a shim already in the engine before ordering, and do it before the camshafts are out.

### C24. known_issues 898 (MV Agusta) “No MV Agusta 'rim band' part could be established — the documented spo” — description

    Drawn from the manufacturer's dealer communication and trade coverage of a 2017 campaign, checked against the fiche.
  - Phase 233 recorded that the Dragster's loose-spoke campaign was remedied by replacing the rear wheel because the nipples' surface treatment could not hold torque.
  - This phase looked for the part a shop would expect to stock for a tubeless spoked MV — a rim seal band — and could not establish one on the fiche.
  + The Dragster's loose-spoke campaign was remedied by replacing the rear wheel because the nipples' surface treatment could not hold torque.
  + No rim seal band — the part a shop would expect to stock for a tubeless spoked MV — could be established on the fiche.
    The documented remedy for the spoked-wheel defect is a **complete rear wheel**, fitted by the dealer, on a small production run over a stated window.

### C25. known_issues 898 (MV Agusta) “No MV Agusta 'rim band' part could be established — the documented spo” — fix_procedure

  - Check the frame number against the campaign first, and do not re-tension the spokes — Phase 233 records why the torque cannot hold.
  + Check the frame number against the campaign first, and do not re-tension the spokes: the nipples' surface treatment cannot hold torque.
    Where the machine is in the campaign, the remedy is a dealer-fitted rear wheel.

### C26. known_issues 898 (MV Agusta) “No MV Agusta 'rim band' part could be established — the documented spo” — fix_procedure

    Where the machine is in the campaign, the remedy is a dealer-fitted rear wheel.
  - Where it is not, treat the wheel as the unit of repair rather than searching for a band that this phase could not find.
  + Where it is not, treat the wheel as the unit of repair rather than searching for a band that could not be found on the fiche.
    Do not quote a rim band for an MV until a part number is confirmed on the fiche.

### C27. known_issues 899 (Aprilia) “The Aprilia V4 charging system exists in two families, and the fiche h” — description

  - Drawn from Aprilia's parts fiche, read this phase.
  + Drawn from Aprilia's parts fiche.
    The RSV4 and Tuono V4 carry two distinct flywheel-and-stator families: an early Mitsubishi-type assembly under one number, and a Kokusan-type family whose two earlier numbers have both been superseded into one current number.

### C28. known_issues 899 (Aprilia) “The Aprilia V4 charging system exists in two families, and the fiche h” — description

    Aftermarket sellers quote an engine-number threshold for the split; **no Aprilia document states that threshold**, and the fiche assigns by model year and variant instead.
  - So the fitted type is established from the machine, not from a number a seller quotes, and the reduced-magnet flywheel that Phase 237 names as the first suspect on a burnt stator exists for the Kokusan family only.
  + So the fitted type is established from the machine, not from a number a seller quotes, and the reduced-magnet flywheel exists for the Kokusan family only.

### C29. known_issues 899 (Aprilia) “The Aprilia V4 charging system exists in two families, and the fiche h” — fix_procedure

    Order the current superseded number for the Kokusan family; the fiche chain is recorded in the catalogue.
  - On the early Mitsubishi family, the aftermarket kit that replaces the original number exists but the reduced-magnet flywheel does not, so the Phase 237 flywheel-first differential applies to the later family only.
  + On the early Mitsubishi family, the aftermarket kit that replaces the original number exists but the reduced-magnet flywheel does not, so a flywheel-first diagnosis applies to the later family only.

### C30. known_issues 900 (BMW) “'BMW supplies the hexhead final drive only as a complete unit' is not ” — description

    A widely repeated statement, and one an earlier research pass in this project produced, is that BMW will not supply hexhead final-drive internals and sells only the complete drive.
  - This phase looked for the document and did not find it; what it found instead is that the crown-wheel bearing and the wheel-side bearing **carry individual BMW part numbers**, are stocked by independent retailers at two-figure prices, and have dimension-matched industrial equivalents.
  + No document stating it was found.
  + The crown-wheel bearing and the wheel-side bearing **carry individual BMW part numbers**, are stocked by independent retailers at two-figure prices, and have dimension-matched industrial equivalents.
    One owner's dealer account of being refused internals in a particular year is an owner report about one dealer, not a policy.

### C31. known_issues 901 (Ducati) “The Ducati Desmoquattro opening rocker arm is discontinued, and the re” — description

    Drawn from Ducati's parts fiche and specialist vendors.
  - The opening rocker arm for the 16-valve Desmoquattro — the part whose hard chrome flakes into the oil, per Phase 237 — is marked discontinued on the fiche for the models it was assigned to.
  + The opening rocker arm for the 16-valve Desmoquattro — the part whose hard chrome flakes into the oil — is marked discontinued on the fiche for the models it was assigned to.
    What remains is a choice between two routes with different economics: a specialist exchange re-chroming service at a modest per-arm price, or aftermarket tool-steel rockers at a four-figure price per set.

### C32. known_issues 902 (Triumph) “Triumph's fiche does not itemise the Street Triple idle-valve hoses th” — description

    Drawn from Triumph's parts fiche.
  - Phase 237 records that warm high idle on the Sagem-era triples is usually the rubber hoses from the idle air control valve to the intake ports perishing, not the valve.
  - This phase went to order those hoses and found that the fiche does not itemise them as such: the idle valve itself is listed with a VIN split between two numbers, and a set of hose numbers exists, but the specific IACV-to-port rubber hoses named by owners are not a separately orderable line.
  + Warm high idle on the Sagem-era triples is usually the rubber hoses from the idle air control valve to the intake ports perishing, not the valve.
  + The fiche does not itemise those hoses as such: the idle valve itself is listed with a VIN split between two numbers, and a set of hose numbers exists, but the specific IACV-to-port rubber hoses named by owners are not a separately orderable line.
    The orderable unit differs from the failing component, and a shop that orders the hose numbers on the fiche expecting the IACV hoses may receive something else.

### C33. known_issues 903 (KTM) “KTM Adventure tubeless rim seal bands and bead gaskets are KTM-only pa” — description

  - Drawn from KTM's parts fiche, read this phase.
  - The rim seal band that Phase 225B records KTM ageing out at five years regardless of wear is not a generic consumable — no aftermarket equivalent was found — and it is not one part.
  + Drawn from KTM's parts fiche.
  + The rim seal band that KTM ages out at five years regardless of wear is not a generic consumable — no aftermarket equivalent was found — and it is not one part.
    The fiche splits it by front wheel size, which follows whether the machine is an R variant or not, and the rear band and its bead gasket are separate numbers again.

### C34. known_issues 904 (KTM) “The KTM LC8 fiche pages for the balancer seal and starter freewheel ar” — description

  - Drawn from KTM's parts fiche, read this phase, with a correction from refutation.
  - The balancer shaft seal that Phase 237 names for an oily front intake, and the starter freewheel whose bolts back out into the stator, both show fiche assignments to the 950 Super Enduro R and the 990 Super Duke, with a 990 Adventure diagram also carrying the freewheel.
  + Drawn from KTM's parts fiche.
  + The balancer shaft seal and the starter freewheel whose bolts back out into the stator both show fiche assignments to the 950 Super Enduro R and the 990 Super Duke, with a 990 Adventure diagram also carrying the freewheel.
    A research pass concluded from that page that the parts are 'scoped to 950/990 only' and that no 1190 or 1290 is listed.

### C35. known_issues 905 (Aprilia) “Aprilia and Moto Guzzi share one parts catalogue, one supersession cha” — description

  - Drawn from the Piaggio Group's parts fiche and its technical bulletins, read this phase.
  - Phase 236 records that these two makes share a dealer tool.
  + Drawn from the Piaggio Group's parts fiche and its technical bulletins.
  + These two makes share a dealer tool.
    They also share a parts system: the same group catalogue serves both, supersessions are carried the same way, and the manufacturer's bulletin route for an out-of-warranty parts claim — a help-desk ticket, used for the Guzzi tappet kits — is a group process rather than a Guzzi one.

### C36. known_issues 1284 (KTM) “The Adventure and its Duke sibling share an engine and its valve inter” — description

  - Drawn from KTM's own owner's manuals, read from the service schedule tables, and corrected at Phase 238.
  + Drawn from KTM's own owner's manuals, read from the service schedule tables.
    The mid-size Adventure models are routinely serviced to the schedule of the naked machine they share an engine with, and on the valve interval that is correct: on each engine — the 373cc single, the 399cc single and the 890 twin — KTM's tables give the Duke and the Adventure the same valve interval.

### C37. known_issues 1284 (KTM) “The Adventure and its Duke sibling share an engine and its valve inter” — description

    The mid-size Adventure models are routinely serviced to the schedule of the naked machine they share an engine with, and on the valve interval that is correct: on each engine — the 373cc single, the 399cc single and the 890 twin — KTM's tables give the Duke and the Adventure the same valve interval.
  - An earlier version of this entry read a 373cc-versus-399cc difference as a Duke-versus-Adventure one; Phase 238 corrected it against eleven KTM manuals, and the figures themselves live there.
    What genuinely differs is the rest of the row: the Adventure schedules carry a dusty-conditions marker against the air filter that the Duke schedule does not, because the Adventure is expected to be ridden where the Duke is not, and the 890 Adventure schedule carries items the naked bike's does not — a clutch lubrication oil nozzle check and an early one-time spoke re-tension.

### C38. known_issues 1284 (KTM) “The Adventure and its Duke sibling share an engine and its valve inter” — fix_procedure

    Take the schedule from the manual for the exact model, variant and model year in front of you.
  - The valve interval follows the engine, and the Duke and Adventure agree on it — read the figure from the manual or from this project's Phase 238 comparison, and do not schedule it by age, since no KTM valve row carries a month mark.
  + The valve interval follows the engine, and the Duke and Adventure agree on it — read the figure from the manual, and do not schedule it by age, since no KTM valve row carries a month mark.
    Where the machine is ridden off-road or in dust, apply the Adventure schedule's dusty-conditions qualifier to the air filter rather than the nominal interval.

### C39. known_issues 1284 (KTM) “The Adventure and its Duke sibling share an engine and its valve inter” — fix_procedure

    Check for Adventure-only items when writing the job, including the clutch lubrication oil nozzle and the early one-time spoke re-tension.
  - Interval figures are deliberately not reproduced here, because Phase 238 owns them; read them from the machine's own manual.
  + Interval figures are deliberately not reproduced here; read them from the machine's own manual.

### C40. known_issues 1288 (KTM) “The 125 and 390 Duke are built in India by Bajaj — what that changes i” — description

    It is not evidence about how well the bike is made, and treating it that way leads a shop to diagnose from a prejudice instead of from the machine.
  - Scope note added at Phase 240: this covers the platform up to 2024.
  + This covers the platform up to 2024.
    The build location of the 2025-onward 390 platform could not be established from any manufacturer document — see the mid-size Adventure file — so do not carry this claim across that change.

### C41. known_issues 1332 (MV Agusta) “MV triple service intervals must come from the specific model's manual” — description

    For the F3 675 the commonly quoted valve interval could not be confirmed when this file was written.
  - **Phase 238 later opened MV's own maintenance manuals and resolved it**, and found that the 798cc triple sits on two different ladders in overlapping model years — so the instruction here is now documented rather than suspected: read the interval from the specific model's own manual, never from a sibling's.
  + **MV's own maintenance manuals resolve it**: the 798cc triple sits on two different ladders in overlapping model years — so the instruction here is now documented rather than suspected: read the interval from the specific model's own manual, never from a sibling's.
    The figures are in the European intervals file.

### C42. known_issues 1332 (MV Agusta) “MV triple service intervals must come from the specific model's manual” — fix_procedure

    2.
  - Take the F3 valve interval from the European intervals file or from the model's own maintenance manual — Phase 238 resolved it from MV's own documents — and never from a sibling model, which may sit on a different coupon ladder.
  + Take the F3 valve interval from the European intervals file or from the model's own maintenance manual, and never from a sibling model, which may sit on a different coupon ladder.
    3.

### C43. known_issues 1475 (Triumph) “The Triumph diagnostic socket looks like OBD-II but does not speak it ” — description

    And on the newest Euro 5 machines Triumph moved to a small red six-pin connector, which needs a six-pin-to-sixteen-pin adapter; the changeover is model-dependent, so check the actual machine rather than the year.
  - Specific transition years are deliberately not printed: Phase 236 found the timelines in circulation disagree by several model years, and a wrong year is worse than none when it decides which lead a shop orders.
  + Specific transition years are deliberately not printed: the timelines in circulation disagree by several model years, and a wrong year is worse than none when it decides which lead a shop orders.
    Identify the socket on the machine.

### C44. known_issues 4615 (Yamaha, Piaggio, Vespa, Honda, Kymco, SYM, Genuine) “What the regulator record shows for scooter CVTs — one campaign, and t” — description

    The only other campaigns using CVT vocabulary are automotive gearboxes, not scooter drivelines.
  - That is a floor and not a census, and the sweep that produced it demonstrated why.
  - Its enumeration was driven by the regulator's model index, and that index returns nothing for 2026 Vespa — so the sweep's own list omitted campaign 26V302000, a real 2026 Vespa campaign that the same sweep had already confirmed by campaign number.
  + That is a floor and not a census, and the sweep that produced it demonstrated why: its enumeration was driven by the regulator's model index, and that index returns nothing for 2026 Vespa — so the sweep's own list omitted campaign 26V302000, a real 2026 Vespa campaign that the same sweep had already confirmed by campaign number.
    A count built on the index is a lower bound by construction.

### C45. known_issues 4615 (Yamaha, Piaggio, Vespa, Honda, Kymco, SYM, Genuine) “What the regulator record shows for scooter CVTs — one campaign, and t” — description

    A count built on the index is a lower bound by construction.
  - The two index endpoints also disagree with each other, in both directions.
  - The 2013 Vespa 946 fuel-line campaign 14V364000 resolves only under its own model string, and for model year 2018 the model index returns one Vespa model while the make index for the same year returns 347 makes with Vespa absent.
  - Tested across seventeen makes and six model years, 25 of 102 combinations were contradictory — thirteen where the model index returns results while the make is missing from the make index, and twelve the other way round.
  - The contradictions concentrate in low-volume makes, though two touched high-volume ones.
  - Seventeen makes over six years is a sample and not a census.
  - Worse, the model index cannot be trusted as a source of query strings even for itself: the exact model string it supplies for 2018 Vespa returns nothing when used against the per-vehicle recall lookup.
  - And the per-vehicle lookup cannot distinguish a wrong name from a clean record.
  - A real make with a real model, a real make with a fabricated model, and a pair of nonsense strings all return the same HTTP 400 carrying the same sixty-six byte body reading that results were returned successfully with a count of zero.
  - A misspelled model name reads exactly like a machine with no campaigns.
  + The indexes fail in several further ways that are not specific to CVTs and are not repeated here; the companion entry titled 'The regulator's two indexes contradict each other, and an empty recall answer is not a clean record' carries them, and applies to any machine rather than only to a CVT.

### C46. known_issues 4615 (Yamaha, Piaggio, Vespa, Honda, Kymco, SYM, Genuine) “What the regulator record shows for scooter CVTs — one campaign, and t” — symptoms

  - ["scooter recall lookup", "is my scooter recalled", "cvt recall", "no recalls found", "recall search scooter"]
  + ["cvt recall", "scooter recall lookup", "variator recall", "is there a recall on my scooter cvt"]

### C47. known_issues 4615 (Yamaha, Piaggio, Vespa, Honda, Kymco, SYM, Genuine) “What the regulator record shows for scooter CVTs — one campaign, and t” — causes

  - ["A recall index that omits models its own campaign data contains", "A per-vehicle lookup whose empty answer is identical for a wrong name and a clean record"]
  + ["A campaign count built from an index that omits records the same sweep confirmed by campaign number"]

### C48. known_issues 4615 (Yamaha, Piaggio, Vespa, Honda, Kymco, SYM, Genuine) “What the regulator record shows for scooter CVTs — one campaign, and t” — fix_procedure

    3.
  - Do not use either index endpoint to decide whether a make or model has campaigns; they contradict each other and the data in both directions.
  - 4.
  - Do not read an empty per-vehicle response as a clean record, because a wrong model string returns the identical response.
  - 5.
  - Query by campaign number wherever one is known, which is the only route that returns the full record.
  + Do not conclude from this entry that a scooter CVT has no open campaign — conclude only that a corpus-wide sweep found one.

### C49. known_issues 5339 (Kymco) “Two Kymco service manuals, two opposite charging systems: the Agility ” — description

    The two books share a maker and a carburetted fuel system and almost nothing in this chapter: the Agility's yellow wire is its lighting coil (pp. 14-5, 14-6), the People's three yellow wires are its generator.
  - Page headers in the Agility 50 manual carry other names in places - Phase 254 found FILLY LX 50 headers, and five pages of this chapter read AGIKITY 50 - so every figure quoted here is from pages headed AGILITY 50 (14-2, 14-4).
  + Page headers in the Agility 50 manual carry other names in places - some read FILLY LX 50, and five pages of this chapter read AGIKITY 50 - so every figure quoted here is from pages headed AGILITY 50 (14-2, 14-4).
    Read from copies held in the project's research library; this entry did not fetch them from the maker.

### C50. known_issues 5340 (SYM) “One SYM manual gives the Jet 50/100 an illumination coil and the Jet E” — description

    SYM's Fiddle 50 service manual repeats the Jet 50/100 pattern - a white charging coil, a yellow illumination coil and a 12.6 ~ 13.6 V headlight control voltage (p. 15-2, p. 15-8).
  - The Joyride 125/150/200 manual (7429958, which Phase 254 also cited) has the Y-Y form and no lighting coil in its 203 pages: 'Charging coil Y - Y 0.4 - 0.8' ohm and 'Control Charging Voltage: 15.0 + 0.5 V / 2000 rpm' (p. 17-6, 17-7).
  + The Joyride 125/150/200 manual (7429958) has the Y-Y form and no lighting coil in its 203 pages: 'Charging coil Y - Y 0.4 - 0.8' ohm and 'Control Charging Voltage: 15.0 + 0.5 V / 2000 rpm' (p. 17-6, 17-7).
    So what the yellow wire is depends on the model, sometimes within one book: on a Jet 50/100 or Fiddle 50 there is a separate white charging coil and yellow is the illumination coil; on a Jet Euro or Joyride the yellow pair is the charging coil.

### C51. known_issues 5343 (Yamaha) “Yamaha's YW125 service manual gives two stator resistances a factor of” — description

  - Yamaha's 2009 service manual for the fuel-injected YW125Y - the name Zuma appears on none of its 338 pages; it identifies the machine by the code on its wiring diagram, 'YW125Y', and the link to the Zuma 125 name is Phase 253's cover-code record, not this manual - lists the charging system as 'System type AC magneto', model 5S9 (T-MORIC), 'Nominal output 14V 170W/5000r/min', a rectifier/regulator SH640E-11 (TAIGENE) with 'No load regulated voltage 14.1 ~ 14.9V' and 'Rectifier capacity 25A', and a YT7B-BS battery, 12V 6.5AH (p. 2-15).
  + Yamaha's 2009 service manual for the fuel-injected YW125Y - the name Zuma appears on none of its 338 pages; it identifies the machine by the code on its wiring diagram, 'YW125Y', and the link to the Zuma 125 name does not come from this manual - lists the charging system as 'System type AC magneto', model 5S9 (T-MORIC), 'Nominal output 14V 170W/5000r/min', a rectifier/regulator SH640E-11 (TAIGENE) with 'No load regulated voltage 14.1 ~ 14.9V' and 'Rectifier capacity 25A', and a YT7B-BS battery, 12V 6.5AH (p. 2-15).
    The same page gives 'Stator coil resistance/color 0.56 ~ 0.84' ohm between white and white.

