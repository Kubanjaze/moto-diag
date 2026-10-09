"""Phase 358, K4 — the F158 ratchet: build references in user-visible text
may only fall, and workflow rows carry none.

The database is built the way `motodiag db init` builds one (migrations,
then the DTC, symptom and known-issue seed loaders, then the marque index),
never read from data/motodiag.db.

**What it sees and what it cannot.** Measured at Step 0: a built database
carries 75 of live's 79 hits. The 5 live-only hits are in `shops` and
`customer_notifications`, operational rows no seed holds; 1 built-only hit
is a seed row (the Honda thermostat, "Phase 243") newer than live's copy,
because loading the seed does not rewrite an existing live row. The ratchet
holds the seed; the live rows are the deploy script's census, on a copy.
"""

from __future__ import annotations

import pathlib
import shutil
import sqlite3
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import f158_census as F  # noqa: E402

#: The count on a database built from this tree's seed. Measured 2026-09-27
#: (Phase 358 Step 0 and build): 75 hits over every text column, four
#: patterns. It may only fall; when a content phase removes references, it
#: lowers this in the same commit. Phase 359 removed the 44 build references
#: ("Phase N", "this phase"): 75 -> 31, every one a BMW F-series model name.
F158_CEILING = 31


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> pathlib.Path:
    from motodiag.core.config import SEED_DATA_DIR
    from motodiag.core.database import init_db
    from motodiag.knowledge.loader import (load_dtc_directory, load_known_issues_file,
                                           load_symptom_file)
    from motodiag.knowledge.marques import rebuild_make_index_at
    from motodiag.knowledge.models import rebuild_model_index_at

    db = tmp_path_factory.mktemp("f158") / "built.db"
    init_db(str(db))
    load_dtc_directory(SEED_DATA_DIR / "dtc_codes", str(db))
    load_symptom_file(SEED_DATA_DIR / "knowledge" / "symptoms.json", str(db))
    for f in sorted((SEED_DATA_DIR / "knowledge").glob("known_issues_*.json")):
        load_known_issues_file(f, str(db))
    rebuild_make_index_at(str(db))
    rebuild_model_index_at(str(db))
    return db


def _planted(src: pathlib.Path, tmp_path: pathlib.Path, sql: str) -> pathlib.Path:
    dst = tmp_path / "planted.db"
    shutil.copy(src, dst)
    c = sqlite3.connect(dst)
    c.execute(sql)
    c.commit()
    c.close()
    return dst


class TestTheRatchet:
    def test_the_count_equals_the_ceiling(self, built):
        hits = F.census(built)
        assert F.ratchet(hits, F158_CEILING) == [], F.report(hits)

    def test_the_database_is_the_whole_seed(self, built):
        """The ratchet is only as good as the build: every seed row loaded."""
        c = sqlite3.connect(built)
        # 1057 since Phase 381 retired F149's three rows.
        assert c.execute("select count(*) from known_issues").fetchone()[0] >= 1057
        assert c.execute("select count(*) from checklist_items").fetchone()[0] >= 100
        c.close()

    def test_the_build_is_db_inits_build(self, built, tmp_path):
        """`db init` ends by rebuilding the model junction. A second rebuild
        of the built database must change nothing (Phase 359, bug fix #2:
        the fixture skipped it, and its junction differed from live's by
        116 and 327 rows)."""
        from motodiag.knowledge.models import rebuild_model_index_at

        q = "select issue_id, make, model from known_issue_models order by 1, 2, 3"
        c = sqlite3.connect(built)
        before = c.execute(q).fetchall()
        c.close()
        again = tmp_path / "again.db"
        shutil.copy(built, again)
        rebuild_model_index_at(str(again))
        c = sqlite3.connect(again)
        assert c.execute(q).fetchall() == before
        c.close()


class TestTheExclusions:
    """Phase 359: what the ceiling still counts is model names, not build
    references. The rule excludes an F-number hit only when its token is a
    BMW F-series name in a BMW row; each exclusion has a control."""

    def test_the_seed_carries_no_build_reference(self, built):
        assert F.build_references(built) == []

    def test_every_remaining_hit_is_a_bmw_model_name(self, built):
        hits = F.census(built)
        assert len(hits) == F158_CEILING
        assert {h[3] for h in hits} == {"F-number"}
        assert {h[4] for h in hits} <= F.BMW_F_MODELS

    def test_a_finding_number_in_a_bmw_row_is_kept(self, built, tmp_path):
        db = _planted(built, tmp_path, "update known_issues set description = description"
                      " || ' See F158.' where rowid = (select min(rowid) from known_issues"
                      " where make like '%BMW%')")
        assert [h[4] for h in F.build_references(db)] == ["F158"]

    def test_a_bmw_model_name_is_excluded(self, built, tmp_path):
        db = _planted(built, tmp_path, "update known_issues set description = description"
                      " || ' Fits the F800 too.' where rowid = (select min(rowid) from known_issues"
                      " where make like '%BMW%')")
        # The census sees the plant ("F800GS" would not do: no word boundary
        # before the G, so the pattern never matches it), and the rule drops it.
        assert len(F.census(db)) == F158_CEILING + 1
        assert F.build_references(db) == []

    def test_a_model_name_outside_a_bmw_row_is_kept(self, built, tmp_path):
        db = _planted(built, tmp_path, "update known_issues set description = description"
                      " || ' Like an F800.' where rowid = (select min(rowid) from known_issues"
                      " where make not like '%BMW%')")
        assert [h[4] for h in F.build_references(db)] == ["F800"]

    def test_an_operational_row_is_reported_not_counted_as_content(self, built, tmp_path):
        """Live's 'Phase 199 Smoke Shop' is a shop's name, user data: the
        census sees it, and the content rule leaves it out."""
        c = sqlite3.connect(built)
        cols = [r for r in c.execute("pragma table_info(shops)")]
        c.close()
        required = [r[1] for r in cols if r[3] and r[4] is None and not r[5]]
        values = ", ".join("'Phase 199 Smoke Shop'" if n == "name" else "'x'" for n in required)
        db = _planted(built, tmp_path, f"insert into shops ({', '.join(required)}) values ({values})")
        assert len(F.census(db)) == F158_CEILING + 1
        assert F.build_references(db) == []

    def test_a_phase_reference_is_caught(self, built, tmp_path):
        db = _planted(built, tmp_path, "update known_issues set fix_procedure = fix_procedure"
                      " || ' (Phase 999)' where rowid = (select min(rowid) from known_issues)")
        assert [h[4] for h in F.build_references(db)] == ["Phase 999"]


class TestItsControls:
    def test_the_census_finds_a_planted_hit(self, built):
        assert F.plant_control(str(built))

    def test_a_new_reference_breaks_it(self, built, tmp_path):
        db = _planted(built, tmp_path, "update known_issues set description = description"
                      " || ' See Track Q.' where rowid = (select min(rowid) from known_issues)")
        fails = F.ratchet(F.census(db), F158_CEILING)
        assert fails and "above the ceiling" in fails[0]

    def test_a_workflow_row_may_carry_none(self, built, tmp_path):
        db = _planted(built, tmp_path, "update checklist_items set description = 'as F158 said'"
                      " where rowid = (select min(rowid) from checklist_items)")
        fails = F.ratchet(F.census(db), F158_CEILING + 1)
        assert any("workflow rows" in f for f in fails), fails

    def test_a_fall_must_lower_the_ceiling(self, built):
        hits = F.census(built)
        fails = F.ratchet(hits[1:], F158_CEILING)
        assert fails and f"lower F158_CEILING to {F158_CEILING - 1}" in fails[0]

    @pytest.mark.parametrize("text,pattern", [
        ("added in Phase 243", "Phase N"), ("see Track N", "Track X"),
        ("filed as F166", "F-number"), ("This phase adds it", "this phase")])
    def test_each_pattern_is_seen(self, tmp_path, text, pattern):
        db = tmp_path / "one.db"
        c = sqlite3.connect(db)
        c.execute("create table t (v TEXT)")
        c.execute("insert into t values (?)", (text,))
        c.commit()
        c.close()
        assert [h[3] for h in F.census(db)] == [pattern]
