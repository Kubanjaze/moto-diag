"""Phase 345's mutations: each breaks one promise, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/345_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 396's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__` under `src/` (a same-length edit in the same second could
otherwise load a stale .pyc), every file restored whatever happens. Exits 1
if any mutation stays green. An argument runs only the mutations whose name
starts with it.

No mutation reads live or opens a socket beyond loopback.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

B = "src/motodiag/backup/"
CRYPT, STORE, SNAP, REST, SET = (B + "crypt.py", B + "store.py", B + "snapshot.py",
                                 B + "restore.py", B + "settings.py")


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_CRYPT = pytest("tests/test_phase345_crypt.py")
T_STORE = pytest("tests/test_phase345_store.py")
T_SNAP = pytest("tests/test_phase345_snapshot_restore.py")
T_SET = pytest("tests/test_phase345_backup_settings.py")

MUTATIONS = [
    ("M1 the tag check removed from decrypt_file",
     [(CRYPT, "                    fout.write(dec.finalize_with_tag(tag))",
       "                    pass")], T_CRYPT),
    ("M2 the host header dropped from the signed headers",
     [(STORE, "self.region,\n" + " " * 49 + "method, path, params, headers, payload_hash)",
       "self.region,\n" + " " * 49 + 'method, path, params, {k: v for k, v in '
       'headers.items() if k != "host"}, payload_hash)')], T_STORE),
    ("M3 the media skip inverted: every file re-uploaded",
     [(SNAP, "        if key in have:", "        if False:")], T_SNAP),
    ("M4 pick chooses the newest after `at`, not before",
     [(REST, "r.taken_at <= at]", "r.taken_at >= at]")], T_SNAP),
    ("M5 the over-live refusal removed",
     [(REST, "        if _overlaps(target, folder):", "        if False:")], T_SNAP),
    ("M6 the mode check removed",
     [(SET, "    if mode & 0o077:", "    if False:")], T_SET),
    ("M7 the manifest uploaded before the database",
     [(SNAP, '        store.put(folder + DB_OBJECT, plain[1], cipher_sha)\n'
             '        counts["bytes_sent"] += plain[1].stat().st_size\n', ""),
      (SNAP, '        counts["bytes_sent"] += plain[3].stat().st_size\n',
       '        counts["bytes_sent"] += plain[3].stat().st_size\n'
       '        store.put(folder + DB_OBJECT, plain[1], cipher_sha)\n'
       '        counts["bytes_sent"] += plain[1].stat().st_size\n')], T_SNAP),
    ("M8 list_snapshots lists a folder that has no manifest",
     [(REST, "if DB_OBJECT not in objects or MANIFEST_OBJECT not in objects:",
       "if DB_OBJECT not in objects:")], T_SNAP),
]


def clear_caches() -> None:
    for d in (ROOT / "src").rglob("__pycache__"):
        for f in d.glob("*.pyc"):
            f.unlink()


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals: dict[str, str] = {}
        try:
            for rel, old, new in edits:
                path = ROOT / rel
                originals.setdefault(rel, path.read_text())
                current = path.read_text()
                assert current.count(old) == 1, \
                    f"{name}: the text occurs {current.count(old)} times in {rel}"
                path.write_text(current.replace(old, new))
            code = run(command)
        finally:
            for rel, text in originals.items():
                (ROOT / rel).write_text(text)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
