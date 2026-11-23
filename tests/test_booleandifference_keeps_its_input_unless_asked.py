"""BooleanDifference has a DeleteInput option, No by default: the solid is
cut in place either way, and No keeps what it was cut with. The tool's
right click runs it with Yes."""

from __future__ import annotations

from blackbyrd3d.commands import CommandContext, CommandProcessor
from blackbyrd3d.core import geometry
from blackbyrd3d.core.history import History
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager


def _setup():
    scene = Scene()
    selection = SelectionManager(scene)
    proc = CommandProcessor(CommandContext(scene, selection, History(scene)))
    block = scene.add(geometry.make_box((0, 0, 0), 10, 10, 10), name="Block")
    tool = scene.add(geometry.make_box((5, 5, 5), 10, 10, 10), name="Tool")
    return scene, proc, block, tool


def _subtract(proc, block, tool, *options):
    proc.run(" ".join(("booleandifference", *options)))
    proc.click_object(block.id)
    proc.provide_text("")
    proc.click_object(tool.id)
    proc.provide_text("")


def test_by_default_it_cuts_in_place_and_keeps_the_tool():
    scene, proc, block, tool = _setup()
    _subtract(proc, block, tool)
    assert scene.get(tool.id) is not None
    assert len(scene.all()) == 2, "a copy of the solid was left standing"
    assert geometry.volume(scene.get(block.id).shape) < 1000.0 - 1e-6


def test_delete_input_yes_cuts_in_place_and_removes_the_tool():
    scene, proc, block, tool = _setup()
    _subtract(proc, block, tool, "DeleteInput=Yes")
    assert scene.get(tool.id) is None
    assert len(scene.all()) == 1
    assert geometry.volume(scene.get(block.id).shape) < 1000.0 - 1e-6


def test_the_toolbar_right_click_deletes_the_input(monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QToolButton

    from blackbyrd3d.app import MainWindow
    monkeypatch.setenv("BYRD3D_NO_RPC", "1")
    win = MainWindow()
    try:
        button = next(b for b in win.findChildren(QToolButton)
                      if b.toolTip().startswith("<table")
                      and "booleandifference" in b.toolTip())
        button.customContextMenuRequested.emit(QPoint(1, 1))
        proc = win.processor
        assert proc.active is not None
        assert proc.active.name == "booleandifference"
        assert proc.option("DeleteInput", "No") == "Yes"
        proc.cancel()
    finally:
        win.mark_saved()
        win.close()
