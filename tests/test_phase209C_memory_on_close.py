"""Phase 209C — closing a session updates what the shop remembers.

F79, decided 2026-09-17: recompile a machine's memory on session close.

Tested through the entry points a close actually arrives by -- the API's close
route, a PATCH to ``closed``, the CLI's ``diagnose`` flow -- because CLAUDE.md
gate item 6 asks for the user-reachable path, and because a hook tested only
as a function is the integration-gap family this codebase keeps finding.

Most of the tests are about the part Step 0 found underneath the one-line
ticket: a fact's identity includes its text, nothing ever superseded one, and
so an edited diagnosis would have sat in recall next to the version it
replaced.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.core.models import ProtocolType, VehicleBase
from motodiag.memory import (
    MemoryFact,
    compile_vehicle_detailed,
    insert_facts,
    list_facts,
    recall,
    recall_summary,
    reconcile_facts,
)
from motodiag.memory import compile as compile_mod
from motodiag.memory import refresh as refresh_mod
from motodiag.vehicles.registry import add_vehicle

from tests.test_phase123_diagnose import (  # type: ignore[import-not-found]
    make_diagnose_fn,
    make_response,
)

REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase209C.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(
            f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999",
        )
    reset_settings()
    yield path
    reset_settings()


def _vehicle(db_path: str, model: str = "CBR600F4i") -> int:
    return add_vehicle(
        VehicleBase(
            make="Honda", model=model, year=2001,
            engine_cc=599, protocol=ProtocolType.NONE,
        ),
        db_path=db_path,
    )


class Shop:
    """One technician with a key, one bike, and the API in front of them."""

    def __init__(self, db_path: str):
        self.db = db_path
        with get_connection(db_path) as conn:
            self.user_id = conn.execute(
                "INSERT INTO users (username, email, tier, is_active) "
                "VALUES ('tech', 't@ex.com', 'individual', 1)"
            ).lastrowid
        _, self.key = create_api_key(self.user_id, db_path=db_path)
        self.client = TestClient(
            create_app(db_path_override=db_path), raise_server_exceptions=False,
        )
        self.vehicle_id = _vehicle(db_path)

    def _call(self, method: str, url: str, **kw):
        r = self.client.request(method, url, headers={"X-API-Key": self.key}, **kw)
        assert r.status_code < 300, (r.status_code, r.text)
        return r.json()

    def open_session(self, symptoms=("idle bog at 4500 rpm",), vehicle=True) -> int:
        body = {
            "vehicle_make": "Honda", "vehicle_model": "CBR600F4i",
            "vehicle_year": 2001, "symptoms": list(symptoms),
        }
        if vehicle:
            body["vehicle_id"] = self.vehicle_id
        return self._call("POST", "/v1/sessions", json=body)["id"]

    def close(self, sid: int) -> dict:
        return self._call("POST", f"/v1/sessions/{sid}/close")

    def reopen(self, sid: int) -> dict:
        return self._call("POST", f"/v1/sessions/{sid}/reopen")

    def patch(self, sid: int, **fields) -> dict:
        return self._call("PATCH", f"/v1/sessions/{sid}", json=fields)

    def live(self) -> list[MemoryFact]:
        return list_facts(self.vehicle_id, db_path=self.db)

    def everything(self) -> list[MemoryFact]:
        return list_facts(self.vehicle_id, include_superseded=True, db_path=self.db)

    def live_subjects(self) -> set[str]:
        return {f.subject for f in self.live()}


@pytest.fixture
def shop(api_db) -> Shop:
    return Shop(api_db)


# ---------------------------------------------------------------------------
# 1. Every way a session closes refreshes memory
# ---------------------------------------------------------------------------


class TestEveryCloseRefreshesMemory:
    def test_nothing_is_remembered_before_the_close(self, shop):
        shop.open_session()
        assert shop.live() == []

    def test_the_close_route_compiles_the_machine(self, shop):
        sid = shop.open_session()
        shop.close(sid)
        assert "idle bog at 4500 rpm" in {
            f.subject for f in recall(shop.vehicle_id, db_path=shop.db)
        }

    def test_a_patch_to_closed_compiles_and_sets_closed_at(self, shop):
        sid = shop.open_session()
        body = shop.patch(sid, status="closed")
        assert body["status"] == "closed"
        assert body["closed_at"], "PATCH to closed never set closed_at before 209C"
        assert "idle bog at 4500 rpm" in shop.live_subjects()

    def test_a_patch_to_closed_writes_the_edited_fields_first(self, shop):
        sid = shop.open_session()
        shop.patch(sid, status="closed", diagnosis="Clogged pilot jet")
        assert "Clogged pilot jet" in shop.live_subjects()

    def test_leaving_closed_by_patch_clears_closed_at(self, shop):
        sid = shop.open_session()
        shop.close(sid)
        body = shop.patch(sid, status="in_progress")
        assert body["status"] == "in_progress"
        assert body["closed_at"] is None

    def test_a_patch_to_closed_on_a_closed_session_keeps_its_closed_at(self, shop):
        sid = shop.open_session()
        closed_at = shop.close(sid)["closed_at"]
        body = shop.patch(sid, status="closed")
        assert body["status"] == "closed"
        assert body["closed_at"] == closed_at

    def test_the_cli_diagnose_flow_compiles_the_machine(self, api_db):
        """`diagnose quick` closes its session when the diagnosis is done;
        that close is the CLI's."""
        from motodiag.cli.main import cli

        vid = _vehicle(api_db)
        fn = make_diagnose_fn(make_response(confidence=0.88))
        with patch("motodiag.cli.diagnose._default_diagnose_fn", fn):
            r = CliRunner().invoke(cli, [
                "diagnose", "quick", "--vehicle-id", str(vid),
                "--symptoms", "won't start",
            ])
        assert r.exit_code == 0, r.output
        facts = list_facts(vid, db_path=api_db)
        assert "won't start" in {f.subject for f in facts}
        diagnosis = [f for f in facts if f.fact_kind == "observation"]
        assert diagnosis, facts
        # Written by the model, so it enters memory as the model's.
        assert {f.source for f in diagnosis} == {"model-generated"}

    def test_closing_twice_adds_nothing(self, shop):
        sid = shop.open_session()
        shop.close(sid)
        first = [(f.id, f.subject) for f in shop.everything()]
        shop.reopen(sid)
        shop.close(sid)
        assert [(f.id, f.subject) for f in shop.everything()] == first

    def test_a_session_without_a_machine_closes_without_compiling(self, shop):
        sid = shop.open_session(vehicle=False)
        with patch.object(refresh_mod, "compile_vehicle_detailed") as spy:
            body = shop.close(sid)
        assert body["status"] == "closed"
        spy.assert_not_called()


class TestAMemoryProblemNeverFailsTheClose:
    def test_a_compile_that_raises(self, shop, caplog):
        sid = shop.open_session()
        with patch.object(
            refresh_mod, "compile_vehicle_detailed",
            side_effect=RuntimeError("disk full"),
        ), caplog.at_level(logging.WARNING):
            body = shop.close(sid)
        assert body["status"] == "closed"
        assert body["closed_at"]
        # The refresh's own message, not the call-site guard's: the inner
        # promise is what held here.
        assert (
            f"(vehicle {shop.vehicle_id}) failed; the close stands" in caplog.text
        )
        assert "disk full" in caplog.text

    def test_a_refresh_module_that_will_not_import(self, shop, caplog, monkeypatch):
        """The call-site guard. `None` in sys.modules makes the import raise."""
        sid = shop.open_session()
        monkeypatch.setitem(sys.modules, "motodiag.memory.refresh", None)
        with caplog.at_level(logging.WARNING):
            body = shop.close(sid)
        assert body["status"] == "closed"
        assert "memory refresh could not run" in caplog.text

    def test_a_patch_to_closed_with_a_failing_compile(self, shop):
        sid = shop.open_session()
        with patch.object(
            refresh_mod, "compile_vehicle_detailed",
            side_effect=RuntimeError("disk full"),
        ):
            body = shop.patch(sid, status="closed")
        assert body["status"] == "closed"

    def test_the_next_close_catches_up(self, shop):
        sid = shop.open_session()
        with patch.object(
            refresh_mod, "compile_vehicle_detailed",
            side_effect=RuntimeError("disk full"),
        ):
            shop.close(sid)
        assert shop.live() == []
        shop.reopen(sid)
        shop.close(sid)
        assert "idle bog at 4500 rpm" in shop.live_subjects()


class TestTheRefreshItself:
    def test_it_returns_what_the_compile_changed(self, shop):
        sid = shop.open_session()
        result = refresh_mod.refresh_after_close(sid, db_path=shop.db)
        assert result is not None and result.inserted == 1

    def test_it_never_raises(self, shop, caplog):
        sid = shop.open_session()
        with patch.object(
            refresh_mod, "compile_vehicle_detailed",
            side_effect=RuntimeError("disk full"),
        ), caplog.at_level(logging.WARNING, logger="motodiag.memory.refresh"):
            assert refresh_mod.refresh_after_close(sid, db_path=shop.db) is None
        assert "failed; the close stands" in caplog.text

    def test_an_unknown_session_is_nothing_to_do(self, shop):
        assert refresh_mod.refresh_after_close(987654, db_path=shop.db) is None


# ---------------------------------------------------------------------------
# 2. An edit replaces what is remembered
# ---------------------------------------------------------------------------


class TestAnEditReplacesWhatIsRemembered:
    def _diagnosed(self, shop, text="Stator cover gasket weeping") -> int:
        sid = shop.open_session()
        shop.patch(sid, diagnosis=text, ai_model_used="haiku")
        shop.close(sid)
        return sid

    def test_reopen_edit_close_supersedes_the_old_diagnosis(self, shop):
        """The operator's own flow from 2026-09-17."""
        sid = self._diagnosed(shop)
        shop.reopen(sid)
        shop.patch(sid, diagnosis="Clutch cover gasket weeping")
        shop.close(sid)

        assert "Clutch cover gasket weeping" in shop.live_subjects()
        assert "Stator cover gasket weeping" not in shop.live_subjects()
        old = [f for f in shop.everything()
               if f.subject == "Stator cover gasket weeping"]
        assert len(old) == 1 and old[0].superseded_at, (
            "superseded, not deleted: the record of what was believed stays"
        )

    def test_recall_and_the_prompt_block_show_only_the_edit(self, shop):
        sid = self._diagnosed(shop)
        shop.reopen(sid)
        shop.patch(sid, diagnosis="Clutch cover gasket weeping")
        shop.close(sid)

        recalled = {f.subject for f in recall(shop.vehicle_id, db_path=shop.db)}
        assert "Stator cover gasket weeping" not in recalled
        block = recall_summary(
            shop.vehicle_id, include_model_generated=True, db_path=shop.db,
        )
        assert "Clutch cover gasket weeping" in block
        assert "Stator cover gasket weeping" not in block

    def test_reverting_the_edit_revives_the_original_row(self, shop):
        sid = self._diagnosed(shop)
        original = next(f for f in shop.live()
                        if f.subject == "Stator cover gasket weeping")
        shop.reopen(sid)
        shop.patch(sid, diagnosis="Clutch cover gasket weeping")
        shop.close(sid)
        shop.reopen(sid)
        shop.patch(sid, diagnosis="Stator cover gasket weeping")
        shop.close(sid)

        live = {f.subject: f for f in shop.live()}
        assert live["Stator cover gasket weeping"].id == original.id
        assert "Clutch cover gasket weeping" not in live

    def test_an_edited_ai_diagnosis_is_still_the_models(self, shop):
        """Provenance rule, 2026-09-17: an edit is not a confirmation."""
        sid = self._diagnosed(shop)
        shop.reopen(sid)
        shop.patch(sid, diagnosis="Clutch cover gasket weeping")
        shop.close(sid)
        edited = next(f for f in shop.live()
                      if f.subject == "Clutch cover gasket weeping")
        assert (edited.fact_kind, edited.source) == ("observation", "model-generated")

    def test_a_human_diagnosis_is_the_mechanics(self, shop):
        sid = shop.open_session()
        shop.patch(sid, diagnosis="Split intake boot, confirmed with smoke test")
        shop.close(sid)
        fact = next(f for f in shop.live() if f.subject.startswith("Split intake"))
        assert (fact.fact_kind, fact.source) == ("correction", "mechanic-verified")

    def test_a_symptom_no_longer_on_the_session_is_superseded(self, shop):
        sid = shop.open_session(symptoms=("idle bog", "smoke on startup"))
        shop.close(sid)
        with get_connection(shop.db) as conn:
            conn.execute(
                "UPDATE diagnostic_sessions SET symptoms = ? WHERE id = ?",
                ('["idle bog"]', sid),
            )
        shop.reopen(sid)
        shop.close(sid)
        assert "idle bog" in shop.live_subjects()
        assert "smoke on startup" not in shop.live_subjects()

    def test_a_deleted_sessions_facts_are_superseded(self, shop):
        """Sessions 8 and 9 needed their facts deleted by hand on 2026-09-17."""
        gone = shop.open_session(symptoms=("rattle from the left side",))
        shop.close(gone)
        with get_connection(shop.db) as conn:
            conn.execute("DELETE FROM diagnostic_sessions WHERE id = ?", (gone,))
        kept = shop.open_session(symptoms=("idle bog",))
        shop.close(kept)
        assert shop.live_subjects() == {"idle bog"}


# ---------------------------------------------------------------------------
# 3. What a compile may retire
# ---------------------------------------------------------------------------


class TestWhatACompileMayRetire:
    def test_another_machines_facts_are_untouched(self, shop):
        other = _vehicle(shop.db, model="VFR800")
        sid = shop.open_session()
        shop.close(sid)
        insert_facts([MemoryFact(
            vehicle_id=other, fact_kind="complaint", subject="stale elsewhere",
            source="customer-reported", origin_table="diagnostic_sessions",
            origin_id=99999, established_at="2026-09-01",
        )], db_path=shop.db)

        shop.reopen(sid)
        shop.close(sid)
        assert [f.subject for f in list_facts(other, db_path=shop.db)] == [
            "stale elsewhere"
        ]

    def test_a_fact_compile_does_not_own_is_never_retired(self, shop):
        insert_facts([MemoryFact(
            vehicle_id=shop.vehicle_id, fact_kind="measurement",
            subject="compression 180 psi, all four",
            source="mechanic-verified", origin_table="bench_notes",
            origin_id=None, established_at="2026-09-01",
        )], db_path=shop.db)
        sid = shop.open_session()
        shop.close(sid)
        assert "compression 180 psi, all four" in shop.live_subjects()

    def test_reconcile_touches_only_the_tables_it_is_given(self, shop):
        sid = shop.open_session()
        shop.close(sid)
        assert reconcile_facts(
            shop.vehicle_id, [], ("videos",), db_path=shop.db,
        ) == (0, 0)
        assert "idle bog at 4500 rpm" in shop.live_subjects()

    def test_the_compiled_tables_are_exactly_the_ones_compile_writes(self):
        source = (REPO / "src/motodiag/memory/compile.py").read_text(encoding="utf-8")
        written = set(re.findall(r'origin_table="([a-z_]+)"', source))
        assert written == set(compile_mod.COMPILED_ORIGIN_TABLES)

    def test_the_detailed_result_counts_rows_changed(self, shop):
        sid = shop.open_session()
        shop.patch(sid, diagnosis="A")
        first = compile_vehicle_detailed(shop.vehicle_id, db_path=shop.db)
        assert (first.superseded, first.revived) == (0, 0) and first.inserted >= 2
        shop.patch(sid, diagnosis="B")
        second = compile_vehicle_detailed(shop.vehicle_id, db_path=shop.db)
        assert (second.inserted, second.superseded, second.revived) == (1, 1, 0)
        shop.patch(sid, diagnosis="A")
        third = compile_vehicle_detailed(shop.vehicle_id, db_path=shop.db)
        assert (third.inserted, third.superseded, third.revived) == (0, 1, 1)
        again = compile_vehicle_detailed(shop.vehicle_id, db_path=shop.db)
        assert (again.inserted, again.superseded, again.revived) == (0, 0, 0)


# ---------------------------------------------------------------------------
# 4. The manual compile says what it retired
# ---------------------------------------------------------------------------


class TestTheCompileCommandReports:
    def _run(self, *args):
        from motodiag.cli.main import cli

        r = CliRunner().invoke(cli, ["memory", "compile", *args])
        assert r.exit_code == 0, r.output
        return r.output

    def test_an_unchanged_compile_reads_as_before(self, shop):
        sid = shop.open_session()
        shop.close(sid)
        assert self._run("--vehicle", str(shop.vehicle_id)) == (
            f"Vehicle {shop.vehicle_id}: 0 new fact(s).\n"
        )
        assert self._run() == "0 new fact(s) across 1 machine(s).\n"

    def test_a_compile_after_an_edit_says_what_it_superseded(self, shop):
        sid = shop.open_session()
        shop.patch(sid, diagnosis="A")
        shop.close(sid)
        with get_connection(shop.db) as conn:
            conn.execute(
                "UPDATE diagnostic_sessions SET diagnosis = 'B' WHERE id = ?", (sid,),
            )
        assert self._run("--vehicle", str(shop.vehicle_id)) == (
            f"Vehicle {shop.vehicle_id}: 1 new fact(s), 1 superseded.\n"
        )

    def test_the_all_machines_summary_counts_them_too(self, shop):
        sid = shop.open_session()
        shop.patch(sid, diagnosis="A")
        shop.close(sid)
        with get_connection(shop.db) as conn:
            conn.execute(
                "UPDATE diagnostic_sessions SET diagnosis = 'B' WHERE id = ?", (sid,),
            )
        out = self._run()
        assert f"  vehicle {shop.vehicle_id}: 1 new fact(s), 1 superseded\n" in out
        assert out.endswith("1 new fact(s) across 1 machine(s), 1 superseded.\n")
