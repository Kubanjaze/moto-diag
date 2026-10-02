"""A VIN's year code never decodes to a future model year (Phase 281, bug fix #1).

The offline decode picked the 30-year cycle closest to today, so in 2026 the
codes W through 7 read as 2028-2037 and A as 2040. vPIC was then asked about
the wrong model year. The rule now: the latest year of the code's cycles that
is not after next year.
"""

from __future__ import annotations

from datetime import datetime as real_datetime

import pytest

from motodiag.advanced import recall_repo
from motodiag.advanced.recall_repo import _YEAR_CODE_TO_BASE, _disambiguate_year, decode_vin


class _Clock(real_datetime):
    year_now = 2026

    @classmethod
    def now(cls, tz=None):
        return real_datetime(cls.year_now, 9, 30, 12, 0, 0)


@pytest.fixture
def in_2026(monkeypatch):
    monkeypatch.setattr(recall_repo, "datetime", _Clock)


@pytest.mark.parametrize("code, year", [
    ("7", 2007), ("A", 2010), ("L", 2020), ("T", 2026), ("V", 2027),
    ("W", 1998), ("Y", 2000), ("1", 2001), ("9", 2009),
])
def test_codes_decode_to_the_latest_year_not_after_next_year(in_2026, code, year):
    assert _disambiguate_year(code) == year


def test_no_code_is_ever_a_future_model_year_by_todays_clock():
    latest_possible = real_datetime.now().year + 1
    for code in _YEAR_CODE_TO_BASE:
        year = _disambiguate_year(code)
        assert year <= latest_possible, (code, year)
        assert year + 30 > latest_possible, (code, year)


def test_a_2007_harley_vin_decodes_as_2007(in_2026):
    assert decode_vin("1HD1FRW177Y600001")["year"] == 2007
