# Phase 208 — Documentation + user guide

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-07

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

- [ ] Every `motodiag` command appearing in any doc exists in the live
      CLI — asserted by test, not by reading
- [ ] Every `/v1/...` path appearing in any doc exists in the live
      OpenAPI schema
- [ ] No Windows-only path (`\Scripts\`, `PowerShell`) survives in
      either README
- [ ] The quickstart was executed start to finish on this machine and
      its pasted output is real
- [ ] The shop workflow was executed against a live server, not
      described from the route list
- [ ] App Store listing fields are within Apple's character limits
      (asserted)
- [ ] `ios/Podfile` no longer claims to disable New Architecture
- [ ] iOS build still succeeds after the Podfile edit
- [ ] Backend regression green; F9 lint clean; mobile `tsc` clean

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
