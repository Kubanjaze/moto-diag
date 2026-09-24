# Known-bad ROADMAP (hand-written). Every rule of roadmap_check.py must fire on this tree.

| Phase | Title | Status | Notes |
|-------|-------|--------|-------|
| 190 | A Track I row | ✅ | R4: mobile-owned; this ROADMAP must not carry it |
| 256 | The retrieval chokepoint | ✅ | closed |
| 256 | Scooter electrical (12V minimal) | 🔲 | R1: the number is already taken (the real 2026-09-24 case) |
| 257 | The orchestrator | 🔲 | R3: its documents are in completed/, the row was never closed |
| 258 | The next phase | 🔲 | R3: its documents are in in_progress/, the row still says not started |
| 400 | Past every range | 🔲 | R4: no range of ROADMAP_AUTHORITY.md covers it (the real 353 case) |
| 260 | Closed with no handoff | ✅ | **CLOSED 2026-09-25.** R6: docs/handoffs/ has nothing for it |
| 261 | Closed with only a mid-phase handoff | ✅ | **CLOSED 2026-09-25.** R6: 2026-09-25_261_after_batch_1.md is not a close-out handoff |
| 262 | Handoff dated before the close | ✅ | **CLOSED 2026-09-26.** R6: its only handoff, 2026-09-25_262_closed.md, predates the close |
| 263 | The day's second close | ✅ | **CLOSED 2026-09-26.** R6: 264's handoff carries the same date, so a date-only rule passes it (the real 2026-09-24: four closes, two handoffs) |
| 264 | The day's first close | ✅ | **CLOSED 2026-09-26.** Has 2026-09-26_264_closed.md; must not be reported |
| 265 | Closed without the date in its row | ✅ | R6: implementation.md's history row dates the close, and there is no handoff |
