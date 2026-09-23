"""Phase 257 — acquire.py, with no network.

A fake transport answers from hand-written pages shaped on the real ones
measured in D7 (phase log, 2026-09-23), so the real routes, matching,
saving, sidecars, derived text and E11 all run; only the wire is absent.
Pinned: every saved file passes E11 as saved and fails it when touched;
the cap stops a run; robots.txt is honoured; a 403 is recorded, not
retried; a weak spelling never takes the nearest name; the inbox ingests
exactly the convention in INBOX_README and rejects each departure from it.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "source-transmission"))

import acquire as A  # noqa: E402
from candidates import candidates  # noqa: E402
from entry_check import acquired_provenance  # noqa: E402

KYMCO_LIST = (b'<html><a href="https://kymcousa.com/scooters/super-8-50x/">Super 8 50X</a>'
              b'<a href="https://kymcousa.com/scooters/x-town-300i/">X-Town 300i</a>'
              b'<a href="https://kymcousa.com/scooters/agility-50/">Agility 50</a></html>')
KYMCO_SPEC = (b"<html><title>KYMCO Super 8 50X Specifications</title><body>KYMCO Super 8 50X"
              b"<table><tr><td>Engine</td><td>49.5cc</td></tr><tr><td>Transmission</td><td>CVT Automatic</td></tr>"
              b"</table>" + b"<p>ride</p>" * 400 + b"</body></html>")
ZERO_HOME = (b'<html><a href="/model/zero-srs">SR/S <span>New</span></a>'
             b'<a href="/model/zero-sr">SR</a><a href="/model/zero-dsrx">DSR/X New</a></html>')
ZERO_SRS = (b'<html><title>Zero SR/S</title><script>self.__next_f.push([1,"{\\"entry_label\\":\\"Transmission\\",'
            b'\\"entry_tooltip\\":\\"\\",\\"model_type_option_1_value\\":\\"Clutchless direct drive\\"}"])</script>'
            + b"<div>Zero Motorcycles SR/S</div>" * 60 + b"</html>")
PDF = b"%PDF-1.4\n% not a real PDF body, derive_text returns None for it\n"


def site(pages: dict[str, tuple[int, bytes]]):
    """A transport: url -> (status, body, error, final_url). robots.txt 404s unless given."""
    calls: list[str] = []

    def transport(url, headers):
        calls.append(url)
        status, body = pages.get(url, (404, b"<html>not found</html>"))
        return status, body, None, url
    transport.calls = calls
    return transport


@pytest.fixture
def lib(tmp_path):
    return tmp_path / "library"


def _kymco(lib, transport, cap=30, spellings=("Super 8-50 X",)):
    f = A.Fetcher(cap=cap, rate=0, transport=transport)
    return A.fetch("Kymco", fetcher=f, library=lib, spellings=list(spellings)), f


class TestASpecRoute:
    PAGES = {"https://kymcousa.com/scooters/": (200, KYMCO_LIST),
             "https://kymcousa.com/scooters/super-8-50x/": (200, KYMCO_SPEC)}

    def test_the_spec_page_is_saved_with_its_provenance(self, lib):
        r, _ = _kymco(lib, site(self.PAGES))
        assert list(r["matched"]) == ["Super 8-50 X"]
        path = lib / r["matched"]["Super 8-50 X"]["path"]
        side = json.loads(path.with_name(path.name + ".acquired.json").read_text())
        assert side["url"] == "https://kymcousa.com/scooters/super-8-50x/"
        assert side["supplied_by"] == "acquire.py" and side["for_spellings"] == ["Super 8-50 X"]
        assert side["referrer"]["url"] == "https://kymcousa.com/scooters/"

    def test_what_it_saves_passes_e11_and_candidates_reads_the_derived_text(self, lib):
        r, _ = _kymco(lib, site(self.PAGES))
        path = lib / r["matched"]["Super 8-50 X"]["path"]
        derived = path.with_name(path.name + ".txt")
        assert acquired_provenance(path, lib, "Kymco", "t") == []
        assert acquired_provenance(derived, lib, "Kymco", "t") == []
        ex = candidates(["Super 8 50X"], lib, make="Kymco")["Super 8 50X"]
        assert ex and all(e["document"].endswith(".txt") for e in ex)
        assert any("CVT Automatic" in e["text"] for e in ex)

    def test_a_touched_derived_text_fails_e11(self, lib):
        r, _ = _kymco(lib, site(self.PAGES))
        path = lib / r["matched"]["Super 8-50 X"]["path"]
        derived = path.with_name(path.name + ".txt")
        derived.write_text(derived.read_text().replace("CVT Automatic", "6-speed manual"))
        assert any("no longer hashes" in x for x in acquired_provenance(derived, lib, "Kymco", "t"))

    def test_a_forged_derived_text_with_a_matching_sidecar_fails_e11(self, lib):
        """Text and sidecar hash rewritten together: every hash agrees, and
        only re-deriving from the maker's bytes shows it is not theirs."""
        import hashlib
        r, _ = _kymco(lib, site(self.PAGES))
        path = lib / r["matched"]["Super 8-50 X"]["path"]
        derived = path.with_name(path.name + ".txt")
        forged = derived.read_text().replace("CVT Automatic", "6-speed manual")
        derived.write_text(forged)
        side = derived.with_name(derived.name + ".acquired.json")
        s = json.loads(side.read_text())
        s["sha256"] = hashlib.sha256(forged.encode("utf-8")).hexdigest()
        side.write_text(json.dumps(s))
        assert any("is not what" in x for x in acquired_provenance(derived, lib, "Kymco", "t"))

    def test_a_spelling_no_page_names_is_reported_not_guessed(self, lib):
        r, _ = _kymco(lib, site(self.PAGES), spellings=("People S 150i",))
        assert r["unmatched"] == ["People S 150i"] and r["matched"] == {}

    def test_a_second_run_does_not_fetch_what_it_has(self, lib):
        t = site(self.PAGES)
        _kymco(lib, t)
        before = len(t.calls)
        r, _ = _kymco(lib, t)
        assert r["asked"] == [] and len(t.calls) == before + 0


class TestEmbeddedJsonSpecs:
    def test_zero_s_spec_table_reaches_the_derived_text(self, lib):
        t = site({"https://www.zeromotorcycles.com/": (200, ZERO_HOME),
                  "https://www.zeromotorcycles.com/model/zero-srs": (200, ZERO_SRS)})
        r = A.fetch("Zero", fetcher=A.Fetcher(rate=0, transport=t), library=lib, spellings=["SR/S"])
        assert r["matched"]["SR/S"]["method"] == "spec_embedded_json"
        path = lib / r["matched"]["SR/S"]["path"]
        text = path.with_name(path.name + ".txt").read_text()
        assert "Transmission: Clutchless direct drive" in text


class TestTheDiscipline:
    def test_the_cap_stops_the_run(self, lib):
        pages = {**TestASpecRoute.PAGES,
                 "https://kymcousa.com/scooters/x-town-300i/": (200, KYMCO_SPEC)}
        r, f = _kymco(lib, site(pages), cap=2, spellings=("Super 8-50 X", "X-Town 300i"))
        assert r["stopped"].startswith("cap reached") and f.count == 2
        assert len(r["log"]) == f.count, "every request the cap counts is in the run record"

    def test_robots_txt_is_honoured(self, lib):
        pages = {**TestASpecRoute.PAGES,
                 "https://kymcousa.com/robots.txt": (200, b"User-agent: *\nDisallow: /scooters/super-8-50x/\n")}
        t = site(pages)
        r, _ = _kymco(lib, t)
        assert "https://kymcousa.com/scooters/super-8-50x/" not in t.calls
        assert r["failed"]["Super 8-50 X"]["method"] == "robots_disallowed"

    def test_a_403_is_recorded_once_and_nothing_saved(self, lib):
        t = site({"https://kymcousa.com/scooters/": (200, KYMCO_LIST),
                  "https://kymcousa.com/scooters/super-8-50x/": (403, b"<html>Access Denied</html>")})
        r, _ = _kymco(lib, t)
        assert r["failed"]["Super 8-50 X"]["method"] == "blocked"
        assert t.calls.count("https://kymcousa.com/scooters/super-8-50x/") == 1
        assert not list((lib / "acquired" / "Kymco").glob("*super-8-50x*"))

    @pytest.mark.parametrize("spelling,expected", [
        ("CB", None),                                    # weak: never the nearest CB
        ("Super 8-50 X", "super 8 50x"), ("X-Town 300i", "x town 300i"),
    ])
    def test_matching(self, spelling, expected):
        names = {"CB500F": "a", "CB650R": "b", "super 8 50x": "super 8 50x", "x town 300i": "x town 300i"}
        assert A.match(spelling, names) == expected


class TestTheInbox:
    PAGE = (b'<html><title>Owner Manuals | Ducati</title>'
            b'<a href="/content/dam/manuals/Panigale V4 OM.pdf">Panigale V4</a></html>')

    def _drop(self, lib, *, url_text=None, page=True, make="Ducati", pdf=b"%PDF-1.4 hand-downloaded\n"):
        d = lib / "inbox" / make
        d.mkdir(parents=True)
        (d / "panigale-v4-om.pdf").write_bytes(pdf)
        (d / "panigale-v4-om.pdf.url").write_text(url_text if url_text is not None else
            "document: https://www.ducati.com/content/dam/manuals/Panigale V4 OM.pdf\n"
            "page: https://www.ducati.com/us/en/owners/owner-manuals\n")
        if page:
            (d / "panigale-v4-om.pdf.page.html").write_bytes(self.PAGE)

    def test_the_convention_is_ingested_and_passes_e11(self, lib):
        self._drop(lib)
        r = A.ingest(lib)
        assert r == {"ingested": ["Ducati/panigale-v4-om.pdf"], "rejected": {}}
        doc = next((lib / "acquired" / "Ducati").glob("*.pdf"))
        side = json.loads(doc.with_name(doc.name + ".acquired.json").read_text())
        assert side["supplied_by"] == "operator"
        assert side["referrer"]["url"] == "https://www.ducati.com/us/en/owners/owner-manuals"
        assert acquired_provenance(doc, lib, "Ducati", "t") == []
        assert (lib / "inbox" / "Ducati" / "panigale-v4-om.pdf").is_file(), "the inbox is read-only"

    @pytest.mark.parametrize("kw,why", [
        ({"page": False}, "needs"),
        ({"url_text": "https://www.ducati.com/x.pdf\n"}, "'document:' line"),
        ({"url_text": "document: https://www.ducati.com/content/dam/manuals/Panigale V4 OM.pdf\n"
                      "page: https://www.ducati-forum.example/manuals\n"}, "not on a Ducati host"),
        ({"url_text": "document: https://www.ducati.com/content/dam/manuals/Monster OM.pdf\n"
                      "page: https://www.ducati.com/us/en/owners/owner-manuals\n"}, "does not link"),
        ({"make": "Ducatti"}, "not a make"),
    ])
    def test_each_departure_is_rejected_with_its_reason(self, lib, kw, why):
        self._drop(lib, **kw)
        r = A.ingest(lib)
        assert r["ingested"] == [] and why in next(iter(r["rejected"].values()))


class TestOperatorDecisions:
    """2026-09-23: dedupe by content hash; never inside the repo; a
    'contains' match is recorded as such (the 4609 rule)."""

    def test_identical_bytes_are_stored_once_with_both_spellings(self, lib):
        pages = {"https://kymcousa.com/scooters/": (200, KYMCO_LIST),
                 "https://kymcousa.com/scooters/super-8-50x/": (200, KYMCO_SPEC),
                 "https://kymcousa.com/scooters/x-town-300i/": (200, KYMCO_SPEC)}
        r, _ = _kymco(lib, site(pages), spellings=("Super 8-50 X", "X-Town 300i"))
        assert r["matched"]["Super 8-50 X"]["path"] == r["matched"]["X-Town 300i"]["path"]
        path = lib / r["matched"]["X-Town 300i"]["path"]
        side = json.loads(path.with_name(path.name + ".acquired.json").read_text())
        assert side["for_spellings"] == ["Super 8-50 X", "X-Town 300i"]
        assert len(list((lib / "acquired" / "Kymco").glob("*super-8-50x*.html"))) == 1

    def test_a_refetched_referrer_never_overwrites_the_copy_others_pin(self, lib):
        """The Wolf 150 shape: a Dropbox-hosted manual counts only through
        SYM's page, pinned by sha. The page is fetched again later with new
        bytes — the pinned copy must survive, or the manual loses its proof."""
        page_url = "https://sym-usa.com/maintenance-guides/"
        doc_url = "https://www.dropbox.com/s/x/Wolf150 Owner Manual.pdf?dl=0"
        page = f'<html><a href="{doc_url}">Wolf 150</a></html>'.encode()
        row = lambda url, body: {"url": url, "final_url": url, "status": 200, "body": body,  # noqa: E731
                                 "method": "document_links", "fetched_at": "t"}
        ref = A.save("SYM", row(page_url, page), referrer=None, for_spellings=[], library=lib)
        doc = A.save("SYM", dict(row(doc_url, b"SYM WOLF 150 manual\n"), method="document_endpoint"),
                     referrer=ref, for_spellings=["Wolf 150"], library=lib)
        A.save("SYM", row(page_url, page + b"<!-- rebuilt -->"), referrer=None, for_spellings=[], library=lib)
        assert acquired_provenance(lib / doc["path"], lib, "SYM", "t") == []

    def test_a_library_inside_the_repo_is_refused(self):
        with pytest.raises(RuntimeError, match="inside the repository"):
            A.fetch("Kymco", library=A.C.REPO / "data" / "library", spellings=["x"])

    def test_the_match_kind_is_in_the_sidecar(self, lib):
        """A strong spelling ('X-Town 300i') takes a longer name; recorded as
        'contains'. (A weak one, 'Super 8-50 X', never does.)"""
        names_page = (b'<html><a href="https://kymcousa.com/scooters/x-town-300i-gt/">X-Town 300i GT</a></html>')
        t = site({"https://kymcousa.com/scooters/": (200, names_page),
                  "https://kymcousa.com/scooters/x-town-300i-gt/": (200, KYMCO_SPEC)})
        r, _ = _kymco(lib, t, spellings=("X-Town 300i",))
        m = r["matched"]["X-Town 300i"]
        assert m["match"] == {"name": "X-Town 300i GT", "kind": "contains"}
        path = lib / m["path"]
        side = json.loads(path.with_name(path.name + ".acquired.json").read_text())
        assert side["matches"]["X-Town 300i"]["kind"] == "contains"


class TestTheAbsYearPage:
    """Kawasaki's 2026 Z900 exists only as '2026-z900-abs' and
    '2026-z900-se-abs' (measured). The base model's page wins; failing it,
    the '-abs' edition; never the SE, Carbon or KRT editions."""

    FAMILY = "https://www.kawasaki.com/en-us/motorcycle/z/supernaked/z900"

    def _hop(self, lib, links):
        body = "".join(f'<a href="/en-us/motorcycle/z/supernaked/z900/{l}">x</a>' for l in links).encode()
        f = A.Fetcher(rate=0, transport=site({self.FAMILY: (200, body)}))
        url, _ = A._newest_year_page(f, "Kawasaki", self.FAMILY, lib)
        return url and url.rsplit("/", 1)[-1]

    def test_the_abs_edition_when_it_is_the_only_one(self, lib):
        assert self._hop(lib, ["2026-z900-se-abs", "2026-z900-abs", "build-your-kawasaki"]) == "2026-z900-abs"

    def test_the_base_model_page_wins(self, lib):
        assert self._hop(lib, ["2026-z900-abs", "2025-z900"]) == "2025-z900"

    def test_special_editions_never_qualify(self, lib):
        assert self._hop(lib, ["2026-z900-se-abs", "2026-z900-carbon-abs", "2026-z900-krt-edition"]) is None


class TestBMWIndex:
    """BMW's rider-manual index, in the live file's own shape: attributes
    separated by CRLF (the first live run matched 0 of 39 because the parser
    expected single spaces, as in D7's copy)."""

    NAV = ('<NAV-MODELL\r\nMARKT="EUR"\r\nTYPSCHL="0K51"\r\nT-BEZ="F 800 GS"\r\n><NAME\r\n>F 800 GS</NAME\r\n>'
           '<MODELLJAHR\r\n><NAME\r\n>08.2024 onward</NAME\r\n><BA-SPRACHE\r\nLANGUAGE="00"\r\n'
           'FILENAME="F_0K51_RM_0724_00.pdf"/><BA-SPRACHE\r\nLANGUAGE="01"\r\nFILENAME="F_0K51_RM_0724_01.pdf"/>'
           '</MODELLJAHR\r\n></NAV-MODELL\r\n>').encode()
    BASE = "https://manuals.bmw-motorrad.com/manuals/BA-Extern/IN/BA-INTERNET-COM"

    def test_the_crlf_index_yields_the_english_pdf(self, lib):
        t = site({self.BASE + "/01/Nav.xml": (200, self.NAV),
                  self.BASE + "/PDF/F_0K51_RM_0724_01.pdf": (200, b"%PDF-1.4 F 800 GS rider's manual\n")})
        r = A.fetch("BMW", fetcher=A.Fetcher(rate=0, transport=t), library=lib, spellings=["F800GS"])
        assert r["matched"]["F800GS"]["url"].endswith("F_0K51_RM_0724_01.pdf")
        assert r["matched"]["F800GS"]["match"] == {"name": "F 800 GS", "kind": "exact"}

    def test_the_riders_manual_not_the_certificate(self, lib):
        nav = ('<NAV-MODELL\r\nT-BEZ="F 750 GS"\r\n><MODELLJAHR\r\n><BA-SPRACHE\r\nLANGUAGE="01"\r\n'
               'FILENAME="F_0B11_RM_0321_01.pdf"/></MODELLJAHR\r\n><MODELLJAHR\r\n><BA-SPRACHE\r\nLANGUAGE="01"\r\n'
               'FILENAME="01408405040_ZBA_Zertifikate_01.pdf"/></MODELLJAHR\r\n></NAV-MODELL\r\n>').encode()
        t = site({self.BASE + "/01/Nav.xml": (200, nav),
                  self.BASE + "/PDF/F_0B11_RM_0321_01.pdf": (200, b"%PDF-1.4 F 750 GS rider's manual\n"),
                  self.BASE + "/PDF/01408405040_ZBA_Zertifikate_01.pdf": (200, b"%PDF-1.4 certificates\n")})
        r = A.fetch("BMW", fetcher=A.Fetcher(rate=0, transport=t), library=lib, spellings=["F 750 GS"])
        assert r["matched"]["F 750 GS"]["url"].endswith("F_0B11_RM_0321_01.pdf")


class TestAPostIsRecordedSoItCanBeRepeated:
    """Operator, 2026-09-23: Yamaha's Owner's Manual Library lists manuals by
    JSON POST. The fetcher sends it, and the sidecar records the method,
    headers and body, so the list can be fetched again from its record."""

    API = "https://parts.example-maker.test/omb2c/model_list/"
    BODY = {"productId": "10", "modelYear": "2009", "publicationLang": "02"}
    LIST = b'{"modelDataCollection": [{"pdffileURL": "//library.example.test/om/x.pdf"}]}'

    def _post_site(self):
        sent: list[tuple] = []

        def transport(url, headers, data=None):
            sent.append((url, dict(headers), data))
            if url.endswith("/robots.txt"):
                return 404, b"", None, url
            if data is not None and json.loads(data) == self.BODY:
                return 200, self.LIST, None, url
            return 400, b'{"error": "bad request"}', None, url
        transport.sent = sent
        return transport

    def test_the_body_is_sent_as_json(self):
        t = self._post_site()
        row = A.Fetcher(rate=0, transport=t).post_json(self.API, self.BODY, {"Origin": "https://library.example.test"})
        assert row["status"] == 200 and row["body"] == self.LIST
        url, headers, data = t.sent[-1]
        assert json.loads(data) == self.BODY and headers["Content-Type"] == "application/json"
        assert row["request"] == {"method": "POST", "body": self.BODY,
                                  "headers": {"Content-Type": "application/json", "Origin": "https://library.example.test"}}

    def test_the_sidecar_records_the_request_and_repeats_it(self, lib):
        t = self._post_site()
        f = A.Fetcher(rate=0, transport=t)
        saved = A.save("Yamaha", f.post_json(self.API, self.BODY), referrer=None, for_spellings=["Vino 125"], library=lib)
        side = json.loads((lib / (saved["path"] + ".acquired.json")).read_text())
        assert side["request"]["method"] == "POST" and side["request"]["body"] == self.BODY
        again = A.Fetcher(rate=0, transport=t).post_json(side["url"], side["request"]["body"], side["request"]["headers"])
        assert hashlib.sha256(again["body"]).hexdigest() == side["sha256"]

    def test_a_get_records_get(self, lib):
        t = site({"https://www.ktm.com/manual.pdf": (200, PDF)})
        saved = A.save("KTM", A.Fetcher(rate=0, transport=t).get("https://www.ktm.com/manual.pdf"),
                       referrer=None, for_spellings=["390 Duke"], library=lib)
        side = json.loads((lib / (saved["path"] + ".acquired.json")).read_text())
        assert side["request"] == {"method": "GET", "headers": {}, "body": None}

    def test_robots_still_gates_a_post(self):
        def transport(url, headers, data=None):
            if url.endswith("/robots.txt"):
                return 200, b"User-agent: *\nDisallow: /omb2c/\n", None, url
            raise AssertionError("a disallowed POST was sent")
        row = A.Fetcher(rate=0, transport=transport).post_json(self.API, self.BODY)
        assert row["method"] == "robots_disallowed" and row["request"]["method"] == "POST"


class TestYamahaOwnersManualRoute:
    """Yamaha's Owner's Manual Library (phase log, 2026-09-23), in the real
    responses' shapes (~/.cache/motodiag/om_probe/Yamaha_20260923_181033):
    POSTs for the user context, the names, the years and the newest year's
    model list; the English PDF on library.ymcapps.net, its referrer the
    saved model list."""

    API = A.YAMAHA_OM_API
    PRODUCTS = json.dumps({"userContext": {"destination": "USA", "useProdCategory": False, "userGroupCode": "AL01",
                                           "destGroupCode": "", "greyModelSign": False},
                           "productDataCollection": [{"productId": "10"}]}).encode()
    NAMES = {"1": [{"nickname": "VINO 125", "modelName": "", "productId": "10", "dispModelName": "VINO 125"},
                   {"nickname": "ZUMA 50", "modelName": "", "productId": "10", "dispModelName": "ZUMA 50"}],
             "9": [{"nickname": "", "modelName": "MT-09", "productId": "10", "dispModelName": "MT-09"}]}
    YEARS = {"VINO 125": ["2009", "2005", "2004"], "MT-09": ["2021", "2019", "2023"]}
    PUBS = {("VINO 125", "2009"): [{"publicationNo": "5YR-F8199-15", "publicationLangId": "02",
                                    "pdffileURL": "//library.ymcapps.net/library/om/contents/pdf/10/5YR-F8199-15_02.pdf"}],
            ("MT-09", "2023"): [{"publicationNo": "B7N-F8199-E0", "publicationLangId": "01",
                                 "pdffileURL": "//library.ymcapps.net/library/om/contents/pdf/10/B7N-F8199-E0_01.pdf"},
                                {"publicationNo": "B7N-F8199-10", "publicationLangId": "02",
                                 "pdffileURL": "//library.ymcapps.net/library/om/contents/pdf/10/B7N-F8199-10_02.pdf"}]}

    def _api(self, pdf_status=200):
        calls: list[tuple] = []

        def transport(url, headers, data=None):
            body = json.loads(data) if data else None
            calls.append((url, body))
            if url.endswith("/robots.txt"):
                return 404, b"", None, url
            if url.endswith("/product_list/"):
                return 200, self.PRODUCTS, None, url
            if url.endswith("/model_name_list/"):
                return 200, json.dumps({"modelNameDataCollection": self.NAMES.get(body["displacementType"], [])}).encode(), None, url
            key = body and (body["nickname"] or body["modelName"])
            if url.endswith("/model_year_list/"):
                assert body["destination"] == "USA" and body["userGroupCode"] == "AL01"
                ys = [{"modelYear": y, "productId": "10"} for y in self.YEARS.get(key, [])]
                return 200, json.dumps({"modelYearDataCollection": ys}).encode(), None, url
            if url.endswith("/model_list/"):
                assert body["publicationLang"] == "02" and body["calledCode"] == "1"
                pubs = self.PUBS.get((key, body["modelYear"]), [])
                return 200, json.dumps({"modelDataCollection": pubs}).encode(), None, url
            if url.startswith("https://library.ymcapps.net/") and url.endswith(".pdf"):
                return pdf_status, (b"%PDF-1.4 " + url.encode() + b"\n") if pdf_status == 200 else b"", None, url
            return 404, b"not found", None, url
        transport.calls = calls
        return transport

    def _fetch(self, lib, t, spellings, cap=30):
        f = A.Fetcher(cap=cap, rate=0, transport=t)
        return A.fetch("Yamaha", fetcher=f, library=lib, spellings=list(spellings)), f

    def test_the_route_is_the_owners_manual_library(self):
        assert A.ROUTES["Yamaha"] is A.yamaha_om_route and "Yamaha" in A.MANUAL_ROUTES

    def test_the_english_pdf_of_the_newest_year_passes_e11(self, lib):
        t = self._api()
        r, _ = self._fetch(lib, t, ["MT-09"])
        m = r["matched"]["MT-09"]
        assert m["year"] == "2023" and m["publication"] == "B7N-F8199-10"
        assert m["url"] == "https://library.ymcapps.net/library/om/contents/pdf/10/B7N-F8199-10_02.pdf"
        assert m["match"] == {"name": "MT-09", "kind": "exact"}
        pdf = lib / m["path"]
        side = json.loads(pdf.with_name(pdf.name + ".acquired.json").read_text())
        assert side["referrer"]["url"] == self.API + "model_list/"
        listed = json.loads((lib / side["referrer"]["path"]).read_bytes())
        assert listed["modelDataCollection"][1]["pdffileURL"].endswith("B7N-F8199-10_02.pdf")
        assert acquired_provenance(pdf, lib, "Yamaha", "t") == []

    def test_the_model_list_request_is_recorded(self, lib):
        r, _ = self._fetch(lib, self._api(), ["Vino 125"])
        pdf = lib / r["matched"]["Vino 125"]["path"]
        ref = json.loads(pdf.with_name(pdf.name + ".acquired.json").read_text())["referrer"]
        side = json.loads((lib / (ref["path"] + ".acquired.json")).read_text())
        assert side["request"]["method"] == "POST"
        assert side["request"]["body"]["nickname"] == "VINO 125" and side["request"]["body"]["modelYear"] == "2009"
        assert side["request"]["headers"]["Referer"] == A.YAMAHA_OM_PORTAL

    def test_a_weak_spelling_takes_no_nearest_name(self, lib):
        t = self._api()
        r, _ = self._fetch(lib, t, ["Zuma"])
        assert r["unmatched"] == ["Zuma"] and r["matched"] == {}
        assert not any(u.endswith("/model_year_list/") for u, _ in t.calls)

    def test_a_spec_page_does_not_make_a_spelling_done_but_a_pdf_does(self, lib):
        spec = {"url": "https://www.yamahamotorsports.com/models/mt-09/specs",
                "final_url": "https://www.yamahamotorsports.com/models/mt-09/specs", "status": 200,
                "body": b"<html>MT-09 specs</html>", "method": "spec_page_html", "fetched_at": "t"}
        A.save("Yamaha", spec, referrer=None, for_spellings=["MT-09"], library=lib)
        t = self._api()
        r, _ = self._fetch(lib, t, ["MT-09"])
        assert "MT-09" in r["matched"]
        before = len(t.calls)
        r2, _ = self._fetch(lib, t, ["MT-09"])
        assert r2["asked"] == [] and len(t.calls) == before

    def test_a_list_response_does_not_make_a_spelling_done(self, lib):
        t = self._api(pdf_status=403)
        r, _ = self._fetch(lib, t, ["Vino 125"])
        assert r["failed"]["Vino 125"]["method"] == "blocked"
        r2, _ = self._fetch(lib, self._api(), ["Vino 125"])
        assert "Vino 125" in r2["matched"]

    def test_the_cap_keeps_what_was_saved_and_names_the_rest(self, lib):
        # robots + product_list + 10 name lists = 12; + robots(library) + 3 for Vino 125 = 16
        r, f = self._fetch(lib, self._api(), ["Vino 125", "MT-09"], cap=17)
        assert r["stopped"].startswith("cap reached") and f.count == 17
        assert list(r["matched"]) == ["Vino 125"] and r["not_reached"] == ["MT-09"]
        assert "MT-09" not in r["match"]
        r2, _ = self._fetch(lib, self._api(), ["Vino 125", "MT-09"])
        assert r2["asked"] == ["MT-09"] and list(r2["matched"]) == ["MT-09"]

    def test_a_contains_match_is_reported_not_fetched(self, lib):
        """The 4609 rule: a longer name is a sibling or variant. Control: the
        same spelling with its exact name listed is fetched."""
        self.NAMES = {**self.NAMES, "8": [{"nickname": "", "modelName": "YZF-R1M", "productId": "10",
                                            "dispModelName": "YZF-R1M"}]}
        t = self._api()
        r, _ = self._fetch(lib, t, ["YZF-R1"])
        assert r["match"]["YZF-R1"] == {"name": "YZF-R1M", "kind": "contains"}
        assert r["failed"]["YZF-R1"]["method"] == "contains_match_not_fetched" and r["matched"] == {}
        assert not any(u.endswith("/model_year_list/") for u, _ in t.calls)
        self.YEARS, self.PUBS = {**self.YEARS, "YZF-R1": ["2024"]}, {**self.PUBS, ("YZF-R1", "2024"): [
            {"publicationNo": "BX4-F8199-10", "publicationLangId": "02",
             "pdffileURL": "//library.ymcapps.net/library/om/contents/pdf/10/BX4-F8199-10_02.pdf"}]}
        self.NAMES = {**self.NAMES, "8": [{"nickname": "", "modelName": "YZF-R1", "productId": "10", "dispModelName": "YZF-R1"}]}
        r2, _ = self._fetch(lib, self._api(), ["YZF-R1"])
        assert r2["matched"]["YZF-R1"]["publication"] == "BX4-F8199-10"
