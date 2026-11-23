"""Startup splash screen — shown while the geometry kernel and main window
load.

Built on Qt's QSplashScreen, which is designed for the "show, then do
blocking init" case and reliably paints its first frame on show — a custom
QWidget does not, because the ~2s kernel import is a pure C dlopen that
pumps no Qt events, so a custom splash would map but never paint.

The static art (dark panel, the bird in its crescent, the wordmark and the
footer stamp) is baked into a pixmap once; the status line and progress
hairline are drawn live in drawContents().
"""

from __future__ import annotations

import os

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QTransform,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QSplashScreen

from . import brand

_BG_TOP = QColor("#232428")
_BG_BOT = QColor("#161719")
_BORDER = QColor("#3a3b40")
_GOLD = QColor("#e6bd67")     # the accent: crescent, "byrd", progress
_BLACK = QColor("#4a4b51")
_MUTED = QColor("#85868a")

_W, _H = 480, 320           # drawn in these units...
_SCALE = 1.3                # ...and shown this much larger
_MARK = 168                 # the bird and crescent, square, px
_WORD_TOP, _WORD_H = 192, 44


def _placed(d: str, transform: QTransform) -> QPainterPath:
    return transform.map(brand.path(d))


def paint_mark(p: QPainter, left: float, top: float, size: float):
    """The splash mark: the gold crescent, the bird in front of it."""
    unit = QTransform()
    unit.translate(left, top)
    unit.scale(size / 4267, size / 4267)
    p.fillPath(_placed(brand.SPLASH_RING, unit), _GOLD)
    QSvgRenderer(QByteArray(brand.SPLASH_BIRD.encode())).render(
        p, QRectF(left, top, size, size))


def paint_wordmark(p: QPainter, left: float, top: float, height: float):
    """The wordmark: "black" in grey, "byrd" in gold."""
    w, h = brand.WORDMARK_SIZE
    k = height / h
    word = QTransform()
    word.translate(left, top)
    word.scale(k, k)
    p.fillPath(_placed(brand.WORDMARK_BLACK, word), _BLACK)
    p.fillPath(_placed(brand.WORDMARK_BYRD, word), _GOLD)


def wordmark_pixmap(height: int) -> QPixmap:
    """The wordmark alone, `height` logical px tall, on nothing."""
    w, h = brand.WORDMARK_SIZE
    width = round(w * height / h) + 2
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    pm = QPixmap(round(width * dpr), round((height + 2) * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint_wordmark(p, 0, 0, height)
    p.end()
    return pm


def splash_mark_pixmap(width: int) -> QPixmap:
    """The splash mark alone, `width` logical px square, on nothing."""
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    pm = QPixmap(round(width * dpr), round(width * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint_mark(p, 0, 0, width)
    p.end()
    return pm


def _base_pixmap(version: str) -> QPixmap:
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    pm = QPixmap(int(_W * _SCALE * dpr), int(_H * _SCALE * dpr))
    pm.setDevicePixelRatio(dpr)
    p = QPainter(pm)
    p.setRenderHints(QPainter.RenderHint.Antialiasing
                     | QPainter.RenderHint.TextAntialiasing)
    p.scale(_SCALE, _SCALE)

    grad = QLinearGradient(0, 0, 0, _H)
    grad.setColorAt(0, _BG_TOP)
    grad.setColorAt(1, _BG_BOT)
    p.fillRect(0, 0, _W, _H, grad)
    p.setPen(QPen(_BORDER, 1.4))
    p.drawRect(QRectF(0.7, 0.7, _W - 1.4, _H - 1.4))

    paint_mark(p, (_W - _MARK) / 2, 14, _MARK)

    w, h = brand.WORDMARK_SIZE
    paint_wordmark(p, (_W - w * _WORD_H / h) / 2, _WORD_TOP, _WORD_H)

    # footer stamp
    ff = QFont()
    ff.setFamilies(["Consolas", "Menlo", "DejaVu Sans Mono", "monospace"])
    ff.setStyleHint(QFont.StyleHint.Monospace)
    ff.setPixelSize(10)
    ff.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
    p.setFont(ff)
    p.setPen(_MUTED)
    p.drawText(QRectF(0, _H - 46, _W, 16), Qt.AlignmentFlag.AlignHCenter,
               f"v{version}   ·   MIT   ·   OPEN SOURCE")
    p.end()
    return pm


class SplashScreen(QSplashScreen):
    def __init__(self, version: str = "0.1.0"):
        super().__init__(_base_pixmap(version))
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self._status = ""
        self._progress = 0.0

    def message(self, text: str, progress: float | None = None):
        """Update status line (+ optional 0..1 progress) and repaint now."""
        self._status = text
        if progress is not None:
            self._progress = max(0.0, min(1.0, progress))
        self.repaint()
        QApplication.processEvents()

    def drawContents(self, painter: QPainter):
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.scale(_SCALE, _SCALE)
        sf = QFont()
        sf.setPointSizeF(8.5)
        painter.setFont(sf)
        painter.setPen(_MUTED)
        painter.drawText(QRectF(0, 244, _W, 18),
                         Qt.AlignmentFlag.AlignHCenter, self._status)
        if self._progress > 0:
            y, x0, x1 = _H - 4, 20, _W - 20
            painter.setPen(QPen(QColor(230, 189, 103, 90), 2))
            painter.drawLine(x0, y, x1, y)
            painter.setPen(QPen(_GOLD, 2))
            painter.drawLine(x0, y, int(x0 + (x1 - x0) * self._progress), y)


def mark_pixmap(width: int) -> QPixmap:
    """The app icon, `width` logical px square, sharp on this screen."""
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    pm = brand.icon_pixmap(round(width * dpr))
    pm.setDevicePixelRatio(dpr)
    return pm


def should_show() -> bool:
    """Skip the splash for headless/automation runs."""
    if os.environ.get("BYRD3D_NO_SPLASH") == "1":
        return False
    if QApplication.platformName() in ("offscreen", "minimal", "vnc"):
        return False
    return True
