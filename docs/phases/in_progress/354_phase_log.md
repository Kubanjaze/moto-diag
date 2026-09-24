# Phase 354 — Scooter electrical (12V minimal) — phase log

**Status:** 🚧 In progress
**Opened:** 2026-09-24

---

### 2026-09-24 — Opened after 257, 257B and the F148 fix

Taken before 258 by the operator: Gate 14 queries a scooter for CVT,
electrical and carb content, and electrical (354) and carb (353) are not
built. Read before acting: ROADMAP (354, 353, 258 and the Track M rows),
`ROADMAP_AUTHORITY.md` (354 is backend, 205+), `257_implementation.md`
and `257B_implementation.md` in place of the newest handoff (operator: the
2026-09-23 handoff predates 257's close, 257B and F148), FOLLOWUPS (F115,
F127, F129, F142 bear on this), and 251–255B's implementation docs for the
content rules this track built.

ROADMAP row to 🚧 before Step 0: `572664b`, pushed on `phase-354`.
`roadmap_check.py` exit 0 before that commit.

**Decision (logged, not asked):** bulk reading goes through Subconscious
(`subc claude`, `subconscious/glm-5.3-marathon`), one document per call,
one turn, tools disabled with 257's flags. Every quote it returns is
checked against the page text by a script before it is used; its
`value` field is a map, not evidence, because a verbatim quote can sit
beside a value that says more than the quote does.

### 2026-09-24 — Step 0: extension, content only, no fork

Measurements S0-1..S0-13 are in the implementation doc. In short: the
scooter charging layer is empty (the only `regulator` in 251–254's files
is the US regulator), three unverified Honda `model = All` charging rows
reach every Honda scooter at tier 1, and the service manuals show that
carburettor versus injection does not predict the charging design (the
carburetted CHF50 Metropolitan is three-phase; the injected Zuma 125
prints "AC magneto"). The PCX150 manual puts the regulator/rectifier
inside the ECM.

**Decision (logged, not asked): no fork.** Each question had a default
this track already set: one make per row (F142), content written from
quotes and a subject dropped when its quote dies (254, 255B), and a defect
in an older row filed rather than patched mid-phase (254's F111). The
row's three phrases are tested, not written: *simple wiring* is no
document's claim, and *no FI on older carb scooters* is already shipped
by 252 and 254.

**Decision:** Honda rows #263, #264, #270 are filed, not edited (D5).

**The census was wrong twice before it was right** (S0-3): `battery`
read 0 through a regex missing its first letter, and `regulator` matched
*regulatory*. Caught because 0 batteries in 1,046 rows is impossible and
16 regulator rows beside 0 stator rows was implausible; both re-run with
the matched strings printed.

**Sweep:** 46 documents, 1,227 facts, 1,115 verified, 9% dropped. Four
calls failed and were re-run: Symply 125 (output overran its limit, only
the tail returned), Vespa LX 50 (a literal `[...]` placeholder), Fiddle
III and Fly 50 (refused at zero tokens). The prompt now caps an answer at
40 facts and forbids placeholders.

**Housekeeping, stated because it cannot be proved either way:** copying
the Step 0 scripts to `~/research/motodiag/354_step0/` briefly wrote five
files (`census.py`, `extract.py`, `select_pages.py`, `sweep.py`,
`verify.py`) into the research root and then deleted them. That tree is
not under git. Nothing in it references root-level files of those names,
so none is believed to have existed; if one did, it was overwritten.
