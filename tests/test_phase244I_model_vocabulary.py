"""Phase 244I — the model column, and the models an entry says it does NOT cover.

The sibling of Phase 244F and the harder one, because `make` never had this:
entries name models in order to exclude them.

    390 Adventure, 790 Adventure, 890 Adventure — as distinct from 1290 Super Adventure
    Hypermotard 1100 (not EVO)
    950 and 990 LC8 on the fiche; 1190/1290 fitment unknown, not excluded

A wrong marque is usually obvious to a technician. A wrong MODEL of the right
marque reads as a machine-specific match and gets acted on — so these guards
lean on the exclusions, and enumerate every contrast value in the corpus rather
than sampling.
"""

import contextlib
import sqlite3

import pytest

from support.source_guards import code_of
from motodiag.core.database import init_db, SCHEMA_VERSION
from motodiag.core.migrations import get_migration_by_version
from motodiag.knowledge import models as md
from motodiag.knowledge import vehicle_resolver as vr
from motodiag.knowledge.issues_repo import add_known_issue
from motodiag.knowledge.marques import dedupe_contained

ROWS = [
    ("KTM", "390 Adventure", "Fuel pump"),
    ("KTM", "390 Adventure R", "Fork seal"),
    ("KTM", "890 Adventure", "Chain guide"),
    ("KTM", "1290 Super Adventure", "Cam chain"),
    ("KTM", "390 Duke", "Clutch basket"),
    # the exclusion cases, verbatim in shape
    ("KTM", "390 Adventure, 790 Adventure, 890 Adventure — as distinct from 1290 Super Adventure",
     "Service interval split"),
    ("KTM", "390 Adventure, 390 Adventure R, 890 Adventure — as against 390 Duke, 890 Duke",
     "Adventure-only recall"),
    ("Ducati", "Panigale", "Desmo service"),
    ("Ducati", "Hypermotard 1100", "Belt tensioner"),
    ("Ducati", "Hypermotard 1100 (not EVO)", "Rear shock linkage"),
    ("BMW", "R1200GS", "Final drive"),
    ("BMW", "Liquid-cooled R-series boxers, R1200GS and all LC R models from 2013", "ELAST belt"),
    ("Honda", "CBR600F4i", "Injector fouling"),
    ("Honda", "All", "Cam chain tensioner"),
    # Shapes the real corpus produces that a hand-built fixture omits, each of
    # which let a mutation escape until it was added:
    #   "... and R" splits to a bare "R", which would match almost any text
    ("KTM", "1290 Super Adventure and R, 1090 Adventure R", "Spoked wheel bearing"),
    #   splitting on "," inside parentheses tears a year qualifier in half
    #   NB the fragment must be SHORT enough to reach the bracket check —
    #   a longer one is rejected on length first and the guard proves nothing
    ("Ducati", "Monster 796 (2010-2014, 2015+)", "DVT timing"),
    #   a scope phrase that names a real model
    ("KTM", "All 390 Adventure variants", "Coolant spec"),
]


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "kb.db")
    init_db(path)
    for make, model, title in ROWS:
        add_known_issue(title=title, description="d", make=make, model=model, db_path=path)
    md.rebuild_model_index_at(path)
    return path


def _models_for(path, title):
    c = sqlite3.connect(path)
    try:
        return {r[0] for r in c.execute(
            "SELECT j.model FROM known_issue_models j JOIN known_issues k ON k.id = j.issue_id "
            "WHERE k.title = ?", (title,))}
    finally:
        c.close()


class TestAnExcludedModelIsNeverIndexed:
    """The failure with a person on the other end."""

    def test_as_distinct_from_excludes(self, db):
        got = _models_for(db, "Service interval split")
        assert "1290 Super Adventure" not in got, "an explicitly excluded model was indexed"
        assert got == {"390 Adventure", "790 Adventure", "890 Adventure"}

    def test_as_against_excludes(self, db):
        got = _models_for(db, "Adventure-only recall")
        assert "390 Duke" not in got and "890 Duke" not in got
        assert got == {"390 Adventure", "390 Adventure R", "890 Adventure"}

    def test_a_parenthetical_not_excludes(self, db):
        """`Hypermotard 1100 (not EVO)` covers the 1100, not the EVO."""
        got = _models_for(db, "Rear shock linkage")
        assert "EVO" not in got
        assert got == {"Hypermotard 1100"}

    def test_the_excluded_model_is_still_reachable_from_its_own_entries(self, db):
        """Excluding it from one entry must not remove it from the corpus."""
        _, rows = vr.known_issues_for_vehicle("KTM", "1290 Super Adventure", db_path=db, limit=50)
        titles = {r["title"] for r in rows if r["match_tier"] == "model"}
        assert "Cam chain" in titles
        assert "Service interval split" not in titles

    @pytest.mark.parametrize("value,forbidden", [
        ("390 Adventure — as against 390 Duke", "390 Duke"),
        ("390 Adventure — as distinct from 1290 Super Adventure", "1290 Super Adventure"),
        ("390 Adventure versus 390 Duke", "390 Duke"),
        ("390 Adventure rather than 390 Duke", "390 Duke"),
        ("390 Adventure, unlike 390 Duke", "390 Duke"),
        ("390 Adventure excluding 390 Duke", "390 Duke"),
        ("390 Adventure; 390 Duke not established", "390 Duke"),
    ])
    def test_every_contrast_phrasing_truncates(self, db, value, forbidden):
        vocab = md.model_vocabulary(db)
        got = md.extract_models("KTM", value, vocab)
        assert forbidden not in got, f"{forbidden!r} survived {value!r}"

    def test_fitment_unknown_yields_nothing_for_the_tail(self, db):
        """`1190/1290 fitment unknown, not excluded` means UNKNOWN. Truncating
        at `not` is correct; a parser clever enough to read the double negative
        would get it wrong."""
        vocab = md.model_vocabulary(db)
        got = md.extract_models("KTM", "390 Adventure on the fiche; 1190/1290 fitment unknown, not excluded", vocab)
        assert "1190" not in got and "1290" not in got


class TestDedupKeepsRealMachines:
    def test_both_survive_when_both_are_named(self, db):
        """`390 Adventure` sits inside `390 Adventure R`, but both are named and
        both are distinct bikes. A naive substring dedup loses the shorter."""
        got = _models_for(db, "Adventure-only recall")
        assert {"390 Adventure", "390 Adventure R"} <= got

    def test_the_shorter_is_dropped_when_only_the_longer_appears(self):
        assert dedupe_contained(["390 Adventure", "390 Adventure R"],
                                "390 Adventure R only") == ["390 Adventure R"]

    def test_containment_is_about_occurrences_not_strings(self):
        hay = "390 Adventure, 390 Adventure R"
        assert dedupe_contained(["390 Adventure", "390 Adventure R"], hay) == \
            ["390 Adventure", "390 Adventure R"]


class TestTheVocabularyComesFromTheStringsThatBrokeTheColumn:
    def test_a_model_named_only_inside_a_list_is_in_the_vocabulary(self, db):
        """`390 Adventure` has a plain row here, but the derivation must also
        surface names that appear only inside list values — that is the
        difference between 4 rows gaining a model and 271."""
        vocab = md.model_vocabulary(db)
        assert "R1200GS" in vocab.get("BMW", set())

    def test_the_vocabulary_is_scoped_per_make(self, db):
        vocab = md.model_vocabulary(db)
        assert "Panigale" not in vocab.get("KTM", set())
        assert "390 Adventure" not in vocab.get("Ducati", set())

    def test_a_model_from_another_make_does_not_match(self, db):
        vocab = md.model_vocabulary(db)
        assert md.extract_models("Ducati", "390 Adventure, 890 Adventure", vocab) == []

    def test_known_models_returns_the_vocabulary_not_raw_column_values(self, db):
        got = set(vr.known_models("KTM", db))
        assert "390 Adventure" in got
        assert not any("as distinct from" in m for m in got), \
            "a prose value reached the matching pool as if it were a model name"
        assert not any(len(m) > 28 for m in got)

    def test_no_single_character_tokens(self, db):
        """A bare `R` reached the vocabulary in the first build and would match
        almost any text."""
        vocab = md.model_vocabulary(db)
        assert not [m for s in vocab.values() for m in s if len(m) < 2]

    def test_no_bare_year_tokens(self, db):
        """`2018+` is a qualifier, not a machine. Splitting
        `"Monster 796 (2010-2014, 2015+)"` on the comma produced one."""
        vocab = md.model_vocabulary(db)
        bad = [m for s in vocab.values() for m in s
               if __import__("re").fullmatch(r"(?:19|20)\d{2}[-–—+]?(?:(?:19|20)\d{2})?\+?", m)]
        assert not bad, f"year tokens in the vocabulary: {bad}"

    def test_no_unbalanced_bracket_debris(self, db):
        """Splitting on `,` inside parentheses left tokens like
        `1200 DVT (2015-2017` — a year qualifier torn in half."""
        vocab = md.model_vocabulary(db)
        bad = [m for s in vocab.values() for m in s
               if m.count("(") != m.count(")") or m.count("[") != m.count("]")]
        assert not bad, f"unbalanced fragments in the vocabulary: {bad[:3]}"

    def test_the_vocabulary_is_derived_not_hardcoded(self):
        src = code_of(md)
        assert "SELECT make, model FROM known_issues" in src
        for name in ("CBR600F4i", "R1200GS", "Panigale", "390 Adventure"):
            assert f'"{name}"' not in src, f"{name} hard-coded"


class TestScopesAreNotModels:
    def test_all_is_never_a_model(self, db):
        assert _models_for(db, "Cam chain tensioner") == set()
        vocab = md.model_vocabulary(db)
        assert not [m for s in vocab.values() for m in s if m == "All"]

    def test_a_scope_phrase_naming_a_model_is_still_a_scope(self, db):
        """`All 390 Adventure variants` is a statement about the make, not a
        model-specific entry. Without the scope check it would index as
        `390 Adventure` and outrank genuinely model-specific rows."""
        assert _models_for(db, "Coolant spec") == set()

    def test_a_scope_phrase_yields_nothing_even_with_a_populated_pool(self, db):
        vocab = md.model_vocabulary(db)
        assert md.extract_models("KTM", "All 390 Adventure variants", vocab) == []

    def test_a_wildcard_row_still_reaches_the_make(self, db):
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=db, limit=50)
        by_title = {r["title"]: r for r in rows}
        assert by_title["Cam chain tensioner"]["match_tier"] == "make_wide"


class TestRetrievalGainsPrecisionWithoutLosingPhase244E:
    def test_a_prose_row_now_ranks_as_this_model(self, db):
        _, rows = vr.known_issues_for_vehicle("BMW", "R1200GS", db_path=db, limit=50)
        by_title = {r["title"]: r for r in rows}
        assert by_title["ELAST belt"]["match_tier"] == "model", \
            "a prose row naming R1200GS should rank as this model, not as another"

    def test_monotonicity_still_holds(self, db):
        for make in vr.known_makes(db):
            _, base = vr.known_issues_for_vehicle(make, "", db_path=db, limit=100)
            for model in vr.known_models(make, db):
                _, narrowed = vr.known_issues_for_vehicle(make, model, db_path=db, limit=100)
                assert len(narrowed) >= len(base), f"{make} + {model!r}"

    def test_cross_make_leakage_is_still_impossible(self, db):
        for make in ("KTM", "Ducati", "BMW", "Honda"):
            _, rows = vr.known_issues_for_vehicle(make, "", db_path=db, limit=100)
            assert {r["make"] for r in rows} <= {make}


class TestTheSchemaContract:
    def test_schema_version_is_current(self):
        assert SCHEMA_VERSION == 56  # f9-noqa: ssot-pin contract-pin: Phase 244I schema-bump pin. The literal is the point — importing the constant alone would make this assert x == x. Bumped 55→56 by migration 056 (known_issue_models junction). Bumping requires a corresponding new migration in src/motodiag/core/migrations.py.

    def test_the_migration_backfills_in_its_own_transaction(self):
        # f9-noqa: ssot-pin contract-pin: 56 is the migration this phase adds,
        # named deliberately. Importing SCHEMA_VERSION here would make the guard
        # follow a future bump and quietly stop checking migration 056.
        migration = get_migration_by_version(56)  # f9-noqa: ssot-pin contract-pin: 56 names the migration this phase adds, not the current schema version. Importing SCHEMA_VERSION here would make the guard follow a future bump and quietly stop checking that migration 056 still backfills its junction.
        assert migration.post_apply == "motodiag.knowledge.models:rebuild_model_index"

    def test_the_model_column_is_never_rewritten(self, db):
        c = sqlite3.connect(db)
        stored = {r[0] for r in c.execute("SELECT DISTINCT model FROM known_issues")}
        c.close()
        assert any("as distinct from" in s for s in stored), \
            "the exclusion text was rewritten out of the column"

    def test_a_rebuild_is_idempotent(self, db):
        c = sqlite3.connect(db); c.row_factory = sqlite3.Row
        before = c.execute("select count(*) from known_issue_models").fetchone()[0]
        md.rebuild_model_index(c); c.commit()
        after = c.execute("select count(*) from known_issue_models").fetchone()[0]
        c.close()
        assert before == after
