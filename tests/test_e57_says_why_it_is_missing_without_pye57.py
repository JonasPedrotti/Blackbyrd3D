"""Where pye57 has no build (ARM Linux), opening an E57 tells the user
why instead of failing with an ImportError, and the scene is left alone."""

import sys

import pytest

from blackbyrd3d import fileio
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.scene import Scene


@pytest.fixture
def without_pye57(monkeypatch):
    monkeypatch.setitem(sys.modules, "pye57", None)
    monkeypatch.delitem(sys.modules, "blackbyrd3d.fileio.e57", raising=False)
    monkeypatch.delattr(fileio, "e57", raising=False)


def test_e57_import_names_the_missing_library(without_pye57, tmp_path):
    scene = Scene()
    scene.add(g.make_box((0, 0, 0), 1, 1, 1), name="kept")
    path = tmp_path / "survey.e57"
    path.write_bytes(b"not read")

    with pytest.raises(ValueError, match="pye57") as caught:
        fileio.import_file(scene, str(path))

    assert "PLY" in str(caught.value)
    assert [o.name for o in scene.all()] == ["kept"]


def test_e57_is_still_offered_in_the_chooser(without_pye57):
    assert ".e57" in fileio.IMPORT_EXTS


def test_other_missing_modules_are_not_disguised(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "blackbyrd3d.fileio.e57", None)
    monkeypatch.delattr(fileio, "e57", raising=False)
    path = tmp_path / "survey.e57"
    path.write_bytes(b"not read")

    with pytest.raises(ModuleNotFoundError):
        fileio.import_file(Scene(), str(path))
