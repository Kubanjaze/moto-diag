"""F9 mock-vs-runtime-drift pattern checks (Phase 191C + 191D).

Standalone CLI invoked from .pre-commit-config.yaml + manually.

Phase 191C checks:
  --check-model-ids: subspecies (ii) narrow — hardcoded model IDs in
      test files. **DEPRECATED at Phase 191D**; stub-redirects to
      ``--check-ssot-constants`` filtered to the model-ID-relevant
      registry entries. Removal targeted Phase 200+.
  --check-deploy-path-init-db: subspecies (iv) — CLI commands launching
      uvicorn/serve without init_db() call.

Phase 191D additions (F20 + F21 mitigations):
  --check-ssot-constants: subspecies (ii) generalized — TOML-driven scan
      of ``tests/**`` for literal pins of any constant declared in
      ``f9_ssot_constants.toml``. Recognizes a new ``contract-pin``
      opt-out subcategory for intentional two-source assertion design.
  --check-tag-catalog-coverage: F21 — diff routes' ``APIRouter(tags=...)``
      strings against ``motodiag.api.openapi.TAG_CATALOG`` and flag
      tags-in-routes-not-in-catalog (error) / tags-in-catalog-not-in-routes
      (warn).

Phase 195C addition (F37 — contract-surface-drift subspecies):
  --check-pydantic-literal-vs-check-constraint: scan
      ``src/motodiag/api/routes/**`` + ``core/models.py`` for Pydantic
      response fields that map to a DB ``CHECK (... IN (...))``
      constraint (parsed from ``core/migrations.py``) but aren't a
      value-set-matching ``Literal``. CHECK sets are keyed by
      ``(table, column)`` so same-named columns across tables (the
      three real ``role`` columns) don't cross-wire. A ``str``-typed
      field or a ``Literal`` value-set mismatch is an error; a
      ``str``/``Enum`` field is a warn. v1.0.2 positive-resolution-
      required matching: a field is flagged only when its model
      resolves to a table that carries a CHECK on that column — a
      mere name-coincidence (no resolution / no CHECK) is no finding.

Importable as a module: ``from check_f9_patterns import (
    check_model_ids, check_deploy_path_init_db, check_ssot_constants,
    check_tag_catalog_coverage, check_pydantic_literal_vs_check_constraint,
    F9Finding, run_all_checks, load_registry
)``

Pattern doc: ``docs/patterns/f9-mock-vs-runtime-drift.md``
"""

from __future__ import annotations

import argparse
import ast
import importlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# Python 3.11+ has tomllib in stdlib; fall back to tomli on older runtimes.
try:  # pragma: no cover — runtime branch
    import tomllib as _tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover — Py<3.11 path
    import tomli as _tomllib  # type: ignore[no-redef]

# Match the model-ID shape ``claude-(haiku|sonnet|opus)-N...`` permissively
# enough to catch every variant the project has produced AND the historical
# bogus IDs we want to lint out:
#   claude-haiku-4-5-20251001    (current Haiku 4.5)
#   claude-sonnet-4-6            (current Sonnet 4.6)
#   claude-opus-4-7              (current Opus 4.7)
#   claude-sonnet-4-5-20241022   (bogus / fabricated; the Phase 191B C2 bug)
# Use ``fullmatch`` against string-literal AST values so docstring substrings
# never trigger false positives.
MODEL_ID_REGEX = re.compile(r"claude-(haiku|sonnet|opus)-[\d\-]+(?:-\d+)?")

# Source-of-truth identifiers that legitimately contain model-ID literals.
# Subspecies (ii) exemption list — keep in sync with the mobile rule
# (eslint-plugin-motodiag/rules/no-hardcoded-model-ids-in-tests.js) per
# Phase 191C plan v1.0.1 Correction 6 (architect-side paired review).
EXEMPT_CONTAINER_NAMES = {
    "KNOWN_GOOD_MODEL_IDS",
    "KNOWN_BOGUS_IDS",
    "MODEL_ALIASES",
    "MODEL_PRICING",
}

# Long-running serve/run patterns that subspecies (iv) cares about.
# Matched as dotted-name strings produced by ``_call_dotted_name``.
SERVE_CALLS = {"uvicorn.run", "app.run", "serve"}


# === Opt-out comment enforcement (Phase 191C Commit 5a refinement) ===
#
# File-level: ``# f9-allow-{kind}: <reason>`` near the top of a file
# opts the entire file out of the named check. ``{kind}`` is one of
# ``model-ids`` or ``deploy-path-init-db``.
#
# Per-line: ``# f9-noqa: {kind} <reason>`` opts a single occurrence
# out (used inside Click-command function bodies for subspecies (iv)).
#
# Both forms require a <reason> at least MIN_OPTOUT_REASON_CHARS long
# so opt-outs can't be drive-by comments. Recommended reason categories
# (not enforced; soft guidance for future audits to bucket by):
#   - SSOT-pin:           file pins canonical model IDs (e.g.,
#                         test_phase79_engine_client validates
#                         MODEL_ALIASES values directly)
#   - meta-test:          file IS a test of the lint/pattern rules
#                         themselves (e.g., test_phase191c_f9_lint
#                         contains synthetic opt-out fixtures)
#   - contract-assertion: line asserts on a backend-controlled
#                         contract value (e.g., the resolved Vision
#                         model used in a captured response)
MIN_OPTOUT_REASON_CHARS = 20
# How many lines from top to scan for the file-level opt-out comment.
# Bumped from 30 to 100 in the Commit 5a sanity-check pass: real Python
# test files put the opt-out below the module docstring, which can run
# 30-50 lines for thoroughly-documented files (e.g.,
# test_phase191b_vision_model_validation.py is 38 lines of docstring).
# 100 covers all realistic cases without becoming a scanning-cost
# concern (test files are typically <500 LoC).
FILE_OPTOUT_SCAN_LINES = 100


@dataclass
class F9Finding:
    """Diagnostic record produced by an F9 check.

    Attributes:
        file: path to the offending source file.
        line: 1-indexed line number of the offending construct.
        rule: short rule name (``"model-ids"`` or ``"deploy-path-init-db"``).
        message: human-readable explanation including the fix path.
        snippet: source line (stripped) for context in the diagnostic.
    """

    file: Path
    line: int
    rule: str
    message: str
    snippet: str

    def format(self) -> str:
        """Render in the standard ``file:line: [rule] message`` shape."""
        return (
            f"{self.file}:{self.line}: [{self.rule}] {self.message}\n"
            f"    {self.snippet}"
        )


# ---------------------------------------------------------------------
# Subspecies (ii) — hardcoded model IDs in test files
# ---------------------------------------------------------------------


def check_model_ids(roots: Iterable[Path]) -> list[F9Finding]:
    """Scan ``test_*.py`` under each root for hardcoded model-ID literals.

    A literal string fully matching :data:`MODEL_ID_REGEX` is flagged unless
    it appears inside an Assign / AnnAssign whose target name is in
    :data:`EXEMPT_CONTAINER_NAMES`. This mirrors the Phase 191B C2 anti-
    regression pattern: ``KNOWN_GOOD_MODEL_IDS`` / ``KNOWN_BOGUS_IDS`` /
    ``MODEL_ALIASES`` / ``MODEL_PRICING`` are the legitimate places for
    these literals to live.

    Args:
        roots: directories to scan recursively (typically ``[Path("tests")]``).

    Returns:
        List of findings; empty if clean.
    """
    findings: list[F9Finding] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("test_*.py")):
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
            except (SyntaxError, OSError):
                continue
            # File-level opt-out: top-of-file `# f9-allow-model-ids:
            # <reason>` (reason length >= MIN_OPTOUT_REASON_CHARS).
            # Phase 191C v1.0.1 + Commit 5a refinement: SSOT-pin test
            # files (test_phase79_engine_client, test_phase162_5_ai_
            # client, test_phase191b_vision_model_validation) opt out
            # entirely because their literals ARE the source of truth
            # — refactoring them through MODEL_ALIASES would make them
            # tautological. Malformed opt-outs (missing reason / too
            # short) emit a finding so the comment can't be a drive-by.
            allow_optout, allow_err = _file_level_optout(
                source, kind="model-ids",
            )
            if allow_optout:
                continue
            if allow_err is not None:
                # Fill in the real path; helper used a placeholder.
                allow_err.file = path
                findings.append(allow_err)
                # Fall through to also report any literal findings —
                # malformed opt-out means it doesn't apply.
            findings.extend(_walk_for_model_ids(tree, path, source))
    return findings


def _walk_for_model_ids(
    tree: ast.AST, path: Path, source: str
) -> list[F9Finding]:
    """AST walk: emit a finding per non-exempt model-ID string literal."""
    findings: list[F9Finding] = []
    source_lines = source.splitlines()

    # Build parent map so the exempt-container check can walk up the chain.
    parent_of: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent_of[child] = node

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if not MODEL_ID_REGEX.fullmatch(node.value):
            continue
        if _is_inside_exempt_container(node, parent_of):
            continue
        snippet = (
            source_lines[node.lineno - 1].strip()
            if 0 <= node.lineno - 1 < len(source_lines)
            else ""
        )
        findings.append(
            F9Finding(
                file=path,
                line=node.lineno,
                rule="model-ids",
                message=(
                    f"Hardcoded model ID literal {node.value!r} found "
                    f"outside source-of-truth set. Move into one of "
                    f"{sorted(EXEMPT_CONTAINER_NAMES)} OR import from "
                    f"src/motodiag/engine/client.py:MODEL_ALIASES."
                ),
                snippet=snippet,
            )
        )
    return findings


def _is_inside_exempt_container(
    node: ast.AST, parent_of: dict[ast.AST, ast.AST]
) -> bool:
    """Return True if ``node`` is inside an exempt-named Assign/AnnAssign."""
    current: ast.AST = node
    while current in parent_of:
        parent = parent_of[current]
        if isinstance(parent, ast.Assign):
            for target in parent.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id in EXEMPT_CONTAINER_NAMES
                ):
                    return True
            # Assigned to a non-exempt target name — definitely not exempt.
            return False
        if isinstance(parent, ast.AnnAssign):
            if (
                isinstance(parent.target, ast.Name)
                and parent.target.id in EXEMPT_CONTAINER_NAMES
            ):
                return True
            return False
        current = parent
    return False


# ---------------------------------------------------------------------
# Subspecies (iv) — deploy-path missing init_db
# ---------------------------------------------------------------------


def check_deploy_path_init_db(cli_dir: Path) -> list[F9Finding]:
    """Scan a CLI package for serve commands that skip ``init_db()``.

    A function is flagged when ALL of the following hold:
      1. It is decorated with ``@<group>.command(...)`` (Click command).
      2. Its body invokes one of :data:`SERVE_CALLS` (``uvicorn.run`` etc.).
      3. Its body does NOT invoke ``init_db(...)`` (any dotted form).
      4. There is no ``# f9-noqa: deploy-path-init-db <reason>`` comment in
         the function body acting as an explicit opt-out.

    Args:
        cli_dir: typically ``Path("src/motodiag/cli")``.

    Returns:
        List of findings; empty if clean or directory missing.
    """
    findings: list[F9Finding] = []
    if not cli_dir.exists():
        return findings
    for path in sorted(cli_dir.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, OSError):
            continue
        source_lines = source.splitlines()
        for func in ast.walk(tree):
            if not isinstance(func, ast.FunctionDef):
                continue
            if not _has_click_command_decorator(func):
                continue
            run_lines = _find_serve_run_calls(func)
            if not run_lines:
                continue
            if _has_init_db_call(func) or _opt_out_present(func, source_lines):
                continue
            for ln in run_lines:
                snippet = (
                    source_lines[ln - 1].strip()
                    if 0 <= ln - 1 < len(source_lines)
                    else ""
                )
                findings.append(
                    F9Finding(
                        file=path,
                        line=ln,
                        rule="deploy-path-init-db",
                        message=(
                            f"CLI command {func.name!r} launches a long-"
                            f"running serve process but does not call "
                            f"init_db() before launch. Add "
                            f"`init_db(settings.db_path, "
                            f"apply_migrations=True)` before the serve "
                            f"call OR opt out with `# f9-noqa: "
                            f"deploy-path-init-db <reason>`."
                        ),
                        snippet=snippet,
                    )
                )
    return findings


def _has_click_command_decorator(func: ast.FunctionDef) -> bool:
    """True if ``func`` carries a ``@<something>.command(...)`` decorator."""
    for dec in func.decorator_list:
        if isinstance(dec, ast.Call):
            target = dec.func
            if isinstance(target, ast.Attribute) and target.attr == "command":
                return True
    return False


def _find_serve_run_calls(func: ast.FunctionDef) -> list[int]:
    """Return line numbers of ``uvicorn.run`` / ``app.run`` etc. inside ``func``."""
    lines: list[int] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            target = _call_dotted_name(node.func)
            if target in SERVE_CALLS:
                lines.append(node.lineno)
    return lines


def _call_dotted_name(node: ast.AST) -> str:
    """Reduce an ``ast.Call.func`` to its dotted-name string (best-effort)."""
    if isinstance(node, ast.Attribute):
        base = _call_dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _has_init_db_call(func: ast.FunctionDef) -> bool:
    """True if ``func`` calls ``init_db(...)`` (bare or dotted)."""
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            name = _call_dotted_name(node.func)
            if name == "init_db" or name.endswith(".init_db"):
                return True
    return False


def _opt_out_present(
    func: ast.FunctionDef, source_lines: list[str]
) -> bool:
    """True if a valid ``# f9-noqa: deploy-path-init-db <reason>`` comment
    is in ``func`` body. Reason must be >= MIN_OPTOUT_REASON_CHARS chars.
    Drive-by ``# f9-noqa: deploy-path-init-db`` (no/short reason) does
    NOT count as an opt-out — keeps the opt-out as a documentation tax,
    not a free escape hatch.
    """
    import re
    pattern = re.compile(
        r"#\s*f9-noqa:\s*deploy-path-init-db\b\s*(.*)$"
    )
    end_line = func.end_lineno or func.lineno
    start = max(0, func.lineno - 1)
    stop = min(end_line, len(source_lines))
    for ln in range(start, stop):
        m = pattern.search(source_lines[ln])
        if m is None:
            continue
        reason = m.group(1).strip()
        if len(reason) >= MIN_OPTOUT_REASON_CHARS:
            return True
        # Comment present but reason too short — don't honor the opt-out.
        # Caller treats this as no opt-out + reports the underlying finding.
    return False


def _file_level_optout(
    source: str, kind: str,
) -> tuple[bool, F9Finding | None]:
    """Scan the first ``FILE_OPTOUT_SCAN_LINES`` lines of ``source`` for
    a ``# f9-allow-{kind}: <reason>`` comment.

    Returns:
        ``(True, None)`` — valid opt-out; the file is exempt from the
            ``{kind}`` check.
        ``(False, finding)`` — comment is present but malformed (missing
            reason or reason shorter than MIN_OPTOUT_REASON_CHARS). The
            returned finding is appended to the rule's output so the
            architect notices the bad comment + can either fix it or
            remove it. The rule continues to report any underlying
            violations.
        ``(False, None)`` — no opt-out comment present; the rule runs
            normally.

    Reason categories (soft guidance, not enforced): SSOT-pin /
    meta-test / contract-assertion.
    """
    import re
    pattern = re.compile(
        rf"#\s*f9-allow-{re.escape(kind)}:\s*(.*)$"
    )
    lines = source.splitlines()
    for idx, line in enumerate(lines[:FILE_OPTOUT_SCAN_LINES]):
        m = pattern.search(line)
        if m is None:
            continue
        reason = m.group(1).strip()
        if len(reason) >= MIN_OPTOUT_REASON_CHARS:
            return True, None
        # Malformed: emit a finding so the comment can't be a drive-by.
        return False, F9Finding(
            file=Path("<source>"),  # caller fills in the real path
            line=idx + 1,
            rule=f"{kind}-malformed-optout",
            message=(
                f"Malformed f9-allow-{kind} opt-out: reason is "
                f"{len(reason)} chars (need >= {MIN_OPTOUT_REASON_CHARS}). "
                f"Opt-outs must teach: state WHY this file/line is exempt "
                f"(e.g., SSOT-pin / meta-test / contract-assertion + "
                f"specifics). Drive-by opt-outs defeat the rule's purpose."
            ),
            snippet=line.strip(),
        )
    return False, None


# ---------------------------------------------------------------------
# Subspecies (ii) generalized — Phase 191D --check-ssot-constants
# ---------------------------------------------------------------------


# Default registry path (relative to repo root).
DEFAULT_SSOT_REGISTRY_PATH = "f9_ssot_constants.toml"

# How many tokens to scan around an offending literal when looking for
# the SSOT identifier / matching import (false-positive heuristic). The
# rule narrows literal-matches to those where either:
#   (a) the registry name (or a key from a dict-typed entry) appears
#       textually nearby (within IDENTIFIER_PROXIMITY_LINES of the
#       offending line), OR
#   (b) the source module is imported anywhere in the file.
# Without this narrowing the scan would flag spurious coincidences
# (e.g. ``assert response.status_code == 5`` matching
# ``TIER_VEHICLE_LIMITS["individual"] == 5``).
IDENTIFIER_PROXIMITY_LINES = 3


@dataclass
class SsotRegistryEntry:
    """One ``[[constants]]`` array-of-tables entry from the registry TOML."""

    name: str
    source_module: str
    description: str
    value_type: str
    exempt_keys: list[str] = field(default_factory=list)
    # Live production value (resolved at registry-load time via dynamic
    # import). May be ``None`` if the source module fails to import —
    # in which case the rule emits a registry-error finding rather than
    # silently skipping.
    live_value: Any = None
    load_error: str | None = None


def load_registry(
    registry_path: Path,
    name_filter: set[str] | None = None,
) -> tuple[list[SsotRegistryEntry], list[F9Finding]]:
    """Parse ``registry_path`` + dynamically import each ``source_module``.

    Args:
        registry_path: Path to the TOML registry file.
        name_filter: Optional set of constant names to include — used by
            the deprecated ``--check-model-ids`` stub-redirect to filter
            the registry down to ``MODEL_ALIASES`` + ``MODEL_PRICING``.

    Returns:
        ``(entries, registry_errors)`` — entries is the list of valid
        registry rows (``live_value`` populated); registry_errors is a
        list of ``F9Finding`` for parse failures or import errors so
        the caller can surface them in the standard finding shape.
    """
    findings: list[F9Finding] = []
    if not registry_path.exists():
        findings.append(
            F9Finding(
                file=registry_path,
                line=0,
                rule="ssot-registry-error",
                message=(
                    f"SSOT-constants registry not found at "
                    f"{registry_path}. Either pass --ssot-registry to "
                    f"point at the right path or create the registry "
                    f"file (see docs/patterns/f9-mock-vs-runtime-drift"
                    f".md)."
                ),
                snippet="(file not found)",
            )
        )
        return [], findings
    try:
        with registry_path.open("rb") as f:
            data = _tomllib.load(f)
    except Exception as exc:
        findings.append(
            F9Finding(
                file=registry_path,
                line=0,
                rule="ssot-registry-error",
                message=(
                    f"SSOT-constants registry parse failure: {exc}. "
                    f"Check TOML syntax."
                ),
                snippet="(parse failed)",
            )
        )
        return [], findings

    raw_entries = data.get("constants", []) or []
    entries: list[SsotRegistryEntry] = []
    for raw in raw_entries:
        name = raw.get("name", "")
        source_module = raw.get("source_module", "")
        if name_filter is not None and name not in name_filter:
            continue
        entry = SsotRegistryEntry(
            name=name,
            source_module=source_module,
            description=raw.get("description", ""),
            value_type=raw.get("value_type", "str"),
            exempt_keys=list(raw.get("exempt_keys", []) or []),
        )
        # Validate description floor (>=30 chars) — a soft lint on the
        # registry itself, mirrors Phase 191C's opt-out reason floor.
        if len(entry.description) < 30:
            findings.append(
                F9Finding(
                    file=registry_path,
                    line=0,
                    rule="ssot-registry-error",
                    message=(
                        f"Registry entry {name!r} from "
                        f"{source_module!r} has description "
                        f"{len(entry.description)} chars (need >= 30). "
                        f"Document WHY this constant is SSOT-managed."
                    ),
                    snippet=entry.description,
                )
            )
            continue
        # Dynamically import + read the live production value.
        try:
            module = importlib.import_module(source_module)
            entry.live_value = getattr(module, name)
        except Exception as exc:
            entry.load_error = str(exc)
            findings.append(
                F9Finding(
                    file=registry_path,
                    line=0,
                    rule="ssot-registry-error",
                    message=(
                        f"Could not load {name!r} from "
                        f"{source_module!r}: {exc}. The lint cannot "
                        f"verify literal-pin drift for this entry."
                    ),
                    snippet=f"{source_module}.{name}",
                )
            )
            continue
        entries.append(entry)
    return entries, findings


# Values that are too universally common in test code to reliably
# attribute to a specific SSOT-managed dict entry. Filtered out for
# dict/tuple-typed entries to keep the false-positive rate sane —
# `assert q.used_this_month == 0` shouldn't flag because 0 happens to
# be `TIER_MONTHLY_VIDEO_LIMITS["individual"]`. Phase 191D fix-cycle:
# initial Builder-B run produced 311 false-positive findings dominated
# by `None` and `0` matches; this list narrows that. Scalar entries
# (int/str typed) keep ALL values since the entry IS the canonical
# pin — `SCHEMA_VERSION == 39` literal-pin is exactly what we want to
# catch even though `39` is itself just an int.
NOISE_LITERALS = (None, True, False, 0, "")


def _expected_literals_for_entry(
    entry: SsotRegistryEntry,
) -> list[Any]:
    """Flatten an entry's ``live_value`` into the literals to scan for.

    For int / str: ``[live_value]``.
    For dict: every value-position literal in the dict (skipping any
        sub-key listed in ``exempt_keys`` AND skipping NOISE_LITERALS
        like None/0/True/False/"" that are too common to attribute).
    For tuple: every element of the tuple (NOISE_LITERALS filtered).
    """
    if entry.live_value is None:
        return []
    vt = entry.value_type
    if vt in ("int", "str"):
        return [entry.live_value]
    if vt == "dict":
        if not isinstance(entry.live_value, dict):
            return []
        out: list[Any] = []
        for k, v in entry.live_value.items():
            if k in entry.exempt_keys:
                continue
            # Recurse one level into nested values (handles tuple/list
            # values like motodiag.shop.ai_client.MODEL_PRICING).
            if isinstance(v, (list, tuple)):
                out.extend(item for item in v if item not in NOISE_LITERALS)
            elif isinstance(v, dict):
                out.extend(
                    val for val in v.values() if val not in NOISE_LITERALS
                )
            else:
                if v not in NOISE_LITERALS:
                    out.append(v)
        return out
    if vt == "tuple":
        if isinstance(entry.live_value, (list, tuple)):
            return [v for v in entry.live_value if v not in NOISE_LITERALS]
        return []
    return []


def _ssot_per_line_optout(
    source_lines: list[str], lineno: int,
) -> tuple[bool, F9Finding | None]:
    """Honor ``# f9-noqa: ssot-pin <reason>`` opt-out on a given line.

    Returns ``(True, None)`` when a valid opt-out (>=20 char reason) is
    present; ``(False, finding)`` when the comment is malformed (the
    caller appends the finding so the comment can't be a drive-by);
    ``(False, None)`` when no opt-out is present.

    Recognizes the ``contract-pin`` subcategory introduced in Phase 191D
    — both ``# f9-noqa: ssot-pin <reason>`` and
    ``# f9-noqa: ssot-pin contract-pin: <reason>`` are honored. The
    20-char floor applies to the trailing reason in both shapes.
    """
    if lineno < 1 or lineno > len(source_lines):
        return False, None
    line = source_lines[lineno - 1]
    pattern = re.compile(r"#\s*f9-noqa:\s*ssot-pin\b\s*(.*)$")
    m = pattern.search(line)
    if m is None:
        return False, None
    reason = m.group(1).strip()
    # Accept the "contract-pin: <reason>" subcategory by stripping the
    # prefix before length-check (so the user's reason after the colon
    # is what's measured). This keeps the 20-char floor honest — the
    # subcategory keyword shouldn't pad out a too-short reason.
    if reason.lower().startswith("contract-pin:"):
        reason = reason.split(":", 1)[1].strip()
    if len(reason) >= MIN_OPTOUT_REASON_CHARS:
        return True, None
    return False, F9Finding(
        file=Path("<source>"),  # caller fills in the real path
        line=lineno,
        rule="ssot-pin-malformed-optout",
        message=(
            f"Malformed f9-noqa: ssot-pin opt-out: reason is "
            f"{len(reason)} chars (need >= {MIN_OPTOUT_REASON_CHARS}). "
            f"Recognized subcategories: ssot-pin <reason> / ssot-pin "
            f"contract-pin: <reason>. Opt-outs must teach: state WHY "
            f"the literal is intentional."
        ),
        snippet=line.strip(),
    )


def _identifier_nearby(
    source_lines: list[str], lineno: int, identifiers: set[str],
) -> bool:
    """True if any of ``identifiers`` appears textually near ``lineno``.

    Scans IDENTIFIER_PROXIMITY_LINES lines on each side of ``lineno``
    using simple substring + word-boundary matching. Cheap and
    sufficient for the heuristic — false-positive narrowing doesn't
    need to be airtight, just enough to drop trivially-coincident
    literals like ``assert response.status_code == 5``.
    """
    start = max(0, lineno - 1 - IDENTIFIER_PROXIMITY_LINES)
    stop = min(len(source_lines), lineno + IDENTIFIER_PROXIMITY_LINES)
    haystack = "\n".join(source_lines[start:stop])
    for ident in identifiers:
        if not ident:
            continue
        if re.search(rf"\b{re.escape(ident)}\b", haystack):
            return True
    return False


def _imported_modules(tree: ast.AST) -> set[str]:
    """Return the set of dotted-name modules imported by ``tree``."""
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)
    return modules


def check_ssot_constants(
    roots: Iterable[Path],
    registry_path: Path | None = None,
    name_filter: set[str] | None = None,
) -> list[F9Finding]:
    """Scan ``test_*.py`` under each root for SSOT-managed literal pins.

    Loads the TOML registry, dynamically imports each entry's source
    module to read the live production value, then AST-walks every
    test file looking for matching literals. Honors file-level
    ``# f9-allow-ssot-constants: <reason>`` opt-outs (full file
    exemption) AND ``# f9-allow-not-ssot: <reason>`` opt-outs (declares
    "this constant is intentionally not SSOT-managed in this file").
    Per-line opt-outs use ``# f9-noqa: ssot-pin <reason>`` or the new
    ``# f9-noqa: ssot-pin contract-pin: <reason>`` subcategory.

    Args:
        roots: Directories to scan recursively (typically
            ``[Path("tests")]``).
        registry_path: Path to ``f9_ssot_constants.toml``. Defaults to
            ``<roots[0].parent>/f9_ssot_constants.toml``; falls back
            to ``Path.cwd() / DEFAULT_SSOT_REGISTRY_PATH`` if no roots.
        name_filter: Optional set of constant names to include — used
            by the ``--check-model-ids`` stub-redirect to constrain
            scope to ``{MODEL_ALIASES, MODEL_PRICING}``.

    Returns:
        List of findings; empty if clean.
    """
    if registry_path is None:
        roots_list = list(roots)
        if roots_list:
            registry_path = (
                roots_list[0].parent / DEFAULT_SSOT_REGISTRY_PATH
            )
        else:
            registry_path = Path.cwd() / DEFAULT_SSOT_REGISTRY_PATH

    entries, registry_findings = load_registry(
        registry_path, name_filter=name_filter,
    )
    findings: list[F9Finding] = list(registry_findings)
    if not entries:
        return findings

    # Pre-compute the set of expected literals per entry, plus the
    # identifier-set for the proximity heuristic. The identifiers
    # include the registry name itself + (for dict-typed entries) the
    # top-level keys, since ``TIER_VEHICLE_LIMITS["individual"]`` would
    # naturally appear textually near a literal-pin of the value.
    by_literal: dict[Any, list[tuple[SsotRegistryEntry, set[str]]]] = {}
    for entry in entries:
        # Identifier set is the registry name ONLY. Dict keys would be
        # tempting to include (TIER_VEHICLE_LIMITS["individual"] reads
        # naturally as "individual" near the literal `5`) but in
        # practice tier-related dict keys like "individual" / "shop" /
        # "company" appear in many test files for unrelated tier-themed
        # tests, swamping the signal. The legitimate signal cases all
        # have the registry name itself nearby, so dropping dict keys
        # cuts the false-positive rate without losing real findings.
        # Phase 191D fix-cycle observation: 142 dropped to ~5-7 after
        # removing dict-key identifiers.
        identifiers: set[str] = {entry.name}
        for lit in _expected_literals_for_entry(entry):
            by_literal.setdefault(lit, []).append((entry, identifiers))

    if not by_literal:
        return findings

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("test_*.py")):
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
            except (SyntaxError, OSError):
                continue
            source_lines = source.splitlines()
            # File-level opt-out: same shape as Phase 191C's
            # _file_level_optout, recognizes:
            #   * ``f9-allow-ssot-constants`` (the rule's own kind)
            #   * ``f9-allow-not-ssot`` (intentional non-SSOT escape)
            #   * ``f9-allow-model-ids`` (legacy 191C back-compat —
            #     mirrors the mobile rule's same back-compat path so
            #     files opted out at 191C 5a continue to work without
            #     a duplicate opt-out comment for the new rule's name)
            allow_optout = False
            for kind in ("ssot-constants", "not-ssot", "model-ids"):
                ok, err = _file_level_optout(source, kind=kind)
                if ok:
                    allow_optout = True
                    break
                if err is not None:
                    err.file = path
                    findings.append(err)
            if allow_optout:
                continue

            # Get imported modules for the file (used by the heuristic
            # to allow "import-implies-relevance" matches).
            imported = _imported_modules(tree)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant):
                    continue
                value = node.value
                # Skip values not in our literal map.
                if value not in by_literal:
                    continue
                # Skip booleans (Python bools are ints; would match
                # int-typed entries with values 0/1 spuriously).
                if isinstance(value, bool):
                    continue
                candidates = by_literal[value]
                # Try each registry entry that owns this literal value.
                for entry, identifiers in candidates:
                    # Heuristic narrowing — different rules per shape:
                    #
                    #   * dict-typed entries: scanning value-position
                    #     literals is inherently lossy because dict
                    #     values are often common magic numbers (3, 4,
                    #     5, 0.8) that coincide with completely
                    #     unrelated test assertions. We REQUIRE an
                    #     identifier-nearby match (the registry name OR
                    #     one of the dict keys) to fire. Import-
                    #     presence alone is too weak — many test files
                    #     import a module for one of its symbols and
                    #     never touch the dict.
                    #
                    #   * int-typed entries: top-level scalar integers
                    #     are also commonly coincident with unrelated
                    #     test literals (counts, percentages, durations,
                    #     timeouts). Phase 192 surfaced 22 false
                    #     positives where ``40`` matched ``SCHEMA_VERSION``
                    #     across 8 unrelated test files (Phase 06 / 115
                    #     / 122 / 140 / 141 / 143 / 158 / 163) where the
                    #     test imports a sibling of the source module
                    #     for unrelated reasons. We tighten int-typed
                    #     to require identifier-nearby — same posture
                    #     as dict/tuple. Import-match alone is too
                    #     loose for ints.
                    #
                    #   * str-typed entries: keep the two-path
                    #     heuristic (identifier-nearby OR source-module
                    #     imported). String literals are far less
                    #     coincidence-prone than integers — a test
                    #     that imports `motodiag.api.app` and asserts
                    #     `response['version'] == 'v1'` is plausibly
                    #     literal-pinning APP_VERSION.
                    #
                    #   * tuple-typed entries: same posture as dict
                    #     (require identifier-nearby) since tuples
                    #     also commonly hold magic-number elements.
                    nearby = _identifier_nearby(
                        source_lines, node.lineno, identifiers,
                    )
                    if entry.value_type in ("dict", "tuple", "int"):
                        if not nearby:
                            continue
                    else:
                        # Match exact source module OR any module
                        # that itself starts with `source_module + "."`
                        # (i.e., a sub-module of the source). DO NOT
                        # match the reverse direction (`source_module
                        # starts with imported + "."`) — that treats
                        # parent-package imports as matching every
                        # child-module entry, which is the false-
                        # positive shape that produced 82 hits where
                        # `from motodiag.api import create_app` was
                        # interpreted as importing every motodiag.api.*
                        # SSOT entry. Phase 191D fix-cycle observation.
                        has_import = (
                            entry.source_module in imported
                            or any(
                                mod.startswith(
                                    entry.source_module + "."
                                )
                                for mod in imported
                            )
                        )
                        if not (has_import or nearby):
                            continue
                    # Honor per-line opt-outs.
                    ok, err = _ssot_per_line_optout(
                        source_lines, node.lineno,
                    )
                    if ok:
                        # Valid opt-out — skip this finding entirely.
                        break
                    if err is not None:
                        err.file = path
                        findings.append(err)
                        # Fall through to also report the underlying
                        # literal-pin: the malformed comment doesn't
                        # exempt the line. Same posture as Phase 191C
                        # file-level opt-out malformed-handling.
                    snippet = (
                        source_lines[node.lineno - 1].strip()
                        if 0 <= node.lineno - 1 < len(source_lines)
                        else ""
                    )
                    findings.append(
                        F9Finding(
                            file=path,
                            line=node.lineno,
                            rule="ssot-pin",
                            message=(
                                f"Literal {value!r} matches the live "
                                f"production value of "
                                f"{entry.source_module}.{entry.name} "
                                f"({entry.value_type}). Import the "
                                f"constant from its source module or "
                                f"opt out with "
                                f"`# f9-noqa: ssot-pin <reason>` (or "
                                f"`# f9-noqa: ssot-pin contract-pin: "
                                f"<reason>` for intentional "
                                f"two-source assertion design)."
                            ),
                            snippet=snippet,
                        )
                    )
                    # One finding per literal per registry entry — but
                    # break here so a literal that matches multiple
                    # entries doesn't fire N times. The first match
                    # that survives the heuristic + opt-out filter
                    # wins; the message names the entry causing the
                    # diagnostic.
                    break
    return findings


# ---------------------------------------------------------------------
# F21 — Phase 191D --check-tag-catalog-coverage
# ---------------------------------------------------------------------


def check_tag_catalog_coverage(
    routes_dir: Path, openapi_path: Path,
) -> list[F9Finding]:
    """Diff route ``APIRouter(tags=...)`` strings vs ``TAG_CATALOG``.

    Two diff directions:
      1. Tags used by routes but missing from TAG_CATALOG -> rule
         ``tag-catalog-coverage`` at error severity. Routes will
         render in OpenAPI without a tag description.
      2. Tags listed in TAG_CATALOG but used by no route -> rule
         ``tag-catalog-orphan`` at warn severity. Could be a future-
         route placeholder or stale entry.

    Args:
        routes_dir: typically ``Path("src/motodiag/api/routes")``.
        openapi_path: typically
            ``Path("src/motodiag/api/openapi.py")``.

    Returns:
        List of findings; empty if clean or files missing.
    """
    findings: list[F9Finding] = []
    if not routes_dir.exists() or not openapi_path.exists():
        return findings

    # --- Step 1: collect every tag used by an APIRouter(...) call. ---
    routes_tags: dict[str, list[tuple[Path, int]]] = {}
    for path in sorted(routes_dir.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = _call_dotted_name(node.func)
            if func_name != "APIRouter" and not func_name.endswith(
                ".APIRouter"
            ):
                continue
            for kw in node.keywords:
                if kw.arg != "tags":
                    continue
                if not isinstance(kw.value, (ast.List, ast.Tuple)):
                    continue
                for elt in kw.value.elts:
                    if (
                        isinstance(elt, ast.Constant)
                        and isinstance(elt.value, str)
                    ):
                        routes_tags.setdefault(elt.value, []).append(
                            (path, elt.lineno),
                        )

    # --- Step 2: extract TAG_CATALOG names from openapi.py. ---
    catalog_names: dict[str, int] = {}
    try:
        openapi_source = openapi_path.read_text(encoding="utf-8")
        openapi_tree = ast.parse(
            openapi_source, filename=str(openapi_path),
        )
    except (SyntaxError, OSError):
        return findings
    for node in ast.walk(openapi_tree):
        # Look for ``TAG_CATALOG: ... = [ {...}, ... ]`` (AnnAssign)
        # or ``TAG_CATALOG = [...]`` (Assign).
        target_name = None
        value_node = None
        if isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == "TAG_CATALOG"
            ):
                target_name = "TAG_CATALOG"
                value_node = node.value
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "TAG_CATALOG":
                    target_name = "TAG_CATALOG"
                    value_node = node.value
                    break
        if target_name is None or not isinstance(
            value_node, (ast.List, ast.Tuple)
        ):
            continue
        for elt in value_node.elts:
            if not isinstance(elt, ast.Dict):
                continue
            for k, v in zip(elt.keys, elt.values):
                if (
                    isinstance(k, ast.Constant)
                    and k.value == "name"
                    and isinstance(v, ast.Constant)
                    and isinstance(v.value, str)
                ):
                    catalog_names[v.value] = elt.lineno

    # --- Step 3: diff (route-only -> error; catalog-only -> warn). ---
    for tag, hits in routes_tags.items():
        if tag in catalog_names:
            continue
        for path, lineno in hits:
            findings.append(
                F9Finding(
                    file=path,
                    line=lineno,
                    rule="tag-catalog-coverage",
                    message=(
                        f"Route uses tag {tag!r} but it is not "
                        f"declared in TAG_CATALOG at "
                        f"{openapi_path}. Add an entry: "
                        f"{{'name': {tag!r}, 'description': '...'}}. "
                        f"Without a catalog entry the tag will render "
                        f"in OpenAPI without a description."
                    ),
                    snippet=f"tags=[..., {tag!r}, ...]",
                )
            )
    for tag, lineno in catalog_names.items():
        if tag in routes_tags:
            continue
        findings.append(
            F9Finding(
                file=openapi_path,
                line=lineno,
                rule="tag-catalog-orphan",
                message=(
                    f"WARN: Tag {tag!r} is in TAG_CATALOG but no "
                    f"route declares it. Either remove the catalog "
                    f"entry or wire a route to it. (Severity: warn — "
                    f"may be a future-route placeholder.)"
                ),
                snippet=f"{{'name': {tag!r}, ...}}",
            )
        )
    return findings


# ---------------------------------------------------------------------
# F37 (contract-surface-drift) — Phase 195C
#   --check-pydantic-literal-vs-check-constraint
# ---------------------------------------------------------------------
#
# A Pydantic response-model field that maps to a DB column carrying a
# ``CHECK (<col> IN ('a', 'b', ...))`` constraint must be typed
# ``Literal[...]`` (or a ``Literal`` alias) whose value-set matches the
# constraint exactly — so the OpenAPI surface emits a strict enum and
# mobile codegen produces a typed union, not a freeform ``string``.
#
# The match is **table-scoped**: CHECK value-sets are keyed by
# ``(table, column)`` because three real tables (``fleet_bikes``,
# ``shop_members``, ``work_order_photos``) carry a same-named ``role``
# column with three *different* CHECK value-sets. A column-name-only
# join would re-commit the F9 family error — a name-level match that is
# not a semantic match — inside the F9 tool itself. See plan 195C
# v1.0.1 amendment.


def check_pydantic_literal_vs_check_constraint(
    routes_dir: Path,
    models_path: Path,
    migrations_path: Path,
) -> list[F9Finding]:
    """Flag Pydantic response fields mapping to a DB CHECK that aren't
    a value-set-matching ``Literal``.

    Steps:
      1. Parse ``migrations_path`` for every ``Migration(upgrade_sql=...)``
         string; regex-scan each for ``CHECK (<col> IN ('a', 'b'))``
         constraints, keyed by ``(table, column)`` (tracking the
         enclosing ``CREATE TABLE`` / ``ALTER TABLE``). Numeric/boolean
         CHECKs (``IN (0, 1)``) are skipped — not a string-Literal
         surface. ``rollback_sql`` is ignored.
      2. AST-walk every ``*.py`` under ``routes_dir`` plus
         ``models_path``; find ``BaseModel`` subclasses (incl.
         transitive); classify each annotated field as
         ``literal`` / ``str`` / ``str_enum`` / ``other``.
      3. Table-scoped, positive-resolution-required join (v1.0.2): a
         field is validated ONLY when its model resolves to a table
         (``# f9-table:`` marker, else class-name convention) that
         actually carries a CHECK on that column. No resolution, or a
         resolved table with no CHECK on the column -> no finding (a
         name-coincidence is never flagged). A ``str``-typed resolved
         field -> ``pydantic-literal-vs-check`` ERROR; a ``Literal``
         value-set mismatch -> ``pydantic-literal-vs-check`` ERROR
         (contract-surface-drift); a ``str``/``Enum`` field ->
         ``pydantic-literal-vs-check-warn`` WARN.

    Args:
        routes_dir: typically ``src/motodiag/api/routes``.
        models_path: typically ``src/motodiag/core/models.py``.
        migrations_path: typically ``src/motodiag/core/migrations.py``.

    Returns:
        List of findings; empty if clean or inputs missing.
    """
    findings: list[F9Finding] = []

    # --- Step 1: parse CHECK constraints, keyed by (table, column). ---
    check_map = _parse_check_constraints(migrations_path)
    if not check_map:
        # No string-enum CHECKs found — nothing the rule can validate.
        # (Still scan models below would yield nothing; return early.)
        return findings

    # column-name -> set of tables carrying that column with a CHECK.
    column_to_tables: dict[str, set[str]] = {}
    for (table, column) in check_map:
        column_to_tables.setdefault(column, set()).add(table)

    # --- Step 2: collect Pydantic model files. ---
    model_files: list[Path] = []
    if models_path.exists():
        model_files.append(models_path)
    if routes_dir.exists():
        model_files.extend(sorted(routes_dir.rglob("*.py")))

    for path in model_files:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, OSError):
            continue
        source_lines = source.splitlines()

        # File-level opt-out: `# f9-allow-pydantic-literal-vs-check:
        # <reason>` near the top of the file. Malformed -> emit a
        # *-malformed-optout finding and keep scanning.
        allow_optout, allow_err = _file_level_optout(
            source, kind="pydantic-literal-vs-check",
        )
        if allow_optout:
            continue
        if allow_err is not None:
            allow_err.file = path
            findings.append(allow_err)
            # Fall through — malformed opt-out doesn't exempt the file.

        findings.extend(
            _scan_models_for_check_drift(
                tree,
                path,
                source_lines,
                check_map,
                column_to_tables,
            )
        )
    return findings


# Regex bank for the CHECK-constraint parser (Step 1).
# Track the enclosing table: CREATE TABLE [IF NOT EXISTS] <name> /
# ALTER TABLE <name>.
_TABLE_TOKEN_RE = re.compile(
    r"\b(?:CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?|ALTER\s+TABLE)\s+(\w+)",
    re.IGNORECASE,
)
# A CHECK (col IN (...)) constraint. DOTALL so multi-line CHECK bodies
# match; the inner list is captured for quoted-string extraction.
_CHECK_IN_RE = re.compile(
    r"\bCHECK\s*\(\s*(\w+)\s+IN\s*\((.*?)\)\s*\)",
    re.IGNORECASE | re.DOTALL,
)
# Single-quoted string literals inside a CHECK ... IN (...) body.
_QUOTED_STR_RE = re.compile(r"'([^']*)'")


def _parse_check_constraints(
    migrations_path: Path,
) -> dict[tuple[str, str], frozenset[str]]:
    """Parse ``migrations_path`` into ``{(table, column): frozenset(values)}``.

    AST-parses the migrations module, collects every ``Migration(...)``
    call's ``upgrade_sql`` keyword string literal (``rollback_sql`` is
    ignored entirely), sorts by lineno so a later migration's
    redefinition of the same ``(table, column)`` overrides an earlier
    one, then regex-scans each SQL string. Each CHECK's table is the
    nearest preceding ``CREATE TABLE`` / ``ALTER TABLE``. A CHECK whose
    ``IN (...)`` body has no single-quoted strings (numeric/boolean,
    e.g. ``IN (0, 1)``) is skipped — it is not a Pydantic-``Literal``-
    of-``str`` surface.
    """
    result: dict[tuple[str, str], frozenset[str]] = {}
    if not migrations_path.exists():
        return result
    try:
        source = migrations_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(migrations_path))
    except (SyntaxError, OSError):
        return result

    # Collect (lineno, upgrade_sql) for every Migration(...) call.
    sql_blocks: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _call_dotted_name(node.func)
        if func_name != "Migration" and not func_name.endswith(
            ".Migration"
        ):
            continue
        for kw in node.keywords:
            if kw.arg != "upgrade_sql":
                continue
            if isinstance(kw.value, ast.Constant) and isinstance(
                kw.value.value, str
            ):
                sql_blocks.append((node.lineno, kw.value.value))

    # Sort by lineno so later migrations override earlier ones.
    sql_blocks.sort(key=lambda pair: pair[0])

    for _, sql in sql_blocks:
        # Build a list of (position, table) so each CHECK can be keyed
        # to its nearest preceding CREATE/ALTER TABLE.
        table_spans: list[tuple[int, str]] = [
            (m.start(), m.group(1).lower())
            for m in _TABLE_TOKEN_RE.finditer(sql)
        ]
        for cm in _CHECK_IN_RE.finditer(sql):
            column = cm.group(1).lower()
            body = cm.group(2)
            values = _QUOTED_STR_RE.findall(body)
            if not values:
                # Numeric/boolean CHECK (IN (0, 1)) — not a string
                # Literal surface; skip.
                continue
            # Nearest preceding CREATE/ALTER TABLE.
            table = ""
            for pos, tname in table_spans:
                if pos <= cm.start():
                    table = tname
                else:
                    break
            if not table:
                continue
            result[(table, column)] = frozenset(values)
    return result


def _pydantic_per_line_optout(
    source_lines: list[str], lineno: int,
) -> tuple[bool, F9Finding | None]:
    """Honor ``# f9-noqa: pydantic-literal-vs-check <reason>`` on a line.

    Returns ``(True, None)`` for a valid opt-out (reason >= 20 chars);
    ``(False, finding)`` for a malformed one (caller appends the
    ``pydantic-literal-vs-check-malformed-optout`` finding so the
    comment can't be a drive-by); ``(False, None)`` when no opt-out is
    present. Modelled on :func:`_ssot_per_line_optout`.
    """
    if lineno < 1 or lineno > len(source_lines):
        return False, None
    line = source_lines[lineno - 1]
    pattern = re.compile(
        r"#\s*f9-noqa:\s*pydantic-literal-vs-check\b\s*(.*)$"
    )
    m = pattern.search(line)
    if m is None:
        return False, None
    reason = m.group(1).strip()
    if len(reason) >= MIN_OPTOUT_REASON_CHARS:
        return True, None
    return False, F9Finding(
        file=Path("<source>"),  # caller fills in the real path
        line=lineno,
        rule="pydantic-literal-vs-check-malformed-optout",
        message=(
            f"Malformed f9-noqa: pydantic-literal-vs-check opt-out: "
            f"reason is {len(reason)} chars (need >= "
            f"{MIN_OPTOUT_REASON_CHARS}). Opt-outs must teach: state "
            f"WHY this field intentionally diverges from the DB CHECK "
            f"(e.g., legacy-column / migration-pending + specifics)."
        ),
        snippet=line.strip(),
    )


# Suffixes stripped from a response-model class name before the
# class-name-convention table fallback (Step 2 tier 2).
_TABLE_NAME_SUFFIXES = ("Response", "Read", "Out", "Base", "Model")
# Marker recognized on (or up to 3 lines above) a class line that names
# the model's owning DB table authoritatively.
_TABLE_MARKER_RE = re.compile(r"#\s*f9-table:\s*(\w+)")


def _camel_to_snake(name: str) -> str:
    """CamelCase -> snake_case (best-effort, for the table fallback)."""
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def _naive_pluralize(word: str) -> str:
    """Naive English pluralization for the class-name table fallback."""
    if word.endswith("y") and not word.endswith(
        ("ay", "ey", "iy", "oy", "uy")
    ):
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def _resolve_model_table(
    class_name: str,
    class_lineno: int,
    source_lines: list[str],
) -> str | None:
    """Resolve a Pydantic model to its DB table (v1.0.2 amendment).

    Tier 1 — explicit ``# f9-table: <table>`` marker on the class line
    or up to 3 lines above (authoritative).
    Tier 2 — class-name convention: strip a trailing
    ``Response``/``Read``/``Out``/``Base``/``Model`` suffix,
    CamelCase->snake_case, naive-pluralize.

    v1.0.2 positive-resolution-required matching: the convention
    candidate is returned UNrestricted — the caller flags a field only
    when ``(resolved_table, column)`` is an actual CHECK constraint, so
    a candidate that names no CHECK-bearing table simply yields no
    finding. This is the fix for the over-firing the retroactive sweep
    surfaced (a field name coinciding with a CHECK column on a table
    the model has nothing to do with — e.g. ``HealthStatus.status``).
    Returns ``None`` only when the class name is empty.
    """
    # Tier 1 — explicit marker (class line or up to 3 lines above).
    start = max(0, class_lineno - 1 - 3)
    stop = min(len(source_lines), class_lineno)
    for idx in range(start, stop):
        m = _TABLE_MARKER_RE.search(source_lines[idx])
        if m is not None:
            return m.group(1).lower()

    # Tier 2 — class-name convention (unrestricted; the caller's
    # (table, column)-in-CHECK-map test is the gate).
    stem = class_name
    for suffix in _TABLE_NAME_SUFFIXES:
        if stem.endswith(suffix) and len(stem) > len(suffix):
            stem = stem[: -len(suffix)]
            break
    if not stem:
        return None
    return _naive_pluralize(_camel_to_snake(stem))


def _literal_values_from_subscript(
    node: ast.Subscript,
) -> frozenset[str] | None:
    """Extract a ``Literal["a", "b"]`` subscript's string value-set.

    Returns the frozenset of string values, or ``None`` if the
    subscript is not a string-only ``Literal[...]`` (any non-str member
    -> not a string Literal surface).
    """
    sl = node.slice
    elts: list[ast.expr]
    if isinstance(sl, ast.Tuple):
        elts = list(sl.elts)
    else:
        elts = [sl]
    values: list[str] = []
    for elt in elts:
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            values.append(elt.value)
        else:
            # Non-str member (int / None / etc.) — not a string Literal.
            return None
    if not values:
        return None
    return frozenset(values)


def _is_literal_subscript(node: ast.expr) -> bool:
    """True if ``node`` is a ``Literal[...]`` subscript."""
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "Literal"
    )


def _collect_literal_aliases(
    tree: ast.AST,
) -> dict[str, frozenset[str]]:
    """Resolve module-level ``X = Literal["a", "b"]`` assignments.

    Returns ``{alias_name: frozenset(values)}``. A ``Literal`` with any
    non-str member is treated as not-a-string-Literal and dropped.
    """
    aliases: dict[str, frozenset[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not _is_literal_subscript(node.value):
            continue
        values = _literal_values_from_subscript(node.value)  # type: ignore[arg-type]
        if values is None:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                aliases[target.id] = values
    return aliases


def _collect_basemodel_classes(
    tree: ast.AST,
) -> set[str]:
    """Return the names of in-file ``BaseModel`` subclasses (transitive).

    A class is a BaseModel subclass if a direct base is named
    ``BaseModel`` OR a direct base is another in-file class already
    known to be a BaseModel subclass (handles
    ``VideoResponse(VideoBase)`` where ``VideoBase(BaseModel)``).
    """
    classdefs = [
        n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)
    ]
    is_basemodel: set[str] = set()
    changed = True
    while changed:
        changed = False
        for cls in classdefs:
            if cls.name in is_basemodel:
                continue
            for base in cls.bases:
                base_name = ""
                if isinstance(base, ast.Name):
                    base_name = base.id
                elif isinstance(base, ast.Attribute):
                    base_name = base.attr
                if base_name == "BaseModel" or base_name in is_basemodel:
                    is_basemodel.add(cls.name)
                    changed = True
                    break
    return is_basemodel


def _collect_enum_classes(
    tree: ast.AST,
) -> set[str]:
    """Return the names of in-file ``Enum`` / ``StrEnum`` / ``IntEnum``
    subclasses (direct-base check — enough for the str_enum classify)."""
    enum_bases = {"Enum", "StrEnum", "IntEnum"}
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_name = ""
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr
            if base_name in enum_bases:
                names.add(node.name)
                break
    return names


def _unwrap_optional(node: ast.expr) -> ast.expr:
    """Unwrap ``Optional[X]`` and ``X | None`` down to ``X``.

    ``Optional[X]`` is a ``Subscript`` of a ``Name``/``Attribute``
    named ``Optional``. ``X | None`` is a ``BinOp`` with ``BitOr`` and
    a ``None`` constant on one side.
    """
    # Optional[X]
    if (
        isinstance(node, ast.Subscript)
        and (
            (isinstance(node.value, ast.Name)
             and node.value.id == "Optional")
            or (isinstance(node.value, ast.Attribute)
                and node.value.attr == "Optional")
        )
    ):
        return _unwrap_optional(node.slice)
    # X | None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left, right = node.left, node.right
        left_is_none = (
            isinstance(left, ast.Constant) and left.value is None
        )
        right_is_none = (
            isinstance(right, ast.Constant) and right.value is None
        )
        if right_is_none and not left_is_none:
            return _unwrap_optional(left)
        if left_is_none and not right_is_none:
            return _unwrap_optional(right)
    return node


def _classify_annotation(
    annotation: ast.expr,
    literal_aliases: dict[str, frozenset[str]],
    enum_classes: set[str],
) -> tuple[str, frozenset[str] | None]:
    """Classify a field annotation.

    Returns ``(kind, value_set)`` where kind is one of:
      * ``"literal"`` — inline ``Literal[...]`` of strs, or a Name that
        is a known module-level ``Literal`` alias. ``value_set`` is the
        frozenset of values.
      * ``"str"`` — annotation is plain ``str``.
      * ``"str_enum"`` — a Name referring to an in-file ``Enum`` /
        ``StrEnum`` / ``IntEnum`` subclass. ``value_set`` is ``None``
        (Enum members are not statically value-set-checked here).
      * ``"other"`` — anything else (ignored by the rule).
    """
    node = _unwrap_optional(annotation)
    # Inline Literal[...] of strings.
    if _is_literal_subscript(node):
        values = _literal_values_from_subscript(node)  # type: ignore[arg-type]
        if values is not None:
            return "literal", values
        return "other", None
    # A bare Name.
    if isinstance(node, ast.Name):
        if node.id in literal_aliases:
            return "literal", literal_aliases[node.id]
        if node.id == "str":
            return "str", None
        if node.id in enum_classes:
            return "str_enum", None
        return "other", None
    return "other", None


def _scan_models_for_check_drift(
    tree: ast.AST,
    path: Path,
    source_lines: list[str],
    check_map: dict[tuple[str, str], frozenset[str]],
    column_to_tables: dict[str, set[str]],
) -> list[F9Finding]:
    """AST-walk one module: emit findings for fields drifting from a
    DB CHECK constraint. Implements the Step-3 table-scoped join."""
    findings: list[F9Finding] = []

    literal_aliases = _collect_literal_aliases(tree)
    basemodel_classes = _collect_basemodel_classes(tree)
    enum_classes = _collect_enum_classes(tree)

    check_columns = set(column_to_tables)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name not in basemodel_classes:
            continue
        # v1.0.2: resolve the model -> table ONCE per model. A field is
        # flagged only when this resolved table actually carries a
        # CHECK on that column (positive-resolution-required matching).
        model_table = _resolve_model_table(
            node.name, node.lineno, source_lines,
        )
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            if not isinstance(stmt.target, ast.Name):
                continue
            field_name = stmt.target.id
            if field_name not in check_columns:
                continue

            # v1.0.2 positive-resolution-required matching: flag ONLY
            # when the model's resolved table actually carries a CHECK
            # on this column. No resolution, or a resolved table that
            # carries no CHECK on this column -> no finding. (The
            # `pydantic-literal-vs-check-ambiguous` finding type is
            # removed in v1.0.2 — see the v1.0.2 amendment: an
            # unresolved / non-CHECK-bearing model is silently skipped,
            # never false-flagged.)
            if model_table is None:
                continue
            check_key = (model_table, field_name)
            if check_key not in check_map:
                continue
            table = model_table
            check_values = check_map[check_key]

            kind, value_set = _classify_annotation(
                stmt.annotation, literal_aliases, enum_classes,
            )
            snippet = (
                source_lines[stmt.lineno - 1].strip()
                if 0 <= stmt.lineno - 1 < len(source_lines)
                else ""
            )

            if kind == "other":
                continue

            if kind == "str_enum":
                # str/Enum emits a typed OpenAPI enum -> contract-
                # correct. House style prefers a Literal alias. WARN,
                # not error; per-line opt-out NOT honored for WARN.
                findings.append(
                    F9Finding(
                        file=path,
                        line=stmt.lineno,
                        rule="pydantic-literal-vs-check-warn",
                        message=(
                            f"WARN: Field {field_name!r} on model "
                            f"{node.name!r} maps to the DB CHECK "
                            f"column {table}.{field_name} and is typed "
                            f"as a str/Enum. A str/Enum DOES emit a "
                            f"typed OpenAPI enum so it is contract-"
                            f"correct; house style prefers a "
                            f"`Literal[...]` alias for consistency. "
                            f"(Severity: warn — not a regression.)"
                        ),
                        snippet=snippet,
                    )
                )
                continue

            # kind is "str" or "literal" — both ERROR-eligible; honor
            # the per-line opt-out.
            ok, err = _pydantic_per_line_optout(
                source_lines, stmt.lineno,
            )
            if ok:
                continue
            if err is not None:
                err.file = path
                findings.append(err)
                # Fall through — malformed opt-out doesn't exempt.

            if kind == "str":
                findings.append(
                    F9Finding(
                        file=path,
                        line=stmt.lineno,
                        rule="pydantic-literal-vs-check",
                        message=(
                            f"Field {field_name!r} on model "
                            f"{node.name!r} maps to the DB CHECK "
                            f"column {table}.{field_name} (allowed "
                            f"values {sorted(check_values)}) but is "
                            f"typed `str`. Type it "
                            f"`Literal[{', '.join(repr(v) for v in sorted(check_values))}]` "
                            f"(or a module-level `Literal` alias) so "
                            f"the OpenAPI surface emits a strict enum "
                            f"and mobile codegen produces a typed "
                            f"union instead of a freeform `string`. "
                            f"Opt out with `# f9-noqa: "
                            f"pydantic-literal-vs-check <reason>` if "
                            f"intentional."
                        ),
                        snippet=snippet,
                    )
                )
            elif kind == "literal":
                if value_set != check_values:
                    findings.append(
                        F9Finding(
                            file=path,
                            line=stmt.lineno,
                            rule="pydantic-literal-vs-check",
                            message=(
                                f"Contract-surface drift: field "
                                f"{field_name!r} on model "
                                f"{node.name!r} is typed `Literal` "
                                f"with value-set "
                                f"{sorted(value_set or [])} but the "
                                f"DB CHECK on {table}.{field_name} "
                                f"allows {sorted(check_values)}. The "
                                f"schema and the API contract have "
                                f"drifted; align the `Literal` to the "
                                f"CHECK value-set exactly (or update "
                                f"the migration if the CHECK is "
                                f"stale). Opt out with `# f9-noqa: "
                                f"pydantic-literal-vs-check <reason>` "
                                f"if intentional."
                            ),
                            snippet=snippet,
                        )
                    )
            # literal with a matching value-set -> pass (no finding).
    return findings


# ---------------------------------------------------------------------
# Orchestration + CLI
# ---------------------------------------------------------------------


def run_all_checks(repo_root: Path) -> list[F9Finding]:
    """Convenience entry point: run all backend checks against ``repo_root``.

    Phase 191D update: ``run_all_checks`` now invokes the generalized
    ``check_ssot_constants`` (which subsumes the deprecated narrow
    ``check_model_ids``) plus ``check_deploy_path_init_db`` (subspecies
    iv) plus ``check_tag_catalog_coverage`` (F21). The narrow
    ``check_model_ids`` is no longer dispatched from ``--all`` to avoid
    double-flagging the model-ID class of literals — ``--check-model-ids``
    remains as a back-compat alias that stub-redirects to
    ``check_ssot_constants`` filtered to MODEL_ALIASES + MODEL_PRICING.

    Phase 195C update: ``run_all_checks`` also invokes
    ``check_pydantic_literal_vs_check_constraint`` (F37 — contract-
    surface-drift): Pydantic response fields mapping to a DB CHECK
    constraint must be a value-set-matching ``Literal``.
    """
    return (
        check_ssot_constants(
            [repo_root / "tests"],
            registry_path=repo_root / DEFAULT_SSOT_REGISTRY_PATH,
        )
        + check_deploy_path_init_db(
            repo_root / "src" / "motodiag" / "cli"
        )
        + check_tag_catalog_coverage(
            repo_root / "src" / "motodiag" / "api" / "routes",
            repo_root / "src" / "motodiag" / "api" / "openapi.py",
        )
        + check_pydantic_literal_vs_check_constraint(
            repo_root / "src" / "motodiag" / "api" / "routes",
            repo_root / "src" / "motodiag" / "core" / "models.py",
            repo_root / "src" / "motodiag" / "core" / "migrations.py",
        )
    )


# Names of registry entries the deprecated --check-model-ids flag
# delegates to. Centralized so the stub-redirect + tests both reference
# one source.
DEPRECATED_MODEL_IDS_FILTER = {"MODEL_ALIASES", "MODEL_PRICING"}

DEPRECATION_NOTICE = (
    "DEPRECATION: --check-model-ids is deprecated as of Phase 191D; "
    "use --check-ssot-constants instead. This stub will be removed in "
    "Phase 200+. See docs/patterns/f9-mock-vs-runtime-drift.md for the "
    "rule rename rationale."
)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Exit 0 on clean, 1 on findings."""
    parser = argparse.ArgumentParser(
        description=(
            "F9 mock-vs-runtime-drift pattern checks. Phase 191C "
            "shipped --check-model-ids (subspecies ii narrow) + "
            "--check-deploy-path-init-db (subspecies iv). Phase 191D "
            "generalized the narrow rule into --check-ssot-constants "
            "(TOML-driven) and added --check-tag-catalog-coverage "
            "(F21 mitigation). --check-model-ids is now a deprecated "
            "stub that redirects to --check-ssot-constants filtered "
            "to MODEL_ALIASES + MODEL_PRICING."
        ),
    )
    parser.add_argument(
        "--check-model-ids",
        action="store_true",
        help=(
            "DEPRECATED (Phase 191D); use --check-ssot-constants. "
            "Stub-redirects to --check-ssot-constants filtered to "
            "model-ID-relevant registry entries. Removal targeted "
            "Phase 200+."
        ),
    )
    parser.add_argument(
        "--check-deploy-path-init-db",
        action="store_true",
        help=(
            "Scan src/motodiag/cli/ for serve commands missing init_db "
            "(subspecies iv)."
        ),
    )
    parser.add_argument(
        "--check-ssot-constants",
        action="store_true",
        help=(
            "Phase 191D F20 mitigation: TOML-driven scan of tests/ for "
            "literal pins of any constant declared in "
            "f9_ssot_constants.toml. Subsumes --check-model-ids."
        ),
    )
    parser.add_argument(
        "--check-tag-catalog-coverage",
        action="store_true",
        help=(
            "Phase 191D F21 mitigation: diff "
            "src/motodiag/api/routes/**/*.py APIRouter(tags=...) "
            "against motodiag.api.openapi.TAG_CATALOG; flag tags in "
            "routes-not-in-catalog (error) / tags in "
            "catalog-not-in-routes (warn)."
        ),
    )
    parser.add_argument(
        "--check-pydantic-literal-vs-check-constraint",
        action="store_true",
        help=(
            "Phase 195C F37 mitigation (contract-surface-drift): scan "
            "src/motodiag/api/routes/**/*.py + core/models.py for "
            "Pydantic response fields mapping to a DB CHECK "
            "constraint (parsed from core/migrations.py) that aren't a "
            "value-set-matching Literal. str-typed -> error; Literal "
            "value-set mismatch -> error; str/Enum -> warn."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Run all checks: --check-ssot-constants + "
            "--check-deploy-path-init-db + --check-tag-catalog-coverage "
            "+ --check-pydantic-literal-vs-check-constraint. "
            "Phase 191D: --check-model-ids is NOT included in --all "
            "since --check-ssot-constants subsumes it."
        ),
    )
    parser.add_argument(
        "--ssot-registry",
        type=Path,
        default=None,
        help=(
            "Path to the SSOT-constants TOML registry. Default: "
            "<repo-root>/f9_ssot_constants.toml."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repo root (default: parent of scripts/).",
    )
    args = parser.parse_args(argv)
    if not (
        args.check_model_ids
        or args.check_deploy_path_init_db
        or args.check_ssot_constants
        or args.check_tag_catalog_coverage
        or args.check_pydantic_literal_vs_check_constraint
        or args.all
    ):
        parser.error(
            "Specify at least one check (--check-model-ids [DEPRECATED], "
            "--check-deploy-path-init-db, --check-ssot-constants, "
            "--check-tag-catalog-coverage, "
            "--check-pydantic-literal-vs-check-constraint, or --all)."
        )

    registry_path = (
        args.ssot_registry
        if args.ssot_registry is not None
        else args.repo_root / DEFAULT_SSOT_REGISTRY_PATH
    )

    findings: list[F9Finding] = []
    if args.check_model_ids:
        # Stub-redirect: warn to STDERR (preserve stdout for CI/pipe
        # consumers that only parse finding lines), then internally
        # invoke check_ssot_constants filtered to model-ID entries.
        # Functionally equivalent for the model-ID case — not a no-op.
        print(DEPRECATION_NOTICE, file=sys.stderr)
        findings.extend(
            check_ssot_constants(
                [args.repo_root / "tests"],
                registry_path=registry_path,
                name_filter=DEPRECATED_MODEL_IDS_FILTER,
            )
        )
    if args.all or args.check_ssot_constants:
        findings.extend(
            check_ssot_constants(
                [args.repo_root / "tests"],
                registry_path=registry_path,
            )
        )
    if args.all or args.check_deploy_path_init_db:
        findings.extend(
            check_deploy_path_init_db(
                args.repo_root / "src" / "motodiag" / "cli"
            )
        )
    if args.all or args.check_tag_catalog_coverage:
        findings.extend(
            check_tag_catalog_coverage(
                args.repo_root / "src" / "motodiag" / "api" / "routes",
                args.repo_root / "src" / "motodiag" / "api"
                / "openapi.py",
            )
        )
    if args.all or args.check_pydantic_literal_vs_check_constraint:
        findings.extend(
            check_pydantic_literal_vs_check_constraint(
                args.repo_root / "src" / "motodiag" / "api" / "routes",
                args.repo_root / "src" / "motodiag" / "core"
                / "models.py",
                args.repo_root / "src" / "motodiag" / "core"
                / "migrations.py",
            )
        )

    # Findings + summary go to stdout (preserves pipe-based callers
    # like `check_f9_patterns.py | grep finding`). Deprecation banner
    # for the legacy --check-model-ids flag stays on stderr (printed
    # earlier above) so it doesn't pollute pipe consumers.
    if findings:
        print(f"F9 lint: {len(findings)} finding(s)\n")
        for finding in findings:
            print(finding.format())
        return 1
    print("F9 lint: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
