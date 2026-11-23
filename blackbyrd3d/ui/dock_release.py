"""Finishing a panel drag that Qt never saw end, on X11.

While a panel is dragged out of its dock, Qt marks its window to bypass
the window manager, so it can follow the cursor, and on the button's
release ends the drag and takes the mark off. Under XWayland that release
can miss the panel: the mark stays, so it floats above every window and
the window manager ignores where Qt puts it, and Qt, still dragging in
its own eyes, ignores every later press on its title. So a panel left
marked is handed the release it missed, once the button is up or when it
is pressed again, and the mark goes in case Qt still leaves it.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QApplication, QDockWidget

_BYPASS = Qt.WindowType.X11BypassWindowManagerHint
_POLL_MS = 100


def stuck(dock: QDockWidget) -> bool:
    return dock.isFloating() and bool(dock.windowFlags() & _BYPASS)


def settle(dock: QDockWidget, pressed: bool = False) -> bool:
    """End the drag a marked floating panel is stuck in. Waits for the
    button to be up unless `pressed`, a new press having shown the old
    drag is over. Returns whether there was one."""
    if not stuck(dock):
        return False
    if not pressed and QApplication.mouseButtons() != Qt.MouseButton.NoButton:
        return False                    # perhaps still being dragged
    geometry = dock.geometry()
    cursor = QCursor.pos()
    QApplication.sendEvent(dock, QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(dock.mapFromGlobal(cursor)), QPointF(cursor),
        Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier))
    if stuck(dock):
        dock.setWindowFlags(dock.windowFlags() & ~_BYPASS)
        dock.setGeometry(geometry)
        dock.show()
    return True


class _Watch(QObject):
    def __init__(self, dock):
        super().__init__(dock)
        self.dock = dock
        self.timer = QTimer(self)
        self.timer.setInterval(_POLL_MS)
        self.timer.timeout.connect(self._poll)
        dock.topLevelChanged.connect(lambda _floating: self.timer.start())
        dock.installEventFilter(self)

    def _poll(self):
        if not stuck(self.dock) or settle(self.dock):
            self.timer.stop()

    def eventFilter(self, dock, ev):
        if ev.type() == QEvent.Type.MouseButtonPress and stuck(dock):
            settle(dock, pressed=True)
        return False


def watch(dock: QDockWidget) -> None:
    """Keep `dock` draggable after it is torn off. Only X11 has the mark;
    elsewhere this does nothing."""
    if QGuiApplication.platformName() == "xcb":
        _Watch(dock)
