"""B-spline edges are drawn from the sampler's parameters, worked out all at
once rather than asked of the kernel a point at a time, which is what a
.3dm of thousands of curves spent its opening on. They must land where the
kernel would have put them."""

from __future__ import annotations

import math

import numpy as np
from OCP.GCPnts import GCPnts_TangentialDeflection
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCP.TopLoc import TopLoc_Location

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core import occ, tessellate


def _kernel_points(edge, deflection):
    adaptor = occ.edge_adaptor(edge)
    disc = GCPnts_TangentialDeflection(adaptor, tessellate.CURVE_ANGLE,
                                       deflection, 2)
    return np.array([disc.Value(i).Coord()
                     for i in range(1, disc.NbPoints() + 1)])


def _drawn_as_the_kernel_would(shape, deflection=0.01):
    for edge in g.edges_of(shape):
        assert occ.edge_adaptor(edge).GetType() == tessellate._BSPLINE_CURVE
        drawn = tessellate._edge_polyline(edge, deflection)
        expected = _kernel_points(edge, deflection)
        assert drawn.shape == expected.shape
        assert np.allclose(drawn, expected, rtol=0, atol=1e-9)


def test_a_cubic_of_several_spans():
    _drawn_as_the_kernel_would(g.make_nurbs_curve(
        [(0, 0, 0), (2, 3, 0), (5, -1, 1), (7, 4, 2), (9, 0, 0), (12, 2, 1)],
        degree=3, knots=[0, 0, 0, 0, 0.3, 0.7, 1, 1, 1, 1]))


def test_a_rational_quarter_circle():
    w = math.sqrt(0.5)
    _drawn_as_the_kernel_would(g.make_nurbs_curve(
        [(10, 0, 0), (10, 10, 0), (0, 10, 0)], degree=2,
        knots=[0, 0, 0, 1, 1, 1], weights=[1, w, 1]))


def test_an_edge_moved_by_its_location():
    curve = g.make_nurbs_curve(
        [(0, 0, 0), (1, 2, 0), (3, 2, 1), (4, 0, 0)], degree=3,
        knots=[0, 0, 0, 0, 1, 1, 1, 1])
    move = gp_Trsf()
    move.SetRotation(gp_Ax1(gp_Pnt(1, 1, 0), gp_Dir(0, 0, 1)), 0.6)
    shift = gp_Trsf()
    shift.SetTranslation(gp_Vec(100, -40, 7))
    _drawn_as_the_kernel_would(
        curve.Moved(TopLoc_Location(shift.Multiplied(move))))


def test_a_curve_it_cannot_work_out_is_still_drawn(monkeypatch):
    curve = g.make_nurbs_curve(
        [(0, 0, 0), (1, 2, 0), (3, 2, 1), (4, 0, 0)], degree=3,
        knots=[0, 0, 0, 0, 1, 1, 1, 1])
    monkeypatch.setattr(tessellate, "_bspline_points",
                        lambda bs, params: np.full((len(params), 3), np.nan))
    _drawn_as_the_kernel_would(curve)
