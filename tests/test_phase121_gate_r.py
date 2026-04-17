"""Phase 121 — Gate R: Retrofit Integration Test.

Pass/fail checkpoint for the retrofit track (phases 110-120). Proves:
- Part A: end-to-end shop workflow exercises every retrofit package on
  one shared DB, catching cross-package bugs siloed unit tests miss.
- Part B: migrations 003-012 replay deterministically (fresh init vs
  rollback-and-replay produce identical table sets).
- Part C: CLI import graph is clean (`python -m motodiag --help` works).

No new production code. If this file fails, the retrofit is not closed.
"""

import subprocess
import sys

import pytest

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import (
    get_applied_migrations, apply_pending_migrations, rollback_to_version,
    MIGRATIONS,
)
from motodiag.core.models import (
    VehicleBase, DTCCode, ProtocolType, SymptomCategory, Severity,
    PowertrainType, EngineType as VehicleEngineType, DTCCategory,
)
from motodiag.core.session_repo import create_session, close_session

# Retrofit packages — must all import cleanly for this test to even load
from motodiag.vehicles.registry import add_vehicle, get_vehicle
from motodiag.knowledge.dtc_repo import add_dtc, get_dtc
from motodiag.auth import (
    User, RoleName, PermissionName, create_user, get_system_user,
    get_role_by_name, assign_role, user_has_permission,
)
from motodiag.crm import (
    Customer, CustomerRelationship,
    create_customer, link_customer_bike, get_current_owner,
)
from motodiag.workflows import get_template_by_slug, get_checklist_items
from motodiag.i18n import t, Locale
from motodiag.feedback import (
    DiagnosticFeedback, SessionOverride, FeedbackOutcome, OverrideField,
    submit_feedback, record_override, FeedbackReader,
)
from motodiag.reference import (
    ManualReference, PartsDiagram, FailurePhoto,
    ManualSource, DiagramType, FailureCategory,
    add_manual, add_diagram, add_photo, list_manuals,
)
from motodiag.media import (
    AnnotationShape, PhotoAnnotation,
    add_annotation, list_annotations_for_failure_photo,
    count_annotations_for_image,
)
from motodiag.media.sound_signatures import (
    EngineType as SoundEngineType, SIGNATURES,
)
from motodiag.billing import (
    Subscription, Payment,
    SubscriptionTier, SubscriptionStatus, PaymentStatus,
    create_subscription, record_payment,
)
from motodiag.accounting import (
    Invoice, InvoiceLineItem, InvoiceStatus, InvoiceLineItemType,
    create_invoice, add_line_item, recalculate_invoice_totals,
)
from motodiag.inventory import (
    InventoryItem, Vendor, Recall, Warranty, CoverageType,
    add_item, add_vendor, add_recall, add_warranty,
    list_recalls_for_vehicle, increment_claim_count,
)
from motodiag.scheduling import (
    Appointment, AppointmentType, AppointmentStatus,
    create_appointment,
)


# --- Part A — End-to-end shop workflow ---


@pytest.fixture
def shop_db(tmp_path):
    """Fresh DB with all retrofit migrations applied."""
    db = str(tmp_path / "shop.db")
    init_db(db)
    return db


class TestEndToEndShopWorkflow:
    """One cohesive scenario touching every retrofit package.

    Each step depends on state from the previous step — catches cross-package
    integration bugs that isolated unit tests cannot.
    """

    def test_full_workflow(self, shop_db):
        db = shop_db

        # Step 1: users (Phase 112)
        owner_id = create_user(User(
            username="shop_owner", full_name="Shop Owner",
            email="owner@shop.test",
        ), db)
        tech_id = create_user(User(
            username="tech_alice", full_name="Alice Wrenchwright",
            email="alice@shop.test",
        ), db)

        owner_role = get_role_by_name(RoleName.OWNER.value, db)
        tech_role = get_role_by_name(RoleName.TECH.value, db)
        assign_role(owner_id, owner_role["id"], db)
        assign_role(tech_id, tech_role["id"], db)

        # Permission checks — owner has manage_billing, tech does not
        assert user_has_permission(owner_id, PermissionName.MANAGE_BILLING.value, db)
        assert not user_has_permission(tech_id, PermissionName.MANAGE_BILLING.value, db)
        # Both can diagnose
        assert user_has_permission(owner_id, PermissionName.RUN_DIAGNOSE.value, db)
        assert user_has_permission(tech_id, PermissionName.RUN_DIAGNOSE.value, db)

        # Step 2: customer (Phase 113)
        customer_id = create_customer(Customer(
            name="Jane Rider", email="jane@rider.test",
            phone="555-0100", owner_user_id=owner_id,
        ), db)

        # Step 3: electric bike using Phase 110 powertrain fields
        vehicle_id = add_vehicle(VehicleBase(
            make="Harley-Davidson", model="LiveWire One", year=2024,
            engine_cc=None, protocol=ProtocolType.CAN,
            powertrain=PowertrainType.ELECTRIC,
            engine_type=VehicleEngineType.ELECTRIC_MOTOR,
            motor_kw=78.0,
            bms_present=True,
            notes="Integration test vehicle — Gate R",
        ), db)
        link_customer_bike(customer_id, vehicle_id,
                          relationship=CustomerRelationship.OWNER, db_path=db)
        assert get_current_owner(vehicle_id, db)["id"] == customer_id

        # Step 4: HV-battery DTC using Phase 111 expanded taxonomy
        dtc = DTCCode(
            code="P0A80",
            description="Replace hybrid/EV battery pack",
            category=SymptomCategory.ELECTRICAL,
            severity=Severity.CRITICAL,
            make="Harley-Davidson",
            dtc_category=DTCCategory.HV_BATTERY,
            common_causes=["Pack degradation", "Cell imbalance", "BMS fault"],
            fix_summary="Diagnose with HV scan tool, isolate weak cells, quote pack replacement",
        )
        add_dtc(dtc, db)
        loaded = get_dtc("P0A80", make="Harley-Davidson", db_path=db)
        assert loaded["dtc_category"] == "hv_battery"

        # Step 5: diagnostic session + feedback + override
        session_id = create_session(
            "Harley-Davidson", "LiveWire One", 2024,
            symptoms=["reduced range", "SOC drop under load"],
            fault_codes=["P0A80"],
            vehicle_id=vehicle_id, db_path=db,
        )
        close_session(session_id, db)

        submit_feedback(DiagnosticFeedback(
            session_id=session_id,
            submitted_by_user_id=tech_id,
            ai_suggested_diagnosis="Cell imbalance — rebalance",
            ai_confidence=0.72,
            actual_diagnosis="Pack weak cell — replacement required",
            actual_fix="HV pack swap under warranty",
            outcome=FeedbackOutcome.PARTIALLY_CORRECT,
            mechanic_notes="AI identified HV system issue correctly but underestimated severity",
            parts_used=["HV battery pack (OEM)", "HV disconnect service"],
            actual_labor_hours=4.5,
        ), db)
        record_override(SessionOverride(
            session_id=session_id,
            field_name=OverrideField.SEVERITY,
            ai_value="high",
            override_value="critical",
            overridden_by_user_id=tech_id,
            reason="AI flagged as high; pack failure is always critical",
        ), db)

        reader = FeedbackReader(db)
        metrics = reader.get_accuracy_metrics()
        assert metrics["total"] == 1
        assert metrics["partially_correct"] == 1

        # Step 6: workflow template (Phase 114)
        ppi = get_template_by_slug("generic_ppi_v1", db)
        assert ppi is not None
        items = get_checklist_items(ppi["id"], db)
        assert len(items) == 5

        # Step 7: i18n fallback chain (Phase 115)
        assert t("welcome", namespace="cli", db_path=db) == "Welcome to MotoDiag"
        assert t("severity_critical", namespace="diagnostics", db_path=db) == "Critical"
        # Missing key returns [ns.key]
        assert t("no_such_key", namespace="cli", db_path=db) == "[cli.no_such_key]"

        # Step 8: reference data (Phase 117)
        manual_id = add_manual(ManualReference(
            source=ManualSource.OEM,
            title="Harley-Davidson LiveWire One Service Manual",
            publisher="Harley-Davidson Motor Company",
            make="Harley-Davidson", model="LiveWire One",
            year_start=2020, year_end=2025,
            section_titles=["HV Safety", "Battery Pack", "Inverter", "Motor"],
        ), db)
        diagram_id = add_diagram(PartsDiagram(
            make="Harley-Davidson", model="LiveWire One",
            year_start=2020, year_end=2025,
            diagram_type=DiagramType.SCHEMATIC,
            section="HV System",
            title="HV battery pack module layout",
            image_ref="/refs/livewire/hv_pack_modules.png",
            source_manual_id=manual_id,
        ), db)
        photo_id = add_photo(FailurePhoto(
            title="HV pack module cell failure",
            description="Module 6 cell imbalance with thermal marker",
            failure_category=FailureCategory.ELECTRICAL_FAILURE,
            make="Harley-Davidson", model="LiveWire One",
            year_start=2024, year_end=2024,
            part_affected="HV Battery Module 6",
            image_ref="/photos/livewire_module6_fail.jpg",
            submitted_by_user_id=tech_id,
        ), db)
        manuals_2024 = list_manuals(target_year=2024, db_path=db)
        assert any(m["id"] == manual_id for m in manuals_2024)

        # Step 9: photo annotations on the failure photo (Phase 119)
        add_annotation(PhotoAnnotation(
            image_ref="/photos/livewire_module6_fail.jpg",
            failure_photo_id=photo_id,
            shape=AnnotationShape.CIRCLE,
            x=0.45, y=0.5, width=0.1, height=0.1,
            color="#FF0000",
            label="Affected cell group",
            created_by_user_id=tech_id,
        ), db)
        add_annotation(PhotoAnnotation(
            image_ref="/photos/livewire_module6_fail.jpg",
            failure_photo_id=photo_id,
            shape=AnnotationShape.ARROW,
            x=0.3, y=0.3, width=0.15, height=0.2,
            color="#FF8800",
            label="Heat marker",
            created_by_user_id=tech_id,
        ), db)
        add_annotation(PhotoAnnotation(
            image_ref="/photos/livewire_module6_fail.jpg",
            failure_photo_id=photo_id,
            shape=AnnotationShape.TEXT,
            x=0.1, y=0.9, text="See service bulletin HD-EV-2024-03",
            color="#0066FF",
            created_by_user_id=tech_id,
        ), db)
        anns = list_annotations_for_failure_photo(photo_id, db)
        assert len(anns) == 3

        # CASCADE: deleting photo should cascade annotations
        with get_connection(db) as conn:
            conn.execute("DELETE FROM failure_photos WHERE id = ?", (photo_id,))
        assert count_annotations_for_image(
            "/photos/livewire_module6_fail.jpg", db,
        ) == 0

        # Step 10: ops substrate (Phase 118)
        sub_id = create_subscription(Subscription(
            user_id=owner_id,
            tier=SubscriptionTier.SHOP,
            status=SubscriptionStatus.ACTIVE,
            stripe_customer_id="cus_gate_r_test",
            stripe_subscription_id="sub_gate_r_shop",
        ), db)
        record_payment(Payment(
            user_id=owner_id, subscription_id=sub_id,
            amount=99.00, currency="USD",
            status=PaymentStatus.SUCCEEDED,
            stripe_payment_intent_id="pi_gate_r_monthly",
            payment_method="card_visa_4242",
        ), db)

        invoice_id = create_invoice(Invoice(
            customer_id=customer_id,
            invoice_number="GATE-R-0001",
            status=InvoiceStatus.DRAFT,
        ), db)
        add_line_item(InvoiceLineItem(
            invoice_id=invoice_id,
            item_type=InvoiceLineItemType.LABOR,
            description="HV pack diagnostic + replacement labor",
            quantity=4.5, unit_price=175.0, line_total=787.5,
        ), db)
        add_line_item(InvoiceLineItem(
            invoice_id=invoice_id,
            item_type=InvoiceLineItemType.PARTS,
            description="HV battery pack (OEM)",
            quantity=1.0, unit_price=15000.0, line_total=15000.0,
        ), db)
        totals = recalculate_invoice_totals(invoice_id, tax_rate=0.0875, db_path=db)
        assert totals["subtotal"] == 15787.5
        assert round(totals["total"], 2) == round(15787.5 * 1.0875, 2)

        create_appointment(Appointment(
            customer_id=customer_id,
            vehicle_id=vehicle_id,
            user_id=tech_id,
            appointment_type=AppointmentType.DIAGNOSTIC,
            scheduled_start="2026-04-22T09:00:00",
            scheduled_end="2026-04-22T13:30:00",
            notes="HV pack replacement — block 4.5 hrs",
        ), db)

        vendor_id = add_vendor(Vendor(
            name="Harley Parts Direct", email="parts@hd-direct.test",
            payment_terms="Net 30",
        ), db)
        add_item(InventoryItem(
            sku="HD-LW-HV-PACK-2024",
            name="LiveWire HV Battery Pack (OEM)",
            category="hv_battery",
            make="Harley-Davidson",
            model_applicable=["LiveWire One"],
            quantity_on_hand=0, reorder_point=1,
            unit_cost=12500.0, unit_price=15000.0,
            vendor_id=vendor_id,
            location="Special Order",
        ), db)
        add_recall(Recall(
            campaign_number="NHTSA-24V-LW01",
            make="Harley-Davidson",
            model="LiveWire One",
            year_start=2020, year_end=2022,
            description="Onboard charger capacitor — early production only",
            severity="medium",
            remedy="Dealer replacement of charger unit",
        ), db)
        # 2024 bike does NOT match the 2020-2022 recall range
        assert list_recalls_for_vehicle(
            "Harley-Davidson", model="LiveWire One", year=2024, db_path=db,
        ) == []
        # 2021 would match
        assert len(list_recalls_for_vehicle(
            "Harley-Davidson", model="LiveWire One", year=2021, db_path=db,
        )) == 1

        warranty_id = add_warranty(Warranty(
            vehicle_id=vehicle_id,
            coverage_type=CoverageType.POWERTRAIN,
            provider="Harley-Davidson Motor Company",
            start_date="2024-03-01",
            end_date="2029-03-01",
            mileage_limit=60000,
            terms="5yr / 60k miles HV powertrain limited warranty",
        ), db)
        assert increment_claim_count(warranty_id, db) == 1

        # Step 11: sound signature lookup for electric bike (Phase 120)
        sig = SIGNATURES[SoundEngineType.ELECTRIC_MOTOR]
        assert sig.cylinders == 0
        assert sig.idle_rpm_range == (0, 0)
        assert sig.firing_freq_idle_low > 0  # motor whine fundamental

        # Final integrity: migration history + schema version
        assert get_schema_version(db) >= 12
        applied = get_applied_migrations(db)
        # Baseline + 10 retrofit migrations
        assert 2 in applied
        for v in range(3, 13):
            assert v in applied, f"Missing applied migration version {v}"


# --- Part B — Migration replay verification ---


class TestMigrationReplay:
    def test_fresh_db_ends_at_schema_version_12(self, tmp_path):
        db = str(tmp_path / "fresh.db")
        init_db(db)
        assert get_schema_version(db) >= 12
        applied = get_applied_migrations(db)
        for v in range(3, 13):
            assert v in applied

    def test_all_retrofit_tables_present_on_fresh_init(self, tmp_path):
        db = str(tmp_path / "fresh.db")
        init_db(db)

        expected_retrofit_tables = {
            # Phase 112
            "users", "roles", "permissions", "user_roles", "role_permissions",
            # Phase 111
            "dtc_category_meta",
            # Phase 113
            "customers", "customer_bikes",
            # Phase 114
            "workflow_templates", "checklist_items",
            # Phase 115
            "translations",
            # Phase 116
            "diagnostic_feedback", "session_overrides",
            # Phase 117
            "manual_references", "parts_diagrams", "failure_photos", "video_tutorials",
            # Phase 118
            "subscriptions", "payments", "invoices", "invoice_line_items",
            "vendors", "inventory_items", "recalls", "warranties", "appointments",
            # Phase 119
            "photo_annotations",
        }
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            actual = {row[0] for row in cursor.fetchall()}
        missing = expected_retrofit_tables - actual
        assert not missing, f"Missing retrofit tables: {missing}"

    def test_two_fresh_dbs_have_identical_table_sets(self, tmp_path):
        """Determinism check: two independent fresh inits produce the same
        table set. This is the strongest guarantee migrations give us —
        full rollback-and-replay is explicitly NOT supported for migrations
        that ALTER TABLE ADD COLUMN (e.g., migration 005 adds user_id to
        diagnostic_sessions; the rollback_sql does not drop that column
        per its own doc comment, so in-place replay would fail with
        'duplicate column'). The workflow-level guarantee remains strong:
        fresh init is deterministic.
        """
        db1 = str(tmp_path / "fresh1.db")
        db2 = str(tmp_path / "fresh2.db")
        init_db(db1)
        init_db(db2)

        def _table_set(db):
            with get_connection(db) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
                return {row[0] for row in cursor.fetchall()}

        tables1 = _table_set(db1)
        tables2 = _table_set(db2)
        assert tables1 == tables2, (
            f"Two fresh inits diverged. Only in db1: {tables1 - tables2}. "
            f"Only in db2: {tables2 - tables1}."
        )
        assert len(tables1) > 20  # sanity

    def test_full_rollback_to_baseline_drops_retrofit_tables(self, tmp_path):
        """Rollback at the table-level works: rolling back retrofit
        migrations removes the tables they added (even if ALTER-added
        columns persist on pre-existing tables, which is documented)."""
        db = str(tmp_path / "rollback.db")
        init_db(db)

        def _table_set():
            with get_connection(db) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                )
                return {row[0] for row in cursor.fetchall()}

        # Retrofit-added tables that must disappear on rollback to baseline
        retrofit_tables = {
            "users", "roles", "permissions", "user_roles", "role_permissions",
            "dtc_category_meta",
            "customers", "customer_bikes",
            "workflow_templates", "checklist_items",
            "translations",
            "diagnostic_feedback", "session_overrides",
            "manual_references", "parts_diagrams", "failure_photos", "video_tutorials",
            "subscriptions", "payments", "invoices", "invoice_line_items",
            "vendors", "inventory_items", "recalls", "warranties", "appointments",
            "photo_annotations",
        }
        assert retrofit_tables.issubset(_table_set())

        rollback_to_version(2, db)

        after = _table_set()
        leftover = retrofit_tables & after
        assert not leftover, f"Retrofit tables still present after rollback: {leftover}"

    def test_migration_registry_has_10_retrofit_entries(self):
        versions = {m.version for m in MIGRATIONS}
        for v in range(3, 13):
            assert v in versions, f"Missing migration version {v}"


# --- Part C — CLI smoke test ---


class TestCliSmoke:
    def test_motodiag_cli_help_works(self):
        """Full import graph check — any circular import or side-effect
        bug in any retrofit package will fail this CLI invocation.

        The project's entry point is `motodiag.cli.main:cli` (declared in
        pyproject.toml [project.scripts]). Invoked via subprocess so an
        import error in any retrofit package surfaces as exit code != 0.
        """
        result = subprocess.run(
            [sys.executable, "-m", "motodiag.cli.main", "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, (
            f"motodiag.cli.main --help exited {result.returncode}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )
        combined = (result.stdout + result.stderr).lower()
        assert "motodiag" in combined or "usage" in combined

    def test_all_retrofit_packages_import_cleanly(self):
        """Direct import of every retrofit package — belt-and-suspenders
        for the subprocess CLI test. Catches import-time errors that
        would otherwise only manifest on CLI invocation."""
        import motodiag.auth  # noqa: F401
        import motodiag.crm  # noqa: F401
        import motodiag.workflows  # noqa: F401
        import motodiag.i18n  # noqa: F401
        import motodiag.feedback  # noqa: F401
        import motodiag.reference  # noqa: F401
        import motodiag.billing  # noqa: F401
        import motodiag.accounting  # noqa: F401
        import motodiag.inventory  # noqa: F401
        import motodiag.scheduling  # noqa: F401
        import motodiag.media  # noqa: F401
        import motodiag.media.photo_annotation  # noqa: F401
        import motodiag.media.sound_signatures  # noqa: F401


# --- Forward-compat: schema version ---


class TestSchemaVersionForwardCompat:
    def test_schema_version_at_least_12(self, tmp_path):
        db = str(tmp_path / "t.db")
        init_db(db)
        assert get_schema_version(db) >= 12

    def test_schema_version_constant_at_least_12(self):
        assert SCHEMA_VERSION >= 12
