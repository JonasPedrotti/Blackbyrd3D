"""The gumball's pivot can be relocated, and reset.

Right-click the gumball's centre for Relocate gumball: the gumball follows
the cursor, snapping where the object snaps are, and a click sets it down.
It stays there for these objects, carried along by a gumball move, and
rotates and scales about the new place. Reset gumball, Escape while
relocating, or picking something else puts it back in the middle.
"""

import numpy as np
import pytest
from PySide6.QtCore import Qt

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.ui.viewport import Viewport


@pytest.fixture
def held():
    scene = Scene()
    sel = SelectionManager(scene)
    vp = Viewport(scene, sel)
    vp.resize(400, 300)
    box = scene.add(g.make_box((0, 0, 0), 2, 2, 2))
    sel.set([box.id])
    return vp, sel, box


def _pixel(vp, point):
    x, y, _ = np.asarray(vp._eye().project(
        np.array([point], float), vp.width(), vp.height()), float)[0]
    return float(x), float(y)


def _anchor(vp):
    return np.asarray(vp.gumball.anchor_and_axes()[0], float)


def _relocate(vp, point):
    gb = vp.gumball
    assert gb.start_relocate()
    assert gb.relocating
    gb.finish_relocate(*_pixel(vp, point))
    assert not gb.relocating


def test_a_click_sets_the_gumball_down_where_the_cursor_is(held):
    vp, _sel, _box = held
    assert _anchor(vp) == pytest.approx((1, 1, 1))
    _relocate(vp, (6, 5, 1))
    assert _anchor(vp) == pytest.approx((6, 5, 1), abs=1e-6)


def test_it_snaps_to_what_the_object_snaps_offer(held):
    vp, _sel, _box = held
    _relocate(vp, (2, 2, 2))
    assert _anchor(vp) == pytest.approx((2, 2, 2), abs=1e-9)


def test_reset_puts_it_back_in_the_middle(held):
    vp, _sel, _box = held
    _relocate(vp, (6, 5, 1))
    vp.gumball.reset_pivot()
    assert _anchor(vp) == pytest.approx((1, 1, 1))


def test_escape_while_relocating_puts_it_back(held):
    vp, _sel, _box = held
    _relocate(vp, (6, 5, 1))
    gb = vp.gumball
    gb.start_relocate()
    gb.relocate_to(*_pixel(vp, (-4, -4, 1)))
    gb.cancel_relocate()
    assert _anchor(vp) == pytest.approx((6, 5, 1), abs=1e-6)


def test_picking_something_else_forgets_it(held):
    vp, sel, box = held
    _relocate(vp, (6, 5, 1))
    other = vp.scene.add(g.make_box((10, 0, 0), 2, 2, 2))
    sel.set([other.id])
    sel.set([box.id])
    assert _anchor(vp) == pytest.approx((1, 1, 1))


def test_a_gumball_move_carries_it_along(held):
    vp, _sel, box = held
    _relocate(vp, (6, 5, 1))
    gb = vp.gumball
    _anchor_now, axes = gb.anchor_and_axes()
    assert gb.begin_drag(("move", 0), *_pixel(vp, (7, 5, 1)),
                         Qt.KeyboardModifier.NoModifier)
    gb.apply_scalar(3.0)
    gb.end_drag()
    moved = np.asarray((6, 5, 1)) + 3.0 * np.asarray(axes[0], float)
    assert _anchor(vp) == pytest.approx(moved, abs=1e-6)
    assert np.asarray(g.bbox(vp.scene.get(box.id).shape)[0]) == \
        pytest.approx(3.0 * np.asarray(axes[0], float), abs=1e-6)


def test_it_turns_about_the_relocated_pivot(held):
    vp, _sel, box = held
    _relocate(vp, (2, 2, 0))
    gb = vp.gumball
    assert gb.begin_drag(("rot", 2), *_pixel(vp, (3, 2, 0)),
                         Qt.KeyboardModifier.NoModifier)
    gb.apply_scalar(180.0)
    gb.end_drag()
    lo, hi = g.bbox(vp.scene.get(box.id).shape)
    assert lo == pytest.approx((2, 2, 0), abs=1e-6)
    assert hi == pytest.approx((4, 4, 2), abs=1e-6)
    assert _anchor(vp) == pytest.approx((2, 2, 0), abs=1e-6)


def test_a_held_face_offers_no_relocation(held):
    vp, sel, box = held
    sel.subobjects = [(box.id, "face", 0)]
    assert vp.gumball._pivot_key() is None
    assert not vp.gumball.start_relocate()


def test_the_menu_offers_relocate_and_reset(held):
    vp, _sel, _box = held
    menu = vp.gumball.open_menu(10, 10)
    labels = {a.text(): a.isEnabled() for a in menu.actions() if a.text()}
    assert labels["Relocate gumball"] is True
    assert labels["Reset gumball"] is False
    menu.close()


def test_escape_to_the_window_cancels_relocating_and_keeps_the_selection():
    from blackbyrd3d.app import MainWindow
    w = MainWindow()
    box = w.ctx.add(g.make_box((0, 0, 0), 2, 2, 2))
    w.selection.set([box.id])
    gb = w.viewport.gumball
    assert gb.start_relocate()
    w._cancel()
    assert not gb.relocating
    assert w.selection.ids == [box.id]
    w.mark_saved()
    w.close()


def test_ctrl_click_on_the_centre_relocates_at_once(held):
    vp, _sel, _box = held
    gb = vp.gumball
    assert gb.begin_drag(("center", 0), *_pixel(vp, (1, 1, 1)),
                         Qt.KeyboardModifier.ControlModifier)
    assert gb.relocating
    assert gb.drag is None
    gb.finish_relocate(*_pixel(vp, (6, 5, 1)))
    assert _anchor(vp) == pytest.approx((6, 5, 1), abs=1e-6)


def test_ctrl_click_through_the_viewport_relocates(held):
    from PySide6.QtCore import QPointF
    from PySide6.QtTest import QTest
    vp, _sel, _box = held
    vp.show()
    at = QPointF(*_pixel(vp, (1, 1, 1))).toPoint()
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.ControlModifier, at)
    assert vp.gumball.relocating
    to = QPointF(*_pixel(vp, (6, 5, 1))).toPoint()
    QTest.mouseMove(vp, to)
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier, to)
    assert not vp.gumball.relocating
    assert _anchor(vp) == pytest.approx((6, 5, 1), abs=0.05)
    vp.close()


def _at(vp, point):
    from PySide6.QtCore import QPointF
    return QPointF(*_pixel(vp, point)).toPoint()


def test_a_double_click_on_the_centre_relocates(held):
    from PySide6.QtTest import QTest
    vp, _sel, box = held
    vp.show()
    QTest.mouseDClick(vp, Qt.MouseButton.LeftButton,
                      Qt.KeyboardModifier.NoModifier, _at(vp, (1, 1, 1)))
    assert vp.gumball.relocating
    assert g.bbox(vp.scene.get(box.id).shape)[0] == pytest.approx((0, 0, 0),
                                                           abs=1e-6)
    to = _at(vp, (6, 5, 1))
    QTest.mouseMove(vp, to)
    QTest.mouseClick(vp, Qt.MouseButton.LeftButton,
                     Qt.KeyboardModifier.NoModifier, to)
    assert not vp.gumball.relocating
    assert _anchor(vp) == pytest.approx((6, 5, 1), abs=0.05)
    vp.close()


def test_a_ctrl_double_click_on_the_centre_resets(held):
    from PySide6.QtTest import QTest
    vp, _sel, _box = held
    vp.show()
    _relocate(vp, (6, 5, 1))
    QTest.mouseDClick(vp, Qt.MouseButton.LeftButton,
                      Qt.KeyboardModifier.ControlModifier, _at(vp, (6, 5, 1)))
    assert not vp.gumball.relocating
    assert _anchor(vp) == pytest.approx((1, 1, 1))
    vp.close()
