"""Phase 257 — the one-turn, no-tools source stage, driven end to end without a model.

`subprocess.run` is replaced by a fake that records every command and
answers as `claude -p --output-format json` does, so the real `batch`,
`run_stage`, `build_cmd`, route guards, `candidates` and `entry_check`
all run; only the model is absent. What is pinned: a spelling no library
file names costs no call; a spelling that has excerpts costs exactly one,
with no tools; the prompt carries the excerpts and not the old browsing
instructions; a finding citing anything but its excerpts is rejected
(E10) and never reaches refute; a stage that looped is an error; every
stage's tokens are summed into the summary and a batch above 150K per
spelling sent is a stop — the before figure being the Kymco agent loop's
own recorded usage (`fixtures/kymco_source_usage.json`).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "source-transmission"
sys.path.insert(0, str(SKILL))

import orchestrate as O  # noqa: E402

LIB = SKILL / "fixtures" / "library"
TRAIL_DOC = str(LIB / "zz_trail_om.txt")
TRAIL_QUOTE = "Transmission  5-speed constant mesh, return shift"
SUBC_MODEL = O.ROUTES["subconscious"]["model"]
OPUS_MODEL = O.ROUTES["anthropic"]["model"]


def _usage(model, n_in=1000, n_out=100):
    return {model: {"inputTokens": n_in, "outputTokens": n_out,
                    "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}}


def _found(spelling="Trail 250", document=TRAIL_DOC, quote=TRAIL_QUOTE):
    return {"make": "ZZ", "spelling": spelling, "aliases": ["trail 250"], "outcome": "found",
            "transmission": "manual", "quote": quote, "document": document, "page": 2,
            "evidence_kind": "owners_manual"}


class Fake:
    """Stands in for subprocess.run. Records calls; answers per route."""

    def __init__(self, findings=(), turns=2, verdict="kept", source_usage=None, refute_usage=None,
                 model_line="", names_model=True):
        self.calls: list[list[str]] = []
        self.findings, self.turns, self.verdict = list(findings), turns, verdict
        self.model_line, self.names_model = model_line, names_model
        self.source_usage = source_usage if source_usage is not None else _usage(SUBC_MODEL)
        self.refute_usage = refute_usage if refute_usage is not None else _usage(OPUS_MODEL)

    def __call__(self, cmd, **kw):
        if cmd[0] == "git":
            raise AssertionError("make_run is stubbed; nothing may clone")
        self.calls.append(cmd)
        if str(O.SUBC) in cmd:
            out = {"type": "result", "is_error": False, "num_turns": self.turns,
                   "structured_output": {"findings": self.findings},
                   "modelUsage": self.source_usage}
        else:
            findings = json.loads(cmd[cmd.index("-p") + 1].split("Findings:\n", 1)[1])
            out = {"type": "result", "is_error": False, "num_turns": 3,
                   "structured_output": {"verdicts": [
                       {"spelling": f["spelling"], "verdict": self.verdict, "quote": f["quote"],
                        "page": f["page"], "model_line": self.model_line,
                        "names_model": self.names_model, "reason": "fake refute"}
                       for f in findings]},
                   "modelUsage": self.refute_usage}
        return subprocess.CompletedProcess(cmd, 0, stdout="banner\n" + json.dumps(out) + "\n", stderr="")

    def source_calls(self):
        return [c for c in self.calls if str(O.SUBC) in c]

    def refute_calls(self):
        return [c for c in self.calls if str(O.SUBC) not in c]


@pytest.fixture
def run_with(tmp_path, monkeypatch):
    def make_run(root, make):
        run = tmp_path / "run"
        for d in ("clone", "tmp/cfg"):
            (run / d).mkdir(parents=True, exist_ok=True)
        return {"run": run, "clone": run / "clone", "tmp": run / "tmp", "profile": run / "sandbox.sb"}

    monkeypatch.setattr(O, "make_run", make_run)
    monkeypatch.setattr(O, "LIBRARY", LIB)
    monkeypatch.setattr(O, "alert", lambda *a: None)
    monkeypatch.setattr(O, "subc_gateway", lambda *a: O.ROUTES["subconscious"]["host"])
    monkeypatch.setattr(O, "load_anthropic_token", lambda *a: "sk-ant-oat01-" + "x" * 40)

    def go(fake, spellings):
        monkeypatch.setattr(O.subprocess, "run", fake)
        return O.batch("ZZ", spellings)
    return go


class TestNoExcerptNoCall:
    def test_a_spelling_no_file_names_costs_nothing(self, run_with):
        fake = Fake()
        s = run_with(fake, ["Nowhere 999"])
        assert fake.calls == []
        [f] = s["findings"]
        assert f["outcome"] == "no_evidence" and f["transmission"] is None
        assert "model was not called" in f["note"]
        assert s["sent_to_model"] == [] and s["stops"] == [] and s["ready_to_write"] == []

    def test_only_spellings_with_excerpts_are_sent(self, run_with):
        fake = Fake(findings=[_found()])
        s = run_with(fake, ["Trail 250", "Nowhere 999"])
        assert s["sent_to_model"] == ["Trail 250"]
        prompt = fake.source_calls()[0][fake.source_calls()[0].index("-p") + 1]
        assert '"Trail 250"' in prompt and "Nowhere 999" not in prompt


class TestOneTurnNoTools:
    def test_exactly_one_source_call_with_no_tools(self, run_with):
        fake = Fake(findings=[_found()])
        run_with(fake, ["Trail 250"])
        [cmd] = fake.source_calls()
        i = cmd.index("--tools")
        assert cmd[i + 1] == ""
        assert "--strict-mcp-config" in cmd and "--disable-slash-commands" in cmd

    def test_the_prompt_is_the_excerpts_not_a_browsing_brief(self, run_with):
        fake = Fake(findings=[_found()])
        run_with(fake, ["Trail 250"])
        prompt = fake.source_calls()[0][fake.source_calls()[0].index("-p") + 1]
        excerpts = json.loads(prompt.split("EXCERPTS (JSON, by spelling):\n", 1)[1])
        assert [e["document"] for e in excerpts["Trail 250"]] == [TRAIL_DOC]
        assert "5-speed constant mesh, return shift" in excerpts["Trail 250"][0]["text"]
        for gone in ("read it first", "on the web", "evidence/", "url_tried"):
            assert gone not in prompt, gone

    def test_a_stage_that_looped_is_an_error_and_a_stop(self, run_with):
        fake = Fake(findings=[_found()], turns=O.SOURCE_MAX_TURNS + 3)
        s = run_with(fake, ["Trail 250"])
        assert "turns" in s["source_error"]
        assert any("source stage error" in r for r in s["stops"])
        assert fake.refute_calls() == [] and s["ready_to_write"] == []


class TestTheExcerptsBindTheFindings:
    def test_a_found_finding_from_its_excerpt_goes_to_refute(self, run_with):
        fake = Fake(findings=[_found()])
        s = run_with(fake, ["Trail 250"])
        assert s["rejections"] == [] and len(fake.refute_calls()) == 1
        assert [f["spelling"] for f in s["ready_to_write"]] == ["Trail 250"]

    def test_a_document_it_was_not_handed_is_stopped_before_refute(self, run_with):
        """The F141 shape: a file that holds the quote and names the
        machine, but that the stage was never shown."""
        planted = str(SKILL / "fixtures" / "docs" / "zz_trail_om.txt")
        fake = Fake(findings=[_found(document=planted, quote="Transmission 5-speed constant mesh, return shift")])
        s = run_with(fake, ["Trail 250"])
        assert any(r.startswith("E10") for r in s["rejections"]), s["rejections"]
        assert fake.refute_calls() == [] and s["ready_to_write"] == []
        assert any("rejected by entry_check" in r for r in s["stops"])


KYMCO = json.loads((SKILL / "fixtures" / "kymco_source_usage.json").read_text(encoding="utf-8"))


class TestTheTokenStop:
    """150K tokens per spelling sent, across every stage — the operator's
    ceiling. A stop, not a setting: nothing in the CLI changes it."""

    def test_usage_is_summed_per_stage_into_the_summary(self, run_with):
        fake = Fake(findings=[_found()], source_usage=_usage(SUBC_MODEL, 20_000, 2_000),
                    refute_usage=_usage(OPUS_MODEL, 5_000, 1_000))
        s = run_with(fake, ["Trail 250"])
        t = s["tokens"]
        assert t["stages"]["source"]["total"] == 22_000
        assert t["stages"]["refute"]["total"] == 6_000
        assert t["total"] == 28_000 and t["ceiling"] == 150_000 and t["stop"] is None
        assert s["stops"] == []

    def test_the_recorded_kymco_source_stage_is_a_stop(self):
        """The real before: the agent loop's own modelUsage, one spelling."""
        u = O.usage(KYMCO)
        assert u["inputTokens"] == 7_661_322
        assert O.token_stop({"source": u}, 1).startswith("tokens ")

    def test_an_over_budget_source_stage_stops_and_skips_refute(self, run_with):
        fake = Fake(findings=[_found()], source_usage=KYMCO["modelUsage"])
        s = run_with(fake, ["Trail 250"])
        assert s["tokens"]["stop"] and any("per spelling" in r for r in s["stops"])
        assert fake.refute_calls() == [] and s["ready_to_write"] == []

    def test_refute_has_its_own_budget(self, run_with):
        """Operator decision 2026-09-23: refute is budgeted apart, never
        trimmed. The real Kymco re-run — source 9,227, refute 226,857 — is
        under both budgets."""
        fake = Fake(findings=[_found()], source_usage=_usage(SUBC_MODEL, 9_227, 0),
                    refute_usage=_usage(OPUS_MODEL, 226_857, 0))
        s = run_with(fake, ["Trail 250"])
        assert s["tokens"]["stop"] is None and s["stops"] == []
        assert s["tokens"]["refute_ceiling"] == O.REFUTE_STOP_PER_FINDING

    def test_refute_over_its_budget_is_a_stop_not_a_skip(self, run_with):
        fake = Fake(findings=[_found()], source_usage=_usage(SUBC_MODEL, 9_227, 0),
                    refute_usage=_usage(OPUS_MODEL, O.REFUTE_STOP_PER_FINDING + 1, 0))
        s = run_with(fake, ["Trail 250"])
        assert len(fake.refute_calls()) == 1, "refute ran; it was not skipped"
        assert any(r.startswith("refute tokens") for r in s["stops"]) and s["ready_to_write"] == []

    def test_refute_tokens_do_not_spend_the_source_budget(self, run_with):
        fake = Fake(findings=[_found()], source_usage=_usage(SUBC_MODEL, 100_000, 0),
                    refute_usage=_usage(OPUS_MODEL, 100_000, 0))
        s = run_with(fake, ["Trail 250"])
        assert s["stops"] == []

    def test_the_budget_is_per_spelling_sent_not_per_spelling_asked(self, run_with):
        """A no_evidence spelling costs nothing and must not lend its 150K."""
        fake = Fake(findings=[_found()], source_usage=_usage(SUBC_MODEL, 200_000, 0))
        s = run_with(fake, ["Trail 250", "Nowhere 999", "Nowhere 998"])
        assert s["tokens"]["sent"] == 1 and s["tokens"]["ceiling"] == 150_000
        assert any("per spelling" in r for r in s["stops"])
        assert fake.refute_calls() == [], "refute was spent on a batch already over budget"

    def test_cache_reads_and_writes_are_tokens(self, run_with):
        """An agent loop's cost is mostly cache reads (Kymco: 6,133,632)."""
        mu = {SUBC_MODEL: {"inputTokens": 10_000, "outputTokens": 1_000,
                           "cacheReadInputTokens": 120_000, "cacheCreationInputTokens": 30_000}}
        fake = Fake(findings=[_found()], source_usage=mu)
        s = run_with(fake, ["Trail 250"])
        assert s["tokens"]["stages"]["source"]["total"] == 161_000
        assert any("per spelling" in r for r in s["stops"])

    def test_unrecorded_usage_is_a_stop(self, run_with):
        fake = Fake(findings=[_found()], source_usage={})
        s = run_with(fake, ["Trail 250"])
        assert any("unrecorded" in r for r in s["stops"])

    def test_the_ceiling_is_the_operators(self):
        assert O.TOKEN_STOP_PER_SPELLING == 150_000


class TestNotAMachineIsNotSearched:
    def test_a_classed_spelling_costs_nothing_and_is_reported(self, run_with, monkeypatch):
        import candidates
        asked = []
        real = candidates.candidates
        monkeypatch.setattr(candidates, "candidates", lambda sp, *a, **k: asked.append(list(sp)) or real(sp, *a, **k))
        fake = Fake(findings=[_found()])
        s = run_with(fake, ["Trail 250", "2020 service manual", "Gilera"])
        assert asked == [["Trail 250"]]
        assert s["not_a_machine"] == {"2020 service manual": "prose", "Gilera": "other_marque"}
        assert s["sent_to_model"] == ["Trail 250"]
        notes = {f["spelling"]: f.get("note", "") for f in s["findings"]}
        assert "not a machine name (prose)" in notes["2020 service manual"]


GT_DOC = str(LIB / "pdfs" / "zz_sprint900gt_om.txt")
S_DOC = str(LIB / "pdfs" / "zz_sprint900_om.txt")


def _sprint(document, quote):
    return {"make": "ZZ", "spelling": "Sprint 900", "aliases": [], "outcome": "found", "transmission": "manual",
            "quote": quote, "document": document, "page": 3, "evidence_kind": "owners_manual"}


class TestADocumentSourcesOnlyTheModelItNames:
    """The 4609 over-claim (operator decision 4): a page that names only a
    sibling — the Sprint 900 GT — is family evidence for the Sprint 900. It
    is recorded, refute still runs, and it writes nothing unless refute
    returns a line that names the model and that line is on the page."""

    def test_a_sibling_page_is_family_evidence_and_writes_nothing(self, run_with):
        fake = Fake(findings=[_sprint(GT_DOC, "Transmission  6-speed constant mesh, return shift")])
        s = run_with(fake, ["Sprint 900"])
        assert len(fake.refute_calls()) == 1
        assert s["ready_to_write"] == [] and [f["scope"] for f in s["family_evidence"]] == ["family"]

    def test_refute_naming_only_the_sibling_does_not_promote_it(self, run_with):
        fake = Fake(findings=[_sprint(GT_DOC, "Transmission  6-speed constant mesh, return shift")],
                    model_line="ZZ Sprint 900 GT Owner's Manual")
        s = run_with(fake, ["Sprint 900"])
        assert s["ready_to_write"] == []

    def test_refute_cannot_promote_it_with_a_line_the_page_does_not_have(self, run_with):
        fake = Fake(findings=[_sprint(GT_DOC, "Transmission  6-speed constant mesh, return shift")],
                    model_line="ZZ Sprint 900 specifications")
        s = run_with(fake, ["Sprint 900"])
        assert s["ready_to_write"] == []

    def test_refute_confirms_a_model_the_text_rule_missed(self, run_with):
        """'ZZ Sprint 900' ends a line and the next begins 'S:' — the text
        rule reads 'Sprint 900 S'. Refute's line names the model and is on
        the page: the finding is written."""
        fake = Fake(findings=[_sprint(S_DOC, "Transmission  5-speed constant mesh, return shift")], model_line="ZZ Sprint 900")
        s = run_with(fake, ["Sprint 900"])
        assert [f["spelling"] for f in s["ready_to_write"]] == ["Sprint 900"]

    def test_a_page_naming_the_model_is_model_scope(self, run_with):
        s = run_with(Fake(findings=[_found()]), ["Trail 250"])
        assert s["ready_to_write"][0]["scope"] == "model" and s["family_evidence"] == []


def _call(mid, inputs, cache_read, out=100):
    """A streamed assistant message: one event per content block, each
    repeating the same usage (as `claude -p --output-format stream-json` does)."""
    u = {"input_tokens": 2, "output_tokens": out, "cache_read_input_tokens": cache_read,
         "cache_creation_input_tokens": 0}
    return [{"type": "assistant", "message": {"id": mid, "usage": u,
                                              "content": [{"type": "tool_use", "input": i}]}} for i in inputs] or \
           [{"type": "assistant", "message": {"id": mid, "usage": u, "content": [{"type": "thinking"}]}}]


class TestRefutePerFinding:
    """Refute's tokens and turns attributed per finding from its stream —
    the measurement behind the operator's rule: if the cost climbs across a
    batch, split refute into groups of at most 5, fresh contexts."""

    FINDINGS = [{"spelling": "GSX-R750", "document": "/lib/acquired/Suzuki/gsx-r750.html.txt"},
                {"spelling": "SV650", "document": "/lib/acquired/Suzuki/sv650-abs.html.txt"}]

    def test_calls_are_attributed_by_what_they_read(self):
        events = (_call("m1", [], 20_000)
                  + _call("m2", [{"file_path": "/lib/acquired/Suzuki/gsx-r750.html.txt"}], 25_000)
                  + _call("m3", [{"command": "grep -n six-speed x"}], 30_000)          # continues GSX-R750
                  + _call("m4", [{"file_path": "/lib/acquired/Suzuki/sv650-abs.html.txt"},
                                 {"command": "grep SV650"}], 40_000)                    # two blocks, one call
                  + _call("m5", [{"verdicts": [{"spelling": "GSX-R750"}, {"spelling": "SV650"}]}], 45_000))
        rows = {r["spelling"]: r for r in O.refute_attribution(events, self.FINDINGS)}
        assert [r["spelling"] for r in O.refute_attribution(events, self.FINDINGS)][:2] == ["GSX-R750", "SV650"]
        assert rows["(setup)"]["turns"] == 1
        assert rows["GSX-R750"]["turns"] == 2 and rows["GSX-R750"]["tokens"] == 25_102 + 30_102
        assert rows["SV650"]["turns"] == 1 and rows["SV650"]["tokens"] == 40_102, "a message's blocks are one call"
        assert rows["(answer)"]["turns"] == 1


class TestRefuteGroups:
    def test_groups_are_separate_fresh_calls(self, run_with, monkeypatch):
        monkeypatch.setattr(O, "REFUTE_GROUP", 1)
        fake = Fake(findings=[_found(), _sprint(S_DOC, "Transmission  5-speed constant mesh, return shift")],
                    model_line="ZZ Sprint 900")
        s = run_with(fake, ["Trail 250", "Sprint 900"])
        assert len(fake.refute_calls()) == 2
        assert all("--output-format" in c and c[c.index("--output-format") + 1] == "stream-json"
                   for c in fake.refute_calls())
        assert sorted(f["spelling"] for f in s["ready_to_write"]) == ["Sprint 900", "Trail 250"]
        assert {r["group"] for r in s["refute_per_finding"]} == {1, 2}

    def test_a_group_over_budget_stops_the_rest(self, run_with, monkeypatch):
        monkeypatch.setattr(O, "REFUTE_GROUP", 1)
        fake = Fake(findings=[_found(), _sprint(S_DOC, "Transmission  5-speed constant mesh, return shift")],
                    refute_usage=_usage(OPUS_MODEL, O.REFUTE_STOP_PER_FINDING + 1, 0))
        s = run_with(fake, ["Trail 250", "Sprint 900"])
        assert len(fake.refute_calls()) == 1, "after a group over budget, no further group runs"
        assert any(r.startswith("refute tokens") for r in s["stops"]) and s["ready_to_write"] == []


BLADE_DOC = str(LIB / "pdfs" / "zz_blade650abs_spec.txt")


def _blade():
    return {"make": "ZZ", "spelling": "Blade 650", "aliases": [], "outcome": "found", "transmission": "manual",
            "quote": "Transmission  6-speed, return shift",
            "document": BLADE_DOC, "page": 2, "evidence_kind": "maker_spec_page"}


class TestBugFix3RefuteMustSayTheModelIsNamed:
    """The SV650 ABS case (run Suzuki_20260923_093052), as a fixture: the
    page is the ABS variant and names the base model only historically
    ('the first … debuted in 1999'). The script's rule reads it as named;
    refute's reason said family evidence, but its verdict said 'kept' — and
    kept/killed could not say 'kept as family evidence', so ready_to_write
    trusted the label. Refute now answers names_model, and both must agree."""

    def test_the_sv650_abs_case_does_not_reach_ready_to_write(self, run_with):
        fake = Fake(findings=[_blade()], names_model=False)
        s = run_with(fake, ["Blade 650"])
        assert s["ready_to_write"] == []
        assert [f["spelling"] for f in s["family_evidence"]] == ["Blade 650"]

    def test_the_disagreement_is_a_stop(self, run_with):
        """D5: refute and the script disagree — the batch stops, it does not
        quietly pick one."""
        s = run_with(Fake(findings=[_blade()], names_model=False), ["Blade 650"])
        assert any("disagree" in r and "Blade 650" in r for r in s["stops"])

    def test_a_missing_names_model_is_not_a_yes(self, run_with):
        s = run_with(Fake(findings=[_blade()], names_model=None), ["Blade 650"])
        assert s["ready_to_write"] == []

    def test_both_saying_named_still_writes(self, run_with):
        s = run_with(Fake(findings=[_found()], names_model=True), ["Trail 250"])
        assert [f["spelling"] for f in s["ready_to_write"]] == ["Trail 250"] and s["stops"] == []

    def test_refute_saying_named_cannot_overrule_the_script(self, run_with):
        """The sibling page (Sprint 900 GT): refute says named, the script
        does not, and refute's line does not name the model."""
        fake = Fake(findings=[_sprint(GT_DOC, "Transmission  6-speed constant mesh, return shift")], names_model=True,
                    model_line="ZZ Sprint 900 GT Owner's Manual")
        s = run_with(fake, ["Sprint 900"])
        assert s["ready_to_write"] == []


class TestTheAbsEditionIsRecorded:
    def test_an_abs_edition_finding_carries_its_edition(self, run_with):
        """The Blade 650 ABS page, now under the exception: both refute and
        the script say it names the Blade 650, and the entry-to-be records
        that it came from the ABS edition."""
        s = run_with(Fake(findings=[_blade()], names_model=True), ["Blade 650"])
        [f] = s["ready_to_write"]
        assert f["edition"] == "ABS" and s["stops"] == []

    def test_a_plain_page_carries_no_edition(self, run_with):
        s = run_with(Fake(findings=[_found()]), ["Trail 250"])
        assert s["ready_to_write"][0]["edition"] is None


class TestBugFix4TheCitationIsRequired:
    """Run Suzuki_20260923_100443: the source stage returned a found SV650
    finding with no `document`; E1 stopped the batch. The schema the model
    answers to now requires the citation fields on every finding."""

    @pytest.mark.parametrize("field", ["transmission", "quote", "document", "page", "evidence_kind"])
    def test_the_schema_requires_it(self, field):
        assert field in O.FINDING["required"]

    def test_a_null_citation_is_allowed_for_no_evidence(self):
        for field in ("quote", "document", "page", "evidence_kind"):
            assert "null" in O.FINDING["properties"][field]["type"], field

    def test_the_schema_the_source_call_carries_is_this_one(self, run_with):
        fake = Fake(findings=[_found()])
        run_with(fake, ["Trail 250"])
        cmd = fake.source_calls()[0]
        sent = json.loads(cmd[cmd.index("--json-schema") + 1])
        assert "document" in sent["properties"]["findings"]["items"]["required"]
