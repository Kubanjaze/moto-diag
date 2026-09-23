"""Phase 257 — the orchestrator's start-up guards (plan D3), each with a planted violation.

A guard that has never been seen to refuse is not a guard. Every case below
plants the thing the guard exists for and asserts the orchestrator refuses
to start — including the one that actually happened on 2026-09-22: the
operator's Anthropic token, wrapped in angle brackets, in a file pointing
at a third-party host.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "source-transmission"))

import orchestrate as O  # noqa: E402

FAKE_ANTHROPIC = "sk-ant-oat01-" + "x" * 40
FAKE_SUBC = "sk-gw-" + "y" * 40


def _file(tmp_path, text, mode=0o600):
    p = tmp_path / "anthropic.env"
    p.write_text(text, encoding="utf-8")
    os.chmod(p, mode)
    return p


class TestTheAnthropicTokenFile:
    def test_a_good_file_loads(self, tmp_path):
        assert O.load_anthropic_token(_file(tmp_path, f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_ANTHROPIC}\n")) == FAKE_ANTHROPIC

    @pytest.mark.parametrize("text,why", [
        (f"CLAUDE_CODE_OAUTH_TOKEN=<{FAKE_ANTHROPIC}>", "angle brackets — the real 2026-09-22 file"),
        (f"CLAUDE_CODE_OAUTH_TOKEN=\"{FAKE_ANTHROPIC}\"", "quotes"),
        (f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_SUBC}", "a Subconscious key in the Anthropic file"),
        (f"ANTHROPIC_AUTH_TOKEN={FAKE_ANTHROPIC}", "wrong variable name"),
        ("", "empty"),
    ])
    def test_a_bad_file_is_refused(self, tmp_path, text, why):
        with pytest.raises(O.GuardError):
            O.load_anthropic_token(_file(tmp_path, text))

    def test_a_world_readable_file_is_refused(self, tmp_path):
        with pytest.raises(O.GuardError, match="chmod 600"):
            O.load_anthropic_token(_file(tmp_path, f"CLAUDE_CODE_OAUTH_TOKEN={FAKE_ANTHROPIC}", 0o644))


class TestACredentialNeverCrossesRoutes:
    def test_the_subconscious_route_carries_no_credential(self):
        O.check_route("subconscious", {"HOME": "/x"}, gateway="api.subconscious.dev")

    @pytest.mark.parametrize("var", O.CREDENTIAL_VARS)
    def test_any_credential_on_the_subconscious_route_is_refused(self, var):
        """The 2026-09-22 shape: an Anthropic token headed for a third party."""
        with pytest.raises(O.GuardError):
            O.check_route("subconscious", {var: FAKE_ANTHROPIC}, gateway="api.subconscious.dev")

    def test_a_non_subconscious_gateway_is_refused(self):
        with pytest.raises(O.GuardError, match="gateway"):
            O.check_route("subconscious", {}, gateway="api.z.ai")

    def test_the_anthropic_route_carries_exactly_its_token(self):
        O.check_route("anthropic", {"CLAUDE_CODE_OAUTH_TOKEN": FAKE_ANTHROPIC})

    @pytest.mark.parametrize("env", [
        {"CLAUDE_CODE_OAUTH_TOKEN": FAKE_SUBC},
        {"CLAUDE_CODE_OAUTH_TOKEN": FAKE_ANTHROPIC, "ANTHROPIC_BASE_URL": "https://api.subconscious.dev"},
        {"CLAUDE_CODE_OAUTH_TOKEN": FAKE_ANTHROPIC, "ANTHROPIC_API_KEY": FAKE_SUBC},
        {},
    ], ids=["wrong-token", "redirected", "second-credential", "none"])
    def test_a_bad_anthropic_environment_is_refused(self, env):
        with pytest.raises(O.GuardError):
            O.check_route("anthropic", env)

    def test_the_real_subc_profile_points_at_subconscious(self):
        """Live control: the operator's own subc profile, read by name only."""
        if not O.SUBC_PROFILE.is_file():
            pytest.fail(f"control missing: {O.SUBC_PROFILE} (run `subc login`)")
        assert O.subc_gateway() == "api.subconscious.dev"


class TestTheCommandLine:
    def test_every_call_names_its_model(self):
        for route, r in O.ROUTES.items():
            cmd = O.build_cmd(route, "hi")
            assert r["model"] in cmd and cmd[cmd.index(r["model"]) - 1] == "--model"

    def test_bare_is_refused(self):
        with pytest.raises(O.GuardError, match="bare"):
            O.build_cmd("anthropic", "hi", extra=("--bare",))

    def test_the_source_route_goes_through_subc(self):
        cmd = O.build_cmd("subconscious", "hi")
        assert cmd[:2] == [str(O.SUBC), "claude"] and "--" in cmd

    def test_the_opus_route_is_budget_capped(self):
        assert "--max-budget-usd" in O.build_cmd("anthropic", "hi")

    def test_a_schema_is_passed_as_json(self):
        cmd = O.build_cmd("subconscious", "hi", schema={"type": "object"})
        assert json.loads(cmd[cmd.index("--json-schema") + 1]) == {"type": "object"}


class TestResultParsing:
    def test_the_subc_banner_is_skipped(self):
        out = "  Launching Claude Code on Subconscious (x)\n\n" + json.dumps({"result": "ok", "is_error": False})
        assert O.parse_result(out)["result"] == "ok"

    def test_no_json_is_an_error(self):
        assert O.parse_result("Not logged in")["is_error"] is True


class TestStops:
    def test_blocked_above_half_stops(self):
        f = [{"outcome": "blocked"}] * 3 + [{"outcome": "found"}]
        assert any("blocked rate" in s for s in O.stops(f, []))

    def test_blocked_at_half_does_not(self):
        f = [{"outcome": "blocked"}, {"outcome": "found"}]
        assert O.stops(f, []) == []

    def test_a_refute_disagreement_stops(self):
        assert O.stops([], [{"spelling": "K-Pipe", "verdict": "killed"}])


class TestTheStopAlertCompiles:
    """Bug fix #2: the STOP title carries an em dash; json.dumps wrote it as
    \\u2014, which AppleScript cannot parse, and osascript's failure was
    swallowed — every stop alert since a8e236e was silent. Compiled here by
    osacompile, the same parser osascript uses; nothing is displayed."""

    @pytest.mark.parametrize("title,message", [
        ("moto-diag source-transmission — STOP", "Kymco: tokens 236,084 exceed 150,000 per spelling"),
        ("moto-diag source-transmission", 'Honda: a "quoted" \\ message'),
    ])
    def test_the_script_compiles(self, tmp_path, title, message):
        import shutil
        import subprocess
        if not shutil.which("osacompile"):
            pytest.fail("osacompile missing: this check needs macOS")
        src = tmp_path / "alert.applescript"
        src.write_text(O.notification_script(title, message), encoding="utf-8")
        p = subprocess.run(["osacompile", "-o", str(tmp_path / "alert.scpt"), str(src)],
                           capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
