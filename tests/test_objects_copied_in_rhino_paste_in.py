"""Ctrl+C in Rhino, Ctrl+V here: Rhino puts the copied objects on the
clipboard as a whole .3dm, one per version it writes, and they come in as
Import brings a file, at their real size and picked."""

import pytest
import rhino3dm
from PySide6.QtWidgets import QApplication

from blackbyrd3d.app import MainWindow, _rhino_clipboard_format


class _Clipboard:
    def __init__(self, formats):
        self._formats = formats

    def formats(self):
        return self._formats


def _rhino_copy(tmp_path) -> bytes:
    model = rhino3dm.File3dm()
    model.Settings.ModelUnitSystem = rhino3dm.UnitSystem.Meters
    model.Objects.AddLine(rhino3dm.Point3d(0, 0, 0), rhino3dm.Point3d(2, 0, 0))
    model.Objects.AddCircle(
        rhino3dm.Circle(rhino3dm.Point3d(0, 0, 0), 0.5))
    path = tmp_path / "clipboard.3dm"
    assert model.Write(str(path), 7)
    return path.read_bytes()


@pytest.fixture
def window():
    w = MainWindow()
    w.resize(1000, 700)
    w.show()
    QApplication.processEvents()
    yield w
    w.hide()


def test_the_newest_rhino_version_on_the_clipboard_is_read():
    offered = ['application/x-qt-windows-mime;value="Rhino 6 3DM Geometry"',
               'application/x-qt-windows-mime;value="Rhino 7 3DM Geometry"',
               "text/plain"]
    assert "Rhino 7" in _rhino_clipboard_format(_Clipboard(offered))
    assert _rhino_clipboard_format(_Clipboard(["text/plain"])) is None
    assert _rhino_clipboard_format(None) is None


def test_objects_copied_in_rhino_arrive_picked_at_their_real_size(
        window, tmp_path):
    window._paste_from_rhino(_rhino_copy(tmp_path))
    pasted = window.scene.all()
    assert len(pasted) == 2
    assert set(window.selection.ids) == {o.id for o in pasted}
    from blackbyrd3d.core import geometry as g
    longest = max(g.curve_length(o.shape) for o in pasted)
    assert longest == pytest.approx(3141.59, abs=0.1), (
        "a 0.5 m circle is 3142 mm round in a millimetre drawing")


def test_a_paste_from_rhino_is_one_undo(window, tmp_path):
    window._paste_from_rhino(_rhino_copy(tmp_path))
    assert window.scene.all()
    window.history.undo()
    QApplication.processEvents()
    assert not window.scene.all()


def test_a_clipboard_that_is_not_a_3dm_pastes_nothing(window):
    window._paste_from_rhino(b"not a 3dm at all")
    assert not window.scene.all()
