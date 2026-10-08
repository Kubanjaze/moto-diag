"""Phase 379, F131, F154 and F155 — the transmission lookup and symptom relevance.

* **F131.** Six lookup entries had a canonical name that resolved to no
  entry, one of them Honda's own name for a machine ("CT125 Hunter Cub").
  Resolution now matches an entry's canonical name too, and every entry's
  canonical name must resolve to that entry.
* **F154.** "Fiddle 50", the corpus's own spelling, resolved `unknown`. It is
  now its own entry, cited to the SYM Fiddle 50 service manual's cover and
  specification table.
* **F155.** `relevance_tokens` makes plurals singular, so "scooter" meets
  "scooters". Its wider effect (51 of 132 measured prompts changed, about 19
  swaps better and 5 worse) is recorded in the phase log and filed as F200.

Gate 14 (`tests/test_phase258_gate14.py`) holds the end-to-end pins.
"""

from __future__ import annotations

import pytest

from motodiag.knowledge.prompt_rows import relevance_score, relevance_tokens
from motodiag.knowledge.transmission import (
    TRANSMISSION_LOOKUP, _alias_match, resolve_transmission,
)


class TestEveryCanonicalNameResolvesToItsEntry:
    def test_every_entry(self):
        wrong = [(e.make, e.canonical) for e in TRANSMISSION_LOOKUP
                 if resolve_transmission(e.make, e.canonical).entry is not e]
        assert wrong == []

    def test_the_control_the_six_the_aliases_alone_miss(self):
        """Without the canonical name in the match, exactly F131's six fail:
        the guard above would see them."""
        missed = {(e.make, e.canonical) for e in TRANSMISSION_LOOKUP
                  if not _alias_match(e.make, e.canonical, e.aliases)}
        assert missed == {("Honda", "SH125i/SH150i"), ("Honda", "CT125 Hunter Cub"),
                          ("Yamaha", "XC155 / SMAX"), ("SYM", "Jet 50/100"),
                          ("Vespa", "LX 125/150"), ("Vespa", "GTS 300/310")}

    def test_the_name_a_rider_types(self):
        r = resolve_transmission("Honda", "CT125 Hunter Cub")
        assert r.provenance == "model-sourced"
        assert r.entry.canonical == "CT125 Hunter Cub"


class TestTheFiddle50:
    @pytest.mark.parametrize("model", ["Fiddle 50", "fiddle50", "SYM Fiddle 50"])
    def test_it_resolves_cvt_from_its_own_book(self, model):
        r = resolve_transmission("SYM", model)
        assert r.provenance == "model-sourced"
        assert sorted(r.candidates) == ["cvt"]
        assert r.entry.canonical == "Fiddle 50"
        assert "Transmission C.V.T." in r.entry.source

    def test_the_fiddle_iii_keeps_its_own_entry(self):
        for model in ("Fiddle", "Fiddle III", "Fiddle 3"):
            assert resolve_transmission("SYM", model).entry.canonical == "Fiddle III"


class TestPluralsMadeSingular:
    @pytest.mark.parametrize("plural, singular", [
        ("scooters", "scooter"), ("brakes", "brake"), ("batteries", "battery"),
        ("bushes", "bush"), ("switches", "switch"), ("boxes", "box"),
        ("glasses", "glass")])
    def test_the_rule(self, plural, singular):
        assert relevance_tokens(plural) == {singular}

    @pytest.mark.parametrize("word", ["pass", "status", "chassis", "pads", "gas"])
    def test_what_it_leaves(self, word):
        assert relevance_tokens(word) <= {word}

    def test_the_lx_50_row_meets_a_belt_symptom(self):
        """F155's case: the LX 50's tier-0 row is titled "…carburetted
        scooters…", and the symptom says "scooter". It scored 0."""
        row = {"title": "Vespa's small carburetted scooters: Dell'Orto on the two-stroke 50s"}
        wanted = relevance_tokens("scooter jerks at low speed, belt squeal, won't pull away")
        assert relevance_score(row, wanted) == 1
