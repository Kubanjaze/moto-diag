# Phase 191C — Phase Log

**Status:** 🚧 In Progress | **Started:** 2026-05-04
**Repo:** https://github.com/Kubanjaze/moto-diag (backend) + https://github.com/Kubanjaze/moto-diag-mobile (mobile)
**Branch:** `phase-191C-f9-architectural-intervention` (will be created in BOTH repos at Commit 1; both repos get all 5 commits with file overlap split per Outputs section)

---

### 2026-05-04 — Plan v1.0 written

Phase 191C opens as the dedicated mitigation infrastructure for the F9 "snapshot/assumption doesn't match runtime" failure family. Per architect's Phase 191B PASS-handoff observation (2026-05-04): "Sixth F9 instance documented; pattern is robust enough that the architectural-pattern doc + lint rule should be Phase 192's lead ticket."

Pre-plan scope round (2026-05-04): two valid scope readings of "Phase 192" surfaced — original ROADMAP scope (diagnostic report viewer) vs architect's lead-ticket framing (F9 intervention). Three options offered to user; user picked **option (a)**: Phase 191C = F9 intervention only (small, focused, ~5 commits); Phase 192 = report viewer as ROADMAP says. Mirrors the substrate-then-feature precedent (191/191B) with the new shape: feature → meta-tooling-fix-from-lessons-learned.

**Pre-implementation Q&A pinned all scope decisions before plan writing** — same Phase 189/190/191/191B discipline. Five decision sections (A through E) covered:

- A. Doc placement + shape
- B. Mobile lint rule (ESLint) — 3 subspecies + plugin shape + severity
- C. Backend lint rule (ruff/pytest)
- D. Phase 191C commit cadence (5 commits)
- E. Branch model

**All recommendations accepted as-written with four refinements + one confirmation question:**

1. **B1(iii) narrowed**: scope (iii) (mock-vs-real-fetch shape mismatch) IS lintable as a specific rule, not warning-only. Specific shape: "mocked async functions must return `Promise<T>` where T is the imported return type, not `as any` / `as unknown as ...`." Would have caught Phase 191B C6's file:// bug. Enforced rule, not warning-only.
2. **B3 severity rollout**: ship rules at `warn` for Commits 3-4. In Commit 5 finalize, run rules against `main` on both repos, fix any false positives in the same commit, then bump severity to `error`. Engages the gate on a clean baseline.
3. **C1 layer**: standalone `scripts/check_f9_patterns.py` as pre-commit hook + standalone CLI, NOT pytest-collection. Keeps lint separate from test runtime per the established `pytest-vs-ruff` separation.
4. **Subspecies coverage honesty**: 5 of 6 F9 instances would have been caught by these lint rules; Phase 191B C1's timestamp-format bug is doc-only catch (runtime semantic mismatch between two valid code paths, not statically lintable). Don't inflate the lint coverage number.

**CI confirmation question** answered by inspection: **NEITHER repo has CI infrastructure.** Mobile defers CI to Phase 204 / Gate 10 per ADR-004; backend has no CI at all (solo-dev posture). Commit 4's "wire into CI" reframed: pre-commit hook locally (`.pre-commit-config.yaml` for backend, `husky` + `lint-staged` for mobile) is the deliverable. Real CI integration explicitly deferred to Phase 204.

**Honest retroactive-coverage claim baked into the doc**: 5 of 6 F9 instances caught by lint, 1 by doc.

**Files plan:**

- New backend (4): `docs/patterns/f9-mock-vs-runtime-drift.md` + `scripts/check_f9_patterns.py` + `tests/test_phase191c_f9_lint.py` + `.pre-commit-config.yaml`.
- New mobile (3): `docs/patterns/f9-mock-vs-runtime-drift.md` (twin of backend) + `eslint-plugin-motodiag/` directory (3 rules + RuleTester tests) + `.husky/pre-commit`.
- Modified backend (2): `pyproject.toml` (0.2.0 → 0.3.0 + add `pre-commit>=3.5` to `[dev]`) + `README.md` (Pre-commit hooks section).
- Modified mobile (3): `package.json` (0.0.7 → 0.0.8 + husky + lint-staged + eslint-plugin-motodiag local file dep) + `eslint.config.js` (register plugin) + `README.md` (Lint hooks section).

**Lint rules planned (5 total across the two stacks):**

Mobile (ESLint custom plugin `motodiag/`):
- `no-closure-state-capture-in-native-callback` — F9 subspecies (i); catches the Phase 191 C3 closure-state bug shape
- `no-hardcoded-model-ids-in-tests` — F9 subspecies (ii); catches the Phase 191B C2 14-references-pinning-the-bug subspecies
- `no-loose-typed-async-mock-returns` — F9 subspecies (iii); catches the Phase 191B C6 file:// shape (mock used `as any` lazy typing)

Backend (`scripts/check_f9_patterns.py`):
- `--check-model-ids` — backend equivalent of subspecies (ii) for `tests/**/*.py`
- `--check-deploy-path-init-db` — F9 subspecies (iv); AST walks `src/motodiag/cli/` for `*_cmd` Click commands invoking `uvicorn.run` / `app.run` without a preceding `init_db()` call (catches the Phase 191B C1 serve.py bug shape)

Doc-only (no lint rule): Phase 191B C1's timestamp-format mismatch.

**No backend route changes. No schema changes (still v39). No new ADR.** The pattern guide doc is reference material, not a load-bearing decision worth a durable ADR slot.

**Commit plan (5 commits on `phase-191C-f9-architectural-intervention` branch on BOTH repos):**

1. **Pattern guide doc** (both repos, single Builder dispatch since they share content) — all 6 case studies as anti-examples + per-subspecies mitigation strategy + cross-references between backend + mobile copies.
2. **Backend lint script + tests + .pre-commit-config.yaml** (backend repo only) — `scripts/check_f9_patterns.py` with `--check-model-ids` + `--check-deploy-path-init-db` modes; ~12-15 unit tests; `pyproject.toml` 0.2.0 → 0.3.0 + add `pre-commit>=3.5` to `[dev]`; README "Pre-commit hooks" section.
3. **Mobile ESLint plugin + tests** (mobile repo only) — `eslint-plugin-motodiag/` directory + 3 rules + RuleTester unit tests + register at `warn` severity. Verify zero findings on current `main`.
4. **Husky + lint-staged wiring** (mobile repo only) — `.husky/pre-commit` runs `npx lint-staged`; lint-staged runs ESLint on staged TS files. Verify hook fires on a deliberately-bad staged change.
5. **Severity bump + finalize** (both repos) — run rules against `main`; confirm zero false positives (or fix in same commit); bump ESLint rules `warn` → `error`; move plan docs in_progress → completed; backend `implementation.md` 0.13.8 → 0.13.9; backend `phase_log.md` closure entry; ROADMAP mark; mobile `implementation.md` 0.0.9 → 0.0.10; mobile FOLLOWUPS update (close F9 with this commit's hash; F12 stays open as a more-specific test addition the general lint doesn't cover).

**Versioning targets at v1.1 finalize:**

- Backend `pyproject.toml`: 0.2.0 → 0.3.0 (Track I tooling-phase bump).
- Backend `implementation.md`: 0.13.8 → 0.13.9.
- Schema: unchanged at v39.
- Mobile `package.json`: 0.0.7 → 0.0.8.
- Mobile `implementation.md`: 0.0.9 → 0.0.10.

**Single-stage architect gate after Commit 5** (~6-8 steps; no native-module integration; no feature surface — purely tooling + docs). Gate verifies: docs render correctly, both lint scripts run cleanly on `main`, regression tests fire on synthetic anti-examples, pre-commit + husky hooks block deliberately-bad commits, no test regression. If gate fails → fix-cycle on same branch (failure modes narrower than a feature phase).

**Next:** plan commit on backend `master` (this file + `191C_implementation.md` v1.0), then create `phase-191C-f9-architectural-intervention` branch in both repos and start Commit 1 (pattern guide doc — single Builder dispatch since both copies share content).
