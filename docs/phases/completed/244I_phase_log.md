# Phase 244I — Model vocabulary + model junction — phase log

**Status:** ✅ Complete
**Opened:** 2026-09-10 | **Closed:** 2026-09-10
**Repo:** https://github.com/Kubanjaze/moto-diag

---

## 2026-09-10 — Plan v1.0 written

The sibling of Phase 244F, and the harder one. `model` carries the same list and
prose structure as `make` did — 221 of 363 distinct values — but with a hazard
`make` never had: **entries name models in order to exclude them.**

> `390 Adventure, 790 Adventure, 890 Adventure — as distinct from 1290 Super Adventure`
> `Hypermotard 1100 (not EVO)`
> `950 and 990 LC8 on the fiche; 1190/1290 fitment unknown, not excluded`

Naive extraction would attach those entries to the exact machines their authors
wrote them to rule out — and a wrong model of the *right* marque is not obviously
wrong to a technician. It reads as a machine-specific match and gets acted on.

**Step 0 nearly killed the phase.** Deriving the vocabulary from clean
single-value entries — the shape that looked like 244F — made **4 of ~298**
prose rows gain a precise model. Models are an open vocabulary and the ones
named in prose mostly appear nowhere as a clean value. Applying what 244F
*actually* did, augmenting the vocabulary with clean tokens split out of the
list values, took that to **271**. Same lesson twice: the vocabulary that
repairs a column comes out of the strings that broke it.

**Two further findings changed the design.** Extraction must truncate at the
first contrast marker and read only what precedes it — verified against both KTM
Adventure entries, which yield their covered models and zero excluded ones. And
substring dedup drops real machines: `"390 Adventure, 390 Adventure R, 890
Adventure"` loses *390 Adventure* because it sits inside *390 Adventure R*.
Dedup has to be position-aware — a match is redundant only when every one of its
occurrences is contained in another.

**That dedup bug is already in Phase 244F**, latent because no marque in the
16-value set is a substring of another. The corrected helper will be shared and
244F will adopt it.

Worth stating what this phase is not for. Phase 244E already makes prose-model
rows reachable, labelled `make_other_model`. This is about precision, so a bad
extraction has no upside to trade against — which is why every rule is
conservative and silent when unsure.


---

## 2026-09-10 — Built

Migration 056 adds `known_issue_models`, backfilled in its own transaction.
**254 of 286 prose rows now carry a precise model**, and the safety property
holds corpus-wide: zero indexed models are absent from the covered part of their
source value.

**The plan's exclusion mechanism was wrong and this phase's own guard proved
it.** v1.0 truncated at the first contrast marker. A parametrised guard over
every phrasing found `"390 Adventure; 390 Duke not established"`, where the
excluded model *precedes* the marker and survives truncation. Exclusion is
clause-scoped instead: negated parentheticals removed, value split into clauses,
any clause carrying a marker dropped whole. Truncation looks right against the
examples anyone would pick — they all put the exclusion last. Enumerating all
fourteen contrast values rather than sampling is what found the one that does
not.

**My fixture was unrepresentative for the second phase running.** Three
mutations escaped because it lacked shapes the corpus has — `"... and R"`
producing a bare `R` that would match almost any text, and a comma inside
parentheses tearing a year qualifier in half. Adding them caught all three, and
one surfaced a defect nothing had flagged: `2018+` was entering the vocabulary
as a machine. **A fixture built from imagination tests the corpus you expected,
not the one you have** — 244F had the same problem with Triumph and Moto Guzzi.

**And one guard passed for the wrong reason.** The bracket mutation still
survived after the fixture gained a bracket case, because the fragment was 30
characters and hit the length check first. Shortened so the check under test is
the one that fires.

**A latent defect in Phase 244F was fixed here.** `extract_marques` used naive
substring dedup, which drops a shorter name whenever a longer one contains it.
Harmless for marques, fatal for models: `390 Adventure` loses to `390 Adventure
R` though both are named and distinct. The corrected position-aware helper is
shared.

34 guards, 7/7 mutations caught, F9 lint clean.
