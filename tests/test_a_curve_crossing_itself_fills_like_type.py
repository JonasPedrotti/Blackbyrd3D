"""Font outlines may cross themselves where a stem meets a bowl; a
rasteriser fills them by the nonzero winding rule, and a letter filled
from them has to be filled the same way or it is not drawn at all."""

import pytest

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.tessellate import tessellate


# One loop over the 3 x 3 square, crossing itself at (2, 1). It winds
# round [1, 2] x [1, 2] twice and leaves [2, 3] x [0, 1] out.
CROSSING = [(0, 0, 0), (2, 0, 0), (2, 2, 0), (1, 2, 0), (1, 1, 0),
            (3, 1, 0), (3, 3, 0), (0, 3, 0)]


def test_a_self_crossing_outline_fills_everything_it_winds_round():
    faces = g.planar_regions([g.make_polyline(CROSSING, closed=True)])
    assert sum(g.surface_area(f) for f in faces) == pytest.approx(8.)


def test_a_self_crossing_outline_is_drawn():
    faces = g.planar_regions([g.make_polyline(CROSSING, closed=True)])
    mesh = tessellate(g.make_compound(faces))
    assert len(mesh.triangles)
