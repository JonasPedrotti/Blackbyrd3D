"""Text in a Rhino model comes in as editable text, lettered where Rhino
lettered it, whether the .3dm is imported or its objects pasted. The data
file is what Rhino 7 put on the clipboard for an extrusion, a polyline and
a text copied out of a metre drawing."""

from pathlib import Path

import numpy as np
import pytest

from blackbyrd3d import fileio
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.text_object import TextShape

DATA = Path(__file__).parent / "data" / "rhino_model_text_v7.3dm"


def _imported():
    scene = Scene()
    fileio.import_file(scene, str(DATA))
    return scene


# Where Rhino 7 says the text is, in metres. Not asked of rhino3dm: on
# Linux it measures text with fonts of its own and puts it elsewhere.
RHINO_BOX = ((16.343975, 12.703926), (22.218975, 13.720231))


def test_rhino_text_is_imported_as_editable_text_alongside_the_rest():
    scene = _imported()
    texts = [o for o in scene.all() if isinstance(o.shape, TextShape)]
    assert len(scene.all()) == 3, "the extrusion and the polyline as before"
    text, = texts
    assert text.shape.text == "asdasdad"
    assert text.shape.font_family == "Arial"


def _rhino3dm_measures_text():
    import rhino3dm
    model = rhino3dm.File3dm.Read(str(DATA))
    text = next(o.Geometry for o in model.Objects
                if isinstance(o.Geometry, rhino3dm.Text))
    box = text.GetBoundingBox()
    return box.Min.X <= box.Max.X


@pytest.mark.skipif(not _rhino3dm_measures_text(),
                    reason="rhino3dm has no fonts to measure text with here")
def test_rhino_text_sits_where_rhino_lettered_it():
    scene = _imported()
    text = next(o.shape for o in scene.all() if isinstance(o.shape, TextShape))
    lo, hi = np.array(RHINO_BOX) * 1000.           # metres, read into mm
    corners = text.frame_box()[:, :2]
    np.testing.assert_allclose(corners.min(axis=0), lo, atol=1.)
    assert corners.max(axis=0)[0] == pytest.approx(hi[0], abs=1.)
    # Rhino's box stands a little above the tallest letter
    assert corners.max(axis=0)[1] == pytest.approx(hi[1], rel=0.01)


def test_text_rhino3dm_cannot_measure_hangs_from_its_plane(monkeypatch):
    """On Linux rhino3dm returns an empty box for text, as it measures it
    with fonts it does not have there."""
    import rhino3dm
    empty = rhino3dm.BoundingBox(1., 0., 0., -1., 0., 0.)
    monkeypatch.setattr(rhino3dm.Text, "GetBoundingBox",
                        lambda self: empty)
    scene = _imported()
    text = next(o.shape for o in scene.all() if isinstance(o.shape, TextShape))
    corners = text.frame_box()[:, :2]
    origin = np.array([16.2951, 13.7202]) * 1000.   # the text's plane, in mm
    np.testing.assert_allclose([corners[:, 0].min(), corners[:, 1].max()],
                               origin, atol=1.)
    assert np.all(np.isfinite(corners))


def test_text_survives_the_trip_from_a_parallel_import_worker():
    from blackbyrd3d.fileio.rhino_parallel import _decode, _encode
    sent = TextShape("Hello", 5., alignment="center")
    received = _decode(_encode(sent))
    assert isinstance(received, TextShape)
    assert (received.text, received.alignment) == ("Hello", "center")
