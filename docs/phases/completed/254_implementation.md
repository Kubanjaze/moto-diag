# Phase 254 — Small-displacement CVT diagnostics: the layer three rows left alone

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-21

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

## Results (v1.1)

**Shipped:** `known_issues_cvt.json`, twelve rows — ten `service-manual`, two
`regulation`, none `model-generated` and none `unverified`. Corpus 1033 →
1045. **No new marque**; every make in the layer already existed.

- 85 tests, 22 mutations.
- Full regression **7,750 passed, 0 failed, 38:34**.

### The row did what Step 0 said it was for

Step 0's argument was that three unrelated components share the phrase
*drive belt* and retrieval cannot separate them. Measured before and after:

| search | before | after |
|---|---|---|
| `drive belt` | 8 rows, **1 CVT, last** | 13 rows, **5 CVT** |
| `variator` | 1 | 6 |
| `weight roller` | 0 | 4 |
| `primary sheave` | 0 | 4 |
| `clutch bell` | 0 | 2 |
| `kickstart` | 0 | 2 |

One gap was found by re-measuring after the first load rather than by
assuming: `roller weight` still returned **zero**, because every maker
writes *weight roller* and the rows had faithfully inherited the makers'
ordering — reproducing the exact gap the phase exists to close. The
vocabulary row now names both orderings.

### The hypothesis died three times

Step 0 flagged a tidy pattern across five makers and wrote that it was
"exactly the kind of tidy claim the last three phases have taught me to
hand to a refuter rather than to trust". It was sent out to be falsified.

| version | killed by | how |
|---|---|---|
| "only Piaggio publishes a belt wear limit" | sweep A | **every** maker publishes roller limits — Honda 19.5 mm, Yamaha 19.5 mm, Kymco 15.4, SYM 19.500 and 15.40, PGO 17.40 |
| "intervals in owner's manuals, limits in service manuals" | sweep B | **three service manuals carry both** — Piaggio 633976 prints the interval one page from the limit |
| "only Piaggio publishes it in an *owner-reachable* document" | sweep C | **backwards** — Piaggio's limit is in a manual stating it is "to be used by the workshops of Piaggio-Gilera dealers", while the Vespa owner's manual has "width" **zero** times and is fully searchable |
| "every belt *number* lives in a service manual" | refuter 3 | a Bintelli owner's manual prints **"Belt Model   Gates 669MM"** — a *length* |

**What survives, and ships:** no owner's manual publishes a belt **width or
wear limit**, tested across 34 of them. The row is worded "width or wear
limit" rather than "number" *because* of that counter-example — the
difference between a claim that survives the sample and one that is false.

### What the refuters corrected

| The sentence | Why it died |
|---|---|
| "the Kymco manual contradicts itself three times" | **four**, and the direction of error is inconsistent, so "trust the table" is ruled out |
| "the manual mixes two machines" | the FILLY pages alternate **strictly by odd/even folio** — a recycled page template — except in two whole chapters where provenance genuinely is unestablished |
| "only the clutch bell is self-consistent" | **four of nine** rows agree; the sweeps stopped reading at 9-10 and missed page 9-11 |
| "the belt limit rests on a third-party transcription" | it is in Kymco's own PDF, **with a paired standard of 17.5 mm** |
| "Kymco's figures cannot be trusted" | a **one-book** defect; the People S 250 agrees with itself on all six figures across 243 uniformly-headed pages |
| "21.5/22.5 belongs to the Vespa LX platform" | it appears in **four** Piaggio manuals and splits by **displacement class**; manual 618162 prints two pairs **on one page** |
| "the shipped 251 row is wrong" | the row's figures and prose are right; the defect is one model name in a **scope field** (F111) |
| "the bare ENGINE component is an anomaly" | 10 of 1,125 campaigns, 233 colon-free — a taxonomy gap, not a one-off |
| "the makes index systematically omits" | **bidirectional** — 13 one way, 12 the other, of 102 tested |

Each is a test and a mutation.

### What was found that nothing had

**Campaign 21V251000** — Yamaha XC155, 4,262 units, park-it: *"The primary
sheave nut may loosen and fall off"*, with *"A missing primary sheave nut
may cause a stall, without the ability to restart the engine"*. It surfaced
**only** because a refuter searched Yamaha's own word, **sheave**, which
appears in exactly **one** of 1,125 campaigns collected — while **variator
appears in none at all** — and it is filed under a bare `ENGINE` component,
so a taxonomy filter would skip it too.

### Deviations

**The Piaggio "correction" was not made.** A sweep proposed correcting a
shipped 251 row; a refuter found the row right and the sweep wrong. The
real defect is smaller — one model name in a coarse scope field — and
because `known_issues` identity is (make, model, title), editing that
column creates a row rather than updating one. **Filed as F111 rather than
patched mid-phase.**

**No marque was created for the counter-example maker.** Bintelli is named
in text where it kills the claim, and deliberately not made a marque,
because it would carry no machines of its own — 245's Damon lesson.

**The 250C control-group pin moved for the third consecutive phase** and
was bumped with its reason, as in 252 and 253. The pattern is now recorded
as F112: for Honda and Yamaha that equality tracks content rather than the
derivation, while Kawasaki and Suzuki still do the real work.

### Verification

- Twelve rows, every one anchored; mirror provenance stated for the service
  manuals, and the statement that **no maker here publishes a service manual
  on its own site** carried explicitly.
- Retrieval measured before and after, not asserted.
- Six of the first 85 assertions failed and **three were real content
  defects the guards caught** — two rows citing no document, one regulator
  row printing no campaign number. All three fixed rather than excused.
- Two blunt token-ban guards, the fourth consecutive phase, both rewritten
  to test the claim scoped to a sentence.
- 22 mutations, all caught.

## Verification Checklist

- [x] Every row anchored to a named document, or dropped
- [x] Every number labelled; no number without a fetched source
- [x] No row restates a per-machine row from 251, 252 or 253
- [x] The three meanings of "drive belt" are named and separated
- [x] The published-limit pattern survived a refuter, or was corrected
- [x] The new test file scanned by 244G's raw-source guard
- [x] Mutations caught — 22/22
- [x] Full regression green — **7,750 passed, 0 failed, 38:34**, 0 skipped
- [x] Live DB loaded copy-first, before-state printed; count docs moved
- [x] Roadmap row, `implementation.md` history row, `phase_log.md`
