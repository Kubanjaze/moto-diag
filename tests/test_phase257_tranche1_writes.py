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


class TestKymcoWrite:
    """Run Kymco_20260922_232607: one spelling, refute verdict kept.

    The manual is a scanned PDF, so the verdict rests on refute's own
    render of the spec page, not the OCR layer.
    """

    def test_k_pipe_resolves_manual(self):
        r = resolve_transmission("Kymco", "K-Pipe")
        assert r.provenance == "model-sourced"
        assert r.candidates == frozenset({"manual"})

    def test_every_k_pipe_alias_resolves(self):
        for model in ("K-PIPE", "K-PIPE 125", "K-Pipe 125", "KPIPE",
                      "KPipe 125", "KPIPE125", "T300-KB25KA-A"):
            r = resolve_transmission("Kymco", model)
            assert r.provenance == "model-sourced", model
            assert r.candidates == frozenset({"manual"}), model

    def test_a_kymco_spelling_that_was_never_seen_stays_unknown(self):
        r = resolve_transmission("Kymco", "X-Town")
        assert r.provenance == "unknown"
        assert r.candidates != frozenset({"manual"})


class TestHondaWrite:
    """Run Honda_20260922_233404: two spellings, both refute verdicts kept.

    The plan expected the service manual's page images to carry the Grom
    (its text layer is OCR). The batch found a better source — Honda's own
    digital spec pages — and the OCR corroborates without being the
    citation. The 255 over-reach test still holds: a `{manual}` Grom
    receives no CVT-declared row, it just stops being all-six-unknown.
    """

    def test_grom_and_grom_125_resolve_manual(self):
        for model in ("Grom", "Grom 125"):
            r = resolve_transmission("Honda", model)
            assert r.provenance == "model-sourced", model
            assert r.candidates == frozenset({"manual"}), model

    def test_every_grom_alias_resolves(self):
        for model in ("Grom ABS", "Grom SP", "Grom (MSX125S)",
                      "Grom ABS (MSX125AS)", "Grom SP (MSX125SS)",
                      "MSX125", "MSX 125", "MSX125S", "MSX125AS", "MSX125SS"):
            r = resolve_transmission("Honda", model)
            assert r.provenance == "model-sourced", model
            assert r.candidates == frozenset({"manual"}), model

    def test_the_grom_still_receives_no_cvt_row(self):
        """The 254 over-reach, restated at the resolver: candidates are
        {manual}, so a cvt-only row is withheld — the fix is not undone
        by classifying the machine."""
        r = resolve_transmission("Honda", "Grom")
        assert "cvt" not in r.candidates

    def test_a_honda_spelling_that_was_never_seen_stays_unknown(self):
        r = resolve_transmission("Honda", "CBR1000RR")
        assert r.provenance == "unknown"
        assert r.candidates != frozenset({"manual"})
