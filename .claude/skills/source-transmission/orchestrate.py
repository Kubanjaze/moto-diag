#!/usr/bin/env python3
"""source-transmission orchestrator — Phase 257.

Runs the written procedure for one make at a time:

    census      (census.py, no model)
      -> candidates  (candidates.py, no model: library excerpts per spelling)
      -> source      (sandboxed, Subconscious GLM-5.3 Marathon, ONE turn, NO tools:
                      extract + classify from the excerpts in its prompt)
      -> check       (entry_check.py, no model: rejects bad evidence; E10 binds
                      each finding to the excerpts it was handed)
      -> refute  (sandboxed, Opus, fresh context: re-opens every citation)
      -> summary (per-make file; stops alert)

**Why two routes.** The source stage runs through Subconscious (`subc
claude`), the operator's reason for the orchestrator. Refute and write stay
on Opus.

**Why one turn, no tools.** As an agent loop the source stage browsed the
library itself and cost ~2.4M tokens per spelling (Kymco's one spelling:
7,661,322 input). Now `candidates.py` cuts the library to excerpts first
and the model sees only those, in one call it cannot extend: a spelling
with no excerpt is `no_evidence` without a call at all. Web acquire left
the source stage with this change. Refute is unchanged and keeps its tools.

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
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOME = pathlib.Path.home()
CLAUDE = HOME / ".local" / "bin" / "claude"
SUBC = pathlib.Path("/opt/homebrew/bin/subc")
SUBC_PROFILE = HOME / ".subconscious" / "profiles" / "default.env"
ANTHROPIC_TOKEN_FILE = HOME / ".config" / "motodiag" / "anthropic.env"
BUDGET_USD = 3.0                    # per call; Opus route only (see run_stage)
BLOCKED_STOP = 0.5                  # plan D5
# The source stage's flags: no tools, no MCP servers, no skills listing. With
# --json-schema a no-tools call reports 2 turns (the structured answer, then
# its acknowledgement) — measured 2026-09-23; more than that is a loop.
SOURCE_FLAGS = ("--tools", "", "--strict-mcp-config", "--disable-slash-commands")
SOURCE_MAX_TURNS = 2
# The operator's ceiling, a stop and not a setting: no flag or argument
# changes it. Counted per spelling SENT to the model (a no_evidence spelling
# costs nothing and must not dilute the rest), over every stage of the batch.
TOKEN_STOP_PER_SPELLING = 150_000
USAGE_FIELDS = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")

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


def run_stage(r: dict, route: str, prompt: str, *, schema: dict | None = None,
              extra: tuple[str, ...] = ()) -> dict:
    """One sandboxed call. The model's text is never acted on unchecked."""
    env = {"HOME": str(HOME), "PATH": f"{SUBC.parent}:/usr/bin:/bin:{CLAUDE.parent}",
           "USER": os.environ.get("USER", ""), "TERM": "dumb",
           "TMPDIR": str(r["tmp"]), "CLAUDE_CONFIG_DIR": str(r["tmp"] / "cfg")}
    if route == "anthropic":
        env["CLAUDE_CODE_OAUTH_TOKEN"] = load_anthropic_token()
    check_route(route, env)
    cmd = ["sandbox-exec", "-f", str(r["profile"])] + build_cmd(route, prompt, schema=schema, extra=extra)
    p = subprocess.run(cmd, cwd=r["clone"], env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=3600)
    out = parse_result(p.stdout)
    model = ROUTES[route]["model"]
    served = list((out.get("modelUsage") or {}).keys())
    if not served or served != [model]:
        out["is_error"] = True
        out["result"] = f"served by {served or 'nothing'}, not {model}: {out.get('result')!r}"[:500]
    return out


# --- token accounting -------------------------------------------------------------
def usage(out: dict) -> dict:
    """One stage's tokens, from the `modelUsage` block `claude -p` prints.

    `total` adds all four fields. Anthropic reports cache reads apart from
    input; the Subconscious gateway's inputTokens may already include them
    (Kymco's source stage: 7,661,322 in, 6,133,632 cache-read), so the total
    can overcount there. Overcounting stops a batch early, never late.
    A stage that printed no usage is counted as unknown, which is a stop.
    """
    mu = out.get("modelUsage") or {}
    if not mu:
        return {"known": False, "total": 0}
    u = {k: sum(int(m.get(k) or 0) for m in mu.values()) for k in USAGE_FIELDS}
    return {"known": True, **u, "total": sum(u.values())}


def token_stop(stages: dict[str, dict], sent: int) -> str | None:
    """The 150K-per-spelling stop over the stages run so far, or None."""
    unknown = [k for k, u in stages.items() if not u["known"]]
    if unknown:
        return f"token usage unrecorded for stage(s) {', '.join(unknown)}: cannot show the batch is under budget"
    total = sum(u["total"] for u in stages.values())
    if total > TOKEN_STOP_PER_SPELLING * max(sent, 1):
        return (f"tokens {total:,} exceed {TOKEN_STOP_PER_SPELLING:,} per spelling "
                f"x {sent} sent = {TOKEN_STOP_PER_SPELLING * max(sent, 1):,}")
    return None


# --- stops (D5) ----------------------------------------------------------------
def stops(findings: list[dict], verdicts: list[dict], tokens: dict | None = None) -> list[str]:
    reasons = []
    if tokens and tokens.get("stop"):
        reasons.append(tokens["stop"])
    n = len(findings)
    blocked = sum(f.get("outcome") in ("blocked", "not_found") for f in findings)
    if n and blocked / n > BLOCKED_STOP:
        reasons.append(f"blocked rate {blocked}/{n} exceeds {BLOCKED_STOP:.0%}")
    killed = [v["spelling"] for v in verdicts if v.get("verdict") != "kept"]
    if killed:
        reasons.append(f"refute disagreed on: {', '.join(killed)}")
    return reasons


def notification_script(title: str, message: str) -> str:
    """AppleScript for a notification. JSON string escaping is AppleScript's
    for quotes and backslashes, but its \\uXXXX is not: non-ASCII stays literal
    (bug fix #2 — the STOP title's em dash made every stop alert fail)."""
    q = lambda s: json.dumps(s, ensure_ascii=False)  # noqa: E731
    return f"display notification {q(message)} with title {q(title)}"


def alert(title: str, message: str) -> None:
    subprocess.run(["osascript", "-e", notification_script(title, message)], check=False)


# --- the batch (one make) -----------------------------------------------------
RUNS_ROOT = HOME / ".cache" / "motodiag" / "source-runs"
LIBRARY = HOME / "research" / "motodiag"

FINDING = {
    "type": "object", "additionalProperties": False,
    "required": ["make", "spelling", "outcome"],
    "properties": {
        "make": {"type": "string"}, "spelling": {"type": "string"},
        "outcome": {"enum": ["found", "blocked", "not_found", "no_evidence"]},
        "transmission": {"type": ["string", "null"]},
        "candidates": {"type": "array", "items": {"type": "string"}},
        "quote": {"type": "string"}, "document": {"type": "string"},
        "page": {"type": ["string", "integer"]}, "evidence_kind": {"type": "string"},
        "aliases": {"type": "array", "items": {"type": "string"}},
        "ocr": {"type": "boolean"}, "needs_page_image": {"type": "boolean"},
        "url_tried": {"type": "string"}, "note": {"type": "string"},
    },
}
SOURCE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["findings"],
                 "properties": {"findings": {"type": "array", "items": FINDING}}}
VERDICT_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["verdicts"],
                  "properties": {"verdicts": {"type": "array", "items": {
                      "type": "object", "additionalProperties": False,
                      "required": ["spelling", "verdict", "quote", "page", "reason"],
                      "properties": {"spelling": {"type": "string"},
                                     "verdict": {"enum": ["kept", "killed"]},
                                     "quote": {"type": "string"}, "page": {"type": ["string", "integer"]},
                                     "reason": {"type": "string"}}}}}}

SOURCE_PROMPT = """You are the SOURCE stage of the moto-diag transmission procedure. Make: {make}. Spellings to source, exactly these: {spellings}.
You have no tools and one answer. Everything you may cite is in the EXCERPTS below: passages of on-disk library documents, cut by a script around each spelling. Return one finding per spelling. Rules, each from a real mistake:
- `document` is an excerpt's `document` path, exactly as given. `page` is the page of the quoted line: the nearest PAGE marker above it inside the excerpt text, else the excerpt's `page`, else its `lines` range.
- `quote` must be copied VERBATIM from that excerpt's text (it is string-matched against the excerpt and against the document), a full statement, not a table cell alone. Use the maker's own word for the mechanism.
- An excerpt with anchor "file" comes from a document whose file name names the machine, but that passage does not name it: say so in `note`.
- `transmission` is one of: manual, cvt, dct, semi_auto_centrifugal, semi_auto_actuated, direct_drive. Ambiguous variants -> `candidates` instead. If the excerpts do not establish the gearbox of THIS machine -> outcome no_evidence and transmission NULL. Never infer from the make or the model family, and never from anything but the excerpts.
- If the text is OCR of a scanned page (garbled words, broken spacing), set ocr=true and needs_page_image=true.
- evidence_kind: owners_manual | service_manual | workshop_manual | spec_sheet | maker_spec_page. Anything else (marketing, dealer, forum, mirror sites, recall notices) is not evidence.
- `aliases`: spellings and model codes the document itself uses for this machine.{hints}
EXCERPTS (JSON, by spelling):
{excerpts}"""

REFUTE_PROMPT = """You are the REFUTE stage. You did not produce these findings and must not trust them. For each finding below, OPEN the cited document yourself at the cited page and decide kept or killed.
If the cited document is under evidence/, it is a copy the source stage saved: its <file>.provenance.json names the ORIGINAL (and, for a URL, the pinned fetch in "fetched_as"). Check the quote against the ORIGINAL, not against the copy.
Kill it if: the quote is not on that page; the page is about a different model; the quote does not actually establish the stated mechanism; or the evidence is OCR and the page IMAGE does not show it. When a finding is marked needs_page_image, find the scanned page image (PNG/JPG near the document; for the Grom: {library}/grom/out/ and {library}/grom/ocr.json maps page index -> OCR lines) and read the IMAGE with the Read tool. OCR text is never enough on its own.
Return one verdict per finding with the verbatim quote YOU saw and its page.
Findings:
{findings}"""


def no_evidence(make: str, spelling: str, unnamed: str | None = None) -> dict:
    """The finding for a spelling nothing is sent for. No model is asked."""
    note = (f"census: not a machine name ({unnamed}); not searched, the model was not called" if unnamed
            else "candidates.py: no library document names this spelling; the model was not called")
    return {"make": make, "spelling": spelling, "outcome": "no_evidence", "transmission": None, "note": note}


def batch(make: str, spellings: list[str], hints: str = "") -> dict:
    """Run one make end to end. Returns the summary; never edits the repository."""
    import candidates
    import census
    import entry_check
    r = make_run(RUNS_ROOT, make)
    summary = {"make": make, "spellings": spellings, "run": str(r["run"]),
               "started": dt.datetime.now().isoformat(timespec="seconds")}
    # A spelling that cannot be a machine name is not searched for, let alone sent.
    unnamed = {s: c for s in spellings if (c := census.not_a_machine(make, s))}
    names = [s for s in spellings if s not in unnamed]
    cands = candidates.candidates(names, LIBRARY, make=make) if names else {}
    (r["run"] / "candidates.json").write_text(json.dumps(cands, indent=1), encoding="utf-8")
    sent = [s for s in names if cands.get(s)]
    findings = [no_evidence(make, s, unnamed.get(s)) for s in spellings if s not in sent]
    summary["source_error"] = None
    stages: dict[str, dict] = {}
    if sent:
        src = run_stage(r, SOURCE_ROUTE, SOURCE_PROMPT.format(
            make=make, spellings=json.dumps(sent),
            excerpts=json.dumps({s: cands[s] for s in sent}, indent=1),
            hints=("\n- Hints: " + hints) if hints else ""), schema=SOURCE_SCHEMA, extra=SOURCE_FLAGS)
        if not src.get("is_error") and (src.get("num_turns") or 0) > SOURCE_MAX_TURNS:
            src["is_error"] = True
            src["result"] = (f"the no-tools source stage took {src.get('num_turns')} turns "
                             f"(at most {SOURCE_MAX_TURNS}): it was not the one call it was built as")
        (r["run"] / "source.json").write_text(json.dumps(src, indent=1), encoding="utf-8")
        stages["source"] = usage(src)
        if src.get("is_error"):
            summary["source_error"] = src.get("result")
        else:
            findings += (src.get("structured_output") or {}).get("findings", [])
    missing = sorted(set(spellings) - {f.get("spelling") for f in findings})
    rejections = entry_check.check(findings, r["clone"], cands)
    passed = [f for f in findings if f.get("outcome") == "found"
              and not entry_check.check_one(f, r["clone"], cands)]
    verdicts = []
    over = token_stop(stages, len(sent))
    if passed and not over:         # over budget already: refute is not spent
        ref = run_stage(r, REFUTE_ROUTE, REFUTE_PROMPT.format(
            library=LIBRARY, findings=json.dumps(passed, indent=1)), schema=VERDICT_SCHEMA)
        (r["run"] / "refute.json").write_text(json.dumps(ref, indent=1), encoding="utf-8")
        stages["refute"] = usage(ref)
        over = token_stop(stages, len(sent))
        verdicts = (ref.get("structured_output") or {}).get("verdicts", []) if not ref.get("is_error") else [
            {"spelling": f["spelling"], "verdict": "error", "quote": "", "page": "", "reason": ref.get("result")}
            for f in passed]
    tokens = {"stages": stages, "total": sum(u["total"] for u in stages.values()),
              "sent": len(sent), "ceiling": TOKEN_STOP_PER_SPELLING * max(len(sent), 1),
              "stop": over}
    reasons = stops(findings, verdicts, tokens)
    if missing:
        reasons.append(f"source returned no finding for: {', '.join(missing)}")
    if rejections:
        reasons.append(f"{len(rejections)} finding(s) rejected by entry_check")
    if summary["source_error"]:
        reasons.append(f"source stage error: {summary['source_error']}")
    kept = {v["spelling"] for v in verdicts if v.get("verdict") == "kept"}
    summary.update({"not_a_machine": unnamed, "sent_to_model": sent, "tokens": tokens, "findings": findings, "rejections": rejections, "verdicts": verdicts,
                    "ready_to_write": [] if over else [f for f in passed if f["spelling"] in kept],
                    "stops": reasons, "finished": dt.datetime.now().isoformat(timespec="seconds")})
    (r["run"] / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    if reasons:
        alert("moto-diag source-transmission — STOP", f"{make}: {reasons[0]}")
    else:
        alert("moto-diag source-transmission", f"{make}: {len(kept)} ready to write")
    return summary


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "batch":
        print("usage: orchestrate.py batch MAKE [SPELLING ...] [--hints TEXT]", file=sys.stderr)
        return 2
    hints = ""
    if "--hints" in argv:
        i = argv.index("--hints"); hints = argv[i + 1]; argv = argv[:i] + argv[i + 2:]
    make, spellings = argv[1], argv[2:]
    if not spellings:
        import census as C
        spellings = [e["model"] for e in C.census(REPO / "data" / "motodiag.db", make).get(make, [])]
    s = batch(make, spellings, hints)
    print(json.dumps({k: s[k] for k in ("make", "run", "stops")}, indent=1))
    print(f"tokens: {s['tokens']['total']:,} (ceiling {s['tokens']['ceiling']:,})")
    print(f"ready to write: {[f['spelling'] for f in s['ready_to_write']]}")
    return 1 if s["stops"] else 0


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    raise SystemExit(main(sys.argv[1:]))
