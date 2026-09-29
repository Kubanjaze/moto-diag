#!/usr/bin/env python3
"""Phase 360 edit guard. Blocks a Bash command that edits `src/` or `tests/`.

The working rule is "targeted edits only on source and tests": the Edit and
Write tools, never `sed -i`, a redirect or a script. Phases 356 and 357 both
broke it — an exact-match replace in a heredoc-fed Python script, and a
`cat >> src/… <<'EOF'` — so the rule is now a hook, not a sentence.

**What it blocks** (each has a planted positive control in
`tests/test_phase360_edit_guard.py`):

* `sed -i` / `gsed -i` in every spelling, anywhere, whatever the path;
* `perl -i` in every spelling, anywhere;
* a write redirect (`>`, `>>`, `>|`, `&>`, `&>>`, `N>`, `<>`, `>&file`)
  whose target is in `src/` or `tests/`;
* `tee`, `cp` or `mv` whose destination is there (`git mv` is git, and
  allowed);
* `patch` onto a file there, or with no explicit file while its directory is
  inside this checkout — the files come from the diff, which is not read;
* a heredoc-fed, here-string or `-c` script whose body writes there: Python
  bodies are parsed (`open(…, 'w')`, `.write_text`, `shutil.copy`, …), shell
  bodies are judged again as a command line.

**It fails closed.** A command line it cannot lex, a write target it cannot
resolve, any exception, and its own clock (`LIMIT_S`, far inside the hook's
timeout) all exit 2. Phase 358 measured that a `PreToolUse` hook killed by
its timeout lets the command run, so the guard must never be the one killed.
The wrapper turns any other exit status into 2 as well.

**It exits early.** A command holding none of the tokens any blocked form
needs (`_TRIGGER`) leaves before any parsing, which bounds the lockout
surface of a guard that fails closed. Recovery, if it ever blocks every Bash
call: edit `.claude/settings.json` with the Write tool, which is not Bash.

**Known limits** (also in the closeout CHANGELOG): a script file run by name
is not opened — the phases' mutation scripts write into `src/` that way, by
design; `install`, `rsync`, `dd`, `truncate`, `ln`, `rm` and `git apply` are
not blocked; `subprocess` calls, `eval` and values known only at run time are
not followed; only Python and shell bodies are parsed; only this checkout is
protected; hooks are read when a session starts.
"""
from __future__ import annotations

import ast
import json
import os
import re
import signal
import sys
import warnings
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PROTECTED = ("src", "tests")

#: The guard's own clock, in seconds. The hook's timeout in
#: `.claude/settings.json` is 30 s; this must stay far inside it.
LIMIT_S = 5

#: Every blocked form needs one of these. A command with none leaves at once.
_TRIGGER = re.compile(r">|<<|\b(?:tee|g?sed|perl|cp|mv|patch|node|ruby)\b|-\w*c\b")

_REMEDY = ("Use the Edit or Write tool for src/ and tests/ (CLAUDE.md working "
           "rules: targeted edits only).")


class Blocked(Exception):
    """The command is blocked; the message is the reason."""


# ------------------------------------------------------------------ words
@dataclass
class Word:
    """One shell word. `parts` holds ("lit", text), ("var", name) or
    ("dyn", source) — a value only the running shell knows."""
    parts: list = field(default_factory=list)
    glob: bool = False
    quoted: bool = False

    @property
    def text(self) -> str:
        return "".join(v if k == "lit" else ("$" + v if k == "var" else v)
                       for k, v in self.parts)

    def resolve(self, env: dict) -> str | None:
        text, exact = self.prefix(env)
        return text if exact else None

    def code(self, env: dict) -> str:
        """The word as a program would receive it; a value only the running
        shell knows reads as the placeholder name `_v`."""
        return "".join(v if k == "lit" else (env.get(v) or "_v") if k == "var" else "_v"
                       for k, v in self.parts)

    def prefix(self, env: dict) -> tuple[str, bool]:
        """(the known leading text, whether that is the whole word)."""
        out = []
        for kind, value in self.parts:
            if kind == "lit" and not (self.glob and re.search(r"[*?\[]", value)):
                out.append(value)
            elif kind == "var" and env.get(value) is not None:
                out.append(env[value])
            else:
                return "".join(out), False
        return "".join(out), not self.glob


def expand_body(body: str, env: dict) -> str:
    """An unquoted heredoc's body as the shell hands it on: `$NAME` and
    `${NAME}` take their value when known, anything else only the running
    shell knows reads as `_v`."""
    body = re.sub(r"\$\(\([^)]*\)\)|\$\([^)]*\)|`[^`]*`", "_v", body)
    body = re.sub(r"\\\$", "\x00", body)
    body = re.sub(r"\$\{?([A-Za-z_]\w*)\}?", lambda m: env.get(m.group(1)) or "_v", body)
    body = re.sub(r"\$[0-9@*#?$!-]", "_v", body)
    return body.replace("\x00", "$")


@dataclass
class Cmd:
    words: list = field(default_factory=list)
    redirs: list = field(default_factory=list)      # (op, target Word)
    stdin: tuple | None = None                      # ("heredoc", i) / ("herestring", Word)
    sep: str = ""


# ------------------------------------------------------------------ lexer
class _Lexer:
    """A small shell lexer: quotes, escapes, `$…` expansions, backticks,
    `$(…)`, process substitution, `((…))`, heredocs and comments. Anything
    it cannot close raises Blocked (fail closed)."""

    def __init__(self, s: str):
        self.s = s
        self.subs: list[str] = []       # command substitutions, judged again
        self.bodies: list[str] = []     # heredoc bodies, by index
        self.expands: list[bool] = []   # whether the shell expands each body

    def body(self, idx: int, env: dict) -> str:
        text = self.bodies[idx]
        return expand_body(text, env) if self.expands[idx] else text

    def fail(self, why: str):
        raise Blocked(f"the edit guard cannot parse this command ({why}), and "
                      "blocks what it cannot read.")

    def run(self, i: int = 0, closer: str | None = None):
        s, n = self.s, len(self.s)
        toks: list[tuple] = []
        word: Word | None = None
        pending: list[tuple[str, bool, int]] = []

        def end_word():
            nonlocal word
            if word is not None:
                toks.append(("word", word))
                word = None

        def cur() -> Word:
            nonlocal word
            if word is None:
                word = Word()
            return word

        while i < n:
            c = s[i]
            if c in " \t":
                end_word()
                i += 1
            elif c == "\n":
                end_word()
                toks.append(("op", "\n"))
                i += 1
                for delim, strip, idx in pending:
                    i = self._heredoc_body(i, delim, strip, idx)
                pending = []
            elif c == "#" and word is None:
                while i < n and s[i] != "\n":
                    i += 1
            elif c == "\\":
                if i + 1 < n and s[i + 1] == "\n":
                    i += 2
                    continue
                if i + 1 >= n:
                    self.fail("a trailing backslash")
                cur().parts.append(("lit", s[i + 1]))
                cur().quoted = True
                i += 2
            elif c == "'":
                j = s.find("'", i + 1)
                if j < 0:
                    self.fail("an unclosed single quote")
                cur().parts.append(("lit", s[i + 1:j]))
                cur().quoted = True
                i = j + 1
            elif c == '"':
                i = self._dquote(i + 1, cur())
            elif c == "$":
                i = self._dollar(i, cur())
            elif c == "`":
                i = self._backtick(i, cur())
            elif c in "*?[" :
                cur().parts.append(("lit", c))
                cur().glob = True
                i += 1
            elif c == ";":
                end_word()
                toks.append(("op", ";"))
                i += 2 if s.startswith(";;", i) else 1
            elif c == "&":
                end_word()
                if s.startswith("&&", i):
                    toks.append(("op", "&&"))
                    i += 2
                elif s.startswith("&>>", i):
                    toks.append(("redir", "&>>"))
                    i += 3
                elif s.startswith("&>", i):
                    toks.append(("redir", "&>"))
                    i += 2
                else:
                    toks.append(("op", "&"))
                    i += 1
            elif c == "|":
                end_word()
                if s.startswith("||", i):
                    toks.append(("op", "||"))
                    i += 2
                else:
                    toks.append(("op", "|"))
                    i += 2 if s.startswith("|&", i) else 1
            elif c in "<>":
                # A word of digits right before the operator is its fd.
                if word is not None and not word.quoted and word.parts and \
                        all(k == "lit" and v.isdigit() for k, v in word.parts):
                    word = None
                end_word()
                i = self._redirect(i, toks, pending)
            elif c == "(":
                end_word()
                if s.startswith("((", i) and (not toks or toks[-1][0] == "op"):
                    j = self._match_parens(i + 2, "))")
                    toks.append(("word", Word([("lit", "((…))")])))
                    i = j
                else:
                    toks.append(("op", "("))
                    i += 1
            elif c == ")":
                end_word()
                if closer == ")":
                    return toks, i + 1
                toks.append(("op", ")"))
                i += 1
            else:
                cur().parts.append(("lit", c))
                i += 1
        end_word()
        if closer is not None:
            self.fail("an unclosed $( or (")
        if pending:
            self.fail(f"an unterminated heredoc ({pending[0][0]})")
        return toks, i

    def _heredoc_body(self, i: int, delim: str, strip: bool, idx: int) -> int:
        """The body up to the delimiter line. With no delimiter line, bash
        takes the rest of the input (and warns), so the guard does too."""
        s, lines = self.s, []
        while i <= len(s):
            j = s.find("\n", i)
            line = s[i:] if j < 0 else s[i:j]
            if (line.lstrip("\t") if strip else line) == delim:
                self.bodies[idx] = "\n".join(lines) + ("\n" if lines else "")
                return len(s) if j < 0 else j + 1
            lines.append(line)
            if j < 0:
                break
            i = j + 1
        self.bodies[idx] = "\n".join(lines)
        return len(s)

    def _dquote(self, i: int, w: Word) -> int:
        s, n = self.s, len(self.s)
        w.quoted = True
        buf = []
        while i < n:
            c = s[i]
            if c == '"':
                if buf:
                    w.parts.append(("lit", "".join(buf)))
                return i + 1
            if c == "\\" and i + 1 < n and s[i + 1] in '$`"\\\n':
                if s[i + 1] != "\n":
                    buf.append(s[i + 1])
                i += 2
            elif c in "$`":
                if buf:
                    w.parts.append(("lit", "".join(buf)))
                    buf = []
                i = self._dollar(i, w, quoted=True) if c == "$" else self._backtick(i, w)
            else:
                buf.append(c)
                i += 1
        self.fail("an unclosed double quote")

    def _dollar(self, i: int, w: Word, quoted: bool = False) -> int:
        s, n = self.s, len(self.s)
        if quoted and s.startswith(("$'", '$"'), i):     # literal inside "…"
            w.parts.append(("lit", "$"))
            return i + 1
        if s.startswith("$((", i):
            j = self._match_parens(i + 3, "))")
            w.parts.append(("dyn", s[i:j]))
            return j
        if s.startswith("$(", i):
            start = i + 2
            _, j = self.run(start, ")")
            self.subs.append(s[start:j - 1])
            w.parts.append(("dyn", s[i:j]))
            return j
        if s.startswith("${", i):
            j = s.find("}", i + 2)
            if j < 0:
                self.fail("an unclosed ${")
            inner = s[i + 2:j]
            w.parts.append(("var", inner) if re.fullmatch(r"[A-Za-z_]\w*", inner)
                           else ("dyn", s[i:j + 1]))
            return j + 1
        if s.startswith("$'", i):
            j = i + 2
            while j < n and s[j] != "'":
                j += 2 if s[j] == "\\" else 1
            if j >= n:
                self.fail("an unclosed $'")
            w.parts.append(("lit", s[i + 2:j]))
            w.quoted = True
            return j + 1
        m = re.compile(r"[A-Za-z_]\w*").match(s, i + 1)
        if m:
            w.parts.append(("var", m.group(0)))
            return m.end()
        if i + 1 < n and s[i + 1] in "0123456789@*#?$!-":
            w.parts.append(("dyn", s[i:i + 2]))
            return i + 2
        w.parts.append(("lit", "$"))
        return i + 1

    def _backtick(self, i: int, w: Word) -> int:
        s, j = self.s, i + 1
        while j < len(s) and s[j] != "`":
            j += 2 if s[j] == "\\" else 1
        if j >= len(s):
            self.fail("an unclosed backtick")
        self.subs.append(s[i + 1:j])
        w.parts.append(("dyn", s[i:j + 1]))
        return j + 1

    def _match_parens(self, i: int, close: str) -> int:
        depth, s = 0, self.s
        while i < len(s):
            if s[i] == "(":
                depth += 1
            elif s.startswith(close, i) and depth == 0:
                return i + len(close)
            elif s[i] == ")":
                depth -= 1
            i += 1
        self.fail(f"an unclosed (( … {close}")

    def _redirect(self, i: int, toks: list, pending: list) -> int:
        s = self.s
        if s.startswith("<<<", i):
            toks.append(("redir", "<<<"))
            return i + 3
        if s.startswith("<<", i):
            m = re.compile(r"<<(-?)[ \t]*(?:'([^'\n]*)'|\"([^\"\n]*)\"|\\?([^\s;&|<>()]+))").match(s, i)
            if not m:
                self.fail("a heredoc with no delimiter")
            delim = next(g for g in m.groups()[1:] if g is not None)
            idx = len(self.bodies)
            self.bodies.append("")
            # An unquoted delimiter means the shell expands the body.
            self.expands.append(m.group(4) is not None and "\\" not in m.group(0))
            pending.append((delim, m.group(1) == "-", idx))
            toks.append(("heredoc", idx))
            return m.end()
        if s[i] == ">" and s.startswith(">(", i) or s[i] == "<" and s.startswith("<(", i):
            start = i + 2
            _, j = self.run(start, ")")
            self.subs.append(s[start:j - 1])
            toks.append(("word", Word([("dyn", s[i:j])])))
            return j
        for op in (">>", ">|", ">&", "<>", "<&", ">", "<"):
            if s.startswith(op, i):
                toks.append(("redir", op))
                return i + len(op)
        raise AssertionError("unreachable")


# ------------------------------------------------------------------ commands
_SEPARATORS = {";", "&&", "||", "|", "&", "\n", "(", ")"}
_KEYWORDS = {"if", "then", "else", "elif", "fi", "do", "done", "while", "until",
             "{", "}", "!", "time", "esac"}
_WRITE_OPS = {">", ">>", ">|", "&>", "&>>", "<>"}


def _commands(toks: list) -> list[Cmd]:
    cmds, cmd, i, test_mode = [], Cmd(), 0, False
    while i < len(toks):
        kind, value = toks[i]
        if kind == "op" and value in _SEPARATORS and not (test_mode and value in "()"):
            cmd.sep = value
            cmds.append(cmd)
            cmd, test_mode = Cmd(), False
        elif kind == "heredoc":
            cmd.stdin = ("heredoc", value)
        elif kind == "redir":
            if test_mode and value in (">", "<"):
                cmd.words.append(Word([("lit", value)]))
            else:
                if i + 1 >= len(toks) or toks[i + 1][0] != "word":
                    raise Blocked(f"the edit guard cannot parse this command (`{value}` "
                                  "with no target), and blocks what it cannot read.")
                i += 1
                if value == "<<<":
                    cmd.stdin = ("herestring", toks[i][1])
                else:
                    cmd.redirs.append((value, toks[i][1]))
        else:
            w = value
            if not cmd.words and w.text == "[[":
                test_mode = True
            elif w.text == "]]":
                test_mode = False
            cmd.words.append(w)
        i += 1
    cmds.append(cmd)
    return [c for c in cmds if c.words or c.redirs or c.stdin]


@dataclass
class State:
    cwd: str | None
    env: dict

    def copy(self) -> "State":
        return State(self.cwd, dict(self.env))


def _abs(path: str, cwd: str | None) -> str | None:
    if path == "~" or path.startswith("~/"):
        home = os.environ.get("HOME")
        if not home:
            return None
        path = home + path[1:]
    elif path.startswith("~"):
        return None
    if not os.path.isabs(path):
        if cwd is None:
            return None
        path = os.path.join(cwd, path)
    return os.path.normpath(path)


def _under(path: str, base: str) -> bool:
    return path == base or path.startswith(base.rstrip("/") + "/")


def _bases() -> list[str]:
    out = []
    for p in PROTECTED:
        b = os.path.join(REPO, p)
        out += [os.path.normpath(b), os.path.realpath(b)]
    return out


def is_protected(path: str) -> bool:
    if path.startswith("/dev/"):
        return False
    real = os.path.realpath(path)
    return any(_under(path, b) or _under(real, b) for b in _bases())


def _inside_repo(path: str) -> bool:
    return _under(path, os.path.normpath(REPO)) or \
        _under(os.path.realpath(path), os.path.realpath(REPO))


def _target(word: Word, state: State, what: str) -> str:
    """The absolute path a write goes to; Blocked when it is protected or
    cannot be told."""
    raw, exact = word.prefix(state.env)
    if not exact:
        # A fixed leading directory still says where the write lands: under
        # src/ or tests/ it is blocked; under a directory that cannot hold
        # them (the scratchpad, docs/) it is not.
        raw = os.path.dirname(raw) if "/" in raw else None
    path = None if raw is None else _abs(raw, state.cwd)
    if path is not None and is_protected(path):
        raise Blocked(f"{what} writes into {os.path.relpath(path, REPO)}"
                      f"{'' if exact else '/…'}. {_REMEDY}")
    if path is None or not exact and _holds_protected(path):
        raise Blocked(f"the edit guard cannot tell where {what} `{word.text}` writes "
                      "(a variable, substitution, glob or unknown directory), and "
                      "blocks what it cannot resolve. Use a literal path.")
    return path


_WRAPPERS = {"env", "sudo", "doas", "time", "nice", "nohup", "command", "exec",
             "stdbuf", "timeout", "xargs", "caffeinate"}
_XARGS_ARG = {"-I", "-n", "-P", "-L", "-d", "-s", "-E", "-a"}


def _base(w: Word) -> str:
    return os.path.basename(w.text)


def _effective(words: list) -> list:
    i = 0
    while i < len(words):
        name = _base(words[i])
        if name not in _WRAPPERS:
            return words[i:]
        i += 1
        while i < len(words):
            a = words[i].text
            if name == "xargs" and a in _XARGS_ARG or name == "nice" and a == "-n":
                i += 2
            elif a.startswith("-") or name == "env" and "=" in a or \
                    name == "timeout" and re.match(r"\d", a):
                i += 1
            else:
                break
    return []


_ASSIGN = re.compile(r"([A-Za-z_]\w*)=")


def _assign(w: Word, state: State) -> bool:
    """Record `NAME=value`; True when the word was an assignment."""
    k = 0
    while k < len(w.parts) and w.parts[k][0] == "lit":
        k += 1
    lead = "".join(v for _, v in w.parts[:k])
    m = _ASSIGN.match(lead)
    if not m:
        return False
    rest = lead[m.end():]
    value = Word(([("lit", rest)] if rest else []) + w.parts[k:], w.glob)
    state.env[m.group(1)] = value.resolve(state.env)
    return True


def _sed_inplace(args: list) -> bool:
    for w in args:
        a = w.text
        if a == "--":
            break
        if a.startswith("--in-place"):
            return True
        if a.startswith("-") and not a.startswith("--"):
            for ch in a[1:]:
                if ch == "i":
                    return True
                if ch in "efl":
                    break
    return False


def _perl(args: list) -> tuple[bool, str | None]:
    """(in-place, the -e code) for a perl command line."""
    inplace, code, i = False, None, 0
    while i < len(args):
        a = args[i].text
        if not a.startswith("-") or a == "--":
            break
        for j, ch in enumerate(a[1:]):
            if ch == "i":
                inplace = True
            if ch in "eE":
                rest = a[j + 2:]
                if rest:
                    code = rest
                elif i + 1 < len(args):
                    code = args[i + 1].text
                    i += 1
                break
            if ch in "IMmxCdD":
                break
        i += 1
    return inplace, code


def _cp_mv_dest(args: list) -> list:
    target, ops, i, dd = None, [], 0, False
    while i < len(args):
        a = args[i].text
        if dd:
            ops.append(args[i])
        elif a == "--":
            dd = True
        elif a in ("-t", "--target-directory"):
            target = args[i + 1] if i + 1 < len(args) else None
            i += 1
        elif a.startswith("--target-directory="):
            target = (Word([("lit", a.split("=", 1)[1])]) if args[i].resolve({}) is not None
                      else Word([("dyn", a)]))
        elif a in ("-S", "--suffix"):
            i += 1
        elif a.startswith("-") and len(a) > 1 and not a.startswith("--") and "t" in a[1:]:
            rest = a[a.index("t", 1) + 1:]
            if rest:
                target = Word([("lit", rest)])
            elif i + 1 < len(args):
                target = args[i + 1]
                i += 1
        elif not a.startswith("-") or a == "-":
            ops.append(args[i])
        i += 1
    if target is not None:
        return [target]
    return [ops[-1]] if len(ops) >= 2 else []


_PATCH_ARG = {"-d", "-i", "-o", "-p", "-F", "-r", "-B", "-z", "-Y", "-D", "-g", "-V",
              "--directory", "--input", "--output", "--strip", "--fuzz",
              "--reject-file", "--prefix", "--suffix", "--basename-prefix",
              "--ifdef", "--get", "--version-control"}


def _patch(args: list, state: State) -> None:
    d = out = None
    pos: list = []
    i = 0
    while i < len(args):
        a = args[i].text
        if a in ("--dry-run", "--check"):
            return
        if a in _PATCH_ARG:
            nxt = args[i + 1] if i + 1 < len(args) else None
            if a in ("-d", "--directory"):
                d = nxt
            elif a in ("-o", "--output"):
                out = nxt
            i += 2
            continue
        if a.startswith("--directory=") or a.startswith("--output="):
            key, val = a.split("=", 1)
            if key == "--directory":
                d = Word([("lit", val)])
            else:
                out = Word([("lit", val)])
        elif re.match(r"-[dopFrBzYDgV].", a) and not a.startswith("--"):
            if a[1] == "d":
                d = Word([("lit", a[2:])])
            elif a[1] == "o":
                out = Word([("lit", a[2:])])
        elif not a.startswith("-"):
            pos.append(args[i])
        i += 1
    here = state.cwd
    if d is not None:
        raw = d.resolve(state.env)
        here = None if raw is None else _abs(raw, state.cwd)
    sub = State(here, state.env)
    if out is not None:
        _target(out, sub, "`patch -o`")
    if pos:
        _target(pos[0], sub, "`patch`")
    elif out is None:
        if here is None:
            raise Blocked("the edit guard cannot tell which directory `patch` works "
                          "in, and blocks what it cannot resolve.")
        if _inside_repo(here):
            raise Blocked("`patch` with no named file writes the files its diff names, "
                          "and the guard does not read diffs; inside this checkout it "
                          f"is blocked. {_REMEDY}")


# ------------------------------------------------------------------ script bodies
_MENTION = re.compile(r"""[^\s'"`(),;=\[\]{}]*(?<![\w.-])(?:src|tests)/[^\s'"`(),;\[\]{}]*""")


def _mentions_protected(code: str, cwd: str | None) -> bool:
    """Whether the body names a path in this checkout's src/ or tests/,
    resolved against the directory the script runs in: `src/` in a script
    run inside another repository is that repository's."""
    for token in _MENTION.findall(code):
        path = _abs(token, cwd)
        if path is None or is_protected(path):
            return True
    return False
_PY_NAME = re.compile(r"python(?:\d+(?:\.\d+)*)?$")
_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
_OTHER = {"node", "ruby", "deno", "bun"}
_COPY_CALLS = {"shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree",
               "shutil.move", "os.replace", "os.rename", "os.renames", "os.link",
               "os.symlink"}


def _dotted(f: ast.AST) -> str:
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        inner = _dotted(f.value)
        return f"{inner}.{f.attr}" if inner else f.attr
    return ""


def _arg(call: ast.Call, i: int, kw: str):
    if len(call.args) > i and not isinstance(call.args[i], ast.Starred):
        return call.args[i]
    return next((k.value for k in call.keywords if k.arg == kw), None)


def _mode_writes(mode) -> bool | None:
    """True/False for a literal mode; None when it cannot be told."""
    if mode is None:
        return False
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return bool(set(mode.value) & set("wax+"))
    return None


#: A candidate for where a Python expression points: (path, exact). An
#: inexact candidate means "somewhere under this directory"; (None, False)
#: means nothing is known.
_UNKNOWN = [(None, False)]


def _prefix_dir(text: str) -> list:
    """The directory a string's known leading part fixes, or unknown."""
    return [(os.path.dirname(text), False)] if "/" in text else _UNKNOWN


def _join(left: list, right: list) -> list:
    out = []
    for lp, lx in left:
        if lp is None:
            out += _UNKNOWN
        elif not lx:
            out.append((lp, False))
        else:
            for rp, rx in right:
                out.append((lp, False) if rp is None else (os.path.join(lp, rp), rx))
    return out


def _py_paths(e, assigns: dict, depth: int = 0) -> list:
    """Every place an expression can point, as far as the body shows it:
    each assignment of a name is followed, and the fixed part of an f-string
    or of a `/` join still names a directory."""
    if e is None or depth > 8:
        return _UNKNOWN
    if isinstance(e, ast.Constant) and isinstance(e.value, str):
        return [(e.value, True)]
    if isinstance(e, ast.JoinedStr):
        lead = []
        for v in e.values:
            if not isinstance(v, ast.Constant):
                return _prefix_dir("".join(lead))
            lead.append(str(v.value))
        return [("".join(lead), True)]
    if isinstance(e, ast.Name):
        found = assigns.get(e.id, [])
        if not found:
            return _UNKNOWN
        return [c for f in found for c in _py_paths(f, assigns, depth + 1)]
    if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Div):
        return _join(_py_paths(e.left, assigns, depth + 1),
                     _py_paths(e.right, assigns, depth + 1))
    if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
        out = []
        for lp, lx in _py_paths(e.left, assigns, depth + 1):
            for rp, rx in _py_paths(e.right, assigns, depth + 1):
                if lp is None:
                    out += _UNKNOWN
                elif lx and rp is not None and rx:
                    out.append((lp + rp, True))
                else:
                    out += _prefix_dir(lp) if lx else [(lp, False)]
        return out
    if isinstance(e, ast.Call):
        name = _dotted(e.func)
        if name.split(".")[-1] in ("Path", "PurePath", "PosixPath") or name == "os.path.join":
            if not e.args:
                return [(".", True)]
            acc = _py_paths(e.args[0], assigns, depth + 1)
            for a in e.args[1:]:
                acc = _join(acc, _py_paths(a, assigns, depth + 1))
            return acc
        if isinstance(e.func, ast.Attribute) and e.func.attr in ("resolve", "absolute",
                                                                   "expanduser"):
            return [(None if p is None else os.path.expanduser(p), x)
                    for p, x in _py_paths(e.func.value, assigns, depth + 1)]
    return _UNKNOWN


def _holds_protected(path: str) -> bool:
    """Whether `path` is this checkout's root or an ancestor of src/ or
    tests/, so that something unknown under it could be protected."""
    return any(_under(b, path) for b in _bases())


def _python_body(code: str, state: State) -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")          # stderr stays the guard's own
            tree = ast.parse(code)
    except SyntaxError as e:
        raise Blocked(f"the script given to python is not valid Python ({e.msg}); the "
                      "edit guard blocks what it cannot read.") from None
    assigns: dict[str, list] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    assigns.setdefault(t.id, []).append(node.value)
        elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and \
                isinstance(node.target, ast.Name) and node.value is not None:
            assigns.setdefault(node.target.id, []).append(node.value)
        elif isinstance(node, (ast.For, ast.comprehension)) and isinstance(node.target, ast.Name):
            it = node.iter
            elts = it.elts if isinstance(it, (ast.List, ast.Tuple, ast.Set)) else [None]
            assigns.setdefault(node.target.id, []).extend(elts)
        elif isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
            assigns.setdefault(node.optional_vars.id, []).append(None)
    targets = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f, name = node.func, _dotted(node.func)
        if name in ("open", "io.open", "codecs.open"):
            writes = _mode_writes(_arg(node, 1, "mode"))
            if writes is not False:
                targets.append(_arg(node, 0, "file"))
        elif name == "os.open":
            flags = ast.unparse(_arg(node, 1, "flags") or ast.Constant(""))
            if re.search(r"WRONLY|RDWR|CREAT|APPEND|TRUNC", flags) or \
                    not re.search(r"O_RDONLY", flags):
                targets.append(_arg(node, 0, "path"))
        elif name in _COPY_CALLS:
            targets.append(_arg(node, 1, "dst"))
        elif isinstance(f, ast.Attribute) and f.attr in ("write_text", "write_bytes", "touch"):
            targets.append(f.value)
        elif isinstance(f, ast.Attribute) and f.attr == "open":
            if _mode_writes(_arg(node, 0, "mode")) is not False:
                targets.append(f.value)
        elif isinstance(f, ast.Attribute) and f.attr in ("rename", "replace") and \
                not name.startswith("os."):
            targets.append(_arg(node, 0, "target"))
    unknown = False
    for t in targets:
        for raw, exact in _py_paths(t, assigns):
            path = None if raw is None else _abs(raw, state.cwd)
            if path is None:
                unknown = True
            elif is_protected(path):
                where = os.path.relpath(path, REPO) + ("" if exact else "/…")
                raise Blocked(f"a Python script body writes {where}. {_REMEDY}")
            elif not exact and _holds_protected(path):
                unknown = True
    if unknown and _mentions_protected(code, state.cwd):
        raise Blocked("a Python script body writes to a path the edit guard cannot "
                      "resolve, and the body names src/ or tests/; it blocks what it "
                      f"cannot resolve. Use a literal path. {_REMEDY}")


def _other_body(code: str, name: str, state: State) -> None:
    if _mentions_protected(code, state.cwd) and re.search(r"writeFile|appendFile|open\(|File\.write|"
                                           r"IO\.write|>>?", code):
        raise Blocked(f"a {name} script body names src/ or tests/ and writes a file. "
                      f"{_REMEDY}")


def _script(name: str, args: list, body: str | None, state: State, depth: int) -> None:
    """Judge an interpreter's code: -c/-e text, or its stdin body."""
    code, from_stdin, i = None, True, 0
    while i < len(args):
        a = args[i].text
        if a == "-":
            break
        if a.startswith("--"):
            if a in ("--eval", "--command"):
                code = args[i + 1].code(state.env) if i + 1 < len(args) else ""
                from_stdin = False
                break
            i += 1
            continue
        if a.startswith("-") and len(a) > 1:
            letters = a[1:]
            flag = "c" if _PY_NAME.match(name) or name in _SHELLS else "e"
            if name == "node" and "p" in letters:
                flag = "p" if "e" not in letters else "e"
            if flag in letters:
                rest = letters[letters.index(flag) + 1:]
                code = rest if rest else (args[i + 1].code(state.env) if i + 1 < len(args)
                                          else "")
                from_stdin = False
                break
            if _PY_NAME.match(name) and "m" in letters:
                return                                   # a module: stdin is data
            if _PY_NAME.match(name) and letters[-1] in "WXQ" or \
                    name in _SHELLS and letters[-1] == "o":
                i += 1
            i += 1
            continue
        return                                           # a script file run by name
    if from_stdin:
        code = body
    if code is None:
        return
    if _PY_NAME.match(name):
        _python_body(code, state)
    elif name in _SHELLS:
        _analyze(code, state.copy(), depth + 1)
    else:
        _other_body(code, name, state)


# ------------------------------------------------------------------ the check
def _command(cmd: Cmd, state: State, lx: "_Lexer", depth: int, piped: str | None) -> None:
    words = list(cmd.words)
    while words and _assign(words[0], state):
        words.pop(0)
    while words and words[0].text in _KEYWORDS:
        words.pop(0)
    for op, target in cmd.redirs:
        dup = op == ">&" and re.fullmatch(r"\d+|-", target.text or "")
        if op in _WRITE_OPS or op == ">&" and not dup:
            _target(target, state, f"the redirect `{op}`")
    if not words:
        return
    if words[0].text in ("for", "case", "select"):
        if len(words) > 1:
            state.env[words[1].text] = None
        return
    body = piped
    if cmd.stdin and cmd.stdin[0] == "heredoc":
        body = lx.body(cmd.stdin[1], state.env)
    elif cmd.stdin:
        body = cmd.stdin[1].code(state.env)
    _words(words, state, body, depth)


def _words(words: list, state: State, body: str | None, depth: int) -> None:
    eff = _effective(words)
    if not eff:
        return
    name, args = _base(eff[0]), eff[1:]
    if name == "cd":
        raw = args[0].resolve(state.env) if args else os.environ.get("HOME")
        state.cwd = None if raw is None or raw == "-" else _abs(raw, state.cwd)
    elif name in ("export", "declare", "local", "typeset", "readonly"):
        for a in args:
            _assign(a, state)
    elif name in ("sed", "gsed"):
        if _sed_inplace(args):
            raise Blocked(f"`{name} -i` edits a file in place, and is blocked "
                          f"wherever it points. {_REMEDY}")
    elif name == "perl":
        inplace, code = _perl(args)
        if inplace:
            raise Blocked(f"`perl -i` edits a file in place, and is blocked wherever "
                          f"it points. {_REMEDY}")
        if code is not None:
            _other_body(code, "perl", state)
    elif name == "tee":
        for a in args:
            if not a.text.startswith("-"):
                _target(a, state, "`tee`")
    elif name in ("cp", "mv"):
        for dest in _cp_mv_dest(args):
            _target(dest, state, f"`{name}`")
    elif name == "patch":
        _patch(args, state)
    elif name == "find":
        for i, a in enumerate(args):
            if a.text in ("-exec", "-execdir", "-ok", "-okdir"):
                sub = []
                for b in args[i + 1:]:
                    if b.text in (";", "+"):
                        break
                    sub.append(b)
                _words(sub, state, None, depth)
    elif _PY_NAME.match(name) or name in _SHELLS or name in _OTHER:
        _script(name, args, body, state, depth)


def _analyze(text: str, state: State, depth: int = 0) -> None:
    if depth > 8:
        raise Blocked("the command nests scripts more than eight deep; the edit "
                      "guard blocks what it cannot read.")
    lx = _Lexer(text)
    toks, _ = lx.run()
    for sub in lx.subs:
        _analyze(sub, state.copy(), depth + 1)
    cmds = _commands(toks)
    piped = None
    for cmd in cmds:
        _command(cmd, state, lx, depth, piped)
        piped = None
        eff = _effective([w for w in cmd.words if not _ASSIGN.match(w.text)])
        if cmd.sep == "|" and eff and _base(eff[0]) == "cat" and len(eff) == 1 and \
                cmd.stdin and cmd.stdin[0] == "heredoc":
            piped = lx.body(cmd.stdin[1], state.env)


def check(command: str, cwd: str | None) -> str | None:
    """None when the command may run; otherwise the reason it is blocked."""
    if not _TRIGGER.search(command or ""):
        return None
    try:
        _analyze(command, State(cwd, dict(os.environ)))
    except Blocked as b:
        return str(b)
    return None


def _out_of_time(*_):
    print(f"edit guard: blocked — it ran past its own limit ({LIMIT_S} s) and fails "
          "closed.", file=sys.stderr)
    os._exit(2)


def main() -> int:
    signal.signal(signal.SIGALRM, _out_of_time)
    signal.alarm(LIMIT_S)
    try:
        payload = json.load(sys.stdin)
        command = (payload.get("tool_input") or {}).get("command", "")
        cwd = payload.get("cwd") or os.getcwd()
        reason = check(command, cwd)
    except Exception as e:                 # fails closed
        reason = f"the edit guard failed inside ({e!r}) and fails closed."
    signal.alarm(0)
    if reason:
        print(f"edit guard: blocked — {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
