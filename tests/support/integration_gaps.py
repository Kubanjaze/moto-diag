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
import re
from collections import Counter
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


def _load(root: Path) -> tuple[dict[Path, str], dict[Path, str]]:
    raw = {p: p.read_text(encoding="utf-8", errors="replace")
           for p in _source_files(root)}
    code = {p: blank_comments_and_docstrings(s) for p, s in raw.items()}
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


def entry_points_from_pyproject(pyproject_text: str) -> set[str]:
    """Module half of every `name = "module:attr"` console script."""
    section = re.search(
        r"^\[project\.scripts\]\s*$(.*?)(?=^\[|\Z)", pyproject_text, re.M | re.S,
    )
    if not section:
        return set()
    return set(re.findall(r'=\s*"([\w.]+):', section.group(1)))
