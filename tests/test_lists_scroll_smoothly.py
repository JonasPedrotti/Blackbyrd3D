"""A list scrolls smoothly under the wheel: by the pixel, gliding, rather
than jumping a row at a time."""

from __future__ import annotations

from PySide6.QtCore import QEventLoop, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QGraphicsView, QListWidget

from blackbyrd3d.ui import smooth_scroll


def _wheel(widget, dy, pixel=0, mods=Qt.KeyboardModifier.NoModifier):
    ev = QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(0, pixel),
                     QPoint(0, dy), Qt.MouseButton.NoButton, mods,
                     Qt.ScrollPhase.NoScrollPhase, False)
    return QApplication.sendEvent(widget, ev)


def _wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _list():
    lw = QListWidget()
    for i in range(200):
        lw.addItem(f"Layer {i}")
    lw.resize(200, 150)
    lw.show()
    QApplication.processEvents()
    return lw


def test_a_notch_glides_by_the_pixel():
    smooth_scroll.install(QApplication.instance())
    lw = _list()
    bar = lw.verticalScrollBar()
    _wheel(lw.viewport(), -120)
    assert lw.verticalScrollMode() == lw.ScrollMode.ScrollPerPixel
    _wait(smooth_scroll.DURATION_MS // 3)
    midway = bar.value()
    _wait(smooth_scroll.DURATION_MS * 2)
    end = bar.value()
    step = QApplication.wheelScrollLines() * smooth_scroll.LINE_PX
    assert 0 < midway < end
    assert end == min(step, bar.maximum())
    lw.deleteLater()


def test_ctrl_and_a_canvas_keep_the_wheel_to_themselves():
    wheel = smooth_scroll.install(QApplication.instance())
    lw = _list()
    assert not wheel.eventFilter(
        lw.viewport(), QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, -120),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier,
            Qt.ScrollPhase.NoScrollPhase, False))
    view = QGraphicsView()
    view.show()
    assert not wheel.eventFilter(
        view.viewport(), QWheelEvent(
            QPointF(10, 10), QPointF(10, 10), QPoint(0, 0), QPoint(0, -120),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase, False))
    lw.deleteLater()
    view.deleteLater()
