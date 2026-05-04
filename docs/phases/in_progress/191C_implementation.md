# Phase 191C — F9 Failure-Family Architectural Intervention

**Version:** 1.0.1 | **Tier:** Standard (small) | **Date:** 2026-05-04 (v1.0 written 2026-05-04; v1.0.1 corrects pre-Commit-1 architect-review nits)

## Plan v1.0.1 — pre-Commit-1 corrections from architect review

Plan v1.0 was reviewed by Kerwyn before Builder dispatch. Five corrections land here on the plan-of-record before any Builder runs, otherwise the divergence multiplies. Doc + lint scope unchanged; framing + one rule's exempt clause + commit cadence detail get sharpened.

### Correction 1 — Total F9 instances: 7, not 6

Plan v1.0's catalog table was correctly 7 rows but the surrounding prose said "6 instances per phase-numbering — instance #4 was discovered alongside instance #5 in fix-cycle-1; counted as one for the '6 instances' headline." That hand-merge was wrong. Instances #4 and #5 share fix commit `832579d` but they're **different subspecies with different lessons**:

- **#4 — deploy-path-missing-wiring**: `motodiag serve` never called `init_db` → schema stale at runtime
- **#5 — self-validating-test-setup** (renamed; see Correction 2): timestamp-format mismatch where Python helper wrote ISO-T but production stored SQLite `datetime('now')` space-format → lex comparison broke on same-day-prefix boundaries

Plan v1.0.1 stops merging them. Headline count standardizes on **7 instances** going forward. Phase 191B's already-shipped closure docs keep "6" as sealed history; Phase 191C's pattern-doc intro will include a reconciliation sentence (per Correction 5).

### Correction 2 — Instance #5 renamed: subspecies (v) "self-validating-test-setup"

Plan v1.0 labeled instance #5 as "format-coincidence-latent" with DOC-ONLY lint coverage. The label is accurate but undersells the lesson and gives the doc nothing to teach beyond "watch for date boundaries."

**Renamed to subspecies (v) "self-validating-test-setup"**. The deeper pattern: **the test exercised the function against itself instead of against the system the function integrates with**. Specifically for Phase 191B C1:

- Helper function `_month_start_iso()` produced format X (Python isoformat, T-separator)
- Test fixtures used that same helper to build comparison data → all in format X
- Production code stored `created_at` via SQLite's `datetime('now')` → format Y (space-separator)
- Production read path compared format-Y data against helper-generated format-X month_start
- **Test setup never crossed the language boundary that production crosses.** SQLite was never invoked in the test setup; only in production runtime.

Closely related to subspecies (iii) mock-fidelity, except instead of a mock, the test setup uses the function-under-test to build fixtures. **High-leverage because the same pattern bites at every cross-language / cross-runtime boundary**: Python ↔ SQLite, JS ↔ Android native, JSON serialize ↔ Date parse round-trip, OpenAPI spec ↔ FastAPI route handlers. Any time a value crosses a boundary where the OTHER side stamps/transforms/parses, and the test setup stays on the function-side rather than reaching across.

**Lint coverage stays DOC-ONLY — that's correct.** Static analysis can't tell whether a test fixture was set up "from the right side" of an integration boundary. But the doc earns its DOC-ONLY status by teaching the recognition pattern, not just the fix:

- **Recognition heuristic** (in the case-study prose): "Did the test setup invoke the same code path that production WRITES through? Or did the test setup invoke the function-under-test to build the data the function-under-test will then consume?"
- **Mitigation by category**:
  - SQLite ↔ Python: test fixtures should `INSERT` via raw SQL using `datetime('now')`, not via Python helpers that produce different formats
  - JS ↔ native: jest tests should invoke the native module's actual signature OR the test-setup builder should be co-located with the production write path
  - JSON ↔ Date: serialize with the same library production uses, not `JSON.stringify(new Date())` shortcuts in tests

The doc must explicitly enumerate the cross-boundary categories so future readers recognize the pattern at the next boundary, not just the SQLite one.

### Correction 3 — Closure-state rule's exempt clause

Plan v1.0's exempt clause for `motodiag/no-closure-state-capture-in-native-callback` had three escape hatches:

> Exempt: the function body references ONLY `*Ref.current.*` reads, OR uses `useState` setters (not getters), OR explicitly opts out via `// eslint-disable-next-line motodiag/no-closure-state-capture-in-native-callback`.

The "useState setters not getters" clause is real but subtle — it'll confuse contributors six months out. Replaced with the cleaner alternative:

**Updated exempt clause**: skip the rule entirely if the callback doesn't reference any non-ref state binding. **"Non-ref state binding" is scoped narrowly to bindings declared via `useState` or `useReducer` only** — not external store subscriptions (Redux / Zustand / Jotai / TanStack Query / etc.). External store subscriptions aren't the F9 subspecies this rule targets; their reactivity model is fundamentally different from local React state and they don't suffer the registration-time-capture bug shape.

Concretely, the rule fires when:
1. Callback function literal is passed as a property value to a `*.current.*` member call (loose AST match for `*Ref.current.method({key: fn})` shape)
2. The function body references at least one identifier that resolves to a `useState` / `useReducer` getter binding in an enclosing scope
3. AND the identifier isn't a `.current` ref access on a `useRef`-declared binding
4. AND no `// eslint-disable-next-line motodiag/no-closure-state-capture-in-native-callback` opt-out is present

If the callback only reads from refs, useStore subscriptions, props, or top-level constants — clean.

### Correction 4 — Wave 2 (Commits 2 + 3) parallelized; bake into commit cadence

Plan v1.0's commit-cadence section listed Commits 2 and 3 sequentially. Pre-flight on cross-references confirmed they are file-disjoint AND import-disjoint:

- Commit 2 outputs: `scripts/check_f9_patterns.py` (Python), `tests/test_phase191c_f9_lint.py` (pytest), `.pre-commit-config.yaml`, `pyproject.toml`, backend `README.md`. Backend-only.
- Commit 3 outputs: `eslint-plugin-motodiag/` (JS ES module), RuleTester tests, `eslint.config.js`, mobile `README.md` (lint hooks section). Mobile-only.

Both consume the SAME source-of-truth (the pattern guide doc from Commit 1) but neither produces output the other consumes. Subspecies (ii) is implemented in BOTH stacks but as independent rule implementations sharing only the conceptual contract.

**Wave 2 = parallel Builder dispatch (Builder-A backend Commit 2 + Builder-B mobile Commit 3 simultaneously)** after Commit 1 lands. Architect runs both pytest + jest+lint independently; commits in any order.

### Correction 5 — Reconciliation sentence in pattern-doc intro

Per architect: preserve the audit trail of the instance-count change without backfilling sealed-history docs. The pattern guide intro must include this sentence verbatim:

> "Earlier closure docs from Phase 191B refer to '6 instances' of this family. That count merged the two distinct bugs fixed in commit 832579d (deploy-path-missing-wiring and format-coincidence-latent / self-validating-test-setup) into a single instance. Going forward, this catalog tracks them as separate subspecies. Total instances: 7."

This goes in the doc, not the plan. Builder-A (Commit 1) lands it verbatim; Architect verifies at gate.

### Correction 6 — Operational ask: paired review of subspecies (ii) across both stacks before Commit 4 ships

Subspecies (ii) "hardcoded source-of-truth values" is implemented in BOTH stacks: mobile ESLint rule `motodiag/no-hardcoded-model-ids-in-tests` (Commit 3) AND backend `scripts/check_f9_patterns.py --check-model-ids` (Commit 2). Both heuristics target the same conceptual pattern. **If their heuristics drift, that's a consistency bug** — e.g., mobile flags `claude-(haiku|sonnet|opus)-\d` shape but backend flags only `claude-sonnet-` prefix; or one stack exempts `KNOWN_BOGUS_IDS` and the other doesn't.

**Architect-side paired review of the subspecies (ii) implementations after Wave 2 returns + before Commit 4 ships.** Architect (me) checks:
1. Both rules fire on the same canonical anti-example (the 14-references Phase 191B C2 scenario)
2. Both rules exempt the same set of patterns (KNOWN_GOOD_MODEL_IDS / KNOWN_BOGUS_IDS / MODEL_ALIASES / MODEL_PRICING — both stacks need the same exempt list)
3. The diagnostic-formatted output from each rule says the same thing in the same shape (file + line + offending literal + rule name)
4. If heuristic regex differs (it likely will — JS regex syntax vs Python `re`), confirm the regexes match the same input set on a small fixture run

If drift detected → fix in a paired commit before Commit 4 ships. Documented as a Commit 3.5 fix-cycle if needed.

---

(End of v1.0.1 corrections. Original v1.0 plan continues below — content remains accurate for everything except the 6→7 prose, the subspecies #5 label, the closure-state rule's exempt clause, the Commit 2/3 parallel-dispatch decision, and the reconciliation sentence requirement. Re-reading the original sections is OK as long as the v1.0.1 corrections override those specific points.)

---

## Goal

Build the dedicated mitigation infrastructure for the F9 "snapshot/assumption doesn't match runtime" failure family that has surfaced 6 times across Track I (Phases 188 / 190 / 191 / 191B C1 / 191B C6 / 191B C2). Per architect's PASS-handoff observation at Phase 191B finalize: "the pattern is robust enough to merit dedicated mitigation infrastructure (contributing.md doc + lint rule for mock-vs-runtime drift at the test-author level). Cost of intervention: one phase. Cost of NOT doing it: another 3-4 fix-cycles per phase that introduces a new external integration."

Phase 191C is option (a) from the Phase 192 scope-pinning round: a small, focused tooling-and-docs phase inserted before Phase 192. Mirrors the substrate-then-feature pattern (Phase 191 → 191B → 191C as feature-then-meta-tooling-fix-from-lessons-learned). Phase 192 (diagnostic report viewer per ROADMAP) follows.

CLI — none new (lint rules + docs only).

## Scope decisions locked at pre-plan Q&A (2026-05-04)

All A/B/C/D/E recommendations accepted as-written with four refinements:

- **B1(iii) narrowed**: scope (iii) (mock-vs-real-fetch shape mismatch) IS lintable as a specific rule, not warning-only. Specific shape: "mocked async functions must return `Promise<T>` where T is the imported return type, not `as any` / `as unknown as ...`." This rule would have caught Phase 191B C6's file:// bug (the mock used a lazy-typed return). Enforced rule, not warning-only.
- **B3 severity rollout**: ship rules at `warn` for Commits 3-4. In Commit 5 finalize, run rules against current `main` on both repos, fix any false positives in the same commit, then bump severity to `error`. Engages the gate on a clean baseline; avoids shipping a noisy change on a codebase that's never been linted by these rules.
- **C1 layer**: standalone `scripts/check_f9_patterns.py` as pre-commit hook + standalone CLI (NOT pytest-collection). Pytest-collection failures look like test failures and disrupt the debug loop; lint stays separate from test runtime per the established `pytest-vs-ruff` separation in this repo.
- **CI reality**: NEITHER repo has GitHub Actions or any other CI. Mobile deferred CI to Phase 204 / Gate 10 per ADR-004; backend has no CI at all (solo-dev posture). Commit 4's "wire into CI" reframed: pre-commit hook locally (`.pre-commit-config.yaml` for backend, `husky` + `lint-staged` for mobile) is the deliverable. Real CI integration explicitly deferred — when Phase 204 wires GitHub Actions, the F9 lint rules go in alongside the existing `pytest`/`tsc`/`jest` invocations.

**Honest retroactive-coverage claim**: 5 of the 6 F9 instances would have been caught by these lint rules. The 6th (Phase 191B C1's timestamp-format bug — function-under-test produces output the rest of the system doesn't consume in the same format) is doc-only catch — the bug shape isn't statically lintable because the format mismatch is a runtime semantic mismatch between two different code paths, neither of which is "wrong" in isolation.

## Outputs

### New files (~7)

**Backend (4):**
- `docs/patterns/f9-mock-vs-runtime-drift.md` — pattern guide with all 6 case studies as anti-examples, fix commit hashes, and per-subspecies mitigation strategy. Cross-linked from mobile.
- `scripts/check_f9_patterns.py` — standalone Python script implementing F9 pattern checks. Exit 0 on clean; exit 1 + diagnostic-formatted output on findings. Importable as a module for unit testing.
- `tests/test_phase191c_f9_lint.py` — unit tests for `scripts/check_f9_patterns.py` covering: positive case (the 14-bogus-model-IDs scenario from Phase 191B C2), negative case (current `main` after fix-cycle-4's scrub), false-positive guards (legitimate model-ID literals in `KNOWN_BOGUS_IDS` test data + `engine/client.py:MODEL_ALIASES`/`MODEL_PRICING` pinned constants).
- `.pre-commit-config.yaml` (NEW) — pre-commit framework config wiring `scripts/check_f9_patterns.py` as a local hook. Documented as architect-side opt-in (`pre-commit install`); not enforced via missing-CI infrastructure.

**Mobile (3):**
- `docs/patterns/f9-mock-vs-runtime-drift.md` — the same pattern guide (cross-linked twin of the backend doc; same 6 case studies + same anti-examples; mobile-specific TS/RN code samples).
- `eslint-plugin-motodiag/` — local custom ESLint plugin directory. Contains:
  - `package.json` (private, `motodiag/eslint-plugin-motodiag@1.0.0`, no npm publish)
  - `index.js` exporting the rule registry
  - `rules/no-closure-state-capture-in-native-callback.js` — F9 subspecies (i)
  - `rules/no-hardcoded-model-ids-in-tests.js` — F9 subspecies (ii)
  - `rules/no-loose-typed-async-mock-returns.js` — F9 subspecies (iii) per flag 1
  - `tests/` for each rule (RuleTester unit tests covering positive + negative + false-positive cases)
- `.husky/pre-commit` (NEW) — husky-installed git hook running `npm run lint` (which now picks up the new plugin via `eslint.config.js`). Architect-side opt-in (`npx husky init`); not enforced via missing-CI infrastructure.

### Modified files (~5)

**Backend (2):**
- `pyproject.toml` — version `0.2.0 → 0.3.0` (Track I tooling-phase bump; F9 intervention is meaningful enough to merit a minor); add `pre-commit>=3.5` to `[dev]` extras.
- `README.md` — new "Pre-commit hooks" section pointing at `.pre-commit-config.yaml` + `pre-commit install` step + reference to `docs/patterns/f9-mock-vs-runtime-drift.md`.

**Mobile (3):**
- `package.json` — version `0.0.7 → 0.0.8`; add `"eslint-plugin-motodiag": "file:./eslint-plugin-motodiag"` (relative-path local install) + `husky` + `lint-staged` to devDependencies.
- `eslint.config.js` (or `.eslintrc.cjs` — depends on what the repo currently uses) — register the new plugin + enable its rules at `warn` severity (Commits 3-4) → `error` (Commit 5).
- `README.md` — new "Lint hooks" section pointing at husky setup + `docs/patterns/f9-mock-vs-runtime-drift.md`.

### Tests

- `tests/test_phase191c_f9_lint.py` — backend lint script tests (~12-15 tests across 3 classes: positive cases, negative cases, false-positive guards)
- `eslint-plugin-motodiag/rules/__tests__/*.test.js` — RuleTester unit tests for each of the 3 mobile rules (~4-6 tests per rule = ~15 tests total)

## Logic

### F9 pattern subspecies catalog (the source of truth)

The pattern guide doc + lint rules both reference this catalog. Six instances; five are statically lintable.

| # | Phase | Surfaced | Subspecies | Lint coverage | Fix commit |
|---|-------|----------|------------|---------------|------------|
| 1 | 188 C7 | 2026-04-26 | Mock-shape mismatch (HVE wrapper assumed Phase 175 envelope; FastAPI returns `{detail: [...]}` shape) | Subspecies (iii) — would have caught | `eb42c21` |
| 2 | 190 C7 | 2026-04-28 | Substring-match-on-error-text discriminator (assumed shape, broke when shape diverged) | Subspecies (iii) — would have caught | `744becf` |
| 3 | 191 C3 | 2026-04-28 | Closure captures useState at registration time, not fire time (`onRecordingFinished` registered with `cameraRef.startRecording`) | **Subspecies (i)** — would have caught | `ffa383c` |
| 4 | 191B C1 | 2026-05-01 | `motodiag serve` never called `init_db` → schema stale at runtime; backend ran on v38 with v39 code | **Subspecies (i) extension** — would have caught (no-init_db-call-in-serve-cmd lint rule) | `832579d` |
| 5 | 191B C1 | 2026-05-01 | Timestamp-format mismatch: Python isoformat (T-separator) vs SQLite `datetime('now')` (space-separator). Same-day-prefix lex comparison broke. | **DOC-ONLY** — runtime semantic mismatch between two valid code paths, not statically lintable | `832579d` |
| 6 | 191B C6 | 2026-05-03 | RN FormData missing `file://` prefix on Android; mock used lazy-typed return so test never hit real fetch | **Subspecies (iii)** — would have caught (mocks must return typed `Promise<T>` not `as any`) | `7e9702e` |
| 7 | 191B C2 | 2026-05-04 | Hardcoded fabricated model ID across 14 test references — tests ASSERTED THE BUG INTO PLACE | **Subspecies (ii)** — would have caught | `c453872` |

(7 fix commits, 6 distinct instances per phase-numbering — instance #4 was discovered alongside instance #5 in fix-cycle-1; counted as one for the "6 instances" headline, broken out here for lint-rule mapping.)

### Subspecies (i): closure-state capture in native callbacks (mobile only)

**Rule name**: `motodiag/no-closure-state-capture-in-native-callback`

**Heuristic**: any function literal passed as a property value to a `*.current.*` member call should not reference any non-`*Ref.current` state binding in its body. The fix pattern is `useRef`.

**Anti-example** (Phase 191 Commit 3):
```ts
const [state, dispatch] = useReducer(recordingTransition, initialRecordingState);

cameraRef.current?.startRecording({
  onRecordingFinished: video => {
    // BUG: state captured at registration time. By the time
    // onRecordingFinished fires, state may have transitioned via
    // AppState handler — but THIS callback sees the snapshot.
    const wasInterrupted = state.kind === 'stopping' && state.reason === 'interrupted';
    // ...
  },
});
```

**Fix pattern** (the commit `ffa383c` shape):
```ts
const interruptedRef = useRef<boolean>(false);

// In AppState handler:
interruptedRef.current = true;
cameraRef.current?.stopRecording().catch(() => undefined);

// In onRecordingFinished:
const wasInterrupted = interruptedRef.current;  // reads at fire time, not registration time
```

**Rule scope**: function literals passed as object property values where the receiver chain contains `.current.` (loose AST match for `*Ref.current.method({key: fn})` shape).

**Exempt**: the function body references ONLY `*Ref.current.*` reads, OR uses `useState` setters (not getters), OR explicitly opts out via `// eslint-disable-next-line motodiag/no-closure-state-capture-in-native-callback`.

### Subspecies (ii): hardcoded values that should reference a source-of-truth set

**Rule name** (mobile): `motodiag/no-hardcoded-model-ids-in-tests`
**Backend equivalent**: `scripts/check_f9_patterns.py` mode `--check-model-ids`

**Heuristic**: literal string values matching the model-ID shape `claude-(haiku|sonnet|opus)-\d` appearing inside test files MUST be inside an explicit allowlist set OR imported from a source-of-truth module.

**Anti-example** (Phase 191B Commit 2 — the 14-references nightmare):
```py
# tests/test_phase79_engine_client.py
def test_resolve_sonnet_alias():
    assert _resolve_model("sonnet") == "claude-sonnet-4-5-20241022"  # bogus ID hardcoded
```

**Fix pattern**:
```py
# tests/test_phase191b_vision_model_validation.py
KNOWN_GOOD_MODEL_IDS = {
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
}

def test_resolve_sonnet_alias():
    resolved = _resolve_model("sonnet")
    assert resolved in KNOWN_GOOD_MODEL_IDS
```

**Rule scope** (mobile): regex match against literal strings in `__tests__/**/*.{ts,tsx}`. False-positive guards: skip if the string appears in an `as const` array literal whose name matches `KNOWN_*_MODEL_IDS`, OR if it appears as a value in an `.eslintrc.cjs`-declared allowlist constant.

**Rule scope** (backend): regex match against literal strings in `tests/**/*.py`. False-positive guards: skip if the string appears in `KNOWN_GOOD_MODEL_IDS` / `KNOWN_BOGUS_IDS` / `MODEL_ALIASES` / `MODEL_PRICING` set/dict literals.

### Subspecies (iii): loose-typed async mock returns

**Rule name** (mobile): `motodiag/no-loose-typed-async-mock-returns`

**Heuristic**: `jest.fn().mockResolvedValue(X)` calls where `X` is typed as `as any` / `as unknown as Y` / has no inferable type. Mocked async functions MUST return `Promise<T>` where T is the imported return type from the module being mocked.

**Anti-example** (the Phase 191B C6 shape):
```ts
const mockApi = {
  POST: jest.fn().mockResolvedValue({data: {} as any, error: undefined}),  // BUG: lazy type
};
// Test passes; production fails because the real api.POST has a typed
// contract the mock doesn't honor.
```

**Fix pattern**:
```ts
import type {paths} from '../../src/api-types';
type UploadResponse = paths['/v1/sessions/{session_id}/videos']['post']['responses']['201']['content']['application/json'];

const mockApi = {
  POST: jest.fn<Promise<{data: UploadResponse | undefined; error: undefined}>, [...]>().mockResolvedValue({...}),
};
```

**Rule scope**: AST match for `jest.fn().mockResolvedValue(...)` where the type argument to `jest.fn` is missing OR the resolved value contains `as any` / `as unknown as`.

**Exempt**: the `as any` / `as unknown as` is followed by a TS-typed annotation matching a `paths[...]` or `components['schemas'][...]` import from `api-types.ts`.

### Subspecies (iv) — backend deploy-path no-init_db check

**Rule name**: `scripts/check_f9_patterns.py` mode `--check-deploy-path-init-db`

**Heuristic**: any module under `src/motodiag/cli/` defining a `*_cmd` Click command that internally invokes `uvicorn.run` (or `app.run` / similar serve-the-API patterns) MUST call `init_db()` before the run invocation.

**Anti-example** (the original `serve.py` pre-fix-cycle-1):
```py
# src/motodiag/cli/serve.py
def serve_cmd(...):
    settings = get_settings()
    uvicorn.run("motodiag.api:create_app", ..., factory=True)
    # BUG: no init_db() before uvicorn.run — schema stays stale.
```

**Fix pattern** (commit `832579d`):
```py
def serve_cmd(...):
    settings = get_settings()
    init_db(settings.db_path, apply_migrations=True)  # required before serve
    uvicorn.run("motodiag.api:create_app", ..., factory=True)
```

**Rule scope**: AST walk over `src/motodiag/cli/` files. Find function definitions with the `@cli_group.command(...)` decorator. Inside the function body, check for `uvicorn.run` / `app.run` / similar patterns. If found AND no `init_db(` call exists in the same function body, fail.

**Exempt**: explicit `# f9-noqa: deploy-path-init-db` comment on the line of the run invocation (with reason).

### Pattern doc structure

Both `docs/patterns/f9-mock-vs-runtime-drift.md` files (backend + mobile) follow the same structure:

```
# F9 — Mock-vs-Runtime Drift Failure Family

## Problem statement
Tests pass against assumptions baked into mocks; production fails when reality diverges.

## Why this matters
Each F9 bug costs ~4-6 architect hours per fix-cycle (smoke halt, diagnose, fix, re-verify).
After 6 instances on Track I across 4 phases, the pattern is robust enough to merit
dedicated mitigation infrastructure.

## Subspecies catalog (with case studies)
[the table above, expanded with code samples + commit links]

## Mitigation by subspecies
- (i) Closure-state capture: useRef pattern + `motodiag/no-closure-state-capture-in-native-callback` lint rule
- (ii) Hardcoded source-of-truth values: centralized allowlist set + `motodiag/no-hardcoded-model-ids-in-tests` lint rule (mobile) + `scripts/check_f9_patterns.py --check-model-ids` (backend)
- (iii) Loose-typed mock returns: explicit Promise<T> typing + `motodiag/no-loose-typed-async-mock-returns` lint rule
- (iv) Deploy-path no-init_db: explicit init_db() call before serve + `scripts/check_f9_patterns.py --check-deploy-path-init-db`
- (Doc-only) Format/semantic mismatch between two code paths: documented; lint not feasible

## When you suspect F9 in your code
Checklist + decision tree for new code review.

## Cross-references
[link to backend doc <-> link to mobile doc; link to each fix commit]
```

## Key Concepts

- **AST-based custom ESLint rules**: ESLint provides `RuleTester` for unit-testing custom rules. The plugin format is well-documented; local plugins (no npm publish) are loaded via `eslint.config.js`'s `plugins` array with a relative require.
- **Pre-commit framework**: Python-based pre-commit (https://pre-commit.com) is the standard tool. `.pre-commit-config.yaml` declares hooks (local OR remote); `pre-commit install` wires them into git's `pre-commit` hook. Architect-side opt-in.
- **Husky**: Node-side equivalent of pre-commit. `husky install` adds `.husky/pre-commit` running whatever shell command. Pairs naturally with `lint-staged` for file-scoped runs.
- **Phased severity rollout**: ESLint and ruff both support per-rule severity (`warn` / `error`). Standard practice when introducing a new rule against legacy code: ship at `warn`, fix violations, then bump to `error`. Phase 191C explicitly does this in Commit 5 finalize after running the rules against `main`.

## Verification Checklist

- [ ] `docs/patterns/f9-mock-vs-runtime-drift.md` exists in both repos with all 6 case studies + per-subspecies mitigation
- [ ] `scripts/check_f9_patterns.py` runs cleanly on current backend `main` (zero findings after fix-cycle-1's serve.py + fix-cycle-4's model-string scrub)
- [ ] `scripts/check_f9_patterns.py` fires on the 14-references regression case (synthetic test that re-introduces a bogus ID)
- [ ] `scripts/check_f9_patterns.py` fires on the no-init_db-in-serve regression case (synthetic test that deletes the init_db call)
- [ ] `tests/test_phase191c_f9_lint.py` passes (~12-15 tests)
- [ ] `eslint-plugin-motodiag` package builds + loads via `eslint.config.js`
- [ ] All 3 ESLint rules pass RuleTester unit tests
- [ ] Running `npm run lint` on current mobile `main` produces ZERO findings at `warn` severity (clean baseline confirmed before bumping to `error`)
- [ ] Running `npm run lint` against the 3 anti-example fixtures produces 1 finding per fixture (regression coverage)
- [ ] `.pre-commit-config.yaml` invokes `scripts/check_f9_patterns.py`; `pre-commit run --all-files` exits 0 on current main
- [ ] `.husky/pre-commit` invokes `npm run lint`; manual git commit with a deliberately-bad change is blocked
- [ ] Backend `pyproject.toml` 0.2.0 → 0.3.0; `pre-commit` added to `[dev]` extras
- [ ] Mobile `package.json` 0.0.7 → 0.0.8; husky + lint-staged + eslint-plugin-motodiag added
- [ ] Backend + mobile READMEs gain "Pre-commit hooks" / "Lint hooks" sections pointing at the F9 pattern doc
- [ ] No regression: full Phase 175-184 backend integration tests + Phase 188-191 mobile tests + Phase 191B suite all green
- [ ] **Severity bumped from `warn` to `error` in Commit 5 ONLY AFTER** a clean-baseline run on `main` (zero false positives confirmed; any false positives fixed in the same Commit 5)

## Risks

- **Custom ESLint plugin maintenance**. Local plugin = no upstream version bumps; the rules need to be maintained by the project. Mitigation: rules are small (~50-100 LoC each); RuleTester unit tests pin behavior; documented in the pattern guide so future contributors understand the why.
- **False positives at the severity bump**. `error`-severity introduction on a never-linted codebase is the highest-risk moment. Mitigation: phased rollout per flag 2 — `warn` for Commits 3-4; clean-baseline confirmation in Commit 5 before the bump; any false positives fixed in the same commit.
- **Pre-commit/husky friction**. Architect opts in via `pre-commit install` / `npx husky init` once per machine. If the architect skips opt-in, the rules don't run at commit time. Mitigation: documented in README; Phase 204's CI integration enforces. Acknowledge this in the pattern doc explicitly.
- **AST heuristics miss edge cases**. The closure-state-capture rule's heuristic is "function literal passed as property value where receiver chain contains `.current.`" — false negatives possible if the callback is named/extracted. Mitigation: documented as "best-effort lint, not exhaustive"; the doc + reviewer attention catch the edge cases.
- **Subspecies (iii) typed-mock rule might be too strict**. Some legitimate mocks use `as any` for genuinely-untyped third-party SDK shapes. Mitigation: the rule's exempt clause for `as any as paths[...]` annotations covers the most common case; broader exemption via `// eslint-disable-next-line` documented in the pattern guide.
- **Doc-only catch for subspecies (timestamp format)**. The 6th F9 instance (Phase 191B C1 timestamp) isn't lint-catchable. Honest claim: 5 of 6 caught by lint, 1 by doc. The pattern guide explicitly calls out the limit so future readers don't expect lint-coverage that doesn't exist.

## Commit plan (5 commits on `phase-191C-f9-architectural-intervention` branch on BOTH repos)

**Commit 1 — Pattern guide doc** (both repos). `docs/patterns/f9-mock-vs-runtime-drift.md` written from scratch with all 6 case studies as anti-examples (with code samples + fix commit links) + per-subspecies mitigation strategy + cross-references between backend + mobile copies. Single Builder dispatch can write both copies in parallel since they share content.

**Commit 2 — Backend lint script + tests + .pre-commit-config.yaml** (backend repo only). `scripts/check_f9_patterns.py` with two checks: `--check-model-ids` (subspecies ii) + `--check-deploy-path-init-db` (subspecies iv). Standalone CLI; importable as a module. `tests/test_phase191c_f9_lint.py` with positive + negative + false-positive-guard cases. `.pre-commit-config.yaml` wires the script as a local hook. `pyproject.toml` bumps 0.2.0 → 0.3.0 + adds `pre-commit>=3.5` to `[dev]`. README "Pre-commit hooks" section.

**Commit 3 — Mobile ESLint plugin + tests** (mobile repo only). `eslint-plugin-motodiag/` directory with `package.json` (private, file-local) + `index.js` rule registry + 3 rules + RuleTester unit tests for each. Rules registered in `eslint.config.js` at `warn` severity. Verify zero findings on current `main`. `package.json` bumps 0.0.7 → 0.0.8 + adds the plugin as a `file:` dep.

**Commit 4 — Husky + lint-staged wiring** (mobile repo only). Add husky + lint-staged to mobile devDependencies. `.husky/pre-commit` runs `npx lint-staged`. `lint-staged` config in `package.json` runs ESLint on staged `.ts`/`.tsx` files. Verify the hook fires on a deliberately-bad staged change. README "Lint hooks" section.

**Commit 5 — Severity bump + finalize** (both repos). Run all rules against current `main` on both repos; confirm zero false positives (or fix in the same commit with documented exemptions). Bump ESLint rule severity from `warn` → `error` in `eslint.config.js`. Backend `scripts/check_f9_patterns.py` keeps a single severity (always `error` since it's invoked explicitly via pre-commit, not severity-gradable like ESLint). Move plan docs in_progress → completed; backend `implementation.md` 0.13.8 → 0.13.9; backend `phase_log.md` closure entry; ROADMAP mark; mobile `implementation.md` 0.0.9 → 0.0.10; mobile FOLLOWUPS update (close F9; F12 stays open since it's a more specific test addition than the general lint rule covers).

Each commit: backend `pytest` green + `ruff check` clean before next; mobile `tsc --noEmit` + `npm test` + `npm run lint` green at Commit 5.

## Architect gate

**Single-stage gate after Commit 5** (~6-8 step smoke; no native-module integration; no feature surface — purely tooling + docs):

1. Both `docs/patterns/f9-mock-vs-runtime-drift.md` files render correctly (markdown validates; cross-links resolve; case study code samples are syntactically valid).
2. Backend `scripts/check_f9_patterns.py --check-model-ids` runs against `main` → exit 0, zero findings.
3. Backend `scripts/check_f9_patterns.py --check-deploy-path-init-db` runs against `main` → exit 0, zero findings.
4. Backend regression test re-introducing a bogus model ID into a test file → script fires with diagnostic-formatted output naming the file + line + offending literal.
5. Backend regression test removing the `init_db()` call from `serve.py` → script fires with diagnostic-formatted output.
6. `pre-commit run --all-files` on backend → exit 0; deliberately-bad commit blocked as expected.
7. Mobile `npm run lint` on `main` → zero findings at `error` severity (post-Commit-5 bump).
8. Mobile lint against the 3 anti-example fixtures (one per rule) → 1 finding per fixture with the rule name + descriptive message.
9. Mobile `npx husky init` + `.husky/pre-commit` setup verified on a fresh emulator-side checkout (or simulated via a fresh clone in `/tmp`).
10. **No regression**: full backend test suite + mobile Jest suite all green.

If gate passes → v1.1 finalize. If gate fails → fix-cycle on the same branch (Phase 188 / 190 / 191 / 191B precedent — though for a docs+tooling phase the failure modes are narrower).

## Versioning targets at v1.1 finalize

- Backend `pyproject.toml`: `0.2.0 → 0.3.0` (Track I tooling-phase bump; F9 intervention is meaningful enough to merit a minor).
- Backend `implementation.md`: `0.13.8 → 0.13.9`.
- Schema: unchanged at v39.
- Mobile `package.json`: `0.0.7 → 0.0.8`.
- Mobile `implementation.md`: `0.0.9 → 0.0.10`.

## Not in scope (firm)

- **Real CI integration**. NEITHER repo has GitHub Actions or any other CI infrastructure. Mobile defers CI to Phase 204 / Gate 10 per ADR-004; backend has no CI. When Phase 204 wires GitHub Actions, the F9 lint rules go in alongside `pytest`/`tsc`/`jest` — but that's a Phase 204 concern. Pre-commit hooks are the deliverable here.
- **Subspecies that aren't statically lintable**. Phase 191B C1's timestamp-format bug is doc-only (runtime semantic mismatch between two valid code paths). The pattern guide calls this out explicitly.
- **General-purpose source-of-truth-set lint rule**. The model-IDs check is concrete; "all hardcoded constants in tests must be in a central set" is too vague to enforce. If new bug shapes surface, Phase 191D would extend the lint with new specific rules.
- **Backend ESLint OR mobile pytest**. Each side uses its native tooling; no cross-stack lint runner.
- **Auto-fix support**. ESLint rules ship without auto-fix initially. Adding `--fix` support is a Phase 192+ polish.
- **Publishing eslint-plugin-motodiag to npm**. Local-only plugin; no need for npm publish until a second project consumes it.
- **CONTRIBUTING.md**. Pattern guide is its own file at `docs/patterns/f9-mock-vs-runtime-drift.md`. A general CONTRIBUTING.md is a different concern; not landing here.

## Smoke test (architect-side, post-build, pre-v1.1)

(Same as the Architect gate above — Phase 191C's gate is the smoke. ~6-8 steps.)
