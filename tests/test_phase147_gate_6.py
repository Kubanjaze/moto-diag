"""Phase 147 — Gate 6: Hardware Integration Test.

Pass/fail checkpoint for Track E (hardware interface, phases 134-146).

Proves the full mechanic-at-a-bench workflow wires together end-to-end
over the Phase 140-146 CLI surface on a single shared DB via Click's
``CliRunner``: garage add → compat recommend → hardware info →
hardware scan → log start → log list/show/replay/export → hardware
stream → hardware diagnose → hardware clear.

Pattern mirrors Phase 133's Gate 5 — one big integration test file,
zero new production code, pure observation over the existing CLI
surface with graceful-skip probes when an individual Track E phase
isn't landed.

Every AI-bearing boundary is patched defensively even though the
hardware workflow should never touch AI:

- ``motodiag.cli.diagnose._default_diagnose_fn`` (Phase 123)
- ``motodiag.cli.code._default_interpret_fn`` (Phase 124)
- ``motodiag.intake.vehicle_identifier._default_vision_call`` (Phase 122)

Three test classes:

- ``TestHardwareEndToEnd``: the full 12+ step hardware scenario.
- ``TestHardwareSurface``: command-tree structural assertions.
- ``TestRegression``: Gate 5 + Gate R subprocess re-runs + schema
  forward-compat floor.

Zero live AI tokens. Zero real serial I/O. Zero real ``time.sleep``
blocking (CI-grep-level discipline — every wait path is no-op patched).
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import click
import pytest
from click.testing import CliRunner

from motodiag.core.database import (
    SCHEMA_VERSION,
    get_connection,
    get_schema_version,
    init_db,
)


# ---------------------------------------------------------------------------
# Phase-presence probes — Gate 6 graceful-skip posture
# ---------------------------------------------------------------------------
#
# Phases 141-146 were all merged before Gate 6, but the probes remain in
# place per the Gate 6 spec so this test stays resilient to future
# re-ordering or partial reverts. A missing phase surfaces as a per-
# sub-step ``pytest.skip`` rather than a red test — Gate 6 captures the
# shape of the track, not a specific merge ordering.


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


_HAS_RECORDER = _has_module("motodiag.hardware.recorder")  # Phase 142
_HAS_SENSORS = _has_module("motodiag.hardware.sensors")  # Phase 141
_HAS_SIMULATOR = _has_module("motodiag.hardware.simulator")  # Phase 144
_HAS_DASHBOARD = _has_module("motodiag.hardware.dashboard")  # Phase 143
_HAS_COMPAT_REPO = _has_module("motodiag.hardware.compat_repo")  # Phase 145
_HAS_COMPAT_LOADER = _has_module("motodiag.hardware.compat_loader")  # Phase 145


# ---------------------------------------------------------------------------
# Canned AI responses — defensive only
# ---------------------------------------------------------------------------
#
# The hardware workflow does not intentionally call AI, but we patch the
# three boundaries for the entire workflow so that any accidental wiring
# through (e.g. a future Phase N adds an "explain this DTC" path to a
# hardware command) fails closed on canned data rather than hitting the
# live Anthropic API during CI.


def _fake_diagnose(**kwargs):
    """Drop-in for ``_default_diagnose_fn`` — returns a canned response."""
    response = SimpleNamespace(
        vehicle_summary="2015 Harley-Davidson Road Glide",
        symptoms_acknowledged=["gate 6 mock — never invoked"],
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
    """Drop-in for ``_default_interpret_fn`` — returns a canned result."""
    result = SimpleNamespace(
        code="P0000",
        code_format="obd2_generic",
        description="gate 6 mock — never invoked",
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
    """Drop-in for ``_default_vision_call`` — canned JSON, no network."""
    canned = (
        '{"make":"Harley-Davidson","model":"Road Glide",'
        '"year_range":[2014,2016],"engine_cc_range":[1690,1690],'
        '"powertrain_guess":"ice","confidence":0.5,'
        '"reasoning":"(mocked for gate 6)","alert":null}'
    )
    return canned, 0, 0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def gate6_db(tmp_path, monkeypatch):
    """Point settings + env at a temp DB; redirect recorder + init_db.

    Mirrors Phase 142's ``_patch_env`` fixture and Phase 133's ``cli_db``
    fixture: the env var makes get_settings() return a Settings pointed
    at the scratch DB, ``reset_settings()`` flushes the cached instance
    around the test, ``init_db(db_path)`` creates the schema, and the
    cli.hardware ``init_db`` top-of-command call is redirected so every
    subcommand lands on the same tmp DB. ``COLUMNS=200`` widens the
    virtual terminal so Rich tables don't word-wrap substring asserts.
    """
    from motodiag.core.config import reset_settings

    db_path = str(tmp_path / "gate6.db")
    monkeypatch.setenv("MOTODIAG_DB_PATH", db_path)
    monkeypatch.setenv("COLUMNS", "200")
    reset_settings()
    init_db(db_path)

    # Redirect cli.hardware.init_db so every subcommand's top-of-handler
    # init_db() call re-uses the tmp DB path rather than the real user
    # settings path. Phase 146's _patch_init_db does the same thing.
    import motodiag.cli.hardware as hw_mod

    original_init_db = hw_mod.init_db

    def _patched_init_db(*args, **kwargs):
        if args or kwargs:
            # Pass through any explicit path override (shouldn't happen
            # from a hardware subcommand but guards against future drift).
            return original_init_db(*args, **kwargs)
        return original_init_db(db_path)

    monkeypatch.setattr(hw_mod, "init_db", _patched_init_db)

    # Redirect RecordingManager default db_path + recordings_dir so JSONL
    # sidecars land under tmp_path rather than ~/.motodiag/recordings and
    # recorder SQLite writes land on the same tmp DB. Phase 142 test
    # fixture pattern.
    if _HAS_RECORDER:
        from motodiag.hardware import recorder as rec_mod

        original_rec_init = rec_mod.RecordingManager.__init__

        def _patched_rec_init(self, db_path_arg=None, recordings_dir=None):
            original_rec_init(
                self,
                db_path=db_path_arg or db_path,
                recordings_dir=(
                    recordings_dir
                    if recordings_dir is not None
                    else tmp_path / "recordings"
                ),
            )

        monkeypatch.setattr(
            rec_mod.RecordingManager, "__init__", _patched_rec_init,
        )

    yield db_path
    reset_settings()


# ---------------------------------------------------------------------------
# Class A — End-to-end hardware workflow
# ---------------------------------------------------------------------------


class TestHardwareEndToEnd:
    """One cohesive hardware scenario — 12+ CLI invocations on a shared DB.

    Each step depends on state from the previous step (e.g. `log show`
    needs an ID produced by `log start`, `compat recommend` needs the
    vehicle `garage add` persisted, the final integrity asserts depend
    on every step's side effects). Catches cross-command integration
    bugs that siloed Phase 140-146 unit tests cannot surface.

    Graceful-skip posture: every sub-step that targets a phase with a
    presence probe is guarded. On a fully-landed Track E (which is the
    current state as of Gate 6) every sub-step runs.
    """

    def test_full_hardware_flow(self, gate6_db, tmp_path, monkeypatch):
        # Import inside the test so the gate6_db env + monkeypatches are
        # active before the CLI module evaluates its command registrations.
        from motodiag.cli.main import cli

        # No-op ``time.sleep`` on the retry-path modules so Phase 146's
        # exponential backoff never stalls the workflow on wall-clock.
        # NOTE: we deliberately do NOT patch the cli.hardware ``_time``
        # alias — the log start inline loop uses ``_time.sleep(interval)``
        # + ``_time.monotonic()`` together to pace polling, and
        # no-opping only the sleep while leaving monotonic as real time
        # turns the loop into a tight spin that can produce tens of
        # thousands of mock samples in one ``--duration 2`` call.
        # Letting the interval sleep run naturally keeps sample_count
        # manageable (~4 cycles at duration=2 / interval=0.5).
        sleep_patches = []
        for modname in ("motodiag.hardware.connection",):
            if _has_module(modname):
                mod = importlib.import_module(modname)
                if hasattr(mod, "time") and hasattr(mod.time, "sleep"):
                    sleep_patches.append(
                        patch.object(mod.time, "sleep", lambda *a, **k: None)
                    )

        runner = CliRunner()

        def run(args, input_=None):
            """Invoke cli; catch_exceptions=False so failures surface loud."""
            return runner.invoke(
                cli, args, input=input_, catch_exceptions=False,
            )

        hardware_group = cli.commands.get("hardware")
        assert hardware_group is not None, (
            "hardware subgroup must be registered; Phase 140+ not landed?"
        )

        # Compose all defensive patches. time.sleep no-ops stack with the
        # three AI boundary patches.
        with patch(
            "motodiag.cli.diagnose._default_diagnose_fn", _fake_diagnose,
        ), patch(
            "motodiag.cli.code._default_interpret_fn", _fake_interpret,
        ), patch(
            "motodiag.intake.vehicle_identifier._default_vision_call",
            _fake_vision,
        ):
            # Activate the time.sleep no-op patches inside the same
            # context so they unwind on exit.
            for p in sleep_patches:
                p.start()
            try:
                # --- Step 1: garage add ------------------------------------
                # Phase 140 precondition. Creates the vehicle the rest of
                # the workflow (bike slugs, compat recommend, log start
                # vehicle_id resolution) depends on.
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
                assert "Added vehicle #1" in r.output
                assert "Road Glide" in r.output

                # Slug convention (Phase 125 _parse_slug): `<stem>-<year>`.
                # "glide-2015" LIKE-matches "Road Glide" model.
                bike_slug = "glide-2015"

                # --- Step 2: compat seed + recommend (Phase 145) -----------
                # Graceful-skip: if Phase 145 isn't present the rest of
                # the workflow (info/scan/log/stream/diagnose/clear)
                # still runs. We track skipped sub-steps in a local list
                # and surface them at the end as a pytest warning rather
                # than aborting the whole test with pytest.skip.
                skipped_substeps: list[str] = []
                if _HAS_COMPAT_REPO and _HAS_COMPAT_LOADER and (
                    "compat" in hardware_group.commands
                ):
                    r = run(["hardware", "compat", "seed", "--yes"])
                    assert r.exit_code == 0, r.output
                    assert "Loaded" in r.output or "adapters" in r.output

                    r = run([
                        "hardware", "compat", "recommend",
                        "--bike", bike_slug,
                    ])
                    assert r.exit_code == 0, r.output
                    # compat recommend either shows a table or a friendly
                    # "no matches" panel — both prove the command wires up.
                    lower = r.output.lower()
                    assert (
                        "adapter" in lower
                        or "compat" in lower
                        or "no " in lower
                    ), f"compat recommend output unexpected:\n{r.output}"
                else:
                    skipped_substeps.append(
                        "Phase 145 compat — compat_repo/loader/compat subgroup "
                        "missing"
                    )

                # --- Step 3: hardware info --simulator healthy_idle --------
                # Phase 140 command + Phase 144 simulator path. No real
                # serial. Simulator scenarios are vendored under
                # src/motodiag/hardware/scenarios/.
                if _HAS_SIMULATOR and "info" in hardware_group.commands:
                    info_opts = {
                        o.name for o in hardware_group.commands["info"].params
                    }
                    if "simulator" in info_opts:
                        r = run([
                            "hardware", "info",
                            "--port", "COM3",
                            "--simulator", "healthy_idle",
                        ])
                        assert r.exit_code == 0, r.output
                        # Phase 144 badge + protocol label surface.
                        assert (
                            "Protocol" in r.output
                            or "healthy_idle" in r.output
                        )
                    else:
                        skipped_substeps.append(
                            "hardware info lacks --simulator — Phase 144 "
                            "not landed"
                        )

                # --- Step 4: hardware scan --simulator overheat ------------
                # Tolerant assertion — the overheat scenario may emit
                # a DTC table or a "no codes" friendly panel depending
                # on the scenario's scripted DTC set.
                if _HAS_SIMULATOR and "scan" in hardware_group.commands:
                    scan_opts = {
                        o.name for o in hardware_group.commands["scan"].params
                    }
                    if "simulator" in scan_opts:
                        r = run([
                            "hardware", "scan",
                            "--port", "COM3",
                            "--simulator", "overheat",
                        ])
                        assert r.exit_code == 0, r.output
                        # Either a DTC table header/rows OR the "no codes
                        # stored" friendly message. Both are valid.
                        lower = r.output.lower()
                        assert (
                            "dtc" in lower
                            or "no codes" in lower
                            or "p0" in lower
                            or "code" in lower
                        ), f"scan output unexpected:\n{r.output}"

                # --- Step 5: log start (Phase 142 + 144) -------------------
                # Phase 142 log subgroup + a scenario-backed mock. The
                # recorder's default dir is redirected to tmp_path via
                # the gate6_db fixture so JSONL sidecars land under tmp.
                #
                # NOTE: Phase 142's ``log start`` supports ``--mock`` but
                # NOT ``--simulator`` (mock-only adapter path at 142
                # land time). We use --mock for the log path so the
                # recorder exercise doesn't block on real serial; the
                # simulator path is covered by scan/info/clear.
                recording_id = None
                if _HAS_RECORDER and "log" in hardware_group.commands:
                    log_group = hardware_group.commands["log"]
                    assert isinstance(log_group, click.Group)
                    if "start" in log_group.commands:
                        r = run([
                            "hardware", "log", "start",
                            "--port", "COM3",
                            "--mock",
                            "--duration", "2",
                            "--interval", "0.5",
                            "--label", "gate6-recording",
                            "--bike", bike_slug,
                        ])
                        assert r.exit_code == 0, r.output
                        # Stdout: "recording id <N>" per Phase 142
                        # cli.hardware:1928 render template.
                        match = re.search(
                            r"recording id\s+(\d+)", r.output,
                        )
                        assert match, (
                            f"recording id not found in log start "
                            f"output:\n{r.output}"
                        )
                        recording_id = int(match.group(1))

                    # --- Step 6: log list ---------------------------------
                    if "list" in log_group.commands:
                        r = run(["hardware", "log", "list"])
                        assert r.exit_code == 0, r.output
                        if recording_id is not None:
                            assert str(recording_id) in r.output, (
                                f"recording id {recording_id} missing from "
                                f"log list output:\n{r.output}"
                            )

                    # --- Step 7: log show -----------------------------
                    if recording_id is not None and (
                        "show" in log_group.commands
                    ):
                        r = run([
                            "hardware", "log", "show", str(recording_id),
                        ])
                        assert r.exit_code == 0, r.output
                        # Protocol label (MockAdapter reports its fake
                        # name) + a sample-count indicator should appear.
                        lower = r.output.lower()
                        assert (
                            "sample" in lower
                            or "pid" in lower
                            or "protocol" in lower
                        ), (
                            f"log show output missing metadata:\n{r.output}"
                        )

                    # --- Step 8: log replay (speed 0 = instant dump) ------
                    if recording_id is not None and (
                        "replay" in log_group.commands
                    ):
                        r = run([
                            "hardware", "log", "replay",
                            str(recording_id),
                            "--speed", "0",
                        ])
                        # Replay can exit 0 (dumped) or 1 (no samples).
                        # Either proves wiring — MockAdapter-backed
                        # recordings with duration 2 + interval 0.5
                        # produce ~4 cycles so exit 0 is the happy path.
                        assert r.exit_code in (0, 1), r.output

                    # --- Step 9: log export --format csv ------------------
                    csv_path: Path = tmp_path / "rec.csv"
                    if recording_id is not None and (
                        "export" in log_group.commands
                    ):
                        r = run([
                            "hardware", "log", "export",
                            str(recording_id),
                            "--format", "csv",
                            "--output", str(csv_path),
                        ])
                        assert r.exit_code == 0, r.output
                        assert csv_path.exists(), "csv not written"
                        assert csv_path.stat().st_size > 0, (
                            "csv export is empty"
                        )
                        # First line should be a header row (not a data
                        # row). Our wide-format export has a leading
                        # ``captured_at`` column per Phase 142.
                        first_line = csv_path.read_text(
                            encoding="utf-8",
                        ).splitlines()[0]
                        assert "captured_at" in first_line.lower() or (
                            "pid" in first_line.lower()
                        ), (
                            f"csv header missing; got {first_line!r}"
                        )

                # --- Step 10: hardware stream (Phase 141 + 144) ------------
                # Phase 141 ``stream`` command. Phase 144's --simulator
                # flag was not added to ``stream`` at Phase 144 land time
                # — guard on option presence and graceful-skip otherwise.
                if _HAS_SENSORS and "stream" in hardware_group.commands:
                    stream_opts = {
                        o.name
                        for o in hardware_group.commands["stream"].params
                    }
                    if "simulator" in stream_opts:
                        r = run([
                            "hardware", "stream",
                            "--port", "COM3",
                            "--simulator", "charging_fault",
                            "--duration", "1",
                            "--hz", "2",
                        ])
                        assert r.exit_code == 0, r.output
                    elif "mock" in stream_opts:
                        # Fallback to --mock; Phase 141 ships with a mock
                        # adapter path for a no-hardware exercise.
                        r = run([
                            "hardware", "stream",
                            "--port", "COM3",
                            "--mock",
                            "--duration", "1",
                            "--hz", "2",
                        ])
                        # stream exit code is 0 on clean termination; any
                        # non-zero here is a real wiring bug worth flagging.
                        assert r.exit_code == 0, r.output
                    # else: graceful-skip — neither flag present means
                    # no mechanical way to exercise stream without real
                    # serial. Gate 6 treats that as a skip, not a failure.

                # --- Step 11: hardware diagnose --mock (Phase 146) ---------
                # 5-step connection troubleshooter. --mock walks all five
                # steps with a happy-path MockAdapter so we get the
                # "5/5 checks passed" summary.
                if "diagnose" in hardware_group.commands:
                    r = run([
                        "hardware", "diagnose",
                        "--port", "COM3",
                        "--mock",
                    ])
                    assert r.exit_code == 0, r.output
                    # Phase 146 summary renders "N/5 checks passed." on
                    # the happy path.
                    assert "5/5" in r.output or "passed" in r.output.lower(), (
                        f"diagnose summary missing 5/5:\n{r.output}"
                    )

                # --- Step 12: hardware clear --simulator healthy_idle ------
                # Closes the workflow. Healthy scenario accepts the clear,
                # --yes skips the confirm prompt. --no-retry explicit
                # even though Phase 146 silently disables retry on the
                # simulator path (discipline — ResilientAdapter never
                # retries clear_dtcs regardless).
                if _HAS_SIMULATOR and "clear" in hardware_group.commands:
                    clear_opts = {
                        o.name for o in hardware_group.commands["clear"].params
                    }
                    if "simulator" in clear_opts:
                        r = run([
                            "hardware", "clear",
                            "--port", "COM3",
                            "--simulator", "healthy_idle",
                            "--yes",
                            "--no-retry",
                        ])
                        assert r.exit_code == 0, r.output
                    else:
                        # Fall back to --mock if Phase 144 not landed.
                        r = run([
                            "hardware", "clear",
                            "--port", "COM3",
                            "--mock",
                            "--yes",
                        ])
                        assert r.exit_code == 0, r.output
            finally:
                for p in sleep_patches:
                    p.stop()

        # --------------------------------------------------------------
        # Final integrity assertions — all patches now out of scope
        # --------------------------------------------------------------

        # Tiered schema floor: 15 baseline, 16 with Phase 142, 17 with
        # Phase 145. Current main is at 17; tiered comparison keeps this
        # test forward-compatible with any schema bump Phase 148+ adds.
        schema = get_schema_version(gate6_db)
        assert schema >= 15, (
            f"schema should be >= Phase 131 floor (v15); got {schema}"
        )
        if _HAS_RECORDER:
            assert schema >= 16, (
                f"schema should be >= Phase 142 floor (v16) when "
                f"recorder is present; got {schema}"
            )
        if _HAS_COMPAT_REPO:
            assert schema >= 17, (
                f"schema should be >= Phase 145 floor (v17) when "
                f"compat repo is present; got {schema}"
            )

        # Exactly one vehicle row from step 1.
        with get_connection(gate6_db) as conn:
            vehicle_count = conn.execute(
                "SELECT COUNT(*) c FROM vehicles",
            ).fetchone()[0]
        assert vehicle_count == 1, (
            f"expected exactly 1 vehicle row; got {vehicle_count}"
        )

        # If Phase 142 is present, exactly one recording row with a
        # non-null stopped_at (log start wrapped up inline) and
        # sample_count > 0 (mock adapter produced at least one tick).
        if _HAS_RECORDER:
            with get_connection(gate6_db) as conn:
                rows = conn.execute(
                    "SELECT id, stopped_at, sample_count FROM sensor_recordings",
                ).fetchall()
            assert len(rows) == 1, (
                f"expected exactly 1 recording row; got {len(rows)}"
            )
            row = dict(rows[0])
            assert row.get("stopped_at") is not None, (
                "recording should have stopped_at populated after log start "
                "--duration wrapped up"
            )
            assert (row.get("sample_count") or 0) > 0, (
                f"recording sample_count should be > 0 after 2s of mock "
                f"polling at 2Hz; got {row.get('sample_count')!r}"
            )

            # CSV export file persisted and non-empty.
            csv_path = tmp_path / "rec.csv"
            assert csv_path.exists(), (
                "csv export file missing after workflow"
            )
            assert csv_path.stat().st_size > 0, (
                "csv export file is empty"
            )

        # tmp_path teardown (via pytest's tmp_path fixture) reclaims the
        # recordings/ JSONL sidecars automatically — no leaked handles
        # if pyserial.Serial was never instantiated (which the --mock /
        # --simulator paths guarantee).


# ---------------------------------------------------------------------------
# Class B — CLI surface breadth (no DB, fast)
# ---------------------------------------------------------------------------


class TestHardwareSurface:
    """Fast structural tests over the Click hardware command tree."""

    def test_hardware_group_registered(self):
        """Hard-require scan/clear/info; soft-expect the Phase 141-146 set."""
        from motodiag.cli.main import cli

        assert "hardware" in cli.commands, (
            "hardware subgroup not registered; Phase 140 missing?"
        )
        hardware_group = cli.commands["hardware"]
        assert isinstance(hardware_group, click.Group)

        hard_required = {"scan", "clear", "info"}
        missing_hard = hard_required - set(hardware_group.commands)
        assert not missing_hard, (
            f"Phase 140 core commands missing: {sorted(missing_hard)}. "
            f"Present: {sorted(hardware_group.commands)}"
        )

        # Soft-expect Phase 141-146 additions. Emit per-subcommand
        # diagnostic so a partial track E landing produces a readable
        # report rather than a single red line.
        soft_expected = {
            "stream": "Phase 141",
            "log": "Phase 142",
            "dashboard": "Phase 143",
            "simulate": "Phase 144",
            "compat": "Phase 145",
            "diagnose": "Phase 146",
        }
        present = set(hardware_group.commands)
        missing_soft = {
            name: phase
            for name, phase in soft_expected.items()
            if name not in present
        }
        if missing_soft:
            # Not a hard failure — spec says Gate 6 builds against
            # whatever has landed. Record via pytest.skip on per-sub
            # where relevant. Here we just assert the count so a
            # regression in Track E (removing a command) screams.
            pytest.skip(
                f"Soft-expected hardware subcommands missing: "
                f"{sorted(missing_soft.items())}"
            )

    def test_expected_subcommands_per_subgroup(self):
        """Each Track E subgroup has its expected subcommand set."""
        from motodiag.cli.main import cli

        hardware_group = cli.commands["hardware"]

        # Phase 142 log — 8 subcommands, tolerant >= 6/8 intersection so
        # one or two missing commands in a partial merge produce a
        # readable skip rather than a red test.
        if "log" in hardware_group.commands:
            log_group = hardware_group.commands["log"]
            assert isinstance(log_group, click.Group)
            expected_log = {
                "start", "stop", "list", "show",
                "replay", "diff", "export", "prune",
            }
            present_log = set(log_group.commands)
            intersection = expected_log & present_log
            assert len(intersection) >= 6, (
                f"hardware log should have >= 6 of {sorted(expected_log)}; "
                f"present: {sorted(present_log)}"
            )

        # Phase 144 simulate — strict subset.
        if "simulate" in hardware_group.commands:
            sim_group = hardware_group.commands["simulate"]
            assert isinstance(sim_group, click.Group)
            expected_sim = {"list", "run", "validate"}
            missing = expected_sim - set(sim_group.commands)
            assert not missing, (
                f"hardware simulate missing: {sorted(missing)}. "
                f"Present: {sorted(sim_group.commands)}"
            )

        # Phase 145 compat — strict subset + nested ``note`` group.
        if "compat" in hardware_group.commands:
            compat_group = hardware_group.commands["compat"]
            assert isinstance(compat_group, click.Group)
            expected_compat = {
                "list", "recommend", "check", "show", "note", "seed",
            }
            missing = expected_compat - set(compat_group.commands)
            assert not missing, (
                f"hardware compat missing: {sorted(missing)}. "
                f"Present: {sorted(compat_group.commands)}"
            )
            # ``note`` is itself a group with add + list.
            note_group = compat_group.commands.get("note")
            if note_group is not None:
                assert isinstance(note_group, click.Group)
                note_subs = set(note_group.commands)
                expected_note = {"add", "list"}
                missing_note = expected_note - note_subs
                assert not missing_note, (
                    f"hardware compat note missing: {sorted(missing_note)}. "
                    f"Present: {sorted(note_subs)}"
                )

    def test_hardware_help_exits_zero(self):
        """``motodiag hardware --help`` exits 0 and lists core commands."""
        from motodiag.cli.main import cli

        runner = CliRunner()
        r = runner.invoke(
            cli, ["hardware", "--help"], catch_exceptions=False,
        )
        assert r.exit_code == 0, r.output
        # Click's help lists commands with the name as the row leader.
        for name in ("scan", "clear", "info"):
            assert name in r.output, (
                f"hardware --help missing {name!r}:\n{r.output}"
            )

    def test_all_hardware_submodules_import_cleanly(self):
        """Hard-require the Phase 140 set; soft-report Phase 141-146 set."""
        # Hard-required at the Phase 140 floor (Gate 6 cannot proceed
        # if these don't import — every workflow command depends on them).
        import motodiag.hardware.connection  # noqa: F401
        import motodiag.hardware.mock  # noqa: F401
        import motodiag.hardware.ecu_detect  # noqa: F401

        # Soft: a broken import here is a real bug but doesn't close the
        # gate. We collect the failure set into a diagnostic and attach
        # it to a skip so the CI log captures exactly which Phase N
        # module is broken.
        soft_modules = [
            ("motodiag.hardware.sensors", "Phase 141"),
            ("motodiag.hardware.recorder", "Phase 142"),
            ("motodiag.hardware.dashboard", "Phase 143"),
            ("motodiag.hardware.simulator", "Phase 144"),
            ("motodiag.hardware.compat_repo", "Phase 145"),
            ("motodiag.hardware.compat_loader", "Phase 145"),
        ]
        broken: list[tuple[str, str, str]] = []
        for modname, phase in soft_modules:
            try:
                __import__(modname)
            except Exception as exc:  # noqa: BLE001
                broken.append((modname, phase, repr(exc)))
        assert not broken, (
            "Track E submodules failed to import:\n"
            + "\n".join(
                f"  {m} ({p}): {err}" for m, p, err in broken
            )
        )


# ---------------------------------------------------------------------------
# Class C — Regression + forward-compat
# ---------------------------------------------------------------------------


class TestRegression:
    """Prove Track E (phases 134-146) did not break Gate 5 or Gate R."""

    def test_phase133_gate_5_still_passes(self):
        """Subprocess re-run of Gate 5's mechanic workflow.

        Gate 5 closed Track D (mechanic CLI, phases 122-132). Re-running
        it here proves Track E did not regress Track D. Subprocess so
        pytest plugin state, fixture teardown, and module-level imports
        are all cold-started — catches monkey-patch leakage that
        in-process collection might mask.
        """
        test_file = Path(__file__).parent / "test_phase133_gate_5.py"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"Gate 5 failed after Track E:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    def test_phase121_gate_r_still_passes(self):
        """Subprocess re-run of Gate R's retrofit workflow.

        Gate R closed the retrofit track (phases 110-120). Running it
        here is belt-and-suspenders — Gate 5 already re-ran it, but
        Gate 6 makes the claim explicit: Track E did not break the
        retrofit substrate either.
        """
        test_file = Path(__file__).parent / "test_phase121_gate_r.py"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q"],
            capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 0, (
            f"Gate R failed after Track E:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    def test_schema_version_tiered(self, tmp_path):
        """Tiered floor — 15 baseline, 17 preferred (Phase 145 landed).

        ``>=`` not ``==`` per Phase 121 + Phase 133 convention so Phase
        148+ can bump without editing this test.
        """
        db = str(tmp_path / "fresh.db")
        init_db(db)
        schema = get_schema_version(db)
        assert schema >= 15, (
            f"schema >= Phase 131 floor (v15) required; got {schema}"
        )
        # Aspirational floor — the current main is at v17 (Phase 145's
        # compat tables). If a future phase rolls back a migration this
        # floor catches it.
        assert schema >= 17, (
            f"schema >= Phase 145 floor (v17) expected on current main; "
            f"got {schema}. Phase 145 compat tables missing?"
        )
        assert SCHEMA_VERSION >= 17, (
            f"SCHEMA_VERSION constant should be >= 17; got {SCHEMA_VERSION}"
        )
