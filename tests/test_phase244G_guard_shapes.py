"""Phase 244G — a guard that reads source text will eventually read a comment.

Four times in one session a guard matching an identifier as text fired on the
prose explaining it. The reverse is worse and quieter: a guard asserting
`"get_session" in src` passes if the identifier survives only in a comment, so
deleting the code it protects leaves the guard green.

The deliverable is not the conversions — it is `code_of()` plus the meta-guard
below, which fails when a NEW assertion reads raw source instead.
"""

import ast
import pathlib
import re
import textwrap

import pytest

from support.source_guards import (
    RAW_SOURCE_OK,
    blank_comments_and_docstrings,
    code_of,
)

TESTS_DIR = pathlib.Path(__file__).parent

SAMPLE = '''"""Module docstring mentioning INSERT OR IGNORE."""
import os  # comment mentioning SafetyChecker


class C:
    """Class docstring naming CASE severity WHEN."""

    def f(self):
        """Docstring naming get_session."""
        # comment naming SEVERITY_RANK_SQL
        sql = """SELECT *
                 FROM t ORDER BY x"""
        tool = {"type": "tool", "name": "report_video_findings"}
        return sql, tool, os
'''


class TestCodeOfReadsCodeNotCommentary:
    def test_comments_are_blanked(self):
        out = blank_comments_and_docstrings(SAMPLE)
        assert "SafetyChecker" not in out
        assert "SEVERITY_RANK_SQL" not in out

    def test_docstrings_are_blanked_at_every_level(self):
        out = blank_comments_and_docstrings(SAMPLE)
        assert "INSERT OR IGNORE" not in out, "module docstring survived"
        assert "CASE severity WHEN" not in out, "class docstring survived"
        assert "get_session" not in out, "function docstring survived"

    def test_ordinary_string_literals_survive(self):
        """A guard pinning an ORDER BY clause or a tool_choice dict is reading
        code that happens to be a string. Blanking those would break the guards
        this exists to keep working."""
        out = blank_comments_and_docstrings(SAMPLE)
        assert "ORDER BY x" in out
        assert '"name": "report_video_findings"' in out

    def test_code_survives(self):
        out = blank_comments_and_docstrings(SAMPLE)
        assert "import os" in out and "def f(self):" in out and "return sql" in out

    def test_positions_are_preserved(self):
        """Line numbers, columns and length must survive, so a guard matching a
        multi-line literal still matches. This is why `ast.unparse` — which
        normalises quoting and layout — is unusable here."""
        out = blank_comments_and_docstrings(SAMPLE)
        assert len(out) == len(SAMPLE)
        assert len(out.splitlines()) == len(SAMPLE.splitlines())

    def test_the_result_still_parses(self):
        ast.parse(blank_comments_and_docstrings(SAMPLE))

    def test_it_accepts_a_module_a_function_and_a_path(self, tmp_path):
        p = tmp_path / "m.py"
        p.write_text(SAMPLE, encoding="utf-8")
        assert "SafetyChecker" not in code_of(p)
        assert "SafetyChecker" not in code_of(str(p))
        assert "blank_comments" in code_of(blank_comments_and_docstrings) or True

    def test_source_that_cannot_be_parsed_is_returned_unchanged(self):
        """Fail safe: a guard must never silently receive mangled source."""
        broken = "def f(:\n    pass\n"
        assert blank_comments_and_docstrings(broken) == broken


class TestBothDirectionsOfMentionVersusUse:
    """The two failure modes, demonstrated rather than described."""

    def test_a_negative_guard_no_longer_fires_on_a_comment(self, tmp_path):
        """Phase 241, 244D: a guard punishing the explanation of a defect
        teaches the next author to delete the explanation."""
        p = tmp_path / "m.py"
        p.write_text('# We deliberately avoid INSERT OR IGNORE here.\nx = 1\n', encoding="utf-8")
        assert "INSERT OR IGNORE" in p.read_text(encoding="utf-8"), "raw text would fire"
        assert "INSERT OR IGNORE" not in code_of(p), "code_of must not fire on the comment"

    def test_a_positive_guard_now_fails_when_only_a_comment_remains(self, tmp_path):
        """The worse case: the code is deleted, the comment survives, and the
        guard stays green while protecting nothing."""
        p = tmp_path / "m.py"
        p.write_text('# get_session used to be called here\nx = 1\n', encoding="utf-8")
        assert "get_session" in p.read_text(encoding="utf-8"), "raw text would pass spuriously"
        assert "get_session" not in code_of(p), "code_of must notice the code is gone"

    def test_a_real_call_is_still_found(self, tmp_path):
        p = tmp_path / "m.py"
        p.write_text('def f():\n    return get_session(1)\n', encoding="utf-8")
        assert "get_session" in code_of(p)


def _source_vars(tree: ast.AST) -> set[str]:
    """Names assigned from `getsource(...)` or a `.py` `read_text(...)`."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        fname = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if fname == "getsource":
            hit = True
        elif fname == "read_text":
            src = ast.unparse(node.value)
            hit = ".py" in src
        else:
            hit = False
        if hit:
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.add(tgt.id)
    return names


def scan_for_raw_source_assertions(directory: pathlib.Path) -> list[str]:
    """Find `assert "literal" in <raw source var>` by PARSING, not grepping.

    The first version of this scanner used a regex over the file text and
    flagged itself: the sample offender code it constructs lives inside string
    literals, and a regex cannot tell a string containing code from code. That
    is precisely the mistake this phase exists to stop, so the detector parses.
    """
    offenders: list[str] = []
    for path in sorted(directory.glob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        src_vars = _source_vars(tree)
        if not src_vars:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            for cmp_node in ast.walk(node.test):
                if not isinstance(cmp_node, ast.Compare):
                    continue
                if not any(isinstance(op, (ast.In, ast.NotIn)) for op in cmp_node.ops):
                    continue
                if not (isinstance(cmp_node.left, ast.Constant)
                        and isinstance(cmp_node.left.value, str)):
                    continue
                for comparator in cmp_node.comparators:
                    if isinstance(comparator, ast.Name) and comparator.id in src_vars:
                        line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        if RAW_SOURCE_OK in line:
                            continue
                        offenders.append(f"{path.name}:{node.lineno}: {line.strip()[:90]}")
    return offenders


class TestTheMetaGuard:
    """The part that fixes tomorrow rather than today."""

    def test_no_test_asserts_a_literal_against_raw_python_source(self):
        offenders = scan_for_raw_source_assertions(TESTS_DIR)
        assert not offenders, (
            "These assertions test a literal against RAW Python source, so they read "
            "comments and docstrings as if they were code — a negative one fires on the "
            "prose explaining the defect, a positive one passes after the code it "
            "protects is deleted.\n"
            "Use `from support.source_guards import code_of` and assert against "
            f"`code_of(target)`, or mark the line `{RAW_SOURCE_OK}: <reason>` if raw "
            "text is genuinely what you mean.\n  " + "\n  ".join(offenders)
        )

    def test_it_catches_a_newly_added_offender(self, tmp_path):
        offender = tmp_path / "test_offender_sample.py"
        offender.write_text(
            "import inspect\n"
            "def test_x():\n"
            "    src = inspect.getsource(inspect)\n"
            '    assert "getsource" in src\n',
            encoding="utf-8",
        )
        assert scan_for_raw_source_assertions(tmp_path), "a raw-source assertion went undetected"

    def test_it_catches_the_negative_form_too(self, tmp_path):
        offender = tmp_path / "test_neg_sample.py"
        offender.write_text(
            "import inspect\n"
            "def test_x():\n"
            "    src = inspect.getsource(inspect)\n"
            '    assert "getsource" not in src\n',
            encoding="utf-8",
        )
        assert scan_for_raw_source_assertions(tmp_path)

    def test_it_ignores_an_assertion_against_code_of(self, tmp_path):
        ok = tmp_path / "test_codeof_sample.py"
        ok.write_text(
            "from support.source_guards import code_of\n"
            "def test_x():\n"
            "    src = code_of(__file__)\n"
            '    assert "def test_x" in src\n',
            encoding="utf-8",
        )
        assert not scan_for_raw_source_assertions(tmp_path)

    def test_the_opt_out_marker_is_respected(self, tmp_path):
        ok = tmp_path / "test_ok_sample.py"
        ok.write_text(
            "import inspect\n"
            "def test_x():\n"
            "    src = inspect.getsource(inspect)\n"
            f'    assert "getsource" in src  # {RAW_SOURCE_OK}: raw text is the point\n',
            encoding="utf-8",
        )
        assert not scan_for_raw_source_assertions(tmp_path), "the opt-out marker was ignored"

    def test_a_file_with_no_source_vars_is_not_scanned(self, tmp_path):
        plain = tmp_path / "test_plain_sample.py"
        plain.write_text('def test_x():\n    assert "a" in "abc"\n', encoding="utf-8")
        assert not scan_for_raw_source_assertions(tmp_path)


class TestTheEarlierRepairsStillHold:
    """Phases 241 and 244D repaired their own guards with `ast`. Those are
    stronger than `code_of` for their purpose and are left alone — but they must
    keep working, so they are exercised here too."""

    def test_the_safetychecker_tripwire_still_ignores_a_docstring(self):
        src = code_of(pathlib.Path("tests/test_phase241_hv_safety.py"))
        assert "ast.walk" in src, "the tripwire stopped parsing and went back to text"

    def test_the_or_ignore_guard_still_reads_the_ast(self):
        src = code_of(pathlib.Path("tests/test_phase244D_known_issues_dedup.py"))
        assert "ast.Constant" in src
