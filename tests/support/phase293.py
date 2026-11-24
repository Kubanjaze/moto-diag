"""Phase 293's test material: PDFs made in the test, stub virus scanners, and
two shops with an owner, a service writer and a tech each.

Every PDF is made here with ``reportlab`` and ``pypdf``; every scanner is a
shell script on a temporary PATH; every database is a temporary one. Nothing
reads the live database or a real manual.
"""

from __future__ import annotations

import io
import json
import os
import stat
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject, TextStringObject
from reportlab.pdfgen import canvas

from motodiag.auth.api_key_repo import create_api_key
from motodiag.core.database import get_connection, init_db
from motodiag.shop import create_shop
from motodiag.shop.rbac import add_shop_member, seed_first_owner

TORQUE = "Front brake caliper mounting bolt torque: 30 N·m"
EICAR = (r"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")


def pdf_bytes(pages: int = 1, texts: list[str] | None = None) -> bytes:
    """A real PDF with a text layer: page n reads ``texts[n-1]``."""
    texts = texts or [TORQUE] + [f"Page {n} stator lead resistance" for n in range(2, pages + 1)]
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for t in texts[:pages]:
        c.drawString(72, 720, t)
        c.showPage()
    c.save()
    return buf.getvalue()


def padded(data: bytes, size: int) -> bytes:
    """The same PDF, exactly ``size`` bytes long, by a trailing comment."""
    pad = size - len(data) - 2
    assert pad >= 0
    return data + b"\n%" + b"x" * pad


def _rewritten(data: bytes, change) -> bytes:
    w = PdfWriter()
    w.append(PdfReader(io.BytesIO(data)))
    change(w)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def _launch(w: PdfWriter) -> None:
    w._root_object[NameObject("/OpenAction")] = DictionaryObject({
        NameObject("/S"): NameObject("/Launch"),
        NameObject("/F"): TextStringObject("calc.exe"),
    })


def bad_files() -> dict[str, tuple[bytes, str]]:
    """The five planted bad files, each with the reason it must be refused."""
    good = pdf_bytes()
    return {
        "png": (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "the file is not a PDF"),
        "javascript": (_rewritten(good, lambda w: w.add_js("app.alert('x');")),
                       "the file carries JavaScript"),
        "attachment": (_rewritten(good, lambda w: w.add_attachment("a.txt", b"hello")),
                       "the file carries an attachment"),
        "launch": (_rewritten(good, _launch), "the file carries a launch action"),
        "locked": (_rewritten(good, lambda w: w.encrypt(user_password="secret",
                                                         owner_password="owner")),
                   "the file is locked with a password"),
    }


def owner_password_only() -> bytes:
    return _rewritten(pdf_bytes(), lambda w: w.encrypt(user_password="", owner_password="owner"))


# ---------------------------------------------------------------- scanners
def stub_scanner(folder: Path, kind: str = "eicar") -> Path:
    """A ``clamdscan`` on ``folder``: ``eicar`` exits 1 for a file holding the
    EICAR string and 0 otherwise; ``broken`` exits 2."""
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / "clamdscan"
    if kind == "broken":
        body = "#!/bin/sh\necho 'ERROR: cannot connect' >&2\nexit 2\n"
    else:
        body = ('#!/bin/sh\nfor f; do :; done\n'
                'if grep -q "EICAR-STANDARD-ANTIVIRUS-TEST-FILE" "$f"; then\n'
                '  echo "$f: Eicar-Signature FOUND"; exit 1\nfi\n'
                'echo "$f: OK"; exit 0\n')
    script.write_text(body)
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return folder


def use_path(monkeypatch, folder: Path) -> None:
    """PATH is the stub folder, plus /usr/bin and /bin for the script's tools."""
    monkeypatch.setenv("PATH", os.pathsep.join([str(folder), "/usr/bin", "/bin"]))


# ---------------------------------------------------------------- the world
@dataclass
class Shop:
    id: int
    keys: dict[str, str] = field(default_factory=dict)
    users: dict[str, int] = field(default_factory=dict)


def make_user(db_path: str, username: str, sub_tier: str | None = "shop") -> int:
    with get_connection(db_path) as conn:
        uid = conn.execute(
            "INSERT INTO users (username, email, tier, is_active) VALUES (?, ?, 'individual', 1)",
            (username, f"{username}@ex.com")).lastrowid
        if sub_tier is not None:
            conn.execute(
                "INSERT INTO subscriptions (user_id, tier, status, current_period_end) "
                "VALUES (?, ?, 'active', datetime('now', '+30 days'))", (uid, sub_tier))
    return int(uid)


def key_for(db_path: str, user_id: int) -> str:
    return create_api_key(user_id, db_path=db_path)[1]


def make_shop(db_path: str, name: str) -> Shop:
    """A shop on the Shop plan: its owner, a service writer on an Individual
    subscription of their own, and a tech."""
    owner = make_user(db_path, f"{name}_owner", "shop")
    shop = Shop(create_shop(name, db_path=db_path))
    seed_first_owner(shop.id, owner, db_path=db_path)
    shop.users["owner"] = owner
    for role, tier in (("service_writer", "individual"), ("tech", "individual")):
        uid = make_user(db_path, f"{name}_{role}", tier)
        add_shop_member(shop.id, uid, role, db_path=db_path)
        shop.users[role] = uid
    shop.keys = {role: key_for(db_path, uid) for role, uid in shop.users.items()}
    return shop


@pytest.fixture
def manuals_db(tmp_path, monkeypatch):
    """A fresh database and data folder, as the photo tests' ``api_db``, with a
    stub scanner on PATH that finds the EICAR string."""
    from motodiag.core.config import reset_settings

    path = str(tmp_path / "phase293.db")
    init_db(path)
    monkeypatch.setenv("MOTODIAG_DB_PATH", path)
    monkeypatch.setenv("MOTODIAG_DATA_DIR", str(tmp_path / "data"))
    for tier in ("anonymous", "individual", "shop", "company"):
        monkeypatch.setenv(f"MOTODIAG_RATE_LIMIT_{tier.upper()}_PER_MINUTE", "9999")
    use_path(monkeypatch, stub_scanner(tmp_path / "bin"))
    reset_settings()
    yield path
    reset_settings()


def metadata(**over) -> str:
    meta = {"title": "Honda CBR600RR service manual", "kind": "service_manual",
            "make": "Honda", "model": "CBR600RR", "year_start": 2003, "year_end": 2006}
    meta.update(over)
    return json.dumps(meta)


def upload(client, shop_id: int, key: str, data: bytes, **meta):
    return client.post(
        f"/v1/shop/{shop_id}/manuals",
        headers={"X-API-Key": key},
        files={"file": ("manual.pdf", data, "application/pdf")},
        data={"metadata": metadata(**meta)},
    )
