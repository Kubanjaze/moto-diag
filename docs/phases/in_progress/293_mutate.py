"""Phase 293's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/293_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 388's harness:
exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it.

Every test runs on temporary databases and PDFs made in the test; nothing
reads the live database.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

RT = "src/motodiag/api/routes/manuals.py"
RP = "src/motodiag/reference/manual_repo.py"
CK = "src/motodiag/manuals/checks.py"
RV = "src/motodiag/manuals/review.py"
RN = "src/motodiag/manuals/render.py"
UP = "src/motodiag/api/uploads.py"
SN = "src/motodiag/backup/snapshot.py"
TA = "src/motodiag/auth/terms_acceptance.py"
DP = ".claude/skills/deploy/deploy.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-p", "no:xdist", "-o", "addopts=", *args]


API = "tests/test_phase293_manuals_api.py"
REV = "tests/test_phase293_review.py"
RS = "tests/test_phase293_render_search.py"

MUTATIONS = [
    ("M1 the list route without the membership check", [(RT,
     "    require_shop_access(shop_id, user, db_path)\n    rows = manual_repo.list_manuals(",
     "    rows = manual_repo.list_manuals(")],
     pytest(API, "-k", "another_shop_reaches_nothing")),
    ("M2 the page route without the shop comparison", [(RT,
     '    manual = _manual_in_shop(shop_id, manual_id, db_path)\n    if manual["status"] != "approved":',
     '    manual = _uploaded_manual(manual_id, db_path)\n    if manual["status"] != "approved":')],
     pytest(API, "-k", "as_id_under_bs_path")),
    ("M3 the search finds a pending page", [(RP,
     "        \" AND m.status = 'approved'\"\n", "")],
     pytest(RS, "-k", "pending_manual_is_never_found")),
    ("M4 the search across shops", [(RP,
     '        " AND m.shop_id = ?"\n', ""), (RP,
     "params: list = [match, shop_id]", "params: list = [match]")],
     pytest(RS, "-k", "another_shops_page")),
    ("M5 the upload without manage_shop", [(RT,
     '    require_shop_access(shop_id, user, db_path, permission="manage_shop")\n    try:',
     "    require_shop_access(shop_id, user, db_path)\n    try:")],
     pytest(API, "-k", "tech_may_not_upload")),
    ("M6 no scanner lets a file through", [(RT,
     '    if scanned.status == "unavailable":', "    if False:")],
     pytest(API, "-k", "no_scanner_is_503")),
    ("M7 the infected branch removed", [(RT,
     '    if scanned.status == "infected":', "    if False:")],
     pytest(API, "-k", "infected")),
    ("M8 the %PDF- check removed", [(CK,
     "        if fin.read(len(PDF_MAGIC)) != PDF_MAGIC:\n            return [NOT_A_PDF]",
     "        fin.read(len(PDF_MAGIC))")],
     pytest("tests/test_phase293_checks.py", "-k", "bad_file")),
    ("M9 the JavaScript names dropped from the walk", [(CK,
     '    "/JavaScript": _JS, "/JS": _JS,\n', "")],
     pytest("tests/test_phase293_checks.py", "-k", "bad_file")),
    ("M10 the locked check removed", [(CK,
     '        if reader.is_encrypted and not reader.decrypt(""):\n            return [LOCKED]\n',
     "")],
     pytest("tests/test_phase293_checks.py", "-k", "bad_file")),
    ("M11 a file at the cap refused", [(UP,
     "        if total > limit_bytes:", "        if total >= limit_bytes:")],
     pytest(API, "-k", "cap_admits")),
    ("M12 the page images counted in the limit", [(RP,
     '"SELECT COALESCE(SUM(file_size_bytes), 0) FROM manual_references WHERE shop_id = ?",',
     '"SELECT COALESCE(SUM(file_size_bytes), 0) + (SELECT count(*) * 300000 FROM '
     'manual_pages p JOIN manual_references r ON r.id = p.manual_id WHERE r.shop_id = ?1) '
     'FROM manual_references WHERE shop_id = ?1",')],
     pytest(RS, "-k", "storage_used")),
    ("M13 the limit read from the uploader's own tier", [(RT,
     "        limit_bytes=storage.storage_limit_bytes(shop_id, db_path),",
     "        limit_bytes=storage.tier_storage_bytes(user.tier),")],
     pytest(API, "-k", "limit_is_the_shops_plan")),
    ("M14 the duplicate check dropped", [(RT,
     "    if same is not None:", "    if False:")],
     pytest(API, "-k", "same_file_again")),
    ("M15 the queue open to any signed-in user", [(RT,
     "    reviewer: AuthedUser = Depends(require_reviewer),\n"
     "    db_path: str = Depends(get_db_path),\n) -> list[ReviewQueueItem]:",
     "    reviewer: AuthedUser = Depends(get_current_user),\n"
     "    db_path: str = Depends(get_db_path),\n) -> list[ReviewQueueItem]:")],
     pytest(REV, "-k", "no_one_else")),
    ("M16 approval while rendering", [(RV,
     '    if manual["rendered_pages"] < (manual["page_count"] or 0):', "    if False:")],
     pytest(REV, "-k", "while_rendering")),
    ("M17 the flag leaves the manual approved", [(RV,
     '        manual_id, db_path=db_path, status="pending_review",\n',
     "        manual_id, db_path=db_path,\n")],
     pytest(API, "-k", "flag")),
    ("M18 manuals not backed up", [(SN,
     'MEDIA_DIRS = ("videos", "photos", "audio", "manuals")',
     'MEDIA_DIRS = ("videos", "photos", "audio")')],
     pytest("tests/test_phase293_backup_restore.py", "-k", "manifest")),
    ("M19 the page images backed up", [(SN,
     'MEDIA_DIRS = ("videos", "photos", "audio", "manuals")',
     'MEDIA_DIRS = ("videos", "photos", "audio", "manuals", "manual_pages")')],
     pytest("tests/test_phase293_backup_restore.py", "-k", "manifest")),
    ("M20 the terms left at 1.0", [(TA,
     'TERMS_VERSION = "1.1"', 'TERMS_VERSION = "1.0"')],
     pytest("tests/test_phase293_terms.py", "-k", "version_is_1_1")),
    ("M21 the render rewrites a page already on disk", [(RN,
     "            if row is not None and image.exists() and thumb.exists():\n"
     "                continue\n", "")],
     pytest(RS, "-k", "second_run")),
    ("M22 the FTS query unquoted", [(RP,
     "    return \" \".join('\"' + term.replace('\"', '\"\"') + '\"' for term in q.split())",
     "    return q.strip()")],
     pytest(RS, "-k", "near_query")),
    ("M23 the delete keeps the files", [(RT,
     "    storage.remove_manual_files(settings.data_dir, shop_id, manual_id)\n", "")],
     pytest(API, "-k", "delete_removes")),
    ("M24 a rejection without a reason accepted", [(RV,
     '    if decision in ("rejected", "taken_down") and reason is None:', "    if False:")],
     pytest(REV, "-k", "without_a_reason")),
    ("M25 dump() reads every table by rowid again", [(DP,
     "    if not (sql and _WITHOUT_ROWID.search(sql)):", "    if True:")],
     pytest("tests/test_phase293_deploy_without_rowid.py")),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude" / "skills" / "deploy"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def apply(rel: str, old: str, new: str, originals: dict) -> None:
    path = ROOT / rel
    originals.setdefault(rel, path.read_text(encoding="utf-8"))
    current = path.read_text(encoding="utf-8")
    assert current.count(old) == 1, f"the text occurs {current.count(old)} times in {rel}"
    path.write_text(current.replace(old, new), encoding="utf-8")


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0] + " ")
              or m[0].startswith(argv[0])]
    commands: list[list[str]] = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals: dict = {}
        try:
            for rel, old, new in edits:
                apply(rel, old, new, originals)
            code = run(command)
        finally:
            for rel, data in originals.items():
                (ROOT / rel).write_text(data, encoding="utf-8")
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
