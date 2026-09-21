# Phase 254 — Small-displacement CVT diagnostics: the layer three rows left alone

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-21

---

## Goal

Row 254: "Small-displacement CVT diagnostics — belt wear, variator/clutch
bells, roller weights, kickstart backup." This is a **generic layer**, in
the shape 246–249 used for Track L: the concept written as *what the
mechanism does* and *how each maker shows it*, anchored per document, with
the absences recorded as content. Rows 251, 252 and 253 wrote the machines
and each deliberately left this layer alone — their test files forbid
`variator`, `roller weight`, `clutch bell` and `driven pulley` in their own
rows, precisely so that 254 could own them.

## Step 0 — findings

Measured against the live database (1033 rows) on 2026-09-21.

**S0-1. The layer is empty, and the vocabulary is the proof.** Across 1033
rows: `roller weight` 0, `clutch bell` 0, `drive face` 0, `torque driver`
0, `CVT` 1, `variator` 1, `centrifugal clutch` 1, `belt width` 1. The one
CVT row and the one variator row are the same Piaggio row 251 shipped.

**S0-2. A fourth consecutive substring collision, and this one matters for
the row's own subject.** `LIKE '%roller%'` returns 62 rows — **33 of them
are *controller***, from Track L's motor-controller work, and 7 more are
roller bearings, roller rockers and roller tappets. Only 16 use *roller* as
a standalone word, and none is a CVT roller weight. `LIKE '%kick%'` returns
five rows and **two are kickstand switches**; the other three are kick-start
on motorcycles (DR-Z400, DR650, SR400/500). **No scooter kickstart row
exists.** 251 met this as *grommet*, 253 as *symptom*, *system* and
*genuine part*; it is now a reliable property of this corpus rather than an
accident.

**S0-3. "Drive belt" names three unrelated components, and retrieval cannot
separate them.** Searching the corpus for `drive belt` returns eight rows:
**five final-drive or other, two alternator, one CVT.** A Harley final-drive
tensioner, a BMW oilhead alternator belt and a Piaggio CVT belt arrive in
one result set, and the CVT row is last. This is the strongest argument for
the row: the generic layer is where the distinction can be named.

**S0-4. Much of the evidence is already gathered, and was scoped out of
251–253 on purpose.** Piaggio's published belt limits are shipped (minimum
21.5 mm against a 22.5 ± 0.2 mm standard, with a tooth-root cracking
criterion that needs no measurement). Yamaha's 50 cm3 belt interval (6,250
mi / 10,000 km) and the Zuma 125's belt width and limit (22 mm, limit 19.8
mm — **in the service manual only, in none of twelve owner's manuals**) are
in the research record but unshipped. Honda's PCX V-BELT indicator (8,000
mi / 12,000 km, resettable) is shipped as a machine fact. Kymco's Like
interval ("Inspect every 5000km, replace every 20000km") and the Agility
grid's single belt inspection at 4,300 miles are gathered and unshipped.
SYM's Symba **has no belt row at all — it is chain drive.** So a large part
of this phase is composition rather than discovery, and the sweeps should be
told what is already in hand.

**S0-5. A pattern is already visible in that evidence and needs testing, not
assuming.** Of the makers looked at so far, only Piaggio publishes a belt
wear limit in an owner-reachable document, and Yamaha publishes one only in
a service manual. Every other maker publishes an *interval* and no *limit*.
If that holds, it is the layer's central finding — and it is exactly the
kind of tidy claim the last three phases have taught me to hand to a
refuter rather than to trust.

**S0-6. The row's boundaries are the rest of the track.** 255 is
"Twist-and-go vs manual small bikes", 256 "Scooter electrical", 257
"Small-engine carb service", and **258 is Gate 14**, which will query
scooter → CVT + electrical + carb end to end. So 254 owns the CVT
mechanism and must leave the twist-and-go comparison, the electrical layer
and carburettor service alone — and must be *reachable* by 258, which is a
constraint on how it is keyed as much as on what it says.

**S0-7. No fault code anywhere touches a CVT.** No corpus row associates a
DTC with belt, variator or clutch wear, and the scooter makers documented
in 251–253 publish no code table at all. Whether any maker publishes a CVT
fault code is a research question, not an assumption.

**S0-8. The count moves.** README, the quickstart, the install guide and the
launch checklist all state 1033 and move together (Phase 208's guard).

**S0-9. Schema version is 62 and stays there.** No migration, no new table.

## Decisions

**D1. Anchored or not written.** Every statement names the document it came
from. A mechanism described from general engineering knowledge and not from
a fetched manufacturer document does not ship, however uncontroversial.

**D2. One row, one label**, and a forum row names its site and the page's
own date. 246's rule, kept.

**D3. The generic layer is written as the catalogue plus the silence.**
246–249's shape: what the mechanism does, how each maker shows it, and the
sentence that says what none of them publishes. The absences are content.

**D4. The machines' own rows are referenced, never restated.** 251, 252 and
253 shipped per-machine belt intervals and limits. 254 may name them to
draw the comparison and must not rewrite them.

**D5. "Drive belt" gets disambiguated here.** The row names the three
components the corpus calls a drive belt and says which one a CVT belt is,
because S0-3 shows retrieval cannot.

**D6. The published-limit pattern is a hypothesis until a refuter tests
it.** S0-5 looks true across five makers. It goes to a refuter as a claim
to break, not into a row as a finding.

**D7. Kickstart backup is a question, not a premise.** The roadmap row names
it. Which small machines actually have one, and what the maker says about
using it, is to be established per document — and if the answer is that it
has largely disappeared, that absence is the content.

## Scope

1. `known_issues_cvt.json` — the generic layer: the variator and its
   rollers, the belt and its wear, the clutch and its bell, kickstart
   backup where it exists, what each maker publishes and what none does.
2. A content test in 253's shape: every row anchored, every number
   labelled, no restatement of 251–253's machine rows, and the layer
   reachable for a scooter query so that 258 can find it.
3. The four user-facing docs' count, moved together.

## Non-goals

- **No twist-and-go comparison, no scooter electrical layer, no carburettor
  service** — rows 255, 256, 257.
- **No restatement of 251, 252 or 253's per-machine rows** (D4).
- No new marque, no `dtc_codes` seeding, no adapter rows.
- No schema change, no migration.
- No fix for F108's vocabulary junk.
- Nothing from memory: no interval, clearance or wear limit that a fetched
  page does not state.

## Verification Checklist

- [ ] Every row anchored to a named document, or dropped
- [ ] Every number labelled; no number without a fetched source
- [ ] No row restates a per-machine row from 251, 252 or 253
- [ ] The three meanings of "drive belt" are named and separated
- [ ] The published-limit pattern survived a refuter, or was corrected
- [ ] The new test file scanned by 244G's raw-source guard
- [ ] Mutations caught
- [ ] Full regression green — 0 failed, 0 skipped
- [ ] Live DB loaded copy-first, before-state printed; count docs moved
- [ ] Roadmap row, `implementation.md` history row, `phase_log.md`
