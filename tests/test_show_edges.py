"""ShowEdges: all or only the naked edges of objects, drawn on top in a
colour of your own, from a popup you can add objects to and take them out
of, as long as it stays open."""

import pytest

from blackbyrd3d.core import geometry as g

SQUARE = [(0.0, 0.0, 0.0), (10.0, 0.0, 0.0),
          (10.0, 10.0, 0.0), (0.0, 10.0, 0.0)]


def _square_face():
    return g.planar_face(g.make_polyline(SQUARE, closed=True))


def _open_box():
    """A box with its lid taken off: four naked edges round the top."""
    box = g.make_box((0.0, 0.0, 0.0), 10.0, 10.0, 10.0)
    faces = g.faces_of(box)
    top = max(faces, key=lambda f: g.centroid(f)[2])
    return g.join_surfaces([f for f in faces if not f.IsSame(top)])


# ------------------------------------------------------------- geometry

def test_a_closed_solid_has_no_naked_edges():
    assert g.naked_edges(g.make_box((0.0, 0.0, 0.0), 1.0, 2.0, 3.0)) == []


def test_every_edge_of_a_single_face_is_naked():
    assert len(g.naked_edges(_square_face())) == 4


def test_an_open_polysurface_is_naked_only_round_its_opening():
    shape = _open_box()
    assert len(g.edges_of(shape)) == 12
    assert len(g.naked_edges(shape)) == 4


def test_a_seam_is_not_a_naked_edge():
    """A cylinder's wall meets itself along its seam: one face, but not
    open there."""
    cyl = g.make_cylinder((0.0, 0.0, 0.0), 5.0, 10.0)
    wall = max(g.faces_of(cyl), key=g.surface_area)
    assert len(g.naked_edges(wall)) == 2


def test_a_mesh_or_nothing_has_no_naked_edges():
    assert g.naked_edges(None) == []


def test_the_segments_drawn_follow_the_edges():
    from blackbyrd3d.ui.viewport import shown_edge_segments
    every, naked = shown_edge_segments(_open_box())
    assert every.shape[1:] == (2, 3) and naked.shape[1:] == (2, 3)
    assert len(every) >= 12 and len(naked) >= 4
    assert naked[:, :, 2] == pytest.approx(10.0)


# ------------------------------------------------------------- commands

@pytest.fixture
def env():
    import blackbyrd3d.commands  # registers all commands  # noqa: F401
    from blackbyrd3d.commands.base import CommandContext, CommandProcessor
    from blackbyrd3d.core.history import History
    from blackbyrd3d.core.scene import Scene
    from blackbyrd3d.core.selection import SelectionManager
    scene = Scene()
    selection = SelectionManager(scene)
    ctx = CommandContext(scene, selection, History(scene))
    return scene, CommandProcessor(ctx)


def _pick(proc, cmd, *objs):
    proc.run(cmd)
    for obj in objs:
        proc.click_object(obj.id)
    proc.finish_selection()


def test_showedges_shows_the_edges_of_what_you_pick(env):
    scene, proc = env
    a, b = scene.add(_square_face()), scene.add(_open_box())
    _pick(proc, "showedges", a, b)
    assert not proc.busy
    assert scene.edges_shown == {a.id, b.id}


def test_objects_can_be_added_and_taken_out_again(env):
    scene, proc = env
    a, b = scene.add(_square_face()), scene.add(_open_box())
    _pick(proc, "showedges", a)
    _pick(proc, "showedgesadd", b)
    assert scene.edges_shown == {a.id, b.id}
    _pick(proc, "showedgesremove", a)
    assert scene.edges_shown == {b.id}


def test_plus_and_minus_take_the_objects_selected(env):
    scene, proc = env
    a, b = scene.add(_square_face()), scene.add(_open_box())
    _pick(proc, "showedges", a)
    proc.ctx.selection.set([b.id])
    proc.run("showedgesadd")
    assert not proc.busy
    assert scene.edges_shown == {a.id, b.id}
    proc.ctx.selection.set([a.id])
    proc.run("showedgesremove")
    assert not proc.busy
    assert scene.edges_shown == {b.id}


def test_showedges_takes_surfaces_and_solids_only(env):
    scene, proc = env
    curve = scene.add(g.make_polyline(SQUARE))
    _pick(proc, "showedges", curve)
    assert curve.id not in scene.edges_shown


def test_a_new_drawing_shows_no_edges(env):
    scene, proc = env
    _pick(proc, "showedges", scene.add(_square_face()))
    scene.clear()
    assert scene.edges_shown == set()


def test_surfaceedges_no_longer_answers_to_showedges():
    import blackbyrd3d.commands  # noqa: F401
    from blackbyrd3d.commands.base import resolve
    assert resolve("showedges").name == "showedges"
    assert resolve("surfaceedges").name == "surfaceedges"


# ------------------------------------------------------------- popup

def _window(scene):
    from PySide6.QtWidgets import QWidget

    class Window(QWidget):
        def all_viewports(self):
            return []

        def run_command(self, name):
            self.ran.append(name)

    window = Window()
    window.scene = scene
    window.ran = []
    return window


@pytest.fixture
def panel():
    from blackbyrd3d.core.scene import Scene
    from blackbyrd3d.ui.show_edges_panel import ShowEdgesPanel
    scene = Scene()
    window = _window(scene)
    return ShowEdgesPanel(window), window, scene


def test_the_popup_opens_on_naked_edges_only(panel):
    p, _window, _scene = panel
    assert p.naked_box.isChecked() and not p.all_box.isChecked()


def test_the_checkboxes_set_which_edges_are_drawn(panel):
    p, _window, scene = panel
    p.all_box.setChecked(True)
    assert scene.edges_show_all is True
    p.naked_box.setChecked(False)
    assert scene.edges_show_naked is False


def test_opening_again_starts_on_naked_edges_only(panel):
    p, _window, scene = panel
    p.all_box.setChecked(True)
    p.naked_box.setChecked(False)
    p.reject()
    p.reset_options()
    p.refresh()
    assert p.naked_box.isChecked() and not p.all_box.isChecked()
    assert scene.edges_show_naked and not scene.edges_show_all


def test_the_default_edge_color_is_blue():
    from blackbyrd3d.core.scene import Scene
    assert Scene().edges_color == (0.0, 0.0, 1.0)


def test_plus_and_minus_add_and_remove_objects(panel):
    p, window, _scene = panel
    p.add_button.click()
    p.remove_button.click()
    assert window.ran == ["showedgesadd", "showedgesremove"]


def test_closing_the_popup_puts_the_edges_away(panel):
    p, _window, scene = panel
    scene.edges_shown.update({"a", "b"})
    p.reject()
    assert scene.edges_shown == set()


def test_the_swatch_sets_the_edge_color(panel, monkeypatch):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QColor
    from PySide6.QtTest import QTest
    from blackbyrd3d.ui import show_edges_panel
    p, _window, scene = panel
    monkeypatch.setattr(show_edges_panel, "get_color",
                        lambda *a, **k: QColor(255, 0, 0))
    p.color_button.resize(30, 30)
    QTest.mouseClick(p.color_button, Qt.MouseButton.LeftButton,
                     pos=QPoint(15, 15))
    assert scene.edges_color == (1.0, 0.0, 0.0)
    assert p.color_button.color == QColor(255, 0, 0)
