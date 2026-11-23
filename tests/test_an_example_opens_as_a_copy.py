"""An example from the welcome screen opens as a copy to work on.

It is a file shipped with the program, in a folder that may not even be
writable, so Save has to ask where to put it, and it never takes a place
among your own recent documents.
"""

from __future__ import annotations

import pytest

from blackbyrd3d.app import MainWindow
from blackbyrd3d.examples import examples


@pytest.fixture
def window(monkeypatch):
    monkeypatch.setenv("BYRD3D_NO_RPC", "1")
    monkeypatch.setenv("BYRD3D_NO_RECOVER", "1")
    w = MainWindow()
    yield w
    w.mark_saved()
    w.close()


@pytest.mark.parametrize("path", [p for p, _t, _a in examples()])
def test_an_example_opens_unnamed_and_off_the_recent_list(window, path):
    window._open_path(path)
    assert window.scene.all()
    assert window.ctx.current_path is None
    assert path not in window.recent_files()



def test_a_drawing_opens_in_the_display_it_was_saved_in(window, tmp_path):
    from blackbyrd3d import fileio
    from blackbyrd3d.core import geometry
    window.scene.add(geometry.make_box((0, 0, 0), 10, 10, 10))
    window.viewport.set_display_mode("plastercolor")
    window.store_view_settings()
    path = str(tmp_path / "kept.byrd")
    fileio.export_file(window.scene, path)
    window.viewport.set_display_mode("wireframe")
    window._open_path(path)
    assert window.viewport.display_mode == "plastercolor"


def test_an_older_drawing_leaves_the_display_as_it_is(window):
    from blackbyrd3d.core.view_settings import from_json
    settings = from_json({"panes": {"perspective": {"look": {"grid": True}}}})
    window.viewport.set_display_mode("ghosted")
    window.viewport.apply_pane_settings(settings.panes["perspective"])
    assert window.viewport.display_mode == "ghosted"


def test_saving_from_the_window_keeps_a_preview(window, tmp_path,
                                                 monkeypatch):
    """Save from the menu, not only the save command, keeps the picture the
    welcome screen shows of the file."""
    from blackbyrd3d.commands import file as file_cmds
    from blackbyrd3d.core import geometry
    from blackbyrd3d.fileio.native import read_thumbnail
    monkeypatch.setattr(file_cmds, "_thumbnail", lambda ctx: b"preview")
    window.scene.add(geometry.make_box((0, 0, 0), 10, 10, 10))
    path = str(tmp_path / "saved.byrd")
    window._export_showing_progress(path)
    assert read_thumbnail(path) == b"preview"
