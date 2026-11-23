"""SelPrev brings back what the last command drew.

A drawing command lets go of what it made, as Rhino's do; with nothing
selected before it, SelPrev then had nothing to bring back, and the line
just drawn could only be picked again by hand.
"""

from __future__ import annotations

from blackbyrd3d.commands import CommandContext, CommandProcessor
from blackbyrd3d.core import geometry
from blackbyrd3d.core.history import History
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager


def _processor():
    scene = Scene()
    selection = SelectionManager(scene)
    ctx = CommandContext(scene, selection, History(scene))
    return scene, selection, CommandProcessor(ctx)


def _run(proc, command, *inputs):
    proc.run(command)
    for value in inputs:
        proc.provide_text(value)


def test_a_line_just_drawn_comes_back():
    scene, selection, proc = _processor()
    _run(proc, "line", "0,0,0", "10,0,0")
    line = scene.all()[-1]
    assert selection.ids == []
    _run(proc, "selprev")
    assert selection.ids == [line.id]


def test_a_polyline_just_drawn_comes_back():
    scene, selection, proc = _processor()
    _run(proc, "polyline", "0,0,0", "10,0,0", "10,10,0", "")
    poly = scene.all()[-1]
    _run(proc, "selprev")
    assert selection.ids == [poly.id]


def test_a_command_that_draws_nothing_leaves_what_it_worked_on():
    scene, selection, proc = _processor()
    box = scene.add(geometry.make_box((0, 0, 0), 1, 1, 1))
    selection.set([box.id])
    _run(proc, "move", "0,0,0", "5,0,0")
    _run(proc, "selprev")
    assert selection.ids == [box.id]
