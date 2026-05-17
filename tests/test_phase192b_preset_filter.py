"""Phase 192B Commit 1 — composer-side preset filtering.

Tests the new ``preset`` + ``overrides`` parameters on
:func:`build_session_report_doc`. Pins the resolution semantics
(explicit override beats preset default; absent entries fall
through; ``preset=None`` returns full document for back-compat
with the GET ``/pdf`` route).

Mirrors the mobile-side preset semantics in
``moto-diag-mobile/src/screens/reportPresets.ts`` exactly. Phase
192B's deliberate two-source design (backend Python + mobile TS)
creates drift potential — these tests are the contract-pin that
catches drift on the backend side.
"""

from __future__ import annotations

import pytest

from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session_for_owner
from motodiag.reporting.builders import (
    _CUSTOMER_HIDDEN_HEADINGS,
    _FULL_HIDDEN_HEADINGS,
    _INSURANCE_HIDDEN_HEADINGS,
    _is_section_hidden,
    _preset_hidden_headings,
    build_session_report_doc,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase192b.db")
    init_db(path)
    yield path


def _make_user(db_path, username="bob"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        return cursor.lastrowid


def _make_session_with_notes(db_path, user_id):
    """Create a session that hits every section variant the
    Customer preset interacts with — specifically a non-empty
    ``notes`` field so the Customer preset has something to hide."""
    session_id = create_session_for_owner(
        owner_user_id=user_id,
        vehicle_make="Honda",
        vehicle_model="CBR600",
        vehicle_year=2005,
        symptoms=["idle bog"],
        fault_codes=["P0171"],
        db_path=db_path,
    )
    # Append notes via direct SQL so we don't need to import the
    # symptom/note repo just for fixture setup.
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE diagnostic_sessions SET notes = ? WHERE id = ?",
            ("Customer reports issue began after oil change.", session_id),
        )
    return session_id


def _section_headings(doc) -> list[str]:
    return [str(s.get("heading", "")) for s in doc["sections"]]


# ---------------------------------------------------------------------------
# 1. _preset_hidden_headings constants pin
# ---------------------------------------------------------------------------


class TestPresetHiddenHeadings:

    def test_customer_hides_notes_only(self):
        assert _CUSTOMER_HIDDEN_HEADINGS == ("Notes",)

    def test_insurance_hides_nothing(self):
        assert _INSURANCE_HIDDEN_HEADINGS == ()

    def test_full_hides_nothing(self):
        assert _FULL_HIDDEN_HEADINGS == ()

    def test_dispatcher_returns_matching_set(self):
        assert _preset_hidden_headings("customer") is _CUSTOMER_HIDDEN_HEADINGS
        assert _preset_hidden_headings("insurance") is _INSURANCE_HIDDEN_HEADINGS
        assert _preset_hidden_headings("full") is _FULL_HIDDEN_HEADINGS


# ---------------------------------------------------------------------------
# 2. _is_section_hidden resolution semantics
# ---------------------------------------------------------------------------


class TestIsSectionHidden:

    def test_preset_none_is_never_hidden(self):
        # Back-compat with Phase 182's GET /pdf path: preset=None
        # means "no filter", every section visible.
        assert _is_section_hidden("Notes", None, None) is False
        assert _is_section_hidden("Vehicle", None, None) is False
        assert _is_section_hidden("anything", None, None) is False

    def test_customer_preset_hides_notes_default(self):
        assert _is_section_hidden("Notes", "customer", None) is True
        assert _is_section_hidden("Vehicle", "customer", None) is False
        assert _is_section_hidden("Reported symptoms", "customer", None) is False
        assert _is_section_hidden("Fault codes", "customer", None) is False
        assert _is_section_hidden("Videos", "customer", None) is False

    def test_insurance_preset_full_disclosure(self):
        for heading in [
            "Vehicle", "Reported symptoms", "Fault codes",
            "Notes", "AI diagnosis", "Videos", "Timeline",
        ]:
            assert _is_section_hidden(heading, "insurance", None) is False

    def test_full_preset_full_disclosure(self):
        for heading in [
            "Vehicle", "Reported symptoms", "Fault codes",
            "Notes", "AI diagnosis", "Videos", "Timeline",
        ]:
            assert _is_section_hidden(heading, "full", None) is False

    def test_explicit_override_true_beats_preset_hide(self):
        # Customer preset hides Notes by default; explicit True
        # forces it visible (the F28 follow-up's "show this even
        # though preset hides it" semantic).
        assert (
            _is_section_hidden("Notes", "customer", {"Notes": True})
            is False
        )

    def test_explicit_override_false_beats_preset_show(self):
        # Full preset shows Vehicle; explicit False forces it
        # hidden (the F28 follow-up's "hide this even though
        # preset shows it" semantic).
        assert (
            _is_section_hidden("Vehicle", "full", {"Vehicle": False})
            is True
        )

    def test_absent_override_falls_through_to_preset(self):
        # Override map has unrelated entries → falls through to
        # preset default for the heading we asked about.
        assert (
            _is_section_hidden(
                "Notes", "customer", {"Vehicle": False, "Other": True},
            )
            is True
        )

    def test_overrides_only_no_preset(self):
        # Overrides without preset: explicit hides win, absent
        # falls through to "not hidden" (preset=None semantics).
        assert _is_section_hidden("Notes", None, {"Notes": False}) is True
        assert _is_section_hidden("Vehicle", None, {"Notes": False}) is False

    def test_case_sensitivity_strict(self):
        # Backend builder uses 'Notes' (capital N). 'notes' /
        # 'NOTES' would NOT be hidden by Customer preset. Same
        # strict-equality posture as the section-iteration code.
        assert _is_section_hidden("notes", "customer", None) is False
        assert _is_section_hidden("NOTES", "customer", None) is False


# ---------------------------------------------------------------------------
# 3. End-to-end composer invocation with preset
# ---------------------------------------------------------------------------


class TestComposerPresetIntegration:

    def test_preset_none_returns_full_document(self, db):
        user_id = _make_user(db)
        session_id = _make_session_with_notes(db, user_id)

        doc = build_session_report_doc(session_id, user_id, db_path=db)
        headings = _section_headings(doc)

        # Default behavior: every populated section present.
        assert "Vehicle" in headings
        assert "Reported symptoms" in headings
        assert "Fault codes" in headings
        assert "Notes" in headings
        assert "Timeline" in headings

    def test_customer_preset_hides_notes_section(self, db):
        user_id = _make_user(db)
        session_id = _make_session_with_notes(db, user_id)

        doc = build_session_report_doc(
            session_id, user_id, db_path=db, preset="customer",
        )
        headings = _section_headings(doc)

        assert "Notes" not in headings
        # Other sections still present.
        assert "Vehicle" in headings
        assert "Reported symptoms" in headings
        assert "Fault codes" in headings
        assert "Timeline" in headings

    def test_insurance_preset_returns_full_disclosure(self, db):
        user_id = _make_user(db)
        session_id = _make_session_with_notes(db, user_id)

        doc = build_session_report_doc(
            session_id, user_id, db_path=db, preset="insurance",
        )
        headings = _section_headings(doc)

        # Insurance hides nothing.
        assert "Notes" in headings
        assert "Vehicle" in headings

    def test_full_preset_returns_full_disclosure(self, db):
        user_id = _make_user(db)
        session_id = _make_session_with_notes(db, user_id)

        doc = build_session_report_doc(
            session_id, user_id, db_path=db, preset="full",
        )
        headings = _section_headings(doc)

        # Full hides nothing.
        assert "Notes" in headings
        assert "Vehicle" in headings

    def test_overrides_force_section_visible_under_customer(self, db):
        user_id = _make_user(db)
        session_id = _make_session_with_notes(db, user_id)

        doc = build_session_report_doc(
            session_id, user_id, db_path=db,
            preset="customer", overrides={"Notes": True},
        )
        headings = _section_headings(doc)

        # Override forces Notes visible despite Customer's default hide.
        assert "Notes" in headings

    def test_overrides_force_section_hidden_under_full(self, db):
        user_id = _make_user(db)
        session_id = _make_session_with_notes(db, user_id)

        doc = build_session_report_doc(
            session_id, user_id, db_path=db,
            preset="full", overrides={"Vehicle": False},
        )
        headings = _section_headings(doc)

        # Override forces Vehicle hidden despite Full's default show.
        assert "Vehicle" not in headings

    def test_overrides_only_no_preset(self, db):
        user_id = _make_user(db)
        session_id = _make_session_with_notes(db, user_id)

        doc = build_session_report_doc(
            session_id, user_id, db_path=db,
            overrides={"Notes": False},
        )
        headings = _section_headings(doc)

        # No preset → no preset filter; only the explicit override
        # in the map applies.
        assert "Notes" not in headings
        assert "Vehicle" in headings  # not in overrides → visible

    def test_preset_filter_preserves_section_order(self, db):
        # Filter is order-preserving: dropping a section doesn't
        # reshuffle the others. Important for stable rendering.
        user_id = _make_user(db)
        session_id = _make_session_with_notes(db, user_id)

        full_doc = build_session_report_doc(
            session_id, user_id, db_path=db,
        )
        customer_doc = build_session_report_doc(
            session_id, user_id, db_path=db, preset="customer",
        )

        full_order = _section_headings(full_doc)
        customer_order = _section_headings(customer_doc)

        # Customer is full minus Notes, in the same relative order.
        expected = [h for h in full_order if h != "Notes"]
        assert customer_order == expected
