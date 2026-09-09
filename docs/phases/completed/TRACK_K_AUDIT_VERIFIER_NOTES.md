# Track K closure audit — per-finding verifier notes

Verbatim output of the audit's verification pass, committed at the request of the
Phase 240B session, which was told these notes were unavailable. They were not lost —
they were in the workflow journal and had simply never been written to the repo.

Each block is one finding, the verdict that reproduced (or rejected) it, and the
verifier's `corrected_fix` where it gave one. **A `real: false` verdict means the
finding did NOT hold up** — those are recorded too, so nobody re-litigates them.


---

## Dimension: contradictions

**Auditor summary.** Audited the 30 Track K knowledge files (211-240), the 6 Track K DTC files, the adapter catalogue and the parts catalogue for claims about the same subject asserted differently in different phases. Found 16 cross-phase contradictions. The pattern is consistent and diagnosable: the four cross-make files (236 tooling, 237 differentials, 238 intervals, 239 parts) were written against primary documents and repeatedly corrected the per-make files that came before them — but the correction was recorded only in the new file. Phase 238 back-propagated exactly once (known_issues_ktm_adventure.json entry 7 carries "corrected at Phase 238"); every other correction left the superseded per-make entry shipping unchanged, so the corpus now asserts both answers. The most dangerous cases are three per-make entries from the BMW block (211, 215) that Phase 237/235 contradict on procedure, not emphasis: setting tension on a stretch-fit belt that must never be tensioned, blaming a sealed grease-packed bearing on oil-change intervals, and denying a Euro 4 OBD access entitlement that a regulation-sourced entry quotes verbatim from EU law. Two further contradictions run the other way — a cross-make file over-generalising across a make (KTM classed wholesale as shim-under-bucket; KTM competition models swept into a km valve ladder). The staged Gate 12 test checks campaign numbers, provenance vocabulary, file existence and counts; it contains no cross-file consistency assertion, so none of these would be caught by the gate.


### [CONFIRMED] BMW alternator belt: Phase 211 tells you to tension a belt Phase 237 says tensioning destroys

- **severity (auditor):** critical
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_bmw_r_series.json (entry 7) vs /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_differentials.json (entry 1)`

**Evidence.**

known_issues_bmw_r_series.json[7], "Alternator drive-belt wear — belt-driven alternator (oilhead, hexhead, R nineT)", model "R-series (belt alternator)", 1994-2023: "Replacement is straightforward but tension must be set correctly — an over-tight belt loads the alternator bearing." Fix step 3: "Replace the belt and set tension per the manual — do not guess it; both slack and over-tight cause failures." Cause: "Alternator bearing wear from over-tight belt".

known_issues_european_differentials.json[1], "BMW boxer alternator belts come in two incompatible types, and tensioning the stretch-fit one destroys it", model "Oilhead 1993–2003 poly-V; 2004-on 50A and all hexhead R1200 ELAST": "From mid-2003 BMW moved to an **ELAST stretch-fit** belt — different designations, different part numbers — which is set by fixed length between the pulley flanges, runs on a freewheeling alternator pulley, and is **never** re-tensioned. Treating an ELAST belt like a poly-V and adjusting it damages it."

Corroborated by the catalogue rows Phase 239 wrote in /Users/lilquant/Projects/moto-diag/src/motodiag/advanced/data/parts.json: BMW 11318528385 "Ribbed V-belt, ELAST stretch-fit", model_pattern R1200% 2005-2014 and R nineT% 2014-2023, notes "ELAST: fitted by length, never re-tensioned (Phase 237)".

**Auditor's recommended fix.**

Phase 237 is right — ELAST belts have no adjuster and a freewheeling pulley. Rescope known_issues_bmw_r_series.json[7] to the pre-mid-2003 poly-V (year_end ~2003, model "R-series oilhead, poly-V belt alternator"), and replace the tensioning steps with a pointer to the ELAST entry for anything later. If the entry is to keep its 1994-2023 range, it must carry the two-belt split in its own fix procedure.

**Verifier verdict — real=True.**

Reproduced independently; both quotes are verbatim and the conflict is substantive, not a scope difference.

known_issues_bmw_r_series.json[7] (title "Alternator drive-belt wear — belt-driven alternator (oilhead, hexhead, R nineT)", model "R-series (belt alternator)", year_start 1994, year_end 2023, source "model-generated") asserts the poly-V architecture across the whole span: description "the belt-driven boxers use a poly-V belt from the crank to a car-style alternator... Replacement is straightforward but tension must be set correctly — an over-tight belt loads the alternator bearing"; causes "Belt tension incorrect", "Alternator bearing wear from over-tight belt"; fix step 3 "Replace the belt and set tension per the manual — do not guess it; both slack and over-tight cause failures"; parts_needed "Alternator poly-V belt".

known_issues_european_differentials.json[1] (1993–2013) says the opposite for the later population: "From mid-2003 BMW moved to an **ELAST stretch-fit** belt... which is set by fixed length between the pulley flanges, runs on a freewheeling alternator pulley, and is **never** re-tensioned. Treating an ELAST belt like a poly-V and adjusting it damages it." Phase 237's ROADMAP row confirms this was the phase's deliberate finding ("tensioning the ELAST stretch-fit destroys it").

Corroboration is real: parts.json carries slug bmw-11318528385-alternator-belt, "Ribbed V-belt, ELAST stretch-fit, marked 4PK582", model_pattern R1200% (2005–2014) with notes "ELAST: fitted by length, never re-tensioned (Phase 237)", plus bmw-11318528385-alternator-belt--r-ninet, model_pattern R nineT%, 2014–2023, same ELAST belt. So the ELAST population includes exactly the hexhead and R nineT years entry 7 claims as poly-V.

Reachability checked in code, not assumed: issues_repo._known_issue_filters applies "(year_start IS NULL OR year_start <= ?) AND (year_end IS NULL OR year_end >= ?)" and orders by severity DESC, title. Both entries are severity "medium", and "Alternator drive-belt wear…" sorts before "BMW boxer alternator belts…", so entry 7 is returned first for 2004–2013. For 2014–2023 the differentials entry (year_end 2013) does not match at all, so entry 7's tensioning procedure is the ONLY belt guidance a year-filtered R nineT search reaches — worse than the finding states.

One extra defect the auditor missed, which is corpus-internal: known_issues_european_differentials.json[2] establishes that from the 2013 water-cooled boxer "the alternator is integral to the crankcase... driven by a gear-driven permanent-magnet rotor" — i.e. no belt at all. Entry 7's 1994–2023 span therefore also sweeps in LC R1200/R1250 machines that have no drive belt; only the R nineT keeps one past 2013.

The recommended fix, however, is wrong as written (see corrected_fix): rescoping to year_end ~2003 breaks a passing test.

**Verifier's corrected_fix.**

Take the auditor's SECOND option, not its first. Rescoping entry 7 to year_end ~2003 breaks the tree:

- tests/test_phase211_bmw_r_series.py::TestBMWRSeriesData::test_every_generation_is_covered is parametrised (2018, 2) with the comment "# wethead: water pump, belt-alternator span" and asserts len(rows) >= 2 for search_known_issues(year=2018, make="BMW"). Only entries 7 and 8 cover 2018 (I checked every year: 2016/2018/2022 each return exactly those two). Ending entry 7 at 2003 leaves one row and the test fails. tests/test_phase211*.py and tests/test_phase237*.py currently pass 52/52.
- It would also strand the R nineT: the differentials ELAST entry stops at 2013, so a 2014–2023 year-filtered search would surface no belt guidance at all while parts.json still hands out the ELAST belt for R nineT% 2014–2023.

Correct fix — keep year_start 1994 / year_end 2023 and make entry 7 self-contained (there is no cross-reference convention in this corpus; I grepped, entries never point at each other):

1. description: drop the flat "uses a poly-V belt... tension must be set correctly" claim and state the split — poly-V with an adjuster up to mid-2003; ELAST stretch-fit from mid-2003 on the hexhead R1200 and the R nineT, set by fitted length between the pulley flanges on a freewheeling pulley and never re-tensioned; the part number is the discriminator, not appearance. Add that the 2013-on liquid-cooled boxers have no drive belt at all (internal gear-driven alternator), so the tail of the span is the R nineT.
   CONSTRAINT: tests/test_phase211_bmw_r_series.py:111 test_every_bmw_description_admits_its_origin requires "general knowledge" (case-insensitive) in every description in this file, and lines 102/109 require source == "model-generated" for all twelve. Keep the existing "Written from general knowledge — verify..." clause and do not upgrade source.
2. fix_procedure step 3: replace "Replace the belt and set tension per the manual — do not guess it" with "Identify the belt by part number before fitting. Poly-V: set tension to the adjuster specification and observe the scheduled re-tension. ELAST: fit to the specified length between the pulley flanges and make no tension adjustment — there is none, and attempting one is the failure."
3. causes: scope "Belt tension incorrect" and "Alternator bearing wear from over-tight belt" to the poly-V, and add "ELAST stretch-fit belt damaged by being treated as a poly-V and adjusted".
4. parts_needed: "Alternator poly-V belt" → "Alternator belt — poly-V or ELAST to the part number for the alternator fitted" (parts.json slugs bmw-11318528385-alternator-belt, bmw-11318528385-alternator-belt--r-ninet, bmw-12317681841-alternator-belt).
5. Do not introduce a tension figure or a fitted length — the entry is model-generated and the corpus's deliberate-absence discipline applies; keep it procedural and route to the fiche by production month, as parts.json already does.
6. Optional and secondary: widen known_issues_european_differentials.json[1] year_end from 2013 to 2023 so the ELAST warning is year-reachable for the R nineT. It is corroborated by the R nineT parts row, and I found no test pinning 2013 in tests/test_phase237_european_differentials.py. Not required once entry 7 is self-contained.

Re-run tests/test_phase211_bmw_r_series.py, tests/test_phase212_bmw_gs_adventure.py (its BOXER_ONLY list at line 47 contains "alternator belt" and asserts it is absent from the F file) and tests/test_phase237_european_differentials.py after the edit.


### [CONFIRMED] BMW Euro 4 OBD: Phase 215 says no legislated layer exists before Euro 5; Phase 235 quotes EU law saying it begins at Euro 4

- **severity (auditor):** critical
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_bmw_electrical.json (entry 0) vs /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_aprilia_mv_electrical.json (entry 3)`

**Evidence.**

known_issues_bmw_electrical.json[0], source model-generated: "Motorcycles carry that layer only from Euro 5 (roughly 2021 model year onward)" and cause: "Motorcycles carry no legislated OBD emissions layer before Euro 5, so on earlier BMWs a generic reader commonly gets no session at all even with a physical adapter fitted" — with "'no communication' there is expected behaviour, not evidence of a network fault."

known_issues_aprilia_mv_electrical.json[3], source regulation, "A Euro 4 Aprilia or MV Agusta is not a locked door — the manufacturer owes you the connector pinout and an adapter, free of charge": "Motorcycles in category L3e became OBD stage I vehicles from 1 January 2016 for new types and 1 January 2017 for all new registrations", quoting Commission Delegated Regulation (EU) No 44/2014 as amended by (EU) 2018/295. Cause: "Euro 4 machines are commonly lumped in with earlier proprietary ones, though the OBD stage I obligation begins at Euro 4 and not at Euro 5".

The same BMW file contradicts itself: known_issues_bmw_electrical.json[2] says BMW "moved to the 16-pin OBD-II socket only around the 2016-2017 model years with the Euro 4 on-board-diagnostics requirement".

**Auditor's recommended fix.**

Correct known_issues_bmw_electrical.json[0] to Euro 4 / 2016-2017 for the OBD stage I layer, and add the cross-reference to the regulation entry. The rest of that entry's argument (proprietary modules outside the emissions layer) survives the correction unchanged.

**Verifier verdict — real=True.**

Independently reproduced, and it is a genuine contradiction rather than a difference of scope.\n\n1. Both quotes are verbatim. known_issues_bmw_electrical.json[0] (source: model-generated) description: "A generic ELM327/OBD-II clone speaks only the legislated emissions diagnostic layer. Motorcycles carry that layer only from Euro 5 (roughly 2021 model year onward), so on a Euro 5 BMW a generic reader returns standard P-codes from the engine ECU and nothing else, while on earlier CAN-era BMWs with the round diagnostic connector it usually will not establish a session at all -- 'no communication' there is expected behaviour, not evidence of a network fault." causes[1]: "Motorcycles carry no legislated OBD emissions layer before Euro 5, so on earlier BMWs a generic reader commonly gets no session at all even with a physical adapter fitted." known_issues_aprilia_mv_electrical.json[3] (source: regulation) reproduces exactly as quoted, including causes[1] "Euro 4 machines are commonly lumped in with earlier proprietary ones, though the OBD stage I obligation begins at Euro 4 and not at Euro 5".\n\n2. Not a scope difference. Both are claims about when the legislated OBD layer exists for L3e motorcycles, and every BMW family named in entry 0 (R1200/R1250, F-series, S1000, K-series) is L3e. OBD stage I is a Euro 4 obligation (new types 1 Jan 2016, all new registrations 1 Jan 2017); OBD stage II arrives with Euro 5. The BMW entry is wrong by one full emissions generation.\n\n3. The corpus sides against the BMW entry everywhere else. Same file, entry 2: BMW "moved to the 16-pin OBD-II socket only around the 2016-2017 model years with the Euro 4 on-board-diagnostics requirement". compat_matrix.json GS-911 rows 110 and 113 (Phase 215's own rows): "2017+ EU4 bikes take the OBD-II connector variant". The Aprilia/MV generic-ELM327 rows are three-tiered incompatible-to-2015 / read-only 2016-2020 / read-only 2021+, verified_by CELEX:32018R0295. ROADMAP row 235 records the correction explicitly: "A refuter overturned a full model generation... found L3e vehicles are OBD stage I from 1 Jan 2016". A grep for "legislated" across all 92 knowledge files returns only known_issues_bmw_electrical.json[0]; it is the sole holdout.\n\n4. The error is real in operational terms for a 2017-2020 window: entry 2 puts those BMWs on the 16-pin socket, and entry 0 tells the shop a failed generic session on them is "expected behaviour" and "means nothing at all". Entry 0's year span (2004-2026) covers them.\n\n5. The auditor understated the blast radius inside entry 0. Beyond description and causes[1], the same claim appears twice in fix_procedure: step 1 ("on earlier CAN-era BMWs, particularly round-connector bikes, it will often not connect at all") and step 7 ("Partial or failed connection with a Tier 1 tool on a pre-Euro 5 bike means nothing at all"). Step 7 is the most damaging line and survives a fix aimed only at the description and the cause.\n\n6. The finding's supporting claim checks out: source=regulation appears exactly once in the whole 917-entry corpus (Counter: model-generated 131, service-manual 108, forum 17, regulation 1, null 660), and test_phase235b_regulation_provenance.py puts regulation in VERIFIED_SOURCES and prints "Authoritative on what is required" rather than a provenance warning.\n\n7. No test pins the wrong wording, so the correction is safe: test_phase215_bmw_electrical.py has no "Euro" assertion, and the staged Gate 12 test only checks the six-value vocabulary and that some entry uses regulation.

**Verifier's corrected_fix.**

The direction of the fix is right but it is incomplete in three ways.\n\nA. Correct four sites in known_issues_bmw_electrical.json[0], not one:\n  - description: replace "Motorcycles carry that layer only from Euro 5 (roughly 2021 model year onward)" with the two-stage fact -- OBD stage I from Euro 4 (L3e: new types 1 Jan 2016, all new registrations 1 Jan 2017), OBD stage II from Euro 5 (roughly 2021).\n  - causes[1]: "no legislated OBD emissions layer before Euro 5" -> "before Euro 4 (roughly 2016-2017)", and re-scope the consequence to genuinely pre-Euro-4 machines, which on BMW are the round-connector bikes per entry 2.\n  - fix_procedure step 1: the Tier 1 description currently has two tiers (Euro 5 vs "earlier"). It needs the same three tiers the compat matrix already uses for Aprilia/MV: pre-2016 no session; 2016-2020 Euro 4, emission-related codes and standard engine data only; 2021+ Euro 5 / OBD stage II.\n  - fix_procedure step 7: "Partial or failed connection with a Tier 1 tool on a pre-Euro 5 bike means nothing at all" must become pre-Euro-4. This is the line that actually costs the shop work -- on a 2016-2020 machine a failed generic session is a finding to chase (adapter, pinout, socket), not expected behaviour. A fix that edits only the description and the cause leaves this standing.\n\nB. Carry over Phase 235's two honest hedges rather than flipping to a promise: the Euro 4 entitlement is a type-approval obligation, not a bench-verified response from any particular BMW, and its scope is narrow -- emission-related DTCs and standard engine data only. That hedge is what keeps entry 0's actual argument (ZFE, ABS, cluster, immobiliser, TPMS, ESA live in proprietary sessions a clone cannot reach) intact and, as the auditor says, unchanged.\n\nC. Do NOT re-source the entry to `regulation`, and do not paste the regulation text into it. tests/test_phase215_bmw_electrical.py:196-197 asserts every BMW entry is source == "model-generated" with "general knowledge" in its description, and tests/test_phase235b_regulation_provenance.py:270 asserts exactly one Phase 235 entry is regulation-sourced ("locked door"). Cross-reference the entitlement entry by title, the way entry 0 already cross-references the CAN-bus and connector entries.\n\nOne correction to my own extension, checked and withdrawn: the BMW generic-ELM327 compat row (compat_matrix.json row 90) is NOT a second instance of this error. Its model_pattern is "S1000RR", not "%", so it is a model-scoped forum-verified claim about one bike's proprietary session layer, not a Euro-generation sweep. BMW simply has no "%" ELM327 rows at all -- a coverage gap next to the three tiers Aprilia and MV received, worth noting separately but not part of this defect and not something to change on this finding's evidence.


### [CONFIRMED] BMW hexhead final drive: Phase 211 blames oil-change intervals on a bearing Phase 237 says the oil never reaches

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_bmw_r_series.json (entry 0) vs /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_differentials.json (entry 11)`

**Evidence.**

known_issues_bmw_r_series.json[0], "Final drive crown-wheel bearing failure — hexhead R1200GS/RT/R", 2005-2011, severity critical. Cause: "Lubricant breakdown from heat and extended change intervals". Fix step 5: "refill with the manual-specified hypoid gear oil and reset the change interval; many owners shorten it from the factory schedule." Fix step 3: "Drain the final drive and inspect the oil for metallic glitter".

known_issues_european_differentials.json[11], "BMW hexhead final drive crown bearing: sealed and greased before 2010, oil-fed and vented after": "On the pre-2010 hexhead final drive the crown-wheel bearing is a sealed, greased bearing that the final-drive oil never reaches; around 2010 BMW moved that bearing into the oil section and added a vent at the top to handle heat expansion. So on a pre-2010 machine a rumble or play at the rear is a bearing that was never oil-fed, and no amount of oil changing addresses it."

**Auditor's recommended fix.**

Phase 237 is right. Strike "Lubricant breakdown from heat and extended change intervals" and the "shorten the interval" advice from known_issues_bmw_r_series.json[0], and split its year range at 2010 or add the pre-2010 sealed-bearing fact to its description.

**Verifier verdict — real=True.**

Reproduced independently; both quotes are verbatim and the contradiction is real, not a scope difference.

known_issues_bmw_r_series.json[0] "Final drive crown-wheel bearing failure — hexhead R1200GS/RT/R", year_start 2005 / year_end 2011, severity "critical", source "model-generated". Its causes list contains exactly "Lubricant breakdown from heat and extended change intervals", and fix step 5 reads "...refill with the manual-specified hypoid gear oil and reset the change interval; many owners shorten it from the factory schedule." Step 3 is "Drain the final drive and inspect the oil for metallic glitter; a magnetic drain plug will show it directly." Its description also self-hedges: "Written from general knowledge of owner reports — confirm against the service manual before quoting."

known_issues_european_differentials.json[11] (source "forum", 2004–2013) says of the same named component on the same machines: "On the pre-2010 hexhead final drive the crown-wheel bearing is a sealed, greased bearing that the final-drive oil never reaches... So on a pre-2010 machine a rumble or play at the rear is a bearing that was never oil-fed, and no amount of oil changing addresses it."

Same make, same generation, same named part, opposite causal claim — a direct contradiction, and 2005–2011 straddles the ~2010 redesign that entry 0 never mentions. Provenance ranks the newer entry higher (forum > model-generated), and entry 0 asks to be confirmed before quoting. ROADMAP row 237 records the crown-bearing entry shipping ("hexhead final drive crown bearing sealed pre-2010, oil-fed and vented after") with no corresponding amendment to Phase 211, and tests/test_phase237_european_differentials.py's ALREADY_IN_CORPUS exclusion list does not cover it — so the overlap was never reconciled. Both tests/test_phase211_bmw_r_series.py and tests/test_phase237_european_differentials.py pass today (52 passed), so nothing in the suite catches this; it is a pure content contradiction that would ship through Gate 12.

**Verifier's corrected_fix.**

The direction is right (strike the interval cause and the shorten-the-interval advice), but the recommended fix as written will break the gate if implemented literally. Constraints an editor must honour:

1. DO NOT split entry 0 into two entries. The R-file entry count is pinned in four places: tests/test_phase211_bmw_r_series.py:52 (`len(rows) == 12`) and :108 (`len(data) == 12`), tests/test_phase212_bmw_gs_adventure.py:184 (BMW total 24), tests/test_phase213_bmw_s1000.py:203 (30), and the corpus total is pinned by the staged Gate 12 test `test_documented_count_matches_the_live_seed` against README.md:44 "917 curated known issues" (live count is exactly 917). Adding an entry fails all of these.

2. Do not simply narrow year_end to 2009 either — entry 0 is the corpus's only make-file entry for the hexhead final drive, and narrowing silently drops 2010–2011 coverage while `test_the_headline_failures_are_present` still needs a "final drive" title and `test_critical_entries_are_the_dangerous_ones` needs a critical entry whose title contains "Final drive". Keep 2005–2011 and make the entry generation-aware in place: state in the description that the pre-2010 crown-wheel bearing is sealed and greased and runs outside the oil section, that BMW moved it into the oil section and added a vent around 2010, and that the two generations therefore fail and are diagnosed differently.

3. Edit the cause, don't just delete blindly: replace "Lubricant breakdown from heat and extended change intervals" with a generation-scoped statement (oil condition is only in play on 2010-on units where the bearing runs in the oil), or drop it outright.

4. In fix step 5, delete only "and reset the change interval; many owners shorten it from the factory schedule" — keep "refill with the manual-specified hypoid gear oil", which is still correct after a rebuild.

5. Qualify step 3 rather than removing it: on pre-2010 units, absence of glitter does not clear the crown-wheel bearing because it sits outside the oil section; the rock-the-wheel play check (step 1) and the seal weep (step 2) carry the diagnosis there.

6. Text-level invariants for this file: the description must still contain "general knowledge" (tests/test_phase211_bmw_r_series.py:116), source must stay "model-generated" (:103, :109), parts_needed and estimated_hours must stay non-empty/positive (:84-92), and the title must stay unique across the BMW files (test_phase213:206) and vs the Ducati file (test_phase216:126). Critically, do NOT copy text across from the differentials entry wholesale: that entry ends with a "Forum tip:" sentence, and pasting it into a model-generated entry violates the six-value provenance rule (forum-only marker) that tests/test_phase237_european_differentials.py:60 enforces file-by-file.

7. One extra item the finding misses, same entry, same cluster: fix step 4 says the drive "must be disassembled... most shops send the unit out or fit an exchange unit", which leans on the framing Phase 239 explicitly refuted — known_issues_european_parts.json[3] ("'BMW supplies the hexhead final drive only as a complete unit' is not established — bearings and seals carry their own numbers") records that the bearing and seal have individual BMW part numbers at two-figure prices. Step 4 should mention quoting the bearing and seal individually before an exchange unit.

8. Note for whoever edits, do not silently merge: known_issues_european_parts.json[3] says "the outer wheel-side ball bearing is the one owners identify" while known_issues_european_differentials.json[11] names the crown-wheel bearing as the sealed/greased one. Entry 0 should keep naming the crown-wheel bearing (its title and two tests depend on it) and attribute the sealed-bearing point to the pre-2010 design as the forum source scopes it, rather than conflating the two bearings.


### [CONFIRMED] KTM valve train: Phase 238 classes the whole make as shim-under-bucket; Phase 237 documents a KTM with rocker arms

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_intervals.json (entry 4) vs /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_differentials.json (entry 7)`

**Evidence.**

known_issues_european_intervals.json[4], "Five valve-train job types across the European makes", model field: "Ducati desmo; MV, Triumph triples, Aprilia, KTM, S1000RR shim-under-bucket; ...". Description: "**Shim-under-bucket, camshafts out**: MV Agusta ..., Triumph triples and air-cooled twins, Aprilia; KTM and the S1000RR by owner report, no manufacturer page opened."

known_issues_european_differentials.json[7], "KTM 690 LC4 valve-train failure is the roller rocker bearing, and a shim-under-bucket model has no place for it": "On the single-cylinder 690 the intake rocker arm runs a needle roller bearing retained by a peened pin, and the documented failure is the pin letting go so the bearing comes apart... a bucket-and-shim engine has no rocker bearing to fail".

**Auditor's recommended fix.**

Phase 237 is right on the 690 LC4. Qualify the KTM entry in known_issues_european_intervals.json[4] by engine family — LC8/LC8c versus LC4 — or drop KTM from the shim-under-bucket list and label it "varies by engine family, see the 690 rocker entry".

**Verifier verdict — real=True.**

Reproduced independently. known_issues_european_intervals.json[4] ("Five valve-train job types across the European makes") puts KTM in the shim-under-bucket column with no engine-family qualifier, in both the description ("**Shim-under-bucket, camshafts out**: MV Agusta ..., Triumph triples and air-cooled twins, Aprilia; KTM and the S1000RR by owner report, no manufacturer page opened.") and the model field ("MV, Triumph triples, Aprilia, KTM, S1000RR shim-under-bucket"). known_issues_european_differentials.json[7] states the opposite for a specific KTM engine: "On the single-cylinder 690 the intake rocker arm runs a needle roller bearing retained by a peened pin ... a bucket-and-shim engine has no rocker bearing to fail". ROADMAP row 237 is the differentials (common failure patterns) file and row 238 the intervals file, so the phase attribution is correct. Two further facts I found that the finding did not cite make the conflict operative rather than theoretical: (a) the intervals file itself covers the 690 — entry 6, "KTM publishes service minutes...", lists "690 Duke" in its model field, so a reader pricing an LC4 valve job from this file is routed straight into entry 4's shim-under-bucket, cams-out column; (b) "rocker" appears in none of the six known_issues_ktm_*.json files, so differentials[7] is the corpus's only statement of KTM valve-train architecture and nothing else corrects entry 4. The entry's sole mitigation is the fix_procedure line "Note which job types here rest on owner reports rather than a manufacturer page — the BMW boxers and KTM — and confirm on the machine", which hedges confidence, not scope, as the finding says. Nothing in the staged Gate 12 test asserts anything about this list, so the entry can be corrected without breaking it.

**Verifier's corrected_fix.**

The recommended fix's first branch is unsafe; take the second branch, expanded. Do NOT "qualify by engine family — LC8/LC8c versus LC4": that would print a new engine-family classification (LC8/LC8c = shim-under-bucket) with more confidence than the entry has any basis for. Entry 4 states in its own text that the KTM classification rests on owner report with "no manufacturer page opened" — the corpus holds no manufacturer source for ANY KTM valve-train type, so a family split would just relocate the unverified claim onto engines nobody opened a page for (and KTM's 790/890 LC8c and 1290 LC8 are commonly described as running finger/rocker followers, so the split may be wrong in the other direction too). Instead, edit known_issues_european_intervals.json[4] as follows, keeping source "model-generated": (1) remove the bare "KTM" from the shim-under-bucket clause in the description and replace it with a scope statement — KTM's valve-train type is not established from any manufacturer page, varies by engine family, and this corpus documents the single-cylinder 690 LC4 as a rocker-arm train (see the KTM 690 rocker-bearing entry in known_issues_european_differentials.json); (2) make the same edit in the model field, which repeats the claim in short form and is what a matcher surfaces — do not leave "KTM ... shim-under-bucket" standing there; (3) update the fix_procedure's closing line so it names the LC4 as the known counter-example rather than only flagging KTM as owner-report-grade — "confirm on the machine" is not enough when the corpus already contains the contradicting engine; (4) since intervals[6] prices a "690 Duke" valve service, add the same one-line pointer there so the priced job and the job-type entry agree. Two constraints on whoever applies this: do not add a "Forum tip:" to entry 4 — its source is model-generated and rule 3 forbids one (the cross-referenced 690 entry is the forum-sourced one); and note the S1000RR sits in the same "by owner report, no manufacturer page opened" clause as KTM, so it carries the identical unverified-classification defect and should be reviewed in the same edit rather than left as the lone survivor of that clause.


### [REJECTED] Triumph connector transition: Phase 230 prints ~2023 and Euro 5+; Phase 236 says the year cannot be established and dates it to Euro 5

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_triumph_electrical.json (entry 1) vs /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_tooling.json (entry 11)`

**Evidence.**

known_issues_triumph_electrical.json[1], model field: "Triumph fuel-injected models — 16-pin socket to approximately 2023, red 6-pin on Euro 5+". Description: "From the late 1990s until around 2023 Triumph fitted a sixteen-pin socket... the changeover is model-dependent across roughly 2023 to 2025".

known_issues_european_tooling.json[11], "Triumph is the European connector outlier — it had the 16-pin socket before Euro 5, then moved to the red 6-pin": "Specific transition years are deliberately not printed here: the sources consulted disagreed by several model years, and a wrong year is worse than none when it decides which lead a shop orders."

**Auditor's recommended fix.**

Phase 236's discipline should win, since the whole point is that ordering a lead by year is the failure mode. Strip "approximately 2023" and "roughly 2023 to 2025" from known_issues_triumph_electrical.json[1] and from the dealertool-triumph adapter row, replacing them with the identify-the-socket-physically instruction Phase 236 gives. Alternatively, if the 2023 date is genuinely sourced, Phase 236's refusal to print it must be withdrawn — but the two cannot both ship.

**Verifier verdict — real=False.**

The claimed contradiction does not exist: the auditor quoted text that is not in the corpus. Three of its four quoted strings appear nowhere in the repo (`grep -rn` over the whole tree for "roughly 2023 to 2025", "socket to approximately 2023", and "until around 2023" all return zero hits).

What known_issues_triumph_electrical.json[1] actually says:
- model: "Triumph fuel-injected models — 16-pin socket era, red 6-pin on Euro 5+" (NOT "16-pin socket to approximately 2023, red 6-pin on Euro 5+" as quoted).
- description: "From the late 1990s until the Euro 5 transition Triumph fitted a sixteen-pin socket... the changeover is model-dependent, so check the actual machine rather than the year. Specific transition years are deliberately not printed: Phase 236 found the timelines in circulation disagree by several model years, and a wrong year is worse than none when it decides which lead a shop orders. Identify the socket on the machine."
- causes[3]: "...over a model-dependent transition". fix_procedure step 4: "the changeover varies by model across a transition period rather than falling on one year."

So the Phase 230 entry prints NO transition year, cites Phase 236 by name, and reaches the same conclusion in the same words as known_issues_european_tooling.json[11] ("Specific transition years are deliberately not printed here: the sources consulted disagreed by several model years, and a wrong year is worse than none when it decides which lead a shop orders"). Phase 236 evidently retro-fixed the Phase 230 entry; the auditor appears to have read a pre-236 version. There is no substance disagreement either — both say 16-pin before Euro 5, red 6-pin on Euro 5+ — and no leak of the "Triumph pre-Euro-5 connector TRANSITION YEAR" absence in either knowledge file. ROADMAP row 236 corroborates: "transition year deliberately not printed — a refuter found it off by three."

The recommended fix is therefore mostly a no-op (there is nothing to strip from the knowledge entry), and its "alternatively, withdraw Phase 236's refusal" branch is wrong outright — the year was refuted, not merely unsourced.

ONE sub-claim does survive, but it is a different and much smaller finding than the one titled: adapters.json slug `dealertool-triumph` still carries "Bikes from approximately 2023 need a 6-pin-to-16-pin adapter." That is a real residual leak of the deliberate absence and, per row 236's "off by three", a wrong number. Its sibling row `tuneecu-triumph-android` already states the same fact correctly with no year ("Euro 5 machines with the red 6-pin connector need a 6-pin-to-16-pin adapter"), which shows Phase 236's sweep hit the knowledge files and one adapter row but missed this one. Severity is low/medium (a single vendor-note sentence, contradicted by its own sibling row and by both knowledge entries), not the high-severity two-entry contradiction claimed.

**Verifier's corrected_fix.**

Discard the knowledge-file half of this finding entirely — known_issues_triumph_electrical.json needs no change; it already implements Phase 236's discipline verbatim and cites it.

File a separate, narrower finding for the only real residue, in /Users/lilquant/Projects/moto-diag/src/motodiag/hardware/compat_data/adapters.json, slug `dealertool-triumph`, `known_issues` field: replace the sentence "Bikes from approximately 2023 need a 6-pin-to-16-pin adapter." with the year-free wording its sibling row already uses, e.g. "Euro 5 machines with the red 6-pin connector need a 6-pin-to-16-pin adapter; the changeover is model-dependent, so identify the socket on the machine rather than ordering the lead by year." Nothing else in that row changes, and no knowledge entry, DTC file or compat_matrix row is affected (a repo-wide grep for "approximately 2023" returns this one line only).

Optionally, since Phase 236's sweep demonstrably missed a non-knowledge file, the Gate 12 test's deliberate-absence assertions should be checked to see whether they scan hardware/compat_data and advanced/data at all, not just seed/knowledge — the staged test at /private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py has no assertion matching on "absence", "shim", "7.48", "rotation" or similar, so this class of leak is currently ungated.


### [CONFIRMED] Ducati desmo intervals: Phase 219 says the valve schedule has a time element; Phase 238 says no European valve row does

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_ducati_desmo.json (entry 4) vs /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_intervals.json (entry 3)`

**Evidence.**

known_issues_ducati_desmo.json[4], "Desmo service intervals vary by generation", source model-generated. Fix step 3: "Check both elements of the schedule — mileage and elapsed time — because a stored or low-mileage bike can be overdue on time while the odometer suggests otherwise." Cause: "Low-mileage bike where a time-based element of the schedule has passed unnoticed".

known_issues_european_intervals.json[3], "No European valve row opened carries a time trigger", source service-manual, drawn from five BMW, eleven KTM, seven Triumph manuals and Ducati's maintenance sheets: "Ducati's Desmo service is by kilometres, its annual service is a separate row, and only the timing belts carry a months figure... A low-mileage machine coming in for its yearly service is therefore not due a valve check on the manufacturer's schedule, however old it is", and "that rule belongs to the belts and does not transfer to the clearances."

**Auditor's recommended fix.**

Phase 238 is right; it read the tables. Rewrite fix step 3 and the matching cause in known_issues_ducati_desmo.json[4] to say the desmo valve row is distance-only and that the time element belongs to the cam belts (which the Monster and Multistrada entries already handle correctly).

**Verifier verdict — real=True.**

Reproduced independently, and it is a genuine contradiction rather than a scope difference.

1. The evidence is verbatim. /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_ducati_desmo.json index 4 ("Desmo service intervals vary by generation — a remembered figure produces a wrong quote", source "model-generated") contains fix step 3: "Check both elements of the schedule — mileage and elapsed time — because a stored or low-mileage bike can be overdue on time while the odometer suggests otherwise." and cause 4: "Low-mileage bike where a time-based element of the schedule has passed unnoticed". /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_intervals.json index 3 (source "service-manual") contains "Ducati's Desmo service is by kilometres, its annual service is a separate row, and only the timing belts carry a months figure", "A low-mileage machine coming in for its yearly service is therefore not due a valve check on the manufacturer's schedule, however old it is", and the carve-out "that rule belongs to the belts and does not transfer to the clearances." Its cause 3 names the exact failure mode: "Timing belts on Ducati do carry a months figure, and the belt rule is carried over to the valves by analogy".

2. It is not a scope difference. "The schedule" in desmo[4] step 3 can only be the desmo valve schedule: the entry's title, symptoms ("unsure when desmo service is due") and step 2 ("Read the interval from the manual or Ducati's published schedule") are all the desmo service, and belts are handled separately in step 6 ("Where a belt-driven engine is also due for belts, say so up front"). So step 3 is not smuggling in the belt or annual row — it asserts a time element for the clearances.

3. The precedence claim checks out. docs/ROADMAP.md row 219 says "Intervals deferred by test — a regex fails any entry stating a mileage figure as fact"; row 238 says "no European valve row opened carries a time trigger — 'due every two years' is a shop convention, not a manufacturer instruction, on these makes", from MD5-matched re-downloaded manufacturer PDFs. 219 is model-generated and self-labels "Written from general knowledge"; 238 read the tables.

4. desmo[4] is the only leak of its kind. I swept every bmw/ktm/triumph/aprilia/mv_agusta/ducati/european file for time-language co-occurring with valve/clearance/shim/desmo/tappet: every other Ducati time reference (monster 0/1/5/6, multistrada 1, panigale 0) attaches calendar life to the cam BELTS, exactly as 238 permits, so the finding's claim that Monster and Multistrada handle it correctly is also true.

5. Nothing catches it. The staged Gate 12 test has no time-trigger check (its only intervals test is test_aprilia_660_valve_interval_is_recorded_as_unverified). tests/test_phase219_ducati_desmo.py bars only mileage FIGURES (regex \b\d{1,3},?\d{3}\s*(?:mi|mile|miles|km)\b), which is precisely why a figureless time assertion survived. tests/test_phase238_european_intervals.py checks only its own file. So this ships through the gate.

**Verifier's corrected_fix.**

The direction is right (238 wins, 219's step 3 must go), but the proposed replacement wording is wrong in two ways and misses a third site.

(a) Do NOT write "the time element belongs to the cam belts" as a blanket statement in this entry. Its own model field is "Desmodue, Desmoquattro, Testastretta, Superquadro and Desmosedici Stradale engines", and known_issues_ducati_panigale.json[0] establishes that the Superquadro "does not: a chain runs from the crank to a gear train... so there is no belt, no belt tensioner and no belt interval" — the Desmosedici Stradale likewise. The belt carve-out must be conditioned on belt-driven engines, the way existing step 6 already conditions it.

(b) Do NOT replace it with a flat positive assertion that the desmo valve row "is distance-only". european_intervals[3] is scoped to year_start 2004 and "All models whose schedule tables were opened"; desmo[4] spans 1993–2026 and covers Desmodue/Desmoquattro sheets 238 did not claim to have read. A model-generated entry asserting a schedule fact across 1993+ re-commits what Phase 219's deferral exists to prevent. Phrase it as the negative instruction plus routing, e.g. step 3: "Do not schedule the desmo service by age. On the manufacturer schedules read for this project the valve row is marked under distance columns only — the annual service is a separate row, and on the belt-driven engines it is the cam belts, not the clearances, that carry a months figure. Read the sheet for the model year in hand from the manual rather than assuming either rule." Cause 4 becomes something like "Ducati's belt and annual-service time limits being carried across to the valve clearances by analogy", mirroring european_intervals[3] cause 3.

(c) The fix as written misses the symptom string. desmo[4] symptoms include "older ducati overdue by years", which encodes the same time trigger and is indexed — find_issues_by_symptom / search_known_issues match on the symptoms column, so leaving it makes an age-based desmo query still land on this row. Replace it (e.g. "desmo service history unknown"), keeping the Phase 219 constraint of <=55 chars and no trailing period.

Constraints any edit must respect, from tests/test_phase219_ducati_desmo.py: no mileage figure may appear (test_no_entry_states_a_mileage_interval_as_fact); the word "manual" must remain in the interval entry (test_the_interval_entry_defers_to_the_manual); the description must keep "general knowledge" (test_every_description_admits_its_origin); every entry must still name desmodromic hardware; "belt" must not enter the title (test_no_cam_belt_procedure_is_rewritten checks titles only, so belts in the body are fine); and source must stay "model-generated" (test_every_entry_is_tagged asserts the whole file is model-generated) — so cite Phase 238's table reading in prose rather than re-sourcing the entry, the way known_issues_ktm_adventure.json[7] does ("read the figure from the manual or from this project's Phase 238 comparison, and do not schedule it by age").

Adjacent, lower confidence, not part of this fix: known_issues_mv_agusta_four.json[3] description says a low-mileage machine "may still be due or overdue on time". MV is outside european_intervals[3]'s make list (BMW, KTM, Triumph, Ducati) and that entry's own fix step 4 says "the manufacturer's table governs", so it is loose wording rather than the same contradiction — worth tightening only if the team wants one voice.


### [REJECTED] MV F3 675 valve interval: Phase 233 says it is unconfirmed and must not be quoted; Phase 238 prints 30,000 km

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json (entry 4) vs /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_intervals.json (entries 0 and 9)`

**Evidence.**

known_issues_mv_agusta_triple.json[4]: "For the **F3 675 the commonly quoted valve interval could not be confirmed against MV's own table** — the figure circulates widely and traces to sources that could not be opened, so it is not repeated here." Fix step 2: "Do not quote the widely circulated F3 valve interval as established". Its symptom list includes "valve interval on an f3 675".

known_issues_european_intervals.json[9]: "The F3 675/800 MY2020 maintenance manual carries the same 30,000 km valve figure, which resolves the interval Phase 234 could not confirm." known_issues_european_intervals.json[0] states it flatly: "at **30,000 km** on the Turismo Veloce MY2015–16 and the F3 MY2020".

**Auditor's recommended fix.**

Update known_issues_mv_agusta_triple.json[4] the way ktm_adventure[7] was updated: record that Phase 238 opened the F3 675/800 MY2020 manual and resolved the figure, and defer the number to Phase 238. Fix the Phase 234/233 attribution in european_intervals[9].

**Verifier verdict — real=False.**

The finding's central evidence is not in the file. It quotes known_issues_mv_agusta_triple.json[4] as saying "For the **F3 675 the commonly quoted valve interval could not be confirmed against MV's own table** — the figure circulates widely and traces to sources that could not be opened, so it is not repeated here," with fix step 2 reading "Do not quote the widely circulated F3 valve interval as established." Neither string exists anywhere in the corpus (grep for "not repeated here", "as established" and "could not be confirmed" across known_issues_mv*.json returns only the single line quoted below). The auditor appears to have quoted a pre-Phase-238 version of the entry.

What the file actually says (/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json, entry 4, line 125): "For the F3 675 the commonly quoted valve interval could not be confirmed when this file was written. **Phase 238 later opened MV's own maintenance manuals and resolved it**, and found that the 798cc triple sits on two different ladders in overlapping model years — so the instruction here is now documented rather than suspected: read the interval from the specific model's own manual, never from a sibling's. The figures are in the European intervals file."

And its fix step 2 (line 145) says the opposite of what the finding claims: "2. Take the F3 valve interval from the European intervals file or from the model's own maintenance manual — Phase 238 resolved it from MV's own documents — and never from a sibling model, which may sit on a different coupon ladder."

So there is no contradiction: the make file does not tell a mechanic the figure is unestablished, it explicitly records that Phase 238 established it and routes the reader to known_issues_european_intervals.json for the number. The entry's residual refusals are narrower and are not the 30,000 km interval — it still withholds the valve *clearance specification* values ("the sources consulted disagreed and none was authoritative"), which is a different quantity that Phase 238 did not resolve, and its symptom "quoted 12000 km for the valves" is consistent with intervals[0], which assigns 12,000 km to the Brutale/Dragster/Rivale ladder and 30,000 km to the Turismo Veloce/F3 ladder.

The finding's supporting contrast is also wrong on its own terms. It claims "the same phase did the right thing on KTM and not on MV." known_issues_ktm_adventure.json[7] reads "Drawn from KTM's own owner's manuals... and corrected at Phase 238... An earlier version of this entry read a 373cc-versus-399cc difference as a Duke-versus-Adventure one; Phase 238 corrected it against eleven KTM manuals, and the figures themselves live there." That is structurally identical to what mv_agusta_triple[4] does — name the correcting phase, state what it resolved, and defer the figures to Phase 238's file. Both entries were back-propagated in the same way, and both withhold the numbers per the Phase 238 interval-ownership decision (decision 2, which requires known_issues_ktm_adventure.json to carry no interval figures — the KTM entry complies, and the MV entry likewise prints none).

The only surviving grain is the sub-point buried in "why_it_matters": known_issues_european_intervals.json[9] ends "...which resolves the interval Phase 234 could not confirm," while the F3 675 is a triple and docs/ROADMAP.md row 233 is the phase that deferred it ("intervals deferred with the widely quoted F3 figure **not repeated** because it could not be confirmed"); row 234 is the F4/4-cylinder phase, whose deferral was the shim diameter. But this is a cosmetic phase-number citation in prose, not a content contradiction, it is consistent with how ROADMAP row 238 itself words it ("the **F3 MY2020 figure is now confirmed** (234's deferral closed)"), 233 and 234 were run as a single paired research run, and no decision in the track's list turns on it. It does not support a "high" severity finding, and it is not the finding as filed — the filed finding is that the make file and the intervals file contradict each other, which they do not.


### [CONFIRMED] Aprilia V4 charging: Phase 237's flywheel-first rule is asserted for 2009-2020; Phase 239 says the flywheel exists for the later family only

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_differentials.json (entry 5) vs /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json (entry 2)`

**Evidence.**

known_issues_european_differentials.json[5], model "RSV4 2009–2020, Tuono V4 1000 2011–2015, Tuono 1100 2016–2020": "the fix offered is a lower-magnet-strength flywheel fitted together with the stator", and fix: "Where the original flywheel is fitted and the stator has failed, quote the flywheel with the stator rather than the stator alone". parts_needed leads with "Replacement flywheel of reduced magnet strength".

known_issues_european_parts.json[2]: "the reduced-magnet flywheel that Phase 237 names as the first suspect on a burnt stator exists for the Kokusan family only" and "On the early Mitsubishi family, the aftermarket kit that replaces the original number exists but the reduced-magnet flywheel does not, so the Phase 237 flywheel-first differential applies to the later family only." The fiche assigns the Mitsubishi type to the first RSV4 years and the Tuono V4 R of the first year.

**Auditor's recommended fix.**

Phase 239 is right — it read the fiche. Add the family split to known_issues_european_differentials.json[5]: name the Kokusan family in the model field or state in the description that the reduced-magnet flywheel exists for the later family only. Reconcile the rsv4[7] / parts[2] wording on whether year-and-variant identifies the family.

**Verifier verdict — real=True.**

Reproduced verbatim from the files, and the parts catalogue corroborates it independently.

known_issues_european_differentials.json[5] (title "Aprilia V4 charging failure: the flywheel is the first suspect…", make Aprilia, model "RSV4 2009–2020, Tuono V4 1000 2011–2015, Tuono 1100 2016–2020", year_start 2009, year_end 2020, source forum). Description: "the fix offered is a lower-magnet-strength flywheel fitted together with the stator". fix_procedure: "Where the original flywheel is fitted and the stator has failed, quote the flywheel with the stator rather than the stator alone". parts_needed[0]: "Replacement flywheel of reduced magnet strength". The entry names no generator family anywhere — grep confirms the strings "Kokusan" and "Mitsubishi" appear nowhere in known_issues_european_differentials.json (only in known_issues_european_parts.json, parts.json and parts_xref.json).

known_issues_european_parts.json[2], description: "The fiche assigns the early type to the first RSV4 years and the Tuono V4 R of the first year, and the Kokusan type from the APRC generation onward… the reduced-magnet flywheel that Phase 237 names as the first suspect on a burnt stator exists for the Kokusan family only." fix_procedure: "On the early Mitsubishi family, the aftermarket kit that replaces the original number exists but the reduced-magnet flywheel does not, so the Phase 237 flywheel-first differential applies to the later family only."

This is a genuine contradiction, not a scope difference: the 237 entry is not merely diagnostic, it issues a parts-ordering instruction ("quote the flywheel with the stator") and leads parts_needed with the exact part 239 says does not exist for the early family, over a year range that includes it, with no pointer to the 239 entry.

Third-source corroboration in /Users/lilquant/Projects/moto-diag/src/motodiag/advanced/data/parts.json: the only reduced-magnet flywheel row is "rmstator-rms120-103587-flywheel" — "Kokusan Improved reduced-magnet flywheel — replaces 1A010574 / 2D000049", year_min 2011, year_max 2020, notes "Maker fitment: RSV4 1000 Factory/R/RF/RR 2011-20, Tuono V4 1000/1100 2011-20… A UK reseller's… 2009-2017 title is not the maker's fitment." The early family's rows are "aprilia-857201-stator" (Mitsubishi type, 2009-2012) and "rmstator-rms900-104929-stator" ("Stator + Mitsubishi-type flywheel kit", 2009-2012) — a flywheel kit, but not a reduced-magnet one. So no reduced-magnet flywheel exists below 2011 in the corpus's own catalogue.

Two corrections to the finding, both widening rather than weakening it: (a) the exposed population is larger than the finding's "2009-2010" — the fiche row assigns Mitsubishi to RSV4 2009-2012 and Tuono V4 R 2011, and the two families' year ranges overlap (857201 RSV4 2009-2012 vs 897479 RSV4 APRC 2011-15), so 2011-2012 RSV4s and the 2011 Tuono V4 R named in differentials[5]'s own model field are also affected; (b) the finding's secondary tension is weaker than it presents. known_issues_aprilia_rsv4.json[7] ("cannot be told apart without removing the generator cover", "The model and year will not tell you") and european_parts[2] ("the fiche assigns by model year and variant instead") are reconcilable, not contradictory: parts[2]'s "instead" is contrasting the fiche's axis with the aftermarket engine-number threshold it has just refuted, and its own fix_procedure agrees with rsv4[7] — "Identify the charging family from the machine before ordering — open the generator cover if necessary — rather than from the model year alone". The overlapping catalogue year ranges are exactly why year alone is insufficient. Both entries land on the same action; this is a wording tension, not a defect of the same severity.

The staged Gate 12 test does not test this cluster (no assertion referencing the flywheel, the family split, or european_differentials entry content).

**Verifier's corrected_fix.**

The finding is right that differentials[5] must be narrowed, but its recommended fix is wrong on one half and incomplete on the other.

Wrong: "name the Kokusan family in the model field". The model/year_start/year_end fields are the retrieval keys and are year-shaped; the family is not a year-keyed attribute — that is the whole point of rsv4[7] and of the overlapping 2011-2012 catalogue rows. Encoding "Kokusan" in the model field would either be undecidable at lookup time or, if it were done by dropping 2009-2012 from the range, would delete the early family from the entry entirely. That over-corrects: the entry's primary instruction — "remove the generator cover and inspect the flywheel before ordering anything… look for debonded or shifted magnets and for heat damage" — is correct for both families (the epoxy-debonding mechanism is not family-specific, and RMS900-104929 shows a Mitsubishi-type flywheel replacement does exist). Only the reduced-magnet remedy is Kokusan-only.

Incomplete: the fix names only the model field or the description, but the field that will actually be read off and quoted is parts_needed, whose first element is the unconditioned "Replacement flywheel of reduced magnet strength".

Correct fix — keep the entry's population at 2009-2020 and split the remedy inside it, touching three fields:
1. parts_needed[0]: condition the part rather than leading with it, e.g. "Replacement flywheel of reduced magnet strength — later (Kokusan) family only; no reduced-magnet flywheel exists for the early family".
2. fix_procedure: after "quote the flywheel with the stator rather than the stator alone", add that the reduced-magnet flywheel exists for the later family only, and that on the early family the remedy is the stator-and-flywheel kit that replaces the original number, so the cover-off inspection decides which remedy is quotable. This preserves the entry's actual differential (inspect before ordering) while removing the un-orderable quote.
3. description: state that the V4 carries two generator families and that the lower-magnet-strength flywheel is offered for the later one only, so the sentence "the fix offered is a lower-magnet-strength flywheel fitted together with the stator" stops being unconditional.

Keep the entry's source as "forum" and its existing "Forum tip:" sentence — the added material is a narrowing of the same supplier/owner claim, and switching the source would break the rule-3 forum-tip pairing.

Do not, as the finding suggests, "reconcile the rsv4[7] / parts[2] wording" as though it were a contradiction. If anything is done there it should be a one-clause softening of parts[2]'s "the fiche assigns by model year and variant instead" to note that the fiche's own year ranges for the two families overlap (2011-2012 on the RSV4), which is why parts[2]'s own procedure still sends the reader to the cover. Editing rsv4[7]'s "the model and year will not tell you" would be the wrong direction — the catalogue rows show it is the accurate statement.

One caution for whoever applies this: five to six copies of the designation-bar guard and the Phase 233 MV-ownership guard match on the known_issues_european_* prefix (per ROADMAP rows 236-238), so re-run the phase 227/228/231/232/226 tests plus the staged Gate 12 file after editing this entry's prose, not just the 237 tests.


---

## Dimension: absences

**Auditor summary.** Audited all seven deliberate absences across the 96 known_issues files (917 entries, 30 European / 257 entries), the 8 DTC files, adapters.json + compat_matrix.json, parts.json + parts_xref.json, ROADMAP.md rows 211-240 and implementation.md, plus the staged Gate 12 test. Four of the seven absences hold cleanly and are claimed where a reader would find them. Three leaked outside the file that made the decision, in every case because the guarding test was scoped to one entry in one file: the Triumph connector transition year is printed as a structured field value in known_issues_triumph_electrical.json; the Moto Guzzi 8V conversion cost ships as "USD 1,226" in parts.json (the exact NZD-rendered-as-USD failure Phase 237 removed); and the 2025 KTM 390 build location is asserted as Bajaj/India in known_issues_ktm_duke.json and compat_matrix.json. One further inverse finding: known_issues_mv_agusta_triple.json still claims an omission Phase 238 has since resolved. The staged Gate 12 campaign-number test would pass over all of these — it scans four fields of the European known_issues files only, with a regex covering two of the six formats the Phase 231 decision names. All 241 tests for phases 225b/230/233/234/236/237/238/239 pass against the current tree, confirming the leaks are unguarded rather than merely unnoticed.


### [REJECTED] Triumph connector transition year is printed in known_issues_triumph_electrical.json, contradicting european_tooling.json's explicit "deliberately not printed"

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_triumph_electrical.json`

**Evidence.**

Entry index 1 ("The Triumph diagnostic socket looks like OBD-II but does not speak it"), line 36, prints the year in the structured `model` field: "Triumph fuel-injected models — 16-pin socket to approximately 2023, red 6-pin on Euro 5+". Line 34 description: "From the late 1990s until around 2023 Triumph fitted a sixteen-pin socket... the changeover is model-dependent across roughly 2023 to 2025". causes repeats "over a model-dependent transition"; fix_procedure step 4 repeats it. Meanwhile known_issues_european_tooling.json entry 11 ("Triumph is the European connector outlier") states: "Specific transition years are deliberately not printed here: the sources consulted disagreed by several model years, and a wrong year is worse than none when it decides which lead a shop orders." ROADMAP.md row 236 records the reason: "transition year deliberately not printed, a refuter found it off by three". The Phase 236 guard tests/test_phase236_european_tooling.py:117 `test_triumph_transition_year_is_deliberately_absent` does `e = next(x for x in raw if "connector outlier" in x["title"])` — one entry, one file. No Phase 230 test asserts or forbids the year. Both files pass today (241 tests green).

**Auditor's recommended fix.**

Strip the years from entry 1 of known_issues_triumph_electrical.json — description, causes, fix_procedure and especially the `model` field (e.g. "Triumph fuel-injected models — 16-pin socket era and red 6-pin Euro 5 era") — and point the reader at the physical socket, as european_tooling.json already does. Then widen test_phase236's guard from one entry in one file to every Track K file, matching Phase 233's rotation-word guard shape.

**Verifier verdict — real=False.**

The finding fabricates its quotations — entry index 1 of /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_triumph_electrical.json contains no year at all in any text field, and already does exactly what the "recommended fix" asks for.\n\n1. The `model` field (line 36) actually reads: "Triumph fuel-injected models — 16-pin socket era, red 6-pin on Euro 5+". The finding quotes it as "...16-pin socket to approximately 2023, red 6-pin on Euro 5+". The words "to approximately 2023" are not in the file. Note the file's phrasing is essentially the exact replacement the fix proposes ("16-pin socket era and red 6-pin Euro 5 era").\n\n2. The description (line 34) actually reads: "From the late 1990s until the Euro 5 transition Triumph fitted a sixteen-pin socket..." and closes with "...the changeover is model-dependent, so check the actual machine rather than the year. Specific transition years are deliberately not printed: Phase 236 found the timelines in circulation disagree by several model years, and a wrong year is worse than none when it decides which lead a shop orders. Identify the socket on the machine." The finding's "From the late 1990s until around 2023" and "roughly 2023 to 2025" are inventions; the entry not only omits the year, it names Phase 236 and states the same rationale as european_tooling.json, so the two entries agree rather than contradict.\n\n3. causes[3] reads "Euro 5 machines moving to a red six-pin connector needing an adapter, over a model-dependent transition" — no year. fix_procedure step 4 reads "...check for the red six-pin connector and obtain the adapter before booking the work; the changeover varies by model across a transition period rather than falling on one year" — no year.\n\nProgrammatic confirmation: `re.findall(r'\\b(?:19|20)\\d{2}\\b', ...)` over every field of entry 1 except year_start/year_end returns `[]`. `grep -n "202[0-9]"` on the whole file matches only four `"year_end": 2026` applicability bounds (lines 8, 38, 98, 128) — entry-scope metadata, not a connector transition year, and year_start 1997 / year_end 2026 are deliberately wide precisely because the boundary is unstated. The only text years in the file are in entry 0 ("A 2017 model-year workshop manual") and entry 2 (the carburetted-to-injected Bonneville changeover, "approximately 2001–2007" / "2008 onward"), which is a different transition and not one of the deliberate absences.\n\nA corpus-wide scan (all known_issues_*.json, dtc_codes/*.json, compat_data/*.json, advanced/data/*.json) for any window containing "Triumph" plus a connector/Euro-5 token plus a four-digit year returned 0 hits. adapters.json line 405 mentions "Euro 5 machines with the red 6-pin connector need a 6-pin adapter" with no year. So the Phase 236 deliberate absence is intact everywhere, not just in the guarded entry.\n\nThe finding's secondary claim — that Phase 236's guard is narrow (tests/test_phase236_european_tooling.py:117 pins one entry in one file, and its year regex only scans `e["description"]`) — is factually true, but a narrow guard is not a contradiction in the content, and there is nothing for a widened guard to catch today. There is no defect to fix, so the recommended fix would be a no-op edit to a field that is already correct.

**Verifier's corrected_fix.**

No content change is warranted; entry 1 already omits the year and states the Phase 236 rationale. The only defensible residual is hardening, not a fix: if the maintainers want the absence enforced rather than merely honoured, widen test_phase236's `test_triumph_transition_year_is_deliberately_absent` from `next(x for x in raw if "connector outlier" in x["title"])` on one file to a scan over every Track K file (`known_issues_{bmw,ducati,ktm,triumph,aprilia,mv,european}*.json` plus adapters.json), asserting that no entry whose text mentions Triumph together with a connector token ("6-pin", "six-pin", "16-pin", "sixteen-pin", "Euro 5") carries a `\b20(1\d|2[0-6])\b` in any scanned field — importantly including `model`, which the current guard's description-only regex does not cover — while exempting `year_start`/`year_end` and the carburetted-Bonneville FI changeover years in known_issues_triumph_electrical.json entry 2, which are a different transition and legitimately printed. That is the same shape as Phase 233's rotation-word guard. It should be filed as a guard-coverage item, not as a high-severity content contradiction, and it must not be used to justify editing the `model` field, which is already the intended wording.


### [REJECTED] Moto Guzzi 8V roller-tappet conversion cost ships as "USD 1,226" in parts.json, the exact figure Phase 237 removed for currency mangling

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/advanced/data/parts.json`

**Evidence.**

Line 1254, slug `moto-1a002060-tappet`, notes field: "...Availability unresolved: fiche 'contact', one US retailer USD 1,226 sold out. Cost 0 is the catalogue's unpriced sentinel (no USD-priced source; excluded from cost ranking)." Against this, known_issues_european_differentials.json entry 8 states "Conversion cost figures in circulation are in more than one currency and are deliberately not printed here", and docs/phases/completed/237_implementation.md:82 records why: "The Moto Guzzi 8V conversion cost in circulation is a New Zealand dollar figure the research rendered as US dollars. No figure ships." The Phase 239 guards both miss it: tests/test_phase239_european_parts.py:163 `test_no_converted_currencies` only inspects rows where `typical_cost_cents > 0`, and this row uses the 0 sentinel, so it is skipped; :252 `test_no_campaign_numbers_and_no_currency_figures` runs on `raw` (the knowledge file) not on `parts`. docs/phases/completed/239_implementation.md discusses these tappet rows at length and never mentions the price, so it went in unnoticed.

**Auditor's recommended fix.**

Remove "one US retailer USD 1,226" from the notes of slug `moto-1a002060-tappet`, leaving "Availability unresolved: fiche 'contact', one US retailer listing sold out". Then fix test_no_converted_currencies to scan every row's `notes` for a currency token regardless of typical_cost_cents, rather than gating on cost > 0.

**Verifier verdict — real=False.**

The evidence does not reproduce. The `notes` field of slug `moto-1a002060-tappet` in /Users/lilquant/Projects/moto-diag/src/motodiag/advanced/data/parts.json (line 1254) does NOT contain "one US retailer USD 1,226 sold out". It actually reads: "...'no preventive operations' — released only against a documented wear claim. Availability unresolved: fiche 'contact', one US retailer listing sold out. Cost 0 is the catalogue's unpriced sentinel (no USD-priced source; excluded from cost ranking)." That is already, verbatim, the text the finding proposes as its own fix.

A repo-wide `grep -rn "1,226"` returns exactly ONE hit in the whole tree, and it is not in any data file: tests/test_phase239_european_parts.py:171, inside the docstring of `test_no_converted_currencies`, narrating the defect in the past tense — "Widened at Phase 240: the first version gated on `typical_cost_cents > 0`, so an UNPRICED row's notes were never scanned — and that is exactly where the withheld Moto Guzzi conversion cost survived, as \"USD 1,226\" on a cost-0 row. The Track K closure audit found it." The auditor appears to have grepped for the figure, hit the test docstring describing the already-remediated bug, and reported it as live catalogue data without opening the JSON.

The guard the finding says is absent also already exists and passes. tests/test_phase239_european_parts.py defines `test_no_withheld_cost_figure_survives_in_notes`, which scans every row whose category contains "tappet" for `(USD|EUR|GBP|NZD|\$)\s?[\d,]{3,}` in notes, ungated by cost. Running `.venv/bin/pytest tests/test_phase239_european_parts.py -q` gives 27 passed. An independent programmatic sweep of all 125 rows in parts.json for currency-amount tokens finds no tappet row carrying any figure; the remaining hits are sanctioned GBP/EUR fiche prices and USD costs on priced rows.

Corroborating content is intact: known_issues_european_differentials.json:229 still states "Conversion cost figures in circulation are in more than one currency and are deliberately not printed here", consistent with docs/phases/completed/237_implementation.md, which records that no figure ships.

**Verifier's corrected_fix.**

No fix is needed for the reported defect — the text is not present and the tappet-scoped guard already exists and passes.

The only residual item worth noting (a documentation defect, not a data defect, and far below the claimed "high" severity) is a docstring/body mismatch in tests/test_phase239_european_parts.py: the docstring of `test_no_converted_currencies` claims "Both halves are checked now: a priced row must say where its figure came from, and no row may carry a bare foreign-currency amount in its notes", but the body still only asserts on rows with `typical_cost_cents > 0`. The second half actually lives in the separate `test_no_withheld_cost_figure_survives_in_notes`, which is scoped to `"tappet" in r["category"]`. Either correct the docstring to point at the sibling test, or widen the bare-figure scan beyond tappet rows — noting that a naive widening would fail legitimately on the sanctioned GBP/EUR fiche prices carried by cost-0 rows such as `aprilia-1a010574-stator` (GBP 576.23) and `mv-8000b5425-oil-filter` (EUR 19.04), which the corpus explicitly permits, so any widened check must exempt GBP/EUR fiche prices rather than ban all currency tokens.


### [REJECTED] The 2025 KTM 390 build location, recorded as "could not be established" in known_issues_ktm_adventure.json, is asserted as Bajaj/India in two other Track K files

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_ktm_duke.json`

**Evidence.**

known_issues_ktm_duke.json line 34, entry title: "The 125 and 390 Duke are built in India by Bajaj — what that changes is parts sourcing, not quality", with year_start 2011, year_end 2026, model "KTM 125 Duke, 390 Duke (and platform-shared RC models)" — an unqualified build-location claim whose year span covers the 2025-onward 390 platform. src/motodiag/hardware/compat_data/compat_matrix.json line 1249 (added by Phase 225, commit cac7e6c): model_pattern "390%", year_min 2013, year_max 2025, notes "390 Duke/RC/Adventure (Bosch, Bajaj-built): not listed — not compatible." Against this, known_issues_ktm_adventure.json entry 9: "The build location of the 2025-onward 390 platform could not be established from any manufacturer document, and is left open here rather than assumed to follow the earlier generation." docs/phases/completed/225B_implementation.md:75 confirms the decision and that "a test asserts that it stays that way" — but tests/test_phase225b_ktm_adventure.py:186 `test_the_unestablished_build_location_stays_unestablished` reads only the ktm_adventure fixture.

**Auditor's recommended fix.**

Bound the ktm_duke entry to the generation it can source (adjust year_end, or add "on the pre-2025 platform; the 2025-onward 390 platform's build location is not established — see the Adventure entry"), and drop "Bajaj-built" from the 390% compat_matrix note or bound its year_max below 2025. Then re-scope the 225B guard to search every Track K surface for a plant assertion against the 2025 390, not just its own file.

**Verifier verdict — real=False.**

The finding is stale: it describes the corpus at commit cac7e6c (Phase 225), not the working tree. Both quoted pieces of evidence fail against the actual files.\n\n(1) known_issues_ktm_duke.json line 34 entry: the auditor quotes year_end 2026 and model "KTM 125 Duke, 390 Duke (and platform-shared RC models)". The file actually reads "model": "KTM 125 Duke, 390 Duke (and platform-shared RC models) - pre-2025 platform", "year_end": 2024, and its description carries an explicit bound: "Scope note added at Phase 240: this covers the platform up to 2024. The build location of the 2025-onward 390 platform could not be established from any manufacturer document - see the mid-size Adventure file - so do not carry this claim across that change."\n\n(2) compat_matrix.json line 1249: the auditor quotes year_max 2025 and notes "390 Duke/RC/Adventure (Bosch, Bajaj-built): not listed - not compatible." The file actually reads "year_max": 2024 and "notes": "390 Duke/RC/Adventure (Bosch): not listed - not compatible." The sibling 125% row (line ~1237) was corrected identically.\n\ngit diff shows these are uncommitted Phase 240 edits applying exactly the recommended fix (year_max 2025->2024 on both KTM rows, ", Bajaj-built" removed from both notes, ktm_duke year_end 2026->2024, model bounded to "pre-2025 platform"). git show cac7e6c:src/motodiag/hardware/compat_data/compat_matrix.json reproduces the auditor's exact text at line 1249 with year_max 2025 - that is the version it read.\n\n(3) The re-scoped guard the fix asks for already exists. The auditor cites the scratchpad staging copy of the Gate 12 test, which has no build-location check. The live tests/test_phase240_gate12.py (untracked, newer, and textually different from the scratchpad copy) already contains a corpus-wide guard in test_the_deliberate_absences_hold_across_every_surface, check (b), over a _track_k_surfaces() set that includes every European known_issues file, all DTC files, compat_matrix.json, adapters.json and parts.json:\n\n    for m in _re.finditer(r"(?:Bajaj|Chakan|built in India)[^\\"]{0,160}", blob):\n        assert not _re.search(r"20 ?2[5-9]", m.group(0)), f"{name}: 2025+ 390 build location - {m.group(0)[:90]}"\n\nIts own comment names this very audit: "The audit found 'Bajaj-built' in compat_matrix and a withheld cost figure in parts.json - neither of which the first draft's file set reached." The test passes (verified, 7 consecutive runs).\n\nA corpus-wide grep for Bajaj finds it in exactly one seed data file (known_issues_ktm_duke.json, bounded as above); every other hit is a test, phase log or ROADMAP row. No file asserts a plant for the 2025-onward 390 platform.\n\nAccurate but no longer load-bearing parts of the finding: known_issues_ktm_adventure.json does say "The build location of the 2025-onward 390 platform could not be established from any manufacturer document, and is left open here rather than assumed to follow the earlier generation", and tests/test_phase225b_ktm_adventure.py:186 test_the_unestablished_build_location_stays_unestablished does read only its own `raw` fixture. But the contradiction those facts were meant to expose is already closed in the content, and the cross-file guard already exists at the gate.

**Verifier's corrected_fix.**

No change required - the fix is already applied in the working tree (uncommitted Phase 240 edits) and the cross-surface guard already exists in tests/test_phase240_gate12.py. Two optional residual items, neither blocking the gate:\n\n1. known_issues_ktm_duke.json line 34: the entry TITLE still reads "The 125 and 390 Duke are built in India by Bajaj - what that changes is parts sourcing, not quality" with no year qualifier. The claim is bounded by the structured fields (year_start 2011 / year_end 2024, model "... - pre-2025 platform") and by the description's scope note, so year-filtered retrieval cannot surface it for a 2025 bike. Only a title-only rendering would show it unscoped. If that surface matters, append "(pre-2025 platform)" to the title. Note the Gate 12 guard would still pass either way, since the regex only fires on a 2025-2029 year within 160 chars of the plant word.\n\n2. tests/test_phase225b_ktm_adventure.py:186 remains fixture-local. That is now acceptable rather than a gap, because Gate 12 check (b) enforces the same decision corpus-wide across all Track K surfaces. Leave the 225B test as the phase-local assertion; do not duplicate the corpus-wide scan into it.\n\nOne observation worth passing on: the gate guard test_the_deliberate_absences_hold_across_every_surface failed on my first invocation and then passed seven consecutive re-runs with unchanged file mtimes (all seed files last written 22:33:53, before any of my runs). I could not reproduce the failure. Most likely a concurrent write from the in-progress Phase 240 rather than a real flake, but if the gate is run while another process is editing the seed files, expect that.


### [REJECTED] known_issues_mv_agusta_triple.json still claims the F3 valve interval is unconfirmed after Phase 238 resolved and printed it

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json`

**Evidence.**

Line 124, entry 4 title: "MV triple service intervals must come from the specific model's manual — the widely quoted F3 figure is unconfirmed", description: "For the F3 675 the commonly quoted valve interval could not be confirmed against MV's own table — the figure circulates widely and traces to sources that could not be opened, so it is not repeated here." But known_issues_european_intervals.json entry 9 now states: "The F3 675/800 MY2020 maintenance manual carries the same 30,000 km valve figure, which resolves the interval Phase 234 could not confirm." Phase 238 amended the equivalent stale deferral in known_issues_ktm_adventure.json in place (git diff shows the title rewritten to "...share an engine and its valve interval..." and the description marked "corrected at Phase 238"), but left the MV one untouched.

**Auditor's recommended fix.**

Amend entry 4 the way ktm_adventure was amended — retitle away from "is unconfirmed", and replace the "not repeated here" sentence with the Phase 238 resolution and a pointer to known_issues_european_intervals.json. Leave the clearance-values omission in the same entry alone; that one is still true.

**Verifier verdict — real=False.**

The finding reproduces only against git HEAD, not against the file on disk. The working tree is dirty (git status shows ' M src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json'), and entry 4 has already been amended in exactly the way the finding recommends. The auditor's two quoted strings — the title '...the widely quoted F3 figure is unconfirmed' and the description clause '...so it is not repeated here' — both appear on the MINUS side of `git diff HEAD` for that file; neither is in the current file. Line 124 now reads: "title": "MV triple service intervals must come from the specific model's manual — models on one engine sit on different ladders". The description now reads: "For the F3 675 the commonly quoted valve interval could not be confirmed WHEN THIS FILE WAS WRITTEN. **Phase 238 later opened MV's own maintenance manuals and resolved it**, and found that the 798cc triple sits on two different ladders in overlapping model years — so the instruction here is now documented rather than suspected: read the interval from the specific model's own manual, never from a sibling's. The figures are in the European intervals file." And fix_procedure step 2 was rewritten from "Do not quote the widely circulated F3 valve interval as established; it could not be confirmed against the manufacturer's own table" to "Take the F3 valve interval from the European intervals file or from the model's own maintenance manual — Phase 238 resolved it from MV's own documents — and never from a sibling model, which may sit on a different coupon ladder." So the retitle, the removal of the stale omission claim, and the forward pointer to known_issues_european_intervals.json are all already present, and the clearance-values omission was correctly left alone. The rest of the finding's supporting evidence is accurate but moot: known_issues_european_intervals.json entry 9 does say "The F3 675/800 MY2020 maintenance manual carries the same 30,000 km valve figure, which resolves the interval Phase 234 could not confirm", and Phase 238 (commit 8374cb1) did amend known_issues_ktm_adventure.json entry 7 in place to "The Adventure and its Duke sibling share an engine and its valve interval, but not the rest of the service schedule" / "corrected at Phase 238". The MV amendment follows that same precedent (pointer, no figures reprinted). Verified by running the suites read-only: tests/test_phase233_mv_agusta_triple.py and tests/test_phase238_european_intervals.py = 56 passed; tests/test_phase240_gate12.py = 46 passed. Nothing to fix.

**Verifier's corrected_fix.**

No fix needed — the amendment is already in the working tree. For the record, had the fix been applied as literally written it would have been unsafe: tests/test_phase233_mv_agusta_triple.py::TestIntervalsAreDeferred::test_the_unconfirmed_figure_is_not_repeated asserts re.search(r"could not be confirmed|not repeated here", claims(interval_entry)), so removing BOTH the 'is unconfirmed' framing and the 'not repeated here' sentence, as the recommendation instructs, breaks that test. The amendment on disk survives only because it retains 'could not be confirmed' in a past-tense clause ('could not be confirmed when this file was written'). Any future edit to this entry must keep one of those two phrases, and must not print '12,000 km' anywhere in the file (same test bans it) — which is why the amendment correctly routes the reader to known_issues_european_intervals.json for the 30,000 km figure instead of reprinting it, matching the ktm_adventure precedent's 'Interval figures are deliberately not reproduced here, because Phase 238 owns them'.


### [REJECTED] Gate 12's campaign-number test covers four fields of one file family and two of the six reference formats the Phase 231 decision names

- **severity (auditor):** medium
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py`

**Evidence.**

Line 245 `test_no_campaign_reference_number_anywhere_in_track_k` builds `text = " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])` and matches `re.compile(r"\b\d{2}V\d{6}\b|\bRecall \d{6,7}\b")` over `known_issues_{bmw,ducati,ktm,triumph,aprilia,mv,european}*.json` only. Not scanned: the `model`, `symptoms`, `parts_needed` and `notes` fields (the Triumph transition year lives in `model`); the six Track K DTC files; adapters.json and compat_matrix.json (where "Bajaj-built" lives); parts.json (where "USD 1,226" lives). Not matched: DVSA `R/YYYY/NNN`, bare 7-digit campaign ids, Transport Canada `YYYY-NNN`, ACCC/PRA formats. The docstring claims the decision is "enforced corpus-wide for the European files", which overstates what the assertion does.

**Auditor's recommended fix.**

Widen the field set to every assertion-bearing string in an entry (or json.dumps the entry), extend the file set to the DTC files, compat_matrix.json, adapters.json and parts.json, and add the DVSA / bare-7-digit / Transport Canada / ACCC alternatives to the regex. If the wider scan is too noisy against OEM part numbers in parts.json, exclude the `oem_part_number` field explicitly rather than excluding the file.

**Verifier verdict — real=False.**

See above.

**Verifier's corrected_fix.**

Do not apply the recommended fix as written — it is built on leaks that do not exist, and two of its specifics would actively break the gate.

DO NOT: extend the file set to parts.json/adapters.json/compat_matrix.json for campaign numbers (zero matches today, and the suggested `oem_part_number` carve-out addresses a noise source that is not the real one); do not add a bare-7-digit alternative over `json.dumps` (it false-positives on every `–` en-dash range — `125–390`, `916–998` — which is how the finding's own scan produced its hits); do not extend the campaign regex to the DTC files expecting to catch the deliberate absences, which are a different decision (item 2) from campaign numbers (item 1) and are already guarded per-phase.

IF ANYTHING IS DONE, it is small and is about honesty of the docstring, not coverage:

1. Add `model`, `symptoms` and `parts_needed` to the joined text on line 254 — the three remaining assertion-bearing string fields. Use the field list explicitly rather than `json.dumps(e)`, so the escape-artifact problem never arises:
   `text = " ".join([e["title"], e["description"], e["fix_procedure"], e["model"]] + e["causes"] + e["symptoms"] + e["parts_needed"])`
   This passes today; it costs nothing and closes the gap the finding correctly identified.

2. Optionally add the DVSA and Transport Canada alternatives, which are anchored enough not to false-positive: `r"\bR/\d{4}/\d{3}\b"` and `r"\bRM/\d{4}/\d+\b"` (the latter matching what 231 and 233 already screen for). Verify against the corpus before adding any bare-numeric alternative.

3. Fix line 250 rather than leaving it. The brace glob is dead code that silently evaluates to `[]` and is carried only by the `or` fallback. A future editor who "fixes" the glob to a real one, or who deletes the fallback as redundant, turns the test into a no-op that still passes. Delete the brace glob and keep the comprehension as the sole file set.

4. Tighten the docstring to what the assertion does, e.g. "The Phase 231 decision, re-checked across all 30 European knowledge files as a backstop; per-phase tests (225B, 231, 233, 234, 237, 238) hold the primary guard, several over every field." That is the finding's one legitimate concern — a future phase should not read this row and stop checking — and it is fixed by naming the real owners rather than by widening the scan.


### [CONFIRMED] known_issues_european_parts.json discloses the withheld conversion cost as "a four-figure kit" and never says a figure is being withheld

- **severity (auditor):** low
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json`

**Evidence.**

Line 2, entry 0 ("Moto Guzzi 1200 8V roller-tappet kits are released only against a documented wear claim, not as prevention"), description ends: "Kit availability is currently unresolved — the fiche says 'contact' and one retailer shows a four-figure kit sold out." The entry carries no note that a cost figure is deliberately not printed; that claim lives only in known_issues_european_differentials.json entry 8. The same file also uses "four figures" and "a four-figure price per set" for BMW final drives and Ducati rockers, so the register is house style rather than a slip.

**Auditor's recommended fix.**

Add the omission claim to the european_parts entry where the reader meets it — one clause noting that circulating conversion cost figures are in more than one currency and are deliberately not printed, cross-referencing the differentials entry. Consider whether "four-figure" should stay at all on this specific kit, given it is the withheld figure's magnitude.

**Verifier verdict — real=True.**

Evidence reproduces verbatim. known_issues_european_parts.json entry 0 ends "Kit availability is currently unresolved — the fiche says 'contact' and one retailer shows a four-figure kit sold out.", carries no omission note, and a corpus-wide grep confirms the omission claim ("Conversion cost figures in circulation are in more than one currency and are deliberately not printed here.") exists only in known_issues_european_differentials.json entry 8. The "four figures"/"four-figure price per set" uses in entries 3 and 4 confirm the register is house style. The convention the finding relies on is real and enforced elsewhere: known_issues_ktm_adventure.json states "Interval figures are deliberately not reproduced here, because Phase 238 owns them" and "No campaign reference numbers are printed here deliberately...", and test_phase236 asserts the phrase for the Triumph transition year. Decisive corroboration the auditor missed: the same phase's catalogue row for the same kit (advanced/data/parts.json, slug moto-1a002060-tappet) records the identical retailer fact WITHOUT a magnitude — "Availability unresolved: fiche 'contact', one US retailer listing sold out. Cost 0 is the catalogue's unpriced sentinel (no USD-priced source...)" — so the knowledge entry is the outlier against its own phase's other surface, and sits in mild tension with it. Two qualifications: the title overstates — no cost figure is disclosed, and the magnitude comes from a Phase 239 retailer listing, not the Phase 237 NZD-rendered-as-USD figure, so "leaks the order of magnitude of the very figure that was pulled" is an inference across two quantities from two sources; and "the only surviving trace once the parts.json leak is fixed" is stale — that leak is already fixed and guarded by the Phase-240-widened test_no_withheld_cost_figure_survives_in_notes. Both affected test files pass today, so this is an editorial-consistency gap, not a rule violation, matching the "low" severity.

**Verifier's corrected_fix.**

Fix only entry 0 of known_issues_european_parts.json, and mirror the catalogue row's own wording rather than inventing new phrasing. Replace the final sentence of the description with: "Kit availability is currently unresolved — the fiche says 'contact' and one retailer listing is sold out. No conversion cost is printed here: the figures in circulation are in more than one currency, and the flat-versus-roller build entry in the differentials file states that omission and owns it." Optionally add a matching cause: "Cost figures in circulation are in more than one currency and are not printed." This drops "four-figure" for this specific kit (the withheld figure's topic) while leaving the BMW final-drive and Ducati rocker uses untouched — those are unrelated to any withheld figure, and entry 3's "a bearing at under a hundred dollars against a complete final drive at four figures" IS the entry's point; removing it would destroy real guidance. Constraints the fix must respect, which the recommendation does not mention: (1) tests/test_phase239_european_parts.py::test_no_campaign_numbers_and_no_currency_figures scans description+fix_procedure+causes for r"\$\s?\d|USD \d|NZD|EUR \d|GBP \d" — bare "NZD" alone is banned, so the clause must NOT name the currencies; use the differentials file's currency-agnostic "in more than one currency". (2) Entry 0's source is "service-manual", so no "Forum tip:" may be introduced (test_forum_tips_only_on_forum_entries). (3) Do not touch the title — test_no_title_collides_corpus_wide and test_no_entry_restates_a_237_differential key on title stems. (4) House form for the clause is the KTM Adventure pattern ("...deliberately not reproduced here, because Phase 238 owns them"), so naming the owning entry/phase in prose is in style. Additionally, the reworded sentence resolves the tension with the catalogue row, which says "no USD-priced source" for the same kit while the knowledge entry currently asserts a retailer showed a four-figure price.


### [CONFIRMED] Pre-existing recalls.json carries fifteen European rows with campaign and recall reference numbers, outside Track K's scope but inside the Phase 231 decision's wording

- **severity (auditor):** low
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/advanced/data/recalls.json`

**Evidence.**

30 rows, of which KTM 3, Ducati 3, BMW 3, Triumph 3, Aprilia 3 are European. Each carries `nhtsa_id` (e.g. "21V123000", "22V456000") and `campaign_number` (e.g. "HD-21-TOUR-BRAKE"). The ids are visibly synthetic placeholders on a 21V/22V/20V grid. `git log --diff-filter=A` puts the file at commit 68f65f4 (Track F Wave 1b, phases 151-159), well before Track K opened at 211, so this is not a Track K leak. Gate 12 does not read this file, and no Track K test does either.

**Auditor's recommended fix.**

Decide the boundary explicitly rather than by omission: either state in the Gate 12 docstring that the Phase 231 decision scopes to Track K-authored content and that recalls.json is pre-existing synthetic fixture data, or extend the scan to it and replace the European rows' ids with a frame-number routing note. Either is fine; leaving it unstated is what makes the invariant look broader than it is.

**Verifier verdict — real=True.**

Reproduced in full. `src/motodiag/advanced/data/recalls.json` holds 30 rows with make distribution `{Harley-Davidson: 5, Honda: 3, Suzuki: 3, KTM: 3, Ducati: 3, BMW: 3, Triumph: 3, Aprilia: 3, Yamaha: 2, Kawasaki: 2}` — 15 European rows (KTM/Ducati/BMW/Triumph/Aprilia x3), each carrying both fields, e.g. `"nhtsa_id": "21V567000", "campaign_number": "KT-21-890DUKE-FORK"`; `"22V678000" / "DU-22-PAN-SWING"`; `"21V901000" / "BMW-21-R1250GS-ABS"`; `"22V012000" / "APR-22-RSV4-ECU"`. The ids are visibly synthetic: all 30 are {19,20,21,22}V + one of 012/123/234/345/456/567/678/789/890/901 + 000 or 500. Provenance confirmed: `git log --diff-filter=A` gives one and only one commit, `68f65f4 2026-04-19 "Track F Wave 1b + Gate 7: Phases 151-155, 157, 159 shipped"`, and `git show 68f65f4:src/motodiag/advanced/data/recalls.json` returns the identical make distribution, so the file predates Track K (211) and has never been touched since. Scan coverage confirmed: the staged `scratchpad/test_phase240_gate12.py::test_no_campaign_reference_number_anywhere_in_track_k` iterates only `K.glob("known_issues_*.json")` filtered to the bmw/ducati/ktm/triumph/aprilia/mv/european prefixes; the untracked widened `tests/test_phase240_gate12.py` `_track_k_surfaces()` adds `DTC/*.json`, `compat_matrix.json` and `adapters.json` but still not recalls.json. `grep -ln "recalls.json|recall_repo|load_recalls" tests/test_phase2[1-4]*.py` returns nothing; the only test that opens the file is `tests/test_phase155_recall.py`. The surface is user-facing: `motodiag advanced recall list --make KTM` (cli/advanced.py:2865) reads the seeded rows, and `predictor.py:425` copies `nhtsa_id` into `FailurePrediction.applicable_recalls`.

Two qualifications that do not sink the finding but narrow it. First, the finding quotes the decision "as written" as "NO campaign or recall reference numbers anywhere in European content" — that is the audit brief's paraphrase, not the repo's. `docs/ROADMAP.md:381` records Phase 231 as "no campaign number appears in **the file** at all", and rows 232/233/234/225B each say "No campaign numbers, per the Phase 231 decision" about their own content file. The gate test is already named `..._anywhere_in_track_k`, so the Track K scope is carried by the test's name even though it is not spelled out. Second, `load_recalls_from_json` is called from no CLI seed command — only from `tests/test_phase155_recall.py` and the public `motodiag.advanced` export — so the rows reach a query only after a caller explicitly loads the seed (which `docs/phases/completed/159_implementation.md:30` documents as a real flow). The core observation stands: European content with campaign reference numbers sits in a shipped, make-queryable surface that no Track K guard scans.

**Verifier's corrected_fix.**

Take option A only. Option B — "extend the scan to it and replace the European rows' ids with a frame-number routing note" — breaks Phase 155 and must not be done:

- `src/motodiag/core/migrations.py:814` declares `campaign_number TEXT NOT NULL UNIQUE` on the `recalls` table, so the column cannot hold a prose routing note across 15 rows without colliding or carrying nonsense.
- `nhtsa_id` is the loader's idempotency key — `load_recalls_from_json` (`src/motodiag/advanced/recall_repo.py:505`) does `INSERT OR IGNORE` against the partial UNIQUE INDEX over `nhtsa_id`; strip it and re-running the loader duplicates every European row.
- `tests/test_phase155_recall.py::test_seed_has_30_campaigns` asserts `"nhtsa_id" in entry` and `"campaign_number" in entry` for every one of the 30 entries, so removing the keys fails an existing green test.
- `advanced recall mark-resolved --recall-id`, `recall lookup`, and `predictor.py:419-425`'s `applicable_recalls` all carry `nhtsa_id` as the record identifier.
- Substantively: a recall table without recall ids is not a recall table. The "route to a frame number instead" remedy that Phase 231 prescribes for prose is already this schema's `vin_range` column, which every row populates. The 231 decision is about prose citing an unverifiable reference as evidence; a recall database's primary key is a different thing.

So: add one sentence to the Gate 12 docstring (and, better, to the ROADMAP row 240 entry) stating that the Phase 231 decision scopes to Track K-authored knowledge, DTC, adapter and parts content, and that `advanced/data/recalls.json` is pre-existing Track F fixture data whose `nhtsa_id`/`campaign_number` are schema keys, deliberately out of scan.

Separately, the finding names the wrong defect in that file, and the real one is worth its own row. `docs/phases/completed/155_implementation.md:16` describes the seed as "~30 **real** NHTSA campaigns" and line 71 as "30 real federal campaigns", but the ids are on a synthetic 012/123/.../901 x 000/500 grid — fabricated identifiers documented as real. They surface verbatim through `motodiag advanced recall list --make KTM` and into `FailurePrediction.applicable_recalls`, where a row with `severity: "critical"` floors the prediction's severity to critical (`predictor.py:417-430`). That is the exact failure mode Phase 231 reacted to — a printed reference number that is not what it claims — one layer below the knowledge files. The fix is to label the fixture honestly rather than to strip the ids: correct the two "real" claims in `155_implementation.md`, and add a leading `_comment` row in `recalls.json` (or a line in the `load_recalls_from_json` docstring) saying the ids are illustrative sample data, not filed campaigns. The 155 doc's own make list ("Suzuki/KTM/Ducati/BMW/Triumph ~3 each") also omits the 3 Aprilia rows that have been in the file since 68f65f4.


---

## Dimension: provenance

**Auditor summary.** Audited all 257 entries in the 30 European known_issues files and all 44 make-specific DTC rows in the 6 European dtc_codes files against generic.json.

PROVENANCE HONESTY: 10 findings. The source vocabulary itself is clean (only service-manual 108, model-generated 131, forum 17, regulation 1 appear across the European corpus — no invented values). The single "regulation" entry genuinely quotes EU legal text verbatim and is correct. The defects are of three kinds: (a) one service-manual entry that rests on nothing at all and says so; (b) two forum entries that break the "Forum tip:" contract; (c) a systematic labelling inconsistency where the SAME evidence class is labelled service-manual in one entry and model-generated in another, inside the same file — most visibly TuneECU's compatibility table in known_issues_european_tooling.json (4x service-manual, 2x model-generated) and parts-fiche evidence in known_issues_european_parts.json (5x service-manual, 2x model-generated). Separately, known_issues_ktm_electrical.json carries three entries labelled "General knowledge entry" that in the same sentence claim to be drawn from KTM manuals, specifications and fitting sheets, and known_issues_triumph_vintage.json labels all 13 entries service-manual while several rest on period road tests, marque-club guidance and specialist-supplier literature.

DTC SHADOW: CLEAN. 23 of the 44 make rows share a code with generic.json; every one of them differs substantively from the generic row in both causes and fix (mechanical similarity check: no row exceeded 0.55 on either field). The remaining 21 rows (all 7 Aprilia, all 6 MV Agusta, and 8 others) share no code with generic.json and therefore shadow nothing — and the Aprilia and MV rows are the strongest in the set, since they exist precisely to overwrite an SAE meaning that would send a mechanic to the wrong system. Resolution order confirmed at /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/dtc_repo.py:41-56 (make first, generic as fallback). No row earns a shadow defect.

I also noted four cross-dimension observations about the deliberate absences, listed at the end, since they bear on gate closure.


### [REJECTED] service-manual entry that explicitly rests on no source at all

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_four.json`

**Evidence.**

Title: "Measure an MV Agusta F4 shim before ordering a kit — the diameter is not established and a Japanese kit may not fit". source = "service-manual". Opening sentence: "Drawn from an explicit gap in the sources consulted, and written because the gap itself is the useful information." And: "For the MV four the shim diameter **could not be established** from any source that could be opened: the figures in circulation disagree, and none was authoritative." The fix_procedure closes with "Treat any diameter quoted online for this engine as unverified until measured."

**Auditor's recommended fix.**

Change source to "unverified". The entry's content is good and should stay; only the label is wrong. Note that its sibling in known_issues_european_intervals.json ("The MV Agusta F4 shim diameter is still in no manufacturer document") legitimately carries service-manual because it does open the Brutale ORO/S workshop manual — so the two entries currently share a label while resting on opposite amounts of evidence.

**Verifier verdict — real=False.**

The quotes are accurate but the inference is wrong, and the fix would break a green test and mislabel the entry.

1) The entry does not "rest on no source at all". Its opener is "Drawn from an explicit gap in **the sources consulted**", and the operative sentence is "could not be established from any source **that could be opened**" — i.e. sources were opened and none of them states a diameter. Its four file-mates in /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_four.json establish which sources those were: entry 0 "Drawn from MV Agusta's own workshop manual", entry 3 "Drawn from the manufacturer's own maintenance table", entry 4 "Drawn from the manufacturer's own workshop documentation and the campaign record". docs/phases/completed/234_implementation.md records the same ("the workshop manual exists and names its tools"; "Entries | 5, all `service-manual`"). The shim entry reports a gap in that consulted manual set — a documented absence, not an absence of documents.

2) The corpus has an explicit, tested convention that a documented absence carries service-manual. In the very file the auditor holds up as the well-behaved sibling, known_issues_european_intervals.json entry 3 — "No European valve row opened carries a time trigger" — is source=service-manual and is *entirely* an absence claim ("**no mark in any month column**, on every document opened"). tests/test_phase238_european_intervals.py:41-46 states the rule in its own words: "Every interval rests on a manufacturer document. The one owner-report figure (a shim diameter) is labelled inside an entry whose own claim is the document's absence." So "filter by source=service-manual" in this corpus means "what the manufacturer documentation yielded", which legitimately includes "it does not state it". The two MV shim entries therefore do not "rest on opposite amounts of evidence"; they differ only in how specifically they name the volume opened (Phase 238 names the Brutale ORO/S manual; Phase 234 says "the sources consulted"), and no rule requires naming — tests/test_phase234_mv_agusta_four.py:224 only requires a "Drawn from" clause, and test_phase238's name-the-document rule is scoped to entries that print a figure, which this one deliberately does not.

3) service-manual is defined in-repo as "primary official document" (src/motodiag/core/migrations.py:3535), not as "cites a figure".

4) The recommended fix is wrong twice over. (a) "unverified" is not the neutral value here: migration 051 defines it as "origin never recorded — the honest value for every existing row" (migrations.py:3508-3509), and Gate 2 puts it in the forum-derived allowlist — FORUM_DERIVED = {"unverified", "forum"} at tests/test_phase78_gate2_integration.py:141 and :167 — so relabelling would file a Track-K-authored entry into the forum-derived population that is required to carry "Forum tip:". docs/phases/completed/235_implementation.md:168-176 rejected "unverified" for exactly this reason. (The 90% threshold would survive: 675/677 = 0.997 becomes 675/678 = 0.9956, so it fails silently as semantics rather than loudly as a test.) (b) It breaks a currently-green test: tests/test_phase234_mv_agusta_four.py:223 asserts {e["source"] for e in raw} == {"service-manual"}; the file's 31 tests pass today (verified by running pytest, read-only).

The entry also honours the deliberate-absence rule it is supposed to honour: it prints no shim diameter anywhere.

**Verifier's corrected_fix.**

No source change. Leave source = "service-manual"; it matches the corpus's own convention for documented absences (known_issues_european_intervals.json entries 3 and 10) and the recorded Phase 234 decision.

If anyone still wants the entry sharpened before the gate, the only defensible change is editorial, not a relabel: replace the vague "any source that could be opened" with the volumes actually consulted (the same MV Agusta workshop manual named by entries 0 and 4 of the file), so the entry reads like intervals entry 3 ("no mark in any month column, on every document opened") rather than like an unsourced assertion. That keeps test_phase234_mv_agusta_four.py:223 and the "Drawn from" check green and needs no test edit.

Do NOT set source = "unverified" under any circumstance: migrations.py:3508 reserves it for legacy rows with no recorded origin, and Gate 2 (tests/test_phase78_gate2_integration.py:141,167) treats unverified as forum-derived and subject to the "Forum tip:" rule this entry deliberately does not carry. If a relabel were ever wanted, "model-generated" — not "unverified" — would be the vocabulary-correct value, and it would additionally require editing tests/test_phase234_mv_agusta_four.py:223, docs/phases/completed/234_implementation.md ("Entries | 5, all service-manual") and ROADMAP.md row 234.


### [REJECTED] forum entry with no "Forum tip:" in fix_procedure (MV triple starter clutch)

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json`

**Evidence.**

Title: "The MV triple's starter clutch is handed for reverse rotation — and is reported to have been fitted backwards". source = "forum". Description opens "Drawn from owner-forum reporting, and flagged as such because it is not manufacturer documentation." The fix_procedure is a five-step numbered procedure ending "Record the battery test result on the job card..." and contains no "Forum tip:" anywhere.

**Auditor's recommended fix.**

Either add a "Forum tip:" clause to fix_procedure carrying the owner-sourced claims (the weak-battery cause and the reassembled-backwards reports are exactly that), or re-source the entry. Adding the marker is the smaller change and matches the description's own framing.

**Verifier verdict — real=False.**

The literal observation reproduces, but the "contract break" does not — and the recommended fix would break a currently-green test.

WHAT REPRODUCES. In /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json, entry [1] has "source": "forum", its description opens "Drawn from owner-forum reporting, and flagged as such because it is not manufacturer documentation.", and its fix_procedure is five numbered steps ending "5. Record the battery test result on the job card..." with no "Forum tip:" anywhere. grep -c "Forum tip:" on the file returns 0.

WHY IT IS NOT A BREAK. Phase 233's own test file — /Users/lilquant/Projects/moto-diag/tests/test_phase233_mv_agusta_triple.py, test_provenance_is_recorded_per_entry (line ~256) — asserts the OPPOSITE of the finding, over every entry in this exact file:

    assert {e["source"] for e in raw} <= {"service-manual", "forum"}
    for e in raw:
        assert re.search(r"[Dd]rawn from", e["description"]), e["title"]
        assert "Forum tip" not in e["fix_procedure"], e["title"]

The `raw` fixture is `json.loads(TRIPLE.read_text(...))` — the whole file, forum entry included, no filtering. So adding a "Forum tip:" clause as recommended turns a green suite red: .venv/bin/python -m pytest tests/test_phase233_mv_agusta_triple.py currently reports 30 passed.

The same holds for the "other" break the finding cites: known_issues_triumph_bonneville.json is pinned by tests/test_phase226_triumph_bonneville.py::test_no_entry_fabricates_a_forum_tip ("Gate 2's other half, asserted locally too") — 45 passed. Both alleged breaks are deliberate, test-pinned decisions, not oversights.

THE RULE IS MISSTATED. The corpus-wide rule lives in /Users/lilquant/Projects/moto-diag/tests/test_phase78_gate2_integration.py and is a POPULATION THRESHOLD, not a per-entry requirement:

    FORUM_DERIVED = {"unverified", "forum"}
    ...
    assert issues_with_tips >= len(forum_sourced) * 0.9

Measured over the seed corpus: the forum-derived population is 677 entries (660 legacy source-less rows defaulting to "unverified" + 17 "forum"), 675 carry a tip = 99.70% against a 90.0% floor. Gate 2 passes with a ~65-entry margin; two abstentions cannot trip it. tests/test_phase78_gate2_integration.py: 22 passed. Its docstring and docs/ROADMAP.md row 218 record why the rule is an allowlist threshold: at Phase 218 the obvious fix (adding tips to non-forum-derived entries) "would have fabricated exactly the provenance the source column exists to record."

THE GATE CLAIM IS FALSE. The staged Gate 12 test at .../scratchpad/test_phase240_gate12.py contains no forum/Forum-tip pairing check at all. Its only provenance assertion is test_provenance_vocabulary_is_the_six_values (line 257-261), which checks the six-value vocabulary. grep for "tip" in that file returns one hit, an unrelated fix_procedure concatenation at line 254. So "a gate test that checks the forum/Forum-tip pairing will fail on it" is not true of the gate that is actually about to close this track.

SCOPE, NOT CONTRADICTION. Track K runs two provenance conventions on purpose. Files that adopt the legacy in-body marker pin it locally (tests/test_phase225b_ktm_adventure.py has both test_forum_entries_carry_a_forum_tip and test_non_forum_entries_do_not_claim_one; known_issues_european_differentials.json and known_issues_european_parts.json follow it — 15 of the 17 forum entries carry a tip). Files 226, 227, 231, 233, 234, 235 and 236 instead carry provenance in the `source` field plus a mandatory "Drawn from ..." clause opening the description, and forbid "Forum tip:" outright. This entry honours that convention exactly: source=forum, and the description's first six words are "Drawn from owner-forum reporting, and flagged as such because it is not manufacturer documentation." The mechanic-facing hedge the finding says is missing is present — it is the first sentence read, and steps 4 and 5 restate it ("this is a commonly reported failure rather than a recalled one; there is no campaign and no free remedy").

No change is warranted. If anything is worth doing here it is documentation, not content: the two conventions are pinned per-phase but never stated in one place, which is what let this reading happen.

**Verifier's corrected_fix.**

No fix to the JSON. The entry is correct as shipped and the recommended edit is actively harmful — inserting "Forum tip:" into fix_procedure fails tests/test_phase233_mv_agusta_triple.py::test_provenance_is_recorded_per_entry, which asserts `"Forum tip" not in e["fix_procedure"]` for every entry in this file. Re-sourcing the entry (the finding's alternative) is worse: it would fail the same test's `{e["source"]} <= {"service-manual", "forum"}` check plus test_the_sprag_entry_is_marked_forum_sourced, and would overstate provenance on content that genuinely rests on owner reports.

The only defensible follow-up is documentary, and it is optional: record in docs/ROADMAP.md (or a Track K conventions note) that the track runs two provenance conventions — the legacy in-body "Forum tip:" marker, pinned by tests/test_phase225b_ktm_adventure.py and used by known_issues_european_{differentials,parts}.json and known_issues_ktm_adventure.json; and the source-field-plus-"Drawn from" prose convention adopted from Phase 226 onward, which forbids the marker and is pinned by tests/test_phase226, 227, 231, 233, 234, 235 and 236. Gate 2's 90% threshold over the {unverified, forum} population is what reconciles them, and it sits at 675/677 = 99.7%.


### [CONFIRMED] forum entry with no "Forum tip:" in fix_procedure (air-cooled Bonneville starter and wheel faults)

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_triumph_bonneville.json`

**Evidence.**

Title: "Air-cooled Bonneville starter and wheel faults that never got a recall — the idler-gear boss, the sprag clutch and left-hand rear spokes". source = "forum". Description opens "Drawn from owner-forum consensus and clusters of owner complaints filed with the road-safety regulator, not from a recall or a Triumph bulletin — and that distinction is the point of the entry." fix_procedure step 1 says "the evidence is owner reports and forum consensus, and the entry says so because a customer conversation should say so too" — but the literal string "Forum tip:" never appears.

**Auditor's recommended fix.**

Rephrase step 1 to lead with "Forum tip:" (e.g. "Forum tip: treat these as inspection items on an early air-cooled bike..."), which changes no substance and satisfies the contract.

**Verifier verdict — real=True.**

Reproduced verbatim. Entry 11 of /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_triumph_bonneville.json is the only `"source": "forum"` entry in the file; its description opens exactly as quoted ("Drawn from owner-forum consensus and clusters of owner complaints filed with the road-safety regulator, not from a recall or a Triumph bulletin..."), its fix_procedure step 1 reads "...the evidence is owner reports and forum consensus, and the entry says so because a customer conversation should say so too", and the literal token "Forum tip" appears nowhere in it (grep and a JSON scan both confirm).

Corpus-wide check: 917 entries, 677 forum-derived (source in {unverified, forum}), and exactly TWO lack the marker — this entry and the MV triple sprag-clutch entry the finding itself names. Of the 17 entries with source == "forum", 15 carry the marker. Three of the five Track K files holding forum entries enforce the biconditional locally and comply (tests/test_phase225b_ktm_adventure.py:62-72, tests/test_phase237_european_differentials.py:60-62, tests/test_phase239_european_parts.py:242-244: `assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum")`). So the convention is real and this entry is off it.

Two qualifications the finding overstates, neither of which sinks it:
(1) "any mechanical check over the corpus reads it as an unmarked forum entry" — the in-tree mechanical check, tests/test_phase78_gate2_integration.py:114-155, is a >=90% threshold over the forum-derived population. At 675/677 = 99.7% it passes comfortably, so nothing is red today. That argues for medium rather than high severity.
(2) The omission is not accidental at the file level: ROADMAP.md row 226 and docs/phases/completed/226_implementation.md both record "one is `forum`, which says so in its own prose", and tests/test_phase226_triumph_bonneville.py:184-187 asserts `"Forum tip" not in e["fix_procedure"]` for EVERY entry in the file. That test's own docstring calls itself "Gate 2's other half, asserted locally too" — but Gate 2's other half (tests/test_phase78_gate2_integration.py:157-177) applies only to NON-forum-derived entries. The local assertion is mis-scoped by exactly the allowlist/denylist bug Phase 226 was fixing in Gate 2, so it is a scoping slip, not a deliberate carve-out of the contract. The contract break therefore stands.

**Verifier's corrected_fix.**

The JSON edit is right in principle but the recommended placement is wrong, and the fix is incomplete — as written it turns a passing test red.

1. DO NOT lead step 1 with the marker. All 15 compliant forum entries put "Forum tip:" in the FINAL step (measured position 0.65-0.82 through fix_procedure) and phrase it "Forum tip: owners ...". This is load-bearing: src/motodiag/advanced/predictor.py:485-517 `_extract_preventive_action` returns everything AFTER the "Forum tip:" marker, tidied and truncated to 200 chars, as the entry's preventive action. A leading marker makes that string the remainder of the whole five-step procedure cut off mid-sentence; a trailing step makes it a self-contained tip. Verified by running the real function on both variants. Append instead, keeping steps 1-5 unchanged, e.g.: "6. Forum tip: owners treat these as inspection items on an early air-cooled bike rather than documented defects, since there is no campaign and no free remedy to quote."

2. MANDATORY companion change the finding misses: tests/test_phase226_triumph_bonneville.py:184-187 (`TestProvenanceIsRecordedHonestly::test_no_entry_fabricates_a_forum_tip`) asserts `"Forum tip" not in e["fix_procedure"]` over ALL 11 entries. Adding the marker fails it. Re-scope it to the biconditional already used by the sibling phases, e.g. `assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"]`, which subsumes the existing fabrication guard for the 10 service-manual entries and matches tests/test_phase239_european_parts.py:242-244. Nothing else breaks: the entry is forum-sourced, so Gate 2's inverse assertion (test_phase78_gate2_integration.py:157) is unaffected, and no other test in the tree asserts on this file's fix_procedure text.

3. Fix the sibling in the same change or the corpus stays inconsistent at 15/17: src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json has the identical shape (one `forum` entry, the reverse-rotation starter clutch, no marker) and tests/test_phase233_mv_agusta_triple.py:259 carries the same over-broad blanket assertion needing the same re-scope.

4. Update the recorded justification, since it is what licenses the current state: docs/ROADMAP.md row 226 and docs/phases/completed/226_implementation.md both say the forum entry "says so in its own prose" — that prose stays, but the row should note the marker was added and the local guard re-scoped, so the next reader does not restore the blanket assertion.


### [CONFIRMED] Same vendor document labelled service-manual in four entries and model-generated in two, inside one file

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_tooling.json`

**Evidence.**

service-manual: "Drawn from TuneECU's own published compatibility table." (Supports BMW); "Drawn from TuneECU's own compatibility table." (Ducati by ECU part number); "Drawn from TuneECU's own compatibility table, read column by column." (KTM/Triumph degradation); "Drawn from TuneECU's published compatibility table." (the "if it is not listed" entry). model-generated, same file: "Drawn from TuneECU's own adaptor list, read across makes."; "Drawn from TuneECU's compatibility table and vendor cable listings." Also carrying service-manual in this file: "Drawn from TEXA's own brochure...", "Drawn from TEXA's own catalogue.", "Drawn from HEX's published GS-911 licence terms."

**Auditor's recommended fix.**

Pick one label for tool-vendor primary documentation and apply it across the file. If the track's position is that a vendor's own published compatibility table counts as a manufacturer document (of the tool), promote the two model-generated entries and record the rule; if not, demote all eight. Either way the file should not disagree with itself, and the TEXA brochure/catalogue entries are the weakest members of the service-manual set.

**Verifier verdict — real=True.**

Independently reproduced, verbatim, in /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_tooling.json (13 entries; array indices below).

TuneECU's compatibility table is cited on both sides of the label: service-manual at [0] "Drawn from TuneECU's own published compatibility table.", [1] "Drawn from TuneECU's own compatibility table.", [2] "Drawn from TuneECU's own compatibility table, read column by column.", [12] "Drawn from TuneECU's published compatibility table." — and model-generated at [11] "Drawn from TuneECU's compatibility table and vendor cable listings." and [10] "Drawn from TuneECU's own adaptor list, read across makes." The other service-manual entries are [3] "Drawn from TEXA's own published material.", [4] "Drawn from TEXA's own brochure...", [5] "Drawn from TEXA's own catalogue.", [6] "Drawn from HEX's published GS-911 licence terms." I read all eight in full: none cites a motorcycle manufacturer document, parts fiche, regulator record or regulation. The auditor's only imprecision is cosmetic — [10] cites the adaptor list, not the compatibility table, so strictly the table itself is 4 service-manual vs 1 model-generated.

No principle separates the two sets. Not document identity (same table, both labels). Not document class ([5] TEXA's catalogue = service-manual vs [9] "Drawn from OBDSTAR's own product pages." = model-generated; both are vendor product catalogues read for coverage). Not "the claim exceeds the document" ([2] "read column by column" and [12], the file's most inferential entry — a general lesson about how to read any vendor's document — are service-manual, while [10], which quotes the adaptor's literal name "Guzzi-Ducati-Aprilia 3pin", is model-generated).

The label has a user-facing consequence, so this is not cosmetic: src/motodiag/cli/kb.py defines VERIFIED_SOURCES = {"service-manual","mechanic-verified","regulation"} and _render_provenance prints "Written from general knowledge, not a service manual. Confirm figures and procedure against the manual" for model-generated and stays SILENT for service-manual. Eight entries resting on a tuning vendor's table, a brochure, a product catalogue and a licence agreement currently render with no caveat; five of materially identical evidence render with one.

Nothing in the tree enforces consistency: tests/test_phase236_european_tooling.py:59 only asserts sources <= {"service-manual","model-generated"}; the staged Gate 12 test only checks the six-value vocabulary (test_provenance_vocabulary_is_the_six_values). Both currently pass (81 passed). docs/phases/completed/236_implementation.md:48 records the split as a count ("13 - 8 service-manual, 5 model-generated") with no rule, and 236_phase_log.md says nothing about provenance at all.

The finding is if anything understated: the track already decided this, one phase earlier. docs/phases/completed/235_implementation.md:174 states "The regulation entries are service-manual, meaning primary official document, with the exact citation in the body and a test requiring it; vendor-documentation entries are model-generated." That rule is enforced by tests/test_phase235_aprilia_mv_electrical.py::TestProvenanceIsHonest (service-manual entries must contain "Service Station Manual"; model-generated must not be "dressed as manuals"). In that same file, "Drawn from TuneECU's own published guide" is model-generated — same vendor, same document class, adjacent phase, opposite label from Phase 236.

**Verifier's corrected_fix.**

The recommended fix is right that the file must stop disagreeing with itself, but wrong to present the direction as an open choice, and it under-scopes the affected entries.

1. Direction is already settled, not a coin flip. Phase 235 recorded and TESTED the rule one phase earlier: service-manual means primary official document (a manufacturer manual, a regulator record), regulation means legal text, and vendor documentation is model-generated (docs/phases/completed/235_implementation.md:174; tests/test_phase235_aprilia_mv_electrical.py::TestProvenanceIsHonest). Promoting the vendor entries to service-manual — the auditor's first option — would put Phase 236 in direct conflict with a passing test in Phase 235 and would silence the CLI caveat across a file where nothing rests on a manufacturer document. So: DEMOTE, do not promote.

2. Scope is four entries becoming uniform, not "the two model-generated ones" becoming eight. Demote all eight service-manual entries — indices [0][1][2][12] (TuneECU compatibility table), [3][4][5] (TEXA published material / brochure / catalogue), [6] (HEX GS-911 licence terms) — to model-generated. That makes the file 13/13 model-generated. Entries [7]-[11] are already correct and need no edit; entry [7] ("the manufacturer group's own tooling arrangements", no named document) is correct on any reading.

3. Do NOT invent a seventh vocabulary value (e.g. "vendor-documentation") as part of this fix, tempting as it is. The six values are pinned by migration 052 and by the staged Gate 12 assertions test_provenance_vocabulary_is_the_six_values and test_schema_version_pin (SCHEMA_VERSION == 52). Extending the CHECK constraint needs its own migration and touches the API Literal in src/motodiag/api/routes/kb.py and src/motodiag/cli/kb.py — exactly what Phase 235B did for `regulation`. That is a follow-up phase, not a pre-gate edit.

4. Verify the demotion breaks nothing (it does not, as staged): tests/test_phase236_european_tooling.py:59 asserts sources <= {service-manual, model-generated} — still true; its test_no_forum_tips_claimed still holds (no "Forum tip" anywhere in the file), which is also what keeps Gate 2's inverse assertion — model-generated entries must NOT claim forum tips — satisfied; Gate 2's forum-tip population is unverified+forum, untouched; Gate 12's count guard keys on entry count, not source. No test asserts the 8/5 split.

5. Two bookkeeping items the auditor omits, without which the corpus goes stale rather than consistent: update the metrics line docs/phases/completed/236_implementation.md:48 ("13 - 8 service-manual, 5 model-generated" becomes 13 model-generated) and add a positive test to tests/test_phase236_european_tooling.py asserting the rule in the file that violated it — e.g. no entry whose description names a tool vendor (TuneECU, TEXA, HEX, OBDSTAR, DiagCode) may carry source == "service-manual" — so the next cross-make phase inherits the rule instead of re-deciding it.

Note also that the auditor's aside that "the TEXA brochure/catalogue entries are the weakest members" is a red herring under the corrected direction: after demotion all eight sit in the same bucket, and no ranking among them is needed.


### [REJECTED] Parts-fiche evidence labelled model-generated in two entries while five fiche entries in the same file carry service-manual

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json`

**Evidence.**

model-generated: "Drawn from Ducati's parts fiche and specialist vendors." (Desmoquattro opening rocker arm) and "Drawn from Hiflofiltro's own catalogue and the Moto Guzzi fiche." (small-block oil filter). service-manual, same file: "Drawn from Aprilia's parts fiche, read this phase."; "Drawn from Triumph's parts fiche."; "Drawn from KTM's parts fiche, read this phase."; "Drawn from KTM's parts fiche, read this phase, with a correction from refutation."; "Drawn from the Piaggio Group's parts fiche and its technical bulletins, read this phase."

**Auditor's recommended fix.**

Promote both to service-manual, or, if the mixed vendor component is the reason for the lower label, say so in the description the way the Aprilia charging entry does. The current split is invisible to a reader and unexplained in the text.

**Verifier verdict — real=False.**

The seven quoted strings exist (I reproduced all of them in /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json: entries 2, 5, 6, 7, 8 are service-manual; entries 4 and 10 are model-generated), but the finding's premise, its "no defensible reason" claim, and its fix are all wrong.

1. The rule it rests on does not exist. "A parts fiche is explicitly one of the four things a service-manual entry is supposed to cite" appears nowhere — not in docs/, not in tests/test_phase239_european_parts.py, not in the staged tests/test_phase240_gate12.py (which touches provenance only at line 261, a vocabulary-membership check). No test or phase decision keys provenance off the word "fiche".

2. The rule that DOES exist says the opposite. docs/phases/completed/235_implementation.md:172-174: "The regulation entries are `service-manual`, meaning primary official document, with the exact citation in the body and a test requiring it; vendor-documentation entries are `model-generated`." Both flagged entries rest materially on non-manufacturer vendor material: entry 4's load-bearing content is the replacement route (a specialist exchange re-chroming service and aftermarket tool-steel rockers, with its own causes list conceding "Aftermarket fitment claims span engine families the fiche does not, and are the maker's claims"); entry 10's entire claim is an absence in Hiflofiltro's third-party catalogue.

3. The convention is applied consistently across Track K, so the split is not an anomaly. In known_issues_european_tooling.json the seven service-manual entries are ones whose source document *states* the claim (entry 0 says so explicitly: "The table also carries its own negative statement, which is what makes this readable rather than inferred"; entry 12 is entirely about that sentence), while the five model-generated entries are the composites and cross-readings — "the manufacturer group's own tooling arrangements", "DiagCode's published function list" (a comparison against the factory tool), "OBDSTAR's own product pages" (plural), "TuneECU's own adaptor list, read across makes", "TuneECU's compatibility table and vendor cable listings". known_issues_aprilia_mv_electrical.json is the same: service-manual for the Service Station Manual, model-generated for "tool vendors' own published cable listings", "published third-party tables", "TuneECU's own published guide". Under either reading of the convention (vendor-documentation, or inferred-rather-than-stated) both flagged entries land on model-generated: the Guzzi one is an argument from a catalogue's silence that the catalogue itself does not license, which is exactly what the tooling file's entry 12 says makes an absence readable.

4. The file itself already differentiates by evidence type, not by the word "fiche". Entry 3, "Drawn from a parts retailer's catalogue and owner reports", is forum. And every service-manual entry in the file asserts a first-hand manufacturer-document read — "read this phase" (Aprilia, KTM x2, Piaggio), "text-extracted and read" (Guzzi bulletins), "checked against the fiche" (MV) — while neither flagged entry makes that claim. The auditor also misquotes the shape of entry 10: it opens on Hiflofiltro's catalogue, not on a fiche.

5. "Unexplained in the text" is false. Both descriptions name the non-manufacturer source in their first sentence, which is the same signal the tooling file uses. And the same phase's parts.json corroborates the intent at finer grain: ducati-20810018a-rocker-arm and its ST4 sibling are verified_by "service-manual" (the fiche fact), electraeon-super-rocker-rocker-arm is "forum" ("Fitment claim is the maker's"); moto-2a000633-oil-filter is "service-manual" and every Hiflofiltro row is "forum". The known-issues entries are composites of both grades, and a single per-entry label cannot claim the higher one.

6. The recommended fix would break something. "service-manual" is in VERIFIED_SOURCES (src/motodiag/cli/kb.py:225), so `kb show` prints no warning for it, while model-generated prints "Written from general knowledge, not a service manual. Confirm figures and procedure...". Promoting these two silences that warning over a vendor price comparison and an inference from a third-party catalogue's silence — the precise thing Phase 211 built the column for ("Three model-generated refuters do not make a service manual"). The other three vocabulary values are worse: forum would force a fabricated "Forum tip:" (tests/test_phase239_european_parts.py:242-244), and unverified sits inside FORUM_DERIVED in tests/test_phase78_gate2_integration.py, so it would be held to the same tip rule. model-generated is the only honest label available.

7. The fix's own model is a misreading: the Aprilia charging entry does not explain a provenance label, it hedges one specific claim inside a documented entry ("no Aprilia document states that threshold"). And the "reader filtering for documented information" harm is not specific to these two — the same filter drops the forum-labelled BMW final-drive negative finding in the same file, and the Ducati discontinuation is not lost to that reader anyway: it is carried as service-manual rows in parts.json.

**Verifier's corrected_fix.**

No relabelling. Promoting either entry to service-manual would silence the Phase 211 CLI warning on vendor-derived and inference-from-silence content and would contradict the same phase's own parts.json grading. If the team wants to close the (real but minor) legibility gap that let this finding be written, the correct step is documentation, not data: record in docs/phases/completed/239_implementation.md the rule Phase 235 already states — a manufacturer document that states the claim is service-manual; an entry that rests on vendor documentation or on a cross-source inference is model-generated — and, if it should be enforced, add a test to tests/test_phase239_european_parts.py asserting that every service-manual entry in the file names a manufacturer document as its basis (all five say "read this phase" / "text-extracted and read" / "checked against the fiche") and that no model-generated entry claims one.


### [REJECTED] model-generated entries that claim in the same sentence to be drawn from KTM's own manuals, specifications and fitting sheets

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_ktm_electrical.json`

**Evidence.**

Three entries, all source = "model-generated", each self-contradicting in its opening clause: "General knowledge entry, drawn from KTM's published technical specifications, on the fact that decides everything downstream."; "General knowledge entry, drawn from KTM owner's and repair manuals, on why a KTM owner cannot tell you the code."; "General knowledge entry, drawn from KTM's own fitting sheets and warranty terms, on what PowerParts means to a shop." The second goes on to quote manual content at specification level: "KTM's repair manuals tabulate that blink code against the stored P-code one to one... the TPS signal-low and signal-high faults both blink 06." A fourth entry in the file ("A generic scanner's label for a P1xxx code on a KTM is not the fault") is labelled "General knowledge entry" and then cites "the 990's repair manual lists P1105 and P1106 for the front and rear manifold-pressure hoses... P1590 for the side-stand switch".

**Auditor's recommended fix.**

Decide per entry. Where a KTM manual was genuinely opened, promote to service-manual and drop "General knowledge entry". Where it was not, delete the "drawn from KTM's ..." clause so the entry stops claiming a document it does not have. Note that known_issues_ktm_adventure.json already labels manual-derived KTM content service-manual ("Drawn verbatim from KTM's owner's manual"), so the corpus has an established convention this file departs from.

**Verifier verdict — real=False.**

The quotes reproduce verbatim, but the rule the finding measures them against is not this corpus's rule, and the file breaks nothing.

WHAT REPRODUCES. In /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_ktm_electrical.json all 7 entries are source="model-generated", and entries 0, 2 and 6 open exactly as quoted ("General knowledge entry, drawn from KTM's published technical specifications, ...", "... drawn from KTM owner's and repair manuals, ...", "... drawn from KTM's own fitting sheets and warranty terms, ..."), entry 2 does say "KTM's repair manuals tabulate that blink code against the stored P-code one to one" and "the TPS signal-low and signal-high faults both blink 06", and entry 3 does list "P1105 and P1106 ... P1590 for the side-stand switch". A fourth "drawn from" clause the finding does not mention is in entry 1 ("drawn from the tools' own published model lists").

WHY THE FINDING FAILS. Its premise is "model-generated entries should not claim to be drawn from a manufacturer document — that is the whole point of the label." The corpus says otherwise, repeatedly and deliberately. 15 entries whose source is "model-generated" open with "Drawn from <a named published source>", across five Track K files: known_issues_european_tooling.json (5), known_issues_aprilia_mv_electrical.json (4), known_issues_european_differentials.json (3), known_issues_european_parts.json (2), known_issues_european_intervals.json (1). Two are stronger claims than anything in the KTM file: european_intervals, source model-generated, opens "Drawn from manufacturer manuals where they describe the method, and labelled where they do not"; aprilia_mv_electrical, source model-generated, opens "Drawn from a 2012 manufacturer press release and from the tool vendor's own release documentation." And tests/test_phase238_european_intervals.py:36-45 asserts BOTH that every entry says what it is drawn from AND that sources are {"service-manual", "model-generated"} — i.e. "drawn from a document" + model-generated is a tested, intended combination, not a contradiction.

The second half is the same story. "Specific, checkable manufacturer content filed under model-generated" is an established pattern, not a defect: known_issues_aprilia_mv_electrical.json, source model-generated, prints MV's whole manufacturer-specific code block ("P1120, P1122, P1220, P1223, a P1300 series, P1602, P1610, P1612, P1655 and P1773 ... U1602 and U1700"), which is exactly parallel to entry 3's P1105/P1106/P1590 and entry 2's blink-06 mapping.

Nor is "General knowledge entry" + a source clause two labels at once. tests/test_phase228_triumph_triples.py:158-161 REQUIRES model-generated entries to start with "General knowledge"; :153-156 requires service-manual entries to say "Drawn from". The KTM entries carry the model-generated marker and additionally name where the underlying facts are published — the label is stated once, conservatively, and the reader is not left guessing: src/motodiag/cli/kb.py:243-249 prints, for every one of these entries, "⚠ Written from general knowledge, not a service manual. Confirm figures and procedure against the manual for this bike before relying on them." What the corpus actually forbids an unsourced entry to carry is a recall number, a publication number or an interval figure (tests/test_phase228_triumph_triples.py:83-88, 142-151); I ran that SOURCED_ONLY regex over known_issues_ktm_electrical.json and it returns zero hits.

The file also passes its own phase test today: tests/test_phase225_ktm_electrical.py, 45 passed.

THE FIX WOULD BREAK THE TREE. Either half of "promote to service-manual and drop 'General knowledge entry'" fails tests/test_phase225_ktm_electrical.py:350-351 (`assert {r["source"] for r in rows} == {"model-generated"}`) and :353-355 (`assert "general knowledge" in e["description"].lower()`). Promoting also silences the kb.py caution above for content Phase 225 deliberately did not certify — and ROADMAP.md row 225 records that phase as researched but shipped model-generated, with service-manual first used one phase later (row 226: "First phase whose entries are not `model-generated`"), which explains the difference from known_issues_ktm_adventure.json (Phase 225B) rather than making it a departure.

At most this is a prose-style inconsistency: the fused form "General knowledge entry, drawn from X" appears only in this one file (4 times), where later files use a bare "Drawn from X". That is cosmetic, violates no Track K decision, and is not a medium-severity content defect.

**Verifier's corrected_fix.**

None — no change should be made. Do not re-label any entry in known_issues_ktm_electrical.json: source values there are pinned by tests/test_phase225_ktm_electrical.py:350-351 and the "general knowledge" opening by :353-355, and promoting to service-manual would suppress the kb.py:243-249 provenance warning for content Phase 225 chose not to certify. If a later phase ever wants the four "drawn from" clauses harmonised with the bare "Drawn from" form used in the 235-239 cross-make files, that is a cosmetic edit that must (a) cover entry 1's "drawn from the tools' own published model lists" as well as the three naming KTM, and (b) keep both the "General knowledge" marker and source="model-generated" intact so the two pinned assertions still hold.


### [REJECTED] model-generated entry opening "Drawn from manufacturer manuals" in a file whose other 12 entries are service-manual

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_intervals.json`

**Evidence.**

Title: "Five valve-train job types across the European makes, and the step each has that the others lack". source = "model-generated". Opening sentence: "Drawn from manufacturer manuals where they describe the method, and labelled where they do not." The body then attributes specific manual content — "Moto Guzzi V85 TT by its service manual", "Moto Guzzi V100 by its service manual", "MV Agusta (the manual names an adjustment pad under the valve cup and sends replacement to the engine manual)" — while correctly marking the unsupported parts ("KTM and the S1000RR by owner report, no manufacturer page opened").

**Auditor's recommended fix.**

Either promote to service-manual (the per-make attributions and the explicit labelling of the two gaps make it as well-evidenced as its neighbours), or add one sentence saying the lower source reflects that this row is a cross-make synthesis rather than a single document reading.

**Verifier verdict — real=False.**

The surface facts reproduce, but the finding's actual claim — "the description does not say that is the reason; it says the opposite" — is produced by truncating the sentence at a comma, and both proposed fixes are wrong.

1. THE QUOTE IS CUT MID-SENTENCE. The auditor renders the opening as "Drawn from manufacturer manuals where they describe the method, and labelled where they do not," then argues it "says the opposite" of caution. The second clause IS the caution. The full sentence says provenance is mixed: manual where a manual exists, labelled where it does not. The body then does exactly that, three times — "KTM and the S1000RR by owner report, no manufacturer page opened", "the air/oil-cooled BMW boxer by owner report", "the liquid-cooled BMW boxer by owner report" — and fix_procedure repeats it: "Note which job types here rest on owner reports rather than a manufacturer page — the BMW boxers and KTM — and confirm on the machine." The caveat the fix asks to add is already the entry's first sentence and its last.

2. "DRAWN FROM" IS THE FILE'S CONVENTION, NOT THIS ENTRY'S CLAIM. All 13 entries open with a "Drawn from" sentence, enforced by tests/test_phase238_european_intervals.py::test_every_entry_says_what_it_is_drawn_from (regex `[Dd]rawn\b[\w' ]{0,16}\bfrom`). So opening that way carries no provenance boast; it is required.

3. THE ENTRY IS THE ONLY ONE IN THE FILE THAT NAMES NO DOCUMENT — which is precisely why it ranks lower, contradicting "as well-evidenced as its neighbours". The other twelve each name a specific document: "Ducati's Transparent Maintenance poster"; "KTM's own service-times sheet, dated October 2019"; "a Triumph Designs service check sheet and seven Triumph handbooks"; "the Turismo Veloce 800 user's manual MY2018–20"; "the MV Agusta Brutale ORO/S workshop manual"; "the V85 TT and V100 Mandello service manuals"; "eleven KTM owner's manuals"; "five BMW Rider's Manuals". Entry 4 says only "manufacturer manuals", generically. Its per-make attributions ("Moto Guzzi V85 TT by its service manual") point at documents read by *other* entries — it is a cross-reference, not a document reading of its own. Note entry 10 is service-manual while also carrying owner reports ("plus owner reports labelled as such") — because it names a workshop manual. Entry 4 names none. The distinction the file draws is document-named vs not, and entry 4 falls on the correct side of it.

4. FIX OPTION 1 (promote to service-manual) BREAKS AN IN-TREE TEST AND LAUNDERS OWNER REPORTS. tests/test_phase238_european_intervals.py:139-142 pins it: `e = next(x for x in raw if "job types" in x["title"]); assert re.search(r"by owner report", text); assert e["source"] == "model-generated"`. I applied the fix to a scratchpad copy of the tree (repo untouched) and ran pytest: 25 passed, 1 failed — `AssertionError: assert 'service-manual' == 'model-generated'`. Unpatched, the file is 26/26 green. Beyond the test, promoting it would assert manual provenance over three claims the entry itself says have none ("no manufacturer page opened") — the exact failure Phase 233 guarded against for the MV crank rotation.

5. THE LABEL IS A RECORDED PHASE DECISION. docs/ROADMAP.md row 238 states the design: "**five job types** with provenance labelled where the method rests on owner reports."

6. NO RULE IS VIOLATED. "model-generated" is in the six-value vocabulary; the entry carries no "Forum tip:" (correct, since it is not forum); it prints no interval figures, no campaign numbers, and none of the six deliberate absences.

The residual observation — one model-generated row among twelve service-manual — is a difference of scope (a cross-make synthesis vs single-document readings), correctly signalled in the prose, pinned by a test, and recorded in the roadmap. There is nothing to fix.


### [CONFIRMED] known_issues_triumph_vintage.json labels all 13 entries service-manual while several rest on period road tests, marque-club guidance and specialist-supplier literature

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_triumph_vintage.json`

**Evidence.**

"Drawn from **period road tests** and marque documentation." (oil-in-frame entry). "Drawn from specialist supplier and **marque club** documentation." (no oil filter entry, which also says "marque club guidance covers retrofitting an external one"). "Drawn from British thread-standard references and **specialist supplier** documentation." (British threads entry). "Drawn from the manufacturer's launch material and **period technical reporting**." (badge-is-not-capacity entry). "Drawn from marque and ignition-manufacturer sources." (vibration entry — "marque sources" is not resolved to anything). For contrast, two entries in the same file rest on genuine component-maker documentation: "Drawn from the carburettor manufacturer's own documentation." (Amal pilot screw) and "Drawn from specialist supplier and ignition manufacturer documentation." (positive earth).

**Auditor's recommended fix.**

Re-source the four or five entries that name journalism, clubs or retailers as their base. "There is no oil filter to change on a Meriden twin" and "On an oil-in-frame Triumph the frame is the oil tank" are the two clearest demotions. "Drawn from marque and ignition-manufacturer sources" should also name what a "marque source" is.

**Verifier verdict — real=True.**

Reproduced independently, though the finding is broader than the evidence supports.

FACTS CONFIRMED. All seven quoted "Drawn from" sentences are verbatim in /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_triumph_vintage.json, and all 13 entries carry "source": "service-manual" (lines 32, 63, 94, 125, 155, 187, 218, 248, 278, 308, 338, 369, 398). The "Drawn from" sentence is not decoration: tests/test_phase229_triumph_vintage.py::test_every_entry_says_what_it_is_drawn_from pins it, so it is the file's own provenance declaration — and in two entries that declaration and the label disagree.

WHY IT IS A REAL DEFECT, NOT A SCOPE DIFFERENCE. The project's own definitions: migrations.py:3535 records `service-manual` as "primary official document"; src/motodiag/cli/kb.py:215 introduces VERIFIED_SOURCES as "Sources a mechanic can act on without a second opinion" and _render_provenance returns silently for it, so these entries print with no caution. Phase 227's implementation.md:60 states the convention — "entries resting on Triumph publications or regulator recall records are `service-manual`, entries resting on owner reports are `forum`". Phase 226 justified the coarse bucket only for regulator recall records, a source at least as authoritative as a manual; a marque club and a retailer are not that.

THE OUTLIER IS REAL. I dumped the "Drawn from" sentence of every `service-manual` entry corpus-wide (108 entries). Every other one resolves to a manufacturer document, a parts fiche, a regulator record, or a tool/component vendor's own published material, and where owner reporting contributes the entries quarantine it explicitly ("plus owner reports for the failure pattern"; "together with owner-reported patterns, and the distinction between the two is stated"; known_issues_aprilia_rsv4.json even pairs "specialist supplier and owner reporting" with "the machines' service documentation" and states the distinction). known_issues_triumph_vintage.json is the only file in the track where the declared base is journalism, an enthusiast club, or a retailer with no primary document named alongside.

WHERE THE AUDITOR OVERREACHES. "13 of 13 carry the strongest label" is the phase's recorded outcome (229_implementation.md Results: "Entries | 13, all `service-manual`"), not itself the defect, and three of the five entries it names do cite a primary document as part of their base: "British thread-standard references" are standards documents (BS Whitworth/BSF/Cycle) and are authoritative on thread form and pitch; "the manufacturer's launch material" is a Triumph document and is what carries the 885/1180 capacities; the vibration entry's one actionable instruction (secure the stator-plate wiring) comes from the ignition manufacturer's fitting instructions. Only two entries declare a base containing no primary document at all — which is the auditor's own pick of the two clearest.

**Verifier's corrected_fix.**

Trim the scope to two entries, name the target value the auditor left blank, and price the collateral it did not check.

WHAT ACTUALLY MOVES (2 entries, not "four or five"):
- "There is no oil filter to change on a Meriden twin" (line 97) — "Drawn from specialist supplier and marque club documentation", with "marque club guidance covers retrofitting an external one". No primary document named anywhere.
- "On an oil-in-frame Triumph the frame is the oil tank" (line 66) — "Drawn from period road tests and marque documentation", journalism named first and "marque documentation" unresolved.
Leave the British-threads, badge-is-not-capacity and vibration entries at `service-manual`: each names a standards reference, a manufacturer document or a component-maker document that underwrites its load-bearing claim.

THE FIX THE AUDITOR DID NOT SPECIFY — demote to WHAT. All six values are wrong in some direction and the fix must choose knowingly: `model-generated` is false (these were researched); `unverified` is false in the opposite direction (the origin IS recorded) and renders "Origin not recorded" over a sourced entry — precisely the false-render regression Phase 235B fought for `regulation`; `forum` is the closest honest bucket for marque-club consensus and retailer literature, and is what 227's convention implies, but note it renders the same "Origin not recorded" line via the else branch in kb.py:250. Preferred: `forum` for the no-oil-filter entry, and for the oil-in-frame entry either `forum` or a prose repair that resolves "marque documentation" to the actual document if one was read — it must not be repaired by naming a Meriden factory manual that was not opened, which is the fabrication 226 warns about.

COLLATERAL THE FIX BREAKS (the auditor checked none of it):
1. tests/test_phase229_triumph_vintage.py:304-305 asserts `{e["source"] for e in raw} == {"service-manual"}` — an equality pin that fails on any demotion. It must become a membership assertion (`<= {"service-manual", "forum"}`) with the reason recorded, not simply deleted.
2. Gate 2 (tests/test_phase78_gate2_integration.py:141) puts `forum` in FORUM_DERIVED, where >=90% must carry "Forum tip:" in fix_procedure. Two untipped `forum` entries already exist corpus-wide (mv_agusta_triple, triumph_bonneville) and 2 more against a 677-entry pool stays inside the slack, so the ratio holds — but tests/test_phase229_triumph_vintage.py:311 forbids any "Forum tip" in this file, so the demotion must be accepted untipped rather than "fixed" by adding a tip, which would fabricate a forum thread that does not exist.
3. docs/phases/completed/229_implementation.md goes stale in two places: the Results row "Entries | 13, all `service-manual`" and the checklist line "Provenance per entry; `service-manual` entries say what they are drawn from". ROADMAP row 372 does not state the count and needs no edit.

PROSE FIX, WIDER THAN PROPOSED. "Marque sources" / "marque documentation" is unresolved in three places, not one: the vibration entry (line 191, "Drawn from marque and ignition-manufacturer sources"), the wasted-spark entry (line 129, "and marque sources"), and the Hinckley-metric entry (line 373, "Drawn from marque documentation") — which the auditor missed entirely. Each should name the document class, since "marque" currently spans factory literature and an owners' club without distinguishing them, and that ambiguity is what lets the label pass unexamined.


---

## Dimension: guards

**Auditor summary.** Ran all 31 Track K test files (1005 passed) plus a per-test coverage pass (coverage.py with dynamic_context=test_function) to cluster tests by SHAPE rather than name, then verified every cluster against the live corpus. Found 11 latent guard families beyond the designation-bar one, 3 proven-vacuous tests, 6 dead discriminators, and one live corpus violation of Phase 231/Gate-2 decision #3 that Gate 12 cannot see. Headline: two European entries carry source="forum" with no "Forum tip:" in fix_procedure (known_issues_triumph_bonneville.json, known_issues_mv_agusta_triple.json). They survive because the forum-tip guard was copied into 14 files under 8 names, and 10 of the copies assert only the negative half — in the two files that actually contain a forum entry, the copy asserts the OPPOSITE of the rule. Gate 2's positive half is a 90% ratio over 677 rows (675 compliant), so 67 more violations could land before it trips, and Gate 12 has no forum-tip test at all and does not run Gate 2. Second-largest: 8 hardcoded cumulative make-totals in the BMW and Ducati blocks (== 24/30/41/44/22/30/36/41 plus "len(files) == 5") — the exact constant-for-invariant bug; the KTM and Triumph blocks fixed the same tests by computing the expected total from the glob, and KTM has already grown from 5 files to 6 without breaking. Also: the campaign-number ban exists in 8 file-local copies with three mutually-incompatible regexes, and Gate 12's corpus-wide sweep uses the one variant that CANNOT match the shape of the original Citroen incident (\d{2}V\d{3} and RM/\d{4}/\d+); the "earns its shadow" DTC guard has no member for Aprilia or MV Agusta; and the 2025 KTM 390 build-location absence has no test guarding it anywhere (the content is correct, nothing holds it there).


### [CONFIRMED] FAMILY 1 (worst): forum-tip contract copied 14 times under 8 names; 10 copies assert only the negative half, and 2 of those actively enforce the violation — 2 live violations in the shipped corpus

- **severity (auditor):** critical
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_triumph_bonneville.json`

**Evidence.**

Decision #3: source==forum MUST carry "Forum tip:" in fix_procedure; any other source MUST NOT. Live violations (both source="forum", no "Forum tip" anywhere in fix_procedure):
  1. known_issues_triumph_bonneville.json — "Air-cooled Bonneville starter and wheel faults that never got a recall — the idler-gear boss, the sprag clutch and left-hand rear spokes"
  2. known_issues_mv_agusta_triple.json — "The MV triple's starter clutch is handed for reverse rotation — and is reported to have been fitted backwards"
Corpus scan of the 30 European files: 17 forum entries, exactly these 2 non-compliant.

FAMILY MEMBERS (INVARIANT in intent; the negative-only copies are the defect).
Correct, biconditional (3):
  tests/test_phase225b_ktm_adventure.py::test_forum_entries_carry_a_forum_tip (l.62) + ::test_non_forum_entries_do_not_claim_one (l.69)
  tests/test_phase237_european_differentials.py::test_forum_entries_carry_a_tip_and_others_do_not (l.60-63, `has == (e["source"]=="forum")`)
  tests/test_phase239_european_parts.py::test_forum_tips_only_on_forum_entries (l.259-261, same shape)
Negative half only (10):
  tests/test_phase226_triumph_bonneville.py::test_no_entry_fabricates_a_forum_tip (l.184-187)  <-- file HAS a forum entry; this test DEMANDS it not carry a tip
  tests/test_phase233_mv_agusta_triple.py::test_provenance_is_recorded_per_entry (l.255-259)   <-- file HAS a forum entry; same inversion
  tests/test_phase227_triumph_tiger.py::test_no_entry_fabricates_a_forum_tip (l.173-175)
  tests/test_phase228_triumph_triples.py::test_no_entry_fabricates_a_forum_tip (l.163-165)
  tests/test_phase229_triumph_vintage.py::test_no_entry_fabricates_a_forum_tip (l.311-313)
  tests/test_phase231_aprilia_rsv4.py::test_no_entry_fabricates_a_forum_tip (l.242-244)
  tests/test_phase234_mv_agusta_four.py::test_provenance_and_symptom_format (l.222-226)
  tests/test_phase235_aprilia_mv_electrical.py::test_no_entry_claims_a_forum_tip (l.97-102)
  tests/test_phase236_european_tooling.py::test_no_forum_tips_claimed (l.57-58)
  tests/test_phase238_european_intervals.py::test_no_forum_entries_here (l.41-46)

WHY THE GATES MISS IT — quantified:
  tests/test_phase78_gate2_integration.py::test_forum_tips_present (l.114-155) is the only positive half in the tree and it is a RATIO: `assert issues_with_tips >= len(forum_sourced) * 0.9`. Measured at runtime: forum-derived population (source in {unverified, forum}) = 677, with tip = 675, ratio 0.9970, threshold 0.9. 67 MORE violations could be added before Gate 2 fails.
  Gate 12 (scratchpad/test_phase240_gate12.py) has NO forum-tip assertion at all, and its regression list (l.279-286) does not include tests/test_phase78_gate2_integration.py.
Each of 226 and 233 was copied from a sibling whose file happened to be 100% service-manual; nobody re-derived the rule when a forum entry was added to the file.

**Auditor's recommended fix.**

Add "Forum tip:" to the fix_procedure of the two entries above (both already say "forum consensus"/"commonly reported" in prose, so the tip is the only missing piece). Then rewrite all 10 negative-only copies to the biconditional shape used at 237:60-63 / 239:259-261 — `assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum")` — which is an invariant that survives a file gaining or losing forum entries. Add that same biconditional as a corpus-wide sweep in Gate 12's TestTrackKCorpusInvariants, and replace Gate 2's 0.9 ratio with an absolute `== len(forum_sourced)` scoped to source=="forum" (keep the ratio only for the legacy `unverified` population if the legacy rows genuinely cannot all be fixed).

**Verifier verdict — real=True.**

Reproduced against the files, not the write-up.

LIVE DATA VIOLATIONS — confirmed, exactly 2. Scanning the 30 European files: 257 entries, 17 with source=="forum", and precisely two lack "Forum tip" anywhere in fix_procedure:
  1. known_issues_triumph_bonneville.json — "Air-cooled Bonneville starter and wheel faults that never got a recall…" source "forum"; its fix_procedure runs "1. Treat these as inspection items… 5. Do not quote these as warranty or recall work." with no tip. Its description does say "Drawn from owner-forum consensus".
  2. known_issues_mv_agusta_triple.json — "The MV triple's starter clutch is handed for reverse rotation…" source "forum"; fix_procedure "1. Test the battery properly… 5. Record the battery test result on the job card." no tip. Description: "Drawn from owner-forum reporting".
Corpus-wide (all 92 files, 917 entries): source counts {unverified 660, model-generated 131, service-manual 108, forum 17, regulation 1}; entries missing a tip = all 108 service-manual, all 131 model-generated, 1 regulation, and exactly those 2 forum rows. All 660 legacy `unverified` rows carry a tip.

THE TWO INVERTED TESTS — confirmed, and they do actively enforce the bad data.
  tests/test_phase226_triumph_bonneville.py:184-187 `test_no_entry_fabricates_a_forum_tip` — docstring "Gate 2's other half, asserted locally too." — iterates the `raw` fixture, which is the whole file (l.135-136 `json.loads(BONNIE.read_text(...))`), asserting `"Forum tip" not in e["fix_procedure"]` for every entry. The same file's l.165-166 asserts sources ⊆ {service-manual, forum} and l.189-193 asserts `len(forum) == 1`. So the file knowingly contains a forum entry and simultaneously forbids it a tip.
  tests/test_phase233_mv_agusta_triple.py:255-259 `test_provenance_is_recorded_per_entry` — `assert {e["source"] for e in raw} <= {"service-manual", "forum"}` on one line and `assert "Forum tip" not in e["fix_procedure"]` on the next. Same inversion.
Applying the data fix breaks both — that is logically forced by the fixture scope, and I confirmed both files currently pass green (97 passed: 226, 233 and Gate 2 all pass with the bad data in place).

GATE 2 RATIO — confirmed to the digit. tests/test_phase78_gate2_integration.py:143-155: FORUM_DERIVED = {"unverified","forum"}, `assert issues_with_tips >= len(forum_sourced) * 0.9`. Measured: 677 forum-derived, 675 with tips, ratio 0.9970, threshold 609.3 — 65 further violations (auditor said 67; harmless arithmetic slip) before it trips.

GATE 12 — confirmed. The staged /private/tmp/.../scratchpad/test_phase240_gate12.py mentions "forum" exactly once, at l.261, and only as a member of the six-value vocabulary set. TestTrackKCorpusInvariants has no forum-tip assertion. Its regression parametrize (l.279-285) lists gates 5,6,7,8,9,11 and not test_phase78_gate2_integration.py; I also grepped those six gate files and none of them invokes phase78 transitively. So the track closes without decision #3 ever being evaluated.

Also checked for reasons the fix might break something else: no test in 226 or 233 constrains fix_procedure beyond `.strip()` truthiness (226:151, 233:83), there is no exact-count assertion on "Forum tip" anywhere, and compliant siblings (european_parts, european_differentials, ktm_adventure) all append the tip as a trailing "Forum tip: owners report/note …" sentence, so the fix has a house style to copy.

Scope correction, not a refutation: the "10 negative-only copies" figure overstates the latent risk. Eight of the ten are paired with an exhaustive source-vocabulary pin that would fail loudly the moment a forum entry entered the file — 227:160, 229:305, 231:236 and 234:222 all assert `{e["source"] for e in raw} == {"service-manual"}`; 228:139-140 asserts `== {"model-generated","service-manual"}`; 236:57-58 and 238:41-46 assert the source subset excluding forum inside the very same test as the no-tip line; 235's pin sits in the sibling test at l.94-95. Only 226 and 233 are genuinely defective, because only those two files actually contain a forum entry. That changes the family's shape (2 defects + 8 stylistic cleanups, not 10 holes) but not the finding's severity: the two live violations, the two inverted tests, and the Gate 2/Gate 12 blind spot are all real.

**Verifier's corrected_fix.**

Data (the actual defect), 2 edits:
1. known_issues_triumph_bonneville.json, entry "Air-cooled Bonneville starter and wheel faults that never got a recall…": append a final sentence to fix_procedure in the house style, e.g. "Forum tip: owners report checking spoke tension at every tyre change on early wire-wheeled bikes, because that is when the wheel is already off." Do NOT let the added sentence introduce a campaign or recall reference number (Phase 231) or the Triumph pre-Euro-5 connector transition year (deliberate absence #2).
2. known_issues_mv_agusta_triple.json, entry "The MV triple's starter clutch is handed for reverse rotation…": append e.g. "Forum tip: owners report load-testing the battery before condemning the starter clutch, because a weak battery is the cause they most often name." The tip must NOT state the crank rotation direction — Phase 233 deliberately withholds it, and the file's own header says so.

Tests — required, or the data fix goes red:
3. tests/test_phase226_triumph_bonneville.py:184-187 and tests/test_phase233_mv_agusta_triple.py:255-259 must be rewritten to the biconditional already used at 237:60-63 / 239:259-261: `assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum"), e["title"]`. In 233 keep the source-vocabulary line that shares the test. These two are mandatory; without them the corpus fix fails CI.

4. The other eight negative-only copies (227:173-175, 228:163-165, 229:311-313, 231:242-244, 234:222-226, 235:97-102, 236:57-58, 238:41-46) are OPTIONAL cleanups, not defects — each is already backstopped by an exhaustive `{e["source"] for e in raw} == {...}` / `<= {...}` pin that excludes "forum", so a future forum entry cannot slip past them silently. If you convert them to the biconditional anyway, KEEP the source-vocabulary pin: it is the thing that currently makes them safe, and dropping it while adding the biconditional is a net loss of coverage for a file that is meant to hold no forum rows at all.

Gates — this is the part that stops the recurrence:
5. Add a corpus-wide sweep to Gate 12's TestTrackKCorpusInvariants over all `K.glob("known_issues_*.json")` (not just the 30 European files — the rule is corpus-wide and the legacy rows already satisfy it): `assert ("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum")` for every entry with an explicit non-legacy source, i.e. skip only rows whose source is the legacy `unverified` default, which is a tip-carrying population by convention rather than by the source=="forum" rule. Concretely: for e where source in {"forum"} require a tip; for source in {"model-generated","service-manual","mechanic-verified","regulation"} forbid one. That is 258 rows today and passes once (1) and (2) land.
6. Add tests/test_phase78_gate2_integration.py to Gate 12's regression parametrize list at l.279-285. Right now no gate in that list reaches it, so Gate 2's forum-tip assertion is never exercised by the closing gate.
7. Tighten Gate 2's ratio — and drop the auditor's hedge, which my measurement makes unnecessary. All 660 legacy `unverified` rows already carry a tip, so after (1) and (2) the whole FORUM_DERIVED population is 677/677. Replace `>= len(forum_sourced) * 0.9` with `== len(forum_sourced)` over the existing {"unverified","forum"} population directly; no separate scoping to source=="forum" and no ratio kept for the legacy rows is needed. Land this only after (1) and (2), or Gate 2 goes red on the two known rows.


### [CONFIRMED] FAMILY 2: cumulative make-total pins — 8 members, 4 names, all CONSTANT. The BMW and Ducati blocks were never given the fix the KTM and Triumph blocks got

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/tests/test_phase215_bmw_electrical.py`

**Evidence.**

Same shape everywhere: load a make's files into a temp db, assert a hardcoded total.
CONSTANT members (break on any added entry or file):
  tests/test_phase212_bmw_gs_adventure.py::test_both_bmw_files_load_together (l.179-185) — `== 24` twice
  tests/test_phase213_bmw_s1000.py::test_they_load_together (l.198-204) — `== 30` twice
  tests/test_phase214_bmw_k_series.py::test_they_load_together (l.213-219) — `== 41` twice
  tests/test_phase215_bmw_electrical.py::test_all_five_bmw_files_load_together (l.256-263) — `assert len(files) == 5` on a glob AND `== 44`
  tests/test_phase217_ducati_panigale.py::test_they_load_together (l.186-192) — `== 22` twice
  tests/test_phase218_ducati_multistrada.py::test_they_load_together (l.218-224) — `== 30` twice
  tests/test_phase219_ducati_desmo.py::test_they_load_together (l.216-222) — `== 36` twice
  tests/test_phase220_ducati_electrical.py::test_all_five_files_load_together (l.194-200) — `== 41` twice
INVARIANT members (the fixed form, same family):
  tests/test_phase225_ktm_electrical.py::test_all_five_ktm_files_load_together (l.308-317) — accumulates `expected` from the glob
  tests/test_phase230_triumph_electrical.py::test_all_five_triumph_files_load_together (l.333-342) — same
Proof the fix matters: KTM_FILES = sorted(K.glob("known_issues_ktm_*.json")) now returns SIX files (Phase 225B added known_issues_ktm_adventure.json). The KTM test survived that growth untouched; its name is merely stale. Had it been written the BMW way it would have failed at 225B. Live counts today: bmw 5 files/44 entries, ducati 5/41, ktm 6/38, triumph 5/51.

**Auditor's recommended fix.**

Port the 225/230 form into all eight: glob the make's files, accumulate `expected += len(json.loads(f.read_text()))`, assert against `expected`. Replace `assert len(files) == 5` in 215 with `assert files` plus the specific coverage assertions that actually matter (each of R/F/S/K/electrical present by name). Rename 225's test off 'five' while you are there — the name is now wrong by one.

**Verifier verdict — real=True.**

Independently reproduced, line for line. All eight constant members exist exactly as described: test_phase212_bmw_gs_adventure.py:184-185 (`count_known_issues(db_path=path) == 24` / `search_known_issues(make="BMW"...) == 24`), 213:203-204 (==30), 214:218-219 (==41), 215:259 `assert len(files) == 5, [f.name for f in files]` followed at :263 by `== 44`, 217:191-192 (==22), 218:223-224 (==30), 219:221-222 (==36), 220:199-200 (==41). The two invariant members are exactly as quoted: 225:308-317 and 230:333-342 both build `expected = 0` then `expected += len(json.loads(f.read_text(encoding="utf-8")))` over a glob-derived file list. The counterfactual holds: KTM_FILES = sorted(K.glob("known_issues_ktm_*.json")) at 225:64 now returns six files, and docs/ROADMAP.md:361 records Phase 225B (closed 2026-09-08) adding known_issues_ktm_adventure.json with 10 entries after Phase 225 shipped — a pinned 28 would have failed there, and the glob form absorbed it untouched. Live counts verified from the JSON: bmw 5 files/44 entries, ducati 5/41, ktm 6/38, triumph 5/51 — matching the finding. The staged Gate 12 test corroborates the house style: it derives its total from a glob (`live = sum(len(json.loads(f.read_text(...))) for f in K.glob("known_issues_*.json"))`) and pins no per-make count. Two precision notes that do not defeat the finding: (a) "break on any added entry or file" is only fully true of 215 — 212/213/214/217/218/219/220 load explicit file constants, so a NEW bmw_/ducati_ file slips past them silently (a coverage hole in its own right) and only an added ENTRY in a named file breaks them; (b) nothing fails today — all 300 tests in the ten files pass — so the cost is hand-editing by a later phase, which argues medium rather than high severity. The defect itself is real and the asymmetry between the two blocks is exactly as described.

**Verifier's corrected_fix.**

Port the invariant form, but not by globbing in all eight, and not by copying 225/230 verbatim — the template has a latent bug.

1. Keep each test's SCOPE; only remove the magic number. 212, 213, 214, 217, 218, 219 are phase-scoped coexistence tests ("both BMW files", TestAllThreeDucatiFilesCoexist, TestAllFourBmwFilesCoexist). Globbing the make would turn all six into duplicates of the block test and falsify their own class names. Accumulate over the file tuple each test ALREADY has: for 212 `(R_FILE, F_FILE)`, 213 `(R_FILE, F_FILE, S_FILE)`, 214/218/219 their existing `_FILES`, 217 `(M_FILE, P_FILE)`. Only the two block tests — 215::test_all_five_bmw_files_load_together and 220::test_all_five_files_load_together — should glob, matching 225/230. Note 220 currently uses an explicit five-name list, so it is not a block test at all today; make it glob `known_issues_ducati_*.json` if it is to keep its name.

2. Do NOT assert `search_known_issues(make=X) == expected` where expected is the sum of file lengths. The make filter is substring, not exact: src/motodiag/knowledge/issues_repo.py:84-86 builds `AND make LIKE ?` with `f"%{make}%"`. Sum-of-lengths equals the make-filtered count only while every entry in the globbed files carries that make verbatim, and this corpus already breaks that: known_issues_aprilia_mv_electrical.json holds makes "Aprilia and MV Agusta" (3), "Aprilia" (3) and "MV Agusta" (2), so the aprilia glob is 21 entries but 19 make-matching. bmw/ducati/ktm/triumph are 44/44, 41/41, 38/38, 51/51 today, so the straight port passes — until one compound or cross-make entry lands in a make-prefixed file, at which point 225 and 230 fail too. Derive both numbers from the JSON:
    entries = [e for f in FILES for e in json.loads(f.read_text(encoding="utf-8"))]
    assert count_known_issues(db_path=path) == len(entries)
    assert len(search_known_issues(make="BMW", db_path=path)) == sum(1 for e in entries if "bmw" in e["make"].lower())
Apply this to 225 and 230 as well — they are the template everyone will copy.

3. Replace 215's `assert len(files) == 5` with `assert files` plus a named-subset coverage assert, not an equality on count: `stems = {f.stem for f in files}; assert {"known_issues_bmw_r_series", "known_issues_bmw_f_series_gs", "known_issues_bmw_s1000", "known_issues_bmw_k_series", "known_issues_bmw_electrical"} <= stems`. Same for the Ducati block test once it globs (monster, panigale, multistrada, desmo, electrical). A subset assert keeps the coverage guarantee the count was standing in for while staying open to growth.

4. Rename off the count in all four block tests, not just 225: `test_all_five_ktm_files_load_together` is already wrong by one, and `test_all_five_bmw_files_load_together` (215), `test_all_five_files_load_together` (220) and 230's Triumph equivalent go stale by the same mechanism the moment a file is added. Use a count-free name such as `test_the_whole_bmw_block_loads_together`. 220 also has `test_no_title_collides_across_the_five_ducati_files` — same rename.

5. Do NOT sweep the single-file pins while you are in there. `len(json.loads(ELEC.read_text(...))) == 7` (225) and `== 5` (230), and the per-file counts at 212:70, 213:66, 214:74, 216:82, 217:81, 221:129, 222:139, 223:124, 224:133, 226:145, 227:114, 228:119, 229:138, 231:79, 232:79, 233:77, 234:73, are each a phase pinning the size of the file it owns. That is a content contract, not a cumulative pin, and it is the thing that makes an unannounced entry addition visible. Only the cross-file totals are the defect.

6. Optional, same family: there is no whole-block cohesion test for the Aprilia/MV Agusta block (231-234) at all. If one is added, point 2 is not hypothetical there — it is the live case.


### [CONFIRMED] FAMILY 3: campaign-reference-number ban — 8 file-local copies, 6 names, three mutually-incompatible regexes; Gate 12's corpus-wide sweep uses the variant that cannot match the original incident's shape

- **severity (auditor):** high
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py`

**Evidence.**

Phase 231 decision: no campaign/recall reference numbers anywhere in European content. Members and their regexes:
  Shape A `\b\d{2}V\d{3}\b` + `RM/\d{4}/\d+` (the actual Citroen-incident shape):
    tests/test_phase231_aprilia_rsv4.py::test_no_campaign_number_appears_at_all (l.114)
    tests/test_phase232_aprilia_dorsoduro.py::test_no_campaign_number_appears
    tests/test_phase233_mv_agusta_triple.py::test_no_campaign_number_appears
    tests/test_phase234_mv_agusta_four.py::test_no_campaign_number_appears
  Shape B `\b\d{2}V\d{6}\b` only:
    tests/test_phase237_european_differentials.py::test_no_campaign_reference_numbers (l.125-127)
    tests/test_phase238_european_intervals.py::test_no_campaign_numbers
    tests/test_phase239_european_parts.py::test_no_campaign_numbers_and_no_currency_figures (l.269-273) — and this one builds `text` from description+fix_procedure+causes, OMITTING title
  Shape C `\b\d{2}V\d{6}\b|\bRecall \d{6,7}\b`:
    tests/test_phase225b_ktm_adventure.py::test_no_campaign_reference_numbers_appear (l.52-57)
    scratchpad/test_phase240_gate12.py::test_no_campaign_reference_number_anywhere_in_track_k (l.245-255)
Shapes A and B cannot match each other: `\b\d{2}V\d{3}\b` fails on 23V456789 (no word boundary after 3 digits) and `\b\d{2}V\d{6}\b` fails on 23V456. `RM/2019/123` is checked in only 4 of 30 European files. Gate 12 — the only corpus-wide member — is shape C, so the exact form that caused the Phase 231 incident is invisible to it.
Separately, Gate 12 l.250 uses `K.glob("known_issues_{bmw,ducati,ktm,triumph,aprilia,mv,european}*.json")`. pathlib has no brace expansion; verified at runtime this returns []. The sweep works only because of the `or [...]` fallback (verified: fallback yields 30 files, misses none). Delete the `or` and the test becomes fully vacuous.
Corpus is clean today (0 matches for any shape), so nothing fails — the hole is entirely latent.

**Auditor's recommended fix.**

Define one union pattern — `\b\d{2}V[-\s]?\d{3,6}\b|RM/\d{4}/\d+|\bRecall\s*(No\.?|#)?\s*\d{5,7}\b` — and use it in Gate 12's corpus-wide sweep. Replace the brace glob with the explicit prefix comprehension (delete the dead `list(...) or` half so the fallback is the code, not the fallback). Have 239 scan title as well. The per-phase copies can then just re-import or duplicate the single pattern.

**Verifier verdict — real=True.**

Reproduced independently, with two corrections to the auditor's bookkeeping and one to its target file.

CONFIRMED — the fragmentation and the three shapes:
- Shape A (`\b\d{2}V\d{3}\b` + `RM/\d{4}/\d+`, both over `json.dumps(raw)`, i.e. all fields): tests/test_phase231_aprilia_rsv4.py::test_no_campaign_number_appears_at_all (def l.114, asserts l.120-121), tests/test_phase232_aprilia_dorsoduro.py::test_no_campaign_number_appears (l.156/160-161), tests/test_phase233_mv_agusta_triple.py::test_no_campaign_number_appears (l.125/127-128), tests/test_phase234_mv_agusta_four.py::test_no_campaign_number_appears (l.192/194-195).
- Shape B (`\b\d{2}V\d{6}\b` only): tests/test_phase237_european_differentials.py::test_no_campaign_reference_numbers (l.125-127), tests/test_phase238_european_intervals.py::test_no_campaign_numbers (l.150-152), tests/test_phase239_european_parts.py::test_no_campaign_numbers_and_no_currency_figures (l.269-273).
- Shape C: tests/test_phase225b_ktm_adventure.py::test_no_campaign_reference_numbers_appear and the gate.
Eight file-local copies under six distinct names — correct. 237 and 238 build `_claims` as `[title, description, fix_procedure] + causes`; 239 alone drops title (`text = " ".join([e["description"], e["fix_procedure"]] + e["causes"])`, l.270) — correct.

CONFIRMED — the regexes cannot substitute for each other. Executed: `\b\d{2}V\d{3}\b` on "23V456789" → no match; `\b\d{2}V\d{6}\b` on "23V456" → no match. `RM/\d{4}/\d+` is asserted unconditionally in only 4 of the 30 European files.

CONFIRMED — the incident shape is invisible to the gate. Phase 231's own docstring names it: "The research cited \"RM/2018/049\" for a brake master-cylinder campaign; in the UK dataset that number is a *Citroën* recall". Neither `\b\d{2}V\d{6}\b` nor `\bRecall \d{6,7}\b` matches `RM/2018/049`.

CONFIRMED — the brace glob is dead. Ran it: `K.glob("known_issues_{bmw,...}*.json")` → `[]`; the `or [...]` comprehension → 30 files, and that set is complete (the other 66 known_issues files are all Harley/Honda/Kawasaki/Suzuki/Yamaha/cross_platform; there is no Moto Guzzi file). Delete the `or` and the loop body never executes.

CONFIRMED — latent only. Scanned all 30 European files plus the 8 DTC files, adapters.json, compat_matrix.json, parts.json and parts_xref.json against all six shapes (A1, A2, B, C, and the tree gate's `R/\d{4}/\d{3}` and phrase pattern), case-insensitively, over raw file text: 0 hits for every one.

CORRECTIONS to the finding:
1. Wrong line cite: 225b's test is at l.173-179, not l.52-57 (l.52-57 is test_every_entry_says_what_it_is_drawn_from). The test itself is exactly as described.
2. A ninth member with a FOURTH shape was missed: tests/test_phase228_triumph_triples.py l.85-88 `SOURCED_ONLY = re.compile(r"\b\d{2}V\d{3}\b|\bSRAN\s?\d+|\bSB\d{3}\b|\bRM/\d{4}/\d+\b|...")`, applied at l.147-151 but only to entries whose source is "model-generated". Different scope (an unsourced-invention guard, not a corpus ban), so excluding it from the family is defensible — but it is a fourth spelling of the same vocabulary, and it means the "6 names / 3 shapes" count understates the drift.
3. MOST IMPORTANT — the finding's target file is a stale draft. `/Users/lilquant/Projects/moto-diag/tests/test_phase240_gate12.py` DOES exist in the tree (21101 bytes, mtime 22:40), is a later revision of the scratchpad copy (14207 bytes, mtime 22:08), and docs/phases/in_progress/ holds 240_implementation.md — Phase 240 is the in-progress phase, so the tree file is the live gate. It already replaced the brace glob with the explicit prefix comprehension and no `or` fallback, reads whole-file blobs (all fields), and extends to the DTC files, adapters.json and compat_matrix.json. It passes (ran it: exit 0, 46 tests). So the "load-bearing `or`" half of the finding is already fixed upstream of the file the auditor read.

The headline nevertheless survives against the live gate: its CAMPAIGN_PATTERNS are `\b\d{2}V\d{6}\b`, `\bRecall\s+\d{6,7}\b`, `\bR/\d{4}/\d{3}\b`, and a "recall number: X" phrase pattern. Verified `\bR/\d{4}/\d{3}\b` does NOT match "RM/2018/049" (R is followed by M, not /) though it does match "R/2018/049"; the phrase pattern needs the literal words in front; and nothing covers the short NHTSA form (`18V084`) that this track's own research files use. The corpus-wide gate still cannot see the Phase 231 incident's own string.

**Verifier's corrected_fix.**

Apply to the LIVE gate, /Users/lilquant/Projects/moto-diag/tests/test_phase240_gate12.py (not the scratchpad draft — its brace-glob/`or` defect is already gone there; only the pattern gap remains).

1. Do not use the auditor's union verbatim. `\b\d{2}V[-\s]?\d{3,6}\b` false-positives on voltage prose: it matches "12V 850" and "12V 1200". This corpus carries 213 digit+V voltage strings ("12V with key on", "22V AC per leg at 2000 RPM", "5V reference voltage"); zero match today, but the optional `[-\s]` separator makes the campaign gate fail the first time someone writes "12V 1200 mAh" or "12V 850 CCA". Drop the separator.

2. Keep the live gate's four patterns and widen them rather than replacing them — the tuple already encodes two hard-won lessons (mention-versus-use, the digit lookahead) that a flat union would discard. Concretely:
   - `r"\b\d{2}V\d{6}\b"` → `r"\b\d{2}V\d{3,6}\b"` (covers both the full 18V084000 and the abbreviated 18V084 form).
   - `r"\bR/\d{4}/\d{3}\b"` → `r"\b[A-Z]{1,3}/\d{4}/\d{1,4}\b"` (covers R/2018/049 AND the incident's own RM/2018/049, plus the Transport Canada / other-prefix variants the docstring anticipates). Verify against the corpus before landing — a broad `[A-Z]{1,3}/dddd/` could in principle collide with a date or part number; it returns 0 hits today across all 30 European files, the 8 DTC files, adapters, compat_matrix, parts and parts_xref.
   - Keep `\bRecall\s+\d{6,7}\b` and the phrase pattern as-is.
   The scan is already `re.I` over raw file text, which is right: the research files use lowercase (`17v772`) as well as uppercase.

3. If the patterns are consolidated into one alternation, make the "Recall No./#" group NON-capturing. The auditor's `\bRecall\s*(No\.?|#)?\s*\d{5,7}\b` has a capturing group; several call sites (225b l.177, 231 l.120, 237 l.127, 238 l.152, 239 l.272) use `re.findall`, which with a group returns the group text — so a real hit reports `['']` instead of the offending reference. Use `(?:No\.?|#)?`.

4. 239 should scan title — correct as written. Change l.270 to `" ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])`, matching _claims in 237 (l.36) and 238 (l.24).

5. For the de-duplication, put the tuple in tests/conftest.py (which today holds only fixtures) as a module-level constant and import it in all nine sites, rather than "re-import or duplicate". Duplicating is what produced four shapes from one decision. Include tests/test_phase228_triumph_triples.py's SOURCED_ONLY: compose it as the shared campaign tuple plus its own extras (`SRAN`, `SB\d{3}`, the interval and publication-number patterns) so the campaign half cannot drift again while keeping its model-generated-only scope.

6. Optional but worth a line in the phase log: ROADMAP.md l.396 still labels row 240 "Gate 11 — European brand coverage integration test" while row 413 assigns "Gate 12" to phase 250 (electric). The test file is named test_phase240_gate12.py. Unrelated to this finding, but the gate's own name disagrees with the roadmap it is closing.


### [CONFIRMED] THREE TESTS PASS VACUOUSLY (proved by per-test coverage contexts + runtime data)

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/tests/test_phase237_european_differentials.py`

**Evidence.**

Method: coverage.py run with dynamic_context=test_function over all 31 Track K files, then for each test node compared the `for` header line against its first body line within that test's own context.

1. tests/test_phase237_european_differentials.py::TestBoundaries::test_no_valve_interval_figures (l.136-144)
   `for m in re.finditer(r"\d{1,3},\d{3}\s*(km|miles)", text)` — coverage: l.142 reached, l.143 and l.144 NEVER reached under this test. Runtime proof: known_issues_european_differentials.json has 15 entries and ZERO tokens matching `\d{1,3},\d{3}\s*(km|miles)` — in fact zero tokens matching the far looser `\d[\d,\.]*\s*(km|kms|miles|mi)\b` either. The assertion body has never executed. This is one of the two Phase 238 interval-deferral guards named in decision #2, so that deferral is currently unguarded for this file.
   Its twin, tests/test_phase225b_ktm_adventure.py::test_it_does_not_take_phase_238_ground (l.133-148), DOES fire (one match, "9,500 miles") and additionally has a non-vacuous tail assertion at l.149-150 — this is the contrast that proves 237's copy is dead rather than merely lucky.

2. tests/test_phase223_ktm_enduro.py::TestTheTpiOilingDistinction::test_no_entry_says_a_tpi_model_takes_premix (l.196-205)
   `for m in re.finditer(r"takes premix|takes premixed", text, re.I)` — coverage: l.203 reached, l.204/205 NEVER reached. Runtime proof: 6 entries, 1 TPI entry, 0 matches for that phrase; the file DOES contain the tokens "premix" and "premixed", just never in that exact two-word form. The entire test body is a no-op. "requires premix", "needs premix", "runs on premix" all pass.

3. tests/test_phase215_bmw_electrical.py::TestTheDealerModeEntriesAreTheRealDeliverable::test_proprietary_codes_are_described_not_enumerated (l.171-179)
   `for code in e["dtc_codes"]` — coverage: l.174 reached, l.175 reached, l.176 (the assert) NEVER reached. Runtime proof: known_issues_bmw_electrical.json has 3 entries; the union of all their dtc_codes is []. STD_CODE has never been applied to anything.

Also near-vacuous (filter selects rows, but the searched term occurs zero times so the predicate never enters its loop):
  tests/test_phase218_ducati_multistrada.py::test_no_belt_claimed_on_a_v4_only_entry (l.112-117) — 3 entries selected, 0 occurrences of "cam belt" in them
  tests/test_phase218_ducati_multistrada.py::test_no_chain_claimed_on_a_belt_engine_entry (l.119-124) — 2 entries selected, 0 occurrences of "cam chain"

**Auditor's recommended fix.**

For 237: broaden the mileage pattern to `\d[\d,\s]{2,}\s*(km|miles|mi)\b|\b\d+k\s*(km|miles)\b` and add an anti-vacuity companion in the style of tests/test_phase215_bmw_electrical.py::test_at_least_one_row_actually_shadows (l.146) — assert the file contains at least one mileage token so the guard cannot silently go dead again. For 223: match on the concept, `r"(takes|needs|requires|runs on|uses)\s+premix"`, and assert the TPI entry set is non-empty. For 215: either assert `dtc_codes == []` for every entry (which is what the file actually means, and is a real assertion) or add codes; the current form asserts nothing.

**Verifier verdict — real=True.**

Independently reproduced, both at the coverage level and at the runtime-data level. Line numbers in the finding match the tree exactly.

COVERAGE (coverage 7.14.1, `--source=tests`, arcs of the three named files):
- tests/test_phase237_european_differentials.py: {140:True, 141:True, 142:True, 143:False, 144:False}
- tests/test_phase223_ktm_enduro.py: {199..203:True, 204:False, 205:False}
- tests/test_phase215_bmw_electrical.py: {174:True, 175:True, 176:False}
All three loop bodies are unreached; all 103 tests in the four files pass.

RUNTIME:
1. 237 — known_issues_european_differentials.json has 15 entries and ZERO matches for `\d{1,3},\d{3}\s*(km|miles)`. Stronger than the auditor claimed: `grep -c "km\|miles"` on the whole file returns 0 — the file contains no km/mile/mi token in ANY field. Its twin at tests/test_phase225b_ktm_adventure.py:133-150 does fire (one match, "9,500 miles") and has a live tail assertion at l.149-150, confirming the contrast.
2. 223 — known_issues_ktm_enduro.json has 6 entries, 1 with "TPI" in `_claims`, and 0 matches for `takes premix|takes premixed` in the assertion-bearing fields. Body never executes.
3. 215 — known_issues_bmw_electrical.json has 3 entries; every one has `dtc_codes: []`. STD_CODE (l.54) is never applied at l.176.
Near-vacuous 218 also reproduces: `_drive_for`=="chain" selects 3 entries with 0 "cam belt" occurrences; =="belt" selects 2 with 0 "cam chain".

TWO PLACES THE FINDING OVERSTATES (they do not sink it, but they change the fix):
- "that deferral is currently unguarded for this file" is too strong. 237's pattern would catch the corpus house format: of 105 mileage tokens across the 30 Track K known_issues files, nearly all are comma-formatted ("15,000 km", "12,000 miles"). The guard is leaky, not absent. The leak is real though: known_issues_mv_agusta_triple.json writes "12000 km" and known_issues_triumph_tiger.json writes "18000 miles", so uncomma'd interval figures demonstrably do get authored in this corpus and would slip past.
- 223's narrow phrase is not arbitrary. "takes premix" is verbatim the entry's own symptom string — `"unsure if this two stroke takes premix"` — and `_claims` deliberately excludes `symptoms` ("Assertion-bearing fields only; `symptoms` are reports", tests/test_phase218_ducati_multistrada.py:50-52 and the equivalent in 223). The guard was written to forbid that exact symptom wording from migrating into a claim field. Still vacuous as written, but it is a scoping choice, not a misreading.

The recommended fix is wrong on 237 and inert on 223 — see corrected_fix.

**Verifier's corrected_fix.**

237 — the recommended fix would break the gate. "Add an anti-vacuity companion ... assert the file contains at least one mileage token" FAILS TODAY: the file has zero km/mile/mi tokens anywhere. Satisfying it would require injecting a mileage figure into the one file whose stated job (decision #2 / Phase 238) is to print none. The 215 `test_at_least_one_row_actually_shadows` pattern does not port here — shadowing is that phase's deliverable, mileage is not this one's. Also drop the proposed `\d[\d,\s]{2,}` : `\s` inside the class lets a match span across tokens. Instead:
  MILEAGE = r"\b\d{1,3}(?:,\d{3})+\s*(?:km|miles|mi)\b|\b\d{4,6}\s*(?:km|miles|mi)\b|\b\d{1,3}k\s*(?:km|miles|mi)\b"
covering "12,000 km", "12000 km", "18000 miles", "12k miles", while the required unit word keeps bare years/model numbers out (the file carries 1200, 2013, 1150 etc.). For anti-vacuity, test the PATTERN, not the content — a plain unit test asserting MILEAGE matches ["12,000 km","12000 km","18,000 miles","12k miles"] and does not match ["2013","1200","0.5"]. That cannot go dead through a regex typo and does not couple the guard to file content. Apply the same widened pattern to the identical leak in tests/test_phase225b_ktm_adventure.py:145.

223 — the recommended regex is a no-op. `(takes|needs|requires|runs on|uses)\s+premix` yields ZERO matches on the TPI entry's `_claims` text (verified); the test stays exactly as vacuous. It omits the bare stem, which is the only form present. Use:
  r"\b(takes?|needs?|requires?|runs? on|uses?)\s+premix"
That produces one match — "...it does not take premixed fuel" — and 223's `_asserts` (l.86) exempts it via NEGATION ("does not"/"not"), so the body executes and the test still passes (verified by loading the module and calling `_asserts`: returns False). Keep the original literal too, so the symptom wording stays forbidden in claim fields. `assert tpi` (the filter selects 1) is worth adding but guards the filter only, not the search — it is not a substitute for the above.

215 — do not freeze `dtc_codes == []`. known_issues_aprilia_mv_electrical.json carries standard P-codes (P0217, P0446, P0462, P0510, P0608), so a legitimate standard code could later belong on a BMW electrical entry, and the test's own docstring is deliberately permissive ("Any code cited must be standard-format"). Freezing to [] silently converts a format rule into a content prohibition. Keep the STD_CODE loop as the conditional it is, and add the assertion that actually covers the named risk — proprietary BMW codes are transcribed in PROSE, not in `dtc_codes`, and nothing currently scans prose. Add a scan of the assertion-bearing text for cited-as-fault-code tokens (e.g. `r"(?:fault |error |code )\s*[0-9A-F]{4,5}\b"`) asserting none appear; note the prose legitimately contains bare 2016/2017/2021, which are years, so the pattern must require the code-word prefix rather than matching bare 4-digit tokens.


### [CONFIRMED] SIX DEAD DISCRIMINATORS: the `_asserts()` negation-window predicate never returns True in any test in 216, 217, 218, 219, 222 or 223 — every guard built on it would pass identically if the function were `return False`

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/tests/test_phase223_ktm_enduro.py`

**Evidence.**

Whole-suite coverage (all 31 files, 1005 tests): the `return True` line inside `_asserts` is never executed in
  tests/test_phase216_ducati_monster.py (l.60)
  tests/test_phase217_ducati_panigale.py (l.59)
  tests/test_phase218_ducati_multistrada.py (l.58)
  tests/test_phase219_ducati_desmo.py (l.79)
  tests/test_phase222_ktm_duke.py (l.116)
  tests/test_phase223_ktm_enduro.py (l.101)
Only tests/test_phase221_ktm_1290.py (l.106) ever returns True (1 test).
223 is the extreme case: lines 96-101 — `before=`, `after=`, the REPORTED/SIMILE check, and `return True` — are ALL unreached across the entire suite. Every term match falls into the quoted-span `continue` at l.94-95, so the negation logic that 216/219/221/222 progressively built up is completely inert in 223.
This family is only ever consumed by `assert not _asserts(...)`, so a False-returning stub passes everything. The mention-versus-use machinery — the most intricate logic in Track K's tests — has essentially no coverage of its discriminating branch.

**Auditor's recommended fix.**

Give each `_asserts` a unit test in its own file that feeds it a known positive ('The LC8c is a V-twin') and a known negative ('This is not a V-twin') and asserts True/False respectively. That is one three-line test per file and it converts six inert predicates into six checked ones. Consider hoisting the six near-identical implementations into tests/conftest.py or a small test helper module so the family has one body instead of six.

**Verifier verdict — real=True.**

Independently reproduced, exactly. (1) Wrapping each module's `_asserts` and running the seven files (181 tests, all green) gives True/False return tallies of 216: 0/60, 217: 0/20, 218: 0/5, 219: 0/12, 221: 1/11, 222: 0/7, 223: 0/6 — the `return True` line fires only in test_phase221_ktm_1290.py. (2) `coverage run ... --show-missing` reports precisely the auditor's line numbers: test_phase216_ducati_monster.py 60; test_phase217_ducati_panigale.py 59; test_phase218_ducati_multistrada.py 57-58; test_phase219_ducati_desmo.py 79; test_phase221_ktm_1290.py 100%; test_phase222_ktm_duke.py 116; test_phase223_ktm_enduro.py 96-101 plus 204-205. (3) The stub-equivalence claim holds literally: replacing `_asserts` with `lambda *a, **k: False` in the six files yields "152 passed"; the same stub applied to 221 fails (`test_msc_is_described_as_a_supplier_system`, because `bosch = [e for e in raw if _asserts(_claims(e), r"\bBosch\b")]` at l.195 goes empty), confirming 221 is the sole file that detects the regression. (4) The 223 mechanism is as described: instrumenting the two call sites shows the l.205 site's outer regex `takes premix|takes premixed` has ZERO matches corpus-wide (so `_asserts` is never called from there, and l.204-205 are dead), while the l.227 site makes 6 calls of which 5 find no match at all and the single match — `450 EXC` inside the entry titled `EXC is a two-stroke and EXC-F is a four-stroke` — is swallowed by the quoted-span `continue` at l.94-95. Lines 96-101 (`before=`, `after=`, the REPORTED/SIMILE check, `return True`) are therefore all unreached. (5) Scope check: `_asserts` is module-local, defined in exactly these seven files, with no cross-imports between test modules (the only other grep hit, tests/test_phase226_triumph_bonneville.py:288, is a test *name* `test_no_entry_asserts_air_cooled_means_360`, not the predicate), so the 7-file run is equivalent to the whole-suite claim. The finding is if anything slightly understated: in 218 even the negation-check line 57 is dead, not just `return True` at 58.

**Verifier's corrected_fix.**

The finding is real but the recommended fix is wrong in one detail, incomplete in two, and its second half (the hoist) would make things worse.

A. THE PROBE AS WRITTEN GIVES FOUR FALSE READINGS. `_asserts` does NOT take the same kind of `term` in all seven files. 216/217/218/219 call `re.finditer(re.escape(term), ...)` — term is a LITERAL. 221/222/223 call `re.finditer(term, ...)` — term is a RAW REGEX. Verified by direct call: `_asserts("The LC8c is a V-twin", r"\bV-twin\b")` returns False in 216, 217, 218 and 219 (the escaped `\bV\-twin\b` matches nothing) and True in 221, 222, 223; with the bare literal `"V-twin"` it returns True in all seven, and `"This is not a V-twin"` returns False in all seven. So write the positive probe with a literal term in 216-219 and a regex term in 221-223, or the "known positive" test silently asserts the very deadness it is meant to detect.

B. ONE POSITIVE/NEGATIVE PAIR ONLY COVERS THE NEGATION BRANCH. The dangerous regression is an exemption regex that OVER-matches, which turns `_asserts` permanently False and stays invisible. Each file needs a probe per exemption it actually has, asserted in both directions (exempted phrasing -> False; same sentence with the exemption marker removed -> True). The exemption sets are not the same:
  - 216/217/218: negation BEFORE only, windows 70/70/80. Their NEGATION vocabularies also differ — 216 lacks `without`, `does not`, `nor `, `neither`; 217 lacks `does not`, `nor `, `neither`; 218 lacks `neither` — so the negative probe must use a word that file actually knows.
  - 219: + negation AFTER, + NAMED_SYSTEM (a +/-14 char window).
  - 221: + REPORTED on `before[-30:]`.
  - 222: + REPORTED on `before[-45:]`, SIMILE_BEFORE on `before[-30:]`, SIMILE_AFTER via `.match(after)`.
  - 223: + `_quoted_spans`, REPORTED(45), SIMILE_BEFORE(30), and NO SIMILE_AFTER.

C. DO NOT HOIST THE BODIES INTO ONE. The seven are not "near-identical"; they diverge on escape-vs-regex, window (70/70/80/90/90/90/90), before-only vs before-or-after negation, NEGATION vocabulary, REPORTED lookback (30 vs 45), and which of NAMED_SYSTEM / SIMILE_AFTER / quoted-spans exist. A union body would ADD exemptions to 216-218, making those guards strictly weaker — the exact failure the finding is trying to close. An intersection body would drop 219's NAMED_SYSTEM and 223's quotation exemption. If consolidation is still wanted, it must be one parameterised helper with a per-phase config, and it must be pinned first by a characterisation test that records the current True/False verdict of all 122 real calls (60+20+5+12+12+7+6) and asserts they are unchanged.

D. MISSING FROM THE FINDING: SEVERAL GUARDS ARE VACUOUS OVER THE REAL CORPUS, NOT MERELY UNCOVERED, AND A UNIT TEST WILL NOT FIX THAT. Counting raw term matches inside each real call: 216 9 matches/60 calls, 217 1/20, 218 **0/5**, 219 6/12, 221 9/12, 222 13/7, 223 1/6. Phase 218's `assert not _asserts(_claims(e), "cam belt")` / `"cam chain"` (l.115, l.122) never enters its loop because those strings never occur in the entries it guards — hence coverage marks l.57-58 dead, not just l.58. Likewise 223's premix guard (l.204-205) never runs because `takes premix|takes premixed` has zero corpus matches. Add, alongside the predicate unit tests, a presence assertion for each guarded term (or explicitly document the guard as an absence check), otherwise those two guards remain no-ops even with a perfectly tested `_asserts`.

E. BEST STRUCTURAL FIX — COPY 221. 221 is the only file whose suite fails under a False stub, and it earns that not from a synthetic unit test but from a real-data positive use: `bosch = [e for e in raw if _asserts(_claims(e), r"\bBosch\b")]` followed by `assert bosch` (l.195). Mirroring that "backwards genericness" pattern in the other six — one assertion that some entry positively claims the thing the file is about — converts the predicate from inert to load-bearing against the actual corpus, which a synthetic three-line probe does not do. Do both: the synthetic probes for branch coverage, the 221-style positive for real-data force.


### [CONFIRMED] FAMILY 4: 'earns its shadow' DTC guard has no member for Aprilia or MV Agusta, pins a single code literal per make, and no member ever compares `description`

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/tests/test_phase235_aprilia_mv_electrical.py`

**Evidence.**

Decision #4 members (shadow-quality half):
  tests/test_phase215_bmw_electrical.py::test_shadowing_rows_do_not_restate_the_generic_text (l.129) + ::test_at_least_one_row_actually_shadows (l.146, the family's only anti-vacuity companion)
  tests/test_phase220_ducati_electrical.py::test_all_six_shadow_a_generic_row (l.109-112) + ::test_no_row_repeats_the_generic_causes_or_fix (l.114-121)
  tests/test_phase225_ktm_electrical.py::test_shadowing_rows_exist_and_differ (l.140-147)
  tests/test_phase230_triumph_electrical.py::test_shadowing_rows_exist_and_differ (l.133-140)
  MISSING: tests/test_phase235_aprilia_mv_electrical.py has no shadow test whatsoever, although Phase 235 shipped dtc_codes/aprilia.json (7 rows) and dtc_codes/mv_agusta.json (6 rows).
Resolution half (make row wins, other makes still get generic) — 8 members, each pinning ONE code literal (CONSTANT):
  215::test_a_bmw_bike_gets_the_bmw_row / ::test_another_make_still_gets_the_generic_row (l.119/124, P0335)
  220::test_a_ducati_gets_the_ducati_row / ::test_another_make_still_gets_generic (l.123/128, P0302)
  225::test_a_ktm_gets_the_ktm_row / ::test_another_make_still_gets_generic (l.149/152, P0301)
  230::test_a_triumph_gets_the_triumph_row / ::test_another_make_still_gets_generic (l.142/145, P0301)
  MISSING for aprilia and mv-agusta.
Runtime scan of dtc_codes/: generic has 35 rows. aprilia.json shadows 0 of them, mv_agusta.json shadows 0. So nothing is hidden today — but by accident of code selection, not by a test. bmw shadows 7, ducati 6, ktm 6, triumph 4.
Blind spot shared by every member: only `common_causes` and `fix_summary` are compared. `description` is byte-identical to generic on 7 BMW rows (P0171 P0301 P0302 P0562 P0335 P0505), 5 Ducati, 3 KTM, 3 Triumph — no test notices.
Gate 12 partially covers the resolution half via ::test_a_make_specific_code_resolves_to_the_make_row_not_the_generic (l.152-163) for all 6 DTC makes — but it uses `_first_code(slug)` = rows[0]. For aprilia that is P0510 and for mv_agusta P0328, neither of which exists in generic.json, so for 2 of the 6 makes the test proves nothing about precedence: there is no generic row to lose to.

**Auditor's recommended fix.**

Add a shadow-quality test to test_phase235_aprilia_mv_electrical.py in the 225/230 shape, and — since neither file shadows anything today — make it the honest form: `shadowing = [c for c in codes if c['code'] in generic]; for c in shadowing: assert c['common_causes'] != g['common_causes'] ...` with no `>= 1` floor, plus an explicit `assert not shadowing, 'if this file starts shadowing, add the resolution pair'` recorded as executable documentation. In Gate 12, pick the first code that IS in generic.json rather than rows[0], and skip-with-message when a make shadows nothing. Add `description` to the compared fields across all four existing members, or state in one place why it is deliberately excluded.

**Verifier verdict — real=True.**

Independently reproduced, every load-bearing claim.

1. MISSING MEMBER — confirmed. `/Users/lilquant/Projects/moto-diag/tests/test_phase235_aprilia_mv_electrical.py` never opens `generic.json`: the only three hits for "generic" in the file are prose ("the generic reading is what the mechanic already has", l.184), an unrelated sentence at l.300, and `test_no_generic_row_claims_full_or_partial` (l.336) which is about `compat_matrix` statuses, not DTC rows. `grep -rl "generic.json\|GEN_DTC\|GENERIC_DTC" tests/` returns only 215, 220, 225, 230 (plus phase05/gate1/phase209, none of which compare make rows). So no shadow guard exists anywhere for the two files Phase 235 shipped.

2. THE FOUR EXISTING MEMBERS — confirmed at the cited lines and shapes. 215 l.129 `test_shadowing_rows_do_not_restate_the_generic_text` + l.146 `test_at_least_one_row_actually_shadows`; 220 l.109/114; 225 l.140; 230 l.133. All four compare exactly `common_causes` and `fix_summary`, none compares `description`. Resolution pairs at 215 l.119/124 (P0335), 220 l.123/128 (P0302), 225 l.149/152 (P0301), 230 l.142/145 (P0301) — one hard-coded literal each, none for aprilia or mv-agusta.

3. RUNTIME SCAN — reproduced exactly. generic.json = 35 rows. Shadowed codes: bmw 7, ducati 6, ktm 6, triumph 4, harley 1, aprilia 0, mv_agusta 0. aprilia codes are P0510 P0462 P0461 P0446 P0190 P0217 P0608; mv are P0328 P0208 P0638 P0639 P0561 P0501 — none in generic.

4. `description` BLIND SPOT — reproduced, with one arithmetic slip in the finding: byte-identical descriptions number 6 for BMW (not 7) — exactly the six codes it lists, P0171 P0301 P0302 P0562 P0335 P0505 — plus ducati 5, ktm 3, triumph 3. e.g. bmw P0171 description == generic P0171 description == 'System Too Lean (Bank 1)'. No test notices.

5. GATE 12 — confirmed hollow for 2 of 6 makes. Staged file l.133 `_first_code` returns `rows[0]["code"]`; l.152 `test_a_make_specific_code_resolves_to_the_make_row_not_the_generic` is parametrized over DTC_MAKES (l.45, all six). rows[0] is P0510 for aprilia and P0328 for mv_agusta, neither present in generic.json, so for those two makes there is no generic row to lose to and the test proves nothing about precedence.

6. Decision #4's premise verified in `src/motodiag/knowledge/dtc_repo.py` l.114-125: make match first, `make IS NULL` second.

Two scope corrections that do not overturn the finding but bound it:
- "Nothing stops a later edit adding P0301 to aprilia.json with the generic causes copied across" is slightly overstated for a *verbatim* copy. Phase 235's own `test_every_row_names_the_sae_divergence` requires `NOT the SAE meaning|SAE ` in every Aprilia row's common_causes, and `test_every_row_carries_its_provenance` requires "PROVENANCE" + "third-party" in every MV row's; no generic row contains any of those strings, so a byte-copy of generic `common_causes` already fails today. What is genuinely unguarded is a paraphrase-with-a-badge, and — completely — `fix_summary`, which neither Phase 235 test touches for either make.
- The finding understates one hazard. Because dtc_repo l.122-125 falls through to `candidates[0]` when neither a make match nor a generic row exists, a *non-shadowing* make row leaks onto other makes. Verified live against a loaded DB: `get_dtcs(["P0510"], make="Honda")` and `get_dtc("P0510", make="Honda")` both return the **Aprilia** row, and `get_dtcs(["P0328"], make="Honda")` returns the **MV Agusta** row. So the two makes with zero shadowing are not merely untested — they are the only two makes whose rows currently reach the wrong make.

**Verifier's corrected_fix.**

The fix is right in outline but wrong in one part and incomplete in two.

WRONG — do not add `description` to the compared fields. "Add `description` to the compared fields across all four existing members" turns 4 test files red against shipped content: bmw P0171/P0301/P0302/P0562/P0335/P0505, ducati P0301/P0302/P0230/P0562/P0505, ktm P0301/P0302/P0420, triumph P0301/P0302/P0303 all have descriptions byte-identical to generic. That identity is correct, not a defect: `description` holds the SAE code title ('System Too Lean (Bank 1)'), which is the same string for every make by definition — the make-specific value is deliberately carried in `common_causes` and `fix_summary`. Take the finding's own hedge instead: add one comment, once (the 215 module docstring at l.16-23 is the natural home, since 220/225/230 all cite 215's reasoning), saying `description` is the shared SAE title and is excluded on purpose, and that shadow quality is judged on causes and fix. Changing 17 shipped descriptions to satisfy a new assert would be the test driving bad content.

INCOMPLETE 1 — Gate 12 needs a second change, not just `_first_code`. Picking "the first code that IS in generic" fixes coverage for bmw/ducati/ktm/triumph, but the test's discriminating assert at l.161 is `body["description"] == row["description"]`, and for bmw/ducati/triumph the first shadowing code (P0171, P0301, P0301) is description-identical to generic — so the assert cannot tell the make row from the generic row even after the fix, and `body["make"] == row["make"]` is doing all the work. Assert on `common_causes` (or `fix_summary`) instead, which the shadow-quality tests already guarantee differ. Keep the make assert.

INCOMPLETE 2 — the aprilia/mv "resolution pair" should pin the leak, not be skipped. A skip-with-message is the wrong shape for these two makes, because their zero-shadow state is not benign: dtc_repo falls through to `candidates[0]` when there is neither a make match nor a generic row, so `get_dtcs(["P0510"], make="Honda")` returns the Aprilia row (verified) — a row whose entire content asserts the SAE reading is wrong for this make, now served to a Honda. The honest pair for Phase 235 is:
  - `get_dtcs(["P0510"], make="Aprilia")` → make == "Aprilia" (the positive half, same as the other four members);
  - a test that pins today's cross-make behaviour for a code with no generic row, named for what it is (e.g. `test_a_code_with_no_generic_row_falls_through_to_the_make_row`), asserting the Honda query returns the Aprilia row, with a comment that this is dtc_repo's `candidates[0]` fallback and that shipping a code that DOES exist in generic would change it. That converts an unnoticed leak into recorded behaviour and gives the file a real reason to exist. Same for mv_agusta with P0328.

REFINE — the tripwire shape. `assert not shadowing, 'if this file starts shadowing, add the resolution pair'` placed after `for c in shadowing: assert ...` makes the loop provably dead, and fails a legitimate future content addition rather than the defect. Better: keep the differ loop as the real guard (it must exist and must cover `fix_summary`, which neither existing Phase 235 test checks for either make), and express the current zero as `assert {c['code'] for c in codes} & generic_codes == SHADOWED` against a module constant `SHADOWED: set[str] = set()`, with the message telling the editor to add the code to the constant and add the resolution pair. Same tripwire, no dead loop, and it self-documents when the state changes.

Everything else in the recommended fix stands: add the shadow-quality test to test_phase235_aprilia_mv_electrical.py in the 225/230 shape, comparing `common_causes` and `fix_summary` with no `>= 1` floor.


### [REJECTED] FAMILY 5: deliberate-absence guards (decision #2) are all single-entry or single-file; the KTM 390 build location has no guard at all

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/tests/test_phase233_mv_agusta_triple.py`

**Evidence.**

Five named absences, five wildly different guard scopes, no corpus sweep for any of them:
  MV shim diameter — tests/test_phase234_mv_agusta_four.py::test_no_diameter_figure_appears (l.128-134) scans only known_issues_mv_agusta_four.json. tests/test_phase238_european_intervals.py::test_shim_diameter_stays_unprinted_as_a_spec (l.131-136) explicitly REQUIRES "7.48 mm" to be present in known_issues_european_intervals.json (correctly, as a labelled owner report). Nothing guards mv_agusta_triple.json, aprilia_mv_electrical.json, european_tooling/differentials/parts.json. Corpus scan confirms 7.48 appears exactly once, in the sanctioned place.
  MV crank rotation direction — tests/test_phase233_mv_agusta_triple.py::test_it_declines_to_state_the_direction (l.140-148) scopes its `assert not re.search(r"\b(clockwise|anticlockwise|counter-?clockwise)\b")` to ONE entry selected by `[e for e in raw if "turns backwards" in e['title']][0]` — not the file, not the corpus. Corpus scan: no leak today.
  Triumph connector transition year — tests/test_phase236_european_tooling.py::test_triumph_transition_year_is_deliberately_absent (l.117-123) scopes to one entry AND scans only `e["description"]`; a year in that entry's fix_procedure or causes passes.
  Moto Guzzi 8V conversion cost — tests/test_phase237_european_differentials.py::test_guzzi_entry_prints_no_currency_figure (l.118-123) scopes to one entry matched by the title substring "Moto Guzzi 1200 8V".
  2025 KTM 390 platform build location — NO GUARD FOUND anywhere in tests/. The content is correct: known_issues_ktm_adventure.json's build-location entry says "The build location of the 2025-onward 390 platform could not be established from any manufacturer document, and is left open here" and repeats it in fix_procedure. But no test holds it there, and tests/test_phase225b_ktm_adventure.py has no assertion about it.
Related: the currency ban itself is a 3-member family with 2 regexes and 3 scopes — 237:118-122 (`\$|USD|NZD|\b\d,\d{3}\b`, one entry) vs tests/test_phase239_european_parts.py::test_no_campaign_numbers_and_no_currency_figures (l.269-273, `\$\s?\d|USD \d|NZD|EUR \d|GBP \d`, whole file but title omitted).

**Auditor's recommended fix.**

Add one class to Gate 12 — TestTheDeliberateAbsences — that sweeps all 30 European files for the five forbidden shapes, with the two sanctioned exceptions named explicitly (the 7.48 mm owner report in known_issues_european_intervals.json; nothing else). That converts five single-entry guards into five corpus invariants and gives the 390 build location its first guard. Widen 236's scan from `description` to the full claims blob, and 239's from description+fix+causes to include title.

**Verifier verdict — real=False.**

The finding's distinguishing claim — the one in its title — is false, and its recommended fix is both already in the tree and, as written, would fail on legitimate content.

1. "NO GUARD FOUND anywhere in tests/" for the KTM 390 build location is wrong, and the finding names the very file that refutes it. /Users/lilquant/Projects/moto-diag/tests/test_phase225b_ktm_adventure.py:186-193:

    def test_the_unestablished_build_location_stays_unestablished(self, raw):
        entry = next(e for e in raw if "built" in e["title"])
        text = _claims(entry)
        assert re.search(r"could not be established|unestablished", text, re.I)
        assert re.search(r"2025", text)

The finding asserts "tests/test_phase225b_ktm_adventure.py has no assertion about it." It has one, and 225b is mtime Sep 8 20:34 — in the tree well before the staged gate (22:08), so the audit could not have raced it. The guard is positive (the absence statement must survive) rather than negative (no plant name), which is arguably the better shape here, since the absence is about one entry's honesty, not about a token.

2. The recommended fix already exists, in a stronger form. /Users/lilquant/Projects/moto-diag/tests/test_phase240_gate12.py:294, test_the_deliberate_absences_hold_across_every_surface inside TestTrackKCorpusInvariants, sweeps all five absences (a) Triumph transition year, (b) KTM 390 build location, (c/c2) Guzzi conversion cost, (d) MV shim diameter, (e) MV crank rotation across a superset of the recommended file set — the 30 European knowledge files plus all 8 dtc_codes files, adapters.json, compat_matrix.json and parts.json. The tree copy (21101 bytes, 22:40) is a later revision of the staged copy (14207 bytes, 22:08), which had only the four-field campaign-number scan. I ran it: `pytest tests/test_phase240_gate12.py::TestTrackKCorpusInvariants tests/test_phase225b_ktm_adventure.py` → 38 passed.

3. The recommended fix would break a legitimate entry. It says to sweep all 30 European files for the five shapes "with the two sanctioned exceptions named explicitly (the 7.48 mm owner report in known_issues_european_intervals.json; nothing else)". A build-location sweep on that rule fires on known_issues_ktm_duke.json — "The 125 and 390 Duke are built in India by Bajaj — what that changes is parts sourcing, not quality" (year_start 2011, year_end 2024) — and on the known_issues_ktm_adventure.json entry itself, which names "the Chakan plant near Pune" in the course of recording the absence. The deliberate absence is scoped to the 2025-onward 390 platform, not to build locations generally; a name blacklist cannot see that distinction. The in-tree gate gets it right structurally, with a negative-phrase escape hatch plus `end = row.get("year_end") ...; assert end < 2025`. Likewise a corpus-wide Guzzi-cost sweep must not reach parts.json/adapters.json wholesale — those carry legitimate fiche and tool prices (GBP 576.23, USD 1,850, USD 190, EUR 300, ~$330); the in-tree gate narrows to tappet rows.

4. Minor: "Corpus scan confirms 7.48 appears exactly once" — it appears twice, both inside the same sanctioned entry of known_issues_european_intervals.json (once in description, once in fix_procedure). Both correctly labelled "owner report".

What does reproduce: the narrowness descriptions of the four phase-local guards are accurate (233:140 entry-scoped by `"turns backwards" in e['title']`; 236:117 asserts the year only against `e["description"]`; 237:118 entry-scoped by the title substring "Moto Guzzi 1200 8V"; 239:269 builds `text` from description+fix_procedure+causes, omitting title). But no leak sits behind any of them — my own corpus scan over the 30 European files plus dtc_codes, adapters, compat_matrix, parts and parts_xref found zero clockwise/anticlockwise tokens anywhere, no year in the Triumph connector entry's fix_procedure or causes, and no currency in any known_issues_european_parts.json title. So the residual is a hypothetical about future rewords, already covered corpus-wide by the gate, not a medium-severity gap at closure.

**Verifier's corrected_fix.**

No new class is needed — tests/test_phase240_gate12.py:294 already is TestTheDeliberateAbsences under a different name. If any hardening is wanted, it is two one-line widenings of the phase-local guards, and they must not be done the way the finding describes:

- tests/test_phase236_european_tooling.py:122 — change `e["description"]` to `_claims(e)` so a transition year in fix_procedure or causes is also caught. Verified safe: that entry currently has no 20xx year in any of the three fields.
- tests/test_phase239_european_parts.py:270 — add `e["title"]` to the joined text. Verified safe: no title in that file matches `\$|USD|EUR|GBP|NZD`.

Do NOT add a corpus-wide build-location name blacklist with "nothing else" exempted: it fails on known_issues_ktm_duke.json's legitimate "built in India by Bajaj" entry (year_end 2024) and on known_issues_ktm_adventure.json's own absence-recording entry, which names the Chakan plant. Keep the gate's structural form — a negative-phrase escape hatch plus a `year_end < 2025` bound — which distinguishes "asserts a plant for the 2025-onward platform" from "mentions a plant at all". Similarly keep the conversion-cost sweep narrowed to tappet rows rather than sweeping parts.json and adapters.json, which carry legitimate fiche and tool prices.


### [CONFIRMED] FAMILY 6: the designation-bar family is 6 sweepers plus 5 silent members that assert the bar with no counter-assertion (or a title-pinned one)

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/tests/test_phase222_ktm_duke.py`

**Evidence.**

The known family — glob the knowledge dir, skip by filename, assert no other make's entry scores a designation — currently has 6 members:
  tests/test_phase226_triumph_bonneville.py::test_no_other_makes_parallel_twin_entries_score (l.240-246)
  tests/test_phase227_triumph_tiger.py::test_no_other_makes_entry_scores (l.135-147)
  tests/test_phase228_triumph_triples.py::test_no_other_makes_entry_scores (l.305-317)
  tests/test_phase231_aprilia_rsv4.py::test_no_other_makes_entry_scores (l.101-110)
  tests/test_phase232_aprilia_dorsoduro.py::test_no_other_makes_entry_scores (l.121-133)
  tests/test_phase233_mv_agusta_triple.py::test_no_other_makes_entry_scores (l.246-253)
Five files define a designation table and assert the positive bar but have NO corpus counter-sweep — these are the family's next members:
  tests/test_phase222_ktm_duke.py — DESIGNATIONS at l.54; counter-assertion at l.176-187 is pinned to ONE entry in ONE file, selected by an exact title string: `e["title"] == "Ninja 250R/300 valve clearance — parallel twin needs regular checks"` in known_issues_kawasaki_ninja_small.json. CONSTANT — any reword of that Kawasaki title trips `assert generic, "the entry this file is measured against is gone"`.
  tests/test_phase224_ktm_engines.py — PREFIXES at l.49; counter-assertion at l.159-163 pinned to ONE file, known_issues_cross_platform_starting.json. CONSTANT.
  tests/test_phase223_ktm_enduro.py — DESIGNATIONS at l.51, bar asserted at l.147/150/161, NO counter-assertion.
  tests/test_phase229_triumph_vintage.py — BRITISH_SPECIFIC at l.72, bar asserted via l.116/163, NO counter-assertion.
  tests/test_phase234_mv_agusta_four.py — DESIGNATIONS at l.43, bar asserted at l.219-220, NO counter-assertion.
The six sweepers also disagree on their skip predicate: 231/232 use `"aprilia" in f.name or f.name.startswith("known_issues_european_")`; 233 needs a third clause naming known_issues_aprilia_mv_electrical.json explicitly. A future known_issues_mv_*.json that is not `mv_agusta_*` escapes 233's exclusion; a future European make file whose name does not start `known_issues_european_` is swept by all six.

**Auditor's recommended fix.**

Add the corpus sweep to 223, 229 and 234, and replace 222's title-literal and 224's single-file counter with the same sweep (skip by prefix, never by exact filename or title). Extract the sweep into one shared helper taking (designations, owned_prefixes) so the family has one body; that also makes 233's third exclusion clause unnecessary.

**Verifier verdict — real=True.**

Partly reproduced, but the enumeration is wrong in two places and the fix is wrong in two places. Baseline: all 400 tests across the eleven files pass (`.venv/bin/python -m pytest tests/test_phase22*.py tests/test_phase23*.py` for the named files).

CONFIRMED — the six sweepers exist, with the identical body (glob `known_issues_*.json`, skip by filename, `re.search(p, json.dumps(e))` over an UNAMBIGUOUS subset): test_phase226_triumph_bonneville.py::test_no_other_makes_parallel_twin_entries_score (def l.226), 227 (l.135), 228 (l.306), 231 (l.101), 232 (l.121), 233 (l.232). Their skip predicates do disagree exactly as claimed: 226/227/228 `"triumph" in f.name or f.name.startswith("known_issues_european_")`; 231/232 the same with "aprilia"; 233 adds a third clause `f.name == "known_issues_aprilia_mv_electrical.json"`.

CONFIRMED — 3 of the 5 claimed silent members:
- 222 l.174-187 `test_the_generic_parallel_twin_entry_fails_this_check` is pinned to one entry selected by an exact title string in known_issues_kawasaki_ninja_small.json, guarded by `assert generic, "the entry this file is measured against is gone"`. Brittle as described.
- 224 l.159-163 `test_a_cross_platform_entry_names_no_ktm_prefix` is pinned to one filename.
- 234 is the one genuinely silent member: its only designation test is `test_every_entry_names_a_designation_in_title_and_body` (l.217-220), there is no counter of any kind, and implementation.md's row 234 records none either.

REFUTED — 2 of the 5 do have counter-assertions; the auditor appears to have grepped for the `K.glob` idiom and missed counters written as named-file loops:
- tests/test_phase223_ktm_enduro.py l.154-163 `test_an_existing_dual_sport_entry_fails_this_check` — "The counter-assertion. The corpus's off-road entries describe trail machines; if one scored a designation the bar would be measuring nothing." — loops every entry of known_issues_honda_dualsport.json and known_issues_suzuki_dual_sport.json. implementation.md records this as the phase that *strengthened* the family idiom: "221 and 222 ran theirs against one hand-picked entry, while this runs over two entire dual-sport files, every entry".
- tests/test_phase229_triumph_vintage.py l.159-169 `test_the_forty_japanese_vintage_entries_score_zero` — "The counter-assertion... Swept over all six existing vintage and cross-platform files, every entry." — honda/kawasaki/suzuki/yamaha_vintage plus cross_platform_carbs and cross_platform_ignition.

So the headline should read 6 sweepers + 1 silent (234) + 2 literal-pinned (222 title, 224 one filename) + 2 file-list-scoped (223, 229) — not 5 silent members. The `K.glob` at 229 l.331 and 234 l.232 that the auditor saw are `test_no_title_collides_corpus_wide`, unrelated to the bar.

FIX DEFECTS (observed, not reasoned): applying the recommended sweep verbatim to 234 in a scratch copy FAILS — `AssertionError: known_issues_ducati_monster.json: Cam belt age-out and tensioner/idler bea scores ['998']`, 12 offending entries in total (Honda CBR600F ×3 on `\bF4\b`, Ducati Monster ×3 on `\b998\b`/`1078`, aprilia_mv_electrical ×6). 234 is the only family member with no UNAMBIGUOUS subset, and that subset is precisely what makes the sweep possible elsewhere (226's own comment: "America" alone matches "North America"). Second defect: removing 233's third clause, as the fix proposes, breaks 233 — that sweep then fails on 6 entries in known_issues_aprilia_mv_electrical.json, which legitimately names Brutale, Dragster, Turismo Veloce and MV Agusta. The fix's own rule "skip by prefix, never by exact filename" cannot reach that file without also exempting the two Aprilia model files. 222, 223, 224 and 229 do all sweep clean corpus-wide (0 hits each), so widening those four is safe.

**Verifier's corrected_fix.**

Scope the finding to what is actually there, then fix it in this order.

1. 234 is the only true gap, and it cannot take the sweep as written. First give it an UNAMBIGUOUS subset, as every other family member has:

   UNAMBIGUOUS = {k: v for k, v in DESIGNATIONS.items() if k in ("Brutale", "MV")}

   dropping "F4" (matches Honda CBR600F F2/F3/F4 entries), "998" (Ducati Monster), "1078" (Ducati Monster) and "four-cylinder" (generic). Keep the full DESIGNATIONS for the positive bar at l.217-220 — the file's five titles need "F4"/"four-cylinder" to clear it. The sweep must also exempt known_issues_aprilia_mv_electrical.json, exactly as 233 does. Verified: with that subset and that exemption the added sweep passes (32 passed on a patched scratch copy).

2. 222 and 224: replace the pinned counters (222 l.174-187 title literal, 224 l.159-163 single filename) with the family sweep. Both pass corpus-wide with 0 hits as-is — 222 on its existing DESIGNATIONS, 224 on PREFIXES.

3. 223 and 229 are not silent; they are narrower. Widening 223 l.154-163 from two dual-sport files to the corpus, and 229 l.159-169 from six vintage files to the corpus, is a real strengthening and both pass with 0 hits — but frame it as widening an existing counter, not as adding a missing one. If the gate is imminent, this is the lowest-value of the three changes.

4. The shared helper must NOT have the signature `(designations, owned_prefixes)`. Cross-make ownership is a second, independent axis: known_issues_aprilia_mv_electrical.json is owned by Phase 235 and legitimately carries MV designations, yet its name shares the `known_issues_aprilia_` prefix with the two Aprilia model files that 233 and 234 must sweep. Use `_no_other_make_scores(unambiguous, own_substrings, exempt=())` where `own_substrings` holds the make token plus the `known_issues_european_` prefix, and `exempt` holds the explicit cross-make files. Call sites: 222/223/224 own_substrings=("ktm",); 226/227/228 ("triumph",); 229 ("triumph",); 231/232 ("aprilia",); 233/234 ("mv_agusta",) with exempt=("known_issues_aprilia_mv_electrical.json",). Do not delete 233's third clause — it is load-bearing.

5. The escape the finding names is real and the helper should close it directly: make `own_substrings` for 233/234 ("mv_agusta", "mv_") so a future known_issues_mv_*.json is skipped, and add a guard test asserting every European make file in the knowledge dir is claimed by at least one family member's own_substrings — that is what stops the next cross-make file from being swept by all eight callers, and it is cheaper to enforce than a naming convention nobody reads.


---

## Dimension: gate

**Auditor summary.** Gate 12 is structurally in the house shape (front doors, honest-gaps class, regression class, schema pin) but the load-bearing assertions are mostly self-referential. Its make-coverage class is fully vacuous — `kb search` echoes the query string into its own output, so `assert "BMW" in result.output` passes on an empty knowledge base (proved: `kb search ZZZNOSUCHMAKE` exits 0 and its output contains "ZZZNOSUCHMAKE"). Its DTC test compares the API response to the very JSON file the test just read, so it cannot detect a make row that restates the generic meaning — the exact defect Rule 4 names, and 17 rows in bmw/ducati/ktm/triumph.json already have descriptions byte-identical to generic.json. Its compat test intersects against a slug set that *includes* the deliberate `status: "incompatible"` rows, so recommending an adapter marked "DELIBERATE INCOMPATIBLE ROW" for MV Agusta would pass. None of the six Phase-231/233/234/238 deliberate absences (Rule 2) has a single assertion. The forum-tip provenance rule (Rule 3) has no assertion at all — and the corpus violates it today in two Track K entries, invisible to Gate 2 because its 90% threshold is diluted by 660 legacy rows. The campaign-number regex is US-NHTSA-shaped (`\d{2}V\d{6}`) while the Phase 231 trigger was a Citroën recall, a European format. The parts catalogue is reached only over HTTP with a make filter the assertion then re-checks, and the 100 parts_xref rows (41 European, all seven makes) are never resolved. The regression class omits Gate 2, the knowledge-base gate that Track K itself re-scoped twice. Concrete replacement/addition code is given for all of it; every recommended test was executed against the live corpus and is green today except the forum-tip test, which is red on two real defects.


### [CONFIRMED] (a) VACUOUS: the entire make-coverage class passes on an empty knowledge base — `kb search` prints the query back

- **severity (auditor):** critical
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py:147`

**Evidence.**

`test_kb_search_by_make_returns_known_issues` runs `kb search <Make>` and asserts `MAKES[slug].split()[0] in result.output`. Both of `kb_search`'s exit paths echo the query verbatim:

  src/motodiag/cli/kb.py:606  console.print(f"[yellow]No issues mention {query!r}.[/yellow]")
  src/motodiag/cli/kb.py:609  _render_issue_table(rows, console, title=f"Known Issues matching {query!r}")

Executed against the fully seeded gate DB:
  [kb search 'BMW']           exit=0  'BMW' in output = True   first line: "Known Issues matching 'BMW'"
  [kb search 'ZZZNOSUCHMAKE'] exit=0  'ZZZNOSUCHMAKE' in output = True   first line: "No issues mention 'ZZZNOSUCHMAKE'."

Breaking input: delete every BMW entry from the corpus (or every European file). `kb search BMW` still exits 0, still prints "No issues mention 'BMW'.", the substring is still present, the test is still green. For MV Agusta the assertion is weaker still — it looks for the two-letter substring "MV". For Moto Guzzi it looks for "Moto", which also matches "MotoDiag", "Motorcycle" and "motor".

Also note the search itself is over title/description/symptoms only (kb.py:587 docstring), not the `make` column — so even a non-empty result set is not evidence that the make is *covered*, only that some row mentions the word.

**Auditor's recommended fix.**

Replace with `kb list --make`, which filters the make column and returns real rows, and assert on row content rather than on the echoed query. Verified against the live corpus: BMW/Ducati/KTM/Triumph/Aprilia/MV Agusta/Moto Guzzi all return rows (Moto Guzzi = 15).

    class TestEveryEuropeanMakeAnswersThroughTheCli:
        #: Floor per make, from the live corpus at Phase 239. Deliberately
        #: a floor and not an equality: new phases add rows, and a gate
        #: that fails on growth teaches people to edit the gate.
        MIN_ROWS = {"bmw": 40, "ducati": 35, "ktm": 35, "triumph": 40,
                    "aprilia": 15, "mv-agusta": 12, "moto-guzzi": 5}

        @pytest.mark.parametrize("slug", sorted(MAKES))
        def test_kb_list_by_make_returns_that_makes_rows(self, slug):
            """`kb search` echoes its own query into both of its exit
            paths, so `<make> in output` is true even for a make with no
            rows at all. `kb list --make` filters the make COLUMN, and
            the assertion counts rendered rows carrying that make."""
            display = MAKES[slug]
            result = _run(["kb", "list", "--make", display, "--limit", "300"])
            hits = result.output.count(display)
            assert hits >= self.MIN_ROWS[slug], (
                f"{display}: {hits} rows rendered, expected >= "
                f"{self.MIN_ROWS[slug]}\n{result.output[-800:]}"
            )

        def test_kb_list_make_filter_is_not_a_no_op(self):
            """The control the test above needs: a make that cannot be in
            the corpus must come back empty. Without this, a --make flag
            that silently ignored its argument would satisfy every row
            count above."""
            result = _run(["kb", "list", "--make", "Bugatti", "--limit", "300"])
            assert "Bugatti" not in result.output or "0" in result.output
            for display in MAKES.values():
                assert result.output.count(display) == 0, result.output[-600:]

**Verifier verdict — real=True.**

REPRODUCED independently. (1) Both `kb search` exit paths echo the query: /Users/lilquant/Projects/moto-diag/src/motodiag/cli/kb.py:604 `f"[yellow]No issues mention {query!r}.[/yellow]"` and :609 `title=f"Known Issues matching {query!r}"` (auditor cited 606; the print starts at 603 — immaterial off-by-two). Neither path is non-zero exit. (2) The search really is text-only: `search_known_issues_text` at /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/issues_repo.py:200-206 is `WHERE LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(symptoms) LIKE ?` — the `make` column is never consulted. (3) I ran the breaking input: built the gate's own fixture DB but loaded ONLY the DTC directory, leaving `known_issues` at 0 rows, then executed the assertion verbatim for all seven makes. Every one exit=0, assertion PASS, output e.g. "No issues mention 'BMW'." On the fully seeded DB, `kb search 'ZZZNOSUCHMAKE'` and `kb search 'Bugatti Chiron'` likewise exit 0 with the query echoed. So the class's only known-issues assertion is green against a knowledge base containing zero known issues. Two corrections that do not save the test: "Track K could be deleted wholesale and class 1 stays green" is overstated — the sibling tests read dtc_codes/<make>.json and compat_matrix.json off disk (`_first_code`, `_compat_rows`) and would error if those files were deleted; the accurate claim is that an emptied known_issues table leaves the whole class green. Severity critical is fair for the gate's headline row.

**Verifier's corrected_fix.**

The direction is right (`kb search` must go; a make filter must replace it) but the proposed replacement is still partly vacuous, and one of its stated numbers is wrong.

WHY IT IS STILL VACUOUS. `hits = result.output.count(display)` counts the substring anywhere in the rendered table — the Title column, and the Make column of CROSS-MAKE rows, whose make cell is a list like "BMW, Ducati, KTM, Triumph, Aprilia, MV Agusta, Moto Guzzi" (these are real values in the corpus). `--make X` is `make LIKE '%X%'` (issues_repo.py:84-86), so those rows match every make named in them. Measured on the live gate DB — rows whose make column matches vs rows whose make is EXACTLY the make: BMW 59/54, Ducati 52/46, KTM 53/48, Triumph 59/55, Aprilia 28/20, MV Agusta 23/16, Moto Guzzi 8/4. I then deleted every make-EXCLUSIVE row for all seven makes, left the cross-make rows, and ran the auditor's assertion: Aprilia hits=15 vs floor 15 -> STILL GREEN; Moto Guzzi hits=7 vs floor 5 -> STILL GREEN. So Phase 235's entire Aprilia contribution could be deleted and the replacement test would still pass, by one hit. (BMW/Ducati/KTM/Triumph/MV Agusta do fail, correctly.) Also, "Moto Guzzi = 15" in the write-up is an output-occurrence count, not a row count: there are 4 rows with make == "Moto Guzzi" (from known_issues_european_parts.json x2, _differentials.json, _intervals.json), 8 matching the LIKE. And the docstring's claim that the assertion "counts rendered rows carrying that make" is not what the code does.

CORRECTED VERSION — count structured rows, and require rows the make OWNS. `kb list` has no --json, so the counting goes through the HTTP API front door the class already uses for the DTC test (note limit is capped at 200 by _MAX_LIMIT in api/routes/kb.py:39, so 300 would 422; `total` is unbounded anyway), with the CLI kept as a real front-door check. Run green as written against the live corpus (15 tests passed):

    class TestEveryEuropeanMakeAnswersThroughTheCli:
        #: Rows whose make column is EXACTLY this make, at Phase 239:
        #: BMW 54, Ducati 46, KTM 48, Triumph 55, Aprilia 20,
        #: MV Agusta 16, Moto Guzzi 4. Floors, not equalities — a gate
        #: that fails on growth teaches people to edit the gate. Counting
        #: OWN rows and not LIKE matches is the point: the corpus has
        #: cross-make rows whose make cell lists all seven makes, so a
        #: LIKE count stays green for a make with no rows of its own.
        MIN_OWN_ROWS = {"bmw": 40, "ducati": 35, "ktm": 35, "triumph": 40,
                        "aprilia": 15, "mv-agusta": 12, "moto-guzzi": 3}

        @pytest.mark.parametrize("slug", sorted(MAKES))
        def test_the_make_has_rows_of_its_own(self, slug, api):
            """`kb search` echoes its query into BOTH exit paths, so
            `<make> in output` is true on an EMPTY knowledge base. Ask a
            filter that reads the make COLUMN and count structured rows."""
            display = MAKES[slug]
            r = api.get("/v1/kb/issues", params={"make": display, "limit": 200})
            assert r.status_code == 200, r.text[:400]
            body = r.json()
            rows = body["items"]
            assert all(display.lower() in (x["make"] or "").lower() for x in rows), \
                [x["make"] for x in rows][:5]
            own = [x for x in rows if (x["make"] or "").strip() == display]
            assert len(own) >= self.MIN_OWN_ROWS[slug], (
                f"{display}: {len(own)} rows of its own "
                f"({body['total']} incl. cross-make), expected >= "
                f"{self.MIN_OWN_ROWS[slug]}")

        def test_the_make_filter_is_not_a_no_op(self, api):
            """The control: a make that cannot be in the corpus must come
            back empty, or every row count above is satisfied by a filter
            that ignores its argument."""
            r = api.get("/v1/kb/issues", params={"make": "Bugatti", "limit": 200})
            assert r.status_code == 200, r.text[:400]
            assert r.json()["total"] == 0, r.json()["total"]

        @pytest.mark.parametrize("slug", sorted(MAKES))
        def test_the_cli_renders_that_make(self, slug):
            """The CLI half of the front door: `kb list --make` filters the
            make column (kb.py:399-471) and must render rows, not the
            'No issues match the filters.' path."""
            display = MAKES[slug]
            result = _run(["kb", "list", "--make", display, "--limit", "300"])
            assert "No issues match the filters." not in result.output, result.output[-400:]
            assert display in result.output, result.output[-800:]

Verified failure modes: on a DB with known_issues empty, all three tests fail for all seven makes; after deleting only the make-exclusive rows, test_the_make_has_rows_of_its_own fails for all seven (including Aprilia and Moto Guzzi, which the auditor's version passes).


### [REJECTED] (a) VACUOUS: the DTC precedence test compares the API answer to the file it just read, and never opens generic.json

- **severity (auditor):** critical
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py:152`

**Evidence.**

`test_a_make_specific_code_resolves_to_the_make_row_not_the_generic` does:

    code, row = _first_code(slug)          # rows[0] of <make>.json
    r = api.get(f"/v1/kb/dtc/{code}", params={"make": row["make"]})
    assert body.get("make") == row["make"]
    assert body.get("description") == row["description"]

Both sides come from the same file. generic.json is never loaded, so the test cannot express the sentence in its own docstring.

Two concrete breakages that pass it:

1. A make row that verbatim restates the generic meaning (Rule 4's "hides it"). This is not hypothetical — it is in the tree now. Comparing dtc_codes/*.json against generic.json (35 codes):
     bmw     10 rows, 7 overlap generic, 6 with byte-identical description  (P0171 P0301 P0302 P0562 P0335 P0505)
     ducati   6 rows, 6 overlap,        5 identical                        (P0301 P0302 P0230 P0562 P0505)
     ktm      8 rows, 6 overlap,        3 identical                        (P0301 P0302 P0420)
     triumph  7 rows, 4 overlap,        3 identical                        (P0301 P0302 P0303)
   The gate is green on all 17. (They do differ in fix_summary and common_causes — which is the argument that they *do* earn the shadow — but the gate measures neither, so it cannot tell those 17 apart from a full copy.)

2. Inverted precedence for two of the six makes. `_first_code` takes rows[0]: aprilia's is P0510 and mv_agusta's is P0328, and NEITHER exists in generic.json (aprilia overlap = 0, mv_agusta overlap = 0). If `get_dtc` were rewritten generic-first (dtc_repo.py:44-58), the generic SELECT returns None for those codes, execution falls through to the make row, and the test still passes. So for Aprilia — the make the docstring calls "the whole point of Phase 235" — the precedence path is never executed at all.

**Auditor's recommended fix.**

Two tests: one that exercises precedence on a code that genuinely exists in both, and one that enforces the shadow rule against generic.json. Both verified green on the live corpus.

    GENERIC = {r["code"]: r for r in json.loads((DTC / "generic.json").read_text(encoding="utf-8"))}

    def _shadowing_rows(make_slug):
        """(make_row, generic_row) for every make row that SHADOWS a
        generic code. Aprilia and MV Agusta shadow nothing — recorded
        in TestTheHonestGaps, not silently skipped here."""
        rows = json.loads((DTC / f"{make_slug.replace('-', '_')}.json").read_text(encoding="utf-8"))
        return [(r, GENERIC[r["code"]]) for r in rows if r["code"] in GENERIC]

    SHADOWING_MAKES = sorted(m for m in DTC_MAKES if _shadowing_rows(m))

    @pytest.mark.parametrize("slug", SHADOWING_MAKES)
    def test_the_make_row_wins_over_a_generic_row_for_the_same_code(self, slug, api):
        """Precedence, exercised on a code that EXISTS IN BOTH files.
        The gate's original picked rows[0], which for Aprilia and MV is
        a code generic.json does not carry — so generic-first ordering
        would have fallen through to the make row and passed anyway."""
        make_row, generic_row = _shadowing_rows(slug)[0]
        code = make_row["code"]
        r = api.get(f"/v1/kb/dtc/{code}", params={"make": make_row["make"]})
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body.get("make") == make_row["make"], body
        # The control: the SAME code with no make must return generic.
        r2 = api.get(f"/v1/kb/dtc/{code}")
        assert r2.status_code == 200, r2.text[:400]
        assert (r2.json().get("make") or None) is None, r2.json()
        assert r2.json().get("description") == generic_row["description"]

    @pytest.mark.parametrize("slug", SHADOWING_MAKES)
    def test_every_shadowing_make_row_earns_its_shadow(self, slug):
        """Rule 4. dtc_repo resolves make-specific before generic
        (dtc_repo.py:44), so a make row that restates generic in EVERY
        field a reader sees does not add a make fact — it deletes the
        generic one for that make. 17 rows currently share the generic
        DESCRIPTION; each is kept alive by a distinct fix_summary and
        common_causes, and that is what this measures. A future row
        pasted wholesale from generic.json fails here."""
        offenders = []
        for make_row, generic_row in _shadowing_rows(slug):
            def norm(row, field):
                v = row.get(field)
                if isinstance(v, list):
                    v = " ".join(v)
                return " ".join((v or "").split()).lower()
            differs = any(
                norm(make_row, f) != norm(generic_row, f)
                for f in ("description", "fix_summary", "common_causes", "severity")
            )
            if not differs:
                offenders.append(make_row["code"])
        assert not offenders, (
            f"{slug}: these rows restate generic.json in every field and "
            f"therefore hide it: {offenders}"
        )

**Verifier verdict — real=False.**

The evidence NUMBERS reproduce exactly, but the two load-bearing claims are false.

1. "The test cannot express the sentence in its own docstring" / "vacuous" — DISPROVED by execution. Every row in generic.json carries make: null (verified: {repr(make)} over all 35 rows == {'None'}), and dtc_repo.get_dtc falls back with "SELECT * FROM dtc_codes WHERE code = ? AND make IS NULL" (dtc_repo.py:53-56). So `assert body.get("make") == row["make"]` IS the precedence discriminator — the make field alone separates the make row from the generic row, which is why the test does not need to open generic.json. I ran the gate in a sandbox (scratchpad/gate, repo untouched) and monkeypatched a generic-first get_dtc into motodiag.api.routes.kb (the route at api/routes/kb.py:362 calls it), then re-ran the gate's exact assertions:
   bmw P0171 -> FAIL (returned make=None); ducati P0301 -> FAIL; ktm P0120 -> FAIL; triumph P0301 -> FAIL; aprilia P0510 -> PASS; mv-agusta P0328 -> PASS.
Four of six parametrizations go red under an inverted get_dtc, so the gate goes red. The test detects exactly the failure its docstring names. Only the aprilia/MV parametrizations are non-exercising — and for them there is no precedence to invert, since generic.json carries neither code.

2. "Gate 12 is the only place that rule could have been enforced, and it enforces nothing" — FALSE. Rule 4 is already enforced per-make, live and green, by tests that DO load generic.json and do precisely what the recommended fix proposes, plus a stronger control the proposed fix lacks:
   tests/test_phase215_bmw_electrical.py:129 test_shadowing_rows_do_not_restate_the_generic_text ("assert c['common_causes'] != g.get('common_causes')" and the same for fix_summary), with :146 test_at_least_one_row_actually_shadows guarding vacuity;
   tests/test_phase220_ducati_electrical.py:114 test_no_row_repeats_the_generic_causes_or_fix, with :109 test_all_six_shadow_a_generic_row;
   tests/test_phase225_ktm_electrical.py:140 and tests/test_phase230_triumph_electrical.py:133 test_shadowing_rows_exist_and_differ.
Each file also asserts the real precedence AND the leak control the finding's fix omits: test_another_make_still_gets_generic — get_dtcs([code], make="Honda") must return make is None. Running those classes: 16 passed.

3. No corpus defect exists. The finding concedes the 17 rows differ in fix_summary and common_causes; I confirmed the proposed shadow test passes green on all four shadowing makes, i.e. it would change nothing about the tree.

So the finding is a scope error: it treats "this one gate test does not re-check Rule 4" as "Rule 4 is unenforced and precedence is untested", when the rule is enforced in four phase files and precedence is exercised by 4/6 of the gate's own parametrizations. Severity "critical" is unsupportable — there is no reachable failure for a mechanic and no green-on-broken-corpus scenario.

**Verifier's corrected_fix.**

No fix is required; do not block the gate on this. The only defensible residue is a small hardening, and it should be written knowing the per-phase tests already own Rule 4 (215/220/225/230), so duplicating the shadow assertion at gate level buys little.

If you want the gate to exercise precedence for all six makes rather than four, change _first_code to prefer a shadowing code and record the honest gap, rather than adding the two proposed tests:

    GENERIC = {r["code"] for r in json.loads((DTC / "generic.json").read_text(encoding="utf-8"))}

    def _precedence_code(make_slug):
        """A code that exists in BOTH the make file and generic.json when
        one exists, so the make-before-generic branch is actually taken.
        Aprilia and MV Agusta shadow nothing; for them rows[0] only proves
        the make row is reachable, which TestTheHonestGaps records."""
        rows = json.loads((DTC / f"{make_slug.replace('-', '_')}.json").read_text(encoding="utf-8"))
        return next((r for r in rows if r["code"] in GENERIC), rows[0])

and in TestTheHonestGaps:

    @pytest.mark.parametrize("slug", ["aprilia", "mv-agusta"])
    def test_these_makes_shadow_no_generic_code(self, slug):
        rows = json.loads((DTC / f"{slug.replace('-', '_')}.json").read_text(encoding="utf-8"))
        assert not [r["code"] for r in rows if r["code"] in GENERIC], (
            f"{slug} now shadows generic rows — give it the Phase 215 shadow "
            "test and widen the gate's precedence parametrisation")

Two defects in the finding's own proposed fix, if it is used anyway:
- Its control ("the same code with no make must return generic") is weaker than what phases 215/220/225/230 already assert. The dangerous leak is a make row answering for a DIFFERENT make; get_dtc with make=None never consults a make row at all, so the no-make control cannot catch it. Use make="Honda" as those tests do.
- test_every_shadowing_make_row_earns_its_shadow passes if ANY of description/fix_summary/common_causes/severity differs, so a row copying generic text verbatim and only bumping severity from medium to high would pass. The existing per-phase tests are stricter: they require common_causes AND fix_summary to both differ.


### [CONFIRMED] (a) VACUOUS: the adapter test's expected set contains the DELIBERATE INCOMPATIBLE rows, so recommending a known-broken adapter passes

- **severity (auditor):** high
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py:164`

**Evidence.**

`test_compat_recommend_names_an_adapter_for_the_make` builds `slugs = {r["adapter_slug"] for r in _compat_rows(slug)}` from EVERY row for that make and asserts `slugs & found`. `_compat_rows` does not filter on `status`.

compat_matrix.json carries 86 European rows, of which 17 are `status: "incompatible"`, several written as explicit teaching rows:

    {"adapter_slug": "tuneecu-aprilia", "make": "mv-agusta", "model_pattern": "%",
     "year_min": 1997, "year_max": 2026, "status": "incompatible",
     "notes": "DELIBERATE INCOMPATIBLE ROW. MV Agusta is absent from TuneECU's supported marque list entirely, at every age. TuneECU is often recommended as the che..."}

Breaking input: regress `list_compatible_adapters`'s `min_status` tier filter (compat_repo.py:426-447) so incompatible rows are returned. `hardware compat recommend --make mv-agusta` now offers `tuneecu-aprilia`. `tuneecu-aprilia` is in `slugs`, the intersection is non-empty, the gate is green — and a mechanic buys the one tool the corpus exists to warn them off. The regression is not merely undetected; the broken behaviour makes the assertion *easier* to satisfy.

Secondary weakness in the same test: `model = rows[0]["model_pattern"].replace("%","").strip() or "any"`. For aprilia and mv-agusta rows[0] has `model_pattern: "%"`, so the gate queries the literal model `"any"` at year 1997 — not a machine anyone owns. It happens to return rows because "%" LIKE-matches, but the gate is not asking the mechanic's question.

**Auditor's recommended fix.**

Assert the exclusion directly, on real model names, in both directions. All six cases verified against the live corpus: default `--min-status read-only` excludes the incompatible adapter and `--min-status incompatible` reveals it.

    #: (make, a model a customer actually names, year, adapter the matrix
    #: marks incompatible for exactly that bike). tuneecu-aprilia is the
    #: sharpest pair: correct for an Aprilia RSV4, a DELIBERATE
    #: INCOMPATIBLE ROW for any MV Agusta.
    INCOMPATIBLE_CASES = [
        ("mv-agusta", "F4",               2010, "tuneecu-aprilia"),
        ("ktm",       "390 Duke",         2020, "tuneecu-ktm-android"),
        ("triumph",   "bonneville T100",  2005, "dealertool-triumph"),
        ("bmw",       "S1000RR",          2018, "elm327-generic-bt-clone"),
        ("ducati",    "panigale V4",      2020, "elm327-generic-bt-clone"),
        ("aprilia",   "RSV4",             2010, "elm327-generic-bt-clone"),
    ]

    def _recommend(make, model, year, min_status=None):
        args = ["hardware", "compat", "recommend", "--make", make,
                "--model", model, "--year", str(year), "--limit", "50", "--json"]
        if min_status:
            args += ["--min-status", min_status]
        return json.loads(_run(args).output)

    class TestTheAdapterCatalogueRefusesTheWrongTool:
        @pytest.mark.parametrize("make,model,year,bad", INCOMPATIBLE_CASES)
        def test_an_incompatible_adapter_is_never_recommended(self, make, model, year, bad):
            """`recommend` defaults to --min-status read-only, which ranks
            incompatible (tier 3) out. The gate's original assertion —
            `any matrix slug for this make appears` — is satisfied BY the
            incompatible row, so it would go green on the regression it
            exists to catch."""
            got = {r.get("slug") or r.get("adapter_slug") for r in _recommend(make, model, year)}
            assert bad not in got, f"{make} {model}: recommended {bad}, which the matrix marks incompatible"

        @pytest.mark.parametrize("make,model,year,bad", INCOMPATIBLE_CASES)
        def test_the_incompatible_row_is_present_and_merely_ranked_out(self, make, model, year, bad):
            """The control. Without it, deleting the incompatible rows
            outright would pass the test above — and the shop would lose
            the warning rather than gain a filter."""
            got = {r.get("slug") or r.get("adapter_slug") for r in _recommend(make, model, year, "incompatible")}
            assert bad in got, f"{make} {model}: {bad} is gone from the matrix, not filtered"

        @pytest.mark.parametrize("make,model,year,_bad", INCOMPATIBLE_CASES)
        def test_no_recommendation_carries_a_non_working_status(self, make, model, year, _bad):
            got = _recommend(make, model, year)
            assert all(r["status"] in {"full", "partial", "read-only"} for r in got), \
                sorted({r["status"] for r in got})

        def test_a_carburetted_triumph_honestly_returns_nothing(self):
            """Executable documentation: the 2001-2007 air-cooled
            Bonneville has no ECU, so every tool row for it is
            incompatible and `recommend` correctly offers nothing. Meant
            to fail the day someone 'fixes' the empty result."""
            assert _recommend("triumph", "bonneville T100", 2005) == []

**Verifier verdict — real=True.**

Reproduced independently, with two factual corrections to the write-up.

CONFIRMED — the test is vacuous with respect to the thing it appears to guard:
1. `_compat_rows(make)` in the staged gate file filters only on `r["make"]`; there is no `status` predicate. `test_compat_recommend_names_an_adapter_for_the_make` then builds `slugs = {r["adapter_slug"] for r in rows}` and asserts `slugs & found`, so every DELIBERATE INCOMPATIBLE slug is a member of the expected set.
2. The quoted row exists verbatim in compat_matrix.json: `{"adapter_slug": "tuneecu-aprilia", "make": "mv-agusta", "model_pattern": "%", "year_min": 1997, "year_max": 2026, "status": "incompatible", "notes": "DELIBERATE INCOMPATIBLE ROW. MV Agusta is absent from TuneECU's supported marque list entirely..."}`.
3. I ran the proposed breaking input. Patching `motodiag.hardware.compat_repo._min_status_tier` to return tier 3 (neutering the `min_status` filter in `list_compatible_adapters`) makes the real CLI return `[('texa-idc5-bike','full'), ('tuneecu-aprilia','incompatible'), ('elm327-generic-bt-clone','incompatible')]` for `hardware compat recommend --make mv-agusta`. The gate test still passed (6 passed) under that regression. The assertion is monotone-increasing in the returned set, so it is structurally incapable of catching over-permissiveness.
4. Secondary weakness confirmed: for `aprilia` and `mv-agusta`, `rows[0]["model_pattern"]` is `"%"`, so `model` becomes `"any"` and `year` becomes 1997 — the gate queries a machine nobody owns.

CORRECTION 1 (does not change the verdict): the matrix has 86 European rows of which 15, not 17, are `status: "incompatible"` (16 incompatible rows corpus-wide, one of them harley).

CORRECTION 2 (moderates severity, does not negate it): "The only gate that could protect them" is false. I copied `tests/test_phase145_compat.py` into an isolated tree and ran it under the same simulated regression: three tests fail — `test_list_compatible_adapters_incompatible_excluded_by_default`, `test_list_compatible_adapters_year_range_filter`, `test_list_compatible_adapters_min_status_filter` (3 failed, 54 passed). So the suite would go red, not green, on that particular regression. However phase 145 exercises only synthetic `mock-elm`/`harley` fixtures, so a European-specific or make-normalisation regression (e.g. hyphenated `mv-agusta`) would slip past both it and the gate. The gate remains non-load-bearing for the content it exists to close, which is the finding's substance.

The recommended fix also verifies: all six pairs behave as claimed against the live corpus (absent at default `--min-status read-only`, present at `--min-status incompatible`), `_recommend("triumph","bonneville T100",2005)` genuinely returns `[]`, and running the fix under the simulated regression produces 13 failures. Its one gap is noted in corrected_fix.

**Verifier's corrected_fix.**

The proposed class is correct as written — I ran it verbatim against the live corpus (25 assertions pass) and against the simulated `_min_status_tier` regression (13 fail). Adopt it. Two amendments:

(1) COMPLETE THE FIX — it leaves untouched the very weakness it diagnoses. The finding flags that `test_compat_recommend_names_an_adapter_for_the_make` queries model `"any"` at 1997, but the patch only adds a new class beside it. Repair the coverage test too, with real bikes. Note that the incompatible-case triple for Triumph CANNOT be reused here: `("triumph","bonneville T100",2005)` correctly returns `[]`, so a coverage assertion on it would fail. Verified non-empty triples:

    COVERAGE_CASES = [
        ("bmw",       "S1000RR",   2018),   # 6 adapters
        ("ducati",    "panigale V4", 2020), # 4
        ("ktm",       "390 Duke",  2020),   # 1 (autel-ap200bt, read-only)
        ("triumph",   "Tiger 800", 2015),   # ECU bike, unlike the 2005 carb Bonneville
        ("aprilia",   "RSV4",      2010),   # 5
        ("mv-agusta", "F4",        2010),   # 2
    ]

    @pytest.mark.parametrize("make,model,year", COVERAGE_CASES)
    def test_compat_recommend_names_a_working_adapter_for_the_make(self, make, model, year):
        got = _recommend(make, model, year)
        assert got, f"{make} {model} {year}: recommend returned nothing"

Drop `_compat_rows`-derived `slugs` from that assertion entirely; the expected set built from unfiltered matrix rows is the defect.

(2) CORRECT THE RATIONALE COMMENT. The docstring on `test_an_incompatible_adapter_is_never_recommended` implies the gate is the sole protection. It is not: `tests/test_phase145_compat.py::TestCompatibilityRepo::test_list_compatible_adapters_incompatible_excluded_by_default` already fails on a tier-filter regression, on mock fixtures. The honest justification for the new class — and the reason it still earns its place — is that phase 145 proves the MECHANISM on `harley`/`honda` mocks while nothing proves it over Track K's real European rows, so a make-normalisation or European-data regression evades every existing test. Word it that way, or the next reader will delete the class as duplicate coverage.

Optional, cheap, and worth it: move `test_a_carburetted_triumph_honestly_returns_nothing` into the existing `TestTheHonestGaps` class, whose stated contract ("PASS today, MEANT to fail the day someone fills the gap") is exactly what that test is.


### [CONFIRMED] (a) VACUOUS: the campaign-number regex is US-NHTSA-shaped, and the Phase 231 leak was a European (Citroën) recall number

- **severity (auditor):** high
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py:245`

**Evidence.**

pat = re.compile(r"\b\d{2}V\d{6}\b|\bRecall \d{6,7}\b")

`\d{2}V\d{6}` is the NHTSA campaign format. The decision this test enforces was taken *because a cited number turned out to be a Citroën recall* — i.e. a European identifier. None of the European forms match: a BMW campaign number (`0061340700`), a Ducati service action (`SRV-24-001`), an EU Safety Gate reference (`A12/00088/24`), a Triumph service bulletin (`SB-2024-11`). Adding any of those to a European entry leaves the gate green.

Field coverage is also partial. The scan is:
    text = " ".join([e["title"], e["description"], e["fix_procedure"]] + e["causes"])
The European entries also carry `symptoms`, `model`, `parts_needed` and `dtc_codes` (union of keys across the 30 European files confirmed). A campaign number in `symptoms` — "Owner asks about campaign A12/00088/24" — is not scanned.

Separately, the file selection is dead code that reads as if it works:
    K.glob("known_issues_{bmw,ducati,ktm,triumph,aprilia,mv,european}*.json")
pathlib has no brace expansion; this always returns []. The `or [...]` fallback is what actually selects the 30 files. Correct today by accident; anyone who "simplifies" the fallback away silently scans nothing.

I scanned all 30 European files for European-shaped identifiers: the corpus is clean today (only "GS-911", a tool name, matches a naive pattern). So this is purely a guard that does not guard.

**Auditor's recommended fix.**

Widen the pattern, widen the fields, and drop the brace-glob. Verified: green on the corpus today, fires on each injected European format.

    EURO_PREFIXES = ("bmw", "ducati", "ktm", "triumph", "aprilia", "mv", "european")
    EURO_FILES = sorted(
        p for p in K.glob("known_issues_*.json")
        if any(p.name.startswith(f"known_issues_{m}") for m in EURO_PREFIXES)
    )

    def _all_text(entry):
        """Every free-text field a reader sees. The gate's original read
        four of nine, so a number in `symptoms` or `model` was invisible."""
        parts = []
        for v in entry.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts += [x for x in v if isinstance(x, str)]
        return " ".join(parts)

    #: Campaign/recall identifier shapes. The NHTSA form alone was the
    #: gate's whole pattern — but the Phase 231 leak was a CITROEN
    #: recall, i.e. a European identifier, which that form cannot match.
    CAMPAIGN_PATTERNS = [
        ("nhtsa",     r"\b\d{2}V\d{6}\b"),
        ("eu-rapex",  r"\bA1[12]/\d{4,5}/\d{2}\b"),
        ("labelled",  r"\b(?:campaign|recall|service action|safety action|service bulletin)"
                      r"\s*(?:number|no\.?|ref(?:erence)?\.?|code|id)?\s*[:#]?\s*"
                      r"([A-Z]{1,4}[-_ ]?\d{3,}[A-Z0-9\-]*|\d{6,12})\b"),
        ("bare-long", r"\b(?:campaign|recall)\b[^.]{0,40}?\b\d{8,12}\b"),
    ]

    def test_no_campaign_reference_number_anywhere_in_track_k(self):
        """Phase 231. Describe the campaign, route the reader to a frame
        number check — never print an identifier, because a cited one
        turned out to belong to a Citroen."""
        import re
        offenders = []
        for f in EURO_FILES:
            for e in json.loads(f.read_text(encoding="utf-8")):
                text = _all_text(e)
                for name, pat in CAMPAIGN_PATTERNS:
                    m = re.search(pat, text, re.I if name == "labelled" else 0)
                    if m:
                        offenders.append(f"{f.name} [{name}] {e['title'][:50]}: {m.group(0)[:40]}")
        assert not offenders, offenders

    def test_the_campaign_guard_selects_the_european_files(self):
        """The gate's file selection was `K.glob(\"...{bmw,ducati,...}*.json\")`,
        which pathlib never expands — it always returned [], and only an
        `or` fallback saved it. Pin the count so an empty scan is loud."""
        assert len(EURO_FILES) == 30, [p.name for p in EURO_FILES]

    def test_campaign_entries_route_to_a_frame_number_check(self):
        """The positive half. Phase 231 did not say 'say nothing about
        campaigns' — it said describe it and send the reader to the frame
        number. An entry that discusses a campaign and offers no route is
        the failure mode a pure denylist cannot see."""
        import re
        talks = re.compile(r"\brecall\b|\bcampaign\b", re.I)
        routes = re.compile(r"frame number|VIN|chassis number|dealer .{0,30}check|"
                            r"manufacturer'?s? .{0,30}(?:check|lookup|database)", re.I)
        offenders = []
        for f in EURO_FILES:
            for e in json.loads(f.read_text(encoding="utf-8")):
                text = _all_text(e)
                if len(talks.findall(text)) >= 3 and not routes.search(text):
                    offenders.append(f"{f.name}: {e['title'][:60]}")
        assert not offenders, offenders

**Verifier verdict — real=True.**

All three sub-claims reproduce, and the underlying decision is weaker-guarded than the auditor even says.

1. NHTSA-only pattern. /private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py:245 is `pat = re.compile(r"\b\d{2}V\d{6}\b|\bRecall \d{6,7}\b")`. I injected each European shape into a sentence and the pattern matched none: `0061340700`, `SRV-24-001`, `A12/00088/24`, `SB-2024-11`, `Campaign 0061340700`.

2. Stronger than the auditor claims: the shape that ACTUALLY leaked is the UK DVSA form, and the gate misses it. The per-phase tests that own the Phase 231 decision guard two patterns — /Users/lilquant/Projects/moto-diag/tests/test_phase231_aprilia_rsv4.py:120-121 (`\b\d{2}V\d{3}\b` and `RM/\d{4}/\d+`), same at test_phase232_aprilia_dorsoduro.py:160-161 and test_phase233_mv_agusta_triple.py:127-128, with the docstring "a UK prefix on a Canadian campaign, whose UK counterpart is a Citroën recall". The gate matches neither `RM/2019/123` nor the 3-digit NHTSA form `19V123`. The corpus-wide backstop is strictly narrower than the per-file tests it backstops.

3. Field coverage. Confirmed by key union over the 30 European files (257 entries): keys are causes, description, dtc_codes, estimated_hours, fix_procedure, make, model, parts_needed, severity, source, symptoms, title, year_end, year_start. The gate scans only title, description, fix_procedure, causes — `symptoms` (a str list on all 257 entries), `model`, `parts_needed`, `dtc_codes` are invisible.

4. Dead brace-glob. `K.glob("known_issues_{bmw,...}*.json")` returns `[]` (reproduced directly); the `or [...]` fallback selects exactly the 30 European files. The `== 30` pin the auditor proposes is correct today.

5. Corpus clean today, so this is a vacuous guard rather than a hidden leak. Independent broad scan of all text in the 30 files found no 6+ digit runs, no `RM/YYYY/N`, no `X-1234-56` shapes; the only identifier-shaped tokens are tool and model strings (GS-911, ELM327, MS80, GT 1000, CCM 450, MY20xx, KTM 1290, RS 660, SRV 850).

The recommended fix, however, is wrong: two of its three new tests are RED on the corpus as it stands, contradicting its own "Verified: green on the corpus today". See corrected_fix.

**Verifier's corrected_fix.**

The diagnosis is right; the patch as written does not pass. I ran all three proposed tests against the live corpus.

WHAT BREAKS IN THE PROPOSED FIX

(i) The "labelled" pattern false-positives twice today, so `test_no_campaign_reference_number_anywhere_in_track_k` fails on a clean corpus:
  known_issues_triumph_bonneville.json "Clutch cable chafing the main harness at the headstock" -> matches "recall in 2019"
  known_issues_triumph_tiger.json "Early Tiger 800 recalls include a deceleration sta..." -> matches "campaign on 2014"
Cause: under re.I, `([A-Z]{1,4}[-_ ]?\d{3,}...)` matches "in 2019" / "on 2014" — every year after the word recall is an "identifier".

(ii) `test_campaign_entries_route_to_a_frame_number_check` fails on four entries today:
  known_issues_ktm_adventure.json  '"Adventure" and "Super Adventure" are different KTM machines'
  known_issues_mv_agusta_triple.json 'The US scope of the MV Agusta fork recall understates the real one'
  known_issues_triumph_tiger.json  'Only the Tiger 1200s are shaft drive'
  known_issues_triumph_triples.json 'There is no cam or valve-gear recall on the 675'
Two of those only mention recalls in passing (a naming-confusion entry, a final-drive entry); one is a deliberate NEGATIVE finding whose whole point is that no campaign exists — Phase 227's own rule excludes those (tests/test_phase227_triumph_tiger.py:322, `if re.search(r"recall", e["title"]) and "not apply" not in e["title"]`). The MV entry does route the reader, via "build date ... affected window" and "where the machine was originally supplied", which the proposed `routes` regex does not accept. A >=3-mentions-anywhere trigger is the wrong scope.

(iii) It omits `RM/\d{4}/\d+`, the UK DVSA form — the actual Phase 231 leak shape, guarded in the three per-phase tests. Its "labelled" branch cannot rescue this either: the separator class is `[-_ ]`, so "recall ref RM/2019/123" does not match.

VERIFIED REPLACEMENT (0 false positives on the 30 files / 257 entries; fires on every injected form)

Keep the auditor's EURO_PREFIXES / EURO_FILES selection, the `_all_text` helper, and `test_the_campaign_guard_selects_the_european_files` (`len(EURO_FILES) == 30` — confirmed). Replace the patterns and the routing test:

    CAMPAIGN_PATTERNS = [
        ("nhtsa",          r"\b\d{2}V\d{3,6}\b", 0),          # 19V123 and 22V123456
        ("uk-dvsa",        r"\bRM?/\d{4}/\d{1,4}\b", 0),      # the shape that actually leaked
        ("eu-safety-gate", r"\bA1[12]/\d{4,5}/\d{2}\b", 0),
        ("alnum-id",       r"\b[A-Z]{2,4}[-/]\d{2,4}[-/]\d{1,4}\b", 0),   # SRV-24-001, SB-2024-11
        ("bare-long",      r"\b\d{8,12}\b", 0),               # BMW 0061340700; corpus has no 6+ digit run
        ("labelled",       r"\b(?:campaign|recall|service action|safety action|service bulletin)"
                           r"\s*(?:number|no\.?|ref(?:erence)?\.?|code|id)s?\b\s*[:#]?\s*"
                           r"(?=\S*\d)([A-Z0-9][A-Z0-9/\-]{2,})", re.I),
        ("labelled-digits", r"\b(?:campaign|recall|service action|bulletin)\b[^.]{0,60}?\b\d{6,12}\b", re.I),
    ]

The `(?=\S*\d)` lookahead is load-bearing: without it the "labelled" branch fires on the meta-mention "campaign reference numbers" in known_issues_ktm_adventure.json. `\d{8,12}` rather than `\d{6,12}` for the unlabelled branch keeps six-figure mileage prose out.

Scan with `_all_text(e)` over EURO_FILES and assert no match. Confirmed green today; confirmed to fire on: campaign 0061340700 / service action SRV-24-001 / A12/00088/24 / SB-2024-11 / RM/2019/123 / recall no. R/2015/078 / 19V123 / 22V123456 / "Owner asks about campaign A12/00088/24" (the symptoms-field case) / "campaign code 0031850200"; and confirmed NOT to fire on "subject to a recall in 2019", "a campaign on 2014 machines", "recall check by frame number".

Routing test, scoped the way Phase 227 scopes it (11 entries qualify today, 0 offenders):

    def test_campaign_entries_route_to_a_frame_number_check(self):
        title_talks = re.compile(r"\brecalls?\b|\bcampaigns?\b", re.I)
        negative    = re.compile(r"\bno\b|\bnot\b|does not apply|understate", re.I)
        routes      = re.compile(r"frame number|\bVIN\b|chassis number|build date|"
                                 r"affected window|originally supplied|dealer.{0,40}check", re.I)
        offenders = []
        for f in EURO_FILES:
            for e in json.loads(f.read_text(encoding="utf-8")):
                if title_talks.search(e["title"]) and not negative.search(e["title"]):
                    if not routes.search(_all_text(e)):
                        offenders.append(f"{f.name}: {e['title'][:60]}")
        assert not offenders, offenders

Trigger on the TITLE, not on a mention count, and exempt negative-finding titles — otherwise the gate punishes exactly the entries Phase 228/231 wanted (an entry that says no campaign exists, or that a national list understates scope).

Unrelated but worth noting while the file is staged: REPO_ROOT is `Path(__file__).resolve().parents[1]`, so the test only resolves the repo once it is placed in tests/; run from the scratchpad every DB-backed test errors in the fixture (`src/motodiag/knowledge/loader.py:87 NotADirectoryError`). Not part of this finding.


### [CONFIRMED] (b) MISSING ENTIRELY: not one assertion covers the six deliberate absences the track spent phases 231-238 protecting

- **severity (auditor):** critical
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py:207`

**Evidence.**

Rule 2 names six things that must not have leaked. Gate 12 tests none of them. Its `TestTheHonestGaps` class is about Moto Guzzi's *file* coverage instead, and its one interval test (line 231) is discussed separately below.

I verified all six are honoured in the corpus today, which is exactly why they need a guard — they are one careless paste from being lost, and each already has the tempting figure sitting nearby in prose:

  - known_issues_european_intervals.json prints "7.48 mm" but frames it: "Owner reports give 7.48 mm ... Treat the 7.48 mm figure as an owner report to be confirmed by the caliper, not a specification." A future edit that drops the frame is a one-word change.
  - known_issues_triumph_electrical.json says "the changeover is model-dependent across roughly 2023 to 2025, so check the actual machine rather than the year" — the hedge is the content.
  - known_issues_ktm_adventure.json: "The build location of the 2025-onward 390 platform could not be established from any manufacturer document, and is left open here rather than assumed to follow the earlier generation." The same entry states India/Chakan/Bajaj for the EARLIER 390, so the two sit one sentence apart.
  - known_issues_mv_agusta_triple.json: "**Which way that is in MV's own words could not be established here**" — while the surrounding paragraph explains at length why the direction matters.
  - the Guzzi roller-tappet entries in european_differentials.json and european_parts.json carry no currency figure.
  - known_issues_ktm_adventure.json and known_issues_european_differentials.json carry zero valve-interval figures; known_issues_european_intervals.json (Phase 238's file) carries 18.

**Auditor's recommended fix.**

A class per Rule 2. Every regex below was run against the live corpus (green) and against injected violations (fires) — results noted inline.

    class TestTheDeliberateAbsencesHeld:
        """Rule 2. Six figures Track K refused to print, each after a
        refutation. These are guards, not documentation: they pass today
        and are meant to fail the moment a figure reappears unframed."""

        def test_the_mv_shim_diameter_is_never_printed_as_a_specification(self):
            """Phase 234/238. A 7.48 mm owner report may be DESCRIBED as an
            owner report. It may not appear as a spec — the whole entry
            exists to say 'measure the shim in the engine first'."""
            import re
            spec = re.compile(r"(?:diameter|shim|pad)[^.]{0,60}?\b\d{1,2}[.,]\d{1,2}\s*mm"
                              r"|\b\d{1,2}[.,]\d{1,2}\s*mm[^.]{0,40}?(?:diameter|shim|pad)", re.I)
            framed = re.compile(r"owner report|owner figure|reported by owners|forum|"
                                r"not a specification|other sizes circulate", re.I)
            offenders = []
            for f in EURO_FILES:
                for e in json.loads(f.read_text(encoding="utf-8")):
                    t = _all_text(e)
                    for m in spec.finditer(t):
                        window = t[max(0, m.start() - 220):m.end() + 220]
                        if not framed.search(window):
                            offenders.append(f"{f.name}: {e['title'][:45]} -> {m.group(0)}")
            assert not offenders, offenders
            # fires on "Shim diameter is 7.48 mm"; silent on the live
            # "Owner reports give 7.48 mm ... that is an owner report".

        def test_the_triumph_connector_transition_year_is_never_pinned(self):
            """Phase 230. The 16-pin to red 6-pin changeover is
            model-dependent across roughly 2023-2025. A single year is
            the wrong answer even when it is nearly right, because it
            tells a shop to skip checking the machine."""
            import re
            connector = re.compile(r"six-pin|6-pin|Euro ?5", re.I)
            year = re.compile(r"\b(?:19|20)\d{2}\b")
            span = re.compile(r"\b(?:19|20)\d{2}\s*(?:to|through|[-–—/])\s*(?:19|20)\d{2}\b")
            hedge = re.compile(r"roughly|approximate|about|around|model-dependent|varies|"
                               r"transition|check the actual|rather than", re.I)
            offenders = []
            for f in [p for p in EURO_FILES if "triumph" in p.name]:
                for e in json.loads(f.read_text(encoding="utf-8")):
                    for s in re.split(r"(?<=[.!?])\s+", _all_text(e)):
                        if connector.search(s) and year.search(span.sub("", s)) and not hedge.search(s):
                            offenders.append(f"{f.name}: {s[:150]}")
            assert not offenders, offenders
            # fires on "Triumph switched to the red six-pin connector in 2023."
            # and "On Euro 5 machines from 2024 onward..."; silent on the
            # live "model-dependent across roughly 2023 to 2025".

        def test_the_2025_ktm_390_build_location_is_left_open(self):
            """Phase 225B. The earlier 390 is India/Chakan/Bajaj and the
            entry says so; the 2025-on platform could not be established
            and must stay open rather than inherit the older answer."""
            import re
            place = re.compile(r"\b(?:India|Chakan|Pune|Bajaj|China|CFMoto|Zhejiang|Mattighofen|Austria)\b")
            offenders = []
            for f in [p for p in EURO_FILES if "ktm" in p.name]:
                for e in json.loads(f.read_text(encoding="utf-8")):
                    for clause in re.finditer(r"[^.]{0,160}\b(?:2025|2026)\b[^.]{0,160}", _all_text(e)):
                        s = clause.group(0)
                        if re.search(r"\b39\d\b", s) and place.search(s):
                            offenders.append(f"{f.name}: {s[:170]}")
            assert not offenders, offenders
            # fires on "The 2025 390 Adventure is built in India at Chakan."

        def test_the_guzzi_roller_tappet_conversion_cost_stays_removed(self):
            """A currency-mangled figure was removed. Any money figure in
            a roller-tappet entry is that figure coming back."""
            import re
            money = re.compile(r"[$€£]\s?\d"
                               r"|(?<![\w.])\d[\d,.]{2,}\s*(?:EUR|USD|GBP|euros?|dollars?|pounds?)\b", re.I)
            offenders = []
            for f in EURO_FILES:
                for e in json.loads(f.read_text(encoding="utf-8")):
                    t = _all_text(e)
                    if re.search(r"roller[- ]?tappet|flat tappet", t, re.I):
                        for m in money.finditer(t):
                            offenders.append(f"{f.name}: {e['title'][:45]} -> {m.group(0)}")
            assert not offenders, offenders
            # fires on "costs about 1,800 EUR" and "€1800".

        def test_the_mv_crank_rotation_direction_is_never_named(self):
            """Phase 233. The triple's crank counter-rotates and the entry
            says so; WHICH WAY could not be established from MV, and the
            entry sends the reader to the machine's own timing marks.
            Naming a direction here is worse than silence: turning the
            wrong way slackens the cam chain and back-drives the starter
            one-way clutch."""
            import re
            direction = re.compile(
                r"(?:crank(?:shaft)?|rotat\w+)[^.]{0,90}?\b(?:clockwise|anti-?clockwise|counter-?clockwise)\b"
                r"|\b(?:clockwise|anti-?clockwise|counter-?clockwise)\b[^.]{0,90}?(?:crank(?:shaft)?|rotat)", re.I)
            offenders = []
            for f in [p for p in EURO_FILES if "mv" in p.name or "european" in p.name]:
                for e in json.loads(f.read_text(encoding="utf-8")):
                    for m in direction.finditer(_all_text(e)):
                        offenders.append(f"{f.name}: {e['title'][:45]} -> {m.group(0)[:90]}")
            assert not offenders, offenders
            # fires on "The MV triple crank turns anti-clockwise viewed from the right."

        @pytest.mark.parametrize("name", [
            "known_issues_ktm_adventure.json",
            "known_issues_european_differentials.json",
        ])
        def test_the_deferring_files_print_no_valve_interval(self, name):
            """Phase 238 owns intervals. These two defer to it, and the
            deferral is the point: two files quoting the same interval
            drift apart and a shop then has two answers."""
            import re
            vi = re.compile(r"(?:valve|shim|clearance)[^.]{0,120}?\b\d{1,3}[,.]?\d{3}\s*(?:km|mi|miles)\b"
                            r"|\b\d{1,3}[,.]?\d{3}\s*(?:km|mi|miles)\b[^.]{0,120}?(?:valve|shim|clearance)", re.I)
            hits = [f"{e['title'][:45]} -> {m.group(0)[:80]}"
                    for e in json.loads((K / name).read_text(encoding="utf-8"))
                    for m in vi.finditer(_all_text(e))]
            assert not hits, hits

        def test_phase_238_actually_holds_the_intervals_it_owns(self):
            """The other half. Without this, deleting every interval from
            the corpus would pass the deferral test above."""
            import re
            vi = re.compile(r"(?:valve|shim|clearance)[^.]{0,120}?\b\d{1,3}[,.]?\d{3}\s*(?:km|mi|miles)\b"
                            r"|\b\d{1,3}[,.]?\d{3}\s*(?:km|mi|miles)\b[^.]{0,120}?(?:valve|shim|clearance)", re.I)
            n = sum(len(vi.findall(_all_text(e)))
                    for e in json.loads((K / "known_issues_european_intervals.json").read_text(encoding="utf-8")))
            assert n >= 15, f"Phase 238's file holds only {n} valve interval figures"

**Verifier verdict — real=True.**

Reproduced independently, both halves.

GAP CONFIRMED. I read all 297 lines of the staged gate. Its complete assertion inventory: TestEveryEuropeanMakeAnswersThroughTheCli (kb search, DTC shadow, compat), TestCrossSurfaceAgreement (API issue search, parts), TestTheHonestGaps (four Moto Guzzi *file/row coverage* tests + test_aprilia_660_valve_interval_is_recorded_as_unverified, which checks a source value, not a figure), TestTrackKCorpusInvariants (cross-make files exist, campaign-number regex, provenance vocabulary, `regulation` in use, README count), TestRegression (six earlier gates + SCHEMA_VERSION == 52). Nothing anywhere touches the MV shim diameter, the Triumph transition year, the KTM 390 build location, the Guzzi conversion cost, the MV crank rotation direction, or the two files that defer intervals to Phase 238. The auditor's characterisation of TestTheHonestGaps as "about Moto Guzzi's file coverage instead" is exact.

CORPUS CLAIMS CONFIRMED. I ran every proposed regex against the live files (30 European files under the bmw/ducati/ktm/triumph/aprilia/mv/european prefixes): shim 0 offenders, Triumph 0, KTM 0, money 0, rotation 0, ktm_adventure 0 interval hits, european_differentials 0. Spot-checked the prose behind each:
 - known_issues_european_intervals.json: "the F4 engine manual — and prints **no diameter**. Owner reports give 7.48 mm ... Treat the 7.48 mm figure as an owner report to be confirmed by the caliper, not a specification."
 - known_issues_ktm_adventure.json: "The build location of the 2025-onward 390 platform could not be established from any manufacturer document, and is left open here rather than assumed to follow the earlier generation." — one sentence after "produced in India ... the Chakan plant near Pune".
 - known_issues_mv_agusta_triple.json: "**Which way that is in MV's own words could not be established here**, so establish it from the machine's own timing marks".
 - Both Guzzi roller-tappet entries (european_differentials.json, european_parts.json) carry no currency figure.
 - "clockwise" appears in exactly one corpus file, known_issues_cross_platform_brakes.json, which is outside Track K.

TWO INACCURACIES IN THE EVIDENCE, neither fatal. (a) The Triumph quote "the changeover is model-dependent across roughly 2023 to 2025" does not exist; the live text in known_issues_triumph_electrical.json is "the changeover is model-dependent, so check the actual machine rather than the year", and grep for "2023 to 2025" over the whole seed returns nothing. The corpus is stricter than described. (b) The claimed 18 valve-interval figures in known_issues_european_intervals.json is wrong under every text-assembly I tried: 14 (title+description+fix_procedure), 15 (+causes), 17 (+symptoms), 16 (raw JSON). This one matters because the fix asserts `n >= 15`.

The fix as pasted does not run and one of its six guards watches the wrong files, so corrected_fix is supplied.

**Verifier's corrected_fix.**

Three defects, all found by executing the proposed code against the live corpus.

DEFECT 1 — the class is a NameError as pasted. `EURO_FILES` and `_all_text` are used by every test and defined nowhere. The gate file's module scope has only json/os/subprocess/sys/Path/pytest plus the motodiag imports, and the constants K, DTC, HW, PARTS, MAKES, DTC_MAKES, COMPAT_MAKES, CROSS_MAKE_FILES. Add at module level (mirroring the fallback branch of test_no_campaign_reference_number_anywhere_in_track_k, which is the file's existing notion of "European"):

    _EURO_PREFIXES = ("bmw", "ducati", "ktm", "triumph", "aprilia", "mv", "european")
    EURO_FILES = sorted(p for p in K.glob("known_issues_*.json")
                        if any(p.name.startswith(f"known_issues_{m}") for m in _EURO_PREFIXES))

    def _all_text(e):
        """Every prose field an editor could paste a figure into."""
        return " ".join([e["title"], e["description"], e["fix_procedure"]]
                        + list(e.get("causes", [])) + list(e.get("symptoms", [])))

Assert the fixture is non-empty once — `assert len(EURO_FILES) == 30` — otherwise a rename silently turns all six guards into no-ops. (30 is the live count.)

DEFECT 2 — the Triumph guard watches the wrong files. It filters `[p for p in EURO_FILES if "triumph" in p.name]`, but the entry that actually carries the Phase 236 decision lives in known_issues_european_tooling.json, title "Triumph is the European connector outlier — it had the 16-pin socket before Euro 5, then moved to the red 6-pin", ending "Specific transition years are deliberately not printed here: the sources consulted disagreed by several model years, and a wrong year is worse than none when it decides which lead a shop orders." A year pasted into THAT entry passes the proposed test. Widening to all EURO_FILES naively fires twice on known_issues_aprilia_mv_electrical.json ("Euro 5 machines including the RS 660 ... and the 2021-on RSV4 and Tuono V4"). Gate on Triumph instead of on the filename. Also drop the `span` strip: the live entry prints no years at all, so a hedged range is not something the corpus needs permission for, and stripping it lets "the changeover ran 2023 to 2025" through.

    def test_the_triumph_connector_transition_year_is_never_pinned(self):
        import re
        connector = re.compile(r"six-pin|6-pin|six pin|Euro ?5", re.I)
        year = re.compile(r"\b(?:19|20)\d{2}\b")
        hedge = re.compile(r"roughly|approximate|about|around|model-dependent|varies|"
                           r"deliberately not printed|check the actual|rather than the year", re.I)
        offenders = []
        for f in EURO_FILES:
            for e in json.loads(f.read_text(encoding="utf-8")):
                t = _all_text(e)
                if "triumph" not in t.lower():
                    continue
                for s in re.split(r"(?<=[.!?])\s+", t):
                    if "triumph" not in s.lower():
                        continue
                    if connector.search(s) and year.search(s) and not hedge.search(s):
                        offenders.append(f"{f.name}: {s[:200]}")
        assert not offenders, offenders

Verified: 0 offenders live (both triumph_electrical and european_tooling now in scope); fires on "Triumph switched to the red six-pin connector in 2023.", "On Euro 5 machines from 2024 onward the red 6-pin is fitted." and "The Triumph changeover to the red six-pin ran 2023 to 2025."

DEFECT 3 — `assert n >= 15` sits exactly on the boundary and is decided by the helper the fix forgot to define. Measured counts for known_issues_european_intervals.json: 14 / 15 / 17 / 16 for the four plausible _all_text definitions. With the `_all_text` above it is 17, so pair the definition with a threshold that has headroom:

        assert n >= 8, f"Phase 238's file holds only {n} valve interval figures"

Eight still fails loudly if the intervals are gutted, and does not break on one editorial rewrite.

TWO SCOPE TIGHTENINGS (optional; the tests are green either way, but both are one legitimate edit away from a false failure that teaches the next author to delete the guard):

 - Crank rotation: `"mv" in p.name or "european" in p.name` puts the four cross-make files in scope, where an ordinary "turn the crankshaft clockwise to align the marks" for a Ducati or BMW would fail the MV guard. Restrict to entries that mention MV — `if not re.search(r"\bMV\b", _all_text(e)): continue` — scanning all EURO_FILES so the guard follows the content if it moves. Verified 0 offenders live; still fires on "The MV triple crank turns anti-clockwise viewed from the right."
 - Shim diameter: the corpus-wide spec regex is green today only by accident. known_issues_triumph_bonneville.json contains "Shim sizes run 2.00 to 3.20 mm in 0.025 mm steps", a legitimate Phase-2xx thickness spec that escapes solely because `[^.]{0,60}?` cannot bridge the decimal point in "2.00". Any future spec written as "shim thickness 2,50 mm" fails the MV guard. Gate the scan on entries that mention MV or the word "diameter", widen the fraction to `\d{1,3}` so "7.480 mm" cannot slip past, and add "no diameter" to the framing vocabulary (the live entry's own phrase is "prints **no diameter**"). Verified 0 offenders live; still fires on "Shim diameter is 7.48 mm", "The MV shims are 7.48 mm", "Order 7.48 mm shims for the F4".

The KTM build-location and Guzzi money guards need no change beyond the two module-level definitions: both are green live and both fire on the injected violations I tested, including "€1800", "1,800 EUR", "1800 euro" and "2000 euros" for the money one.

One residual the class does not cover, worth a comment rather than a test: the ktm_adventure interval guard passes partly because the file's single distance figure ("the protective sheath worn completely through and into the line at around 9,500 miles") has no valve/shim/clearance word within its 120-character window. That is correct behaviour, not luck, but a reviewer who sees "9,500 miles" in a file the gate calls interval-free should be told why it is allowed.


### [CONFIRMED] (b) MISSING, AND THE CORPUS IS RED: the forum-tip provenance rule (Rule 3) has no assertion, and two Track K entries break it

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json`

**Evidence.**

Gate 12's only provenance test is `test_provenance_vocabulary_is_the_six_values` (line 257), a subset check. The half of Rule 3 that carries meaning — forum entries must carry "Forum tip:", non-forum entries must not — is untested.

The corpus violates it today. Scanning all 96 files for `source == "forum"` without "Forum tip:" in fix_procedure:

  known_issues_mv_agusta_triple.json — "The MV triple's starter clutch is handed for reverse rotation — and is reported to have been fitted backwards"  (source: forum, no "Forum tip" anywhere in fix_procedure)
  known_issues_triumph_bonneville.json — "Air-cooled Bonneville starter and wheel faults that never got a recall — the idler-gear boss, the sprag clutch and left-hand rear spokes"  (source: forum, same)

Gate 2 cannot see them. `test_forum_tips_present` (tests/test_phase78_gate2_integration.py:114) measures the forum-derived population — `unverified` plus `forum` — against a 90% threshold. That population is 677 rows (660 legacy rows with no `source` column, defaulting to unverified, plus the 17 Track K `forum` rows). 675 carry a tip: 99.7% against a 90% floor. The two Track K defects are 2/677 and are drowned by the legacy denominator.

Provenance distribution across the 257 European entries: model-generated 131, service-manual 108, forum 17, regulation 1. `unverified` = 0 and `mechanic-verified` = 0 in Track K. Gate 12's vocabulary check is `seen <= {six values}`, which is satisfied by a corpus using only one value — so it also cannot detect a phase that dropped provenance recording altogether. And it reads the JSON files rather than the seeded DB, so it duplicates the CHECK constraint that migration 052 already enforces (migrations.py:3625) rather than testing anything the constraint does not.

**Auditor's recommended fix.**

Scope both halves of the rule to the Track K population, so its denominator is its own, and run it through the seeded DB rather than the files. NOTE: `test_every_forum_sourced_entry_carries_a_forum_tip` FAILS on the current corpus with the two entries above. That is the correct outcome — either add a "Forum tip:" line to each fix_procedure, or correct the `source` value to what the entry actually is.

    #: Track K's own titles, so the assertions below have a Track K
    #: denominator. Gate 2's 90% threshold is diluted by 660 legacy rows
    #: and cannot see a 2-row Track K defect.
    def _track_k_issues(gate_db):
        from motodiag.knowledge.issues_repo import search_known_issues
        titles = set()
        for f in EURO_FILES:
            titles |= {e["title"] for e in json.loads(f.read_text(encoding="utf-8"))}
        return [i for i in search_known_issues(db_path=gate_db) if i["title"] in titles]

    class TestTrackKProvenance:
        def test_the_seeded_rows_survived_the_loader(self, gate_db):
            """Read through the DB, not the JSON. The gate's file-level
            check duplicates migration 052's CHECK constraint; only a DB
            read catches an entry the loader silently dropped."""
            assert len(_track_k_issues(gate_db)) == 257

        def test_every_forum_sourced_entry_carries_a_forum_tip(self, gate_db):
            """Rule 3, first half, on Track K's own denominator.
            CURRENTLY RED — two entries break it:
              known_issues_mv_agusta_triple.json  'The MV triple's starter clutch is handed...'
              known_issues_triumph_bonneville.json 'Air-cooled Bonneville starter and wheel faults...'
            Fix the corpus, not the threshold."""
            forum = [i for i in _track_k_issues(gate_db) if i.get("source") == "forum"]
            assert forum, "no forum-sourced Track K entries"
            offenders = [i["title"][:60] for i in forum
                         if "Forum tip" not in (i.get("fix_procedure") or "")]
            assert not offenders, f"{len(offenders)}/{len(forum)} forum entries lack a Forum tip: {offenders}"

        def test_no_non_forum_entry_claims_a_forum_tip(self, gate_db):
            """Rule 3, second half. A service-manual entry carrying a
            'Forum tip:' asserts provenance it does not have — worse than
            carrying no tip at all."""
            offenders = [f"{i['title'][:50]} [{i.get('source')}]"
                         for i in _track_k_issues(gate_db)
                         if i.get("source") != "forum"
                         and "Forum tip" in (i.get("fix_procedure") or "")]
            assert not offenders, offenders

        def test_every_track_k_entry_records_a_source(self, gate_db):
            """The 660 pre-Track-K rows predate the column and default to
            unverified. Track K added the column and must populate it —
            `.get(\"source\", \"unverified\")`, as the gate writes it,
            makes a missing value indistinguishable from a recorded one."""
            missing = [i["title"][:50] for i in _track_k_issues(gate_db) if not i.get("source")]
            assert not missing, missing

        def test_the_provenance_distribution_is_the_one_track_k_recorded(self, gate_db):
            """`seen <= {six values}` passes on a corpus that uses one
            value. This pins the shape instead: no single source may
            dominate, and the two hard-won values must be present."""
            import collections
            dist = collections.Counter(i.get("source") for i in _track_k_issues(gate_db))
            assert set(dist) <= {"unverified", "model-generated", "forum",
                                 "service-manual", "mechanic-verified", "regulation"}, dist
            total = sum(dist.values())
            assert dist["service-manual"] >= 100, dist   # Phase 238's MD5-matched PDFs
            assert dist["forum"] >= 15, dist
            assert dist["regulation"] >= 1, dist          # Phase 235B's reason to exist
            assert dist["model-generated"] <= total * 0.6, dist

        def test_the_regulation_value_survives_the_check_constraint(self, gate_db, api):
            """The gate asserted `regulation` appears in one JSON file.
            Phase 235B's migration 052 rebuilt known_issues to widen the
            CHECK; the thing worth testing is that the value reaches a
            reader through the API, not that it is present in a file."""
            r = api.get("/v1/kb/issues", params={"q": "Euro 4", "limit": 100})
            assert r.status_code == 200, r.text[:400]
            items = r.json().get("items", [])
            assert any(i.get("source") == "regulation" for i in items), \
                sorted({i.get("source") for i in items})

**Verifier verdict — real=True.**

Reproduced independently, every number exact.

1) The two violations are real. Scanning all 96 `known_issues_*.json` for `source == "forum"` with no `"Forum tip"` in `fix_procedure` yields exactly two rows, the two named:
- `known_issues_mv_agusta_triple.json` — "The MV triple's starter clutch is handed for reverse rotation — and is reported to have been fitted backwards", `"source": "forum"`, fix_procedure is a 5-step numbered list with no marker.
- `known_issues_triumph_bonneville.json` — "Air-cooled Bonneville starter and wheel faults that never got a recall…", same.
15 of the 17 Track K `forum` rows carry the marker (12 in european_differentials, 2 in european_parts, 1 in ktm_adventure); these two do not. Zero non-forum rows carry one.

2) Gate 12 has no assertion for either half. `test_provenance_vocabulary_is_the_six_values` at line 257 is `assert seen <= {six}` — satisfied by a one-value corpus — plus `test_the_regulation_value_is_in_use`, which reads one file. Nothing else in the staged gate touches `Forum tip`.

3) Gate 2 is blind exactly as described. I seeded a DB from all 96 files (917 rows) and ran Gate 2's own population: `{"unverified","forum"}` = 677 rows, 675 with tips = 99.70% against the 90% floor. The two defects are 0.3% and cannot move it.

4) Distribution confirmed on the 257 Track K entries (30 European files, 257 unique titles, all 257 resolvable by title in the seeded DB with no legacy collision): model-generated 131, service-manual 108, forum 17, regulation 1; unverified 0, mechanic-verified 0.

5) The marker is load-bearing in production, not decorative: `src/motodiag/advanced/predictor.py:126` defines `_FORUM_TIP_MARKER = "Forum tip:"` and line 492 uses it as the first-choice extractor for the recommended action. So the two entries also silently take a different path through the predictor.

The finding's `why_it_matters` overstates one point — both entries do declare their provenance prominently in prose ("Drawn from owner-forum reporting, and flagged as such because it is not manufacturer documentation" / "Drawn from owner-forum consensus… not from a recall or a Triumph bulletin"), so a human reader is not misled. The machine-readable convention, and the rule, are still broken.

**Verifier's corrected_fix.**

The finding holds; the fix has three defects, one of them serious.

SERIOUS — the prescribed corpus repair cannot be applied as written. Both offenders live in files whose own phase tests forbid the marker file-wide AND pin the forum source. All 75 of these tests pass today:

- `tests/test_phase226_triumph_bonneville.py:183` `test_no_entry_fabricates_a_forum_tip` — "Gate 2's other half, asserted locally too" — asserts `"Forum tip" not in e["fix_procedure"]` for EVERY entry in the file, the forum-sourced one included. And `test_the_forum_sourced_entry_says_so_in_prose` asserts `len(forum) == 1`, with `test_the_entry_that_says_there_is_no_recall_is_excluded` then indexing `[0]`.
- `tests/test_phase233_mv_agusta_triple.py:255` `test_provenance_is_recorded_per_entry` does both in one body: `assert {e["source"] for e in raw} <= {"service-manual","forum"}` and `assert "Forum tip" not in e["fix_procedure"]`. Plus `test_the_sprag_entry_is_marked_forum_sourced` at line 158 asserts `sprag["source"] == "forum"`.

So "add a Forum tip: line" turns 226 and 233 red, and "correct the source value" turns them red too (one by count, one by pin). This is not an oversight the gate can quietly repair: Phases 226 and 233 chose prose-declared provenance over the token, pasted only the second half of Rule 3 locally, and the contradiction has been green ever since. The real finding is stronger than stated — the corpus contains a live, tested contradiction with Rule 3. Phase 240 must decide it explicitly and amend those two phase tests in the same change (replace the file-wide `not in` with the biconditional `("Forum tip" in e["fix_procedure"]) == (e["source"] == "forum")` already used at `test_phase237_european_differentials.py:63`, `test_phase239_european_parts.py:261` and `test_phase225b_ktm_adventure.py:62-72`), then add the marker. Note for whoever edits the MV text: `test_phase233…::test_it_declines_to_state_the_direction` bars `clockwise|anticlockwise|counter-clockwise` — "reverse rotation" is fine (the roadmap uses it), a direction word is not.

DEFECT 2 — `test_every_track_k_entry_records_a_source` is vacuous as written. Migration 052 declares `source TEXT NOT NULL DEFAULT 'unverified'` and `loader.py:162` passes `source=item.get("source", "unverified")`. A DB read can never return a falsy source; I measured 0 and it is structurally 0. Its own docstring argues for a file-level check, so make it one:
    missing = [e["title"][:50] for f in EURO_FILES
               for e in json.loads(f.read_text(encoding="utf-8")) if "source" not in e]
This is the one provenance assertion that genuinely must read the JSON, not the DB.

DEFECT 3 — `EURO_FILES` does not exist in the staged gate (only `CROSS_MAKE_FILES`). Define it, e.g. `EURO_FILES = [f for f in K.glob("known_issues_*.json") if f.name.startswith(tuple(f"known_issues_{p}" for p in ("bmw","ducati","ktm","triumph","aprilia","mv","european")))]` — that yields 30 files / 257 entries. Also replace `assert len(_track_k_issues(gate_db)) == 257` with a comparison against the file-derived count; that actually tests "the loader dropped nothing", which is what its docstring claims, instead of adding a magic number the gate already covers README-side via `test_documented_count_matches_the_live_seed`.

Verified as correct: the distribution thresholds all hold (service-manual 108 ≥ 100, forum 17 ≥ 15, regulation 1 ≥ 1, model-generated 131 ≤ 154.2), and the API test works — `q="Euro 4"` matches 3 rows total, `_MAX_LIMIT` is 200 so `limit=100` is accepted, and the `regulation` row sorts to position 0.


### [REJECTED] (b) MISSING: the parts cross-references are never resolved, and the parts test that exists asserts non-emptiness in disguise

- **severity (auditor):** high
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py:194`

**Evidence.**

`test_parts_search_reaches_the_european_rows` calls `/v1/shop/{id}/parts/search?q=oil filter&make=aprilia` and asserts `any("aprilia" in json.dumps(i).lower() for i in items)`. The API already filtered on `make=aprilia` (parts.py:248-266), so every returned row necessarily contains "aprilia" in its make field. The assertion reduces to `items != []`. It is the only parts test, it covers one make of seven, and it never touches parts_xref.

What Phase 239 actually built, and what nothing tests:
  parts.json      125 rows, 83 European — ducati 17, ktm 17, bmw 16, aprilia 11, triumph 9, moto-guzzi 9, mv-agusta 4
  parts_xref.json 100 rows, 41 European, all seven makes represented (bmw 12, ducati 10, triumph 7, ktm 5, aprilia 5, mv-agusta 1, moto-guzzi 1)
  0 dangling slugs; 0 European parts with an empty oem_part_number

`advanced parts xref <OEM_PN>` resolves by OEM PART NUMBER, not by slug (cli/advanced.py:3213-3241, parts_repo.get_xrefs). That is a second key space, and it is the one a mechanic types off the box. I ran it for one part per European make against the seeded DB: all seven exit 0 with a non-empty `xrefs` list. Nothing in Gate 12 would notice if a Phase 239 slug were renamed and the xref rows stopped resolving — the API search test would still pass, because search does not join xrefs.

**Auditor's recommended fix.**

Resolve one xref per European make through the CLI, and check the API search actually discriminates. Verified green on the live corpus for all seven makes.

    def _one_xref_per_make():
        """(make, oem_part_number) for one cross-referenced European part
        each. Derived from the data so a renamed slug shows up as a
        KeyError here rather than as a silently thinner catalogue."""
        parts = json.loads((PARTS / "parts.json").read_text(encoding="utf-8"))
        xrefs = json.loads((PARTS / "parts_xref.json").read_text(encoding="utf-8"))
        by_slug = {p["slug"]: p for p in parts}
        out = {}
        for x in xrefs:
            oem = by_slug.get(x["oem_slug"])
            if oem and oem["make"] in MAKES and oem["make"] not in out:
                out[oem["make"]] = oem["oem_part_number"]
        return sorted(out.items())

    XREF_CASES = _one_xref_per_make()

    class TestThePartsCatalogueResolves:
        def test_every_european_make_has_a_cross_referenced_part(self):
            assert {m for m, _ in XREF_CASES} == set(MAKES), sorted(m for m, _ in XREF_CASES)

        @pytest.mark.parametrize("make,oem_pn", XREF_CASES)
        def test_an_oem_number_resolves_to_an_aftermarket_equivalent(self, make, oem_pn):
            """`advanced parts xref` keys off the OEM PART NUMBER, a
            different key space from the slug the API search returns —
            so a renamed slug breaks this and nothing else."""
            body = json.loads(_run(["advanced", "parts", "xref", oem_pn, "--json"]).output)
            assert body["oem_part_number"] == oem_pn, body
            assert body["xrefs"], f"{make} {oem_pn}: no aftermarket equivalent resolved"

        def test_no_xref_row_points_at_a_part_that_does_not_exist(self):
            """Phase 239 wrote 100 xref rows against 125 parts. A dangling
            slug is invisible to `parts search`, which never joins."""
            parts = json.loads((PARTS / "parts.json").read_text(encoding="utf-8"))
            xrefs = json.loads((PARTS / "parts_xref.json").read_text(encoding="utf-8"))
            slugs = {p["slug"] for p in parts}
            dangling = [f"{x['oem_slug']} -> {x['aftermarket_slug']}" for x in xrefs
                        if x["oem_slug"] not in slugs or x["aftermarket_slug"] not in slugs]
            assert not dangling, dangling

        @pytest.mark.parametrize("make", sorted(MAKES))
        def test_parts_search_discriminates_by_make(self, make, api, shop_id):
            """The gate asserted `\"aprilia\" in the rows` after asking the
            API for make=aprilia — which the filter guarantees. The real
            question is whether the catalogue HAS rows for each make and
            whether the filter excludes the others."""
            r = api.get(f"/v1/shop/{shop_id}/parts/search", params={"make": make, "limit": 100})
            assert r.status_code == 200, r.text[:400]
            items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
            assert items, f"{make}: no catalogue rows"
            assert all((i.get("make") or "").lower() == make for i in items), \
                sorted({i.get("make") for i in items})

**Verifier verdict — real=False.**

The finding is half-true and misdiagnosed; its load-bearing evidence claim is refuted by execution, and the severity rests entirely on that refuted claim.

WHAT REPRODUCES (the true half, and it is a nit, not a gap):
- Staged file line 194, `test_parts_search_reaches_the_european_rows`, does reduce to `items != []`. `search_parts` filters with `AND make = ?` (/Users/lilquant/Projects/moto-diag/src/motodiag/advanced/parts_repo.py:263-265) and `PartSummary` carries `make` (/Users/lilquant/Projects/moto-diag/src/motodiag/api/routes/parts.py:100), so `any("aprilia" in json.dumps(i).lower() for i in items)` is true of any row the filter can return. I ran it: 4 rows, all serializing `"make": "aprilia"`. (It is not vacuous, though — `q="oil filter"` genuinely constrains, so the test does assert "Phase 239 added an Aprilia oil filter row".)
- All the corpus numbers are exact: parts.json 125 rows / 83 European (ducati 17, ktm 17, bmw 16, aprilia 11, triumph 9, moto-guzzi 9, mv-agusta 4); parts_xref.json 100 rows / 41 European with all seven makes (bmw 12, ducati 10, triumph 7, ktm 5, aprilia 5, mv-agusta 1, moto-guzzi 1); 0 dangling slugs; 0 European rows with an empty oem_part_number. All seven OEM part numbers resolve through `get_xrefs`.

WHAT IS FALSE:

1. The title's "the parts cross-references are never resolved" is wrong. Gate 12's own module-scoped `gate_db` fixture resolves all 100 of them on every run — staged file lines 65-66:
       load_parts_file(PARTS / "parts.json", path)
       load_parts_xref_file(PARTS / "parts_xref.json", path)
   `load_parts_xref_file` calls `add_xref` per row (advanced/parts_loader.py:119-142), and `add_xref` raises on an unresolvable slug (advanced/parts_repo.py:349-353): `raise ValueError(f"add_xref: unknown oem_slug {oem_slug!r}")`.

2. "Nothing in Gate 12 would notice if a Phase 239 slug were renamed and the xref rows stopped resolving — the API search test would still pass" is FALSE, and I disproved it by execution. I copied the two JSON files, renamed one cross-referenced European slug, and ran the loader pair the fixture runs:
       renaming slug: bmw-33117660878-final-drive-seal make= bmw
       RAISED: ValueError add_xref: unknown oem_slug 'bmw-33117660878-final-drive-seal'
   Because `gate_db` is module-scoped and every other fixture depends on it, that ValueError errors out EVERY test in Gate 12, the parts search test included. The gate is loud about exactly the break the finding says it is blind to.

3. "A silent break there is invisible to every other test in the tree" is FALSE. /Users/lilquant/Projects/moto-diag/tests/test_phase239_european_parts.py:128 `test_every_xref_resolves_both_sides` asserts both slugs of all 100 rows resolve — literally the same assertion the recommended fix re-adds as `test_no_xref_row_points_at_a_part_that_does_not_exist`. And :134 `test_the_loader_accepts_everything_end_to_end` loads both files into a real DB and asserts `count(parts_xref) == len(distinct pairs)` with the one known Phase 153 duplicate pinned. Two independent existing guards, plus the gate fixture, on the failure mode the finding calls invisible.

4. Consequently the recommended fix is partly redundant: `test_no_xref_row_points_at_a_part_that_does_not_exist` duplicates test_phase239:128 verbatim in effect, and `_one_xref_per_make()`'s stated rationale ("a renamed slug shows up as a KeyError here rather than as a silently thinner catalogue") is wrong — a renamed slug shows up as a fixture ValueError first, before any test body runs.

Downgrade: what actually remains is a low-severity test-quality nit (one tautological assertion covering one make of seven), not a high-severity MISSING coverage gap. The finding invented the failure mode that justified its severity.

**Verifier's corrected_fix.**

If the weak assertion is worth tightening at all, keep only the two genuinely additive pieces and drop the redundant one. Do NOT add `test_no_xref_row_points_at_a_part_that_does_not_exist` — it duplicates tests/test_phase239_european_parts.py:128, and the gate_db fixture already hard-fails on that condition.

Genuinely additive piece 1 — make the search test discriminate instead of restating the filter (this is the real content of the finding):

    @pytest.mark.parametrize("make", sorted(MAKES))
    def test_parts_search_discriminates_by_make(self, make, api, shop_id):
        r = api.get(f"/v1/shop/{shop_id}/parts/search", params={"make": make, "limit": 100})
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        items = body if isinstance(body, list) else body.get("items", body.get("results", []))
        assert items, f"{make}: no catalogue rows"
        assert all((i.get("make") or "").lower() == make for i in items), \
            sorted({i.get("make") for i in items})

Note this exercises a DIFFERENT code path from the existing test: with `q` empty and no `model`, routes/parts.py:268-276 still takes the `search_parts` branch (the `list_parts_for_bike` branch needs both make AND model), so the LIKE clause degenerates to `%%` and the row count per make is the full catalogue slice. Verified: all seven makes return non-empty and homogeneous.

Genuinely additive piece 2 — the second key space. `get_xrefs` joins on `oem.oem_part_number` (advanced/parts_repo.py:433), NOT on slug, so it is the one thing the fixture's slug-resolution does not cover: emptying or editing a European `oem_part_number` would leave every existing test green while `advanced parts xref` returned nothing. Keep this, but state that rationale rather than the false "renamed slug" one:

    XREF_CASES = _one_xref_per_make()   # as written in the finding; verified all 7 makes

    @pytest.mark.parametrize("make,oem_pn", XREF_CASES)
    def test_an_oem_number_resolves_to_an_aftermarket_equivalent(self, make, oem_pn):
        """get_xrefs keys off oem_part_number, not slug. The gate fixture
        resolves slugs and fails loudly on a bad one; nothing checks that
        the OEM NUMBER a mechanic reads off the box still finds a match."""
        body = json.loads(_run(["advanced", "parts", "xref", oem_pn, "--json"]).output)
        assert body["oem_part_number"] == oem_pn, body
        assert body["xrefs"], f"{make} {oem_pn}: no aftermarket equivalent resolved"

Verified green on the live corpus: aprilia 1A010574 -> 3, bmw 33117660878 -> 2, ducati 19020221A -> 3, ktm 75030088000 -> 3, moto-guzzi 30153000 -> 1, mv-agusta 8000B5425 -> 1, triumph T2017070 -> 4.

This is a medium-at-most improvement, and it should not block the Gate 12 close.


### [REJECTED] (b) MISSING: the four cross-make files are checked for existence, never for their boundaries

- **severity (auditor):** medium
- **file:** `/private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/test_phase240_gate12.py:241`

**Evidence.**

`test_every_cross_make_file_exists` is `assert (K / name).exists()` for the four names. That is the weakest possible statement about phases 236-239 — four empty JSON arrays pass it.

The roadmap records that these four files exist *because* their topics were saturated elsewhere and had to be scoped against the existing corpus: row 236 "GS-911, TuneECU and DDS were each in 3 files, CAN in 14, and 215/220/225/230/235 own each"; row 237 "The row shrank by more than half, and that is the finding — regulator, stator, cam chain were in 12, 57 and 3"; row 238 "the best-sourced phase in the block"; row 239 "`parts.json` had ZERO Aprilia, MV Agusta and Moto Guzzi".

Live shape: european_tooling 6 entries, european_differentials 15, european_intervals ~20, european_parts. european_intervals holds 18 valve-interval figures; the other three hold zero, which is the Phase 238 ownership boundary working. None of that is asserted.

**Auditor's recommended fix.**

class TestTheCrossMakeFilesKeepTheirBoundaries:
        #: Floors from the live corpus at Phase 239. Growth is fine; an
        #: emptied file is not.
        MIN_ENTRIES = {
            "known_issues_european_tooling.json": 5,
            "known_issues_european_differentials.json": 12,
            "known_issues_european_intervals.json": 15,
            "known_issues_european_parts.json": 5,
        }

        @pytest.mark.parametrize("name", CROSS_MAKE_FILES)
        def test_the_file_carries_content_not_just_a_filename(self, name):
            entries = json.loads((K / name).read_text(encoding="utf-8"))
            assert len(entries) >= self.MIN_ENTRIES[name], (name, len(entries))

        @pytest.mark.parametrize("name", CROSS_MAKE_FILES)
        def test_a_cross_make_file_spans_more_than_one_make(self, name):
            """The premise of phases 236-239. A 'cross-make' file whose
            rows are all one marque belongs in that marque's file, where
            `kb list --make` finds it without a text search."""
            makes = {e["make"] for e in json.loads((K / name).read_text(encoding="utf-8"))}
            assert len(makes) >= 3, (name, sorted(makes))

        @pytest.mark.parametrize("name", [n for n in CROSS_MAKE_FILES
                                          if n != "known_issues_european_intervals.json"])
        def test_only_phase_238_prints_intervals(self, name):
            """Ownership, stated as an invariant rather than as a habit."""
            import re
            vi = re.compile(r"(?:valve|shim|clearance)[^.]{0,120}?\b\d{1,3}[,.]?\d{3}\s*(?:km|mi|miles)\b"
                            r"|\b\d{1,3}[,.]?\d{3}\s*(?:km|mi|miles)\b[^.]{0,120}?(?:valve|shim|clearance)", re.I)
            hits = [e["title"][:50] for e in json.loads((K / name).read_text(encoding="utf-8"))
                    if vi.search(_all_text(e))]
            assert not hits, (name, hits)

        def test_no_cross_make_entry_duplicates_a_make_file_title(self):
            """Phases 236-237 shrank against saturation. An identical title
            in both places is that work being undone."""
            cross = {}
            for name in CROSS_MAKE_FILES:
                for e in json.loads((K / name).read_text(encoding="utf-8")):
                    cross[e["title"]] = name
            dupes = []
            for f in EURO_FILES:
                if f.name in CROSS_MAKE_FILES:
                    continue
                for e in json.loads(f.read_text(encoding="utf-8")):
                    if e["title"] in cross:
                        dupes.append(f"{e['title'][:50]} in {f.name} and {cross[e['title']]}")
            assert not dupes, dupes

**Verifier verdict — real=False.**

The finding is wrong on its facts, wrong on its premise, and its fix fails on the live corpus.

1. THE EVIDENCE NUMBERS ARE WRONG. Live counts (json.load over the four files):
   - known_issues_european_tooling.json = 13 entries (finding says "6")
   - known_issues_european_differentials.json = 15 (correct)
   - known_issues_european_intervals.json = 13 (finding says "~20")
   - known_issues_european_parts.json = 11
   The "18 valve-interval figures" in intervals is also unsupported: the finding's own regex matches 8 entries there. (Its "the other three hold zero" claim IS correct — tooling/differentials/parts return 0 hits.)

2. THE PREMISE IS FALSE. "Existence checks do not encode that work" — the work of phases 236-239 IS encoded, in the four per-phase test files that are already in the tree and collected by the default suite (pyproject.toml: `testpaths = ["tests"]`). Every claim the recommended fix wants to add is already asserted there, and more strictly:
   - Entry counts are pinned EXACTLY, not floored: tests/test_phase236_european_tooling.py `def test_thirteen_entries(self, raw): assert len(raw) == 13`; tests/test_phase237_european_differentials.py `assert len(raw) == 15`; tests/test_phase238_european_intervals.py `assert len(raw) == 13`; tests/test_phase239_european_parts.py `assert len(raw) == 11`.
   - Phase 238 interval ownership: tests/test_phase237_european_differentials.py `test_no_valve_interval_figures` — "Phase 238 owns intervals. Scoped to mileages used AS an interval, as at 225B, so an owner's failure mileage passes." That windowed regex is better than the proposed one, which cannot distinguish a failure mileage from a schedule.
   - Title duplication: all four files carry `test_no_title_collides_corpus_wide`, which compares against `K.glob("known_issues_*.json")` — the WHOLE 917-entry corpus, strictly stronger than the proposed check against EURO_FILES only. Verified: zero duplicate titles corpus-wide, so the proposed test adds nothing.
   - Anti-duplication against saturation: test_phase236 `test_no_pads_detail_restated` / `test_no_aprilia_connector_pin_counts_restated`, test_phase237 `test_no_entry_duplicates_what_the_refuter_found_already_present` / `test_does_not_restate_the_generic_charging_file`, test_phase239 `test_no_entry_restates_a_237_differential`.
   I ran all four: 108 passed in 0.55s.

3. "FOUR EMPTY JSON ARRAYS PASS IT" IS FALSE AT THE SUITE LEVEL, AND EVEN INSIDE THE GATE. Emptying any of the four fails the exact-count pin above; it also fails the gate's own `test_documented_count_matches_the_live_seed` (live sum = 917, README "917 curated known issues" — verified equal), and emptying tooling drops Moto Guzzi rows from 8 to 4, failing the gate's `test_moto_guzzi_is_covered_only_by_the_cross_make_phases` (`assert hits >= 5`).

4. THE RECOMMENDED FIX BREAKS THE BUILD. I ran it verbatim against the live corpus (with EURO_FILES/_all_text supplied, see below): 1 failed, 11 passed —
   `AssertionError: ('known_issues_european_intervals.json', 13)` / `assert 13 >= 15`.
   MIN_ENTRIES floors intervals at 15 against a file of 13, and directly contradicts test_phase238's `assert len(raw) == 13`. Any corpus satisfying the fix would fail Phase 238's gate, and vice versa.

5. THE FIX ALSO DOES NOT COMPILE AS WRITTEN. It references `EURO_FILES` and `_all_text`, neither of which is defined anywhere in the staged test_phase240_gate12.py (grep confirms: only MAKES, DTC_MAKES, COMPAT_MAKES, CROSS_MAKE_FILES, _env, _run, _first_code, _compat_rows). Both would raise NameError at collection/run time.

6. `test_a_cross_make_file_spans_more_than_one_make` is semantically unsound even where it passes. `make` is free text — the live values include "All European makes", "BMW, Ducati, KTM, MV Agusta", and "BMW and Ducati have listed adjustments; KTM, Triumph, Aprilia, Moto Guzzi have none". `len({e["make"]}) >= 3` counts distinct STRINGS, so a file of three single-make rows passes while a genuinely cross-make file of two multi-make strings fails. It also cuts against Phase 237's stated design, whose `test_every_entry_is_anchored_to_one_european_make` asserts `e["make"] in MAKES` per entry.

The single true sentence in the finding — that line 241's `test_every_cross_make_file_exists` is only an existence check — describes a gate that deliberately delegates file-shape to the per-phase tests and spends itself on cross-surface agreement through the real CLI/HTTP front doors, exactly as its docstring says. That is scope, not a gap.

**Verifier's corrected_fix.**

No change to the gate is warranted; adding the proposed class would red the suite. If a reviewer still wants the gate to restate file shape rather than delegate it, the only non-conflicting form is to mirror the pins that already exist instead of inventing floors — EXACT_ENTRIES = {"known_issues_european_tooling.json": 13, "known_issues_european_differentials.json": 15, "known_issues_european_intervals.json": 13, "known_issues_european_parts.json": 11} — which merely duplicates tests/test_phase23{6,7,8,9}. Drop `test_a_cross_make_file_spans_more_than_one_make` (make is free text; it counts strings, and Phase 237 anchors each entry to one make by design), drop `test_no_cross_make_entry_duplicates_a_make_file_title` (each phase file already runs the corpus-wide title-uniqueness check, which is a superset), and if the interval-ownership invariant is wanted at gate level, reuse Phase 237's windowed matcher — `for m in re.finditer(r"\d{1,3},\d{3}\s*(km|miles)", text)` with a ±90-char `(valve|service|interval|schedule|due|every)` window — not the proposed pattern, which would flag an owner's failure mileage as a published interval. Note the brief scopes the Phase 238 deferral to known_issues_ktm_adventure.json and known_issues_european_differentials.json only; extending it to tooling and parts asserts an invariant the track never adopted, and would fire the day a legitimate tooling row mentions a service mileage.


---

## Dimension: factcheck

**Auditor summary.** Adversarial fact-check of the ten highest-stakes European claims, all attempted against primary sources on the web (EUR-Lex regulation text, NHTSA recall API Part 573 records, DVSA recall listings, supplier fitment catalogues, manufacturer technical bulletins, and the project's own Aprilia service-manual extraction).

Six of the ten survived intact and are better than their secondary sources: the KTM 950 Super Enduro R overcharging/whistle claim is corroborated almost verbatim by the LC8 compilation and correctly scoped to "All Years SE-R's" (2006-2008); the MV Dragster campaign remedy is exactly right, including the do-not-ride status that NO press coverage carries and only NHTSA's parkIt flag records; the Aprilia nineteen dash-invisible codes list is correct code-for-code and the entry's warning about hyphenation undercounting is itself verified (a naive search returns 18); the KTM Adventure two-cause fuel starvation is confirmed on both causes plus the pump-left/sender-right layout; the BMW hexhead crown-bearing 2010 generation split is confirmed nearly word-for-word; and the BMW "complete unit only is not established" negative holds - no BMW document supports the complete-only claim and individual bearing numbers demonstrably retail.

Four claims are refuted or materially over-scoped. The most serious is the Euro 4 entitlement: the regulation sentence immediately following the entry's quoted material says manufacturers MAY CHARGE for the adapter, and that sentence is present in the project's own scratchpad copy of the regulation. The other three are the classic over-scope failure mode: a flywheel remedy that exists only for the later Aprilia generation asserted across 2009-2020; the Ducati 998 (a Testastretta) listed as a Desmoquattro; and a Moto Guzzi population that omits the one model never factory-updated.


### [CONFIRMED] Euro 4 adapter is NOT free of charge - the regulation says manufacturers may charge for it, and the omitted sentence sits between the two the entry quotes

- **severity (auditor):** critical
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_aprilia_mv_electrical.json`

**Evidence.**

Entry index 3 (source: regulation). Title: "the manufacturer owes you the connector pinout and an adapter, free of charge". fix_procedure: "request the connector pin configuration and the generic-scan-tool adapter from the manufacturer, which the regulation obliges them to supply free of charge and without discriminating against independent operators."

Commission Delegated Regulation (EU) 2018/295, point 3.13, full text: "...the vehicle manufacturer shall make available to test equipment manufacturers the details of the vehicle connector pin configuration free of charge. The vehicle manufacturer shall provide an adapter enabling connection to a generic scan tool. Such an adapter shall be of suitable quality for professional workshop use. It shall be provided upon request to all independent operators in a non-discriminating manner. MANUFACTURERS MAY CHARGE A REASONABLE AND PROPORTIONATE PRICE FOR THIS ADAPTER, taking into account the additional costs caused for the customer by this choice of the manufacturer."

Verified at https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32018R0295 and, decisively, in the project's own evidence file /private/tmp/claude-501/-Users-lilquant-Projects/69bc631b-b059-4654-bf24-20a66d528aa8/scratchpad/32018R0295.txt lines 206-208, which contain the charging sentence verbatim. The entry quotes the sentence before it and the sentence after it and drops the one in between.

Two separate errors: (a) "free of charge" attaches ONLY to the pin configuration and ONLY as an obligation toward TEST EQUIPMENT MANUFACTURERS - not toward the independent workshop the entry addresses as "you"; (b) the adapter carries an explicit right to charge. The entry's own description paragraph gets the split right; the title and the fix_procedure - the two fields a reader acts on - both get it wrong.

**Auditor's recommended fix.**

Restate the title and fix_procedure to match point 3.13: the pin configuration must be supplied free of charge to test-equipment manufacturers; the adapter must be supplied to independent operators on request in a non-discriminating manner, at a price the manufacturer may set so long as it is reasonable and proportionate. Add the omitted sentence to the quoted block in the description so the next reader cannot re-derive the error. Severity of the entry should rise from medium given it is a money claim made to third parties.

**Verifier verdict — real=True.**

Reproduced against the files. Point 3.13 in the project's own evidence file (32018R0295.txt, lines ~200-208) reads, in order: "the vehicle manufacturer shall make available to test equipment manufacturers the details of the vehicle connector pin configuration free of charge. The vehicle manufacturer shall provide an adapter enabling connection to a generic scan tool. Such an adapter shall be of suitable quality for professional workshop use. It shall be provided upon request to all independent operators in a non-discriminating manner. Manufacturers may charge a reasonable and proportionate price for this adapter, taking into account the additional costs caused for the customer by this choice of the manufacturer."

Entry index 3 of known_issues_aprilia_mv_electrical.json (source "regulation", severity "medium") states in its title: "A Euro 4 Aprilia or MV Agusta is not a locked door - the manufacturer owes you the connector pinout and an adapter, free of charge", and in fix_procedure: "For a Euro 4 machine, request the connector pin configuration and the generic-scan-tool adapter from the manufacturer, which the regulation obliges them to supply free of charge and without discriminating against independent operators." Both attach "free of charge" to the adapter, which the regulation expressly permits the manufacturer to charge for; and both address the pinout duty to "you" (the independent shop), when 3.13 owes the free pinout to test equipment manufacturers, not to operators. The entry's description quotes sentences 1, 2 and 4 and does keep the split correct, so the defect is confined to the two action-bearing fields - it is a real contradiction inside one entry, not a difference of scope.

Corroborating: every other surface in the repo gets it right, which rules out a house convention I might be misreading. compat_matrix.json line 1629 (aprilia 2016-2020) says the manufacturer "must publish its pinout free of charge and supply a generic-scan-tool adapter on request"; line 1659 (mv-agusta 2016-2020) says "with a free pinout and a generic-scan-tool adapter owed to independent operators on request". ROADMAP row 235 and docs/phases/completed/235_implementation.md use the same correct scoping. A corpus-wide grep for a free-adapter claim (free adapter | adapter...free | no charge | at no cost across src/) returns this entry's title as the only hit.

One correction to the auditor's narrative, which does not affect the verdict: the charging sentence does NOT "sit between the two the entry quotes". It is the LAST sentence of the block, after "...in a non-discriminating manner", which is the entry's final quoted fragment. The sentence that actually sits between two quoted fragments is "Such an adapter shall be of suitable quality for professional workshop use." The entry drops both.

**Verifier's corrected_fix.**

The recommended fix is right in substance but incomplete on two points, and it must be written to survive tests that already exist.

1) Fix the two fields, and fix BOTH halves of each. It is not enough to move "free of charge" off the adapter - the pinout half is also misdirected. 3.13's free-of-charge pinout duty runs to test equipment manufacturers, so a shop cannot demand a free pinout for itself either; what the shop is owed is the adapter, on request, non-discriminating, at a price the manufacturer may set if reasonable and proportionate. Suggested title (keeps the substring the tests key on): "A Euro 4 Aprilia or MV Agusta is not a locked door - the manufacturer owes you an adapter to a generic tool, though it may charge for it". Suggested fix_procedure opening: "For a Euro 4 machine, request the generic-scan-tool adapter from the manufacturer: it is owed to independent operators upon request in a non-discriminating manner, must be of suitable quality for professional workshop use, and the manufacturer may charge a reasonable and proportionate price for it. The connector pin configuration is published free of charge to test-equipment manufacturers rather than to workshops, so obtain it through a tool vendor, not by demanding it as your own entitlement." Keep the rest of the existing paragraph verbatim.

2) Restore BOTH omitted sentences to the quoted block in the description, not just the charging one. The auditor names only sentence 5; sentence 3 ("Such an adapter shall be of suitable quality for professional workshop use") is the one actually dropped mid-quote, and it is load-bearing in the shop's favour - it is what stops a manufacturer discharging the duty with a token lead. Quoting 1-2-3-4-5 in order also removes the elision that let the error form.

3) Constraints any rewrite must satisfy or it breaks the tree. tests/test_phase235_aprilia_mv_electrical.py pins: title must still contain "locked door" (lines 292, 301, 308 select the entry by that substring) and must stay unique corpus-wide (test_no_title_collides_corpus_wide); description must still contain "free of charge" (line 295 - satisfied by keeping it on the pin-configuration sentence), plus "2018/295" or "44/2014" and "alternative connection interface"; fix_procedure must still contain "narrow", "ABS", "immobiliser", "coding", and the literal regex "type approval requires, not a bench-verified"; no "Forum tip" (source is regulation). The staged Gate 12 test adds nothing that a rewrite would trip - its campaign-number regex (\d{2}V\d{6} | Recall \d{6,7}) does not match any of the restored text, provenance stays "regulation", and the entry count stays 8.

4) Severity: raising medium to high is defensible and nothing pins it, but it is optional and secondary. The correction of the claim is what matters; a correctly scoped entry is no longer a money claim made to a third party.

5) Optional consistency touch, not required: compat_matrix.json lines 1629 and 1659 say "must publish its pinout free of charge" / "with a free pinout" without naming the recipient. Those rows describe the adapter correctly and are not the defect, but appending "(published to test-equipment manufacturers)" to both notes would keep a reader from re-deriving the same misreading from the adapter catalogue. Do not change either row's status, year bounds or adapter_slug - the read-only Euro 4 tiering is the 235 correction and Gate 12's test_euro4_rows_are_read_only_not_incompatible depends on it.


### [CONFIRMED] Aprilia V4 flywheel-first remedy asserted across 2009-2020, but the reduced-magnet flywheel exists only for the later Kokusan family - and the corpus's own sibling entry says so

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_differentials.json`

**Evidence.**

Entry index 5 (severity high, source forum). model: "RSV4 2009-2020, Tuono V4 1000 2011-2015, Tuono 1100 2016-2020", year_start 2009. fix_procedure: "quote the flywheel with the stator rather than the stator alone". parts_needed: "Replacement flywheel of reduced magnet strength". No generation caveat anywhere in the entry.

The supplier whose claim this is scopes it narrower. RMSTATOR's Kokusan reduced-magnet kit fitment is "Aprilia RSV4: 2011-2020, Aprilia Tuono 1000 V4: 2011-2015, Aprilia Tuono 1100 V4: 2016-2020" (https://www.rmstator.com/products/rms900-103848). The early machines have their own, different kit: "Kit Stator + Mitsubishi Flywheel for Aprilia RSV4 1000 R Factory 2009-12 (up to 3413) | Tuono V4 2011 2012 | OEM # 857201 | RMS900-104929" - a Mitsubishi flywheel, not a reduced-magnet Kokusan one.

The corpus already knows this. /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json index 2 states: "the reduced-magnet flywheel that Phase 237 names as the first suspect on a burnt stator exists for the Kokusan family only" and "On the early Mitsubishi family, the aftermarket kit that replaces the original number exists but the reduced-magnet flywheel does not, so the Phase 237 flywheel-first differential applies to the later family only."

The correction lives in a different file from the entry it corrects, and the corrected entry was never amended.

**Auditor's recommended fix.**

Either narrow entry 5's model/year_start to the Kokusan generation, or add the Mitsubishi/Kokusan split to its description and fix_procedure with the same wording the parts entry already uses. At minimum the fix_procedure's "quote the flywheel with the stator" step needs a preceding step: establish which generator family is fitted, because the reduced-magnet flywheel exists for only one of them.

**Verifier verdict — real=True.**

Independently reproduced in three places. (1) known_issues_european_differentials.json index 5 (source forum, severity high) scopes the flywheel-first remedy to "RSV4 2009–2020, Tuono V4 1000 2011–2015, Tuono 1100 2016–2020", year_start 2009, tells the shop to "quote the flywheel with the stator rather than the stator alone", and lists parts_needed[0] "Replacement flywheel of reduced magnet strength" — the file contains neither the string "Kokusan" nor "Mitsubishi", so there is no generation caveat anywhere in the entry. (2) known_issues_european_parts.json index 2 (source service-manual, written two phases later) states the opposite scope in its own description and fix_procedure: "the reduced-magnet flywheel that Phase 237 names as the first suspect on a burnt stator exists for the Kokusan family only" and "On the early Mitsubishi family, the aftermarket kit that replaces the original number exists but the reduced-magnet flywheel does not, so the Phase 237 flywheel-first differential applies to the later family only." (3) Corroboration the auditor did not cite: src/motodiag/advanced/data/parts.json holds the split as catalogue rows — rmstator-rms120-103587-flywheel "Kokusan Improved reduced-magnet flywheel", year_min 2011 / year_max 2020, notes "Maker fitment: RSV4 1000 Factory/R/RF/RR 2011-20, Tuono V4 1000/1100 2011-20. … A UK reseller's GBP 30 is a clearance price and its 2009-2017 title is not the maker's fitment"; against rmstator-rms900-104929-stator "Stator + Mitsubishi-type flywheel kit for the early charging family — replaces 857201", 2009–2012; and OEM aprilia-857201-stator "Flywheel + stator assembly, Mitsubishi type", fiche "RSV4 2009-12, Tuono V4 R 2011". No reduced-magnet flywheel row exists for the early family. So on a 2009–2012 RSV4 the differentials entry instructs quoting a part the corpus's own catalogue says does not exist for that machine, and justifies it on a magnet-strength mechanism that belongs to the other generation. The correction was written into a different file (Phase 239) and the Phase 237 entry was never amended — exactly the defect class the gate already pins for the MV F3 case in test_no_file_still_defers_something_a_later_phase_resolved. Note also that known_issues_aprilia_rsv4.json index 7 already orders family-determination first ("remove the generator cover and establish which family is fitted. The model and year will not tell you"), so the differentials entry is the single entry out of step, not the corpus consensus. One minor overstatement in the finding, which does not affect its validity: search_known_issues_text LIKE-matches description as well as title, so the parts entry is not unreachable by a "stator" search — it just is not the entry that names the remedy part. No test pins entry 5's model, year_start, parts_needed or the flywheel wording, so the entry can be corrected without breaking the suite.

**Verifier's corrected_fix.**

Take the auditor's SECOND option only; its first option (narrow model/year_start to the Kokusan generation) is wrong and would introduce a new false claim.

Why the narrowing option is wrong: the corpus explicitly denies that the split is a clean year boundary. parts.json has the Mitsubishi assembly at 2009–2012 (fiche: "RSV4 2009-12, Tuono V4 R 2011") and the Kokusan reduced-magnet flywheel at 2011–2020 — they overlap in 2011–2012. known_issues_european_parts.json index 2 carries the symptom "Two RSV4s of one year take different parts" and states the engine-number threshold sellers quote is "in no Aprilia document"; parts.json repeats it ("the engine-number split quoted by aftermarket sellers (3413) is NOT in any Aprilia document"). Setting year_start=2011 would encode the aftermarket boundary the corpus refutes, and would also silently delete the 2009–2012 machines from a differential whose SYMPTOM does apply to them — parts index 2's own cause line says "A burnt stator on the early family has a different remedy set from the later one", not "no failure".

Correct edit — keep model/year_start/year_end as they are (the burnt-stator symptom and the inspect-the-flywheel-before-ordering ordering are right for both families) and gate only the REMEDY on family:

1. fix_procedure — make family determination the explicit first step and make the flywheel quote conditional, e.g.: "On a V4 with a burnt stator, remove the generator cover before ordering anything, and use that opening for two things: establish which generator family is fitted — the model year will not tell you and the two do not interchange — and inspect the flywheel for debonded or shifted magnets and heat damage. On the later Kokusan family, quote the reduced-magnet flywheel together with the stator rather than the stator alone, and explain why: the reported cause is upstream of the parts a standard test condemns. On the early Mitsubishi family no reduced-magnet flywheel exists, so the flywheel-first economics do not apply — the replacement there is the flywheel-and-stator assembly for that family. Treat a second stator failure on the same machine as confirmation. …" Two hard constraints when editing this string: keep the existing "Forum tip: owners inspect the flywheel epoxy…" sentence (tests/test_phase237_european_differentials.py::test_forum_entries_carry_a_tip_and_others_do_not asserts Forum tip presence iff source == forum), and keep a first/before/start token (test_every_fix_states_an_order_of_checks).

2. parts_needed — replace "Replacement flywheel of reduced magnet strength" with "Reduced-magnet flywheel — later (Kokusan) family only" and add "Flywheel-and-stator assembly for the early (Mitsubishi) family".

3. description and causes — add the split in the parts entry's own wording ("the reduced-magnet flywheel exists for the Kokusan family only"), and add a cause line such as "The two generator families take different remedy sets, and neither the model year nor a seller's engine-number threshold identifies which is fitted".

4. Do NOT print the 3413 engine number as a threshold in this entry. The corpus records it only as an aftermarket claim with no Aprilia document behind it; naming it here would turn a refuted seller claim into a diagnostic specification. Route to the cover-off inspection instead, matching known_issues_aprilia_rsv4.json index 7.

5. Leave the title unchanged — "the flywheel is the first suspect" remains true for both families (inspection is the first step either way); it is the remedy part that is family-specific. Changing it would also churn the title-collision and Phase 239 stem tests for no gain.

No change is needed in known_issues_european_parts.json or parts.json; both are already correct. Optionally extend the gate's test_no_file_still_defers_something_a_later_phase_resolved with a second case pinning that the differentials Aprilia entry names both generator families, since this is the same stale-correction class it already guards for MV.


### [CONFIRMED] The Ducati 998 is a Testastretta, not a Desmoquattro - it is listed in the Desmoquattro rocker-flaking population in two entries

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_differentials.json`

**Evidence.**

Entry index 12 (severity high). model: "Desmoquattro 16-valve - 851, 888, 748, 916, 996, 998, ST4 and ST4S", years 1988-2004. Repeated in /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json index 4: "916-998 family by aftermarket fitment".

The 998 uses the Testastretta head, not the Desmoquattro. Per https://en.wikipedia.org/wiki/Ducati_Desmoquattro_engine the Desmoquattro line runs 851, 888, 916, 996 and the included valve angle changed "from 40 degrees to 25 degrees" with Testastretta; the first Testastretta was the 996R in 2001, and the 998 "had the Testastretta engine in all 998 models".

The aftermarket fitment claim is also over-stated: Electraeon states its Super Rocker Arms "fit all production Ducati Desmoquatro 748, 916, and 996 motors including 748R and 996SPS" (https://www.electraeon.com/superrockers.html) - the 998 is not in that list either, so the entry's "916-998 family by aftermarket fitment" has no vendor behind it.

**Auditor's recommended fix.**

Remove 998 from both model lists. Consider whether 851/888 belong either: no vendor in the sources fits rockers to them, and the specialist fitment evidence covers 748/916/996 only.

**Verifier verdict — real=True.**

Reproduced at both loci. known_issues_european_differentials.json index 12 (line 343) reads "model": "Desmoquattro 16-valve — 851, 888, 748, 916, 996, 998, ST4 and ST4S" (1988–2004, severity high, source forum), and known_issues_european_parts.json index 4 (line 6) reads "model": "Desmoquattro — Monster S4R 2003–06, ST4 S 2003–05 on the fiche; 916–998 family by aftermarket fitment". The 998 is a Testastretta: Wikipedia's Desmoquattro article states the 998 "had the Testastretta engine in all 998 models" and dates the first Testastretta to the 2001 996R. The corpus already knows this and contradicts itself — known_issues_ducati_monster.json line 40 says "Belt and roller part numbers differ between the 996 Desmoquattro (S4R 2003-2006, and the 916 S4 2001-2003) and the 998 Testastretta (S4R 2007-2008 and S4RS 2006-2008) - order by engine number and engine type, never by the S4R badge." The fitment half also holds, and there is a further inconsistency the auditor did not cite: electraeon.com/superrockers.html says verbatim "Super Rocker Arms fit all production Ducati Desmoquatro 748, 916, and 996 motors including 748R and 996SPS" (no 998, no 851/888), while the corpus's own catalogue row for that vendor — parts.json slug "electraeon-super-rocker-rocker-arm" — carries "model_pattern": "9_6%", year_min 1994, year_max 2002, which matches neither 998 nor 748. So the parts entry's prose over-claims relative to the very row it describes. Nothing pins these strings in tests (test_phase237_european_differentials.py:162 queries "ducati 916 chrome flakes in oil"; test_phase239 has no Electraeon assertion), so a fix is safe. Two caveats on the auditor's framing, which are why the fix needs correcting rather than the finding rejecting: (1) the why_it_matters overstates the diagnostic harm — Testastretta rockers are also chrome-faced and owner reports of flaking on them exist (there is a dedicated ducati.ms thread "Anyone experienced flaking rockers on 998?"), merely far rarer than on Desmoquattro, so the "don't open the gearbox" redirect is not wrong for a 998; the genuinely high-severity consequence is the parts trap, since neither fiche number 20810018A nor the Electraeon set fits a Testastretta and the engine is open by the time that is discovered. (2) The auditor's stated reason for doubting 851/888 is wrong — 851 and 888 are the original Desmoquattro by every source, and vendor silence is not evidence of absence (Electraeon simply does not make a rocker for them).

**Verifier's corrected_fix.**

Do not simply delete 998 from both lists — a bare deletion loses a true fact and leaves three related defects untouched.

1) known_issues_european_differentials.json index 12: change model to "Desmoquattro 16-valve — 851, 888, 748, 916, 996, ST4 and ST4S". Then ADD the Testastretta contrast to the description or fix_procedure rather than dropping it, because it is the part a shop gets wrong: the 998, 999 and 749 are Testastretta, owner reports of flaking rockers exist there too but are markedly less common, and the rockers are a different design with different part numbers — so the cam-cover-before-gearbox redirect still applies to a 998, but the parts route in this entry does not. Sourcing this as an owner report matches the entry's existing source: "forum" (which already carries the required "Forum tip:").

2) Fix year_start in the same entry. 1988 contradicts the entry's own stated cause — chrome quality degrading "after rocker plating was outsourced as production scaled up in the late 1990s". The reported high-incidence population is roughly MY1996–2003; early 851/888 and the 1994–95 916 predate the plating window. Keep 851/888 in the engine family (they are Desmoquattro) but move year_start to 1994 at the earliest, or state the plating-era window in prose and leave the family range alone — do not resolve the conflict by deleting 851/888 on the auditor's vendor-silence reasoning. With 998 gone the top of the range is ST4S, which this corpus itself dates to 2005 in known_issues_european_parts.json ("ST4 S 2003–05"), so year_end 2004 is also short by a year.

3) known_issues_european_parts.json index 4: change the model tail from "916–998 family by aftermarket fitment" to the vendor's actual claim — "748, 916 and 996 by aftermarket fitment (the maker's claim)". The existing causes bullet "Aftermarket fitment claims span engine families the fiche does not" stays accurate and is the reason to print the vendor list exactly. Its year_start of 1994 is only there to reach the aftermarket family and remains defensible; year_end 2006 covers the fiche's Monster S4R and should stay.

4) parts.json, slug "electraeon-super-rocker-rocker-arm": model_pattern "9_6%" excludes the 748 and 748R that the vendor explicitly lists, so the catalogue under-claims where the knowledge entry over-claims. Widen the pattern (or add a sibling row with a pattern token, per the Phase 239 slug-collision fix) to cover 748/916/996 and no more. This is the same failure Phase 239 named as its own key finding — "a catalogue row fails at the fitment pattern, not the part number" — and it should be closed in the same change so the knowledge entry and the row it describes agree.

Severity "high" is correct, but for the parts reason rather than the misdiagnosis reason; if the entry's justification text is carried into the fix commit, state it that way.


### [CONFIRMED] Desmoquattro rocker entry names only the opening rocker and quotes half the job - the vendor says openers and closers both fail, and its four-figure price is for openers alone

- **severity (auditor):** high
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json`

**Evidence.**

Entry index 4 (severity high). Title: "The Ducati Desmoquattro opening rocker arm is discontinued...". description: "aftermarket tool-steel rockers at a four-figure price per set". differentials index 12 fix_procedure likewise says "set the clearances accurately since that is reported to reduce recurrence".

Electraeon's FAQ (https://www.electraeon.com/ducati_rocker_arm_frequently_asked_questions.html) states: "They all fail, intake, exhaust, openers, closers, and on both heads." It gives the mechanism as mechanical rather than a plating-quality lapse: the arms are "cast metal that is plated in the areas that are contacted by the cam shaft" and the "cam shaft impacting the surface of the rocker arm causes the plating to indent into the cast metal material below and fracture." On clearances it says incorrect settings accelerate failure ("will do it faster, possibly in minutes") but does not say correct clearances prevent it - stock-design plated rockers fail regardless.

On price, https://www.electraeon.com/superrockers.html lists "Super Rocker Arms, Set of 8 Openers - $1850.00" with a separate closer set. So the entry's "four-figure price per set" is the openers only; a full engine needs both sets.

Re-chroming pricing does check out as "modest per-arm": forum reports of Megacycle exchange around $89 each and older MBP quotes around $50 each.

**Auditor's recommended fix.**

Change the framing from "the opening rocker arm" to the rocker set, and say plainly that openers and closers both flake on both heads. Price the tool-steel route as two sets. Soften "clearance accuracy reduces recurrence" to what the source supports: incorrect clearances accelerate failure sharply; correct ones do not prevent it on plated rockers, which is the argument for the tool-steel route.

**Verifier verdict — real=True.**

Reproduced independently, on both halves.

CORPUS SIDE (verbatim). known_issues_european_parts.json index 4, severity high, source model-generated, title "The Ducati Desmoquattro opening rocker arm is discontinued, and the replacement is re-plating or tool steel". Its description reads: "The opening rocker arm for the 16-valve Desmoquattro - the part whose hard chrome flakes into the oil, per Phase 237 - is marked discontinued on the fiche for the models it was assigned to. What remains is a choice between two routes with different economics: a specialist exchange re-chroming service at a modest per-arm price, or aftermarket tool-steel rockers at a four-figure price per set." parts_needed is ["Re-chromed exchange rockers or tool-steel aftermarket rockers", "Cam cover gaskets", "Shims to reset clearances"] - nothing tells a reader the tool-steel route is sold as two sets. known_issues_european_differentials.json index 12 (source forum) fix_procedure contains "set the clearances accurately since that is reported to reduce recurrence" verbatim.

SOURCE SIDE (fetched both pages). electraeon.com/ducati_rocker_arm_frequently_asked_questions.html: "They all fail, intake, exhaust, openers, closers, and on both heads." Mechanism is mechanical, not a plating-quality lapse - the arms are "cast from metal that is plated", "The cam shaft not only slides over the rocker arms it also impacts the face of the arms on each revolution", the plating "due to its brittle nature can not withstand impacts". On clearances: "They are going to fail regardless of the valve clearance settings but incorrectly set clearances will do it faster, possibly in minutes." electraeon.com/superrockers.html: "Super Rocker Arms, Set of 8 Openers" at $1,850.00, with a separately listed "Set of 8 Closers". A 16-valve Desmoquattro has 8 openers and 8 closers, so the entry's single "four-figure price per set" covers half the engine's rockers. The re-chroming leg does check out as modest per-arm: Desmo Times/EMSDuc quote $104.99 each exchange, and the corpus's own parts.json note says EUR 90.

ERROR PROPAGATES BEYOND THE FILE THE FINDING NAMES. /Users/lilquant/Projects/moto-diag/src/motodiag/advanced/data/parts.json, slug "electraeon-super-rocker-rocker-arm": description "Super Rocker Arms, tool steel - aftermarket for Desmoquattro chrome-flaking rockers", typical_cost_cents 185000, notes "Maker USD 1,850 per set. Fitment claim is the maker's; not cross-referenced to a Ducati number here because families differ." Same unlabelled opener-set price, and unlike the neighbouring rows this one is not the 0 unpriced sentinel, so it is live to cost queries. A shop pricing the job off the catalogue gets half the parts cost with no hint that a second set exists.

WHAT SURVIVES AS TRUE: (a) the entry states, as a definite description, that the opening rocker is "the part whose hard chrome flakes into the oil" - the specialist says all four types on both heads fail, and even the more conservative community view is openers usually, closers also; (b) the tool-steel price is quoted as one set when a full engine needs two. Those are the two compounding quote errors the finding claims, and both reproduce.

WHAT DOES NOT SURVIVE, and why the fix needs correcting: the finding's third leg (that "clearance accuracy reduces recurrence" misstates the source) is weak. Electraeon says wrong clearances make it fail "possibly in minutes", which supports a recurrence-rate effect; both corpus entries already hedge with "reported to", and neither asserts prevention. The finding also attributes the late-1990s-outsourcing causal story to the parts entry - that text is only in the forum-sourced differentials entry, hedged as "The community attributes it to...", which is within that entry's provenance. And the recommended fix's opening move ("change the framing from 'the opening rocker arm' to the rocker set") would break the one fact here that is well-grounded: parts.json rows ducati-20810018a-rocker-arm and ...--st4 record 20810018A specifically as the OPENING rocker, DISCONTINUED, verified_by service-manual, fiche Monster S4R 2003-06 / ST4 S ABS 2003-05. Nothing in the corpus or the sources establishes that the closing rocker is discontinued, so generalising the title to "the rocker set" swaps a documented availability fact for an unverified one.

No test pins any of this wording (grep over tests/ for rocker, four-figure, Electraeon, 185000, 1,850 returns nothing relevant); the staged Gate 12 test references known_issues_european_parts.json only by filename. Track K rules are unaffected either way: no campaign numbers involved, none of the Phase 231/233/238 deliberate absences touched, provenance unchanged (index 4 model-generated with no "Forum tip:", index 12 forum with one).

**Verifier's corrected_fix.**

Keep the availability claim scoped to the opener; widen only the failure scope and the price. Four edits:

1. known_issues_european_parts.json index 4 - failure scope. Leave the title as is: 20810018A is the opening rocker and it is the part documented as discontinued (parts.json, verified_by service-manual); do not generalise to "the rocker set", which would assert a closer-availability fact nothing establishes. Instead fix the definite description inside the description field. Replace "The opening rocker arm for the 16-valve Desmoquattro - the part whose hard chrome flakes into the oil, per Phase 237 -" with wording that separates the two facts, e.g. "The opening rocker arm for the 16-valve Desmoquattro - the more commonly reported of the flaking rockers, per Phase 237, though the closing rockers flake too and a specialist vendor states all four types fail on both heads -". That preserves the mainstream openers-first picture without adopting Electraeon's "they all fail" wholesale (Electraeon sells both sets).

2. Same entry - price. Change "aftermarket tool-steel rockers at a four-figure price per set" to make the set boundary explicit: openers and closers are sold as separate sets of eight, each four-figure, so a whole-engine tool-steel conversion is two sets. Do NOT print the $1,850 figure in the knowledge prose - Phase 239's discipline puts currency in parts.json (cost 0 sentinel, no-conversion test) and the entry is already qualitative ("modest per-arm price"). The closer set's price is not displayed on the vendor page and must not be invented or extrapolated from the opener price.

3. Same entry - causes and parts_needed. Add a cause line to the effect that openers and closers are separate part families quoted separately, and change parts_needed[0] from "Re-chromed exchange rockers or tool-steel aftermarket rockers" to something that names the count, e.g. "Re-chromed exchange rockers, or tool-steel aftermarket rockers - openers and closers are separate sets of eight". This is where the shop's order actually comes from.

4. parts.json, slug electraeon-super-rocker-rocker-arm - the finding does not mention this row and it carries the same error with a live price. Change description to "Super Rocker Arms, tool steel, set of 8 openers - aftermarket for Desmoquattro chrome-flaking rockers" and extend notes to "Maker USD 1,850 per set of 8 openers; closers are a separate set, priced separately - a whole-engine conversion is two sets." typical_cost_cents 185000 can stay, since it is now correctly labelled as the opener set. Do not add a closer row: no price is published for it, and a 0-sentinel row asserting fitment is not needed to fix the quote error.

On the clearance sentence, correct the finding rather than follow it. Do not soften or delete "reported to reduce recurrence" in either file - the source supports a rate effect ("incorrectly set clearances will do it faster, possibly in minutes"). Add the missing half instead: in known_issues_european_parts.json index 4 fix_procedure, after "which is reported to reduce recurrence of the flaking on plated rockers", append that it does not prevent it, the specialist's position being that the plated-on-cast design fails by impact regardless of clearance - which is the argument for the tool-steel route. That single clause delivers the finding's why_it_matters (the customer who pays for re-chroming may be buying a repeat) without overstating the source.

Optional, separate from this finding and lower priority: known_issues_european_differentials.json index 12 carries "The community attributes it to plating quality after rocker plating was outsourced as production scaled up in the late 1990s". That is hedged and within its forum provenance, so it is not a defect on its own, but its year_start 1988 covers 851/888 machines that predate the attributed lapse, and vendor pages date the OEM chrome-flaking window to roughly 1995-2003. If touched, note the specialist's mechanical explanation alongside the community one rather than replacing it.


### [CONFIRMED] MV swingarm bolt: the entry denies a documented fact - the defect was found when a bolt broke while being tightened to 70 Nm

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json`

**Evidence.**

Entry index 2 (severity critical). description: "a batch received incorrect heat treatment and can fail in service, allowing the swingarm to loosen while riding - NOT, AS IS SOMETIMES DESCRIBED, A BOLT THAT BREAKS WHILE BEING TIGHTENED." causes repeats it: "able to fail in service rather than during tightening". fix_procedure step 4: "understand the failure is in service rather than at assembly, so a correctly torqued bolt is not evidence of safety."

MV Agusta's own chronology, as reported from the Part 573 filing for NHTSA 14V189000: an MV Agusta worker reported that this bolt broke suddenly while attempting to tighten it to the specified 70 Nm torque - that is how the non-conformant heat treatment and quenching was discovered (https://www.motorcyclistonline.com/news/mv-agusta-recalls-certain-2014-brutale-rivale-and-f3-models-potential-swingarm-pin-failure/).

Both things are true: discovered at assembly, recalled because it may fail in service. The NHTSA Consequence field carries only the in-service half - "A failure of the bolt that secures the swingarm pin may allow the swingarm to loosen while riding" - which is presumably where the entry's over-correction came from.

**Auditor's recommended fix.**

Replace the negative with the chronology: the batch was identified after a bolt broke during tightening to the specified 70 Nm, and the recall is for in-service failure. Keep step 4's conclusion; drop "not, as is sometimes described". Everything else in this entry verified clean - see the clean list.

**Verifier verdict — real=True.**

Reproduced independently, and it is worse than the finding states — the false claim is also load-bearing in a passing test and in the ROADMAP record.

1. The text is there, verbatim, in /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_mv_agusta_triple.json, entry index 2 (severity "critical", title "Two MV triple recalls are do-not-ride..."):
   - description: "...a batch received incorrect heat treatment and can fail **in service**, allowing the swingarm to loosen while riding — not, as is sometimes described, a bolt that breaks while being tightened."
   - causes[3]: "A swingarm pin securing bolt batch with incorrect heat treatment, able to fail in service rather than during tightening"
   - fix_procedure step 4: "...understand the failure is in service rather than at assembly, so a correctly torqued bolt is not evidence of safety."

2. The denied fact is documented. motorcycle.com's report of the campaign states directly: "While securing the swingarm pin, a screw broke while being fastened to the prescribed torque of 70 nm (51.6 ft-lb.)" — detected March 2014 by an MV Agusta factory worker during assembly, on machines built 18 Dec 2013 – 10 Mar 2014, root cause "the incorrect heat treatment and quenching process". A second independent search source gives the same chronology (worker, sudden break at the specified 70 Nm, non-conformant heat treatment and quenching). Both halves are true: found at assembly, recalled for in-service failure. The entry keeps the second and denies the first.

3. This is not a scope difference — it is a positive false claim. causes[3]'s "rather than during tightening" asserts a failure envelope that excludes exactly the event that produced the campaign, and the description names the accurate description in order to reject it. A technician holding a snapped bolt off a torque wrench at book figure, on a machine in the build window, is told by this entry that he is not looking at the campaign.

4. The error is deliberate and recorded, which is why the auditor's fix is incomplete. docs/ROADMAP.md row 233 states it as a phase decision: "A second correction on the same entry: the swingarm pin bolt fails **in service** from incorrect heat treatment, not while being tightened." And tests/test_phase233_mv_agusta_triple.py:109 pins it — test_the_swingarm_bolt_fails_in_service_not_at_assembly, docstring "Also corrected: the failure is a heat-treatment defect showing up in service, not a bolt snapping while being torqued." The suite is green today (30 passed). The likely origin is as the auditor guessed: the NHTSA Consequence field carries only the in-service half.

**Verifier's corrected_fix.**

The direction is right; the fix as written is incomplete in three ways and has one silent trap.

(a) causes[3] must be rewritten too, not just the description and step 4. "able to fail in service rather than during tightening" is the flattest false statement in the entry — the batch demonstrably failed during tightening. Replace with something like: "A swingarm pin securing bolt batch with incorrect heat treatment and quenching — weak enough to snap at the specified assembly torque and weak enough to fail later in service".

(b) The shipped test must change in the same edit, or the correction is cosmetic. tests/test_phase233_mv_agusta_triple.py:109 asserts that every match of `break\w* (?:while|during) (?:being )?tighten` in the entry is preceded within 90 chars by "not" / "rather than" / "sometimes described" — i.e. the test actively forbids stating the true chronology in the natural present tense. Its docstring asserts the wrong doctrine outright. Trap to avoid: the auditor's own suggested phrasing "a bolt broke during tightening to the specified 70 Nm" scores ZERO matches against that regex (`break\w*` does not match "broke") — I checked. So the fix would land, the test would stay green, and a test asserting a false fact would survive to block the next correct rewording. Delete or invert that third assertion and rewrite the docstring; keep the "heat treatment" and "in service" assertions, and add one asserting the assembly-discovery half is present so the correction cannot be silently reverted. docs/ROADMAP.md row 233's "not while being tightened" clause is likewise now a wrong record.

(c) Step 4's conclusion survives but its stated reason does not. "the failure is in service rather than at assembly" is the false premise; the sound version is: a bolt from this batch that reached spec torque without breaking is still not evidence of safety, because the same defect fails in service. Add the positive diagnostic the entry currently deletes: a bolt that snaps on the wrench at the specified torque on a machine in the build window is the campaign presenting itself — do not fit another bolt from stock, check the frame number.

Constraints the rewrite must respect: no campaign or recall reference number (Phase 231; test_no_campaign_number_appears greps `\b\d{2}V\d{3}\b`), so write the chronology without "14V189000" and keep the frame-number routing. Leave source as "service-manual" and add no "Forum tip:" — the chronology comes from the manufacturer's own Part 573 defect chronology, which is inside the "road-safety regulator's own campaign records" the description already cites; do not re-source it to the press article. 70 Nm is not on the deliberate-absence list and no test bans it, but present it as the figure the factory bolt broke at, not as a repair torque, since the remedy under the open campaign is dealer replacement.


### [CONFIRMED] BMW ELAST belt: the cited reference does not support "tensioning it destroys it", and the entry withholds the 116mm figure that is the actual instruction

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_differentials.json`

**Evidence.**

Entry index 1 (severity medium). Title: "...tensioning the stretch-fit one destroys it". description: "Treating an ELAST belt like a poly-V and adjusting it damages it." fix_procedure: "there is no adjustment to perform and attempting one is the failure."

The independent BMW technical reference the entry describes is largiader.com/articles/altbelts/, which catalogues both belts by designation and part number as the entry says. It establishes: poly-V "used only on Oilheads (1993 through 2003 50A alternators, and all 40A alternators)", ELAST "introduced in July 2003 (2004 models)"; the ELAST "is set to a fixed length" and "At no point is there any assessment of tension"; "116mm between pulley flanges"; the freewheel pulley behaviour ("if the pulley slows down... the alternator will continue to spin"); and "Since the distance between the pulleys doesn't change, there is no need to re-tension this belt during its life."

It carries no warning about damage from tensioning. The documented ELAST hazard in the wider sources is damage during INSTALLATION - prying it on without the tool - not applying a tensioning procedure to a fitted belt.

Secondary: the entry's poly-V scope is "Oilhead 1993-2003"; the source says poly-V also covers ALL 40A alternators irrespective of year.

**Auditor's recommended fix.**

Restate as what the source supports: the ELAST is set to 116mm between pulley flanges and has no tension check or scheduled re-tension at any point. Move the real hazard into the fix_procedure - the belt is damaged by prying it on without the installation tool. Add "and all 40A alternators" to the poly-V scope.

**Verifier verdict — real=True.**

Reproduced on both sides.

FILE (known_issues_european_differentials.json, entry index 1, source "model-generated"). Title: "BMW boxer alternator belts come in two incompatible types, and tensioning the stretch-fit one destroys it". description: "Treating an ELAST belt like a poly-V and adjusting it damages it." causes[1]: "The ELAST belt is set by length and runs a freewheeling pulley, so applying a tensioning procedure to it damages it". symptoms[1]: "Belt failed shortly after being adjusted". fix_procedure: "On an ELAST belt, fit it by the specified length between pulley flanges and leave the tension alone thereafter — there is no adjustment to perform and attempting one is the failure." model: "Oilhead 1993–2003 poly-V; 2004-on 50A and all hexhead R1200 ELAST".

SOURCE. The reference the description points at ("an independent BMW technical reference that catalogues both belts by designation and part number") is unambiguously largiader.com/articles/altbelts/ — it carries, in one place, every structural fact the entry uses: two belt types with designations and part numbers, the July-2003/2004-model changeover, fixed length between pulley flanges, the freewheeling alternator pulley, and the poly-V re-tension schedule "starting with the R1150". The string "largiader" appears nowhere in the repo, so the entry is the only link, but the fingerprint is exact. Fetching it confirms the auditor verbatim: poly-V is "used only on Oilheads (1993 through 2003 50A alternators, and all 40A alternators)"; "At no point is there any assessment of tension"; "Since the distance between the pulleys doesn't change, there is no need to re-tension this belt during its life"; "any method of spacing the pulleys properly (116mm between pulley flanges) will accomplish the goal". It contains no warning that tensioning or adjusting an ELAST belt damages it.

The defect is worse than "unsupported", it is inverted on the models the entry scopes. For the 2004-on 50A oilhead the source says "the alternator is still free to slide up and down, and this is how the new belt is installed" and "the two pulleys are pushed apart to a preset distance using a special tool, then the alternator is bolted down tight". So on that machine there IS an alternator-position adjustment to perform, it is the specified procedure, and it has a number — while the entry tells the mechanic "there is no adjustment to perform and attempting one is the failure" and declines to print the number it just gestured at ("the specified length between pulley flanges"). The hexhead is the opposite case: "the alternator is simply bolted to the bike without any provision for adjustability", so there the warning is about a control that does not exist.

This is the same defect Phase 237 removed from a sibling entry in this very file: the KTM water-pump "weep hole" hook was attributed to a page where the word does not occur, and 237_implementation.md records "It is gone; the entry says only what the source supports". test_ktm_water_pump_carries_no_weep_hole_claim pins that standard for one entry; the belt entry violates it and nothing pins it. docs/ROADMAP.md row 393 repeats the unsupported claim ("tensioning the ELAST stretch-fit destroys it"); implementation.md row 468 states it correctly and without the damage claim ("a tensioned poly-V and a fixed-length ELAST stretch-fit that is never re-tensioned"), so the two docs already disagree.

Secondary scope claim also holds verbatim: the source's poly-V covers all 40A alternators irrespective of year, the entry's poly-V half stops at 2003.

Nothing exempts this. The 116mm is a fitting dimension, not a valve interval, so the Phase 238 deferral this file owes does not cover it, and it is not on the Track K deliberate-absence list. The staged Gate 12 test does not touch the entry.

**Verifier's corrected_fix.**

The diagnosis is right; the recommended fix repeats the defect in one place and stops short in three others.

1. DROP "the belt is damaged by prying it on without the installation tool". The auditor sources that to "the wider sources" and names none — it is a second unsourced hazard swapped in for the first, in an entry whose description claims to rest on one named reference. Say instead what the reference does support: the ELAST is fitted and removed by walking it over the pulley with a special tool while the engine is turned. That is a procedure note, not a damage claim, and it needs no source the entry does not have.

2. SCOPE THE 116mm — do not state it flatly as "the ELAST is set to 116mm". The source puts it on the 2004-on 50A oilhead only, where the alternator "is still free to slide up and down": pulleys pushed apart to the preset distance with the tool, then bolted down, 116mm between pulley flanges, no tension assessed. On the hexhead the alternator "is simply bolted to the bike without any provision for adjustability" — nothing to set, and printing 116mm as a hexhead spec would be a new error. The differential the entry is for is exactly this split, and it is currently collapsed.

3. THE FIX MUST REACH THE TITLE, symptoms AND causes, not just description + fix_procedure. The claim lives in four fields. Title (the loudest, and it is what ROADMAP row 237 quotes): replace "…and tensioning the stretch-fit one destroys it" with the real contrast, e.g. "BMW boxer alternator belts come in two incompatible types: one is re-tensioned on a schedule, the other is set to a fixed length and never tensioned". Keep "BMW" in the title — tests/test_phase237_european_differentials.py::test_every_entry_is_anchored_to_one_european_make asserts make in title, and test_no_title_collides_corpus_wide requires it stay unique. causes[1] ("…so applying a tensioning procedure to it damages it") must be restated as what actually goes wrong: moving the alternator off the 116mm setting puts the belt at a length it was not fitted to. symptoms[1] "Belt failed shortly after being adjusted" is an observation that exists only if the damage claim is true — drop it or replace with a symptom of the real error (e.g. "Alternator moved during a habitual re-tension"); the test caps symptoms at 55 chars with no trailing period. causes[2] ("A shop that has re-tensioned poly-V belts on earlier boxers will do the same to a later one") is the genuine differential and stays.

4. KEEP THE POLY-V INTERVAL UNNUMBERED. The source gives 6,000 miles for the R1150-onward re-tension. Do not add it: test_no_valve_interval_figures matches \d{1,3},\d{3} (km|miles) within 90 chars of "schedule"/"interval"/"every" and would fail, and Phase 238 owns intervals in this file. The existing wording "re-tensioned at a scheduled interval from the R1150 onward" is correct as it stands.

5. MODEL FIELD, both halves, per the source: poly-V = oilheads only, 1993–2003 50A and all 40A; ELAST = 2004-on 50A and all hexhead. The auditor names only the 40A half.

6. LEAVE source AS "model-generated". An independent technical reference is not one of the six provenance values, and the entry must not be promoted to "service-manual" on the strength of carrying a figure from it. It must also gain no "Forum tip:" — test_forum_entries_carry_a_tip_and_others_do_not asserts the tip iff source == forum. Keep an ordering word in fix_procedure ("before" is already there) for test_every_fix_states_an_order_of_checks, and keep the description's "Drawn … from" phrasing for test_every_entry_says_what_it_is_drawn_from.

7. FIX THE DOC THAT REPEATS IT. docs/ROADMAP.md row 237 (line 393) carries "tensioning the ELAST stretch-fit destroys it" and must be amended with the entry, or the roadmap keeps asserting what the corpus no longer says. implementation.md row 468 already reads correctly and needs no change. src/motodiag/advanced/data/parts.json ("ELAST: fitted by length, never re-tensioned (Phase 237)") and known_issues_european_parts.json entry 9 are consistent with the corrected framing and need no change.


### [CONFIRMED] Moto Guzzi 8V population omits the 1200 Sport 8V - the one model whose engine was never factory-updated to rollers

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_differentials.json`

**Evidence.**

Entry index 8 (severity CRITICAL) model: "1200 8V - Griso 8V, Stelvio, Norge - built before the mid-2012 change". Same three-model list in /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json index 0.

The affected population includes the 1200 Sport 8V. Per the GuzziTech reference thread (https://www.guzzitech.com/forums/threads/everything-you-ever-wanted-to-know-about-the-1200-8v-engine-tappet-failure-but-were-afraid-to-ask.17282/): models are Stelvio, Griso, Norge and 1200 Sport, and the 1200 Sport used an A7 engine designation that was never factory updated.

The cut-offs themselves check out and are tighter than "mid-2012": Stelvio (AC) after AC12596 as of 03/12/2012; Griso (A8) after 13524 as of 04/12/2012; Norge (AA) after 12214 as of 04/18/2012.

Two further corrections to the same pair of entries. Coverage is understated: the manufacturer offered FULL coverage (parts and labour) where the customer could demonstrate complete authorised-dealer service history, and PARTS-ONLY coverage where the problem was dealer-confirmed but the history was incomplete. The entry says only "covered the roller conversion where full dealer service history existed", which reads as all-or-nothing. And availability: the conversion kits are reported no longer in production and NLA as of end-2025 - the parts entry hedges this as "unresolved", but the critical entry's parts_needed still lists "Roller tappet conversion camshaft kit" as the remedy without qualification.

The mechanism and the bulletin claims verify: DLC hard coating on flat tappets; Technical Bulletin 020-2013 and 002-2014; roller components fitted only where timing-system work is done for bucket-tappet wear, with mandatory photographic evidence of wear - which is the entry's "no preventive operations" and "documented wear claim", both sound.

**Auditor's recommended fix.**

Add the 1200 Sport 8V (A7) to both model lists, with the note that it was never factory-updated so every A7 is a flat-tappet build. Split the coverage sentence into the two documented tiers. Tighten "mid-2012" to the three per-model cut-offs, which the corpus already sources. Carry the parts entry's availability caveat into the critical entry's parts_needed.

**Verifier verdict — real=True.**

Reproduced on all three counts.

(1) The omission is real. known_issues_european_differentials.json index 8 has `"model": "1200 8V — Griso 8V, Stelvio, Norge — built before the mid-2012 change"` and its description opens "The 8V engines in the Griso 8V, Stelvio and Norge built before a mid-2012 design change use flat tappets…". known_issues_european_parts.json index 0 carries the same three-model list, `"model": "1200 8V — Griso 8V, Stelvio, Norge"`. Grepping every JSON under src/ for "1200 Sport" returns zero hits — the model is nowhere in the corpus, so this is a gap, not a scope split into another entry. The only other Guzzi entries (known_issues_european_intervals.json) are V85/V100 and unrelated.

(2) The external claim holds. The cited GuzziTech thread states of the 1200 Sport that A7-engined bikes "were never included in the rollerising updates", and carries the cut-offs verbatim as "Stelvio - AC - After AC12596 - 03/12/2012 / Griso - A8 - After 13524 - 04/12/2012 / Norge - AA - After 12214 - 04/18/2012". So the model whose every example is a flat-tappet build is the one the critical entry does not name, while its instruction is "Establish from the engine number whether the build is flat-tappet or roller" — on an A7 there is nothing to establish.

(3) The coverage tiers check out and the differentials entry does read all-or-nothing: it says only "the manufacturer is reported to have covered the roller conversion where full dealer service history existed", where the source gives two tiers — complete history "free of charge, both the parts and labor", incomplete history parts free with the owner paying labour.

The auditor's supporting claims that I could check all survive: the mechanism, the "no preventive operations" rule and the documented-wear requirement are corroborated by the parts entry and by parts.json rows moto-1a002060/1a002063/1a002082, whose notes name bulletins 020-2013 and 002-2014. No test blocks the correction: the Gate 12 deliberate-absence checks cover only the conversion COST on tappet rows, and Phase 237's test_guzzi_entry_prints_no_currency_figure only bans currency figures and requires the phrase "engine number" to remain.

The recommended fix is right on the population and the coverage tiers but wrong in two of its four parts — see corrected_fix.

**Verifier's corrected_fix.**

Keep parts 1 and 2 of the fix, drop part 3, and weaken part 4.

A. Add the 1200 Sport 8V — but do not append it inside the existing qualifier. The differentials `model` field ends "— built before the mid-2012 change". Appending "1200 Sport" inside that clause creates a new error: it implies a late-built Sport is safe, when no Sport was ever factory-rollered and 2012 was its last year of manufacture. Restructure instead, e.g. "1200 8V — Griso 8V, Stelvio and Norge built before the 2012 change, plus every 1200 Sport 8V (A7 engine), which was never factory-updated". Make the same change to the description's opening list and to the parts entry's `model`.

B. Short-circuit the fix_procedure for A7. The current text says "On any pre-2012 8V Guzzi… Establish from the engine number whether the build is flat-tappet or roller." Two defects: the "pre-2012" gate excludes 2012-built Sports, and the establish-step has no answer on an A7. Say that an A7 prefix ends the question — it is a flat-tappet build — and keep the literal phrase "engine number" in the entry, because tests/test_phase237_european_differentials.py::test_guzzi_entry_prints_no_currency_figure asserts it is present.

C. Split the coverage sentence in the DIFFERENTIALS entry only. That entry is `"source": "forum"`, which is the right home for a forum-sourced two-tier goodwill account. Do NOT push it into the parts entry: that entry is `"source": "service-manual"`, drawn from the two Piaggio bulletins, and importing a forum claim into it either makes the source field false or forces it to "forum", which under rule 3 would then require a "Forum tip:" and would degrade a bulletin-sourced entry. The parts entry already documents a parts-free route on its own axis ("out-of-warranty parts were made free through a help-desk ticket route") — leave that as the bulletin's statement and let the two entries carry the two provenances.

D. Do NOT print the three per-model cut-offs. The auditor's claim that "the corpus already sources" them is wrong — the corpus deliberately does not print them, saying only "The owner community has documented the build cut-offs precisely by engine number", which is Phase 231's route-the-reader pattern applied to an engine number instead of a frame number. Printing them would (i) turn a forum record into what reads as a manufacturer cut-off, the same failure mode the MV shim-diameter rule exists to prevent; (ii) import format-ambiguous dates — 03/12/2012 and 04/12/2012 are only disambiguated by 04/18/2012 being US order, so a UK reader reads the Stelvio cut-off as 3 December, exactly the class of mangling that got the NZD-as-USD cost figure removed at Phase 237; and (iii) propagate a source inconsistency, since the Griso row is "After 13524" with no A8 prefix while the Stelvio row is "After AC12596". "Mid-2012" is not the defect here — the defect is that the Sport was being swept under a date question that does not apply to it, and A above fixes that.

E. Soften the availability carry-over. Add the availability caveat to the differentials entry's parts_needed (currently "Roller tappet conversion camshaft kit where the flat-tappet build has failed" with no qualification) — correct, and that entry is forum-sourced, so it may attribute the community's end-2025 no-longer-in-production/NLA report AS a report. But do not upgrade "unresolved" to a flat NLA in the parts entry or in parts.json: those are service-manual-sourced, their evidence is "fiche 'contact'" plus one sold-out retailer listing, and a definite NLA rests only on forum posts. "Confirm availability before quoting a date" is the honest instruction on that surface.

F. Change nothing in parts.json. The three roller-kit rows already carry `"model_pattern": "%1200%"`, which matches a 1200 Sport, and the bulletins select the kit by engine rather than by model — so the catalogue is already correct and only the two knowledge entries mislead. Worth stating explicitly so the catalogue is not "fixed" into a narrower three-model pattern.


### [REJECTED] BMW final drive: the negative holds, but the entry over-states which parts have industrial equivalents and prices a job it does not scope

- **severity (auditor):** medium
- **file:** `/Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json`

**Evidence.**

Entry index 3 (severity high). I tried hard to refute the negative and could not: no BMW document establishing complete-unit-only supply exists in any source found, and individual numbers plainly retail. BMW 33 11 7 722 799 sells at $89.99 against a $144.05 BMW list (https://www.euromotoelectrics.com/product-p/fdbearing799.htm). The UKGSer bearing thread (https://ukgser.com/forums/archive/index.php/t-300631.html) lists TRA20235 crown-wheel ball bearing at GBP 48.39 with the standard equivalent 6013 2RS-B-L195-R8-20 (100x65x18) at about GBP 29. The core claim is correct and saves an order of magnitude.

Two corrections. (1) The entry's causes say the bearings and seals "have dimension-matched industrial equivalents". The same source says only one of the two crown-wheel-shaft bearings is standard: the needle/roller bearing TRA74121 is "non-standard", the right-hand seal TRA79862 (60x75x8) is "non-standard", and the large seal is a non-standard thickness - "BMW being 9mm thick, with a std seal in the same OD and ID being 10mm thick". The forum tip does hedge ("treat that as approximate and confirm the seal arrangement") but the causes field states it flatly and plurally.

(2) The entry frames the dealer refusal as "One owner's dealer account of being refused internals in a particular year... an owner report about one dealer, not a policy". Multiple owners across BMW MOA, UKGSer and r1200gs.info report dealers refusing, one named (Vines, Guildford). The refusals also have a stated technical basis: the rebuild needs correct heat and press procedure and correct-size shims to set play and tolerance, and a botched press damages the unit.

**Auditor's recommended fix.**

Keep the negative - it survived the attempt. Narrow the causes claim to the one bearing that has a standard envelope, and state that the needle bearing and both seals are non-standard, naming the 9mm/10mm seal thickness trap. Add a fix_procedure line that the quote must include shim selection and press/heat setup, not just the bearing and seal, since that is the actual reason for the complete-unit advice.

**Verifier verdict — real=False.**

Both corrections fail against the actual text of entry index 3 in /Users/lilquant/Projects/moto-diag/src/motodiag/knowledge/seed/knowledge/known_issues_european_parts.json.

(1) The load-bearing correction misquotes the file twice. The finding says: "The entry's causes say the bearings and seals 'have dimension-matched industrial equivalents' ... the causes field states it flatly and plurally." The causes field is, verbatim and in full: ["The 'complete unit only' claim circulates without a BMW document behind it", "Individual bearing and seal numbers exist and are retailed independently", "A single dealer's refusal in one year is reported as manufacturer policy", "The two quotes differ by more than an order of magnitude"]. The substring "industrial" does not occur in causes at all (verified programmatically). The phrase lives in the description, and its subject is not "bearings and seals" — it is two specifically named bearings: "the crown-wheel bearing and the wheel-side bearing **carry individual BMW part numbers**, are stocked by independent retailers at two-figure prices, and have dimension-matched industrial equivalents." No seal is ever claimed to have an industrial equivalent anywhere in the entry.

The finding's own cited source does not refute the narrowed claim it actually made. The finding reports that the crown-wheel ball bearing TRA20235 has the standard equivalent 6013 2RS-B-L195-R8-20 — i.e. it confirms the first of the two bearings the entry names. The items the source calls non-standard (the needle/roller bearing TRA74121, the seals TRA79862 and the 9mm-vs-10mm one) are items the entry never claims equivalents for. The only causes bullet touching seals is "Individual bearing and seal numbers exist and are retailed independently" — a claim about part numbers existing and retailing, which the finding itself corroborates by citing TRA79862 as a seal number.

Consequently the harm story in why_it_matters — "a mechanic who reads 'bearings and seals have industrial equivalents' and orders a 10mm standard seal against BMW's 9mm one has built a leak into a final drive" — is built on a sentence the entry does not contain. The entry's fix_procedure scopes the substitution to one bearing and then explicitly warns against exactly that move: "owners report that the wheel-side bearing's dimensions match a common industrial deep-groove bearing, which is a fallback when the BMW number is on back-order; treat that as approximate and confirm the seal arrangement." The finding acknowledges this hedge and then discounts it by attributing a flat claim to the wrong field.

(2) The "prices a job it does not scope" charge is a difference of scope, and the corpus already carries the missing half. known_issues_european_parts.json is the Phase 239 parts-sourcing file (ROADMAP row 239: "'Pricing' was already refuted as generic at 237, so this became rows a catalogue can hold"), and this entry is a supply negative — its verbatim ask is "Quote the bearing and seal by their individual part numbers before quoting a complete final drive". The rebuild reality the finding says is missing is stated in the diagnostic entry for the same failure, known_issues_bmw_r_series.json entry 0 ("Final drive crown-wheel bearing failure — hexhead R1200GS/RT/R", severity critical, estimated_hours 4.0), step 4: "the final drive must be disassembled for bearing and seal replacement — this is a press job and most shops send the unit out or fit an exchange unit." A reader is not left believing this is a bolt-in job.

The remaining sub-claim — that multiple owners across BMW MOA, UKGSer and r1200gs.info report refusals, versus the entry's "One owner's dealer account ... an owner report about one dealer, not a policy" — is quoted accurately from the file but is not reproducible from anything in the repo, and the finding supplies only one URL, cited for bearing dimensions rather than for a chorus of refusals. Even taken at face value it does not touch the entry's actual assertion, which is that no BMW document establishes complete-unit-only supply and that a dealer refusal is not manufacturer policy — a negative the finding itself concedes survives.

**Verifier's corrected_fix.**

No change is required, and the recommended fix should not be applied as written — it would edit a field (causes) that does not contain the sentence it targets, and would narrow a claim that is already narrow. If a maintainer wants the one defensible residual improvement, it is small and cosmetic, not the medium-severity rewrite proposed: append a pointer in fix_procedure to the existing rebuild entry, e.g. "the strip itself is a press job — see the crown-wheel bearing entry in the BMW R-series file — so a parts quote is not a job quote". That keeps the parts/diagnosis split the file was built on instead of duplicating the press caveat.

Explicitly do NOT adopt the "naming the 9mm/10mm seal thickness trap" part of the recommendation. Those figures, and the 60x75x8 seal envelope, come from a forum archive thread; printing them as flat specification in a parts row is the exact failure mode this track has repeatedly guarded against (the Phase 234 MV Agusta 7.48mm shim rule: an owner report may be described as an owner report but never printed as a specification). If the seal-thickness hazard is worth stating at all, it belongs inside the existing "Forum tip:" clause as an owner report and without printing the dimensions — the clause already discharges the duty with "confirm the seal arrangement". Note also that this entry is source "forum" and is bound by tests/test_phase239_european_parts.py::test_forum_tips_only_on_forum_entries and ::test_no_campaign_numbers_and_no_currency_figures, and that ::test_the_negative_findings_stay_negative pins "not established" in the title — any edit must keep the "Forum tip:" marker, add no currency figure, and leave the title's negative intact.

