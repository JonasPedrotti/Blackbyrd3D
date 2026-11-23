"""Three things about where a snap lands.

A stretch held to an axis snaps where that axis runs into an edge, though
neither edge touches it; Near lands under the cursor in perspective, where
it used to slide down a long edge running away from the eye; and Mid under
the cursor wins over an End a few pixels further off.
"""

from __future__ import annotations

import numpy as np

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.core.snaps import SNAP_TYPES, SnapIndex


def _vp(scene, view):
    from blackbyrd3d.ui.viewport import Viewport
    vp = Viewport(scene, SelectionManager(scene))
    vp.resize(900, 700)
    vp.camera.target = np.zeros(3)
    vp.camera.distance = 80.0
    vp.camera.set_standard_view(view)
    vp.camera._vp_cache = None
    return vp


def _index(scene, *on):
    idx = SnapIndex(scene)
    for t in SNAP_TYPES:
        idx.types[t] = t in on
    return idx


def _px(vp, world):
    scr = vp.camera.project(np.asarray([world], float), vp.width(),
                            vp.height())[0]
    return float(scr[0]), float(scr[1])


def test_the_axis_snaps_where_it_runs_into_an_edge():
    scene = Scene()
    # an upright edge off to the side, behind the axis's line in depth
    scene.add(g.make_line((10, 5, -10), (10, 5, 10)))
    vp = _vp(scene, "front")
    idx = _index(scene, "int")
    px, py = _px(vp, (10, 5, 2))
    base, axis = np.array([0.0, 0.0, 2.0]), np.array([1.0, 0.0, 0.0])
    assert idx.find(vp.camera, px, py, vp.width(), vp.height()) is None
    snap = idx.find(vp.camera, px, py, vp.width(), vp.height(),
                    along=(base, axis))
    assert snap is not None and snap[1] == "int"
    assert np.allclose(snap[0], (10.0, 0.0, 2.0), atol=1e-6)


def test_near_lands_under_the_cursor_in_perspective():
    scene = Scene()
    scene.add(g.make_line((0, -40, 0), (0, 60, 0)))   # running away
    vp = _vp(scene, "perspective")
    idx = _index(scene, "near")
    target = (0.0, 30.0, 0.0)
    px, py = _px(vp, target)
    snap = idx.find(vp.camera, px, py, vp.width(), vp.height())
    assert snap is not None and snap[1] == "near"
    back = _px(vp, snap[0])
    assert abs(back[0] - px) < 0.5 and abs(back[1] - py) < 0.5


def test_mid_under_the_cursor_beats_an_end_a_few_pixels_off():
    scene = Scene()
    scene.add(g.make_line((0, 0, 0), (1.2, 0, 0)))    # short on screen
    vp = _vp(scene, "top")
    idx = _index(scene, "end", "mid")
    px, py = _px(vp, (0.6, 0, 0))
    end_px = _px(vp, (0, 0, 0))
    assert 5 < abs(end_px[0] - px) < 12              # the end is in range
    snap = idx.find(vp.camera, px, py, vp.width(), vp.height())
    assert snap[1] == "mid"


def test_an_end_still_wins_when_it_is_about_as_near():
    scene = Scene()
    scene.add(g.make_line((0, 0, 0), (40, 0, 0)))
    vp = _vp(scene, "top")
    idx = _index(scene, "end", "mid")
    px, py = _px(vp, (0, 0, 0))
    snap = idx.find(vp.camera, px + 1.0, py, vp.width(), vp.height())
    assert snap[1] == "end"
