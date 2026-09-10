"""Phase 244M — reading the memory back.

Recall is a deterministic ordering over recorded facts. There is no similarity
search here and there is not meant to be one: Phase 244M's research found that
similarity is an unreliable key for context-dependent questions, and every
question this product answers is context-dependent.

The ordering is by **what the fact rests on**, then by recency. A mechanic's
confirmed correction outranks a model's observation regardless of which is
newer, because the failure this ordering prevents is a fresh guess displacing
an established fact.
"""

from __future__ import annotations

from typing import Optional, Sequence

from motodiag.memory.facts import MemoryFact, list_facts

# Lower sorts first. This is the whole trust model, in five lines.
_SOURCE_RANK: dict[str, int] = {
    "mechanic-verified": 0,
    "service-record": 1,
    "customer-reported": 2,
    "model-generated": 3,
}


def _rank(fact: MemoryFact) -> tuple:
    # `established_at` descending is expressed by negating the sort at the
    # call site rather than here, because dates are strings; reverse-sorting
    # the whole tuple would also reverse the source ranking.
    return (_SOURCE_RANK.get(fact.source, 99), _invert_date(fact.established_at))


def _invert_date(value: str) -> str:
    """Make a date sort descending inside an ascending tuple sort.

    Dates are ISO strings, so ordinary descending order needs `reverse=True`,
    which would also flip the source rank sharing the tuple. Complementing each
    digit gives a string whose ascending order is the date's descending order.
    """
    return "".join(
        str(9 - int(ch)) if ch.isdigit() else ch for ch in (value or "")
    ).ljust(10, "￿")


def recall(
    vehicle_id: int,
    *,
    kinds: Optional[Sequence[str]] = None,
    limit: Optional[int] = None,
    db_path: Optional[str] = None,
) -> list[MemoryFact]:
    """Everything currently established about one machine, best-supported first.

    ``limit`` truncates the *ordered* list, so raising it can only ever reveal
    more -- it never reorders or removes what a smaller limit returned. That is
    the monotonicity property Phase 244E established for the corpus and it
    applies here for the same reason: knowing more must never return less.
    """
    facts = list_facts(vehicle_id, kinds=kinds, db_path=db_path)
    facts.sort(key=_rank)
    return facts[:limit] if limit is not None else facts


def recall_summary(
    vehicle_id: int,
    *,
    limit: int = 12,
    include_model_generated: bool = False,
    db_path: Optional[str] = None,
) -> str:
    """A prompt-ready block of what is known about this machine.

    **Model-generated observations are excluded by default, and that is the
    important part of this function.** This block is injected into the prompt
    of the next vision analysis, and the vision analysis is what wrote those
    observations in the first place. Feeding them back labelled as "known
    history" launders a guess into an established fact across runs: an early
    wrong reading -- "possible stator cover leak" -- returns as context, biases
    the next analysis toward itself, and is written back with more confidence
    than it earned. Nothing in the loop can discount it, because the model
    cannot tell its own prior output from the shop's records.

    This was not in the plan. It surfaced on the first run against real data:
    vehicle 10 had eleven facts, ten of them the model's own prose from a
    single sweep, and all ten were about to become its next prompt's history.

    Human-established facts -- complaints, repairs, parts, corrections -- are
    what a shop actually knows, and they are the whole point of the feature.
    ``include_model_generated=True`` is available for callers displaying to a
    person, who can read the label and weigh it.

    Every line carries its date and what it rests on. An undated fact in a
    prompt reads as current, and a five-year-old complaint would otherwise
    argue with today's symptom on equal terms.

    Returns "" when there is nothing, so the caller can omit the section
    entirely rather than telling a model that a machine has no history --
    which is a claim, and a different one from saying nothing.
    """
    facts = recall(vehicle_id, limit=None, db_path=db_path)
    if not include_model_generated:
        facts = [f for f in facts if f.source != "model-generated"]
    facts = facts[:limit]
    if not facts:
        return ""

    lines = ["Known history for this machine (most reliable first):"]
    for fact in facts:
        when = fact.established_at or "date unknown"
        miles = f", at {fact.at_miles:,} mi" if fact.at_miles else ""
        detail = f" — {fact.value}" if fact.value else ""
        lines.append(
            f"- [{fact.fact_kind}] {fact.subject}{detail} "
            f"({when}{miles}, {fact.source})"
        )
    return "\n".join(lines)
