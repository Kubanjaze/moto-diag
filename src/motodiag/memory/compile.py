"""Phase 244M — turn recorded interactions into retrievable facts.

The compile pass reads the tables the product already writes and emits
:class:`MemoryFact` rows. It is idempotent: running it twice inserts nothing
the second time, because every fact's identity is a hash of the row it came
from.

Sources, and what each is worth:

============================  =====================  =========================
table                          fact kinds             source label
============================  =====================  =========================
``diagnostic_sessions``       complaint, correction  customer-reported /
                                                     mechanic-verified
``videos``                    observation            model-generated
``work_orders``               repair                 service-record
``work_order_parts``          part-replaced          service-record
``service_history``           repair                 service-record
``diagnostic_feedback``       correction             mechanic-verified
============================  =====================  =========================

``diagnostic_feedback`` is the one that matters most and the one with no rows
today: a mechanic writing "the code said lean, it was actually a split intake
boot" is the shop's own labour and the most valuable thing in here. It is wired
anyway, so value accrues from the first correction rather than waiting for a
later phase to come back for it.
"""

from __future__ import annotations

import json
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.memory.facts import MemoryFact, insert_facts

# A finding below this confidence is not compiled into memory at all. A vision
# sweep emits low-confidence guesses freely -- that is appropriate for a
# ranked list a technician reads and discards, and inappropriate for a store
# that will later be recalled as "what is known about this machine".
_MIN_OBSERVATION_CONFIDENCE = 0.5


def _date_of(value: Optional[str]) -> str:
    """Normalise a timestamp to a date, or return '' if there isn't one.

    Facts are dated to the day. Compiling a repair as
    ``2026-04-18T14:22:07.113`` implies a precision the underlying record does
    not have, and makes two facts about the same visit sort against each other
    on milliseconds.
    """
    if not value:
        return ""
    return str(value)[:10]


def _rows(conn, sql: str, params: tuple = ()) -> list[tuple]:
    try:
        return conn.execute(sql, params).fetchall()
    except Exception:
        # A source table that does not exist in this database is not an error.
        # The compile pass runs against installs at different schema versions
        # and must degrade to "compiled what was there".
        return []


def _session_facts(conn, vehicle_id: int) -> list[MemoryFact]:
    facts: list[MemoryFact] = []
    for row in _rows(
        conn,
        "SELECT id, notes, symptoms, diagnosis, created_at "
        "FROM diagnostic_sessions WHERE vehicle_id = ?",
        (vehicle_id,),
    ):
        sid, notes, symptoms, diagnosis, created_at = row
        when = _date_of(created_at)

        # The technician's free-text complaint. Phase 244B found this field
        # was read by nothing, while holding the only record of what the
        # customer actually reported.
        if notes and notes.strip():
            facts.append(
                MemoryFact(
                    vehicle_id=vehicle_id,
                    fact_kind="complaint",
                    subject=notes.strip(),
                    source="customer-reported",
                    origin_table="diagnostic_sessions",
                    origin_id=sid,
                    established_at=when,
                )
            )

        parsed = symptoms
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except (ValueError, TypeError):
                parsed = [parsed] if parsed.strip() else []
        for symptom in parsed or []:
            text = str(symptom).strip()
            if text:
                facts.append(
                    MemoryFact(
                        vehicle_id=vehicle_id,
                        fact_kind="complaint",
                        subject=text,
                        source="customer-reported",
                        origin_table="diagnostic_sessions",
                        origin_id=sid,
                        established_at=when,
                    )
                )

        if diagnosis and str(diagnosis).strip():
            facts.append(
                MemoryFact(
                    vehicle_id=vehicle_id,
                    fact_kind="correction",
                    subject=str(diagnosis).strip(),
                    source="mechanic-verified",
                    origin_table="diagnostic_sessions",
                    origin_id=sid,
                    established_at=when,
                )
            )
    return facts


def _video_facts(conn, vehicle_id: int) -> list[MemoryFact]:
    """Vision findings, labelled `model-generated` because that is what they are.

    The provenance label is not decoration. Phase 244M's research measured that
    citations raise trust *even when random*, and that only about a tenth of
    cited answers are ever checked -- so a fact that reads as established when
    a model guessed it buys unearned confidence from nearly everyone. These
    rows say where they came from and are ranked below anything a mechanic
    confirmed.
    """
    facts: list[MemoryFact] = []
    for video_id, findings_json, analyzed_at in _rows(
        conn,
        "SELECT v.id, v.analysis_findings, v.analyzed_at "
        "FROM videos v JOIN diagnostic_sessions s ON v.session_id = s.id "
        "WHERE s.vehicle_id = ? AND v.analysis_findings IS NOT NULL "
        "AND v.deleted_at IS NULL",
        (vehicle_id,),
    ):
        try:
            blob = json.loads(findings_json)
        except (ValueError, TypeError):
            continue
        if not isinstance(blob, dict):
            continue

        when = _date_of(analyzed_at)
        for finding in blob.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            confidence = finding.get("confidence")
            if isinstance(confidence, (int, float)) and (
                confidence < _MIN_OBSERVATION_CONFIDENCE
            ):
                continue
            text = str(
                finding.get("description") or finding.get("summary") or ""
            ).strip()
            if not text:
                continue
            facts.append(
                MemoryFact(
                    vehicle_id=vehicle_id,
                    fact_kind="observation",
                    subject=text,
                    value=str(finding.get("severity") or ""),
                    source="model-generated",
                    origin_table="videos",
                    origin_id=video_id,
                    established_at=when,
                )
            )
    return facts


def _work_order_facts(conn, vehicle_id: int) -> list[MemoryFact]:
    facts: list[MemoryFact] = []
    for wid, title, description, completed_at, created_at in _rows(
        conn,
        "SELECT id, title, description, completed_at, created_at "
        "FROM work_orders WHERE vehicle_id = ?",
        (vehicle_id,),
    ):
        if not title or not str(title).strip():
            continue
        facts.append(
            MemoryFact(
                vehicle_id=vehicle_id,
                fact_kind="repair",
                subject=str(title).strip(),
                value=str(description or "").strip(),
                source="service-record",
                origin_table="work_orders",
                origin_id=wid,
                # A work order that is not finished is not a repair that
                # happened; it is dated by when it opened, and the distinction
                # matters to "when was it last worked on".
                established_at=_date_of(completed_at or created_at),
            )
        )

        for part_row in _rows(
            conn,
            "SELECT wop.id, p.name, wop.quantity, wop.installed_at "
            "FROM work_order_parts wop LEFT JOIN parts p ON wop.part_id = p.id "
            "WHERE wop.work_order_id = ?",
            (wid,),
        ):
            wop_id, name, quantity, installed_at = part_row
            if not name:
                continue
            facts.append(
                MemoryFact(
                    vehicle_id=vehicle_id,
                    fact_kind="part-replaced",
                    subject=str(name).strip(),
                    value=f"qty {quantity}" if quantity else "",
                    source="service-record",
                    origin_table="work_order_parts",
                    origin_id=wop_id,
                    established_at=_date_of(installed_at or completed_at or created_at),
                )
            )
    return facts


def _service_history_facts(conn, vehicle_id: int) -> list[MemoryFact]:
    facts: list[MemoryFact] = []
    for hid, event_type, at_miles, at_date, notes in _rows(
        conn,
        "SELECT id, event_type, at_miles, at_date, notes "
        "FROM service_history WHERE vehicle_id = ?",
        (vehicle_id,),
    ):
        facts.append(
            MemoryFact(
                vehicle_id=vehicle_id,
                fact_kind="repair",
                subject=str(event_type),
                value=str(notes or "").strip(),
                source="service-record",
                origin_table="service_history",
                origin_id=hid,
                at_miles=at_miles,
                established_at=_date_of(at_date),
            )
        )
    return facts


def _feedback_facts(conn, vehicle_id: int) -> list[MemoryFact]:
    """Mechanic corrections -- the shop's own labour, and the crown jewels.

    Zero rows today. Wired regardless: this is the input that makes the memory
    worth having, and the compile path existing means the first correction a
    mechanic writes lands in memory rather than waiting for a later phase.
    """
    facts: list[MemoryFact] = []
    for fid, actual, fix, notes, submitted_at in _rows(
        conn,
        "SELECT f.id, f.actual_diagnosis, f.actual_fix, f.mechanic_notes, "
        "       f.submitted_at "
        "FROM diagnostic_feedback f "
        "JOIN diagnostic_sessions s ON f.session_id = s.id "
        "WHERE s.vehicle_id = ?",
        (vehicle_id,),
    ):
        when = _date_of(submitted_at)
        for text in (actual, fix, notes):
            if text and str(text).strip():
                facts.append(
                    MemoryFact(
                        vehicle_id=vehicle_id,
                        fact_kind="correction",
                        subject=str(text).strip(),
                        source="mechanic-verified",
                        origin_table="diagnostic_feedback",
                        origin_id=fid,
                        established_at=when,
                    )
                )
    return facts


def compile_vehicle(vehicle_id: int, db_path: Optional[str] = None) -> int:
    """Compile one machine's interactions into facts. Returns ROWS INSERTED."""
    with get_connection(db_path) as conn:
        facts = (
            _session_facts(conn, vehicle_id)
            + _video_facts(conn, vehicle_id)
            + _work_order_facts(conn, vehicle_id)
            + _service_history_facts(conn, vehicle_id)
            + _feedback_facts(conn, vehicle_id)
        )
    return insert_facts(facts, db_path=db_path)


def compile_all(db_path: Optional[str] = None) -> dict[int, int]:
    """Compile every machine. Returns {vehicle_id: rows inserted}."""
    with get_connection(db_path) as conn:
        vehicle_ids = [r[0] for r in conn.execute("SELECT id FROM vehicles")]
    return {vid: compile_vehicle(vid, db_path=db_path) for vid in vehicle_ids}
