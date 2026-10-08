"""Phase 380, F142 — a multi-make row's models under their own make.

The model junction filed every model of a multi-make row under every make
the row named: Energica's Ego under Harley-Davidson, LiveWire and Zero. The
vocabulary now places a model by evidence first:
- a single-make row that names it, its marque prefix included ("Energica
  Ego");
- the transmission lookup.

The rest (the operator's 3A) stay under every make their row names, as
before, in a list pinned here that may only shrink as evidence arrives.
Measured on the operator's database: 109 junction rows leave, none are
added, and the migrated junction equals a fresh seed build's.
"""

from __future__ import annotations

import pathlib
import sqlite3

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.marques import (
    european_marques, extract_marques, rebuild_make_index_at,
)
from motodiag.knowledge.marques import vocabulary_from_conn as marque_vocabulary_from_conn
from motodiag.knowledge.models import lookup_marques, rebuild_model_index_at, unassigned_models

SEED = pathlib.Path(__file__).resolve().parent.parent / "src" / "motodiag" / "knowledge" \
    / "seed" / "knowledge"

#: 3A: models on multi-make rows that no evidence places, so they stay under
#: every make their row names. Measured 2026-10-08 on a fresh seed build; the
#: list may only shrink. Several are prose read as models (F135's question).
UNASSIGNED = [
    ('2020 service manual', ('Energica', 'Harley-Davidson', 'LiveWire', 'Zero')),
    ("2025 owner's manuals", ('Energica', 'Harley-Davidson', 'LiveWire', 'Zero')),
    ('946', ('Piaggio', 'Vespa')),
    ('Alpinista', ('Energica', 'Harley-Davidson', 'LiveWire', 'Zero')),
    ('BV 250 Tourer', ('Piaggio', 'Vespa')),
    ('BV 300 Tourer', ('Piaggio', 'Vespa')),
    ('BV 500', ('Piaggio', 'Vespa')),
    ('Beverly 300', ('Piaggio', 'Vespa')),
    ('Beverly 400', ('Piaggio', 'Vespa')),
    ('DS/SR', ('Damon', 'Energica', 'Harley-Davidson', 'LiveWire', 'Zero')),
    ('Esse', ('Damon', 'Energica', 'Harley-Davidson', 'LiveWire', 'Zero')),
    ('Fiddle 4', ('Kymco', 'SYM')),
    ('GTV 250', ('Piaggio', 'Vespa')),
    ('GTV 310', ('Piaggio', 'Vespa')),
    ('Gilera', ('Aprilia', 'BMW', 'Ducati', 'KTM', 'MV Agusta', 'Moto Guzzi', 'Triumph')),
    ('Guzzi V100', ('Aprilia', 'BMW', 'Ducati', 'KTM', 'MV Agusta', 'Moto Guzzi', 'Triumph')),
    ('Guzzi V85', ('Aprilia', 'BMW', 'Ducati', 'KTM', 'MV Agusta', 'Moto Guzzi', 'Triumph')),
    ('Husqvarna', ('Aprilia', 'BMW', 'Ducati', 'KTM', 'MV Agusta', 'Moto Guzzi', 'Triumph')),
    ('Jet 14', ('Kymco', 'SYM')),
    ('LXV 150', ('Piaggio', 'Vespa')),
    ('Liberty 125', ('Piaggio', 'Vespa')),
    ('Liberty 50', ('Piaggio', 'Vespa')),
    ('MV', ('Aprilia', 'BMW', 'Ducati', 'KTM', 'MV Agusta', 'Moto Guzzi', 'Triumph')),
    ('Medley 125', ('Piaggio', 'Vespa')),
    ('Medley 150', ('Piaggio', 'Vespa')),
    ('Moto Morini', ('Aprilia', 'BMW', 'Ducati', 'KTM', 'MV Agusta', 'Moto Guzzi', 'Triumph')),
    ('Mulholland', ('Energica', 'Harley-Davidson', 'LiveWire', 'Zero')),
    ('Primavera 125', ('Piaggio', 'Vespa')),
    ('Primavera 50', ('Piaggio', 'Vespa')),
    ('S 1000 RR by type code', ('Aprilia', 'BMW', 'Ducati', 'KTM', 'Moto Guzzi', 'Triumph')),
    ('S 1000 XR', ('Aprilia', 'BMW', 'Ducati', 'KTM', 'Moto Guzzi', 'Triumph')),
    ('S 150', ('Piaggio', 'Vespa')),
    ('SRV', ('Aprilia', 'MV Agusta')),
    ('Testastretta MY2010', ('BMW', 'Ducati', 'KTM', 'MV Agusta')),
    ('X-Town 300', ('Kymco', 'SYM')),
    ('X9 500', ('Piaggio', 'Vespa')),
    ('approximately 2016 to 2020', ('Aprilia', 'MV Agusta')),
]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    db = str(tmp_path_factory.mktemp("f142") / "built.db")
    init_db(db)
    for f in sorted(SEED.glob("known_issues_*.json")):
        load_known_issues_file(f, db)
    rebuild_make_index_at(db)
    rebuild_model_index_at(db)
    conn = sqlite3.connect(db)
    yield conn
    conn.close()


def test_the_unassigned_list_equals_its_pin(built):
    """3A. When evidence places one of these, drop it from the pin."""
    assert unassigned_models(built) == UNASSIGNED


def test_no_lookup_placed_model_sits_under_another_make(built):
    marques = marque_vocabulary_from_conn(built)
    european = european_marques(vocabulary=marques)
    wrong = []
    for issue_id, make, model in built.execute(
            "SELECT j.issue_id, j.make, j.model FROM known_issue_models j "
            "JOIN known_issues k ON k.id = j.issue_id WHERE k.make LIKE '%,%'"):
        row_make = built.execute("SELECT make FROM known_issues WHERE id = ?",
                                 (issue_id,)).fetchone()[0]
        row_marques = extract_marques(row_make, vocabulary=marques, european=european)
        placed = lookup_marques(model, row_marques)
        if placed and make not in placed:
            wrong.append((issue_id, make, model, sorted(placed)))
    assert wrong == []


def test_the_ego_is_energicas(built):
    makes = {r[0] for r in built.execute(
        "SELECT make FROM known_issue_models WHERE model = 'Ego'")}
    assert makes == {"Energica"}
