# Phase 255C — The junction stores names the tier query cannot match — phase log

**Status:** 🔲 In progress
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
