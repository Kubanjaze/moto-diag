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

#: The rows Phase 255B adds — the general half of each split.
_255B_ADDED = (
    "The regulator's two indexes contradict each other, and an empty recall "
    "answer is not a clean record",
    "A kickstart that works when the starter button does not is a "
    "brake-lever switch test",
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
        # Exact membership, not a substring: the junction stores the
        # marque-prefixed `SYM Symba` (S0-4), so `"Symba" not in models`
        # would pass even with the entry present.
        assert not any("Symba" in m for m in models), sorted(models)
        assert "Vespa GTS" in models, "positive control: the junction is populated"

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
T_4611_GENERAL = ("A kickstart that works when the starter button does not is a "
                  "brake-lever switch test")


class TestRow4611Splits:
    """A brake-lever switch is not a transmission.

    4611 declared `{cvt}` over two claims: which machines in this class
    have a kickstart, and what a working kickstart tells you when the
    starter button does nothing. The second is about an interlock — a
    lever and a switch — and was being withheld from every machine that
    is not a CVT.
    """

    def test_the_cvt_half_keeps_its_id_title_and_scope(self, seeded):
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4611_CVT)
        assert json.loads(row["applicability"]) == {"transmission": ["cvt"]}
        assert row["source"] == "service-manual"

    def test_the_general_half_is_unscoped(self, seeded):
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4611_GENERAL)
        assert row["applicability"] is None

    def test_4611_names_no_machine_it_excludes_before_or_after(self, seeded):
        """Stated because the brief implied otherwise.

        Two of this phase's three splits touch KNOWN_SELF_EXCLUDING, not
        three. 4611 has no entry because no model in its junction resolves
        to something its `{cvt}` declaration excludes — every one of them
        is a CVT or resolves `unknown` without being named by the lookup
        as something else.
        """
        with sqlite3.connect(seeded) as conn:
            row = _row(conn, T_4611_CVT)
            models = [m for (m,) in conn.execute(
                "SELECT model FROM known_issue_models WHERE issue_id = ?", (row["id"],))]
        assert models, "positive control: the junction is populated"
        makes = [m.strip() for m in row["make"].split(",")]
        offenders = []
        for model in models:
            res = next((resolve_transmission(mk, model) for mk in makes
                        if resolve_transmission(mk, model).provenance == "model-sourced"),
                       resolve_transmission(makes[0], model))
            if not row_applies(row, "transmission", res.candidates):
                offenders.append((model, res.provenance))
        assert offenders == [], offenders

    def test_unscoping_reaches_the_semi_auto_machines_it_was_withheld_from(self, seeded):
        """The gain, measured rather than asserted.

        The Super Cub C125 and the CT125 Hunter Cub are
        `semi_auto_centrifugal` and both are kickstart machines. A `{cvt}`
        declaration withheld the diagnostic from them; an unscoped row
        does not.
        """
        with sqlite3.connect(seeded) as conn:
            general = _row(conn, T_4611_GENERAL)
            cvt_half = _row(conn, T_4611_CVT)

        # `CT125` and not `CT125 Hunter Cub`: the canonical label of that
        # lookup entry is absent from its own alias tuple, so the exact
        # canonical string resolves `unknown` while every alias resolves.
        # Filed as F131. Using the string that works keeps this test about
        # the split rather than about that defect.
        for model in ("Super Cub C125", "CT125"):
            res = resolve_transmission("Honda", model)
            assert res.provenance == "model-sourced", model
            assert res.candidates == frozenset({"semi_auto_centrifugal"}), model
            assert row_applies(general, "transmission", res.candidates) is True, model
            assert row_applies(cvt_half, "transmission", res.candidates) is False, (
                f"positive control: the CVT half IS still withheld from {model}")

    def test_the_split_did_not_duplicate_the_diagnostic_prose(self, seeded):
        needle = "not necessary to hold the brake lever"
        with sqlite3.connect(seeded) as conn:
            hits = [r[0] for r in conn.execute(
                "SELECT title FROM known_issues WHERE description LIKE ?",
                ("%" + needle + "%",))]
        assert len(hits) == 1, f"{len(hits)} rows carry the quote: {hits}"
        assert hits[0] == T_4611_GENERAL

    def test_the_canonical_name_gap_is_recorded_not_silently_worked_around(self):
        """F131, pinned so the workaround above cannot rot unnoticed.

        Six of the 50 lookup entries have a canonical label that does not
        resolve to their own entry. Five are compound display labels
        nobody types as a model — `LX 125/150`, `GTS 300/310`,
        `SH125i/SH150i`, `XC155 / SMAX`, `Jet 50/100`. The sixth,
        `CT125 Hunter Cub`, is Honda's actual name for the machine, and a
        rider who types it loses every scoped row to the fail-closed
        filter. Not fixed here — 255B adds no lookup entries — but a
        seventh, or a change in the six, should be noticed.
        """
        from motodiag.knowledge.transmission import TRANSMISSION_LOOKUP
        unresolved = {
            e.canonical for e in TRANSMISSION_LOOKUP
            if resolve_transmission(e.make, e.canonical).entry is not e
        }
        assert unresolved == {
            "SH125i/SH150i", "CT125 Hunter Cub", "XC155 / SMAX",
            "Jet 50/100", "LX 125/150", "GTS 300/310",
        }, sorted(unresolved)

    def test_the_general_half_names_its_documents(self, seeded):
        """No quote, no row — and the quote needs a document behind it."""
        with sqlite3.connect(seeded) as conn:
            body = _row(conn, T_4611_GENERAL)["description"]
        assert "Buddy 50 owner's manual" in body
        assert "service station manual 633976" in body
        assert "not necessary to hold the brake lever" in body


class TestTheSplitsAsASet:
    def test_both_new_rows_are_registered_with_the_migration_hook(self):
        """The hook reads prose from the seed file and raises on drift."""
        from motodiag.knowledge.loader import _255B_NEW_ROW_TITLES
        entries = json.loads(CVT_SEED.read_text(encoding="utf-8"))
        titles = {e["title"] for e in entries}
        for t in _255B_NEW_ROW_TITLES:
            assert t in titles, f"hook expects {t!r}, seed file does not have it"
        assert set(_255B_NEW_ROW_TITLES) == {T_4615_GENERAL, T_4611_GENERAL}

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

        rollback_migration(get_migration_by_version(65), db_path=path)
        assert counts() == before, (
            f"rollback is not a round trip: {before} -> {after} -> {counts()}")
