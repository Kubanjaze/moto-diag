"""Phase 406 (K93) — the one-time install at the desktop.

The operator approved password-free restarts for exactly two units: the
payments feed (start, stop, restart) and the fleet (restart). These cases
hold the rule file to 382's line and that one line, and nothing wider: no
other unit, no other verb, no wildcard, no `systemd-run`.

The two scripts are run, not read (the review's 6): copies of them, with
only their two root paths moved into a temporary folder (each move must
happen exactly once), and stand-ins for `id`, `install`, `visudo`,
`sha256sum` and `systemctl`, proven to be the ones the scripts' shell finds.
They put the dispatcher where Phase 384 does, root-owned, then the rules,
each checked first; they refuse without sudo, without 384's install, or with
a dispatcher that does not parse, having changed nothing; and they touch no
SSH setting, no key and no unit.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import stat
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OPS = ROOT / "ops" / "desktop"
SUDOERS = (OPS / "install_sudoers.sh").read_text()
UPDATE = (OPS / "update_remote.sh").read_text()
INSTALL = (OPS / "install_remote.sh").read_text()
DISPATCHER = "/usr/local/libexec/motodiag-remote"
RULE = "/etc/sudoers.d/motodiag-api"

STAND_INS = {
    "id": '[ "$1" = "-u" ] && echo "${FAKE_UID:-0}"\n',
    # install [-o U -g G] -m MODE SRC DST, recorded; the file copied, the mode set
    "install": ('echo "install $*" >> "$CALLS"\n'
                'while [ $# -gt 2 ]; do case "$1" in -m) mode=$2; shift 2;; '
                '-o|-g) shift 2;; *) shift;; esac; done\n'
                'cp "$1" "$2" && chmod "$mode" "$2"\n'),
    "visudo": ('echo "visudo $*" >> "$CALLS"\n'
               '[ "$1" = "-cf" ] && [ -n "${FAKE_VISUDO_FAIL:-}" ] && '
               '{ echo "visudo: syntax error"; exit 1; }\nexit 0\n'),
    "sha256sum": ('python3 -c \'import hashlib, sys; '
                  'print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(), '
                  'sys.argv[1])\' "$1"\n'),
    "systemctl": 'echo "systemctl $*" >> "$CALLS"\nexit 1\n',
}


def rules() -> list[str]:
    return SUDOERS.split("<<'RULES'\n", 1)[1].split("\nRULES", 1)[0].splitlines()


def commands(line: str) -> list[str]:
    user, rest = line.split(" NOPASSWD: ")
    assert user == "lilcu ALL=(root)"
    return [c.strip() for c in rest.split(",")]


def moved(text: str, real: str, there: pathlib.Path) -> str:
    """`real` (a root path) moved to `there`: it must be named exactly once."""
    assert text.count(real) == 1, f"{real} is named {text.count(real)} times"
    return text.replace(real, str(there))


@pytest.fixture
def desk(tmp_path):
    """A checkout's two scripts and dispatcher, 384's dispatcher already in
    place, and the stand-ins first on the PATH."""
    repo = tmp_path / "repo"
    (repo / "ops" / "desktop").mkdir(parents=True)
    root = tmp_path / "root"
    (root / "libexec").mkdir(parents=True)
    (root / "sudoers.d").mkdir()
    there = {"dispatcher": root / "libexec" / "motodiag-remote",
             "rule": root / "sudoers.d" / "motodiag-api"}
    (repo / "ops" / "desktop" / "update_remote.sh").write_text(
        moved(UPDATE, DISPATCHER, there["dispatcher"]))
    (repo / "ops" / "desktop" / "install_sudoers.sh").write_text(
        moved(SUDOERS, RULE, there["rule"]))
    (repo / "ops" / "desktop" / "motodiag_remote.py").write_bytes(
        (OPS / "motodiag_remote.py").read_bytes())
    there["dispatcher"].write_text("# 384's dispatcher\n")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name, body in STAND_INS.items():
        p = bin_ / name
        p.write_text("#!/bin/sh\n" + body)
        p.chmod(0o755)
    calls = tmp_path / "calls"
    calls.write_text("")
    env = {"PATH": f"{bin_}:/usr/bin:/bin", "CALLS": str(calls), "HOME": str(tmp_path)}
    return {"repo": repo, "bin": bin_, "calls": calls, "env": env, **there}


def update(desk, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(["sh", str(desk["repo"] / "ops" / "desktop" / "update_remote.sh")],
                          env={**desk["env"], **extra}, capture_output=True, text=True,
                          timeout=60)


def calls(desk) -> list[str]:
    return desk["calls"].read_text().splitlines()


# ---------------------------------------------------------------- the rules
def test_the_rule_file_is_382s_line_and_406s_line_only():
    assert len(rules()) == 2
    assert commands(rules()[0]) == [f"/usr/bin/systemctl {v} motodiag-api.service"
                                    for v in ("start", "stop", "restart")]
    assert commands(rules()[1]) == [
        "/usr/bin/systemctl start motodiag-payments.service",
        "/usr/bin/systemctl stop motodiag-payments.service",
        "/usr/bin/systemctl restart motodiag-payments.service",
        "/usr/bin/systemctl restart motodiag-fleet.service"]


def test_no_rule_is_wider_than_one_unit_and_one_verb():
    for line in rules():
        for cmd in commands(line):
            words = cmd.split()
            assert words[0] == "/usr/bin/systemctl" and len(words) == 3, cmd
            assert words[1] in ("start", "stop", "restart"), cmd
            assert words[2].startswith("motodiag-") and words[2].endswith(".service"), cmd
            assert "*" not in cmd and "systemd-run" not in cmd, cmd


def test_the_dispatcher_goes_where_384_puts_it():
    assert f"DISPATCHER={DISPATCHER}\n" in INSTALL
    assert f"DISPATCHER={DISPATCHER}\n" in UPDATE


# ---------------------------------------------------------------- the run
def test_the_stand_ins_are_the_ones_the_scripts_shell_finds(desk):
    r = subprocess.run(["sh", "-c", "command -v " + " ".join(STAND_INS)], env=desk["env"],
                       capture_output=True, text=True)
    assert r.stdout.split() == [str(desk["bin"] / name) for name in STAND_INS]


def test_the_update_installs_the_dispatcher_root_owned_then_the_checked_rules(desk):
    r = update(desk)
    assert r.returncode == 0, r.stdout + r.stderr
    new = (OPS / "motodiag_remote.py").read_bytes()
    assert desk["dispatcher"].read_bytes() == new
    assert stat.S_IMODE(desk["dispatcher"].stat().st_mode) == 0o755
    assert desk["rule"].read_text().splitlines() == rules()
    assert stat.S_IMODE(desk["rule"].stat().st_mode) == 0o440
    did = calls(desk)
    assert did[0] == (f"install -o root -g root -m 755 "
                      f"{desk['repo'] / 'ops' / 'desktop' / 'motodiag_remote.py'} "
                      f"{desk['dispatcher']}")
    assert did[1].startswith("visudo -cf ") and did[2].startswith("install -m 440 ")
    assert did[2].endswith(f" {desk['rule']}") and did[3] == "visudo -c"
    assert len(did) == 4, "no unit restarted, nothing else installed"
    assert r.stdout.rstrip().endswith(f"sha256 {hashlib.sha256(new).hexdigest()[:16]}")


def test_the_update_without_sudo_changes_nothing(desk):
    r = update(desk, FAKE_UID="1000")
    assert r.returncode == 1 and "run with sudo" in r.stdout
    assert desk["dispatcher"].read_text() == "# 384's dispatcher\n"
    assert not desk["rule"].exists() and calls(desk) == []


def test_the_update_without_384s_install_changes_nothing(desk):
    desk["dispatcher"].unlink()
    r = update(desk)
    assert r.returncode == 1 and "run install_remote.sh first" in r.stdout
    assert not desk["dispatcher"].exists() and not desk["rule"].exists()
    assert calls(desk) == []


def test_a_dispatcher_that_does_not_parse_is_not_installed(desk):
    (desk["repo"] / "ops" / "desktop" / "motodiag_remote.py").write_text("def broken(:\n")
    r = update(desk)
    assert r.returncode == 1 and "does not parse; nothing changed" in r.stdout
    assert desk["dispatcher"].read_text() == "# 384's dispatcher\n"
    assert not desk["rule"].exists() and calls(desk) == []


def test_rules_visudo_refuses_are_not_installed(desk):
    r = update(desk, FAKE_VISUDO_FAIL="1")
    assert r.returncode != 0
    assert not desk["rule"].exists(), "a rule visudo refused was installed"
    assert [c.split()[0] for c in calls(desk)] == ["install", "visudo"]


def test_the_update_changes_no_ssh_setting_and_no_key():
    for word in ("sshd", "ssh.socket", "authorized_keys", "ForceCommand", "PermitTTY",
                 "tailscale", "systemctl"):
        assert word not in UPDATE, word


@pytest.mark.skipif(os.geteuid() == 0, reason="the refusal is of a user who is not root")
def test_the_real_update_refuses_a_user_who_is_not_root():
    r = subprocess.run(["sh", str(OPS / "update_remote.sh")], capture_output=True, text=True,
                       timeout=60)
    assert r.returncode == 1 and r.stdout.strip() == "run with sudo"
