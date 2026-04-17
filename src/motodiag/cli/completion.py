"""Shell completion + dynamic completers.

Phase 130: wraps Click's built-in completion infrastructure with a
user-friendly ``motodiag completion <shell>`` command and three dynamic
completer callbacks that turn ``--bike <TAB>``, ``code <TAB>``, and session-id
<TAB> into live suggestions sourced from the local SQLite DB.

Design goals
------------
1. **Zero crashes on fresh installs.** Every completer wraps its DB access in
   a try/except and returns ``[]`` on any error. If ``motodiag.db`` doesn't
   exist yet, the ``dtc_codes`` table was never populated, or the DB file is
   on a flaky network mount — tab-completion silently returns no suggestions
   rather than killing the mechanic's shell session.
2. **Bounded latency.** Each completer has a ``LIMIT 20`` (or post-filter
   equivalent). Tab-press should feel instant; the user never waits on more
   than 20 rows of SQLite fetch work.
3. **Uses Click's public completion API.** ``click.shell_completion`` has been
   stable since Click 8.1. The wrapper falls back to a documented manual-
   install stub if the API shape changes in a future Click version.

Wired from ``cli/main.py`` via ``register_completion(cli)``. The three
dynamic completers are imported directly by ``cli/diagnose.py`` and
``cli/code.py`` and attached to ``shell_complete=...`` on the relevant
options/arguments.
"""

from __future__ import annotations

import click
from click.shell_completion import CompletionItem


# Maximum number of suggestions returned per tab-press.
# Tab-completion UIs typically page beyond this; keeping the cap small
# preserves responsiveness on large garages / DTC tables.
_MAX_SUGGESTIONS = 20

# Maximum rows fetched from diagnostic_sessions before prefix-filtering.
# 50 covers the "recent sessions" window without dumping an entire busy
# shop's history into a completion shortlist.
_SESSION_FETCH_LIMIT = 50


# --- Dynamic completer callbacks ---


def _safe_get_db_path() -> str | None:
    """Resolve the current DB path from settings, defensively.

    Returns ``None`` if settings cannot be read (ImportError during
    package load, misconfigured environment). Completers treat ``None``
    as "no suggestions available".
    """
    try:
        from motodiag.core.config import get_settings

        return get_settings().db_path
    except Exception:
        return None


def complete_bike_slug(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> list[CompletionItem]:
    """Suggest garage bike slugs matching the ``incomplete`` prefix.

    Slug format mirrors ``_resolve_bike_slug`` in ``cli/diagnose.py``:
    ``{model-lowercased-with-spaces-as-hyphens}-{year}``. Case-insensitive
    prefix match.

    Defensive: any DB error returns ``[]`` so tab-completion never crashes
    the user's shell.
    """
    db_path = _safe_get_db_path()
    if db_path is None:
        return []

    try:
        from motodiag.core.database import get_connection

        prefix = (incomplete or "").lower()
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT model, year FROM vehicles ORDER BY created_at, id"
            ).fetchall()
    except Exception:
        return []

    out: list[CompletionItem] = []
    for row in rows:
        try:
            model = (row["model"] or "").lower().replace(" ", "-")
            year = row["year"]
            if not model or year is None:
                continue
            slug = f"{model}-{year}"
        except Exception:
            continue
        if slug.startswith(prefix):
            out.append(CompletionItem(slug))
            if len(out) >= _MAX_SUGGESTIONS:
                break
    return out


def complete_dtc_code(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> list[CompletionItem]:
    """Suggest known DTC codes matching the ``incomplete`` prefix.

    Uses a ``LIKE`` query on the ``dtc_codes`` table. Codes are stored
    uppercase by convention, so ``incomplete`` is force-uppercased before
    the comparison — mechanics who type ``p01<TAB>`` still get ``P0115`` /
    ``P0562`` back.

    Defensive: any DB error returns ``[]``.
    """
    db_path = _safe_get_db_path()
    if db_path is None:
        return []

    try:
        from motodiag.core.database import get_connection

        prefix = (incomplete or "").upper()
        like = f"{prefix}%"
        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT code FROM dtc_codes "
                "WHERE code LIKE ? ORDER BY code LIMIT ?",
                (like, _MAX_SUGGESTIONS),
            ).fetchall()
    except Exception:
        return []

    return [
        CompletionItem(row["code"])
        for row in rows
        if row["code"] is not None
    ]


def complete_session_id(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> list[CompletionItem]:
    """Suggest recent session IDs matching the ``incomplete`` prefix.

    Fetches the most recent 50 sessions by ``created_at DESC`` and returns
    up to 20 whose stringified ID starts with ``incomplete``. Prefix-match
    on stringified ints is more useful than numeric-range filtering for
    tab-completion — ``motodiag diagnose show 4<TAB>`` should surface
    ``4``, ``40``, ``42``, ``47`` etc.

    Defensive: any DB error returns ``[]``.
    """
    db_path = _safe_get_db_path()
    if db_path is None:
        return []

    try:
        from motodiag.core.database import get_connection

        with get_connection(db_path) as conn:
            rows = conn.execute(
                "SELECT id FROM diagnostic_sessions "
                "ORDER BY created_at DESC LIMIT ?",
                (_SESSION_FETCH_LIMIT,),
            ).fetchall()
    except Exception:
        return []

    prefix = incomplete or ""
    out: list[CompletionItem] = []
    for row in rows:
        sid = row["id"]
        if sid is None:
            continue
        s = str(sid)
        if s.startswith(prefix):
            out.append(CompletionItem(s))
            if len(out) >= _MAX_SUGGESTIONS:
                break
    return out


# --- `motodiag completion <shell>` command ---


# The env-var name Click uses to recognize a completion-source request.
# Derived from the top-level command name (``motodiag``) per Click's
# convention: ``_{UPPER_PROG}_COMPLETE``.
_COMPLETE_VAR = "_MOTODIAG_COMPLETE"

# User-facing install hints baked into each printed script so mechanics
# don't have to dig through docs when setting up tab-completion.
_INSTALL_HINTS = {
    "bash": (
        "# MotoDiag bash completion\n"
        "# Install (persistent):\n"
        "#   motodiag completion bash > "
        "~/.local/share/bash-completion/completions/motodiag\n"
        "# Install (current shell only):\n"
        "#   eval \"$(motodiag completion bash)\"\n"
    ),
    "zsh": (
        "# MotoDiag zsh completion\n"
        "# Install (persistent):\n"
        "#   motodiag completion zsh > \"${fpath[1]}/_motodiag\"\n"
        "#   # then restart zsh or run 'autoload -U compinit && compinit'\n"
        "# Install (current shell only):\n"
        "#   eval \"$(motodiag completion zsh)\"\n"
    ),
    "fish": (
        "# MotoDiag fish completion\n"
        "# Install (persistent):\n"
        "#   motodiag completion fish > "
        "~/.config/fish/completions/motodiag.fish\n"
        "# Install (current shell only):\n"
        "#   motodiag completion fish | source\n"
    ),
}


def _render_completion_script(cli_group: click.Group, shell: str) -> str:
    """Return the full completion script (header + Click-generated body).

    Falls back to a manual-install stub if Click's
    ``shell_completion.get_completion_class`` is unavailable or errors —
    keeps ``motodiag completion <shell>`` useful even if Click's API
    drifts in a future major version.
    """
    header = _INSTALL_HINTS.get(shell, f"# MotoDiag {shell} completion\n")
    try:
        cls = click.shell_completion.get_completion_class(shell)
        if cls is None:
            raise RuntimeError(f"no completion class for shell {shell!r}")
        # Click's completion class constructor: cls(cli, ctx_args, prog_name, complete_var)
        instance = cls(cli_group, {}, "motodiag", _COMPLETE_VAR)
        body = instance.source()
    except (ImportError, AttributeError, RuntimeError, Exception) as exc:  # noqa: BLE001
        # Absolute worst case — print a documented stub so the user isn't
        # left with silent output. We include the error so they can file a
        # report if this ever fires.
        body = (
            f"# Click completion generation failed: {exc}\n"
            f"# Manually enable completion with:\n"
            f"#   {_COMPLETE_VAR}={shell}_source motodiag\n"
        )
    return header + body


def register_completion(cli_group: click.Group) -> None:
    """Attach the ``completion`` subgroup (bash / zsh / fish) to the top-level CLI.

    Called from ``cli/main.py`` after the other ``register_*`` calls. Keeping
    the wiring explicit mirrors the Phase 123/124/125/128 pattern and makes
    the ordering auditable (completion depends on nothing; no ordering
    constraints).
    """

    @cli_group.group("completion")
    def completion() -> None:
        """Print shell completion scripts (bash, zsh, fish).

        Dynamic tab-completion for --bike, DTC codes, and session IDs is
        wired on individual commands; once you source the script for your
        shell, those completions work automatically.
        """

    @completion.command("bash")
    def completion_bash() -> None:
        """Print the bash completion script to stdout.

        Pipe to ``~/.local/share/bash-completion/completions/motodiag`` for
        a persistent install, or ``eval`` it for the current shell only.
        """
        click.echo(_render_completion_script(cli_group, "bash"))

    @completion.command("zsh")
    def completion_zsh() -> None:
        """Print the zsh completion script to stdout.

        Pipe to a file on your ``$fpath`` (e.g.
        ``${fpath[1]}/_motodiag``) and run ``compinit`` to install
        persistently.
        """
        click.echo(_render_completion_script(cli_group, "zsh"))

    @completion.command("fish")
    def completion_fish() -> None:
        """Print the fish completion script to stdout.

        Pipe to ``~/.config/fish/completions/motodiag.fish`` or ``source``
        the output directly in your current session.
        """
        click.echo(_render_completion_script(cli_group, "fish"))


__all__ = [
    "complete_bike_slug",
    "complete_dtc_code",
    "complete_session_id",
    "register_completion",
]
