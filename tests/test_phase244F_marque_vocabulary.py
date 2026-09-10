"""Phase 244F — a make column that holds prose cannot be queried.

`known_issues.make` was one free-text column doing four jobs. The cost was
concrete: **LiveWire and Damon were not queryable makes at all**, because every
one of their entries lives inside a multi-marque string. Phase 243 researched
and wrote 24 LiveWire entries and none could be retrieved.

The guards lean hardest on OVER-extraction, because attaching an entry to a
marque it does not name puts another machine's documented fault in front of a
mechanic — the one failure here with a person on the other end.
"""

import contextlib
import inspect
import json
import sqlite3

import pytest

from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import init_db, SCHEMA_VERSION
from motodiag.core.migrations import get_migration_by_version
from motodiag.knowledge import marques as mq
from motodiag.knowledge import vehicle_resolver as vr
from motodiag.knowledge.issues_repo import add_known_issue, count_known_issues
from motodiag.knowledge.loader import load_known_issues_file
from support.source_guards import code_of

SEED = SEED_DATA_DIR / "knowledge"

# Mirrors the shapes the real corpus turned out to contain.
ROWS = [
    ("Honda", "CBR600F4i", "Injector fouling"),
    ("Honda", "All", "Cam chain tensioner"),
    ("Harley-Davidson", "Sportster", "Stator connector"),
    ("Harley-Davidson, LiveWire", "All", "HV interlock check"),
    ("Zero, Harley-Davidson, LiveWire, Energica, Damon", "All", "HV first responder cut loop"),
    ("BMW, Ducati, KTM, MV Agusta", "All", "Desmo vs shim service intervals"),
    ("Aprilia and MV Agusta", "All", "Italian ECU connector"),
    ("BMW and Ducati have listed adjustments; KTM, Triumph, Aprilia, Moto Guzzi have none",
     "All", "TEXA coding coverage"),
    ("All makes", "All", "Reading a vendor compatibility table"),
    ("All European makes", "All", "Valve-train job types"),
    ("BMW", "R1200GS", "Final drive bearing"),
    ("Ducati", "Panigale", "Desmo service"),
    # Triumph and Moto Guzzi have standalone rows in the real corpus, so the
    # fixture must too: without them they exist only inside the prose sentence,
    # and the extractor conservatively — and correctly — declines to invent a
    # marque it has seen nowhere else.
    ("Triumph", "Bonneville", "Sprag clutch"),
    ("Moto Guzzi", "V7", "Shaft drive service"),
]


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "kb.db")
    init_db(path)
    for make, model, title in ROWS:
        add_known_issue(title=title, description="d", make=make, model=model, db_path=path)
    # The vocabulary is a function of the whole corpus, so the index is only
    # complete once every row is in. Mirrors what `db init` does after seeding.
    mq.rebuild_make_index_at(path)
    return path


def _marques_for(path, title):
    c = sqlite3.connect(path)
    try:
        return {r[0] for r in c.execute(
            "SELECT j.make FROM known_issue_makes j JOIN known_issues k ON k.id = j.issue_id "
            "WHERE k.title = ?", (title,))}
    finally:
        c.close()


class TestTheMarquesThatDidNotExist:
    """LiveWire and Damon appear nowhere as a standalone make value."""

    def test_livewire_is_reachable(self, db):
        _, rows = vr.known_issues_for_vehicle("LiveWire", "", db_path=db, limit=50)
        titles = {r["title"] for r in rows}
        assert "HV interlock check" in titles
        assert "HV first responder cut loop" in titles

    def test_damon_is_reachable(self, db):
        _, rows = vr.known_issues_for_vehicle("Damon", "", db_path=db, limit=50)
        assert "HV first responder cut loop" in {r["title"] for r in rows}

    def test_they_are_in_the_vocabulary_despite_having_no_row_of_their_own(self, db):
        vocab = mq.marque_vocabulary(db)
        assert {"LiveWire", "Damon"} <= vocab
        c = sqlite3.connect(db)
        standalone = c.execute(
            "SELECT COUNT(*) FROM known_issues WHERE make IN ('LiveWire','Damon')").fetchone()[0]
        c.close()
        assert standalone == 0, "fixture no longer models the defect"

    def test_livewire_resolves_as_a_make(self, db):
        identity = vr.resolve_vehicle("LiveWire", db_path=db)
        assert identity.make.resolved == "LiveWire" and identity.make.applied


class TestEveryNamedMarqueCanFindTheEntry:
    def test_a_four_marque_entry_is_reachable_from_each(self, db):
        for make in ("BMW", "Ducati", "KTM", "MV Agusta"):
            _, rows = vr.known_issues_for_vehicle(make, "", db_path=db, limit=50)
            assert "Desmo vs shim service intervals" in {r["title"] for r in rows}, make

    def test_the_prose_sentence_reaches_all_six_marques(self, db):
        got = _marques_for(db, "TEXA coding coverage")
        assert got == {"BMW", "Ducati", "KTM", "Triumph", "Aprilia", "Moto Guzzi"}

    def test_an_and_joined_pair_reaches_both(self, db):
        assert _marques_for(db, "Italian ECU connector") == {"Aprilia", "MV Agusta"}


class TestScopePhrasesAreNotMarqueLists:
    def test_all_makes_reaches_any_make(self, db):
        for make in ("Honda", "BMW", "LiveWire"):
            _, rows = vr.known_issues_for_vehicle(make, "", db_path=db, limit=50)
            assert "Reading a vendor compatibility table" in {r["title"] for r in rows}, make

    def test_all_makes_is_stored_as_a_wildcard_not_a_marque(self, db):
        assert _marques_for(db, "Reading a vendor compatibility table") == {mq.WILDCARD_MAKE}
        assert mq.WILDCARD_MAKE not in mq.marque_vocabulary(db)

    def test_all_european_makes_expands_to_european_marques(self, db):
        got = _marques_for(db, "Valve-train job types")
        assert "BMW" in got and "Ducati" in got and "Triumph" in got

    def test_all_european_makes_does_not_reach_honda(self, db):
        """The scope means something; treating it as a wildcard would put
        European valve-train guidance in front of a Honda."""
        assert "Honda" not in _marques_for(db, "Valve-train job types")
        _, rows = vr.known_issues_for_vehicle("Honda", "", db_path=db, limit=50)
        assert "Valve-train job types" not in {r["title"] for r in rows}


class TestOverExtractionIsTheDangerousDirection:
    """Attaching an entry to a marque it does not name is the failure with a
    mechanic on the other end."""

    def test_no_entry_reaches_a_marque_its_make_string_does_not_name(self, db):
        c = sqlite3.connect(db)
        pairs = c.execute(
            "SELECT k.make, j.make FROM known_issue_makes j "
            "JOIN known_issues k ON k.id = j.issue_id").fetchall()
        c.close()
        euro = mq.european_marques(db_path=db)
        for source, marque in pairs:
            if marque == mq.WILDCARD_MAKE:
                assert source == mq.ALL_MAKES
            elif source == mq.ALL_EUROPEAN:
                assert marque in euro
            else:
                assert marque in source, f"{marque!r} attached to an entry tagged {source!r}"

    def test_matching_is_whole_word(self):
        """A substring match would attach entries to marques never named."""
        vocab = {"BMW", "KTM", "Zero"}
        assert mq.extract_marques("BMWX", vocab, set()) == []
        assert mq.extract_marques("Zeroing the throttle", vocab, set()) == []

    def test_a_single_marque_is_settled_before_any_parsing(self):
        assert mq.extract_marques("MV Agusta", {"MV Agusta", "BMW"}, set()) == ["MV Agusta"]

    def test_an_unknown_make_extracts_nothing(self):
        assert mq.extract_marques("Bimota", {"BMW", "Ducati"}, set()) == []

    def test_a_marque_named_only_in_prose_is_not_invented(self):
        """A name appearing solely inside a sentence, and established nowhere
        else in the corpus, is NOT extracted. Conservative on purpose: the
        vocabulary is what the corpus establishes, not what a sentence mentions.
        Found while building — a fixture lacking standalone Triumph and Moto
        Guzzi rows made this behaviour visible."""
        vocab = {"BMW", "Ducati"}
        got = mq.extract_marques(
            "BMW and Ducati have listed adjustments; KTM, Triumph have none", vocab, set())
        assert got == ["BMW", "Ducati"]
        assert "Triumph" not in got and "KTM" not in got


class TestTheVocabularyIsDerived:
    def test_no_hardcoded_marque_list_in_the_module(self):
        src = code_of(mq)
        code = "\n".join(
            l for l in src.splitlines()
            if not l.strip().startswith("#") and not l.strip().startswith('"')
        )
        for marque in ("Honda", "Kawasaki", "Suzuki", "Yamaha", "Triumph", "Aprilia"):
            assert f'"{marque}"' not in code, f"{marque} hard-coded — must come from the corpus"
        assert "SELECT DISTINCT make FROM known_issues" in src

    def test_known_makes_returns_marques_not_raw_column_values(self, db):
        got = set(vr.known_makes(db))
        assert "LiveWire" in got
        assert mq.ALL_MAKES not in got
        assert not any(";" in m for m in got), "a sentence reached the matching pool"
        assert not any("," in m for m in got)

    def test_the_european_set_comes_from_seed_filenames(self):
        src = code_of(mq.european_marques)
        assert "known_issues_european_" in src


class TestTheIndexStaysInStepWithTheColumn:
    def test_every_issue_has_at_least_one_marque(self, db):
        c = sqlite3.connect(db)
        orphans = c.execute(
            "SELECT COUNT(*) FROM known_issues k WHERE NOT EXISTS "
            "(SELECT 1 FROM known_issue_makes j WHERE j.issue_id = k.id)").fetchone()[0]
        c.close()
        assert orphans == 0

    def test_the_make_column_is_never_rewritten(self, db):
        """The author's text is the source; the junction is derived from it."""
        c = sqlite3.connect(db)
        stored = {r[0] for r in c.execute("SELECT DISTINCT make FROM known_issues")}
        c.close()
        assert mq.ALL_EUROPEAN in stored, "a scope phrase was rewritten out of the column"
        assert any(";" in s for s in stored), "the prose entry was rewritten"

    def test_a_rebuild_is_idempotent(self, db):
        c = sqlite3.connect(db); c.row_factory = sqlite3.Row
        before = c.execute("select count(*) from known_issue_makes").fetchone()[0]
        mq.rebuild_make_index(c); c.commit()
        after = c.execute("select count(*) from known_issue_makes").fetchone()[0]
        c.close()
        assert before == after

    def test_a_rebuild_repairs_an_order_dependent_incremental_index(self, tmp_path):
        """The vocabulary is a function of the WHOLE corpus, so a row inserted
        before the entry that establishes a marque under-indexes. Found during
        the build: a rebuild after seeding produced more rows than the inserts
        had. The rebuild is authoritative and `db init` runs it."""
        path = str(tmp_path / "order.db"); init_db(path)
        # A PROSE make: its fragments carry prose markers, so nothing clean can
        # be split out of it and it teaches the vocabulary nothing. A comma-list
        # would not reproduce the effect, because splitting it establishes the
        # marques from that very row.
        add_known_issue(title="Coverage", description="d",
                        make="Triumph has listed adjustments and Ducati has none",
                        model="All", db_path=path)
        add_known_issue(title="Sprag", description="d", make="Triumph", model="Bonneville", db_path=path)
        c = sqlite3.connect(path)
        incremental = {r[0] for r in c.execute(
            "SELECT j.make FROM known_issue_makes j JOIN known_issues k ON k.id=j.issue_id "
            "WHERE k.title='Coverage'")}
        c.close()
        assert "Triumph" not in incremental, "fixture no longer reproduces the ordering effect"

        mq.rebuild_make_index_at(path)
        c = sqlite3.connect(path)
        rebuilt = {r[0] for r in c.execute(
            "SELECT j.make FROM known_issue_makes j JOIN known_issues k ON k.id=j.issue_id "
            "WHERE k.title='Coverage'")}
        c.close()
        assert rebuilt == {"Triumph"}, "the rebuild did not repair the index"

    def test_db_init_rebuilds_after_seeding(self):
        import inspect as _i
        from motodiag.cli import main as cli_main
        assert "rebuild_make_index_at" in code_of(cli_main)

    def test_reseeding_twice_leaves_the_index_unchanged(self, tmp_path):
        path = str(tmp_path / "seed.db"); init_db(path)
        files = sorted(SEED.glob("known_issues_*.json"))[:12]
        for f in files:
            load_known_issues_file(f, path)
        c = sqlite3.connect(path)
        n1 = c.execute("select count(*) from known_issue_makes").fetchone()[0]
        c.close()
        for f in files:
            load_known_issues_file(f, path)
        c = sqlite3.connect(path)
        n2 = c.execute("select count(*) from known_issue_makes").fetchone()[0]
        c.close()
        assert n1 == n2 and n1 > 0

    def test_schema_version_is_current(self):
        assert SCHEMA_VERSION == 56  # f9-noqa: ssot-pin contract-pin: Phase 244F schema-bump pin. The literal is the point — importing the constant alone would make this assert x == x. Bumped 54→55 by migration 055 (known_issue_makes junction, because LiveWire and Damon were not queryable makes at all). Bumping requires a corresponding new migration in src/motodiag/core/migrations.py. Bumped 55→56 at Phase 244I (migration 056 adds the known_issue_models junction; the model column has the same list-and-prose disease as make, plus entries that name models in order to EXCLUDE them).

    def test_the_migration_backfills_inside_its_own_transaction(self):
        """An index that exists but is empty is indistinguishable from a corpus
        that says nothing — the confusion Phase 244C was written to end."""
        m = get_migration_by_version(55)
        assert m.post_apply == "motodiag.knowledge.marques:rebuild_make_index"


class TestPhase244EStillHolds:
    def test_monotonicity_survives_the_junction(self, db):
        for make in vr.known_makes(db):
            _, base = vr.known_issues_for_vehicle(make, "", db_path=db, limit=100)
            for model in vr.known_models(make, db):
                _, narrowed = vr.known_issues_for_vehicle(make, model, db_path=db, limit=100)
                assert len(narrowed) >= len(base), f"{make} + {model!r}"

    def test_tiers_are_still_attached(self, db):
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=db, limit=50)
        assert all(r.get("match_tier") for r in rows)


class TestAMissingJunctionDegradesRatherThanGoesSilent:
    """A database below schema 55 has no junction table. Joining against a table
    that is not there returns nothing — and "no rows" is the one answer this
    whole line of work exists to stop being ambiguous, because it looks
    identical to a corpus with nothing to say about the machine.

    Caught by the regression: eleven tests whose fixtures predate the junction
    went from working to silently empty."""

    def _corpus_without_junction(self, tmp_path, monkeypatch):
        p = tmp_path / "old.db"
        c = sqlite3.connect(p)
        c.execute("""CREATE TABLE known_issues (id INTEGER PRIMARY KEY, make TEXT,
                     model TEXT, title TEXT, description TEXT, severity TEXT)""")
        c.executemany(
            "INSERT INTO known_issues (make, model, title, description, severity) VALUES (?,?,?,?,?)",
            [("Honda", "CBR600F4i", "Injector fouling", "d", "high"),
             ("Honda", "All", "Cam chain tensioner", "d", "critical"),
             ("Kawasaki", "ZX-10R", "Cam chain guide", "d", "high")])
        c.commit(); c.close()

        @contextlib.contextmanager
        def _conn(path=None):
            cc = sqlite3.connect(p); cc.row_factory = sqlite3.Row
            try: yield cc
            finally: cc.close()

        monkeypatch.setattr(vr, "get_connection", _conn)
        monkeypatch.setattr(mq, "get_connection", _conn)
        return str(p)

    def test_retrieval_still_works_without_the_junction(self, tmp_path, monkeypatch):
        path = self._corpus_without_junction(tmp_path, monkeypatch)
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=path, limit=25)
        assert rows, "a pre-55 database went silently empty instead of falling back"
        assert "Injector fouling" in {r["title"] for r in rows}

    def test_the_fallback_still_refuses_to_cross_a_make(self, tmp_path, monkeypatch):
        """Degrading must not degrade the safety property."""
        path = self._corpus_without_junction(tmp_path, monkeypatch)
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=path, limit=25)
        assert {r["make"] for r in rows} == {"Honda"}
        assert "Cam chain guide" not in {r["title"] for r in rows}

    def test_the_fallback_still_tiers(self, tmp_path, monkeypatch):
        path = self._corpus_without_junction(tmp_path, monkeypatch)
        _, rows = vr.known_issues_for_vehicle("Honda", "CBR600F4i", db_path=path, limit=25)
        assert rows[0]["match_tier"] == "model"

    def test_the_fallback_is_scoped_to_junction_errors(self):
        """Asserted on the source, and the reason is worth recording.

        A behavioural test cannot distinguish a narrow catch from a blanket one
        here: the junction query and the fallback depend on the same columns, so
        any error the first hits, the second hits too, and both end up raising.
        Removing the scoping condition therefore changes nothing observable
        through this path — mutation testing showed exactly that, and the first
        version of this guard passed with the condition deleted.

        The condition still earns its place: it stops a future edit to either
        statement from turning an unrelated failure into silently
        column-matched results. Since the behaviour is not reachable, the
        structure is what gets pinned, and this docstring says why rather than
        implying a stronger check than exists."""
        import inspect as _i
        src = code_of(vr.known_issues_for_vehicle)
        assert '"known_issue_makes" in msg' in src, (
            "the junction fallback must not absorb unrelated SQL errors")
        assert "else:\n                    raise" in src, (
            "an error concerning neither junction must propagate")
        assert src.count("raise") >= 2

    def test_a_genuinely_broken_query_still_raises(self, tmp_path, monkeypatch):
        """A malformed query must surface even with the fallback in place."""
        p = tmp_path / "broken.db"
        c = sqlite3.connect(p)
        c.execute("CREATE TABLE known_issues (id INTEGER PRIMARY KEY, make TEXT, model TEXT, title TEXT)")
        c.execute("INSERT INTO known_issues (make, model, title) VALUES ('Honda','CBR','T')")
        c.commit(); c.close()

        @contextlib.contextmanager
        def _conn(path=None):
            cc = sqlite3.connect(p); cc.row_factory = sqlite3.Row
            try: yield cc
            finally: cc.close()

        monkeypatch.setattr(vr, "get_connection", _conn)
        monkeypatch.setattr(mq, "get_connection", _conn)
        # no `severity` column -> the ORDER BY is malformed, which is a bug and
        # must surface rather than be absorbed by the fallback
        with pytest.raises(sqlite3.OperationalError):
            vr.known_issues_for_vehicle("Honda", "CBR", db_path=str(p))
