"""Phase 357 — saved workflow runs: start, record, resume, finish, read back.

Row 357: "A migration adds tables for a workflow run and its per-item
results, tied to a bike or a work order, with the commands to start,
record and finish a run; a run can be resumed and read back." F165 closes
when a run and its per-item results are saved and read back:
`TestF165::test_a_run_and_its_results_are_saved_and_read_back`.

Every command goes through the real CLI root with `CliRunner` and typed
input, on a freshly migrated database under `tmp_path` (never
`data/motodiag.db`). What was saved is read with plain SQL, not through
the repository the commands use, so a command cannot agree with itself.

The operator's pick at Step 0 (A+, 2026-09-28): the powertrain comes from
`--powertrain` or the prompt; a bike stored with another is refused, and
`garage update --powertrain` corrects it.

Each assertion helper has a planted known-bad input it must fail on
(`TestTheHelpersFailOnPlantedInput`).
"""

from __future__ import annotations

import re
import sqlite3

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli as main_cli
from motodiag.cli.theme import reset_console
from motodiag.core.config import reset_settings
from motodiag.core.database import SCHEMA_VERSION, init_db
from motodiag.core.migrations import MIGRATIONS, rollback_to_version
from motodiag.workflows import get_checklist_items, get_template_by_slug

WIDE = 10000
PROMPT = re.compile(r"Result \((p/f|p/f/s)\):")
BRAKES = "brake_service_v1"          # 7 items; 3 and 4 optional; all powertrains
BRAKE_ANSWERS = ["p", "f", "s", "p", "p", "p", "p"]
WORDS = {"p": "pass", "f": "fail", "s": "skipped"}
MIGRATION = 73


# --- The door ---


def _cli(db_path, *args, answers=()):
    text = "".join(f"{a}\n" for a in answers)
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MOTODIAG_DB_PATH", db_path)
            mp.setenv("COLUMNS", str(WIDE))
            reset_settings()
            reset_console()
            return CliRunner().invoke(main_cli, list(args), input=text)
    finally:
        reset_settings()
        reset_console()


def _wf(db_path, *args, answers=()):
    return _cli(db_path, "workflow", *args, answers=answers)


def _sql(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        rows = conn.execute(sql, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


def _items(db_path, slug=BRAKES):
    return get_checklist_items(get_template_by_slug(slug, db_path)["id"], db_path)


def _runs(db_path):
    return _sql(db_path, "SELECT id, vehicle_id, work_order_id, powertrain, status, "
                         "finished_at FROM workflow_runs ORDER BY id")


def _saved(db_path, run_id):
    """{sequence_number: (result, diagnosis, notes)} as stored."""
    return {n: (r, d, notes) for n, r, d, notes in _sql(
        db_path, "SELECT sequence_number, result, diagnosis, notes "
                 "FROM workflow_run_items WHERE run_id = ?", (run_id,))}


def _run_id(output):
    m = re.search(r"Run #(\d+) · ", output)
    assert m, "no run number printed"
    return int(m.group(1))


# --- What must be true, as checks ---


def assert_saved(db_path, run_id, items, answers):
    """Exactly one row per item; each answered item holds its answer, a fail
    holds the item's diagnosis, and an unanswered item holds nothing."""
    saved = _saved(db_path, run_id)
    assert sorted(saved) == [i["sequence_number"] for i in items], f"rows {sorted(saved)}"
    for n, item in enumerate(items):
        result, diagnosis, _ = saved[item["sequence_number"]]
        want = WORDS[answers[n]] if n < len(answers) else None
        assert result == want, f"item {item['sequence_number']}: {result!r}, want {want!r}"
        want_d = item["diagnosis_if_fail"] if want == "fail" else None
        assert diagnosis == want_d, f"item {item['sequence_number']}: diagnosis {diagnosis!r}"


def assert_report(output, db_path, run_id):
    """One line per saved row, in order, with its result, and the counts."""
    rows = _sql(db_path, "SELECT sequence_number, title, required, result, diagnosis "
                         "FROM workflow_run_items WHERE run_id = ? "
                         "ORDER BY sequence_number", (run_id,))
    positions = []
    for n, title, required, result, diagnosis in rows:
        flag = "" if required else " (optional)"
        line = f"{n}. {title}{flag}: {result or 'unanswered'}"
        assert output.count(line) == 1, f"report line missing or repeated: {line!r}"
        positions.append(output.index(line))
        if diagnosis:
            assert f"Diagnosis: {diagnosis}" in output
    assert positions == sorted(positions), "report out of order"
    results = [r[3] for r in rows]
    counts = (f"{results.count('pass')} passed, {results.count('fail')} failed, "
              f"{results.count('skipped')} skipped, {results.count(None)} unanswered "
              f"of {len(rows)}")
    assert counts in output, f"counts missing: {counts!r}"


def assert_refused(result, message, db_path, runs_before=0):
    """Exit 1, the message, no item asked, and no run saved."""
    assert result.exit_code == 1, f"exit {result.exit_code}: {result.output}"
    assert message in result.output, f"missing {message!r}"
    assert not PROMPT.search(result.output), "an item was asked after a refusal"
    assert len(_runs(db_path)) == runs_before, "a refused start saved a run"


# --- Fixtures ---


@pytest.fixture
def garage(tmp_path):
    """A migrated database with two bikes, a shop, a customer, an open
    work order on the electric bike and a completed one."""
    path = str(tmp_path / "motodiag.db")
    init_db(path)
    _sql(path, "INSERT INTO vehicles (id, make, model, year, powertrain) "
               "VALUES (1, 'Zero', 'SR/F', 2021, 'electric')")
    _sql(path, "INSERT INTO vehicles (id, make, model, year, powertrain) "
               "VALUES (2, 'Harley-Davidson', 'Sportster', 2001, 'ice')")
    _sql(path, "INSERT INTO shops (id, name) VALUES (1, 'Shop')")
    # Customer 1 is the seeded "Unassigned".
    _sql(path, "INSERT INTO customers (id, owner_user_id, name) VALUES (2, 1, 'Rider')")
    _sql(path, "INSERT INTO work_orders (id, shop_id, vehicle_id, customer_id, title, status) "
               "VALUES (7, 1, 1, 2, 'Brakes', 'open')")
    _sql(path, "INSERT INTO work_orders (id, shop_id, vehicle_id, customer_id, title, status) "
               "VALUES (8, 1, 1, 2, 'Done', 'completed')")
    return path


def _start_full(db, *args, answers=BRAKE_ANSWERS, finish="y"):
    r = _wf(db, "start", BRAKES, *args, answers=[*answers, finish])
    assert r.exit_code == 0, r.output
    return r


# --- F165 ---


class TestF165:
    def test_a_run_and_its_results_are_saved_and_read_back(self, garage):
        r = _start_full(garage, "--bike", "sr/f-2021", "--powertrain", "electric")
        run_id = _run_id(r.output)
        assert _runs(garage) == [(run_id, 1, None, "electric", "complete",
                                  _runs(garage)[0][5])]
        assert _runs(garage)[0][5] is not None
        assert_saved(garage, run_id, _items(garage), BRAKE_ANSWERS)
        report = _wf(garage, "report", str(run_id))
        assert report.exit_code == 0, report.output
        assert_report(report.output, garage, run_id)
        assert "Status: complete" in report.output


# --- start: how a run is tied ---


class TestStart:
    def test_by_vehicle_id(self, garage):
        r = _start_full(garage, "--vehicle-id", "2", "--powertrain", "ice")
        assert _runs(garage)[0][1:3] == (2, None)
        assert_saved(garage, _run_id(r.output), _items(garage), BRAKE_ANSWERS)

    def test_by_work_order_takes_its_bike(self, garage):
        r = _start_full(garage, "--work-order", "7", "--powertrain", "electric")
        assert _runs(garage)[0][1:3] == (1, 7)
        assert "work order #7" in r.output

    def test_a_work_order_and_its_own_bike_agree(self, garage):
        _start_full(garage, "--work-order", "7", "--vehicle-id", "1", "--powertrain", "electric")
        assert _runs(garage)[0][1:3] == (1, 7)

    def test_a_work_order_and_another_bike_are_refused(self, garage):
        r = _wf(garage, "start", BRAKES, "--work-order", "7", "--vehicle-id", "2",
                "--powertrain", "ice")
        assert_refused(r, "Work order #7 is for bike #1, not bike #2.", garage)

    def test_neither_bike_nor_work_order_is_refused(self, garage):
        r = _wf(garage, "start", BRAKES, "--powertrain", "ice")
        assert_refused(r, "A saved run is tied to a bike or a work order", garage)

    def test_an_unknown_bike_is_refused(self, garage):
        assert_refused(_wf(garage, "start", BRAKES, "--vehicle-id", "99", "--powertrain", "ice"),
                       "No bike with id 99", garage)
        assert_refused(_wf(garage, "start", BRAKES, "--bike", "nosuch", "--powertrain", "ice"),
                       "No bike matches 'nosuch'", garage)

    def test_an_unknown_or_closed_work_order_is_refused(self, garage):
        assert_refused(_wf(garage, "start", BRAKES, "--work-order", "99"),
                       "No work order #99.", garage)
        assert_refused(_wf(garage, "start", BRAKES, "--work-order", "8"),
                       "Work order #8 is completed", garage)

    def test_a_retired_template_is_refused(self, garage):
        r = _wf(garage, "start", "generic_ppi_v1", "--vehicle-id", "2", "--powertrain", "ice")
        assert_refused(r, "generic_ppi_v1: Retired.", garage)

    def test_an_unknown_slug_is_refused(self, garage):
        r = _wf(garage, "start", "no_such_v1", "--vehicle-id", "2", "--powertrain", "ice")
        assert_refused(r, "No workflow template with slug 'no_such_v1'.", garage)


# --- The powertrain (A+) ---


class TestThePowertrain:
    def test_asked_for_when_not_given(self, garage):
        r = _wf(garage, "start", BRAKES, "--vehicle-id", "2",
                answers=["ice", *BRAKE_ANSWERS, "y"])
        assert r.exit_code == 0, r.output
        assert "Powertrain" in r.output and _runs(garage)[0][3] == "ice"

    def test_an_uncovered_template_is_refused(self, garage):
        r = _wf(garage, "start", "valve_adjustment_v1", "--vehicle-id", "1",
                "--powertrain", "electric")
        assert_refused(r, "valve_adjustment_v1 covers ice, hybrid, not electric.", garage)

    def test_a_bike_stored_otherwise_is_refused_with_its_remedy(self, garage):
        r = _wf(garage, "start", BRAKES, "--bike", "sportster-2001", "--powertrain", "electric")
        assert_refused(r, "Bike #2 (2001 Harley-Davidson Sportster) is stored as ice, "
                          "not electric.", garage)
        assert ("motodiag garage update --bike 'sportster-2001' --powertrain electric"
                in r.output)

    def test_a_wrongly_stated_bike_is_caught_and_the_remedy_works(self, garage):
        """An electric bike stated as ice by mistake. Phase 360 closed F174, so
        the mistake is now a person's, not a default's; the run still refuses
        it, and the command the refusal names still fixes it."""
        added = _cli(garage, "garage", "add", "--make", "Energica", "--model", "Esse",
                     "--year", "2021", "--powertrain", "ice", "--engine-type", "unknown")
        assert added.exit_code == 0, added.output
        assert _sql(garage, "SELECT powertrain FROM vehicles WHERE model = 'Esse'") == [("ice",)]
        r = _wf(garage, "start", BRAKES, "--bike", "esse-2021", "--powertrain", "electric")
        assert_refused(r, "is stored as ice, not electric.", garage)
        fix = _cli(garage, "garage", "update", "--bike", "esse-2021", "--powertrain", "electric")
        assert fix.exit_code == 0, fix.output
        _start_full(garage, "--bike", "esse-2021", "--powertrain", "electric")
        assert _runs(garage)[0][3] == "electric"

    def test_garage_update_with_nothing_is_still_refused(self, garage):
        r = _cli(garage, "garage", "update", "--bike", "esse-2021")
        assert r.exit_code != 0
        r = _cli(garage, "garage", "update", "--bike", "sportster-2001")
        assert "Nothing to update" in r.output and "--powertrain" in r.output


# --- record, resume, finish ---


class TestResume:
    def test_a_run_left_part_way_is_saved_and_resumed(self, garage):
        items = _items(garage)
        first = _wf(garage, "start", BRAKES, "--vehicle-id", "1", "--powertrain", "electric",
                    answers=BRAKE_ANSWERS[:3])
        assert first.exit_code == 1
        run_id = _run_id(first.output)
        assert f"motodiag workflow resume {run_id}" in first.output
        assert_saved(garage, run_id, items, BRAKE_ANSWERS[:3])
        assert _runs(garage)[0][4] == "in_progress"

        second = _wf(garage, "resume", str(run_id), answers=[*BRAKE_ANSWERS[3:], "y"])
        assert second.exit_code == 0, second.output
        for item in items[:3]:
            heading = re.compile(rf"^{item['sequence_number']}\. {re.escape(item['title'])}",
                                 re.MULTILINE)
            assert not heading.search(second.output), f"item {item['sequence_number']} asked again"
        assert len(PROMPT.findall(second.output)) == 4
        assert_saved(garage, run_id, items, BRAKE_ANSWERS)
        assert _runs(garage)[0][4] == "complete"

    def test_a_finished_run_cannot_be_resumed(self, garage):
        run_id = _run_id(_start_full(garage, "--vehicle-id", "1", "--powertrain", "electric").output)
        r = _wf(garage, "resume", str(run_id))
        assert r.exit_code == 1 and f"Run #{run_id} is finished" in r.output

    def test_an_unknown_run_is_refused(self, garage):
        for verb in ("resume", "finish", "report"):
            r = _wf(garage, verb, "42")
            assert r.exit_code == 1 and "No saved run #42" in r.output, verb


class TestRecord:
    def _open_run(self, garage):
        r = _wf(garage, "start", BRAKES, "--vehicle-id", "1", "--powertrain", "electric")
        return _run_id(r.output)

    def test_one_item_is_recorded_with_notes(self, garage):
        run_id = self._open_run(garage)
        r = _wf(garage, "record", str(run_id), "2", "fail", "--notes", "pads at 2 mm")
        assert r.exit_code == 0, r.output
        item = _items(garage)[1]
        assert _saved(garage, run_id)[2] == ("fail", item["diagnosis_if_fail"], "pads at 2 mm")

    def test_an_answer_can_be_corrected_before_finish(self, garage):
        run_id = self._open_run(garage)
        _wf(garage, "record", str(run_id), "2", "fail")
        _wf(garage, "record", str(run_id), "2", "pass")
        assert _saved(garage, run_id)[2] == ("pass", None, None)

    def test_a_skip_on_a_required_item_is_refused(self, garage):
        run_id = self._open_run(garage)
        r = _wf(garage, "record", str(run_id), "1", "skip")
        assert r.exit_code == 1 and "required: pass or fail, not skip" in r.output
        assert _saved(garage, run_id)[1] == (None, None, None)

    def test_an_unknown_item_is_refused(self, garage):
        run_id = self._open_run(garage)
        r = _wf(garage, "record", str(run_id), "99", "pass")
        assert r.exit_code == 1 and f"Run #{run_id} has no item 99." in r.output

    def test_a_finished_run_is_read_only(self, garage):
        run_id = _run_id(_start_full(garage, "--vehicle-id", "1", "--powertrain", "electric").output)
        r = _wf(garage, "record", str(run_id), "1", "fail")
        assert r.exit_code == 1 and "is finished" in r.output
        assert _saved(garage, run_id)[1][0] == "pass"


class TestFinish:
    def test_refused_while_items_are_unanswered(self, garage):
        r = _wf(garage, "start", BRAKES, "--vehicle-id", "1", "--powertrain", "electric",
                answers=["p", "p"])
        run_id = _run_id(r.output)
        f = _wf(garage, "finish", str(run_id))
        assert f.exit_code == 1 and "unanswered items: 3, 4, 5, 6, 7." in f.output
        assert _runs(garage)[0][4] == "in_progress"

    def test_declined_at_the_end_then_finished_by_command(self, garage):
        r = _start_full(garage, "--vehicle-id", "1", "--powertrain", "electric", finish="n")
        run_id = _run_id(r.output)
        assert _runs(garage)[0][4:] == ("in_progress", None)
        f = _wf(garage, "finish", str(run_id))
        assert f.exit_code == 0, f.output
        assert _runs(garage)[0][4] == "complete"
        again = _wf(garage, "finish", str(run_id))
        assert again.exit_code == 1 and "already finished" in again.output

    def test_finished_by_record_then_finish(self, garage):
        r = _wf(garage, "start", BRAKES, "--vehicle-id", "1", "--powertrain", "electric")
        run_id = _run_id(r.output)
        for n, a in zip(range(1, 8), BRAKE_ANSWERS):
            assert _wf(garage, "record", str(run_id), str(n),
                       {"p": "pass", "f": "fail", "s": "skip"}[a]).exit_code == 0
        assert _wf(garage, "finish", str(run_id)).exit_code == 0
        assert_saved(garage, run_id, _items(garage), BRAKE_ANSWERS)


# --- read back ---


class TestReadBack:
    def test_runs_lists_newest_first_and_filters(self, garage):
        _start_full(garage, "--vehicle-id", "2", "--powertrain", "ice")
        _start_full(garage, "--work-order", "7", "--powertrain", "electric")
        r = _wf(garage, "runs")
        assert r.exit_code == 0
        lines = [ln for ln in r.output.splitlines() if ln.startswith("#")]
        assert [ln.split()[0] for ln in lines] == ["#2", "#1"]
        assert "work order #7" in lines[0] and "7/7 answered" in lines[0]
        def listed(output):
            return [ln.split()[0] for ln in output.splitlines() if ln.startswith("#")]
        assert listed(_wf(garage, "runs", "--bike", "sportster-2001").output) == ["#1"]
        assert listed(_wf(garage, "runs", "--work-order", "7").output) == ["#2"]

    def test_the_report_keeps_the_title_the_run_was_worked_under(self, garage):
        run_id = _run_id(_start_full(garage, "--vehicle-id", "1", "--powertrain", "electric").output)
        old = _items(garage)[0]["title"]
        _sql(garage, "UPDATE checklist_items SET title = 'Renamed later' WHERE id = ?",
             (_items(garage)[0]["id"],))
        report = _wf(garage, "report", str(run_id)).output
        assert f"1. {old}: pass" in report and "Renamed later" not in report

    def test_an_unfinished_run_reads_back_as_unanswered(self, garage):
        r = _wf(garage, "start", BRAKES, "--vehicle-id", "1", "--powertrain", "electric",
                answers=["p"])
        run_id = _run_id(r.output)
        report = _wf(garage, "report", str(run_id)).output
        assert_report(report, garage, run_id)
        assert "Status: in_progress" in report


# --- The migration ---


class TestMigration073:
    def test_the_head_is_073_or_later_and_equals_the_last_migration(self):
        assert SCHEMA_VERSION >= MIGRATION
        assert SCHEMA_VERSION == max(m.version for m in MIGRATIONS)

    def test_it_adds_two_tables_and_three_indexes(self, garage):
        names = {n for (n,) in _sql(garage, "SELECT name FROM sqlite_master")}
        assert {"workflow_runs", "workflow_run_items", "idx_workflow_runs_vehicle",
                "idx_workflow_runs_work_order", "idx_workflow_run_items_item"} <= names

    def test_rollback_peels_073_and_nothing_else(self, tmp_path):
        path = str(tmp_path / "rb.db")
        init_db(path)
        named = "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"
        before = {n for (n,) in _sql(path, named)}
        rollback_to_version(MIGRATION - 1, path)
        after = {n for (n,) in _sql(path, named)}
        mine = {"workflow_runs", "workflow_run_items", "idx_workflow_runs_vehicle",
                "idx_workflow_runs_work_order", "idx_workflow_run_items_item"}
        # Later migrations are peeled too; whatever they add is theirs.
        later = {m.version for m in MIGRATIONS if m.version > MIGRATION}
        assert not (after & mine)
        if not later:
            assert before - after == mine
        assert _sql(path, "SELECT MAX(version) FROM schema_version") == [(MIGRATION - 1,)]

    @pytest.mark.parametrize("sql", [
        "INSERT INTO workflow_runs (template_id, vehicle_id, powertrain) VALUES (1, 1, 'diesel')",
        "INSERT INTO workflow_runs (template_id, vehicle_id, powertrain, status) "
        "VALUES (1, 1, 'ice', 'complete')",
        "INSERT INTO workflow_runs (template_id, vehicle_id, powertrain) VALUES (1, 999, 'ice')",
    ])
    def test_the_run_table_refuses_a_bad_row(self, garage, sql):
        with pytest.raises(sqlite3.IntegrityError):
            _sql(garage, sql)

    @pytest.mark.parametrize("values", [
        "(1, 1, 'T', 1, 'skipped', CURRENT_TIMESTAMP, NULL)",    # skip on required
        "(1, 1, 'T', 0, 'pass', NULL, NULL)",                    # answer without a time
        "(1, 1, 'T', 0, 'pass', CURRENT_TIMESTAMP, 'd')",         # diagnosis on a pass
        "(1, 1, 'T', 0, 'maybe', CURRENT_TIMESTAMP, NULL)",       # not a result
    ])
    def test_the_item_table_refuses_a_bad_row(self, garage, values):
        _sql(garage, "INSERT INTO workflow_runs (id, template_id, vehicle_id, powertrain) "
                     "VALUES (1, 1, 1, 'electric')")
        with pytest.raises(sqlite3.IntegrityError):
            _sql(garage, "INSERT INTO workflow_run_items (run_id, sequence_number, title, "
                         "required, result, answered_at, diagnosis) VALUES " + values)

    def test_a_bike_with_a_saved_run_cannot_be_deleted(self, garage):
        _start_full(garage, "--vehicle-id", "2", "--powertrain", "ice")
        with pytest.raises(sqlite3.IntegrityError):
            _sql(garage, "DELETE FROM vehicles WHERE id = 2")


# --- Each helper fails on a planted input ---


class TestTheHelpersFailOnPlantedInput:
    @pytest.fixture
    def done(self, garage):
        r = _start_full(garage, "--vehicle-id", "1", "--powertrain", "electric")
        run_id = _run_id(r.output)
        return garage, run_id, _wf(garage, "report", str(run_id)).output

    def test_the_good_run_passes_every_helper(self, done):
        db, run_id, report = done
        assert_saved(db, run_id, _items(db), BRAKE_ANSWERS)
        assert_report(report, db, run_id)

    def test_assert_saved_fails_on_a_changed_answer(self, done):
        db, run_id, _ = done
        _sql(db, "UPDATE workflow_run_items SET result = 'pass', diagnosis = NULL "
                 "WHERE run_id = ? AND sequence_number = 2", (run_id,))
        with pytest.raises(AssertionError, match="item 2"):
            assert_saved(db, run_id, _items(db), BRAKE_ANSWERS)

    def test_assert_saved_fails_on_a_lost_diagnosis(self, done):
        db, run_id, _ = done
        _sql(db, "UPDATE workflow_run_items SET diagnosis = NULL "
                 "WHERE run_id = ? AND sequence_number = 2", (run_id,))
        with pytest.raises(AssertionError, match="diagnosis"):
            assert_saved(db, run_id, _items(db), BRAKE_ANSWERS)

    def test_assert_saved_fails_on_a_missing_row(self, done):
        db, run_id, _ = done
        _sql(db, "DELETE FROM workflow_run_items WHERE run_id = ? AND sequence_number = 7",
             (run_id,))
        with pytest.raises(AssertionError, match="rows"):
            assert_saved(db, run_id, _items(db), BRAKE_ANSWERS)

    def test_assert_report_fails_on_a_missing_line(self, done):
        db, run_id, report = done
        with pytest.raises(AssertionError, match="report line"):
            assert_report(report.replace("1. ", "1) ", 1), db, run_id)

    def test_assert_report_fails_on_wrong_counts(self, done):
        db, run_id, report = done
        with pytest.raises(AssertionError, match="counts"):
            assert_report(report.replace("5 passed", "6 passed"), db, run_id)

    def test_assert_refused_fails_when_a_run_was_saved(self, done):
        db, _, _ = done
        planted = type("R", (), {"exit_code": 1, "output": "refused"})()
        with pytest.raises(AssertionError, match="saved a run"):
            assert_refused(planted, "refused", db)

    def test_assert_refused_fails_when_an_item_was_asked(self, garage):
        planted = type("R", (), {"exit_code": 1, "output": "refused\n  Result (p/f): "})()
        with pytest.raises(AssertionError, match="asked"):
            assert_refused(planted, "refused", garage)
