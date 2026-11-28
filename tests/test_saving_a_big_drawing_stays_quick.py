"""Saving a Rhino survey of ten thousand objects as .byrd took a minute.

Two things made it slow. Each shape went through a temporary file of its
own, which Windows' virus scanner opened before it could be read back, 35
of the 51 seconds. And every object still hidden was converted one at a
time, each telling the layers panel to recount the whole scene.
"""

import tempfile

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.deferred import DeferredShape
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.fileio import export_file, native


def _box():
    return g.make_box((0, 0, 0), 10, 10, 10)


def test_a_shape_turns_into_bytes_without_a_temporary_file(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("went through a temporary file")
    monkeypatch.setattr(tempfile, "mkstemp", refuse)
    back = g.shape_from_bytes(g.shape_to_bytes(_box()))
    assert g.shape_kind(back) == "solid"


def _hidden_scene(n=20):
    scene = Scene()
    for _ in range(n):
        scene.add(DeferredShape(lambda: [_box()], kind="solid"))
    return scene


def _count_notifications(scene):
    calls = []
    scene.add_listener(lambda *a: calls.append(1))
    return calls


def test_saving_converts_what_is_hidden_with_one_notification(tmp_path):
    scene = _hidden_scene()
    calls = _count_notifications(scene)
    export_file(scene, str(tmp_path / "a.byrd"))
    assert all(o.shape_ready for o in scene.all())
    assert len(calls) == 1


def test_autosave_converts_what_is_hidden_with_one_notification(tmp_path):
    scene = _hidden_scene()
    calls = _count_notifications(scene)
    native.save_scene(scene, str(tmp_path / "a.byrd"))
    assert len(calls) == 1


def test_what_was_hidden_comes_back_from_the_file(tmp_path):
    path = str(tmp_path / "a.byrd")
    export_file(_hidden_scene(3), path)
    back = Scene()
    native.load_scene(back, path)
    assert [o.kind for o in back.all()] == ["solid"] * 3
