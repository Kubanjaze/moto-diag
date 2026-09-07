# Phase 211 — BMW R-series boxer twin (1969+)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-07

## Goal

Open Track K (European brand coverage) with the BMW boxer line — airhead,
oilhead, hexhead, camhead and wethead generations, R nineT, R1200/1250
GS and RT — and, before writing a single entry, give the knowledge base
the thing it has never had: a record of where each entry came from.

Every one of the existing 660 known issues carries specific repair
claims ("50–70 VAC per leg at 5000 RPM") with no provenance field, so a
mechanic cannot tell a service-manual figure from a model-generated one.
Track K is 30 phases of exactly that kind of content, authored from
training data rather than a manual on the bench. This phase adds the
`source` column and tags what it adds as **model-generated, needs
mechanic review** — so the content is usable, honest, and reviewable.

CLI: `motodiag kb list --make bmw`, `motodiag kb show <id>`; the guard
is `pytest tests/test_phase211_bmw_r_series.py`.

Outputs:
- Migration 051: `known_issues.source` with a CHECK constraint
- `KnownIssueResponse.source` on the API; `kb show` renders it, with a
  visible warning on unverified content
- `src/motodiag/knowledge/seed/knowledge/known_issues_bmw_r_series.json`
  — 12 entries, every one tagged `model-generated`
- `tests/test_phase211_bmw_r_series.py`
- Mobile `api-types.ts` regenerated

## Existing-code audit (Step 0, per CLAUDE.md)

Nouns audited: `bmw`, `boxer`, `oilhead`, `hexhead`, `known_issues`,
`source`, `provenance`, `verified_by`, `KnownIssue`.

| Finding | Verdict |
|---|---|
| No BMW-specific seed file exists. Three cross-platform entries mention BMW in passing (brake fluid, shaft drive, charging) under other makes. | **Greenfield** for content |
| `known_issues` has 14 columns and no provenance. The `parts` table has `verified_by` (`service-manual` / `forum` / `manual`), so the concept exists in the schema — only for parts. | **Reshape**: add the column, following the `parts` precedent |
| Every read in `issues_repo` is `SELECT *`, so a new column flows to the CLI and API without touching the queries. The loader uses `item.get()` per field, so a `source` key in JSON is already tolerated — it is simply dropped. | Loader + insert + response model need the field; readers do not |
| `make` is free text everywhere (registry, KB, search). No enum to extend. | No registry change |
| Mobile renders no known-issue screen; only `api-types.ts` references the shape. | Regenerate types only |
| The docs advertised 6,600 known issues; the seed holds 660. Fixed on `master` before this branch, with a guard. | Done — but this phase must not reintroduce a number without it |

**A defect found by the audit, fixed on master first:** the knowledge
base was documented at ten times its actual size. Auditing what exists
before adding to it is the only reason that was caught.

## Logic

1. **Migration 051.** `ALTER TABLE known_issues ADD COLUMN source TEXT
   NOT NULL DEFAULT 'unverified'`, with the allowed values enforced by
   a CHECK: `unverified` · `model-generated` · `forum` ·
   `service-manual` · `mechanic-verified`. Existing rows take the
   default, which is the truth: their origin was never recorded.
2. **Loader and insert** carry `source` from JSON to the row, defaulting
   to `unverified` so the 660 existing files load unchanged.
3. **`kb show`** prints the provenance line, and for anything short of
   `service-manual`/`mechanic-verified` prints a one-line warning under
   the fix procedure — where the eye is when deciding whether to trust
   it. `kb list` gains a `Source` column.
4. **API** `KnownIssueResponse.source`; the KB export carries it, so a
   client can render its own warning.
5. **Content.** Twelve entries across the boxer generations — the
   things a shop actually sees: final-drive bearing failure (2005–2011
   hexhead GS), the R1200 paralever pivot, oilhead surging (Motronic
   MA2.4, 1994–2004), hexhead stator/alternator, wethead cam-chain
   tensioner and shift-assist, ABS pump failures (Integral ABS 2002–
   2006), R nineT fork seals and the alternator belt, airhead diode
   board and clutch splines, gearbox input-shaft spline wear, and the
   fuel-strip sensor (2007–2012). Each tagged `model-generated`.
6. **Test** loads the file, asserts count and year coverage, asserts
   every entry carries `source == "model-generated"`, asserts the
   `unverified` default on a legacy file, asserts the CHECK rejects a
   made-up source, and asserts the CLI warning is rendered.
7. **Schema pins** 50 → 51 in the three designed tests.

Data flow: JSON seed → `load_known_issues_file` → `add_known_issue` →
row with `source` → `SELECT *` → CLI panel / API response / KB export.

## Key Concepts

- `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT` — SQLite permits
  NOT NULL on an added column only with a constant default, which is
  what makes the backfill implicit.
- `CHECK (source IN (...))` — an added column can carry a CHECK; it is
  the only mechanism that stops a typo like `model_generated` becoming
  a fourth silent category.
- Provenance vocabulary mirrors `parts.verified_by` (`service-manual`,
  `forum`) and adds the two this phase needs: `unverified` for
  unrecorded origin and `model-generated` for what Track K writes.
- **Content is written to be reviewable, not authoritative.** Each
  entry states the failure, the generations affected, symptoms, causes,
  a procedure and parts — and is tagged so a mechanic who knows the
  bike can confirm or strike it. Figures that are commonly cited in
  BMW owner communities are included; figures I am not confident in are
  omitted rather than invented.

## Verification Checklist

- [ ] Migration 051 applies on a fresh DB and on a DB already at 50;
      the 660 existing rows read `unverified` after
- [ ] The CHECK rejects an unknown `source`
- [ ] Every BMW entry loads with `source == "model-generated"`
- [ ] A legacy seed file (no `source` key) still loads, as `unverified`
- [ ] `motodiag kb show <bmw id>` prints the provenance and the warning
- [ ] `motodiag kb list --make bmw` returns the twelve
- [ ] `/v1/kb/issues/{id}` includes `source`
- [ ] Mobile `api-types.ts` regenerated; `tsc` clean
- [ ] The documented known-issue count guard still passes (660 → 672)
- [ ] Backend regression green; F9 lint clean

## Risks

- **The content is model-generated and says so.** That is the whole
  design, but it bears repeating: nothing in this file has been checked
  against a BMW service manual. The tag makes it reviewable; it does not
  make it right. A mechanic who knows these bikes should read the file
  before it is relied on, and the field exists so their verdict can be
  recorded.
- **Tagging the existing 660 as `unverified` is accurate and may look
  like a downgrade.** It is not a claim they are wrong — it is a
  statement that their origin was never written down. Recording that
  honestly is better than implying a verification that never happened.
- **A warning on every entry becomes wallpaper.** The CLI warning is
  suppressed for `service-manual` and `mechanic-verified`, so it means
  something; if nothing ever reaches those tiers the warning is
  permanent, and that would itself be worth knowing.
