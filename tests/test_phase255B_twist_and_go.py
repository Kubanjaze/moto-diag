"""Phase 255B — the twist-and-go side, and the row edits Phase 256 deferred.

Phase 255 built the transmission axis; 254 wrote twelve scooter-CVT rows
before there was one. 256 found four rows that name a machine their own
`applicability` excludes and deferred three repairs here. This file guards
those repairs and the content rows written alongside them.

Two things in this file are easy to get backwards, so they are stated once:

* **Withdrawing a claim is not granting one.** 4609 dropped `Filly LX 50`
  because the Kymco Agility service manual prints that name only in the
  recycled header of 21 of its 183 pages. The Filly does not thereby
  receive 4609 — it is absent from the transmission lookup, resolves
  `unknown`, and the fail-closed filter withholds a `{cvt}` row from it
  before and after. `test_the_filly_still_does_not_receive_4609` is the
  guard that keeps anyone from "completing" this fix by adding a lookup
  entry nobody sourced.

* **A seed edit to `make`, `model` or `title` does not update a row.**
  Those three columns are the UNIQUE identity index, and `add_known_issue`
  upserts `ON CONFLICT DO NOTHING`, so a re-seed inserts a second row and
  leaves the first. Filed as F129, not fixed here, and demonstrated by
  `test_a_reseed_after_an_identity_edit_duplicates_rather_than_updates`.
  It is why migration 065 edits by UPDATE instead of by re-seeding.
"""

from __future__ import annotations

import json
import sqlite3
import pathlib
from pathlib import Path

import pytest

from motodiag.core.database import init_db
from motodiag.knowledge.applicability import row_applies
from motodiag.knowledge.loader import load_known_issues_file, reconcile_255B_rows
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.knowledge.transmission import resolve_transmission

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "src" / "motodiag" / "knowledge" / "seed" / "knowledge"
CVT_SEED = SEED_DIR / "known_issues_cvt.json"

#: Title prefixes. Row ids are seed-order-relative and differ between a
#: fresh fixture and the operator's database, so nothing here keys on one.
T_4609 = "A Kymco service manual gives four CVT figures twice"

#: 4609's model column as Phase 254 shipped it, and as it stands after
#: 255B. The difference is the whole of commit 1.
MODEL_4609_AS_SHIPPED = "Agility 50, Agility 125, People S 250, People 250, Filly LX 50"
MODEL_4609_AFTER = "Agility 50, Agility 125, People S 250, People 250"

T_4605 = "Three unrelated components are all called a drive belt"

#: F115. The marques whose owners produce the `drive belt` collision but
#: which 4605's make column did not reach. Measured from the corpus, not
#: chosen: see _255B_MAKE_EDITS in knowledge/loader.py.
MAKE_4605_AS_SHIPPED = "Piaggio, Vespa, Honda, Yamaha, Kymco, SYM, Genuine"
MAKE_4605_AFTER = MAKE_4605_AS_SHIPPED + ", Harley-Davidson, BMW, LiveWire"
MARQUES_ADDED_F115 = ("Harley-Davidson", "BMW", "LiveWire")

#: The rows Phase 255B adds — the general half of each split.
_255B_ADDED = (
    "The regulator's two indexes contradict each other, and an empty recall answer is not a clean record",
)


@pytest.fixture(scope="module")
def seeded(tmp_path_factory) -> str:
    """A database seeded from the whole knowledge corpus, as shipped."""
    path = str(tmp_path_factory.mktemp("p255B") / "p255B.db")
    init_db(path)
    for f in sorted(SEED_DIR.glob("known_issues_*.json")):
        load_known_issues_file(f, path)
    rebuild_make_index_at(path)
    rebuild_model_index_at(path)
    return path


def _row(conn, title_prefix: str) -> dict:
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM known_issues WHERE title LIKE ?", (title_prefix + "%",))]
    assert len(rows) == 1, f"expected exactly one row for {title_prefix!r}, got {len(rows)}"
    return rows[0]


class TestRow4609DropsTheFilly:
    """The over-claim is withdrawn. The retrieval is unchanged."""

    def test_the_seed_row_no_longer_names_the_filly(self):
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        hits = [e for e in entries if e["title"].startswith(T_4609)]
        assert len(hits) == 1
        assert "Filly" not in hits[0]["model"], hits[0]["model"]
        assert hits[0]["model"] == MODEL_4609_AFTER

    def test_no_seed_file_anywhere_names_the_filly(self):
        """Scope and count stated, not a first screenful.

        Vocabulary is the maker's own spelling, `Filly` — the string the
        Agility manual's recycled header prints. Positive control below
        proves the search can find a model name that IS present.
        """
        named = [p.name for p in sorted(SEED_DIR.glob("*.json"))
                 if "Filly" in p.read_text(encoding="utf-8")]
        assert named == [], f"{len(named)} of {len(list(SEED_DIR.glob('*.json')))} files: {named}"

        control = [p.name for p in sorted(SEED_DIR.glob("*.json"))
                   if "Agility 50" in p.read_text(encoding="utf-8")]
        assert control, "positive control failed: 'Agility 50' should still be present"

    def test_the_junction_no_longer_carries_the_filly(self, seeded):
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4609)
            models = {m for (m,) in conn.execute(
                "SELECT model FROM known_issue_models WHERE issue_id = ?", (row["id"],))}
        assert "Filly LX 50" not in models
        assert "Agility 50" in models, "positive control: the junction is populated"

    def test_the_filly_still_does_not_receive_4609(self, seeded):
        """The correction that matters. Dropping the name grants nothing.

        The Filly is absent from the transmission lookup, so it resolves
        `unknown` — every candidate open — and `row_applies` is False for a
        `{cvt}` row under the fail-closed rule. That was true before this
        phase and is true after. If this test ever fails, someone has added
        a lookup entry for the Filly that no document supports.
        """
        res = resolve_transmission("Kymco", "Filly LX 50")
        assert res.provenance == "unknown"
        assert res.entry is None

        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4609)
        assert json.loads(row["applicability"]) == {"transmission": ["cvt"]}
        assert row_applies(row, "transmission", res.candidates) is False

        sourced = resolve_transmission("Kymco", "Agility 50")
        assert sourced.provenance == "model-sourced"
        assert row_applies(row, "transmission", sourced.candidates) is True


class TestMigration065EditsByIdentity:
    """F129's consequence, handled rather than tripped over."""

    def _legacy(self, tmp_path) -> str:
        """A database holding 4609 as it shipped, with the Filly."""
        path = str(tmp_path / "legacy.db")
        init_db(path)
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        hits = [e for e in entries if e["title"].startswith(T_4609)]
        assert len(hits) == 1
        # Set the shipped value explicitly rather than appending: an append
        # against a seed that still carried the Filly would build
        # "Filly LX 50, Filly LX 50" and this fixture would pass while
        # proving nothing.
        assert "Filly" not in hits[0]["model"], "the seed still names the Filly"
        hits[0]["model"] = MODEL_4609_AS_SHIPPED
        stale = tmp_path / "known_issues_cvt.json"
        stale.write_text(json.dumps(entries), encoding="utf-8")
        load_known_issues_file(stale, path)
        rebuild_make_index_at(path)
        rebuild_model_index_at(path)
        return path

    def test_a_reseed_after_an_identity_edit_duplicates_rather_than_updates(self, tmp_path):
        """F129, demonstrated. This is why the hook exists.

        Not a guard on 255B's own code — a pin on the defect 255B works
        around. If this starts failing, F129 has been fixed and the hook
        can be reconsidered.
        """
        path = self._legacy(tmp_path)
        with sqlite3.connect(path) as conn:
            before = conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0]

        load_known_issues_file(CVT_SEED, path)  # the edited seed

        with sqlite3.connect(path) as conn:
            after = conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0]
            dupes = conn.execute(
                "SELECT COUNT(*) FROM known_issues WHERE title LIKE ?", (T_4609 + "%",)
            ).fetchone()[0]
        assert after == before + 1, "a re-seed after an identity edit should insert, not update"
        assert dupes == 2, "both the old and the new row are present — that is F129"

    def test_the_hook_updates_in_place_and_keeps_the_id(self, tmp_path):
        path = self._legacy(tmp_path)
        with sqlite3.connect(path) as conn:
            before_id = _row(conn, T_4609)["id"]
            before_n = conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0]

            changed = reconcile_255B_rows(conn)
            assert changed == 1, f"expected one row changed, got {changed}"

            row = _row(conn, T_4609)
            after_n = conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0]
            models = {m for (m,) in conn.execute(
                "SELECT model FROM known_issue_models WHERE issue_id = ?", (row["id"],))}

        assert row["id"] == before_id, "the hook must not churn known_issues.id"
        assert after_n == before_n, "the hook must not insert"
        assert "Filly" not in row["model"]
        assert "Filly LX 50" not in models, "the hook must rebuild the derived junction"

    def test_the_hook_is_idempotent(self, tmp_path):
        path = self._legacy(tmp_path)
        with sqlite3.connect(path) as conn:
            assert reconcile_255B_rows(conn) == 1
            assert reconcile_255B_rows(conn) == 0, "a second run must match nothing"
            _row(conn, T_4609)  # still exactly one


T_4615_CVT = "What the regulator record shows for scooter CVTs"
T_4615_GENERAL = ("The regulator's two indexes contradict each other, and an "
                  "empty recall answer is not a clean record")


class TestRow4615Splits:
    """The regulator-index methodology was never about CVTs.

    4615 declared `{cvt}` over two claims: one genuinely about scooter CVT
    campaigns, and one about how the regulator's record behaves for any
    machine at all. The second was withheld from every non-CVT machine in
    the corpus, and it named the SYM Symba, which the lookup classifies
    `semi_auto_centrifugal` — a contradiction on disk.
    """

    def test_the_cvt_half_keeps_its_id_title_and_scope(self, seeded):
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4615_CVT)
        assert json.loads(row["applicability"]) == {"transmission": ["cvt"]}
        assert row["source"] == "regulation"

    def test_the_cvt_half_no_longer_names_the_symba(self, seeded):
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4615_CVT)
            models = {m for (m,) in conn.execute(
                "SELECT model FROM known_issue_models WHERE issue_id = ?", (row["id"],))}
        assert "SYM Symba" not in row["model"]
        # Phase 255C made the junction's model a bare canonical with the
        # marque in its own column, so the entry to look for is `Symba`
        # rather than `SYM Symba`. Exact membership, not a substring.
        assert not any("Symba" in m for m in models), sorted(models)
        # 255C: the junction model is a bare canonical, marque in its own column.
        assert "GTS" in models, "positive control: the junction is populated"

    def test_the_cvt_half_still_names_the_vespa_946(self, seeded):
        """Deliberate, not an oversight.

        `(regulator, Vespa 946)` is a live KNOWN_SELF_EXCLUDING entry the
        operator ruled stays as-is under F119 (closed-unobtainable).
        Moving the 946 to the unscoped half would have resolved a pin this
        phase was not asked to touch, and would have done it silently.
        """
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4615_CVT)
        assert "Vespa 946" in row["model"]

    def test_the_general_half_is_unscoped(self, seeded):
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4615_GENERAL)
        assert row["applicability"] is None, (
            "the index methodology holds for every machine; declaring any "
            "transmission on it re-creates the defect the split repairs")
        assert row["source"] == "regulation"

    def test_the_general_half_carries_the_symba_and_reaches_it(self, seeded):
        """The Symba gets the row it was being denied."""
        res = resolve_transmission("SYM", "Symba 100")
        assert res.provenance == "model-sourced"
        assert res.candidates == frozenset({"semi_auto_centrifugal"})

        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4615_GENERAL)
            models = {m for (m,) in conn.execute(
                "SELECT model FROM known_issue_models WHERE issue_id = ?", (row["id"],))}
        assert "SYM Symba" in row["model"]
        assert any("Symba" in m for m in models), sorted(models)
        assert row_applies(row, "transmission", res.candidates) is True

        cvt_only = {"applicability": json.dumps({"transmission": ["cvt"]})}
        assert row_applies(cvt_only, "transmission", res.candidates) is False, (
            "positive control: a {cvt} row IS withheld from the Symba")

    def test_both_halves_name_an_nhtsa_campaign(self, seeded):
        """The regulation provenance rule: a regulation row names its campaign."""
        pat = __import__("re").compile(r"\b\d{2}V\d{3}0*\b")
        with sqlite3.connect(seeded) as conn:
            for title in (T_4615_CVT, T_4615_GENERAL):
                row = _row(conn, title)
                found = set(pat.findall(row["description"]))
                assert found, f"{title[:40]!r} names no campaign"
                assert row["source"] == "regulation"

    def test_the_split_did_not_duplicate_the_index_prose(self, seeded):
        """A split, not a copy. The methodology lives in one row."""
        needle = "sixty-six byte body"
        with sqlite3.connect(seeded) as conn:
            hits = [r[0] for r in conn.execute(
                "SELECT title FROM known_issues WHERE description LIKE ?",
                ("%" + needle + "%",))]
        assert len(hits) == 1, f"{len(hits)} rows carry the index prose: {hits}"
        assert hits[0] == T_4615_GENERAL


T_4611_CVT = "Kickstart backup, and the scooter named Kick that has none"


class TestTheSplitsAsASet:
    def test_both_new_rows_are_registered_with_the_migration_hook(self):
        """The hook reads prose from the seed file and raises on drift."""
        from motodiag.knowledge.loader import _255B_NEW_ROW_TITLES
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        titles = {e["title"] for e in entries}
        for t in _255B_NEW_ROW_TITLES:
            assert t in titles, f"hook expects {t!r}, seed file does not have it"

    def test_no_row_in_the_file_declares_a_set_containing_manual(self):
        """Phase 255's rule, and 255B's first non-goal.

        Manual coverage is not sourced — the lookup holds one `manual`
        entry — so a `{manual}` row would be withheld from every machine
        that resolves `unknown`, which is most of them.
        """
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        offenders = [e["title"][:50] for e in entries
                     if "manual" in (e.get("applicability") or {}).get("transmission", [])]
        assert offenders == [], offenders

        declared = [e for e in entries if "applicability" in e]
        assert declared, "positive control: rows in this file DO declare a set"

    def _pre_255B_seed(self, tmp_path) -> pathlib.Path:
        """The CVT seed file as it stood before this phase.

        Reconstructed from the shipped file rather than from a rollback,
        which is the whole point: a round trip measured against a state
        the rollback itself produced cannot detect a rollback that is
        wrong in the same way twice.
        """
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        entries = [e for e in entries if e["title"] not in _255B_ADDED]
        assert len(entries) == 12, len(entries)
        for e in entries:
            if e["title"].startswith(T_4609):
                assert "Filly" not in e["model"]
                e["model"] = MODEL_4609_AS_SHIPPED
            if e["title"].startswith(T_4615_CVT):
                assert "SYM Symba" not in e["model"]
                e["model"] = e["model"].replace(
                    "Kymco Like 150i", "Kymco Like 150i, SYM Symba")
            if e["title"].startswith(T_4605):
                assert e["make"] == MAKE_4605_AFTER
                e["make"] = MAKE_4605_AS_SHIPPED
        out = tmp_path / "known_issues_cvt.json"
        out.write_text(json.dumps(entries), encoding="utf-8")
        return out

    def test_migration_065_round_trips_including_the_derived_junctions(self, tmp_path):
        """Apply then roll back must land exactly where it started.

        Found by running it: the first cut of `rollback_sql` restored the
        `model` columns and deleted the added rows, but nothing rebuilt
        `known_issue_models` -- rollback has no `post_apply` hook, it is
        pure SQL. The round trip landed at 2,422 junction rows having
        started at 2,424, silently short the Filly and Symba entries.

        The FIRST version of this test also passed with the fix removed,
        because it took its baseline after a rollback and so compared a
        buggy rollback against itself. The baseline is now built from a
        reconstructed pre-255B seed file, independent of the rollback
        path. Counts, not spot checks, because counts are what caught it.
        """
        from motodiag.core.migrations import (
            apply_pending_migrations, rollback_migration,
            get_migration_by_version, rollback_to_version,
        )

        path = str(tmp_path / "roundtrip.db")
        init_db(path)
        for f in sorted(SEED_DIR.glob("known_issues_*.json")):
            if f.name == CVT_SEED.name:
                continue
            load_known_issues_file(f, path)
        load_known_issues_file(self._pre_255B_seed(tmp_path), path)
        rebuild_make_index_at(path)
        rebuild_model_index_at(path)
        rollback_to_version(64, db_path=path)

        def counts():
            with sqlite3.connect(path) as conn:
                return tuple(conn.execute(q).fetchone()[0] for q in (
                    "SELECT COUNT(*) FROM known_issues",
                    "SELECT COUNT(*) FROM known_issue_models",
                    "SELECT COUNT(*) FROM known_issue_makes",
                ))

        before = counts()
        with sqlite3.connect(path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM known_issue_models WHERE model = 'Filly LX 50'"
            ).fetchone()[0] == 1, "baseline must be the genuine pre-255B state"

        apply_pending_migrations(db_path=path)
        after = counts()
        assert after[0] == before[0] + len(_255B_ADDED), (
            f"migration should add {len(_255B_ADDED)} rows: {before} -> {after}")

        # Roll back to the version the baseline was taken at, not just 065.
        # Phase 255C's migration 066 changes the junction's SHAPE, so undoing
        # 065 alone leaves a three-column junction being compared against a
        # two-column baseline — 2,779 against 2,385, which is a schema
        # difference reported as a row-count difference.
        rollback_to_version(64, db_path=path)
        assert counts() == before, (
            f"rollback is not a round trip: {before} -> {after} -> {counts()}")


class TestF115TheVocabularyRowReachesTheOwnersItIsFor:
    """4605 exists to tell a cruiser owner a final-drive belt is not a CVT belt.

    Its make column named seven scooter marques. A Harley Road King owner,
    a BMW R1200GS owner and a LiveWire owner — the three the row's own
    description is about — could not receive it.
    """

    def test_the_marque_list_is_derived_from_the_corpus_not_chosen(self, seeded):
        """The collision set, measured. Scope and count, not a screenful.

        Vocabulary is the maker's own phrase `drive belt`, over
        title || description || symptoms, across the whole corpus.
        """
        with sqlite3.connect(seeded) as conn:
            hits = list(conn.execute(
                "SELECT id, make FROM known_issues WHERE "
                "lower(title || ' ' || description || ' ' || COALESCE(symptoms,'')) "
                "LIKE '%drive belt%' ORDER BY id"))
        assert len(hits) >= 13, f"collision set shrank to {len(hits)}"

        marques = {m.strip() for _, mk in hits for m in (mk or "").split(",")}
        for marque in MARQUES_ADDED_F115:
            assert marque in marques, (
                f"{marque} is in 4605's make column but no row in the "
                "collision set justifies it")

        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4605)
        assert row["id"] in {i for i, _ in hits}, (
            "positive control: 4605 must be in its own collision set")

    def test_the_make_column_now_carries_the_three_marques(self, seeded):
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4605)
            makes = {m for (m,) in conn.execute(
                "SELECT make FROM known_issue_makes WHERE issue_id = ?", (row["id"],))}
        assert row["make"] == MAKE_4605_AFTER
        for marque in MARQUES_ADDED_F115:
            assert marque in makes, f"{marque} missing from the derived junction"
        assert "Piaggio" in makes, "positive control: the original marques stay"

    def test_no_model_was_invented_for_the_new_marques(self, seeded):
        """Makes only. Naming a model no document establishes is 4609's error."""
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4605)
        for name in ("Road King", "R1200GS", "LiveWire ONE", "VRSC", "Bolt"):
            assert name not in (row["model"] or ""), name

    def test_4605_stays_unscoped_and_that_is_the_point(self, seeded):
        """Scoping this row would re-create F115 in the fix that closes it.

        All three added marques resolve `unknown`, and the filter is
        fail-closed, so ANY transmission set here withholds the row from
        exactly the owners this commit added.
        """
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4605)
        assert row["applicability"] is None

        # The unknown BMW is a spelling absent from the junction, so no batch
        # can ever source it. It was the R1200GS (sourced by Phase 257), then
        # the R1250 — not safe either: names_model("R 1250 RT", "R1250") is
        # True, because "rt" is not a variant token (measured 2026-09-23).
        # The claim is about an unknown BMW. Assertions untouched.
        assert resolve_transmission("BMW", "ZZ-0 unlisted").provenance == "unknown", (
            "the example machine has been sourced: pick another spelling absent from the junction")
        for make, model in (("Harley-Davidson", "Road King"),
                            ("BMW", "ZZ-0 unlisted"),
                            ("LiveWire", "ONE")):
            res = resolve_transmission(make, model)
            assert res.provenance == "unknown", (make, model)
            assert row_applies(row, "transmission", res.candidates) is True
            scoped = {"applicability": json.dumps({"transmission": ["cvt"]})}
            assert row_applies(scoped, "transmission", res.candidates) is False, (
                f"positive control: a scoped row IS withheld from {make} {model}")

    def test_the_row_actually_reaches_those_machines_now(self, seeded):
        """End to end, through the chokepoint, not just the column."""
        from motodiag.knowledge.retrieval import rows_for_machine
        from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

        with sqlite3.connect(seeded) as conn:
            title = _row(conn, T_4605)["title"]

        for make, model in (("Harley-Davidson", "Road King"),
                            ("BMW", "R1200GS"),
                            ("LiveWire", "ONE")):
            _, raw = known_issues_for_vehicle(make, model, db_path=seeded, limit=400)
            kept = rows_for_machine(raw, make=make, model=model, purpose="prompt",
                                    db_path=seeded, record=False).rows
            assert title in {r["title"] for r in kept}, (
                f"{make} {model} still does not receive the row written for it")

        # Positive control: a marque with no belt-vocabulary collision and
        # no entry in 4605's make column must NOT start receiving it.
        _, raw = known_issues_for_vehicle("Kawasaki", "Ninja 400",
                                          db_path=seeded, limit=400)
        kept = rows_for_machine(raw, make="Kawasaki", model="Ninja 400",
                                purpose="prompt", db_path=seeded, record=False).rows
        assert title not in {r["title"] for r in kept}, (
            "the fix must not become a wildcard")


class TestRow4611WasNotSplit:
    """Phase 256 recorded a debt: split 4611's general half out. 255B tried,
    shipped it, audited it, and backed it out. The debt is CLOSED as wrong,
    not carried forward — the operator's decision of 2026-09-22.

    **The split as conceived cannot work.** The general half asserted that a
    kickstart and an electric starter do not share interlocks, so an engine
    that kick-starts but will not start electrically indicts the brake-lever
    switch. That is documented for one maker family and CONTRADICTED by two
    of the machines the split half declared:

    * Genuine's Buddy 50 owner's manual: *"It is not necessary to hold the
      brake lever in when starting your vehicle with the kick-start method"*
      — the interlock difference the diagnostic needs.
    * Kymco's Agility 50/125 owner's manual and Super 8 50X owner's manual:
      *"While squeezing the rear brake lever, kick down on the kick start
      lever without rotating the throttle grip."* — the brake lever IS
      required, so on a Kymco the comparison proves nothing.

    The claim is maker-specific, and a row scoped by transmission cannot
    carry a maker-specific claim. A Genuine-only interlock row is a note for
    a future content phase, not a 255B debt.

    **The split's own failure mode is the lesson**: the quote that refutes
    generalising the diagnostic was left behind in the other half. Splitting
    a row separates a claim from its counter-evidence unless someone checks
    for that, and nobody did until an audit ran.
    """

    def test_4611_is_one_row_again(self):
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        hits = [e for e in entries if e["title"] == T_4611_CVT]
        assert len(hits) == 1
        assert hits[0]["applicability"] == {"transmission": ["cvt"]}

        halves = [e for e in entries
                  if "brake-lever switch test" in e["title"]
                  or "starter button does not" in e["title"]]
        assert halves == [], f"the 4611 split is back: {[h['title'][:60] for h in halves]}"

    def test_both_the_claim_and_its_counter_evidence_live_in_that_one_row(self):
        """The reason the split failed, pinned so a re-split has to face it."""
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        body = next(e for e in entries if e["title"] == T_4611_CVT)["description"]
        assert "not necessary to hold the brake lever" in body, (
            "the Genuine interlock quote — the diagnostic's evidence")
        assert "squeezing the rear brake lever" in body, (
            "the Kymco quote — the counter-evidence that stops it generalising. "
            "If a future phase splits this row, these two must not be separated.")


#: F132. Machines and model years the year-window change was measured over.
#: Named individually so that dropping one is an edit somebody reviews.
F132_MACHINES = [
    ("Honda", "PCX 150", True), ("Kymco", "Agility 50", True),
    ("Vespa", "LX 50", True), ("Yamaha", "Zuma 125", True),
    ("Genuine", "Buddy 125", True), ("Kymco", "People S 250", True),
    ("Honda", "GL1800 Gold Wing", False), ("Yamaha", "YZF-R1", False),
    ("Honda", "Grom", False), ("Kawasaki", "Ninja 400", False),
    ("SYM", "Symba 100", False),
]
F132_YEARS = [2001, 2003, 2005, 2013, 2019, 2022, 2026, 2027]

#: The two rows whose own prose names a model-year range and therefore keep
#: their window: "model years 2015 to 2020" / "April 2021", and "model years
#: 2003 to 2026".
F132_KEEP_WINDOW = {
    "A CVT recall exists that no belt, pulley or variator search would find",
    "What the regulator record shows for scooter CVTs",
}


class TestF132UnevidencedMetadata:
    """Year windows and repair estimates the documents do not support.

    `_covers_year` gates retrieval, so an unevidenced window silently adds
    and removes rows. Nulling a bound REMOVES a gate, so this can only
    widen — which is the direction the rest of this phase has been
    tightening, and why the change shipped with a measured table rather
    than an argument.
    """

    def test_only_rows_whose_prose_names_a_range_keep_a_window(self):
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        kept = {e["title"] for e in entries if e.get("year_start") is not None}
        expected = {t for t in {e["title"] for e in entries}
                    if any(t.startswith(k) for k in F132_KEEP_WINDOW)}
        assert kept == expected, (
            "a year window appeared or vanished. A row keeps one only if its "
            "own description names the model-year range.\n"
            f"  unexpected: {sorted(kept - expected)}\n"
            f"  missing:    {sorted(expected - kept)}")

    def test_no_row_in_this_file_asserts_repair_hours(self):
        """None of these rows describes a repair; they are reference rows."""
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        offenders = [e["title"][:50] for e in entries
                     if e.get("estimated_hours") is not None]
        assert offenders == [], offenders

    def test_the_widening_never_removes_a_row(self, tmp_path):
        """The property that makes this change safe to review as a table.

        A null bound cannot exclude, so no machine may lose a row. If this
        ever fails, the change is doing something other than removing a
        gate.
        """
        from motodiag.knowledge.retrieval import rows_for_machine
        from motodiag.knowledge.vehicle_resolver import known_issues_for_vehicle

        titles = {e["title"] for e in json.loads(CVT_SEED.read_text(encoding="utf-8"))}

        def build(restore_windows: bool) -> str:
            path = str(tmp_path / f"f132-{restore_windows}.db")
            init_db(path)
            entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
            if restore_windows:
                for e in entries:
                    e.setdefault("year_start", 2002)
                    e.setdefault("year_end", 2026)
            f = tmp_path / f"seed-{restore_windows}.json"
            f.write_text(json.dumps(entries), encoding="utf-8")
            for s in sorted(SEED_DIR.glob("known_issues_*.json")):
                load_known_issues_file(f if s.name == CVT_SEED.name else s, path)
            rebuild_make_index_at(path)
            rebuild_model_index_at(path)
            return path

        def covers(row, year):
            s, e = row.get("year_start"), row.get("year_end")
            return not ((s is not None and year < s) or (e is not None and year > e))

        def reached(db, make, model, year):
            _, raw = known_issues_for_vehicle(make, model, db_path=db, limit=400)
            kept = [r for r in raw if covers(r, year)]
            out = rows_for_machine(kept, make=make, model=model, year=year,
                                   purpose="prompt", db_path=db, record=False).rows
            return {r["title"] for r in out} & titles

        before, after = build(True), build(False)
        lost_total = 0
        for make, model, is_cvt in F132_MACHINES:
            for year in F132_YEARS:
                b = reached(before, make, model, year)
                a = reached(after, make, model, year)
                lost = b - a
                lost_total += len(lost)
                assert not lost, (
                    f"{make} {model} {year} LOST {sorted(lost)} — nulling a "
                    "year bound must never exclude a row")
                if not is_cvt:
                    # The only row a non-CVT machine may gain is the one that
                    # is unscoped by design: the drive-belt vocabulary row,
                    # whose reach F115 deliberately widened. Anything else
                    # would mean scoped CVT content reaching a machine the
                    # filter is supposed to exclude.
                    # A non-CVT machine may gain only rows that are UNSCOPED
                    # by design — the drive-belt vocabulary row and the
                    # regulator-index row. Both are unscoped precisely so
                    # every machine can receive them, and neither is CVT
                    # content. Anything else would mean scoped content
                    # reaching a machine the filter is supposed to exclude.
                    entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
                    unscoped = {e["title"] for e in entries
                                if "applicability" not in e}
                    for t in a - b:
                        assert t in unscoped, (
                            f"{make} {model} {year} gained a SCOPED row: {t}")
        assert lost_total == 0


class TestTheHookOnlyRepairsASeededCorpus:
    """Both sides of the anchor guard in `_insert_255B_new_rows`.

    `init_db` runs migrations, so a hook with no guard fires on an empty
    database and inserts this phase's rows before the loader writes
    anything. These two tests exist because that defect shipped TWICE: the
    first time it was caught by a round-trip test's arithmetic, the second
    time the guard AND these tests were deleted together by a regex edit,
    and nothing noticed until a full regression failed 134 tests across 17
    phase files — every one of them a `test_loads` counting rows after
    loading a single seed file.

    An edit that removes a protection and its test in the same stroke
    leaves nothing to notice. That is why the guard's comment names these
    tests and these tests name the guard.
    """

    def test_the_hook_does_not_seed_a_fresh_database(self, tmp_path):
        path = str(tmp_path / "fresh.db")
        init_db(path)
        with sqlite3.connect(path) as conn:
            n = conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0]
        assert n == 0, (
            f"init_db planted {n} known_issues rows on a fresh database — "
            "the anchor guard in _insert_255B_new_rows is missing again")

    def test_a_single_seed_file_loads_to_its_own_count(self, tmp_path):
        """The shape of the 134 failures, pinned directly.

        Every one of them was a phase test loading one seed file into a
        fresh database and asserting the row count. If the hook seeds, they
        all read one too many.
        """
        path = str(tmp_path / "one.db")
        init_db(path)
        one = SEED_DIR / "known_issues_suzuki_common.json"
        expected = len(json.loads(one.read_text(encoding="utf-8")))
        load_known_issues_file(one, path)
        with sqlite3.connect(path) as conn:
            got = conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0]
        assert got == expected, f"{one.name}: loaded {got}, file holds {expected}"

    def test_the_hook_still_repairs_a_seeded_corpus(self, tmp_path):
        """The other side: the guard must not make the hook a no-op."""
        path = str(tmp_path / "seeded.db")
        init_db(path)
        for f in sorted(SEED_DIR.glob("known_issues_*.json")):
            if f.name == CVT_SEED.name:
                continue
            load_known_issues_file(f, path)
        load_known_issues_file(
            TestTheSplitsAsASet()._pre_255B_seed(tmp_path), path)
        with sqlite3.connect(path) as conn:
            before = conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0]
            reconcile_255B_rows(conn)
            after = conn.execute("SELECT COUNT(*) FROM known_issues").fetchone()[0]
        assert after - before == len(_255B_ADDED), (before, after)
