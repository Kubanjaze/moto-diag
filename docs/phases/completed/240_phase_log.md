# Phase 240 — Phase Log

**Gate 12: European brand coverage integration test**
Branch: `phase-240-gate12` | Date: 2026-09-08

## Step 0
- Row 240 said "Gate 11"; Phase 205 already closed under that number. This is
  Gate 12.
- No existing gate sweeps the European makes.
- Coverage matrix: six makes with DTC file + compat rows + make-file; Moto
  Guzzi with none of the three, covered only by 236–239.

## Build
Staged in the scratchpad and dry-run against the pre-merge tree as a temporary
copy under tests/ (removed after each run), regression class deselected:
- 404s: routers mount under /v1.
- 401s: /v1 routes are API-key gated — key minted for a seeded user.
- `recommend` empty for every make: the fixture never seeded the compat
  catalogue.
- `compat check` requires --adapter; the gate's question is `recommend`.
- 403 on parts: shop-scoped — shop created via CLI, owner seeded.
- Parts search returns a bare list, not {items}.
Final dry run: 37 passed, regression class deselected.

## Close-out
- 46 gate tests; regression 5945 passed / 0 failed; F9 clean.
- Cleared for roadmap ✅ (row corrected to Gate 12), implementation.md
  0.13.51 → 0.13.52, merge. **Track K closes.**
