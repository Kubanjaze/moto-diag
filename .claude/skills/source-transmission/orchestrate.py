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
# Refute's own budget, per finding refuted — approved by the operator
# 2026-09-23: ~1.3x the largest refute measured (226,857 for one finding,
# Kymco; 165,071 before the redesign). Not raised to fit a batch: if the
# per-finding cost climbs, refute is split into groups (REFUTE_GROUP).
REFUTE_STOP_PER_FINDING = 300_000
# Findings per refute call, each call a fresh context. None: one call for
# all. Operator, 2026-09-23: if per-finding cost climbs across a batch,
# groups of at most 5 — not a higher budget.
REFUTE_GROUP: int | None = None
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
              extra: tuple[str, ...] = (), stream: bool = False) -> list[str]:
    model = ROUTES[route]["model"]
    if not model:
        raise GuardError("every call names its model explicitly")
    if "--bare" in extra:
        raise GuardError("--bare skips hooks; never passed")
    # stream: one JSON event per line, each API call's usage in it — how refute's
    # cost is attributed per finding. The last line is the same result object.
    fmt = ["--output-format", "stream-json", "--verbose"] if stream else ["--output-format", "json"]
    args = ["-p", prompt, *fmt, "--no-session-persistence",
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
              extra: tuple[str, ...] = (), stream: bool = False) -> dict:
    """One sandboxed call. The model's text is never acted on unchecked.
    With stream, the parsed events are returned under `_events`."""
    env = {"HOME": str(HOME), "PATH": f"{SUBC.parent}:/usr/bin:/bin:{CLAUDE.parent}",
           "USER": os.environ.get("USER", ""), "TERM": "dumb",
           "TMPDIR": str(r["tmp"]), "CLAUDE_CONFIG_DIR": str(r["tmp"] / "cfg")}
    if route == "anthropic":
        env["CLAUDE_CODE_OAUTH_TOKEN"] = load_anthropic_token()
    check_route(route, env)
    cmd = ["sandbox-exec", "-f", str(r["profile"])] + build_cmd(route, prompt, schema=schema, extra=extra,
                                                                stream=stream)
    p = subprocess.run(cmd, cwd=r["clone"], env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=3600)
    out = parse_result(p.stdout)
    if stream:
        events = []
        for line in p.stdout.splitlines():
            if line.strip().startswith("{"):
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        out["_events"] = events
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


def add_usage(a: dict | None, b: dict) -> dict:
    """Two stages' usage summed (refute run in groups)."""
    if a is None:
        return dict(b)
    if not (a["known"] and b["known"]):
        return {"known": False, "total": 0}
    return {"known": True, **{k: a[k] + b[k] for k in (*USAGE_FIELDS, "total")}}


def refute_attribution(events: list[dict], findings: list[dict]) -> list[dict]:
    """Refute's tokens and API calls ("turns") per finding, in order.

    Each API call is one assistant message id (a message streams as several
    events repeating its usage — deduplicated). A call is the finding's whose
    spelling or document its tool inputs name; a call naming none continues
    the previous finding; before any, '(setup)'; a call naming several
    findings (the final structured answer) is '(answer)'. An attribution by
    what refute was reading — not a measurement inside the model."""
    calls: dict[str, dict] = {}
    order: list[str] = []
    for e in events:
        m = e.get("message") or {}
        if e.get("type") != "assistant" or not m.get("id"):
            continue
        if m["id"] not in calls:
            calls[m["id"]] = {"usage": {}, "inputs": []}
            order.append(m["id"])
        calls[m["id"]]["usage"] = m.get("usage") or calls[m["id"]]["usage"]
        calls[m["id"]]["inputs"] += [json.dumps(c.get("input"), ensure_ascii=False)
                                     for c in m.get("content") or [] if c.get("type") == "tool_use"]
    keys = {f["spelling"]: [k for k in (f["spelling"], f.get("document") or "",
                                        pathlib.Path(f.get("document") or "").name) if k]
            for f in findings}
    rows = {s: {"spelling": s, "turns": 0, "tokens": 0} for s in [*keys, "(setup)", "(answer)"]}
    current = "(setup)"
    for mid in order:
        text = " ".join(calls[mid]["inputs"])
        hits = [s for s, ks in keys.items() if any(k in text for k in ks)]
        who = hits[0] if len(hits) == 1 else ("(answer)" if hits else current)
        if len(hits) == 1:
            current = hits[0]
        u = calls[mid]["usage"]
        rows[who]["turns"] += 1
        rows[who]["tokens"] += sum(int(u.get(k) or 0) for k in
                                   ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                    "cache_creation_input_tokens"))
    return [rows[s] for s in [*keys, "(setup)", "(answer)"]]


def token_stop(stages: dict[str, dict], sent: int, refuted: int = 0) -> str | None:
    """The two budgets over the stages run so far, or None.

    Every stage but refute: 150K per spelling sent. Refute: its own budget,
    per finding sent to it (operator decision 2026-09-23 — refute is the
    step that caught fabricated citations; it is budgeted, never trimmed or
    skipped; over its budget is a stop)."""
    unknown = [k for k, u in stages.items() if not u["known"]]
    if unknown:
        return f"token usage unrecorded for stage(s) {', '.join(unknown)}: cannot show the batch is under budget"
    rest = sum(u["total"] for k, u in stages.items() if k != "refute")
    if rest > TOKEN_STOP_PER_SPELLING * max(sent, 1):
        return (f"tokens {rest:,} exceed {TOKEN_STOP_PER_SPELLING:,} per spelling "
                f"x {sent} sent = {TOKEN_STOP_PER_SPELLING * max(sent, 1):,}")
    if "refute" in stages and stages["refute"]["total"] > REFUTE_STOP_PER_FINDING * max(refuted, 1):
        return (f"refute tokens {stages['refute']['total']:,} exceed {REFUTE_STOP_PER_FINDING:,} per finding "
                f"x {refuted} refuted = {REFUTE_STOP_PER_FINDING * max(refuted, 1):,}")
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
    # Bug fix #4: the citation fields are required on every finding (null
    # where there is nothing to cite). Optional, the SV650 re-run returned a
    # found finding with no `document` — E1 stopped it, but the schema let the
    # model omit the one field the whole procedure turns on.
    "required": ["make", "spelling", "outcome", "transmission", "quote", "document", "page", "evidence_kind"],
    "properties": {
        "make": {"type": "string"}, "spelling": {"type": "string"},
        "outcome": {"enum": ["found", "blocked", "not_found", "no_evidence"]},
        "transmission": {"type": ["string", "null"]},
        "candidates": {"type": "array", "items": {"type": "string"}},
        "quote": {"type": ["string", "null"]}, "document": {"type": ["string", "null"]},
        "page": {"type": ["string", "integer", "null"]}, "evidence_kind": {"type": ["string", "null"]},
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
                      "required": ["spelling", "verdict", "quote", "page", "names_model", "model_line", "reason"],
                      "properties": {"spelling": {"type": "string"},
                                     "verdict": {"enum": ["kept", "killed"]},
                                     "quote": {"type": "string"}, "page": {"type": ["string", "integer"]},
                                     "names_model": {"type": "boolean"},
                                     "model_line": {"type": "string"},
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
A "manual" classification needs the quote itself to name a rider-operated clutch (clutch lever, cable or hydraulic clutch, clutch pull), a foot-shift pattern (return shift, shift pedal) or the word "manual". A gear count, "constant mesh" or "close-ratio" alone is NOT mechanism evidence — a DCT or Y-AMT is a constant-mesh six-speed too — kill such a finding (entry_check E12 enforces the same rule).
Kill it if: the quote is not on that page; the page is about a different model; the quote does not actually establish the stated mechanism; or the evidence is OCR and the page IMAGE does not show it. When a finding is marked needs_page_image, find the scanned page image (PNG/JPG near the document; for the Grom: {library}/grom/out/ and {library}/grom/ocr.json maps page index -> OCR lines) and read the IMAGE with the Read tool. OCR text is never enough on its own.
Render page images ONLY for findings marked needs_page_image (weak OCR); for a digital text layer, read the text.
`verdict` answers whether the quote is on the page and establishes the mechanism. `names_model` answers a separate question: true ONLY if the document is about THIS exact model — not a variant ("SV650X", "ZX-10RR", "V-Strom 650XT", "Z900 SE"), not a sibling, not the model named in passing (history, comparison). ONE named exception: a page for "<exact model> ABS" (e.g. "SV650 ABS" for the SV650) IS about the model — ABS is braking equipment — so names_model is true. Nothing else qualifies, and NEVER a transmission variant: "Africa Twin DCT", "MT-09 Y-AMT", "E-Clutch" pages do not name the base model. "kept" with names_model false is family evidence and writes nothing.
`model_line`: copy VERBATIM the line on the document that names THIS exact model (the finding's spelling) — not a sibling, a variant or the family: "1290 Super Duke GT" does not name the 1290 Super Duke R; "F 800 GS" does not name the F800. If the document names only a sibling or the family, return "" — the finding is then family evidence and cannot write an entry. The line is checked against the document by a script.
Return one verdict per finding with the verbatim quote YOU saw and its page.
Findings:
{findings}"""


def model_named(f: dict, verdicts: list[dict], docs_root: pathlib.Path) -> bool:
    """Refute's confirmation that a family-scope finding's page names the
    model — never taken on its word: the line must name the model by
    entry_check's rule and be in the document."""
    import entry_check
    line = next((v.get("model_line") or "" for v in verdicts if v.get("spelling") == f["spelling"]), "")
    text = entry_check.document_text(f, docs_root)
    return bool(line) and text is not None and entry_check.names_model(line, f["spelling"]) \
        and entry_check._norm(line) in entry_check._norm(text)


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
    for f in passed:
        f["scope"] = entry_check.model_scope(f, r["clone"])     # the 4609 rule: model or family
        f["edition"] = entry_check.model_edition(f, r["clone"])  # 'ABS': the one named exception
    verdicts = []
    over = token_stop(stages, len(sent))
    per_finding: list[dict] = []
    if passed and not over:         # over budget already: refute is not spent
        size = REFUTE_GROUP or len(passed)
        groups = [passed[i:i + size] for i in range(0, len(passed), size)]
        refuted = 0
        for n, group in enumerate(groups, 1):
            if over:
                break               # a stop: the remaining findings get no verdict and write nothing
            ref = run_stage(r, REFUTE_ROUTE, REFUTE_PROMPT.format(
                library=LIBRARY, findings=json.dumps(group, indent=1)), schema=VERDICT_SCHEMA, stream=True)
            events = ref.pop("_events", [])
            tag = "" if len(groups) == 1 else f"_{n}"
            (r["run"] / f"refute{tag}.json").write_text(json.dumps(ref, indent=1), encoding="utf-8")
            (r["run"] / f"refute{tag}.stream.jsonl").write_text(
                "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
            per_finding += [dict(row, group=n) for row in refute_attribution(events, group)]
            stages["refute"] = add_usage(stages.get("refute"), usage(ref))
            refuted += len(group)
            over = token_stop(stages, len(sent), refuted)
            verdicts += (ref.get("structured_output") or {}).get("verdicts", []) if not ref.get("is_error") else [
                {"spelling": f["spelling"], "verdict": "error", "quote": "", "page": "", "reason": ref.get("result")}
                for f in group]
    tokens = {"stages": stages, "total": sum(u["total"] for u in stages.values()),
              "sent": len(sent), "ceiling": TOKEN_STOP_PER_SPELLING * max(len(sent), 1),
              "refuted": len(passed) if "refute" in stages else 0,
              "refute_ceiling": REFUTE_STOP_PER_FINDING * max(len(passed), 1) if "refute" in stages else None,
              "stop": over}
    reasons = stops(findings, verdicts, tokens)
    if missing:
        reasons.append(f"source returned no finding for: {', '.join(missing)}")
    if rejections:
        reasons.append(f"{len(rejections)} finding(s) rejected by entry_check")
    if summary["source_error"]:
        reasons.append(f"source stage error: {summary['source_error']}")
    kept = {v["spelling"] for v in verdicts if v.get("verdict") == "kept"}
    # Bug fix #3: "kept" says the quote holds; it does not say the page is
    # about THIS model. A finding writes only when refute's names_model is
    # true AND the script agrees; a disagreement is a D5 stop.
    writable, family = [], []
    disagree = []
    for f in (passed if not over else []):
        if f["spelling"] not in kept:
            continue
        v = next(x for x in verdicts if x.get("spelling") == f["spelling"])
        refute_says = v.get("names_model") is True
        script_says = f["scope"] == "model" or model_named(f, verdicts, r["clone"])
        if refute_says and script_says:
            writable.append(f)
        else:
            family.append(f)
            if refute_says != script_says:
                disagree.append(f"{f['spelling']} (script {'named' if script_says else 'family'}, "
                                f"refute {'named' if refute_says else 'family'})")
    if disagree:
        reasons.append(f"refute and the script disagree on whether the page names the model: {', '.join(disagree)}")
    summary.update({"not_a_machine": unnamed, "sent_to_model": sent, "tokens": tokens, "findings": findings, "rejections": rejections, "verdicts": verdicts,
                    "family_evidence": family, "refute_per_finding": per_finding,
                    "ready_to_write": writable,
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
