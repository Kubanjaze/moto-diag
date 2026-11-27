"""Phase 329's blocks against stand-ins, in a scratch home: the settings
block (4), the undo (7) and the sign-up check (6b) run against the real
server code of this branch, served by uvicorn on 127.0.0.1:8000 from a
scratch database, with `sudo` and `systemctl` as small stand-ins that
restart it on the settings file. Run from the repository root with its
.venv built:  .venv/bin/python docs/phases/in_progress/329_blocks/standin/cases.py
Nothing here reaches the network: curl only reaches the scratch server.
"""
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[5]
BLOCKS = REPO / "docs" / "phases" / "in_progress" / "329_blocks"
PY = sys.executable
KEY = "re_StandIn_0123456789"

SYSTEMCTL = r'''#!/bin/bash
# stand-in: restart = stop the scratch uvicorn and start it on server.env
if [ "$1" = is-active ]; then [ -f "$HOME/payments_down" ] && exit 3; exit 0; fi
if [ "$1" = restart ]; then
  [ -f "$HOME/uvicorn.pid" ] && kill "$(cat "$HOME/uvicorn.pid")" 2>/dev/null
  sleep 0.5
  # setsid: the block runs under `script`, whose end would hang up a child
  # left in its session; systemd owns the real server, so nothing does.
  ( set -a; . "$HOME/.config/motodiag/server.env"; set +a
    exec setsid "$STANDIN_PY" -m uvicorn motodiag.api.app:create_app --factory --host 127.0.0.1 --port 8000 --log-level warning
  ) > "$HOME/uvicorn.log" 2>&1 < /dev/null &
  echo $! > "$HOME/uvicorn.pid"
  exit 0
fi
exit 0
'''


def home():
    h = pathlib.Path(tempfile.mkdtemp(prefix="329standin_"))
    (h / ".config/motodiag").mkdir(parents=True)
    (h / "motodiag/live").mkdir(parents=True)
    os.symlink(REPO, h / "motodiag/server")
    db = h / "motodiag/live/motodiag.db"
    subprocess.run([PY, "-c", f"from motodiag.core.database import init_db; init_db({str(db)!r})"],
                   check=True)
    (h / ".config/motodiag/server.env").write_text(
        f"MOTODIAG_DB_PATH={db}\nMOTODIAG_STRIPE_PRICE_INDIVIDUAL=price_standin\n"
        "MOTODIAG_BILLING_PROVIDER=fake\n")
    os.chmod(h / ".config/motodiag/server.env", 0o600)
    b = h / "bin"
    b.mkdir()
    (b / "systemctl").write_text(SYSTEMCTL)
    (b / "sudo").write_text('#!/bin/bash\nshift_path="$1"; shift; exec "$(basename "$shift_path")" "$@"\n')
    for f in ("systemctl", "sudo"):
        os.chmod(b / f, 0o755)
    return h


def env(h):
    return dict(os.environ, HOME=str(h), PATH=f"{h}/bin:{os.environ['PATH']}", STANDIN_PY=PY,
                PYTHONUTF8="1")


def start(h):
    subprocess.run(["systemctl", "restart", "x"], env=env(h), check=True)
    for _ in range(60):
        r = subprocess.run(["curl", "-fsS", "-m", "2", "http://127.0.0.1:8000/healthz"],
                           capture_output=True, text=True)
        if '"status":"ok"' in r.stdout:
            return
        time.sleep(0.5)
    raise SystemExit("the scratch server did not start: " + (h / "uvicorn.log").read_text())


def stop(h):
    pid = h / "uvicorn.pid"
    if pid.exists():
        subprocess.run(["kill", pid.read_text().strip()])
    time.sleep(0.5)
    shutil.rmtree(h, ignore_errors=True)


def run_block(h, name, typed=""):
    body = (BLOCKS / name).read_text().splitlines()[1:-1]
    script = h / "block.sh"
    script.write_text("\n".join(body) + "\n")
    r = subprocess.run(["script", "-qec", f"bash {script}", "/dev/null"], input=typed,
                       capture_output=True, text=True, env=env(h), timeout=180)
    return r.stdout.replace(typed.strip(), "<typed>") if typed.strip() else r.stdout


results = []


def case(name, ok, out):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name, flush=True)
    if not ok:
        print(out)


def settings_text(h):
    return (h / ".config/motodiag/server.env").read_text()


# 1. the good path, then the undo
h = home(); start(h)
before = settings_text(h)
out = run_block(h, "4_server_settings.txt", KEY + "\n")
s = settings_text(h)
case("4: good key ends ALL GOOD", out.rstrip().endswith("ALL GOOD"), out)
case("4: settings hold resend, its key, both switches, shops off",
     all(x in s for x in ("MOTODIAG_EMAIL_PROVIDER=resend\n", f"MOTODIAG_RESEND_API_KEY={KEY}\n",
                          "MOTODIAG_INDIVIDUAL_SIGNUP_ENABLED=true\n",
                          "MOTODIAG_PASSWORD_RESET_EMAIL_ENABLED=true\n",
                          "MOTODIAG_SELF_SERVE_SIGNUP_ENABLED=false\n")), s)
case("4: the key is never printed", KEY not in out.replace("<typed>", ""), out)
case("4: the old settings are kept", (h / ".config/motodiag/server.env.pre329").read_text() == before, "")
case("4: the file stays private", oct(os.stat(h / ".config/motodiag/server.env").st_mode)[-3:] == "600", "")
out = run_block(h, "4_server_settings.txt", KEY + "\n")
case("4: a second run keeps the first kept copy and ends ALL GOOD",
     out.rstrip().endswith("ALL GOOD") and "already kept" in out
     and (h / ".config/motodiag/server.env.pre329").read_text() == before, out)
out = run_block(h, "7_undo.txt")
case("7: undo ends ALL GOOD and puts the old settings back",
     out.rstrip().endswith("ALL GOOD") and settings_text(h) == before, out)
stop(h)

# 2. refusals that change nothing
for label, typed, prep in [
    ("4: a key that is not Resend's", "sk_live_nope\n", None),
    ("4: a key with odd characters", "re_ab;rm -rf\n", None),
    ("4: no Individual price", KEY + "\n", "price"),
    ("4: the database is not at 93", KEY + "\n", "schema"),
    ("4: the code has no sign-up", KEY + "\n", "code"),
]:
    h = home()
    if prep == "price":
        (h / ".config/motodiag/server.env").write_text(
            settings_text(h).replace("MOTODIAG_STRIPE_PRICE_INDIVIDUAL=price_standin\n", ""))
    if prep == "schema":
        with sqlite3.connect(h / "motodiag/live/motodiag.db") as c:
            c.execute("DELETE FROM schema_version WHERE version = 93")
    if prep == "code":
        os.unlink(h / "motodiag/server")
        (h / "motodiag/server").mkdir()
    start(h)
    before = settings_text(h)
    out = run_block(h, "4_server_settings.txt", typed)
    case(label + " refuses and changes nothing",
         "SOMETHING IS OFF" in out and "ALL GOOD" not in out and settings_text(h) == before, out)
    stop(h)

# 3. put back when the payments feed does not come back
h = home(); start(h)
before = settings_text(h)
(h / "payments_down").write_text("")
out = run_block(h, "4_server_settings.txt", KEY + "\n")
case("4: the payments feed down puts the old settings back",
     "SOMETHING IS OFF" in out and "old settings are back" in out and settings_text(h) == before, out)
stop(h)

# 4. the sign-up check, before and after a completed individual sign-up
h = home()
db = str(h / "motodiag/live/motodiag.db")
out = run_block(h, "6b_signup_check.txt")
case("6b: no sign-up is SOMETHING IS OFF", "SOMETHING IS OFF" in out, out)
code = f"""
from motodiag.auth.signup_repo import create_signup, mark_verified, complete_signup
from motodiag.auth.passwords import hash_password
from motodiag.core.database import get_connection
db = {db!r}
sid = create_signup(email="r@x.example", owner_name="R", username="rita",
                    password_hash=hash_password("correct horse"), shop_name=None,
                    tier="individual", terms_version="1.1", db_path=db)
mark_verified(sid, db_path=db)
done = complete_signup(sid, "sub_1", db_path=db)
with get_connection(db) as c:
    c.execute("INSERT INTO subscriptions (user_id, tier, status, stripe_subscription_id) "
              "VALUES (?, 'individual', 'active', 'sub_1')", (done.user_id,))
"""
subprocess.run([PY, "-c", code], check=True)
out = run_block(h, "6b_signup_check.txt")
case("6b: a completed sign-up is ALL GOOD", out.rstrip().endswith("ALL GOOD"), out)
shutil.rmtree(h, ignore_errors=True)

n = sum(ok for _, ok in results)
print(f"\n{n} of {len(results)}")
sys.exit(0 if n == len(results) else 1)
