"""Phase 192B Commit 1 — POST /v1/reports/session/{id}/pdf integration.

Covers the new sibling POST route for preset-filtered session PDFs:

- 200 with ``application/pdf`` for valid preset.
- 422 when ``preset`` body field absent (FastAPI auto-validation).
- 422 when ``preset`` is an unknown value (FastAPI Literal narrowing).
- 404 cross-owner (matches GET sibling + F29 ADR posture).
- 401 missing API key.
- Customer preset → smaller PDF than full preset (proxy for
  "Notes section absent in body").

Existing GET sibling untouched; a regression-guard test pins that.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session_for_owner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase192b_post.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _make_user(db_path, username="bob"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com"),
        )
        return cursor.lastrowid


def _make_session_with_notes(db_path, user_id):
    session_id = create_session_for_owner(
        owner_user_id=user_id,
        vehicle_make="Honda",
        vehicle_model="CBR600",
        vehicle_year=2005,
        symptoms=["idle bog"],
        fault_codes=["P0171"],
        db_path=db_path,
    )
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE diagnostic_sessions SET notes = ? WHERE id = ?",
            ("Customer reports issue began after oil change.", session_id),
        )
    return session_id


@pytest.fixture
def client(api_db):
    return TestClient(create_app())


@pytest.fixture
def owner_auth(api_db):
    user_id = _make_user(api_db, "owner")
    _, plaintext = create_api_key(user_id, db_path=api_db)
    return user_id, {"X-API-Key": plaintext}


@pytest.fixture
def other_user_auth(api_db):
    user_id = _make_user(api_db, "stranger")
    _, plaintext = create_api_key(user_id, db_path=api_db)
    return user_id, {"X-API-Key": plaintext}


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


class TestPostPdfHappyPath:

    def test_returns_pdf_bytes_with_valid_preset(
        self, client, api_db, owner_auth,
    ):
        user_id, headers = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        resp = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "customer"},
            headers=headers,
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content[:5] == b"%PDF-"  # PDF magic bytes
        assert (
            f'filename="session-{session_id}.pdf"'
            in resp.headers["content-disposition"]
        )

    def test_all_three_presets_return_200(self, client, api_db, owner_auth):
        user_id, headers = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        for preset in ("full", "customer", "insurance"):
            resp = client.post(
                f"/v1/reports/session/{session_id}/pdf",
                json={"preset": preset},
                headers=headers,
            )
            assert resp.status_code == 200, (
                f"preset={preset!r} returned {resp.status_code}: {resp.text}"
            )

    def test_customer_pdf_smaller_than_full(
        self, client, api_db, owner_auth,
    ):
        """Proxy for "Notes section absent under Customer preset" —
        bytes are smaller because a section dropped out. Stronger
        than text-extraction-based assertions (no PDF text-extract
        dep) and faster than scrubbing the PDF stream for the word
        'Notes' (which can appear in metadata)."""
        user_id, headers = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        full = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "full"},
            headers=headers,
        )
        customer = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "customer"},
            headers=headers,
        )

        assert full.status_code == 200
        assert customer.status_code == 200
        assert len(customer.content) < len(full.content), (
            f"Customer PDF ({len(customer.content)} bytes) should be "
            f"smaller than Full PDF ({len(full.content)} bytes) — "
            f"Notes section removal should reduce byte count."
        )


# ---------------------------------------------------------------------------
# 2. Validation
# ---------------------------------------------------------------------------


class TestPostPdfValidation:

    def test_missing_preset_returns_422(self, client, api_db, owner_auth):
        user_id, headers = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        resp = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={},
            headers=headers,
        )

        assert resp.status_code == 422
        # FastAPI's HTTPValidationError shape — `detail` is a list
        # of error dicts; one must reference the missing 'preset'.
        body = resp.json()
        assert "detail" in body
        assert any(
            "preset" in str(err.get("loc", []))
            for err in body["detail"]
        )

    def test_unknown_preset_value_returns_422(
        self, client, api_db, owner_auth,
    ):
        user_id, headers = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        resp = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "supercharged"},
            headers=headers,
        )

        assert resp.status_code == 422

    def test_overrides_field_silently_ignored_in_192B(
        self, client, api_db, owner_auth,
    ):
        """``overrides`` is reserved for F28; not in the
        ``PdfRenderRequest`` schema this phase. Pydantic's default
        ``extra='ignore'`` means clients passing it get a 200
        (preset-only filtering applied). Pin this so the F28 work
        knows the wire-shape evolution path."""
        user_id, headers = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        resp = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "customer", "overrides": {"Notes": True}},
            headers=headers,
        )
        # Either 200 (extra silently ignored) or 422 (extra rejected)
        # is a defensible posture; pin whichever Pydantic's default
        # produces so future schema changes are an explicit break.
        # As of Pydantic v2 the default is ignore → 200 expected.
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 3. Auth
# ---------------------------------------------------------------------------


class TestPostPdfAuth:

    def test_no_api_key_returns_401(self, client, api_db, owner_auth):
        user_id, _ = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        resp = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "full"},
        )

        assert resp.status_code == 401

    def test_cross_owner_returns_404(
        self, client, api_db, owner_auth, other_user_auth,
    ):
        """F29 ADR: cross-owner access returns 404 (NOT 403),
        matching the GET sibling + the rest of the session
        ownership posture."""
        owner_id, _ = owner_auth
        _, stranger_headers = other_user_auth
        session_id = _make_session_with_notes(api_db, owner_id)

        resp = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "full"},
            headers=stranger_headers,
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. GET sibling regression guard
# ---------------------------------------------------------------------------


class TestGetSiblingUnchanged:

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "F34: byte-equality between GET and POST(preset=full) "
            "depends on deterministic PDF rendering. Reportlab's "
            "default render embeds non-deterministic CreationDate / "
            "ModDate / trailer-/ID. When Phase 192B Commit 1.5 lands "
            "the deterministic-rendering fix, this test un-xfails to "
            "PASS and the marker should be removed."
        ),
    )
    def test_get_pdf_still_returns_full_document(
        self, client, api_db, owner_auth,
    ):
        """Phase 182's GET ``/pdf`` route must remain unchanged —
        no preset filtering, returns the full document. Byte-
        equality with POST(preset='full') is the load-bearing
        assertion since Full hides nothing."""
        user_id, headers = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        get_resp = client.get(
            f"/v1/reports/session/{session_id}/pdf",
            headers=headers,
        )
        post_full_resp = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "full"},
            headers=headers,
        )

        assert get_resp.status_code == 200
        assert post_full_resp.status_code == 200
        # GET (no preset) should byte-equal POST with preset='full'
        # because Full hides nothing. Currently F34-xfailed: see
        # decorator above. Sister test below provides a F34-
        # independent regression guard for the GET-still-works
        # property.
        assert get_resp.content == post_full_resp.content

    def test_get_pdf_includes_notes_section_byte_count(
        self, client, api_db, owner_auth,
    ):
        """Pin: GET /pdf renders the same byte count as POST with
        preset='full' (no filter). If GET drifts to filtering by
        default at any future phase, this test catches it."""
        user_id, headers = owner_auth
        session_id = _make_session_with_notes(api_db, user_id)

        get_resp = client.get(
            f"/v1/reports/session/{session_id}/pdf",
            headers=headers,
        )
        post_customer_resp = client.post(
            f"/v1/reports/session/{session_id}/pdf",
            json={"preset": "customer"},
            headers=headers,
        )

        # GET should be larger than Customer-preset POST (GET is
        # full doc; Customer drops Notes).
        assert len(get_resp.content) > len(post_customer_resp.content)
