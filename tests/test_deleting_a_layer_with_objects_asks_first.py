"""Deleting a layer that holds objects asks first, and deletes them with it.

The objects used to move, unasked, to another layer, and a layer of
hundreds left its contents scattered over whichever was current.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from blackbyrd3d.core import geometry
from blackbyrd3d.core.history import History
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.ui import delete_layer_prompt
from blackbyrd3d.ui.delete_layer_prompt import DeleteLayerPrompt
from blackbyrd3d.ui.layers_panel import LayersPanel


@pytest.fixture
def panel_with_walls(monkeypatch):
    scene = Scene()
    panel = LayersPanel(scene, History(scene))
    panel.show()
    walls = scene.layers.create("Walls")
    box = scene.add(geometry.make_box((0, 0, 0), 1, 1, 1), layer_id=walls.id)
    scene.notify()
    QApplication.processEvents()
    panel._layer_id = lambda _item: walls.id
    panel.tree.currentItem = lambda: object()
    asked = []

    def answer(value):
        def confirm(_parent, name, count, sublayers=False):
            asked.append((name, count, sublayers))
            return value
        monkeypatch.setattr(delete_layer_prompt, "confirm_delete_layer",
                            confirm)
    return scene, panel, walls, box, asked, answer


def test_cancel_keeps_the_layer_and_what_is_on_it(panel_with_walls):
    scene, panel, walls, box, asked, answer = panel_with_walls
    answer(False)
    panel._delete_layer()
    assert asked == [("Walls", 1, False)]
    assert scene.layers.get(walls.id) is not None
    assert scene.get(box.id) is not None


def test_delete_takes_the_objects_with_the_layer(panel_with_walls):
    scene, panel, walls, box, _asked, answer = panel_with_walls
    answer(True)
    panel._delete_layer()
    assert walls.id not in {la.id for la in scene.layers.all()}
    assert scene.get(box.id) is None


def test_undo_brings_both_back(panel_with_walls):
    scene, panel, walls, box, _asked, answer = panel_with_walls
    answer(True)
    panel._delete_layer()
    panel.history.undo()
    assert scene.layers.get(walls.id) is not None
    assert scene.get(box.id) is not None


def test_an_empty_layer_goes_without_asking(panel_with_walls):
    scene, panel, walls, box, asked, answer = panel_with_walls
    answer(False)
    scene.remove(box.id)
    panel._delete_layer()
    assert asked == []
    assert walls.id not in {la.id for la in scene.layers.all()}


def test_the_prompt_reads_as_it_should():
    dlg = DeleteLayerPrompt(None, "Walls", 3, True)
    body = [w.text() for w in dlg.findChildren(type(dlg.heading))
            if w.objectName() == "body"][0]
    assert "3 objects are on it and its sublayers" in body
    assert dlg.heading.text() == "Delete layer “Walls”?"
