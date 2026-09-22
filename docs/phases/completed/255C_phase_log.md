# Phase 255C — The junction stores names the tier query cannot match — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-22

---

### 2026-09-22 11:40 — Bug fix #1: a comma inside a thousands separator split a figure in half

**Issue.** `known_issue_models` held `'000 km'` (3 rows), `'F3 at 30'`,
`'Rivale at 12'`, and the bare numbers `'10'`, `'24'`, `'45'`, `'60'` as
model names. A bare `'10'` in the model vocabulary matches almost any text,
so the damage was not limited to the junction — it reached the resolver's
matching pool.

**Root cause.** `models._model_tokens` splits a model value on
`,|;|—|–|/| and`. A comma **between digits** is a thousands separator, not a
list delimiter, and nothing distinguished the two. `"Rivale at 12,000 km"`
split into `"Rivale at 12"` and `"000 km"`; `"Diavel V4 (V4 Granturismo,
60,000 km)"` contributed `"60"` and `"000 km)"`.

**Fix.** `_THOUSANDS_COMMA` (`(?<=\d),(?=\d)`) is substituted for a hold
character before the split and restored after, exactly as `_COMPOUND_SLASH`
already does for a slash inside a compound designation. The idiom was
already in the file; the digit case was simply not covered.

**Files.** `src/motodiag/knowledge/models.py` — `_THOUSANDS_COMMA` and
`_COMMA_HOLD` added beside `_SLASH_HOLD`; the hold and restore added in
`_model_tokens`.

**Verified.** Junction rebuilt on a copy of the live database: 2,433 → 2,430
rows, 706 → 705 distinct strings.

```
GONE : '000 km', '10', '24', '45', '60', 'F3 at 30', 'Rivale at 12'
NEW  : '10,000 km', '24,000 km', '45,000 km', '60,000 km',
       'F3 at 30,000 km', 'Rivale at 12,000 km'
```

Positive control — a real comma list must still split:
`"Agility 50, Agility 125, People S 250"` → three tokens;
`"PCX125, PCX150, PCX160"` → three tokens.

**Known consequence, recorded rather than fixed here.** The fix turns
torn-in-half debris into *whole* debris. The six new strings carry a code
token (`000`) and therefore fall in group (B), which the extraction gate
does not reject and which the operator's decision of 2026-09-22 leaves as
it is, filed on the general-applicability ticket. The fix is still strictly
better: four bare numbers leave the model vocabulary, where they could match
almost any text.

### 2026-09-22 12:20 — The positive gate at extraction

**What it replaces.** `CONTRAST`, `_PROSE_WORD`, `_NEGATED_PAREN` and
`is_scope` are all blacklists, and every debris root cause found was a gap in
one of them. Four gaps in a single pass is the signature of the wrong shape
of check: **a blacklist admits everything nobody thought to name.**

**The rule.** `admits_as_model` rejects a fragment that contains a bare
lowercase word and carries no designation code. Parentheticals are stripped
first, so `R-series (airhead)` is judged on `R-series`.

**The bypass that the whole-corpus control found.** `is_plain_model` is used
as an early-accept in **two** places — `_model_tokens` and `extract_models`
— and neither consulted any filter. A short delimiter-free prose sentence
took that branch in both. `"Piaggio Group marques only"` is 26 characters
with no comma and reached the junction whole through each of them. Gating
one left the other open, and only running the gate over all 705 strings
showed it.

**Result, on a copy of the live database:** junction 2,430 → 2,334 rows,
705 → 650 distinct strings. The gate rejects **exactly** the 55 pinned
group (A) strings and admits the other 650, every group (B) string included.

**Two pins moved deliberately.** Phase 250C's `BEFORE` table asserts no
marque's pool may shrink; Ducati 83 → 78 and Triumph 82 → 77, because what
left was `dry clutch`, `wet slipper clutch`, `spring valves`, `rear radar`,
`belt-driven cams`, `carburetted`, `injected`, `independent`, `related` and
`per handbook`. Each is in `REJECTED_BY_THE_GATE`. First time that table has
been lowered, and it stays a pin: a pool may only shrink by strings named in
the pinned set.

**Break-it.** Disabling the gate in `_model_tokens` fails 2 tests; disabling
only the `extract_models` plain-model accept fails the whole-corpus control
specifically — which is the test that found that bypass in the first place.

### 2026-09-22 15:05 — The fork on single-token models, and a remedy for a non-problem

**Issue.** Building the pair form raised a case v1.0 had not decided: a model
name that is a single token also present as a marque or a common word. `ONE`
is the specimen — LiveWire's model, and an English word.

**Two branches drafted, both rejected.** Each kept or reintroduced the marque
inside the model string, which decision 3 forbids. The operator's ruling was
*neither branch* — the fork is an extraction problem, not a canonical-form
one.

**The mechanism tried.** Admit a single-token model only when it appears
adjacent to its marque in the source string. Measured before committing, as
instructed: it **lost 457 legitimate rows across 108 models.** `SR` 33 → 1,
`DS` 28 → 1, `Experia` 26 → 0, `DSR` 26 → 2, `FX` 20 → 1, `Alpinista` and
`Mulholland` 16 → 0 each, plus `Grom`, `Thruxton`, `Speedmaster`. Named and
stopped, per the standing instruction not to reach for a list. Stripped out.

**Why it was ever built.** The "32 false `One` rows" it was meant to remove
do not exist. The count was read off the rows' **titles** rather than the
**model columns** that produced the junction entries. Forty-two model columns
literally contain `LiveWire ONE`, and a bare `One` was the correct canonical
on every one of them. Recorded as D7 in the plan, and on the CLAUDE.md
instance list as *measure what produced the number*.

**Resolution.** Decision 3's plain rule, nothing added. `One` stays bare;
`Zuma` collapses against `Zuma 125` by containment. `_stands_alone` and
`_is_single_token` removed. The per-marque dedupe restructuring is kept
regardless — under the pair form `dedupe_contained` must compare within one
make, which is right whether or not a cross-make collision exists today.

**Measured after.**

| quantity | before | after |
|---|---|---|
| PCX 150 rows at tier `model` | 2 | **11** |
| PCX 150 retrieved / kept | 166 | **166, unchanged** |
| distinct `(issue, model)` | 2,433 | **2,397** (ceiling was 2,412) |
| total `(issue, make, model)` | — | **2,795** (+398 = the marque dimension) |
| PCX spellings in the junction | 6 | **1** |
| Guard 2 violations, per marque | — | **0** |
| strings the whole-corpus gate rejects | — | **55, exactly** |

**Break-it.** Guard 1 and Guard 2 were each broken on purpose and seen to
fail before the commit landed.

### 2026-09-22 15:40 — Three more bug fixes, each a real defect in shipped code

* **#2 — migration 065's `post_apply` wrote the 3-column junction at v65.**
  It calls `rebuild_model_index`, which writes the pair form, but 065 runs
  while the table is still 2-column. **Any database at 64 or 65 could not
  migrate.** Fixed by reading `PRAGMA table_info` and writing to suit the
  shape in front of it.
* **#3 — the schema-56 degradation path crashed on placeholder count.** The
  tier query gained a binding for the pair; the make-only fallback still
  passed six parameters into five placeholders — *"Incorrect number of
  bindings"*. Reachable on any database short of migration 057. Fixed with a
  separate `make_only_params`.
* **#4 — migration 065's rollback restored a string no rebuild produces.**
  Its `INSERT OR IGNORE` carried the literal `'SYM Symba'`, the form the
  model **column** spells; 255C canonicalises that machine to `'Symba'`. The
  round trip landed one row short — 2,385 → 2,384, `(164, 'Symba')` lost and
  `'SYM Symba'` left behind — and the 2,385 baseline was itself inflated by
  the same spurious insert, so the *correct* figure on both sides is 2,384.
  Fixed to the canonical form, reasoning left in the SQL. **Junction literals
  are written in the form the extractor produces, never the form the column
  spells.**

**Process note.** 255C's first three commits were made on `master` rather
than on a phase branch, against the convention every prior phase follows.
Corrected before this commit: `phase-255C-junction-identity` was created at
the tip and local `master` rewound to the pushed v1.0 at `297780a`. Nothing
that had been pushed was discarded.

### 2026-09-22 16:20 — The full regression found two the narrow run could not

The four-file run was green and the first commit landed at `f11505b`. The
full regression — 8,088 collected — came back **2 failed / 8,086 passed** in
30m56s. Both failures were real, and neither was reachable from the files
255C had touched. This is the case for running the whole thing.

**Failure 1 — `test_phase245_damon_absence`: `'HyperSport' != 'Damon
HyperSport'`.** A **17th** pinned literal, where D4's AST enumeration named
sixteen. The pin was stale, not wrong-to-move: the caller asks for
`("Damon", "HyperSport")` and was handed back a model carrying its own
marque, because the vocabulary was built from Phase 241's column, which
spells it `Damon HyperSport`. **The canonical a caller got back could not be
typed by that caller** — 255C's defect in miniature. Moved to `HyperSport`;
`corpus_hits == 0` still pins what the file exists to guard.

**D4's enumeration missed one, and the reason is worth recording:** it
enumerated consumers of canonical strings in `src/`. This pin is in a test,
asserting a resolver return value. The enumeration's positive control proved
it found what it looked for; it did not prove it looked in the right places.

**Failure 2 — 209B's orphan pin: `knowledge/models.py::extract_models`.** The
pair form superseded its one `src/` caller, leaving a public function
referenced by nothing but its own tests — the F9 integration gap, exactly
what that pin is for.

**It was deleted rather than allowlisted, and measuring is what decided
that.** `extract_models` and `extract_model_pairs` disagree on **3 of 1,003**
live rows, and every disagreement is a marque-prefixed raw string:
`Energica Experia`, `KTM 690 Duke (LC4 single)`, `KTM LC8 75-degree V-twin`.
A superseded function still emitting the defect its replacement removes is a
loaded gun for the next caller.

**And chasing that disagreement found bug fix #5, which is the real one.**
The three rows above are indexed by the pair form as **nothing at all**. The
plain-model early accept tests **exact** vocabulary membership, and
`Energica Experia` is not in a pool that now correctly holds `Experia`. So
row 868 names the Experia and an Experia can never reach tier 0 on it —
**255C's own defect, reintroduced on three rows by 255C.**

The accept is removed, not patched. It skipped `covered_part` *and* the
vocabulary and returned the raw column text, which is a second normaliser in
a phase whose decision 1 says extraction has none.

| | |
|---|---|
| rows unchanged | **985** |
| rows changed | **18** |
| rows lost | **0** |
| rescued from being indexed as nothing | **3** |
| distinct `(issue, model)` | 2,393 → **2,397** |
| total `(issue, make, model)` | 2,791 → **2,795** (ceiling 2,412 on the distinct form still holds) |

The fifteen others traded a raw string for the canonical:
`S1000XR (2015-2019)` → `S 1000 XR`, `Road King (FLHR)` → `Road King`,
`R-series (Paralever)` → `R-series`, and `R1150/R1200 (Integral ABS)` →
**both** `R1150` and `R1200` — one row reaching two machines it always named.

**Where the gate went.** It stays in `_model_tokens`, at vocabulary
construction, which is where a name is first admitted and where the
whole-corpus negative control measures. Nothing reaches `extract_model_pairs`
that the vocabulary did not already admit, so the second gate had nothing
left to gate.
