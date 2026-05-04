"""F9 mock-vs-runtime-drift pattern checks (Phase 191C).

Standalone CLI invoked from .pre-commit-config.yaml + manually.
Two checks:
  --check-model-ids: subspecies (ii) — hardcoded model IDs in test files
  --check-deploy-path-init-db: subspecies (iv) — CLI commands launching
      uvicorn/serve without init_db() call

Importable as a module: ``from check_f9_patterns import (
    check_model_ids, check_deploy_path_init_db, F9Finding, run_all_checks
)``

Pattern doc: ``docs/patterns/f9-mock-vs-runtime-drift.md``
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
# Orchestration + CLI
# ---------------------------------------------------------------------


def run_all_checks(repo_root: Path) -> list[F9Finding]:
    """Convenience entry point: run both checks against ``repo_root``."""
    return check_model_ids([repo_root / "tests"]) + check_deploy_path_init_db(
        repo_root / "src" / "motodiag" / "cli"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Exit 0 on clean, 1 on findings."""
    parser = argparse.ArgumentParser(
        description="F9 mock-vs-runtime-drift pattern checks.",
    )
    parser.add_argument(
        "--check-model-ids",
        action="store_true",
        help="Scan tests/ for hardcoded model ID literals (subspecies ii).",
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
        "--all",
        action="store_true",
        help="Run all checks.",
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
        or args.all
    ):
        parser.error(
            "Specify at least one check (--check-model-ids, "
            "--check-deploy-path-init-db, or --all)."
        )

    findings: list[F9Finding] = []
    if args.all or args.check_model_ids:
        findings.extend(check_model_ids([args.repo_root / "tests"]))
    if args.all or args.check_deploy_path_init_db:
        findings.extend(
            check_deploy_path_init_db(
                args.repo_root / "src" / "motodiag" / "cli"
            )
        )

    if findings:
        print(f"F9 lint: {len(findings)} finding(s)\n", file=sys.stderr)
        for finding in findings:
            print(finding.format(), file=sys.stderr)
        return 1
    print("F9 lint: clean", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
