"""Asking before a layer that still holds objects is deleted with them."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy

from .card_dialog import CardDialog


class DeleteLayerPrompt(CardDialog):
    def __init__(self, parent, name: str, count: int, sublayers: bool):
        super().__init__(parent, f"Delete layer “{name}”?",
                         title="Delete layer")
        card, col = self.card, self.column
        self.heading.setMinimumWidth(340)
        where = "on it and its sublayers" if sublayers else "on it"
        things = "1 object" if count == 1 else f"{count} objects"
        body = QLabel(f"{things} {'is' if count == 1 else 'are'} {where}. "
                      "Deleting the layer deletes "
                      f"{'it' if count == 1 else 'them'} too.", card)
        body.setObjectName("body")
        body.setWordWrap(True)
        col.addWidget(body)
        col.addSpacing(14)

        row = QHBoxLayout()
        row.setSpacing(8)
        cancel = QPushButton("Cancel", card)
        delete = QPushButton("Delete", card)
        delete.setObjectName("primaryButton")
        for b in (cancel, delete):
            b.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Fixed)
            row.addWidget(b, 1)
        col.addLayout(row)
        cancel.clicked.connect(self.reject)
        delete.clicked.connect(self.accept)
        # Enter, without a look, keeps the work
        cancel.setDefault(True)
        cancel.setFocus()


def confirm_delete_layer(parent, name: str, count: int,
                         sublayers: bool = False) -> bool:
    """True when Delete was chosen; Cancel, the cross and Escape keep it."""
    return DeleteLayerPrompt(parent, name, count, sublayers).exec() == \
        DeleteLayerPrompt.DialogCode.Accepted
