"""Phase 406 (K93) — the one-time install at the desktop.

The operator approved password-free restarts for exactly two units: the
payments feed (start, stop, restart) and the fleet (restart). These cases
hold the rule file to 382's line and that one line, and nothing wider: no
other unit, no other verb, no wildcard, no `systemd-run`. And the update
script puts the dispatcher where Phase 384 does, root-owned, and changes no
SSH setting and no key: the lock stays as 384 made it.
"""
from __future__ import annotations

import ast
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
OPS = ROOT / "ops" / "desktop"
SUDOERS = (OPS / "install_sudoers.sh").read_text()
UPDATE = (OPS / "update_remote.sh").read_text()
INSTALL = (OPS / "install_remote.sh").read_text()


def rules() -> list[str]:
    return SUDOERS.split("<<'RULES'\n", 1)[1].split("\nRULES", 1)[0].splitlines()


def commands(line: str) -> list[str]:
    user, rest = line.split(" NOPASSWD: ")
    assert user == "lilcu ALL=(root)"
    return [c.strip() for c in rest.split(",")]


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


def test_the_rules_are_checked_before_and_after_they_are_installed():
    assert "visudo -cf \"$TMP\"" in SUDOERS
    assert SUDOERS.rstrip().endswith("visudo -c")


def test_the_update_puts_the_dispatcher_where_384_does_root_owned():
    dispatcher = INSTALL.split("DISPATCHER=", 1)[1].split("\n", 1)[0]
    assert f"DISPATCHER={dispatcher}" in UPDATE
    assert 'install -o root -g root -m 755 "$NEW" "$DISPATCHER"' in UPDATE
    assert 'NEW="$REPO/ops/desktop/motodiag_remote.py"' in UPDATE


def test_the_update_refuses_without_sudo_or_without_384s_install():
    assert '[ "$(id -u)" -eq 0 ] || { echo "run with sudo"; exit 1; }' in UPDATE
    assert '[ -f "$DISPATCHER" ] ||' in UPDATE


def test_the_update_changes_no_ssh_setting_and_no_key():
    for word in ("sshd", "ssh.socket", "authorized_keys", "ForceCommand", "PermitTTY",
                 "tailscale"):
        assert word not in UPDATE, word


def test_the_update_runs_the_rule_install_and_checks_the_new_code_parses():
    assert 'sh "$REPO/ops/desktop/install_sudoers.sh"' in UPDATE
    assert "ast.parse" in UPDATE


def test_both_scripts_are_sound_shell():
    for script in ("install_sudoers.sh", "update_remote.sh"):
        r = subprocess.run(["sh", "-n", str(OPS / script)], capture_output=True, text=True)
        assert r.returncode == 0, (script, r.stderr)


def test_the_new_dispatcher_parses():
    ast.parse((OPS / "motodiag_remote.py").read_text())
