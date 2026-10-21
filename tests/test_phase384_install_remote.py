"""Phase 384 — the way in's settings, and verify_phase.sh's live check through it.

`ops/desktop/install_remote.sh` runs once on the desktop, by the operator,
so the settings that make the way in tailnet-only, key-only, Mac-only and
list-only are held here as text. The real machine's proof is in the phase
log: the attempts that must fail.

Check 8 and 9 (the operator's (i)): where live is elsewhere, verify_phase.sh
asks remote.py; it passes on live-check's 0 or 2 and fails on anything else,
including 4, no way in.
"""

from __future__ import annotations

import pathlib
import re
import sqlite3
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALL = (ROOT / "ops" / "desktop" / "install_remote.sh").read_text()
VERIFY = ROOT / ".claude" / "skills" / "closeout" / "verify_phase.sh"
DISPATCHER = "/usr/local/libexec/motodiag-remote"


def _sshd() -> list[str]:
    block = INSTALL.split("10-motodiag-ops.conf <<EOF\n", 1)[1].split("\nEOF", 1)[0]
    return block.splitlines()


def test_sshd_takes_keys_only_from_the_mac_and_runs_only_the_dispatcher():
    lines = _sshd()
    for want in ("ListenAddress $TS4:22", "AllowUsers $USER_NAME@$MAC_IP",
                 "AuthenticationMethods publickey", "PasswordAuthentication no",
                 "KbdInteractiveAuthentication no", "PermitRootLogin no",
                 "DisableForwarding yes", "PermitTTY no", "PermitUserRC no",
                 "ForceCommand $DISPATCHER"):
        assert want in lines, want


def test_the_socket_listens_on_the_tailnet_address_only():
    block = INSTALL.split("ssh.socket.d/10-motodiag-ops.conf <<EOF\n", 1)[1].split("\nEOF", 1)[0]
    lines = block.splitlines()
    assert lines[1:] == ["[Socket]", "ListenStream=", "ListenStream=$TS4:22", "FreeBind=yes"]
    assert '[ "$LISTEN" = "$TS4:22" ]' in INSTALL


def test_the_key_line_carries_its_three_restrictions():
    line = re.search(r"printf '%s\\nrestrict,from=\"%s\",command=\"%s\" %s\\n'"
                     r" \"\$MARK\" \"\$MAC_IP\" \"\$DISPATCHER\" \"\$KEY\"", INSTALL)
    assert line, "the authorized_keys line"
    assert '"ssh-ed25519 "*) ;;' in INSTALL


def test_an_existing_key_file_is_never_replaced():
    assert 'if [ -s "$AK" ] && ! grep -qF "$MARK" "$AK"; then' in INSTALL


def test_tailscale_inside_ubuntu_is_tagged_with_its_own_ssh_off():
    up = re.search(r"tailscale up (.*?)\n(.*?)\n", INSTALL).group(0)
    for flag in ("--hostname=motodiag-ops", "--advertise-tags=tag:motodiag-ops",
                 "--accept-dns=false", "--ssh=false"):
        assert flag in up, flag


def test_the_dispatcher_is_installed_root_owned_outside_the_checkout():
    assert f"DISPATCHER={DISPATCHER}" in INSTALL
    assert ('install -o root -g root -m 755 "$REPO/ops/desktop/motodiag_remote.py" '
            '"$DISPATCHER"') in INSTALL
    assert INSTALL.startswith("#!/bin/sh") and "\nset -eu\n" in INSTALL


# --- check 8 and 9 through the way in, with stand-ins ---


def _blocks(tmp_path: pathlib.Path, remote_code: int, *, live_here: bool = False):
    script = VERIFY.read_text()
    block = 'echo "=== 8.' + script.split('echo "=== 8.', 1)[1].split('echo "=== 10.', 1)[0]
    repo = tmp_path / "repo"
    (repo / "docs" / "phases" / "completed").mkdir(parents=True)
    (repo / "docs" / "phases" / "completed" / "999_dryrun_diff.md").write_text("x")
    skills = tmp_path / "skills"
    (skills / "closeout").mkdir(parents=True)
    (skills / "deploy").mkdir(parents=True)
    calls = tmp_path / "calls"
    (skills / "deploy" / "remote.py").write_text(
        "import sys, pathlib\n"
        f"pathlib.Path({str(calls)!r}).open('a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        f"sys.exit({remote_code})\n")
    (skills / "deploy" / "deploy.py").write_text("import sys; sys.exit(0)\n")
    if live_here:
        db = repo / "live.db"
        c = sqlite3.connect(db)
        c.executescript("create table schema_version (version integer); "
                        "insert into schema_version values (87); "
                        "create table known_issues (id integer);")
        c.close()
        (skills / "deploy" / "live.py").write_text(f"print({str(db)!r})\n")
    else:
        (skills / "deploy" / "live.py").write_text("import sys; sys.exit(4)\n")
    run = subprocess.run(
        ["sh", "-c", f'FAILED=0\n{block}\nexit $FAILED'], cwd=repo, capture_output=True,
        text=True, env={"PATH": "/usr/bin:/bin", "PHASE": "999", "PY": "python3",
                        "DIR": str(skills / "closeout"), "HOME": str(tmp_path)})
    sent = calls.read_text().splitlines() if calls.exists() else []
    return run.returncode, run.stdout, sent


def test_live_elsewhere_runs_the_check_through_the_way_in(tmp_path):
    for code in (0, 2):
        rc, _, sent = _blocks(tmp_path / str(code), code)
        assert rc == 0
        assert sent == ["live-check 999", "backups"]


def test_a_failure_through_the_way_in_fails_the_check(tmp_path):
    for code in (1, 3, 4, 255):
        rc, out, _ = _blocks(tmp_path / str(code), code)
        assert rc == 1, code
        assert f"live-check through the way in exited {code}" in out


def test_live_here_never_uses_the_way_in(tmp_path):
    rc, out, sent = _blocks(tmp_path, 1, live_here=True)
    assert rc == 0 and sent == []
    assert "| schema 87" in out
