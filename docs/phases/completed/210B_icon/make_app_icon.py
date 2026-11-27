"""The app's icon, redrawn from the website's mark (site/favicon.svg).

The mark is a 64 x 64 drawing: an orange square (#e8590c) with a white M
whose outline is straight lines only. This draws the same M at 1024 x 1024
from its own coordinates, so nothing is enlarged from pixels and the edges
stay sharp. The square fills the whole picture (no rounded corners: the
phone rounds them itself) and the picture has no transparency, which Apple
requires of an app icon.

Usage: python make_app_icon.py OUT.png
"""
from __future__ import annotations

import sys

from PIL import Image, ImageDraw

ORANGE = (0xE8, 0x59, 0x0C)
WHITE = (0xFF, 0xFF, 0xFF)
SIZE = 1024
SUPERSAMPLE = 4  # drawn at 4096 and reduced, for smooth diagonal edges

# site/favicon.svg's path, "M14 46V20l9 0 9 13 9-13 9 0v26h-8V31l-10 14-10-14v15z",
# as absolute points in its 64 x 64 view box.
M_OUTLINE = [
    (14, 46), (14, 20), (23, 20), (32, 33), (41, 20), (50, 20),
    (50, 46), (42, 46), (42, 31), (32, 45), (22, 31), (22, 46),
]


def draw(size: int = SIZE) -> Image.Image:
    big = size * SUPERSAMPLE
    scale = big / 64
    img = Image.new("RGB", (big, big), ORANGE)
    ImageDraw.Draw(img).polygon([(x * scale, y * scale) for x, y in M_OUTLINE], fill=WHITE)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: make_app_icon.py OUT.png")
    icon = draw()
    assert icon.size == (SIZE, SIZE) and icon.mode == "RGB"
    icon.save(sys.argv[1], format="PNG", optimize=True)
    print(f"wrote {sys.argv[1]}: {icon.size[0]} x {icon.size[1]}, {icon.mode}, no transparency")
