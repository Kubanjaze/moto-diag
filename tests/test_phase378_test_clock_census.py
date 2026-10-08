"""Phase 378, K19 — test lines that turn the real clock into a day, month,
year or minute: a census, not a sentence in every prompt.

Four failures came from such lines (F10, 370's minute, F196 twice). 375
cleared them by hand under a faked clock; this pins what is left, so a new
line fails here instead of on some evening at 20:00 EDT.
`.claude/skills/closeout/clock_check.sh` runs the pinned files under
libfaketime at 375's four moments.
"""

from __future__ import annotations

import pathlib
import subprocess

from support.clock_census import CLEARED, PINNED, census, files_to_check, lines_in

TESTS = pathlib.Path(__file__).resolve().parent
ROOT = TESTS.parent
SCRIPT = ROOT / ".claude" / "skills" / "closeout" / "clock_check.sh"


def test_the_census_equals_the_pin():
    """A new line fails: give its test 370's frozen clock
    (`tests/support/frozen_clock.py`). A line that goes leaves the pin in
    the same commit."""
    assert census(TESTS) == PINNED


def test_the_cleared_files_exist_and_carry_no_line():
    for name in CLEARED:
        assert lines_in((TESTS / name).read_text(encoding="utf-8")) == [], name


# --- The control: each shape is seen, and what is not a day is not ---

PLANTED = '''
from datetime import date, datetime, timedelta, timezone
import datetime as dt

A = datetime.now(timezone.utc).strftime("%Y-%m")
B = date.today().isoformat()
C = datetime.utcnow().date()
D = dt.datetime.now().year
E = datetime.now(timezone.utc).isoformat()[:10]
F = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
NOW = datetime.now(timezone.utc)
G = NOW.month
H = datetime.now().strftime("%H:%M")
'''

NOT_A_DAY = '''
from datetime import datetime, timezone
from motodiag.core.timestamps import local_day

A = datetime.now(timezone.utc).isoformat()
B = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
C = local_day(datetime.now(timezone.utc).isoformat())
D = datetime(2026, 10, 31).year
E = "datetime.now().date()"
# datetime.utcnow().strftime("%Y-%m-%d") in a comment
'''


def test_each_shape_is_seen():
    assert [n for n, _ in lines_in(PLANTED)] == [5, 6, 7, 8, 9, 10, 12, 13]


def test_a_timestamp_the_shops_day_a_fixed_date_a_string_and_a_comment_are_not():
    assert lines_in(NOT_A_DAY) == []


def test_a_file_on_the_frozen_clock_is_exempt():
    assert lines_in("from support.frozen_clock import frozen_datetime\n" + PLANTED) == []


def test_a_planted_file_turns_the_census_red(tmp_path):
    (tmp_path / "test_new.py").write_text(PLANTED)
    assert len(census(tmp_path)) == 8


# --- The script ---


def test_the_script_runs_the_pinned_and_the_cleared_files():
    assert files_to_check() == sorted({f for f, _ in PINNED} | set(CLEARED))
    out = subprocess.run(["sh", str(SCRIPT), "--list"], capture_output=True, text=True,
                         check=True).stdout.split()
    assert out == [f"tests/{f}" for f in files_to_check()]


def test_the_script_names_the_four_moments():
    text = SCRIPT.read_text(encoding="utf-8")
    for moment in ("2026-10-31 21:00:00", "2026-10-07 21:00:00", "2026-12-31 21:00:00",
                   "2026-11-01 00:30:00"):
        assert moment in text


def test_the_close_out_skill_names_the_script():
    skill = (ROOT / ".claude" / "skills" / "closeout" / "SKILL.md").read_text(encoding="utf-8")
    assert "`clock_check.sh`" in skill
    assert "month's last evening" in skill
