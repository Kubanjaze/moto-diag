# MotoDiag Phase 125 — Quick Diagnosis Mode (Bike Slug + Top-Level Shortcut)

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
UX sugar on top of Phase 123's `diagnose quick`. Adds a bike slug resolver so mechanics don't need numeric vehicle IDs, plus a top-level shortcut `motodiag quick "<symptoms>"` that skips the `diagnose` subgroup. Example target UX:

```
motodiag quick "won't start when cold" --bike sportster-2001
```

Phase 123 already handles all the heavy lifting (session creation, AI call, persistence, tier gating). Phase 125 is pure ergonomics: new helpers in `cli/diagnose.py` + one new option on the existing `diagnose quick` command + one top-level `quick` command that delegates via Click's `ctx.invoke()`.

CLI:
- `motodiag quick "<symptoms>" [--bike SLUG | --vehicle-id N] [--description TXT] [--model haiku|sonnet]` — top-level shortcut
- `motodiag diagnose quick --bike SLUG --symptoms "..."` — extended existing command, `--bike` alternative to `--vehicle-id`

Outputs: extended `src/motodiag/cli/diagnose.py` (~180 LoC added), modified `cli/main.py` (one-line wire-up), 34 new tests. **No migration, no new file.**

## Logic

### 1. Helpers added to `cli/diagnose.py`
- `SLUG_YEAR_MIN = 1980` and `SLUG_YEAR_MAX = 2035` — module constants bounding which trailing integers count as year hints.
- `_parse_slug(slug: str) -> tuple[str, Optional[int]]` — splits on the LAST hyphen. If the final token parses as an int in `[SLUG_YEAR_MIN, SLUG_YEAR_MAX]`, returns `(stem_lowercased, year)`. Otherwise returns `(full_slug_lowercased, None)` — the slug is treated as stem-only with no year constraint. Handles empty, whitespace, and out-of-range years gracefully.
- `_resolve_bike_slug(slug, db_path) -> Optional[dict]` — 4-tier SQL match against `vehicles` with `LOWER(...)` for case-insensitivity, ordered by `created_at, id` for deterministic ambiguous-match behavior:
  1. **Exact model match**: `LOWER(model) = stem` (and year if present)
  2. **Exact make match**: `LOWER(make) = stem` (and year)
  3. **Partial model**: `LOWER(model) LIKE '%stem%'`
  4. **Partial make**: `LOWER(make) LIKE '%stem%'`
  
  First hit wins. Returns None if all four tiers miss.
- `_list_garage_summary(db_path, limit=10) -> str` — helper for the "unknown slug" error message; builds a short multiline string listing `id, year make model` of recent vehicles so the user can see what they could have typed.

### 2. Extended `diagnose quick` command
- Added `--bike TEXT` option alongside existing `--vehicle-id INT`.
- **Both provided**: `--vehicle-id` wins, yellow warning printed (`"⚠ Both --bike and --vehicle-id given; using --vehicle-id."`).
- **Neither provided**: ClickException with a clear error instructing the user to provide one.
- **`--bike` only**: `_resolve_bike_slug` runs; hit → uses row's `id`; miss → ClickException with `"No bike matches slug '...'. Your garage:"` + `_list_garage_summary` output (or `"... Garage is empty."` if the garage is empty).
- Existing flow after vehicle resolution is unchanged — Phase 123 does all the heavy lifting.

### 3. New top-level `motodiag quick` command
- New `register_quick(cli_group)` function added alongside the existing `register_diagnose(cli_group)`.
- Pulls the already-registered `diagnose quick` command object from `cli_group.commands["diagnose"].commands["quick"]` (raises RuntimeError if `register_diagnose` wasn't called first).
- Defines a top-level `@cli_group.command("quick")` that takes a positional `symptoms` argument plus the usual flags, then uses `ctx.invoke(quick_cmd, symptoms=symptoms, ...)` to delegate. Single source of truth for the diagnosis flow.
- Wired into `cli/main.py` via `register_quick(cli)` called immediately after `register_diagnose(cli)`.

### 4. Tests (34 across 5 classes)
- **`TestParseSlug`** (9): year-suffix split, no-year case, out-of-range year treated as stem, whitespace trimming, boundary years (1980, 2035), case-insensitive, empty slug.
- **`TestResolveBikeSlug`** (11): exact model + year, partial model + year, make match when model doesn't, partial make (`"harley"` → Harley-Davidson), no match returns None, year filter exclusion, case-insensitive, ambiguous returns first-by-created_at, empty slug, slug without year matches by model.
- **`TestDiagnoseQuickBikeSlug`** (5): happy path with slug, unknown slug error with garage hint, unknown slug empty garage, both flags prefers ID + warning, neither flag errors.
- **`TestTopLevelQuick`** (6): bike slug path, vehicle-id path, missing-symptoms error, description passthrough, unknown slug error propagates, sonnet-on-individual HARD paywall mode exits with tier error.
- **`TestRegression`** (3): existing vehicle-id path unchanged + still persists session, top-level `quick` command registered, `diagnose quick` still present as subcommand.

All AI calls mocked via `patch("motodiag.cli.diagnose._default_diagnose_fn", fn)` — same pattern as Phase 123. Zero live tokens.

## Key Concepts
- **Pure sugar phase**: no new substrate, no new tables, no new persistence logic. The win is UX friction removal.
- **Slug format `model-year`** is deliberately loose. A mechanic types what feels natural; 4-tier match catches exact and partial hits; failure prints the garage so they see what they could have typed.
- **Slug matching priority** (4 tiers, deterministic by `created_at`):
  1. Exact model match wins — the specific case like `sportster-2001` should hit the exact Sportster row even if you also have a "Sportster Custom".
  2. Exact make match handles `harley-davidson-2001` style inputs.
  3. Partial model match catches short stems like `cbr929` matching "CBR929RR".
  4. Partial make match catches brand-only inputs like `harley` matching "Harley-Davidson".
- **`--vehicle-id` stays primary**; `--bike` is additive. Power users and scripts keep using IDs; walk-up users use slugs.
- **Top-level `motodiag quick` reduces keystrokes** from `motodiag diagnose quick --symptoms "..."` to `motodiag quick "..."`. For the highest-frequency CLI path this matters.
- **Delegation via `ctx.invoke()` preserves a single source of truth**: the top-level `quick` is a thin wrapper. All the session creation + AI call + persistence + tier gating lives in Phase 123's `diagnose quick` unchanged.
- **`register_quick` requires `register_diagnose` first** — runtime check via RuntimeError. Means `cli/main.py` must register them in order. Acceptable since they're ordered in the source anyway.

## Verification Checklist
- [x] `_resolve_bike_slug("sportster-2001")` returns the Sportster row when seeded
- [x] `_resolve_bike_slug("cbr929-2000")` returns the CBR row via partial model match
- [x] `_resolve_bike_slug("notabike-9999")` returns None
- [x] Slug without year (`sportster`) still matches by model
- [x] Slug case-insensitive (`SPORTSTER-2001` works)
- [x] Ambiguous slug returns first match (deterministic by created_at)
- [x] `diagnose quick --bike sportster-2001 --symptoms "x"` happy path — session created
- [x] `diagnose quick --bike unknownbike --symptoms "x"` exits 1 with error listing garage
- [x] `diagnose quick --bike unknownbike --symptoms "x"` on empty garage shows "Garage is empty" variant
- [x] `diagnose quick --bike X --vehicle-id 5 --symptoms "x"` uses vehicle-id, prints warning
- [x] `diagnose quick --symptoms "x"` (neither provided) exits 1 with error
- [x] `motodiag quick "won't start" --bike sportster-2001` top-level shortcut works
- [x] `motodiag quick "x" --vehicle-id N` top-level shortcut works with vehicle-id
- [x] `motodiag quick` with no symptoms argument exits 1
- [x] `motodiag quick "x" --description "additional info"` passes description through
- [x] `motodiag quick "x" --bike unknown` error propagates from delegated command
- [x] `motodiag quick "x" --bike sportster-2001 --model sonnet` with HARD paywall + individual tier → tier error
- [x] Existing `diagnose quick --vehicle-id N --symptoms "..."` regression — still works unchanged and persists session
- [x] Top-level `quick` command registered in cli.commands alongside `diagnose`
- [x] `diagnose quick` still present as subcommand
- [x] All 2123 existing tests still pass (zero regressions)
- [x] Zero live API tokens burned

## Risks (all resolved)
- **Ambiguous slugs pick first match deterministically**: accepted. The 4-tier priority plus `ORDER BY created_at, id` gives predictable behavior. A warning wasn't added (plan mentioned it); the deterministic behavior was sufficient for v1.
- **`motodiag quick` vs `motodiag diagnose quick` both exist**: intentional. Discovery via `--help` lists both; the top-level shortcut is documented as the preferred surface.
- **Slug parsing is simple**: accepted for v1. Phase 128 (Knowledge base browser) and Phase 130 (shell completions) will add structured lookup and tab-completion respectively.
- **Click callback reuse via `ctx.invoke`**: worked cleanly. No need for the `_run_quick`-direct-call fallback mentioned in the plan.

## Deviations from Plan
- **4-tier slug match instead of plan's 3-tier**. Plan said "exact model → exact make → first by created_at". Builder-A added Tier 3/4 (partial model LIKE → partial make LIKE) to make useful examples like `cbr929` → CBR929RR and `harley` → Harley-Davidson actually work. The deterministic `ORDER BY created_at, id` tie-break at each tier preserves the plan's intent.
- **Out-of-range years treated as part of the stem**, not split + discarded. Plan said "no year constraint" when year is absent; Builder-A extended this to "treat out-of-range years as stem characters" so `foo-9999` is stem=`foo-9999` rather than stem=`foo` + (silently ignored year). More honest handling of unexpected input.
- **Ambiguous-match warning NOT added**. Plan mentioned "Matched first Harley; use --vehicle-id for precision". Builder-A skipped it on the grounds that Tier 1-2 exact matches rarely ambiguate; Tier 3-4 partials are where ambiguity shows up, and the deterministic `ORDER BY created_at` already makes the behavior predictable. Easy to add later if user feedback wants it.
- **Test count 34 vs planned 15-20**. Builder-A added thorough `TestParseSlug` coverage (9 tests for all boundary cases) and `TestResolveBikeSlug` (11 tests covering every match tier + edge case). Extra coverage came for free given the 4-tier matching.
- **`_list_garage_summary` helper not in plan** — added to build the "unknown slug" error message body (shows what's actually in the garage so user can see what they could have typed). Natural UX improvement.

## Results
| Metric | Value |
|--------|------:|
| New files | 1 (`tests/test_phase125_quick.py`) |
| Modified files | 2 (`src/motodiag/cli/diagnose.py`, `src/motodiag/cli/main.py`) |
| New tests | 34 |
| Total tests | 2157 passing (was 2123) |
| New CLI commands | 1 (top-level `quick`) + 1 new option (`--bike` on `diagnose quick`) |
| Production LoC | ~180 added to `cli/diagnose.py` |
| New tables | 0 |
| New migrations | 0 |
| Schema version | 13 (unchanged) |
| Regression status | Zero regressions — full suite in ~12 min |
| Live API tokens burned | **0** (all calls mocked via `patch`) |

Phase 125 is pure UX sugar — no substrate, no migration, no new package. The 4-tier slug matcher makes `motodiag quick "won't start" --bike sportster-2001` work for the walk-up usage while `--vehicle-id` remains primary for scripts and power users. First agent-delegated phase: Builder-A produced clean code that passed all 34 tests on the Architect's trust-but-verify run — despite the sandboxed agent runtime blocking Python execution (so Builder-A shipped without self-testing, and Architect caught that as a process issue — documented for CLAUDE.md correction).
