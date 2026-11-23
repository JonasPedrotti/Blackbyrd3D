"""Smooth wheel scrolling for the app's lists, trees and panels.

A list scrolled by the wheel jumped a whole row, or three, at a time, and
in a short panel that is a jolt you lose your place in. Here every scroll
area scrolls by the pixel and glides each notch of the wheel over a short
animation instead.

The model's viewports and Wyrm's canvas keep the wheel for zooming, and a
held Ctrl is a zoom anywhere. A touchpad already scrolls by the pixel, so
its events go through as they come.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QAbstractScrollArea, QApplication, QGraphicsView)

DURATION_MS = 140
LINE_PX = 20                 # one line of the wheel's worth, in pixels


class SmoothWheel(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._anims = {}

    def eventFilter(self, obj, ev):
        if ev.type() != QEvent.Type.Wheel:
            return False
        area = obj.parent()
        if (not isinstance(area, QAbstractScrollArea)
                or area.viewport() is not obj
                or isinstance(area, QGraphicsView)
                or ev.modifiers() & Qt.KeyboardModifier.ControlModifier
                or not ev.pixelDelta().isNull()):
            return False
        delta = ev.angleDelta()
        vertical = abs(delta.y()) >= abs(delta.x())
        if ev.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            vertical = False
        notches = (delta.y() if abs(delta.y()) >= abs(delta.x())
                   else delta.x()) / 120.0
        if not notches:
            return False
        bar = area.verticalScrollBar() if vertical \
            else area.horizontalScrollBar()
        if bar is None or bar.maximum() <= bar.minimum():
            return False
        if isinstance(area, QAbstractItemView):
            mode = QAbstractItemView.ScrollMode.ScrollPerPixel
            if vertical:
                area.setVerticalScrollMode(mode)
            else:
                area.setHorizontalScrollMode(mode)
        step = QApplication.wheelScrollLines() * LINE_PX
        anim = self._anims.get(bar)
        start = bar.value()
        aim = anim.endValue() if (anim is not None and anim.state()
                                  == QPropertyAnimation.State.Running) \
            else start
        target = max(bar.minimum(),
                     min(bar.maximum(), round(aim - notches * step)))
        if target == start:
            return True
        if anim is None:
            anim = QPropertyAnimation(bar, b"value", self)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.setDuration(DURATION_MS)
            self._anims[bar] = anim
            bar.destroyed.connect(lambda _=None, b=bar: self._anims.pop(b, None))
        anim.stop()
        anim.setStartValue(start)
        anim.setEndValue(target)
        anim.start()
        return True


def install(app: QApplication) -> SmoothWheel:
    """Give every scroll area in the app a smooth wheel."""
    wheel = getattr(app, "_smooth_wheel", None)
    if wheel is None:
        wheel = app._smooth_wheel = SmoothWheel(app)
        app.installEventFilter(wheel)
    return wheel
