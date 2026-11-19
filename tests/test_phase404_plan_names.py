"""Phase 404, Logic items 2 and 3 (F271, F272) — the plans' names and the
figures the CLI shows.

``motodiag tier`` under each plan and ``motodiag tier --compare`` print
"Individual: for your own bikes", "Shop" and "Company"; Company's
"Physical locations" row reads 3; the "AI cost cap / month" row reads the
server's figure for every plan; no old name is left under ``src/``.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest
from click.testing import CliRunner

from motodiag.cli.subscription import (
    TIER_LIMITS,
    SubscriptionTier,
    format_tier_comparison,
)
from motodiag.shop.cost_cap import PLAN_AI_CENTS

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = {
    SubscriptionTier.INDIVIDUAL: "Individual: for your own bikes",
    SubscriptionTier.SHOP: "Shop",
    SubscriptionTier.COMPANY: "Company",
}
OLD_NAMES = ("Solo Mechanic", "Shop (per location)", "Multi-Location / Enterprise")


def _tier(monkeypatch, plan: SubscriptionTier, *args: str) -> str:
    from motodiag.cli.main import cli

    monkeypatch.setenv("MOTODIAG_SUBSCRIPTION_TIER", plan.value)
    monkeypatch.setenv("COLUMNS", "200")
    r = CliRunner().invoke(cli, ["tier", *args])
    assert r.exit_code == 0, r.output
    return r.output


def _row(output: str, label: str) -> str:
    line = next(line for line in output.splitlines() if label in line)
    return line.split(label, 1)[1].strip(" │|")


@pytest.mark.parametrize("plan", list(SubscriptionTier))
def test_the_display_names(plan):
    assert TIER_LIMITS[plan].display_name == NAMES[plan]


@pytest.mark.parametrize("plan", list(SubscriptionTier))
def test_motodiag_tier_names_the_plan(monkeypatch, plan):
    assert NAMES[plan] in _tier(monkeypatch, plan)


@pytest.mark.parametrize("plan", list(SubscriptionTier))
def test_motodiag_tier_compare_names_all_three(monkeypatch, plan):
    out = _tier(monkeypatch, plan, "--compare")
    for name in NAMES.values():
        assert name in out


def test_the_compare_table_stays_aligned():
    lines = format_tier_comparison().splitlines()
    assert len({len(line) for line in lines}) == 1
    assert "Plans: Individual: for your own bikes · Shop · Company" in lines[1]


def test_companys_physical_locations_read_3(monkeypatch):
    out = _tier(monkeypatch, SubscriptionTier.COMPANY)
    assert _row(out, "Physical locations") == "3"


@pytest.mark.parametrize("plan,shown", [
    (SubscriptionTier.INDIVIDUAL, "$5.00"),
    (SubscriptionTier.SHOP, "$50.00"),
    (SubscriptionTier.COMPANY, "$150.00"),
])
def test_the_ai_row_reads_the_servers_figure(monkeypatch, plan, shown):
    out = _tier(monkeypatch, plan)
    assert _row(out, "AI cost cap / month") == shown
    assert round(TIER_LIMITS[plan].ai_monthly_cost_cap_usd * 100) == PLAN_AI_CENTS[plan.value]


def test_the_server_and_the_cli_name_the_same_plans():
    assert set(PLAN_AI_CENTS) == {p.value for p in SubscriptionTier}


@pytest.mark.parametrize("old", OLD_NAMES)
def test_no_old_name_is_left_under_src(old):
    found = subprocess.run(["git", "grep", "-n", "-F", old, "--", "src"],
                           cwd=ROOT, capture_output=True, text=True)
    assert found.returncode == 1, found.stdout


def test_control_the_search_finds_a_name_that_is_there():
    found = subprocess.run(["git", "grep", "-n", "-F", NAMES[SubscriptionTier.INDIVIDUAL],
                            "--", "src"], cwd=ROOT, capture_output=True, text=True)
    assert found.returncode == 0
