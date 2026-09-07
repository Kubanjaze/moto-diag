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
