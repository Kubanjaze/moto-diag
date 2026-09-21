"""Phase 256 — one chokepoint, and the fixtures that stop it being split.

Phase 255 filtered the door it knew about. Three more were found afterwards,
one at a time, each by someone noticing. This file asserts, per door, what
each machine must and must not receive — so the next door cannot be added,
or quietly unwired, without a named machine failing.

**Read the door-4 block with its history.** Door 4 leaks nothing today, and
it is safe for the wrong reason: it matches `LOWER(make) = ?`, exact string
equality, and nine of the eleven transmission-scoped rows carry
`make = "Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine"`, which is never
equal to `"yamaha"`. The 244C-244I substring defect on that door is acting as
accidental protection.

**Routing it through the resolver is what creates the exposure.** The moment
door 4 matches through the junction, an R1 becomes eligible for all nine. So
these fixtures are committed **before** the rewire: they pass now (nothing
scoped matches), they pass after (the filter withholds), and **they fail in
between** — which is what makes "filter and rewire land together" enforced
rather than written down.

A fixture green on both sides cannot tell the two reasons apart on its own,
so the rewire commit carries a positive control: remove the filter call,
watch these fail, restore it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"

#: The D8 matrix. `keeps_scoped` is the whole point: True means this machine
#: is entitled to transmission-scoped rows, False means receiving even one is
#: a defect. Each is named, so deleting one is a visible edit.
MACHINES = [
    ("Honda", "GL1800 Gold Wing", 2020, False, "ambiguous: manual or DCT, never CVT"),
    ("Honda", "CBR1000RR", 2019, False, "unknown: six-speed sportbike"),
    ("Honda", "Grom", 2022, False, "unknown: five-speed, the Step 0 poster child"),
    ("Honda", "Africa Twin", 2021, False, "ambiguous, column NULL: manual or DCT"),
    ("Yamaha", "YZF-R1", 2016, False, "unknown: six-speed, and a LIVE vehicle"),
    ("Kawasaki", "Ninja 400", 2020, False, "the isolating control: never had them"),
    ("Honda", "PCX 150", 2020, True, "model-sourced cvt: MUST keep them"),
]


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    from motodiag.core.config import reset_settings

    path = str(tmp_path_factory.mktemp("p256") / "p256.db")
    init_db(path)
    for f in sorted(SEED.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    with sqlite3.connect(path) as conn:
        for i, (mk, md, yr, _keep, _why) in enumerate(MACHINES, start=8100):
            conn.execute(
                "INSERT INTO vehicles (id, make, model, year) VALUES (?,?,?,?)",
                (i, mk, md, yr),
            )
    reset_settings()
    return path


def scoped_ids(db_path: str) -> set[int]:
    """Every row that declares anything on the transmission axis."""
    with sqlite3.connect(db_path) as conn:
        return {r[0] for r in conn.execute(
            "SELECT id FROM known_issues WHERE applicability IS NOT NULL"
        )}


def vehicle_id_of(db_path: str, make: str, model: str) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT id FROM vehicles WHERE make = ? AND model = ?", (make, model)
        ).fetchone()[0]


# --- the doors, each as the product actually calls it ----------------------
#
# Each returns (before_filter, after_filter) as id sets, so a test can ask
# what the FILTER did rather than what the twelve-row cap did. That
# distinction is not pedantry: a PCX 150 retrieves 165 rows of which 8 are
# transmission-scoped, and none of the 8 reaches the final twelve, because
# Phase 244S caps the prompt and PCX-specific rows outrank a generic CVT
# layer. Asserting "the PCX's prompt contains a scoped row" would fail on
# correct behaviour and tempt someone to loosen the filter to satisfy it.
# The property that matters is that the filter WITHHOLDS NOTHING from a
# machine entitled to them.


#: Wide enough that no door's own limit can hide a scoped row. A Gold Wing's
#: scoped rows sit at resolver positions 56, 64, 75, 81, 113 and 115, so any
#: fetch narrower than that makes a leak invisible and the guard useless —
#: which is exactly how door 4's first tripwire passed on leaking code.
GUARD_FETCH = 400


def door1_diagnose(db_path, make, model, year):
    """The diagnose/code path. Asserted pre-cap.

    The product caps this at twelve (`KNOWN_ISSUE_PROMPT_LIMIT`). The guard
    does not, because a cap is a presentation decision: raise it tomorrow
    and a property proved through it stops being proved.
    """
    from motodiag.knowledge.prompt_rows import compose_prompt_rows
    from motodiag.knowledge.transmission import resolve_transmission
    from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

    _identity, raw = known_issues_for_vehicle(make, model, db_path=db_path,
                                              limit=GUARD_FETCH)
    kept = compose_prompt_rows(raw, limit=GUARD_FETCH,
                               transmission=resolve_transmission(make, model))
    return {r["id"] for r in raw}, {r["id"] for r in kept}


def door2_ask(db_path, make, model, year):
    """The video /ask path. Asserted pre-cap, and that matters here.

    The endpoint fetches twenty-five. A Gold Wing's scoped rows start at
    position 56, so at twenty-five this door cannot leak them **whatever
    the filter does** — safety by arithmetic, not by design, and it
    evaporates the day someone raises the limit. The guard therefore fetches
    wide and asserts that the FILTER withholds them.
    """
    from motodiag.knowledge.prompt_rows import drop_inapplicable
    from motodiag.knowledge.transmission import resolve_transmission
    from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

    _identity, issues = known_issues_for_vehicle(make, model, db_path=db_path,
                                                 limit=GUARD_FETCH)
    kept = drop_inapplicable(issues, resolve_transmission(make, model))
    return {r["id"] for r in issues}, {r["id"] for r in kept}


def door4_priority(db_path, make, model, year):
    """Asserted BEFORE the five-row cap, deliberately.

    The first version of this helper read `_find_kb_matches_safe`, which
    caps at five. That made the tripwire useless: with the filter removed,
    a Gold Wing's scoped rows sit at resolver positions 56, 64, 75, 81, 113
    and 115, so the cap hid every one and the guard passed on leaking code.
    """
    from motodiag.shop.priority_scorer import _kb_candidates_for_vehicle
    from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

    vid = vehicle_id_of(db_path, make, model)
    _identity, raw = known_issues_for_vehicle(make, model, db_path=db_path,
                                              limit=GUARD_FETCH)
    after = {r["id"] for r in _kb_candidates_for_vehicle(vid, db_path)}
    return {r["id"] for r in raw}, after


DOORS = {
    "1-diagnose": door1_diagnose,
    "2-video-ask": door2_ask,
    "4-priority-scorer": door4_priority,
}


#: Split rather than skipped. A conditional `pytest.skip` inside a
#: parametrised matrix produces a skip count that reads as "18 tests did not
#: run" — and this project has a standing rule that a skip must stop a
#: close-out rather than vanish into a summary line. Two lists, no skips.
NOT_ENTITLED = [m for m in MACHINES if not m[3]]
ENTITLED = [m for m in MACHINES if m[3]]
_ids = lambda ms: [f"{m}-{d}" for m, d, _y, _k, _w in ms]


@pytest.mark.parametrize("door", sorted(DOORS))
class TestEveryDoorRespectsApplicability:
    @pytest.mark.parametrize("make,model,year,keeps_scoped,why", NOT_ENTITLED,
                             ids=_ids(NOT_ENTITLED))
    def test_a_machine_without_the_transmission_receives_no_scoped_row(
        self, db, door, make, model, year, keeps_scoped, why
    ):
        """The negative. Not 'fewer rows' — zero, named machine by named machine."""
        _before, after = DOORS[door](db, make, model, year)
        leaked = after & scoped_ids(db)
        assert leaked == set(), (
            f"door {door}: {make} {model} ({why}) received scoped row(s) "
            f"{sorted(leaked)}"
        )

    @pytest.mark.parametrize("make,model,year,keeps_scoped,why", MACHINES,
                             ids=_ids(MACHINES))
    def test_the_door_returns_something_at_all(
        self, db, door, make, model, year, keeps_scoped, why
    ):
        """Positive control for the negative above.

        Every "receives no scoped row" assertion also passes on a door that
        returns nothing whatsoever — which is precisely what door 4 did for
        its entire existence until F126 was fixed today. Without this, the
        negatives would be untestable by construction.
        """
        before, _after = DOORS[door](db, make, model, year)
        assert before, f"door {door} retrieved nothing at all for {make} {model}"

    @pytest.mark.parametrize("make,model,year,keeps_scoped,why", ENTITLED,
                             ids=_ids(ENTITLED))
    def test_an_entitled_machine_has_nothing_withheld(
        self, db, door, make, model, year, keeps_scoped, why
    ):
        """The filter must take nothing from a machine that may have it."""
        before, after = DOORS[door](db, make, model, year)
        scoped = scoped_ids(db)
        lost = (before & scoped) - after
        assert lost == set(), (
            f"door {door}: {make} {model} lost scoped row(s) {sorted(lost)} "
            "— the filter withheld from a machine entitled to them"
        )


class TestTheKawasakiControlIsUnmoved:
    """Step 0 isolated the cause with Kawasaki; it must stay at zero."""

    @pytest.mark.parametrize("door", sorted(DOORS))
    def test_zero_before_and_after(self, db, door):
        before, after = DOORS[door](db, "Kawasaki", "Ninja 400", 2020)
        assert before & scoped_ids(db) == set()
        assert after & scoped_ids(db) == set()
