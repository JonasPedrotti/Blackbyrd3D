"""ViewCapture: one command for the old two, behind a popup.

ViewCaptureToFile and ViewCaptureToClipboard took the pane at its own
pixels and nothing else. ViewCapture shows the picture, takes it at any
size the pane's aspect allows, and copies or saves it from there; the old
names, and Screenshot, start it too.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

import blackbyrd3d.commands  # noqa: F401  registers them
from blackbyrd3d.commands.base import resolve
from blackbyrd3d.core import geometry as g
from blackbyrd3d.ui.view_capture import ViewCaptureDialog


class _Pane:
    """What the popup asks of a viewport, without drawing anything."""

    def __init__(self, w=400, h=300):
        self.w, self.h = w, h
        self.taken = []

    def width(self):
        return self.w

    def height(self):
        return self.h

    def capture_size(self, scale=1.0):
        return max(1, round(self.w * scale)), max(1, round(self.h * scale))

    def capture_max_scale(self):
        return 10.0

    def capture_image(self, scale=1.0):
        self.taken.append(scale)
        w, h = self.capture_size(scale)
        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(0x336699)
        return img


@pytest.fixture
def popup():
    said = []
    picked = []

    def pick(**kwargs):
        picked.append(kwargs)
        return picked[0].get("answer", "")

    dlg = ViewCaptureDialog(None, _Pane(), pick, said.append)
    yield dlg, said, picked
    dlg.deleteLater()


@pytest.mark.parametrize("name", ["viewcapture", "screenshot",
                                  "viewcapturetofile", "vcf",
                                  "viewcapturetoclipboard", "vcc"])
def test_every_old_name_starts_viewcapture(name):
    assert resolve(name).name == "viewcapture"


def test_the_preview_is_smaller_than_the_pane(popup):
    dlg, _said, _picked = popup
    size = dlg.preview.pixmap().size()
    assert size.width() < 400 and size.height() < 300
    assert abs(size.width() / size.height() - 400 / 300) < 0.02


def test_it_opens_at_the_pane_s_own_pixels(popup):
    dlg, _said, _picked = popup
    assert (dlg.width_box.value(), dlg.height_box.value()) == (400, 300)
    assert dlg.scale_box.value() == 1.0


def test_a_new_width_brings_the_height_and_the_scale_along(popup):
    dlg, _said, _picked = popup
    dlg.width_box.setValue(800)
    assert dlg.height_box.value() == 600
    assert dlg.scale_box.value() == 2.0


def test_a_new_height_brings_the_width_along(popup):
    dlg, _said, _picked = popup
    dlg.height_box.setValue(150)
    assert dlg.width_box.value() == 200
    assert dlg.scale_box.value() == 0.5


def test_the_arrows_step_the_scale_by_a_tenth(popup):
    dlg, _said, _picked = popup
    dlg.scale_box.stepBy(1)
    assert dlg.scale_box.value() == pytest.approx(1.1)
    assert (dlg.width_box.value(), dlg.height_box.value()) == (440, 330)
    dlg.scale_box.stepBy(-3)
    assert dlg.scale_box.value() == pytest.approx(0.8)
    assert (dlg.width_box.value(), dlg.height_box.value()) == (320, 240)


def test_copy_puts_the_picture_at_the_size_asked_on_the_clipboard(popup):
    dlg, said, _picked = popup
    QApplication.clipboard().clear()
    dlg.scale_box.setValue(2.0)
    dlg.copy_button.click()
    img = QApplication.clipboard().image()
    assert (img.width(), img.height()) == (800, 600)
    assert dlg.viewport.taken[-1] == 2.0
    assert "Copied 800x600" in said[-1]


def test_copy_says_so_on_the_button_and_then_goes_back(popup):
    dlg, _said, _picked = popup
    dlg.copy_button.click()
    assert dlg.copy_button.text() == "Copied ✓"
    assert dlg.copy_button.objectName() == "copiedButton"
    dlg._copied.timeout.emit()
    assert dlg.copy_button.text() == "Copy"


def test_save_asks_the_file_chooser_and_writes_there(popup, tmp_path):
    dlg, said, picked = popup
    out = tmp_path / "shot"
    picked.append({"answer": str(out)})
    dlg.scale_box.setValue(0.5)
    dlg.save_button.click()
    assert picked[1]["save"] is True
    written = QImage(str(out) + ".png")
    assert (written.width(), written.height()) == (200, 150)
    assert "Saved 200x150" in said[-1]


def test_a_cancelled_chooser_saves_nothing(popup):
    dlg, said, picked = popup
    picked.append({"answer": ""})
    dlg.save_button.click()
    assert dlg.viewport.taken == [1.0]          # the preview only
    assert said == []


@pytest.fixture
def window(_qapp):
    from blackbyrd3d.app import MainWindow
    w = MainWindow()
    w.set_view_layout("single")
    w.resize(900, 700)
    w.show()
    vp = w.viewport
    vp.grabFramebuffer()
    if not (vp.isValid() and getattr(vp, "_marker_prog", 0)):
        w.mark_saved()
        w.close()
        pytest.skip("no GL 3.3 to draw with here (CI runs offscreen)")
    yield w, vp
    w.mark_saved()
    w.close()


def test_a_capture_at_twice_the_scale_has_twice_the_pixels(window):
    w, vp = window
    w.scene.add(g.make_box((0, 0, 0), 10, 10, 10))
    vp.zoom_extents()
    one = vp.capture_image(1.0)
    two = vp.capture_image(2.0)
    assert one is not None and two is not None
    assert (two.width(), two.height()) == (one.width() * 2,
                                           one.height() * 2)
    assert (one.width(), one.height()) == vp.capture_size(1.0)


def test_no_field_is_selected_when_it_opens(popup):
    dlg, _said, _picked = popup
    dlg.show()
    QApplication.processEvents()
    focused = QApplication.focusWidget()
    assert focused not in (dlg.width_box, dlg.height_box, dlg.scale_box)
    for box in (dlg.width_box, dlg.height_box, dlg.scale_box):
        assert not box.lineEdit().hasSelectedText()
    dlg.close()
