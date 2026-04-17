# MotoDiag Phase 125 — Quick Diagnosis Mode (Bike Slug + Top-Level Shortcut)

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-04-17

## Goal
UX sugar on top of Phase 123's `diagnose quick`. Adds a **bike slug resolver** so mechanics don't need to remember numeric vehicle IDs, plus a **top-level shortcut** `motodiag quick "<symptoms>"` that skips the `diagnose` subgroup. Example target UX:

```
motodiag quick "won't start when cold" --bike sportster-2001
```

Phase 123 already handles all the heavy lifting (session creation, AI call, persistence, tier gating). Phase 125 is pure ergonomics: one new helper function + one new option on the existing `diagnose quick` command + one top-level `quick` command that proxies to it.

CLI:
- `motodiag quick "<symptoms>" [--bike SLUG | --vehicle-id N] [--description TXT] [--model haiku|sonnet]` — top-level shortcut
- `motodiag diagnose quick --bike SLUG --symptoms "..."` — extended existing command, `--bike` alternative to `--vehicle-id`

Outputs: extend `src/motodiag/cli/diagnose.py` (~80 LoC added), 15-20 new tests. **No migration, no new file.**

## Logic

### 1. New helper `_resolve_bike_slug(slug, db_path) -> Optional[dict]`

Lives in `cli/diagnose.py`. Takes a slug like `"sportster-2001"` or `"cbr929-2000"` and returns a matching vehicle dict (or None).

**Slug parse rules:**
- Split on `-` (last hyphen) → `(stem, year_str)`. If the last token parses as a 4-digit int in 1980–2035, treat it as the year; otherwise there's no year constraint.
- `stem` is lowercased and matched against `vehicles.make` or `vehicles.model` via SQL `LIKE '%stem%'` (case-insensitive via `LOWER()`).
- If multiple matches, prefer exact-model match → exact-make match → first row by `created_at`.
- If no matches, return None. Caller prints a clear error listing partial matches if any.

**Examples:**
- `sportster-2001` → matches Harley-Davidson Sportster 1200 / 2001
- `cbr929-2000` → matches Honda CBR929RR / 2000
- `harley` → matches first Harley (ambiguous but usable); prints "Matched first Harley; use --vehicle-id for precision" warning
- `zyx-9999` → None

### 2. Extend `diagnose quick` command

- Add `--bike TEXT` option alongside existing `--vehicle-id INT`.
- If both provided: `--vehicle-id` wins, yellow warning printed.
- If neither provided: clear error, exit 1.
- If `--bike` provided: call `_resolve_bike_slug`. None → error listing garage. Dict → use its `id` as vehicle_id.
- Existing flow after resolution is unchanged.

### 3. Top-level `motodiag quick` command (new)

- One-level-up alias for `diagnose quick`. Symptoms are now a positional argument (no flag needed), so most common usage is `motodiag quick "starts but dies"`.
- Implementation: thin wrapper that builds kwargs and invokes the `diagnose_quick` callback directly (Click lets us do this). Avoids duplicating the command body.
- All other flags (`--bike`, `--vehicle-id`, `--description`, `--model`) passed through.
- Registered in `cli/main.py` after `register_diagnose(cli)` via a one-liner `register_quick(cli)` that lives in `cli/diagnose.py`.

### 4. Testing (15-20 tests)

- **`_resolve_bike_slug`**: exact model match, exact make match, ambiguous (returns first), no match returns None, year filter works, slug without year, case-insensitive.
- **`diagnose quick --bike SLUG --symptoms "..."`**: happy path, unknown slug errors, both --bike and --vehicle-id prefers ID with warning, neither provided errors.
- **`motodiag quick "symptoms" --bike SLUG`**: happy path, positional symptom arg, all flags pass through.
- **Regression**: existing `diagnose quick --vehicle-id N --symptoms "..."` still works identically.

All AI calls mocked via `patch("motodiag.cli.diagnose._default_diagnose_fn", fn)` — same pattern as Phase 123. Zero live tokens.

## Key Concepts
- **Pure sugar phase**: no new substrate, no new tables, no new persistence logic. The win is UX friction removal.
- **Slug format `model-year`** is deliberately loose. A mechanic types what feels natural; we match fuzzily and fail loudly if we can't disambiguate. Phase 130 (shell completions) will tab-complete from the garage.
- **`--vehicle-id` stays primary**; `--bike` is additive. Power users and scripts keep using IDs; walk-up users use slugs.
- **Top-level `motodiag quick` reduces keystrokes** from `motodiag diagnose quick --symptoms "..."` to `motodiag quick "..."`. For the highest-frequency CLI path it matters.
- **Reuse, don't duplicate**: the top-level `quick` command delegates to `diagnose_quick` via Click's `ctx.invoke()` or direct callback invocation. No copy-paste of the diagnosis flow.

## Verification Checklist
- [ ] `_resolve_bike_slug("sportster-2001")` returns the Sportster row when seeded
- [ ] `_resolve_bike_slug("cbr929-2000")` returns the CBR row
- [ ] `_resolve_bike_slug("notabike-9999")` returns None
- [ ] Slug without year (`sportster`) still matches by model
- [ ] Slug case-insensitive (`SPORTSTER-2001` works)
- [ ] Ambiguous slug returns first match (deterministic by created_at)
- [ ] `diagnose quick --bike sportster-2001 --symptoms "x"` happy path, session created
- [ ] `diagnose quick --bike unknownbike --symptoms "x"` exits 1 with error listing garage
- [ ] `diagnose quick --bike sportster-2001 --vehicle-id 5` uses vehicle-id, prints warning
- [ ] `diagnose quick --symptoms "x"` (neither provided) exits 1 with error
- [ ] `motodiag quick "won't start"` top-level shortcut works with bike or vehicle-id
- [ ] `motodiag quick "x" --bike sportster-2001` positional + flag combo
- [ ] `motodiag quick` with no symptoms argument exits 1
- [ ] Existing `diagnose quick --vehicle-id N --symptoms "..."` regression — still works unchanged
- [ ] All 2123 existing tests still pass (zero regressions)
- [ ] Zero live API tokens burned

## Risks
- **Ambiguous slugs pick first match silently**: mitigated by warning when >1 match. Phase 130 tab completion + Phase 128 knowledge browser give better disambiguation surfaces later.
- **`motodiag quick` vs `motodiag diagnose quick` both exist**: intentional. Discovery via `--help` lists both; docs direct users to the shortcut.
- **Slug parsing is dumb**: accepted for v1. Phase 128 (Knowledge base browser) or Phase 130 (shell completions) will add structured lookup.
- **Click callback reuse**: `ctx.invoke(diagnose_quick, ...)` should work. If not, fall back to a tiny dispatch function that calls `_run_quick` directly — same outcome.
