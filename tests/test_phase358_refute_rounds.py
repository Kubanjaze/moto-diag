"""Phase 358, K9 — at most three refute rounds, held by refute_check C5–C7.

The operator, amended: "max 3 refute rounds. after round 3, remaining
wording defects go to one finding; remaining factual or citation defects
mean the row doesn't ship. fixes delete a sentence rather than rewrite it
where possible. rounds 2+ refute the diff plus its surrounding sentences,
not the whole row."

The first three sentences are checked here, over the checklist's fifth
column `round · kind · outcome`. The last two are judgement and are stated
in SKILL.md as text; nothing here claims to hold them.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "refute"
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "closeout"))

import refute_check as R  # noqa: E402

FIX = SKILL / "fixtures"


def _read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def _block(*cells: str) -> str:
    rows = "\n".join(f"| claim {i} | kept | \"q\" | manual p. {i} | {c} |"
                     for i, c in enumerate(cells, 1))
    return ("## Refuter pass\n\n| claim | verdict | quote | source | round · kind · outcome |\n"
            "|---|---|---|---|---|\n" + rows + "\n")


class TestTheRoundRule:
    @pytest.fixture(scope="class")
    def fails(self):
        return R.check(_read("bad_rounds_log.md"))

    @pytest.mark.parametrize("aid,needle", [
        ("C5", "round 4; at most 3"),
        ("C5", "that parses"),
        ("C6", "open factual defect"),
        ("C7", "no finding"),
        ("C7", "ONE finding"),
    ])
    def test_each_planted_defect_is_named(self, fails, aid, needle):
        assert any(f.startswith(aid) and needle in f for f in fails), fails

    def test_the_good_log_passes(self):
        assert R.check(_read("good_log.md")) == []

    @pytest.mark.parametrize("cell", ["3 · factual · fixed", "3 · citation · deleted",
                                      "1 · none · kept", "2 / wording / fixed"])
    def test_a_defect_closed_by_round_3_ships(self, cell):
        assert R.check(_block(cell)) == []

    def test_an_open_citation_defect_does_not_ship(self):
        assert any(f.startswith("C6") for f in R.check(_block("2 · citation · open")))

    def test_one_finding_for_all_open_wording_is_enough(self):
        assert R.check(_block("3 · wording · open F163", "3 · wording · open F163")) == []


class TestTheOldFormat:
    def test_an_old_checklist_passes_only_under_its_exemption(self):
        text = _read("old_format_log.md")
        assert R.check(text, require_rounds=False) == []
        assert any(f.startswith("C5") for f in R.check(text))

    def test_the_exemption_is_exactly_the_checklists_written_before_358(self):
        """The control: every closed log with a checklist, and none has the
        fifth column. If a new close lacks it, it is not on this list and
        fails."""
        done = ROOT / "docs" / "phases" / "completed"
        with_block = {p.name.split("_")[0] for p in done.glob("*_phase_log.md")
                      if "## Refuter pass" in p.read_text(encoding="utf-8")}
        assert with_block == R.OLD_FORMAT
        for phase in R.OLD_FORMAT:
            text = (done / f"{phase}_phase_log.md").read_text(encoding="utf-8")
            assert R.check(text, require_rounds=False) == [], phase

    def test_the_cli_applies_the_exemption_by_the_log_name(self, tmp_path, monkeypatch):
        """verify_phase check 12 calls the CLI with the log's path."""
        for name, code in (("257_phase_log.md", 0), ("999_phase_log.md", 1)):
            p = tmp_path / name
            p.write_text(_read("old_format_log.md"))
            monkeypatch.setattr(sys, "argv", ["refute_check.py", str(p)])
            assert R.main() == code, name


class TestTheCloseOutUsesIt:
    def test_a8_holds_a_new_close_to_the_round_column(self):
        import closeout_check as C
        old = _read("old_format_log.md")
        assert C.refute_record(old, "257") == []
        assert any("C5" in f for f in C.refute_record(old, "999"))


class TestTheSkillSaysWhatNoCheckCanSee:
    def test_the_text_only_parts_are_stated_as_text(self):
        txt = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        assert "max 3 refute rounds" in txt
        assert "no check" in txt.lower()
