# Phase 250B — The electric layers never reach the model — phase log

**Status:** 🚧 In progress
**Opened:** 2026-09-19

---

## 2026-09-19 — Plan v1.0

Opened by Gate 13 with the measurement already in hand, which is the
difference between this row and a hunch. Step 0 then answered the two
questions the plan owed.

First, raising the prompt cap is not the fix: a Harley-Davidson LiveWire
would need 95 rows and 68 KB per call to reach all four layers, three times
over in the interactive flow. A powertrain filter collapses that query from
165 candidate rows to 45 and puts it on the LiveWire ONE's own footing, and
composition — eight rows by today's ranking plus four reserved slots —
delivers every layer at today's prompt size while the safety floor holds or
improves.

Second, the reserved slots go to what the rider actually reported, not to a
fixed list of four layers. Measured: "brake light does not come on under
regen" brings the regen rows, "pack overheats while charging" brings the
pack and thermal rows, "motor controller fault code" brings the controller
and cooling rows. A fixed list would answer the rider's question by
accident, and relevance is a rule every other track can use.

Step 0 also found the cause underneath: the model-resolution pool is keyed
by the raw make column, so LiveWire and Damon can never resolve a model at
all and ten of sixteen marques resolve only some of theirs. That is why a
Harley-Davidson LiveWire is handed V-twin content — an engine, a clutch and
a stator it does not have. The operator's decision is that it opens as row
250C rather than growing this one, because it changes resolution for every
marque in the corpus, not only the electric ones.
