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
TRAIL_QUOTE = "Transmission  5-speed constant mesh, return type"
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

    def __init__(self, findings=(), turns=2, verdict="kept", source_usage=None, refute_usage=None):
        self.calls: list[list[str]] = []
        self.findings, self.turns, self.verdict = list(findings), turns, verdict
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
                        "page": f["page"], "reason": "fake refute"} for f in findings]},
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
        assert "5-speed constant mesh" in excerpts["Trail 250"][0]["text"]
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
        fake = Fake(findings=[_found(document=planted, quote="Transmission 5-speed constant mesh, return type")])
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

    def test_refute_counts_toward_the_same_budget(self, run_with):
        fake = Fake(findings=[_found()], source_usage=_usage(SUBC_MODEL, 100_000, 0),
                    refute_usage=_usage(OPUS_MODEL, 60_000, 0))
        s = run_with(fake, ["Trail 250"])
        assert len(fake.refute_calls()) == 1
        assert any("per spelling" in r for r in s["stops"]) and s["ready_to_write"] == []

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
