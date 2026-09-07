# Phase 211 — BMW R-series boxer twin (1969+)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-07

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
5. **Content.** Twelve entries across the boxer generations, as built:
   final-drive crown-wheel bearing (hexhead 2005–2011) · oilhead
   surging (Motronic MA2.4, 1994–2004) · rear-main/input-seal leak
   contaminating the dry clutch · gearbox input-shaft spline wear ·
   Hall-effect sensor wiring (oilhead) · Integral ABS servo-pump failure
   (2001–2006) · fuel-level strip sensor (hexhead 2007–2012) · alternator
   drive belt (oilhead/hexhead/R nineT) · water-pump seal weep (wethead
   2013+) · diode board (airhead) · alternator rotor and brushes
   (airhead) · Paralever pivot bearings. Each tagged `model-generated`.
   The v1.0 list also named a wethead cam-chain tensioner, shift-assist
   and R nineT fork entries; those were dropped rather than padded — see
   Deviations.
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

- [x] Migration 051 applies on a fresh DB (schema 51) and on a DB built
      to 50 with a pre-existing row — that row reads `unverified` after
- [x] The CHECK rejects `model_generated` (underscore) with
      `IntegrityError`; all five vocabulary values are accepted
- [x] Every BMW entry loads with `source == "model-generated"`, and the
      tag is in the JSON itself, not only the loader default
- [x] Every BMW description states "general knowledge" in its own text,
      so a reader with no schema in front of them is still told
- [x] A legacy seed file (no `source` key) loads as `unverified`
- [x] `motodiag kb show <bmw id>` prints `Source: model-generated` and
      the warning under the fix procedure — captured from a real run
- [x] `service-manual` content renders its source with **no** warning,
      so the warning can be absent and therefore means something
- [x] `motodiag kb list --make bmw` returns twelve with a `Source` column
- [x] `/v1/kb/issues/{id}` includes `source`; OpenAPI emits a strict
      five-value enum; mobile `api-types.ts` regenerated as a typed
      union; `tsc` clean
- [x] The documented known-issue count guard fired on 660 → 672 exactly
      as designed, and the four docs were corrected
- [x] F9 lint clean — after it correctly flagged `source: str` and the
      field was retyped as a `Literal`
- [x] Backend regression 4930 passed / 0 failed

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


## Deviations from Plan

**The F9 lint caught me typing the field as `str`.** The plan said
`KnownIssueResponse.source`; the first cut typed it `str`, and
`--check-pydantic-literal-vs-check` flagged it against the migration's
CHECK constraint before anything was regenerated. Retyped as a
module-level `Literal` alias so the OpenAPI schema emits an enum and the
mobile codegen produces a typed union. This is the F37 discipline —
Literal-vs-CHECK drift — enforced by the lint *before* the types were
generated, which is the first time that guard has fired in the
direction it was built for.

**The knowledge-base count guard fired.** Adding twelve entries moved
the seed from 660 to 672, and the Phase 208 guard failed on four docs
that still said 660. That is the guard working: the number in the docs
is now tied to the seed files, and a content phase cannot silently drift
it. Updated to 672.

**One test of mine assumed a raw JSON column.** `search_known_issues`
already deserialises `parts_needed`; the assertion now accepts either
shape, since it is a content check and not a serialisation one.

**Content scope held at twelve.** Entries where I could not state a
procedure without inventing a figure — wethead starter sprag, R nineT
fork specifics — were left out rather than padded. The file says what it
knows and no more.

## Results

| Metric | Value |
|--------|-------|
| Known issues | 660 → 672 |
| BMW entries | 12, spanning airhead (1970) → wethead (2023) |
| Entries tagged `model-generated` | 12 of 12 |
| Existing entries now `unverified` | 660 |
| Schema | 50 → 51 |
| Phase tests | 26 |
| Backend regression | 4930 passed / 0 failed |
| F9 lint | clean (1 finding, fixed) |
| Mobile | types regenerated, `tsc` clean |

**Key finding: the honest label cost nothing and changes everything
downstream.** Adding `source` was one migration, one parameter and a
render function. What it buys is that Track K's remaining 29 phases can
proceed without pretending — every entry says what it is, the CLI says
it out loud, the API types it, and a mechanic who knows the bike can
promote an entry to `mechanic-verified` and make the warning go away.
The alternative was 300 more entries indistinguishable from the 660
whose origin nobody recorded.
