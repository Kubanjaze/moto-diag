"""Read code, not commentary — Phase 244G.

Four times in one session a guard matching an identifier as **text** fired on
the **prose** explaining it. Phase 241's SafetyChecker tripwire fired on a
docstring citing it as a cross-reference; Phase 244D's guard against
``INSERT OR IGNORE`` fired on the comment saying why it is not used.

The reverse is worse and quieter: ``assert "get_session" in src`` passes if the
identifier survives only in a comment, so deleting the code the guard protects
leaves the guard green.

:func:`code_of` returns source with comments and docstrings blanked and
everything else byte-for-byte intact, so an assertion tests what runs.

**Ordinary string literals are kept.** A guard pinning a ``tool_choice`` dict or
an ``ORDER BY`` clause is reading code that happens to be a string; blanking
those would break the very guards this exists to keep working.

**Formatting is preserved deliberately.** Comments and docstrings are replaced
with equivalent whitespace rather than removed, so line numbers, columns and
indentation survive and a guard matching a multi-line literal still matches.
That rules out ``ast.unparse``, which normalises quoting and layout.
"""

from __future__ import annotations

import ast
import inspect
import io
import tokenize
from pathlib import Path
from typing import Union

#: Put this marker in a test file to opt a deliberate raw-source assertion out
#: of the meta-guard. Rare, and it should carry a reason on the same line.
RAW_SOURCE_OK = "raw-source-ok"


def _docstring_token_positions(source: str) -> set[tuple[int, int]]:
    """(line, col) starts of every module/class/function docstring."""
    out: set[tuple[int, int]] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            out.add((first.value.lineno, first.value.col_offset))
    return out


def blank_comments_and_docstrings(source: str) -> str:
    """Blank comments and docstrings, preserving every other byte and position."""
    lines = source.splitlines(keepends=True)
    docstrings = _docstring_token_positions(source)

    # (line_index, start_col, end_col) spans to blank, applied per line so that
    # multi-line docstrings keep their line count and everything after them
    # stays where it was.
    spans: list[tuple[int, int, int]] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source

    for tok in tokens:
        is_comment = tok.type == tokenize.COMMENT
        is_docstring = tok.type == tokenize.STRING and (tok.start[0], tok.start[1]) in docstrings
        if not (is_comment or is_docstring):
            continue
        (srow, scol), (erow, ecol) = tok.start, tok.end
        for row in range(srow, erow + 1):
            idx = row - 1
            if idx >= len(lines):
                continue
            start = scol if row == srow else 0
            end = ecol if row == erow else len(lines[idx].rstrip("\r\n"))
            spans.append((idx, start, end))

    for idx, start, end in spans:
        line = lines[idx]
        newline = ""
        stripped = line.rstrip("\r\n")
        if len(line) > len(stripped):
            newline = line[len(stripped):]
        end = min(end, len(stripped))
        if start >= end:
            continue
        lines[idx] = stripped[:start] + " " * (end - start) + stripped[end:] + newline

    return "".join(lines)


def code_of(target: Union[str, Path, object]) -> str:
    """Source of ``target`` with comments and docstrings blanked.

    Accepts a module, class, function, or a path to a ``.py`` file.
    """
    if isinstance(target, (str, Path)):
        source = Path(target).read_text(encoding="utf-8")
    else:
        source = inspect.getsource(target)
    return blank_comments_and_docstrings(source)
