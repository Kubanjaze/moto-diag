# Phase 237 — Phase Log

**European failure patterns, as differential diagnosis by make**
Branch: `phase-237-european-differentials` | Date: 2026-09-08

## Step 0
- Row topics saturated: `stator` 57 files, `rectifier` 47, `cam chain` 39,
  `voltage regulator` 12; `cross_platform_charging` already holds the generic
  causal chain; 26 European make-files hold the instances.
- Reframed as differential diagnosis — the only uncovered axis.

## Research
Paired 6-agent run with 236. This question refuted on genericness: 19 of 34
proposed entries named as duplicates of existing entries, file and title.
Seven source-quality defects applied (SE-R is a model; weep-hole fabricated;
NZD as USD; three others on entries already excluded).

## Failures caught
- Three entries implied an order of checks without stating it — made explicit.
- Searchability matcher missed "canbus" against "CAN-bus" — hyphens normalised.
- Designation-bar guards in 228 and 231 fired; a sweep found five copies
  (227, 228, 231, 232, 233) and exempted all by `european_` prefix.

## Close-out
- 878 → 893. Regression 5846 passed / 0 failed. F9 clean.
- Cleared for roadmap ✅, implementation.md 0.13.48 → 0.13.49, merge.
