"""Phase 182 — PDF report generation endpoints tests.

Covers the reporting package + the 6 HTTP endpoints across session /
work-order / invoice reports. Zero AI, zero network.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.session_repo import create_session_for_owner
from motodiag.reporting.builders import (
    ReportBuildError,
    build_invoice_report_doc,
    build_session_report_doc,
    build_work_order_report_doc,
)
from motodiag.reporting.renderers import (
    PDF_AVAILABLE,
    PdfReportRenderer,
    TextReportRenderer,
    get_renderer,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings
    path = str(tmp_path / "phase182.db")
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


def _make_sub(db_path, user_id, tier="individual"):
    with get_connection(db_path) as conn:
        conn.execute(
            """INSERT INTO subscriptions
               (user_id, tier, status, current_period_end)
               VALUES (?, ?, 'active', datetime('now', '+30 days'))""",
            (user_id, tier),
        )


def _make_shop_owner(db_path):
    from motodiag.shop import create_shop, seed_first_owner
    user_id = _make_user(db_path, "owner")
    _make_sub(db_path, user_id, tier="shop")
    _, plaintext = create_api_key(user_id, db_path=db_path)
    shop_id = create_shop("TestShop", db_path=db_path)
    seed_first_owner(shop_id, user_id, db_path=db_path)
    return user_id, plaintext, shop_id


def _seed_wo_for_shop(db_path, shop_id):
    """Create a customer + vehicle + a completed WO in the shop.
    Returns (wo_id, customer_id, vehicle_id)."""
    from motodiag.crm.models import Customer
    from motodiag.crm import customer_repo
    from motodiag.shop import (
        complete_work_order, create_work_order,
        open_work_order, start_work,
    )
    cust_id = customer_repo.create_customer(
        Customer(name="Alice", phone="555-0100", email="a@ex.com"),
        db_path=db_path,
    )
    with get_connection(db_path) as conn:
        c = conn.execute(
            "INSERT INTO vehicles (make, model, year, protocol) "
            "VALUES ('Honda', 'CBR600', 2005, 'none')"
        )
        vid = c.lastrowid
    wo_id = create_work_order(
        shop_id=shop_id, vehicle_id=vid, customer_id=cust_id,
        title="brake service", estimated_hours=2.0, db_path=db_path,
    )
    open_work_order(wo_id, db_path=db_path)
    start_work(wo_id, db_path=db_path)
    complete_work_order(wo_id, actual_hours=2.0, db_path=db_path)
    return wo_id, cust_id, vid


def _generate_invoice(db_path, shop_id, wo_id):
    from motodiag.shop.invoicing import (
        generate_invoice_for_wo, get_invoice_with_items,
    )
    invoice_id = generate_invoice_for_wo(
        wo_id=wo_id, labor_hourly_rate_cents=10000,
        db_path=db_path,
    )
    return get_invoice_with_items(invoice_id, db_path=db_path)


# ===========================================================================
# 1. Renderers
# ===========================================================================


class TestRenderers:

    def test_text_renderer_always_available(self):
        r = TextReportRenderer()
        assert r.content_type.startswith("text/plain")

    def test_text_renderer_basic_output(self):
        r = TextReportRenderer()
        doc = {
            "title": "Hello",
            "subtitle": "World",
            "sections": [
                {"heading": "S1", "body": "A paragraph."},
                {"heading": "S2", "rows": [("k", "v"), ("a", "b")]},
                {"heading": "S3", "bullets": ["one", "two"]},
                {"heading": "S4", "table": {
                    "columns": ["A", "B"],
                    "rows": [[1, 2], [3, 4]],
                }},
            ],
            "footer": "fine print",
        }
        out = r.render(doc).decode("utf-8")
        assert "Hello" in out
        assert "World" in out
        assert "S1" in out and "S2" in out and "S3" in out and "S4" in out
        assert "A paragraph." in out
        assert "k: v" in out
        assert "- one" in out
        assert "A | B" in out
        assert "fine print" in out

    def test_pdf_renderer_available(self):
        assert PDF_AVAILABLE is True

    def test_pdf_renderer_produces_pdf_bytes(self):
        r = PdfReportRenderer()
        doc = {
            "title": "Smoke PDF",
            "sections": [
                {"heading": "Section", "body": "Body text."},
                {"heading": "Rows", "rows": [("k", "v")]},
                {"heading": "Table", "table": {
                    "columns": ["A"], "rows": [["a"]],
                }},
            ],
        }
        body = r.render(doc)
        assert body[:5] == b"%PDF-"
        assert len(body) > 500

    def test_pdf_renderer_escapes_xml_special_chars(self):
        """Paragraph markup uses <...> — user text with '<' must
        not break the builder."""
        r = PdfReportRenderer()
        doc = {
            "title": "A <b>weird</b> & tricky title",
            "sections": [
                {"heading": "H", "body": "1 < 2 & 3 > 0"},
            ],
        }
        body = r.render(doc)
        assert body[:5] == b"%PDF-"

    def test_pdf_renderer_handles_unicode(self):
        r = PdfReportRenderer()
        doc = {
            "title": "Réport",
            "subtitle": "Señor García",
            "sections": [{"heading": "H", "body": "n-tilde: ñ"}],
        }
        body = r.render(doc)
        assert body[:5] == b"%PDF-"

    def test_get_renderer_factory(self):
        assert isinstance(get_renderer("text"), TextReportRenderer)
        assert isinstance(get_renderer("pdf"), PdfReportRenderer)

    def test_get_renderer_unknown_raises(self):
        with pytest.raises(ValueError):
            get_renderer("latex")

    def test_renderer_skips_unknown_section_kind(self):
        """Forward compat — future section shapes shouldn't break
        existing renderers."""
        r = TextReportRenderer()
        doc = {
            "title": "Stable",
            "sections": [
                {"heading": "H", "body": "known"},
                {"heading": "Unknown", "chart": {"data": [1, 2]}},
            ],
        }
        out = r.render(doc).decode("utf-8")
        assert "known" in out
        # Unknown section heading is still rendered; chart key silently
        # ignored
        assert "Unknown" in out


# ===========================================================================
# 2. Session report builder
# ===========================================================================


class TestSessionBuilder:

    def test_build_basic(self, api_db):
        user_id = _make_user(api_db)
        sid = create_session_for_owner(
            owner_user_id=user_id,
            vehicle_make="Honda", vehicle_model="CBR600",
            vehicle_year=2005,
            symptoms=["rough idle", "stalling"],
            fault_codes=["P0171"],
            db_path=api_db,
        )
        doc = build_session_report_doc(sid, user_id, db_path=api_db)
        assert f"#{sid}" in doc["title"]
        assert "Honda CBR600" in doc["subtitle"]
        headings = [s.get("heading") for s in doc["sections"]]
        assert "Vehicle" in headings
        assert "Reported symptoms" in headings
        assert "Fault codes" in headings

    def test_build_no_dtc_no_symptoms_does_not_crash(self, api_db):
        user_id = _make_user(api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        doc = build_session_report_doc(sid, user_id, db_path=api_db)
        headings = [s.get("heading") for s in doc["sections"]]
        assert "Vehicle" in headings
        assert "Reported symptoms" not in headings
        assert "Fault codes" not in headings

    def test_build_cross_user_raises(self, api_db):
        from motodiag.core.session_repo import SessionOwnershipError
        me = _make_user(api_db, "me")
        other = _make_user(api_db, "other")
        sid = create_session_for_owner(
            other, "Honda", "CBR", 2005, db_path=api_db,
        )
        with pytest.raises(SessionOwnershipError):
            build_session_report_doc(sid, me, db_path=api_db)


# ===========================================================================
# 3. Work-order report builder
# ===========================================================================


class TestWorkOrderBuilder:

    def test_build_wo_report_for_member(self, api_db):
        _, _plaintext, shop_id = _make_shop_owner(api_db)
        owner_id = _make_user(api_db, "owner2")
        # use the original owner user (not 'owner2') via shop
        # but _make_shop_owner already created 'owner'
        from motodiag.core.database import get_connection as gc
        with gc(api_db) as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username='owner'"
            ).fetchone()
        user_id = int(row["id"])
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_id)
        doc = build_work_order_report_doc(
            wo_id, user_id, db_path=api_db,
        )
        assert f"#{wo_id}" in doc["title"] or "receipt" in doc["title"].lower()
        headings = [s.get("heading") for s in doc["sections"]]
        assert "Shop & customer" in headings
        assert "Work order" in headings

    def test_build_wo_cross_shop_forbidden(self, api_db):
        from motodiag.shop.rbac import PermissionDenied
        _, _plaintext_a, shop_a = _make_shop_owner(api_db)
        # Create a second user who's NOT a member of shop_a
        outsider = _make_user(api_db, "outsider")
        _make_sub(api_db, outsider, tier="shop")
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_a)
        with pytest.raises(PermissionDenied):
            build_work_order_report_doc(
                wo_id, outsider, db_path=api_db,
            )

    def test_build_wo_missing_raises(self, api_db):
        from motodiag.shop.work_order_repo import WorkOrderNotFoundError
        user_id = _make_user(api_db)
        with pytest.raises(WorkOrderNotFoundError):
            build_work_order_report_doc(
                9999, user_id, db_path=api_db,
            )


# ===========================================================================
# 4. Invoice report builder
# ===========================================================================


class TestInvoiceBuilder:

    def _owner_with_invoice(self, api_db):
        _, _plaintext, shop_id = _make_shop_owner(api_db)
        from motodiag.core.database import get_connection as gc
        with gc(api_db) as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username='owner'"
            ).fetchone()
        user_id = int(row["id"])
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_id)
        inv = _generate_invoice(api_db, shop_id, wo_id)
        return user_id, shop_id, wo_id, inv

    def test_build_invoice_for_member(self, api_db):
        user_id, _, _, inv = self._owner_with_invoice(api_db)
        doc = build_invoice_report_doc(
            inv.id, user_id, db_path=api_db,
        )
        # Totals section must exist
        headings = [s.get("heading") for s in doc["sections"]]
        assert "Totals" in headings
        # The invoice number appears in the title
        assert str(inv.invoice_number or inv.id) in doc["title"]

    def test_build_invoice_missing_raises(self, api_db):
        from motodiag.shop.invoicing import InvoiceNotFoundError
        user_id = _make_user(api_db)
        with pytest.raises(InvoiceNotFoundError):
            build_invoice_report_doc(
                99999, user_id, db_path=api_db,
            )

    def test_build_invoice_cross_shop_forbidden(self, api_db):
        from motodiag.shop.rbac import PermissionDenied
        _, _, _, inv = self._owner_with_invoice(api_db)
        outsider = _make_user(api_db, "outsider")
        _make_sub(api_db, outsider, tier="shop")
        with pytest.raises(PermissionDenied):
            build_invoice_report_doc(
                inv.id, outsider, db_path=api_db,
            )


# ===========================================================================
# 5. Session report HTTP endpoints
# ===========================================================================


class TestSessionReportsHTTP:

    def test_unauth_401(self, api_db):
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/v1/reports/session/1")
        assert r.status_code == 401

    def test_session_preview_happy(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/session/{sid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "title" in body
        assert "sections" in body

    def test_session_pdf_happy(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        sid = create_session_for_owner(
            user_id, "Honda", "CBR", 2005,
            symptoms=["rough idle"], fault_codes=["P0171"],
            db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/session/{sid}/pdf",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-"
        # Content-Disposition should include the session id
        cd = r.headers.get("content-disposition", "")
        assert f"session-{sid}" in cd

    def test_session_cross_user_404(self, api_db):
        me = _make_user(api_db, "me")
        other = _make_user(api_db, "other")
        _, plaintext = create_api_key(me, db_path=api_db)
        sid = create_session_for_owner(
            other, "Honda", "CBR", 2005, db_path=api_db,
        )
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/session/{sid}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404
        r2 = client.get(
            f"/v1/reports/session/{sid}/pdf",
            headers={"X-API-Key": plaintext},
        )
        assert r2.status_code == 404

    def test_session_missing_404(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/reports/session/99999",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404


# ===========================================================================
# 6. Work-order + invoice report HTTP endpoints
# ===========================================================================


class TestShopReportsHTTP:

    def test_wo_report_requires_shop_tier(self, api_db):
        user_id = _make_user(api_db)
        _, plaintext = create_api_key(user_id, db_path=api_db)
        _make_sub(api_db, user_id, tier="individual")
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/reports/work-order/1",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 402

    def test_wo_preview_happy(self, api_db):
        _, plaintext, shop_id = _make_shop_owner(api_db)
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/work-order/{wo_id}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "sections" in body

    def test_wo_pdf_happy(self, api_db):
        _, plaintext, shop_id = _make_shop_owner(api_db)
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/work-order/{wo_id}/pdf",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:5] == b"%PDF-"
        cd = r.headers.get("content-disposition", "")
        assert f"work-order-{wo_id}" in cd

    def test_wo_cross_shop_403(self, api_db):
        _, plaintext_a, shop_a = _make_shop_owner(api_db)
        # Make a second shop-tier user NOT in shop_a
        outsider_id = _make_user(api_db, "outsider")
        _make_sub(api_db, outsider_id, tier="shop")
        _, plaintext_b = create_api_key(outsider_id, db_path=api_db)
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_a)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/work-order/{wo_id}",
            headers={"X-API-Key": plaintext_b},
        )
        assert r.status_code == 403

    def test_wo_missing_404(self, api_db):
        _, plaintext, _ = _make_shop_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/reports/work-order/99999",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404

    def test_invoice_preview_happy(self, api_db):
        _, plaintext, shop_id = _make_shop_owner(api_db)
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_id)
        inv = _generate_invoice(api_db, shop_id, wo_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/invoice/{inv.id}",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        totals_section = next(
            s for s in body["sections"] if s.get("heading") == "Totals"
        )
        # Must surface the invoice total
        assert any("Total" in row[0] for row in totals_section["rows"])

    def test_invoice_pdf_happy(self, api_db):
        _, plaintext, shop_id = _make_shop_owner(api_db)
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_id)
        inv = _generate_invoice(api_db, shop_id, wo_id)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/invoice/{inv.id}/pdf",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 200, r.text
        assert r.content[:5] == b"%PDF-"
        cd = r.headers.get("content-disposition", "")
        assert f"invoice-{inv.id}" in cd

    def test_invoice_cross_shop_403(self, api_db):
        _, plaintext_a, shop_a = _make_shop_owner(api_db)
        wo_id, _, _ = _seed_wo_for_shop(api_db, shop_a)
        inv = _generate_invoice(api_db, shop_a, wo_id)
        outsider_id = _make_user(api_db, "outsider")
        _make_sub(api_db, outsider_id, tier="shop")
        _, plaintext_b = create_api_key(outsider_id, db_path=api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            f"/v1/reports/invoice/{inv.id}",
            headers={"X-API-Key": plaintext_b},
        )
        assert r.status_code == 403

    def test_invoice_missing_404(self, api_db):
        _, plaintext, _ = _make_shop_owner(api_db)
        app = create_app(db_path_override=api_db)
        client = TestClient(app, raise_server_exceptions=False)
        r = client.get(
            "/v1/reports/invoice/99999",
            headers={"X-API-Key": plaintext},
        )
        assert r.status_code == 404


# ===========================================================================
# 7. ReportBuildError mapping
# ===========================================================================


class TestReportBuildError:

    def test_error_class_exists(self):
        err = ReportBuildError("test")
        assert isinstance(err, ValueError)
        assert str(err) == "test"
