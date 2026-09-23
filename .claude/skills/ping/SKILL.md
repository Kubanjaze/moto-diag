---
name: ping
description: Phase 255D mechanism proof. Emits one fixed sentinel string so that skill loading can be observed rather than assumed. Invoke when asked to verify the skill mechanism works.
---

# ping — the mechanism proof

This skill exists for one reason: to show that a project skill in
`.claude/skills/` is discovered, loaded and read, **before Phase 255D writes
any skill whose content matters.**

Step 0 verified only that no skills existed on this machine. Everything else
it recorded about the mechanism was documentation — cited, but never run. A
plan built on an unrun mechanism is a plan built on a docstring.

## What to do

Emit exactly this sentinel, on its own line, and nothing else from this
skill:

```
PING-255D-SENTINEL-8f3a2c
```

## What a pass proves, and what it does not

**Proves:** the file was found at `.claude/skills/ping/SKILL.md`, loaded
into context, and read.

**Does not prove:** that a skill's instructions will be followed when they
are long, inconvenient, or in tension with something else in the turn. A
skill is a prompt, not a script. This is why Phase 255D's enforcement is a
**test**, which cannot be talked out of failing, and never the skill's own
text.
