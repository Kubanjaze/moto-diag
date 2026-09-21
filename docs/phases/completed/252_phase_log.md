# Phase 252 — Honda's small machines: the four the corpus never named — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-20

---

## 2026-09-20 — Plan v1.0

The subject is empty, and the check that would say otherwise is a
substring collision: `LIKE '%Grom%'` returns four rows and all four are
the word *grommet*. Nothing in 1006 rows names the Ruckus, the
Metropolitan or the PCX.

What makes this row different from 251's is the company it keeps. Honda is
the corpus's third-largest marque — 142 rows — and **every one of them is
`unverified`**, inherited from the pre-242 legacy seed. So 252 writes the
first anchored Honda content in the corpus, sitting beside 142 rows that
name no document, and Decision 4 says plainly that those rows are not
evidence for anything written here.

The before-state is measurable and was measured: Honda's model pool is 27
entries and every one is 250 cm3 or bigger, so Grom, Ruckus, PCX150,
Metropolitan, Monkey 125, Super Cub C125 and Trail 125 all resolve to
`unresolved` and fall back to 20 make-wide hits, where a CBR1000RR
resolves exact and gets 31.

One thing was found in Step 0 that its equivalent in 250C was found by the
full regression instead: `test_phase250C_model_vocabulary.py` pins Honda's
pool at **exactly** 27 as a control group — Honda writes one marque per
row, so raw-key and marque-key agree, and the equality proved the
derivation changed nothing it should not have. Adding content moves that
number for an unrelated reason. The pin moves in the same commit, with the
reason written into it.

Boundaries set before research, as 251 set them: the generic CVT layer is
row 254, scooter electrical 256, carburettor service 257, and the other
small marques are 253. 252 is the machines. The miniMOTO siblings ride
only where a fetched document covers them with the Grom — never because
sharing an engine makes it plausible.

Sweeps launched with the plan. Each fetches every page it cites and quotes
it, or the claim does not exist.

## 2026-09-20 — Complete

Regression **7,560 passed, 0 failed, 31:28**. Corpus 1006 -> 1019, Honda's model pool 27 -> 46. No schema change. F105, F106 and F107 filed, and F103 amended.
