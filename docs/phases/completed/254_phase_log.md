# Phase 254 — Small-displacement CVT diagnostics — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-21

---

## 2026-09-21 — Plan v1.0

This is the layer three consecutive rows deliberately left alone. 251, 252
and 253 wrote the machines, and each of their test files forbids `variator`,
`roller weight`, `clutch bell` and `driven pulley` in its own rows so that
254 could own them. The vocabulary check confirms it: across 1033 rows,
`roller weight`, `clutch bell`, `drive face` and `torque driver` all return
zero, and the single `CVT` row and single `variator` row are the same
Piaggio row.

Two measurements shaped the plan. The first is a fourth consecutive
substring collision, and this time it lands on the row's own subject:
searching for `roller` returns 62 rows of which **33 are *controller***,
from Track L, and searching for `kick` returns five of which **two are
kickstand switches**. No scooter kickstart row exists. After *grommet*,
*symptom*, *system* and *genuine part*, this is a property of the corpus
rather than an accident, and Step 0 now checks for it by default.

The second is the argument for the row. Searching the corpus for `drive
belt` returns eight rows — five final-drive or other, two alternator, one
CVT — so a Harley tensioner, a BMW oilhead alternator belt and a Piaggio
CVT belt arrive together, with the CVT row last. Three unrelated components
share one name and retrieval cannot separate them. The generic layer is
where that can be said.

Much of the evidence is already in hand, scoped out of 251–253 on purpose:
Piaggio's published belt limits, Yamaha's 50 cm3 interval and the Zuma
125's belt width and limit, Honda's PCX belt indicator, Kymco's Like
interval, and the fact that SYM's Symba has no belt at all because it is
chain drive. So this phase is more composition than discovery, and the
sweeps are being told what is already gathered.

One tidy pattern is visible across those five makers — that only Piaggio
publishes a belt wear limit in an owner-reachable document — and it is
going to a refuter as a claim to break rather than into a row as a finding.
The last three phases have all turned on exactly that kind of sentence.

Sweeps launched with the plan.

## 2026-09-21 — Complete

Regression **7,750 passed, 0 failed, 38:34**. Corpus 1033 -> 1045, no new marque. No schema change. F111, F112, F113 and F114 filed.

---

## 2026-09-21 — Bug fix: the rows reach machines they do not describe

Logged against 254 rather than folded into a later phase, because the defect
is this phase's and the record should say so.

**What shipped wrong.** The twelve rows carry
`make = "Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine"`. Two of those
marques also build motorcycles, and retrieval's make-wide tier matches on the
make alone. Measured against the live database the day after the merge:

| machine | Phase 254 rows retrieved |
|---|---|
| Honda GL1800 Gold Wing | 9 |
| Honda CBR1000RR | 9 |
| Honda Grom | 9 |
| Yamaha YZF-R1 | 10 |
| Yamaha XS650 | 10 |
| Honda PCX 150 *(the intended target)* | 9 |
| **Kawasaki Ninja 400** | **0** |

Kawasaki's zero isolates the cause. Kawasaki is not in that make list; every
other marque in it is. **It is the make column doing this, not the content.**

**Nothing about the rows is wrong.** Every one is anchored to a manufacturer
document, carries one provenance label, and survived the refuters. The rows
would be correct in front of the right machine. They were put in front of the
wrong one.

**This is a validation failure, not a verification one** — the distinction
written into the delivery standards the same day. Phase 254 passed 85 of its
own tests, 22 of 22 mutations, a 986-test blast radius and a 7,750-test
regression, all green. Every one of those tests asked whether the rows were
right. **None asked which machines would receive them.** That class of test —
assertions about machines, stated as negatives — is what was missing, and
`tests/test_phase255_transmission_axis.py` is that file.

**How it was fixed.** Not by editing these rows' make column, which would
trade one hand-maintained list for another. Phase 255 builds the mechanism the
corpus lacked: a machine attribute, a per-row declaration of what the row
applies to, and a filter that **excludes**. Eleven of the twelve rows now
declare `{"transmission": ["cvt"]}`; the twelfth stays unscoped because it is
about vocabulary rather than about CVTs. Every machine above drops to the one
unscoped row, and every sourced scooter keeps all of them.

**What this phase should have done at the time.** Measured retrieval against
named machines that the rows do *not* describe, before close-out — not only
against the machines they do. A row's correctness and a row's reach are two
different questions, and 254 only asked the first.
