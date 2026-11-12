"""Phase 371B's mutations, and the new tests run against the code before the fix.

Run from the repository root:
`.venv/bin/python docs/phases/in_progress/371B_mutate.py`. ROOT is three
levels up from in_progress/ or completed/. Output goes to stdout, and the
phase keeps it in `371B_mutate.out`.

Every mutation is applied to a **copy**. These are copied to a temporary
folder:
- `src/`;
- `tests/conftest.py`, `tests/support/` and `tests/fixtures/`;
- the phase's two test files;
- the deploy skill's folder, because the conftest reads `live.py`.

The copy is edited, and the tests run there with the copy's `src` first on
`PYTHONPATH`; the venv's editable install is a `.pth` path, which comes
after it. The checkout is never written. Each edit's text must occur
once. The script exits 1 if any mutation stays green.

`--old` instead runs the new tests against `monitor.py` as it was at
`OLD_REF`, the master this phase started from. That is 371's code, which
sends the key twice. It prints each test's outcome and the counts.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
OLD_REF = "1b7e40d"

MON = "src/motodiag/telemetry/monitor.py"
T_NEW = "tests/test_phase371B_checkin_key_once.py"
T_371 = "tests/test_phase371_monitor.py"
TESTS = (T_NEW, T_371)

HEADERS = '    headers = {"Content-Type": "application/json"}\n'

MUTATIONS = [
    ("M1 the X-Sentry-Auth header comes back",
     [(MON, HEADERS,
       '    headers = {"Content-Type": "application/json",\n'
       '               "X-Sentry-Auth": dsn.auth_header}\n')]),
    ("M2 an Authorization header with the Sentry scheme is added",
     [(MON, HEADERS,
       '    headers = {"Content-Type": "application/json",\n'
       '               "Authorization": dsn.auth_header}\n')]),
    ("M3 the key is added to the URL's query as well",
     [(MON, "send(checkin_url(dsn, slug), headers, body)",
       'send(checkin_url(dsn, slug) + "?sentry_key=" + dsn.public_key, headers, body)')]),
    ("M4 the key is left out of the URL",
     [(MON, 'f"{dsn.project_id}/cron/{slug}/{dsn.public_key}/")',
       'f"{dsn.project_id}/cron/{slug}/")')]),
]


def make_copy() -> pathlib.Path:
    work = pathlib.Path(tempfile.mkdtemp(prefix="371B_mutate_"))
    shutil.copytree(ROOT / "src", work / "src",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (work / "tests").mkdir()
    shutil.copy(ROOT / "tests" / "conftest.py", work / "tests" / "conftest.py")
    shutil.copytree(ROOT / "tests" / "support", work / "tests" / "support",
                    ignore=shutil.ignore_patterns("__pycache__"))
    # tests/support/stripe_fixtures.py reads tests/fixtures/phase273 (371's tests use it).
    shutil.copytree(ROOT / "tests" / "fixtures", work / "tests" / "fixtures")
    for rel in TESTS:
        shutil.copy(ROOT / rel, work / rel)
    shutil.copytree(ROOT / ".claude" / "skills" / "deploy",
                    work / ".claude" / "skills" / "deploy",
                    ignore=shutil.ignore_patterns("__pycache__"))
    return work


def run(work: pathlib.Path, *extra: str, tests: tuple[str, ...] = TESTS) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(work / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "-p", "no:xdist", "-o", "addopts=", "--rootdir", str(work), *extra, *tests],
        cwd=work, capture_output=True, text=True, env=env,
    )


def check_copy_is_imported(work: pathlib.Path) -> None:
    env = dict(os.environ, PYTHONPATH=str(work / "src"))
    out = subprocess.run(
        [sys.executable, "-B", "-c", "import motodiag; print(motodiag.__file__)"],
        cwd=work, capture_output=True, text=True, env=env,
    ).stdout.strip()
    assert out.startswith(str(work)), f"the copy is not what is imported: {out}"


def mutate(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    work = make_copy()
    try:
        check_copy_is_imported(work)
        assert run(work, "-x").returncode == 0, "not green before mutating"
        print("K1 the copy without a mutation: green", flush=True)
        survivors = []
        for name, edits in chosen:
            originals: dict[str, str] = {}
            try:
                for rel, old, new in edits:
                    path = work / rel
                    originals.setdefault(rel, path.read_text())
                    current = path.read_text()
                    assert current.count(old) == 1, \
                        f"{name}: the text occurs {current.count(old)} times in {rel}"
                    path.write_text(current.replace(old, new))
                code = run(work, "-x").returncode
            finally:
                for rel, text in originals.items():
                    (work / rel).write_text(text)
            verdict = "red" if code != 0 else "GREEN (survived)"
            print(f"{name}: {verdict}", flush=True)
            if code == 0:
                survivors.append(name)
        assert run(work, "-x").returncode == 0, "not green after restoring"
        print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
        return 1 if survivors else 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def old() -> int:
    work = make_copy()
    try:
        text = subprocess.run(["git", "show", f"{OLD_REF}:{MON}"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout
        (work / MON).write_text(text)
        check_copy_is_imported(work)
        result = run(work, "-rA", tests=(T_NEW,))
        lines = [ln for ln in result.stdout.splitlines()
                 if ln.startswith(("PASSED ", "FAILED ", "ERROR "))]
        print(f"the new tests against {MON} at {OLD_REF}:")
        for ln in sorted(lines):
            outcome, node = ln.split(" - ")[0].split(" ", 1)
            print(outcome, node.rsplit("::", 1)[-1])
        print(result.stdout.strip().splitlines()[-1])
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--old"]:
        sys.exit(old())
    sys.exit(mutate(args))
