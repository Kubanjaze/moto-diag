"""Phase 402's mutations, and the run of the new tests against master's code.

Run from the repository root:
`.venv/bin/python docs/phases/in_progress/402_mutate.py` (ROOT is three
levels up from in_progress/ or completed/). Output goes to stdout; the
phase keeps it in `402_mutate.out`.

Every mutation is applied to a **copy**: `src/`, `tests/conftest.py`,
`tests/support/`, the phase's test file and the deploy skill's folder (the
conftest reads `live.py`) are copied to a temporary
folder, the copy is edited, and the tests run there with the copy's `src`
first on `PYTHONPATH` (the venv's editable install is a `.pth` path, which
comes after it). The checkout is never written. Each edit's text must occur
once. Exits 1 if any mutation stays green.

`--old` instead runs the new tests against master's four changed modules
(`git show master:<path>`). Master has none of the names the tests import,
so the copy appends the smallest stand-ins that keep master's behaviour:
the six field names, the mint message (master never sends it), and a
`startup_public_url_problems` that is master's direct call. It prints each
test's outcome and the counts.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]

CFG = "src/motodiag/core/config.py"
PU = "src/motodiag/core/public_url.py"
SV = "src/motodiag/cli/serve.py"
SH = "src/motodiag/api/routes/share.py"
T = "tests/test_phase402_share_links_off.py"
CHANGED = (CFG, PU, SV, SH)

MUTATIONS = [
    ("M1 the switch ignored at mint",
     [(SH, "    if not get_settings().share_links_enabled:\n"
           "        raise HTTPException",
       "    if False:\n        raise HTTPException")]),
    ("M2 the switch ignored at open",
     [(SH, "    if not get_settings().share_links_enabled:\n"
           "        return _message_response(",
       "    if False:\n        return _message_response(")]),
    ("M3 the open route looks the token up before refusing",
     [(SH, "    if not get_settings().share_links_enabled:\n"
           "        return _message_response(",
       "    resolve_share(token, db_path=db_path)\n"
       "    if not get_settings().share_links_enabled:\n"
       "        return _message_response(")]),
    ("M3b a refused open still records a view",
     [(SH, "    if not get_settings().share_links_enabled:\n"
           "        return _message_response(",
       "    _st, _sh = resolve_share(token, db_path=db_path)\n"
       "    if _sh is not None:\n"
       "        record_view(int(_sh['id']), db_path=db_path)\n"
       "    if not get_settings().share_links_enabled:\n"
       "        return _message_response(")]),
    ("M4 the start-up check still runs with the switch off",
     [(PU, "    if not settings.share_links_enabled:\n        return []\n", "")]),
    ("M5 the new function returns an empty list with the switch on",
     [(PU, "    return check_public_base_url(settings.public_base_url, settings.env)",
       "    return []")]),
    ("M6 the switch's default flipped to false",
     [(CFG, "    share_links_enabled: bool = True", "    share_links_enabled: bool = False")]),
    ("M7 the page ignored",
     [(CFG, "        if not page:\n            return self\n",
       "        return self\n")]),
    ("M8 a field given on its own overridden by the page",
     [(CFG, "            if name not in given:\n", "            if True:\n")]),
    ("M9 serve prints nothing when the check is skipped",
     [(SV, '                "MOTODIAG_PUBLIC_BASE_URL is not checked.",\n',
       '                "",\n')]),
    ("M10 serve calls the old check directly again",
     [(SV, "        url_problems = startup_public_url_problems(settings)",
       "        from motodiag.core.public_url import check_public_base_url\n"
       "        url_problems = check_public_base_url(\n"
       "            settings.public_base_url, settings.env)")]),
    ("M11 the mint refuses after the ownership check",
     [(SH, "    if not get_settings().share_links_enabled:\n"
           "        raise HTTPException(status_code=403, detail=SHARE_LINKS_OFF_MESSAGE)\n",
       ""),
      (SH, "    share = create_share(",
       "    if not get_settings().share_links_enabled:\n"
       "        raise HTTPException(status_code=403, detail=SHARE_LINKS_OFF_MESSAGE)\n"
       "    share = create_share(")]),
    ("M12 the mint's 403 is not declared",
     [(SH, "    responses={\n        403: {\"description\": SHARE_LINKS_OFF_MESSAGE},\n    },\n",
       "")]),
]

#: Appended to master's modules for `--old`: names only, master's behaviour.
OLD_STANDINS = {
    CFG: '\nSTRIPE_RETURN_URL_FIELDS = (\n    "checkout_success_url",\n'
         '    "checkout_cancel_url",\n    "billing_portal_return_url",\n'
         '    "invoice_payment_return_url",\n    "connect_return_url",\n'
         '    "connect_refresh_url",\n)\n',
    PU: "\n\ndef startup_public_url_problems(settings):\n"
        "    return check_public_base_url(settings.public_base_url, settings.env)\n",
    SH: '\nSHARE_LINKS_OFF_MESSAGE = (\n    "Share links are switched off for now. "\n'
        '    "You can still send the report as a PDF."\n)\n',
}


def make_copy() -> pathlib.Path:
    work = pathlib.Path(tempfile.mkdtemp(prefix="402_mutate_"))
    shutil.copytree(ROOT / "src", work / "src",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (work / "tests").mkdir()
    shutil.copy(ROOT / "tests" / "conftest.py", work / "tests" / "conftest.py")
    shutil.copytree(ROOT / "tests" / "support", work / "tests" / "support",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / T, work / T)
    # tests/conftest.py asks the deploy skill's live.py where live is (382).
    shutil.copytree(ROOT / ".claude" / "skills" / "deploy",
                    work / ".claude" / "skills" / "deploy",
                    ignore=shutil.ignore_patterns("__pycache__"))
    return work


def run(work: pathlib.Path, *extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(work / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "-p", "no:xdist", "-o", "addopts=", "--rootdir", str(work), *extra, T],
        cwd=work, capture_output=True, text=True, env=env,
    )


def check_copy_is_imported(work: pathlib.Path) -> None:
    env = dict(os.environ, PYTHONPATH=str(work / "src"))
    out = subprocess.run(
        [sys.executable, "-B", "-c", "import motodiag; print(motodiag.__file__)"],
        cwd=work, capture_output=True, text=True, env=env,
    ).stdout.strip()
    assert out.startswith(str(work)), f"the copy is not what is imported: {out}"


def mutate(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    work = make_copy()
    try:
        check_copy_is_imported(work)
        assert run(work, "-x").returncode == 0, "not green before mutating"
        survivors = []
        for name, edits in chosen:
            originals: dict[str, str] = {}
            try:
                for rel, old, new in edits:
                    path = work / rel
                    originals.setdefault(rel, path.read_text())
                    current = path.read_text()
                    assert current.count(old) == 1, \
                        f"{name}: the text occurs {current.count(old)} times in {rel}"
                    path.write_text(current.replace(old, new))
                code = run(work, "-x").returncode
            finally:
                for rel, text in originals.items():
                    (work / rel).write_text(text)
            verdict = "red" if code != 0 else "GREEN (survived)"
            print(f"{name}: {verdict}", flush=True)
            if code == 0:
                survivors.append(name)
        assert run(work, "-x").returncode == 0, "not green after restoring"
        print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
        return 1 if survivors else 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def old() -> int:
    work = make_copy()
    try:
        for rel in CHANGED:
            text = subprocess.run(
                ["git", "show", f"master:{rel}"], cwd=ROOT,
                capture_output=True, text=True, check=True,
            ).stdout
            (work / rel).write_text(text + OLD_STANDINS.get(rel, ""))
        check_copy_is_imported(work)
        result = run(work, "-rA")
        lines = [ln for ln in result.stdout.splitlines()
                 if ln.startswith(("PASSED ", "FAILED ", "ERROR "))]
        for ln in sorted(lines):
            print(ln.split(" - ")[0])
        print(result.stdout.strip().splitlines()[-1])
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--old"]:
        sys.exit(old())
    sys.exit(mutate(sys.argv[1:]))
