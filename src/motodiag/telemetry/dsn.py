"""A Sentry DSN, read into its parts (Phase 343).

``https://<public key>@<host>[:port]/[<path>/]<project id>``. The key is
what lets a sender post to the project, so nothing this module prints
carries it: a refusal names only the part that is missing, and a parsed
``Dsn``'s ``repr`` and ``str`` show the host and the project id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlsplit

from motodiag import __version__

CLIENT_NAME = f"motodiag/{__version__}"


class DsnError(ValueError):
    """A DSN that cannot be used. The message never holds the DSN's text."""


@dataclass(frozen=True)
class Dsn:
    scheme: str
    host: str
    port: int | None
    public_key: str = field(repr=False)
    project_id: str
    path_prefix: str
    text: str = field(repr=False)

    @property
    def netloc(self) -> str:
        return self.host if self.port is None else f"{self.host}:{self.port}"

    @property
    def envelope_url(self) -> str:
        return (f"{self.scheme}://{self.netloc}/{self.path_prefix}"
                f"api/{self.project_id}/envelope/")

    @property
    def auth_header(self) -> str:
        return (f"Sentry sentry_version=7, sentry_client={CLIENT_NAME}, "
                f"sentry_key={self.public_key}")

    def __repr__(self) -> str:
        return f"Dsn(host={self.netloc!r}, project_id={self.project_id!r})"

    def __str__(self) -> str:
        return f"{self.netloc}/{self.project_id}"


def parse_dsn(text: str) -> Dsn:
    """Read a DSN, or raise :class:`DsnError` naming what is missing."""
    parts = urlsplit((text or "").strip())
    if parts.scheme not in ("http", "https"):
        raise DsnError("the DSN has no http or https scheme")
    if not parts.username:
        raise DsnError("the DSN has no public key")
    if not parts.hostname:
        raise DsnError("the DSN has no host")
    try:
        port = parts.port
    except ValueError:
        raise DsnError("the DSN's port is not a number") from None
    segments = [s for s in parts.path.split("/") if s]
    if not segments:
        raise DsnError("the DSN has no project id")
    prefix = "".join(f"{s}/" for s in segments[:-1])
    return Dsn(scheme=parts.scheme, host=parts.hostname, port=port,
               public_key=parts.username, project_id=segments[-1],
               path_prefix=prefix, text=(text or "").strip())
