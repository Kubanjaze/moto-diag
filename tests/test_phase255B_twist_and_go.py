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
