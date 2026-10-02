"""NHTSA's recall service and vPIC VIN decoder (Phase 281, rows 281 and 287).

What the recall service does, as this project measured it (F103, Phases 251
and 252; ``docs/phases/completed/281_sources.md`` S4):

- it refuses Python's default User-Agent with a 403; `core.outbound` sends
  its own;
- it answers a query with no result with **HTTP 400 and a valid body**,
  ``{"Count":0,"Message":"Results returned successfully","results":[]}``.
  That 400 is an answer here only when the body parses with that shape;
- a model name it does not use returns the same zero-result answer as a year
  with no campaign, so zero results are never an all-clear;
- a block is an HTML page, which `core.outbound` treats as a failure.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Optional

from motodiag.core.outbound import Response, ServiceUnavailable, fetch

RECALL_SERVICE = "NHTSA recalls"
VPIC_SERVICE = "NHTSA vPIC"
RECALLS_URL = "https://api.nhtsa.gov/recalls/recallsByVehicle"
VPIC_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/"


@dataclass(frozen=True)
class RecallAnswer:
    url: str
    status: int
    fetched_at: str
    results: list[dict]
    size: int


def recalls_url(make: str, model: str, year: int) -> str:
    query = urllib.parse.urlencode({"make": make, "model": model, "modelYear": int(year)},
                                   quote_via=urllib.parse.quote)
    return f"{RECALLS_URL}?{query}"


def _recall_results(response: Response) -> list[dict]:
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ServiceUnavailable(RECALL_SERVICE, "malformed",
                                 "the answer has no list of results", response.status)
    results = data["results"]
    count = data.get("Count")
    if not isinstance(count, int) or count != len(results):
        raise ServiceUnavailable(
            RECALL_SERVICE, "malformed",
            f"it gave Count {count!r} with {len(results)} results", response.status)
    if response.status == 400 and count != 0:
        raise ServiceUnavailable(RECALL_SERVICE, "error", "HTTP 400", 400)
    for result in results:
        if not isinstance(result, dict) or not result.get("NHTSACampaignNumber"):
            raise ServiceUnavailable(RECALL_SERVICE, "malformed",
                                     "a result has no campaign number", response.status)
    return results


def fetch_recalls(make: str, model: str, year: int) -> RecallAnswer:
    """NHTSA's recalls for a make, model and model year, or ServiceUnavailable."""
    url = recalls_url(make, model, year)
    response = fetch(RECALL_SERVICE, url, expect="json", accept_statuses=(400,))
    results = _recall_results(response)
    return RecallAnswer(url=url, status=response.status, fetched_at=response.fetched_at,
                        results=results, size=len(response.body))


@dataclass(frozen=True)
class VinDecode:
    vin: str
    make: Optional[str]
    model: Optional[str]
    model_year: Optional[int]
    manufacturer: Optional[str]
    vehicle_type: Optional[str]
    error_code: Optional[str]
    error_text: Optional[str]
    url: str
    status: int
    fetched_at: str
    raw: str
    size: int

    @property
    def partial(self) -> bool:
        return (self.error_code or "0").strip() not in ("", "0")


def vpic_url(vin: str, model_year: Optional[int] = None) -> str:
    url = f"{VPIC_URL}{urllib.parse.quote(vin)}?format=json"
    if model_year:
        url += f"&modelyear={int(model_year)}"
    return url


def _blank(value) -> Optional[str]:
    text = "" if value is None else str(value).strip()
    return text or None


def decode_vin_vpic(vin: str, model_year: Optional[int] = None) -> VinDecode:
    """vPIC's flat decode of a VIN, or ServiceUnavailable."""
    url = vpic_url(vin, model_year)
    response = fetch(VPIC_SERVICE, url, expect="json")
    data = response.json()
    results = data.get("Results") if isinstance(data, dict) else None
    if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
        raise ServiceUnavailable(VPIC_SERVICE, "malformed",
                                 "expected one decoded result", response.status)
    row = results[0]
    year_text = _blank(row.get("ModelYear"))
    return VinDecode(
        vin=vin, make=_blank(row.get("Make")), model=_blank(row.get("Model")),
        model_year=int(year_text) if year_text and year_text.isdigit() else None,
        manufacturer=_blank(row.get("Manufacturer")),
        vehicle_type=_blank(row.get("VehicleType")),
        error_code=_blank(row.get("ErrorCode")), error_text=_blank(row.get("ErrorText")),
        url=url, status=response.status, fetched_at=response.fetched_at,
        raw=response.body.decode("utf-8", "replace"), size=len(response.body),
    )
