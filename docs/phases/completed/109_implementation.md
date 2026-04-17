# MotoDiag Phase 109 — CLI Foundation + Subscription Tier System

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
Restructure the CLI foundation and introduce the 3-tier subscription system ($19 solo / $99 shop / $299 multi-location). Add the `SubscriptionTier` enum, per-tier feature flags, the `requires_tier` decorator with soft/hard enforcement modes, a command registry for modular CLI organization, and a new `motodiag tier` command that shows current tier and compares all three.

CLI: `python -m pytest tests/test_phase109_cli_foundation.py -v`

Outputs: `src/motodiag/cli/subscription.py`, `src/motodiag/cli/registry.py`, updated `cli/main.py` with new `tier` command, 41 tests

## Key Concepts
- Three concrete tiers with real pricing: INDIVIDUAL $19/mo, SHOP $99/mo, COMPANY $299/mo (yearly 10x = 2 months free)
- TierFeatures model: max_vehicles, max_sessions_per_month, max_users, max_locations, feature flags, AI model access, cost caps
- Dual enforcement modes: SOFT (dev default — warn but allow) vs HARD (Track H+ — raise TierAccessDenied)
- `MOTODIAG_PAYWALL_MODE` env var toggles between soft/hard — defaults to soft during Tracks D-G development
- `MOTODIAG_SUBSCRIPTION_TIER` env var overrides current tier for testing
- `requires_tier` decorator: gates commands by minimum tier, behavior determined by enforcement mode
- CommandRegistry: global singleton for modular command registration by group (main/diagnostic/data/admin)
- `motodiag tier` command: shows current tier panel + limits table + features table + upgrade hint
- `motodiag tier --compare`: side-by-side comparison table of all three tiers
- `format_tier_comparison()`: ASCII table with pricing, limits, and feature flags for all tiers

## Verification Checklist
- [x] SubscriptionTier enum with 3 tiers and rank comparison (6 tests)
- [x] TierFeatures models for individual ($19), shop ($99), company ($299) with correct pricing and limits (7 tests)
- [x] current_tier() reads env var with case insensitivity and falls back to INDIVIDUAL (5 tests)
- [x] has_feature() correctly gates features per tier (5 tests)
- [x] requires_tier decorator works in both soft and hard modes (6 tests)
- [x] format_tier_comparison produces all 3 tiers with pricing (3 tests)
- [x] CommandRegistry registers, retrieves, groups, clears (7 tests)
- [x] Global registry singleton + @register_command decorator (2 tests)
- [x] CLI still works: --version, info, tier, tier --compare, config, code, search, db init (manual)
- [x] All 41 tests pass (0.10s), full regression 1616/1616 (3m 57s)

## Results
| Metric | Value |
|--------|-------|
| Files created | 2 (subscription.py, registry.py) + main.py updated |
| Tests | 41/41, 0.10s |
| Full regression | 1616/1616, 3m 57s |
| Subscription tiers | 3 (Individual $19, Shop $99, Company $299) |
| Enforcement modes | 2 (soft for dev, hard for Track H+) |
| New CLI commands | 1 (`motodiag tier` + `--compare`) |

Key finding: The 3-tier system is fully architected with the user's confirmed pricing. Soft enforcement during Tracks D-G lets all features be built and tested without payment friction. When Track H (phases 148-162) adds real auth/billing, flipping `MOTODIAG_PAYWALL_MODE=hard` activates paywall enforcement without code changes. All downstream CLI commands (110-120) will use `requires_tier` to gate appropriately.
