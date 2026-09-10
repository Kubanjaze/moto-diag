"""Phase 244M — answering from memory, with no API call.

This is the part the operator asked for: *answer inquiries without even using
the api*. It does that for a **bounded grammar** of questions, exactly, and
refuses everything else rather than guessing.

That boundary is the design, not a shortcut. The alternative -- matching a
question against stored answers by embedding similarity -- is what Phase 244M's
research argues against: similarity is an unreliable key for context-dependent
questions, correct and incorrect matches occupy overlapping similarity ranges,
and embeddings are insensitive to negation, which is the exact distinction
between two opposite diagnostic answers. A wrong answer delivered instantly and
for free is worse than no answer, because nothing about it looks wrong.

So: intents are matched by keyword, answers are assembled from recorded facts,
and every answer names its sources and their dates. A question outside the
grammar returns a miss that says what it would have needed. The API path is
untouched and still handles everything else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from motodiag.memory.facts import MemoryFact
from motodiag.memory.recall import recall

# Intent -> the phrases that select it. Matched as whole normalised substrings
# of the question, longest-intent-first, so "when was it last serviced" does
# not fall into the broader "serviced" bucket.
_INTENTS: dict[str, tuple[str, ...]] = {
    "last_service": (
        "when was it last",
        "last serviced",
        "last service",
        "last worked on",
        "how long since",
    ),
    "parts": (
        "what parts",
        "which parts",
        "parts replaced",
        "parts were replaced",
        "parts fitted",
    ),
    "repairs": (
        "what was done",
        "what work",
        "what has been done",
        "work has been done",
        "repairs",
        "repair history",
        "service history",
    ),
    "complaints": (
        "what was the complaint",
        "what did the customer",
        "reported problem",
        "complaint",
        "symptoms",
    ),
    "seen_before": (
        "seen before",
        "happened before",
        "had this before",
        "before on this",
        "recurring",
    ),
    "mileage": (
        "what mileage",
        "at what mileage",
        "how many miles",
    ),
    "history": (
        "what do we know",
        "what do you know",
        "everything about",
        "full history",
        "tell me about this bike",
    ),
}

_KINDS_FOR_INTENT: dict[str, tuple[str, ...]] = {
    "last_service": ("repair", "part-replaced"),
    "parts": ("part-replaced",),
    "repairs": ("repair", "part-replaced"),
    "complaints": ("complaint",),
    "seen_before": ("complaint", "observation", "correction", "repair"),
    "mileage": ("repair", "part-replaced", "measurement"),
    "history": (),
}


@dataclass
class Answer:
    """What memory could say, and what it rests on.

    ``used_api`` exists to be asserted on. It is always False here -- this
    module has no client, no network and no model -- and a guard checks that a
    ledger row is never written by this path, because "answers without the
    api" is a claim about spend that a docstring cannot enforce.
    """

    answered: bool
    text: str
    intent: Optional[str] = None
    facts: list[MemoryFact] = field(default_factory=list)
    used_api: bool = False


def _normalise(question: str) -> str:
    return " ".join(question.lower().replace("?", " ").split())


def _match_intent(question: str) -> Optional[str]:
    """Pick an intent by longest matching phrase, not by first hit.

    Iterating a dict in insertion order and returning the first match makes
    the answer depend on how the table happens to be written -- "what was the
    complaint" contains "complaint", and both are real entries. Scoring by
    phrase length makes the most specific phrase win regardless of order.
    """
    normalised = _normalise(question)
    best: Optional[tuple[int, str]] = None
    for intent, phrases in _INTENTS.items():
        for phrase in phrases:
            if phrase in normalised and (best is None or len(phrase) > best[0]):
                best = (len(phrase), intent)
    return best[1] if best else None


def _subject_terms(question: str, intent: str) -> list[str]:
    """For 'has this been seen before', what is 'this'.

    Plain token overlap -- deliberately literal. A term either appears in a
    recorded fact or it does not; there is no partial credit and no threshold,
    so the answer is reproducible and explainable.
    """
    if intent != "seen_before":
        return []
    stop = {
        "has", "this", "been", "seen", "before", "on", "the", "bike", "it",
        "we", "ever", "had", "a", "an", "is", "was", "with", "any", "of",
        "happened", "recurring", "does", "do",
    }
    return [t for t in _normalise(question).split() if t not in stop and len(t) > 2]


def answer_from_memory(
    vehicle_id: int,
    question: str,
    *,
    db_path: Optional[str] = None,
) -> Answer:
    """Answer from recorded facts, or miss explicitly. Never calls a model."""
    intent = _match_intent(question)
    if intent is None:
        return Answer(
            answered=False,
            text=(
                "Not in memory: that question is outside what can be answered "
                "from recorded facts. Memory answers questions about this "
                "machine's repairs, parts, complaints, mileage and whether "
                "something has been seen before. Anything else needs the "
                "full diagnostic path."
            ),
        )

    facts = recall(
        vehicle_id, kinds=_KINDS_FOR_INTENT[intent] or None, db_path=db_path
    )

    if intent == "seen_before":
        terms = _subject_terms(question, intent)
        if not terms:
            return Answer(
                answered=False,
                intent=intent,
                text=(
                    "Not in memory: no subject to look for. Ask about "
                    "something specific — 'has this charging fault been seen "
                    "before' rather than 'has this been seen before'."
                ),
            )
        facts = [
            f
            for f in facts
            if any(t in f.subject.lower() or t in f.value.lower() for t in terms)
        ]
        if not facts:
            # An honest negative, and a narrow one: it says what was searched
            # for, because "no" to a question memory misunderstood is worse
            # than a miss.
            return Answer(
                answered=True,
                intent=intent,
                text=(
                    "No — nothing in this machine's recorded history mentions "
                    + ", ".join(terms)
                    + "."
                ),
            )

    if not facts:
        return Answer(
            answered=False,
            intent=intent,
            text=(
                "Not in memory: nothing has been compiled for this machine "
                "yet. Run `motodiag memory compile --vehicle "
                f"{vehicle_id}` if it has recorded work."
            ),
        )

    return Answer(
        answered=True,
        intent=intent,
        facts=facts,
        text=_render(intent, facts),
    )


def _render(intent: str, facts: list[MemoryFact]) -> str:
    """Assemble the answer. Every line dated and sourced, without exception."""

    def line(fact: MemoryFact) -> str:
        when = fact.established_at or "date unknown"
        miles = f", {fact.at_miles:,} mi" if fact.at_miles else ""
        detail = f" — {fact.value}" if fact.value else ""
        return f"  - {fact.subject}{detail} ({when}{miles}, {fact.source})"

    if intent == "last_service":
        # Most recent by date, which is NOT the head of `facts` -- recall
        # orders by what a fact rests on first, so the best-supported fact can
        # be years older than the most recent one.
        newest = max(facts, key=lambda f: f.established_at or "")
        return (
            f"Last recorded work: {newest.subject} on "
            f"{newest.established_at or 'an unrecorded date'}"
            f"{f' at {newest.at_miles:,} mi' if newest.at_miles else ''} "
            f"({newest.source})."
        )

    if intent == "mileage":
        with_miles = [f for f in facts if f.at_miles]
        if not with_miles:
            return "No mileage was recorded against any work on this machine."
        return "Mileage on record:\n" + "\n".join(line(f) for f in with_miles)

    headers = {
        "parts": "Parts replaced:",
        "repairs": "Work recorded on this machine:",
        "complaints": "Complaints recorded:",
        "seen_before": "Yes — this machine's history mentions it:",
        "history": "What is known about this machine:",
    }
    return headers[intent] + "\n" + "\n".join(line(f) for f in facts)
