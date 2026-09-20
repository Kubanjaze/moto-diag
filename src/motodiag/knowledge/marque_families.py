"""Which marques belong to the same family — Phase 250C.

Phase 250C keys the model vocabulary by derived marque, and attributes each
model to the marque it belongs to: a token that names a marque is that
marque's, not the row's other marques'. That rule is what keeps
"BMW S 1000 R" out of Aprilia's matching pool when a single row compares
six marques.

It has exactly one counter-example in this corpus, and it is not an
accident of the data. LiveWire is Harley-Davidson's own electric marque,
spun out in 2021 and carrying the 2019-2020 Harley-Davidson LiveWire with
it, so the model token "LiveWire" names a marque *and* is a
Harley-Davidson machine. Applying the exclusion there would take every
LiveWire model out of Harley-Davidson's pool — the opposite of the fix.
Measured both ways: Harley-Davidson keeps 23 models with the exemption and
15 without.

This fact lives in its own module because it cannot be derived. The make
column never writes the relationship, `marques.py` derives its vocabulary
from the corpus and is guarded by Phase 244F against holding a marque name
at all, and `vehicle_resolver.py` is guarded the same way by 244C. A fact
the data does not state has to be stated somewhere, and somewhere is here,
next to the reason.
"""

from __future__ import annotations

#: sub-marque -> the marque it belongs to. One entry, and it is the whole
#: known set: Zero, Energica and Damon are independent makes, and every
#: other marque in this corpus is its own parent.
SUB_MARQUES: dict[str, str] = {
    "LiveWire": "Harley-Davidson",
}

#: Both directions, as pairs, for the membership test below.
_FAMILY = frozenset(
    {(sub, parent) for sub, parent in SUB_MARQUES.items()}
    | {(parent, sub) for sub, parent in SUB_MARQUES.items()}
)


def same_family(one: str, other: str) -> bool:
    """Are these two marques the same machine family?

    True for a marque and itself, and for a sub-marque and its parent in
    either direction. False for two unrelated marques, which is the case
    the attribution rule cares about.
    """
    if not one or not other:
        return False
    if one == other:
        return True
    return (one, other) in _FAMILY
