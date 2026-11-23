"""A .byrd carries what was on screen, so opening it shows the drawing
without meshing every object again. A mesh it cannot vouch for, made by
another release or unreadable, is made afresh as it always was."""

from __future__ import annotations

import json
import zipfile

import numpy as np

from blackbyrd3d.core import geometry as g
from blackbyrd3d.core import tessellate
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.fileio import native


def _saved(tmp_path, meshed=True):
    scene = Scene()
    scene.add(g.make_sphere((0, 0, 0), 5), name="Ball")
    scene.add(g.make_line((0, 0, 0), (10, 0, 0)), name="Line")
    if meshed:
        for obj in scene.all():
            obj.mesh
    path = str(tmp_path / "drawing.byrd")
    native.save_scene(scene, path)
    return path


def _opened(path):
    scene = Scene()
    native.load_scene(scene, path)
    return scene


def _rewritten(path, change_doc=None, change_member=None):
    with zipfile.ZipFile(path) as z:
        members = {n: z.read(n) for n in z.namelist()}
    doc = json.loads(members["document.json"])
    if change_doc:
        change_doc(doc)
    members["document.json"] = json.dumps(doc).encode()
    if change_member:
        change_member(members)
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)


def test_the_meshes_come_back_as_they_were_drawn(tmp_path):
    scene = _opened(_saved(tmp_path))
    for obj in scene.all():
        assert obj.mesh_ready
        fresh = tessellate.tessellate(obj.shape)
        for name in tessellate._STORED:
            assert np.array_equal(getattr(obj.mesh, name),
                                  getattr(fresh, name))


def test_what_was_never_meshed_is_not_carried(tmp_path):
    scene = _opened(_saved(tmp_path, meshed=False))
    assert not any(obj.mesh_ready for obj in scene.all())


def test_meshes_from_another_release_are_made_afresh(tmp_path):
    path = _saved(tmp_path)
    _rewritten(path, change_doc=lambda doc: doc.update(
        display_meshes="0.0.1/1"))
    assert not any(obj.mesh_ready for obj in _opened(path).all())


def test_an_unreadable_mesh_is_made_afresh(tmp_path):
    path = _saved(tmp_path)

    def spoil(members):
        for name in members:
            if name.startswith("meshes/"):
                members[name] = b"not a mesh"
    _rewritten(path, change_member=spoil)
    scene = _opened(path)
    assert not any(obj.mesh_ready for obj in scene.all())
    assert all(obj.mesh.has_faces or len(obj.mesh.local_edges)
               for obj in scene.all())


def test_without_qt_no_meshes_are_kept(tmp_path, monkeypatch):
    """Lettering meshed with no fonts to hand is boxes, not figures."""
    from PySide6.QtGui import QGuiApplication
    monkeypatch.setattr(QGuiApplication, "instance", staticmethod(lambda: None))
    path = _saved(tmp_path)
    assert not any(obj.mesh_ready for obj in _opened(path).all())
