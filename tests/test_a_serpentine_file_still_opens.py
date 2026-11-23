"""Blackbyrd3D grew out of Serpentine3D: its .serp files keep opening, while
what Blackbyrd3D saves is a .byrd of its own."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from blackbyrd3d import fileio
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.scripting import Document

# saved by Serpentine3D, before the rename
SAMPLE = Path(__file__).resolve().parent / "data" / "serpentine_vase.serp"


def _serpentine_file(tmp_path):
    path = tmp_path / "vase.serp"
    shutil.copy(SAMPLE, path)
    return path


def _format_of(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            return json.loads(z.read("document.json"))["format"]
    return json.loads(Path(path).read_text(encoding="utf-8"))["format"]


def test_the_sample_really_is_a_serpentine_file():
    assert _format_of(SAMPLE) == "serpentine3d"


def test_a_serp_file_opens(tmp_path):
    scene = Scene()
    fileio.import_file(scene, str(_serpentine_file(tmp_path)), replace=True)
    assert scene.all()


def test_a_serp_file_imports_beside_what_is_there(tmp_path):
    scene = Scene()
    scene.add(g.make_box((0, 0, 0), 1, 1, 1), name="Mine")
    added = fileio.import_file(scene, str(_serpentine_file(tmp_path)))
    assert added > 0
    assert "Mine" in [o.name for o in scene.all()]


def test_a_serp_is_offered_to_open_but_not_to_save():
    opens = [ext for _, exts in fileio.IMPORT_FORMATS for ext in exts]
    saves = [ext for _, exts in fileio.EXPORT_FORMATS for ext in exts]
    assert ".serp" in opens and ".byrd" in opens
    assert ".serp" not in saves and ".byrd" in saves


def test_saving_writes_a_blackbyrd_file(tmp_path):
    doc = Document()
    doc.add(g.make_box((0, 0, 0), 1, 1, 1))
    path = tmp_path / "part.byrd"
    doc.save(str(path))
    assert _format_of(path) == "blackbyrd3d"
