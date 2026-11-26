"""The popup ViewCapture opens: the pane as a picture, the pixels it is
taken at, and Copy and Save."""

from __future__ import annotations

import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QSpinBox,
)

from .card_dialog import STYLE, CardDialog

IMAGE_FILTER = "PNG image (*.png);;JPEG image (*.jpg *.jpeg)"

# the preview is a look at what is taken, never as big as the pane itself
_PREVIEW_SHARE = 0.55
_PREVIEW_MAX = (720, 460)
_COPIED_MS = 1500
_SCALE_STEP = 0.1

_STYLE = STYLE + """
QSpinBox, QDoubleSpinBox {
    background: #26272b; border: 1px solid #45464c; border-radius: 6px;
    color: #e8e8ea; padding: 4px 6px; min-width: 72px;
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #e6bd67; }
#preview { border: 1px solid #45464c; border-radius: 4px; }
#times { color: #8d8e93; }
#quietButton {
    background: transparent; border: 1px solid #4a4b52; color: #c4c5c9;
}
#quietButton:hover { background: #3a3b41; color: #e8e8ea; }
#copiedButton {
    background: #3d5a40; border: 1px solid #6fbf73; color: #dff5e0;
    font-weight: 600;
}
"""


def default_name() -> str:
    pictures = os.path.expanduser("~/Pictures")
    base = pictures if os.path.isdir(pictures) else os.path.expanduser("~")
    stamp = time.strftime("%Y-%m-%d %H-%M-%S")
    return os.path.join(base, f"Blackbyrd3D capture {stamp}.png")


class ViewCaptureDialog(CardDialog):
    """Width and height keep the pane's aspect: change one and the other
    follows, and so does the scale, which is the pixels over the pane's."""

    def __init__(self, parent, viewport, pick_file, echo):
        super().__init__(parent, "View capture", title="View capture")
        self.setStyleSheet(_STYLE)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.viewport = viewport
        self._pick_file = pick_file
        self._echo = echo
        self._syncing = False
        self.base_w, self.base_h = viewport.capture_size(1.0)
        max_scale = viewport.capture_max_scale()
        col, card = self.column, self.card

        self.preview = QLabel(card)
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shot = viewport.capture_image(1.0)
        if shot is not None:
            box_w = min(_PREVIEW_MAX[0], int(viewport.width() * _PREVIEW_SHARE))
            box_h = min(_PREVIEW_MAX[1], int(viewport.height() * _PREVIEW_SHARE))
            pix = QPixmap.fromImage(shot).scaled(
                max(box_w, 1), max(box_h, 1),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(pix)
            self.preview.setFixedSize(pix.size())
        col.addSpacing(8)
        col.addWidget(self.preview, 0, Qt.AlignmentFlag.AlignHCenter)
        col.addSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.width_box = self._pixels(int(self.base_w * max_scale))
        self.height_box = self._pixels(int(self.base_h * max_scale))
        times = QLabel("×", card)
        times.setObjectName("times")
        px = QLabel("px", card)
        px.setObjectName("times")
        self.scale_box = QDoubleSpinBox(card)
        self.scale_box.setDecimals(2)
        self.scale_box.setSingleStep(_SCALE_STEP)
        self.scale_box.setRange(0.1, max_scale)
        self.scale_box.setPrefix("× ")
        self.scale_box.setKeyboardTracking(False)
        self.scale_box.setToolTip("Scale: the pane's own pixels times this")
        self.width_box.setToolTip("Width in pixels")
        self.height_box.setToolTip("Height in pixels")
        row.addWidget(self.width_box)
        row.addWidget(times)
        row.addWidget(self.height_box)
        row.addWidget(px)
        row.addSpacing(10)
        row.addWidget(self.scale_box)
        row.addStretch(1)

        self.copy_button = QPushButton("Copy", card)
        self.copy_button.setObjectName("quietButton")
        self.copy_button.setAutoDefault(False)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self.copy)
        self.save_button = QPushButton("Save…", card)
        self.save_button.setObjectName("primaryButton")
        self.save_button.setAutoDefault(False)
        self.save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_button.clicked.connect(self.save)
        row.addWidget(self.copy_button)
        row.addWidget(self.save_button)
        col.addLayout(row)

        self._copied = QTimer(self)
        self._copied.setSingleShot(True)
        self._copied.timeout.connect(self._copy_done)

        self.width_box.valueChanged.connect(self._width_changed)
        self.height_box.valueChanged.connect(self._height_changed)
        self.scale_box.valueChanged.connect(self._scale_changed)
        self.set_scale(1.0)
        # the card holds the focus, so no field opens selected and typing
        # has to start with a click into one
        card.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def showEvent(self, ev):
        super().showEvent(ev)
        self.card.setFocus()

    def _pixels(self, top: int) -> QSpinBox:
        box = QSpinBox(self.card)
        box.setRange(1, max(1, top))
        box.setSuffix("")
        box.setKeyboardTracking(False)
        return box

    # -- the three numbers, kept together --

    @property
    def scale(self) -> float:
        return self.width_box.value() / self.base_w

    def set_scale(self, scale: float):
        self._show(scale, None)

    def _show(self, scale: float, held):
        """Every box but the one being typed in, set from `scale`."""
        if self._syncing:
            return
        self._syncing = True
        try:
            if held is not self.width_box:
                self.width_box.setValue(max(1, round(self.base_w * scale)))
            if held is not self.height_box:
                self.height_box.setValue(max(1, round(self.base_h * scale)))
            if held is not self.scale_box:
                self.scale_box.setValue(scale)
        finally:
            self._syncing = False

    def _width_changed(self, value: int):
        self._show(value / self.base_w, self.width_box)

    def _height_changed(self, value: int):
        self._show(value / self.base_h, self.height_box)

    def _scale_changed(self, value: float):
        self._show(value, self.scale_box)

    # -- what it is for --

    def image(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            img = self.viewport.capture_image(self.scale)
        finally:
            QApplication.restoreOverrideCursor()
        if img is None:
            self._echo("The viewport could not be captured at "
                       f"{self.width_box.value()}x{self.height_box.value()}.")
        return img

    def copy(self):
        img = self.image()
        if img is None:
            return
        QApplication.clipboard().setImage(img)
        self._echo(f"Copied {img.width()}x{img.height()} capture to the "
                   "clipboard.")
        self.copy_button.setText("Copied ✓")
        self.copy_button.setObjectName("copiedButton")
        self._restyle(self.copy_button)
        self._copied.start(_COPIED_MS)

    def _copy_done(self):
        self.copy_button.setText("Copy")
        self.copy_button.setObjectName("quietButton")
        self._restyle(self.copy_button)

    @staticmethod
    def _restyle(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def save(self):
        path = self._pick_file(save=True, title="Save view capture",
                               name=default_name(), filters=IMAGE_FILTER)
        if not path:
            return
        if not path.lower().endswith((".png", ".jpg", ".jpeg")):
            path += ".png"
        img = self.image()
        if img is None:
            return
        if not img.save(path):
            self._echo(f"Could not save the capture to {path}.")
            return
        self._echo(f"Saved {img.width()}x{img.height()} capture to {path}")
        self.accept()
