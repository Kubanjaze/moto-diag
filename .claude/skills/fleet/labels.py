#!/usr/bin/env python3
"""The fleet's state words on GitHub: the eleven labels, made once.

    labels.py            # list what exists, make what is missing
    labels.py --check    # list only; exit 1 if any is missing

An existing label is reused untouched: never `--force`, which would
overwrite its colour and description (the operator's pre-approval (b) for
Phase 387: "if a GitHub label already exists, reuse it"). Run under the
operator's own `gh` login, a stand-in until the fleet has its own identity
(F214).
"""
from __future__ import annotations

import json
import subprocess
import sys

from rank_call import Runner, gh

#: (name, colour, what it means), in the order a phase passes through them.
LABELS = (
    ("mission", "1d76db", "A phase the Admiral has opened; its ROADMAP row is in progress"),
    ("step0:done", "c5def5", "Step 0 report written; the Captain writes v1.0"),
    ("plan:needs-review", "fbca04", "A v1.0 waiting for the Executive Officer"),
    ("plan:approved", "0e8a16", "The Executive Officer approved the v1.0"),
    ("build:open", "5319e7", "The Chief Engineer is building"),
    ("review:open", "d4c5f9", "A PR waiting for the Red Team"),
    ("review:clear", "c2e0c6", "The Red Team found nothing that stops the merge"),
    ("merge:needs-review", "f9d0c4", "Waiting for the Quartermaster's checks and merge"),
    ("needs-admiral", "b60205", "Needs the operator: a decision only the Admiral makes"),
    ("needs-hands", "e99695", "Needs the operator's hands: a login, a device, a portal"),
    ("merged", "6f42c1", "Merged and closed out"),
)


def existing(run: Runner) -> list[str]:
    r = gh(["label", "list", "--limit", "200", "--json", "name"], run=run)
    if r.returncode != 0:
        raise SystemExit(f"gh label list failed: {r.stderr.strip()}")
    return [x["name"] for x in json.loads(r.stdout)]


def ensure(run: Runner = subprocess.run, make: bool = True, out=print) -> int:
    before = existing(run)
    out(f"before: {len(before)} labels: {', '.join(before)}")
    for name, colour, desc in LABELS:
        if name in before:
            out(f"  reused: {name}")
        elif make:
            r = gh(["label", "create", name, "--color", colour, "--description", desc], run=run)
            out(f"  {'made' if r.returncode == 0 else 'FAILED'}: {name}"
                + ("" if r.returncode == 0 else f" ({r.stderr.strip()[:120]})"))
        else:
            out(f"  missing: {name}")
    after = existing(run)
    missing = [n for n, _, _ in LABELS if n not in after]
    out(f"after: {len(after)} labels; the fleet's {len(LABELS)}: "
        + ("all present" if not missing else f"missing {', '.join(missing)}"))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(ensure(make="--check" not in sys.argv[1:]))
