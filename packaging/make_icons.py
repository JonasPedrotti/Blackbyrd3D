"""Writes the build icons from the marks in blackbyrd3d/ui/brand.py, so the
installers wear the logo the app draws. From the repository root:

    .venv/Scripts/python packaging/make_icons.py
"""

from __future__ import annotations

import io
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PIL import Image  # noqa: E402
from PySide6.QtCore import QBuffer  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _image(px: int, mark: str = "app") -> Image.Image:
    from blackbyrd3d.ui.brand import icon_pixmap
    from blackbyrd3d.ui.icons import wyrm_icon
    pixmap = icon_pixmap(px) if mark == "app" else wyrm_icon().pixmap(px, px)
    buf = QBuffer()
    buf.open(QBuffer.OpenModeFlag.WriteOnly)
    pixmap.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


def main():
    _app = QGuiApplication(sys.argv)
    here = os.path.dirname(os.path.abspath(__file__))
    for name, mark in (("byrd3d.ico", "app"), ("wyrm.ico", "wyrm")):
        frames = [_image(px, mark) for px in ICO_SIZES]
        frames[-1].save(os.path.join(here, "windows", name), format="ICO",
                        sizes=[(px, px) for px in ICO_SIZES],
                        append_images=frames[:-1])
    _image(256).save(os.path.join(here, "appimage", "blackbyrd3d.png"))
    _image(256, "wyrm").save(os.path.join(here, "appimage", "wyrm.png"))
    _image(1024).save(os.path.join(here, "macos", "byrd3d_icon.png"))
    _image(1024, "wyrm").save(os.path.join(here, "macos", "wyrm_icon.png"))
    print("icons written")


if __name__ == "__main__":
    main()
