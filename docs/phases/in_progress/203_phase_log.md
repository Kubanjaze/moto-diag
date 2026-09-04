# Phase 203 — Dark Mode + Shop-Friendly UI — Phase Log

**Status:** 📋 Planned
**Started:** 2026-09-04 | **Completed:** —
**Repos:** `Kubanjaze/moto-diag-mobile` (code) + `Kubanjaze/moto-diag`
(this ledger), branch `phase-203-dark-mode`

---

### 2026-09-04 15:52 — Plan written (Step 0 audit + v1.0)

- **Step 0 (delegated read-only sweep) found theming greenfield but the
  groundwork already laid.** No theme module, no `useColorScheme`, no
  `NavigationContainer theme=` — yet 596 hex literals across 33 files
  reduce to only ~95 distinct values and ~20-25 semantic roles, because
  the style keys are already role-named locally. This is extraction, not
  redesign.
- **The headline finding: the app is ALREADY dark-capable natively.**
  iOS has no `UIUserInterfaceStyle` pin and Android already declares
  `Theme.AppCompat.DayNight` with no `values-night/`. A phone on dark
  hands this app a dark shell today and gets light-hardcoded content
  inside it. 203 fixes a latent inconsistency rather than adding a
  capability.
- **Semantic colour is diagnostic data**, not decoration — severity,
  extraction state and symptom source all encode meaning a naive dark
  inversion would destroy. Explicit dark pairs plus distinctness tests.
- **The suite will not fight this** (zero colour assertions across 75
  test files) — which also means it will not catch a regression, hence
  the pinning tests.
- **ADR-003 is tripped but blesses Context**; `ApiKeyProvider` is the
  shape. Storage key `motodiag:ui:theme` per the existing convention.
- **No Settings screen exists** anywhere, though `App.tsx` has referred
  to one since Phase 193.
- **Backend confirmed uninvolved.**
- **User decisions:** all 33 files in staged commits · light/dark/system
  in a new Settings screen · bounded readability pass in scope.
- **Explicitly declined:** the icon library that `RootNavigator` defers
  "until a design pass earns it". This is that design pass and it still
  says no — recorded so it reads as a decision.
- **Next milestone:** plan commit → tokens + provider + primitive →
  app chrome + Settings → components → screens in batches → readability
  pass → device smoke in both appearances.
