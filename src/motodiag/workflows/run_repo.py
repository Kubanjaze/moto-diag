"""Saved workflow runs: a template's checklist worked on one bike.

Phase 357 (F165). Migration 073's `workflow_runs` and
`workflow_run_items`. A run is started with one row per checklist item,
copying the item's number, title and required flag, so it reads back as
it was worked even if the template changes later. Each answer is written
as it is given; a finished run is read-only.
"""

from __future__ import annotations

from motodiag.core.database import get_connection

RESULTS = ("pass", "fail", "skipped")


class RunRefused(ValueError):
    """A write the run's state does not allow; the message says why."""


def start_run(
    template: dict,
    items: list[dict],
    vehicle_id: int,
    powertrain: str,
    work_order_id: int | None = None,
    db_path: str | None = None,
) -> int:
    """Save a new run and one unanswered row per item. Returns the run id."""
    with get_connection(db_path) as conn:
        run_id = conn.execute(
            """INSERT INTO workflow_runs
               (template_id, vehicle_id, work_order_id, powertrain)
               VALUES (?, ?, ?, ?)""",
            (template["id"], vehicle_id, work_order_id, powertrain),
        ).lastrowid
        conn.executemany(
            """INSERT INTO workflow_run_items
               (run_id, checklist_item_id, sequence_number, title, required)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (run_id, item["id"], item["sequence_number"], item["title"],
                 1 if item["required"] else 0)
                for item in items
            ],
        )
        return run_id


def get_run(run_id: int, db_path: str | None = None) -> dict | None:
    """The run with its template's slug and name and its bike's label."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """SELECT r.*, t.slug AS template_slug, t.name AS template_name,
                      v.year AS vehicle_year, v.make AS vehicle_make,
                      v.model AS vehicle_model
               FROM workflow_runs r
               JOIN workflow_templates t ON t.id = r.template_id
               JOIN vehicles v ON v.id = r.vehicle_id
               WHERE r.id = ?""",
            (run_id,),
        ).fetchone()
        return dict(row) if row else None


def get_run_items(run_id: int, db_path: str | None = None) -> list[dict]:
    """The run's item rows in number order, each with its checklist item's
    current text (None when the item has since been deleted)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT ri.*, ci.description, ci.instruction_text,
                      ci.expected_pass, ci.expected_fail,
                      ci.diagnosis_if_fail, ci.tools_needed,
                      ci.estimated_minutes
               FROM workflow_run_items ri
               LEFT JOIN checklist_items ci ON ci.id = ri.checklist_item_id
               WHERE ri.run_id = ?
               ORDER BY ri.sequence_number""",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_runs(
    vehicle_id: int | None = None,
    work_order_id: int | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Runs, newest first, optionally for one bike or one work order."""
    query = """
        SELECT r.*, t.slug AS template_slug,
               v.year AS vehicle_year, v.make AS vehicle_make,
               v.model AS vehicle_model,
               SUM(ri.result IS NOT NULL) AS answered,
               COUNT(ri.id) AS total
        FROM workflow_runs r
        JOIN workflow_templates t ON t.id = r.template_id
        JOIN vehicles v ON v.id = r.vehicle_id
        LEFT JOIN workflow_run_items ri ON ri.run_id = r.id
    """
    where, params = [], []
    if vehicle_id is not None:
        where.append("r.vehicle_id = ?")
        params.append(vehicle_id)
    if work_order_id is not None:
        where.append("r.work_order_id = ?")
        params.append(work_order_id)
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " GROUP BY r.id ORDER BY r.started_at DESC, r.id DESC"
    with get_connection(db_path) as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def record_result(
    run_id: int,
    sequence_number: int,
    result: str,
    notes: str | None = None,
    diagnosis: str | None = None,
    db_path: str | None = None,
) -> None:
    """Set one item's answer. A later answer replaces an earlier one until
    the run is finished. `diagnosis` is kept only on a fail."""
    if result not in RESULTS:
        raise RunRefused(f"A result is one of {', '.join(RESULTS)}, not {result!r}.")
    with get_connection(db_path) as conn:
        run = conn.execute(
            "SELECT status FROM workflow_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if run is None:
            raise RunRefused(f"No saved run #{run_id}.")
        if run["status"] == "complete":
            raise RunRefused(f"Run #{run_id} is finished; its answers can no longer change.")
        item = conn.execute(
            """SELECT required FROM workflow_run_items
               WHERE run_id = ? AND sequence_number = ?""",
            (run_id, sequence_number),
        ).fetchone()
        if item is None:
            raise RunRefused(f"Run #{run_id} has no item {sequence_number}.")
        if result == "skipped" and item["required"]:
            raise RunRefused(
                f"Item {sequence_number} of run #{run_id} is required: pass or fail, not skip."
            )
        conn.execute(
            """UPDATE workflow_run_items
               SET result = ?, notes = ?, diagnosis = ?,
                   answered_at = CURRENT_TIMESTAMP
               WHERE run_id = ? AND sequence_number = ?""",
            (result, notes, diagnosis if result == "fail" else None,
             run_id, sequence_number),
        )


def finish_run(run_id: int, db_path: str | None = None) -> None:
    """Mark a run complete. Refused while any item is unanswered."""
    with get_connection(db_path) as conn:
        run = conn.execute(
            "SELECT status FROM workflow_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if run is None:
            raise RunRefused(f"No saved run #{run_id}.")
        if run["status"] == "complete":
            raise RunRefused(f"Run #{run_id} is already finished.")
        open_items = [
            r["sequence_number"] for r in conn.execute(
                """SELECT sequence_number FROM workflow_run_items
                   WHERE run_id = ? AND result IS NULL
                   ORDER BY sequence_number""",
                (run_id,),
            )
        ]
        if open_items:
            raise RunRefused(
                f"Run #{run_id} has unanswered items: "
                f"{', '.join(map(str, open_items))}."
            )
        conn.execute(
            """UPDATE workflow_runs
               SET status = 'complete', finished_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (run_id,),
        )
