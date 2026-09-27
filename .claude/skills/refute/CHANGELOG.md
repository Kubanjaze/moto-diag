# refute — changelog

## 2026-09-27 — at most three rounds, held by C5–C7 (Phase 358, K9)

The operator's amended rule is quoted verbatim in SKILL.md. The reason is
that 264 needed 3 rounds and 262 needed 5, because each round's fixes
added claims the next round then found.

- **The checklist gained one column,** `round · kind · outcome`. The
  operator chose this: "extra column — yes".
- **`refute_check.py` gained three checks:**
  - **C5:** every row carries the column, and no round is above 3;
  - **C6:** no factual or citation defect is left open;
  - **C7:** every open wording defect names one and the same F-number.
- **`OLD_FORMAT` exempts the seven checklists written before the column**
  (257, 260, 261, 262, 264, 353, 354). `tests/test_phase358_refute_rounds.py`
  checks that this list equals every closed log with a block.
- **The CLI applies the exemption by the log's file name.** Close-out's A8
  applies it by the phase.
- **Held as text only:** "delete rather than rewrite" and "rounds 2+ read
  the diff and its neighbours". SKILL.md says no check can see them.
- **Fixtures:**
  - `good_log.md` has the fifth column;
  - `old_format_log.md` keeps the four-column shape;
  - `bad_rounds_log.md` plants one case for each of C5, C6 and C7.

## 2026-09-22 — created (Phase 255D)

Third and last folder of the phase, sequenced last because it is the one
that **cannot have a runtime assertion over its actual work.**

The scope rules are not invented here; each is a failure this project
already paid for — a row killed on a manual never opened, a machine kept on
a single hit in a boilerplate fault table, 263 file paths counted as 263
documents when they were 172, and a split that separated a claim from the
quote contradicting it.

**The checklist was sharpened after review.** The first design asked only
for claims examined / killed / citations fetched — counts. The operator's
amendment requires, **per claim kept or killed, the verbatim quote and the
document plus page it rests on**, so that a human can spot-check any row
against the PDF in one step.

**The ceiling is recorded in the skill itself**, not buried here: this
checks the report, not the work. A complete block is consistent with a lazy
pass. What the quote and page buy is cheap falsification — one step from row
to source — and that is the entire claim being made for it.
