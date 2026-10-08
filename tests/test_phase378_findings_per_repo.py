"""Phase 378, K20 — B1 checks each repository's own findings header.

B1 compared the backend header's "highest assigned" with the union of both
repositories' entries. Mobile's header states its own file's highest, so a
finding filed in mobile above the backend's highest turned the backend red
until a backend commit updated its header (F179 in 360, F181 in 361), and a
mobile session cannot make that commit. Now B1 reads its own file; the next
number still comes from the union, and B2 still resolves citations against
both.
"""

from __future__ import annotations

import pathlib
import subprocess

from test_phase255D_finding_contract import SKILL, check, entries

ROOT = pathlib.Path(__file__).resolve().parent.parent
K20 = ROOT / ".claude" / "skills" / "finding" / "fixtures" / "k20"
SIBLING = "../sibling/docs/FOLLOWUPS.md"


def _b1(repo: pathlib.Path) -> list[str]:
    return [f for f in check(repo, sibling=SIBLING) if f.startswith("B1")]


def test_a_sibling_ahead_does_not_fail_b1():
    """The fixture's sibling has F20; this file's highest is F12."""
    assert max(entries(K20 / "sibling" / "docs" / "FOLLOWUPS.md")) == 20
    assert _b1(K20 / "sibling_ahead") == []


def test_a_stale_own_header_fails_b1():
    assert _b1(K20 / "stale_header") == [
        "B1 header claims highest assigned is F11, but this file's highest entry is F12"]


def test_the_backend_header_names_its_own_file():
    text = (ROOT / "docs" / "FOLLOWUPS.md").read_text(encoding="utf-8")
    assert "**F" in text and "(this file)" in text.split("highest assigned is", 1)[1][:40]


def test_allocation_still_takes_the_union(tmp_path):
    """next_f_number.sh reads both files; nothing in K20 narrows it."""
    script = (SKILL / "next_f_number.sh").read_text(encoding="utf-8")
    assert "moto-diag-mobile/docs/FOLLOWUPS.md" in script
    out = subprocess.run(["sh", str(SKILL / "next_f_number.sh")], capture_output=True,
                         text=True, check=True).stdout
    here = entries(ROOT / "docs" / "FOLLOWUPS.md")
    there = entries(ROOT / ".." / "moto-diag-mobile" / "docs" / "FOLLOWUPS.md")
    assert f"next free: F{max(here | there) + 1}" in out
