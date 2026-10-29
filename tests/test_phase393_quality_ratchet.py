"""Phase 393 (K54) — the ratchet: the code's counts may only improve.

Six counts are measured here by `scripts/code_quality.py` and compared with
their one pin each in `tests/support/quality_counts.py`:

- above the pin fails: the code got worse;
- below the pin fails too, until the pin is lowered in the same commit, so a
  gain is locked in and cannot quietly be spent again.

The seventh, line coverage, works the other way and comes from the full
run, so `regression.sh` holds it (`code_quality.py coverage-gate`), and this
file holds the gate and its wiring.

Planted trees are built in `tmp_path`, never in `src/` (Phase 355 bug fix
#2: a control planted in the real tree).
"""
from __future__ import annotations

import ast
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
sys.path.insert(0, str(ROOT / "scripts"))

import code_quality as cq  # noqa: E402
from support import quality_counts as QC  # noqa: E402

#: The pin's name, and the count `code_quality.counts` gives it under.
PINNED = {
    "RUFF_FINDINGS": "ruff",
    "MYPY_ERRORS": "mypy",
    "COMPLEX_FUNCTIONS": "complex",
    "BIG_FILES": "big",
    "PRIVATE_HELPERS": "helpers",
    "SWALLOWED_EXCEPTIONS": "swallowed",
}


def ratchet(name: str, measured: int, pin: int) -> str | None:
    """Why `measured` does not hold `pin`, or None."""
    if measured > pin:
        return (f"{name}: {measured}, above its pin {pin}: the code got worse. Fix what "
                f"was added (each count's rule is in scripts/code_quality.py).")
    if measured < pin:
        return (f"{name}: {measured}, below its pin {pin}: lower {name} in "
                f"tests/support/quality_counts.py to {measured} in this commit, with the "
                f"reason in its history, so the gain is locked in.")
    return None


@pytest.fixture(scope="module")
def measured() -> dict:
    return cq.counts(ROOT)


# ------------------------------------------------------- the six counts
@pytest.mark.parametrize("name", sorted(PINNED))
def test_each_count_holds_its_pin(name, measured):
    why = ratchet(name, measured[PINNED[name]], getattr(QC, name))
    assert why is None, why


def test_coverage_is_pinned_as_a_percent():
    assert isinstance(QC.COVERAGE_PERCENT, float) and 0 < QC.COVERAGE_PERCENT <= 100


# ------------------------------------------------- the ratchet, planted
class TestTheRatchet:
    def test_up_fails(self):
        assert "above its pin" in ratchet("X", 4, 3)

    def test_down_fails_until_the_pin_is_lowered(self):
        assert "lower X" in ratchet("X", 2, 3)

    def test_equal_holds(self):
        assert ratchet("X", 3, 3) is None


@pytest.fixture
def planted(tmp_path) -> pathlib.Path:
    """A tree with a src/ of one module, and this repository's pyproject."""
    (tmp_path / "src" / "motodiag").mkdir(parents=True)
    (tmp_path / "src" / "motodiag" / "__init__.py").write_text("")
    shutil.copyfile(ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    return tmp_path


def _write(tree: pathlib.Path, body: str) -> None:
    (tree / "src" / "motodiag" / "m.py").write_text(body)


class TestEachCountSeesAPlantedCase:
    def test_the_clean_module_counts_nothing(self, planted):
        _write(planted, "def f() -> int:\n    return 1\n")
        assert cq.counts(planted) == {"ruff": 0, "mypy": 0, "complex": 0, "big": 0,
                                      "helpers": 0, "swallowed": 0}

    def test_a_swallowed_exception(self, planted):
        _write(planted, "def f():\n    try:\n        return 1\n    except Exception:\n"
                        "        pass\n")
        assert cq.counts(planted)["swallowed"] == 1

    def test_a_handler_that_names_its_error_is_not_counted(self, planted):
        """The exclusion's control: only `Exception` with a body of `pass`."""
        _write(planted, "def f():\n    try:\n        return 1\n    except KeyError:\n"
                        "        pass\n    except Exception:\n        raise\n")
        assert cq.counts(planted)["swallowed"] == 0

    def test_a_money_and_a_time_helper(self, planted):
        _write(planted, "def _money(c):\n    return c\n\n\ndef _now_iso():\n    return ''\n\n\n"
                        "def money():\n    return 1\n")
        assert cq.counts(planted)["helpers"] == 2

    def test_a_lint_finding_and_a_type_error(self, planted):
        _write(planted, "import os\n\n\ndef f() -> int:\n    return 'x'\n")
        got = cq.counts(planted)
        assert (got["ruff"], got["mypy"]) == (1, 1)

    def test_a_function_over_mccabe_20(self, planted):
        branches = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(21))
        _write(planted, f"def f(x):\n{branches}    return -1\n")
        assert cq.counts(planted)["complex"] == 1

    def test_a_file_over_100_kb(self, planted):
        _write(planted, "X = 1\n" + ("# " + "x" * 96 + "\n") * 1011)
        assert (planted / "src/motodiag/m.py").stat().st_size > cq.SIZE_LIMIT
        assert cq.counts(planted)["big"] == 1


def test_the_operators_numbers():
    """K54: "85% changed-line coverage, McCabe 20, 100 KB per file"."""
    assert (cq.CHANGED_COVERAGE, cq.COMPLEXITY_LIMIT, cq.SIZE_LIMIT) == (85.0, 20, 100_000)


# ------------------------------------------------------- the coverage gate
class TestTheCoverageGate:
    def test_below_the_pin_fails(self):
        ok, line = cq.coverage_gate(70.0, 71.0, "abc1234")
        assert not ok and "below the pin" in line and "not of record" in line

    def test_at_the_pin_passes(self):
        ok, line = cq.coverage_gate(71.0, 71.0, "abc1234")
        assert ok and line.startswith(cq.COVERAGE_PREFIX) and "raise" not in line

    def test_a_rise_says_to_raise_the_pin(self):
        ok, line = cq.coverage_gate(72.0, 71.0, "abc1234")
        assert ok and "raise COVERAGE_PERCENT" in line

    def test_the_line_parses(self):
        _, line = cq.coverage_gate(87.56, 87.5, "abc1234")
        m = cq.COVERAGE_LINE.search(line)
        assert m and m.group(1) == "87.56" and m.group(2) == "abc1234"

    def test_the_cli_reads_a_coverage_json(self, tmp_path):
        for delta, rc in ((-1.0, 1), (0.0, 0)):
            p = tmp_path / "cov.json"
            p.write_text(json.dumps({"totals": {"percent_covered": QC.COVERAGE_PERCENT + delta},
                                     "files": {}}))
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "code_quality.py"),
                                "coverage-gate", str(p), "abc1234"], capture_output=True,
                               text=True)
            assert r.returncode == rc, r.stdout + r.stderr

    def test_regression_sh_runs_with_coverage_and_the_gate(self):
        """Wiring: the regression of record measures coverage, and a total
        under the pin makes its exit code 1, so its line is not of record."""
        text = (ROOT / ".claude/skills/closeout/regression.sh").read_text()
        assert "--cov=motodiag" in text and "code_quality.py\" coverage-gate" in text
        assert "|| RC=1" in text


# ------------------------------------------------------- one pin per count
def test_no_other_test_file_assigns_a_pin():
    names = {*PINNED, "COVERAGE_PERCENT"}
    found = []
    for path in sorted(TESTS.rglob("*.py")):
        if path.name == "quality_counts.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id in names for t in node.targets):
                found.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not found, "a pin assigned outside tests/support/quality_counts.py: " + ", ".join(found)
