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
from functools import lru_cache
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

#: A parenthetical qualifier is not part of the name being judged:
#: "R-series (airhead)" is judged on "R-series".
_PAREN_QUALIFIER = re.compile(r"\([^)]*\)")

#: A designation code — the thing that makes a fragment a machine name rather
#: than a description. "PCX", "CBR1000RR", "XC155", "LC8", "R1200", "1290",
#: "2V", "V4".
_CODE_TOKEN = re.compile(
    r"\b(?:[A-Z]{1,4}\d{2,4}[A-Za-z]?|\d{3,4}|[0-9]V|V\d)\b"
)


def admits_as_model(value: str) -> bool:
    """Whether a fragment is shaped like a model name. A POSITIVE gate.

    Phase 255C. Every filter above this one is a blacklist — `CONTRAST`,
    `_PROSE_WORD`, `_NEGATED_PAREN`, `is_scope` — and each defect found in
    the junction was a gap in one of them. Four gaps were found in a single
    pass, which is the signature of the wrong shape of check rather than of
    four oversights: a blacklist admits everything nobody thought to name.

    So this asks the other question. A fragment is admitted when **every
    word looks like part of a designation** — capitalised, all-caps, numeric,
    or alphanumeric-mixed — or when the fragment carries a designation code
    even though some word is lowercase. A fragment with a bare lowercase word
    and no code is prose.

    Admitted, and these are the negative control: `PCX 150`, `F-series`,
    `R-series (airhead)`, `250`, `125`, `Brutale 800`, `Super Cub C125`,
    `390 Adventure R`, `XC155 / SMAX`, `S 1000 RR by type code`, and every
    engine-family designation the corpus uses.

    Rejected: `Electric motorcycles`, `as this corpus names them`, `BMS logs`,
    `year`, `location`, `per handbook`, `one per make`.

    **The boundary this does NOT draw**, recorded because it is the next
    question and not this one: a fragment carrying a code token is admitted
    whatever else it says, so `R1200 hexhead` (a designation 244I is built to
    carry) and `2020 service manual` (debris) are both admitted. No shape
    rule separates them — both are "number plus lowercase words" — and
    telling them apart is a question about what the corpus means by a model.
    Filed rather than guessed.
    """
    core = _PAREN_QUALIFIER.sub(" ", value or "").strip()
    if not core:
        return False
    if _CODE_TOKEN.search(core):
        return True
    for word in (w for w in re.split(r"[\s/]+", core) if w):
        token = word.strip(".,;:")
        if not token:
            continue
        if token[0].isupper() or token[0].isdigit():
            continue
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            continue
        return False
    return True


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

#: A comma BETWEEN DIGITS is a thousands separator, not a list delimiter.
#: Splitting on it tore figures in half and fed both halves to the
#: vocabulary: "Rivale at 12,000 km" became the tokens "Rivale at 12" and
#: "000 km", and "Diavel V4 (V4 Granturismo, 60,000 km)" contributed
#: "000 km" to three more rows. Held across the split the same way a
#: compound slash is, and put back after.
_THOUSANDS_COMMA = re.compile(r"(?<=\d),(?=\d)")

#: Stands in for a thousands-separator comma across the split.
_COMMA_HOLD = "\x01"


def _model_tokens(model: str) -> list[str]:
    """The model names one value states, before any attribution."""
    if is_scope(model):
        return []
    if is_plain_model(model):
        # The gate applies here too. `is_plain_model` only asks whether a
        # value is a single name rather than a list, so a short prose
        # sentence with no delimiter takes this branch and would bypass
        # every downstream filter: "Piaggio Group marques only" is 26
        # characters and carries no comma, and reached the junction as a
        # model name that way.
        return [model] if admits_as_model(model) else []
    held = _COMPOUND_SLASH.sub(
        lambda m: f"{m.group(1)}{_SLASH_HOLD}{m.group(2)}", covered_part(model))
    held = _THOUSANDS_COMMA.sub(_COMMA_HOLD, held)
    out: list[str] = []
    for part in re.split(r",|;|—|–|/| and ", held):
        part = _clean_token(
            part.replace(_SLASH_HOLD, "/").replace(_COMMA_HOLD, ","))
        if part and not _PROSE_WORD.search(part) and admits_as_model(part):
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
    return {marque: canonicalise(marque, names)
            for marque, names in vocab.items() if names}


def _identity_key(name: str) -> str:
    """What makes two spellings the same machine. Case and separators only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


@lru_cache(maxsize=4096)
def _flex_pattern(name: str) -> "re.Pattern[str]":
    """A pattern matching `name` however the text spaces or hyphenates it.

    Phase 255C. The pool is canonical now — one spelling per machine — but a
    row's model column is whatever its author typed. Matching the canonical
    literally would find `PCX 150` in a column reading "PCX 150" and miss it
    in one reading "Honda PCX150", which is the same defect one level along:
    an identity that depends on spelling.

    So separators between the runs of a designation are optional, and the
    marque may precede it. Boundaries are still enforced on both ends, which
    is what keeps `PCX` out of `PCX150` and `R` out of `R1200GS`.
    """
    runs = [r for r in re.findall(r"[A-Za-z]+|\d+", name) if r]
    if not runs:
        return re.compile(r"(?!x)x")
    body = r"[\s\-/]*".join(re.escape(r) for r in runs)
    return re.compile(r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])", re.I)


def _flex_search(name: str, haystack: str) -> bool:
    return bool(_flex_pattern(name).search(haystack))


def canonicalise(marque: str, names: set[str]) -> set[str]:
    """One canonical model string per machine, within a marque.

    Phase 255C. The resolver has **no rule about marques** — its canonical
    set is this vocabulary, which 244I derives from what row authors typed
    into the model column. So one machine acquired several canonicals:
    `Honda PCX150` and `PCX 150` are both `exact`, confidence 1.0, and which
    one a caller gets depends on whether they typed the marque. The junction
    then indexed under whichever spelling the row used, and a row reached
    tier 0 only from the spelling that produced it.

    Two operations, in order:

    1. **The model never carries its own marque.** `Aprilia SR Max` under
       Aprilia becomes `SR Max`. A leading marque is stripped only when it
       names the marque whose pool this is — so `LiveWire One` under
       Harley-Davidson keeps its `LiveWire`, which is a machine there and
       not a redundant prefix.
    2. **One spelling per identity.** Forms differing only in case or
       separators collapse to one, preferring the spaced form because that
       is how the corpus writes a designation when it writes it out:
       `PCX 150` over `PCX150`.
    """
    out: dict[str, str] = {}
    prefix = marque.lower() + " "
    for name in names:
        stripped = (name[len(prefix):].strip()
                    if name.lower().startswith(prefix) else name)
        if not stripped:
            stripped = name
        # The model NEVER carries its own marque — decision 3, unconditional.
        # An earlier cut made an exception for single mixed-case words, to stop
        # `LiveWire One` becoming `One`; it was wrong twice over. It kept the
        # marque in the model string, and it created `Yamaha Zuma`, which then
        # matched inside "Yamaha Zuma 125" without being contained by it, so
        # `dedupe_contained` could not collapse the pair. The `One` problem is
        # an EXTRACTION problem and is solved there, by marque adjacency.
        key = _identity_key(stripped)
        if not key or len(stripped) < 2:
            continue
        held = out.get(key)
        if held is None or (stripped.count(" "), stripped) > (held.count(" "), held):
            out[key] = stripped
    return set(out.values())


# `extract_models` (244I, flat `list[str]`) was deleted in Phase 255C.
#
# The pair form superseded its one `src/` caller, and 209B's orphan pin caught
# what was left: a public function referenced by nothing but its own tests.
# Deleting rather than allowlisting it was not tidiness. Its plain-model
# branch returned the RAW column value, so it disagreed with the pair form on
# three live rows and every disagreement was a marque-prefixed string —
# `Energica Experia`, `KTM 690 Duke (LC4 single)`, `KTM LC8 75-degree V-twin`
# — which is the exact defect 255C exists to remove. A superseded function
# that still emits the old defect is a loaded gun for the next caller.
#
# Tests that want models without marques project the pair form:
#     sorted({model for _, model in extract_model_pairs(...)})


def extract_model_pairs(
    make: Optional[str],
    value: Optional[str],
    vocabulary: Optional[dict[str, set[str]]] = None,
    db_path: Optional[str] = None,
    marques: Optional[set[str]] = None,
    european: Optional[set[str]] = None,
) -> list[tuple[str, str]]:
    """The (marque, model) pairs a value states the entry covers.

    Phase 255C. Two things this does that the flat form could not.

    **Dedupe is per marque.** `dedupe_contained` compares a flat list of
    strings against one haystack, so pooling every marque's models first
    meant one marque's name could suppress another's. Containment is decided
    inside a marque now, which is the scope the pair form gives it.

    **There is no `is_plain_model` early accept.** 244I short-circuited a
    delimiter-free value straight into the index, which skipped `covered_part`
    AND the vocabulary — so the raw column text became the junction entry.
    Under 255C that is the defect itself: `Energica Experia` indexed with its
    marque still attached, and `R-series (Paralever)` with a qualifier no
    caller ever types. Decision 1 says extraction has no normaliser of its
    own; an accept that returns the raw value IS a second normaliser, and the
    worst kind, because it returns the input unchanged.

    Every value now goes through the vocabulary, which is canonical. Measured
    over the corpus: **985 rows unchanged, 18 changed, none lost.** Three of
    the 18 were being indexed as NOTHING — the plain branch tested exact
    membership, and `Energica Experia` is not in a pool that holds `Experia`.
    The other 15 traded a raw string for the canonical: `S1000XR (2015-2019)`
    → `S 1000 XR`, `Road King (FLHR)` → `Road King`, and
    `R1150/R1200 (Integral ABS)` → **both** `R1150` and `R1200`, which is one
    row reaching two machines it always named.

    The gate stays where it belongs, at vocabulary construction in
    `_model_tokens`. Nothing reaches this function that the vocabulary did
    not already admit.
    """
    if not value or not value.strip() or is_scope(value):
        return []
    value = value.strip()
    vocab = model_vocabulary(db_path) if vocabulary is None else vocabulary
    if marques is None:
        marques = set(vocab)
    names = extract_marques(make or "", vocabulary=marques, european=european)
    head = covered_part(value)
    out: list[tuple[str, str]] = []
    for marque in names:
        hits = [m for m in vocab.get(marque, set()) if _flex_search(m, head)]
        for model in dedupe_contained(hits, head):
            out.append((marque, model))
    return out


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
    pairs = extract_model_pairs(make, model_value, vocabulary=vocabulary,
                                marques=marques, european=european)
    # Phase 255C: the junction carries the MARQUE the model belongs to, not
    # just the model. Phase 250C already works this out -- its three-rung
    # ladder attributes every token to a marque and handles the case where a
    # marque is also a model line ("LiveWire is a marque AND a
    # Harley-Davidson machine") -- and the junction write then threw that
    # attribution away. This carries it through; nothing new is derived.
    # The junction gained its `make` column at migration 066, and this runs as
    # the post_apply of 056 and 065 as well -- on a database that has not
    # reached 066 yet. Writing three columns into the two-column table failed
    # the 64 -> 65 -> 66 path outright, which is the ordering the operator's
    # own database is on. Shape is read, not assumed.
    has_make = any(
        r[1] == "make"
        for r in conn.execute("PRAGMA table_info(known_issue_models)")
    )
    written = 0
    seen: set = set()
    for owner, model in pairs:
        if has_make:
            conn.execute(
                "INSERT INTO known_issue_models (issue_id, make, model) "
                "VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                (issue_id, owner, model),
            )
        else:
            if model in seen:
                continue
            seen.add(model)
            conn.execute(
                "INSERT INTO known_issue_models (issue_id, model) VALUES (?, ?) "
                "ON CONFLICT DO NOTHING",
                (issue_id, model),
            )
        written += 1
    return written


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
