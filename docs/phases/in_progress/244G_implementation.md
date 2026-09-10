# Phase 244G — A guard that reads source text will eventually read a comment

**Version:** 1.0 | **Tier:** Standard | **Date:** 2026-09-10

---

## Goal

Four times in one session a guard that matched an identifier as **text** fired
on the **prose** explaining it:

| phase | guard | fired on |
|---|---|---|
| 241 | `SafetyChecker` has no production caller | a docstring citing it as a cross-reference |
| 244 | provenance attribution filter | the correction quoting the claim it refutes |
| 244D | `INSERT OR IGNORE` must not appear | the comment saying why it is not used |
| 244F | derivation lives in this module | the code moving, the prose staying |

Two were repaired ad hoc with `ast`. This phase makes the property general and
prevents recurrence.

**The reverse case is worse and nobody has hit it yet.** A guard asserting
`"get_session" in src` passes if the identifier survives *only in a comment* —
so deleting the code it protects leaves the guard green. A false failure is
loud; a false pass rots silently.

## Step 0 findings

Fourteen assertions across the suite read Python source and test a literal
against it. Two are negative (`not in`) and vulnerable to firing on prose; the
rest are positive and vulnerable to passing on prose. The `.read_text()`
population is larger — 60 files — but most read report output or JSON corpus
content, where matching text is exactly the point and the concern does not
apply.

**The perverse incentive is the real damage.** A guard that punishes explaining
a defect teaches the next author to delete the explanation rather than examine
the code. Phase 241's tripwire fired on the sentence written to make its own gap
findable.

## Non-goals

- **Not touching assertions over data.** Report text, API bodies and JSON corpus
  blobs are content, not code; matching them literally is correct.
- **Not banning source assertions.** They are legitimate — sometimes the only way
  to pin a structural property. The fix is to make them read code.

## Logic

**`tests/support/source_guards.py`** provides `code_of(target)`: source with
**comments and docstrings blanked**, everything else byte-for-byte intact.

Implemented with `tokenize` plus `ast`, replacing comment and docstring tokens
with equivalent whitespace so line numbers, columns and formatting survive. That
matters: a guard asserting on a multi-line SQL literal must still match, so
`ast.unparse` — which normalises quoting and layout — is the wrong tool.

Ordinary string literals are **kept**. A guard pinning a `tool_choice` dict or an
`ORDER BY` clause is reading code that happens to be a string, and blanking those
would break exactly the guards this phase exists to keep working.

**The vulnerable guards convert to `code_of`.** Fourteen call sites; each keeps
its assertion and changes only what it reads.

**A meta-guard prevents recurrence.** A test walks the suite and fails when an
assertion tests a literal against a variable holding raw Python source without
going through `code_of`. That is the deliverable — the conversions fix today,
the meta-guard fixes tomorrow.

## Key Concepts

- **Mention is not use.** The distinction the whole family turns on.
- **A false pass is worse than a false failure.** Loud wrongness gets fixed.
- **A guard must not punish documentation**, or it selects for codebases that
  explain nothing.
- **Preserve formatting when blanking.** A guard that matches a multi-line
  literal must keep working, so normalising rewriters are unusable here.

## Verification Checklist

- [ ] `code_of` blanks comments
- [ ] `code_of` blanks module, class and function docstrings
- [ ] `code_of` keeps ordinary string literals, including multi-line ones
- [ ] Line numbers and indentation survive blanking
- [ ] All fourteen vulnerable assertions read `code_of`
- [ ] A negative guard no longer fires when its identifier appears only in a comment
- [ ] A positive guard now fails when its identifier survives only in a comment
- [ ] The meta-guard fails on a newly added raw-source assertion
- [ ] Phase 241's SafetyChecker tripwire and 244D's `OR IGNORE` guard keep working
- [ ] Mutation: unblank comments → the mention-vs-use guard fails
- [ ] Full regression green

## Risks

- **The meta-guard could become the thing people work around.** It must name the
  helper and the reason in its failure message, so the cheap fix is the correct
  one.
- **False positives in the meta-guard.** Detecting "a variable holding Python
  source" is heuristic. It keys on assignment from `getsource(` or a `.py`
  `read_text(`, which is narrow and auditable, and an explicit opt-out marker is
  provided for the rare legitimate case rather than leaving someone to fight it.
- **Blanking could corrupt source.** Anything other than byte-identical output
  outside comments and docstrings would silently change what guards match.
  Asserted directly.
- **This phase's own guards are in the vulnerable family.** They are written
  against fixtures, not against the suite's own text, so the tool is not used to
  test itself into a circle.
