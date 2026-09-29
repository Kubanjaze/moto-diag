"""Phase 361 Step 0: what the API does with each powertrain and engine_type value (scratch DB)."""
import os, sys, tempfile
d = tempfile.mkdtemp(dir=sys.argv[1])
path = os.path.join(d, "probe.db")
os.environ["MOTODIAG_DB_PATH"] = path
for t in ("ANONYMOUS", "INDIVIDUAL", "SHOP", "COMPANY"):
    os.environ[f"MOTODIAG_RATE_LIMIT_{t}_PER_MINUTE"] = "9999"
from motodiag.core.config import reset_settings; reset_settings()
from motodiag.core.database import init_db, get_connection
init_db(path)
from fastapi.testclient import TestClient
from motodiag.api import create_app
from motodiag.auth.api_key_repo import create_api_key
with get_connection(path) as c:
    uid = c.execute("INSERT INTO users (username,email,tier,is_active) VALUES ('p','p@x','company',1)").lastrowid
_, key = create_api_key(uid, db_path=path)
cl = TestClient(create_app(db_path_override=path), raise_server_exceptions=False)
H = {"X-API-Key": key}
base = {"make": "Honda", "model": "CHF50", "year": 2005}
def stored(vid):
    with get_connection(path) as c:
        return tuple(c.execute("select powertrain, engine_type from vehicles where id=?", (vid,)).fetchone())
r = cl.post("/v1/vehicles", headers=H, json=base); vid = r.json()["id"]
print("POST (no powertrain, no engine_type):", r.status_code, "stored", stored(vid))
for f, vals in (("powertrain", ["ice","electric","hybrid","hybrid_parallel","hybrid_series"]),
                ("engine_type", ["four_stroke","two_stroke","rotary","diesel","none","electric_motor","hybrid","desmodromic"])):
    for v in vals:
        r = cl.post("/v1/vehicles", headers=H, json={**base, f: v})
        s = stored(r.json()["id"]) if r.status_code == 201 else None
        if r.status_code == 201:
            cl.delete(f"/v1/vehicles/{r.json()['id']}", headers=H)
        rp = cl.patch(f"/v1/vehicles/{vid}", headers=H, json={f: v})
        print(f"{f}={v!r}: POST {r.status_code} stored {s}; PATCH {rp.status_code} stored {stored(vid)}")
