"""Shared 3-tier DTC enrichment helper (Phase 140).

A single canonical path for resolving a DTC string (``"P0115"``,
``"C1234"``, ``"U0100"``…) into a human-friendly metadata dict. Used by
the hardware CLI (:mod:`motodiag.cli.hardware`) and intended to
eventually back :mod:`motodiag.cli.code`'s default lookup path too —
Phase 124's ``code`` command currently has an inline equivalent that a
later cleanup phase (Phase 145) will migrate onto this helper.

The lookup cascades through three tiers, in order:

1. **Make-specific DB row** — an exact ``(code, make)`` match in
   ``dtc_codes``. Returns ``source="db_make"``. Only attempted when a
   ``make_hint`` is supplied.
2. **Generic DB row** — an exact ``code`` match with ``make IS NULL``,
   or any row matching the code if the make-scoped lookup already
   fell through. Returns ``source="db_generic"``.
3. **Classifier heuristic** — :func:`motodiag.engine.fault_codes.classify_code`
   pattern-matches the code format alone (P/C/U/B prefix, Suzuki C-mode,
   etc.). Returns ``source="classifier"`` with ``severity="unknown"`` and
   a generic "Classified by pattern only" description — enough that the
   CLI can still render the code nicely instead of a bare string.

Design notes
------------
- **Always returns a dict.** Even a completely unknown code falls through
  to tier 3, which will at minimum label the format. No caller ever has
  to handle ``None`` — the worst case is an unknown-format classifier
  result with ``description`` set to "Classified by pattern only".
- **The ``source`` field is the primary discriminator.** Callers that
  want to surface DB freshness vs pattern-matched guesses branch on
  ``source``, not on field presence. The hardware CLI uses this to
  colour the Source column differently for each tier.
- **``severity`` from classifier fallback is the string ``"unknown"``**,
  not ``None``. Rich's severity-style map handles unknown severities
  without branching, and unit tests assert the literal ``"unknown"`` so
  nobody silently swaps it for ``None``.
"""

from __future__ import annotations

from typing import Literal, Optional, TypedDict

from motodiag.engine.fault_codes import classify_code
from motodiag.knowledge.dtc_repo import get_dtc


class DTCInfo(TypedDict):
    """Shape of the dict :func:`resolve_dtc_info` returns.

    All fields are always present. ``description`` / ``category`` /
    ``severity`` can be ``None`` only when the DB row has a NULL in
    the corresponding column — the classifier fallback path always
    populates ``description`` and ``severity``.
    """

    code: str
    description: Optional[str]
    category: Optional[str]
    severity: Optional[str]
    source: Literal["db_make", "db_generic", "classifier"]


def resolve_dtc_info(
    code: str,
    make_hint: Optional[str] = None,
    db_path: Optional[str] = None,
) -> DTCInfo:
    """Resolve a DTC code into a human-friendly metadata dict.

    Parameters
    ----------
    code:
        Raw DTC string (e.g. ``"P0115"``, ``"c1234"``). Upper-cased
        internally; the returned ``code`` is also upper-cased.
    make_hint:
        Optional manufacturer hint (``"harley"``, ``"honda"``, …). When
        provided, enables tier 1 (make-specific DB row) before falling
        through to tier 2 (generic). Unknown values degrade silently —
        they just won't match a make-specific row.
    db_path:
        Optional override for the database path. Passed through to
        :func:`motodiag.knowledge.dtc_repo.get_dtc`. Tests use this to
        point at a ``tmp_path`` DB; production callers leave it ``None``
        so the default settings-driven path is used.

    Returns
    -------
    DTCInfo
        Always a populated dict — see module docstring for the 3-tier
        cascade and the ``source`` values that flag which tier won.
    """
    normalized_code = code.strip().upper()

    # Tier 1: make-specific DB row. ``get_dtc`` attempts the make-scoped
    # query first when ``make`` is provided, then falls back to generic
    # and any-match internally. We differentiate tier 1 vs tier 2 by
    # checking the returned row's ``make`` field: a non-NULL make that
    # matches the hint means we got a make-specific row; anything else
    # means the make-scoped query fell through to generic.
    if make_hint:
        row = get_dtc(normalized_code, make=make_hint, db_path=db_path)
        if row is not None:
            row_make = (row.get("make") or "").strip().lower()
            if row_make == make_hint.strip().lower():
                return _row_to_info(row, normalized_code, source="db_make")
            # Make-scoped query fell through to a generic or other-make
            # row — treat it as tier 2 (db_generic) so the Source column
            # accurately reflects what we pulled.
            return _row_to_info(row, normalized_code, source="db_generic")

    # Tier 2: generic DB row. No hint given, so we ask for any match.
    row = get_dtc(normalized_code, make=None, db_path=db_path)
    if row is not None:
        return _row_to_info(row, normalized_code, source="db_generic")

    # Tier 3: classifier heuristic. Always succeeds — the worst case is
    # an unknown-format code, which ``classify_code`` still labels
    # generically ("unknown_system"). We keep that label in
    # ``category`` and synthesize a human description that flags the
    # pattern-only provenance.
    code_format, system = classify_code(normalized_code, make_hint)
    return {
        "code": normalized_code,
        "description": "Classified by pattern only",
        "category": system or code_format,
        "severity": "unknown",
        "source": "classifier",
    }


def _row_to_info(
    row: dict,
    code: str,
    source: Literal["db_make", "db_generic", "classifier"],
) -> DTCInfo:
    """Project a DB row dict onto the :class:`DTCInfo` shape."""
    return {
        "code": code,
        "description": row.get("description"),
        "category": row.get("category"),
        "severity": row.get("severity"),
        "source": source,
    }


__all__ = ["DTCInfo", "resolve_dtc_info"]
