"""The shop manual library (Phase 293; K94, K119, K121, K123).

A shop's admin uploads a PDF manual it owns; the server checks it
(``checks``, ``scan``), stores it under the data folder (``storage``),
renders its pages and their text in the background (``render``), and a
person at Mekno reviews it before anyone in the shop can open it
(``review``). A file stays private to the shop that uploaded it.

The errors below are the library's refusals; ``motodiag.api.errors`` maps
each to its status and problem type.
"""

from __future__ import annotations

from motodiag.auth.deps import SubscriptionRequiredError


class ManualNotFoundError(Exception):
    """404: no such manual here, or not one this caller may open yet."""


class ManualConflictError(Exception):
    """409: the manual is not in a state that allows this (still rendering,
    not approved for a flag)."""


class ManualDuplicateError(Exception):
    """409: the shop already holds this file."""


class ManualReasonRequiredError(Exception):
    """422: a rejection or a takedown needs a reason the shop can read."""


class ManualRefusedError(Exception):
    """422: the file failed the server's checks or the virus scan."""


class ManualStorageExceededError(Exception):
    """402: the file would take the shop past its plan's storage."""


class ManualScannerUnavailableError(Exception):
    """503: no virus scanner, so no upload is accepted (K119)."""


class ShopPlanRequiredError(SubscriptionRequiredError):
    """402 ``subscription-required``: the shop has no active plan, so it has
    no storage for manuals."""

    def __init__(self) -> None:
        Exception.__init__(
            self, "this shop has no active plan, so it cannot store manuals")
        self.required_tier = "individual"
