"""Model vocabulary and extraction — Phase 244I.

The sibling of :mod:`motodiag.knowledge.marques`, and the harder one. `model`
carries the same list-and-prose structure `make` did — 221 of 363 distinct
values — but with a hazard `make` never had: **entries name models in order to
exclude them.**

    390 Adventure, 790 Adventure, 890 Adventure — as distinct from 1290 Super Adventure
    Hypermotard 1100 (not EVO)
    950 and 990 LC8 on the fiche; 1190/1290 fitment unknown, not excluded

Attaching those entries to the machines their authors wrote them to rule out
would be worse than the gap it closes. A wrong *marque* is usually obvious to a
technician; a wrong **model of the right marque** reads as a machine-specific
match and gets acted on.

Phase 244E already makes these rows reachable, labelled `make_other_model`, so
this module buys **precision, not reachability** — a bad extraction has no
upside to trade against. Every rule is therefore conservative: whole-word,
make-scoped, truncated at the first contrast marker, and silent when unsure.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Optional

from motodiag.core.database import get_connection
from motodiag.knowledge.marques import dedupe_contained

#: Wildcard model meaning "the whole make". Never a model in its own right.
WILDCARD_MODEL = "All"

#: Everything from one of these onward names models the entry does NOT cover,
#: or states that coverage is unknown. Extraction reads only what precedes the
#: first match. The list covers the fourteen contrast values in the corpus
#: today; a new phrasing must be added here, and the guards enumerate all
#: fourteen rather than sampling so a gap shows up as a failure.
CONTRAST = re.compile(
    r"\b(?:as against|as distinct from|as opposed to|rather than|unlike"
    r"|excluding|except|versus|vs\.?|not established|not excluded|unknown|not)\b",
    re.I,
)

#: Clause boundaries. Exclusion is scoped to the CLAUSE that carries the marker,
#: not to everything after it — "390 Adventure; 390 Duke not established" puts
#: the excluded model BEFORE the marker, so truncating at the marker would keep
#: it. Found by this phase's own parametrised guard.
_CLAUSE_SPLIT = re.compile(r"\s*(?:;|—|–)\s*")

#: A parenthetical carrying a negation excludes what it contains:
#: "Hypermotard 1100 (not EVO)" covers the 1100 and not the EVO.
_NEGATED_PAREN = re.compile(r"\([^)]*\b(?:not|excluding|except|unlike)\b[^)]*\)", re.I)

#: Words that mark a fragment as description rather than a model name.
_PROSE_WORD = re.compile(
    r"\b(models?|era|built|before|after|onward|fitment|unknown|generally"
    r"|variants?|same|the|with|on|all|and)\b",
    re.I,
)

#: "Harley-Davidson Road Glide Special" is 34 characters, but a model *value*
#: longer than this in the corpus is a description, not a name.
_MAX_MODEL_LEN = 28


def _clean_token(part: str) -> str:
    """Normalise a split fragment into a candidate model name, or "".

    Two defects this exists for, both found in the first build. Bracket and
    quote debris survived truncation, producing the token
    ``"Hypermotard 1100 ("``. And a bare ``"R"`` reached the vocabulary from
    splitting ``"Liquid-cooled R-series boxers, R1200GS and all LC R models"``,
    where a single letter would then match almost any text. A real model name is
    at least two characters — Honda's ``CB`` is the shortest in this corpus.
    """
    part = part.strip().strip("()[]{}\"'“”‘’ ").strip()
    if len(part) < 2 or len(part) > _MAX_MODEL_LEN:
        return ""
    if not re.search(r"[A-Za-z0-9]", part):
        return ""
    # A bare year or year range is a qualifier, not a model name. Splitting
    # "Multistrada 1200 DVT (2015-2017, 2018+)" on the comma yields "2018+",
    # which would otherwise enter the vocabulary as a machine.
    if re.fullmatch(r"(?:19|20)\d{2}\s*[-–—+]?\s*(?:(?:19|20)\d{2})?\+?", part):
        return ""
    # Splitting on "," inside parentheses leaves unbalanced debris such as
    # "1200 DVT (2015-2017" — a year qualifier torn in half, not a model name.
    if part.count("(") != part.count(")") or part.count("[") != part.count("]"):
        return ""
    return part


def is_scope(value: Optional[str]) -> bool:
    """Whether a model value is a scope statement rather than a model."""
    if not value:
        return False
    return value == WILDCARD_MODEL or value.lower().startswith("all ")


def is_plain_model(value: Optional[str]) -> bool:
    """Whether a value is a single model name rather than a list or description."""
    if not value or is_scope(value):
        return False
    if len(value) > _MAX_MODEL_LEN:
        return False
    return not re.search(r",|;|—|–| and |\bversus\b|\bnot\b", value)


def covered_part(value: str) -> str:
    """The portion of a model value that states what IS covered.

    Exclusion is **clause-scoped**, not a truncation. The first implementation
    cut everything from the first contrast marker onward, which fails whenever
    the excluded model precedes it: ``"390 Adventure; 390 Duke not established"``
    kept *390 Duke*, because the marker comes after the name it disqualifies.
    Caught by this phase's own parametrised guard over every contrast phrasing.

    So: negated parentheticals are removed — ``"Hypermotard 1100 (not EVO)"``
    covers the 1100 and not the EVO — then the value is split into clauses and
    any clause carrying a contrast marker is dropped whole.

    ``"1190/1290 fitment unknown, not excluded"`` loses its entire clause, which
    is right: *unknown* is not coverage, and a parser clever enough to read the
    double negative would conclude the opposite.
    """
    value = _NEGATED_PAREN.sub(" ", value)
    clauses = [c for c in _CLAUSE_SPLIT.split(value) if c.strip()]
    kept = [c for c in clauses if not CONTRAST.search(c)]
    return " ; ".join(kept)


def model_vocabulary(db_path: Optional[str] = None) -> dict[str, set[str]]:
    """Model names per make, derived from the corpus.

    Derived the way Phase 244F actually derived marques, which matters more here
    than it did there: building the vocabulary from clean single-value entries
    alone let only **4** of ~298 prose rows gain a precise model, because models
    are an open vocabulary and the ones named in prose mostly appear nowhere as
    a clean value. Augmenting it with clean tokens split out of the list values
    took that to **271**. The vocabulary that repairs the column comes out of
    the strings that broke it.
    """
    try:
        with get_connection(db_path) as conn:
            return vocabulary_from_conn(conn)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return {}
        raise


def vocabulary_from_conn(conn) -> dict[str, set[str]]:
    """Derive the per-make model vocabulary from an open connection.

    Scoped per make deliberately: a model name is only meaningful inside a
    marque, and an unscoped pool would let one make's model match another's text.
    """
    rows = conn.execute(
        "SELECT make, model FROM known_issues "
        "WHERE model IS NOT NULL AND model != ''"
    ).fetchall()

    vocab: dict[str, set[str]] = {}
    for row in rows:
        make = (row[0] if isinstance(row, tuple) else row["make"]) or ""
        model = (row[1] if isinstance(row, tuple) else row["model"]) or ""
        if not make or is_scope(model):
            continue
        if is_plain_model(model):
            vocab.setdefault(make, set()).add(model)
            continue
        for part in re.split(r",|;|—|–|/| and ", covered_part(model)):
            part = _clean_token(part)
            if part and not _PROSE_WORD.search(part):
                vocab.setdefault(make, set()).add(part)
    return vocab


def extract_models(
    make: Optional[str],
    value: Optional[str],
    vocabulary: Optional[dict[str, set[str]]] = None,
    db_path: Optional[str] = None,
) -> list[str]:
    """Return the models a value states the entry covers.

    Order matters: a scope yields nothing, a plain name settles immediately, and
    only then is anything parsed — and only the covered part of it.
    """
    if not value or not value.strip() or is_scope(value):
        return []
    value = value.strip()
    if is_plain_model(value):
        return [value]

    vocab = model_vocabulary(db_path) if vocabulary is None else vocabulary
    pool = vocab.get(make or "", set())
    if not pool:
        return []

    head = covered_part(value)
    hits = [m for m in pool if re.search(
        r"(?<![A-Za-z0-9])" + re.escape(m) + r"(?![A-Za-z0-9])", head)]
    return dedupe_contained(hits, head)


def index_models_for_issue(conn, issue_id: int, make: Optional[str],
                           model_value: Optional[str],
                           vocabulary: Optional[dict[str, set[str]]] = None) -> int:
    """Write one junction row per model an entry covers. Returns how many."""
    if vocabulary is None:
        vocabulary = vocabulary_from_conn(conn)
    models = extract_models(make, model_value, vocabulary=vocabulary)
    for model in models:
        conn.execute(
            "INSERT INTO known_issue_models (issue_id, model) VALUES (?, ?) "
            "ON CONFLICT DO NOTHING",
            (issue_id, model),
        )
    return len(models)


def rebuild_model_index(conn) -> int:
    """Rebuild the whole junction from the `model` column. Returns rows written.

    Authoritative, for the same reason as Phase 244F's make rebuild: the
    vocabulary is a function of the whole corpus, so a row inserted before the
    entry that establishes a model name cannot index against it.
    """
    vocab = vocabulary_from_conn(conn)
    conn.execute("DELETE FROM known_issue_models")
    written = 0
    for row in conn.execute("SELECT id, make, model FROM known_issues").fetchall():
        issue_id = row[0] if isinstance(row, tuple) else row["id"]
        make = row[1] if isinstance(row, tuple) else row["make"]
        model = row[2] if isinstance(row, tuple) else row["model"]
        written += index_models_for_issue(conn, issue_id, make, model, vocab)
    return written


def rebuild_model_index_at(db_path: Optional[str] = None) -> int:
    """Rebuild the junction for a database path. Best-effort before schema 56."""
    try:
        with get_connection(db_path) as conn:
            return rebuild_model_index(conn)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return 0
        raise
