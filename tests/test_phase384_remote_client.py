"""Phase 384 — the Mac's side of the way in, `.claude/skills/deploy/remote.py`.

The SSH command never prompts and offers only the named key; a machine with
no way in refuses (exit 4) as live.py does; an operation that runs code on
the desktop names HEAD, and only a clean, pushed HEAD; a fetched file is
written only when what arrived hashes as the desktop said (the operator's
3A: the Mac commits it, under its own guards).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPLOY = ROOT / ".claude" / "skills" / "deploy"
sys.path.insert(0, str(DEPLOY))
spec = importlib.util.spec_from_file_location("remote384", DEPLOY / "remote.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


@pytest.fixture
def config(tmp_path):
    key = tmp_path / "motodiag_ops"
    key.write_text("stand-in, never read\n")
    cfg = tmp_path / "live.json"
    cfg.write_text(json.dumps({"live": None, "host": "desktop-76s9bqv",
                               "remote": {"ssh": "lilcu@motodiag-ops", "key": str(key)}}))
    return cfg


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True,
                   capture_output=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    (work / "docs" / "phases" / "in_progress").mkdir(parents=True)
    (work / "a.txt").write_text("a\n")
    _git(work, "add", "a.txt")
    _git(work, "commit", "-q", "-m", "a")
    _git(work, "push", "-q", "origin", "HEAD:refs/heads/phase-384")
    _git(work, "fetch", "-q", "origin")
    return work


@pytest.fixture
def sent(monkeypatch):
    calls: list[list[str]] = []
    monkeypatch.setattr(C, "run", lambda argv: calls.append(argv) or 0)
    return calls


def test_the_ssh_command_never_prompts_and_offers_one_key(config, sent):
    assert C.main(["status"], config=config) == 0
    argv = sent[0]
    opts = [argv[i + 1] for i, a in enumerate(argv) if a == "-o"]
    assert "BatchMode=yes" in opts and "IdentitiesOnly=yes" in opts
    assert f"IdentityFile={json.loads(config.read_text())['remote']['key']}" in opts
    assert "-T" in argv
    assert argv[-2:] == ["lilcu@motodiag-ops", "status"]


@pytest.mark.parametrize("entry", [
    {"live": None, "host": "desktop-76s9bqv"},
    {"live": None, "remote": {"ssh": "lilcu@motodiag-ops"}},
    {"live": None, "remote": {"ssh": "lilcu@motodiag-ops", "key": "/nonexistent/key"}},
])
def test_no_way_in_refuses_with_exit_4(entry, tmp_path, sent):
    cfg = tmp_path / "live.json"
    cfg.write_text(json.dumps(entry))
    assert C.main(["status"], config=cfg) == C.REFUSED == 4
    assert sent == []


def test_a_missing_config_refuses(tmp_path, sent):
    assert C.main(["status"], config=tmp_path / "absent.json") == 4
    assert sent == []


def test_an_operation_on_code_names_the_pushed_head(config, repo, sent):
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    assert C.main(["dryrun", "384"], repo=repo, config=config) == 0
    assert sent[0][-1] == f"dryrun 384 {head}"


def test_a_dirty_tree_refuses(config, repo, sent):
    (repo / "stray.txt").write_text("x\n")
    assert C.main(["apply-live", "384"], repo=repo, config=config) == 4
    assert sent == []


def test_an_unpushed_head_refuses(config, repo, sent):
    (repo / "b.txt").write_text("b\n")
    _git(repo, "add", "b.txt")
    _git(repo, "commit", "-q", "-m", "b")
    assert C.main(["live-check", "384"], repo=repo, config=config) == 4
    assert sent == []


def test_an_operation_without_code_adds_nothing(config, sent):
    C.main(["backup", "pre384proof"], config=config)
    assert sent[0][-1] == "backup pre384proof"


def _reply(monkeypatch, name, text, sha=None):
    body = json.dumps({"name": name, "text": text,
                       "sha256": sha or hashlib.sha256(text.encode()).hexdigest()})
    monkeypatch.setattr(C, "capture", lambda argv: (0, body))


def test_fetch_writes_on_an_equal_sha256(config, repo, monkeypatch, capsys):
    _reply(monkeypatch, "384_dryrun_diff.md", "the diff\n")
    assert C.main(["fetch", "384", "dryrun"], repo=repo, config=config) == 0
    f = repo / "docs" / "phases" / "in_progress" / "384_dryrun_diff.md"
    assert f.read_text() == "the diff\n"
    out = capsys.readouterr().out
    sha = hashlib.sha256(b"the diff\n").hexdigest()
    assert f"desktop sha256: {sha}" in out and f"arrived sha256: {sha}" in out


def test_fetch_refuses_an_unequal_sha256(config, repo, monkeypatch):
    _reply(monkeypatch, "384_dryrun_diff.md", "the diff\n", sha="0" * 64)
    assert C.main(["fetch", "384", "dryrun"], repo=repo, config=config) == 1
    assert not (repo / "docs" / "phases" / "in_progress" / "384_dryrun_diff.md").exists()


def test_fetch_refuses_a_file_it_did_not_ask_for(config, repo, monkeypatch):
    _reply(monkeypatch, "../../CLAUDE.md", "x\n")
    assert C.main(["fetch", "384", "dryrun"], repo=repo, config=config) == 1
    assert not (repo / "CLAUDE.md").exists()


def test_the_desktops_exit_comes_back(config, monkeypatch):
    monkeypatch.setattr(C, "run", lambda argv: 3)
    assert C.main(["backups"], config=config) == 3
