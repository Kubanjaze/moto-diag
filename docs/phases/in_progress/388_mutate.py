"""Phase 388's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/388_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 384's and 387's
harness: exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`F` the fence, `N` the network gate, `D` the dispatcher, `S` the service.

No mutation makes a real model call or reaches GitHub: the gate's allow-all
mutation runs only the gate's own unit test, and the dispatcher's are
judged against stand-ins.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

FE = ".claude/skills/fleet/fence.sh"
NE = ".claude/skills/fleet/fence_net.py"
DI = ".claude/skills/fleet/dispatcher.py"
UN = "ops/desktop/motodiag-fleet.service"
XM = "ops/desktop/motodiag-fleet-boot.xml"
IN = "ops/desktop/install_fleet_unit.sh"
BC = "ops/desktop/fleet_boot_check.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_FE = pytest("tests/test_phase388_fence_boundary.py")
T_GATE = pytest("tests/test_phase388_fence_boundary.py", "-k", "allows_the_model_api_only")
T_DI = pytest("tests/test_phase388_dispatcher.py")
T_SV = pytest("tests/test_phase388_service_contract.py")

MUTATIONS = [
    ("F1 the home mounted read-only", [(FE,
     "--ro-bind /etc /etc --proc /proc", "--ro-bind /home /home --ro-bind /etc /etc --proc /proc")], T_FE),
    ("F2 the home mounted writable", [(FE,
     "--ro-bind /etc /etc --proc /proc", "--bind /home /home --ro-bind /etc /etc --proc /proc")], T_FE),
    ("F3 the root left writable", [(FE,
     "args+=(--remount-ro /fleet --remount-ro /", "args+=(--remount-ro /fleet")], T_FE),
    ("F4 the network shared", [(FE,
     "args=(--unshare-all --die-with-parent", "args=(--unshare-all --share-net --die-with-parent")], T_FE),
    ("F5 the caller's environment crosses", [(FE,
     '[ "$var" = CLAUDE_CODE_OAUTH_TOKEN ] || unset', 'true || unset')], T_FE),
    ("F6 the token on the command line", [(FE,
     "--setenv TERM dumb", '--setenv TERM dumb --setenv CLAUDE_CODE_OAUTH_TOKEN "${CLAUDE_CODE_OAUTH_TOKEN:-}"')], T_FE),
    ("F7 workspace-docs writable", [(FE,
     '--ro-bind "$wsdocs" /fleet/workspace-docs', '--bind "$wsdocs" /fleet/workspace-docs')], T_FE),
    ("F8 a fence without working-rules.md runs", [(FE,
     '[ -n "$wsdocs" ] && [ -f "$wsdocs/claude/working-rules.md" ]', '[ -n "$wsdocs" ] && [ -d "$wsdocs" ]')], T_FE),
    ("F9 the import approval not seeded", [(FE,
     "hasClaudeMdExternalIncludesApproved=True", "hasClaudeMdExternalIncludesApproved=False")], T_FE),
    ("F10 the operator's checkout accepted as the clone", [(FE,
     '  && refuse "the clone is the repository fence.sh runs from: $clone"', "  && true")], T_FE),
    ("F11 workspace-docs not bound", [(FE,
     '      --ro-bind "$wsdocs" /fleet/workspace-docs\n', "")], T_FE),
    ("N1 the gate allows every host", [(NE,
     "return target if target in ALLOW else None", "return target")], T_GATE),
    ("N2 the gate ignores the port", [(NE,
     "target = (host.lower(), int(port))", "target = (host.lower(), 443)")], T_GATE),
    ("N3 the gate logs nothing", [(NE,
     "print(f\"{'ALLOW' if target else 'DENY'} {line}\", file=log, flush=True)", "pass")], T_FE),
    ("D1 the ceiling at more than 70", [(DI, "if pct >= OPUS_CEILING:", "if pct > OPUS_CEILING:")], T_DI),
    ("D2 unreadable usage lets Opus through", [(DI,
     '        return "the weekly usage could not be read"', "        return None")], T_DI),
    ("D3 the Opus gate skipped", [(DI,
     "if model == OPUS and self.resume is None:", "if False:")], T_DI),
    ("D4 a resumed stage not resumed", [(DI,
     'cmd = [cmd[0], "--resume", self.resume, *cmd[1:]]', "pass")], T_DI),
    ("D5 a usage limit not recognised", [(DI,
     'if d.get("is_error") and _LIMIT.search(text):', "if False:")], T_DI),
    ("D6 a pause that does not hold", [(DI,
     'if self.now() < _time(paused["until"]):', "if False:")], T_DI),
    ("D7 an unknown reset does not wait", [(DI,
     "or self.now() + RESET_UNKNOWN", "or self.now()")], T_DI),
    ("D8 the due rule ignores the rank's comments", [(DI,
     "return not ranks or _time(applied) > max(ranks)", "return True")], T_DI),
    ("D9 the fence gets the whole environment", [(DI,
     'env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),', 'env = {**os.environ, "PATH": os.environ.get("PATH", "/usr/bin:/bin"),')], T_DI),
    ("D10 workspace-docs not passed to the fence", [(DI,
     '"--workspace-docs", str(self.fleet.workspace_docs), "--", *cmd]', '"--", *cmd]')], T_DI),
    ("D11 gh without GH_REPO", [(DI,
     'env={**os.environ, "GH_REPO": REPO}', "env=dict(os.environ)")], T_DI),
    ("D12 a model call outside the clone allowed", [(DI,
     "if cwd is not None and pathlib.Path(cwd).resolve() != self.clone.resolve():", "if False:")], T_DI),
    ("D13 mission swept", [(DI,
     'STATE_LABELS = tuple(name for name, _, _ in LABELS if name != "mission")',
     "STATE_LABELS = tuple(name for name, _, _ in LABELS)")], T_DI),
    ("D14 the sweep under 24 hours", [(DI,
     "if hours <= self.sweep_hours or any(marker in b for b in bodies):",
     "if any(marker in b for b in bodies):")], T_DI),
    ("D15 the sweep twice for one application", [(DI,
     "if hours <= self.sweep_hours or any(marker in b for b in bodies):",
     "if hours <= self.sweep_hours:")], T_DI),
    ("D16 the digest before seven", [(DI, "if now.hour < DIGEST_HOUR or", "if now.hour < 0 or")], T_DI),
    ("D17 the digest not recorded", [(DI,
     '        state["last_digest"] = day.isoformat()\n', "")], T_DI),
    ("D18 an API key allowed", [(DI, 'if "ANTHROPIC_API_KEY" in env:', "if False:")], T_DI),
    ("D19 a token of any class", [(DI, 'if not token.startswith("sk-ant-oat"):', "if False:")], T_DI),
    ("D20 no lock", [(DI, "        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)", "        pass")], T_DI),
    ("D21 an issue with no branch run anyway", [(DI,
     "            if branch is None:\n                self.comment(n, \"stopped\"",
     "            if False:\n                self.comment(n, \"stopped\"")], T_DI),
    ("D22 the paused run pruned", [(DI, "if str(p) not in keep_also:", "if True:")], T_DI),
    ("S1 the unit runs as root", [(UN, "User=lilcu", "User=root")], T_SV),
    ("S2 the unit retries a refusal", [(UN, "RestartPreventExitStatus=4\n", "")], T_SV),
    ("S3 the task does not hold the VM", [(XM,
     "<Arguments>-d Ubuntu-26.04 --exec /bin/sleep infinity</Arguments>",
     "<Arguments>-d Ubuntu-26.04 --exec /bin/true</Arguments>")], T_SV),
    ("S4 the install script starts the service", [(IN,
     "systemctl is-enabled motodiag-fleet.service", "systemctl start motodiag-fleet.service")], T_SV),
    ("S5 the restart check passes after sign-in", [(BC, "if started < logon:", "if started <= logon or True:")], T_SV),
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
