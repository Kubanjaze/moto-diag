"""Phase 378, K22, K23, K24, K26, K27 — the words that rules live in.

K22: the close-out skill's description and verify_phase's check 11 said
"seven artefacts" for two weeks after A8 made eight; README kept a clause
CLAUDE.md removed on 2026-09-27. K23 moved the standing prompt lines into
CLAUDE.md's rule 6 or a check; K24 put the generator rule in the close-out
skill; K26 and K27 are the operator's calls, recorded where they apply.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLOSEOUT = ROOT / ".claude" / "skills" / "closeout"


def _flat(path: pathlib.Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_the_artefact_count_matches_closeout_check():
    import sys
    sys.path.insert(0, str(CLOSEOUT))
    from closeout_check import ASSERTION_IDS

    words = {7: "seven", 8: "eight", 9: "nine"}[len(ASSERTION_IDS)]
    description = re.search(r"^description: (.*)$",
                            (CLOSEOUT / "SKILL.md").read_text(encoding="utf-8"), re.M).group(1)
    assert f"the {words} artefacts" in description
    assert f"(all {words} artefacts)" in (CLOSEOUT / "verify_phase.sh").read_text()


def test_readme_carries_no_removed_clause():
    readme = _flat(ROOT / "README.md")
    assert "is not available until the next one" not in readme
    assert "A skill added part-way through a session does load" in readme


def test_the_generator_rule_is_in_the_close_out_sequence():
    assert ("A script whose output ships in `src/`, or whose output a migration loads, is "
            "committed in the phase folder with it") in _flat(CLOSEOUT / "SKILL.md")


def test_rule_6_holds_the_standing_lines_and_k26():
    claude = _flat(ROOT / "CLAUDE.md")
    rule_6 = claude.split("6. **Standing practice**", 1)[1].split("## Procedure folders", 1)[0]
    for line in ("Run the whole-tree command on its own", "Raise `COLLECTED_TEST_FLOOR`",
                 "File a finding with the `finding` skill before any document cites",
                 "never loosen the guard", "`tests/support/worker_loss.py`",
                 "A builder may install a Homebrew core tool a test needs"):
        assert line in rule_6, line
    assert "## How a phase runs: six standing rules" in claude


def test_k27_is_recorded_where_backups_are_kept():
    skill = _flat(ROOT / ".claude" / "skills" / "deploy" / "SKILL.md")
    assert ("5 now; 5 plus the first backup of each week once the first shop's real data "
            "is in") in skill
