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
from motodiag.knowledge.marque_families import same_family
from motodiag.knowledge.marques import (
    dedupe_contained,
    european_marques,
    extract_marques,
)
from motodiag.knowledge.marques import (
    vocabulary_from_conn as marque_vocabulary_from_conn,
)

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


#: A slash that belongs to the model's own name rather than separating two
#: models. Phase 250C: `/` is a list separator in this corpus — "R1200/R1250",
#: "F650/F700", "450/500 EXC-F", "Zero S/DS", "Ego/Eva" all enumerate two
#: machines — but it is also part of a designation, and Zero writes four of
#: them: SR/F, SR/S, SR/FX, DSR/X. Splitting those produced "SR" and "F", so
#: `SR/F` matched nothing and a Zero SR/F resolved to no model at all.
#:
#: The two cases separate cleanly on the corpus's own evidence: in every
#: enumeration the right-hand fragment is a full designation of three
#: characters or more (1250, EXC-F, Eva, M50, MT-09), and in every compound
#: name it is one or two (F, S, FX, X). The left-hand side must be at least
#: two characters, which is what keeps "S/DS" — Zero S and Zero DS — a list.
_COMPOUND_SLASH = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z0-9]{2,})/([A-Za-z0-9]{1,2})(?![A-Za-z0-9])"
)

#: Stands in for a slash that survives the split, and is put back after it.
_SLASH_HOLD = "\x00"


def _model_tokens(model: str) -> list[str]:
    """The model names one value states, before any attribution."""
    if is_scope(model):
        return []
    if is_plain_model(model):
        return [model]
    held = _COMPOUND_SLASH.sub(
        lambda m: f"{m.group(1)}{_SLASH_HOLD}{m.group(2)}", covered_part(model))
    out: list[str] = []
    for part in re.split(r",|;|—|–|/| and ", held):
        part = _clean_token(part.replace(_SLASH_HOLD, "/"))
        if part and not _PROSE_WORD.search(part):
            out.append(part)
    return out


def _marque_named_by(token: str, marque_vocab: set[str]) -> set[str]:
    """The marques a model token names, whole-word."""
    return {
        marque for marque in marque_vocab
        if re.search(r"(?<![A-Za-z])" + re.escape(marque) + r"(?![A-Za-z])",
                     token, re.IGNORECASE)
    }


def vocabulary_from_conn(conn) -> dict[str, set[str]]:
    """Derive the per-marque model vocabulary from an open connection.

    Scoped per marque deliberately: a model name is only meaningful inside a
    marque, and an unscoped pool would let one make's model match another's text.

    Phase 250C. This used to key on the **raw** make column, which meant a row
    reading "Zero, Harley-Davidson, LiveWire, Energica" filed its models under
    that whole string and under no marque at all. 501 of the corpus's 764
    models were reachable; LiveWire could resolve **none** of its 23 and Damon
    none of its 10, so the model tier could never fire for them and every such
    query fell back to make-wide content. Exactly the defect Phase 244F fixed
    for makes and 244I fixed for model *values*, one level down in the keys.

    Keying alone is not enough, because the junction it would copy is not
    clean: a row comparing six marques names every model against all six, so
    "BMW S 1000 R" would enter Aprilia's matching pool. So each token is
    attributed, in three rungs:

    1. A model seen on a **single-marque** row belongs to that marque. This is
       what catches "Brutale" and "F4" — MV Agusta machines that name no marque.
    2. A token that **names** a marque belongs to it, unless the two marques
       are the same family (`marque_families`): "LiveWire" is a marque *and* a
       Harley-Davidson machine.
    3. Otherwise the row's marques all take it.

    A token that is exactly a marque name is not a model and is dropped: the
    "All European makes" row's model column is a list of marques.

    Measured on the shipped corpus: 638 models against 501, one token in a
    marque's pool that another marque owns, and 644 of the junction's 764
    (marque, model) pairs resolving where 511 did.
    """
    rows = conn.execute(
        "SELECT make, model FROM known_issues "
        "WHERE model IS NOT NULL AND model != ''"
    ).fetchall()

    marque_vocab = marque_vocabulary_from_conn(conn)
    european = european_marques(vocabulary=marque_vocab)
    pairs: list[tuple[list[str], list[str]]] = []
    for row in rows:
        make = (row[0] if isinstance(row, tuple) else row["make"]) or ""
        model = (row[1] if isinstance(row, tuple) else row["model"]) or ""
        if not make:
            continue
        tokens = _model_tokens(model)
        if not tokens:
            continue
        marques = extract_marques(make, vocabulary=marque_vocab, european=european)
        if not marques:
            continue
        pairs.append((marques, tokens))

    # Rung 1, first, because it is the only unambiguous evidence there is.
    vocab: dict[str, set[str]] = {}
    owner: dict[str, set[str]] = {}
    for marques, tokens in pairs:
        if len(marques) != 1:
            continue
        for token in tokens:
            vocab.setdefault(marques[0], set()).add(token)
            owner.setdefault(token.lower(), set()).add(marques[0])

    for marques, tokens in pairs:
        if len(marques) == 1:
            continue
        for token in tokens:
            named = _marque_named_by(token, marque_vocab)
            claim = (named | owner.get(token.lower(), set())) & set(marques)
            if claim:
                targets = {
                    marque for marque in marques
                    if any(same_family(marque, claimed) for claimed in claim)
                }
            else:
                targets = set(marques)
            for marque in targets:
                vocab.setdefault(marque, set()).add(token)

    # A marque name is not a model, wherever it came from.
    for marque, names in vocab.items():
        names -= {m for m in list(names) if m in marque_vocab}
    return {marque: names for marque, names in vocab.items() if names}


def extract_models(
    make: Optional[str],
    value: Optional[str],
    vocabulary: Optional[dict[str, set[str]]] = None,
    db_path: Optional[str] = None,
    marques: Optional[set[str]] = None,
    european: Optional[set[str]] = None,
) -> list[str]:
    """Return the models a value states the entry covers.

    Order matters: a scope yields nothing, a plain name settles immediately, and
    only then is anything parsed — and only the covered part of it.

    Phase 250C: the pool is the union over every marque the make string names,
    not the entry for the raw string. The vocabulary is keyed by marque now, so
    a row reading "Harley-Davidson, LiveWire" looks up both and gets both
    marques' models; before the change it looked up that whole string, which
    after the re-keying would be a key that exists nowhere.

    `marques` and `european` come after `db_path` deliberately: four callers
    pass `vocabulary` positionally as the third argument.
    """
    if not value or not value.strip() or is_scope(value):
        return []
    value = value.strip()
    if is_plain_model(value):
        return [value]

    vocab = model_vocabulary(db_path) if vocabulary is None else vocabulary
    if marques is None:
        marques = set(vocab)
    names = extract_marques(make or "", vocabulary=marques, european=european)
    pool: set[str] = set()
    for marque in names:
        pool |= vocab.get(marque, set())
    if not pool:
        return []

    head = covered_part(value)
    hits = [m for m in pool if re.search(
        r"(?<![A-Za-z0-9])" + re.escape(m) + r"(?![A-Za-z0-9])", head)]
    return dedupe_contained(hits, head)


def index_models_for_issue(conn, issue_id: int, make: Optional[str],
                           model_value: Optional[str],
                           vocabulary: Optional[dict[str, set[str]]] = None,
                           marques: Optional[set[str]] = None,
                           european: Optional[set[str]] = None) -> int:
    """Write one junction row per model an entry covers. Returns how many.

    Phase 250C: the marque vocabulary is derived from the connection in hand,
    never from a db_path. `marques.py` records what the alternative cost —
    deriving by path where a connection was open once let "the write path and
    the read path disagree about what a marque is".
    """
    if vocabulary is None:
        vocabulary = vocabulary_from_conn(conn)
    if marques is None:
        marques = marque_vocabulary_from_conn(conn)
    if european is None:
        european = european_marques(vocabulary=marques)
    models = extract_models(make, model_value, vocabulary=vocabulary,
                            marques=marques, european=european)
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
    marques = marque_vocabulary_from_conn(conn)
    european = european_marques(vocabulary=marques)
    conn.execute("DELETE FROM known_issue_models")
    written = 0
    for row in conn.execute("SELECT id, make, model FROM known_issues").fetchall():
        issue_id = row[0] if isinstance(row, tuple) else row["id"]
        make = row[1] if isinstance(row, tuple) else row["make"]
        model = row[2] if isinstance(row, tuple) else row["model"]
        written += index_models_for_issue(conn, issue_id, make, model, vocab,
                                          marques=marques, european=european)
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
