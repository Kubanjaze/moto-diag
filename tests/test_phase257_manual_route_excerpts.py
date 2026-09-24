"""Phase 257 — a manual-route owner's manual is read whole, and named by its list record.

Operator decision, 2026-09-23, after the Yamaha dry run sent 8 spellings on
contents-page lines and missed Vino 125, the positive control: its manual
prints only "YJ125Y". Three parts, each pinned here:

1. Excerpts: a PDF a manual route (`acquire.MANUAL_ROUTES`) fetched for a
   spelling is tied to it by its sidecar's `for_spellings`, and cut around
   its mechanism lines anywhere in the text (`anchor: "route"`).
2. Contents lines are not evidence: a dot leader or a trailing page
   reference ("6-16 Clutch lever ......", "Clutch lever......... 4-9") is
   neither an anchor nor a dry-run line.
3. Identity: `names_model` takes its model line from the hash-pinned list
   record ("dispModelName": "VINO 125 - YJ125Y" beside this PDF's
   pdffileURL), exact matches only, and the code becomes an alias.

Fixture manuals are real, minimal PDFs, so `acquire.save`, `derive_text`
and E11 run as they do on the library. The real-file controls skip on a
machine without the library.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "source-transmission"
sys.path.insert(0, str(SKILL))

import acquire as A  # noqa: E402
import orchestrate as O  # noqa: E402
from candidates import candidates  # noqa: E402
from entry_check import check_one, list_identity, mechanism_lines, model_scope, toc_line  # noqa: E402

API = A.YAMAHA_OM_API + "model_list/"
PDF_URL = "https://library.ymcapps.net/library/om/contents/pdf/10/5YR-F8199-15_02.pdf"
# The Vino 125 manual's own lines (5YR-F8199-15): it never prints "Vino 125".
VINO_LINES = ["Congratulations on your purchase of the Yamaha YJ125Y.", *["Keep this manual with the scooter."] * 50,
              "Clutch", "Clutch type", "Dry, centrifugal automatic", "Transmission",
              "Transmission type", "V-belt automatic", "Operation", "Centrifugal automatic type"]
# Only contents lines name a clutch or a pedal (the MT-09's 6-16, the XT250's 4-9).
TOC_LINES = ["Yamaha MT-09 Owner's Manual", "TABLE OF CONTENTS", "6-16 Clutch lever ....................",
             "Clutch lever......... 4-9", "Shift pedal (page 5-29)", *["Riding tips."] * 50]
SHIFT_LINE = "To shift the transmission to a higher gear, move the shift pedal up."

REAL = pathlib.Path.home() / "research" / "motodiag"
REAL_YAMAHA = REAL / "acquired" / "Yamaha"
VINO_TXT = REAL_YAMAHA / "library_om_contents_pdf_10_5YR-F8199-15_02.pdf.txt"
R1_SPELLING = "YZF-R1"
real = pytest.mark.skipif(not VINO_TXT.is_file(), reason="needs the on-disk library")


def text_pdf(lines: list[str]) -> bytes:
    """A one-page PDF whose text layer pypdf extracts line for line."""
    esc = lambda s: s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")  # noqa: E731
    body = "BT /F1 10 Tf 12 TL 40 800 Td " + " ".join(f"({esc(x)}) Tj T*" for x in lines) + " ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
            "/Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(body)} >>\nstream\n{body}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for n, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{n} 0 obj\n{o}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    return out + f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


def plant(lib: pathlib.Path, lines: list[str], for_spellings: list[str], *, disp: str = "VINO 125 - YJ125Y",
          pdf_url: str = PDF_URL, listed_url: str | None = None, make: str = "Yamaha") -> pathlib.Path:
    """What yamaha_om_route saves: the model_list record, then the PDF with
    it as referrer. Returns the PDF's derived text."""
    record = {"modelDataCollection": [{"modelYear": "2009", "dispModelName": disp, "publicationNo": "5YR-F8199-15",
                                       "pdffileURL": listed_url or pdf_url[len("https:"):], "publicationLangId": "02"}]}
    lrow = {"url": API, "final_url": API, "status": 200, "body": json.dumps(record).encode(),
            "method": "json_endpoint", "fetched_at": "t"}
    ref = A.save(make, lrow, referrer=None, for_spellings=for_spellings, library=lib)
    drow = {"url": pdf_url, "final_url": pdf_url, "status": 200, "body": text_pdf(lines),
            "method": "document_endpoint", "fetched_at": "t"}
    saved = A.save(make, drow, referrer=ref, for_spellings=for_spellings, library=lib)
    txt = lib / (saved["path"] + ".txt")
    assert txt.is_file(), "the fixture PDF must derive text, or nothing below is tested"
    return txt


@pytest.fixture
def lib(tmp_path):
    return tmp_path / "library"


class TestTableOfContentsLines:
    @pytest.mark.parametrize("line", ["6-16 Clutch lever ....................", "Clutch lever......... 4-9",
                                      "Shift pedal (page 5-29)", "4-6 Shift pedal......................................."])
    def test_a_contents_line_is_one(self, line):
        assert toc_line(line)

    @pytest.mark.parametrize("line", [SHIFT_LINE, "Dry, centrifugal automatic", "V-belt automatic",
                                      "0.7-0.8 mm (0.028-0.031 in)", "Transmission  5-speed constant mesh, return shift"])
    def test_a_text_line_is_not(self, line):
        assert not toc_line(line)

    def test_a_contents_line_is_not_a_dry_run_line(self):
        assert mechanism_lines([{"text": "\n".join(TOC_LINES[2:5])}]) == []

    def test_control_the_same_excerpt_with_the_operation_line_is(self):
        assert mechanism_lines([{"text": "\n".join([*TOC_LINES[2:5], SHIFT_LINE])}]) == [SHIFT_LINE]


# KTM's own lines (bug fix #7): its contents shapes, and a sentence the PDF
# wraps so that a line ends in a range (23_3214761, 1290 Super Duke R).
KTM_TOC = ["6.1 Clutch lever..................................... 16", "Clutch lever. . . . . . . . . . . . . . . 16",
           "6.1 Clutch lever .................................... 21", "hydraulic clutch............................ 117"]
KTM_WRAPPED = ["Press and", "hold theSET", "button for 3-5", "seconds."]
KTM_CLUTCH_WRAPPED = ["Pull the clutch lever and shift", "into first gear. Wait for 2-3", "seconds."]


class TestKTMContentsLines:
    @pytest.mark.parametrize("line", KTM_TOC)
    def test_ktm_contents_lines_are_contents_lines(self, line):
        assert toc_line(line)

    @pytest.mark.parametrize("line", ["button for 3-5", "into first gear. Wait for 2-3", "tighten to 8-10",
                                      "between 1-2", "approx. 2-3", "or equipment damage. See page 5-1",
                                      "self-diagnosis system. (See page 4-8"])
    def test_a_range_in_a_wrapped_sentence_is_not(self, line):
        assert not toc_line(line)

    @pytest.mark.parametrize("line", ["6. Shift pedal (page 6-31)", "1. Spring preload adjuster (page 5-29)",
                                      "Shift pedal page 6-31", "Replacing the tail/brake light bulb6-26",
                                      "LOCATION OF IMPORTANT LABELS1-1"])
    def test_control_a_callout_page_reference_still_is(self, line):
        assert toc_line(line)

    def test_a_wrapped_operation_line_is_still_a_dry_run_line(self):
        got = mechanism_lines([{"text": "\n".join([*KTM_TOC, *KTM_CLUTCH_WRAPPED])}])
        assert got == ["Pull the clutch lever and shift into first gear."]

    @pytest.mark.skipif(not (REAL / "acquired" / "KTM").is_dir(), reason="needs the on-disk library")
    def test_on_every_real_ktm_manual_only_dot_leader_lines_and_headings_are_dropped(self):
        """Every line of the 26 real KTM texts the filter drops has a dot
        leader, or is a heading or label (no sentence ends on it): measured
        2026-09-23, 4 such lines before the fix, 2 after."""
        texts = sorted((REAL / "acquired" / "KTM").glob("*.pdf.txt"))
        assert len(texts) >= 26
        dot_leader = re.compile(r"(?:\.\s?){4,}|…{2,}")
        other = [ln for t in texts for ln in t.read_text(encoding="utf-8").splitlines()
                 if toc_line(ln) and not dot_leader.search(ln)]
        assert sorted(other) == ["7.23.27 Favourites indicator 1-4", "FCC ID: T8VCL9-904"]


class TestAManualRoutePdfIsReadWhole:
    def test_the_manual_is_excerpted_at_its_spec_rows_without_naming_the_spelling(self, lib):
        plant(lib, VINO_LINES, ["Vino 125"])
        [e] = candidates(["Vino 125"], lib, make="Yamaha")["Vino 125"]
        assert e["anchor"] == "route" and "V-belt automatic" in e["text"]
        assert mechanism_lines([e])

    def test_control_the_same_manual_fetched_for_another_spelling_gives_none(self, lib):
        plant(lib, VINO_LINES, ["Vino 50"])
        assert candidates(["Vino 125"], lib, make="Yamaha")["Vino 125"] == []

    def test_control_a_make_without_a_manual_route_gives_none(self, lib):
        plant(lib, [*VINO_LINES, "Kymco"], ["Vino 125"], make="Kymco")
        assert candidates(["Vino 125"], lib, make="Kymco")["Vino 125"] == []

    def test_a_manual_whose_only_hits_are_contents_lines_sends_nothing(self, lib):
        plant(lib, TOC_LINES, ["MT-09"])
        ex = candidates(["MT-09"], lib, make="Yamaha")["MT-09"]
        assert ex, "the name-anchored contents page is found, or this tests the no-excerpt path"
        assert not any(e["anchor"] == "route" for e in ex) and mechanism_lines(ex) == []

    def test_control_the_same_manual_with_the_operation_line_is_sent(self, lib):
        plant(lib, [*TOC_LINES, SHIFT_LINE], ["MT-09"])
        ex = candidates(["MT-09"], lib, make="Yamaha")["MT-09"]
        assert any(e["anchor"] == "route" for e in ex) and SHIFT_LINE in mechanism_lines(ex)


class TestTheListRecordNamesTheModel:
    def test_an_exact_match_gives_the_model_line_and_the_code(self, lib):
        txt = plant(lib, VINO_LINES, ["Vino 125"])
        ident = list_identity(txt, lib, "Yamaha", "Vino 125")
        assert ident["model_line"] == "VINO 125 - YJ125Y" and ident["code"] == "YJ125Y"
        assert ident["publication"] == "5YR-F8199-15" and ident["record"].startswith("acquired/Yamaha/")
        assert list_identity(lib / ident["record"], lib, "Yamaha", "Vino 125") is None   # the record is not the manual
        assert model_scope({"make": "Yamaha", "spelling": "Vino 125", "document": str(txt)}, lib, lib) == "model"

    @pytest.mark.parametrize("spelling, disp", [("T100", "BONNEVILLE T100 - 3850782"), ("Vino", "VINO 125 - YJ125Y")])
    def test_a_partial_match_does_not_pass(self, lib, spelling, disp):
        txt = plant(lib, VINO_LINES, [spelling], disp=disp)
        assert list_identity(txt, lib, "Yamaha", spelling) is None
        assert model_scope({"make": "Yamaha", "spelling": spelling, "document": str(txt)}, lib, lib) == "family"

    def test_a_changed_record_does_not_pass(self, lib):
        txt = plant(lib, VINO_LINES, ["Vino 125"])
        record = lib / list_identity(txt, lib, "Yamaha", "Vino 125")["record"]
        record.write_bytes(record.read_bytes().replace(b"YJ125Y", b"YJ125X"))
        assert list_identity(txt, lib, "Yamaha", "Vino 125") is None

    def test_a_record_listing_another_pdf_does_not_pass(self, lib):
        txt = plant(lib, VINO_LINES, ["Vino 125"], listed_url="//library.ymcapps.net/library/om/contents/pdf/10/OTHER_02.pdf")
        assert list_identity(txt, lib, "Yamaha", "Vino 125") is None

    def test_a_pdf_not_fetched_for_the_spelling_does_not_pass(self, lib):
        txt = plant(lib, VINO_LINES, ["Vino 50"])
        assert list_identity(txt, lib, "Yamaha", "Vino 125") is None


def _verdict_fake(findings: list[dict]):
    """subprocess.run for batch(): the anthropic source route returns
    `findings`; refute keeps each with names_model true."""
    calls: list[list[str]] = []

    def run(cmd, **kw):
        calls.append(cmd)
        prompt = cmd[cmd.index("-p") + 1]
        if prompt.startswith("You are the SOURCE stage"):
            out = {"structured_output": {"findings": findings}}
            model = O.ROUTES["anthropic"]["model"]
        else:
            got = json.loads(prompt.split("Findings:\n", 1)[1])
            out = {"structured_output": {"verdicts": [
                {"spelling": f["spelling"], "verdict": "kept", "quote": f["quote"], "page": f["page"],
                 "model_line": (f.get("identity") or {}).get("model_line", ""), "names_model": True,
                 "reason": "fake refute"} for f in got]}}
            model = O.ROUTES[O.REFUTE_ROUTE]["model"]
        out.update({"type": "result", "is_error": False, "num_turns": 2, "modelUsage": {
            model: {"inputTokens": 1000, "outputTokens": 100, "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0}}})
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(out) + "\n", stderr="")
    run.calls = calls
    return run


# The YZF-R6 manual (BN6-28199-13) prints only its model-year codes.
R6_LINES = ["YZFR6L/YZFR6LC", *["Keep this manual with the motorcycle."] * 50, SHIFT_LINE]
R6_URL = "https://library.ymcapps.net/library/om/contents/pdf/10/BN6-28199-13_02.pdf"


class TestE4AcceptsTheListRecord:
    """Operator, 2026-09-23: E4's "the document never names the machine"
    accepts the pinned list record naming the model exactly. No year-letter
    parsing: "YZFR1M" is the R1M, never the YZF-R1."""

    @staticmethod
    def _e4(lib, txt, spelling):
        f = {"make": "Yamaha", "spelling": spelling, "aliases": [], "outcome": "found", "transmission": "manual",
             "quote": SHIFT_LINE, "document": str(txt), "page": 1, "evidence_kind": "owners_manual"}
        return [x for x in check_one(f, lib, library=lib) if x.startswith("E4")]

    def test_a_code_only_manual_is_named_by_its_record(self, lib):
        txt = plant(lib, R6_LINES, ["YZF-R6"], disp="YZF-R6 - YZF600", pdf_url=R6_URL)
        assert self._e4(lib, txt, "YZF-R6") == []

    def test_control_the_same_manual_without_its_record_is_not(self, lib):
        txt = plant(lib, R6_LINES, ["YZF-R6"], disp="YZF-R6 - YZF600", pdf_url=R6_URL)
        record = lib / list_identity(txt, lib, "Yamaha", "YZF-R6")["record"]
        record.write_bytes(record.read_bytes() + b" ")           # the pin no longer holds
        assert self._e4(lib, txt, "YZF-R6") == ["E4 Yamaha | YZF-R6: the document never names the machine"]

    def test_the_r1m_record_does_not_name_the_r1(self, lib):
        txt = plant(lib, ["YZFR1M", *R6_LINES[1:]], ["YZF-R1"], disp="YZF-R1M - YZF1000D",
                    pdf_url=R6_URL.replace("BN6", "B67"))
        assert self._e4(lib, txt, "YZF-R1") == ["E4 Yamaha | YZF-R1: the document never names the machine"]

    def test_a_weak_spelling_is_named_as_a_model_by_its_record(self, lib):
        """"XT 660" is weak and in no lookup entry: the manual prints it, but
        not after the make, in its title or its file name. Since Vino 125 was
        written, its YJ125Y alias names it without the record, so this is the
        case that still reaches the record. Control: the pin broken."""
        lines = [*R6_LINES[1:4], "Ride your XT 660 carefully.", *R6_LINES[4:]]
        txt = plant(lib, lines, ["XT 660"], disp="XT 660 - XT660Z", pdf_url=R6_URL.replace("BN6", "10S"))
        assert self._e4(lib, txt, "XT 660") == []
        record = lib / list_identity(txt, lib, "Yamaha", "XT 660")["record"]
        record.write_bytes(record.read_bytes() + b" ")
        assert [x[:20] for x in self._e4(lib, txt, "XT 660")] == ["E4 Yamaha | XT 660: "]

    def test_a_record_for_another_spelling_does_not_name_this_one(self, lib):
        txt = plant(lib, R6_LINES, ["YZF-R7"], disp="YZF-R6 - YZF600", pdf_url=R6_URL)
        assert self._e4(lib, txt, "YZF-R7") == ["E4 Yamaha | YZF-R7: the document never names the machine"]


class TestTheBatchCarriesTheIdentity:
    """The integration point: batch() attaches the list record's identity and
    its code as an alias before entry_check, and hands it to refute."""

    @pytest.fixture
    def go(self, tmp_path, monkeypatch, lib):
        def make_run(root, make):
            run = tmp_path / "run"
            for d in ("clone", "tmp/cfg"):
                (run / d).mkdir(parents=True, exist_ok=True)
            return {"run": run, "clone": run / "clone", "tmp": run / "tmp", "profile": run / "sandbox.sb"}
        monkeypatch.setattr(O, "make_run", make_run)
        monkeypatch.setattr(O, "LIBRARY", lib)
        monkeypatch.setattr(O, "alert", lambda *a: None)
        monkeypatch.setattr(O, "load_anthropic_token", lambda *a: "sk-ant-oat01-" + "x" * 40)

        def run(finding_for):
            txt = plant(lib, VINO_LINES, ["Vino 125"])
            fake = _verdict_fake([finding_for(txt)])
            monkeypatch.setattr(O.subprocess, "run", fake)
            return O.batch("Yamaha", ["Vino 125"], source_route="anthropic"), fake
        return run

    @staticmethod
    def _found(txt):
        return {"make": "Yamaha", "spelling": "Vino 125", "aliases": [], "outcome": "found",
                "transmission": "cvt", "quote": "Transmission type V-belt automatic", "document": str(txt),
                "page": 1, "evidence_kind": "owners_manual"}

    def test_vino_125_is_ready_to_write_with_its_code_as_an_alias(self, go):
        s, fake = go(self._found)
        assert s["sent_to_model"] == ["Vino 125"] and s["rejections"] == [], s["rejections"]
        [f] = s["ready_to_write"]
        assert f["identity"]["model_line"] == "VINO 125 - YJ125Y" and f["aliases"] == ["YJ125Y"]
        assert f["scope"] == "model"
        refute_prompt = fake.calls[-1][fake.calls[-1].index("-p") + 1]
        assert '"model_line": "VINO 125 - YJ125Y"' in refute_prompt

    def test_the_prompts_say_how_to_read_a_route_excerpt_and_an_identity(self):
        assert 'anchor "route"' in O.SOURCE_PROMPT and "prints only a model code" in O.SOURCE_PROMPT
        assert "A finding carrying `identity`" in O.REFUTE_PROMPT and "identity.model_line" in O.REFUTE_PROMPT

    def test_control_without_the_identity_the_manual_never_names_the_machine(self, go, lib):
        def found(txt):
            record = lib / list_identity(txt, lib, "Yamaha", "Vino 125")["record"]
            record.write_bytes(record.read_bytes() + b" ")       # the pin no longer holds
            return self._found(txt)
        s, _ = go(found)
        assert s["ready_to_write"] == []
        assert any(x.startswith("E4 Yamaha | Vino 125") for x in s["rejections"]), s["rejections"]


@real
class TestOnTheRealLibrary:
    """Controls on the real files (operator): Vino 125 is sent with its V-belt
    automatic spec rows and names_model passes through its list record;
    YZF-R1's "move the shift pedal up" line is still sent."""

    @pytest.fixture(scope="class")
    def real_cands(self):
        return candidates(["Vino 125", R1_SPELLING], REAL, make="Yamaha")     # one pass: ~100 s

    def test_vino_125_is_sent_with_its_spec_rows(self, real_cands):
        ex = real_cands["Vino 125"]
        lines = mechanism_lines(ex)
        assert any("V-belt automatic" in e["text"] and e["anchor"] == "route" for e in ex)
        assert any("Transmission type V-belt automatic" in x for x in lines)

    def test_vino_125_names_its_model_through_the_list_record(self):
        ident = list_identity(VINO_TXT, REAL, "Yamaha", "Vino 125")
        assert ident["model_line"] == "VINO 125 - YJ125Y" and ident["code"] == "YJ125Y"
        assert ident["sha256"] == "805a1811cfcea2a73008982bd5776022ce10a1c4b5eb01f54bcd2a2bd2ec8ef9"
        assert model_scope({"make": "Yamaha", "spelling": "Vino 125", "document": str(VINO_TXT)}, REAL, REAL) == "model"

    def test_yzf_r1s_shift_line_is_still_sent(self, real_cands):
        assert SHIFT_LINE in mechanism_lines(real_cands[R1_SPELLING])

    def test_a_partial_spelling_does_not_pass_through_the_real_record(self, tmp_path):
        """The real Vino 125 files, copied with the sidecars saying they were
        fetched for "Vino": the record's name is VINO 125, so no identity.
        Control in the same copy: fetched for "Vino 125", it passes."""
        pdf = VINO_TXT.with_suffix("")
        side = json.loads(pdf.with_name(pdf.name + ".acquired.json").read_text())
        record = REAL / side["referrer"]["path"]
        dst = tmp_path / "acquired" / "Yamaha"
        dst.mkdir(parents=True)
        for p in (pdf, VINO_TXT, record):
            shutil.copy(p, dst / p.name)
        for spelling, expect in (("Vino", None), ("Vino 125", "VINO 125 - YJ125Y")):
            for p in (pdf, VINO_TXT):
                s = json.loads(p.with_name(p.name + ".acquired.json").read_text())
                s["for_spellings"] = [spelling]
                (dst / (p.name + ".acquired.json")).write_text(json.dumps(s))
            got = list_identity(dst / VINO_TXT.name, tmp_path, "Yamaha", spelling)
            assert (got or {}).get("model_line") == expect, spelling
