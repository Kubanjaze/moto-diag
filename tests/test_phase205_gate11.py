"""Phase 205 — Gate 11: desktop + mobile end-to-end integration.

Track J opens here. Phase 204 (Gate 10) verified the MOBILE path on real
hardware, so re-running it would be slow, green and information-free.
This gate takes the half that has had far less real use: the DESKTOP.

Why that is the right target, from the Step 0 audit: Gate 8's roadmap row
claims to close Track G, but ``test_phase174_gate8.py`` makes **3**
``runner.invoke`` calls against **54** direct repo calls. Track G's ~96
shop subcommands were therefore exercised through the REPO LAYER, not
through the CLI. The shop CLI is at once the least-tested desktop surface
and the one a shop owner actually touches.

Four classes, in the Gate 5/6/7 house style:

- :class:`TestDesktopEndToEnd` — one shop-owner job, every step a real
  ``runner.invoke`` against the FULL cli root (not a partial group).
- :class:`TestCrossSurfaceAgreement` — re-read the CLI-created records
  through the API and assert the two front doors of one database agree.
- :class:`TestDesktopCannotFinishTheJob` — executable documentation of
  the four verbs the CLI lacks. These PASS today and are MEANT to fail
  the day someone adds a verb, which is the cheapest possible reminder
  to close the ticket.
- :class:`TestContractSnapshot` — the committed mobile ``openapi.json``
  still matches the live spec.

Zero production code, per the rule every prior gate kept.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from motodiag.api.app import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.cli.main import cli as real_cli
from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db

REPO_ROOT = Path(__file__).resolve().parents[1]
MOBILE_SNAPSHOT = (
    REPO_ROOT.parent / "moto-diag-mobile" / "api-schema" / "openapi.json"
)


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "gate11.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _run(args, expect_ok=True):
    """Invoke the REAL cli root. Gate 8 built a partial root containing
    only the shop group, which cannot catch a command that fails to
    register on the real one."""
    result = CliRunner().invoke(real_cli, args, catch_exceptions=False)
    if expect_ok:
        assert result.exit_code == 0, (
            f"`motodiag {' '.join(args)}` exited "
            f"{result.exit_code}:\n{result.output}"
        )
    return result


def _last_id(db_path, table):
    """Read the id the CLI just created.

    Deliberately NOT parsed out of the CLI's output: that would pin the
    human-readable wording ("Added vehicle #1") rather than the
    behaviour, and a copy edit would fail the gate for no reason. The
    claim under test is that the CLI CAN DO the step, which its exit
    code and the resulting row both attest.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            f"SELECT id FROM {table} ORDER BY id DESC LIMIT 1",
        ).fetchone()
    assert row is not None, f"CLI step created no row in {table}"
    return int(row[0])


def _seed_user(db_path, username="gate11_owner", tier="shop"):
    with get_connection(db_path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) "
            "VALUES (?, ?, ?, 1)",
            (username, f"{username}@ex.com", tier),
        ).lastrowid
        conn.execute(
            "INSERT INTO subscriptions (user_id, tier, status, "
            " current_period_end) VALUES (?, ?, 'active', "
            " datetime('now', '+30 days'))",
            (uid, tier),
        )
    return uid


def _seed_part(db_path, slug="gate11-brake-pad", cents=4999):
    with get_connection(db_path) as conn:
        return conn.execute(
            """INSERT INTO parts (slug, oem_part_number, brand,
               description, category, make, model_pattern,
               typical_cost_cents, verified_by)
               VALUES (?, 'OEM-G11', 'EBC', 'front brake pad', 'brakes',
                       'harley-davidson', '%', ?, 'gate11')""",
            (slug, cents),
        ).lastrowid


# ===========================================================================
# 1. The desktop walk — every step through the CLI
# ===========================================================================


class TestDesktopEndToEnd:
    """One shop owner, one job, start to invoice, entirely through the
    CLI. Any step that cannot be done from the CLI is recorded rather
    than routed around silently — see TestDesktopCannotFinishTheJob."""

    def test_shop_owner_walks_a_job_to_a_paid_invoice(self, cli_db):
        owner = _seed_user(cli_db)
        part_id = _seed_part(cli_db)

        # --- the shop exists -------------------------------------------
        _run([
            "shop", "profile", "init", "--name", "Gate 11 Cycles",
            "--city", "Austin", "--state", "TX",
        ])
        shop_id = _last_id(cli_db, "shops")

        # --- a customer and their bike ---------------------------------
        _run([
            "shop", "customer", "add", "--name", "Dana Reyes",
            "--email", "dana@ex.com", "--phone", "555-0142",
        ])
        customer_id = _last_id(cli_db, "customers")

        _run([
            "garage", "add", "--make", "Harley-Davidson",
            "--model", "Road King", "--year", "2012",
        ])
        bike_id = _last_id(cli_db, "vehicles")

        # --- the work order --------------------------------------------
        _run([
            "shop", "work-order", "create",
            "--shop", str(shop_id), "--customer", str(customer_id),
            "--bike", str(bike_id), "--title", "20k service",
            "--estimated-hours", "2.5",
        ])
        wo_id = _last_id(cli_db, "work_orders")

        # --- parts: add, order, receive --------------------------------
        _run([
            "shop", "parts-needs", "add", str(wo_id),
            "-p", str(part_id), "-q", "2",
        ])
        lines = _run(["shop", "parts-needs", "list", "--wo", str(wo_id)]).output
        # Assert on the NUMBERS, not the prose: the Rich table truncates
        # the description to fit, so a substring check on the part name
        # pins column widths rather than behaviour. The unit cost and
        # line subtotal came from the catalog row, so seeing them proves
        # the line was created, priced and rendered.
        assert "4999" in lines, lines
        assert "9998" in lines, f"2 x 4999 should subtotal 9998:\n{lines}"

        with get_connection(cli_db) as conn:
            wop_id = conn.execute(
                "SELECT id FROM work_order_parts WHERE work_order_id = ?",
                (wo_id,),
            ).fetchone()[0]

        _run(["shop", "parts-needs", "mark-ordered", str(wop_id)])
        _run(["shop", "parts-needs", "mark-received", str(wop_id)])

        with get_connection(cli_db) as conn:
            status = conn.execute(
                "SELECT status FROM work_order_parts WHERE id = ?",
                (wop_id,),
            ).fetchone()[0]
        assert status == "received", (
            f"CLI parts lifecycle stalled at {status!r}"
        )

        # --- do the work -----------------------------------------------
        # NOTE: no `open` verb on the CLI — a work order goes draft →
        # in_progress via `start`. The API's transition endpoint DOES
        # accept an "open" action (api/routes/shop_mgmt.py), so this is
        # another CLI/API asymmetry; pinned in
        # TestDesktopCannotFinishTheJob below.
        _run(["shop", "work-order", "start", str(wo_id)])
        # NOTE: actual hours must be hand-typed here. There is no CLI for
        # the Phase 202 time-entry ledger, so a desktop shop cannot
        # measure labour, only assert it. Pinned below.
        _run([
            "shop", "work-order", "complete", str(wo_id),
            "--actual-hours", "2.75",
        ])

        # --- bill it ----------------------------------------------------
        _run([
            "shop", "invoice", "generate", str(wo_id),
            "--tax-rate", "0.0825", "--hourly-rate", "9500",
        ])
        invoice_id = _last_id(cli_db, "invoices")
        _run(["shop", "invoice", "mark-paid", str(invoice_id)])

        with get_connection(cli_db) as conn:
            inv = dict(conn.execute(
                "SELECT status, subtotal, tax_amount, total "
                "FROM invoices WHERE id = ?",
                (invoice_id,),
            ).fetchone())
        assert inv["status"] == "paid"
        # The invoice must actually price the job: labour at the given
        # hourly rate plus the received part, taxed. A zero total would
        # mean the CLI produced a document with no content.
        assert inv["total"] > 0, f"invoice totalled nothing: {inv}"
        assert inv["subtotal"] > 0, f"invoice has no line items: {inv}"
        assert inv["tax_amount"] > 0, (
            f"8.25% tax was requested but not applied: {inv}"
        )

        # --- and the shop can see it ------------------------------------
        _run(["shop", "analytics", "snapshot", "--shop", str(shop_id)])


# ===========================================================================
# 2. The two front doors must agree
# ===========================================================================


class TestCrossSurfaceAgreement:
    """The CLI and the API import the same domain modules over one DB, so
    they SHOULD agree. This asserts it rather than assuming it — drift
    between the two front doors would be invisible until a mechanic and
    an owner compared screens."""

    def test_a_cli_created_work_order_reads_identically_over_http(
        self, cli_db,
    ):
        owner = _seed_user(cli_db, "gate11_api_owner")
        _, key = create_api_key(owner, db_path=cli_db)

        _run([
            "shop", "profile", "init", "--name", "Cross Surface Cycles",
        ])
        shop_id = _last_id(cli_db, "shops")

        from motodiag.shop import seed_first_owner
        seed_first_owner(shop_id, owner, db_path=cli_db)

        _run(["shop", "customer", "add", "--name", "Sam Okafor"])
        customer_id = _last_id(cli_db, "customers")
        _run([
            "garage", "add", "--make", "Honda", "--model", "CB500",
            "--year", "2020",
        ])
        bike_id = _last_id(cli_db, "vehicles")
        _run([
            "shop", "work-order", "create", "--shop", str(shop_id),
            "--customer", str(customer_id), "--bike", str(bike_id),
            "--title", "Chain and sprockets",
        ])
        wo_id = _last_id(cli_db, "work_orders")

        client = TestClient(
            create_app(db_path_override=cli_db),
            raise_server_exceptions=False,
        )
        resp = client.get(
            f"/v1/shop/{shop_id}/work-orders/{wo_id}",
            headers={"X-API-Key": key},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()

        with get_connection(cli_db) as conn:
            row = dict(conn.execute(
                "SELECT * FROM work_orders WHERE id = ?", (wo_id,),
            ).fetchone())

        # Field-level agreement on what both surfaces claim to show.
        assert body["id"] == row["id"] == wo_id
        assert body["title"] == row["title"] == "Chain and sprockets"
        assert body["customer_id"] == row["customer_id"] == customer_id
        assert body["shop_id"] == row["shop_id"] == shop_id
        assert body["status"] == row["status"]


# ===========================================================================
# 3. Executable documentation of what the desktop CANNOT do
# ===========================================================================


class TestDesktopCannotFinishTheJob:
    """These tests assert ABSENCES, and are meant to fail the day the gap
    closes — the cheapest possible reminder to close the ticket.

    The finding: a desktop-only shop cannot finish a job the way a
    phone-equipped one can. Time tracking, reporting and share links are
    API-only, and the parts lifecycle stops one step short.
    """

    def _subcommands(self, *path):
        """Read click's actual command registry.

        Grepping --help prose was the first attempt and it was wrong:
        "time" matches "AI labor time estimation", so the test failed on
        a description rather than a command. Ask the registry.
        """
        node = real_cli
        for name in path:
            node = node.commands[name]
        return set(node.commands)

    def test_no_cli_verb_installs_a_received_part(self):
        """F59. `mark_part_installed` exists in the repo layer and is
        tested; no CLI reaches it, so the lifecycle ends at 'received'."""
        verbs = self._subcommands("shop", "parts-needs")
        assert {"mark-ordered", "mark-received"} <= verbs
        assert "mark-installed" not in verbs, (
            "A CLI verb for installing a part now exists — close F59 and "
            "delete this assertion."
        )

    def test_no_cli_group_logs_actual_labour(self):
        """Phase 202's time-entry ledger is reachable only from
        api/routes/time_tracking.py. On the desktop, `--actual-hours` on
        `work-order complete` is a claim, not a measurement."""
        groups = self._subcommands("shop")
        for name in ("time", "time-entry", "time-entries", "clock", "timer"):
            assert name not in groups, (
                f"A '{name}' group now exists in the shop CLI — the "
                "desktop can measure labour; update this gate."
            )

    def test_the_cli_has_no_open_verb_the_api_accepts(self):
        """Smaller asymmetry, found by walking it: the API's WO
        transition endpoint accepts an "open" action, and the CLI has no
        such verb — a work order goes draft → in_progress via `start`.
        Harmless today because `start` covers it, but the two surfaces
        describe the same lifecycle with different vocabularies, which
        is how the F37 enum-drift family begins."""
        verbs = self._subcommands("shop", "work-order")
        assert "start" in verbs
        assert "open" not in verbs, (
            "The CLI gained an `open` verb — check it agrees with the "
            "API's transition action set and update this gate."
        )

    def test_no_cli_renders_a_report_or_invoice_pdf(self):
        """`motodiag.reporting` is reachable only from
        api/routes/reports.py. A desktop shop cannot hand a customer
        anything printed."""
        verbs = self._subcommands("shop", "invoice")
        assert not any("pdf" in v for v in verbs), (
            f"Invoice PDF rendering reached the CLI ({verbs}) — update "
            "this gate."
        )

    def test_no_cli_mints_a_customer_share_link(self):
        """Phase 200's share links are API-only, so a desktop shop
        cannot send a customer the report the mobile app can."""
        groups = self._subcommands("shop")
        assert "share" not in groups, (
            "Share-link minting reached the CLI — update this gate."
        )


# ===========================================================================
# 4. The contract the mobile app is generated from
# ===========================================================================


class TestContractSnapshot:
    """The mobile app's TypeScript types are generated from a COMMITTED
    snapshot that a human refreshes by hand. Nothing has ever asserted
    the snapshot still matches the running API, so the app can compile
    against a contract the server no longer honours — silently, until a
    device session. Structural comparison, not byte-wise: a prose edit to
    a description should not fail the build."""

    def test_snapshot_exists(self):
        assert MOBILE_SNAPSHOT.is_file(), (
            f"mobile OpenAPI snapshot missing at {MOBILE_SNAPSHOT}"
        )

    def test_every_live_path_is_in_the_committed_snapshot(self):
        live = create_app().openapi()
        snapshot = json.loads(MOBILE_SNAPSHOT.read_text())

        live_ops = {
            (path, method)
            for path, item in live["paths"].items()
            for method in item
            if method in {"get", "post", "put", "patch", "delete"}
        }
        snap_ops = {
            (path, method)
            for path, item in snapshot["paths"].items()
            for method in item
            if method in {"get", "post", "put", "patch", "delete"}
        }

        missing = sorted(live_ops - snap_ops)
        assert not missing, (
            "The API exposes operations the mobile snapshot does not "
            "know about — run `npm run refresh-api-schema` and "
            f"regenerate types. Missing: {missing[:10]}"
        )

    def test_the_snapshot_does_not_promise_routes_the_api_dropped(self):
        """The more dangerous direction: the app generates a typed client
        for an endpoint the server no longer serves, and the failure is a
        404 at runtime rather than a compile error."""
        live = create_app().openapi()
        snapshot = json.loads(MOBILE_SNAPSHOT.read_text())

        live_ops = {
            (path, method)
            for path, item in live["paths"].items()
            for method in item
            if method in {"get", "post", "put", "patch", "delete"}
        }
        snap_ops = {
            (path, method)
            for path, item in snapshot["paths"].items()
            for method in item
            if method in {"get", "post", "put", "patch", "delete"}
        }

        stale = sorted(snap_ops - live_ops)
        assert not stale, (
            "The mobile snapshot describes operations the API no longer "
            f"serves — these would 404 at runtime: {stale[:10]}"
        )


# ===========================================================================
# 5. Anti-regression — the earlier gates still hold
# ===========================================================================


class TestRegression:
    """Mirrors test_phase159_gate_7.py:540 — a gate guards the gates
    before it."""

    @pytest.mark.parametrize("gate_file", [
        "tests/test_phase133_gate_5.py",
        "tests/test_phase147_gate_6.py",
        "tests/test_phase159_gate_7.py",
        "tests/test_phase174_gate8.py",
        "tests/test_phase184_gate9.py",
    ])
    def test_earlier_gate_still_passes(self, gate_file):
        result = subprocess.run(
            [sys.executable, "-m", "pytest", gate_file, "-q",
             "-p", "no:cacheprovider"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=900,
        )
        assert result.returncode == 0, (
            f"{gate_file} regressed:\n{result.stdout[-2000:]}"
        )

    def test_schema_version_pin(self):
        assert SCHEMA_VERSION == 55, (  # f9-noqa: ssot-pin contract-pin: Gate 11 schema-bump pin. The literal is the point — importing the constant would make this assert `x == x` and it would never fail. Bumped 51→52 at Phase 235B (migration 052 rebuilt known_issues to widen the source CHECK with `regulation`, for entries quoted from primary legal text). Previously 50→51 at Phase 211 (migration 051 added known_issues.source). Bumping requires a corresponding new migration in src/motodiag/core/migrations.py. Bumped 52→53 at Phase 240C (migration 053 replaces idx_known_issues_sort with an expression index on the severity rank, because the ordering fix moved the queries from `ORDER BY severity DESC` — lexicographic, `critical` last — to a CASE rank that the old index cannot serve). Bumped 53→54 at Phase 244D (migration 054 deduplicates known_issues — 6,600 rows for 660 distinct issues, every entry present exactly ten times, because the table had no uniqueness constraint and the loader was not idempotent — and adds a UNIQUE EXPRESSION index over (COALESCE(make,''), COALESCE(model,''), title); COALESCE rather than a plain column constraint because 43 seeded entries carry a NULL model and SQLite treats NULLs as DISTINCT in a UNIQUE constraint, so the naive form would have left those free to keep duplicating behind something that looked like a fix). Bumped 54→55 at Phase 244F (migration 055 adds the known_issue_makes junction: `known_issues.make` is one free-text column holding a marque, a list of marques, a scope phrase and in one row a whole sentence of findings, so LiveWire and Damon were not queryable makes AT ALL — all 24 LiveWire rows sit inside 'Harley-Davidson, LiveWire' and Phase 243's entire output was unreachable. The column is not modified; the junction is derived from it by knowledge/marques.extract_marques).
            "SCHEMA_VERSION moved — confirm a migration accompanies it "
            "and update this pin."
        )
