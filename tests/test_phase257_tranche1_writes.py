"""Phase 257 — the tranche-1 writes: every spelling a batch proved, resolves.

Each make's batch ends in a write to `TRANSMISSION_LOOKUP`, one make per
commit. This file is the test that the write actually happened: for every
spelling the run reported `ready_to_write`, the resolver must now answer
`model-sourced` with the mechanism the maker's document stated — where an
hour earlier the same query answered `unknown` and withheld every scoped
row.

The spellings are written down one by one, not counted, for the reason the
census exists: a number that summarises spellings cannot fail when one of
them is missing. Delete `wolf series` from the lookup and one test below
goes red on its own; nothing here sums to a total that could absorb it.

Each class cites its run directory (`~/.cache/motodiag/source-runs/…`) —
the `summary.json` there is the batch's own account of what it proved, and
the verdict that mattered was refute's, not the source stage's.
"""

from __future__ import annotations

from motodiag.knowledge.transmission import resolve_transmission


class TestSYMWrite:
    """Run SYM_20260922_232240: two spellings, both refute verdicts kept."""

    def test_wolf_classic_150_resolves_manual(self):
        """The alias on the Wolf 150 entry — same manual, spec page headed
        'Model Classic 150'."""
        r = resolve_transmission("SYM", "Wolf Classic 150")
        assert r.provenance == "model-sourced"
        assert r.candidates == frozenset({"manual"})

    def test_every_new_wolf_150_alias_resolves(self):
        """Every spelling the run recorded for the Classic 150 machine."""
        for model in ("wolf classic 150", "wolfclassic150",
                      "wolf classic", "wolf series"):
            r = resolve_transmission("SYM", model)
            assert r.provenance == "model-sourced", model
            assert r.candidates == frozenset({"manual"}), model

    def test_wolf_cr300i_resolves_manual(self):
        """The new entry — owner's manual page 12, six shift tables."""
        r = resolve_transmission("SYM", "Wolf CR300i")
        assert r.provenance == "model-sourced"
        assert r.candidates == frozenset({"manual"})

    def test_every_wolf_cr300i_alias_resolves(self):
        for model in ("WOLF CR 300i", "wolfcr300i", "cr300i", "CR 300i",
                      "PF30A3-EU"):
            r = resolve_transmission("SYM", model)
            assert r.provenance == "model-sourced", model
            assert r.candidates == frozenset({"manual"}), model

    def test_the_bare_wolf_alias_still_lands_on_the_150(self):
        """The pre-existing alias is unmoved: still the Wolf 150 entry."""
        r = resolve_transmission("SYM", "wolf")
        assert r.provenance == "model-sourced"
        assert r.candidates == frozenset({"manual"})

    def test_a_wolf_spelling_that_was_never_seen_stays_unknown(self):
        """The write must not leak: an unlisted Wolf spelling resolves
        unknown, all six candidates — the fail-closed policy is not
        suspended for the make we just touched."""
        r = resolve_transmission("SYM", "Wolf TX")
        assert r.provenance == "unknown"
        assert r.candidates != frozenset({"manual"})
