"""Phase 209 — does the thing we hand people actually work?

Every other test in this suite runs against the source tree, where
`PROJECT_ROOT` resolves correctly, the data files are on disk, and the
dev virtualenv has every optional extra installed. 4,879 of them passed
while `pip install motodiag` produced a CLI that could not start:

    $ motodiag --version
    ModuleNotFoundError: No module named 'fastapi'

Four defects hid in that gap — an eager import of an optional extra, a
data directory that resolved inside the virtualenv, a hand-maintained
package-data list missing a knowledge base, and seed data that lived
outside the package entirely so `db init` loaded nothing and still
reported success.

So this file does the only thing that could have caught them: it builds
the wheel, installs it into a throwaway virtualenv **with no extras**,
and runs the product.

It is slow (roughly a minute) and deselectable with `-m "not slow"`. A
guard that is routinely skipped is not running — if this starts getting
skipped in practice, that is the thing to fix, not the runtime.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import re
import venv
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_PKG = REPO_ROOT / "src" / "motodiag"

pytestmark = pytest.mark.slow


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=900, **kw,
    )


@pytest.fixture(scope="module")
def wheel(tmp_path_factory) -> Path:
    """Build a real wheel from the working tree."""
    out = tmp_path_factory.mktemp("dist")
    proc = _run([sys.executable, "-m", "build", "--wheel", "--outdir", str(out)],
                cwd=str(REPO_ROOT))
    if proc.returncode != 0:
        pytest.skip(f"wheel build unavailable: {proc.stderr[-400:]}")
    wheels = list(out.glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"
    return wheels[0]


@pytest.fixture(scope="module")
def installed(wheel, tmp_path_factory):
    """A venv with the wheel and NOTHING else — no extras, no dev deps.

    `HOME` is redirected so the installed copy writes its user data
    somewhere disposable instead of the real home directory.
    """
    env_dir = tmp_path_factory.mktemp("cleanvenv")
    home = tmp_path_factory.mktemp("fakehome")
    venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)

    bindir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    pip = bindir / "pip"
    proc = _run([str(pip), "install", str(wheel)])
    assert proc.returncode == 0, proc.stderr[-2000:]

    env = dict(os.environ)
    env["HOME"] = str(home)
    env.pop("MOTODIAG_DB_PATH", None)      # must not inherit the dev DB
    env.pop("XDG_DATA_HOME", None)
    env["COLUMNS"] = "100"

    def run_cli(*args: str) -> subprocess.CompletedProcess:
        return _run([str(bindir / "motodiag"), *args], env=env)

    def run_py(code: str) -> subprocess.CompletedProcess:
        return _run([str(bindir / "python"), "-c", code], env=env)

    return run_cli, run_py, home


class TestTheWheelCarriesEveryDataFile:
    """`[tool.setuptools.package-data]` is a hand-maintained list, and it
    drifted: `hardware.compat_data` was never declared, so every
    installed copy was missing the entire adapter-compatibility
    knowledge base while the source tree had it."""

    def test_every_non_python_source_file_ships(self, wheel):
        expected = {
            p.relative_to(REPO_ROOT / "src").as_posix()
            for p in SRC_PKG.rglob("*")
            if p.is_file()
            and p.suffix not in (".py", ".pyc")
            and "__pycache__" not in p.parts
        }
        with zipfile.ZipFile(wheel) as zf:
            shipped = set(zf.namelist())
        missing = sorted(expected - shipped)
        assert not missing, (
            f"{len(missing)} data file(s) in the source tree never reach "
            f"the wheel — declare them in [tool.setuptools.package-data]:"
            "\n  " + "\n  ".join(missing[:20])
        )

    def test_the_seed_knowledge_base_is_in_the_wheel(self, wheel):
        """The knowledge base IS the product; it used to live in the
        repo's `data/`, which is not shipped."""
        with zipfile.ZipFile(wheel) as zf:
            names = zf.namelist()
        issues = [n for n in names
                  if "knowledge/seed/knowledge/known_issues_" in n]
        assert len(issues) >= 60, f"only {len(issues)} known-issue files"
        assert any("seed/dtc_codes/generic.json" in n for n in names)


class TestTheInstalledCliStarts:
    """The whole CLI, not one command, failed to import on a base
    install — `cli.main` → `cli.apikey` → `motodiag.auth.__init__` →
    `auth.deps` → `fastapi`, which is in the `api` extra."""

    def test_version_runs_without_any_extra(self, installed):
        run_cli, _run_py, _home = installed
        proc = run_cli("--version")
        assert proc.returncode == 0, (
            "the installed CLI cannot start:\n" + proc.stderr[-1500:]
        )
        assert "motodiag v" in proc.stdout

    def test_fastapi_is_genuinely_absent(self, installed):
        """Proves the previous test is not passing because the venv
        happened to have FastAPI."""
        _run_cli, run_py, _home = installed
        proc = run_py("import fastapi")
        assert proc.returncode != 0
        assert "No module named 'fastapi'" in proc.stderr

    def test_help_lists_the_command_groups(self, installed):
        run_cli, _run_py, _home = installed
        proc = run_cli("--help")
        assert proc.returncode == 0, proc.stderr[-1000:]
        for group in ("diagnose", "garage", "hardware", "shop", "kb"):
            assert group in proc.stdout, f"{group} missing from --help"


class TestTheInstalledCliWorks:
    def test_db_init_actually_seeds(self, installed):
        """`db init` used to print 'Database ready.' over an empty
        knowledge base, because its loaders read the repo's unshipped
        `data/` directory and every guard silently found nothing."""
        run_cli, _run_py, _home = installed
        proc = run_cli("db", "init")
        assert proc.returncode == 0, proc.stderr[-1500:]
        assert "Seed data missing" not in proc.stdout
        assert "Loaded" in proc.stdout, (
            "db init reported success without loading anything:\n"
            + proc.stdout[-1200:]
        )

    def test_a_fault_code_resolves_from_the_seeded_database(self, installed):
        run_cli, _run_py, _home = installed
        run_cli("db", "init")
        proc = run_cli("code", "P0115")
        assert proc.returncode == 0, proc.stderr[-1000:]
        assert "Engine Coolant Temperature" in proc.stdout, proc.stdout[-800:]
        assert "No DB entry" not in proc.stdout, (
            "fell back to heuristics — the seed data did not load"
        )

    def test_the_adapter_knowledge_base_loads(self, installed):
        """The compat_data case: three JSON files that never shipped."""
        run_cli, _run_py, _home = installed
        run_cli("db", "init")
        seeded = run_cli("hardware", "compat", "seed", "--yes")
        assert seeded.returncode == 0, seeded.stderr[-1000:]
        listed = run_cli("hardware", "compat", "list")
        assert listed.returncode == 0, listed.stderr[-1000:]
        assert "No adapters match" not in listed.stdout


class TestTheApiStartsOnTheApiExtraAlone:
    """`media/photo_pipeline.py` imported Pillow at module level, and
    both `api/errors.py` and `routes/photos.py` import that module at
    load time — so `motodiag serve` died on
    `ModuleNotFoundError: No module named 'PIL'` before binding a port.
    Pillow is in the `vision` extra, so an `[api]` deployment could not
    serve anything at all."""

    @pytest.fixture(scope="class")
    def api_env(self, wheel, tmp_path_factory):
        env_dir = tmp_path_factory.mktemp("apivenv")
        home = tmp_path_factory.mktemp("apihome")
        venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
        bindir = env_dir / ("Scripts" if os.name == "nt" else "bin")
        proc = _run([str(bindir / "pip"), "install", f"{wheel}[api]"])
        if proc.returncode != 0:
            pytest.skip(f"api extra unavailable offline: {proc.stderr[-300:]}")
        env = dict(os.environ)
        env["HOME"] = str(home)
        env["MOTODIAG_DB_PATH"] = str(home / "api.db")
        return bindir, env

    def test_pillow_is_genuinely_absent(self, api_env):
        bindir, env = api_env
        proc = _run([str(bindir / "python"), "-c", "import PIL"], env=env)
        assert proc.returncode != 0, "vision extra leaked into [api]"

    def test_the_app_object_builds_without_pillow(self, api_env):
        """`create_app()` imports every router, so this exercises the
        whole import graph the server would.

        Counted via `openapi()["paths"]`, NOT `len(app.routes)`: FastAPI
        0.141 stopped flattening included routers into `app.routes` and
        stores an `_IncludedRouter` per call instead, so a route count
        taken from that attribute silently collapsed from 109 to 21
        between the pinned dev version (0.136) and the version a fresh
        install resolves. The OpenAPI path set is the contract; the
        `routes` list is an implementation detail that already moved
        once.
        """
        bindir, env = api_env
        proc = _run([str(bindir / "python"), "-c",
                     "from motodiag.api.app import create_app;"
                     "print(len(create_app().openapi()['paths']))"],
                    env=env)
        assert proc.returncode == 0, (
            "the API cannot import without Pillow:\n" + proc.stderr[-1500:]
        )
        assert int(proc.stdout.strip()) >= 75, (
            f"only {proc.stdout.strip()} paths registered"
        )

    def test_business_routes_are_present_not_just_docs(self, api_env):
        """The failure this guards against is subtle: an app that boots,
        answers /healthz, and serves nothing else."""
        bindir, env = api_env
        proc = _run([str(bindir / "python"), "-c",
                     "from motodiag.api.app import create_app;"
                     "p = create_app().openapi()['paths'];"
                     "print('/v1/sessions' in p, '/v1/kb/dtc' in p)"],
                    env=env)
        assert proc.stdout.strip() == "True True", proc.stdout + proc.stderr[-400:]

    def test_pdf_reports_name_the_missing_extra(self, api_env):
        """Phase 209B. `[api]` alone has no reportlab, so a PDF request must
        say which extra to install, the same way photo processing does."""
        bindir, env = api_env
        proc = _run([str(bindir / "python"), "-c",
                     "from motodiag.reporting.renderers import PdfReportRenderer\n"
                     "try:\n"
                     "    PdfReportRenderer()\n"
                     "except RuntimeError as e:\n"
                     "    print('NAMED', 'reports' in str(e), 'server' in str(e))"],
                    env=env)
        assert "NAMED True True" in proc.stdout, proc.stdout + proc.stderr[-500:]

    def test_photo_processing_names_the_missing_extra(self, api_env):
        """Degrading is only useful if the error says what to install."""
        bindir, env = api_env
        proc = _run([str(bindir / "python"), "-c",
                     "from motodiag.media.photo_pipeline import "
                     "normalize_photo, PillowUnavailableError\n"
                     "try:\n"
                     "    normalize_photo(b'not-an-image')\n"
                     "except PillowUnavailableError as e:\n"
                     "    print('NAMED', 'vision' in str(e))"], env=env)
        assert "NAMED True" in proc.stdout, proc.stdout + proc.stderr[-500:]


class TestUserDataDoesNotLiveInsideTheVirtualenv:
    """`PROJECT_ROOT` is four parents up from `core/config.py`, which is
    the repo root in a checkout and `<venv>/lib/python3.x` in an
    install. The default database resolved to
    `<venv>/lib/python3.14/data/motodiag.db` — destroyed by a venv
    rebuild, unwritable in a system install."""

    def test_db_path_is_a_user_data_directory(self, installed):
        _run_cli, run_py, home = installed
        proc = run_py(
            "from motodiag.core.config import get_settings;"
            "print(get_settings().db_path)"
        )
        assert proc.returncode == 0, proc.stderr[-800:]
        db_path = proc.stdout.strip()
        assert "site-packages" not in db_path
        assert "/lib/python" not in db_path
        assert str(home) in db_path, (
            f"db_path {db_path!r} is not under the user's home"
        )

    def test_the_installed_copy_knows_it_is_not_a_checkout(self, installed):
        _run_cli, run_py, _home = installed
        proc = run_py(
            "from motodiag.core.config import _running_from_source_checkout;"
            "print(_running_from_source_checkout())"
        )
        assert proc.stdout.strip() == "False"

    def test_a_source_checkout_still_uses_the_repo_data_dir(self):
        """Developers' existing databases must not move underfoot."""
        from motodiag.core.config import DATA_DIR, _running_from_source_checkout

        assert _running_from_source_checkout()
        assert DATA_DIR == REPO_ROOT / "data"

    def test_the_env_override_still_wins(self, installed, tmp_path):
        _run_cli, run_py, _home = installed
        target = tmp_path / "explicit.db"
        proc = _run([
            sys.executable, "-c",
            "from motodiag.core.config import get_settings;"
            "print(get_settings().db_path)",
        ], env={**os.environ, "MOTODIAG_DB_PATH": str(target)})
        assert proc.stdout.strip() == str(target)


class TestPackagingMetadataIsCoherent:
    def test_entry_point_is_declared(self, wheel):
        with zipfile.ZipFile(wheel) as zf:
            entry = next(n for n in zf.namelist()
                         if n.endswith("entry_points.txt"))
            body = zf.read(entry).decode()
        assert "motodiag = motodiag.cli.main:cli" in body

    def test_wheel_version_matches_the_package(self, wheel):
        from motodiag import __version__
        assert f"-{__version__}-" in wheel.name

    def test_base_dependencies_do_not_include_optional_frameworks(self):
        """The extras exist so a mechanic's CLI install stays small. If
        fastapi ever lands in the base list, that intent is gone and the
        lazy boundary in `auth/__init__` is pointless."""
        import tomllib

        with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
            cfg = tomllib.load(fh)
        base = " ".join(cfg["project"]["dependencies"]).lower()
        for pkg in ("fastapi", "uvicorn", "anthropic", "openai", "pillow"):
            assert pkg not in base, (
                f"{pkg} is a base dependency; it belongs in an extra"
            )

    def test_the_api_extra_still_declares_what_the_api_needs(self):
        import tomllib

        with open(REPO_ROOT / "pyproject.toml", "rb") as fh:
            cfg = tomllib.load(fh)
        api = " ".join(
            cfg["project"]["optional-dependencies"]["api"]
        ).lower()
        assert "fastapi" in api and "uvicorn" in api


class TestLazyAuthBoundaryHolds:
    """These run in-process and are fast — they catch a re-introduced
    eager import without waiting for a wheel build."""

    def test_auth_exports_resolve_without_importing_fastapi_first(self):
        import importlib

        mod = importlib.import_module("motodiag.auth")
        for name in ("get_current_user", "require_tier", "AuthedUser",
                     "tier_meets", "SUBSCRIPTION_TIERS"):
            assert getattr(mod, name) is not None

    def test_unknown_attributes_still_raise(self):
        import motodiag.auth as auth

        with pytest.raises(AttributeError):
            auth.definitely_not_a_real_export

    def test_the_cli_module_chain_has_no_top_level_fastapi_import(self):
        """The specific chain that broke: cli.main → cli.apikey →
        motodiag.auth. Asserted by source inspection, because in this
        process FastAPI is installed and an import would succeed."""
        for mod in ("cli/main.py", "cli/apikey.py", "auth/__init__.py",
                    "auth/api_key_repo.py"):
            text = (SRC_PKG / mod).read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                assert not stripped.startswith(
                    ("import fastapi", "from fastapi")
                ), f"{mod} imports fastapi at module level: {stripped!r}"


class TestTheServerRecipeIsTheWholeServer:
    """Phase 209B.

    Three hand-written copies of the server recipe -- the Dockerfile, the
    launch checklist and install.md's production line -- all said
    `motodiag[api,vision,push]`. That left out `ai`, the only extra declaring
    `anthropic` and `openai`, so a server built from any of them could not
    diagnose, run the vision sweep, answer a question or transcribe audio,
    with keys or without.

    The API's PDF routes also render with `reportlab`, which nothing declared.
    It reached the dev venv as a dependency of `xhtml2pdf` from the unrelated
    `export` extra -- and `reporting/renderers.py` said so outright:
    "reportlab is already a transitive dep (installed in the project venv)".

    This module's own tests covered a venv with no extras and one with
    `[api]`, and never the combination a server is actually installed with.
    """

    @pytest.fixture(scope="class")
    def server_env(self, wheel, tmp_path_factory):
        env_dir = tmp_path_factory.mktemp("servervenv")
        home = tmp_path_factory.mktemp("serverhome")
        venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
        bindir = env_dir / ("Scripts" if os.name == "nt" else "bin")
        proc = _run([str(bindir / "pip"), "install", f"{wheel}[server]"])
        if proc.returncode != 0:
            pytest.skip(f"server extra unavailable offline: {proc.stderr[-300:]}")
        env = dict(os.environ)
        env["HOME"] = str(home)
        env["MOTODIAG_DB_PATH"] = str(home / "server.db")
        return bindir, env

    def _py(self, server_env, code: str):
        bindir, env = server_env
        return _run([str(bindir / "python"), "-c", code], env=env)

    def test_the_ai_sdks_are_present(self, server_env):
        proc = self._py(server_env, "import anthropic, openai")
        assert proc.returncode == 0, (
            "a [server] install cannot call Claude or Whisper:\n"
            + proc.stderr[-800:]
        )

    def test_a_pdf_report_renders(self, server_env):
        """Renders real PDF bytes through the renderer the API's
        /reports/.../pdf routes use.

        The first draft of this test only constructed the renderer and was
        still named "renders" -- a name promising more than the body checked.
        """
        proc = self._py(server_env, (
            "from motodiag.reporting.renderers import PdfReportRenderer\n"
            "b = PdfReportRenderer(deterministic=True).render("
            "{'title': 'Packaging probe', 'sections': [{'heading': 'Vehicle', "
            "'rows': [('Make', 'Honda')]}]})\n"
            "import sys; sys.stdout.write(b[:5].decode('latin-1'))\n"
        ))
        assert proc.returncode == 0, (
            "a [server] install cannot render PDF reports:\n" + proc.stderr[-800:]
        )
        assert proc.stdout.startswith("%PDF-"), proc.stdout[:40]

    def test_the_api_builds_with_every_route(self, server_env):
        proc = self._py(server_env,
                        "from motodiag.api.app import create_app;"
                        "print(len(create_app().openapi()['paths']))")
        assert proc.returncode == 0, proc.stderr[-1500:]
        assert int(proc.stdout.strip()) >= 75


class TestEveryServerRecipeIsComplete:
    """Static and fast: no venv. Guards the recipes themselves, so the three
    copies can't drift apart again."""

    PYPROJECT = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    # Source files too: the photo pipeline's own error message recommended
    # `pip install 'motodiag[api,vision]'` -- an API with no AI -- and a
    # docs-only scan never saw it.
    RECIPE_FILES = [
        REPO_ROOT / "Dockerfile",
        REPO_ROOT / "README.md",
        REPO_ROOT / "docs" / "launch-checklist.md",
        REPO_ROOT / "docs" / "guide" / "install.md",
        *sorted(SRC_PKG.rglob("*.py")),
    ]
    RECIPE = re.compile(r"motodiag\[([a-z0-9_,\-]+)\]")

    def _extras(self) -> dict[str, list[str]]:
        section = re.search(
            r"^\[project\.optional-dependencies\]\s*$(.*?)(?=^\[(?!project\.optional)|\Z)",
            self.PYPROJECT, re.M | re.S,
        ).group(1)
        extras: dict[str, list[str]] = {}
        for name, body in re.findall(r"^([a-z0-9_\-]+)\s*=\s*\[(.*?)\]\s*$",
                                     section, re.M | re.S):
            extras[name] = re.findall(r'"([^"]+)"', body)
        return extras

    def _expand(self, names: set[str]) -> set[str]:
        """Follow self-references: `server` -> `motodiag[api,ai,...]`."""
        extras, seen, stack = self._extras(), set(), list(names)
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            for dep in extras.get(n, []):
                m = re.match(r"motodiag\[([^\]]+)\]", dep)
                if m:
                    stack.extend(x.strip() for x in m.group(1).split(","))
        return seen

    def test_a_server_extra_exists_and_is_complete(self):
        assert {"api", "ai", "vision", "push", "reports"} <= self._expand({"server"})

    def test_reportlab_is_declared_and_reaches_the_server(self):
        """Declared in its own extra, and pulled in by `server`.

        Not in `api`: reportlab requires Pillow, and Phase 209 made `[api]`
        deliberately Pillow-free. The first version of this phase put
        reportlab in `api`, and Phase 209's own `[api]` tests caught it.
        """
        extras = self._extras()
        assert any("reportlab" in d.lower() for d in extras.get("reports", []))
        assert "reports" in self._expand({"server"})

    def test_the_api_extra_stays_pillow_free_by_declaration(self):
        """reportlab and Pillow must not be declared directly in `api`."""
        api = " ".join(self._extras()["api"]).lower()
        assert "reportlab" not in api and "pillow" not in api

    def test_every_recipe_names_only_real_extras(self):
        real = set(self._extras())
        for path in self.RECIPE_FILES:
            for match in self.RECIPE.finditer(path.read_text(encoding="utf-8")):
                named = {x.strip() for x in match.group(1).split(",")}
                assert named <= real, f"{path.name}: unknown extra in {match.group(0)}"

    def test_no_recipe_installs_the_api_without_ai(self):
        """An API without the AI SDKs starts, answers /healthz, and then
        fails every diagnosis, sweep, question and transcription. It looks
        like a working server, which is what makes it dangerous."""
        for path in self.RECIPE_FILES:
            for match in self.RECIPE.finditer(path.read_text(encoding="utf-8")):
                named = self._expand({x.strip() for x in match.group(1).split(",")})
                if "api" in named:
                    assert "ai" in named, (
                        f"{path.name}: {match.group(0)} installs the API "
                        "without the AI SDKs"
                    )

    def test_the_dockerfile_installs_ffmpeg(self):
        """Unverified here -- Docker isn't installed on the machine that
        wrote this -- but the absence is certain, and it made every video
        upload 503 in a container."""
        text = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        assert re.search(r"apt-get install[^\n]*\bffmpeg\b", text)
