"""Canonical severity ranking — one mapping, used by every ordered query.

Phase 240C. Six query paths ordered results by ``severity DESC`` on a TEXT
column. SQLite sorts that lexicographically, and the four values alphabetise
into almost exactly the wrong order::

    ORDER BY severity DESC  ->  medium, low, high, critical

so ``critical`` came back **last** everywhere. On the knowledge paths a
``medium``-rated stale entry outranked the ``critical``-rated entry written to
correct it — the mechanism behind Track K's contradiction pattern. On the
recall paths an open-recall list put the critical campaigns at the bottom.

The mapping itself was never in doubt: it already existed five times over in
correct form (``advanced/predictor.py``, ``advanced/tsb_repo.py``,
``engine/correlation.py``, and the inline SQL ``CASE`` in
``shop/issue_repo.py``). What was missing was one place to keep it.

``SEVERITY_RANK_SQL`` is shared between the queries and migration 053's
expression index deliberately: SQLite only uses an expression index when the
query's ``ORDER BY`` expression matches the indexed one, so writing the
expression twice would silently cost the optimisation.
"""

from __future__ import annotations

#: Worst first. ``ELSE 0`` in the SQL form matches this dict's ``.get(x, 0)``:
#: an unrecognised or NULL severity ranks below ``low``. Neither
#: ``known_issues.severity`` nor ``recalls.severity`` carries a CHECK
#: constraint, so an unrecognised value is possible.
SEVERITY_RANK: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

#: The same mapping as a SQL expression, for ``ORDER BY``.
#: Built from SEVERITY_RANK so the two cannot drift.
SEVERITY_RANK_SQL: str = (
    "CASE severity "
    + " ".join(f"WHEN '{k}' THEN {v}" for k, v in SEVERITY_RANK.items())
    + " ELSE 0 END"
)


def severity_rank_sql(column: str = "severity") -> str:
    """``SEVERITY_RANK_SQL`` against a qualified column (e.g. ``r.severity``).

    Joined queries need the table alias; the bare constant is the unqualified
    form used by single-table queries and by migration 053's index, which
    cannot carry an alias.
    """
    return SEVERITY_RANK_SQL.replace("CASE severity ", f"CASE {column} ", 1)
