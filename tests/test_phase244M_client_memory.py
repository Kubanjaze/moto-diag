"""Phase 244M — the shop remembers the machine.

The operator asked for a per-client long-term memory that compiles every
interaction and answers inquiries without an API call, plus a cross-shop hive
mind on top. This file guards layer (a). The hive mind is a separate phase for
a reason that is not size — it is a controller-status change under GDPR
Art. 28(10) and CCPA's service-provider carve-out, and no privacy technique
reaches it.

Two guards here are worth reading before the rest, because they pin decisions
that are easy to undo by accident:

``TestTheSubjectIsTheVehicleNotTheCustomer`` — every vehicle row in the real
database carries ``customer_id = 1``, the column default, and customer 1 is
literally named ``Unassigned``. Keying the memory on that produces one memory
holding every bike in the shop.

``TestItNeverCallsAModel`` — "answers without the api" is a claim about money.
A docstring cannot enforce it, so it is asserted against the Phase 244L ledger.
"""

import importlib
import json
import sqlite3

import pytest

from support.source_guards import code_of

from motodiag.core.database import SCHEMA_VERSION, get_connection, init_db
from motodiag.core.migrations import get_migration_by_version, rollback_to_version
from motodiag.media.vision_types import VehicleContext
from motodiag.memory import (
    FACT_KINDS,
    SOURCES,
    MemoryFact,
    answer_from_memory,
    attach_vehicle,
    compile_vehicle,
    erase_customer,
    erase_plan,
    fact_key,
    insert_facts,
    recall,
    recall_summary,
)
from motodiag.memory import answers as answers_mod
from motodiag.memory import compile as compile_mod
from motodiag.memory import facts as facts_mod

# `from motodiag.memory import recall` gives the FUNCTION, not the module —
# the package re-exports `recall.recall` under the same name, so the function
# shadows its own module in the package namespace. importlib asks for the
# module unambiguously.
recall_mod = importlib.import_module("motodiag.memory.recall")

VEHICLE = 10
CUSTOMER = 2


@pytest.fixture
def db(tmp_path):
    """A shop with one machine, one real customer, and some recorded work."""
    path = str(tmp_path / "memory.db")
    init_db(path)
    c = sqlite3.connect(path)
    c.execute(
        "INSERT INTO customers (id, name) VALUES (?, 'Dana Reyes')", (CUSTOMER,)
    )
    c.execute(
        "INSERT INTO vehicles (id, make, model, year, customer_id, mileage) "
        "VALUES (?, 'Honda', 'CBR600F4i', 2001, 1, 31000)",
        (VEHICLE,),
    )
    c.execute(
        "INSERT INTO diagnostic_sessions "
        "(id, vehicle_id, vehicle_make, vehicle_model, vehicle_year, status, "
        " notes, symptoms, created_at) "
        "VALUES (1, ?, 'Honda', 'CBR600F4i', 2001, 'open', "
        "        'Leaking oil on left side', ?, '2026-09-01T10:00:00')",
        (VEHICLE, json.dumps(["oil leak", "smoke on startup"])),
    )
    c.execute(
        "INSERT INTO service_history "
        "(id, vehicle_id, event_type, at_miles, at_date, notes) "
        "VALUES (1, ?, 'valve-adjust', 28000, '2025-06-14', 'shims replaced')",
        (VEHICLE,),
    )
    c.commit()
    c.close()
    return path


def _facts(path, vehicle_id=VEHICLE):
    return recall(vehicle_id, db_path=path)


# ---------------------------------------------------------------------------


class TestTheSubjectIsTheVehicleNotTheCustomer:
    """The load-bearing decision, and the one a refactor would quietly undo.

    `customers` row 1 is named `Unassigned`, and every vehicle row carries
    `customer_id = 1` — the column DEFAULT, never overwritten. Compiling per
    customer against that key produces ONE memory belonging to `Unassigned`
    containing every bike in the shop: the exact cross-contamination the
    feature exists to prevent, arriving on day one wearing the feature's name.
    """

    def test_the_fact_table_is_keyed_on_vehicle(self):
        sql = get_migration_by_version(58).upgrade_sql
        assert "vehicle_id INTEGER NOT NULL" in sql
        assert "REFERENCES vehicles(id)" in sql
        assert "customer_id" not in sql, (
            "memory_facts must not carry a customer key — customer is derived "
            "by joining, precisely so the sentinel cannot become a subject"
        )

    def test_the_fact_row_carries_no_customer(self):
        assert not hasattr(MemoryFact(
            vehicle_id=1, fact_kind="repair", subject="x",
            source="service-record", origin_table="t", established_at="2026-01-01",
        ), "customer_id")

    def test_recall_takes_a_vehicle(self):
        src = code_of(recall_mod.recall)
        assert "vehicle_id" in src
        assert "customer" not in src.lower()

    def test_two_machines_owned_by_one_customer_keep_separate_memories(self, db):
        c = sqlite3.connect(db)
        c.execute(
            "INSERT INTO vehicles (id, make, model, year, customer_id) "
            "VALUES (11, 'Yamaha', 'MT07', 2021, 1)"
        )
        c.commit(); c.close()
        attach_vehicle(VEHICLE, CUSTOMER, db_path=db)
        attach_vehicle(11, CUSTOMER, db_path=db)
        compile_vehicle(VEHICLE, db_path=db)

        assert _facts(db, VEHICLE), "the Honda has facts"
        assert _facts(db, 11) == [], (
            "the Yamaha shares an owner and must not inherit the Honda's history"
        )


class TestOwnership:
    def test_attach_records_a_real_owner(self, db):
        attach_vehicle(VEHICLE, CUSTOMER, db_path=db)
        with get_connection(db) as conn:
            owner = conn.execute(
                "SELECT customer_id FROM vehicles WHERE id = ?", (VEHICLE,)
            ).fetchone()[0]
            junction = conn.execute(
                "SELECT COUNT(*) FROM customer_bikes WHERE vehicle_id = ?",
                (VEHICLE,),
            ).fetchone()[0]
        assert owner == CUSTOMER
        assert junction == 1, "both ownership tables are written, not just one"

    def test_attaching_twice_is_idempotent(self, db):
        attach_vehicle(VEHICLE, CUSTOMER, db_path=db)
        attach_vehicle(VEHICLE, CUSTOMER, db_path=db)
        with get_connection(db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM customer_bikes WHERE vehicle_id = ?",
                (VEHICLE,),
            ).fetchone()[0] == 1

    def test_the_sentinel_is_never_written_as_an_owner(self, db):
        with pytest.raises(ValueError, match="sentinel"):
            attach_vehicle(VEHICLE, 1, db_path=db)

    def test_attaching_to_a_missing_customer_raises(self, db):
        with pytest.raises(ValueError, match="No customer"):
            attach_vehicle(VEHICLE, 9999, db_path=db)


class TestCompileIsIdempotent:
    def test_a_second_compile_inserts_nothing(self, db):
        first = compile_vehicle(VEHICLE, db_path=db)
        second = compile_vehicle(VEHICLE, db_path=db)
        assert first > 0, "the fixture has recorded work to compile"
        assert second == 0, "re-compiling must insert nothing"

    def test_it_reports_rows_inserted_not_items_walked(self, db):
        """Phase 244D's loader reported items walked, so a re-seed announced
        '970 inserted' while inserting nothing."""
        compile_vehicle(VEHICLE, db_path=db)
        with get_connection(db) as conn:
            before = conn.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0]
        reported = compile_vehicle(VEHICLE, db_path=db)
        with get_connection(db) as conn:
            after = conn.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0]
        assert reported == after - before == 0

    def test_the_count_matches_reality_on_a_first_run(self, db):
        reported = compile_vehicle(VEHICLE, db_path=db)
        with get_connection(db) as conn:
            actual = conn.execute("SELECT COUNT(*) FROM memory_facts").fetchone()[0]
        assert reported == actual

    def test_new_work_compiles_without_duplicating_old(self, db):
        first = compile_vehicle(VEHICLE, db_path=db)
        c = sqlite3.connect(db)
        c.execute(
            "INSERT INTO service_history "
            "(id, vehicle_id, event_type, at_miles, at_date) "
            "VALUES (2, ?, 'chain', 31000, '2026-08-02')",
            (VEHICLE,),
        )
        c.commit(); c.close()
        second = compile_vehicle(VEHICLE, db_path=db)
        assert second == 1
        with get_connection(db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM memory_facts"
            ).fetchone()[0] == first + 1


class TestTheKeyHandlesNulls:
    """SQLite treats NULLs as DISTINCT in a UNIQUE constraint.

    A naive UNIQUE over the columns would let two facts differing only by a
    NULL ``origin_id`` both insert, and every re-compile would duplicate them.
    Phase 244D proved this with a three-insert probe before trusting it.
    """

    def test_a_null_origin_id_still_dedupes(self, db):
        fact = MemoryFact(
            vehicle_id=VEHICLE, fact_kind="observation", subject="weeping seal",
            source="model-generated", origin_table="videos", origin_id=None,
            established_at="2026-09-01",
        )
        assert insert_facts([fact], db_path=db) == 1
        assert insert_facts([fact], db_path=db) == 0, (
            "a NULL origin_id must not defeat deduplication"
        )

    def test_sqlite_really_does_treat_nulls_as_distinct(self, db):
        """The premise, proven here rather than assumed — if SQLite ever
        changed this, the COALESCE would be dead weight and this test says so.
        """
        with get_connection(db) as conn:
            conn.execute("CREATE TABLE probe (a TEXT, b INTEGER, UNIQUE(a, b))")
            conn.execute("INSERT INTO probe VALUES ('x', NULL)")
            conn.execute("INSERT INTO probe VALUES ('x', NULL)")
            conn.commit()
            assert conn.execute("SELECT COUNT(*) FROM probe").fetchone()[0] == 2

    def test_the_none_sentinel_cannot_collide_with_a_real_id(self):
        none_key = fact_key(
            vehicle_id=1, fact_kind="repair", subject="s",
            origin_table="t", origin_id=None,
        )
        for candidate in (0, 1, -1):
            assert none_key != fact_key(
                vehicle_id=1, fact_kind="repair", subject="s",
                origin_table="t", origin_id=candidate,
            )

    def test_the_key_coalesces_rather_than_dropping_the_null(self):
        src = code_of(facts_mod.fact_key)
        assert "origin_id is None" in src, "the null branch must be explicit"


class TestBadDataIsRejectedNotDropped:
    def test_a_typod_source_raises(self, db):
        """`INSERT OR IGNORE` suppresses CHECK violations as well as
        uniqueness ones, so a typo'd value would vanish silently. Phase 244D
        shipped that; Phases 211/235B caught it."""
        bad = MemoryFact(
            vehicle_id=VEHICLE, fact_kind="repair", subject="x",
            source="serivce-record",  # typo, deliberately
            origin_table="t", established_at="2026-01-01",
        )
        with pytest.raises(sqlite3.IntegrityError):
            insert_facts([bad], db_path=db)

    def test_a_typod_fact_kind_raises(self, db):
        bad = MemoryFact(
            vehicle_id=VEHICLE, fact_kind="repaired", subject="x",
            source="service-record", origin_table="t", established_at="2026-01-01",
        )
        with pytest.raises(sqlite3.IntegrityError):
            insert_facts([bad], db_path=db)

    def test_the_insert_does_not_use_the_or_forms(self):
        src = code_of(facts_mod.insert_facts)
        assert "ON CONFLICT" in src
        assert "INSERT OR IGNORE" not in src
        assert "INSERT OR REPLACE" not in src

    def test_the_python_vocabularies_match_the_database(self, db):
        with get_connection(db) as conn:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'memory_facts'"
            ).fetchone()[0]
        for kind in FACT_KINDS:
            assert f"'{kind}'" in sql, f"{kind} missing from the CHECK"
        for source in SOURCES:
            assert f"'{source}'" in sql, f"{source} missing from the CHECK"


class TestRecall:
    def test_every_fact_carries_its_vintage_and_its_source(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        for fact in _facts(db):
            assert fact.established_at, f"{fact.subject} has no date"
            assert fact.source in SOURCES

    def test_a_mechanic_correction_outranks_a_newer_model_guess(self, db):
        insert_facts(
            [
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="correction",
                    subject="split intake boot", source="mechanic-verified",
                    origin_table="diagnostic_feedback", origin_id=1,
                    established_at="2024-01-01",
                ),
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="observation",
                    subject="possible fuel starvation", source="model-generated",
                    origin_table="videos", origin_id=1,
                    established_at="2026-09-09",
                ),
            ],
            db_path=db,
        )
        ordered = _facts(db)
        assert ordered[0].source == "mechanic-verified", (
            "a fresh guess must not displace an established fact"
        )

    def test_within_one_source_the_newest_comes_first(self, db):
        insert_facts(
            [
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="repair", subject="old",
                    source="service-record", origin_table="t", origin_id=1,
                    established_at="2020-01-01",
                ),
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="repair", subject="new",
                    source="service-record", origin_table="t", origin_id=2,
                    established_at="2026-01-01",
                ),
            ],
            db_path=db,
        )
        subjects = [f.subject for f in _facts(db) if f.subject in ("old", "new")]
        assert subjects == ["new", "old"]

    def test_monotonicity_adding_a_fact_never_removes_one(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        before = {f.subject for f in _facts(db)}
        insert_facts(
            [
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="measurement",
                    subject="compression 165 psi", source="mechanic-verified",
                    origin_table="manual", origin_id=99,
                    established_at="2026-09-05",
                )
            ],
            db_path=db,
        )
        after = {f.subject for f in _facts(db)}
        assert before < after, "knowing more must never return less"

    def test_raising_the_limit_only_reveals_more(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        small = recall(VEHICLE, limit=2, db_path=db)
        large = recall(VEHICLE, limit=6, db_path=db)
        assert [f.subject for f in large[: len(small)]] == [
            f.subject for f in small
        ], "a larger limit must extend the list, never reorder it"

    def test_a_superseded_fact_is_not_returned_as_current(self, db):
        insert_facts(
            [
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="measurement",
                    subject="valve clearance 0.10mm", source="mechanic-verified",
                    origin_table="t", origin_id=1, established_at="2020-01-01",
                    superseded_at="2026-01-01",
                )
            ],
            db_path=db,
        )
        assert "valve clearance 0.10mm" not in {f.subject for f in _facts(db)}

    def test_an_empty_memory_summarises_to_nothing_not_to_a_claim(self, db):
        assert recall_summary(VEHICLE, db_path=db) == "", (
            "saying 'no history' is a claim; saying nothing is not"
        )

    def test_the_summary_dates_and_sources_every_line(self, db):
        """`"20" in line` would also be satisfied by a subject containing 20,
        so each line is matched against the real dates instead."""
        compile_vehicle(VEHICLE, db_path=db)
        dates = {f.established_at for f in _facts(db)}
        summary = recall_summary(VEHICLE, db_path=db)
        lines = summary.splitlines()[1:]
        assert lines, "the summary had no fact lines to check"
        for line in lines:
            assert any(d and d in line for d in dates), f"undated line: {line}"
            assert any(s in line for s in SOURCES), f"unsourced line: {line}"


class TestTheVisionPathSeesTheHistory:
    """The payoff. Phase 244C fixed `_build_vehicle_context` from a stub that
    told the model nothing was known; this makes the context carry what the
    shop has actually done to the machine."""

    def test_vehicle_context_renders_history(self):
        vc = VehicleContext(
            make="Honda", model="CBR600F4i",
            history="Known history:\n- [repair] valve-adjust (2025-06-14)",
        )
        rendered = vc.to_context_string()
        assert "valve-adjust" in rendered
        assert "No vehicle context provided." not in rendered

    def test_empty_history_adds_no_line(self):
        vc = VehicleContext(make="Honda", model="CBR600F4i", history="")
        assert vc.to_context_string() == "Vehicle: ? Honda CBR600F4i"

    def test_the_builder_populates_it(self, db):
        from motodiag.media.analysis_worker import _build_vehicle_context

        compile_vehicle(VEHICLE, db_path=db)
        vc = _build_vehicle_context({"session_id": 1}, db_path=db)
        assert vc.history, "the builder must read the compiled memory"
        assert "valve-adjust" in vc.history
        assert "valve-adjust" in vc.to_context_string()

    def test_a_broken_memory_does_not_stop_the_analysis(self, db, monkeypatch):
        from motodiag.media import analysis_worker

        def boom(*a, **k):
            raise RuntimeError("memory unavailable")

        monkeypatch.setattr(recall_mod, "recall_summary", boom)
        vc = analysis_worker._build_vehicle_context({"session_id": 1}, db_path=db)
        assert vc.make == "Honda", "the analysis still gets its context"
        assert vc.history == ""



class TestTheModelIsNotFedItsOwnOutput:
    """Surfaced by running it, not by planning it.

    Vehicle 10 in the real database had eleven compiled facts: one human
    complaint and ten paragraphs of the vision model's own prose from a single
    sweep. All ten were about to be injected into the next sweep's prompt
    labelled "known history for this machine".

    That is a self-reinforcing loop with no brake in it. An early wrong reading
    returns as context, biases the next analysis toward itself, and is written
    back looking more established each time. The provenance label does not help
    here the way it helps a person -- the model cannot discount its own prior
    output, and Phase 244M's research measured that even people mostly do not
    check.
    """

    @pytest.fixture
    def mixed(self, db):
        insert_facts(
            [
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="observation",
                    subject="possible stator cover leak",
                    source="model-generated", origin_table="videos",
                    origin_id=1, established_at="2026-09-10",
                ),
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="repair",
                    subject="clutch cover gasket replaced",
                    source="service-record", origin_table="work_orders",
                    origin_id=1, established_at="2026-09-08",
                ),
            ],
            db_path=db,
        )
        return db

    def test_the_prompt_block_excludes_model_generated_facts(self, mixed):
        summary = recall_summary(VEHICLE, db_path=mixed)
        assert "clutch cover gasket replaced" in summary
        assert "possible stator cover leak" not in summary, (
            "the model's own prior output must not return to it as history"
        )
        assert "model-generated" not in summary

    def test_a_caller_showing_a_person_can_ask_for_them(self, mixed):
        summary = recall_summary(
            VEHICLE, include_model_generated=True, db_path=mixed
        )
        assert "possible stator cover leak" in summary

    def test_the_vision_context_carries_no_model_generated_history(self, mixed):
        from motodiag.media.analysis_worker import _build_vehicle_context

        compile_vehicle(VEHICLE, db_path=mixed)
        vc = _build_vehicle_context({"session_id": 1}, db_path=mixed)
        assert "model-generated" not in vc.to_context_string()

    def test_filtering_happens_before_the_limit(self, db):
        """Otherwise a machine with a chatty sweep loses its human history.

        The limit is applied to the FILTERED list. Applied first, twenty model
        observations would fill the budget and push the one complaint that
        matters out of the block entirely.
        """
        insert_facts(
            [
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="observation",
                    subject=f"model observation {i}", source="model-generated",
                    origin_table="videos", origin_id=i,
                    established_at="2026-09-10",
                )
                for i in range(20)
            ]
            + [
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="complaint",
                    subject="the one thing that matters",
                    source="customer-reported", origin_table="diagnostic_sessions",
                    origin_id=1, established_at="2026-09-01",
                )
            ],
            db_path=db,
        )
        summary = recall_summary(VEHICLE, limit=5, db_path=db)
        assert "the one thing that matters" in summary

    def test_show_and_ask_still_surface_them_to_a_person(self, mixed):
        assert any(
            f.source == "model-generated" for f in recall(VEHICLE, db_path=mixed)
        ), "recall itself is unfiltered — only the prompt block excludes them"
        result = answer_from_memory(
            VEHICLE, "has this stator leak been seen before?", db_path=mixed
        )
        assert result.answered and "stator" in result.text


class TestAnsweringFromMemory:
    def test_it_answers_what_work_was_done(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(VEHICLE, "what work has been done?", db_path=db)
        assert result.answered
        assert "valve-adjust" in result.text

    def test_it_answers_when_it_was_last_worked_on(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(VEHICLE, "when was it last serviced?", db_path=db)
        assert result.answered
        assert "2025-06-14" in result.text

    def test_last_service_is_the_newest_not_the_best_supported(self, db):
        """Recall orders by what a fact rests on, so the head of the list can
        be years older than the most recent work. `last_service` must sort by
        date or it answers a different question."""
        compile_vehicle(VEHICLE, db_path=db)
        insert_facts(
            [
                MemoryFact(
                    vehicle_id=VEHICLE, fact_kind="repair", subject="fork seals",
                    source="service-record", origin_table="t", origin_id=77,
                    established_at="2026-08-30",
                )
            ],
            db_path=db,
        )
        result = answer_from_memory(VEHICLE, "when was it last serviced?", db_path=db)
        assert "fork seals" in result.text and "2026-08-30" in result.text

    def test_it_answers_the_complaint(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(
            VEHICLE, "what was the complaint?", db_path=db
        )
        assert result.answered
        assert "Leaking oil on left side" in result.text

    def test_seen_before_finds_a_real_recurrence(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(
            VEHICLE, "has this oil leak been seen before?", db_path=db
        )
        assert result.answered
        assert result.text.startswith("Yes")

    def test_seen_before_says_no_honestly_and_names_what_it_looked_for(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(
            VEHICLE, "has this speedometer fault been seen before?", db_path=db
        )
        assert result.answered
        assert result.text.startswith("No")
        assert "speedometer" in result.text, (
            "a negative must say what it searched for — 'no' to a "
            "misunderstood question is worse than a miss"
        )

    def test_mileage_comes_back_with_the_miles(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(VEHICLE, "at what mileage?", db_path=db)
        assert result.answered
        assert "28,000" in result.text

    def test_an_out_of_grammar_question_misses_explicitly(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(
            VEHICLE, "why is the engine running lean at 6000 rpm?", db_path=db
        )
        assert not result.answered
        assert "Not in memory" in result.text
        assert result.facts == [], "a miss returns nothing, never a guess"

    def test_a_machine_with_no_memory_misses_and_says_how_to_fix_it(self, db):
        result = answer_from_memory(VEHICLE, "what work has been done?", db_path=db)
        assert not result.answered
        assert "memory compile" in result.text

    def test_the_most_specific_phrase_wins(self, db):
        """'what was the complaint' contains 'complaint', and both are real
        entries — matching by first hit would make the answer depend on how
        the table happens to be written."""
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(VEHICLE, "what was the complaint?", db_path=db)
        assert result.intent == "complaints"

    def test_every_answer_line_is_dated_and_sourced(self, db):
        """Checks BOTH, against the facts' real dates.

        The first version of this asserted only the source while its name
        promised the date as well — a mutation that stripped the vintage
        passed it. Each line is now matched against the actual
        ``established_at`` of the fact behind it, so "date present" cannot be
        satisfied by a digit that happens to be in the subject text.
        """
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(VEHICLE, "what work has been done?", db_path=db)
        dates = {f.established_at for f in result.facts}
        lines = [ln for ln in result.text.splitlines() if ln.startswith("  - ")]
        assert lines, "the answer had no fact lines to check"
        for line in lines:
            assert any(s in line for s in SOURCES), f"unsourced: {line}"
            assert any(d and d in line for d in dates), f"undated: {line}"


class TestItNeverCallsAModel:
    """'Answers without the api' is a claim about money, and a docstring
    cannot enforce it. Asserted against the Phase 244L ledger."""

    def test_answering_writes_no_cost_event(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        for question in (
            "what work has been done?",
            "when was it last serviced?",
            "what parts were replaced?",
            "why is it running lean?",
        ):
            answer_from_memory(VEHICLE, question, db_path=db)
        with get_connection(db) as conn:
            spent = conn.execute("SELECT COUNT(*) FROM cost_events").fetchone()[0]
        assert spent == 0, "memory answers must cost nothing"

    def test_the_answer_module_imports_no_client(self):
        src = code_of(answers_mod)
        for forbidden in (
            "DiagnosticClient", "anthropic", "ask_with_images", "requests",
            "httpx", "openai",
        ):
            assert forbidden not in src, f"{forbidden} reached the offline path"

    def test_the_answer_reports_that_it_did_not_use_the_api(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        result = answer_from_memory(VEHICLE, "what work has been done?", db_path=db)
        assert result.used_api is False


class TestNoSimilarityMatchingAnywhere:
    """Phase 244M's research: similarity is an unreliable key for
    context-dependent questions, correct and incorrect matches occupy
    overlapping similarity ranges, and embeddings are insensitive to negation
    — the exact distinction between two opposite diagnostic answers.

    Matched against code with comments and docstrings blanked, so the prose
    above does not trip the guard. Phase 244G: a guard that reads source text
    will eventually read a comment, and it did so five times in one session.
    """

    @pytest.mark.parametrize(
        "module", [answers_mod, recall_mod, compile_mod, facts_mod]
    )
    def test_no_embedding_or_vector_call(self, module):
        src = code_of(module).lower()
        for forbidden in (
            "embedding", "embed(", "cosine", "vector", "faiss", "chromadb",
            "sentence_transformer", "similarity",
        ):
            assert forbidden not in src, (
                f"{forbidden} in {module.__name__} — recall is deterministic "
                "by design, not by omission"
            )

    def test_intent_matching_is_literal(self):
        src = code_of(answers_mod)
        assert "in normalised" in src or "phrase in normalised" in src


class TestErasure:
    def test_dry_run_lists_exactly_what_forget_deletes(self, db):
        attach_vehicle(VEHICLE, CUSTOMER, db_path=db)
        compile_vehicle(VEHICLE, db_path=db)
        plan = erase_plan(CUSTOMER, db_path=db)
        deleted = erase_customer(CUSTOMER, db_path=db)
        assert plan.fact_count == deleted > 0

    def test_forget_actually_hard_deletes(self, db):
        attach_vehicle(VEHICLE, CUSTOMER, db_path=db)
        compile_vehicle(VEHICLE, db_path=db)
        erase_customer(CUSTOMER, db_path=db)
        with get_connection(db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM memory_facts"
            ).fetchone()[0] == 0

    def test_forget_does_not_touch_the_records_it_compiled_from(self, db):
        """The compiled memory has no retention justification. The work orders
        and sessions it was compiled from are mandated records."""
        attach_vehicle(VEHICLE, CUSTOMER, db_path=db)
        compile_vehicle(VEHICLE, db_path=db)
        erase_customer(CUSTOMER, db_path=db)
        with get_connection(db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM diagnostic_sessions"
            ).fetchone()[0] == 1
            assert conn.execute(
                "SELECT COUNT(*) FROM service_history"
            ).fetchone()[0] == 1
            assert conn.execute(
                "SELECT notes FROM diagnostic_sessions WHERE id = 1"
            ).fetchone()[0] == "Leaking oil on left side"

    def test_erasing_the_sentinel_is_refused_and_explained(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        plan = erase_plan(1, db_path=db)
        assert plan.refused
        assert "sentinel" in plan.reason
        assert erase_customer(1, db_path=db) == 0
        with get_connection(db) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM memory_facts"
            ).fetchone()[0] > 0, "the shop's memory survived a sentinel erase"

    def test_erasing_one_customer_leaves_anothers_memory_alone(self, db):
        c = sqlite3.connect(db)
        c.execute("INSERT INTO customers (id, name) VALUES (3, 'Other Owner')")
        c.execute(
            "INSERT INTO vehicles (id, make, model, year, customer_id) "
            "VALUES (11, 'Yamaha', 'MT07', 2021, 1)"
        )
        c.execute(
            "INSERT INTO service_history "
            "(id, vehicle_id, event_type, at_date) "
            "VALUES (5, 11, 'chain', '2026-01-01')"
        )
        c.commit(); c.close()
        attach_vehicle(VEHICLE, CUSTOMER, db_path=db)
        attach_vehicle(11, 3, db_path=db)
        compile_vehicle(VEHICLE, db_path=db)
        compile_vehicle(11, db_path=db)

        erase_customer(CUSTOMER, db_path=db)
        assert _facts(db, VEHICLE) == []
        assert _facts(db, 11), "the other customer's memory is untouched"

    def test_a_customer_with_no_machines_erases_nothing(self, db):
        assert erase_customer(CUSTOMER, db_path=db) == 0

    def test_deleting_a_vehicle_cascades_its_memory(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        with get_connection(db) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("DELETE FROM diagnostic_sessions WHERE vehicle_id = ?", (VEHICLE,))
            conn.execute("DELETE FROM vehicles WHERE id = ?", (VEHICLE,))
            conn.commit()
            assert conn.execute(
                "SELECT COUNT(*) FROM memory_facts"
            ).fetchone()[0] == 0


class TestTheSchemaContract:
    def test_schema_version_is_current(self):
        assert SCHEMA_VERSION == 60  # f9-noqa: ssot-pin contract-pin: Phase 244M schema-bump pin. The literal is the point — importing the constant would make this assert x == x. Bumped 57→58 by migration 058 (memory_facts). Bumping requires a corresponding new migration in src/motodiag/core/migrations.py. Bumped 58→59 at Phase 244N (migration 059 adds guidance_interactions and video_analyses: /ask discarded its whole answer while 244L recorded what the question cost, and set_analysis_findings overwrote the findings blob so every re-analysis destroyed the prior sweep). Bumped 59→60 at Phase 244Q (migration 060 widens the cost_events kind CHECK to accept text_diagnosis: the TEXT diagnosis path spent money the ledger could not hold, so the first half of 244Q tuned max_tokens against spend nobody could measure). Reminder: test_phase191b_serve_migrations.py spells its pin `get_current_version(db_path) == N`, so grepping only for SCHEMA_VERSION misses it.

    def test_the_migration_declares_every_index(self, db):
        with get_connection(db) as conn:
            idx = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND tbl_name='memory_facts' AND name NOT LIKE 'sqlite_%'"
                )
            }
        assert idx == {
            "idx_memory_facts_vehicle",
            "idx_memory_facts_kind",
            "idx_memory_facts_established",
        }

    def test_the_fact_key_is_unique_in_the_database(self, db):
        with get_connection(db) as conn:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name = 'memory_facts'"
            ).fetchone()[0]
        assert "fact_key TEXT NOT NULL UNIQUE" in sql

    def test_rolling_back_058_destroys_nothing_it_did_not_create(self, db):
        """Phase 244L shipped a rollback copied from another migration that
        dropped a table it had not created. This one DID create its table, so
        dropping it is correct — and everything else must survive."""
        compile_vehicle(VEHICLE, db_path=db)
        rollback_to_version(57, db_path=db)
        with get_connection(db) as conn:
            names = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        assert "memory_facts" not in names, "058 created it, so it goes"
        for survivor in (
            "vehicles", "customers", "diagnostic_sessions",
            "service_history", "cost_events", "customer_bikes",
        ):
            assert survivor in names, f"{survivor} must survive a 058 rollback"

    def test_the_session_rows_survive_the_rollback(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        rollback_to_version(57, db_path=db)
        with get_connection(db) as conn:
            assert conn.execute(
                "SELECT notes FROM diagnostic_sessions WHERE id = 1"
            ).fetchone()[0] == "Leaking oil on left side"


class TestCompileSources:
    def test_the_session_complaint_is_compiled(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        subjects = {f.subject for f in _facts(db)}
        assert "Leaking oil on left side" in subjects

    def test_json_symptoms_are_compiled_individually(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        subjects = {f.subject for f in _facts(db)}
        assert "oil leak" in subjects and "smoke on startup" in subjects

    def test_service_history_carries_its_mileage(self, db):
        compile_vehicle(VEHICLE, db_path=db)
        valve = next(f for f in _facts(db) if f.subject == "valve-adjust")
        assert valve.at_miles == 28000
        assert valve.source == "service-record"

    def test_a_mechanic_correction_compiles_as_mechanic_verified(self, db):
        c = sqlite3.connect(db)
        c.execute(
            "INSERT INTO diagnostic_feedback "
            "(id, session_id, outcome, actual_diagnosis, submitted_at) "
            "VALUES (1, 1, 'incorrect', 'split intake boot', '2026-09-02')"
        )
        c.commit(); c.close()
        compile_vehicle(VEHICLE, db_path=db)
        fact = next(f for f in _facts(db) if f.subject == "split intake boot")
        assert fact.source == "mechanic-verified"
        assert fact.fact_kind == "correction"

    def test_a_low_confidence_vision_finding_is_not_compiled(self, db):
        """A sweep emits low-confidence guesses freely, which is right for a
        ranked list a technician discards and wrong for a store that will be
        recalled as 'what is known'."""
        c = sqlite3.connect(db)
        c.execute(
            "INSERT INTO videos (id, session_id, started_at, duration_ms, width, "
            "height, file_size_bytes, file_path, sha256, analysis_findings, "
            "analyzed_at) VALUES (1, 1, '2026-09-01', 1, 1, 1, 1, '/x', 'h', ?, "
            "'2026-09-01')",
            (json.dumps({"findings": [
                {"description": "confident leak", "confidence": 0.9,
                 "severity": "high"},
                {"description": "maybe a scratch", "confidence": 0.2},
            ]}),),
        )
        c.commit(); c.close()
        compile_vehicle(VEHICLE, db_path=db)
        subjects = {f.subject for f in _facts(db)}
        assert "confident leak" in subjects
        assert "maybe a scratch" not in subjects

    def test_a_vision_finding_is_labelled_model_generated(self, db):
        c = sqlite3.connect(db)
        c.execute(
            "INSERT INTO videos (id, session_id, started_at, duration_ms, width, "
            "height, file_size_bytes, file_path, sha256, analysis_findings, "
            "analyzed_at) VALUES (2, 1, '2026-09-01', 1, 1, 1, 1, '/y', 'h2', ?, "
            "'2026-09-03')",
            (json.dumps({"findings": [
                {"description": "weeping cam cover gasket", "confidence": 0.8},
            ]}),),
        )
        c.commit(); c.close()
        compile_vehicle(VEHICLE, db_path=db)
        fact = next(
            f for f in _facts(db) if f.subject == "weeping cam cover gasket"
        )
        assert fact.source == "model-generated", (
            "a model's observation must not read as an established fact"
        )

    def test_a_deleted_video_is_not_compiled(self, db):
        c = sqlite3.connect(db)
        c.execute(
            "INSERT INTO videos (id, session_id, started_at, duration_ms, width, "
            "height, file_size_bytes, file_path, sha256, analysis_findings, "
            "analyzed_at, deleted_at) VALUES (3, 1, '2026-09-01', 1, 1, 1, 1, "
            "'/z', 'h3', ?, '2026-09-01', '2026-09-02')",
            (json.dumps({"findings": [
                {"description": "deleted finding", "confidence": 0.9},
            ]}),),
        )
        c.commit(); c.close()
        compile_vehicle(VEHICLE, db_path=db)
        assert "deleted finding" not in {f.subject for f in _facts(db)}

    def test_a_missing_source_table_does_not_break_the_compile(self, db):
        with get_connection(db) as conn:
            conn.execute("DROP TABLE service_history")
            conn.commit()
        assert compile_vehicle(VEHICLE, db_path=db) > 0, (
            "the compile degrades to what was there"
        )
