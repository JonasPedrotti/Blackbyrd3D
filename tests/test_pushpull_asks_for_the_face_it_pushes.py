"""pushpull always asks for the face, and a plain click takes it.

What was picked before does not count: the command asks "Select surface to
pushpull" every time. A click on a face, without Ctrl+Shift, picks that
face and goes straight on to how far.
"""

import numpy as np
import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest

from blackbyrd3d.app import MainWindow
from blackbyrd3d.commands.base import PointReq, SelectReq
from blackbyrd3d.core import geometry as g


def _top(shape):
    faces = g.faces_of(shape)
    return max(range(len(faces)),
               key=lambda i: g.face_point_normal(faces[i])[0][2])


def test_it_asks_even_with_something_picked(env):
    scene, sel, _hist, _ctx, proc = env
    box = scene.add(g.make_box((0, 0, 0), 10, 10, 10))
    sel.set([box.id])
    sel.toggle_subobject(box.id, "face", _top(box.shape))
    proc.run("pushpull")
    assert isinstance(proc.request, SelectReq)
    assert proc.request.prompt == "Select surface to pushpull"
    assert proc.request.want_face


def test_a_picked_face_goes_straight_to_the_distance(env):
    scene, _sel, _hist, _ctx, proc = env
    box = scene.add(g.make_box((0, 0, 0), 10, 10, 10))
    proc.run("pushpull")
    proc.click_face(box.id, _top(box.shape))
    assert isinstance(proc.request, PointReq)
    proc.provide_text("5")
    assert not proc.busy
    assert g.volume(scene.get(box.id).shape) == pytest.approx(1500, rel=1e-3)


def test_a_typed_name_without_a_face_pushes_nothing(env):
    scene, _sel, _hist, _ctx, proc = env
    box = scene.add(g.make_box((0, 0, 0), 10, 10, 10))
    proc.run("pushpull")
    proc.click_object(box.id)
    assert not proc.busy
    assert g.volume(scene.get(box.id).shape) == pytest.approx(1000, rel=1e-3)


def test_a_plain_click_in_the_view_picks_the_face():
    w = MainWindow()
    w.show()
    vp = w.viewport
    vp.resize(800, 600)
    vp.set_view("top")
    box = w.ctx.add(g.make_box((0, 0, 0), 10, 10, 10))
    vp.camera.target = np.array([5.0, 5.0, 5.0])
    vp.camera.distance = 60.0
    w.processor.run("pushpull")
    px, py = vp._eye().project(np.array([[3.0, 4.0, 10.0]]),
                               vp.width(), vp.height())[0, :2]
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier,
                     QPointF(float(px), float(py)).toPoint())
    assert isinstance(w.processor.request, PointReq)
    w.processor.provide_text("5")
    assert not w.processor.busy
    lo, hi = g.bbox(w.scene.get(box.id).shape)
    assert hi[2] == pytest.approx(15.0, abs=1e-6)
    w.mark_saved()
    w.close()
