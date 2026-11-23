"""The app's own popup: a frameless card with a shadow, a heading, a close
cross in its corner and a highlighted main button, dragged by its body."""

from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QFrame, QGraphicsDropShadowEffect, QLabel, QPushButton,
    QVBoxLayout, QWidget,
)

_CLOSE_SIZE = 30
_CLOSE_INSET = 8

STYLE = """
#card {
    background: #2e2f34; border: 1px solid #45464c; border-radius: 10px;
}
QLabel { background: transparent; }
#heading { font-size: 15px; font-weight: 600; color: #e8e8ea; }
#body { color: #a9aaae; }
#fieldLabel { color: #c4c5c9; }
QPushButton { min-width: 60px; padding: 6px 14px; border-radius: 6px; }
#closeX {
    min-width: 0; padding: 0; border: none; border-radius: 5px;
    background: transparent; color: #8d8e93; font-size: 17px;
}
#closeX:hover { background: #3f4047; color: #e8e8ea; }
#primaryButton {
    background: #e6bd67; border: 1px solid #e6bd67; color: #1f1f22;
    font-weight: 600;
}
#primaryButton:hover { background: #f4d07f; border-color: #f4d07f; }
#primaryButton:pressed { background: #c4a054; }
"""


class CardDialog(QDialog):
    """Subclasses fill `self.column`, under the heading."""

    def __init__(self, parent, heading: str, title: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title or heading)
        self.setWindowFlags(Qt.WindowType.Dialog
                            | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(STYLE)
        self._drag = None

        outer = QVBoxLayout(self)
        card = QFrame(self)
        card.setObjectName("card")
        if sys.platform.startswith("linux"):
            # Linux desktops frame, round and shade every window themselves,
            # a transparent shadow margin included, which then shows as a
            # box around the card: there the window is the card.
            outer.setContentsMargins(0, 0, 0, 0)
            card.setStyleSheet("#card { border-radius: 0; }")
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            outer.setContentsMargins(18, 18, 18, 18)
            shadow = QGraphicsDropShadowEffect(card)
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 2)
            shadow.setColor(QColor(0, 0, 0, 70))
            card.setGraphicsEffect(shadow)
        outer.addWidget(card)
        self.card = card

        col = QVBoxLayout(card)
        col.setContentsMargins(22, 18, 22, 18)
        col.setSpacing(6)
        self.heading = QLabel(heading, card)
        self.heading.setObjectName("heading")
        self.heading.setContentsMargins(0, 0, _CLOSE_SIZE, 0)
        col.addWidget(self.heading)
        self.column = col

        self._close = QPushButton("✕", card)
        self._close.setObjectName("closeX")
        self._close.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._close.setFixedSize(_CLOSE_SIZE, _CLOSE_SIZE)
        self._close.clicked.connect(self.reject)
        card.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if obj is self.card and ev.type() == QEvent.Type.Resize:
            # as far in from the top as from the right: on the corner's
            # diagonal
            self._close.move(obj.width() - _CLOSE_INSET - _CLOSE_SIZE,
                             _CLOSE_INSET)
            self._close.raise_()
        return super().eventFilter(obj, ev)

    def showEvent(self, ev):
        super().showEvent(ev)
        parent = self.parentWidget()
        if parent is not None:
            g = self.frameGeometry()
            # QWidget's own window(): a parent may hide it under an
            # attribute of that name, as the Wyrm editor does
            g.moveCenter(QWidget.window(parent).frameGeometry().center())
            self.move(g.topLeft())

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag = ev.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._drag is not None:
            self.move(ev.globalPosition().toPoint() - self._drag)
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._drag = None
        super().mouseReleaseEvent(ev)
