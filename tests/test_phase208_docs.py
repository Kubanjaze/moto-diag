"""Phase 208 — the documentation drift guard.

Docs rot silently. Nothing fails when a command is renamed, so the
README keeps describing a product that no longer exists — which is
exactly what Phase 208 found: a quick start whose first line
(`.venv/Scripts/activate`) could not run on the only host this project
has, and a `--version` five minors stale.

These tests assert the docs' *claims about the software* against the
software: every `motodiag` command named in any doc exists in the live
Click registry, and every `/v1/...` path exists in the live OpenAPI
schema.

What this CANNOT do: prove the sentence next to a command is true. It
checks names. Running the commands you document is still the only cover
for meaning, and the guides were written that way — see the Phase 208
log for which commands were executed and which (the paid AI ones) were
not.
"""

from __future__ import annotations

import re
from pathlib import Path

import click
import pytest

from motodiag.api.app import create_app
from motodiag.cli.main import cli

REPO_ROOT = Path(__file__).resolve().parent.parent
MOBILE_ROOT = REPO_ROOT.parent / "moto-diag-mobile"

#: Docs written FOR USERS. Phase docs, the roadmap and the pattern
#: catalogue are development history — they describe what a command was
#: called at the time, deliberately, and pinning them to the present
#: would make the historical record wrong.
BACKEND_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "contributing.md",
    REPO_ROOT / "docs" / "guide" / "quickstart.md",
    REPO_ROOT / "docs" / "guide" / "shop-workflow.md",
    REPO_ROOT / "docs" / "guide" / "api.md",
    # Phase 209
    REPO_ROOT / "docs" / "guide" / "install.md",
    REPO_ROOT / "docs" / "releasing.md",
    REPO_ROOT / "docs" / "launch-checklist.md",
]

MOBILE_DOCS = [
    MOBILE_ROOT / "README.md",
    MOBILE_ROOT / "docs" / "app-store-listing.md",
]


def _user_docs() -> list[Path]:
    docs = [p for p in BACKEND_DOCS if p.exists()]
    docs += [p for p in MOBILE_DOCS if p.exists()]
    return docs


def _bash_blocks(text: str) -> list[str]:
    """Fenced ```bash blocks only.

    Output samples are fenced bare, so a panel that happens to contain
    the word `motodiag` is not mistaken for a command claim.
    """
    return re.findall(r"```bash\n(.*?)```", text, re.S)


def _motodiag_invocations(text: str) -> list[tuple[str, list[str]]]:
    """Every `motodiag ...` line inside a bash block, as (raw, tokens)."""
    out: list[tuple[str, list[str]]] = []
    for block in _bash_blocks(text):
        for raw in block.splitlines():
            line = raw.strip()
            if line.startswith("#") or not line.startswith("motodiag"):
                continue
            line = line.split("#", 1)[0].strip()  # trailing comment
            line = line.split("|", 1)[0].strip()  # piped
            line = line.rstrip("\\").strip()      # line continuation
            out.append((line, line.split()[1:]))
    return out


def _resolve(tokens: list[str]) -> tuple[bool, str]:
    """Walk tokens through the Click registry.

    Reads `cli.commands` rather than scraping `--help`, so reformatting
    help output cannot break this test.
    """
    node: click.Command = cli
    walked: list[str] = []
    for tok in tokens:
        if tok.startswith("-"):
            break  # a flag; the command path ended
        if tok.startswith("<") or tok.startswith("$"):
            break  # documentation placeholder, not a name
        commands = getattr(node, "commands", None)
        if not commands:
            break  # node is a leaf; remaining tokens are arguments
        if tok not in commands:
            if walked:
                return False, (
                    f"`{' '.join(walked)}` has no subcommand {tok!r}"
                )
            return False, f"no top-level command {tok!r}"
        node = commands[tok]
        walked.append(tok)
    return True, ""


def _normalise(path: str) -> str:
    """Collapse ids and path params so a concrete URL matches its route."""
    parts = []
    for seg in path.split("/"):
        if seg.isdigit() or (seg.startswith("{") and seg.endswith("}")):
            parts.append("*")
        else:
            parts.append(seg)
    return "/".join(parts)


@pytest.fixture(scope="module")
def schema_paths() -> set[str]:
    spec = create_app().openapi()
    return {_normalise(p) for p in spec["paths"]}


class TestDocumentedCommandsExist:
    """A doc naming a command the CLI does not have is a lie a reader
    discovers by typing it."""

    def test_at_least_one_doc_was_found(self):
        """Guards the guard: a path typo here would silently pass
        everything below by iterating an empty list."""
        docs = _user_docs()
        assert len(docs) >= 8, f"only found {[d.name for d in docs]}"

    def test_commands_resolve(self):
        failures: list[str] = []
        for doc in _user_docs():
            text = doc.read_text(encoding="utf-8")
            for raw, tokens in _motodiag_invocations(text):
                ok, why = _resolve(tokens)
                if not ok:
                    rel = doc.relative_to(REPO_ROOT.parent)
                    failures.append(f"{rel}: `{raw}` — {why}")
        assert not failures, (
            "documented commands that do not exist:\n  "
            + "\n  ".join(failures)
        )

    def test_the_guard_would_catch_a_rename(self):
        """A guard nobody has seen fail is a guard nobody should trust."""
        ok, why = _resolve(["shop", "customer", "add"])
        assert ok, why
        ok, why = _resolve(["shop", "customer", "adds"])
        assert not ok and "adds" in why


class TestDocumentedRoutesExist:
    def test_v1_paths_resolve(self, schema_paths):
        failures: list[str] = []
        pattern = re.compile(r"/v1/[A-Za-z0-9_{}/-]+")
        for doc in _user_docs():
            text = doc.read_text(encoding="utf-8")
            for match in pattern.findall(text):
                path = match.rstrip("/.,;:)`")
                if _normalise(path) not in schema_paths:
                    rel = doc.relative_to(REPO_ROOT.parent)
                    failures.append(f"{rel}: {path}")
        assert not failures, (
            "documented routes not in the OpenAPI schema:\n  "
            + "\n  ".join(sorted(set(failures)))
        )

    def test_the_route_guard_would_catch_a_rename(self, schema_paths):
        assert _normalise("/v1/reports/session/1/share") in schema_paths
        assert _normalise("/v1/reports/sessions/1/share") not in schema_paths


class TestNoWindowsOnlyInstructions:
    """Both READMEs shipped `.venv/Scripts/activate` and PowerShell
    windows long after macOS became the only host. A reader following
    them failed on line one."""

    @pytest.mark.parametrize("needle", [
        r"\Scripts\\",
        "/Scripts/activate",
        "PowerShell",
        ".venv\\",
    ])
    def test_no_windows_paths_in_user_docs(self, needle):
        offenders = [
            str(doc.relative_to(REPO_ROOT.parent))
            for doc in _user_docs()
            if needle in doc.read_text(encoding="utf-8")
        ]
        assert not offenders, f"{needle!r} still in {offenders}"


class TestVersionHasOneSourceOfTruth:
    """`motodiag --version` reported 0.1.0 against a 0.6.0 package
    because the version was a literal in two places besides
    pyproject.toml. A version number that lies routes a bug report to
    the wrong release."""

    def test_package_version_matches_installed_metadata(self):
        from importlib.metadata import version as pkg_version

        from motodiag import __version__
        assert __version__ == pkg_version("motodiag")

    def test_settings_do_not_carry_a_second_literal(self):
        from motodiag import __version__
        from motodiag.core.config import Settings
        assert Settings().version == __version__

    def test_the_api_reports_the_same_version(self):
        from fastapi.testclient import TestClient

        from motodiag import __version__
        client = TestClient(create_app())
        assert client.get("/v1/version").json()["package"] == __version__


@pytest.mark.skipif(
    not (MOBILE_ROOT / "docs" / "app-store-listing.md").exists(),
    reason="mobile repo not checked out alongside",
)
class TestAppStoreListingFitsApplesLimits:
    """App Store Connect rejects over-length fields at upload. Finding
    that out after a build-and-upload cycle is a wasted round trip, and
    the limits are trivially checkable here."""

    LIMITS = {"name": 30, "subtitle": 30, "promotional": 170,
              "keywords": 100, "description": 4000}

    @pytest.fixture(scope="class")
    def listing(self) -> str:
        return (MOBILE_ROOT / "docs" / "app-store-listing.md").read_text(
            encoding="utf-8",
        )

    def _blocks(self, listing: str) -> list[str]:
        return [b.strip() for b in re.findall(r"```\n(.*?)\n```", listing, re.S)]

    def test_name_and_subtitle(self, listing):
        name = re.search(r"\*\*Name\*\* \| `([^`]+)`", listing).group(1)
        subtitle = re.search(r"\*\*Subtitle\*\* \| `([^`]+)`", listing).group(1)
        assert len(name) <= self.LIMITS["name"], f"name is {len(name)}"
        assert len(subtitle) <= self.LIMITS["subtitle"], (
            f"subtitle is {len(subtitle)}"
        )

    def test_promotional_description_and_keywords(self, listing):
        promo, description, keywords = self._blocks(listing)[:3]
        assert len(promo) <= self.LIMITS["promotional"], len(promo)
        assert len(description) <= self.LIMITS["description"], len(description)
        assert len(keywords) <= self.LIMITS["keywords"], len(keywords)

    def test_stated_counts_are_the_real_counts(self, listing):
        """The doc prints its own character counts. All three were wrong
        when first written — stating a count you did not compute is how
        you end up over the limit while believing you are under it."""
        promo, description, keywords = self._blocks(listing)[:3]
        stated = [
            int(n.replace(",", ""))
            for n in re.findall(r"^\((\d[\d,]*) / [\d,]+\)$", listing, re.M)
        ]
        assert stated == [len(promo), len(description), len(keywords)], (
            f"doc claims {stated}, actual "
            f"{[len(promo), len(description), len(keywords)]}"
        )

    def test_keywords_waste_no_characters_on_spaces(self, listing):
        keywords = self._blocks(listing)[2]
        assert " " not in keywords, "Apple counts spaces in the keyword field"


@pytest.mark.skipif(
    not (MOBILE_ROOT / "ios" / "MotoDiag" / "Info.plist").exists(),
    reason="mobile repo not checked out alongside",
)
class TestPermissionStringsMatchTheBinary:
    """The listing documents the permission prompts a user will read.
    It drifted immediately on first writing — the strings in the doc
    were invented, and the plist declared a location permission for a
    feature that does not exist."""

    @pytest.fixture(scope="class")
    def plist_keys(self) -> set[str]:
        text = (MOBILE_ROOT / "ios" / "MotoDiag" / "Info.plist").read_text(
            encoding="utf-8",
        )
        return set(re.findall(r"<key>(NS\w*UsageDescription)</key>", text))

    def test_listing_documents_every_declared_permission(self, plist_keys):
        listing = (MOBILE_ROOT / "docs" / "app-store-listing.md").read_text(
            encoding="utf-8",
        )
        missing = sorted(k for k in plist_keys if k not in listing)
        assert not missing, (
            f"Info.plist declares {missing} but the listing does not "
            "document what the user will be asked"
        )

    def test_no_location_permission_is_declared(self, plist_keys):
        """No location dependency is installed and no location API is
        called. A declared-but-unused permission is a review question
        with no good answer."""
        assert not [k for k in plist_keys if "Location" in k]
