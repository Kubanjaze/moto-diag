"""A shop's bikes and their customers, from one CSV file (Phase 330).

The file has a header row. ``make``, ``model`` and ``year`` are required;
``vin``, ``engine_cc``, ``powertrain``, ``engine_type``, ``protocol``,
``notes``, ``customer_name``, ``customer_phone`` and ``customer_email`` are
optional. Every row is checked before any is written: one problem anywhere
and nothing is written.

A bike is identified only by its VIN. A row whose VIN is already in
``vehicles`` is skipped; a row with no VIN is added every time the file is
imported, and the report counts such rows. A customer is matched only
within the shop: by exact phone when the row gives one, else by exact
name. A customer not found is made under the shop, never unclaimed.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from motodiag.core.database import get_connection
from motodiag.core.models import VehicleBase
from motodiag.crm.customer_bikes_repo import link_customer_bike
from motodiag.crm.customer_repo import create_customer, search_customers
from motodiag.crm.models import Customer
from motodiag.vehicles.registry import add_vehicle

REQUIRED_COLUMNS = ("make", "model", "year")
OPTIONAL_COLUMNS = (
    "vin", "engine_cc", "powertrain", "engine_type", "protocol", "notes",
    "customer_name", "customer_phone", "customer_email",
)
COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


@dataclass
class BikeRow:
    """One checked row: the bike, and the customer it belongs to (if named)."""

    line: int
    vehicle: VehicleBase
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None


@dataclass
class ImportReport:
    """What an import did, or would do on a dry run; line numbers per count."""

    problems: list[str] = field(default_factory=list)
    added: list[int] = field(default_factory=list)
    skipped: list[tuple[int, int]] = field(default_factory=list)
    customers_made: list[int] = field(default_factory=list)
    customers_matched: list[int] = field(default_factory=list)
    links: list[int] = field(default_factory=list)
    without_vin: list[int] = field(default_factory=list)
    vehicle_ids: list[int] = field(default_factory=list)
    written: bool = False

    def lines(self) -> list[str]:
        """The report as plain lines, the same for a dry run and a write."""
        if self.problems:
            return [f"{len(self.problems)} problem(s); nothing was written:"] + [
                f"  {p}" for p in self.problems
            ]

        def at(lines: list[int]) -> str:
            return f" (lines {', '.join(str(n) for n in lines)})" if lines else ""

        out = [
            f"Bikes added: {len(self.added)}{at(self.added)}",
            f"Bikes skipped: {len(self.skipped)}"
            + at([line for line, _ in self.skipped]),
        ]
        out += [
            f"  line {line}: already in the garage (bike #{vid})"
            for line, vid in self.skipped
        ]
        out += [
            f"Customers made: {len(self.customers_made)}{at(self.customers_made)}",
            f"Customers matched: {len(self.customers_matched)}"
            f"{at(self.customers_matched)}",
            f"Links made: {len(self.links)}{at(self.links)}",
        ]
        if self.without_vin:
            out.append(
                f"Rows without a VIN: {len(self.without_vin)}{at(self.without_vin)}"
                " (added again on every import of this file)"
            )
        return out


def _blank_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _int_or_problem(
    record: dict, column: str, line: int, problems: list[str],
) -> Optional[int]:
    raw = record.get(column)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        problems.append(f"line {line}: {column} {raw!r} is not a whole number")
        return None


def parse_row(line: int, raw: dict) -> tuple[Optional[BikeRow], list[str]]:
    """Check one row's values; return the row, or None and its problems."""
    record = {k: _blank_to_none(v) for k, v in raw.items()}
    problems: list[str] = []
    for column in REQUIRED_COLUMNS:
        if record.get(column) is None:
            problems.append(f"line {line}: {column} is empty")
    year = _int_or_problem(record, "year", line, problems)
    engine_cc = _int_or_problem(record, "engine_cc", line, problems)
    if record.get("customer_name") is None and (
        record.get("customer_phone") or record.get("customer_email")
    ):
        problems.append(
            f"line {line}: customer_phone or customer_email given with no "
            "customer_name"
        )
    if problems:
        return None, problems
    values = {
        "make": record["make"], "model": record["model"], "year": year,
        "engine_cc": engine_cc, "vin": record.get("vin"),
        "powertrain": record.get("powertrain"),
        "engine_type": record.get("engine_type"),
        "notes": record.get("notes"),
    }
    if record.get("protocol") is not None:
        values["protocol"] = record["protocol"]
    try:
        vehicle = VehicleBase(**values)
    except ValidationError as e:
        for err in e.errors():
            where = ".".join(str(part) for part in err["loc"])
            problems.append(f"line {line}: {where}: {err['msg']}")
        return None, problems
    return BikeRow(
        line=line, vehicle=vehicle,
        customer_name=record.get("customer_name"),
        customer_phone=record.get("customer_phone"),
        customer_email=record.get("customer_email"),
    ), []


def read_bike_rows(path: str | Path) -> tuple[list[BikeRow], list[str]]:
    """Read and check every row of the file; return the rows and the problems.

    Line numbers are the file's own: the header is line 1.
    """
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        header = [h.strip() for h in (reader.fieldnames or [])]
        problems = [
            f"line 1: unknown column {h!r}" for h in header if h not in COLUMNS
        ] + [
            f"line 1: missing required column {c!r}"
            for c in REQUIRED_COLUMNS if c not in header
        ]
        if problems:
            return [], problems
        reader.fieldnames = header
        rows: list[BikeRow] = []
        first_line_of_vin: dict[str, int] = {}
        for raw in reader:
            line = reader.line_num
            row, row_problems = parse_row(line, raw)
            problems += row_problems
            if row is None:
                continue
            vin = row.vehicle.vin
            if vin is not None and vin in first_line_of_vin:
                problems.append(
                    f"line {line}: VIN {vin!r} is also on line "
                    f"{first_line_of_vin[vin]}"
                )
                continue
            if vin is not None:
                first_line_of_vin[vin] = line
            rows.append(row)
    return rows, problems


def _vehicle_with_vin(vin: str, db_path: Optional[str]) -> Optional[int]:
    with get_connection(db_path) as conn:
        found = conn.execute(
            "SELECT id FROM vehicles WHERE vin = ? ORDER BY id LIMIT 1", (vin,),
        ).fetchone()
    return int(found[0]) if found else None


def _customer_key(row: BikeRow) -> tuple[str, str]:
    """What identifies the row's customer: the phone if given, else the name."""
    if row.customer_phone is not None:
        return "phone", row.customer_phone
    return "name", row.customer_name or ""


def _shop_customer(
    key: tuple[str, str], shop_id: int, db_path: Optional[str],
) -> Optional[int]:
    """The shop's customer with exactly this phone, or exactly this name."""
    column, wanted = key
    for found in search_customers(wanted, db_path=db_path, shop_id=shop_id):
        if found.get(column) == wanted:
            return int(found["id"])
    return None


def import_bikes(
    rows: list[BikeRow],
    shop_id: int,
    db_path: Optional[str] = None,
    *,
    problems: Optional[list[str]] = None,
    dry_run: bool = False,
) -> ImportReport:
    """Write the rows under the shop, or say what would be written on a dry run.

    With any problem, nothing is written and the report lists the problems.
    """
    report = ImportReport(problems=list(problems or []))
    if report.problems:
        return report
    # Customers this run makes, so a dry run matches later rows to them
    # exactly as the write does.
    pending: dict[tuple[str, str], int] = {}
    for row in rows:
        vin = row.vehicle.vin
        existing = _vehicle_with_vin(vin, db_path) if vin is not None else None
        if existing is not None:
            report.skipped.append((row.line, existing))
            continue
        if vin is None:
            report.without_vin.append(row.line)
        report.added.append(row.line)
        vehicle_id = 0 if dry_run else add_vehicle(row.vehicle, db_path)
        if not dry_run:
            report.vehicle_ids.append(vehicle_id)
        if row.customer_name is None:
            continue
        key = _customer_key(row)
        customer_id = _shop_customer(key, shop_id, db_path) or pending.get(key)
        if customer_id is not None:
            report.customers_matched.append(row.line)
        else:
            report.customers_made.append(row.line)
            customer_id = -row.line if dry_run else create_customer(Customer(
                name=row.customer_name, phone=row.customer_phone,
                email=row.customer_email, shop_id=shop_id,
            ), db_path)
            pending[key] = customer_id
        report.links.append(row.line)
        if not dry_run:
            link_customer_bike(customer_id, vehicle_id, "owner", db_path=db_path)
    report.written = not dry_run
    return report
