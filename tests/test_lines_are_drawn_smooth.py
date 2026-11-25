"""Curves are drawn as quads with a faded edge, not as stepped GL_LINES.

A one pixel GL_LINES line steps like a staircase, and 4x multisampling only
softens it a little. Curves, edges and isocurves now go through the quad
shader at every width, which fades each line's edge over a pixel.
"""

from __future__ import annotations

import numpy as np

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.ui import gpu_share
from blackbyrd3d.ui import viewport as vp_mod

THICK = 13


class _GL:
    def __init__(self):
        self.names = {}
        self.program = 0
        self.draws = []

    def __getattr__(self, name):
        if name.startswith("GL_"):
            return self.names.setdefault(name, len(self.names) + 1)
        if name == "glUseProgram":
            def use(prog):
                self.program = prog
            return use
        if name in ("glDrawElements", "glDrawArrays"):
            def draw(mode, *a):
                self.draws.append((name, mode, self.program))
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
        view._thick_prog, view._point_prog = THICK, 14
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


def test_a_hairline_curve_goes_through_the_quad_shader(_qapp, monkeypatch):
    scene = Scene()
    scene.add(g.make_polyline([(0, 0, 0), (10, 1, 0), (7, -6, 0)]))
    gl = _draw(monkeypatch, scene)
    assert any(name == "glDrawElements" and prog == THICK
               for name, _mode, prog in gl.draws), "the curve was not drawn"
    assert not any(mode == gl.GL_LINES for _name, mode, _prog in gl.draws), \
        "a curve was drawn as stepped GL_LINES"


def test_the_far_end_of_a_quad_is_corners_two_and_three():
    """The shader flips its sense of side at corners 2 and 3, where the
    normal turns round; the quads have to be laid out that way."""
    a, b = np.array([1.0, 2.0, 3.0]), np.array([4.0, 5.0, 6.0])
    flat, idx = vp_mod._thick_arrays(np.array([[a, b]]))
    assert np.allclose(flat[0:2, :3], a) and np.allclose(flat[2:4, :3], b)
    assert "gl_VertexID & 2" in vp_mod.THICK_VERT
