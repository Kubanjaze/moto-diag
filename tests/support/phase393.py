"""Phase 393: the Red Team's code checklist, as a stand-in answer gives it.

Every stand-in Red Team reply since 393 carries `code_checklist`, as the
schema requires: `ALL_YES` answers the five questions with no defect.
"""

ALL_YES = [{"question": q, "answer": "yes", "where": "src/motodiag/core/config.py:1",
            "why": "nothing in the diff bears on it"} for q in (1, 2, 3, 4, 5)]
