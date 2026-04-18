# MotoDiag Phase 133 — Phase Log

**Status:** ✅ Complete | **Started:** 2026-04-17 | **Completed:** 2026-04-18
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-18 04:30 — Build complete (Builder agent + Architect trust-but-verify)
Phase 133 Gate 5 PASSED. Builder shipped clean code first try; sandbox blocked Python for the agent so Architect ran 7 phase tests locally — all passed in 6.04s. 19-step mechanic CLI workflow executes cleanly on a shared DB fixture with all three AI call paths mocked. Deviations: test count consolidated from planned 15-20 to 7 (same pattern as Gate R's 20→10), subprocess-pytest-rerun of Gate R dropped in favor of schema-version + import-diagnostic checks.

---

### 2026-04-17 16:07 — Plan written, v1.0
Gate 5: CLI integration test — the checkpoint that closes Track D (mechanic CLI, phases 109-132). Single new test file `tests/test_phase133_gate_5.py` with ~15-20 tests across 3 classes. Pattern mirrors Phase 121's Gate R: one big end-to-end workflow test using Click's `CliRunner` to drive the real `motodiag.cli.main:cli` group through 18 command invocations on a shared DB fixture, plus a small CLI-surface breadth suite, plus regression tests that re-run Gate R and verify schema >= 15.

**Scope:**
- **Part A** (`TestMechanicEndToEnd`, 1 big test): `garage add` → `garage list` → `motodiag quick "won't start"` → `diagnose list` → `diagnose show` → `diagnose show --format md/html/pdf --output` → `diagnose annotate` → `diagnose reopen` → `code P0115` → `code P0115 --explain` → `kb list` → `kb search` → `kb show --format md` → `cache stats` → `intake quota` → `tier --compare` → `completion bash`. Shared DB fixture, three AI mocks (`_default_diagnose_fn`, `_default_interpret_fn`, `_default_vision_call`), zero live tokens.
- **Part B** (`TestCliSurface`, 4 tests): all 14 canonical top-level commands registered, 4 hidden aliases (`d`/`k`/`g`/`q`) present but not in `--help`, expected subcommands per subgroup, subprocess `--help` exits 0.
- **Part C** (`TestRegression`, 3 tests): Phase 121 Gate R's workflow test still passes, `SCHEMA_VERSION >= 15`, all `motodiag.cli.*` submodules import cleanly.

**Constraints:**
- Zero new production code — pure observation over the existing CLI surface (all Phase 109-132 commands).
- Zero schema changes — stays at v15 from Phase 131.
- Zero live API tokens — mandatory mock patches at the boundary for diagnose, code-interpret, and vision.
- CliRunner over subprocess for the workflow test (10-100x faster, cleaner exception surface); subprocess reserved for the import-graph smoke test only.

**Key design decisions captured in v1.0:**
1. **One big test, not 18 small ones.** State flows through the workflow (session created → annotated → reopened → exported) — siloed tests wouldn't catch cross-step integration bugs. This matches Phase 121 Gate R's proven pattern.
2. **Seed DTC P0115 + one known-issue entry in the fixture.** Keeps `code P0115` and `kb search "stator"` tests hermetic without depending on production data files.
3. **Re-run Phase 121's Gate R** in Part C as a "Track D did not break the substrate" claim. ~4s extra but high signal-to-noise.
4. **Pin mock patch paths in the file docstring.** Any future renamer of `_default_diagnose_fn` / `_default_interpret_fn` / `_default_vision_call` must update Gate 5 — documented risk, accepted.
5. **Hidden-alias test uses structural substring match** (`"\n  d "` as a row marker), not byte-exact help text. Tolerates minor Click formatting changes.

**Next:** Write `tests/test_phase133_gate_5.py`, run it, fix any integration bugs surfaced, finalize to v1.1 with Deviations + Results, then close Track D and promote phase docs to `completed/`.
