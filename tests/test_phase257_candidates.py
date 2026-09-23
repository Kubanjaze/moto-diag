"""Phase 257 — candidates.py: the library excerpts a source stage may read.

The token-budget redesign's first step. A one-turn, no-tools source stage
is only as cheap as what it is handed and only as honest as where that
came from, so each property is pinned against a hand-written fixture
library (`fixtures/library/`, 255D decision 5): the ±40-line window, the
page, the absolute path, the exclusions, the caps, and that a spelling no
file names gets nothing — which is what lets the orchestrator skip the
model for it.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "source-transmission"
sys.path.insert(0, str(SKILL))

import candidates as C  # noqa: E402

LIB = SKILL / "fixtures" / "library"


def _one(spelling, **kw):
    return C.candidates([spelling], LIB, **kw)[spelling]


class TestTheWindow:
    def test_a_match_is_cut_forty_lines_either_side(self):
        """ZZ Ranger 400 is line 100 of a 200-line file of numbered filler:
        the excerpt is lines 60–140, exactly 81 lines, and nothing else."""
        [e] = _one("Ranger 400")
        lines = e["text"].split("\n")
        assert len(lines) == 81
        assert lines[0] == "filler line 060" and lines[-1] == "filler line 140"
        assert lines[40] == "The ZZ Ranger 400 is built for gravel."
        assert e["lines"] == "60-140" and e["hit_line"] == 100

    def test_the_document_is_the_absolute_library_path(self):
        [e] = _one("Ranger 400")
        assert e["document"] == str(LIB / "zz_ranger_om.pdf.txt")
        assert pathlib.Path(e["document"]).is_absolute()

    def test_letters_and_digits_split_the_same_way_on_both_sides(self):
        """'Trail250' must find 'TRAIL 250'; 'CR300i' must find 'CR 300i'."""
        assert _one("Trail250")

    def test_a_longer_word_is_not_a_match(self):
        """'Glide' is not 'Glider' — the Grom/program trap."""
        docs = {e["document"] for e in _one("Glide")}
        assert str(LIB / "zz_glider300_owners_manual.txt") not in docs


class TestThePage:
    def test_page_from_a_marker(self):
        [e] = _one("Ranger 400")
        assert e["page"] == 1

    def test_page_from_a_form_feed(self):
        """zz_trail_om.txt: cover, then \\f, then the spec page — page 2."""
        [e] = _one("Trail 250")
        assert e["page"] == 2

    def test_page_from_an_angle_marker_in_a_subfolder(self):
        [e] = _one("Glide 125")
        assert e["page"] == 7 and e["document"].endswith("sub/zz_glide_quickref.txt")

    def test_html_has_no_page_and_no_markup(self):
        [e] = _one("Scout 50")
        assert e["page"] is None
        assert "Automatic; V-Matic belt" in e["text"]
        assert "<" not in e["text"] and "color:red" not in e["text"]


class TestAFileNamedForTheMachine:
    def test_its_gearbox_lines_are_anchors_too(self):
        """The gear-change page of zz_glider300_owners_manual.txt never
        names the machine; the file's own name does."""
        ex = _one("Glider 300")
        by_file = [e for e in ex if e["anchor"] == "file"]
        assert any("Always use the clutch when changing gear." in e["text"] for e in by_file)
        assert any(e["page"] == 9 for e in by_file)


class TestWhatIsNeverRead:
    def test_nothing_names_it_so_nothing_is_returned(self):
        assert C.candidates(["Nowhere 999"], LIB) == {"Nowhere 999": []}

    @pytest.mark.parametrize("name", ["refute/notes.txt", "257_research_raw.txt",
                                      "kymco_crawl_log.txt", "zz_ranger.json"])
    def test_the_projects_own_artefacts_are_not_library(self, name):
        """Each of these names ZZ Ranger 400 and a gearbox: past refute
        output, a phase note, a crawl log, an unsupported type."""
        assert (LIB / name).is_file()
        assert all(e["document"] != str(LIB / name) for e in _one("Ranger 400"))

    def test_a_database_dump_is_not_library(self, monkeypatch):
        monkeypatch.setattr(C, "MAX_BYTES", 100)
        assert _one("Trail 250") == []


class TestTheCaps:
    def test_excerpts_per_spelling(self, monkeypatch):
        monkeypatch.setattr(C, "MAX_EXCERPTS", 1)
        assert len(_one("Glider 300")) == 1

    def test_characters_per_spelling(self, monkeypatch):
        uncapped = _one("Glider 300")
        monkeypatch.setattr(C, "MAX_CHARS", 1000)
        ex = _one("Glider 300")
        assert ex and len(ex) < len(uncapped)
        assert sum(len(e["text"]) for e in ex) <= 1000
