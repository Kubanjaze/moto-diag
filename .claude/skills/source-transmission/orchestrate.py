#!/usr/bin/env python3
"""source-transmission orchestrator — Phase 257.

Runs the written procedure for one make at a time:

    census  (census.py, no model)
      -> source  (sandboxed, Subconscious GLM-5.3 Marathon: acquire + extract + classify)
      -> check   (entry_check.py, no model: rejects bad evidence)
      -> refute  (sandboxed, Opus, fresh context: re-opens every citation)
      -> summary (per-make file; stops alert)

**Why two routes.** The source stages read manuals and portals — long,
context-heavy work — so they run through Subconscious (`subc claude`),
whose gateway keeps a 3M-token context and compacts for us. That is the
operator's reason for the orchestrator. Refute and write stay on Opus.

The WRITE step — editing the lookup in the repository — is not done here.
It is done by Opus in the repository, one make per commit, from the refuted
batch this produces (plan D4). Every model stage runs in a fresh clone
under `sandbox-exec`; tests/test_phase257_sandbox_boundary.py proves the
profile.

Guards (plan D3) refuse rather than warn: a credential sent to another
route's host, the Subconscious gateway not being Subconscious, `--bare`
(skips hooks), and a call without an explicit `--model`. The first is not
hypothetical: the operator's first key file pointed the Anthropic token at
api.z.ai, caught only because the file failed to parse.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import sqlite3
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOME = pathlib.Path.home()
CLAUDE = HOME / ".local" / "bin" / "claude"
SUBC = pathlib.Path("/opt/homebrew/bin/subc")
SUBC_PROFILE = HOME / ".subconscious" / "profiles" / "default.env"
ANTHROPIC_TOKEN_FILE = HOME / ".config" / "motodiag" / "anthropic.env"
BUDGET_USD = 3.0                    # per call; Opus route only (see run_stage)
BLOCKED_STOP = 0.5                  # plan D5

ROUTES = {
    # Credential held by `subc login`; the orchestrator never reads the key.
    "subconscious": {"model": "subconscious/glm-5.3-marathon",
                     "host": "api.subconscious.dev"},
    # Credential from the operator's file, passed by environment only.
    "anthropic": {"model": "claude-opus-5-5", "host": "api.anthropic.com"},
}
SOURCE_ROUTE, REFUTE_ROUTE = "subconscious", "anthropic"
CREDENTIAL_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN",
                   "SUBCONSCIOUS_API_KEY", "ANTHROPIC_BASE_URL")


class GuardError(RuntimeError):
    """A start-up guard refused. Never caught inside this module."""


# --- guards (D3) ------------------------------------------------------------
def _host(url: str) -> str:
    return re.sub(r"^[a-z]+://([^/:]+).*$", r"\1", url.strip().lower())


def subc_gateway(profile: pathlib.Path = SUBC_PROFILE) -> str:
    """The Subconscious profile's gateway host — read by name, key untouched."""
    if not profile.is_file():
        raise GuardError("subc is not logged in (run `subc login`)")
    for line in profile.read_text(encoding="utf-8").splitlines():
        if line.startswith("GATEWAY_URL="):
            return _host(line.split("=", 1)[1].strip().strip("'\""))
    return ROUTES["subconscious"]["host"]      # subc's documented default


def load_anthropic_token(path: pathlib.Path = ANTHROPIC_TOKEN_FILE) -> str:
    """CLAUDE_CODE_OAUTH_TOKEN from the operator's file. Never logged."""
    if not path.is_file():
        raise GuardError(f"no token file at {path}")
    if path.stat().st_mode & 0o077:
        raise GuardError(f"{path} is readable by others; chmod 600 it")
    token = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
            token = line.split("=", 1)[1].strip()
    if not token:
        raise GuardError(f"{path} has no CLAUDE_CODE_OAUTH_TOKEN line")
    if not token.startswith("sk-ant-") or re.search(r"[<>\"'\s]", token):
        raise GuardError("the token is not a bare Anthropic token (sk-ant-…)")
    return token


def check_route(route: str, env: dict, gateway: str | None = None) -> None:
    """A route's environment may carry only its own credential."""
    present = {k for k in CREDENTIAL_VARS if env.get(k)}
    if route == "subconscious":
        if present:
            raise GuardError(f"subconscious route carries {sorted(present)}; "
                             "subc supplies its own credential")
        if (gateway or subc_gateway()) != ROUTES["subconscious"]["host"]:
            raise GuardError(f"subc gateway is {gateway!r}, not Subconscious")
    elif route == "anthropic":
        if present != {"CLAUDE_CODE_OAUTH_TOKEN"}:
            raise GuardError(f"anthropic route must carry exactly the OAuth token, got {sorted(present)}")
        if not env["CLAUDE_CODE_OAUTH_TOKEN"].startswith("sk-ant-"):
            raise GuardError("anthropic route token is not an Anthropic token")
    else:
        raise GuardError(f"unknown route {route!r}")


def build_cmd(route: str, prompt: str, *, schema: dict | None = None,
              extra: tuple[str, ...] = ()) -> list[str]:
    model = ROUTES[route]["model"]
    if not model:
        raise GuardError("every call names its model explicitly")
    if "--bare" in extra:
        raise GuardError("--bare skips hooks; never passed")
    args = ["-p", prompt, "--output-format", "json", "--no-session-persistence",
            "--dangerously-skip-permissions"]
    if schema is not None:
        args += ["--json-schema", json.dumps(schema)]
    args += list(extra)
    if route == "subconscious":
        return [str(SUBC), "claude", "--model", model, "--", *args]
    return [str(CLAUDE), "--model", model, "--max-budget-usd", str(BUDGET_USD), *args]


# --- the sandbox -------------------------------------------------------------
def harness_dir(clone: pathlib.Path) -> pathlib.Path:
    """Claude Code's per-cwd dir: /private/tmp/claude-<uid>/<encoded path>.

    Allowed by exact path only — its parent also holds other sessions'
    files, including the operator's own interactive sessions.
    """
    real = os.path.realpath(clone)
    return pathlib.Path(f"/private/tmp/claude-{os.getuid()}") / re.sub(r"[^A-Za-z0-9]", "-", real)


def render_profile(clone: pathlib.Path, runtmp: pathlib.Path, home: pathlib.Path = HOME) -> str:
    text = (HERE / "sandbox.sb.tmpl").read_text(encoding="utf-8")
    subs = {"@CLONE@": os.path.realpath(clone), "@RUNTMP@": os.path.realpath(runtmp),
            "@HARNESS_DIR@": str(harness_dir(clone)), "@HOME@": str(home)}
    for k, v in subs.items():
        if '"' in v:
            raise GuardError(f"path contains a quote: {v!r}")
        text = text.replace(k, v)
    if "@" in re.sub(r";.*", "", text):
        raise GuardError("unfilled placeholder in sandbox profile")
    return text


def make_run(root: pathlib.Path, make: str) -> dict:
    """A fresh clone, a tmp dir, a DB snapshot and a rendered profile."""
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run = root / f"{re.sub(r'[^A-Za-z0-9]+', '_', make)}_{stamp}"
    clone, tmp = run / "clone", run / "tmp"
    tmp.mkdir(parents=True)
    subprocess.run(["git", "clone", "-q", "--no-hardlinks", str(REPO), str(clone)], check=True)
    src = sqlite3.connect(f"file:{REPO / 'data' / 'motodiag.db'}?mode=ro", uri=True)
    dst = sqlite3.connect(tmp / "snapshot.db")
    src.backup(dst)
    src.close(); dst.close()
    (tmp / "cfg").mkdir()
    profile = run / "sandbox.sb"
    profile.write_text(render_profile(clone, tmp), encoding="utf-8")
    return {"run": run, "clone": clone, "tmp": tmp, "profile": profile}


def parse_result(stdout: str) -> dict:
    """The last JSON object on stdout. `subc` prints a banner before it."""
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                break
    return {"is_error": True, "result": stdout[-500:]}


def run_stage(r: dict, route: str, prompt: str, *, schema: dict | None = None) -> dict:
    """One sandboxed call. The model's text is never acted on unchecked."""
    env = {"HOME": str(HOME), "PATH": f"{SUBC.parent}:/usr/bin:/bin:{CLAUDE.parent}",
           "USER": os.environ.get("USER", ""), "TERM": "dumb",
           "TMPDIR": str(r["tmp"]), "CLAUDE_CONFIG_DIR": str(r["tmp"] / "cfg")}
    if route == "anthropic":
        env["CLAUDE_CODE_OAUTH_TOKEN"] = load_anthropic_token()
    check_route(route, env)
    cmd = ["sandbox-exec", "-f", str(r["profile"])] + build_cmd(route, prompt, schema=schema)
    p = subprocess.run(cmd, cwd=r["clone"], env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=3600)
    out = parse_result(p.stdout)
    model = ROUTES[route]["model"]
    served = list((out.get("modelUsage") or {}).keys())
    if not served or served != [model]:
        out["is_error"] = True
        out["result"] = f"served by {served or 'nothing'}, not {model}: {out.get('result')!r}"[:500]
    return out


# --- stops (D5) ----------------------------------------------------------------
def stops(findings: list[dict], verdicts: list[dict]) -> list[str]:
    reasons = []
    n = len(findings)
    blocked = sum(f.get("outcome") in ("blocked", "not_found") for f in findings)
    if n and blocked / n > BLOCKED_STOP:
        reasons.append(f"blocked rate {blocked}/{n} exceeds {BLOCKED_STOP:.0%}")
    killed = [v["spelling"] for v in verdicts if v.get("verdict") != "kept"]
    if killed:
        reasons.append(f"refute disagreed on: {', '.join(killed)}")
    return reasons


def alert(title: str, message: str) -> None:
    subprocess.run(["osascript", "-e",
                    f'display notification {json.dumps(message)} with title {json.dumps(title)}'],
                   check=False)
