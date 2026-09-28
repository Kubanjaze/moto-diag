# Phase 359 — the round-2 refute input: round 1's fixes, with their neighbours

`-` is the text round 1 refuted, `+` what ships now; unmarked lines are unchanged neighbours.

## Workflow text

### C1. `generic_ppi_v1` description

    Retired.
  - For a pre-purchase inspection use ppi_engine_v1 and ppi_chassis_v1.
  + For a pre-purchase inspection use ppi_chassis_v1, and ppi_engine_v1 on a machine with an engine.

### C2. `ppi_engine_v1` description

    Engine-side protocol for buying a used ICE motorcycle: compression, leak-down, oil, fuel, starter/charging health and the visual checks.
  - For the full chassis-side protocol see ppi_chassis_v1.
  + For the chassis-side protocol see ppi_chassis_v1.
    Figures in the item text cite the document they come from; where no document sets a figure the item says where the figure belongs — nothing here is invented.

### C3. `ppi_chassis_v1` item 1 expected_fail

  - Cracks, non-factory welds, repainted sections hiding damage, bent peg or lever mounts, a crash story that does not match the machine, a stamped frame number that does not match the title or registration.
  + Cracks, non-factory welds, repainted sections hiding damage, bent peg or lever mounts, a crash story that does not match the machine, a stamped frame number that does not match the title or registration, or that has been altered.

### C4. `ppi_chassis_v1` item 2 diagnosis_if_fail

  - Rocking play is loose adjustment or worn bearings; the KTM manual warns that running with play damages the bearing seats in the frame as well (PDF p. 76).
  + Rocking play is loose adjustment or worn bearings; the KTM manual warns that running with play can damage the bearings and the bearing seats in the frame over time (PDF p. 76).
  + For a detent position the same manual says to adjust the steering head bearing play, then check the bearing and change it if necessary (PDF p. 76).
    Adjustment is cheap; seats damaged at the frame belong to the frame item's walk-away.

## Known-issue text

### C5. known_issues 899 (Aprilia) “The Aprilia V4 charging system exists in two families, and the fiche h” — description

    Aftermarket sellers quote an engine-number threshold for the split; **no Aprilia document states that threshold**, and the fiche assigns by model year and variant instead.
  - So the fitted type is established from the machine, not from a number a seller quotes, and the reduced-magnet flywheel exists for the Kokusan family only.
  + So the fitted type is established from the machine, not from a number a seller quotes, and the reduced-magnet flywheel offered for a burnt stator (see the entry titled 'Aprilia V4 charging failure: the flywheel is the first suspect, and replacing only the stator reproduces the fault') exists for the Kokusan family only.

### C6. known_issues 902 (Triumph) “Triumph's fiche does not itemise the Street Triple idle-valve hoses th” — description

    Drawn from Triumph's parts fiche.
  - Warm high idle on the Sagem-era triples is usually the rubber hoses from the idle air control valve to the intake ports perishing, not the valve.
  + Owner reports say warm high idle on the Sagem-era triples is usually the rubber hoses from the idle air control valve to the intake ports perishing, not the valve.
    The fiche does not itemise those hoses as such: the idle valve itself is listed with a VIN split between two numbers, and a set of hose numbers exists, but the specific IACV-to-port rubber hoses named by owners are not a separately orderable line.

### C7. known_issues 1288 (KTM) “The 125 and 390 Duke are built in India by Bajaj — what that changes i” — description

    It is not evidence about how well the bike is made, and treating it that way leads a shop to diagnose from a prejudice instead of from the machine.
  - This covers the platform up to 2024.
  + This entry covers the platform up to 2024.
    The build location of the 2025-onward 390 platform could not be established from any manufacturer document — see the mid-size Adventure file — so do not carry this claim across that change.

### C8. known_issues 1332 (MV Agusta) “MV triple service intervals must come from the specific model's manual” — fix_procedure

    2.
  - Take the F3 valve interval from the European intervals file or from the model's own maintenance manual, and never from a sibling model, which may sit on a different coupon ladder.
  + Take the F3 valve interval from the model's own maintenance manual, and never from a sibling model, which may sit on a different coupon ladder.
    3.

