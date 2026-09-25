"""Phase 258 — Gate 14: the scooter / small-displacement track through the real front doors.

Track M's closing gate. Roadmap row 258 names a path — "query scooter/small
bike → CVT + electrical + carb workflow" — so the gate's first duty is to
walk that path and report what a technician actually gets. Step 0 walked it
(`docs/phases/in_progress/258_step0.md`), and the headline is the opposite
of Gate 13's: **the path carries the track's content.** The three layers
(254's CVT, 354's scooter electrical, 353's small-engine carburettor) reach
the 12-row prompt for every machine all three cover, composition (250B)
answers the symptom, the transmission axis (255) withholds scoped CVT rows
from a manual Grom, and the chokepoint (256) sits under every door.

What the gate adds, and pins:

* **The SYM exception (F153).** The CVT rows pair SYM in the junction under
  `Jet 50` / `Joyride` / `Symply 125`, while 353 and 354 pair the same
  machines under `Jet Euro 50` / `Joyride 125` / `Fiddle 50`. No SYM
  scooter reaches a CVT row at tier 0; the CVT content that reaches the
  prompt arrives labelled `make_other_model`. The tests in
  `TestTheSymException` fail the day F153 closes.
* **The Fiddle 50 (F154).** `TRANSMISSION_LOOKUP` has no `fiddle 50`
  spelling, so a machine 354's own tests name at tier 0 resolves
  transmission `unknown` and the applicability filter withholds all 8
  scoped CVT rows from it.
* **The F155 displacement.** A belt-shaped symptom costs a Vespa LX 50 its
  own tier-0 carburettor row, because `relevance_tokens` does not stem
  plurals ("scooter" ≠ "scooters") and a tier-2 row sharing the word
  "belt" takes the reserved slot.
* **The gaps the 353 handoff told the gate to state rather than find:**
  an injected scooter gets no carburettor row and should get none; a
  carburetted Ruckus has no scooter-electrical row of its own and F149's
  three unverified `model = All` rows are its only charging content; the
  Ruckus carburettor row carries a 2012–2025 window (F132), so a 2008
  query gets nothing; a 2002–2006 Metropolitan is a CHF50 that reaches no
  CHF50 row under its own name (F156); no adapter is known for any scooter
  make (F157); no Track M make has a DTC file and no scooter row carries a
  DTC code.

House style from Gates 8, 9, 11, 12 and 13: every query goes through the
REAL CLI root or the HTTP API, never the repository layer; honest gaps are
pinned as executable documentation MEANT to fail the day someone fills
them; a gate guards the gates before it. Zero production code — the gate
reports, and each repair opens under its own finding.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
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
# CLI persists — the arrangement Phase 125 established and Gate 13 kept.
from tests.test_phase123_diagnose import (  # type: ignore[import-not-found]
    make_diagnose_fn,
    make_response,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = REPO_ROOT / "src" / "motodiag" / "knowledge" / "seed"
K = SEED / "knowledge"
DTC = SEED / "dtc_codes"
HW = REPO_ROOT / "src" / "motodiag" / "hardware" / "compat_data"

#: The makes the track's own content is filed under. Honda and Yamaha hold
#: their scooter content beside big-bike content; the other five exist in
#: this corpus only because Track M wrote them.
SCOOTER_MAKES = ("Kymco", "SYM", "Piaggio", "Vespa", "Genuine")
CONTENT_MAKES = SCOOTER_MAKES + ("Honda", "Yamaha")

#: Track M's six content files, with the provenance mix each phase shipped
#: (251, 252, 253, 254, 354, 353) and the row counts Step 0 measured.
TRACK_M_FILES = {
    "known_issues_vespa_piaggio.json": {"service-manual": 7, "regulation": 3},
    "known_issues_honda_small.json": {"service-manual": 9, "regulation": 4},
    "known_issues_yamaha_kymco_sym_genuine.json": {"service-manual": 9, "regulation": 5},
    "known_issues_cvt.json": {"service-manual": 10, "regulation": 3},
    "known_issues_scooter_electrical.json": {"service-manual": 7},
    "known_issues_small_engine_carbs.json": {"service-manual": 7},
}
TRACK_M_TOTAL = sum(sum(v.values()) for v in TRACK_M_FILES.values())  # 64

#: The three layers the row names, as title sets for classifying a prompt.
LAYER_FILES = {
    "CVT": "known_issues_cvt.json",
    "ELEC": "known_issues_scooter_electrical.json",
    "CARB": "known_issues_small_engine_carbs.json",
}

#: 254's own vocabulary (the terms its content tests pinned), plus 354's
#: and 353's — the maker's word, not the generic one.
LAYER_TERMS = [
    "variator", "weight roller", "clutch bell", "driven pulley",
    "primary sheave", "drive belt width",                 # 254
    "stator resistance", "regulator rectifier",          # 354
    "pilot screw", "auto by-starter",                     # 353
]

#: The machines the 353 handoff named as the gate's fixtures, plus the gap
#: machines it told the gate to state rather than find. Years chosen inside
#: each row's own window: the CHF50 rows cover 2002–2006, the Ruckus
#: carburettor row 2012–2025 (F132).
GARAGE_MACHINES = [
    ("Honda", "CHF50", 2005),
    ("Kymco", "Agility 50", 2015),
    ("Kymco", "People S 250", 2015),
    ("SYM", "Jet Euro 50", 2015),
    ("SYM", "Joyride 125", 2015),
    ("SYM", "Fiddle 50", 2015),
    ("Piaggio", "Fly 50", 2015),
    ("Vespa", "LX 50", 2015),
    ("Honda", "Ruckus", 2015),
    ("Honda", "Ruckus", 2008),
    ("Honda", "PCX150", 2014),
    ("Yamaha", "Zuma 125", 2018),
    ("Honda", "Metropolitan", 2005),
    ("Honda", "Grom 125", 2023),
    ("Yamaha", "Vino 50", 2015),
    ("Honda", "CBR1000RR", 2020),
]

BELT_SYMPTOM = "scooter jerks at low speed, belt squeal, won't pull away"
CHARGING_SYMPTOM = "battery not charging, lights dim at idle"

#: The layer census of the 12-row prompt, measured on a freshly seeded
#: database (Step 0, S0-2) under the belt symptom. The LX 50's missing
#: CARB is F155's displacement; the Fiddle 50's two CVT rows are the two
#: UNSCOPED ones, because its transmission resolves unknown (F154).
BELT_CENSUS = {
    ("Honda", "CHF50", 2005): {"CVT": 7, "CARB": 1, "ELEC": 1},
    ("Kymco", "Agility 50", 2015): {"CVT": 9, "CARB": 1, "ELEC": 1},
    ("Kymco", "People S 250", 2015): {"CVT": 9, "CARB": 1, "ELEC": 1},
    ("SYM", "Jet Euro 50", 2015): {"CVT": 7, "CARB": 1, "ELEC": 1},
    ("SYM", "Joyride 125", 2015): {"CVT": 7, "CARB": 1, "ELEC": 1},
    ("SYM", "Fiddle 50", 2015): {"CVT": 2, "CARB": 1, "ELEC": 1},
    ("Piaggio", "Fly 50", 2015): {"CVT": 6, "CARB": 1, "ELEC": 1},
    ("Vespa", "LX 50", 2015): {"CVT": 10, "ELEC": 1},          # F155
    ("Honda", "Ruckus", 2015): {"CVT": 4, "CARB": 1},
    ("Honda", "Ruckus", 2008): {"CVT": 4},                       # F132's window
    ("Honda", "PCX150", 2014): {"CVT": 7, "ELEC": 1},            # injected
    ("Yamaha", "Zuma 125", 2018): {"CVT": 8},                    # injected
    ("Honda", "Metropolitan", 2005): {"CVT": 6},                 # F156
    ("Honda", "Grom 125", 2023): {"CVT": 1},                     # the naming row
    ("Yamaha", "Vino 50", 2015): {"CVT": 5, "CARB": 1},
    ("Honda", "CBR1000RR", 2020): {"CVT": 1},                     # the naming row
}

#: Tier-0 junction pairs per gate machine, measured in Step 0. The SYM
#: machines hold exactly their electrical + carburettor rows (F153); the
#: Kymco control holds nine CVT rows beside them.
TIER0_PAIRS = {
    ("Honda", "CHF50"): 11,
    ("Kymco", "Agility 50"): 11,
    ("Kymco", "People S 250"): 11,
    ("SYM", "Jet Euro 50"): 2,
    ("SYM", "Joyride 125"): 2,
    ("SYM", "Fiddle 50"): 2,
    ("Piaggio", "Fly 50"): 4,
    ("Vespa", "LX 50"): 11,
    ("Honda", "Ruckus"): 5,
    ("Honda", "Metropolitan"): 7,
    ("Yamaha", "Zuma 125"): 15,
    ("Yamaha", "Vino 50"): 4,
    ("Honda", "PCX 150"): 12,
    ("Honda", "Grom 125"): 8,
}

#: F149's three `model = All`, `unverified` Honda charging rows, by title.
F149_TITLES = (
    "Regulator/rectifier failure — the universal Honda problem",
    "Stator failure diagnosis and replacement — all Honda models",
    "Charging system preventive testing — annual check protocol",
)

PROVENANCE = {"unverified", "model-generated", "forum",
              "service-manual", "mechanic-verified", "regulation"}

LABELS = ("service-manual", "forum", "regulation", "model-generated", "unverified")


def _entries(name: str) -> list[dict]:
    raw = json.loads((K / name).read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else next(v for v in raw.values() if isinstance(v, list))


def _layer_titles() -> dict[str, set[str]]:
    return {layer: {e["title"] for e in _entries(name)}
            for layer, name in LAYER_FILES.items()}


_TITLES = _layer_titles()


def _layer_of(row: dict) -> str | None:
    for layer, titles in _TITLES.items():
        if row.get("title") in titles:
            return layer
    return None


def _census(rows: list[dict]) -> Counter:
    return Counter(filter(None, (_layer_of(r) for r in rows)))


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
    import os

    path = str(tmp_path_factory.mktemp("gate14") / "gate14.db")
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
    import os

    os.environ["MOTODIAG_DB_PATH"] = gate_db
    reset_settings()
    with get_connection(gate_db) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) VALUES (?, ?, ?, 1)",
            ("gate14_owner", "gate14_owner@ex.com", "shop"),
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
    """The gate's machines, added through the real `garage add`. Returns
    {(make, model, year): vehicle_id}. The CLI has no `--transmission`
    option — the lookup is what covers these machines, which is exactly
    the arrangement the gate measures (and the Fiddle 50's undoing)."""
    from motodiag.core.config import reset_settings
    import os

    os.environ["MOTODIAG_DB_PATH"] = gate_db
    os.environ["COLUMNS"] = "240"
    reset_settings()
    ids = {}
    for make, model, year in GARAGE_MACHINES:
        _run(["garage", "add", "--make", make, "--model", model,
              "--year", str(year), "--engine-cc", "50"])
        with get_connection(gate_db) as conn:
            ids[(make, model, year)] = conn.execute(
                "SELECT id FROM vehicles WHERE make = ? AND model = ? AND year = ? "
                "ORDER BY id DESC LIMIT 1",
                (make, model, year),
            ).fetchone()[0]
    return ids


def _diagnose_and_capture(vehicle_id: int, symptoms: str) -> tuple[list[dict], str]:
    """Run the REAL `diagnose quick` with the AI call replaced, and return the
    known issues it handed the model plus the context string it built.

    Row 258's path ends at the model, so the gate walks to the prompt rather
    than calling the retrieval helper — a helper that returns the right rows
    while the command sends the wrong ones is exactly the bug Gate 11's rule
    exists to catch."""
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
# 1. Every scooter make answers through the CLI
# ===========================================================================
class TestEveryScooterMakeAnswersThroughTheCli:
    @pytest.mark.parametrize("make", CONTENT_MAKES)
    def test_kb_list_returns_rows_for_the_make(self, gate_db, make):
        out = _run(["kb", "list", "--make", make]).output
        assert "No known issues" not in out, out[-600:]
        assert any(label in out for label in LABELS), "the label must show beside the row"

    @pytest.mark.parametrize("make", ["Kymco", "SYM", "Piaggio", "Vespa"])
    def test_the_make_s_own_electrical_and_carburettor_rows_list(self, gate_db, make):
        """354 and 353 wrote one make-specific row per scooter make they
        read manuals for; the make filter must reach them under the make's
        own name."""
        out = _run(["kb", "list", "--make", make]).output
        assert "charging" in out.lower() or "regulator" in out.lower(), out[-800:]
        assert "carburet" in out.lower() or "by-starter" in out.lower(), out[-800:]

    def test_genuine_is_covered_only_by_the_cross_make_rows(self, gate_db):
        """The Damon shape, measured on Track M: Genuine is a make with no
        electrical and no carburettor row of its own — 353 and 354 read no
        Genuine manual — so its answer is 253's rows and the multi-make CVT
        rows. An honest gap, not a defect: filed as the record of what a
        Genuine owner reaches."""
        out = _run(["kb", "list", "--make", "Genuine", "--limit", "50"]).output
        assert "No known issues" not in out, out[-600:]
        for absent in ("Genuine carburet", "Genuine charging", "Two Genuine"):
            assert absent.lower() not in out.lower(), absent

    def test_kymcos_own_rows_do_not_cross_into_sym(self, gate_db):
        """The single-make rows must stay behind the make filter: SYM's own
        carburettor row is not Kymco's, and Kymco's charging row is not
        SYM's. The multi-make CVT rows are shared by design and are the
        F142 question, not this one."""
        kymco = _run(["kb", "list", "--make", "Kymco", "--limit", "50"]).output
        sym = _run(["kb", "list", "--make", "SYM", "--limit", "50"]).output
        assert "SYM carburetted scooters" not in kymco, kymco[-800:]
        assert "Two Kymco service manuals" not in sym, sym[-800:]

    def test_the_label_travels_with_the_content_rows(self, gate_db):
        """Track M's content rows are `service-manual` or `regulation` —
        anchored, unlike the 660 `unverified` rows around them."""
        out = _run(["kb", "list", "--make", "Vespa", "--limit", "50"]).output
        assert "service-manual" in out, out[-800:]
        assert "unverified" not in out or "model-generated" in out, out[-800:]


# ===========================================================================
# 2. The three layers are reachable by the commands people use
# ===========================================================================
class TestTheThreeLayersReachTheCommandsPeopleUse:
    @pytest.mark.parametrize("term", LAYER_TERMS)
    def test_kb_search_returns_the_layer_with_its_label(self, gate_db, term):
        out = _run(["kb", "search", term]).output
        assert term.lower() in out.lower(), out[-600:]
        assert any(label in out for label in LABELS), "the label travels with the row"

    def test_kb_by_symptom_reaches_the_cvt_layer_in_its_own_vocabulary(self, gate_db):
        """254's rule: the maker's own word. `weight roller` is what the
        service manuals print; `roller weight` is what an English speaker
        types."""
        out = _run(["kb", "by-symptom", "weight roller"]).output
        assert "roller" in out.lower(), out[-600:]

    def test_kb_by_symptom_reaches_the_carburettor_layer(self, gate_db):
        out = _run(["kb", "by-symptom", "pilot screw"]).output
        assert "pilot screw" in out.lower(), out[-600:]

    def test_kb_by_symptom_reaches_the_electrical_layer(self, gate_db):
        out = _run(["kb", "by-symptom", "scooter battery not charging"]).output
        assert "illumination coil" in out.lower() or "acg" in out.lower() \
            or "stator" in out.lower(), out[-600:]


# ===========================================================================
# 3. The diagnostic path — the row's own walk, pinned
# ===========================================================================
class TestTheDiagnosticPath:
    @pytest.mark.parametrize("make,model,year", [
        ("Honda", "CHF50", 2005), ("Kymco", "Agility 50", 2015),
        ("Kymco", "People S 250", 2015), ("Piaggio", "Fly 50", 2015),
    ], ids=["chf50", "agility-50", "people-s-250", "fly-50"])
    def test_all_three_layers_reach_the_prompt(self, gate_db, garage,
                                               make, model, year):
        """Step 0's headline, pinned: for the machines all three layers
        cover, one `diagnose quick` reaches CVT, electrical and carburettor
        content together. Gate 13's equivalent test failed for two of its
        four machines — the composition 250B built is what makes this one
        pass, so it stands as the gate's positive control."""
        known, _ctx = _diagnose_and_capture(garage[(make, model, year)], BELT_SYMPTOM)
        census = _census(known)
        assert {"CVT", "ELEC", "CARB"} <= set(census), (
            f"{make} {model}: a belt complaint reached {dict(census)}")

    def test_the_vespa_keeps_all_three_layers_under_a_charging_symptom(self, gate_db, garage):
        """The LX 50 is the fifth full-coverage machine, measured under the
        OTHER symptom because of F155: a belt-shaped symptom displaces its
        carburettor row (pinned below), a charging-shaped one does not."""
        known, _ctx = _diagnose_and_capture(
            garage[("Vespa", "LX 50", 2015)], CHARGING_SYMPTOM)
        census = _census(known)
        assert {"CVT", "ELEC", "CARB"} <= set(census), dict(census)

    @pytest.mark.parametrize("make,model,year", GARAGE_MACHINES,
                             ids=[f"{m}-{mo}-{y}" for m, mo, y in GARAGE_MACHINES])
    def test_the_prompt_is_filled_to_its_cap(self, gate_db, garage,
                                             make, model, year):
        """244S's cap is unchanged — composition, not enlargement. The one
        machine under it is the Fiddle 50, whose transmission resolves
        unknown and whose scoped CVT rows are withheld (F154); its 9 is
        pinned in TestTheSymException."""
        known, _ctx = _diagnose_and_capture(garage[(make, model, year)], BELT_SYMPTOM)
        expected_len = 9 if (make, model, year) == ("SYM", "Fiddle 50", 2015) else 12
        assert len(known) == expected_len, (
            f"{make} {model} {year}: {len(known)} rows reached the prompt")

    @pytest.mark.parametrize("make,model,year", GARAGE_MACHINES,
                             ids=[f"{m}-{mo}-{y}" for m, mo, y in GARAGE_MACHINES])
    def test_the_prompt_census_is_step0s_measurement(self, gate_db, garage,
                                                     make, model, year):
        """The full pin, per machine. Every count is Step 0's, taken on a
        freshly seeded database through the same chain; a change here means
        retrieval changed, and the census is the record of what changed.
        The LX 50's missing CARB is F155; the SYM machines' CVT counts are
        tier-2 rows reaching the cap (F153); the Grom's and the CBR's 1 is
        the unscoped naming row, by design."""
        known, _ctx = _diagnose_and_capture(garage[(make, model, year)], BELT_SYMPTOM)
        census = _census(known)
        assert census == Counter(BELT_CENSUS[(make, model, year)]), (
            f"{make} {model} {year}: {dict(census)}")

    def test_a_belt_symptom_costs_the_vespa_its_own_carburettor_row(self, gate_db, garage):
        """F155, pinned at the displacement Step 0 measured. `relevance_tokens`
        does not stem plurals, so the symptom token "scooter" scores 0
        against the tier-0 row titled "…carburetted scooters…", and tier-2
        CVT rows sharing the word "belt" take the reserved slots instead.
        This test FAILS the day F155 closes — that is its job."""
        known, _ctx = _diagnose_and_capture(garage[("Vespa", "LX 50", 2015)], BELT_SYMPTOM)
        assert "CARB" not in _census(known), (
            "the LX 50's carburettor row is back: F155 has closed, update this pin")
        assert "CVT" in _census(known), "the belt rows must still arrive"

    def test_a_charging_symptom_rescues_the_zumas_tier0_electrical_row(self, gate_db, garage):
        """S0-5, both directions. The YW125 row is tier 0 for the Zuma 125
        but rank order crowds it out of the cap under a belt symptom;
        250B's relevance reserve brings it in when the rider reports
        charging. Composition working as designed, measured both ways."""
        belt, _ctx = _diagnose_and_capture(garage[("Yamaha", "Zuma 125", 2018)], BELT_SYMPTOM)
        charging, _ctx = _diagnose_and_capture(garage[("Yamaha", "Zuma 125", 2018)], CHARGING_SYMPTOM)
        assert "ELEC" not in _census(belt), "the pin moved: re-measure"
        assert "ELEC" in _census(charging), (
            "a charging complaint must reach the machine's own charging row")

    def test_the_context_the_model_sees_carries_every_label(self, gate_db, garage):
        """246 Decision 3, re-run on the scooter half of the corpus: the
        label travels with the number, and the prompt is a display surface."""
        known, ctx = _diagnose_and_capture(garage[("Kymco", "Agility 50", 2015)], BELT_SYMPTOM)
        assert known and ctx
        for row in known:
            if row.get("source"):
                assert f"source: {row['source']}" in ctx, row["title"]


# ===========================================================================
# 4. The SYM exception — F153 and F154, pinned
#
# The 353 handoff left one question open on purpose: whether the SYM overlap
# machines also reach a CVT row at tier 0. Step 0 answered it: no. The CVT
# rows pair SYM in the junction under `Jet 50` / `Joyride` / `Symply 125`,
# spellings no query for Jet Euro 50 / Joyride 125 / Fiddle 50 resolves to.
# These tests fail the day F153 closes; the Fiddle's fail the day F154 does.
# ===========================================================================
class TestTheSymException:
    def test_the_tier0_pair_counts_are_step0s_measurement(self, gate_db):
        """The junction, measured directly: the SYM machines hold exactly
        their electrical + carburettor pairs, the Kymco control holds nine
        CVT rows beside them. Fails when F153's migration lands."""
        with get_connection(gate_db) as conn:
            for (make, model), count in TIER0_PAIRS.items():
                got = conn.execute(
                    "SELECT COUNT(*) FROM known_issue_models WHERE make = ? AND model = ?",
                    (make, model)).fetchone()[0]
                assert got == count, f"({make}, {model}): {got} pairs, pinned {count}"

    @pytest.mark.parametrize("make,model,year", [
        ("SYM", "Jet Euro 50", 2015), ("SYM", "Joyride 125", 2015)],
        ids=["jet-euro-50", "joyride-125"])
    def test_the_cvt_rows_reach_sym_only_as_another_models(self, gate_db, garage,
                                                            make, model, year):
        """F153: the CVT content reaches the SYM prompt — the cap admits
        tier-2 rows — but every CVT row arrives labelled `make_other_model`,
        while the machine's electrical and carburettor rows arrive at
        `model`. The day the spellings are fixed this fails: the CVT rows
        move to tier 0 and their tier label changes."""
        known, _ctx = _diagnose_and_capture(garage[(make, model, year)], BELT_SYMPTOM)
        cvt = [r for r in known if _layer_of(r) == "CVT"]
        assert cvt, "no CVT content reached the SYM prompt at all"
        assert all(r["match_tier"] == "make_other_model" for r in cvt), (
            "a CVT row reached tier 0 for an SYM machine: F153 has closed, "
            "update this pin")
        for r in known:
            if _layer_of(r) in ("ELEC", "CARB"):
                assert r["match_tier"] == "model", r["title"]

    def test_the_fiddle_resolves_unknown_and_loses_the_scoped_cvt_layer(self, gate_db, garage):
        """F154: `TRANSMISSION_LOOKUP`'s Fiddle entry carries `fiddle`,
        `fiddle iii`, `fiddle 3`, `fiddle3` — but not `fiddle 50`, the
        spelling the corpus's own electrical and carburettor rows use. The
        machine resolves transmission `unknown`, so the applicability filter
        withholds every `{"transmission": ["cvt"]}` row. The chokepoint
        records the cost in `retrieval_withheld`; this FAILS when the
        spelling is added."""
        from motodiag.knowledge.retrieval import withheld_report

        _diagnose_and_capture(garage[("SYM", "Fiddle 50", 2015)], BELT_SYMPTOM)
        report = withheld_report(db_path=gate_db, limit=200)
        rows = [r for r in report if r["make"] == "SYM" and r["model"] == "Fiddle 50"]
        assert rows, "the Fiddle 50 no longer resolves unknown: F154 has closed"
        assert all(r["provenance"] == "unknown" for r in rows), rows
        assert max(r["rows_withheld"] for r in rows) >= 8, rows

    def test_the_fiddles_prompt_holds_only_the_two_unscoped_cvt_rows(self, gate_db, garage):
        """The two CVT rows that survive F154's withholding are the ones with
        no applicability claim — the naming row and the recall-index row,
        whose scope is the search term, not the machine. 254's scoped
        roller, belt and clutch content never reaches this owner."""
        known, _ctx = _diagnose_and_capture(garage[("SYM", "Fiddle 50", 2015)], BELT_SYMPTOM)
        cvt_titles = {r["title"] for r in known if _layer_of(r) == "CVT"}
        assert cvt_titles == {
            "Three unrelated components are all called a drive belt, and a "
            "search for one returns the other two",
            "The regulator's two indexes contradict each other, and an "
            "empty recall answer is not a clean record",
        }, cvt_titles


# ===========================================================================
# 5. The gaps the handoff told the gate to state rather than find
# ===========================================================================
class TestTheGapsTheHandoffPredicted:
    def test_an_injected_honda_gets_electrical_but_no_carburettor_row(self, gate_db, garage):
        """The handoff: an injected scooter gets no carburettor row, and it
        should get none. The PCX150's prompt carries its electrical row and
        no carburettor row."""
        known, _ctx = _diagnose_and_capture(garage[("Honda", "PCX150", 2014)], BELT_SYMPTOM)
        census = _census(known)
        assert "ELEC" in census, "the PCX150's own charging row is missing"
        assert "CARB" not in census, census

    def test_the_carburettor_file_never_names_an_injected_scooter(self):
        """The seed-level half of the same statement: 353's file covers the
        carburetted machines only — no PCX, no Zuma 125, no Metropolitan of
        the injected era."""
        joined = " ".join(e.get("model") or "" for e in _entries(LAYER_FILES["CARB"]))
        for absent in ("PCX", "Zuma 125", "YW125"):
            assert absent not in joined, absent

    def test_an_injected_yamaha_gets_electrical_but_no_carburettor_row(self, gate_db, garage):
        known, _ctx = _diagnose_and_capture(garage[("Yamaha", "Zuma 125", 2018)], BELT_SYMPTOM)
        assert "CARB" not in _census(known), _census(known)

    def test_a_carburetted_ruckus_has_no_scooter_electrical_row_of_its_own(self, gate_db, garage):
        """The handoff's stated gap: the Ruckus is carburetted, 354 wrote no
        Ruckus row, and the only charging content its prompt carries is
        F149's three unverified `model = All` rows — which outrank nothing
        here because there is nothing else. Pinned as today's truth; this
        FAILS when F149 closes."""
        known, _ctx = _diagnose_and_capture(garage[("Honda", "Ruckus", 2015)], CHARGING_SYMPTOM)
        assert "CARB" in _census(known), "the Ruckus's carburettor row is missing"
        assert "ELEC" not in _census(known), "354 wrote no Ruckus row — re-measure"
        titles = {r["title"] for r in known}
        assert set(F149_TITLES) <= titles, (
            "F149's rows no longer reach a Ruckus prompt: F149 has closed, "
            "update this pin")

    def test_the_carburettor_row_reaches_inside_its_year_window_only(self, gate_db, garage):
        """F132's rule, at the row 353 actually shipped: the Ruckus
        carburettor row carries a 2012–2025 window, so a 2015 query gets it
        and a 2008 query does not. The gate tests inside the window and
        states the outside-window gap rather than finding it."""
        ruckus_2015, _ctx = _diagnose_and_capture(garage[("Honda", "Ruckus", 2015)], BELT_SYMPTOM)
        ruckus_2008, _ctx = _diagnose_and_capture(garage[("Honda", "Ruckus", 2008)], BELT_SYMPTOM)
        assert "CARB" in _census(ruckus_2015), "inside the window the row must arrive"
        assert "CARB" not in _census(ruckus_2008), "outside the window it must not"
        row = next(e for e in _entries(LAYER_FILES["CARB"]) if "Ruckus" in e.get("model", ""))
        assert (row.get("year_start"), row.get("year_end")) == (2012, 2025), row

    def test_a_manual_small_bike_gets_no_scoped_cvt_content(self, gate_db, garage):
        """The transmission axis (255) at work on the track's own machines:
        a Grom resolves `manual`, so every `{"transmission": ["cvt"]}` row
        is withheld from it, while its own eight Grom rows arrive — 252's
        steady-lamp row among them."""
        known, _ctx = _diagnose_and_capture(garage[("Honda", "Grom 125", 2023)], BELT_SYMPTOM)
        titles = " ".join(r["title"].lower() for r in known)
        for scoped in ("roller wear limit", "belt width", "engagement speed",
                       "weight roller"):
            assert scoped not in titles, scoped
        assert "grom" in titles, "the Grom's own rows must arrive"

    def test_a_big_bike_gets_none_of_the_three_layers_at_home_tiers(self, gate_db, garage):
        """The negative control: a CBR1000RR query reaches no tier-0 or
        tier-1 scooter content. The one CVT row in its prompt is 254's
        unscoped naming row, whose scope is the search term — the same
        row that reaches the Grom, pinned as by-design."""
        known, _ctx = _diagnose_and_capture(garage[("Honda", "CBR1000RR", 2020)], BELT_SYMPTOM)
        for r in known:
            if _layer_of(r) is not None:
                assert r["match_tier"] == "make_other_model", (r["title"], r["match_tier"])

    def test_a_2005_metropolitan_reaches_no_chf50_row(self, gate_db, garage):
        """F156: the 2002–2006 Metropolitan IS a CHF50 (252's finding,
        F152's cover), but the CHF50 carburettor and charging rows are
        modelled `CHF50` only and the junction holds no `(Honda,
        Metropolitan)` pair on them. What the owner gets instead: the CVT
        recall rows (which do list "Honda Metropolitan") at tier 0 and
        F149's unverified rows at tier 1. FAILS when F156's bridge lands."""
        known, _ctx = _diagnose_and_capture(garage[("Honda", "Metropolitan", 2005)], BELT_SYMPTOM)
        census = _census(known)
        assert "CARB" not in census and "ELEC" not in census, dict(census)
        assert "CVT" in census, "the recall rows that do name the Metropolitan must arrive"
        at_model = [r["title"] for r in known if r["match_tier"] == "model"]
        for title in at_model:
            assert "CHF50" not in title, "a CHF50 row reached the Metropolitan: F156 has closed"

    def test_the_two_unscoped_cvt_rows_reach_manual_bikes_by_design(self, gate_db, garage):
        """254 left two rows unscoped deliberately — the naming row (its
        subject is the search term "drive belt") and the recall-index row.
        They reach a manual Grom and a CBR at tier 2 under a belt-shaped
        symptom. Pinned so that the day someone scopes them, this fails
        and the scoping is a decision, not an accident."""
        for machine in (("Honda", "Grom 125", 2023), ("Honda", "CBR1000RR", 2020)):
            known, _ctx = _diagnose_and_capture(garage[machine], BELT_SYMPTOM)
            cvt = [r["title"] for r in known if _layer_of(r) == "CVT"]
            assert cvt == ["Three unrelated components are all called a drive "
                           "belt, and a search for one returns the other two"], cvt


# ===========================================================================
# 6. Cross-surface agreement
# ===========================================================================
class TestCrossSurfaceAgreement:
    @pytest.mark.parametrize("term", ["variator", "pilot screw", "stator resistance"])
    def test_the_api_finds_the_layer_the_cli_found(self, gate_db, api, term):
        cli = _run(["kb", "search", term]).output
        body = api.get("/v1/kb/search", params={"q": term}).json()
        assert term.split()[0].lower() in cli.lower()
        assert body["known_issues"], body

    def test_the_api_answers_for_every_scooter_make(self, gate_db, api):
        for make in SCOOTER_MAKES:
            body = api.get("/v1/kb/issues", params={"make": make, "limit": 5}).json()
            assert body["total"] > 0, (make, body)

    def test_the_cli_resolves_a_misspelt_make_and_the_api_does_not(self, gate_db, api):
        """F97, re-measured on the scooter makes: `kb list --make` runs the
        resolver and prints its correction; the API filters `make LIKE`
        with no resolution at all."""
        out = _run(["kb", "list", "--make", "Kymcoo"]).output
        assert "Kymco" in out, out[-600:]
        body = api.get("/v1/kb/issues", params={"make": "Kymcoo", "limit": 5}).json()
        assert body["total"] == 0, body

    @pytest.mark.parametrize("make", SCOOTER_MAKES)
    def test_the_cross_platform_carburettor_rows_reach_no_scooter_make(self, gate_db, api, make):
        """F151, at the door: the ten `cross_platform_carbs` rows are filed
        under one make and one large model each, so none reaches a Kymco,
        SYM, Piaggio, Vespa or Genuine owner on any surface. This FAILS the
        day someone scopes those rows honestly."""
        cp_titles = {e["title"] for e in _entries("known_issues_cross_platform_carbs.json")}
        body = api.get("/v1/kb/issues", params={"make": make, "limit": 200}).json()
        reached = {i["title"] for i in body["items"]} & cp_titles
        assert reached == set(), (make, reached)

    def test_the_kb_routes_are_key_gated(self, gate_db):
        client = TestClient(create_app(db_path_override=gate_db))
        assert client.get("/v1/kb/issues", params={"make": "Kymco"}).status_code == 401


# ===========================================================================
# 7. The honest gaps — what Track M knowingly lacks
#
# Each test pins a MEASURED absence and is written to fail when the absence
# is filled. A test that would still pass after the gap was closed is not
# documentation, it is decoration.
# ===========================================================================
class TestTheHonestGaps:
    @pytest.mark.parametrize("slug", ["kymco", "sym", "piaggio", "vespa",
                                      "genuine", "honda", "yamaha"])
    def test_no_track_m_make_has_a_dtc_file(self, slug):
        """The directory holds aprilia, bmw, ducati, generic, harley_davidson,
        ktm, mv_agusta and triumph only — no Track M make, Honda and
        Yamaha included, even though 253 measured that Kymco and SYM show
        fault codes on the dash under their own vocabulary."""
        assert not (DTC / f"{slug}.json").exists()

    def test_the_only_codes_a_scooter_row_carries_are_honda_blink_codes(self):
        """Measured over the track's six files: exactly one row rides on
        `dtc_codes` — 252's GROM125 code table, in Honda's own pair format
        (7-1 … 54-2). No Track M row carries an SAE OBD code, which is why
        `kb by-code P0300` answers nothing for a scooter: 254's finding,
        corpus-wide."""
        import re

        sae = re.compile(r"^[PUBC][0-9A-Z]{3,4}$")
        coded = []
        for name in TRACK_M_FILES:
            for e in _entries(name):
                assert not any(sae.match(str(c)) for c in (e.get("dtc_codes") or [])), (
                    name, e["title"])
                if e.get("dtc_codes"):
                    coded.append((name, e["title"]))
        assert coded == [("known_issues_honda_small.json",
                          "The eleven codes a GROM125 can show — and the one "
                          "pair Honda printed inverted")], coded

    def test_kb_by_code_reaches_the_grom_s_own_blink_codes(self, gate_db):
        """The positive control for the code above: Honda's pair format is
        reachable through the front door, so the absence elsewhere is a
        corpus fact, not a broken command."""
        out = _run(["kb", "by-code", "9-1"]).output
        assert "GROM125" in out, out[-600:]

    def test_no_scooter_row_is_reached_by_an_obd_code(self, gate_db):
        out = _run(["kb", "by-code", "P0300"]).output
        for name in TRACK_M_FILES:
            for e in _entries(name):
                assert e["title"][:40] not in out, e["title"][:40]

    @pytest.mark.parametrize("make,model", [
        ("Kymco", "Agility 50"), ("SYM", "Jet Euro 50"),
        ("Piaggio", "Fly 50"), ("Vespa", "LX 50"),
        ("Yamaha", "Zuma 125"), ("Genuine", "Buddy 125"),
    ], ids=["agility-50", "jet-euro-50", "fly-50", "lx-50",
            "zuma-125", "buddy-125"])
    def test_no_adapter_is_known_for_a_scooter_make(self, gate_db, make, model):
        """F157, one half: Kymco, SYM, Piaggio, Vespa, Genuine — and Yamaha's
        scooters against its model-scoped rows — answer "none known", while
        Track M's own rows document scooter diagnostic surfaces (251's
        six-pin Piaggio connector, 253's Kymco and SYM dash codes). FAILS
        the day compat rows land."""
        out = _run(["hardware", "compat", "recommend", "--make", make,
                    "--model", model]).output
        assert "No compat entries known" in out, out[-600:]

    @pytest.mark.parametrize("make,model", [
        ("Honda", "Ruckus"), ("Honda", "CHF50"),
    ], ids=["ruckus", "chf50"])
    def test_a_honda_scooter_inherits_only_the_dev_test_mock(self, gate_db, make, model):
        """F157, the other half, measured on a SEEDED catalogue: a Honda
        scooter query inherits the make-level "Mock Adapter (dev/test
        only)" — Honda's 13 rows are big-bike rows, and no real adapter is
        named for any scooter. The mock IS the honest answer today; the
        day a real scooter adapter lands this fails, which is the point."""
        out = _run(["hardware", "compat", "recommend", "--make", make,
                    "--model", model]).output
        assert "Mock Adapter (dev/test only)" in out, out[-600:]
        for row in out.splitlines():
            if "│" in row and "Mock Adapter" not in row \
                    and "Recommended" not in row and "───" not in row:
                assert "adapter" not in row.lower(), row

    def test_the_compat_store_holds_no_scooter_make(self):
        rows = json.loads((HW / "compat_matrix.json").read_text(encoding="utf-8"))
        makes = {r["make"].lower() for r in rows}
        assert not ({m.lower() for m in SCOOTER_MAKES} & makes), makes


# ===========================================================================
# 8. Track M's corpus invariants, re-run against the live seed
# ===========================================================================
class TestTrackMCorpusInvariants:
    def test_provenance_vocabulary_is_the_six_values(self):
        seen = set()
        for f in K.glob("known_issues_*.json"):
            seen |= {e.get("source", "unverified") for e in _entries(f.name)}
        assert seen <= PROVENANCE, seen

    @pytest.mark.parametrize("name", sorted(TRACK_M_FILES))
    def test_each_track_m_file_ships_the_provenance_mix_its_phase_claimed(self, name):
        assert Counter(e["source"] for e in _entries(name)) == Counter(TRACK_M_FILES[name])

    def test_track_m_is_sixty_four_rows(self):
        assert sum(len(_entries(n)) for n in TRACK_M_FILES) == TRACK_M_TOTAL

    def test_eleven_of_thirteen_cvt_rows_are_transmission_scoped(self):
        """254's applicability decision, re-run: the two unscoped rows are
        the naming row and the recall-index row, and they are named so a
        future scoping is a visible decision (its pin is in class 5)."""
        rows = _entries("known_issues_cvt.json")
        scoped = [e for e in rows if e.get("applicability") == {"transmission": ["cvt"]}]
        unscoped = [e for e in rows if e.get("applicability") is None]
        assert len(scoped) == 11 and len(unscoped) == 2, (len(scoped), len(unscoped))
        assert {e["title"] for e in unscoped} == {
            "Three unrelated components are all called a drive belt, and a "
            "search for one returns the other two",
            "The regulator's two indexes contradict each other, and an "
            "empty recall answer is not a clean record",
        }

    def test_every_regulation_row_names_its_campaign_number(self):
        """The format Track M's campaigns print: `\\d{2}V\\d{6}`. Every
        regulation row across the track's six files names at least one —
        251's four brake campaigns, 252's miniMOTO pair, 253's five, 254's
        sheave campaign."""
        import re
        rx = re.compile(r"\b\d{2}V\d{6}\b")
        for name in TRACK_M_FILES:
            for e in _entries(name):
                if e["source"] == "regulation":
                    text = " ".join(str(e.get(k) or "") for k in
                                    ("title", "description", "fix_procedure"))
                    assert rx.search(text), (name, e["title"][:50])

    def test_the_identity_is_unique_corpus_wide(self):
        seen = set()
        for f in sorted(K.glob("known_issues_*.json")):
            for e in _entries(f.name):
                identity = (e.get("make"), e.get("model"), e["title"])
                assert identity not in seen, identity
                seen.add(identity)

    def test_the_documented_count_matches_the_live_seed(self, gate_db):
        """The corpus the seed builds is the corpus the live database holds:
        1,060 rows, the figure the 353 handoff recorded for the live
        database after the 353 deploy."""
        live = sum(len(_entries(f.name)) for f in K.glob("known_issues_*.json"))
        assert live == 1060, live
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        import re
        m = re.search(r"(\d{3,4}) curated known issues", readme)
        assert m and int(m.group(1)) == live, (m and m.group(1), live)
        with get_connection(gate_db) as conn:
            assert conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0] == live


# ===========================================================================
# 9. Regression — a gate guards the gates before it
# ===========================================================================
class TestRegression:
    def test_gate_13_still_passes(self):
        """Gate 13 re-runs Gates 8, 9, 11 and 12, so they are guarded
        transitively — the deviation Gate 13 itself recorded for 5, 6 and
        7. Re-running the chain again would add four more pytest subprocesses
        to every regression for a guarantee already held."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_phase250_gate13.py",
             "-q", "-p", "no:cacheprovider", "-p", "no:xdist"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800,
        )
        assert result.returncode == 0, f"Gate 13 regressed:\n{result.stdout[-2000:]}"

    def test_the_schema_is_at_least_the_one_the_gate_ran_on(self):
        """A floor, not a head pin (F124). As first written this asserted
        `SCHEMA_VERSION == 66`, and F124's guard failed the regression of
        record: a literal equal to the head must be edited by every later
        migration and catches nothing the canonical pin in
        test_phase240c_severity_ordering.py does not. That this phase
        shipped no migration is shown by its diff (no src/ change), not by
        a test. This asserts only that the head never drops below the
        schema Gate 14 ran against."""
        from motodiag.core.database import SCHEMA_VERSION
        assert SCHEMA_VERSION >= 66
