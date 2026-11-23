"""The server's checks on an uploaded manual, before it is stored (K119).

``check_pdf`` returns every reason a file is refused, and nothing when it
passes: a real PDF by its bytes; not locked by a password; carrying no
scripts, attachments, launch actions or embedded media anywhere in its
object tree (the walk follows indirect objects, so it reads inside object
streams, which a byte search would miss); and able to open, render page 1
and give up its text layer through ``pypdfium2``. A scan with no text layer
passes: its text is empty, and search will not find it.

Both PDF libraries are imported inside the functions that use them, as
``pillow-heif`` is; when either is missing every file is refused with "the
server cannot read PDFs", never let through.
"""

from __future__ import annotations

from pathlib import Path

PDF_MAGIC = b"%PDF-"
CANNOT_READ = "the server cannot read PDFs"
NOT_A_PDF = "the file is not a PDF"
LOCKED = "the file is locked with a password"
UNREADABLE = "the file could not be opened as a PDF"
UNRENDERABLE = "the file could not be rendered"
NO_PAGES = "the file has no pages"

_JS = "the file carries JavaScript"
#: A name anywhere in the tree, as a key or as a value (an action's /S),
#: and the reason it gives.
FORBIDDEN_NAMES = {
    "/JavaScript": _JS, "/JS": _JS,
    "/Launch": "the file carries a launch action",
    "/EmbeddedFile": "the file carries an attachment",
    "/EmbeddedFiles": "the file carries an attachment",
    "/RichMedia": "the file carries embedded media",
}


def _forbidden_in_tree(reader) -> list[str]:
    """The reasons found walking every object reachable from the trailer."""
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject

    found: set[str] = set()
    seen: set[tuple[int, int]] = set()
    stack: list = [reader.trailer]
    while stack:
        obj = stack.pop()
        if isinstance(obj, IndirectObject):
            ref = (obj.idnum, obj.generation)
            if ref in seen:
                continue
            seen.add(ref)
            stack.append(obj.get_object())
        elif isinstance(obj, DictionaryObject):
            for key, value in obj.items():
                if key in FORBIDDEN_NAMES:
                    found.add(FORBIDDEN_NAMES[key])
                stack.append(value)
        elif isinstance(obj, ArrayObject):
            stack.extend(obj)
        elif isinstance(obj, NameObject) and obj in FORBIDDEN_NAMES:
            found.add(FORBIDDEN_NAMES[obj])
    return sorted(found)


def _structure_reasons(path: Path) -> list[str]:
    """pypdf's reading: locked, or carrying something active."""
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(""):
            return [LOCKED]
        return _forbidden_in_tree(reader)
    except (PyPdfError, ValueError, KeyError, TypeError, OSError):
        return [UNREADABLE]


def _render_reasons(path: Path) -> list[str]:
    """pypdfium2's reading: it opens, has pages, renders page 1 and reads its text."""
    import pypdfium2 as pdfium

    try:
        doc = pdfium.PdfDocument(str(path))
    except pdfium.PdfiumError:
        return [UNRENDERABLE]
    try:
        if len(doc) == 0:
            return [NO_PAGES]
        page = doc[0]
        page.render(scale=0.25).to_pil()
        page.get_textpage().get_text_bounded()
        return []
    except pdfium.PdfiumError:
        return [UNRENDERABLE]
    finally:
        doc.close()


def check_pdf(path: str | Path) -> list[str]:
    """Every reason the file is refused; empty when it passes."""
    path = Path(path)
    with open(path, "rb") as fin:
        if fin.read(len(PDF_MAGIC)) != PDF_MAGIC:
            return [NOT_A_PDF]
    try:
        import pypdf  # noqa: F401
        import pypdfium2  # noqa: F401
    except ImportError:
        return [CANNOT_READ]
    reasons = _structure_reasons(path)
    if reasons:
        return reasons
    return _render_reasons(path)


def page_count(path: str | Path) -> int:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(path))
    try:
        return len(doc)
    finally:
        doc.close()
