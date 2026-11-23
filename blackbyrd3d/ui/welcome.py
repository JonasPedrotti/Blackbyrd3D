"""Welcome / start screen, shown on launch.

Start a new model in the units of your choice, open a file, or pick a card:
the documents last saved or opened, and the examples in the places they
have not filled yet. Skippable, and remembers the "show at startup" choice.
"""

from __future__ import annotations

import os
import sys
import time

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QColor, QDesktopServices, QFont, QFontMetrics, QPainter, QPainterPath,
    QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QVBoxLayout, QWidget,
)

from . import theme
from .card_dialog import STYLE as CARD_STYLE, CardDialog
from .splash import splash_mark_pixmap, wordmark_pixmap

_GITHUB = "https://github.com/JonasPedrotti/Blackbyrd3D"
_DOCS = "https://github.com/JonasPedrotti/Blackbyrd3D/tree/main/docs"

# New model and Open first, then the recent documents, examples in the
# places they leave
SLOTS = 4
COLUMNS = 3
PREVIEW = (240, 146)
# where the wordmark's baseline lies, as a share of its height
_BASELINE = 72.8 / 95.4

_QSS = f"""
QWidget#docs {{ background: transparent; }}
QLabel#word {{ color: #ececee; font-size: 24px; font-weight: 600; }}
QLabel#ver {{ color: #8d8e93; }}
QFrame#docCard {{ background: #27282c; border: 1px solid #3d3e44;
                 border-radius: 8px; }}
QFrame#docCard:hover {{ border-color: {theme.ACCENT}; }}
QLabel#cardName {{ color: #ececee; font-weight: bold; }}
QLabel#cardDetail {{ color: #85868a; font-size: 11px; }}
QComboBox#units {{ padding: 2px 8px; }}
QLabel#link {{ color: {theme.ACCENT}; }}
QCheckBox {{ color: #8d8e93; background: transparent; }}
"""


def start_cards(recent: list[str], examples: list[tuple]) -> list[dict]:
    """What the cards show, in order: the recent documents, newest first,
    then as many examples as there are places left. An example saved where
    it is stays an example rather than a recent document as well."""
    from ..examples import is_example
    own = [p for p in recent if not is_example(p)]
    cards = [{"path": p, "example": False} for p in own[:SLOTS]]
    for path, title, about in examples[:SLOTS - len(cards)]:
        cards.append({"path": path, "example": True, "title": title,
                      "about": about})
    return cards


def card_preview(path: str, width: int, height: int) -> QPixmap:
    """The picture a .byrd keeps of itself, or the kind of file on a plain
    tile when there is none."""
    pix = QPixmap(width, height)
    pix.fill(QColor("#1e1f23"))
    data = None
    if path.lower().endswith(".byrd"):
        from ..fileio.native import read_thumbnail
        try:
            data = read_thumbnail(path)
        except Exception:                               # noqa: BLE001
            data = None
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    shown = QPixmap()
    if data and shown.loadFromData(data):
        shown = shown.scaled(width, height,
                             Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                             Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap((width - shown.width()) // 2,
                           (height - shown.height()) // 2, shown)
    else:
        painter.setPen(QColor("#5c5d63"))
        f = QFont("monospace")
        f.setPointSizeF(13)
        painter.setFont(f)
        kind = os.path.splitext(path)[1].lstrip(".").upper() or "FILE"
        painter.drawText(QRectF(0, 0, width, height),
                         Qt.AlignmentFlag.AlignCenter, kind)
    painter.end()
    return pix


class Tile(QFrame):
    """One card on the welcome screen: a picture, a name and a line under
    it, which may be a widget of its own. A click anywhere else on it acts."""

    def __init__(self, picture: QPixmap, title: str, detail, act,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("docCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(PREVIEW[0] + 16)
        self._act = act
        shown = QLabel()
        shown.setPixmap(picture)
        self.name = QLabel()
        self.name.setObjectName("cardName")
        self.full_name = title
        self.name.setText(QFontMetrics(self.name.font()).elidedText(
            title, Qt.TextElideMode.ElideMiddle, PREVIEW[0]))
        if isinstance(detail, str):
            about = QLabel()
            about.setObjectName("cardDetail")
            about.setText(QFontMetrics(about.font()).elidedText(
                detail, Qt.TextElideMode.ElideRight, PREVIEW[0]))
            detail = about
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)
        lay.addWidget(shown)
        lay.addWidget(self.name)
        lay.addWidget(detail)

    def mouseReleaseEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton
                and self.rect().contains(event.position().toPoint())):
            self._act()
            return
        super().mouseReleaseEvent(event)


class DocCard(Tile):
    """A document: its picture, name and where it is. A click opens it."""

    def __init__(self, card: dict, open_it, parent=None):
        self.path = card["path"]
        self.example = card["example"]
        if self.example:
            title = card["title"]
            detail = f"Example · {card['about']}"
        else:
            title = os.path.basename(self.path)
            detail = _recent_detail(self.path)
        super().__init__(card_preview(self.path, *PREVIEW), title, detail,
                         lambda: open_it(self.path), parent)
        self.setToolTip(self.path)


def _symbol_picture(draw) -> QPixmap:
    """A plain tile with one symbol in the accent colour."""
    width, height = PREVIEW
    pix = QPixmap(width, height)
    pix.fill(QColor("#1e1f23"))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(theme.ACCENT), 3, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    draw(painter, width / 2, height / 2)
    painter.end()
    return pix


def _plus(painter, cx, cy, arm=20):
    painter.drawLine(QPointF(cx - arm, cy), QPointF(cx + arm, cy))
    painter.drawLine(QPointF(cx, cy - arm), QPointF(cx, cy + arm))


def _folder(painter, cx, cy):
    w, h = 54, 38
    x, y = cx - w / 2, cy - h / 2 + 3
    path = QPainterPath(QPointF(x, y + h))
    path.lineTo(x, y - 6)
    path.lineTo(x + 18, y - 6)
    path.lineTo(x + 23, y)
    path.lineTo(x + w, y)
    path.lineTo(x + w, y + h)
    path.closeSubpath()
    painter.drawPath(path)


def _recent_detail(path: str) -> str:
    """The folder a document is in and when it was last saved."""
    folder = os.path.basename(os.path.dirname(path)) or path
    try:
        when = time.strftime("%d.%m.%Y %H:%M",
                             time.localtime(os.path.getmtime(path)))
    except OSError:
        return folder
    return f"{folder} · {when}"


class WelcomeScreen(CardDialog):
    """The app's own popup card, centred on the window, closed with its
    cross or Escape. Not modal, so the window behind stays closable."""

    def __init__(self, window):
        super().__init__(window, "", title="Welcome to Blackbyrd3D")
        self.win = window
        self.setObjectName("welcome")
        if sys.platform.startswith("linux"):
            # GNOME glues a dialog-type window to its parent
            # (ui/dialogs.untether)
            self.setWindowFlags(Qt.WindowType.Window
                                | Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.heading.hide()
        self.cards: list[DocCard] = []
        self._build()
        # after the build: set before it, the labels kept the app's look
        self.setStyleSheet(CARD_STYLE + _QSS)
        self.adjustSize()
        self.setFixedSize(self.size())
        self._center_over(window.frameGeometry())

    def _build(self):
        outer = self.column
        outer.setContentsMargins(26, 22, 26, 18)
        outer.setSpacing(16)

        # the mark with the wordmark level with its middle, the version
        # under the mark
        header = QGridLayout()
        header.setHorizontalSpacing(16)
        header.setVerticalSpacing(4)
        logo = QLabel()
        logo.setPixmap(splash_mark_pixmap(64))
        header.addWidget(logo, 0, 0)
        word = QLabel()
        word.setObjectName("word")
        word.setAccessibleName("Blackbyrd3D")
        word.setPixmap(wordmark_pixmap(54))
        # level by the letters, not the tail of the y: the part above the
        # baseline is what centres on the mark
        word.setContentsMargins(0, round(54 * (1 - _BASELINE)), 0, 0)
        header.addWidget(word, 0, 1, Qt.AlignmentFlag.AlignVCenter)
        from .. import __version__
        ver = QLabel(f"v{__version__}  ·  precision NURBS modelling")
        ver.setObjectName("ver")
        header.addWidget(ver, 1, 0, 1, 2)
        header.setColumnStretch(2, 1)
        outer.addLayout(header)

        outer.addWidget(self._tiles(), 1)

        footer = QHBoxLayout()
        show = QCheckBox("Show this screen at startup")
        show.setChecked(self.win.cfg.get("show_welcome", default=True))
        show.toggled.connect(
            lambda on: self.win.cfg.set("show_welcome", on))
        footer.addWidget(show)
        footer.addStretch(1)
        footer.addWidget(self._link("Documentation", _DOCS))
        dot = QLabel("·")
        dot.setObjectName("ver")
        footer.addWidget(dot)
        footer.addWidget(self._link("GitHub", _GITHUB))
        outer.addLayout(footer)

    def _new_tile(self) -> Tile:
        from ..utils.units import UNIT_LABELS, UNITS
        self.units = QComboBox()
        self.units.setObjectName("units")
        self.units.setToolTip("Units of the new model")
        for unit in UNITS:
            self.units.addItem(UNIT_LABELS[unit].capitalize(), unit)
        default = self.win.cfg.get("default_units", default="mm")
        index = self.units.findData(default)
        self.units.setCurrentIndex(index if index >= 0 else 0)
        return Tile(_symbol_picture(_plus), "New model", self.units,
                    self._new)

    def _tiles(self) -> QWidget:
        from ..examples import examples
        shown = start_cards(self.win.recent_files(), examples())
        page = QWidget()
        page.setObjectName("docs")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setAlignment(Qt.AlignmentFlag.AlignLeft
                          | Qt.AlignmentFlag.AlignTop)
        tiles = [self._new_tile(),
                 Tile(_symbol_picture(_folder), "Open a file…",
                      "STEP · DXF · 3dm · OBJ · byrd", self._open)]
        for card in shown:
            doc = DocCard(card, self._open_path)
            self.cards.append(doc)
            tiles.append(doc)
        for i, tile in enumerate(tiles):
            grid.addWidget(tile, i // COLUMNS, i % COLUMNS)
        lay.addLayout(grid)
        lay.addStretch(1)
        return page

    def showEvent(self, ev):
        super().showEvent(ev)
        # On launch the window is still taking its saved, perhaps maximised,
        # size: centre again once it has.
        self._center()
        QTimer.singleShot(0, self._center)
        QTimer.singleShot(150, self._center)
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, ev):
        QApplication.instance().removeEventFilter(self)
        super().hideEvent(ev)

    def eventFilter(self, obj, ev):
        # A click anywhere outside it closes it, as a popup does; one in a
        # list it opened, the units', is still a click inside.
        if (ev.type() == QEvent.Type.MouseButtonPress and self.isVisible()
                and QApplication.activePopupWidget() is None
                and not self.frameGeometry().contains(
                    ev.globalPosition().toPoint())):
            self.reject()
            return False
        return super().eventFilter(obj, ev)

    def _center(self):
        """Over the middle of the window, or of its screen while the window
        is not on show."""
        win = self.win.window() if self.win is not None else None
        if win is not None and win.isVisible() and not win.isMinimized():
            area = win.frameGeometry()
        else:
            screen = (win.screen() if win is not None else None)                 or QApplication.primaryScreen()
            area = screen.availableGeometry()
        self._center_over(area)

    def _center_over(self, area):
        g = self.frameGeometry()
        g.moveCenter(area.center())
        self.move(g.topLeft())

    def _link(self, text: str, url: str) -> QLabel:
        lab = QLabel(f'<a style="color:{theme.ACCENT};text-decoration:none" '
                     f'href="{url}">{text}</a>')
        lab.setObjectName("link")
        lab.setOpenExternalLinks(False)
        lab.linkActivated.connect(lambda u: QDesktopServices.openUrl(QUrl(u)))
        return lab

    # -- actions --
    def _new(self):
        self.win.start_new(self.units.currentData())
        self.accept()

    def _open(self):
        self.accept()
        self.win._file_open()

    def _open_path(self, path: str):
        self.accept()
        self.win._open_path(path)


def should_show(window) -> bool:
    """Show the welcome screen on launch? Skips headless/automation, when
    turned off, and when a document is already loaded (CLI file / recovery)."""
    from PySide6.QtWidgets import QApplication
    if os.environ.get("BYRD3D_NO_WELCOME") == "1":
        return False
    if QApplication.platformName() in ("offscreen", "minimal", "vnc"):
        return False
    if not window.cfg.get("show_welcome", default=True):
        return False
    if getattr(window.ctx, "current_path", None) is not None:
        return False          # a file was opened / recovered
    return True
