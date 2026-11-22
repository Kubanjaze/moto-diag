"""Draw getmekno.com's two images, and clean the founder's photo (Phase 408).

    python scripts/site_images.py brand            # site/og.png and site/logo.png
    python scripts/site_images.py photo IN.jpg     # site/founder.jpg, pixels only

Pillow is not one of the project's dependencies: this is run by hand, once
per change, from an environment that has it (`pip install Pillow`), and the
images it writes are committed. Phase 408 drew them with Pillow 11.3.0 and
the Inter Bold font (`/usr/share/fonts/opentype/inter/Inter-Bold.otf`; pass
another path with MEKNO_FONT).

`og.png` (1200x630) is the link preview: the logo mark from `favicon.svg`
and the name, with no product claim. `logo.png` (512x512) is the mark alone,
for the Organization data. `photo` re-encodes the pixels only: no Exif, no
location, no camera, no colour profile, no comment, turned upright first
and at most 800 pixels on its long side. `tests/test_phase408_site.py`
reads every image's bytes and fails on any metadata.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
FONT = os.environ.get("MEKNO_FONT", "/usr/share/fonts/opentype/inter/Inter-Bold.otf")

ACCENT = (232, 89, 12)      # #e8590c, the mark's colour in favicon.svg
BG = (247, 246, 243)        # #f7f6f3, the site's --bg
INK = (22, 24, 29)          # #16181d, the site's --ink
WHITE = (255, 255, 255)

#: favicon.svg's M, in its 64x64 box: M14 46V20l9 0 9 13 9-13 9 0v26h-8V31l-10 14-10-14v15z
M_PATH = [(14, 46), (14, 20), (23, 20), (32, 33), (41, 20), (50, 20), (50, 46), (42, 46),
          (42, 31), (32, 45), (22, 31), (22, 46)]


def mark(size: int) -> Image.Image:
    """The logo mark, drawn at 4x and scaled down for smooth edges."""
    big = size * 4
    s = big / 64
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, big - 1, big - 1], radius=round(16 * s), fill=ACCENT)
    d.polygon([(x * s, y * s) for x, y in M_PATH], fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


def save_png(img: Image.Image, path: Path) -> None:
    img.convert("RGB").save(path, format="PNG", optimize=True)
    print(f"wrote {path.relative_to(ROOT)}")


def brand() -> None:
    og = Image.new("RGB", (1200, 630), BG)
    m = mark(260)
    font = ImageFont.truetype(FONT, 190)
    d = ImageDraw.Draw(og)
    word = "mekno"
    left, top, right, bottom = d.textbbox((0, 0), word, font=font)
    gap = 56
    total = m.width + gap + (right - left)
    x = (og.width - total) // 2
    og.paste(m, (x, (og.height - m.height) // 2), m)
    tx = x + m.width + gap - left
    ty = (og.height - (bottom - top)) // 2 - top
    d.text((tx, ty), word, font=font, fill=INK)
    save_png(og, SITE / "og.png")

    logo = Image.new("RGB", (512, 512), WHITE)
    lm = mark(512)
    logo.paste(lm, (0, 0), lm)
    save_png(logo, SITE / "logo.png")


def photo(source: Path) -> None:
    with Image.open(source) as raw:
        img = ImageOps.exif_transpose(raw).convert("RGB")
    img.thumbnail((800, 800), Image.LANCZOS)
    clean = Image.new("RGB", img.size)
    clean.putdata(list(img.getdata()))
    out = SITE / "founder.jpg"
    clean.save(out, format="JPEG", quality=85, optimize=True, progressive=False)
    print(f"wrote {out.relative_to(ROOT)} ({clean.width}x{clean.height})")


def main(argv: list[str]) -> int:
    if argv == ["brand"]:
        brand()
        return 0
    if len(argv) == 2 and argv[0] == "photo":
        photo(Path(argv[1]))
        return 0
    print("\n".join(__doc__.strip().splitlines()[2:4]), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
