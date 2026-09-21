# Phase 253 — Yamaha's scooters and the Taiwanese makers — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-20

---

## 2026-09-20 — Plan v1.0

The subject is empty and three separate checks say otherwise. Searching the
corpus for `SYM` returns 117 rows and every one is *symptom* or *system*;
`Genuine` returns 60 and every one is *genuine part*; `Buddy` returns five
and none is the scooter. 252 met this once, as *grommet*. Here there are
three of them, because two of the three marque names are ordinary English
words.

That made the first real question of this phase a safety question rather
than a content one: does adding makes literally named `SYM` and `Genuine`
corrupt retrieval for the whole corpus? Probed on a copy before anything was
written. It does not — `resolve_vehicle("system")` and `("symptom")` both
stay unresolved, marque matching is not substring-based, all three new
marques and their models resolve exact, integrity is clean, and the only
retrieval that moved was Yamaha's make-wide count rising by the one probe
row carrying its name. Evidence rather than hope, and cheap to get.

The rest of Step 0 is 252's situation one marque over. Yamaha is the
corpus's fifth-largest marque with 111 rows and **every one is
`unverified`**; its model pool is 23 entries and every one is a motorcycle.
So these will be the first anchored Yamaha rows, written beside 111 that
name no document, under the same decision 252 made about Honda's 142.

The heavier constraint this time is 252 itself. It closed hours ago on
adjacent machines — same class, same regulator, same document-access
problems — so its rows are referenced and never restated. The same applies
to parts availability, which the roadmap row names and which Track K has
already written for the Piaggio Group and for KTM.

One side finding came out of the probe. `resolve_vehicle("SYM", "Mio")`
returned `ambiguous` against alternatives including `2017 campaign
population` and `cast-aluminium Front Frame`, which led to measuring the
model vocabulary: 32 of its entries are not models at all, but descriptions
and components that reached it through model columns used as a description
field. Filed, not fixed — this is a content row.

Sweeps launched with the plan. Each fetches every page it cites and quotes
it, or the claim does not exist.

## 2026-09-21 — Complete

Regression **7,665 passed, 0 failed, 36:56**. Corpus 1019 -> 1033, three new marques (Kymco, SYM, Genuine), Yamaha's model pool 23 -> 46. No schema change. F108, F109 and F110 filed.
