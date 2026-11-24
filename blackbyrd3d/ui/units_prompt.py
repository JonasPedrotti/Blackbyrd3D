"""Asking whether a model keeps its real size when the units change."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy

from .card_dialog import CardDialog

SCALE, KEEP, CANCEL = "scale", "keep", "cancel"


class UnitsPrompt(CardDialog):
    def __init__(self, parent, factor: float, old: str, new: str):
        super().__init__(parent, f"Do you want to scale by {factor:g}?",
                         title="Change units")
        self.answer = CANCEL
        card, col = self.card, self.column
        self.heading.setMinimumWidth(340)
        body = QLabel(f"Without scaling, 100 {old} becomes 100 {new}.", card)
        body.setObjectName("body")
        body.setWordWrap(True)
        col.addWidget(body)
        col.addSpacing(14)

        row = QHBoxLayout()
        row.setSpacing(8)
        keep = QPushButton("Don't Scale", card)
        scale = QPushButton("Scale", card)
        scale.setObjectName("primaryButton")
        scale.setDefault(True)
        for b in (scale, keep):
            b.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Fixed)
            row.addWidget(b, 1)
        col.addLayout(row)

        keep.clicked.connect(lambda: self._finish(KEEP))
        scale.clicked.connect(lambda: self._finish(SCALE))
        scale.setFocus()

    def _finish(self, answer: str):
        self.answer = answer
        self.accept()


def ask_scale_for_units(parent, factor: float, old: str, new: str) -> str:
    """SCALE or KEEP; CANCEL when closed with the cross or Escape."""
    dlg = UnitsPrompt(parent, factor, old, new)
    dlg.exec()
    return dlg.answer
