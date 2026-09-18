"""Phase 245 — Damon HyperSport / HyperFighter: nothing to write yet, and that is recorded.

Row 245 as written cannot be done honestly. As of 2026-09-18 Damon has
delivered no customer motorcycle (its own 2025-05-28 investor release puts
prototype production in Q1 2026 and mentions no deliveries), has published no
owner's or service manual, has no vehicle on NHTSA's record (products
endpoint, Count 0), and has no owner community. Phase 241's precedent: on a
file where the content cannot be sourced, the deliberate absence *is* the
content.

**The trigger.** Revisit — and flip these tests on purpose — when Damon ships
customer units *and* publishes an owner's manual. Not before.

**The trap.** Fabricated "owner reports" exist for this bike: `ev.care` says
it "launched in Canada/US in 2024" and lists regen-tuning, throttle-map and
"monsoon parking connector waterproofing" problems "addressed by OTA
updates", with no owner, date, region or source, contradicting the
manufacturer's own schedule. `ridereview.com` and a `bikenrider.com` "reaches
its first customers" post are the same shape. Under the 242 cadence every one
dies at the refuter. The last test here is what fails first if any of it is
ever ingested as a forum tip.

And the row's premise was wrong: Shift is adjustable ergonomics — windscreen,
pegs, bars and seat between a sport and a commuter position on a button —
not "smart suspension"; CoPilot is 77 GHz radar plus 1080p cameras feeding a
neural net, warning through windscreen LEDs and bar haptics. Both from press
coverage of Damon's CES 2020 prototype, which is all that has been shown.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.knowledge.loader import load_known_issues_file
from motodiag.knowledge.vehicle_resolver import resolve_vehicle

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
HV = K / "known_issues_electric_hv_safety.json"


@pytest.fixture
def db(tmp_path):
    """The corpus as seeded, in a copy: the HV floor is the only file that
    names Damon, and this fixture proves that by loading only it."""
    path = str(tmp_path / "phase245.db")
    init_db(path)
    load_known_issues_file(HV, path)
    return path


def _rows_naming_damon(db):
    with get_connection(db) as conn:
        return conn.execute(
            "SELECT make, model, source, year_start, year_end FROM known_issues "
            "WHERE lower(make) LIKE '%damon%'"
        ).fetchall()


class TestTheAbsenceIsDeliberate:
    def test_no_make_specific_entry_exists(self, db):
        """Zero rows with `make = 'Damon'`. The day this fails on purpose is
        the day the trigger in the module docstring has been met."""
        assert search_known_issues(make="Damon", db_path=db) == [] or all(
            "," in r["make"] for r in search_known_issues(make="Damon", db_path=db)
        ), "a Damon-specific entry exists — was the trigger met, and is it sourced?"

    def test_no_seed_file_is_named_for_damon(self):
        """242–244 each added `known_issues_<make>.json`. 245 does not."""
        assert not list(K.glob("*damon*")), "a Damon seed file appeared; see the trigger"

    def test_the_hv_floor_still_names_damon(self, db):
        """Phase 241's cross-make safety floor is the only thing that reaches a
        Damon owner today, and it must keep doing so."""
        rows = _rows_naming_damon(db)
        assert len(rows) >= 10
        assert all("Damon" in r[0] and "," in r[0] for r in rows), (
            "every row naming Damon should be the shared list-valued make"
        )

    def test_every_row_naming_damon_is_model_generated(self, db):
        """The trap. If a 'forum', 'owner' or 'service-manual' row naming
        Damon ever lands, it fails here before anything else — because no
        such source exists for a bike with no owners and no manual."""
        sources = {r[2] for r in _rows_naming_damon(db)}
        assert sources == {"model-generated"}, sources


class TestTheMarqueResolves:
    def test_the_make_resolves_exactly(self, db):
        """244F made list-valued makes queryable; Damon surfaces through the
        union. The make resolves; the model cannot, because no row carries one,
        and that is correct today."""
        identity = resolve_vehicle("Damon", "HyperSport", db_path=db)
        assert identity.make.resolved == "Damon"
        assert identity.make.method == "exact"
        assert identity.model.resolved is None
