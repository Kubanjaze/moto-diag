"""Phase 244R — the DTC taxonomy can hold content.

`motodiag code --category engine` answered "No DTCs found in category
'engine'." over 29 engine codes. `knowledge/loader.py` built every `DTCCode`
without `dtc_category`, the field defaulted to `unknown`, and `add_dtc`
persisted it — one omitted keyword argument, the only production writer of
`dtc_codes`, 99 rows.

6,692 tests missed it because of where they looked. Three modules do load the
real seed corpus through the real loader (`test_phase05_dtc.py:117-147`,
`test_phase240_gate12.py:63`) and none asserts anything about the category;
every test of `--category` builds synthetic `DTCCode` objects with the field
passed by hand. The seam between authored data and the filter was never
crossed. These tests cross it: the corpus guard reads the shipped files, and
the command tests run the command a technician runs.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.core.config import SEED_DATA_DIR
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import (
    apply_pending_migrations,
    get_migration_by_version,
    rollback_to_version,
)
from motodiag.core.models import DTCCategory
from motodiag.knowledge.dtc_repo import get_dtcs_by_category
from motodiag.knowledge.loader import backfill_dtc_categories, load_dtc_directory

DTC_SEED = Path(SEED_DATA_DIR) / "dtc_codes"

# The six categories that exist for electric drivetrains. This phase does not
# author EV codes; see TestWhatThisPhaseDoesNotClaim.
EV_CATEGORIES = (
    "hv_battery", "motor", "inverter", "regen", "charging_port", "thermal",
)


def _seed_entries() -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for path in sorted(DTC_SEED.glob("*.json")):
        for entry in json.loads(path.read_text(encoding="utf-8")):
            out.append((path.name, entry))
    return out


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase244R.db")
    init_db(path)
    return path


@pytest.fixture
def seeded(db):
    load_dtc_directory(DTC_SEED, db)
    return db


@pytest.fixture
def cli_db(seeded, monkeypatch):
    from motodiag.core.config import reset_settings

    monkeypatch.setenv("MOTODIAG_DB_PATH", seeded)
    reset_settings()
    yield seeded
    reset_settings()


def _run(*args) -> str:
    from motodiag.cli.main import cli

    result = CliRunner().invoke(cli, list(args))
    assert result.exit_code == 0, result.output
    return result.output


# ---------------------------------------------------------------------------
# 1. The shipped corpus is classified
# ---------------------------------------------------------------------------


class TestTheSeedCorpusIsClassified:
    def test_the_corpus_is_the_size_it_was(self):
        """Pinned so a new file cannot arrive unclassified without saying so."""
        assert len(_seed_entries()) == 99

    @pytest.mark.parametrize("file_name,entry", _seed_entries(),
                             ids=[f"{f}:{e['code']}" for f, e in _seed_entries()])
    def test_every_entry_carries_a_real_category(self, file_name, entry):
        assert "dtc_category" in entry, f"{file_name}: {entry['code']} has no dtc_category"
        # Constructs, i.e. it is a member of the enum rather than free text.
        DTCCategory(entry["dtc_category"])

    def test_nothing_is_left_unknown(self):
        unknown = [
            f"{f}:{e['code']}" for f, e in _seed_entries()
            if e.get("dtc_category") == "unknown"
        ]
        assert not unknown, f"unclassified after 244R: {unknown}"

    def test_every_value_is_a_category_the_database_knows(self, db):
        """The join the CLI depends on, and nothing enforced it."""
        with get_connection(db) as conn:
            known = {r[0] for r in conn.execute(
                "SELECT category FROM dtc_category_meta"
            )}
        used = {e["dtc_category"] for _, e in _seed_entries()}
        assert used <= known, f"categories in no meta row: {sorted(used - known)}"


# ---------------------------------------------------------------------------
# 2. The loader reads it — and cannot destroy a make on a typo
# ---------------------------------------------------------------------------


class TestTheLoaderReadsIt:
    def test_the_real_corpus_loads_fully_classified(self, seeded):
        with get_connection(seeded) as conn:
            total, unknown = conn.execute(
                "SELECT COUNT(*), SUM(dtc_category = 'unknown') FROM dtc_codes"
            ).fetchone()
        assert total == 99
        assert unknown == 0, "the defect this phase fixes"

    def test_a_file_without_the_key_still_loads(self, db, tmp_path):
        """Read tolerantly, like every neighbouring field: making the key
        required would break four older fixture-based tests and change a
        contract this phase has no reason to change."""
        f = tmp_path / "legacy.json"
        f.write_text(json.dumps([
            {"code": "P9001", "description": "Legacy fixture entry",
             "category": "engine", "severity": "low", "make": "Fixture"},
        ]))
        from motodiag.knowledge.loader import load_dtc_file

        assert load_dtc_file(f, db) == 1
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT dtc_category FROM dtc_codes WHERE code = 'P9001'"
            ).fetchone()
        assert row[0] == "unknown"

    def test_a_bad_category_deletes_nothing(self, seeded, tmp_path):
        """Parse-then-write. The pre-delete commits in its own transaction, so
        a value that raises mid-insert would otherwise leave that make's codes
        deleted and not replaced."""
        from motodiag.knowledge.loader import load_dtc_file

        before = get_dtcs_by_category("engine", db_path=seeded)
        assert before, "fixture precondition"

        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps([
            {"code": before[0]["code"], "description": "x", "category": "engine",
             "dtc_category": "not-a-category", "make": before[0].get("make")},
        ]))
        with pytest.raises(ValueError):
            load_dtc_file(bad, seeded)

        after = get_dtcs_by_category("engine", db_path=seeded)
        assert [r["code"] for r in after] == [r["code"] for r in before]


# ---------------------------------------------------------------------------
# 3. The command a technician runs
# ---------------------------------------------------------------------------


def _populated_categories() -> list[str]:
    """Read at collection time, so it must tolerate an unclassified corpus:
    the guard that the corpus IS classified is a test, not an import error."""
    return sorted(
        {e.get("dtc_category", "unknown") for _, e in _seed_entries()}
        - {"unknown"}
    )


class TestTheCommandAnswers:
    @pytest.mark.parametrize("category", _populated_categories())
    def test_every_populated_category_returns_codes(self, cli_db, category):
        out = _run("code", "--category", category)
        assert "No DTCs found" not in out, f"{category} is populated but lists empty"
        assert "DTCs in category" in out

    def test_the_engine_category_the_bug_was_reported_on(self, cli_db):
        out = _run("code", "--category", "engine")
        assert "No DTCs found" not in out

    def test_an_invalid_category_says_so_and_lists_the_valid_ones(self, cli_db):
        from motodiag.cli.main import cli

        result = CliRunner().invoke(cli, ["code", "--category", "nonsense"])
        assert result.exit_code == 1
        assert "not a DTC category" in result.output
        assert "engine" in result.output and "emissions" in result.output

    def test_the_panel_and_the_list_agree_about_a_code(self, cli_db):
        """`motodiag code P0440` used to print the SYMPTOM category while
        `--category` narrowed on the DTC one, so a row was filed under a name
        its own panel never showed."""
        entry = next(e for _, e in _seed_entries() if e["code"] == "P0440")
        panel = _run("code", "P0440")
        assert entry["dtc_category"] in panel
        listed = _run("code", "--category", entry["dtc_category"])
        assert "P0440" in listed


class TestWhatThisPhaseDoesNotClaim:
    @pytest.mark.parametrize("category", EV_CATEGORIES)
    def test_the_ev_categories_are_empty_on_purpose(self, cli_db, category):
        """Empty because no EV DTC data exists — all eight seed files are
        internal-combustion makes — not because the filter is broken. Phase
        244R classifies what the corpus has and invents nothing. Roadmap row
        247 is what fills these, and it now has a column to fill."""
        from motodiag.cli.main import cli

        result = CliRunner().invoke(cli, ["code", "--category", category])
        assert result.exit_code == 0
        assert "No DTCs found" in result.output


# ---------------------------------------------------------------------------
# 4. The operator's existing rows
# ---------------------------------------------------------------------------


class TestMigration062:
    def test_it_says_what_it_is_for(self):
        text = get_migration_by_version(62).description
        assert "unknown" in text and "post_apply" in text
        assert "emissions" in text and "exhaust" in text

    def test_the_schema_version_moved_with_it(self):
        assert SCHEMA_VERSION >= 62  # f9-noqa: ssot-pin contract-pin: Phase 244R's own pin. Migration 062 classifies the 99 seeded dtc_codes rows that the loader had written as 'unknown', and rewrites the two dtc_category_meta descriptions that made `emissions` and `exhaust` claim the same faults. The literal is the point: importing the constant would make this assert x == x. WAS `== 62`, relaxed to `>= 62` at Phase 255 (migration 063, the transmission axis). The equality was only ever true while 062 was the head, so it asserted two things at once: that 244R's bump happened, and that nothing had happened since. The second was never this test's claim, and the first is what `>= 62` states — migration 062 is in the head and the constant never moved back below it. The SEVEN pins that DO want the exact head — 184_gate9, 240_gate12, 244D, 244I, 244M, 244N and 191b_serve_migrations — keep their equality form and were all bumped to 63 in the same commit. There are seven and not the three the first blast radius surfaced, because they sit in files a subsystem-scoped selection does not include; only the full regression finds them all, which is the same lesson 244M learned and wrote into 191b's own note.

    def test_it_classifies_rows_already_in_the_database(self, seeded):
        """The operator's case: rows written before the loader read the key."""
        with get_connection(seeded) as conn:
            conn.execute("UPDATE dtc_codes SET dtc_category = 'unknown'")
            ids_before = [r[0] for r in conn.execute(
                "SELECT id FROM dtc_codes ORDER BY id"
            )]
            changed = backfill_dtc_categories(conn)
        assert changed == 99
        with get_connection(seeded) as conn:
            unknown = conn.execute(
                "SELECT COUNT(*) FROM dtc_codes WHERE dtc_category = 'unknown'"
            ).fetchone()[0]
            ids_after = [r[0] for r in conn.execute(
                "SELECT id FROM dtc_codes ORDER BY id"
            )]
        assert unknown == 0
        assert ids_after == ids_before, (
            "ids must not churn — that is why this is an UPDATE and not a re-seed"
        )

    def test_running_it_twice_changes_nothing_the_second_time(self, seeded):
        with get_connection(seeded) as conn:
            conn.execute("UPDATE dtc_codes SET dtc_category = 'unknown'")
            first = backfill_dtc_categories(conn)
            second = backfill_dtc_categories(conn)
        assert first == 99
        assert second == 0, "Phase 244H: migrations do get applied twice"

    def test_it_leaves_rows_the_seed_does_not_mention_alone(self, seeded):
        with get_connection(seeded) as conn:
            conn.execute(
                "INSERT INTO dtc_codes (code, description, category, "
                "dtc_category, severity, make) VALUES "
                "('P9999', 'Operator-loaded code', 'engine', 'unknown', 'low', 'Mine')"
            )
            backfill_dtc_categories(conn)
            row = conn.execute(
                "SELECT dtc_category FROM dtc_codes WHERE code = 'P9999'"
            ).fetchone()
        assert row[0] == "unknown", "this migration has no opinion about a private file"

    def test_the_two_descriptions_no_longer_claim_the_same_faults(self, db):
        with get_connection(db) as conn:
            meta = dict(conn.execute(
                "SELECT category, description FROM dtc_category_meta "
                "WHERE category IN ('emissions', 'exhaust')"
            ).fetchall())
        assert "catalyst" in meta["emissions"].lower()
        assert "catalyst" not in meta["exhaust"].lower(), (
            "an authority that contradicts itself cannot settle where P0420 goes"
        )

    def test_rollback_restores_the_prior_state(self, seeded):
        rollback_to_version(61, seeded)
        c = sqlite3.connect(seeded)
        try:
            values = {r[0] for r in c.execute(
                "SELECT DISTINCT dtc_category FROM dtc_codes"
            )}
            emissions = c.execute(
                "SELECT description FROM dtc_category_meta WHERE category = 'emissions'"
            ).fetchone()[0]
        finally:
            c.close()
        assert values == {"unknown"}
        assert emissions == "Emissions system faults (O2, EVAP, PAIR, cat)"

    def test_forward_again_after_a_rollback(self, seeded):
        rollback_to_version(61, seeded)
        apply_pending_migrations(seeded)
        with get_connection(seeded) as conn:
            unknown = conn.execute(
                "SELECT COUNT(*) FROM dtc_codes WHERE dtc_category = 'unknown'"
            ).fetchone()[0]
        assert unknown == 0
