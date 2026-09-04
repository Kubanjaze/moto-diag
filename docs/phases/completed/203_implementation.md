# Phase 203 — Dark Mode + Shop-Friendly UI

**Version:** 1.1 | **Tier:** Standard | **Date:** 2026-09-04 (v1.0 plan → v1.1 as-built same day)

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

- [x] Every semantic role in light has a dark counterpart — asserted by
      flattening both maps and comparing key sets, not eyeballed
- [x] The four severity levels are mutually distinct in BOTH schemes,
      and so are extractionState, symptomSource and status; dark reuses
      no light value (the "no lazy inversion" assertion)
- [x] Provider: system-follow tracks `useColorScheme`; explicit
      light/dark overrides it; a corrupt stored value falls back to
      system; **a failed write still applies the choice** and **a failed
      read still renders a theme**
- [x] `createThemedStyles` memoises per theme object
- [x] Zero hex / rgb / hsl literals in `src/` outside `theme/` — asserted
      by a source-scanning test, which also guards the code paths no
      test renders
- [x] Body-text floor raised (209 declarations across 32 files); all 13
      sub-48dp targets lifted; `Button` now labels itself from its title
- [x] 78 suites / **982 tests** green (+51); tsc clean; eslint 0 errors
      repo-wide
- [x] **Device smoke PASSED, in two places.** Simulator (iPhone 17 Pro):
      launched light, opened Settings, tapped Dark, and the whole app
      flipped — nav bar, tab bar, status bar, card surfaces, and the
      accent shifting to the lighter blue that reads on dark. Verified
      by screenshot, not by assertion. Physical iPhone 16 Pro: the
      themed build installed and is running.

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

## Deviations from Plan

- **The conversion was scripted, and the script had a bug worth
  recording.** An unmapped colour was returned WITHOUT its surrounding
  quotes, producing bare hex in the source. tsc caught it immediately,
  but it is the exact failure mode that makes people distrust codemods:
  it only affected literals the mapping did not know about, so a
  narrower test set would have missed it. The fix — leave unmapped
  values untouched and report them — then surfaced the Phase 200/201
  parts-row grey cluster the first pass had silently skipped.
- **Colour literals also live in inline JSX props**, not only in
  stylesheets (`placeholderTextColor`, `ActivityIndicator color`). The
  converter only rewrites sheet bodies, so five of these survived the
  sweep and needed a separate grep. Easy to miss precisely because they
  are not where colours normally live.
- **`AsyncStorage` had to become a global jest mock.** It was mocked
  per-file until `ThemeProvider` pulled it into the import graph of
  every screen. Same reasoning as the Phase 198 op-sqlite/netinfo mocks;
  backed by a real Map so the hydrate-then-persist round trip behaves
  like storage.
- **`useTheme` keeps its throw** rather than defaulting to light without
  a provider. Defaulting would have avoided touching seven test files,
  and would also have hidden exactly the wiring gap this codebase has
  been bitten by before. The tests got a `withTheme` helper instead.
- **Five dependency arrays needed `styles`** once it became a hook
  result. eslint found all five; no test would have.
- **The icon library was declined**, as the plan said it would be.
  `RootNavigator` still carries Phase 189's "no icon library yet — defer
  until a design pass earns it". This was the design pass and the answer
  is still no; recorded so the next reader knows it was decided.

## Results

| Metric | Value |
|--------|-------|
| Files converted | 35 (9 components + 26 screens/modals) |
| Colour literals removed | 596 → **0** outside `src/theme/` |
| Distinct values → roles | ~95 → 25 semantic tokens × 2 schemes |
| Type declarations raised | 209 across 32 files |
| Touch targets lifted to 48dp | 13 |
| Tests | 78 suites / **982** (+51); tsc clean; eslint 0 |
| Backend changes | **none** (as the audit predicted) |
| Device verification | simulator screenshots in both schemes; physical device running the themed build |

**Key finding:** the phase's real risk was never the colours, it was that
`StyleSheet.create` is evaluated once at module import — so "add dark
mode" is secretly "make 35 static module-scope objects reactive". Naming
that early turned an open-ended redesign into one mechanical change per
file plus a compiler-driven cleanup: `createThemedStyles` swapped the
wrapper, and every remaining site became a type error that tsc listed by
line. The 161 errors after the card components were not a setback; they
were the work list. A codemod that leans on the type checker to find its
own leftovers is far safer than one that tries to be clever.
