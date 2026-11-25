from blackbyrd3d.core.snaps import SNAP_TYPES
from blackbyrd3d.ui.viewport import _SNAP_LABELS


def test_every_snap_but_near_has_a_name():
    for kind in SNAP_TYPES:
        if kind == "near":
            assert kind not in _SNAP_LABELS
        else:
            assert _SNAP_LABELS.get(kind)


def test_perp_reaches_every_side_of_a_polyline():
    import numpy as np
    from blackbyrd3d.core import geometry as g
    from blackbyrd3d.core.scene import Scene
    from blackbyrd3d.core.snaps import SnapIndex
    from blackbyrd3d.ui.camera import Camera
    size = (900, 700)
    cam = Camera()
    cam.set_standard_view("top")
    cam.target = np.zeros(3)
    cam.distance = 40.0
    scene = Scene()
    scene.add(g.make_polyline([(0, 0, 0), (10, 0, 0), (10, 10, 0),
                               (0, 10, 0)]))
    index = SnapIndex(scene)
    index.types = {k: k == "perp" for k in SNAP_TYPES}
    for foot in ((5.0, 0.0, 0.0), (10.0, 2.0, 0.0), (5.0, 10.0, 0.0)):
        px, py = cam.project(np.asarray([foot], float), *size)[0, :2]
        hit = index.find(cam, px + 2, py + 2, *size, base_point=(5, 2, 0))
        assert hit is not None and hit[1] == "perp"
        assert np.allclose(hit[0], foot)
