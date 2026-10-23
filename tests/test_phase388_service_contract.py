"""Phase 388 — the fleet dispatcher's unit and Windows task, against 382's shapes.

`ops/desktop/motodiag-fleet.service` copies `motodiag-api.service`'s shape
and adds the fleet's own rules; `motodiag-fleet-boot.xml` is
`motodiag-wsl-boot.xml` under its own name. Each rule below has a
hand-written known-bad case in `.claude/skills/fleet/fixtures/service/
cases.json` that fails it and no other.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
OPS = ROOT / "ops" / "desktop"
UNIT = OPS / "motodiag-fleet.service"
API_UNIT = OPS / "motodiag-api.service"
CASES = json.loads((ROOT / ".claude" / "skills" / "fleet" / "fixtures" / "service" / "cases.json")
                   .read_text())
TOKEN_FILE = "/home/lilcu/.config/motodiag/anthropic.env"
CODE = "/home/lilcu/motodiag/fleet/code"


def parse(text: str) -> dict[str, list[tuple[str, str]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    section = None
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith("[") and ln.endswith("]"):
            section = ln[1:-1]
            out.setdefault(section, [])
        elif "=" in ln and section:
            k, v = ln.split("=", 1)
            out[section].append((k.strip(), v.strip()))
    return out


def values(unit: dict, section: str, key: str) -> list[str]:
    return [v for k, v in unit.get(section, []) if k == key]


RULES = {
    "user": lambda u: values(u, "Service", "User") == ["lilcu"],
    "restart": lambda u: values(u, "Service", "Restart") == ["always"],
    "no-envfile": lambda u: not values(u, "Service", "EnvironmentFile") and not any(
        "KEY" in v or "TOKEN" in v for v in values(u, "Service", "Environment")),
    "own-clone": lambda u: values(u, "Service", "WorkingDirectory") == [CODE],
    "condition": lambda u: values(u, "Unit", "ConditionPathExists") == [TOKEN_FILE],
    "path": lambda u: any(v.startswith("PATH=") and "/home/lilcu/.local/bin" in v.split(":")[0]
                          for v in values(u, "Service", "Environment")),
    "refusal": lambda u: values(u, "Service", "RestartPreventExitStatus") == ["4"],
    "wanted": lambda u: values(u, "Install", "WantedBy") == ["multi-user.target"],
    "exec": lambda u: values(u, "Service", "ExecStart") == [
        f"/usr/bin/python3 {CODE}/.claude/skills/fleet/dispatcher.py run"],
}


def failed(text: str) -> set[str]:
    u = parse(text)
    return {name for name, ok in RULES.items() if not ok(u)}


class TestTheUnit:
    def test_the_unit_passes_every_rule(self):
        assert failed(UNIT.read_text()) == set()

    @pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
    def test_each_known_bad_case_fails_its_own_rule_alone(self, case):
        text = UNIT.read_text()
        assert text.count(case["old"]) == 1, f"case {case['id']} does not edit the unit"
        assert failed(text.replace(case["old"], case["new"])) == {case["rule"]}

    def test_every_rule_has_a_known_bad_case(self):
        assert {c["rule"] for c in CASES} == set(RULES)

    @pytest.mark.parametrize("section,key", [("Unit", "After"), ("Unit", "Wants"),
                                             ("Service", "Type"), ("Service", "User"),
                                             ("Service", "Restart"), ("Install", "WantedBy")])
    def test_shaped_like_the_api_unit(self, section, key):
        assert values(parse(UNIT.read_text()), section, key) == \
            values(parse(API_UNIT.read_text()), section, key)


class TestTheInstallScript:
    def test_installs_enables_and_does_not_start(self):
        text = (OPS / "install_fleet_unit.sh").read_text()
        assert ('install -m 644 "$(dirname "$0")/motodiag-fleet.service" '
                "/etc/systemd/system/motodiag-fleet.service") in text
        for line in ("systemctl daemon-reload", "systemctl enable motodiag-fleet.service",
                     "systemctl is-enabled motodiag-fleet.service", "set -eu"):
            assert line in text
        assert "systemctl start" not in text and "restart" not in text


class TestTheTokenStepsCheck:
    """Step 1 of the operator's steps: its check must pass one token and only
    that. Its first version checked the line's start and passed a file holding
    the token five times with a stray escape character (2026-10-22)."""

    STEPS = ROOT / "docs" / "phases" / "in_progress" / "388_operator_steps.md"
    TOKEN = "sk-ant-oat01-" + "Ab9_-" * 19          # 108 characters, the measured length

    def check(self, tmp_path, content: str, mode: int = 0o600) -> str:
        steps = self.STEPS if self.STEPS.is_file() else \
            ROOT / "docs" / "phases" / "completed" / "388_operator_steps.md"
        block = next(ln for ln in steps.read_text().splitlines() if ln.startswith("claude setup-token"))
        check = block.split("unset T; ", 1)[1]
        f = tmp_path / "anthropic.env"
        f.write_text(content)
        f.chmod(mode)
        check = check.replace("F=~/.config/motodiag/anthropic.env", f"F={f}", 1)
        assert f"F={f}" in check
        return subprocess.run(["bash", "-c", check], capture_output=True, text=True).stdout.strip()

    def test_one_token_passes(self, tmp_path):
        assert len(self.TOKEN) == 108
        assert self.check(tmp_path, f"CLAUDE_CODE_OAUTH_TOKEN={self.TOKEN}\n") == "ALL GOOD"

    @pytest.mark.parametrize("content", [
        "CLAUDE_CODE_OAUTH_TOKEN=" + "sk-ant-oat01-" * 0 + ("sk-ant-oat01-" + "Ab9_-" * 19) * 5 + "\x1b\n",
        "CLAUDE_CODE_OAUTH_TOKEN=" + "sk-ant-oat01-" + "Ab9_-" * 19 + "\x1b\n",
        "CLAUDE_CODE_OAUTH_TOKEN=" + ("sk-ant-oat01-" + "Ab9_-" * 19) * 2 + "\n",
        "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-" + "Ab9_-" * 19 + " extra\n",
        "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-" + "Ab9_-" * 19 + "\nCLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-x\n",
        "CLAUDE_CODE_OAUTH_TOKEN=sk-ant-api03-" + "Ab9_-" * 19 + "\n",
    ], ids=["five-copies-and-escape", "stray-escape", "two-copies", "trailing-text", "two-lines",
            "api-key-class"])
    def test_anything_else_fails(self, tmp_path, content):
        assert self.check(tmp_path, content) == "SOMETHING IS OFF"

    def test_readable_by_others_fails(self, tmp_path):
        assert self.check(tmp_path, f"CLAUDE_CODE_OAUTH_TOKEN={self.TOKEN}\n", 0o644) == "SOMETHING IS OFF"


class TestTheRestartCheck:
    """`fleet_boot_check.py`, the operator's reboot proof: up before sign-in."""

    QUSER = (" USERNAME              SESSIONNAME        ID  STATE   IDLE TIME  LOGON TIME\n"
             ">lilcu                 console             1  Active      none   10/23/2026 09:15 AM\n")

    @pytest.fixture(scope="class")
    def check(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("fleet_boot_check", OPS / "fleet_boot_check.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_the_measured_quser_line(self, check):
        import datetime as dt
        assert check.signed_in(self.QUSER) == dt.datetime(2026, 10, 23, 9, 15)
        assert check.unit_started("Fri 2026-10-23 09:02:41 EDT") == dt.datetime(2026, 10, 23, 9, 2, 41)

    def test_up_before_sign_in_passes_and_after_fails(self, check):
        logon = check.signed_in(self.QUSER)
        assert check.verdict(True, check.unit_started("Fri 2026-10-23 09:02:41 EDT"), logon)[0]
        ok, why = check.verdict(True, check.unit_started("Fri 2026-10-23 09:15:30 EDT"), logon)
        assert not ok and "waited for you" in why

    def test_not_running_or_unknown_sign_in_fails(self, check):
        assert not check.verdict(False, None, check.signed_in(self.QUSER))[0]
        assert not check.verdict(True, check.unit_started("Fri 2026-10-23 09:02:41 EDT"),
                                 check.signed_in("no sessions"))[0]


class TestTheWindowsTask:
    NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"

    def flat(self, path: pathlib.Path) -> dict[str, str]:
        out = {}

        def walk(el, trail):
            name = el.tag.replace(self.NS, "")
            key = f"{trail}/{name}"
            if len(el) == 0:
                out[key] = (el.text or "").strip()
            for child in el:
                walk(child, key)
            for a, v in el.attrib.items():
                out[f"{key}@{a}"] = v

        walk(ET.parse(path).getroot(), "")
        return out

    def test_the_same_task_as_382s_but_for_its_name(self):
        fleet = self.flat(OPS / "motodiag-fleet-boot.xml")
        api = self.flat(OPS / "motodiag-wsl-boot.xml")
        named = {"/Task/RegistrationInfo/Description", "/Task/RegistrationInfo/URI"}
        assert set(fleet) == set(api)
        assert {k: v for k, v in fleet.items() if k not in named} == \
            {k: v for k, v in api.items() if k not in named}
        assert fleet["/Task/RegistrationInfo/URI"] == r"\motodiag\fleet-boot"
        assert "fleet dispatcher" in fleet["/Task/RegistrationInfo/Description"]
        assert fleet["/Task/Actions/Exec/Arguments"] == "-d Ubuntu-26.04 --exec /bin/sleep infinity"
