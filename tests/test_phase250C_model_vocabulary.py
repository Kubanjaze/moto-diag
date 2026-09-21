"""Phase 250C — the model vocabulary is keyed by marque, and attributed.

The defect 250B handed over: `vocabulary_from_conn` keyed the per-make
model vocabulary by the **raw** `known_issues.make` string, so a row
reading "Zero, Harley-Davidson, LiveWire, Energica" filed its models under
that whole string and under no marque. LiveWire could resolve none of its
23 models and Damon none of its 10, and ten of sixteen marques could
resolve only some of theirs.

Keying alone would not have been safe. The corpus compares marques on
single rows — "BMW, Ducati, KTM, Triumph, Aprilia, MV Agusta" with a model
column listing all six marques' machines — so keying by marque would have
put "BMW S 1000 R" in Aprilia's matching pool. Hence attribution, in three
rungs, each earned from the data and tested here.

This file also covers the compound-name split that Phase 250C folded in at
the operator's request: `/` separates two machines in most of this corpus
("R1200/R1250", "F650/F700", "Ego/Eva") but is part of the name in Zero's
own designations (SR/F, SR/S, SR/FX, DSR/X), which used to be split into
"SR" and "F" and therefore matched nothing at all.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge import models as md
from motodiag.knowledge.marque_families import SUB_MARQUES, same_family
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.knowledge.vehicle_resolver import known_models, resolve_vehicle

REPO_ROOT = Path(__file__).resolve().parents[1]
K = REPO_ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"

#: What each marque could resolve BEFORE this phase, measured on the shipped
#: corpus. The point of the table is the direction: no marque may go down.
BEFORE = {
    "Aprilia": 31, "BMW": 51, "Damon": 0, "Ducati": 83, "Energica": 6,
    "Harley-Davidson": 13, "Honda": 27, "KTM": 62, "Kawasaki": 39,
    "LiveWire": 0, "MV Agusta": 30, "Moto Guzzi": 11, "Suzuki": 29,
    "Triumph": 82, "Yamaha": 23, "Zero": 14,
}

#: The four marques whose every row carries a single marque. They were
#: already complete, so they are the control group: their pools must not
#: move at all *from a change to the derivation*.
#:
#: Honda's number moved 27 -> 46 at Phase 252, and not because the
#: derivation changed: 252 added thirteen rows naming the Ruckus, the
#: Metropolitan, the Grom, the PCX and their siblings, machines the corpus
#: had never carried. The other three are untouched by that phase and still
#: pin the derivation exactly, which is what this test is for. When a
#: content phase moves one of these, move the number and say which phase
#: and why — do not relax the equality, because the equality is the guard.
UNCHANGED = {"Honda": 46, "Kawasaki": 39, "Suzuki": 29, "Yamaha": 23}

#: Zero writes four designations with a slash in the name itself.
COMPOUND = ("SR/F", "SR/S", "DSR/X")


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    """The whole shipped corpus, indexed the way `db init` indexes it."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p250C") / "p250C.db")
    os.environ["MOTODIAG_DB_PATH"] = path
    reset_settings()
    init_db(path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    return path


@pytest.fixture(autouse=True)
def _env(corpus, monkeypatch):
    from motodiag.core.config import reset_settings

    monkeypatch.setenv("MOTODIAG_DB_PATH", corpus)
    reset_settings()
    yield
    reset_settings()


def _vocab(db):
    return md.model_vocabulary(db)


# ---------------------------------------------------------------------------
# 1. The keys are marques
# ---------------------------------------------------------------------------
class TestTheVocabularyIsKeyedByMarque:
    def test_every_key_is_a_marque(self, corpus):
        """Before this phase, six of 23 keys were not marques — one was the
        whole sentence "BMW and Ducati have listed adjustments; KTM, Triumph,
        Aprilia, Moto Guzzi have none", holding three models."""
        from motodiag.knowledge.marques import marque_vocabulary

        marques = marque_vocabulary(corpus)
        assert set(_vocab(corpus)) <= marques, set(_vocab(corpus)) - marques

    @pytest.mark.parametrize("marque", ["LiveWire", "Damon"])
    def test_a_marque_with_no_single_marque_row_can_still_resolve(self, corpus, marque):
        """LiveWire's every row reads "Harley-Davidson, LiveWire" and Damon's
        every row names four other marques beside it, so both keyed to
        nothing and resolved none of their models."""
        assert known_models(marque, db_path=corpus), marque

    @pytest.mark.parametrize("marque", sorted(BEFORE))
    def test_no_marque_resolves_fewer_models_than_before(self, corpus, marque):
        assert len(known_models(marque, db_path=corpus)) >= BEFORE[marque]

    @pytest.mark.parametrize("marque,count", sorted(UNCHANGED.items()))
    def test_the_already_complete_marques_do_not_move(self, corpus, marque, count):
        """Honda, Kawasaki, Suzuki and Yamaha write one marque per row, so
        raw-key and marque-key are the same thing for them. If one of these
        moves without a content phase behind it, the derivation changed
        something it had no business changing. See UNCHANGED for Honda's
        move at Phase 252, which had a content phase behind it."""
        assert len(known_models(marque, db_path=corpus)) == count


# ---------------------------------------------------------------------------
# 2. Attribution — which marque a model belongs to
# ---------------------------------------------------------------------------
class TestAttribution:
    def test_a_model_named_on_a_single_marque_row_belongs_to_that_marque(self, corpus):
        """Rung 1. "Brutale" is an MV Agusta, and it says so nowhere in its
        own name — only by appearing on MV Agusta's own rows."""
        assert "Brutale" in known_models("MV Agusta", db_path=corpus)
        assert "Brutale" not in known_models("Aprilia", db_path=corpus)

    def test_a_token_that_names_a_marque_belongs_to_it(self, corpus):
        """Rung 2, and the reason keying alone was not enough: one row
        compares six marques and lists all six marques' machines."""
        for foreign in ("BMW S 1000 R", "Ducati desmo", "Triumph triples"):
            assert foreign not in known_models("Aprilia", db_path=corpus), foreign

    def test_a_marque_name_is_not_a_model(self, corpus):
        """Rung 3's exception. The "All European makes" row's model column
        reads "Aprilia, BMW, Ducati, Gilera, Husqvarna, KTM, Moto Guzzi,
        Moto Morini" — a list of marques, tokenised as models."""
        for marque in ("BMW", "Ducati", "Aprilia", "KTM", "Moto Guzzi", "Zero"):
            assert marque not in known_models(marque, db_path=corpus), marque

    def test_a_sub_marques_models_stay_with_its_parent(self, corpus):
        """The exemption. "LiveWire" names a marque *and* is a
        Harley-Davidson machine, so the rung-2 exclusion would have taken
        every LiveWire model out of Harley-Davidson's pool."""
        harley = known_models("Harley-Davidson", db_path=corpus)
        assert [m for m in harley if "LiveWire" in m], sorted(harley)

    def test_the_family_is_declared_not_derived(self):
        assert SUB_MARQUES == {"LiveWire": "Harley-Davidson"}
        assert same_family("Harley-Davidson", "LiveWire")
        assert same_family("LiveWire", "Harley-Davidson")
        assert same_family("Zero", "Zero")
        assert not same_family("Zero", "Energica")
        assert not same_family("", "Zero")


# ---------------------------------------------------------------------------
# 3. Compound model names — the slash that belongs to the name
# ---------------------------------------------------------------------------
class TestCompoundModelNames:
    @pytest.mark.parametrize("name", COMPOUND)
    def test_a_compound_designation_survives_tokenisation(self, name):
        """The reproduction. "Zero S, SR, SR/F, SR/S, DS, DSR" used to
        tokenise to "SR" and "F", so the machine's own name was never in the
        vocabulary and an SR/F resolved to no model at all."""
        tokens = md._model_tokens("Zero S, SR, SR/F, SR/S, DS, DSR, DSR/X and FXE")
        assert name in tokens, tokens

    @pytest.mark.parametrize("value,expected", [
        ("BMW F650/F700, F750/F800 parallel twins", ["BMW F650", "F700", "F750"]),
        ("Ducati Monster 695/S2R, Multistrada 620/1000", ["S2R", "Multistrada 620"]),
        ("Energica Ego/Eva, Eva Ribelle, Esse", ["Eva", "Esse"]),
    ])
    def test_a_slash_between_two_machines_still_separates_them(self, value, expected):
        """`/` is a list separator everywhere else in this corpus, and must
        stay one: in every enumeration the right-hand fragment is a full
        designation of three characters or more."""
        tokens = md._model_tokens(value)
        for name in expected:
            assert name in tokens, (value, tokens)

    @pytest.mark.parametrize("name", COMPOUND)
    def test_a_compound_designation_resolves(self, corpus, name):
        resolution = resolve_vehicle("Zero", name, db_path=corpus)
        assert resolution.model.applied, (name, resolution.model.method)
        assert resolution.resolved_model() == name

    @pytest.mark.parametrize("name", COMPOUND)
    def test_a_compound_designation_reaches_the_junction(self, corpus, name):
        with sqlite3.connect(corpus) as conn:
            found = conn.execute(
                "SELECT COUNT(*) FROM known_issue_models WHERE model = ?", (name,)
            ).fetchone()[0]
        assert found, name

    def test_the_left_hand_side_must_be_a_name_not_a_letter(self):
        """"Zero S/DS" is Zero S and Zero DS — two machines — and stays two.
        The rule needs two characters on the left, which is what separates a
        designation from an enumeration with a shared prefix."""
        tokens = md._model_tokens("Zero S/DS, FX, FXS and FXE")
        assert "S/DS" not in tokens, tokens


# ---------------------------------------------------------------------------
# 4. What this phase deliberately did not change
# ---------------------------------------------------------------------------
class TestWhatStaysRefused:
    def test_an_ambiguous_abbreviation_is_still_refused(self, corpus):
        """BMW R1250GS matches R1150, R1200 and R-series, and the resolver is
        right to refuse rather than pick. 250C changes what is in the pool,
        never how the ladder decides."""
        resolution = resolve_vehicle("BMW", "R1250GS", db_path=corpus)
        assert not resolution.model.applied
        assert resolution.model.method == "ambiguous"

    def test_a_model_belonging_to_another_marque_does_not_resolve(self, corpus):
        assert not resolve_vehicle("Aprilia", "Brutale", db_path=corpus).model.applied

    def test_a_bare_sub_marque_name_stays_ambiguous(self, corpus):
        """The corpus never writes a bare "LiveWire" model: it writes
        "Harley-Davidson LiveWire (ELW)" and "LiveWire ONE (LW1)", so the
        name genuinely covers two machines and refusing is the honest
        answer."""
        resolution = resolve_vehicle("Harley-Davidson", "LiveWire", db_path=corpus)
        assert not resolution.model.applied

    def test_the_wildcard_model_never_enters_a_pool(self, corpus):
        for marque in BEFORE:
            assert md.WILDCARD_MODEL not in known_models(marque, db_path=corpus)


# ---------------------------------------------------------------------------
# 5. The junction, rebuilt
# ---------------------------------------------------------------------------
class TestTheJunction:
    def test_a_rebuild_is_idempotent(self, corpus):
        first = rebuild_model_index_at(corpus)
        second = rebuild_model_index_at(corpus)
        assert first == second

    def test_every_marque_with_models_reaches_the_junction(self, corpus):
        with sqlite3.connect(corpus) as conn:
            rows = conn.execute("SELECT COUNT(*) FROM known_issue_models").fetchone()[0]
        assert rows > 1800, rows

    def test_a_marque_name_is_not_indexed_as_a_model(self, corpus):
        """The junction carried (Aprilia, "BMW"), (BMW, "Ducati") and
        (Ducati, "Ducati") before this phase."""
        with sqlite3.connect(corpus) as conn:
            found = conn.execute(
                "SELECT COUNT(*) FROM known_issue_models WHERE model IN "
                "('BMW', 'Ducati', 'Aprilia', 'KTM', 'Moto Guzzi')"
            ).fetchone()[0]
        assert found == 0, found
