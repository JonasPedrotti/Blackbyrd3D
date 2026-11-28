"""A curve behind a face is hidden by it, however many layers the drawing has.

Curves are drawn a hair nearer than they are, so one lying on an edge wins
the tie, and lines lying on each other are ranked by pen and layer, each
rank a little nearer still. Each rank was a whole nudge, and every layer
took one, hidden ones too: in a church survey of 42 layers a curve on
Default stood 3% of the view distance in front of where it was, and the
eaves' outlines showed through the roof (Petersbergkirche).

That was half of it. The near plane stood at a thousandth of the zoom, and
depth coarsens with the square of the distance past it, so 22 m off even
the smallest nudge was 2 cm, and the cornice's outline 4 cm under the roof
still showed. The near plane now comes forward to what is drawn nearest.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.ui import viewport as vp_mod


def _ranked_scene(layers: int, hidden: int = 0):
    scene = Scene()
    for i in range(layers + hidden):
        layer = scene.layers.create(f"L{i}")
        if i >= layers:
            scene.layers.set_visible(layer.id, False)
        scene.add(g.make_line((i, 0, 0), (i, 1, 0)),
                  layer_id=layer.id)
    return scene


def test_hidden_layers_take_no_rank(_qapp):
    scene = _ranked_scene(3, hidden=40)
    view = vp_mod.Viewport(scene, SelectionManager(scene))
    ranks = view._line_ranks()
    assert max(ranks.values()) == 2


def test_the_top_rank_stays_close_to_the_faces(_qapp):
    assert vp_mod.line_nudge(vp_mod.MAX_LINE_RANK) < 25 * \
        vp_mod.CURVE_DEPTH_NUDGE
    assert vp_mod.line_nudge(1) - vp_mod.line_nudge(0) > 2e-7, \
        "ranks closer than the fringe bias of a wide line"


@pytest.fixture
def window(_qapp):
    from blackbyrd3d.app import MainWindow
    w = MainWindow()
    w.set_view_layout("single")
    w.resize(900, 700)
    w.show()
    vp = w.viewport
    vp.grabFramebuffer()
    if not (vp.isValid() and getattr(vp, "_mesh_prog", 0)):
        w.mark_saved()
        w.close()
        pytest.skip("no GL 3.3 to draw with here (CI runs offscreen)")
    yield w, vp
    w.mark_saved()
    w.close()


def test_a_curve_on_a_top_ranked_layer_behind_a_face_is_hidden(window):
    w, vp = window
    scene = w.scene
    # the lines that give the drawing its ranks, off to the side: as many
    # as the church survey has in sight
    for i in range(16):
        layer = scene.layers.create(f"Lines {i}")
        scene.add(g.make_line((200 + i, 0, 0), (200 + i, 10, 0)),
                  layer_id=layer.id)
    face = scene.add(g.planar_face(g.make_polyline(
        [(-50, -50, 0), (50, -50, 0), (50, 50, 0), (-50, 50, 0)],
        closed=True)))
    scene.update(face.id, color=(1.0, 0.0, 0.0))
    vp.set_view("perspective")
    # looked at steeply, as the roof was: a face is drawn a pixel's worth
    # of its own slope deeper, so its edges lie over it, and a grazing
    # view makes that pixel a deep one
    vp.camera.elevation = math.radians(60.0)
    vp.zoom_extents()
    assert vp.camera.projection == "perspective"
    # 0.3% of the view distance behind the face, along the line of sight:
    # the cornice under the church's roof was 0.2% at 22 m
    on_face = np.array([10.0, 0.0, 0.0])
    eye = np.asarray(vp.camera.position, float)
    sight = (on_face - eye) / np.linalg.norm(on_face - eye)
    behind = on_face + sight * 0.003 * vp.camera.distance
    top = scene.layers.all()[0]
    curve = scene.add(g.make_line(behind - (30, 0, 0), behind + (30, 0, 0)),
                      layer_id=top.id)
    scene.update(curve.id, color=(0.0, 0.0, 1.0))
    scene.notify()
    assert vp._line_ranks()[curve.id] >= 15, "the test needs a high rank"
    image = vp.grabFramebuffer()
    (x, y, _w), = vp.camera.project(np.asarray([behind]),
                                    vp.width(), vp.height())
    scale = image.width() / max(vp.width(), 1)
    pixel = image.pixelColor(int(round(x * scale)), int(round(y * scale)))
    assert not (pixel.blue() > 150 and pixel.red() < 100), \
        f"the curve shows through the face: {pixel.name()}"


def test_the_near_plane_comes_forward_to_what_is_drawn():
    from blackbyrd3d.ui.camera import Camera
    cam = Camera()
    cam.distance = 22.0
    box = np.array([[[-5.0, -5.0, -5.0], [5.0, 5.0, 5.0]]])
    cam.object_boxes = box
    cam.scene_bounds = cam.drawing_bounds = (tuple(box[0, 0]),
                                             tuple(box[0, 1]))
    near, _far = cam.clip_planes()
    clearance = cam._clearance(cam.position)
    assert clearance > 10.0
    assert near == pytest.approx(0.5 * clearance)


def test_an_eye_inside_something_keeps_the_near_plane_close():
    from blackbyrd3d.ui.camera import Camera
    cam = Camera()
    cam.distance = 22.0
    box = np.array([[[-100.0, -100.0, -100.0], [100.0, 100.0, 100.0]]])
    cam.object_boxes = box
    cam.scene_bounds = cam.drawing_bounds = (tuple(box[0, 0]),
                                             tuple(box[0, 1]))
    near, _far = cam.clip_planes()
    assert near == pytest.approx(22.0 * 0.001)


def _grab_at(vp, point):
    image = vp.grabFramebuffer()
    (x, y, _w), = vp.camera.project(np.asarray([point], float),
                                    vp.width(), vp.height())
    scale = image.width() / max(vp.width(), 1)
    return image.pixelColor(int(round(x * scale)), int(round(y * scale)))


def _box_behind_a_wall(window, select: bool):
    w, vp = window
    scene = w.scene
    box = scene.add(g.make_box((-10, -10, -10), 20, 20, 20))
    wall = scene.add(g.planar_face(g.make_polyline(
        [(-40, -40, 30), (40, -40, 30), (40, 40, 30), (-40, 40, 30)],
        closed=True)))
    scene.update(wall.id, color=(0.15, 0.15, 0.8))
    vp.set_view("top")
    vp.zoom_extents()
    if select:
        w.selection.set([box.id])
    scene.notify()
    # on the box's top edge, clear of the gumball's arrows
    return _grab_at(vp, (-10.0, -5.0, 10.0))


def test_a_selected_object_shows_its_outline_through_what_hides_it(window):
    pixel = _box_behind_a_wall(window, select=True)
    assert pixel.red() > pixel.blue(), \
        f"no gold where the selected box is hidden: {pixel.name()}"


def test_an_object_not_selected_stays_hidden(window):
    pixel = _box_behind_a_wall(window, select=False)
    assert pixel.red() < pixel.blue(), \
        f"the box shows through: {pixel.name()}"
