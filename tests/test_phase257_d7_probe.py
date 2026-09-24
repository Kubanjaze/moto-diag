"""Phase 257 — d7_probe.classify: the rule that turns one response into a method.

Hand-written responses, one per method, each shaped on a real one from the
2026-09-23 run (`~/.cache/motodiag/d7/20260923_002937/d7.json`). No network.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "source-transmission"))

from d7_probe import classify  # noqa: E402

SPEC_TEXT = "Super 8 50X Specifications Engine 49.5cc Transmission CVT Automatic " + "x " * 800
LINKS_HTML = b'<html><body>' + b"Owner's manuals " * 200 + b'<a href="/files/om.pdf">OM</a></body></html>'


@pytest.mark.parametrize("status,body,error,final,text,method", [
    (None, b"", "URLError: CERTIFICATE_VERIFY_FAILED", "https://energica/", None, "unreachable"),
    (522, b"<html>origin down" + b" x" * 900, None, "https://damon.com/", None, "unreachable"),
    (302, b"<html>moved</html>", None, "https://kawasaki/owner-center", None, "redirect_loop"),
    (403, b"<html>Access Denied</html>", None, "https://ducati/", None, "blocked"),
    (200, b"<html><title>Just a moment...</title></html>", None, "https://x/", None, "blocked"),
    (404, b"<html>gone</html>", None, "https://x/", None, "not_found"),
    (200, b"<html>" + b" y" * 900, None, "https://suzukicycles.com/404?item=gsx", None, "not_found"),
    (200, b"%PDF-1.6 ...", None, "https://genuine/Buddy125.pdf", None, "document_endpoint"),
    (200, b"<html>spec</html>", None, "https://kymcousa.com/scooters/super-8-50x/", SPEC_TEXT, "spec_page_html"),
    (200, LINKS_HTML, None, "https://maker/manuals", None, "document_links"),
    (200, b"<html><div id=app></div></html>", None, "https://manuals.bmw-motorrad.com/", "", "needs_browser"),
    (200, b"<html>about</html>", None, "https://ktm/manuals", "About us " * 400, "html_no_evidence"),
])
def test_the_method(status, body, error, final, text, method):
    assert classify(status, body, error, final, text)[0] == method


def test_a_transmission_word_without_a_gearbox_is_not_a_spec_page():
    """'Transmission' as a menu word (a service department) is not a spec line."""
    text = "Service Transmission repair specialists near you " + "z " * 900
    assert classify(200, b"<html></html>", None, "https://dealer/", text)[0] != "spec_page_html"


ZERO_RSC = (b'<html><script>self.__next_f.push([1,"{\\"fields\\":[{\\"entry_id\\":[],'
            b'\\"entry_label\\":\\"Transmission\\",\\"entry_tooltip\\":\\"\\",'
            b'\\"model_type_option_1_value\\":\\"Clutchless direct drive\\"}]}"])</script>'
            + b"<div>" + b"Zero SR/S " * 300 + b"</div></html>")


class TestTheTwoRecordedRules:
    """Round 2's two misses: Honda motopub's JSON answers and Zero's spec
    table embedded as JSON in the page. Both shaped on the real bodies."""

    def test_a_json_answer_is_a_json_endpoint(self):
        assert classify(200, b'["CB1000RA","CBR1000RR-RA-S1-S2"]', None, "https://www.hondamotopub.com/ajax/x", None)[0] \
            == "json_endpoint"

    def test_an_embedded_spec_table_is_found(self):
        method, info = classify(200, ZERO_RSC, None, "https://www.zeromotorcycles.com/model/zero-srs", None)
        assert method == "spec_embedded_json"
        assert info["transmission_line"] == "Transmission: Clutchless direct drive"

    def test_an_embedded_label_that_is_not_a_gearbox_is_not_a_spec(self):
        body = ZERO_RSC.replace(b"Transmission", b"Seat height")
        assert classify(200, body, None, "https://z/", None)[0] != "spec_embedded_json"
