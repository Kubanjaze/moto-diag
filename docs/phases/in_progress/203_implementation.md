# Phase 203 — Dark Mode + Shop-Friendly UI

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-04

## Existing-code audit (Step 0 — run 2026-09-04, before this plan)

- **Theming — GREENFIELD.** No theme, palette or token module exists.
  Zero hits for `useColorScheme`, `Appearance`, `DarkTheme`,
  `DefaultTheme` across `src/` and `App.tsx`. `NavigationContainer`
  (`App.tsx:93`) takes no `theme` prop; `RootNavigator.tsx:51-65`
  hardcodes its tab tints. Stacks use `headerShown: false`, so there is
  no header chrome to re-theme — a real scope saving.
- **Scale — RESHAPE by extraction, not redesign.** 33 files call
  `StyleSheet.create`; **596 hex-literal occurrences, 95 distinct
  values**, plus 7 `rgba` scrims. But the style KEYS are already
  role-named locally (`label`, `requiredMark`, `inputError`,
  `severityHigh`), so ~95 literals collapse to **20-25 semantic roles**.
  Worst files: `WorkOrderSectionCard.tsx` (61 literals),
  `SessionDetailScreen.tsx` (57), `ReportSectionCard.tsx` (52).
- **The app is ALREADY dark-capable natively, and that is a latent
  bug.** `ios/MotoDiag/Info.plist` has **no `UIUserInterfaceStyle`**
  key, and `android/.../styles.xml:4` already declares
  `Theme.AppCompat.DayNight.NoActionBar` with **no `values-night/`**.
  So a phone set to dark hands this app a dark shell today, and it
  renders light-hardcoded content inside it. Phase 203 fixes an
  existing inconsistency rather than introducing a new capability.
- **`Button.tsx` already has the abstraction to copy.** `ButtonVariant
  = 'primary'|'secondary'|'danger'` resolved through
  `variantBackgroundStyle`/`variantLabelStyle` into six style entries.
  Every other component is role-named but locally-defined — the ideal
  precondition for extraction.
- **An accent inconsistency to reconcile:** `SectionToggle` uses
  `#1976d2` while the app accent everywhere else is `#007aff`.
- **Semantic colour families carry DIAGNOSTIC meaning** — severity
  (critical/high/medium/low), extraction state, symptom source. A naive
  dark inversion would silently destroy the distinctions a mechanic
  reads. These need explicit dark pairs and pinning tests.
- **Accessibility — EXTENSION, from a very low base.**
  `accessibilityRole` × 22, but `accessibilityLabel` × **1**, and
  `hitSlop` / `allowFontScaling` / `maxFontSizeMultiplier` × **0**. The
  48dp floor is mostly honoured (`minHeight: 48` × 11, and `Button.tsx`
  encodes `full: 48` / `compact: 44`) with five violations. Body text
  skews small for arm's length in sun: 14pt × 84, 13pt × 68, 12pt × 41.
- **State — ADR-003 is tripped, and blesses the answer.** A theme read
  by 33 style modules trips both the ≥3-screens and prop-drilling
  triggers, but the ADR explicitly says "Context + hooks handle a
  surprising amount" — so `ApiKeyProvider` is the shape to copy, not a
  new state library. Storage key convention is
  `motodiag:<domain>:<item>`, so `motodiag:ui:theme`.
- **There is NO Settings screen.** Zero settings/preferences/profile
  routes in any of the four stacks. `App.tsx:33-36` has referenced an
  "explicit settings shop-switch" since Phase 193 and it was never
  built.
- **Backend — NOT INVOLVED. Confirmed.** No theme/preference column or
  route anywhere. (`cli/theme.py` is a Rich TERMINAL theme for the CLI —
  unrelated, but its `SEVERITY_COLORS` / `STATUS_COLORS` maps are a
  useful naming precedent, and backend Phase 313 "Dark mode (desktop)"
  expects mobile to define the shared vocabulary.)
- **No prior spec.** "(was 191)" is pure renumbering — rows 45-55 carry
  a uniform +12 shift. No follow-up ticket anywhere defers anything to
  "the dark-mode phase". The one adjacent note is `RootNavigator.tsx:57`
  quoting Phase 189: *"no icon library yet — defer until a design pass
  earns it."* **203 is that design pass, and adding an icon library is
  an in-scope temptation this plan explicitly declines.**
- **The test suite will not fight this.** Across 75 test files there are
  two incidental hex strings and **zero** `toHaveStyle` /
  `backgroundColor` assertions.

**User decisions (2026-09-04):** convert **all 33 files**, in staged
commits · **light / dark / system** tri-state in a **new Settings
screen** · the **readability pass is in scope**, bounded.

## Goal

A mechanic working outside in direct sun can read the screen, and one
working under the lift at night is not blinded by it. The app follows
the phone by default and can be forced either way from a Settings screen
that has been implied since Phase 193. Diagnostic colour still means
what it meant — severity and status survive the dark palette instead of
being inverted into mush.

CLI: none. Backend: none (confirmed by the audit).

Run: `npm test`, `npx tsc --noEmit`, `npx eslint src/ __tests__/`;
device smoke in both appearances.

Outputs (mobile only, branch `phase-203-dark-mode`):
- `src/theme/tokens.ts` — 20-25 semantic roles × light/dark. Named
  semantically (`surface`, `textPrimary`, `border`, `accent`,
  `severity.critical.bg`), NOT by mobile-specific role, because backend
  Phase 313 will reuse the vocabulary.
- `src/theme/ThemeProvider.tsx` + `useTheme()` — Context in the
  `ApiKeyProvider` shape; `useColorScheme()` bridge; tri-state
  preference persisted at `motodiag:ui:theme`.
- `src/theme/createThemedStyles.ts` — the conversion primitive. Turns a
  module-scope `StyleSheet.create({...})` into
  `createThemedStyles((t) => ({...}))`, returning a hook that memoises
  per theme. This is what makes a static, module-scope stylesheet
  reactive with one line changed per file plus the literal swaps.
- `App.tsx`: `ThemeProvider` wrapping; `NavigationContainer theme=`;
  `StatusBar barStyle` derived from the resolved scheme.
- `RootNavigator`: tab tints from tokens; `SectionToggle`'s `#1976d2`
  reconciled to the single accent.
- `SettingsScreen` + route (in `ShopStack`? no — see Logic) with the
  light/dark/system control.
- Conversion of all 33 `StyleSheet.create` files.
- Readability pass, bounded: body-text floor raised, the five sub-48dp
  targets fixed (`SessionDetailScreen.tsx:1343-1388`,
  `WorkOrderSectionCard.tsx:1010`, `SessionsListScreen.tsx:298`,
  `VehiclesScreen.tsx:222`, `ExtractedSymptomEditModal.tsx:305`),
  `accessibilityLabel` added to unlabelled interactive controls.
- Tests: token completeness (every light role has a dark pair), the
  provider's tri-state + persistence + system-follow, the themed-styles
  primitive, **semantic-family pinning tests** so severity and status
  keep distinct colours in BOTH schemes, and the readability floors.

## Logic

- `ThemeProvider` resolves `preference` (`light|dark|system`) against
  `useColorScheme()` into a concrete `scheme`, then hands down the
  matching token map. Preference is hydrated from AsyncStorage on mount
  (the `ApiKeyProvider` hydration pattern) and written on change.
- `createThemedStyles(fn)` returns `useStyles()`. Inside, `useTheme()`
  supplies the tokens and `useMemo` keyed on the token object rebuilds
  the sheet only when the scheme actually changes — so a re-render costs
  nothing and a theme flip costs one rebuild per mounted component.
- Conversion per file is mechanical: swap the wrapper, replace literals
  with token references, call `useStyles()` in the component body.
- **Settings lives in `HomeStack`**, reached from HomeScreen. The Home
  tab already owns app-level concerns (the API-key card), Settings is
  app-level not shop-level, and putting it in `ShopStack` would hide it
  behind the shop picker for a mechanic with no shop membership.

## Key Concepts

- **Extraction, not redesign.** The literals already encode a coherent
  palette; this phase gives it names and a second scheme. Where the
  audit found genuine inconsistency (two accents), reconcile — but this
  is not a visual redesign, and no icon library is added.
- **Semantic colour is data, not decoration.** Severity and status
  colours carry diagnostic meaning. Each gets an explicit dark pair
  chosen for contrast against the dark surface, never an algorithmic
  inversion, and tests pin that the four severity levels remain mutually
  distinct in both schemes.
- **Sunlight is a light-mode problem.** Dark mode is *worse* in direct
  sun. The tri-state exists so a mechanic outdoors can force light while
  their phone sits on dark — which is why "follow the system only" was
  rejected.
- **Reactivity via a hook, not a re-render trick.** `StyleSheet.create`
  at module scope is evaluated once at import. The primitive is what
  makes the whole sweep one mechanical change per file rather than 33
  bespoke refactors.

## Verification Checklist

- [ ] Every semantic role in the light map has a dark counterpart
      (asserted, not eyeballed)
- [ ] The four severity levels are mutually distinct in BOTH schemes,
      and so are the extraction-state and symptom-source families
- [ ] Provider: system-follow tracks `useColorScheme`; explicit
      light/dark overrides it; the choice survives a remount; a storage
      failure degrades to system rather than crashing
- [ ] `createThemedStyles` rebuilds on scheme change and not otherwise
- [ ] Zero remaining hex literals in `src/` outside `theme/tokens.ts`
      (asserted by a test that greps the tree)
- [ ] Body-text floor raised; the five sub-48dp targets meet 48;
      `accessibilityLabel` on every unlabelled interactive control
- [ ] `npm test` green; tsc clean; eslint 0 errors repo-wide
- [ ] Device smoke: flip the system appearance with the app open and
      watch it follow; force the opposite in Settings; confirm severity
      chips stay legible in both

## Risks

- **This touches every styled file at once.** Mitigated by sequencing —
  tokens, then the primitive, then leaf components, then screens in
  batches, each its own commit — and by the fact that no test asserts a
  colour, so the suite will not produce false failures. The flip side is
  that the suite also will not CATCH a colour regression, which is why
  the semantic families get explicit pinning tests.
- **A naive dark palette destroys meaning.** Four severity levels that
  are distinguishable in light can collapse into near-identical dark
  values. Explicit pairs plus distinctness assertions.
- **Scope creep toward a redesign.** The audit surfaced a standing "no
  icon library yet — defer until a design pass earns it" note. This
  phase declines it, and says so, so a future reader knows it was a
  decision rather than an oversight.
- **The device smoke has failed for environment reasons in each of the
  last two phases** (tailnet proxy wedged, then the Mac changed
  networks). A theme change is exactly the kind of work that needs eyes
  on hardware, so if the device leg fails again that is a genuine gap,
  not a formality — record it as such.
- **ADR-003 drift:** the ADR says "use MMKV directly" for persistence
  while the codebase settled on AsyncStorage. This phase follows the
  code, and notes the drift rather than silently contradicting the ADR.
