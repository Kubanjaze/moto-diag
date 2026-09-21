"""Choosing which corpus rows reach the model — Phase 250B.

Phase 244S bounded the prompt at twelve rows and took them in rank order:
most specific tier first, then severity, then title. Gate 13 measured what
that costs on an electric motorcycle. Phase 241's ten critical HV-safety
rows are the most severe rows any electric machine has, so they fill the
cap every time, and the four generic layers written across 246-249 — the
pack, the controller, regen, cooling — never reach the model at all on an
Energica Ego or a Harley-Davidson LiveWire. Retrieval was also
symptom-blind: a rider reporting a hot pack and a rider reporting a dead
regen brake light were handed the same twelve rows.

The fix is composition, not enlargement. Gate 13 measured that too: to
reach all four layers by raising the cap, a Zero needs 27 rows and a
Harley-Davidson LiveWire needs 95 — 68 KB of prompt, three times over in
the interactive flow. Eight rows by rank plus four reserved for what the
rider actually reported carries every relevant layer at today's size.

Two rules keep this honest:

* **The safety floor is not spent on relevance.** The reserved slots come
  out of the tail, never out of the head, so the most specific and most
  severe rows are still there.
* **The order the model sees is unchanged.** Whatever is chosen is
  re-sorted by the same key retrieval used, so 244S's contract — most
  specific first, and the prompt still saying "same make, DIFFERENT
  model" — holds.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional, Sequence

from motodiag.core.severity import SEVERITY_RANK
from motodiag.knowledge.applicability import row_applies
from motodiag.knowledge.powertrain import is_electric_row
from motodiag.knowledge.transmission import Resolution, record_withheld

#: How many of the prompt's rows are reserved for rows that match what the
#: rider reported. Four of twelve: enough to carry the layer a complaint
#: points at, small enough that the head — the most specific, most severe
#: rows — is still two thirds of the prompt.
RELEVANCE_RESERVE = 4

#: How many of the prompt's rows are held for the most severe content the
#: machine has, wherever it sits in the ranking.
#:
#: Phase 250C added this, and the reason is worth keeping. That phase made
#: model resolution work for machines it had never worked for, and on a Zero
#: SR/F the effect was immediate: twelve tier-0 rows, all of them specific to
#: that model, and **not one critical row left**. Phase 241's high-voltage
#: rules — do not work alone on a live pack, the service disconnect does not
#: de-energise the motor, the capacitor discharge wait is a specified interval
#: — are `make_wide`, so a better model match outranked every one of them.
#:
#: Specificity is not the only thing a prompt owes a technician. Three of
#: twelve is the floor: enough that the rules for opening a pack survive any
#: ranking, small enough that it never crowds out the machine's own content.
SAFETY_RESERVE = 3

#: Tier order, most specific first. Mirrors the SQL in
#: vehicle_resolver.known_issues_for_vehicle; a row with no tier sorts
#: last, the same fail-safe the resolver uses.
_TIER_ORDER = {"model": 0, "make_wide": 1, "make_other_model": 2}

#: Tokens of four characters or more, the shape predictor.py already uses
#: for its TSB matching. Short words carry no signal and the stop list
#: removes the ones that survive the length filter.
_TOKEN = re.compile(r"[a-z0-9]{4,}")
_STOP = frozenset({
    "this", "that", "with", "from", "when", "does", "dont", "wont", "have",
    "been", "will", "your", "bike", "motorcycle", "issue", "problem", "fault",
    "after", "before", "under", "over", "only", "very", "much", "more", "some",
    "make", "model", "year", "still", "just", "also", "than", "then", "them",
})


def relevance_tokens(text: str) -> set[str]:
    """The comparable words in a piece of text."""
    return {t for t in _TOKEN.findall((text or "").lower()) if t not in _STOP}


def relevance_score(row: Mapping[str, Any], wanted: set[str]) -> int:
    """How many of the rider's words this row also uses.

    Title and symptoms carry the row's subject; the description is read
    only at its head, because a long description would otherwise outscore
    a precise title by sheer surface area.
    """
    if not wanted:
        return 0
    symptoms = row.get("symptoms") or []
    if isinstance(symptoms, str):
        symptoms = [symptoms]
    haystack = " ".join([
        str(row.get("title") or ""),
        " ".join(str(s) for s in symptoms),
        str(row.get("description") or "")[:400],
    ])
    return len(relevance_tokens(haystack) & wanted)


def _canonical_key(row: Mapping[str, Any]) -> tuple[int, int, str]:
    """The order retrieval already put these rows in."""
    tier = _TIER_ORDER.get(str(row.get("match_tier") or ""), len(_TIER_ORDER))
    severity = SEVERITY_RANK.get(str(row.get("severity") or "").lower(), 0)
    return (tier, -severity, str(row.get("title") or ""))


def _electric_first(rows: Sequence[Mapping[str, Any]], limit: int) -> list[Mapping[str, Any]]:
    """Rows about electric machines, topped up in rank order if too few.

    The top-up matters: 244S pins that the prompt is exactly full, and a
    corpus that holds fewer than `limit` electric rows for some machine
    must not produce a short prompt.
    """
    electric = [r for r in rows if is_electric_row(r)]
    if len(electric) >= limit:
        return electric
    seen = {id(r) for r in electric}
    return electric + [r for r in rows if id(r) not in seen]


def drop_inapplicable(
    rows: Sequence[Mapping[str, Any]],
    transmission: Optional[Resolution],
) -> list[Mapping[str, Any]]:
    """Remove rows whose declared transmission set does not cover this machine.

    Public because `compose_prompt_rows` is not the only door. The video
    `/ask` endpoint hands retrieved rows straight to a vision model without
    composing them, and it needs the same filter for the same reason.

    **This excludes; it does not reorder.** That is the deliberate
    divergence from Phase 250B's powertrain filter twelve lines above, and
    the ADR records why. 250B puts electric rows first and leaves the rest
    in place, which is right for its problem — an electric machine that
    also sees a generic row has lost nothing. It is wrong for this one.
    A Gold Wing shown a variator-roller row has been told something false
    about itself, and moving it to position twelve does not make it true.

    The second divergence is where the answer comes from. 250B infers a
    row's powertrain from the marque names in its `make` column, and is
    documented as deliberately generous about it. That generosity is
    exactly what fails here, because Honda and Yamaha build both scooters
    and motorcycles — it is the mechanism that produced the 254 defect.
    Nothing here reads row text or marque names: the row declares its own
    set in the seed file and the machine is classified from a sourced
    table.
    """
    if transmission is None:
        return list(rows)
    kept = [r for r in rows if row_applies(r, "transmission", transmission.candidates)]
    record_withheld(transmission.provenance, len(rows) - len(kept))
    return kept


def compose_prompt_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
    powertrain: Optional[str] = None,
    symptoms: Optional[Sequence[str]] = None,
    transmission: Optional[Resolution] = None,
    reserve: int = RELEVANCE_RESERVE,
    safety: int = SAFETY_RESERVE,
) -> list[dict]:
    """Choose the rows that reach the model, and order them as before.

    With no powertrain, no symptoms and no transmission this is exactly
    what Phase 244S did: the first `limit` rows in rank order. That default
    is what keeps `motodiag code` and every existing caller unchanged.

    `transmission` (Phase 255) is a `Resolution` — a candidate set and how
    it was reached. Passing one removes rows the machine cannot have.
    """
    if not rows:
        return []
    # Phase 255. Applicability is settled BEFORE composition, not after:
    # a row that does not apply to this machine must not occupy one of the
    # twelve slots, and must not be able to win a reserved slot either.
    rows = drop_inapplicable(rows, transmission)
    if not rows:
        return []
    pool: Sequence[Mapping[str, Any]] = rows
    if (powertrain or "").lower() == "electric":
        pool = _electric_first(rows, limit)

    head = list(pool[:max(limit - reserve, 0)])
    tail = list(pool[max(limit - reserve, 0):])
    chosen = list(head)

    wanted = relevance_tokens(" ".join(symptoms or []))
    if wanted and tail:
        ranked = sorted(
            ((relevance_score(r, wanted), i, r) for i, r in enumerate(tail)),
            key=lambda t: (-t[0], t[1]),
        )
        for score, _i, row in ranked:
            if len(chosen) >= limit:
                break
            if score > 0:
                chosen.append(row)

    chosen_ids = {id(r) for r in chosen}
    for row in tail:
        if len(chosen) >= limit:
            break
        if id(row) not in chosen_ids:
            chosen.append(row)
            chosen_ids.add(id(row))

    chosen = _hold_the_safety_floor(chosen[:limit], pool, reserve=safety)
    return sorted((dict(r) for r in chosen[:limit]), key=_canonical_key)


def _hold_the_safety_floor(chosen, pool, *, reserve: int) -> list:
    """Make room for the most severe rows the machine has.

    They are swapped in over the lowest-ranked rows already chosen, so the
    prompt keeps its size and loses its least specific content, not its
    most relevant.
    """
    if reserve <= 0:
        return chosen
    chosen_ids = {id(r) for r in chosen}
    present = sum(1 for r in chosen if str(r.get("severity") or "").lower() == "critical")
    missing = reserve - present
    if missing <= 0:
        return chosen
    candidates = [r for r in pool
                  if str(r.get("severity") or "").lower() == "critical"
                  and id(r) not in chosen_ids]
    if not candidates:
        return chosen
    out = list(chosen)
    for row in candidates[:missing]:
        droppable = [i for i, r in enumerate(out)
                     if str(r.get("severity") or "").lower() != "critical"]
        if not droppable:
            break
        out[max(droppable, key=lambda i: _canonical_key(out[i]))] = row
    return out
