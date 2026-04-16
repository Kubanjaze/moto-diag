# MotoDiag Phase 10 — Logging + Audit Trail

**Version:** 1.1 | **Tier:** Micro | **Date:** 2026-04-15

## Goal
Add structured logging throughout the application so diagnostic sessions, searches, and data loads leave an audit trail.

CLI: No new command. Logging configurable via MOTODIAG_LOG_LEVEL and MOTODIAG_LOG_FILE settings.

Outputs: `core/logging.py` (setup, get_logger, reset), logging in session_repo, 9 tests

## Logic
1. Created `core/logging.py`: `setup_logging(level, log_file?)`, `get_logger(name)`, `reset_logging()`
2. Console handler (stderr) + optional file handler with structured format
3. Idempotent initialization with `_initialized` flag
4. Added logging to session_repo: create, set_diagnosis, close operations
5. Module-level loggers via `logging.getLogger("motodiag.<module>")`

## Key Concepts
- `logging.getLogger("motodiag")` as root, child loggers inherit level
- Format: `[TIMESTAMP] [LEVEL] [MODULE]: message` with `%Y-%m-%d %H:%M:%S`
- File handler creates parent dirs automatically
- `reset_logging()` for test isolation

## Verification Checklist
- [x] `setup_logging()` returns configured logger
- [x] Log level configurable (DEBUG, INFO, WARNING, ERROR)
- [x] Idempotent — multiple calls don't add duplicate handlers
- [x] File logging writes to specified path
- [x] File handler creates parent directories
- [x] Child loggers inherit parent level
- [x] Session create logs "Session N created"
- [x] Session close logs "Session N closed"
- [x] 9 tests pass in 1.13s

## Risks
- ~~Log noise in tests~~ — mitigated with reset_logging() fixture and caplog

## Results
| Metric | Value |
|--------|-------|
| Functions | 3 (setup_logging, get_logger, reset_logging) |
| Modules with logging | 1 (session_repo — more will be added as needed) |
| Tests | 9 |
| Test time | 1.13s |

Audit trail foundation is in place. Session lifecycle events are now logged with timestamps.
