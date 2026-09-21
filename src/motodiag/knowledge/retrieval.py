"""One function decides whether a corpus row may reach a machine — Phase 256.

Phase 255 built an applicability filter and wired it into the retrieval path
it knew about. Asked late which *other* paths read `known_issues` for a
specific machine, it found a second — the video `/ask` endpoint, handing
twenty-five rows straight to a vision model — and a third, `predict_failures`,
with its own retrieval and no filter at all. Phase 256's Step 0 then found a
fourth, `shop/priority_scorer`, whose raw query had been dead since it was
written.

Four doors, found one at a time, each by someone noticing. This module is the
one door.

**`purpose` has no default, deliberately.** A default is how the fourth door
was added without anyone deciding what it was. Passing `purpose` forces the
caller to say which kind of retrieval this is, and the structural guard in
`tests/test_phase256_chokepoint.py` fails the build if anything reaches
`known_issues` for a machine without coming through here.

**What this does not do.** It does not compose, rank or cap —
`compose_prompt_rows` keeps that job and calls this first. It answers one
question: *of these rows, which may this machine see?*
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Literal, Mapping, Optional, Sequence

from motodiag.core.database import get_connection
from motodiag.knowledge.applicability import ApplicabilityError, row_applies
from motodiag.knowledge.transmission import Resolution, resolve_transmission

logger = logging.getLogger(__name__)

#: What a retrieval is for. Required at every call site.
#:
#: * ``prompt``     — rows going to a model as context about one machine
#: * ``prediction`` — rows behind a scored prediction for one machine
#: * ``search``     — a person searching the catalogue, not a machine lookup
Purpose = Literal["prompt", "prediction", "search"]

#: Provenances worth recording. `explicit` and `model-sourced` resolve to a
#: single transmission and withhold only what genuinely does not apply, so
#: they are not a gap in the lookup. The other two are.
_RECORDED_PROVENANCE = frozenset({"unknown", "ambiguous"})


@dataclass(frozen=True)
class FilterResult:
    """What survived, and what it cost."""

    rows: list[dict]
    resolution: Resolution
    withheld: int
    corrupt: int

    @property
    def leaked_nothing(self) -> bool:
        """True when every row here is one this machine may see."""
        return True


def _row_applies_or_excluded(row: Mapping[str, Any], candidates) -> tuple[bool, bool]:
    """(applies, was_corrupt).

    **F122, and the option Phase 255 did not consider.** That phase weighed
    two ways to handle a row whose `applicability` cannot be parsed —
    load it as unscoped, or raise — and chose to raise, because loading a
    typo as unscoped puts it back in front of every machine. The cost was
    that one bad row stopped diagnosis for everyone, which is what shipped.

    The third option follows from this axis's own principle, *missing beats
    misleading*: **exclude the row.** Never unscoped, so a typo cannot
    reintroduce the defect. Never fatal, so one bad row cannot take down the
    product. The row id is logged and the count is persisted, so a corrupt
    row is loud in the record rather than loud in the user's face.

    Rejection stays **loud at write time** — `add_known_issue` still raises,
    and so does seed load. The asymmetry is deliberate: at write time nothing
    is lost by refusing; at read time refusing costs the technician an answer
    they could have had.
    """
    try:
        return row_applies(row, "transmission", candidates), False
    except ApplicabilityError as exc:
        logger.error(
            "retrieval: excluding known_issues row id=%r — unreadable "
            "applicability: %s", row.get("id"), exc,
        )
        return False, True


def rows_for_machine(
    rows: Sequence[Mapping[str, Any]],
    *,
    make: str,
    model: str,
    purpose: Purpose,
    year: Optional[int] = None,
    powertrain: Optional[str] = None,
    transmission: Optional[str] = None,
    db_path: Optional[str] = None,
    record: bool = True,
) -> FilterResult:
    """The chokepoint. Every door calls this.

    Resolves the machine once, drops the rows it may not see, and records
    what that cost. Returns the survivors plus the resolution, so a caller
    that wants to explain itself can.
    """
    resolution = resolve_transmission(
        make, model, explicit=transmission, powertrain=powertrain,
    )
    kept: list[dict] = []
    corrupt = 0
    for row in rows:
        applies, was_corrupt = _row_applies_or_excluded(row, resolution.candidates)
        corrupt += was_corrupt
        if applies:
            kept.append(dict(row))
    withheld = len(rows) - len(kept)

    if record and (withheld or corrupt):
        _record_withheld(
            make=make, model=model, provenance=resolution.provenance,
            purpose=purpose, rows_withheld=withheld, corrupt_rows=corrupt,
            db_path=db_path,
        )
    if withheld or corrupt:
        logger.info(
            "retrieval[%s]: %s %s — withheld %d row(s), %d corrupt; provenance=%s",
            purpose, make, model, withheld, corrupt, resolution.provenance,
        )
    return FilterResult(rows=kept, resolution=resolution,
                        withheld=withheld, corrupt=corrupt)


def _record_withheld(
    *, make: str, model: str, provenance: str, purpose: str,
    rows_withheld: int, corrupt_rows: int, db_path: Optional[str],
) -> None:
    """Persist what this retrieval withheld. Best-effort, never fatal.

    Phase 255 kept this in process memory, which made it unreadable by
    anyone: every CLI command is a fresh process, so the aggregate was
    always zero by the time anybody could look. Phase 209B's orphan guard
    recorded the two accessors and said "retire these or wire that route".
    This is wiring the route.

    **Only `unknown` and `ambiguous` are recorded.** A machine whose
    transmission is known withholds only rows that genuinely do not apply to
    it, which is the filter working rather than a gap. The rows here are the
    ones a sourced lookup entry would have saved — so **this table is the
    lookup's to-do list**, ordered by what each missing entry costs.

    A failure to record must never break a retrieval: the count is
    diagnostics, the rows are the product.
    """
    if provenance not in _RECORDED_PROVENANCE:
        return
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_connection(db_path) as conn:
            conn.execute(
                """INSERT INTO retrieval_withheld
                     (make, model, provenance, purpose, rows_withheld,
                      retrievals, corrupt_rows, first_seen, last_seen)
                   VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                   ON CONFLICT(make, model, provenance, purpose) DO UPDATE SET
                     rows_withheld = rows_withheld + excluded.rows_withheld,
                     retrievals    = retrievals + 1,
                     corrupt_rows  = corrupt_rows + excluded.corrupt_rows,
                     last_seen     = excluded.last_seen""",
                (str(make or ""), str(model or ""), provenance, purpose,
                 int(rows_withheld), int(corrupt_rows), now, now),
            )
    except sqlite3.OperationalError as exc:
        # A database below schema 64 has no table. That is not an error
        # worth failing a retrieval over -- but anything else is unexpected
        # and is logged rather than swallowed, because a counter that
        # silently stops counting is how Phase 255's cost went unmeasured.
        if "no such table" not in str(exc).lower():
            logger.warning("retrieval: could not record withheld rows: %s", exc)
    except Exception as exc:  # pragma: no cover - defensive, logged not hidden
        logger.warning("retrieval: could not record withheld rows: %s", exc)


def withheld_report(
    db_path: Optional[str] = None, limit: int = 50,
) -> list[dict]:
    """The lookup's to-do list: machines that lost rows, worst first."""
    try:
        with get_connection(db_path) as conn:
            return [dict(r) for r in conn.execute(
                """SELECT make, model, provenance, purpose, rows_withheld,
                          retrievals, corrupt_rows, first_seen, last_seen
                     FROM retrieval_withheld
                    ORDER BY rows_withheld DESC, retrievals DESC
                    LIMIT ?""", (int(limit),),
            ).fetchall()]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return []
        raise
