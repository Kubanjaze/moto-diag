"""What a corpus row applies to — Phase 255.

Phase 254 shipped twelve rows about scooter CVTs whose `make` column named
seven marques, and two of those marques build motorcycles as well as
scooters. A Gold Wing, a CBR1000RR and a Grom were each handed seven rows
about variator rollers and drive belts they do not have. Nothing in the
schema could have caught it, because `known_issues` had no way to say what
a row is *about* beyond the marques it names.

This module is that way of saying it: a JSON object keyed by axis, holding
the set of values on that axis the row's own content holds for.

    {"transmission": ["cvt"]}

**An absent key means unscoped on that axis** — the row makes no claim there
and every machine may have it. **An empty list is a validation error**, never
"applies to nothing" and never "applies to everything": an empty list is
almost always an authoring slip, and a slip that could silently mean either
of two opposite things must fail instead of picking one.

Adding a second axis later is a new key, not a migration. That is the whole
reason this is JSON rather than a `transmission_applicability` column — and
it costs little, because the filtering happens in Python, not in SQL.

**The stated limit.** A JSON column carries no CHECK constraint, so the
Phase 195C schema lint does not cover this the way it covers
`known_issues.source`. The pydantic model below is the only guard there is,
which makes it load-bearing — so it rejects an unknown axis key and an
unknown axis value loudly, at seed load and again at read, and has its own
tests for both.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Literal, Mapping, Optional

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

#: The transmission values a row may declare. Written out rather than
#: derived because `Literal` needs static members — and because a silent
#: divergence from `VehicleTransmission` is exactly the SSOT-shadowing
#: failure the F9 taxonomy names, a test pins the two together.
TransmissionValue = Literal[
    "manual",
    "cvt",
    "dct",
    "semi_auto_centrifugal",
    "semi_auto_actuated",
    "direct_drive",
]

#: The axes this contract knows. One today; the key set is the extension
#: point, and an unknown key is rejected rather than ignored.
AXES: tuple[str, ...] = ("transmission",)


class RowApplicability(BaseModel):
    """What a row's own content holds for, per axis.

    `extra="forbid"` is the point of the model: a row declaring
    `{"transmision": ["cvt"]}` fails loudly rather than loading as unscoped
    and quietly reaching every machine — which is precisely the 254 defect,
    reintroduced by a typo.
    """

    model_config = ConfigDict(extra="forbid")

    transmission: Optional[list[TransmissionValue]] = None

    @field_validator("transmission")
    @classmethod
    def _no_empty_set(cls, value):
        """An empty list is a mistake, and must not be read as a policy."""
        if value is not None and len(value) == 0:
            raise ValueError(
                "applicability: an empty list is not a valid declaration — "
                "omit the axis key to leave the row unscoped on it"
            )
        return value

    def declared(self, axis: str) -> Optional[frozenset[str]]:
        """The set declared on `axis`, or None when the row is unscoped."""
        values = getattr(self, axis, None)
        return None if values is None else frozenset(values)


class ApplicabilityError(ValueError):
    """A row's applicability could not be read. Never swallowed."""


def parse_applicability(raw: Any) -> Optional[RowApplicability]:
    """Read a row's applicability, or raise.

    `None`, an empty string and an empty object all mean the same thing —
    the row declares nothing on any axis — and that is the state every row
    written before this phase is in. Anything else that is not a valid
    declaration raises; nothing is dropped and nothing is defaulted.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ApplicabilityError(f"applicability is not valid JSON: {exc}") from exc
    if isinstance(raw, RowApplicability):
        return raw
    if not isinstance(raw, Mapping):
        raise ApplicabilityError(
            f"applicability must be a JSON object, got {type(raw).__name__}"
        )
    if not raw:
        return None
    try:
        return RowApplicability(**dict(raw))
    except ValidationError as exc:
        raise ApplicabilityError(f"applicability rejected: {exc}") from exc


def dump_applicability(value: Any) -> Optional[str]:
    """Validate then serialise, for the write path. None stays None."""
    parsed = parse_applicability(value)
    if parsed is None:
        return None
    payload = {k: v for k, v in parsed.model_dump().items() if v is not None}
    return json.dumps(payload) if payload else None


def row_applies(
    row: Mapping[str, Any],
    axis: str,
    candidates: Optional[Iterable[str]],
) -> bool:
    """Does this row apply to a machine whose `axis` might be any of `candidates`?

    **The inclusion rule: a scoped row is included only if its declared set
    covers every candidate.** An unscoped row — no key for this axis —
    always applies, which is every row written before Phase 255.

    The rule is what makes the policy fail closed. An unknown machine has
    all six transmissions as candidates, so only a row declaring all six
    passes, which is the same as being unscoped. An ambiguous Africa Twin
    has `{manual, dct}`, so a row valid for both passes and a `{dct}`-only
    row is withheld.

    Never misleading, sometimes missing. A Gold Wing told about variator
    rollers is a wrong answer; a PCX missing one row is an incomplete one.
    """
    declared = _declared_for(row, axis)
    if declared is None:
        return True
    if candidates is None:
        return False
    wanted = frozenset(candidates)
    if not wanted:
        return False
    return wanted <= declared


def _declared_for(row: Mapping[str, Any], axis: str) -> Optional[frozenset[str]]:
    """Read one row's declared set, naming the row if it cannot be read.

    The raise is deliberate and specified: an invalid declaration must not
    be dropped or defaulted, because loading a typo as unscoped is exactly
    the Phase 254 defect reintroduced. But a loud failure that does not say
    WHICH row failed is not actionable, and this one reaches the product's
    primary command — so the row identifies itself in the message.
    """
    if axis not in AXES:
        raise ApplicabilityError(f"unknown applicability axis: {axis!r}")
    try:
        parsed = parse_applicability(row.get("applicability"))
    except ApplicabilityError as exc:
        raise ApplicabilityError(
            f"known_issues row id={row.get('id')!r} "
            f"({str(row.get('title') or '')[:60]!r}): {exc}"
        ) from exc
    return None if parsed is None else parsed.declared(axis)

