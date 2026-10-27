"""Phase 392's mutations: each breaks one thing the phase built, and a test must go red.

Run from the repository root: `.venv/bin/python docs/phases/in_progress/392_mutate.py`
(ROOT is three levels up from in_progress/ or completed/). 390's and 391's
harness: exact strings (each must occur once), the tests run after clearing
`__pycache__`, every file restored whatever happens. Exits 1 if any mutation
stays green. An argument runs only the mutations whose name starts with it:
`O` the order, `A` answered stops, `P` plan_check, `C` the citations, `F`
F223, `T` F226, `L` F225, `U` F227, `R` F228, `N` the next mission, `Y` the
Yeoman.

Where a rule has two guards on purpose (a rule-1 stop is refused by the
Covers check and by `answer`; the operator's label is waited for by the due
rule and by the stage), the mutation breaks both: one alone is caught by
the other by design.

No mutation makes a real model call or reaches GitHub. Run it only when no
fleet model-free run is in progress on this machine (F220).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]

F = ".claude/skills/fleet/"
PO, PC, DI, FG = F + "plan_order.py", F + "plan_check.py", F + "dispatcher.py", F + "fleet_git.py"
RT, YE, SC, CA = F + "red_team.py", F + "yeoman.py", F + "scout.py", F + "captain.py"
XO, QM, EN = F + "xo.py", F + "quartermaster.py", F + "engineer.py"
UNIT = "ops/desktop/motodiag-fleet.service"


def pytest(*args: str) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
            "-o", "addopts=", *args]


T_PO = pytest("tests/test_phase392_plan_order.py")
T_PC = pytest("tests/test_phase387_fleet_contract.py")
T_CITE = pytest("tests/test_phase392_ranks_cite.py")
T_NEXT = pytest("tests/test_phase392_next_mission.py")
T_ANS = pytest("tests/test_phase392_answers.py")
T_AUTH = pytest("tests/test_phase392_authors.py")
T_TMP = pytest("tests/test_phase392_tmp.py")
T_LIM = pytest("tests/test_phase392_check_limit.py")
T_UNIT = pytest("tests/test_phase388_service_contract.py")
T_C7 = pytest("tests/test_phase392_red_team_c7.py")
T_Y = pytest("tests/test_phase387_yeoman.py")

MUTATIONS = [
    # the order (plan_order.py)
    ("O1 an unknown builder passes", [(PO, "if built not in BUILT_BY:", "if False:")], T_PO),
    ("O2 a need with no what passes", [(PO, 'if needs != "nothing" and not any(',
                                        'if False and not any(')], T_PO),
    ("O3 the as-of date is not checked", [(PO, "        if day not in {d[:10] for d, _, _ in changes(plan)}:",
                                           "        if False:")], T_PO),
    ("O4 the dated entry need not cite the as-of K-id",
     [(PO, "        elif not any(d[:10] == day and kid in body for d, _, body in changes(plan)):",
       "        elif False:")], T_PO),
    ("O5 a phase with no row passes",
     [(PO, 'fails += [f"phase {e.phase} has no ROADMAP row" for e in order.entries if e.phase not in rows]',
       "fails += []")], T_PO),
    ("O6 a closed phase is next", [(PO, 'return next((e for e in order.entries if rows.get(e.phase, ("",))[0] != DONE), None)',
                                    "return next(iter(order.entries), None)")], T_PO),
    ("O7 a number inside another names it", [(PO, 'rf"(?<![\\w.]){re.escape(phase)}(?!\\w)"',
                                              'rf"{re.escape(phase)}"')], T_PO),
    # answered stops (K50)
    ("A1 a rule-1 stop is answered (both guards)",
     [(PO, '    if m.group(1) in RULE1_KINDS:\n        return f"Covers names',
       '    if False:\n        return f"Covers names'),
      (PO, "    if kind not in ANSWERABLE:\n        return None", "    if False:\n        return None")],
     T_PO),
    ("A2 two covering K-ids answer", [(PO, "    return found[0] if len(found) == 1 else None",
                                       "    return found[0] if found else None")], T_PO),
    ("A3 the same stop is answered twice", [(DI, "        if self.has_comment(issue, mark):",
                                             "        if False:")], T_ANS),
    ("A4 the answer never reaches the Engineer", [(EN, "    if answer:\n        prompt += ANSWERED",
                                                   "    if False:\n        prompt += ANSWERED")], T_ANS),
    ("A5 the answered Engineer is never due",
     [(DI, "            if said and (latest_mine is None or said[0] >= latest_mine[0]):",
       "            if False:")], T_ANS),
    # plan_check P9, P10, the pin
    ("P9 any plan puts its phase in order",
     [(PC, '    if (any(d.kid in kids and plan_order.names(f"{d.words} {d.check}", phase)',
       '    if (True or any(d.kid in kids and plan_order.names(f"{d.words} {d.check}", phase)')],
     T_PC),
    ("P10a no phase is fleet-only", [(PC, "    if not fleet_only:\n        return []",
                                      "    if True:\n        return []")], T_PC),
    ("P10b a closed first-shop phase counts",
     [(PC, "    shop = [p for p in plan_order.first_shop(por) if status.get(p) != DONE]",
       "    shop = list(plan_order.first_shop(por))")], T_PC),
    ("P11 the pin is wider than needed", [(PC, '    "384": frozenset({"P9"}),',
                                           '    "384": frozenset({"P9", "P10"}),')], T_PC),
    # the citations
    ("C1 the XO's verdict cites nothing", [(XO, "    if cite:\n        lines += [\"\", cite]",
                                            "    if False:\n        lines += [\"\", cite]")], T_CITE),
    ("C2 the Red Team's issue comment cites nothing",
     [(DI, "f\"(PR #{pr['number']}).\\n\\n{red_team.findings_text(v)}{filed}\\n\\n{cite}\")",
       "f\"(PR #{pr['number']}).\\n\\n{red_team.findings_text(v)}{filed}\")")], T_CITE),
    ("C3 the Captain's plan brief lacks the record",
     [(CA, '            f"=== docs/phases/in_progress/{phase}_step0.md ===\\n{step0}\\n\\n{record}")',
       '            f"=== docs/phases/in_progress/{phase}_step0.md ===\\n{step0}")')], T_CITE),
    ("C4 the Science Officer's report lacks its section", [(SC, "{record}\n## The calls",
                                                            "## The calls")], T_CITE),
    ("C5 the Quartermaster's context lacks the record",
     [(QM, '            + f"\\n\\n{plan_order.brief_block(clone, phase)}")', "            )")], T_CITE),
    ("C6 the Red Team's context lacks the record",
     [(RT, '            + f"\\n\\n{plan_order.brief_block(clone, phase)}")', "            )")], T_CITE),
    ("C7 the Captain's recommendation cites nothing",
     [(DI, '                      f"(PR #{pr[\'number\']}).\\n\\n{lines}\\n\\n{cite}\\n\\nThe operator merges.")',
       '                      f"(PR #{pr[\'number\']}).\\n\\n{lines}\\n\\nThe operator merges.")')], T_CITE),
    # F223
    ("F1 every author's comment counts",
     [(FG, '    return [c for c in comments if str((c.get("author") or {}).get("login", "")).lower() in want]',
       "    return list(comments)")], T_AUTH),
    ("F2 the operator counts on any issue", [(FG, '    if TRIAL_MARKER in (issue_body or ""):\n        out.add(OPERATOR_LOGIN)',
                                              "    if True:\n        out.add(OPERATOR_LOGIN)")], T_AUTH),
    ("F3 any account's issue is a mission",
     [(FG, "    return login in {OPERATOR_LOGIN.lower(), *([fleet.login.lower()] if fleet else [])}",
       "    return True")], T_AUTH),
    ("F4 the XO counts a third login's rounds",
     [(XO, '        data.get("comments", []), fleet_git.trusted_authors(data.get("body", ""), identity_file))]',
       '        data.get("comments", []), {"mallory", *fleet_git.trusted_authors(data.get("body", ""), identity_file)})]')],
     T_AUTH),
    # F226
    ("T1 the worker-loss files are deleted", [(DI, "        if p.name.startswith(WORKER_LOSS_PREFIX):\n            kept.append(p.name)",
                                               "        if False:\n            kept.append(p.name)")], T_TMP),
    ("T2 a finished stage keeps its tmp", [(DI, "            if not (j.run / journal.HELD).is_file():\n                clean_tmp(j.run)",
                                            "            if False:\n                clean_tmp(j.run)")], T_TMP),
    ("T3 a held stage loses its tmp", [(DI, "            if not (j.run / journal.HELD).is_file():\n                clean_tmp(j.run)",
                                        "            if True:\n                clean_tmp(j.run)")], T_TMP),
    ("T4 a paused stage ends", [(DI, '        if j is not None and outcome != "rate-limited":\n            j.end',
                                 "        if j is not None:\n            j.end")], T_TMP),
    ("T5 prune cleans an unfinished run", [(DI, "            if j is not None and not j.unfinished:\n                clean_tmp(p)",
                                            "            if j is not None:\n                clean_tmp(p)")], T_TMP),
    ("T6 prune cleans a held run", [(DI, "            if str(p) in keep_also or (p / journal.HELD).is_file():\n                continue",
                                     "            if str(p) in keep_also:\n                continue")], T_TMP),
    ("T7 a check run keeps its tmp", [(DI, "        clean_tmp(run)                 # F226: the run has ended; its result is written",
                                       "        pass")], T_TMP),
    ("T8 the reclaim line never says nothing came back",
     [(DI, '"space inside Ubuntu only)") if after - before < 0.1 else ""',
       '"space inside Ubuntu only)") if False else ""')], T_TMP),
    # F225
    ("L1 the time-out escapes the stage", [(DI, "        except subprocess.TimeoutExpired as e:\n            # F225",
                                            "        except ZeroDivisionError as e:\n            # F225")], T_LIM),
    ("L2 only the direct child is killed", [(DI, "                os.killpg(p.pid, signal.SIGKILL)",
                                             "                p.kill()")], T_LIM),
    ("L3 the limit is not the operator's", [(DI, "CHECK_TIMEOUT_S = 5400", "CHECK_TIMEOUT_S = 3600")],
     T_LIM),
    # F227
    ("U1 the unit sets no open-file limit", [(UNIT, "\nLimitNOFILE=1048576\n", "\n")], T_UNIT),
    # F228
    ("R1 C7 is not set aside on an early back",
     [(RT, 'not (not files and f.startswith("C7 "))', 'not (False and f.startswith("C7 "))')], T_C7),
    ("R2 round 3's back files nothing", [(RT, "    files = not back or rnd >= MAX_ROUNDS",
                                          "    files = not back")], T_C7),
    ("R3 the number is not written into the rows",
     [(RT, '            line = line[:m.start("rko")] + m.group("rko").rstrip() + f" {fnum} " + line[m.end("rko"):]',
       "            pass")], T_C7),
    ("R4 the brief does not state C7", [(RT, "the checker holds (K9): every\nwording defect left open goes to one finding",
                                         "the checker holds (K9): any\nwording defect is fine")], T_C7),
    ("R5 the record may remove from FOLLOWUPS", [(FG, '    if rank == "red-team-record" and FOLLOWUPS in names:',
                                                  "    if False:")], T_C7),
    # the next mission
    ("N1 a builder's phase is not waited for", [(DI, '        if e.built_by != "fleet":', "        if False:")],
     T_NEXT),
    ("N2 the operator's label is not waited for (both guards)",
     [(DI, "        if labels & set(OPERATOR):\n            return None\n        if e.need",
       "        if False:\n            return None\n        if e.need"),
      (DI, '            if label in self.labels_of(n):\n                return "waiting for the operator"',
       '            if False:\n                return "waiting for the operator"')], T_NEXT),
    ("N3 the row's edit changes more than its status",
     [(DI, '    cells[3] = f" {roadmap_check.ACTIVE} "\n    lines[hits[0]] = "|".join(cells)',
       '    cells[3] = f" {roadmap_check.ACTIVE} "\n    cells[4] += "more "\n    lines[hits[0]] = "|".join(cells)')],
     T_NEXT),
    ("N4 the row rank's line rule is off", [(FG, '    if rank == "row" and ROADMAP in names:', "    if False:")],
     T_NEXT),
    ("N5 the row rank may touch any file", [(FG, "        return path == ROADMAP\n    return rank == \"engineer\"",
                                             "        return True\n    return rank == \"engineer\"")], T_NEXT),
    ("N6 the issue is opened again", [(DI, "lambda: find() or self.open_mission(", "lambda: self.open_mission(")],
     T_NEXT),
    ("N7 a list that does not read exactly still starts",
     [(DI, '        if fails:\n            self.once("order:"', '        if False:\n            self.once("order:"')],
     T_NEXT),
    ("N8 without the account the stage goes on",
     [(DI, '        if ident is None:\n            self.once("next-account"',
       '        if False:\n            self.once("next-account"')], T_NEXT),
    # the Yeoman
    ("Y1 decide takes any Covers", [(YE, "    if bad_cover:\n        why.append(bad_cover)",
                                     "    if False:\n        why.append(bad_cover)")], T_Y),
]


def clear_caches() -> None:
    for d in (ROOT / ".claude" / "skills").rglob("__pycache__"):
        for f in d.glob("*.pyc"):
            f.unlink()


def run(command: list[str]) -> int:
    clear_caches()
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True).returncode


def main(argv: list[str]) -> int:
    chosen = [m for m in MUTATIONS if not argv or m[0].startswith(argv[0])]
    commands = []
    for m in chosen:
        if m[2] not in commands:
            commands.append(m[2])
    for command in commands:
        assert run(command) == 0, f"not green before mutating: {command}"
    survivors = []
    for name, edits, command in chosen:
        originals = {}
        try:
            for rel, old, new in edits:
                path = ROOT / rel
                originals.setdefault(rel, path.read_text())
                current = path.read_text()
                assert current.count(old) == 1, \
                    f"{name}: the text occurs {current.count(old)} times in {rel}"
                path.write_text(current.replace(old, new))
            code = run(command)
        finally:
            for rel, text in originals.items():
                (ROOT / rel).write_text(text)
        verdict = "red" if code != 0 else "GREEN (survived)"
        print(f"{name}: {verdict}", flush=True)
        if code == 0:
            survivors.append(name)
    for command in commands:
        assert run(command) == 0, f"not green after restoring: {command}"
    print(f"{len(chosen) - len(survivors)}/{len(chosen)} red")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
