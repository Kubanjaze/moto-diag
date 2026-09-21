# Phase 255 — The transmission axis — phase log

**Status:** 🚧 In progress
**Opened:** 2026-09-21

---

## 2026-09-21 — Plan v1.0

Row 255 was planned as a content row about twist-and-go versus manual small
bikes. Its first Step 0 measurement found that the corpus cannot express that
distinction at all, and that **Phase 254 — closed the same day — shipped a
defect because of it.** Every Honda and Yamaha now retrieves the generic CVT
layer: a CBR1000RR gets 7 CVT rows, a Gold Wing 7, an XS650 8. A Kawasaki Ninja
400 gets 0, which isolates the cause to the make column rather than the content.

By the delivery standard written earlier the same day, that is a **validation**
failure and not a verification one. Phase 254 passed 85 tests, 22 of 22
mutations, a 986-test blast radius and a 7,750-test regression, all green, and
still reaches machines it does not describe. The operator's call: 255 becomes the
mechanism, the content row follows as 255B, and the over-reach is logged as a
dated bug-fix entry against 254 with its own commit.

Two things shaped the design more than anything else.

**250B cannot be copied, for two independent reasons found by reading its code
rather than its docstring.** It *reorders* rather than excludes —
`_electric_first` returns `electric + [everything else]` and removes nothing — so
copying it would leave CVT rows in a CBR1000RR's prompt. And it infers a row's
powertrain from the row's *marque names*, with `is_electric_row` documented as
"deliberately generous". That generosity is exactly what breaks here, because
Honda and Yamaha build both scooters and motorcycles. 255 diverges on both
points, deliberately, and 250B is not touched.

**The Cub clutch verification corrected my own premise.** I had assumed that
clutch content mentioning a lever does not apply to a Cub. Honda's own parts
catalogue `13K0GK01` — fetched and checked in the main session, not taken from a
report — names the internal actuator `LEVER COMP., CLUTCH`, part 22810-KPH-900,
inside the right crankcase cover. Excluding on the word "lever" would have
withheld content that applies. The catalogue also shows the Cub has **two**
clutches with disjoint parts lists: a centrifugal primary with no friction plates
at all, and a multiplate change clutch with four friction disks released by the
gear pedal. And `STARTING CLUTCH` turns out to be the starter motor sprag, a
third component — so my own earlier phrase "centrifugal start clutch" was using
Honda's name for something else.

One claim did not survive contact with the document. "Clutch free play is a
published Cub adjustment" is **not supported for the C125**: its owner's manual
`32K0GC20` returns zero hits for clutch lever, clutch cable and clutch adjust,
and all 18 of its freeplay references are about the brake pedal. The parts
catalogue proves a `BOLT, CLUTCH ADJUSTING` exists; no obtainable Honda document
publishes the procedure. Downgraded rather than shipped.

The operator tightened five things before the plan was committed, and the
sharpest was catching a per-category example I had written into my own
per-row rule: I had said a centrifugal-engagement row would declare
`{cvt, semi_auto_centrifugal}`, which is reasoning from the category rather than
from what the row says. A scooter clutch-bell wear limit does not hold for a
Cub's primary clutch. Most 254 rows will be `{cvt}` alone.
