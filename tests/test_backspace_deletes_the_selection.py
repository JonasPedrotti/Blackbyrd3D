"""Backspace deletes what is selected, as Delete does.

A Mac's delete key reaches Qt as Backspace, and a Mac laptop has no forward
Delete, so in model space nothing happened when it was pressed.
"""

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from blackbyrd3d.app import MainWindow
from blackbyrd3d.core import geometry as g


def _window_with_a_box():
    w = MainWindow()
    oid = w.ctx.add(g.make_box((0, 0, 0), 1, 1, 1)).id
    return w, oid


def _close(w):
    w.mark_saved()
    w.close()


def test_backspace_deletes_the_selection():
    w, oid = _window_with_a_box()
    w.selection.set([oid])
    QTest.keyClick(w.viewport, Qt.Key.Key_Backspace)
    assert w.scene.get(oid) is None
    _close(w)


def test_backspace_with_nothing_selected_deletes_nothing():
    w, oid = _window_with_a_box()
    w.selection.set([])
    QTest.keyClick(w.viewport, Qt.Key.Key_Backspace)
    assert w.scene.get(oid) is not None
    assert not w.processor.busy
    _close(w)


def test_backspace_during_a_command_leaves_the_objects():
    w, oid = _window_with_a_box()
    w.processor.run("line")
    w.selection.set([oid])
    QTest.keyClick(w.viewport, Qt.Key.Key_Backspace)
    assert w.scene.get(oid) is not None
    w.processor.cancel()
    _close(w)
