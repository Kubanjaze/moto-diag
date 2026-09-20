# Phase 250C — The model-resolution pool is keyed by the raw make column — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-20

---

## 2026-09-20 — Plan v1.0

250B measured the bug and handed it over; Step 0 re-verified it from
scratch and then found the part the measurement had hidden. Keying the
vocabulary by marque is the fix, but the junction it would copy from is not
clean: 95 of its 764 pairs are cross-attributed, because a row naming six
marques files every model against all six. Keyed alone, the pool grows to
764 and carries all 95 — a bike entered as an Aprilia could match "BMW
S 1000 R". Keyed and attributed, it is 638 with one mis-attribution, and
resolution goes from 511 pairs to 644.

Attribution has three rungs, each earned from the data: a model seen on a
single-marque row belongs to that marque; a token that names a marque
belongs to it; a token that is exactly a marque name is not a model at all,
which is what the "All European makes" row's model column turns out to be —
a list of marques.

One fact the data cannot supply: the cross-marque exclusion must not fire
between Harley-Davidson and LiveWire, or every LiveWire model leaves
Harley-Davidson's pool. Simulated both ways; the exemption is worth 23
models against 15, and it lives in its own module because 244F and 244C
guard the derived ones against exactly this kind of hard-coded name.

Three machines still will not resolve and none is this row's: Zero SR/F
(the tokenizer splits on "/"), BMW R1250GS (ambiguous against R1150 and
R1200, and right to refuse), and Harley-Davidson LiveWire (the corpus never
writes a bare "LiveWire"; the name covers two machines). Each was checked
against today's behaviour before being ruled out, and each is filed.

## 2026-09-20 — Complete

Regression **7,403 passed, 0 failed, 25:05**. No schema change, no migration, no corpus edit. The live junction was rebuilt at close-out, copy first, because the derivation changed and nothing rebuilds it automatically.
