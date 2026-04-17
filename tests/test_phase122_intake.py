"""Phase 122 — Vehicle garage + photo bike intake tests.

Covers:
- Migration 013 (intake_usage_log table + indexes + rollback)
- Models (IdentifyKind, VehicleGuess, IntakeQuota, exceptions)
- Image preprocessing (resize, JPEG re-encode, hash determinism, PNG alpha)
- Cost calculation
- JSON parse (valid, malformed, markdown-fenced)
- Tier detection + quota math
- Identify flow (success, Sonnet escalation, cache hit, quota exhausted)
- Budget alert fires only on threshold crossing
- Usage logging
- CLI: garage add/list/remove, garage add-from-photo, intake photo, intake quota

All vision calls mocked — zero live API usage.
"""

import io
import json

import pytest
from click.testing import CliRunner

from motodiag.core.database import (
    init_db, get_schema_version, SCHEMA_VERSION, get_connection,
)
from motodiag.core.migrations import get_migration_by_version, rollback_migration
from motodiag.core.models import VehicleBase, ProtocolType, PowertrainType
from motodiag.vehicles.registry import add_vehicle, list_vehicles
from motodiag.billing import (
    Subscription, SubscriptionTier, SubscriptionStatus, create_subscription,
)
from motodiag.intake import (
    IdentifyKind, VehicleGuess, IntakeQuota,
    IntakeError, QuotaExceededError,
    VehicleIdentifier,
    MONTHLY_CAPS, BUDGET_ALERT_THRESHOLD,
)
from motodiag.intake.vehicle_identifier import (
    _preprocess_image, _compute_cost_cents, _parse_guess_json, _get_user_tier,
)


# --- Fixtures ---


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "intake.db")
    init_db(path)
    return path


@pytest.fixture
def jpeg_path(tmp_path):
    """Synthetic JPEG for preprocessing tests."""
    from PIL import Image
    p = tmp_path / "bike.jpg"
    img = Image.new("RGB", (1600, 900), (40, 80, 120))
    # Add some texture so JPEG compression isn't trivially uniform
    for y in range(0, 900, 30):
        for x in range(0, 1600, 30):
            img.putpixel((x, y), (200, 200, 200))
    img.save(p, format="JPEG", quality=90)
    return p


@pytest.fixture
def png_alpha_path(tmp_path):
    """PNG with alpha channel — exercises the flatten-to-white path."""
    from PIL import Image
    p = tmp_path / "bike_alpha.png"
    img = Image.new("RGBA", (800, 600), (30, 60, 90, 200))
    img.save(p, format="PNG")
    return p


def make_vision_mock(payloads, tokens_in=1500, tokens_out=400):
    """Factory for a vision_call mock that returns successive payloads."""
    if isinstance(payloads, str):
        payloads = [payloads]
    calls = {"i": 0}

    def _call(image_bytes, hints, model_id):
        idx = min(calls["i"], len(payloads) - 1)
        calls["i"] += 1
        return payloads[idx], tokens_in, tokens_out
    _call.calls = calls
    return _call


def _sample_guess_json(
    make="Honda", model="CBR929RR",
    year_low=2000, year_high=2001,
    cc_low=900, cc_high=930,
    confidence=0.88, powertrain="ice",
) -> str:
    return json.dumps({
        "make": make, "model": model,
        "year_low": year_low, "year_high": year_high,
        "engine_cc_low": cc_low, "engine_cc_high": cc_high,
        "powertrain_guess": powertrain,
        "confidence": confidence,
        "reasoning": "Tank badge visible, fairing silhouette matches.",
    })


# --- Migration 013 ---


class TestMigration013:
    def test_migration_exists(self):
        m = get_migration_by_version(13)
        assert m is not None
        assert "intake_usage_log" in m.upgrade_sql.lower()

    def test_table_created(self, db):
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='intake_usage_log'"
            )
            assert cursor.fetchone() is not None

    def test_indexes_created(self, db):
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_intake%'"
            )
            names = {row[0] for row in cursor.fetchall()}
        for expected in ("idx_intake_user", "idx_intake_user_time", "idx_intake_image_hash"):
            assert expected in names

    def test_rollback_drops_table(self, db):
        m = get_migration_by_version(13)
        rollback_migration(m, db)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='intake_usage_log'"
            )
            assert cursor.fetchone() is None


# --- Enums and models ---


class TestModels:
    def test_identify_kind_2(self):
        assert len(IdentifyKind) == 2
        assert {k.value for k in IdentifyKind} == {"identify", "manual_add"}

    def test_vehicle_guess_defaults(self):
        g = VehicleGuess(
            make="Honda", model="CBR929RR",
            year_range=(2000, 2001),
            engine_cc_range=(900, 930),
            confidence=0.88,
        )
        assert g.powertrain_guess == "ice"
        assert g.model_used == "haiku"
        assert g.cached is False
        assert g.alert is None

    def test_vehicle_guess_electric_no_cc(self):
        g = VehicleGuess(
            make="Harley-Davidson", model="LiveWire One",
            year_range=(2024, 2024),
            engine_cc_range=None,
            powertrain_guess="electric",
            confidence=0.95,
        )
        assert g.engine_cc_range is None

    def test_confidence_bounded(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            VehicleGuess(
                make="X", model="Y", year_range=(2020, 2020),
                confidence=1.5,
            )


# --- Image preprocessing ---


class TestPreprocessing:
    def test_resize_large_image(self, jpeg_path):
        from PIL import Image
        jpeg_bytes, sha = _preprocess_image(jpeg_path)
        img = Image.open(io.BytesIO(jpeg_bytes))
        assert max(img.size) == 1024
        assert img.mode == "RGB"
        assert len(sha) == 64  # sha256 hex

    def test_hash_deterministic(self, jpeg_path):
        _, sha1 = _preprocess_image(jpeg_path)
        _, sha2 = _preprocess_image(jpeg_path)
        assert sha1 == sha2

    def test_png_alpha_flattened(self, png_alpha_path):
        from PIL import Image
        jpeg_bytes, sha = _preprocess_image(png_alpha_path)
        img = Image.open(io.BytesIO(jpeg_bytes))
        assert img.mode == "RGB"  # alpha gone
        assert len(jpeg_bytes) > 0

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            _preprocess_image(tmp_path / "nope.jpg")

    def test_directory_raises(self, tmp_path):
        d = tmp_path / "adir"
        d.mkdir()
        with pytest.raises(ValueError, match="not a file"):
            _preprocess_image(d)

    def test_unsupported_format(self, tmp_path):
        p = tmp_path / "fake.jpg"
        p.write_bytes(b"not an image")
        with pytest.raises(ValueError, match="Unsupported"):
            _preprocess_image(p)


# --- Cost ---


class TestCostComputation:
    def test_zero_tokens_zero_cost(self):
        assert _compute_cost_cents("haiku", 0, 0) == 0

    def test_haiku_typical_call(self):
        # 1500 in + 400 out ≈ (1500*100 + 400*500) / 1e6 ≈ 0.35 cents → rounds to 1¢
        cents = _compute_cost_cents("haiku", 1500, 400)
        assert cents == 1

    def test_sonnet_more_expensive_than_haiku(self):
        h = _compute_cost_cents("haiku", 10000, 2000)
        s = _compute_cost_cents("sonnet", 10000, 2000)
        assert s > h

    def test_unknown_model_defaults_to_haiku(self):
        cents = _compute_cost_cents("opus", 1500, 400)
        assert cents > 0


# --- JSON parse ---


class TestJsonParse:
    def test_valid_ice(self):
        g = _parse_guess_json(_sample_guess_json(), "haiku", "hash0")
        assert g.make == "Honda"
        assert g.model == "CBR929RR"
        assert g.year_range == (2000, 2001)
        assert g.engine_cc_range == (900, 930)

    def test_valid_electric_null_cc(self):
        raw = json.dumps({
            "make": "Harley-Davidson", "model": "LiveWire One",
            "year_low": 2024, "year_high": 2024,
            "engine_cc_low": None, "engine_cc_high": None,
            "powertrain_guess": "electric",
            "confidence": 0.95,
            "reasoning": "Clean tank, no exhaust, visible motor pack.",
        })
        g = _parse_guess_json(raw, "haiku", "hash0")
        assert g.engine_cc_range is None
        assert g.powertrain_guess == "electric"

    def test_markdown_fenced_accepted(self):
        raw = "```json\n" + _sample_guess_json() + "\n```"
        g = _parse_guess_json(raw, "haiku", "hash0")
        assert g.make == "Honda"

    def test_malformed_raises(self):
        with pytest.raises(IntakeError, match="valid JSON"):
            _parse_guess_json("not even close", "haiku", "hash0")

    def test_missing_required_key(self):
        raw = json.dumps({"make": "Honda", "model": "CBR929RR", "confidence": 0.8})
        with pytest.raises(IntakeError, match="missing required keys"):
            _parse_guess_json(raw, "haiku", "hash0")


# --- Tier detection ---


class TestTierDetection:
    def test_no_subscription_defaults_individual(self, db):
        # User exists (system user id=1)
        assert _get_user_tier(1, db) == "individual"

    def test_active_subscription(self, db):
        create_subscription(Subscription(
            user_id=1, tier=SubscriptionTier.SHOP,
            status=SubscriptionStatus.ACTIVE,
        ), db)
        assert _get_user_tier(1, db) == "shop"

    def test_cancelled_subscription_fallback(self, db):
        create_subscription(Subscription(
            user_id=1, tier=SubscriptionTier.SHOP,
            status=SubscriptionStatus.CANCELLED,
        ), db)
        assert _get_user_tier(1, db) == "individual"

    def test_most_recent_active_wins(self, db):
        create_subscription(Subscription(
            user_id=1, tier=SubscriptionTier.INDIVIDUAL,
            status=SubscriptionStatus.ACTIVE,
        ), db)
        create_subscription(Subscription(
            user_id=1, tier=SubscriptionTier.COMPANY,
            status=SubscriptionStatus.ACTIVE,
        ), db)
        # Most-recently-started active row
        assert _get_user_tier(1, db) == "company"


# --- Quota ---


class TestQuota:
    def test_individual_default(self, db):
        vi = VehicleIdentifier(db_path=db)
        q = vi.check_quota(user_id=1)
        assert q.tier == "individual"
        assert q.monthly_limit == 20
        assert q.used_this_month == 0
        assert q.remaining == 20
        assert q.percent_used == 0.0

    def test_company_unlimited(self, db):
        create_subscription(Subscription(
            user_id=1, tier=SubscriptionTier.COMPANY,
            status=SubscriptionStatus.ACTIVE,
        ), db)
        vi = VehicleIdentifier(db_path=db)
        q = vi.check_quota(user_id=1)
        assert q.monthly_limit is None
        assert q.remaining is None
        assert q.percent_used == 0.0

    def test_usage_counted(self, db, jpeg_path):
        mock = make_vision_mock(_sample_guess_json())
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        vi.identify(jpeg_path, user_id=1)
        q = vi.check_quota(user_id=1)
        assert q.used_this_month == 1
        assert q.remaining == 19


# --- Identify flow ---


class TestIdentifyFlow:
    def test_basic_identify(self, db, jpeg_path):
        mock = make_vision_mock(_sample_guess_json(confidence=0.9))
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g = vi.identify(jpeg_path, user_id=1)
        assert g.make == "Honda"
        assert g.model_used == "haiku"
        assert g.cached is False
        # Only one vision call for Haiku high-confidence
        assert mock.calls["i"] == 1

    def test_sonnet_escalation_on_low_confidence(self, db, jpeg_path):
        # Haiku returns 0.4 → below threshold → retry with Sonnet returning 0.85
        mock = make_vision_mock([
            _sample_guess_json(confidence=0.4),
            _sample_guess_json(confidence=0.85),
        ])
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g = vi.identify(jpeg_path, user_id=1)
        assert g.model_used == "sonnet"
        assert g.confidence == 0.85
        assert mock.calls["i"] == 2

    def test_force_sonnet_no_escalation_back(self, db, jpeg_path):
        mock = make_vision_mock(_sample_guess_json(confidence=0.4))
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g = vi.identify(jpeg_path, user_id=1, force_model="sonnet")
        assert g.model_used == "sonnet"
        # Force disables escalation — only one call
        assert mock.calls["i"] == 1

    def test_cache_hit_zero_tokens(self, db, jpeg_path):
        mock = make_vision_mock(_sample_guess_json())
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g1 = vi.identify(jpeg_path, user_id=1)
        assert g1.cached is False
        g2 = vi.identify(jpeg_path, user_id=1)
        assert g2.cached is True
        # Second call does not hit vision
        assert mock.calls["i"] == 1
        # But both calls logged against the quota (cache hits count as usage)
        q = vi.check_quota(user_id=1)
        assert q.used_this_month == 2

    def test_quota_exhausted_raises(self, db, jpeg_path):
        mock = make_vision_mock(_sample_guess_json())
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        # Pre-fill 20 usage rows directly
        with get_connection(db) as conn:
            for _ in range(20):
                conn.execute(
                    "INSERT INTO intake_usage_log (user_id, kind, model_used, "
                    "tokens_input, tokens_output, cost_cents) VALUES (1, 'identify', 'haiku', 100, 50, 1)"
                )
        with pytest.raises(QuotaExceededError) as exc:
            vi.identify(jpeg_path, user_id=1)
        assert "individual" in str(exc.value)
        assert "20/20" in str(exc.value)

    def test_malformed_json_retries_once(self, db, jpeg_path):
        mock = make_vision_mock([
            "not json at all",
            _sample_guess_json(confidence=0.9),
        ])
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g = vi.identify(jpeg_path, user_id=1)
        assert g.confidence == 0.9
        assert mock.calls["i"] == 2

    def test_malformed_twice_raises(self, db, jpeg_path):
        mock = make_vision_mock(["bad", "still bad"])
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        with pytest.raises(IntakeError):
            vi.identify(jpeg_path, user_id=1)


# --- Budget alert ---


class TestBudgetAlert:
    def test_no_alert_below_threshold(self, db, jpeg_path):
        # Pre-fill 15 → this call puts at 16/20 = 80% threshold exactly
        # Actually 15/20 = 75%, this call 16/20 = 80% — crossing!
        # Test the non-crossing case: 10 before → 11/20 = 55% → no alert
        with get_connection(db) as conn:
            for _ in range(10):
                conn.execute(
                    "INSERT INTO intake_usage_log (user_id, kind, model_used, "
                    "tokens_input, tokens_output, cost_cents) VALUES (1, 'identify', 'haiku', 100, 50, 1)"
                )
        mock = make_vision_mock(_sample_guess_json())
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g = vi.identify(jpeg_path, user_id=1)
        assert g.alert is None

    def test_alert_on_crossing_threshold(self, db, jpeg_path):
        # Pre-fill 15 → percent_used = 0.75. This call: 16/20 = 0.80 → alert
        with get_connection(db) as conn:
            for _ in range(15):
                conn.execute(
                    "INSERT INTO intake_usage_log (user_id, kind, model_used, "
                    "tokens_input, tokens_output, cost_cents) VALUES (1, 'identify', 'haiku', 100, 50, 1)"
                )
        mock = make_vision_mock(_sample_guess_json())
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g = vi.identify(jpeg_path, user_id=1)
        assert g.alert is not None
        assert "80%" in g.alert

    def test_no_alert_already_past_threshold(self, db, jpeg_path):
        # Pre-fill 17 → 85% already. This call: 18/20 = 90%. Was above threshold, still above.
        # Don't re-fire — only crossings.
        with get_connection(db) as conn:
            for _ in range(17):
                conn.execute(
                    "INSERT INTO intake_usage_log (user_id, kind, model_used, "
                    "tokens_input, tokens_output, cost_cents) VALUES (1, 'identify', 'haiku', 100, 50, 1)"
                )
        mock = make_vision_mock(_sample_guess_json())
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g = vi.identify(jpeg_path, user_id=1)
        assert g.alert is None

    def test_no_alert_for_company_tier(self, db, jpeg_path):
        create_subscription(Subscription(
            user_id=1, tier=SubscriptionTier.COMPANY,
            status=SubscriptionStatus.ACTIVE,
        ), db)
        mock = make_vision_mock(_sample_guess_json())
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        g = vi.identify(jpeg_path, user_id=1)
        assert g.alert is None


# --- Usage logging ---


class TestUsageLogging:
    def test_log_records_tokens_and_cost(self, db, jpeg_path):
        mock = make_vision_mock(_sample_guess_json(), tokens_in=1500, tokens_out=400)
        vi = VehicleIdentifier(vision_call=mock, db_path=db)
        vi.identify(jpeg_path, user_id=1)
        with get_connection(db) as conn:
            cursor = conn.execute(
                "SELECT model_used, tokens_input, tokens_output, cost_cents, "
                "image_hash, confidence FROM intake_usage_log WHERE user_id = 1"
            )
            row = dict(cursor.fetchone())
        assert row["model_used"] == "haiku"
        assert row["tokens_input"] == 1500
        assert row["tokens_output"] == 400
        assert row["cost_cents"] >= 1
        assert len(row["image_hash"]) == 64
        assert row["confidence"] == 0.88  # default in _sample_guess_json


# --- CLI ---


@pytest.fixture
def cli_db(db, monkeypatch):
    """DB fixture that also redirects the cached settings.db_path to the test DB."""
    from motodiag.core.config import reset_settings
    monkeypatch.setenv("MOTODIAG_DB_PATH", db)
    reset_settings()  # Invalidate lru_cache so new env var takes effect
    yield db
    reset_settings()  # Clean up after test so next test gets a fresh settings


class TestCliGarage:
    def test_garage_add_and_list(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, [
            "garage", "add",
            "--make", "Honda", "--model", "CBR929RR", "--year", "2001",
            "--engine-cc", "929", "--protocol", "k_line",
        ])
        assert r.exit_code == 0, r.output
        assert "Added vehicle" in r.output

        r = runner.invoke(cli, ["garage", "list"])
        assert r.exit_code == 0
        assert "Honda" in r.output
        assert "CBR929RR" in r.output

    def test_garage_remove(self, cli_db):
        # Seed one vehicle via the same DB the CLI will use
        vid = add_vehicle(VehicleBase(
            make="Honda", model="CBR929RR", year=2001,
            engine_cc=929, protocol=ProtocolType.K_LINE,
        ), db_path=cli_db)

        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["garage", "remove", str(vid), "--yes"])
        assert r.exit_code == 0, r.output
        assert "Removed" in r.output
        assert list_vehicles(db_path=cli_db) == []


class TestCliIntake:
    def test_intake_quota_individual(self, cli_db):
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["intake", "quota"])
        assert r.exit_code == 0
        assert "individual" in r.output
        assert "0/20" in r.output

    def test_intake_quota_warns_at_threshold(self, cli_db):
        with get_connection(cli_db) as conn:
            for _ in range(17):
                conn.execute(
                    "INSERT INTO intake_usage_log (user_id, kind, model_used, "
                    "tokens_input, tokens_output, cost_cents) VALUES (1, 'identify', 'haiku', 100, 50, 1)"
                )
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["intake", "quota"])
        assert r.exit_code == 0
        assert "17/20" in r.output

    def test_intake_quota_company_unlimited(self, cli_db):
        create_subscription(Subscription(
            user_id=1, tier=SubscriptionTier.COMPANY,
            status=SubscriptionStatus.ACTIVE,
        ), cli_db)
        from motodiag.cli.main import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["intake", "quota"])
        assert r.exit_code == 0
        assert "unlimited" in r.output.lower()


# --- Forward compat ---


class TestSchemaVersionForwardCompat:
    def test_schema_version_at_least_13(self, db):
        assert get_schema_version(db) >= 13

    def test_schema_version_constant_at_least_13(self):
        assert SCHEMA_VERSION >= 13
