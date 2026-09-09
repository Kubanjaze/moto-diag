# Phase 240B — Closing the Track K audit debt

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-09

## Goal

Close the audit debt Track K left open when Gate 12 shipped: re-run the
contradictions dimension **without the `slice(0, 8)` cap** that hid half its
findings, fix the six confirmed cross-file contradictions in section A of
`TRACK_K_AUDIT_DEBT.md`, and repair the guard/gate defects B1–B5 plus the
provenance labelling rule in section C.

The debt document's own warning is the reason this phase exists: the
contradictions auditor reported **16** findings, the workflow submitted only the
first **8** for verification, and 6 of those were confirmed. **Eight were never
examined.** Section A is a confirmed subset, not the full set, and nobody may
call the corpus clean until the dimension runs uncapped.

Every one of these is a defect no single phase's tests could have caught,
because each file was written and reviewed against its own sources and never
against its siblings.

CLI: no new commands. This phase changes seed content, tests and docs only.

Outputs:
- `docs/phases/completed/TRACK_K_AUDIT_DEBT_2.md` — the uncapped re-run's findings
- corrected entries in 8 `known_issues_*.json` seed files
- `tests/test_phase240b_audit_debt.py` — the new guards
- edits to 14 existing test files (guard-family repairs)

## Logic

### Part 1 — Re-run the contradictions dimension uncapped

The original audit script lived in the workflow journal, not the repo, so it
cannot be re-executed. The dimension is re-run as a fresh adversarial sweep over
the same corpus (30 Track K knowledge files, 257 entries, 8 DTC files, the
adapter and parts catalogues), partitioned six ways so no slice is capped:

1. BMW cluster vs the four cross-make files
2. Ducati cluster vs the four cross-make files
3. KTM cluster vs the four cross-make files
4. Triumph cluster vs the four cross-make files
5. Aprilia + MV Agusta cluster vs the four cross-make files
6. The four cross-make files against each other and against the catalogues

Each finding must carry verbatim quotes from both sides, a same-subject
argument, the operative cost, a reachability trace through the real retrieval
predicate, and a recorded kill attempt. Findings that survive are written to
`TRACK_K_AUDIT_DEBT_2.md`. **The re-run's deliverable is the verified finding
list, not a corpus-wide rewrite** — fixing what it turns up is scheduled, not
smuggled into this phase.

### Part 2 — Fix the six confirmed contradictions (section A)

Each follows its verifier's `corrected_fix`, not the auditor's recommendation;
the auditor's first option is wrong or tree-breaking in five of the six.

- **A1 BMW ELAST belt** (`bmw_r_series[7]`). Keep 1994–2023 and make the entry
  self-contained: state the poly-V/ELAST split, that the part number is the
  discriminator, and that 2013-on liquid-cooled boxers have no belt at all.
  Do **not** rescope to 2003 — `test_every_generation_is_covered` is
  parametrised (2018, 2) and only entries 7 and 8 cover 2018.
- **A2 BMW final drive** (`bmw_r_series[0]`). Make generation-aware in place.
  Do **not** split the entry — the count is pinned in four places. Strike the
  interval cause and the shorten-the-interval advice; qualify the glitter check;
  add that the bearing and seal carry individual part numbers.
- **A3 Euro 4 OBD** (`bmw_electrical[0]`). Correct **four** sites, not one:
  description, `causes[1]`, fix step 1 (three tiers, not two) and fix step 7.
  Step 7 is the line that costs a shop work and survives a description-only fix.
  Do **not** re-source to `regulation`.
- **A4 Ducati desmo time element** (`ducati_desmo[4]`). Phrase as a negative
  instruction plus routing, not a flat positive "distance-only" claim — the
  entry spans 1993–2026 and Phase 238 read only 2004-on sheets. Also replace the
  indexed symptom string `older ducati overdue by years`, which is what makes an
  age-based query land here.
- **A5 KTM valve train** (`european_intervals[4]` **and** `[6]`). Remove the
  bare "KTM" from the shim-under-bucket clause in the description **and** the
  `model` field. Do not invent an LC8/LC8c-vs-LC4 split — the corpus holds no
  manufacturer source for any KTM valve-train type.
- **A6 MV swingarm bolt** (`mv_agusta_triple[2]`). Rewrite the description,
  `causes[3]` and fix step 4, **and** change the test that pins the false
  doctrine in the same edit, or the correction is cosmetic.

### Part 3 — Guard and gate defects B1–B5 and the section C rule

- **B1** Add a trailing `Forum tip:` step to the two untipped `forum` entries
  and re-scope the two blanket assertions that currently forbid it. Also
  re-scope the eight other negative-only copies to the biconditional so the
  family stops being correct-by-accident.
- **B2** **No change.** Verification rejected this. `unverified` is reserved for
  legacy rows with no recorded origin and sits inside Gate 2's forum-derived
  population; the corpus's own convention files a documented absence as
  `service-manual`.
- **B3** Replace the eight constant cumulative pins with the invariant form,
  deriving both the total and the make-filtered count from the JSON. Keep each
  test's existing scope; only the two block tests glob.
- **B4** **Not as framed** — Rule 4 is enforced in four phase files. The real
  gap: Aprilia and MV Agusta shadow zero generic codes, so pin the zero with a
  tripwire that fires when that changes.
- **B5** De-vacuum the three dead guards and the six dead discriminators. Every
  `_asserts` probe must use a literal term in 216–219 and a raw regex in
  221–223, or the probe asserts the deadness it is meant to detect.
- **C** Decide and apply the rule, then enforce it. Demote the eight
  vendor-documentation entries in `european_tooling.json` to `model-generated`.

## Key Concepts

**The weakest-link provenance rule** (section C's deliverable), reconstructed
from what Phase 235 already recorded and tested. An entry's `source` names the
weakest link in the evidence chain its load-bearing claim rests on:

| value | means |
|---|---|
| `regulation` | the entry quotes legal text and the claim *is* the requirement |
| `service-manual` | a primary official document **states** the claim. A documented absence counts. |
| `model-generated` | vendor/third-party published material, or inference across sources |
| `forum` | owner reporting or marque-community consensus |
| `unverified` | legacy rows only — origin never recorded. Never assign to Track K content. |

**Gate 2's two halves are not a biconditional.** Forward: ≥90% of the
forum-derived population (`unverified` + `forum`) carries `Forum tip:`.
Reverse: **no** non-forum-derived entry may carry one, absolutely. The strict
per-file biconditional used by phases 225B/237/239 is a stronger local rule, and
it is correct for files whose forum entries are all tipped.

**Constant-for-invariant.** Assert the property, not the number. A count derived
from the same JSON the test loads survives corpus growth; a literal does not.

**Mention versus use.** Every new regex needs a negation-aware pass — but a
positive assertion in the title must override a disclaimer exemption, or a scope
note makes a real regression invisible.

**Earning the shadow.** `dtc_repo.get_dtcs` resolves make-specific before
generic, so a make row restating the generic row hides it. A make row must
differ in `common_causes` **and** `fix_summary`. `description` is excluded on
purpose — it is the shared SAE code title.

**Sweep by shape, not by name.** The same assertion exists under different names
across phases. A name-keyed sweep missed family members three times.

## Verification Checklist

- [ ] Contradictions dimension re-run with no cap; findings written up with
      verbatim quotes, reachability traces and kill attempts
- [ ] All six section A contradictions corrected at every site the verifier named
- [ ] No entry added, removed or split — corpus stays at 917, so every pinned
      count and the Phase 208 doc-count guard stay green
- [ ] Exactly zero untipped `forum` entries; forum-tip guards assert the
      biconditional rather than the negative half alone
- [ ] The eight constant cumulative pins derive their numbers from the JSON
- [ ] Aprilia/MV zero-shadow state pinned with a tripwire, not a skip
- [ ] Every de-vacuumed guard mutation-tested: reintroduce the defect, confirm
      the guard fails, revert
- [ ] `european_tooling.json` is 13/13 `model-generated`; a positive test
      enforces the vendor rule
- [ ] `tests/test_phase236_european_tooling.py` and
      `docs/phases/completed/236_implementation.md` updated off the 8/5 split
- [ ] Full regression at or above the 5954 baseline, 0 failed

## Risks

- **Pinned entry counts.** Four places pin the BMW file at 12 and the block at
  24/30/41/44; Gate 12 ties README's figure to the live seed. Mitigated by
  editing in place and adding no entries — but any accidental split fails all of
  them at once.
- **The forum-tip fix turns a green test red.** Adding the marker to
  `triumph_bonneville[10]` fails `test_no_entry_fabricates_a_forum_tip`, which
  asserts the negative half over all 11 entries. The test must change in the
  same commit.
- **A leading `Forum tip:` breaks the predictor.**
  `predictor._extract_preventive_action` returns everything after the marker, so
  a leading tip yields the rest of the procedure truncated mid-sentence. All 15
  compliant entries put it last; the new ones must too.
- **The A6 fix can land silently green.** `break\w*` does not match "broke", so
  the natural rewording scores zero against the existing negation-window regex.
  The test must be inverted, not relied upon.
- **Two verifiers disagree on B1.** The MV-sprag verifier rejected it because a
  test forbids the tip; the Bonneville verifier identified that same test as the
  mis-scoped denylist. Resolved in favour of the latter: a guard that enforces
  the violation is not evidence the violation is permitted.
- **BSD sed has no `\b`.** Any doc-count edit by sed can silently no-op. Use
  Python for text edits that must not fail quietly.
- **Scope pressure.** The uncapped re-run is expected to surface more
  contradictions than section A holds. Fixing them all in this phase would mean
  abbreviating the care each entry gets, which the working agreement forbids.
  They are documented and scheduled instead.
