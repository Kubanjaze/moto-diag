"""Phase 293 — the server's checks on an uploaded manual, and its virus scan.

Every PDF is made in the test (``support.phase293``); every scanner is a
stub script on a temporary PATH. ``check_pdf`` refuses each of the five
planted files with its own reason and passes the good one; a file locked
only against editing (an owner password, opening with none) passes; with
``pypdfium2`` unimportable every file is refused, never let through.
"""

from __future__ import annotations

import builtins
import os
import shutil

import pytest
from support.phase293 import (
    EICAR,
    TORQUE,
    bad_files,
    owner_password_only,
    padded,
    pdf_bytes,
    stub_scanner,
    use_path,
)

from motodiag.manuals import checks, scan


def _write(tmp_path, name: str, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_the_good_file_passes(tmp_path):
    assert checks.check_pdf(_write(tmp_path, "good.pdf", pdf_bytes())) == []


def test_a_good_file_with_a_trailing_comment_passes(tmp_path):
    data = pdf_bytes()
    assert checks.check_pdf(_write(tmp_path, "pad.pdf", padded(data, len(data) + 4096))) == []


@pytest.mark.parametrize("name", ["png", "javascript", "attachment", "launch", "locked"])
def test_each_bad_file_is_refused_with_its_reason(tmp_path, name):
    data, reason = bad_files()[name]
    assert checks.check_pdf(_write(tmp_path, "manual.pdf", data)) == [reason]


def test_an_owner_password_alone_does_not_lock_it(tmp_path):
    assert checks.check_pdf(_write(tmp_path, "owner.pdf", owner_password_only())) == []


def test_a_pdf_header_on_garbage_cannot_be_opened(tmp_path):
    reasons = checks.check_pdf(_write(tmp_path, "junk.pdf", b"%PDF-1.7\n" + b"\x00" * 200))
    assert reasons and reasons[0] in (checks.UNREADABLE, checks.UNRENDERABLE)


def test_page_count(tmp_path):
    assert checks.page_count(_write(tmp_path, "three.pdf", pdf_bytes(3))) == 3


def test_with_pypdfium2_unimportable_every_file_is_refused(tmp_path, monkeypatch):
    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name == "pypdfium2" or name.startswith("pypdfium2."):
            raise ImportError("no pypdfium2")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(__import__("sys").modules, "pypdfium2", raising=False)
    monkeypatch.setattr(builtins, "__import__", refuse)
    assert checks.check_pdf(_write(tmp_path, "good.pdf", pdf_bytes())) == [checks.CANNOT_READ]


# ---------------------------------------------------------------- the scan
def test_a_clean_file_scans_clean(tmp_path, monkeypatch):
    use_path(monkeypatch, stub_scanner(tmp_path / "bin"))
    result = scan.scan_file(_write(tmp_path, "good.pdf", pdf_bytes()))
    assert result.status == "clean"


def test_the_eicar_string_scans_infected(tmp_path, monkeypatch):
    use_path(monkeypatch, stub_scanner(tmp_path / "bin"))
    data = pdf_bytes() + b"\n%" + EICAR.encode()
    result = scan.scan_file(_write(tmp_path, "eicar.pdf", data))
    assert result.status == "infected"
    assert "FOUND" in result.detail


def test_a_scanner_that_fails_is_unavailable(tmp_path, monkeypatch):
    use_path(monkeypatch, stub_scanner(tmp_path / "bin", "broken"))
    result = scan.scan_file(_write(tmp_path, "good.pdf", pdf_bytes()))
    assert result.status == "unavailable"
    assert "exit 2" in result.detail


def test_no_scanner_on_path_is_unavailable(tmp_path, monkeypatch):
    (tmp_path / "empty").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    result = scan.scan_file(_write(tmp_path, "good.pdf", pdf_bytes()))
    assert result.status == "unavailable"


def test_clamscan_is_used_when_the_daemon_is_absent(tmp_path, monkeypatch):
    folder = stub_scanner(tmp_path / "bin")
    (folder / "clamdscan").rename(folder / "clamscan")
    # Phase 210, bug fix #1: only the stub and the one tool it runs, never
    # /usr/bin, where a machine with ClamAV installed has a real clamdscan
    # that `_command` rightly prefers.
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "grep").symlink_to(shutil.which("grep"))
    monkeypatch.setenv("PATH", os.pathsep.join([str(folder), str(tools)]))
    assert scan._command(tmp_path / "x.pdf")[0] == str(folder / "clamscan")
    assert scan.scan_file(_write(tmp_path, "good.pdf", pdf_bytes())).status == "clean"


def test_the_text_planted_is_the_text_read(tmp_path):
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(_write(tmp_path, "good.pdf", pdf_bytes())))
    try:
        assert TORQUE.split(":")[0] in doc[0].get_textpage().get_text_bounded()
    finally:
        doc.close()
