"""Text is drawn as a desktop draws it: each glyph is meshed once and a
line is copies of those, so typing and dragging do not refill the whole
text. What is drawn still has to be exactly the saved outlines."""

import numpy as np

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.tessellate import tessellate
from blackbyrd3d.core.text_object import TextShape


def _area(mesh):
    v = np.asarray(mesh.vertices, float)
    t = mesh.triangles
    return 0.5 * np.linalg.norm(
        np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]]),
        axis=1).sum()


def test_the_glyphs_cover_the_outlines_wherever_the_text_is():
    text = g.rotate(TextShape("Bob ate\nap", 6., alignment="center"),
                    (1., 2., 0.), (0., 1., 1.), 40.)
    mesh = tessellate(text)
    assert text.display_mesh() is not None, "text should draw from its glyphs"
    np.testing.assert_allclose(mesh.bounds(), g.bbox(text), atol=1e-2)
    filled = sum(g.surface_area(f) for f in g.faces_of(text.fill()))
    assert abs(_area(mesh) - filled) < 1e-2 * filled


def test_typing_a_letter_reuses_the_glyphs_already_meshed():
    from blackbyrd3d.core import text as lettering
    TextShape("abc", 5.).display_mesh()
    before = len(lettering._glyph_meshes)
    TextShape("abcab", 5.).display_mesh()
    assert len(lettering._glyph_meshes) == before


def test_saved_outlines_the_font_does_not_draw_are_drawn_as_saved():
    saved = TextShape("Hi", 5.)
    other = TextShape("Ho", 5.)
    # outlines of "Hi" under typography that now lays out "Ho", as a file
    # set in a font this machine draws differently would arrive
    loaded = TextShape._from_geometry(other._typography(), saved._frame,
                                      saved._brep)
    assert loaded.display_mesh() is None
    mesh = tessellate(loaded)
    assert len(mesh.triangles)
    np.testing.assert_allclose(mesh.bounds(), g.bbox(saved), atol=1e-2)
