"""CLI entrypoint: ``motodiag serve`` — launch the HTTP API (Phase 175)."""

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
    def serve_cmd(
        host: Optional[str],
        port: Optional[int],
        reload: bool,
        log_level: Optional[str],
        workers: int,
    ) -> None:
        """Launch the MotoDiag HTTP API via uvicorn.

        Zero-config startup: ``motodiag serve`` reads MOTODIAG_API_*
        env vars or falls back to Settings defaults
        (127.0.0.1:8080 with dev CORS origins).
        """
        try:
            import uvicorn
        except ImportError as e:
            raise click.ClickException(
                "uvicorn not installed; run "
                "`pip install 'motodiag[api]'` first"
            ) from e

        from motodiag.core.config import get_settings
        settings = get_settings()
        effective_host = host or settings.api_host
        effective_port = port if port is not None else settings.api_port
        effective_level = (log_level or settings.api_log_level).lower()

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
