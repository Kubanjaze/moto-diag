#!/usr/bin/env python3
"""The Mac's way in to the desktop's deploy steps (Phase 384, the operator's 1A, 2A, 3A).

Live is on the desktop; this sends one named operation to the fixed list
there (ops/desktop/motodiag_remote.py) over the tailnet, by SSH to the
`motodiag-ops` device, with the key the operator made. The Mac's
`~/.config/motodiag/live.json` names the way in:

    {"live": null, "host": "desktop-76s9bqv",
     "remote": {"ssh": "lilcu@motodiag-ops", "key": "~/.ssh/motodiag_ops"}}

    remote.py status
    remote.py dryrun 384          the commit is added: HEAD, clean and pushed
    remote.py fetch 384 dryrun    writes docs/phases/in_progress/384_dryrun_diff.md
                                  only when its sha256 equals the desktop's
    remote.py deploy-step 334 <branch> <commit>
                                  the fleet's database step from the Mac (Phase
                                  406): the dry run's list shown, then yes asked
                                  here, then the apply of exactly that diff;
                                  `deploy-apply` alone is refused, so the apply
                                  is never sent without the question

No remote in live.json, or no key file: exit 4, as live.py refuses. The
operation's own exit comes back unchanged; 255 is SSH's own failure.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import sys
from collections.abc import Callable

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import live as L  # noqa: E402

REFUSED = 4
ROOT = pathlib.Path(__file__).resolve().parents[3]
KNOWN_HOSTS = pathlib.Path.home() / ".config" / "motodiag" / "known_hosts"
# Operations that run repository code on the desktop: each names the commit.
AT_COMMIT = {"dryrun", "apply-live", "verify-live", "live-check", "media-check"}


class NoWayIn(Exception):
    """This machine has no way in to live's machine, or may not use it now."""


def way_in(config: pathlib.Path | None = None) -> dict[str, str]:
    cfg = config or L.config_path()
    if not cfg.is_file():
        raise NoWayIn(f"{cfg} is missing: no way in to live's machine")
    entry = json.loads(cfg.read_text()).get("remote") or {}
    if not entry.get("ssh") or not entry.get("key"):
        raise NoWayIn(f"{cfg} names no remote (Phase 384): no way in to live's machine")
    key = pathlib.Path(entry["key"]).expanduser()
    if not key.is_file():
        raise NoWayIn(f"the key {key} is missing")
    return {"ssh": entry["ssh"], "key": str(key)}


def ssh_argv(way: dict[str, str], words: list[str]) -> list[str]:
    # AddKeysToAgent (F294): the key's passphrase is read from the Mac's
    # keychain, which cannot be read while the Mac is locked; the first
    # connection made while it is unlocked leaves the key in the agent, so
    # the ones after it work while it is locked, until the agent restarts.
    return ["ssh", "-T", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
            "-o", f"IdentityFile={way['key']}", "-o", "IgnoreUnknown=UseKeychain",
            "-o", "UseKeychain=yes", "-o", "AddKeysToAgent=yes", "-o", "ConnectTimeout=15",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"UserKnownHostsFile={KNOWN_HOSTS}",
            way["ssh"], shlex.join(words)]


def _git(repo: pathlib.Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def pushed_head(repo: pathlib.Path) -> str:
    """HEAD, when the tree is clean and origin holds it: what the desktop will run."""
    if _git(repo, "status", "--porcelain")[1]:
        raise NoWayIn("the tree is not clean: commit and push first, so the desktop "
                      "runs what is here")
    _git(repo, "fetch", "--quiet", "origin")
    head = _git(repo, "rev-parse", "HEAD")[1]
    if not _git(repo, "branch", "-r", "--contains", head)[1]:
        raise NoWayIn(f"origin does not hold {head[:12]}: push first")
    return head


def run(argv: list[str]) -> int:
    return subprocess.run(argv).returncode


def capture(argv: list[str]) -> tuple[int, str]:
    r = subprocess.run(argv, capture_output=True, text=True)
    if r.stderr:
        print(r.stderr, end="", file=sys.stderr)
    return r.returncode, r.stdout


def fetch(way: dict[str, str], phase: str, kind: str, repo: pathlib.Path) -> int:
    code, out = capture(ssh_argv(way, ["fetch", phase, kind]))
    if code != 0:
        return code
    sent = json.loads(out)
    data = sent["text"].encode()
    got = hashlib.sha256(data).hexdigest()
    print(f"desktop sha256: {sent['sha256']}")
    print(f"arrived sha256: {got}")
    if got != sent["sha256"] or sent["name"] != f"{phase}_{kind}_diff.md":
        print("REFUSED: what arrived is not what the desktop sent; nothing written",
              file=sys.stderr)
        return 1
    out_path = repo / "docs" / "phases" / "in_progress" / sent["name"]
    out_path.write_bytes(data)
    print("wrote", out_path.relative_to(repo))
    return 0


def stream(argv: list[str]) -> tuple[int, list[str]]:
    """Run, showing each line as it comes, and keep the lines."""
    lines: list[str] = []
    with subprocess.Popen(argv, stdout=subprocess.PIPE, text=True) as p:
        assert p.stdout is not None
        for line in p.stdout:
            print(line, end="", flush=True)
            lines.append(line.rstrip("\n"))
    return p.returncode, lines


def ask_tty(prompt: str) -> str:
    """The operator's answer, from this Mac's own terminal."""
    with open("/dev/tty", "w") as out, open("/dev/tty") as tty:
        out.write(prompt)
        out.flush()
        return tty.readline().rstrip("\n")


#: The desktop's last line of a dry run alone (`through_fleet.SHA_LINE`).
SHA_LINE = re.compile(r"dry-run diff sha256: ([0-9a-f]{64})")
STEP_ARGS = (r"\d{3}[A-Z]?", r"phase-\d{3}[A-Z]?-[a-z0-9-]{1,80}", r"[0-9a-f]{40}")
QUESTION = ("\nType yes and press Enter to make this change to the live database "
            "(anything else stops here, and nothing changes): ")


def deploy_step(way: dict[str, str], phase: str, branch: str, commit: str, *,
                run_lines: Callable[[list[str]], tuple[int, list[str]]] = stream,
                ask: Callable[[str], str] = ask_tty) -> int:
    """The fleet's database step from the Mac (Phase 406, K93). The desktop
    has no terminal to ask on, so: its dry run, whose list is shown here as
    it comes; the yes asked on this terminal, after the list (the operator's
    condition); then the apply of the diff the list was made from, named by
    its sha256. Anything but yes sends nothing more."""
    code, lines = run_lines(ssh_argv(way, ["deploy-dryrun", phase, branch, commit]))
    if code != 0:
        return code
    if any("already on the live database" in ln for ln in lines):
        return 0
    shas = [m.group(1) for m in (SHA_LINE.fullmatch(ln.strip()) for ln in lines) if m]
    if len(shas) != 1:
        print("SOMETHING IS OFF: the dry run did not end with one sha256 line, so there is "
              "nothing to say yes to; nothing was applied", file=sys.stderr)
        return 1
    words = ask(QUESTION)
    if words.strip().lower() != "yes":
        print(f"You typed {words!r}, not yes: nothing was applied, and the live database is "
              "as it was.")
        return 2
    return run(ssh_argv(way, ["deploy-apply", phase, branch, commit, shas[0]]))


def main(argv: list[str], *, repo: pathlib.Path = ROOT,
         config: pathlib.Path | None = None) -> int:
    if not argv:
        print(__doc__)
        return 2
    try:
        way = way_in(config)
        if argv[0] == "fetch" and len(argv) == 3:
            return fetch(way, argv[1], argv[2], repo)
        if argv[0] == "deploy-step":
            args = argv[1:]
            if len(args) != 3 or not all(re.fullmatch(p, a) for p, a in zip(STEP_ARGS, args)):
                raise NoWayIn("deploy-step takes a phase, its branch and a 40-hex commit")
            return deploy_step(way, *args)
        if argv[0] == "deploy-apply":
            raise NoWayIn("deploy-apply is sent only by deploy-step, after the dry run's list "
                          "and your yes: run remote.py deploy-step <phase> <branch> <commit>")
        words = argv + [pushed_head(repo)] if argv[0] in AT_COMMIT else argv
    except NoWayIn as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return REFUSED
    code = run(ssh_argv(way, words))
    if code == 255:
        print("the way in did not answer (SSH exit 255): is the desktop up, and is "
              "this Mac on the tailnet?", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
