"""Phase 356 — `motodiag workflow run <slug>`: a template's checklist through
Phase 82's step engine, one item at a time, nothing saved.

Every run is driven through the real CLI root with `CliRunner` and typed
input, against a freshly migrated database under `tmp_path` (never
`data/motodiag.db`). What each run should print is taken from the
repository's rows, not from the command, so the command cannot agree with
itself.

The operator's pick at Step 0 (option A, 2026-09-28): the run takes
`--powertrain` or asks for one, and refuses a template that does not
cover it.

Each assertion helper has a planted known-bad input it must fail on
(`TestTheHelpersFailOnPlantedOutput`), so a helper that passes everything
is caught.
"""

from __future__ import annotations

import re
import sqlite3
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from motodiag.cli.main import cli as main_cli
from motodiag.cli.theme import reset_console
from motodiag.core.config import reset_settings
from motodiag.core.database import init_db
from motodiag.engine.workflows import (
    DiagnosticWorkflow, StepResult, WorkflowStep,
)
from motodiag.workflows import (
    get_checklist_items, get_template_by_slug, list_templates,
)
from motodiag.workflows.runner import checklist_workflow

POWERTRAINS = ("ice", "electric", "hybrid")
RETIRED = ("generic_ppi_v1", "generic_winterization_v1")
# Wide enough that no heading, prompt or summary line wraps.
WIDE = 10000


# --- The door ---


def _run(db_path, *args, answers=(), columns=WIDE):
    """`motodiag workflow run <args>` with `answers` typed, one per line."""
    text = "".join(f"{a}\n" for a in answers)
    try:
        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("MOTODIAG_DB_PATH", db_path)
            mp.setenv("COLUMNS", str(columns))
            reset_settings()
            reset_console()
            return CliRunner().invoke(main_cli, ["workflow", "run", *args], input=text)
    finally:
        reset_settings()
        reset_console()


def _items(db_path, slug):
    return get_checklist_items(get_template_by_slug(slug, db_path)["id"], db_path)


def _execute(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    conn.execute(sql, params)
    conn.commit()
    conn.close()


def _dump(db_path):
    """Every table's rows, for comparing a database before and after."""
    conn = sqlite3.connect(db_path)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {t: conn.execute(f'SELECT * FROM "{t}" ORDER BY rowid').fetchall()
                for t in tables}
    finally:
        conn.close()


# --- What a run must print, as checks over the output ---

PROMPT = re.compile(r"Result \((p/f|p/f/s)\):")


def _headings(output, items):
    """Each item's heading position, in the items' order; fails if one is
    missing, repeated, or out of order."""
    positions = []
    for item in items:
        pattern = re.compile(
            rf"^{item['sequence_number']}\. {re.escape(item['title'])}", re.MULTILINE)
        found = [m.start() for m in pattern.finditer(output)]
        assert len(found) == 1, (
            f"item {item['sequence_number']} heading printed {len(found)} times")
        positions.append(found[0])
    assert positions == sorted(positions), f"items out of order: {positions}"
    return positions


def _segments(output, items):
    """The output from each item's heading to the next (the last to the summary)."""
    positions = _headings(output, items)
    end = output.find("Summary · ")
    assert end > positions[-1], "no summary after the last item"
    bounds = positions[1:] + [end]
    return [output[a:b] for a, b in zip(positions, bounds)]


def assert_items_in_order(output, items):
    _headings(output, items)


def assert_prompts_match_required(output, items):
    """One prompt per item: (p/f) on a required item, (p/f/s) on an optional one.
    An answer asked again prints the same prompt again, so every prompt in a
    segment must be of the item's kind."""
    for item, seg in zip(items, _segments(output, items)):
        kinds = set(PROMPT.findall(seg))
        want = "p/f" if item["required"] else "p/f/s"
        assert kinds == {want}, (
            f"item {item['sequence_number']}: prompts {kinds}, want {want}")


def assert_diagnosis_on_fail(output, items, failed):
    """`Diagnosis: <the item's diagnosis>` inside a failed item's own segment,
    after its prompt, and in no other segment."""
    for item, seg in zip(items, _segments(output, items)):
        line = f"Diagnosis: {item['diagnosis_if_fail']}"
        if item["sequence_number"] in failed:
            assert line in seg, f"item {item['sequence_number']}: no diagnosis after its fail"
            assert seg.index(line) > PROMPT.search(seg).start(), (
                f"item {item['sequence_number']}: diagnosis before the answer")
        else:
            assert "Diagnosis:" not in seg, (
                f"item {item['sequence_number']}: a diagnosis without a fail")


def assert_summary(output, slug, powertrain, items, answers):
    """The counts line, then exactly the failed items with their diagnoses."""
    n = len(items)
    counts = (answers.count("p"), answers.count("f"), answers.count("s"))
    line = (f"Summary · {slug} · for {powertrain}: {counts[0]} passed, "
            f"{counts[1]} failed, {counts[2]} skipped of {n}")
    assert line in output, f"summary line missing; want {line!r}"
    tail = output[output.index(line) + len(line):]
    listed = re.findall(r"^\s+(\d+)\. ", tail, re.MULTILINE)
    want = [str(i["sequence_number"]) for i, a in zip(items, answers) if a == "f"]
    assert listed == want, f"summary lists failed items {listed}, want {want}"
    for item, a in zip(items, answers):
        if a == "f":
            assert f"{item['sequence_number']}. {item['title']}: {item['diagnosis_if_fail']}" in tail
    assert "Nothing was saved" in tail


def assert_refused(result, message):
    """Exit 1, the message, and no question asked: no item, no answer prompt."""
    assert result.exit_code == 1, f"exit {result.exit_code}"
    assert message in result.output, f"missing {message!r}"
    assert not PROMPT.search(result.output), "an item was asked after a refusal"
    assert not re.search(r"^1\. ", result.output, re.MULTILINE), "item 1 printed"


# --- Fixtures ---


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    """One freshly migrated database for the runs that do not change it."""
    path = str(tmp_path_factory.mktemp("run356") / "motodiag.db")
    init_db(path)
    return path


@pytest.fixture
def fresh_db(tmp_path):
    """A database of its own, for a planted change."""
    path = str(tmp_path / "motodiag.db")
    init_db(path)
    return path


# --- The engine ---


class TestTheEngine:
    def _two_steps(self, **kw):
        return DiagnosticWorkflow(steps=[
            WorkflowStep(step_number=1, test_instruction="a", diagnosis_if_fail="d1"),
            WorkflowStep(step_number=2, test_instruction="b", diagnosis_if_fail="d2"),
        ], **kw)

    def test_by_default_a_fail_ends_the_workflow_as_in_phase_82(self):
        wf = self._two_steps()
        assert wf.report_result(StepResult.FAIL) is None
        assert wf.is_complete() and wf.steps[1].result is None

    def test_with_stop_on_fail_off_a_fail_goes_on_to_the_next_step(self):
        wf = self._two_steps(stop_on_fail=False)
        assert wf.report_result(StepResult.FAIL) is wf.steps[1]
        assert not wf.is_complete()
        assert wf.report_result(StepResult.PASS) is None
        assert wf.is_complete()
        assert [s.result for s in wf.steps] == [StepResult.FAIL, StepResult.PASS]

    def test_checklist_workflow_maps_each_item_to_a_step(self, db):
        template = get_template_by_slug("valve_adjustment_v1", db)
        items = _items(db, "valve_adjustment_v1")
        wf = checklist_workflow(template, items)
        assert wf.stop_on_fail is False
        assert wf.max_steps == len(items) == len(wf.steps)
        assert wf.workflow_id == "valve_adjustment_v1"
        for item, step in zip(items, wf.steps):
            assert step.step_number == item["sequence_number"]
            assert step.test_instruction == item["instruction_text"]
            assert step.expected_pass == item["expected_pass"]
            assert step.expected_fail == item["expected_fail"]
            assert step.diagnosis_if_fail == item["diagnosis_if_fail"]


# --- The five named cases ---


class TestAFullPass:
    def test_every_item_in_order_and_a_clean_summary(self, db):
        items = _items(db, "brake_service_v1")
        answers = ["p"] * len(items)
        r = _run(db, "brake_service_v1", "--powertrain", "ice", answers=answers)
        assert r.exit_code == 0, r.output
        assert "brake_service_v1 · for ice · 7 items" in r.output
        assert_items_in_order(r.output, items)
        assert_prompts_match_required(r.output, items)
        assert_diagnosis_on_fail(r.output, items, failed=set())
        assert_summary(r.output, "brake_service_v1", "ice", items, answers)


class TestAFailShowsItsDiagnosis:
    def test_the_diagnosis_prints_on_the_fail_and_the_run_goes_on(self, db):
        items = _items(db, "brake_service_v1")
        # Items 2 and 6 fail; 3 and 4 are optional and pass.
        answers = ["p", "f", "p", "p", "p", "f", "p"]
        r = _run(db, "brake_service_v1", "--powertrain", "electric", answers=answers)
        assert r.exit_code == 0, r.output
        assert_items_in_order(r.output, items)
        assert_diagnosis_on_fail(r.output, items, failed={2, 6})
        assert_summary(r.output, "brake_service_v1", "electric", items, answers)


class TestAnOptionalItem:
    def test_an_optional_item_takes_a_skip(self, db):
        items = _items(db, "winterization_v1")
        optional = [i for i in items if not i["required"]]
        assert optional, "winterization_v1 has no optional item to skip"
        answers = ["p" if i["required"] else "s" for i in items]
        r = _run(db, "winterization_v1", "--powertrain", "hybrid", answers=answers)
        assert r.exit_code == 0, r.output
        assert_prompts_match_required(r.output, items)
        assert_summary(r.output, "winterization_v1", "hybrid", items, answers)

    def test_a_required_item_refuses_a_skip_and_asks_again(self, db):
        items = _items(db, "brake_service_v1")
        assert items[0]["required"]
        answers = ["p"] * len(items)
        r = _run(db, "brake_service_v1", "--powertrain", "ice", answers=["s"] + answers)
        assert r.exit_code == 0, r.output
        assert "Error: 's' is not one of 'p', 'f'." in r.output
        assert_prompts_match_required(r.output, items)
        assert_summary(r.output, "brake_service_v1", "ice", items, answers)


class TestARetiredSlug:
    @pytest.mark.parametrize("slug", RETIRED)
    @pytest.mark.parametrize("flag", [(), ("--powertrain", "ice")])
    def test_refused_as_show_refuses_it(self, db, slug, flag):
        description = get_template_by_slug(slug, db)["description"]
        assert description.startswith("Retired.")
        r = _run(db, slug, *flag, answers=["ice"] + ["p"] * 10)
        assert_refused(r, f"{slug}: {description}")
        assert "Powertrain" not in r.output, "asked for a powertrain before refusing"

    def test_control_the_same_template_active_runs(self, fresh_db):
        """The refusal is the retirement: made active, the starter runs."""
        _execute(fresh_db, "UPDATE workflow_templates SET is_active = 1"
                           " WHERE slug = 'generic_ppi_v1'")
        items = _items(fresh_db, "generic_ppi_v1")
        r = _run(fresh_db, "generic_ppi_v1", "--powertrain", "ice",
                 answers=["p"] * len(items))
        assert r.exit_code == 0, r.output
        assert_items_in_order(r.output, items)


class TestAnUnknownSlug:
    def test_refused_as_show_refuses_it(self, db):
        r = _run(db, "no_such_template_v1", answers=["ice"])
        assert_refused(r, "No workflow template with slug 'no_such_template_v1'.")
        assert "motodiag workflow list" in r.output


# --- The powertrain (option A) ---


class TestThePowertrain:
    def test_the_flag_refuses_a_template_that_does_not_cover_it(self, db):
        r = _run(db, "valve_adjustment_v1", "--powertrain", "electric", answers=["p"] * 8)
        assert_refused(r, "valve_adjustment_v1 covers ice, hybrid, not electric.")

    def test_without_the_flag_the_run_asks(self, db):
        items = _items(db, "brake_service_v1")
        answers = ["p"] * len(items)
        r = _run(db, "brake_service_v1", answers=["electric"] + answers)
        assert r.exit_code == 0, r.output
        assert "Powertrain (ice, electric, hybrid):" in r.output
        assert "brake_service_v1 · for electric · 7 items" in r.output
        assert_summary(r.output, "brake_service_v1", "electric", items, answers)

    def test_the_prompt_refuses_a_template_that_does_not_cover_it(self, db):
        r = _run(db, "valve_adjustment_v1", answers=["electric"] + ["p"] * 8)
        assert_refused(r, "valve_adjustment_v1 covers ice, hybrid, not electric.")

    def test_control_the_refusal_follows_the_templates_powertrains(self, fresh_db):
        """brake_service_v1 runs on electric; take electric off it and the
        same run is refused."""
        _execute(fresh_db, "UPDATE workflow_templates SET applicable_powertrains ="
                           " '[\"ice\",\"hybrid\"]' WHERE slug = 'brake_service_v1'")
        r = _run(fresh_db, "brake_service_v1", "--powertrain", "electric",
                 answers=["p"] * 7)
        assert_refused(r, "brake_service_v1 covers ice, hybrid, not electric.")


class TestEveryActiveTemplate:
    def test_each_runs_for_each_powertrain_it_covers_and_is_refused_otherwise(self, db):
        templates = list_templates(db, is_active=True)
        assert len(templates) == 13
        ran = refused = 0
        for t in templates:
            items = get_checklist_items(t["id"], db)
            answers = ["p"] * len(items)
            for p in POWERTRAINS:
                r = _run(db, t["slug"], "--powertrain", p, answers=answers)
                if p in t["applicable_powertrains"]:
                    assert r.exit_code == 0, (t["slug"], p, r.output[-500:])
                    assert_items_in_order(r.output, items)
                    assert_prompts_match_required(r.output, items)
                    assert_summary(r.output, t["slug"], p, items, answers)
                    ran += 1
                else:
                    assert_refused(r, f"not {p}.")
                    refused += 1
        # 8 templates cover all three powertrains, 5 cover ice and hybrid.
        assert (ran, refused) == (8 * 3 + 5 * 2, 5)


class TestNothingIsSaved:
    def test_a_run_leaves_every_table_as_it_was(self, fresh_db):
        before = _dump(fresh_db)
        items = _items(fresh_db, "winterization_v1")
        answers = ["f" if i["required"] else "s" for i in items]
        r = _run(fresh_db, "winterization_v1", "--powertrain", "ice", answers=answers)
        assert r.exit_code == 0, r.output
        assert _dump(fresh_db) == before


# --- The helpers fail on planted output ---


class TestTheHelpersFailOnPlantedOutput:
    """Each planted output is a real run's output with one thing wrong."""

    @pytest.fixture(scope="class")
    def good(self, db):
        items = _items(db, "brake_service_v1")
        answers = ["p", "f", "s", "p", "p", "p", "p"]
        r = _run(db, "brake_service_v1", "--powertrain", "ice", answers=answers)
        assert r.exit_code == 0, r.output
        return SimpleNamespace(out=r.output, items=items, answers=answers)

    def test_the_good_output_passes_every_helper(self, good):
        assert_items_in_order(good.out, good.items)
        assert_prompts_match_required(good.out, good.items)
        assert_diagnosis_on_fail(good.out, good.items, failed={2})
        assert_summary(good.out, "brake_service_v1", "ice", good.items, good.answers)

    def test_items_swapped(self, good):
        a, b = good.items[3], good.items[4]
        ha, hb = f"4. {a['title']}", f"5. {b['title']}"
        planted = good.out.replace(ha, "\0").replace(hb, ha).replace("\0", hb)
        with pytest.raises(AssertionError, match="out of order"):
            assert_items_in_order(planted, good.items)

    def test_an_item_missing(self, good):
        planted = good.out.replace(f"5. {good.items[4]['title']}", "")
        with pytest.raises(AssertionError, match="item 5 heading printed 0 times"):
            assert_items_in_order(planted, good.items)

    def test_a_run_that_stopped_at_the_fail(self, good):
        planted = good.out[:good.out.index(f"3. {good.items[2]['title']}")]
        with pytest.raises(AssertionError):
            assert_items_in_order(planted, good.items)

    def test_a_skip_offered_on_a_required_item(self, good):
        head = f"1. {good.items[0]['title']}"
        i = good.out.index(head)
        planted = good.out[:i] + good.out[i:].replace("Result (p/f):", "Result (p/f/s):", 1)
        with pytest.raises(AssertionError, match="item 1: prompts"):
            assert_prompts_match_required(planted, good.items)

    def test_the_diagnosis_missing(self, good):
        planted = good.out.replace("Diagnosis: ", "", 1)
        with pytest.raises(AssertionError, match="item 2: no diagnosis"):
            assert_diagnosis_on_fail(planted, good.items, failed={2})

    def test_the_diagnosis_under_the_next_item(self, good):
        line = f"  Diagnosis: {good.items[1]['diagnosis_if_fail']}\n"
        head3 = f"3. {good.items[2]['title']}"
        planted = good.out.replace(line, "", 1)
        i = planted.index(head3) + len(head3)
        planted = planted[:i] + "\n" + line + planted[i:]
        with pytest.raises(AssertionError):
            assert_diagnosis_on_fail(planted, good.items, failed={2})

    def test_the_diagnosis_before_the_answer(self, good):
        seg_start = good.out.index(f"2. {good.items[1]['title']}")
        line = f"Diagnosis: {good.items[1]['diagnosis_if_fail']}"
        planted = good.out.replace("  " + line, "", 1)
        planted = planted[:seg_start] + line + "\n" + planted[seg_start:]
        # The line now sits in item 1's segment and item 2's is empty of it.
        with pytest.raises(AssertionError):
            assert_diagnosis_on_fail(planted, good.items, failed={2})

    def test_a_wrong_count_in_the_summary(self, good):
        planted = good.out.replace("1 failed", "0 failed")
        with pytest.raises(AssertionError, match="summary line missing"):
            assert_summary(planted, "brake_service_v1", "ice", good.items, good.answers)

    def test_a_failed_item_left_out_of_the_summary(self, good):
        tail_at = good.out.index("Summary · ")
        planted = good.out[:tail_at] + re.sub(
            r"^\s+2\. .*$", "", good.out[tail_at:], flags=re.MULTILINE)
        with pytest.raises(AssertionError, match="summary lists failed items"):
            assert_summary(planted, "brake_service_v1", "ice", good.items, good.answers)

    def test_a_refusal_that_went_on_to_ask(self, good):
        planted = SimpleNamespace(exit_code=1, output="refused\n" + good.out)
        with pytest.raises(AssertionError, match="an item was asked"):
            assert_refused(planted, "refused")

    def test_a_refusal_that_exited_0(self):
        planted = SimpleNamespace(exit_code=0, output="refused\n")
        with pytest.raises(AssertionError, match="exit 0"):
            assert_refused(planted, "refused")

    def test_a_planted_write_is_seen_by_the_dump(self, fresh_db):
        before = _dump(fresh_db)
        _execute(fresh_db, "UPDATE checklist_items SET title = title || ' x'"
                           " WHERE id = (SELECT MIN(id) FROM checklist_items)")
        assert _dump(fresh_db) != before
