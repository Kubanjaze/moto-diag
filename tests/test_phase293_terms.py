"""Phase 293 — the terms and the privacy policy at version 1.1 (K119, K122).

The terms gain "Manuals and files you upload", five bullets each found by
one short phrase; the privacy policy gains its manuals line and its review
sentence; the Backblaze sentence is unchanged (K121). The sign-in gate is as
it was (K128): with ``MOTODIAG_TERMS_REQUIRED`` on, a user who accepted 1.0
is held at the four exempt routes until they accept 1.1.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from support.phase303 import (
    add_member,
    auth,
    client,
    login,
    make_key,
    make_shop,
    make_sub,
    make_user,
    new_db,
)

from motodiag.auth import terms_acceptance as terms
from motodiag.core.config import reset_settings

ROOT = Path(__file__).resolve().parent.parent
TERMS = (ROOT / "docs" / "legal" / "terms.md").read_text()
PRIVACY = (ROOT / "docs" / "legal" / "privacy.md").read_text()

UPLOAD_BULLETS = [
    "**Only what you have the right to use.**",
    "**It stays with your shop.**",
    "by a person at Mekno, who sees the file to do so",
    "we may take it down while we look into it",
    "the mechanic decides.",
]


def _section(text: str, heading: str) -> str:
    return text.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def test_the_version_is_1_1_and_both_headers_say_so():
    assert terms.TERMS_VERSION == "1.1"
    line = f"Version {terms.TERMS_VERSION} — {terms.TERMS_DATE}"
    assert TERMS.splitlines()[2] == line
    # Phase 409: the privacy policy keeps its own number and is at 1.2 (it
    # names Cloudflare for the app); the terms stay at 1.1.
    assert PRIVACY.splitlines()[2] == "Version 1.2 — 2026-11-27"


@pytest.mark.parametrize("phrase", UPLOAD_BULLETS)
def test_each_upload_bullet(phrase):
    assert phrase in _flat(_section(TERMS, "Manuals and files you upload"))


def test_the_clause_sits_after_the_shops_data_and_promises_no_company_sharing():
    assert TERMS.index("## The shop's data is the shop's") < TERMS.index(
        "## Manuals and files you upload") < TERMS.index("## Paying, renewing and cancelling")
    assert "its own shops" not in TERMS


def test_the_privacy_policys_two_new_sentences():
    kept = _flat(_section(PRIVACY, "What we keep"))
    assert ("**Manuals and parts books** the shop uploads, the page images and the text "
            "made from them, and who uploaded, reviewed, flagged or removed each one") in kept
    why = _flat(_section(PRIVACY, "Why we keep it"))
    assert ("A person at Mekno looks at each manual a shop uploads before the shop can open "
            "it, and again when someone in the shop flags a page or a publisher complains"
            ) in why


def test_the_backblaze_sentence_is_unchanged():
    assert ("an encrypted copy of the database and of every upload, each night"
            in _flat(PRIVACY))


def test_the_site_pages_are_the_builds_output():
    import importlib.util

    spec = importlib.util.spec_from_file_location("site_build", ROOT / "scripts" / "site_build.py")
    sb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sb)
    assert set(sb.LEGAL_PAGES) == {"terms/index.html", "privacy/index.html"}
    for page in sb.LEGAL_PAGES:
        html = (ROOT / "site" / page).read_text(encoding="utf-8")
        assert html == sb.render_legal(page), f"run scripts/site_build.py legal ({page})"
        # Phase 409: the privacy policy is at 1.2, the terms at 1.1.
        assert ("Version 1.2" if page.startswith("privacy") else "Version 1.1") in html


@pytest.fixture
def held(tmp_path, monkeypatch):
    """A shop owner who accepted 1.0, with the switch on."""
    db = new_db(tmp_path, monkeypatch)
    uid = make_user(db, "olga")
    make_sub(db, uid, "shop")
    shop = make_shop(db, "alpha", uid)
    add_member(db, shop, make_user(db, "tom"))
    terms.record_acceptance(uid, "1.0", db_path=db)
    monkeypatch.setenv("MOTODIAG_TERMS_REQUIRED", "true")
    reset_settings()
    c = client(db)
    yield c, shop, {"X-API-Key": make_key(db, uid)}, auth(login(c, "olga"))
    reset_settings()


def test_a_user_who_accepted_1_0_is_held_until_they_accept_1_1(held):
    c, shop, key, session = held
    assert c.get("/v1/terms").json()["version"] == "1.1"
    r = c.get(f"/v1/shop/{shop}/manuals", headers=key)
    assert r.status_code == 403
    assert r.json()["type"].endswith("terms-not-accepted")
    assert "version 1.1" in r.json()["detail"]
    assert c.get("/v1/terms", headers=key).status_code == 200
    assert c.get("/v1/auth/me", headers=key).status_code == 200
    assert c.post("/v1/auth/logout", headers=session).status_code in (200, 204)
    assert c.post("/v1/terms/accept", json={"version": "1.1"}, headers=key).status_code == 200
    assert c.get(f"/v1/shop/{shop}/manuals", headers=key).status_code == 200
