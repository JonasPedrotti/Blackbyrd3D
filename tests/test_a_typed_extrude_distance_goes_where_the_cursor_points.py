"""A typed extrude distance used to run along the normal whatever the cursor
was doing. It takes its way from the cursor, as a typed line length does,
and a negative number goes the other way."""

import json

import pytest

from blackbyrd3d.commands.base import CommandContext, CommandProcessor
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.history import History
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager

import blackbyrd3d.commands  # noqa: F401

UP, DOWN = (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)


def _extrude(aim, text):
    scene = Scene()
    ctx = CommandContext(scene, SelectionManager(scene), History(scene))
    proc = CommandProcessor(ctx)
    circle = scene.add(g.make_circle((0, 0, 0), 5.0))
    proc.run("extrude")
    proc.click_object(circle.id)
    proc.finish_selection()
    ctx.replay_aim = None if aim is None else ((0.0, 0.0, 0.0), aim)
    proc.provide_text(text)
    assert not proc.busy
    solid = scene.all()[-1]
    assert solid.kind == "solid"
    lo, hi = g.bbox(solid.shape)
    return lo[2], hi[2]


@pytest.mark.parametrize("aim, text, expected", [
    (UP, "10", (0, 10)),
    (DOWN, "10", (-10, 0)),
    (UP, "-10", (-10, 0)),
    (DOWN, "-10", (0, 10)),
    (None, "10", (0, 10)),
])
def test_the_cursor_says_which_way(aim, text, expected):
    lo, hi = _extrude(aim, text)
    assert (lo, hi) == pytest.approx(expected, abs=1e-6)


@pytest.fixture
def window(tmp_path, monkeypatch):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({}))
    monkeypatch.setenv("BYRD3D_CONFIG", str(cfg))
    monkeypatch.setenv("BYRD3D_AUTOSAVE_DIR", str(tmp_path / "autosave"))
    from blackbyrd3d.app import MainWindow
    w = MainWindow()
    yield w
    w._saved_revision = w.scene.revision
    w.close()


def test_the_ghost_of_a_typed_number_turns_with_the_cursor(window):
    c = window.scene.add(g.make_circle((0, 0, 0), 5))
    window.selection.set([c.id])
    window.processor.run("extrude")
    window.command_line.input.setText("10")
    shown = []
    for vp in window.all_viewports():
        vp.set_ghost = shown.append
    for aim, top in ((UP, 10.0), (DOWN, 0.0)):
        window.ctx.replay_aim = ((0.0, 0.0, 0.0), aim)
        shown.clear()
        window._show_cursor_ghost((0.0, 0.0, 3.0))
        assert shown and shown[-1] is not None
        assert g.bbox(shown[-1])[1][2] == pytest.approx(top, abs=1e-6)
