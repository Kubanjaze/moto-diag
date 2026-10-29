"""Phase 388 — the fleet's dispatcher, with stand-ins for GitHub, the fence and claude.

What must hold, from the operator's prompt: it polls by label and runs a
stage through fence.sh; it handles only 387's read-only ranks (the
Executive Officer on plan:needs-review, the daily digest) plus a sweep that
comments on any label older than 24 hours; a run that cannot finish leaves
the label where it found it and comments why; a rate limit is a stop that
records the reset time and resumes with --resume; no new Opus stage above
70% of the weekly cap; one process; the label is the lock.

git is real (a mirror of a repository built from 387's good fixture tree);
`gh` and the fenced `claude` are stand-ins on one clock.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "fleet"
FIX = SKILL / "fixtures" / "dispatcher"
sys.path.insert(0, str(SKILL))

import dispatcher as D  # noqa: E402
import rank_call  # noqa: E402
import xo  # noqa: E402
from plan_check import FIXTURE_PHASE, GOOD  # noqa: E402

NY = dt.timezone(dt.timedelta(hours=-4))
T0 = dt.datetime(2026, 10, 22, 21, 0, tzinfo=NY)
TOKEN = "sk-ant-oat01-test-token"
BRANCH = f"phase-{FIXTURE_PHASE}-fixture"
USAGE_OK = (FIX / "usage_measured.txt").read_text()
USAGE_CEILING = (FIX / "usage_at_ceiling.txt").read_text()
USAGE_LIMITED = (FIX / "usage_limited.txt").read_text()
USAGE_BAD = (FIX / "usage_unparseable.txt").read_text()
LIMITED = (FIX / "rate_limited.json").read_text()

V_APPROVE = {"verdict": "approve", "items": [], "reason": "Buildable as written."}
V_BACK = {"verdict": "back-to-captain", "items": ["Fix the count."], "reason": "One defect."}


def claude_json(structured: dict | None, *, usage: bool = True, session: str = "sess-1",
                model: str = rank_call.FABLE) -> str:
    return json.dumps({
        "type": "result", "is_error": False, "session_id": session, "num_turns": 3,
        "duration_ms": 4000, "total_cost_usd": 0.5, "result": json.dumps(structured or {}),
        "structured_output": structured, "modelUsage": {model: {"inputTokens": 10}},
        "usage": ({"input_tokens": 10, "cache_creation_input_tokens": 100,
                   "cache_read_input_tokens": 1000, "output_tokens": 20} if usage else {})})


def iso(t: dt.datetime) -> str:
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Clock:
    def __init__(self, t: dt.datetime = T0):
        self.t = t

    def __call__(self) -> dt.datetime:
        return self.t


class Host:
    """The host runner: gh and the fence are stand-ins, git is real."""

    def __init__(self, clock: Clock, fence: pathlib.Path):
        self.clock, self.fence = clock, str(fence)
        self.issues: dict[int, dict] = {}
        self.replies: list[str] = []
        self.usage_text = USAGE_OK
        self.usage_after: str | None = None    # what /usage says once a model call has run
        self.fenced: list[tuple[list[str], dict]] = []
        self.usage_reads: list[tuple[list[str], dict]] = []   # outside the fence, since 389
        self.gh_calls: list[tuple[list[str], dict]] = []
        self.commenter = D.fleet_git.OPERATOR_LOGIN    # who `gh issue comment` posts as

    def issue(self, n: int, title: str, body: str = "", labels: dict[str, dt.datetime] | None = None):
        self.issues[n] = {"title": title, "body": body, "comments": [], "events": [],
                          "labels": []}
        for name, at in (labels or {}).items():
            self.label(n, name, at)

    def label(self, n: int, name: str, at: dt.datetime | None = None):
        i = self.issues[n]
        if name not in i["labels"]:
            i["labels"].append(name)
        i["events"].append({"label": name, "at": iso(at or self.clock())})

    def comments(self, n: int) -> list[str]:
        return [c["body"] for c in self.issues[n]["comments"]]

    def model_calls(self) -> list[list[str]]:
        return [inner for inner, _ in self.fenced if "/usage" not in inner]

    def model_briefs(self) -> list[str | None]:
        """Each model call's brief, as it reached the fence's stdin (Phase 394)."""
        return [kw.get("input") for inner, kw in self.fenced if "/usage" not in inner]

    def __call__(self, cmd, **kw):
        cmd = list(cmd)
        if cmd[0] == "gh":
            self.gh_calls.append((cmd, kw))
            return self.gh(cmd)
        if cmd[0] == "claude" and "/usage" in cmd:
            self.usage_reads.append((cmd, kw))
            return subprocess.CompletedProcess(cmd, 0, json.dumps({"result": self.usage_text}), "")
        if cmd[0] == self.fence:
            inner = cmd[cmd.index("--") + 1:]
            self.fenced.append((inner, kw))
            if "/usage" in inner:
                return subprocess.CompletedProcess(cmd, 0, json.dumps({"result": self.usage_text}), "")
            out = self.replies.pop(0)
            if self.usage_after is not None:
                self.usage_text, self.usage_after = self.usage_after, None
            rc = 1 if '"is_error": true' in out else 0
            return subprocess.CompletedProcess(cmd, rc, out, "")
        return subprocess.run(cmd, **kw)

    def gh(self, cmd):
        ok = lambda out="": subprocess.CompletedProcess(cmd, 0, out, "")  # noqa: E731
        if cmd[1:3] == ["issue", "list"]:
            want = cmd[cmd.index("--label") + 1] if "--label" in cmd else None
            rows = [{"number": n, "title": i["title"], "body": i["body"], "state": "OPEN",
                     "author": {"login": i.get("author", D.fleet_git.OPERATOR_LOGIN)},
                     "url": f"https://github.com/{D.REPO}/issues/{n}",
                     "updatedAt": iso(self.clock()),
                     "labels": [{"name": lab} for lab in i["labels"]]}
                    for n, i in sorted(self.issues.items()) if want is None or want in i["labels"]]
            return ok(json.dumps(rows))
        if cmd[1] == "api":
            path = next(a for a in cmd if a.startswith("repos/"))
            n = int(path.split("/issues/")[1].split("/")[0])
            return ok("".join(json.dumps(e) + "\n" for e in self.issues[n]["events"]))
        n = int(cmd[3])
        i = self.issues[n]
        if cmd[1:3] == ["issue", "view"]:
            field = cmd[cmd.index("--json") + 1]
            if field in ("comments", "comments,body"):
                # A comment a test planted with no author is the operator's, as
                # #14's history (fixtures/resume) was before the fleet's account.
                said = [{"author": {"login": D.fleet_git.OPERATOR_LOGIN}, **c} for c in i["comments"]]
                return ok(json.dumps({"comments": said, "body": i["body"]}))
            return ok(json.dumps({"labels": [{"name": lab} for lab in i["labels"]]}))
        if cmd[1:3] == ["issue", "comment"]:
            # GitHub names each comment's author (Phase 392, F223): here, whoever
            # this stand-in says is commenting, the operator unless a test says.
            i["comments"].append({"body": cmd[cmd.index("--body") + 1],
                                  "createdAt": iso(self.clock()),
                                  "author": {"login": self.commenter}})
            return ok()
        if cmd[1:3] == ["issue", "edit"]:
            for k, a in enumerate(cmd):
                if a == "--add-label":
                    self.label(n, cmd[k + 1])
                if a == "--remove-label" and cmd[k + 1] in i["labels"]:
                    i["labels"].remove(cmd[k + 1])
            return ok()
        raise AssertionError(f"unexpected gh {cmd}")


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_DATE": "2026-10-20T12:00:00",
                        "GIT_COMMITTER_DATE": "2026-10-20T12:00:00"})


@pytest.fixture(scope="module")
def origin(tmp_path_factory):
    """A repository from 387's good tree: master and the phase branch."""
    src = tmp_path_factory.mktemp("origin") / "repo"
    shutil.copytree(GOOD, src)
    git("init", "-q", "-b", "master", str(src))
    git("-C", str(src), "add", "-A")
    git("-C", str(src), "-c", "user.name=t", "-c", "user.email=t@l", "commit", "-qm", "good")
    git("-C", str(src), "branch", BRANCH)
    return src


@pytest.fixture(autouse=True)
def ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("FLEET_LEDGER", str(tmp_path / "calls.jsonl"))


@pytest.fixture
def world(tmp_path, origin):
    clock = Clock()
    fence = tmp_path / "fence.sh"
    host = Host(clock, fence)
    lines: list[str] = []
    # No fleet account, planted: the default is the desktop's real file, which
    # the operator created on 2026-10-25 at 22:25 (Phase 390, bug fix #1).
    fleet = D.Fleet(state=tmp_path / "state", token=TOKEN, host=host, fence=fence,
                    workspace_docs=tmp_path / "wsd", repo_url=str(origin), now=clock,
                    out=lines.append, identity_file=tmp_path / "no-identity.env")
    fleet.save({"last_digest": "2026-10-21"})      # T0's digest is done: cycles at T0 run none
    return fleet, host, clock, lines


def mission(host, n=21, labels=None, body=None):
    # A planted trial (Phase 392, F223): with no account of its own, the
    # fleet comments as the operator, whose markers count only on a trial.
    host.issue(n, f"Phase {FIXTURE_PHASE}: the fixture",
               f"Mission issue, branch `{BRANCH}`. {D.fleet_git.TRIAL_MARKER}" if body is None
               else body,
               labels if labels is not None else {"mission": T0 - dt.timedelta(minutes=5),
                                                  "plan:needs-review": T0 - dt.timedelta(minutes=5)})


# ---------------------------------------------------------------- the usage
class TestUsage:
    def test_the_measured_lines(self):
        u = D.parse_usage(USAGE_OK, T0)
        assert {k: v[0] for k, v in u.items()} == {"session": 7, D.WEEK_ALL: 8, "week (Fable)": 13}
        assert u["session"][1] == dt.datetime(2026, 10, 22, 22, 0, tzinfo=NY)
        assert u[D.WEEK_ALL][1] == dt.datetime(2026, 10, 28, 12, 0, tzinfo=NY)

    def test_a_reset_with_minutes(self):
        assert D.parse_usage(USAGE_CEILING, T0)["session"][1] == dt.datetime(2026, 10, 23, 3, 30, tzinfo=NY)

    def test_a_bare_time_is_the_next_one(self):
        assert D.parse_reset("8pm", "America/New_York", T0) == dt.datetime(2026, 10, 23, 20, 0, tzinfo=NY)
        assert D.parse_reset("11pm", "America/New_York", T0) == dt.datetime(2026, 10, 22, 23, 0, tzinfo=NY)

    def test_the_year_rolls_over(self):
        eve = dt.datetime(2026, 12, 31, 22, 0, tzinfo=dt.timezone(dt.timedelta(hours=-5)))
        assert D.parse_reset("Jan 1, 2am", "America/New_York", eve).year == 2027

    @pytest.mark.parametrize("text,tz", [("soon", "America/New_York"), ("Oct 28, 12pm", "Mars/Olympus")])
    def test_unreadable_resets(self, text, tz):
        assert D.parse_reset(text, tz, T0) is None

    def test_unparseable_usage_is_empty(self):
        assert D.parse_usage(USAGE_BAD, T0) == {}


class TestTheOpusCeiling:
    def test_below_is_allowed(self):
        assert D.opus_refusal(D.parse_usage(USAGE_OK, T0)) is None
        assert D.opus_refusal(D.parse_usage(USAGE_CEILING.replace("70% used", "69% used"), T0)) is None

    def test_at_seventy_is_refused(self):
        assert "70%" in D.opus_refusal(D.parse_usage(USAGE_CEILING, T0))

    @pytest.mark.parametrize("usage", [None, {}, {"session": (5, None)}])
    def test_unreadable_is_refused(self, usage):
        assert D.opus_refusal(usage) == "the weekly usage could not be read"

    def test_the_runner_refuses_an_opus_call_and_makes_none(self, world, tmp_path):
        fleet, host, _, _ = world
        host.usage_text = USAGE_CEILING
        runner = D.FencedRunner(fleet, tmp_path, tmp_path / "run")
        with pytest.raises(rank_call.Stop, match="no new Opus stage"):
            runner(["claude", "-p", "x", "--model", rank_call.OPUS], cwd=tmp_path)
        assert host.model_calls() == []

    def test_the_runner_lets_an_opus_call_through_below_the_ceiling(self, world, tmp_path):
        fleet, host, _, _ = world
        host.replies = [claude_json({}, model=rank_call.OPUS)]
        D.FencedRunner(fleet, tmp_path, tmp_path / "run")(
            ["claude", "-p", "x", "--model", rank_call.OPUS], cwd=tmp_path)
        assert len(host.model_calls()) == 1

    def test_haiku_is_not_gated(self, world, tmp_path):
        fleet, host, _, _ = world
        host.usage_text = USAGE_CEILING
        host.replies = [claude_json({}, model=rank_call.HAIKU)]
        D.FencedRunner(fleet, tmp_path, tmp_path / "run")(["claude", "-p", "x", "--model",
                                                           rank_call.HAIKU])
        assert host.usage_reads == []

    def test_fable_is_gated_by_its_own_week_since_389(self, world, tmp_path):
        """USAGE_CEILING: all models at 70%, Fable at 52%: Fable passes."""
        fleet, host, _, _ = world
        host.usage_text = USAGE_CEILING
        host.replies = [claude_json({}, model=rank_call.FABLE)]
        D.FencedRunner(fleet, tmp_path, tmp_path / "run")(["claude", "-p", "x", "--model",
                                                           rank_call.FABLE])
        assert len(host.model_calls()) == 1 and len(host.usage_reads) == 1

    def test_the_usage_is_read_outside_the_fence_on_the_operators_sign_in(self, world):
        """F218 and the operator's "Use my sign-in to read (Recommended)":
        not through fence.sh, and with no token of the fleet's in reach."""
        fleet, host, _, _ = world
        assert D.parse_usage(USAGE_OK, T0) == fleet.usage()
        (cmd, kw), = host.usage_reads
        assert cmd[:3] == ["claude", "-p", "/usage"] and not any(i for i, _ in host.fenced)
        assert {"CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
                "ANTHROPIC_API_KEY"}.isdisjoint(kw["env"])
        assert "pass_fds" not in kw

    def test_a_resumed_opus_stage_is_not_new(self, world, tmp_path):
        fleet, host, _, _ = world
        host.usage_text = USAGE_CEILING
        host.replies = [claude_json({}, model=rank_call.OPUS)]
        # Phase 390: the session comes from the stage's journal, not an argument.
        j = D.journal.Journal.create(tmp_path, {"stage": "xo", "session": "s-9"}, T0)
        j.resumed = True
        D.FencedRunner(fleet, tmp_path, tmp_path / "run", journal=j)(
            ["claude", "-p", "x", "--model", rank_call.OPUS])
        assert host.model_calls()[0][:3] == ["claude", "--resume", "s-9"]


class TestTheRateLimitIsRead:
    def test_the_hand_written_limit(self):
        r = subprocess.CompletedProcess([], 1, LIMITED, "")
        assert D.rate_limit(r) == ("sess-limited-1", json.loads(LIMITED)["result"])

    def test_the_limit_in_the_result_with_exit_zero(self):
        r = subprocess.CompletedProcess([], 0, LIMITED, "")
        assert D.rate_limit(r) == ("sess-limited-1", json.loads(LIMITED)["result"])

    def test_a_limit_on_stderr_with_a_nonzero_exit(self):
        assert D.rate_limit(subprocess.CompletedProcess([], 1, "", "API Error: rate limit exceeded"))

    @pytest.mark.parametrize("out,rc", [(claude_json(V_APPROVE), 0),
                                        (json.dumps({"is_error": True, "result": "Invalid API key"}), 1),
                                        ("not json", 0)])
    def test_other_ends_are_not_limits(self, out, rc):
        assert D.rate_limit(subprocess.CompletedProcess([], rc, out, "")) is None

    def test_the_reset_is_the_later_full_line(self):
        assert D.reset_after_limit(D.parse_usage(USAGE_LIMITED, T0)) == \
            dt.datetime(2026, 10, 28, 12, 0, tzinfo=NY)

    def test_with_no_full_line_the_session_reset(self):
        assert D.reset_after_limit(D.parse_usage(USAGE_OK, T0)) == dt.datetime(2026, 10, 22, 22, 0, tzinfo=NY)


# ---------------------------------------------------------------- the token
class TestTheToken:
    def write(self, tmp_path, text):
        p = tmp_path / "anthropic.env"
        p.write_text(text)
        return p

    def test_the_fleets_token(self, tmp_path):
        p = self.write(tmp_path, f"# the fleet\nCLAUDE_CODE_OAUTH_TOKEN={TOKEN}\n")
        assert D.load_token(p, environ={}) == TOKEN

    @pytest.mark.parametrize("text,why", [
        (None, "no token file"),
        (f"CLAUDE_CODE_OAUTH_TOKEN={TOKEN}\nOTHER=1\n", "exactly one line"),
        ("ANTHROPIC_API_KEY=sk-ant-api03-x\n", "exactly one line"),
        ("CLAUDE_CODE_OAUTH_TOKEN=sk-ant-api03-x\n", "OAuth class"),
    ])
    def test_refused(self, tmp_path, text, why):
        p = self.write(tmp_path, text) if text is not None else tmp_path / "missing.env"
        with pytest.raises(D.Refused, match=why):
            D.load_token(p, environ={})

    @pytest.mark.parametrize("value", [TOKEN * 5, TOKEN + "\x1b", f"'{TOKEN}'", f"{TOKEN} extra",
                                       "\x1b[200~" + TOKEN],
                             ids=["five-copies", "stray-escape", "quoted", "trailing-text",
                                  "bracketed-paste"])
    def test_anything_but_one_token_on_the_line_is_refused(self, tmp_path, value):
        p = self.write(tmp_path, f"CLAUDE_CODE_OAUTH_TOKEN={value}\n")
        with pytest.raises(D.Refused):
            D.load_token(p, environ={})

    def test_an_api_key_in_the_environment_is_refused(self, tmp_path):
        p = self.write(tmp_path, f"CLAUDE_CODE_OAUTH_TOKEN={TOKEN}\n")
        with pytest.raises(D.Refused, match="ANTHROPIC_API_KEY"):
            D.load_token(p, environ={"ANTHROPIC_API_KEY": "sk-ant-api03-x"})

    def test_main_refuses_with_exit_4(self, tmp_path, monkeypatch):
        monkeypatch.setattr(D, "STATE", tmp_path / "state")
        monkeypatch.setattr(D, "TOKEN_FILE", tmp_path / "missing.env")
        assert D.main(["once"]) == 4


class TestOneProcess:
    def test_a_second_dispatcher_is_refused(self, tmp_path):
        held = D.lock(tmp_path)
        try:
            with pytest.raises(D.Refused, match="another dispatcher"):
                D.lock(tmp_path)
        finally:
            held.close()
        D.lock(tmp_path).close()


# ---------------------------------------------------------------- the XO
class TestDue:
    def test_due_when_the_label_is_newer_than_the_ranks_last_comment(self, world):
        fleet, host, clock, _ = world
        mission(host)
        assert fleet.due(21)
        host.issues[21]["comments"].append({"body": "<!-- xo-verdict: back-to-captain round=1",
                                            "createdAt": iso(T0)})
        assert not fleet.due(21)
        clock.t = T0 + dt.timedelta(hours=1)
        host.label(21, "plan:needs-review")
        assert fleet.due(21)

    def test_an_operators_comment_does_not_count(self, world):
        fleet, host, _, _ = world
        mission(host)
        host.issues[21]["comments"].append({"body": "Looks fine to me.", "createdAt": iso(T0)})
        assert fleet.due(21)

    def test_never_labelled_is_not_due(self, world):
        fleet, host, _, _ = world
        mission(host, labels={"mission": T0})
        assert not fleet.due(21)


class TestTheBranch:
    def test_named_in_the_body(self, world):
        fleet, _, _, _ = world
        fleet.update_mirror()
        assert fleet.branch_for(FIXTURE_PHASE, f"branch `{BRANCH}`") == (BRANCH, "")

    def test_named_but_not_on_github(self, world):
        fleet, _, _, _ = world
        fleet.update_mirror()
        b, why = fleet.branch_for(FIXTURE_PHASE, f"branch `phase-{FIXTURE_PHASE}-gone`")
        assert b is None and "not on GitHub" in why

    def test_the_one_head_when_unnamed(self, world):
        fleet, _, _, _ = world
        fleet.update_mirror()
        assert fleet.branch_for(FIXTURE_PHASE, "no branch here") == (BRANCH, "")
        assert fleet.branch_for("90", "")[0] is None   # phase-90-* never matches phase-900-*


class TestOneCycle:
    def test_approve_end_to_end(self, world):
        fleet, host, _, _ = world
        mission(host)
        host.replies = [claude_json(V_APPROVE)]
        fleet.cycle()
        i = host.issues[21]
        assert "plan:approved" in i["labels"] and "plan:needs-review" not in i["labels"]
        assert "mission" in i["labels"]
        assert host.comments(21)[-1].startswith("<!-- xo-verdict: approve round=0")
        (inner, kw), = [(c, k) for c, k in host.fenced if "/usage" not in c]
        assert inner[0] == "claude" and "--model" in inner and rank_call.FABLE in inner
        # Since 389 the token is on a pipe at fd 3, never in the environment.
        assert kw["env"] == {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        assert kw["pass_fds"] == (3,) and callable(kw["preexec_fn"])
        assert all(k["env"]["GH_REPO"] == D.REPO for _, k in host.gh_calls)

    def test_the_fence_gets_the_stage_clone_of_the_phase_branch(self, world):
        fleet, host, _, _ = world
        mission(host)
        host.replies = [claude_json(V_APPROVE)]
        seen = []
        real = host.__call__

        def spy(cmd, **kw):
            if cmd[0] == host.fence and "/usage" not in cmd:
                clone = pathlib.Path(cmd[cmd.index("--clone") + 1])
                seen.append((cmd, subprocess.run(["git", "-C", str(clone), "branch", "--show-current"],
                                                 capture_output=True, text=True).stdout.strip()))
            return real(cmd, **kw)

        fleet.host = spy
        fleet.cycle()
        (cmd, branch), = seen
        assert branch == BRANCH
        assert cmd[cmd.index("--clone") + 1].startswith(str(fleet.runs))
        assert cmd[cmd.index("--workspace-docs") + 1] == str(fleet.workspace_docs)

    def test_once_per_application_of_the_label(self, world):
        fleet, host, clock, _ = world
        mission(host)
        host.replies = [claude_json(V_BACK)]
        fleet.cycle()
        assert host.issues[21]["labels"].count("plan:needs-review") == 1
        clock.t = T0 + dt.timedelta(minutes=5)
        # Since 389 the Captain's revision is next. The issue is a planted trial
        # (Phase 392, F223), so it runs; both its plans fail the checklist, so it
        # stops, label unchanged, and nothing is pushed.
        host.replies = [claude_json({"implementation_md": "# no plan"})] * 2
        fleet.cycle()
        verdicts = lambda: [c for c in host.comments(21) if c.startswith(xo.MARKER)]  # noqa: E731
        assert len(verdicts()) == 1, "a back-to-captain was reviewed again unasked"
        assert host.comments(21)[-1].startswith(f"{D.MARKER} stopped rank=captain")
        clock.t = T0 + dt.timedelta(minutes=10)
        host.label(21, "plan:needs-review")
        host.replies = [claude_json(V_APPROVE)]
        fleet.cycle()
        assert len(verdicts()) == 2 and "plan:approved" in host.issues[21]["labels"]

    def test_a_ranks_stop_leaves_the_label(self, world):
        fleet, host, clock, _ = world
        mission(host)
        host.replies = [claude_json(V_APPROVE, usage=False)]
        fleet.cycle()
        assert "plan:needs-review" in host.issues[21]["labels"]
        assert "plan:approved" not in host.issues[21]["labels"]
        assert "stopped, label unchanged" in host.comments(21)[-1]
        clock.t = T0 + dt.timedelta(minutes=5)
        fleet.cycle()
        assert len(host.model_calls()) == 1

    def test_no_phase_in_the_title_comments_and_runs_nothing(self, world):
        fleet, host, _, _ = world
        host.issue(22, "The fixture", "", {"plan:needs-review": T0})
        fleet.cycle()
        assert host.model_calls() == []
        assert host.issues[22]["labels"] == ["plan:needs-review"]
        assert host.comments(22)[-1].startswith(D.MARKER) and "names no `Phase <N>`" in host.comments(22)[-1]

    def test_no_branch_comments_and_runs_nothing(self, world):
        fleet, host, _, _ = world
        host.issue(23, f"Phase {FIXTURE_PHASE}: gone", f"Mission, branch `phase-{FIXTURE_PHASE}-gone`.",
                   {"plan:needs-review": T0})
        fleet.cycle()
        assert host.model_calls() == []
        assert f"`phase-{FIXTURE_PHASE}-gone` the issue names is not on GitHub" in host.comments(23)[-1]

    def test_a_phase_with_no_active_row_gets_no_stage_and_no_comment(self, world):
        """Since 389: every stage refuses a phase whose row on master is not 🚧."""
        fleet, host, _, lines = world
        host.issue(24, "Phase 777: none", "", {"plan:needs-review": T0})
        fleet.cycle()
        assert host.model_calls() == [] and host.comments(24) == []
        assert any("phase 777's row on master is 'missing'" in ln for ln in lines)

    def test_a_model_call_outside_the_clone_is_a_stop(self, world, tmp_path):
        fleet, host, _, _ = world
        with pytest.raises(rank_call.Stop, match="outside the stage's clone"):
            D.FencedRunner(fleet, tmp_path / "clone", tmp_path / "run")(["claude", "-p", "x"],
                                                                        cwd=tmp_path)


class TestTheRateLimitPauses:
    def test_recorded_commented_paused_then_resumed(self, world):
        fleet, host, clock, _ = world
        # Not a trial: once approved, the Engineer waits for the operator
        # (no account, no trial marker), so the resumed XO is the last model call.
        mission(host, body=f"Mission issue, branch `{BRANCH}`.")
        host.usage_after = USAGE_LIMITED      # the call finds the limit; the gate did not
        host.replies = [LIMITED]
        fleet.cycle()
        paused = fleet.load()["paused"]
        assert paused["session"] == "sess-limited-1" and paused["stage"] == "xo"
        assert D._time(paused["until"]) == dt.datetime(2026, 10, 28, 12, 0, tzinfo=NY)
        assert "plan:needs-review" in host.issues[21]["labels"]
        assert host.comments(21)[-1].startswith(f"{D.MARKER} rate-limited stage=xo session=sess-limited-1")
        assert "label unchanged" in host.comments(21)[-1]

        clock.t = dt.datetime(2026, 10, 28, 11, 0, tzinfo=NY)
        host.label(21, "plan:needs-review")
        fleet.cycle()
        assert len(host.model_calls()) == 1, "a model stage started while paused"

        clock.t = dt.datetime(2026, 10, 28, 12, 1, tzinfo=NY)
        # Phase 393: past Monday 08:00, the weekly page is due; its own tests
        # are 393's, so this week's is marked done.
        fleet.save({**fleet.load(), "last_quality": "2026-10-26"})
        host.usage_text = USAGE_OK
        host.replies = [claude_json(V_APPROVE, session="sess-limited-1"),
                        claude_json({"summary": "A quiet day."}, model=rank_call.HAIKU)]
        fleet.cycle()
        resumed = host.model_calls()[1]
        assert resumed[:3] == ["claude", "--resume", "sess-limited-1"]
        assert "paused" not in fleet.load()
        assert "plan:approved" in host.issues[21]["labels"]
        assert fleet.load()["last_digest"] == "2026-10-27"   # the day's digest after the resume
        assert len(host.model_calls()) == 3, "the approved plan was reviewed again"

    def test_with_no_reset_readable_it_waits_an_hour(self, world):
        fleet, host, _, _ = world
        mission(host)
        host.usage_after = USAGE_BAD
        host.replies = [LIMITED]
        fleet.cycle()
        assert D._time(fleet.load()["paused"]["until"]) == T0 + D.RESET_UNKNOWN

    def test_the_paused_run_is_kept(self, world):
        fleet, host, _, _ = world
        mission(host)
        host.usage_after = USAGE_LIMITED
        host.replies = [LIMITED]
        fleet.cycle()
        run = pathlib.Path(fleet.load()["paused"]["run"])
        for k in range(D.KEEP_RUNS + 2):
            (fleet.runs / f"30000101_00000{k:02d}_x").mkdir(parents=True)
        fleet.prune_runs({str(run)})
        assert run.is_dir() and len(list(fleet.runs.iterdir())) == D.KEEP_RUNS + 1


# ---------------------------------------------------------------- the sweep
class TestTheSweep:
    def test_one_comment_for_a_label_older_than_24_hours(self, world):
        fleet, host, _, _ = world
        # A trial: the sweep's own marker, said as the operator, counts (F223).
        host.issue(9, "Phase 387: the XO", D.fleet_git.TRIAL_MARKER,
                   {"mission": T0 - dt.timedelta(hours=100),
                    "plan:approved": T0 - dt.timedelta(hours=25)})
        assert fleet.sweep() == 1
        body = host.comments(9)[-1]
        assert body.startswith(f"{D.SWEEP_MARKER} label=plan:approved applied=")
        assert "25 hours" in body and "the Chief Engineer" in body
        assert fleet.sweep() == 0, "the same label application was swept twice"

    def test_nothing_under_24_hours_and_mission_is_never_swept(self, world):
        fleet, host, _, _ = world
        host.issue(9, "Phase 387", "", {"mission": T0 - dt.timedelta(hours=100),
                                        "needs-admiral": T0 - dt.timedelta(hours=23)})
        assert fleet.sweep() == 0 and host.comments(9) == []

    def test_a_reapplied_label_is_swept_again_after_24_hours(self, world):
        fleet, host, clock, _ = world
        host.issue(9, "Phase 387", "", {"needs-hands": T0 - dt.timedelta(hours=30)})
        assert fleet.sweep() == 1
        host.label(9, "needs-hands", T0)
        clock.t = T0 + dt.timedelta(hours=25)
        assert fleet.sweep() == 1 and len(host.comments(9)) == 2

    def test_every_state_label_names_who_moves_it(self):
        assert set(D.STATE_LABELS) == set(D.NEXT_RANK)
        assert "mission" not in D.STATE_LABELS and len(D.STATE_LABELS) == 10


# ---------------------------------------------------------------- the digest
class TestTheDigest:
    def test_due_once_a_day_after_seven(self, world):
        fleet, _, clock, _ = world
        clock.t = dt.datetime(2026, 10, 23, 6, 59, tzinfo=NY)
        assert fleet.digest_day() is None
        clock.t = dt.datetime(2026, 10, 23, 7, 0, tzinfo=NY)
        assert fleet.digest_day() == dt.date(2026, 10, 22)
        fleet.save({"last_digest": "2026-10-22"})
        assert fleet.digest_day() is None

    def test_written_through_the_fence_and_kept(self, world):
        fleet, host, clock, _ = world
        clock.t = dt.datetime(2026, 10, 23, 7, 5, tzinfo=NY)
        fleet.update_mirror()
        host.replies = [claude_json({"summary": "A quiet day."}, model=rank_call.HAIKU)]
        assert fleet.stage_digest(dt.date(2026, 10, 22)).startswith("written")
        kept = fleet.state_dir / "digests" / "2026-10-22.md"
        assert kept.is_file() and "A quiet day." in kept.read_text()
        assert fleet.load()["last_digest"] == "2026-10-22"
        assert host.model_calls()[0][0] == "claude"

    def test_a_stop_records_nothing(self, world):
        fleet, host, clock, _ = world
        clock.t = dt.datetime(2026, 10, 23, 7, 5, tzinfo=NY)
        fleet.update_mirror()
        host.replies = [claude_json({"summary": "x"}, model=rank_call.HAIKU, usage=False)]
        assert fleet.stage_digest(dt.date(2026, 10, 22)) == "stopped"
        assert fleet.load()["last_digest"] == "2026-10-21"
        assert fleet.digest_day() == dt.date(2026, 10, 22), "the next cycle does not try again"

    def test_no_digest_while_paused(self, world):
        fleet, host, clock, _ = world
        clock.t = dt.datetime(2026, 10, 23, 7, 5, tzinfo=NY)
        fleet.save({"paused": {"stage": "xo", "until": iso(clock.t + dt.timedelta(hours=2)),
                               "run": "", "session": "s", "issue": 1, "phase": "900"}})
        fleet.cycle()
        assert host.model_calls() == [] and not (fleet.state_dir / "digests").exists()
