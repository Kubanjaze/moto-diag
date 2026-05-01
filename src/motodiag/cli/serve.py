"""CLI entrypoint: ``motodiag serve`` — launch the HTTP API (Phase 175).

Phase 191B fix-cycle (2026-04-30): apply pending migrations at startup
before launching uvicorn. Latent since Phase 175 — neither
``serve_cmd`` nor ``create_app()`` was calling ``init_db()``, so
``motodiag serve`` against an existing-but-out-of-date DB would
silently run on the old schema. CLI invocations + pytest both call
``init_db()`` implicitly so the gap was never surfaced — until Phase
191B's SCHEMA_VERSION 38 → 39 bump deployed against a v38 DB and
the architect-gate /v1/version still reported schema_version=38.

Same failure family as Phase 187 latent + Phase 188 surfaced (Content-
Type strip on POST) and Phase 175 latent + Phase 190 surfaced (DTC 404
ProblemDetail shape mismatch): a code path that "works in tests"
because the tests' setup happens to compensate for the production
gap.

Fix lives in ``serve_cmd`` rather than ``create_app()`` to preserve
Phase 175's choice that the app factory be side-effect-free for tests.
"""

from __future__ import annotations

from typing import Optional

import click


def register_serve(cli_group: click.Group) -> None:
    """Attach the ``serve`` command to the top-level CLI."""

    @cli_group.command("serve")
    @click.option(
        "--host", default=None,
        help="Bind host (default from MOTODIAG_API_HOST / 127.0.0.1).",
    )
    @click.option(
        "--port", type=int, default=None,
        help="Bind port (default from MOTODIAG_API_PORT / 8080).",
    )
    @click.option(
        "--reload", is_flag=True, default=False,
        help="Enable uvicorn's autoreload (development only).",
    )
    @click.option(
        "--log-level", default=None,
        help="Uvicorn log level (default from "
             "MOTODIAG_API_LOG_LEVEL / INFO).",
    )
    @click.option(
        "--workers", type=int, default=1,
        help="Number of uvicorn workers (default 1).",
    )
    @click.option(
        "--skip-migrations", is_flag=True, default=False,
        help="Skip the startup migration apply step. Use only if a "
             "migration has been verified out-of-band (e.g., as part "
             "of a deploy script). Default behavior is to apply "
             "pending migrations at startup so the schema matches the "
             "code's SCHEMA_VERSION constant.",
    )
    def serve_cmd(
        host: Optional[str],
        port: Optional[int],
        reload: bool,
        log_level: Optional[str],
        workers: int,
        skip_migrations: bool,
    ) -> None:
        """Launch the MotoDiag HTTP API via uvicorn.

        Zero-config startup: ``motodiag serve`` reads MOTODIAG_API_*
        env vars or falls back to Settings defaults
        (127.0.0.1:8080 with dev CORS origins).

        Applies pending schema migrations at startup (Phase 191B
        fix-cycle). Pass ``--skip-migrations`` to opt out (e.g., for
        deploy scripts that run migrations out-of-band).
        """
        try:
            import uvicorn
        except ImportError as e:
            raise click.ClickException(
                "uvicorn not installed; run "
                "`pip install 'motodiag[api]'` first"
            ) from e

        from motodiag.core.config import get_settings
        from motodiag.core.database import SCHEMA_VERSION, init_db
        from motodiag.core.migrations import get_current_version

        settings = get_settings()
        effective_host = host or settings.api_host
        effective_port = port if port is not None else settings.api_port
        effective_level = (log_level or settings.api_log_level).lower()

        # === Phase 191B fix-cycle: apply pending migrations at startup ===
        if skip_migrations:
            try:
                current = get_current_version(settings.db_path)
            except Exception:
                current = None
            click.echo(
                f"Skipping migration apply (--skip-migrations); "
                f"DB schema_version={current}, code SCHEMA_VERSION={SCHEMA_VERSION}"
            )
            if current is not None and current != SCHEMA_VERSION:
                click.echo(
                    f"WARNING: DB schema_version ({current}) does not match "
                    f"code SCHEMA_VERSION ({SCHEMA_VERSION}). API may fail.",
                    err=True,
                )
        else:
            before = None
            try:
                before = get_current_version(settings.db_path)
            except Exception:
                # Fresh DB; init_db will create it.
                before = 0
            init_db(settings.db_path, apply_migrations=True)
            after = get_current_version(settings.db_path)
            if before != after:
                click.echo(
                    f"Applied migrations: schema_version {before} → {after} "
                    f"(code SCHEMA_VERSION={SCHEMA_VERSION})"
                )
            else:
                click.echo(
                    f"DB schema up to date at version {after} "
                    f"(code SCHEMA_VERSION={SCHEMA_VERSION})"
                )

        click.echo(
            f"MotoDiag API starting on "
            f"http://{effective_host}:{effective_port} "
            f"(log={effective_level}, reload={reload}, "
            f"workers={workers})"
        )

        uvicorn.run(
            "motodiag.api:create_app",
            host=effective_host,
            port=effective_port,
            reload=reload,
            log_level=effective_level,
            workers=workers if not reload else 1,
            factory=True,
        )
