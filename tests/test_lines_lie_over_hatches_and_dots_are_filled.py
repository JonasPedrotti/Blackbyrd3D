"""On a flat drawing, lines lie over hatches and the heavier pen over the
lighter, and a dotted hatch's dots are drawn as filled discs.

Lines in one plane fought pixel by pixel for a depth rounding made a little
different along each, and came out dashed where they met: a pane's line on
a spacer's outline, a membrane on a slab's edge. And dots drawn as circles
read as small rings, each cut into hundreds of segments, which was most of
what a dotted hatch cost to draw.
"""

from __future__ import annotations

import time

import pytest

from blackbyrd3d.core import geometry
from blackbyrd3d.core.hatch import HatchShape
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager
from blackbyrd3d.core.tessellate import DOT_SIDES, tessellate
from blackbyrd3d.ui import viewport as vp_mod


def _square(size):
    return geometry.planar_face(geometry.make_rectangle((0, 0, 0),
                                                        (size, size, 0)))


def test_a_dotted_hatchs_dots_are_filled_discs():
    hatch = HatchShape(_square(200), "dots", angle=0, spacing=20)
    mesh = tessellate(hatch)
    dots = len(hatch.dots())
    assert dots
    # its own face first, then a fan of triangles per dot
    region = int((mesh.face_of_triangle == 0).sum())
    assert len(mesh.triangles) - region == dots * DOT_SIDES
    # and each dot's rim, a few sides rather than a few hundred
    assert len(mesh.local_edges) <= dots * DOT_SIDES + 8


def test_a_large_dotted_hatch_tessellates_quickly():
    hatch = HatchShape(_square(2000), "dots", angle=0, spacing=20)
    start = time.perf_counter()
    tessellate(hatch)
    assert time.perf_counter() - start < 2.0


def test_the_hatch_keeps_its_circles_in_the_model():
    hatch = HatchShape(_square(200), "dots", angle=0, spacing=20)
    assert hatch.has_dots
    circles = len(geometry.edges_of(hatch)) - \
        len(geometry.edges_of(hatch.without_dots()))
    assert circles == len(hatch.dots())


@pytest.fixture
def scene_and_view():
    scene = Scene()
    view = vp_mod.Viewport(scene, SelectionManager(scene))
    return scene, view


def _line(scene, layer, x=0.0, width=None):
    obj = scene.add(geometry.make_line((x, 0, 0), (x, 10, 0)),
                    layer_id=layer.id)
    if width is not None:
        scene.update(obj.id, print_width=width)
    return obj


def test_the_heavier_pen_lies_on_top(scene_and_view):
    scene, view = scene_and_view
    layer = scene.layers.create("Lines")
    thin = _line(scene, layer, width=0.18)
    thick = _line(scene, layer, width=0.5)
    ranks = view._line_ranks()
    assert ranks[thick.id] > ranks[thin.id]


def test_between_equal_pens_the_layer_higher_in_the_list_wins(
        scene_and_view):
    scene, view = scene_and_view
    upper = scene.layers.create("Upper")
    lower = scene.layers.create("Lower")
    a = _line(scene, upper, width=0.5)
    b = _line(scene, lower, width=0.5)
    ranks = view._line_ranks()
    assert ranks[a.id] > ranks[b.id]


def test_a_hatch_has_no_rank_and_draws_after_the_lines(scene_and_view):
    scene, view = scene_and_view
    hatch = scene.add(HatchShape(_square(10), "lines", angle=45, spacing=1))
    line = scene.add(geometry.make_line((0, 0, 0), (10, 10, 0)))
    assert hatch.id not in view._line_ranks()
    order = [o.id for o in view._drawn_objects()]
    assert order.index(line.id) < order.index(hatch.id)
