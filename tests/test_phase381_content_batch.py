"""Phase 381 — the content batch on the row key.

The operator's choices (2026-10-08): "1A. 2A, with the alias window
2002–2007 … 3A, and file the "research library" finding. 4A." What this file
holds, beside Gate 14's inverted pins (F153, F156, F149) and 354's and 262's
moved ones:

* **F156, the dated alias:** a 2002–2007 Metropolitan reaches the CHF50 rows
  at tier 0 when the year is known, a 2018 one and a yearless one do not, and
  every door that fetches rows passes the year.
* **Migration 086:** its generated data equals the seed by key; it changes a
  row only where the old text is still held; F149's three rows are in no seed.
* **The parity check** refuses a removed row whose key is still a seed entry.
* **F158, widened:** each removed word is caught when planted, "census" is
  not, a row's key is not read, and the two rendered data files are clean.
"""

from __future__ import annotations

import ast
import json
import pathlib
import sqlite3
import sys

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.core.migration_086_rows import (
    CHANGED_ROWS_086, RETIRED_PAIRS_086, RETIRED_ROWS_086)
from motodiag.knowledge.issues_repo import add_known_issue
from motodiag.knowledge.vehicle_resolver import dated_alias, known_issues_for_vehicle

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "motodiag"
SEED = SRC / "knowledge" / "seed" / "knowledge"
sys.path.insert(0, str(ROOT / "scripts"))

import f158_census as F  # noqa: E402
from test_phase358_deploy_contract import D  # noqa: E402

F149_KEYS = {
    "honda-regulator-rectifier-failure-the-universal-honda-problem",
    "honda-stator-failure-diagnosis-and-replacement-all-honda-models",
    "honda-charging-system-preventive-testing-annual-check-protocol",
}


def _seed_entries() -> dict[str, dict]:
    out = {}
    for f in sorted(SEED.glob("known_issues_*.json")):
        for e in json.loads(f.read_text(encoding="utf-8")):
            out[e["key"]] = e
    return out


# --- F156: the dated alias -------------------------------------------------

class TestTheDatedAlias:
    @pytest.mark.parametrize("year,code", [
        (2001, None), (2002, "CHF50"), (2005, "CHF50"), (2007, "CHF50"),
        (2008, None), (2018, None), (None, None)])
    def test_the_window_is_2002_to_2007(self, year, code):
        assert dated_alias("Honda", "Metropolitan", year) == code

    def test_spelling_and_make_are_matched_loosely_and_only_for_honda(self):
        assert dated_alias("honda", "METROPOLITAN", 2005) == "CHF50"
        assert dated_alias("Yamaha", "Metropolitan", 2005) is None
        assert dated_alias("Honda", "Ruckus", 2005) is None

    @pytest.fixture
    def db(self, tmp_path):
        from motodiag.knowledge.marques import rebuild_make_index_at
        from motodiag.knowledge.models import rebuild_model_index_at

        path = str(tmp_path / "alias.db")
        init_db(path)
        add_known_issue("The CHF50 row", "d", make="Honda", model="CHF50", key="chf50",
                        db_path=path)
        add_known_issue("The Metropolitan row", "d", make="Honda", model="Metropolitan",
                        key="metro", db_path=path)
        add_known_issue("The Ruckus row", "d", make="Honda", model="Ruckus", key="ruckus",
                        db_path=path)
        rebuild_make_index_at(path)
        rebuild_model_index_at(path)
        return path

    def _tiers(self, db, year):
        _, rows = known_issues_for_vehicle("Honda", "Metropolitan", db_path=db, year=year)
        return {r["row_key"]: r["match_tier"] for r in rows}

    def test_a_2005_metropolitan_reaches_both_names_at_tier_0(self, db):
        assert self._tiers(db, 2005) == {
            "chf50": "model", "metro": "model", "ruckus": "make_other_model"}

    @pytest.mark.parametrize("year", [None, 2018])
    def test_a_2018_or_yearless_metropolitan_reaches_only_its_own_name(self, db, year):
        assert self._tiers(db, year) == {
            "chf50": "make_other_model", "metro": "model", "ruckus": "make_other_model"}


class TestEveryDoorPassesTheYear:
    """Wiring: the alias does nothing at a door that drops the year. Read
    from the AST, so a new caller that forgets it fails here."""

    def test_every_call_of_the_resolver_passes_year(self):
        callers = []
        for path in SRC.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "known_issues_for_vehicle"):
                    callers.append((path.relative_to(SRC).as_posix(),
                                    any(k.arg == "year" for k in node.keywords)))
        assert sorted(callers) == [("api/routes/videos.py", True),
                                   ("cli/diagnose.py", True),
                                   ("shop/priority_scorer.py", True)]

    def test_diagnose_passes_the_vehicle_year(self, monkeypatch, tmp_path):
        from motodiag.cli import diagnose

        db = str(tmp_path / "d.db")
        init_db(db)
        seen = {}

        def fake(make, model, **kw):
            seen.update(kw)
            raise RuntimeError("stop here")

        monkeypatch.setattr(diagnose, "known_issues_for_vehicle", fake)
        diagnose._load_known_issues("Honda", "Metropolitan", 2005, db_path=db)
        assert seen.get("year") == 2005


# --- Migration 086 -----------------------------------------------------------

class TestMigration086Data:
    def test_every_new_value_is_the_seeds(self):
        seed = _seed_entries()
        for key, field, _old, new in CHANGED_ROWS_086:
            want = seed[key][field]
            got = json.loads(new) if isinstance(want, list) else new
            assert got == want, (key, field)

    def test_every_old_value_differs_from_the_new(self):
        assert all(old != new for _k, _f, old, new in CHANGED_ROWS_086)

    def test_f149s_three_rows_are_retired_and_in_no_seed(self):
        assert {r["row_key"] for r in RETIRED_ROWS_086} == F149_KEYS
        assert not F149_KEYS & set(_seed_entries())
        assert {p[1] for p in RETIRED_PAIRS_086} <= {r["id"] for r in RETIRED_ROWS_086}

    def test_no_honda_scooter_gets_an_unverified_all_charging_row(self):
        """F149's close: no seed row of make Honda, model All and source
        unverified is about the charging system."""
        for e in _seed_entries().values():
            if e.get("make") == "Honda" and e.get("model") == "All":
                assert not any(w in e["title"].lower()
                               for w in ("stator", "regulator", "charging")), e["title"]

    def test_the_dtc_and_checklist_edits_match_what_ships(self, tmp_path):
        from motodiag.core.migrations import _CHECKLIST_086, _DTC_086
        from motodiag.knowledge.loader import load_dtc_file

        mv = json.loads((SRC / "knowledge" / "seed" / "dtc_codes" / "mv_agusta.json")
                        .read_text(encoding="utf-8"))
        p0328 = next(e for e in mv if e["code"] == "P0328")
        assert any(_DTC_086[0][4] in c for c in p0328["common_causes"])
        db = str(tmp_path / "fresh.db")
        init_db(db)
        load_dtc_file(SRC / "knowledge" / "seed" / "dtc_codes" / "mv_agusta.json", db)
        with get_connection(db) as conn:
            for slug, seq, field, old, new in _CHECKLIST_086:
                text = conn.execute(
                    f"SELECT c.{field} FROM checklist_items c JOIN workflow_templates t"
                    " ON t.id = c.template_id WHERE t.slug = ? AND c.sequence_number = ?",
                    (slug, seq)).fetchone()[0]
                assert new in text and old not in text.replace(new, ""), slug
            causes = conn.execute("SELECT common_causes FROM dtc_codes WHERE code = 'P0328'"
                                  " AND make = 'MV Agusta'").fetchone()[0]
            assert "this project" not in causes and "MotoDiag could open" in causes

    def test_item_18_no_longer_names_a_cause(self, tmp_path):
        """F171: the cited KTM page gives the remedy, not the cause."""
        db = str(tmp_path / "fresh.db")
        init_db(db)
        with get_connection(db) as conn:
            text = conn.execute(
                "SELECT c.diagnosis_if_fail FROM checklist_items c JOIN workflow_templates t"
                " ON t.id = c.template_id WHERE t.slug = 'ppi_chassis_v1'"
                " AND c.sequence_number = 2").fetchone()[0]
        assert "loose adjustment" not in text
        assert text.startswith("The KTM manual notes that running with play")


class TestTheRetirementAndItsRollback:
    """F149's three rows leave with their junction pairs, and the rollback
    restores them only where their seed file was held (a sibling row)."""

    def _db(self, tmp_path, *, sibling: bool) -> str:
        from motodiag.core.migrations import _RETIRED_SIBLING_086

        path = str(tmp_path / "r.db")
        init_db(path)
        if sibling:
            add_known_issue("PGM-FI blink codes", "d", make="Honda", key=_RETIRED_SIBLING_086,
                            db_path=path)
        with get_connection(path) as conn:
            for row in RETIRED_ROWS_086:
                conn.execute("INSERT INTO known_issues (id, row_key, title, description, make)"
                             " VALUES (?, ?, ?, 'd', 'Honda')",
                             (row["id"], row["row_key"], row["title"]))
                conn.execute("INSERT INTO known_issue_makes (issue_id, make) VALUES (?, 'Honda')",
                             (row["id"],))
        return path

    def _keys(self, path):
        with get_connection(path) as conn:
            return {r[0] for r in conn.execute("SELECT row_key FROM known_issues")}

    def test_the_forward_sql_deletes_the_rows_and_their_pairs(self, tmp_path):
        from motodiag.core.migrations import _sql_086

        path = self._db(tmp_path, sibling=True)
        with get_connection(path) as conn:
            conn.executescript(_sql_086(reverse=False))
            ids = [r["id"] for r in RETIRED_ROWS_086]
            assert conn.execute(f"SELECT COUNT(*) FROM known_issue_makes WHERE issue_id IN"
                                f" ({','.join('?' * len(ids))})", ids).fetchone()[0] == 0
        assert not self._keys(path) & F149_KEYS

    def test_the_rollback_restores_them_where_the_seed_was_held(self, tmp_path):
        from motodiag.core.migrations import _sql_086

        path = self._db(tmp_path, sibling=True)
        with get_connection(path) as conn:
            conn.executescript(_sql_086(reverse=False))
            conn.executescript(_sql_086(reverse=True))
        assert F149_KEYS <= self._keys(path)

    def test_the_rollback_adds_nothing_where_the_seed_was_never_held(self, tmp_path):
        from motodiag.core.migrations import _sql_086

        path = str(tmp_path / "empty.db")
        init_db(path)
        with get_connection(path) as conn:
            conn.executescript(_sql_086(reverse=True))
        assert self._keys(path) == set()


class TestContent086ChangesOnlyHeldText:
    def _db(self, tmp_path, text):
        key, field, old, new = next(c for c in CHANGED_ROWS_086 if c[1] == "description")
        path = str(tmp_path / "held.db")
        init_db(path)
        add_known_issue("t", text(old), make="Honda", key=key, db_path=path)
        return path, key, old, new

    def test_the_old_text_is_replaced_by_the_seeds(self, tmp_path):
        from motodiag.knowledge.loader import content_086

        path, key, _old, new = self._db(tmp_path, lambda old: old)
        with get_connection(path) as conn:
            content_086(conn)
            assert conn.execute("SELECT description FROM known_issues WHERE row_key = ?",
                                (key,)).fetchone()[0] == new

    def test_a_row_edited_since_is_left_alone(self, tmp_path):
        from motodiag.knowledge.loader import content_086

        path, key, _old, _new = self._db(tmp_path, lambda old: old + " An edit since.")
        with get_connection(path) as conn:
            content_086(conn)
            assert conn.execute("SELECT description FROM known_issues WHERE row_key = ?",
                                (key,)).fetchone()[0].endswith("An edit since.")


# --- The parity check, for removed rows -----------------------------------------

def _removed_diff(key: str) -> dict:
    return {"known_issues": {"cols": ["id", "row_key", "title"], "added": [], "changed": [],
                             "removed": [7], "a": {7: (7, 7, key, "t")}, "b": {}}}


def _build_with(keys):
    def build(path):
        c = sqlite3.connect(path)
        c.execute("create table known_issues (id integer primary key, row_key text, title text)")
        c.executemany("insert into known_issues (row_key, title) values (?, 't')",
                      [(k,) for k in keys])
        c.commit()
        c.close()
    return build


class TestParityForRemovedRows:
    def _copy(self, tmp_path):
        p = tmp_path / "copy.db"
        _build_with([])(p)
        return p

    def test_a_removed_key_still_in_the_seed_is_a_scope_problem(self, tmp_path):
        probs = D.seed_parity(tmp_path, self._copy(tmp_path), _removed_diff("gone"),
                              build=_build_with(["gone"]))
        assert probs == ["seed parity: removed row_key 'gone' is still a seed entry"]

    def test_a_removed_key_the_seed_dropped_passes(self, tmp_path):
        assert D.seed_parity(tmp_path, self._copy(tmp_path), _removed_diff("gone"),
                             build=_build_with(["kept"])) == []


# --- F158, widened ------------------------------------------------------------------

def _db_with(tmp_path, description: str, key: str = "k") -> pathlib.Path:
    p = tmp_path / "c.db"
    c = sqlite3.connect(p)
    c.execute("create table known_issues (id integer primary key, row_key text,"
              " make text, description text)")
    c.execute("insert into known_issues (row_key, make, description) values (?, 'Honda', ?)",
              (key, description))
    c.commit()
    c.close()
    return p


class TestTheWidenedCensus:
    @pytest.mark.parametrize("planted,pattern", [
        ("Measured for this project.", "this project"),
        ("Not known when this file was written.", "this file"),
        ("A refuter caught it.", "refut"),
        ("The corpus carries it.", "corpus"),
        ("A research pass proposed it.", "research pass")])
    def test_each_removed_word_is_caught(self, tmp_path, planted, pattern):
        hits = F.build_references(_db_with(tmp_path, planted))
        assert [h[3] for h in hits] == [pattern]

    def test_census_in_its_ordinary_sense_is_kept(self, tmp_path):
        assert F.build_references(_db_with(tmp_path, "A sample and not a census.")) == []

    def test_a_rows_key_is_not_read(self, tmp_path):
        p = _db_with(tmp_path, "clean", key="zero-hv-work-and-this-corpus-does")
        assert F.census(p) == []

    def test_logged_model_answers_are_operational(self, tmp_path):
        p = tmp_path / "g.db"
        c = sqlite3.connect(p)
        c.execute("create table guidance_interactions (id integer primary key,"
                  " response_json text)")
        c.execute("insert into guidance_interactions (response_json) values"
                  " ('{\"note\": \"the corpus says\"}')")
        c.commit()
        c.close()
        assert len(F.census(p)) == 1 and F.build_references(p) == []

    @pytest.mark.parametrize("rel", [
        "advanced/data/parts.json",
        "hardware/compat_data/adapters.json",
        "hardware/compat_data/compat_matrix.json"])
    def test_the_rendered_data_files_carry_no_build_reference(self, rel):
        """F158's three data files: rendered by `advanced parts show` and
        `hardware compat show`. compat_matrix.json's one F-number is the BMW
        F650, a model."""
        found = []
        for entry in json.loads((SRC / rel).read_text(encoding="utf-8")):
            for value in entry.values():
                if not isinstance(value, str):
                    continue
                for name, pat in F.PATTERNS.items():
                    found += [m.group() for m in pat.finditer(value)
                              if not (name == "F-number" and m.group() in F.BMW_F_MODELS)]
        assert found == []
