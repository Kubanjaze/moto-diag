# MotoDiag Phase 153 — Parts Cross-Reference

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-18

## Goal

Sixth Track F phase. OEM ↔ aftermarket parts cross-reference. Mechanic sees `HD-26499-08` (TC cam tensioner) → returns Feuling 4124 + S&S 33-4220 alternatives with prices + purchase URLs, ranked by shop preference. Side-effect: populates Phase 148 `FailurePrediction.parts_cost_cents` (currently always None).

CLI: `motodiag advanced parts {search, xref, show, seed}`.

No AI, no network. Migration 021 (next available).

Outputs:
- Migration 021: `parts` (slug UNIQUE, oem_part_number, brand, description, category, make, model_pattern, year_min/max, typical_cost_cents CHECK≥0, purchase_url, notes, verified_by) + `parts_xref` (oem_part_id FK CASCADE, aftermarket_part_id FK CASCADE, equivalence_rating 1-5 CHECK, UNIQUE pair, CHECK oem≠aftermarket) + 4 indexes.
- `advanced/parts_repo.py` (~250 LoC): add_part, get_part, get_part_by_oem, search_parts (fuzzy LIKE across oem+description+brand), list_parts_for_bike, add_xref (INSERT OR IGNORE on UNIQUE pair), get_xrefs (JOIN + sort: rating DESC → cost ASC → brand ASC → id ASC), lookup_typical_cost (Phase 148 hook).
- `advanced/parts_loader.py` (~100 LoC): idempotent JSON seeder (Phase 145 pattern).
- `advanced/data/parts.json` (~60 rows) + `parts_xref.json` (~80 rows) — real OEM+aftermarket across Harley TC88, Honda CBR, Yamaha R1, Kawasaki KLR, Suzuki GSX-R, BMW R1200GS, Ducati Monster, Triumph 675, KTM 690.
- `cli/advanced.py` +~250 LoC: `parts` subgroup. `search` Rich Table (OEM# | Brand | Description | Category | Make/Model | Cost | Verified); `xref` ranked (★1-5 | Brand | P/N | Cost | Notes | Source); `show` Panel + nested xref table; `seed` summary.
- `advanced/predictor.py` +~20 LoC: `_lookup_parts_cost(parts_needed_raw, make, db_path)` import-delayed + broad `except` → graceful None for Phase 148 regression.
- `tests/test_phase153_parts.py` (~30 tests, 4 classes).

## Key Concepts

- Template of real OEM+aftermarket curated from public catalogs (Revzilla, HD parts, K&N, Feuling, S&S, All Balls, EBC, Eagle Mike).
- Equivalence rating curated, not algorithmic: 5=drop-in, 4=minor notes, 3=functional-equiv-with-tweak, 2=partial, 1=related.
- Phase 148 hook opportunistic (None-on-miss preserves 44-test regression).
- Cascade delete: xref wiped when OEM deleted.
- Self-xref rejected via CHECK.

## Verification Checklist

- [ ] Migration 021 bumps SCHEMA_VERSION; rollback FK-safe (child first).
- [ ] parts.json ≥60 entries across 5 price tiers + bikes; parts_xref.json ≥80 real xrefs.
- [ ] Loader idempotent (second seed_all: zero new inserts).
- [ ] Self-xref via CHECK prevented.
- [ ] `get_xrefs` sort: rating DESC → cost ASC → brand ASC → id ASC.
- [ ] `lookup_typical_cost` None on miss, int on hit.
- [ ] CLI 4 subcommands work + `--json` round-trip.
- [ ] Phase 148 `predict_failures` populates `parts_cost_cents` when seeded.
- [ ] Phase 148 44 tests still green when parts table empty.

## Risks

- Migration slot race — Builder claims next integer at build time.
- Seed curation load-bearing — real OEM+aftermarket P/Ns from public catalogs only, no fantasy numbers. Architect spot-checks 5-10 rows.
- `cli/advanced.py` growth (~500 LoC after +250) — acceptable; extract option documented.
- Phase 148 import-delayed hook + broad `except` guards regression.
- SQLite LIKE case-insensitivity for ASCII; lowercase normalization on insert.
