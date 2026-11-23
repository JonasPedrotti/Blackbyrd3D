"""The About box.

An About box gets opened for one of two reasons: somebody wants to know
what this program is, or somebody is filing a bug and needs to say which
build they are on and what it is standing on. The first is a sentence and
it never changes; the second is a table, and the version, the kernel and
the Qt build in it are exactly the facts a reporter cannot be expected to
dig out by hand — so they are on the box, and one button puts the lot on
the clipboard in the shape an issue wants them.
"""

from __future__ import annotations

import platform
import sys

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)

from . import theme
from .card_dialog import STYLE as CARD_STYLE, CardDialog
from .splash import splash_mark_pixmap, wordmark_pixmap
from .welcome import _BASELINE, _DOCS, _GITHUB

_BLURB = ("An open-source NURBS modeller for Rhino users and 3D CAD "
          "designers: surfaces, solids and drawing sheets, on Linux, "
          "Windows and macOS.")
_AUTHOR = "Made by Jonas Pedrotti."
_NAME_STORY = "Built on Serpentine3D by Chisomo Banzi."

_QSS = f"""
QLabel#ver, QLabel#section, QLabel#key {{ color: #8d8e93; }}
QLabel#section {{ font-family: monospace; letter-spacing: 1.5px; }}
QLabel#blurb {{ color: #cfcfd2; font-size: 13px; }}
QLabel#author {{ color: #ececee; font-size: 13px; font-weight: 600; }}
QLabel#val {{ color: #e6e6e8; font-family: monospace; font-size: 12px; }}
QFrame#build {{ background: #27282c; border: 1px solid #3d3e44;
               border-radius: 8px; }}
QLabel#link {{ color: {theme.ACCENT}; }}
"""


def _kernel_version() -> str:
    """OCCT arrives as a wheel, so its own headers are not around to ask —
    the wheel's version is the honest answer and the one a bug report can
    be matched against."""
    try:
        from importlib.metadata import version
        return version("cadquery-ocp")
    except Exception:                                      # noqa: BLE001
        return "unknown"


def build_rows() -> list[tuple[str, str]]:
    """What this build is, and what it is standing on."""
    from PySide6 import __version__ as pyside_version
    from PySide6.QtCore import qVersion

    from .. import __version__
    host = (f"{platform.system()} {platform.release()} "
            f"({platform.machine()})")
    return [
        ("Blackbyrd3D", __version__),
        ("Python", platform.python_version()),
        ("Qt", f"{qVersion()} (PySide6 {pyside_version})"),
        ("OpenCASCADE", _kernel_version()),
        ("Platform", host),
    ]


class AboutDialog(CardDialog):
    """The app's own popup card, like the others: no title bar, a cross in
    its corner, centred on the window."""

    def __init__(self, window: QWidget | None = None):
        super().__init__(window, "", title="About Blackbyrd3D")
        from .. import __version__
        self._version = __version__
        self._rows = build_rows()
        self.setObjectName("about")
        if sys.platform.startswith("linux"):
            # GNOME glues a dialog-type window to its parent
            # (ui/dialogs.untether)
            self.setWindowFlags(Qt.WindowType.Window
                                | Qt.WindowType.FramelessWindowHint)
        self.heading.hide()
        self._build()
        # after the build: set before it, the labels kept the app's look
        self.setStyleSheet(CARD_STYLE + _QSS)
        # Fixed both ways: a window manager stretched a box only fixed in
        # width to the height of its own layout.
        self.setFixedWidth(540)
        self.setFixedHeight(self.heightForWidth(540))

    # ---------------------------------------------------------------- text
    def summary_text(self) -> str:
        """What the box says in prose, as one string."""
        return "\n".join([f"Blackbyrd3D v{self._version} · MIT licence",
                          _BLURB, _AUTHOR, _NAME_STORY])

    def details_text(self) -> str:
        """The table, in the shape an issue wants it pasted."""
        width = max(len(k) for k, _ in self._rows)
        return "\n".join(f"{k.ljust(width)}  {v}" for k, v in self._rows)

    def link_urls(self) -> list[str]:
        return [_DOCS, _GITHUB]

    def copy_details(self):
        QApplication.clipboard().setText(self.details_text())
        # Say it took, then go back to being a button: a control stuck
        # reading "Copied" no longer looks like something you can press.
        self._copy_btn.setText("Copied")
        QTimer.singleShot(1500, self._reset_copy_label)

    def _reset_copy_label(self):
        self._copy_btn.setText("Copy details")

    # --------------------------------------------------------------- build
    def _build(self):
        outer = self.column
        outer.setContentsMargins(26, 22, 26, 20)
        outer.setSpacing(14)

        outer.addLayout(self._header())

        blurb = QLabel(_BLURB)
        blurb.setObjectName("blurb")
        blurb.setWordWrap(True)
        outer.addWidget(blurb)
        credits = QVBoxLayout()
        credits.setSpacing(2)
        author = QLabel(_AUTHOR)
        author.setObjectName("author")
        bold = author.font()
        bold.setWeight(QFont.Weight.DemiBold)
        author.setFont(bold)
        credits.addWidget(author)
        story = QLabel(_NAME_STORY)
        story.setObjectName("ver")
        credits.addWidget(story)
        outer.addLayout(credits)

        outer.addSpacing(2)
        outer.addWidget(self._build_card())
        outer.addSpacing(4)
        outer.addLayout(self._footer())

    def _header(self) -> QGridLayout:
        """The splash's mark and wordmark, level by its letters, with the
        version under the mark, as the welcome screen has them."""
        head = QGridLayout()
        head.setHorizontalSpacing(14)
        head.setVerticalSpacing(4)
        mark, letters = 80, 64
        logo = QLabel()
        logo.setPixmap(splash_mark_pixmap(mark))
        head.addWidget(logo, 0, 0)
        word = QLabel()
        word.setAccessibleName("Blackbyrd3D")
        word.setPixmap(wordmark_pixmap(letters))
        word.setContentsMargins(0, round(letters * (1 - _BASELINE)), 0, 0)
        head.addWidget(word, 0, 1, Qt.AlignmentFlag.AlignVCenter)
        ver = QLabel(f"v{self._version}  ·  MIT licence")
        ver.setObjectName("ver")
        head.addWidget(ver, 1, 0, 1, 2)
        head.setColumnStretch(2, 1)
        return head

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("build")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        section = QLabel("BUILD")
        section.setObjectName("section")
        sf = QFont("monospace")
        sf.setPointSizeF(8.5)
        section.setFont(sf)
        lay.addWidget(section)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(4)
        for row, (key, value) in enumerate(self._rows):
            k = QLabel(key)
            k.setObjectName("key")
            v = QLabel(value)
            v.setObjectName("val")
            # The values are the half of this anybody retypes, so let them
            # be selected out of the box as well as copied wholesale.
            v.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(k, row, 0)
            grid.addWidget(v, row, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        return card

    def _footer(self) -> QHBoxLayout:
        foot = QHBoxLayout()
        foot.setSpacing(8)
        foot.addWidget(self._link("Docs", _DOCS))
        foot.addWidget(self._dot())
        foot.addWidget(self._link("GitHub", _GITHUB))
        foot.addStretch(1)
        self._copy_btn = QPushButton("Copy details")
        self._copy_btn.clicked.connect(self.copy_details)
        close = QPushButton("Close")
        close.setObjectName("primaryButton")
        close.clicked.connect(self.accept)
        close.setDefault(True)
        for b in (self._copy_btn, close):
            b.setMinimumWidth(110)
            b.setSizePolicy(QSizePolicy.Policy.Fixed,
                            QSizePolicy.Policy.Fixed)
            foot.addWidget(b)
        return foot

    def _dot(self) -> QLabel:
        dot = QLabel("·")
        dot.setObjectName("ver")
        return dot

    def _link(self, text: str, url: str) -> QLabel:
        lab = QLabel(text)
        lab.setObjectName("link")
        lab.setCursor(Qt.CursorShape.PointingHandCursor)
        lab.mousePressEvent = (
            lambda _ev, u=url: QDesktopServices.openUrl(QUrl(u)))
        return lab


if __name__ == "__main__":                                 # pragma: no cover
    app = QApplication(sys.argv)
    AboutDialog().exec()
