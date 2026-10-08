"""Phase 378, K19 — test lines that turn the real clock into a day, month,
year or minute. ONE implementation: the census test pins what it finds, and
`.claude/skills/closeout/clock_check.sh` runs the files it names under a
faked clock.

Four failures came from such lines (F10, 370's minute, F196 twice): a test
that passes at noon and fails from 20:00 EDT, when the UTC day is already
tomorrow, or on a month's last evening, when it is already next month.

**The rule, by parsing (244G's lesson: a grep reads comments and strings).**
- A *real-clock read* is a call of `.now(…)`, `.utcnow()` or `.today()` on a
  name or attribute that is `date`, ends in `_date`, or ends in `datetime`.
  A name assigned from one in the same file is a read too.
- It is *turned into a day, month, year or minute* when the value, or the
  value plus or minus a timedelta, meets:
  - `.date()`, or `.year`, `.month`, `.day`, `.hour`, `.minute`;
  - `.strftime(fmt)` whose literal format has no seconds (`%S`, `%f`, `%s`,
    `%T`, `%X`, `%c`, `%r`);
  - `.isoformat()` of `date.today()`;
  - a `[:n]` slice of an `.isoformat()` with n ≤ 16.
- **Exempt by convention:** a file importing `support.frozen_clock`. Its
  clock is the frozen one where the test sets it.

**What it cannot see.** A product's own clock (370's minute was the rate
limiter's), a clock read through a helper in another file, and `time.time()`.
"""

from __future__ import annotations

import ast
import pathlib
import re

CLOCK_CALLS = frozenset({"now", "utcnow", "today"})
DAY_ATTRS = frozenset({"year", "month", "day", "hour", "minute"})
SECONDS = re.compile(r"%[STfsXcr]")
FROZEN = re.compile(r"^\s*(from|import)\s+support\.frozen_clock\b", re.M)


def _ident(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def clock_kind(node: ast.AST) -> str | None:
    """'date' or 'datetime' for a real-clock read, else None."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in CLOCK_CALLS):
        return None
    base = _ident(node.func.value)
    if base == "date" or base.endswith("_date"):
        return "date"
    if base.endswith("datetime"):
        return "datetime"
    return None


def _becomes_a_day(node: ast.AST, kind: str, parents: dict) -> bool:
    cur = node
    while True:
        par = parents.get(cur)
        if isinstance(par, ast.BinOp) and isinstance(par.op, (ast.Add, ast.Sub)) \
                and kind != "iso":
            cur = par  # a datetime plus or minus a timedelta is still the clock
            continue
        if isinstance(par, ast.Subscript) and par.value is cur:
            s = par.slice
            return (kind == "iso" and isinstance(s, ast.Slice) and s.lower is None
                    and isinstance(s.upper, ast.Constant) and isinstance(s.upper.value, int)
                    and s.upper.value <= 16)
        if not (isinstance(par, ast.Attribute) and par.value is cur):
            return False
        call = parents.get(par)
        is_call = isinstance(call, ast.Call) and call.func is par
        if par.attr in DAY_ATTRS or (par.attr == "date" and is_call):
            return True
        if par.attr == "strftime" and is_call:
            fmt = call.args[0] if call.args else None
            return (isinstance(fmt, ast.Constant) and isinstance(fmt.value, str)
                    and not SECONDS.search(fmt.value))
        if par.attr == "isoformat" and is_call:
            if kind == "date":
                return True
            kind, cur = "iso", call
            continue
        return False


def lines_in(text: str) -> list[tuple[int, str]]:
    """(line number, stripped line) for each line of ``text`` that turns the
    real clock into a day, month, year or minute; [] for a frozen-clock file."""
    if FROZEN.search(text):
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    parents = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    bound: dict[str, str] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            kind = clock_kind(n.value)
            if kind:
                bound[n.targets[0].id] = kind
    source = text.splitlines()
    hits: dict[int, str] = {}
    for n in ast.walk(tree):
        kind = clock_kind(n)
        if kind is None and isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            kind = bound.get(n.id)
        if kind and _becomes_a_day(n, kind, parents):
            hits[n.lineno] = source[n.lineno - 1].strip()
    return sorted(hits.items())


def census(tests_dir: pathlib.Path) -> list[tuple[str, str]]:
    """(file, line text) for every such line under ``tests_dir``, a line
    repeated as often as it occurs."""
    found = []
    for path in sorted(tests_dir.rglob("*.py")):
        for _, text in lines_in(path.read_text(encoding="utf-8")):
            found.append((path.relative_to(tests_dir).as_posix(), text))
    return sorted(found)


#: The census on 2026-10-07 (Phase 378). Each was run with the whole
#: process's clock faked by libfaketime at 375's four moments and passed
#: (375's bug fix #2, F196). A new line fails the census: give its test 370's
#: frozen clock. A line that goes leaves this pin in the same commit.
PINNED: list[tuple[str, str]] = sorted([
    ("test_phase152_history.py", '(vid, "frobnicate", date.today().isoformat()),'),
    ("test_phase171_analytics.py", 'today = datetime.utcnow().strftime("%Y-%m-%d")'),
    ("test_phase171_analytics.py", 'today = datetime.utcnow().strftime("%Y-%m-%d")'),
    ("test_phase171_analytics.py", "datetime.utcnow() - timedelta(days=1)"),
    ("test_phase274_quotes_variance.py", 'assert quoted_at[:10] == NOW.strftime("%Y-%m-%d")'),
    ("test_phase281_intake_month.py",
     'first = datetime.now(timezone.utc).strftime("%Y-%m-01 00:00:01")'),
    ("test_phase281_intake_month.py",
     "year, month = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)"),
    ("test_phase281_vin_year.py", "latest_possible = real_datetime.now().year + 1"),
])

#: Files whose clock-to-day lines were fixed by deriving the shop's day
#: (`core.timestamps.local_day`), so the census no longer reports them. The
#: script runs them too, because the fix is what it proves.
CLEARED = (
    "test_phase274_pnl.py",                # F196, 375's bug fix #2
    "test_phase275_accounting_export.py",  # F196, 375's bug fix #1
)


def files_to_check() -> list[str]:
    """What `clock_check.sh` runs: every pinned file, and the cleared ones."""
    return sorted({f for f, _ in PINNED} | set(CLEARED))
