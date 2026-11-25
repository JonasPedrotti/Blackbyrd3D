"""The ShowEdges popup: which edges to draw, in which colour, and on which
objects. It stays open beside the model, and the edges go when it closes."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QWidget

from .card_dialog import CardDialog
from .color_picker import get_color
from .list_buttons import list_button

BUTTON_HEIGHT = 34

_SIDE_BUTTON_STYLE = f"""
QPushButton {{
    min-width: 0; padding: 0; border-radius: 5px;
    min-height: {BUTTON_HEIGHT - 2}px; max-height: {BUTTON_HEIGHT - 2}px;
    background: #3a3b41; border: 1px solid #4a4b52;
}}
QPushButton:hover {{ background: #45464d; }}
QPushButton:pressed {{ background: #505159; }}
"""

PANEL_STYLE = """
QCheckBox { color: #c4c5c9; spacing: 8px; }
"""


class ColorSwatch(QWidget):
    """The edge colour as a rounded square; a click opens the picker.

    Painted rather than styled: a styled button left a trail of shadow
    behind it while the card was dragged."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = QColor()
        self._hover = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_color(self, color: QColor):
        self.color = QColor(color)
        self.update()

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        edge = "#8d8e93" if self._hover else "#55565c"
        p.setPen(QPen(QColor(edge), 1))
        p.setBrush(self.color)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
                          5, 5)
        p.end()

    def enterEvent(self, _ev):
        self._hover = True
        self.update()

    def leaveEvent(self, _ev):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, ev):
        if (ev.button() == Qt.MouseButton.LeftButton
                and self.rect().contains(ev.position().toPoint())):
            self.clicked.emit()

    def mousePressEvent(self, ev):
        # taken here, so the press does not start a drag of the card
        ev.accept()


class ShowEdgesPanel(CardDialog):
    def __init__(self, window):
        super().__init__(window, "Show Edges")
        self.setStyleSheet(self.styleSheet() + PANEL_STYLE)
        self.setModal(False)
        self.window_ = window

        self.all_box = QCheckBox("All edges")
        self.naked_box = QCheckBox("Naked edges")
        for box, attr in ((self.all_box, "edges_show_all"),
                          (self.naked_box, "edges_show_naked")):
            box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            box.toggled.connect(
                lambda on, attr=attr: self._set(attr, bool(on)))
            self.column.addWidget(box)

        self.color_button = ColorSwatch()
        self.color_button.setToolTip("Edge color")
        self.color_button.clicked.connect(self._pick_color)
        self.add_button = list_button(
            "new", "Add the selected objects",
            lambda: self._run("showedgesadd"))
        self.remove_button = list_button(
            "remove", "Remove the selected objects",
            lambda: self._run("showedgesremove"))

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        for button in (self.add_button, self.remove_button):
            button.setIconSize(QSize(18, 18))
            # the card's own button size would win over the layout's
            button.setStyleSheet(_SIDE_BUTTON_STYLE)
        for button in (self.add_button, self.remove_button,
                       self.color_button):
            button.setMinimumWidth(0)
            button.setMaximumWidth(16777215)
            button.setFixedHeight(BUTTON_HEIGHT)
            buttons.addWidget(button, 1)
        self.column.addSpacing(6)
        self.column.addLayout(buttons)
        self.refresh()

    @property
    def scene(self):
        return self.window_.scene

    def reset_options(self):
        """Each time it opens: naked edges only."""
        self.scene.edges_show_all = False
        self.scene.edges_show_naked = True

    def refresh(self):
        """Show what the scene holds, without echoing it back."""
        scene = self.scene
        for box, on in ((self.all_box, scene.edges_show_all),
                        (self.naked_box, scene.edges_show_naked)):
            box.blockSignals(True)
            box.setChecked(on)
            box.blockSignals(False)
        self.color_button.set_color(QColor.fromRgbF(*scene.edges_color[:3]))

    def _set(self, attr, value):
        setattr(self.scene, attr, value)
        self._repaint()

    def _pick_color(self):
        scene = self.scene
        before = scene.edges_color

        def preview(color):
            scene.edges_color = (before if color is None
                                 else color.getRgbF()[:3])
            self._repaint()

        picked = get_color(QColor.fromRgbF(*before[:3]), self,
                           "Edge color", preview=preview)
        if picked.isValid():
            scene.edges_color = picked.getRgbF()[:3]
        self.refresh()
        self._repaint()

    def _run(self, name):
        self.window_.run_command(name)

    def _repaint(self):
        for pane in self.window_.all_viewports():
            pane.update()

    def done(self, result):
        # the edges belong to the panel, as Rhino's go with its dialog
        self.scene.edges_shown.clear()
        self._repaint()
        super().done(result)
