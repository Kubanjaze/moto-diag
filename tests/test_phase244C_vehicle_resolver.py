"""Phase 244C — vehicle identity resolution.

The defect: a user typed "Homda cbrf4i" into a real session and every
knowledge-base lookup returned zero rows, while the corpus held entries for the
Honda CBR600F4i. Silently — nothing downstream could tell an unmatched name
from a machine nobody has documented.

The guards below are weighted toward the NEGATIVE cases, because the dangerous
failure here is not missing a match. It is inventing one: resolving a machine
onto a neighbouring make would attach another bike's documented faults to it,
with a mechanic acting on the result.
"""

import inspect
import sqlite3
import contextlib

import pytest

from motodiag.knowledge import vehicle_resolver as vr
from motodiag.media import analysis_worker as vap_worker
from motodiag.media.vision_types import VehicleContext


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    """A miniature corpus with the shape of the real one, including the
    wildcard model and a same-make near-neighbour."""
    p = tmp_path / "kb.db"
    conn = sqlite3.connect(p)
    # `severity` is part of the real table and the ordering depends on it;
    # a fixture missing it made a malformed query look like an empty corpus.
    conn.execute("CREATE TABLE known_issues (id INTEGER PRIMARY KEY, make TEXT, model TEXT, title TEXT, severity TEXT DEFAULT 'medium')")
    rows = [
        ("Honda", "CBR600F4i", "Fuel injector fouling"),
        ("Honda", "CBR600F4i", "Float bowl seep"),
        ("Honda", "CBR600F", "Carb sync drift"),
        ("Honda", "CBR600RR", "Regulator rectifier"),
        ("Honda", "All", "Cam chain tensioner"),
        ("Honda", "CB", "Fork seal weep"),
        ("Kawasaki", "ZX-10R", "Cam chain guide"),
        ("Harley-Davidson", "Sportster", "Stator connector"),
    ]
    for mk, md, ti in rows:
        # every row ten times over, mirroring the live corpus's duplication
        for _ in range(10):
            conn.execute("INSERT INTO known_issues (make, model, title) VALUES (?,?,?)", (mk, md, ti))
    conn.commit(); conn.close()

    @contextlib.contextmanager
    def _conn(path=None):
        c = sqlite3.connect(p); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()

    monkeypatch.setattr(vr, "get_connection", _conn)
    return str(p)


class TestTheVocabularyComesFromTheCorpus:
    def test_makes_are_read_from_the_data(self, corpus):
        assert set(vr.known_makes(corpus)) == {"Honda", "Kawasaki", "Harley-Davidson"}

    def test_the_wildcard_model_is_never_a_target(self, corpus):
        """Resolving a model TO 'All' would silently widen a specific question
        into a make-wide one."""
        assert vr.WILDCARD_MODEL not in vr.known_models("Honda", corpus)

    def test_no_hardcoded_make_list_in_the_module(self):
        """An alias table drifts the moment a phase adds a make."""
        # Phase 244F moved the derivation into `knowledge/marques.py`; the
        # guard follows the code rather than pinning a module.
        from motodiag.knowledge import marques as _mq
        src = inspect.getsource(vr) + inspect.getsource(_mq)
        assert "SELECT DISTINCT make FROM known_issues" in src
        for marque in ("Yamaha", "Suzuki", "Ducati", "Triumph"):
            assert f'"{marque}"' not in src, f"{marque} hard-coded — vocabulary must come from the corpus"


class TestItFixesWhatIsClear:
    def test_a_typo_in_the_make_resolves(self, corpus):
        r = vr.resolve_vehicle("Homda", db_path=corpus)
        assert r.make.resolved == "Honda" and r.make.applied and r.make.changed

    def test_an_abbreviated_model_resolves(self, corpus):
        """'cbrf4i' is not a misspelling — it is the same name with the
        displacement dropped."""
        r = vr.resolve_vehicle("Honda", "cbrf4i", db_path=corpus)
        assert r.model.resolved == "CBR600F4i"
        assert r.model.method == "abbreviation"

    def test_case_and_punctuation_are_not_differences(self, corpus):
        r = vr.resolve_vehicle("harley davidson", db_path=corpus)
        assert r.make.resolved == "Harley-Davidson" and r.make.method == "exact"

    def test_a_correction_is_reported(self, corpus):
        r = vr.resolve_vehicle("Homda", "cbrf4i", db_path=corpus)
        text = " ".join(r.corrections())
        assert "Homda" in text and "Honda" in text, "the user must be able to see what was changed"


class TestItRefusesWhatIsNotClear:
    """The load-bearing half of the phase."""

    def test_a_make_absent_from_the_corpus_resolves_to_nothing(self, corpus):
        r = vr.resolve_vehicle("Ducati", "Panigale", db_path=corpus)
        assert r.make.resolved is None
        assert r.make.method == "unresolved"
        assert not r.make.applied

    def test_a_wrong_make_model_does_not_match(self, corpus):
        """ZX-10R is a Kawasaki. Under Honda it must find nothing."""
        r = vr.resolve_vehicle("Honda", "zx10r", db_path=corpus)
        assert r.make.resolved == "Honda"
        assert r.model.resolved is None

    def test_an_ambiguous_model_is_suggested_not_applied(self, corpus):
        r = vr.resolve_vehicle("Honda", "cbr600", db_path=corpus)
        assert r.model.method == "ambiguous"
        assert not r.model.applied, "ambiguity is a question for the user, not a decision"
        assert len(r.model.alternatives) > 1
        assert any("did you mean" in s for s in r.suggestions())

    def test_a_very_short_string_cannot_fuzzy_match(self, corpus):
        """difflib on a three-character string scores 0.80 against the
        two-character model "CB" with a 0.40 margin — clearing BOTH the floor
        and the margin. Only the length gate stops "cbz" being silently read as
        a real model.

        The first version of this guard used "Ho", which the floor rejected on
        its own; it passed with the gate removed and proved nothing. Mutation
        testing caught it."""
        r = vr.resolve_vehicle("Honda", "cbz", db_path=corpus)
        assert not r.model.applied, "a 3-character string was accepted as a model name"

    def test_the_margin_rule_is_present_and_nonzero(self):
        """Mutation target: dropping the margin makes every near-tie an
        auto-fix, which is precisely the dangerous behaviour."""
        assert vr.FUZZY_MARGIN > 0
        assert vr.FUZZY_FLOOR >= 0.7
        src = inspect.getsource(vr._resolve_against)
        assert "FUZZY_MARGIN" in src and "FUZZY_FLOOR" in src


class TestEmptyAndUnmatchedAreDifferentFailures:
    def test_an_unresolved_make_returns_no_rows_and_says_so(self, corpus):
        identity, rows = vr.known_issues_for_vehicle("Ducati", "Panigale", db_path=corpus)
        assert rows == []
        assert identity.make.method == "unresolved", (
            "the caller must be able to tell 'nobody could match this' from "
            "'nothing is documented'"
        )

    def test_a_resolved_make_reaches_rows_that_literal_matching_missed(self, corpus):
        _, rows = vr.known_issues_for_vehicle("Homda", "cbrf4i", db_path=corpus)
        assert rows, "this is the bug: literal matching returned zero here"
        titles = {r["title"] for r in rows}
        assert "Fuel injector fouling" in titles

    def test_rows_are_deduplicated(self, corpus):
        """The corpus carries every entry ten times. Twenty rows of two facts
        reads to a model as a narrow corpus rather than a duplicated one."""
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=corpus, limit=25)
        keys = [(r["make"], r["model"], r["title"]) for r in rows]
        assert len(keys) == len(set(keys)), "duplicate rows reached the caller"

    def test_another_makes_issues_never_leak_in(self, corpus):
        """The absolute half of what was one bundled guard.

        Phase 244E widened retrieval so a same-make, different-model entry may
        now be returned — labelled — because 30% of the corpus carries prose in
        its `model` column and an equality filter reaches almost none of it.
        That relaxation must never extend across makes: attaching a Kawasaki
        fault to a Honda puts wrong work in a mechanic's hands.

        This assertion is deliberately duplicated in
        `test_phase244E_retrieval_widening.py`. Splitting a guard is how its
        strict half goes missing, so it now lives in two files."""
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=corpus, limit=25)
        assert {r["make"] for r in rows} == {"Honda"}
        assert "Cam chain guide" not in {r["title"] for r in rows}, "a Kawasaki issue leaked into a Honda"

    def test_a_near_neighbour_model_is_returned_but_labelled(self, corpus):
        """The relaxed half. A CBR600RR entry may reach an F4i query, but it
        must arrive marked as another model — never as machine-specific."""
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=corpus, limit=25)
        by_title = {r["title"]: r for r in rows}
        assert "Regulator rectifier" in by_title, "Phase 244E: same-make entries now fill the request"
        assert by_title["Regulator rectifier"]["match_tier"] == "make_other_model"
        assert by_title["Fuel injector fouling"]["match_tier"] == "model"


class TestTheAnalysisPathUsesIt:
    def test_the_context_reports_the_correction_rather_than_applying_it_silently(self):
        s = VehicleContext(
            make="Honda", model="CBR600F4i", year=2001,
            identity_note="Vehicle identity: model recorded as 'cbrf4i', read as 'CBR600F4i'",
        ).to_context_string()
        assert "cbrf4i" in s and "CBR600F4i" in s

    def test_the_builder_calls_the_resolver(self):
        src = inspect.getsource(vap_worker._build_vehicle_context)
        assert "resolve_vehicle" in src
        assert "except Exception" in src, "resolution must stay best-effort"
