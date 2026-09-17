"""F86 — a recall lookup that cannot be performed must not read as an all-clear.

Filed after Phase 244R's sweep as "30 real NHTSA recalls ship and nothing loads
them; seed them". Assessing it inverted the fix. **The 30 entries are not real.**
This project's own audit established it with git provenance
(`docs/phases/completed/TRACK_K_AUDIT_VERIFIER_NOTES.md:508`): every `nhtsa_id`
sits on a synthetic {19,20,21,22}V x {012,123,…,901} x {000,500} grid, from one
commit, never touched. Phase 155's doc called them "real NHTSA campaigns"
anyway, and that audit's recommended remedy — label the fixture honestly — was
never applied.

So seeding them is the one thing not to do: a fabricated federal campaign number
carries authority, and a `critical` row floors a prediction's severity
(`advanced/predictor.py:417-430`).

What was actually broken is what the commands say when the table is empty:
`check-vin` and `lookup` printed a green "Clear ✓" panel — the same border, icon
and words a genuinely clear bike gets. And `mark-resolved` against a recall id
that does not exist wrote nothing and reported that it was **already resolved**,
telling a technician the work was on file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.advanced.recall_repo import (
    RecallNotFoundError,
    count_recalls,
    load_recalls_from_json,
    mark_resolved,
)
from motodiag.core.database import get_connection, init_db
from motodiag.core.models import ProtocolType, VehicleBase
from motodiag.vehicles.registry import add_vehicle

SEED = Path(__file__).resolve().parent.parent / "src/motodiag/advanced/data/recalls.json"


@pytest.fixture
def garage(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    db = str(tmp_path / "f86.db")
    init_db(db)
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()
    add_vehicle(
        VehicleBase(make="Harley-Davidson", model="Road King", year=2021,
                    engine_cc=1746, protocol=ProtocolType.CAN),
        db_path=db,
    )
    yield db
    reset_settings()


def _run(*args):
    from motodiag.cli.main import cli

    return CliRunner().invoke(cli, list(args))


def _flat(text: str) -> str:
    """Panel text wraps across box-drawn lines; compare on the words alone."""
    import re

    stripped = re.sub(r"[│╭╮╰╯─]", " ", text)
    return re.sub(r"\s+", " ", stripped).strip()


# ---------------------------------------------------------------------------
# 1. An empty corpus cannot clear a motorcycle
# ---------------------------------------------------------------------------


class TestAnEmptyCorpusIsNotAnAllClear:
    def test_the_table_is_empty_to_begin_with(self, garage):
        assert count_recalls() == 0, "nothing seeds recalls, by design — see F86"

    def test_check_vin_says_the_lookup_could_not_be_performed(self, garage):
        """A 2021 Harley VIN — inside the sample file's brake campaign range,
        had it been loaded, and inside a real one for all anyone knows."""
        out = _flat(_run("advanced", "recall", "check-vin", "1HD1KHC15MB123456").output)
        assert "NOT an all-clear" in out
        assert "No open recalls for this VIN" not in out

    def test_lookup_says_the_same(self, garage):
        out = _flat(_run(
            "advanced", "recall", "lookup",
            "--make", "Harley-Davidson", "--model", "Road King", "--year", "2021",
        ).output)
        assert "NOT an all-clear" in out
        assert "No recalls for" not in out

    def test_it_says_why_and_what_to_do(self, garage):
        out = _flat(_run("advanced", "recall", "check-vin", "1HD1KHC15MB123456").output)
        assert "not filed NHTSA campaigns" in out, "the fixture's nature must be stated"
        assert "manufacturer or NHTSA directly" in out, "somewhere real to go"

    def test_a_loaded_corpus_still_clears_a_bike_that_is_clear(self, garage):
        """The warning must not replace the real negative. With data loaded, a
        bike outside every campaign's year range gets the green panel it
        deserves — 1995 predates all 30 sample campaigns."""
        load_recalls_from_json(str(SEED), db_path=garage)
        assert count_recalls() == 30
        out = _flat(_run(
            "advanced", "recall", "lookup",
            "--make", "Honda", "--model", "CBR1000RR", "--year", "1995",
        ).output)
        assert "No recalls for" in out
        assert "NOT an all-clear" not in out


# ---------------------------------------------------------------------------
# 2. "Already resolved" must mean it is
# ---------------------------------------------------------------------------


class TestARecallThatDoesNotExist:
    def test_the_repo_raises_instead_of_reporting_success(self, garage):
        with pytest.raises(RecallNotFoundError):
            mark_resolved(vehicle_id=1, recall_id=999, db_path=garage)

    def test_nothing_is_written(self, garage):
        with pytest.raises(RecallNotFoundError):
            mark_resolved(vehicle_id=1, recall_id=999, db_path=garage)
        with get_connection(garage) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM recall_resolutions"
            ).fetchone()[0] == 0

    def test_the_command_says_so_and_fails(self, garage):
        result = _run(
            "advanced", "recall", "mark-resolved",
            "--bike", "king-2021", "--recall-id", "999",
        )
        assert result.exit_code == 1
        assert "No recall with id 999" in result.output
        assert "already marked resolved" not in result.output

    def test_a_real_duplicate_is_still_idempotent(self, garage):
        """The other IntegrityError — UNIQUE(vehicle_id, recall_id) — keeps its
        meaning: the work is recorded, say so, write nothing twice."""
        load_recalls_from_json(str(SEED), db_path=garage)
        with get_connection(garage) as conn:
            rid = conn.execute("SELECT id FROM recalls LIMIT 1").fetchone()[0]
        assert mark_resolved(vehicle_id=1, recall_id=rid, db_path=garage) == 1
        assert mark_resolved(vehicle_id=1, recall_id=rid, db_path=garage) == 0

        result = _run(
            "advanced", "recall", "mark-resolved",
            "--bike", "king-2021", "--recall-id", str(rid),
        )
        assert result.exit_code == 0
        assert "already marked resolved" in result.output


# ---------------------------------------------------------------------------
# 3. The fixture says what it is
# ---------------------------------------------------------------------------


class TestTheSampleDataIsLabelled:
    def test_the_loader_says_the_ids_are_illustrative(self):
        assert load_recalls_from_json.__doc__ is not None
        doc = load_recalls_from_json.__doc__
        assert "illustrative sample data" in doc
        assert "not filed campaigns" in doc

    def test_the_ids_really_are_on_the_synthetic_grid(self):
        """Pins the audit's finding so nobody re-labels the file as real
        without first replacing its contents."""
        entries = json.loads(SEED.read_text(encoding="utf-8"))
        assert len(entries) == 30
        tails = {e["nhtsa_id"][3:] for e in entries}
        assert tails <= {
            "012000", "123000", "234000", "345000", "456000",
            "567000", "678000", "789000", "890000", "901000",
            "012500", "123500", "234500", "345500", "456500",
            "567500", "678500", "789500", "890500", "901500",
        }, "if these are now real campaign ids, this guard should be deleted"

    def test_nothing_in_the_product_seeds_them(self):
        """The fix for F86 is NOT to load this file. If a caller appears, it
        must be a deliberate decision with real data behind it."""
        src = Path(__file__).resolve().parent.parent / "src"
        callers = [
            f"{p.relative_to(src)}:{i}"
            for p in src.rglob("*.py")
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if "load_recalls_from_json(" in line
            and "def load_recalls_from_json" not in line
        ]
        assert callers == [], f"something now seeds the sample recalls: {callers}"
