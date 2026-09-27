# Phase 262: the dry-run diff the operator approved for migration 071 (recovered)

**Recovered on 2026-09-27**, at the operator's request: "the 071 deploy diff I approved: if any copy survives in the temp folders, recover it into the repo now with a dated note."

Where it came from:
- **Source:** Phase 262's builder session scratchpad, at `/private/tmp/claude-501/-Users-lilquant-Projects-moto-diag/1f9f79a3-ddb3-422e-9ddd-52a4075ab5c9/scratchpad/s0/dryrun_diff.md`.
- **Written:** 2026-09-26 at 16:32 local time, by `deploy262.py dryrun`, against a copy of the backup `~/backups/motodiag/motodiag_pre262_20260926_163221.db`.
- **Role:** this is the diff shown to the operator before the live apply, and the one the operator approved.

How to check it:
- Everything after the line `<!-- original file below, unaltered -->` is the original file, byte for byte.
- The original's sha256 is `13a22578a282f76a94ffc6107cff431023a09d5704c39e4589d65dc23392c772`.
- To check it: `tail -n +20 docs/phases/completed/262_dryrun_diff.md | shasum -a 256`.

How it compares with what went live:
- **The builder's post-apply diff:** `live_diff.md`, written at 17:37, sha256 `89fec345f367144e28736152e18223e7ca3c4c9d4ee57f89fbf81383dac27a55`. It differs from this file in one line only, line 54: schema_version 71's applied time, `2026-09-26 20:32:22` on the copy and `2026-09-26 21:37:12` live (UTC).
- **The advisor session's own dry run:** made on a separate copy on 2026-09-26, it matched this scope. Live after the apply matched it row for row, apart from timestamps.

<!-- original file below, unaltered -->
## checklist_items: +21 added, 5 changed, 0 removed

### checklist_items rowid 6

**instruction_text**

- before: Add Sta-Bil or equivalent to fuel tank per manufacturer ratio. Run engine 5 minutes to circulate.
- after:  Fuel before storage differs by maker — a full tank with stabilizer and the engine run, a full tank with additive and no run, or an empty tank — and the makers' positions cannot be averaged. Follow the machine's own manual: winterization_v1 gives the fuel steps of the makers it cites, each with its document and page.

**expected_pass**

- before: Stabilizer circulated through fuel system
- after:  Fuel left as the machine's own manual asks, with stabilizer where it names one.

**expected_fail**

- before: Engine not run after adding — stabilizer did not reach carbs/injectors
- after:  Fuel left in a state the machine's own manual does not ask for.

### checklist_items rowid 7

**instruction_text**

- before: Change engine oil and filter with recommended winter weight (typically 10W-40).
- after:  Change the oil for storage as the machine's own manual lists it, with the oil it specifies; the makers differ on whether and when. winterization_v1 gives the oil steps of the makers it cites, each with its document and page.

### checklist_items rowid 8

**expected_pass**

- before: Battery on tender, reading float voltage (13.2V-13.6V)
- after:  Battery kept as the machine's own manual says; winterization_v1 compares several makers' battery steps, with their pages.

### checklist_items rowid 18

**description**

- before: Feel, not figures — the cited manuals give the procedure and the adjustment torques, not a play tolerance. Cited: the Yamaha YW125Y 2009 service manual (PDF p. 93): "Grasp the bottom of the front fork legs and gently rock the front fork"; the KTM 250/300 EXC owner's manual (PDF p. 76): "Play should not be detectable on the steering head bearing."
- after:  Feel, not figures — the cited manuals give the procedure and the adjustment torques, not a play tolerance. Cited: the Yamaha YW125Y 2009 service manual (PDF p. 93): "Grasp the bottom of the front fork legs and gently rock the front fork"; the KTM 2022 250/300 EXC TPI owner's manual (PDF p. 76): "Play should not be detectable on the steering head bearing."

**instruction_text**

- before: Raise the front wheel clear of the ground. Grasp the bottom of the fork legs and rock them to and fro in the direction of travel: the KTM manual's standard is that play should not be detectable (PDF p. 76); the YW125Y service manual calls the same movement binding or looseness (PDF p. 93). Then turn the bars slowly lock to lock — they must move easily over the entire range with no detent position. A notch at the straight-ahead position is dented bearing races. The YW125Y manual's adjustment is made on the lower ring nut, 38 N·m initial tightening torque and 14 N·m final (PDF p. 94) — freshly adjusted but unchanged bearings only hide the notch until the grease settles.
- after:  Raise the front wheel clear of the ground. Grasp the bottom of the fork legs and rock them to and fro in the direction of travel: the KTM manual's standard is that play should not be detectable (PDF p. 76); the YW125Y service manual checks the same movement for binding or looseness (PDF p. 93). Then turn the bars slowly lock to lock — they must move easily over the entire range with no detent position. A notch at the straight-ahead position is dented bearing races. The YW125Y manual's adjustment is made on the lower ring nut, 38 N·m initial tightening torque and 14 N·m final (PDF p. 94) — freshly adjusted but unchanged bearings only hide the notch until the grease settles.

### checklist_items rowid 56

**description**

- before: The makers agree on a full charge and disagree on how often. Cited: the Honda CB500F owner's manual removes the battery, charges it fully and keeps it shaded and ventilated, or disconnects the negative terminal if it stays in (PDF p. 117). Recharge intervals, each with its condition: a removed, stored battery every two weeks in the Honda PCX150 (2013–2017) service manual (PDF p. 390); a removed battery once a month in the Yamaha XVS95CL owner's manual (PDF p. 81); about every 4 months in store, and every 2 months at the latest if left connected, in the BMW R 850 R / R 1150 R Maintenance Instructions (PDF p. 49); a sealed battery's charge checked and, if necessary, recharged every six months while the vehicle is stored in open circuit in the Piaggio Beverly 125 service station manual (PDF pp. 77–78); the same manual says that if the vehicle is not used for some time (1 month or more) the battery needs periodic recharging, and runs down completely in the course of three months (PDF p. 78).
- after:  The makers agree on a full charge and disagree on how often. Cited: the Honda CB500F owner's manual removes the battery, charges it fully and keeps it shaded and ventilated, or disconnects the negative terminal if it stays in (PDF p. 117). Recharge intervals, each with its condition: a removed, stored battery every two weeks in the Honda PCX150 (2013–2017) service manual (PDF p. 390); a removed battery once a month in the Yamaha XVS95CL owner's manual (PDF p. 81); about every 4 months in store, and every 2 months at the latest if left connected, in the BMW R 850 R / R 1150 R Maintenance Instructions (PDF p. 49); a sealed battery's charge checked and, if necessary, recharged every six months while the vehicle is stored in open circuit in the Piaggio Beverly 125 service station manual (PDF pp. 77–78); in a caution box on the same page, which also warns about a low electrolyte level before first use, the manual says that if the vehicle is not used for some time (1 month or more) the battery needs periodic recharging, and runs down completely in the course of three months (PDF p. 78; the same words are in its troubleshooting table, PDF p. 55). The manual gives both figures and does not reconcile them: the six-month check is for a vehicle stored in open circuit, and the caution does not say whether the battery is connected.
- added rowids 80–100 (21 items)
## schema_version: +1 added, 0 changed, 0 removed
- added rowid 70: (71, '2026-09-26 20:32:22')
## workflow_templates: +3 added, 0 changed, 0 removed
- added rowid 13: (13, 'crash_support_v1', 'Crash support — post-crash inspection and the California salvage decision')
- added rowid 14: (14, 'track_prep_v1', 'Track-day preparation')
- added rowid 15: (15, 'emissions_v1', 'Emissions and smog compliance — California first')
