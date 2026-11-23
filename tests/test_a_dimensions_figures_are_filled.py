"""A dimension's figures are drawn filled, as editable text is.

Drawn as their outlines they read as hollow lettering beside text that is
solid, and on a hatch they all but vanish into it.
"""

from __future__ import annotations

import pytest

from blackbyrd3d.core.dimension import DimensionShape
from blackbyrd3d.core.tessellate import tessellate


def _dim(**style):
    return DimensionShape((0, 0, 0), (120, 0, 0), (0, 20, 0),
                          text_height=24, decimals=0, **style)


def test_its_figures_fill_into_faces():
    assert _dim().fill() is not None


def test_a_view_draws_them_filled():
    assert len(tessellate(_dim()).triangles) > 0


def test_without_text_there_is_nothing_to_fill():
    dim = _dim(text=" ")
    assert dim.fill() is None
    assert dim.drawn() is dim


def test_a_click_shows_none_of_its_points():
    """A click on a curve shows its control points. A dimension counts as a
    curve, and asking it for a curve's points crashed every click after it;
    its own three are F10's to show."""
    from blackbyrd3d.core import geometry
    dim = _dim()
    assert not geometry.has_control_points(dim)
    assert len(geometry.get_control_points(dim)) == 3


def test_an_ordinary_curve_still_has_them():
    from blackbyrd3d.core import geometry
    curve = geometry.make_interp_curve([(0, 0, 0), (10, 5, 0), (20, 0, 0)])
    assert geometry.has_control_points(curve)
    assert len(geometry.get_control_points(curve)) >= 3


# -- its three control points and how it scales --------------------------------

def _plain():
    return DimensionShape((0, 0, 0), (100, 0, 0), (0, 30, 0), text_height=5,
                          arrow="tick", arrow_size=3)


def test_f10_shows_the_ends_of_its_line_and_the_middle_below():
    from blackbyrd3d.core import geometry
    assert geometry.get_control_points(_plain()) == [
        (0.0, 30.0, 0.0), (100.0, 30.0, 0.0), (50.0, 0.0, 0.0)]


def test_an_end_slides_its_point_along_and_carries_the_line():
    from blackbyrd3d.core import geometry
    moved = geometry.move_control_point(_plain(), 1, (150, 60, 0))
    assert moved.label == "150.00"
    assert geometry.get_control_points(moved)[1] == (150.0, 60.0, 0.0)


def test_the_middle_lengthens_the_extension_lines():
    from blackbyrd3d.core import geometry
    moved = geometry.move_control_point(_plain(), 2, (50, -20, 0))
    assert moved.label == "100.00"
    assert moved._p1 == (0.0, -20.0, 0.0) and moved._p2 == (100.0, -20.0, 0.0)
    assert geometry.get_control_points(moved)[0] == (0.0, 30.0, 0.0)


def test_the_middle_never_moves_the_dimension_sideways():
    from blackbyrd3d.core import geometry
    moved = geometry.move_control_point(_plain(), 2, (90, -20, 0))
    assert moved._p1 == (0.0, -20.0, 0.0) and moved._p2 == (100.0, -20.0, 0.0)


def test_scale1d_moves_its_points_but_not_its_ticks_or_figures():
    from blackbyrd3d.core import geometry
    out = geometry.scale_along_axis(_plain(), (0, 0, 0), (0, 1, 0), 0.5)
    assert out._at[1] == pytest.approx(15.0)
    assert out._style["text_height"] == 5.0
    assert out._style["arrow_size"] == 3.0


def test_a_uniform_scale_still_grows_its_lettering():
    from blackbyrd3d.core import geometry
    out = geometry.scale(_plain(), (0, 0, 0), 2.0)
    assert out._style["text_height"] == pytest.approx(10.0)


def test_its_points_cannot_be_deleted_or_added_to():
    from blackbyrd3d.core import geometry
    with pytest.raises(geometry.GeometryError):
        geometry.delete_control_points(_plain(), [0])
    with pytest.raises(geometry.GeometryError):
        geometry.insert_knot(_plain(), (50, 30, 0))
