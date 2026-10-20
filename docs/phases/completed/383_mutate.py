"""Phase 383's mutations: each breaks one thing the phase built, and the check beside it must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/383_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 381's and 382's
harness: exact strings (each must occur once), the check run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`R` the regression line (F206), `S` the server's writes (F208), `M` media
paths and migration 087 (F205).
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

CHECK = ".claude/skills/closeout/closeout_check.py"
REGSH = ".claude/skills/closeout/regression.sh"
DEPLOY = ".claude/skills/deploy/deploy.py"
VIDEOS = "src/motodiag/api/routes/videos.py"
PHOTOS = "src/motodiag/api/routes/photos.py"
TRANSCRIPTS = "src/motodiag/api/routes/transcripts.py"
SWEEP = "src/motodiag/media/audio_sweep.py"
PIPELINE = "src/motodiag/media/transcript_pipeline.py"
WORKER = "src/motodiag/media/analysis_worker.py"
MIGRATIONS = "src/motodiag/core/migrations.py"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


REG = pytest("tests/test_phase383_regression_outcome.py")
SRV = pytest("tests/test_phase383_server_writes.py")
MEDIA = pytest("tests/test_phase383_media_paths.py")
VAPI = pytest("tests/test_phase191b_videos_api.py")

MUTATIONS = [
    ("R1 the failures are not read", [(CHECK,
     'if (failed, errors, rc) != ("0", "0", "0"):', 'if (errors, rc) != ("0", "0"):')], REG),
    ("R2 the errors are not read", [(CHECK,
     'if (failed, errors, rc) != ("0", "0", "0"):', 'if (failed, rc) != ("0", "0"):')], REG),
    ("R3 the exit code is not read", [(CHECK,
     'if (failed, errors, rc) != ("0", "0", "0"):', 'if (failed, errors) != ("0", "0"):')], REG),
    ("R4 any named skip passes", [(CHECK,
     "        if (s.group(2), s.group(3)) not in EXPECTED_SKIPS:", "        if False:")], REG),
    ("R5 a skip is pinned by its reason alone", [(CHECK,
     "        if (s.group(2), s.group(3)) not in EXPECTED_SKIPS:",
     "        if s.group(3) not in {r for _, r in EXPECTED_SKIPS}:")], REG),
    ("R6 the skip count is not compared", [(CHECK,
     "    if named != int(skipped) and not unnamed_ok:", "    if False:")], REG),
    ("R7 the unnamed-skip exemption grows", [(CHECK,
     'A5_UNNAMED_SKIP_EXEMPT = frozenset({"382"})',
     'A5_UNNAMED_SKIP_EXEMPT = frozenset({"382", "383"})')], REG),
    ("R8 the writer prints a failing run as of record", [(CHECK,
     "    prefix = PREFIX if (rc, f, e) == (0, 0, 0) else FAILED_PREFIX",
     "    prefix = PREFIX")], REG),
    ("R9 the writer drops the skip lines", [(CHECK,
     "for k, where, why in _PYTEST_SKIP.findall(log_text)]", "for k, where, why in []]")], REG),
    ("R10 regression.sh prints its own line", [(REGSH,
     '"$PY" -B "$DIR/closeout_check.py" --format-regression "$STEM.log" "$HASH" "$WALL" "$CMD" "$RC" \\\n  || exit 2',
     'echo "Regression of record: $HASH"')], REG),
    ("R11 the legacy rule passes a failure", [(CHECK,
     '               and not re.search(r"\\b[1-9][\\d,]* (?:failed|errors?)\\b", ln)\n', "")], REG),
    ("R12 K18 reads the line without its outcome", [(DEPLOY,
     '    line, why = closeout_check.regression_record(log.read_text(encoding="utf-8"), phase)',
     '    line, why = closeout_check.regression_record(\n'
     '        log.read_text(encoding="utf-8").replace("5 failed", "0 failed")'
     '.replace("exit 1)", "exit 0)").replace("33 skipped", "0 skipped"), phase)')], REG),
    ("S1 the drift check masks nothing", [(DEPLOY,
     "    drift, aside = server_masked(diff(dump(bk), dump(db)), approved)",
     "    drift, aside = diff(dump(bk), dump(db)), []")], SRV),
    ("S2 the after-apply comparison masks nothing", [(DEPLOY,
     "    d, aside = server_masked(diff(dump(bk), dump(db)), approved)",
     "    d, aside = diff(dump(bk), dump(db)), []")], SRV),
    ("S3 verify-live masks nothing", [(DEPLOY,
     "        d, aside = server_masked(diff(dump(bk_copy), dump(live_copy)), _approved_exact(text))",
     "        d, aside = diff(dump(bk_copy), dump(live_copy)), []")], SRV),
    ("S4 every column of the table is masked", [(DEPLOY,
     "                if c in listed and c not in keep and row[i] != x[\"a\"][k][i]:",
     "                if c not in keep and row[i] != x[\"a\"][k][i]:")], SRV),
    ("S5 the column is masked in every table", [(DEPLOY,
     "        listed = SERVER_WRITES.get(t, frozenset())",
     '        listed = frozenset({"last_used_at"})')], SRV),
    ("S6 a field the approved diff names is masked", [(DEPLOY,
     "                if c in listed and c not in keep and row[i] != x[\"a\"][k][i]:",
     "                if c in listed and row[i] != x[\"a\"][k][i]:")], SRV),
    ("S7 an added row is dropped with the masked ones", [(DEPLOY,
     '        if changed or x["added"] or x["removed"]:', "        if changed:")], SRV),
    ("S8 verify-live does not say what it set aside", [(DEPLOY,
     '    if aside:\n        print(f"  set aside: {len(aside)} change(s) the running API writes "',
     '    if False:\n        print(f"  set aside: {len(aside)} change(s) the running API writes "')], SRV),
    ("M1 the video route stores the absolute path", [(VIDEOS,
     "stored_media_path(file_path, settings.data_dir), db_path=db_path,",
     "str(file_path), db_path=db_path,")], MEDIA),
    ("M2 the photo route stores the absolute path", [(PHOTOS,
     "stored_media_path(file_path, settings.data_dir),", "str(file_path),")], MEDIA),
    ("M3 the transcript route stores the absolute path", [(TRANSCRIPTS,
     "stored_media_path(audio_path, settings.data_dir),", "str(audio_path),")], MEDIA),
    ("M4 the video file route reads the stored path as is", [(VIDEOS,
     '            f"video id={video_id} not found"\n        )\n'
     '    file_path = resolve_media_path(row["file_path"], settings.data_dir)',
     '            f"video id={video_id} not found"\n        )\n'
     '    file_path = Path(row["file_path"])')], MEDIA),
    ("M5 the video ask route reads the stored path as is", [(VIDEOS,
     'not found")\n\n    file_path = resolve_media_path(row["file_path"], settings.data_dir)',
     'not found")\n\n    file_path = Path(row["file_path"])')], MEDIA),
    ("M6 the photo route reads the stored path as is", [(PHOTOS,
     '    file_path = resolve_media_path(row["file_path"], settings.data_dir)',
     '    file_path = Path(row["file_path"])')], MEDIA),
    ("M7 the transcript route reads the stored path as is", [(TRANSCRIPTS,
     '    audio_path = resolve_media_path(row["audio_path"], settings.data_dir)',
     '    audio_path = Path(row["audio_path"])')], MEDIA),
    ("M8 the sweep ignores its data folder", [(SWEEP,
     "    data_dir = data_dir or get_settings().data_dir",
     "    data_dir = get_settings().data_dir")], MEDIA),
    ("M9 the transcript pipeline ignores its data folder", [(PIPELINE,
     "resolve_media_path(stored, data_dir or get_settings().data_dir)",
     "resolve_media_path(stored, get_settings().data_dir)")], MEDIA),
    ("M10 the analysis worker ignores its data folder", [(WORKER,
     'video["file_path"], data_dir or get_settings().data_dir),',
     'video["file_path"], get_settings().data_dir),')], MEDIA),
    ("M11 the video route does not pass its data folder", [(VIDEOS,
     "run_analysis_pipeline, new_video_id, db_path, settings.data_dir,",
     "run_analysis_pipeline, new_video_id, db_path,")], VAPI),
    ("M12 the transcript route does not pass its data folder", [(TRANSCRIPTS,
     "run_extraction_pipeline, transcript_id, shop_id, db_path, settings.data_dir,",
     "run_extraction_pipeline, transcript_id, shop_id, db_path,")], MEDIA),
    ("M13 087 keeps the leading slash", [(MIGRATIONS,
     "SET file_path = substr(file_path, instr(file_path, '/videos/shop_') + 1)",
     "SET file_path = substr(file_path, instr(file_path, '/videos/shop_'))")], MEDIA),
    ("M14 087 leaves the photos", [(MIGRATIONS,
     "            UPDATE work_order_photos\n", "            UPDATE work_order_photos_x\n")], MEDIA),
    ("M15 087 leaves the transcripts", [(MIGRATIONS,
     "            UPDATE voice_transcripts\n", "            UPDATE voice_transcripts_x\n")], MEDIA),
]


def clear_caches() -> None:
    for base in (ROOT / "src", ROOT / "tests", ROOT / ".claude", ROOT / "scripts"):
        for cache in base.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals = {}
        try:
            for rel, old, new in edits:
                path = ROOT / rel
                originals.setdefault(rel, path.read_text())
                current = path.read_text()
                assert current.count(old) == 1, f"{name}: the text occurs {current.count(old)} times in {rel}"
                path.write_text(current.replace(old, new))
            code = run(command)
        finally:
            for rel, text in originals.items():
                (ROOT / rel).write_text(text)
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
