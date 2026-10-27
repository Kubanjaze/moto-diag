"""Phase 392 — F227: the fleet service's open-file limit.

Systemd's default soft limit is 1024; the fleet's service ran at it, and in
391's emptied-handoff trial a test worker raised "Too many open files". At
392's Step 0 one xdist worker in the fence peaked at 793 open files
(`docs/phases/in_progress/392_fd_probe.py`). The operator set the unit's
limit (K51): 1048576. The unit's rule is held by
`tests/test_phase388_service_contract.py` ("nofile"); here, the known-bad
case: a planted xdist run under a small limit loses its worker to the
limit, and the same run under the operator's number passes.
"""
from __future__ import annotations

import resource
import subprocess
import sys

import pytest

PLANTED = '''
import os, tempfile

def test_holds_many_files_open():
    d = tempfile.mkdtemp()
    held = [open(os.path.join(d, str(i)), "w") for i in range(300)]
    assert len(held) == 300
'''


def run_under(tmp_path, soft: int) -> subprocess.CompletedProcess:
    (tmp_path / "test_planted.py").write_text(PLANTED)
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    hard = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    cap = soft if hard == resource.RLIM_INFINITY else min(soft, hard)

    def limit():
        resource.setrlimit(resource.RLIMIT_NOFILE, (cap, hard))

    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-n", "2", "-p",
                           "no:cacheprovider", "-c", str(tmp_path / "pytest.ini"),
                           "--rootdir", str(tmp_path), str(tmp_path / "test_planted.py")],
                          capture_output=True, text=True, cwd=tmp_path, preexec_fn=limit,
                          timeout=300)


def test_a_planted_run_under_a_small_limit_runs_out(tmp_path):
    r = run_under(tmp_path, 256)
    assert r.returncode != 0
    assert "Too many open files" in r.stdout + r.stderr


def test_the_same_run_under_the_operators_limit_passes(tmp_path):
    if resource.getrlimit(resource.RLIMIT_NOFILE)[1] < 1024:
        pytest.fail("control: this machine's hard limit is below 1024")
    r = run_under(tmp_path, 1048576)
    assert r.returncode == 0, r.stdout[-800:]
