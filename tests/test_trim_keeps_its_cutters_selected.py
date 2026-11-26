"""Objects selected before Trim are its cutters, and they used to go dark
the moment it took them. They stay lit while you click the parts away,
without a gumball on them to catch those clicks."""

import json

import pytest

from blackbyrd3d.commands.base import CommandContext, CommandProcessor
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.history import History
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager

import blackbyrd3d.commands  # noqa: F401


@pytest.fixture
def env():
    scene = Scene()
    sel = SelectionManager(scene)
    ctx = CommandContext(scene, sel, History(scene))
    cutter = scene.add(g.make_line((5, -5, 0), (5, 5, 0)))
    other = scene.add(g.make_line((-5, 0, 3), (5, 0, 3)))   # not touching
    line = scene.add(g.make_line((0, 0, 0), (10, 0, 0)))
    return scene, sel, CommandProcessor(ctx), cutter, other, line


def test_preselected_cutters_stay_selected_while_trimming(env):
    scene, sel, proc, cutter, other, line = env
    sel.set([cutter.id, other.id])
    proc.run("trim")
    assert proc.busy
    assert set(sel.ids) == {cutter.id, other.id}
    proc.click_object(line.id, at=(8, 0, 0))
    assert proc.busy, "asks for the next part"
    assert set(sel.ids) == {cutter.id, other.id}
    assert line.id not in scene.objects
    proc.provide_text("")
    assert not proc.busy


def test_clicked_cutters_stay_selected_too(env):
    _scene, sel, proc, cutter, _other, _line = env
    proc.run("trim")
    proc.click_object(cutter.id)
    proc.finish_selection()
    assert sel.ids == [cutter.id]


def test_a_cutter_trimmed_away_is_no_longer_lit(env):
    scene, sel, proc, cutter, _other, line = env
    sel.set([cutter.id, line.id])
    proc.run("trim")
    proc.click_object(cutter.id, at=(5, 4, 0))
    assert cutter.id not in scene.objects
    assert cutter.id not in sel.ids
    assert line.id in sel.ids


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


def test_no_gumball_on_the_cutters(window):
    cutter = window.scene.add(g.make_line((5, -5, 0), (5, 5, 0)))
    window.scene.add(g.make_line((0, 0, 0), (10, 0, 0)))
    window.selection.set([cutter.id])
    assert window.viewport.gumball.active()
    window.processor.run("trim")
    assert window.selection.ids == [cutter.id]
    assert not window.viewport.gumball.active()
    window.processor.cancel()
    assert window.viewport.gumball.active(), "back once trim is over"
