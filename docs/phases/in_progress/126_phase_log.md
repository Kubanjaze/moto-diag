# MotoDiag Phase 126 — Phase Log

**Status:** 🔄 In Progress | **Started:** 2026-04-17 | **Completed:** —
**Repo:** https://github.com/Kubanjaze/moto-diag

---

### 2026-04-17 23:58 — Plan written, v1.0
Diagnostic report export. Extends Phase 123's `diagnose show` with `--format [terminal|txt|json|md]` and `--output PATH`. Three new pure formatters in `cli/diagnose.py` (`_format_session_text/_json/_md`), overwrite confirmation, parent-dir auto-create, UTF-8 + `newline=""` for Windows. JSON includes `"format_version": "1"` for future schema evolution. No new substrate, no migration. Second agent-delegated phase (Builder-A slot).
