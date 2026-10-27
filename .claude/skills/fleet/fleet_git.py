"""What the dispatcher checks before it pushes, and whose name it pushes in.

The repository's push guard is a Claude Code hook: it fires on a `git push`
inside a session's tool loop and nowhere else (the fleet proposal,
"Guardrails"). The dispatcher pushes from outside any session, after a
rank's stage, so it runs its own gate here, with the closeout skill's own
functions where one exists (`roadmap_check.check_tree`), and a
model-free test run the caller supplies (a whole-tree record written inside
a fence is signed with a key the rank inside can read: Phase 389, S0-4).

**The gate** (`gate`), each refusal naming itself:
  G1  the branch is `phase-<N>-…` and never `master`
  G2  the push is a fast-forward of what GitHub has
  G3  every changed path is one the rank may touch (`may_touch`)
  G4  no added line holds a credential
  G5  the ledger holds: `roadmap_check.check_tree` on the clone
  G6  the commit pushed passed a run no model touched

**The identity** (`identity`): the fleet's machine user, from
`~/.config/motodiag/fleet-github.env` (mode 600: the account and its
token), named on the one command that pushes; without that file, the
operator's own login, and only for an issue planted as a trial (its body
carries `TRIAL_MARKER`): the operator's pre-approval (b) for Phase 389,
"a planted trial mission may use my login until the identity exists".
Anything else is `NeedsHands`.
"""
from __future__ import annotations

import os
import pathlib
import re
import stat
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "closeout"))
import roadmap_check  # noqa: E402

REPO_URL = "https://github.com/Kubanjaze/moto-diag.git"
IDENTITY_FILE = pathlib.Path.home() / ".config" / "motodiag" / "fleet-github.env"
MOBILE = pathlib.Path(os.environ.get("FLEET_MOBILE")
                      or pathlib.Path.home() / "Projects" / "moto-diag-mobile")
TRIAL_MARKER = "<!-- fleet-trial -->"
#: Until the machine user exists: a reserved, non-routable domain (RFC 2606).
PLACEHOLDER_EMAIL = "fleet@motodiag.invalid"

#: Paths no rank's push may change: the guards, what loads them, the fleet's
#: own code, and the operator's rules ("never loosen a guard"; CLAUDE.md is
#: the Admiral's, the fleet proposal's standing orders).
NEVER = ("CLAUDE.md", ".claude/settings.json", ".claude/settings.local.json",
         ".claude/skills/closeout/edit_guard.sh", ".claude/skills/closeout/_edit_guard.py",
         ".claude/skills/closeout/pre_push_guard.sh", ".claude/skills/closeout/_pre_push_guard.py",
         ".claude/skills/fleet/")
ROADMAP = "docs/ROADMAP.md"
FOLLOWUPS = "docs/FOLLOWUPS.md"

#: A credential in an added line. Long enough that a test's fake token
#: ("sk-ant-oat01-test-token") is not one; a real OAuth token runs to about
#: a hundred characters (388's step 1 measured 108).
SECRET = re.compile(r"sk-ant-[a-z]{2,4}\d{2}-[A-Za-z0-9_-]{60,}|sk-gw-[A-Za-z0-9_-]{32,}|"
                    r"\bghp_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{60,}|\bgho_[A-Za-z0-9]{36}\b")
_GH_TOKEN = re.compile(r"(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,})")

Runner = Callable[..., subprocess.CompletedProcess]


class NeedsHands(Exception):
    """A push no identity may make yet: the operator's step comes first."""


# ------------------------------------------------------------------ paths
def may_touch(rank: str, phase: str, path: str) -> bool:
    """Whether `rank`'s push may change `path` (G3)."""
    if any(path == n or (n.endswith("/") and path.startswith(n)) for n in NEVER):
        return False
    if rank == "scout":
        return (path == f"docs/phases/in_progress/{phase}_step0.md"
                or re.fullmatch(rf"docs/prompts/{re.escape(phase)}_[a-z0-9_]+\.txt", path) is not None)
    if rank == "captain":
        return path == f"docs/phases/in_progress/{phase}_implementation.md"
    if rank == "red-team-record":
        # The phase log's table, and (Phase 392, F228) the one finding the
        # wording it left open goes to: an entry added, nothing removed (G3).
        return path in (f"docs/phases/in_progress/{phase}_phase_log.md",
                        f"docs/phases/completed/{phase}_phase_log.md", FOLLOWUPS)
    if rank == "row":
        # The next mission's one-row pull request (Phase 392, K49): the
        # ROADMAP only, and in it only the phase's status (G3, below).
        return path == ROADMAP
    return rank == "engineer"


def row_status_only(diff: str, phase: str) -> list[str]:
    """Why a `row` push's ROADMAP diff is more than the phase's row going 🚧."""
    minus = [ln[1:] for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---")]
    plus = [ln[1:] for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    if len(minus) != 1 or len(plus) != 1:
        return [f"G3 the row may change one line, phase {phase}'s row, not "
                f"{len(minus)} removed and {len(plus)} added"]
    if not re.match(rf"\| {re.escape(phase)} \|", minus[0]):
        return [f"G3 the row may change only phase {phase}'s row, not {minus[0][:40]!r}"]
    cells = minus[0].split("|")
    cells[3] = f" {roadmap_check.ACTIVE} "
    if plus[0] != "|".join(cells):
        return [f"G3 the row may change only phase {phase}'s status, to {roadmap_check.ACTIVE}"]
    return []


def roadmap_rows_removed(diff: str) -> list[str]:
    """The ROADMAP rows a diff removes or changes (a removed `| N |` line)."""
    return [ln[1:] for ln in diff.splitlines()
            if ln.startswith("-") and not ln.startswith("---") and re.match(r"-\| *\d", ln)]


# ------------------------------------------------------------------- gate
def _git(clone: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True)


def gate(clone: pathlib.Path, *, rank: str, phase: str, branch: str, base: str,
         tested: Callable[[str], tuple[bool, str]], mobile: pathlib.Path | None = MOBILE
         ) -> list[str]:
    """Why HEAD of `clone` may not be pushed to `branch`; [] when it may.
    `base` is the commit GitHub has for the branch (master's, for a new one)."""
    fails: list[str] = []
    if branch == "master" or not re.fullmatch(rf"phase-{re.escape(phase)}-[A-Za-z0-9._-]+", branch):
        fails.append(f"G1 the branch {branch!r} is not phase-{phase}-…")
    head = _git(clone, "rev-parse", "HEAD").stdout.strip()
    if _git(clone, "merge-base", "--is-ancestor", base, head).returncode != 0:
        fails.append(f"G2 {head[:12]} is not a fast-forward of {base[:12]}")
        return fails
    names = _git(clone, "diff", "--name-only", f"{base}..{head}").stdout.split()
    if not names:
        fails.append("G3 nothing to push")
    for path in names:
        if not may_touch(rank, phase, path):
            fails.append(f"G3 the {rank} may not change {path}")
    if rank == "engineer" and ROADMAP in names:
        own = re.compile(rf"\| *{re.escape(phase)} *\|")
        others = [r for r in roadmap_rows_removed(_git(clone, "diff", f"{base}..{head}", "--",
                                                       ROADMAP).stdout) if not own.match(r)]
        fails += [f"G3 the engineer may not change another phase's row: {r[:60]!r}" for r in others]
    if rank == "row" and ROADMAP in names:
        fails += row_status_only(_git(clone, "diff", f"{base}..{head}", "--", ROADMAP).stdout,
                                 phase)
    if rank == "red-team-record" and FOLLOWUPS in names:
        gone = [ln for ln in _git(clone, "diff", f"{base}..{head}", "--", FOLLOWUPS).stdout
                .splitlines() if ln.startswith("-") and not ln.startswith("---")
                and "highest assigned is **F" not in ln]
        fails += [f"G3 the {rank} may only add to {FOLLOWUPS}, not change {ln[1:61]!r}"
                  for ln in gone]
    added = [ln[1:] for ln in _git(clone, "diff", f"{base}..{head}").stdout.splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    if any(SECRET.search(ln) for ln in added):
        fails.append("G4 an added line holds what looks like a credential")
    drift = roadmap_check.check_tree(clone, mobile if mobile and mobile.is_dir() else None)
    fails += [f"G5 {d}" for d in drift]
    if not fails:
        ok, why = tested(head)
        if not ok:
            fails.append(f"G6 {head[:12]} did not pass a model-free run: {why}")
    return fails


# --------------------------------------------------------------- identity
@dataclass(frozen=True)
class Identity:
    login: str              # the GitHub account, or "operator" for the ambient login
    token: str | None       # None: the operator's own gh login, ambient

    @property
    def is_fleet(self) -> bool:
        return self.token is not None

    def author(self, rank: str) -> tuple[str, str]:
        email = f"{self.login}@users.noreply.github.com" if self.is_fleet else PLACEHOLDER_EMAIL
        return f"MotoDiag fleet ({rank})", email

    def env(self) -> dict[str, str]:
        """What `gh` needs for this identity, added to its environment."""
        return {"GH_TOKEN": self.token} if self.token else {}


def read_identity_file(path: pathlib.Path = IDENTITY_FILE) -> Identity | None:
    """The fleet's account, or None when the operator has not made it yet.
    A file that is there but wrong is refused outright, never ignored."""
    if not path.exists():
        return None
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise NeedsHands(f"{path} is readable by others; it must be mode 600")
    fields = dict(ln.split("=", 1) for ln in path.read_text(encoding="utf-8").splitlines()
                  if "=" in ln)
    user, token = fields.get("FLEET_GITHUB_USER", ""), fields.get("FLEET_GITHUB_TOKEN", "")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", user) or not _GH_TOKEN.fullmatch(token):
        raise NeedsHands(f"{path} must hold FLEET_GITHUB_USER and one FLEET_GITHUB_TOKEN")
    if user.lower() == "kubanjaze":
        raise NeedsHands(f"{path} names the operator's own account, not the fleet's")
    return Identity(user, token)


def identity(issue_body: str, path: pathlib.Path = IDENTITY_FILE) -> Identity:
    """Whose name a push for this issue goes out in."""
    fleet = read_identity_file(path)
    if fleet is not None:
        return fleet
    if TRIAL_MARKER in (issue_body or ""):
        return Identity("operator", None)
    raise NeedsHands("the fleet has no GitHub account of its own yet, and this issue is not a "
                     "planted trial: the operator's step 1 in 389_operator_steps.md comes first")


#: The operator's GitHub login: the repository's owner.
OPERATOR_LOGIN = "Kubanjaze"


def trusted_authors(issue_body: str, path: pathlib.Path = IDENTITY_FILE) -> set[str]:
    """Whose comments on this issue a rank may read as a marker (Phase 392,
    F223): the fleet's account, and the operator's only on an issue planted
    as a trial, the push identity's own rule. The repository is public, so
    anyone can comment; nobody else's words are a rank's."""
    try:
        fleet = read_identity_file(path)
    except NeedsHands:
        fleet = None
    out = {fleet.login} if fleet is not None else set()
    if TRIAL_MARKER in (issue_body or ""):
        out.add(OPERATOR_LOGIN)
    return out


def from_trusted(comments: list[dict], authors: set[str]) -> list[dict]:
    """The comments whose author is one of `authors`; GitHub's login case is
    not significant."""
    want = {a.lower() for a in authors}
    return [c for c in comments if str((c.get("author") or {}).get("login", "")).lower() in want]


def opened_by_trusted(issue: dict, path: pathlib.Path = IDENTITY_FILE) -> bool:
    """An issue a rank may work: opened by the fleet's account or the
    operator. A third account's `Phase <N>: …` issue is never a mission."""
    try:
        fleet = read_identity_file(path)
    except NeedsHands:
        fleet = None
    login = str((issue.get("author") or {}).get("login", "")).lower()
    return login in {OPERATOR_LOGIN.lower(), *([fleet.login.lower()] if fleet else [])}


def push_argv(clone: pathlib.Path, branch: str, ident: Identity, url: str = REPO_URL) -> list[str]:
    """The one command that pushes. For the fleet's account the credential
    helpers are reset (`-c credential.helper=`), so the operator's `gh`
    helper in ~/.gitconfig is never asked, and the token comes from this
    process's environment (FLEET_PUSH_TOKEN), never its command line."""
    git = ["git", "-C", str(clone)]
    if ident.is_fleet:
        git += ["-c", "credential.helper=", "-c",
                "credential.helper=!f() { echo username=" + ident.login
                + "; echo \"password=$FLEET_PUSH_TOKEN\"; }; f"]
    return [*git, "push", "-q", url, f"HEAD:refs/heads/{branch}"]


def push(clone: pathlib.Path, branch: str, ident: Identity, *, run: Runner = subprocess.run,
         url: str = REPO_URL) -> subprocess.CompletedProcess:
    env = {**os.environ}
    env.pop("FLEET_PUSH_TOKEN", None)
    if ident.is_fleet:
        env["FLEET_PUSH_TOKEN"] = ident.token
    return run(push_argv(clone, branch, ident, url), capture_output=True, text=True, env=env,
               timeout=300)
