"""Which powertrain a corpus row is about — Phase 250B.

Gate 13 measured what the absence of this costs: a Harley-Davidson
LiveWire, a battery-electric motorcycle, was handed twelve rows about
stator failure, compensator sprocket noise, intake manifold seals and
clutch pack wear, because `known_issues` has no powertrain column and the
knowledge search has never had a powertrain filter. Phase 243 recorded
that debt; this is the fourth phase shaped by it.

`known_issues` still has no powertrain column and this phase does not add
one. What it has is a `make` string that names its marques and a `model`
string that names its models, and four marques in this corpus build
battery-electric machines and nothing else. That is enough to answer the
only question the prompt needs answered: *is this row about an electric
machine?*

The marque names live here rather than in `marques.py` or
`vehicle_resolver.py` because Phase 244C guards both of those against a
hard-coded marque name — the vocabulary there is derived from the corpus,
and it should stay derived. This is a different kind of fact: not "which
marques exist" but "which of them are electric", which no column states.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

#: Marques in this corpus that build battery-electric machines only. Zero,
#: Energica and Damon have no combustion model at all; LiveWire is
#: Harley-Davidson's electric marque, spun out in 2021 and carrying the
#: 2019-2020 Harley-Davidson LiveWire with it.
ELECTRIC_MARQUES = frozenset({"Zero", "LiveWire", "Energica", "Damon"})

#: A mixed marque's electric models, for rows filed under the parent. The
#: 2019-2020 machine is a "Harley-Davidson LiveWire": the marque column
#: says Harley-Davidson and only the model says otherwise.
ELECTRIC_MODELS = ("LiveWire",)

#: Rows that apply to every make (Phase 244F's wildcard) are about no
#: powertrain in particular and belong in any prompt.
WILDCARD_MAKE = "*"

_MARQUE_PATTERNS = tuple(
    re.compile(rf"(?<![A-Za-z]){re.escape(m)}(?![A-Za-z])", re.I)
    for m in sorted(ELECTRIC_MARQUES)
)
_MODEL_PATTERNS = tuple(
    re.compile(rf"(?<![A-Za-z]){re.escape(m)}(?![A-Za-z])", re.I)
    for m in ELECTRIC_MODELS
)


def is_electric_row(row: Mapping[str, Any]) -> bool:
    """Does this row speak about an electric machine?

    True when the row names an electric-only marque, names an electric
    model of a mixed marque, or applies to every make. Substring matching
    is bounded by letter boundaries so "Zero" the marque is not found
    inside another word.

    Deliberately generous: a row naming four marques of which one is
    electric IS about an electric machine, which is exactly how Phase
    241's HV-safety file is written.
    """
    make = str(row.get("make") or "")
    if make.strip() == WILDCARD_MAKE:
        return True
    if any(p.search(make) for p in _MARQUE_PATTERNS):
        return True
    model = str(row.get("model") or "")
    return any(p.search(model) for p in _MODEL_PATTERNS)
