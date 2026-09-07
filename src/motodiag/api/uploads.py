"""Bounded reads for multipart uploads (Phase 207).

Every upload route used to call ``await file.read()`` and only then
consult its quota helpers. The quotas are per-*session* or per-work-order
aggregates, not per-request ceilings, so a single arbitrarily large POST
was fully materialised as ``bytes`` before anything looked at its size.
Reading first and checking second is the wrong order: the check cannot
undo the allocation it was meant to prevent.

:func:`read_bounded` reads in chunks and stops the moment the stream
exceeds the ceiling, so an oversized body costs one chunk of headroom
rather than its full length.
"""

from typing import Optional

from fastapi import UploadFile


CHUNK_BYTES = 1024 * 1024  # 1 MiB


class UploadTooLargeError(Exception):
    """Raised when a single upload exceeds its per-request ceiling."""

    def __init__(self, limit_bytes: int, kind: str = "file") -> None:
        self.limit_bytes = limit_bytes
        self.kind = kind
        super().__init__(
            f"{kind} exceeds the per-upload limit of {limit_bytes} bytes"
        )


async def read_bounded(
    file: UploadFile,
    limit_bytes: int,
    kind: str = "file",
    declared_length: Optional[int] = None,
) -> bytes:
    """Read `file` fully, aborting past `limit_bytes`.

    `declared_length` (the request's Content-Length, when present) lets
    an obviously-oversized request be rejected before the first read.
    It is a hint only — it is client-supplied and may be absent under
    chunked transfer encoding — so the chunk loop still enforces the
    ceiling regardless of what was declared.
    """
    if declared_length is not None and declared_length > limit_bytes:
        raise UploadTooLargeError(limit_bytes, kind)

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > limit_bytes:
            raise UploadTooLargeError(limit_bytes, kind)
        chunks.append(chunk)
    return b"".join(chunks)
