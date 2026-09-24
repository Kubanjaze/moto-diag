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
        # A spelling absent from the junction, so no batch can ever source
        # it (it was the CBR1000RR, then the CBR929RR; each broke when sourced).
        r = resolve_transmission("Honda", "ZZ-0 unlisted")
        assert r.provenance == "unknown", (
            "the example machine has been sourced: pick another spelling absent from the junction")
        assert r.provenance == "unknown"
        assert r.candidates != frozenset({"manual"})


class TestSuzukiWrite:
    """Run Suzuki_20260923_093052: Suzuki's own current spec pages, fetched
    by acquire.py; nine spellings kept by refute and named on their pages.
    Each spelling written down, not counted."""

    import pytest as _pytest

    @_pytest.mark.parametrize("model", [
        "V-Strom 650", "vstrom650", "DR-Z400S", "drz400s", "Boulevard C50",
    ])
    def test_resolves_manual(self, model):
        r = resolve_transmission("Suzuki", model)
        assert r.provenance == "model-sourced", model
        assert r.candidates == frozenset({"manual"}), model

    @_pytest.mark.parametrize("model", ["SV650 Gladius", "GSX-R1100", "GSX-S750", "DR-Z400SM",
                                        "GSX-R750", "GSX-R1000", "GSX-R600", "GSX-S1000",
                                        "Boulevard M109R", "V-Strom 1050"])
    def test_what_the_run_did_not_prove_stays_unknown(self, model):
        """SV650 Gladius: a different machine (2009–15). GSX-R1100: no
        current page. GSX-S750, DR-Z400SM: named in passing. The six after:
        written in 9a02aa0, reverted under E12 — their pages show no
        rider-operated clutch or foot-shift pattern."""
        assert resolve_transmission("Suzuki", model).provenance == "unknown", model

    def test_the_make_is_the_scope(self):
        assert resolve_transmission("Kawasaki", "GSX-R750").provenance == "unknown"


class TestKawasakiWrite:
    """Run Kawasaki_20260923_100438: ten spellings, eight machines, each
    quoting its page's spec row with 'return shift' or a manual clutch.
    Ninja H2, Z900, Ninja 300 from the ABS edition's page (the one named
    exception)."""

    import pytest as _pytest

    @_pytest.mark.parametrize("model", [
        "ZX-10R", "Ninja ZX-10R", "ZX-6R", "Ninja ZX-6R", "Ninja H2", "KLR650", "KLR 650",
        "Z900", "Ninja 300", "KLX300", "Z650",
    ])
    def test_resolves_manual(self, model):
        r = resolve_transmission("Kawasaki", model)
        assert r.provenance == "model-sourced", model
        assert r.candidates == frozenset({"manual"}), model

    @_pytest.mark.parametrize("model", ["Ninja 650", "ZX-14R", "Ninja H2 SX", "Z H2", "Versys 650",
                                        "Vulcan 900", "ZX-10RR", "Z900RS", "KLX300SM"])
    def test_what_the_run_did_not_prove_stays_unknown(self, model):
        """Ninja 650: refute killed its gear-count-only quote. The rest:
        no qualifying page, or a different machine."""
        assert resolve_transmission("Kawasaki", model).provenance == "unknown", model

    def test_the_abs_entries_say_where_they_came_from(self):
        for model in ("Ninja H2", "Z900", "Ninja 300"):
            assert "ABS edition" in resolve_transmission("Kawasaki", model).entry.source, model


class TestEveryPhase257ManualEntryMeetsE12:
    """Operator decision 2026-09-23: every entry this phase wrote as manual
    carries, in its own source string, a quote that names a rider-operated
    clutch, a foot-shift pattern or the word "manual" (entry_check E12).
    A guard on the lookup itself: a later edit that swaps in a gear-count
    quote fails here."""

    import pytest as _pytest

    PHASE_257 = [("SYM", "Wolf 150"), ("SYM", "Wolf CR300i"), ("Kymco", "K-Pipe"), ("Honda", "Grom 125"),
                 ("Suzuki", "SV650"), ("Suzuki", "V-Strom 650"),
                 ("BMW", "K 1200 GT"), ("BMW", "K 1200 RS"), ("BMW", "R 1200 GS"), ("BMW", "S 1000 R"),
                 ("BMW", "K 1600 GT"), ("BMW", "K 1300 S"), ("BMW", "K 1200 S"),
                 ("Honda", "CBR600RR"), ("Honda", "CBR1000RR"), ("Honda", "CB500F"), ("Honda", "XR650L"),
                 ("Honda", "CRF250L"), ("Suzuki", "DR-Z400S"), ("Suzuki", "Boulevard C50"),
                 ("Kawasaki", "Ninja ZX-10R"), ("Kawasaki", "Ninja ZX-6R"), ("Kawasaki", "Ninja H2"),
                 ("Kawasaki", "KLR650"), ("Kawasaki", "Z900"), ("Kawasaki", "Ninja 300"),
                 ("Kawasaki", "KLX300"), ("Kawasaki", "Z650"),
                 ("Yamaha", "YZF-R1"), ("Yamaha", "YZF600R"), ("Yamaha", "SR400"), ("Yamaha", "WR250R"),
                 ("Yamaha", "XT250"), ("Yamaha", "Bolt"), ("Yamaha", "V-Star 1300"), ("Yamaha", "V-Star 250"),
                 ("Yamaha", "FZ6"), ("Yamaha", "FZ8"), ("Yamaha", "MT-10"), ("Yamaha", "Tenere 700"),
                 *[("KTM", m) for m in ("125 Duke", "390 Duke", "690 Duke", "790 Duke", "890 Duke",
                                        "1290 Super Duke R", "RC 390", "1190 RC8", "390 Adventure",
                                        "390 Adventure R", "790 Adventure", "790 Adventure R", "890 Adventure",
                                        "890 Adventure R", "890 Adventure R Rally", "1090 Adventure R",
                                        "1190 Adventure", "1290 Super Adventure", "1290 Super Adventure R",
                                        "690 Enduro", "690 SMC", "950 Super Enduro R", "250 EXC TPI", "300 EXC",
                                        "500 EXC-F", "450 SX-F")]]

    @_pytest.mark.parametrize("make,canonical", PHASE_257)
    def test_its_quote_names_the_mechanism(self, make, canonical):
        import re
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".claude" / "skills" / "source-transmission"))
        from entry_check import manual_evidence
        from motodiag.knowledge.transmission import TRANSMISSION_LOOKUP
        [e] = [e for e in TRANSMISSION_LOOKUP if e.make == make and e.canonical == canonical]
        # A quote opens after whitespace, '(' or the start, and closes on a
        # "'" not followed by a letter — so "rider's" and "Suzuki's" are not
        # quote marks (they were, and the commentary "a rider's clutch lever"
        # passed as a quote).
        quoted = re.findall(r"(?:(?<=\s)|(?<=\()|^)'(.{8,}?)'(?![A-Za-z])", e.source.replace("’", "'"))
        assert any(manual_evidence(q) for q in quoted), (canonical, quoted)


class TestTheSourceRouteIsAField:
    """Which route sourced an entry is a structured field, so the fallback's
    entries can be selected mechanically and re-run once Subconscious is back."""

    def test_the_subconscious_entries_say_so(self):
        from motodiag.knowledge.transmission import TRANSMISSION_LOOKUP
        subc = {(e.make, e.canonical) for e in TRANSMISSION_LOOKUP if e.source_route == "subconscious/glm-5.3-marathon@default"}
        assert ("Kawasaki", "Ninja ZX-10R") in subc and ("SYM", "Wolf CR300i") in subc and len(subc) == 14

    def test_older_entries_carry_no_route(self):
        from motodiag.knowledge.transmission import TRANSMISSION_LOOKUP
        [pcx] = [e for e in TRANSMISSION_LOOKUP if e.make == "Honda" and e.canonical == "PCX"]
        assert pcx.source_route is None

    def test_the_fallback_is_one_filter(self):
        from motodiag.knowledge.transmission import TRANSMISSION_LOOKUP
        fallback = [e for e in TRANSMISSION_LOOKUP if e.source_route and not e.source_route.startswith("subconscious/")]
        assert {e.source_route for e in fallback} <= {"claude-opus-5-5@medium", "claude-sonnet-5@default"}


class TestSV650Write:
    """Live vehicle #8, a 2019 SV650. Run Suzuki_20260923_123652: the source
    stage on the fallback route (claude-sonnet-5), refute on Opus; from the
    2026 SV650 ABS page under the ABS exception; the quote is its clutch
    pull (E12, widened)."""

    import pytest as _pytest

    @_pytest.mark.parametrize("model", ["SV650", "SV 650", "SV650 ABS"])
    def test_resolves_manual(self, model):
        r = resolve_transmission("Suzuki", model)
        assert r.provenance == "model-sourced" and r.candidates == frozenset({"manual"}), model

    def test_it_records_its_route_and_edition(self):
        e = resolve_transmission("Suzuki", "SV650").entry
        assert e.source_route in ("claude-sonnet-5@default", "claude-opus-5-5@medium") and "ABS edition" in e.source

    def test_the_gladius_is_another_machine(self):
        assert resolve_transmission("Suzuki", "SV650 Gladius").provenance == "unknown"


class TestBMWWrite:
    """Run BMW_20260923_142134 on the fallback source route
    (claude-opus-5-5@medium): four rider's manuals whose title pages name
    the model, each quote naming the clutch lever or 'Manual transmission'."""

    import pytest as _pytest

    @_pytest.mark.parametrize("model", ["K1200GT", "K 1200 GT", "K1200RS", "R1200GS", "R 1200 GS", "S 1000 R", "S1000R",
                                        "K1600GT", "K 1600 GT", "K1300S", "K 1300 S", "K1200S", "K 1200 S"])
    def test_resolves_manual(self, model):
        r = resolve_transmission("BMW", model)
        assert r.provenance == "model-sourced" and r.candidates == frozenset({"manual"}), model
        assert r.entry.source_route == "claude-opus-5-5@medium"

    @_pytest.mark.parametrize("model", ["R1200", "F650", "F900", "S1000", "R1150", "R1100", "R1200GS LC",
                                        "S 1000 XR", "F800GS", "K1600GTL", "K1600", "K1300", "K1300R",
                                        "K1200", "K1200R", "K1200S/R"])
    def test_what_the_run_did_not_prove_stays_unknown(self, model):
        """Family evidence (R1200, F650, F900, S1000); E12 rejections (R1150,
        R1100); no evidence (F800GS, S 1000 XR); a different spelling (R1200GS
        LC); and the siblings of the three re-sourced in BMW_20260923_154333
        (K1600GTL, K1300R, K1200R, the families K1600/K1300/K1200, and the
        census's "K1200S/R" slash-list, which names two machines)."""
        assert resolve_transmission("BMW", model).provenance == "unknown", model


class TestHondaMotopubWrite:
    """Run Honda_20260923_155534 on the fallback source route
    (claude-opus-5-5@medium): American Honda's 2018 owner's manuals from
    motopub, each quoting the side-stand check's 'pull the clutch lever in'."""

    import pytest as _pytest

    @_pytest.mark.parametrize("model", ["CBR600RR", "CBR 600RR", "CBR1000RR", "CB500F", "XR650L", "CRF250L"])
    def test_resolves_manual(self, model):
        r = resolve_transmission("Honda", model)
        assert r.provenance == "model-sourced" and r.candidates == frozenset({"manual"}), model
        assert r.entry.source_route == "claude-opus-5-5@medium"

    @_pytest.mark.parametrize("model", ["CBR1000RR-R", "CBR1000RR SP", "CBR600F", "CBR600F4i", "CBR929RR",
                                        "CB500X", "CBR500R", "XR650R", "CRF250R", "CRF250 Rally",
                                        "CB650R", "CB750"])
    def test_what_the_run_did_not_prove_stays_unknown(self, model):
        """Siblings and variants of the five; the E-Clutch-flagged CB650R and
        CB750 (no_evidence, not classified)."""
        assert resolve_transmission("Honda", model).provenance == "unknown", model

    @_pytest.mark.parametrize("model", ["NCW50", "NCW 50", "Honda NCW50"])
    def test_ncw50_resolves_cvt_through_the_metropolitan_entry(self, model):
        """Operator decision 2026-09-23: NCW50 is the Metropolitan's model
        code — its 2018 manual 31GJB620 is the same 31GJB6x0 series the entry
        cites, with the same V-matic line. An alias on that entry, not a new one."""
        r = resolve_transmission("Honda", model)
        assert r.provenance == "model-sourced" and r.candidates == frozenset({"cvt"}), model
        assert r.entry.canonical == "Metropolitan"
        assert "31GJB620" in r.entry.source


class TestYamahaOwnersManualWrite:
    """Run Yamaha_20260923_194048 on the fallback source route
    (claude-opus-5-5@medium): Yamaha's owner's manuals from its Owner's
    Manual Library, each model line the maker's pinned model_list record.
    14 ready, all kept with names_model true; Tenere 700 added by the re-run
    after bug fix #6 (Yamaha_20260923_210233)."""

    import pytest as _pytest

    MANUAL = ["YZF-R1", "YZF600R", "SR400", "WR250R", "XT250", "Bolt", "V-Star 1300", "V-Star 250",
              "FZ6", "FZ8", "MT-10",
              "Tenere 700", "Ténéré 700", "XTZ690"]   # run Yamaha_20260923_210233, after bug fix #6
    CVT = ["Vino 50", "Vino 125", "Vino Classic"]

    @_pytest.mark.parametrize("model", MANUAL + ["XVS950CU", "XVS1300A", "XV250", "YZF1000", "MTN1000"])
    def test_resolves_manual(self, model):
        r = resolve_transmission("Yamaha", model)
        assert r.provenance == "model-sourced" and r.candidates == frozenset({"manual"}), model
        assert r.entry.source_route == "claude-opus-5-5@medium"

    @_pytest.mark.parametrize("model", CVT + ["YJ125Y"])
    def test_resolves_cvt(self, model):
        r = resolve_transmission("Yamaha", model)
        assert r.provenance == "model-sourced" and r.candidates == frozenset({"cvt"}), model

    def test_yj125y_is_the_vino_125_through_its_list_record(self):
        """The manual prints only 'YJ125Y'; the maker's record pairs it with VINO 125."""
        e = resolve_transmission("Yamaha", "YJ125Y").entry
        assert e.canonical == "Vino 125" and "'VINO 125 - YJ125Y'" in e.source

    @_pytest.mark.parametrize("model", ["MT-09", "MT-07"])
    def test_held_for_y_amt_stays_unknown(self, model):
        """Operator, 2026-09-23: held from the write pending what Yamaha's own
        pages say about a Y-AMT version (and E4 withheld both in this run)."""
        assert resolve_transmission("Yamaha", model).provenance == "unknown", model

    @_pytest.mark.parametrize("model", ["YZF-R6", "YZF-R7", "MT-03",   # E4: their manuals print only YZFR6L, YZFR7T, MT03T
                                        "Tenere 700 Rally", "Tenere 700 World Raid",
                                        "XC50", "XC50A", "YZF-R1M", "MT-10 SP", "Vino", "Zuma", "V-Star 650"])
    def test_what_the_run_did_not_prove_stays_unknown(self, model):
        """E4's three; Tenere 700's variants; XC50, the code of both the Vino 50 and the Vino Classic
        (so on neither); variants, and the weak spellings no route matched."""
        assert resolve_transmission("Yamaha", model).provenance == "unknown", model


class TestKTMOwnersManualWrite:
    """Run KTM_20260923_215704 on the fallback source route
    (claude-opus-5-5@medium): KTM's owner's manuals from ktm.com's manual
    list, each the newest year's US English edition or, with no US row, the
    first English one. 26 sent, 26 kept with names_model true, 0 withheld.
    No manual names an AMT (phase log, "KTM: no AMT in its manuals")."""

    import pytest as _pytest

    MANUAL = ["125 Duke", "390 Duke", "690 Duke", "790 Duke", "890 Duke", "1290 Super Duke R", "RC 390",
              "1190 RC8", "390 Adventure", "390 Adventure R", "790 Adventure", "790 Adventure R", "890 Adventure",
              "890 Adventure R", "890 Adventure R Rally", "1090 Adventure R", "1190 Adventure",
              "1290 Super Adventure", "1290 Super Adventure R", "690 Enduro", "690 SMC", "950 Super Enduro R",
              "250 EXC TPI", "300 EXC", "500 EXC-F", "450 SX-F"]

    @_pytest.mark.parametrize("model", MANUAL + ["KTM 390 Duke", "450 SX F", "500 exc-f"])
    def test_resolves_manual(self, model):
        r = resolve_transmission("KTM", model)
        assert r.provenance == "model-sourced" and r.candidates == frozenset({"manual"}), model
        assert r.entry.source_route == "claude-opus-5-5@medium" and "ktm.com's manual list" in r.entry.source

    @_pytest.mark.parametrize("model", ["1290 Super Duke", "Super Adventure S",     # contains matches, not fetched (4609)
                                        "EXC", "Enduro R",                         # no manual of their own; not sent
                                        "Adventure", "Adventure R", "LC8", "GT", "350 SXF", "690 Duke 4",
                                        "1290 Super Duke GT", "390 Duke R2R", "1390 Super Adventure S EVO",
                                        "690 Enduro R", "1190 RC8 R"])
    def test_what_the_run_did_not_prove_stays_unknown(self, model):
        """The two 'contains' matches; the two held from the send; the spellings
        KTM's list does not name; siblings and variants of what was written,
        including the AMT-equipped 1390 Super Adventure S EVO."""
        assert resolve_transmission("KTM", model).provenance == "unknown", model

    def test_the_make_is_exactly_the_run(self):
        from motodiag.knowledge.transmission import TRANSMISSION_LOOKUP
        assert sorted(e.canonical for e in TRANSMISSION_LOOKUP if e.make == "KTM") == sorted(self.MANUAL)
