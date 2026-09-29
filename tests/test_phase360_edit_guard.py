"""Phase 360 — the edit guard.

The rule "targeted edits only on source and tests" was broken twice by the
tool meant to keep it: 356 edited `src/` with an exact-match replace in a
heredoc-fed Python script, 357 appended to `src/` with `cat >> … <<'EOF'`.
The guard is a `PreToolUse` hook on Bash. These tests drive its wrapper the
way Claude Code does, with the hook payload as JSON on stdin, as
`test_phase255D_closeout_contract.py` drives the push guard.

Every blocked form has a planted positive control that must come back
exit 2; every form a session needs has a negative control that must come
back exit 0. `{tmp}` is a directory outside the checkout (the scratchpad's
stand-in); `{repo}` is the checkout.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
SKILL = REPO / ".claude" / "skills" / "closeout"
GUARD = SKILL / "edit_guard.sh"


def _run(command: str, cwd: pathlib.Path | str = REPO, guard: pathlib.Path = GUARD,
         raw: str | None = None) -> subprocess.CompletedProcess:
    payload = raw if raw is not None else json.dumps(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash", "cwd": str(cwd),
         "tool_input": {"command": command}})
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(REPO)}
    env.pop("UNKNOWN_VAR_360", None)
    return subprocess.run([str(guard)], input=payload, capture_output=True, text=True,
                          timeout=60, env=env)


def _fill(command: str, tmp: pathlib.Path) -> str:
    return command.replace("{tmp}", str(tmp)).replace("{repo}", str(REPO))


def assert_blocked(r: subprocess.CompletedProcess, why: str = "") -> None:
    assert r.returncode == 2, f"expected a block, got exit {r.returncode}: {r.stderr}"
    assert "edit guard: blocked" in r.stderr
    assert why in r.stderr, r.stderr


def assert_allowed(r: subprocess.CompletedProcess) -> None:
    assert r.returncode == 0, f"expected no block, got exit {r.returncode}: {r.stderr}"
    assert r.stderr == ""


class TestTheAssertionsCanFail:
    """Each helper is shown red on the other's output first."""

    def test_assert_blocked_fails_on_an_allowed_command(self):
        with pytest.raises(AssertionError):
            assert_blocked(_run("ls -la"))

    def test_assert_allowed_fails_on_a_blocked_command(self):
        with pytest.raises(AssertionError):
            assert_allowed(_run("echo x > src/motodiag/_planted.py"))

    def test_assert_blocked_fails_on_the_wrong_reason(self):
        with pytest.raises(AssertionError):
            assert_blocked(_run("echo x > src/motodiag/_planted.py"), "patch")


# ---------------------------------------------------------------- blocked
SED = [
    "sed -i 's/a/b/' src/motodiag/__init__.py",
    "sed -i.bak 's/a/b/' docs/anything.md",
    "sed -i '' 's/a/b/' /tmp/anything",
    "sed --in-place 's/a/b/' {tmp}/x",
    "sed --in-place=.bak -e 's/a/b/' {tmp}/x",
    "sed -Ei 's/a/b/' {tmp}/x",
    "sed -ni 'p' {tmp}/x",
    "sed -ie 's/a/b/' {tmp}/x",
    "sed -e 's/a/b/' -i {tmp}/x",
    "gsed -i 's/a/b/' {tmp}/x",
    "grep -l foo src | xargs sed -i 's/a/b/'",
    "find src -name '*.py' -exec sed -i 's/a/b/' {} \\;",
    "env LC_ALL=C sed -i 's/a/b/' {tmp}/x",
    "/usr/bin/sed -i '' 's/a/b/' {tmp}/x",
]

PERL = [
    "perl -pi -e 's/a/b/' src/motodiag/__init__.py",
    "perl -i.bak -pe 's/a/b/' {tmp}/x",
    "perl -i -pe 's/a/b/' {tmp}/x",
    "perl -pie 's/a/b/' {tmp}/x",
]

REDIRECT = [
    "echo x > src/motodiag/_planted.py",
    "echo x >> src/motodiag/_planted.py",
    "echo x >| tests/_planted.py",
    "ls &> tests/_planted.log",
    "ls &>> tests/_planted.log",
    "ls 2> tests/_planted.log",
    "printf 'x\\n' >> tests/test_planted.py",
    "echo x >& tests/_planted.log",
    "cat 3<> src/motodiag/_planted.py",
    "echo x > {repo}/src/motodiag/_planted.py",
    "cd src && echo x > motodiag/_planted.py",
    "cd {repo}/tests && echo x > _planted.py",
    "D={repo}/tests; echo x > $D/_planted.py",
    'echo x > "$CLAUDE_PROJECT_DIR/tests/_planted.py"',
    "echo x > ./src/../src/motodiag/_planted.py",
    # 357's form: an append to source through a heredoc.
    "cat >> src/motodiag/cli/workflow.py <<'EOF'\ndef planted():\n    pass\nEOF",
    "cat > tests/test_planted.py <<'EOF'\nimport os\nEOF",
    "x=$(echo y > tests/_planted.py)",
]

TEE = [
    "echo x | tee src/motodiag/_planted.py",
    "echo x | tee -a tests/_planted.py",
    "echo x | tee {tmp}/a tests/_planted.py",
]

CP = [
    "cp {tmp}/x.py src/motodiag/_planted.py",
    "cp -r {tmp}/d tests/",
    "cp -t tests {tmp}/a {tmp}/b",
    "cp --target-directory=src {tmp}/a",
    "cp -v {tmp}/x.py {repo}/tests/_planted.py",
]

MV = [
    "mv {tmp}/x.py tests/_planted.py",
    "mv src/motodiag/a.py src/motodiag/b.py",
    "mv -t src {tmp}/a",
    "mv -f {tmp}/a {repo}/src/motodiag/",
]

PATCH = [
    "patch src/motodiag/cli/main.py < {tmp}/fix.diff",
    "patch -p1 < {tmp}/fix.diff",
    "patch -d src -p1 < {tmp}/fix.diff",
    "patch -o tests/_planted.py {tmp}/a {tmp}/fix.diff",
    "patch -p1 -i {tmp}/fix.diff",
]

SCRIPT = [
    # 356's form: an exact-match replace in a heredoc-fed Python script.
    "python3 - <<'EOF'\nimport pathlib\np = pathlib.Path(\"src/motodiag/cli/main.py\")\n"
    "s = p.read_text()\nassert s.count(\"a\") == 1\np.write_text(s.replace(\"a\", \"b\"))\nEOF",
    ".venv/bin/python <<'EOF'\nwith open('tests/_planted.py', 'a') as f:\n    f.write('x')\nEOF",
    "python3 -c \"open('src/motodiag/_planted.py', 'w').write('')\"",
    "python3 - <<'EOF'\nimport shutil\nshutil.copy('/tmp/a', 'tests/_planted.py')\nEOF",
    "python3 - <<'EOF'\nimport os\nos.replace('/tmp/a', 'src/motodiag/_planted.py')\nEOF",
    "python3 - <<'EOF'\nfrom pathlib import Path\n(Path('{repo}') / 'tests' / 'x.py').write_text('')\nEOF",
    "python3 <<< \"open('src/motodiag/_planted.py', 'w')\"",
    "cat <<'EOF' | python3 -\nopen('src/motodiag/_planted.py', 'w')\nEOF",
    "bash <<'EOF'\nsed -i 's/a/b/' {tmp}/x\nEOF",
    "bash -c 'echo x > src/motodiag/_planted.py'",
    "sh -c \"cp {tmp}/a tests/\"",
    "node -e \"require('fs').writeFileSync('src/motodiag/x.js', '')\"",
    # One of two assignments of the same name points into tests/.
    "python3 - <<'EOF'\nimport pathlib\np = pathlib.Path('docs/a.md')\np.write_text('x')\n"
    "p = pathlib.Path('tests/test_x.py')\np.write_text('x')\nEOF",
    "cp {tmp}/a \"src/motodiag/$(basename $f)\"",
    # An unquoted heredoc is expanded by the shell before Python reads it.
    "D=tests; python3 - <<EOF\nopen('$D/_planted.py', 'w')\nEOF",
    # With no delimiter line, bash reads the body to the end, and so does the guard.
    "python3 - <<'EOF'\nopen('src/motodiag/_planted.py', 'w')",
]

UNRESOLVED_WRITE_IN_BODY = (
    "python3 - <<'EOF'\nimport sys\nfor p in sys.argv[1:]:\n    open(p, 'w')\n"
    "# the paths are under tests/\nEOF")


@pytest.mark.parametrize("command", SED, ids=range(len(SED)))
def test_sed_in_place_is_blocked_in_every_spelling(command, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)), "sed -i")


@pytest.mark.parametrize("command", PERL, ids=range(len(PERL)))
def test_perl_in_place_is_blocked(command, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)), "perl -i")


@pytest.mark.parametrize("command", REDIRECT, ids=range(len(REDIRECT)))
def test_a_redirect_into_src_or_tests_is_blocked(command, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)), "the redirect")


@pytest.mark.parametrize("command", TEE, ids=range(len(TEE)))
def test_tee_into_src_or_tests_is_blocked(command, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)), "`tee`")


@pytest.mark.parametrize("command", CP, ids=range(len(CP)))
def test_cp_into_src_or_tests_is_blocked(command, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)), "`cp`")


@pytest.mark.parametrize("command", MV, ids=range(len(MV)))
def test_mv_into_src_or_tests_is_blocked(command, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)), "`mv`")


@pytest.mark.parametrize("command", PATCH, ids=range(len(PATCH)))
def test_patch_into_src_or_tests_is_blocked(command, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)), "patch")


@pytest.mark.parametrize("command", SCRIPT, ids=range(len(SCRIPT)))
def test_a_script_body_that_writes_there_is_blocked(command, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)))


FIXED_DIRECTORY = [
    ("python3 - <<'EOF'\ndef sub(stem):\n    p = open(f'tests/test_phase{stem}.py', 'w')\nEOF",
     "writes tests/…"),
    ("python3 - <<'EOF'\nfrom pathlib import Path\nK = Path('src/motodiag/knowledge/seed')\n"
     "for name in names:\n    (K / name).write_text('x')\nEOF",
     "writes src/motodiag/knowledge/seed/…"),
]


@pytest.mark.parametrize("command,why", FIXED_DIRECTORY, ids=range(len(FIXED_DIRECTORY)))
def test_the_fixed_directory_of_a_python_path_is_enough_to_block(command, why):
    """The fixed part of an f-string or a `/` join names the directory, and
    the block says so, rather than falling back on the mention rule."""
    assert_blocked(_run(command), why)


def test_a_script_body_writing_an_unresolvable_path_that_names_tests_is_blocked():
    assert_blocked(_run(UNRESOLVED_WRITE_IN_BODY), "cannot resolve")


def test_a_symlink_into_src_is_followed(tmp_path):
    link = tmp_path / "link"
    link.symlink_to(REPO / "src")
    assert_blocked(_run(f"echo x > {link}/motodiag/_planted.py"), "the redirect")


# ---------------------------------------------------------------- fail closed
FAIL_CLOSED = [
    ("echo 'unclosed > src/x", "cannot parse"),
    ("echo $(echo x > {tmp}/y", "cannot parse"),
    ('echo x > "$UNKNOWN_VAR_360/x"', "cannot tell"),
    ("echo x > `pwd`/x", "cannot tell"),
    ("echo x > *.py", "cannot tell"),
    ('cp a "{repo}/$(basename $f)"', "cannot tell"),
    ("cd $UNKNOWN_VAR_360 && echo x > y", "cannot tell"),
    ("echo x >", "cannot parse"),
    ("python3 - <<'EOF'\nthis is not ( python\nEOF", "not valid Python"),
]


@pytest.mark.parametrize("command,why", FAIL_CLOSED, ids=range(len(FAIL_CLOSED)))
def test_what_it_cannot_read_is_blocked(command, why, tmp_path):
    assert_blocked(_run(_fill(command, tmp_path)), why)


def test_a_payload_that_is_not_json_is_blocked():
    assert_blocked(_run("", raw="not json"), "fails closed")


def _in_process(patch: str) -> subprocess.CompletedProcess:
    code = (f"import sys, time; sys.path.insert(0, {str(SKILL)!r}); "
            f"import _edit_guard as g; {patch}; sys.exit(g.main())")
    payload = json.dumps({"cwd": str(REPO), "tool_input": {"command": "echo x > y"}})
    return subprocess.run([sys.executable, "-B", "-c", code], input=payload,
                          capture_output=True, text=True, timeout=60)


def test_an_exception_inside_the_guard_blocks():
    r = _in_process("g.check = lambda *a: 1 / 0")
    assert r.returncode == 2
    assert "ZeroDivisionError" in r.stderr and "fails closed" in r.stderr


def test_the_guards_own_clock_blocks_a_slow_check():
    """358 measured that a hook killed by its timeout lets the command run.
    So the guard keeps its own clock: a check planted to outrun it is
    blocked, and well before the planted sleep ends."""
    start = time.monotonic()
    r = _in_process("g.LIMIT_S = 1; g.check = lambda *a: time.sleep(20)")
    assert r.returncode == 2
    assert "own limit" in r.stderr
    assert time.monotonic() - start < 10


def test_the_clock_does_not_fire_on_a_normal_check():
    assert _in_process("g.LIMIT_S = 1").returncode == 0


def _fake_guard(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    d = tmp_path / ".claude" / "skills" / "closeout"
    d.mkdir(parents=True)
    shutil.copy(GUARD, d / "edit_guard.sh")
    (d / "_edit_guard.py").write_text(body)
    return d / "edit_guard.sh"


def test_the_wrapper_turns_any_other_exit_status_into_a_block(tmp_path):
    r = _run("ls", guard=_fake_guard(tmp_path, "import sys\nsys.exit(1)\n"))
    assert r.returncode == 2
    assert "exited 1" in r.stderr


def test_the_wrapper_passes_a_clean_exit(tmp_path):
    assert _run("ls", guard=_fake_guard(tmp_path, "import sys\nsys.exit(0)\n")).returncode == 0


# ---------------------------------------------------------------- allowed
ALLOWED = [
    # The commit-message heredoc, with every trap in its body.
    "git commit -q -F - <<'MSGEOF'\nDon't sed -i; echo x > src/x.py; it's \"fine\" & done\n"
    "cat >> tests/y.py\nMSGEOF",
    "git commit -m \"$(cat <<'EOF'\nmsg with > src/x and sed -i\nEOF\n)\"",
    "git mv src/motodiag/a.py src/motodiag/b.py",
    "git checkout -- src/motodiag/__init__.py",
    "git apply {tmp}/fix.diff",
    "git stash pop",
    "git -C {repo} log --oneline > {tmp}/log.txt",
    # Read-only scripts.
    "python3 - <<'EOF'\nimport pathlib\nprint(pathlib.Path('src/motodiag/cli/main.py').read_text()[:10])\nEOF",
    "python3 - <<'EOF'\nt = open('src/motodiag/cli/main.py').read()\n"
    "open('{tmp}/out.txt', 'w').write(t)\nEOF",
    "python3 -c \"import json, sys; print(json.load(sys.stdin))\" < {tmp}/x.json",
    "sqlite3 {tmp}/x.db <<'EOF'\nselect 1;\nEOF",
    "cat <<'EOF'\n> src/x and sed -i\nEOF",
    "bash <<'EOF'\necho hello > {tmp}/x\nEOF",
    # Redirects outside src/ and tests/.
    "echo x > {tmp}/x.txt",
    "echo x >> docs/phases/in_progress/scratch.md",
    "S={tmp}; .venv/bin/python -m pytest -q tests/test_x.py > $S/out.txt 2>&1",
    "ls 2>&1 | tail -3",
    "ls >/dev/null 2>&1",
    "ls &>/dev/null",
    "cd /tmp && echo x > src/x.py",
    "echo x | tee {tmp}/log.txt",
    "cp src/motodiag/__init__.py {tmp}/",
    "mv {tmp}/a {tmp}/b",
    "patch --dry-run -p1 < {tmp}/fix.diff",
    "cd {tmp} && patch -p1 < fix.diff",
    # sed without -i, and '>' that is not a redirect.
    "sed -n '1,5p' src/motodiag/cli/main.py",
    "sed 's/a/b/' src/motodiag/cli/main.py",
    "grep -n '->' src/motodiag/cli/main.py",
    "awk '$1 > 5' tests/conftest.py",
    "(( 3 > 2 )) && echo ok",
    "[[ b > a ]] && echo ok",
    "echo 'sed -i is blocked' && echo \"> src/x\"",
    "grep -c 'python3 -c' src/motodiag/cli/main.py",
    # A fixed directory outside src/ and tests/ is enough to know.
    "for f in a b; do cp \"$f\" \"{tmp}/mut/$(basename $f).bak\"; done",
    "python3 - <<'EOF'\nimport pathlib\np = pathlib.Path('docs/a.md')\np.write_text('x')\n"
    "p = pathlib.Path('docs/b.md')\np.write_text('y')\nEOF",
    "python3 - <<'EOF'\nfrom pathlib import Path\nOUT = Path('{tmp}')\n"
    "for n in names:\n    (OUT / n).write_text(open('src/motodiag/cli/main.py').read())\nEOF",
    # `$'` inside double quotes is a literal dollar, not an ANSI-C string.
    ".venv/bin/python -c \"import re; print(re.findall(r'^\\]\\s*$', open('src/motodiag/cli/main.py').read(), re.M))\"",
    # Shell values inside -c code and unquoted heredocs.
    "for m in fitz pypdf; do .venv/bin/python -c \"import $m; print('$m')\"; done",
    "n=3; .venv/bin/python - <<PY\nif $n != 2:\n    print('n is $n')\nPY",
    "cat <<EOF > {tmp}/x\nno terminator",
    # No trigger at all.
    "ls -la",
    "cat src/motodiag/cli/main.py",
]


@pytest.mark.parametrize("command", ALLOWED, ids=range(len(ALLOWED)))
def test_what_sessions_need_is_allowed(command, tmp_path):
    assert_allowed(_run(_fill(command, tmp_path)))


def test_src_in_another_repository_is_not_this_checkouts(tmp_path):
    """The mobile repo has its own src/. A script run there that names
    src/ is not writing this checkout's source."""
    other = tmp_path / "moto-diag-mobile"
    (other / "src").mkdir(parents=True)
    body = ("node - <<'EOF'\nconst fs = require('fs');\nlet s = fs.readFileSync('src/a.tsx', "
            "'utf8');\nfs.writeFileSync('src/a.tsx', s);\nEOF")
    assert_allowed(_run(f"cd {other}\n{body}"))
    assert_blocked(_run(body))                       # the same body, run here


class TestKnownLimits:
    """What the guard cannot see, pinned so a change to it is noticed."""

    def test_a_script_file_run_by_name_is_not_opened(self):
        assert_allowed(_run("python3 docs/phases/completed/357_mutate.py RUN"))

    def test_rm_is_not_blocked(self):
        assert_allowed(_run("rm -f tests/_planted.py"))


# ---------------------------------------------------------------- the hook
class TestTheHookEntry:
    def _hooks(self):
        settings = json.loads((REPO / ".claude" / "settings.json").read_text())
        bash = [m for m in settings["hooks"]["PreToolUse"] if m["matcher"] == "Bash"]
        return [h for m in bash for h in m["hooks"]]

    def test_the_edit_guard_is_a_bash_pretooluse_hook_beside_the_push_guard(self):
        commands = [h["command"] for h in self._hooks()]
        assert "${CLAUDE_PROJECT_DIR}/.claude/skills/closeout/edit_guard.sh" in commands
        assert "${CLAUDE_PROJECT_DIR}/.claude/skills/closeout/pre_push_guard.sh" in commands

    def test_the_guards_clock_is_far_inside_the_hook_timeout(self):
        sys.path.insert(0, str(SKILL))
        import _edit_guard
        hook = next(h for h in self._hooks() if h["command"].endswith("edit_guard.sh"))
        assert _edit_guard.LIMIT_S * 3 <= hook["timeout"]

    def test_the_wrapper_is_executable(self):
        assert os.access(GUARD, os.X_OK)
