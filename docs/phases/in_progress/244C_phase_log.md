# Phase 244C — Vehicle identity resolution — phase log

**Status:** Planned
**Opened:** 2026-09-10

---

## 2026-09-10 — Plan v1.0 written

Opened directly out of Phase 244B's re-run. Re-running the user's real
recording surfaced that the session recorded the bike as **"Homda cbrf4i"** and
the corpus lookup returned **zero rows**, while the knowledge base holds **20
entries for the Honda CBR600F4i**. Nothing anywhere reported that the lookup
had failed to match a name rather than found nothing to say.

The user's framing: *"it should suggest and fix what it's clearly
representing."*

**Two defects, both silent.** `make` is matched literally, so a one-character
typo empties the corpus. `model` is free text matched against canonical corpus
names, so `cbrf4i` — which is simply how people write CBR600F4i — also returns
nothing. Neither produces a warning, and the analysis downstream cannot
distinguish "this machine has no documented issues" from "nobody could find
this machine".

**The design commitment that matters is the negative one.** Resolving a bike
onto a neighbouring make would attach another machine's documented faults to
it, with a mechanic acting on the result. So the ladder has an `unresolved`
rung with teeth: a fuzzy match must clear 0.78 *and* beat the runner-up by
0.15, and an abbreviation must match exactly one candidate. `Ducati` scoring
0.364 against this corpus resolves to nothing, and that is pinned as a test.

Vocabulary is read from the corpus with `SELECT DISTINCT` rather than kept in
an alias table, because an alias table drifts the moment a phase adds a make —
the constant-for-invariant family in a different costume.
