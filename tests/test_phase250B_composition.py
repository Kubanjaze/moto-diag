"""Phase 250B — composing the prompt instead of truncating it.

Gate 13 measured the defect: Phase 241's ten critical HV-safety rows are
the most severe rows any electric machine has, so they filled the
twelve-row cap every time and the pack, controller, regen and thermal
layers written across 246-249 never reached the model. Retrieval was also
symptom-blind — a hot pack and a dead regen brake light got the same
twelve rows.

This file tests the fix in three places: the classifier that says whether
a row is about an electric machine, the composition itself, and the real
`diagnose quick` command that has to show the result. The end-to-end
tests are the ones that matter; the unit tests are here because the
composition has rules a walk cannot show — that the head is never spent
on relevance, that the result is exactly full, and that what comes out is
ordered the way retrieval ordered it.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from motodiag.cli.diagnose import KNOWN_ISSUE_PROMPT_LIMIT, _load_known_issues
from motodiag.cli.main import cli as real_cli
from motodiag.core.database import get_connection, init_db
from motodiag.knowledge.loader import load_dtc_directory, load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.knowledge.powertrain import is_electric_row
from motodiag.knowledge.prompt_rows import (
    RELEVANCE_RESERVE,
    compose_prompt_rows,
    relevance_score,
    relevance_tokens,
)

from tests.test_phase123_diagnose import (  # type: ignore[import-not-found]
    make_diagnose_fn,
    make_response,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = REPO_ROOT / "src" / "motodiag" / "knowledge" / "seed"
K = SEED / "knowledge"
DTC = SEED / "dtc_codes"

#: The four layers 246-249 shipped, as they read in a title.
LAYERS = {
    "bms": re.compile(r"balanc|state of health|voltage curve|cycle count|cell", re.I),
    "inverter": re.compile(r"inverter|motor controller|igbt|phase loss|firmware|controller", re.I),
    "regen": re.compile(r"regen|brake light|coast|one-pedal|single-pedal", re.I),
    "thermal": re.compile(r"cool|temperature|thermal|ambient", re.I),
}

ELECTRIC_BIKES = [
    ("Zero", "SR/F", 2023),
    ("Energica", "Ego", 2022),
    ("LiveWire", "LiveWire One", 2022),
    ("Harley-Davidson", "LiveWire", 2021),
]

COMBUSTION_BIKES = [
    ("Honda", "CBR600RR", 2006),
    ("Harley-Davidson", "Sportster 1200", 2001),
    ("Yamaha", "MT07", 2021),
    ("Suzuki", "SV650", 2019),
    ("BMW", "R1250GS", 2020),
]

#: Words a V-twin has and a battery-electric machine does not.
COMBUSTION_WORDS = ("stator", "compensator sprocket", "intake manifold",
                    "clutch pack", "carburetor", "valve clearance")


def _layers_in(rows) -> set[str]:
    return {name for name, rx in LAYERS.items()
            if any(rx.search(str(r.get("title") or "")) for r in rows)}


def _row(title, *, make="Honda", model="CBR600RR", severity="medium",
         tier="model", symptoms=None, description=""):
    return {"title": title, "make": make, "model": model, "severity": severity,
            "match_tier": tier, "symptoms": symptoms or [], "description": description}


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p250B") / "p250B.db")
    os.environ["MOTODIAG_DB_PATH"] = path
    reset_settings()
    init_db(path)
    load_dtc_directory(DTC, path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    return path


@pytest.fixture(autouse=True)
def _env(db, monkeypatch):
    from motodiag.core.config import reset_settings

    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield
    reset_settings()


@pytest.fixture(scope="module")
def garage(db):
    from motodiag.core.config import reset_settings

    os.environ["MOTODIAG_DB_PATH"] = db
    os.environ["COLUMNS"] = "240"
    reset_settings()
    ids = {}
    for bikes, powertrain in ((ELECTRIC_BIKES, "electric"), (COMBUSTION_BIKES, "ice")):
        for make, model, year in bikes:
            CliRunner().invoke(real_cli, [
                "garage", "add", "--make", make, "--model", model,
                "--year", str(year), "--powertrain", powertrain,
            ], catch_exceptions=False)
            with get_connection(db) as conn:
                ids[(make, model)] = conn.execute(
                    "SELECT id FROM vehicles WHERE make = ? AND model = ? ORDER BY id DESC LIMIT 1",
                    (make, model),
                ).fetchone()[0]
    return ids


def _prompt_rows(vehicle_id: int, symptoms: str) -> list[dict]:
    """Run the REAL `diagnose quick` and return what reached the model."""
    captured: dict = {}
    base = make_diagnose_fn(make_response())

    def _capture(**kwargs):
        captured["known"] = list(kwargs.get("known_issues") or [])
        return base(**kwargs)

    with patch("motodiag.cli.diagnose._default_diagnose_fn", _capture):
        result = CliRunner().invoke(real_cli, [
            "diagnose", "quick", "--vehicle-id", str(vehicle_id), "--symptoms", symptoms,
        ], catch_exceptions=False)
    assert result.exit_code == 0, result.output[-1200:]
    return captured.get("known", [])


# ---------------------------------------------------------------------------
# 1. Which rows are about an electric machine
# ---------------------------------------------------------------------------
class TestTheClassifier:
    @pytest.mark.parametrize("make", ["Zero", "LiveWire", "Energica", "Damon",
                                      "Zero, Harley-Davidson, LiveWire, Energica, Damon"])
    def test_an_electric_marque_makes_a_row_electric(self, make):
        assert is_electric_row(_row("t", make=make))

    def test_a_mixed_marques_electric_model_counts(self):
        """The 2019-2020 machine is a Harley-Davidson LiveWire: the marque
        column says Harley-Davidson and only the model says otherwise."""
        assert is_electric_row(_row("t", make="Harley-Davidson", model="LiveWire"))

    def test_a_wildcard_row_belongs_in_any_prompt(self):
        assert is_electric_row(_row("t", make="*"))

    @pytest.mark.parametrize("make,model", [("Honda", "CBR600RR"),
                                            ("Harley-Davidson", "Sportster 883/1200"),
                                            ("BMW", "R1250GS"), ("Ducati", "Multistrada")])
    def test_a_combustion_row_is_not_electric(self, make, model):
        assert not is_electric_row(_row("t", make=make, model=model))

    @pytest.mark.parametrize("make", [
        "Honda — zeroing the TPS is part of this procedure",
        "Honda, Kawasaki (nonzero play at the swingarm pivot)",
        "Triumph — the procedure is zeroed against the crank",
    ])
    def test_a_marque_is_not_found_inside_another_word(self, make):
        """"Zero" the marque, not "zero" the word.

        The shipped corpus cannot tell these apart: its 27 make strings are
        comma-separated marque lists, and the one prose string among them
        ("BMW and Ducati have listed adjustments; KTM, Triumph, Aprilia,
        Moto Guzzi have none") names no electric marque. So this guard is
        for the next prose value, not the current ones — and the column has
        already proved it accepts a whole sentence.

        Written twice. The first version put the word in the title, which
        the classifier never reads, and the mutation that strips the word
        boundaries survived it; the second put it in the model, which the
        marque patterns never scan. Phase 244's lesson — a guard written
        before the evidence is a guess about what the evidence looks
        like — earned twice in one phase."""
        assert not is_electric_row(_row("t", make=make, model="CB750"))


# ---------------------------------------------------------------------------
# 2. The composition rules
# ---------------------------------------------------------------------------
class TestComposition:
    def test_with_no_powertrain_and_no_symptoms_it_is_244s(self):
        """The default is the old behaviour exactly: the first `limit` rows in
        the order retrieval returned them. That is what keeps `motodiag code`
        and every other caller unchanged."""
        rows = [_row(f"Row {i:02d}") for i in range(30)]
        out = compose_prompt_rows(rows, limit=12)
        assert [r["title"] for r in out] == [f"Row {i:02d}" for i in range(12)]

    def test_the_result_is_exactly_full(self):
        """244S pins this: a prompt that under-fills wastes budget the cap was
        chosen to spend."""
        rows = [_row(f"Row {i:02d}") for i in range(30)]
        out = compose_prompt_rows(rows, limit=12, powertrain="electric",
                                  symptoms=["nothing matches this text"])
        assert len(out) == 12

    def test_a_short_corpus_is_not_padded(self):
        rows = [_row(f"Row {i}") for i in range(5)]
        assert len(compose_prompt_rows(rows, limit=12)) == 5

    def test_the_head_is_never_spent_on_relevance(self):
        """The reserved slots come out of the tail. The most specific, most
        severe rows are still there — that is Phase 241's safety floor."""
        rows = ([_row(f"Head {i}", severity="critical") for i in range(8)]
                + [_row(f"Tail {i}", symptoms=["regen brake light"]) for i in range(20)])
        out = compose_prompt_rows(rows, limit=12, symptoms=["regen brake light fails"])
        titles = [r["title"] for r in out]
        for i in range(8):
            assert f"Head {i}" in titles

    def test_a_matching_row_is_pulled_out_of_the_tail(self):
        rows = ([_row(f"Head {i}", severity="critical") for i in range(8)]
                + [_row(f"Filler {i}") for i in range(10)]
                + [_row("Regenerative braking and the brake lamp",
                        symptoms=["brake light does not light under regen"])])
        out = compose_prompt_rows(rows, limit=12, symptoms=["brake light under regen"])
        assert "Regenerative braking and the brake lamp" in [r["title"] for r in out]

    def test_the_reserve_is_bounded(self):
        """At most RELEVANCE_RESERVE rows are promoted, however many match."""
        rows = ([_row(f"Head {i}", severity="critical") for i in range(8)]
                + [_row(f"Regen match {i}", symptoms=["regen brake light"]) for i in range(10)])
        out = compose_prompt_rows(rows, limit=12, symptoms=["regen brake light"])
        promoted = [r for r in out if r["title"].startswith("Regen match")]
        assert len(promoted) <= RELEVANCE_RESERVE

    def test_what_comes_out_is_ordered_the_way_retrieval_ordered_it(self):
        """244S's contract: most specific tier first, then severity. A promoted
        row takes its place in that order rather than arriving at the end."""
        rows = ([_row(f"Model {i}", tier="model", severity="high") for i in range(8)]
                + [_row(f"Wide {i}", tier="make_wide") for i in range(6)]
                + [_row("Other regen row", tier="make_other_model",
                        symptoms=["regen brake light"])])
        out = compose_prompt_rows(rows, limit=12, symptoms=["regen brake light"])
        order = {"model": 0, "make_wide": 1, "make_other_model": 2}
        tiers = [order[r["match_tier"]] for r in out]
        assert tiers == sorted(tiers), [r["title"] for r in out]

    def test_an_electric_bike_prefers_electric_rows(self):
        rows = ([_row(f"Combustion {i}", make="Harley-Davidson", severity="critical")
                 for i in range(20)]
                + [_row(f"Electric {i}", make="Zero") for i in range(12)])
        out = compose_prompt_rows(rows, limit=12, powertrain="electric")
        assert all(r["title"].startswith("Electric") for r in out), [r["title"] for r in out]

    def test_too_few_electric_rows_are_topped_up_rather_than_starving_the_prompt(self):
        rows = ([_row("Electric one", make="Zero")]
                + [_row(f"Combustion {i}", make="Harley-Davidson") for i in range(20)])
        out = compose_prompt_rows(rows, limit=12, powertrain="electric")
        assert len(out) == 12
        assert "Electric one" in [r["title"] for r in out]

    def test_a_combustion_bike_is_not_filtered(self):
        rows = [_row(f"Combustion {i}", make="Honda") for i in range(20)]
        assert len(compose_prompt_rows(rows, limit=12, powertrain="ice")) == 12

    def test_relevance_reads_the_title_and_the_symptoms(self):
        wanted = relevance_tokens("brake light does not come on under regen")
        hit = _row("Does regen light the brake lamp", symptoms=["brake light stays off"])
        miss = _row("Valve clearance tightening", symptoms=["ticking at idle"])
        assert relevance_score(hit, wanted) > relevance_score(miss, wanted)

    def test_short_and_empty_words_carry_no_signal(self):
        """Four characters or more, minus a stop list — the shape
        predictor.py already uses for its TSB matching."""
        tokens = relevance_tokens("the pack is hot and this bike overheats")
        assert "pack" in tokens and "overheats" in tokens
        for noise in ("the", "is", "hot", "and", "this", "bike"):
            assert noise not in tokens, noise
        assert relevance_tokens("") == set()
        assert relevance_score(_row("anything"), set()) == 0


# ---------------------------------------------------------------------------
# 3. Through the real command
# ---------------------------------------------------------------------------
class TestTheDiagnosticPath:
    @pytest.mark.parametrize("make,model,year", ELECTRIC_BIKES,
                             ids=[f"{m}-{mo}" for m, mo, _y in ELECTRIC_BIKES])
    def test_a_range_complaint_reaches_the_layers_that_answer_it(
            self, db, garage, make, model, year):
        rows = _prompt_rows(garage[(make, model)], "range dropped by half")
        assert {"bms", "thermal"} <= _layers_in(rows), sorted(_layers_in(rows))

    @pytest.mark.parametrize("make,model,year", ELECTRIC_BIKES,
                             ids=[f"{m}-{mo}" for m, mo, _y in ELECTRIC_BIKES])
    def test_a_regen_complaint_reaches_the_regen_layer(self, db, garage, make, model, year):
        rows = _prompt_rows(garage[(make, model)], "brake light does not come on under regen")
        assert "regen" in _layers_in(rows), sorted(_layers_in(rows))

    @pytest.mark.parametrize("make,model,year", ELECTRIC_BIKES,
                             ids=[f"{m}-{mo}" for m, mo, _y in ELECTRIC_BIKES])
    def test_the_prompt_is_still_exactly_twelve_rows(self, db, garage, make, model, year):
        assert len(_prompt_rows(garage[(make, model)], "range dropped by half")) == \
            KNOWN_ISSUE_PROMPT_LIMIT

    def test_a_battery_electric_machine_is_not_told_about_its_clutch(self, db, garage):
        """The Harley-Davidson LiveWire case. Before this phase its twelve rows
        were stator failure, compensator sprocket noise, intake manifold seal
        leak and clutch pack wear — an engine, a clutch and a stator it does
        not have — because its model does not resolve and every row it got was
        make-wide V-twin content."""
        rows = _prompt_rows(garage[("Harley-Davidson", "LiveWire")], "range dropped by half")
        titles = " ".join(r["title"].lower() for r in rows)
        for word in COMBUSTION_WORDS:
            assert word not in titles, word

    def test_the_safety_floor_is_still_there(self, db, garage):
        """241 put the HV rows first on purpose: a technician opening a pack
        needs them. Composition must not spend them."""
        rows = _prompt_rows(garage[("Zero", "SR/F")], "range dropped by half")
        assert sum(1 for r in rows if r.get("severity") == "critical") >= 5

    @pytest.mark.parametrize("make,model,year", COMBUSTION_BIKES,
                             ids=[f"{m}-{mo}" for m, mo, _y in COMBUSTION_BIKES])
    def test_a_combustion_bike_gets_no_electric_row(self, db, garage, make, model, year):
        """The powertrain filter engages only for an electric machine, and
        tiering already kept the HV rows out of a combustion prompt. Measured
        on five bikes, including the Sportster that shares its marque with a
        LiveWire.

        Asserted with the classifier rather than the layer regexes: a
        combustion bike legitimately has cooling rows — an MT07 head gasket
        row names coolant, a boxer charging row names liquid cooling — and a
        keyword search for "cool" would call those electric content."""
        rows = _prompt_rows(garage[(make, model)], "hard starting when hot")
        electric = [r["title"] for r in rows if is_electric_row(r)]
        assert electric == [], electric

    @pytest.mark.parametrize("make,model,year", COMBUSTION_BIKES,
                             ids=[f"{m}-{mo}" for m, mo, _y in COMBUSTION_BIKES])
    def test_a_combustion_prompt_is_still_full_and_ordered(self, db, garage, make, model, year):
        rows = _prompt_rows(garage[(make, model)], "hard starting when hot")
        assert len(rows) == KNOWN_ISSUE_PROMPT_LIMIT
        order = {"model": 0, "make_wide": 1, "make_other_model": 2}
        tiers = [order.get(str(r.get("match_tier")), 3) for r in rows]
        assert tiers == sorted(tiers)

    def test_the_helper_still_answers_its_old_signature(self, db):
        """244S calls this positionally with three fields and no keywords, and
        `motodiag code` still does. The new arguments are optional."""
        identity, rows = _load_known_issues("Zero", "SR/F", 2023, db)
        assert identity is not None and rows


# ---------------------------------------------------------------------------
# 4. F95 — the garage can show an electric bike's power
# ---------------------------------------------------------------------------
class TestTheGarageShowsMotorPower:
    def test_motor_kw_round_trips_through_the_cli(self, db):
        CliRunner().invoke(real_cli, [
            "garage", "add", "--make", "Zero", "--model", "SR/S", "--year", "2024",
            "--powertrain", "electric", "--motor-kw", "82",
        ], catch_exceptions=False)
        out = CliRunner().invoke(real_cli, ["garage", "list"], catch_exceptions=False).output
        assert "82.0kW" in out, out[-800:]

    def test_an_unset_motor_power_renders_like_every_other_unset_field(self, db):
        """Not "NonekW". `.get(key, default)` never fires for a key that exists
        holding None, which is what every electric bike had."""
        CliRunner().invoke(real_cli, [
            "garage", "add", "--make", "Energica", "--model", "Esse", "--year", "2021",
            "--powertrain", "electric",
        ], catch_exceptions=False)
        out = CliRunner().invoke(real_cli, ["garage", "list"], catch_exceptions=False).output
        assert "NonekW" not in out, out[-800:]
