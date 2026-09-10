"""Marque vocabulary and extraction — Phase 244F.

`known_issues.make` is one free-text column doing four different jobs: a marque,
a list of marques, a scope phrase, and in one row a whole sentence of findings.
The cost was concrete — **LiveWire and Damon were not queryable makes at all**,
because every one of their entries lives inside a multi-marque string, so
Phase 243's entire output was unreachable.

This module derives a marque vocabulary from the corpus and extracts, from any
make string, the marques it actually names.

**Nothing here is hard-coded.** The vocabulary is built from the corpus's own
values, and the European set from the seed filenames. A written-out list of
marques would be wrong the next time a phase adds one — the same reason
Phase 244C reads its matching pool from the data.

**Over-extraction is the dangerous direction.** Attaching an entry to a marque
it does not concern puts another machine's documented fault in front of a
mechanic, so matching is whole-word against a closed vocabulary: never
substring, never inferred.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Optional

from motodiag.core.database import get_connection

#: Marker stored for an entry that applies to every make. Not a marque, and
#: never returned by the vocabulary — retrieval treats it as "matches anything".
WILDCARD_MAKE = "*"

#: Scope phrases that are statements about coverage, not marque lists. Read
#: individually at Phase 244F: both are real editorial scopes (vendor tooling
#: tiers, valve-train job types), so they are expanded deliberately rather than
#: split on delimiters, which would have produced nonsense.
ALL_MAKES = "All makes"
ALL_EUROPEAN = "All European makes"

#: Words that mark a fragment as prose rather than a marque, used when
#: harvesting tokens out of delimiter-separated values.
_PROSE_MARKERS = re.compile(r"\b(have|has|none|listed|adjustments|and)\b", re.I)

#: Longest plausible marque name. "Harley-Davidson" is 15 characters; anything
#: much longer is a sentence fragment, not a manufacturer.
_MAX_MARQUE_LEN = 22


def _is_multi(value: str) -> bool:
    """Whether a make string is anything other than a single bare marque."""
    return (
        "," in value
        or " and " in value
        or ";" in value
        or value.startswith("All ")
    )


def _vocabulary_from_values(values: list[str]) -> set[str]:
    """Derive the marque set from raw `make` column values. Pure."""
    vocab = {v for v in values if not _is_multi(v)}
    for value in values:
        if not _is_multi(value) or value.startswith("All "):
            continue
        for part in re.split(r",| and ", value):
            part = part.strip()
            if part and len(part) <= _MAX_MARQUE_LEN and not _PROSE_MARKERS.search(part):
                vocab.add(part)
    return vocab


def vocabulary_from_conn(conn) -> set[str]:
    """Derive the vocabulary from an open connection.

    Phase 244F build: the first version derived it by ``db_path``, defaulting to
    the configured production database. Writing to any other database therefore
    indexed it against production's marque list — the write path and the read
    path could disagree about what a marque is. Deriving from the connection in
    hand makes that impossible.
    """
    values = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT make FROM known_issues WHERE make IS NOT NULL AND make != ''"
        ).fetchall()
    ]
    return _vocabulary_from_values(values)


def marque_vocabulary(db_path: Optional[str] = None) -> set[str]:
    """Derive the set of real marques from the corpus.

    Single-marque values, unioned with the clean tokens split out of the
    list-valued ones. That union is what surfaces **LiveWire and Damon**: they
    have no single-marque row anywhere, so the pool that lets them resolve is
    built out of the very strings that were hiding them.
    """
    try:
        with get_connection(db_path) as conn:
            values = [
                r[0]
                for r in conn.execute(
                    "SELECT DISTINCT make FROM known_issues "
                    "WHERE make IS NOT NULL AND make != ''"
                ).fetchall()
            ]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return set()
        raise

    return _vocabulary_from_values(values)


def european_marques(seed_dir: Optional[Path] = None, db_path: Optional[str] = None,
                     vocabulary: Optional[set[str]] = None) -> set[str]:
    """The marques `All European makes` refers to, derived from seed filenames.

    Files named ``known_issues_european_*`` carry exactly the marques Track K
    treated as European. **Energica falls outside this set** — it is an Italian
    manufacturer but ships in its own seed file, so the derivation does not see
    it. The two entries scoped this way concern valve-train work and ICE
    diagnostic tooling, neither of which applies to it, so the exclusion is
    defensible; it is recorded here rather than papered over because it is an
    artefact of how the set is derived, not a judgment about the marque.
    """
    import json

    if seed_dir is None:
        from motodiag.core.config import SEED_DATA_DIR

        seed_dir = SEED_DATA_DIR / "knowledge"
    vocab = marque_vocabulary(db_path) if vocabulary is None else vocabulary
    out: set[str] = set()
    for path in Path(seed_dir).glob("known_issues_european_*.json"):
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        for entry in entries:
            make = (entry.get("make") or "").strip()
            if make and not _is_multi(make) and (not vocab or make in vocab):
                out.add(make)
    return out


def extract_marques(
    value: Optional[str],
    vocabulary: Optional[set[str]] = None,
    european: Optional[set[str]] = None,
    db_path: Optional[str] = None,
) -> list[str]:
    """Return the marques a make string actually names.

    Order matters — a bare marque is settled before anything is parsed, and the
    two scope phrases are handled before the general scan, because splitting
    them on delimiters would produce nonsense.
    """
    if not value or not value.strip():
        return []
    value = value.strip()
    vocab = marque_vocabulary(db_path) if vocabulary is None else vocabulary

    if value in vocab:
        return [value]
    if value == ALL_MAKES:
        return [WILDCARD_MAKE]
    if value == ALL_EUROPEAN:
        euro = european_marques(db_path=db_path) if european is None else european
        return sorted(euro)

    # Whole-word only. A substring match would attach an entry to a marque the
    # author never named, which is the one failure mode with a mechanic on the
    # other end.
    hits = [
        m
        for m in vocab
        if re.search(r"(?<![A-Za-z])" + re.escape(m) + r"(?![A-Za-z-])", value)
    ]
    # Drop a marque matched only because it sits inside a longer matched one.
    return sorted({h for h in hits if not any(h != o and h in o for o in hits)})


def index_makes_for_issue(conn, issue_id: int, make_value: Optional[str],
                          vocabulary: Optional[set[str]] = None,
                          european: Optional[set[str]] = None) -> int:
    """Write one junction row per marque an entry names. Returns how many.

    Idempotent: the junction carries a UNIQUE pair constraint and this uses
    ``ON CONFLICT DO NOTHING`` — deliberately not ``INSERT OR IGNORE``, which
    would suppress CHECK violations too. That distinction cost Phase 244D a red
    regression and is not being re-learned here.
    """
    if vocabulary is None:
        vocabulary = vocabulary_from_conn(conn)
    if european is None:
        european = european_marques(vocabulary=vocabulary)
    marques = extract_marques(make_value, vocabulary=vocabulary, european=european)
    for marque in marques:
        conn.execute(
            "INSERT INTO known_issue_makes (issue_id, make) VALUES (?, ?) "
            "ON CONFLICT DO NOTHING",
            (issue_id, marque),
        )
    return len(marques)


def rebuild_make_index(conn) -> int:
    """Rebuild the whole junction from the `make` column. Returns rows written.

    **This is the authoritative builder, and it has to be.** The vocabulary is
    derived from the corpus, so it is a function of the WHOLE corpus — a row
    inserted before any standalone `Triumph` entry exists cannot know that
    Triumph is a marque, and will under-index. Incremental indexing on insert is
    a convenience that is correct once the vocabulary is stable; a bulk load must
    rebuild at the end. Found during the Phase 244F build, when a rebuild after
    seeding produced more rows than the inserts had.

    Called as migration 055's ``post_apply``, inside its transaction, and
    available for repair. The `make` column stays the single source of truth —
    this derives from it and never writes back, so a rebuild is always safe and
    the author's text is never rewritten.
    """
    # The vocabulary is derived from the same connection's data rather than a
    # fresh one, so a rebuild inside a transaction sees the rows it is indexing.
    vocab = vocabulary_from_conn(conn)
    euro = european_marques(vocabulary=vocab)

    conn.execute("DELETE FROM known_issue_makes")
    written = 0
    for issue_id, make_value in conn.execute(
        "SELECT id, make FROM known_issues"
    ).fetchall():
        written += index_makes_for_issue(conn, issue_id, make_value, vocab, euro)
    return written


def rebuild_make_index_at(db_path: Optional[str] = None) -> int:
    """Rebuild the junction for a database path. Best-effort before schema 55."""
    try:
        with get_connection(db_path) as conn:
            return rebuild_make_index(conn)
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return 0
        raise
