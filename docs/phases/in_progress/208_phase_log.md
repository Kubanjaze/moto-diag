# Phase 208 — Documentation + user guide — Phase Log

**Status:** 🔨 In progress
**Started:** 2026-09-07
**Repos:** `Kubanjaze/moto-diag` + mobile, branch `phase-208-documentation`

---

### 2026-09-07 — Plan v1.0 + Step 0 audit

- **Step 0 finding: this is reshape territory and the existing docs are
  wrong, not merely thin.** Both READMEs were written for a
  Windows-hosted CLI and never revised through 200 phases of becoming a
  macOS-hosted platform with an iOS app. The backend README tells a new
  reader to run `.venv/Scripts/activate` — which fails immediately on
  the only host this project has — lists 8 of ~20 packages, never
  mentions work orders, invoicing, share links or the iOS app, and
  spends over half its length on F9 pre-commit-hook minutiae.
- **The mobile README says iOS is "deferred until Mac access
  materializes".** iOS is the only shipped target; there is an `.ipa`
  and a TestFlight runbook.
- **User guide, quickstart and App Store listing do not exist** in
  either repo. That half of the phase is genuinely greenfield.
- **Code defect surfaced by the audit:** `ios/Podfile:1` still sets
  `RCT_NEW_ARCH_ENABLED = '0'` while ADR-002 records that decision as
  not implementable at RN 0.85, where New Arch is mandatory. The line
  disables nothing — it is a false statement about the build sitting in
  the file a new contributor reads first. In scope.
- **Anti-theatre commitment made in the plan.** A docs phase is the
  easiest place to mistake word count for work. Two things make this
  one falsifiable: every command in the docs is executed and its real
  output pasted, and `tests/test_phase208_docs.py` asserts that every
  `motodiag` command and every `/v1/...` path named in any doc actually
  exists — reading the live Click registry and the live OpenAPI schema,
  not scraped help text or the committed JSON.
- **Stated limit:** the guard proves a documented command exists. It
  cannot prove the sentence beside it is true. Only executing the
  quickstart and shop workflow covers that, and only for those paths.

### 2026-09-07 — Built. The documentation was a better test than the test suite.

- **Ground truth first.** Enumerated the real surface before writing a
  word: **255 leaf commands across 24 groups**, **80 paths / 103
  operations across 17 tags**. The README documented three commands.
- **Shipped:** both READMEs rewritten, `docs/guide/{quickstart,
  shop-workflow,api}.md`, `docs/contributing.md` (the F9 hook material
  that had occupied over half the README — contributor content that had
  pushed the product description off the page), and the mobile
  `docs/app-store-listing.md`.
- **Five code defects, all found by running what I was about to
  describe:**
  1. `motodiag --version` reported **0.1.0 against a 0.6.0 package** —
     the version was a literal in `__init__.py` and a second literal in
     `Settings.version`, neither tracking `pyproject.toml`.
     `/v1/version` and the OpenAPI `version` field were equally stale.
     Now derived from installed metadata. The Phase 01 pin asserting
     `== "0.1.0"` had been **agreeing with the bug**; it now asserts
     internal consistency instead of a number.
  2. **The CLI wrote customers the API could never read.** Phase 207
     gave `customers` a `shop_id` and scoped the API on it; `motodiag
     shop customer add` kept inserting NULL, which the API serves to no
     shop. Every customer added from the terminal was invisible in the
     mobile app — silently, with both sides passing their own tests.
     This is mine: I fixed one side of a seam in 207 and tested only
     that side.
  3. `list_shops()` **defaults to `owner_user_id=1`**, so the helper
     written for defect 2 saw no shops whenever the operator was any
     other user. Caught by the parity test failing on a fixture whose
     owner was user 2.
  4. The iOS Info.plist declared **`NSLocationWhenInUseUsageDescription`
     for a feature that does not exist** — no location dependency, no
     location API call anywhere. Removed; a declared-but-unused
     permission is a review question with no good answer.
  5. The App Store listing's **own stated character counts were all
     three wrong**, stated from estimate rather than computed.
- **Two drift guards, both proven to fail before they were trusted.**
  `test_phase208_docs.py` (18 tests) reads the live Click registry and
  the live OpenAPI schema — a fabricated `motodiag garrage list` and
  `/v1/sessions/{session_id}/bogus` were injected and both were caught
  by file and offender. `test_phase208_cli_api_parity.py` (7 tests)
  holds the CLI↔API seam that defect 2 fell through.
- **Correct behaviour that reads as breakage, documented rather than
  "fixed":** an invoice bills only parts marked `received` or
  `installed` — you do not bill for a part still on a truck. A part left
  at `open` silently misses the invoice and the total looks right while
  being wrong. The guide now says so at the point where it bites.
- **iOS New-Arch line removed and verified**: `pod install` succeeds and
  the generated xcconfigs still carry `-DRCT_NEW_ARCH_ENABLED=1`, which
  is what proves the removed line was inert. The Android twin was
  **annotated, not flipped** — nobody has run an Android build since iOS
  became the shipped target, and changing a build flag you cannot test
  is not an improvement.
- **Honest gaps, stated in the doc rather than papered over:** the two
  AI commands were not executed (they cost money) and are documented
  from their `--help` contract; the share-link `curl` calls in the
  workflow guide were not run against a live mint; no full Xcode app
  build was re-run after the Podfile edit.
- **Key finding: two of the five defects were invisible to 4,854
  passing tests** because every test exercised one side of a seam.
  Documenting the shop workflow meant walking it, and walking it crossed
  the seam on the first step. A docs phase near launch is not a
  formality — it is the first time anyone uses the product the way a
  stranger would, which is a different act from testing it.
