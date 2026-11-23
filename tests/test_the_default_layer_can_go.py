"""Default is a layer like any other: it can be deleted, and only the last
layer of a drawing cannot, a drawing needing one to draw on."""

from __future__ import annotations

import pytest

from blackbyrd3d.core import geometry
from blackbyrd3d.core.layers import DEFAULT_LAYER_ID
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.fileio import import_file, native


def test_default_can_be_deleted_once_there_is_another():
    scene = Scene()
    other = scene.layers.create("Walls")
    scene.remove_layer(DEFAULT_LAYER_ID)
    assert [la.id for la in scene.layers.all()] == [other.id]
    assert scene.layers.current_id == other.id


def test_the_only_layer_cannot_be_deleted():
    scene = Scene()
    with pytest.raises(ValueError):
        scene.remove_layer(DEFAULT_LAYER_ID)


def test_what_was_on_it_moves_to_the_current_layer():
    scene = Scene()
    walls = scene.layers.create("Walls")
    scene.layers.current_id = walls.id
    obj = scene.add(geometry.make_box((0, 0, 0), 1, 1, 1),
                    layer_id=DEFAULT_LAYER_ID)
    scene.remove_layer(DEFAULT_LAYER_ID)
    assert scene.get(obj.id).layer_id == walls.id


def test_deleting_the_current_layer_hands_its_objects_to_the_first_left():
    scene = Scene()
    walls = scene.layers.create("Walls")
    obj = scene.add(geometry.make_box((0, 0, 0), 1, 1, 1),
                    layer_id=DEFAULT_LAYER_ID)
    scene.remove_layer(DEFAULT_LAYER_ID)
    assert scene.get(obj.id).layer_id == walls.id


def test_a_drawing_saved_without_default_opens_without_it(tmp_path):
    scene = Scene()
    walls = scene.layers.create("Walls")
    scene.add(geometry.make_box((0, 0, 0), 1, 1, 1), layer_id=walls.id)
    scene.remove_layer(DEFAULT_LAYER_ID)
    path = str(tmp_path / "no-default.byrd")
    native.save_scene(scene, path)
    opened = Scene()
    import_file(opened, path, replace=True)
    assert [la.name for la in opened.layers.all()] == ["Walls"]
