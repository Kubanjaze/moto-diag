"""Phase 131 — Offline mode + AI response caching tests.

Covers:
- ``TestMigration015``: migration 015 definition, SCHEMA_VERSION bump,
  ``ai_response_cache`` table + indexes present on a fresh init.
- ``TestCacheKey``: deterministic hashing, kind-prefix disambiguation,
  sort-key stability, full-input coverage.
- ``TestCacheCRUD``: set/get round-trip, INSERT OR REPLACE semantics, miss
  returns None, hit_count increments, last_used_at touches, JSON
  round-trip.
- ``TestPurge``: purge all, purge older-than, purge with no matches,
  stats post-purge.
- ``TestDiagnoseIntegration``: cache miss calls AI + primes cache; second
  call with same inputs serves from cache (zero new tokens); use_cache=
  False skips the cache entirely; offline=True on cache miss raises
  a clear RuntimeError.
- ``TestInterpretIntegration``: same three patterns for
  :class:`FaultCodeInterpreter.interpret`.
- ``TestCliCache``: ``cache stats``, ``cache purge --yes``, ``cache
  clear --yes``, and the empty-cache message.
- ``TestCliOfflineFlag``: ``diagnose quick --offline`` on cache miss
  errors cleanly; ``diagnose quick --offline`` works after a primed
  online run.

Zero live API tokens — ``Anthropic`` is patched everywhere the SDK
would be instantiated.
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    init_db,
    table_exists,
)
from motodiag.core.migrations import get_migration_by_version
from motodiag.core.models import ProtocolType, VehicleBase
from motodiag.engine.cache import (
    _make_cache_key,
    cost_dollars_to_cents,
    get_cache_stats,
    get_cached_response,
    purge_cache,
    set_cached_response,
)
from motodiag.engine.fault_codes import FaultCodeInterpreter, FaultCodeResult
from motodiag.engine.client import DiagnosticClient
from motodiag.engine.models import (
    DiagnosisItem,
    DiagnosticResponse,
    DiagnosticSeverity,
    TokenUsage,
)
from motodiag.vehicles.registry import add_vehicle


# --- Fixtures ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "phase131.db")
    init_db(path)
    return path


@pytest.fixture
def cli_db(db, monkeypatch):
    """Point settings at the temp DB; reset config cache after.

    Mirrors the Phase 125-130 pattern so the CLI sees the same DB the
    direct-engine-call tests see.
    """
    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()
    yield db
    reset_settings()


# --- Helpers ---


def _make_diagnose_response_dict() -> dict:
    """Return a Pydantic-valid DiagnosticResponse dump for cache round-trips.

    Uses ``mode="json"`` to match the production cache store path in
    ``DiagnosticClient.diagnose``, so the fixture produces the same
    shape the production cache persists.
    """
    return DiagnosticResponse(
        vehicle_summary="2001 Harley-Davidson Sportster 1200",
        symptoms_acknowledged=["won't start", "cranks slow"],
        diagnoses=[
            DiagnosisItem(
                diagnosis="Stator failure — voltage drops under load.",
                confidence=0.87,
                severity=DiagnosticSeverity.HIGH,
                evidence=["Stator AC output <5V at 2000 RPM"],
                repair_steps=["Test stator", "Replace if low"],
                estimated_hours=3.5,
                estimated_cost="$200-$400",
            )
        ],
        additional_tests=[],
        notes=None,
    ).model_dump(mode="json")


def _make_interpret_response_dict() -> dict:
    """Return a FaultCodeResult dump for cache round-trips."""
    return FaultCodeResult(
        code="P0115",
        code_format="obd2_generic",
        description="Engine Coolant Temperature Sensor Circuit",
        system="fuel_and_air_metering",
        possible_causes=["ECT sensor open", "Harness chafe"],
        tests_to_confirm=["Ohm-check sensor cold and warm"],
        related_symptoms=["Hard cold start"],
        repair_steps=["Replace ECT sensor", "Clear codes"],
        estimated_hours=1.5,
        estimated_cost="$120-$250",
        safety_critical=False,
        notes=None,
    ).model_dump(mode="json")


class _FakeAnthropicResponse:
    """Mimic the shape of Anthropic's messages.create response."""

    def __init__(self, text: str, input_tokens: int, output_tokens: int):
        self.content = [SimpleNamespace(text=text)]
        self.usage = SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


class _FakeAnthropicClient:
    """Minimal stand-in for an instantiated Anthropic client.

    Counts ``.messages.create`` invocations so tests can assert cache
    hits bypass the API entirely.
    """

    def __init__(self, canned_text: str, input_tokens: int = 500,
                 output_tokens: int = 150):
        self._canned = canned_text
        self._in = input_tokens
        self._out = output_tokens
        self.call_count = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.call_count += 1
        return _FakeAnthropicResponse(self._canned, self._in, self._out)


def _diagnose_json_text() -> str:
    """Produce a JSON response body the DiagnosticResponse parser accepts."""
    return json.dumps({
        "vehicle_summary": "2001 Harley-Davidson Sportster 1200",
        "symptoms_acknowledged": ["won't start"],
        "diagnoses": [
            {
                "diagnosis": "Stator failure",
                "confidence": 0.87,
                "severity": "high",
                "evidence": ["low stator AC output"],
                "repair_steps": ["Test", "Replace"],
                "estimated_hours": 3.5,
                "estimated_cost": "$200-$400",
                "parts_needed": ["Stator assembly"],
                "safety_warning": None,
            }
        ],
        "additional_tests": [],
        "notes": None,
    })


def _interpret_json_text() -> str:
    """Produce a JSON response body the FaultCodeResult parser accepts."""
    return json.dumps({
        "possible_causes": ["ECT sensor open", "Harness chafe"],
        "tests_to_confirm": ["Ohm-check ECT sensor cold and warm"],
        "related_symptoms": ["Hard cold start"],
        "repair_steps": ["Replace ECT sensor", "Clear codes"],
        "estimated_hours": 1.5,
        "estimated_cost": "$120-$250",
        "safety_critical": False,
        "notes": None,
        "system": "fuel_and_air_metering",
    })


# ---------- TestMigration015 (3) ----------


class TestMigration015:
    def test_migration_exists(self):
        m = get_migration_by_version(15)
        assert m is not None
        assert m.name == "ai_response_cache"
        assert "CREATE TABLE" in m.upgrade_sql
        assert "ai_response_cache" in m.upgrade_sql
        assert "DROP TABLE IF EXISTS ai_response_cache" in m.rollback_sql

    def test_table_present_on_fresh_init(self, db):
        assert table_exists("ai_response_cache", db_path=db)
        # Both indexes should exist.
        with get_connection(db) as conn:
            idx_rows = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='ai_response_cache'"
            ).fetchall()
            idx_names = {r["name"] for r in idx_rows}
            assert "idx_ai_cache_key" in idx_names
            assert "idx_ai_cache_created" in idx_names

    def test_schema_version_at_least_15(self):
        assert SCHEMA_VERSION >= 15


# ---------- TestCacheKey (4) ----------


class TestCacheKey:
    def test_deterministic(self):
        payload = {"make": "Honda", "model_name": "CBR929RR", "year": 2001}
        k1 = _make_cache_key("diagnose", payload)
        k2 = _make_cache_key("diagnose", payload)
        assert k1 == k2
        assert len(k1) == 64  # SHA256 hex digest length

    def test_kind_prefix_disambiguates(self):
        payload = {"code": "P0115"}
        k_diag = _make_cache_key("diagnose", payload)
        k_interp = _make_cache_key("interpret", payload)
        assert k_diag != k_interp

    def test_sort_keys_stability(self):
        # Payloads with identical data but different insertion order must
        # produce the same key — otherwise ordering bugs in callers would
        # fragment the cache.
        a = {"alpha": 1, "beta": 2, "gamma": 3}
        b = {"gamma": 3, "alpha": 1, "beta": 2}
        assert _make_cache_key("diagnose", a) == _make_cache_key("diagnose", b)

    def test_all_inputs_influence_key(self):
        # Changing any field should produce a different key — otherwise
        # the cache would conflate distinct inputs.
        base = {
            "make": "Honda", "model_name": "CBR929RR", "year": 2001,
            "symptoms": ["won't start"], "description": None,
            "mileage": None, "engine_type": None, "modifications": [],
            "ai_model": "haiku",
        }
        base_key = _make_cache_key("diagnose", base)
        for field, new_val in [
            ("make", "Yamaha"),
            ("year", 2002),
            ("symptoms", ["stalls"]),
            ("ai_model", "sonnet"),
            ("mileage", 25000),
        ]:
            variant = dict(base)
            variant[field] = new_val
            assert _make_cache_key("diagnose", variant) != base_key, (
                f"Changing {field!r} did not change the cache key"
            )


# ---------- TestCacheCRUD (6) ----------


class TestCacheCRUD:
    def test_set_then_get_round_trip(self, db):
        payload = _make_diagnose_response_dict()
        key = _make_cache_key("diagnose", {"make": "Honda", "year": 2001})
        rid = set_cached_response(
            cache_key=key,
            kind="diagnose",
            model_used="haiku",
            response_dict=payload,
            tokens_input=500,
            tokens_output=150,
            cost_cents=100,
            db_path=db,
        )
        assert rid > 0

        row = get_cached_response(key, db_path=db)
        assert row is not None
        assert row["kind"] == "diagnose"
        assert row["model_used"] == "haiku"
        assert row["tokens_input"] == 500
        assert row["tokens_output"] == 150
        assert row["cost_cents"] == 100
        assert row["response"]["vehicle_summary"] == payload["vehicle_summary"]

    def test_insert_or_replace_on_duplicate_key(self, db):
        key = _make_cache_key("diagnose", {"x": 1})
        set_cached_response(
            cache_key=key, kind="diagnose", model_used="haiku",
            response_dict={"k": "v1"}, tokens_input=10, tokens_output=5,
            cost_cents=1, db_path=db,
        )
        # Replace with new data under same key
        set_cached_response(
            cache_key=key, kind="diagnose", model_used="sonnet",
            response_dict={"k": "v2"}, tokens_input=100, tokens_output=50,
            cost_cents=9, db_path=db,
        )
        row = get_cached_response(key, db_path=db)
        assert row["model_used"] == "sonnet"
        assert row["response"] == {"k": "v2"}
        assert row["tokens_input"] == 100

    def test_get_on_missing_key_returns_none(self, db):
        assert get_cached_response("does-not-exist", db_path=db) is None

    def test_hit_count_increments(self, db):
        key = _make_cache_key("diagnose", {"y": 2})
        set_cached_response(
            cache_key=key, kind="diagnose", model_used="haiku",
            response_dict={"a": 1}, tokens_input=0, tokens_output=0,
            cost_cents=10, db_path=db,
        )
        # First lookup
        r1 = get_cached_response(key, db_path=db)
        assert r1["hit_count"] == 0  # pre-increment snapshot
        # Second lookup — DB should reflect bump to 1, so lookup sees 1
        r2 = get_cached_response(key, db_path=db)
        assert r2["hit_count"] == 1
        r3 = get_cached_response(key, db_path=db)
        assert r3["hit_count"] == 2

    def test_last_used_at_updates_on_hit(self, db):
        key = _make_cache_key("diagnose", {"z": 3})
        set_cached_response(
            cache_key=key, kind="diagnose", model_used="haiku",
            response_dict={"b": 2}, db_path=db,
        )
        # Fresh row: last_used_at starts NULL.
        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT last_used_at FROM ai_response_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
            assert row["last_used_at"] is None

        get_cached_response(key, db_path=db)

        with get_connection(db) as conn:
            row = conn.execute(
                "SELECT last_used_at FROM ai_response_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
            assert row["last_used_at"] is not None

    def test_json_round_trip_preserves_structure(self, db):
        # Use a complex structure with nested dicts + lists to confirm
        # json.dumps/loads preserves it.
        payload = {
            "vehicle_summary": "2001 Honda CBR929RR",
            "symptoms_acknowledged": ["won't start"],
            "diagnoses": [
                {"diagnosis": "X", "confidence": 0.8, "severity": "high",
                 "evidence": ["e1", "e2"], "repair_steps": ["s1"]},
            ],
            "additional_tests": ["t1", "t2"],
            "notes": "Something with Ω and ±",
        }
        key = _make_cache_key("diagnose", {"q": "q"})
        set_cached_response(
            cache_key=key, kind="diagnose", model_used="haiku",
            response_dict=payload, db_path=db,
        )
        row = get_cached_response(key, db_path=db)
        assert row["response"] == payload


# ---------- TestPurge (4) ----------


class TestPurge:
    def _seed(self, db, n=3):
        for i in range(n):
            set_cached_response(
                cache_key=f"k{i}",
                kind="diagnose",
                model_used="haiku",
                response_dict={"i": i},
                cost_cents=10 * (i + 1),
                db_path=db,
            )

    def test_purge_all(self, db):
        self._seed(db, n=3)
        deleted = purge_cache(older_than_days=None, db_path=db)
        assert deleted == 3
        assert get_cache_stats(db_path=db)["total_rows"] == 0

    def test_purge_older_than(self, db):
        # Seed two "old" rows + one "new" row by back-dating directly.
        self._seed(db, n=3)
        with get_connection(db) as conn:
            conn.execute(
                "UPDATE ai_response_cache SET created_at = datetime('now', '-40 days') "
                "WHERE cache_key IN ('k0', 'k1')"
            )
        deleted = purge_cache(older_than_days=30, db_path=db)
        assert deleted == 2
        remaining = get_cache_stats(db_path=db)
        assert remaining["total_rows"] == 1

    def test_purge_no_matches_returns_zero(self, db):
        self._seed(db, n=2)
        # Everything is brand-new so a 30-day threshold deletes nothing.
        deleted = purge_cache(older_than_days=30, db_path=db)
        assert deleted == 0
        assert get_cache_stats(db_path=db)["total_rows"] == 2

    def test_stats_reflect_post_purge_state(self, db):
        self._seed(db, n=5)
        # Simulate some hits so total_hits > 0 before purge.
        for i in range(5):
            get_cached_response(f"k{i}", db_path=db)
        before = get_cache_stats(db_path=db)
        assert before["total_rows"] == 5
        assert before["total_hits"] == 5

        purge_cache(older_than_days=None, db_path=db)
        after = get_cache_stats(db_path=db)
        assert after["total_rows"] == 0
        assert after["total_hits"] == 0
        assert after["total_cost_cents_saved"] == 0


# ---------- TestDiagnoseIntegration (4) ----------


class TestDiagnoseIntegration:
    """End-to-end cache behavior on DiagnosticClient.diagnose.

    Anthropic is patched with a counting fake so we can assert that
    a cache hit serves without calling the API.
    """

    def _make_client(self, fake_anthropic, db_path):
        """Build a DiagnosticClient pointing at the test DB.

        The DB path override flows through ``get_settings`` (monkeypatched
        via ``cli_db`` or direct env set), so the engine cache calls
        resolve to the same DB as the test fixture.
        """
        client = DiagnosticClient(api_key="sk-ant-test-key-01234567", model="haiku")
        # Bypass the lazy import; force our fake.
        client._client = fake_anthropic
        return client

    def test_miss_calls_api_and_caches(self, cli_db):
        fake = _FakeAnthropicClient(_diagnose_json_text(),
                                     input_tokens=500, output_tokens=150)
        client = self._make_client(fake, cli_db)
        resp, usage = client.diagnose(
            make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["won't start"], use_cache=True,
        )
        assert fake.call_count == 1
        assert usage.input_tokens == 500
        assert resp.vehicle_summary.startswith("2001 Harley")
        # Cache should now hold exactly one diagnose row.
        stats = get_cache_stats(db_path=cli_db)
        assert stats["total_rows"] == 1

    def test_hit_serves_with_zero_tokens(self, cli_db):
        fake = _FakeAnthropicClient(_diagnose_json_text(),
                                     input_tokens=500, output_tokens=150)
        client = self._make_client(fake, cli_db)
        # Prime
        client.diagnose(
            make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["won't start"], use_cache=True,
        )
        assert fake.call_count == 1

        # Second call with identical args — cache hit, no new API call.
        client2 = self._make_client(fake, cli_db)
        resp2, usage2 = client2.diagnose(
            make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["won't start"], use_cache=True,
        )
        assert fake.call_count == 1, "cache hit must not re-hit the API"
        assert usage2.input_tokens == 0
        assert usage2.output_tokens == 0
        assert usage2.cost_estimate == 0.0
        assert resp2.vehicle_summary.startswith("2001 Harley")

    def test_use_cache_false_skips_cache_entirely(self, cli_db):
        fake = _FakeAnthropicClient(_diagnose_json_text())
        client = self._make_client(fake, cli_db)
        client.diagnose(
            make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["won't start"], use_cache=False,
        )
        # First call with cache disabled → API hit, nothing stored.
        assert fake.call_count == 1
        assert get_cache_stats(db_path=cli_db)["total_rows"] == 0

        client.diagnose(
            make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["won't start"], use_cache=False,
        )
        # Second identical call — API hit again, still nothing cached.
        assert fake.call_count == 2
        assert get_cache_stats(db_path=cli_db)["total_rows"] == 0

    def test_offline_on_miss_raises(self, cli_db):
        fake = _FakeAnthropicClient(_diagnose_json_text())
        client = self._make_client(fake, cli_db)
        with pytest.raises(RuntimeError, match="Offline mode"):
            client.diagnose(
                make="Honda", model_name="CBR929RR", year=2001,
                symptoms=["won't start"], offline=True,
            )
        # API must NOT have been called.
        assert fake.call_count == 0


# ---------- TestInterpretIntegration (3) ----------


class TestInterpretIntegration:
    def _make_interpreter(self, fake_anthropic):
        client = DiagnosticClient(api_key="sk-ant-test-key-01234567", model="haiku")
        client._client = fake_anthropic
        return FaultCodeInterpreter(client)

    def test_miss_then_hit_round_trip(self, cli_db):
        fake = _FakeAnthropicClient(_interpret_json_text(),
                                     input_tokens=400, output_tokens=120)
        interpreter = self._make_interpreter(fake)
        r1, u1 = interpreter.interpret(
            code="P0115", make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["hard cold start"],
        )
        assert fake.call_count == 1
        assert u1.input_tokens == 400

        # Identical interpret — cache hit.
        r2, u2 = interpreter.interpret(
            code="P0115", make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["hard cold start"],
        )
        assert fake.call_count == 1
        assert u2.input_tokens == 0
        assert u2.output_tokens == 0
        assert r2.code == "P0115"

    def test_use_cache_false_skips(self, cli_db):
        fake = _FakeAnthropicClient(_interpret_json_text())
        interpreter = self._make_interpreter(fake)
        interpreter.interpret(
            code="P0115", make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["hard cold start"], use_cache=False,
        )
        interpreter.interpret(
            code="P0115", make="Honda", model_name="CBR929RR", year=2001,
            symptoms=["hard cold start"], use_cache=False,
        )
        assert fake.call_count == 2
        assert get_cache_stats(db_path=cli_db)["total_rows"] == 0

    def test_offline_on_miss_raises(self, cli_db):
        fake = _FakeAnthropicClient(_interpret_json_text())
        interpreter = self._make_interpreter(fake)
        with pytest.raises(RuntimeError, match="Offline mode"):
            interpreter.interpret(
                code="P0115", make="Honda", model_name="CBR929RR", year=2001,
                symptoms=["hard cold start"], offline=True,
            )
        assert fake.call_count == 0


# ---------- TestCliCache (4) ----------


class TestCliCache:
    def test_cache_stats_populated(self, cli_db):
        # Seed a single cache row so the stats command has something to show.
        key = _make_cache_key("diagnose", {"x": 1})
        set_cached_response(
            cache_key=key, kind="diagnose", model_used="haiku",
            response_dict={"ok": True}, tokens_input=500, tokens_output=150,
            cost_cents=120, db_path=cli_db,
        )
        # Bump hit_count a couple of times to exercise the savings total.
        get_cached_response(key, db_path=cli_db)
        get_cached_response(key, db_path=cli_db)

        from motodiag.cli.main import cli
        r = CliRunner().invoke(cli, ["cache", "stats"])
        assert r.exit_code == 0, r.output
        assert "AI Response Cache" in r.output
        assert "1" in r.output  # Entries: 1
        assert "2" in r.output  # Total hits: 2
        # Savings = 120 * 2 = 240 cents = $2.40
        assert "$2.40" in r.output

    def test_cache_stats_empty_message(self, cli_db):
        from motodiag.cli.main import cli
        r = CliRunner().invoke(cli, ["cache", "stats"])
        assert r.exit_code == 0, r.output
        assert "Cache is empty" in r.output

    def test_cache_purge_yes_no_prompt(self, cli_db):
        # Seed + back-date so the default 30-day window catches the row.
        set_cached_response(
            cache_key="old-key", kind="diagnose", model_used="haiku",
            response_dict={"k": "v"}, db_path=cli_db,
        )
        with get_connection(cli_db) as conn:
            conn.execute(
                "UPDATE ai_response_cache SET created_at = datetime('now', '-60 days')"
            )
        from motodiag.cli.main import cli
        r = CliRunner().invoke(cli, ["cache", "purge", "--yes"])
        assert r.exit_code == 0, r.output
        assert "Purged" in r.output or "1 cache" in r.output
        assert get_cache_stats(db_path=cli_db)["total_rows"] == 0

    def test_cache_clear_yes(self, cli_db):
        for i in range(3):
            set_cached_response(
                cache_key=f"k{i}", kind="diagnose", model_used="haiku",
                response_dict={"i": i}, db_path=cli_db,
            )
        from motodiag.cli.main import cli
        r = CliRunner().invoke(cli, ["cache", "clear", "--yes"])
        assert r.exit_code == 0, r.output
        assert "Cleared" in r.output
        assert "3" in r.output
        assert get_cache_stats(db_path=cli_db)["total_rows"] == 0


# ---------- TestCliOfflineFlag (2) ----------


class TestCliOfflineFlag:
    def _seed_vehicle(self, db_path):
        return add_vehicle(
            VehicleBase(
                make="Honda", model="CBR929RR", year=2001,
                engine_cc=929, protocol=ProtocolType.K_LINE,
            ),
            db_path=db_path,
        )

    def test_offline_miss_errors_cleanly(self, cli_db):
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli

        # Patch the default diagnose function so it raises the same
        # RuntimeError the engine would produce on offline miss.
        def _raise_offline(**kwargs):
            raise RuntimeError(
                "Offline mode: no cached response for this query. "
                "Either remove --offline or prime the cache with an "
                "online run."
            )

        with patch("motodiag.cli.diagnose._default_diagnose_fn",
                   _raise_offline):
            r = CliRunner().invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "won't start",
                "--offline",
            ])
        assert r.exit_code != 0
        assert "Offline mode" in r.output

    def test_offline_hit_works_after_online_prime(self, cli_db):
        vid = self._seed_vehicle(cli_db)
        from motodiag.cli.main import cli

        # We bypass the engine cache plumbing and exercise the CLI path
        # directly: first call primes (offline=False behavior), second
        # call with --offline is served by the same mock — proving the
        # CLI threads the `offline` kwarg through without erroring.
        call_log = {"offline_flags": []}

        def _fake_diagnose(**kwargs):
            call_log["offline_flags"].append(kwargs.get("offline", False))
            resp = SimpleNamespace(
                vehicle_summary="2001 Honda CBR929RR",
                symptoms_acknowledged=["won't start"],
                diagnoses=[
                    SimpleNamespace(
                        diagnosis="Stator failure", confidence=0.9,
                        severity="high", rationale="test",
                        recommended_actions=["Replace stator"],
                    )
                ],
                additional_tests=[],
                notes=None,
            )
            usage = TokenUsage(
                input_tokens=0, output_tokens=0, model="haiku",
                cost_estimate=0.0, latency_ms=None,
            )
            return resp, usage

        with patch("motodiag.cli.diagnose._default_diagnose_fn",
                   _fake_diagnose):
            # Prime
            r1 = CliRunner().invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "won't start",
            ])
            assert r1.exit_code == 0, r1.output
            # Offline — succeeds because the fake always returns a response.
            r2 = CliRunner().invoke(cli, [
                "diagnose", "quick",
                "--vehicle-id", str(vid),
                "--symptoms", "won't start",
                "--offline",
            ])
            assert r2.exit_code == 0, r2.output

        # Sanity: the CLI actually passed offline=True on the second call.
        assert call_log["offline_flags"] == [False, True]
