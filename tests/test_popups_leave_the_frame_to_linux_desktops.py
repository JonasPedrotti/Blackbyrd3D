from PySide6.QtCore import Qt

from blackbyrd3d.ui import card_dialog
from blackbyrd3d.ui.card_dialog import CardDialog


def _dialog(monkeypatch, platform):
    monkeypatch.setattr(card_dialog.sys, "platform", platform)
    return CardDialog(None, "Save changes?")


def test_on_linux_the_window_is_the_card(monkeypatch):
    dlg = _dialog(monkeypatch, "linux")
    assert dlg.layout().contentsMargins().left() == 0
    assert dlg.card.graphicsEffect() is None
    assert not dlg.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


def test_elsewhere_the_card_floats_on_its_own_shadow(monkeypatch):
    dlg = _dialog(monkeypatch, "win32")
    assert dlg.layout().contentsMargins().left() == 18
    assert dlg.card.graphicsEffect() is not None
    assert dlg.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
