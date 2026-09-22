"""Phase 255C — the extraction gate's pinned sets, in one place.

SSOT for every canonical-string literal this phase pins, so the next
form change is one edit rather than sixteen. Operator's decision,
2026-09-22.
"""


#: The strings the extraction gate rejects, pinned as a SET.
#:
#: 244U's orphan pin and Phase 256's `KNOWN_SELF_EXCLUDING` in the same
#: shape: a new rejection fails the suite naming the string, rather than
#: vanishing into a count. Loud means a failing test here — a gate cannot
#: know whether a rejection is legitimate, so it never crashes the loader.
#:
#: Fifty-five strings, 95 junction rows. Every one is prose that reached the
#: junction as a model name: `Electric motorcycles`, `as this corpus names
#: them`, `BMS logs`, down to `year`, `location` and `per handbook`.
#:
#: To change it: if a string here is a real model, the gate is wrong and the
#: fix is in `admits_as_model`, not in this list. If a NEW string appears,
#: read it before adding it.
REJECTED_BY_THE_GATE = frozenset({
    "798cc triple",
    "Aprilia shim-under-bucket",
    "BMS logs",
    "BMW air",
    "CAN generations",
    "Concentric carburettors",
    "DRY slipper clutch",
    "Desmosedici Stradale engines",
    "Ducati desmo",
    "Electric motorcycles",
    "Enduro later years",
    "LC4 engine families",
    "LC4 engines",
    "Piaggio Group marques only",
    "Single-brand handheld units",
    "Triumph Bonneville family",
    "Triumph LC twins",
    "Triumph early Hinckley",
    "Triumph oil-in-frame twins",
    "Triumph siblings that agree",
    "Triumph triples",
    "against KTM",
    "as this corpus names them",
    "belt-driven cams",
    "camhead boxers",
    "camhead final drives",
    "camshafts out",
    "carburetted",
    "cast-aluminium Front Frame",
    "chassis fault-code systems",
    "dealer tool landscape",
    "dry clutch",
    "earlier build",
    "early production",
    "equivalent trims",
    "four-cylinder Brutale",
    "in-tank pump flange",
    "independent",
    "injected",
    "location",
    "longitudinal Telelever",
    "maxi-scooter",
    "module name",
    "nylon fuel tank",
    "one per make",
    "per handbook",
    "rear radar",
    "related",
    "remapped engine management",
    "ride-by-wire",
    "single-sided swingarm",
    "spring valves",
    "transverse four",
    "wet slipper clutch",
    "year",
})


#: Model designations that MUST survive the gate. The negative control is the
#: whole corpus — see `test_the_gate_rejects_exactly_the_pinned_set` — and
#: these are the named cases that make a regression legible.
#:
#: The last four are group (B): they carry a designation code and are
#: admitted whatever else they say. `R1200 hexhead` is a designation 244I is
#: built to carry; `2020 service manual` is debris. No shape rule separates
#: them, and telling them apart is a question about what the corpus means by
#: a model — filed, not guessed.
ADMITTED_BY_THE_GATE = (
    "PCX 150", "F-series", "R-series (airhead)", "250", "125",
    "Brutale 800", "Super Cub C125", "390 Adventure R",
    "S 1000 RR by type code", "XC155",
    "R1200 hexhead", "990 LC8 twins", "798 triples", "2020 service manual",
)
