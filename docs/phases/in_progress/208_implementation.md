# Phase 208 — Documentation + user guide

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Every document a new reader meets first — both READMEs — describes a
product that no longer exists. They were written for a Windows-hosted
CLI tool and never revised through 200 phases of becoming a macOS-hosted
platform with an iOS app, a shop console, billing and a public share
surface. This phase replaces them, writes the user-facing guides that
have never existed at all (mechanic quickstart, shop workflow, App Store
listing), and — the part that keeps it from rotting again — lands a test
that fails when the docs name a command or route the software does not
have.

CLI: `motodiag --help` is the contract the docs must match; the guard is
`pytest tests/test_phase208_docs.py`.

Outputs:
- `README.md` (backend, rewritten)
- `README.md` (mobile, rewritten)
- `docs/guide/quickstart.md` — diagnose a bike in ten minutes
- `docs/guide/shop-workflow.md` — intake → work order → parts → labour →
  invoice → customer share link
- `docs/guide/api.md` — the HTTP surface, for whoever integrates
- `docs/app-store-listing.md` (mobile) — name, subtitle, description,
  keywords, privacy answers
- `tests/test_phase208_docs.py` — the drift guard

## Existing-code audit (Step 0, per CLAUDE.md)

Nouns audited: `README`, `quickstart`, `guide`, `usage`, `app store`,
`listing`, plus the doc trees of both repos.

**Findings — this is reshape territory, not greenfield, and the existing
material is actively wrong rather than merely thin:**

| Artefact | State | Verdict |
|---|---|---|
| `moto-diag/README.md` (3.4 KB) | Windows venv paths (`.venv/Scripts/activate`, `.venv\Scripts\python.exe`) on a project whose only host is macOS. Architecture tree lists 8 packages; the tree has ~20 — `crm`, `shop`, `accounting`, `scheduling`, `billing`, `reporting`, `push`, `media`, `auth`, `obd_reports` all missing. Describes a two-phase software/hardware product and never mentions the iOS app, work orders, invoicing or share links. Over half its length is F9 pre-commit-hook minutiae. Says "Real CI integration is deferred to Phase 204 / Gate 10" — Phase 204 shipped. Says `--check-model-ids` removal is "targeted Phase 200+" — we are at 208. | **Rewrite** |
| `moto-diag-mobile/README.md` (13.7 KB) | "iOS (macOS only; deferred for this project until Mac access materializes)" — iOS is now the only shipped target, with an `.ipa` built and a TestFlight runbook. Setup instructions use PowerShell windows. | **Rewrite** |
| User guide / quickstart | Does not exist in either repo. | **Greenfield** |
| App Store listing | Does not exist. `docs/testflight.md` covers upload mechanics only, not listing copy. | **Greenfield** |
| `docs/adr/002-new-arch-disabled-pending-ble-plx.md` | Correctly marked **Superseded 2026-07-20**. No action — but see the Podfile finding below. | **Leave** |
| `implementation.md` (275 KB), `phase_log.md` (255 KB), `docs/phases/**` | Development history, correctly maintained, not user-facing. | **Out of scope** |
| `docs/patterns/f9-*.md`, `docs/architecture/*` | Internal engineering docs, current. | **Out of scope** |

**Code defect surfaced by the audit:** `ios/Podfile:1` still sets
`ENV['RCT_NEW_ARCH_ENABLED'] = '0'` even though ADR-002 records that
decision as not implementable at RN 0.85, where New Architecture is
mandatory. The line does not disable anything; it is a build-config
statement that is false. In scope to remove, because a stale config line
misleads exactly like a stale doc — and this one sits in the file a new
contributor reads to understand the build.

## Logic

1. **Establish ground truth before writing a word.** Enumerate the real
   CLI (`motodiag --help` and each group's `--help`), the real route
   list (from the OpenAPI schema regenerated in Phase 207), and the real
   package tree. The docs are written *from* that output, not from
   memory.
2. **Backend README** — rewritten around what the thing is now: a
   diagnostic platform with a CLI, an HTTP API and an iOS client. macOS
   paths. Real architecture tree. The F9 hook section moves to
   `docs/contributing.md`, because it is contributor material and its
   bulk is what pushed the actual product description off the page.
3. **Mechanic quickstart** — the shortest path from install to a
   finished diagnosis, written as a task, not a feature list. Every
   command in it is executed and its real output pasted in.
4. **Shop workflow guide** — the full job: intake a bike, open a work
   order, add parts, log labour, produce an invoice, send the customer a
   share link. This is the product's actual value proposition and it is
   currently undocumented anywhere.
5. **API guide** — the HTTP surface, auth model (API key header, tier
   gating), the ProblemDetail error shape, and the share-link capability
   model. Generated against the schema so path lists cannot drift.
6. **Mobile README + App Store listing** — iOS-first setup; listing copy
   with the metadata App Store Connect actually asks for, including the
   privacy questionnaire answers, which are determined by what the app
   collects (camera, microphone, photo library) and are answerable now.
7. **Drift guard** — `tests/test_phase208_docs.py` parses the markdown,
   extracts every `motodiag <group> <cmd>` invocation and every `/v1/...`
   path, and asserts each exists in the live CLI and the live OpenAPI
   schema. Docs that name something the software lacks fail the build.

Data flow: `motodiag --help` + `app.openapi()` → ground-truth
inventories → prose → the same two inventories re-derived in the test →
assertion. Nothing is sent to any API; this phase is entirely local.

## Key Concepts

- `click.Context` / `CliRunner` — the guard enumerates commands through
  Click's own registry (`cli.commands`, then `group.commands` per group)
  rather than scraping `--help` text, so reformatting help output cannot
  break the test.
- `create_app().openapi()["paths"]` — the same call Phase 207 used to
  regenerate the schema; the route inventory comes from the app object,
  not the committed JSON, so a doc cannot pass by matching a stale file.
- Markdown fenced-block extraction — only ```bash blocks are scanned for
  commands, so prose mentioning a word like "diagnose" is not treated as
  a command claim.
- Deliberate exclusions in the guard: `pip`, `python`, `git`, `npx`,
  `cd`, and anything not starting with `motodiag`. The guard's job is
  our own contract, not the whole shell.
- App Store Connect metadata limits — name ≤ 30 chars, subtitle ≤ 30,
  keywords ≤ 100 total, promotional text ≤ 170, description ≤ 4000.
  The listing is written to those limits and the guard asserts them,
  because discovering a 31-character name at upload time is a wasted
  round trip.

## Verification Checklist

- [x] Every `motodiag` command appearing in any doc exists in the live
      CLI — asserted by test, not by reading
- [x] The guard was proven to FAIL on a bad doc: a fabricated
      `motodiag garrage list` and `/v1/sessions/{session_id}/bogus` were
      injected into the quickstart and both were caught, by file and by
      offender
- [x] Every `/v1/...` path appearing in any doc exists in the live
      OpenAPI schema
- [x] No Windows-only path (`\Scripts\`, `PowerShell`) survives in
      either README — asserted
- [x] The quickstart was executed on this machine and its pasted output
      is real — **except** `motodiag quick` and `motodiag diagnose
      start`, which call a paid API and are documented from their
      `--help` contract instead. The quickstart says so where they appear
- [x] The shop workflow was executed end to end — shop, customer,
      bike link, intake, work order, parts search and seed, part line
      through ordered and received, completion, invoice, void and
      regenerate. **Not executed:** the share-link `curl` calls in step
      7, which are documented from the route contract and the Phase 200
      implementation, not from a live mint
- [x] The workflow run surfaced two real defects (CLI/API tenancy split;
      `list_shops` owner default) and one correct-behaviour-that-reads-
      as-breakage (parts must be `received` before an invoice bills
      them), now documented as the precondition it is
- [x] App Store listing fields are within Apple's character limits, and
      the doc's own stated counts are asserted to equal the real ones —
      all three were wrong when written
- [x] Every permission the Info.plist declares is documented in the
      listing, and no location permission is declared — asserted
- [x] `ios/Podfile` no longer claims to disable New Architecture
- [x] `pod install` succeeds after the Podfile edit, and the generated
      `Pods-MotoDiag.{debug,release}.xcconfig` still carry
      `-DRCT_NEW_ARCH_ENABLED=1` — which is the evidence that the removed
      line was inert. A full Xcode app build was **not** re-run
- [x] Backend regression green; F9 lint clean; mobile `tsc` clean, lint
      0 errors

## Risks

- **A docs phase is the easiest place to produce theatre.** Word count
  is not the deliverable. The guard test and the executed-and-pasted
  outputs are what make this phase falsifiable; without them it is
  prose that will be stale again by Phase 212.
- **The guard can only check names, not truth.** It proves a documented
  command exists. It cannot prove the documented command does what the
  sentence next to it claims. Executing the quickstart and the shop
  workflow by hand is the only cover for that, and it covers those two
  paths only.
- **App Store listing copy is a marketing artefact submitted under the
  user's developer account.** It is drafted here, not submitted, and
  the privacy answers must be confirmed against the final binary's
  actual entitlements before anyone files them.
- **Removing the Podfile line touches the build.** It should be inert —
  RN 0.85 ignores it — but "should be inert" is exactly the kind of
  claim this project has been burned by. It gets a real build.


## Deviations from Plan

**The phase found five code defects it did not plan to find.** All were
surfaced by the plan's own anti-theatre commitment — executing the
commands rather than describing them — and all are fixed here rather
than filed, because each one falsified something the docs would
otherwise have asserted.

1. **`motodiag --version` reported 0.1.0 against a 0.6.0 package.** The
   version was a literal in `src/motodiag/__init__.py` *and* a second
   literal in `Settings.version`, neither of which tracked
   `pyproject.toml`. `/v1/version` and the OpenAPI `version` field were
   equally stale. A version number that lies routes a bug report to the
   wrong release. Both literals now derive from installed package
   metadata; `pyproject.toml` is the single source. The Phase 01 pin
   that asserted `== "0.1.0"` had been *agreeing with the bug*, so it
   now asserts internal consistency instead of a specific number.

2. **The CLI wrote customers the API could never read.** Phase 207 gave
   `customers` a `shop_id` and taught the API to scope on it, but
   `motodiag shop customer add` kept inserting NULL — and the API serves
   a NULL-`shop_id` row to no shop. Every customer added from the
   terminal was invisible in the mobile app, silently, with both sides
   passing their own tests. Found by writing the shop workflow guide,
   which required running it. `tests/test_phase208_cli_api_parity.py`
   now holds the seam.

3. **`list_shops()` defaults to `owner_user_id=1`.** The helper written
   for defect 2 called it bare and so saw no shops whenever the operator
   was any other user, turning "which of your shops?" into "you have no
   shop". Caught by the parity test failing on a fixture whose owner was
   user 2. Now passes `owner_user_id=None` explicitly, with a comment
   saying why.

4. **The iOS Info.plist declared a location permission for a feature
   that does not exist.** `NSLocationWhenInUseUsageDescription`
   described tagging work orders with a bay location; there is no
   location dependency and no location API call anywhere in the app. A
   declared-but-unused permission is a review question with no good
   answer. Removed.

5. **The App Store listing's own stated character counts were all three
   wrong** on first writing — stated from estimate rather than computed.
   The guard now asserts the printed counts equal the real ones, which
   is the only reason this is a footnote rather than a rejected upload.

**Scope added:** `docs/contributing.md` was not in the plan. The F9
pre-commit material occupied over half the old README and is
contributor-only; moving it was the difference between a README that
describes the product and one that describes its git hooks.

**Scope reduced:** the plan said "every command in the guides is
executed and its real output pasted." True except for the two AI
commands (`motodiag quick`, `motodiag diagnose start`), which call a
paid API. They are documented from their `--help` contract and flagged
in the quickstart as costing money. Saying so here rather than letting
the claim stand unqualified.

**Android New-Arch flag annotated, not flipped.** The plan called for
removing the misleading `RCT_NEW_ARCH_ENABLED=0`; that was done on iOS
and verified by `pod install` (the generated Pods still carry
`-DRCT_NEW_ARCH_ENABLED=1`, which is what proves the line was inert).
The Android `newArchEnabled=false` got a comment instead of a flip:
nobody has run an Android build since iOS became the shipped target,
and changing a build flag you cannot test is not an improvement.

## Results

| Metric | Value |
|--------|-------|
| CLI commands enumerated | 255 leaf commands, 24 groups |
| HTTP surface enumerated | 80 paths, 103 operations, 17 tags |
| Commands the old README documented | 3 |
| User-facing docs before | 2 READMEs, both describing a Windows-hosted CLI |
| User-facing docs after | 2 READMEs + 3 guides + contributing + App Store listing |
| Code defects found and fixed | 5 |
| Drift-guard tests | 18 (docs) + 7 (CLI/API parity) |
| Backend regression | 4879 passed / 0 failed |
| F9 lint | clean |
| Mobile `tsc` | clean; lint 0 errors |

**Key finding: writing the documentation was a better test than the test
suite.** Two of the five defects — the CLI/API tenancy split and the
`list_shops` owner default — were invisible to 4,854 passing tests
because every test exercised one side of a seam. Documenting the shop
workflow meant *walking* it, and walking it crossed the seam on the
first step. The suite asserted that each half worked; only the guide
asked whether they worked together.

The corollary is uncomfortable and worth writing down: a docs phase
scheduled near launch is not a formality. It is the first time anyone
uses the product the way a stranger would, and that is a different act
from testing it.
