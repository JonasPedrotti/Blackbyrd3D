"""The units at the foot of the window are a button that picks new units."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel

from blackbyrd3d.app import MainWindow
from blackbyrd3d.core import geometry as g
from blackbyrd3d.ui import units_prompt
from blackbyrd3d.ui.units_prompt import UnitsPrompt


@pytest.fixture
def win():
    w = MainWindow()
    w.resize(1200, 800)
    return w


def test_the_button_shows_the_document_units(win):
    assert win._status_line.units_button.text().startswith("units: mm")
    assert "units:" not in win.statusBar().currentMessage()


def test_an_empty_document_changes_units_without_asking(win, monkeypatch):
    asked = []
    monkeypatch.setattr(units_prompt, "ask_scale_for_units",
                        lambda *a: asked.append(a))
    win._status_line.unitsChosen.emit("in")
    assert win.scene.units == "in"
    assert not asked
    assert win._status_line.units_button.text().startswith("units: in")


@pytest.mark.parametrize("answer, units, volume", [
    (units_prompt.SCALE, "m", 1.0),
    (units_prompt.KEEP, "m", 1e9),
    (units_prompt.CANCEL, "mm", 1e9),
])
def test_a_model_asks_whether_to_scale(win, monkeypatch, answer, units,
                                       volume):
    win.scene.add(g.make_box((0, 0, 0), 1000, 1000, 1000))
    asked = []

    def ask(parent, factor, old, new):
        asked.append(factor)
        return answer
    monkeypatch.setattr(units_prompt, "ask_scale_for_units", ask)
    win._status_line.unitsChosen.emit("m")
    assert asked == [pytest.approx(0.001)]
    assert win.scene.units == units
    assert g.volume(win.scene.all()[0].shape) == pytest.approx(volume,
                                                                rel=1e-6)


def test_one_undo_puts_the_units_and_the_model_back(win, monkeypatch):
    win.scene.add(g.make_box((0, 0, 0), 1000, 1000, 1000))
    monkeypatch.setattr(units_prompt, "ask_scale_for_units",
                        lambda *a: units_prompt.SCALE)
    win._status_line.unitsChosen.emit("m")
    win.processor.run("undo")
    assert win.scene.units == "mm"
    assert g.volume(win.scene.all()[0].shape) == pytest.approx(1e9, rel=1e-6)


def test_the_prompt_names_the_factor(win):
    dlg = UnitsPrompt(win, 0.001, "mm", "m")
    assert dlg.heading.text() == "Do you want to scale by 0.001?"
    assert dlg.findChild(QLabel, "body").text() == (
        "Without scaling, 100 mm becomes 100 m.")
    assert dlg.answer == units_prompt.CANCEL
