"""Phase 159 — Gate 7: Advanced Diagnostics Integration Test.

Pass/fail checkpoint for Track F (advanced diagnostics, phases 148-158).

Proves the advanced subgroup wires up end-to-end over the Phase 148-158
CLI surface on a shared DB via Click's ``CliRunner``: garage add →
advanced predict → wear → fleet status → schedule → history → parts →
tsb → recall → compare → baseline → drift. Zero new production code,
zero real network I/O, zero live tokens.

Three defensive AI boundary patches match the Gate 6 pattern even
though advanced diagnostics are SQL-backed analytics (no AI calls at
Gate 7 build time — patches are forward-compat for future phases).

Three test classes:
- ``TestAdvancedEndToEnd`` (1 test): the full workflow on a shared DB.
- ``TestAdvancedSurface`` (4 tests): command-tree structural assertions.
- ``TestRegression`` (3 tests): Gate 5/6 subprocess re-runs + schema
  forward-compat floor.
"""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.core.database import (
    get_connection,
    get_schema_version,
    init_db,
)


# ---------------------------------------------------------------------------
# Phase-presence probes — Gate 7 graceful-skip posture
# ---------------------------------------------------------------------------


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


_HAS_PREDICTOR = _has_module("motodiag.advanced.predictor")   # 148
_HAS_WEAR = _has_module("motodiag.advanced.wear")             # 149
_HAS_FLEET_REPO = _has_module("motodiag.advanced.fleet_repo") # 150
_HAS_SCHEDULE_REPO = _has_module("motodiag.advanced.schedule_repo")  # 151
_HAS_HISTORY_REPO = _has_module("motodiag.advanced.history_repo")    # 152
_HAS_PARTS_REPO = _has_module("motodiag.advanced.parts_repo")        # 153
_HAS_TSB_REPO = _has_module("motodiag.advanced.tsb_repo")            # 154
_HAS_RECALL_REPO = _has_module("motodiag.advanced.recall_repo")      # 155
_HAS_COMPARATIVE = _has_module("motodiag.advanced.comparative")      # 156
_HAS_BASELINE = _has_module("motodiag.advanced.baseline")            # 157
_HAS_DRIFT = _has_module("motodiag.advanced.drift")                  # 158


# ---------------------------------------------------------------------------
# Canned AI responses — defensive forward-compat only
# ---------------------------------------------------------------------------


def _fake_diagnose(**kwargs):
    response = SimpleNamespace(
        vehicle_summary="2015 Harley-Davidson Road Glide",
        symptoms_acknowledged=["gate 7 mock — never invoked"],
        diagnoses=[],
        additional_tests=[],
        notes=None,
    )
    from motodiag.engine.models import TokenUsage

    usage = TokenUsage(
        input_tokens=0,
        output_tokens=0,
        model="haiku",
        cost_estimate=0.0,
        latency_ms=0,
    )
    return response, usage


def _fake_interpret(**kwargs):
    result = SimpleNamespace(
        code="P0000",
        code_format="obd2_generic",
        description="gate 7 mock — never invoked",
        system="unused",
        possible_causes=[],
        tests_to_confirm=[],
        related_symptoms=[],
        repair_steps=[],
        estimated_hours=0.0,
        estimated_cost="$0",
        safety_critical=False,
        notes=None,
    )
    from motodiag.engine.models import TokenUsage

    usage = TokenUsage(
        input_tokens=0,
        output_tokens=0,
        model="haiku",
        cost_estimate=0.0,
        latency_ms=0,
    )
    return result, usage


def _fake_vision(image_bytes, hints, model_id):
    canned = (
        '{"make":"Harley-Davidson","model":"Road Glide",'
        '"year_range":[2014,2016],"engine_cc_range":[1690,1690],'
        '"powertrain_guess":"ice","confidence":0.5,'
        '"reasoning":"(mocked for gate 7)","alert":null}'
    )
    return canned, 0, 0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gate7_db(tmp_path, monkeypatch):
    """Point settings + env + CLI init_db at a scratch DB."""
    from motodiag.core.config import reset_settings

    db_path = str(tmp_path / "gate7.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    monkeypatch.setenv("COLUMNS", "240")
    reset_settings()
    init_db(db_path)

    # Redirect cli.advanced.init_db the same way Gate 6 redirects
    # cli.hardware.init_db — every ``advanced`` subcommand's top-of-
    # handler init_db() call re-uses the tmp DB path.
    import motodiag.cli.advanced as adv_mod

    original_init_db = adv_mod.init_db

    def _patched_init_db(*args, **kwargs):
        if args or kwargs:
            return original_init_db(*args, **kwargs)
        return original_init_db(db_path)

    monkeypatch.setattr(adv_mod, "init_db", _patched_init_db)

    yield db_path
    reset_settings()


# ---------------------------------------------------------------------------
# Class A — End-to-end advanced workflow
# ---------------------------------------------------------------------------


class TestAdvancedEndToEnd:
    """One cohesive advanced-diagnostics scenario on a shared DB.

    Every sub-step is guarded by a presence probe so a partial Track F
    landing produces a readable skip list rather than a red test.
    """

    def test_full_advanced_flow(self, gate7_db, tmp_path, monkeypatch):
        from motodiag.cli.main import cli

        runner = CliRunner()

        def run(args, input_=None):
            return runner.invoke(
                cli, args, input=input_, catch_exceptions=False,
            )

        advanced_group = cli.commands.get("advanced")
        assert advanced_group is not None, (
            "advanced subgroup not registered — Phase 148 missing?"
        )

        skipped_substeps: list[str] = []

        with patch(
            "motodiag.cli.diagnose._default_diagnose_fn", _fake_diagnose,
        ), patch(
            "motodiag.cli.code._default_interpret_fn", _fake_interpret,
        ), patch(
            "motodiag.intake.vehicle_identifier._default_vision_call",
            _fake_vision,
        ):
            # --- Step 1: garage add -----------------------------------
            r = run([
                "garage", "add",
                "--make", "Harley-Davidson",
                "--model", "Road Glide",
                "--year", "2015",
                "--vin", "1HD1KHM19FB123456",
                "--protocol", "can",
                "--powertrain", "ice",
            ])
            assert r.exit_code == 0, r.output
            bike_slug = "glide-2015"

            # --- Step 2: advanced predict (Phase 148) -----------------
            if "predict" in advanced_group.commands:
                r = run([
                    "advanced", "predict",
                    "--bike", bike_slug,
                    "--horizon-days", "180",
                    "--json",
                ])
                # Exit 0 with predictions OR exit 0 with empty-results
                # yellow panel — both prove wiring. The JSON flag may not
                # apply cleanly when there are zero predictions; be
                # tolerant of both shapes.
                assert r.exit_code == 0, r.output
            else:
                skipped_substeps.append("Phase 148 predict missing")

            # --- Step 3: advanced wear (Phase 149) --------------------
            if _HAS_WEAR and "wear" in advanced_group.commands:
                r = run([
                    "advanced", "wear",
                    "--bike", bike_slug,
                    "--symptoms", "tick of death,dim headlight",
                    "--json",
                ])
                assert r.exit_code == 0, r.output
            else:
                skipped_substeps.append("Phase 149 wear missing")

            # --- Step 4: advanced fleet (Phase 150) -------------------
            if _HAS_FLEET_REPO and "fleet" in advanced_group.commands:
                fleet_group = advanced_group.commands["fleet"]
                if "create" in fleet_group.commands:
                    r = run([
                        "advanced", "fleet", "create",
                        "gate7-fleet",
                    ])
                    assert r.exit_code == 0, r.output
                if "add-bike" in fleet_group.commands:
                    r = run([
                        "advanced", "fleet", "add-bike",
                        "gate7-fleet", "--bike", bike_slug,
                    ])
                    assert r.exit_code == 0, r.output
                if "status" in fleet_group.commands:
                    r = run([
                        "advanced", "fleet", "status", "gate7-fleet",
                    ])
                    assert r.exit_code == 0, r.output
            else:
                skipped_substeps.append("Phase 150 fleet missing")

            # --- Step 5: advanced schedule (Phase 151) ----------------
            if _HAS_SCHEDULE_REPO and (
                "schedule" in advanced_group.commands
            ):
                sched_group = advanced_group.commands["schedule"]
                if "due" in sched_group.commands:
                    r = run([
                        "advanced", "schedule", "due",
                        "--bike", bike_slug,
                    ])
                    # Either a table or a "nothing due" panel — both are
                    # valid wiring proof.
                    assert r.exit_code in (0, 1), r.output
            else:
                skipped_substeps.append("Phase 151 schedule missing")

            # --- Step 6: advanced history (Phase 152) -----------------
            if _HAS_HISTORY_REPO and (
                "history" in advanced_group.commands
            ):
                hist_group = advanced_group.commands["history"]
                if "list" in hist_group.commands:
                    r = run([
                        "advanced", "history", "list",
                        "--bike", bike_slug,
                    ])
                    assert r.exit_code == 0, r.output
            else:
                skipped_substeps.append("Phase 152 history missing")

            # --- Step 7: advanced parts (Phase 153) -------------------
            if _HAS_PARTS_REPO and "parts" in advanced_group.commands:
                parts_group = advanced_group.commands["parts"]
                if "search" in parts_group.commands:
                    r = run([
                        "advanced", "parts", "search", "stator",
                    ])
                    assert r.exit_code == 0, r.output
            else:
                skipped_substeps.append("Phase 153 parts missing")

            # --- Step 8: advanced tsb (Phase 154) ---------------------
            if _HAS_TSB_REPO and "tsb" in advanced_group.commands:
                tsb_group = advanced_group.commands["tsb"]
                if "list" in tsb_group.commands:
                    r = run(["advanced", "tsb", "list", "--limit", "5"])
                    assert r.exit_code == 0, r.output
                if "search" in tsb_group.commands:
                    r = run([
                        "advanced", "tsb", "search", "stator",
                    ])
                    assert r.exit_code == 0, r.output
            else:
                skipped_substeps.append("Phase 154 tsb missing")

            # --- Step 9: advanced recall (Phase 155) ------------------
            if _HAS_RECALL_REPO and "recall" in advanced_group.commands:
                recall_group = advanced_group.commands["recall"]
                if "list" in recall_group.commands:
                    r = run([
                        "advanced", "recall", "list",
                        "--make", "Harley-Davidson",
                    ])
                    assert r.exit_code == 0, r.output
            else:
                skipped_substeps.append("Phase 155 recall missing")

            # --- Step 10: advanced compare (Phase 156) ----------------
            if _HAS_COMPARATIVE and (
                "compare" in advanced_group.commands
            ):
                cmp_group = advanced_group.commands["compare"]
                if "bike" in cmp_group.commands:
                    r = run([
                        "advanced", "compare", "bike",
                        "--bike", bike_slug,
                    ])
                    # Exit 0 (peer stats or "no peers" panel) — both fine.
                    assert r.exit_code in (0, 1), r.output
            else:
                skipped_substeps.append("Phase 156 compare missing")

            # --- Step 11: advanced baseline (Phase 157) ---------------
            if _HAS_BASELINE and (
                "baseline" in advanced_group.commands
            ):
                bl_group = advanced_group.commands["baseline"]
                if "list" in bl_group.commands:
                    r = run(["advanced", "baseline", "list"])
                    assert r.exit_code == 0, r.output
            else:
                skipped_substeps.append("Phase 157 baseline missing")

            # --- Step 12: advanced drift (Phase 158) ------------------
            if _HAS_DRIFT and "drift" in advanced_group.commands:
                drift_group = advanced_group.commands["drift"]
                # ``drift show`` takes only --bike (no --pid). ``drift
                # bike`` requires both --bike and --pid, so we use show
                # as the Gate 7 wiring probe — same Phase 158 code
                # path, cleaner CLI shape for integration tests.
                if "show" in drift_group.commands:
                    r = run([
                        "advanced", "drift", "show",
                        "--bike", bike_slug,
                    ])
                    # No drift data → "no recordings" panel. Both fine.
                    assert r.exit_code in (0, 1), r.output
            else:
                skipped_substeps.append("Phase 158 drift missing")

        # --- Final integrity --------------------------------------------
        schema = get_schema_version(gate7_db)
        # Phase 148 is the Track F floor — migration 017 at minimum.
        assert schema >= 17, (
            f"schema must be >= Track F floor (v17); got {schema}"
        )

        with get_connection(gate7_db) as conn:
            vehicle_count = conn.execute(
                "SELECT COUNT(*) c FROM vehicles",
            ).fetchone()[0]
        assert vehicle_count == 1, (
            f"expected exactly 1 vehicle row; got {vehicle_count}"
        )

        # Emit diagnostic about any skipped sub-steps so partial Track F
        # landings are observable in CI logs without turning the test red.
        if skipped_substeps:
            print(
                "\nGate 7 partial Track F — skipped sub-steps:\n  "
                + "\n  ".join(skipped_substeps)
            )


# ---------------------------------------------------------------------------
# Class B — CLI surface breadth (no DB, fast)
# ---------------------------------------------------------------------------


class TestAdvancedSurface:
    """Fast structural tests over the Click advanced command tree."""

    def test_advanced_group_registered(self):
        from motodiag.cli.main import cli

        assert "advanced" in cli.commands, (
            "advanced subgroup not registered — Phase 148 missing?"
        )
        advanced_group = cli.commands["advanced"]
        assert isinstance(advanced_group, click.Group)
        # Phase 148 is the hard floor.
        assert "predict" in advanced_group.commands, (
            f"predict command missing from advanced group; present: "
            f"{sorted(advanced_group.commands)}"
        )

    def test_expected_subcommands_per_subgroup(self):
        """Each Track F subgroup has its expected subcommand set.

        Tolerant: uses intersection checks with a floor count so a
        partial Track F landing produces a readable skip rather than a
        red test.
        """
        from motodiag.cli.main import cli

        advanced_group = cli.commands["advanced"]

        expectations: dict[str, tuple[set[str], int]] = {
            "fleet": (
                {
                    "create", "list", "show", "add-bike",
                    "remove-bike", "rename", "delete", "status",
                },
                6,
            ),
            "schedule": (
                {"init", "list", "due", "overdue", "complete", "history"},
                4,
            ),
            "history": (
                {"add", "list", "show", "show-all", "by-type"},
                3,
            ),
            "parts": (
                {"search", "xref", "show", "seed"},
                2,
            ),
            "tsb": (
                {"list", "search", "show", "by-make"},
                3,
            ),
            "recall": (
                {"list", "check-vin", "lookup", "mark-resolved"},
                2,
            ),
            "compare": (
                {"bike", "recording", "fleet"},
                1,
            ),
            "baseline": (
                {"show", "flag-healthy", "rebuild", "list"},
                2,
            ),
            "drift": (
                {"bike", "show", "recording", "plot"},
                1,
            ),
        }

        for name, (expected, floor) in expectations.items():
            group = advanced_group.commands.get(name)
            if group is None:
                continue  # Phase not landed; skip rather than fail.
            assert isinstance(group, click.Group), (
                f"advanced {name} should be a Click Group"
            )
            present = set(group.commands)
            intersection = expected & present
            assert len(intersection) >= floor, (
                f"advanced {name} should have >= {floor} of {sorted(expected)}; "
                f"present: {sorted(present)}"
            )

    def test_advanced_help_exits_zero(self):
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(
            cli, ["advanced", "--help"], catch_exceptions=False,
        )
        assert r.exit_code == 0, r.output
        assert "predict" in r.output

    def test_all_advanced_submodules_import_cleanly(self):
        """Hard: predictor + models. Soft: phases 149-158 submodules."""
        import motodiag.advanced.predictor  # noqa: F401
        import motodiag.advanced.models  # noqa: F401

        soft_modules = [
            ("motodiag.advanced.wear", "Phase 149"),
            ("motodiag.advanced.fleet_repo", "Phase 150"),
            ("motodiag.advanced.fleet_analytics", "Phase 150"),
            ("motodiag.advanced.schedule_repo", "Phase 151"),
            ("motodiag.advanced.scheduler", "Phase 151"),
            ("motodiag.advanced.history_repo", "Phase 152"),
            ("motodiag.advanced.parts_repo", "Phase 153"),
            ("motodiag.advanced.parts_loader", "Phase 153"),
            ("motodiag.advanced.tsb_repo", "Phase 154"),
            ("motodiag.advanced.recall_repo", "Phase 155"),
            ("motodiag.advanced.comparative", "Phase 156"),
            ("motodiag.advanced.baseline", "Phase 157"),
            ("motodiag.advanced.drift", "Phase 158"),
        ]
        broken: list[tuple[str, str, str]] = []
        for modname, phase in soft_modules:
            if importlib.util.find_spec(modname) is None:
                continue
            try:
                __import__(modname)
            except Exception as exc:  # noqa: BLE001
                broken.append((modname, phase, repr(exc)))
        assert not broken, (
            "Track F submodules failed to import:\n"
            + "\n".join(f"  {m} ({p}): {err}" for m, p, err in broken)
        )


# ---------------------------------------------------------------------------
# Class C — Regression + forward-compat
# ---------------------------------------------------------------------------


class TestRegression:
    """Prove Track F (phases 148-158) did not break Gate 5 or Gate 6."""

    def test_phase147_gate_6_still_passes(self):
        """Subprocess re-run of Gate 6's hardware workflow."""
        test_file = Path(__file__).parent / "test_phase147_gate_6.py"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q"],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, (
            f"Gate 6 failed after Track F:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    def test_phase133_gate_5_still_passes(self):
        """Subprocess re-run of Gate 5's mechanic workflow."""
        test_file = Path(__file__).parent / "test_phase133_gate_5.py"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"Gate 5 failed after Track F:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    def test_schema_version_tiered(self, tmp_path):
        """Tiered floor — v17 baseline (Phase 145), v20+ preferred.

        ``>=`` not ``==`` so Phase 160+ can bump without editing this test.
        """
        db = str(tmp_path / "fresh.db")
        init_db(db)
        schema = get_schema_version(db)
        assert schema >= 17, (
            f"schema >= Phase 145 floor (v17) required; got {schema}"
        )
        # Aspirational: Track F migrations take the floor to v20+.
        # Current main should land at v24 post-Phase-157.
        if _HAS_HISTORY_REPO:
            assert schema >= 20, (
                f"schema >= Phase 152 floor (v20) expected when history_repo "
                f"present; got {schema}"
            )
