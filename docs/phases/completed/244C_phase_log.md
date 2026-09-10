# Phase 244C — Vehicle identity resolution — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

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

---

## 2026-09-10 — Built

`src/motodiag/knowledge/vehicle_resolver.py`. Match ladder is exact →
abbreviation → fuzzy → unresolved, with the vocabulary read from the corpus by
`SELECT DISTINCT` so it cannot drift from the data.

**The negative cases are the point, and they hold.** `Ducati` resolves to
nothing against a corpus that does not contain it. `zx10r` finds no match under
Honda. `cbr600` is a subsequence of three CBR models, so it is reported as
ambiguous and **suggested rather than applied** — ambiguity is a question for
the technician, not a decision for the resolver.

**Mutation testing earned its place again.** Six mutations, five caught on the
first write; the sixth escaped. `test_a_very_short_string_cannot_fuzzy_match`
used `"Ho"`, which scores 0.0 here and was being rejected by the floor rather
than by the length gate it claimed to test — it passed with the gate deleted.
Repaired using `"cbz"`, which scores 0.800 against the two-character model `CB`
with a 0.400 margin and clears both other bars; only the length gate stops it.
Second phase in a row where a guard tested the failure I imagined instead of
the one that exists.

**A third defect surfaced while wiring and was not folded in.** `known_issues`
holds 6,600 rows for 660 distinct issues — every entry present exactly ten
times, with no UNIQUE constraint and a non-idempotent loader. It had been
silently degrading retrieval all along: the run that exposed this was handed 20
rows containing 2 distinct facts, and said so. `known_issues_for_vehicle`
deduplicates on retrieval (2 → 22 distinct for the same request), but the
constraint needs a migration and a table rebuild that must preserve migration
053's severity expression index. Recorded as separate work.

**Verified against the recording that started it.** Session 6, a 2001 Honda
CBR600F4i entered as "Homda cbrf4i", complaint recorded only in the session
notes. Before: 0 corpus rows, 0 of 15 findings about the leak, marque guessed as
"Kawasaki ZX-series or Suzuki GSX-R". After: 22 distinct corpus rows, three
ordered leak candidates, two of them citing real corpus entries, and the marque
read from the session rather than the pixels.
