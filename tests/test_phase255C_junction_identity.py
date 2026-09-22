"""Phase 255C — one canonical identity per machine, and a positive gate on extraction.

Two classes, and they are closed by different things:

* **Spelling-split** — one machine under several junction strings, each
  reachable only from the spelling that produced it. Closed by the pair form
  and by the two guards in `TestOneCanonicalPerMachine`.
* **Debris** — strings in the junction that are not model names at all.
  **The spelling guards cannot close this**, and the reason is worth stating
  because it was nearly built that way: 244I derives `model_vocabulary` FROM
  the model column, so a debris string that reached the junction is in the
  vocabulary, and the resolver returns it by exact match. Debris defines its
  own canonical. A guard asking "does this resolve to itself" is satisfied by
  construction on exactly the strings it was written for.

  Closed instead by a **positive gate** at extraction, whose negative control
  is the whole corpus rather than a sample.
"""

from __future__ import annotations

import json
import pathlib
import sqlite3

import pytest

from motodiag.knowledge.models import _model_tokens

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestBugFix1ThousandsSeparator:
    """A comma between digits is a thousands separator, not a list delimiter."""

    @pytest.mark.parametrize("value,expected", [
        ("798cc triple — Brutale 800, Dragster RR, Rivale at 12,000 km; "
         "Turismo Veloce, F3 at 30,000 km",
         ["798cc triple", "Brutale 800", "Dragster RR", "Rivale at 12,000 km",
          "Turismo Veloce", "F3 at 30,000 km"]),
        ("Multistrada V4, Diavel V4 (V4 Granturismo, 60,000 km); Panigale V4",
         ["Multistrada V4", "60,000 km", "Panigale V4"]),
    ])
    def test_a_figure_is_not_torn_in_half(self, value, expected):
        assert _model_tokens(value) == expected

    def test_no_bare_thousands_fragment_survives(self):
        """'000 km' and the bare numbers it left behind are the defect."""
        toks = _model_tokens("Rivale at 12,000 km; F3 at 30,000 km")
        assert "000 km" not in toks
        assert "12" not in toks and "30" not in toks

    @pytest.mark.parametrize("value,count", [
        ("Agility 50, Agility 125, People S 250", 3),
        ("PCX125, PCX150, PCX160", 3),
        ("Vespa LX 50, Vespa LX 125, Vespa LX 150", 3),
    ])
    def test_positive_control_a_real_comma_list_still_splits(self, value, count):
        """The fix must not stop commas working as delimiters."""
        assert len(_model_tokens(value)) == count
