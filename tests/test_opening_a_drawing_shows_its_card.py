"""Opening one of our own drawings shows the loading card at once.

Reading and unpacking a .byrd reports nothing until its objects come in,
so a card held back half a second, as for an import, never came at all
and the window just sat there.
"""

from __future__ import annotations

import pytest

from blackbyrd3d.app import MainWindow
from blackbyrd3d.core import geometry
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.fileio import native
from blackbyrd3d.ui import progress_card


@pytest.fixture
def window(monkeypatch):
    monkeypatch.setenv("BYRD3D_NO_RPC", "1")
    monkeypatch.setenv("BYRD3D_NO_RECOVER", "1")
    w = MainWindow()
    yield w
    w.mark_saved()
    w.close()


def test_a_byrd_shows_the_card_from_the_start(window, tmp_path, monkeypatch):
    scene = Scene()
    scene.add(geometry.make_box((0, 0, 0), 1, 1, 1))
    path = str(tmp_path / "drawing.byrd")
    native.save_scene(scene, path)
    shown = []
    monkeypatch.setattr(progress_card.ProgressCard, "show",
                        lambda self: shown.append(self.labelText()))
    window._import_showing_progress(path, replace=True)
    assert shown, "no loading card"
    assert window.scene.all()
