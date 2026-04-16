"""Unified search engine — query across all knowledge stores from one entry point."""

from motodiag.vehicles.registry import list_vehicles
from motodiag.knowledge.dtc_repo import search_dtcs
from motodiag.knowledge.symptom_repo import search_symptoms
from motodiag.knowledge.issues_repo import search_known_issues
from motodiag.core.session_repo import list_sessions


def search_all(
    query: str,
    make: str | None = None,
    model: str | None = None,
    year: int | None = None,
    db_path: str | None = None,
) -> dict:
    """Search across all knowledge stores.

    Returns dict with keys: vehicles, dtc_codes, symptoms, known_issues, sessions.
    Each value is a list of matching results.
    """
    if not query or not query.strip():
        return {
            "vehicles": [],
            "dtc_codes": [],
            "symptoms": [],
            "known_issues": [],
            "sessions": [],
            "total": 0,
        }

    q = query.strip()

    # Search each store
    vehicles = list_vehicles(make=make or q, model=model, year=year, db_path=db_path)
    if make:
        # If make is explicitly provided, also search by query in model
        vehicles += list_vehicles(model=q, db_path=db_path)
        # Deduplicate by id
        seen = set()
        unique = []
        for v in vehicles:
            if v["id"] not in seen:
                seen.add(v["id"])
                unique.append(v)
        vehicles = unique

    dtc_codes = search_dtcs(query=q, make=make, db_path=db_path)
    symptoms = search_symptoms(query=q, db_path=db_path)
    known_issues = search_known_issues(query=q, make=make, model=model, year=year, db_path=db_path)
    sessions = list_sessions(vehicle_make=make or q, db_path=db_path)

    total = len(vehicles) + len(dtc_codes) + len(symptoms) + len(known_issues) + len(sessions)

    return {
        "vehicles": vehicles,
        "dtc_codes": dtc_codes,
        "symptoms": symptoms,
        "known_issues": known_issues,
        "sessions": sessions,
        "total": total,
    }
