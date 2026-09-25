"""Phase 250 — Gate 13: the electric track through the real front doors.

Track L's closing gate. Roadmap row 250 names a path — "query electric
bike → BMS/motor/regen/thermal analysis end-to-end" — so the gate's first
duty is to walk that path and report what a technician actually gets.

House style from Gates 8, 9, 11 and 12: every query goes through the REAL
CLI root or the HTTP API, never the repository layer; a class of
executable documentation records what the corpus honestly lacks and is
MEANT to fail the day someone fills it; and a gate guards the gates
before it.

What Step 0 measured, and what `TestTheDiagnosticPathAsItIs` pins: the
path does not carry the track's own content. Retrieval is by vehicle and
symptom-blind, capped at twelve rows, and since 240C orders critical
first, 241's ten critical HV-safety rows fill the cap. A Zero SR/F or
LiveWire ONE query reaches the controller layer only; an Energica Ego or
Harley-Davidson LiveWire query reaches none of BMS, inverter, regen or
thermal. Four phases and 26 rows do not arrive.

Those tests assert today's truth so that the truth is visible, and every
one of them is written to FAIL when row 250B fixes retrieval. That is the
operator's decision for this gate (2026-09-19): the gate reports, 250B
repairs — the pattern 240B and 240C set after Gate 12.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.cli.main import cli as real_cli
from motodiag.core.database import get_connection, init_db
from motodiag.engine.prompts import build_knowledge_context
from motodiag.hardware.compat_loader import seed_all
from motodiag.knowledge.loader import load_dtc_directory, load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at

# Reuse the Phase 123 doubles so the mocked response matches the shape the
# CLI persists — Phase 125 established this import.
from tests.test_phase123_diagnose import (  # type: ignore[import-not-found]
    make_diagnose_fn,
    make_response,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = REPO_ROOT / "src" / "motodiag" / "knowledge" / "seed"
K = SEED / "knowledge"
DTC = SEED / "dtc_codes"
HW = REPO_ROOT / "src" / "motodiag" / "hardware" / "compat_data"

#: Track L's makes as the corpus spells them. Damon is here deliberately:
#: Phase 245 is paused (no customer unit, no manual, no NHTSA record), so
#: Damon exists only inside 241's multi-marque HV rows — the same shape as
#: Moto Guzzi in Gate 12.
MAKES = ("Zero", "Energica", "LiveWire", "Harley-Davidson", "Damon")
ELECTRIC_MAKES = ("Zero", "Energica", "LiveWire")

#: Track L's eight files, with the provenance mix each phase shipped.
TRACK_L_FILES = {
    "known_issues_electric_hv_safety.json": {"model-generated": 10},
    "known_issues_zero.json": {"service-manual": 16, "forum": 1},
    "known_issues_livewire.json": {"service-manual": 11, "forum": 3},
    "known_issues_energica.json": {"service-manual": 10, "forum": 2},
    "known_issues_bms.json": {"service-manual": 5, "forum": 2},
    "known_issues_inverter.json": {"service-manual": 5, "regulation": 2, "forum": 1},
    "known_issues_regen.json": {"service-manual": 6, "forum": 1},
    "known_issues_thermal.json": {"service-manual": 4},
}

#: The four generic layers 246-249 shipped, as they read in a title.
LAYERS = {
    "bms": re.compile(r"balanc|state of health|voltage curve|cycle count|cell", re.I),
    "inverter": re.compile(r"inverter|motor controller|igbt|phase loss|firmware|controller", re.I),
    "regen": re.compile(r"regen|brake light|coast|one-pedal|single-pedal", re.I),
    "thermal": re.compile(r"cool|temperature|thermal|ambient", re.I),
}

#: (make, model, year, the layers that reach the prompt today). Measured on
#: a freshly seeded database on 2026-09-19 and reproduced from the live copy.
PAIRS = [
    ("Zero", "SR/F", 2023, {"inverter"}),
    ("Energica", "Ego", 2022, set()),
    ("LiveWire", "LiveWire One", 2022, {"inverter"}),
    ("Harley-Davidson", "LiveWire", 2021, set()),
]

#: The search terms 246-249 each pinned in their own content tests.
LAYER_TERMS = [
    "balancing", "state of health", "derating",
    "inverter", "motor controller", "firmware",
    "regen", "brake light", "coast",
    "cooling", "motor temperature", "ambient",
]

#: The nine Energica cooling codes Phase 249 put on the cooling-fault row.
COOLING_CODES = ["P0A05", "P0A06", "P0A07", "P1040", "P1041",
                 "P1042", "P1037", "P1038", "P0A08"]

PROVENANCE = {"unverified", "model-generated", "forum",
              "service-manual", "mechanic-verified", "regulation"}

LABELS = ("service-manual", "forum", "regulation", "model-generated", "unverified")


def _entries(name: str) -> list[dict]:
    raw = json.loads((K / name).read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else next(v for v in raw.values() if isinstance(v, list))


def _text(e: dict) -> str:
    return " ".join(str(e.get(k) or "") for k in ("title", "description", "fix_procedure"))


def _layers_in(rows: list[dict]) -> set[str]:
    return {name for name, rx in LAYERS.items()
            if any(rx.search(str(r.get("title") or "")) for r in rows)}


def _run(args, expect_ok=True):
    """Invoke the REAL cli root, as Gate 11 insisted — a partial root cannot
    catch a command that fails to register on the real one."""
    result = CliRunner().invoke(real_cli, args, catch_exceptions=False)
    if expect_ok:
        assert result.exit_code == 0, f"{' '.join(args)} failed:\n{result.output[-1500:]}"
    return result


@pytest.fixture(scope="module")
def gate_db(tmp_path_factory):
    """One fully seeded database, built the way `db init` builds one: DTCs,
    every knowledge file in sorted order, then the two junction rebuilds —
    which must run AFTER the bulk load, because the marque vocabulary is
    derived from the whole corpus. The adapter catalogue comes too, so the
    gate can ask for an adapter and get an honest "none known"."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("gate13") / "gate13.db")
    os.environ["MOTODIAG_DB_PATH"] = path
    reset_settings()
    init_db(path)
    load_dtc_directory(DTC, path)
    for f in sorted(K.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    seed_all(data_dir=HW, db_path=path)
    return path


@pytest.fixture(autouse=True)
def _env(gate_db, monkeypatch):
    from motodiag.core.config import reset_settings

    monkeypatch.setenv("MOTODIAG_DB_PATH", gate_db)
    monkeypatch.setenv("COLUMNS", "240")
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    reset_settings()
    yield
    reset_settings()


@pytest.fixture(scope="module")
def api_key(gate_db):
    """A real key for a real user — the /v1 routes are key-gated and the gate
    walks in the front door. Created in-process and revoked when the module
    finishes, so no key outlives the test run."""
    from motodiag.auth.api_key_repo import create_api_key, revoke_api_key
    from motodiag.core.config import reset_settings

    os.environ["MOTODIAG_DB_PATH"] = gate_db
    reset_settings()
    with get_connection(gate_db) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) VALUES (?, ?, ?, 1)",
            ("gate13_owner", "gate13_owner@ex.com", "shop"),
        ).lastrowid
    record, key = create_api_key(uid, db_path=gate_db)
    yield key
    revoke_api_key(record.id, db_path=gate_db)


@pytest.fixture(scope="module")
def api(api_key, gate_db):
    client = TestClient(create_app(db_path_override=gate_db))
    client.headers.update({"X-API-Key": api_key})
    return client


@pytest.fixture(scope="module")
def garage(gate_db):
    """The four electric bikes, added through the real `garage add` — each
    declared `--powertrain electric`, which is the flag the diagnostic path
    then ignores. Returns {(make, model): vehicle_id}."""
    from motodiag.core.config import reset_settings

    os.environ["MOTODIAG_DB_PATH"] = gate_db
    os.environ["COLUMNS"] = "240"
    reset_settings()
    ids = {}
    for make, model, year, _layers in PAIRS:
        _run(["garage", "add", "--make", make, "--model", model,
              "--year", str(year), "--powertrain", "electric"])
        with get_connection(gate_db) as conn:
            ids[(make, model)] = conn.execute(
                "SELECT id FROM vehicles WHERE make = ? AND model = ? ORDER BY id DESC LIMIT 1",
                (make, model),
            ).fetchone()[0]
    return ids


def _diagnose_and_capture(vehicle_id: int, symptoms: str) -> tuple[list[dict], str]:
    """Run the REAL `diagnose quick` with the AI call replaced, and return the
    known issues it handed the model plus the context string it built.

    Row 250's path ends at the model, so the gate walks to the prompt rather
    than calling the retrieval helper — a helper that returns the right rows
    while the command sends the wrong ones is exactly the bug Gate 11's rule
    exists to catch.
    """
    captured: dict = {}
    base = make_diagnose_fn(make_response())

    def _capture(**kwargs):
        captured["known"] = list(kwargs.get("known_issues") or [])
        return base(**kwargs)

    with patch("motodiag.cli.diagnose._default_diagnose_fn", _capture):
        _run(["diagnose", "quick", "--vehicle-id", str(vehicle_id),
              "--symptoms", symptoms])
    known = captured.get("known", [])
    return known, build_knowledge_context(known)


# ===========================================================================
# 1. Every electric make answers through the CLI
# ===========================================================================
class TestEveryElectricMakeAnswersThroughTheCli:
    @pytest.mark.parametrize("make", MAKES)
    def test_kb_list_returns_rows_for_the_make(self, gate_db, make):
        out = _run(["kb", "list", "--make", make]).output
        assert "No known issues" not in out, out[-600:]
        assert any(label in out for label in LABELS), "the label must show beside the row"

    @pytest.mark.parametrize("make", MAKES)
    def test_the_hv_floor_returns_with_every_electric_make(self, gate_db, make):
        """241's rule: the HV file names all five makes in one string, and a
        make-filtered lookup returns it for each of them."""
        out = _run(["kb", "list", "--make", make]).output
        assert "service disconnect" in out.lower() or "HV" in out, out[-600:]

    def test_critical_comes_first_on_a_safety_file(self, gate_db):
        """240C. Position, not just presence — 243's lesson was that content
        which merely exists is unfindable."""
        out = _run(["kb", "list", "--make", "Zero", "--limit", "5"]).output
        assert "critical" in out.split("high")[0], out[-800:]

    def test_a_make_filter_does_not_cross_into_another_make(self, gate_db):
        """S0-7: `SR` (Zero) sits beside `SR400` (Yamaha) and `SRV 850`
        (Aprilia) in the model junction."""
        out = _run(["kb", "list", "--make", "Zero", "--limit", "50"]).output
        assert "Yamaha" not in out and "Aprilia" not in out, out[-800:]


# ===========================================================================
# 2. The four layers are reachable by the commands people use
# ===========================================================================
class TestTheFourLayersAreReachableByTheCommandsPeopleUse:
    @pytest.mark.parametrize("term", LAYER_TERMS)
    def test_kb_search_returns_the_layer_with_its_label(self, gate_db, term):
        out = _run(["kb", "search", term]).output
        assert term.split()[0].lower() in out.lower(), out[-600:]
        assert any(label in out for label in LABELS), "the label travels with the row"

    @pytest.mark.parametrize("code", COOLING_CODES)
    def test_kb_by_code_reaches_the_cooling_fault_row(self, gate_db, code):
        out = _run(["kb", "by-code", code]).output
        assert "cooling loop" in out.lower(), out[-600:]

    def test_kb_by_symptom_reaches_the_architecture_row(self, gate_db):
        out = _run(["kb", "by-symptom", "liquid cooled battery"]).output
        assert "liquid-cool" in out.lower(), out[-600:]


# ===========================================================================
# 3. The diagnostic path — measured before and after row 250B
#
# Gate 13 wrote this class to pin what it found: the layers 246-249 shipped
# never reached the model, and the twelve rows did not change when the
# symptom did. Row 250B fixed that, and these tests now pin the fix, which
# is what the gate was for. The old measurement is kept in each docstring,
# because a test that records only the current state cannot tell you a
# regression from a history.
# ===========================================================================
class TestTheDiagnosticPath:
    @pytest.mark.parametrize("make,model,year,expected", PAIRS,
                             ids=[f"{m}-{mo}" for m, mo, _y, _e in PAIRS])
    def test_a_range_complaint_reaches_the_pack_and_thermal_layers(
            self, gate_db, garage, make, model, year, expected):
        """Before 250B: Zero and LiveWire ONE reached the controller layer
        only; Energica Ego and Harley-Davidson LiveWire reached nothing.
        After: a range complaint reaches the layers that answer it."""
        known, _ctx = _diagnose_and_capture(garage[(make, model)], "range dropped by half")
        assert {"bms", "thermal"} <= _layers_in(known), (
            f"{make} {model}: a range complaint reached {sorted(_layers_in(known))}")

    @pytest.mark.parametrize("make,model,year,expected", PAIRS,
                             ids=[f"{m}-{mo}" for m, mo, _y, _e in PAIRS])
    def test_the_prompt_is_filled_to_its_cap(self, gate_db, garage, make, model,
                                             year, expected):
        """244S's cap is unchanged by 250B — composition, not enlargement.
        Reaching all four layers by raising the cap would have cost 27 rows
        on a Zero and 95 on a Harley-Davidson LiveWire (68 KB of prompt,
        three times over in the interactive flow)."""
        known, _ctx = _diagnose_and_capture(garage[(make, model)], "range dropped by half")
        assert len(known) == 12, f"{make} {model}: {len(known)} rows reached the prompt"

    def test_no_electric_pair_is_left_without_a_layer(self, gate_db, garage):
        """Before 250B this set was {Energica Ego, Harley-Davidson LiveWire} —
        two of four machines got none of the content Track L wrote for them."""
        empty = {(make, model) for make, model, _y, _e in PAIRS
                 if not _layers_in(_diagnose_and_capture(
                     garage[(make, model)], "range dropped by half")[0])}
        assert empty == set(), empty

    def test_a_regen_complaint_reaches_the_regen_layer(self, gate_db, garage):
        """The reserved slots go to what the rider reported, not to a fixed
        list — so the same machine answers a different complaint differently."""
        for make, model, _y, _e in PAIRS:
            known, _ctx = _diagnose_and_capture(
                garage[(make, model)], "brake light does not come on under regen")
            assert "regen" in _layers_in(known), (make, model, sorted(_layers_in(known)))

    def test_the_selection_changes_when_the_symptom_does(self, gate_db, garage):
        """Before 250B these two lists were identical: retrieval was by
        vehicle only, so a rider reporting a hot pack and a rider reporting a
        dead regen brake light were handed the same twelve rows."""
        vid = garage[("Zero", "SR/F")]
        hot, _a = _diagnose_and_capture(vid, "pack overheats while charging")
        lamp, _b = _diagnose_and_capture(vid, "brake light does not come on under regen")
        assert [r["title"] for r in hot] != [r["title"] for r in lamp]
        assert "thermal" in _layers_in(hot) and "regen" in _layers_in(lamp)

    def test_the_electric_powertrain_flag_now_reaches_retrieval(self, gate_db, garage):
        """The debt Phase 243 recorded and four phases were shaped by. Before
        250B, this machine — registered `--powertrain electric` — was handed
        twelve rows of V-twin content: stator failure, compensator sprocket
        noise, intake manifold seals, clutch pack wear."""
        known, _ctx = _diagnose_and_capture(
            garage[("Harley-Davidson", "LiveWire")], "range dropped by half")
        assert _layers_in(known), "no electric layer reached a battery-electric machine"
        titles = " ".join(r["title"].lower() for r in known)
        for combustion in ("stator", "compensator sprocket", "intake manifold", "clutch pack"):
            assert combustion not in titles, combustion

    def test_the_context_the_model_sees_carries_every_label(self, gate_db, garage):
        """246 Decision 3: the label travels with the number, and the prompt
        is a display surface. That part works, and stays working."""
        known, ctx = _diagnose_and_capture(garage[("Zero", "SR/F")], "range dropped by half")
        assert known and ctx
        for row in known:
            if row.get("source"):
                assert f"source: {row['source']}" in ctx


# ===========================================================================
# 4. Cross-surface agreement
# ===========================================================================
class TestCrossSurfaceAgreement:
    def test_the_api_finds_the_layer_the_cli_found(self, gate_db, api):
        cli = _run(["kb", "search", "cooling"]).output
        body = api.get("/v1/kb/search", params={"q": "cooling"}).json()
        assert "cooling" in cli.lower()
        assert body["known_issues"], body

    def test_the_api_answers_for_every_electric_make(self, gate_db, api):
        for make in ELECTRIC_MAKES:
            body = api.get("/v1/kb/issues", params={"make": make, "limit": 5}).json()
            assert body["total"] > 0, (make, body)

    def test_the_cli_resolves_a_misspelt_make_and_the_api_does_not(self, gate_db, api):
        """S0-5. `kb list --make` runs the resolver and says so; the API
        filters `make LIKE` with no resolution at all. Same corpus, two
        answers, and only the CLI tells the technician it corrected them."""
        out = _run(["kb", "list", "--make", "Zerro"]).output
        assert "Zero" in out, out[-600:]
        body = api.get("/v1/kb/issues", params={"make": "Zerro", "limit": 5}).json()
        assert body["total"] == 0, body

    def test_the_kb_routes_are_key_gated(self, gate_db):
        client = TestClient(create_app(db_path_override=gate_db))
        assert client.get("/v1/kb/issues", params={"make": "Zero"}).status_code == 401


# ===========================================================================
# 5. The honest gaps — what Track L knowingly lacks
#
# Each test pins a MEASURED absence and is written to fail when the absence
# is filled. A test that would still pass after the gap was closed is not
# documentation, it is decoration.
# ===========================================================================
class TestTheHonestGaps:
    @pytest.mark.parametrize("slug", ["zero", "energica", "livewire", "damon"])
    def test_no_electric_make_has_a_dtc_file(self, slug):
        """242: Zero publishes no machine-readable vocabulary — its codes are
        a numbered table in the owner's manual, which is knowledge-base
        content. Energica's 127 SAE codes are published and still unseeded:
        that is F90, open."""
        assert not (DTC / f"{slug}.json").exists()

    def test_the_code_command_cannot_classify_a_hybrid_ev_code(self, gate_db):
        """P0A05 is a valid SAE J2012 hybrid-propulsion code and the command a
        technician reaches for first calls it unrecognised: `classify_code`
        has no branch for the block, and `^P[0-9]{4}$` cannot match a hex
        letter in the third position. Phase 244 recorded the hazard."""
        out = _run(["code", "P0A05"]).output
        assert "unrecognized code format" in out.lower(), out[-600:]

    def test_kb_by_code_reaches_what_the_code_command_cannot(self, gate_db):
        """The two paths disagree for every electric code, because `kb
        by-code` LIKEs known_issues.dtc_codes while `code` reads the
        dtc_codes table. 247 corrected 246's claim that `code` reaches
        them."""
        assert "cooling loop" in _run(["kb", "by-code", "P0A05"]).output.lower()

    @pytest.mark.parametrize("category", ["hv_battery", "inverter", "regen",
                                          "thermal", "charging_port"])
    def test_the_electric_categories_exist_and_hold_no_codes(self, gate_db, category):
        """The category validates — so the CLI accepts it — and answers
        nothing. F90, open since 246."""
        out = _run(["code", "--category", category]).output
        assert "No DTCs found" in out, out[-600:]

    @pytest.mark.parametrize("make,model", [("Zero", "SR/F"), ("Energica", "Ego"),
                                            ("LiveWire", "LiveWire One"),
                                            ("Harley-Davidson", "LiveWire")])
    def test_no_adapter_is_known_for_any_electric_bike(self, gate_db, make, model):
        """Gate 12 could assert an adapter per European make. This one cannot:
        compat_matrix.json covers eleven combustion makes and no electric
        one — while 244's shipped row says a generic scan tool reads
        Energica's codes."""
        out = _run(["hardware", "compat", "recommend", "--make", make, "--model", model]).output
        assert "No compat entries known" in out, out[-600:]

    def test_the_compat_store_holds_no_electric_make(self):
        rows = json.loads((HW / "compat_matrix.json").read_text(encoding="utf-8"))
        makes = {r["make"] for r in rows}
        assert not ({"zero", "energica", "livewire", "damon"} & makes), makes

    def test_damon_is_a_make_with_no_content_of_its_own(self, gate_db):
        """245 is paused, not done: no customer unit delivered, no manual
        published, no NHTSA record. Damon exists only inside 241's HV rows,
        every one of them model-generated."""
        assert not (K / "known_issues_damon.json").exists()
        out = _run(["kb", "list", "--make", "Damon"]).output
        assert "model-generated" in out and "service-manual" not in out, out[-800:]

    def test_no_maker_publishes_a_regen_fault_code(self, gate_db):
        """248: the lamp-circuit codes the brake-light row names are named in
        its text as lamp codes, and nothing rides on dtc_codes."""
        for e in _entries("known_issues_regen.json"):
            assert not e.get("dtc_codes"), e["title"]

    def test_no_row_claims_a_liquid_cooled_battery(self):
        """249's premise correction: no document states how any of the three
        batteries is cooled. Scoped to description and fix_procedure the way
        249's own guard is — a title may say that nothing documents one, and
        the architecture row's title does exactly that."""
        bad = re.compile(r"(?:battery|pack|RESS) is (?:liquid|air)[- ]cooled"
                         r"|(?:liquid|air)[- ]cooled (?:battery|pack|RESS)\b(?! on any)", re.I)
        for name in TRACK_L_FILES:
            for e in _entries(name):
                for field in ("description", "fix_procedure"):
                    found = bad.search(e.get(field) or "")
                    assert not found, (name, e["title"][:40], found and found.group(0))

    def test_the_stale_energica_anchor_is_still_twenty_four_rows(self):
        """F93, open: 246-248 anchor Energica to "the 2018 Eva" where 249
        anchors to the document code. Two in bms, ten in inverter, twelve in
        regen. This fails when F93 is paid, which is the point."""
        counts = {n: len(re.findall(r"2018 Eva", (K / n).read_text(encoding="utf-8")))
                  for n in ("known_issues_bms.json", "known_issues_inverter.json",
                            "known_issues_regen.json", "known_issues_thermal.json",
                            "known_issues_energica.json")}
        assert counts == {"known_issues_bms.json": 2, "known_issues_inverter.json": 10,
                          "known_issues_regen.json": 12, "known_issues_thermal.json": 0,
                          "known_issues_energica.json": 0}, counts

    def test_an_electric_bike_shows_its_motor_power_in_the_garage(self, gate_db):
        """F95, found by this gate and fixed in 250B. `motor_kw` is a real
        column that `garage add` had no option to set, and the renderer's
        `.get('motor_kw', '?')` default never fired for a key that exists
        holding None, so every electric bike printed "NonekW"."""
        _run(["garage", "add", "--make", "Zero", "--model", "SR/S",
              "--year", "2024", "--powertrain", "electric", "--motor-kw", "82"])
        out = _run(["garage", "list"]).output
        assert "NonekW" not in out, out[-800:]
        assert "82.0kW" in out, out[-800:]


# ===========================================================================
# 6. Track L's corpus invariants, re-run against the live seed
# ===========================================================================
class TestTrackLCorpusInvariants:
    def test_provenance_vocabulary_is_the_six_values(self):
        seen = set()
        for f in K.glob("known_issues_*.json"):
            seen |= {e.get("source", "unverified") for e in _entries(f.name)}
        assert seen <= PROVENANCE, seen

    @pytest.mark.parametrize("name", sorted(TRACK_L_FILES))
    def test_each_track_l_file_ships_the_provenance_mix_its_phase_claimed(self, name):
        from collections import Counter
        assert Counter(e["source"] for e in _entries(name)) == Counter(TRACK_L_FILES[name])

    def test_track_l_is_seventy_nine_rows(self):
        assert sum(len(_entries(n)) for n in TRACK_L_FILES) == 79

    @pytest.mark.parametrize("name", ["known_issues_bms.json", "known_issues_inverter.json",
                                      "known_issues_regen.json", "known_issues_thermal.json"])
    def test_nothing_in_the_generic_layer_is_model_generated(self, name):
        assert all(e["source"] != "model-generated" for e in _entries(name))

    @pytest.mark.parametrize("name", ["known_issues_bms.json", "known_issues_inverter.json",
                                      "known_issues_regen.json", "known_issues_thermal.json"])
    def test_a_generic_layer_forum_row_names_its_site_and_the_page_date(self, name):
        """The convention 246 set and 247-248 kept. 249 shipped no forum row
        at all — its one readable thread held nothing quotable — so this is
        vacuously true there, which the next test makes visible."""
        for e in _entries(name):
            if e["source"] == "forum":
                assert re.search(r"last updated", e["description"], re.I), e["title"]
                assert re.search(r"zerologs\.bike", e["description"], re.I), e["title"]

    def test_the_page_date_convention_starts_at_246(self):
        """Measured, not assumed. The per-make forum rows of 242-244 label
        their evidence class ("Drawn from owner reporting, and labelled as
        such") but carry no page date; the generic layer's do. Two
        conventions in one corpus, recorded here rather than smoothed over,
        because a gate that asserts the newer rule corpus-wide would report
        a defect that is really a history."""
        dated = {n: [bool(re.search(r"last updated", e["description"], re.I))
                     for e in _entries(n) if e["source"] == "forum"]
                 for n in TRACK_L_FILES}
        per_make = ["known_issues_zero.json", "known_issues_livewire.json",
                    "known_issues_energica.json"]
        generic = ["known_issues_bms.json", "known_issues_inverter.json",
                   "known_issues_regen.json"]
        assert not any(any(dated[n]) for n in per_make), dated
        assert all(dated[n] and all(dated[n]) for n in generic), dated
        for n in per_make:
            for e in _entries(n):
                if e["source"] == "forum":
                    assert re.search(r"owner|community", e["description"], re.I), e["title"]

    def test_a_regulation_row_names_its_campaign_number(self):
        rows = [e for e in _entries("known_issues_inverter.json") if e["source"] == "regulation"]
        assert rows, "247 shipped the only regulation rows in Track L"
        for e in rows:
            assert re.search(r"\b\d{2}V-?\d{3}\b", _text(e)), e["title"]

    @pytest.mark.parametrize("name", sorted(TRACK_L_FILES))
    def test_every_listed_code_is_named_in_the_row_text(self, name):
        for e in _entries(name):
            for code in e.get("dtc_codes") or []:
                assert code in _text(e), (e["title"], code)

    def test_the_identity_is_unique_corpus_wide(self):
        seen = set()
        for f in sorted(K.glob("known_issues_*.json")):
            for e in _entries(f.name):
                identity = (e.get("make"), e.get("model"), e["title"])
                assert identity not in seen, identity
                seen.add(identity)

    def test_the_documented_count_matches_the_live_seed(self, gate_db):
        live = sum(len(_entries(f.name)) for f in K.glob("known_issues_*.json"))
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        m = re.search(r"(\d{3,4}) curated known issues", readme)
        assert m and int(m.group(1)) == live, (m and m.group(1), live)
        with get_connection(gate_db) as conn:
            assert conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0] == live


# ===========================================================================
# 7. Regression — a gate guards the gates before it
# ===========================================================================
class TestRegression:
    @pytest.mark.parametrize("gate_file", [
        "tests/test_phase174_gate8.py",
        "tests/test_phase184_gate9.py",
        "tests/test_phase205_gate11.py",
        "tests/test_phase240_gate12.py",
    ])
    def test_earlier_gate_still_passes(self, gate_file):
        """Gates 5, 6 and 7 are re-run by Gate 12, which is re-run here."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", gate_file, "-q", "-p", "no:cacheprovider",
             "-p", "no:xdist"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800,
        )
        assert result.returncode == 0, f"{gate_file} regressed:\n{result.stdout[-2000:]}"

