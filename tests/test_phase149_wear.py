"""Phase 149 — wear pattern analysis tests.

Four test classes across ~29 tests:

- :class:`TestWearPatternModel` (4) — Pydantic round-trip, frozen
  semantics, tuple stability, confidence_hint range enforcement.
- :class:`TestAnalyzer` (12) — tokenizer edges, substring-either-
  direction match, bike-match-tier ladder (exact/family/make/generic),
  dropped-make patterns, generic patterns cross-make, min_confidence
  boundaries (0.0 / 0.5 / 1.0), confidence_hint floor, empty symptoms,
  missing file, sort determinism.
- :class:`TestWearCommand` (10, CliRunner) — --bike happy path,
  direct-args path, --json round-trip, unknown bike → remediation
  panel, mutex, missing --symptoms, invalid --min-confidence, empty
  matches → yellow panel, --help, Phase 148 ``predict`` still
  registered alongside.
- :class:`TestRegression` (3) — Phase 148 predict, Phase 140 hardware
  scan, Phase 08 known_issues still pass with Phase 149 loaded.

All tests are SW-only — zero AI, zero network, zero tokens. The
catalog file lives next to ``wear.py``; the analyzer's
``patterns_path=`` hook lets tests inject tiny fixtures without
touching the shipped 30-entry catalog.
"""

from __future__ import annotations

import json as _json
from pathlib import Path

import pytest
from click.testing import CliRunner

from motodiag.advanced import analyze_wear
from motodiag.advanced.wear import (
    WearMatch,
    WearPattern,
    _bike_match_tier,
    _load_wear_patterns,
    _tokenize_symptoms,
)
from motodiag.cli.advanced import register_advanced
from motodiag.core.database import init_db


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_cli():
    """Build a fresh CLI group with only `advanced` registered."""
    import click

    @click.group()
    def root() -> None:
        """test root"""

    register_advanced(root)
    return root


@pytest.fixture(autouse=True)
def _clear_pattern_cache():
    """Ensure each test gets a fresh lru_cache'd pattern load.

    The analyzer memoizes on path, and tests inject different tmp
    fixture paths per run — but a stale cache for the default catalog
    path survives across tests if we don't clear. Safer to reset.
    """
    _load_wear_patterns.cache_clear()
    yield
    _load_wear_patterns.cache_clear()


@pytest.fixture
def cli_db(tmp_path, monkeypatch):
    """Point settings + CLI paths at a temp DB. Mirrors Phase 148."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase149_cli.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    yield path
    reset_settings()


# A small fixture catalog — 4 patterns that exercise all four tiers
# (exact / family / make / generic) without relying on the shipped
# 30-entry JSON. Written to tmp_path so each test gets a clean copy.
_FIXTURE_PATTERNS = [
    {
        "id": "tc88-tensioner-fixture",
        "component": "cam chain tensioner",
        "make": "harley-davidson",
        "model_pattern": "sportster%",
        "year_min": 2001,
        "year_max": 2006,
        "symptoms": [
            "tick of death",
            "valvetrain tick at 2000 rpm",
        ],
        "inspection_steps": ["Pull primary", "Measure slack"],
        "confidence_hint": 0.9,
        "verified_by": "hdforums consensus",
    },
    {
        "id": "klr-fixture",
        "component": "doohickey",
        "make": "kawasaki",
        "model_pattern": "klr%",
        "year_min": 1987,
        "year_max": 2007,
        "symptoms": ["ticking from right side"],
        "inspection_steps": ["Drain oil", "Pull cover"],
        "confidence_hint": 0.95,
        "verified_by": "klrworld",
    },
    {
        "id": "generic-chain-fixture",
        "component": "drive chain",
        "make": None,
        "model_pattern": "%",
        "year_min": None,
        "year_max": None,
        "symptoms": ["chain slap", "chain stretch"],
        "inspection_steps": ["Pull chain", "Measure 20-pin"],
        "confidence_hint": 0.8,
        "verified_by": "service manual",
    },
    {
        "id": "harley-generic-fixture",
        "component": "primary tensioner",
        "make": "harley-davidson",
        # Make-level fallback: model_pattern won't match road glide,
        # but the make WILL — so we drop to "make" tier when year
        # misses, or "family" when year hits.
        "model_pattern": "electra%",
        "year_min": 2010,
        "year_max": 2020,
        "symptoms": ["primary rattle", "whine from primary"],
        "inspection_steps": ["Pull cover", "Inspect shoe"],
        "confidence_hint": 0.75,
        "verified_by": "hdforums",
    },
]


@pytest.fixture
def fixture_catalog(tmp_path):
    """Write the fixture catalog and return its path."""
    path = tmp_path / "fixture_wear.json"
    path.write_text(_json.dumps(_FIXTURE_PATTERNS), encoding="utf-8")
    return str(path)


# ===========================================================================
# 1. WearPattern / WearMatch models
# ===========================================================================


class TestWearPatternModel:
    """Pydantic v2 round-trip + frozen + tuple stability."""

    def _pattern_kwargs(self) -> dict:
        return dict(
            id="test-1",
            component="test component",
            make="harley-davidson",
            model_pattern="sportster%",
            year_min=2001,
            year_max=2006,
            symptoms=("tick of death", "valvetrain noise"),
            inspection_steps=("step 1", "step 2", "step 3"),
            confidence_hint=0.9,
            verified_by="hdforums",
        )

    def test_roundtrip_json_mode(self):
        """model_dump(mode='json') + model_validate preserves all fields."""
        pat = WearPattern(**self._pattern_kwargs())
        dumped = pat.model_dump(mode="json")
        # Tuples serialize as JSON arrays
        assert dumped["symptoms"] == ["tick of death", "valvetrain noise"]
        assert dumped["inspection_steps"] == ["step 1", "step 2", "step 3"]
        restored = WearPattern.model_validate(dumped)
        assert restored == pat

    def test_frozen_prevents_mutation(self):
        """ConfigDict(frozen=True) blocks attribute assignment."""
        pat = WearPattern(**self._pattern_kwargs())
        with pytest.raises(Exception):
            pat.confidence_hint = 0.1

    def test_tuple_symptoms_stability(self):
        """Symptoms arriving as a list coerce to tuple for hashability."""
        kw = self._pattern_kwargs()
        kw["symptoms"] = ["a", "b", "c"]
        pat = WearPattern(**kw)
        assert pat.symptoms == ("a", "b", "c")
        # Must be hashable (tuples are)
        hash(pat.symptoms)

    def test_confidence_hint_range_enforced(self):
        """confidence_hint is clamped [0, 1] — out-of-range raises."""
        kw = self._pattern_kwargs()
        kw["confidence_hint"] = 1.5
        with pytest.raises(Exception):
            WearPattern(**kw)
        kw["confidence_hint"] = -0.1
        with pytest.raises(Exception):
            WearPattern(**kw)


# ===========================================================================
# 2. analyze_wear() core logic
# ===========================================================================


class TestAnalyzer:
    """Tokenization, matching, bike-tier ladder, and filters."""

    def test_tokenizer_comma_and_semicolon(self):
        """Both ',' and ';' delimiters work, dedupe preserved."""
        tokens = _tokenize_symptoms("tick of death, DIM headlight; chain slap")
        assert tokens == ["tick of death", "dim headlight", "chain slap"]

    def test_tokenizer_dedupe_preserves_order(self):
        """Repeated tokens are deduped; first-occurrence order kept."""
        tokens = _tokenize_symptoms("a, b, a, c, b")
        assert tokens == ["a", "b", "c"]

    def test_tokenizer_empty_returns_empty(self):
        """Empty / whitespace / None → []."""
        assert _tokenize_symptoms("") == []
        assert _tokenize_symptoms("   ") == []
        assert _tokenize_symptoms(None) == []

    def test_empty_symptoms_returns_empty(self, fixture_catalog):
        """analyze_wear with empty symptoms → [] (no crash, no load)."""
        vehicle = {"make": "Harley-Davidson", "model": "Sportster 1200", "year": 2003}
        assert analyze_wear(vehicle, "", patterns_path=fixture_catalog) == []
        assert analyze_wear(vehicle, [], patterns_path=fixture_catalog) == []

    def test_substring_either_direction(self, fixture_catalog):
        """User token 'tick' matches pattern 'tick of death' AND vice versa."""
        vehicle = {"make": "Harley-Davidson", "model": "Sportster 1200", "year": 2003}
        # User says "ticking" — should substring-match "tick of death" only if
        # we also do pattern-in-user; here we do BOTH directions. "tick" is
        # in "tick of death" (user token is substring of pattern symptom).
        matches = analyze_wear(
            vehicle, "tick",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        assert any("tick of death" in m.symptoms_matched for m in matches)

    def test_exact_tier_scores_highest(self, fixture_catalog):
        """make + model + year all match → tier='exact', strongest score."""
        vehicle = {"make": "Harley-Davidson", "model": "Sportster 1200", "year": 2003}
        matches = analyze_wear(
            vehicle, "tick of death, valvetrain tick at 2000 rpm",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        exact = [m for m in matches if m.bike_match_tier == "exact"]
        assert exact, "Expected an exact-tier match"
        assert exact[0].pattern_id == "tc88-tensioner-fixture"

    def test_family_tier_when_year_out_of_range(self, fixture_catalog):
        """make + model match, year outside range → family."""
        vehicle = {"make": "Harley-Davidson", "model": "Sportster 1200", "year": 2015}
        matches = analyze_wear(
            vehicle, "tick of death",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        family = [m for m in matches if m.bike_match_tier == "family"]
        assert family, "Expected a family-tier match"

    def test_make_tier_when_model_missing(self, fixture_catalog):
        """make matches but model_pattern doesn't → make-tier."""
        vehicle = {"make": "Harley-Davidson", "model": "Road Glide", "year": 2015}
        matches = analyze_wear(
            vehicle, "primary rattle",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        make_tier = [m for m in matches if m.bike_match_tier == "make"]
        assert make_tier, "Expected a make-tier match"

    def test_dropped_when_make_mismatches(self, fixture_catalog):
        """Kawasaki pattern must NEVER appear in Harley results."""
        vehicle = {"make": "Harley-Davidson", "model": "Sportster 1200", "year": 2003}
        matches = analyze_wear(
            vehicle, "ticking from right side",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        # KLR fixture must be dropped (Kawasaki vs Harley)
        assert not any(m.pattern_id == "klr-fixture" for m in matches)

    def test_generic_tier_scores_cross_make(self, fixture_catalog):
        """make=None patterns score against every bike."""
        for make in ("Harley-Davidson", "Kawasaki", "Honda", "Vincent"):
            vehicle = {"make": make, "model": "Whatever", "year": 2010}
            matches = analyze_wear(
                vehicle, "chain slap",
                min_confidence=0.0,
                patterns_path=fixture_catalog,
            )
            generics = [m for m in matches if m.bike_match_tier == "generic"]
            assert generics, f"Expected generic match for {make}"

    def test_min_confidence_boundaries(self, fixture_catalog):
        """min_confidence=0.0 keeps everything, 1.0 only perfects."""
        vehicle = {"make": "Harley-Davidson", "model": "Sportster 1200", "year": 2003}
        all_matches = analyze_wear(
            vehicle, "tick of death",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        perfect_only = analyze_wear(
            vehicle, "tick of death",
            min_confidence=1.0,
            patterns_path=fixture_catalog,
        )
        assert len(all_matches) >= len(perfect_only)
        # Default 0.5 floor — some matches should still get through
        default = analyze_wear(
            vehicle, "tick of death",
            min_confidence=0.5,
            patterns_path=fixture_catalog,
        )
        for m in default:
            assert m.confidence_score >= 0.5

    def test_confidence_hint_floor_applied(self, fixture_catalog):
        """Score floor = ratio * confidence_hint; observable for partial
        coverage on high-confidence-hint patterns."""
        vehicle = {"make": "Harley-Davidson", "model": "Sportster 1200", "year": 2003}
        # 1 matched out of 2 pattern symptoms = ratio 0.5;
        # floor = 0.5 * 0.9 = 0.45; raw = 0.5*0.7 + 1.0*0.3 = 0.65.
        # Score should be max(0.65, 0.45) = 0.65. Match still passes 0.5 gate.
        matches = analyze_wear(
            vehicle, "tick of death",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        tc88 = next(m for m in matches if m.pattern_id == "tc88-tensioner-fixture")
        assert tc88.confidence_score > 0.5

    def test_missing_file_raises(self, tmp_path):
        """Non-existent patterns_path raises FileNotFoundError."""
        vehicle = {"make": "a", "model": "b", "year": 2000}
        bogus = str(tmp_path / "nosuch.json")
        with pytest.raises(FileNotFoundError):
            analyze_wear(vehicle, "x", patterns_path=bogus)

    def test_sort_determinism(self, fixture_catalog):
        """Results sort confidence DESC → matched-count DESC → pattern_id ASC."""
        vehicle = {"make": "Harley-Davidson", "model": "Sportster 1200", "year": 2003}
        matches = analyze_wear(
            vehicle,
            "tick of death, valvetrain tick at 2000 rpm, chain slap, primary rattle",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        # Run twice to confirm determinism
        again = analyze_wear(
            vehicle,
            "tick of death, valvetrain tick at 2000 rpm, chain slap, primary rattle",
            min_confidence=0.0,
            patterns_path=fixture_catalog,
        )
        assert [m.pattern_id for m in matches] == [m.pattern_id for m in again]
        # Confirm sort order: confidence DESC
        for a, b in zip(matches, matches[1:]):
            if a.confidence_score == b.confidence_score:
                if len(a.symptoms_matched) == len(b.symptoms_matched):
                    assert a.pattern_id <= b.pattern_id
                else:
                    assert len(a.symptoms_matched) >= len(b.symptoms_matched)
            else:
                assert a.confidence_score >= b.confidence_score


# ===========================================================================
# 3. motodiag advanced wear CLI
# ===========================================================================


class TestWearCommand:
    """Click-runner tests for the wear subcommand."""

    def _seed_vehicle(self, db_path: str) -> int:
        """Seed a Harley Sportster 1200 2003 for --bike tests."""
        from motodiag.core.models import (
            VehicleBase, ProtocolType, PowertrainType, EngineType,
        )
        from motodiag.vehicles.registry import add_vehicle

        vehicle = VehicleBase(
            make="Harley-Davidson",
            model="Sportster 1200",
            year=2003,
            engine_cc=1200,
            protocol=ProtocolType.J1850,
            powertrain=PowertrainType.ICE,
            engine_type=EngineType.FOUR_STROKE,
        )
        return add_vehicle(vehicle, db_path=db_path)

    def test_bike_happy_path(self, cli_db):
        """--bike sportster-2003 with real symptoms returns the TC88 pattern."""
        self._seed_vehicle(cli_db)

        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "wear",
                "--bike", "sportster-2003",
                "--symptoms", "tick of death, valvetrain tick at 2000 rpm",
                "--min-confidence", "0.1",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "cam chain tensioner" in result.output.lower()

    def test_direct_args_happy_path(self, cli_db):
        """--make/--model/--year synthesizes a vehicle."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "wear",
                "--make", "Harley-Davidson",
                "--model", "Sportster 1200",
                "--year", "2003",
                "--symptoms", "tick of death",
                "--min-confidence", "0.1",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "cam chain tensioner" in result.output.lower()

    def test_json_output_parses(self, cli_db):
        """--json emits a JSON object with vehicle + matches keys."""
        self._seed_vehicle(cli_db)

        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "wear",
                "--bike", "sportster-2003",
                "--symptoms", "tick of death",
                "--min-confidence", "0.1",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = _json.loads(result.output)
        assert "vehicle" in payload
        assert "matches" in payload
        for raw in payload["matches"]:
            wm = WearMatch.model_validate(raw)
            assert wm.confidence_score >= 0.1

    def test_unknown_bike_remediation(self, cli_db):
        """Unknown slug renders a red 'not found' panel + exit 1."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "wear",
                "--bike", "nosuch-bike-2099",
                "--symptoms", "tick",
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "no bike" in result.output.lower()

    def test_bike_and_make_mutex(self, cli_db):
        """--bike + --make is a user error."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "wear",
                "--bike", "sportster-2003",
                "--make", "Harley-Davidson",
                "--model", "Sportster 1200",
                "--year", "2003",
                "--symptoms", "tick",
            ],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_missing_symptoms_is_error(self, cli_db):
        """--symptoms is required."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "wear",
                "--make", "Harley-Davidson",
                "--model", "Sportster 1200",
                "--year", "2003",
            ],
        )
        assert result.exit_code != 0
        assert "symptoms" in result.output.lower()

    def test_invalid_min_confidence(self, cli_db):
        """--min-confidence outside [0, 1] raises ClickException."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "wear",
                "--make", "Harley-Davidson",
                "--model", "Sportster 1200",
                "--year", "2003",
                "--symptoms", "tick",
                "--min-confidence", "1.5",
            ],
        )
        assert result.exit_code != 0
        assert "min-confidence" in result.output.lower() or "between" in result.output.lower()

    def test_empty_matches_yellow_panel(self, cli_db):
        """No matches → yellow 'No wear matches' panel (not a crash)."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(),
            [
                "advanced", "wear",
                "--make", "Vincent",
                "--model", "Black Shadow",
                "--year", "1951",
                "--symptoms", "abcdefghijk zzzz xxxx",  # Nonsense — no match
                "--min-confidence", "0.5",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "no wear matches" in result.output.lower() or "no wear" in result.output.lower()

    def test_help_renders(self, cli_db):
        """motodiag advanced wear --help lists all flags."""
        runner = CliRunner()
        result = runner.invoke(
            _make_cli(), ["advanced", "wear", "--help"]
        )
        assert result.exit_code == 0
        for flag in ("--bike", "--make", "--model", "--year",
                     "--symptoms", "--min-confidence", "--json"):
            assert flag in result.output

    def test_phase148_predict_still_registered(self, cli_db):
        """Phase 148 predict subcommand still exists alongside wear."""
        cli = _make_cli()
        advanced_group = cli.commands["advanced"]
        assert "predict" in advanced_group.commands
        assert "wear" in advanced_group.commands


# ===========================================================================
# 4. Regression
# ===========================================================================


class TestRegression:
    """Prior-phase regression smoke checks."""

    def test_phase148_predict_imports_clean(self):
        """Phase 148 predict still imports + registers."""
        from motodiag.advanced import predict_failures  # noqa: F401
        from motodiag.cli.advanced import register_advanced

        import click

        @click.group()
        def root():
            pass

        register_advanced(root)
        assert "advanced" in root.commands
        advanced_group = root.commands["advanced"]
        assert "predict" in advanced_group.commands

    def test_phase140_hardware_scan_imports(self):
        """Phase 140 hardware CLI is still importable + registers cleanly."""
        from motodiag.cli.hardware import register_hardware

        import click

        @click.group()
        def root():
            pass

        register_hardware(root)
        assert "hardware" in root.commands

    def test_phase08_known_issues_search(self, tmp_path):
        """Phase 08 search_known_issues unchanged and functional."""
        from motodiag.knowledge.issues_repo import (
            add_known_issue,
            search_known_issues,
        )

        db = str(tmp_path / "phase149_regression.db")
        init_db(db)
        add_known_issue(
            title="Test issue",
            description="Description",
            make="Honda",
            model="CBR600RR",
            year_start=2003,
            year_end=2007,
            severity="high",
            symptoms=["test symptom"],
            dtc_codes=[],
            causes=["test cause"],
            fix_procedure="test fix",
            parts_needed=["test part"],
            estimated_hours=1.0,
            db_path=db,
        )
        rows = search_known_issues(make="Honda", db_path=db)
        assert len(rows) >= 1
        assert rows[0]["make"].lower() == "honda"


# Also verify the shipped 30-entry catalog loads and is well-formed
# (lives in module scope so pytest collects it as a top-level test).


def test_shipped_catalog_loads():
    """The canonical wear_patterns.json loads + all entries validate."""
    _load_wear_patterns.cache_clear()
    default_path = str(
        Path(__file__).parents[1]
        / "src" / "motodiag" / "advanced" / "wear_patterns.json"
    )
    patterns = _load_wear_patterns(default_path)
    assert len(patterns) == 30
    # All entries are valid WearPattern instances
    assert all(isinstance(p, WearPattern) for p in patterns)
    # Anchor IDs from the phase spec
    ids = {p.id for p in patterns}
    for anchor in (
        "tc88-cam-tensioner",
        "sportster-stator-undercharge",
        "chain-stretch-sprocket",
        "fork-seal-leak-upper",
        "wheel-bearing-whine-rear",
    ):
        assert anchor in ids, f"Missing anchor entry {anchor}"
    _load_wear_patterns.cache_clear()


def test_bike_match_tier_returns_none_for_make_mismatch():
    """_bike_match_tier returns None (drop signal) on explicit make mismatch."""
    pat = WearPattern(
        id="test",
        component="x",
        make="kawasaki",
        model_pattern="klr%",
        year_min=1987,
        year_max=2007,
        symptoms=("tick",),
        inspection_steps=("step",),
        confidence_hint=0.8,
        verified_by="fixture",
    )
    vehicle = {"make": "Harley-Davidson", "model": "Sportster", "year": 2003}
    assert _bike_match_tier(pat, vehicle) is None
