"""A curve lying on a mesh's edge is drawn in front of it.

A curve and the edge it lies on have the same depth, so the two fought
for every pixel and the curve came and went along its length. A curve is
drawn a hair nearer than it is, by narrowing the depth range it is drawn
into, for that draw alone. Left narrowed until the next object's edges, it
brought the faces drawn in between forward too: a mesh after a curve hid
its own edges, and what stood behind showed through what was in front.
"""

from __future__ import annotations

import numpy as np

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.mesh import MeshShape
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.ui import gpu_share
from blackbyrd3d.ui import viewport as vp_mod


class _GL:
    def __init__(self):
        self.ranges = []
        self.events = []
        self.names = {}
        self.program = 0

    def __getattr__(self, name):
        if name.startswith("GL_"):
            return self.names.setdefault(name, len(self.names) + 1)
        if name == "glDepthRange":
            def depth_range(near, far):
                self.ranges.append((near, far))
                self.events.append(("range", far))
            return depth_range
        if name == "glUseProgram":
            def use(prog):
                self.program = prog
            return use
        if name == "glDrawElements":
            def draw(mode, *a):
                # a curve's quads are triangles too, through its own program
                if mode == self.GL_TRIANGLES and self.program == 11:
                    self.events.append(("triangles", None))
            return draw
        return lambda *a, **k: 0


def _draw(monkeypatch, scene):
    gl = _GL()
    monkeypatch.setattr(vp_mod, "GL", gl)
    monkeypatch.setattr(vp_mod, "_current_share_group", lambda: None)
    gpu_share.reset()
    try:
        view = vp_mod.Viewport(scene, SelectionManager(scene))
        view.resize(800, 600)
        view._mesh_prog, view._line_prog = 11, 12
        view._thick_prog, view._point_prog = 13, 14
        view._max_line_width = 10.0
        for obj in scene.all():
            obj.mesh
        view._sync_gpu()
        view.zoom_extents()
        w, h = view.width(), view.height()
        v = view.camera.view_matrix()
        view._draw_objects(view.camera.proj_matrix(w, h) @ v, v)
    finally:
        gpu_share.reset()
    return gl


def _mesh():
    v = np.array([(0, 0, 0), (10, 0, 0), (10, 10, 3)], float)
    return MeshShape(v, [[0, 1, 2]], faceted=True)


def test_curves_are_drawn_nearer_and_the_range_is_put_back(_qapp,
                                                           monkeypatch):
    scene = Scene()
    scene.add(_mesh())
    for i in range(3):
        scene.add(g.make_line((0, i, 0), (10, i, 0)))
    gl = _draw(monkeypatch, scene)
    nearer = [r for r in gl.ranges if r[1] < 1.0]
    assert nearer, "no curve was drawn nearer"
    assert nearer[0][1] == 1.0 - vp_mod.CURVE_DEPTH_NUDGE
    assert gl.ranges[-1] == (0.0, 1.0), "the range was left narrowed"


def test_a_mesh_after_a_curve_is_not_drawn_nearer(_qapp, monkeypatch):
    scene = Scene()
    scene.add(g.make_line((0, 0, 0), (10, 0, 0)))
    scene.add(_mesh())
    gl = _draw(monkeypatch, scene)
    narrowed = False
    for kind, far in gl.events:
        if kind == "range":
            narrowed = far < 1.0
        else:
            assert not narrowed, "triangles drawn in a curve's depth range"
    assert any(k == "range" for k, _ in gl.events), "no curve was drawn"
