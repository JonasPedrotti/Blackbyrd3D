"""Telling on launch that a newer release is out, with a way to fetch it."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy

from .card_dialog import CardDialog


class UpdatePrompt(CardDialog):
    """Not modal: it waits behind the welcome screen and blocks nothing."""

    downloadRequested = Signal()

    def __init__(self, parent):
        super().__init__(parent, "", title="Update available")
        self.setWindowModality(Qt.WindowModality.NonModal)
        card = self.card
        col = self.column
        self.heading.setMinimumWidth(340)
        self.body = QLabel(card)
        self.body.setObjectName("body")
        self.body.setWordWrap(True)
        col.addWidget(self.body)
        col.addSpacing(14)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.download = QPushButton("Download now", card)
        self.download.setObjectName("primaryButton")
        self.download.setDefault(True)
        self.cancel = QPushButton("Cancel", card)
        for b in (self.download, self.cancel):
            b.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Fixed)
            row.addWidget(b, 1)
        col.addLayout(row)

        self.download.clicked.connect(self.downloadRequested)
        self.download.clicked.connect(self.accept)
        self.cancel.clicked.connect(self.reject)

    def set_release(self, version: str, current: str,
                    installs: bool = False):
        self.heading.setText(f"Blackbyrd3D {version} is available")
        if installs:
            self.download.setText("Update now")
            self.body.setText(f"You have version {current}. Blackbyrd3D "
                              "downloads and installs it, then restarts.")
        else:
            self.download.setText("Download now")
            self.body.setText(f"You have version {current}.")
