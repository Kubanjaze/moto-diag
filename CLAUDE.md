# moto-diag — project rules

Cross-project rules live in the workspace `CLAUDE.md`. This file holds what
is true of **moto-diag specifically**, and is loaded when a session starts
here.

@../workspace-docs/claude/working-rules.md

## Start sessions at this repository root

Skills and hooks under `.claude/` are discovered **from the directory the
session was started in, at the moment it starts.** A session opened in the
parent directory does not see them, and a skill added part-way through a
session is not available until the next one. Measured in Phase 255D, at
both candidate roots, before this rule was written.

No symlinks and no `.claude/` at the parent: both work, and both hide where
the mechanism is actually reading from.

## Procedure folders

Recurring procedures are skills in `.claude/skills/`, each with its own
dated changelog, a script for anything that is "run this and check that",
and a hand-written known-bad fixture its assertion must fail on.

| folder | what it covers |
|---|---|
| `closeout` | finishing a phase; the seven artefacts; `verify_phase.sh` |
| `finding` | filing an F-number; every cited number must resolve |
| `refute` | an adversarial pass, and the checklist it must emit |

The enforcement is a test, never the skill's own text: a skill is a prompt
and can be talked out of; `tests/test_phase255D_*_contract.py` cannot.

---

## MotoDiag-Specific Context

**Repo:** `Kubanjaze/moto-diag` | **Local:** `~/Projects/moto-diag`

> The local path was corrected when this file was created: the line carried a
> Windows path (`C:\Users\Kerwyn\PycharmProjects\...`) that has not been true of
> this machine for some time. Everything else below is moved verbatim.

### MotoDiag track summary (198 phases, 11 tracks)
- A (01-12): Core Infrastructure
- B (13-78): Vehicle Knowledge Base (Harley, Honda, Yamaha, Kawasaki, Suzuki, cross-platform)
- C (79-95): AI Diagnostic Engine
- C2 (96-108): Media Diagnostic Intelligence (video/audio analysis)
- D (109-121): CLI + User Experience
- E (122-135): Hardware OBD Interface
- F (136-147): Advanced Diagnostics
- G (148-162): Shop Management + Optimization
- H (163-172): API + Web Layer
- I (173-192): Mobile App (iOS App Store + Google Play Store, React Native, universal device support)
- J (193-198): Ship + Scale

---


---

## Change log

### 2026-09-23 — the working-rules index is imported (Phase 257)

Nothing loaded the workspace rules in this repo: a session started here saw
this file and nothing else. Phase 257 then committed an exclusion with no
positive control (bug fix #1, `6639490`) — a rule the index states in one
line. The `@../workspace-docs/claude/working-rules.md` line under the
opening paragraph imports the lean index (9 KB) into every session started
at this root. The first session after this change asks once to approve the
external import.

### 2026-09-22 — created (Phase 255D)

moto-diag had no `CLAUDE.md` of its own. Its rules sat in the workspace
file in front of every session for every project. Created here with the
MotoDiag-specific context moved verbatim, plus the two rules Phase 255D
measured: repo-rooted sessions, and where the procedure folders live.
