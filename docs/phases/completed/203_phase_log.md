# Phase 203 — Dark Mode + Shop-Friendly UI — Phase Log

**Status:** ✅ Complete
**Started:** 2026-09-04 | **Completed:** 2026-09-04
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

---

### 2026-09-04 16:28 — Build complete in five staged commits

Sequenced as the plan required, each commit independently green:

1. **Foundation** — `tokens.ts` (25 roles × 2 schemes), `ThemeProvider`
   + `useTheme`, `createThemedStyles`, app chrome (NavigationContainer
   theme, scheme-derived StatusBar, tab tints), `SettingsScreen`, and 6
   leaf components. `SectionToggle`'s stray `#1976d2` reconciled.
2. **The three card components** — the audit's worst offenders. Their
   module-scope `_renderX` helpers can no longer close over a themed
   sheet, so each takes `styles` as a parameter; tsc verified 161 sites.
3. **All 24 screens** — 596 literals → 0 outside `src/theme/`.
4. **Readability + the pinning tests** — type floor, touch targets,
   `Button` self-labelling, and 51 new tests.
5. **The Settings entry point** on Home (the screen was registered but
   unreachable).

### 2026-09-04 16:28 — SMOKE PASSED: dark mode verified visually, both schemes

- **Simulator (iPhone 17 Pro), by screenshot:** app launched light with
  the new Settings section; opened Settings, which correctly reported
  "currently showing the light theme"; tapped **Dark** and the entire
  app flipped — nav bar, tab bar, status bar, card surfaces, and the
  accent shifting to the lighter blue chosen to read on dark. Navigated
  back and confirmed Home was fully dark too, so the change propagates
  beyond the screen that triggered it.
- **Physical iPhone 16 Pro:** the themed build installed and is running.
  The phone was on cellular while the Mac was on a hotspot address, so
  Metro was unreachable over the baked localhost URL; rebuilding with
  `FORCE_BUNDLING=1` embedded the JS and removed the dependency on
  Metro entirely. Worth remembering as a dev-loop technique — it makes a
  Debug build self-contained when the network is uncooperative.
- **This is the first phase in four whose device leg actually ran.**
  199's banner and 201/202's UI legs were all blocked by the tailnet
  proxy or a network change. Two things fixed it: the user turning off a
  second VPN that had been capturing the default route, and using the
  simulator as a first-class verification surface for a pure-UI change
  rather than treating hardware as the only option.

### 2026-09-04 16:28 — Documentation update + close

- `203_implementation.md` → v1.1 (checklist, deviations incl. the
  codemod quote bug and the inline-prop colours, results, key finding).
  Docs → `completed/`.
- Mobile project docs, ROADMAP 203 ✅, follow-ups filed.
