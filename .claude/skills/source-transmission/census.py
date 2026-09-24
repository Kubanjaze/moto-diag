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
| `bare_number` | a number named in NOT_A_MODEL_NUMBER, with its rows | Ducati `1000`, MV Agusta `20`, Aprilia `1077cc` — not Ducati `916` |
| `other_marque` | starts with another marque's name | `Gilera` under six makes, Ducati `Guzzi V85` |
| `marque_name` | the make's own name or short name | MV Agusta `MV` |
| `prose` | junction prose (F135): a named non-model word | `2020 service manual`, `approximately 2016 to 2020` |
| `engine_family` | named in NOT_A_MACHINE_NAMED: an engine, not a machine | Ducati `Testastretta`, `Superquadro` |
| `other_make_model` | named: another make's machine attached by a shared row | Ducati `S 1000 XR` — not BMW's |

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

# Numbers that are NOT a model name, each shown from its junction rows
# (known_issues.id). Named, never by shape: a number is often exactly what a
# maker calls the machine — Ducati 916, 996, 1299; Vespa 946; MV Agusta 910 —
# and the shape rule this replaced (bug fix #1) dropped every one of them.
# A number not listed here is a machine name, and strict E4 then demands the
# document name it after the make ("Ducati 916").
NOT_A_MODEL_NUMBER: dict[tuple[str, str], str] = {
    ("Ducati", "06"): "year fragment: 'Monster S4R 2003–06' (#901)",
    ("MV Agusta", "20"): "year fragment: 'Turismo Veloce 800 MY2015–20' (#893)",
    ("Ducati", "1000"): "fragment: 'BMW S 1000 R …; Ducati generally' (#912), 'Multistrada 620/1000/1100' (#909)",
    ("Ducati", "1100"): "fragment of 'Monster 696 / 796 / 1100' (#820, #822), 'Hypermotard 1100' (#909)",
    ("Ducati", "1200"): "fragment of 'Monster 821 / 1200' (#823, #824), 'Multistrada 1200' (#835)",
    ("Ducati", "1260"): "fragment of 'Multistrada 1200 / 1260' (#830, #835, #836)",
    ("Ducati", "796"): "fragment of 'Monster 696 / 796 / 1100' (#820, #821, #822)",
    ("Triumph", "750"): "displacement badge: '750, 900, 1000 and 1200 badges' (#1508); '… into the 750' (#1503)",
    ("Triumph", "900"): "displacement badge (#1508); 'modern classics — 900 and 1200' (#1472)",
    ("Triumph", "1000"): "displacement badge (#1508); BMW 'S 1000' fragment (#912)",
    ("Triumph", "1200"): "displacement badge (#1508); 'liquid-cooled 1200 modern classics' (#1471, #1472)",
    ("Triumph", "865"): "engine size of the air-cooled Bonneville family (#1467, #1468)",
    ("Triumph", "1050"): "engine size: '1050 Speed Triple', 'Speed Triple 1050' (#878, #1493, #1498)",
    ("KTM", "125"): "fragment of '125–390 (Bosch)' — an engine-management range (#1292)",
    ("KTM", "250"): "fragment of '250/300 EXC' and '250/350/450/500 EXC-F' (#1300, #1302, #1303)",
    ("KTM", "350"): "fragment of '250/350/450/500 EXC-F' (#1300)",
    ("KTM", "450"): "fragment of '450 SX-F, 450/500 EXC-F' (#890, #1300)",
    ("KTM", "950"): "engine platform: '950 and 990 LC8 twins' (#873, #883, #904)",
    ("KTM", "1090"): "fragment of 'Adventure 1050/1090/1190/1290' (#910)",
    ("KTM", "1190"): "fragment of 'Adventure 1050/1090/1190/1290' (#910)",
    ("KTM", "1290"): "fragment: '1290 variants' (#1274), 'Adventure …/1290' (#910)",
    ("Aprilia", "900"): "fragment of 'Shiver 750/900 and Dorsoduro 750/900' — two machines (#661, #662, #664)",
    ("Aprilia", "1077cc"): "displacement: 'RSV4 and Tuono V4 — 999.6cc, 1077cc and 1099cc' (#674)",
    ("Aprilia", "1099cc"): "displacement (#674)",
}

# Named, make-scoped, one reason each (operator decision 2026-09-23). The
# same spelling under its own make is a machine: (BMW, "S 1000 XR") is not
# listed and stays one.
NOT_A_MACHINE_NAMED: dict[tuple[str, str], tuple[str, str]] = {
    ("Ducati", "Testastretta"): ("engine_family", "Ducati's liquid-cooled twin family (#806–#810, #823–#825)"),
    ("Ducati", "Desmoquattro"): ("engine_family", "Ducati's 4-valve twin family (#806–#810, #818, #819, #901)"),
    ("Ducati", "Superquadro"): ("engine_family", "the 1199/1299/899/959 Panigale engine (#806–#810, #837, #841)"),
    ("Ducati", "Desmodue"): ("engine_family", "Ducati's air-cooled 2-valve family (#806–#810)"),
    ("Ducati", "Desmoquattro 16-valve"): ("engine_family", "'Desmoquattro 16-valve — 851, 888, 748, …' (#881)"),
    ("Ducati", "Testastretta MY2010"): ("engine_family", "an engine generation (#886)"),
    ("Ducati", "998 Testastretta"): ("engine_family", "the S4RS's engine: '996 Desmoquattro and 998 Testastretta' (#819)"),
    # Row #912 reads 'BMW S 1000 R, S 1000 XR, S 1000 RR by type code; Ducati
    # generally' and is attached to five other makes.
    ("Ducati", "S 1000 XR"): ("other_make_model", "BMW's machine, from #912"),
    ("Aprilia", "S 1000 XR"): ("other_make_model", "BMW's machine, from #912"),
    ("Moto Guzzi", "S 1000 XR"): ("other_make_model", "BMW's machine, from #912"),
    ("Triumph", "S 1000 XR"): ("other_make_model", "BMW's machine, from #912"),
    ("KTM", "S 1000 XR"): ("other_make_model", "BMW's machine, from #912"),
    # Row #886, a Ducati engine generation, is attached to three other makes.
    ("KTM", "Testastretta MY2010"): ("other_make_model", "Ducati's engine, from #886"),
    ("BMW", "Testastretta MY2010"): ("other_make_model", "Ducati's engine, from #886"),
    ("MV Agusta", "Testastretta MY2010"): ("other_make_model", "Ducati's engine, from #886"),
    # Multi-make rows pair every model with every make in the junction (F142):
    # #4593 and #4596 have make 'Kymco, SYM'; #4603 'Yamaha, Kymco, SYM, Genuine'.
    ("Kymco", "Jet 14"): ("other_make_model", "SYM's scooter, from 'Kymco, SYM' rows #4593, #4596"),
    ("Kymco", "Fiddle 4"): ("other_make_model", "SYM's scooter, from 'Kymco, SYM' row #4596"),
    ("Kymco", "Wolf CR300i"): ("other_make_model", "SYM's motorcycle, from 'Kymco, SYM' rows #4593, #4596"),
    ("SYM", "X-Town 300"): ("other_make_model", "Kymco's scooter, from 'Kymco, SYM' rows #4593, #4596"),
    ("Kymco", "XC50"): ("other_make_model", "Yamaha's (Vino) scooter, from row #4603"),
    ("SYM", "XC50"): ("other_make_model", "Yamaha's (Vino) scooter, from row #4603"),
    ("Genuine", "XC50"): ("other_make_model", "Yamaha's (Vino) scooter, from row #4603"),
}


def _words(s: str) -> list[str]:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).split()


def not_a_machine(make: str, spelling: str) -> str | None:
    """The class of a spelling that cannot be a machine name, or None."""
    named = NOT_A_MACHINE_NAMED.get((make, spelling.strip()))
    if named:
        return named[0]
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
    if (make, spelling.strip()) in NOT_A_MODEL_NUMBER:
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
        kinds = ("machine", "bare_number", "other_marque", "marque_name", "prose", "engine_family",
                 "other_make_model")
        print(f"{'':20s} {'total':>5s} " + " ".join(f"{k:>12s}" for k in kinds))
        for mk, entries in result.items():
            print(f"{mk:20s} {len(entries):5d} " + " ".join(f"{len(cls[mk].get(k, [])):12d}" for k in kinds))
        print(f"{'TOTAL':20s} {sum(len(v) for v in result.values()):5d} "
              + " ".join(f"{sum(len(c.get(k, [])) for c in cls.values()):12d}" for k in kinds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
