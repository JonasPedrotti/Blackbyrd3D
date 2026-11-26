"""Ctrl+C in one Blackbyrd3D window, Ctrl+V in another.

Each window is a process of its own, so the copy lived only where it was
made, and the other window pasted the words "2 objects copied in
Blackbyrd3D" into its command line. The copy now goes to a file the other
window reads, written as the first window loses the focus or closes.
"""

from __future__ import annotations

import json

import pytest
from PySide6.QtWidgets import QApplication

from blackbyrd3d.app import MainWindow
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core import shared_clipboard
from blackbyrd3d.core.layout import Layout, TextNote


def _as_if_from_another_process():
    """Both windows of a test share one pid, which is what tells them apart."""
    with open(shared_clipboard.path(), encoding="utf-8") as fh:
        record = json.load(fh)
    record["pid"] = -1
    with open(shared_clipboard.path(), "w", encoding="utf-8") as fh:
        json.dump(record, fh)


@pytest.fixture
def two():
    QApplication.clipboard().clear()
    return MainWindow(), MainWindow()


def test_objects_copied_in_one_window_paste_in_the_other(two):
    a, b = two
    walls = a.scene.layers.create("Walls", (0.8, 0.1, 0.1))
    a.scene.add(g.make_box((0, 0, 0), 10, 10, 10), layer_id=walls.id)
    a.scene.add(g.make_line((0, 0, 0), (50, 0, 0)))
    a.selection.set([o.id for o in a.scene.all()])
    a._copy_selected()
    a._publish_clipboard()
    _as_if_from_another_process()

    b._paste()

    pasted = b.scene.all()
    assert len(pasted) == 2
    assert b.command_line.input.text() == ""
    layer = b.scene.layers.find_by_name("Walls")
    assert layer is not None and layer.color == (0.8, 0.1, 0.1)
    assert sorted(o.layer_id for o in pasted) == sorted(
        [layer.id, b.scene.layers.current_id])


def test_a_paste_waits_for_the_other_window_to_write_its_copy(two,
                                                               monkeypatch):
    a, b = two
    a.scene.add(g.make_line((0, 0, 0), (50, 0, 0)))
    a.selection.set([o.id for o in a.scene.all()])
    a._copy_selected()
    _as_if_from_another_process()           # announced, not yet written
    waited = []

    def other_window_lets_go(_seconds):
        waited.append(True)
        a._publish_clipboard()
        _as_if_from_another_process()

    monkeypatch.setattr("time.sleep", other_window_lets_go)

    b._paste()

    assert waited
    assert len(b.scene.all()) == 1


def test_waiting_for_the_other_window_can_be_cancelled(two, monkeypatch):
    from blackbyrd3d.fileio.progress import Cancelled
    a, b = two
    a.scene.add(g.make_line((0, 0, 0), (50, 0, 0)))
    a.selection.set([o.id for o in a.scene.all()])
    a._copy_selected()
    _as_if_from_another_process()

    def the_user_clicks_cancel(_seconds):
        raise Cancelled("waiting")

    monkeypatch.setattr("time.sleep", the_user_clicks_cancel)
    said = []
    b.ctx.add_echo_listener(said.append)

    b._paste()

    assert b.scene.all() == []
    assert "Paste cancelled." in said


def test_the_own_newer_copy_wins_over_the_other_window(two):
    a, b = two
    a.scene.add(g.make_line((0, 0, 0), (50, 0, 0)))
    a.selection.set([o.id for o in a.scene.all()])
    a._copy_selected()
    a._publish_clipboard()
    _as_if_from_another_process()
    b.scene.add(g.make_box((0, 0, 0), 5, 5, 5))
    b.selection.set([o.id for o in b.scene.all()])
    b._copy_selected()                        # same words, made later

    b._paste()

    assert len(b.scene.all()) == 2
    assert all(o.shape.ShapeType() == b.scene.all()[0].shape.ShapeType()
               for o in b.scene.all())


def test_sheet_items_paste_onto_a_sheet_in_the_other_window(two):
    a, b = two
    one = Layout(name="Sheet1")
    one.notes.append(TextNote(x=50.0, y=200.0, text="SECTION A-A"))
    a.scene.layouts.append(one)
    a.switch_space(one.id)
    a.viewport.layout_view.selected = [("note", one.notes[0])]
    a._copy_selected()
    a._publish_clipboard()
    _as_if_from_another_process()
    other = Layout(name="Sheet9")
    b.scene.layouts.append(other)
    b.switch_space(other.id)

    b._paste()

    assert [n.text for n in other.notes] == ["SECTION A-A"]
    assert other.notes[0].id != one.notes[0].id


def _copy_on_a_new_layer(a):
    walls = a.scene.layers.create("Walls", (0.8, 0.1, 0.1))
    a.scene.add(g.make_box((0, 0, 0), 10, 10, 10), layer_id=walls.id)
    a.selection.set([o.id for o in a.scene.all()])
    a._copy_selected()
    a._publish_clipboard()
    _as_if_from_another_process()


def test_a_paste_cancelled_while_reading_leaves_no_layer_behind(two,
                                                               monkeypatch):
    from blackbyrd3d.fileio.progress import Cancelled
    a, b = two
    _copy_on_a_new_layer(a)
    real = shared_clipboard.model_items

    def cancelled_after_reading(record, progress=None):
        real(record, progress)
        raise Cancelled("reading")

    monkeypatch.setattr(shared_clipboard, "model_items",
                        cancelled_after_reading)
    layers_before = len(b.scene.layers.all())

    b._paste()

    assert b.scene.all() == []
    assert len(b.scene.layers.all()) == layers_before
    assert not b.history.can_undo


def test_undo_takes_the_layer_a_paste_made_with_it(two):
    a, b = two
    _copy_on_a_new_layer(a)

    b._paste()
    assert b.scene.layers.find_by_name("Walls") is not None
    b.history.undo()

    assert b.scene.all() == []
    assert b.scene.layers.find_by_name("Walls") is None


def test_a_big_paste_shows_its_card_before_the_work(two, monkeypatch):
    """OpenCascade holds the interpreter while it copies, so a card held
    back half a second never came for one big polysurface."""
    from blackbyrd3d import app as app_module
    from blackbyrd3d.ui.progress_card import ProgressCard
    a, _b = two
    monkeypatch.setattr(app_module, "_BIG_PASTE_FACES", 0)
    shown = []
    monkeypatch.setattr(ProgressCard, "show",
                        lambda self: shown.append(self.labelText()))
    a.scene.add(g.make_box((0, 0, 0), 10, 10, 10))
    a.selection.set([o.id for o in a.scene.all()])
    a._copy_selected()

    a._paste()

    assert shown and shown[0] == "Pasting object 1 of 1"
    assert len(a.scene.all()) == 2


def test_a_copy_from_another_window_is_not_copied_again(two, monkeypatch):
    a, b = two
    _copy_on_a_new_layer(a)
    copied = []
    monkeypatch.setattr(g, "copy_shape", lambda s: copied.append(s) or s)

    b._paste()

    assert len(b.scene.all()) == 1
    assert copied == []
