"""The one encrypted format of a backup object (Phase 345).

A key of 32 bytes is derived from the passphrase with scrypt (a random 16-byte
salt per file; cost ``2**17``, r 8, p 1 by default) and the file is encrypted
with AES-256-GCM, streamed in 1 MiB chunks. The file is::

    b"MDBK" | version (1 byte) | log2 of the cost (1 byte) | salt (16) | nonce (12)
    | ciphertext | tag (16)

The header is the cipher's associated data, so a changed byte anywhere fails
the tag. :func:`decrypt_file` writes plaintext to a temporary file beside its
destination and renames it there only after the tag verifies, so a wrong
passphrase or a tampered object leaves nothing behind.

``cryptography`` is imported inside the calls: a CLI install without the
``backup`` extra still imports the package.
"""

from __future__ import annotations

import hashlib
import os
import struct
from pathlib import Path
from typing import Any

MAGIC = b"MDBK"
VERSION = 1
DEFAULT_LOG2_COST = 17
CHUNK = 1 << 20
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
_HEADER = struct.Struct(f">4sBB{SALT_LEN}s{NONCE_LEN}s")
HEADER_LEN = _HEADER.size


class BackupTampered(Exception):
    """An object does not decrypt or check: a wrong passphrase, or changed bytes."""


class BackupLibraryMissing(Exception):
    """The ``cryptography`` package is not installed."""


def _primitives() -> tuple[Any, Any, Any, Any]:
    try:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    except ImportError as e:
        raise BackupLibraryMissing(
            "the backup needs the cryptography package: pip install 'motodiag[backup]'"
        ) from e
    return Cipher, (algorithms, modes), Scrypt, InvalidTag


def _key(passphrase: str, salt: bytes, log2_cost: int, scrypt: Any) -> bytes:
    kdf = scrypt(salt=salt, length=32, n=2 ** log2_cost, r=8, p=1)
    return bytes(kdf.derive(passphrase.encode("utf-8")))


def encrypt_file(src: Path, dst: Path, passphrase: str, *,
                 log2_cost: int | None = None) -> str:
    """Encrypt ``src`` into ``dst``; returns the sha256 of what was written.
    The cost is :data:`DEFAULT_LOG2_COST` as it stands at the call, so a test
    may lower it for a whole run; the cost used is in the header."""
    cipher_cls, (algorithms, modes), scrypt, _ = _primitives()
    log2_cost = DEFAULT_LOG2_COST if log2_cost is None else log2_cost
    salt, nonce = os.urandom(SALT_LEN), os.urandom(NONCE_LEN)
    header = _HEADER.pack(MAGIC, VERSION, log2_cost, salt, nonce)
    enc = cipher_cls(algorithms.AES(_key(passphrase, salt, log2_cost, scrypt)),
                     modes.GCM(nonce)).encryptor()
    enc.authenticate_additional_data(header)
    digest = hashlib.sha256(header)
    with open(src, "rb") as fin, open(dst, "wb") as fout:
        fout.write(header)
        while chunk := fin.read(CHUNK):
            out = enc.update(chunk)
            digest.update(out)
            fout.write(out)
        tail = enc.finalize() + enc.tag
        digest.update(tail)
        fout.write(tail)
    return digest.hexdigest()


def _read_header(fin: Any, total: int) -> tuple[bytes, int, bytes, bytes]:
    raw = fin.read(HEADER_LEN)
    if len(raw) < 4 or raw[:4] != MAGIC:
        raise BackupTampered("not a MotoDiag backup object (no MDBK header)")
    if len(raw) < HEADER_LEN or total < HEADER_LEN + TAG_LEN:
        raise BackupTampered("the backup object is truncated")
    _, version, log2_cost, salt, nonce = _HEADER.unpack(raw)
    if version != VERSION:
        raise BackupTampered(f"unknown backup format version {version}")
    return raw, log2_cost, salt, nonce


def decrypt_file(src: Path, dst: Path, passphrase: str) -> None:
    """Decrypt ``src`` onto ``dst``, only once its tag verifies; raises
    :class:`BackupTampered` and leaves nothing at ``dst`` otherwise."""
    cipher_cls, (algorithms, modes), scrypt, invalid_tag = _primitives()
    dst = Path(dst)
    tmp = dst.with_name(f".{dst.name}.partial")
    total = os.path.getsize(src)
    try:
        with open(src, "rb") as fin:
            header, log2_cost, salt, nonce = _read_header(fin, total)
            if not 10 <= log2_cost <= 22:
                raise BackupTampered(f"the header's cost 2**{log2_cost} is out of range")
            dec = cipher_cls(algorithms.AES(_key(passphrase, salt, log2_cost, scrypt)),
                             modes.GCM(nonce)).decryptor()
            dec.authenticate_additional_data(header)
            remaining = total - HEADER_LEN - TAG_LEN
            with open(tmp, "wb") as fout:
                while remaining > 0:
                    chunk = fin.read(min(CHUNK, remaining))
                    remaining -= len(chunk)
                    fout.write(dec.update(chunk))
                tag = fin.read(TAG_LEN)
                try:
                    fout.write(dec.finalize_with_tag(tag))
                except invalid_tag as e:
                    raise BackupTampered(
                        f"{Path(src).name} does not decrypt: a wrong passphrase, "
                        "or the object was changed") from e
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)
