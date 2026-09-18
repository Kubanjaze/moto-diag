"""Phase 209B — find code that was built and never connected.

The 244 series kept finding this by accident: the whole `feedback/` package
had no caller for nine phases, `diagnose quick` had never completed,
`SafetyChecker` and the `VehicleContext` builder were stubs nothing noticed.
This module finds that shape on purpose.

Two shapes, because one scan misses the other:

**Orphans** — a public top-level function or class that nothing else in the
source tree refers to.

**Islands** — a package whose members refer to each other (so none of them
looks orphaned) but which nothing OUTSIDE the package reaches.
`motodiag.scheduling` is the case that motivated this: twelve public names,
all internally consistent, zero external references.

**References are counted in code only.** Comments and docstrings are blanked
first. Without that, a function that is merely *described* in a docstring
elsewhere looks called — a false negative, the dangerous direction, and the
mention-vs-use family this project has hit five times.

Framework entry points are not orphans: a route handler is called by FastAPI,
a click command by click, a validator by pydantic. Those are excluded by
decorator. Console-script entry points in `pyproject.toml` count as references.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from support.source_guards import blank_comments_and_docstrings

# Decorators whose presence means "the framework calls this".
_FRAMEWORK_DECORATOR = re.compile(
    r"(?:router|app)\s*\.\s*(?:get|post|put|patch|delete|websocket|middleware"
    r"|exception_handler|on_event)"
    r"|\.command\b|\.group\b|click\.(?:group|command)"
    r"|field_validator|model_validator|\bvalidator\b|root_validator"
    r"|\bproperty\b|staticmethod|classmethod|lru_cache|cache\b"
)

# Packages that are entry surfaces rather than libraries: everything in them is
# reached by a framework, so asking "does anything outside reach this package"
# is the wrong question.
_ENTRY_PACKAGES = frozenset({"cli", "api", "core"})


def _source_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.py") if "__pycache__" not in p.parts
    )


def _public_defs(path: Path, source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names = []
    for node in tree.body:
        if not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        if node.name.startswith("_"):
            continue
        decorators = [ast.unparse(d) for d in node.decorator_list]
        if any(_FRAMEWORK_DECORATOR.search(d) for d in decorators):
            continue
        names.append(node.name)
    return names


def _package_of(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


# Phase 244X: the alias group is either a parenthesised list, which may span
# lines, or the rest of the line. 244U's `[^)\n]*` stopped at a newline, so
# the multi-line form most packages here use was never blanked at all.
_FROM_IMPORT = re.compile(r"(from\s+[\w\.]+\s+import\s*)(\([^)]*\)|[^\n]*)")
_ALL_ASSIGN = re.compile(r"__all__\s*=\s*[\[\(](?:[^\]\)]*)[\]\)]", re.S)
_STRING_LITERAL = re.compile(r"\"[^\"]*\"|'[^']*'")


def _blank_identifiers(text: str) -> str:
    return _IDENTIFIER_FOR_BLANKING.sub(lambda m: "_" * len(m.group(0)), text)


_IDENTIFIER_FOR_BLANKING = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def blank_exports(source: str, *, is_init: bool) -> str:
    """Blank re-exported names so a re-export stops reading as a use.

    Phase 244U. The scanner counts identifiers, and a package re-export writes
    the name twice — once in the ``from … import`` alias list, once in
    ``__all__`` — so every name a package exports looked referenced whether or
    not anything called it. ``SafetyChecker`` is the proof: Phase 241 recorded
    that it had no caller, ``engine/__init__`` re-exported it, and the gate
    stayed silent until Phase 244T wired it four phases later.

    **Both halves are required.** Measured on this tree: blanking the alias
    lists alone reveals nothing at all (46 orphans, unchanged), blanking
    ``__all__`` alone reveals 3, and together they reveal 20 — because
    blanking one occurrence leaves the other standing. An implementer who
    ships the first half, sees a green gate and stops has learned the opposite
    of the truth.

    Phase 244X: the alias list may be parenthesised across several lines —
    ``auth``, ``inventory``, ``billing`` and ``feedback`` all export that way
    — and 244U's regex stopped at the first newline, so for those packages
    the rule above had never applied. 57 names surfaced when it did.

    The module path in a ``from`` statement is deliberately left intact:
    :func:`find_unreachable_modules` walks imports for the reachability half
    of the gate, and blanking the path would break it.
    """
    out = _ALL_ASSIGN.sub(
        lambda m: _STRING_LITERAL.sub(
            lambda s: s.group(0)[0] + "_" * (len(s.group(0)) - 2) + s.group(0)[0],
            m.group(0),
        ),
        source,
    )
    if is_init:
        out = _FROM_IMPORT.sub(
            lambda m: m.group(1) + _blank_identifiers(m.group(2)), out,
        )
    return out


def blank_prose_strings(source: str) -> str:
    """Blank identifiers inside string literals that read as prose.

    Phase 244W. Comments and docstrings were already blanked; a name inside an
    error message or a migration description was not, so
    ``feedback/learning_hook.py`` — whose only mention outside its package init
    is *"phases 318-327 consume this via FeedbackReader read-only hook."* in
    ``core/migrations.py:545`` — counted as used. The mention-vs-use family,
    in a string.

    A literal containing a space is prose. One without — a dotted module path,
    a ``post_apply="mod:attr"`` hook, a table name — is left alone, because
    the dynamic-import and hook scans read those. Tokenizer-based, so the
    ``{expr}`` parts of an f-string stay code: only ``FSTRING_MIDDLE`` chunks
    are touched. Any source the tokenizer rejects is returned unchanged, the
    same fallback the docstring blanking uses.
    """
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return source
    prose_types = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", -1)}
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    out = list(source)
    for tok in tokens:
        if tok.type not in prose_types or " " not in tok.string:
            continue
        # A whole-f-string STRING token (Python < 3.12) carries code in
        # braces; leave it rather than blank an expression.
        if tok.type == tokenize.STRING and "{" in tok.string and \
                tok.string.lstrip("rRbBuU")[:1] in ("f", "F"):
            continue
        a = offsets[tok.start[0] - 1] + tok.start[1]
        b = offsets[tok.end[0] - 1] + tok.end[1]
        out[a:b] = list(_blank_identifiers(source[a:b]))
    return "".join(out)


def _load(root: Path) -> tuple[dict[Path, str], dict[Path, str]]:
    raw = {p: p.read_text(encoding="utf-8", errors="replace")
           for p in _source_files(root)}
    code = {
        p: blank_exports(
            blank_prose_strings(blank_comments_and_docstrings(s)),
            is_init=(p.name == "__init__.py"),
        )
        for p, s in raw.items()
    }
    return raw, code


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def find_orphans(
    root: Path, *, extra_reference_text: str = "",
) -> set[str]:
    """`relative/path.py::name` for every public def nothing else refers to.

    Identifiers are counted once per file rather than searched for once per
    definition: the naive form ran ~300,000 regex scans over this tree and
    made the gate take most of a minute.
    """
    raw, code = _load(root)
    counts = {p: Counter(_IDENTIFIER.findall(text)) for p, text in code.items()}
    total: Counter = Counter()
    for c in counts.values():
        total.update(c)
    extra = set(_IDENTIFIER.findall(extra_reference_text))

    orphans: set[str] = set()
    for path, source in raw.items():
        own = counts[path]
        for name in _public_defs(path, source):
            # References anywhere, minus this file's own count, plus this
            # file's count minus the definition itself.
            elsewhere = total[name] - own[name]
            here = own[name] - 1
            if elsewhere <= 0 and here <= 0 and name not in extra:
                orphans.add(f"{path.relative_to(root).as_posix()}::{name}")
    return orphans


def find_islands(
    root: Path, *, entry_packages: Iterable[str] = _ENTRY_PACKAGES,
) -> set[str]:
    """Packages none of whose public names are referenced from outside."""
    raw, code = _load(root)
    entry = set(entry_packages)

    by_package: dict[str, list[str]] = {}
    for path, source in raw.items():
        if path.parent == root:
            continue  # top-level modules are not packages
        pkg = _package_of(path, root)
        by_package.setdefault(pkg, []).extend(_public_defs(path, source))

    islands: set[str] = set()
    for pkg, names in by_package.items():
        if pkg in entry or not names:
            continue
        outside = {p: t for p, t in code.items()
                   if _package_of(p, root) != pkg}
        reached = any(
            re.search(rf"\b{re.escape(n)}\b", t)
            for n in set(names)
            for t in outside.values()
        )
        # A package can also be reached by module path without naming a
        # member, e.g. `import motodiag.scheduling as s` then `s.x()`.
        if not reached:
            mod_ref = re.compile(rf"\bmotodiag\.{re.escape(pkg)}\b")
            reached = any(mod_ref.search(t) for t in outside.values())
        if not reached:
            islands.add(pkg)
    return islands


# ---------------------------------------------------------------------------
# Reachability — the primary check
# ---------------------------------------------------------------------------

# A literal module path handed to a dynamic loader is an import edge. Missing
# these would one day report a dynamically loaded module as dead.
_DYNAMIC_IMPORT = re.compile(
    r"""(?:import_module|__import__)\(\s*["']([\w.]+)["']"""
)
_POST_APPLY = re.compile(r"""post_apply\s*=\s*["']([\w.]+):""")


def module_map(src_root: Path, package: str) -> dict[str, Path]:
    """Dotted module name -> file, for every module in `package`."""
    mods: dict[str, Path] = {}
    for path in _source_files(src_root / package):
        parts = list(path.relative_to(src_root).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        mods[".".join(parts)] = path
    return mods


def _imports(name: str, path: Path, known: set[str]) -> set[str]:
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    base = name if path.name == "__init__.py" else name.rsplit(".", 1)[0]
    found: set[str] = set()
    # ast.walk, not tree.body: lazy imports inside functions are real edges,
    # and this codebase uses them heavily to keep optional deps optional.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                anchor = base.split(".")
                if node.level > 1:
                    anchor = anchor[: len(anchor) - (node.level - 1)]
                mod = ".".join(anchor + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            found.add(mod)
            # `from pkg import submodule` imports the submodule.
            found.update(f"{mod}.{a.name}" for a in node.names)
    code = blank_comments_and_docstrings(source)
    found.update(_DYNAMIC_IMPORT.findall(code))
    found.update(_POST_APPLY.findall(code))

    # Importing a.b.c runs a/__init__ and a/b/__init__ as well.
    expanded: set[str] = set()
    for mod in found:
        bits = mod.split(".")
        expanded.update(".".join(bits[:i]) for i in range(1, len(bits) + 1))
    return expanded & known


def find_unreachable_modules(
    src_root: Path, package: str, entry_points: Iterable[str],
) -> set[str]:
    """Modules no import chain from any entry point can reach."""
    mods = module_map(src_root, package)
    known = set(mods)
    graph = {m: _imports(m, p, known) for m, p in mods.items()}

    seen: set[str] = set()
    stack = [e for e in entry_points if e in known]
    missing = [e for e in entry_points if e not in known]
    if missing:
        raise ValueError(f"entry points not found in {package}: {missing}")
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        stack.extend(graph[mod] - seen)
    return known - seen


def _public_surface(source: str) -> set[str]:
    """Every public name a module defines at top level — the module's reason
    to exist. Unlike :func:`_public_defs` this keeps framework-decorated names
    and adds module-level constants: a route module's surface *is* its
    handlers and its ``router``. Stripping them leaves the module vacuously
    dead and everything it calls follows — 55 modules, 15,669 lines, measured.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets
                         if isinstance(t, ast.Name) and not t.id.startswith("_"))
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
                names.add(node.target.id)
    return names


def find_module_islands(
    src_root: Path, package: str, entry_points: Iterable[str],
) -> set[str]:
    """Modules no public name of which is used by any live module.

    Phase 244W. The gate's second blind spot, after 244U's re-exports: a
    module whose names refer only to each other, inside a package that is
    otherwise alive. The import walk cannot see it (the ``__init__`` import
    edge is real), the package-level island check cannot (the package is
    alive), and the orphan count cannot — a class that names itself counts
    as used, and a dead module naming another launders it. ``engine/history``
    and ``engine/retrieval``, 668 lines with no caller, were invisible to all
    three.

    A reference is evidence of life only if the referring module is not the
    defining module, not a package ``__init__`` (244U's rule, applied at
    referrer granularity rather than by text), and not itself an island.
    The island set starts as :func:`find_unreachable_modules`' answer, which
    is the one seed that changes the result: a name collision with an
    already-dead module (``add_item`` in ``pricing/repair_plan``) otherwise
    shields a second dead module (``inventory/item_repo``). Then iterate to a
    fixpoint — two generations on this tree. Only what the existing checks do
    not already report is returned.

    An entry point is never a candidate: it is the root the question is
    asked from. On this tree that never mattered, because ``cli`` is named
    in dozens of files — and the synthetic trees showed what happens when it
    is not: the entry module is flagged, its references stop counting, and
    everything it calls follows. Route modules survive the same way today,
    through ``app.py`` naming each ``router``; a framework that registered
    handlers by discovery instead of by name would need a seed here.

    A module with no public surface is never flagged: there is no name-level
    evidence either way, and it may exist for an import side effect. The
    limitation inherited from the whole gate stands: a name collision with a
    *live* module hides a dead one.
    """
    mods = module_map(src_root, package)
    by_path = {p: m for m, p in mods.items()}
    raw, code = _load(src_root / package)
    roots = set(entry_points)

    surface = {by_path[p]: _public_surface(text) for p, text in raw.items()}
    mentioned_by: dict[str, set[str]] = defaultdict(set)
    for path, text in code.items():
        if path.name == "__init__.py":
            continue
        for name in set(_IDENTIFIER.findall(text)):
            mentioned_by[name].add(by_path[path])

    already_dead = find_unreachable_modules(src_root, package, entry_points)
    islands = set(already_dead)
    candidates = [
        m for m, p in mods.items()
        if p.name != "__init__.py" and surface[m]
        and m not in islands and m not in roots
    ]
    changed = True
    while changed:
        changed = False
        for m in candidates:
            if m in islands:
                continue
            alive = any(mentioned_by[n] - islands - {m} for n in surface[m])
            if not alive:
                islands.add(m)
                changed = True
    return islands - already_dead


def entry_points_from_pyproject(pyproject_text: str) -> set[str]:
    """Module half of every `name = "module:attr"` console script."""
    section = re.search(
        r"^\[project\.scripts\]\s*$(.*?)(?=^\[|\Z)", pyproject_text, re.M | re.S,
    )
    if not section:
        return set()
    return set(re.findall(r'=\s*"([\w.]+):', section.group(1)))
