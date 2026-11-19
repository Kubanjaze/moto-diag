"""Phase 334 — the two legal texts, their template, and row 334B (Logic items 1 to 3, 8).

Each of the operator's six clauses is found by one short phrase of it, so
deleting a clause turns its test red. Every service the Step 0 census traced
data to is named in the privacy policy. Neither file holds a phone number, a
price id or Sentry's address.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from motodiag.auth import terms_acceptance

ROOT = Path(__file__).resolve().parent.parent
LEGAL = ROOT / "docs" / "legal"
TERMS = LEGAL / "terms.md"
PRIVACY = LEGAL / "privacy.md"
HEADER = re.compile(r"^Version (\d+\.\d+) — (\d{4}-\d{2}-\d{2})$", re.M)
ATTRIBUTION = (
    "Adapted from Basecamp's policies (https://github.com/basecamp/policies), "
    "used under the Creative Commons Attribution 4.0 International licence (CC BY 4.0)."
)

#: The operator's six clauses (K84), each by one short phrase of its own.
CLAUSES = {
    "the mechanic decides": "The mechanic decides what to do to a bike",
    "the shop's own sales tax": "The shop is responsible for its own sales tax",
    "the shop indemnifies Mekno": "The shop agrees to indemnify Mekno",
    "the cap": ("is capped at what the shop paid Mekno in fees in the 12 "
                "months before the claim"),
    "the data is the shop's, out and deleted": "When a shop asks, its data is deleted",
    "shown before paid, cancelled online": "You can cancel online as easily as you subscribed",
}
#: The Step 0 census (334_phase_log.md): every service data leaves for.
SERVICES = ("Stripe", "Anthropic", "OpenAI", "Whisper", "Sentry", "Backblaze",
            "Apple", "NHTSA")
FORBIDDEN = {
    "a phone number": re.compile(r"\+?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b|\+\d[\d\s-]{8,}"),
    "a price id": re.compile(r"\bprice_\w+"),
    "Sentry's address": re.compile(r"sentry\.io|ingest\.|https?://[^\s)]*sentry", re.I),
}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _words(path: Path) -> str:
    """The text with its line wrapping undone, for finding a phrase."""
    return " ".join(_text(path).split())


def _header(path: Path) -> tuple[str, str]:
    head = "\n".join(_text(path).splitlines()[:5])
    m = HEADER.search(head)
    assert m, f"{path.name}: no 'Version X.Y — YYYY-MM-DD' line at the top"
    return m.group(1), m.group(2)


@pytest.mark.parametrize("path", [TERMS, PRIVACY], ids=["terms", "privacy"])
def test_the_header_parses(path):
    _header(path)


def test_the_server_knows_the_terms_version_and_date():
    assert _header(TERMS) == (terms_acceptance.TERMS_VERSION, terms_acceptance.TERMS_DATE)


@pytest.mark.parametrize("name", list(CLAUSES))
def test_each_clause_is_in_the_terms(name):
    assert CLAUSES[name] in _words(TERMS), name


def test_the_terms_cover_the_rest_of_the_clauses():
    t = _words(TERMS)
    assert "it can take its data out" in t
    assert "Before you pay for a subscription, Mekno shows its price" in t
    assert "responsible for the repair" in t
    assert "https://getmekno.com/privacy/" in t


@pytest.mark.parametrize("service", SERVICES)
def test_every_service_in_the_census_is_named(service):
    assert service in _text(PRIVACY), service


@pytest.mark.parametrize("path", [TERMS, PRIVACY], ids=["terms", "privacy"])
@pytest.mark.parametrize("what", list(FORBIDDEN))
def test_nothing_forbidden(path, what):
    hits = FORBIDDEN[what].findall(_text(path))
    assert hits == [], f"{path.name} holds {what}: {hits}"


@pytest.mark.parametrize("what", list(FORBIDDEN))
def test_the_forbidden_patterns_catch_a_planted_case(what):
    planted = {"a phone number": "call 555-123-4567",
               "a price id": "price_1QabcXYZ",
               "Sentry's address": "https://o1.ingest.sentry.io/123"}[what]
    assert FORBIDDEN[what].search(planted)


@pytest.mark.parametrize("path", [TERMS, PRIVACY], ids=["terms", "privacy"])
def test_contact_is_the_support_page(path):
    assert "https://getmekno.com/support/" in _text(path)


@pytest.mark.parametrize("path", [TERMS, PRIVACY], ids=["terms", "privacy"])
def test_each_ends_with_the_attribution(path):
    assert _text(path).rstrip().splitlines()[-1] == ATTRIBUTION


def test_the_readme_names_the_template_its_address_and_licence():
    t = _text(LEGAL / "README.md")
    assert "Basecamp's policies" in t
    assert "https://github.com/basecamp/policies" in t
    assert "CC BY 4.0" in t
    assert "TERMS_VERSION" in t


def test_row_334B_is_open_and_names_its_prompt():
    rows = [line for line in _text(ROOT / "docs" / "ROADMAP.md").splitlines()
            if line.startswith("| 334B |")]
    assert len(rows) == 1
    cells = [c.strip() for c in rows[0].split("|")]
    assert cells[3] == "🔲"
    assert "docs/prompts/334B_the_apps_terms_screen.txt" in rows[0]
    assert (ROOT / "docs" / "prompts" / "334B_the_apps_terms_screen.txt").exists()
