"""Phase 371, Logic items 5 to 7 — the commands, the mask, the unit, the
guide and the ledger.

``payments feed run --once`` and ``payments feed status`` under
``CliRunner`` with Stripe answering through :class:`FixtureHTTP`; ``config
show`` masking the webhook secret (F248); the desktop unit and its
installer; the guide on ``BACKEND_DOCS``; row 401 and its prompt.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

import pytest
from support.phase273 import STRIPE_ENV, answer, cli, new_db, seed_account, seed_invoice, sql
from support.phase371 import ask, refused
from support.stripe_fixtures import SHOP_ACCOUNT, TEST_KEY, TEST_SECRET

from motodiag.payments import event_feed

ROOT = pathlib.Path(__file__).resolve().parent.parent
UNIT = ROOT / "ops" / "desktop" / "motodiag-payments.service"
INSTALLER = ROOT / "ops" / "desktop" / "install_payments_unit.sh"
PLANTED_WHSEC = "whsec_" + "planted0phase371mask"


@pytest.fixture
def db(tmp_path):
    path = new_db(tmp_path)
    ids = seed_invoice(path)
    seed_account(path, ids["shop_id"])
    return path


class TestFeedRunOnce:
    def test_one_line_per_account_and_exit_0(self, db, monkeypatch):
        http = answer(monkeypatch, [ask(), ask()])
        out = cli(db, "payments", "feed", "run", "--once")
        assert out.exit_code == 0, out.output
        lines = out.output.splitlines()
        assert any(line.startswith("platform: 0 seen, 0 handled") for line in lines)
        assert any(line.startswith(f"{SHOP_ACCOUNT}: 0 seen, 0 handled") for line in lines)
        assert "Alarm: off: no Sentry DSN" in out.output
        assert len(http.requests) == 2

    def test_a_refusal_exits_1_naming_the_account(self, db, monkeypatch):
        answer(monkeypatch, [refused(), ask()])
        out = cli(db, "payments", "feed", "run", "--once")
        assert out.exit_code == 1
        line = next(line for line in out.output.splitlines() if line.startswith("platform:"))
        assert "Stripe refused the key" in line

    @pytest.mark.parametrize("cmd", [["run", "--once"], ["run"], ["status"]])
    def test_unconfigured_exits_2_with_the_gateways_message(self, db, monkeypatch, cmd):
        answer(monkeypatch, [])
        env = {**STRIPE_ENV, "MOTODIAG_BILLING_PROVIDER": "fake"}
        out = cli(db, "payments", "feed", *cmd, env=env)
        assert out.exit_code == 2
        assert "Stripe is not configured" in out.output

    def test_a_live_key_outside_prod_exits_2(self, db, monkeypatch):
        answer(monkeypatch, [])
        env = {**STRIPE_ENV, "MOTODIAG_STRIPE_API_KEY": "sk_live_" + "planted371"}
        out = cli(db, "payments", "feed", "run", "--once", env=env)
        assert out.exit_code == 2
        assert "Live keys are used only with MOTODIAG_ENV=prod" in out.output

    def test_the_alarm_line_names_the_host_and_never_the_key(self, db, monkeypatch):
        answer(monkeypatch, [ask(), ask()])
        env = {**STRIPE_ENV,
               "MOTODIAG_SENTRY_DSN": "https://plantedKey371@o0.ingest.sentry.io/0"}
        out = cli(db, "payments", "feed", "run", "--once", env=env)
        assert "Alarm: checks in to o0.ingest.sentry.io/0 every 5 minutes" in out.output
        assert "plantedKey371" not in out.output


class TestFeedStatus:
    def _round(self, db, monkeypatch):
        answer(monkeypatch, [ask(), ask()])
        assert cli(db, "payments", "feed", "run", "--once").exit_code == 0

    def test_exit_0_after_a_fresh_round(self, db, monkeypatch):
        self._round(db, monkeypatch)
        out = cli(db, "payments", "feed", "status")
        assert out.exit_code == 0, out.output
        assert "platform: last asked" in out.output
        assert f"{SHOP_ACCOUNT}: last asked" in out.output
        assert "Notices in the last 30 days: 0" in out.output
        assert "Alarm: off" in out.output

    def test_exit_1_when_asked_60_seconds_ago_under_a_20_second_interval(
            self, db, monkeypatch):
        self._round(db, monkeypatch)
        import time
        sql(db, "UPDATE stripe_event_cursors SET polled_at = ? WHERE account = 'platform'",
            (event_feed.stamp(time.time() - 60),))
        out = cli(db, "payments", "feed", "status")
        assert out.exit_code == 1
        assert "platform was not asked within two intervals" in out.output

    def test_control_asked_30_seconds_ago_is_still_within_two_intervals(
            self, db, monkeypatch):
        self._round(db, monkeypatch)
        import time
        sql(db, "UPDATE stripe_event_cursors SET polled_at = ? WHERE account = 'platform'",
            (event_feed.stamp(time.time() - 30),))
        assert cli(db, "payments", "feed", "status").exit_code == 0

    def test_exit_1_when_the_last_error_is_set(self, db, monkeypatch):
        answer(monkeypatch, [refused(), ask()])
        cli(db, "payments", "feed", "run", "--once")
        out = cli(db, "payments", "feed", "status")
        assert out.exit_code == 1
        assert "platform's last round ended in an error" in out.output

    def test_exit_1_when_never_asked(self, db):
        out = cli(db, "payments", "feed", "status")
        assert out.exit_code == 1
        assert "platform has never been asked" in out.output


class TestNoKeyInOutput:
    def test_no_planted_key_in_any_output(self, db, monkeypatch):
        answer(monkeypatch, [refused(), ask()])
        run = cli(db, "payments", "feed", "run", "--once")
        status = cli(db, "payments", "feed", "status")
        for out in (run, status):
            assert TEST_KEY not in out.output
            assert TEST_SECRET not in out.output

    def test_control_a_printed_key_is_seen(self, db, monkeypatch):
        import motodiag.cli.payments as cp
        monkeypatch.setattr(cp, "_alarm_line", lambda s: s.stripe_api_key)
        answer(monkeypatch, [ask(), ask()])
        assert TEST_KEY in cli(db, "payments", "feed", "run", "--once").output


def test_feed_help_lists_both_commands(db):
    out = cli(db, "payments", "feed", "--help")
    assert out.exit_code == 0
    assert re.search(r"^\s+run\b", out.output, re.M)
    assert re.search(r"^\s+status\b", out.output, re.M)


class TestConfigShowMasksTheWebhookSecret:
    def _show(self, db):
        env = {**STRIPE_ENV, "MOTODIAG_STRIPE_WEBHOOK_SECRET": PLANTED_WHSEC}
        out = cli(db, "config", "show", env=env)
        assert out.exit_code == 0, out.output
        return out.output

    def test_the_row_is_masked_and_the_secret_never_prints(self, db):
        out = self._show(db)
        row = next(line for line in out.splitlines() if "stripe_webhook_secret" in line)
        assert "****" + PLANTED_WHSEC[-4:] in row
        assert PLANTED_WHSEC not in out

    def test_control_with_the_mask_bypassed_the_secret_prints(self, db, monkeypatch):
        import motodiag.cli.main as main
        monkeypatch.setattr(main, "SECRET_SETTING_NAMES", ("api_key", "sentry_dsn"))
        assert PLANTED_WHSEC in self._show(db)


class TestTheUnit:
    def _lines(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for raw in UNIT.read_text().splitlines():
            if "=" in raw and not raw.startswith("#"):
                k, v = raw.split("=", 1)
                out.setdefault(k, []).append(v)
        return out

    def test_the_units_lines_as_the_plan_writes_them(self):
        u = self._lines()
        assert u["ConditionPathExists"] == ["/home/lilcu/motodiag/live/motodiag.db"]
        assert u["EnvironmentFile"] == ["-/home/lilcu/.config/motodiag/server.env"]
        assert u["ExecStart"] == [
            "/home/lilcu/motodiag/server/.venv/bin/motodiag payments feed run"]
        assert u["Restart"] == ["on-failure"]
        assert u["RestartSec"] == ["30"]
        assert u["After"] == ["network-online.target"]
        assert u["User"] == ["lilcu"]
        assert u["WorkingDirectory"] == ["/home/lilcu/motodiag/server"]
        assert u["Environment"] == [
            "MOTODIAG_DB_PATH=/home/lilcu/motodiag/live/motodiag.db",
            "MOTODIAG_DATA_DIR=/home/lilcu/motodiag/live"]

    def test_the_installer_names_the_unit_and_parses(self):
        text = INSTALLER.read_text()
        assert "motodiag-payments.service" in text
        assert "enable --now motodiag-payments.service" in text
        assert subprocess.run(["sh", "-n", str(INSTALLER)]).returncode == 0


def test_the_guide_is_on_backend_docs():
    sys.path.insert(0, str(ROOT / "tests"))
    import test_phase208_docs as docs
    assert ROOT / "docs" / "guide" / "payments.md" in docs.BACKEND_DOCS


class TestTheLedger:
    def _row(self, n: int) -> str:
        text = (ROOT / "docs" / "ROADMAP.md").read_text()
        return next(line for line in text.splitlines() if line.startswith(f"| {n} |"))

    def test_row_401_is_paused_and_names_its_prompt(self):
        row = self._row(401)
        assert "| ⏸️ |" in row
        assert "docs/prompts/401_payments_news_by_webhook.txt" in row
        assert (ROOT / "docs" / "prompts" / "401_payments_news_by_webhook.txt").exists()

    @pytest.mark.parametrize("n", [371, 401])
    def test_the_rows_are_within_120_words(self, n):
        out = subprocess.run(
            [sys.executable, str(ROOT / ".claude" / "skills" / "closeout" / "roadmap_words.py"),
             str(n), "--check"], capture_output=True, text=True)
        assert out.returncode == 0, out.stdout + out.stderr
        assert int(out.stdout.split()[0]) <= 120
