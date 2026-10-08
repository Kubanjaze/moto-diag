"""F155 measurement: the prompt rows per (machine, symptom), before and after stemming."""
import json, os, sys
from pathlib import Path
REPO = Path("/Users/lilquant/Projects/moto-diag")
out, dbp = sys.argv[1], sys.argv[2]
os.environ["MOTODIAG_DB_PATH"] = dbp
from motodiag.core.config import reset_settings; reset_settings()
from motodiag.core.database import init_db
from motodiag.hardware.compat_loader import seed_all
from motodiag.knowledge.loader import load_dtc_directory, load_known_issues_file
from motodiag.knowledge.marques import rebuild_make_index_at
from motodiag.knowledge.models import rebuild_model_index_at
from motodiag.cli.diagnose import _load_known_issues
SEED = REPO / "src/motodiag/knowledge/seed"
if not Path(dbp).exists():
    init_db(dbp); load_dtc_directory(SEED / "dtc_codes", dbp)
    for f in sorted((SEED / "knowledge").glob("known_issues_*.json")): load_known_issues_file(f, dbp)
    rebuild_make_index_at(dbp); rebuild_model_index_at(dbp)
    seed_all(data_dir=REPO / "src/motodiag/hardware/compat_data", db_path=dbp)
MACHINES = [("Honda","CHF50",2005,"ice"),("Kymco","Agility 50",2015,"ice"),("Kymco","People S 250",2015,"ice"),
 ("SYM","Jet Euro 50",2015,"ice"),("SYM","Joyride 125",2015,"ice"),("SYM","Fiddle 50",2015,"ice"),
 ("Piaggio","Fly 50",2015,"ice"),("Vespa","LX 50",2015,"ice"),("Honda","Ruckus",2015,"ice"),("Honda","Ruckus",2008,"ice"),
 ("Honda","PCX150",2014,"ice"),("Yamaha","Zuma 125",2018,"ice"),("Honda","Metropolitan",2005,"ice"),("Honda","Grom 125",2023,"ice"),
 ("Yamaha","Vino 50",2015,"ice"),("Honda","CBR1000RR",2020,"ice"),
 ("Harley-Davidson","Road King",2015,"ice"),("Honda","CBR600RR",2005,"ice"),("Yamaha","MT-07",2018,"ice"),
 ("BMW","R1200GS",2015,"ice"),("Kawasaki","Ninja 650",2019,"ice"),("Energica","Ego",2020,"electric")]
SYMPTOMS = ["scooter jerks at low speed, belt squeal, won't pull away",
 "battery not charging, lights dim at idle", "brakes squeal and the pads wear fast",
 "engine stalls at idle and runs rough", "won't start when cold, battery is fine",
 "leaking oil from the gaskets and seals"]
res = {}
for make, model, year, pt in MACHINES:
    for s in SYMPTOMS:
        _, rows = _load_known_issues(make, model, year, dbp, powertrain=pt, symptoms=[s])
        res[f"{make}|{model}|{year}|{s}"] = [r["id"] for r in rows]
json.dump(res, open(out, "w"), indent=1)
print(len(res), "combinations")
