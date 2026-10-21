"""Phase 384's mutations: each breaks one thing the phase built, and the check beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/384_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 383's harness:
exact strings (each must occur once), the check run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`D` the desktop's dispatcher, `C` the Mac's client, `M` the video check,
`V` verify_phase.sh's checks 8 and 9, `I` the installer.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DISP = "ops/desktop/motodiag_remote.py"
INST = "ops/desktop/install_remote.sh"
CLIENT = ".claude/skills/deploy/remote.py"
MEDIA = ".claude/skills/deploy/media_check.py"
VERIFY = ".claude/skills/closeout/verify_phase.sh"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_DISP = pytest("tests/test_phase384_remote_dispatcher.py")
T_CLIENT = pytest("tests/test_phase384_remote_client.py")
T_MEDIA = pytest("tests/test_phase384_media_check.py")
T_INST = pytest("tests/test_phase384_install_remote.py")

MUTATIONS = [
    ("D1 a shell joins the list", [(DISP,
     '    "server-pull": (),\n}', '    "server-pull": (),\n    "shell": (),\n}')], T_DISP),
    ("D2 any phase id", [(DISP, '"phase": r"\\d{3}[A-Z]?",', '"phase": r".+",')], T_DISP),
    ("D3 a short or upper-case commit", [(DISP,
     '"commit": r"[0-9a-f]{40}",', '"commit": r"[0-9a-fA-F]{12,40}",')], T_DISP),
    ("D4 any label", [(DISP, '"label": r"[a-z0-9_-]{1,32}",', '"label": r".+",')], T_DISP),
    ("D5 extra arguments pass", [(DISP,
     "    if len(args) != len(kinds):", "    if len(args) < len(kinds):")], T_DISP),
    ("D6 an empty request is not refused", [(DISP,
     "    if not command or not command.strip():", "    if command is None:")], T_DISP),
    ("D7 a dirty checkout runs", [(DISP,
     "        if dirty:\n            raise Refused(f\"the development checkout",
     "        if False:\n            raise Refused(f\"the development checkout")], T_DISP),
    ("D8 the head is not compared", [(DISP,
     "        if head != commit:", "        if False:")], T_DISP),
    ("D9 a tracked diff is deleted", [(DISP, "        if tracked:", "        if False:")], T_DISP),
    ("D10 the diff stays in the checkout", [(DISP,
     '            self.to_outbox(phase, "dryrun" if mode == "dryrun" else "live")',
     "            pass")], T_DISP),
    ("D11 sudo may prompt", [(DISP,
     '["sudo", "-n", "systemctl", verb, UNIT]', '["sudo", "systemctl", verb, UNIT]')], T_DISP),
    ("D12 the server pulls on any branch", [(DISP,
     '        if branch != "master":', "        if False:")], T_DISP),
    ("D13 live-check never verifies", [(DISP,
     '        if not list(self.p.dev.glob(f"docs/phases/*/{phase}_dryrun_diff.md")):',
     "        if True:")], T_DISP),
    ("D14 a request is not logged", [(DISP,
     '    log(paths, command, f"exit {code}")', "    pass")], T_DISP),
    ("C1 SSH may prompt", [(CLIENT, '"-o", "BatchMode=yes", ', "")], T_CLIENT),
    ("C2 SSH offers every key", [(CLIENT, '"-o", "IdentitiesOnly=yes",', "")], T_CLIENT),
    ("C3 a missing key is accepted", [(CLIENT,
     "    if not key.is_file():", "    if False:")], T_CLIENT),
    ("C4 a dirty tree is sent", [(CLIENT,
     '    if _git(repo, "status", "--porcelain")[1]:', "    if False:")], T_CLIENT),
    ("C5 an unpushed head is sent", [(CLIENT,
     '    if not _git(repo, "branch", "-r", "--contains", head)[1]:', "    if False:")], T_CLIENT),
    ("C6 the commit is not added", [(CLIENT,
     "        words = argv + [pushed_head(repo)] if argv[0] in AT_COMMIT else argv",
     "        words = argv")], T_CLIENT),
    ("C7 the sha256 is not compared", [(CLIENT,
     '    if got != sent["sha256"] or sent["name"] != f"{phase}_{kind}_diff.md":',
     '    if sent["name"] != f"{phase}_{kind}_diff.md":')], T_CLIENT),
    ("C8 the file's name is not compared", [(CLIENT,
     '    if got != sent["sha256"] or sent["name"] != f"{phase}_{kind}_diff.md":',
     '    if got != sent["sha256"]:')], T_CLIENT),
    ("M1 the upload's sha256 is not compared", [(MEDIA,
     "{'equals' if served == recorded else", "{'equals' if True else")], T_MEDIA),
    ("M2 a soft-deleted video may serve", [(MEDIA,
     "passed = status == 404 if deleted else", "passed = True if deleted else")], T_MEDIA),
    ("M3 no videos passes", [(MEDIA, "    ok = bool(results)", "    ok = True")], T_MEDIA),
    ("V1 a failure through the way in passes", [(VERIFY,
     "  if [ $REMOTE_CODE -ne 0 ] && [ $REMOTE_CODE -ne 2 ]; then", "  if false; then")], T_INST),
    ("V2 no way in passes", [(VERIFY,
     "  if [ $REMOTE_CODE -ne 0 ] && [ $REMOTE_CODE -ne 2 ]; then",
     "  if [ $REMOTE_CODE -ne 0 ] && [ $REMOTE_CODE -ne 2 ] && [ $REMOTE_CODE -ne 4 ]; then")],
     T_INST),
    ("V3 check 9 lists the Mac's own folder", [(VERIFY,
     'else "$PY" -B "$DIR/../deploy/remote.py" backups; fi',
     "else ls -lh ~/backups/motodiag/; fi")], T_INST),
    ("I1 sshd listens everywhere", [(INST, "ListenAddress $TS4:22\n", "")], T_INST),
    ("I2 any user from anywhere", [(INST, "AllowUsers $USER_NAME@$MAC_IP\n", "")], T_INST),
    ("I3 passwords allowed", [(INST,
     "PasswordAuthentication no", "PasswordAuthentication yes")], T_INST),
    ("I4 forwarding allowed", [(INST, "DisableForwarding yes", "DisableForwarding no")], T_INST),
    ("I5 no forced command", [(INST, "ForceCommand $DISPATCHER\n", "")], T_INST),
    ("I6 the socket on every address", [(INST,
     "ListenStream=\nListenStream=$TS4:22\n", "ListenStream=0.0.0.0:22\n")], T_INST),
    ("I7 the socket fails at boot", [(INST, "FreeBind=yes\n", "")], T_INST),
    ("I8 the key unrestricted", [(INST,
     "printf '%s\\nrestrict,from=\"%s\",command=\"%s\" %s\\n'",
     "printf '%s\\nfrom=\"%s\",command=\"%s\" %s\\n'")], T_INST),
    ("I9 Tailscale's own SSH on", [(INST, "--accept-dns=false --ssh=false", "--accept-dns=false --ssh")],
     T_INST),
    ("I10 an existing key file replaced", [(INST,
     'if [ -s "$AK" ] && ! grep -qF "$MARK" "$AK"; then', "if false; then")], T_INST),
    ("I11 the dispatcher run from the checkout", [(INST,
     "DISPATCHER=/usr/local/libexec/motodiag-remote",
     "DISPATCHER=$REPO/ops/desktop/motodiag_remote.py")], T_INST),
    ("I12 what listens is not checked", [(INST,
     '[ "$LISTEN" = "$TS4:22" ] ||', "true ||")], T_INST),
    ("I13 a key broken across lines passes", [(INST,
     '[ "$(printf \'%s\' "$KEY" | wc -l)" -eq 0 ] ||', "true ||")], T_INST),
    ("I14 the key file's lines are not counted", [(INST,
     '[ "$(wc -l < "$AK")" -eq 2 ] ||', "true ||")], T_INST),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude", ROOT / "scripts", ROOT / "ops"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


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
        originals = {}
        try:
            for rel, old, new in edits:
                path = ROOT / rel
                originals.setdefault(rel, path.read_text())
                current = path.read_text()
                assert current.count(old) == 1, f"{name}: the text occurs {current.count(old)} times in {rel}"
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
