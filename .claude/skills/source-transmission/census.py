#!/usr/bin/env python3
"""Census — every (make, model) in the junction that resolves `unknown`.

No model, no sampling, no search: a rule applied to the whole junction.
That is how the figures of record were produced (F139), and the reason
this step is a script — a model counting spellings is how 427 appeared
where ~600 was true.

**Not every unknown spelling can be a machine.** `not_a_machine` classes
the ones that cannot, by named lists (never by shape alone — see the
`finding` skill on why a rule by shape hides true positives):

| class | what | example |
|---|---|---|
| `bare_number` | digits, optionally `cc` | Ducati `1000`, MV Agusta `20`, Aprilia `1077cc` |
| `other_marque` | starts with another marque's name | `Gilera` under six makes, Ducati `Guzzi V85` |
| `marque_name` | the make's own name or short name | MV Agusta `MV` |
| `prose` | junction prose (F135): a named non-model word | `2020 service manual`, `approximately 2016 to 2020` |

They stay in the census count (the figure of record) and are reported as
their own count; the orchestrator gives them `no_evidence` without a
library search or a model call.

Usage:  census.py [DB] [--make MAKE] [--json]
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from motodiag.knowledge.transmission import resolve_transmission  # noqa: E402


# Marques by the names a junction spelling would start with. The junction's
# own makes plus the marques that leak into it through shared rows.
MARQUES: dict[str, tuple[str, ...]] = {
    "Aprilia": ("aprilia",), "BMW": ("bmw",), "Ducati": ("ducati",), "Energica": ("energica",),
    "Harley-Davidson": ("harley davidson", "harley"), "Honda": ("honda",), "Kawasaki": ("kawasaki",),
    "KTM": ("ktm",), "Kymco": ("kymco",), "LiveWire": ("livewire",), "MV Agusta": ("mv agusta", "mv"),
    "Moto Guzzi": ("moto guzzi", "guzzi"), "Piaggio": ("piaggio",), "SYM": ("sym",), "Suzuki": ("suzuki",),
    "Triumph": ("triumph",), "Vespa": ("vespa",), "Yamaha": ("yamaha",), "Zero": ("zero",),
    "Damon": ("damon",), "Genuine": ("genuine",),
    # not makes in the junction, but named in it
    "Gilera": ("gilera",), "Husqvarna": ("husqvarna",), "Moto Morini": ("moto morini", "morini"),
    "Cagiva": ("cagiva",), "Benelli": ("benelli",), "Bimota": ("bimota",),
}
# Words that make a junction string prose, not a name (F135), each seen in the
# junction: "2020 service manual", "positive earth through 1978",
# "approximately 2016 to 2020", "changeover around 2016-2017", "2017 campaign
# population", "2024 build", "pre-2025 platform", "1200 badges", "950 through
# 1290 generations", "990 LC8 twins", "R1150 oilhead boxers", "loaded V4",
# "S 1000 RR by type code", "air-cooled 790", "carburetted 790",
# "65-degree longitudinal V4".
PROSE_WORDS = {"to", "through", "around", "approximately", "by", "service", "manual", "campaign",
               "population", "build", "badges", "platform", "generations", "earth", "changeover",
               "pre", "twins", "boxers", "loaded", "type", "code", "cooled", "carburetted", "degree"}


def _words(s: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).split()


def not_a_machine(make: str, spelling: str) -> str | None:
    """The class of a spelling that cannot be a machine name, or None."""
    w = _words(spelling)
    if not w:
        return "prose"
    joined = " " + " ".join(w) + " "
    for marque, names in MARQUES.items():
        for n in names:
            if joined.startswith(" " + n + " "):
                if marque != make:
                    return "other_marque"
                if joined.strip() == n:
                    return "marque_name"
    if PROSE_WORDS.intersection(w):
        return "prose"
    if re.fullmatch(r"\d+\s*(cc)?", spelling.strip(), re.I):
        return "bare_number"
    return None


def classes(db: pathlib.Path, make: str | None = None) -> dict[str, dict[str, list[str]]]:
    """{make: {class: [spelling]}} over the census, `machine` for the rest."""
    out: dict[str, dict[str, list[str]]] = {}
    for mk, entries in census(db, make).items():
        by: dict[str, list[str]] = collections.defaultdict(list)
        for e in entries:
            by[not_a_machine(mk, e["model"]) or "machine"].append(e["model"])
        out[mk] = dict(by)
    return out


def census(db: pathlib.Path, make: str | None = None) -> dict[str, list[dict]]:
    """{make: [{"model", "rows"}]} for every unknown pair, rows descending."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        pairs = c.execute("SELECT make, model, count(*) FROM known_issue_models "
                          "GROUP BY make, model").fetchall()
    finally:
        c.close()
    out: dict[str, list[dict]] = collections.defaultdict(list)
    for mk, md, n in pairs:
        if make and mk != make:
            continue
        if resolve_transmission(mk, md).provenance == "unknown":
            out[mk].append({"model": md, "rows": n})
    return {mk: sorted(v, key=lambda e: (-e["rows"], e["model"]))
            for mk, v in sorted(out.items(), key=lambda kv: (-len(kv[1]), kv[0]))}


def main(argv: list[str]) -> int:
    db = pathlib.Path(next((a for a in argv if not a.startswith("--") and
                            argv[argv.index(a) - 1] != "--make"), REPO / "data" / "motodiag.db"))
    make = argv[argv.index("--make") + 1] if "--make" in argv else None
    result = census(db, make)
    if "--json" in argv:
        print(json.dumps(result, indent=1))
    else:
        cls = classes(db, make)
        kinds = ("machine", "bare_number", "other_marque", "marque_name", "prose")
        print(f"{'':20s} {'total':>5s} " + " ".join(f"{k:>12s}" for k in kinds))
        for mk, entries in result.items():
            print(f"{mk:20s} {len(entries):5d} " + " ".join(f"{len(cls[mk].get(k, [])):12d}" for k in kinds))
        print(f"{'TOTAL':20s} {sum(len(v) for v in result.values()):5d} "
              + " ".join(f"{sum(len(c.get(k, [])) for c in cls.values()):12d}" for k in kinds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
