"""Vehicle identity resolution — Phase 244C.

Maps free-text make/model onto the knowledge corpus's own vocabulary.

**Why this exists.** A user recorded a real session, typed the bike in as
"Homda cbrf4i", and every knowledge-base lookup returned zero rows. The corpus
holds 20 entries for the Honda CBR600F4i. Nothing warned anyone, because
nothing in the stack could tell the difference between *this machine has no
documented issues* and *nobody could match this name*. The analysis ran to
completion and answered confidently without them.

**The design commitment is the negative one.** Resolving a machine onto a
neighbouring make would attach another bike's documented faults to it, with a
mechanic acting on the result. That is a correctness defect with a person on
the other end, so the ladder below has an ``unresolved`` rung with teeth: a
fuzzy match must clear both an absolute floor and a margin over the runner-up,
and an abbreviation must match exactly one candidate. ``Ducati`` scores 0.364
against this corpus and resolves to nothing. That is the behaviour, not a gap
in it.

**Vocabulary is read from the corpus**, never hard-coded. An alias table drifts
the moment a phase adds a make — the constant-for-invariant family wearing a
different hat.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Optional

from motodiag.core.database import get_connection

#: Absolute floor for a fuzzy match. Below this, nothing is proposed at all.
FUZZY_FLOOR = 0.78

#: A fuzzy winner must beat the runner-up by this much to be *applied*. Inside
#: the margin the match is real but ambiguous, so it is suggested instead.
FUZZY_MARGIN = 0.15

#: difflib on very short strings is noise — "CB" scores high against half the
#: corpus. Below this length only exact matching is allowed to fire.
MIN_FUZZY_LEN = 4

#: Corpus rows use this as a wildcard model meaning "applies to the whole make".
#: It must never be a resolution target: resolving a model *to* "All" would
#: silently widen a specific question into a make-wide one.
WILDCARD_MODEL = "All"


def _norm(s: Optional[str]) -> str:
    """Lowercase and strip everything that is not alphanumeric.

    Handles the separator noise that makes literal matching fail:
    "Harley-Davidson" / "harley davidson" / "HarleyDavidson" all normalize
    together, as do "CBR-600 F4i" and "cbr600f4i".
    """
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _is_subsequence(needle: str, haystack: str) -> bool:
    """True when every character of ``needle`` appears in ``haystack`` in order.

    This is the rung that catches how people actually write model names:
    "cbrf4i" is not a misspelling of "CBR600F4i", it is the same name with the
    displacement dropped. Subsequence matching catches that; edit distance
    treats the three missing characters as three errors.
    """
    it = iter(haystack)
    return all(c in it for c in needle)


@dataclass
class Resolution:
    """What was given, what it was read as, and how certain that reading is."""

    field_name: str
    given: str
    resolved: Optional[str]
    method: str  # exact | abbreviation | fuzzy | ambiguous | unresolved
    confidence: float
    alternatives: list[str] = field(default_factory=list)

    @property
    def applied(self) -> bool:
        """Whether this resolution is confident enough to act on.

        ``ambiguous`` is deliberately excluded: it means a real match was found
        but more than one candidate fits, which is a question for the user, not
        a decision for the resolver.
        """
        return self.method in ("exact", "abbreviation", "fuzzy") and bool(self.resolved)

    @property
    def changed(self) -> bool:
        """Whether acting on this would alter what the user typed."""
        return self.applied and _norm(self.given) != _norm(self.resolved)


@dataclass
class VehicleIdentity:
    """Resolved make + model, with everything needed to explain the outcome."""

    make: Resolution
    model: Resolution
    corpus_hits: int = 0

    @property
    def changed(self) -> bool:
        return self.make.changed or self.model.changed

    def resolved_make(self) -> str:
        return self.make.resolved if self.make.applied else self.make.given

    def resolved_model(self) -> str:
        return self.model.resolved if self.model.applied else self.model.given

    def corrections(self) -> list[str]:
        """Human-readable list of corrections actually applied."""
        out = []
        for r in (self.make, self.model):
            if r.changed:
                out.append(f"{r.field_name} recorded as {r.given!r}, read as {r.resolved!r}")
        return out

    def suggestions(self) -> list[str]:
        """Matches found but NOT applied, because more than one candidate fit.

        Kept separate from :meth:`corrections` on purpose — the caller must be
        able to tell what was decided from what is being asked.
        """
        out = []
        for r in (self.make, self.model):
            if r.method == "ambiguous" and r.alternatives:
                shown = ", ".join(repr(a) for a in r.alternatives[:4])
                out.append(f"{r.field_name} {r.given!r} is ambiguous — did you mean {shown}?")
        return out


def known_makes(db_path: Optional[str] = None) -> list[str]:
    """Distinct makes present in the corpus. The vocabulary, read from the data."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT make FROM known_issues WHERE make IS NOT NULL AND make != '' ORDER BY make"
        ).fetchall()
    return [r[0] for r in rows]


def known_models(make: Optional[str] = None, db_path: Optional[str] = None) -> list[str]:
    """Distinct models, optionally scoped to a make.

    The wildcard model is filtered out — see :data:`WILDCARD_MODEL`.
    """
    sql = "SELECT DISTINCT model FROM known_issues WHERE model IS NOT NULL AND model != ''"
    params: tuple = ()
    if make:
        sql += " AND make = ?"
        params = (make,)
    with get_connection(db_path) as conn:
        rows = conn.execute(sql + " ORDER BY model", params).fetchall()
    return [r[0] for r in rows if r[0] != WILDCARD_MODEL]


def _resolve_against(field_name: str, given: str, pool: list[str]) -> Resolution:
    """Run the match ladder for one field. Rungs are ordered most-certain first."""
    g = _norm(given)
    if not g or not pool:
        return Resolution(field_name, given or "", None, "unresolved", 0.0)

    # Rung 1 — exact after normalization.
    for cand in pool:
        if _norm(cand) == g:
            return Resolution(field_name, given, cand, "exact", 1.0)

    # Rung 2 — abbreviation. Only when exactly one candidate contains the input
    # as a subsequence; more than one means the input is genuinely ambiguous.
    subs = [c for c in pool if _is_subsequence(g, _norm(c))]
    if len(subs) == 1:
        return Resolution(field_name, given, subs[0], "abbreviation", 0.9)
    if len(subs) > 1:
        return Resolution(field_name, given, None, "ambiguous", 0.5, alternatives=subs)

    # Rung 3 — fuzzy, with a length gate so short strings cannot match by luck.
    if len(g) < MIN_FUZZY_LEN:
        return Resolution(field_name, given, None, "unresolved", 0.0)

    scored = sorted(
        ((difflib.SequenceMatcher(None, g, _norm(c)).ratio(), c) for c in pool),
        key=lambda t: (-t[0], t[1]),
    )
    best_score, best = scored[0]
    if best_score < FUZZY_FLOOR:
        return Resolution(field_name, given, None, "unresolved", best_score)

    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if best_score - runner_up < FUZZY_MARGIN:
        near = [c for s, c in scored if best_score - s < FUZZY_MARGIN]
        return Resolution(field_name, given, None, "ambiguous", best_score, alternatives=near)

    return Resolution(field_name, given, best, "fuzzy", best_score)


def resolve_vehicle(
    make: Optional[str],
    model: Optional[str] = None,
    db_path: Optional[str] = None,
) -> VehicleIdentity:
    """Resolve a free-text make/model pair against the corpus vocabulary.

    The model is resolved *within* the resolved make when one was found, so a
    Kawasaki model cannot match under Honda. When the make is unresolved the
    model pool widens to the whole corpus, but every bar stays where it is.
    """
    make_res = _resolve_against("make", make or "", known_makes(db_path))
    scope = make_res.resolved if make_res.applied else None
    model_res = _resolve_against("model", model or "", known_models(scope, db_path))

    identity = VehicleIdentity(make=make_res, model=model_res)
    identity.corpus_hits = _count_hits(
        identity.resolved_make(), identity.resolved_model(), db_path
    )
    return identity


def _count_hits(make: str, model: str, db_path: Optional[str]) -> int:
    """How many corpus rows the resolved identity actually reaches.

    This is the number that separates the two failures this phase exists for:
    zero after a successful resolution means the corpus really is silent about
    this machine; zero after an unresolved name means nobody could find it.
    """
    if not make:
        return 0
    sql = "SELECT COUNT(*) FROM known_issues WHERE make = ?"
    params: list = [make]
    if model:
        sql += " AND (model = ? OR model = ?)"
        params += [model, WILDCARD_MODEL]
    try:
        with get_connection(db_path) as conn:
            return int(conn.execute(sql, params).fetchone()[0])
    except Exception:
        return 0


def known_issues_for_vehicle(
    make: Optional[str],
    model: Optional[str] = None,
    db_path: Optional[str] = None,
    limit: int = 25,
) -> tuple[VehicleIdentity, list[dict]]:
    """Resolve the identity, then fetch corpus rows for it — deduplicated.

    The one obvious way to get knowledge for a free-text vehicle. Returns the
    identity alongside the rows so a caller can report *why* a result is empty
    rather than only that it is.

    **Deduplicated on the way out** because the corpus currently carries every
    entry ten times over (no UNIQUE constraint, non-idempotent loader — flagged
    separately). Without this, asking for 25 rows can yield two distinct facts
    repeated, which reads to a model as a narrow corpus rather than a duplicated
    one. Dedup here is a retrieval-quality fix, not a substitute for the
    constraint.
    """
    identity = resolve_vehicle(make, model, db_path=db_path)
    resolved_make = identity.resolved_make()
    if not resolved_make or not identity.make.applied:
        return identity, []

    sql = "SELECT * FROM known_issues WHERE make = ?"
    params: list = [resolved_make]
    resolved_model = identity.resolved_model()
    if resolved_model and identity.model.applied:
        sql += " AND (model = ? OR model = ?)"
        params += [resolved_model, WILDCARD_MODEL]

    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
    except Exception:
        return identity, []

    seen: set = set()
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        key = (d.get("make"), d.get("model"), d.get("title"))
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
        if len(out) >= limit:
            break
    return identity, out
