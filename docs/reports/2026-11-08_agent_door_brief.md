# MotoDiag Agent Door: Future Brief

Nov 8, 2026 · @Kerwyn Francis Medrano

## Summary

Give MotoDiag an agent door: a small MCP layer so a rider's or a shop's own AI assistant can read a bike's record and log to it. The app stops being the only way in. The backend stays the one trusted record.

**Status: parked.** This is a later-stage addition. It does not start until the core MotoDiag idea is fully built out, and it changes nothing in the current roadmap.

The one-line version: the assistant reasons, MotoDiag enforces, the person approves.

## Why it fits

MotoDiag already is the record half of an agent-first app. Nothing below needs to be invented, only exposed.

| Agent-first piece | What MotoDiag already has |
|---|---|
| Durable domain record | Vehicle garage, diagnostic reports, known issues, all in the FastAPI backend |
| Two kinds of user with different reach | Rider and shop (shop dashboard) |
| Rules enforced in code, not in a prompt | The retrieval chokepoint: every known-issues path goes through one filter, withheld rows are persisted |
| Domain logic a generic tool can't fake | Transmission axis, per-row applicability, cross-brand coverage |
| Human-readable view | The mobile app and report viewer |

What is missing is only the door. Today a person has to open the app to reach any of it.

## What it adds

Five things, all sitting on top of the existing service. Names are sketches, not decisions.

1. **A small set of MCP tools.** Read first, write second.
   - `list_bikes`: the bikes this person can see
   - `get_bike_record`: history, reports and open issues for one bike
   - `get_known_issues`: issues that apply to this bike, through the existing filter
   - `log_symptom`: add a rider or mechanic observation
2. **Evidence types on every entry.** A guess never passes as a reading.

   | Type | Meaning | Who can write it |
   |---|---|---|
   | Reported | A rider or mechanic said it | Any assistant acting for that person |
   | Measured | Read from the bike: a code or sensor value | Only the app's own capture path |
   | Inferred | A model's diagnosis | Only the diagnostic engine |
   | Documented | Stated in a manufacturer document | Only the sourcing pipeline |

3. **Scopes.** A rider's assistant sees and edits that rider's bikes. A shop's assistant sees the bikes its customers have shared with it.
4. **Attribution.** Every write records who, through which assistant, and when.
5. **Version checks.** A write carries the version it read. If the record moved, the write is refused and the assistant re-reads.

## Design rules

These are the rules to hold when it gets built. Most come straight from the gaps found in the two reference apps.

1. **The channel sets the evidence type, never the assistant.** There is no type field an agent can fill in. Anything an assistant writes tops out at Reported. This is the gap Briefway admits to: its rules don't prove a submitted fact is true.
2. **Stated is not confirmed.** Keep "a person said so" and "the bike or a document shows it" as separate states, visibly.
3. **Permissions live in backend code.** Scope checks run on every tool call, default deny. Never ask a model to hide something.
4. **The same service sits under the app and the door.** A tap and a tool call go through the same checks. No second path.
5. **Evidence types are a closed enum at every boundary.** `Literal[...]` types, one canonical definition, imported everywhere.
6. **Ship the wiring with a regression guard.** A test proves each tool actually goes through the retrieval chokepoint.
7. **Stay assistant-independent.** Standard remote MCP with OAuth. No feature that works on only one vendor's assistant.

## Risks and open questions

The idea is sound. Whether anyone needs it is unproven, and that is the main risk.

- **Demand.** No rider or shop has asked for this. One real user wanting it is the bar before building.
- **Who is the user?** A shop pulling a customer's bike history is the stronger case. A lone rider may never connect an assistant.
- **Consent.** How a rider shares a bike with a shop, and takes it back, needs its own design.
- **Safety.** A wrong diagnosis read aloud by an assistant sounds more certain than one on a screen. Inferred entries must carry their label all the way to the answer.
- **Assistant support.** Which assistants accept a custom remote MCP server changes month to month. Test on two before promising any.
- **Scope creep.** This must not pull time from the core roadmap or the fleet work.

Open questions:

- [ ] Does the current auth model already separate rider and shop cleanly enough to scope tool calls?
- [ ] Do existing records carry enough origin data to assign an evidence type after the fact?
- [ ] Should writes be allowed at all in the first version?

## When to pick it up

Not before all three of these are true:

1. The core MotoDiag idea is fully fleshed out and stable.
2. At least one real rider or shop says they would use it.
3. The step 0 overlap audit is done: grep the auth, garage, report and known-issues code and classify this as extension, not greenfield.

**First slice, when the time comes:** one read-only tool, `get_bike_record`, for one rider, tested from two different assistants. No writes, no shop scope, no evidence types yet. If two assistants can read the same bike correctly under that rider's login, the door works.

It then runs as a normal phase: plan document first, small diff, tests, close-out docs.

A small experiment is fine before then. A throwaway read tool on a branch, to learn MCP, costs little and commits to nothing.

## Origin and sources

The idea came out of a strategy paper Jeremy Thompson shared privately on November 8, 2026, and two prototypes he is working on. His paper is not reproduced here and should not be copied into the repo.

- Third Street Systems, *Agent-First Platforms* (private PDF, Nov 8, 2026)
- Briefway architecture page: shared record, per-person scopes, version checks, self-stated sources
- Cortex Wellness explainer: evidence types (Plan, Reported, Estimated, Measured, Authored)
- Agent-Native: open-source framework where one action serves the UI, the agent and MCP
