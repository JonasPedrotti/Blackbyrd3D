"""Model lettering can sit naturally on planes throughout a 3D model."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QPlainTextEdit, QPushButton

from blackbyrd3d.app import MainWindow
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.cplane import CPlane
from blackbyrd3d.core.text import TextShape
from blackbyrd3d.script_runtime import fingerprint


@pytest.fixture
def window():
    w = MainWindow()
    w.resize(1200, 850)
    w.show()
    QApplication.processEvents()
    yield w
    w.processor.cancel()
    w.hide()


def _write_text_at(window, anchor, text="Room label"):
    window.processor.provide(anchor)
    QApplication.processEvents()
    editor = window.viewport.findChild(QPlainTextEdit, "model_text_content")
    assert editor is not None and editor.isVisible(), (
        "Picking the anchor must begin direct editing in the viewport")
    editor.setPlainText(text)
    QApplication.processEvents()
    QTest.keyClick(editor, Qt.Key.Key_Escape)
    QApplication.processEvents()
    obj, = [o for o in window.scene.all() if isinstance(o.shape, TextShape)]
    return obj


def _text_frame(obj):
    frame = np.asarray(obj.shape._frame, dtype=float)
    assert frame.shape == (4, 4)
    return frame


def test_new_model_text_lies_on_the_active_cplane(window):
    cplane = CPlane(origin=(3., 5., 7.), normal=(0., -1., 0.),
                    xdir=(1., 0., 0.))
    window.viewport.cplane = cplane

    window.processor.run("text")
    assert window.findChild(QComboBox, "text_placement_plane") is None, (
        "there is no placement to choose: text goes on the CPlane")
    anchor = (20., 5., 30.)
    obj = _write_text_at(window, anchor)
    frame = _text_frame(obj)
    np.testing.assert_allclose(frame[:3, 3], anchor, atol=1e-7)
    np.testing.assert_allclose(
        frame[:3, :3], np.column_stack((cplane.xdir, cplane.ydir,
                                        cplane.normal)), atol=1e-7)


def test_look_at_text_is_a_reversible_camera_only_action(window):
    normal = np.asarray((1., 2., 3.), dtype=float)
    normal /= np.linalg.norm(normal)
    xdir = np.cross((0., 0., 1.), normal)
    xdir /= np.linalg.norm(xdir)
    plane = CPlane(origin=(12., 18., 24.), normal=normal, xdir=xdir)
    shape = g.apply_matrix(TextShape("Angled label", 6.),
                           plane.basis_matrix())
    obj = window.scene.add(shape, name="Angled label")

    camera = window.viewport.camera
    camera.set_standard_view("front")
    camera.target = np.asarray((-10., 4., 2.))
    camera.distance = 175.
    window.viewport.note_view_change(now=0.)
    before_camera = camera.state()
    before_shape = obj.shape.to_bytes()
    before_scene = fingerprint(window.scene.snapshot())
    before_history = list(window.history._undo)

    window.selection.set([obj.id])
    QApplication.processEvents()
    button = window.findChild(QPushButton, "look_at_text")
    assert button is not None and button.isVisible() and button.isEnabled(), (
        "Selecting angled editable text must expose Look at text")

    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
    QApplication.processEvents()
    assert camera.state() != before_camera
    assert button.text() == "Look at text", "it does one thing"
    window.viewport.note_view_change(now=100.)
    text_origin = _text_frame(obj)[:3, 3]
    toward_camera = camera.position - text_origin
    toward_camera /= np.linalg.norm(toward_camera)
    assert np.dot(toward_camera, normal) > .999999, (
        "Look at text must put the camera squarely in front of its plane")
    assert window.scene.get(obj.id).shape.to_bytes() == before_shape
    assert fingerprint(window.scene.snapshot()) == before_scene
    assert window.history._undo == before_history

    window.processor.run("undoview")
    QApplication.processEvents()
    assert camera.state() == before_camera, (
        "Undo View goes back to the view before, as after any other")
    assert window.scene.get(obj.id).shape.to_bytes() == before_shape
    assert fingerprint(window.scene.snapshot()) == before_scene
    assert window.history._undo == before_history


@pytest.mark.parametrize("turn,face_up", [(0., True), (30., True),
                                         (120., True), (0., False)])
def test_looking_at_flat_text_reads_it_level(window, turn, face_up):
    """Straight down on lettering lying flat, the view still turns so the
    text reads across the screen, not up it."""
    angle = np.radians(turn)
    basis = np.eye(4)
    basis[:3, 0] = (np.cos(angle), np.sin(angle), 0.)
    basis[:3, 1] = (-np.sin(angle), np.cos(angle), 0.)
    if not face_up:
        basis[:3, 1] *= -1.
        basis[:3, 2] = (0., 0., -1.)
    obj = window.scene.add(g.apply_matrix(TextShape("Flat label", 6.), basis))
    window.selection.set([obj.id])
    QApplication.processEvents()
    window._look_at_text()
    vp = window.active_viewport
    frame = _text_frame(obj)
    origin = frame[:3, 3]
    o, up, across = vp.camera.project(
        np.asarray([origin, origin + frame[:3, 1], origin + frame[:3, 0]]),
        vp.width(), vp.height())
    assert abs(up[0] - o[0]) < 1e-6 and up[1] < o[1], "its up is up"
    assert abs(across[1] - o[1]) < 1e-6 and across[0] > o[0], (
        "and it runs left to right")
