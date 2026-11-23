"""The welcome screen: recent documents and examples as cards, and a new
model in the units chosen there.

The examples fill the places the recent documents have not taken yet, so a
first launch has something to open and a busy one shows your own work.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from blackbyrd3d.examples import examples, is_example
from blackbyrd3d.ui.welcome import SLOTS, WelcomeScreen, start_cards
from blackbyrd3d.utils.config import Config

LONG = "HGS2_3DM_124_SAM_CAVE_INTERIOR_AND_EXTERIOR_SURVEY_001_final.3dm"


class _Window(QWidget):
    """Just enough window for the welcome screen to read and call."""

    def __init__(self, cfg, files):
        super().__init__()
        self.cfg = cfg
        self._files = files
        self.started = None
        self.opened = None

    def recent_files(self):
        return list(self._files)

    def start_new(self, units):
        self.started = units

    def _open_path(self, path):
        self.opened = path


def _screen(tmp_path, names=()):
    paths = []
    for name in names:
        p = tmp_path / name
        p.write_text("")
        paths.append(str(p))
    cfg = Config(path=str(tmp_path / "settings.json"))
    win = _Window(cfg, paths)
    dlg = WelcomeScreen(win)
    dlg.show()
    QApplication.processEvents()
    return dlg, win, paths


def test_the_examples_ship_with_the_program():
    assert len(examples()) >= 3
    assert all(is_example(path) for path, _t, _a in examples())


def test_with_nothing_recent_the_examples_fill_the_cards(tmp_path):
    dlg, _win, _paths = _screen(tmp_path)
    assert [c.path for c in dlg.cards] == [p for p, _t, _a in examples()]
    assert all(c.example for c in dlg.cards)


def test_recent_documents_come_first_and_push_examples_out():
    recent = [f"/work/part{i}.byrd" for i in range(SLOTS - 1)]
    cards = start_cards(recent, examples())
    assert [c["path"] for c in cards[:len(recent)]] == recent
    assert len(cards) == SLOTS
    assert [c["example"] for c in cards].count(True) == 1


def test_a_full_history_leaves_no_room_for_examples():
    recent = [f"/work/part{i}.byrd" for i in range(SLOTS + 3)]
    cards = start_cards(recent, examples())
    assert len(cards) == SLOTS
    assert not any(c["example"] for c in cards)


def test_a_long_name_gives_in_the_middle(tmp_path):
    dlg, _win, paths = _screen(tmp_path, [LONG])
    card = dlg.cards[0]
    shown = card.name.text()
    assert shown != LONG and "…" in shown
    assert shown.endswith(".3dm")
    assert card.toolTip() == paths[0]


def test_a_new_model_takes_the_units_chosen(tmp_path):
    dlg, win, _paths = _screen(tmp_path)
    dlg.units.setCurrentIndex(dlg.units.findData("m"))
    dlg._new()
    assert win.started == "m"


def test_the_units_start_on_the_default(tmp_path):
    cfg = Config(path=str(tmp_path / "settings.json"))
    cfg.set("default_units", "in")
    dlg = WelcomeScreen(_Window(cfg, []))
    assert dlg.units.currentData() == "in"


@pytest.mark.parametrize("index", [0, -1])
def test_a_card_opens_its_document(tmp_path, index):
    dlg, win, _paths = _screen(tmp_path, ["stool.byrd"])
    card = dlg.cards[index]
    dlg._open_path(card.path)
    assert win.opened == card.path


def test_an_example_saved_in_place_is_not_listed_twice():
    path = examples()[0][0]
    cards = start_cards([path, "/work/part.byrd"], examples())
    assert [c["path"] for c in cards].count(path) == 1
    assert cards[0]["path"] == "/work/part.byrd"


def test_it_sits_in_the_middle_of_the_window(tmp_path):
    """Again once the window has its size: on launch it is still growing
    into its saved, perhaps maximised, geometry."""
    dlg, win, _paths = _screen(tmp_path)
    win.setGeometry(100, 100, 1600, 1000)
    win.show()
    QApplication.processEvents()
    dlg._center()
    assert dlg.frameGeometry().center() == win.frameGeometry().center()


def test_the_window_behind_stays_closable(tmp_path):
    from PySide6.QtCore import Qt
    dlg, _win, _paths = _screen(tmp_path)
    assert dlg.windowModality() == Qt.WindowModality.NonModal


def test_a_click_outside_closes_it(tmp_path):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    dlg, win, _paths = _screen(tmp_path)
    outside = dlg.frameGeometry().bottomRight() + QPointF(40, 40).toPoint()
    ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5),
                     QPointF(outside), Qt.MouseButton.LeftButton,
                     Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(win, ev)
    assert not dlg.isVisible()


def test_a_click_inside_leaves_it_open(tmp_path):
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    dlg, _win, _paths = _screen(tmp_path)
    inside = dlg.frameGeometry().center()
    ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5),
                     QPointF(inside), Qt.MouseButton.LeftButton,
                     Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(dlg, ev)
    assert dlg.isVisible()
