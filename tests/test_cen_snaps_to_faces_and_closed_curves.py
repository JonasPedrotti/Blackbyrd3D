"""Cen finds the middle of faces and of closed curves, and the centroid
command places a point at an object's area or volume centroid."""

import pytest

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.snaps import _static_snap_points


def _centers(shape):
    return sorted({tuple(round(c, 6) for c in p)
                   for p, kind in _static_snap_points(shape)
                   if kind == "center"})


def test_a_rectangle_offers_its_middle():
    assert _centers(g.make_rectangle((0, 0, 0), (4, 2, 0))) == [(2, 1, 0)]


def test_a_planar_surface_offers_its_middle():
    srf = g.planar_face(g.make_rectangle((0, 0, 0), (4, 2, 0)))
    assert _centers(srf) == [(2, 1, 0)]


def test_every_face_of_a_box_offers_its_middle():
    centers = _centers(g.make_box((0, 0, 0), 2, 2, 2))
    assert centers == sorted([(1, 1, 0), (1, 1, 2), (0, 1, 1), (2, 1, 1),
                              (1, 0, 1), (1, 2, 1)])


def test_a_circle_still_offers_its_center():
    assert _centers(g.make_circle((1, 1, 0), 3)) == [(1, 1, 0)]


def test_an_open_curve_has_no_center():
    assert _centers(g.make_polyline([(0, 0, 0), (1, 0, 0), (1, 1, 0)])) == []


def _points(scene):
    return [o for o in scene.objects.values()
            if g.shape_kind(o.shape) == "point"]


@pytest.mark.parametrize("shape, expected", [
    (lambda: g.make_box((0, 0, 0), 2, 4, 6), (1, 2, 3)),
    (lambda: g.planar_face(g.make_rectangle((0, 0, 0), (4, 2, 0))), (2, 1, 0)),
    (lambda: g.make_rectangle((2, 2, 0), (6, 4, 0)), (4, 3, 0)),
])
def test_centroid_places_a_point(env, shape, expected):
    scene, selection, _history, ctx, proc = env
    oid = ctx.add(shape()).id
    selection.set([oid])
    proc.run("centroid")
    assert not proc.busy
    (pt,) = _points(scene)
    assert g.point_coords(pt.shape) == pytest.approx(expected, abs=1e-6)


def test_an_open_curve_has_no_centroid(env):
    scene, selection, _history, ctx, proc = env
    oid = ctx.add(g.make_polyline([(0, 0, 0), (1, 0, 0), (1, 1, 0)])).id
    selection.set([oid])
    proc.run("centroid")
    assert _points(scene) == []
