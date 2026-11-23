"""A rectangle, plane, box base or circle begun on something above the
CPlane is drawn at that height.

The second corner came from where the cursor's ray met the CPlane at
height zero, which in perspective is far off below and behind: the shape
shot out to it. Its later points lie on the plane through its first one,
level with the CPlane, as Rhino's do, and the grid still holds there.
"""

from __future__ import annotations

import numpy as np

from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager


def _vp():
    from blackbyrd3d.ui.viewport import Viewport
    scene = Scene()
    vp = Viewport(scene, SelectionManager(scene))
    vp.resize(900, 700)
    vp.camera.target = np.array([0.0, 0.0, 100.0])
    vp.camera.distance = 400.0
    vp.camera.set_standard_view("perspective")
    vp.camera._vp_cache = None
    vp.snaps.enabled = False
    return vp


def test_the_next_corner_is_at_the_height_of_the_first():
    vp = _vp()
    vp.point_plane = ((0.0, 0.0, 100.0), (0.0, 0.0, 1.0))
    p = vp._point_at(500, 300)
    assert p is not None and abs(p[2] - 100.0) < 1e-6
    assert np.linalg.norm(p[:2]) < 500, "not shot off into the distance"


def test_the_grid_still_holds_up_there():
    vp = _vp()
    vp.point_plane = ((0.0, 0.0, 100.0), (0.0, 0.0, 1.0))
    vp.grid_snap = True
    vp.grid_snap_step = 10.0
    p = vp._point_at(517, 311)
    assert abs(p[2] - 100.0) < 1e-6
    assert all(abs(c / 10.0 - round(c / 10.0)) < 1e-9 for c in p[:2])


def test_a_plane_turned_from_the_cplane_still_picks_on_itself():
    vp = _vp()
    vp.point_plane = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
    p = vp._point_at(450, 350)
    assert p is not None and abs(p[0]) < 1e-6
