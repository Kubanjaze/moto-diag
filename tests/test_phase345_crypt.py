"""Phase 345 — the one encrypted format: scrypt and AES-256-GCM, streamed.

Round trips over more than one chunk; two encryptions of the same bytes
differ after the magic; a flipped byte in the ciphertext, the tag and the
salt each refuses and leaves nothing; a wrong passphrase refuses; a bad magic
refuses before reading further.
"""

from __future__ import annotations

import hashlib
import os
import sys

import pytest
from support.phase345 import REAL_LOG2_COST, cheap_crypto

from motodiag.backup import crypt
from motodiag.backup.crypt import (
    CHUNK,
    HEADER_LEN,
    MAGIC,
    BackupLibraryMissing,
    BackupTampered,
    decrypt_file,
    encrypt_file,
)

PASS = "correct horse battery staple"


@pytest.fixture(autouse=True)
def _cheap(monkeypatch):
    cheap_crypto(monkeypatch)


@pytest.fixture
def plain(tmp_path):
    path = tmp_path / "plain.bin"
    path.write_bytes(os.urandom(CHUNK * 2 + 12345))
    return path


def test_a_round_trip_over_more_than_one_chunk(tmp_path, plain):
    digest = encrypt_file(plain, tmp_path / "x.enc", PASS)
    assert digest == hashlib.sha256((tmp_path / "x.enc").read_bytes()).hexdigest()
    decrypt_file(tmp_path / "x.enc", tmp_path / "out.bin", PASS)
    assert (tmp_path / "out.bin").read_bytes() == plain.read_bytes()
    assert list(tmp_path.glob(".*partial")) == []


def test_the_header(tmp_path, plain):
    encrypt_file(plain, tmp_path / "x.enc", PASS)
    data = (tmp_path / "x.enc").read_bytes()
    assert data[:4] == MAGIC and data[4] == 1 and data[5] == 10
    assert len(data) == HEADER_LEN + plain.stat().st_size + 16


def test_the_default_cost_is_two_to_the_seventeenth():
    assert crypt.DEFAULT_LOG2_COST == 10  # this module's cheap cost, patched
    assert REAL_LOG2_COST == 17


def test_two_encryptions_differ_in_every_byte_after_the_magic(tmp_path, plain):
    encrypt_file(plain, tmp_path / "a.enc", PASS)
    encrypt_file(plain, tmp_path / "b.enc", PASS)
    a, b = (tmp_path / "a.enc").read_bytes(), (tmp_path / "b.enc").read_bytes()
    assert a[:6] == b[:6]  # magic, version, cost
    same = sum(x == y for x, y in zip(a[6:], b[6:]))
    assert same < len(a) // 100  # chance agreement only (1 in 256 per byte)
    assert a[6:22] != b[6:22] and a[22:34] != b[22:34]  # salt, nonce


@pytest.mark.parametrize("where", ["ciphertext", "tag", "salt"])
def test_a_flipped_byte_refuses_and_leaves_nothing(tmp_path, plain, where):
    encrypt_file(plain, tmp_path / "x.enc", PASS)
    data = bytearray((tmp_path / "x.enc").read_bytes())
    pos = {"ciphertext": HEADER_LEN + CHUNK + 7, "tag": len(data) - 3, "salt": 9}[where]
    data[pos] ^= 0x01
    (tmp_path / "x.enc").write_bytes(bytes(data))
    with pytest.raises(BackupTampered):
        decrypt_file(tmp_path / "x.enc", tmp_path / "out.bin", PASS)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["plain.bin", "x.enc"]


def test_a_wrong_passphrase_refuses(tmp_path, plain):
    encrypt_file(plain, tmp_path / "x.enc", PASS)
    with pytest.raises(BackupTampered, match="wrong passphrase"):
        decrypt_file(tmp_path / "x.enc", tmp_path / "out.bin", PASS + "!")
    assert not (tmp_path / "out.bin").exists()


def test_a_failed_decrypt_leaves_an_existing_destination_alone(tmp_path, plain):
    encrypt_file(plain, tmp_path / "x.enc", PASS)
    (tmp_path / "out.bin").write_bytes(b"before")
    with pytest.raises(BackupTampered):
        decrypt_file(tmp_path / "x.enc", tmp_path / "out.bin", "wrong")
    assert (tmp_path / "out.bin").read_bytes() == b"before"


def test_a_bad_magic_refuses_before_reading_further(tmp_path, monkeypatch):
    (tmp_path / "x.enc").write_bytes(b"NOPE" + b"\0" * 100)

    def no_kdf(*a, **k):
        raise AssertionError("the key was derived for a file with no MDBK header")

    monkeypatch.setattr(crypt, "_key", no_kdf)
    with pytest.raises(BackupTampered, match="MDBK"):
        decrypt_file(tmp_path / "x.enc", tmp_path / "out.bin", PASS)
    assert not (tmp_path / "out.bin").exists()


def test_a_truncated_object_refuses(tmp_path):
    (tmp_path / "x.enc").write_bytes(MAGIC + b"\x01\x0a" + b"\0" * 10)
    with pytest.raises(BackupTampered, match="truncated"):
        decrypt_file(tmp_path / "x.enc", tmp_path / "out.bin", PASS)


def test_an_unknown_version_and_an_absurd_cost_refuse(tmp_path, plain):
    encrypt_file(plain, tmp_path / "x.enc", PASS)
    data = bytearray((tmp_path / "x.enc").read_bytes())
    for pos, value, match in ((4, 2, "version 2"), (5, 40, "out of range")):
        bad = bytearray(data)
        bad[pos] = value
        (tmp_path / "bad.enc").write_bytes(bytes(bad))
        with pytest.raises(BackupTampered, match=match):
            decrypt_file(tmp_path / "bad.enc", tmp_path / "out.bin", PASS)


def test_without_the_package_it_says_what_to_install(tmp_path, plain, monkeypatch):
    monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives.ciphers", None)
    with pytest.raises(BackupLibraryMissing, match=r"motodiag\[backup\]"):
        encrypt_file(plain, tmp_path / "x.enc", PASS)
