"""A typed box or cylinder height always went up. It goes to the cursor's
side of the base, and a negative number to the other side."""

import pytest

from blackbyrd3d.commands.base import CommandContext, CommandProcessor
from blackbyrd3d.core import geometry as g
from blackbyrd3d.core.history import History
from blackbyrd3d.core.scene import Scene
from blackbyrd3d.core.selection import SelectionManager

import blackbyrd3d.commands  # noqa: F401

UP, DOWN = (0.0, 0.0, 1.0), (0.0, 0.0, -1.0)

BASES = {
    "box": [(0.0, 0.0, 0.0), (4.0, 3.0, 0.0)],
    "box center": ["Center", (0.0, 0.0, 0.0), (2.0, 1.5, 0.0)],
    "cylinder": [(0.0, 0.0, 0.0), "2"],
}


def _draw(kind, aim, text):
    scene = Scene()
    ctx = CommandContext(scene, SelectionManager(scene), History(scene))
    proc = CommandProcessor(ctx)
    proc.run(kind.split()[0])
    for answer in BASES[kind]:
        if isinstance(answer, str):
            proc.provide_text(answer)
        else:
            proc.provide(answer)
    assert proc.busy, "should be asking for the height"
    ctx.replay_aim = None if aim is None else ((0.0, 0.0, 0.0), aim)
    proc.provide_text(text)
    assert not proc.busy
    solid = scene.all()[-1]
    lo, hi = g.bbox(solid.shape)
    return lo[2], hi[2]


@pytest.mark.parametrize("kind", list(BASES))
@pytest.mark.parametrize("aim, text, expected", [
    (UP, "10", (0, 10)),
    (DOWN, "10", (-10, 0)),
    (UP, "-10", (-10, 0)),
    (DOWN, "-10", (0, 10)),
    (None, "10", (0, 10)),
])
def test_the_cursor_says_which_way(kind, aim, text, expected):
    assert _draw(kind, aim, text) == pytest.approx(expected, abs=1e-6)


@pytest.fixture
def window(tmp_path, monkeypatch):
    import json
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({}))
    monkeypatch.setenv("BYRD3D_CONFIG", str(cfg))
    monkeypatch.setenv("BYRD3D_AUTOSAVE_DIR", str(tmp_path / "autosave"))
    from blackbyrd3d.app import MainWindow
    w = MainWindow()
    yield w
    w._saved_revision = w.scene.revision
    w.close()


def test_the_cylinder_height_is_aimed_from_its_base(window):
    """Without a base in the pane there is no cursor direction to ask."""
    window.processor.run("cylinder")
    window.processor.provide((1.0, 2.0, 0.0))
    window.processor.provide_text("2")
    assert window.processor.busy
    assert window.viewport.snap_base == (1.0, 2.0, 0.0)
