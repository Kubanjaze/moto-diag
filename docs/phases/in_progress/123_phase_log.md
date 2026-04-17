# MotoDiag Phase 123 — Phase Log

**Status:** 🔄 In Progress | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 22:20 — Plan written, v1.0
Interactive diagnostic session CLI. New `src/motodiag/cli/diagnose.py` orchestration module + 4 new CLI subcommands under `diagnose`: start (Q&A loop), quick (one-shot), list, show. Tier-based model access (individual → Haiku forced; shop/company → Sonnet available via `--model sonnet`). Q&A loop terminates at confidence ≥ 0.7, empty input, or 3-round hard cap. One session row per user-visible interaction; rounds accumulate tokens_used. No new migration — reuses Phase 03 `diagnostic_sessions` table. ~35 tests planned, all AI calls mocked.
