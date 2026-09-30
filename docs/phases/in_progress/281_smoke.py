"""Phase 281's smoke calls: one live request per service, logged.

The operator's rule (2026-09-28): no live API call during the build except
one smoke call per service, logged. Each call goes through the app's own
command (Click's runner over the real CLI) against a scratch database, so
the call proves the real client. A tap on `core.outbound._open` records the
URL, the time (UTC), the HTTP status and the body's size, and keeps the body
for the fixture. The tap calls the real transport once and changes nothing.

Usage (from the repository root):
    .venv/bin/python docs/phases/in_progress/281_smoke.py OUT_DIR

Writes OUT_DIR/smoke_log.json and one body file per call. It refuses to run
if OUT_DIR already holds a log, so it cannot be re-run by accident.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CALLS = [
    ("nhtsa_recalls", ["advanced", "recall", "refresh", "--make", "PIAGGIO",
                       "--model", "MP3 500", "--year", "2020"]),
    ("nhtsa_vpic", ["advanced", "vin", "decode", "1HD1FRW177Y600001"]),
    ("ecb_daily", ["shop", "currency", "refresh"]),
]


def main(out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if (out / "smoke_log.json").exists():
        print(f"refusing: {out / 'smoke_log.json'} exists; the smoke calls were made")
        return 2
    scratch = Path(tempfile.mkdtemp(prefix="motodiag_smoke_")) / "smoke.db"
    os.environ["MOTODIAG_DB_PATH"] = str(scratch)

    from click.testing import CliRunner

    from motodiag.cli.main import cli
    from motodiag.core import outbound
    from motodiag.core.config import reset_settings

    reset_settings()
    real_open = outbound._open
    log: list[dict] = []

    def tap(url, headers, timeout):
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        status, body = real_open(url, headers, timeout)
        log.append({"url": url, "time_utc": started, "status": status,
                    "bytes": len(body), "user_agent": headers.get("User-Agent"),
                    "body": body})
        return status, body

    outbound._open = tap
    entries = []
    for name, args in CALLS:
        before = len(log)
        result = CliRunner().invoke(cli, args)
        calls = log[before:]
        for i, call in enumerate(calls):
            suffix = ".xml" if name.startswith("ecb") else ".json"
            body_file = out / f"{name}{'' if i == 0 else f'_{i}'}{suffix}"
            body_file.write_bytes(call.pop("body"))
            entries.append({"service": name, "command": "motodiag " + " ".join(args),
                            **call, "body_file": body_file.name,
                            "exit_code": result.exit_code,
                            "output": result.output})
        print(f"{name}: {len(calls)} request(s), exit {result.exit_code}")
    (out / "smoke_log.json").write_text(json.dumps(entries, indent=2) + "\n")
    print(json.dumps([{k: v for k, v in e.items() if k != "output"} for e in entries],
                     indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
