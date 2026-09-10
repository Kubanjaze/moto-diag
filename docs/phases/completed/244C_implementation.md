# Phase 244C — Vehicle identity resolution: a typo must not silently empty the corpus

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

A user recorded a real session, typed the bike in as **"Homda cbrf4i"**, and the
product silently retrieved **zero** knowledge-base entries. The corpus holds
**20 entries for the Honda CBR600F4i**. Nothing warned anyone. The analysis ran
to completion, produced a confident answer, and was never told that the machine
it was reasoning about had documented issues on file.

Two separate defects sit under that, both found by re-running the recording:

1. **`make` is matched literally.** `search_known_issues(make="Homda")` returns
   0 rows. There is no normalization, no alias table, no fuzzy fallback, and —
   worst — **no signal that a lookup returned empty because the name did not
   match rather than because nothing is known.**
2. **`model` is free text against canonical corpus names.** The corpus stores
   `CBR600F4i`; the user typed `cbrf4i`. That is not a typo, it is how people
   write it. It also returns 0.

The user's instruction: *"it should suggest and fix what it's clearly
representing."* So the goal is a resolver that maps free-text make/model onto
the corpus's own vocabulary, **fixes what is unambiguous and only suggests what
is not** — and never invents a match for a machine the corpus genuinely does
not cover.

## Non-goals

- **Not a spell-checker for the whole app.** This resolves against the corpus's
  actual `known_issues.make` / `.model` vocabulary, which is the only vocabulary
  that determines whether a lookup succeeds.
- **Not a silent rewrite of user data.** The garage row is the user's record.
  The resolver returns a resolution; persisting a correction is the caller's
  decision, and the media path uses it for retrieval and prompt context only.
- **Not make inference from pixels.** If the user did not say, we do not guess.

## Logic

New `src/motodiag/knowledge/vehicle_resolver.py`.

**Vocabulary comes from the corpus, not a hand-written list.** `known_makes()`
and `known_models(make)` read `SELECT DISTINCT` from `known_issues`. A
hand-maintained alias table would drift from the corpus the moment a phase adds
a make — the same class of defect as the constant-for-invariant family.

**Match ladder, most-certain first.** Each rung returns a `method` so the caller
can tell an exact hit from a guess:

| rung | method | when |
|---|---|---|
| 1 | `exact` | identical after normalization (lowercase, strip non-alphanumeric) |
| 2 | `abbreviation` | the input is a **subsequence** of exactly one candidate — `cbrf4i` ⊂ `cbr600f4i` |
| 3 | `fuzzy` | `difflib` ratio ≥ 0.78 **and** ≥ 0.15 clear of the runner-up |
| — | `unresolved` | nothing above cleared its bar |

**The margin requirement is the whole safety property.** `Ducati` scores 0.364
against its best corpus candidate and resolves to nothing, which is correct —
Ducati is not in this corpus. `cbr600` is a subsequence of three CBR models, so
it is ambiguous and is **suggested, not applied**. Auto-fixing requires both a
high score and a lone candidate.

**Models resolve within a make.** `zx10r` must not match a Honda model. If the
make is unresolved the model pool is every model in the corpus, and the bar
stays the same.

**Return shape.** `VehicleIdentity` carries a `Resolution` per field
(`given` / `resolved` / `method` / `confidence` / `alternatives`) plus
`corpus_hits` for the resolved pair. `applied` means confident enough to use;
`suggestions()` renders the human-readable "did you mean" for the ambiguous
ones. **A caller can always see what it was given and what was done with it.**

**Wiring, media path.** `_build_vehicle_context` resolves the identity and uses
it for the prompt and for corpus retrieval. The context string reports a
correction when one was applied, so the model is told the bike was recorded as
"Homda" and read as "Honda" rather than being quietly handed different data than
the technician typed.

## Key Concepts

- **An empty result and an unmatched name are different failures.** Today both
  render as "no known issues". `corpus_hits` plus `method` separates them, and
  that distinction is the reason this phase exists.
- **Vocabulary from the data, not from a list.** Alias tables drift; `SELECT DISTINCT` cannot.
- **Confidence gates the verb.** High and unique → fix. High and ambiguous → suggest. Low → say nothing and retrieve nothing.
- **Suggesting is not correcting.** The garage row stays the user's until they change it.

## Verification Checklist

- [x] `Homda` resolves to `Honda`; `Ducati` resolves to nothing
- [x] `cbrf4i` resolves to `CBR600F4i`; `zx10r` does not resolve under Honda
- [x] An ambiguous input is suggested, never applied
- [x] The corpus lookup for session 6 returns > 0 entries after resolution
- [x] A correction is visible in the context string, not silent
- [x] The vocabulary is read from the corpus, not hard-coded
- [x] Mutation: reintroduce literal matching → a guard fails
- [x] Full regression green

## Risks

- **Over-eager matching is worse than no matching.** Resolving a machine the
  corpus does not cover onto a neighbouring make would attach the wrong bike's
  documented faults to it — a correctness defect with a mechanic on the other
  end. The margin rule and the `unresolved` rung exist for this; `Ducati` is the
  pinned test case.
- **`difflib` on short strings is noisy.** Two- and three-character inputs can
  score high by accident. Guarded with a minimum input length before fuzzy is
  allowed to fire at all.
- **The corpus vocabulary is dirty.** `Africa Twin`, `Africa Twin CRF1100L` and
  `CRF1100L Africa Twin` are all present, as is the wildcard `All`. `All` must
  never be a resolution target.
- **Scope pressure.** This wants to become a global normalization layer touching
  every repo. It stays a resolver plus the media-path wiring; other callers
  adopt it deliberately.

---

## Deviations from Plan

**One guard was vacuous and mutation testing caught it.** Five of six mutations
failed their guard on the first pass; the sixth —
`test_a_very_short_string_cannot_fuzzy_match` — passed with `MIN_FUZZY_LEN`
removed entirely, proving nothing. The input it used, `"Ho"`, scores 0.0 against
this corpus and was being rejected by the floor, not by the length gate.

The repair required finding an input where the gate is genuinely load-bearing:
`"cbz"` scores **0.800** against the two-character model `CB` with a **0.400**
margin, clearing both the floor and the margin rule. Only the length gate stops
it being read as a real model name. The guard now uses that, and fails when the
gate is removed. **This is the second phase running where a guard written before
its evidence tested the failure its author imagined rather than the one that
exists** — Phase 244's finding, reproduced.

**A third defect was found while wiring, and is a separate piece of work.** The
`known_issues` table holds **6,600 rows for 660 distinct issues — every entry
duplicated exactly ten times.** There is no UNIQUE constraint on the table and
`loader.load_known_issues_file` is not idempotent, so each seed run duplicates
the whole corpus. This is not cosmetic: it degraded the very run that exposed
it. A request for 20 corpus rows returned **two distinct facts repeated ten
times**, and the model accordingly reported the corpus covered only "fuel
injector issues and float bowl fuel leaks".

`known_issues_for_vehicle` therefore deduplicates on the way out — a
retrieval-quality fix that takes the same request from 2 distinct facts to 22.
**It is not a substitute for the constraint**, which needs a migration and a
table rebuild that must preserve migration 053's severity expression index. That
is recorded as separate work, not folded in here.

**Corrections are reported, never applied silently.** The plan left open whether
a confident correction should rewrite the session. It does not. The garage row
stays the user's, and the analysis context carries an explicit line —
`Vehicle identity: model recorded as 'cbrf4i', read as 'CBR600F4i'` — so the
model is told what was typed *and* how it was read. Swapping a technician's
input without saying so would be a different flavour of the guessing this whole
line of work exists to stop.

## Results

| Metric | Value |
|--------|-------|
| Corpus rows for session 6, before | **0** |
| Corpus rows for session 6, after | **22 distinct** |
| Guards | 18 |
| Mutations run / caught | 6 / 6 (5 on first write, 1 after repair) |
| Vocabulary source | `SELECT DISTINCT` over `known_issues`, no hard-coded marques |
| Regression | **6140 passed / 0 failed** (baseline 6087; +53 guards across 244B and 244C). **One run validates both phases** — 244C was built on top of uncommitted 244B work, so there is no independent green run for 244C alone |

**Verified end-to-end against the recording that started this**, a 2001 Honda
CBR600F4i entered as "Homda cbrf4i" with the complaint in the session notes:

| | before | after |
|---|---|---|
| leak candidates | **0 of 15 findings** | 3, ordered by what to check first |
| corpus grounding | n/a — 0 rows retrieved | 2 of 3 candidates cite real entries |
| marque | guessed "Kawasaki ZX-series or Suzuki GSX-R" | read from the session |

**Key finding: the corpus was never silent — it was unreachable, and nothing in
the stack could tell the difference.** A one-character typo and a colloquial
model name each returned zero rows through the same code path that returns zero
rows for a machine nobody has documented. The fix that matters is not the fuzzy
matching, it is that `method` and `corpus_hits` now make those two outcomes
distinguishable to every caller.
