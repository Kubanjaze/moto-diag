#!/usr/bin/env python3
"""Phase 255D push guard. Blocks `git push` when closeout is incomplete.

Since 2026-09-24 it also blocks ANY `git push` while the ROADMAP has drifted
from docs/phases/ (`roadmap_check.py`). Close-out is guarded on `master`
only because it cannot be complete mid-phase; continuity can always be true
mid-phase — a phase's row exists before its Step 0 — so a work-in-progress
push is no reason to let the ledger lie.

Since Phase 358 (K1) it also runs the whole-tree command on every push, and
guards a commit that changes seed data or migrations:

* **A push** is let through only when every commit it sends has a record
  that `wholetree.sh` wrote for that exact commit, tree and script (see
  wholetree.py). With no record, the guard runs fast mode itself — only on
  the checked-out commit, on a clean tree — under `FAST_LIMIT_S`, and
  blocks on a failure or when time runs out.
* **A commit** that changes `src/motodiag/knowledge/seed/` or
  `src/motodiag/core/migrations.py` needs a `wholetree.sh --full` record for
  exactly the tree being committed.

**Why it fails closed on time, and what that rests on.** Phase 358 measured
that a `PreToolUse` hook that outruns its `timeout` is killed and the
command PROCEEDS, and the hooks documentation says the same. So the guard
keeps its own clock: a bounded run of fast mode, and an alarm over the whole
push check, both far inside the hook's 600 s. A timeout blocks.

**This script filters itself, and that is not a stylistic choice.** Phase
255D measured that `PreToolUse` ignores the `if` field in this build, while
`PostToolUse` honours it — same field, same value, same matcher, opposite
behaviour. A guard relying on `if` fires on EVERY Bash command, which is
what happened during D1: a blocking guard meant for `git push` blocked a
`cat`, and took away the shell needed to remove itself.

So the contract here is deliberately lopsided:

* **Exit 0 as early as possible.** Anything not recognised as a `git push`
  or `git commit` leaves in the first few lines, before any file is read or
  any test is run. A guard that can fail while deciding whether to guard is
  the lockout bug again.
* **Exit 2 only for a real `git push` or `git commit` with a real failure**,
  because exit 2 is what blocks the call and returns stderr to the model.
* **The ledger and close-out checks exit 0 on an internal error; the
  whole-tree checks exit 2.** The first two predate 358 and never lock out
  the shell. The whole-tree checks fail closed, as the operator required:
  they can only ever block a push or a commit, never a `cat`.

Recovery, if a guard ever does block `Bash`: edit `.claude/settings.json`
with the **Write tool**, which does not pass through a `Bash` matcher.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Shell operators that begin a new command within one command line. A
# newline does too; heredoc bodies are stripped before the split, so a line
# of a commit message is never read as a command.
_SEP = re.compile(r"(?:&&|\|\||[;|&\n])")
# A heredoc: `<<'EOF'`, `<<"EOF"`, `<<-EOF`, `<<EOF`, through its end line.
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?^\s*\2\s*$", re.S | re.M)


def _strip_heredocs(command: str) -> str:
    """Remove heredoc bodies, keeping the line that opens each one.

    A commit message in a heredoc holds `;`, `&` and apostrophes. Left in,
    they split the `git commit` line into fragments shlex cannot parse, and
    the commit goes unseen.
    """
    return _HEREDOC.sub(lambda m: m.group(0).split("\n", 1)[0].split("<<", 1)[0], command or "")


def _git_invocations(command: str):
    """(subcommand, args) for each segment that runs git. `args` is None when
    the segment names the subcommand but cannot be parsed further."""
    for segment in _SEP.split(_strip_heredocs(command)):
        try:
            words = shlex.split(segment)
        except ValueError:            # unbalanced quotes — not parseable
            m = re.match(r"\s*(?:\S*/)?git\s+(push|commit)\b", segment)
            if m:
                yield m.group(1), None
            continue
        # Skip env assignments, then git's own options (-C path, -c k=v).
        while words and ("=" in words[0] and not words[0].startswith("/")):
            words = words[1:]
        if not words or pathlib.Path(words[0]).name != "git":
            continue
        rest = words[1:]
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in ("-C", "-c") else rest[1:]
        if rest:
            yield rest[0], rest[1:]


def is_git_push(command: str) -> bool:
    """Whether the command line actually runs `git push`.

    Split on shell operators, then check each segment's first two words.
    `echo "git push"` is NOT a push: the words appear inside a quoted
    argument, and shlex keeps them together as one token. v1.1-3 requires
    that such a command passes, because the cost of a false block is the
    lockout and the cost of a false pass is caught by the test.
    """
    return any(sub == "push" for sub, _ in _git_invocations(command))


def is_git_commit(command: str) -> bool:
    return any(sub == "commit" for sub, _ in _git_invocations(command))


#: git subcommands that can move HEAD or a branch. The hook judges a command
#: line BEFORE any of it runs, so `git commit … && git push` would have its
#: push checked against the old HEAD and then push a commit nobody checked.
_MOVES_HEAD = {"commit", "merge", "rebase", "reset", "cherry-pick", "revert", "pull",
               "am", "checkout", "switch", "stash", "branch", "update-ref"}


def moves_head_before_push(command: str) -> str | None:
    """The first HEAD-moving git subcommand that precedes a push in the same
    command line, or None."""
    subs = [s for s, _ in _git_invocations(command)]
    if "push" not in subs:
        return None
    return next((s for s in subs[:subs.index("push")] if s in _MOVES_HEAD), None)


def _push_args(command: str) -> list[str] | None:
    for sub, args in _git_invocations(command):
        if sub == "push":
            return args
    return []


def targets_master(command: str, repo: pathlib.Path) -> bool:
    """Whether this push puts commits on `master`.

    **Why the guard is narrower than "any push".** Close-out is what must
    happen before work reaches `master`. A phase branch is pushed many times
    while the phase is still open — that is normal and is not a skipped
    close-out. A guard that blocked every push would block every
    work-in-progress push for the whole phase, and the only way to work
    would be to disable the guard, which is worse than not having one.

    So: a push is guarded when it names `master` as a refspec, or when it
    names no refspec and the checkout is on `master`.
    """
    words = _push_args(command) or []
    refs = [w for w in words if not w.startswith("-")]
    if any(w == "master" or w.endswith(":master") or w.startswith("master:")
           for w in refs):
        return True
    if len(refs) > 1:            # an explicit non-master refspec was given
        return False
    head = (repo / ".git" / "HEAD")
    try:
        return head.read_text(encoding="utf-8").strip().endswith("/master")
    except OSError:
        return False


def current_phase(repo: pathlib.Path) -> str | None:
    """The phase with documents still in in_progress/, if exactly one."""
    d = repo / "docs" / "phases" / "in_progress"
    if not d.is_dir():
        return None
    phases = {m.group(1) for f in d.glob("*.md")
              if (m := re.match(r"^(\d+[A-Z]?)_", f.name))}
    return phases.pop() if len(phases) == 1 else None


# ------------------------------------------------------ K1: the whole tree
_PUSH_OPTS_WITH_ARG = {"--repo", "-o", "--push-option", "--receive-pack", "--exec"}
_PUSH_ALL = {"--all", "--mirror", "--tags", "--branches"}
_COMMIT_LONG_WITH_ARG = {"--message", "--file", "--reuse-message", "--reedit-message",
                         "--author", "--date", "--template", "--fixup", "--squash",
                         "--cleanup", "--trailer", "--pathspec-from-file"}


def _rev(repo: pathlib.Path, spec: str) -> str | None:
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", spec],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def pushed_commits(command: str, repo: pathlib.Path) -> list[str] | None:
    """The commits a push sends, or None when that cannot be told."""
    args = _push_args(command)
    if args is None:
        return None
    positional, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in _PUSH_ALL:
            return None
        elif a in _PUSH_OPTS_WITH_ARG:
            skip = True
        elif a[:1] in "<>" or a.startswith("2>"):
            continue
        elif not a.startswith("-"):
            positional.append(a)
    out = []
    for ref in positional[1:] or ["HEAD"]:
        src = ref.lstrip("+").split(":", 1)[0]
        if not src:                  # `:branch` deletes; nothing is sent
            continue
        commit = _rev(repo, f"{src}^{{commit}}")
        if commit is None:
            return None
        out.append(commit)
    return out


def _log(repo: pathlib.Path, line: str) -> None:
    try:
        import wholetree
        d = wholetree.records_dir(repo)
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "guard.log", "a", encoding="utf-8") as f:
            import datetime as dt
            f.write(f"{dt.datetime.now().isoformat(timespec='seconds')} {line}\n")
    except Exception:
        pass


def wholetree_gate(command: str, repo: pathlib.Path, run=None) -> list[str]:
    """[] when every pushed commit has a whole-tree pass; else why not."""
    import wholetree as W
    commits = pushed_commits(command, repo)
    if commits is None:
        return ["the guard cannot tell which commits this push sends (--all, --mirror, "
                "--tags, or a ref that does not resolve). Push a named branch."]
    head = _rev(repo, "HEAD")
    for c in commits:
        tree = _rev(repo, f"{c}^{{tree}}")
        rec, why = W.valid_record(tree, ("fast", "full"), c, root=repo)
        if rec is not None:
            _log(repo, f"push {c[:12]}: accepted {rec['mode']} record")
            continue
        if c != head or W.tested_state(repo) != (head, tree):
            _log(repo, f"push {c[:12]}: blocked, no record ({why}) and not testable in place")
            return [f"no whole-tree record for {c[:12]} ({why}). The guard can only test "
                    "the checked-out commit on a clean tree. Run "
                    ".claude/skills/closeout/wholetree.sh on a clean checkout of it, "
                    "then push again."]
        _log(repo, f"push {c[:12]}: no record ({why}); running fast mode, limit "
                   f"{W.FAST_LIMIT_S} s")
        res = (run or W.run_bounded)("fast", W.FAST_LIMIT_S, repo)
        if res.timed_out:
            _log(repo, f"push {c[:12]}: blocked, fast mode ran out of time")
            return [f"the whole-tree fast mode ran out of time ({W.FAST_LIMIT_S} s) and "
                    "the push is blocked: the guard fails closed. Run wholetree.sh "
                    "yourself, then push again."]
        if not res.passed:
            _log(repo, f"push {c[:12]}: blocked, fast mode failed")
            return [f"the whole-tree fast mode failed:\n{res.summary}"]
        rec, why = W.valid_record(tree, ("fast",), c, root=repo)
        if rec is None:
            return [f"fast mode passed but left no valid record: {why}"]
        _log(repo, f"push {c[:12]}: fast mode passed in {res.wall:.1f} s")
    return []


def _commit_parse(args: list[str]) -> tuple[bool, list[str]]:
    """(-a given, pathspecs) from `git commit` arguments."""
    all_, paths, i, dd = False, [], 0, False
    while i < len(args):
        a = args[i]
        if dd:
            paths.append(a)
        elif a == "--":
            dd = True
        elif a in ("<", ">", ">>", "2>", "&>"):
            i += 1
        elif a[:1] in "<>" or a.startswith("2>"):
            pass
        elif a in ("-a", "--all"):
            all_ = True
        elif a.startswith("--"):
            if "=" not in a and a in _COMMIT_LONG_WITH_ARG:
                i += 1
        elif a.startswith("-") and len(a) > 1:
            for j, ch in enumerate(a[1:]):
                if ch == "a":
                    all_ = True
                if ch in "mFCct":
                    if j == len(a) - 2:
                        i += 1           # the option's argument is the next word
                    break                # or the rest of this word
        else:
            paths.append(a)
        i += 1
    return all_, paths


def _tree_with(repo: pathlib.Path, *, all_: bool = False, paths: list[str] = ()) -> str:
    """The tree `git commit` would record, computed on a temporary index."""
    g = ["git", "-C", str(repo)]
    if not all_ and not paths:
        return subprocess.run(g + ["write-tree"], capture_output=True, text=True,
                              check=True).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": os.path.join(tmp, "index")}
        if paths:
            subprocess.run(g + ["read-tree", "HEAD"], env=env, check=True, capture_output=True)
            subprocess.run(g + ["add", "--", *paths], env=env, check=True, capture_output=True)
        else:
            real = subprocess.run(g + ["rev-parse", "--git-path", "index"], capture_output=True,
                                  text=True, check=True).stdout.strip()
            real = real if os.path.isabs(real) else os.path.join(repo, real)
            shutil.copy(real, env["GIT_INDEX_FILE"])
            subprocess.run(g + ["add", "-u"], env=env, check=True, capture_output=True)
        return subprocess.run(g + ["write-tree"], env=env, capture_output=True, text=True,
                              check=True).stdout.strip()


def content_commit_gate(command: str, repo: pathlib.Path) -> list[str]:
    """[] unless the commit changes seed data or migrations.py without a
    `wholetree.sh --full` record for exactly the tree being committed."""
    import wholetree as W
    args = next((a for s, a in _git_invocations(command) if s == "commit"), None)
    if args is None:                  # unparseable: judge both shapes it could be
        trees = {_tree_with(repo), _tree_with(repo, all_=True)}
    else:
        all_, paths = _commit_parse(args)
        trees = {_tree_with(repo, all_=all_, paths=paths)}
    head_tree = _rev(repo, "HEAD^{tree}")
    for tree in trees:
        changed = subprocess.run(["git", "-C", str(repo), "diff-tree", "-r", "--name-only",
                                  head_tree, tree], capture_output=True, text=True,
                                 check=True).stdout.split()
        content = [p for p in changed if p.startswith(W.CONTENT_PATHS)]
        if not content:
            continue
        rec, why = W.valid_record(tree, ("full",), None, root=repo)
        if rec is None:
            _log(repo, f"commit of tree {tree[:12]}: blocked, content without --full ({why})")
            return [f"this commit changes seed data or migrations ({', '.join(content[:5])}) "
                    f"and has no `wholetree.sh --full` record for the tree it commits ({why}). "
                    "Stage the change, run .claude/skills/closeout/wholetree.sh --full with "
                    "nothing unstaged or untracked, then commit."]
        _log(repo, f"commit of tree {tree[:12]}: content, accepted --full record")
    return []


def _out_of_time(*_):
    print("the push guard ran out of time and blocks the push: it fails closed.",
          file=sys.stderr)
    os._exit(2)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0                                   # not our shape; stay out
    command = (payload.get("tool_input") or {}).get("command", "")
    if is_git_commit(command) and not is_git_push(command):
        try:
            fails = content_commit_gate(command, HERE.parents[2])
        except Exception as e:                     # fails closed; only a commit is blocked
            fails = [f"the content-commit check could not run ({e!r}); the commit is blocked"]
        if fails:
            print("\n".join(fails), file=sys.stderr)
            return 2
        return 0
    if not is_git_push(command):
        return 0                                   # THE early exit

    mover = moves_head_before_push(command)
    if mover:
        print(f"whole-tree check: push blocked. This command runs `git {mover}` before "
              "`git push`, and the guard judges the push before any of it runs, so it "
              f"would push a commit it never saw. Run `git {mover}` and `git push` as "
              "separate commands.", file=sys.stderr)
        return 2

    try:
        import roadmap_check                       # the SAME function the test calls
        drift = roadmap_check.check_tree()
    except Exception:
        drift = []                                 # never lock out the shell
    if drift:
        print("the ROADMAP has drifted from docs/phases/; push blocked.\n"
              + "\n".join("  " + f for f in drift)
              + "\n\nUpdate docs/ROADMAP.md (CLAUDE.md: a phase's row exists before "
                "its Step 0 and changes with the work), then push again. "
                "tests/test_roadmap_continuity.py is the guarantee, and it calls "
                "the same function.", file=sys.stderr)
        return 2

    repo = HERE.parents[2]
    try:
        import wholetree
        signal.signal(signal.SIGALRM, _out_of_time)
        signal.alarm(wholetree.FAST_LIMIT_S + 60)  # far inside the hook's 600 s
        fails = wholetree_gate(command, repo)
        signal.alarm(0)
    except Exception as e:                         # fails closed: only a push is blocked
        fails = [f"the whole-tree check could not run ({e!r}); the push is blocked"]
    if fails:
        print("whole-tree check: push blocked.\n" + "\n".join(fails), file=sys.stderr)
        return 2

    try:
        if not targets_master(command, repo):
            return 0                               # a phase-branch push
        phase = current_phase(repo)
        if phase is None:
            return 0                               # nothing mid-flight
        from closeout_check import check           # the SAME function the test calls
        fails = check(repo, phase)
    except Exception:
        return 0                                   # never lock out the shell

    if fails:
        print(f"closeout is not complete for phase {phase}; push blocked.\n"
              + "\n".join("  " + f for f in fails)
              + "\n\nFinish the close-out, or push again once these pass. "
                "This guard is only the earlier feedback — "
                "tests/test_phase255D_closeout_contract.py is the guarantee, "
                "and it calls the same function.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
