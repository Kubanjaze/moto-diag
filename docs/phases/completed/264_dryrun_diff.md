# Phase 264: the dry-run diff the operator approved for migration 070 (recovered)

**Recovered on 2026-09-27**, at the operator's request: "recover the 070 diff from batch 2's temp folder into the repo, same treatment as 071's (dated note, byte-for-byte, sha256). if it's already gone, record the loss." It had not gone.

Where it came from:
- **Source:** Phase 264's builder session scratchpad, at `/private/tmp/claude-501/-Users-lilquant-Projects-moto-diag/146de57a-56a5-4b7d-ae87-2637e1720055/scratchpad/s0/dryrun_diff.md`.
- **Written:** 2026-09-26 at 13:19 local time, by that session's `deploy264.py`, against a copy of the backup `~/backups/motodiag/motodiag_pre264_20260926_131946.db`.
- **Role:** this is the diff shown to the operator before migration 070's live apply, and the one the operator approved.

How to check it:
- Everything after the line `<!-- original file below, unaltered -->` is the original file, byte for byte.
- The original's sha256 is `2c80d4c1a1b8c200adf7464aae58363d3cb7ca98d2471f1c3cf75f7f7d4655c5`.
- To check it: `tail -n +20 docs/phases/completed/264_dryrun_diff.md | shasum -a 256`.

How it compares with what went live:
- **The builder's post-apply diff:** `live_diff.md`, written at 14:09, sha256 `280af804adc7debf4900ecb2ec61281274b845ac12df281961314df36cabdb69`. It differs from this file in two lines only, both timestamps: schema_version 70's applied time (line 45) and `workflow_templates` row 2's `updated_at` (line 58). Both read `2026-09-26 17:19:46` on the copy and `2026-09-26 18:09:51` live (UTC).
- **The advisor session's own check, re-run on 2026-09-27:** its independent dry run of 070 was compared with `~/backups/motodiag/motodiag_pre262_20260926_163221.db`, the backup of live taken just before 071. The result: 0 differences apart from 6 timestamp-only rows, schema 70 on both, and the `known_issues` hash `60fec9b4e4e1dfb1` unchanged.

<!-- original file below, unaltered -->
## checklist_items: +28 added, 3 changed, 0 removed

### checklist_items rowid 18

**description**

- before: Feel, not figures — the cited manuals give the procedure and the adjustment torques, not a play tolerance. Cited: the Yamaha Zuma 125 2009 service manual (PDF p. 93): "Grasp the bottom of the front fork legs and gently rock the front fork"; the KTM 250/300 EXC owner's manual (PDF p. 76): "Play should not be detectable on the steering head bearing."
- after:  Feel, not figures — the cited manuals give the procedure and the adjustment torques, not a play tolerance. Cited: the Yamaha YW125Y 2009 service manual (PDF p. 93): "Grasp the bottom of the front fork legs and gently rock the front fork"; the KTM 250/300 EXC owner's manual (PDF p. 76): "Play should not be detectable on the steering head bearing."

**instruction_text**

- before: Raise the front wheel clear of the ground. Grasp the bottom of the fork legs and rock them to and fro in the direction of travel: the KTM manual's standard is that play should not be detectable (PDF p. 76); the Zuma 125 service manual calls the same movement binding or looseness (PDF p. 93). Then turn the bars slowly lock to lock — they must move easily over the entire range with no detent position. A notch at the straight-ahead position is dented bearing races. The Zuma manual's adjustment is made on the lower ring nut, 38 N·m initial tightening torque and 14 N·m final (PDF p. 94) — freshly adjusted but unchanged bearings only hide the notch until the grease settles.
- after:  Raise the front wheel clear of the ground. Grasp the bottom of the fork legs and rock them to and fro in the direction of travel: the KTM manual's standard is that play should not be detectable (PDF p. 76); the YW125Y service manual calls the same movement binding or looseness (PDF p. 93). Then turn the bars slowly lock to lock — they must move easily over the entire range with no detent position. A notch at the straight-ahead position is dented bearing races. The YW125Y manual's adjustment is made on the lower ring nut, 38 N·m initial tightening torque and 14 N·m final (PDF p. 94) — freshly adjusted but unchanged bearings only hide the notch until the grease settles.

### checklist_items rowid 19

**description**

- before: Cited: the Yamaha Zuma 125 2009 service manual's front-fork check (PDF p. 95): inner tube "Damage/scratches → Replace", oil seal "Oil leakage → Replace", and "Push down hard on the handlebar several times and check if the front fork rebounds smoothly. Rough movement → Repair." Its chassis specifications (PDF p. 34) give that machine's fork spring a 252.1 mm standard free length with a 247 mm limit, and the inner tube a 0.2 mm bending limit.
- after:  Cited: the Yamaha YW125Y 2009 service manual's front-fork check (PDF p. 95): inner tube "Damage/scratches → Replace", oil seal "Oil leakage → Replace", and "Push down hard on the handlebar several times and check if the front fork rebounds smoothly. Rough movement → Repair." Its chassis specifications (PDF p. 34) give that machine's fork spring a 252.1 mm standard free length with a 247 mm limit, and the inner tube a 0.2 mm bending limit.

**instruction_text**

- before: Hold the machine upright, pull the front brake, and push down hard on the bars several times: the fork must rebound smoothly — the Zuma 125 service manual's check is exactly this, and rough movement is a repair (PDF p. 95). Then look at each leg: run a gloved finger or a thin plastic card over the chrome above the seal line for nicks and pitting, and inspect the seal lips and the back of the dust wipers for an oil ring — oil on the stanchion or a film on the slider is a seal already weeping, and the manual's rule for a weeping oil seal is replace, and for a damaged or scratched inner tube, replace (PDF p. 95). A leg that has been weeping a while feels dry and sticky on the first compression. Sight along both legs from the side for a bend: a twisted or bent fork is crash evidence, and the frame item gets the story.
- after:  Hold the machine upright, pull the front brake, and push down hard on the bars several times: the fork must rebound smoothly — the YW125Y service manual's check is exactly this, and rough movement is a repair (PDF p. 95). Then look at each leg: run a gloved finger or a thin plastic card over the chrome above the seal line for nicks and pitting, and inspect the seal lips and the back of the dust wipers for an oil ring — oil on the stanchion or a film on the slider is a seal already weeping, and the manual's rule for a weeping oil seal is replace, and for a damaged or scratched inner tube, replace (PDF p. 95). A leg that has been weeping a while feels dry and sticky on the first compression. Sight along both legs from the side for a bend: a twisted or bent fork is crash evidence, and the frame item gets the story.

**diagnosis_if_fail**

- before: Weeping seals mean a seal and oil service at minimum; a nick in the chrome tears new seals, so a nicked stanchion prices a tube. For spring and straightness figures, the machine's own manual owns the numbers: the Zuma 125's fork spring measures 252.1 mm free against a 247 mm limit and its inner tube's bending limit is 0.2 mm (PDF p. 34); the CHF50's fork spring is 128.5 mm against a 125.9 mm service limit (PDF p. 12).
- after:  Weeping seals mean a seal and oil service at minimum; a nick in the chrome tears new seals, so a nicked stanchion prices a tube. For spring and straightness figures, the machine's own manual owns the numbers: the YW125Y's fork spring measures 252.1 mm free against a 247 mm limit and its inner tube's bending limit is 0.2 mm (PDF p. 34); the CHF50's fork spring is 128.5 mm against a 125.9 mm service limit (PDF p. 12).

### checklist_items rowid 21

**description**

- before: Cited: the Yamaha Zuma 125 2009 service manual's maintenance table (PDF p. 55): wheels — check runout and for damage; wheel bearings — "Check bearings for smooth operation. Replace if necessary." The Honda CHF50 service manual gives axle runout a 0.20 mm service limit (PDF p. 218) and wheel rim runout 2.0 mm radial and 2.0 mm axial service limits (PDF pp. 12, 242), and names faulty wheel bearings and a bent front axle as causes of a front wheel that turns hard (PDF p. 217), and worn or damaged wheel bearings and a bent axle behind a wheel that will not spin freely by hand (PDF p. 314).
- after:  Cited: the Yamaha YW125Y 2009 service manual's maintenance table (PDF p. 55): wheels — check runout and for damage; wheel bearings — "Check bearings for smooth operation. Replace if necessary." The Honda CHF50 service manual gives axle runout a 0.20 mm service limit (PDF p. 218) and wheel rim runout 2.0 mm radial and 2.0 mm axial service limits (PDF pp. 12, 242), and names faulty wheel bearings and a bent front axle as causes of a front wheel that turns hard (PDF p. 217), and worn or damaged wheel bearings and a bent axle behind a wheel that will not spin freely by hand (PDF p. 314).

**instruction_text**

- before: Raise each wheel in turn and spin it: it must turn freely and quietly — the CHF50 manual's drag causes are brake dragging, worn or damaged wheel bearings, and a bent axle (PDF p. 314). Grasp the wheel at opposite sides and rock it hard: any movement you can feel is bearing play (a drum-brake machine drags lightly through its shoes — feel past it); the Zuma 125 manual's table check is bearings for smooth operation, replace if necessary (PDF p. 55). Watch the rim at the valve while it spins for hop and wobble, and check the rim for dents, flat spots and cracked or missing spokes on a laced wheel. No document in the research library sets a wheel-bearing play figure, so none is invented here: the hand test is the standard — smooth and silent passes, any grinding, rumble or knock fails — and a borderline case belongs to the machine's own manual, whose runout limits for its own parts are figures like the CHF50's 0.20 mm axle and 2.0 mm rim limits (PDF pp. 12, 218, 242).
- after:  Raise each wheel in turn and spin it: it must turn freely and quietly — the CHF50 manual's drag causes are brake dragging, worn or damaged wheel bearings, and a bent axle (PDF p. 314). Grasp the wheel at opposite sides and rock it hard: any movement you can feel is bearing play (a drum-brake machine drags lightly through its shoes — feel past it); the YW125Y manual's table check is bearings for smooth operation, replace if necessary (PDF p. 55). Watch the rim at the valve while it spins for hop and wobble, and check the rim for dents, flat spots and cracked or missing spokes on a laced wheel. No document in the research library sets a wheel-bearing play figure, so none is invented here: the hand test is the standard — smooth and silent passes, any grinding, rumble or knock fails — and a borderline case belongs to the machine's own manual, whose runout limits for its own parts are figures like the CHF50's 0.20 mm axle and 2.0 mm rim limits (PDF pp. 12, 218, 242).
- added rowids 52–79 (28 items)
## schema_version: +1 added, 0 changed, 0 removed
- added rowid 69: (70, '2026-09-26 17:19:46')
## workflow_templates: +4 added, 1 changed, 0 removed

### workflow_templates rowid 2

**description**

- before: Seasonal storage: fuel stabilization, battery tender, oil change, storage position. Track N phase 264 expands.
- after:  Seasonal storage: fuel stabilization, battery tender, oil change, storage position. For the full protocol, with each maker's own figures cited, see winterization_v1.

**updated_at**

- before: None
- after:  2026-09-26 17:19:46
- added rowid 9: (9, 'winterization_v1', 'Winterization — seasonal storage')
- added rowid 10: (10, 'de_winterization_v1', 'De-winterization — return to service')
- added rowid 11: (11, 'engine_break_in_v1', 'Engine break-in')
- added rowid 12: (12, 'valve_adjustment_v1', 'Valve clearance check and adjustment')
