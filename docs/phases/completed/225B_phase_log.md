# Phase 225B — Phase Log

**KTM mid-size Adventure line (390 / 790 / 890 Adventure)**
Branch: `phase-225b-ktm-midsize-adventure` | Date: 2026-09-08

## Step 0 — existing-code audit

- `390/790/890 Adventure` appeared **zero times in 855 entries**; `Super
  Adventure` appeared 25 times and is all Phase 221's 1290. The open item was
  not a tracking omission with content behind it — there was no content.
- Phase 222 owns the Duke naked models, Phase 224 the LC8c family, Phase 225
  engine management. Engine-internal content here would shadow all three.
- Phase 221 and 222 already assert model boundaries from their side; this
  phase asserts the reciprocal.

## Research

One capped 6-agent run (2 questions × 2 refuter lenses). 6/6 returned;
3 refuted, 1 clean. Five corrections forced — see the implementation doc.

## Failures caught during the build

- Three of my own test selectors were wrong, all the same family:
  `[Dd]rawn from` missed "Drawn **verbatim** from"; a mileage guard for the
  Phase 238 boundary caught an owner's report of *when a part failed* rather
  than a service interval; and a searchability matcher used exact substrings,
  so "location" missed "located". Fixed at the right level rather than by
  loosening the assertions.
- BSD `sed` does not support `\b`, so the first doc-count update silently did
  nothing and the Phase 208 guard caught it.

## Close-out

- 855 → 865 known issues. Regression 5791 passed / 0 failed. F9 clean.
- Cleared for: roadmap row 225B, implementation.md row + 0.13.46 → 0.13.47,
  merge, delete branch.
- **This closes the KTM block's open item, carried since Phase 223/225.**
