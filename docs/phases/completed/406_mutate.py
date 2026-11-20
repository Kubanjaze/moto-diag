"""Phase 406's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/completed/406_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness, as
404's: exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`D` the desktop's dispatcher, `T` the database step's two calls, `C` the
Mac's client, `I` the install.

Nothing here reaches the desktop, live or GitHub: every test it runs uses
stand-ins, a tmp git mirror and a tmp database.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

DSP = "ops/desktop/motodiag_remote.py"
TFL = ".claude/skills/deploy/through_fleet.py"
CLI = ".claude/skills/deploy/remote.py"
SUD = "ops/desktop/install_sudoers.sh"
UPD = "ops/desktop/update_remote.sh"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_OPS = pytest("tests/test_phase406_remote_ops.py")
T_TWO = pytest("tests/test_phase406_through_fleet_split.py")
T_CLI = pytest("tests/test_phase406_remote_client.py")
T_INS = pytest("tests/test_phase406_install.py")

MUTATIONS = [
    ("D1 any branch passes", [(DSP, '"branch": r"phase-\\d{3}[A-Z]?-[a-z0-9-]{1,80}",',
                                '"branch": r"\\S+",')], T_OPS),
    ("D2 any sha256 passes", [(DSP, '"sha256": r"[0-9a-f]{64}",', '"sha256": r"\\S+",')], T_OPS),
    ("D3 feed-stop stops the app server", [(DSP, '"feed-stop": lambda: self.unit(FEED, "stop"),',
                                            '"feed-stop": lambda: self.unit(UNIT, "stop"),')],
     T_OPS),
    ("D4 server-update skips GitHub's master", [(DSP,
     "        self.master_is(srv, commit, what)\n", "")], T_OPS),
    ("D5 a checkout changed by hand is moved", [(DSP,
     "        if dirty:\n            raise Refused(f\"{what} has changes made by hand",
     "        if False:\n            raise Refused(f\"{what} has changes made by hand")], T_OPS),
    ("D6 server-update keeps the new code when the server fails", [(DSP,
     "            if not self.back(srv, before, what):\n                return 1\n", "")], T_OPS),
    ("D7 the feed's restart seen from 'running' alone", [(DSP,
     'if not self.active(FEED) or new in ("", "0", old):',
     "if not self.active(FEED):")], T_OPS),
    ("D8 the app server always healthy", [(DSP,
     "            if '\"status\":\"ok\"' in self.sh.healthz():",
     "            if True:")], T_OPS),
    ("D9 fleet-move ignores a running stage", [(DSP,
     "        if self.stage_running():\n            raise Refused(\"a stage of the fleet",
     "        if False:\n            raise Refused(\"a stage of the fleet")], T_OPS),
    ("D10 fleet-move ignores the search on start", [(DSP,
     'if rc != 0 or said.strip().splitlines()[-1:] != ["nothing to resume"]:',
     "if rc != 0:")], T_OPS),
    ("D11 fleet-move keeps the new code when the fleet fails", [(DSP,
     "        if self.back(code, before, what):\n", "        if True:\n")], T_OPS),
    ("D12 the fleet's start not waited for", [(DSP,
     "            if self.starts() > seen and self.active(FLEET):",
     "            if self.active(FLEET):")], T_OPS),
    ("D13 the fleet's log read up to its first zero byte", [(DSP,
     "            data = path.read_bytes()\n",
     "            data = path.read_bytes().split(b\"\\x00\")[0]\n")], T_OPS),
    ("D14 deploy-apply drops the sha256", [(DSP,
     '"deploy-apply": lambda: self.through_fleet(*args[:3], "--apply", args[3]),',
     '"deploy-apply": lambda: self.through_fleet(*args[:3]),')], T_OPS),
    ("D15 feed-status keeps the caller's MOTODIAG_*", [(DSP,
     'env = {k: v for k, v in os.environ.items() if not k.startswith("MOTODIAG_")}',
     "env = dict(os.environ)")], T_OPS),
    # The review's points (406_phase_log.md, "the review"): each fix, broken.
    ("D16 the put-back not checked", [(DSP,
     '        if rc != 0 or self.git(repo, "rev-parse", "HEAD")[1] != before:',
     "        if False:")], T_OPS),
    ("D17 the put-back checked by its exit alone", [(DSP,
     '        if rc != 0 or self.git(repo, "rev-parse", "HEAD")[1] != before:',
     "        if rc != 0:")], T_OPS),
    ("D18 two changing steps at once", [(DSP,
     "        if name in CHANGING:\n            lock = one_at_a_time(paths)\n", "")], T_OPS),
    ("D19 a Mac gone away ends the step", [(DSP,
     "    try:\n        print(*args, file=file if file is not None else sys.stdout, flush=True)\n"
     "    except (BrokenPipeError, OSError):\n        pass\n",
     "    print(*args, file=file if file is not None else sys.stdout, flush=True)\n")], T_OPS),
    ("D20 commands write to the Mac's channel themselves", [(DSP,
     "        with subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,\n"
     "                              stderr=subprocess.STDOUT, text=True, "
     "errors=\"replace\") as p:\n"
     "            assert p.stdout is not None\n"
     "            for line in p.stdout:\n"
     "                say(line.rstrip(\"\\n\"))\n"
     "        return p.returncode\n",
     "        return subprocess.run(argv, cwd=cwd, env=env).returncode\n")], T_OPS),
    ("D21 server-update reads the settings after the change", [(DSP,
     "        env = self.server_settings()\n        seen = self.checkins()\n",
     "        env = None\n        seen = self.checkins()\n")], T_OPS),
    ("D22 server-update reads the check-ins after the change", [(DSP,
     "        seen = self.checkins()\n", "        seen = 0\n")], T_OPS),
    ("D23 a feed that never checks in passes", [(DSP,
     "            elif not self.checked_in_since(seen):\n"
     "                say(\"the payments feed runs the new code, but no new check-in could be "
     "seen \"\n"
     "                    \"on live in 3 minutes; it asks Stripe as before, so bring this to "
     "the \"\n"
     "                    \"advisor\")\n"
     "                return 1\n", "")], T_OPS),
    ("D24 a feed systemd restarted after a crash passes", [(DSP,
     "            if not self.active(FEED) or self.main_pid(FEED) != pid:",
     "            if not self.active(FEED):")], T_OPS),
    ("D25 a feed that died after its check-in passes", [(DSP,
     "            if not self.active(FEED) or self.main_pid(FEED) != pid:",
     "            if self.main_pid(FEED) != pid:")], T_OPS),
    ("D26 the search on start's exit not read", [(DSP,
     'if rc != 0 or said.strip().splitlines()[-1:] != ["nothing to resume"]:',
     'if said.strip().splitlines()[-1:] != ["nothing to resume"]:')], T_OPS),
    ("D27 the search on start with sshd's PATH", [(DSP,
     "        env = {**os.environ,\n"
     "               \"PATH\": f\"{self.p.home / '.local' / 'bin'}"
     ":/usr/local/bin:/usr/bin:/bin\"}\n",
     "        env = dict(os.environ)\n")], T_OPS),
    ("D28 SIGHUP ends the step", [(DSP,
     "    signal.signal(signal.SIGHUP, signal.SIG_IGN)\n", "")], T_OPS),
    ("D29 the fleet's start seen while it is not running", [(DSP,
     "            if self.starts() > seen and self.active(FLEET):",
     "            if self.starts() > seen:")], T_OPS),
    ("D30 a line that is not UTF-8 ends the step", [(DSP,
     'stderr=subprocess.STDOUT, text=True, errors="replace") as p:',
     "stderr=subprocess.STDOUT, text=True) as p:")], T_OPS),
    ("D31 384's backups print to the closed channel", [(DSP,
     '        say(f"backups ({self.p.backups}): {len(files)}")',
     '        print(f"backups ({self.p.backups}): {len(files)}")')], T_OPS),
    ("D32 384's fetch prints to the closed channel", [(DSP,
     '        say(json.dumps({"name": f.name,',
     '        print(json.dumps({"name": f.name,')], T_OPS),
    ("D33 a check-in unreadable after the change is a refusal", [(DSP,
     "        try:\n            return self.checkins() > seen\n        except Refused:\n"
     "            return False\n",
     "        return self.checkins() > seen\n")], T_OPS),
    ("D34 server-update reads the settings again after the change", [(DSP,
     "        status = self.feed_status(env)\n", "        status = self.feed_status()\n")],
     T_OPS),
    ("T1 the apply skips the sha256", [(TFL, "    if D.sha256(diff) != sha:\n",
                                        "    if False:\n")], T_TWO),
    ("T2 the apply skips a moved branch", [(TFL,
     "    if head != commit:\n        at = head[:12]",
     "    if False:\n        at = head[:12]")], T_TWO),
    ("T3 the apply without a dry run", [(TFL,
     "    if not diff.is_file():\n        raise Off(\"there is no dry run here",
     "    if False:\n        raise Off(\"there is no dry run here")], T_TWO),
    ("T4 the dry run alone prints no sha256", [(TFL,
     '    say(f"{SHA_LINE}{D.sha256(D.diff_path(co, phase))}")\n', "")], T_TWO),
    ("T5 the answer says the desktop asked", [(TFL,
     'where="on the Mac, through the way in (Phase 406; the time is when the "',
     'where="on the home desktop (the time is when the "')], T_TWO),
    ("T7 the answer says the operator's words were seen", [(TFL,
     'typed="The answer was typed on the Mac, not here. The Mac\'s `remote.py "',
     'typed="The operator typed, verbatim. The Mac\'s `remote.py "')], T_TWO),
    ("T6 the apply of another commit's dry run", [(TFL,
     '    if _git(co, "rev-parse", "HEAD").stdout.strip() != commit:\n',
     "    if False:\n")], T_TWO),
    ("C1 yes asked before the list", [
        (CLI, "    code, lines = run_lines(ssh_argv(way, [\"deploy-dryrun\", phase, branch, commit]))\n",
         "    words = ask(QUESTION)\n"
         "    code, lines = run_lines(ssh_argv(way, [\"deploy-dryrun\", phase, branch, commit]))\n"),
        (CLI, "    words = ask(QUESTION)\n    if words.strip().lower() != \"yes\":",
         "    if words.strip().lower() != \"yes\":")], T_CLI),
    ("C2 any answer is a yes", [(CLI, '    if words.strip().lower() != "yes":',
                                  "    if not words.strip():")], T_CLI),
    ("C3 the first of several sha256 lines taken", [(CLI, "    if len(shas) != 1:",
                                                     "    if not shas:")], T_CLI),
    ("C4 deploy-step's arguments unchecked", [(CLI,
     "            if len(args) != 3 or not all(re.fullmatch(p, a) for p, a in zip(STEP_ARGS, args)):",
     "            if len(args) != 3:")], T_CLI),
    ("C5 deploy-apply sent on its own", [(CLI,
     "        if argv[0] == \"deploy-apply\":\n"
     "            raise NoWayIn(\"deploy-apply is sent only by deploy-step, "
     "after the dry run's list \"\n"
     "                          \"and your yes: run remote.py deploy-step "
     "<phase> <branch> <commit>\")\n",
     "")], T_CLI),
    ("I1 a wider password-free rule", [(SUD, "/usr/bin/systemctl restart motodiag-fleet.service\n",
                                        "/usr/bin/systemctl restart motodiag-fleet.service, "
                                        "/usr/bin/systemd-run\n")], T_INS),
    ("I2 the update touches the SSH listener", [(UPD, 'sh "$REPO/ops/desktop/install_sudoers.sh"\n',
                                                 'sh "$REPO/ops/desktop/install_sudoers.sh"\n'
                                                 "systemctl restart ssh.socket\n")], T_INS),
    ("I3 the dispatcher installed group-writable", [(UPD, "install -o root -g root -m 755",
                                                     "install -o root -g root -m 775")], T_INS),
    ("I4 a dispatcher that does not parse is installed", [(UPD,
     "python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' \"$NEW\" \\\n"
     "  || { echo \"the new dispatcher does not parse; nothing changed\"; exit 1; }\n", "")],
     T_INS),
    ("I5 the update runs for any user", [(UPD,
     '[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }\n', "")], T_INS),
    ("I6 the rules installed before visudo checks them", [(SUD, 'visudo -cf "$TMP"\n', "")],
     T_INS),
]


def run(command: list[str]) -> int:
    for cache in ROOT.rglob("__pycache__"):
        if ".venv" not in cache.parts and ".git" not in cache.parts:
            shutil.rmtree(cache, ignore_errors=True)
    return subprocess.run(command, cwd=ROOT, capture_output=True).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands: list[list[str]] = []
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
