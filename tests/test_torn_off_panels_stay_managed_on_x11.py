from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication, QDockWidget, QLabel, QMainWindow, QWidget,
)

from blackbyrd3d.ui import dock_release

BYPASS = Qt.WindowType.X11BypassWindowManagerHint


def _floating_dock():
    window = QMainWindow()
    dock = QDockWidget("Wyrm", window)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
    window.show()
    dock.setFloating(True)
    dock.show()
    return window, dock


def test_a_panel_left_bypassing_the_window_manager_is_handed_back(
        monkeypatch):
    # Qt keeps a button down that an earlier test pressed and never let go
    monkeypatch.setattr(dock_release, "buttons_down", lambda: False)
    window, dock = _floating_dock()
    dock.setWindowFlags(dock.windowFlags() | BYPASS)
    dock.setGeometry(QRect(40, 166, 583, 701))
    dock.show()

    assert dock_release.settle(dock)
    assert not dock.windowFlags() & BYPASS
    assert dock.isFloating() and dock.isVisible()
    assert dock.geometry().size() == QRect(40, 166, 583, 701).size()
    window.close()


def test_a_tear_off_whose_release_went_missing_is_ended():
    window = QMainWindow()
    window.setCentralWidget(QLabel("model"))
    window.resize(800, 600)
    dock = QDockWidget("Wyrm", window)
    dock.setWidget(QLabel("graph"))
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
    window.show()
    QApplication.processEvents()

    def send(kind, local, buttons):
        QApplication.sendEvent(dock, QMouseEvent(
            kind, QPointF(local), QPointF(dock.mapToGlobal(local)),
            Qt.MouseButton.LeftButton, buttons,
            Qt.KeyboardModifier.NoModifier))

    title = QPoint(10, 5)
    send(QEvent.Type.MouseButtonPress, title, Qt.MouseButton.LeftButton)
    send(QEvent.Type.MouseMove, title + QPoint(300, 200),
         Qt.MouseButton.LeftButton)
    # torn off, and the release never arrives
    assert dock_release.stuck(dock)
    assert QWidget.mouseGrabber() is dock

    assert dock_release.settle(dock, pressed=True)
    assert not dock_release.stuck(dock)
    assert QWidget.mouseGrabber() is None
    window.close()


def test_a_panel_still_being_dragged_is_left_alone(monkeypatch):
    monkeypatch.setattr(dock_release, "buttons_down", lambda: True)
    window, dock = _floating_dock()
    dock.setWindowFlags(dock.windowFlags() | BYPASS)
    dock.show()
    assert not dock_release.settle(dock)
    assert dock_release.stuck(dock)
    window.close()


def test_a_managed_or_docked_panel_is_left_alone():
    window, dock = _floating_dock()
    assert not dock_release.settle(dock)
    dock.setFloating(False)
    assert not dock_release.settle(dock)
    window.close()
