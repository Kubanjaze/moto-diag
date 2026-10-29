"""Phase 393 Step 0: one fenced model-free pytest run, as Fleet.check_run makes it.
    fenced_measure.py <state-dir> <commit> <cov|nocov> <tag>"""
import pathlib, sys, time
ROOT = pathlib.Path("/home/lilcu/Projects/moto-diag")
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "fleet"))
import dispatcher as D
state, commit, mode, tag = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
fleet = D.Fleet(state=state, venv=pathlib.Path.home() / ".local/state/motodiag/fleet/venv",
                mobile=pathlib.Path.home() / "Projects/moto-diag-mobile")
cov = (f"--cov=motodiag --cov-report=json:/fleet/run/{tag}.json --cov-report=" if mode == "cov" else "")
cmd = ["T0=$(date +%s);", f"COVERAGE_FILE=/fleet/run/{tag}.data", "PYTHONUTF8=1",
       ".venv/bin/python -m pytest -n auto --dist load -q -p no:cacheprovider -rA", cov,
       f"> /fleet/run/{tag}.log 2>&1; echo rc=$? wall=$(( $(date +%s) - T0 ))"]
t0 = time.time()
c = fleet.check_run(ROOT, commit, full=False, command=cmd)
print(f"ok={c.ok} wall_outside={time.time()-t0:.0f}s")
print(c.out[-500:])
print(sorted((state / "runs").glob("*_check"))[-1])
