"""Draws the installer's wizard images from the app's own marks.

    python make_wizard_images.py [out_dir]

The tall image beside the Welcome and Finished pages is the splash in
portrait, on the popup grey so it runs into the page: the bird in its crescent over the wordmark. The small one in the
corner of every other page is the mark alone. Each comes in the sizes Inno
Setup picks from per DPI, so neither is ever scaled up.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor, QGuiApplication, QImage, QPainter,
)

from blackbyrd3d.ui import brand  # noqa: E402
from blackbyrd3d.ui.splash import paint_mark, paint_wordmark  # noqa: E402

# the title bar grey of the wizard's dark style, which installer.iss sets
# behind every page too, so window and page are one colour
CARD = QColor("#2b2b2b")

# The image area's heights at 100% to 250% DPI with WizardSizePercent's
# height at 100, each as wide as the area is at the 120 Inno Setup's modern
# style defaults to: installer.iss widens the area to match, so the bird
# keeps its size in a lower window.
RATIO = (202, 314)
LARGE = [(round(h * RATIO[0] / RATIO[1]), h)
         for h in (314, 386, 459, 556, 604, 700, 797)]
SMALL = [58, 77, 97, 116, 124, 143, 159]

HERE = Path(__file__).resolve().parent


def _canvas(w: int, h: int) -> tuple[QImage, QPainter]:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return img, p


def large(w: int, h: int) -> QImage:
    img, p = _canvas(w, h)
    p.fillRect(0, 0, w, h, CARD)

    mark = w * 0.78
    ww, wh = brand.WORDMARK_SIZE
    word_w = w * 0.70
    word_h = word_w * wh / ww
    top = (h - (mark * 1.02 + word_h)) / 2
    paint_mark(p, (w - mark) / 2, top, mark)
    paint_wordmark(p, (w - word_w) / 2, top + mark * 1.02, word_h)

    p.end()
    return img


def small(px: int) -> QImage:
    img, p = _canvas(px, px)
    inset = px * 0.16
    paint_mark(p, inset, inset, px - 2 * inset)
    p.end()
    return img


def main(out: Path) -> list[Path]:
    QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for w, h in LARGE:
        path = out / f"wizard-{w}x{h}.png"
        large(w, h).save(str(path))
        written.append(path)
    for px in SMALL:
        path = out / f"wizard-small-{px}.png"
        small(px).save(str(path))
        written.append(path)
    return written


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "wizard"
    for path in main(target):
        print(path.name)
