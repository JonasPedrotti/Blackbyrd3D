"""Ortho and grid snap are one switch for every pane.

The object snaps were shared by all panes, but ortho and the grid lived on
each pane. The Ortho button set only the first pane and F8 only the active
one, so in a four-pane layout the button lit up while the pane under the
cursor drew freely.
"""

from blackbyrd3d.app import MainWindow


def _close(w):
    w.mark_saved()
    w.close()


def test_the_ortho_button_holds_in_every_pane():
    w = MainWindow()
    w.set_view_layout("quad")
    w.osnap_bar._ortho.setChecked(True)
    assert all(vp.ortho for vp in w.all_viewports())
    w.osnap_bar._ortho.setChecked(False)
    assert not any(vp.ortho for vp in w.all_viewports())
    _close(w)


def test_f8_in_another_pane_is_the_same_switch():
    w = MainWindow()
    w.set_view_layout("quad")
    other = [vp for vp in w.all_viewports() if vp is not w.viewport][0]
    w.ctx.viewport = other
    before = w.viewport.ortho
    w.processor.run("ortho")
    assert w.viewport.ortho is not before
    assert all(vp.ortho is not before for vp in w.all_viewports())
    assert w.osnap_bar._ortho.isChecked() is not before
    _close(w)


def test_grid_snap_holds_in_every_pane():
    w = MainWindow()
    w.set_view_layout("quad")
    w.osnap_bar._grid.setChecked(True)
    assert all(vp.grid_snap for vp in w.all_viewports())
    w.viewport.grid_snap_step = 2.5
    assert all(vp.grid_snap_step == 2.5 for vp in w.all_viewports())
    _close(w)
