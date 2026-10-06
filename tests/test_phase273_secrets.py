"""Phase 273 — the test session never sees the operator's Stripe keys.

The operator's keys stay outside the repo, but a shell can export them
and Settings reads ``.env``. ``tests/conftest.py`` clears every Stripe
variable and blanks each Stripe setting before anything reads Settings.

Proof: a spawned pytest runs a planted test with a planted key in its
environment. Loaded with this suite's conftest, the planted test must not
find the key; run without it (the control), the same test must find it,
so the check is one that can fail.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from motodiag.core.config import Settings

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
PLANTED = "sk_test_" + "planted0must0never0be0seen"
PLANTED_SECRET = "whsec_" + "planted0must0never0be0seen"

PLANTED_TEST = textwrap.dedent(f'''
    import os
    from motodiag.core.config import reset_settings

    def test_the_planted_key_is_not_visible():
        s = reset_settings()
        seen = [s.stripe_api_key, s.stripe_webhook_secret, *os.environ.values()]
        assert {PLANTED!r} not in seen
        assert {PLANTED_SECRET!r} not in seen
        assert s.billing_provider == "fake"
''')


def _spawn(tmp_path: Path, with_conftest: bool) -> subprocess.CompletedProcess:
    test_file = tmp_path / "test_planted_stripe_key.py"
    test_file.write_text(PLANTED_TEST)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MOTODIAG_")}
    env.update({
        "MOTODIAG_STRIPE_API_KEY": PLANTED,
        "MOTODIAG_STRIPE_WEBHOOK_SECRET": PLANTED_SECRET,
        "STRIPE_API_KEY": PLANTED,
        "MOTODIAG_BILLING_PROVIDER": "stripe",
        "MOTODIAG_DB_PATH": str(tmp_path / "planted.db"),
        "PYTHONPATH": str(TESTS),
    })
    args = [sys.executable, "-m", "pytest", str(test_file), "-q", "-p", "no:cacheprovider",
            "-p", "no:xdist", "--rootdir", str(tmp_path), "-c", os.devnull]
    if with_conftest:
        args += ["-p", "conftest"]
    return subprocess.run(args, cwd=tmp_path, env=env, capture_output=True,
                          text=True, timeout=180)


def test_with_this_suites_conftest_the_planted_key_is_not_seen(tmp_path):
    proc = _spawn(tmp_path, with_conftest=True)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "1 passed" in proc.stdout


def test_the_control_without_it_the_planted_key_is_seen(tmp_path):
    proc = _spawn(tmp_path, with_conftest=False)
    assert proc.returncode == 1, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "1 failed" in proc.stdout
    assert "planted0must0never0be0seen" in proc.stdout


def test_a_stripe_value_in_an_env_file_does_not_reach_settings(tmp_path):
    """pydantic-settings reads the environment before `.env`; conftest has
    set every Stripe setting to "" there, so a `.env` value loses."""
    planted_env = tmp_path / "planted.env"
    planted_env.write_text(
        f"MOTODIAG_STRIPE_API_KEY={PLANTED}\n"
        f"MOTODIAG_STRIPE_WEBHOOK_SECRET={PLANTED_SECRET}\n"
        "MOTODIAG_BILLING_PROVIDER=stripe\n"
    )
    s = Settings(_env_file=str(planted_env))
    assert (s.stripe_api_key, s.stripe_webhook_secret, s.billing_provider) == (
        "", "", "fake")


def test_the_env_file_control_without_the_blanks_it_would_be_read(tmp_path, monkeypatch):
    planted_env = tmp_path / "planted.env"
    planted_env.write_text(f"MOTODIAG_STRIPE_API_KEY={PLANTED}\n")
    monkeypatch.delenv("MOTODIAG_STRIPE_API_KEY")
    assert Settings(_env_file=str(planted_env)).stripe_api_key == PLANTED
